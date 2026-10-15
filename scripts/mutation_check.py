"""T-01 mutation check: each mutation must make at least its named scenario test fail.

The repository source is never edited. Each mutation is applied to a temporary copy of
src/atlas that is placed first on PYTHONPATH for pytest and for the fixture child processes.

Run: uv run --locked python scripts/mutation_check.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUTATIONS = [
    {
        "id": "m1",
        "what": "state-dependency check uses the fold where a state was fitted instead of where it was used",
        "file": "checks/fit_provenance.py",
        "old": 'check_fold = use["fold"]  # the fold where the state is USED (F1)',
        "new": 'check_fold = use["state_fit_fold"]  # MUTATION m1',
        # Scenario 5a still FAILs under m1 because the classifier is refit in the use fold on the
        # reused selector's output, so the dependency propagates. This test isolates the rule.
        "must_fail": "test_whole_model_fitted_in_one_fold_and_reused_to_predict_another_fails",
    },
    {
        "id": "m2",
        "what": "group/unit overlap compares row IDs instead of group IDs",
        "file": "checks/split_integrity.py",
        "old": "overlap = _overlap_by(column, table, splits)  # compares unit values, never row IDs",
        "new": "overlap = _row_overlap_by_fold(splits)  # MUTATION m2",
        "must_fail": "s01_faulty",
    },
    {
        "id": "m3",
        "what": "a valid index on an untracked frame is accepted as ancestry",
        "file": "recorder.py",
        "old": "known = False  # untracked: a valid index is identity, not ancestry",
        "new": "known = True  # MUTATION m3",
        "must_fail": "s03a_rebuilt_frame",
    },
]


# A failure here under a mutation would be unrelated to the mutation (the origin test must
# accept the intended temporary package root).
UNRELATED = (
    "test_fixture_child_imports_atlas_from_the_trusted_package_not_the_fixture",
)


def run(mutation: dict) -> bool:
    with tempfile.TemporaryDirectory(prefix=f"atlas-{mutation['id']}-") as tmp:
        pkg = Path(tmp) / "atlas"
        shutil.copytree(
            ROOT / "src" / "atlas", pkg, ignore=shutil.ignore_patterns("__pycache__")
        )
        if mutation["old"] is not None:
            target = pkg / mutation["file"]
            source = target.read_text(encoding="utf-8")
            if source.count(mutation["old"]) != 1:
                print(
                    f"{mutation['id']}: mutation target not found exactly once; check is invalid"
                )
                return False
            target.write_text(
                source.replace(mutation["old"], mutation["new"]), encoding="utf-8"
            )
        env = {
            **os.environ,
            "PYTHONPATH": tmp + os.pathsep + os.environ.get("PYTHONPATH", ""),
        }
        where = subprocess.run(
            [sys.executable, "-c", "import atlas; print(atlas.__file__)"],
            check=False,
            env=env,
            capture_output=True,
            text=True,
        ).stdout.strip()
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests",
                "-q",
                "-rf",
                "-p",
                "no:cacheprovider",
                "-W",
                "ignore::UserWarning",
            ],
            check=False,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
    failed = re.findall(r"^FAILED (\S+)", proc.stdout, flags=re.MULTILINE)
    unrelated = [f for f in failed if any(u in f for u in UNRELATED)]
    print(f"{mutation['id']}: {mutation['what']}")
    print(f"  mutated package imported from: {where}")
    print(f"  pytest exit {proc.returncode}; {len(failed)} failing test(s)")
    for f in failed:
        print(f"    FAILED {f}")
    if mutation["old"] is None:
        ok = proc.returncode == 0 and not failed
        print(
            f"  unmutated temporary copy: {'ALL PASS' if ok else 'FAILURES (baseline invalid)'}"
        )
        return ok
    caught = proc.returncode != 0 and any(mutation["must_fail"] in f for f in failed)
    print(
        f"  expected failing test: {mutation['must_fail']} -> {'CAUGHT' if caught else 'NOT CAUGHT'}"
    )
    print(f"  unrelated runtime-origin failures: {unrelated or 'none'}")
    return caught and not unrelated


BASELINE = {
    "id": "baseline",
    "what": "unmutated temporary copy (must pass the full suite)",
    "old": None,
}


def main() -> int:
    if not run(BASELINE):
        print("baseline failed: mutation results would be meaningless")
        return 1
    results = [run(m) for m in MUTATIONS]
    print(f"mutations caught cleanly: {sum(results)}/{len(results)}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
