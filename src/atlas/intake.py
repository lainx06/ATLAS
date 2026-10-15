"""Project intake: manifest validation and the run-level supportedness decision (SPEC §3)."""

import ast
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from atlas import tables
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
    return source_uses_adapter(entry.read_text(encoding="utf-8"), str(entry))


def source_uses_adapter(source: str, filename: str) -> bool:
    """`uses_adapter` on source already in memory (the candidate snapshot reads it bounded)."""
    tree = ast.parse(source, filename=filename)
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
        return Intake(False, validation_reason(exc), None)
    reason = manifest_reason(manifest)
    if reason is not None:
        return Intake(False, reason, manifest)
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


def validation_reason(exc: ValidationError, limit: int = 5) -> str:
    """'manifest unparseable', naming the failing fields (SPEC §3). Input values are not echoed."""
    parts = [
        f"{'.'.join(map(str, e['loc'])) or '<manifest>'}: {e['msg']}"
        for e in exc.errors(include_input=False)[:limit]
    ]
    more = exc.error_count() - len(parts)
    detail = "; ".join(parts) + (f"; and {more} more" if more > 0 else "")
    return f"manifest unparseable: {exc.error_count()} validation error(s): {detail}"


def manifest_reason(manifest: Manifest) -> str | None:
    """Why a validated manifest alone makes the project unsupported, or None."""
    if not supported_claim(manifest.claim.type):
        return f"claim type {manifest.claim.type!r} is not supported in V1 (combined or unknown)"
    if len(manifest.columns.class_map) < 2:
        return "task is not classification (class_map has fewer than two classes)"
    if manifest.table.format not in TABLE_FORMATS:
        return f"table format {manifest.table.format!r} is unsupported"
    return None


def read_table(project: Path, manifest: Manifest) -> pd.DataFrame:
    """The table indexed by string row IDs (used by the candidate session and, separately, the evaluator)."""
    return tables.read_table(
        project / manifest.table.path, manifest.table.format, manifest.columns.row_id
    )
