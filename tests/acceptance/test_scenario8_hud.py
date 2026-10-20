"""Scenario 8 (UI design pass, phase 1): the HUD on the local recorded-run viewer.

Copies of the bundled live run 6 (`demo/recorded/live6/...`, only read) sit under this module's
recorded-run root: one intact, one with one byte changed in the candidate's outcome.json. The
page must show, in the first viewport at 1440 x 900 and 1280 x 800, the integrity ring, both
outcome reticles, both leak maps and both fit-scope flows, with values equal to the files; the
changed copy shows the broken ring and no outcome or diagram. Motion plays once and never under
reduced motion; nothing is fetched from outside the app. With ATLAS_UI_SCREENS set, screenshots
(and a video of the first load) are saved there.
"""

import json
import os
import shutil
import time
from pathlib import Path

import pytest
from helpers import settle, shot, text, wait_idle

from atlas.ui import artifacts as A

ROOT = Path(__file__).resolve().parents[2]
NAME = "agent-s01_faulty-877f8245a8a2"
SOURCE = ROOT / "demo" / "recorded" / "live6" / NAME
INTACT = f"live6/{NAME}"
TAMPERED = f"live6-tampered/{NAME}"
VIEWPORTS = [(1440, 900), (1280, 800)]
PHONE = (390, 844)


def app_env(base: Path) -> dict:
    recorded = base / "recorded"
    shutil.copytree(SOURCE, recorded / INTACT)
    shutil.copytree(SOURCE, recorded / TAMPERED)
    outcome = recorded / TAMPERED / "candidates" / "c1" / "outcome.json"
    data = bytearray(outcome.read_bytes())
    i = next(i for i, b in enumerate(data) if chr(b).isdigit())
    data[i] = ord(str((int(chr(data[i])) + 1) % 10))  # one byte; still valid JSON
    outcome.write_bytes(bytes(data))
    return {"ATLAS_UI_RECORDED_DIR": str(recorded)}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def outside_requests(page) -> list[str]:
    """Every request the page makes to anything but the app server."""
    seen: list[str] = []
    page.on(
        "request",
        lambda r: (
            seen.append(r.url)
            if not r.url.startswith(
                ("http://localhost", "ws://localhost", "data:", "blob:")
            )
            else None
        ),
    )
    return seen


def open_recorded(page, app, label: str) -> None:
    page.goto(app.url + "/try_it_live")  # Try It Live
    page.get_by_role("button", name="Confirm & run").wait_for(timeout=60_000)
    width = (page.viewport_size or {}).get("width", 1440)
    if width < 600:
        page.get_by_test_id("stExpandSidebarButton").click()
    page.get_by_test_id("stSidebar").get_by_text(
        "Open a recorded run", exact=True
    ).click()
    choose(page, label)


def choose(page, label: str) -> None:
    box = page.get_by_role("combobox", name="Recorded run")
    box.wait_for()
    wait_idle(page)
    box.click()
    page.get_by_role("option", name=f"{label} (agent)", exact=True).click()
    page.locator(".st-key-card-integrity").wait_for(timeout=30_000)
    wait_idle(page)
    if (page.viewport_size or {}).get("width", 1440) < 600:
        page.keyboard.press("Escape")
        close = page.get_by_test_id("stSidebarCollapseButton")
        if close.count() and close.is_visible():
            close.click()
        time.sleep(0.5)


def in_viewport(page, selector: str) -> list[tuple[float, float]]:
    return page.locator(selector).evaluate_all(
        "els => els.map(e => { const r = e.getBoundingClientRect(); return [r.top, r.bottom]; })"
    )


