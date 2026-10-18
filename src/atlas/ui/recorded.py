"""Recorded runs (T-07 follow-up, slice 4h): finished run directories opened read-only.

Nothing here executes, approves or evaluates anything. A recorded run is shown only from its
own files, and only after every hash the engine recorded for them has been recomputed from the
bytes on disk (`verify`). A file that changed, is missing or lies outside the run directory,
or a report outcome that differs from its verified `outcome.json`, makes the run not intact:
the page then shows "evidence changed since recording" and no outcome headline. This detects
changes since recording; it is not authenticity against someone who rewrites both a file and
the hash recorded for it. It is the basis for hosted replay (T-12).
"""

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from atlas.contracts import Manifest
from atlas.intake import manifest_reason
from atlas.ui import artifacts as A
from atlas.ui.catalogue import ROOT, ClaimView, claim_view

RECORDED_ENV = "ATLAS_UI_RECORDED_DIR"
AGENT = "agent"
AUDIT = "audit"
CHANGED = "evidence changed since recording"
NOT_REEXECUTED = "not re-executed here"


def recorded_root() -> Path:
    return Path(os.environ.get(RECORDED_ENV) or ROOT / "runs").resolve()


@dataclass(frozen=True)
class RecordedRun:
    path: Path
    label: str  # the directory relative to the root, with forward slashes
    kind: str  # AGENT or AUDIT

    @property
    def project(self) -> str:
        """The project name in the directory name (`agent-<project>-<id>`, `<project>-<id>`)."""
        name = (
            self.path.name.removeprefix("agent-")
            if self.kind == AGENT
            else self.path.name
        )
        return name.rsplit("-", 1)[0]


def _kind(d: Path) -> str | None:
    if d.name.startswith("agent-"):
        return AGENT if (d / "agent_report.json").is_file() else None
    if (d / "outcome.json").is_file() and (d / "report.json").is_file():
        return AUDIT
    return None


def list_runs(root: Path) -> list[RecordedRun]:
    """Finished runs under `root`: `live*/agent-*` and `ui/*` (UI agent and audit runs).
    A directory without its final report (still running, or never finished) is not listed."""
    root = Path(root)
    found = []
    candidates = sorted(root.glob("live*/agent-*")) if root.is_dir() else []
    ui = root / "ui"
    if ui.is_dir():
        candidates += sorted(p for p in ui.iterdir() if not p.name.startswith("."))
    for d in candidates:
        kind = _kind(d) if d.is_dir() else None
        if kind is not None:
            found.append(RecordedRun(d, d.relative_to(root).as_posix(), kind))
    return found


@dataclass(frozen=True)
class Check:
    item: str  # a path relative to the run directory, or a report key path
    recorded: str | None
    recomputed: str | None
    status: str  # "matches", "changed", "missing" or "outside"

    @property
    def ok(self) -> bool:
        return self.status == "matches"


def _file_check(run_dir: Path, rel: str, recorded) -> Check:
    path = (run_dir / rel).resolve()
    try:
        path.relative_to(run_dir.resolve())
    except ValueError:
        return Check(rel, recorded, None, "outside")
    if not path.is_file():
        return Check(rel, recorded, None, "missing")
    digest = A.sha256_file(path)
    return Check(rel, recorded, digest, "matches" if digest == recorded else "changed")


def _evaluated(run_dir: Path, sub: str, evidence: dict | None, add) -> dict | None:
    """The hashes recorded for one evaluated run (`original`, `candidates/cN` or the audit
    run itself): the report's `evidence_sha256`, then the run's own index.json."""
    base = f"{sub}/" if sub else ""
    for name, digest in (evidence or {}).items():
        add(base + name, digest)
    index = (
        A.read_json(run_dir / base / "index.json")
        if (run_dir / base / "index.json").is_file()
        else None
    )
    for group in ("artifacts", "outputs"):
        for name, digest in ((index or {}).get(group) or {}).items():
            add(base + name, digest)
    if (
        "outcome.json" not in (evidence or {})
        and not (run_dir / base / "outcome.json").is_file()
    ):
        return None  # nothing was evaluated here, so there is no outcome to compare
    return A.read_json(run_dir / base / "outcome.json") or {}


