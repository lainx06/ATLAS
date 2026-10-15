"""T-05 runner contract (SPEC §9, §10): what the isolated Docker runner enforces.

Acceptance command (Docker tests fail instead of skipping when isolation is unavailable):
    ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py

Section A needs no Docker: unavailable isolation and hash mismatches never execute anything.
Section B runs controlled probe candidates in the real container, sequentially, in file order:
restrictions and limits are verified first; the memory and PID stress probes depend on that
verification. Every probe is an approved candidate going through the full SPEC §9 path
(snapshot -> unified diff -> validation -> approval -> hash-checked staging -> container).
Only containers created here (label atlas.runner=t05, names recorded below) are ever removed.
"""

import difflib
import json
import os
import subprocess
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from atlas.candidates import (
    CandidateRejected,
    approve,
    build_snapshot,
    validate_diff,
)
from atlas.runner import docker as dr
from atlas.runner.container_entry import CHILD_ENV, TAIL_BYTES
from atlas.runner.trusted import run_trusted_fixture

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "benchmarks" / "t01" / "s02_clean"
OTHER = ROOT / "benchmarks" / "t01" / "s01_faulty"
REQUIRE_DOCKER = os.environ.get("ATLAS_REQUIRE_DOCKER") == "1"
CREATED: list[str] = []
# Set by scikit-learn itself at import (inside the container), not passed from the host.
SKLEARN_SET_ENV = {"KMP_DUPLICATE_LIB_OK", "KMP_INIT_AT_FORK"}
EROFS, EACCES, ENOSPC, EAGAIN = 30, 13, 28, 11


def make_diff(old: str, new: str, path: str = "evaluate.py") -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}"
        )
    )


def snapshot_and_candidate(tmp_path: Path, source: str, project: Path = CLEAN):
    snap = build_snapshot(project, tmp_path / "snapshot")
    old = (snap.root / snap.entry_point).read_text(encoding="utf-8")
    cand = validate_diff(snap, make_diff(old, textwrap.dedent(source).lstrip()))
    return snap, cand


def run_source(tmp_path: Path, source: str, **kwargs):
    snap, cand = snapshot_and_candidate(tmp_path, source)
    rec = dr.run_candidate(snap, cand, approve(snap, cand), tmp_path / "run", **kwargs)
    if rec.get("container_name"):
        CREATED.append(rec["container_name"])
    saved = json.loads(
        (tmp_path / "run" / "execution.json").read_text(encoding="utf-8")
    )
    assert saved["status"] == rec["status"]
    probe = tmp_path / "run" / "out" / "probe.json"
    return rec, (
        json.loads(probe.read_text(encoding="utf-8")) if probe.exists() else None
    )


@pytest.fixture
def no_execution(monkeypatch):
    """Fail loudly if anything would start a container or run code on the host."""
    calls = {"docker": [], "spawn": []}

    def spawn(*args, **kwargs):
        calls["spawn"].append(args)
        raise AssertionError("a container was started")

    real_docker = dr._docker

    def docker(cli, args, env, timeout=dr.CLI_TIMEOUT_S):
        calls["docker"].append(args[0])
        if args[0] in {"run", "create", "start", "exec"}:
            raise AssertionError("docker run/exec attempted")
        return real_docker(cli, args, env, timeout)

    def host(*args, **kwargs):
        raise AssertionError("host execution attempted")

    monkeypatch.setattr(dr, "_spawn", spawn)
    monkeypatch.setattr(dr, "_docker", docker)
    monkeypatch.setattr("atlas.runner.trusted.run_trusted_fixture", host)
    monkeypatch.setattr("atlas.runner.bootstrap.main", host)
    return calls


MARKER_SOURCE = """
from pathlib import Path
Path(r"{marker}").write_text("candidate executed")
"""


# ============================================================================================
# A. No host fallback and hash binding (no Docker needed)
# ============================================================================================


def test_missing_docker_cli_means_no_execution(tmp_path, no_execution):
    marker = tmp_path / "HOST_EXECUTED"
    env = {
        "PATH": "",
        "LOCALAPPDATA": str(tmp_path / "nowhere"),
        "ProgramFiles": str(tmp_path / "nowhere"),
    }
    rec, _ = run_source(tmp_path, MARKER_SOURCE.format(marker=marker), env=env)
    assert rec["status"] == "not_executed"
    assert rec["capability"] == dr.CAPABILITY_UNAVAILABLE
    assert "Docker CLI not found" in rec["reason"]
    assert no_execution == {"docker": [], "spawn": []}
    assert not marker.exists()
    assert not (tmp_path / "run" / "out").exists()
    assert not (tmp_path / "run" / "stage").exists()


