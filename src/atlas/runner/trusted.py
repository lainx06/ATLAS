"""Trusted-fixture runner (SPEC §10, fixture rule).

Only repo-authored, reviewed fixtures whose entry point and manifest hashes are on the allowlist
may run, in a host subprocess. Candidate or generated code never runs here. A subprocess,
timeout, cwd or reduced environment is not a sandbox; this runner provides no isolation and its
capability is reported as `trusted_pipeline_only`.

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

ALLOWLIST_PATH = Path(__file__).with_name("trusted_fixtures.json")
CAPABILITY = "trusted_pipeline_only"
TIMEOUT_S = 30
_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


class UntrustedFixtureError(RuntimeError):
    pass


def normalized_sha256(path: Path) -> str:
    """Hash with line endings normalized, so a Git checkout's CRLF conversion doesn't change identity."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def fixture_key(project: Path, entry_point: str) -> dict:
    return {
        "entry_sha256": normalized_sha256(project / entry_point),
        "manifest_sha256": normalized_sha256(project / "atlas_manifest.json"),
    }


def load_allowlist() -> list[dict]:
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))["fixtures"]


def is_trusted(project: Path, entry_point: str) -> bool:
    key = fixture_key(project, entry_point)
    return any(
        e["entry_sha256"] == key["entry_sha256"]
        and e["manifest_sha256"] == key["manifest_sha256"]
        for e in load_allowlist()
    )


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
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "atlas.runner.bootstrap",
                str(project.resolve()),
                str(Path(out_dir).resolve()),
            ],
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
    entries = []
    for manifest in sorted(root.glob("*/atlas_manifest.json")):
        project = manifest.parent
        entries.append({"fixture": project.name, **fixture_key(project, "evaluate.py")})
    return {
        "description": "Reviewed trusted fixtures (SPEC §10). Content hashes, LF-normalized.",
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
