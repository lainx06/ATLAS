"""The finished-run cards (2. Analysis to 6. Trust and export), shared by a run started on this
page, the hosted live session and a recorded run opened read-only (`atlas.ui.recorded`). Every
value is read from the run's own files; nothing here executes or decides an outcome.

The cards render into one clearable placeholder (T-12 fix pass 2). If rendering raises, the
placeholder is cleared, so no headline or partial result remains, and one fixed error is shown
instead; the event is logged by a fixed code only. The saved run record is never touched. A
recorded run's HUD (`atlas.ui.hud`: the hero, the leak map, the fit-scope flow, the check
matrix) renders inside the same placeholder, so a failure clears it too.

One verification gate (release review 1, F1): every page that shows a run's outcome, briefing,
HUD, check table, revision, comparison, metric or export passes `gate` first, with the run
whose files it will read. When the recomputed hashes and outcomes are not all intact, `gate`
draws only the evidence-changed panel (the integrity ring and the table of differing items)
and the page returns without calling any result renderer. `finished_run` calls `gate` again
itself, so a caller that skipped it still shows nothing but that panel.

The audit report verifies the run once more, from the bytes it reads (`atlas.ui.report`;
release review 2, F1). When evidence changed after the gate, the report raises `NotIntact`;
`case_page` and `finished_run` then clear what they drew, draw only the evidence-changed panel
and rerun the app once (`_evidence_changed`).
"""

import logging
from collections.abc import Callable
from pathlib import Path

import streamlit as st

from atlas.ui import artifacts as A
from atlas.ui import hud as H
from atlas.ui import recorded as R
from atlas.ui import report as RP
from atlas.ui import views as V
from atlas.ui.catalogue import BY_NAME

AGENT = "agent"
AUDIT = "audit"
RENDER_FAILED = (
    "The results could not be displayed. The saved run record is unchanged; open it in the "
    "recorded-run viewer."
)
RENDER_FAILED_EVENT = "results_render_failed"
HUD_PLAYED = "hud_played"  # session key: the run IDs whose first-load motion has played
# Session key: the run whose report boundary last found changed evidence and reran the app
# (`_evidence_changed`); a second failure in a row for the same run draws the panel without
# another rerun. A report built successfully clears it (`story.report_button`).
REPORT_RERUN = "report_rerun"
_log = logging.getLogger(__name__)


def recorded_page(
    run: R.RecordedRun, *, bundled: bool = False, notes: tuple[str, ...] = ()
) -> None:
    """A recorded run, read-only: integrity first, then the HUD and the same cards as a
    finished run. `bundled`: the run is in the hosted demo bundle (the ring's caption says so);
    `notes` go into the banner (the hosted replay disclosure and dataset citation).

    The first-load motion plays once per run per session: the run's ID is remembered in the
    session, and every later rerun renders the final state."""
    report = (
        A.read_json(run.path / "agent_report.json") if run.kind == R.AGENT else None
    )
    finished_utc, _source = R.finished(run, report)
    played_runs = st.session_state.setdefault(HUD_PLAYED, set())
    played = run.label in played_runs
    with st.container(key="hud-page"):
        if not played:
            st.html(H.once_css(played))
        V.recorded_banner(report, run.label, finished_utc, notes)
        st.title("Does the evaluation support the claim?")
        checks = gate(
            run.path,
            report,
            run.kind,
            H.Ids(H.run_hash(run.label)),
            played=played,
            phrase=_ring_phrase(bundled),
        )
        if checks is None:
            played_runs.add(run.label)
            return
        hud = (
            H.build(run.path, report, checks, run.label, bundled=bundled)
            if run.kind == R.AGENT
            else None
        )
        if hud is None:
            V.integrity(checks, True)
        fixture = BY_NAME.get(run.project)
        finished_run(
            run.path,
            report,
            run.kind,
            decisions=R.logged_decisions(A.read_log(run.path)),
            notes=fixture.notes if fixture else (),
            hud=hud,
            played=played,
            preamble=lambda: _recorded_preamble(run, checks, hud is not None),
            briefing=briefing(run.path, report, checks, run.label),
        )
    played_runs.add(run.label)


