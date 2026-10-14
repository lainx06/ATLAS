"""Project intake: manifest validation and the run-level supportedness decision (SPEC §3)."""

import ast
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from atlas.contracts import Manifest
from atlas.policy import supported_claim

MANIFEST_NAME = "atlas_manifest.json"
TABLE_FORMATS = ("csv", "parquet")


@dataclass
class Intake:
    supported: bool
    reason: str | None
    manifest: Manifest | None


def uses_adapter(entry: Path) -> bool:
    """Static check: does the entry point import the ATLAS adapter at all?"""
    tree = ast.parse(entry.read_text(encoding="utf-8"), filename=str(entry))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            a.name == "atlas" or a.name.startswith("atlas.") for a in node.names
        ):
            return True
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == "atlas" or node.module.startswith("atlas."))
        ):
            return True
    return False


def load_project(project: Path) -> Intake:
    path = project / MANIFEST_NAME
    if not path.exists():
        return Intake(False, "manifest absent", None)
    try:
        manifest = Manifest.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        return Intake(
            False,
            f"manifest unparseable: {exc.error_count()} validation error(s)",
            None,
        )
    if not supported_claim(manifest.claim.type):
        return Intake(
            False,
            f"claim type {manifest.claim.type!r} is not supported in V1 (combined or unknown)",
            manifest,
        )
    if len(manifest.columns.class_map) < 2:
        return Intake(
            False,
            "task is not classification (class_map has fewer than two classes)",
            manifest,
        )
    if manifest.table.format not in TABLE_FORMATS:
        return Intake(
            False, f"table format {manifest.table.format!r} is unsupported", manifest
        )
    if not (project / manifest.table.path).exists():
        return Intake(False, "table absent", manifest)
    entry = project / manifest.entry_point
    if not entry.exists():
        return Intake(False, "entry point absent", manifest)
    if not uses_adapter(entry):
        return Intake(
            False,
            "entry point does not use the ATLAS adapter (static suspicions only; no static analyzer is implemented in T-01)",
            manifest,
        )
    return Intake(True, None, manifest)


def read_table(project: Path, manifest: Manifest) -> pd.DataFrame:
    """The table indexed by string row IDs (used by the candidate session and, separately, the evaluator)."""
    path = project / manifest.table.path
    row_id = manifest.columns.row_id
    if manifest.table.format == "csv":
        table = pd.read_csv(path, dtype={row_id: str})
    else:
        table = pd.read_parquet(path)
        table[row_id] = table[row_id].astype(str)
    table = table.set_index(row_id)
    if not table.index.is_unique:
        raise ValueError("row_id values are not unique")
    return table
