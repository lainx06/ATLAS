"""The story layout (UI restructure slice 1): the Overview & Cases page, offline (AppTest).

Every case card shows its outcome codes from its own verified files, and "evidence changed"
for a bundle that no longer verifies; after a failed verification no verdict bar and no step
renders. Plain mode hides hashes, run paths, assertion IDs, costs and request counts; Expert
view shows them; no local filesystem path appears in either. Analogies appear only when their
assertion FAILs; every reason sentence's numbers equal the assertion's observed fields; all
new copy comes from the copy files. The bundled runs (demo/recorded) are only read; tampering
uses copies.
"""

import ast
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import recorded as R
from atlas.ui import results as RS
from atlas.ui import story

ROOT = Path(__file__).resolve().parents[2]
APP = str(ROOT / "app.py")
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR_FLAWED = "t09/agent-har_flawed-1e2267f662c0"
HAR_CLEAN = "t09/agent-har_clean-ac63eaecd7a8"
CASES = {"live6": LIVE6, "harflawed": HAR_FLAWED, "harclean": HAR_CLEAN}
HASH = re.compile(r"\b[0-9a-f]{64}\b")
LOCAL_PATH = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]|\\Users\\|/Users/|/home/")
DEFINITIONS = json.loads(
    (ROOT / "evaluation/assertion_definitions.json").read_text(encoding="utf-8")
)["definitions"]

# The descriptions the task fixes exactly (the temporal four are written from their
# definitions and listed in the report for review).
GIVEN = {
    "split.evaluation_folds_nonempty": "Every test fold contains at least one row to evaluate",
    "split.no_row_overlap": "No data row appears in both training and testing within a fold",
    "split.no_shared_source_observation": "No test row is the same original observation as "
    "a training row",
    "split.no_group_overlap": "No group, such as a person, appears in both training and "
    "testing within a fold",
    "split.sampling_unit_disjoint": "Each declared sampling unit, such as a participant, "
    "stays on one side of the split",
    "split.repeated_measures_rule": "Repeated measurements of one unit are not split between "
    "training and testing",
    "split.no_window_overlap": "Time windows used for training and testing do not overlap "
    "within the same recording stream",
    "fit.state_dependencies_within_fold_train": "Every preprocessing and model step used in a "
    "fold learned only from that fold's training rows",
    "fit.coverage_complete": "Each fold has exactly one set of predictions, traced back "
    "through every step that produced it",
    "metric.prediction_ids_match_eval_ids": "Predictions cover exactly the test rows "
    "declared for each fold",
    "metric.reported_matches_recomputed": "The score the project reports matches the score "
    "ATLAS recomputes from its predictions, within tolerance",
}
# The failure labels as they were before this slice (unchanged).
FAILURES_BEFORE = {
    "fit.coverage_complete": "predictions are not exactly one per fold, or are not "
    "traceable to their producing step",
    "fit.state_dependencies_within_fold_train": "a preprocessing or model step was fit on "
    "rows outside its fold's training data",
    "metric.prediction_ids_match_eval_ids": "the predictions do not cover exactly the rows "
    "each fold was meant to evaluate",
    "metric.reported_matches_recomputed": "the reported metric does not match the metric "
    "ATLAS recomputed",
    "split.evaluation_folds_nonempty": "a declared evaluation fold contains no evaluation "
    "rows",
    "split.no_group_overlap": "the same subjects appear in training and testing",
    "split.no_row_overlap": "the same rows appear in both training and testing",
    "split.no_shared_source_observation": "the same source observation appears in both "
    "training and testing",
    "split.no_window_overlap": "a training time window overlaps an evaluation window in the "
    "same stream",
    "split.repeated_measures_rule": "repeated measurements of one subject are split across "
    "training and testing",
    "split.sampling_unit_disjoint": "the same sampling units (subjects) appear on both sides "
    "of a split",
    "split.temporal_separation": "training and evaluation items are closer in time than the "
    "declared minimum gap",
    "temporal.cutoff_precedes_evaluation": "the training cutoff, plus the allowed gap, is not "
    "before the earliest evaluation time",
    "temporal.features_available_when_used": "a feature value was used before the time it "
    "became available",
    "temporal.training_labels_available_by_cutoff": "a training row or its label is dated "
    "after the training cutoff",
}


