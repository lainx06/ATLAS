"""Scenarios 2 and 3 (UI_SPEC §9): the clean control, missing metadata and an unsupported claim.

No fabricated leakage finding on the clean control, limitations visible; missing metadata and
the unsupported claim are never shown as a green pass, and each carries a next action keyed
to the engine's reason. Values are checked against the run's artifacts.
"""

import json

from helpers import (
    answer,
    click_run,
    open_app,
    select_mode,
    select_project,
    select_script,
    shot,
    shown_hash,
    table_rows,
    text,
    wait_finished,
)

GREEN = "rgb(21, 128, 61)"  # #15803D, the PASS / NO_VIOLATION_FOUND colour
AMBER = "rgb(180, 83, 9)"  # #B45309, INCONCLUSIVE / NOT_ASSESSED
STONE = "rgb(68, 64, 60)"  # #44403C, NOT_SUPPORTED


def agent_run(page, app, project: str, approvals: int = 1):
    open_app(page, app)
    select_project(page, project)
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    select_script(page, "Inspect only, no revision")
    click_run(page)
    previous = None
    for _ in range(approvals):
        previous = shown_hash(page, previous)
        answer(page, previous[:12])
    wait_finished(page, app)
    run = app.agent_runs(project)[-1]
    return run, json.loads((run / "agent_report.json").read_text(encoding="utf-8"))


def headline_color(page, key: str, code: str) -> str:
    """The computed colour of the printed outcome code in the headline."""
    return (
        page.locator(f".st-key-{key} h2")
        .get_by_text(code, exact=True)
        .evaluate("el => getComputedStyle(el).color")
    )


def test_clean_control_has_no_fabricated_finding(app, docker, page):
    _run, report = agent_run(page, app, "s02_clean")
    shot(page, "s2_01_clean_result")
    assert report["scientific_outcomes"]["original"] == "NO_VIOLATION_FOUND"
    headline = text(page, "headline-original")
    assert "NO_VIOLATION_FOUND" in headline
    assert "Every required check passed within the coverage shown." in headline
    required = report["comparison"]["original"]["required_set"]
    rows = table_rows(page, "finding-checks")
    assert (
        [r[0] for r in rows] == [r["status"] for r in required] == ["PASS"] * len(rows)
    )
    assert "0 of 9 required checks FAIL" in text(page, "finding-counts")
    # No candidate, honestly: the model finished without one.
    revision = page.locator(".st-key-card-revision").inner_text()
    assert "No candidate proposed" in revision
    assert page.locator(".st-key-card-comparison").count() == 0
    # Limitations stay visible: the run's, and the evaluation's behind their expander.
    shown = text(page, "run-limitations")
    assert all(x in shown for x in report["limitations"])
    page.get_by_text("Limitations of this evaluation").click()
    evaluation = text(page, "finding-limitations")
    assert all(x in evaluation for x in report["comparison"]["original"]["limitations"])


def test_missing_metadata_is_inconclusive_with_reasons_and_next_action(
    app, docker, page
):
    _run, report = agent_run(page, app, "s06_missing_metadata")
    shot(page, "s3_01_missing_metadata")
    assert report["scientific_outcomes"]["original"] == "INCONCLUSIVE"
    assert "INCONCLUSIVE" in text(page, "headline-original")
    assert headline_color(page, "headline-original", "INCONCLUSIVE") == AMBER != GREEN
    required = report["comparison"]["original"]["required_set"]
    expected = [
        [r["status"], r["assertion_id"], r["reason"] or ""]
        for r in required
        if r["status"] == "NOT_ASSESSED"
    ]
    shown = [
        r[:3] for r in table_rows(page, "finding-checks") if r[0] == "NOT_ASSESSED"
    ]
    assert shown == expected and all(r[2] == "missing_metadata" for r in shown)
    actions = text(page, "next-actions")
    assert (
        "missing_metadata" in actions
        and "Declare the missing identity columns" in actions
    )
    coverage = report["comparison"]["original"]["incomplete_coverage"]
    assert coverage and all(
        c in page.locator(".st-key-card-finding").inner_text() for c in coverage
    )


def test_unsupported_claim_shows_not_supported_and_next_action(app, page):
    open_app(page, app)
    select_project(page, "s08a_combined_claim")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    click_run(page)
    wait_finished(
        page, app
    )  # NOT_SUPPORTED at intake: nothing to approve, nothing runs
    shot(page, "s3_02_not_supported")
    run = app.agent_runs("s08a_combined_claim")[-1]
    report = json.loads((run / "agent_report.json").read_text(encoding="utf-8"))
    assert report["terminal_state"] == "NOT_SUPPORTED"
    block = text(page, "not-supported")
    assert "NOT_SUPPORTED" in block
    assert "ATLAS can't assess this claim or project in V1." in block
    assert report["terminal_reason"] in block
    assert "Split the claim into one supported type" in block
    assert headline_color(page, "not-supported", "NOT_SUPPORTED") == STONE != GREEN
    assert not (run / "original").exists()  # nothing executed


def test_deterministic_audit_mode_matches_outcome_json(app, page):
    open_app(page, app)
    select_project(page, "s06_missing_metadata")
    select_mode(page, "Deterministic audit: no model")
    click_run(page)
    wait_finished(page, app)
    shot(page, "s3_03_audit_mode")
    run = app.audit_runs("s06_missing_metadata")[-1]
    outcome = json.loads((run / "outcome.json").read_text(encoding="utf-8"))
    assert outcome["outcome"] == "INCONCLUSIVE"
    assert "Deterministic audit: no model" in text(page, "banner")
    assert "INCONCLUSIVE" in text(page, "headline-original")
    rows = table_rows(page, "finding-checks")
    assert sorted(r[1] for r in rows) == sorted(
        a["assertion_id"] for a in outcome["assertions"]
    )
    assert "missing_metadata" in text(page, "next-actions")
