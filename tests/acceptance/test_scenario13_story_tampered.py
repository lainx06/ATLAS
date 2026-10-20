"""Scenario 13 (UI restructure slice 1): a case whose bundle changed, in the browser.

The server reads its cases from a copy of demo/recorded (ATLAS_UI_CASES_DIR) in which one
byte of live6's candidates/c1/outcome.json changed; demo/recorded itself is only read. The
live6 card shows "evidence changed" and no outcome; selecting it draws only the
evidence-changed panel: no verdict bar, no step, no outcome. The other cards still verify.
"""

import shutil
from pathlib import Path

from helpers import wait_idle
from test_scenario12_story import full_page

from atlas.ui import copy as C

ROOT = Path(__file__).resolve().parents[2]
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"


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
    page.goto(app.url)
    panel = page.locator(".st-key-integrity-failed")
    panel.wait_for(timeout=60_000)
    wait_idle(page)
    assert "evidence changed since recording" in panel.inner_text()
    card = page.locator(".st-key-case-card-on-live6").inner_text()
    assert C.CARD_CHANGED in card and "VIOLATION" not in card
    for key in ("harflawed", "harclean"):
        other = page.locator(f".st-key-case-card-{key}").inner_text()
        assert C.CARD_CHANGED not in other and "VIOLATION_FOUND" in other
    for absent in (
        ".st-key-verdict-bar",
        "[class*='st-key-step-']",
        ".hud-ret",
        ".hud-brief",
    ):
        assert page.locator(absent).count() == 0, absent
    rows = page.locator(".st-key-trace-integrity table tbody tr")
    assert rows.count() == 1 and "candidates/c1/outcome.json" in rows.first.inner_text()
    full_page(page, "s12_06_tampered_live6")