# -- helpers -------------------------------------------------------------------------------------
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
    at = AppTest.from_file(APP, default_timeout=60)
    if case is not None:
        at.session_state[story.CASE] = case
    at.session_state[story.EXPERT] = expert
    at.run()
    assert not at.exception, at.exception
    return at


def texts(at: AppTest, *, untrusted: bool = True) -> str:
    """Everything the page shows: Markdown, captions, labels, tables and, unless
    `untrusted` is False, the model-written frames (st.code, st.text)."""
    parts = []
    for kind in (
        "markdown",
        "caption",
        "title",
        "subheader",
        "info",
        "warning",
        "error",
    ):
        parts += [str(x.value) for x in getattr(at, kind)]
    parts += [e.label for e in at.expander] + [b.label for b in at.button]
    parts += [t.label for t in at.toggle]
    parts += [t.value.to_csv() for t in at.table]
    if untrusted:
        parts += [str(c.value) for c in at.code] + [str(t.value) for t in at.text]
    return "\n".join(parts)


def card(at: AppTest, key: str) -> str:
    description = next(c for c in C.CASES if c.key == key).description
    return next(
        str(m.value)
        for m in at.markdown
        if "hud-case" in str(m.value) and H.esc(description) in str(m.value)
    )


def outcome_codes(run: Path) -> list[str]:
    report = A.read_json(run / "agent_report.json")
    codes = [A.read_json(run / "original/outcome.json")["outcome"]]
    for i, c in enumerate(report["comparison"].get("candidates") or [], start=1):
        sub = R.candidate_subfolder(c, i)
        if (A.read_json(run / sub / "execution.json") or {}).get(
            "status"
        ) == "completed":
            codes = codes[:1] + [A.read_json(run / sub / "outcome.json")["outcome"]]
    return codes


def tampered_bundle(tmp_path: Path, monkeypatch, label: str = LIVE6) -> Path:
    root = tmp_path / "bundle"
    shutil.copytree(BUNDLE, root)
    target = root / label / "original" / "outcome.json"
    target.write_bytes(target.read_bytes().replace(b'"FAIL"', b'"PASS"', 1))
    monkeypatch.setattr(story, "BUNDLE_ROOT", root)
    return root


class Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.refs = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        for key in ("aria-labelledby", "for"):
            if a.get(key):
                self.refs += a[key].split()
        for value in a.values():
            self.refs += re.findall(r"url\(#([^)]+)\)", value or "")


# -- the copy files ------------------------------------------------------------------------------
def test_the_labels_file_has_both_fields_for_exactly_the_canonical_ids():
    data = json.loads((ROOT / "src/atlas/ui/assertion_labels.json").read_text("utf-8"))
    labels = data["labels"]
    assert set(labels) == set(DEFINITIONS)
    for aid, entry in labels.items():
        assert set(entry) == {"failure", "description"}, aid
        for field in ("failure", "description"):
            assert isinstance(entry[field], str) and entry[field].strip(), (aid, field)
    assert {aid: e["failure"] for aid, e in labels.items()} == FAILURES_BEFORE
    for aid, text in GIVEN.items():
        assert labels[aid]["description"] == text, aid
    assert H.load_descriptions() == {aid: e["description"] for aid, e in labels.items()}


SENTENCE = re.compile(r"[A-Za-z']{2,}(?:[ ,;]+[A-Za-z']{2,}){2,}")


