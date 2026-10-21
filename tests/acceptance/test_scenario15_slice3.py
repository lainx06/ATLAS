"""Scenario 15 (UI restructure slice 3), hosted (ATLAS_HOSTED=1), in the browser.

C1/C2: the tamper demo is a collapsed expander directly after step 5, and the Expert view
switch sits beside the page title, top right, on the Overview, the comparison page and How It
Works & Limits. D: "Download audit report" saves atlas-audit-<case>-<outcome>.html; the file
renders on its own (no request); printed (copy fix pass R1: 15 mm margins, 10.5 pt type) every
table fits the page width and the report takes at most two pages. E: axe-core finds no serious or
critical violation in ATLAS's own markup on any page, at 1440 x 900 and 390 x 844; every chart
or diagram has role="img" and a name; every control reached by Tab shows a visible focus
indicator.

With ATLAS_UI_SCREENS set, settled full-page screenshots are saved (1440 x 900, 1280 x 800,
390 x 844); with ATLAS_UI_A11Y set, the axe results (JSON) and the keyboard-walk screenshots.
"""

import json
import os
import re
import time
from pathlib import Path

import a11y
from helpers import settle, wait_idle
from test_scenario12_story import SIZES, full_page, open_overview

from atlas.ui import copy as C

TITLES = {c.key: c.title for c in C.CASES}


def app_env(base: Path) -> dict:
    return {
        "ATLAS_HOSTED": "1",
        "HOSTED_LIVE_ENABLED": "false",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "hosted-runs"),
    }


def a11y_dir() -> Path | None:
    folder = os.environ.get("ATLAS_UI_A11Y")
    return Path(folder) if folder else None


def expert(page, on: bool) -> None:
    toggle = page.locator('[data-testid="stCheckbox"] input').first
    toggle.wait_for(state="attached", timeout=60_000)
    if toggle.is_checked() != on:
        page.get_by_text(C.EXPERT_TOGGLE, exact=True).click()
        wait_idle(page)


def box(page, selector: str) -> dict:
    return page.locator(selector).first.bounding_box()


# -- C1 / C2 ---------------------------------------------------------------------------------------
def test_tamper_after_step_5_collapsed_and_the_switch_top_right(app, page):
    open_overview(page, app)
    page.locator(".st-key-tamper").wait_for(timeout=60_000)
    order = page.evaluate(
        """() => {
          const t = document.querySelector('.st-key-tamper');
          const s5 = document.querySelector('.st-key-step-5');
          const bar = document.querySelector('.st-key-verdict-bar');
          return {afterStep5: !!(s5.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING),
                  afterBar: !!(bar.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING),
                  open: t.querySelector('details').open};
        }"""
    )
    assert order["afterStep5"] and order["afterBar"] and order["open"] is False
    # Nothing of the demo sits between the verdict bar and step 1.
    gap = page.evaluate(
        """() => {
          const bar = document.querySelector('.st-key-verdict-bar').getBoundingClientRect();
          const s1 = document.querySelector('.st-key-step-1').getBoundingClientRect();
          const t = document.querySelector('.st-key-tamper').getBoundingClientRect();
          return {barBottom: bar.bottom, s1Top: s1.top, tTop: t.top};
        }"""
    )
    assert gap["tTop"] > gap["s1Top"] > gap["barBottom"] - 1
    full_page(page, "s15_01_overview_live6")
    # The switch: beside the title, at the right, on every page that has an Expert view.
    for path, title in (
        ("/", C.APP_NAME),
        ("/agent_vs_model", C.PAGE_AGENT),
        ("/how_it_works", C.PAGE_LIMITS),
    ):
        page.goto(app.url + path)
        page.get_by_text(C.EXPERT_TOGGLE, exact=True).wait_for(timeout=60_000)
        wait_idle(page)
        for w, h in ((1440, 900), (1280, 800)):
            page.set_viewport_size({"width": w, "height": h})
            time.sleep(0.5)
            heading = page.get_by_role("heading", name=title, exact=True).bounding_box()
            switch = (
                page.get_by_text(C.EXPERT_TOGGLE, exact=True)
                .locator("..")
                .bounding_box()
            )
            main = page.get_by_test_id("stMain").bounding_box()
            # Same row as the title, in the right part of the main column.
            assert switch["y"] < heading["y"] + heading["height"], (path, w)
            assert switch["y"] + switch["height"] > heading["y"], (path, w)
            assert switch["x"] > main["x"] + main["width"] * 0.6, (
                path,
                w,
                switch,
                main,
            )
    page.set_viewport_size({"width": 1440, "height": 900})


