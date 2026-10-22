"""The readability pass (2026-10-21): headline first, one idea per screen (AppTest, offline).

Plain view: the Overview's story is a five-step stepper that opens on step 2, with one visual
per step and the rest behind "Show more"; "Show all steps" shows the five expanders exactly as
before. The comparison page leads with one answer sentence, the caveat line and three stat
tiles; How It Works & Limits shows one line per step, six safety tiles and four key limits.
Nothing is removed: every moved item is one click away, unchanged, and Expert view renders
exactly what it rendered before the pass (`tests/fixtures/ui_readability/before.json`,
recorded from commit b690af2 by the capture script beside it). Verification is re-run on every
render, including the stepper's own runs, and is never cached. The bundled runs are only read.
"""

import html
import inspect
import json
import re
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_capture import find, items, segments

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import limits as L
from atlas.ui import recorded as R
from atlas.ui import results as RS
from atlas.ui import story
from atlas.ui import versus as VS

ROOT = Path(__file__).resolve().parents[2]
APP = str(ROOT / "app.py")
VS_PAGE = "app_pages/agent_vs_model.py"
LIM_PAGE = "app_pages/how_it_works.py"
BUNDLE = ROOT / "demo" / "recorded"
CASES = {c.key: c.run for c in C.CASES}
BEFORE = json.loads(
    (ROOT / "tests/fixtures/ui_readability/before.json").read_text(encoding="utf-8")
)
RESULTS = ROOT / "evaluation" / "results" / "t11-live-20261019"


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


def overview(
    case: str | None = None, *, expert: bool = False, show_all: bool = False
) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    if case is not None:
        at.session_state[story.CASE] = case
    at.session_state[story.EXPERT] = expert
    at.session_state[story.SHOW_ALL] = show_all
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


def visible(node) -> list[str]:
    """What shows without a click: everything except closed expanders' and popovers'
    content (AppTest has no open state, so every expander counts as closed)."""
    out = []
    for child in getattr(node, "children", {}).values():
        kind = getattr(child, "type", None)
        if kind == "expander":
            out.append(f"Expander:{child.label}")
            continue
        if kind == "popover":
            out.append(f"Popover:{child.proto.popover.label}")
            continue
        sub = items(_Wrap(child)) if not getattr(child, "children", None) else []
        out += sub
        if getattr(child, "children", None):
            out += visible(child)
    return out


class _Wrap:
    """One leaf element as a node with a single child (for `items`)."""

    def __init__(self, element):
        self.children = {0: element}


def text_of(lines: list[str]) -> str:
    return "\n".join(s for line in lines for s in segments(line))


def at_step(at: AppTest, key: str, n: int) -> AppTest:
    at.session_state[story.step_key(key)] = n
    at.run()
    assert not at.exception, at.exception
    return at


# == the stepper ==================================================================================
@pytest.mark.parametrize("key", list(CASES))
def test_each_case_opens_on_step_2_and_moves_by_next_back_and_the_row(mode, key):
    at = overview(key)
    row = at.button_group(key=story.STEP_WIDGET + key)
    assert row.value == 2
    assert list(row.options) == [
        "1 Claim",
        "2 What the checks found",
        "3 The AI's fix",
        "4 Approval & sealed run",
        "5 Verified evidence",
    ]

    def position() -> str:
        return next(str(m.value) for m in at.markdown if "hud-step-pos" in str(m.value))

    # Shown and announced: a polite live region.
    assert 'role="status"' in position() and 'aria-live="polite"' in position()
    assert ">Step 2 of 5<" in position()
    assert find(at.main, "stepper-body-2") is not None
    at.button(key=f"stepper-next-{key}").click().run()
    assert at.session_state[story.step_key(key)] == 3 and ">Step 3 of 5<" in position()
    assert find(at.main, "stepper-body-3") is not None
    assert find(at.main, "stepper-body-2") is None  # one step at a time
    at.button(key=f"stepper-back-{key}").click().run()
    at.button(key=f"stepper-back-{key}").click().run()
    assert at.session_state[story.step_key(key)] == 1
    assert at.button(key=f"stepper-back-{key}").disabled
    assert not at.button(key=f"stepper-next-{key}").disabled
    at.button_group(key=story.STEP_WIDGET + key).set_value(5).run()
    assert at.session_state[story.step_key(key)] == 5 and ">Step 5 of 5<" in position()
    assert at.button(key=f"stepper-next-{key}").disabled
    assert not at.exception


