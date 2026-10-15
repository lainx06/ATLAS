"""Docker runner for approved candidates (SPEC §9, §10). T-05.

The only path by which candidate code executes. There is no host fallback: when isolation is
unavailable (no Docker CLI, unreachable daemon, missing or mismatched runner image) the result
is `not_executed` and nothing runs anywhere. This module never imports the trusted-fixture
runner or its bootstrap.

Container policy (each flag is in `docker_run_args`): non-root user, read-only root filesystem,
`--network none`, `--cap-drop ALL`, `no-new-privileges`, default seccomp, memory without swap,
CPU and PID limits, no IPC namespace sharing (`--ipc none`: no /dev/shm), size-capped tmpfs
scratch (/tmp) and outputs (/work/out), no environment passed from the host, no Docker socket,
and exactly two read-only bind mounts: the staged project snapshot and the staged
adapter/recorder code. The execution timeout is enforced inside (the supervisor) and outside
(the host deadline, after which the container is killed and removed).

Outputs live on a tmpfs that disappears when the container stops, so the in-container
supervisor (PID 1) emits them as one framed tar archive on stdout before exiting; the host
reads it under byte, file-count, expanded-size and time caps, validates every entry and only
then writes files. Containers created here are always removed (success, timeout, malformed
output, collection failure).

Containers reduce execution risk; they do not make hostile code safe (SPEC §10) and do not
prove provenance integrity or scientific correctness (SPEC §9.9).

Build the image:  uv run --locked python -m atlas.runner.docker build
Probe capability: uv run --locked python -m atlas.runner.docker probe
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import atlas
from atlas.candidates import (
    Approval,
    Candidate,
    Snapshot,
    SnapshotError,
    candidate_hash,
    current_inventory,
    inventory_hash,
    safe_relpath,
    sha256_bytes,
)
from atlas.reports import write_json

RUNNER_NAME = "docker_isolated"
CAPABILITY_AVAILABLE = "isolated_available"
CAPABILITY_UNAVAILABLE = "unavailable"
IMAGE_TAG = "atlas-runner:t05"
TASK_LABEL = "atlas.runner"
TASK_LABEL_VALUE = "t05"
RECIPE_LABEL = "atlas.runner.recipe_sha256"
RUNNER_USER = "10001:10001"
REPO_ROOT = Path(__file__).resolve().parents[3]
# Build context allowlist: context name -> repository path. Nothing else is sent to Docker.
BUILD_CONTEXT = {
    "Dockerfile": "Dockerfile.runner",
    "runner-requirements.txt": "docker/runner-requirements.txt",
}
PACKAGE_DIR = Path(atlas.__file__).resolve().parent
# The only atlas code mounted into the container (adapter, recorder and their imports).
MOUNTED_MODULES = (
    "__init__.py",
    "adapter.py",
    "recorder.py",
    "reports.py",
    "tables.py",
)
ENTRY_SOURCE = PACKAGE_DIR / "runner" / "container_entry.py"
ENTRY_NAME = "atlas_runner_entry.py"
_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
FRAME_MAGIC = b"ATLAS-OUT-V1 "
MAX_HEADER_BYTES = 256 * 1024
STDERR_TAIL_BYTES = 64 * 1024
CLI_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class Limits:
    memory_bytes: int = 1 << 30  # 1 GiB, and the same value for memory+swap: no swap
    cpus: str = "1"
    pids: int = 128
    exec_timeout_s: float = 30.0
    scratch_bytes: int = 64 << 20
    output_bytes: int = 32 << 20
    max_output_files: int = 256
    host_grace_s: float = 30.0  # container start + output collection beyond the timeout
    host_deadline_s: float | None = (
        None  # explicit override (tests of the outer kill path)
    )
    max_stderr_bytes: int = 1 << 20

    @property
    def deadline_s(self) -> float:
        if self.host_deadline_s is not None:
            return self.host_deadline_s
        return self.exec_timeout_s + self.host_grace_s

    @property
    def max_archive_bytes(self) -> int:
        # tar overhead: <= 1.5 KiB of headers and padding per file, plus end blocks.
        return self.output_bytes + self.max_output_files * 2048 + 64 * 1024

    @property
    def max_stdout_bytes(self) -> int:
        return len(FRAME_MAGIC) + MAX_HEADER_BYTES + 1 + self.max_archive_bytes

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "deadline_s": self.deadline_s,
            "max_archive_bytes": self.max_archive_bytes,
            "max_stdout_bytes": self.max_stdout_bytes,
        }


DEFAULT_LIMITS = Limits()


@dataclass
class Capability:
    state: str
    reason: str | None
    docker_cli: str | None = None
    server_version: str | None = None
    server_os: str | None = None
    context: str | None = None
    image_ref: str | None = None
    image_id: str | None = None
    recipe_sha256: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class CollectionError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


# --- Docker CLI ---------------------------------------------------------------------------


def resolve_docker_cli(env=None, exclude=()) -> Path | None:
    """The Docker CLI from absolute PATH entries, then the known per-user/system install dirs.

    Relative PATH entries (including '.') and any directory inside `exclude` (candidate,
    snapshot and run directories) are never searched. Unlike shutil.which on Windows, the
    current directory is not searched implicitly.
    """
    env = os.environ if env is None else env
    names = ("docker.exe",) if os.name == "nt" else ("docker",)
    excluded = [Path(e).resolve() for e in exclude]
    dirs = [
        Path(p.strip().strip('"'))
        for p in env.get("PATH", "").split(os.pathsep)
        if p.strip().strip('"') and os.path.isabs(p.strip().strip('"'))
    ]
    for var, rel in (
        ("LOCALAPPDATA", "Programs/DockerDesktop/resources/bin"),
        ("ProgramFiles", "Docker/Docker/resources/bin"),
    ):
        root = env.get(var)
        if root and os.path.isabs(root):
            dirs.append(Path(root) / rel)
    for d in dirs:
        try:
            rd = d.resolve()
        except OSError:
            continue
        if any(rd == e or rd.is_relative_to(e) for e in excluded):
            continue
        for name in names:
            exe = rd / name
            if exe.is_file():
                return exe
    return None


def cli_env(cli: Path, env=None) -> dict:
    """Environment for the Docker CLI itself: secret-like names removed; the CLI's own
    directory first on PATH (for its credential helpers). Nothing here reaches the container."""
    env = dict(os.environ if env is None else env)
    clean = {
        k: v for k, v in env.items() if not any(m in k.upper() for m in _SECRET_MARKERS)
    }
    path_key = next((k for k in clean if k.upper() == "PATH"), "PATH")
    clean[path_key] = str(cli.parent) + os.pathsep + clean.get(path_key, "")
    return clean


def _docker(cli: Path, args: list[str], env: dict, timeout: float = CLI_TIMEOUT_S):
    """Every short Docker CLI call goes through here (one place to observe in tests)."""
    return subprocess.run(
        [str(cli), *args],
        env=env,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )


def _spawn(cli: Path, args: list[str], env: dict) -> subprocess.Popen:
    """The container run itself (one place to observe in tests)."""
    return subprocess.Popen(
        [str(cli), *args],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


# --- image recipe, build and capability ---------------------------------------------------


def _lf_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def recipe_sha256() -> str:
    """Hash of the exact build context (LF-normalized), recorded as an image label."""
    h = hashlib.sha256()
    for name in sorted(BUILD_CONTEXT):
        data = _lf_bytes(REPO_ROOT / BUILD_CONTEXT[name])
        h.update(f"{name}\0{len(data)}\0".encode())
        h.update(data)
    return h.hexdigest()


def write_build_context(dest: Path) -> list[str]:
    """Write only the allowlisted files into the empty directory `dest`."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=False)
    for name, rel in BUILD_CONTEXT.items():
        (dest / name).write_bytes(_lf_bytes(REPO_ROOT / rel))
    return sorted(p.name for p in dest.iterdir())


