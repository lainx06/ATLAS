"""Docker runner lifecycle on the host: cleanup confirmation, failure records and bounded
snapshot revalidation. Offline: Docker, the container process and its output are fakes, so
no container is created and no candidate code runs (regressions from the Codex review of
f494c95, findings 1-3)."""

import hashlib
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

from atlas import candidates
from atlas.candidates import Candidate, approve, build_snapshot
from atlas.runner import docker as dr

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "benchmarks" / "t01" / "s02_clean"
NAME = "atlas-t05-unit"


def completed(args, code=0, out=b"", err=b""):
    return subprocess.CompletedProcess(args, code, out, err)


def unreachable(cli, args, env, timeout=dr.CLI_TIMEOUT_S):
    return completed(args, 1, err=b"failed to connect to the docker API")


def gone(cli, args, env, timeout=dr.CLI_TIMEOUT_S):
    """A reachable daemon on which the container no longer exists."""
    if args[0] == "ps":
        return completed(args, 0, b"atlas-t05-someone-else\n")
    if args[0] == "rm":
        return completed(args, 0)
    return completed(args, 1, err=b"Error response from daemon: No such container")


def still_there(cli, args, env, timeout=dr.CLI_TIMEOUT_S):
    """A reachable daemon that keeps listing the container after removal."""
    name = next(
        (a.split("=", 1)[1] for a in args if a.startswith("name=")),
        args[-1],
    )
    if args[0] == "ps":
        return completed(args, 0, name.encode() + b"\n")
    if args[0] == "rm":
        return completed(args, 1, err=b"removal of container is already in progress")
    if "{{json .State}}" in args:
        return completed(args, 0, b'{"Running": true}')
    return completed(args, 0, b"sha256:still-there")


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(dr.time, "sleep", lambda s: None)


# --- cleanup confirmation (finding 1) --------------------------------------------------------


def test_daemon_failure_does_not_confirm_removal(monkeypatch):
    """Codex's reproduction: every Docker call fails to reach the daemon."""
    monkeypatch.setattr(dr, "_docker", unreachable)
    result = dr._remove_container(Path("docker.exe"), {}, NAME)
    assert result["removed"] is False
    assert result["cleanup"] == "unknown"


def test_cli_launch_failure_does_not_confirm_removal(monkeypatch):
    def broken(cli, args, env, timeout=dr.CLI_TIMEOUT_S):
        raise OSError("docker.exe vanished")

    monkeypatch.setattr(dr, "_docker", broken)
    result = dr._remove_container(Path("docker.exe"), {}, NAME)
    assert (result["removed"], result["cleanup"]) == (False, "unknown")


def test_absence_is_confirmed_by_a_successful_listing(monkeypatch):
    monkeypatch.setattr(dr, "_docker", gone)
    result = dr._remove_container(Path("docker.exe"), {}, NAME)
    assert (result["removed"], result["cleanup"]) == (True, "confirmed_absent")


def test_container_still_listed_is_not_removed(monkeypatch):
    monkeypatch.setattr(dr, "_docker", still_there)
    result = dr._remove_container(Path("docker.exe"), {}, NAME)
    assert (result["removed"], result["cleanup"]) == (False, "still_present")
    assert result["state"] == {"Running": True}


# --- lifecycle with fake Docker and process --------------------------------------------------


class FakeProcess:
    returncode = 0

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0

    def kill(self):
        raise AssertionError("already exited")


def empty_archive_frame(**header) -> bytes:
    archive = b"\0" * (2 * tarfile.BLOCKSIZE)
    head = {
        "version": 1,
        "archive_bytes": len(archive),
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "child_returncode": 0,
        **header,
    }
    return dr.FRAME_MAGIC + json.dumps(head).encode() + b"\n" + archive


