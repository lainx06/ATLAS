"""Release review 1, F1 (P1): no outcome or result card from unverified evidence, on any page.

Codex's reproductions (runs/release-review/probes/hud_probe.py and followup_probe.py): a copy
of the bundled live run 6 record with (a) one byte of candidates/c1/outcome.json changed, or
(b) the original's outcome.json and the report's original outcome both changed to
NO_VIOLATION_FOUND with the recorded hashes left as they were. Before this fix, the hosted
live view showed EVIDENCE CHANGED and still drew the cards, and (b) drew a green
NO_VIOLATION_FOUND.

Now one gate (`atlas.ui.results.gate`) runs before any result renderer on every entry point:
the hosted live view (the finished session and "The original's findings (recorded)"), the
hosted recorded view, the local recorded view and the local finished run. On a failed
verification only the evidence-changed panel (the ring and the table of differing items) is
drawn, and no entry point calls `finished_run`, the HUD builders, the briefing or the check
tables. `finished_run` repeats the gate itself (defence in depth). Offline: the fixtures of
test_render_failure (no Docker, no provider, no network).
"""

import json
import re
import shutil
from pathlib import Path

import hosted_helpers as Hh
import pytest
from streamlit.testing.v1 import AppTest

# The fixtures are test_render_failure's; test arguments use their names (F811 below).
from test_render_failure import (  # noqa: F401 - pytest fixtures
    APP,
    LOCAL_RUN,
    hosted_page,
    hosted_run,
    local_page,
    local_run,
    shown,
)

from atlas.hosted import bundle, page
from atlas.ui import artifacts as A
from atlas.ui import hud as H
from atlas.ui import recorded as RR
from atlas.ui import results as R
from atlas.ui import views as V

LIVE6 = bundle.LIVE_ORIGINAL_RUN  # live6/agent-s01_faulty-877f8245a8a2
OUTCOME_CODES = re.compile(
    r"(NO_)?VIOLATION(_|&#95;)FOUND|INCONCLUSIVE|NOT(_|&#95;)SUPPORTED"
)
INTEGRITY_COLUMNS = ["result", "item", "recorded", "recomputed now"]
CARDS = (
    "2. Analysis",
    "3. Finding",
    "4. Revision",
    "5. Comparison",
    "6. Trust and export",
)


# -- Codex's two tamperings ------------------------------------------------------------------
def one_byte(run: Path) -> None:
    """hud_probe.py: the last byte of candidates/c1/outcome.json changed."""
    target = run / "candidates" / "c1" / "outcome.json"
    if not target.is_file():  # a hosted session executes no candidate
        target = run / "original" / "outcome.json"
    raw = target.read_bytes()
    target.write_bytes(raw[:-1] + (b" " if raw[-1:] != b" " else b"\n"))


def changed_outcome(run: Path) -> None:
    """hud_probe.py: the original's outcome and the report's original outcome both say
    NO_VIOLATION_FOUND; every recorded hash and comparison.original left unchanged."""
    target = run / "original" / "outcome.json"
    data = target.read_bytes()
    target.write_bytes(data.replace(b'"VIOLATION_FOUND"', b'"NO_VIOLATION_FOUND"', 1))
    path = run / "agent_report.json"
    report = A.read_json(path)
    report["scientific_outcomes"]["original"] = "NO_VIOLATION_FOUND"
    path.write_text(json.dumps(report), encoding="utf-8")


TAMPER = {"one-byte": one_byte, "changed-outcome": changed_outcome}


def tampered_copy(dest: Path, how: str) -> Path:
    shutil.copytree(LOCAL_RUN, dest)
    TAMPER[how](dest)
    assert not RR.intact(RR.verify(dest, A.read_json(dest / "agent_report.json")))
    return dest


# -- what a page drawn from changed evidence may and may not show -----------------------------
@pytest.fixture
def renderers(monkeypatch):
    """Spies on every result renderer an entry point could reach after the gate: none may be
    called on a failed verification (the entry point returns before them)."""
    calls: list[str] = []

    def spy(module, name):
        original = getattr(module, name)

        def wrapper(*args, **kwargs):
            calls.append(name)
            return original(*args, **kwargs)

        monkeypatch.setattr(module, name, wrapper)

    for name in ("finished_run", "briefing"):
        spy(R, name)
    for name in ("build", "briefing_lines", "hero", "evidence", "track", "gauge"):
        spy(H, name)
    for name in (
        "outcome_headline",
        "required_table",
        "not_supported",
        "comparison",
        "protocol_comparison",
        "metric_block",
        "proposal",
        "export",
    ):
        spy(V, name)
    return calls