def test_unreachable_daemon_means_no_execution(tmp_path, no_execution):
    marker = tmp_path / "HOST_EXECUTED"
    env = dict(os.environ, DOCKER_HOST="tcp://127.0.0.1:9", DOCKER_CONTEXT="")
    env.pop("DOCKER_CONTEXT")
    rec, _ = run_source(tmp_path, MARKER_SOURCE.format(marker=marker), env=env)
    assert rec["status"] == "not_executed"
    assert rec["capability"] == dr.CAPABILITY_UNAVAILABLE
    assert no_execution["spawn"] == []
    assert not marker.exists()


def test_missing_runner_image_means_no_execution(tmp_path, no_execution):
    marker = tmp_path / "HOST_EXECUTED"
    rec, _ = run_source(
        tmp_path, MARKER_SOURCE.format(marker=marker), image="atlas-runner:absent-t05"
    )
    assert rec["status"] == "not_executed"
    assert no_execution["spawn"] == []
    assert not marker.exists()


def test_image_from_another_recipe_means_no_execution(
    tmp_path, no_execution, monkeypatch
):
    monkeypatch.setattr(dr, "recipe_sha256", lambda: "0" * 64)
    rec, _ = run_source(tmp_path, "print('x')\n")
    assert rec["status"] == "not_executed"
    assert no_execution["spawn"] == []


def test_changed_candidate_bytes_are_refused_before_docker(tmp_path, no_execution):
    snap, cand = snapshot_and_candidate(tmp_path, "print('approved')\n")
    approval = approve(snap, cand)
    changed = type(cand)(cand.entry_point, cand.entry_bytes + b"print('extra')\n", "x")
    rec = dr.run_candidate(snap, changed, approval, tmp_path / "run")
    assert (rec["status"], rec["reason"]) == ("refused", "candidate_hash_mismatch")
    assert no_execution == {"docker": [], "spawn": []}


def test_changed_snapshot_is_refused_before_docker(tmp_path, no_execution):
    snap, cand = snapshot_and_candidate(tmp_path, "print('approved')\n")
    approval = approve(snap, cand)
    table = snap.root / "table.csv"
    table.write_bytes(table.read_bytes() + b"\n")
    rec = dr.run_candidate(snap, cand, approval, tmp_path / "run")
    assert (rec["status"], rec["reason"]) == ("refused", "base_snapshot_changed")
    assert no_execution == {"docker": [], "spawn": []}


def test_extra_file_in_snapshot_is_refused_before_docker(tmp_path, no_execution):
    snap, cand = snapshot_and_candidate(tmp_path, "print('approved')\n")
    approval = approve(snap, cand)
    (snap.root / "labels.csv").write_text("row_id,label\n", encoding="utf-8")
    rec = dr.run_candidate(snap, cand, approval, tmp_path / "run")
    assert rec["status"] == "refused" and rec["reason"].startswith("snapshot_invalid")
    assert no_execution == {"docker": [], "spawn": []}


def test_approval_for_another_snapshot_is_refused(tmp_path, no_execution):
    snap_a, cand_a = snapshot_and_candidate(tmp_path / "a", "print('a')\n")
    snap_b, cand_b = snapshot_and_candidate(tmp_path / "b", "print('a')\n", OTHER)
    rec = dr.run_candidate(snap_b, cand_b, approve(snap_a, cand_a), tmp_path / "run")
    assert (rec["status"], rec["reason"]) == ("refused", "approval_for_other_snapshot")
    assert no_execution == {"docker": [], "spawn": []}


@pytest.mark.parametrize(
    "target",
    [
        "../src/atlas/policy.py",
        "src/atlas/audit.py",
        "atlas_manifest.json",
        "table.csv",
        "labels/holdout.csv",
        "/etc/passwd",
    ],
)
def test_evaluator_label_and_escape_targets_are_refused(tmp_path, target):
    snap = build_snapshot(CLEAN, tmp_path / "snapshot")
    with pytest.raises(CandidateRejected):
        validate_diff(snap, make_diff("a\n", "b\n", target))


# ============================================================================================
# B. The real container (Docker required; sequential, in file order)
# ============================================================================================