def fake_run(monkeypatch, tmp_path, stdout: bytes, docker=gone, communicate=None):
    """run_candidate with a fake probe, process, output and Docker CLI; returns the
    returned record, the saved execution.json and the Docker calls made."""
    snap = build_snapshot(CLEAN, tmp_path / "snapshot")
    cand = Candidate(snap.entry_point, b'print("not executed")\n', "unit")
    cap = dr.Capability(
        dr.CAPABILITY_AVAILABLE, None, docker_cli="docker.exe", image_id="sha256:unit"
    )
    calls = []

    def spy(cli, args, env, timeout=dr.CLI_TIMEOUT_S):
        calls.append(args)
        return docker(cli, args, env, timeout)

    def bounded(proc, limits):
        return {
            "stdout": bytearray(stdout),
            "stderr_tail": bytearray(),
            "counts": {"stdout": len(stdout), "stderr": 0},
            "problems": [],
            "host_timed_out": False,
            "threads": [],
        }

    monkeypatch.setattr(dr, "probe", lambda *a, **k: cap)
    monkeypatch.setattr(dr, "_spawn", lambda *a, **k: FakeProcess())
    monkeypatch.setattr(dr, "communicate_bounded", communicate or bounded)
    monkeypatch.setattr(dr, "_docker", spy)
    run_dir = tmp_path / "run"
    try:
        rec = dr.run_candidate(snap, cand, approve(snap, cand), run_dir)
    finally:
        saved = json.loads((run_dir / "execution.json").read_text(encoding="utf-8"))
    return rec, saved, calls


def test_confirmed_cleanup_allows_completion(monkeypatch, tmp_path):
    rec, saved, _ = fake_run(monkeypatch, tmp_path, empty_archive_frame())
    assert rec["status"] == saved["status"] == "completed"
    assert rec["container_removed"] is True


@pytest.mark.parametrize(
    ("docker", "cleanup"),
    [(unreachable, "unknown"), (still_there, "still_present")],
    ids=["daemon_unreachable", "still_present"],
)
def test_unconfirmed_cleanup_prevents_completion(
    monkeypatch, tmp_path, docker, cleanup
):
    """Codex's reproduction: a clean run whose container removal was not confirmed."""
    rec, saved, _ = fake_run(monkeypatch, tmp_path, empty_archive_frame(), docker)
    assert rec["status"] == saved["status"] == "cleanup_failed"
    assert rec["execution_status"] == "completed"
    assert rec["container_removed"] is False
    assert rec["cleanup"]["status"] == cleanup


def test_unconfirmed_cleanup_after_launch_failure_is_explicit(monkeypatch, tmp_path):
    def cannot_start(*args, **kwargs):
        raise OSError("injected launch failure")

    monkeypatch.setattr(dr, "_spawn", cannot_start)
    snap = build_snapshot(CLEAN, tmp_path / "snapshot")
    cand = Candidate(snap.entry_point, b'print("not executed")\n', "unit")
    cap = dr.Capability(
        dr.CAPABILITY_AVAILABLE, None, docker_cli="docker.exe", image_id="sha256:unit"
    )
    monkeypatch.setattr(dr, "probe", lambda *a, **k: cap)
    monkeypatch.setattr(dr, "_docker", unreachable)
    rec = dr.run_candidate(snap, cand, approve(snap, cand), tmp_path / "run")
    assert (rec["status"], rec["execution_status"]) == (
        "cleanup_failed",
        "not_executed",
    )
    assert rec["container_removed"] is False and rec["cleanup"]["status"] == "unknown"


def test_nested_header_is_a_recorded_collection_failure(monkeypatch, tmp_path):
    """Codex's reproduction: RecursionError escaped and execution.json kept status null."""
    header = b'{"nested":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}"
    rec, saved, calls = fake_run(monkeypatch, tmp_path, dr.FRAME_MAGIC + header + b"\n")
    assert rec["status"] == saved["status"] == "collection_failed"
    assert saved["collection"]["problem"] == "malformed_header"
    assert ["rm", "--force", saved["container_name"]] in calls
    assert saved["container_removed"] is True