def _literals(path: Path) -> list[str]:
    """The string constants of a module that could be user-visible sentences: not
    docstrings, not the CSS block, not markup or format fragments."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                skip.add(id(first.value))
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "CSS" for t in node.targets
        ):
            skip.update(id(n) for n in ast.walk(node.value))
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in skip
            and SENTENCE.search(node.value)
            and not re.search(r"[<>{}=#/]", node.value)
        ):
            out.append(node.value)
    return out


def test_all_new_copy_comes_from_the_copy_files():
    """The story renderer and the page files carry no inline user-visible sentence: every
    sentence they show is a constant of atlas.ui.copy (or the assertion labels file)."""
    files = [ROOT / "src/atlas/ui/story.py", *sorted((ROOT / "app_pages").glob("*.py"))]
    found = {p.name: _literals(p) for p in files}
    assert all(not v for v in found.values()), found
    # And every copy template that names fields is filled only with keyword fields.
    for name in dir(C):
        value = getattr(C, name)
        values = value.values() if isinstance(value, dict) else [value]
        for v in values:
            if isinstance(v, str):
                assert not re.search(r"\{\d*\}", v), (name, v)


def test_the_why_it_matters_line_links_to_its_source(mode):
    at = overview()
    shown = texts(at)
    assert C.TAGLINE.replace(".", "") in shown.replace("\\", "").replace(".", "")
    line = next(str(m.value) for m in at.markdown if "Kapoor" in str(m.value))
    assert f"[{C.WHY_LINK}]({C.WHY_URL})" in line
    assert C.WHY_URL == (
        "https://collaborate.princeton.edu/en/publications/"
        "leakage-and-the-reproducibility-crisis-in-machine-learning-based-/"
    )
    assert story.md(C.WHY_TEXT) in line and "294 published papers" in C.WHY_TEXT


# -- case cards ----------------------------------------------------------------------------------
def test_case_cards_show_the_verified_outcome_codes(mode):
    at = overview()
    assert [b.label for b in at.button][:3] == [c.title for c in C.CASES]
    for case in C.CASES:
        expected = outcome_codes(BUNDLE / case.run)
        shown = card(at, case.key)
        assert re.findall(r'hud-code hud-c-\w+">([^<]+)</b>', shown) == [
            H.esc(x) for x in expected
        ], case.key
        assert H.esc(C.CARD_CHANGED) not in shown
    assert outcome_codes(BUNDLE / LIVE6) == ["VIOLATION_FOUND", "NO_VIOLATION_FOUND"]
    assert outcome_codes(BUNDLE / HAR_FLAWED) == ["VIOLATION_FOUND"]
    assert outcome_codes(BUNDLE / HAR_CLEAN) == ["NO_VIOLATION_FOUND"]
    # The first case is active by default; the selection is kept in the session.
    assert at.session_state[story.CASE] == "live6"
    assert H.esc(C.CARD_SHOWING) in card(at, "live6")
    at.button(key="case-btn-harclean").click().run()
    assert at.session_state[story.CASE] == "harclean"
    assert H.esc(C.CARD_SHOWING) in card(at, "harclean")
    assert H.esc(C.CARD_SHOWING) not in card(at, "live6")


@pytest.fixture
def spies(monkeypatch):
    calls: list[str] = []

    def spy(module, name):
        original = getattr(module, name)

        def wrapper(*args, **kwargs):
            calls.append(name)
            return original(*args, **kwargs)

        monkeypatch.setattr(module, name, wrapper)

    for name in ("build", "hero", "evidence", "briefing_lines", "track", "gauge"):
        spy(H, name)
    for name in ("case", "verdict_bar", "facts"):
        spy(story, name)
    for name in ("finished_run", "finding_section", "analysis_section"):
        spy(RS, name)
    return calls


@pytest.mark.parametrize("label", [LIVE6, HAR_FLAWED])
def test_a_tampered_bundle_shows_evidence_changed_and_no_verdict_bar_or_step(
    mode, tmp_path, monkeypatch, spies, label
):
    tampered_bundle(tmp_path, monkeypatch, label)
    key = next(k for k, v in CASES.items() if v == label)
    at = overview(key)
    shown = card(at, key)
    assert H.esc(C.CARD_CHANGED) in shown
    assert not re.findall(r"VIOLATION|INCONCLUSIVE|NOT&#95;SUPPORTED", shown)
    # The other cases still verify and show their own codes.
    for other in (k for k in CASES if k != key):
        assert H.esc(C.CARD_CHANGED) not in card(at, other)
    # Only the evidence-changed panel: no verdict bar, step, toggle, outcome or briefing.
    text = texts(at)
    assert ":red-badge[EVIDENCE CHANGED]" in text and "so no outcome is shown" in text
    assert not at.expander and not at.toggle
    assert [b.label for b in at.button] == [c.title for c in C.CASES]
    markup = "\n".join(str(m.value) for m in at.markdown)
    for absent in ("hud-hero", "hud-ret", "hud-verdict", "hud-brief", "hud-leak"):
        assert absent not in markup, absent
    assert A.CAVEAT not in text
    assert spies == [], spies


def test_the_gate_also_stops_the_story_on_the_other_pages(mode, tmp_path, monkeypatch):
    """The story renders only on the Overview; the other pages never draw a verdict bar or
    a step, whatever the bundle's state."""
    tampered_bundle(tmp_path, monkeypatch)
    for page in ("try_it_live", "agent_vs_model", "how_it_works"):
        at = AppTest.from_file(APP, default_timeout=60)
        at.switch_page(f"app_pages/{page}.py")
        at.run()
        assert not at.exception, page
        # Slice 2 pages carry only the session-wide Expert view toggle.
        assert [t.label for t in at.toggle] == (
            [] if page == "try_it_live" else [C.EXPERT_TOGGLE]
        )
        assert not [e for e in at.expander if "·" in e.label]
        assert "hud-verdict" not in "\n".join(str(m.value) for m in at.markdown)


