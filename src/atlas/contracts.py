"""Data contracts shared by the trusted evaluator (SPEC §3, §5, §6, §7)."""

import math
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _finite_number(value: Any) -> Any:
    """A finite int or float. Booleans, strings and nonfinite values are refused (SPEC §3)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # ValueError, not TypeError: pydantic reports only ValueError as a validation error.
        raise ValueError(  # noqa: TRY004
            "must be a finite number (booleans and strings are not accepted)"
        )
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


Number = Annotated[float, BeforeValidator(_finite_number)]
NonNegative = Annotated[float, BeforeValidator(_finite_number), Field(ge=0)]
UnitInterval = Annotated[float, BeforeValidator(_finite_number), Field(ge=0, le=1)]


def _text(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        raise ValueError("must not be empty")
    return value


Text = Annotated[str, BeforeValidator(_text)]


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
    EMPTY_EVALUATION = "empty_evaluation"
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


class TimeBasis(BaseModel):
    """All temporal values are numbers in `unit`. `reference_time` is documentation only.

    `scope` says which values are comparable: `global` (any two) or `per_stream` (within a
    stream). Required in schema 0.3; absent in legacy 0.2 means unspecified (SPEC §3).
    """

    model_config = ConfigDict(extra="forbid")
    unit: Text
    reference_time: Text
    scope: Literal["global", "per_stream"] | None = None


class AvailabilitySource(BaseModel):
    """Exactly one of an availability-time column or an offset from prediction time."""

    model_config = ConfigDict(extra="forbid")
    column: Text | None = None
    offset: Number | None = None

    @model_validator(mode="after")
    def _exactly_one(self):
        if (self.column is None) == (self.offset is None):
            raise ValueError("give exactly one of 'column' or 'offset'")
        return self


class LabelAvailability(BaseModel):
    """An availability-time column, or horizon + reporting delay after prediction time."""

    model_config = ConfigDict(extra="forbid")
    column: Text | None = None
    horizon: NonNegative | None = None
    reporting_delay: NonNegative | None = None

    @model_validator(mode="after")
    def _one_form(self):
        offsets = (self.horizon, self.reporting_delay)
        if self.column is not None and any(v is not None for v in offsets):
            raise ValueError(
                "give either 'column' or 'horizon' + 'reporting_delay', not both"
            )
        if self.column is None and any(v is None for v in offsets):
            raise ValueError("give 'column', or both 'horizon' and 'reporting_delay'")
        return self


class SeparationRule(BaseModel):
    """Declared separation for temporal_order. `times` is required in schema 0.3."""

    model_config = ConfigDict(extra="forbid")
    scope: Literal["global", "per_stream"]
    min_gap: NonNegative
    times: Literal["prediction_time", "window"] | None = None


class WindowContainment(BaseModel):
    """A documented declaration that streams lie within groups. Recorded, never verified."""

    model_config = ConfigDict(extra="forbid")
    within: Literal["group_id"]
    source: Text
    statement: Text


class ReportedMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric_definition: Literal["balanced_accuracy", "macro_f1"]
    partition: Literal["development_eval", "final_holdout"]
    fold: Text
    aggregation: Literal["single_fold", "mean_over_folds", "pooled"]
    value: UnitInterval

    @model_validator(mode="after")
    def _fold_matches_aggregation(self):
        if (self.fold == "all") != (self.aggregation != "single_fold"):
            raise ValueError(
                "fold 'all' goes with mean_over_folds or pooled; a named fold goes with single_fold"
            )
        return self


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["0.2", "0.3"]
    table: TableRef
    columns: Columns
    claim: Claim
    primary_metric: Literal["balanced_accuracy", "macro_f1"]
    development_seeds: list[int]
    entry_point: str
    known_duplicates: list[list[str]] = Field(default_factory=list)
    reported_metrics: list[ReportedMetric] = Field(default_factory=list)
    time_basis: TimeBasis | None = None
    feature_availability: dict[str, AvailabilitySource] | None = None
    label_availability: LabelAvailability | None = None
    temporal_gap: Number | None = None
    separation_rule: SeparationRule | None = None
    window_containment: WindowContainment | None = None

    @model_validator(mode="after")
    def _version_and_references(self):
        if self.schema_version == "0.3":
            if self.time_basis is not None and self.time_basis.scope is None:
                raise ValueError("time_basis.scope is required in schema 0.3")
            if self.separation_rule is not None and self.separation_rule.times is None:
                raise ValueError("separation_rule.times is required in schema 0.3")
        unknown = set(self.feature_availability or {}) - set(self.columns.features)
        if unknown:
            raise ValueError(
                f"feature_availability names undeclared features: {sorted(unknown)}"
            )
        return self

    def dependence_kinds(self) -> set[str]:
        return {d.kind for d in self.claim.dependence}


class DescriptiveResult(BaseModel):
    """A descriptive result (SPEC §5 'D'): reported, never part of outcome derivation."""

    result_id: str
    available: bool
    reason: str | None = None
    observed: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RunOutcome(BaseModel):
    outcome: Outcome
    policy_version: str
    reason: str | None = None
    assertions: list[AssertionResult] = Field(default_factory=list)
    incomplete_coverage: list[str] = Field(default_factory=list)
    descriptive: list[DescriptiveResult] = Field(default_factory=list)


class ExecutionRecord(BaseModel):
    """execution.json, written by the trusted runner after the fixture child exits."""

    model_config = ConfigDict(extra="forbid", strict=True)
    runner: str
    capability: str
    returncode: int | None
    timed_out: bool
    elapsed_s: float
    stderr_tail: str


class RuntimeRecord(BaseModel):
    """runtime.json, written by the fixture child: where its imports resolved from."""

    model_config = ConfigDict(extra="forbid", strict=True)
    atlas_origin: str
    isolated: int
    safe_path: bool
    project_dir_on_sys_path: bool
    cwd_on_sys_path: bool
    python: str
