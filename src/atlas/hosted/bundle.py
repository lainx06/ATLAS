"""The bundled recorded runs (T-12 step 3) and the hosted original runner (step 1).

`demo/recorded/` holds byte-exact copies of finished runs (`scripts/build_recorded_bundle.py`;
the UCI HAR feature table is left out, decision 1). `BUNDLE.json` lists them. The hosted page
opens them only through the recorded-run viewer, which recomputes every recorded hash first.

`recorded_original(run)` is the original runner of a hosted session: the original is never
executed here. Its findings come from a bundled recorded run, used only if

1. the recorded run is intact (`ui.recorded.verify`: every recorded hash and outcome);
2. the recorded original evaluated exactly this project's code: the code hash and snapshot
   hash in its `candidate.json` equal those of the snapshot this session just built;
3. the recorded `original/` copied into this session's run directory still has every
   recorded hash.

Otherwise the run ends ERROR before any model request ("evidence changed since recording" or
a code mismatch). Its findings are labelled "computed by ATLAS's trusted evaluation functions
(recorded <date>)". This detects changes since recording; it does not authenticate a run whose
files and recorded hashes were both rewritten.
"""

import json
import shutil
from pathlib import Path

from atlas.agent import controller as ctl
from atlas.candidates import MAX_ENTRY_BYTES, _permitted_file, candidate_hash
from atlas.contracts import RunOutcome
from atlas.ui import artifacts as A
from atlas.ui import recorded as RR
from atlas.ui.catalogue import ROOT

BUNDLE_ROOT = ROOT / "demo" / "recorded"
MANIFEST = "BUNDLE.json"
# The project offered for the one live session, and the recorded run its findings come from
# (live run 6: the original VIOLATION_FOUND in Docker).
LIVE_PROJECT = "s01_faulty"
LIVE_ORIGINAL_RUN = "live6/agent-s01_faulty-877f8245a8a2"


def load_manifest(root: Path = BUNDLE_ROOT) -> dict:
    path = Path(root) / MANIFEST
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"runs": []}
    return data if isinstance(data, dict) else {"runs": []}


def list_bundle(root: Path = BUNDLE_ROOT) -> list[RR.RecordedRun]:
    """The bundled runs named in BUNDLE.json, in its order, that are finished agent runs
    inside the bundle (anything else is not listed)."""
    root = Path(root).resolve()
    runs = []
    for entry in load_manifest(root).get("runs") or []:
        rel = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(rel, str):
            continue
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.is_dir() and (path / "agent_report.json").is_file():
            runs.append(RR.RecordedRun(path, rel, RR.AGENT))
    return runs


def recorded_date(report: dict | None) -> str | None:
    """The recorded run's finish date (UTC, YYYY-MM-DD) from its own report."""
    finished = A.run_finished_utc(report)
    return finished[:10] if isinstance(finished, str) and len(finished) >= 10 else None


def _refuse(reason: str):
    return ctl.RunRefused(ctl.ERROR, reason)


def recorded_original(run_path: Path, label: str):
    """The hosted original runner for `run_agent(original=...)`, from the bundled run at
    `run_path` (shown as `label`)."""
    run_path = Path(run_path)

    def original(run) -> ctl.OriginalRun:
        run.enter(
            "CHECK",
            f"recorded original {label}: re-verified by hash; not executed here",
        )
        report = A.read_json(run_path / "agent_report.json")
        if report is None:
            raise _refuse("recorded_original_unavailable: no agent_report.json")
        checks = RR.verify(run_path, report)
        changed = [c for c in checks if not c.ok]
        if not checks or changed:
            run.log({"event": "recorded_original", "run": label, "result": "changed",
                     "items": len(checks), "changed": [c.item for c in changed][:20]})  # fmt: skip
            raise _refuse(
                f"recorded_original_changed: {RR.CHANGED} ({len(changed)} of "
                f"{len(checks)} items); not used"
            )
        recorded = A.read_json(run_path / "original" / "candidate.json") or {}
        entry = _permitted_file(
            run.snapshot.root, run.snapshot.entry_point, MAX_ENTRY_BYTES
        )
        expected = candidate_hash(run.snapshot.base_hash, entry)
        if (
            recorded.get("base_snapshot_hash") != run.snapshot.base_hash
            or recorded.get("candidate_hash") != expected
        ):
            run.log({"event": "recorded_original", "run": label, "result": "mismatch"})
            raise _refuse(
                "recorded_original_mismatch: the recorded evaluation is of other code "
                "than this project's snapshot; not used"
            )
        dest = run.run_dir / "original"
        shutil.copytree(run_path / "original", dest)
        copied = [
            c
            for c in checks
            if c.item.startswith("original/")
            and A.sha256_file(run.run_dir / c.item) != c.recorded
        ]
        if copied:
            raise _refuse(
                f"recorded_original_changed: {RR.CHANGED} after copying "
                f"({len(copied)} items); not used"
            )
        outcome = RunOutcome.model_validate_json(
            (dest / "outcome.json").read_text(encoding="utf-8")
        )
        date = recorded_date(report)
        info = {
            "run": label,
            "recorded_utc": A.run_finished_utc(report),
            "label": ctl.recorded_label(date or "date unknown"),
            "verified_items": len(checks),
            "recorded_mode": report.get("mode"),
        }
        run.log({"event": "recorded_original", "run": label, "result": "intact",
                 "items": len(checks), "outcome": outcome.outcome})  # fmt: skip
        return ctl.OriginalRun(
            run_dir=dest,
            outcome=outcome,
            runner=ctl.RECORDED_RUNNER,
            executed=True,  # in the recorded run (Docker); never here
            execution=A.read_json(dest / "execution.json") or {},
            recorded=info,
        )

    return original


def live_original(root: Path = BUNDLE_ROOT):
    """The original runner for the hosted live session's project."""
    return recorded_original(Path(root) / LIVE_ORIGINAL_RUN, LIVE_ORIGINAL_RUN)