def case_page(
    run: R.RecordedRun,
    *,
    bundled: bool,
    notes: tuple[str, ...] = (),
    plain_notes: tuple[str, ...] = (),
) -> None:
    """A bundled case on the Overview & Cases page (story layout, `atlas.ui.story`): the
    banner, then the one verification gate, then the verdict bar and the five steps. On a
    failed verification only the evidence-changed panel is drawn and nothing else of the
    case: no verdict bar, no step, no outcome. Motion plays once per case per session."""
    from atlas.ui import story

    report = (
        A.read_json(run.path / "agent_report.json") if run.kind == R.AGENT else None
    )
    finished_utc, _source = R.finished(run, report)
    played_runs = st.session_state.setdefault(HUD_PLAYED, set())
    played = run.label in played_runs
    with st.container(key="hud-page"):
        if not played:
            st.html(H.once_css(played))
        story.banner(report, run.label, finished_utc, notes, plain_notes)
        checks = gate(
            run.path,
            report,
            run.kind,
            H.Ids(H.run_hash(run.label)),
            played=played,
            phrase=_ring_phrase(bundled),
        )
        if checks is None:
            played_runs.add(run.label)
            return
        slot = st.empty()
        try:
            with slot.container():
                story.case(run, report, checks, bundled=bundled, played=played)
        except RP.NotIntact as changed:
            _evidence_changed(
                slot,
                changed.checks,
                H.Ids(H.run_hash(run.label)),
                key=run.label,
                played=played,
                phrase=_ring_phrase(bundled),
            )
        except Exception:  # noqa: BLE001 - never a partial result; the record is unchanged
            slot.empty()
            _log.error(RENDER_FAILED_EVENT)
            st.error(RENDER_FAILED, icon=":material/error:")
    played_runs.add(run.label)


def finished_verified(
    run_dir: Path | None, report: dict | None, mode: str, *, run_id: str, **kwargs
) -> None:
    """A run that finished on this page (a local run, or a hosted live session): every hash
    it recorded is recomputed first (`gate`), as for a recorded run. When intact, the HUD
    (hero, evidence, track) and the integrity record lead its cards, with first-load motion
    once per run per session; when not, only the evidence-changed panel is drawn: no outcome,
    no briefing, no HUD and no card."""
    played_runs = st.session_state.setdefault(HUD_PLAYED, set())
    played = run_id in played_runs
    checks = gate(run_dir, report, mode, H.Ids(H.run_hash(run_id)), played=True)
    if checks is None:
        return
    hud = (
        H.build(run_dir, report, checks, run_id)
        if checks and mode == AGENT and report is not None
        else None
    )
    if not played and hud is not None:
        st.html(H.once_css(played))
    finished_run(
        run_dir,
        report,
        mode,
        hud=hud,
        played=played,
        preamble=(lambda: V.integrity(checks, True)) if checks else None,
        briefing=briefing(run_dir, report if mode == AGENT else None, checks, run_id)
        if checks
        else None,
        **kwargs,
    )
    played_runs.add(run_id)


def gate(
    run_dir: Path | None,
    report: dict | None,
    mode: str,
    ids: H.Ids,
    *,
    played: bool,
    phrase: str = "recomputed now from the run's files",
) -> list[R.Check] | None:
    """The one verification gate before any result rendering (release review 1, F1).

    Verifies exactly the run whose files the caller will read: every hash it recorded and
    each reported outcome against its outcome.json (`atlas.ui.recorded.verify`, unchanged).
    Intact: returns the checks and draws nothing (an empty list when there is no run folder
    and no report, so nothing will be read). Not intact: draws only the evidence-changed
    panel (the integrity ring and the table of differing items) and returns None; the
    caller then returns without drawing an outcome, briefing, diagram, check table, revision,
    comparison, metric or export. An agent run without its report, or a report without a
    run folder, has nothing its outcomes can be verified against: it fails closed."""
    checks = verification(run_dir, report, mode)
    if R.intact(checks):
        return checks
    _changed_panel(checks, ids, played=played, phrase=phrase)
    return None