@pytest.mark.parametrize("size", VIEWPORTS, ids=lambda s: f"{s[0]}x{s[1]}")
def test_the_hero_fills_the_first_viewport_with_the_runs_own_values(app, page, size):
    w, h = size
    page.set_viewport_size({"width": w, "height": h})
    outside = outside_requests(page)
    open_recorded(page, app, INTACT)
    page.locator(".hud-flow").first.wait_for()
    time.sleep(1.5)  # the three beats end at 1.2 s
    shot(page, "s8_01_live6_hero")
    run = app.runs.parent / "recorded" / INTACT
    orig, cand = (
        read(run / "original/outcome.json"),
        read(run / "candidates/c1/outcome.json"),
    )

    # The briefing, the ring and both reticles sit inside the first viewport (phase 2: the
    # briefing leads the run, so the leak maps and flows follow directly below the hero).
    for selector, count in ((".hud-brief", 1), (".hud-ring svg", 1), (".hud-ret", 2)):
        boxes = in_viewport(page, selector)
        assert len(boxes) == count, selector
        assert all(0 <= top and bottom <= h for top, bottom in boxes), (selector, boxes)
    hero_bottom = max(b for _, b in in_viewport(page, ".hud-ret"))
    for selector in (".hud-leak", ".hud-flow"):
        boxes = in_viewport(page, selector)
        assert len(boxes) == 2 and all(top >= hero_bottom for top, _ in boxes), selector

    hero = page.locator(".st-key-hud-hero").inner_text()
    assert "49/49" in hero and "INTACT" in hero
    for code in (orig["outcome"], cand["outcome"]):
        assert code in hero and A.OUTCOME_LABELS[code] in hero
    assert hero.count(A.CAVEAT) == 2
    assert "4 of 9 required checks FAIL" in hero and "4 FAIL → PASS" in hero
    assert "executed in the isolated Docker runner after typed approval" in hero
    assert "original/outcome.json" in hero and "candidates/c1/outcome.json" in hero

    # Leak map cells equal the files (32 on both sides in the original, none in the candidate).
    assert page.locator(".hud-pane-orig td.hud-both").count() == 32
    assert page.locator(".hud-pane-cand td.hud-both").count() == 0
    assert page.locator(".hud-pane-cand td.hud-none").count() == 32
    flow = page.locator(".hud-pane-orig .hud-flow").inner_text()
    assert "SelectKBest" in flow and "(fit: global)" in flow and "[160 rows]" in flow

    # Rendered colours are the spec's; the fonts are the vendored ones; nothing outside.
    color = "e => getComputedStyle(e).color"
    codes = page.locator(".hud-ret-code")
    assert codes.nth(0).evaluate(color) == "rgb(248, 113, 113)"  # #F87171
    assert codes.nth(1).evaluate(color) == "rgb(74, 222, 128)"  # #4ADE80
    assert page.locator(".hud-ring-n").evaluate("e => getComputedStyle(e).fill") == (
        "rgb(103, 232, 249)"  # #67E8F9, the verified signal
    )
    loaded = page.evaluate(
        "() => document.fonts.ready.then(() => [...document.fonts]"
        ".filter(f => f.status === 'loaded').map(f => f.family))"
    )
    assert {"IBM Plex Sans", "IBM Plex Mono", "IBM Plex Sans Condensed"} <= set(loaded)
    assert outside == []
    assert "LIVE RUN" in text(page, "banner")
    assert "not re-executed here" in text(page, "recorded-label")


@pytest.mark.parametrize("size", [*VIEWPORTS, PHONE], ids=lambda s: f"{s[0]}x{s[1]}")
def test_the_diagrams_matrix_and_trust_sections(app, page, size):
    page.set_viewport_size({"width": size[0], "height": size[1]})
    open_recorded(page, app, INTACT)
    for key, name in (
        ("hud-evidence", "s8_02_live6_diagrams_and_matrix"),
        ("card-analysis", "s8_03_live6_track_and_gauge"),
        ("card-trust", "s8_04_live6_trust"),
    ):
        el = page.locator(f".st-key-{key}")
        el.scroll_into_view_if_needed()
        time.sleep(0.3)
        folder = os.environ.get("ATLAS_UI_SCREENS")
        if folder:
            settle(page)
            el.screenshot(path=str(Path(folder) / f"{name}_{size[0]}x{size[1]}.png"))
    tiles = page.locator(".hud-pane-cand .hud-move")
    assert [t for t in tiles.all_text_contents() if t] == ["FAIL → PASS"] * 4
    track = page.locator(".st-key-hud-track").inner_text()
    assert "5 of 6" in track and "5 of 12" in track and "2 of 2" in track
    gauge = page.locator(".st-key-hud-gauge").inner_text()
    assert "0.0190884 of 0.0648" in gauge
    frame = page.locator(".st-key-model-text-0")
    assert frame.evaluate("e => getComputedStyle(e).borderTopStyle") == "dashed"
    assert "MODEL-WRITTEN · UNTRUSTED" in frame.inner_text()
    assert frame.locator(".hud-ret, .hud-code").count() == 0


@pytest.mark.parametrize("size", [*VIEWPORTS, PHONE], ids=lambda s: f"{s[0]}x{s[1]}")
def test_a_changed_copy_shows_the_broken_ring_and_nothing_else(app, page, size):
    page.set_viewport_size({"width": size[0], "height": size[1]})
    open_recorded(page, app, TAMPERED)
    time.sleep(1.0)
    shot(page, "s8_05_tampered")
    assert "evidence changed since recording" in text(page, "integrity-failed")
    ring = page.locator(".st-key-hud-ring")
    assert "EVIDENCE" in ring.inner_text() and "CHANGED" in ring.inner_text()
    assert page.locator(".hud-seg-bad").count() == 1
    for absent in (".hud-ret", ".hud-ev", ".hud-lm", ".hud-flow", ".hud-tile"):
        assert page.locator(absent).count() == 0, absent
    for key in ("card-finding", "card-comparison", "headline-original"):
        assert page.locator(f".st-key-{key}").count() == 0