@pytest.fixture(scope="module")
def isolation():
    cap = dr.probe()
    if cap.state != dr.CAPABILITY_AVAILABLE:
        message = f"isolated runner unavailable: {cap.reason}"
        if REQUIRE_DOCKER:
            pytest.fail(message)
        pytest.skip(message)
    return cap


RESTRICTIONS_PROBE = r"""
import importlib, json, os
def read(p):
    try:
        return open(p).read()
    except OSError as e:
        return "ERR %d" % e.errno
mounts = []
for line in read("/proc/self/mountinfo").splitlines():
    left, _, right = line.partition(" - ")
    f, r = left.split(), right.split()
    mounts.append({"point": f[4], "opts": f[5], "fstype": r[0], "super": r[2] if len(r) > 2 else ""})
keys = ("CapEff", "CapPrm", "CapBnd", "CapAmb", "CapInh", "NoNewPrivs", "Seccomp")
status = {k: v.strip() for k, _, v in (l.partition(":") for l in read("/proc/self/status").splitlines()) if k in keys}
imports = {}
for m in ("atlas.adapter", "atlas.recorder", "atlas.tables", "atlas.policy", "atlas.audit",
          "atlas.contracts", "atlas.intake", "atlas.checks", "atlas.candidates", "dotenv",
          "openai", "pydantic", "pyarrow"):
    try:
        importlib.import_module(m)
        imports[m] = True
    except ImportError:
        imports[m] = False
try:
    os.listdir("/proc/1/fd")
    proc1_fd = "readable"
except OSError as e:
    proc1_fd = "ERR %d" % e.errno
json.dump({
    "uid": os.getuid(), "gid": os.getgid(), "groups": os.getgroups(), "status": status,
    "mounts": mounts,
    "cgroup": {n: read("/sys/fs/cgroup/" + n).strip()
               for n in ("memory.max", "memory.swap.max", "pids.max", "cpu.max")},
    "docker_sock": [p for p in ("/var/run/docker.sock", "/run/docker.sock") if os.path.exists(p)],
    "dev_shm": os.path.exists("/dev/shm"),
    "opt_atlas": sorted(os.listdir("/opt/atlas")),
    "opt_atlas_pkg": sorted(os.listdir("/opt/atlas/atlas")),
    "project": sorted(os.listdir("/work/project")),
    "env": dict(os.environ),
    "proc1_environ": read("/proc/1/environ")[:10], "proc1_fd": proc1_fd,
    "net": sorted(os.listdir("/sys/class/net")),
    "imports": imports,
    "writable": {p: os.access(p, os.W_OK) for p in ("/etc/hosts", "/etc/hostname", "/etc/resolv.conf", "/dev", "/")},
}, open("/work/out/probe.json", "w"))
"""


@pytest.fixture(scope="module")
def restrictions(isolation, tmp_path_factory):
    rec, probe = run_source(tmp_path_factory.mktemp("restrictions"), RESTRICTIONS_PROBE)
    assert rec["status"] == "completed", rec
    assert rec["container_removed"] is True
    return rec, probe


@pytest.fixture(scope="module")
def verified_limits(restrictions):
    """Stress probes run only after the configured limits are read back from the cgroup."""
    _, probe = restrictions
    assert probe["cgroup"] == {
        "memory.max": str(1 << 30),
        "memory.swap.max": "0",
        "pids.max": "128",
        "cpu.max": "100000 100000",
    }
    return probe["cgroup"]


def test_approved_candidate_runs_isolated_and_matches_the_trusted_runner(
    isolation, tmp_path
):
    original = (CLEAN / "evaluate.py").read_text(encoding="utf-8")
    rec, _ = run_source(tmp_path, original + "# approved trivial change\n")
    assert rec["status"] == "completed", rec
    assert rec["capability"] == dr.CAPABILITY_AVAILABLE
    assert rec["docker"]["image_id"] == isolation.image_id
    assert rec["docker"]["docker_cli"] == isolation.docker_cli
    assert rec["container_removed"] is True
    assert rec["supervisor"]["nondumpable"] is True
    out = tmp_path / "run" / "out"
    assert sorted(f["path"] for f in rec["collection"]["files"]) == [
        "predictions/fold0.parquet",
        "predictions/fold1.parquet",
        "predictions/fold2.parquet",
        "predictions/fold3.parquet",
        "provenance.jsonl",
        "runtime.json",
        "splits.json",
    ]
    runtime = json.loads((out / "runtime.json").read_text(encoding="utf-8"))
    assert (runtime["uid"], runtime["isolated"], runtime["safe_path"]) == (
        10001,
        1,
        True,
    )
    assert runtime["atlas_origin"] == "/opt/atlas/atlas/__init__.py"
    # Same evidence as the trusted host runner on the unmodified fixture.
    host = tmp_path / "host"
    assert run_trusted_fixture(CLEAN, "evaluate.py", host)["returncode"] == 0
    for name in ("provenance.jsonl", "splits.json"):
        assert (out / name).read_bytes() == (host / name).read_bytes(), name
    for k in range(4):
        part = f"predictions/fold{k}.parquet"
        pd.testing.assert_frame_equal(
            pd.read_parquet(out / part), pd.read_parquet(host / part)
        )


