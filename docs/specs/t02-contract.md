# T-02 contract

Status: **contract decided by the lead (2026-10-15); implemented in T-02 (self-tested, awaiting Codex review); T-02 not accepted.** The lead reviewed the full proposal and approved it with corrections (DECISIONS.md, "T-02 contract dispositions"). This file is the detailed contract with worked examples. The normative summary is in `docs/SPEC.md` §3, §4.2, §5 and §8; if they disagree, SPEC wins. Implementation status is tracked in `TASKS.md` T-02.

Scheduling note: the T-03 hosting probe is due (playbook §11, Day two, 2026-10-15) and is independent of T-02.

**Origin labels** (from the reviewed proposal):

| Label | Meaning |
| --- | --- |
| **[R]** | Required by SPEC text before this review |
| **[C]** | Clarification |
| **[D]** | Lead decision or correction (2026-10-15) |

## 0 Repeated-measures scope (decided separately)

V1 adds no rule beyond routes A and B of `split.repeated_measures_rule`. Other structures stay NOT_ASSESSED `no_supported_rule` (DECISIONS.md, "Repeated-measures scope for V1"). Window-overlap and separation checks are never presented as proof of statistical independence (SPEC §15).

## 1 Manifest field shapes (schema 0.3)

| Field | Shape | Origin |
| --- | --- | --- |
| `schema_version` | `"0.3"`. Legacy `"0.2"` is accepted as qualified below; anything else is rejected | [D] |
| `time_basis` | `{unit: non-empty str, reference_time: non-empty str, scope: "global" \| "per_stream"}`. `scope` is required in 0.3 whenever `time_basis` is supplied. In 0.2 an absent scope means *unspecified* | unit/reference_time [R]; scope [D] |
| `columns.prediction_time`, `stream_id`, `window_start`, `window_end` | Column names | [R] |
| `feature_availability` | Object keyed by declared feature. Each value is exactly one of `{"column": name}` or `{"offset": number}`; availability = `prediction_time + offset` | [R] forms; [C] keys and sign |
| `label_availability` | Exactly one of `{"column": name}` or `{"horizon": number ≥ 0, "reporting_delay": number ≥ 0}` | [R] forms; [C] ≥ 0 |
| `temporal_gap` | Finite number. A negative gap FAILs `cutoff_precedes_evaluation` (SPEC: "`temporal_gap` ≥ 0 and …") | [R] |
| `separation_rule` | `{scope: "global" \| "per_stream", min_gap: number ≥ 0, times: "prediction_time" \| "window"}`. `times` is required in 0.3; a 0.2 rule without it is not assessable | scope/min_gap [R]; times [D] |
| `window_containment` | Optional `{within: "group_id", source: non-empty str, statement: non-empty str}` | [D] |
| `reported_metrics[]` | `{metric_definition: "balanced_accuracy" \| "macro_f1", partition: "development_eval" \| "final_holdout", fold: str, aggregation: "single_fold" \| "mean_over_folds" \| "pooled", value: finite number in [0, 1]}`. `fold = "all"` exactly when `aggregation` is `mean_over_folds` or `pooled` | [R] fields; [C] enumerations and pairing |
| `primary_metric` | `"balanced_accuracy" \| "macro_f1"` | [R] |

**Validation** [D]:
- Every number is a finite `int`/`float`; booleans are rejected everywhere.
- A malformed, nonfinite, out-of-range or boolean value, or an unsupported `schema_version`, fails intake. That takes the existing `NOT_SUPPORTED` path ("manifest unparseable"), and the reason names the failing fields.
- Missing or corrupt *runtime* evidence is a different case and gives ERROR.

**Complete example** (`future_time`):

