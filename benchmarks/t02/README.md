# T-02 trusted fixtures

Repo-authored, reviewed **synthetic** fixtures for the T-02 scenarios (TASKS.md T-02; policy-v1.3; manifest schema 0.3). They are test fixtures, not a benchmark measurement.

They run under the same fixture rule as T-01 (docs/SPEC.md §10). Each fixture's complete file inventory must match `src/atlas/runner/trusted_fixtures.json`. After any reviewed fixture change, regenerate the allowlist over every fixture root:

```text
uv run --locked python -m atlas.runner.trusted allowlist benchmarks/t01 benchmarks/t02
```

## Generator settings (fixed before use)

Tables and manifests are written by `generate.py` (`uv run --locked python benchmarks/t02/generate.py`). Regeneration is byte-identical.

| Setting | Value |
| --- | --- |
| Seed | 20261015 (future-time table); 20261016 (window table) |
| Features | f0–f2; class signal label × [1.0, 0.7, 0.4] plus N(0, 1) noise |
| Future-time table | 120 rows, one per day (`pred_day` 0–119), global day clock |
| Label availability | horizon 5 + reporting delay 2: a label is known 7 days after its prediction day |
| Feature availability | f0 offset 0, f1 offset −1, f2 via `f2_known` = prediction day (the equality boundary) |
| Future-time folds | 4 forward folds; fold k evaluates days [60 + 15k, 75 + 15k) with cutoff 60 + 15k and gap 0 |
| Window table | 6 sensor streams × 24 windows; window j spans [5j, 5j + 10) samples (overlapping); label (j // 3) mod 2 |
| Separation rule | per stream, `min_gap` 5, `times: window`; per-stream clock |

The reported metrics in s11b and s11c are computed in `generate.py` by scikit-learn, on a plain replication of the clean protocol read back from the written CSV. This independently cross-checks the evaluator's metric code.

## Scenarios

| Directory | What differs | Expected |
| --- | --- | --- |
| `s11a_future_time_label_leak` | Training uses every day before the cutoff, so the last 6 training days' labels are not yet available (ATLAS-authored flaw) | `training_labels_available_by_cutoff` FAIL → VIOLATION_FOUND |
| `s11b_future_time_clean` | Training keeps only days whose labels are known by the cutoff; two reported metrics (mean-over-folds balanced accuracy, pooled macro-F1) | All PASS → NO_VIOLATION_FOUND |
| `s11c_reported_metric_mismatch` | s11b, with the balanced accuracy misreported by 0.01 | `reported_matches_recomputed` FAIL → VIOLATION_FOUND |
| `s12a_same_population_random_windows` | Shuffled `KFold(4)` over overlapping windows (ATLAS-authored flaw) | window overlap FAIL, separation FAIL → VIOLATION_FOUND |
| `s12b_same_population_blocked_windows` | Contiguous evaluation blocks, with neighbours purged to keep 5 samples' separation | All PASS (smallest gap exactly 5) → NO_VIOLATION_FOUND |