def _changed_panel(checks: list[R.Check], ids: H.Ids, *, played: bool, phrase: str):
    """The evidence-changed panel: the integrity ring and the table of differing items."""
    V.integrity(checks, False, ring=H.ring(checks, ids, played=played, phrase=phrase))


def _evidence_changed(
    slot, checks: list[R.Check], ids: H.Ids, *, key: str, played: bool, phrase: str
) -> None:
    """The report boundary found the evidence changed after the page's gate (release review
    2, F1; `report.NotIntact`): everything drawn into `slot` since the gate is cleared and only
    the evidence-changed panel is drawn, from the report boundary's own checks. Then the whole
    app reruns once, so every part of the page (the case cards, the Expert view toggle, an
    integrity line above the slot) is drawn again from a fresh verification; a second failure
    in a row for the same run draws the panel without another rerun."""
    slot.empty()
    with slot.container():
        _changed_panel(checks, ids, played=played, phrase=phrase)
    if st.session_state.pop(REPORT_RERUN, None) != key:
        st.session_state[REPORT_RERUN] = key
        st.rerun(scope="app")


def verification(run_dir: Path | None, report: dict | None, mode: str) -> list[R.Check]:
    """The checks `gate` decides on (see there)."""
    if run_dir is None:
        return [] if report is None else [_MISSING_RUN]
    if mode == AGENT and report is None:
        return [_MISSING_REPORT]
    return R.verify(run_dir, report if mode == AGENT else None)


_MISSING_RUN = R.Check("run folder", None, None, "missing")
_MISSING_REPORT = R.Check("agent_report.json", None, None, "missing")


def briefing(
    run_dir: Path, report: dict | None, checks: list, run_id: str
) -> str | None:
    """The deterministic briefing's markup (`atlas.ui.hud.briefing_lines`: the run's verified
    files and the fixed assertion labels only); None unless the run is intact."""
    lines = H.briefing_lines(run_dir, report, checks, H.load_labels())
    return H.briefing(lines, H.Ids(H.run_hash(run_id))) if lines else None


def _ring_phrase(bundled: bool) -> str:
    return (
        "recomputed now from the bundled files"
        if bundled
        else "recomputed now from the run's files"
    )


def _recorded_preamble(run: R.RecordedRun, checks: list, with_integrity: bool) -> None:
    """Below the HUD: the integrity record (when the HUD shows the ring) and the claim."""
    if with_integrity:
        V.integrity(checks, True)
    with st.container(key="card-claim", border=True):
        st.subheader("1. Claim")
        source = R.claim_source(run)
        claim = None
        if source is not None:
            try:
                claim = R.read_claim(source)
            except Exception as exc:  # noqa: BLE001 - shown, never a result
                st.error(f"Recorded manifest unreadable: {type(exc).__name__}")
        if claim is None:
            st.markdown("No manifest was recorded for this run.")
        else:
            with st.container(key="claim-statement"):
                st.markdown(f"#### {claim.statement}")
            st.caption(
                f"Read-only, from the run's own `{source.relative_to(run.path).as_posix()}`"
                f" (the manifest the run evaluated)."
            )
            with st.expander("Claim fields (read-only, from the recorded manifest)"):
                V.claim_fields(claim)


