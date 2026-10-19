"""T-12 step 3: the bundled recorded runs and the publication check (offline).

The viewer verifies all three bundled runs; a one-byte change anywhere it checks shows
"evidence changed since recording". `scripts/check_recorded.py` reports (never rewrites)
host paths, user names, e-mails, key-shaped strings and .env references.
"""

import importlib.util
import json
import shutil
import subprocess

import hosted_helpers as H
import pytest

from atlas.hosted import bundle
from atlas.ui import artifacts as A
from atlas.ui import recorded as RR

spec = importlib.util.spec_from_file_location(
    "check_recorded", H.ROOT / "scripts" / "check_recorded.py"
)
CR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CR)
RUNS = [
    "live6/agent-s01_faulty-877f8245a8a2",
    "t09/agent-har_flawed-1e2267f662c0",
    "t09/agent-har_clean-ac63eaecd7a8",
]


def test_the_bundle_lists_exactly_the_three_runs():
    assert [r.label for r in bundle.list_bundle()] == RUNS
    manifest = bundle.load_manifest()
    assert [r["path"] for r in manifest["runs"]] == RUNS
    assert [r["original_outcome"] for r in manifest["runs"]] == [
        "VIOLATION_FOUND", "VIOLATION_FOUND", "NO_VIOLATION_FOUND",
    ]  # fmt: skip


@pytest.mark.parametrize("label", RUNS)
def test_the_viewer_verifies_each_bundled_run(label):
    run = next(r for r in bundle.list_bundle() if r.label == label)
    checks = RR.verify(run.path, A.read_json(run.path / "agent_report.json"))
    assert checks and RR.intact(checks)


@pytest.mark.parametrize(
    ("label", "rel"),
    [
        (RUNS[0], "original/outcome.json"),
        (RUNS[0], "agent_log.jsonl"),
        (RUNS[0], "replies/a3.txt"),
        (RUNS[0], "candidates/c1/predictions/fold2.parquet"),
        (RUNS[1], "original/checks/split_integrity.json"),
        (RUNS[2], "original/predictions/fold0.parquet"),
    ],
)
def test_a_one_byte_change_shows_evidence_changed(tmp_path, label, rel):
    copy = tmp_path / "run"
    shutil.copytree(H.BUNDLE / label, copy)
    path = copy / rel
    data = bytearray(path.read_bytes())
    data[len(data) // 3] ^= 0x20
    path.write_bytes(bytes(data))
    checks = RR.verify(copy, A.read_json(copy / "agent_report.json"))
    assert not RR.intact(checks)
    changed = [c.item for c in checks if not c.ok]
    assert changed[0] == rel  # (an unreadable outcome.json also fails its comparison)
    assert all(c == rel or c.startswith("agent_report.json:") for c in changed)
    assert RR.CHANGED == "evidence changed since recording"


def test_the_har_feature_table_is_not_bundled():
    assert not list(H.BUNDLE.rglob("table.parquet"))
    for run in bundle.load_manifest()["runs"]:
        excluded = run["excluded"]
        if run["path"].startswith("t09/"):
            assert sorted(e["path"] for e in excluded) == [
                "original/exec/stage/project/table.parquet",
                "snapshot/table.parquet",
            ]
            assert all("not redistributed" in e["reason"] for e in excluded)
        else:
            assert excluded == []


def test_the_bundle_is_byte_exact_and_never_normalized():
    result = CR.check(H.BUNDLE, names=[])
    assert result["fidelity_problems"] == []
    assert all(v["intact"] for v in result["viewer"].values())
    attrs = subprocess.run(
        ["git", "check-attr", "text", "eol", "--", f"demo/recorded/{RUNS[0]}/preflight.json"],
        capture_output=True, text=True, cwd=H.ROOT, check=True,
    ).stdout  # fmt: skip
    assert "text: unset" in attrs


def test_the_bundle_holds_no_credential_or_contact_data():
    """The bundle's current findings, as a regression guard: host paths and the user name
    are reported for the lead; key-shaped hits are only the provenance `token =` variables
    in the copied ATLAS sources; no e-mail, .env reference or synthetic secret marker."""
    result = CR.check(H.BUNDLE)
    assert "email" not in result["counts"] and "env_reference" not in result["counts"]
    for file, findings in result["findings"].items():
        for f in findings:
            if f["kind"] == "key_shaped":
                assert f["subkind"] == "assignment", (file, f)
                assert "/exec/stage/code/atlas/" in f"/{file}"
    for path in H.BUNDLE.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            for marker in (H.KEY, H.JUDGE_CODE, H.DB_PASSWORD_MARKER):
                assert marker.encode() not in data


def test_the_check_reports_each_kind_without_rewriting(tmp_path, capsys):
    root = tmp_path / "recorded"
    run = root / "r" / "agent-x-000000000000"
    run.mkdir(parents=True)
    texts = {
        "agent_report.json": json.dumps({"agent_log": {"path": "C:\\Users\\alice\\x"}}),
        "notes.txt": (
            "see /home/alice/project and bob@example.org\n"
            f"key {H.KEY} here\n"
            "loaded from .env with NEBIUS_API_KEY\n"
            "postgresql://user:hunter2pass@db.example/x\n"
        ),
    }
    for name, text in texts.items():
        (run / name).write_text(text, encoding="utf-8")
    before = {p: p.read_bytes() for p in run.iterdir()}
    files = {p.name: CR.sha256(p) for p in run.iterdir()}
    (root / "BUNDLE.json").write_text(
        json.dumps({"runs": [{"path": "r/agent-x-000000000000", "files": files}]}),
        encoding="utf-8",
    )
    assert CR.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    result = CR.check(root, names=["alice"])
    kinds = result["counts"]
    for kind in ("host_path", "username", "email", "key_shaped", "env_reference"):
        assert kinds.get(kind), kind
    subkinds = {f.get("subkind") for fs in result["findings"].values() for f in fs}
    assert {"sk_token", "database_url"} <= subkinds
    assert H.KEY not in out and "hunter2pass" not in out  # values never printed
    assert H.KEY not in json.dumps(result) and "hunter2pass" not in json.dumps(result)
    assert {p: p.read_bytes() for p in run.iterdir()} == before  # nothing rewritten
