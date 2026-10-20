"""The one-page audit report (UI restructure slice 3, part D): a self-contained, printable HTML
file built from a run's verified files only.

`build` is called only after the run passed the one verification gate (`results.gate`); it
checks again and raises `NotIntact` otherwise, so a failed verification never yields a report.
The report holds fixed copy (`atlas.ui.copy`, `assertion_labels.json`) filled with values from
the verified files: the claim, the outcomes, the checks, the reason sentences the page shows,
the approval and sealed-run facts, and the recorded hashes. It never includes model-written
text (no rationale, no raw reply, no diff). Every value is escaped (`hud.esc`). There are no
scripts, no links, no images and nothing fetched; one inline style sheet with a print style.

Deterministic apart from the generated-at time, which comes from the injected `now`. Nothing
executes here: no subprocess, no network. The ATLAS commit is read from the repository's git
metadata as files (no git command); when it cannot be read, it is left out.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import recorded as R
from atlas.ui.catalogue import ROOT

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_SAFE = re.compile(r"[^A-Za-z0-9_-]+")

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #ffffff; color: #111827;
  font: 14px/1.5 "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif; }
main { max-width: 780px; margin: 0 auto; padding: 28px 24px 32px; }
h1 { font-size: 22px; margin: 0 0 2px; letter-spacing: 0.02em; }
h2 { font-size: 15px; margin: 18px 0 6px; padding-bottom: 3px; border-bottom: 1px solid #d1d5db;
  break-after: avoid; page-break-after: avoid; }
p { margin: 4px 0; }
.tag { font-size: 15px; color: #1f2937; }
.meta, .note, footer { color: #4b5563; font-size: 12px; }
.claim { font-size: 16px; font-weight: 600; }
.code { font-family: "IBM Plex Mono", Consolas, monospace; font-weight: 600; }
.caveat { font-style: italic; color: #374151; }
table { width: 100%; border-collapse: collapse; margin: 6px 0; font-size: 12.5px; }
th, td { text-align: left; vertical-align: top; padding: 4px 6px; border: 1px solid #d1d5db; }
th { background: #f3f4f6; font-weight: 600; }
tr { break-inside: avoid; page-break-inside: avoid; }
td.id, td.hash { font-family: "IBM Plex Mono", Consolas, monospace; font-size: 11.5px;
  overflow-wrap: anywhere; word-break: break-all; }
.FAIL { color: #b91c1c; font-weight: 600; }
.PASS { color: #15803d; font-weight: 600; }
.NOT_ASSESSED, .ERROR { color: #92400e; font-weight: 600; }
ul { margin: 4px 0; padding-left: 20px; }
li { margin: 2px 0; }
footer { margin-top: 18px; padding-top: 6px; border-top: 1px solid #d1d5db; }
@page { size: portrait; margin: 9mm 11mm; }
@media print {
  body { font-size: 8.4pt; line-height: 1.28; }
  main { max-width: none; padding: 0; }
  h1 { font-size: 13pt; margin: 0; }
  h2 { font-size: 9.6pt; margin: 6px 0 2px; padding-bottom: 1px; }
  p { margin: 1px 0; }
  .tag { font-size: 9pt; }
  .claim { font-size: 9.6pt; }
  .meta, .note, footer { font-size: 7.4pt; }
  table { font-size: 7.6pt; margin: 2px 0; }
  th, td { padding: 1px 4px; }
  td.id, td.hash { font-size: 7pt; }
  ul { margin: 1px 0; padding-left: 14px; }
  li { margin: 0; }
  footer { margin-top: 6px; padding-top: 3px; }
}
"""


class NotIntact(Exception):
    """The run did not verify: no report is built."""


@dataclass(frozen=True)
class Report:
    file_name: str
    html: str


def atlas_commit(root: Path = ROOT) -> str | None:
    """The checked-out commit, read from the repository's git metadata as plain files (a
    worktree's `.git` file, HEAD, the ref, packed-refs); None when it cannot be read."""
    try:
        dot = Path(root) / ".git"
        if dot.is_file():
            text = dot.read_text(encoding="utf-8").strip()
            if not text.startswith("gitdir:"):
                return None
            gitdir = Path(text.split(":", 1)[1].strip())
            if not gitdir.is_absolute():
                gitdir = (Path(root) / gitdir).resolve()
        elif dot.is_dir():
            gitdir = dot
        else:
            return None
        common = gitdir
        if (gitdir / "commondir").is_file():
            common = (
                gitdir / (gitdir / "commondir").read_text("utf-8").strip()
            ).resolve()
        head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
        if _HEX40.match(head):
            return head
        if not head.startswith("ref: "):
            return None
        ref = head[5:].strip()
        for base in (gitdir, common):
            path = base / ref
            if path.is_file():
                value = path.read_text(encoding="utf-8").strip()
                return value if _HEX40.match(value) else None
        packed = common / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref and _HEX40.match(parts[0]):
                    return parts[0]
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return None