```json
{
  "schema_version": "0.3",
  "table": {"path": "table.csv", "format": "csv"},
  "columns": {
    "row_id": "row_id",
    "target": "churned",
    "class_map": {"0": "stayed", "1": "churned"},
    "features": ["tenure_days", "tickets_30d", "last_invoice"],
    "prediction_time": "pred_day"
  },
  "claim": {
    "type": "future_time",
    "statement": "The model predicts next-month churn for later months.",
    "sampling_unit": "row",
    "dependence": [{"kind": "temporal_order"}]
  },
  "time_basis": {"unit": "day", "reference_time": "day 0 = 2025-01-01T00:00Z", "scope": "global"},
  "feature_availability": {
    "tenure_days": {"offset": 0},
    "tickets_30d": {"offset": -1},
    "last_invoice": {"column": "invoice_known_day"}
  },
  "label_availability": {"horizon": 30, "reporting_delay": 20},
  "temporal_gap": 0,
  "primary_metric": "balanced_accuracy",
  "reported_metrics": [
    {"metric_definition": "balanced_accuracy", "partition": "development_eval",
     "fold": "all", "aggregation": "mean_over_folds", "value": 0.7123456789},
    {"metric_definition": "macro_f1", "partition": "development_eval",
     "fold": "fold0", "aggregation": "single_fold", "value": 0.6890123456}
  ],
  "development_seeds": [0],
  "entry_point": "evaluate.py"
}
```

The per-fold training cutoff comes from `declare_split(..., training_cutoff=...)` and is recorded in `splits.json` [R].

## 2 Time representation, scope and equality

**Representation** [D]: finite numbers in the one declared unit. There is no date parsing and no automatic unit conversion. `reference_time` is documentation only, and global comparability is never inferred from it.

**Scope** [D]: `global` means any two values in the project are comparable. `per_stream` means only values in the same stream are comparable. An unspecified scope (legacy 0.2) blocks only cross-stream comparisons.

| Comparison | Needs |
| --- | --- |
| Window bounds within one stream (`no_window_overlap`) | A known stream; any scope |
| Separation, `scope: per_stream` | A known stream; any `time_basis` scope |
| Separation, `scope: global` | `time_basis.scope: global` |
| `training_labels_available_by_cutoff`, `cutoff_precedes_evaluation` (one cutoff per fold) | `time_basis.scope: global` |
| `features_available_when_used` (same row: availability vs prediction time; column or offset) | Any scope, because it compares within one row on its declared local clock |

**Rows and values** [C]:
- Rows considered are the train and eval rows of every declared fold.
- A null, non-numeric, boolean or nonfinite time makes that row unknown.
- A witness among known rows gives FAIL, with unknown counts disclosed. Otherwise an unknown participating row gives NOT_ASSESSED `missing_metadata`. PASS needs every participating row known.
- A null cutoff gives NOT_ASSESSED `missing_metadata`. A non-numeric, boolean or nonfinite cutoff is invalid candidate-produced evidence and gives ERROR `evidence_invalid`. A valid FAIL elsewhere stands.

**Equality boundaries:**

| Rule | Passes when | Origin |
| --- | --- | --- |
| Window overlap | No same-stream pair with `max(start) < min(end)`. `[0,10)` and `[10,20)` do not overlap | [R] |
| Window bounds | `start < end` for every window whose bounds are needed. Zero-length or reversed windows are unusable metadata, so the row is unknown | [D] lead policy change |
| Training labels | `prediction_time ≤ cutoff` and label availability `≤ cutoff` | [R] |
| Cutoff precedes evaluation | `temporal_gap ≥ 0` and `cutoff + gap ≤` earliest eval `prediction_time` | [R] |
| Feature availability | Availability `≤` the row's `prediction_time` | [R] |
| Separation | Gap `≥ min_gap` | [C] |
| Reported metric | `abs(reported − recomputed) <= 1e-6` in float64; no relative tolerance, rounding or extra epsilon | [D] |

