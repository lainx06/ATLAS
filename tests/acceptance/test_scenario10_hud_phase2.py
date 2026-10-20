"""Scenario 10 (UI design pass, phase 2): the HUD on every local view, in the browser.

Recorded runs (copies of the bundled live run 6 and HAR flawed, plus a changed copy) show the
briefing first, the drill-down opened by keyboard, the BUDGET_EXHAUSTED state and the
evidence-changed panel. A run on the page (fixture replies, the real Docker runner) shows the
claim, the typed-approval panel (both hashes in full, the model-written frame, the decision;
its keyboard order), the running track, the finished run's briefing and HUD; and the failure
states NEEDS_INPUT, ERROR, NOT_SUPPORTED and INCONCLUSIVE. With ATLAS_UI_SCREENS set, every
state is saved settled at 1440 x 900, 1280 x 800 and 390 x 844, with the tab orders, and a
video of live run 6's first load.
"""

import contextlib
import json
import os
import re
import shutil
import time
from pathlib import Path

import pytest
from helpers import (
    FOCUSED,
    answer,
    click_run,
    open_app,
    select_mode,
    select_project,
    select_script,
    shots,
    shown_hash,
    tab_order,
    text,
    wait_finished,
    wait_idle,
)
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from atlas.ui import hud as H

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR = "ui/agent-har_flawed-1e2267f662c0"
TAMPERED = "live6-changed/agent-s01_faulty-877f8245a8a2"
KEYBOARD: dict[str, list[str]] = {}


def app_env(base: Path) -> dict:
    recorded = base / "recorded"
    shutil.copytree(BUNDLE / LIVE6, recorded / LIVE6)
    shutil.copytree(BUNDLE / "t09" / Path(HAR).name, recorded / HAR)
    shutil.copytree(BUNDLE / LIVE6, recorded / TAMPERED)
    target = recorded / TAMPERED / "candidates" / "c1" / "outcome.json"
    target.write_bytes(target.read_bytes().replace(b"PASS", b"PAS5", 1))
    return {"ATLAS_UI_RECORDED_DIR": str(recorded)}