def build_image(tag: str = IMAGE_TAG, env=None) -> dict:
    cli = resolve_docker_cli(env)
    if cli is None:
        raise RuntimeError("Docker CLI not found")
    e = cli_env(cli, env)
    recipe = recipe_sha256()
    with tempfile.TemporaryDirectory(prefix="atlas-runner-build-") as tmp:
        ctx = Path(tmp) / "context"
        files = write_build_context(ctx)
        args = ["build", "--file", str(ctx / "Dockerfile"), "--tag", tag]
        args += ["--label", f"{RECIPE_LABEL}={recipe}"]
        args += ["--label", f"{TASK_LABEL}={TASK_LABEL_VALUE}", str(ctx)]
        proc = subprocess.run([str(cli), *args], env=e, timeout=1800, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"docker build failed with exit code {proc.returncode}")
    inspect = _docker(cli, ["image", "inspect", tag, "--format", "{{.Id}}"], e)
    return {
        "image": tag,
        "image_id": inspect.stdout.decode().strip(),
        "recipe_sha256": recipe,
        "context_files": files,
        "docker_cli": str(cli),
    }


def probe(image: str = IMAGE_TAG, env=None, exclude=()) -> Capability:
    """Is isolated execution available right now? Checks the CLI, the daemon, the server OS
    and the runner image (recipe label and non-root user). Does not run a container."""

    def unavailable(reason: str, **kw) -> Capability:
        return Capability(CAPABILITY_UNAVAILABLE, reason, **kw)

    cli = resolve_docker_cli(env, exclude)
    if cli is None:
        return unavailable(
            "Docker CLI not found on PATH or in the known install locations"
        )
    e = cli_env(cli, env)
    try:
        version = _docker(cli, ["version", "--format", "{{json .}}"], e)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return unavailable(
            f"Docker CLI failed: {type(exc).__name__}", docker_cli=str(cli)
        )
    try:
        server = json.loads(version.stdout or b"{}").get("Server") or {}
    except ValueError:
        server = {}
    if version.returncode != 0 or not server:
        tail = version.stderr.decode("utf-8", "replace")[-300:].strip()
        return unavailable(f"Docker daemon unreachable: {tail}", docker_cli=str(cli))
    seen = {
        "docker_cli": str(cli),
        "server_version": server.get("Version"),
        "server_os": server.get("Os"),
    }
    if server.get("Os") != "linux":
        return unavailable("Docker server is not running Linux containers", **seen)
    context = _docker(cli, ["context", "show"], e).stdout.decode().strip() or None
    seen.update(context=context, image_ref=image)
    inspect = _docker(cli, ["image", "inspect", image, "--format", "{{json .}}"], e)
    if inspect.returncode != 0:
        return unavailable(
            f"runner image {image} is missing; build it with "
            "`uv run --locked python -m atlas.runner.docker build`",
            **seen,
        )
    data = json.loads(inspect.stdout)
    config = data.get("Config") or {}
    expected = recipe_sha256()
    seen.update(image_id=data.get("Id"), recipe_sha256=expected)
    if (config.get("Labels") or {}).get(RECIPE_LABEL) != expected:
        return unavailable("runner image was built from a different recipe", **seen)
    if config.get("User") != RUNNER_USER:
        return unavailable(
            "runner image does not run as the non-root runner user", **seen
        )
    return Capability(CAPABILITY_AVAILABLE, None, **seen)


