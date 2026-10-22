"""The final UI fix pass (2026-10-22): F1-F13 (AppTest and copy, offline).

F1: the stepper's "Show expert detail" and "Show me the evidence" buttons turn Expert view on
for the whole page (a one-shot full-app rerun request, popped by the next stepper or full run);
every widget inside the stepper is classified. F2-F5 and F8-F13: each new sentence as rendered,
and the source text it rests on. F7: the headline above the visual on every step. F10: step 5's
"all passed" headline only when every required check is PASS. F13: each proposal outcome's own
reviewed wording. The browser half (the click in a real fragment rerun, tile heights, the order
on screen) is tests/acceptance/test_scenario18_final_fix.py. The bundled runs are only read.
"""

import dataclasses
import inspect
import itertools
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_capture import find, items

from atlas.runner import docker as dr
from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import recorded as R
from atlas.ui import story
from atlas.ui import versus as VS

ROOT = Path(__file__).resolve().parents[2]
APP = str(ROOT / "app.py")
VS_PAGE = "app_pages/agent_vs_model.py"
LIM_PAGE = "app_pages/how_it_works.py"
BUNDLE = ROOT / "demo" / "recorded"
CASES = {c.key: c.run for c in C.CASES}
RESULTS = ROOT / "evaluation" / "results" / "t11-live-20261019"
README = (ROOT / "README.md").read_text(encoding="utf-8")
HOSTED_OPS = (ROOT / "docs" / "HOSTED_OPERATIONS.md").read_text(encoding="utf-8")
EVALUATION = (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


@pytest.fixture(params=["local", "hosted"])
def mode(request, monkeypatch, tmp_path):
    if request.param == "hosted":
        monkeypatch.setenv("ATLAS_HOSTED", "1")
        monkeypatch.setenv("ATLAS_HOSTED_RUNS_DIR", str(tmp_path / "hosted-runs"))
        monkeypatch.setenv("HOSTED_LIVE_ENABLED", "false")
        for name in ("NEBIUS_API_KEY", "DATABASE_URL", "JUDGE_ACCESS_CODE"):
            monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.delenv("ATLAS_HOSTED", raising=False)
        monkeypatch.setenv("ATLAS_UI_RUNS_DIR", str(tmp_path / "ui-runs"))
    return request.param


def overview(case: str | None = None, *, expert: bool = False) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    if case is not None:
        at.session_state[story.CASE] = case
    at.session_state[story.EXPERT] = expert
    at.run()
    assert not at.exception, at.exception
    return at


def page(path: str, *, expert: bool = False) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state[story.EXPERT] = expert
    at.switch_page(path)
    at.run()
    assert not at.exception, at.exception
    return at


def at_step(at: AppTest, key: str, n: int) -> AppTest:
    at.session_state[story.step_key(key)] = n
    at.run()
    assert not at.exception, at.exception
    return at


def keyed(node) -> list[str]:
    """Every user key under `node`, in document order."""
    out = []
    for child in getattr(node, "children", {}).values():
        if getattr(child, "key", None):
            out.append(child.key)
        out += keyed(child)
    return out


def widgets(node) -> list[tuple[str, str]]:
    """(type, key) of every widget and expander under `node`, in document order."""
    out = []
    for child in getattr(node, "children", {}).values():
        kind = type(child).__name__
        if kind in ("Button", "ButtonGroup", "Expander", "Toggle", "Selectbox"):
            out.append((kind, getattr(child, "key", None) or ""))
        out += widgets(child)
    return out


def _hud(key: str) -> H.Hud:
    rr = R.RecordedRun(BUNDLE / CASES[key], CASES[key], R.AGENT)
    report = A.read_json(rr.path / "agent_report.json")
    checks = R.verify(rr.path, report)
    return H.build(rr.path, report, checks, rr.label, bundled=True)


# == F1: the stepper's Expert view buttons ==========================================================
@pytest.mark.parametrize("label", [C.SHOW_EXPERT, C.SHOW_EVIDENCE])
@pytest.mark.parametrize("key", list(CASES))
def test_a_stepper_expert_button_turns_expert_view_on_for_the_page(mode, key, label):
    for n in range(1, 6):
        at = at_step(overview(key), key, n)
        button = next((b for b in at.button if b.label == label), None)
        # "Show me the evidence" is step 2's; "Show expert detail" is every other step's.
        if label != (C.SHOW_EVIDENCE if n == 2 else C.SHOW_EXPERT):
            assert button is None, n
            continue
        assert button.key == f"expert-on-{n}"
        button.click().run()
        assert not at.exception, at.exception
        assert at.session_state[story.EXPERT] is True
        assert at.toggle(key=story.EXPERT_WIDGET).value is True
        assert story.APP_RERUN not in at.session_state  # consumed by the full run
        assert find(at.main, "stepper") is None  # Expert view: the five expanders
        assert find(at.main, "step-5") is not None
        assert "Recorded run" in "\n".join(items(find(at.main, "banner")))


def test_the_callback_requests_a_full_app_rerun_and_the_stepper_honours_it_first():
    assert "st.session_state[APP_RERUN] = True" in inspect.getsource(story._set_expert)
    body = inspect.getsource(story.stepper).split('"""')[2]  # after the docstring
    lines = [x.strip() for x in body.strip().splitlines()]
    # The request is the stepper's first act, before the verification and any drawing.
    assert lines[:2] == [
        "if st.session_state.pop(APP_RERUN, False):",
        'st.rerun(scope="app")',
    ]
    # A full run consumes it before drawing (so a later stepper run never reruns needlessly).
    case = inspect.getsource(story.case)
    assert case.index("st.session_state.pop(APP_RERUN, None)") < case.index("stepper(")
    # The buttons keep their callback (state set before the rerun; st.rerun there is a no-op).
    assert "on_click=_set_expert" in inspect.getsource(story.expert_line)


# Every widget the stepper draws, with its disposition (F1 audit). A new widget fails here
# until it is classified.
STEPPER_WIDGETS = {
    # The step row, Back and Next: they set only the stepper's own step (story.step_key),
    # read nowhere outside the fragment, so a fragment rerun is complete.
    "ButtonGroup:stepper-row-": "fragment",
    "Button:stepper-back-": "fragment",
    "Button:stepper-next-": "fragment",
    # Show more: a native expander (on_change="ignore"): opens in the browser, no rerun.
    "Expander:stepper-more-": "browser",
    # Show expert detail / Show me the evidence: Expert view, outside the fragment: full rerun.
    "Button:expert-on-": "app",
}


@pytest.mark.parametrize("key", list(CASES))
def test_every_widget_in_the_stepper_is_classified(key):
    seen = set()
    for n in range(1, 6):
        at = at_step(overview(key), key, n)
        for kind, wkey in widgets(find(at.main, "stepper")):
            prefix = next(
                (p for p in STEPPER_WIDGETS if f"{kind}:{wkey}".startswith(p)), None
            )
            assert prefix is not None, (n, kind, wkey)
            seen.add(prefix)
    assert seen == set(STEPPER_WIDGETS)
    # "Show all steps" and the tamper demo are drawn by the page, outside the fragment.
    at = overview(key)
    stepper = keyed(find(at.main, "stepper"))
    assert story.SHOW_ALL_WIDGET not in stepper and "tamper" not in stepper
    assert all(not k.startswith("tamper") for k in stepper)


# == F2: the recorded-run line ======================================================================
def test_the_recorded_run_line_and_the_replay_disclosure_in_expert_view(mode):
    assert "Every recorded hash is recomputed before anything is shown" in flat(
        HOSTED_OPS
    )
    live = A.read_json(BUNDLE / CASES["live6"] / "agent_report.json")
    assert story.banner_text(live, "2026-10-18T01:02:03Z") == (
        "Recorded run · Nemotron · finished 2026-10-18 · replayed here, not re-run. "
        "Every recorded hash is recomputed before display."
    )
    har = A.read_json(BUNDLE / CASES["harflawed"] / "agent_report.json")
    assert story.banner_text(har, "2026-10-19T00:00:00Z") == (
        "Recorded run · scripted replies, no model called · finished 2026-10-19 · "
        "replayed here, not re-run. Every recorded hash is recomputed before display."
    )
    for key in CASES:
        plain = "\n".join(items(find(overview(key).main, "banner")))
        assert C.REPLAY_DISCLOSURE not in plain
        assert "Every recorded hash is recomputed before display." in plain
        expert = "\n".join(items(find(overview(key, expert=True).main, "banner")))
        assert C.REPLAY_DISCLOSURE in expert


# == F3, F5, F8, F4, F9: How It Works & Limits =========================================================
def test_the_sealed_runner_tile_names_exactly_the_runners_writable_folders(tmp_path):
    args = dr.docker_run_args(
        "atlas-x", "run1", tmp_path / "p", tmp_path / "c", "sha256:abc", dr.Limits()
    )
    assert "--read-only" in args and ("--network", "none") in itertools.pairwise(args)
    tmpfs = [args[i + 1].split(":")[0] for i, a in enumerate(args) if a == "--tmpfs"]
    assert sorted(tmpfs) == ["/tmp", "/work/out"]  # output and temporary folders
    mounts = [args[i + 1] for i, a in enumerate(args) if a == "--mount"]
    assert len(mounts) == 2 and all(m.endswith(",readonly") for m in mounts)
    assert not any(a in ("-v", "--volume") for a in args)
    assert dict(C.SAFETY_TILES)["Sealed runner"] == (
        "No network, no admin rights, and a read-only filesystem except its output and "
        "temporary folders. If it is unavailable, ATLAS stops; it never runs code on the host."
    )
    assert "(no network, non-root, read-only root" in README
    assert "never falls back to the host" in README
    assert "--network none`, non-root, read-only rootfs, no host fallback" in EVALUATION


def test_the_tamper_tile_names_only_hashed_files_and_expert_view_keeps_the_full_sentence():
    assert dict(C.SAFETY_TILES)["Tamper check"] == (
        "Every recorded hash is recomputed before display; a change to a hashed file shows "
        "'evidence changed'. It does not catch a run whose files and hashes were both "
        "rewritten."
    )
    assert (
        "it does not authenticate a run whose files and recorded hashes were both"
        in flat(C.SAFETY[5][0])
    )
    expert = "\n".join(items(page(LIM_PAGE, expert=True).main))
    assert H.esc(C.SAFETY[5][0]) in expert


def test_how_it_works_step_1_and_the_key_limits_and_their_sources(mode):
    assert C.HOW_LINES[0] == (
        "The evaluation runs in a sealed container, and ATLAS records what each supported "
        "step learned from."
    )
    assert "Fit provenance covers only the bounded supported path." in README
    assert list(C.KEY_LIMITS) == [
        (
            "A clean result means only that the listed checks passed within the coverage "
            "shown. It does not prove the claim true."
        ),
        "Only small tabular scikit-learn classification, with three kinds of claim.",
        "No held-out test projects: every result here is on projects ATLAS was built on.",
        (
            "Tracing starts at the feature table the project supplies; how data was "
            "collected, labelled or turned into features is not checked."
        ),
        (
            "Container isolation reduces risk; it does not prove the code safe, the traces "
            "intact, or the science correct."
        ),
        (
            "The live AI's replies often broke the required format: schema failures in 5 of "
            "the 8 live runs."
        ),
    ]
    assert "passed within the stated coverage." in README
    assert (
        "Container isolation reduces risk; it is not proof of safety, provenance integrity "
        "or scientific correctness." in README
    )
    assert "schema failures in 5 of the 8 live runs" in README
    at = page(LIM_PAGE)
    shown = str(find(at.main, "lim-key-limits").children[0].value)
    assert len(C.KEY_LIMITS) == 6
    for line in C.KEY_LIMITS:
        assert f"<li>{story.code_html(line)}</li>" in shown, line
    tiles = [str(m.value) for m in find(at.main, "lim-safety-tiles").markdown]
    for title, line in C.SAFETY_TILES:
        assert story.md(line) in tiles, title
    steps = str(find(at.main, "lim-steps").children[0].value)
    assert H.esc(C.HOW_LINES[0]) in steps


# == F7: the headline above the visual =================================================================
VISUALS = {
    "concept-groups",
    "hud-evidence",
    "analogies",
    "stepper-chips",
    "concept-sealed",
    "stepper-outcomes",
}


@pytest.mark.parametrize("key", list(CASES))
def test_on_every_step_the_headline_sits_above_the_visual(mode, key):
    for n in range(1, 6):
        at = at_step(overview(key), key, n)
        order = keyed(find(at.main, f"stepper-body-{n}"))
        head = next(
            i for i, k in enumerate(order) if k in ("stepper-headline", "no-proposal")
        )
        shown = [i for i, k in enumerate(order) if k in VISUALS]
        assert all(i > head for i in shown), (key, n, order)
        if n == 4:
            assert order.index("concept-sealed") > head


# == F10: step 5's headline when nothing fails ===========================================================
def _with(hud: H.Hud, statuses: list[str | None], *, candidate: bool) -> H.Hud:
    rows = tuple(
        H.MatrixRow(f"a.{i}", s if not candidate else "PASS", s if candidate else None)
        if candidate
        else H.MatrixRow(f"a.{i}", s, None)
        for i, s in enumerate(statuses)
    )
    return dataclasses.replace(hud, matrix=rows)


def test_the_all_passed_headline_needs_every_required_check_to_pass():
    hud = _hud("harclean")
    assert hud.candidate is None
    assert story.outcome_chips(_with(hud, ["PASS"] * 4, candidate=False)) == (
        C.ALL_PASSED,
        [],
    )
    assert C.ALL_PASSED == "All required checks passed within the coverage shown"
    for bad in ("FAIL", "ERROR", "NOT_ASSESSED"):
        head, chips = story.outcome_chips(
            _with(hud, ["PASS", bad, "PASS"], candidate=False)
        )
        assert head == C.WHAT_FAILED and len(chips) == 1, bad
    # A required check with no recorded status: not "all passed".
    assert story.outcome_chips(_with(hud, ["PASS", None], candidate=False)) == ("", [])
    assert story.outcome_chips(_with(hud, [], candidate=False)) == ("", [])
    # With an executed revision, its statuses decide.
    live = _hud("live6")
    assert live.candidate is not None
    for bad in ("FAIL", "ERROR", "NOT_ASSESSED"):
        head, _chips = story.outcome_chips(_with(live, ["PASS", bad], candidate=True))
        assert head != C.ALL_PASSED, bad


@pytest.mark.parametrize("key", list(CASES))
def test_step_5_shows_the_all_passed_headline_only_for_the_all_pass_case(mode, key):
    at = at_step(overview(key), key, 5)
    body = find(at.main, "stepper-body-5")
    headline = str(find(body, "stepper-headline").children[0].value)
    statuses = {
        r.candidate if r.candidate is not None else r.original for r in _hud(key).matrix
    }
    if key == "harclean":
        assert statuses == {"PASS"}
        assert headline == f"### {story.md(C.ALL_PASSED)}"
        integrity = str(find(body, "stepper-integrity").children[0].value)
        assert integrity.startswith(story.md("Evidence intact: "))
        assert find(body, "stepper-outcomes") is None  # the headline says it once
    else:
        assert statuses != {"PASS"} or key == "live6"
        assert story.md(C.ALL_PASSED) not in "\n".join(items(body))


# == F11: the comparison page ===========================================================================
def _figures() -> VS.Figures:
    return VS.figures(
        json.loads((RESULTS / "scores.json").read_text(encoding="utf-8")),
        json.loads((RESULTS / "suite.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "evaluation/expected.json").read_text(encoding="utf-8")),
    )


def test_the_comparison_answer_caveat_and_tile_labels(mode):
    f = _figures()
    assert (f.cases, f.repetitions) == (4, 3)
    assert VS.answer(f) == (
        "On these 4 projects, ATLAS's checks found all 8 problems they can assess, with no "
        "false alarms. The AI model on its own, asked 3 times per project, made 19 of 20 "
        "detections on those same 8 problems (19 of 23 overall), raised 2 false alarms, and "
        "gave 3 unusable answers out of 12."
    )
    assert VS.caveat_line(f) == (
        "Read with care: a small test of finding problems, not fixing them, on the 4 "
        "projects ATLAS was built on. The flawed projects' files describe their flaws in "
        "text the model could read, and only ATLAS ran the code on the data."
    )
    findings = flat(EVALUATION)
    for source in (
        "evaluates violation detection only and does not test repair",
        "describe the project's deliberate flaws in plain text",
        "leg (b) reads only the manifest and source, without the data table",
        "Three repetitions per case",
    ):
        assert source in findings, source
    at = page(VS_PAGE)
    assert str(find(at.main, "vs-caveat-line").children[0].value) == story.md(
        VS.caveat_line(f)
    )
    assert [(m.label, m.value) for m in at.metric] == [
        ("ATLAS (problems)", "8 of 8"),
        ("Model alone (detections)", "19 of 20"),
        ("ATLAS", "0"),
        ("Model alone", "2"),
        ("ATLAS", "none"),
        ("Model alone", "3 of 12"),
    ]
    assert f"**{story.md('Planted problems found')}**" in [
        str(m.value) for m in find(at.main, "vs-tile-0").markdown
    ]
    captions = [str(c.value) for c in find(at.main, "vs-tile-0").caption]
    assert captions == [
        story.md("assessable; 1 of 9 not assessed"),
        story.md("detections on the same 8; 19 of 23 overall"),
    ]


# == F12: the HAR data line ===============================================================================
@pytest.mark.parametrize("key", ["harflawed", "harclean"])
def test_the_har_data_line(mode, key):
    at = overview(key)
    line = str(find(at.main, "har-data").children[0].value)
    assert (
        line
        == story.md(
            "Data: UCI HAR (Reyes-Ortiz et al., 2013), CC BY 4.0 on the dataset page; the "
            "archive's README says no commercial use. No data is redistributed here."
        )
        + f" [{C.HAR_DOI}]({C.HAR_DOI})"
    )
    assert [str(c.value) for c in at.expander(key="har-details").caption] == [
        C.HAR_CITATION_PLAIN
    ]
    assert "The dataset page grants **CC BY 4.0**" in README
    assert '"Any commercial use is prohibited."' in README
    assert "No data is redistributed here" in README
    assert (
        "Reyes-Ortiz, J., Anguita, D., Ghio, A., Oneto, L., & Parra, X. (2013)"
        in README
    )
    assert find(overview("live6").main, "har-data") is None


# == F13: step 3's chips ==================================================================================
def test_each_proposal_outcome_has_its_own_reviewed_wording():
    rr = R.RecordedRun(BUNDLE / CASES["live6"], CASES["live6"], R.AGENT)
    report = A.read_json(rr.path / "agent_report.json")
    checks = R.verify(rr.path, report)
    f = story.facts(rr, report, checks, _hud("live6"))
    f.report = {
        "proposals": [
            {"revision": 1, "outcome": "not_executed_here"},
            {"revision": 2, "outcome": "declined"},
            {"revision": 3, "outcome": "unavailable"},
            {"revision": 4, "outcome": "rejected"},
        ]
    }
    f.isolated_revisions = set()
    assert story.proposal_chips(f) == [
        ("Revision 1: not executed here", "gray"),
        ("Revision 2: declined at approval", "gray"),
        ("Revision 3: not run (runner unavailable)", "gray"),
        ("Revision 4: rejected by ATLAS validation", "red"),
    ]
    # The reviewed wording each rests on (step 3's summary parts), without the count.
    for code, chip in (
        ("not_executed_here", "not executed here"),
        ("declined", "declined at approval"),
        ("unavailable", "not run (runner unavailable)"),
    ):
        assert C.PROPOSAL_PARTS[code] == "{k} " + chip
        assert C.CHIP_OUTCOME[code] == chip
    assert len({C.CHIP_OUTCOME[c] for c in ("declined", "unavailable")}) == 2
