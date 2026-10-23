"""Scenario 13 (UI restructure slice 1): a case whose bundle changed, in the browser.

The server reads its cases from a copy of demo/recorded (ATLAS_UI_CASES_DIR) in which one
byte of live6's candidates/c1/outcome.json changed; demo/recorded itself is only read. The
live6 card shows "evidence changed" and no outcome; selecting it draws only the
evidence-changed panel: no verdict bar, no step, no outcome. The other cards still verify.
"""

import shutil
from pathlib import Path

from helpers import wait_idle
from playwright.sync_api import expect
from test_scenario12_story import full_page

from atlas.ui import copy as C

ROOT = Path(__file__).resolve().parents[2]
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
WAIT = 30_000  # ms, for each condition after the app settles


def app_env(base: Path) -> dict:
    cases = base / "cases"
    shutil.copytree(ROOT / "demo" / "recorded", cases)
    target = cases / LIVE6 / "candidates" / "c1" / "outcome.json"
    raw = target.read_bytes()
    target.write_bytes(raw[:-1] + (b" " if raw[-1:] != b" " else b"\n"))
    return {
        "ATLAS_HOSTED": "1",
        "HOSTED_LIVE_ENABLED": "false",
        "ATLAS_HOSTED_RUNS_DIR": str(base / "hosted-runs"),
        "ATLAS_UI_CASES_DIR": str(cases),
    }


def test_a_changed_bundle_shows_only_the_evidence_changed_panel(app, page):
    # Release review 2, F4: every check waits for its condition (Playwright's expect, with a
    # timeout) once the app settles; an element drawn a moment later is no longer missed.
    page.goto(app.url)
    panel = page.locator(".st-key-integrity-failed")
    panel.wait_for(timeout=60_000)
    wait_idle(page)
    expect(panel).to_contain_text("evidence changed since recording", timeout=WAIT)
    card = page.locator(".st-key-case-card-on-live6")
    expect(card).to_contain_text(C.CARD_CHANGED, timeout=WAIT)
    expect(card).not_to_contain_text("VIOLATION", timeout=WAIT)
    for key in ("harflawed", "harclean"):
        other = page.locator(f".st-key-case-card-{key}")
        expect(other).to_contain_text("VIOLATION_FOUND", timeout=WAIT)
        expect(other).not_to_contain_text(C.CARD_CHANGED, timeout=WAIT)
    for absent in (
        ".st-key-verdict-bar",
        "[class*='st-key-step-']",
        ".st-key-stepper",
        ".st-key-claim-line",
        ".hud-ret",
        ".hud-brief",
    ):
        expect(page.locator(absent)).to_have_count(0, timeout=WAIT)
    rows = page.locator(".st-key-trace-integrity table tbody tr")
    expect(rows).to_have_count(1, timeout=WAIT)
    expect(rows.first).to_contain_text("candidates/c1/outcome.json", timeout=WAIT)
    full_page(page, "s12_06_tampered_live6")
