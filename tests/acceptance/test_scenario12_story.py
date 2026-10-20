"""Scenario 12 (UI restructure slice 1): the Overview & Cases story in the browser (hosted).

ATLAS_HOSTED=1 with the live kill switch off; the bundled runs in demo/recorded are only
read. Each case card opens its case; the five steps are native expanders, operable by
keyboard; the compact leak map fits without clipping at 1280 x 800 and keeps its scroll
region at 390 px; no element ID repeats in the document. With ATLAS_UI_SCREENS set, settled
full-page screenshots (top to bottom) are saved at 1440 x 900, 1280 x 800 and 390 x 844.
"""

import os
import time
from pathlib import Path

import pytest
from helpers import settle, wait_idle

from atlas.ui import copy as C

SIZES = ((1440, 900), (1280, 800), (390, 844))
TITLES = {c.key: c.title for c in C.CASES}


def app_env(base: Path) -> dict:
    return {
        "ATLAS_HOSTED": "1",
        "HOSTED_LIVE_ENABLED": "false",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "hosted-runs"),
    }


def full_page(page, name: str) -> list[str]:
    """Settled full-page screenshots at the three sizes: the viewport is grown to the
    page's own height for each capture, then restored."""
    folder = os.environ.get("ATLAS_UI_SCREENS")
    if not folder:
        return []
    Path(folder).mkdir(parents=True, exist_ok=True)
    names = []
    for w, h in SIZES:
        page.set_viewport_size({"width": w, "height": h})
        time.sleep(0.6)
        settle(page)
        height = page.evaluate(
            "() => Math.max(...[...document.querySelectorAll("
            "'[data-testid=stMain], [data-testid=stAppViewContainer], body')]"
            ".map(e => e.scrollHeight))"
        )
        page.set_viewport_size({"width": w, "height": max(h, height)})
        time.sleep(0.6)
        settle(page)
        names.append(f"{name}_{w}x{h}.png")
        page.screenshot(path=str(Path(folder) / names[-1]))
        page.set_viewport_size({"width": w, "height": h})
    page.set_viewport_size({"width": 1440, "height": 900})
    time.sleep(0.4)
    return names


def open_overview(page, app, case: str | None = None) -> None:
    page.goto(app.url)
    page.locator(".st-key-verdict-bar").wait_for(timeout=60_000)
    wait_idle(page)
    if case is not None and case != "live6":
        page.get_by_role("button", name=TITLES[case], exact=True).click()
        page.locator(f".st-key-case-card-on-{case}").wait_for(timeout=30_000)
        page.locator(".st-key-verdict-bar").wait_for(timeout=30_000)
        wait_idle(page)


def is_open(page, n: int) -> bool:
    step = page.locator(
        f".st-key-step-{n} details"
    ).first  # the step itself, not a nested one
    return step.get_attribute("open") is not None


def toggle_step(page, n: int, want: bool) -> None:
    if is_open(page, n) != want:
        page.locator(f".st-key-step-{n} summary").first.click()
        page.wait_for_function(
            f"() => document.querySelector('.st-key-step-{n} details').open === {str(want).lower()}"
        )
        time.sleep(0.3)


def duplicate_ids(page) -> list[str]:
    return page.evaluate(
        """() => { const seen = {}, dup = [];
        for (const e of document.querySelectorAll('[id]')) {
            if (seen[e.id]) dup.push(e.id); seen[e.id] = 1; }
        return dup; }"""
    )