def test_container_restrictions(restrictions, verified_limits):
    _, p = restrictions
    assert (p["uid"], p["gid"], p["groups"]) == (10001, 10001, [10001])
    for cap in ("CapEff", "CapPrm", "CapBnd", "CapAmb", "CapInh"):
        assert p["status"][cap] == "0000000000000000", cap
    assert (p["status"]["NoNewPrivs"], p["status"]["Seccomp"]) == ("1", "2")
    mounts = {m["point"]: m for m in p["mounts"]}
    for point in ("/", "/work/project", "/opt/atlas"):
        assert mounts[point]["opts"].split(",")[0] == "ro", point
    for point, size in (("/tmp", "size=65536k"), ("/work/out", "size=32768k")):
        m = mounts[point]
        assert m["fstype"] == "tmpfs" and size in m["super"].split(",")
        assert {"noexec", "nosuid", "nodev"} <= set(m["opts"].split(","))
    system = ("/proc", "/sys", "/dev")
    writable = {
        m["point"]
        for m in p["mounts"]
        if m["opts"].split(",")[0] == "rw" and not m["point"].startswith(system)
    }
    assert writable == {"/tmp", "/work/out"}
    assert not any(p["writable"].values()), p["writable"]
    assert p["docker_sock"] == [] and p["dev_shm"] is False
    assert p["opt_atlas"] == ["atlas", "atlas_runner_entry.py"]
    assert p["opt_atlas_pkg"] == sorted(dr.MOUNTED_MODULES)
    assert p["project"] == ["atlas_manifest.json", "evaluate.py", "table.csv"]
    assert p["imports"] == {
        "atlas.adapter": True,
        "atlas.recorder": True,
        "atlas.tables": True,
        "atlas.policy": False,
        "atlas.audit": False,
        "atlas.contracts": False,
        "atlas.intake": False,
        "atlas.checks": False,
        "atlas.candidates": False,
        "dotenv": False,
        "openai": False,
        "pydantic": False,
        "pyarrow": True,
    }
    # PID 1 is non-dumpable: the candidate cannot read its environment or descriptors.
    assert p["proc1_environ"] == f"ERR {EACCES}" and p["proc1_fd"] == f"ERR {EACCES}"


NETWORK_PROBE = r"""
import json, os, socket
res = {"net": sorted(os.listdir("/sys/class/net"))}
try:
    socket.create_connection(("1.1.1.1", 53), timeout=3).close()
    res["tcp"] = "connected"
except OSError as e:
    res["tcp"] = "%s %s" % (type(e).__name__, e.errno)
try:
    socket.getaddrinfo("example.com", 443)
    res["dns"] = "resolved"
except OSError as e:
    res["dns"] = type(e).__name__
json.dump(res, open("/work/out/probe.json", "w"))
"""


def test_no_network(isolation, tmp_path):
    rec, p = run_source(tmp_path, NETWORK_PROBE)
    assert rec["status"] == "completed" and rec["container_removed"]
    assert p["net"] == ["lo"]
    assert p["tcp"] != "connected" and p["dns"] != "resolved"


SECRETS_PROBE = r"""
import json, os
found = []
for top in ("/work", "/opt", "/tmp", "/etc", "/home", "/root", "/run"):
    for dirpath, dirnames, filenames in os.walk(top):
        found += [os.path.join(dirpath, n) for n in filenames if n.startswith(".env")]
json.dump({"env": dict(os.environ), "dotenv_files": found}, open("/work/out/probe.json", "w"))
"""