# --- staging --------------------------------------------------------------------------------


def stage_code(dest: Path) -> tuple[tuple[str, str], ...]:
    """Copy only the mounted modules and the container entry into `dest`."""
    (dest / "atlas").mkdir(parents=True)
    for name in MOUNTED_MODULES:
        (dest / "atlas" / name).write_bytes(_lf_bytes(PACKAGE_DIR / name))
    (dest / ENTRY_NAME).write_bytes(_lf_bytes(ENTRY_SOURCE))
    paths = [f"atlas/{n}" for n in MOUNTED_MODULES] + [ENTRY_NAME]
    return current_inventory(dest, paths)


def stage_project(snapshot: Snapshot, candidate: Candidate, dest: Path) -> None:
    for rel, _ in snapshot.inventory:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel == snapshot.entry_point:
            data = candidate.entry_bytes
        else:
            data = (snapshot.root / rel).read_bytes()
        with open(target, "xb") as f:
            f.write(data)


def docker_run_args(
    name: str, run_id: str, project: Path, code: Path, image_id: str, limits: Limits
) -> list[str]:
    mem = str(limits.memory_bytes)
    return [
        "run",
        "--name", name,
        "--label", f"{TASK_LABEL}={TASK_LABEL_VALUE}",
        "--label", f"atlas.run={run_id}",
        "--pull", "never",
        "--network", "none",
        "--read-only",
        "--user", RUNNER_USER,
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges=true",
        "--memory", mem,
        "--memory-swap", mem,
        "--cpus", limits.cpus,
        "--pids-limit", str(limits.pids),
        "--ulimit", "core=0",
        "--ulimit", "nofile=1024:1024",
        "--ipc", "none",
        "--hostname", "atlas-runner",
        "--log-driver", "none",
        "--tmpfs", f"/tmp:rw,noexec,nosuid,nodev,size={limits.scratch_bytes},mode=1777",
        "--tmpfs", f"/work/out:rw,noexec,nosuid,nodev,size={limits.output_bytes},mode=1777",
        "--mount", f"type=bind,source={project},target=/work/project,readonly",
        "--mount", f"type=bind,source={code},target=/opt/atlas,readonly",
        "--workdir", "/work/project",
        "--entrypoint", "/usr/local/bin/python",
        image_id,
        "-I", "-B", f"/opt/atlas/{ENTRY_NAME}", "supervise",
        str(limits.exec_timeout_s),
        str(limits.max_output_files),
        str(limits.output_bytes),
    ]  # fmt: skip


