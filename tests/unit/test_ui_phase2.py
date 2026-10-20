"""UI design pass phase 2 (docs/UI_DESIGN_HUD.md §11): the HUD on every view.

The typed-approval panel keeps the engine's request in full and its one submission unchanged;
failure and honest-empty states carry their status colour, code, reason and next action and
never success styling; the mission track and budget gauge read a run's log while it is going.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas.agent.approval import CONFIRM_CHARS
from atlas.ui import artifacts as A
from atlas.ui import hud as H

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = BUNDLE / "live6" / "agent-s01_faulty-877f8245a8a2"
CODE = "ab12cd34ef56" + "0" * 52
SNAPSHOT = "c" * 64
SUCCESS = (":green-badge", ":green[", "st.success", "hud-c-green")


def pending(kind: str = "candidate") -> dict:
    return {
        "seq": 3,
        "kind": kind,
        "candidate_hash": CODE,
        "base_snapshot_hash": SNAPSHOT,
        "entry_point": "evaluate.py",
        "model_rationale": "fold-local <b>selection</b>",
        "diff": "--- a/evaluate.py\n+++ b/evaluate.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n",
    }


def panel_app(tmp_path: Path, request: dict) -> AppTest:
    channel = tmp_path / "channel"
    channel.mkdir(exist_ok=True)
    script = tmp_path / "panel.py"
    script.write_text(
        "import json\nfrom pathlib import Path\nfrom atlas.ui import views as V\n"
        f"V.approval_panel(Path({str(channel)!r}), json.loads({json.dumps(request)!r}))\n",
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script), default_timeout=30)
    at.run()
    assert not at.exception
    return at


def markdown(at) -> list[str]:
    return [str(m.value) for m in at.markdown]


# -- the typed-approval panel ------------------------------------------------------------------
def test_the_approval_panel_shows_both_hashes_in_full(tmp_path):
    at = panel_app(tmp_path, pending())
    blocks = [m for m in markdown(at) if "hud-hash" in m]
    assert blocks == [H.hash_block(SNAPSHOT), H.hash_block(CODE)]
    for value in (SNAPSHOT, CODE):  # never truncated, in Plex Mono, wrapping
        assert any(f">{value}</p>" in b for b in blocks)
    css = H.CSS
    rule = css[css.index(".hud.hud-hash{") :].split("}", 1)[0]
    assert "IBM Plex Mono" in rule and "color:#E2E8F0" in rule
    assert "overflow-wrap:anywhere" in rule and "word-break:break-all" in rule
    assert "text-overflow" not in rule and "ellipsis" not in rule


def test_the_diff_and_rationale_sit_in_the_model_written_frame(tmp_path):
    at = panel_app(tmp_path, pending())
    shown = markdown(at)
    # Each model-written block: the badge first, then the engine's label, then the text.
    assert shown.count(H.MODEL_BADGE_MARKDOWN) == 2
    captions = [c.value for c in at.caption]
    assert "Rationale: model-written (untrusted)" in captions
    assert "Proposed diff (untrusted; control characters shown as escapes)" in captions
    assert [t.value for t in at.text] == ["fold-local <b>selection</b>"]  # inert
    (code,) = [c for c in at.code if c.language == "diff"]
    assert code.value == pending()["diff"].rstrip()
    # The frame never carries outcome styling.
    for value in shown:
        if "hud" in value:
            assert "hud-ret" not in value and "VIOLATION_FOUND" not in value


def test_the_original_panel_has_no_model_written_frame(tmp_path):
    at = panel_app(tmp_path, pending("original"))
    assert H.MODEL_BADGE_MARKDOWN not in markdown(at)
    assert not at.code and not at.text
    assert any("Run the ORIGINAL" in m for m in markdown(at))


def test_the_decision_is_one_submission_of_exactly_what_was_typed(tmp_path):
    at = panel_app(tmp_path, pending())
    (field,) = at.text_input
    assert field.label == (
        f"Type the first {CONFIRM_CHARS} characters of the code hash to approve; "
        "anything else declines"
    )
    labels = [b.label for b in at.button]
    assert labels == ["Submit confirmation", "Close without deciding"]
    field.input("  AB12CD34EF56 ")
    next(b for b in at.button if b.label == "Submit confirmation").click()
    at.run()
    answer = json.loads((tmp_path / "channel" / "answer-3.json").read_text("utf-8"))
    assert answer == {"typed": "  AB12CD34EF56 "}  # the rule is applied by the engine
    # Once answered, the panel only waits; nothing more can be submitted.
    assert not at.text_input and not at.button
    assert [i.value for i in at.info] == [
        "Decision submitted; waiting for the engine to continue."
    ]


def test_closing_without_deciding_sends_no_typed_text(tmp_path):
    at = panel_app(tmp_path, pending())
    next(b for b in at.button if b.label == "Close without deciding").click()
    at.run()
    answer = json.loads((tmp_path / "channel" / "answer-3.json").read_text("utf-8"))
    assert answer == {"typed": None}


def test_the_active_frame_and_the_decision_are_documented_hooks():
    from atlas.ui import views as V

    css = V.CSS
    panel = css[css.index(".st-key-approval-panel {") :].split("}", 1)[0]
    assert panel.count("#67E8F9 0 0") == 8  # four corner brackets, two marks each
    assert "background-origin: border-box" in panel
    assert ".st-key-approval-decision {" in css and ".st-key-approval-close {" in css


# -- failure and honest-empty states -----------------------------------------------------------
def finished_app(tmp_path: Path, report: dict) -> AppTest:
    """The report in a run folder whose one recorded file (the log) verifies: finished_run
    verifies the run itself before drawing anything (release review 1, F1)."""
    run_dir = tmp_path / "agent-s01_faulty-000000000000"
    run_dir.mkdir()
    log = run_dir / "agent_log.jsonl"
    log.write_bytes(b"")
    report = {**report, "agent_log": {"sha256": A.sha256_file(log)}}
    script = tmp_path / "finished.py"
    script.write_text(
        "import json\nfrom pathlib import Path\nfrom atlas.ui import results as R\n"
        f"R.finished_run(Path({str(run_dir)!r}), json.loads({json.dumps(report)!r}), "
        "R.AGENT, decisions=[])\n",
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script), default_timeout=30)
    at.run()
    assert not at.exception
    return at


@pytest.mark.parametrize(
    ("state", "badge"),
    [
        ("ERROR", ":violet-badge[ERROR]"),
        ("NEEDS_INPUT", ":orange-badge[NEEDS_INPUT]"),
        ("BUDGET_EXHAUSTED", ":orange-badge[BUDGET_EXHAUSTED]"),
    ],
)
def test_a_failed_terminal_state_shows_code_reason_and_next_action(
    tmp_path, state, badge
):
    report = {
        "terminal_state": state,
        "terminal_reason": "model_timeout (after one retry)",
        "states": [
            {"state": "INTAKE", "time_utc": None, "detail": None},
            {"state": state, "time_utc": None, "detail": None},
        ],
        "budget": {"used": {"attempts": 2}, "limits": {"model_attempts": 6}},
        "cost": {"applicable": False, "reason": "fixture replies: no provider request"},
    }
    at = finished_app(tmp_path, report)
    shown = "\n".join(markdown(at))
    assert f"{badge} Terminal state. Reason: `model_timeout (after one retry)`" in shown
    assert f"**Next action:** {A.TERMINAL_ACTIONS[state]}" in shown
    for success in SUCCESS:
        assert success not in shown
    assert not at.success
    # The mission track ends in the state's own colour and code.
    track = next(m for m in markdown(at) if "hud-track" in m)
    tone = H.TONE[state]
    assert f'<b class="hud-code hud-c-{tone}">{H.esc(state)}</b>' in track


def test_not_supported_keeps_its_headline_reason_and_next_action(tmp_path):
    report = {
        "terminal_state": "NOT_SUPPORTED",
        "terminal_reason": "claim type 'combined' is not supported in V1 (combined or "
        "unknown)",
        "states": [{"state": "NOT_SUPPORTED", "time_utc": None, "detail": None}],
    }
    shown = "\n".join(markdown(finished_app(tmp_path, report)))
    assert "## :gray[NOT_SUPPORTED]" in shown
    assert "**Next action:** Split the claim into one supported type" in shown
    for success in SUCCESS:
        assert success not in shown


def test_every_state_tone_has_a_frame_colour_and_no_green():
    from atlas.ui import views as V

    assert set(V.STATE_TONE.values()) <= set(V.STATE_BADGE)
    assert "green" not in V.STATE_BADGE
    for tone in ("red", "amber", "violet"):
        assert f'[class*="st-key-state-{tone}-"]' in V.CSS
    assert set(A.TERMINAL_ACTIONS) == set(A.FAILED_STATES)


# -- the track and the gauge from a run's own log -----------------------------------------------
def log_events() -> list[dict]:
    return [
        json.loads(line)
        for line in (LIVE6 / "agent_log.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_the_live_track_shows_the_stages_recorded_so_far():
    events = log_events()
    ids = H.Ids("0" * 8)
    states = [e for e in events if e["event"] == "state"]
    for cut in (1, 5, len(events)):
        so_far = events[:cut]
        recorded = [e["state"] for e in so_far if e["event"] == "state"]
        html = H.track_live(so_far, ids, lit_from=None)
        assert html.count('<li class="hud-stage') == max(len(recorded), 1)
        for state in recorded:
            assert H.esc(state) in html
        attempts = sum(e["event"] == "model_attempt" for e in so_far)
        assert f"{attempts} so far" in html
    full = H.track_live(events, ids)
    assert f"{len(states)} recorded stages" in full
    assert states[-1]["state"] == "BUDGET_EXHAUSTED"
    assert f'<b class="hud-code hud-c-amber">{H.esc("BUDGET_EXHAUSTED")}</b>' in full
    assert 'aria-current="step"' not in full  # ended: nothing is current


def test_only_new_stages_light_and_only_once():
    events = log_events()[:6]
    ids = H.Ids("0" * 8)
    n = len([e for e in events if e["event"] == "state"])
    first = H.track_live(events, ids, lit_from=0)
    assert first.count("hud-a-node") == n and "hud-anim" in first
    later = H.track_live(log_events()[:12], ids, lit_from=n)
    m = len([e for e in log_events()[:12] if e["event"] == "state"])
    assert later.count("hud-a-node") == m - n
    settled = H.track_live(events, ids, lit_from=n)
    assert "hud-a-node" not in settled and "hud-anim" not in settled
    assert "infinite" not in H.CSS


def test_the_live_gauge_sums_the_logged_attempts():
    events = log_events()
    report = A.read_json(LIVE6 / "agent_report.json")
    requests, spent = H.log_spend(events)
    assert requests == len(report["cost"]["entries"]) == 5
    assert spent == Decimal(report["cost"]["estimated_total_usd"])
    html = H.gauge_live(
        events, H.Ids("0" * 8), max_attempts=6, cap_usd="0.0648", caps_source="x"
    )
    assert "5 of 6" in html and f"{spent} of 0.0648 estimate cap" in html
    assert "estimate, not billing" in html.lower()
    fixture = [{"event": "model_attempt", "cost": "not applicable (fixture)"}]
    assert H.log_spend(fixture) == (1, None)


def test_the_hash_block_escapes_and_never_truncates():
    assert H.hash_block(CODE) == f'<p class="hud hud-hash">{CODE}</p>'
    assert H.NOT_RECORDED in H.hash_block(None)
    assert "<b>" not in H.hash_block("<b>x</b>")
