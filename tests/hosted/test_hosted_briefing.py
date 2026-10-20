"""The deterministic briefing on a hosted live session (UI design pass phase 2, part C).

A session run offline (mocked Token Factory, fake reservations): its briefing is exactly the
lines its verified files support, including "Proposals were checked by ATLAS validation and
not executed here."; a marker seeded into the model's replies reaches the run's replies and
model text but never the briefing.
"""

import json

import hosted_helpers as H
from test_render_failure import hosted_page

from atlas.agent import controller as ctl
from atlas.agent.budget import Budget
from atlas.agent.network import deny_network
from atlas.hosted import bundle, page
from atlas.hosted import session as hs
from atlas.ui import artifacts as A
from atlas.ui import hud as HUD
from atlas.ui import recorded as R

MARKER = "ZQX-HOSTED-BRIEFING-MARKER-41d9"
EXPECTED = [
    "Evidence intact: 25 of 25 recorded hashes verified now.",
    "Original outcome: VIOLATION_FOUND. Required checks: 4 FAIL, 0 NOT_ASSESSED, "
    + "0 ERROR (of 9).",
    "split.no_group_overlap (FAIL): No group_id value is in both partitions of a fold.",
    "split.sampling_unit_disjoint (FAIL): No unit_id value crosses partitions.",
    "split.repeated_measures_rule (FAIL): v1.1: assessed through an explicit route over rows "
    + "participating in the declared folds, from the route's own same-fold witnesses; "
    + "aggregate group/unit statuses are never inherited.",
    "fit.state_dependencies_within_fold_train (FAIL): For every use event in fold k "
    + "(transforms and predictions, on train or eval rows), the dependency rows of the used "
    + "state version ⊆ train(k).",
    HUD.PROPOSALS_NOT_EXECUTED,
    "Balanced accuracy (pooled), descriptive only: original 0.6812.",
    A.CAVEAT,
]


def session(tmp_path, replies):
    provider = H.Provider([H.completion(c) for c in replies])
    with deny_network():
        result = ctl.run_agent(
            H.S01, tmp_path / "runs", H.client(provider), H.SpyApprover(),
            budget=Budget(max_attempts=6), original=bundle.live_original(),
            live_authorized=True, spend=H.decided_limits(), hosted=True,
            reservations=H.FakeReservations(provider=provider),
        )  # fmt: skip
    assert result.terminal_state == ctl.REPORT, result.reason
    return result.run_dir


def lines_for(run_dir):
    report = A.read_json(run_dir / "agent_report.json")
    checks = R.verify(run_dir, report)
    return HUD.briefing_lines(run_dir, report, checks, HUD.load_definitions())


def test_the_hosted_session_briefing_text_is_exact(tmp_path, monkeypatch):
    run_dir = session(tmp_path, [*H.LIVE6_REPLIES, H.FINISH])
    assert HUD.briefing_text(lines_for(run_dir)) == EXPECTED
    # The page shows it first, inside the finished session.
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_HOSTED_RUNS_DIR", str(tmp_path / "hosted-runs"))
    for name in ("NEBIUS_API_KEY", "DATABASE_URL", "JUDGE_ACCESS_CODE"):
        monkeypatch.delenv(name, raising=False)
    handle = page.LiveHandle(
        tmp_path,
        outcome=hs.Outcome("ran", None, "public", run_dir, ctl.REPORT),
    )
    at = hosted_page(handle)
    assert not at.exception and not at.error
    brief = next(m.value for m in at.markdown if "hud-brief" in str(m.value))
    for line in EXPECTED[:2] + EXPECTED[6:]:
        assert HUD.esc(line) in brief


def test_a_marker_in_the_models_replies_never_reaches_the_briefing(tmp_path):
    revision = json.loads(H.LIVE6_REPLIES[2])
    revision["action"]["rationale"] = f"{MARKER} rationale"
    finish = {"action": {"tool": "finish", "summary": f"{MARKER} summary"}}
    replies = [*H.LIVE6_REPLIES[:2], json.dumps(revision), json.dumps(finish)]
    run_dir = session(tmp_path, replies)
    report = A.read_json(run_dir / "agent_report.json")
    # The marker is in the run's model-written records ...
    stored = "".join(p.read_text("utf-8") for p in (run_dir / "replies").iterdir())
    assert MARKER in stored
    assert any(MARKER in t["text"] for t in report.get("model_text") or [])
    assert [p["outcome"] for p in report["proposals"]] == ["not_executed_here"]
    # ... and nowhere in the briefing, its markup or its sources.
    lines = lines_for(run_dir)
    assert HUD.briefing_text(lines) == EXPECTED
    html = HUD.briefing(lines, HUD.Ids(HUD.run_hash(run_dir.name)))
    assert MARKER not in html
    assert MARKER not in " ".join(line.source for line in lines)