def test_the_tamper_demo_opens_and_runs_after_step_5(app, page):
    open_overview(page, app)
    page.locator(".st-key-tamper summary").first.click()
    page.get_by_role("button", name=C.TAMPER_BUTTON).click()
    page.locator(".st-key-tamper-result").wait_for(timeout=60_000)
    wait_idle(page)
    assert (
        page.locator(".st-key-tamper details").first.get_attribute("open") is not None
    )
    text = " ".join(page.locator(".st-key-tamper-result").inner_text().split())
    assert C.TAMPER_STATEMENT in text
    page.locator(".st-key-tamper").scroll_into_view_if_needed()
    full_page(page, "s15_02_overview_live6_tamper_open")


# -- D: the audit report -----------------------------------------------------------------------------
def test_the_audit_report_downloads_and_prints_within_the_page_width(
    app, page, tmp_path
):
    for case, outcome in (
        ("live6", "VIOLATION_FOUND"),
        ("harflawed", "VIOLATION_FOUND"),
    ):
        open_overview(page, app, case)
        with page.expect_download() as info:
            page.get_by_role("button", name=C.REPORT_BUTTON).click()
        download = info.value
        name = f"atlas-audit-{case}-{outcome}.html"
        assert download.suggested_filename == name
        saved = tmp_path / name
        download.save_as(saved)
        html = saved.read_text(encoding="utf-8")
        assert "<script" not in html.lower() and "href=" not in html
        report = page.context.new_page()
        requests: list[str] = []
        report.on("request", lambda r, seen=requests: seen.append(r.url))
        report.goto(saved.resolve().as_uri())
        report.wait_for_load_state("load")
        assert [u for u in requests if not u.startswith("file:")] == []
        assert C.REPORT_TITLE in report.locator("h1").inner_text()
        for kind in ("screen", "print"):
            report.emulate_media(media="print" if kind == "print" else "screen")
            full_page_file(report, f"s15_05_report_{case}_{kind}")
        report.emulate_media(media="print")
        # The printable width of A4 and Letter inside the 15 mm margins, in CSS pixels.
        for fmt, width in (("A4", 681), ("Letter", 703)):
            report.set_viewport_size({"width": width, "height": 1000})
            wide = report.evaluate(
                """() => [...document.querySelectorAll('table, main')]
                    .filter(e => e.scrollWidth > e.parentElement.clientWidth)
                    .map(e => e.tagName)"""
            )
            assert wide == [], (case, fmt, wide)
            assert report.evaluate(
                "() => document.documentElement.scrollWidth"
                " <= document.documentElement.clientWidth"
            )
            pdf = report.pdf(format=fmt)
            assert 1 <= _pages(pdf) <= 2, (case, fmt, _pages(pdf))
        report.close()


def _pages(pdf: bytes) -> int:
    """Pages in a PDF Chromium wrote (its page objects)."""
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf))


def full_page_file(page, name: str) -> None:
    folder = os.environ.get("ATLAS_UI_SCREENS")
    if not folder:
        return
    Path(folder).mkdir(parents=True, exist_ok=True)
    for w, h in SIZES:
        page.set_viewport_size({"width": w, "height": h})
        time.sleep(0.3)
        height = page.evaluate("() => document.documentElement.scrollHeight")
        page.set_viewport_size({"width": w, "height": max(h, height)})
        time.sleep(0.3)
        page.screenshot(path=str(Path(folder) / f"{name}_{w}x{h}.png"))
    page.set_viewport_size({"width": 1440, "height": 900})


