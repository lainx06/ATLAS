"""T-12 step 4: the hosted page in process (Streamlit AppTest), offline.

With ATLAS_HOSTED=1 the app shows the bundled recorded runs (disclosed as replay, verified
by hash) and one live session per visitor session. Without the kill switch nothing is sent
and the recorded runs still render. A live session (mocked Token Factory, local PostgreSQL)
shows the SPEC §13 labels. Docker, approvals and the local registry are never reached.
"""

import re
import time

import hosted_helpers as H
import pytest
from streamlit.testing.v1 import AppTest

from atlas.runner import docker as dr
from atlas.ui import worker

APP = str(H.ROOT / "app.py")
LABEL = "computed by ATLAS's trusted evaluation functions (recorded 2026-10-18)"


class Tripwire(Exception):
    pass


def trip(name):
    def fail(*args, **kwargs):
        raise Tripwire(f"{name} was reached")

    return fail


@pytest.fixture
def hosted(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_HOSTED_RUNS_DIR", str(tmp_path / "hosted-runs"))
    for name in (
        "NEBIUS_API_KEY",
        "DATABASE_URL",
        "JUDGE_ACCESS_CODE",
        "HOSTED_LIVE_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(dr, "probe", trip("Docker probe"))
    monkeypatch.setattr(dr, "_docker", trip("Docker CLI"))
    monkeypatch.setattr(worker.Registry, "start", trip("local run start"))
    provider = H.live6_provider()
    H.wire(monkeypatch, provider)
    return provider


def page(**view):
    at = AppTest.from_file(APP, default_timeout=60)
    with H.loopback_only():
        at.run()
    return at


def texts(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [e.value for e in at.info] + [e.value for e in at.warning]
    parts += [e.value for e in at.error] + [s.value for s in at.subheader]
    return "\n".join(str(p) for p in parts)


def switch_to_live(at):
    at.sidebar.radio[0].set_value("live")
    with H.loopback_only():
        at.run()
    return at


@pytest.mark.parametrize("switch", [None, "false", "TRUE", "1"])
def test_without_the_kill_switch_nothing_is_sent_and_recorded_runs_render(
    hosted, monkeypatch, switch
):
    monkeypatch.setenv("NEBIUS_API_KEY", H.KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:9/x")
    if switch is not None:
        monkeypatch.setenv("HOSTED_LIVE_ENABLED", switch)
    at = page()
    assert not at.exception
    shown = texts(at)
    assert "Replay: these are recorded runs" in shown
    assert "Live: unavailable" in shown
    assert at.get("stContainer") is not None
    # Each bundled run renders intact.
    for label in [
        "live6/agent-s01_faulty-877f8245a8a2",
        "t09/agent-har_flawed-1e2267f662c0",
        "t09/agent-har_clean-ac63eaecd7a8",
    ]:
        at.selectbox(key="hosted_recorded_run").set_value(label)
        with H.loopback_only():
            at.run()
        assert not at.exception
        shown = texts(at)
        assert re.search(
            r"\d+ of \d+ recorded items verified now \(\d+ file hashes?, "
            r"\d+ outcome comparisons?\)",
            shown,
        ), label
        assert "matches the files on disk" in shown, label
        assert "Recorded run, finished" in shown
        if "har_" in label:
            assert "CC BY 4.0" in shown and "Any commercial use is prohibited" in shown
    at = switch_to_live(at)
    shown = texts(at)
    assert "Live calls are unavailable; recorded runs remain available." in shown
    assert LABEL in shown  # the recorded original's findings are still shown
    assert not at.button  # no start button, so no live session
    assert hosted.requests == []
    assert H.KEY not in shown


def test_the_local_page_is_unchanged_without_atlas_hosted(monkeypatch):
    monkeypatch.delenv("ATLAS_HOSTED", raising=False)
    monkeypatch.setattr(
        dr, "probe", lambda: dr.Capability("isolated_unavailable", "test")
    )
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert [o for o in at.sidebar.radio[0].options] == [
        "Run a project",
        "Open a recorded run",
    ]
    assert "Replay: these are recorded runs" not in texts(at)


def run_live(at, typed=""):
    at.text_input[0].set_value(typed)
    at.button[0].click()
    with H.loopback_only() as attempts:
        at.run()
        deadline = time.time() + 120
        while time.time() < deadline:
            handle = at.session_state["hosted_live"]
            if not handle.active:
                break
            time.sleep(0.2)
        at.run()
    assert attempts == []  # nothing but loopback (the local database) was contacted
    return at


def test_a_live_session_shows_the_hosted_labels(hosted, monkeypatch, database_url):
    monkeypatch.setenv("NEBIUS_API_KEY", H.KEY)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JUDGE_ACCESS_CODE", H.JUDGE_CODE)
    monkeypatch.setenv("HOSTED_LIVE_ENABLED", "true")
    at = switch_to_live(page())
    assert "Live: available" in texts(at)
    at = run_live(at)
    assert not at.exception
    shown = texts(at)
    handle = at.session_state["hosted_live"]
    assert handle.outcome.status == "ran", handle.outcome
    assert f"Original: {LABEL}" in shown
    assert "not_executed_here" in shown
    assert "Passes ATLAS validation; **not executed here**" in shown
    assert "Route: public demo budget." in shown
    assert len(hosted.posts()) == 4
    # One live session per visitor session: no second start.
    assert not at.button or all(b.label != "Start the live session" for b in at.button)
    for marker in (H.KEY, H.JUDGE_CODE, database_url):
        assert marker not in shown


def test_the_judge_code_selects_the_judge_route(hosted, monkeypatch, database_url):
    monkeypatch.setenv("NEBIUS_API_KEY", H.KEY)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JUDGE_ACCESS_CODE", H.JUDGE_CODE)
    monkeypatch.setenv("HOSTED_LIVE_ENABLED", "true")
    at = run_live(switch_to_live(page()), typed=H.JUDGE_CODE)
    assert "Route: judge pool (access code accepted)." in texts(at)
    assert H.JUDGE_CODE not in texts(at)
