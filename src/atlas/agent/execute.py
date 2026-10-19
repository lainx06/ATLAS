"""Approved candidate -> isolated execution -> trusted re-evaluation (SPEC §6, §9; T-06 slice 1).

No model is involved in this slice: the candidate comes from `validate_diff` and the approval
from the caller (the CLI approval step is later work). The only executor is
`runner.docker.run_candidate`; there is no host fallback, and when isolation is unavailable the
candidate is reported "not executed" with every required assertion NOT_ASSESSED.

The view the evaluator reads is built here, on the host, from three trusted inputs: the
approval and invocation context (written before execution), the runner's own record, and the
snapshot. Collected candidate files enter the view only through the explicit mapping of
`docker_evidence.plan_mapping`, after their bytes match the hashes the runner recorded at
collection, and every file is created exclusively, so nothing the candidate wrote can replace
a host-owned record. Time spent waiting for a human approval happens before this function is
called and is not part of `active_s`; the total since the proposal is recorded separately.

Preflight, before any required assertion set is derived: the supplied snapshot must be the one
the approval identifies (its recorded inventory hashes to its base hash, and that base hash is
the approval's). If not, nothing runs and the approved required set cannot be reconstructed:
the supplied, unapproved snapshot's manifest is never used, intact or not. Then the snapshot's
manifest is read (bounded) and must still have the hash recorded when the snapshot was
built. A missing, changed or invalid manifest is a
recorded refusal: Docker is never touched, an execution record and a final outcome and report
are written, and the required assertion set comes only from a trusted source (a manifest whose
canonical bytes have the snapshot's recorded hash); otherwise the outcome says that the set
cannot be reconstructed, and no assertion is invented.
"""

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from atlas.audit import evaluate
from atlas.candidates import (
    MAX_MANIFEST_BYTES,
    Approval,
    Candidate,
    Snapshot,
    SnapshotError,
    _permitted_file,
    candidate_hash,
    inventory_hash,
    sha256_bytes,
)
from atlas.contracts import Manifest, Outcome, RunOutcome
from atlas.docker_evidence import (
    EXEC_DIR,
    HOST_RECORDS,
    TRUSTED_LIMITS,
    VIEW_NAME,
    plan_mapping,
)
from atlas.hosted import refuse_if_hosted
from atlas.intake import MANIFEST_NAME
from atlas.policy import (
    POLICY_VERSION,
    incomplete_coverage,
    materialize,
    required_assertions,
)
from atlas.runner import docker as dr

NOT_RUN = ("refused", "not_executed")


@dataclass
class CandidateResult:
    candidate_dir: Path
    candidate_hash: str
    approval: dict
    diff_sha256: str
    execution: dict  # runner status and reason: did the candidate run, in isolation?
    evaluated: bool  # False when nothing ran, so the evaluator had no evidence to read
    outcome: RunOutcome  # the trusted evaluator's result for the full required set
    timing: dict
    # The candidate's own output as the in-container supervisor captured it (its stderr merged
    # into stdout; `supervisor.candidate_output_tail`). Untrusted, in memory only, never
    # reported: the controller derives `failure_summary` from it (T-06 slice 4f).
    candidate_output: str | None = None
    failure_summary: dict | None = None


def _new_json(path: Path, data) -> None:
    """Create a JSON file that must not exist yet (never replaces a file)."""
    text = json.dumps(data, indent=2, sort_keys=True, default=str) + "\n"
    with open(path, "xb") as f:
        f.write(text.encode("utf-8"))


def _new_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as f:
        f.write(data)


