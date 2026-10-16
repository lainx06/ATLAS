"""Deterministic audit: intake -> trusted execution -> trusted evaluation -> evidence (SPEC §6, §7).

Scope (T-01, T-02): audit mode only, trusted fixtures only, no model calls, no candidate execution.
T-06 slice 1: `evaluate` also accepts a Docker candidate view (`atlas.docker_evidence`), whose
execution evidence is checked separately; the trusted-fixture path is unchanged.
"""

import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from atlas import docker_evidence
from atlas.adapter import ADAPTER_VERSION
from atlas.checks.fit_provenance import fit_assertions
from atlas.checks.independent_metrics import metric_assertions
from atlas.checks.metric_ids import prediction_id_assertions
from atlas.checks.split_integrity import split_assertions
from atlas.checks.temporal import temporal_assertions
from atlas.contracts import (
    SPLITS,
    AssertionResult,
    DescriptiveResult,
    EvidenceRef,
    ExecutionRecord,
    Manifest,
    Outcome,
    Reason,
    RunIndex,
    RunOutcome,
    RuntimeRecord,
    Status,
    validate_provenance_event,
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
    CAPABILITY,
    RUNNER_NAME,
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
SNAPSHOT_PROBLEM = "manifest snapshot missing or invalid"


def _clear_outputs(run_dir: Path, index: dict | None) -> None:
    """Remove outputs of any earlier evaluation, and their index entries, before evaluating."""
    for name in OUTPUT_FILES:
        (run_dir / name).unlink(missing_ok=True)
    shutil.rmtree(run_dir / "checks", ignore_errors=True)
    if index is not None and "outputs" in index:
        index.pop("outputs")
        write_json(run_dir / "index.json", index)


def _finalize(
    run_dir: Path, index: dict | None, outcome: RunOutcome, report: dict
) -> None:
    """The one finalization path: write outputs, then index exactly what was written."""
    written = ["outcome.json", "report.json"]
    by_check: dict[str, list] = {}
    for a in outcome.assertions:
        check = CHECK_OF_PREFIX.get(a.assertion_id.split(".", 1)[0], "other")
        by_check.setdefault(check, []).append(a.model_dump(mode="json"))
    descriptive: dict[str, list] = {}
    for d in outcome.descriptive:
        check = CHECK_OF_PREFIX.get(d.result_id.split(".", 1)[0], "other")
        descriptive.setdefault(check, []).append(d.model_dump(mode="json"))
    for check in [*by_check, *(c for c in descriptive if c not in by_check)]:
        write_json(
            run_dir / "checks" / f"{check}.json",
            {
                "check_id": check,
                "assertions": by_check.get(check, []),
                "descriptive": descriptive.get(check, []),
            },
        )
        written.append(f"checks/{check}.json")
    write_json(run_dir / "outcome.json", outcome.model_dump(mode="json"))
    write_json(run_dir / "report.json", report)
    if index is not None:
        index = {k: v for k, v in index.items() if k != "outputs"}
        index["outputs"] = {name: sha256_file(run_dir / name) for name in written}
        write_json(run_dir / "index.json", index)


def _load_index(run_dir: Path) -> dict | None:
    try:
        index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
    # Unreadable or undecodable (including excessive nesting): the index is unavailable.
    except (OSError, ValueError, RecursionError):
        return None
    try:
        RunIndex.model_validate(index)
    # Decodes, but not the structure audit reads (e.g. a list): the index is unavailable too.
    except ValidationError:
        return None
    return index


def _trusted_manifest(
    project: Path, run_dir: Path, index: dict | None
) -> tuple[Manifest | None, str | None]:
    """(manifest, snapshot problem). Built from verified evidence only; never invented.

    A hash-matching project manifest may reconstruct the required set, but the missing or
    invalid snapshot remains a reported problem (it is not silently cleared).
    """
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
            return None, f"{SNAPSHOT_PROBLEM} and project manifest unparseable"
        return manifest, (
            f"{SNAPSHOT_PROBLEM}; required set reconstructed from the project manifest "
            "matching the recorded snapshot hash"
        )
    return None, f"{SNAPSHOT_PROBLEM} and no hash-matching trusted manifest"


def _execution_trust(
    project: Path, run_dir: Path, index: dict, manifest: Manifest, image_verifier
) -> docker_evidence.Trust:
    """A candidate view (marked by view.json in the index) is checked only as Docker evidence;
    anything else only as trusted-fixture evidence, whose index is used unchanged."""
    if docker_evidence.VIEW_NAME in index["artifacts"]:
        return docker_evidence.docker_trust(
            project, run_dir, index, manifest, image_verifier
        )
    record, problem = _fixture_execution_trust(run_dir, index)
    if problem is None:
        mode = docker_evidence.COMPLETED
    elif problem == "fixture execution did not complete":
        mode = docker_evidence.NOT_COMPLETED
    else:
        mode = docker_evidence.UNCONFIRMED
    return docker_evidence.Trust(record, problem, mode, index, [])


def _fixture_execution_trust(
    run_dir: Path, index: dict
) -> tuple[dict | None, str | None]:
    """(execution record, problem). Both records must verify, validate, and be semantically valid."""
    exec_path, _, exec_ok = verified(run_dir, index, "execution.json")
    if not exec_ok:
        return None, "execution record missing or hash-mismatched"
    try:
        record = ExecutionRecord.model_validate_json(
            exec_path.read_text(encoding="utf-8")
        )
    except ValueError:
        return None, "execution record fails schema validation"
    if record.runner != RUNNER_NAME or record.capability != CAPABILITY:
        return (
            record.model_dump(),
            "execution record claims an unexpected runner or capability",
        )
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
        or not runtime.safe_path
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
) -> None:
    """Without confirmed evidence no PASS is established; valid FAILs stand.

    `completed=True` means verified non-completion (NOT_ASSESSED not_executed); otherwise the
    evidence itself is missing or invalid (ERROR evidence_invalid).
    """
    for aid, result in computed.items():
        if result.status is Status.PASS:
            computed[aid] = result.model_copy(
                update={
                    "status": Status.NOT_ASSESSED if completed else Status.ERROR,
                    "reason": Reason.NOT_EXECUTED
                    if completed
                    else Reason.EVIDENCE_INVALID,
                    "evidence_valid": completed,
                    "limitations": [*result.limitations, problem],
                }
            )


