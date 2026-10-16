"""Trusted evaluation of Docker candidate runs (SPEC §9, §10; T-06 slice 1).

A candidate's evidence reaches the trusted evaluator only through a *candidate view*, a
directory the trusted controller (`atlas.agent.execute`) builds around the runner's own run
directory:

    approval.json           host-owned, written before execution: the exact approval
    candidate.json          host-owned, written before execution: the invocation context
    exec/                   the Docker runner's run directory (execution.json, stage/, out/)
    execution.json          host-owned: byte copy of exec/execution.json
    manifest.snapshot.json  host-owned: the snapshot's manifest bytes
    view.json               host-owned: marks the view; lists the mapping applied
    runtime.json, provenance.jsonl, splits.json, predictions/<fold>.parquet
                            candidate-produced: copied from exec/out/ through `map_collected`
    index.json              host-owned: hashes of everything above except exec/

**Trust is anchored outside the record.** `execution.json` is never checked only against
itself. The approval comes from approval.json (written before execution). The snapshot is
re-hashed from disk against that approval. The staged project and the staged code are
re-hashed from disk; the staged code must equal the evaluator's own copy of the mounted
modules. The limits must equal the trusted runner limits, and the recorded `docker run`
command must equal the one `docker_run_args` builds from the trusted limits, the view's own
paths and an image that Docker itself confirms is the runner image (recipe label, non-root
user). Changing a limit together with its recorded command is therefore still refused.

**What this does not establish.** Matching hashes establish consistency, not authenticity
against an attacker who controls the host. `runtime.json`, provenance, splits and predictions
are written inside the candidate process: they are candidate-produced (SPEC §9.9), and
`runtime.json` only corroborates.

Order: shared integrity and binding first. A failure there (the record, the approval, the
snapshot, the staged bytes, the configuration, the view record, a host-name collision or an
indexed file that was never collected) makes the mode `UNTRUSTED`: every PASS and FAIL becomes
ERROR, because no evidence of that execution can be attributed to the approved candidate.

Individual collected artifacts are checked separately. The host collection record is the
authority for each artifact's hash: an artifact the view lacks (for example, a failed copy) or
whose indexed hash differs from the collection record is unavailable, and so is an artifact
whose bytes no longer match. Only the assertions that depend on it lose their evidence
(ERROR, as for any missing artifact); findings established from other, separately verified
artifacts stand. A mismatched artifact is never accepted to preserve a finding.

Then the documented status mapping, with `runtime.json` as corroboration only.
"""

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from pydantic import ValidationError

from atlas.candidates import (
    MAX_ENTRY_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_TABLE_BYTES,
    SnapshotError,
    _permitted_file,
    candidate_hash,
    current_inventory,
    inventory_hash,
    safe_relpath,
    sha256_bytes,
)
from atlas.contracts import (
    ApprovalRecord,
    ContainerRuntimeRecord,
    DockerExecutionRecord,
    Manifest,
)
from atlas.intake import MANIFEST_NAME
from atlas.reports import sha256_file, verified
from atlas.runner import docker as dr

EXEC_DIR = "exec"
VIEW_NAME = "view.json"
HOST_RECORDS = (
    "approval.json",
    "candidate.json",
    "execution.json",
    "manifest.snapshot.json",
    VIEW_NAME,
)
# Names the candidate's collected files may never take (compared case-insensitively, because
# the view may live on a case-insensitive file system).
HOST_OWNED = frozenset({*HOST_RECORDS, "index.json", "outcome.json", "report.json"})
RESERVED_PREFIXES = ("checks/", f"{EXEC_DIR}/")
CANDIDATE_FILES = ("runtime.json", "provenance.jsonl", "splits.json")
TRUSTED_LIMITS = dr.DEFAULT_LIMITS
CONTAINER_NAME = re.compile(r"atlas-t05-[0-9a-f]{12}")
CONTAINER_RUNTIME = {
    "isolated": 1,
    "safe_path": True,
    "uid": 10001,
    "gid": 10001,
    "cwd": "/work/project",
    "atlas_origin": "/opt/atlas/atlas/__init__.py",
}

