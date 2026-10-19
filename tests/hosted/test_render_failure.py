"""T-12 fix pass 2: a render failure leaves no partial result (review 2, P2-2).

Codex's C4 reproduction (runs/t12-review/probes/test_faults.py::
test_c4_render_failure_keeps_headline) made `st.markdown` raise immediately after the outcome
code was emitted: the page kept the VIOLATION_FOUND headline without its label or caveat.
`ui.results.finished_run` now renders into one clearable placeholder; on any exception it is
cleared and only the fixed RENDER_FAILED error is shown. The same function renders the hosted
live session, both recorded viewers and the local page's finished run, so the hosted page and
the local page are both tested here. Offline: a completed hosted run with mocked Token Factory
and fake reservations; the local run is a copy of the bundled live run 6 record.
"""

import hashlib
import logging
import shutil
from datetime import UTC, datetime

import hosted_helpers as H
import pytest
from streamlit.testing.v1 import AppTest

from atlas.agent import controller as ctl
from atlas.agent.budget import Budget
from atlas.agent.network import deny_network
from atlas.hosted import bundle, page
from atlas.hosted import session as hs
from atlas.runner import docker as dr
from atlas.ui import artifacts as A
from atlas.ui import recorded as RR
from atlas.ui import results as R
from atlas.ui import views as V
from atlas.ui import worker

APP = str(H.ROOT / "app.py")
INJECTED = "review injected rendering failure"
LOCAL_RUN = H.BUNDLE / "live6" / "agent-s01_faulty-877f8245a8a2"


class Tripwire(Exception):
    pass


def trip(*args, **kwargs):
    raise Tripwire("an execution step was reached")


# -- the two injections ------------------------------------------------------------------------


def fail_after_headline(monkeypatch):
    """Codex's C4 injection: st.markdown raises right after emitting the outcome code."""
    original = V.st.markdown

    def markdown(body, *args, **kwargs):
        result = original(body, *args, **kwargs)
        if (
            isinstance(body, str)
            and body.startswith("## :")
            and "VIOLATION_FOUND" in body
        ):
            raise RuntimeError(INJECTED + " after headline delta")
        return result

    monkeypatch.setattr(V.st, "markdown", markdown)


def fail_after_table(monkeypatch):
    """The following table: the Finding card's required-set table is drawn, then raises."""
    original = V.required_table

    def required_table(rows, key):
        original(rows, key)
        if key == "finding-checks":
            raise RuntimeError(INJECTED + " after the table")

    monkeypatch.setattr(V, "required_table", required_table)


INJECTIONS = {"headline": fail_after_headline, "table": fail_after_table}


# -- helpers -----------------------------------------------------------------------------------


def shown(at) -> str:
    parts = []
    for kind in (
        "markdown",
        "caption",
        "subheader",
        "title",
        "info",
        "warning",
        "error",
    ):
        parts += [str(x.value) for x in getattr(at, kind)]
    parts += [str(x.value) for x in at.table]
    return "\n".join(parts)


def record_state(run_dir):
    report_bytes = (run_dir / "agent_report.json").read_bytes()
    hashes = {
        p.relative_to(run_dir).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(run_dir.rglob("*"))
        if p.is_file()
    }
    return report_bytes, hashes


def assert_cleared(at, caplog, run_dir, before, original_title):
    text = shown(at)
    assert not at.exception  # no exception element, so no exception text
    assert [e.value for e in at.error] == [R.RENDER_FAILED]
    # No outcome code, label, caveat or partial result card remains.
    for partial in (
        "VIOLATION_FOUND",
        A.OUTCOME_LABELS["VIOLATION_FOUND"],
        A.CAVEAT,
        original_title,
        "2. Analysis",
        "3. Finding",
        "Terminal state",
        "6. Trust and export",
    ):
        assert partial not in text, partial
    # The required-set table is gone (the local claim card's own fields table may remain).
    assert not [t for t in at.table if "assertion" in t.value.columns]
    assert INJECTED not in text and "RuntimeError" not in text
    # One fixed event code, nothing else (no exception text, path or value).
    events = [r for r in caplog.records if r.name == R.__name__]
    assert [r.getMessage() for r in events] == [R.RENDER_FAILED_EVENT]
    assert all(r.exc_info is None and not r.args for r in events)
    assert INJECTED not in caplog.text and str(run_dir) not in caplog.text
    # The saved run record is unchanged and its recorded hashes still verify.
    assert record_state(run_dir) == before
    report = A.read_json(run_dir / "agent_report.json")
    assert RR.intact(RR.verify(run_dir, report))


