"""Fixture integrity: allowlist matches reviewed fixtures; generator reproduces tables; declarations are truthful."""

import importlib.util
import json
from pathlib import Path

import pandas as pd

from atlas.runner.trusted import build_allowlist, load_allowlist

FIXTURES = Path(__file__).resolve().parents[2] / "benchmarks" / "t01"


def _generator():
    spec = importlib.util.spec_from_file_location(
        "t01_generate", FIXTURES / "generate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_allowlist_matches_current_fixture_hashes():
    # Every reviewed fixture root, in order: T-01, then T-02 (policy-v1.3).
    roots = (FIXTURES, FIXTURES.parent / "t02")
    assert load_allowlist() == build_allowlist(*roots)["fixtures"]


def test_generator_reproduces_the_committed_base_table():
    regenerated = _generator().base_table()
    committed = pd.read_csv(FIXTURES / "s02_clean" / "table.csv", dtype={"row_id": str})

    pd.testing.assert_frame_equal(committed, regenerated, check_dtype=False)


def test_declared_overlapping_windows_really_overlap_within_a_stream():
    table = pd.read_csv(FIXTURES / "s07_unimplemented_window" / "table.csv")
    first = table[table["stream_id"] == table["stream_id"].iloc[0]].sort_values(
        "window_start"
    )

    assert (
        first["window_start"].iloc[1:].to_numpy()
        < first["window_end"].iloc[:-1].to_numpy()
    ).all()


def test_planted_identical_value_pairs_have_distinct_observation_ids():
    gen = _generator()
    table = pd.read_csv(
        FIXTURES / "s10a_identical_values_with_ids" / "table.csv", dtype={"row_id": str}
    ).set_index("row_id")
    pairs = gen.planted_pairs(gen.base_table())
    value_cols = [*gen.FEATURES, "activity"]

    for src, dst in pairs:
        assert (
            table.loc[src, value_cols].to_numpy()
            == table.loc[dst, value_cols].to_numpy()
        ).all()
        assert table.loc[src, "observation_id"] != table.loc[dst, "observation_id"]
    manifest = json.loads(
        (FIXTURES / "s10c_known_duplicate" / "atlas_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["known_duplicates"] == [list(pairs[0])]
