"""Copy finished runs into the hosted demo bundle, byte for byte (T-12 step 3).

    uv run --locked python scripts/build_recorded_bundle.py SOURCE=DEST [SOURCE=DEST ...]

Each SOURCE run directory is copied (never moved) to `demo/recorded/DEST`, and every copied
file is re-read and compared with its source. Nothing is rewritten: the recorded-run viewer
recomputes the hashes the run recorded, so a single changed byte would show "evidence changed
since recording".

One kind of file is left out on purpose: the UCI HAR feature table (`table.parquet`, the
project's data). The hosted demo shows precomputed HAR results only and does not redistribute
the dataset (DECISIONS.md "T-12 decisions (user, 2026-10-18)", item 1). The viewer does not
verify the table (it is not among the recorded evidence hashes), so the copies stay intact.
Each left-out file is listed in BUNDLE.json with its size and SHA-256.

BUNDLE.json records, for each run, where it came from and the SHA-256 of every bundled file;
`scripts/check_recorded.py` re-checks the bundle against it and scans it for publication.
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "demo" / "recorded"
MANIFEST = "BUNDLE.json"
EXCLUDED_NAMES = {"table.parquet"}  # the UCI HAR feature table (T-12 decision 1)
EXCLUDED_REASON = (
    "UCI HAR feature table (dataset content): not redistributed by the hosted demo "
    "(T-12 decision 1); the viewer does not verify it"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_run(source: Path, dest_rel: str) -> dict:
    dest = BUNDLE / dest_rel
    if dest.exists():
        raise SystemExit(f"{dest} exists; remove it first (nothing is overwritten)")
    files, excluded = {}, []
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = path.relative_to(source).as_posix()
        if path.name in EXCLUDED_NAMES:
            excluded.append(
                {
                    "path": rel,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "reason": EXCLUDED_REASON,
                }
            )
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        digest = sha256(path)
        if sha256(target) != digest or target.read_bytes() != path.read_bytes():
            raise SystemExit(f"copy of {rel} differs from its source")
        files[rel] = digest
    report = json.loads((source / "agent_report.json").read_text(encoding="utf-8"))
    return {
        "path": dest_rel,
        "source_name": source.name,
        "mode": report.get("mode"),
        "live": report.get("live"),
        "terminal_state": report.get("terminal_state"),
        "original_outcome": (report.get("scientific_outcomes") or {}).get("original"),
        "finished_utc": (report.get("states") or [{}])[-1].get("time_utc"),
        "files": files,
        "excluded": excluded,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="build_recorded_bundle")
    p.add_argument(
        "pairs", nargs="+", help="SOURCE=DEST (DEST relative to demo/recorded)"
    )
    args = p.parse_args(argv)
    manifest_path = BUNDLE / MANIFEST
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {"bundle": "atlas-hosted-recorded-runs", "runs": []}
    )
    for pair in args.pairs:
        source, _, dest = pair.partition("=")
        if not dest:
            raise SystemExit(f"expected SOURCE=DEST, got {pair!r}")
        entry = copy_run(Path(source), dest)
        manifest["runs"] = [r for r in manifest["runs"] if r["path"] != dest] + [entry]
        print(
            f"{dest}: {len(entry['files'])} files copied byte-exact, "
            f"{len(entry['excluded'])} excluded"
        )
    BUNDLE.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
