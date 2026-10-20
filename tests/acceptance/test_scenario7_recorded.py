"""Scenario 7 (T-07 follow-up, slice 4h): a recorded run opened read-only.

Live run 6 (`runs/live6/agent-s01_faulty-877f8245a8a2/`, git-ignored, so only on the machine
that recorded it) is copied into this module's basetemp; runs/live6 itself is only read. The
page lists the copy under "Open a recorded run", re-verifies every recorded hash and renders
the run's own cards with its LIVE label, without executing anything or asking for approval.
A second copy with one byte changed in a candidate's outcome.json shows "evidence changed
since recording" and no outcome headline.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from helpers import shot, table_rows, text, wait_idle

from atlas.ui import artifacts as A

ROOT = Path(__file__).resolve().parents[2]
NAME = "agent-s01_faulty-877f8245a8a2"
SOURCE = ROOT / "runs" / "live6" / NAME
INTACT = f"live6/{NAME}"
TAMPERED = f"live6-tampered/{NAME}"
FLIPPED = []  # the tampered byte's position, set by app_env
_SOURCE_DIGEST = {}


def tree_digest(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def app_env(base: Path) -> dict:
    """Copies of live run 6 under the server's recorded-run root: one intact, one tampered."""
    if not SOURCE.is_dir():
        pytest.skip(f"{SOURCE.relative_to(ROOT)} is not on this machine (git-ignored)")
    _SOURCE_DIGEST["before"] = tree_digest(SOURCE)
    recorded = base / "recorded"
    shutil.copytree(SOURCE, recorded / INTACT)
    shutil.copytree(SOURCE, recorded / TAMPERED)
    outcome = recorded / TAMPERED / "candidates" / "c1" / "outcome.json"
    data = bytearray(outcome.read_bytes())
    i = next(i for i, b in enumerate(data) if chr(b).isdigit())
    data[i] = ord(str((int(chr(data[i])) + 1) % 10))  # one byte; still valid JSON
    outcome.write_bytes(bytes(data))
    FLIPPED.append(i)
    return {"ATLAS_UI_RECORDED_DIR": str(recorded)}


def recorded_dir(app) -> Path:
    return app.runs.parent / "recorded"