def test_the_step_is_kept_per_case_and_a_newly_selected_case_starts_on_step_2(mode):
    at = overview()
    at.button(key="stepper-next-live6").click().run()
    at.button(key="stepper-next-live6").click().run()
    assert at.session_state[story.step_key("live6")] == 4
    at.run()  # an unrelated rerun keeps it
    assert at.button_group(key=story.STEP_WIDGET + "live6").value == 4
    at.button(key="case-btn-harflawed").click().run()
    assert at.button_group(key=story.STEP_WIDGET + "harflawed").value == 2
    at.button_group(key=story.STEP_WIDGET + "harflawed").set_value(5).run()
    at.button(key="case-btn-harflawed").click().run()  # the same case again: kept
    assert at.session_state[story.step_key("harflawed")] == 5
    at.button(key="case-btn-live6").click().run()  # switching case: its default step
    assert at.button_group(key=story.STEP_WIDGET + "live6").value == 2
    assert story.step_key("live6") != story.step_key("harflawed")


@pytest.mark.parametrize("key", list(CASES))
def test_show_all_steps_shows_todays_five_expanders_unchanged(mode, key):
    at = overview(key, show_all=True)  # the first render, as the baseline was recorded
    assert find(at.main, "stepper") is None
    for n in range(1, 6):
        assert (
            items(find(at.main, f"step-{n}")) == BEFORE["plain_steps"][key][str(n)]
        ), n
    at.toggle(key=story.SHOW_ALL_WIDGET).set_value(False).run()
    assert at.session_state[story.SHOW_ALL] is False
    assert find(at.main, "stepper") is not None and find(at.main, "step-1") is None
    at.toggle(key=story.SHOW_ALL_WIDGET).set_value(True).run()
    assert find(at.main, "stepper") is None and find(at.main, "step-5") is not None


ANALOGY_TEXTS = [text for _aids, text in C.ANALOGIES]


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("key", list(CASES))
def test_each_step_screen_holds_all_of_todays_step_text_once(mode, key, n):
    at = at_step(overview(key), key, n)
    body = find(at.main, f"stepper-body-{n}")
    shown = text_of(items(body))
    for line in BEFORE["plain_steps"][key][str(n)]:
        for piece in segments(line):
            assert piece in shown, (key, n, piece[:80])
    # Show more holds only the rest: never the headline, a visual or an analogy.
    more = find(body, f"stepper-more-{n}")
    assert more is not None and more.label == C.SHOW_MORE
    # (The briefing, unchanged inside Show more, opens with the integrity sentence, which is
    # step 5's headline when no revision ran; it is left out of this check.)
    inside = [x for x in items(more) if "hud-brief" not in x]
    markup = "\n".join(inside)
    headline = story.summaries(*_hud_facts(key)[::-1], _checks(key))[n]
    assert story.md(headline) not in markup and H.esc(headline) not in markup
    for visual in ("hud-concept", "hud-leak", "hud-flow", "hud-analogy"):
        assert visual not in markup, visual
    assert (
        find(more, "stepper-chips") is None and find(more, "stepper-outcomes") is None
    )
    # Each visual and analogy appears once in the step.
    everything = "\n".join(items(body))
    for text in ANALOGY_TEXTS:
        assert everything.count(H.esc(text)) <= 1
    assert everything.count("hud-concept") <= 1
    assert everything.count('class="hud hud-evidence') <= 1


def _checks(key: str) -> list:
    run = BUNDLE / CASES[key]
    return R.verify(run, A.read_json(run / "agent_report.json"))


def _rr(key: str) -> R.RecordedRun:
    return R.RecordedRun(BUNDLE / CASES[key], CASES[key], R.AGENT)