def _invalidate(computed: dict[str, AssertionResult], problem: str) -> None:
    """Evidence that cannot be attributed to the approved execution supports nothing: every
    PASS and FAIL becomes ERROR (evidence_invalid)."""
    for aid, result in computed.items():
        if result.status in (Status.PASS, Status.FAIL):
            computed[aid] = result.model_copy(
                update={
                    "status": Status.ERROR,
                    "reason": Reason.EVIDENCE_INVALID,
                    "evidence_valid": False,
                    "limitations": [*result.limitations, problem],
                }
            )


def evaluate(project: Path, run_dir: Path, *, image_verifier=None) -> RunOutcome:
    """Trusted evaluation of an executed run; always materializes the full required set.

    `image_verifier` applies only to Docker candidate views (default: ask Docker).
    """
    project = Path(project).resolve()
    run_dir = Path(run_dir)
    index = _load_index(run_dir)
    _clear_outputs(run_dir, index)
    manifest, snapshot_problem = _trusted_manifest(project, run_dir, index)
    if manifest is None:
        outcome = RunOutcome(
            outcome=Outcome.INCONCLUSIVE,
            policy_version=POLICY_VERSION,
            reason=f"required assertion set could not be reconstructed: {snapshot_problem}",
            incomplete_coverage=["required_assertion_set"],
        )
        _finalize(run_dir, index, outcome, _report(project, None, None, outcome))
        return outcome

    required = required_assertions(manifest)
    trust = _execution_trust(project, run_dir, index, manifest, image_verifier)
    execution, problem, mode = trust.record, trust.problem, trust.mode
    computed, descriptive, evidence_problem = _compute(
        project, run_dir, trust.evidence_index, manifest
    )
    evidence_problem = (
        "; ".join(p for p in (*trust.artifact_problems, evidence_problem) if p) or None
    )
    if snapshot_problem is not None:
        _degrade_unconfirmed(computed, snapshot_problem, completed=False)
    if problem is not None and mode == docker_evidence.UNTRUSTED:
        _invalidate(computed, problem)
    elif problem is not None:
        _degrade_unconfirmed(
            computed, problem, completed=mode == docker_evidence.NOT_COMPLETED
        )
    unconfirmed = "; ".join(p for p in (snapshot_problem, problem) if p)
    if unconfirmed:
        descriptive = [
            d.model_copy(
                update={
                    "available": False,
                    "reason": f"evidence not confirmed: {unconfirmed}",
                    "observed": {},
                }
            )
            for d in descriptive
        ]
    results = materialize(required, computed)
    outcome = RunOutcome(
        outcome=derive_outcome(results),
        policy_version=POLICY_VERSION,
        reason="; ".join(p for p in (unconfirmed, evidence_problem) if p) or None,
        assertions=results,
        incomplete_coverage=incomplete_coverage(results),
        descriptive=descriptive,
    )
    docker_view = docker_evidence.VIEW_NAME in index["artifacts"]
    _finalize(
        run_dir,
        index,
        outcome,
        _report(project, manifest, execution, outcome, docker_view=docker_view),
    )
    return outcome


