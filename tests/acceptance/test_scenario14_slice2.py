"""Scenario 14 (UI restructure slice 2): in the browser (hosted, ATLAS_HOSTED=1).

A1: on the Overview the active case card's "Showing this case" label, and every card's last
line, lie fully inside their card (with bottom padding left) at every width tested. The tamper
demo changes one byte in a temporary copy, shows the real check's result and leaves
demo/recorded unchanged. The AI Agent vs. Model Alone page shows its question, chart, data
table and caveats without expanding anything; How It Works & Limits shows its diagram, steps
and limits. With ATLAS_UI_SCREENS set, settled full-page screenshots are saved at 1440 x 900,
1280 x 800 and 390 x 844.
"""

import time
from pathlib import Path

from helpers import settle, wait_idle
from test_scenario12_story import full_page, open_overview, toggle_step

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import versus as VS

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
WIDTHS = ((1920, 1080), (1440, 900), (1366, 768), (1280, 800), (1024, 768), (800, 900),
          (390, 844))  # fmt: skip


def app_env(base: Path) -> dict:
    return {
        "ATLAS_HOSTED": "1",
        "HOSTED_LIVE_ENABLED": "false",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "hosted-runs"),
    }


def bundle_hashes() -> dict[str, str]:
    return {
        p.relative_to(BUNDLE).as_posix(): A.sha256_file(p)
        for p in sorted(BUNDLE.rglob("*"))
        if p.is_file()
    }


CARD_GEOMETRY = """() => [...document.querySelectorAll('[class*="st-key-case-card-"]')]
  .map(card => {
    const box = card.getBoundingClientRect();
    const pad = parseFloat(getComputedStyle(card).paddingBottom);
    const label = card.querySelector('.hud-case-on');
    const last = card.querySelector('.hud-case-desc');
    const r = (e) => e ? e.getBoundingClientRect() : null;
    return {
      key: [...card.classList].find(k => k.startsWith('st-key-case-card-')),
      bottom: box.bottom, pad,
      label: label ? {bottom: r(label).bottom, top: r(label).top, h: label.scrollHeight}
                   : null,
      desc: r(last).bottom,
    };
  })"""


def test_a1_the_card_label_is_fully_visible_at_every_width(app, page):
    open_overview(page, app)
    for case in ("live6", "harflawed", "harclean"):
        if case != "live6":
            open_overview(page, app, case)
        for w, h in WIDTHS:
            page.set_viewport_size({"width": w, "height": h})
            time.sleep(0.5)
            settle(page)
            cards = page.evaluate(CARD_GEOMETRY)
            assert len(cards) == 3
            active = [c for c in cards if c["label"] is not None]
            assert [c["key"] for c in active] == [f"st-key-case-card-on-{case}"], (
                w,
                active,
            )
            for c in cards:
                # The last text line ends inside the card, above its bottom padding.
                assert c["desc"] <= c["bottom"] - c["pad"] + 0.5, (w, c)
            label = active[0]["label"]
            assert label["bottom"] <= active[0]["bottom"] - active[0]["pad"] + 0.5, (
                w,
                label,
            )
            assert label["bottom"] - label["top"] >= 12, (w, label)  # not squashed
    page.set_viewport_size({"width": 1440, "height": 900})
    open_overview(page, app)
    full_page(page, "s14_01_overview_live6")


def test_harflawed_step_4_says_no_ai_agent_took_part(app, page):
    open_overview(page, app, "harflawed")
    toggle_step(page, 4, True)
    summary = page.locator(".st-key-step-4 summary").first.inner_text()
    assert C.SCRIPT_ONLY.rstrip(".") in summary.replace("\n", " ")
    page.locator(".st-key-story-approvals").wait_for()
    wait_idle(page)
    page.locator(".st-key-step-4").first.scroll_into_view_if_needed()
    full_page(page, "s14_02_harflawed_step4")


