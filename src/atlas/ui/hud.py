"""The HUD components of the recorded-run viewer (docs/UI_DESIGN_HUD.md §4–§6).

Builders read values from a recorded run's own files, and only from files whose relative path
`recorded.verify` reported as matching (`verified_paths`); `build` returns None unless the run is
intact. Renderers are pure: values in, one HTML/SVG string out. Streamlit only places the string
(`st.markdown(..., unsafe_allow_html=True)`; the 1.66 `st.html` sanitiser removes SVG). A missing
file or field renders "not recorded"; nothing is inferred. Every string taken from a file is
escaped by `esc`, and each block is a single line, so Markdown never leaves the HTML block.

Motion is CSS only. Animated markup carries the `hud-anim` class and `hud-a-*` classes; with
`played=True` none of them is emitted, so a rerun renders the final state. Every element's resting
state is its final state; animations only start from a blank or unlit frame.
"""

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from atlas.ui import artifacts as A
from atlas.ui import recorded as R
from atlas.ui.catalogue import ROOT

# -- tokens (docs/UI_DESIGN_HUD.md §2.1; .streamlit/config.toml uses the same values) ------------
BG = "#0A0F14"
PANEL = "#0F1720"
HAIRLINE = "#1E2A36"
TEXT = "#E2E8F0"
MUTED = "#94A3B8"
ACCENT = "#67E8F9"
RED = "#F87171"
GREEN = "#4ADE80"
AMBER = "#FBBF24"
VIOLET = "#C084FC"
STONE = "#A8A29E"
COLORS = {"red": RED, "green": GREEN, "amber": AMBER, "violet": VIOLET, "stone": STONE}
TONE = {
    "VIOLATION_FOUND": "red",
    "FAIL": "red",
    "NO_VIOLATION_FOUND": "green",
    "PASS": "green",
    "INCONCLUSIVE": "amber",
    "NOT_ASSESSED": "amber",
    "BUDGET_EXHAUSTED": "amber",
    "NEEDS_INPUT": "amber",
    "ERROR": "violet",
    "NOT_SUPPORTED": "stone",
}
GLOW = {  # the reticle's one subtle glow, per status colour
    "red": "rgba(248,113,113,0.35)",
    "green": "rgba(74,222,128,0.30)",
    "amber": "rgba(251,191,36,0.30)",
    "violet": "rgba(192,132,252,0.32)",
    "stone": "rgba(168,162,158,0.28)",
}

NOT_RECORDED = "not recorded"
LEAK_ASSERTION = "split.no_group_overlap"
FIT_ASSERTION = "fit.state_dependencies_within_fold_train"
LEAK_Y_LABEL = (
    "Groups with recorded overlap in the original (observed.overlapping_groups)"
)
BOTH, NONE_SHARED = "on both sides", "0 shared"
NO_USE = "no use listed"
TYPED_APPROVAL = "executed in the isolated Docker runner after typed approval"
MODEL_BADGE = "MODEL-WRITTEN · UNTRUSTED"

# Beats (seconds; docs/UI_DESIGN_HUD.md §5).
BEAT1_END = 0.4
BEAT2 = (0.4, 0.3)  # start, duration: changed tiles flip
BEAT3 = (0.4, 0.8)  # start, duration: leak cells light fold by fold, flow lines draw
NODE_MS = 300  # a live mission-track node that has just appeared lights once

# -- escaping ------------------------------------------------------------------------------------
# HTML specials, Markdown and Streamlit directive characters, and line breaks become character
# references: the text cannot open a tag, leave the HTML block or start Markdown, a :directive[]
# or $math$, and the browser still shows it unchanged.
_ENTITIES = {c: f"&#{ord(c)};" for c in "&<>\"'$:*_[]\\`~#|{}"}
_ENTITIES["\n"] = "&#10;"
_ENTITIES["\r"] = ""


def esc(value) -> str:
    return "".join(_ENTITIES.get(c, c) for c in str(value))


# -- IDs (docs/UI_DESIGN_HUD.md §6) ----------------------------------------------------------------
def run_hash(run_id: str) -> str:
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:8]


@dataclass(frozen=True)
class Ids:
    """`atlas-<component>-<part>-<scope>-<runhash8>-<instance>`: unique per rendered instance."""

    runhash: str
    instance: str = "h"

    def __post_init__(self):
        for value in (self.runhash, self.instance):
            if not value or not value.isascii() or not value.isalnum():
                raise ValueError("ID parts must be ASCII letters and digits")

    def __call__(self, component: str, part: str, scope: str = "run") -> str:
        return f"atlas-{component}-{part}-{scope}-{self.runhash}-{self.instance}"


def _anim(played: bool, *classes: str) -> str:
    return "" if played else " " + " ".join(("hud-anim",) + classes)


def _a(played: bool, cls: str) -> str:
    return "" if played else f" {cls}"


def _delay(played: bool, start_s: float, dur_s: float | None = None) -> str:
    if played:
        return ""
    parts = [f"animation-delay:{round(start_s * 1000)}ms"]
    if dur_s is not None:
        parts.append(f"animation-duration:{round(dur_s * 1000)}ms")
    return f' style="{";".join(parts)}"'


def _tone(code) -> str:
    return TONE.get(code, "stone")


def _code(code, *, cls: str = "") -> str:
    """A status code in its colour, always as text."""
    text = esc(code) if code else NOT_RECORDED
    tone = _tone(code) if code else "stone"
    return f'<b class="hud-code hud-c-{tone}{cls}">{text}</b>'


# -- reading verified files -----------------------------------------------------------------------
def verified_paths(checks: list[R.Check]) -> frozenset[str]:
    return frozenset(c.item for c in checks if c.ok)


def _json(run_dir: Path, rel: str, verified: frozenset[str]):
    if rel not in verified:
        return None
    return A.read_json(Path(run_dir) / rel)


def _assertion(doc, assertion_id: str) -> dict | None:
    if not isinstance(doc, dict):
        return None
    for a in doc.get("assertions") or []:
        if isinstance(a, dict) and a.get("assertion_id") == assertion_id:
            return a
    return None


def _str_or_none(value) -> str | None:
    return value if isinstance(value, str) else None


# -- data -------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Leak:
    """split.no_group_overlap of one evaluated run, and its folds."""

    base: str  # "original" or "candidates/<c>"
    recorded: bool  # the assertion is in a verified split_integrity.json
    status: str | None
    column: str | None
    groups: dict[str, list[str]] | None  # observed.overlapping_groups; None when absent
    folds: list[str] | None  # splits.json[].fold; None when absent

    @property
    def source(self) -> str:
        return f"{self.base}/checks/split_integrity.json"

    @property
    def folds_source(self) -> str:
        return f"{self.base}/splits.json"

    def columns(self) -> list[str]:
        """The folds from splits.json, then any fold the assertion lists that splits.json does not
        (shown, never dropped)."""
        cols = list(self.folds or [])
        for fold in self.groups or {}:
            if fold not in cols:
                cols.append(fold)
        return cols

    def both(self, group: str, fold: str) -> bool:
        return group in (self.groups or {}).get(fold, [])


def leak(run_dir: Path, base: str, verified: frozenset[str]) -> Leak:
    doc = _json(run_dir, f"{base}/checks/split_integrity.json", verified)
    a = _assertion(doc, LEAK_ASSERTION)
    observed = a.get("observed") if a and isinstance(a.get("observed"), dict) else {}
    raw = observed.get("overlapping_groups")
    groups = (
        {
            str(fold): [str(g) for g in listed]
            for fold, listed in raw.items()
            if isinstance(listed, list)
        }
        if isinstance(raw, dict)
        else None
    )
    splits = _json(run_dir, f"{base}/splits.json", verified)
    folds = (
        [str(s["fold"]) for s in splits if isinstance(s, dict) and "fold" in s]
        if isinstance(splits, list)
        else None
    )
    return Leak(
        base=base,
        recorded=a is not None,
        status=_str_or_none(a.get("status")) if a else None,
        column=_str_or_none(observed.get("column")),
        groups=groups,
        folds=folds,
    )


def leak_rows(original: Leak) -> list[str]:
    """Exactly the groups the original lists, in its order (first appearance, folds in file
    order)."""
    rows: list[str] = []
    for listed in (original.groups or {}).values():
        for g in listed:
            if g not in rows:
                rows.append(g)
    return rows


@dataclass(frozen=True)
class Flow:
    """fit.state_dependencies_within_fold_train of one evaluated run."""

    base: str
    recorded: bool
    status: str | None
    origins: list[dict] | None  # observed.origins; None when absent
    judged_uses: int | None
    unknown_uses: int | None  # number of observed.unknown_uses entries
    violating_folds: int | None  # number of folds in observed.violations
    folds: int | None = None  # number of folds in <base>/splits.json
    violation_entries: int | None = None  # entries listed across observed.violations

    @property
    def source(self) -> str:
        return f"{self.base}/checks/fit_provenance.json"

    @property
    def folds_source(self) -> str:
        return f"{self.base}/splits.json"


def flow(run_dir: Path, base: str, verified: frozenset[str]) -> Flow:
    doc = _json(run_dir, f"{base}/checks/fit_provenance.json", verified)
    a = _assertion(doc, FIT_ASSERTION)
    observed = a.get("observed") if a and isinstance(a.get("observed"), dict) else {}
    origins = observed.get("origins")
    unknown = observed.get("unknown_uses")
    violations = observed.get("violations")
    judged = observed.get("judged_uses")
    splits = _json(run_dir, f"{base}/splits.json", verified)
    return Flow(
        base=base,
        recorded=a is not None,
        status=_str_or_none(a.get("status")) if a else None,
        origins=[o for o in origins if isinstance(o, dict)]
        if isinstance(origins, list)
        else None,
        judged_uses=judged
        if isinstance(judged, int) and not isinstance(judged, bool)
        else None,
        unknown_uses=len(unknown) if isinstance(unknown, list) else None,
        violating_folds=len(violations) if isinstance(violations, dict) else None,
        folds=sum(1 for s in splits if isinstance(s, dict) and "fold" in s)
        if isinstance(splits, list)
        else None,
        violation_entries=sum(
            len(v) if isinstance(v, list) else 1 for v in violations.values()
        )
        if isinstance(violations, dict)
        else None,
    )


# -- 10. evidence drill-down (the inspection frame) ------------------------------------------------
INSPECTED = ("FAIL", "NOT_ASSESSED", "ERROR")
LIST_SHOWN = 6  # list items shown in a row before "and <k> more"
_DEPTH = 2  # nested objects become dotted keys this deep; deeper ones are summarised


@dataclass(frozen=True)
class Inspect:
    """One assertion's record, read from its verified check file (or, when no check file
    lists it, the evaluated run's verified outcome.json)."""

    assertion_id: str
    source: str  # the file, relative to the run
    record: dict


def inspect_records(
    run_dir: Path, base: str, statuses: list[tuple[str, str | None]], verified
) -> dict[str, Inspect]:
    """The records of an evaluated run's FAIL, NOT_ASSESSED and ERROR assertions."""
    wanted = {aid for aid, status in statuses if status in INSPECTED}
    found: dict[str, Inspect] = {}
    checks = sorted(
        p for p in verified if p.startswith(f"{base}/checks/") and p.endswith(".json")
    )
    for rel in [*checks, f"{base}/outcome.json"]:
        doc = _json(run_dir, rel, verified)
        for aid in sorted(wanted - set(found)):
            a = _assertion(doc, aid)
            if a is not None:
                found[aid] = Inspect(aid, rel, a)
    return found


