# T-11 three-way comparison (descriptive)

> **Development cases, not held-out: ATLAS's checks were built and debugged on these four cases, so ATLAS's results on them are not evidence of generalization. Results are descriptive.**

- Mode: LIVE, model `nvidia/nemotron-3-super-120b-a12b`.
- Seed 2937182895; leg (b) case order: s02_clean, s01_faulty, har_clean, har_flawed.
- Policy policy-v1.3; 3 repetitions per case, at most 3 requests per case run, no retries.

## Expected violated assertion IDs (predeclared, `evaluation/expected.json`)

| Case | Expected |
| --- | --- |
| s01_faulty | `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.repeated_measures_rule`, `split.sampling_unit_disjoint` |
| s02_clean | none |
| har_flawed | `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.no_window_overlap`, `split.repeated_measures_rule`, `split.sampling_unit_disjoint` |
| har_clean | none |

## Leg (a): ATLAS deterministic audit

| Case | Source | Outcome | TP | FP | FN | Coverage gaps (expected) | Errors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s01_faulty | recorded: demo/recorded/live6/agent-s01_faulty-877f8245a8a2 | VIOLATION_FOUND | `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.repeated_measures_rule`, `split.sampling_unit_disjoint` | none | none | none (none) | none |
| s02_clean | re-run: the T-09 Docker audit path (benchmarks/real_sensor/run_audit.py) | NO_VIOLATION_FOUND | none | none | none | none (none) | none |
| har_flawed | recorded: demo/recorded/t09/agent-har_flawed-1e2267f662c0 | VIOLATION_FOUND | `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.repeated_measures_rule`, `split.sampling_unit_disjoint` | none | none | `split.no_window_overlap` (`split.no_window_overlap`) | none |
| har_clean | recorded: demo/recorded/t09/agent-har_clean-ac63eaecd7a8 | NO_VIOLATION_FOUND | none | none | none | none (none) | none |

## Leg (b): Nemotron alone (no executable checks)

| Case | Input estimate | Trial | Status | Code | Violated | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s01_faulty | 8293 | 1 | VALID |  | `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.repeated_measures_rule`, `split.sampling_unit_disjoint` | 4 | 0 | 0 |
| s01_faulty | 8293 | 2 | INVALID_REPLY | rationale_too_long |  |  |  |  |
| s01_faulty | 8293 | 3 | VALID |  | `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.sampling_unit_disjoint` | 3 | 0 | 1 |
| s02_clean | 8264 | 1 | VALID |  | none | 0 | 0 | 0 |
| s02_clean | 8264 | 2 | VALID |  | none | 0 | 0 | 0 |
| s02_clean | 8264 | 3 | INVALID_REPLY | rationale_too_long |  |  |  |  |
| har_flawed | 34605 | 1 | VALID |  | `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.repeated_measures_rule`, `split.sampling_unit_disjoint` | 4 | 0 | 1 |
| har_flawed | 34605 | 2 | VALID |  | `fit.coverage_complete`, `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.repeated_measures_rule`, `split.sampling_unit_disjoint` | 4 | 1 | 1 |
| har_flawed | 34605 | 3 | VALID |  | `fit.coverage_complete`, `fit.state_dependencies_within_fold_train`, `split.no_group_overlap`, `split.repeated_measures_rule`, `split.sampling_unit_disjoint` | 4 | 1 | 1 |
| har_clean | 33726 | 1 | VALID |  | none | 0 | 0 | 0 |
| har_clean | 33726 | 2 | VALID |  | none | 0 | 0 | 0 |
| har_clean | 33726 | 3 | INVALID_REPLY | rationale_too_long |  |  |  |  |

## Totals

| Leg | TP | FP | FN | Precision | Recall | Clean FP | Clean false-violation rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (a) ATLAS | 8 | 0 | 0 | 1.0000 | 1.0000 | 0 | 0.0000 |
| (b) Nemotron alone, valid trials | 19 | 2 | 4 | 0.9048 | 0.8261 | 0 | 0.0000 |

- Leg (a): 4 of 4 cases available; expected IDs left NOT_ASSESSED (coverage gaps, not misses): 1; on ERROR: 0.
- Leg (b): 12 trials scheduled; 9 valid, 3 INVALID_REPLY, 0 not sent, 0 model errors (none of these is scored).

## Leg (c): reported against recomputed metric (descriptive, never an outcome)

| Case | Metric | Reported | Recomputed (mean over folds) | Recomputed (pooled) | Clean control | Clean control recomputed (mean over folds) |
| --- | --- | --- | --- | --- | --- | --- |
| s01_faulty | balanced_accuracy | none declared | 0.6824 | 0.6812 | s02_clean | 0.6688 |
| s02_clean | balanced_accuracy | none declared | 0.6688 | 0.6687 |  |  |
| har_flawed | balanced_accuracy | 0.9064 | 0.9064 | 0.9063 | har_clean | 0.8752 |
| har_clean | balanced_accuracy | none declared | 0.8752 | 0.8746 |  |  |

## Cost (estimates, not billing)

- estimates at listed prices from provider-reported usage; not billing.
- Per case run: {"har_clean": "0.0213912", "har_flawed": "0.0203715", "s01_faulty": "0.0108198", "s02_clean": "0.0104796"}.
- Estimated total: 0.0630621 USD (not billing).
