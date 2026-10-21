"""Copy accuracy fix pass (Gemini review, 2026-10-21), offline (AppTest and pure functions).

G1-G18: the rendered copy equals the reviewed wording. G3: the comparison page's title and
navigation label. G4: every number on the comparison page comes from scores.json and
evaluation/expected.json (detections summed over usable answers, not distinct problems). G9:
step 2 is "What the checks found" for every case, and the everyday analogies appear only when
their check FAILs (none on har_clean). G17: a reason sentence never reads "0 ... in 0 of N".
G13-G15: the changed labels keep both fields for every canonical ID.
"""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import limits as L
from atlas.ui import story
from atlas.ui import versus as VS

ROOT = Path(__file__).resolve().parents[2]
APP = str(ROOT / "app.py")
VS_PAGE = str(ROOT / "app_pages" / "agent_vs_model.py")
LIM_PAGE = str(ROOT / "app_pages" / "how_it_works.py")
BUNDLE = ROOT / "demo" / "recorded"
RESULTS = ROOT / "evaluation" / "results" / "t11-live-20261019"
EXPECTED = ROOT / "evaluation" / "expected.json"
DEFINITIONS = json.loads(
    (ROOT / "evaluation" / "assertion_definitions.json").read_text(encoding="utf-8")
)["definitions"]
CASES = {c.key: c.run for c in C.CASES}


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


def run(path: str, *, expert: bool = False, case: str | None = None) -> AppTest:
    at = AppTest.from_file(path, default_timeout=120)
    at.session_state[story.EXPERT] = expert
    if case is not None:
        at.session_state[story.CASE] = case
    at.run()
    assert not at.exception, at.exception
    return at


def shown(at: AppTest) -> str:
    parts = []
    for kind in ("markdown", "caption", "title", "subheader"):
        parts += [str(x.value) for x in getattr(at, kind)]
    parts += [e.label for e in at.expander]
    parts += [t.value.to_csv() for t in at.table]
    return "\n".join(parts)


# == the exact wording ==============================================================================
def test_the_reviewed_wording():
    assert C.TAGLINE == (
        "ATLAS checks a machine-learning evaluation for leaks between training and test "
        "data, shows its evidence, and tests a proposed fix in an isolated container."
    )
    assert C.STEP_TITLES[2] == "What the checks found" == C.REPORT_LEAK
    assert C.STEP_TITLES[5] == "Verified evidence"
    assert C.PAGE_AGENT == "ATLAS Checks vs. Model Alone"
    assert C.VERDICT_ALL_PASS.format(model="Nemotron") == (
        "A revision proposed by Nemotron was executed in isolation and passes every "
        "required check within the coverage shown."
    )
    cases = {c.key: c.description for c in C.CASES}
    assert cases["harflawed"] == (
        "Real smartphone sensor data (UCI HAR) with a deliberately flawed evaluation "
        "written by ATLAS's authors."
    )
    assert cases["harclean"] == (
        "The same real sensor data with a clean evaluation written by ATLAS's authors: "
        "each person on one side of the split, and every step fit inside each fold."
    )
    assert C.LEAK_Y_PLAIN == "Groups on both sides of the split, by test fold"
    assert "in the original" not in H.LEAK_Y_LABEL
    assert C.HOW_STEPS[3][1] == (
        "A person approves the original code and each exact revision by typing the start "
        "of its code hash; the approval is bound to the snapshot and code hashes. Any "
        "change to the code needs a new approval."
    )
    safety = [text for text, _source in C.SAFETY]
    assert safety[0] == (
        "Isolated Docker runner: no network, a non-root user and a read-only filesystem, "
        "with limits on memory, CPU, processes and time. If the container runner is "
        "unavailable, ATLAS stops and never runs code directly on the host computer."
    )
    assert safety[1] == (
        "Typed approval bound to the snapshot and code hashes: an approval names the exact "
        "original or revision code, and the runner refuses to run any other code."
    )
    assert safety[4] == (
        "The hosted demo executes no project or candidate code: it replays recorded runs, "
        "and in a hosted live session it checks the AI's proposals and shows them as not "
        "executed here."
    )
    assert C.NOT_DO[1][0] == (
        "It does not check how the data was collected or labelled, or how features were "
        "extracted or normalised before the feature table the project supplies: its "
        "tracing starts at that table."
    )


