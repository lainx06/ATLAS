"""Runner-container entry (SPEC §10). Mounted read-only at /opt/atlas/atlas_runner_entry.py.

Two roles, both inside the disposable container:

- `supervise` (PID 1, standard library only): makes itself non-dumpable so candidate code (same
  uid) cannot reach its file descriptors, starts the candidate as a child process with an
  explicit minimal environment, enforces the execution timeout, kills every remaining process,
  then writes ONE frame to stdout: `ATLAS-OUT-V1 <header JSON>\\n<tar archive>`. The archive
  holds the regular files under /work/out (a size-capped tmpfs that disappears when the
  container stops), within file-count and byte caps. The host validates the frame again.
- `child`: imports the mounted adapter, reads the snapshot's manifest and table, writes
  runtime.json and runs the entry point inside an adapter session (as the trusted runner does).

Nothing here is a security boundary by itself; the container restrictions are.
"""

import hashlib
import io
import json
import os
import signal
import stat
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

PROJECT = Path("/work/project")
OUT = Path("/work/out")
CODE = Path("/opt/atlas")
MANIFEST_NAME = "atlas_manifest.json"
FRAME_MAGIC = b"ATLAS-OUT-V1 "
FRAME_VERSION = 1
TAIL_BYTES = 16 * 1024
MAX_SKIPPED_REPORTED = 50
# The candidate's whole environment. BLAS/OpenMP pools are pinned to one thread so thread
# counts stay well inside the PID limit (threads count as PIDs).
CHILD_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp",
    "TMPDIR": "/tmp",
    "LANG": "C.UTF-8",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
}
# The child first makes itself the OOM killer's preferred target (raising one's own
# oom_score_adj needs no privilege), then runs child_main().
CHILD_LAUNCH = (
    "import sys; sys.path.insert(0, '/opt/atlas'); "
    "import atlas_runner_entry; atlas_runner_entry.raise_oom_score(); "
    "atlas_runner_entry.child_main()"
)


# --- supervisor (PID 1) ---------------------------------------------------------------------


def _set_nondumpable() -> bool:
    """PR_SET_DUMPABLE=0: same-uid processes can no longer open /proc/1/fd/* or ptrace PID 1."""
    try:
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        return libc.prctl(4, 0, 0, 0, 0) == 0  # PR_SET_DUMPABLE = 4
    except (OSError, AttributeError):
        return False


def _read_events(path: str) -> dict:
    try:
        text = Path(path).read_text()
    except OSError:
        return {}
    out = {}
    for line in text.splitlines():
        key, _, value = line.partition(" ")
        if value.strip().isdigit():
            out[key] = int(value)
    return out


def _kill_all_others() -> None:
    """SIGKILL every process this one may signal; as PID 1 (init) it is itself exempt."""
    try:
        os.kill(-1, signal.SIGKILL)
    except OSError:
        pass
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            time.sleep(0.02)


