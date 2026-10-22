"""Scenario 17 (readability pass, 2026-10-21): headline first, one idea per screen, in the browser.

Hosted (ATLAS_HOSTED=1, live kill switch off), with the cases read from a copy of demo/recorded
(ATLAS_UI_CASES_DIR), so one test can change a byte in it; demo/recorded is only read.

- The stepper: opens on step 2; the step row, Back and Next move it by mouse and keyboard;
  "Step n of 5" is shown in a polite live region; every control shows its focus.
- Word counts of plain view at 1440 x 900 (closed expanders and popovers excluded): recorded,
  and held at or under the counts measured for this pass (`WORDS`; the requested ceilings are
  not met, see docs/UI_DESIGN_HUD.md §16.5).
- The stat tiles: no value or caption truncated at 1920 x 1080, 1440 x 900 and 390 x 844.
- The always-visible items need no click.
- Verification is never cached, the stepper's own runs included: a byte changed between two
  full renders, or before a click on Next inside the stepper, leaves only the
  evidence-changed panel.

With ATLAS_UI_SCREENS set, settled full-page screenshots are saved at 1920 x 1080, 1440 x 900
and 390 x 844; with ATLAS_UI_WORDS set, the word counts (JSON) and the measured text.
"""

import json
import os
import shutil
import time
from pathlib import Path

from helpers import settle, wait_idle
from test_scenario12_story import go_step, open_more, open_overview, step_now

from atlas.ui import copy as C

ROOT = Path(__file__).resolve().parents[2]
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
SIZES = ((1920, 1080), (1440, 900), (390, 844))
CASES_DIR: dict[str, Path] = {}
# Measured (closed expanders and popovers excluded); the readability pass's ceilings were
# 220 (Overview, both measures), 140 (comparison) and 230 (limits). Final fix pass
# (2026-10-22): 591 -> 571 and 356 -> 336 (the replay disclosure moved to Expert view, the hash
# sentence added), 278 -> 301 (the longer answer and caveat line, tile labels), 304 -> 345 (the
# runner and tamper tiles, two more key limits).
WORDS = {"overview_live6_step2": 571, "overview_live6_step1": 336, "agent_vs_model": 301,
         "how_it_works": 345}  # fmt: skip

COUNT = """() => {
  const main = document.querySelector('[data-testid="stMainBlockContainer"]');
  const hidden = [];
  for (const el of main.querySelectorAll('details:not([open]) > :not(summary)')) {
    hidden.push([el, el.style.display]); el.style.display = 'none';
  }
  const text = main.innerText;
  for (const [el, d] of hidden) el.style.display = d;
  return {count: text.split(/\\s+/).filter(t => /[A-Za-z0-9]/.test(t)).length, text};
}"""


def app_env(base: Path) -> dict:
    cases = base / "cases"
    shutil.copytree(ROOT / "demo" / "recorded", cases)
    CASES_DIR["path"] = cases
    return {
        "ATLAS_HOSTED": "1",
        "HOSTED_LIVE_ENABLED": "false",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "hosted-runs"),
        "ATLAS_UI_CASES_DIR": str(cases),
    }


def shots(page, name: str) -> None:
    """Settled full-page screenshots at the three sizes, if ATLAS_UI_SCREENS is set."""
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


def expert(page, on: bool) -> None:
    toggle = page.locator('[data-testid="stCheckbox"] input').first
    toggle.wait_for(state="attached", timeout=60_000)
    if toggle.is_checked() != on:
        page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
        wait_idle(page)


def goto(page, app, path: str, wait: str) -> None:
    page.goto(app.url + path)
    page.locator(wait).first.wait_for(timeout=60_000)
    wait_idle(page)
    settle(page)