# Trust modes returned with every problem.
COMPLETED = "completed"  # trusted, completed execution
NOT_COMPLETED = "not_completed"  # trusted record of a verified non-completion
UNCONFIRMED = (
    "unconfirmed"  # trusted binding, but the execution or its evidence is unconfirmed
)
UNTRUSTED = "untrusted"  # integrity or binding failed: nothing can be attributed

ImageVerifier = Callable[[str], str | None]


class Trust(NamedTuple):
    """The evaluator's view of an execution: its record, the problem and trust mode, the index
    the evidence checks may use, and the artifacts that are individually unavailable."""

    record: dict | None
    problem: str | None
    mode: str
    evidence_index: dict
    artifact_problems: list[str]


NOT_TRUSTED = "Docker execution evidence not trusted: "


def map_collected(path: str) -> tuple[str, str | None]:
    """(kind, name in the view) for one collected path: mapped, collision or unmapped."""
    folded = path.casefold()
    if folded in {h.casefold() for h in HOST_OWNED} or folded.startswith(
        tuple(p.casefold() for p in RESERVED_PREFIXES)
    ):
        return "collision", None
    if path in CANDIDATE_FILES:
        return "mapped", path
    parts = path.split("/")
    if len(parts) == 2 and parts[0] == "predictions" and parts[1].endswith(".parquet"):
        try:
            safe_relpath(path)
        except SnapshotError:
            return "unmapped", None
        return "mapped", path
    return "unmapped", None


def plan_mapping(files: list[dict]) -> dict:
    """The explicit artifact mapping for a list of collected files {path, size, sha256}.

    The same function is used by the controller that builds the view and by the evaluator that
    checks it, so the evaluator derives the mapping from the host record, not from view.json.
    """
    mapped, unmapped, collisions, seen = [], [], [], set()
    for f in sorted(files, key=lambda f: f["path"]):
        kind, target = map_collected(f["path"])
        if kind == "mapped" and target.casefold() in seen:
            kind = "collision"  # two outputs that would land on one file
        if kind == "mapped":
            seen.add(target.casefold())
            mapped.append({"from": f["path"], "to": target, "sha256": f["sha256"]})
        elif kind == "collision":
            collisions.append(f["path"])
        else:
            unmapped.append(f["path"])
    return {"mapped": mapped, "unmapped": unmapped, "collisions": collisions}


def expected_mounted_code() -> list[list[str]]:
    """The evaluator's own hashes of the code the runner must have mounted."""
    items = [
        [f"atlas/{n}", sha256_bytes(dr._lf_bytes(dr.PACKAGE_DIR / n))]
        for n in dr.MOUNTED_MODULES
    ]
    items.append([dr.ENTRY_NAME, sha256_bytes(dr._lf_bytes(dr.ENTRY_SOURCE))])
    return sorted(items)


def snapshot_limits(manifest: Manifest) -> dict[str, int]:
    return {
        MANIFEST_NAME: MAX_MANIFEST_BYTES,
        manifest.entry_point: MAX_ENTRY_BYTES,
        manifest.table.path: MAX_TABLE_BYTES,
    }


def verify_runner_image(image_id: str) -> str | None:
    """Ask Docker whether `image_id` is the runner image (recipe label, non-root user)."""
    cap = dr.probe(image_id)
    if cap.state != dr.CAPABILITY_AVAILABLE:
        return f"runner image could not be verified: {cap.reason}"
    if cap.image_id != image_id:
        return "runner image identity does not match the recorded image"
    return None


def docker_trust(
    project: Path,
    run_dir: Path,
    index: dict,
    manifest: Manifest,
    image_verifier: ImageVerifier | None = None,
) -> Trust:
    """Shared trust of a candidate view, then the availability of each collected artifact."""
    exec_path, _, exec_ok = verified(run_dir, index, "execution.json")
    if not exec_ok:
        problem = f"{NOT_TRUSTED}execution record missing or hash-mismatched"
        return Trust(None, problem, UNTRUSTED, index, [])
    try:
        record = DockerExecutionRecord.model_validate_json(
            exec_path.read_text(encoding="utf-8")
        )
    except (ValueError, RecursionError):
        problem = f"{NOT_TRUSTED}execution record fails schema validation"
        return Trust(None, problem, UNTRUSTED, index, [])
    dump = record.model_dump(mode="json")
    problem = _integrity_problem(
        project, run_dir, index, manifest, record, image_verifier or verify_runner_image
    )
    if problem is not None:
        return Trust(dump, f"{NOT_TRUSTED}{problem}", UNTRUSTED, index, [])
    evidence_index, artifact_problems = _artifact_index(index, record)
    problem, mode = _status_mapping(run_dir, evidence_index, record)
    return Trust(dump, problem, mode, evidence_index, artifact_problems)


