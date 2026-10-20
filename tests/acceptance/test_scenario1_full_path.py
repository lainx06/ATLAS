"""Scenario 1 (UI_SPEC §9): the faulty project, full path, plus the approval label checks.

Select s01_faulty, confirm the claim, run, approve the original and the candidate by typing
the shown prefixes, inspect the evidence, open the diff, export. Every visible value checked
here is compared with the engine artifact it displays.
"""

import contextlib
import hashlib
import json

import pytest
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
from playwright.sync_api import TimeoutError as PlaywrightTimeout

LABEL = "model-written text; not evidence and not an outcome"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def finished(app, docker, browser):
    """One s01 run driven through the page; the page stays open for the checks."""
    context = browser.new_context(
        viewport={"width": 1440, "height": 900}, accept_downloads=True
    )
    page = context.new_page()
    open_app(page, app)
    select_project(page, "s01_faulty")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    select_script(page, "Propose a grouped, fold-local revision")
    shot(page, "s1_01_claim")
    click_run(page)
    seen = []
    previous = None
    for kind in ("original", "candidate"):
        full = shown_hash(page, previous)
        panel = page.locator(".st-key-approval-panel").inner_text()
        seen.append((kind, full, panel))
        shot(page, f"s1_02_approval_{kind}")
        answer(page, full[:12])
        previous = full
        if kind == "original":  # best effort: the running window lasts seconds
            with contextlib.suppress(
                PlaywrightTimeout
            ):  # a screenshot, not an assertion
                page.locator(".st-key-card-analysis").wait_for(timeout=15_000)
                shot(page, "s1_02b_running_trace")
    wait_finished(page, app)
    shot(page, "s1_03_result_top")
    (run,) = app.agent_runs("s01_faulty")
    report = json.loads((run / "agent_report.json").read_text(encoding="utf-8"))
    yield page, run, report, seen
    context.close()


def test_the_approval_panel_shows_the_engine_request_in_full(finished):
    _page, run, report, seen = finished
    (_, original_hash, original_panel), (_, cand_hash, cand_panel) = seen
    assert (
        "Run the ORIGINAL, unmodified project code in the isolated Docker runner."
        in (original_panel)
    )
    assert "Run this CANDIDATE revision in the isolated Docker runner." in cand_panel
    approvals = [
        json.loads(line)
        for line in (run / "agent_log.jsonl").read_text(encoding="utf-8").splitlines()
        if '"event": "approval"' in line
    ]
    assert [a["candidate_hash"] for a in approvals] == [original_hash, cand_hash]
    assert [a["approver_reason"] for a in approvals] == ["confirmed", "confirmed"]
    # The full hash is shown and recorded; only its 12-character prefix was typed.
    assert all(len(a["approval"]["candidate_hash"]) == 64 for a in approvals)
    assert report["comparison"]["candidates"][0]["candidate_hash"] == cand_hash
    # The candidate panel shows the rationale and the proposed diff, labelled.
    assert "Rationale: model-written (untrusted)" in cand_panel
    assert (
        "Proposed diff (untrusted; control characters shown as escapes)" in cand_panel
    )
    diff = (run / "proposals" / "r1.diff").read_text(encoding="utf-8")
    assert all(line in cand_panel for line in diff.splitlines()[2:8] if line.strip())


def test_the_headline_and_fail_rows_equal_the_report(finished):
    page, _run, report, _ = finished
    headline = text(page, "headline-original")
    assert report["scientific_outcomes"]["original"] == "VIOLATION_FOUND"
    assert "VIOLATION_FOUND" in headline
    assert "The evaluation breaks at least one requirement of this claim." in headline
    assert "This does not say the scientific claim is true or false." in headline
    required = report["comparison"]["original"]["required_set"]
    shown = table_rows(page, "finding-checks")
    assert [r[:2] for r in shown if r[0] == "FAIL"] == [
        ["FAIL", r["assertion_id"]] for r in required if r["status"] == "FAIL"
    ]
    assert len(shown) == len(required)
    assert "4 of 9 required checks FAIL" in text(page, "finding-counts")