def test_no_claim_of_proof_or_safety_in_the_copy():
    """G2: "proof", "prove(s)", "guarantee", "secure", "safe(ly)" appear only in negative
    statements ("does not prove ..."), never as a claim."""
    import re

    words = re.compile(
        r"\b(proof|proves?|guarantee\w*|secure\w*|safe|safely)\b", re.IGNORECASE
    )
    texts = []
    for name in dir(C):
        if name.startswith("_"):
            continue
        value = getattr(C, name)
        stack = [value]
        while stack:
            v = stack.pop()
            if isinstance(v, str):
                texts.append(v)
            elif isinstance(v, dict):
                stack += list(v.values())
            elif isinstance(v, tuple | list):
                stack += list(v)
            elif hasattr(v, "__dataclass_fields__") and not isinstance(v, type):
                stack += [getattr(v, f) for f in v.__dataclass_fields__]
    labels = json.loads(
        (ROOT / "src/atlas/ui/assertion_labels.json").read_text(encoding="utf-8")
    )["labels"]
    texts += [x for e in labels.values() for x in e.values()]
    hits = [t for t in texts if words.search(t)]
    allowed = re.compile(r"\b(not|None of them)\b[^.]*\b(prove|proves|tamper-proof)\b")
    for t in hits:
        for sentence in re.split(r"(?<=[.;])\s+", t):
            if words.search(sentence):
                assert allowed.search(sentence) or "not tamper-proof" in sentence, (
                    sentence
                )


# == G3: the comparison page's name ===================================================================
def test_the_comparison_page_title_and_nav_label(mode):
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"app_pages/agent_vs_model.py",\n        title=C.PAGE_AGENT,' in app
    at = run(VS_PAGE)
    assert [t.value for t in at.title] == ["ATLAS Checks vs. Model Alone"]
    for path in (ROOT / "app.py", ROOT / "app_pages/agent_vs_model.py"):
        assert "AI Agent vs" not in path.read_text(encoding="utf-8")


# == G4: the comparison's numbers ====================================================================
def sources():
    scores = json.loads((RESULTS / "scores.json").read_text(encoding="utf-8"))
    suite = json.loads((RESULTS / "suite.json").read_text(encoding="utf-8"))
    exp = json.loads(EXPECTED.read_text(encoding="utf-8"))
    return scores, suite, exp


