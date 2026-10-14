"""Deterministic audit: intake -> trusted execution -> trusted evaluation -> evidence (SPEC §6, §7).

T-01 scope: audit mode only, trusted fixtures only, no model calls, no candidate execution.
"""

import hashlib
import json
import shutil
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
    ExecutionRecord,
    Manifest,
    Outcome,
    Reason,
    RunOutcome,
    RuntimeRecord,
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
from atlas.runner.trusted import (
    UntrustedFixtureError,
    run_trusted_fixture,
    trusted_atlas_parent,
)

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


OUTPUT_FILES = ("outcome.json", "report.json")


def _clear_outputs(run_dir: Path) -> None:
    """Remove outputs of any earlier evaluation so nothing stale can look current."""
    for name in OUTPUT_FILES:
        (run_dir / name).unlink(missing_ok=True)
    shutil.rmtree(run_dir / "checks", ignore_errors=True)


def _load_index(run_dir: Path) -> dict | None:
    try:
        index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return index if isinstance(index.get("artifacts"), dict) else None


def _trusted_manifest(
    project: Path, run_dir: Path, index: dict | None
) -> tuple[Manifest | None, str | None]:
    """The manifest the run executed under, from verified evidence only; never invented."""
    if index is None:
        return None, "run index missing or unparseable"
    snap_path, recorded, snap_ok = verified(run_dir, index, "manifest.snapshot.json")
    if snap_ok:
        try:
            return Manifest.model_validate_json(
                snap_path.read_text(encoding="utf-8")
            ), None
        except ValueError:
            pass
    project_manifest = project / MANIFEST_NAME
    if (
        recorded
        and project_manifest.exists()
        and sha256_file(project_manifest) == recorded
    ):
        try:
            manifest = Manifest.model_validate_json(
                project_manifest.read_text(encoding="utf-8")
            )
        except ValueError:
            return None, "manifest snapshot invalid and project manifest unparseable"
        return manifest, (
            "manifest snapshot missing or invalid; required set reconstructed from the "
            "project manifest matching the recorded snapshot hash"
        )
    return (
        None,
        "manifest snapshot missing or invalid and no hash-matching trusted manifest",
    )


def _execution_trust(run_dir: Path, index: dict) -> tuple[dict | None, str | None]:
    """(execution record, problem). Both execution.json and runtime.json must verify and validate."""
    exec_path, _, exec_ok = verified(run_dir, index, "execution.json")
    if not exec_ok:
        return None, "execution record missing or hash-mismatched"
    try:
        record = ExecutionRecord.model_validate_json(
            exec_path.read_text(encoding="utf-8")
        )
    except ValueError:
        return None, "execution record fails schema validation"
    if record.timed_out or record.returncode != 0:
        return record.model_dump(), "fixture execution did not complete"
    rt_path, _, rt_ok = verified(run_dir, index, "runtime.json")
    if not rt_ok:
        return record.model_dump(), "runtime record missing or hash-mismatched"
    try:
        runtime = RuntimeRecord.model_validate_json(rt_path.read_text(encoding="utf-8"))
    except ValueError:
        return record.model_dump(), "runtime record fails schema validation"
    trusted_pkg = Path(trusted_atlas_parent()) / "atlas"
    if (
        runtime.isolated != 1
        or runtime.project_dir_on_sys_path
        or runtime.cwd_on_sys_path
        or Path(runtime.atlas_origin).parent != trusted_pkg
    ):
        return (
            record.model_dump(),
            "fixture imports were not resolved under the controlled launcher",
        )
    return record.model_dump(), None


def _degrade_unconfirmed(
    computed: dict[str, AssertionResult], problem: str, completed: bool
):
    """Without a trusted, completed execution no PASS is established; valid FAILs stand."""
    for aid, result in computed.items():
        if result.status is Status.PASS:
            computed[aid] = result.model_copy(
                update={
                    "status": Status.ERROR if not completed else Status.NOT_ASSESSED,
                    "reason": Reason.EVIDENCE_INVALID
                    if not completed
                    else Reason.NOT_EXECUTED,
                    "evidence_valid": completed,
                    "limitations": [*result.limitations, problem],
                }
            )


def evaluate(project: Path, run_dir: Path) -> RunOutcome:
    """Trusted evaluation of an executed run; always materializes the full required set."""
    project = Path(project).resolve()
    run_dir = Path(run_dir)
    _clear_outputs(run_dir)
    index = _load_index(run_dir)
    manifest, note = _trusted_manifest(project, run_dir, index)
    if manifest is None:
        outcome = RunOutcome(
            outcome=Outcome.INCONCLUSIVE,
            policy_version=POLICY_VERSION,
            reason=f"required assertion set could not be reconstructed: {note}",
            incomplete_coverage=["required_assertion_set"],
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
        return outcome

    required = required_assertions(manifest)
    execution, problem = _execution_trust(run_dir, index)
    computed = _compute(project, run_dir, index, manifest)
    if problem is not None:
        # "did not complete" is verified evidence of non-completion: NOT_ASSESSED(not_executed).
        _degrade_unconfirmed(
            computed, problem, completed=problem == "fixture execution did not complete"
        )
    results = materialize(required, computed)
    outcome = RunOutcome(
        outcome=derive_outcome(results),
        policy_version=POLICY_VERSION,
        reason="; ".join(p for p in (note, problem) if p) or None,
        assertions=results,
        incomplete_coverage=incomplete_coverage(results),
    )
    _write_outputs(project, run_dir, index, manifest, execution, outcome)
    return outcome


def _read_events(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _compute(
    project: Path, run_dir: Path, index: dict, manifest: Manifest
) -> dict[str, AssertionResult]:
    table_info = index.get("table") or {}
    table_path = project / manifest.table.path
    table_ok = table_path.exists() and sha256_file(table_path) == table_info.get(
        "sha256"
    )
    table_ref = EvidenceRef(
        artifact=f"table:{manifest.table.path}", sha256=table_info.get("sha256")
    )
    splits_path, splits_hash, splits_ok = verified(run_dir, index, "splits.json")
    splits_ref = EvidenceRef(artifact="splits.json", sha256=splits_hash)
    splits = json.loads(splits_path.read_text(encoding="utf-8")) if splits_ok else []

    prov_path, prov_hash, prov_ok = verified(run_dir, index, "provenance.jsonl")
    events = _read_events(prov_path) if prov_ok else []

    # Expected prediction inventory: one artifact per declared fold (never inferred from files).
    expected = {s["fold"]: f"predictions/{s['fold']}.parquet" for s in splits}
    for e in events:
        if e["type"] == "predictions" and e["fold"] in expected and e.get("artifact"):
            expected[e["fold"]] = e["artifact"]
    pred_refs, by_fold, verified_artifacts = [], {}, {}
    for fold, name in expected.items():
        path, recorded, ok = verified(run_dir, index, name)
        pred_refs.append(EvidenceRef(artifact=name, sha256=recorded))
        if ok:
            verified_artifacts[name] = recorded
            by_fold[fold] = [str(r) for r in pd.read_parquet(path)["row_id"]]
        elif recorded is not None:
            by_fold[fold] = None  # present in the inventory but invalid
    for name in index["artifacts"]:
        if name.startswith("predictions/") and name not in expected.values():
            by_fold[Path(name).stem] = []  # artifact for an undeclared fold
            pred_refs.append(
                EvidenceRef(artifact=name, sha256=index["artifacts"][name])
            )

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
            artifacts=verified_artifacts,
        )
    )
    computed.update(
        prediction_id_assertions(splits, by_fold, [splits_ref, *pred_refs], splits_ok)
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
