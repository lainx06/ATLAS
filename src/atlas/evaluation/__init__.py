"""T-11 three-way comparison (re-scoped; DECISIONS.md "T-11 re-scope and T-10 (lead,
2026-10-19)"; protocol `docs/EVALUATION.md`).

Four development cases, three legs: (a) the ATLAS deterministic audit (`suite`), (b) Nemotron
alone reading the same files with no executable checks (`baseline`), and (c) the project's
reported metric against ATLAS's recomputed metric and the clean control (`suite`). Scoring is
`score`. Results are descriptive, and every report states the development-case caveat.

This module loads the predeclared inputs: `evaluation/expected.json` (the canonical violated
assertion IDs per case, fixed before any live trial) and `evaluation/assertion_definitions.json`
(the policy's definitions, verbatim from docs/SPEC.md section 5).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from atlas.candidates import (
    MAX_ENTRY_BYTES,
    MAX_MANIFEST_BYTES,
    _lf,
    _permitted_file,
    safe_relpath,
)
from atlas.contracts import Manifest
from atlas.intake import MANIFEST_NAME
from atlas.policy import POLICY_VERSION, required_assertions

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_PATH = ROOT / "evaluation" / "expected.json"
DEFINITIONS_PATH = ROOT / "evaluation" / "assertion_definitions.json"
CASE_IDS = ("s01_faulty", "s02_clean", "har_flawed", "har_clean")
CAVEAT = (
    "Development cases, not held-out: ATLAS's checks were built and debugged on these four "
    "cases, so ATLAS's results on them are not evidence of generalization. Results are "
    "descriptive."
)


class CaseError(ValueError):
    """A predeclared input is missing or inconsistent; nothing is run."""


@dataclass(frozen=True)
class Case:
    case_id: str
    path: Path
    role: str  # "flawed" or "clean_control"
    clean_control: str | None
    manifest: Manifest
    manifest_text: str  # the file as read, UTF-8
    entry_point: str
    entry_text: str  # LF-normalized, as the snapshot stores it
    canonical: tuple[
        str, ...
    ]  # the required assertions for this claim, in policy order
    expected: frozenset[str]


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CaseError(f"{path.name} unreadable ({type(exc).__name__})") from None
    if not isinstance(data, dict):
        raise CaseError(f"{path.name} is not an object")
    return data


def load_definitions(path: Path = DEFINITIONS_PATH) -> dict[str, str]:
    definitions = _read_json(path).get("definitions")
    if not isinstance(definitions, dict):
        raise CaseError("assertion definitions missing")
    return definitions


def load_expected(path: Path = EXPECTED_PATH) -> dict:
    data = _read_json(path)
    if data.get("policy_version") != POLICY_VERSION:
        raise CaseError("expected.json names another policy version")
    cases = data.get("cases")
    if not isinstance(cases, dict) or tuple(cases) != CASE_IDS:
        raise CaseError("expected.json must list exactly the four cases, in order")
    return data


def load_case(case_id: str, entry: dict, root: Path = ROOT) -> Case:
    """One case, its files read through the same permitted-file reader as the agent's
    `read_project_file` (bounded, no links), and its expected set checked against the
    canonical IDs of its own claim."""
    project = root / safe_relpath(entry["path"])
    raw = _permitted_file(project, MANIFEST_NAME, MAX_MANIFEST_BYTES)
    manifest = Manifest.model_validate_json(raw)
    entry_point = safe_relpath(manifest.entry_point)
    entry_text = _lf(
        _permitted_file(project, entry_point, MAX_ENTRY_BYTES), "entry point"
    ).decode("utf-8")
    canonical = tuple(required_assertions(manifest))
    expected = [e["assertion_id"] for e in entry["expected_violated"]]
    if len(set(expected)) != len(expected) or not set(expected) <= set(canonical):
        raise CaseError(f"{case_id}: expected IDs must be distinct canonical IDs")
    for e in entry["expected_violated"]:
        if not e.get("sources"):
            raise CaseError(f"{case_id}: {e['assertion_id']} has no source")
    if not expected and not entry.get("empty_set_sources"):
        raise CaseError(f"{case_id}: the empty expected set has no source")
    return Case(
        case_id=case_id,
        path=project,
        role=entry["role"],
        clean_control=entry.get("clean_control"),
        manifest=manifest,
        manifest_text=raw.decode("utf-8"),
        entry_point=entry_point,
        entry_text=entry_text,
        canonical=canonical,
        expected=frozenset(expected),
    )


def load_cases(expected_path: Path = EXPECTED_PATH, root: Path = ROOT) -> list[Case]:
    data = load_expected(expected_path)
    return [load_case(cid, entry, root) for cid, entry in data["cases"].items()]
