"""UI restructure slice 2, offline (AppTest and pure functions).

A2: the step 4 summary of a run approved by the T-09 audit script comes from the recorded
approval reason, not from the case name. Part B (ATLAS Checks vs. Model Alone): the page shows
nothing but the evidence-changed panel when a result file's SHA-256 differs from the recorded
one; the chart's values equal scores.json; the caveats are visible without expanding; the
findings equal docs/EVALUATION.md's. Part C (How It Works & Limits): every README limitation
is present, in plain words and in its original wording. Part D (the tamper demo): the shown
result equals verify() on a changed copy; the temporary directory is removed, also on an
error; the original bundle is unchanged; the session limits hold; the size limit holds; it
works with ATLAS_HOSTED=1 and executes nothing.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas import hosted
from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import limits as L
from atlas.ui import recorded as R
from atlas.ui import story
from atlas.ui import tamper as T
from atlas.ui import versus as VS

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR_FLAWED = "t09/agent-har_flawed-1e2267f662c0"
HAR_CLEAN = "t09/agent-har_clean-ac63eaecd7a8"
RESULTS = ROOT / "evaluation" / "results" / "t11-live-20261019"
EXPECTED = ROOT / "evaluation" / "expected.json"
VS_PAGE = str(ROOT / "app_pages" / "agent_vs_model.py")
LIM_PAGE = str(ROOT / "app_pages" / "how_it_works.py")
APP = str(ROOT / "app.py")


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


def run_page(path: str, *, expert: bool = False, **state) -> AppTest:
    at = AppTest.from_file(path, default_timeout=60)
    at.session_state[story.EXPERT] = expert
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def shown(at: AppTest) -> str:
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
    parts += [t.value.to_csv() for t in at.table]
    return "\n".join(parts)


def tree_hashes(path: Path) -> dict[str, str]:
    return {
        p.relative_to(path).as_posix(): A.sha256_file(p)
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


# == A2: the T-09 audit script's approval =========================================================
def _facts(run_dir: Path, label: str):
    run = R.RecordedRun(run_dir, label, R.AGENT)
    report = A.read_json(run_dir / "agent_report.json")
    checks = R.verify(run_dir, report)
    assert R.intact(checks)
    hud = H.build(run_dir, report, checks, label, bundled=True)
    return hud, story.facts(run, report, checks, hud), checks


@pytest.mark.parametrize("label", [HAR_FLAWED, HAR_CLEAN])
def test_step_4_of_an_audit_script_run_says_no_ai_agent_took_part(label):
    hud, f, checks = _facts(BUNDLE / label, label)
    events = [e for e in A.read_log(BUNDLE / label) if e.get("event") == "approval"]
    assert [e["approver_reason"] for e in events] == ["t09_task_authorized_original"]
    assert story.summaries(hud, f, checks)[4] == C.SCRIPT_ONLY
    assert C.SCRIPT_ONLY == (
        "No AI agent took part: the audit script approved and ran the original in the "
        "isolated Docker runner."
    )
    assert f.approvals == [C.APPROVED_SCRIPT.format(who=C.WHO_ORIGINAL)]


def test_the_summary_follows_the_approval_reason_not_the_case_name(
    tmp_path, monkeypatch
):
    # The same verified run under another name still reads as the audit script's ...
    renamed = tmp_path / "t09" / "agent-some_other_project-0123456789ab"
    shutil.copytree(BUNDLE / HAR_CLEAN, renamed)
    hud, f, checks = _facts(renamed, "t09/agent-some_other_project-0123456789ab")
    assert story.summaries(hud, f, checks)[4] == C.SCRIPT_ONLY
    # ... and the HAR run, with any other recorded reason, does not.
    real = A.read_log

    def other_reason(run_dir):
        return [
            {**e, "approver_reason": "something_else"}
            if e.get("event") == "approval"
            else e
            for e in real(run_dir)
        ]

    monkeypatch.setattr(story.A, "read_log", other_reason)
    hud, f, checks = _facts(BUNDLE / HAR_CLEAN, HAR_CLEAN)
    line = story.summaries(hud, f, checks)[4]
    assert line != C.SCRIPT_ONLY
    assert line == f"{C.UNTYPED_ONLY}; {C.RAN_ORIGINAL}"


def test_live6_keeps_its_typed_approval_summary():
    hud, f, checks = _facts(BUNDLE / LIVE6, LIVE6)
    assert f.script == 0 and f.typed == 2
    assert story.summaries(hud, f, checks)[4] == (
        "2 typed approvals; the original and 1 revision ran in the isolated Docker runner"
    )


# == Part B: ATLAS Checks vs. Model Alone =============================================================
def results_copy(tmp_path: Path) -> tuple[Path, Path]:
    d = tmp_path / "t11"
    shutil.copytree(RESULTS, d)
    e = tmp_path / "expected.json"
    shutil.copyfile(EXPECTED, e)
    return d, e


def test_the_recorded_result_hashes_are_the_readme_s_and_match_now():
    readme = (RESULTS / "README.md").read_text(encoding="utf-8")
    recorded = VS.recorded_hashes(readme)
    assert set(recorded) == {"results.md", "scores.json", "suite.json"}
    for name, digest in recorded.items():
        assert A.sha256_file(RESULTS / name) == digest
    checks = VS.verify()
    assert [c.item for c in checks] == [*VS.RESULT_FILES, "expected.json"]
    assert R.intact(checks)
    suite = json.loads((RESULTS / "suite.json").read_text(encoding="utf-8"))
    assert checks[3].recorded == suite["inputs"]["expected.json"]


NUMBERS = ("19 of", "8 of 8", "0.0630621", "3 of 12", "0.83", "recall")


@pytest.mark.parametrize(
    "target",
    [
        "scores.json",
        "results.md",
        "suite.json",
        "README.md",
        "expected.json",
        "missing",
    ],
)
def test_a_changed_result_file_shows_only_the_evidence_changed_panel(
    target, tmp_path, monkeypatch, mode
):
    d, e = results_copy(tmp_path)
    if target == "expected.json":
        e.write_bytes(e.read_bytes().replace(b"s01_faulty", b"s01_faultz", 1))
    elif target == "README.md":
        p = d / "README.md"
        p.write_bytes(p.read_bytes().replace(b"`73efbe39", b"`03efbe39", 1))
    elif target == "missing":
        (d / "scores.json").unlink()
    else:
        p = d / target
        data = bytearray(p.read_bytes())
        data[len(data) // 2] ^= 0x01
        p.write_bytes(bytes(data))
    monkeypatch.setattr(VS, "RESULTS_DIR", d)
    monkeypatch.setattr(VS, "EXPECTED", e)
    for expert in (False, True):
        at = run_page(VS_PAGE, expert=expert)
        text = shown(at)
        assert C.EVIDENCE_CHANGED_CODE in text
        assert "evidence changed since recording" in text
        for n in NUMBERS:
            assert n not in text, (target, n)
        assert "<svg" not in text
        for caveat in C.VS_CAVEATS:
            assert caveat.split(":")[0] not in text
        assert C.T11_FINDINGS[0] not in text and C.VS_REVIEW not in text


def scores() -> dict:
    return json.loads((RESULTS / "scores.json").read_text(encoding="utf-8"))


def test_the_chart_values_equal_scores_json():
    s = scores()
    suite = json.loads((RESULTS / "suite.json").read_text(encoding="utf-8"))
    exp = json.loads(EXPECTED.read_text(encoding="utf-8"))
    f = VS.figures(s, suite, exp)
    a, b = s["atlas"]["totals"], s["baseline"]["totals"]
    # Independently, from scores.json: the ATLAS-assessable violations are the expected ones
    # minus ATLAS's coverage gaps; the model's valid trials are scored on them.
    gaps = {c["case_id"]: set(c["coverage_gaps"]) for c in s["atlas"]["cases"]}
    want = {
        cid: {x["assertion_id"] for x in c["expected_violated"]}
        for cid, c in exp["cases"].items()
    }
    pairs = [
        (set(t["tp"]), want[c["case_id"]] - gaps[c["case_id"]])
        for c in s["baseline"]["cases"]
        for t in c["trials"]
        if t["status"] == "VALID"
    ]
    assert (f.atlas_found, f.atlas_assessable) == (a["tp"], a["tp"] + a["fn"]) == (8, 8)
    assert (f.same_found, f.same_total) == (
        sum(len(tp & ok) for tp, ok in pairs),
        sum(len(ok) for _, ok in pairs),
    )
    assert (f.same_found, f.same_total, f.same_ids) == (19, 20, 8)
    assert (f.all_found, f.all_total) == (b["tp"], b["tp"] + b["fn"]) == (19, 23)
    assert (f.atlas_false, f.model_false) == (a["fp"], b["fp"]) == (0, 2)
    assert (f.model_invalid, f.trials) == (b["invalid_reply"], b["trials_scheduled"])
    assert (f.atlas_invalid, f.model_invalid, f.trials) == (0, 3, 12)
    assert f.cost_usd == suite["spend"]["estimated_total_usd"] == "0.0630621"
    # Copy fix pass (2026-10-21): 9 planted problems (expected, summed over the flawed cases),
    # 1 of them not assessed (in ATLAS's coverage gaps); the model's valid trials split 5 on
    # the flawed cases and 4 on the clean ones.
    flawed = [cid for cid in want if want[cid]]
    assert f.expected_total == sum(len(want[c]) for c in flawed) == 9
    assert f.not_assessed == sum(len(want[c] & gaps[c]) for c in want) == 1
    assert f.atlas_assessable + f.not_assessed == f.expected_total
    valid = {
        c["case_id"]: sum(1 for t in c["trials"] if t["status"] == "VALID")
        for c in s["baseline"]["cases"]
    }
    assert f.flawed_valid == sum(valid[c] for c in flawed) == 5
    assert f.clean_valid == sum(valid[c] for c in want if not want[c]) == 4
    assert f.flawed_valid + f.clean_valid == b["valid"]
    v = VS.values(f)
    assert v == {
        "fa": "8 of 8 assessable (1 of 9 not assessed)",
        "fs": "19 of 20 detections",
        "fo": "19 of 23 detections",
        "fm": "19 of 20 detections on the same 8 problems; 19 of 23 on all 9",
        "xa": "0",
        "xm": "2",
        "ia": "none",
        "im": "3 of 12",
    }
    labels = [b.label for b in VS.panels(f)[0][3]]
    assert labels == [
        "ATLAS",
        "Model alone, same 8 problems",
        "Model alone, all 9 problems",
    ]
    assert C.VS_CHART_NOTE.format(v=f.flawed_valid) == (
        "The model's figures count each planted problem once per usable answer on its "
        "project (5 usable answers on the two flawed projects), so they are detections, not "
        "distinct problems."
    )
    assert len(flawed) == 2
    # The bars: lengths in their panel's unit, printed values, and both layouts.
    bars = {
        key: [(b.series, b.value, b.text) for b in bs] for key, _, _, bs in VS.panels(f)
    }
    assert bars == {
        "found": [
            ("atlas", 1.0, v["fa"]),
            ("model", 19 / 20, v["fs"]),
            ("model", 19 / 23, v["fo"]),
        ],
        "false": [("atlas", 0, "0"), ("model", 2, "2")],
        "invalid": [("atlas", 0, "none"), ("model", 3, "3 of 12")],
    }
    for narrow in (False, True):
        svg = VS.chart_svg(f, narrow=narrow)
        printed = re.findall(r'font-weight="600" text-anchor="\w+">([^<]+)</text>', svg)
        drawn = [v[k] for k in ("fa", "fs", "fo", "xa", "xm", "ia", "im")]
        assert printed == [H.esc(x) for x in drawn], printed
        assert 'role="img"' in svg and "<desc" in svg and H.esc(VS.alt_text(f)) in svg
    # The data table carries the same values.
    table = VS.table(f)
    assert list(table[C.VS_SERIES_ATLAS]) == [v["fa"], v["xa"], v["ia"]]
    assert list(table[C.VS_SERIES_MODEL]) == [v["fm"], v["xm"], v["im"]]


def evaluation_findings() -> list[str]:
    text = (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")
    section = text.split("## Results (live, 2026-10-19)", 1)[1]
    block = section.split("### Findings (descriptive)", 1)[1].split(
        "Claims review:", 1
    )[0]
    return [line[2:].strip() for line in block.splitlines() if line.startswith("- ")]


def test_the_findings_are_copied_exactly_from_evaluation_md():
    assert list(C.T11_FINDINGS) == evaluation_findings()
    assert "Claims review: Gemini Argon (high effort), 2026-10-19" in C.VS_REVIEW_FULL
    assert C.VS_REVIEW == "Claims reviewed by Gemini (2026-10-19)"


def test_the_page_shows_the_question_chart_caveats_findings_cost_and_review(mode):
    at = run_page(VS_PAGE)
    text = shown(at)
    assert story.md(C.VS_QUESTION) in text  # plain view: under "About this comparison"
    assert "<svg" in text and 'class="vs-wide"' in text and 'class="vs-narrow"' in text
    f = VS.figures(
        scores(),
        json.loads((RESULTS / "suite.json").read_text(encoding="utf-8")),
        json.loads(EXPECTED.read_text(encoding="utf-8")),
    )
    # The caveats (readability pass): one visible line, outside any expander; all six,
    # unchanged, behind "All caveats (6)".
    inside = "\n".join(str(m.value) for m in at.expander(key="vs-all-caveats").markdown)
    for caveat in VS.caveats(f):
        assert H.esc(caveat) in inside, caveat
    assert story.md(VS.caveat_line(f)) in text
    for e in at.expander:
        assert story.md(VS.caveat_line(f)) not in "\n".join(
            str(m.value) for m in e.markdown
        )
    assert [e.label for e in at.expander] == [
        C.VS_ALL_CAVEATS.format(n=6),
        C.VS_DATA_TABLE,
        C.VS_MEANS_DETAIL,
        C.VS_ABOUT,
    ]
    assert "Development cases, not held-out" in VS.caveats(f)[0]
    assert "3 of the model's 12 replies" in VS.caveats(f)[3]
    assert "(3 recorded runs, 1 re-run)" in VS.caveats(f)[2]
    for item in C.VS_MEANS_PLAIN:  # slice 3: the plain-words items in plain view
        assert story.code_html(item) in text
    assert story.md(C.VS_COST.format(usd="0.0630621")) in text
    assert "estimate, not billing" in C.VS_COST
    assert story.md(C.VS_REVIEW) in text
    # Plain view: no hash.
    assert re.search(r"\b[0-9a-f]{64}\b", text) is None


def test_expert_view_adds_files_hashes_ids_and_every_trial(mode):
    at = run_page(VS_PAGE, expert=True)
    text = shown(at)
    for c in VS.verify():
        assert c.recomputed in text
    for finding in C.T11_FINDINGS:
        assert story.code_html(finding) in text
    assert story.md(C.VS_REVIEW_FULL) in text
    trials = next(t for t in at.table if "trial" in t.value.columns)
    assert len(trials.value) == 12
    assert list(trials.value["status"]).count("INVALID_REPLY") == 3
    assert "fit.state_dependencies_within_fold_train" in text
    assert "2937182895" in text


# == Part C: How It Works & Limits ================================================================
def test_every_readme_limitation_is_present_plain_and_expert(mode):
    original = L.readme_limitations()
    assert len(original) == 13
    assert len(C.LIMITS_PLAIN) == len(original)
    plain = shown(run_page(LIM_PAGE))
    expert = shown(run_page(LIM_PAGE, expert=True))
    for text in C.LIMITS_PLAIN:
        assert story.code_html(text) in plain and story.code_html(text) in expert
    for text in original:
        assert story.code_html(text) not in plain
        assert story.code_html(text) in expert, text
    # The plain wording keeps every limit's key terms.
    pairs = dict(zip(original, C.LIMITS_PLAIN, strict=True))
    keep = {
        "not tamper-proof": "not tamper-proof",
        "upstream feature extraction": "extracted",
        "did not declare": "did not declare",
        "exact-value screen": "exact values",
        "statistical independence": "statistically",
        "listed assertions passed": "listed checks passed",
        "development cases": "development projects",
        "not proof of safety": "safe",
        "5 of the 8 live runs": "5 of the 8",
        "not independent benchmark evidence": "not independent benchmark evidence",
        "exactly three claim types": "exactly three kinds of claim",
        "2026-12-15": "15 December 2026",
        "Procedures": "procedures",
    }
    for word, plain_word in keep.items():
        item = next(o for o in original if word in o)
        assert plain_word in pairs[item], (word, pairs[item])


def test_how_it_works_has_five_steps_safety_and_what_atlas_does_not_do(mode):
    at = run_page(LIM_PAGE)
    text = shown(at)
    assert len(C.HOW_STEPS) == 5
    # Plain view (readability pass): one line per step, six tiles, the four key limits;
    # the longer text is in Expert view, "What ATLAS does not do" behind one click.
    for title, line in zip(C.HOW_DIAGRAM_SHORT, C.HOW_LINES, strict=True):
        assert H.esc(title) in text and story.code_html(line) in text
    assert H.esc(C.DIAGRAM_LABEL) in text and "lim-fade" in text
    assert re.search(r'lim-box">[^<]*\d', text) is None  # no number in the diagram
    for title, line in C.SAFETY_TILES:
        assert story.md(title) in text and story.md(line) in text
    for item in C.KEY_LIMITS:
        assert story.code_html(item) in text
    inside = "\n".join(str(m.value) for m in at.expander(key="lim-all-limits").markdown)
    for item, _source in C.NOT_DO:
        assert story.code_html(item) in inside
    expert_view = shown(run_page(LIM_PAGE, expert=True))
    for title, body, _source in C.HOW_STEPS:
        assert H.esc(title) in expert_view and story.code_html(body) in expert_view
    for item, _source in C.SAFETY:
        assert story.code_html(item) in expert_view
    assert "does not prove a claim true" in C.NOT_DO[0][0]
    # Sources only in Expert view; the fade plays once per session.
    assert "docs/SPEC.md" not in text
    at.run()
    assert "lim-fade" not in shown(at)
    expert = shown(run_page(LIM_PAGE, expert=True))
    for _t, _b, source in C.HOW_STEPS:
        assert H.esc(source) in expert
    assert H.esc("docs/HOSTED_OPERATIONS.md") in expert


def test_the_new_modules_carry_no_inline_sentence():
    from test_ui_story import _literals

    for name in ("versus.py", "limits.py", "tamper.py"):
        assert _literals(ROOT / "src" / "atlas" / "ui" / name) == [], name


# == Part D: the tamper demo ======================================================================
def test_the_files_offered_are_the_run_s_own_hashed_files():
    expect = {
        LIVE6: [
            "original/outcome.json",
            "candidates/c1/outcome.json",
            "original/execution.json",
            "agent_log.jsonl",
        ],
        HAR_FLAWED: [
            "original/outcome.json",
            "original/execution.json",
            "agent_log.jsonl",
        ],
        HAR_CLEAN: [
            "original/outcome.json",
            "original/execution.json",
            "agent_log.jsonl",
        ],
    }
    for label, files in expect.items():
        report = A.read_json(BUNDLE / label / "agent_report.json")
        assert T.options(R.verify(BUNDLE / label, report)) == files


def _manual(run_dir: Path, rel: str, tmp_path: Path) -> list[R.Check]:
    """The demo's steps by hand: a copy, its last byte changed, verify()."""
    copy = tmp_path / "manual"
    shutil.copytree(run_dir, copy)
    p = copy / rel
    data = bytearray(p.read_bytes())
    data[-1] = 0x0A if data[-1] == 0x20 else 0x20
    p.write_bytes(bytes(data))
    return R.verify(copy, A.read_json(copy / "agent_report.json"))


