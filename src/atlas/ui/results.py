"""The finished-run cards (2. Analysis to 6. Trust and export), shared by a run started on this
page and a recorded run opened read-only (`atlas.ui.recorded`). Every value is read from the
run's own files; nothing here executes or decides an outcome.
"""

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from atlas.ui import artifacts as A
from atlas.ui import recorded as R
from atlas.ui import views as V
from atlas.ui.catalogue import BY_NAME

AGENT = "agent"
AUDIT = "audit"


def recorded_page(run: R.RecordedRun) -> None:
    """A recorded run, read-only: integrity first, then the same cards as a finished run."""
    report = (
        A.read_json(run.path / "agent_report.json") if run.kind == R.AGENT else None
    )
    checks = R.verify(run.path, report)
    ok = R.intact(checks)
    finished_utc, _source = R.finished(run, report)
    V.recorded_banner(report, run.label, finished_utc)
    st.title("Does the evaluation support the claim?")
    V.integrity(checks, ok)
    if not ok:
        return  # nothing from changed evidence, and no outcome headline
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
    fixture = BY_NAME.get(run.project)
    finished_run(
        run.path,
        report,
        run.kind,
        decisions=R.logged_decisions(A.read_log(run.path)),
        notes=fixture.notes if fixture else (),
    )


def finished_run(
    run_dir: Path | None,
    report: dict | None,
    mode: str,
    *,
    decisions: list[dict],
    notes: tuple[str, ...] = (),
    compare: tuple | None = None,
    on_restart: Callable[[], None] | None = None,
) -> None:
    """`compare` is (this fixture, the related fixture) for the descriptive protocol
    comparison; `on_restart` is None where nothing may be started (a recorded run)."""
    terminal = report.get("terminal_state") if report else None
    terminal_reason = report.get("terminal_reason") if report else None
    comp = (report or {}).get("comparison") or {}

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
            V.trace(
                A.read_log(run_dir) if run_dir else [],
                report,
                decisions,
                collapsed=terminal not in A.FAILED_STATES,
            )

    # -- 3. Finding ---------------------------------------------------------------------------
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
                V.outcome_headline(
                    code, "headline-original", "Original, trusted evaluator"
                )
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
                st.warning(
                    "Incomplete coverage: " + ", ".join(coverage),
                    icon=":material/warning:",
                )
            with st.expander("Check details: observed values, limitations, evidence"):
                V.assertion_details(outcome, rows)
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

    # -- 4. Revision and 5. Comparison (agent runs) -----------------------------------------
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
        if comp.get("candidates"):
            with st.container(key="card-comparison", border=True):
                st.subheader("5. Comparison")
                V.comparison(report, run_dir)

    # -- 6. Trust and export ----------------------------------------------------------------
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