def _pack_outputs(max_files: int, max_bytes: int) -> tuple[bytes, dict]:
    """Regular files under OUT as an uncompressed tar with normalized metadata."""
    files, skipped, total = [], [], 0
    for dirpath, dirnames, filenames in os.walk(OUT, followlinks=False):
        for name in sorted(dirnames):
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                skipped.append({"path": os.path.relpath(full, OUT), "type": "symlink"})
        dirnames[:] = sorted(
            d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))
        )
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, OUT)
            st = os.lstat(full)
            if not _is_regular(st.st_mode):
                skipped.append({"path": rel, "type": _kind(st.st_mode)})
                continue
            files.append((rel, full))
            if len(files) > max_files:  # stop walking: bounds collection time
                break
        if len(files) > max_files:
            break
    meta = {"files": len(files), "skipped": skipped[:MAX_SKIPPED_REPORTED]}
    meta["skipped_count"] = len(skipped)
    if len(files) > max_files:
        return b"", {**meta, "archive_error": "file_count_exceeded"}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for rel, full in files:
            fd = os.open(full, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as f:
                st = os.fstat(f.fileno())
                if not _is_regular(st.st_mode):
                    return b"", {**meta, "archive_error": "file_changed_type"}
                total += st.st_size
                if total > max_bytes:
                    return b"", {**meta, "archive_error": "expanded_bytes_exceeded"}
                data = f.read(st.st_size + 1)
            if len(data) != st.st_size:
                return b"", {**meta, "archive_error": "file_changed_size"}
            info = tarfile.TarInfo(rel.replace(os.sep, "/"))
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue(), {**meta, "expanded_bytes": total, "archive_error": None}


def _is_regular(mode: int) -> bool:
    return stat.S_ISREG(mode)


def _kind(mode: int) -> str:
    for test, name in (
        (stat.S_ISLNK, "symlink"),
        (stat.S_ISFIFO, "fifo"),
        (stat.S_ISSOCK, "socket"),
        (stat.S_ISCHR, "char_device"),
        (stat.S_ISBLK, "block_device"),
    ):
        if test(mode):
            return name
    return "other"


def supervise(timeout_s: float, max_files: int, max_bytes: int) -> int:
    header: dict = {"version": FRAME_VERSION, "nondumpable": _set_nondumpable()}
    archive = b""
    try:
        started = time.monotonic()
        proc = subprocess.Popen(
            [sys.executable, "-I", "-B", "-c", CHILD_LAUNCH],
            cwd=PROJECT,
            env=CHILD_ENV,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        tail = bytearray()
        counted = [0]

        def drain() -> None:
            for chunk in iter(lambda: proc.stdout.read(65536), b""):
                counted[0] += len(chunk)
                tail.extend(chunk)
                del tail[:-TAIL_BYTES]

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        timed_out = False
        try:
            returncode = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            returncode = proc.wait()
        _kill_all_others()
        reader.join(timeout=2.0)
        header.update(
            child_returncode=returncode,
            timed_out=timed_out,
            child_elapsed_s=round(time.monotonic() - started, 3),
            candidate_output_bytes=counted[0],
            candidate_output_tail=bytes(tail).decode("utf-8", "replace"),
            cgroup={
                "memory_events": _read_events("/sys/fs/cgroup/memory.events"),
                "pids_events": _read_events("/sys/fs/cgroup/pids.events"),
            },
        )
        archive, meta = _pack_outputs(max_files, max_bytes)
        header.update(meta)
    except Exception as exc:  # noqa: BLE001 - report, never hang: the host still gets one frame
        archive = b""
        header["supervisor_error"] = f"{type(exc).__name__}: {exc}"[:2000]
    header["archive_bytes"] = len(archive)
    header["archive_sha256"] = hashlib.sha256(archive).hexdigest()
    out = sys.stdout.buffer
    out.write(FRAME_MAGIC + json.dumps(header, sort_keys=True).encode() + b"\n")
    out.write(archive)
    out.flush()
    return 0


# --- child (candidate process) ---------------------------------------------------------------


def raise_oom_score() -> None:
    try:
        with open("/proc/self/oom_score_adj", "w") as f:
            f.write("1000")
    except OSError:
        pass


def _runtime_record() -> dict:
    import atlas

    return {
        "python": sys.version.split()[0],
        "isolated": sys.flags.isolated,
        "safe_path": bool(sys.flags.safe_path),
        "uid": os.getuid(),
        "gid": os.getgid(),
        "cwd": os.getcwd(),
        "sys_path": list(sys.path),
        "atlas_origin": str(Path(atlas.__file__).resolve()),
        "atlas_modules": sorted(os.listdir(CODE / "atlas")),
    }


def child_main() -> None:
    import runpy

    from atlas import adapter
    from atlas.tables import read_table

    OUT.mkdir(exist_ok=True)
    (OUT / "runtime.json").write_text(
        json.dumps(_runtime_record(), indent=2) + "\n", encoding="utf-8"
    )
    manifest = json.loads((PROJECT / MANIFEST_NAME).read_text(encoding="utf-8"))
    table = read_table(
        PROJECT / manifest["table"]["path"],
        manifest["table"]["format"],
        manifest["columns"]["row_id"],
    )
    with adapter.session(manifest, table, OUT):
        runpy.run_path(str(PROJECT / manifest["entry_point"]), run_name="__main__")


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "supervise":
        raise SystemExit(
            "usage: atlas_runner_entry.py supervise TIMEOUT MAX_FILES MAX_BYTES"
        )
    sys.exit(supervise(float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])))