def _alpha(n: int) -> str:
    """0 -> a, 25 -> z, 26 -> ba: an ID part that stays letters only (§6)."""
    out = ""
    while True:
        out = chr(97 + n % 26) + out
        n //= 26
        if n == 0:
            return out


def _scalar(value) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def _inline(value) -> str:
    """A list item on one line: scalars as they are, objects as key: value pairs with nested
    lists and objects summarised by their size."""
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if isinstance(v, list):
                parts.append(f"{k}: [{len(v)} items]")
            elif isinstance(v, dict):
                parts.append(f"{k}: {{{len(v)} keys}}")
            else:
                parts.append(f"{k}: {_scalar(v)}")
        return "{" + ", ".join(parts) + "}"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return _scalar(value)


def list_text(values: list) -> str:
    """'<n> items: a; b; c and <k> more': the full count first, then what is shown."""
    if not values:
        return "0 items"
    shown = "; ".join(_inline(v) for v in values[:LIST_SHOWN])
    more = len(values) - LIST_SHOWN
    tail = f" and {more} more" if more > 0 else ""
    return f"{len(values)} item{'s' if len(values) != 1 else ''}: {shown}{tail}"


def observed_rows(observed, prefix: str = "", depth: int = 0) -> list[tuple[str, str]]:
    """The observed object as (key, value) rows (keys relative to `observed`); nested
    objects as dotted keys."""
    if not isinstance(observed, dict):
        value = NOT_RECORDED if observed is None else _inline(observed)
        return [(prefix or "observed", value)]
    if not observed:
        return [(prefix or "observed", "{} (empty)")]
    rows: list[tuple[str, str]] = []
    for k, v in observed.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict) and v and depth < _DEPTH:
            rows += observed_rows(v, key, depth + 1)
        elif isinstance(v, list):
            rows.append((key, list_text(v)))
        else:
            rows.append((key, _inline(v)))
    return rows


def _field(a: dict, key: str) -> str:
    return _scalar(a.get(key)) if key in a else NOT_RECORDED


def record_body(item: Inspect) -> str:
    """An assertion's recorded fields: status, reason, evidence_valid, limitations, the
    evidence artifacts with their sha256, the observed object as rows, and the source."""
    a = item.record
    kv = "".join(
        f"<dt>{key}</dt><dd>{esc(_field(a, key))}</dd>"
        for key in ("status", "reason", "evidence_valid")
    )
    lims = a.get("limitations")
    if isinstance(lims, list) and lims:
        limitations = (
            '<ul class="hud-insp-list">'
            + "".join(f"<li>{esc(x)}</li>" for x in lims)
            + "</ul>"
        )
    else:
        limitations = f'<p class="hud-insp-none">{"none (empty list)" if isinstance(lims, list) else NOT_RECORDED}</p>'
    ev = a.get("evidence")
    if isinstance(ev, list) and ev:
        evidence = (
            '<dl class="hud-insp-kv hud-insp-ev">'
            + "".join(
                f"<dt>{esc(e.get('artifact') if isinstance(e, dict) else e)}</dt>"
                f"<dd>{esc((e.get('sha256') if isinstance(e, dict) else None) or NOT_RECORDED)}</dd>"
                for e in ev
            )
            + "</dl>"
        )
    else:
        evidence = f'<p class="hud-insp-none">{"none (empty list)" if isinstance(ev, list) else NOT_RECORDED}</p>'
    observed = "".join(
        f"<dt>{esc(key)}</dt><dd>{esc(val)}</dd>"
        for key, val in observed_rows(a.get("observed") if "observed" in a else None)
    )
    source = f"{item.source} · assertions[assertion_id={item.assertion_id}]"
    return (
        f'<dl class="hud-insp-kv">{kv}</dl>'
        f'<span class="hud-lbl">Limitations</span>{limitations}'
        f'<span class="hud-lbl">Evidence · artifact, sha256</span>{evidence}'
        f'<span class="hud-lbl">Observed</span><dl class="hud-insp-kv hud-insp-obs">{observed}</dl>'
        f'<div class="hud-src">{esc(source)}</div>'
    )


def inspection(item: Inspect, ids: Ids, scope: str, k: int, summary: str) -> str:
    """A tile that opens its inspection frame: details/summary, so no Streamlit widget and no
    rerun; Enter and Space toggle it and the browser reports its expanded state. The open
    frame carries the active-frame corner brackets."""
    sid = ids("insp", "sum" + _alpha(k), scope)
    brackets = "".join(
        f'<span class="hud-br hud-br-{c}" aria-hidden="true"></span>'
        for c in ("tl", "tr", "bl", "br")
    )
    return (
        f'<details class="hud-insp"><summary class="hud-tile-row" id="{sid}">{summary}'
        "</summary>"
        f'<div class="hud-insp-frame" role="group" aria-labelledby="{sid}">{brackets}'
        f"{record_body(item)}</div></details>"
    )


@dataclass(frozen=True)
class Outcome:
    """One reticle: an evaluated run's outcome and the line beneath it."""

    scope: str  # "orig" or "cand"
    heading: str
    code: str | None
    source: str
    detail: str
    detail_source: str
    execution: str | None = None
    execution_source: str | None = None


@dataclass(frozen=True)
class MatrixRow:
    assertion_id: str
    original: str | None
    candidate: str | None  # None when no candidate was executed

    @property
    def changed(self) -> bool:
        return self.candidate is not None and self.candidate != self.original


@dataclass(frozen=True)
class Hud:
    run_id: str
    ids: Ids
    bundled: bool
    checks: list[R.Check]
    original: Outcome
    candidate: Outcome | None
    cand_base: str | None
    rows: list[str]
    leak_orig: Leak
    leak_cand: Leak | None
    flow_orig: Flow
    flow_cand: Flow | None
    matrix: list[MatrixRow]
    inspect_orig: dict[str, Inspect] = field(default_factory=dict)
    inspect_cand: dict[str, Inspect] = field(default_factory=dict)


def _statuses(outcome) -> list[tuple[str, str | None]]:
    return [
        (str(a.get("assertion_id")), _str_or_none(a.get("status")))
        for a in (outcome or {}).get("assertions") or []
        if isinstance(a, dict) and a.get("assertion_id")
    ]


def _counts_line(statuses: list[tuple[str, str | None]]) -> str:
    if not statuses:
        return f"required checks: {NOT_RECORDED}"
    counts = {s: sum(1 for _, x in statuses if x == s) for s in A.STATUS_ORDER}
    line = f"{counts['FAIL']} of {len(statuses)} required checks FAIL"
    extra = [f"{counts[s]} {s}" for s in ("NOT_ASSESSED", "ERROR") if counts[s]]
    return " · ".join([line, *extra])


def _changes_line(rows: list[MatrixRow]) -> str:
    moves: dict[str, int] = {}
    for r in rows:
        if r.changed:
            key = f"{r.original or NOT_RECORDED} → {r.candidate}"
            moves[key] = moves.get(key, 0) + 1
    if not moves:
        return "no required-check status changed"
    return " · ".join(f"{n} {move}" for move, n in moves.items())


def executed_candidate(
    run_dir: Path, report: dict, verified: frozenset[str]
) -> tuple[str, dict] | None:
    """The last candidate that was executed and evaluated, with its files verified:
    (`candidates/<c>`, its comparison entry). Never a proposal that was not executed."""
    found = None
    for i, c in enumerate((report.get("comparison") or {}).get("candidates") or [], 1):
        if not isinstance(c, dict):
            continue
        sub = R.candidate_subfolder(c, i)
        if sub is None:
            continue
        execution = _json(run_dir, f"{sub}/execution.json", verified) or {}
        outcome = _json(run_dir, f"{sub}/outcome.json", verified) or {}
        if execution.get("status") == "completed" and outcome.get("outcome"):
            found = (sub, c)
    return found


def _typed_approval(events: list[dict], candidate_hash) -> dict | None:
    for e in events:
        if (
            e.get("event") == "approval"
            and e.get("kind") == "candidate"
            and candidate_hash
            and e.get("candidate_hash") == candidate_hash
        ):
            return e
    return None


def build(
    run_dir: Path,
    report: dict | None,
    checks: list[R.Check],
    run_id: str,
    *,
    bundled: bool = False,
    instance: str = "h",
    with_candidate: bool = True,
) -> Hud | None:
    """Everything the HUD shows, read only from verified files; None unless the run is intact
    (a tampered run shows no outcome and no diagram) or it is not an agent run.
    `with_candidate=False` reads the original only (the hosted live session's starting
    point, taken from a recorded run whose revision is not part of that session)."""
    if report is None or not checks or not R.intact(checks):
        return None
    run_dir = Path(run_dir)
    verified = verified_paths(checks)
    orig_outcome = _json(run_dir, "original/outcome.json", verified)
    if not isinstance(orig_outcome, dict):
        return None
    orig_statuses = _statuses(orig_outcome)
    original = Outcome(
        scope="orig",
        heading="Before · original",
        code=_str_or_none(orig_outcome.get("outcome")),
        source="original/outcome.json · outcome",
        detail=_counts_line(orig_statuses),
        detail_source="original/outcome.json · assertions[].status",
    )
    chosen = executed_candidate(run_dir, report, verified) if with_candidate else None
    candidate = cand_base = leak_cand = flow_cand = None
    inspect_cand: dict[str, Inspect] = {}
    matrix = [MatrixRow(aid, status, None) for aid, status in orig_statuses]
    if chosen is not None:
        cand_base, _entry = chosen
        cand_outcome = _json(run_dir, f"{cand_base}/outcome.json", verified) or {}
        cand_status = dict(_statuses(cand_outcome))
        orig_status = dict(orig_statuses)
        order = [aid for aid, _ in orig_statuses] + [
            aid for aid in cand_status if aid not in orig_status
        ]
        matrix = [
            MatrixRow(aid, orig_status.get(aid), cand_status.get(aid) or NOT_RECORDED)
            for aid in order
        ]
        execution = _json(run_dir, f"{cand_base}/execution.json", verified) or {}
        approval = _typed_approval(
            A.read_log(run_dir) if "agent_log.jsonl" in verified else [],
            execution.get("candidate_hash"),
        )
        typed = (
            execution.get("runner") == "docker_isolated"
            and execution.get("status") == "completed"
            and approval is not None
            and approval.get("decision") == "approved"
            and approval.get("approver_reason") == "confirmed"
        )
        if typed:
            ran = TYPED_APPROVAL
        else:
            ran = (
                f"execution {execution.get('status') or NOT_RECORDED} in runner "
                f"{execution.get('runner') or NOT_RECORDED}; approval "
                f"{(approval or {}).get('approver_reason') or NOT_RECORDED}"
            )
        candidate = Outcome(
            scope="cand",
            heading=f"Verified revision · {cand_base}",
            code=_str_or_none(cand_outcome.get("outcome")),
            source=f"{cand_base}/outcome.json · outcome",
            detail=_changes_line(matrix),
            detail_source=(
                f"original/outcome.json vs {cand_base}/outcome.json · assertions[].status"
            ),
            execution=ran,
            execution_source=(
                f"{cand_base}/execution.json · runner, status; agent_log.jsonl · "
                "event approval (kind candidate, decision, approver_reason)"
            ),
        )
        leak_cand = leak(run_dir, cand_base, verified)
        flow_cand = flow(run_dir, cand_base, verified)
        inspect_cand = inspect_records(
            run_dir, cand_base, list(cand_status.items()), verified
        )
    else:
        # Nothing executed comes after it, so it is not headed "before".
        original = Outcome(**{**original.__dict__, "heading": "Original"})
    leak_orig = leak(run_dir, "original", verified)
    return Hud(
        run_id=run_id,
        ids=Ids(run_hash(run_id), instance),
        bundled=bundled,
        checks=list(checks),
        original=original,
        candidate=candidate,
        cand_base=cand_base,
        rows=leak_rows(leak_orig),
        leak_orig=leak_orig,
        leak_cand=leak_cand,
        flow_orig=flow(run_dir, "original", verified),
        flow_cand=flow_cand,
        matrix=matrix,
        inspect_orig=inspect_records(run_dir, "original", orig_statuses, verified),
        inspect_cand=inspect_cand,
    )


