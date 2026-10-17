"""The curated project list (GAP-2: the engine has no catalogue API) and claim lookup."""

from dataclasses import dataclass
from pathlib import Path

from atlas.intake import load_project

ROOT = Path(__file__).resolve().parents[3]
BENCHMARKS = ROOT / "benchmarks" / "t01"
CATALOGUE_LABEL = "Development fixtures (synthetic), not benchmark evidence"


@dataclass(frozen=True)
class Fixture:
    name: str
    purpose: str

    @property
    def path(self) -> Path:
        return BENCHMARKS / self.name


FIXTURES = (
    Fixture("s01_faulty", "The faulty main case"),
    Fixture("s02_clean", "Clean control"),
    Fixture("s06_missing_metadata", "Missing metadata"),
    Fixture(
        "s07_unimplemented_window",
        "Truthfully declared overlapping windows (NO_VIOLATION_FOUND under policy-v1.3; "
        "INCONCLUSIVE under v1.2, hence the name)",
    ),
    Fixture("s08a_combined_claim", "Combined claim: NOT_SUPPORTED"),
)
BY_NAME = {f.name: f for f in FIXTURES}


@dataclass(frozen=True)
class ClaimView:
    """What intake reads from `atlas_manifest.json:claim` (read-only, GAP-1)."""

    supported: bool
    reason: str | None
    type: str | None
    statement: str | None
    sampling_unit: str | None
    dependence: list[dict]
    roles: dict[str, str | None]
    entry_point: str | None
    primary_metric: str | None


def read_claim(project: Path) -> ClaimView:
    """Intake's view of the project. Raises only if the project cannot be read at all."""
    intake = load_project(project)
    manifest = intake.manifest
    if manifest is None:
        return ClaimView(False, intake.reason, None, None, None, [], {}, None, None)
    claim = manifest.claim
    cols = manifest.columns
    return ClaimView(
        supported=intake.supported,
        reason=intake.reason,
        type=str(claim.type),
        statement=claim.statement,
        sampling_unit=claim.sampling_unit,
        dependence=[d.model_dump() for d in claim.dependence],
        roles={
            "target": cols.target,
            "group_id": cols.group_id,
            "unit_id": cols.unit_id,
            "observation_id": cols.observation_id,
        },
        entry_point=manifest.entry_point,
        primary_metric=getattr(manifest, "primary_metric", None),
    )
