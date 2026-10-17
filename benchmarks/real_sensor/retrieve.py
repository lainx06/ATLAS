"""Retrieve and verify UCI HAR (dataset 240), then build the two T-09 project tables.

    uv run --locked python benchmarks/real_sensor/retrieve.py            # download or verify
    uv run --locked python benchmarks/real_sensor/retrieve.py --record   # first run only

Source: https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones
(CC BY 4.0; see ATTRIBUTION.md). Nothing downloaded here is committed:

- the archive and the extracted files go to `benchmarks/real_sensor/data/` (git-ignored);
- each project's `table.parquet` is built from the **training partition only** and is
  git-ignored too.

`checksums.json` (committed) records the SHA-256 of the archive, of the inner archive, of
every extracted file and of each built table. `--record` writes it once, from a first
download. Every later run recomputes all of them and **fails closed** (exit 1, nothing
written) on any difference: a changed upstream archive is never silently accepted.

Only the named members are extracted, by exact name (no path from the archive is trusted).
The official test partition (`test/`) is extracted and hashed so its identity is recorded,
but no project table contains a test row: it stays reserved (SPEC §17, F4).
"""

import argparse
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CHECKSUMS = HERE / "checksums.json"
URL = (
    "https://archive.ics.uci.edu/static/public/240/"
    "human+activity+recognition+using+smartphones.zip"
)
ARCHIVE = DATA / "human+activity+recognition+using+smartphones.zip"
INNER = "UCI HAR Dataset.zip"
ROOT = "UCI HAR Dataset/"
MEMBERS = (
    "README.txt",
    "features_info.txt",
    "features.txt",
    "activity_labels.txt",
    "train/X_train.txt",
    "train/y_train.txt",
    "train/subject_train.txt",
    "test/X_test.txt",
    "test/y_test.txt",
    "test/subject_test.txt",
)
PROJECTS = ("har_flawed", "har_clean")
TIMEOUT_S = 120


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download() -> bytes:
    with urllib.request.urlopen(URL, timeout=TIMEOUT_S) as r:  # a fixed https URL
        if r.status != 200:
            raise RuntimeError(f"download failed: HTTP {r.status}")
        return r.read()


def extract(archive: bytes) -> tuple[bytes, dict[str, bytes]]:
    """The inner archive's bytes and the named members' bytes, by exact name."""
    with zipfile.ZipFile(io.BytesIO(archive)) as outer:
        inner = outer.read(INNER)
    files = {}
    with zipfile.ZipFile(io.BytesIO(inner)) as z:
        names = set(z.namelist())
        for m in MEMBERS:
            if ROOT + m not in names:
                raise RuntimeError(f"member missing from the archive: {ROOT + m}")
            files[m] = z.read(ROOT + m)
    return inner, files


def feature_names(features_txt: bytes) -> list[str]:
    """`features.txt` lines are '<index> <name>'. Names are not unique upstream, so each column
    is named by its 1-based index plus the original name: f001_tBodyAcc-mean()-X, ..."""
    names = []
    for line in features_txt.decode("ascii").splitlines():
        if line.strip():
            idx, name = line.split(" ", 1)
            names.append(f"f{int(idx):03d}_{name.strip()}")
    if len(names) != len(set(names)) or len(names) != 561:
        raise RuntimeError("unexpected feature list")
    return names


def build_table(files: dict[str, bytes]) -> bytes:
    """The training partition as one Parquet table: row_id, subject_id, the 561 features and
    the activity label (1-6). Rows keep the upstream order."""
    import numpy as np
    import pandas as pd

    names = feature_names(files["features.txt"])
    X = np.loadtxt(io.BytesIO(files["train/X_train.txt"]), dtype=np.float64)
    y = np.loadtxt(io.BytesIO(files["train/y_train.txt"]), dtype=np.int64)
    subject = np.loadtxt(io.BytesIO(files["train/subject_train.txt"]), dtype=np.int64)
    if X.shape != (len(y), len(names)) or len(subject) != len(y):
        raise RuntimeError(f"unexpected training shapes {X.shape}, {y.shape}")
    table = pd.DataFrame(X, columns=names)
    table.insert(0, "subject_id", [f"S{s:02d}" for s in subject])
    table.insert(0, "row_id", [f"w{i:05d}" for i in range(len(y))])
    table["activity"] = y.astype(str)
    buf = io.BytesIO()
    table.to_parquet(buf, index=False, engine="pyarrow", compression="zstd")
    return buf.getvalue()


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--record", action="store_true", help="write checksums.json (first run)"
    )
    args = p.parse_args(argv)
    if args.record == CHECKSUMS.exists():
        print("--record is only for the first run" if CHECKSUMS.exists() else
              "checksums.json is missing: run once with --record")  # fmt: skip
        return 1
    expected = (
        None if args.record else json.loads(CHECKSUMS.read_text(encoding="utf-8"))
    )

    DATA.mkdir(exist_ok=True)
    if ARCHIVE.exists():
        archive = ARCHIVE.read_bytes()
    else:
        archive = download()
    inner, files = extract(archive)
    tables = {name: build_table(files) for name in PROJECTS}
    observed = {
        "source": URL,
        "archive": {
            "name": ARCHIVE.name,
            "bytes": len(archive),
            "sha256": sha256(archive),
        },
        "inner_archive": {"name": INNER, "sha256": sha256(inner)},
        "files": {m: sha256(b) for m, b in sorted(files.items())},
        "tables": {f"{n}/table.parquet": sha256(t) for n, t in sorted(tables.items())},
    }
    if expected is not None:
        problems = [
            f"{section}: expected {expected.get(section)!r}, found {observed[section]!r}"
            for section in observed
            if observed[section] != expected.get(section)
        ]
        if problems:
            print("VERIFICATION FAILED; nothing written:\n  " + "\n  ".join(problems))
            return 1
    if not ARCHIVE.exists():
        ARCHIVE.write_bytes(archive)
    for m, b in files.items():
        target = DATA / "UCI HAR Dataset" / m
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b)
    for name, data in tables.items():
        (HERE / name / "table.parquet").write_bytes(data)
    if args.record:
        CHECKSUMS.write_text(json.dumps(observed, indent=2) + "\n", encoding="utf-8")
        print(f"recorded {CHECKSUMS.name}")
    print(f"archive sha256 {observed['archive']['sha256']} ({len(archive)} bytes)")
    for k, v in observed["tables"].items():
        print(f"{k} sha256 {v}")
    print("verified" if expected is not None else "first run recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