# -- 1. integrity ring --------------------------------------------------------------------------------
def _arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    def pt(a):
        rad = math.radians(a - 90)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    (x0, y0), (x1, y1) = pt(a0), pt(a1)
    large = 1 if a1 - a0 > 180 else 0
    return f"M{x0:.2f} {y0:.2f}A{r} {r} 0 {large} 1 {x1:.2f} {y1:.2f}"


def ring(checks: list[R.Check], ids: Ids, *, played: bool, phrase: str) -> str:
    """One segment per recorded item `verify` checked; lit when it matches. A changed run's
    differing segments are red and the centre reads EVIDENCE CHANGED (no outcome here)."""
    n = len(checks)
    bad = [c for c in checks if not c.ok]
    ok = not bad and n > 0
    title_id, desc_id = ids("ring", "title"), ids("ring", "desc")
    if ok:
        title = f"Integrity: {n} of {n} recorded items intact"
        desc = "Every recorded hash and outcome matches, recomputed now."
    else:
        title = f"Integrity: evidence changed, {len(bad)} of {n} recorded items differ"
        desc = "Differing items: " + "; ".join(f"{c.item} ({c.status})" for c in bad)
    segs = []
    per = 360 / max(n, 1)
    gap = min(1.8, per * 0.3) if n > 1 else 0
    for i, c in enumerate(checks):
        a0, a1 = i * per + gap / 2, (i + 1) * per - gap / 2
        if n == 1:
            a1 = a0 + 359.9
        cls = "hud-seg-ok" if c.ok else "hud-seg-bad"
        if ok:
            anim = _a(played, "hud-a-seg")
            style = _delay(played, i * (BEAT1_END - 0.08) / max(n, 1))
        else:
            anim = _a(played, "hud-a-bad") if not c.ok else ""
            style = ""
        segs.append(
            f'<path class="hud-seg {cls}{anim}"{style} d="{_arc(64, 64, 52, a0, a1)}">'
            f"<title>{esc(c.item)}: {esc(c.status)}</title></path>"
        )
    if ok:
        centre = (
            f'<text x="64" y="62" text-anchor="middle" class="hud-ring-n">{n}/{n}</text>'
            '<text x="64" y="80" text-anchor="middle" class="hud-ring-l">INTACT</text>'
        )
    else:
        centre = (
            '<text x="64" y="60" text-anchor="middle" class="hud-ring-x">EVIDENCE</text>'
            '<text x="64" y="76" text-anchor="middle" class="hud-ring-x">CHANGED</text>'
        )
    group = f'<g class="hud-ring-g{_a(played or ok, "hud-a-shake")}">'
    count = (
        ""
        if ok
        else f'<span class="hud-c-red hud-code">{len(bad)} of {n} differ</span>'
    )
    return (
        f'<div class="hud hud-ring{_anim(played)}">'
        f'<svg viewBox="0 0 128 128" width="108" height="108" role="img" '
        f'aria-labelledby="{title_id} {desc_id}">'
        f'<title id="{title_id}">{esc(title)}</title><desc id="{desc_id}">{esc(desc)}</desc>'
        f'{group}<circle cx="64" cy="64" r="52" class="hud-ring-track"/>{"".join(segs)}</g>'
        f"{centre}</svg>"
        f'<div class="hud-ring-cap">{count}<span class="hud-src">{esc(phrase)}</span></div>'
        "</div>"
    )


# -- 2. outcome reticle ----------------------------------------------------------------------------
def reticle(o: Outcome, *, played: bool) -> str:
    tone = _tone(o.code) if o.code else "stone"
    brackets = "".join(
        f'<span class="hud-br hud-br-{c}{_a(played, "hud-a-lock-" + c)}" aria-hidden="true">'
        "</span>"
        for c in ("tl", "tr", "bl", "br")
    )
    code = (
        f'<div class="hud-ret-code hud-c-{tone}" style="text-shadow:0 0 14px {GLOW[tone]}">'
        f"{esc(o.code)}</div>"
        if o.code
        else f'<div class="hud-ret-none">outcome: {NOT_RECORDED}</div>'
    )
    label = A.OUTCOME_LABELS.get(o.code or "", "")
    execution = (
        f'<div class="hud-ret-exec" title="{esc(o.execution_source)}">{esc(o.execution)}</div>'
        if o.execution
        else ""
    )
    return (
        f'<section class="hud-ret hud-ret-{o.scope} hud-t-{tone}" '
        f'aria-label="{esc(o.heading)} outcome">{brackets}'
        f'<div class="hud-lbl">{esc(o.heading)}</div>{code}'
        f'<div class="hud-ret-detail" title="{esc(o.detail_source)}">{esc(o.detail)}</div>'
        f"{execution}"
        f'<div class="hud-ret-label">{esc(label)}</div>'
        f'<div class="hud-ret-caveat">{esc(A.CAVEAT)}</div>'
        f'<div class="hud-src">{esc(o.source)}</div></section>'
    )


def hero(h: Hud, *, played: bool, head: str | None = None) -> str:
    """The ring and the reticles: the first row of the hero. `head` is its accessible name
    when the default ("before → verified revision", or "no executed revision in this run")
    does not describe it."""
    phrase = (
        "recomputed now from the bundled files"
        if h.bundled
        else "recomputed now from the run's files"
    )
    head = head or (
        "Before → verified revision"
        if h.candidate is not None
        else "Original evaluation · no executed revision in this run"
    )
    arrow = (
        '<div class="hud-hero-arrow" aria-hidden="true">→</div>'
        if h.candidate is not None
        else ""
    )
    cand = reticle(h.candidate, played=played) if h.candidate is not None else ""
    single = "" if h.candidate is not None else " hud-hero-single"
    return (
        f'<section class="hud hud-hero{single}{_anim(played)}" aria-label="{esc(head)}">'
        f'<div class="hud-hero-ring">{ring(h.checks, h.ids, played=played, phrase=phrase)}</div>'
        f"{reticle(h.original, played=played)}{arrow}{cand}</section>"
    )


# -- 7. leak map ---------------------------------------------------------------------------------------
def leak_map(data: Leak, rows: list[str], ids: Ids, scope: str, *, played: bool) -> str:
    title = "Leak map · " + ("original" if scope == "orig" else data.base)
    cap = f"{data.source} · {LEAK_ASSERTION} · observed.overlapping_groups"
    status = _code(data.status) if data.recorded else ""
    head = (
        f'<div class="hud-ph"><span class="hud-lbl">{esc(title)}</span>{status}</div>'
    )
    foot = f'<div class="hud-src">{esc(cap)}</div>'
    if not data.recorded:
        body = f'<p class="hud-nr">{esc(LEAK_ASSERTION)} in {esc(data.source)}: {NOT_RECORDED}</p>'
        return f'<div class="hud-panel hud-leak">{head}{body}{foot}</div>'
    if data.groups is None:
        body = f'<p class="hud-nr">observed.overlapping_groups: {NOT_RECORDED}</p>'
        return f'<div class="hud-panel hud-leak">{head}{body}{foot}</div>'
    cols = data.columns()
    fold_note = (
        f'<p class="hud-nr">{esc(data.folds_source)}: {NOT_RECORDED}</p>'
        if data.folds is None
        else ""
    )
    step = BEAT3[1] / max(len(cols), 1)
    header = "".join(
        f'<th scope="col" title="{esc(data.folds_source)} · fold">{esc(f)}</th>'
        for f in cols
    )
    column = data.column or f"column {NOT_RECORDED}"
    body_rows = []
    for g in rows:
        cells = []
        for k, fold in enumerate(cols):
            both = data.both(g, fold)
            text, short = (BOTH, "B") if both else (NONE_SHARED, "0")
            full = f"{g}, {fold}: {text}"
            cls = "hud-both" + _a(played, "hud-a-light") if both else "hud-none"
            style = _delay(played, BEAT3[0] + k * step, step) if both else ""
            cells.append(
                f'<td class="{cls}"{style} title="{esc(full)}" aria-label="{esc(full)}">'
                f'<span class="hud-full" aria-hidden="true">{text}</span>'
                f'<span class="hud-short" aria-hidden="true">{short}</span></td>'
            )
        body_rows.append(f'<tr><th scope="row">{esc(g)}</th>{"".join(cells)}</tr>')
    if not rows:
        body_rows.append(
            f'<tr><td class="hud-empty" colspan="{len(cols) + 1}">No group is listed in '
            "observed.overlapping_groups for any fold.</td></tr>"
        )
    extra = sorted(
        {g for listed in (data.groups or {}).values() for g in listed} - set(rows)
    )
    extra_note = (
        f'<p class="hud-nr">Also listed here, not in the original’s rows: '
        f"{esc(', '.join(extra))}</p>"
        if extra
        else ""
    )
    region = ids("leak", "region", scope)
    table = (
        f'<div class="hud-scroll" tabindex="0" role="region" id="{region}" '
        f'aria-label="{esc(title)}: groups by fold">'
        f'<table class="hud-lm"><caption class="hud-axis">{esc(LEAK_Y_LABEL)}</caption>'
        f'<thead><tr><th scope="col" class="hud-lm-col">{esc(column)}</th>{header}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody></table></div>"
    )
    legend = '<p class="hud-legend">B = on both sides (listed for that fold) · 0 = 0 shared</p>'
    return (
        f'<div class="hud-panel hud-leak{_anim(played)}">{head}{table}{legend}'
        f"{fold_note}{extra_note}{foot}</div>"
    )


# -- 8. fit-scope flow -----------------------------------------------------------------------------------
def _origin_uses(o: dict) -> list[tuple[str, str]]:
    """One origin's (fold, use) targets in recorded order; an affected fold without a listed
    use keeps one target of its own (drawn without a line: no use is recorded for it)."""
    nodes: list[tuple[str, str]] = []
    for u in o.get("affected_uses") or []:
        if isinstance(u, str):
            fold, _, name = u.partition(":") if ":" in u else ("", "", u)
            if (fold, name) not in nodes:
                nodes.append((fold, name))
    for fold in o.get("affected_folds") or []:
        if isinstance(fold, str) and not any(f == fold for f, _ in nodes):
            nodes.append((fold, NO_USE))
    return nodes


def _origin_text(o: dict) -> tuple[str, str, str]:
    rows = o.get("contributing_rows")
    rows_text = (
        f"[{rows} rows] →" if isinstance(rows, int) else f"[rows {NOT_RECORDED}] →"
    )
    cls = o.get("class") if isinstance(o.get("class"), str) else f"class {NOT_RECORDED}"
    scope = o.get("fit_scope") if isinstance(o.get("fit_scope"), str) else NOT_RECORDED
    return rows_text, cls, f"(fit: {scope})"