**Float64 at the boundary** [D]: the rule is applied literally to binary floats. A decimal-intended equality can land on either side. `5/9 + 1e-6` differs from `5/9` by 1.0000000000287557e-06, so it FAILs. With `recomputed = 0`, `reported = 1e-6` PASSes, and the next representable value above 1e-6 FAILs. Tests cover equality, both adjacent representable values, and the 5/9 example.

**Trust boundary** [R]: cutoffs and fold membership are declared by the candidate's code. The checks test the data against those declarations; they do not verify them independently.

## 3 Separation rule

**Applicability** [R]:
- Required for `same_population` and `unseen_group` when `temporal_order` is declared.
- `future_time` stays directional and separate, through the `temporal.*` assertions.
- No rule gives NOT_ASSESSED `no_declared_rule`.

**Basis** [D]: `times: "prediction_time"` uses points, and `times: "window"` uses `[start, end)` intervals, which must satisfy `start < end`. The basis is never guessed. An undeclared `times` or a missing named column gives NOT_ASSESSED `missing_metadata`.

**Direction** [D]: two-sided, within each fold. Every train item and every eval item in scope must be at least `min_gap` apart, whichever comes first. A one-sided "eval after train" rule would exclude designs that train after evaluation, which is why it was not chosen for these claims.

**Distance** [D]:
- points: `abs(t_eval − t_train)`;
- intervals: `max(start_eval − end_train, start_train − end_eval)`, which is negative when they overlap and 0 when adjacent.
- Equality passes.

**Scope:**
- `per_stream` compares pairs within the same known stream. A missing `stream_id` column gives `missing_metadata`, and a null stream makes that row unknown.
- `global` needs `time_basis.scope: global`.

Every result carries the limitation "verifies the declared rule; not proof of statistical independence".

## 4 Window overlap: routes D and C

Evaluated per fold.

**D, direct (table)** [D]:
- If every participating row has a known stream and no stream has rows in both partitions, the fold has no possible overlap. Bounds are not used. The basis recorded is `stream_membership_disjoint`.
- A stream in both partitions needs usable bounds (`start < end`) for its rows, and then the overlap test applies. The basis recorded is `interval_comparison`.
- Comparing bounds needs a `time_basis` (any scope, since the comparison is within one stream).
- Any witness gives FAIL, recording the fold, stream, rows and intervals.

**C, documented containment** [D]:
- Used only for folds where D is incomplete. It needs a `window_containment` declaration (`within: "group_id"`) and a **valid PASS of `split.no_group_overlap`** (`depends_on` recorded).
- It is conditional on the declaration, not independent verification. The source and statement are recorded verbatim and prominently. Non-empty strings show only that a declaration was supplied, and sources are never fetched.
- UCI HAR containment evidence still needs the T-09 review.
- If the group check is not a valid PASS, the result is NOT_ASSESSED `missing_metadata`; the group check reports any group violation itself.

**Contradiction** [D]:
- A known stream observed in two or more groups (among participating rows with both values known) disables route C and is recorded.
- It never suppresses a valid D FAIL or a complete D assessment.
- If C was needed and is disabled, the result is NOT_ASSESSED `no_supported_rule`.

**Neither route completes, and no witness** [R]: NOT_ASSESSED `missing_metadata`.

Every result carries the limitation "verifies declared stream identity and window intervals; not proof of statistical independence".

s07 (committed table) passes through D, with basis `stream_membership_disjoint`: its 16 streams each lie within one subject, and no stream has rows in both partitions in any of its 4 `GroupKFold` folds.

## 5 Metrics

**Class universe** [C]:
- The keys of `class_map`.
- A value maps to a key if it is a string equal to the key, an integer whose decimal form equals it, or an integral finite float (`1.0` → `"1"`).
- Anything else is invalid: other floats, booleans, null, or a class *name*.
- True labels come from the evaluator's own copy of the table; predictions come from `predictions/<fold>.parquet`, matched by row ID [R].