# -- the stepper -----------------------------------------------------------------------------------
def test_the_stepper_by_mouse_and_keyboard(app, page):
    open_overview(page, app)
    assert step_now(page) == 2
    live = page.locator(".st-key-stepper-position .hud-step-pos")
    assert live.get_attribute("role") == "status"
    assert live.get_attribute("aria-live") == "polite"
    assert live.inner_text() == "Step 2 of 5"
    row = page.locator(".st-key-stepper-row button")
    assert row.all_inner_texts() == [
        "1 Claim",
        "2 What the checks found",
        "3 The AI's fix",
        "4 Approval & sealed run",
        "5 Verified evidence",
    ]
    # Mouse: Next, Back, the row.
    page.get_by_role("button", name=C.STEP_NEXT).click()
    page.locator(".st-key-stepper-body-3").wait_for(timeout=30_000)
    wait_idle(page)
    assert step_now(page) == 3 and live.inner_text() == "Step 3 of 5"
    page.get_by_role("button", name=C.STEP_BACK).click()
    page.locator(".st-key-stepper-body-2").wait_for(timeout=30_000)
    wait_idle(page)
    go_step(page, 5)
    assert step_now(page) == 5
    assert page.get_by_role("button", name=C.STEP_NEXT).is_disabled()
    # Keyboard: Tab from "Show all steps" reaches the row (one stop), the arrow keys move
    # within it, each with a visible focus outline; Enter selects.
    page.locator(".st-key-show-all input").focus()
    page.keyboard.press("Tab")
    focus = """() => { const e = document.activeElement, s = getComputedStyle(e);
        return {text: e.innerText, style: s.outlineStyle, width: s.outlineWidth,
                row: !!e.closest('.st-key-stepper-row')}; }"""
    focused = page.evaluate(focus)
    assert focused["row"] and focused["style"] != "none", focused
    assert focused["width"] != "0px", focused
    page.keyboard.press("ArrowLeft")
    focused = page.evaluate(focus)
    assert focused["row"] and focused["style"] != "none", focused
    assert focused["text"] == "4 Approval & sealed run", focused
    page.keyboard.press("Enter")
    page.locator(".st-key-stepper-body-4").wait_for(timeout=30_000)
    wait_idle(page)
    page.get_by_role("button", name=C.STEP_BACK).focus()
    page.keyboard.press("Enter")
    page.locator(".st-key-stepper-body-3").wait_for(timeout=30_000)
    wait_idle(page)
    assert step_now(page) == 3
    # The step is kept across a rerun of the page (another case and back resets it).
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    wait_idle(page)
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    page.locator(".st-key-stepper-body-3").wait_for(timeout=30_000)
    wait_idle(page)
    assert step_now(page) == 3
    page.get_by_role("button", name="A real-data leak", exact=True).click()
    page.locator(".st-key-stepper-body-2").wait_for(timeout=30_000)
    wait_idle(page)
    assert step_now(page) == 2


def test_word_counts_in_plain_view(app, page):
    counts, texts = {}, {}
    open_overview(page, app)
    page.locator(".st-key-stepper-body-2 .st-key-analogies").wait_for(timeout=60_000)
    page.get_by_role("button", name=C.REPORT_BUTTON).wait_for(timeout=60_000)
    wait_idle(page)
    settle(page)
    r = page.evaluate(COUNT)
    counts["overview_live6_step2"], texts["overview_live6_step2"] = (
        r["count"],
        r["text"],
    )
    go_step(page, 1)
    settle(page)
    r = page.evaluate(COUNT)
    counts["overview_live6_step1"], texts["overview_live6_step1"] = (
        r["count"],
        r["text"],
    )
    for name, path, wait, last in (
        (
            "agent_vs_model",
            "/agent_vs_model",
            ".st-key-vs-chart",
            ".st-key-vs-footnote",
        ),
        (
            "how_it_works",
            "/how_it_works",
            ".st-key-lim-key-limits",
            ".st-key-lim-all-limits",
        ),
    ):
        goto(page, app, path, wait)
        # The whole page drawn before counting (the last element, and the six tile metrics).
        page.locator(last).first.wait_for(timeout=60_000)
        if name == "agent_vs_model":
            page.wait_for_function(
                "() => document.querySelectorAll('[data-testid=stMetricValue]').length === 6"
            )
        settle(page)
        r = page.evaluate(COUNT)
        counts[name], texts[name] = r["count"], r["text"]
    folder = os.environ.get("ATLAS_UI_WORDS")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / "counts.json").write_text(json.dumps(counts, indent=1), "utf-8")
        for name, text in texts.items():
            (Path(folder) / f"{name}.txt").write_text(text, "utf-8")
    for name, ceiling in WORDS.items():
        assert counts[name] <= ceiling, (name, counts[name], ceiling)
    # Closed expanders' content is not counted: opening one adds words.
    page.locator(".st-key-lim-all-limits summary").first.click()
    page.locator(".st-key-lim-limits").wait_for(timeout=30_000)
    assert page.evaluate(COUNT)["count"] > counts["how_it_works"]


