"""The Overview & Cases page (UI restructure, slice 1): each bundled case told as a story.

Top to bottom: the header, the case cards, then the selected case's banner, the one
verification gate (`atlas.ui.results.case_page`), the verdict bar and five numbered steps.
Everything about a case is read from its own verified files (`atlas.ui.recorded.verify`;
only paths in the verified set are read, through `atlas.ui.hud`), and every sentence is the
fixed copy of `atlas.ui.copy` or `assertion_labels.json`, filled only with recorded values.
Model-written text appears only in the model-written frame (`st.text` / `st.code`), never in
HUD markup.

Plain English is the default; Expert view (one session-wide setting) adds assertion IDs,
hashes, run-relative paths, sources, costs and request counts, and the full record cards.
Local filesystem paths are never shown in either mode.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import streamlit as st

from atlas.agent.approval import inert
from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import recorded as R
from atlas.ui import results as RS
from atlas.ui import tamper as T
from atlas.ui import views as V
from atlas.ui.catalogue import ROOT

# The recorded bundle the cases come from (atlas.hosted.bundle's too). ATLAS_UI_CASES_DIR,
# set only by whoever starts the server (the browser tests use it for a changed copy),
# names another folder with the same layout; it is verified exactly like the bundle.
CASES_ENV = "ATLAS_UI_CASES_DIR"
BUNDLE_ROOT = ROOT / "demo" / "recorded"
EXPERT = "expert"  # session key: Expert view on (plain key; the widget writes it)
EXPERT_WIDGET = "expert_widget"
CASE = "story_case"  # session key: the selected case
# Recorded approval reasons of the T-09 audit script's approver (benchmarks/real_sensor/
# run_audit.py, OriginalOnly): the original approved by the script, no typed confirmation.
SCRIPT_REASONS = frozenset({"t09_task_authorized_original"})
TAMPER_LIMIT = "tamper_limit"  # session key: the tamper demo's SessionLimit
TAMPER_RESULTS = "tamper_results"  # session key: the last demo result per case
TAMPER_EVENT = "tamper_demo_failed"
_log = logging.getLogger(__name__)
_MD = set(
    "\\`*_[]<>#|$~"
)  # marks that can start Markdown, a link or a directive inline

CSS = """
<style>
/* The header (the page's own hooks). */
.st-key-story-page { gap: 0.75rem; }
.st-key-story-header { gap: 0.5rem; }
/* As on the recorded page: the heading's padding balances Streamlit's -1rem pull-up. */
.st-key-story-header h1 { padding: 0 0 0.75rem; letter-spacing: 0.04em; }
.st-key-story-tagline p { font-size: 17px; line-height: 1.45; color: #E2E8F0; }
.st-key-story-why p { font-size: 13px; line-height: 1.45; color: #94A3B8; }
/* Case cards: one panel each; the selected one carries the accent edge. The title button is
   stretched over its card, so the whole card is the click target; its focus ring is the
   card's. */
[class*="st-key-case-card-"] { position: relative; background: #0F1720;
  border: 1px solid #1E2A36; border-radius: 4px; padding: 10px 14px 12px; gap: 4px;
  transition: border-color 120ms ease-out; }
[class*="st-key-case-card-"]:hover { border-color: #94A3B8; }
[class*="st-key-case-card-on-"] { border-color: #67E8F9;
  box-shadow: inset 3px 0 0 #67E8F9; }
[class*="st-key-case-card-"] [class*="st-key-case-btn-"],
[class*="st-key-case-card-"] [class*="st-key-case-btn-"] * { position: static; }
[class*="st-key-case-btn-"] button { justify-content: flex-start; padding: 0; min-height: 0;
  border: 0; background: transparent; text-align: left; }
[class*="st-key-case-btn-"] button > div { width: 100%; justify-content: flex-start; }
[class*="st-key-case-btn-"] button p { font-size: 16px; font-weight: 600; color: #E2E8F0;
  text-align: left; width: 100%; }
[class*="st-key-case-btn-"] button::after { content: ""; position: absolute; inset: 0;
  border-radius: 4px; }
/* The card's text lets clicks through to the stretched button below it. Streamlit pulls each
   Markdown block up by 1rem at its bottom, which ate the card's bottom padding and clipped the
   last line ("Showing this case"); the card body keeps its full height instead (slice 2, A1). */
[class*="st-key-case-body-"] { pointer-events: none; }
[class*="st-key-case-body-"] [data-testid="stMarkdownContainer"] { margin-bottom: 0; }
[class*="st-key-case-btn-"] button:focus-visible { outline: none; }
[class*="st-key-case-card-"]:has(button:focus-visible) { outline: 2px solid #67E8F9;
  outline-offset: 2px; }
/* The verdict bar: the hero, then the verdict line beside the Expert view toggle. */
.st-key-verdict-bar { gap: 0.75rem; }
.st-key-verdict-row { gap: 8px 16px; align-items: center; flex-wrap: wrap;
  margin-top: 6px; }
.st-key-verdict-line { flex: 1 1 0; min-width: min(100%, 18rem); }
/* The story's HUD markup. */
.hud-case p { margin: 0; }
.hud .hud-case-codes { display: flex; flex-wrap: wrap; gap: 2px 6px; align-items: baseline;
  margin: 2px 0 6px; }
.hud .hud-case-codes .hud-code { font-size: 12px; }
.hud-case-arrow { color: #94A3B8; }
.hud .hud-case-desc { font-size: 13px; line-height: 1.45; color: #E2E8F0; }
.hud .hud-case-on { font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 600;
  font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: #67E8F9;
  margin-top: 6px; }
.hud.hud-verdict { font-size: 16px; line-height: 1.5; font-weight: 500; margin: 0; }
.hud.hud-analogy { background: #0F1720; border: 1px solid #1E2A36;
  border-left: 2px solid #A8A29E; border-radius: 4px; padding: 8px 12px; margin: 0; }
.hud.hud-analogy .hud-lbl { display: block; margin-bottom: 2px; }
.hud.hud-facts ul { margin: 4px 0 0; padding-left: 18px; }
.hud.hud-facts li { margin: 0 0 3px; font-size: 14px; line-height: 1.45; }
.hud.hud-metric { font-family: 'IBM Plex Mono', monospace; font-size: 13px; margin: 0; }
/* Steps: native expanders; a 200 ms reveal when one opens (never under reduced motion). */
[class*="st-key-step-"] summary p { font-size: 15px; line-height: 1.4; }
@media (prefers-reduced-motion: no-preference) {
  @keyframes story-open { from { opacity: 0; transform: translateY(-4px); } }
  [class*="st-key-step-"] details[open] > :not(summary) {
    animation: story-open 200ms ease-out; }
}
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def md(text) -> str:
    """Text for a Markdown context (a label, a heading): every Markdown and directive mark
    backslash-escaped, line breaks as spaces."""
    flat = " ".join(str(text).split())
    return "".join("\\" + c if c in _MD else c for c in flat)


def code_html(text) -> str:
    """Fixed copy as HTML: every character escaped, `backtick` spans as <code>."""
    parts = str(text).split("`")
    if len(parts) % 2 == 0:  # an unpaired backtick: no code spans
        return esc(text)
    return "".join(
        f"<code>{esc(part)}</code>" if i % 2 else esc(part)
        for i, part in enumerate(parts)
    )


def expert() -> bool:
    return bool(st.session_state.get(EXPERT, False))


def _set_expert() -> None:
    st.session_state[EXPERT] = True
    st.session_state[EXPERT_WIDGET] = True


def _sync_expert() -> None:
    st.session_state[EXPERT] = bool(st.session_state[EXPERT_WIDGET])


def _select(key: str) -> None:
    st.session_state[CASE] = key


# -- the page --------------------------------------------------------------------------------
def header() -> None:
    with st.container(key="story-header"):
        st.title(C.APP_NAME)
        with st.container(key="story-tagline"):
            st.markdown(md(C.TAGLINE))
        with st.container(key="story-why"):
            st.markdown(
                f"**{md(C.WHY_LABEL)}:** {md(C.WHY_TEXT)} [{C.WHY_LINK}]({C.WHY_URL})"
            )


def case_runs(root: Path) -> list[tuple[C.Case, R.RecordedRun | None]]:
    """Each case's bundled run, or None when it is not in the bundle (inside `root` only)."""
    root = Path(root).resolve()
    out = []
    for case in C.CASES:
        path = (root / case.run).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            out.append((case, None))
            continue
        ok = path.is_dir() and (path / "agent_report.json").is_file()
        out.append((case, R.RecordedRun(path, case.run, R.AGENT) if ok else None))
    return out


def card_codes(run: R.RecordedRun) -> list[str] | None:
    """The case's outcome codes from its own verified files (the original's, then the
    executed revision's); None when its bundle does not verify."""
    report = A.read_json(run.path / "agent_report.json")
    checks = RS.verification(run.path, report, R.AGENT)
    if not checks or not R.intact(checks) or report is None:
        return None
    verified = H.verified_paths(checks)
    original = H.verified_json(run.path, "original/outcome.json", verified) or {}
    codes = [original.get("outcome")] if original.get("outcome") else []
    chosen = H.executed_candidate(run.path, report, verified)
    if chosen is not None:
        cand = H.verified_json(run.path, f"{chosen[0]}/outcome.json", verified) or {}
        if cand.get("outcome"):
            codes.append(cand["outcome"])
    return codes


def _card_html(case: C.Case, codes: list[str] | None, bundled: bool, on: bool) -> str:
    if not bundled:
        state = f'<p class="hud-case-codes"><b class="hud-code hud-c-stone">{esc(C.CARD_MISSING)}</b></p>'
    elif codes is None:
        state = f'<p class="hud-case-codes"><b class="hud-code hud-c-red">{esc(C.CARD_CHANGED)}</b></p>'
    else:
        arrow = ' <span class="hud-case-arrow" aria-hidden="true">→</span> '
        state = (
            '<p class="hud-case-codes">'
            + arrow.join(H._code(c) for c in codes)
            + "</p>"
        )
    showing = f'<p class="hud-case-on">{esc(C.CARD_SHOWING)}</p>' if on else ""
    return (
        f'<div class="hud hud-case">{state}'
        f'<p class="hud-case-desc">{esc(case.description)}</p>{showing}</div>'
    )


def esc(value) -> str:
    return H.esc(value)


def case_cards(runs: list[tuple[C.Case, R.RecordedRun | None]]) -> str:
    """The row of case cards; returns the selected case's key (the first by default)."""
    keys = [case.key for case, _ in runs]
    selected = st.session_state.get(CASE)
    if selected not in keys:
        selected = keys[0]
        st.session_state[CASE] = selected
    with st.container(key="story-cases"):
        cols = st.columns(len(runs), gap="small")
        for col, (case, run) in zip(cols, runs, strict=True):
            on = case.key == selected
            codes = card_codes(run) if run is not None else None
            with col, st.container(key=f"case-card-{'on-' if on else ''}{case.key}"):
                st.button(
                    case.title,
                    key=f"case-btn-{case.key}",
                    on_click=_select,
                    args=(case.key,),
                    type="tertiary",
                    width="stretch",
                )
                with st.container(key=f"case-body-{case.key}"):
                    st.markdown(
                        _card_html(case, codes, run is not None, on),
                        unsafe_allow_html=True,
                    )
    return selected


def case_notes(run: R.RecordedRun) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """A bundled case's banner notes, (Expert view, plain): the replay disclosure, and the
    HAR citation for HAR runs (in plain mode without its repository file reference)."""
    har = run.project.startswith("har_")
    return (
        (C.REPLAY_DISCLOSURE, *((C.HAR_CITATION,) if har else ())),
        (C.REPLAY_DISCLOSURE, *((C.HAR_CITATION_PLAIN,) if har else ())),
    )


def overview(root: Path | None = None) -> None:
    """The Overview & Cases page: the header, the case cards and the selected case, from
    the recorded bundle (`BUNDLE_ROOT` unless `root` is given)."""
    with st.container(key="story-page"):
        header()
        default = Path(os.environ.get(CASES_ENV) or BUNDLE_ROOT)
        runs = case_runs(root if root is not None else default)
        selected = case_cards(runs)
        run = {case.key: r for case, r in runs}[selected]
        if run is None:
            return
        notes, plain_notes = case_notes(run)
        RS.case_page(run, bundled=True, notes=notes, plain_notes=plain_notes)


# -- the banner ---------------------------------------------------------------------------------
def model_name(report: dict | None) -> str:
    """Who proposed revisions: the model's short name for a live run (the model ID when no
    short name is fixed for it), else the scripted fixture reply."""
    if not isinstance(report, dict) or report.get("live") is not True:
        return C.FIXTURE_PROPOSER
    model = report.get("model_id")
    return (
        C.MODEL_NAMES.get(model, model) if isinstance(model, str) else C.UNNAMED_MODEL
    )


def banner_text(report: dict | None, finished_utc: str | None) -> str:
    date = (finished_utc or "")[:10] or C.NO_DATE
    if report is None:
        return C.BANNER_AUDIT.format(date=date)
    if report.get("live") is True:
        return C.BANNER_LIVE.format(model=model_name(report), date=date)
    return C.BANNER_FIXTURE.format(date=date)


def banner(
    report: dict | None,
    label: str,
    finished_utc: str | None,
    notes: tuple[str, ...],
    plain_notes: tuple[str, ...],
) -> None:
    """Expert view: the full recorded banner. Plain: one line from the report (recorded,
    the model, the finish date, not re-run here) and the plain notes."""
    if expert():
        V.recorded_banner(report, label, finished_utc, notes)
        return
    with st.container(key="banner", border=True):
        with st.container(key="recorded-label"):
            st.markdown(
                f":blue-badge[{md(C.BANNER_TAG)}] {md(banner_text(report, finished_utc))}"
            )
        for note in plain_notes:
            st.caption(note)  # fixed copy, as in the Expert banner


# -- facts (read once from the verified files) ----------------------------------------------------
@dataclass
class Facts:
    report: dict
    verified: frozenset[str]
    model: str
    claim: object | None = None  # catalogue.ClaimView
    claim_rel: str | None = None
    claim_problem: str | None = None
    orig_status: dict[str, str | None] = field(default_factory=dict)
    cand_status: dict[str, str | None] = field(default_factory=dict)
    cand_outcome: dict | None = None
    orig_outcome: dict | None = None
    cand_execution: dict | None = None
    approvals: list[str] = field(default_factory=list)
    approval_events: list[dict] = field(default_factory=list)
    executions: list[str] = field(default_factory=list)
    exec_sources: list[str] = field(default_factory=list)
    typed: int = 0
    untyped: int = 0
    script: int = 0  # approvals by the T-09 audit script (its recorded approval reason)
    ran_isolated: int = 0  # evaluated runs (the original first) in the isolated runner
    original_runner: str | None = None
    not_here: int = 0


def _docker_facts(execution: dict) -> list[str]:
    """Isolation facts the recorded docker_args state: no network, a non-root user, a
    read-only filesystem (only those recorded)."""
    args = execution.get("docker_args")
    if not isinstance(args, list):
        return []
    args = [str(a) for a in args]
    facts = []

    def value(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == flag and i + 1 < len(args):
                return args[i + 1]
            if a.startswith(flag + "="):
                return a.split("=", 1)[1]
        return None

    if value("--network") == "none":
        facts.append(C.EXEC_FACTS["network"])
    user = value("--user")
    if user is not None and user.split(":", 1)[0] not in ("0", "root", ""):
        facts.append(C.EXEC_FACTS["user"])
    if "--read-only" in args:
        facts.append(C.EXEC_FACTS["read_only"])
    return facts


def _execution_line(who: str, execution: dict) -> tuple[str, bool]:
    """(the sentence, ran in the isolated runner)."""
    runner, status = execution.get("runner"), execution.get("status")
    if runner == "docker_isolated" and status == "completed":
        facts = _docker_facts(execution)
        line = C.EXEC_ISOLATED.format(who=who)
        if facts:
            joined = (
                facts[0]
                if len(facts) == 1
                else ", ".join(facts[:-1]) + C.AND + facts[-1]
            )
            line += C.EXEC_WITH.format(facts=joined)
        line += "."
        if execution.get("container_removed") is True:
            line += C.EXEC_REMOVED
        return line, True
    return (
        C.EXEC_OTHER.format(
            who=who,
            runner=runner or H.NOT_RECORDED,
            status=status or H.NOT_RECORDED,
        ),
        False,
    )


def _revision_of(report: dict, candidate_hash) -> int | None:
    for p in report.get("proposals") or []:
        if (
            isinstance(p, dict)
            and candidate_hash
            and p.get("candidate_hash") == candidate_hash
        ):
            n = p.get("revision")
            return n if isinstance(n, int) and not isinstance(n, bool) else None
    return None


def _who(report: dict, kind, candidate_hash) -> str:
    if kind == "original":
        return C.WHO_ORIGINAL
    n = _revision_of(report, candidate_hash)
    return C.WHO_REVISION.format(n=n) if n is not None else C.WHO_REVISION_UNKNOWN


def facts(run: R.RecordedRun, report: dict, checks: list, hud: H.Hud) -> Facts:
    verified = H.verified_paths(checks)
    f = Facts(report=report, verified=verified, model=model_name(report))
    source = R.claim_source(run)
    if source is not None:
        rel = source.relative_to(run.path).as_posix()
        if rel in verified:
            try:
                f.claim, f.claim_rel = R.read_claim(source), rel
            except Exception:  # noqa: BLE001 - shown as unreadable, never a result
                f.claim_problem = C.MANIFEST_UNREADABLE
    f.orig_outcome = H.verified_json(run.path, "original/outcome.json", verified)
    f.orig_status = {r.assertion_id: r.original for r in hud.matrix if r.original}
    if hud.cand_base is not None:
        f.cand_status = {r.assertion_id: r.candidate for r in hud.matrix}
        f.cand_outcome = H.verified_json(
            run.path, f"{hud.cand_base}/outcome.json", verified
        )
        f.cand_execution = H.verified_json(
            run.path, f"{hud.cand_base}/execution.json", verified
        )
    # Approvals: from the run's own verified log.
    events = A.read_log(run.path) if "agent_log.jsonl" in verified else []
    for e in events:
        if e.get("event") != "approval":
            continue
        f.approval_events.append(e)
        who = _who(report, e.get("kind"), e.get("candidate_hash"))
        if e.get("decision") == "approved" and e.get("approver_reason") == "confirmed":
            f.typed += 1
            f.approvals.append(C.APPROVED_TYPED.format(who=who))
        elif (
            e.get("decision") == "approved"
            and e.get("approver_reason") in SCRIPT_REASONS
        ):
            f.script += 1
            f.approvals.append(C.APPROVED_SCRIPT.format(who=who))
        elif e.get("decision") == "approved":
            f.untyped += 1
            f.approvals.append(C.APPROVED_UNTYPED.format(who=who))
        else:
            f.approvals.append(C.NOT_APPROVED.format(who=who))
    # Sealed runs: the original, then each evaluated candidate, from their execution.json.
    original = H.verified_json(run.path, "original/execution.json", verified)
    if isinstance(original, dict):
        line, isolated = _execution_line(C.WHO_ORIGINAL, original)
        f.executions.append(line)
        f.exec_sources.append(C.EXEC_SOURCE.format(sub="original"))
        f.ran_isolated += isolated
        f.original_runner = original.get("runner")
    comp = report.get("comparison") or {}
    for i, c in enumerate(comp.get("candidates") or [], start=1):
        sub = R.candidate_subfolder(c, i) if isinstance(c, dict) else None
        ex = (
            H.verified_json(run.path, f"{sub}/execution.json", verified)
            if sub
            else None
        )
        if not isinstance(ex, dict):
            continue
        who = _who(report, "candidate", ex.get("candidate_hash"))
        line, isolated = _execution_line(who, ex)
        f.executions.append(line)
        f.exec_sources.append(C.EXEC_SOURCE.format(sub=sub))
        f.ran_isolated += isolated
    for p in report.get("proposals") or []:
        if isinstance(p, dict) and p.get("outcome") == "not_executed_here":
            f.not_here += 1
            n = p.get("revision")
            who = (
                C.WHO_REVISION.format(n=n)
                if isinstance(n, int)
                else C.WHO_REVISION_UNKNOWN
            )
            f.executions.append(C.NOT_EXECUTED_HERE.format(who=who))
    return f


# -- the verdict line and the step summaries (deterministic) ----------------------------------------
def _all_pass(statuses: dict) -> bool:
    return bool(statuses) and all(s == "PASS" for s in statuses.values())


def verdict(hud: H.Hud, f: Facts) -> list[str]:
    out = []
    first = C.VERDICT_ORIGINAL.get(hud.original.code or "")
    if first:
        out.append(first)
    proposals = [p for p in f.report.get("proposals") or [] if isinstance(p, dict)]
    if hud.candidate is not None:
        ex = f.cand_execution or {}
        isolated = (
            ex.get("runner") == "docker_isolated" and ex.get("status") == "completed"
        )
        code = hud.candidate.code or H.NOT_RECORDED
        if isolated and code == "NO_VIOLATION_FOUND" and _all_pass(f.cand_status):
            out.append(C.VERDICT_ALL_PASS.format(model=f.model))
        elif isolated:
            out.append(C.VERDICT_CANDIDATE.format(model=f.model, outcome=code))
        else:
            out.append(
                C.VERDICT_CANDIDATE_RUNNER.format(
                    model=f.model,
                    runner=ex.get("runner") or H.NOT_RECORDED,
                    outcome=code,
                )
            )
    elif proposals:
        out.append(
            C.plural(
                C.VERDICT_NONE_EXECUTED, len(proposals), n=len(proposals), model=f.model
            )
        )
    else:
        out.append(C.VERDICT_NO_PROPOSAL)
    observed = hud.observed_cand if hud.candidate is not None else hud.observed_orig
    statuses = f.cand_status if hud.candidate is not None else f.orig_status
    n = len(H.conditional(observed, statuses))
    if n:
        out.append(C.plural(C.VERDICT_CONDITIONAL, n, n=n))
    return out


def summaries(hud: H.Hud, f: Facts, checks: list) -> dict[int, str]:
    out = {}
    # 1. the claim
    if f.claim is not None and getattr(f.claim, "statement", None):
        out[1] = f.claim.statement
    else:
        out[1] = f.claim_problem or C.NO_MANIFEST
    # 2. the leak (the original's statuses)
    statuses = list(f.orig_status.values())
    n, k = len(statuses), statuses.count("FAIL")
    na, err = statuses.count("NOT_ASSESSED"), statuses.count("ERROR")
    if k:
        line = C.LEAK_FAILS.format(k=k, n=n)
    elif n and statuses.count("PASS") == n:
        line = C.LEAK_ALL_PASS.format(n=n)
    else:
        line = C.LEAK_NONE_FAIL
    if na:
        line += "; " + C.plural(C.LEAK_NOT_ASSESSED, na, m=na)
    if err:
        line += "; " + C.plural(C.LEAK_ERROR, err, m=err)
    out[2] = line
    # 3. the AI's fix
    proposals = [p for p in f.report.get("proposals") or [] if isinstance(p, dict)]
    if not proposals:
        out[3] = C.NO_PROPOSAL
    else:
        counts: dict[str, int] = {}
        for p in proposals:
            code = p.get("outcome")
            key = code if code in C.PROPOSAL_PARTS else "other"
            counts[key] = counts.get(key, 0) + 1
        parts = ", ".join(
            C.PROPOSAL_PARTS[key].format(k=counts[key])
            for key in C.PROPOSAL_PARTS
            if counts.get(key)
        )
        out[3] = C.plural(
            C.PROPOSALS_SUMMARY,
            len(proposals),
            model=f.model,
            n=len(proposals),
            parts=parts,
        )
    # 4. approval and the sealed run
    if script_only(f):
        out[4] = C.SCRIPT_ONLY
        out[5] = _proof(hud, checks)
        return out
    untyped = f.untyped + f.script
    if f.typed and untyped:
        approval = C.MIXED_APPROVALS.format(t=f.typed, u=untyped)
    elif f.typed:
        approval = C.plural(C.TYPED_APPROVALS, f.typed, n=f.typed)
    elif untyped:
        approval = C.UNTYPED_ONLY
    else:
        approval = C.NO_APPROVAL
    if f.original_runner is None:
        ran = C.NOT_RUN
    elif f.original_runner != "docker_isolated":
        ran = C.RAN_OTHER.format(runner=f.original_runner)
    elif f.ran_isolated > 1:
        ran = C.plural(C.RAN_BOTH, f.ran_isolated - 1, k=f.ran_isolated - 1)
    else:
        ran = C.RAN_ORIGINAL
    line = f"{approval}; {ran}"
    if f.not_here:
        line += C.plural(C.NOT_HERE_SUFFIX, f.not_here, n=f.not_here)
    out[4] = line
    out[5] = _proof(hud, checks)
    return out


def script_only(f: Facts) -> bool:
    """Every recorded approval was the T-09 audit script's (by its recorded approval reason),
    no model proposed anything, and only the original ran, in the isolated Docker runner: no
    AI agent took part."""
    return (
        f.script > 0
        and not f.typed
        and not f.untyped
        and len(f.approvals) == f.script
        and not (f.report.get("proposals") or [])
        and f.report.get("live") is not True
        and f.original_runner == "docker_isolated"
        and f.ran_isolated == 1
        and not f.not_here
    )


def _proof(hud: H.Hud, checks: list) -> str:
    """Step 5's summary: the checks that moved, and the integrity count."""
    count = H.integrity_count(checks)
    v, t = count.total - count.differ, count.total
    if hud.candidate is not None:
        moved = sum(
            1 for r in hud.matrix if r.original == "FAIL" and r.candidate == "PASS"
        )
        return C.plural(C.PROOF_MOVED, moved, k=moved, v=v, t=t)
    return C.PROOF_INTACT.format(v=v, t=t)


# -- the verdict bar and the steps ------------------------------------------------------------------
def case(
    run: R.RecordedRun,
    report: dict | None,
    checks: list,
    *,
    bundled: bool,
    played: bool,
) -> None:
    """A verified case (called by `results.case_page` after the gate only)."""
    hud = (
        H.build(run.path, report, checks, run.label, bundled=bundled)
        if report is not None
        else None
    )
    if hud is None:
        st.markdown(md(C.NO_OUTCOME))
        V.integrity(checks, True)
        return
    plain = not expert()
    f = facts(run, report, checks, hud)
    verdict_bar(hud, f, played=played, plain=plain)
    tamper_section(run, checks, plain)
    told = summaries(hud, f, checks)
    bodies = {
        1: lambda: step_claim(f, plain),
        2: lambda: step_leak(run, hud, f, plain, played),
        3: lambda: step_fix(run, f, plain),
        4: lambda: step_approval(f, plain),
        5: lambda: step_proof(run, hud, f, checks, plain, played),
    }
    with st.container(key="story-steps"):
        for n, body in bodies.items():
            label = C.STEP_LABEL.format(
                n=n, title=md(C.STEP_TITLES[n]), summary=md(told[n])
            )
            with st.expander(label, expanded=n == 2, key=f"step-{n}"):
                body()


def verdict_bar(hud: H.Hud, f: Facts, *, played: bool, plain: bool) -> None:
    with st.container(key="verdict-bar"):
        with st.container(key="hud-hero"):
            st.markdown(H.hero(hud, played=played, plain=plain), unsafe_allow_html=True)
        with st.container(
            key="verdict-row", horizontal=True, vertical_alignment="center"
        ):
            with st.container(key="verdict-line"):
                st.markdown(
                    '<p class="hud hud-verdict">'
                    + " ".join(esc(s) for s in verdict(hud, f))
                    + "</p>",
                    unsafe_allow_html=True,
                )
            expert_toggle()


def expert_toggle() -> None:
    """The one session-wide Expert view toggle (the same setting on every page)."""
    if EXPERT_WIDGET not in st.session_state:
        st.session_state[EXPERT_WIDGET] = expert()
    st.toggle(
        C.EXPERT_TOGGLE,
        key=EXPERT_WIDGET,
        on_change=_sync_expert,
        help=C.EXPERT_HELP,
        width="content",
    )


# -- the tamper demo (slice 2, part D; atlas.ui.tamper) ---------------------------------------------
def _limit() -> T.SessionLimit:
    limit = st.session_state.get(TAMPER_LIMIT)
    if not isinstance(limit, T.SessionLimit):
        limit = st.session_state[TAMPER_LIMIT] = T.SessionLimit()
    return limit


def attempt(run: R.RecordedRun, rel: str) -> object:
    """One demo under the session's limits: a `tamper.Demo`, or a fixed message (str)."""
    limit = _limit()
    refusal = limit.acquire()
    if refusal is not None:
        return refusal
    try:
        return T.run_demo(run.path, rel)
    except T.Refused as exc:
        return exc.message
    except T.OriginalChanged:
        _log.error(TAMPER_EVENT)
        return C.TAMPER_ORIGINAL_CHANGED
    except Exception:  # noqa: BLE001 - a fixed message only; the copy is already deleted
        _log.error(TAMPER_EVENT)
        return C.TAMPER_FAILED
    finally:
        limit.release()


def _byte_name(value: int) -> str:
    return C.TAMPER_BYTE_NAMES.get(value) or C.TAMPER_BYTE_OTHER.format(value=value)


def tamper_result(demo: T.Demo, plain: bool) -> None:
    bad = demo.differing
    t = len(demo.checks)
    items = ", ".join(dict.fromkeys(T.label(c.item) if plain else c.item for c in bad))
    head = (
        C.plural(C.TAMPER_RESULT, len(bad), d=len(bad), t=t, items=items)
        if bad
        else C.TAMPER_NOT_DETECTED.format(t=t)
    )
    with st.container(key="tamper-result"):
        st.markdown(
            f":red-badge[{md(C.EVIDENCE_CHANGED_CODE)}] **{md(head)}**"
            if bad
            else f":orange-badge[{md(C.EVIDENCE_CHANGED_CODE)}] **{md(head)}**"
        )
        with st.container(key="tamper-statement"):
            st.markdown(md(C.TAMPER_STATEMENT))
        if plain:
            byte = C.TAMPER_BYTE.format(
                label=T.label(demo.rel),
                old=_byte_name(demo.old),
                new=_byte_name(demo.new),
            )
        else:
            byte = C.TAMPER_BYTE_EXPERT.format(
                offset=demo.offset, rel=demo.rel, old=demo.old, new=demo.new
            )
        st.caption(byte if not plain else md(byte))
        count = H.integrity_count(list(demo.original_checks))
        with st.container(key="tamper-original"):
            st.caption(
                md(
                    C.TAMPER_ORIGINAL_OK.format(
                        v=count.total - count.differ,
                        t=count.total,
                        f=demo.original_files,
                    )
                )
                + " "
                + md(C.TAMPER_DELETED)
            )
        if not plain and bad:
            with st.container(key="tamper-table"):
                st.caption(md(C.TAMPER_TABLE_HEAD))
                st.table(
                    pd.DataFrame(
                        [
                            {
                                "result": c.status,
                                "item": c.item,
                                "recorded": c.recorded or "",
                                "recomputed now": c.recomputed or "",
                            }
                            for c in bad
                        ]
                    ),
                    hide_index=True,
                )


def tamper_section(run: R.RecordedRun, checks: list, plain: bool) -> None:
    """Below the verdict bar: pick one of the run's fixed files, change one byte in a
    temporary copy, run the real check on the copy, show its result (atlas.ui.tamper)."""
    files = T.options(checks)
    if not files:
        return
    tag = H.run_hash(run.label)
    results = st.session_state.setdefault(TAMPER_RESULTS, {})
    with st.container(key="tamper", border=True):
        st.markdown(f"**{md(C.TAMPER_HEAD)}**")
        st.caption(md(C.TAMPER_INTRO))
        with st.container(
            key="tamper-controls", horizontal=True, vertical_alignment="bottom"
        ):
            rel = st.selectbox(
                C.TAMPER_PICK,
                files,
                format_func=lambda r: T.label(r) if plain else r,
                key=f"tamper-file-{tag}",
            )
            clicked = st.button(C.TAMPER_BUTTON, key=f"tamper-go-{tag}")
        if clicked:
            results[run.label] = attempt(run, rel)
        st.caption(md(C.TAMPER_LIMITS.format(n=T.PER_HOUR, mb=T.MAX_MB)))
        shown = results.get(run.label)
        if isinstance(shown, T.Demo):
            tamper_result(shown, plain)
        elif isinstance(shown, str):
            with st.container(key="tamper-refused"):
                st.warning(md(shown), icon=":material/block:")


def expert_line(n: int, label: str = C.SHOW_EXPERT) -> None:
    st.button(label, key=f"expert-on-{n}", type="tertiary", on_click=_set_expert)


def step_claim(f: Facts, plain: bool) -> None:
    with st.container(key="claim-statement"):
        if f.claim is not None and getattr(f.claim, "statement", None):
            st.caption(md(C.CLAIM_INTRO))
            st.markdown(f"#### {md(f.claim.statement)}")
        else:
            st.markdown(md(f.claim_problem or C.NO_MANIFEST))
    if plain:
        expert_line(1)
    elif f.claim is not None:
        st.caption(C.CLAIM_SOURCE.format(path=f.claim_rel))
        V.claim_fields(f.claim)


def _analogies(f: Facts) -> list[str]:
    return [
        text
        for aids, text in C.ANALOGIES
        if any(f.orig_status.get(aid) == "FAIL" for aid in aids)
    ]


def step_leak(
    run: R.RecordedRun, hud: H.Hud, f: Facts, plain: bool, played: bool
) -> None:
    with st.container(key="hud-evidence"):
        st.markdown(
            H.evidence(hud, played=played, plain=plain, parts=("leak", "flow")),
            unsafe_allow_html=True,
        )
    for i, text in enumerate(_analogies(f), start=1):
        with st.container(key=f"analogy-{i}"):
            st.markdown(
                '<p class="hud hud-analogy"><span class="hud-lbl">'
                f"{esc(C.ANALOGY_LABEL)}</span> {esc(text)}</p>",
                unsafe_allow_html=True,
            )
    if plain:
        expert_line(2, C.SHOW_EVIDENCE)
        return
    drill = H.Ids(hud.ids.runhash, "d")
    for scope, inspect, statuses in (
        ("orig", hud.inspect_orig, f.orig_status),
        ("cand", hud.inspect_cand, f.cand_status),
    ):
        rows = [r for r in hud.matrix if statuses.get(r.assertion_id) in H.INSPECTED]
        if not rows or not inspect:
            continue
        side = C.SIDE_ORIGINAL if scope == "orig" else hud.cand_base
        source = (
            "original/outcome.json"
            if scope == "orig"
            else f"{hud.cand_base}/outcome.json"
        )
        with st.container(key=f"story-drill-{scope}"):
            st.markdown(
                '<div class="hud">'
                + H.matrix_column(
                    rows,
                    scope,
                    source,
                    played=True,
                    inspect=inspect,
                    ids=drill,
                    observed=hud.observed_orig
                    if scope == "orig"
                    else hud.observed_cand,
                    title=C.DRILLDOWN_TITLE.format(side=side),
                )
                + "</div>",
                unsafe_allow_html=True,
            )
    RS.finding_section(run.path, f.report, RS.AGENT, (), None, C.ORIGINAL_TITLE)


def step_fix(run: R.RecordedRun, f: Facts, plain: bool) -> None:
    views = A.proposals(run.path, f.report)
    if not plain:
        RS.revision_section(run.path, f.report, RS.AGENT)
        return
    if not views:
        with st.container(key="no-proposal"):
            st.markdown(md(C.NO_PROPOSAL))
        expert_line(3)
        return
    rationale = [
        t
        for t in f.report.get("model_text") or []
        if t.get("kind") == "patch_rationale"
    ]
    for i, v in enumerate(views, start=1):
        r = v.record
        n = r.get("revision") if isinstance(r.get("revision"), int) else i
        code = r.get("outcome")
        outcome = C.PROPOSAL_OUTCOME.get(code) or C.PROPOSAL_UNKNOWN.format(code=code)
        with st.container(key=f"story-proposal-{i}", border=True):
            st.markdown(f"**{md(C.PROPOSAL_HEAD.format(n=n))}** · {md(outcome)}")
            with st.container(key=f"model-story-diff-{i}"):
                st.markdown(H.MODEL_BADGE_MARKDOWN)
                st.caption(md(C.PROPOSED_BY.format(model=f.model)))
                if v.diff_text is not None:
                    st.caption(md(C.DIFF_CAPTION))
                    with st.container(key=f"scroll-story-diff-{i}"):
                        st.code(inert(v.diff_text), language="diff")
                else:
                    st.caption(md(C.NO_DIFF))
            if i <= len(rationale):
                V.model_text(
                    rationale[i - 1]["text"],
                    rationale[i - 1]["label"],
                    f"model-story-rationale-{i}",
                )
    expert_line(3)


def _fact_list(lines: list[str], key: str, head: str) -> None:
    if not lines:
        return
    with st.container(key=key):
        st.markdown(
            f'<div class="hud hud-facts"><span class="hud-lbl">{esc(head)}</span><ul>'
            + "".join(f"<li>{esc(x)}</li>" for x in lines)
            + "</ul></div>",
            unsafe_allow_html=True,
        )


def step_approval(f: Facts, plain: bool) -> None:
    _fact_list(f.approvals, "story-approvals", C.APPROVALS_HEAD)
    _fact_list(f.executions, "story-executions", C.EXECUTIONS_HEAD)
    if plain:
        expert_line(4)
        return
    if f.approval_events:
        with st.container(key="story-approval-table"):
            st.table(
                pd.DataFrame(
                    [
                        {
                            "kind": e.get("kind"),
                            "decision": e.get("decision"),
                            "approver reason": e.get("approver_reason") or "",
                            "code hash": e.get("candidate_hash"),
                        }
                        for e in f.approval_events
                    ]
                ),
                hide_index=True,
            )
    st.markdown(
        '<div class="hud">'
        + "".join(f'<div class="hud-src">{esc(x)}</div>' for x in f.exec_sources)
        + "</div>",
        unsafe_allow_html=True,
    )


def step_proof(
    run: R.RecordedRun,
    hud: H.Hud,
    f: Facts,
    checks: list,
    plain: bool,
    played: bool,
) -> None:
    with st.container(key="story-matrix"):
        st.markdown(
            H.evidence(
                hud,
                played=played,
                plain=plain,
                parts=("matrix",),
                ids=H.Ids(hud.ids.runhash, "p"),
            ),
            unsafe_allow_html=True,
        )
    metric = H.metric_text(f.orig_outcome, f.cand_outcome)
    if metric:
        with st.container(key="story-metric"):
            st.markdown(
                f'<p class="hud hud-metric">{esc(metric)}</p>', unsafe_allow_html=True
            )
    if plain:
        with st.container(key="story-track"):
            st.markdown(
                H.track(f.report, H.Ids(hud.ids.runhash, "p"), plain=True),
                unsafe_allow_html=True,
            )
    else:
        RS.analysis_section(
            run.path,
            f.report,
            RS.AGENT,
            R.logged_decisions(A.read_log(run.path)),
            None,
            hud,
        )
    lines = H.briefing_lines(run.path, f.report, checks, H.load_labels())
    if lines:
        with st.container(key="hud-briefing"):
            st.markdown(H.briefing(lines, hud.ids, plain=plain), unsafe_allow_html=True)
    V.integrity(checks, True, plain=plain)
    if plain:
        expert_line(5)
        return
    RS.comparison_section(run.path, f.report, RS.AGENT)
    RS.trust_section(run.path, f.report)