def _read_events(path: Path) -> tuple[list[dict], str | None]:
    """(events, decoding problem). The event stream is decoded whole: one undecodable line (an
    over-limit integer, malformed JSON, non-UTF-8 bytes, excessive nesting) makes all of
    provenance.jsonl invalid evidence. A decoded prefix is never returned.
    """
    try:
        events = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]
    except (ValueError, RecursionError) as exc:
        return [], _decode_problem("provenance.jsonl", exc)
    # Each decoded event must have the structure its consumers read; one invalid event makes
    # the whole artifact invalid (no prefix is kept, nothing is skipped).
    for number, event in enumerate(events, 1):
        try:
            validate_provenance_event(event)
        except ValueError as exc:  # pydantic's ValidationError is a ValueError
            detail = " ".join(str(exc).split())[:200]
            return (
                [],
                f"provenance.jsonl event {number} has an invalid structure ({detail})",
            )
    return events, None


def _load_splits(path: Path) -> tuple[list, str | None]:
    """(declared splits, decoding problem). Hash-verified bytes that cannot be decoded are invalid
    evidence, never an exception: e.g. an integer beyond Python's int-from-string digit limit
    (ValueError), malformed JSON or non-UTF-8 bytes (ValueError subclasses), or nesting deep
    enough to exhaust recursion. Nothing is parsed partially or dropped.
    """
    try:
        splits = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, RecursionError) as exc:
        return [], _decode_problem("splits.json", exc)
    # The whole artifact must have the structure every check reads before any check runs.
    try:
        SPLITS.validate_python(splits)
    except ValidationError as exc:
        return [], _structure_problem("splits.json", exc)
    return splits, None


def _unknown_split_rows(splits: list[dict], table: pd.DataFrame) -> str | None:
    """The producer only declares rows of the table (SPEC §4.1); others are invalid evidence."""
    rows = set(table.index)
    for s in splits:
        for name in ("train_ids", "eval_ids"):
            unknown = [r for r in s[name] if r not in rows]
            if unknown:
                return (
                    f"splits.json fold {s['fold']!r} {name} names {len(unknown)} row(s) "
                    f"absent from the table (e.g. {unknown[0][:40]!r})"
                )
    return None