def verify(run_dir: Path, report: dict | None) -> list[Check]:
    """Every recorded hash, recomputed from disk, plus each reported outcome against its
    verified outcome.json. The same file listed twice with the same hash is checked once."""
    run_dir = Path(run_dir)
    checks: list[Check] = []
    seen: set[tuple[str, str]] = set()

    def add(rel: str, recorded) -> None:
        if not isinstance(rel, str) or (rel, str(recorded)) in seen:
            return
        seen.add((rel, str(recorded)))
        checks.append(_file_check(run_dir, rel, recorded))

    def same(item: str, recorded, recomputed) -> None:
        status = "matches" if recorded == recomputed else "changed"
        checks.append(Check(item, recorded, recomputed, status))

    if report is None:  # a deterministic audit run
        outcome = _evaluated(run_dir, "", None, add)
        audit_report = A.read_json(run_dir / "report.json") or {}
        same(
            "report.json:outcome",
            audit_report.get("outcome"),
            (outcome or {}).get("outcome"),
        )
        return checks
    add("agent_log.jsonl", (report.get("agent_log") or {}).get("sha256"))
    for r in report.get("replies") or []:
        add(r.get("path"), r.get("sha256"))
    for p in report.get("proposals") or []:
        if p.get("diff_path"):
            add(p["diff_path"], p.get("diff_sha256"))
        if p.get("new_source_path"):
            add(p["new_source_path"], p.get("new_source_sha256"))
    comp = report.get("comparison") or {}
    outcomes = report.get("scientific_outcomes") or {}
    original = comp.get("original") or {}
    outcome = _evaluated(run_dir, "original", original.get("evidence_sha256"), add)
    if outcome is not None:
        same(
            "agent_report.json:scientific_outcomes.original",
            outcomes.get("original"),
            outcome.get("outcome"),
        )
    reported = outcomes.get("candidates") or []
    for i, c in enumerate(comp.get("candidates") or [], start=1):
        sub = f"candidates/{Path(c.get('run_dir') or f'c{i}').name}"
        outcome = _evaluated(run_dir, sub, c.get("evidence_sha256"), add)
        if outcome is not None:
            same(
                f"agent_report.json:comparison.candidates[{i}].scientific_outcome",
                c.get("scientific_outcome"),
                outcome.get("outcome"),
            )
            same(
                f"agent_report.json:scientific_outcomes.candidates[{i}]",
                reported[i - 1] if i <= len(reported) else None,
                outcome.get("outcome"),
            )
    return checks


def intact(checks: list[Check]) -> bool:
    return all(c.ok for c in checks)


def claim_source(run: RecordedRun) -> Path | None:
    """The manifest the run evaluated: the hashed snapshot copy, else the run's snapshot."""
    for rel in (
        ("original/manifest.snapshot.json", "snapshot/atlas_manifest.json")
        if run.kind == AGENT
        else ("manifest.snapshot.json",)
    ):
        if (run.path / rel).is_file():
            return run.path / rel
    return None


def read_claim(path: Path) -> ClaimView:
    manifest = Manifest.model_validate_json(Path(path).read_text(encoding="utf-8"))
    reason = manifest_reason(manifest)
    return claim_view(manifest, reason is None, reason)


def finished(run: RecordedRun, report: dict | None) -> tuple[str | None, str]:
    """When the run finished, and where that time comes from."""
    if report is not None:
        return A.run_finished_utc(report), "the last state in agent_report.json"
    path = run.path / "outcome.json"
    stamp = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    return stamp, "the modification time of outcome.json"


def logged_decisions(events: list[dict]) -> list[dict]:
    """Approval decisions from the run's own log (a live page reads them from its channel)."""
    return [
        {"kind": e.get("kind"), "decision": e.get("decision")}
        for e in events
        if e.get("event") == "approval"
    ]