def test_the_slice_2_pages_replace_the_placeholders(mode):
    """Slice 2: the two pages that said "Coming in slice 2" now carry their content
    (tests/unit/test_ui_slice2.py tests it)."""
    for page, title, marker in (
        ("agent_vs_model", C.PAGE_AGENT, story.md(C.VS_QUESTION)),
        ("how_it_works", C.PAGE_LIMITS, C.LIMITS_HEAD),
    ):
        at = AppTest.from_file(APP, default_timeout=60)
        at.switch_page(f"app_pages/{page}.py")
        at.run()
        assert not at.exception, page
        assert [t.value for t in at.title] == [title]
        assert "Coming in slice 2" not in texts(at)
        assert marker in texts(at)


# -- plain and expert ----------------------------------------------------------------------------
@pytest.mark.parametrize("key", list(CASES))
def test_plain_mode_hides_hashes_paths_ids_and_costs(mode, key):
    at = overview(key)
    shown = texts(at, untrusted=False)  # model-written frames are shown verbatim
    assert HASH.search(shown) is None, HASH.search(shown)
    for absent in (
        "original/",
        "candidates/",
        ".json",
        "provenance.jsonl",
        "USD",
        "$0.",
    ):
        assert absent not in shown, absent
    for aid in DEFINITIONS:
        assert aid not in shown and H.esc(aid) not in shown, aid
    for absent in (
        "Model attempts",
        "Provider requests",
        "estimate cap",
        "Mission track",
    ):
        assert absent not in shown, absent
    assert "mode `" not in shown and "live `True`" not in shown  # no debug banner
    assert LOCAL_PATH.search(shown) is None, LOCAL_PATH.search(shown)
    assert str(ROOT) not in shown
    # Each step offers its one line of expert detail (after the case cards and, slice 2,
    # the tamper demo's button).
    assert [b.label for b in at.button][3] == C.TAMPER_BUTTON
    labels = [b.label for b in at.button][4:]
    assert labels == [
        C.SHOW_EXPERT,
        C.SHOW_EVIDENCE,
        C.SHOW_EXPERT,
        C.SHOW_EXPERT,
        C.SHOW_EXPERT,
    ]


