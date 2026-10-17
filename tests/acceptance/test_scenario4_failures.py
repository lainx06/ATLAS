"""Scenario 4 (UI_SPEC §9): a provider timeout or an invalid response, and recovery.

Fixture scripts: two timeouts (then a non-JSON reply that is never read), and a non-JSON
reply. The run ends ERROR with the engine's reason, the attempts shown equal
`budget.used.attempts`, there is no hidden retry beyond the one recorded, and "Start a new
run" works. Also the rejected-proposal display (a run with zero executed candidates).
"""

import hashlib
import json

from helpers import (
    answer,
    click_run,
    open_app,
    select_mode,
    select_project,
    select_script,
    shot,
    shown_hash,
    table_rows,
    text,
    wait_finished,
)


def failing_run(page, app, script: str):
    open_app(page, app)
    select_project(page, "s01_faulty")
    select_mode(page, "Agent, fixture replies (NON-LIVE)")
    select_script(page, script)
    click_run(page)
    h = shown_hash(page, None)
    answer(page, h[:12])  # the original runs; the model then fails
    wait_finished(page, app)
    run = app.agent_runs("s01_faulty")[-1]
    return run, json.loads((run / "agent_report.json").read_text(encoding="utf-8"))


def attempts_logged(run):
    return [
        json.loads(x)
        for x in (run / "agent_log.jsonl").read_text(encoding="utf-8").splitlines()
        if '"event": "model_attempt"' in x
    ]


def test_provider_timeout_ends_error_after_one_recorded_retry(app, docker, page):
    run, report = failing_run(page, app, "Provider timeout")
    shot(page, "s4_01_timeout")
    assert report["terminal_state"] == "ERROR"
    assert report["terminal_reason"] == "model_timeout (after one retry)"
    terminal = text(page, "terminal")
    assert "ERROR" in terminal and "model_timeout (after one retry)" in terminal
    used = report["budget"]["used"]
    assert used["attempts"] == 2 and used["retries"] == 1
    rows = table_rows(page, "trace-attempts")
    assert len(rows) == used["attempts"] == len(attempts_logged(run))
    assert [r[3] for r in rows] == ["no", "yes"]  # exactly one retry, the recorded one
    assert (
        f"{used['attempts']} of 6" in page.locator(".st-key-card-analysis").inner_text()
    )
    # The original's findings stay visible.
    assert "VIOLATION_FOUND" in text(page, "headline-original")
    # Recovery: "Start a new run" starts exactly one new run.
    before = len(app.agent_runs("s01_faulty"))
    click_run(page, "Start a new run")
    shown_hash(page, None)  # the new run asks to approve its original
    assert len(app.agent_runs("s01_faulty")) == before + 1
    page.get_by_role("button", name="Close without deciding").click()
    wait_finished(page, app)
    latest = app.agent_runs("s01_faulty")[-1]
    report2 = json.loads((latest / "agent_report.json").read_text(encoding="utf-8"))
    assert report2["terminal_state"] == "NEEDS_INPUT"  # nothing executed
    assert "NEEDS_INPUT" in text(page, "terminal")


def test_invalid_reply_is_a_schema_failure_without_repair(app, docker, page):
    _run, report = failing_run(page, app, "Invalid reply")
    shot(page, "s4_02_invalid_reply")
    assert report["terminal_state"] == "ERROR"
    assert report["terminal_reason"].startswith("schema_failure: ")
    assert report["terminal_reason"] in text(page, "terminal")
    assert report["budget"]["used"]["attempts"] == 1
    rows = table_rows(page, "trace-attempts")
    assert len(rows) == 1 and rows[0][2].startswith("schema_failure")
    assert page.get_by_role("button", name="Start a new run").is_visible()


def test_a_rejected_revision_explains_itself(app, docker, page):
    run, report = failing_run(page, app, "Propose a malformed revision")
    page.locator(".st-key-card-revision").scroll_into_view_if_needed()
    shot(page, "s4_03_rejected_revision")
    (record,) = report["proposals"]
    assert (record["outcome"], record["code"]) == ("rejected", "malformed_diff")
    shown = text(page, "proposal-1")
    assert "rejected" in shown and "malformed_diff" in shown
    assert "validator message; may quote model text" in shown
    assert record["detail"] in shown
    data = (run / record["diff_path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == record["diff_sha256"]
    assert record["diff_sha256"] in shown and "model-written (untrusted)" in shown
    assert "1 proposal: 1 rejected by validation, 0 declined, 0 executed" in text(
        page, "proposal-summary"
    )
    assert page.locator(".st-key-card-comparison").count() == 0