def _artifact_index(
    index: dict, record: DockerExecutionRecord
) -> tuple[dict, list[str]]:
    """The index the evidence checks use: host records as indexed, and each collected artifact
    with the hash from the host collection record, only if the view indexed exactly that hash.
    An artifact the view lacks or indexed differently is left out, so its dependants see it as
    missing; whether its bytes still match is checked when it is read (`verified`)."""
    files = (
        [f.model_dump() for f in record.collection.files] if record.collection else []
    )
    artifacts = {k: v for k, v in index["artifacts"].items() if k in HOST_RECORDS}
    problems = []
    for item in plan_mapping(files)["mapped"]:
        indexed = index["artifacts"].get(item["to"])
        if indexed == item["sha256"]:
            artifacts[item["to"]] = item["sha256"]
        elif indexed is None:
            problems.append(f"{item['to']} unavailable: not in the candidate view")
        else:
            problems.append(
                f"{item['to']} unavailable: indexed hash differs from the collection record"
            )
    return {**index, "artifacts": artifacts}, problems


def _read_verified(run_dir: Path, index: dict, name: str):
    path, _, ok = verified(run_dir, index, name)
    if not ok:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return None


def _integrity_problem(
    project: Path,
    run_dir: Path,
    index: dict,
    manifest: Manifest,
    record: DockerExecutionRecord,
    image_verifier: ImageVerifier,
) -> str | None:
    if record.runner != dr.RUNNER_NAME:
        return f"the candidate view holds a record from runner {record.runner!r}"
    if record.capability != dr.CAPABILITY_AVAILABLE:
        return f"execution capability {record.capability!r} is not isolated"
    exec_copy = run_dir / EXEC_DIR / "execution.json"
    if not exec_copy.is_file() or sha256_file(exec_copy) != index["artifacts"].get(
        "execution.json"
    ):
        return "execution.json differs from the runner's own record"

    # 1. The approval, written before execution, is the anchor for both hashes.
    try:
        approval = ApprovalRecord.model_validate(
            _read_verified(run_dir, index, "approval.json")
        )
    except ValidationError:
        return "approval record missing, hash-mismatched or invalid"
    if record.approval != approval:
        return "the runner executed under a different approval"
    if (record.base_snapshot_hash, record.candidate_hash) != (
        approval.base_snapshot_hash,
        approval.candidate_hash,
    ):
        return "the runner's hashes differ from the approval"

    # 2. The snapshot, re-hashed from disk, is the approved one.
    limits = snapshot_limits(manifest)
    try:
        live = dict(current_inventory(project, limits))
    except SnapshotError as exc:
        return f"snapshot cannot be re-hashed: {exc}"
    if inventory_hash(sorted(live.items())) != approval.base_snapshot_hash:
        return "the snapshot changed or is not the approved snapshot"
    if index["artifacts"].get("manifest.snapshot.json") != live[MANIFEST_NAME]:
        return "manifest.snapshot.json is not the snapshot's manifest"
    if (index.get("table") or {}).get("sha256") != live[manifest.table.path]:
        return "the indexed table is not the snapshot's table"

    # 3. The staged bytes are the approved candidate on the approved snapshot.
    stage = run_dir / EXEC_DIR / "stage"
    try:
        staged = dict(current_inventory(stage / "project", limits))
        entry = _permitted_file(
            stage / "project", manifest.entry_point, MAX_ENTRY_BYTES
        )
        code = current_inventory(
            stage / "code",
            dict.fromkeys(
                (p for p, _ in expected_mounted_code()), dr.MAX_CODE_FILE_BYTES
            ),
        )
    except SnapshotError as exc:
        return f"staged files cannot be re-hashed: {exc}"
    if any(staged[rel] != live[rel] for rel in live if rel != manifest.entry_point):
        return "staged project inputs differ from the snapshot"
    if candidate_hash(approval.base_snapshot_hash, entry) != approval.candidate_hash:
        return "the staged entry point is not the approved candidate"
    if record.staged_project != sorted([list(i) for i in staged.items()]):
        return "the recorded staged project differs from the staged files"
    expected_code = expected_mounted_code()
    if sorted([list(i) for i in code]) != expected_code:
        return "staged code differs from the trusted adapter and recorder"
    if record.mounted_code is None or sorted(record.mounted_code) != expected_code:
        return "the recorded mounted code differs from the trusted adapter and recorder"

    # 4. The container configuration is the trusted one, not just self-consistent.
    if record.limits != TRUSTED_LIMITS.to_dict():
        return "execution limits differ from the trusted runner limits"
    docker = record.docker
    if docker is None or docker.recipe_sha256 != dr.recipe_sha256():
        return "runner image recipe differs from the trusted recipe"
    if not isinstance(docker.image_id, str) or not docker.image_id:
        return "runner image is not recorded"
    if record.container_name is None or not CONTAINER_NAME.fullmatch(
        record.container_name
    ):
        return "container name is not one this runner creates"
    image_problem = image_verifier(docker.image_id)
    if image_problem is not None:
        return image_problem
    expected_args = dr.docker_run_args(
        record.container_name,
        EXEC_DIR,
        (stage / "project").resolve(),
        (stage / "code").resolve(),
        docker.image_id,
        TRUSTED_LIMITS,
    )
    if record.docker_args != expected_args:
        return "the recorded docker command differs from the trusted runner command"

    # 5. The view holds exactly the collected files, through the explicit mapping.
    files = (
        [f.model_dump() for f in record.collection.files] if record.collection else []
    )
    plan = plan_mapping(files)
    if plan["collisions"]:
        return f"candidate output collides with host-owned names: {plan['collisions']}"
    view = _read_verified(run_dir, index, VIEW_NAME)
    if not isinstance(view, dict) or view.get("mapped") != plan["mapped"]:
        return "view.json does not match the mapping of the recorded collection"
    # An indexed file that was never collected (an extra or remapped name) is a host-record
    # inconsistency, not a missing artifact. Missing or differing collected artifacts are
    # handled one by one in `_artifact_index`.
    expected = {m["to"] for m in plan["mapped"]}
    extra = sorted(
        k for k in index["artifacts"] if k not in HOST_RECORDS and k not in expected
    )
    if extra:
        return f"the view indexes files that were not collected: {extra[:5]}"
    return _status_consistency(record)