# -- the comparison and limits pages (screenshots) ----------------------------------------------------
def test_comparison_and_limits_screens(app, page):
    open_overview(page, app)
    page.get_by_role("link", name=C.PAGE_AGENT).click()
    page.locator(".st-key-vs-means").wait_for(timeout=30_000)
    wait_idle(page)
    means = page.locator(".st-key-vs-means").inner_text()
    for item in C.VS_MEANS_PLAIN:
        assert item in " ".join(means.split())
    assert page.locator(".st-key-vs-caveats").is_visible()
    full_page(page, "s15_03_agent_vs_model_plain")
    expert(page, True)
    page.locator(".st-key-vs-trials").wait_for(timeout=30_000)
    means = " ".join(page.locator(".st-key-vs-means").inner_text().split())
    assert C.VS_MEANS_PLAIN[0] not in means
    assert page.locator(".st-key-vs-caveats").is_visible()
    full_page(page, "s15_03_agent_vs_model_expert")
    expert(page, False)
    page.get_by_role("link", name=C.PAGE_LIMITS).click()
    page.locator(".st-key-lim-limits").wait_for(timeout=30_000)
    wait_idle(page)
    text = " ".join(page.locator(".st-key-lim-limits").inner_text().split())
    assert (
        "schema failures in 5 of the 8 live runs: runs 1 to 8, with 3 and 3b counted as one"
        in text
    )
    assert "Established on 19 October 2026 for the private hosted app" in text
    full_page(page, "s15_04_how_it_works_plain")


# -- E: accessibility ------------------------------------------------------------------------------------
def states(app):
    def ov(case, on):
        def go(page):
            open_overview(page, app, case)
            expert(page, on)

        return go

    def at(path, selector, on=False):
        def go(page):
            page.goto(app.url + path)
            page.locator(selector).first.wait_for(timeout=60_000)
            wait_idle(page)
            if on:
                expert(page, True)

        return go

    out = [
        (f"overview_{c}_{'expert' if on else 'plain'}", ov(c, on))
        for c in TITLES
        for on in (False, True)
    ]
    out += [
        ("try_it_live_hosted", at("/try_it_live", ".st-key-live-unavailable")),
        ("agent_vs_model_plain", at("/agent_vs_model", ".st-key-vs-chart")),
        ("agent_vs_model_expert", at("/agent_vs_model", ".st-key-vs-chart", True)),
        ("how_it_works_plain", at("/how_it_works", ".st-key-lim-limits")),
        ("how_it_works_expert", at("/how_it_works", ".st-key-lim-limits", True)),
    ]
    return out


def check_page(page, name: str, results: dict) -> None:
    settle(page)
    response = a11y.run(page)
    nodes = a11y.classify(page, response)
    folder = a11y_dir()
    if folder is not None:
        a11y.save(folder, name, response, nodes)
    results[name] = nodes
    for svg in page.evaluate(a11y.SVGS):
        assert svg["role"] == "img" and svg["name"], (name, svg)


def test_axe_finds_no_serious_violation_in_atlas_markup(app, browser):
    results: dict = {}
    for w, h in ((1440, 900), (390, 844)):
        for name, go in states(app):
            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()
            go(page)
            time.sleep(0.4)
            check_page(page, f"{name}_{w}x{h}", results)
            context.close()
    atlas = {k: [n for n in v if n["owner"] != "streamlit"] for k, v in results.items()}
    assert all(not v for v in atlas.values()), json.dumps(atlas, indent=1)[:4000]
    folder = a11y_dir()
    if folder is not None:
        (folder / "summary_hosted.json").write_text(
            json.dumps(
                {k: [(n["owner"], n["rule"]) for n in v] for k, v in results.items()},
                indent=1,
            ),
            encoding="utf-8",
        )


def test_every_control_reached_by_tab_shows_its_focus(app, page):
    folder = a11y_dir()
    for path, wait, name in (
        ("/", ".st-key-verdict-bar", "overview"),
        ("/agent_vs_model", ".st-key-vs-chart", "agent_vs_model"),
    ):
        page.goto(app.url + path)
        page.locator(wait).first.wait_for(timeout=60_000)
        wait_idle(page)
        settle(page)
        walk = a11y.tab_walk(page, shots=folder, name=name)
        assert len(walk) >= 6, walk
        missing = [w for w in walk if w["shown"] is None]
        assert missing == [], missing
        if folder is not None:
            (folder / f"tab_{name}.json").write_text(
                json.dumps(walk, indent=1), "utf-8"
            )
