"""T-07 UI, offline units: fixture scripts, the BrowserApprover rule, artifact readers.

No browser, Docker or model: the approver is driven from a thread, as the page drives it.
"""

import hashlib
import importlib.util
import json
import threading
import time
from pathlib import Path

import pytest

from atlas.agent.approval import ApprovalUnavailable
from atlas.agent.controller import ApprovalRequest
from atlas.candidates import Approval
from atlas.ui import approver as ch
from atlas.ui import artifacts as A
from atlas.ui import scripts

ROOT = Path(__file__).resolve().parents[2]
HASH = "ab12cd34ef56" + "7" * 52


def _integration_module():
    path = ROOT / "tests" / "integration" / "test_agent_fixture_docker.py"
    spec = importlib.util.spec_from_file_location("agent_fixture_docker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_revision_script_is_the_integration_tests_script():
    assert scripts.BY_KEY["revision"].replies() == _integration_module().SCRIPT


def test_every_script_is_valid_fixture_input():
    from atlas.agent.client import FixtureClient

    for s in scripts.SCRIPTS:
        FixtureClient(f"ui-{s.key}", s.replies())  # plain identifier, list of entries
    assert scripts.default_script("s01_faulty") == "revision"
    assert {s.key for s in scripts.scripts_for("s02_clean")} == {
        "inspect_only",
        "timeout",
        "invalid",
    }


# -- approver --------------------------------------------------------------------------------
def request(kind="candidate"):
    return ApprovalRequest(
        entry_point="evaluate.py",
        diff="--- a/evaluate.py\n+++ b/evaluate.py\n",
        candidate_hash=HASH,
        base_snapshot_hash="c" * 64,
        model_rationale="r",
        kind=kind,
    )


def decide_with(tmp_path, typed, **kwargs):
    """Run decide() on a thread and answer it like the page does."""
    ch.touch(tmp_path)
    approver = ch.BrowserApprover(tmp_path, now=lambda: "t", **kwargs)
    out = {}

    def run():
        try:
            out["result"] = approver.decide(request())
        except ApprovalUnavailable as exc:
            out["unavailable"] = str(exc)

    t = threading.Thread(target=run)
    t.start()
    deadline = time.time() + 10
    while ch.read_pending(tmp_path) is None and time.time() < deadline:
        time.sleep(0.05)
    pending = ch.read_pending(tmp_path)
    if typed is not ...:
        assert ch.answer(tmp_path, pending["seq"], typed) is True
        assert ch.answer(tmp_path, pending["seq"], "again") is False  # one attempt
    t.join(timeout=10)
    return approver, out, pending


def test_the_typed_prefix_approves_with_the_full_hash(tmp_path):
    approver, out, pending = decide_with(tmp_path, "  AB12CD34EF56 \n")
    assert out["result"] == Approval(HASH, "c" * 64, "t")
    assert approver.last_reason == "confirmed"
    # The pending request is exactly the engine's request.
    assert {
        k: pending[k] for k in ("candidate_hash", "base_snapshot_hash", "kind")
    } == {
        "candidate_hash": HASH,
        "base_snapshot_hash": "c" * 64,
        "kind": "candidate",
    }
    assert ch.read_pending(tmp_path) is None
    assert ch.read_decisions(tmp_path) == [
        {"kind": "candidate", "decision": "approved"}
    ]


@pytest.mark.parametrize("typed", ["ab12cd34ef5", HASH, "yes", "", "zz12cd34ef56"])
def test_anything_but_the_exact_prefix_declines(tmp_path, typed):
    approver, out, _ = decide_with(tmp_path, typed)
    assert out["result"] is None and approver.last_reason == "confirmation_mismatch"


def test_closing_the_panel_means_unavailable(tmp_path):
    approver, out, _ = decide_with(tmp_path, None)
    assert "unavailable" in out and approver.last_reason == "input_closed"


def test_no_page_means_no_terminal(tmp_path):
    approver = ch.BrowserApprover(tmp_path)  # no heartbeat file at all
    with pytest.raises(ApprovalUnavailable):
        approver.decide(request())
    assert approver.last_reason == "no_terminal"
    assert ch.read_pending(tmp_path) is None


def test_a_page_left_without_a_decision_means_unavailable(tmp_path):
    approver, out, _ = decide_with(tmp_path, ..., left_page_s=0.5)
    assert "the page was left" in out["unavailable"]
    assert approver.last_reason == "input_closed"


# -- artifact readers ----------------------------------------------------------------------------
def test_proposal_files_are_read_with_recomputed_hashes(tmp_path):
    (tmp_path / "proposals").mkdir()
    (tmp_path / "proposals" / "r1.diff").write_bytes(b"diff text\n")
    good = hashlib.sha256(b"diff text\n").hexdigest()
    report = {
        "proposals": [
            {"revision": 1, "diff_path": "proposals/r1.diff", "diff_sha256": good},
            {"revision": 2, "diff_path": "proposals/r1.diff", "diff_sha256": "0" * 64},
            {"revision": 3, "diff_path": "../outside.diff", "diff_sha256": good},
        ]
    }
    (tmp_path.parent / "outside.diff").write_text("x", encoding="utf-8")
    views = A.proposals(tmp_path, report)
    assert views[0].diff_text == "diff text\n" and views[0].diff_hash_matches is True
    assert (
        views[1].diff_hash_matches is False
    )  # a recorded hash that differs is shown so
    assert views[2].diff_text is None  # never read outside the run directory


def test_exports_compare_with_the_recorded_hashes(tmp_path):
    (tmp_path / "agent_log.jsonl").write_bytes(b"{}\n")
    (tmp_path / "agent_report.json").write_bytes(b"{}")
    log_sha = hashlib.sha256(b"{}\n").hexdigest()
    rows = {
        f.label: f
        for f in A.exports(
            tmp_path, {"agent_log": {"sha256": log_sha}, "comparison": {}}
        )
    }
    assert rows["agent_log.jsonl"].matches is True
    assert rows["agent_report.json"].matches is None  # the engine records no self-hash


def test_the_log_reader_skips_a_line_still_being_written(tmp_path):
    (tmp_path / "agent_log.jsonl").write_text(
        json.dumps({"event": "state", "state": "INTAKE"}) + "\n" + '{"event": "sta',
        encoding="utf-8",
    )
    assert A.trace(A.read_log(tmp_path)).current_state == "INTAKE"


def test_next_actions_cover_every_not_assessed_reason():
    from atlas.contracts import Reason

    assert set(A.NEXT_ACTIONS) == {r.value for r in Reason}
    assert "Split the claim" in A.next_action_for_intake(
        "claim type 'a+b' is not supported in V1 (combined or unknown)"
    )
    assert A.next_action_for_intake("anything else") == A.INTAKE_FALLBACK


def test_outcome_labels_are_the_prd_labels():
    assert set(A.OUTCOME_LABELS) == {
        "VIOLATION_FOUND",
        "NO_VIOLATION_FOUND",
        "INCONCLUSIVE",
        "NOT_SUPPORTED",
    }
    assert A.CAVEAT == "This does not say the scientific claim is true or false."


# -- T-09: real-data catalogue entries ------------------------------------------------------------
def test_har_entries_are_labelled_and_unavailable_without_data(tmp_path, monkeypatch):
    from atlas.ui import catalogue as cat
    from atlas.ui import worker

    flawed = cat.BY_NAME["har_flawed"]
    assert "ATLAS-authored flawed variant" in flawed.label
    assert (
        cat.BY_NAME["s01_faulty"].unavailable() is None
    )  # synthetic fixtures always run
    monkeypatch.setattr(cat, "REAL_SENSOR", tmp_path)  # no data/ folder, no table
    missing = cat.Fixture("har_clean", "x", root=tmp_path)
    reason = missing.unavailable()
    assert reason is not None and cat.RETRIEVE_COMMAND in reason
    # The intake still reads the manifest without crashing ("table absent").
    assert cat.read_claim(cat.REAL_SENSOR.parent / "missing").supported is False
    # The worker refuses to start an unavailable project: nothing runs.
    monkeypatch.setitem(cat.BY_NAME, "har_clean", missing)
    monkeypatch.setitem(worker.BY_NAME, "har_clean", missing)
    monkeypatch.setenv(worker.RUNS_ENV, str(tmp_path / "runs"))
    assert worker.Registry().start("har_clean", worker.AGENT, "inspect_only") is None