@pytest.mark.parametrize(
    "label,rel",
    [
        (LIVE6, "original/outcome.json"),
        (LIVE6, "candidates/c1/outcome.json"),
        (LIVE6, "agent_log.jsonl"),
        (HAR_FLAWED, "original/execution.json"),
        (HAR_CLEAN, "original/outcome.json"),
    ],
)
def test_the_demo_result_equals_verify_on_the_changed_copy(label, rel, tmp_path):
    before = tree_hashes(BUNDLE / label)
    demo = T.run_demo(BUNDLE / label, rel)
    assert list(demo.checks) == _manual(BUNDLE / label, rel, tmp_path)
    assert [c.item for c in demo.differing] == [rel]
    assert demo.differing[0].status == "changed"
    assert demo.offset == (BUNDLE / label / rel).stat().st_size - 1
    assert (demo.old, demo.new) == (0x0A, 0x20)
    assert R.intact(list(demo.original_checks))
    assert demo.original_files == len(before)
    assert tree_hashes(BUNDLE / label) == before  # the original bundle is unchanged


def _track_tmp(monkeypatch) -> list[Path]:
    made = []
    real = tempfile.mkdtemp

    def mkdtemp(*a, **k):
        made.append(Path(real(*a, **k)))
        return str(made[-1])

    monkeypatch.setattr(T.tempfile, "mkdtemp", mkdtemp)
    return made


