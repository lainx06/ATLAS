"""UI design pass phase 2: the HUD on the local run view and the hosted live session.

The local page's finished run and the hosted live session are verified like a recorded run
before any HUD is drawn: intact, they lead with the ring and the reticles; changed, they
show an evidence-changed state and no HUD. The hosted live view shows the recorded original's
ring and reticle (original only), the route line, "not executed here" proposals in the
model-written frame, and its unavailable and exhausted states. Offline: the fixtures of
test_render_failure (a mocked provider and fake reservations; a copy of live run 6).
"""

import hosted_helpers as Hh
from streamlit.testing.v1 import AppTest

# The fixtures are test_render_failure's; test arguments use their names (F811 below).
from test_render_failure import (  # noqa: F401 - pytest fixtures
    APP,
    hosted_page,
    hosted_run,
    local_page,
    local_run,
    shown,
)

from atlas.hosted import page
from atlas.hosted import session as hs
from atlas.ui import artifacts as A
from atlas.ui import hud as H
from atlas.ui import recorded as RR
from atlas.ui import results as R


def hud_markup(at) -> str:
    return "\n".join(str(m.value) for m in at.markdown if 'class="hud' in str(m.value))


# -- the local page ----------------------------------------------------------------------------
def test_the_local_finished_run_leads_with_the_verified_hud(local_run):  # noqa: F811
    at = local_page()
    assert not at.exception and not at.error
    hud = hud_markup(at)
    assert hud.count('<section class="hud-ret') == 2
    report = A.read_json(local_run / "agent_report.json")
    n = len(RR.verify(local_run, report))
    assert n == 49 and f"{n}/{n}" in hud
    assert "hud-track" in hud and "hud-gauge" in hud
    assert "hud-anim" in hud  # the first load plays once
    text = shown(at)
    assert f"{H.integrity_count(RR.verify(local_run, report)).verified}: each" in text
    assert at.session_state[R.HUD_PLAYED] == {local_run.name}
    at.run()  # a rerun renders the settled state
    assert "hud-anim" not in hud_markup(at) and "hud-ret" in hud_markup(at)


def test_a_local_run_whose_files_changed_shows_no_hud(local_run):  # noqa: F811
    target = local_run / "candidates" / "c1" / "outcome.json"
    target.write_bytes(target.read_bytes().replace(b"PASS", b"PAS5", 1))
    at = local_page()
    assert not at.exception
    hud = hud_markup(at)
    assert "hud-ret" not in hud and "hud-lm" not in hud and "hud-flow" not in hud
    text = shown(at)
    assert ":red-badge[EVIDENCE CHANGED]" in text
    assert "so no outcome is shown" in text
    # Release review 1, F1: nothing is read from changed evidence, not even the cards.
    assert "2. Analysis" not in text and "3. Finding" not in text


# -- the hosted live session ---------------------------------------------------------------------
def hosted_live(monkeypatch, tmp_path) -> AppTest:
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_HOSTED_RUNS_DIR", str(tmp_path / "hosted-runs"))
    for name in ("NEBIUS_API_KEY", "DATABASE_URL", "JUDGE_ACCESS_CODE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOSTED_LIVE_ENABLED", "false")
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["hosted_view"] = page.LIVE_VIEW
    with Hh.loopback_only():
        at.run()
    return at


def test_the_live_view_shows_the_recorded_original_with_ring_and_reticle(
    monkeypatch, tmp_path
):
    at = hosted_live(monkeypatch, tmp_path)
    assert not at.exception
    hud = hud_markup(at)
    assert hud.count('<section class="hud-ret') == 1
    assert "49/49" in hud and "VIOLATION&#95;FOUND" in hud
    for absent in ("Verified revision", "hud-pane-cand", "Before"):
        assert absent not in hud, absent
    text = shown(at)
    assert ":gray-badge[LIVE UNAVAILABLE] " + hs.UNAVAILABLE_MESSAGE in text
    assert "**Next action:**" in text and not at.button
    # The ring, its caption and the page's own line carry the one integrity count.
    count = (
        "49 of 49 recorded items verified now (46 file hashes, 3 outcome comparisons)"
    )
    assert hud.count(count) == 2 and f"{count}. The original is not executed" in text


def test_the_finished_session_shows_route_hud_and_framed_proposals(hosted_run):  # noqa: F811
    at = hosted_page(hosted_run)
    assert not at.exception and not at.error
    hud = hud_markup(at)
    assert hud.count('<section class="hud-ret') == 1  # nothing executed: no after
    assert "Verified revision" not in hud
    gauge = next(m for m in at.markdown if "hud-gauge" in str(m.value)).value
    assert "of 6" in gauge and "estimate cap" in gauge
    text = shown(at)
    assert "Route: public demo budget." in text
    assert "Passes ATLAS validation; **not executed here**" in text
    assert H.MODEL_BADGE_MARKDOWN in text


def test_an_exhausted_session_is_a_state_not_an_error(tmp_path, hosted_run):  # noqa: F811
    hosted_run.outcome = hs.Outcome("exhausted", "public_daily", "public")
    at = hosted_page(hosted_run)
    text = shown(at)
    assert ":orange-badge[BUDGET_EXHAUSTED] " + hs.EXHAUSTED_MESSAGE in text
    assert not at.error and not at.success


def test_an_unavailable_session_names_its_reason(tmp_path, hosted_run):  # noqa: F811
    hosted_run.outcome = hs.Outcome("unavailable", "preflight_abort", "public")
    text = shown(hosted_page(hosted_run))
    assert hs.UNAVAILABLE_MESSAGE in text and hs.REASONS["preflight_abort"] in text
    assert ":gray-badge[LIVE UNAVAILABLE]" in text