def save_keyboard() -> None:
    folder = os.environ.get("ATLAS_UI_SCREENS")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / "keyboard_tab_order.json").write_text(
            json.dumps(KEYBOARD, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def open_recorded(page, app, label: str) -> None:
    page.goto(app.url)
    page.get_by_role("button", name="Confirm & run").wait_for(timeout=60_000)
    page.get_by_test_id("stSidebar").get_by_text(
        "Open a recorded run", exact=True
    ).click()
    box = page.get_by_role("combobox", name="Recorded run")
    box.wait_for()
    wait_idle(page)
    box.click()
    page.get_by_role("option", name=f"{label} (agent)", exact=True).click()
    page.locator(".st-key-card-integrity").wait_for(timeout=30_000)
    wait_idle(page)


# -- recorded runs -------------------------------------------------------------------------------
def test_the_briefing_and_the_drill_down_on_recorded_runs(app, page):
    open_recorded(page, app, LIVE6)
    brief = page.locator(".st-key-hud-briefing")
    brief.wait_for()
    shown = brief.inner_text()
    for line in (
        "Evidence intact: 46 of 46 recorded hashes verified now.",
        "Revision candidates/c1, executed and verified: NO_VIOLATION_FOUND; 4 FAIL → PASS.",
        "Balanced accuracy (pooled), descriptive only: original 0.6812, candidate 0.6750.",
        "This does not say the scientific claim is true or false.",
    ):
        assert line in shown, line
    assert "split.no_group_overlap (FAIL): No group_id value" in shown
    box = brief.bounding_box()
    hero = page.locator(".st-key-hud-hero").bounding_box()
    assert box["y"] + box["height"] <= hero["y"]  # the briefing comes first
    shots(page, "p2_01_briefing_live6")

    # The drill-down by keyboard: focus the first FAIL tile, Enter opens, Space closes.
    summary = page.locator(".hud-pane-orig summary.hud-tile-row").first
    summary.scroll_into_view_if_needed()
    page.locator(".hud-pane-orig .hud-scroll").first.focus()
    KEYBOARD["drill-down (from the original leak map's scroll region)"] = tab_order(
        page, 4
    )
    summary.focus()
    assert page.evaluate(FOCUSED).startswith("summary")
    outline = summary.evaluate("e => getComputedStyle(e).outlineStyle")
    assert outline == "solid"  # the visible focus ring (2 px accent)
    page.keyboard.press("Enter")
    frame = page.locator(".hud-pane-orig .hud-insp-frame").first
    frame.wait_for()
    assert summary.evaluate("e => e.parentElement.open") is True
    body = frame.inner_text()
    assert "split_integrity.json" in body and "8 items: S01; S02" in body
    assert "and 2 more" in body
    assert re.search(r"[0-9a-f]{64}", re.sub(r"\s", "", body))  # full sha256, wrapped
    shots(page, "p2_02_drilldown_open_live6", frame)
    page.keyboard.press("Space")
    time.sleep(0.3)
    assert summary.evaluate("e => e.parentElement.open") is False

    # The run's own terminal state: BUDGET_EXHAUSTED, amber, with a next action.
    terminal = page.locator(".st-key-terminal")
    assert "BUDGET_EXHAUSTED" in terminal.inner_text()
    assert "Next action:" in terminal.inner_text()
    shots(page, "p2_03_state_budget_exhausted", terminal)

    # HAR flawed: its briefing and its NOT_ASSESSED drill-down.
    open_recorded(page, app, HAR)
    shown = page.locator(".st-key-hud-briefing").inner_text()
    assert "Required checks: 4 FAIL, 1 NOT_ASSESSED, 0 ERROR (of 11)." in shown
    assert "Revision" not in shown
    shots(page, "p2_04_briefing_har_flawed")
    tile = page.locator("summary.hud-tile-row", has_text="split.no_window_overlap")
    tile.scroll_into_view_if_needed()
    tile.click()
    page.locator(".hud-insp[open] .hud-insp-frame").wait_for()
    shots(page, "p2_05_drilldown_open_har_flawed", page.locator(".hud-insp[open]"))
    save_keyboard()


def test_a_changed_copy_shows_the_evidence_changed_state(app, page):
    open_recorded(page, app, TAMPERED)
    failed = text(page, "integrity-failed")
    assert "EVIDENCE CHANGED" in failed and "evidence changed since recording" in failed
    assert "Next action:" in failed
    assert page.locator(".st-key-hud-briefing").count() == 0
    shots(page, "p2_06_state_evidence_changed")


def test_live6_first_load_motion_capture(app, browser):
    folder = os.environ.get("ATLAS_UI_SCREENS")
    if not folder:
        pytest.skip("motion capture is evidence only (ATLAS_UI_SCREENS)")
    video = Path(folder) / "video_live6_load"
    context = browser.new_context(
        viewport={"width": 1440, "height": 900}, record_video_dir=str(video)
    )
    page = context.new_page()
    open_recorded(page, app, LIVE6)
    page.locator(".hud-ret").first.wait_for()
    start = time.time()
    for at in (0.05, 0.3, 0.6, 1.0, 1.5):
        time.sleep(max(0.0, at - (time.time() - start)))
        page.screenshot(
            path=str(
                Path(folder)
                / f"p2_07_motion_live6_t{int(at * 1000):04d}ms_1440x900.png"
            )
        )
    context.close()


# -- a run on the page ----------------------------------------------------------------------------
def test_a_run_through_the_page(app, docker, page):
    open_app(page, app)
    select_project(page, "s01_faulty")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    select_script(page, "Propose a grouped, fold-local revision")
    shots(page, "p2_10_claim")
    click_run(page)
    previous = None
    for kind in ("original", "candidate"):
        full = shown_hash(page, previous)
        panel = page.locator(".st-key-approval-panel")
        shown = re.sub(
            r"\s", "", page.locator(".st-key-approval-code-hash").inner_text()
        )
        assert full in shown  # all 64 characters, never truncated
        assert page.locator(".hud-hash").count() == 2
        assert (
            page.locator(".hud-hash").first.evaluate("e => getComputedStyle(e).color")
            == "rgb(226, 232, 240)"  # the neutral text colour
        )
        if kind == "candidate":
            frame = page.locator(".st-key-model-approval-diff")
            assert "MODEL-WRITTEN · UNTRUSTED" in frame.inner_text()
            assert frame.evaluate("e => getComputedStyle(e).borderTopStyle") == "dashed"
        decision = page.locator(".st-key-approval-decision")
        assert decision.evaluate("e => getComputedStyle(e).backgroundColor") == (
            "rgb(10, 15, 20)"
        )
        time.sleep(0.5)
        shots(page, f"p2_11_approval_{kind}", panel)
        # The keyboard order from the request to the decision (nothing is typed or sent).
        page.locator(".st-key-approval-code-hash").click()
        KEYBOARD[f"approval panel ({kind}), from the code hash"] = tab_order(page, 6)
        answer(page, full[:12])
        previous = full
        if kind == "original":
            with contextlib.suppress(PlaywrightTimeout):  # the window lasts seconds
                page.locator(".st-key-hud-track").wait_for(timeout=15_000)
                shots(page, "p2_12_running_track", page.locator(".st-key-hud-track"))
    run = wait_finished(page, app)
    report = json.loads((run / "agent_report.json").read_text(encoding="utf-8"))
    assert report["scientific_outcomes"]["candidates"] == ["NO_VIOLATION_FOUND"]
    brief = page.locator(".st-key-hud-briefing")
    assert "executed and verified: NO_VIOLATION_FOUND" in brief.inner_text()
    assert page.locator(".hud-ret").count() == 2
    shots(page, "p2_13_finished_briefing_hero", page.locator(".st-key-hud-page h1"))
    shots(page, "p2_14_finished_track_gauge", page.locator(".st-key-hud-track"))
    shots(page, "p2_15_finished_revision", page.locator(".st-key-card-revision"))
    shots(page, "p2_16_finished_comparison", page.locator(".st-key-card-comparison"))
    shots(page, "p2_17_finished_trust_export", page.locator(".st-key-export"))
    save_keyboard()


def test_needs_input_and_error(app, docker, page):
    open_app(page, app)
    select_project(page, "s01_faulty")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    select_script(page, "Provider timeout")
    click_run(page)
    h = shown_hash(page, None)
    answer(page, h[:12])
    wait_finished(page, app)
    terminal = text(page, "terminal")
    assert "ERROR" in terminal and "Next action:" in terminal
    color = page.locator(
        ".st-key-terminal [class*='st-key-state-violet-']"
    ).first.evaluate("e => getComputedStyle(e).borderLeftColor")
    assert color == "rgb(192, 132, 252)"  # violet: ERROR, never success styling
    shots(page, "p2_20_state_error", page.locator(".st-key-terminal"))
    click_run(page, "Start a new run")
    shown_hash(page, None)
    page.get_by_role("button", name="Close without deciding").click()
    wait_finished(page, app)
    terminal = text(page, "terminal")
    assert "NEEDS_INPUT" in terminal and "Next action:" in terminal
    shots(page, "p2_21_state_needs_input", page.locator(".st-key-terminal"))


def test_not_supported_and_inconclusive(app, page):
    open_app(page, app)
    select_project(page, "s08a_combined_claim")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    click_run(page)
    wait_finished(page, app)
    block = text(page, "not-supported")
    assert "NOT_SUPPORTED" in block and "Next action:" in block
    shots(page, "p2_22_state_not_supported", page.locator(".st-key-not-supported"))
    select_project(page, "s06_missing_metadata")
    select_mode(page, "Deterministic audit: no model")
    click_run(page)
    wait_finished(page, app)
    assert "INCONCLUSIVE" in text(page, "headline-original")
    assert page.locator(".st-key-hud-briefing").count() == 1  # an audit run, verified
    coverage = page.locator("[class*='st-key-state-amber-coverage']")
    assert "incomplete_coverage" in coverage.inner_text()
    assert "Next action:" in coverage.inner_text()
    shots(page, "p2_23_state_inconclusive", page.locator(".st-key-headline-original"))
    shots(page, "p2_24_audit_briefing", page.locator(".st-key-hud-briefing"))


def test_no_page_scrolls_sideways_at_phone_width(app, page):
    page.set_viewport_size({"width": 390, "height": 844})
    open_app(page, app)
    width = page.evaluate("() => [document.documentElement.scrollWidth, innerWidth]")
    assert width[0] <= width[1]
    assert H.CSS  # the HUD stylesheet is loaded with the page