@pytest.mark.parametrize("key", list(CASES))
def test_expert_view_shows_them_with_run_relative_paths_only(mode, key):
    at = overview(key, expert=True)
    shown = texts(at)
    assert HASH.search(shown) is not None
    assert "original/outcome.json" in shown and "agent_report.json" in shown
    assert any(aid in shown or H.esc(aid) in shown for aid in DEFINITIONS)
    assert "Mission track" in shown and "Model attempts" in shown
    if key == "live6":
        assert "Estimated cost (not a bill)" in shown and "USD" in shown
        assert "Provider requests" in "\n".join(str(m.value) for m in at.markdown)
        assert "LIVE RUN" in shown and "live `True`" in shown  # the full banner
    assert LOCAL_PATH.search(shown) is None, LOCAL_PATH.search(shown)
    assert str(ROOT) not in shown
    assert at.toggle(key=story.EXPERT_WIDGET).value is True


def test_the_expert_setting_is_one_session_wide_switch(mode):
    at = overview()
    assert at.toggle(key=story.EXPERT_WIDGET).value is False
    at.button(key="expert-on-2").click().run()  # "Show me the evidence"
    assert at.session_state[story.EXPERT] is True
    assert at.toggle(key=story.EXPERT_WIDGET).value is True
    at.button(key="case-btn-harflawed").click().run()  # another case: still on
    assert at.toggle(key=story.EXPERT_WIDGET).value is True
    at.toggle(key=story.EXPERT_WIDGET).set_value(False).run()
    assert at.session_state[story.EXPERT] is False
    assert at.button(key="expert-on-1")


def test_no_local_path_on_the_try_it_live_pages(monkeypatch, tmp_path):
    monkeypatch.delenv("ATLAS_HOSTED", raising=False)
    monkeypatch.setenv("ATLAS_UI_RUNS_DIR", str(tmp_path / "ui-runs"))
    for recorded in (None, tmp_path / "rec"):
        if recorded is not None:
            (recorded / "ui").mkdir(parents=True)
            shutil.copytree(BUNDLE / LIVE6, recorded / "ui" / Path(LIVE6).name)
            monkeypatch.setenv(R.RECORDED_ENV, str(recorded))
        at = AppTest.from_file(APP, default_timeout=60)
        at.switch_page("app_pages/try_it_live.py")
        at.session_state["view"] = "recorded"
        at.run()
        assert not at.exception
        shown = texts(at) + "\n".join(str(c.value) for c in at.sidebar.caption)
        assert LOCAL_PATH.search(shown) is None, LOCAL_PATH.search(shown)
        assert str(tmp_path) not in shown and str(ROOT) not in shown


# -- the verdict bar and the steps ----------------------------------------------------------------
VERDICTS = {
    "live6": "ATLAS found a violation in this evaluation. A revision proposed by Nemotron was "
    "executed in isolation and passes every required check.",
    "harflawed": "ATLAS found a violation in this evaluation. No revision was proposed.",
    "harclean": "ATLAS found no violation in this evaluation. No revision was proposed. 1 check "
    "passed on a documented declaration that ATLAS did not verify.",
}
SUMMARIES = {
    "live6": [
        "The activity classifier works on people absent from training.",
        "4 of 9 required checks FAIL in the original evaluation",
        "Nemotron proposed 2 revisions: 1 executed, 1 rejected by ATLAS validation",
        "2 typed approvals; the original and 1 revision ran in the isolated Docker runner",
        "4 checks moved from FAIL to PASS · evidence intact, 49 of 49 recorded items",
    ],
    "harflawed": [
        (
            "The activity classifier works on people absent from training. [ATLAS-authored "
            "flawed variant: this evaluation is deliberately wrong; no flaw is alleged in "
            "the original study.]"
        ),
        "4 of 11 required checks FAIL in the original evaluation; 1 could not be assessed",
        "No revision was proposed.",
        C.SCRIPT_ONLY,  # slice 2, A2: from the recorded approval reason
        "Evidence intact: 21 of 21 recorded items verified now",
    ],
    "harclean": [
        "The activity classifier works on people absent from training.",
        "All 10 required checks PASS in the original evaluation",
        "No revision was proposed.",
        C.SCRIPT_ONLY,  # slice 2, A2: from the recorded approval reason
        "Evidence intact: 21 of 21 recorded items verified now",
    ],
}


