"""Trusted-fixture runner (SPEC §10, fixture rule).

Only repo-authored, reviewed fixtures whose complete file inventory matches an allowlist entry may
run, in a host subprocess. Candidate or generated code never runs here.

Import resolution is controlled: the child starts in Python isolated mode (`-I`: safe path, no
PYTHON* environment variables, no user site), so neither the fixture directory nor the working
directory is on `sys.path`. The parent's resolved `atlas` package directory is inserted explicitly.

This is NOT a sandbox. A subprocess, isolated mode, timeout, cwd or reduced environment does not
confine code; the runner's capability is reported as `trusted_pipeline_only`.

Regenerate the allowlist only after reviewing fixture changes:
  uv run --locked python -m atlas.runner.trusted allowlist benchmarks/t01
"""

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import atlas

ALLOWLIST_PATH = Path(__file__).with_name("trusted_fixtures.json")
CAPABILITY = "trusted_pipeline_only"
TIMEOUT_S = 30
_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
# Runs as `python -I -c LAUNCHER <atlas_parent> <project> <out_dir>`.
LAUNCHER = (
    "import sys; sys.path.insert(0, sys.argv[1]); "
    "from pathlib import Path; from atlas.runner.bootstrap import main; "
    "main(Path(sys.argv[2]), Path(sys.argv[3]))"
)


class UntrustedFixtureError(RuntimeError):
    pass


def normalized_sha256(path: Path) -> str:
    """Hash with line endings normalized, so a Git checkout's CRLF conversion doesn't change identity."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def fixture_inventory(project: Path) -> list[dict]:
    """Every file in the fixture directory, with its normalized hash. Any extra file changes it."""
    return [
        {
            "path": path.relative_to(project).as_posix(),
            "sha256": normalized_sha256(path),
        }
        for path in sorted(project.rglob("*"))
        if path.is_file()
    ]


def load_allowlist() -> list[dict]:
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))["fixtures"]


def is_trusted(project: Path, entry_point: str) -> bool:
    inventory = fixture_inventory(project)
    if entry_point not in {f["path"] for f in inventory}:
        return False
    return any(entry["inventory"] == inventory for entry in load_allowlist())


def trusted_atlas_parent() -> str:
    """The directory containing the `atlas` package this (trusted) process imported."""
    return str(Path(atlas.__file__).resolve().parent.parent)


def run_trusted_fixture(project: Path, entry_point: str, out_dir: Path) -> dict:
    if not is_trusted(project, entry_point):
        raise UntrustedFixtureError(
            f"{project} is not an allowlisted trusted fixture; refusing to execute"
        )
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(m in k.upper() for m in _SECRET_MARKERS)
    }
    command = [
        sys.executable,
        "-I",
        "-c",
        LAUNCHER,
        trusted_atlas_parent(),
        str(project.resolve()),
        str(Path(out_dir).resolve()),
    ]
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            check=False,
            cwd=project,
            env=env,
            timeout=TIMEOUT_S,
            capture_output=True,
            text=True,
            shell=False,
        )
        returncode, stderr, timed_out = proc.returncode, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        returncode, stderr, timed_out = None, str(exc.stderr or ""), True
    return {
        "runner": "trusted_fixture_host_subprocess",
        "capability": CAPABILITY,
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_s": round(time.monotonic() - started, 3),
        "stderr_tail": stderr[-2000:],
    }


def build_allowlist(root: Path) -> dict:
    entries = [
        {
            "fixture": manifest.parent.name,
            "inventory": fixture_inventory(manifest.parent),
        }
        for manifest in sorted(root.glob("*/atlas_manifest.json"))
    ]
    return {
        "description": "Reviewed trusted fixtures (SPEC §10): complete file inventories, LF-normalized SHA-256.",
        "fixtures": entries,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "allowlist":
        raise SystemExit(
            "usage: python -m atlas.runner.trusted allowlist <fixtures-root>"
        )
    data = build_allowlist(Path(sys.argv[2]))
    ALLOWLIST_PATH.write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {len(data['fixtures'])} entries to {ALLOWLIST_PATH}")
