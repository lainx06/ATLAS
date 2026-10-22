"""Scenario 18 (final UI fix pass, 2026-10-22), in the browser.

Hosted (ATLAS_HOSTED=1, live kill switch off), the cases read from a copy of demo/recorded
(ATLAS_UI_CASES_DIR); demo/recorded is only read.

- F1 (user-found): inside the stepper (a fragment), "Show expert detail" and "Show me the
  evidence" set Expert view in their callback, but only the fragment reran, so the page and the
  Expert view toggle stayed in plain view. Now the click reruns the whole app: on every step of
  live6 and har_flawed, clicking the step's button leaves the toggle checked and the Expert
  view content shown (the five step expanders and the full banner).
- F6: the comparison page's three stat tiles share one height (within 2 px) where they sit
  side by side (1920 x 1080, 1440 x 900; at 390 x 844 they stack), and each caption sits
  directly under its own metric.
- F7: on every step of every case, the headline is above the visual.

With ATLAS_UI_SCREENS set, settled full-page screenshots are saved at 1440 x 900 and 390 x 844.
"""

import os
import shutil
import time
from pathlib import Path

import pytest
from helpers import settle, wait_idle
from test_scenario12_story import go_step, open_more, open_overview

from atlas.ui import copy as C

ROOT = Path(__file__).resolve().parents[2]
SIZES = ((1440, 900), (390, 844))


def app_env(base: Path) -> dict:
    cases = base / "cases"
    shutil.copytree(ROOT / "demo" / "recorded", cases)
    return {
        "ATLAS_HOSTED": "1",
        "HOSTED_LIVE_ENABLED": "false",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "hosted-runs"),
        "ATLAS_UI_CASES_DIR": str(cases),
    }


def toggle_on(page) -> bool:
    toggle = page.locator(".st-key-expert_widget input").first
    toggle.wait_for(state="attached", timeout=60_000)
    return toggle.is_checked()


def goto(page, app, path: str, wait: str) -> None:
    page.goto(app.url + path)
    page.locator(wait).first.wait_for(timeout=60_000)
    wait_idle(page)
    settle(page)


# -- F1 ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("case", ["live6", "harflawed"])
def test_a_stepper_expert_button_turns_expert_view_on(app, page, case, n):
    open_overview(page, app, case)
    if n != 2:
        go_step(page, n)
    assert not toggle_on(page)
    open_more(page, n)
    label = C.SHOW_EVIDENCE if n == 2 else C.SHOW_EXPERT
    more = page.locator(f".st-key-stepper-more-{n}")
    assert more.get_by_role("button", name=label, exact=True).count() == 1
    more.get_by_role("button", name=label, exact=True).click()
    # Expert view: the five step expanders replace the stepper; the banner is the full one.
    page.locator(".st-key-step-5").wait_for(timeout=30_000)
    page.locator(".st-key-stepper").wait_for(state="detached", timeout=30_000)
    wait_idle(page)
    assert toggle_on(page)
    assert page.locator(".st-key-stepper").count() == 0
    banner = page.locator(".st-key-banner").inner_text()
    assert "LIVE RUN" in banner or "NON-LIVE RUN" in banner
    assert "Replay: these are recorded runs" in banner  # F2: Expert view's banner
    # The switch still works both ways afterwards.
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    page.locator(".st-key-stepper").wait_for(timeout=30_000)
    wait_idle(page)
    assert not toggle_on(page)