def facts_of(label: str):
    run = R.RecordedRun(BUNDLE / label, label, R.AGENT)
    report = A.read_json(run.path / "agent_report.json")
    checks = R.verify(run.path, report)
    hud = H.build(run.path, report, checks, label, bundled=True)
    return run, report, checks, hud, story.facts(run, report, checks, hud)


@pytest.mark.parametrize("key", list(CASES))
def test_the_verdict_line_and_step_summaries_are_deterministic(mode, key):
    _run, _report, checks, hud, f = facts_of(CASES[key])
    assert " ".join(story.verdict(hud, f)) == VERDICTS[key]
    assert list(story.summaries(hud, f, checks).values()) == SUMMARIES[key]
    at = overview(key)
    verdict = next(str(m.value) for m in at.markdown if "hud-verdict" in str(m.value))
    assert H.esc(VERDICTS[key]) in verdict
    labels = [e.label for e in at.expander]
    assert labels == [
        C.STEP_LABEL.format(n=n, title=story.md(C.STEP_TITLES[n]), summary=story.md(s))
        for n, s in enumerate(SUMMARIES[key], start=1)
    ]
    # Step 2 open by default; the others collapsed (their headers tell the story).
    assert [e.proto.expanded for e in at.expander] == [
        False,
        True,
        False,
        False,
        False,
    ]
    # The verdict bar: the ring ("n/n INTACT · recomputed now") and the reticles' caveat.
    hero = next(str(m.value) for m in at.markdown if "hud-hero" in str(m.value))
    total = len(checks)
    assert f">{total}/{total}</text>" in hero and "INTACT" in hero
    assert H.esc(C.RING_PLAIN) in hero and "file hashes" not in hero.split("</svg>")[1]
    assert hero.count(H.esc(A.CAVEAT)) == (2 if hud.candidate else 1)


def test_the_counts_in_step_sentences_are_the_files():
    run, report, _checks, _hud, f = facts_of(LIVE6)
    events = [
        json.loads(x) for x in (run.path / "agent_log.jsonl").read_text().splitlines()
    ]
    approvals = [e for e in events if e.get("event") == "approval"]
    typed = sum(e["approver_reason"] == "confirmed" for e in approvals)
    assert f.typed == typed == 2 and f.untyped == 0
    executed = [
        e
        for e in (
            A.read_json(run.path / "original/execution.json"),
            A.read_json(run.path / "candidates/c1/execution.json"),
        )
    ]
    for ex in executed:
        args = ex["docker_args"]
        assert args[args.index("--network") + 1] == "none" and "--read-only" in args
        assert args[args.index("--user") + 1].split(":")[0] not in ("0", "root")
    assert f.ran_isolated == 2
    outcomes = [p["outcome"] for p in report["proposals"]]
    assert outcomes == ["executed", "rejected"]


# -- analogies and reason sentences ---------------------------------------------------------------
@pytest.mark.parametrize("key", list(CASES))
def test_analogies_appear_only_when_their_assertion_fails(mode, key):
    at = overview(key)
    shown = "\n".join(str(m.value) for m in at.markdown)
    outcome = A.read_json(BUNDLE / CASES[key] / "original/outcome.json")
    status = {a["assertion_id"]: a["status"] for a in outcome["assertions"]}
    for aids, text in C.ANALOGIES:
        expected = any(status.get(a) == "FAIL" for a in aids)
        assert (H.esc(text) in shown) is expected, (key, aids)
    assert (key == "harclean") is (H.esc(C.ANALOGY_GROUP) not in shown)


def test_analogies_follow_the_status_alone():
    _run, _report, _checks, _hud, f = facts_of(LIVE6)
    f.orig_status = {"split.repeated_measures_rule": "FAIL"}
    assert story._analogies(f) == [C.ANALOGY_GROUP]
    f.orig_status = {"fit.state_dependencies_within_fold_train": "FAIL"}
    assert story._analogies(f) == [C.ANALOGY_FIT]
    f.orig_status = {aid: "PASS" for aid in DEFINITIONS}
    assert story._analogies(f) == []