def test_chained_pax_archive_is_a_recorded_collection_failure(monkeypatch, tmp_path):
    pax = tarfile.TarInfo("pax")
    pax.type, pax.size = tarfile.XHDTYPE, 10
    record = pax.tobuf(format=tarfile.USTAR_FORMAT) + b"10 path=x\n" + b"\0" * 502
    member = tarfile.TarInfo("file.txt")
    member.size = 1
    archive = (
        record * 600
        + member.tobuf(format=tarfile.USTAR_FORMAT)
        + b"x"
        + b"\0" * 511
        + b"\0" * 1024
    )
    head = {
        "version": 1,
        "archive_bytes": len(archive),
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "child_returncode": 0,
    }
    stdout = dr.FRAME_MAGIC + json.dumps(head).encode() + b"\n" + archive
    rec, saved, _ = fake_run(monkeypatch, tmp_path, stdout)
    assert rec["status"] == saved["status"] == "collection_failed"
    assert saved["collection"]["problem"] == "malformed_archive"
    assert not (tmp_path / "run" / "out").exists()


def test_unexpected_collection_error_is_recorded(monkeypatch, tmp_path):
    def broken(*args, **kwargs):
        raise RuntimeError("injected parser defect")

    monkeypatch.setattr(dr, "extract_archive", broken)
    rec, saved, calls = fake_run(monkeypatch, tmp_path, empty_archive_frame())
    assert rec["status"] == saved["status"] == "collection_failed"
    assert saved["collection"]["problem"] == "unexpected_error"
    assert "RuntimeError" in saved["collection"]["detail"]
    assert ["rm", "--force", saved["container_name"]] in calls


def test_lifecycle_error_still_cleans_up_and_saves_a_final_status(
    monkeypatch, tmp_path
):
    def broken(proc, limits):
        raise RuntimeError("injected IO defect")

    with pytest.raises(RuntimeError):
        fake_run(monkeypatch, tmp_path, b"", communicate=broken)
    saved = json.loads((tmp_path / "run" / "execution.json").read_text("utf-8"))
    assert saved["status"] == "runner_error"
    assert "RuntimeError" in saved["reason"]
    assert saved["container_removed"] is True
    assert saved["cleanup"]["status"] == "confirmed_absent"


# --- bounded revalidation (finding 2) -------------------------------------------------------


def no_docker(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Docker was reached")

    monkeypatch.setattr(dr, "probe", refuse)
    monkeypatch.setattr(dr, "_docker", refuse)
    monkeypatch.setattr(dr, "_spawn", refuse)


def test_revalidation_hashes_with_bounded_reads(monkeypatch, tmp_path):
    snap = build_snapshot(CLEAN, tmp_path / "snapshot")
    cand = Candidate(snap.entry_point, b'print("not executed")\n', "unit")
    approval = approve(snap, cand)
    table = snap.root / snap.table_path
    limit = table.stat().st_size
    monkeypatch.setattr(candidates, "MAX_TABLE_BYTES", limit)
    with open(table, "ab") as f:
        f.write(b"x" * (1 << 20))
    sizes = []
    real_read_bytes = Path.read_bytes
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda p: sizes.append(len(data := real_read_bytes(p))) or data,
    )
    no_docker(monkeypatch)
    rec = dr.run_candidate(snap, cand, approval, tmp_path / "run")
    assert rec["status"] == "refused"
    assert rec["reason"].startswith("snapshot_invalid") and "exceeds" in rec["reason"]
    assert all(size <= limit + 1 for size in sizes)


def test_revalidation_stops_at_the_first_unexpected_entry(monkeypatch, tmp_path):
    snap = build_snapshot(CLEAN, tmp_path / "snapshot")
    cand = Candidate(snap.entry_point, b'print("not executed")\n', "unit")
    approval = approve(snap, cand)
    for i in range(200):
        (snap.root / f"extra{i:03d}.txt").write_bytes(b"x")
    lstats = []
    real_lstat = os.lstat
    monkeypatch.setattr(
        os, "lstat", lambda p, *a, **k: lstats.append(p) or real_lstat(p, *a, **k)
    )
    no_docker(monkeypatch)
    rec = dr.run_candidate(snap, cand, approval, tmp_path / "run")
    assert rec["status"] == "refused" and rec["reason"].startswith("snapshot_invalid")
    assert len(lstats) <= 20