# -- the hosted page ---------------------------------------------------------------------------


@pytest.fixture
def hosted_run(monkeypatch, tmp_path):
    """A completed hosted live session (mocked provider, fake reservations), as the page's
    LiveHandle. Docker and the local registry are tripwires."""
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_HOSTED_RUNS_DIR", str(tmp_path / "hosted-runs"))
    for name in ("NEBIUS_API_KEY", "DATABASE_URL", "JUDGE_ACCESS_CODE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(dr, "probe", trip)
    monkeypatch.setattr(dr, "_docker", trip)
    monkeypatch.setattr(worker.Registry, "start", trip)
    provider = H.live6_provider()
    with deny_network():
        result = ctl.run_agent(
            H.S01, tmp_path / "runs", H.client(provider), H.SpyApprover(),
            budget=Budget(max_attempts=6), original=bundle.live_original(),
            live_authorized=True, spend=H.decided_limits(), hosted=True,
            reservations=H.FakeReservations(provider=provider),
        )  # fmt: skip
    assert result.terminal_state == ctl.REPORT, result.reason
    assert result.report["scientific_outcomes"]["original"] == "VIOLATION_FOUND"
    outcome = hs.Outcome(
        status="ran",
        route="public",
        run_dir=result.run_dir,
        terminal_state=result.terminal_state,
    )
    return page.LiveHandle(tmp_path, outcome=outcome)


def hosted_page(handle):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["hosted_view"] = page.LIVE_VIEW
    at.session_state["hosted_live"] = handle
    with H.loopback_only():
        at.run()
    return at


def test_the_hosted_finished_run_renders_whole_without_a_fault(hosted_run):
    """Control: the same page shows the headline, caveat and tables when nothing fails."""
    at = hosted_page(hosted_run)
    assert not at.exception and not at.error
    text = shown(at)
    assert "VIOLATION_FOUND" in text and A.CAVEAT in text and "3. Finding" in text
    assert [t for t in at.table if "assertion" in t.value.columns]


@pytest.mark.parametrize("where", list(INJECTIONS))
def test_a_hosted_render_failure_leaves_no_partial_result(
    monkeypatch, caplog, hosted_run, where
):
    run_dir = hosted_run.outcome.run_dir
    before = record_state(run_dir)
    INJECTIONS[where](monkeypatch)
    caplog.set_level(logging.INFO)
    at = hosted_page(hosted_run)
    assert_cleared(at, caplog, run_dir, before, "Original: computed by ATLAS")
    # The page around the results still renders (claim, route), and nothing executed.
    text = shown(at)
    assert "1. Claim" in text and "Route: public demo budget." in text


# -- the local page ----------------------------------------------------------------------------


@pytest.fixture
def local_run(monkeypatch, tmp_path):
    """The local page with a finished agent run in the registry (a copy of live run 6)."""
    monkeypatch.delenv("ATLAS_HOSTED", raising=False)
    monkeypatch.setenv(worker.RUNS_ENV, str(tmp_path / "ui-runs"))
    monkeypatch.setattr(
        dr, "probe", lambda *a, **k: dr.Capability("unavailable", "test")
    )
    monkeypatch.setattr(worker.Registry, "start", trip)
    run_dir = tmp_path / "ui-runs" / LOCAL_RUN.name
    shutil.copytree(LOCAL_RUN, run_dir)
    channel = tmp_path / "channel"
    channel.mkdir()
    now = datetime.now(UTC).isoformat()
    handle = worker.RunHandle(
        id="render-test", project="s01_faulty", mode=worker.AGENT, script=None,
        runs_root=tmp_path / "ui-runs", channel=channel, started_utc=now,
        before=frozenset(), finished_utc=now, run_dir=run_dir,
    )  # fmt: skip
    monkeypatch.setattr(worker.registry(), "_handle", handle)
    return run_dir


def local_page():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at


def test_the_local_finished_run_renders_whole_without_a_fault(local_run):
    at = local_page()
    assert not at.exception and not at.error
    text = shown(at)
    assert "VIOLATION_FOUND" in text and A.CAVEAT in text and "3. Finding" in text
    assert [t for t in at.table if "assertion" in t.value.columns]


@pytest.mark.parametrize("where", list(INJECTIONS))
def test_a_local_render_failure_leaves_no_partial_result(
    monkeypatch, caplog, local_run, where
):
    before = record_state(local_run)
    INJECTIONS[where](monkeypatch)
    caplog.set_level(logging.INFO)
    at = local_page()
    assert_cleared(at, caplog, local_run, before, "Original, trusted evaluator")
    assert "1. Claim" in shown(at)
