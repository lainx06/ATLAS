"""T-06 slice 1, offline: approved candidate -> Docker runner -> candidate view -> trusted
re-evaluation, with fake Docker and a fake container process.

The runner's own host code (hash binding, staging, frame and archive parsing, cleanup records)
runs for real; only the Docker CLI, the container process and its output frame are fakes. The
evidence in the frame is real adapter evidence, produced by the trusted host runner on the
repo-authored, allowlisted T-01 fixtures. No candidate code runs anywhere in this file.

Negative tests change one thing in a view that otherwise passes (the positive control), so
each failure is attributable to that change, not to Docker evidence being refused wholesale.
"""

import hashlib
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from atlas import docker_evidence as de
from atlas.agent.execute import execute_and_reevaluate
from atlas.agent.report import MIXED_BASIS, comparison_report
from atlas.audit import DOCKER_LIMITATIONS, audit, evaluate
from atlas.candidates import Candidate, approve, build_snapshot, validate_diff
from atlas.contracts import Outcome, Reason, Status
from atlas.runner import docker as dr
from atlas.runner import trusted

ROOT = Path(__file__).resolve().parents[2]
S01 = ROOT / "benchmarks" / "t01" / "s01_faulty"
S02 = ROOT / "benchmarks" / "t01" / "s02_clean"
FAKE_IMAGE = "sha256:" + "ab" * 32
CONTAINER_RUNTIME = {
    "python": "3.11.17",
    "isolated": 1,
    "safe_path": True,
    "uid": 10001,
    "gid": 10001,
    "cwd": "/work/project",
    "sys_path": ["/usr/local/lib/python311.zip", "/opt/atlas"],
    "atlas_origin": "/opt/atlas/atlas/__init__.py",
    "atlas_modules": [
        "__init__.py",
        "adapter.py",
        "recorder.py",
        "reports.py",
        "tables.py",
    ],
}
EVIDENCE_NAMES = ("provenance.jsonl", "splits.json")


def make_diff(old: str, new: str, path: str = "evaluate.py") -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}"
        )
    )


# --- real adapter evidence from the trusted host runner (allowlisted fixtures only) ----------


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    base = tmp_path_factory.mktemp("evidence")
    runs = {}
    for name, project in (("clean", S02), ("faulty", S01)):
        run = base / name
        run.mkdir()
        assert (
            trusted.run_trusted_fixture(project, "evaluate.py", run)["returncode"] == 0
        )
        runs[name] = run
    return runs


