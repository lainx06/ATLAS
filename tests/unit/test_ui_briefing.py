"""The deterministic mission briefing (UI design pass phase 2, part C).

Built by a pure function from a run's verified files and the policy's frozen definitions
(evaluation/assertion_definitions.json) only: never model text, a rationale, a proposal's
text, a diff, a complete file or a reply. A run whose evidence changed gets no briefing.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from atlas.ui import artifacts as A
from atlas.ui import hud as H
from atlas.ui import recorded as R

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR_FLAWED = "t09/agent-har_flawed-1e2267f662c0"
HAR_CLEAN = "t09/agent-har_clean-ac63eaecd7a8"
MARKER = "ZQX-BRIEFING-MARKER-7f31c2"

GROUP = (
    "FAIL split.no_group_overlap: No group_id value is in both partitions of a fold."
)
UNIT = "FAIL split.sampling_unit_disjoint: No unit_id value crosses partitions."
REPEATED = (
    "FAIL split.repeated_measures_rule: v1.1: assessed through an explicit route over rows "
    "participating in the declared folds, from the route's own same-fold witnesses; "
    "aggregate group/unit statuses are never inherited."
)
FIT = (
    "FAIL fit.state_dependencies_within_fold_train: For every use event in fold k "
    "(transforms and predictions, on train or eval rows), the dependency rows of the used "
    "state version ⊆ train(k)."
)
EXPECTED = {
    LIVE6: [
        "Evidence intact: 46 of 46 recorded hashes verified now.",
        (
            "Original outcome: VIOLATION_FOUND. Required checks: 4 FAIL, 0 NOT_ASSESSED, "
            "0 ERROR (of 9)."
        ),
        GROUP,
        UNIT,
        REPEATED,
        FIT,
        "Revision candidates/c1, executed and verified: NO_VIOLATION_FOUND; 4 FAIL → PASS.",
        "Balanced accuracy (pooled), descriptive only: original 0.6812, candidate 0.6750.",
        A.CAVEAT,
    ],
    HAR_FLAWED: [
        "Evidence intact: 20 of 20 recorded hashes verified now.",
        (
            "Original outcome: VIOLATION_FOUND. Required checks: 4 FAIL, 1 NOT_ASSESSED, "
            "0 ERROR (of 11)."
        ),
        GROUP,
        UNIT,
        REPEATED,
        FIT,
        "Balanced accuracy (pooled), descriptive only: original 0.9063.",
        A.CAVEAT,
    ],
    HAR_CLEAN: [
        "Evidence intact: 20 of 20 recorded hashes verified now.",
        (
            "Original outcome: NO_VIOLATION_FOUND. Required checks: 0 FAIL, "
            "0 NOT_ASSESSED, 0 ERROR (of 10)."
        ),
        "Balanced accuracy (pooled), descriptive only: original 0.8746.",
        A.CAVEAT,
    ],
}


def lines_for(run_dir: Path):
    report = A.read_json(run_dir / "agent_report.json")
    checks = R.verify(run_dir, report)
    return H.briefing_lines(run_dir, report, checks, H.load_definitions())


@pytest.mark.parametrize("label", list(EXPECTED))
def test_the_briefing_text_is_exact(label):
    lines = lines_for(BUNDLE / label)
    assert H.briefing_text(lines) == EXPECTED[label]
    html = H.briefing(lines, H.Ids(H.run_hash(label)))
    for line in lines:
        if line.kind == "fail":
            aid, _, words = line.text[5:].partition(": ")
            assert H.esc(aid) in html and H.esc(words) in html
        else:
            assert H.esc(line.text) in html


@pytest.mark.parametrize("label", list(EXPECTED))
def test_every_number_in_the_briefing_is_the_files(label):
    d = BUNDLE / label
    report = A.read_json(d / "agent_report.json")
    checks = R.verify(d, report)
    hashes = [c for c in checks if ":" not in c.item]
    assert all(c.ok and c.recorded == c.recomputed for c in hashes)
    text = H.briefing_text(lines_for(d))
    assert (
        text[0]
        == f"Evidence intact: {len(hashes)} of {len(hashes)} recorded hashes verified now."
    )
    outcome = json.loads((d / "original/outcome.json").read_text(encoding="utf-8"))
    statuses = [a["status"] for a in outcome["assertions"]]
    assert text[1] == (
        f"Original outcome: {outcome['outcome']}. Required checks: "
        f"{statuses.count('FAIL')} FAIL, {statuses.count('NOT_ASSESSED')} NOT_ASSESSED, "
        f"{statuses.count('ERROR')} ERROR (of {len(statuses)})."
    )
    defs = json.loads(
        (ROOT / "evaluation/assertion_definitions.json").read_text(encoding="utf-8")
    )["definitions"]
    fails = [a["assertion_id"] for a in outcome["assertions"] if a["status"] == "FAIL"]
    shown = [t for t in text if t.startswith("FAIL ")]
    assert [t[5:].split(": ", 1)[0] for t in shown] == fails[: H.BRIEF_FAILS]
    for t in shown:
        aid, words = t[5:].split(": ", 1)
        plain = defs[aid].replace("`", "").replace("*", "")
        assert plain.startswith(
            words.rstrip(".")
        )  # the definition's own first sentence
    assert text[-1] == A.CAVEAT


def test_more_than_four_failing_checks_end_with_the_count():
    lines = []
    statuses = [(f"a.{i}", "FAIL") for i in range(7)]
    outcome = {"outcome": "VIOLATION_FOUND", "assertions": [
        {"assertion_id": aid, "status": s} for aid, s in statuses
    ]}  # fmt: skip
    checks = [R.Check("outcome.json", "x", "x", "matches")]
    original = H._json
    try:
        H._json = lambda run_dir, rel, verified: (
            outcome if rel == "outcome.json" else None
        )
        lines = H.briefing_lines(Path("."), None, checks, {"a.0": "Zero is defined."})
    finally:
        H._json = original
    text = H.briefing_text(lines)
    assert text[2] == "FAIL a.0: Zero is defined."
    assert text[3] == "FAIL a.1: definition not recorded."
    assert [t for t in text if t.startswith("FAIL ")] == [
        "FAIL a.0: Zero is defined.",
        "FAIL a.1: definition not recorded.",
        "FAIL a.2: definition not recorded.",
        "FAIL a.3: definition not recorded.",
    ]
    assert "and 3 more" in text


def test_changed_evidence_gets_no_briefing(tmp_path):
    copy = tmp_path / "live6"
    shutil.copytree(BUNDLE / LIVE6, copy)
    target = copy / "candidates/c1/outcome.json"
    data = bytearray(target.read_bytes())
    i = next(i for i, b in enumerate(data) if chr(b).isdigit())
    data[i] = ord(str((int(chr(data[i])) + 1) % 10))
    target.write_bytes(bytes(data))
    assert lines_for(copy) is None


def _seed(copy: Path) -> None:
    """Put MARKER into every model-written place of a live6 copy and re-record the hashes of
    the files it changes, so the copy still verifies intact."""
    report = json.loads((copy / "agent_report.json").read_text(encoding="utf-8"))
    for t in report.get("model_text") or []:
        t["text"] = f"{MARKER} {t['text']}"
    for p in report.get("proposals") or []:
        p["detail"] = f"{MARKER} detail"
        p["rationale"] = f"{MARKER} rationale"
        for key, sha in (
            ("diff_path", "diff_sha256"),
            ("new_source_path", "new_source_sha256"),
        ):
            if p.get(key):
                f = copy / p[key]
                f.write_text(f.read_text(encoding="utf-8") + f"\n# {MARKER}\n", "utf-8")
                p[sha] = hashlib.sha256(f.read_bytes()).hexdigest()
    for r in report.get("replies") or []:
        f = copy / r["path"]
        f.write_text(f"{MARKER} " + f.read_text(encoding="utf-8"), "utf-8")
        r["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
    report["summary"] = MARKER
    (copy / "agent_report.json").write_text(json.dumps(report), encoding="utf-8")


def test_nothing_model_written_ever_reaches_the_briefing(tmp_path):
    copy = tmp_path / "live6"
    shutil.copytree(BUNDLE / LIVE6, copy)
    _seed(copy)
    report = A.read_json(copy / "agent_report.json")
    checks = R.verify(copy, report)
    assert R.intact(checks)  # the seeded copy still verifies, so a briefing is built
    replies = [c for c in checks if c.item.startswith("replies/")]
    assert replies and all(c.ok for c in replies)
    assert any(MARKER in (copy / c.item).read_text("utf-8") for c in replies)
    lines = H.briefing_lines(copy, report, checks, H.load_definitions())
    assert H.briefing_text(lines) == EXPECTED[LIVE6]
    html = H.briefing(lines, H.Ids(H.run_hash(LIVE6)))
    assert MARKER not in html and MARKER not in "".join(x.source for x in lines)


def test_definitions_are_the_frozen_file():
    defs = H.load_definitions()
    data = json.loads(
        (ROOT / "evaluation/assertion_definitions.json").read_text(encoding="utf-8")
    )
    assert defs == data["definitions"]
    assert H.plain_definition(defs["split.no_group_overlap"]) == (
        "No group_id value is in both partitions of a fold."
    )
    assert H.load_definitions(ROOT / "no-such-file.json") == {}


# -- on the page -------------------------------------------------------------------------------
def recorded_page(monkeypatch, root: Path, label: str):
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("ATLAS_HOSTED", raising=False)
    monkeypatch.setenv(R.RECORDED_ENV, str(root))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["view"] = "recorded"
    at.session_state["recorded_run"] = label
    at.run()
    assert not at.exception
    return at


def test_the_briefing_comes_first_on_a_recorded_page(monkeypatch, tmp_path):
    shutil.copytree(BUNDLE / LIVE6, tmp_path / LIVE6)
    at = recorded_page(monkeypatch, tmp_path, LIVE6)
    blocks = [str(m.value) for m in at.markdown if 'class="hud' in str(m.value)]
    assert "hud-brief" in blocks[0] and "hud-hero" in blocks[1]
    for line in EXPECTED[LIVE6][:2] + EXPECTED[LIVE6][6:]:
        assert H.esc(line) in blocks[0]


def test_a_tampered_copy_shows_the_evidence_changed_panel_and_no_briefing(
    monkeypatch, tmp_path
):
    copy = tmp_path / LIVE6
    shutil.copytree(BUNDLE / LIVE6, copy)
    target = copy / "candidates/c1/outcome.json"
    target.write_bytes(target.read_bytes().replace(b"PASS", b"PAS5", 1))
    at = recorded_page(monkeypatch, tmp_path, LIVE6)
    markup = "\n".join(str(m.value) for m in at.markdown)
    assert "hud-brief" not in markup and "Evidence intact" not in markup
    assert ":red-badge[EVIDENCE CHANGED]" in markup
    assert "evidence changed since recording" in markup
