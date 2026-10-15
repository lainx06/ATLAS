"""Candidate snapshot, diff validation, hashing and approval (SPEC §9). Offline."""

import difflib
import json
import shutil
from pathlib import Path

import pytest

from atlas.candidates import (
    MAX_DIFF_BYTES,
    CandidateRejected,
    SnapshotError,
    approve,
    build_snapshot,
    candidate_hash,
    inventory_hash,
    safe_relpath,
    sha256_bytes,
    validate_diff,
)

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "benchmarks" / "t01" / "s02_clean"
NO_ADAPTER = ROOT / "benchmarks" / "t01" / "s08b_no_adapter"


@pytest.fixture
def snap(tmp_path):
    return build_snapshot(CLEAN, tmp_path / "snapshot")


def entry_text(snap) -> str:
    return (snap.root / snap.entry_point).read_text(encoding="utf-8")


def make_diff(old: str, new: str, path: str = "evaluate.py") -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}"
        )
    )


def copy_project(tmp_path: Path, **manifest_changes) -> Path:
    project = tmp_path / "project"
    shutil.copytree(CLEAN, project)
    if manifest_changes:
        path = project / "atlas_manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, value in manifest_changes.items():
            if key == "table_path":
                data["table"]["path"] = value
            else:
                data[key] = value
        path.write_text(json.dumps(data), encoding="utf-8")
    return project


# --- snapshot -----------------------------------------------------------------------------


def test_snapshot_holds_only_the_three_permitted_inputs(snap):
    files = sorted(p.relative_to(snap.root).as_posix() for p in snap.root.rglob("*"))
    assert files == ["atlas_manifest.json", "evaluate.py", "table.csv"]
    assert [rel for rel, _ in snap.inventory] == files
    assert snap.base_hash == inventory_hash(snap.inventory)
    assert b"\r\n" not in (snap.root / "evaluate.py").read_bytes()
    assert (snap.root / "table.csv").read_bytes() == (CLEAN / "table.csv").read_bytes()


def test_snapshot_ignores_extra_project_files(tmp_path):
    project = copy_project(tmp_path)
    (project / ".env").write_text("NEBIUS_API_KEY=not-a-real-key\n", encoding="utf-8")
    (project / "helper.py").write_text("x = 1\n", encoding="utf-8")
    snap = build_snapshot(project, tmp_path / "snapshot")
    assert sorted(p.name for p in snap.root.iterdir()) == [
        "atlas_manifest.json",
        "evaluate.py",
        "table.csv",
    ]


def test_snapshot_hash_is_deterministic(tmp_path):
    a = build_snapshot(CLEAN, tmp_path / "a")
    b = build_snapshot(CLEAN, tmp_path / "b")
    assert a.base_hash == b.base_hash


def test_unsupported_project_is_refused(tmp_path):
    with pytest.raises(SnapshotError, match="not supported"):
        build_snapshot(NO_ADAPTER, tmp_path / "snapshot")


@pytest.mark.parametrize("bad", ["../table.csv", "/etc/passwd", "C:/x.csv", "a\\b.csv"])
def test_table_path_escape_is_refused(tmp_path, bad):
    project = copy_project(tmp_path, table_path=bad)
    with pytest.raises(SnapshotError):
        build_snapshot(project, tmp_path / "snapshot")


def test_symlinked_input_is_refused(tmp_path):
    project = copy_project(tmp_path)
    outside = tmp_path / "outside.csv"
    shutil.copy(project / "table.csv", outside)
    (project / "table.csv").unlink()
    try:
        (project / "table.csv").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation not permitted on this host")
    with pytest.raises(SnapshotError, match="symlink"):
        build_snapshot(project, tmp_path / "snapshot")


def test_input_behind_a_directory_junction_is_refused(tmp_path):
    """Windows reparse points (junctions need no privilege) are refused like symlinks."""
    import os
    import subprocess

    if os.name != "nt":
        pytest.skip("directory junctions are Windows-only")
    project = copy_project(tmp_path, table_path="data/table.csv")
    outside = tmp_path / "outside"
    outside.mkdir()
    shutil.copy(project / "table.csv", outside / "table.csv")
    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(project / "data"), str(outside)],
        capture_output=True,
        check=False,
    )
    assert made.returncode == 0, made.stderr
    with pytest.raises(SnapshotError, match="symlink or reparse point"):
        build_snapshot(project, tmp_path / "snapshot")


def test_existing_destination_is_refused(tmp_path):
    (tmp_path / "snapshot").mkdir()
    with pytest.raises(FileExistsError):
        build_snapshot(CLEAN, tmp_path / "snapshot")


@pytest.mark.parametrize(
    "path",
    ["", ".", "a/../b", "/abs", "a//b", "con", "lpt1.txt", "a/b. ", "x:y", "a\\b"],
)
def test_safe_relpath_rejects(path):
    with pytest.raises(SnapshotError):
        safe_relpath(path)


def test_safe_relpath_accepts_normal_paths():
    assert safe_relpath("predictions/fold0.parquet") == "predictions/fold0.parquet"


# --- diff validation ------------------------------------------------------------------------


def test_valid_diff_yields_candidate(snap):
    old = entry_text(snap)
    new = old.replace("k=3", "k=2")
    cand = validate_diff(snap, make_diff(old, new))
    assert cand.entry_bytes == new.encode()
    assert cand.entry_point == "evaluate.py"


