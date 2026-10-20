"""Scenario 9 (UI design pass, phase 1; story slice 1): the HUD on the hosted Overview.

ATLAS_HOSTED=1 with the live kill switch off ("Live: unavailable"); the bundled runs in
demo/recorded are only read. Since story slice 1 they are the Overview's case cards: live6
(the default case) shows the verdict bar's hero in the first viewport; the two HAR bundles
(no candidate) show the ring, one reticle, the leak map and the fit-scope flow from their own
files in step 2, with no candidate column. With ATLAS_UI_SCREENS set, screenshots are saved.
"""

import json
import os
import time
from pathlib import Path

import pytest
from helpers import settle, shot, shots, wait_idle

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


TITLES = {
    "t09/agent-har_flawed-1e2267f662c0": "A real-data leak",
    "t09/agent-har_clean-ac63eaecd7a8": "A clean evaluation",
}


def open_hosted(page, app, label: str | None = None) -> None:
    """The Overview; `label` selects that bundled run's case card (layout step)."""
    page.goto(app.url)
    page.locator(".st-key-verdict-bar").wait_for(timeout=60_000)
    wait_idle(page)
    if label is None:
        return
    page.get_by_role("button", name=TITLES[label], exact=True).click()
    page.locator("[class*='st-key-case-card-on-']").get_by_text(
        TITLES[label], exact=True
    ).wait_for(timeout=30_000)
    page.locator(".st-key-verdict-bar").wait_for(timeout=30_000)
    wait_idle(page)


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
        for selector in (".hud-ret",):  # slice 1: the verdict bar leads
            boxes = page.locator(selector).evaluate_all(
                "els => els.map(e => e.getBoundingClientRect().bottom)"
            )
            assert boxes and max(boxes) <= h, (selector, boxes)
    banner = page.locator(".st-key-banner").inner_text()
    # Plain mode: the run's own live label in plain words (Expert view: the full banner).
    assert "Replay: these are recorded runs" in banner and "Recorded live run" in banner
    assert "recomputed now" in page.locator(".hud-ring").inner_text()
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
        settle(page)
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
    if not fit["observed"].get("origins"):  # plain mode: the PASS reason sentence
        assert (
            f"{fit['observed']['judged_uses']} uses of a fitted step were checked"
            in flow
        )
    assert "CC BY 4.0" in page.locator(".st-key-banner").inner_text()


def test_the_live_view_with_the_kill_switch_off(app, page):
    """Phase 2: the recorded original's ring and reticle (original only) and the
    live-unavailable state with its next action; nothing to start."""
    open_hosted(page, app)
    page.get_by_role("link", name="Try It Live").click()  # the navigation
    state = page.locator(".st-key-live-unavailable")
    state.wait_for(timeout=30_000)
    assert "LIVE UNAVAILABLE" in state.inner_text()
    assert "Live calls are unavailable; recorded runs remain available." in (
        state.inner_text()
    )
    assert "Next action:" in state.inner_text()
    assert page.locator(".hud-ret").count() == 1
    assert (
        "Verified revision" not in page.locator(".st-key-hosted-original").inner_text()
    )
    assert page.get_by_role("button", name="Start the live session").count() == 0
    shots(page, "p2_46_hosted_live_original", page.locator(".st-key-hosted-original"))
    shots(page, "p2_47_hosted_live_unavailable", state)