def finished_run(
    run_dir: Path | None,
    report: dict | None,
    mode: str,
    *,
    decisions: list[dict],
    notes: tuple[str, ...] = (),
    compare: tuple | None = None,
    on_restart: Callable[[], None] | None = None,
    original_title: str = "Original, trusted evaluator",
    hud: H.Hud | None = None,
    played: bool = True,
    preamble: Callable[[], None] | None = None,
    briefing: str | None = None,
) -> None:
    """`compare` is (this fixture, the related fixture) for the descriptive protocol
    comparison; `on_restart` is None where nothing may be started (a recorded run).
    `original_title` labels the original's headline (the hosted page names the recorded
    trusted evaluation, SPEC §13). `hud` (a recorded run's verified HUD values) draws the hero
    and the evidence block first, with first-load motion unless `played`; `preamble` draws
    what sits between them and the cards (the recorded run's integrity record and claim).
    `briefing` (the deterministic briefing's markup, built only for an intact run) comes
    before everything else.

    All or nothing: a rendering failure clears every card drawn so far and shows only the
    fixed RENDER_FAILED error (no exception text). Streamlit's stop and rerun signals are not
    `Exception`s and pass through.

    Defence in depth (release review 1, F1): the run is verified again here (`gate`), so a
    caller that skipped the gate still draws nothing but the evidence-changed panel."""
    guard = gate(
        run_dir,
        report,
        mode,
        hud.ids if hud is not None else H.Ids(H.run_hash(str(run_dir)), "g"),
        played=True,
    )
    if guard is None:
        return
    slot = st.empty()
    try:
        with slot.container():
            _cards(
                run_dir,
                report,
                mode,
                checks=guard,
                decisions=decisions,
                notes=notes,
                compare=compare,
                on_restart=on_restart,
                original_title=original_title,
                hud=hud,
                played=played,
                preamble=preamble,
                briefing=briefing,
            )
    except RP.NotIntact as changed:
        _evidence_changed(
            slot,
            changed.checks,
            hud.ids if hud is not None else H.Ids(H.run_hash(str(run_dir)), "g"),
            key=str(run_dir),
            played=True,
            phrase="recomputed now from the run's files",
        )
    except Exception:  # noqa: BLE001 - never a partial result; the record is unchanged
        slot.empty()
        _log.error(RENDER_FAILED_EVENT)
        st.error(RENDER_FAILED, icon=":material/error:")


def _cards(
    run_dir: Path | None,
    report: dict | None,
    mode: str,
    *,
    checks: list[R.Check],
    decisions: list[dict],
    notes: tuple[str, ...],
    compare: tuple | None,
    on_restart: Callable[[], None] | None,
    original_title: str,
    hud: H.Hud | None,
    played: bool,
    preamble: Callable[[], None] | None,
    briefing: str | None,
) -> None:
    if run_dir is not None and checks:
        # Slice 3: the one-page audit report, from this verified run's files only.
        from atlas.ui import story

        with st.container(key="run-report"):
            story.report_button(
                R.RecordedRun(Path(run_dir), Path(run_dir).name, mode),
                subject=Path(run_dir).name,
            )
    if briefing is not None:
        with st.container(key="hud-briefing"):
            st.markdown(briefing, unsafe_allow_html=True)
    if hud is not None:
        with st.container(key="hud-hero"):
            st.markdown(H.hero(hud, played=played), unsafe_allow_html=True)
        with st.container(key="hud-evidence"):
            st.markdown(H.evidence(hud, played=played), unsafe_allow_html=True)
    if preamble is not None:
        preamble()
    analysis_section(run_dir, report, mode, decisions, on_restart, hud)
    finding_section(run_dir, report, mode, notes, compare, original_title)
    revision_section(run_dir, report, mode)
    comparison_section(run_dir, report, mode)
    trust_section(run_dir, report)


