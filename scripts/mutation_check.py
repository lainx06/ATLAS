"""T-01 mutation check: each mutation must make at least its named scenario test fail.

The repository source is never edited. Each mutation is applied to a temporary copy of
src/atlas that is placed first on PYTHONPATH for pytest and for the fixture child processes.

The copy mirrors the repository layout (<tmp>/src/atlas plus the runner build recipe files at
<tmp>/), because the Docker runner reads its recipe relative to the package
(`runner/docker.py`: REPO_ROOT = parents[3]); a bare <tmp>/atlas copy made every test that
computes the recipe hash fail with FileNotFoundError, unrelated to any mutation. Before the
suite, an origin probe confirms that the copy is what gets imported, by this process's children
and by a trusted-fixture child, and that the runner sees the copied recipe.

Run: uv run --locked python scripts/mutation_check.py
(with ATLAS_REQUIRE_DOCKER=1 so the Docker tests fail instead of skipping)
"""

import json
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
# Output that means a test-resource or package-origin problem, never a mutation effect.
UNRELATED_TEXT = ("Dockerfile.runner", "runner-requirements.txt")
# The runner's build recipe (runner/docker.py BUILD_CONTEXT), copied beside the package copy.
RECIPE_FILES = ("Dockerfile.runner", "docker/runner-requirements.txt")
ORIGIN_PROBE = r"""
import json, sys, tempfile
from pathlib import Path
import atlas
from atlas.runner import docker, trusted
root = Path(sys.argv[1])
out = Path(sys.argv[2])
fixture = root / "benchmarks" / "t01" / "s02_clean"
record = trusted.run_trusted_fixture(fixture, "evaluate.py", out)
runtime = json.loads((out / "runtime.json").read_text(encoding="utf-8"))
print(json.dumps({
    "parent_atlas": str(Path(atlas.__file__).resolve()),
    "runner_package_dir": str(docker.PACKAGE_DIR),
    "runner_repo_root": str(docker.REPO_ROOT),
    "recipe_sha256": docker.recipe_sha256(),
    "fixture_returncode": record["returncode"],
    "child_atlas": str(Path(runtime["atlas_origin"]).resolve()),
}))
"""


def origin_probe(tmp: Path, env: dict, mutation: dict) -> bool:
    """The copy is imported by a child of this script, by its trusted-fixture grandchild, and
    by the Docker runner (package and recipe); the recipe hash equals the repository's."""
    proc = subprocess.run(
        [sys.executable, "-c", ORIGIN_PROBE, str(ROOT), str(tmp / "origin-probe")],
        check=False,
        cwd=tmp,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"  origin probe failed (exit {proc.returncode}): {proc.stderr[-600:]}")
        return False
    seen = json.loads(proc.stdout.strip().splitlines()[-1])
    expected = subprocess.run(
        [
            sys.executable,
            "-c",
            "from atlas.runner import docker; print(docker.recipe_sha256())",
        ],
        check=False,
        cwd=ROOT,
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
        capture_output=True,
        text=True,
    ).stdout.strip()
    copy = (tmp / "src" / "atlas").resolve()
    checks = {
        "parent imports the copy": Path(seen["parent_atlas"]).parent == copy,
        "trusted-fixture child imports the copy": Path(seen["child_atlas"]).parent
        == copy,
        "runner mounts the copy": Path(seen["runner_package_dir"]) == copy,
        "runner recipe is the copied recipe": Path(seen["runner_repo_root"])
        == tmp.resolve(),
        "recipe hash equals the repository's": seen["recipe_sha256"] == expected,
        "fixture child completed": seen["fixture_returncode"] == 0,
    }
    if mutation["old"] is not None:
        child_file = Path(seen["child_atlas"]).parent / mutation["file"]
        checks["child's package holds the mutation"] = mutation[
            "new"
        ] in child_file.read_text(encoding="utf-8")
    for name, ok in checks.items():
        print(f"  origin: {name}: {'yes' if ok else 'NO'}")
    print(f"  origin: child atlas {seen['child_atlas']}")
    return all(checks.values())


def run(mutation: dict) -> bool:
    with tempfile.TemporaryDirectory(prefix=f"atlas-{mutation['id']}-") as tmp:
        tmp_root = Path(tmp)
        src = tmp_root / "src"
        pkg = src / "atlas"
        shutil.copytree(
            ROOT / "src" / "atlas", pkg, ignore=shutil.ignore_patterns("__pycache__")
        )
        for rel in RECIPE_FILES:
            (tmp_root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, tmp_root / rel)
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
            "PYTHONPATH": str(src) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        }
        print(f"{mutation['id']}: {mutation['what']}")
        if not origin_probe(tmp_root, env, mutation):
            print("  origin probe failed: the result would not test the copy")
            return False
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
                "-rfE",
                # Temporary writes stay inside this run's temporary directory.
                "--basetemp",
                str(tmp_root / "bt"),
            ],
            check=False,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
    failed = re.findall(r"^FAILED (\S+)", proc.stdout, flags=re.MULTILINE)
    errors = re.findall(r"^ERROR (\S+)", proc.stdout, flags=re.MULTILINE)
    unrelated = [f for f in failed + errors if any(u in f for u in UNRELATED)]
    unrelated += [
        f"output mentions {t}"
        for t in UNRELATED_TEXT
        if t in proc.stdout or t in proc.stderr
    ]
    summary = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    print(f"  mutated package imported from: {where}")
    print(f"  pytest exit {proc.returncode}; {summary}")
    print(f"  {len(failed)} failing test(s), {len(errors)} error(s)")
    for f in failed:
        print(f"    FAILED {f}")
    for e in errors:
        print(f"    ERROR {e}")
    if not where.startswith(str(src)):
        print("  the copy was not imported: result invalid")
        return False
    if mutation["old"] is None:
        ok = proc.returncode == 0 and not failed and not errors and not unrelated
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
