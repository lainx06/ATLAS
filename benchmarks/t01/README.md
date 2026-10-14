# T-01 trusted fixtures

Repo-authored, reviewed **synthetic** fixtures for the T-01 acceptance scenarios (TASKS.md). They are test fixtures, not a benchmark measurement, and the data does not represent any real person.

Only these fixtures may execute on the host, under the fixture rule (docs/SPEC.md §10): each fixture's complete file inventory (every file in its directory, LF-normalized SHA-256) must match an entry in `src/atlas/runner/trusted_fixtures.json`, so an added or changed file is refused. The child runs in Python isolated mode with the trusted `atlas` package inserted explicitly; this is not a sandbox. After any reviewed fixture change, regenerate the allowlist:

```text
uv run --locked python -m atlas.runner.trusted allowlist benchmarks/t01
```

## Generator settings (fixed before use)

Tables and manifests are written by `generate.py` (`uv run --locked python benchmarks/t01/generate.py`):

| Setting | Value |
| --- | --- |
| Seed | 20261014 |
| Subjects × sessions × windows | 8 × 2 × 10 = 160 rows |
| Features | f0–f5 |
| Class signal | label × [0.8, 0.6, 0.4, 0, 0, 0] |
| Subject offset SD / session offset SD / noise SD | 1.0 / 0.3 / 1.0 |
| Label | window index mod 2 (balanced within each session) |
| Base windows | non-overlapping; `overlapping_windows` is not declared |
| s07 windows | length 10, step 5 within each session stream (truthfully overlapping) |
| s10 planted pairs | 3 rows given another subject's identical feature and label values, chosen so the subjects fall in different `GroupKFold(4)` folds |

## Scenarios

| Directory | What differs |
| --- | --- |
| `s01_faulty` | Global `SelectKBest(f_classif)` on all rows, then a random-row `KFold` (ATLAS-authored flaws) |
| `s02_clean` | `GroupKFold(4)` by subject; scaler, selector and classifier fit per fold via `take` |
| `s03a_rebuilt_frame` | s02, but the training frame is rebuilt with the same valid index |
| `s03b_inplace_mutation` | s02, but a tracked training frame is modified in place |
| `s04_zero_fit` | Majority-class predictions; no classifier fit |
| `s05a_contaminated_reuse` | A selector fit in fold 0 is reused in later folds |
| `s05b_benign_reuse` | A selector fit only on always-training subjects (S07, S08) is reused |
| `s06_missing_metadata` | s02 code; the manifest omits the `group_id` and `unit_id` roles |
| `s07_unimplemented_window` | s02 code; the manifest truthfully declares overlapping windows |
| `s08a_combined_claim` | Claim type `unseen_group+future_time` (never executed) |
| `s08b_no_adapter` | Plain scikit-learn script without the adapter (never executed) |
| `s10a_identical_values_with_ids` | Planted identical-value pairs with distinct `observation_id` |
| `s10b_identical_values_no_ids` | The same pairs; no observation identity declared |
| `s10c_known_duplicate` | As s10b, plus one pair documented in `known_duplicates` |
