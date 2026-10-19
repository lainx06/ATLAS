"""Page sections for app.py. Each renders artifact values with the spec's labels (§1, §4).

Styling is Streamlit's theme (`.streamlit/config.toml`) plus the one documented CSS block in
`inject_css`, which targets only `st-key-*` classes (a container's `key` becomes the class
`st-key-<key>`, per `st.container`'s documentation). Status colours always sit next to the
printed code, never instead of it.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from atlas.agent.approval import CONFIRM_CHARS, inert
from atlas.ui import artifacts as A
from atlas.ui.recorded import CHANGED

CSS = """
<style>
/* Cards: white surface on the #FAFAF9 page (UI_SPEC §7). Only st-key-* hooks. */
[class*="st-key-card-"] { background: #FFFFFF; padding: 16px 24px 20px; }
/* Model-written text: tinted panel (#F5F5F4) with its tag (UI_SPEC §1.2, §7). */
[class*="st-key-model-"] { background: #F5F5F4; padding: 12px 16px; border-radius: 6px; }
/* The blocking approval panel: accent outline so it cannot be mistaken for a result. */
.st-key-approval-panel { background: #FFFFFF; outline: 2px solid #1D4ED8;
  outline-offset: -2px; padding: 16px 24px 20px; }
/* Wide diffs and tables scroll inside their own region (UI_SPEC §7 viewports). */
[class*="st-key-scroll-"] { overflow-x: auto; }
/* Hashes in trace and export tables wrap instead of being clipped (never truncated). */
[class*="st-key-trace-"] td, .st-key-export td { word-break: break-all; }
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def _count(value) -> str:
    return "n/a" if value is None else str(value)


def badge(code: str, colors: dict) -> str:
    return f":{colors.get(code, 'gray')}-badge[{code}]"


# -- banner and labels ---------------------------------------------------------------------
def banner(report: dict | None, run_name: str | None, mode: str | None) -> None:
    with st.container(key="banner", border=True):
        if report is not None:
            live = report.get("live") is True
            tag = ":blue-badge[LIVE RUN]" if live else ":gray-badge[NON-LIVE RUN]"
            st.markdown(
                f"{tag} mode `{report.get('mode')}`, live `{report.get('live')}`"
            )
            st.caption(report.get("banner", ""))
        elif mode == "audit":
            st.markdown(":gray-badge[Deterministic audit: no model]")
            st.caption(
                "Audit mode runs the trusted, repository-authored fixture pipeline. No "
                "model is called and no candidate code runs."
            )
        else:
            st.markdown(
                ":gray-badge[NON-LIVE] Agent runs in this build use fixture replies."
            )
            st.caption(
                "No model is called. Live runs need the lead's explicit go-ahead."
            )
        if run_name:
            st.caption(f"Run `{run_name}`")


def recorded_banner(report: dict | None, label: str, finished_utc: str | None) -> None:
    """A recorded run's own LIVE or NON-LIVE label, and that it is not re-executed here."""
    with st.container(key="banner", border=True):
        if report is not None:
            live = report.get("live") is True
            tag = ":blue-badge[LIVE RUN]" if live else ":gray-badge[NON-LIVE RUN]"
            st.markdown(
                f"{tag} mode `{report.get('mode')}`, live `{report.get('live')}`"
            )
            st.caption(report.get("banner", ""))
        else:
            st.markdown(":gray-badge[Deterministic audit: no model]")
        with st.container(key="recorded-label"):
            st.markdown(
                f":violet-badge[Recorded run] Recorded run, finished "
                f"{A.short_time(finished_utc)}; not re-executed here"
            )
        st.caption(
            f"Run `{label}`, opened read-only: nothing executes and no approval is asked."
        )


def integrity(checks: list, ok: bool) -> None:
    """The recorded hashes, recomputed from the files on disk before anything is shown."""
    with st.container(key="card-integrity", border=True):
        st.subheader("Recorded evidence")
        rows = [
            {
                "result": c.status,
                "item": c.item,
                "recorded": c.recorded or "",
                "recomputed now": c.recomputed or "",
            }
            for c in checks
        ]
        if ok:
            with st.container(key="integrity-ok"):
                st.markdown(
                    f":green-badge[intact] All {len(checks)} recorded hashes and outcomes "
                    "match the files on disk, recomputed now."
                )
            with (
                st.expander("Integrity checks"),
                st.container(key="scroll-integrity"),
                st.container(key="trace-integrity"),
            ):
                st.table(pd.DataFrame(rows), hide_index=True)
        else:
            bad = [r for r in rows if r["result"] != "matches"]
            with st.container(key="integrity-failed"):
                st.error(
                    f"**{CHANGED}**: {len(bad)} of {len(rows)} recorded items differ from "
                    "the files on disk, so no outcome is shown.",
                    icon=":material/gpp_bad:",
                )
            with (
                st.container(key="scroll-integrity"),
                st.container(key="trace-integrity"),
            ):
                st.table(pd.DataFrame(bad), hide_index=True)
        st.caption(
            "Each hash the run recorded is recomputed from the bytes on disk, and each "
            "reported outcome is compared with its outcome.json. This detects changes since "
            "recording; it does not authenticate a run whose files and recorded hashes were "
            "both rewritten."
        )


def outcome_headline(code: str | None, key: str, title: str) -> None:
    with st.container(key=key):
        st.caption(title)
        if code is None:
            st.markdown("No outcome: the evaluated run produced none.")
            return
        st.markdown(f"## :{A.OUTCOME_COLORS.get(code, 'gray')}[{code}]")
        st.markdown(f"**{A.OUTCOME_LABELS.get(code, '')}**")
        st.caption(A.CAVEAT)


def model_text(text: str, label: str, key: str) -> None:
    with st.container(key=key):
        st.markdown(":gray-badge[model-written]")
        st.caption(label)
        st.text(text)


def state_badge(state: str | None) -> str:
    if state in A.FAILED_STATES:
        return (
            f":violet-badge[{state}]" if state == "ERROR" else f":orange-badge[{state}]"
        )
    if state == "NOT_SUPPORTED":
        return f":gray-badge[{state}]"
    return f":blue-badge[{state}]" if state else ""


# -- claim ---------------------------------------------------------------------------------
def claim_fields(claim) -> None:
    rows = [
        ("Statement", claim.statement),
        ("Claim type", claim.type),
        ("Sampling unit", claim.sampling_unit),
        (
            "Dependence",
            "; ".join(f"{d['kind']} ({d.get('column')})" for d in claim.dependence)
            or "none declared",
        ),
    ]
    rows += [(f"Column role: {k}", v or "not declared") for k, v in claim.roles.items()]
    st.table(
        pd.DataFrame(rows, columns=["Field", "Value"]),
        hide_index=True,
        hide_header=True,
    )


def not_supported(reason: str | None, key: str = "not-supported") -> None:
    with st.container(key=key):
        st.markdown("## :gray[NOT_SUPPORTED]")
        st.markdown(f"**{A.OUTCOME_LABELS['NOT_SUPPORTED']}**")
        st.caption(A.CAVEAT)
        st.markdown(f"Reason: `{reason}`")
        st.markdown(f"Next action: {A.next_action_for_intake(reason)}")


# -- trace ---------------------------------------------------------------------------------
def trace(
    events: list[dict],
    report: dict | None,
    approvals_seen: list[dict],
    collapsed: bool | None = None,
) -> None:
    """Stages and budget always; the tables inline (collapsed None) or in an expander."""
    t = A.trace(events)
    limits = ((report or {}).get("budget") or {}).get("limits") or {}
    used = ((report or {}).get("budget") or {}).get("used") or {}
    with st.container(key="trace-stages"):
        st.markdown("**Stages**")
        st.markdown(
            " ".join(state_badge(s["state"]) for s in t.states) or "Not started yet."
        )
    cols = st.columns(3)
    attempts = used.get("attempts", len(t.attempts))
    cols[0].metric("Model attempts", f"{attempts} of {limits.get('model_attempts', 6)}")
    cols[1].metric(
        "Tool operations",
        f"{used.get('tool_operations', len(t.tools))} of {limits.get('tool_operations', 12)}",
    )
    cols[2].metric(
        "Revisions",
        f"{used.get('revisions', 0)} of {limits.get('candidate_revisions', 2)}",
    )
    if report is not None:
        budget = report.get("budget") or {}
        st.caption(
            f"Active time {budget.get('active_s')} s of {limits.get('active_s')} s "
            f"(approval wait excluded); approval wait {budget.get('approval_wait_s')} s."
        )
    for d in approvals_seen:
        if d["decision"] == "declined":
            st.warning(f"{d['kind']}: Confirmation did not match: NOT approved.")
    for r in t.refused:
        st.warning(
            f"Refused before sending: `{r.get('result')}`"
            + (
                f" (projected {r.get('projected_usd')}, cap {r.get('estimate_cap_usd')})"
                if r.get("result") == "spend_cap"
                else ""
            )
        )
    if collapsed is None:
        trace_tables(t)
    else:
        with st.expander(
            "Agent trace: model attempts, tool calls, approvals", expanded=not collapsed
        ):
            trace_tables(t)


def trace_tables(t: "A.Trace") -> None:
    if t.attempts:
        rows = []
        for a in t.attempts:
            usage = a.get("usage") or {}
            cost = a.get("cost")
            if cost == "not applicable (fixture)" or cost is None:
                cost_text = "No provider cost (fixture replies)"
            else:
                cost_text = (
                    f"{cost.get('status')}: {cost.get('known_usd')} known, "
                    f"{cost.get('unresolved_usd')} held"
                )
            rows.append(
                {
                    "attempt": a.get("attempt"),
                    "action": a.get("tool") or "none",
                    "result": a.get("schema_failure")
                    and f"schema_failure: {a['schema_failure']}"
                    or a.get("result"),
                    "retry": "yes" if a.get("retry") else "no",
                    "elapsed s": a.get("elapsed_s"),
                    "prompt tokens": _count(usage.get("prompt_tokens")),
                    "completion tokens": _count(usage.get("completion_tokens")),
                    "estimated cost (not a bill)": cost_text,
                }
            )
        with st.container(key="trace-attempts"):
            st.markdown("**Model attempts**")
            st.table(pd.DataFrame(rows), hide_index=True)
    if t.tools:
        with st.container(key="trace-tools"):
            st.markdown("**Tool calls**")
            st.table(
                pd.DataFrame(
                    [
                        {
                            "tool": e.get("tool"),
                            "args": json.dumps(e.get("args"), sort_keys=True)[:120],
                            "outcome": e.get("outcome") or "",
                            "code": e.get("code") or "",
                            "result chars": e.get("result_chars"),
                            "result sha256": (e.get("result_sha256") or "")[:16] + "…",
                        }
                        for e in t.tools
                    ]
                ),
                hide_index=True,
            )
    if t.approvals:
        with st.container(key="trace-approvals"):
            st.markdown("**Approvals**")
            st.table(
                pd.DataFrame(
                    [
                        {
                            "kind": e.get("kind"),
                            "decision": e.get("decision"),
                            "approver reason": e.get("approver_reason") or "",
                            "code hash": e.get("candidate_hash"),
                        }
                        for e in t.approvals
                    ]
                ),
                hide_index=True,
            )


# -- approval panel -------------------------------------------------------------------------
def approval_panel(channel: Path, pending: dict) -> None:
    """Exactly the ApprovalRequest the engine passed (UI_SPEC §4.5), and one submission."""
    from atlas.ui.approver import answer

    kind = pending.get("kind")
    with st.container(key="approval-panel"):
        st.markdown("### Approval required")
        if kind == "original":
            st.markdown(
                "**Run the ORIGINAL, unmodified project code in the isolated Docker runner.**"
            )
        else:
            st.markdown(
                "**Run this CANDIDATE revision in the isolated Docker runner.**"
            )
        st.markdown(f"Entry point: `{inert(pending.get('entry_point') or '')}`")
        st.markdown("Snapshot hash")
        with st.container(key="approval-snapshot-hash"):
            st.code(pending.get("base_snapshot_hash"), language=None, wrap_lines=True)
        st.markdown("Code hash")
        with st.container(key="approval-code-hash"):
            st.code(pending.get("candidate_hash"), language=None, wrap_lines=True)
        if kind != "original":
            model_text(
                inert(pending.get("model_rationale") or "(none)"),
                "Rationale: model-written (untrusted)",
                "model-approval-rationale",
            )
            st.markdown(
                "Proposed diff (untrusted; control characters shown as escapes)"
            )
            with st.container(key="scroll-approval-diff"):
                st.code(inert(pending.get("diff") or ""), language="diff")
        form_key = (
            f"approve-{pending.get('seq')}-{(pending.get('candidate_hash') or '')[:16]}"
        )
        if (Path(channel) / f"answer-{pending.get('seq')}.json").exists():
            st.info(
                "Decision submitted; waiting for the engine to continue.",
                icon=":material/hourglass_top:",
            )
            return
        with st.form(form_key, clear_on_submit=True):
            typed = st.text_input(
                f"Type the first {CONFIRM_CHARS} characters of the code hash to approve; "
                "anything else declines",
                key=f"{form_key}-typed",
            )
            submitted = st.form_submit_button("Submit confirmation", type="primary")
        if submitted:
            answer(channel, pending["seq"], typed)
            st.rerun()
        if st.button(
            "Close without deciding",
            help="Nothing executes; the run ends NEEDS_INPUT.",
            key=f"{form_key}-close",
        ):
            answer(channel, pending["seq"], None)
            st.rerun()


# -- finding ---------------------------------------------------------------------------------
def required_table(rows: list[dict], key: str) -> None:
    with st.container(key=key):
        st.table(
            pd.DataFrame(
                [
                    {
                        "status": r.get("status"),
                        "assertion": r.get("assertion_id"),
                        "reason": r.get("reason") or "",
                        "evidence valid": "yes" if r.get("evidence_valid") else "no",
                    }
                    for r in A.sort_required(rows)
                ]
            ),
            hide_index=True,
        )


def next_actions(rows: list[dict]) -> None:
    """GAP-10: one next action per NOT_ASSESSED or ERROR reason code present."""
    reasons = sorted(
        {
            r["reason"]
            for r in rows
            if r.get("status") in ("NOT_ASSESSED", "ERROR") and r.get("reason")
        }
    )
    if not reasons:
        return
    with st.container(key="next-actions"):
        st.markdown("**Next actions**")
        for reason in reasons:
            action = A.NEXT_ACTIONS.get(
                reason, "See the check details for what is missing."
            )
            st.markdown(f"- `{reason}`: {action}")


def counts_line(rows: list[dict]) -> str:
    c = A.status_counts(rows)
    return (
        f"{c['FAIL']} of {len(rows)} required checks FAIL, {c['NOT_ASSESSED']} NOT_ASSESSED, "
        f"{c['ERROR']} ERROR, {c['PASS']} PASS"
    )


def assertion_details(outcome: dict | None, rows: list[dict]) -> None:
    for r in A.sort_required(rows):
        a = A.assertion(outcome, r.get("assertion_id")) or {}
        label = f"{r.get('status')} {r.get('assertion_id')}"
        if r.get("reason"):
            label += f" ({r['reason']})"
        with st.expander(label):
            st.markdown("Observed")
            st.json(a.get("observed") or {}, expanded=1)
            if a.get("limitations"):
                st.markdown("Limitations")
                for x in a["limitations"]:
                    st.markdown(f"- {x}")
            if a.get("evidence"):
                st.markdown("Evidence")
                st.table(pd.DataFrame(a["evidence"]), hide_index=True)


def metric_block(outcome: dict | None, key: str) -> None:
    m = A.primary_metric(outcome)
    with st.container(key=key):
        if m is None:
            st.markdown("Independent primary metric: not available for this run.")
            return
        st.markdown(f"**Independent primary metric:** `{m.name}`")
        cols = st.columns(2)
        cols[0].metric(
            f"Pooled, {m.observations} evaluated rows",
            A.fmt_metric(m.pooled),
            help="complete" if m.pooled_complete else "incomplete",
        )
        cols[1].metric(
            f"Mean over {m.folds} folds",
            A.fmt_metric(m.mean_over_folds),
            help="complete" if m.folds_complete else "incomplete",
        )
        for x in m.limitations:
            st.caption(x)


def conditional_passes(outcome: dict | None) -> None:
    """PASS results that rest on a documented, unverified declaration (route C containment),
    with the engine's own limitation text, verbatim."""
    shown = []
    for a in (outcome or {}).get("assertions", []):
        basis = (a.get("observed") or {}).get("established_by")
        values = basis.values() if isinstance(basis, dict) else [basis]
        if a.get("status") == "PASS" and "documented_containment" in values:
            shown.append(a)
    if not shown:
        return
    with st.container(key="conditional-passes"):
        for a in shown:
            st.warning(
                f"**Conditional PASS: `{a['assertion_id']}`** depends on "
                f"{', '.join(a.get('depends_on') or []) or 'a declaration'}.\n\n"
                + "\n\n".join(a.get("limitations") or []),
                icon=":material/rule:",
            )


def provenance_notes(limitations, notes) -> None:
    """The engine's provenance-scope limitation, and the catalogue's dataset notes."""
    engine = [x for x in limitations or [] if "Provenance begins" in x]
    if not engine and not notes:
        return
    with st.container(key="provenance-notes"):
        st.markdown("**Provenance scope**")
        for x in engine:
            st.markdown(f"- {x} (from the run's report)")
        for x in notes:
            st.markdown(f"- {x} (catalogue note)")


def _latest_run(runs_root: Path, project: str) -> Path | None:
    runs = sorted(
        (
            p
            for p in runs_root.iterdir()
            if p.is_dir()
            and p.name.startswith(f"agent-{project}-")
            and (p / "original" / "outcome.json").is_file()
        ),
        key=lambda p: p.stat().st_mtime,
    )
    return runs[-1] if runs else None


def protocol_comparison(run_dir: Path, this, other) -> None:
    """Descriptive: this run's independent metric beside the related project's latest run.
    Every number is read from the two runs' outcome.json files."""
    with st.container(key="protocol-comparison", border=True):
        st.markdown(f"**Descriptive comparison: {this.name} and {other.name}**")
        other_dir = _latest_run(run_dir.parent, other.name)
        if other_dir is None:
            st.caption(
                f"Run {other.name} to compare the two protocols' independent metrics."
            )
            return
        rows = []
        for fx, d in ((this, run_dir), (other, other_dir)):
            outcome = A.read_json(d / "original" / "outcome.json")
            m = A.primary_metric(outcome)
            reported = A.reported_metric(outcome)
            rows.append(
                {
                    "project": fx.label,
                    "run": d.name,
                    "outcome": (outcome or {}).get("outcome"),
                    f"independent {m.name if m else 'metric'}, mean over folds": A.fmt_metric(
                        m.mean_over_folds if m else None
                    ),
                    "pooled": A.fmt_metric(m.pooled if m else None),
                    "folds": m.folds if m else None,
                    "reported by the project": ", ".join(
                        A.fmt_metric(r["reported"]) for r in reported
                    )
                    if reported
                    else "none",
                }
            )
        st.table(pd.DataFrame(rows), hide_index=True)
        st.caption(
            "Descriptive only, not causal: two different protocols evaluated on the same "
            "training subjects. The difference is not the effect of any single flaw, and the "
            "metric is never part of an outcome. Values are read from each run's outcome.json."
        )


def baselines(outcome: dict | None) -> None:
    d = A.descriptive(outcome, "metric.baselines")
    m = A.primary_metric(outcome)
    if not d or m is None:
        return
    rows = []
    for name, data in (d.get("observed") or {}).items():
        agg = (data.get("aggregates") or {}).get("development_eval", {}).get(
            m.name
        ) or {}
        rows.append(
            {
                "baseline": name,
                f"pooled {m.name}": A.fmt_metric(
                    (agg.get("pooled") or {}).get("value")
                ),
                "mean over folds": A.fmt_metric(
                    (agg.get("mean_over_folds") or {}).get("value")
                ),
            }
        )
    if rows:
        st.markdown("Baselines (descriptive)")
        st.table(pd.DataFrame(rows), hide_index=True)
        for x in d.get("limitations") or []:
            st.caption(x)


def class_support(outcome: dict | None) -> None:
    d = A.descriptive(outcome, "split.class_support")
    if not d:
        return
    with st.expander("Class support per fold (descriptive)"):
        for x in d.get("limitations") or []:
            st.caption(x)
        st.json(d.get("observed") or {}, expanded=1)


def reported_metric(outcome: dict | None) -> None:
    rows = A.reported_metric(outcome)
    if rows is None:
        st.caption("This project declares no reported metric.")
        return
    st.markdown("Reported against independent")
    st.table(pd.DataFrame(rows), hide_index=True)


def bullet_list(items, key: str | None = None) -> None:
    with st.container(key=key):
        for x in items or []:
            st.markdown(f"- {x}")


# -- revision ---------------------------------------------------------------------------------
def proposal(view: A.ProposalView, index: int) -> None:
    r = view.record
    outcome = r.get("outcome") or "unknown"
    colors = {
        "executed": "blue",
        "rejected": "red",
        "declined": "orange",
        "unavailable": "orange",
        "not_executed_here": "violet",  # hosted mode (T-12)
    }
    with st.container(key=f"proposal-{index}", border=True):
        st.markdown(
            f"**Revision {r.get('revision')}** :{colors.get(outcome, 'gray')}-badge[{outcome}]"
            f" source `{r.get('source_kind')}`"
            + (f", code `{r.get('code')}`" if r.get("code") else "")
        )
        if outcome == "not_executed_here":
            with st.container(key=f"proposal-hosted-{index}"):
                st.markdown(
                    "Passes ATLAS validation; **not executed here**. The hosted demo runs "
                    "no candidate code, so nothing here validates this diff beyond that."
                )
        if r.get("detail"):
            st.caption(r.get("detail_label", "validator message; may quote model text"))
            with st.container(key=f"model-detail-{index}"):
                st.text(r["detail"])
        files_label = r.get("files_label", "model-written (untrusted)")
        if view.diff_text is not None:
            match = "matches" if view.diff_hash_matches else "DOES NOT match"
            st.markdown(f"Diff, {files_label}: `{r.get('diff_path')}`")
            st.caption(
                f"SHA-256 {view.diff_file_sha256} (recomputed from the file; {match} the "
                f"recorded diff_sha256)"
            )
            with st.container(key=f"scroll-diff-{index}"):
                st.code(inert(view.diff_text), language="diff")
        elif r.get("diff_sha256"):
            st.caption(
                f"Diff not stored (over the size limit); recorded SHA-256 {r['diff_sha256']}"
            )
        else:
            st.caption("No diff could be generated from this proposal.")
        if view.new_source_text is not None:
            with st.expander(f"Complete file sent by the model, {files_label}"):
                st.caption(f"SHA-256 {view.new_source_file_sha256}")
                st.code(inert(view.new_source_text), language="python")


def candidate_detail(c: dict, index: int) -> None:
    ex = c.get("execution") or {}
    with st.container(key=f"candidate-{index}", border=True):
        st.markdown(
            f"**Candidate {index}** execution `{ex.get('status')}` in `{ex.get('runner')}`, "
            f"scientific outcome {badge(c.get('scientific_outcome'), A.OUTCOME_COLORS)}"
        )
        st.caption("Execution status is not the outcome; both are shown.")
        st.markdown("Code hash")
        st.code(c.get("candidate_hash"), language=None, wrap_lines=True)
        st.markdown(f"Diff SHA-256 `{c.get('diff_sha256')}`")
        appr = c.get("approval") or {}
        st.caption(
            f"Approved {appr.get('approved_at')} for code hash {appr.get('candidate_hash')} "
            f"on snapshot {appr.get('base_snapshot_hash')}"
        )


# -- comparison -------------------------------------------------------------------------------
def comparison(report: dict, run_dir: Path) -> None:
    comp = report.get("comparison") or {}
    orig = comp.get("original") or {}
    cands = comp.get("candidates") or []
    st.markdown(f"**Basis:** {comp.get('comparison_basis')}")
    orig_outcome = A.read_json(run_dir / "original" / "outcome.json")
    for i, c in enumerate(cands, start=1):
        cand_dir = run_dir / "candidates" / Path(c.get("run_dir") or f"c{i}").name
        cand_outcome = A.read_json(cand_dir / "outcome.json")
        om, cm = A.primary_metric(orig_outcome), A.primary_metric(cand_outcome)
        ex = c.get("execution") or {}

        def metric_text(m):
            if m is None:
                return "not available"
            return (
                f"{m.name} {A.fmt_metric(m.pooled)} pooled over {m.observations} rows"
            )

        def fails(rows):
            return (
                ", ".join(r["assertion_id"] for r in rows if r.get("status") == "FAIL")
                or "none"
            )

        rows = [
            ("Outcome", orig.get("scientific_outcome"), c.get("scientific_outcome")),
            (
                "Execution",
                (
                    f"{orig.get('execution_status')} in {orig.get('runner')} "
                    f"(executed: {orig.get('executed')})"
                ),
                (
                    f"{ex.get('status')} in {ex.get('runner')} (container removed: "
                    f"{ex.get('container_removed')}, {ex.get('elapsed_s')} s, evaluated: "
                    f"{c.get('evaluated')})"
                ),
            ),
            (
                "Failed assertions",
                fails(orig.get("required_set") or []),
                fails(c.get("required_set") or []),
            ),
            ("Independent primary metric", metric_text(om), metric_text(cm)),
            (
                "Incomplete coverage",
                ", ".join(orig.get("incomplete_coverage") or []) or "none",
                ", ".join(c.get("incomplete_coverage") or []) or "none",
            ),
        ]
        with st.container(key=f"scroll-comparison-{i}"):
            st.table(
                pd.DataFrame(rows, columns=["", "Original", f"Candidate {i}"]),
                hide_index=True,
            )
        st.caption(
            "A lower score can be the honest result: the metric is descriptive and never part "
            "of the outcome."
        )
        changes = []
        for s in c.get("status_by_assertion") or []:
            changed = s.get("original") != s.get("candidate")
            changes.append(
                {
                    "assertion": s.get("assertion_id"),
                    "original": s.get("original"),
                    "candidate": s.get("candidate"),
                    "change": f"{s.get('original')} → {s.get('candidate')}"
                    if changed
                    else "unchanged",
                }
            )
        with st.container(key=f"status-changes-{i}"):
            st.markdown("**Per-assertion change**")
            frame = pd.DataFrame(changes)
            styled = frame.style.apply(
                lambda row: (
                    [
                        "background-color: #EFF6FF; font-weight: 600"
                        if row["change"] != "unchanged"
                        else ""
                    ]
                    * len(row)
                ),
                axis=1,
            ).hide(axis="index")
            st.table(styled)
        with st.expander("Limitations and evidence hashes"):
            st.markdown("Original")
            bullet_list(orig.get("limitations"))
            st.markdown(f"Candidate {i}")
            bullet_list(c.get("limitations"))
            st.markdown("Evidence SHA-256 (original)")
            st.json(orig.get("evidence_sha256") or {}, expanded=True)
            st.markdown(f"Evidence SHA-256 (candidate {i})")
            st.json(c.get("evidence_sha256") or {}, expanded=True)
    st.markdown("**Reading guide**")
    bullet_list(comp.get("reading_guide"))


# -- trust and export --------------------------------------------------------------------------
def cost(report: dict) -> None:
    c = report.get("cost") or {}
    with st.container(key="cost"):
        st.markdown("**Estimated cost (not a bill)**")
        if not c.get("applicable"):
            st.markdown(c.get("reason", "not applicable"))
            return
        st.markdown(
            f"{c.get('known_usd')} USD from reported usage at listed prices; "
            f"{c.get('unresolved_usd')} USD held for unknown usage; "
            f"estimated total {c.get('estimated_total_usd')} USD."
        )
        st.caption(c.get("unresolved_note", ""))
        st.caption(c.get("note", ""))


def rendered_markdown(report: dict, report_sha: str) -> str:
    """GAP-6: a readable rendering of the same report fields; it adds no data."""
    so = report.get("scientific_outcomes") or {}
    lines = [
        f"# ATLAS run report (rendered from agent_report.json {report_sha})",
        "",
        report.get("banner", ""),
        "",
        f"- Terminal state: {report.get('terminal_state')}"
        + (
            f" ({report.get('terminal_reason')})"
            if report.get("terminal_reason")
            else ""
        ),
        f"- Original outcome: {so.get('original')}",
        f"- Candidate outcomes: {', '.join(str(x) for x in so.get('candidates') or []) or 'none'}",
        f"- {A.CAVEAT}",
        "",
        "## Proposals",
    ]
    for p in report.get("proposals") or []:
        lines.append(
            f"- Revision {p.get('revision')}: {p.get('outcome')}"
            + (f" ({p.get('code')})" if p.get("code") else "")
        )
    lines += ["", "## Limitations"] + [
        f"- {x}" for x in report.get("limitations") or []
    ]
    return "\n".join(lines) + "\n"


def export(run_dir: Path, report: dict | None) -> None:
    files = A.exports(run_dir, report)
    with st.container(key="export"):
        rows = []
        for f in files:
            rows.append(
                {
                    "file": f.label,
                    "sha256 (recomputed)": f.sha256,
                    "recorded by the engine": "matches"
                    if f.matches
                    else ("not recorded" if f.matches is None else "DOES NOT match"),
                }
            )
        st.table(pd.DataFrame(rows), hide_index=True)
        cols = st.columns(min(len(files), 3) or 1)
        for i, f in enumerate(files):
            cols[i % len(cols)].download_button(
                f"Download {f.label}",
                data=f.path.read_bytes(),
                file_name=f.label.replace("/", "_"),
                key=f"download-{f.label}",
                width="stretch",
            )
        if report is not None:
            report_file = next(
                (f for f in files if f.label == "agent_report.json"), None
            )
            if report_file is not None:
                text = rendered_markdown(report, report_file.sha256)
                st.download_button(
                    "Download readable report (Markdown)",
                    data=text.encode("utf-8"),
                    file_name="agent_report.md",
                    key="download-markdown",
                    help=f"Rendered from agent_report.json {report_file.sha256}",
                )
