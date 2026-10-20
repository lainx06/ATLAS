"""Scenario 9 (UI design pass, phase 1): the HUD on the hosted "Recorded runs" view.

ATLAS_HOSTED=1 with the live kill switch off ("Live: unavailable"); the bundled runs in
demo/recorded are only read. live6 shows the hero in the first viewport; the two HAR bundles
(no candidate) show the ring, one reticle, the leak map and the fit-scope flow from their own
files, with no candidate column. With ATLAS_UI_SCREENS set, screenshots are saved there.
"""

import json
import os
import time
from pathlib import Path

import pytest
from helpers import shot, wait_idle

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR = ["t09/agent-har_flawed-1e2267f662c0", "t09/agent-har_clean-ac63eaecd7a8"]
SIZES = [(1440, 900), (1280, 800), (390, 844)]


def app_env(base: Path) -> dict:
    return {
        "ATLAS_HOSTED": "1",
        "HOSTED_LIVE_ENABLED": "false",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "hosted-runs"),
    }


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def open_hosted(page, app, label: str | None = None) -> None:
    page.goto(app.url)
    page.locator(".st-key-card-integrity").wait_for(timeout=60_000)
    wait_idle(page)
    if label is None:
        return
    phone = (page.viewport_size or {}).get("width", 1440) < 600
    if phone:
        page.get_by_test_id("stExpandSidebarButton").click()
    box = page.get_by_role("combobox", name="Recorded run")
    box.click()
    page.get_by_role("option", name=label, exact=True).click()
    page.get_by_text(f"Run {label}.", exact=False).wait_for(timeout=30_000)
    wait_idle(page)
    if phone:
        page.keyboard.press("Escape")
        close = page.get_by_test_id("stSidebarCollapseButton")
        if close.count() and close.is_visible():
            close.click()
        time.sleep(0.5)


@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_the_hosted_header_with_live_unavailable_and_the_live6_hero(app, page, size):
    w, h = size
    page.set_viewport_size({"width": w, "height": h})
    open_hosted(page, app)
    time.sleep(1.5)
    shot(page, "s9_01_hosted_live6_hero")
    if w >= 1024:
        sidebar = page.get_by_test_id("stSidebar").inner_text()
        assert "Live: unavailable" in sidebar and "Hosted demo: limited" in sidebar
        assert "Recorded run" in sidebar
        for selector in (".hud-ret", ".hud-leak", ".hud-flow"):
            boxes = page.locator(selector).evaluate_all(
                "els => els.map(e => e.getBoundingClientRect().bottom)"
            )
            assert boxes and max(boxes) <= h, (selector, boxes)
    banner = page.locator(".st-key-banner").inner_text()
    assert "Replay: these are recorded runs" in banner and "LIVE RUN" in banner
    assert (
        "recomputed now from the bundled files"
        in page.locator(".hud-ring").inner_text()
    )
    if w < 1024:
        page.get_by_test_id("stExpandSidebarButton").click()
        time.sleep(0.6)
        shot(page, "s9_02_hosted_sidebar")
        assert "Live: unavailable" in page.get_by_test_id("stSidebar").inner_text()


@pytest.mark.parametrize("label", HAR)
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_the_har_bundles_render_from_their_own_files(app, page, size, label):
    page.set_viewport_size({"width": size[0], "height": size[1]})
    open_hosted(page, app, label)
    time.sleep(1.5)
    short = label.split("-")[1]
    shot(page, f"s9_03_{short}_hero")
    folder = os.environ.get("ATLAS_UI_SCREENS")
    ev = page.locator(".st-key-hud-evidence")
    ev.scroll_into_view_if_needed()
    if folder:
        ev.screenshot(
            path=str(Path(folder) / f"s9_04_{short}_diagrams_{size[0]}x{size[1]}.png")
        )
    run = BUNDLE / label
    outcome = read(run / "original/outcome.json")
    reticles = page.locator(".hud-ret")
    assert reticles.count() == 1 and outcome["outcome"] in reticles.inner_text()
    assert page.locator(".hud-pane-cand").count() == 0
    assert page.locator(".hud-tg-in").count() == 0
    assert "Verified revision" not in page.locator(".st-key-hud-hero").inner_text()
    split = next(
        a
        for a in read(run / "original/checks/split_integrity.json")["assertions"]
        if a["assertion_id"] == "split.no_group_overlap"
    )
    groups = split["observed"]["overlapping_groups"]
    rows = {g for v in groups.values() for g in v}
    folds = [s["fold"] for s in read(run / "original/splits.json")]
    assert page.locator(".hud-lm tbody th").count() == len(rows)
    assert page.locator("td.hud-both").count() == sum(len(v) for v in groups.values())
    assert page.locator(".hud-lm thead th").count() == len(folds) + 1
    flow = page.locator(".hud-flow").inner_text()
    fit = next(
        a
        for a in read(run / "original/checks/fit_provenance.json")["assertions"]
        if a["assertion_id"] == "fit.state_dependencies_within_fold_train"
    )
    for origin in fit["observed"].get("origins") or []:
        assert (
            origin["class"] in flow and f"[{origin['contributing_rows']} rows]" in flow
        )
    if not fit["observed"].get("origins"):
        assert "observed.judged_uses" in flow
    assert "CC BY 4.0" in page.locator(".st-key-banner").inner_text()
