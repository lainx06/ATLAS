"""Evidence files: hashing, verified loading, and JSON outputs (SPEC §7)."""

import hashlib
import json
from importlib import metadata
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids_sha256(ids) -> str:
    """Order-sensitive hash of a row-ID list (adapter and trusted evaluator)."""
    return hashlib.sha256("\n".join(map(str, ids)).encode("utf-8")).hexdigest()


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def verified(run_dir: Path, index: dict, name: str) -> tuple[Path, str | None, bool]:
    """(path, recorded hash, valid): valid only if the file exists and matches the index hash."""
    path = run_dir / name
    recorded = index["artifacts"].get(name)
    valid = recorded is not None and path.exists() and sha256_file(path) == recorded
    return path, recorded, valid


def versions() -> dict:
    out = {}
    for dist in ("atlas", "scikit-learn", "pandas", "numpy", "pydantic"):
        try:
            out[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            out[dist] = None
    return out
