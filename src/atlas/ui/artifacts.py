"""Read what the engine wrote, for display. Nothing here decides an outcome.

Every value the page shows comes from a run's files (`agent_report.json`, `agent_log.jsonl`,
`outcome.json`, `report.json`, `proposals/`); the key paths are those of docs/UI_SPEC.md.
Hashes shown next to files are recomputed from the bytes on disk and compared with the hash
the engine recorded, never assumed.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

OUTCOME_LABELS = {
    "VIOLATION_FOUND": "The evaluation breaks at least one requirement of this claim.",
    "NO_VIOLATION_FOUND": "Every required check passed within the coverage shown.",
    "INCONCLUSIVE": "No violation established, but required evidence is incomplete.",
    "NOT_SUPPORTED": "ATLAS can't assess this claim or project in V1.",
}
CAVEAT = "This does not say the scientific claim is true or false."
OUTCOME_COLORS = {
    "VIOLATION_FOUND": "red",
    "NO_VIOLATION_FOUND": "green",
    "INCONCLUSIVE": "orange",
    "NOT_SUPPORTED": "gray",
}
STATUS_COLORS = {
    "FAIL": "red",
    "PASS": "green",
    "NOT_ASSESSED": "orange",
    "ERROR": "violet",
}
STATUS_ORDER = {"FAIL": 0, "ERROR": 1, "NOT_ASSESSED": 2, "PASS": 3}
FAILED_STATES = ("ERROR", "BUDGET_EXHAUSTED", "NEEDS_INPUT")
MODEL_LABEL = "model-written text; not evidence and not an outcome"

# GAP-10: next actions keyed to the engine's existing reason codes and intake reasons.
NEXT_ACTIONS = {
    "missing_metadata": "Declare the missing identity columns in atlas_manifest.json "
    "(columns.group_id, columns.unit_id or the dependence entries), then run again.",
    "not_executed": "Run again with Docker available and approve the original when asked; "
    "nothing was evaluated.",
    "unknown_ancestry": "Keep feature construction inside the supported adapter path so the "
    "fitted state's ancestry is recorded.",
    "zero_fit": "Fit the model through the supported adapter calls; no fit was recorded.",
    "coverage_gap": "Route every fit and transform through the supported adapter path.",
    "no_supported_rule": "Declare a dependence rule ATLAS supports for this claim type.",
    "no_declared_rule": "Declare the dependence rule (claim.dependence) in the manifest.",
    "unresolved_duplicate_candidates": "Add observation identifiers so duplicate rows can be "
    "told apart.",
    "empty_evaluation": "Check that every evaluation fold contains rows.",
    "evidence_invalid": "Rerun; the evidence failed its integrity checks.",
    "unimplemented_assertion": "This check is not implemented in V1; the result cannot "
    "cover it.",
}
INTAKE_ACTIONS = (
    (
        "is not supported in V1 (combined or unknown)",
        (
            "Split the claim into one supported type (same_population, unseen_group or "
            "future_time) and audit each part separately."
        ),
    ),
    (
        "task is not classification",
        (
            "V1 assesses classification only: declare at least two classes in "
            "columns.class_map."
        ),
    ),
    ("table format", "Provide the table as CSV or Parquet."),
)
INTAKE_FALLBACK = "Fix atlas_manifest.json as the reason says, then run again."


def next_action_for_intake(reason: str | None) -> str:
    for needle, action in INTAKE_ACTIONS:
        if reason and needle in reason:
            return action
    return INTAKE_FALLBACK


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_log(run_dir: Path) -> list[dict]:
    """The log so far. A line still being written (no newline yet) is left for next time."""
    try:
        text = (Path(run_dir) / "agent_log.jsonl").read_text(encoding="utf-8")
    except OSError:
        return []
    events = []
    for line in text.split("\n")[:-1]:
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


@dataclass
class Trace:
    states: list[dict]
    attempts: list[dict]
    tools: list[dict]
    approvals: list[dict]
    refused: list[dict]

    @property
    def current_state(self) -> str | None:
        return self.states[-1]["state"] if self.states else None


def trace(events: list[dict]) -> Trace:
    by = lambda name: [e for e in events if e.get("event") == name]
    return Trace(
        states=by("state"),
        attempts=by("model_attempt"),
        tools=by("tool"),
        approvals=by("approval"),
        refused=by("model_request_refused"),
    )


def sort_required(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: STATUS_ORDER.get(r.get("status"), 9))


def status_counts(rows: list[dict]) -> dict[str, int]:
    counts = {s: 0 for s in STATUS_ORDER}
    for r in rows:
        counts[r.get("status")] = counts.get(r.get("status"), 0) + 1
    return counts


def assertion(outcome: dict | None, assertion_id: str) -> dict | None:
    for a in (outcome or {}).get("assertions", []):
        if a.get("assertion_id") == assertion_id:
            return a
    return None


def descriptive(outcome: dict | None, result_id: str) -> dict | None:
    for d in (outcome or {}).get("descriptive", []):
        if d.get("result_id") == result_id:
            return d
    return None


@dataclass
class Metric:
    name: str
    pooled: float | None
    observations: int | None
    pooled_complete: bool | None
    mean_over_folds: float | None
    folds: int | None
    folds_complete: bool | None
    per_fold: list[dict]
    limitations: list[str]


def primary_metric(outcome: dict | None) -> Metric | None:
    """`descriptive[result_id=metric.recomputed_primary]`: descriptive only, never the outcome."""
    d = descriptive(outcome, "metric.recomputed_primary")
    if not d or not d.get("available", True):
        return None
    obs = d.get("observed") or {}
    name = obs.get("primary_metric")
    agg = (obs.get("aggregates") or {}).get("development_eval", {}).get(name) or {}
    pooled = agg.get("pooled") or {}
    folds = agg.get("mean_over_folds") or {}
    return Metric(
        name=name,
        pooled=pooled.get("value"),
        observations=pooled.get("observations"),
        pooled_complete=pooled.get("complete"),
        mean_over_folds=folds.get("value"),
        folds=folds.get("folds"),
        folds_complete=folds.get("complete"),
        per_fold=[
            {"fold": f.get("fold"), name: f.get(name), "usable": f.get("usable")}
            for f in obs.get("per_fold", [])
        ],
        limitations=list(d.get("limitations") or []),
    )


def reported_metric(outcome: dict | None) -> list[dict] | None:
    """`assertions[metric.reported_matches_recomputed].observed.entries[]`, if declared."""
    a = assertion(outcome, "metric.reported_matches_recomputed")
    if a is None:
        return None
    rows = []
    for e in (a.get("observed") or {}).get("entries", []):
        entry = e.get("entry") or {}
        rows.append(
            {
                "reported": entry.get("value"),
                "recomputed": (e.get("recomputed") or {}).get("value"),
                "abs_difference": e.get("abs_difference"),
                "tolerance": e.get("tolerance"),
                "status": e.get("status"),
            }
        )
    return rows


def fmt_metric(value) -> str:
    return "n/a" if value is None else f"{value:.4f}"


@dataclass
class ProposalView:
    record: dict
    diff_text: str | None
    diff_file_sha256: str | None
    new_source_text: str | None
    new_source_file_sha256: str | None

    @property
    def diff_hash_matches(self) -> bool | None:
        if self.diff_file_sha256 is None:
            return None
        return self.diff_file_sha256 == self.record.get("diff_sha256")


def _inside(run_dir: Path, rel: str | None) -> Path | None:
    """A report-named path, only if it stays inside the run directory."""
    if not rel:
        return None
    path = (run_dir / rel).resolve()
    try:
        path.relative_to(run_dir.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def proposals(run_dir: Path, report: dict | None) -> list[ProposalView]:
    views = []
    for record in (report or {}).get("proposals", []):
        diff = _inside(run_dir, record.get("diff_path"))
        source = _inside(run_dir, record.get("new_source_path"))
        views.append(
            ProposalView(
                record=record,
                diff_text=diff.read_text(encoding="utf-8", errors="replace")
                if diff
                else None,
                diff_file_sha256=sha256_file(diff) if diff else None,
                new_source_text=source.read_text(encoding="utf-8", errors="replace")
                if source
                else None,
                new_source_file_sha256=sha256_file(source) if source else None,
            )
        )
    return views


@dataclass
class ExportFile:
    label: str
    path: Path
    sha256: str
    recorded: (
        str | None
    )  # the hash the engine recorded for this file, if it records one

    @property
    def matches(self) -> bool | None:
        return None if self.recorded is None else self.recorded == self.sha256


def exports(run_dir: Path, report: dict | None) -> list[ExportFile]:
    """Downloads (§4.7) with SHA-256 recomputed from disk and the engine's recorded hash."""
    run_dir = Path(run_dir)
    out = []

    def add(label, rel, recorded=None):
        path = run_dir / rel
        if path.is_file():
            out.append(ExportFile(label, path, sha256_file(path), recorded))

    if report is None:  # deterministic audit run
        add("outcome.json", "outcome.json")
        add("report.json", "report.json")
        return out
    comparison = report.get("comparison") or {}
    original = (comparison.get("original") or {}).get("evidence_sha256") or {}
    add("agent_report.json", "agent_report.json")
    add(
        "agent_log.jsonl",
        "agent_log.jsonl",
        (report.get("agent_log") or {}).get("sha256"),
    )
    add("original/outcome.json", "original/outcome.json", original.get("outcome.json"))
    add("original/report.json", "original/report.json", original.get("report.json"))
    for i, c in enumerate(comparison.get("candidates") or [], start=1):
        rel = Path(c.get("run_dir") or f"candidates/c{i}").name
        add(
            f"candidates/{rel}/outcome.json",
            f"candidates/{rel}/outcome.json",
            (c.get("evidence_sha256") or {}).get("outcome.json"),
        )
    add("preflight.json", "preflight.json")
    return out


def short_time(iso: str | None) -> str:
    if not iso:
        return "unknown time"
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return iso


def run_finished_utc(report: dict | None) -> str | None:
    states = (report or {}).get("states") or []
    return states[-1].get("time_utc") if states else None