def analysis_section(
    run_dir: Path | None,
    report: dict | None,
    mode: str,
    decisions: list[dict],
    on_restart: Callable[[], None] | None,
    hud: H.Hud | None,
) -> None:
    """2. Analysis: the terminal state, the mission track, the budget gauge, the trace."""
    terminal = report.get("terminal_state") if report else None
    terminal_reason = report.get("terminal_reason") if report else None
    if mode == AUDIT:
        with st.container(key="card-analysis", border=True):
            st.subheader("2. Analysis")
            execution = (A.read_json(run_dir / "report.json") or {}).get(
                "execution"
            ) or {}
            st.markdown(
                "Deterministic audit: no model was called and there is no agent trace. The "
                "trusted, repository-authored fixture pipeline ran once."
            )
            if execution:
                st.caption(
                    f"Runner `{execution.get('runner')}` ({execution.get('capability')}), "
                    f"{execution.get('elapsed_s')} s, return code {execution.get('returncode')}."
                )
            if on_restart is not None:
                st.button("Start a new run", on_click=on_restart, key="restart-audit")

    if mode == AGENT:
        with st.container(key="card-analysis", border=True):
            st.subheader("2. Analysis")
            with st.container(key="terminal"):
                if terminal in A.FAILED_STATES:
                    V.state_panel(
                        "terminal",
                        V.STATE_TONE[terminal],
                        terminal,
                        "Terminal state"
                        + (f". Reason: `{terminal_reason}`" if terminal_reason else ""),
                        A.TERMINAL_ACTIONS[terminal],
                    )
                else:
                    st.markdown(f"Terminal state {V.state_badge(terminal)}")
                    if terminal_reason:
                        st.markdown(f"Reason: `{terminal_reason}`")
            if report is None:
                st.error(
                    "No agent_report.json was written for this run.",
                    icon=":material/error:",
                )
            elif report.get("finalization_failures"):
                st.warning(
                    "Partial report: the full report could not be built "
                    f"({report['finalization_failures']}). It is shown as written.",
                )
            if on_restart is not None and (
                terminal in A.FAILED_STATES or terminal is None
            ):
                st.button("Start a new run", on_click=on_restart, key="restart")
            if report is not None:
                ids = hud.ids if hud is not None else H.Ids(H.run_hash(str(run_dir)))
                with st.container(key="hud-track"):
                    st.markdown(H.track(report, ids), unsafe_allow_html=True)
                with st.container(key="hud-gauge"):
                    st.markdown(H.gauge(report, ids), unsafe_allow_html=True)
            V.trace(
                A.read_log(run_dir) if run_dir else [],
                report,
                decisions,
                collapsed=terminal not in A.FAILED_STATES,
            )


def finding_section(
    run_dir: Path | None,
    report: dict | None,
    mode: str,
    notes: tuple[str, ...],
    compare: tuple | None,
    original_title: str,
) -> None:
    """3. Finding: the original's outcome, its required checks and their details."""
    terminal = report.get("terminal_state") if report else None
    terminal_reason = report.get("terminal_reason") if report else None
    comp = (report or {}).get("comparison") or {}
    with st.container(key="card-finding", border=True):
        st.subheader("3. Finding")
        if mode == AUDIT:
            outcome = A.read_json(run_dir / "outcome.json") if run_dir else None
            audit_report = A.read_json(run_dir / "report.json") if run_dir else None
            code = (outcome or {}).get("outcome")
            if code == "NOT_SUPPORTED":
                V.not_supported((outcome or {}).get("reason"))
            else:
                V.outcome_headline(
                    code, "headline-original", "Deterministic audit outcome"
                )
            rows = [
                {
                    k: a.get(k)
                    for k in ("assertion_id", "status", "reason", "evidence_valid")
                }
                for a in (outcome or {}).get("assertions", [])
            ]
            coverage = (outcome or {}).get("incomplete_coverage") or []
            limitations = (audit_report or {}).get("limitations")
        elif terminal == "NOT_SUPPORTED":
            V.not_supported(terminal_reason)
            outcome, rows, coverage, limitations = None, [], [], None
        else:
            original = comp.get("original") or {}
            outcome = (
                A.read_json(run_dir / "original" / "outcome.json") if run_dir else None
            )
            code = ((report or {}).get("scientific_outcomes") or {}).get("original")
            if not original and code is None:
                st.markdown(
                    "No findings yet: the original was not evaluated in this run."
                )
            else:
                V.outcome_headline(code, "headline-original", original_title)
                if original and not original.get("executed"):
                    st.warning(
                        f"The original was not executed. {comp.get('comparison_basis', '')}",
                        icon=":material/block:",
                    )
            rows = original.get("required_set") or []
            coverage = original.get("incomplete_coverage") or []
            limitations = original.get("limitations")
        if rows:
            with st.container(key="finding-counts"):
                st.markdown(V.counts_line(rows))
            V.required_table(rows, "finding-checks")
            V.next_actions(rows)
            if coverage:
                V.state_panel(
                    "coverage",
                    "amber",
                    "incomplete_coverage",
                    "Required checks without a PASS or FAIL: "
                    + ", ".join(f"`{c}`" for c in coverage)
                    + ".",
                    "the next actions above name what is missing for each reason code."
                    if any(r.get("status") in ("NOT_ASSESSED", "ERROR") for r in rows)
                    else "see the check details for what is missing.",
                )
            with st.expander("Check details: observed values, limitations, evidence"):
                V.assertion_details(
                    outcome,
                    rows,
                    "outcome.json" if mode == AUDIT else "original/outcome.json",
                )
            V.conditional_passes(outcome)
            V.provenance_notes(limitations, notes)
            V.metric_block(outcome, "finding-metric")
            if compare is not None and mode == AGENT and run_dir is not None:
                V.protocol_comparison(run_dir, *compare)
            V.baselines(outcome)
            V.class_support(outcome)
            V.reported_metric(outcome)
        if limitations:
            with st.expander("Limitations of this evaluation"):
                V.bullet_list(limitations, "finding-limitations")