**Per fold** [D]:
- **Balanced accuracy:** the mean of recall `TP_c/(TP_c+FN_c)` over classes present in the evaluated true labels.
- **Macro-F1:** the mean of `2·TP_c/(2·TP_c+FP_c+FN_c)` over classes present in the true labels or the predictions.

**Aggregation** [D]:
- `single_fold`: one fold's value.
- `mean_over_folds`: the unweighted mean over every declared fold of the partition.
- `pooled`: the metric over the concatenated (fold, row) observations. A row evaluated in several folds counts once per evaluation occurrence; the number of such repeated rows is reported.

**Completeness** [D]:
- An empty, invalid or missing required fold is never silently omitted.
- An incomplete aggregate cannot support PASS; its reason is reported. Missing or invalid evidence, or invalid labels or predictions, give ERROR `evidence_invalid`. An empty evaluation fold gives NOT_ASSESSED `empty_evaluation`.
- Valid per-fold results are still shown separately.

**`metric.reported_matches_recomputed` per entry**, then the worst result (FAIL > ERROR > NOT_ASSESSED > PASS), so a valid FAIL is preserved:
- PASS within tolerance; FAIL outside it.
- ERROR `evidence_invalid` when:
  - a needed fold's prediction artifact is missing or invalid, or its row IDs differ from the declared evaluation rows;
  - a label or prediction is outside the class universe;
  - the named fold is undeclared or of another partition kind;
  - `fold = "all"` is ambiguous because a declared fold is literally named `"all"`.
- NOT_ASSESSED `not_executed` for `final_holdout` (no evaluator-only holdout label store exists yet), or when no fold of the partition is declared.

**Descriptive outputs:**
- `metric.recomputed_primary` reports both metrics per fold, `mean_over_folds` and `pooled`, with completeness flags, and marks the primary metric.
- Descriptive results never affect the outcome. They are listed separately from required assertions.

## 6 Baselines and class support

**Dummy baseline** [D]:
- It is the most frequent class among fold *k*'s training labels in the evaluator's copy, with ties broken by declared `class_map` order. That tie rule is not claimed to match scikit-learn's.
- It predicts that class for each of fold *k*'s evaluation rows and reports both metrics per fold, `mean_over_folds` and `pooled`.
- Empty or invalid training labels make it unavailable for that fold, with the reason; no prediction is invented. Aggregates follow the completeness rule.
- It is descriptive. Beating it is not evidence of usefulness, and falling below it is not evidence of leakage.
- **Linear baseline:** deferred; reported as not computed.

**`split.class_support`** (descriptive): per-fold train and eval counts for each `class_map` key, and the absent classes. Splitter minimum requirements are reported as **unavailable** (not recorded by the recorder); SPEC §4.2 is corrected accordingly [D].

## 7 Versioning and fixtures

**Versions** [D]:
- Manifest schema `0.3`, accepting `0.2` as qualified above and rejecting other versions.
- The policy becomes `policy-v1.3`, with required sets unchanged.
- Historical evidence keeps its recorded version and is not rewritten.
- `policy_version` names the rules, not the code. Task records keep the reviewed commit.

**Fixtures** [D]:
- T-01 fixture bytes are preserved.
- s07's `split.no_window_overlap` may become PASS, and its outcome `NO_VIOLATION_FOUND`, once every required assertion is shown to pass. Its historical policy-v1.2 result (`INCONCLUSIVE`) stays a correct record.
- Required-but-unimplemented assertions keep independent test coverage.
- New T-02 fixtures live in `benchmarks/t02/`.

## 8 Worked examples

**A. The `future_time` counterexample** (global day clock):
- Training row `r1` has `prediction_time` 100.
- Label availability `{horizon: 30, reporting_delay: 20}`, so r1's label arrives at 150.
- Evaluation row `r2` has `prediction_time` 120.
- The gap is 0.