def test_no_stat_tile_is_truncated(app, page):
    goto(page, app, "/agent_vs_model", ".st-key-vs-tiles")
    for w, h in SIZES:
        page.set_viewport_size({"width": w, "height": h})
        time.sleep(0.8)
        cut = page.evaluate(
            """() => [...document.querySelectorAll(
                '[class*="st-key-vs-tile-"] [data-testid="stMetricValue"] *,' +
                '[class*="st-key-vs-tile-"] [data-testid="stMetricLabel"] *,' +
                '[class*="st-key-vs-tile-"] [data-testid="stCaptionContainer"] *')]
              .filter(e => e.scrollWidth > e.clientWidth + 0.5 ||
                (getComputedStyle(e).textOverflow === 'ellipsis' &&
                 e.scrollWidth > e.clientWidth))
              .map(e => e.innerText)"""
        )
        assert cut == [], (w, cut)
        values = page.locator(
            "[class*='st-key-vs-tile-'] [data-testid='stMetricValue']"
        ).all_inner_texts()
        assert values == ["8 of 8", "19 of 20", "0", "2", "none", "3 of 12"], (
            w,
            values,
        )
    page.set_viewport_size({"width": 1440, "height": 900})


def test_the_always_visible_items_need_no_click(app, page):
    open_overview(page, app)
    for n in (2, 1, 3, 4, 5):
        go_step(page, n)
        text = page.evaluate(COUNT)["text"]
        for item in (
            "VIOLATION_FOUND",
            "NO_VIOLATION_FOUND",
            "This does not say the scientific claim is true or false.",
            "Claim: The activity classifier works on people absent from training.",
            "replayed here, not re-run.",
        ):
            assert item in text, (n, item)
    open_overview(page, app, "harflawed")
    text = page.evaluate(COUNT)["text"]
    assert "[ATLAS-authored flawed variant:" in text
    assert f"{C.HAR_DATA_LINE} {C.HAR_DOI}" in text  # a space before the link
    goto(page, app, "/agent_vs_model", ".st-key-vs-chart")
    text = page.evaluate(COUNT)["text"]
    assert C.VS_CAVEAT_LINE.format(c=4) in text and "(estimate, not billing)" in text
    goto(page, app, "/how_it_works", ".st-key-lim-key-limits")
    text = page.evaluate(COUNT)["text"]
    for line in C.KEY_LIMITS:
        assert line in text


def test_r0_width_and_body_text(app, page):
    """R0: the content at most 1150 px wide and centred; body text at least 16 px."""
    sizes = """(sel) => [...document.querySelectorAll(sel)]
        .map(e => parseFloat(getComputedStyle(e).fontSize))"""
    for path, wait, selectors in (
        ("/", ".st-key-claim-line", (".st-key-story-why p", ".st-key-claim-line p",
                                     ".hud-case-desc", ".st-key-recorded-label p")),
        ("/agent_vs_model", ".st-key-vs-answer", (".st-key-vs-answer p",
                                                  ".st-key-vs-caveat-line p")),
        ("/how_it_works", ".st-key-lim-key-limits", (".st-key-lim-key-limits li",
                                                     ".st-key-lim-steps li",
                                                     ".st-key-lim-safety-tiles p")),
    ):  # fmt: skip
        goto(page, app, path, wait)
        for sel in selectors:
            found = page.evaluate(sizes, sel)
            assert found and min(found) >= 16, (path, sel, found)
        for w, h in ((1920, 1080), (1440, 900), (1000, 800)):
            page.set_viewport_size({"width": w, "height": h})
            time.sleep(0.5)
            box = page.get_by_test_id("stMainBlockContainer").bounding_box()
            main = page.get_by_test_id("stMain").bounding_box()
            assert box["width"] <= 1150.5, (path, w, box)
            left = box["x"] - main["x"]
            right = main["x"] + main["width"] - box["x"] - box["width"]
            assert abs(left - right) <= 20, (path, w, left, right)  # centred
        page.set_viewport_size({"width": 1440, "height": 900})