def test_every_comparison_number_comes_from_its_source():
    scores, suite, exp = sources()
    want = {
        cid: {e["assertion_id"] for e in c["expected_violated"]}
        for cid, c in exp["cases"].items()
    }
    flawed = [c for c in want if want[c]]
    clean = [c for c in want if not want[c]]
    gaps = {c["case_id"]: set(c["coverage_gaps"]) for c in scores["atlas"]["cases"]}
    base = {c["case_id"]: c for c in scores["baseline"]["cases"]}
    a, b = scores["atlas"]["totals"], scores["baseline"]["totals"]

    def valid(cids):
        return [t for c in cids for t in base[c]["trials"] if t["status"] == "VALID"]

    planted = sum(len(want[c]) for c in flawed)  # 9: expected, summed over flawed cases
    assessable = a["tp"] + a["fn"]  # 8
    chances = sum(
        len(want[c])
        for c in flawed
        for t in base[c]["trials"]
        if t["status"] == "VALID"
    )
    same = sum(
        len(want[c] - gaps[c])
        for c in flawed
        for t in base[c]["trials"]
        if t["status"] == "VALID"
    )
    assert (len(flawed), len(clean)) == (2, 2)
    assert planted == 9 and assessable == 8
    assert planted - assessable == sum(len(want[c] & gaps[c]) for c in want) == 1
    assert (len(valid(flawed)), len(valid(clean))) == (5, 4)
    assert chances == b["tp"] + b["fn"] == 23
    assert same == 20 and b["tp"] == 19 and b["fp"] == 2
    assert base["har_flawed"]["fp"] == 2
    assert all(base[c]["fp"] == 0 for c in clean)

    f = VS.figures(scores, suite, exp)
    v = VS.values(f)
    assert v["fa"] == "8 of 8 assessable (1 of 9 not assessed)"
    assert v["fs"] == "19 of 20 detections"
    assert v["fo"] == "19 of 23 detections"
    assert v["fm"] == "19 of 20 detections on the same 8 problems; 19 of 23 on all 9"
    rows = [(bar.label, bar.text) for bar in VS.panels(f)[0][3]]
    assert rows == [
        ("ATLAS", "8 of 8 assessable (1 of 9 not assessed)"),
        ("Model alone, same 8 problems", "19 of 20 detections"),
        ("Model alone, all 9 problems", "19 of 23 detections"),
    ]
    assert VS.table(f)[C.VS_SERIES_MODEL][0] == v["fm"]
    assert VS.table(f)[C.VS_SERIES_ATLAS][0] == v["fa"]
    assert C.VS_CHART_NOTE.format(v=f.flawed_valid) == (
        "The model's figures count each planted problem once per usable answer on its "
        "project (5 usable answers on the two flawed projects), so they are detections, "
        "not distinct problems."
    )
    assert C.VS_MEANS_PLAIN[0] == (
        "The two flawed projects contain 9 planted problems. The model on its own gave 5 "
        "usable answers on those projects, so there were 23 chances to name a planted "
        "problem; it named 19. It raised 2 false alarms on the flawed real-data project and "
        "none in its 4 usable answers on the two clean projects."
    )
    # Every chart number is in the chart's accessible description too.
    assert H.esc(v["fa"]) in VS.chart(f) and H.esc(v["fm"]) in VS.chart(f)


def test_the_full_atlas_figure_has_no_gap_note():
    scores, suite, exp = sources()
    for case in scores["atlas"]["cases"]:
        case["coverage_gaps"] = []
    f = VS.figures(scores, suite, exp)
    assert f.not_assessed == 0 and VS.values(f)["fa"] == "8 of 8 assessable"


def test_the_page_shows_the_note_under_the_chart(mode):
    for expert in (False, True):
        at = run(VS_PAGE, expert=expert)
        text = shown(at)
        assert story.md(C.VS_CHART_NOTE.format(v=5)) in text
        assert "19 of 20 detections on the same 8 problems; 19 of 23 on all 9" in text


# == G9: step 2 and the analogies =====================================================================
@pytest.mark.parametrize("key", list(CASES))
def test_step_2_title_and_analogies_only_on_fail(mode, key):
    at = run(APP, case=key)
    labels = [e.label for e in at.expander]
    step2 = [x for x in labels if x.startswith("**2 ·")]
    assert len(step2) == 1 and step2[0].startswith("**2 · What the checks found** — ")
    assert not any("The leak" in x for x in labels)
    markdown = "\n".join(str(m.value) for m in at.markdown)
    outcome = A.read_json(BUNDLE / CASES[key] / "original/outcome.json")
    fails = {a["assertion_id"] for a in outcome["assertions"] if a["status"] == "FAIL"}
    for aids, text in C.ANALOGIES:
        assert (H.esc(text) in markdown) is bool(fails & set(aids)), (key, aids)
    if key == "harclean":
        assert not fails
        assert "hud-analogy" not in markdown
        assert H.esc(C.ANALOGY_LABEL) not in markdown


