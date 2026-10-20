"""Page sections for app.py. Each renders artifact values with the spec's labels (§1, §4).

Styling is Streamlit's theme (`.streamlit/config.toml`, the HUD visual system of
docs/UI_DESIGN_HUD.md) plus the documented CSS block in `inject_css`, which targets only
`st-key-*` classes (a container's `key` becomes the class `st-key-<key>`, per `st.container`'s
documentation), and the HUD's own markup (`atlas.ui.hud`). Status colours always sit next to
the printed code, never instead of it.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from atlas.agent.approval import CONFIRM_CHARS, inert
from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import recorded as RR
from atlas.ui.recorded import CHANGED

CSS = """
<style>
/* Cards: the #0F1720 panel on the #0A0F14 page, with the theme's 1 px #1E2A36 hairline
   (UI_DESIGN_HUD §2). Only st-key-* hooks. */
[class*="st-key-card-"] { background: #0F1720; padding: 16px 20px 20px; }
/* Model-written text: a subdued dashed frame on the page colour; the full amber only on the
   header badge (UI_SPEC §1.2, UI_DESIGN_HUD §4.6). Diffs are model-written too, and sit in
   their own st-key-model-* frame. */
[class*="st-key-model-"] { background: #0A0F14;
  border: 1px dashed rgba(251, 191, 36, 0.35); border-radius: 4px; padding: 12px 16px; }
/* The blocking approval panel: the active frame (UI_DESIGN_HUD §2.3, phase 2). Its accent
   corner brackets are eight solid marks painted as background layers under the 1 px hairline
   (3 px wide, so 2 px show inside it; solid colour, not a visual gradient), so no markup is
   needed around native widgets. */
.st-key-approval-panel { border: 1px solid #1E2A36; border-radius: 2px;
  padding: 20px 24px 24px; gap: 12px; background:
  linear-gradient(#67E8F9 0 0) left top / 18px 3px, linear-gradient(#67E8F9 0 0) left top / 3px 18px,
  linear-gradient(#67E8F9 0 0) right top / 18px 3px, linear-gradient(#67E8F9 0 0) right top / 3px 18px,
  linear-gradient(#67E8F9 0 0) left bottom / 18px 3px, linear-gradient(#67E8F9 0 0) left bottom / 3px 18px,
  linear-gradient(#67E8F9 0 0) right bottom / 18px 3px, linear-gradient(#67E8F9 0 0) right bottom / 3px 18px,
  #0F1720; background-repeat: no-repeat; background-origin: border-box; }
/* The decision: its own inset, apart from the request it answers; closing without deciding
   sits below a hairline, away from the confirmation. */
.st-key-approval-decision { background: #0A0F14; border: 1px solid #1E2A36; border-radius: 4px;
  padding: 12px 16px 16px; gap: 8px; }
.st-key-approval-close { border-top: 1px solid #1E2A36; padding-top: 12px; }
/* Failure and honest-empty states: the status colour on the left edge, next to the printed
   code; never success styling. */
[class*="st-key-state-"] { background: #0F1720; border: 1px solid #1E2A36;
  border-left: 2px solid #A8A29E; border-radius: 4px; padding: 10px 14px; gap: 4px; }
[class*="st-key-state-red-"] { border-left-color: #F87171; }
[class*="st-key-state-amber-"] { border-left-color: #FBBF24; }
[class*="st-key-state-violet-"] { border-left-color: #C084FC; }
/* Data tables (trace, checks, comparison, integrity, export): hairline rows, Plex Mono data
   in the neutral text colour, a readable row height; HUD labels for the column heads. */
:is([class*="st-key-trace-"], .st-key-export, .st-key-finding-checks,
  .st-key-hosted-original-checks, [class*="st-key-status-changes-"],
  [class*="st-key-scroll-comparison-"], .st-key-protocol-comparison) table td {
  font-family: 'IBM Plex Mono', monospace; font-size: 13px; line-height: 1.45;
  color: #E2E8F0; padding: 7px 12px; border-color: #1E2A36; vertical-align: top;
  overflow-wrap: anywhere; }
:is([class*="st-key-trace-"], .st-key-export, .st-key-finding-checks,
  .st-key-hosted-original-checks, [class*="st-key-status-changes-"],
  [class*="st-key-scroll-comparison-"], .st-key-protocol-comparison) table th {
  font-family: 'IBM Plex Sans Condensed', sans-serif; font-size: 11px; font-weight: 500;
  letter-spacing: 0.08em; text-transform: uppercase; color: #94A3B8; padding: 7px 12px;
  border-color: #1E2A36; vertical-align: bottom; }
/* The Route line and other single data lines in Plex Mono. */
.st-key-route p { font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: #E2E8F0; }
/* The banner: a compact strip; the recorded page sits tighter so its hero fits the first
   viewport (UI_DESIGN_HUD §3.1). */
.st-key-banner { background: #0F1720; gap: 2px; padding: 6px 14px; }
.st-key-hud-page { gap: 0.75rem; }
/* Streamlit pulls the next element up under a heading (its markdown block has a -1rem bottom
   margin, which its own 1rem heading padding balances). Phase 1 removed that padding and the
   hero rode up under the title; with 0.75rem of padding and the 0.75rem page gap, the title's
   text clears the panel below by 0.5rem at every width. */
.st-key-hud-page h1 { padding: 0 0 0.75rem; }
/* Primary buttons: dark text on the accent (Streamlit draws white text, 1.45:1). */
[class*="st-key-primary-"] button, [class*="st-key-primary-"] button p { color: #0A0F14; }
/* Disabled buttons are transparent: the muted token keeps their words readable (7.04:1 on a
   panel) instead of dark text on nothing, or Streamlit's 40 % text. */
[class*="st-key-primary-"] button:disabled, [class*="st-key-primary-"] button:disabled p,
.st-key-live-disabled button p { color: #94A3B8; }
/* Wide diffs and tables scroll inside their own region (UI_SPEC §7 viewports). */
[class*="st-key-scroll-"] { overflow-x: auto; }
/* Hashes in trace and export tables wrap instead of being clipped (never truncated). */
[class*="st-key-trace-"] td, .st-key-export td { word-break: break-all; }
</style>
"""


def inject_css() -> None:
    from atlas.ui import story

    st.html(CSS)
    st.html(H.CSS)
    story.inject_css()


def _count(value) -> str:
    return "n/a" if value is None else str(value)


def badge(code: str, colors: dict) -> str:
    return f":{colors.get(code, 'gray')}-badge[{code}]"


STATE_BADGE = {"red": "red", "amber": "orange", "violet": "violet", "stone": "gray"}
STATE_TONE = {"ERROR": "violet", "NEEDS_INPUT": "amber", "BUDGET_EXHAUSTED": "amber"}


def state_panel(
    key: str, tone: str, code: str, reason: str, action: str | None = None
) -> None:
    """A failure or honest-empty state (UI_DESIGN_HUD phase 2): the code as a status-coloured
    badge, the reason, then the next action, in a state frame (st-key-state-<tone>-*: the
    status colour on its left edge). Native elements, rendered in one pass. `reason` and
    `action` are Markdown written by ATLAS; callers wrap engine codes in backticks."""
    with st.container(key=f"state-{tone}-{key}"):
        st.markdown(f":{STATE_BADGE[tone]}-badge[{code}] {reason}")
        if action:
            st.markdown(f"**Next action:** {action}")


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


def recorded_banner(
    report: dict | None,
    label: str,
    finished_utc: str | None,
    notes: tuple[str, ...] = (),
) -> None:
    """A recorded run's own LIVE or NON-LIVE label, and that it is not re-executed here.
    `notes` (the hosted replay disclosure, a dataset citation) follow as captions; with a
    note, the run line is shortened, since the replay disclosure says nothing runs here."""
    with st.container(key="banner", border=True):
        if report is not None:
            live = report.get("live") is True
            tag = ":blue-badge[LIVE RUN]" if live else ":gray-badge[NON-LIVE RUN]"
            mode = f"{tag} mode `{report.get('mode')}`, live `{report.get('live')}`"
        else:
            mode = ":gray-badge[Deterministic audit: no model]"
        # One line: the run's own LIVE or NON-LIVE label, then the recorded label.
        with st.container(key="recorded-label"):
            st.markdown(
                f"{mode} &ensp; :blue-badge[Recorded run] Recorded run, finished "
                f"{A.short_time(finished_utc)}; not re-executed here"
            )
        if report is not None:
            st.caption(report.get("banner", ""))
        if notes:
            st.caption(f"Run `{label}`. {notes[0]}")
            for note in notes[1:]:
                st.caption(note)
        else:
            st.caption(
                f"Run `{label}`, opened read-only: nothing executes and no approval is "
                "asked."
            )


def integrity(
    checks: list, ok: bool, ring: str | None = None, *, plain: bool = False
) -> None:
    """The recorded hashes, recomputed from the files on disk before anything is shown.
    `ring` is the HUD integrity ring's markup (`atlas.ui.hud.ring`), shown first. `plain`
    (the story's plain mode, intact runs only) leaves out the table of hashes and names no
    file; a run that is not intact always shows its table of differing items."""
    with st.container(key="card-integrity", border=True):
        st.subheader("Recorded evidence")
        if ring is not None:
            with st.container(key="hud-ring"):
                st.markdown(ring, unsafe_allow_html=True)
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
                    f":green-badge[intact] {H.integrity_count(checks).verified}: each "
                    "matches the files on disk, recomputed now."
                )
            if not plain:
                with (
                    st.expander("Integrity checks"),
                    st.container(key="scroll-integrity"),
                    st.container(key="trace-integrity"),
                ):
                    st.table(pd.DataFrame(rows), hide_index=True)
        else:
            bad = [r for r in rows if r["result"] != "matches"]
            with st.container(key="integrity-failed"):
                state_panel(
                    "integrity",
                    "red",
                    "EVIDENCE CHANGED",
                    f"**{CHANGED}**: {H.integrity_count(checks).differing} from the "
                    "files on disk, so no outcome is shown.",
                    "restore the run's files from the recording (or copy the run again) and "
                    "open it again; the table lists each differing item.",
                )
            with (
                st.container(key="scroll-integrity"),
                st.container(key="trace-integrity"),
            ):
                st.table(pd.DataFrame(bad), hide_index=True)
        st.caption(
            C.INTEGRITY_NOTE_PLAIN
            if plain and ok
            else "Each hash the run recorded is recomputed from the bytes on disk, and each "
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
    """Model-written text in its frame: a native header (badge and the engine's label), then
    the untrusted text as a plain `st.text` element, never parsed as HTML or Markdown."""
    with st.container(key=key):
        st.markdown(H.MODEL_BADGE_MARKDOWN)
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
    with st.container(key=key), st.container(key=f"state-stone-{key}"):
        st.markdown("## :gray[NOT_SUPPORTED]")
        st.markdown(f"**{A.OUTCOME_LABELS['NOT_SUPPORTED']}**")
        st.caption(A.CAVEAT)
        st.markdown(f"Reason: `{reason}`")
        st.markdown(f"**Next action:** {A.next_action_for_intake(reason)}")


# -- trace ---------------------------------------------------------------------------------
def trace(
    events: list[dict],
    report: dict | None,
    approvals_seen: list[dict],
    collapsed: bool | None = None,
) -> None:
    """The trace below the HUD mission track (which shows the stages and the budget): the
    active time, declined approvals, refused requests, then the tables inline (collapsed
    None) or in an expander."""
    t = A.trace(events)
    limits = ((report or {}).get("budget") or {}).get("limits") or {}
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
def _label(text: str) -> str:
    """A HUD label (Plex Sans Condensed, uppercase, muted) for a native block below it."""
    return f'<p class="hud hud-flabel"><span class="hud-lbl">{H.esc(text)}</span></p>'


def approval_panel(channel: Path, pending: dict) -> None:
    """Exactly the ApprovalRequest the engine passed (UI_SPEC §4.5), and one submission.

    The active frame (accent corner brackets, st-key-approval-panel): the request (what runs,
    the entry point, both hashes in full), the model-written rationale and diff in the
    model-written frame, then the decision in its own inset, with closing without deciding
    below a hairline. The rule, the timeouts and the declines are the engine's
    (`atlas.ui.approver`), unchanged."""
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
        st.markdown(_label("Snapshot hash"), unsafe_allow_html=True)
        with st.container(key="approval-snapshot-hash"):
            st.markdown(
                H.hash_block(pending.get("base_snapshot_hash")), unsafe_allow_html=True
            )
        st.markdown(_label("Code hash"), unsafe_allow_html=True)
        with st.container(key="approval-code-hash"):
            st.markdown(
                H.hash_block(pending.get("candidate_hash")), unsafe_allow_html=True
            )
        if kind != "original":
            model_text(
                inert(pending.get("model_rationale") or "(none)"),
                "Rationale: model-written (untrusted)",
                "model-approval-rationale",
            )
            with st.container(key="model-approval-diff"):
                st.markdown(H.MODEL_BADGE_MARKDOWN)
                st.caption(
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
        with st.container(key="approval-decision"):
            st.markdown(_label("Your decision"), unsafe_allow_html=True)
            with st.form(form_key, clear_on_submit=True, border=False):
                typed = st.text_input(
                    f"Type the first {CONFIRM_CHARS} characters of the code hash to approve; "
                    "anything else declines",
                    key=f"{form_key}-typed",
                )
                with st.container(key="primary-submit-confirmation"):
                    submitted = st.form_submit_button(
                        "Submit confirmation", type="primary"
                    )
            if submitted:
                answer(channel, pending["seq"], typed)
                st.rerun()
            with st.container(key="approval-close"):
                if st.button(
                    "Close without deciding",
                    help="Nothing executes; the run ends NEEDS_INPUT.",
                    key=f"{form_key}-close",
                ):
                    answer(channel, pending["seq"], None)
                    st.rerun()
                st.caption("Nothing executes; the run ends NEEDS_INPUT.")


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


def assertion_details(
    outcome: dict | None, rows: list[dict], source: str = "outcome.json"
) -> None:
    """Each required check's recorded fields (status, reason, evidence_valid, limitations,
    evidence with sha256, observed as rows), drawn like the HUD's inspection frame."""
    for r in A.sort_required(rows):
        aid = r.get("assertion_id")
        a = A.assertion(outcome, aid)
        label = f"{r.get('status')} {aid}"
        if r.get("reason"):
            label += f" ({r['reason']})"
        with st.expander(label):
            if a is None:
                st.markdown(f"`{aid}` is not recorded in `{source}`.")
                continue
            st.markdown(
                '<div class="hud hud-detail">'
                + H.record_body(H.Inspect(str(aid), source, a))
                + "</div>",
                unsafe_allow_html=True,
            )


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
    Every number is read from the two runs' outcome.json files. `run_dir` passed the page's
    verification gate; the related run is verified here the same way, and when it is not
    intact nothing is read from it (release review 1, F1)."""
    with st.container(key="protocol-comparison", border=True):
        st.markdown(f"**Descriptive comparison: {this.name} and {other.name}**")
        other_dir = _latest_run(run_dir.parent, other.name)
        if other_dir is None:
            st.caption(
                f"Run {other.name} to compare the two protocols' independent metrics."
            )
            return
        other_report = A.read_json(other_dir / "agent_report.json")
        if other_report is None or not RR.intact(RR.verify(other_dir, other_report)):
            st.caption(
                f"The latest {other.name} run (`{other_dir.name}`): {CHANGED}, so it is "
                "not compared."
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
        "not_executed_here": "gray",  # hosted mode (T-12): not run, not an error
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
            with st.container(key=f"model-diff-{index}"):
                st.markdown(H.MODEL_BADGE_MARKDOWN)
                st.markdown(f"Diff, {files_label}: `{r.get('diff_path')}`")
                st.caption(
                    f"SHA-256 {view.diff_file_sha256} (recomputed from the file; {match} "
                    f"the recorded diff_sha256)"
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
            with (
                st.expander(f"Complete file sent by the model, {files_label}"),
                st.container(key=f"model-source-{index}"),
            ):
                st.markdown(H.MODEL_BADGE_MARKDOWN)
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
        name = A.recorded_basename(c.get("run_dir") or f"c{i}")
        cand_outcome = (
            A.read_json(run_dir / "candidates" / name / "outcome.json")
            if name
            else None
        )
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
                        "background-color: #2D343D; font-weight: 600"
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