def flow_summary(data: Flow) -> tuple[str, str]:
    """The fit-scope state without drawn origins, from the fields that are recorded: (line,
    the fields it reads). A PASS with no origins field lists none ("no global fit origins
    listed"); "not recorded" only for a field that is absent where a value is expected."""
    parts = []
    if data.violation_entries is None:
        parts.append(f"observed.violations: {NOT_RECORDED}")
    elif data.folds is None:
        parts.append(
            f"{data.violation_entries} violations ({data.folds_source}: {NOT_RECORDED})"
        )
    else:
        parts.append(f"{data.violation_entries} violations across {data.folds} folds")
    parts.append(
        f"observed.judged_uses: {NOT_RECORDED}"
        if data.judged_uses is None
        else f"{data.judged_uses} uses judged"
    )
    parts.append(
        f"observed.unknown_uses: {NOT_RECORDED}"
        if data.unknown_uses is None
        else f"{data.unknown_uses} unknown"
    )
    if data.origins is not None:
        parts.append("observed.origins: none listed")
    elif data.status == "PASS":
        parts.append("no global fit origins listed")
    else:
        parts.append(f"observed.origins: {NOT_RECORDED}")
    fields = (
        "status, observed.violations, observed.judged_uses, observed.unknown_uses, "
        f"observed.origins; {data.folds_source} · fold"
    )
    return " · ".join(parts), fields


def fit_flow(data: Flow, ids: Ids, scope: str, *, played: bool) -> str:
    title = "Fit-scope flow · " + ("original" if scope == "orig" else data.base)
    status = _code(data.status) if data.recorded else ""
    head = (
        f'<div class="hud-ph"><span class="hud-lbl">{esc(title)}</span>{status}</div>'
    )
    if not data.recorded:
        foot = f'<div class="hud-src">{esc(data.source)} · {esc(FIT_ASSERTION)}</div>'
        body = f'<p class="hud-nr">{esc(FIT_ASSERTION)} in {esc(data.source)}: {NOT_RECORDED}</p>'
        return f'<div class="hud-panel hud-flow">{head}{body}{foot}</div>'
    if not data.origins:
        line, fields = flow_summary(data)
        foot = (
            f'<div class="hud-src">{esc(data.source)} · {esc(FIT_ASSERTION)} · '
            f"{esc(fields)}</div>"
        )
        body = f'<p class="hud-flow-sum">{esc(line)}</p>'
        return f'<div class="hud-panel hud-flow">{head}{body}{foot}</div>'
    foot = (
        f'<div class="hud-src">{esc(data.source)} · {esc(FIT_ASSERTION)} · '
        "observed.origins</div>"
    )

    # One lane per origin: the origin box on the left, its own recorded targets (grouped by
    # fold) on the right, a line to each of them. A target that several origins affect is
    # listed once in each origin's lane, so no line crosses into another lane.
    tone = "red" if data.status == "FAIL" else "muted"
    row_h, origin_h, fold_gap, lane_gap, pad = 14, 44, 4, 14, 6
    ox, ow, nx, tx = 4, 124, 214, 252  # origin box, fold label, use text
    arrow = ids("flow", "arrow", scope)
    title_id, desc_id = ids("flow", "title", scope), ids("flow", "desc", scope)
    parts, lines, labels, desc, seps = [], [], [], [], []
    longest = 10
    y = pad
    for k, o in enumerate(data.origins):
        nodes = _origin_uses(o)
        longest = max([longest, *(len(n) for _, n in nodes)])
        offsets, at, last = [], 0, None
        for fold, _ in nodes:
            if last is not None and fold != last:
                at += fold_gap
            offsets.append(at)
            at += row_h
            last = fold
        nodes_h = max(at, row_h)
        lane_h = max(origin_h, nodes_h)
        top = y + (lane_h - origin_h) / 2
        mid = top + origin_h / 2
        n0 = y + (lane_h - nodes_h) / 2 + 10
        rows_text, cls, fit = _origin_text(o)
        uses = [u for u in o.get("affected_uses") or [] if isinstance(u, str)]
        desc.append(
            f"{cls} {fit} on {rows_text.strip('[] →')}, used by {', '.join(uses)}"
        )
        if k:
            seps.append(y - lane_gap / 2)
        parts.append(
            f'<rect x="{ox}" y="{top:.1f}" width="{ow}" height="{origin_h}" rx="2" '
            f'class="hud-fo hud-fo-{tone}"/>'
            f'<text x="{ox + 8}" y="{top + 13:.1f}" class="hud-ft-m">{esc(rows_text)}</text>'
            f'<text x="{ox + 8}" y="{top + 28:.1f}" class="hud-ft">{esc(cls)}</text>'
            f'<text x="{ox + 8}" y="{top + 41:.1f}" class="hud-ft-s">{esc(fit)}</text>'
        )
        last = None
        for (fold, name), off in zip(nodes, offsets, strict=True):
            ny = n0 + off
            if fold != last:
                labels.append(
                    f'<text x="{nx}" y="{ny:.1f}" class="hud-ft-f">{esc(fold)}</text>'
                )
                last = fold
            labels.append(
                f'<text x="{tx}" y="{ny:.1f}" class="hud-ft">{esc(name)}</text>'
            )
            if name == NO_USE:
                continue
            use = f"{fold}:{name}" if fold else name
            x0, x1, y1 = ox + ow, nx - 8, ny - 4
            c = (x0 + x1) / 2
            lines.append(
                f'<path class="hud-fl hud-fl-{tone}{_a(played, "hud-a-draw")}" '
                f'pathLength="1" data-lane="{k}" data-use="{esc(use)}" '
                f'd="M{x0} {mid:.1f}C{c:.1f} {mid:.1f} {c:.1f} {y1:.1f} {x1} {y1:.1f}" '
                f'marker-end="url(#{arrow})"><title>{esc(cls)} → {esc(use)}</title></path>'
            )
        y += lane_h + lane_gap
    height = y - lane_gap + pad
    width = int(tx + longest * 6.7 + 8)
    rules = "".join(
        f'<line x1="0" x2="{width}" y1="{s:.1f}" y2="{s:.1f}" class="hud-lane"/>'
        for s in seps
    )
    marker = (
        f'<defs><marker id="{arrow}" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="6" '
        f'markerHeight="6" orient="auto"><path d="M0 0L6 3L0 6z" class="hud-fh-{tone}'
        f'{_a(played, "hud-a-head")}"/></marker></defs>'
    )
    svg = (
        f'<svg class="hud-flow-svg" viewBox="0 0 {width} {height:.0f}" '
        f'style="max-width:{width}px" role="img" aria-labelledby="{title_id} {desc_id}">'
        f'<title id="{title_id}">{esc(title)}: {esc(FIT_ASSERTION)} {esc(data.status)}</title>'
        f'<desc id="{desc_id}">{esc(". ".join(desc))}</desc>'
        f"{marker}{rules}{''.join(lines)}{''.join(parts)}{''.join(labels)}</svg>"
    )
    return f'<div class="hud-panel hud-flow{_anim(played)}">{head}{svg}{foot}</div>'


# -- 3. check matrix ------------------------------------------------------------------------------------------
def matrix_column(
    rows: list[MatrixRow],
    side: str,
    source: str,
    *,
    played: bool,
    paired: bool = False,
    inspect: dict[str, Inspect] | None = None,
    ids: Ids | None = None,
) -> str:
    """One column of assertion tiles (status code + assertion ID); `side` is "orig" or "cand".
    A changed candidate tile states its direction. A FAIL, NOT_ASSESSED or ERROR tile whose
    record is in `inspect` opens its inspection frame (needs `ids`)."""
    tiles = []
    for k, r in enumerate(rows):
        status = r.original if side == "orig" else r.candidate
        changed = side == "cand" and r.changed
        move = (
            f'<span class="hud-move">{esc(r.original or NOT_RECORDED)} → {esc(r.candidate)}</span>'
            if changed
            else ('<span class="hud-move" aria-hidden="true"></span>' if paired else "")
        )
        anim = _a(played, "hud-a-flip") if changed else ""
        head = f'{_code(status)}<span class="hud-aid">{esc(r.assertion_id)}</span>'
        item = (inspect or {}).get(r.assertion_id) if status in INSPECTED else None
        if item is not None and ids is not None:
            # The direction and the "Inspect" cue share the tile's end slot.
            cue = '<span class="hud-insp-cue" aria-hidden="true"></span>'
            end = f'<span class="hud-tile-end">{move}{cue}</span>'
            tiles.append(
                f'<li class="hud-tile hud-tile-insp{" hud-changed" if changed else ""}{anim}">'
                f"{inspection(item, ids, side, k, head + end)}</li>"
            )
            continue
        tiles.append(
            f'<li class="hud-tile{" hud-changed" if changed else ""}{anim}">{head}{move}</li>'
        )
    label = "Required checks · " + (
        "original" if side == "orig" else source.split("/outcome")[0]
    )
    return (
        f'<div class="hud-panel hud-mx{_anim(played)}"><div class="hud-ph">'
        f'<span class="hud-lbl">{esc(label)}</span></div>'
        f'<ol class="hud-tiles{" hud-tiles-pair" if paired else ""}" aria-label="{esc(label)}">{"".join(tiles)}</ol>'
        f'<div class="hud-src">{esc(source)} · assertions[].status</div></div>'
    )


# -- the evidence block (pairs and the narrow-screen toggle) ---------------------------------------------------
def evidence(h: Hud, *, played: bool) -> str:
    """Leak maps, fit-scope flows and the check matrix: original and candidate side by side at
    when the recorded page is 760 px wide or more (a CSS container query on st-key-hud-page:
    1280 px with the sidebar open, for example); narrower, a CSS-only toggle (hidden radio
    inputs) cross-fades between them."""
    ids = h.ids
    orig_parts = [
        leak_map(h.leak_orig, h.rows, ids, "orig", played=played),
        fit_flow(h.flow_orig, ids, "orig", played=played),
        matrix_column(
            h.matrix,
            "orig",
            "original/outcome.json",
            played=played,
            paired=h.candidate is not None,
            inspect=h.inspect_orig,
            ids=ids,
        ),
    ]
    if h.candidate is None:
        return (
            '<div class="hud hud-ev hud-ev-single"><div class="hud-panes">'
            f'<section class="hud-pane hud-pane-orig" aria-label="Original">'
            f"{''.join(orig_parts)}</section></div></div>"
        )
    cand_parts = [
        leak_map(h.leak_cand, h.rows, ids, "cand", played=played),
        fit_flow(h.flow_cand, ids, "cand", played=played),
        matrix_column(
            h.matrix,
            "cand",
            f"{h.cand_base}/outcome.json",
            played=played,
            paired=True,
            inspect=h.inspect_cand,
            ids=ids,
        ),
    ]
    name = ids("toggle", "group")
    in_o, in_c = ids("toggle", "input", "orig"), ids("toggle", "input", "cand")
    toggle = (
        f'<input type="radio" class="hud-tg-in hud-tg-in-orig" name="{name}" id="{in_o}">'
        f'<input type="radio" class="hud-tg-in hud-tg-in-cand" name="{name}" '
        f'id="{in_c}"><div class="hud-tg" role="group" aria-label="Show the original or '
        f'the verified revision"><label for="{in_o}" class="hud-tg-orig">Original</label>'
        f'<label for="{in_c}" class="hud-tg-cand">Verified revision</label></div>'
    )
    return (
        f'<div class="hud hud-ev">{toggle}<div class="hud-panes">'
        f'<section class="hud-pane hud-pane-orig" aria-label="Original">{"".join(orig_parts)}'
        f"</section>"
        f'<section class="hud-pane hud-pane-cand" aria-label="Verified revision, '
        f'{esc(h.cand_base)}">{"".join(cand_parts)}</section></div></div>'
    )