def collected(
    src: Path | None, dest: Path, *, extra=None, runtime=CONTAINER_RUNTIME
) -> Path:
    """What the container would emit: runtime.json plus (optionally) the adapter evidence."""
    dest.mkdir(parents=True)
    (dest / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
    if src is not None:
        for name in EVIDENCE_NAMES:
            shutil.copyfile(src / name, dest / name)
        shutil.copytree(src / "predictions", dest / "predictions")
    for rel, data in (extra or {}).items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_bytes(data)
    return dest


def frame(out_dir: Path, *, returncode=0, timed_out=False) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(p for p in out_dir.rglob("*") if p.is_file()):
            data = path.read_bytes()
            info = tarfile.TarInfo(path.relative_to(out_dir).as_posix())
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    archive = buf.getvalue()
    header = {
        "version": 1,
        "nondumpable": True,
        "child_returncode": returncode,
        "timed_out": timed_out,
        "archive_error": None,
        "archive_bytes": len(archive),
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
    }
    return dr.FRAME_MAGIC + json.dumps(header).encode() + b"\n" + archive


class FakeProcess:
    returncode = 0

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0

    def kill(self):
        raise AssertionError("already exited")


def gone(cli, args, env, timeout=dr.CLI_TIMEOUT_S):
    """A reachable daemon on which the container no longer exists (removal confirmed)."""
    if args[0] == "ps":
        return subprocess.CompletedProcess(args, 0, b"", b"")
    return subprocess.CompletedProcess(args, 0 if args[0] == "rm" else 1, b"", b"")


def fake_docker(monkeypatch, out_dir: Path | None, **frame_kwargs) -> dict:
    """Docker 'available' with the runner image; the container emits `out_dir` as its frame."""
    calls = {"spawn": 0}
    cap = dr.Capability(
        dr.CAPABILITY_AVAILABLE,
        None,
        docker_cli="docker.exe",
        image_id=FAKE_IMAGE,
        recipe_sha256=dr.recipe_sha256(),
    )

    def spawn(cli, args, env):
        calls["spawn"] += 1
        return FakeProcess()

    def bounded(proc, limits):
        stdout = frame(out_dir, **frame_kwargs)
        return {
            "stdout": bytearray(stdout),
            "stderr_tail": bytearray(),
            "counts": {"stdout": len(stdout), "stderr": 0},
            "problems": [],
            "host_timed_out": False,
            "threads": [],
        }

    monkeypatch.setattr(
        dr, "probe", lambda image=dr.IMAGE_TAG, env=None, exclude=(): cap
    )
    monkeypatch.setattr(dr, "_spawn", spawn)
    monkeypatch.setattr(dr, "communicate_bounded", bounded)
    monkeypatch.setattr(dr, "_docker", gone)
    monkeypatch.setattr(dr.time, "sleep", lambda s: None)
    return calls


def no_host_execution(monkeypatch):
    def host(*args, **kwargs):
        raise AssertionError("host execution attempted")

    monkeypatch.setattr(trusted, "run_trusted_fixture", host)
    monkeypatch.setattr("atlas.runner.bootstrap.main", host)


def prepared(tmp_path, new_source=None):
    """s01 snapshot; candidate = s02's fold-local entry point (or `new_source`); approval."""
    snap = build_snapshot(S01, tmp_path / "snapshot")
    old = (snap.root / snap.entry_point).read_text(encoding="utf-8")
    new = (
        new_source
        if new_source is not None
        else (S02 / "evaluate.py").read_text(encoding="utf-8")
    )
    cand = validate_diff(snap, make_diff(old, new))
    return snap, cand, approve(snap, cand)


def run_case(
    tmp_path,
    monkeypatch,
    evidence_dir,
    *,
    new_source=None,
    extra=None,
    runtime=CONTAINER_RUNTIME,
    **frame_kwargs,
):
    snap, cand, appr = prepared(tmp_path, new_source)
    out = collected(
        evidence_dir, tmp_path / "container-out", extra=extra, runtime=runtime
    )
    fake_docker(monkeypatch, out, **frame_kwargs)
    no_host_execution(monkeypatch)
    result = execute_and_reevaluate(snap, cand, appr, tmp_path / "agent" / "c1")
    return snap, result


def statuses(outcome):
    return {a.assertion_id: a.status for a in outcome.assertions}


def accept_image(image_id):
    return None if image_id == FAKE_IMAGE else "not the runner image"


def reevaluate(snap, cdir, verifier=accept_image):
    return evaluate(snap.root, cdir, image_verifier=verifier)


def reindex(cdir: Path, *names: str) -> None:
    index = json.loads((cdir / "index.json").read_text(encoding="utf-8"))
    for name in names:
        index["artifacts"][name] = hashlib.sha256(
            (cdir / name).read_bytes()
        ).hexdigest()
    (cdir / "index.json").write_text(json.dumps(index), encoding="utf-8")


def tamper_record(cdir: Path, change) -> None:
    """Coordinated tampering: the runner's record and its indexed copy change together."""
    record = json.loads((cdir / "execution.json").read_text(encoding="utf-8"))
    change(record)
    text = json.dumps(record)
    for path in (cdir / "execution.json", cdir / "exec" / "execution.json"):
        path.write_text(text, encoding="utf-8")
    reindex(cdir, "execution.json")


def assert_untrusted(outcome, fragment):
    assert outcome.outcome is not Outcome.NO_VIOLATION_FOUND
    assert outcome.outcome is not Outcome.VIOLATION_FOUND
    assert Status.PASS not in statuses(outcome).values()
    assert "not trusted" in outcome.reason and fragment in outcome.reason, (
        outcome.reason
    )


# --- the positive control --------------------------------------------------------------------


@pytest.fixture
def clean_view(tmp_path, monkeypatch, evidence):
    snap, result = run_case(tmp_path, monkeypatch, evidence["clean"])
    assert result.execution["status"] == "completed", result.execution
    assert result.evaluated
    assert result.outcome.outcome is Outcome.NO_VIOLATION_FOUND, result.outcome.reason
    # Re-evaluating the untouched view gives the same result (the control for every tamper).
    assert reevaluate(snap, result.candidate_dir).outcome is Outcome.NO_VIOLATION_FOUND
    return snap, result.candidate_dir


def test_completed_candidate_is_reevaluated_on_the_full_required_set(
    tmp_path, monkeypatch, evidence
):
    _snap, result = run_case(tmp_path, monkeypatch, evidence["clean"])
    original = audit(S01, tmp_path / "runs").outcome
    assert result.outcome.outcome is Outcome.NO_VIOLATION_FOUND
    assert [a.assertion_id for a in result.outcome.assertions] == [
        a.assertion_id for a in original.assertions
    ]
    report = json.loads(
        (result.candidate_dir / "report.json").read_text(encoding="utf-8")
    )
    assert report["limitations"][: len(DOCKER_LIMITATIONS)] == DOCKER_LIMITATIONS
    assert any("candidate-produced" in x for x in report["limitations"])
    assert not any("trusted_pipeline_only" in x for x in report["limitations"])
    view = json.loads((result.candidate_dir / "view.json").read_text(encoding="utf-8"))
    assert {m["to"] for m in view["mapped"]} >= {
        "runtime.json",
        "splits.json",
        "provenance.jsonl",
    }
    assert result.timing["active_s"] >= 0 and result.timing["total_elapsed_s"] is None


# --- integrity and binding: each a single change to the passing view -------------------------


def _limit_and_command(record):
    doubled = str(2 << 30)
    record["limits"]["memory_bytes"] = 2 << 30
    args = record["docker_args"]
    for flag in ("--memory", "--memory-swap"):
        args[args.index(flag) + 1] = doubled


def _without_network(record):
    args = record["docker_args"]
    i = args.index("--network")
    del args[i : i + 2]


def _foreign_name(record):
    old = record["container_name"]
    record["container_name"] = "someone-elses-container"
    record["docker_args"] = [
        a if a != old else "someone-elses-container" for a in record["docker_args"]
    ]


def _completed_but_failed(record):
    record["supervisor"]["child_returncode"] = 3


RECORD_TAMPERS = {
    "runner_renamed": (lambda r: r.update(runner="docker_elsewhere"), "from runner"),
    "capability_not_isolated": (
        lambda r: r.update(capability="trusted_pipeline_only"),
        "not isolated",
    ),
    "limit_and_command_changed_together": (_limit_and_command, "limits differ"),
    "network_flag_removed": (_without_network, "docker command differs"),
    "recipe_changed": (lambda r: r["docker"].update(recipe_sha256="0" * 64), "recipe"),
    "foreign_container_name": (_foreign_name, "container name"),
    "status_contradicts_details": (_completed_but_failed, "contradicts"),
    "fixture_record_in_view": (
        lambda r: (
            r.clear(),
            r.update(
                runner=trusted.RUNNER_NAME,
                capability=trusted.CAPABILITY,
                returncode=0,
                timed_out=False,
                elapsed_s=1.0,
                stderr_tail="",
            ),
        ),
        "schema validation",
    ),
}


@pytest.mark.parametrize("case", list(RECORD_TAMPERS))
def test_tampered_execution_record_is_not_trusted(clean_view, case):
    snap, cdir = clean_view
    change, fragment = RECORD_TAMPERS[case]
    tamper_record(cdir, change)
    assert_untrusted(reevaluate(snap, cdir), fragment)


def test_command_change_alone_is_refused_against_the_trusted_command(clean_view):
    """Limits untouched; only the recorded command differs from what the runner must run."""
    snap, cdir = clean_view

    def change(record):
        args = record["docker_args"]
        args[args.index("--pids-limit") + 1] = "100000"

    tamper_record(cdir, change)
    assert_untrusted(reevaluate(snap, cdir), "docker command differs")


def test_image_docker_does_not_confirm_is_refused(clean_view):
    snap, cdir = clean_view
    outcome = reevaluate(
        snap, cdir, verifier=lambda image_id: "runner image could not be verified: unit"
    )
    assert_untrusted(outcome, "could not be verified")


def test_approval_for_another_candidate_is_refused(clean_view):
    snap, cdir = clean_view
    other = "f" * 64

    def change(record):
        record["approval"]["candidate_hash"] = other
        record["candidate_hash"] = other

    approval = json.loads((cdir / "approval.json").read_text(encoding="utf-8"))
    approval["candidate_hash"] = other
    (cdir / "approval.json").write_text(json.dumps(approval), encoding="utf-8")
    reindex(cdir, "approval.json")
    tamper_record(cdir, change)
    assert_untrusted(reevaluate(snap, cdir), "not the approved candidate")


def test_approval_for_another_snapshot_is_refused(clean_view):
    snap, cdir = clean_view
    other = "e" * 64
    approval = json.loads((cdir / "approval.json").read_text(encoding="utf-8"))
    approval["base_snapshot_hash"] = other
    (cdir / "approval.json").write_text(json.dumps(approval), encoding="utf-8")
    reindex(cdir, "approval.json")

    def change(record):
        record["approval"]["base_snapshot_hash"] = other
        record["base_snapshot_hash"] = other

    tamper_record(cdir, change)
    assert_untrusted(reevaluate(snap, cdir), "not the approved snapshot")


def test_approval_record_not_matching_the_runner_is_refused(clean_view):
    snap, cdir = clean_view
    approval = json.loads((cdir / "approval.json").read_text(encoding="utf-8"))
    approval["approved_at"] = "2000-01-01T00:00:00+00:00"
    (cdir / "approval.json").write_text(json.dumps(approval), encoding="utf-8")
    reindex(cdir, "approval.json")
    assert_untrusted(reevaluate(snap, cdir), "different approval")


def test_snapshot_changed_after_execution_is_refused(clean_view):
    snap, cdir = clean_view
    table = snap.root / "table.csv"
    table.write_bytes(table.read_bytes() + b"\n")
    assert_untrusted(reevaluate(snap, cdir), "snapshot")


def test_staged_entry_point_changed_after_execution_is_refused(clean_view):
    snap, cdir = clean_view
    entry = cdir / "exec" / "stage" / "project" / "evaluate.py"
    entry.write_bytes(entry.read_bytes() + b"# changed\n")
    assert_untrusted(reevaluate(snap, cdir), "not the approved candidate")


def test_staged_code_changed_with_its_record_is_refused(clean_view):
    """The mounted recorder and the recorded hash change together; the evaluator compares
    both with its own copy of the trusted modules."""
    snap, cdir = clean_view
    recorder = cdir / "exec" / "stage" / "code" / "atlas" / "recorder.py"
    recorder.write_bytes(recorder.read_bytes() + b"# changed\n")
    new_hash = hashlib.sha256(recorder.read_bytes()).hexdigest()

    def change(record):
        record["mounted_code"] = [
            [p, new_hash if p == "atlas/recorder.py" else h]
            for p, h in record["mounted_code"]
        ]

    tamper_record(cdir, change)
    assert_untrusted(reevaluate(snap, cdir), "staged code differs")


def test_collected_file_changed_and_reindexed_is_refused(clean_view):
    snap, cdir = clean_view
    splits = json.loads((cdir / "splits.json").read_text(encoding="utf-8"))
    splits[0]["eval_ids"] = splits[0]["eval_ids"][:-1]
    (cdir / "splits.json").write_text(json.dumps(splits), encoding="utf-8")
    reindex(cdir, "splits.json")
    assert_untrusted(reevaluate(snap, cdir), "differ from the recorded collection")


def test_execution_copy_differing_from_the_runner_record_is_refused(clean_view):
    snap, cdir = clean_view
    record = json.loads((cdir / "execution.json").read_text(encoding="utf-8"))
    record["reason"] = "edited copy"
    (cdir / "execution.json").write_text(json.dumps(record), encoding="utf-8")
    reindex(cdir, "execution.json")
    assert_untrusted(reevaluate(snap, cdir), "differs from the runner's own record")


def test_view_marker_removed_falls_to_the_fixture_check_and_fails(clean_view):
    """Without view.json the run is checked as trusted-fixture evidence, which a Docker record
    cannot satisfy: cross-runner confusion fails closed."""
    snap, cdir = clean_view
    index = json.loads((cdir / "index.json").read_text(encoding="utf-8"))
    del index["artifacts"]["view.json"]
    (cdir / "index.json").write_text(json.dumps(index), encoding="utf-8")
    outcome = reevaluate(snap, cdir)
    assert outcome.outcome is not Outcome.NO_VIOLATION_FOUND
    assert Status.PASS not in statuses(outcome).values()
    assert "schema validation" in outcome.reason


def test_untrusted_evidence_does_not_support_a_violation_either(
    tmp_path, monkeypatch, evidence
):
    """Evidence that cannot be attributed to the approved candidate supports no FAIL."""
    source = (S01 / "evaluate.py").read_text(encoding="utf-8") + "# approved comment\n"
    snap, result = run_case(
        tmp_path, monkeypatch, evidence["faulty"], new_source=source
    )
    assert result.outcome.outcome is Outcome.VIOLATION_FOUND
    tamper_record(result.candidate_dir, _without_network)
    outcome = reevaluate(snap, result.candidate_dir)
    assert outcome.outcome is Outcome.INCONCLUSIVE
    assert not {Status.PASS, Status.FAIL} & set(statuses(outcome).values())


# --- status mapping after a trusted record ---------------------------------------------------


def test_cleanup_unconfirmed_establishes_no_pass(clean_view):
    snap, cdir = clean_view

    def change(record):
        record.update(
            execution_status="completed",
            execution_reason=None,
            status="cleanup_failed",
            reason="container removal unconfirmed (unknown)",
            container_removed=False,
        )
        record["cleanup"]["status"] = "unknown"

    tamper_record(cdir, change)
    outcome = reevaluate(snap, cdir)
    assert outcome.outcome is Outcome.INCONCLUSIVE
    assert Status.PASS not in statuses(outcome).values()
    assert "not confirmed (cleanup_failed" in outcome.reason


def test_inconsistent_container_runtime_establishes_no_pass(
    tmp_path, monkeypatch, evidence
):
    _snap, result = run_case(
        tmp_path,
        monkeypatch,
        evidence["clean"],
        runtime={**CONTAINER_RUNTIME, "uid": 0},
    )
    assert result.execution["status"] == "completed"
    assert result.outcome.outcome is Outcome.INCONCLUSIVE
    assert Status.PASS not in statuses(result.outcome).values()
    assert "runtime record is inconsistent" in result.outcome.reason


def test_failure_before_evidence_is_inconclusive_and_missing_evidence_stays_error(
    tmp_path, monkeypatch
):
    source = 'raise SystemExit("stopped before any evidence")\n' + (
        S01 / "evaluate.py"
    ).read_text(encoding="utf-8")
    _snap, result = run_case(
        tmp_path, monkeypatch, None, new_source=source, returncode=1
    )
    assert result.execution["status"] == "failed"
    out = result.outcome
    assert out.outcome is Outcome.INCONCLUSIVE
    assert not {Status.PASS, Status.FAIL} & set(statuses(out).values())
    errors = [a for a in out.assertions if a.status is Status.ERROR]
    assert errors and all(a.reason is Reason.EVIDENCE_INVALID for a in errors)
    assert "did not complete (failed" in out.reason


def test_failure_after_evidence_keeps_the_supported_violation(
    tmp_path, monkeypatch, evidence
):
    source = (S01 / "evaluate.py").read_text(
        encoding="utf-8"
    ) + 'raise SystemExit("late failure")\n'
    _snap, result = run_case(
        tmp_path, monkeypatch, evidence["faulty"], new_source=source, returncode=3
    )
    assert result.execution["status"] == "failed"
    assert result.outcome.outcome is Outcome.VIOLATION_FOUND
    passed = [a for a in result.outcome.assertions if a.status is Status.PASS]
    assert not passed  # what passed is unconfirmed: NOT_ASSESSED (not_executed)
    assert any(
        a.status is Status.NOT_ASSESSED and a.reason is Reason.NOT_EXECUTED
        for a in result.outcome.assertions
    )


def test_timeout_is_a_verified_non_completion(tmp_path, monkeypatch, evidence):
    _snap, result = run_case(
        tmp_path, monkeypatch, evidence["clean"], returncode=-9, timed_out=True
    )
    assert result.execution["status"] == "timed_out"
    assert result.outcome.outcome is Outcome.INCONCLUSIVE
    assert Status.PASS not in statuses(result.outcome).values()


# --- the explicit mapping and host-owned names -----------------------------------------------


def test_collected_files_never_replace_host_records(tmp_path, monkeypatch, evidence):
    forged = b'{"runner": "docker_isolated", "status": "completed", "forged": true}'
    _snap, result = run_case(
        tmp_path,
        monkeypatch,
        evidence["clean"],
        extra={"execution.json": forged, "INDEX.json": b"{}", "approval.json": b"{}"},
    )
    cdir = result.candidate_dir
    assert (cdir / "execution.json").read_bytes() == (
        cdir / "exec" / "execution.json"
    ).read_bytes()
    assert b"forged" not in (cdir / "execution.json").read_bytes()
    view = json.loads((cdir / "view.json").read_text(encoding="utf-8"))
    assert sorted(view["collisions"]) == [
        "INDEX.json",
        "approval.json",
        "execution.json",
    ]
    assert_untrusted(result.outcome, "collides with host-owned names")


def test_unmapped_outputs_are_listed_and_ignored(tmp_path, monkeypatch, evidence):
    _snap, result = run_case(
        tmp_path,
        monkeypatch,
        evidence["clean"],
        extra={"notes.txt": b"hello", "deep/x.parquet": b"x"},
    )
    view = json.loads((result.candidate_dir / "view.json").read_text(encoding="utf-8"))
    assert sorted(view["unmapped"]) == ["deep/x.parquet", "notes.txt"]
    assert not (result.candidate_dir / "notes.txt").exists()
    assert result.outcome.outcome is Outcome.NO_VIOLATION_FOUND


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        ("splits.json", "mapped"),
        ("predictions/fold0.parquet", "mapped"),
        ("Execution.json", "collision"),
        ("checks/split_integrity.json", "collision"),
        ("exec/execution.json", "collision"),
        ("outcome.json", "collision"),
        ("predictions/a/b.parquet", "unmapped"),
        ("Splits.json", "unmapped"),
        ("notes.txt", "unmapped"),
    ],
)
def test_mapping_rules(path, kind):
    assert de.map_collected(path)[0] == kind