| Cutoff | Labels by cutoff | Cutoff precedes eval | Outcome |
| --- | --- | --- | --- |
| 120 | FAIL (150 > 120) | PASS (120 ≤ 120) | VIOLATION_FOUND |
| 150 | PASS (equality) | FAIL (150 > 120) | VIOLATION_FOUND |
| 130 | FAIL | FAIL | VIOLATION_FOUND |
| null | NOT_ASSESSED `missing_metadata` | NOT_ASSESSED `missing_metadata` | INCONCLUSIVE |

- No cutoff passes both checks.
- With `time_basis.scope: per_stream` or unspecified, both cutoff checks are NOT_ASSESSED `missing_metadata`. `features_available_when_used` is still assessed, row by row.

**B. Feature availability:**
- `r2` at 120 with an availability of 121 → FAIL. At 120 → PASS.
- `{"offset": 1}` → FAIL for every row.
- No entry for a feature → NOT_ASSESSED `missing_metadata`, unless another FAIL exists.

**C. Windows** (same stream unless stated):
- `[0,10)` vs `[10,20)` → PASS.
- `[0,10)` vs `[5,15)` → FAIL.
- Streams A and B → PASS.
- A crossing stream with `[5,5)` or `[6,5)` → unknown → NOT_ASSESSED `missing_metadata`.
- An eval row with a null stream and no witness → NOT_ASSESSED.
- Complete streams that never cross partitions → PASS with basis `stream_membership_disjoint` (s07).
- Route C with a valid group PASS → PASS, with the documented-containment limitation and `depends_on`.
- A contradiction plus an incomplete direct route → NOT_ASSESSED `no_supported_rule`.
- A contradiction plus a direct witness → FAIL.

**D. Separation** (`unseen_group`, `temporal_order`):
- Points, global, `min_gap` 15:
  - train `{0, 10, 20}`, eval `{35, 45}` → PASS (15 ≥ 15);
  - `min_gap` 16 → FAIL;
  - eval `{−10}` → FAIL (distance 10, two-sided).
- Windows, `min_gap` 0:
  - `[0,10)` vs `[10,20)` → PASS;
  - `[5,15)` → FAIL (gap −5);
  - `min_gap` 1 with adjacent windows → FAIL.

**E. Metrics** (`class_map` keys `"0"`, `"1"`, `"2"`; values checked against scikit-learn 1.9.1):
- **E1:** true `[0,0,0,1,1,2]`, predicted `[0,0,1,1,1,0]`.
  - Recall: class 0 is 2/3, class 1 is 1, class 2 is 0. Balanced accuracy is **5/9**.
  - F1: class 0 is 2/3, class 1 is 4/5, class 2 is 0. Macro-F1 is **22/45**.
- **E2 (absent class):** true `[0,0,1,1]`, predicted `[0,2,1,1]`. Balanced accuracy is **0.75** (class 2 adds no term). Macro-F1 is **5/9** (class 2 counts, with F1 0).
- **E3 (aggregation over E1 and E2):** `mean_over_folds` gives BA 47/72 and macro-F1 47/90. `pooled` gives BA 8/15 and macro-F1 14/27.
- **E4 (comparison against 5/9):** `0.555556` → PASS; `0.555558` → FAIL; `0.5556` → FAIL; `5/9 + 1e-6` → FAIL (literal float64). `NaN`, `1.2` or `true` → rejected at intake.
- **E5 (invalid input):** a prediction of `3`, or the class name `"move"` → ERROR `evidence_invalid`. If a fold of a `mean_over_folds` entry is missing, the entry is ERROR, never a mean over the remaining folds.

**F. Dummy baseline:**
- Training labels `[0,0,1,1,1,2]` → predicts 1 → E1 gives BA 1/3 and macro-F1 1/6.
- A tie in `[0,0,1,1]` → `class_map` order → `"0"`.
- An empty training partition → unavailable.

**G. Class support:** E2's fold lists class `"2"` as absent from evaluation. No split assertion changes.
