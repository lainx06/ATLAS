"""Release review 2, F1: the audit report is built only from bytes verified at the report
boundary (`atlas.ui.report.build`, inside one `atlas.ui.artifacts.snapshot`).

Ported from the review's race probe (runs/release-review-3/report_race_probe.py): the page runs
its real gate, then a hook changes the evidence (one byte, or a forged outcome with the
recorded hashes unchanged) immediately before the real report builder. The builder must
refuse: no report, no download button, the page shows only the evidence-changed panel, and the
integrity sentence is never printed for the changed evidence. Covered for every entry point
that offers the report: the Overview case page (plain and Expert view), the full Overview, and
the finished-run views (local and hosted).

At the builder itself: every file it consumes is read from disk exactly once, and a change
made after its own verification never reaches the HTML.
"""

import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import recorded as R
from atlas.ui import report as RP

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
KINDS = ("one-byte", "forged")
CLOCK = datetime(2026, 10, 22, 12, 0, 0, tzinfo=UTC)
VERIFIED_SENTENCE = (
    "recorded items verified"  # page ("... now") and report ("... generated")
)


def tamper(run_dir: Path, kind: str) -> None:
    """The probe's two changes: one byte of original/outcome.json, or its outcome forged
    together with the report's reported outcome (recorded hashes left unchanged)."""
    p = run_dir / "original" / "outcome.json"
    if kind == "one-byte":
        data = p.read_bytes()
        p.write_bytes(data[:-1] + (b" " if data[-1:] != b" " else b"\n"))
        return
    data = json.loads(p.read_text(encoding="utf-8"))
    data["outcome"] = "NO_VIOLATION_FOUND"
    p.write_text(json.dumps(data), encoding="utf-8")
    report_path = run_dir / "agent_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["scientific_outcomes"]["original"] = "NO_VIOLATION_FOUND"
    report_path.write_text(json.dumps(report), encoding="utf-8")


def shown(at: AppTest) -> str:
    parts = []
    for kind in (
        "markdown",
        "caption",
        "title",
        "subheader",
        "text",
        "warning",
        "error",
    ):
        parts += [str(x.value) for x in getattr(at, kind)]
    parts += [t.value.to_csv() for t in at.table]
    return "\n".join(parts)


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


# The app scripts below run in AppTest's script thread. Each installs the race hook: the first
# call to the real report builder (after the page's gate passed) changes the evidence first;
# `marker` records what the builder did (it never writes a report file).
def case_app(run_dir: str, kind: str, expert: bool, marker: str) -> None:
    from pathlib import Path
    from unittest.mock import patch

    import streamlit as st
    import test_report_race as T

    from atlas.ui import recorded as R
    from atlas.ui import report as RP
    from atlas.ui import results as RS
    from atlas.ui import story

    st.session_state[story.EXPERT] = expert
    root, real = Path(run_dir), RP.build

    def raced(*args, **kwargs):
        if not Path(marker).exists():
            T.tamper(root, kind)
            Path(marker).write_text("changed", encoding="utf-8")
        try:
            built = real(*args, **kwargs)
        except RP.NotIntact:
            Path(marker).write_text("refused", encoding="utf-8")
            raise
        Path(marker).write_text("built", encoding="utf-8")
        return built

    with patch.object(RP, "build", side_effect=raced):
        RS.case_page(R.RecordedRun(root, T.LIVE6, R.AGENT), bundled=True)


def overview_app(bundle: str, kind: str, expert: bool, marker: str) -> None:
    from pathlib import Path
    from unittest.mock import patch

    import streamlit as st
    import test_report_race as T

    from atlas.ui import report as RP
    from atlas.ui import story

    st.session_state[story.EXPERT] = expert
    root, real = Path(bundle), RP.build

    def raced(*args, **kwargs):
        if not Path(marker).exists():
            T.tamper(root / T.LIVE6, kind)
            Path(marker).write_text("changed", encoding="utf-8")
        try:
            built = real(*args, **kwargs)
        except RP.NotIntact:
            Path(marker).write_text("refused", encoding="utf-8")
            raise
        Path(marker).write_text("built", encoding="utf-8")
        return built

    with patch.object(RP, "build", side_effect=raced):
        story.overview(root)


