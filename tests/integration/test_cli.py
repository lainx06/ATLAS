"""CLI behavior, including the relative --runs-dir regression found while running T-01 by hand."""

from pathlib import Path

from atlas.cli import main

FIXTURES = Path(__file__).resolve().parents[2] / "benchmarks" / "t01"


def test_relative_runs_dir_keeps_evidence_in_the_run_directory(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)

    code = main(
        ["audit", str(FIXTURES / "s02_clean"), "--mode", "audit", "--runs-dir", "runs"]
    )

    assert code == 0
    assert "outcome: NO_VIOLATION_FOUND" in capsys.readouterr().out
    assert list((tmp_path / "runs").rglob("provenance.jsonl"))
    assert not list((FIXTURES / "s02_clean").rglob("provenance.jsonl"))


def test_agent_mode_needs_a_fixture_script_and_memory_mode_is_not_implemented(capsys):
    # T-06 slice 3: agent mode exists (fixture replies only); it refuses to start without one.
    code = main(["audit", str(FIXTURES / "s02_clean"), "--mode", "agent"])
    assert code == 2
    assert "--fixture-script" in capsys.readouterr().err
    code = main(["audit", str(FIXTURES / "s02_clean"), "--mode", "agent+memory"])
    assert code == 2
    assert "not implemented" in capsys.readouterr().err
