"""Recorded runs (T-07 follow-up, slice 4h): listing and integrity, without a browser.

A recorded run is shown only after every hash it recorded is recomputed from disk and each
reported outcome matches its verified outcome.json (`atlas.ui.recorded.verify`). The browser
path is tests/acceptance/test_scenario7_recorded.py.
"""

import importlib.util
import json
import shutil
from pathlib import Path, PureWindowsPath

import pytest

from atlas.agent import controller as ctl
from atlas.agent.client import FixtureClient
from atlas.audit import audit
from atlas.hosted.bundle import BUNDLE_ROOT
from atlas.ui import artifacts as A
from atlas.ui.catalogue import read_claim

try:  # new in slice 4h; at an earlier commit each test fails on its own (red demonstration)
    from atlas.ui import recorded as R
except ImportError:
    R = None


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.removesuffix(".py"), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("test_agent_slice3.py")
S01 = S.S01


def write(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def original_inside(run):
    """TEST-ONLY host baseline, placed where production puts the original: <run>/original."""
    staged = S.host_fixture_original(run)
    target = run.run_dir / "original"
    shutil.move(staged.run_dir, target)
    return ctl.OriginalRun(
        run_dir=target,
        outcome=staged.outcome,
        runner=staged.runner,
        executed=True,
    )


@pytest.fixture(scope="module")
def agent_run(tmp_path_factory):
    """A finished fixture agent run: the original evaluated, one proposal executed."""
    root = tmp_path_factory.mktemp("recorded")
    client = FixtureClient("rec", [{"content": S.PATCH}, {"content": S.FINISH}])
    result = ctl.run_agent(
        S01, root / "src", client, S.ApproveExactly(),
        executor=S.RecordingExecutor(), original=original_inside, env={},
    )  # fmt: skip
    assert result.terminal_state == ctl.REPORT, result.reason
    return result.run_dir


def copy_run(src: Path, dest: Path) -> Path:
    shutil.copytree(src, dest)
    return dest


def report_of(run: Path) -> dict:
    return json.loads((run / "agent_report.json").read_text(encoding="utf-8"))


def failing(checks) -> dict[str, str]:
    return {c.item: c.status for c in checks if not c.ok}


# =============================================================================================
# 1. Listing
# =============================================================================================


def test_only_finished_runs_under_the_two_patterns_are_listed(tmp_path):
    write(tmp_path / "live1" / "agent-s01_faulty-aaa" / "agent_report.json", {})
    (tmp_path / "live2" / "agent-s01_faulty-bbb").mkdir(parents=True)  # not finished
    write(tmp_path / "ui" / "agent-har_clean-ccc" / "agent_report.json", {})
    write(tmp_path / "ui" / "s02_clean-ddd" / "outcome.json", {})
    write(tmp_path / "ui" / "s02_clean-ddd" / "report.json", {})
    write(tmp_path / "ui" / ".ui-channels" / "x" / "result.json", {})
    write(tmp_path / "g4" / "agent-s01_faulty-eee" / "agent_report.json", {})
    write(tmp_path / "agent-s01_faulty-fff" / "agent_report.json", {})
    runs = R.list_runs(tmp_path)
    assert [(r.label, r.kind, r.project) for r in runs] == [
        ("live1/agent-s01_faulty-aaa", R.AGENT, "s01_faulty"),
        ("ui/agent-har_clean-ccc", R.AGENT, "har_clean"),
        ("ui/s02_clean-ddd", R.AUDIT, "s02_clean"),
    ]


def test_the_root_is_configurable(monkeypatch, tmp_path):
    monkeypatch.setenv(R.RECORDED_ENV, str(tmp_path))
    assert R.recorded_root() == tmp_path.resolve()
    monkeypatch.delenv(R.RECORDED_ENV)
    assert R.recorded_root() == (Path(S01).parents[2] / "runs").resolve()


def test_a_missing_root_lists_nothing(tmp_path):
    assert R.list_runs(tmp_path / "absent") == []


# =============================================================================================
# 2. Integrity
# =============================================================================================


def test_a_recorded_agent_run_verifies_intact(agent_run):
    report = report_of(agent_run)
    checks = R.verify(agent_run, report)
    assert R.intact(checks), failing(checks)
    items = {c.item for c in checks}
    assert {"agent_log.jsonl", "replies/a1.txt", "replies/a2.txt"} <= items
    assert {
        "original/outcome.json",
        "original/report.json",
        "proposals/r1.diff",
    } <= items
    assert "agent_report.json:scientific_outcomes.original" in items
    # Every hash the report records for the original is among the checks.
    evidence = report["comparison"]["original"]["evidence_sha256"]
    assert {f"original/{k}" for k in evidence} <= items


def test_one_changed_byte_is_detected(agent_run, tmp_path):
    run = copy_run(agent_run, tmp_path / "run")
    path = run / "original" / "outcome.json"
    data = bytearray(path.read_bytes())
    i = next(i for i, b in enumerate(data) if chr(b).isdigit())
    data[i] = ord(str((int(chr(data[i])) + 1) % 10))  # one byte; still valid JSON
    path.write_bytes(bytes(data))
    checks = R.verify(run, report_of(run))
    assert not R.intact(checks)
    assert failing(checks) == {"original/outcome.json": "changed"}


def test_a_missing_recorded_file_is_detected(agent_run, tmp_path):
    run = copy_run(agent_run, tmp_path / "run")
    (run / "replies" / "a1.txt").unlink()
    assert failing(R.verify(run, report_of(run))) == {"replies/a1.txt": "missing"}


def test_a_report_outcome_that_differs_from_its_outcome_json_is_detected(
    agent_run, tmp_path
):
    """The headline comes from the report: it must equal the verified outcome.json."""
    run = copy_run(agent_run, tmp_path / "run")
    report = report_of(run)
    assert report["scientific_outcomes"]["original"] == "VIOLATION_FOUND"
    report["scientific_outcomes"]["original"] = "NO_VIOLATION_FOUND"
    write(run / "agent_report.json", report)
    checks = R.verify(run, report_of(run))
    assert failing(checks) == {
        "agent_report.json:scientific_outcomes.original": "changed"
    }


def test_a_recorded_path_outside_the_run_is_refused(agent_run, tmp_path):
    run = copy_run(agent_run, tmp_path / "run")
    (tmp_path / "outside.diff").write_text("x", encoding="utf-8")
    report = report_of(run)
    report["proposals"][0]["diff_path"] = "../outside.diff"
    write(run / "agent_report.json", report)
    assert failing(R.verify(run, report_of(run))) == {"../outside.diff": "outside"}


def test_an_audit_run_verifies_from_its_index(tmp_path):
    run = audit(S01, tmp_path / "runs").run_dir
    checks = R.verify(run, None)
    assert R.intact(checks), failing(checks)
    assert {"outcome.json", "report.json", "report.json:outcome"} <= {
        c.item for c in checks
    }
    path = run / "report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["outcome"] = "NO_VIOLATION_FOUND"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert failing(R.verify(run, None)) == {
        "report.json": "changed",
        "report.json:outcome": "changed",
    }


