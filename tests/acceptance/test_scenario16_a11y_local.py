"""Scenario 16 (UI restructure slice 3), local mode, in the browser.

A verified finished run (live6, opened read-only from a copy under the module's basetemp)
offers "Download audit report" (named after the run, from its verified files); a case whose
copy no longer verifies shows only the evidence-changed panel and no report button. axe-core
finds no serious or critical violation in ATLAS's own markup on the finished-run view, local
Try It Live and the evidence-changed panel, at 1440 x 900 and 390 x 844. demo/recorded is only
read; every change is made in copies.
"""

import json
import shutil
import time
from pathlib import Path

from helpers import settle, wait_idle
from test_scenario15_slice3 import a11y_dir, check_page

from atlas.ui import copy as C

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"


def app_env(base: Path) -> dict:
    recorded = base / "recorded"
    shutil.copytree(BUNDLE / LIVE6, recorded / LIVE6)
    cases = base / "cases"
    shutil.copytree(BUNDLE, cases)
    target = cases / LIVE6 / "original" / "outcome.json"
    target.write_bytes(target.read_bytes().replace(b'"FAIL"', b'"PASS"', 1))
    return {"ATLAS_UI_RECORDED_DIR": str(recorded), "ATLAS_UI_CASES_DIR": str(cases)}


def open_finished(page, app) -> None:
    page.goto(app.url + "/try_it_live")
    page.get_by_role("button", name="Confirm & run").wait_for(timeout=60_000)
    expand = page.get_by_test_id("stExpandSidebarButton")
    if expand.count() and expand.is_visible():
        expand.click()
        time.sleep(0.5)
    page.get_by_test_id("stSidebar").get_by_text(
        "Open a recorded run", exact=True
    ).click()
    page.get_by_role("combobox", name="Recorded run").wait_for()
    wait_idle(page)
    page.get_by_role("combobox", name="Recorded run").click()
    page.get_by_role("option", name=f"{LIVE6} (agent)", exact=True).click()
    page.locator(".st-key-card-integrity").wait_for(timeout=30_000)
    wait_idle(page)
    close = page.get_by_test_id("stSidebarCollapseButton")
    if page.viewport_size["width"] < 600 and close.count() and close.is_visible():
        close.click()
        time.sleep(0.5)


def test_a_finished_run_offers_its_report(app, page, tmp_path):
    open_finished(page, app)
    with page.expect_download() as info:
        page.locator(".st-key-run-report").get_by_role(
            "button", name=C.REPORT_BUTTON
        ).click()
    download = info.value
    assert (
        download.suggested_filename
        == "atlas-audit-agent-s01_faulty-877f8245a8a2-VIOLATION_FOUND.html"
    )
    saved = tmp_path / download.suggested_filename
    download.save_as(saved)
    html = saved.read_text(encoding="utf-8")
    assert "49 of 49 recorded items verified when this report was generated." in html


def test_no_report_after_a_failed_verification(app, page):
    page.goto(app.url)
    page.locator(".st-key-card-integrity").wait_for(timeout=60_000)
    wait_idle(page)
    assert "EVIDENCE CHANGED" in page.locator(".st-key-card-integrity").inner_text()
    assert page.get_by_role("button", name=C.REPORT_BUTTON).count() == 0
    assert page.get_by_text(C.EXPERT_TOGGLE, exact=True).count() == 0


def test_axe_on_the_local_views(app, browser):
    def try_it_live(page):
        page.goto(app.url + "/try_it_live")
        page.get_by_role("button", name="Confirm & run").wait_for(timeout=60_000)
        wait_idle(page)

    def changed(page):
        page.goto(app.url)
        page.locator(".st-key-card-integrity").wait_for(timeout=60_000)
        wait_idle(page)

    results: dict = {}
    for w, h in ((1440, 900), (390, 844)):
        for name, go in (
            ("finished_run_local", lambda p: open_finished(p, app)),
            ("try_it_live_local", try_it_live),
            ("evidence_changed", changed),
        ):
            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()
            go(page)
            time.sleep(0.4)
            settle(page)
            check_page(page, f"{name}_{w}x{h}", results)
            context.close()
    atlas = {k: [n for n in v if n["owner"] != "streamlit"] for k, v in results.items()}
    assert all(not v for v in atlas.values()), json.dumps(atlas, indent=1)[:4000]
    folder = a11y_dir()
    if folder is not None:
        (folder / "summary_local.json").write_text(
            json.dumps(
                {k: [(n["owner"], n["rule"]) for n in v] for k, v in results.items()},
                indent=1,
            ),
            encoding="utf-8",
        )