# -- 4. mission track and 5. budget gauge ------------------------------------------------------------------------
TERMINAL_STATES = (
    "REPORT",
    "ERROR",
    "BUDGET_EXHAUSTED",
    "NEEDS_INPUT",
    "NOT_SUPPORTED",
)


def _stage_items(
    states: list[dict], terminal: str | None, lit_from: int | None, *, live: bool
) -> list[str]:
    """One node per recorded stage. The terminal stage shows its code in its colour; on a
    live track the latest stage of a run still going is marked current. Nodes from index
    `lit_from` on light once (a stage that has just appeared); None renders settled."""
    items = []
    for i, s in enumerate(states):
        state = str(s["state"])
        last = i == len(states) - 1
        is_end = last and (state == terminal or (live and state in TERMINAL_STATES))
        now = live and last and not is_end
        tip = " · ".join(
            str(x) for x in (s.get("detail"), A.short_time(s.get("time_utc"))) if x
        )
        body = (
            _code(state) if is_end else f'<span class="hud-stage-n">{esc(state)}</span>'
        )
        cls = "hud-stage" + (" hud-stage-end" if is_end else "")
        cls += " hud-stage-now" if now else ""
        cls += " hud-a-node" if lit_from is not None and i >= lit_from else ""
        current = ' aria-current="step"' if now else ""
        items.append(f'<li class="{cls}"{current} title="{esc(tip)}">{body}</li>')
    if not states:
        items.append(
            f'<li class="hud-stage"><span class="hud-stage-n">states: {NOT_RECORDED}</span></li>'
        )
    return items


def _counter(label: str, used, limit, source: str) -> str:
    """'<used> of <limit>' with one cell per unit of the limit; '<used> so far' when no limit
    is recorded yet (a run still going)."""
    if not isinstance(used, int) or isinstance(used, bool):
        return (
            f'<div class="hud-cnt"><span class="hud-lbl">{label}</span>'
            f'<span class="hud-cnt-v">{NOT_RECORDED}</span></div>'
        )
    if limit is None:
        return (
            f'<div class="hud-cnt" title="{esc(source)}"><span class="hud-lbl">{label}</span>'
            f'<span class="hud-cnt-v">{used} so far</span></div>'
        )
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        return (
            f'<div class="hud-cnt"><span class="hud-lbl">{label}</span>'
            f'<span class="hud-cnt-v">{NOT_RECORDED}</span></div>'
        )
    cells = "".join(
        f'<span class="{"on" if k < used else ""}"></span>'
        for k in range(min(limit, 24))
    )
    return (
        f'<div class="hud-cnt" title="{esc(source)}"><span class="hud-lbl">{label}</span>'
        f'<span class="hud-cnt-v">{used} of {limit}</span>'
        f'<span class="hud-cells" aria-hidden="true">{cells}</span></div>'
    )


def _track(
    items: list[str], n: int, counters: str, source: str, ids: Ids, lit: bool
) -> str:
    label = ids("track", "label")
    return (
        f'<div class="hud hud-track{_anim(not lit)}"><div class="hud-ph">'
        f'<span class="hud-lbl" id="{label}">Mission track · {n} recorded stages</span></div>'
        f'<ol class="hud-stages" aria-labelledby="{label}">{"".join(items)}</ol>'
        f'<div class="hud-cnts">{counters}</div><div class="hud-src">{esc(source)}</div></div>'
    )


def track(report: dict, ids: Ids, *, lit_from: int | None = None) -> str:
    """A finished run's recorded stages, in order, and its budget counters, from its report.
    Settled unless `lit_from` names the first stage to light."""
    states = [
        s for s in report.get("states") or [] if isinstance(s, dict) and s.get("state")
    ]
    budget = report.get("budget") or {}
    used, limits = budget.get("used") or {}, budget.get("limits") or {}

    def counter(label: str, u_key: str, l_key: str) -> str:
        src = f"agent_report.json · budget.used.{u_key} of budget.limits.{l_key}"
        limit = limits.get(l_key)
        return _counter(
            label, used.get(u_key), NOT_RECORDED if limit is None else limit, src
        )

    counters = (
        counter("Model attempts", "attempts", "model_attempts")
        + counter("Tool operations", "tool_operations", "tool_operations")
        + counter("Revisions", "revisions", "candidate_revisions")
    )
    items = _stage_items(states, report.get("terminal_state"), lit_from, live=False)
    source = "agent_report.json · states[], budget.used, budget.limits"
    lit = lit_from is not None and lit_from < len(states)
    return _track(items, len(states), counters, source, ids, lit)


def log_progress(events: list[dict]) -> tuple[list[dict], int, int]:
    """What a run's log records so far: (its state events, model attempts, tool operations)."""
    states = [
        e
        for e in events
        if e.get("event") == "state" and isinstance(e.get("state"), str)
    ]
    attempts = sum(1 for e in events if e.get("event") == "model_attempt")
    tools = sum(1 for e in events if e.get("event") == "tool")
    return states, attempts, tools


def track_live(events: list[dict], ids: Ids, *, lit_from: int | None = None) -> str:
    """The stages a run still going has recorded so far, from its own log (agent_log.jsonl),
    and its counters so far (the limits are recorded with the report at the end)."""
    states, attempts, tools = log_progress(events)
    src = "agent_log.jsonl · events so far"
    counters = _counter("Model attempts", attempts, None, src) + _counter(
        "Tool operations", tools, None, src
    )
    items = _stage_items(states, None, lit_from, live=True)
    source = "agent_log.jsonl · event state, model_attempt, tool (recorded so far)"
    lit = lit_from is not None and lit_from < len(states)
    return _track(items, len(states), counters, source, ids, lit)


