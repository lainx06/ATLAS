"""Deterministic audit: intake -> trusted execution -> trusted evaluation -> evidence (SPEC §6, §7).

T-01 scope: audit mode only, trusted fixtures only, no model calls, no candidate execution.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from atlas.adapter import ADAPTER_VERSION
from atlas.checks.fit_provenance import fit_assertions
from atlas.checks.metric_ids import prediction_id_assertions
from atlas.checks.split_integrity import split_assertions
from atlas.contracts import (
    AssertionResult,
    EvidenceRef,
    Manifest,
    Outcome,
    Reason,
    RunOutcome,
    Status,
)
from atlas.intake import MANIFEST_NAME, load_project, read_table
from atlas.policy import (
    POLICY_VERSION,
    derive_outcome,
    incomplete_coverage,
    materialize,
    required_assertions,
)
from atlas.reports import sha256_file, verified, versions, write_json
from atlas.runner.trusted import UntrustedFixtureError, run_trusted_fixture

CHECK_OF_PREFIX = {
    "split": "split_integrity",
    "fit": "fit_provenance",
    "metric": "independent_metrics",
    "temporal": "temporal_availability",
}


@dataclass
class AuditResult:
    run_dir: Path
    outcome: RunOutcome


def _new_run_dir(project: Path, runs_root: Path) -> Path:
    h = hashlib.sha256()
    h.update(
        (project / MANIFEST_NAME).read_bytes()
        if (project / MANIFEST_NAME).exists()
        else b""
    )
    h.update(POLICY_VERSION.encode())
    h.update(str(time.time_ns()).encode())
    # Absolute: the fixture child runs with cwd=project, so a relative path would land there.
    run_dir = Path(runs_root).resolve() / f"{project.name}-{h.hexdigest()[:12]}"
    run_dir.mkdir(parents=True)
    return run_dir


def audit(project: Path, runs_root: Path) -> AuditResult:
    project = Path(project).resolve()
    intake = load_project(project)
    if not intake.supported:
        run_dir = _new_run_dir(project, Path(runs_root))
        outcome = RunOutcome(
            outcome=Outcome.NOT_SUPPORTED,
            policy_version=POLICY_VERSION,
            reason=intake.reason,
        )
        write_json(run_dir / "outcome.json", outcome.model_dump(mode="json"))
        write_json(
            run_dir / "report.json",
            {
                "project": project.name,
                "outcome": outcome.model_dump(mode="json"),
                "versions": versions(),
            },
        )
        return AuditResult(run_dir, outcome)
    run_dir = execute(project, runs_root)
    return AuditResult(run_dir, evaluate(project, run_dir))


def execute(project: Path, runs_root: Path) -> Path:
    """Run an allowlisted trusted fixture and hash its evidence. Refuses anything else."""
    project = Path(project).resolve()
    intake = load_project(project)
    if not intake.supported:
        raise ValueError(f"not supported: {intake.reason}")
    manifest = intake.manifest
    from atlas.runner.trusted import (
        is_trusted,  # checked before any run directory exists
    )

    if not is_trusted(project, manifest.entry_point):
        raise UntrustedFixtureError(
            f"{project} is not an allowlisted trusted fixture; refusing to execute"
        )
    run_dir = _new_run_dir(project, Path(runs_root))
    (run_dir / "manifest.snapshot.json").write_bytes(
        (project / MANIFEST_NAME).read_bytes()
    )
    execution = run_trusted_fixture(project, manifest.entry_point, run_dir)
    write_json(run_dir / "execution.json", execution)
    artifacts = {}
    for path in sorted(run_dir.rglob("*")):
        if path.is_file():
            artifacts[path.relative_to(run_dir).as_posix()] = sha256_file(path)
    table_path = project / manifest.table.path
    write_json(
        run_dir / "index.json",
        {
            "artifacts": artifacts,
            "table": {"path": manifest.table.path, "sha256": sha256_file(table_path)},
        },
    )
    return run_dir


def evaluate(project: Path, run_dir: Path) -> RunOutcome:
    """Trusted evaluation of an executed run; always materializes the full required set."""
    project = Path(project).resolve()
    index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    snap_path, _, snap_ok = verified(run_dir, index, "manifest.snapshot.json")
    manifest = Manifest.model_validate_json(snap_path.read_text(encoding="utf-8"))
    required = required_assertions(manifest)
    execution = json.loads((run_dir / "execution.json").read_text(encoding="utf-8"))

    if not snap_ok:
        computed = {
            aid: AssertionResult(
                assertion_id=aid,
                status=Status.ERROR,
                reason=Reason.EVIDENCE_INVALID,
                evidence_valid=False,
            )
            for aid in required
        }
    elif execution["returncode"] != 0:
        computed = {}  # nothing was established; implemented assertions become NOT_ASSESSED(not_executed)
    else:
        computed = _compute(project, run_dir, index, manifest)

    results = materialize(required, computed)
    outcome = RunOutcome(
        outcome=derive_outcome(results),
        policy_version=POLICY_VERSION,
        assertions=results,
        incomplete_coverage=incomplete_coverage(results),
    )
    _write_outputs(project, run_dir, index, manifest, execution, outcome)
    return outcome


def _compute(
    project: Path, run_dir: Path, index: dict, manifest: Manifest
) -> dict[str, AssertionResult]:
    table_path = project / manifest.table.path
    table_ok = (
        table_path.exists() and sha256_file(table_path) == index["table"]["sha256"]
    )
    table_ref = EvidenceRef(
        artifact=f"table:{manifest.table.path}", sha256=index["table"]["sha256"]
    )
    splits_path, splits_hash, splits_ok = verified(run_dir, index, "splits.json")
    splits_ref = EvidenceRef(artifact="splits.json", sha256=splits_hash)
    splits = json.loads(splits_path.read_text(encoding="utf-8")) if splits_ok else []

    prov_path, prov_hash, prov_ok = verified(run_dir, index, "provenance.jsonl")
    events = (
        [
            json.loads(line)
            for line in prov_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        if prov_ok
        else []
    )

    pred_refs, predictions, preds_ok = [], {}, True
    for name in sorted(n for n in index["artifacts"] if n.startswith("predictions/")):
        path, recorded, ok = verified(run_dir, index, name)
        pred_refs.append(EvidenceRef(artifact=name, sha256=recorded))
        preds_ok = preds_ok and ok
        if ok:
            predictions[Path(name).stem] = [
                str(r) for r in pd.read_parquet(path)["row_id"]
            ]

    computed: dict[str, AssertionResult] = {}
    table = read_table(project, manifest) if table_ok else None
    computed.update(
        split_assertions(
            manifest,
            table,
            splits,
            [splits_ref, table_ref],
            evidence_valid=splits_ok and table_ok,
        )
    )
    computed.update(
        fit_assertions(
            events,
            splits,
            [EvidenceRef(artifact="provenance.jsonl", sha256=prov_hash), splits_ref],
            prov_ok and splits_ok,
        )
    )
    computed.update(
        prediction_id_assertions(
            splits, predictions, [splits_ref, *pred_refs], splits_ok and preds_ok
        )
    )
    return computed


def _write_outputs(
    project, run_dir, index, manifest, execution, outcome: RunOutcome
) -> None:
    by_check: dict[str, list] = {}
    for a in outcome.assertions:
        check = CHECK_OF_PREFIX.get(a.assertion_id.split(".", 1)[0], "other")
        by_check.setdefault(check, []).append(a.model_dump(mode="json"))
    for check, assertions in by_check.items():
        write_json(
            run_dir / "checks" / f"{check}.json",
            {"check_id": check, "assertions": assertions},
        )
    write_json(run_dir / "outcome.json", outcome.model_dump(mode="json"))
    write_json(
        run_dir / "report.json",
        {
            "project": project.name,
            "claim": manifest.claim.model_dump(mode="json"),
            "outcome": outcome.outcome,
            "incomplete_coverage": outcome.incomplete_coverage,
            "policy_version": POLICY_VERSION,
            "adapter_version": ADAPTER_VERSION,
            "execution": execution,
            "versions": versions(),
            "limitations": [
                "T-01 audit mode: trusted repo-authored fixtures only; no isolation (trusted_pipeline_only).",
                "Fit provenance covers only the bounded supported path; the in-process recorder is not tamper-proof.",
                "Provenance begins at the supplied feature table.",
            ],
        },
    )
    outputs = {}
    for name in (
        "outcome.json",
        "report.json",
        *(f"checks/{c}.json" for c in by_check),
    ):
        outputs[name] = sha256_file(run_dir / name)
    write_json(run_dir / "index.json", {**index, "outputs": outputs})