def test_no_host_environment_or_secrets(isolation, tmp_path):
    canaries = {
        "NEBIUS_API_KEY": "canary-secret-7f3a91",
        "ATLAS_TEST_PLAIN_CANARY": "canary-plain-c41d08",
    }
    rec, p = run_source(tmp_path, SECRETS_PROBE, env=dict(os.environ, **canaries))
    assert rec["status"] == "completed" and rec["container_removed"]
    assert set(p["env"]) <= set(CHILD_ENV) | SKLEARN_SET_ENV, sorted(p["env"])
    assert p["dotenv_files"] == []
    everything = json.dumps(p) + json.dumps(rec)
    for value in canaries.values():
        assert value not in everything


WRITES_PROBE = r"""
import json
targets = {
    "root": ("/probe.txt", "w"),
    "usr_lib": ("/usr/local/lib/python3.11/probe.txt", "w"),
    "adapter": ("/opt/atlas/atlas/adapter.py", "a"),
    "new_code": ("/opt/atlas/atlas/policy.py", "w"),
    "entry": ("/work/project/evaluate.py", "a"),
    "table": ("/work/project/table.csv", "a"),
    "manifest": ("/work/project/atlas_manifest.json", "a"),
    "new_label_file": ("/work/project/labels.csv", "w"),
    "etc_passwd": ("/etc/passwd", "a"),
}
res = {}
for key, (path, mode) in targets.items():
    try:
        with open(path, mode) as f:
            f.write("x")
        res[key] = "written"
    except OSError as e:
        res[key] = e.errno
with open("/tmp/scratch.txt", "w") as f:
    f.write("ok")
res["tmp"] = open("/tmp/scratch.txt").read()
json.dump(res, open("/work/out/probe.json", "w"))
"""


def test_read_only_filesystem_and_protected_paths(isolation, tmp_path):
    rec, p = run_source(tmp_path, WRITES_PROBE)
    assert rec["status"] == "completed" and rec["container_removed"]
    assert p.pop("tmp") == "ok"
    # EROFS, not merely EACCES: the read-only mounts refuse the write, independently of file
    # permissions (without --read-only the root-filesystem writes fail with EACCES instead).
    assert p.pop("etc_passwd") in (EROFS, EACCES)
    assert set(p.values()) == {EROFS}, p


CAPS_PROBE = r"""
import json, os
def fill(path, limit):
    written, err = 0, None
    try:
        with open(path, "wb") as f:
            chunk = b"\0" * (1 << 20)
            while written < limit:
                f.write(chunk)
                f.flush()
                written += len(chunk)
    except OSError as e:
        err = e.errno
    size = os.path.getsize(path)
    os.remove(path)
    return {"bytes": size, "errno": err}
json.dump({"tmp": fill("/tmp/fill", 100 << 20), "out": fill("/work/out/fill", 50 << 20)},
          open("/work/out/probe.json", "w"))
"""


def test_scratch_and_output_size_caps(isolation, tmp_path):
    rec, p = run_source(tmp_path, CAPS_PROBE)
    assert rec["status"] == "completed" and rec["container_removed"]
    assert p["tmp"]["errno"] == ENOSPC and p["tmp"]["bytes"] <= 64 << 20
    assert p["out"]["errno"] == ENOSPC and p["out"]["bytes"] <= 32 << 20


MEMORY_PROBE = r"""
held = []
for step in range(1, 33):  # at most 2 GiB in 64 MiB steps, each page written
    held.append(b"\x01" * (64 << 20))
    with open("/work/out/progress", "w") as f:
        f.write(str(step))
"""


def test_memory_limit_triggers(verified_limits, tmp_path):
    rec, _ = run_source(tmp_path, MEMORY_PROBE)
    assert rec["container_removed"] is True
    sup = rec["supervisor"]
    assert rec["status"] == "failed" and sup["child_returncode"] == -9
    assert sup["cgroup"]["memory_events"]["oom_kill"] >= 1
    steps = int((tmp_path / "run" / "out" / "progress").read_text())
    assert 1 <= steps < 16  # stopped below 1 GiB of probe allocations


PIDS_PROBE = r"""
import json, os, signal, time
pids, err = [], None
for _ in range(200):  # bounded: stops at the first refusal
    try:
        pid = os.fork()
    except OSError as e:
        err = e.errno
        break
    if pid == 0:
        time.sleep(60)
        os._exit(0)
    pids.append(pid)
for pid in pids:
    os.kill(pid, signal.SIGKILL)
for pid in pids:
    os.waitpid(pid, 0)
json.dump({"started": len(pids), "errno": err}, open("/work/out/probe.json", "w"))
"""


