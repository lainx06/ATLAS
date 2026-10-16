"""Data contracts shared by the trusted evaluator (SPEC §3, §5, §6, §7)."""

import math
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    TypeAdapter,
    model_validator,
)


def _finite_number(value: Any) -> Any:
    """A finite int or float. Booleans, strings and nonfinite values are refused (SPEC §3)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # ValueError, not TypeError: pydantic reports only ValueError as a validation error.
        raise ValueError(  # noqa: TRY004
            "must be a finite number (booleans and strings are not accepted)"
        )
    try:
        number = float(value)  # an int beyond float64 range raises OverflowError here
    except OverflowError:
        raise ValueError("must be finite (outside the float64 range)") from None
    if not math.isfinite(number):
        raise ValueError("must be finite")
    return number


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


# --- Docker candidate evidence (T-06 slice 1) --------------------------------------------------
# The fields the trusted evaluator reads from host-written Docker runner records, strict, with
# other fields allowed. Validating the shape says nothing about trust; docker_evidence.py checks
# every value against anchors outside the record.


class ApprovalRecord(BaseModel):
    """approval.json: the exact candidate approved against the exact snapshot (SPEC §9.5)."""

    model_config = ConfigDict(extra="forbid", strict=True)
    candidate_hash: str
    base_snapshot_hash: str
    approved_at: str


class _CollectedFile(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    path: str
    size: int
    sha256: str


class _Collection(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    status: str
    files: list[_CollectedFile]


class _DockerInfo(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    image_id: str | None = None
    recipe_sha256: str | None = None


class _Supervisor(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    child_returncode: int | None = None
    timed_out: bool | None = None


class _Cleanup(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    status: str


class DockerExecutionRecord(BaseModel):
    """execution.json as written by the Docker runner on the host (runner/docker.py)."""

    model_config = ConfigDict(extra="allow", strict=True)
    runner: str
    capability: str | None
    status: str
    reason: str | None
    approval: ApprovalRecord
    base_snapshot_hash: str
    candidate_hash: str | None
    limits: dict[str, Any]
    docker: _DockerInfo | None = None
    mounted_code: list[list[str]] | None = None
    staged_project: list[list[str]] | None = None
    container_name: str | None = None
    docker_args: list[str] | None = None
    container_removed: bool | None = None
    cleanup: _Cleanup | None = None
    collection: _Collection | None = None
    supervisor: _Supervisor | None = None
    host_timed_out: bool | None = None


class ContainerRuntimeRecord(BaseModel):
    """runtime.json written inside the container by the candidate process: corroborating only."""

    model_config = ConfigDict(extra="allow", strict=True)
    isolated: int
    safe_path: bool
    uid: int
    gid: int
    cwd: str
    atlas_origin: str


# --- Structure of evidence the trusted evaluator consumes (T-02 repair pass 4) -----------------
# Only fields the consumers actually read are checked, with the types the recorder and adapter
# write; other fields are allowed (extra="allow"). Strict: no coercion of strings, booleans or
# floats into other types. Recorded evidence is validated, never rewritten.


class _IndexTable(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    sha256: str | None = None


class RunIndex(BaseModel):
    """index.json as read by audit: artifact name -> sha256, and the table record."""

    model_config = ConfigDict(extra="allow", strict=True)
    artifacts: dict[str, str]
    table: _IndexTable | None = None


class _Event(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    type: str


class _LoadEvent(_Event):
    token: str | None = None


class _TakeEvent(_Event):
    token: str | None = None
    input_token: str | None
    input_status: str | None = None


class _FitEvent(_Event):
    instance: str
    version: int
    fold: str
    input_token: str | None
    input_status: str | None  # read directly by fit_provenance._walk: must be present
    labels_token: str | None = None
    classifier: bool
    supported: bool
    labels_supplied: bool
    labels_used: bool
    rows: list[str] | None
    deps: list[str] | None
    class_: str = Field(alias="class")


class _UseEvent(_Event):
    instance: str
    version: int | None
    state_fit_fold: str | None
    method: str
    fold: str
    input_token: str | None
    input_status: str | None = None
    input_known: bool
    output_token: str | None = None
    rows: list[str] | None
    effective_deps: list[str] | None
    class_: str = Field(alias="class")


class _SplitEvent(_Event):
    fold: str
    train_sha256: str
    eval_sha256: str


class _PredictionsEvent(_Event):
    fold: str
    pred_token: str | None
    pred_status: str
    rows: list[str] | None
    artifact: str | None = None
    artifact_sha256: str | None = None


PROVENANCE_EVENTS: dict[str, type[_Event]] = {
    "load": _LoadEvent,
    "take": _TakeEvent,
    "fit": _FitEvent,
    "use": _UseEvent,
    "split": _SplitEvent,
    "predictions": _PredictionsEvent,
}


def validate_provenance_event(event: Any) -> None:
    """Raise ValidationError (a ValueError) unless `event` has the structure its consumers read.

    Event types the evaluator does not consume (e.g. "gap") need only a string `type`.
    """
    if not isinstance(event, dict):
        # ValueError like pydantic's ValidationError, so the loader handles one error family.
        raise ValueError(f"event is a {type(event).__name__}, not an object")  # noqa: TRY004
    _Event.model_validate(event)
    model = PROVENANCE_EVENTS.get(event["type"])
    if model is not None:
        model.model_validate(event)


class SplitDeclaration(BaseModel):
    """One splits.json entry, as written by adapter.declare_split and read by every check.

    Required: string `fold`; `train_ids`/`eval_ids` as lists of string row IDs, each without
    repeats (the producer refuses duplicates within a list; SPEC §4.1). Empty lists are valid.
    Optional: `kind`, a string when present (consumers default a missing kind to
    development_eval; the default is never written back). `training_cutoff` is not checked here:
    the temporal checks judge it per fold, so an invalid cutoff is ERROR for the cutoff
    assertions only. Extra fields are allowed; nothing is coerced.
    """

    model_config = ConfigDict(extra="allow", strict=True)
    fold: str
    train_ids: list[str]
    eval_ids: list[str]
    kind: str = "development_eval"

    @model_validator(mode="after")
    def _no_repeats_within_a_list(self):
        for name in ("train_ids", "eval_ids"):
            ids = getattr(self, name)
            if len(ids) != len(set(ids)):
                raise ValueError(f"{name} repeats a row ID")
        return self


SPLITS = TypeAdapter(list[SplitDeclaration])
