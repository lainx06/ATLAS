"""Data contracts shared by the trusted evaluator (SPEC §3, §5, §6, §7)."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_ASSESSED = "NOT_ASSESSED"
    ERROR = "ERROR"


class Outcome(StrEnum):
    NOT_SUPPORTED = "NOT_SUPPORTED"
    VIOLATION_FOUND = "VIOLATION_FOUND"
    INCONCLUSIVE = "INCONCLUSIVE"
    NO_VIOLATION_FOUND = "NO_VIOLATION_FOUND"


class Reason(StrEnum):
    """Reason codes for NOT_ASSESSED (SPEC §6) plus evidence-integrity codes for ERROR."""

    UNIMPLEMENTED_ASSERTION = "unimplemented_assertion"
    NOT_EXECUTED = "not_executed"
    MISSING_METADATA = "missing_metadata"
    UNKNOWN_ANCESTRY = "unknown_ancestry"
    ZERO_FIT = "zero_fit"
    COVERAGE_GAP = "coverage_gap"
    NO_SUPPORTED_RULE = "no_supported_rule"
    NO_DECLARED_RULE = "no_declared_rule"
    UNRESOLVED_DUPLICATE_CANDIDATES = "unresolved_duplicate_candidates"
    EVIDENCE_INVALID = "evidence_invalid"


class EvidenceRef(BaseModel):
    artifact: str
    sha256: str | None


class AssertionResult(BaseModel):
    assertion_id: str
    status: Status
    reason: Reason | None = None
    observed: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_valid: bool = True


class TableRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    format: str


class Columns(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row_id: str
    target: str
    class_map: dict[str, str]
    features: list[str]
    group_id: str | None = None
    unit_id: str | None = None
    observation_id: str | None = None
    stream_id: str | None = None
    window_start: str | None = None
    window_end: str | None = None
    prediction_time: str | None = None


class Dependence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    column: str | None = None
    text: str | None = None


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Kept loose on purpose: an unsupported claim type is a run-level NOT_SUPPORTED, not a parse error.
    type: Any
    statement: str
    sampling_unit: str
    dependence: list[Dependence] = Field(default_factory=list)


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str
    table: TableRef
    columns: Columns
    claim: Claim
    primary_metric: str
    development_seeds: list[int]
    entry_point: str
    known_duplicates: list[list[str]] = Field(default_factory=list)
    reported_metrics: list[dict[str, Any]] = Field(default_factory=list)
    time_basis: dict[str, Any] | None = None
    feature_availability: dict[str, Any] | None = None
    label_availability: dict[str, Any] | None = None
    temporal_gap: float | None = None
    separation_rule: dict[str, Any] | None = None

    def dependence_kinds(self) -> set[str]:
        return {d.kind for d in self.claim.dependence}


class RunOutcome(BaseModel):
    outcome: Outcome
    policy_version: str
    reason: str | None = None
    assertions: list[AssertionResult] = Field(default_factory=list)
    incomplete_coverage: list[str] = Field(default_factory=list)