# --- bounded IO, frame and archive ---------------------------------------------------------


def communicate_bounded(proc: subprocess.Popen, limits: Limits) -> dict:
    """Read stdout/stderr concurrently under byte caps until exit, overflow or the deadline.

    Returns as soon as one of those happens; the caller kills the container and the process.
    """
    stdout, stderr_tail = bytearray(), bytearray()
    counts = {"stdout": 0, "stderr": 0}
    problems: list[str] = []
    overflow = threading.Event()

    def pump(stream, key: str, cap: int) -> None:
        for chunk in iter(lambda: stream.read(65536), b""):
            counts[key] += len(chunk)
            if counts[key] > cap:
                if not overflow.is_set():
                    problems.append(f"{key}_cap_exceeded")
                    overflow.set()
                continue  # keep draining so the writer is not blocked; store nothing more
            if key == "stdout":
                stdout.extend(chunk)
            else:
                stderr_tail.extend(chunk)
                del stderr_tail[:-STDERR_TAIL_BYTES]

    threads = [
        threading.Thread(
            target=pump,
            args=(proc.stdout, "stdout", limits.max_stdout_bytes),
            daemon=True,
        ),
        threading.Thread(
            target=pump,
            args=(proc.stderr, "stderr", limits.max_stderr_bytes),
            daemon=True,
        ),
    ]
    for t in threads:
        t.start()
    deadline = time.monotonic() + limits.deadline_s
    host_timed_out = False
    while proc.poll() is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            host_timed_out = True
            break
        if overflow.wait(min(remaining, 0.2)):
            break
    return {
        "stdout": stdout,
        "stderr_tail": stderr_tail,
        "counts": counts,
        "problems": problems,
        "host_timed_out": host_timed_out,
        "threads": threads,
    }


def parse_frame(data: bytes, limits: Limits) -> tuple[dict, bytes]:
    """Exactly one frame: magic, header JSON line, archive of the declared length and hash."""
    if not data.startswith(FRAME_MAGIC):
        raise CollectionError("missing_frame")
    start = len(FRAME_MAGIC)
    newline = data.find(b"\n", start, start + MAX_HEADER_BYTES + 1)
    if newline < 0:
        raise CollectionError("malformed_header", "no header terminator within the cap")
    try:
        header = json.loads(data[start:newline])
    except ValueError as exc:
        raise CollectionError("malformed_header", "not JSON") from exc
    if (
        not isinstance(header, dict)
        or header.get("version") != 1
        or not isinstance(header.get("archive_bytes"), int)
        or not isinstance(header.get("archive_sha256"), str)
    ):
        raise CollectionError("malformed_header", "missing or invalid fields")
    archive = data[newline + 1 :]
    if len(archive) > limits.max_archive_bytes:
        raise CollectionError("archive_too_large")
    if len(archive) != header["archive_bytes"]:
        raise CollectionError("archive_length_mismatch")
    if sha256_bytes(archive) != header["archive_sha256"]:
        raise CollectionError("archive_hash_mismatch")
    return header, archive


def extract_archive(archive: bytes, dest: Path, limits: Limits) -> list[dict]:
    """Validate every entry first, then write regular files only into the new `dest`."""
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            members = _validated_members(tar, limits)
            return _write_members(tar, members, Path(dest))
    except tarfile.TarError as exc:
        raise CollectionError("malformed_archive", str(exc)) from exc