# --- approval binding and no host fallback ---------------------------------------------------


def _refusing_docker(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("Docker was used")

    monkeypatch.setattr(dr, "probe", refuse)
    monkeypatch.setattr(dr, "_spawn", refuse)
    monkeypatch.setattr(dr, "_docker", refuse)
    no_host_execution(monkeypatch)


def _not_executed(result, reason_fragment):
    assert not result.evaluated
    assert reason_fragment in (result.execution["reason"] or "")
    assert result.outcome.outcome is Outcome.INCONCLUSIVE
    assert result.outcome.assertions and all(
        a.status is Status.NOT_ASSESSED and a.reason is Reason.NOT_EXECUTED
        for a in result.outcome.assertions
    )


def test_changed_candidate_bytes_need_fresh_approval(tmp_path, monkeypatch):
    snap, cand, appr = prepared(tmp_path)
    changed = Candidate(
        cand.entry_point, cand.entry_bytes + b"# after approval\n", cand.diff_sha256
    )
    _refusing_docker(monkeypatch)
    result = execute_and_reevaluate(snap, changed, appr, tmp_path / "c1")
    assert result.execution["status"] == "refused"
    _not_executed(result, "candidate_hash_mismatch")


def test_snapshot_changed_after_approval_is_refused(tmp_path, monkeypatch):
    snap, cand, appr = prepared(tmp_path)
    table = snap.root / "table.csv"
    table.write_bytes(table.read_bytes() + b"\n")
    _refusing_docker(monkeypatch)
    result = execute_and_reevaluate(snap, cand, appr, tmp_path / "c1")
    _not_executed(result, "base_snapshot_changed")


def test_approval_for_another_snapshot_never_runs(tmp_path, monkeypatch):
    snap, cand, _ = prepared(tmp_path)
    other_snap = build_snapshot(S02, tmp_path / "other")
    other = approve(
        other_snap, Candidate(cand.entry_point, cand.entry_bytes, cand.diff_sha256)
    )
    _refusing_docker(monkeypatch)
    result = execute_and_reevaluate(snap, cand, other, tmp_path / "c1")
    _not_executed(result, "approval_for_other_snapshot")


def test_unavailable_isolation_means_not_executed_and_no_host_run(
    tmp_path, monkeypatch
):
    snap, cand, appr = prepared(tmp_path)
    no_host_execution(monkeypatch)
    spawned = []
    monkeypatch.setattr(
        dr,
        "probe",
        lambda image=dr.IMAGE_TAG, env=None, exclude=(): dr.Capability(
            dr.CAPABILITY_UNAVAILABLE, "unit: daemon unreachable"
        ),
    )
    monkeypatch.setattr(dr, "_spawn", lambda *a: spawned.append(a))
    result = execute_and_reevaluate(snap, cand, appr, tmp_path / "c1")
    assert result.execution["status"] == "not_executed"
    assert spawned == []
    _not_executed(result, "isolation unavailable")


def test_missing_runner_image_only_invokes_the_docker_cli(tmp_path, monkeypatch):
    """Real capability probe: legitimate Docker CLI subprocesses are allowed and recorded;
    starting any other program (a Python interpreter running the candidate) fails the test."""
    snap, cand, appr = prepared(tmp_path)
    no_host_execution(monkeypatch)
    real_popen = subprocess.Popen
    launched = []

    class Guarded(real_popen):
        def __init__(self, args, *a, **kw):
            program = Path(
                str(args[0] if isinstance(args, (list, tuple)) else args)
            ).name.lower()
            launched.append(program)
            if program not in ("docker", "docker.exe"):
                raise AssertionError(f"non-Docker process started: {program}")
            super().__init__(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", Guarded)
    result = execute_and_reevaluate(
        snap,
        cand,
        appr,
        tmp_path / "c1",
        image="atlas-runner:t06-image-that-does-not-exist",
    )
    assert result.execution["status"] == "not_executed"
    assert all(p in ("docker", "docker.exe") for p in launched)
    record = json.loads(
        (result.candidate_dir / "exec" / "execution.json").read_text(encoding="utf-8")
    )
    assert "container_name" not in record
    _not_executed(result, "isolation unavailable")


# --- reporting, and the original audit left untouched ----------------------------------------


def _tree_hashes(root: Path) -> dict:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_report_separates_execution_from_outcome_and_leaves_the_original_alone(
    tmp_path, monkeypatch, evidence
):
    original = audit(S01, tmp_path / "runs")
    before = _tree_hashes(original.run_dir)

    _snap, done = run_case(
        tmp_path / "a",
        monkeypatch,
        evidence["faulty"],
        new_source=(S01 / "evaluate.py").read_text(encoding="utf-8") + "# comment\n",
    )
    snap2, cand2, appr2 = prepared(tmp_path / "b")
    changed = Candidate(
        cand2.entry_point, cand2.entry_bytes + b"#x\n", cand2.diff_sha256
    )
    refused = execute_and_reevaluate(snap2, changed, appr2, tmp_path / "b" / "c2")
    failed_source = 'raise SystemExit("early")\n' + (S01 / "evaluate.py").read_text(
        encoding="utf-8"
    )
    _, failed = run_case(
        tmp_path / "c", monkeypatch, None, new_source=failed_source, returncode=1
    )

    report = comparison_report(
        original.run_dir, original.outcome, [done, refused, failed]
    )
    assert _tree_hashes(original.run_dir) == before

    assert report["comparison_basis"] == MIXED_BASIS
    assert report["original"]["runner"] == trusted.RUNNER_NAME
    assert report["original"]["scientific_outcome"] == Outcome.VIOLATION_FOUND
    required = [a.assertion_id for a in original.outcome.assertions]
    assert [a["assertion_id"] for a in report["original"]["required_set"]] == required
    by_status = {c["execution"]["status"]: c for c in report["candidates"]}
    assert set(by_status) == {"completed", "refused", "failed"}
    # Execution success and scientific outcome are separate fields with separate values.
    assert by_status["completed"]["scientific_outcome"] == Outcome.VIOLATION_FOUND
    assert by_status["refused"]["scientific_outcome"] == Outcome.INCONCLUSIVE
    assert by_status["refused"]["evaluated"] is False
    assert by_status["failed"]["scientific_outcome"] == Outcome.INCONCLUSIVE
    for c in report["candidates"]:
        assert [a["assertion_id"] for a in c["required_set"]] == required
        assert [s["assertion_id"] for s in c["status_by_assertion"]] == required
        assert c["limitations"]
    assert any("candidate-produced" in x for x in by_status["completed"]["limitations"])
    assert "outcome.json" in by_status["completed"]["evidence_sha256"]
    text = json.dumps(report).lower()
    assert "fixed" not in text and "improved" not in text
