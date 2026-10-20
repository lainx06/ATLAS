"""The live mission track in a hosted live session (UI design pass phase 2, part E).

Display only. The page's existing one-second fragment (`page._follow`) reads the session's own
log; the track shows the stages recorded so far, each lighting once when it first appears,
and the gauge the requests and estimated cost so far against the session's decided limits.
When the session ends the page renders the finished session without the fragment, so the
polling stops. Offline: the session runs `run_agent` in a thread over the mocked Token
Factory, paused inside chosen provider requests; no network, no store, no spend.
"""

import threading
import time

import hosted_helpers as H
import pytest
from streamlit.testing.v1 import AppTest

from atlas.agent import controller as ctl
from atlas.agent.budget import DECIDED_SLICE4, Budget
from atlas.hosted import bundle, page
from atlas.hosted import session as hs
from atlas.ui import artifacts as A
from atlas.ui import hud as HUD

APP = str(H.ROOT / "app.py")


class Paused:
    """A mocked provider that holds chosen requests (by POST number) until released."""

    def __init__(self, hold: tuple[int, ...]):
        self.gates = {n: threading.Event() for n in hold}
        self.reached = {n: threading.Event() for n in hold}
        self.posts = 0
        self.provider = H.Provider(
            [H.completion(c) for c in [*H.LIVE6_REPLIES, H.FINISH]],
            on_post=self.on_post,
        )

    def on_post(self, request):
        self.posts += 1
        if self.posts in self.gates:
            self.reached[self.posts].set()
            assert self.gates[self.posts].wait(60)

    def wait(self, n: int) -> None:
        assert self.reached[n].wait(60), f"request {n} was not reached"
        time.sleep(0.2)  # the log line before the request is flushed

    def release(self, n: int) -> None:
        self.gates[n].set()


@pytest.fixture
def live(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_HOSTED_RUNS_DIR", str(tmp_path / "hosted-runs"))
    for name in ("NEBIUS_API_KEY", "DATABASE_URL", "JUDGE_ACCESS_CODE"):
        monkeypatch.delenv(name, raising=False)
    paused = Paused(hold=(2, 3))
    handle = page.LiveHandle(tmp_path / "session")
    result = {}

    def work():
        result["run"] = ctl.run_agent(
            H.S01, handle.runs_dir, H.client(paused.provider), H.SpyApprover(),
            budget=Budget(max_attempts=6), original=bundle.live_original(),
            live_authorized=True, spend=H.decided_limits(), hosted=True,
            reservations=H.FakeReservations(provider=paused.provider),
        )  # fmt: skip

    calls = []
    real = page._follow
    monkeypatch.setattr(page, "_follow", lambda h: (calls.append(1), real(h)))
    with H.loopback_only():
        handle.thread = threading.Thread(
            target=work, name="atlas-test-live", daemon=True
        )
        handle.thread.start()
        yield paused, handle, result, calls
        for gate in paused.gates.values():
            gate.set()
        handle.thread.join(60)


def render(at: AppTest) -> AppTest:
    at.run()
    assert not at.exception
    return at


def block(at: AppTest, cls: str) -> str:
    return next(str(m.value) for m in at.markdown if cls in str(m.value))


def logged_states(handle) -> list[str]:
    return [
        e["state"] for e in A.read_log(handle.run_dir()) if e.get("event") == "state"
    ]


def test_the_track_follows_the_session_and_stops_with_it(live):
    paused, handle, result, calls = live
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["hosted_view"] = page.LIVE_VIEW
    at.session_state["hosted_live"] = handle

    # Intermediate point 1: the session waits inside its second provider request.
    paused.wait(2)
    assert handle.active
    render(at)
    first = logged_states(handle)
    track = block(at, "hud-track")
    assert track.count('<li class="hud-stage') == len(first) >= 3
    for state in first:
        assert HUD.esc(state) in track
    assert 'aria-current="step"' in track  # the latest stage of a session still going
    assert track.count("hud-a-node") == len(first)  # first sight: each lights once
    gauge = block(at, "hud-gauge")
    attempts = [
        e for e in A.read_log(handle.run_dir()) if e["event"] == "model_attempt"
    ]
    assert f"{len(attempts)} of {DECIDED_SLICE4['max_attempts']}" in gauge
    assert f"of {DECIDED_SLICE4['estimate_cap_usd']} estimate cap" in gauge
    assert "Live session in progress" in "\n".join(str(m.value) for m in at.markdown)

    # Intermediate point 2: only the stages recorded since then light.
    paused.release(2)
    paused.wait(3)
    render(at)
    second = logged_states(handle)
    assert len(second) > len(first), (first, second)
    track = block(at, "hud-track")
    assert track.count('<li class="hud-stage') == len(second)
    assert track.count("hud-a-node") == len(second) - len(first)
    render(at)  # a rerun with nothing new: nothing lights
    assert "hud-a-node" not in block(at, "hud-track")
    assert len(calls) == 3

    # The end: the session finishes; the page shows the full recorded track, no fragment.
    paused.release(3)
    handle.thread.join(60)
    assert not handle.active
    run = result["run"]
    assert run.terminal_state == ctl.REPORT
    handle.outcome = hs.Outcome("ran", None, "public", run.run_dir, run.terminal_state)
    render(at)
    assert (
        len(calls) == 3
    )  # the follower (and its one-second fragment) is not drawn again
    shown = "\n".join(str(m.value) for m in at.markdown)
    assert "Live session in progress" not in shown
    report = A.read_json(run.run_dir / "agent_report.json")
    track = block(at, "hud-track")
    assert track.count('<li class="hud-stage') == len(report["states"])
    assert f"{len(report['states'])} recorded stages" in track
    assert "hud-a-node" not in track and 'aria-current="step"' not in track
    assert (
        f"{len(report['cost']['entries'])} of {report['spending']['max_attempts']}"
        in (block(at, "hud-gauge"))
    )