def _validated_members(tar: tarfile.TarFile, limits: Limits) -> list:
    members = []
    seen: set[str] = set()
    implied_dirs: set[str] = set()
    total = 0
    for member in tar:
        if len(members) >= limits.max_output_files:
            raise CollectionError("file_count_exceeded")
        if not member.isreg():
            raise CollectionError("unsafe_entry_type", member.name[:200])
        try:
            name = safe_relpath(member.name)
        except SnapshotError as exc:
            raise CollectionError("unsafe_path", member.name[:200]) from exc
        key = name.casefold()
        parts = key.split("/")
        prefixes = {"/".join(parts[:i]) for i in range(1, len(parts))}
        if key in seen:
            raise CollectionError("duplicate_entry", name)
        if key in implied_dirs or prefixes & seen:
            raise CollectionError("path_conflict", name)
        seen.add(key)
        implied_dirs |= prefixes
        total += member.size
        if total > limits.output_bytes:
            raise CollectionError("expanded_bytes_exceeded")
        members.append((name, member))
    return members


def _write_members(tar: tarfile.TarFile, members: list, dest: Path) -> list[dict]:
    dest.mkdir(parents=True, exist_ok=False)
    root = dest.resolve()
    files = []
    for name, member in members:
        data = tar.extractfile(member).read(member.size + 1)
        if len(data) != member.size:
            raise CollectionError("truncated_entry", name)
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.resolve().is_relative_to(root):
            raise CollectionError("unsafe_path", name)
        with open(target, "xb") as f:
            f.write(data)
        files.append({"path": name, "size": member.size, "sha256": sha256_bytes(data)})
    return files


# --- lifecycle ------------------------------------------------------------------------------