def execute_and_reevaluate(
    snapshot: Snapshot,
    candidate: Candidate,
    approval: Approval,
    candidate_dir: Path,
    *,
    proposed_at: datetime | None = None,
    image: str = dr.IMAGE_TAG,
    env=None,
    image_verifier=None,
    trusted_manifest: Manifest | None = None,
) -> CandidateResult:
    """Run one approved candidate in Docker and evaluate the full required set on the result.

    `trusted_manifest` (optional) is used only if the snapshot's own manifest is unusable, only
    when the snapshot is the approved one, and only when its canonical bytes have the hash
    recorded in that snapshot's inventory.

    Refused with ATLAS_HOSTED=1 before anything is written (`hosted.HostedExecutionRefused`).
    """
    refuse_if_hosted("executing a candidate")
    started = time.monotonic()
    candidate_dir = Path(candidate_dir)
    candidate_dir.mkdir(parents=True, exist_ok=False)
    computed_hash = candidate_hash(snapshot.base_hash, candidate.entry_bytes)

    # Host-owned records of the authorized invocation, written before anything runs.
    _new_json(candidate_dir / "approval.json", approval.to_dict())
    _new_json(
        candidate_dir / "candidate.json",
        {
            "entry_point": candidate.entry_point,
            "diff_sha256": candidate.diff_sha256,
            "candidate_hash": computed_hash,
            "base_snapshot_hash": snapshot.base_hash,
            "image_ref": image,
            "limits": TRUSTED_LIMITS.to_dict(),
            "proposed_at": proposed_at.isoformat() if proposed_at else None,
            "approved_at": approval.approved_at,
        },
    )

    # 1. The snapshot must be the approved one before anything is derived from it.
    binding = _approval_binding_problem(snapshot, approval)
    if binding is not None:
        manifest_bytes, manifest, problem = None, None, binding
        required = None  # the approved snapshot's manifest is not available here
    else:
        # 2. Its manifest must still be the bytes recorded when it was built.
        manifest_bytes, manifest, problem = _snapshot_manifest(snapshot)
        if problem is not None:
            problem = f"snapshot_manifest_invalid: {problem}"
            required = _trusted_required_set(snapshot, trusted_manifest)
    if problem is not None:
        record = {
            "stage": "preflight",
            "runner": None,
            "status": "refused",
            "reason": problem,
            "docker_used": False,
            "approval": approval.to_dict(),
            "base_snapshot_hash": snapshot.base_hash,
            "candidate_hash": computed_hash,
        }
        _new_json(candidate_dir / "execution.json", record)
        return _result(
            candidate_dir,
            computed_hash,
            approval,
            candidate,
            record,
            False,
            _not_executed(candidate_dir, required, record),
            started,
            proposed_at,
        )

    # The runner re-checks both hashes against the bytes it stages, before Docker is touched.
    exec_dir = candidate_dir / EXEC_DIR
    try:
        record = dr.run_candidate(
            snapshot,
            candidate,
            approval,
            exec_dir,
            limits=TRUSTED_LIMITS,
            image=image,
            env=env,
        )
    except Exception:  # noqa: BLE001 - runner_error: the runner saved its record, then raised
        record = _saved_record(exec_dir)

    if record.get("status") in NOT_RUN or not (exec_dir / "execution.json").is_file():
        outcome = _not_executed(candidate_dir, required_assertions(manifest), record)
        evaluated = False
    else:
        _build_view(candidate_dir, snapshot, manifest_bytes, manifest)
        outcome = evaluate(snapshot.root, candidate_dir, image_verifier=image_verifier)
        evaluated = True
    return _result(
        candidate_dir,
        computed_hash,
        approval,
        candidate,
        record,
        evaluated,
        outcome,
        started,
        proposed_at,
    )


def _canonical_manifest_bytes(manifest: Manifest) -> bytes:
    """The serialization `candidates.build_snapshot` writes into a snapshot."""
    text = json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    return text.encode("utf-8")


def _approval_binding_problem(snapshot: Snapshot, approval: Approval) -> str | None:
    """Why the supplied snapshot is not the approved one, or None. The approval names the
    snapshot by its base hash; the snapshot object must also be internally consistent (its
    recorded inventory hashes to that base hash), since the manifest check reads that inventory.
    The bytes on disk are re-hashed later by the runner, before anything executes."""
    if inventory_hash(snapshot.inventory) != snapshot.base_hash:
        return "snapshot_inconsistent: the recorded inventory does not hash to the base hash"
    if approval.base_snapshot_hash != snapshot.base_hash:
        return (
            "approval_for_other_snapshot: the supplied snapshot is not the approved one"
        )
    return None


def _snapshot_manifest(snapshot: Snapshot):
    """(bytes, manifest, None), or (None, None, problem) if the snapshot's manifest is missing,
    unreadable, no longer the bytes recorded at snapshot time, or invalid."""
    try:
        data = _permitted_file(snapshot.root, MANIFEST_NAME, MAX_MANIFEST_BYTES)
    except SnapshotError as exc:
        return None, None, f"manifest unreadable ({exc})"
    if sha256_bytes(data) != dict(snapshot.inventory).get(MANIFEST_NAME):
        return None, None, "manifest changed after the snapshot was built"
    try:
        return data, Manifest.model_validate_json(data), None
    except (ValueError, RecursionError) as exc:
        return None, None, f"manifest invalid ({type(exc).__name__})"


def _trusted_required_set(
    snapshot: Snapshot, trusted_manifest: Manifest | None
) -> list[str] | None:
    """The required set from a manifest bound to the snapshot's recorded hash, else None."""
    if trusted_manifest is None:
        return None
    recorded = dict(snapshot.inventory).get(MANIFEST_NAME)
    if sha256_bytes(_canonical_manifest_bytes(trusted_manifest)) != recorded:
        return None
    return required_assertions(trusted_manifest)