def _expected_reasons(aid: str, o: dict) -> list[str]:
    """The same sentences, computed here from the observed fields directly."""
    if aid in ("split.no_group_overlap", "split.sampling_unit_disjoint"):
        by = o[
            "overlapping_groups"
            if aid == "split.no_group_overlap"
            else "overlapping_units"
        ]
        k = len({g for v in by.values() for g in v})
        m = sum(1 for v in by.values() if v)
        return [C.REASONS[aid].format(k=k, m=m, n=o["folds"], column=o["column"])]
    if aid == "fit.state_dependencies_within_fold_train" and o.get("origins"):
        return [
            C.REASONS[aid].format(
                cls=x["class"],
                rows=x["contributing_rows"],
                scope=x["fit_scope"],
                folds=len(x["affected_folds"]),
            )
            for x in o["origins"]
        ]
    if aid == "split.evaluation_folds_nonempty":
        return [
            C.REASONS[aid].format(
                empty=len(o["empty_evaluation_folds"]), folds=o["folds"]
            )
        ]
    if aid == "fit.coverage_complete":
        return [
            C.REASONS[aid].format(
                fits=o["supported_classifier_fits"],
                folds=o["folds"],
                gaps=len(o["gaps"]),
            )
        ]
    return None


@pytest.mark.parametrize("label", [LIVE6, HAR_FLAWED])
def test_every_reason_sentences_numbers_equal_the_observed_fields(label):
    _run, _report, _checks, hud, _f = facts_of(label)
    sides = [hud.observed_orig] + ([hud.observed_cand] if hud.candidate else [])
    checked = 0
    for observed in sides:
        for aid, o in observed.items():
            said = H.reasons(aid, o)
            for s in said:
                assert (
                    "null" not in s and "None" not in s and H.NOT_RECORDED not in s
                ), s
            expected = _expected_reasons(aid, o)
            if expected is not None:
                assert said == expected, aid
                checked += 1
            # Every number in a sentence is a value of the observed object (a count of a
            # list or map in it, or a recorded number).
            recorded = set(re.findall(r"\d+(?:\.\d+)?(?:e-\d+)?", json.dumps(o)))
            for number in (
                n for s in said for n in re.findall(r"\d+(?:\.\d+)?(?:e-\d+)?", s)
            ):
                sizes = _sizes(o)
                assert number in recorded or int(float(number)) in sizes, (aid, number)
    assert checked >= 5
    # The leak map and the fit-scope flow carry their sentences.
    leak = H.leak_map(hud.leak_orig, hud.rows, hud.ids, "orig", played=True, plain=True)
    flow = H.fit_flow(hud.flow_orig, hud.ids, "orig", played=True, plain=True)
    for s in H.reasons(H.LEAK_ASSERTION, hud.observed_orig[H.LEAK_ASSERTION]):
        assert H.esc(s) in leak
    for s in H.reasons(H.FIT_ASSERTION, hud.observed_orig[H.FIT_ASSERTION]):
        assert H.esc(s) in flow


def _sizes(value) -> set[int]:
    """Sizes of every list and map in an observed object, and distinct-ID counts of maps of
    lists (what the templates count)."""
    out: set[int] = set()
    if isinstance(value, dict):
        out.add(len(value))
        if all(isinstance(v, list) for v in value.values()):
            out.add(len({str(x) for v in value.values() for x in v}))
            out.add(sum(1 for v in value.values() if v))
        for v in value.values():
            out |= _sizes(v)
    elif isinstance(value, list):
        out.add(len(value))
        if value and all(isinstance(w, dict) for w in value):
            for key in ("unit_id", "fold"):
                out.add(len({str(w.get(key)) for w in value if key in w}))
        for v in value:
            out |= _sizes(v)
    return out