def revision_section(run_dir: Path | None, report: dict | None, mode: str) -> None:
    """4. Revision (agent runs): the proposals, their rationale, the candidates."""
    comp = (report or {}).get("comparison") or {}
    if mode == AGENT and report is not None:
        views = A.proposals(run_dir, report)
        rationale = [
            t
            for t in report.get("model_text") or []
            if t.get("kind") == "patch_rationale"
        ]
        with st.container(key="card-revision", border=True):
            st.subheader("4. Revision")
            line = next(
                (
                    x
                    for x in report.get("limitations") or []
                    if " proposal" in x and "rejected by validation" in x
                ),
                None,
            )
            if line:
                with st.container(key="proposal-summary"):
                    st.markdown(line)
            if not views:
                st.markdown(
                    "No candidate proposed: the model finished without a revision."
                )
            for i, v in enumerate(views, start=1):
                V.proposal(v, i)
                if i <= len(rationale):
                    V.model_text(
                        rationale[i - 1]["text"],
                        rationale[i - 1]["label"],
                        f"model-rationale-{i}",
                    )
            for i, c in enumerate(comp.get("candidates") or [], start=1):
                V.candidate_detail(c, i)


def comparison_section(run_dir: Path | None, report: dict | None, mode: str) -> None:
    """5. Comparison (agent runs with an evaluated candidate)."""
    comp = (report or {}).get("comparison") or {}
    if mode == AGENT and report is not None and comp.get("candidates"):
        with st.container(key="card-comparison", border=True):
            st.subheader("5. Comparison")
            V.comparison(report, run_dir)


def trust_section(run_dir: Path | None, report: dict | None) -> None:
    """6. Trust and export: other model-written text, the cost, limitations, export."""
    with st.container(key="card-trust", border=True):
        st.subheader("6. Trust and export")
        if report is not None:
            for i, t in enumerate(report.get("model_text") or []):
                if t.get("kind") != "patch_rationale":
                    V.model_text(t["text"], t["label"], f"model-text-{i}")
            V.cost(report)
            with st.container(key="run-limitations"):
                st.markdown("**Limitations**")
                V.bullet_list(report.get("limitations"))
        if run_dir is not None:
            V.export(run_dir, report)
        else:
            st.caption("Export is available once a report exists.")