def test_the_temporary_directory_is_outside_the_repository_and_removed(monkeypatch):
    made = _track_tmp(monkeypatch)
    T.run_demo(BUNDLE / LIVE6, "original/outcome.json")
    assert len(made) == 1 and not made[0].exists()
    with pytest.raises(ValueError):
        made[0].resolve().relative_to(ROOT.resolve())


@pytest.mark.parametrize("where", ["copy", "change", "verify"])
def test_the_temporary_directory_is_removed_on_an_injected_error(where, monkeypatch):
    made = _track_tmp(monkeypatch)
    before = tree_hashes(BUNDLE / LIVE6)
    if where == "copy":
        monkeypatch.setattr(T, "_copy", lambda *a: (_ for _ in ()).throw(OSError("x")))
    elif where == "change":
        monkeypatch.setattr(
            T, "change_one_byte", lambda *a: (_ for _ in ()).throw(RuntimeError("x"))
        )
    else:
        real = R.verify

        def boom(run_dir, report):
            if made and Path(run_dir).is_relative_to(made[0]):
                raise RuntimeError("injected")
            return real(run_dir, report)

        monkeypatch.setattr(T.R, "verify", boom)
    with pytest.raises((OSError, RuntimeError)):
        T.run_demo(BUNDLE / LIVE6, "original/outcome.json")
    assert made and not made[0].exists()
    assert tree_hashes(BUNDLE / LIVE6) == before