def test_the_phone_layout_and_its_toggle(app, page):
    page.set_viewport_size({"width": PHONE[0], "height": PHONE[1]})
    open_recorded(page, app, INTACT)
    time.sleep(1.5)
    shot(page, "s8_06_phone_hero")
    width = page.evaluate("() => [document.documentElement.scrollWidth, innerWidth]")
    assert width[0] <= width[1]  # no page-level horizontal scroll
    ev = page.locator(".st-key-hud-evidence")
    ev.scroll_into_view_if_needed()
    visibility = "els => els.map(e => getComputedStyle(e).visibility)"
    panes = page.locator(".hud-pane")
    assert panes.evaluate_all(visibility) == ["visible", "hidden"]
    region = page.locator(".hud-pane-orig .hud-scroll")
    assert (
        region.get_attribute("role") == "region"
        and region.get_attribute("tabindex") == "0"
    )
    assert page.locator(".hud-pane-orig .hud-legend").is_visible()
    cell = page.locator(".hud-pane-orig td.hud-both").first
    assert cell.locator(".hud-sq").count() == 1 and cell.inner_text() == ""
    assert cell.get_attribute("aria-label").endswith(": on both sides")
    folder = os.environ.get("ATLAS_UI_SCREENS")
    if folder:
        settle(page)
        ev.screenshot(
            path=str(Path(folder) / "s8_07_phone_toggle_original_390x844.png")
        )
    page.locator("label.hud-tg-cand").click()
    time.sleep(0.4)  # the 200 ms cross-fade
    assert panes.evaluate_all(visibility) == ["hidden", "visible"]
    if folder:
        settle(page)
        ev.screenshot(
            path=str(Path(folder) / "s8_08_phone_toggle_candidate_390x844.png")
        )
    page.locator("label.hud-tg-orig").click()
    time.sleep(0.4)
    assert panes.evaluate_all(visibility) == ["visible", "hidden"]


def test_motion_plays_once_and_never_under_reduced_motion(app, browser):
    folder = os.environ.get("ATLAS_UI_SCREENS")
    video = {"record_video_dir": str(Path(folder) / "video")} if folder else {}
    context = browser.new_context(viewport={"width": 1440, "height": 900}, **video)
    page = context.new_page()
    page.goto(app.url + "/try_it_live")  # Try It Live
    page.get_by_role("button", name="Confirm & run").wait_for(timeout=60_000)
    page.get_by_test_id("stSidebar").get_by_text(
        "Open a recorded run", exact=True
    ).click()
    box = page.get_by_role("combobox", name="Recorded run")
    box.wait_for()
    wait_idle(page)
    box.click()
    page.get_by_role("option", name=f"{INTACT} (agent)", exact=True).click()
    page.locator(".hud-ret").first.wait_for(timeout=30_000)
    start = time.time()
    frames = []
    for at in (0.05, 0.25, 0.5, 0.8, 1.4):
        time.sleep(max(0.0, at - (time.time() - start)))
        if folder:
            path = Path(folder) / f"s8_09_motion_t{int(at * 1000):04d}ms_1440x900.png"
            page.screenshot(path=str(path))
            frames.append(path.name)
    names = page.locator(".hud-a-seg").first.evaluate(
        "e => getComputedStyle(e).animationName"
    )
    assert names == "hud-seg"
    assert page.locator(".hud-anim").count() > 0
    # Another run, then back: the first run renders settled (played), with no animation class.
    choose(page, TAMPERED)
    choose(page, INTACT)
    page.locator(".hud-ret").first.wait_for()
    assert page.locator(".hud-anim").count() == 0
    assert (
        page.locator(".hud-a-seg, .hud-a-light, .hud-a-draw, .hud-a-flip").count() == 0
    )
    context.close()

    reduced = browser.new_context(
        viewport={"width": 1440, "height": 900}, reduced_motion="reduce"
    )
    page = reduced.new_page()
    open_recorded(page, app, INTACT)
    page.locator(".hud-ret").first.wait_for()
    for selector in (".hud-a-seg", ".hud-a-light", ".hud-a-draw", ".hud-a-flip"):
        el = page.locator(selector).first
        assert el.evaluate("e => getComputedStyle(e).animationName") == "none", selector
    shot(page, "s8_10_reduced_motion")
    reduced.close()