def open_recorded(page, app, label: str) -> None:
    page.goto(app.url + "/try_it_live")  # Try It Live
    page.get_by_role("button", name="Confirm & run").wait_for(timeout=60_000)
    page.get_by_test_id("stSidebar").get_by_text(
        "Open a recorded run", exact=True
    ).click()
    page.get_by_role("combobox", name="Recorded run").wait_for()
    wait_idle(page)
    page.get_by_role("combobox", name="Recorded run").click()
    page.get_by_role("option", name=f"{label} (agent)", exact=True).click()
    page.locator(".st-key-card-integrity").wait_for(timeout=30_000)
    wait_idle(page)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_live_run_6_opens_read_only_with_its_own_outcomes(app, page):
    run = recorded_dir(app) / INTACT
    report = read(run / "agent_report.json")
    original = read(run / "original" / "outcome.json")
    candidate = read(run / "candidates" / "c1" / "outcome.json")
    open_recorded(page, app, INTACT)
    shot(page, "s7_01_recorded_live6_top")

    # The run's own LIVE label, and that it is recorded, not re-executed here.
    banner = text(page, "banner")
    assert "LIVE RUN" in banner and "NON-LIVE" not in banner
    assert report["live"] is True and report["banner"] in banner
    finished = A.short_time(A.run_finished_utc(report))
    assert f"Recorded run, finished {finished}; not re-executed here" in text(
        page, "recorded-label"
    )
    assert "intact" in text(page, "integrity-ok")

    # The outcome headlines equal the artifacts.
    assert original["outcome"] == report["scientific_outcomes"]["original"]
    assert original["outcome"] == "VIOLATION_FOUND"
    headline = [x.strip() for x in text(page, "headline-original").splitlines()]
    assert [x for x in headline if x][:3] == [
        "Original, trusted evaluator",
        original["outcome"],
        A.OUTCOME_LABELS[original["outcome"]],
    ]
    assert candidate["outcome"] == "NO_VIOLATION_FOUND"
    assert candidate["outcome"] in text(page, "candidate-1")
    rows = table_rows(page, "scroll-comparison-1")
    assert rows[0] == ["Outcome", original["outcome"], candidate["outcome"]]
    om, cm = A.primary_metric(original), A.primary_metric(candidate)
    assert om.name == "balanced_accuracy"
    assert (om.pooled, cm.pooled) == pytest.approx((0.68125, 0.675), abs=1e-12)
    metric = next(r for r in rows if r[0] == "Independent primary metric")
    assert A.fmt_metric(om.pooled) in metric[1] and A.fmt_metric(cm.pooled) in metric[2]

    # The FAIL -> PASS rows.
    (entry,) = report["comparison"]["candidates"]
    expected = [
        [s["assertion_id"], s["original"], s["candidate"], "FAIL → PASS"]
        for s in entry["status_by_assertion"]
        if s["original"] != s["candidate"]
    ]
    assert [e[0] for e in expected] == [
        "split.no_group_overlap",
        "split.sampling_unit_disjoint",
        "split.repeated_measures_rule",
        "fit.state_dependencies_within_fold_train",
    ]
    shown = [r for r in table_rows(page, "status-changes-1") if r[3] != "unchanged"]
    assert shown == expected
    page.locator(".st-key-card-comparison").scroll_into_view_if_needed()
    shot(page, "s7_02_recorded_live6_comparison")

    # Proposals: the executed one and the rejected one with its code, both model-written.
    first, second = text(page, "proposal-1"), text(page, "proposal-2")
    assert "executed" in first and "new_source" in first
    assert "rejected" in second and "syntax_error" in second
    for shown_text in (first, second):
        assert "model-written (untrusted)" in shown_text
        assert "matches the recorded diff_sha256" in shown_text
    page.locator(".st-key-card-revision").scroll_into_view_if_needed()
    shot(page, "s7_03_recorded_live6_revision")

    # Read-only: nothing can be started or approved, and nothing ran.
    assert page.get_by_role("button", name="Confirm & run").count() == 0
    assert page.get_by_role("button", name="Start a new run").count() == 0
    assert page.locator(".st-key-approval-panel").count() == 0
    assert not app.runs.exists() or not any(app.runs.iterdir())
    assert "Estimated cost (not a bill)" in text(page, "cost")
    page.locator(".st-key-card-trust").scroll_into_view_if_needed()
    shot(page, "s7_04_recorded_live6_trust")


def test_a_tampered_copy_shows_evidence_changed_and_no_headline(app, page):
    run = recorded_dir(app) / TAMPERED
    report = read(run / "agent_report.json")
    open_recorded(page, app, TAMPERED)
    assert "evidence changed since recording" in text(page, "integrity-failed")
    rows = table_rows(page, "trace-integrity")
    recorded = report["comparison"]["candidates"][0]["evidence_sha256"]["outcome.json"]
    recomputed = A.sha256_file(run / "candidates" / "c1" / "outcome.json")
    assert recomputed != recorded
    assert rows == [["changed", "candidates/c1/outcome.json", recorded, recomputed]]
    # No outcome headline and no result card from changed evidence.
    for key in (
        "headline-original",
        "card-finding",
        "card-comparison",
        "card-revision",
    ):
        assert page.locator(f".st-key-{key}").count() == 0, key
    assert "LIVE RUN" in text(page, "banner")
    shot(page, "s7_05_recorded_tampered")


def test_runs_live6_itself_is_unchanged(app):
    assert FLIPPED, "the tampered copy was made"
    assert tree_digest(SOURCE) == _SOURCE_DIGEST["before"]