def _hud_facts(key: str):
    rr = R.RecordedRun(BUNDLE / CASES[key], CASES[key], R.AGENT)
    report = A.read_json(rr.path / "agent_report.json")
    checks = R.verify(rr.path, report)
    hud = H.build(rr.path, report, checks, rr.label, bundled=True)
    return story.facts(rr, report, checks, hud), hud


# == the visuals ==================================================================================
def test_step_3_chips_equal_the_verified_proposals(mode):
    at = at_step(overview("live6"), "live6", 3)
    chips = str(find(at.main, "stepper-chips").children[0].value)
    report = A.read_json(BUNDLE / CASES["live6"] / "agent_report.json")
    assert [(p["revision"], p["outcome"]) for p in report["proposals"]] == [
        (1, "executed"),
        (2, "rejected"),
    ]
    assert chips.splitlines() == [
        f":green-badge[{story.md('Revision 1: approved and executed in the sealed runner')}]".join(
            ["- ", ""]
        ),
        f":red-badge[{story.md('Revision 2: rejected by ATLAS validation')}]".join(
            ["- ", ""]
        ),
    ]
    for key in ("harflawed", "harclean"):
        at = at_step(overview(key), key, 3)
        assert find(at.main, "stepper-chips") is None
        assert story.md(C.NO_PROPOSAL) in str(
            find(at.main, "no-proposal").children[0].value
        )


def test_proposal_chips_follow_each_recorded_outcome():
    f, _hud = _hud_facts("live6")
    f.report = {
        "proposals": [
            {"revision": 1, "outcome": "executed"},
            {"revision": 2, "outcome": "executed"},
            {"revision": 3, "outcome": "rejected"},
            {"revision": 4, "outcome": "declined"},
            {"revision": 5, "outcome": "not_executed_here"},
            {"revision": 6, "outcome": "unavailable"},
            {"revision": 7, "outcome": "odd"},
        ]
    }
    f.isolated_revisions = {1}
    f.exec_runners = {1: "docker_isolated", 2: "local"}
    assert story.proposal_chips(f) == [
        ("Revision 1: approved and executed in the sealed runner", "green"),
        ("Revision 2: executed (runner local)", "gray"),
        ("Revision 3: rejected by ATLAS validation", "red"),
        ("Revision 4: declined at approval", "gray"),
        ("Revision 5: not executed here", "gray"),
        ("Revision 6: not run (runner unavailable)", "gray"),
        ("Revision 7: recorded outcome odd", "gray"),
    ]


def _statuses(path: Path) -> dict[str, str]:
    return {a["assertion_id"]: a["status"] for a in A.read_json(path)["assertions"]}


@pytest.mark.parametrize("key", list(CASES))
def test_step_5_what_changed_equals_the_recorded_statuses(key):
    _f, hud = _hud_facts(key)
    labels = H.load_descriptions()
    run = BUNDLE / CASES[key]
    before = _statuses(run / "original/outcome.json")
    head, chips = story.outcome_chips(hud)
    if key == "live6":
        after = _statuses(run / "candidates/c1/outcome.json")
        changed = [a for a in before if a in after and before[a] != after[a]]
        assert head == C.WHAT_CHANGED and len(changed) == 4
        assert [t for t, _c in chips] == [
            f"{labels[a]}: {before[a]} → {after[a]}" for a in changed
        ]
        assert all(after[a] == "PASS" and before[a] == "FAIL" for a in changed)
    elif key == "harflawed":
        bad = [a for a, s in before.items() if s in ("FAIL", "NOT_ASSESSED", "ERROR")]
        assert head == C.WHAT_FAILED and len(bad) == 5
        assert [t for t, _c in chips] == [f"{labels[a]}: {before[a]}" for a in bad]
    else:
        assert set(before.values()) == {"PASS"}
        assert (head, chips) == (C.ALL_PASSED, [])