@pytest.mark.parametrize("case", list(TITLES))
def test_each_case_opens_with_step_2_and_fits(app, page, case):
    open_overview(page, app, case)
    assert [is_open(page, n) for n in range(1, 6)] == [False, True, False, False, False]
    assert page.locator("[class*='st-key-case-card-on-']").count() == 1
    assert duplicate_ids(page) == []
    # The compact leak map fits its pane without clipping at 1280 x 800.
    page.set_viewport_size({"width": 1280, "height": 800})
    time.sleep(0.8)
    regions = page.locator(".hud-pane-orig .hud-scroll")
    assert regions.count() == 1
    sizes = regions.evaluate_all("els => els.map(e => [e.scrollWidth, e.clientWidth])")
    assert all(sw <= cw for sw, cw in sizes), sizes
    squares = page.locator(".hud-pane-orig .hud-sq").evaluate_all(
        "els => els.map(e => e.getBoundingClientRect().width)"
    )
    assert all(14 <= w <= 16 for w in squares), set(squares)
    assert bool(squares) is (case != "harclean")  # the clean case lists no group
    # At 390 px the map keeps its keyboard-reachable scroll region; no page-level scroll.
    page.set_viewport_size({"width": 390, "height": 844})
    time.sleep(0.8)
    region = page.locator(".hud-pane-orig .hud-scroll")
    assert region.get_attribute("role") == "region"
    assert region.get_attribute("tabindex") == "0"
    width = page.evaluate("() => [document.documentElement.scrollWidth, innerWidth]")
    assert width[0] <= width[1], width
    page.set_viewport_size({"width": 1440, "height": 900})
    time.sleep(0.4)
    full_page(page, f"s12_01_overview_{case}")


def test_the_case_cards_and_collapsed_steps_are_keyboard_operable(app, page):
    open_overview(page, app)
    # A case card's title button takes focus and Enter opens the case.
    button = page.get_by_role("button", name=TITLES["harclean"], exact=True)
    button.focus()
    page.keyboard.press("Enter")
    page.locator(".st-key-case-card-on-harclean").wait_for(timeout=30_000)
    wait_idle(page)
    # A collapsed step's header is focusable and Enter / Space toggle it.
    summary = page.locator(".st-key-step-3 summary").first
    summary.focus()
    assert page.evaluate("() => document.activeElement.tagName") == "SUMMARY"
    assert not is_open(page, 3)
    page.keyboard.press("Enter")
    page.wait_for_function(
        "() => document.querySelector('.st-key-step-3 details').open"
    )
    page.keyboard.press(" ")
    page.wait_for_function(
        "() => !document.querySelector('.st-key-step-3 details').open"
    )
    # The whole card is the click target (the stretched title button covers it).
    page.locator(".st-key-case-card-live6").scroll_into_view_if_needed()
    box = page.locator(".st-key-case-card-live6").bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] - 8)
    page.locator(".st-key-case-card-on-live6").wait_for(timeout=30_000)


def test_each_step_of_live6_and_expert_view(app, page):
    open_overview(page, app)
    toggle_step(page, 2, False)
    for n in range(1, 6):
        toggle_step(page, n, True)
        page.locator(f".st-key-step-{n}").scroll_into_view_if_needed()
        assert duplicate_ids(page) == []
        full_page(page, f"s12_02_live6_step{n}")
        toggle_step(page, n, False)
    # Expert view: one session-wide switch; the full banner and the run-relative sources.
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    wait_idle(page)
    page.locator(".st-key-banner").get_by_text("LIVE RUN", exact=True).wait_for()
    for n in range(1, 6):
        toggle_step(page, n, True)
    body = page.locator("body").inner_text()
    assert "original/outcome.json" in body and "Estimated cost (not a bill)" in body
    assert duplicate_ids(page) == []
    full_page(page, "s12_03_live6_expert")


def test_try_it_live_and_the_slice_2_pages(app, page):
    open_overview(page, app)
    page.get_by_role("link", name=C.PAGE_LIVE).click()
    state = page.locator(".st-key-live-unavailable")
    state.wait_for(timeout=30_000)
    assert "LIVE UNAVAILABLE" in state.inner_text()
    assert page.get_by_role("button", name="Start the live session").count() == 0
    full_page(page, "s12_04_try_it_live_unavailable")
    for title, name in (
        (C.PAGE_AGENT, "agent_vs_model"),
        (C.PAGE_LIMITS, "how_it_works"),
    ):
        page.get_by_role("link", name=title).click()
        page.locator(
            ".st-key-vs-chart" if name == "agent_vs_model" else ".st-key-lim-limits"
        ).wait_for()
        wait_idle(page)
        full_page(page, f"s12_05_{name}")