# -- F6 ------------------------------------------------------------------------------------------------
def test_the_stat_tiles_share_one_height_and_captions_sit_under_their_metric(app, page):
    goto(page, app, "/agent_vs_model", ".st-key-vs-tiles")
    for w, h in ((1920, 1080), (1440, 900), (390, 844)):
        page.set_viewport_size({"width": w, "height": h})
        time.sleep(0.8)
        settle(page)
        boxes = page.evaluate(
            """() => [0, 1, 2].map(i => {
                const r = document.querySelector('.st-key-vs-tile-' + i)
                    .getBoundingClientRect();
                return {top: r.top, height: r.height}; })"""
        )
        if w >= 1000:  # side by side: one row, one height
            assert max(b["top"] for b in boxes) - min(b["top"] for b in boxes) <= 2, (
                boxes
            )
            heights = [b["height"] for b in boxes]
            assert max(heights) - min(heights) <= 2, (w, heights)
        pairs = page.evaluate(
            """() => [...document.querySelectorAll('[class*="st-key-vs-side-"]')]
              .filter(s => s.querySelector('[data-testid="stCaptionContainer"]'))
              .map(s => {
                const m = s.querySelector('[data-testid="stMetric"]').getBoundingClientRect();
                const c = s.querySelector('[data-testid="stCaptionContainer"]')
                    .getBoundingClientRect();
                return {ml: m.left, cl: c.left, gap: c.top - m.bottom}; })"""
        )
        assert len(pairs) == 2, (w, pairs)
        for p in pairs:
            assert abs(p["ml"] - p["cl"]) <= 1, (w, p)
            assert -1 <= p["gap"] <= 8, (w, p)
    page.set_viewport_size({"width": 1440, "height": 900})


# -- F7 ------------------------------------------------------------------------------------------------
VISUALS = (
    ".st-key-concept-groups, .st-key-hud-evidence, .st-key-analogies, .st-key-stepper-chips, "
    ".st-key-concept-sealed, .st-key-stepper-outcomes"
)


@pytest.mark.parametrize("case", ["live6", "harflawed", "harclean"])
def test_on_every_step_the_headline_sits_above_the_visual(app, page, case):
    open_overview(page, app, case)
    for n in range(1, 6):
        go_step(page, n)
        tops = page.evaluate(
            """([n, sel]) => {
              const body = document.querySelector('.st-key-stepper-body-' + n);
              const head = body.querySelector('.st-key-stepper-headline, .st-key-no-proposal');
              return {head: head.getBoundingClientRect().bottom,
                      visuals: [...body.querySelectorAll(sel)]
                        .map(e => e.getBoundingClientRect().top)}; }""",
            [n, VISUALS],
        )
        assert all(top >= tops["head"] - 1 for top in tops["visuals"]), (case, n, tops)
        if n == 4:
            assert tops["visuals"], (case, n)  # the sealed-run diagram


# -- evidence: screenshots -----------------------------------------------------------------------------
def shots(page, name: str) -> None:
    folder = os.environ.get("ATLAS_UI_SCREENS")
    if not folder:
        return
    Path(folder).mkdir(parents=True, exist_ok=True)
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
        page.screenshot(path=str(Path(folder) / f"{name}_{w}x{h}.png"))
        page.set_viewport_size({"width": w, "height": h})
    page.set_viewport_size({"width": 1440, "height": 900})
    time.sleep(0.4)


def test_screens(app, page):
    if not os.environ.get("ATLAS_UI_SCREENS"):
        return
    open_overview(page, app)
    for n in (2, 3, 4):
        go_step(page, n)
        shots(page, f"s18_01_overview_live6_step{n}")
    go_step(page, 1)
    open_more(page, 1)
    page.locator(".st-key-stepper-more-1").get_by_role(
        "button", name=C.SHOW_EXPERT, exact=True
    ).click()
    page.locator(".st-key-step-5").wait_for(timeout=30_000)
    wait_idle(page)
    assert toggle_on(page)
    shots(page, "s18_02_overview_live6_after_show_expert_detail")
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    page.locator(".st-key-stepper").wait_for(timeout=30_000)
    wait_idle(page)
    open_overview(page, app, "harflawed")
    shots(page, "s18_03_harflawed_step2")
    open_overview(page, app, "harclean")
    go_step(page, 5)
    shots(page, "s18_04_harclean_step5")
    goto(page, app, "/agent_vs_model", ".st-key-vs-chart")
    shots(page, "s18_05_agent_vs_model_plain")
    goto(page, app, "/how_it_works", ".st-key-lim-key-limits")
    shots(page, "s18_06_how_it_works_plain")