# == G17: the zero case ==============================================================================
def test_reason_sentences_have_a_zero_form():
    folds = {"0": [], "1": [], "2": []}
    assert H.reasons(
        "split.no_group_overlap",
        {"folds": 3, "column": "subject", "overlapping_groups": folds},
    ) == ["No subject value appears on both sides of the split in any of the 3 folds"]
    assert H.reasons(
        "split.sampling_unit_disjoint",
        {"folds": 3, "column": "subject", "overlapping_units": folds},
    ) == [
        (
            "No subject value (the sampling unit) appears on both sides of the split in "
            "any of the 3 folds"
        )
    ]
    assert H.reasons(
        "split.no_row_overlap", {"folds": 3, "overlapping_rows": folds}
    ) == ["No row appears in both training and testing in any of the 3 folds"]
    assert H.reasons(
        "split.no_shared_source_observation", {"shared_observation_ids": folds}
    ) == ["No original observation appears in both training and testing in any fold"]
    assert H.reasons(
        "split.repeated_measures_rule",
        {"units": [{"route": "sampling_unit", "column": "subject", "witnesses": []}]},
    ) == ["No subject value has measurements on both sides of the split in any fold"]
    # k > 0: unchanged.
    assert H.reasons(
        "split.no_group_overlap",
        {
            "folds": 3,
            "column": "subject",
            "overlapping_groups": {"0": ["a", "b"], "1": []},
        },
    ) == ["2 subject values appear on both sides of the split in 1 of 3 folds"]
    assert set(C.REASONS_NONE) <= set(C.REASONS)
    for text in C.REASONS_NONE.values():
        assert "{k}" not in text and "{m}" not in text


@pytest.mark.parametrize("key", list(CASES))
def test_no_rendered_reason_reads_zero_in_zero(mode, key):
    import re

    text = shown(run(APP, case=key, expert=True))
    assert re.search(r"\b0 \w[^.]*\bin 0 (of \d+ )?folds", text) is None
    if key == "harclean":
        assert "appears on both sides of the split in any of the" in text


# == G13-G15: the labels =============================================================================
def test_the_changed_labels_follow_their_definitions():
    labels = json.loads(
        (ROOT / "src/atlas/ui/assertion_labels.json").read_text(encoding="utf-8")
    )["labels"]
    assert set(labels) == set(DEFINITIONS)
    for aid, entry in labels.items():
        assert set(entry) == {"failure", "description"}, aid
        assert all(isinstance(x, str) and x.strip() for x in entry.values()), aid
    cut = labels["temporal.cutoff_precedes_evaluation"]
    assert cut["failure"] == (
        "the declared gap is negative, or the training cutoff plus the declared gap comes "
        "after the earliest test prediction time"
    )
    assert "declared gap" in cut["description"] and "allowed gap" not in json.dumps(
        labels
    )
    assert labels["split.repeated_measures_rule"] == {
        "failure": "repeated measurements of a unit (or its containing group) appear on "
        "both sides of a fold's split",
        "description": "Within each fold, repeated measurements of a unit (or its "
        "containing group) are not split between training and testing",
    }
    # The containing-group route is part of the definition (route B, contained group).
    assert "contained group" in DEFINITIONS["split.repeated_measures_rule"]
    assert labels["fit.coverage_complete"]["description"] == (
        "Each fold has exactly one set of predictions, traced back through every recorded "
        "supported step on its path"
    )
    assert labels["fit.state_dependencies_within_fold_train"]["description"] == (
        "Every recorded preprocessing and model step used in a fold learned only from that "
        "fold's training rows"
    )
    for aid in ("split.no_group_overlap", "split.no_row_overlap"):
        assert labels[aid]["failure"].endswith("within a fold"), aid


# == G18: the limits page follows README ==============================================================
def test_the_schema_failure_figure(mode):
    readme = L.readme_limitations()
    t06 = next(x for x in readme if x.startswith("T-06"))
    assert (
        "schema failures in 5 of the 8 live runs (runs 1 to 8, with 3 and 3b counted as one)"
        in t06
    )
    plain = shown(run(LIM_PAGE))
    assert "5 of 8 live runs" not in plain
    assert "with 3 and 3b counted as one" in plain
