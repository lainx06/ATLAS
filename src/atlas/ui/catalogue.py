"""The curated project list (GAP-2: the engine has no catalogue API) and claim lookup."""

from dataclasses import dataclass
from pathlib import Path

from atlas.intake import load_project

ROOT = Path(__file__).resolve().parents[3]
BENCHMARKS = ROOT / "benchmarks" / "t01"
REAL_SENSOR = ROOT / "benchmarks" / "real_sensor"
CATALOGUE_LABEL = (
    "s01-s08a: development fixtures (synthetic), not benchmark evidence. har_*: UCI HAR "
    "real data (CC BY 4.0), with ATLAS-authored evaluations."
)
RETRIEVE_COMMAND = "uv run --locked python benchmarks/real_sensor/retrieve.py"
HAR_UPSTREAM = (
    "Upstream preprocessing: the 561 features were computed and normalized by the dataset "
    'authors ("Features are normalized and bounded within [-1,1]", UCI HAR README.txt). '
    "Provenance begins at the supplied feature table; whether that normalization was fit "
    "globally (across subjects or partitions) is not established (docs/T09_CONTAINMENT.md §4)."
)


@dataclass(frozen=True)
class Fixture:
    name: str
    purpose: str
    root: Path = BENCHMARKS
    display: str | None = None  # the rail label; the name if None
    notes: tuple[
        str, ...
    ] = ()  # catalogue documentation shown with the finding, never a result
    compare_with: str | None = (
        None  # a related project for the descriptive metric comparison
    )

    @property
    def path(self) -> Path:
        return self.root / self.name

    @property
    def label(self) -> str:
        return self.display or self.name

    def unavailable(self) -> str | None:
        """Why the project cannot be run here (its data is not retrieved), or None."""
        if self.root != REAL_SENSOR:
            return None
        if (
            not (REAL_SENSOR / "data").is_dir()
            or not (self.path / "table.parquet").is_file()
        ):
            return (
                "The UCI HAR data is not retrieved on this machine. Run "
                f"`{RETRIEVE_COMMAND}` (it downloads, verifies and builds the table), then "
                "reload."
            )
        return None


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
    Fixture(
        "har_flawed",
        "UCI HAR, real data: random row folds and global fitting (deliberately wrong)",
        root=REAL_SENSOR,
        display="har_flawed (ATLAS-authored flawed variant)",
        notes=(HAR_UPSTREAM,),
        compare_with="har_clean",
    ),
    Fixture(
        "har_clean",
        "UCI HAR, real data: subject-grouped folds, all fitting inside each fold",
        root=REAL_SENSOR,
        notes=(HAR_UPSTREAM,),
        compare_with="har_flawed",
    ),
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