def file_name(subject: str, outcome: str | None) -> str:
    """`atlas-audit-<case or run id>-<outcome>.html` (letters, digits, `_` and `-` only); the
    outcome is the original evaluation's verified outcome code."""
    subject = _SAFE.sub("-", subject).strip("-") or "run"
    code = _SAFE.sub("-", outcome or "").strip("-") or "NO_OUTCOME"
    return f"atlas-audit-{subject}-{code}.html"


def _e(value) -> str:
    return H.esc(value)


def _status(value) -> str:
    text = value if isinstance(value, str) and value else "—"
    cls = value if value in ("PASS", "FAIL", "NOT_ASSESSED", "ERROR") else ""
    return f'<td class="{cls}">{_e(text)}</td>'


def _ul(items: list[str]) -> str:
    return (
        "<ul>" + "".join(f"<li>{_e(x)}</li>" for x in items) + "</ul>" if items else ""
    )


def build(
    run: R.RecordedRun,
    report: dict | None,
    checks: list[R.Check],
    *,
    subject: str,
    subject_title: str | None = None,
    citation: str | None = None,
    now: Callable[[], datetime] | None = None,
    commit: str | None = None,
) -> Report:
    """The report for a verified run. `subject`: the case key (Overview) or the run's ID;
    `subject_title`: the case title, when there is one; `citation`: the dataset citation the
    page shows for this run; `now`: the clock (UTC); `commit`: the ATLAS commit (read from the
    git metadata when not given)."""
    from atlas.ui import story

    if not checks or not R.intact(checks):
        raise NotIntact()
    if run.kind == R.AGENT and report is None:
        raise NotIntact()
    stamp = (now or (lambda: datetime.now(UTC)))().astimezone(UTC)
    commit = commit if commit is not None else atlas_commit()
    verified = H.verified_paths(checks)
    descriptions = H.load_descriptions()
    parts: list[str] = []

    # Claim.
    claim = None
    source = R.claim_source(run)
    if source is not None and source.relative_to(run.path).as_posix() in verified:
        try:
            claim = R.read_claim(source)
        except Exception:  # noqa: BLE001 - an unreadable manifest is stated, never guessed
            claim = None
    statement = getattr(claim, "statement", None)

    if run.kind == R.AGENT:
        hud = H.build(run.path, report, checks, run.label, bundled=True)
        f = story.facts(run, report, checks, hud)
        told = story.summaries(hud, f, checks)
        verdict = story.verdict(hud, f)
        orig_code = hud.original.code
        cand_code = hud.candidate.code if hud.candidate is not None else None
        rows = [(r.assertion_id, r.original, r.candidate) for r in hud.matrix]
        has_after = hud.candidate is not None
        observed = hud.observed_orig
        orig_outcome = f.orig_outcome or {}
        banner = story.banner_text(report, A.run_finished_utc(report))
    else:
        outcome = H.verified_json(run.path, "outcome.json", verified) or {}
        orig_code = outcome.get("outcome")
        cand_code, has_after, told, verdict, f = None, False, {}, [], None
        statuses = [
            (str(a.get("assertion_id")), a.get("status"))
            for a in outcome.get("assertions") or []
            if isinstance(a, dict) and a.get("assertion_id")
        ]
        rows = [(aid, status, None) for aid, status in statuses]
        observed = {
            str(a.get("assertion_id")): a.get("observed")
            for a in outcome.get("assertions") or []
            if isinstance(a, dict) and isinstance(a.get("observed"), dict)
        }
        orig_outcome = outcome
        banner = None

    # Header.
    who = (
        C.REPORT_SUBJECT_CASE.format(title=subject_title)
        if subject_title
        else C.REPORT_SUBJECT_RUN.format(run=run.label)
    )
    meta = who + (C.REPORT_SEP + banner if banner else "")
    parts.append(
        f"<header><h1>{_e(C.REPORT_TITLE)}</h1>"
        f'<p class="tag">{_e(C.TAGLINE)}</p><p class="meta">{_e(meta)}</p></header>'
    )
    # The claim.
    parts.append(f"<section><h2>{_e(C.REPORT_CLAIM)}</h2>")
    if statement:
        parts.append(
            f'<p class="note">{_e(C.REPORT_CLAIM_INTRO)}</p><p class="claim">{_e(statement)}</p>'
        )
    else:
        parts.append(f"<p>{_e(C.NO_MANIFEST)}</p>")
    parts.append("</section>")
    # The outcome, before and after.
    after = (
        f'<span class="code">{_e(cand_code or H.NOT_RECORDED)}</span>'
        if has_after
        else _e(C.REPORT_NO_REVISION)
    )
    parts.append(
        f"<section><h2>{_e(C.REPORT_OUTCOME)}</h2><table>"
        f"<tr><th>{_e(C.REPORT_BEFORE)}</th>"
        f'<td><span class="code">{_e(orig_code or H.NOT_RECORDED)}</span></td></tr>'
        f"<tr><th>{_e(C.REPORT_AFTER)}</th><td>{after}</td></tr></table>"
        f'<p class="caveat">{_e(A.CAVEAT)}</p>'
        + "".join(f"<p>{_e(v)}</p>" for v in verdict)
        + "</section>"
    )
    # The checks.
    head = (
        f"<tr><th>{_e(C.REPORT_COL_CHECK)}</th><th>{_e(C.REPORT_COL_ID)}</th>"
        f"<th>{_e(C.REPORT_COL_BEFORE)}</th>"
        + (f"<th>{_e(C.REPORT_COL_AFTER)}</th>" if has_after else "")
        + "</tr>"
    )
    body = "".join(
        f'<tr><td>{_e(descriptions.get(aid, aid))}</td><td class="id">{_e(aid)}</td>'
        + _status(before)
        + (_status(later) if has_after else "")
        + "</tr>"
        for aid, before, later in rows
    )
    parts.append(
        f"<section><h2>{_e(C.REPORT_CHECKS)}</h2><table><thead>{head}</thead>"
        f"<tbody>{body}</tbody></table></section>"
    )
    # The leak: the step 2 summary and the reason sentences of the original's FAILs.
    leak = [told[2]] if told.get(2) else []
    for aid, before, _later in rows:
        if before == "FAIL":
            leak += H.reasons(aid, observed.get(aid))
    if leak:
        parts.append(f"<section><h2>{_e(C.REPORT_LEAK)}</h2>{_ul(leak)}</section>")
    # Approval and the sealed run (step 4), with the proposals' recorded outcomes (step 3).
    parts.append(f"<section><h2>{_e(C.REPORT_APPROVAL)}</h2>")
    if f is not None:
        parts.append(f"<p>{_e(told[4])}</p>")
        parts.append(_ul([told[3], *f.approvals, *f.executions]))
    else:
        parts.append(f"<p>{_e(C.REPORT_AUDIT_ONLY)}</p>")
    parts.append("</section>")
    # Evidence.
    count = H.integrity_count(checks)
    hashes = [
        (C.REPORT_HASH_OUTCOME.format(rel=c.item), c.recorded)
        for c in checks
        if ":" not in c.item and c.item.endswith("outcome.json")
    ]
    if f is not None:
        for e in f.approval_events:
            if e.get("decision") == "approved" and e.get("candidate_hash"):
                who_ = story._who(report, e.get("kind"), e.get("candidate_hash"))
                hashes.append(
                    (C.REPORT_HASH_APPROVED.format(who=who_), e.get("candidate_hash"))
                )
    table = "".join(
        f'<tr><td>{_e(item)}</td><td class="hash">{_e(value)}</td></tr>'
        for item, value in hashes
    )
    parts.append(
        f"<section><h2>{_e(C.REPORT_EVIDENCE)}</h2>"
        f"<p>{_e(C.REPORT_INTEGRITY.format(v=count.total - count.differ, t=count.total))}</p>"
        f"<table><thead><tr><th>{_e(C.REPORT_HASH_COL_ITEM)}</th>"
        f"<th>{_e(C.REPORT_HASH_COL_VALUE)}</th></tr></thead><tbody>{table}</tbody></table>"
        f'<p class="note">{_e(C.INTEGRITY_NOTE_PLAIN)}</p>'
        f'<p class="note">{_e(C.REPORT_MODEL_TEXT_NOTE)}</p></section>'
    )
    if citation:
        parts.append(
            f"<section><h2>{_e(C.REPORT_DATA)}</h2><p>{_e(citation)}</p></section>"
        )
    parts.append(
        "<section><p>"
        + _e(C.REPORT_WHY.format(label=C.WHY_LABEL, text=C.WHY_TEXT, url=C.WHY_URL))
        + "</p></section>"
    )
    # Footer.
    policy = (
        orig_outcome.get("policy_version") if isinstance(orig_outcome, dict) else None
    )
    foot = [
        *([C.REPORT_COMMIT.format(commit=commit)] if commit else []),
        *([C.REPORT_POLICY.format(policy=policy)] if policy else []),
        C.REPORT_GENERATED.format(utc=stamp.strftime("%Y-%m-%dT%H:%M:%SZ")),
    ]
    parts.append(f"<footer>{_e(C.REPORT_SEP.join(foot))}</footer>")

    html = (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_e(C.REPORT_TITLE + C.REPORT_SEP + subject)}</title>"
        f"<style>{CSS}</style></head><body><main>"
        + "".join(parts)
        + "</main></body></html>\n"
    )
    return Report(file_name(subject, orig_code), html)