def test_no_reason_sentence_when_a_needed_field_is_absent():
    assert (
        H.reasons("split.no_group_overlap", {"column": "subject_id", "folds": 4}) == []
    )
    assert (
        H.reasons("split.no_group_overlap", {"overlapping_groups": {}, "folds": 4})
        == []
    )
    assert (
        H.reasons("split.no_group_overlap", {"overlapping_groups": {}, "column": "s"})
        == []
    )
    assert (
        H.reasons(H.FIT_ASSERTION, {"origins": [{"class": "X", "fit_scope": "global"}]})
        == []
    )
    assert H.reasons(H.FIT_ASSERTION, {"judged_uses": 3}) == []
    assert H.reasons("fit.coverage_complete", {"folds": None, "gaps": {}}) == []
    assert H.reasons("split.no_window_overlap", {"folds": []}) == []  # no template
    assert H.reasons("split.no_group_overlap", None) == []
    assert (
        H.reasons("temporal.features_available_when_used", {"witness_count": True})
        == []
    )
    for aid in DEFINITIONS:
        assert H.reasons(aid, {}) == [], aid


def test_every_assertion_with_observed_counts_has_a_template():
    for aid in DEFINITIONS:
        if aid == "split.no_window_overlap":  # observed folds and routes, no counts
            assert aid not in C.REASONS
            continue
        assert aid in C.REASONS, aid


# -- markup: IDs, motion, keyboard -----------------------------------------------------------------
@pytest.mark.parametrize("expert", [False, True])
@pytest.mark.parametrize("key", list(CASES))
def test_ids_are_unique_and_every_reference_resolves(mode, key, expert):
    at = overview(key, expert=expert)
    parser = Ids()
    for m in at.markdown:
        parser.feed(str(m.value))
    assert len(parser.ids) == len(set(parser.ids)), sorted(
        i for i in parser.ids if parser.ids.count(i) > 1
    )
    assert set(parser.refs) <= set(parser.ids), set(parser.refs) - set(parser.ids)
    assert all(i.startswith("atlas-") for i in parser.ids)


def test_motion_plays_once_per_case_per_session(mode):
    at = overview()

    def animated():
        return any(
            "hud-anim" in str(m.value)
            for m in at.markdown
            if "hud-hero" in str(m.value)
        )

    assert animated()
    at.run()
    assert not animated()  # a rerun renders the final state
    at.button(key="case-btn-harflawed").click().run()
    assert animated()  # another case's first selection
    at.button(key="case-btn-live6").click().run()
    assert not animated()  # never again for the same case in this session
    assert at.session_state[RS.HUD_PLAYED] >= {LIVE6, HAR_FLAWED}


def test_step_motion_respects_reduced_motion():
    css = story.CSS
    reveal = css.index("story-open 200ms")
    assert css.rindex("@media (prefers-reduced-motion: no-preference)", 0, reveal) >= 0
    assert "infinite" not in css and "infinite" not in H.CSS


def test_the_item_5_lanes_come_from_recorded_fold_fields(tmp_path):
    _run, _report, _checks, hud, _f = facts_of(LIVE6)
    assert hud.flow_cand.fold_fits is not None
    assert [fold for fold, _ in hud.flow_cand.fold_fits] == [
        "fold0",
        "fold1",
        "fold2",
        "fold3",
    ]
    assert hud.flow_orig.fold_fits is None  # the original FAILs: its origins are drawn
    # A fit event without a recorded fold: nothing is drawn (the fold is never derived).
    rel = "candidates/c1/provenance.jsonl"
    lines = (BUNDLE / LIVE6 / rel).read_text(encoding="utf-8").splitlines()
    events = [json.loads(x) for x in lines]
    first_fit = next(i for i, e in enumerate(events) if e.get("type") == "fit")
    del events[first_fit]["fold"]
    target = tmp_path / rel
    target.parent.mkdir(parents=True)
    target.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    assert H.fold_fits(tmp_path, "candidates/c1", frozenset({rel})) is None
    # A provenance file that is not in the verified set is never read.
    assert H.fold_fits(BUNDLE / LIVE6, "candidates/c1", frozenset()) is None