def test_the_tamper_demo_on_live6(app, page):
    before = bundle_hashes()
    open_overview(page, app)
    section = page.locator(".st-key-tamper")
    section.wait_for()
    assert C.TAMPER_HEAD in section.inner_text()
    # Slice 3: a collapsed expander after step 5; open it.
    page.locator(".st-key-tamper summary").first.click()
    page.get_by_role("button", name=C.TAMPER_BUTTON).wait_for()
    assert page.locator(".st-key-tamper-result").count() == 0
    full_page(page, "s14_05_tamper_before_live6")
    page.get_by_role("button", name=C.TAMPER_BUTTON).click()
    result = page.locator(".st-key-tamper-result")
    result.wait_for(timeout=60_000)
    wait_idle(page)
    text = " ".join(result.inner_text().split())
    head = C.TAMPER_RESULT[1].format(t=49, items="the original's recorded result")
    assert head in text, text
    assert C.TAMPER_STATEMENT in text
    # The case itself still shows its verified outcome; the bundle is unchanged.
    assert "49/49" in page.locator(".st-key-hud-hero").inner_text()
    assert bundle_hashes() == before
    full_page(page, "s14_05_tamper_after_live6")
    # Another file of the run, in Expert view.
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    wait_idle(page)
    details = page.locator(".st-key-tamper details").first
    if details.get_attribute("open") is None:  # the rerun may redraw it collapsed
        page.locator(".st-key-tamper summary").first.click()
    page.locator(".st-key-tamper-table table").wait_for(timeout=30_000)  # Expert drawn
    wait_idle(page)
    option = page.get_by_role("option", name="candidates/c1/outcome.json")
    for _ in range(
        10
    ):  # the selectbox is redrawn for Expert view; open it once it is ready
        page.locator(".st-key-tamper").get_by_role("combobox").click()
        try:
            option.wait_for(timeout=2_000)
            break
        except Exception:  # noqa: BLE001 - not open yet
            page.keyboard.press("Escape")
            time.sleep(0.5)
    option.click()
    wait_idle(page)
    page.get_by_role("button", name=C.TAMPER_BUTTON).click()
    page.get_by_text("differ: candidates/c1/outcome.json").wait_for(timeout=60_000)
    wait_idle(page)
    assert page.locator(".st-key-tamper-table table").count() == 1
    assert bundle_hashes() == before
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    wait_idle(page)


def test_agent_vs_model_alone_page(app, page):
    open_overview(page, app)
    page.get_by_role("link", name=C.PAGE_AGENT).click()
    page.locator(".st-key-vs-chart svg").first.wait_for(timeout=30_000)
    wait_idle(page)
    body = page.locator(".st-key-vs-page").inner_text()
    assert C.VS_QUESTION in body
    # The caveats are visible without expanding anything.
    caveats = page.locator(".st-key-vs-caveats")
    assert caveats.is_visible()
    assert "Development cases, not held-out" in caveats.inner_text()
    assert page.locator(".st-key-vs-page details").count() == 0
    page.locator(".st-key-vs-table table tbody tr").nth(2).wait_for(timeout=30_000)
    rows = page.locator(".st-key-vs-table table tbody tr").all_inner_texts()
    assert any("8 of 8 assessable" in r and "19 of 20 on the same 8" in r for r in rows)
    assert C.VS_REVIEW in body and "estimate, not billing" in body
    assert page.locator(".st-key-vs-chart svg.vs-wide").is_visible()
    full_page(page, "s14_03_agent_vs_model_plain")
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    page.locator(".st-key-vs-trials table").wait_for(timeout=30_000)
    wait_idle(page)
    for c in VS.verify():
        assert c.recomputed in page.locator(".st-key-vs-files").inner_text()
    full_page(page, "s14_03_agent_vs_model_expert")
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    wait_idle(page)


def test_how_it_works_and_limits_page(app, page):
    open_overview(page, app)
    page.get_by_role("link", name=C.PAGE_LIMITS).click()
    page.locator(".st-key-lim-limits").wait_for(timeout=30_000)
    wait_idle(page)
    settle(page)
    assert page.locator(".hud-lim-diagram li").count() == 5
    assert (
        C.DIAGRAM_LABEL.upper()
        in page.locator(".st-key-lim-diagram").inner_text().upper()
    )
    assert page.locator(".st-key-lim-limits li").count() == len(C.LIMITS_PLAIN)
    full_page(page, "s14_04_how_it_works_plain")
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    page.locator(".st-key-lim-limits .lim-orig").first.wait_for(timeout=30_000)
    wait_idle(page)
    assert page.locator(".st-key-lim-limits .lim-orig").count() == len(C.LIMITS_PLAIN)
    full_page(page, "s14_04_how_it_works_expert")
    page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
    wait_idle(page)