def assert_only_the_evidence_changed_panel(at: AppTest) -> None:
    assert not at.exception
    text = shown(at)
    assert ":red-badge[EVIDENCE CHANGED]" in text
    assert "evidence changed since recording" in text
    assert "so no outcome is shown" in text
    # The table of differing items is the only table with results.
    tables = [list(t.value.columns) for t in at.table]
    assert INTEGRITY_COLUMNS in tables
    for columns in tables:
        assert not {"assertion", "assertion_id", "status"} & set(columns), columns
    rows = next(t.value for t in at.table if list(t.value.columns) == INTEGRITY_COLUMNS)
    assert len(rows) >= 1 and set(rows["result"]) <= {"changed", "missing", "outside"}
    # No outcome code, briefing, HUD diagram, card, download or success badge.
    non_table = "\n".join(
        str(x.value)
        for kind in ("markdown", "caption", "subheader", "title", "info", "warning")
        for x in getattr(at, kind)
    )
    assert OUTCOME_CODES.search(non_table) is None, OUTCOME_CODES.search(non_table)
    hud = set(re.findall(r'class="hud (hud-[a-z-]+)', non_table))
    assert hud <= {"hud-ring"}, hud  # the ring is the integrity panel's own record
    for card in CARDS:
        assert card not in text, card
    assert A.CAVEAT not in text and "hud-brief" not in non_table
    assert ":green-badge[intact]" not in text
    assert not at.success and not at.get("download_button")


# -- the hosted live view: the finished session (Codex's exact entry, page.py:353) -------------
def hosted_live_of(run: Path) -> AppTest:
    """page.live_view for a session whose run folder is `run` (Codex's harness)."""
    script = run.parent / f"live-{run.name}.py"
    script.write_text(
        "from pathlib import Path\n"
        "from types import SimpleNamespace\n"
        "from atlas.hosted import page\n"
        f"p = Path({str(run)!r})\n"
        "h = page.LiveHandle(p.parent)\n"
        'h.outcome = SimpleNamespace(status="ran", code=None, run_dir=p, route="public")\n'
        "page.live_view(lambda key: None, None, h)\n",
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script), default_timeout=60)
    with Hh.loopback_only():
        at.run()
    return at


@pytest.mark.parametrize("how", list(TAMPER))
def test_the_hosted_live_view_shows_no_result_from_changed_evidence(
    tmp_path, renderers, how
):
    run = tampered_copy(tmp_path / "s" / LOCAL_RUN.name, how)
    at = hosted_live_of(run)
    assert_only_the_evidence_changed_panel(at)
    assert "Route: public demo budget." in shown(at)  # the page around it still renders
    assert renderers == []


def test_the_hosted_live_view_of_an_intact_session_still_shows_its_results(tmp_path):
    """Control: the same harness on an untouched copy draws the outcome and the cards."""
    run = tmp_path / "s" / LOCAL_RUN.name
    shutil.copytree(LOCAL_RUN, run)
    at = hosted_live_of(run)
    assert not at.exception and not at.error
    text = shown(at)
    assert "## :red[VIOLATION_FOUND]" in text and "3. Finding" in text
    assert ":green-badge[intact]" in text


@pytest.mark.parametrize("how", list(TAMPER))
def test_a_completed_hosted_session_whose_files_changed_shows_no_result(
    hosted_run,  # noqa: F811
    renderers,
    how,
):
    """The real session record (mocked provider), changed after it finished."""
    run = hosted_run.outcome.run_dir
    assert RR.intact(RR.verify(run, A.read_json(run / "agent_report.json")))
    TAMPER[how](run)
    assert not RR.intact(RR.verify(run, A.read_json(run / "agent_report.json")))
    at = hosted_page(hosted_run)
    assert_only_the_evidence_changed_panel(at)
    assert renderers == []


# -- the hosted live view: "The original's findings (recorded)" ------------------------------
@pytest.mark.parametrize("how", list(TAMPER))
def test_the_recorded_original_card_shows_no_findings_from_changed_evidence(
    monkeypatch, tmp_path, renderers, how
):
    root = tmp_path / "bundle"
    tampered_copy(root / LIVE6, how)
    monkeypatch.setattr(bundle, "BUNDLE_ROOT", root)
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_HOSTED_RUNS_DIR", str(tmp_path / "hosted-runs"))
    for name in ("NEBIUS_API_KEY", "DATABASE_URL", "JUDGE_ACCESS_CODE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOSTED_LIVE_ENABLED", "false")
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["hosted_view"] = page.LIVE_VIEW
    with Hh.loopback_only():
        at.run()
    assert_only_the_evidence_changed_panel(at)
    assert "The original's findings (recorded)" in shown(at)
    assert not at.button  # no live session can be started on changed evidence
    assert renderers == []


def test_the_finished_session_label_dates_only_an_intact_original(
    monkeypatch, tmp_path
):
    root = tmp_path / "bundle"
    shutil.copytree(LOCAL_RUN, root / LIVE6)
    monkeypatch.setattr(bundle, "BUNDLE_ROOT", root)
    assert "date unknown" not in page._label()
    one_byte(root / LIVE6)
    assert "date unknown" in page._label()