def test_the_page_reports_an_injected_error_with_a_fixed_message(monkeypatch, mode):
    made = _track_tmp(monkeypatch)
    monkeypatch.setattr(
        T, "change_one_byte", lambda *a: (_ for _ in ()).throw(RuntimeError("secret"))
    )
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.button(key=f"tamper-go-{H.run_hash(LIVE6)}").click().run()
    assert not at.exception
    text = shown(at)
    assert story.md(C.TAMPER_FAILED) in text and "secret" not in text
    assert made and not made[0].exists()


def test_a_changed_original_is_reported_not_shown(tmp_path, monkeypatch):
    run = tmp_path / "run"
    shutil.copytree(BUNDLE / LIVE6, run)
    real = T.change_one_byte

    def also_original(path):  # a fault that touches the original during the demo
        target = run / "replies" / "a1.txt"
        target.write_bytes(target.read_bytes() + b" ")
        return real(path)

    monkeypatch.setattr(T, "change_one_byte", also_original)
    with pytest.raises(T.OriginalChanged):
        T.run_demo(run, "original/outcome.json")
    # And an original that does not verify is refused before any copy.
    made = _track_tmp(monkeypatch)
    with pytest.raises(T.Refused) as exc:
        T.run_demo(run, "original/outcome.json")
    assert exc.value.message == C.TAMPER_NOT_INTACT and made == []


