"""Scenario 6 (UI_SPEC §9) and the remaining label checks.

A double-click on "Confirm & run" starts exactly one run; a refresh during a run reattaches
without starting another; results after a project change are labelled stale. A wrong prefix
declines and nothing executes. The phone viewport keeps the main path usable.
"""

import json
import time

from helpers import (
    answer,
    click_run,
    open_app,
    select_mode,
    select_project,
    select_script,
    shot,
    shown_hash,
    text,
    wait_finished,
)


def test_double_click_refresh_and_stale_label(app, docker, page):
    open_app(page, app)
    select_project(page, "s01_faulty")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    select_script(page, "Inspect only, no revision")
    before = len(app.agent_runs("s01_faulty"))
    click_run(page, double=True)
    first = shown_hash(page, None)
    time.sleep(2)
    assert len(app.agent_runs("s01_faulty")) == before + 1  # exactly one run
    shot(page, "s6_01_running_approval")
    # A refresh reattaches to the same pending request; no second run starts.
    page.reload()
    assert shown_hash(page, None) == first
    assert len(app.agent_runs("s01_faulty")) == before + 1
    answer(page, first[:12])
    wait_finished(page, app)
    run = app.agent_runs("s01_faulty")[-1]
    report = json.loads((run / "agent_report.json").read_text(encoding="utf-8"))
    label = text(page, "results-label")
    assert run.name in label and "finished" in label
    # A different project: the shown results are labelled stale until a new run finishes.
    select_project(page, "s02_clean")
    shot(page, "s6_02_stale_label")
    stale = page.get_by_text("Results below are from a different project (s01_faulty)")
    assert stale.is_visible()
    assert "from a different project: s01_faulty" in text(page, "results-label")
    assert report["terminal_state"] == "REPORT"


def test_a_wrong_prefix_declines_and_nothing_executes(app, docker, page):
    open_app(page, app)
    select_project(page, "s01_faulty")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    select_script(page, "Propose a grouped, fold-local revision")
    click_run(page)
    original = shown_hash(page, None)
    answer(page, original[:12])
    candidate = shown_hash(page, original)
    answer(page, candidate[:11])  # eleven characters: not the 12-character prefix
    wait_finished(page, app)
    run = app.agent_runs("s01_faulty")[-1]
    report = json.loads((run / "agent_report.json").read_text(encoding="utf-8"))
    (record,) = report["proposals"]
    assert (record["outcome"], record["code"]) == ("declined", "confirmation_mismatch")
    assert report["comparison"]["candidates"] == []
    assert not (run / "candidates").exists() or not any((run / "candidates").iterdir())
    assert (
        "Confirmation did not match: NOT approved."
        in page.locator(".st-key-card-analysis").inner_text()
    )
    assert "declined" in text(page, "proposal-1")


def test_phone_viewport_keeps_the_main_path_reachable(app, docker, browser):
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True
    )
    page = context.new_page()
    open_app(page, app)
    shot(page, "phone_01_claim")
    # The rail is collapsed into a menu; the primary action stays reachable without it.
    rail = page.get_by_test_id("stSidebar")
    assert rail.bounding_box()["width"] == 0  # collapsed off-canvas
    page.get_by_test_id("stExpandSidebarButton").click()
    rail.get_by_text("s01_faulty", exact=True).click()
    shot(page, "phone_01b_menu")
    page.get_by_test_id("stSidebarHeader").get_by_role("button").last.click()
    page.wait_for_function(
        "document.querySelector('[data-testid=stSidebar]').getBoundingClientRect().right <= 1"
    )
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    select_script(page, "Propose a grouped, fold-local revision")
    click_run(page)
    previous = None
    for i in range(2):
        previous = shown_hash(page, previous)
        shot(page, f"phone_02_approval_{i}")
        answer(page, previous[:12])
    wait_finished(page, app)
    shot(page, "phone_03_result")
    for key in ("card-finding", "card-comparison", "card-trust"):
        page.locator(f".st-key-{key}").scroll_into_view_if_needed()
        shot(page, f"phone_04_{key}")
    width = page.evaluate("document.documentElement.scrollWidth")
    assert (
        width <= 390 + 1
    )  # no page-level horizontal scroll; wide content scrolls inside
    run = app.agent_runs("s01_faulty")[-1]
    report = json.loads((run / "agent_report.json").read_text(encoding="utf-8"))
    assert report["terminal_state"] == "REPORT"
    assert report["scientific_outcomes"]["original"] in text(page, "headline-original")
    context.close()
