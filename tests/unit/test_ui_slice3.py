"""UI restructure slice 3, offline (AppTest and pure functions).

A3: the How It Works & Limits page carries the recounted schema-failure figure and the
recorded hosted state, in plain and Expert view. B1: the comparison page's plain "What this
means" is exactly the four plain items, and every number in them equals scores.json or the
reviewed findings; Expert view shows the reviewed findings. C1/C2: the tamper demo is a
collapsed expander after step 5; the Expert view switch sits beside the Overview's title (and
is not drawn when the selected case fails verification). D: the audit report is built only
after the gate, holds no model-written text, escapes every value, is deterministic with an
injected clock, executes nothing in hosted mode, and is named atlas-audit-<id>-<outcome>.html.
E: every colour token meets its contrast floor.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas import hosted
from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import limits as L
from atlas.ui import recorded as R
from atlas.ui import report as RP
from atlas.ui import story
from atlas.ui import versus as VS

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR_FLAWED = "t09/agent-har_flawed-1e2267f662c0"
HAR_CLEAN = "t09/agent-har_clean-ac63eaecd7a8"
RESULTS = ROOT / "evaluation" / "results" / "t11-live-20261019"
APP = str(ROOT / "app.py")
VS_PAGE = str(ROOT / "app_pages" / "agent_vs_model.py")
LIM_PAGE = str(ROOT / "app_pages" / "how_it_works.py")
CLOCK = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)


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
    for kind in ("markdown", "caption", "title", "subheader", "warning", "error"):
        parts += [str(x.value) for x in getattr(at, kind)]
    parts += [e.label for e in at.expander] + [b.label for b in at.button]
    parts += [t.value.to_csv() for t in at.table]
    return "\n".join(parts)


def scores() -> dict:
    return json.loads((RESULTS / "scores.json").read_text(encoding="utf-8"))


# == A3 ===========================================================================================
def test_the_limits_page_shows_the_recounted_and_recorded_limitations(mode):
    readme = L.readme_limitations()
    t06 = next(x for x in readme if x.startswith("T-06"))
    hosted_item = next(x for x in readme if "hosted app" in x)
    assert (
        "schema failures in 5 of the 8 live runs (runs 1 to 8, with 3 and 3b counted as one)"
        in t06
    )
    assert "3 of 6" not in t06
    assert hosted_item == (
        "Established on 2026-10-19 for the private hosted app: Nebius connectivity and the "
        "locked build on the host, and a smoke test on the public and judge routes. Not yet "
        "established: a signed-out check of the public app and availability through "
        "2026-12-15 (both at publication)."
    )
    plain = shown(run_page(LIM_PAGE))
    expert = shown(run_page(LIM_PAGE, expert=True))
    assert (
        story.code_html(
            "schema failures in 5 of the 8 live runs: runs 1 to 8, with 3 and 3b counted as one"
        )
        in plain
    )
    for item in (t06, hosted_item):
        assert story.code_html(item) in expert and story.code_html(item) not in plain
    assert "3 of 6" not in plain and "3 of 6" not in expert
    assert "Until deployment" not in plain


# == B1 ===========================================================================================
GIVEN = (
    (
        "The two flawed projects contain 9 planted problems. The model on its own gave 5 usable "
        "answers on those projects, so there were 23 chances to name a planted problem; it named "
        "19. It raised 2 false alarms on the flawed real-data project and none in its 4 usable "
        "answers on the two clean projects."
    ),
    (
        "ATLAS found all 8 of the planted problems its checks can assess, with no false alarms. One "
        "planted problem (overlapping time windows in the real-data project) needs information the "
        "project did not record, so ATLAS reported it as not assessed instead of guessing. The model "
        "on its own did not name it in any of its 3 usable answers for that project."
    ),
    (
        "The model's answers varied from try to try, and 3 of its 12 answers broke the required "
        "format and could not be scored. ATLAS's checks are deterministic by design."
    ),
    (
        "This compares finding problems only, not fixing them, on the small set of projects ATLAS "
        "was built on."
    ),
)


def numbers(text: str) -> list[int]:
    return [int(n) for n in re.findall(r"\b\d+\b", text)]


def test_the_plain_items_are_the_given_text():
    assert C.VS_MEANS_PLAIN == GIVEN


def test_every_number_in_the_plain_items_equals_its_source():
    s = scores()
    exp = json.loads((ROOT / "evaluation/expected.json").read_text(encoding="utf-8"))
    a, b = s["atlas"]["totals"], s["baseline"]["totals"]
    base = {c["case_id"]: c for c in s["baseline"]["cases"]}
    atlas = {c["case_id"]: c for c in s["atlas"]["cases"]}
    clean = [cid for cid, c in exp["cases"].items() if not c["expected_violated"]]
    flawed = [cid for cid, c in exp["cases"].items() if c["expected_violated"]]
    f1, f2, f3, f4 = C.VS_MEANS_PLAIN

    def valid(cids: list[str]) -> int:
        return sum(1 for c in cids for t in base[c]["trials"] if t["status"] == "VALID")

    # 1: the two flawed projects hold 9 planted problems; 5 usable answers on them give 23
    # chances, 19 named; 2 false alarms on har_flawed, none in 4 usable clean answers.
    assert numbers(f1) == [9, 5, 23, 19, 2, 4]
    assert len(flawed) == 2 and "two flawed" in f1
    assert sum(len(exp["cases"][c]["expected_violated"]) for c in flawed) == 9
    assert valid(flawed) == 5 and valid(clean) == 4
    assert (
        sum(
            len(exp["cases"][c]["expected_violated"])
            for c in flawed
            for t in base[c]["trials"]
            if t["status"] == "VALID"
        )
        == (b["tp"] + b["fn"])
        == 23
    )
    assert b["tp"] == 19 and b["valid"] == valid(flawed) + valid(clean)
    assert base["har_flawed"]["fp"] == b["fp"] == 2
    assert len(clean) == 2 and "two clean" in f1
    assert all(base[c]["fp"] == 0 for c in clean) and b["clean_false_positives"] == 0
    assert exp["cases"]["har_flawed"]["path"].startswith("benchmarks/real_sensor")
    # 2: all 8 assessable, no false alarms; one gap (window overlap) not assessed; the model
    # did not name it in its 3 usable har_flawed answers.
    assert numbers(f2) == [8, 3]
    assert (a["tp"], a["fn"], a["fp"]) == (8, 0, 0)
    assert atlas["har_flawed"]["coverage_gaps"] == ["split.no_window_overlap"]
    assert sum(len(c["coverage_gaps"]) for c in atlas.values()) == 1
    outcome = A.read_json(BUNDLE / HAR_FLAWED / "original" / "outcome.json")
    window = next(
        x
        for x in outcome["assertions"]
        if x["assertion_id"] == "split.no_window_overlap"
    )
    assert (window["status"], window["reason"]) == ("NOT_ASSESSED", "missing_metadata")
    valid = [t for t in base["har_flawed"]["trials"] if t["status"] == "VALID"]
    assert len(valid) == 3
    assert all("split.no_window_overlap" not in t["violated"] for t in valid)
    assert "missing window metadata" in C.T11_FINDINGS[1]
    assert (
        "did not name it in any of its 3 valid har_flawed trials" in C.T11_FINDINGS[1]
    )
    # 3: answers varied; 3 of 12 broke the format and were not scored; deterministic by design.
    assert numbers(f3) == [3, 12]
    assert (b["invalid_reply"], b["trials_scheduled"]) == (3, 12)
    s01 = [len(t["tp"]) for t in base["s01_faulty"]["trials"] if t["status"] == "VALID"]
    assert s01 == [4, 3]  # varied from try to try
    assert "deterministic by design" in C.T11_FINDINGS[2]
    # 4: detection only, not repair; development cases.
    assert numbers(f4) == []
    assert "does not test repair" in C.T11_FINDINGS[4]
    assert "development cases on which ATLAS's checks were built" in C.T11_FINDINGS[4]


def test_plain_shows_the_plain_items_and_expert_the_reviewed_findings(mode):
    plain = shown(run_page(VS_PAGE))
    expert = shown(run_page(VS_PAGE, expert=True))
    for item in C.VS_MEANS_PLAIN:
        assert story.code_html(item) in plain and story.code_html(item) not in expert
    for finding in C.T11_FINDINGS:
        assert (
            story.code_html(finding) in expert and story.code_html(finding) not in plain
        )
    f = VS.figures(
        scores(),
        json.loads((RESULTS / "suite.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "evaluation/expected.json").read_text(encoding="utf-8")),
    )
    for caveat in VS.caveats(f):
        assert H.esc(caveat) in plain and H.esc(caveat) in expert


# == C1 / C2 ======================================================================================
def overview(case: str | None = None, *, expert: bool = False) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    if case is not None:
        at.session_state[story.CASE] = case
    at.session_state[story.EXPERT] = expert
    at.run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("show_all", [False, True])
@pytest.mark.parametrize("case", ["live6", "harflawed", "harclean"])
def test_the_tamper_demo_is_a_collapsed_expander_after_step_5(mode, case, show_all):
    """After step 5 ("Show all steps"), or directly after the stepper."""
    at = overview(case)
    if show_all:
        at.session_state[story.SHOW_ALL] = True
        at.run()
    labels = [e.label for e in at.expander]
    assert labels[-1] == story.md(C.TAMPER_HEAD)
    if show_all:
        steps = [i for i, label in enumerate(labels) if label.startswith("**5 ·")]
        assert steps and steps[-1] == len(labels) - 2  # directly after step 5
    else:
        assert labels[-2] == C.SHOW_MORE  # the stepper's last element
    assert C.TAMPER_HEAD == (
        "Try tampering: change one byte in a copy and watch the check catch it"
    )
    tamper = at.expander[-1]
    assert tamper.proto.expanded is False
    # Behaviour unchanged: the button inside runs the real check.
    run = next(c.run for c in C.CASES if c.key == case)
    at.button(key=f"tamper-go-{H.run_hash(run)}").click().run()
    assert story.md(C.TAMPER_STATEMENT) in shown(at)


def flat(node) -> list:
    """The page's elements in document order (AppTest's tree)."""
    out = []
    for child in getattr(node, "children", {}).values():
        if getattr(child, "children", None):
            out += flat(child)
        else:
            out.append(child)
    return out


def test_the_expert_switch_is_beside_the_overview_title_and_only_once(mode):
    at = overview()
    # The switch once; plain view adds the stepper's "Show all steps" after the verdict bar.
    assert [t.label for t in at.toggle] == [C.EXPERT_TOGGLE, C.SHOW_ALL_STEPS]
    order = flat(at.main)
    kinds = [type(e).__name__ for e in order]
    title = kinds.index("Title")
    toggle = kinds.index("Toggle")
    first_button = kinds.index("Button")  # the first case card
    assert order[title].value == C.APP_NAME
    assert title < toggle < first_button  # in the header, before the tagline and cards
    assert all(type(e).__name__ != "Title" for e in order[title + 1 : toggle])
    # The comparison and limits pages: the same switch, after their title.
    for path in (VS_PAGE, LIM_PAGE):
        kinds = [type(e).__name__ for e in flat(run_page(path).main)]
        assert kinds.index("Title") < kinds.index("Toggle") == kinds.index("Title") + 1


def test_no_switch_when_the_selected_case_fails_verification(
    mode, tmp_path, monkeypatch
):
    root = tmp_path / "bundle"
    shutil.copytree(BUNDLE, root)
    target = root / LIVE6 / "original" / "outcome.json"
    target.write_bytes(target.read_bytes().replace(b'"FAIL"', b'"PASS"', 1))
    monkeypatch.setattr(story, "BUNDLE_ROOT", root)
    at = overview()
    assert not at.toggle
    assert C.REPORT_BUTTON not in [b.proto.label for b in at.get("download_button")]
    assert ":red-badge[EVIDENCE CHANGED]" in shown(at)


# == D: the audit report ==========================================================================
def build(
    label: str = LIVE6, path: Path | None = None, *, clock=CLOCK, commit="c" * 40
):
    run_dir = path or BUNDLE / label
    run = R.RecordedRun(run_dir, label, R.AGENT)
    case = next((c for c in C.CASES if c.run == label), None)
    return RP.build(
        run,
        subject=case.key if case else run_dir.name,
        subject_title=case.title if case else None,
        citation=story.report_citation(run),
        now=lambda: clock,
        commit=commit,
    )


def test_the_report_file_name_and_contents():
    out = build()
    assert out.file_name == "atlas-audit-live6-VIOLATION_FOUND.html"
    assert build(HAR_CLEAN).file_name == "atlas-audit-harclean-NO_VIOLATION_FOUND.html"
    assert build(HAR_FLAWED).file_name == "atlas-audit-harflawed-VIOLATION_FOUND.html"
    html = out.html
    e = H.esc
    for text in (
        C.REPORT_TITLE,
        C.TAGLINE,
        "The activity classifier works on people absent from training.",
        A.CAVEAT,
        "VIOLATION_FOUND",
        "NO_VIOLATION_FOUND",
        C.REPORT_INTEGRITY.format(v=49, t=49),
        "49 of 49 recorded items verified when this report was generated.",
        C.WHY_TEXT,
        C.WHY_URL,
        "policy policy-v1.3",
        "generated 2026-10-20T12:00:00Z (UTC)",
        C.REPORT_COMMIT.format(commit="c" * 40),
        "2 typed approvals; the original and 1 revision ran in the isolated Docker runner",
    ):
        assert e(text) in html, text
    descriptions = H.load_descriptions()
    report = A.read_json(BUNDLE / LIVE6 / "agent_report.json")
    checks = R.verify(BUNDLE / LIVE6, report)
    hud = H.build(BUNDLE / LIVE6, report, checks, LIVE6, bundled=True)
    for row in hud.matrix:
        assert e(row.assertion_id) in html and e(descriptions[row.assertion_id]) in html
    for c in checks:
        if c.item.endswith("outcome.json") and ":" not in c.item:
            assert c.recorded in html
    approved = [
        ev["candidate_hash"]
        for ev in A.read_log(BUNDLE / LIVE6)
        if ev.get("event") == "approval" and ev.get("decision") == "approved"
    ]
    assert approved and all(h in html for h in approved)
    assert e(C.HAR_CITATION) not in html
    assert e(C.HAR_CITATION) in build(HAR_FLAWED).html
    assert e("[ATLAS-authored flawed variant") in build(HAR_FLAWED).html
    assert e(C.SCRIPT_ONLY) in build(HAR_FLAWED).html


def test_the_report_is_self_contained_with_a_print_style():
    html = build().html
    for absent in (
        "<script",
        "<link",
        "<img",
        "<iframe",
        "src=",
        "href=",
        "url(",
        "@import",
    ):
        assert absent not in html.lower(), absent
    assert html.startswith("<!DOCTYPE html>") and "@media print" in html
    assert "@page" in html and "size: portrait" in html
    assert html.count("<style>") == 1


def test_the_report_holds_no_model_written_text():
    html = build().html
    report = A.read_json(BUNDLE / LIVE6 / "agent_report.json")
    texts = [t["text"] for t in report["model_text"]]
    assert texts
    for t in texts:
        for piece in (t[:40], t[-40:]):
            assert H.esc(piece) not in html and piece not in html
    for reply in sorted((BUNDLE / LIVE6 / "replies").glob("*.txt")):
        raw = reply.read_text(encoding="utf-8")
        assert raw[:60] not in html and H.esc(raw[:60]) not in html
    for diff in sorted((BUNDLE / LIVE6 / "proposals").glob("*.diff")):
        for line in diff.read_text(encoding="utf-8").splitlines():
            if line.startswith(("+", "-")) and len(line.strip()) > 20:
                assert H.esc(line[1:].strip()) not in html, line
    assert H.esc(C.REPORT_MODEL_TEXT_NOTE) in html


def test_the_report_is_deterministic_apart_from_the_clock():
    a, b = build(), build()
    assert a.html.encode("utf-8") == b.html.encode("utf-8")
    later = build(clock=datetime(2026, 10, 21, 8, 30, tzinfo=UTC))
    assert later.html != a.html
    stamp = H.esc("2026-10-21T08:30:00Z"), H.esc("2026-10-20T12:00:00Z")
    assert later.html.replace(*stamp) == a.html


HOSTILE = "<script>alert('x')</script>&\"'<b>"


def test_every_value_is_escaped(tmp_path):
    run_dir = tmp_path / "live6" / "agent-s01_faulty-877f8245a8a2"
    shutil.copytree(BUNDLE / LIVE6, run_dir)
    p = run_dir / "agent_report.json"
    report = json.loads(p.read_text(encoding="utf-8"))
    report["model_id"] = HOSTILE  # not a hashed file: verification still passes
    p.write_text(json.dumps(report), encoding="utf-8")
    assert R.intact(R.verify(run_dir, report))
    html = build(LIVE6, run_dir).html
    assert HOSTILE not in html and "<script" not in html and "<b>" not in html
    assert H.esc(HOSTILE) in html


def test_no_report_without_an_intact_verification(tmp_path):
    run_dir = tmp_path / "run"
    shutil.copytree(BUNDLE / LIVE6, run_dir)
    target = run_dir / "original" / "outcome.json"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(RP.NotIntact) as changed:
        build(LIVE6, run_dir)
    assert not R.intact(changed.value.checks)
    (run_dir / "agent_report.json").unlink()
    with pytest.raises(RP.NotIntact) as missing:
        RP.build(R.RecordedRun(run_dir, LIVE6, R.AGENT), subject="x")
    assert [c.status for c in missing.value.checks] == ["missing"]


def test_the_report_works_hosted_and_executes_nothing(monkeypatch):
    monkeypatch.setenv("ATLAS_HOSTED", "1")

    def tripwire(*a, **k):
        raise AssertionError("the report started a process or opened a socket")

    for name in ("Popen", "run", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, tripwire)
    monkeypatch.setattr(os, "system", tripwire)
    monkeypatch.setattr(socket.socket, "connect", tripwire)
    monkeypatch.setattr(hosted, "refuse_if_hosted", tripwire)
    out = build(commit=None)  # also reads the git metadata, as files only
    assert out.file_name.endswith(".html")


def test_the_commit_is_read_from_git_metadata_or_left_out(tmp_path):
    commit = RP.atlas_commit()
    assert commit is None or re.fullmatch(r"[0-9a-f]{40}", commit)
    assert RP.atlas_commit(tmp_path) is None
    html = build(commit="").html
    assert "ATLAS commit" not in html


@pytest.mark.parametrize("case", ["live6", "harflawed", "harclean"])
def test_the_overview_offers_the_download_in_plain_and_expert(mode, case):
    for expert in (False, True):
        at = overview(case, expert=expert)
        labels = [b.proto.label for b in at.get("download_button")]
        # Expert view also shows the run's existing export downloads (Trust and export).
        assert labels.count(C.REPORT_BUTTON) == 1, labels


def test_a_verified_finished_run_offers_the_download(tmp_path, monkeypatch, mode):
    run_dir = tmp_path / "runs" / "agent-s01_faulty-877f8245a8a2"
    shutil.copytree(BUNDLE / LIVE6, run_dir)

    def page(run_dir: str):
        from pathlib import Path

        from atlas.ui import artifacts as A
        from atlas.ui import results as RS

        report = A.read_json(Path(run_dir) / "agent_report.json")
        RS.finished_run(Path(run_dir), report, RS.AGENT, decisions=[])

    at = AppTest.from_function(page, args=(str(run_dir),), default_timeout=60)
    at.run()
    assert not at.exception
    labels = [b.proto.label for b in at.get("download_button")]
    assert labels.count(C.REPORT_BUTTON) == 1, labels
    # And none after a failed verification.
    target = run_dir / "original" / "outcome.json"
    target.write_bytes(target.read_bytes() + b" ")
    at = AppTest.from_function(page, args=(str(run_dir),), default_timeout=60)
    at.run()
    assert not at.exception
    assert C.REPORT_BUTTON not in [b.proto.label for b in at.get("download_button")]


# == E: colour contrast ===========================================================================
def _lum(hex_: str) -> float:
    h = hex_.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


THEME = tomllib.loads((ROOT / ".streamlit/config.toml").read_text(encoding="utf-8"))[
    "theme"
]
SURFACES = (THEME["backgroundColor"], THEME["secondaryBackgroundColor"])


def test_every_text_token_meets_4_5_to_1_on_both_surfaces():
    tokens = {
        k: v
        for k, v in THEME.items()
        if isinstance(v, str)
        and v.startswith("#")
        and (
            k.endswith("TextColor") or k in ("textColor", "linkColor", "codeTextColor")
        )
    }
    assert len(tokens) >= 9
    for name, value in tokens.items():
        for surface in SURFACES:
            assert contrast(value, surface) >= 4.5, (name, value, surface)
    # The HUD's own text colours (the CSS colour declarations of the UI modules).
    css_text = set()
    for module in ("hud.py", "views.py", "story.py", "versus.py", "limits.py"):
        src = (ROOT / "src" / "atlas" / "ui" / module).read_text(encoding="utf-8")
        css_text |= {
            m.upper()
            for m in re.findall(r"(?<![-\w])color\s*:\s*(#[0-9A-Fa-f]{6})", src)
        }
    dark_ink = "#0A0F14"  # text on light fills only (the accent, badges, bars)
    for value in css_text - {dark_ink}:
        for surface in SURFACES:
            assert contrast(value, surface) >= 4.5, (value, surface)
    for fill in ("#67E8F9", "#94A3B8", "#4ADE80", "#FBBF24"):
        assert contrast(dark_ink, fill) >= 4.5, fill


def test_badge_text_meets_4_5_to_1_on_its_badge_background():
    for c in ("red", "green", "orange", "violet", "gray", "blue"):
        assert contrast(THEME[f"{c}TextColor"], THEME[f"{c}BackgroundColor"]) >= 4.5, c


def test_chart_marks_and_the_accent_meet_3_to_1():
    for mark in (VS.ACCENT, VS.NEUTRAL, THEME["primaryColor"], "#F87171", "#4ADE80"):
        for surface in SURFACES:
            assert contrast(mark, surface) >= 3.0, (mark, surface)


def test_the_report_s_light_palette_meets_4_5_to_1():
    found = {m.lower() for m in re.findall(r"color:\s*(#[0-9a-fA-F]{6})", RP.CSS)}
    assert found
    for value in found:
        for surface in ("#ffffff", "#f3f4f6"):
            assert contrast(value, surface) >= 4.5, (value, surface)


def test_the_new_modules_carry_no_inline_sentence():
    from test_ui_story import _literals

    assert _literals(ROOT / "src" / "atlas" / "ui" / "report.py") == []