def finished_app(run_dir: str, kind: str, expert: bool, marker: str) -> None:
    from pathlib import Path
    from unittest.mock import patch

    import streamlit as st
    import test_report_race as T

    from atlas.ui import artifacts as A
    from atlas.ui import report as RP
    from atlas.ui import results as RS
    from atlas.ui import story

    st.session_state[story.EXPERT] = expert
    root, real = Path(run_dir), RP.build

    def raced(*args, **kwargs):
        if not Path(marker).exists():
            T.tamper(root, kind)
            Path(marker).write_text("changed", encoding="utf-8")
        try:
            built = real(*args, **kwargs)
        except RP.NotIntact:
            Path(marker).write_text("refused", encoding="utf-8")
            raise
        Path(marker).write_text("built", encoding="utf-8")
        return built

    report = A.read_json(root / "agent_report.json")
    with patch.object(RP, "build", side_effect=raced):
        RS.finished_verified(root, report, RS.AGENT, run_id=root.name, decisions=[])


def assert_only_the_changed_panel(at: AppTest, marker: Path) -> str:
    assert not at.exception, at.exception
    assert marker.read_text(encoding="utf-8") == "refused"
    assert not at.get("download_button"), [
        b.proto.label for b in at.get("download_button")
    ]
    text = shown(at)
    assert C.EVIDENCE_CHANGED_CODE in text
    assert VERIFIED_SENTENCE not in text
    for token in ("hud-verdict", "hud-stepper", "hud-evidence", "NO_VIOLATION_FOUND"):
        assert token not in text, token
    assert not at.metric
    return text


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("expert", [False, True], ids=["plain", "expert"])
def test_a_change_between_the_gate_and_the_report_yields_no_report(
    kind, expert, tmp_path
):
    run_dir = tmp_path / "live6" / "agent-s01_faulty-877f8245a8a2"
    shutil.copytree(BUNDLE / LIVE6, run_dir)
    marker = tmp_path / "marker.txt"
    at = AppTest.from_function(
        case_app, args=(str(run_dir), kind, expert, str(marker)), default_timeout=60
    ).run()
    assert_only_the_changed_panel(at, marker)
    assert not R.intact(R.verify(run_dir, A.read_json(run_dir / "agent_report.json")))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("expert", [False, True], ids=["plain", "expert"])
def test_the_full_overview_redraws_from_a_fresh_verification(kind, expert, tmp_path):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    marker = tmp_path / "marker.txt"
    at = AppTest.from_function(
        overview_app, args=(str(bundle), kind, expert, str(marker)), default_timeout=60
    ).run()
    assert not at.exception, at.exception
    assert marker.read_text(encoding="utf-8") == "refused"
    assert not at.get("download_button")
    text = shown(at)
    assert C.EVIDENCE_CHANGED_CODE in text and VERIFIED_SENTENCE not in text
    assert not at.toggle  # the Expert view switch is not drawn for a changed case
    card = next(  # the selected (live6) case's card, drawn again after the rerun
        str(m.value)
        for m in at.markdown
        if "hud-case-codes" in str(m.value) and "hud-case-on" in str(m.value)
    )
    assert C.CARD_CHANGED in card and "VIOLATION_FOUND" not in card


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("expert", [False, True], ids=["plain", "expert"])
def test_a_finished_run_s_report_refuses_changed_evidence(kind, expert, tmp_path, mode):
    run_dir = tmp_path / "runs" / "agent-s01_faulty-877f8245a8a2"
    shutil.copytree(BUNDLE / LIVE6, run_dir)
    marker = tmp_path / "marker.txt"
    at = AppTest.from_function(
        finished_app, args=(str(run_dir), kind, expert, str(marker)), default_timeout=60
    ).run()
    assert_only_the_changed_panel(at, marker)


def test_without_a_change_the_report_is_offered(tmp_path):
    """The hook's control: the same pages offer the report when nothing changes."""
    run_dir = tmp_path / "live6" / "agent-s01_faulty-877f8245a8a2"
    shutil.copytree(BUNDLE / LIVE6, run_dir)

    def app(run_dir: str) -> None:
        from pathlib import Path

        import test_report_race as T

        from atlas.ui import recorded as R
        from atlas.ui import results as RS

        RS.case_page(R.RecordedRun(Path(run_dir), T.LIVE6, R.AGENT), bundled=True)

    at = AppTest.from_function(app, args=(str(run_dir),), default_timeout=60).run()
    assert not at.exception
    labels = [b.proto.label for b in at.get("download_button")]
    assert labels.count(C.REPORT_BUTTON) == 1


