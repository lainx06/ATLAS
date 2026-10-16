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
    _permitted_file,
    candidate_hash,
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
) -> CandidateResult:
    """Run one approved candidate in Docker and evaluate the full required set on the result."""
    started = time.monotonic()
    candidate_dir = Path(candidate_dir)
    candidate_dir.mkdir(parents=True, exist_ok=False)
    manifest_bytes = _permitted_file(snapshot.root, MANIFEST_NAME, MAX_MANIFEST_BYTES)
    manifest = Manifest.model_validate_json(manifest_bytes)
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
        outcome = _not_executed(candidate_dir, manifest, record)
        evaluated = False
    else:
        _build_view(candidate_dir, snapshot, manifest_bytes, manifest)
        outcome = evaluate(snapshot.root, candidate_dir, image_verifier=image_verifier)
        evaluated = True

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
    )


def _saved_record(exec_dir: Path) -> dict:
    try:
        return json.loads((exec_dir / "execution.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "runner_error", "reason": "runner raised without a record"}


def _not_executed(candidate_dir: Path, manifest: Manifest, record: dict) -> RunOutcome:
    """Nothing ran: every required assertion is NOT_ASSESSED (not_executed), never clean."""
    results = materialize(required_assertions(manifest), {})
    outcome = RunOutcome(
        outcome=Outcome.INCONCLUSIVE,
        policy_version=POLICY_VERSION,
        reason=f"candidate not executed ({record.get('status')}: {record.get('reason')})",
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