def test_the_concept_diagrams_carry_no_number_and_the_groups_one_only_for_unseen_group():
    for markup in (story.group_diagram(), story.sealed_diagram()):
        text = html.unescape(re.sub(r"<[^>]+>", " ", markup))  # the rendered text
        assert re.search(r"\d", text) is None, text
        label = html.unescape(re.search(r'aria-label="([^"]+)"', markup).group(1))
        assert re.search(r"\d", label) is None and 'role="img"' in markup
        assert H.esc(C.DIAGRAM_LABEL) in markup
    assert H.esc(C.DIAGRAM_GROUP_CAPTION) in story.group_diagram()
    for name in (C.DIAGRAM_TRAIN_PEOPLE, C.DIAGRAM_TEST_PEOPLE):
        assert H.esc(name) in story.group_diagram()
    for name in (C.DIAGRAM_CODE, C.DIAGRAM_TYPED_HASH, C.DIAGRAM_SEALED):
        assert H.esc(name) in story.sealed_diagram()

    class Claim:
        def __init__(self, kind):
            self.type = kind

    assert story.claim_diagram(Claim("unseen_group")) == story.group_diagram()
    for kind in ("same_population", "future_time", None):
        assert story.claim_diagram(Claim(kind)) is None
    assert story.claim_diagram(None) is None


@pytest.mark.parametrize("key", list(CASES))
def test_steps_1_and_4_show_their_diagrams(mode, key):
    at = at_step(overview(key), key, 1)
    f, _hud = _hud_facts(key)
    assert f.claim.type == "unseen_group"  # every bundled case
    assert "hud-concept" in str(find(at.main, "concept-groups").children[0].value)
    at = at_step(at, key, 4)
    body = items(find(at.main, "stepper-body-4"))
    assert any("concept-locked" in x for x in body)
    told = story.summaries(_hud_facts(key)[1], f, _checks(key))[4]
    assert (
        f"Markdown:### {story.md(told)}" in body
    )  # the summary line under the diagram
    if key != "live6":
        assert told == C.SCRIPT_ONLY


# == verification: never cached, re-run in the stepper ==========================================
def test_nothing_in_the_ui_is_cached():
    """No st.cache_data / st.cache_resource on the recorded-run gate, the T-11 hash gate or
    anything they read: they run on every render. The UI's one cache is the local page's
    Docker probe (30 s), which no verification reads."""
    for path in [
        ROOT / "app.py",
        *sorted((ROOT / "app_pages").glob("*.py")),
        *sorted((ROOT / "src/atlas/ui").glob("*.py")),
        *sorted((ROOT / "src/atlas/hosted").glob("*.py")),
    ]:
        text = path.read_text(encoding="utf-8")
        found = re.findall(r"@st\.cache_\w+[^\n]*\ndef (\w+)", text)
        assert text.count("cache_data") + text.count("cache_resource") == len(found)
        expected = ["docker_capability"] if path.name == "local_page.py" else []
        assert found == expected, (path.name, found)
    assert 'st.rerun(scope="app")' in inspect.getsource(story.stepper)


def test_a_byte_changed_between_two_renders_shows_only_the_evidence_changed_panel(
    mode, tmp_path, monkeypatch
):
    root = tmp_path / "bundle"
    shutil.copytree(BUNDLE, root)
    monkeypatch.setattr(story, "BUNDLE_ROOT", root)
    at = overview()
    assert find(at.main, "stepper") is not None
    target = root / CASES["live6"] / "candidates" / "c1" / "outcome.json"
    raw = target.read_bytes()
    target.write_bytes(raw[:-1] + (b" " if raw[-1:] != b" " else b"\n"))
    at.button(key="stepper-next-live6").click().run()  # the same session
    assert not at.exception
    assert find(at.main, "stepper") is None and find(at.main, "verdict-bar") is None
    assert find(at.main, "integrity-failed") is not None
    assert A.CAVEAT not in "\n".join(str(m.value) for m in at.markdown)


def test_the_stepper_verifies_again_itself_and_reruns_the_page_on_a_failure(
    mode, monkeypatch
):
    """The stepper's own verification fails (as if a byte changed after the page's gate):
    it draws nothing and reruns the whole page, whose gate then shows only the panel."""
    real = RS.verification
    state = {"stepper": 0, "failed": False}

    def verification(run_dir, report, mode_):
        caller = inspect.stack()[1].function
        if caller == "stepper":
            state["stepper"] += 1
            state["failed"] = True
        checks = real(run_dir, report, mode_)
        if state["failed"] and run_dir is not None and "live6" in str(run_dir):
            return [R.Check("original/outcome.json", "a" * 64, "b" * 64, "changed")]
        return checks

    monkeypatch.setattr(RS, "verification", verification)
    at = overview()
    assert state["stepper"] == 1
    assert find(at.main, "stepper") is None and find(at.main, "verdict-bar") is None
    assert find(at.main, "integrity-failed") is not None