# =============================================================================================
# 3. The claim and the time come from the run itself
# =============================================================================================


def test_the_claim_is_the_manifest_the_run_evaluated(agent_run):
    run = R.RecordedRun(agent_run, "x/" + agent_run.name, R.AGENT)
    source = R.claim_source(run)
    assert source == agent_run / "original" / "manifest.snapshot.json"
    recorded, project = R.read_claim(source), read_claim(S01)
    assert (recorded.statement, recorded.type, recorded.roles) == (
        project.statement,
        project.type,
        project.roles,
    )


def test_the_finish_time_is_the_last_recorded_state(agent_run):
    run = R.RecordedRun(agent_run, agent_run.name, R.AGENT)
    report = report_of(agent_run)
    when, source = R.finished(run, report)
    assert when == report["states"][-1]["time_utc"]
    assert "agent_report.json" in source


def test_decisions_come_from_the_log():
    events = [
        {"event": "approval", "kind": "original", "decision": "approved"},
        {"event": "tool", "tool": "finish"},
        {"event": "approval", "kind": "candidate", "decision": "declined"},
    ]
    assert R.logged_decisions(events) == [
        {"kind": "original", "decision": "approved"},
        {"kind": "candidate", "decision": "declined"},
    ]


# =============================================================================================
# 4. Recorded path strings are reduced to a name without the host's path rules
#    (hosted stage C, 2026-10-19: a Windows run_dir parsed on Linux named a missing subfolder)
# =============================================================================================

WIN_RUN_DIR = r"C:\Users\x\runs\r\candidates\c1"
POSIX_RUN_DIR = "/home/x/runs/r/candidates/c1"


@pytest.mark.parametrize(
    ("value", "name"),
    [
        (WIN_RUN_DIR, "c1"),
        (POSIX_RUN_DIR, "c1"),
        ("candidates/c1", "c1"),
        (r"candidates\c1", "c1"),
        ("c1", "c1"),
        ("", None),
        (".", None),
        ("..", None),
        ("C:", None),
        ("C:\\", None),
        ("a/..", None),
        (r"a\..", None),
        ("c1:stream", None),
        (None, None),
        (5, None),
    ],
)
def test_a_recorded_basename_is_separator_agnostic_and_fails_closed(value, name):
    assert A.recorded_basename(value) == name


@pytest.mark.parametrize("run_dir", [WIN_RUN_DIR, POSIX_RUN_DIR, "candidates/c1"])
def test_the_candidate_subfolder_does_not_depend_on_the_host_platform(run_dir):
    """Pure string logic: the same subfolder for a Windows and a POSIX recorded run_dir."""
    assert R.candidate_subfolder({"run_dir": run_dir}, 1) == "candidates/c1"
    assert R.candidate_subfolder({}, 2) == "candidates/c2"  # none recorded: by position


# Read only, never changed.
LIVE6 = BUNDLE_ROOT / "live6" / "agent-s01_faulty-877f8245a8a2"


@pytest.mark.parametrize("run_dir", [WIN_RUN_DIR, POSIX_RUN_DIR])
def test_a_run_recorded_on_another_platform_verifies_intact(run_dir):
    """The bundled live run 6 (recorded on Windows), with its candidate's run_dir in either
    form: every candidate file is checked and matches."""
    report = report_of(LIVE6)
    assert (
        PureWindowsPath(report["comparison"]["candidates"][0]["run_dir"]).name == "c1"
    )
    report["comparison"]["candidates"][0]["run_dir"] = run_dir
    checks = R.verify(LIVE6, report)
    assert R.intact(checks), failing(checks)
    assert len([c for c in checks if c.item.startswith("candidates/c1/")]) >= 6
    exported = {f.label for f in A.exports(LIVE6, report)}
    assert "candidates/c1/outcome.json" in exported


@pytest.mark.parametrize("run_dir", ["..", "C:\\", "a/..", 5])
def test_an_unusable_recorded_run_dir_is_not_intact(run_dir):
    report = report_of(LIVE6)
    report["comparison"]["candidates"][0]["run_dir"] = run_dir
    assert failing(R.verify(LIVE6, report)) == {
        "agent_report.json:comparison.candidates[1].run_dir": "missing"
    }
    assert not any(f.label.startswith("candidates/") for f in A.exports(LIVE6, report))