# What the consumers of a prediction artifact read: the row-ID check reads `row_id`, the metric
# check reads `row_id` and `y_pred` (each value judged by `canonical_label`). Row IDs are the
# strings the adapter writes (`adapter.write_predictions`).
PREDICTION_COLUMNS = ("row_id", "y_pred")


def _load_predictions(path: Path) -> tuple[pd.DataFrame | None, str | None]:
    """(frame, None) in the shape its consumers read, or (None, why it is unusable).

    Decoding failures of the file are evidence errors, not evaluator crashes. Arrow's errors
    subclass these built-in types (ArrowInvalid is a ValueError, ArrowIOError an OSError,
    ArrowTypeError a TypeError, ArrowNotImplementedError a NotImplementedError); the guard covers
    only the read itself, so evaluator programming errors elsewhere still raise.
    """
    try:
        frame = pd.read_parquet(path)
    except (OSError, ValueError, TypeError, NotImplementedError) as exc:
        return None, f"could not be decoded as Parquet ({type(exc).__name__})"
    columns = list(frame.columns)
    if len(columns) != len(set(columns)):
        return None, "has repeated column names"
    missing = [c for c in PREDICTION_COLUMNS if c not in columns]
    if missing:
        return None, f"lacks required column(s) {missing}"
    if not all(isinstance(r, str) for r in frame["row_id"]):
        return None, "has row_id values that are not strings"
    return frame, None


def _structure_problem(artifact: str, exc: ValidationError) -> str:
    """Name the failing entries and fields (as intake does); input values are not echoed."""
    parts = [
        f"{'.'.join(map(str, e['loc'])) or '<top level>'}: {e['msg']}"
        for e in exc.errors(include_input=False)[:3]
    ]
    return f"{artifact} has an invalid structure ({'; '.join(parts)})"


def _decode_problem(artifact: str, exc: Exception) -> str:
    return f"{artifact} could not be decoded ({type(exc).__name__}: {str(exc)[:160]})"