def _result(
    candidate_dir: Path,
    computed_hash: str,
    approval: Approval,
    candidate: Candidate,
    record: dict,
    evaluated: bool,
    outcome: RunOutcome,
    started: float,
    proposed_at: datetime | None,
) -> CandidateResult:
    finished = datetime.now(UTC)
    return CandidateResult(
        candidate_dir=candidate_dir,
        candidate_hash=computed_hash,
        approval=approval.to_dict(),
        diff_sha256=candidate.diff_sha256,
        execution={
            k: record.get(k)
            for k in (
                "status",
                "reason",
                "execution_status",
                "execution_reason",
                "capability",
                "container_removed",
                "elapsed_s",
            )
        },
        evaluated=evaluated,
        outcome=outcome,
        timing={
            "proposed_at": proposed_at.isoformat() if proposed_at else None,
            "approved_at": approval.approved_at,
            "execution_started_utc": record.get("started_utc"),
            "execution_elapsed_s": record.get("elapsed_s"),
            # Revalidation, execution, collection and evaluation; excludes approval waiting.
            "active_s": round(time.monotonic() - started, 3),
            "total_elapsed_s": round((finished - proposed_at).total_seconds(), 3)
            if proposed_at
            else None,
        },
        candidate_output=_candidate_output(record),
    )


def _candidate_output(record: dict) -> str | None:
    """The supervisor's captured candidate output, if the candidate ran and it was recorded."""
    supervisor = record.get("supervisor")
    tail = (
        supervisor.get("candidate_output_tail")
        if isinstance(supervisor, dict)
        else None
    )
    return tail if isinstance(tail, str) else None


def _saved_record(exec_dir: Path) -> dict:
    try:
        return json.loads((exec_dir / "execution.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "runner_error", "reason": "runner raised without a record"}


def _not_executed(
    candidate_dir: Path, required: list[str] | None, record: dict
) -> RunOutcome:
    """Nothing ran: every required assertion is NOT_ASSESSED (not_executed), never clean. With no
    trusted source for the required set, the outcome says so and lists no assertion."""
    reason = f"candidate not executed ({record.get('status')}: {record.get('reason')})"
    if required is None:
        outcome = RunOutcome(
            outcome=Outcome.INCONCLUSIVE,
            policy_version=POLICY_VERSION,
            reason=f"{reason}; the approved required assertion set could not be "
            "reconstructed: no trusted manifest bound to the approved snapshot",
            incomplete_coverage=["required_assertion_set"],
        )
    else:
        results = materialize(required, {})
        outcome = RunOutcome(
            outcome=Outcome.INCONCLUSIVE,
            policy_version=POLICY_VERSION,
            reason=reason,
            assertions=results,
            incomplete_coverage=incomplete_coverage(results),
        )
    _new_json(candidate_dir / "outcome.json", outcome.model_dump(mode="json"))
    _new_json(
        candidate_dir / "report.json",
        {
            "outcome": outcome.outcome,
            "reason": outcome.reason,
            "execution": record,
            "limitations": [
                (
                    "The candidate was not executed, so no evidence exists for it; "
                    "there is no host fallback (SPEC §9.8)."
                )
            ],
        },
    )
    return outcome


def _build_view(
    candidate_dir: Path, snapshot: Snapshot, manifest_bytes: bytes, manifest: Manifest
) -> None:
    exec_dir = candidate_dir / EXEC_DIR
    record_bytes = (exec_dir / "execution.json").read_bytes()
    _new_bytes(candidate_dir / "execution.json", record_bytes)
    _new_bytes(candidate_dir / "manifest.snapshot.json", manifest_bytes)
    try:
        record = json.loads(record_bytes)
        files = (record.get("collection") or {}).get("files") or []
        plan = plan_mapping(files)
    except (ValueError, AttributeError, KeyError, TypeError):
        plan = {"mapped": [], "unmapped": [], "collisions": []}
    copied, problems = {}, []
    for item in plan["mapped"]:
        try:
            data = (exec_dir / "out" / item["from"]).read_bytes()
        except OSError as exc:
            problems.append(f"{item['from']}: {type(exc).__name__}")
            continue
        if sha256_bytes(data) != item["sha256"]:
            problems.append(f"{item['from']}: bytes differ from the collection record")
            continue
        try:
            _new_bytes(candidate_dir / item["to"], data)
        except OSError as exc:
            problems.append(f"{item['from']}: {type(exc).__name__}")
            continue
        copied[item["to"]] = sha256_bytes(data)
    _new_json(
        candidate_dir / VIEW_NAME, {"exec_dir": EXEC_DIR, **plan, "problems": problems}
    )
    artifacts = {
        name: sha256_bytes((candidate_dir / name).read_bytes()) for name in HOST_RECORDS
    }
    _new_json(
        candidate_dir / "index.json",
        {
            "artifacts": {**artifacts, **copied},
            "table": {
                "path": manifest.table.path,
                "sha256": dict(snapshot.inventory)[manifest.table.path],
            },
        },
    )