# == the comparison page ==========================================================================
ANSWER = (
    "On these 4 projects, ATLAS's checks found all 8 problems they can assess, with no false "
    "alarms. The AI model on its own, asked 3 times per project, made 19 of 20 detections on "
    "those same 8 problems (19 of 23 overall), raised 2 false alarms, and gave 3 unusable "
    "answers out of 12."
)


def _from_scores() -> dict:
    """The figures, computed here from scores.json and expected.json directly."""
    scores = json.loads((RESULTS / "scores.json").read_text(encoding="utf-8"))
    expected = json.loads(
        (ROOT / "evaluation/expected.json").read_text(encoding="utf-8")
    )
    want = {
        cid: {e["assertion_id"] for e in c.get("expected_violated") or []}
        for cid, c in expected["cases"].items()
    }
    gaps = {
        c["case_id"]: set(c.get("coverage_gaps") or [])
        for c in scores["atlas"]["cases"]
    }
    same_k = same_n = 0
    for case in scores["baseline"]["cases"]:
        ok = want[case["case_id"]] - gaps.get(case["case_id"], set())
        for t in case["trials"]:
            if t.get("status") == "VALID":
                same_n += len(ok)
                same_k += len(set(t.get("tp") or []) & ok)
    a, b = scores["atlas"]["totals"], scores["baseline"]["totals"]
    tries = {len(case["trials"]) for case in scores["baseline"]["cases"]}
    return {
        "projects": len(expected["cases"]),
        "tries": tries,
        "atlas_found": a["tp"],
        "atlas_assessable": a["tp"] + a["fn"],
        "atlas_false": a["fp"],
        "same": (same_k, same_n),
        "all": (b["tp"], b["tp"] + b["fn"]),
        "model_false": b["fp"],
        "invalid": (b["invalid_reply"], b["trials_scheduled"]),
        "not_assessed": sum(len(want[c] & gaps.get(c, set())) for c in want),
        "expected": sum(len(v) for v in want.values()),
    }