def _compute(
    project: Path, run_dir: Path, index: dict, manifest: Manifest
) -> tuple[dict[str, AssertionResult], list[DescriptiveResult], str | None]:
    """(computed assertions, descriptive results, evidence-decoding problems or None)."""
    table_info = index.get("table") or {}
    table_path = project / manifest.table.path
    table_ok = table_path.exists() and sha256_file(table_path) == table_info.get(
        "sha256"
    )
    table_ref = EvidenceRef(
        artifact=f"table:{manifest.table.path}", sha256=table_info.get("sha256")
    )
    table = read_table(project, manifest) if table_ok else None
    splits_path, splits_hash, splits_ok = verified(run_dir, index, "splits.json")
    splits_ref = EvidenceRef(artifact="splits.json", sha256=splits_hash)
    splits, splits_problem = [], None
    if splits_ok:
        splits, splits_problem = _load_splits(splits_path)
        if splits_problem is None and table is not None:
            splits_problem = _unknown_split_rows(splits, table)
        # Undecodable or structurally invalid evidence takes the existing invalid-evidence path:
        # every assertion that depends on the splits becomes ERROR(evidence_invalid). The whole
        # artifact is invalid; no entry is dropped or assessed on its own.
        if splits_problem is not None:
            splits = []
        splits_ok = splits_problem is None

    prov_path, prov_hash, prov_ok = verified(run_dir, index, "provenance.jsonl")
    events, prov_problem = [], None
    if prov_ok:
        events, prov_problem = _read_events(prov_path)
        # Undecodable provenance is wholly invalid: the fit assertions that depend on it become
        # ERROR(evidence_invalid); findings with separate valid evidence are unaffected.
        prov_ok = prov_problem is None

    # Expected prediction inventory: exactly predictions/<fold>.parquet per declared fold.
    # Never inferred from files that exist, and never remapped by candidate-produced events.
    expected = {s["fold"]: f"predictions/{s['fold']}.parquet" for s in splits}
    inventory_issues = [
        f"prediction event for fold {e['fold']} names {e.get('artifact')!r}, not {expected[e['fold']]!r}"
        for e in events
        if e["type"] == "predictions"
        and e["fold"] in expected
        and e.get("artifact") != expected[e["fold"]]
    ]
    pred_refs, by_fold, frames, verified_artifacts = [], {}, {}, {}
    prediction_problems: list[str] = []
    for fold, name in expected.items():
        path, recorded, ok = verified(run_dir, index, name)
        pred_refs.append(EvidenceRef(artifact=name, sha256=recorded))
        frame, problem = _load_predictions(path) if ok else (None, None)
        if frame is not None:
            verified_artifacts[name] = recorded
            frames[fold] = frame
            by_fold[fold] = [str(r) for r in frame["row_id"]]
        elif recorded is not None:
            # Present in the inventory but invalid: a hash mismatch, or (problem) bytes whose
            # hash matches but that its consumers cannot read. Only its dependants are affected.
            by_fold[fold] = None
            if problem is not None:
                prediction_problems.append(f"{name} {problem}")
    # Unexpected paths stay separate from verified fold data; they are never read as rows.
    unexpected = sorted(
        name
        for name in index["artifacts"]
        if name.startswith("predictions/") and name not in set(expected.values())
    )
    pred_refs += [
        EvidenceRef(artifact=n, sha256=index["artifacts"][n]) for n in unexpected
    ]

    computed: dict[str, AssertionResult] = {}
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
        prediction_id_assertions(
            splits,
            by_fold,
            [splits_ref, *pred_refs],
            splits_ok,
            unexpected_artifacts=unexpected,
            inventory_issues=inventory_issues,
        )
    )
    # T-02 (policy-v1.3). Route C of the window check depends on the computed group result.
    computed.update(
        temporal_assertions(
            manifest,
            table,
            splits,
            [splits_ref, table_ref],
            evidence_valid=splits_ok and table_ok,
            group_result=computed.get("split.no_group_overlap"),
        )
    )
    metrics, descriptive = metric_assertions(
        manifest,
        table,
        splits,
        frames,  # verified artifacts only; a missing or invalid one is absent
        [splits_ref, table_ref, *pred_refs],
        evidence_valid=splits_ok and table_ok,
    )
    computed.update(metrics)
    problems = "; ".join(
        p for p in (splits_problem, prov_problem, *prediction_problems) if p
    )
    return computed, descriptive, problems or None


FIXTURE_LIMITATION = "Audit mode: trusted repo-authored fixtures only; no isolation (trusted_pipeline_only)."
DOCKER_LIMITATIONS = [
    (
        "Candidate executed only in the isolated Docker runner (isolated_available). Container "
        "restrictions reduce execution risk; they do not prove provenance integrity or scientific "
        "correctness."
    ),
    (
        "Provenance, splits, predictions and runtime.json are written inside the candidate process "
        "(candidate-produced evidence); runtime.json only corroborates."
    ),
    (
        "Hash and configuration checks establish consistency with the approved candidate and the "
        "trusted runner configuration, not authenticity against an attacker who controls the host."
    ),
]


def _report(
    project, manifest, execution, outcome: RunOutcome, docker_view: bool = False
) -> dict:
    return {
        "project": project.name,
        "claim": manifest.claim.model_dump(mode="json") if manifest else None,
        "outcome": outcome.outcome,
        "reason": outcome.reason,
        "incomplete_coverage": outcome.incomplete_coverage,
        "policy_version": POLICY_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "execution": execution,
        "versions": versions(),
        "limitations": [
            *(DOCKER_LIMITATIONS if docker_view else [FIXTURE_LIMITATION]),
            "Fit provenance covers only the bounded supported path; the in-process recorder is not tamper-proof.",
            "Provenance begins at the supplied feature table.",
            "Window-overlap and temporal-separation checks verify declared rules; they are not proof of statistical independence.",
            "Training cutoffs and fold membership are declared by the evaluated code and are not verified independently.",
        ],
    }