def test_git_style_preamble_and_no_newline_marker(snap):
    old = entry_text(snap)
    new = old + "# trailing comment without newline"
    diff = "diff --git a/evaluate.py b/evaluate.py\nindex 1234567..89abcde 100644\n"
    diff += make_diff(old, new)
    if not diff.endswith("\n"):
        diff += "\n\\ No newline at end of file\n"
    cand = validate_diff(snap, diff)
    assert cand.entry_bytes == new.encode()


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("table.csv", "path_not_allowed"),
        ("atlas_manifest.json", "path_not_allowed"),
        ("../src/atlas/policy.py", "path_escape"),
        ("src/atlas/audit.py", "path_not_allowed"),
        ("/etc/passwd", "path_escape"),
        ("labels/holdout.csv", "path_not_allowed"),
    ],
)
def test_diff_to_any_other_path_is_refused(snap, path, code):
    diff = make_diff("a\n", "b\n", path)
    with pytest.raises(CandidateRejected) as exc:
        validate_diff(snap, diff)
    assert exc.value.code == code


@pytest.mark.parametrize(
    ("diff", "code"),
    [
        (
            "--- /dev/null\n+++ b/evaluate.py\n@@ -0,0 +1 @@\n+x = 1\n",
            "file_created_or_deleted",
        ),
        (
            "--- a/evaluate.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n",
            "file_created_or_deleted",
        ),
        (
            "diff --git a/evaluate.py b/new.py\nrename from evaluate.py\nrename to new.py\n",
            "forbidden_change",
        ),
        (
            "diff --git a/evaluate.py b/evaluate.py\nold mode 100644\nnew mode 100755\n",
            "forbidden_change",
        ),
        ("diff --git a/x b/x\nnew file mode 120000\n", "forbidden_change"),
        ("Binary files a/evaluate.py and b/evaluate.py differ\n", "forbidden_change"),
        ("GIT binary patch\nliteral 0\n", "forbidden_change"),
        ("", "multiple_or_missing_files"),
        (
            "garbage\n--- a/evaluate.py\n+++ b/evaluate.py\n@@ -1 +1 @@\n-a\n+b\n",
            "malformed_diff",
        ),
    ],
)
def test_structural_diff_rejections(snap, diff, code):
    with pytest.raises(CandidateRejected) as exc:
        validate_diff(snap, diff)
    assert exc.value.code == code


def test_two_files_in_one_diff_is_refused(snap):
    old = entry_text(snap)
    diff = make_diff(old, old + "# x\n") + make_diff(old, old + "# y\n")
    with pytest.raises(CandidateRejected) as exc:
        validate_diff(snap, diff)
    assert exc.value.code == "multiple_or_missing_files"


def test_oversized_diff_is_refused(snap):
    old = entry_text(snap)
    new = old + "".join(f"# {'x' * 70} {i}\n" for i in range(1000))
    diff = make_diff(old, new)
    assert len(diff.encode()) > MAX_DIFF_BYTES
    with pytest.raises(CandidateRejected) as exc:
        validate_diff(snap, diff)
    assert exc.value.code == "too_large"


def test_context_mismatch_is_refused(snap):
    diff = make_diff("not the file\n", "changed\n")
    with pytest.raises(CandidateRejected) as exc:
        validate_diff(snap, diff)
    assert exc.value.code == "does_not_apply"


def test_hunk_count_mismatch_is_refused(snap):
    old = entry_text(snap)
    diff = make_diff(old, old.replace("k=3", "k=2")).replace("@@ -", "@@ -9", 1)
    with pytest.raises(CandidateRejected):
        validate_diff(snap, diff)


def test_syntax_error_is_refused(snap):
    old = entry_text(snap)
    with pytest.raises(CandidateRejected) as exc:
        validate_diff(snap, make_diff(old, old + "def broken(:\n"))
    assert exc.value.code == "syntax_error"


def test_no_change_and_carriage_returns_are_refused(snap):
    old = entry_text(snap)
    with pytest.raises(CandidateRejected) as exc:
        validate_diff(
            snap, make_diff(old, old.replace("k=3", "k=2")).replace("k=2", "k=3")
        )
    assert exc.value.code in {"no_change", "does_not_apply"}
    with pytest.raises(CandidateRejected) as exc:
        validate_diff(snap, make_diff(old, old + "# x\n").replace("\n", "\r\n"))
    assert exc.value.code == "malformed_diff"


# --- hashing and approval -------------------------------------------------------------------


def test_candidate_hash_binds_base_and_bytes(snap):
    old = entry_text(snap)
    cand = validate_diff(snap, make_diff(old, old + "# x\n"))
    expected = sha256_bytes(bytes.fromhex(snap.base_hash) + cand.entry_bytes)
    assert candidate_hash(snap.base_hash, cand.entry_bytes) == expected
    approval = approve(snap, cand, approved_at="2026-10-14T00:00:00+00:00")
    assert approval.to_dict() == {
        "candidate_hash": expected,
        "base_snapshot_hash": snap.base_hash,
        "approved_at": "2026-10-14T00:00:00+00:00",
    }
    assert candidate_hash(snap.base_hash, cand.entry_bytes + b" ") != expected
    other_base = "0" * 64
    assert candidate_hash(other_base, cand.entry_bytes) != expected