def _usd(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bar(name: str, used, cap, value: str, source: str) -> str:
    fill = ""
    if used is not None and cap is not None and cap > 0:
        pct = max(0.0, min(100.0, 100 * used / cap))
        fill = f'<span style="width:{pct:.1f}%"></span>'
    return (
        f'<div class="hud-gb" title="{esc(source)}"><span class="hud-lbl">{name}</span>'
        f'<span class="hud-gb-v">{esc(value)}</span>'
        f'<span class="hud-bar" aria-hidden="true">{fill}</span></div>'
    )


def _gauge_head(ids: Ids) -> tuple[str, str]:
    label = ids("gauge", "label")
    return label, (
        f'<div class="hud-ph"><span class="hud-lbl" id="{label}">Budget · estimate, '
        "not billing</span></div>"
    )


def gauge(report: dict, ids: Ids) -> str:
    cost, spending = report.get("cost") or {}, report.get("spending") or {}
    label, head = _gauge_head(ids)
    if not cost.get("applicable"):
        reason = cost.get("reason") or NOT_RECORDED
        return (
            f'<div class="hud hud-gauge" role="group" aria-labelledby="{label}">{head}'
            f'<p class="hud-nr">{esc(reason)}</p>'
            '<div class="hud-src">agent_report.json · cost.reason</div></div>'
        )
    entries = cost.get("entries")
    requests = len(entries) if isinstance(entries, list) else None
    cap = spending.get("max_attempts")
    cap = cap if isinstance(cap, int) and not isinstance(cap, bool) else None
    est, est_cap = (
        _usd(cost.get("estimated_total_usd")),
        _usd(spending.get("estimate_cap_usd")),
    )
    requests_text = NOT_RECORDED if requests is None else str(requests)
    cap_text = NOT_RECORDED if cap is None else str(cap)
    return (
        f'<div class="hud hud-gauge" role="group" aria-labelledby="{label}">{head}'
        + _bar(
            "Provider requests",
            requests,
            cap,
            f"{requests_text} of {cap_text}",
            "agent_report.json · cost.entries[] of spending.max_attempts",
        )
        + _bar(
            "Estimated cost (USD)",
            est,
            est_cap,
            f"{cost.get('estimated_total_usd') or NOT_RECORDED} of "
            f"{spending.get('estimate_cap_usd') or NOT_RECORDED} estimate cap",
            "agent_report.json · cost.estimated_total_usd of spending.estimate_cap_usd",
        )
        + '<div class="hud-src">agent_report.json · cost, spending (estimate, not billing)</div>'
        "</div>"
    )


def log_spend(events: list[dict]) -> tuple[int, Decimal | None]:
    """Provider requests so far and their estimated cost so far, from the log's
    model_attempt events: known plus held (unresolved) USD, as the engine records them.
    The cost is None when an attempt's cost is not a recorded amount."""
    attempts = [e for e in events if e.get("event") == "model_attempt"]
    total = Decimal(0)
    for e in attempts:
        cost = e.get("cost")
        if not isinstance(cost, dict):
            return len(attempts), None
        try:
            total += Decimal(str(cost.get("known_usd"))) + Decimal(
                str(cost.get("unresolved_usd"))
            )
        except (InvalidOperation, ValueError):
            return len(attempts), None
    return len(attempts), total


def gauge_live(
    events: list[dict], ids: Ids, *, max_attempts: int, cap_usd: str, caps_source: str
) -> str:
    """A session still going: its requests and estimated cost so far, from its own log,
    against the limits it was started with (`caps_source` names them)."""
    label, head = _gauge_head(ids)
    requests, spent = log_spend(events)
    cap = _usd(cap_usd)
    spent_text = NOT_RECORDED if spent is None else format(spent.normalize(), "f")
    return (
        f'<div class="hud hud-gauge" role="group" aria-labelledby="{label}">{head}'
        + _bar(
            "Provider requests so far",
            requests,
            max_attempts,
            f"{requests} of {max_attempts}",
            f"agent_log.jsonl · model_attempt events; limit {caps_source}",
        )
        + _bar(
            "Estimated cost so far (USD)",
            None if spent is None else float(spent),
            cap,
            f"{spent_text} of {cap_usd} estimate cap",
            "agent_log.jsonl · model_attempt[].cost.known_usd + unresolved_usd; cap "
            + caps_source,
        )
        + f'<div class="hud-src">agent_log.jsonl so far; limits {esc(caps_source)} '
        "(estimate, not billing)</div></div>"
    )


def hash_block(value) -> str:
    """A full hash, never truncated: Plex Mono in the neutral text colour, wrapping."""
    text = esc(value) if value else NOT_RECORDED
    return f'<p class="hud hud-hash">{text}</p>'


def state_panel(tone: str, code: str, reason: str, action: str | None) -> str:
    """A failure or honest-empty state as HUD markup (used where AppTest reads no text):
    the code in its status colour, the reason, the next action. Never celebratory."""
    nxt = (
        f'<p class="hud-state-next"><span class="hud-lbl">Next action</span> {esc(action)}</p>'
        if action
        else ""
    )
    return (
        f'<div class="hud hud-state hud-state-{tone}" role="status">'
        f'<b class="hud-code hud-c-{tone}">{esc(code)}</b>'
        f'<p class="hud-state-why">{esc(reason)}</p>{nxt}</div>'
    )


# -- 6. model-written frame ------------------------------------------------------------------------------------
# The frame's header is native Streamlit (a badge, then the engine's label as a caption), so it
# renders in the same pass as the untrusted text (`st.text`) it labels: a raw-HTML header renders
# a moment later, and the text was briefly shown unlabelled (found by the scenario 1 test). The
# dashed frame is CSS on the st-key-model-* container (views.CSS). Streamlit's orange badge is
# the spec's amber (#FBBF24 on #302F21).
MODEL_BADGE_MARKDOWN = f":orange-badge[{MODEL_BADGE}]"


# -- 9. mission briefing (deterministic, text only) -----------------------------------------------
# The briefing is built only from a run's verified files and the policy's frozen definitions
# (evaluation/assertion_definitions.json). It never reads model text, a rationale, a proposal's
# text, a diff, a complete file or a reply: from the report it takes only the proposals'
# outcome codes, which the engine sets.
DEFINITIONS = ROOT / "evaluation" / "assertion_definitions.json"
BRIEF_FAILS = 4  # failing assertions listed by name, then "and <k> more"
PROPOSALS_NOT_EXECUTED = (
    "Proposals were checked by ATLAS validation and not executed here."
)
_SENTENCE_END = re.compile(r"\.\s+(?=[A-Z*`(])")
_MARKUP = re.compile(r"[*`]")


def load_definitions(path: Path = DEFINITIONS) -> dict[str, str]:
    """The policy's frozen definitions, by assertion ID; {} when the file is unreadable."""
    data = A.read_json(path)
    defs = (data or {}).get("definitions") if isinstance(data, dict) else None
    return {k: v for k, v in (defs or {}).items() if isinstance(v, str)}


def plain_definition(text: str) -> str:
    """A definition's first sentence, without its Markdown emphasis and code marks."""
    first = _SENTENCE_END.split(text.strip(), maxsplit=1)[0].strip()
    first = _MARKUP.sub("", first)
    return first if first.endswith(".") else first + "."


@dataclass(frozen=True)
class BriefLine:
    text: str
    source: str
    kind: str = "line"  # "line", "fail" (a failing assertion) or "caveat"
    assertion_id: str | None = None  # a "fail" line's assertion


def briefing_lines(
    run_dir: Path,
    report: dict | None,
    checks: list[R.Check],
    definitions: dict[str, str],
) -> list[BriefLine] | None:
    """The briefing of a finished or recorded run, in order; each line only when its data is
    recorded. None unless the run is intact (changed evidence gets no briefing). `report` is
    None for a deterministic audit run (its outcome.json is at the run's root)."""
    if not checks or not R.intact(checks):
        return None
    run_dir = Path(run_dir)
    verified = verified_paths(checks)
    base = "original/" if report is not None else ""
    lines: list[BriefLine] = []
    hashes = [
        c for c in checks if ":" not in c.item
    ]  # report-key checks are not hashes
    if hashes:
        lines.append(
            BriefLine(
                f"Evidence intact: {len(hashes)} of {len(hashes)} recorded hashes verified "
                "now.",
                "recomputed now from the run's files (each recorded sha256)",
            )
        )
    outcome = _json(run_dir, f"{base}outcome.json", verified)
    if isinstance(outcome, dict) and outcome.get("outcome"):
        statuses = _statuses(outcome)
        counts = {s: sum(1 for _, x in statuses if x == s) for s in A.STATUS_ORDER}
        lines.append(
            BriefLine(
                f"Original outcome: {outcome['outcome']}. Required checks: "
                f"{counts['FAIL']} FAIL, {counts['NOT_ASSESSED']} NOT_ASSESSED, "
                f"{counts['ERROR']} ERROR (of {len(statuses)}).",
                f"{base}outcome.json · outcome, assertions[].status",
            )
        )
        failing = [aid for aid, status in statuses if status == "FAIL"]
        for aid in failing[:BRIEF_FAILS]:
            words = definitions.get(aid)
            lines.append(
                BriefLine(
                    f"{aid} (FAIL): "
                    + (
                        plain_definition(words)
                        if words
                        else f"definition {NOT_RECORDED}."
                    ),
                    "evaluation/assertion_definitions.json · definitions."
                    + aid
                    + " (first sentence)",
                    "fail",
                    aid,
                )
            )
        if len(failing) > BRIEF_FAILS:
            lines.append(
                BriefLine(
                    f"and {len(failing) - BRIEF_FAILS} more",
                    f"{base}outcome.json · assertions[].status",
                    "fail",
                )
            )
    cand_outcome = None
    if report is not None:
        chosen = executed_candidate(run_dir, report, verified)
        if chosen is not None:
            sub = chosen[0]
            cand_outcome = _json(run_dir, f"{sub}/outcome.json", verified) or {}
            before = dict(_statuses(outcome or {}))
            fixed = sum(
                1
                for aid, status in _statuses(cand_outcome)
                if status == "PASS" and before.get(aid) == "FAIL"
            )
            lines.append(
                BriefLine(
                    f"Revision {sub}, executed and verified: {cand_outcome['outcome']}; "
                    f"{fixed} FAIL → PASS.",
                    f"{sub}/execution.json · status; {sub}/outcome.json · outcome, "
                    "assertions[].status",
                )
            )
        if any(
            isinstance(p, dict) and p.get("outcome") == "not_executed_here"
            for p in report.get("proposals") or []
        ):
            lines.append(
                BriefLine(
                    PROPOSALS_NOT_EXECUTED,
                    "agent_report.json · proposals[].outcome (the engine's code only)",
                )
            )
    m_orig = A.primary_metric(outcome) if isinstance(outcome, dict) else None
    if m_orig is not None and m_orig.pooled is not None:
        name = (m_orig.name or "metric").replace("_", " ").capitalize()
        text = (
            f"{name} (pooled), descriptive only: original {A.fmt_metric(m_orig.pooled)}"
        )
        m_cand = A.primary_metric(cand_outcome) if cand_outcome else None
        if (
            m_cand is not None
            and m_cand.pooled is not None
            and m_cand.name == m_orig.name
        ):
            text += f", candidate {A.fmt_metric(m_cand.pooled)}"
        lines.append(
            BriefLine(
                text + ".",
                "outcome.json · descriptive[metric.recomputed_primary] (pooled)",
            )
        )
    lines.append(BriefLine(A.CAVEAT, "the fixed caveat (UI_SPEC §1.1)", "caveat"))
    return lines


def briefing(lines: list[BriefLine], ids: Ids) -> str:
    """The briefing panel: each line as plain, escaped text with its source in a title."""
    label = ids("brief", "label")
    items = []
    for line in lines:
        if line.assertion_id is not None:
            # The same words as the text line: "<assertion> (FAIL): <definition>".
            aid = line.assertion_id
            words = line.text.removeprefix(f"{aid} (FAIL): ")
            body = (
                f'<span class="hud-brief-aid">{esc(aid)}</span> ('
                f'<b class="hud-code hud-c-red">FAIL</b>)&#58; {esc(words)}'
            )
        else:
            body = esc(line.text)
        items.append(
            f'<li class="hud-brief-{line.kind}" title="{esc(line.source)}">{body}</li>'
        )
    return (
        f'<section class="hud hud-brief" aria-labelledby="{label}">'
        f'<div class="hud-ph"><span class="hud-lbl" id="{label}">Briefing</span></div>'
        f'<ul class="hud-brief-lines">{"".join(items)}</ul>'
        '<div class="hud-src">from the run&#39;s verified files and '
        "evaluation/assertion&#95;definitions.json only; no model-written text</div>"
        "</section>"
    )


def briefing_text(lines: list[BriefLine]) -> list[str]:
    """The briefing as plain text lines (what the panel shows, in order)."""
    return [line.text for line in lines]


# -- CSS ----------------------------------------------------------------------------------------------------------
_KEYFRAMES = """
@keyframes hud-fade{from{opacity:0}}
@keyframes hud-seg{from{stroke:#1E2A36}}
@keyframes hud-bad{from{stroke:#67E8F9}}
@keyframes hud-shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-3px)}75%{transform:translateX(3px)}}
@keyframes hud-lock-tl{from{transform:translate(-8px,-8px);opacity:0}}
@keyframes hud-lock-tr{from{transform:translate(8px,-8px);opacity:0}}
@keyframes hud-lock-bl{from{transform:translate(-8px,8px);opacity:0}}
@keyframes hud-lock-br{from{transform:translate(8px,8px);opacity:0}}
@keyframes hud-flip{from{transform:perspective(420px) rotateX(90deg)}}
@keyframes hud-light{from{opacity:0}}
@keyframes hud-draw{from{stroke-dashoffset:1}}
@keyframes hud-node{from{opacity:0}}
"""

_MOTION = f"""
@media (prefers-reduced-motion: no-preference) {{
{_KEYFRAMES}
.hud-anim .hud-a-seg{{animation:hud-seg 80ms ease-out backwards}}
.hud-anim .hud-a-bad{{animation:hud-bad 250ms ease-out backwards}}
.hud-anim .hud-a-shake{{animation:hud-shake 300ms ease-out 250ms 1;transform-box:fill-box;transform-origin:center}}
.hud-anim .hud-a-lock-tl{{animation:hud-lock-tl 400ms ease-out backwards}}
.hud-anim .hud-a-lock-tr{{animation:hud-lock-tr 400ms ease-out backwards}}
.hud-anim .hud-a-lock-bl{{animation:hud-lock-bl 400ms ease-out backwards}}
.hud-anim .hud-a-lock-br{{animation:hud-lock-br 400ms ease-out backwards}}
.hud-anim .hud-a-flip{{animation:hud-flip {int(BEAT2[1] * 1000)}ms ease-out {int(BEAT2[0] * 1000)}ms backwards;transform-origin:50% 50%}}
.hud-anim .hud-a-light{{animation-name:hud-light;animation-timing-function:ease-out;animation-fill-mode:backwards}}
.hud-anim .hud-a-draw{{stroke-dasharray:1;animation:hud-draw {int((BEAT3[1] - 0.1) * 1000)}ms ease-out {int(BEAT3[0] * 1000)}ms backwards}}
.hud-anim .hud-a-head{{animation:hud-fade 100ms ease-out {int((sum(BEAT3) - 0.1) * 1000)}ms backwards}}
.hud-anim .hud-a-node{{animation:hud-node {NODE_MS}ms ease-out backwards}}
.hud-insp[open]>.hud-insp-frame{{animation:hud-fade 120ms ease-out}}
.hud-tg label,.hud-scroll{{transition:background-color 120ms ease-out,color 120ms ease-out,outline-color 120ms ease-out}}
.hud-panes .hud-pane{{transition:opacity 200ms ease-out,visibility 200ms}}
}}
@media (prefers-reduced-motion: reduce) {{
.hud-anim,.hud-anim *,.hud,.hud *{{animation:none !important;transition:none !important}}
}}
"""

CSS = (
    "<style>"
    # The engineering grid, on the recorded page's own container (st-key hook).
    ".st-key-hud-page{container:hud / inline-size;background-color:#0A0F14;background-image:"
    "linear-gradient(rgba(148,163,184,0.04) 1px,transparent 1px),"
    "linear-gradient(90deg,rgba(148,163,184,0.04) 1px,transparent 1px);"
    "background-size:24px 24px}"
    ".hud{font-family:'IBM Plex Sans',sans-serif;color:#E2E8F0;font-size:14px;line-height:1.45}"
    ".hud *,.hud *::before,.hud *::after{box-sizing:border-box}"
    ".hud p{margin:0}"
    ".hud-lbl{font-family:'IBM Plex Sans Condensed',sans-serif;font-weight:500;font-size:11px;"
    "letter-spacing:0.08em;text-transform:uppercase;color:#94A3B8}"
    ".hud-src{display:block;font-family:'IBM Plex Mono',monospace;font-size:11px;line-height:1.35;"
    "color:#94A3B8;overflow-wrap:anywhere;margin-top:4px}"
    ".hud .hud-nr{font-size:13px;color:#94A3B8;margin:6px 0}"
    ".hud-code{font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:500}"
    ".hud-c-red{color:#F87171}.hud-c-green{color:#4ADE80}.hud-c-amber{color:#FBBF24}"
    ".hud-c-violet{color:#C084FC}.hud-c-stone{color:#A8A29E}"
    ".hud-panel{background:#0F1720;border:1px solid #1E2A36;border-radius:4px;padding:8px 12px;"
    "min-width:0}"
    ".hud-ph{display:flex;justify-content:space-between;align-items:baseline;gap:8px;"
    "margin-bottom:2px}"
    ".hud :focus-visible{outline:2px solid #67E8F9;outline-offset:2px}"
    # hero
    ".hud-hero{display:grid;grid-template-columns:124px minmax(0,1fr) 14px minmax(0,1fr);"
    "gap:10px;align-items:stretch}"
    ".hud-hero-single{grid-template-columns:124px minmax(0,1fr)}"
    ".hud-hero-arrow{align-self:center;text-align:center;color:#94A3B8;font-size:18px}"
    ".hud-hero-ring{background:#0F1720;border:1px solid #1E2A36;border-radius:4px;"
    "padding:8px 6px;display:flex;justify-content:center;align-items:center}"
    ".hud-ring{display:flex;flex-direction:column;align-items:center;gap:4px;text-align:center}"
    ".hud-ring svg{display:block}"
    ".hud-ring-track{fill:none;stroke:#1E2A36;stroke-width:8}"
    ".hud-seg{fill:none;stroke-width:8}.hud-seg-ok{stroke:#67E8F9}.hud-seg-bad{stroke:#F87171}"
    ".hud-ring-n{font-family:'IBM Plex Mono',monospace;font-weight:500;font-size:20px;"
    "fill:#67E8F9}"
    ".hud-ring-l{font-family:'IBM Plex Sans Condensed',sans-serif;font-weight:600;"
    "font-size:11px;letter-spacing:0.08em;fill:#67E8F9}"
    ".hud-ring-x{font-family:'IBM Plex Sans Condensed',sans-serif;font-weight:600;"
    "font-size:13px;letter-spacing:0.08em;fill:#F87171}"
    ".hud-ring-cap{display:flex;flex-direction:column;align-items:center}"
    ".hud-ring-cap .hud-src{margin-top:2px;text-align:center}"
    # reticle (the only corner brackets and the only glow)
    ".hud-ret{position:relative;background:#0F1720;border:1px solid #1E2A36;border-radius:2px;"
    "padding:8px 14px 7px;min-width:0}"
    ".hud-t-red{color:#F87171}.hud-t-green{color:#4ADE80}.hud-t-amber{color:#FBBF24}"
    ".hud-t-violet{color:#C084FC}.hud-t-stone{color:#A8A29E}"
    ".hud-br{position:absolute;width:16px;height:16px;border-color:currentColor;"
    "border-style:solid;border-width:0}"
    ".hud-br-tl{top:-1px;left:-1px;border-top-width:2px;border-left-width:2px}"
    ".hud-br-tr{top:-1px;right:-1px;border-top-width:2px;border-right-width:2px}"
    ".hud-br-bl{bottom:-1px;left:-1px;border-bottom-width:2px;border-left-width:2px}"
    ".hud-br-br{bottom:-1px;right:-1px;border-bottom-width:2px;border-right-width:2px}"
    ".hud-ret-code{font-family:'IBM Plex Mono',monospace;font-weight:600;"
    "font-size:clamp(20px,1.95vw,30px);line-height:1.1;letter-spacing:0.02em;margin:2px 0 2px;"
    "overflow-wrap:anywhere}"
    ".hud-ret-none{font-family:'IBM Plex Mono',monospace;color:#A8A29E;margin:6px 0}"
    ".hud-ret-detail{font-family:'IBM Plex Mono',monospace;font-size:13px;color:#E2E8F0}"
    ".hud-ret-exec{font-size:13px;color:#E2E8F0;margin-top:1px;line-height:1.3}"
    ".hud-ret-label{font-size:13px;color:#E2E8F0;margin-top:4px;font-weight:500;line-height:1.3}"
    ".hud-ret-caveat{font-size:12px;color:#94A3B8}"
    # evidence block: pairs on a shared grid (subgrid keeps rows aligned), toggle when the page is under 760 px
    ".hud-ev{position:relative;margin-top:4px}"
    ".hud-panes{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:16px;"
    "row-gap:8px;grid-template-rows:auto auto auto}"
    ".hud-pane{display:grid;grid-row:1/span 3;grid-template-rows:subgrid;row-gap:8px;min-width:0}"
    ".hud-pane-orig{grid-column:1}.hud-pane-cand{grid-column:2}"
    ".hud-ev-single .hud-panes{grid-template-columns:minmax(0,1fr);grid-template-rows:auto}"
    ".hud-ev-single .hud-pane{grid-row:auto;grid-template-rows:none;"
    "grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px 16px}"
    ".hud-ev-single .hud-mx{grid-column:1/-1}"
    ".hud-tg,.hud-tg-in{display:none}"
    ".hud-tg label{font-family:'IBM Plex Sans Condensed',sans-serif;font-weight:600;"
    "font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#E2E8F0;"
    "border:1px solid #1E2A36;padding:6px 12px;cursor:pointer;background:#0F1720}"
    ".hud-tg label:hover{color:#67E8F9}"
    ".hud-tg-in-cand:not(:checked)~.hud-tg .hud-tg-orig,.hud-tg-in-cand:checked~.hud-tg .hud-tg-cand"
    "{background:#67E8F9;color:#0A0F14;border-color:#67E8F9}"
    ".hud-tg-in-orig:focus-visible~.hud-tg .hud-tg-orig,"
    ".hud-tg-in-cand:focus-visible~.hud-tg .hud-tg-cand{outline:2px solid #67E8F9;"
    "outline-offset:2px}"
    "@container hud (max-width:759px){"
    ".hud-hero{grid-template-columns:1fr}.hud-hero-arrow{display:none}"
    ".hud-tg{display:flex;gap:0;margin:4px 0 10px}"
    ".hud-tg-in{display:block;position:absolute;top:0;left:0;width:1px;height:1px;opacity:0;"
    "margin:0;pointer-events:none}"
    ".hud-panes{grid-template-columns:minmax(0,1fr);grid-template-rows:auto}"
    ".hud-pane{grid-row:1;grid-column:1;grid-template-rows:none}"
    ".hud-ev-single .hud-pane{grid-template-columns:minmax(0,1fr)}"
    ".hud-panes .hud-pane-cand,.hud-tg-in-cand:checked~.hud-panes .hud-pane-orig"
    "{opacity:0;visibility:hidden}"
    ".hud-tg-in-cand:checked~.hud-panes .hud-pane-cand{opacity:1;visibility:visible}}"
    # leak map
    ".hud-scroll{overflow-x:auto;max-width:100%}"
    ".hud-scroll:focus-visible{outline:2px solid #67E8F9;outline-offset:2px}"
    ".hud table.hud-lm{border-collapse:separate;border-spacing:2px;margin:0;font-size:11px;"
    "width:auto;border:0}"
    ".hud .hud-lm caption{caption-side:top;text-align:left;font-family:'IBM Plex Sans Condensed',"
    "sans-serif;font-size:10.5px;letter-spacing:0;color:#94A3B8;padding:0 0 3px}"
    ".hud .hud-lm th{font-family:'IBM Plex Mono',monospace;font-weight:400;font-size:11px;"
    "color:#94A3B8;text-align:left;padding:0 4px;border:0;background:none;line-height:1.2}"
    ".hud .hud-lm tbody th{color:#E2E8F0}"
    ".hud .hud-lm td{min-width:68px;height:15px;padding:0 3px;border-radius:2px;"
    "text-align:center;vertical-align:middle;font-size:10px;white-space:nowrap;line-height:1}"
    ".hud .hud-lm td.hud-both{background:rgba(248,113,113,0.18);border:2px solid #F87171;"
    "font-weight:600;color:#E2E8F0}"
    ".hud .hud-lm td.hud-none{background:transparent;border:1px dotted #A8A29E;color:#A8A29E}"
    ".hud .hud-lm td.hud-empty{border:1px dotted #A8A29E;color:#A8A29E;white-space:normal;"
    "text-align:left;padding:4px 8px}"
    ".hud-short,.hud-legend{display:none}"
    ".hud-legend{font-size:11px;color:#94A3B8;margin-top:4px}"
    "@media (max-width:480px){.hud-full{display:none}.hud-short{display:inline}"
    ".hud-legend{display:block}.hud .hud-lm td{min-width:30px}}"
    # fit-scope flow
    ".hud-flow-svg{display:block;width:100%;height:auto}"
    ".hud-fo{fill:#0A0F14;stroke-width:1.5}.hud-fo-red{stroke:#F87171}.hud-fo-muted{stroke:#1E2A36}"
    ".hud-fl{fill:none;stroke-width:1.5}.hud-fl-red{stroke:#F87171}.hud-fl-muted{stroke:#94A3B8}"
    ".hud-fh-red{fill:#F87171}.hud-fh-muted{fill:#94A3B8}"
    ".hud-ft,.hud-ft-m,.hud-ft-s{font-family:'IBM Plex Mono',monospace;font-size:11px;fill:#E2E8F0}"
    ".hud-ft-m{fill:#94A3B8}.hud-ft-s{fill:#E2E8F0}"
    ".hud-ft-f{font-family:'IBM Plex Sans Condensed',sans-serif;font-size:11px;"
    "letter-spacing:0.08em;fill:#94A3B8}"
    ".hud .hud-flow-sum{font-family:'IBM Plex Mono',monospace;font-size:13px;line-height:1.5;"
    "color:#E2E8F0;margin:6px 0 2px;overflow-wrap:anywhere}"
    ".hud-lane{stroke:#1E2A36;stroke-width:1;stroke-dasharray:2 3}"
    # check matrix
    ".hud ol.hud-tiles{list-style:none;margin:0;padding:0;display:grid;gap:4px}"
    ".hud li.hud-tile{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;background:#0A0F14;"
    "border:1px solid #1E2A36;border-radius:2px;padding:4px 8px;font-family:'IBM Plex Mono',"
    "monospace;font-size:12px;margin:0}"
    ".hud-tile .hud-code{min-width:7.2em}"
    ".hud .hud-tiles-pair li.hud-tile{display:grid;grid-template-columns:7.2em minmax(0,1fr) 7em;"
    "gap:4px 8px}"
    ".hud-tiles-pair .hud-move{text-align:right}"
    # the inspection frame (a FAIL, NOT_ASSESSED or ERROR tile, opened in place)
    ".hud li.hud-tile.hud-tile-insp{display:block;padding:0}"
    ".hud summary.hud-tile-row{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;"
    "padding:4px 8px;cursor:pointer;list-style:none;border-radius:2px}"
    ".hud summary.hud-tile-row::-webkit-details-marker{display:none}"
    ".hud summary.hud-tile-row::marker{content:''}"
    ".hud .hud-tiles-pair summary.hud-tile-row{display:grid;"
    "grid-template-columns:7.2em minmax(0,1fr) 7em;gap:4px 8px;align-items:baseline}"
    ".hud-tile-end{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:2px 8px;"
    "margin-left:auto;text-align:right}"
    ".hud .hud-tiles-pair li.hud-tile.hud-tile-insp{display:block}"
    ".hud-insp-cue{font-family:'IBM Plex Sans Condensed',"
    "sans-serif;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#94A3B8}"
    ".hud-insp>summary .hud-insp-cue::after{content:'Inspect'}"
    ".hud-insp[open]>summary .hud-insp-cue::after{content:'Close'}"
    ".hud summary.hud-tile-row:hover .hud-insp-cue{color:#67E8F9}"
    ".hud summary.hud-tile-row:focus-visible{outline:2px solid #67E8F9;outline-offset:2px}"
    ".hud-insp-frame{position:relative;margin:2px 8px 8px;padding:12px 14px 10px;"
    "background:#0F1720;border:1px solid #1E2A36;border-radius:2px;color:#67E8F9;"
    "font-family:'IBM Plex Sans',sans-serif}"
    ".hud-insp-frame .hud-lbl{display:block;margin:8px 0 2px}"
    ".hud dl.hud-insp-kv{display:grid;grid-template-columns:fit-content(42%) "
    "minmax(0,1fr);gap:3px 14px;margin:0;font-family:'IBM Plex Mono',monospace;font-size:13px;"
    "line-height:1.45}"
    ".hud .hud-insp-kv dt{color:#94A3B8;font-weight:400;overflow-wrap:anywhere;margin:0}"
    ".hud .hud-insp-kv dd{color:#E2E8F0;margin:0;overflow-wrap:anywhere}"
    ".hud .hud-insp-ev dd{word-break:break-all}"
    "@container hud (max-width:759px){.hud dl.hud-insp-kv{grid-template-columns:minmax(0,1fr);"
    "gap:0}.hud .hud-insp-kv dd{margin:0 0 4px 12px}}"
    ".hud ul.hud-insp-list{margin:0;padding-left:18px;font-size:13px;color:#E2E8F0}"
    ".hud .hud-insp-list li{margin:0 0 2px}"
    ".hud p.hud-insp-none{margin:0;font-size:13px;color:#94A3B8}"
    ".hud-insp-frame .hud-src{color:#94A3B8}"
    "@container hud (max-width:759px){.hud .hud-tiles-pair li.hud-tile,"
    ".hud .hud-tiles-pair summary.hud-tile-row{grid-template-columns:7.2em minmax(0,1fr)}"
    ".hud-tiles-pair .hud-move{grid-column:2;text-align:left}.hud-move:empty{display:none}"
    ".hud-tiles-pair .hud-tile-end{grid-column:2;justify-content:flex-start}}"
    ".hud-aid{color:#E2E8F0;overflow-wrap:anywhere}"
    ".hud-changed{border-left:2px solid #E2E8F0}"
    ".hud-move{margin-left:auto;color:#94A3B8;font-size:11px}"
    # mission track and budget gauge
    ".hud-track,.hud-gauge{background:#0F1720;border:1px solid #1E2A36;border-radius:4px;"
    "padding:12px 16px;margin-bottom:8px}"
    ".hud ol.hud-stages{display:flex;flex-wrap:wrap;align-items:center;gap:6px 0;list-style:none;"
    "margin:0;padding:0}"
    ".hud li.hud-stage{display:flex;align-items:center;margin:0;padding:0}"
    ".hud-stage+.hud-stage::before{content:'';display:block;width:12px;height:1px;"
    "background:#1E2A36;margin:0 4px}"
    ".hud-stage-n{font-family:'IBM Plex Sans Condensed',sans-serif;font-weight:500;font-size:11px;"
    "letter-spacing:0.08em;color:#E2E8F0;border:1px solid #1E2A36;border-radius:2px;"
    "padding:2px 6px}"
    ".hud-stage-end .hud-code{border:1px solid currentColor;border-radius:2px;padding:1px 6px}"
    ".hud-stage-now .hud-stage-n{border-color:#E2E8F0}"
    ".hud-cnts{display:flex;flex-wrap:wrap;gap:8px 28px;margin-top:10px}"
    ".hud-cnt{display:flex;align-items:center;gap:8px}"
    ".hud-cnt-v,.hud-gb-v{font-family:'IBM Plex Mono',monospace;font-size:13px;color:#E2E8F0}"
    ".hud-cells{display:flex;gap:2px}.hud-cells span{width:8px;height:8px;background:#1E2A36;"
    "border-radius:1px}.hud-cells span.on{background:#E2E8F0}"
    ".hud-gb{display:grid;grid-template-columns:150px auto;gap:2px 12px;align-items:center;"
    "margin:4px 0}"
    ".hud-bar{grid-column:1/-1;display:block;height:6px;background:#1E2A36;border-radius:1px;"
    "overflow:hidden}.hud-bar span{display:block;height:100%;background:#E2E8F0}"
    # the briefing
    ".hud-brief{background:#0F1720;border:1px solid #1E2A36;border-radius:4px;"
    "padding:10px 16px 8px}"
    ".hud ul.hud-brief-lines{list-style:none;margin:4px 0 2px;padding:0;display:grid;gap:3px}"
    ".hud ul.hud-brief-lines li{margin:0;font-size:14px;line-height:1.45;color:#E2E8F0}"
    ".hud li.hud-brief-fail{padding-left:16px}"
    ".hud-brief-aid{font-family:'IBM Plex Mono',monospace;font-size:13px;color:#E2E8F0}"
    ".hud li.hud-brief-caveat{font-size:13px;color:#94A3B8}"
    # full hashes, field labels and HUD state panels
    ".hud.hud-flabel{margin:0}"
    ".hud.hud-hash{font-family:'IBM Plex Mono',monospace;font-size:13px;line-height:1.5;"
    "color:#E2E8F0;overflow-wrap:anywhere;word-break:break-all;margin:0;background:#0A0F14;"
    "border:1px solid #1E2A36;border-radius:2px;padding:8px 12px}"
    ".hud-state{background:#0F1720;border:1px solid #1E2A36;border-left:2px solid #A8A29E;"
    "border-radius:4px;padding:10px 14px}"
    ".hud-state-red{border-left-color:#F87171}.hud-state-amber{border-left-color:#FBBF24}"
    ".hud-state-violet{border-left-color:#C084FC}.hud-state-stone{border-left-color:#A8A29E}"
    ".hud-state .hud-code{font-size:13px}"
    ".hud .hud-state-why,.hud .hud-state-next{margin:4px 0 0;color:#E2E8F0;font-size:14px}"
    ".hud-state-next .hud-lbl{margin-right:6px}"
    + _MOTION.replace("\n", "")
    + "</style>"
)


def once_css(played: bool) -> str:
    """First render of a run only: the cards fade in once (150 ms) and, on a changed run, the
    evidence-changed panel fades in after the ring's shake. Empty when played."""
    if played:
        return ""
    return (
        "<style>@media (prefers-reduced-motion: no-preference){"
        ".st-key-hud-page [class*='st-key-card-']{animation:hud-fade 150ms ease-out backwards}"
        ".st-key-hud-page .st-key-integrity-failed{animation:hud-fade 150ms ease-out 550ms "
        "backwards}}</style>"
    )


# -- contrast (docs/UI_DESIGN_HUD.md §7; checked by tests) ----------------------------------------------------
def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def over(fg: str, alpha: float, bg: str) -> str:
    """`fg` at `alpha` composited over the opaque `bg`, as hex."""
    mixed = (
        round(alpha * f + (1 - alpha) * b)
        for f, b in zip(_rgb(fg), _rgb(bg), strict=True)
    )
    return "#" + "".join(f"{v:02X}" for v in mixed)


def contrast(a: str, b: str) -> float:
    def lum(h):
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

        r, g, bl = _rgb(h)
        return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(bl)

    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


GRID_LINE = over("#94A3B8", 0.04, BG)
RED_TINT_CELL = over(RED, 0.18, PANEL)
BADGE_BG = {
    "red": "#30242B",
    "green": "#17332D",
    "orange": "#302F21",
    "violet": "#28263F",
    "gray": "#242A32",
    "blue": "#2D343D",
}
CAPTION = {bg: over(TEXT, 0.6, bg) for bg in (PANEL, BG)}
# (text, background, where): every text/background pair the HUD screen uses.
CONTRAST_PAIRS = [
    (TEXT, BG, "body text, insets, model-written text"),
    (TEXT, PANEL, "cards and panels"),
    (TEXT, GRID_LINE, "text over a grid line"),
    (TEXT, RED_TINT_CELL, "'on both sides' cell"),
    (MUTED, BG, "HUD labels on the page"),
    (MUTED, PANEL, "HUD labels and sources in panels"),
    (MUTED, GRID_LINE, "labels over a grid line"),
    (ACCENT, BG, "accent on the page"),
    (ACCENT, PANEL, "ring count, links, toggle hover"),
    (BG, ACCENT, "selected toggle and primary button text"),
    (RED, BG, "FAIL tiles"),
    (RED, PANEL, "VIOLATION_FOUND reticle, FAIL codes"),
    (RED, RED_TINT_CELL, "red on the tinted cell"),
    (GREEN, BG, "PASS tiles"),
    (GREEN, PANEL, "NO_VIOLATION_FOUND reticle, PASS codes"),
    (AMBER, BG, "NOT_ASSESSED tiles"),
    (AMBER, PANEL, "amber codes"),
    (VIOLET, BG, "ERROR tiles"),
    (VIOLET, PANEL, "ERROR codes"),
    (STONE, BG, "NOT_SUPPORTED tiles"),
    (STONE, PANEL, "'0 shared' cells, NOT_SUPPORTED"),
    (RED, BADGE_BG["red"], "red badge and alert"),
    (GREEN, BADGE_BG["green"], "green badge and alert"),
    (AMBER, BADGE_BG["orange"], "amber badge, model-written badge"),
    (VIOLET, BADGE_BG["violet"], "violet badge and alert"),
    (STONE, BADGE_BG["gray"], "gray badge (NON-LIVE)"),
    (TEXT, BADGE_BG["blue"], "neutral badge (LIVE RUN, Recorded run)"),
    (CAPTION[PANEL], PANEL, "Streamlit caption in a card"),
    (CAPTION[BG], BG, "Streamlit caption on the page"),
    # phase 2
    (TEXT, BADGE_BG["blue"], "changed row of the per-assertion table"),
    (MUTED, PANEL, "disabled button text (transparent button on a card)"),
    (MUTED, BG, "HUD labels in the decision inset and the inspection frame"),
    (TEXT, BG, "full hashes, the decision inset, the inspection frame's values"),
    (AMBER, BG, "state-panel edge and code beside the page colour"),
    (
        ACCENT,
        PANEL,
        "approval and inspection frame corner brackets (non-text, 3:1 needed)",
    ),
]