def test_pid_limit_triggers(verified_limits, tmp_path):
    rec, p = run_source(tmp_path, PIDS_PROBE)
    assert rec["status"] == "completed" and rec["container_removed"]
    assert p["errno"] == EAGAIN
    assert 64 <= p["started"] < 128
    assert rec["supervisor"]["cgroup"]["pids_events"]["max"] >= 1


SLEEP_PROBE = "import time\ntime.sleep(120)\n"


def test_execution_timeout_inside_the_container(isolation, tmp_path):
    limits = dr.Limits(exec_timeout_s=3)
    rec, _ = run_source(tmp_path, SLEEP_PROBE, limits=limits)
    assert rec["status"] == "timed_out" and rec["container_removed"]
    assert rec["supervisor"]["timed_out"] is True
    assert rec["supervisor"]["child_elapsed_s"] < 6
    assert (
        rec["collection"]["status"] == "ok"
    )  # outputs written before the kill survive


def test_host_deadline_kills_and_removes_the_container(isolation, tmp_path):
    limits = dr.Limits(exec_timeout_s=60, host_deadline_s=8)
    rec, _ = run_source(tmp_path, SLEEP_PROBE, limits=limits)
    assert rec["status"] == "timed_out" and rec["host_timed_out"] is True
    assert rec["container_removed"] is True
    assert rec["collection"]["problem"] == "host_deadline_exceeded"
    assert rec["elapsed_s"] < 8 + 20
    assert not (tmp_path / "run" / "out").exists()


COUNT_PROBE = r"""
for i in range(300):
    with open("/work/out/f%03d.txt" % i, "w") as f:
        f.write("x")
"""


def test_output_file_count_cap(isolation, tmp_path):
    rec, _ = run_source(tmp_path, COUNT_PROBE)
    assert rec["status"] == "collection_failed" and rec["container_removed"]
    assert rec["reason"] == "file_count_exceeded"
    assert not (tmp_path / "run" / "out").exists()


UNSAFE_OUTPUT_PROBE = r"""
import os
os.symlink("/etc/passwd", "/work/out/link")
os.mkfifo("/work/out/fifo")
os.makedirs("/work/out/sub")
os.symlink("/etc", "/work/out/sub/dirlink")
with open("/work/out/ok.txt", "w") as f:
    f.write("ok")
"""


def test_unsafe_output_entries_are_not_collected(isolation, tmp_path):
    rec, _ = run_source(tmp_path, UNSAFE_OUTPUT_PROBE)
    assert rec["status"] == "completed" and rec["container_removed"]
    paths = {f["path"] for f in rec["collection"]["files"]}
    assert "ok.txt" in paths
    assert not {"link", "fifo", "sub/dirlink"} & paths
    skipped = {(s["path"], s["type"]) for s in rec["supervisor"]["skipped"]}
    assert {
        ("link", "symlink"),
        ("fifo", "fifo"),
        ("sub/dirlink", "symlink"),
    } <= skipped
    out = tmp_path / "run" / "out"
    assert not (out / "link").exists() and not (out / "fifo").exists()


NOISY_PROBE = r"""
import sys
sys.stdout.write("x" * 1_000_000)
sys.stdout.flush()
try:
    open("/proc/1/fd/1", "wb").write(b"forged frame")
    print("WROTE TO PID 1")
except OSError as e:
    print("pid1 stdout refused", e.errno)
raise SystemExit(3)
"""


def test_candidate_output_is_bounded_and_cannot_reach_the_frame(isolation, tmp_path):
    rec, _ = run_source(tmp_path, NOISY_PROBE)
    assert rec["status"] == "failed" and rec["container_removed"]
    sup = rec["supervisor"]
    assert sup["child_returncode"] == 3
    assert sup["candidate_output_bytes"] >= 1_000_000
    assert len(sup["candidate_output_tail"].encode()) <= TAIL_BYTES
    assert f"pid1 stdout refused {EACCES}" in sup["candidate_output_tail"]
    assert rec["collection"]["status"] == "ok"


def test_zz_no_runner_containers_left_behind(isolation):
    cli = Path(isolation.docker_cli)
    env = dr.cli_env(cli)
    listed = subprocess.run(
        [
            str(cli),
            "ps",
            "--all",
            "--quiet",
            "--filter",
            f"label={dr.TASK_LABEL}={dr.TASK_LABEL_VALUE}",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    if listed:  # remove only containers this session created, then fail
        for name in CREATED:
            subprocess.run(
                [str(cli), "rm", "--force", name],
                env=env,
                capture_output=True,
                check=False,
            )
    assert listed == []
    assert CREATED, "no container was created by this module"