def test_the_evidence_and_independent_metric_match_outcome_json(finished):
    page, run, _report, _ = finished
    page.get_by_text("Check details: observed values, limitations, evidence").click()
    page.get_by_text("FAIL split.no_group_overlap").click()
    shot(page, "s1_04_evidence")
    outcome = json.loads(
        (run / "original" / "outcome.json").read_text(encoding="utf-8")
    )
    metric = next(
        d
        for d in outcome["descriptive"]
        if d["result_id"] == "metric.recomputed_primary"
    )["observed"]
    pooled = metric["aggregates"]["development_eval"][metric["primary_metric"]][
        "pooled"
    ]
    shown = text(page, "finding-metric")
    assert metric["primary_metric"] in shown
    assert f"{pooled['value']:.4f}" in shown
    assert f"Pooled, {pooled['observations']} evaluated rows" in shown
    assert "Descriptive only; never part of the outcome." in shown


def test_the_diff_shown_is_the_persisted_file_with_its_hash(finished):
    page, run, report, _ = finished
    page.locator(".st-key-card-revision").scroll_into_view_if_needed()
    shot(page, "s1_05_revision")
    (record,) = report["proposals"]
    assert record["outcome"] == "executed"
    shown = text(page, "proposal-1")
    data = (run / record["diff_path"]).read_bytes()
    assert sha(data) == record["diff_sha256"]
    assert f"SHA-256 {record['diff_sha256']}" in shown and "matches" in shown
    assert "model-written (untrusted)" in shown
    assert "1 proposal: 0 rejected by validation, 0 declined, 1 executed" in text(
        page, "proposal-summary"
    )
    rationale = text(page, "model-rationale-1")
    assert "model-written" in rationale and LABEL in rationale
    assert report["model_text"][0]["label"] == LABEL


def test_the_comparison_rows_equal_status_by_assertion(finished):
    page, run, report, _ = finished
    page.locator(".st-key-card-comparison").scroll_into_view_if_needed()
    shot(page, "s1_06_comparison")
    cand = report["comparison"]["candidates"][0]
    rows = table_rows(page, "status-changes-1")
    expected = [
        [
            s["assertion_id"],
            s["original"],
            s["candidate"],
            f"{s['original']} → {s['candidate']}"
            if s["original"] != s["candidate"]
            else "unchanged",
        ]
        for s in cand["status_by_assertion"]
    ]
    assert rows == expected
    side = text(page, "scroll-comparison-1")
    assert (
        report["comparison"]["comparison_basis"]
        in page.locator(".st-key-card-comparison").inner_text()
    )
    cand_outcome = json.loads(
        (run / "candidates" / "c1" / "outcome.json").read_text(encoding="utf-8")
    )
    m = next(
        d
        for d in cand_outcome["descriptive"]
        if d["result_id"] == "metric.recomputed_primary"
    )["observed"]
    value = m["aggregates"]["development_eval"][m["primary_metric"]]["pooled"]["value"]
    assert f"{value:.4f}" in side
    assert "NO_VIOLATION_FOUND" in side and "VIOLATION_FOUND" in side


def test_banner_cost_and_export_hashes(finished):
    page, run, report, _ = finished
    banner = text(page, "banner")
    assert "NON-LIVE RUN" in banner and report["banner"] in banner
    assert "LIVE RUN" not in banner.replace("NON-LIVE RUN", "")
    page.locator(".st-key-card-trust").scroll_into_view_if_needed()
    shot(page, "s1_07_trust_export")
    cost = text(page, "cost")
    assert "Estimated cost (not a bill)" in cost
    assert report["cost"]["reason"] in cost
    with page.expect_download() as download:
        page.get_by_role("button", name="Download agent_report.json").click()
    exported = download.value.path().read_bytes()
    on_disk = (run / "agent_report.json").read_bytes()
    assert sha(exported) == sha(on_disk)
    assert sha(on_disk) in text(page, "export")
    rows = {r[0]: r for r in table_rows(page, "export")}
    assert rows["agent_log.jsonl"][2] == "matches"
    assert rows["original/outcome.json"][2] == "matches"
    assert rows["candidates/c1/outcome.json"][2] == "matches"


def test_the_documented_css_hooks_apply(finished):
    """UI_DESIGN_HUD §2 and UI_SPEC §12: panel cards and the inset model-written frame, via
    st-key-* only."""
    page, *_ = finished
    style = "el => getComputedStyle(el).backgroundColor"
    assert page.locator(".st-key-card-finding").evaluate(style) == "rgb(15, 23, 32)"
    assert (
        page.locator(".st-key-model-rationale-1").evaluate(style) == "rgb(10, 15, 20)"
    )
    red = (
        page.locator(".st-key-headline-original h2")
        .get_by_text("VIOLATION_FOUND", exact=True)
        .evaluate("el => getComputedStyle(el).color")
    )
    assert red == "rgb(248, 113, 113)"  # #F87171, always next to the printed code