# -- the hosted recorded view (page.py:146) -----------------------------------------------------
@pytest.mark.parametrize("how", list(TAMPER))
def test_the_hosted_recorded_view_shows_no_result_from_changed_evidence(
    tmp_path, renderers, how
):
    run = tampered_copy(tmp_path / LIVE6, how)
    script = tmp_path / "recorded.py"
    script.write_text(
        "from pathlib import Path\n"
        "from atlas.hosted import page\n"
        "from atlas.ui import recorded as RR\n"
        f"run = RR.RecordedRun(Path({str(run)!r}), {LIVE6!r}, RR.AGENT)\n"
        "page.recorded_view(run)\n",
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script), default_timeout=60)
    at.run()
    assert_only_the_evidence_changed_panel(at)
    assert page.REPLAY_DISCLOSURE in shown(at)
    assert renderers == []


# -- the local recorded view (app.py:174) -------------------------------------------------------
@pytest.mark.parametrize("how", list(TAMPER))
def test_the_local_recorded_view_shows_no_result_from_changed_evidence(
    monkeypatch, tmp_path, renderers, how
):
    tampered_copy(tmp_path / LIVE6, how)
    monkeypatch.delenv("ATLAS_HOSTED", raising=False)
    monkeypatch.setenv(RR.RECORDED_ENV, str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["view"] = "recorded"
    at.session_state["recorded_run"] = LIVE6
    at.run()
    assert_only_the_evidence_changed_panel(at)
    assert renderers == []


# -- the local finished run (app.py:444) --------------------------------------------------------
@pytest.mark.parametrize("how", list(TAMPER))
def test_the_local_finished_run_shows_no_result_from_changed_evidence(
    local_run,  # noqa: F811
    renderers,
    how,
):
    TAMPER[how](local_run)
    at = local_page()
    assert_only_the_evidence_changed_panel(at)
    assert "1. Claim" in shown(at)  # the claim comes from the project, not the run
    assert renderers == []


# -- finished_run's own guard (defence in depth) -------------------------------------------------
@pytest.mark.parametrize("how", list(TAMPER))
def test_finished_run_called_without_the_gate_still_draws_only_the_panel(
    tmp_path, renderers, how
):
    run = tampered_copy(tmp_path / "r" / LOCAL_RUN.name, how)
    script = tmp_path / "direct.py"
    script.write_text(
        "from pathlib import Path\n"
        "from atlas.ui import artifacts as A, results as R\n"
        f"p = Path({str(run)!r})\n"
        "R.finished_run(p, A.read_json(p / 'agent_report.json'), R.AGENT, decisions=[])\n",
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script), default_timeout=60)
    at.run()
    assert_only_the_evidence_changed_panel(at)
    assert renderers == ["finished_run"]  # called directly; nothing after it


# -- the gate itself ------------------------------------------------------------------------------
def test_the_gate_fails_closed_without_a_report_or_a_run_folder(tmp_path):
    run = tmp_path / LOCAL_RUN.name
    shutil.copytree(LOCAL_RUN, run)
    report = A.read_json(run / "agent_report.json")
    assert RR.intact(R.verification(run, report, R.AGENT))
    assert R.verification(None, None, R.AGENT) == []  # nothing will be read
    for args in ((run, None, R.AGENT), (None, report, R.AGENT)):
        checks = R.verification(*args)
        assert checks and not RR.intact(checks)


def test_the_related_run_of_a_protocol_comparison_is_verified_first(tmp_path):
    """The local page's descriptive comparison reads a second run: it is gated too."""
    this = tmp_path / LOCAL_RUN.name
    shutil.copytree(LOCAL_RUN, this)
    other = tmp_path / LOCAL_RUN.name.replace("s01_faulty", "s02_clean")
    tampered_copy(other, "changed-outcome")
    script = tmp_path / "compare.py"
    script.write_text(
        "from pathlib import Path\n"
        "from types import SimpleNamespace as N\n"
        "from atlas.ui import views as V\n"
        f"V.protocol_comparison(Path({str(this)!r}), N(name='s01_faulty', label='a'),"
        " N(name='s02_clean', label='b'))\n",
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script), default_timeout=60)
    at.run()
    assert not at.exception
    text = shown(at)
    assert "evidence changed since recording, so it is not compared" in text
    assert not at.table and OUTCOME_CODES.search(text) is None


def test_no_entry_point_reads_results_outside_the_gate():
    """Every entry point that displays a run's results, found by a source search: each one
    passes `gate` before reading (the AppTests above exercise each)."""
    root = Path(__file__).resolve().parents[2]
    callers = {}
    for path in [root / "app.py", *sorted((root / "src" / "atlas").rglob("*.py"))]:
        text = path.read_text(encoding="utf-8")
        for name in ("finished_run(", "finished_verified(", "recorded_page("):
            for m in re.finditer(rf"\b(R|results)\.{re.escape(name)}", text):
                line = text.count("\n", 0, m.start()) + 1
                callers[f"{path.relative_to(root).as_posix()}:{line}"] = name
    assert sorted(callers.values()) == [
        "finished_verified(",
        "finished_verified(",
        "recorded_page(",
        "recorded_page(",
    ], callers
    results = (root / "src/atlas/ui/results.py").read_text(encoding="utf-8")
    for fn in ("def recorded_page(", "def finished_verified(", "def finished_run("):
        body = results.split(fn, 1)[1].split("\ndef ", 1)[0]
        assert "gate(" in body and "return" in body, fn