# -- the builder itself ------------------------------------------------------------------------
def _build(run_dir: Path) -> RP.Report:
    return RP.build(
        R.RecordedRun(run_dir, LIVE6, R.AGENT),
        subject="live6",
        now=lambda: CLOCK,
        commit="c" * 40,
    )


def test_the_builder_reads_each_file_it_consumes_exactly_once(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    shutil.copytree(BUNDLE / LIVE6, run_dir)
    inside_run = run_dir.resolve()
    reads: Counter[Path] = Counter()
    real_read_bytes, real_read_text, real_open = Path.read_bytes, Path.read_text, open

    def counted(self):
        reads[Path(self).resolve()] += 1
        return real_read_bytes(self)

    def text_outside_only(self, *a, **k):
        if Path(self).resolve().is_relative_to(inside_run):
            raise AssertionError(f"{self} was read from disk, not from the snapshot")
        return real_read_text(self, *a, **k)

    def open_outside_only(file, *a, **k):
        if isinstance(file, (str, Path)) and Path(file).resolve().is_relative_to(
            inside_run
        ):
            raise AssertionError(f"{file} was opened, not read from the snapshot")
        return real_open(file, *a, **k)

    monkeypatch.setattr(Path, "read_bytes", counted)
    monkeypatch.setattr(Path, "read_text", text_outside_only)
    monkeypatch.setattr("builtins.open", open_outside_only)
    _build(run_dir)
    monkeypatch.undo()
    inside = {p: n for p, n in reads.items() if p.is_relative_to(inside_run)}
    assert inside and all(n == 1 for n in inside.values()), inside
    report = A.read_json(run_dir / "agent_report.json")
    hashed = {
        (run_dir / c.item).resolve()
        for c in R.verify(run_dir, report)
        if ":" not in c.item
    }
    assert hashed <= set(inside)  # every hashed file came from the one read


@pytest.mark.parametrize("kind", KINDS)
def test_a_change_after_the_builder_s_own_verification_never_reaches_the_html(
    kind, tmp_path, monkeypatch
):
    run_dir = tmp_path / "run"
    shutil.copytree(BUNDLE / LIVE6, run_dir)
    clean = _build(run_dir)
    real_verify = R.verify

    def verify_then_change(*args, **kwargs):
        checks = real_verify(*args, **kwargs)
        tamper(run_dir, kind)  # the disk changes; the snapshot does not
        return checks

    monkeypatch.setattr(R, "verify", verify_then_change)
    raced = _build(run_dir)
    assert raced == clean  # the verified bytes, not the changed disk
    assert not R.intact(
        real_verify(run_dir, A.read_json(run_dir / "agent_report.json"))
    )


@pytest.mark.parametrize("kind", KINDS)
def test_a_change_before_the_builder_s_read_refuses_the_report(kind, tmp_path):
    run_dir = tmp_path / "run"
    shutil.copytree(BUNDLE / LIVE6, run_dir)
    tamper(run_dir, kind)
    with pytest.raises(RP.NotIntact) as refused:
        _build(run_dir)
    # The forged outcome agrees with the forged report, but not with the recorded hash.
    assert [c.item for c in refused.value.checks if not c.ok] == [
        "original/outcome.json"
    ]


def test_outside_a_snapshot_the_readers_read_disk(tmp_path):
    p = tmp_path / "f.json"
    p.write_bytes(b'{"a": 1}\r\n')
    assert A.read_json(p) == {"a": 1} and A.is_file(p)
    assert A.read_text(p) == p.read_text(encoding="utf-8")
    with A.snapshot(tmp_path) as snap:
        assert A.read_text(p) == p.read_text(encoding="utf-8")
        p.write_bytes(b'{"a": 2}\n')
        assert A.read_json(p) == {"a": 1}  # the bytes read first
        snap.freeze()
        assert not A.is_file(tmp_path / "other.json")
    assert A.read_json(p) == {"a": 2}