def _remove_container(cli: Path, env: dict, name: str) -> dict:
    """Inspect, then force-remove a container this runner created; confirm it is gone."""
    state = None
    try:
        inspect = _docker(
            cli, ["container", "inspect", name, "--format", "{{json .State}}"], env
        )
        if inspect.returncode == 0:
            state = json.loads(inspect.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    removed = False
    for _ in range(3):
        try:
            _docker(cli, ["rm", "--force", name], env)
            gone = _docker(
                cli, ["container", "inspect", name, "--format", "{{.Id}}"], env
            )
            removed = gone.returncode != 0
        except (OSError, subprocess.TimeoutExpired):
            removed = False
        if removed:
            break
        time.sleep(0.5)
    return {"state": state, "removed": removed}


def run_candidate(
    snapshot: Snapshot,
    candidate: Candidate,
    approval: Approval,
    run_dir: Path,
    *,
    limits: Limits = DEFAULT_LIMITS,
    image: str = IMAGE_TAG,
    env=None,
) -> dict:
    """Execute one approved candidate in the isolated runner; never on the host.

    Writes run_dir/execution.json and returns the same record. Statuses: `refused` (hash or
    staging check failed; nothing started), `not_executed` (isolation unavailable),
    `completed`, `failed` (non-zero exit), `timed_out`, `collection_failed`.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    record: dict = {
        "runner": RUNNER_NAME,
        "capability": None,
        "status": None,
        "reason": None,
        "approval": approval.to_dict(),
        "base_snapshot_hash": snapshot.base_hash,
        "candidate_hash": None,
        "limits": limits.to_dict(),
        "started_utc": datetime.now(UTC).isoformat(),
        "full_reevaluation": "not performed by the runner (T-06 schedules the required set)",
    }
    try:
        _run(snapshot, candidate, approval, run_dir, limits, image, env, record)
    finally:
        write_json(run_dir / "execution.json", record)
    return record


def _refuse(record: dict, reason: str) -> None:
    record.update(status="refused", reason=reason)


def _run(snapshot, candidate, approval, run_dir, limits, image, env, record) -> None:
    # 1. Hash binding, before anything touches Docker.
    paths = [rel for rel, _ in snapshot.inventory]
    try:
        live = current_inventory(snapshot.root, paths)
    except SnapshotError as exc:
        return _refuse(record, f"snapshot_invalid: {exc}")
    if inventory_hash(live) != snapshot.base_hash:
        return _refuse(record, "base_snapshot_changed")
    if approval.base_snapshot_hash != snapshot.base_hash:
        return _refuse(record, "approval_for_other_snapshot")
    if candidate.entry_point != snapshot.entry_point:
        return _refuse(record, "candidate_entry_point_mismatch")
    computed = candidate_hash(snapshot.base_hash, candidate.entry_bytes)
    record["candidate_hash"] = computed
    if computed != approval.candidate_hash:
        return _refuse(record, "candidate_hash_mismatch")

    # 2. Capability. Unavailable isolation means no execution, anywhere.
    cap = probe(image, env, exclude=[snapshot.root, run_dir])
    record["capability"] = cap.state
    record["docker"] = cap.to_dict()
    if cap.state != CAPABILITY_AVAILABLE:
        record.update(
            status="not_executed", reason=f"isolation unavailable: {cap.reason}"
        )
        return None

    # 3. Stage exactly the approved bytes and re-check them as they will be mounted.
    project, code = run_dir / "stage" / "project", run_dir / "stage" / "code"
    stage_project(snapshot, candidate, project)
    record["mounted_code"] = [list(i) for i in stage_code(code)]
    staged = dict(current_inventory(project, paths))
    expected = dict(snapshot.inventory)
    expected[snapshot.entry_point] = sha256_bytes(candidate.entry_bytes)
    entry_bytes = (project / snapshot.entry_point).read_bytes()
    if staged != expected or (
        candidate_hash(approval.base_snapshot_hash, entry_bytes)
        != approval.candidate_hash
    ):
        return _refuse(record, "staged_bytes_mismatch")
    record["staged_project"] = sorted([list(i) for i in staged.items()])
    for path in (project, code):
        if "," in str(path.resolve()):
            return _refuse(record, "unsafe_mount_path")

    # 4. Run, bounded; always remove the container.
    cli = Path(cap.docker_cli)
    e = cli_env(cli, env)
    run_id = run_dir.name
    name = f"atlas-t05-{uuid.uuid4().hex[:12]}"
    args = docker_run_args(
        name, run_id, project.resolve(), code.resolve(), cap.image_id, limits
    )
    record.update(container_name=name, docker_args=args)
    started = time.monotonic()
    io_result = None
    try:
        proc = _spawn(cli, args, e)
    except OSError as exc:
        record.update(
            status="not_executed",
            reason=f"docker run could not start: {type(exc).__name__}",
            container_removed=_remove_container(cli, e, name)["removed"],
        )
        return None
    try:
        io_result = communicate_bounded(proc, limits)
    finally:
        cleanup = _remove_container(cli, e, name)
        if proc.poll() is None:
            proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        if io_result:
            for t in io_result["threads"]:
                t.join(timeout=5)
    record.update(
        elapsed_s=round(time.monotonic() - started, 3),
        container_removed=cleanup["removed"],
        docker_state=cleanup["state"],
        docker_cli_returncode=proc.returncode,
        host_timed_out=io_result["host_timed_out"],
        io_problems=io_result["problems"],
        stdout_bytes=io_result["counts"]["stdout"],
        stderr_bytes=io_result["counts"]["stderr"],
        stderr_tail=bytes(io_result["stderr_tail"]).decode("utf-8", "replace"),
    )

    # 5. Collect: parse the frame, then validate and extract the archive.
    out_dir = run_dir / "out"
    collection: dict = {"status": "ok", "problem": None, "files": []}
    record["collection"] = collection
    try:
        if io_result["problems"]:
            raise CollectionError(io_result["problems"][0])
        if io_result["host_timed_out"]:
            raise CollectionError("host_deadline_exceeded")
        header, archive = parse_frame(bytes(io_result["stdout"]), limits)
        record["supervisor"] = header
        if header.get("supervisor_error"):
            raise CollectionError("supervisor_error", header["supervisor_error"])
        if header.get("archive_error"):
            raise CollectionError(header["archive_error"])
        collection["files"] = extract_archive(archive, out_dir, limits)
    except CollectionError as exc:
        collection.update(status="failed", problem=exc.code, detail=str(exc))
        shutil.rmtree(out_dir, ignore_errors=True)
    except OSError as exc:
        collection.update(status="failed", problem="write_failed", detail=str(exc))
        shutil.rmtree(out_dir, ignore_errors=True)

    sup = record.get("supervisor") or {}
    if io_result["host_timed_out"] or sup.get("timed_out"):
        record.update(status="timed_out", reason="execution timeout")
    elif collection["status"] != "ok":
        record.update(status="collection_failed", reason=collection["problem"])
    elif sup.get("child_returncode") != 0:
        record.update(
            status="failed",
            reason=f"candidate exited with {sup.get('child_returncode')}",
        )
    else:
        record.update(status="completed", reason=None)
    return None


def main(argv: list[str]) -> int:
    if argv == ["build"]:
        print(json.dumps(build_image(), indent=2))
        return 0
    if argv == ["probe"]:
        cap = probe()
        print(json.dumps(cap.to_dict(), indent=2))
        return 0 if cap.state == CAPABILITY_AVAILABLE else 1
    print("usage: python -m atlas.runner.docker build|probe", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
