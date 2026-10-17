"""T-09 in the browser: the UCI HAR flawed variant and clean control, each through the full path.

Select, confirm, run, approve the original by TYPING its 12-character prefix (the browser
approver; no scripted approval), read the outcome, the conditional containment PASS, the
provenance scope and the descriptive protocol comparison, and check the export hashes. Every
value is compared with the run's artifacts. Needs the retrieved data (benchmarks/real_sensor/
retrieve.py); without it the tests skip and say so.
"""

import hashlib
import json
import os
import time
from pathlib import Path

import pytest
from helpers import (
    answer,
    click_run,
    open_app,
    shot,
    shown_hash,
    table_rows,
    text,
    wait_finished,
    wait_idle,
)

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "benchmarks" / "real_sensor" / "har_flawed" / "table.parquet"
FLAWED_LABEL = "har_flawed (ATLAS-authored flawed variant)"
TIMINGS: dict[str, float] = {}

pytestmark = pytest.mark.skipif(
    not TABLE.is_file(),
    reason="UCI HAR not retrieved: run uv run --locked python benchmarks/real_sensor/retrieve.py",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome_of(run: Path) -> dict:
    return json.loads((run / "original" / "outcome.json").read_text(encoding="utf-8"))


def metric_of(outcome: dict) -> dict:
    d = next(
        x
        for x in outcome["descriptive"]
        if x["result_id"] == "metric.recomputed_primary"
    )
    obs = d["observed"]
    return obs["aggregates"]["development_eval"][obs["primary_metric"]]


def full_path(page, app, label: str, name: str):
    open_app(page, app)
    page.get_by_test_id("stSidebar").get_by_text(label, exact=True).click()
    page.locator(".st-key-claim-statement").wait_for()
    wait_idle(page)  # the rerun after the project click has finished
    shot(page, f"har_{name}_01_claim")
    started = time.monotonic()
    click_run(page)
    prefix_source = shown_hash(page, None)  # the original's approval panel
    asked = time.monotonic()
    shot(page, f"har_{name}_02_typed_approval")
    answer(page, prefix_source[:12])  # typed, as a person reads it off the screen
    run = wait_finished(page, app, timeout=300)
    TIMINGS[name] = {
        "click_to_approval_panel_s": round(asked - started, 1),
        "approval_to_finished_s": round(time.monotonic() - asked, 1),
    }
    report = json.loads((run / "agent_report.json").read_text(encoding="utf-8"))
    approvals = [
        json.loads(x)
        for x in (run / "agent_log.jsonl").read_text(encoding="utf-8").splitlines()
        if '"event": "approval"' in x
    ]
    return run, report, approvals


def common_checks(page, run, report, approvals):
    # The original's approval was typed in the browser: the CLI rule, full hash recorded.
    assert [a["approver_reason"] for a in approvals] == ["confirmed"]
    assert len(approvals[0]["approval"]["candidate_hash"]) == 64
    assert report["comparison"]["original"]["runner"] == "docker_isolated"
    assert "NON-LIVE RUN" in text(page, "banner")
    # Provenance scope: the engine's limitation and the catalogue's dataset note.
    provenance = text(page, "provenance-notes")
    assert "Provenance begins at the supplied feature table." in provenance
    assert (
        "normalization was fit globally" in provenance
        and "not established" in provenance
    )
    # Export: recomputed hashes match the files and the engine's recorded hashes.
    rows = {r[0]: r for r in table_rows(page, "export")}
    assert rows["agent_report.json"][1] == sha(run / "agent_report.json")
    assert rows["agent_log.jsonl"][2] == "matches"
    assert rows["original/outcome.json"][1] == sha(run / "original" / "outcome.json")
    assert rows["original/outcome.json"][2] == "matches"


@pytest.fixture(scope="module")
def flawed(app, docker, browser):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    result = full_path(page, app, FLAWED_LABEL, "flawed")
    yield page, *result
    context.close()


def test_har_flawed_full_path(flawed):
    page, run, report, approvals = flawed
    common_checks(page, run, report, approvals)
    outcome = outcome_of(run)
    assert (
        report["scientific_outcomes"]["original"]
        == outcome["outcome"]
        == "VIOLATION_FOUND"
    )
    assert "VIOLATION_FOUND" in text(page, "headline-original")
    assert "ATLAS-authored flawed variant" in text(page, "claim-statement")
    shown_fails = [r[1] for r in table_rows(page, "finding-checks") if r[0] == "FAIL"]
    assert shown_fails == [
        a["assertion_id"] for a in outcome["assertions"] if a["status"] == "FAIL"
    ]
    window = next(
        r
        for r in table_rows(page, "finding-checks")
        if r[1] == "split.no_window_overlap"
    )
    assert window[:3] == ["NOT_ASSESSED", "split.no_window_overlap", "missing_metadata"]
    assert (
        page.locator(".st-key-conditional-passes").count() == 0
    )  # no containment PASS
    page.locator(".st-key-finding-metric").scroll_into_view_if_needed()
    shot(page, "har_flawed_03_finding")
    assert "Run har_clean to compare" in text(page, "protocol-comparison")
    page.locator(".st-key-card-trust").scroll_into_view_if_needed()
    shot(page, "har_flawed_04_export")


def test_har_clean_full_path_and_the_descriptive_comparison(flawed, app, docker, page):
    _, flawed_run, *_ = flawed
    run, report, approvals = full_path(page, app, "har_clean", "clean")
    common_checks(page, run, report, approvals)
    outcome = outcome_of(run)
    assert (
        report["scientific_outcomes"]["original"]
        == outcome["outcome"]
        == "NO_VIOLATION_FOUND"
    )
    assert "NO_VIOLATION_FOUND" in text(page, "headline-original")
    assert [r[0] for r in table_rows(page, "finding-checks")] == ["PASS"] * len(
        outcome["assertions"]
    )
    # The containment PASS is shown as conditional, with the engine's limitation verbatim.
    window = next(
        a
        for a in outcome["assertions"]
        if a["assertion_id"] == "split.no_window_overlap"
    )
    conditional = text(page, "conditional-passes")
    assert "Conditional PASS: split.no_window_overlap" in conditional
    assert "split.no_group_overlap" in conditional
    assert window["limitations"][0].split(": source")[0] in conditional
    assert "not independently verified" in conditional
    page.locator(".st-key-conditional-passes").scroll_into_view_if_needed()
    shot(page, "har_clean_03_conditional_pass")
    # The descriptive comparison: both values read from the two runs' outcome.json files.
    page.locator(".st-key-protocol-comparison").scroll_into_view_if_needed()
    shot(page, "har_clean_04_protocol_comparison")
    rows = {r[0]: r for r in table_rows(page, "protocol-comparison")}
    mine, theirs = metric_of(outcome), metric_of(outcome_of(flawed_run))
    assert rows["har_clean"][1] == run.name and rows[FLAWED_LABEL][1] == flawed_run.name
    assert rows["har_clean"][3] == f"{mine['mean_over_folds']['value']:.4f}"
    assert rows[FLAWED_LABEL][3] == f"{theirs['mean_over_folds']['value']:.4f}"
    assert rows[FLAWED_LABEL][6] == "0.9064" and rows["har_clean"][6] == "none"
    caption = text(page, "protocol-comparison")
    assert "Descriptive only, not causal" in caption
    page.locator(".st-key-card-trust").scroll_into_view_if_needed()
    shot(page, "har_clean_05_export")
    out = os.environ.get("ATLAS_UI_TIMINGS")
    if out:
        Path(out).write_text(json.dumps(TIMINGS, indent=2) + "\n", encoding="utf-8")
    for name, t in TIMINGS.items():
        assert t["approval_to_finished_s"] < 240, (name, t)