def test_the_answer_sentence_and_the_tiles_equal_scores_json(mode):
    s = _from_scores()
    assert s == {
        "projects": 4,
        "tries": {3},
        "atlas_found": 8,
        "atlas_assessable": 8,
        "atlas_false": 0,
        "same": (19, 20),
        "all": (19, 23),
        "model_false": 2,
        "invalid": (3, 12),
        "not_assessed": 1,
        "expected": 9,
    }
    at = page(VS_PAGE)
    f = VS.figures(
        json.loads((RESULTS / "scores.json").read_text(encoding="utf-8")),
        json.loads((RESULTS / "suite.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "evaluation/expected.json").read_text(encoding="utf-8")),
    )
    assert VS.answer(f) == ANSWER
    first = items(at.main)
    assert first.index(f"Markdown:{story.md(ANSWER)}") < first.index(
        f"Markdown:{story.md(VS.caveat_line(f))}"
    )
    assert first[0] == f"Title:{C.PAGE_AGENT}"
    assert [(m.label, m.value) for m in at.metric] == [
        (C.VS_TILE_FOUND_ATLAS, f"{s['atlas_found']} of {s['atlas_assessable']}"),
        (C.VS_TILE_FOUND_MODEL, "{} of {}".format(*s["same"])),
        ("ATLAS", str(s["atlas_false"])),
        ("Model alone", str(s["model_false"])),
        ("ATLAS", "none"),
        ("Model alone", "{} of {}".format(*s["invalid"])),
    ]
    captions = [str(c.value) for c in at.caption]
    assert (
        story.md(f"assessable; {s['not_assessed']} of {s['expected']} not assessed")
        in captions
    )
    assert (
        story.md("detections on the same 8; {} of {} overall".format(*s["all"]))
        in captions
    )
    tiles = [str(m.value) for m in at.markdown if str(m.value).startswith("**")]
    for title in (C.VS_TILE_FOUND, C.VS_TILE_FALSE, C.VS_TILE_INVALID):
        assert f"**{story.md(title)}**" in tiles


# == always visible, and nothing removed ============================================================
@pytest.mark.parametrize("key", list(CASES))
def test_the_always_visible_items_need_no_click(mode, key):
    run = BUNDLE / CASES[key]
    report = A.read_json(run / "agent_report.json")
    codes = [A.read_json(run / "original/outcome.json")["outcome"]]
    if key == "live6":
        codes.append(A.read_json(run / "candidates/c1/outcome.json")["outcome"])
    f, _hud = _hud_facts(key)
    at = overview(key)
    for n in range(1, 6):
        shown = "\n".join(visible(at_step(at, key, n).main))
        for code in codes:
            assert H.esc(code) in shown, code
        assert H.esc(A.CAVEAT) in shown
        assert f"**{story.md(C.CLAIM_LINE.format(claim=f.claim.statement))}**" in shown
        assert (
            story.md(story.banner_text(report, R.finished(_rr(key), report)[0]))
            in shown
        )
        assert C.REPLAY_DISCLOSURE not in shown  # Expert view only (final fix pass, F2)
        assert C.BANNER_HASHES in story.banner_text(report, None)
    if key == "harflawed":
        assert "ATLAS-authored flawed variant" in f.claim.statement
    vs = "\n".join(visible(page(VS_PAGE).main))
    for line in (VS.caveat_line(_figures()), VS.answer(_figures())):
        assert story.md(line) in vs
    assert "estimate, not billing" in vs
    lim = "\n".join(visible(page(LIM_PAGE).main))
    for line in C.KEY_LIMITS:
        assert story.code_html(line) in lim


def _figures() -> VS.Figures:
    return VS.figures(
        json.loads((RESULTS / "scores.json").read_text(encoding="utf-8")),
        json.loads((RESULTS / "suite.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "evaluation/expected.json").read_text(encoding="utf-8")),
    )


def test_every_moved_item_is_one_click_away_unchanged(mode):
    # Overview: the HAR citation, unchanged, behind "Data licence details".
    at = overview("harflawed")
    details = at.expander(key="har-details")
    assert details.label == C.HAR_DETAILS
    assert [str(c.value) for c in details.caption] == [C.HAR_CITATION_PLAIN]
    line = str(find(at.main, "har-data").children[0].value)
    assert line == f"{story.md(C.HAR_DATA_LINE)} [{C.HAR_DOI}]({C.HAR_DOI})"
    assert C.HAR_DOI in C.HAR_CITATION_PLAIN and "CC BY 4.0" in C.HAR_CITATION_PLAIN
    # The comparison page: the six caveats, the table, the four items, question and setup.
    f = _figures()
    at = page(VS_PAGE)
    caveats = at.expander(key="vs-all-caveats")
    assert caveats.label == "All caveats (6)"
    assert all(
        f"<li>{story.code_html(c)}</li>" in str(caveats.markdown[0].value)
        for c in VS.caveats(f)
    )
    table = at.expander(key="vs-data-table")
    assert table.table[0].value.equals(VS.table(f))
    means = at.expander(key="vs-means-detail")
    assert all(
        f"<li>{story.code_html(x)}</li>" in str(means.markdown[0].value)
        for x in C.VS_MEANS_PLAIN
    )
    assert [str(c.value) for c in means.caption] == [story.md(C.VS_MEANS_PLAIN_SOURCE)]
    about = [str(m.value) for m in at.expander(key="vs-about").markdown]
    assert about == [
        story.md(C.VS_QUESTION),
        story.md(C.VS_SETUP.format(r=f.repetitions, c=f.cases)),
    ]
    foot = str(find(at.main, "vs-footnote").children[0].value)
    for part in (
        C.VS_COST.format(usd=f.cost_usd),
        C.VS_REVIEW,
        C.VS_INTACT.format(v=4, t=4),
    ):
        assert story.md(part) in foot
    # How It Works & Limits: every limitation and what ATLAS does not do, unchanged.
    at = page(LIM_PAGE)
    full = at.expander(key="lim-all-limits")
    assert full.label == f"All limitations ({len(C.LIMITS_PLAIN)}), in full"
    original = L.readme_limitations()
    assert str(full.caption[0].value) == story.md(C.LIMITS_INTRO)
    assert L.limits_html(True, original) in [str(m.value) for m in full.markdown]
    assert [s.value for s in full.subheader] == [C.NOT_DO_HEAD]
    assert L._items(list(C.NOT_DO), True, ordered=False) in [
        str(m.value) for m in full.markdown
    ]


def test_the_glossary_has_exactly_the_four_terms(mode):
    at = overview()
    pop = find(at.main, "glossary")
    assert pop.proto.popover.label == "New to this? 4 terms"
    raw = str(find(pop, "glossary-terms").children[0].value)
    terms = [s for line in raw.splitlines() for s in segments(f"Markdown:{line}")]
    assert terms == [
        "Training data: the examples a model learns from.",
        "Test data: examples held back to score the model on cases it has not seen.",
        (
            "Fold: one round of a repeated train-then-test split; each round tests on a "
            "different part of the data."
        ),
        (
            "Leak: test information reaching the model during training, which can make its "
            "score look better than it would be on new data."
        ),
    ]
    assert find(overview(expert=True).main, "glossary") is None  # Expert view unchanged


def test_the_recorded_run_line(mode):
    report = A.read_json(BUNDLE / CASES["live6"] / "agent_report.json")
    assert story.banner_text(report, "2026-10-18T01:02:03Z") == (
        "Recorded run · Nemotron · finished 2026-10-18 · replayed here, not re-run. "
        "Every recorded hash is recomputed before display."
    )
    har = A.read_json(BUNDLE / CASES["harflawed"] / "agent_report.json")
    assert story.banner_text(har, "2026-10-19T00:00:00Z") == (
        "Recorded run · scripted replies, no model called · finished 2026-10-19 · "
        "replayed here, not re-run. Every recorded hash is recomputed before display."
    )


# == Expert view: unchanged ===========================================================================
@pytest.mark.parametrize(
    "name",
    [
        "overview_live6",
        "overview_harflawed",
        "overview_harclean",
        "agent_vs_model",
        "how_it_works",
    ],
)
def test_expert_view_renders_exactly_what_it_rendered_before(name):
    if name.startswith("overview_"):
        at = overview(name.removeprefix("overview_"), expert=True)
    else:
        at = page(f"app_pages/{name}.py", expert=True)
    assert items(at.main) == BEFORE["expert"][name]


# == plain copy: one line per item ===================================================================
# The items whose wording a task fixed word for word, with their word counts (final fix pass
# 2026-10-22: F3, F5, F4, F9; the fourth key limit and the glossary from the readability pass).
FIXED_WORDING = {
    "Sealed runner": 28,
    "Tamper check": 29,
    "key limit 1": 21,
    "key limit 4": 21,
    "key limit 5": 18,
    "key limit 6": 18,
}


def test_new_plain_items_are_short():
    """At most 20 words per new plain item (R0), except the items whose wording a task fixed
    word for word (`FIXED_WORDING`, counts held exactly) and the glossary."""
    tiles = dict(C.SAFETY_TILES)
    counted = {
        "Sealed runner": tiles["Sealed runner"],
        "Tamper check": tiles["Tamper check"],
        **{f"key limit {i}": line for i, line in enumerate(C.KEY_LIMITS, start=1)},
    }
    for name, words in FIXED_WORDING.items():
        assert len(counted[name].split()) == words, name
    lines = [
        *C.HOW_LINES,
        *(line for title, line in C.SAFETY_TILES if title not in FIXED_WORDING),
        *(line for name, line in counted.items() if name not in FIXED_WORDING),
        C.DIAGRAM_GROUP_CAPTION,
    ]
    for line in lines:
        assert len(line.split()) <= 20, line
    assert len(C.SAFETY_TILES) == 6 and len(C.KEY_LIMITS) == 6 and len(C.HOW_LINES) == 5