def test_only_the_fixed_files_may_be_changed(tmp_path):
    for rel in (
        "agent_report.json",
        "../x",
        "replies/a1.txt",
        "original/../agent_report.json",
    ):
        with pytest.raises(T.Refused) as exc:
            T.run_demo(BUNDLE / LIVE6, rel)
        assert exc.value.message == C.TAMPER_UNKNOWN_FILE
    with pytest.raises(T.Refused):  # not recorded for a HAR audit run
        T.run_demo(BUNDLE / HAR_CLEAN, "candidates/c1/outcome.json")


def test_the_size_limit_refuses_with_a_fixed_message(monkeypatch):
    made = _track_tmp(monkeypatch)
    monkeypatch.setattr(T, "MAX_BYTES", 1_000_000)  # live6 is about 0.83 MB; HAR 8 MB
    T.run_demo(BUNDLE / LIVE6, "original/outcome.json")
    with pytest.raises(T.Refused) as exc:
        T.run_demo(BUNDLE / HAR_FLAWED, "original/outcome.json")
    assert exc.value.message == C.TAMPER_TOO_LARGE.format(mb=50)
    assert len(made) == 1  # no copy was made for the refused run
    assert T.MAX_MB * 1024 * 1024 == 50 * 1024 * 1024


def test_a_link_in_the_run_refuses_the_demo(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(BUNDLE / LIVE6, run)
    try:
        os.symlink(run / "agent_log.jsonl", run / "link.txt")
    except OSError:
        pytest.skip("symlink creation needs a permission this host does not grant")
    with pytest.raises(T.Refused) as exc:
        T.run_demo(run, "original/outcome.json")
    assert exc.value.message == C.TAMPER_LINK


def test_the_session_limits_one_at_a_time_and_five_per_hour():
    now = [1000.0]
    limit = T.SessionLimit(clock=lambda: now[0])
    assert limit.acquire() is None
    assert limit.acquire() == C.TAMPER_BUSY  # one at a time
    limit.release()
    for _ in range(4):
        now[0] += 60
        assert limit.acquire() is None
        limit.release()
    now[0] += 60
    assert limit.acquire() == C.TAMPER_RATE.format(n=5)  # the sixth within the hour
    assert not limit.lock.locked()
    now[0] = 1000.0 + 3600.5  # the first start leaves the window
    assert limit.acquire() is None
    limit.release()


def test_the_page_enforces_the_limit(monkeypatch, mode):
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    key = f"tamper-go-{H.run_hash(LIVE6)}"
    for _ in range(5):
        at.button(key=key).click().run()
        assert not at.exception
        assert story.md(C.TAMPER_STATEMENT) in shown(at)
    at.button(key=key).click().run()
    text = shown(at)
    assert story.md(C.TAMPER_RATE.format(n=5)) in text
    assert story.md(C.TAMPER_STATEMENT) not in text


def test_the_demo_works_hosted_and_executes_nothing(monkeypatch):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    assert hosted.enabled()

    def tripwire(*a, **k):
        raise AssertionError("the tamper demo started a process or opened a socket")

    for name in ("Popen", "run", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, tripwire)
    monkeypatch.setattr(os, "system", tripwire)
    monkeypatch.setattr(socket.socket, "connect", tripwire)
    monkeypatch.setattr(hosted, "refuse_if_hosted", tripwire)  # nothing it guards runs
    before = tree_hashes(BUNDLE / LIVE6)
    demo = T.run_demo(BUNDLE / LIVE6, "original/outcome.json")
    assert [c.item for c in demo.differing] == ["original/outcome.json"]
    assert tree_hashes(BUNDLE / LIVE6) == before


def test_the_overview_shows_the_real_result_in_plain_and_expert(mode):
    before = tree_hashes(BUNDLE / LIVE6)
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state[story.EXPERT] = False
    at.run()
    assert story.md(C.TAMPER_HEAD) in shown(at)
    assert story.md(C.TAMPER_STATEMENT) not in shown(at)  # before: nothing claimed
    at.button(key=f"tamper-go-{H.run_hash(LIVE6)}").click().run()
    assert not at.exception
    text = shown(at)
    head = C.TAMPER_RESULT[1].format(t=49, items="the original's recorded result")
    assert story.md(head) in text
    assert story.md(C.TAMPER_STATEMENT) in text
    assert "1 of 49 recorded items differ: the original" in head
    # Expert view: the item itself and its hashes.
    at.session_state[story.EXPERT] = True
    at.session_state[story.EXPERT_WIDGET] = True
    at.run()
    text = shown(at)
    assert (
        story.md(C.TAMPER_RESULT[1].format(t=49, items="original/outcome.json")) in text
    )
    recorded = next(
        c.recorded
        for c in R.verify(
            BUNDLE / LIVE6, A.read_json(BUNDLE / LIVE6 / "agent_report.json")
        )
        if c.item == "original/outcome.json"
    )
    assert recorded in text
    assert tree_hashes(BUNDLE / LIVE6) == before