# -- verification: never cached, the stepper's runs included ------------------------------------------
def _flip(path: Path) -> bytes:
    raw = path.read_bytes()
    path.write_bytes(raw[:-1] + (b" " if raw[-1:] != b" " else b"\n"))
    return raw


def test_a_byte_changed_mid_session_shows_only_the_evidence_changed_panel(app, page):
    target = CASES_DIR["path"] / LIVE6 / "candidates" / "c1" / "outcome.json"
    # (a) Between two full renders of the same session (a case card click reruns the page).
    open_overview(page, app)
    raw = _flip(target)
    try:
        page.get_by_role("button", name="A leak caught and fixed", exact=True).click()
        page.locator(".st-key-integrity-failed").wait_for(timeout=60_000)
        wait_idle(page)
        for absent in (".st-key-stepper", ".st-key-verdict-bar", ".st-key-claim-line"):
            assert page.locator(absent).count() == 0, absent
    finally:
        target.write_bytes(raw)
    # (b) Inside the stepper: render, change the byte, then click Next (a fragment rerun).
    open_overview(page, app)
    assert step_now(page) == 2
    raw = _flip(target)
    try:
        page.get_by_role("button", name=C.STEP_NEXT).click()
        page.locator(".st-key-integrity-failed").wait_for(timeout=60_000)
        wait_idle(page)
        for absent in (
            ".st-key-stepper",
            "[class*='st-key-stepper-body-']",
            ".st-key-verdict-bar",
            ".hud-ret",
        ):
            assert page.locator(absent).count() == 0, absent
        rows = page.locator(".st-key-trace-integrity table tbody tr")
        assert "candidates/c1/outcome.json" in rows.first.inner_text()
    finally:
        target.write_bytes(raw)
    open_overview(page, app)
    assert step_now(page) == 2  # restored: the case verifies again


# -- evidence: screenshots -----------------------------------------------------------------------------
def test_screens(app, page):
    if not os.environ.get("ATLAS_UI_SCREENS"):
        return
    open_overview(page, app)
    for n in range(1, 6):
        go_step(page, n)
        shots(page, f"s17_01_overview_live6_step{n}")
    page.get_by_text(C.SHOW_ALL_STEPS, exact=True).click()
    page.locator(".st-key-step-5").wait_for(timeout=30_000)
    wait_idle(page)
    shots(page, "s17_02_overview_live6_show_all")
    page.get_by_text(C.SHOW_ALL_STEPS, exact=True).click()
    wait_idle(page)
    expert(page, True)
    shots(page, "s17_03_overview_live6_expert")
    expert(page, False)
    open_overview(page, app, "harflawed")
    shots(page, "s17_04_harflawed_step2")
    go_step(page, 4)
    shots(page, "s17_04_harflawed_step4")
    open_overview(page, app, "harclean")
    go_step(page, 5)
    open_more(page, 5)
    shots(page, "s17_05_harclean_step5")
    for name, path, wait in (
        ("s17_06_agent_vs_model", "/agent_vs_model", ".st-key-vs-chart"),
        ("s17_07_how_it_works", "/how_it_works", ".st-key-lim-steps"),
    ):
        goto(page, app, path, wait)
        shots(page, f"{name}_plain")
        expert(page, True)
        shots(page, f"{name}_expert")
        expert(page, False)
    open_overview(page, app)
    page.get_by_role("button", name=C.GLOSSARY_BUTTON).click()
    page.get_by_text("Training data:", exact=False).wait_for(timeout=30_000)
    folder = Path(os.environ["ATLAS_UI_SCREENS"])
    for w, h in SIZES:  # viewport captures: the popover is anchored to its button
        page.set_viewport_size({"width": w, "height": h})
        time.sleep(0.6)
        if not page.get_by_text("Training data:", exact=False).is_visible():
            page.get_by_role("button", name=C.GLOSSARY_BUTTON).click()
            page.get_by_text("Training data:", exact=False).wait_for(timeout=30_000)
        settle(page)
        page.screenshot(path=str(folder / f"s17_08_overview_glossary_open_{w}x{h}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})