def _status_consistency(record: DockerExecutionRecord) -> str | None:
    """A host record whose status contradicts its own details is not trusted."""
    sup = record.supervisor
    removed = record.container_removed is True and (
        record.cleanup is not None and record.cleanup.status == dr.CLEANUP_CONFIRMED
    )
    collected = record.collection is not None and record.collection.status == "ok"
    if record.status == "completed" and not (
        sup is not None
        and sup.child_returncode == 0
        and sup.timed_out is False
        and record.host_timed_out is False
        and collected
        and removed
    ):
        return "status 'completed' contradicts the recorded execution details"
    if record.status == "failed" and not (
        sup is not None
        and sup.child_returncode not in (0, None)
        and collected
        and removed
    ):
        return "status 'failed' contradicts the recorded execution details"
    return None


def _status_mapping(
    run_dir: Path, index: dict, record: DockerExecutionRecord
) -> tuple[str | None, str]:
    if record.status in ("failed", "timed_out"):
        return (
            f"candidate execution did not complete ({record.status}: {record.reason})",
            NOT_COMPLETED,
        )
    if record.status != "completed":
        return (
            f"candidate execution not confirmed ({record.status}: {record.reason})",
            UNCONFIRMED,
        )
    try:
        runtime = ContainerRuntimeRecord.model_validate(
            _read_verified(run_dir, index, "runtime.json")
        )
    except ValidationError:
        return "container runtime record missing or invalid", UNCONFIRMED
    observed = {k: getattr(runtime, k) for k in CONTAINER_RUNTIME}
    if observed != CONTAINER_RUNTIME:
        return "container runtime record is inconsistent with the runner", UNCONFIRMED
    return None, COMPLETED
