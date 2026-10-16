# ATLAS technical specification (V1, LENS)

Status: **reviewed draft**. Step 8 scientific-review dispositions were applied on 2026-10-14 (DECISIONS.md, "Step 8 scientific review dispositions"); the reviewed packet snapshot is `handoffs/science-01.md`. These contracts are **not implemented**. The remaining gated questions (§14) are owned by named later milestones. Product requirements are in `docs/PRD.md`; vocabulary in `GLOSSARY.md`; decision history in `DECISIONS.md` (Q1–Q6, F1–F5, L1–L2).

## 1 Conventions

- "Planned" means specified here, not built. No command in this file exists yet unless it is marked existing.
- Check statuses: `PASS | FAIL | NOT_ASSESSED | ERROR`. Every NOT_ASSESSED carries a reason code (§6).
- Run outcomes: `NOT_SUPPORTED | VIOLATION_FOUND | INCONCLUSIVE | NO_VIOLATION_FOUND`.
- Contracts are Pydantic models serialized to JSON. Every contract has a `schema_version`, and evidence artifacts carry SHA-256 hashes.
- The engine (`src/atlas/`) is independent of the UI (`app.py`). The UI only calls engine APIs and renders their results.

## 2 Modules (planned layout, from playbook §5/§10)

| Module | Owns | Must not |
| --- | --- | --- |
| `atlas.contracts` | Manifest, claim, check, run, candidate, procedure, policy schemas | — |
| `atlas.intake` | File/schema inventory, manifest validation, supportedness decision | Trust repository instructions or guess ground truth |
| `atlas.adapter` + `atlas.recorder` | Candidate-side data loading, supported row selection, split/prediction declaration, provenance recording (§4) | Score anything; hold final-holdout labels |
| `atlas.checks.*` | The five checks (§5) | Free-form judgments |
| `atlas.policy` | Versioned evaluation policy, scheduling of the full required set, outcome derivation (§6) | Accept agent-selected assertion subsets |
| `atlas.evaluator` | Trusted metric recomputation and label stores (§8) | Run inside the candidate process |
| `atlas.runner` | Snapshots, isolated execution, capability reporting (§10) | Fall back to host execution of candidate code |
| `atlas.agent` | Nebius client, bounded state machine, typed tools (§11) | Execute raw shell; declare success; remove scheduled assertions |
| `atlas.procedures` | Admission, applicability, retrieval, versioning (§12) | Reuse on textual similarity or across claim mismatch |
| `atlas.reports`, `atlas.cli` | Evidence export, repeatable commands | Hide failures, replay or limits |

## 3 Project manifest and claim

A supported project directory contains `atlas_manifest.json`, a table (`.csv`/`.parquet`) and an entry script (default `evaluate.py`).

```text
ProjectManifest (schema_version "0.3"; legacy "0.2" accepted as qualified below; any other value is rejected)
  table: path, format (csv|parquet)
  columns:
    row_id              required, unique
    target              required; class_map required (classification only)
    features            explicit list (no implicit "all other columns")
    group_id            required for unseen_group; optional otherwise
    unit_id             required when claim.sampling_unit is session|subject|other (the unit's identifier column; may equal group_id)
    observation_id      optional: source-observation identity (§5, duplicates)
    stream_id           required when dependence includes overlapping_windows (source-stream identity; never guessed)
    window_start / window_end   required with overlapping_windows; half-open interval [start, end) in the time basis
    prediction_time     required for future_time
  time_basis            required for future_time and for window/temporal rules:
                        {unit: non-empty text, reference_time: non-empty text (documentation, never parsed),
                         scope: global | per_stream}  (scope required in 0.3; absent in 0.2 = unspecified)
  feature_availability  future_time: object keyed by declared feature; each value exactly one of
                        {column: <availability-time column>} or {offset: <number>} (availability = prediction_time + offset)
  label_availability    future_time: exactly one of {column: <availability-time column>} or
                        {horizon: <number ≥ 0>, reporting_delay: <number ≥ 0>} (availability = prediction_time + horizon + reporting_delay)
  temporal_gap          future_time: declared gap (finite number; a negative gap FAILs cutoff_precedes_evaluation, §5)
  separation_rule       optional, for temporal_order: {scope: global | per_stream, min_gap: <number ≥ 0>,
                        times: prediction_time | window}  (times required in 0.3; absent in 0.2 → not assessable)
  window_containment    optional, for overlapping_windows: {within: group_id, source: non-empty text, statement: non-empty text}
                        (a documented declaration; recorded, never fetched or verified; §5)
  known_duplicates      optional: documented groups of row IDs that are the same source observation
  claim:
    type                same_population | unseen_group | future_time
    statement           the user's plain-language claim (kept verbatim)
    sampling_unit       row | window | session | subject | other(text)
    dependence          list of: none_declared | repeated_measures(column) | overlapping_windows | temporal_order | other(text)
  primary_metric        balanced_accuracy | macro_f1
  development_seeds     predeclared list (robustness)
  entry_point           path relative to project root (allowed path for candidates)
  reported_metrics      optional list of {metric_definition: balanced_accuracy | macro_f1,
                        partition: development_eval | final_holdout, fold: <declared fold> | "all",
                        aggregation: single_fold | mean_over_folds | pooled, value: finite number in [0, 1]}
                        (fold "all" exactly when aggregation is mean_over_folds or pooled; §8)
```

**Values and validation (schema 0.3, T-02).**
- Every temporal and metric number is a finite `int` or `float`; booleans are rejected. Times are numbers in the one declared `time_basis.unit`. ATLAS parses no dates and converts no units.
- A manifest that is malformed, uses an unsupported `schema_version`, or carries a nonfinite, out-of-range or boolean value is rejected at intake. The run is `NOT_SUPPORTED` ("manifest unparseable"), and the reason names the failing fields. This is distinct from missing or corrupt runtime evidence, which gives ERROR (§6).
- **Legacy 0.2:** it is validated with the same field shapes, except that `time_basis.scope` and `separation_rule.times` may be absent. An absent scope means *unspecified*. It is never read as per-stream or as global, and global comparability is never inferred from `reference_time` prose.

**Supportedness (run-level).** The run outcome is `NOT_SUPPORTED` when any of these hold:
- the claim type is not one of the three, or is combined;
- the task is not classification;
- the manifest or table is absent or unparseable;
- the table format is unsupported;
- the entry point doesn't use the adapter at all.

In the last case, static suspicions may still be shown; they never change statuses (Q3). Missing *metadata* for a supported claim type is **not** NOT_SUPPORTED: the affected required assertions become NOT_ASSESSED with reason `missing_metadata` (Q1, Q2 rule 2).

**Claim confirmation.** The model may pre-fill a `Claim` from the statement. It is a proposal until the user confirms it. Only a confirmed claim reaches the policy, and an edit invalidates any prior results for the run. Truthful dependence declarations are never removed to change an outcome.

## 4 Adapter, supported path, provenance (Q3, F1)

### 4.1 Adapter API (candidate side, read-only package mounted into the container)

| Call | Contract |
| --- | --- |
| `load_table()` | Returns tracked `(X: DataFrame, y: Series)` for **development** rows. Index = `row_id` (unique, validated against the manifest). `X` holds only the declared feature columns. |
| `load_holdout_features()` | Returns tracked final-holdout `X` only (no target), for evaluation runs. Holdout labels never enter the container (§8). |
| `load_metadata()` | Returns the table's non-feature, non-target columns (e.g. group IDs) for building splits. **Untracked**: data from it has no ancestry, so fitting on it is a coverage gap. Added during T-01. |
| `take(obj, row_ids)` | **Supported row selection.** Returns a tracked subset of a tracked frame/series. `row_ids` must be a subset of `obj`'s rows. Splitter output is turned into row IDs and passed through `take`. |
| `declare_split(fold, train_ids, eval_ids, kind[, training_cutoff])` | Opens fold context `fold`. `kind` ∈ {development_eval, final_holdout}. `training_cutoff` is required for `future_time`. Validated: IDs exist, no duplicates within a list. Also records a provenance split event with hashes of both ID lists, for reconciliation with `splits.json`. |
| `write_predictions(fold, row_ids, y_pred[, y_score])` | Writes `predictions/<fold>.parquet` keyed by row ID, then records a prediction event with the written row IDs, the artifact path and its SHA-256. `y_pred` must be a tracked output of a recorded prediction use in that fold; otherwise prediction ancestry is missing (a coverage gap). |

### 4.2 Supported operations (initial enumerated list; tested before being claimed)

- Adapter: `load_table`, `load_holdout_features`, `take`, `declare_split`, `write_predictions`.
- Composition: `Pipeline`.
- Unsupervised: `StandardScaler`, `SimpleImputer`.
- Supervised selection: `SelectKBest(score_func=f_classif)`.
- Classifiers: `LogisticRegression`, `RandomForestClassifier`, `DummyClassifier`.
- Splitters (no fitting; they produce indices for `take`): `GroupKFold`, `KFold`, `StratifiedKFold`, `train_test_split`. Each has minimum requirements (for example, `GroupKFold` needs `n_splits` ≤ number of groups). **The recorder does not record them yet** (corrected 2026-10-15): `split.class_support` reports them as unavailable.

An operation enters this list only with tests for identity, ancestry, label-use classification and state-dependency propagation. There is no promise to intercept every scikit-learn call, and no universal provenance coverage.

### 4.3 The bounded supported path and what is recorded

The supported path runs from adapter-loaded data, through enumerated operations and `take`, to recorded predictions. On it, the recorder keeps:
1. **Tracked objects.** Every frame or series produced by the adapter, a supported transform or a recorded prediction carries an ancestry record: producing operation and instance, input ancestry, row-ID list hash, and a content fingerprint taken at creation.
2. **Operation and instance identity.** Each supported estimator instance has a stable instance ID. Each `fit` / `fit_transform` / `partial_fit` creates a new **fitted-state version** of that instance.
3. **Fitted-state dependencies.** For each state version, the set of training rows that contributed to it: its own fit-input rows plus the dependency rows of every fitted state upstream in its input's ancestry. Also recorded: `labels_supplied`, and `labels_used` (true only for known supervised components given `y`).
4. **Use events.** Each `transform` / `predict` / `predict_proba` / `decision_function` on a tracked input in fold context *k* records the instance, the state version used, the fold, and the input and output ancestry.
5. **Lineage.** Supported transforms must return outputs whose rows correspond to their input rows, checked per call. `take` preserves the connection to the source rows.

**Coverage gaps** (each gives NOT_ASSESSED with a specific reason, never PASS):
- unexplained mutation: a tracked object's fingerprint changed outside a recorded operation;
- a reconstructed frame: a new object without an ancestry record, *even if its index is valid*;
- an unsupported operation on the path;
- missing prediction ancestry.

A valid pandas index establishes row identity, **not** preprocessing ancestry. **Index preservation alone never establishes `fit.coverage_complete`.**

**Fingerprints** detect unexpected changes to tracked objects. They do not prove that arbitrary Python preprocessing was observed.

**Known limitation (Q3.5, F1).** The recorder runs inside candidate Python. It is not a tamper-proof observation boundary, and missing traces cannot establish that no unobserved fits occurred. Provenance coverage begins at the supplied feature table; upstream feature extraction or normalization is not verified.

## 5 Checks and the evaluation policy

Each check returns `CheckResult`:
- `check_id`, `check_version`;
- `assertions[]`, each with `assertion_id`, status, NOT_ASSESSED reason if any, observed values, evidence refs, and dependencies on other assertions;
- check-level `status`;
- `applicability` (`applicable`, or `not_applicable` with a policy reason);
- `coverage`, `limitations`, `category` (`deployment_mismatch | contamination | instability | missing_evidence | metric_discrepancy`);
- evidence paths and hashes.

A missing field never passes. A check's status is the worst of its required assertions (FAIL > ERROR > NOT_ASSESSED > PASS), and every assertion stays visible.

**Evaluation policy `policy-v1.3` (draft, post-review).**
- v1.1 (2026-10-14) clarified `split.repeated_measures_rule` (DECISIONS.md, "Repeated-measures policy clarification").
- v1.2 (2026-10-14) added the required prerequisite `split.evaluation_folds_nonempty` (DECISIONS.md, "Evaluation-fold prerequisite").
- v1.3 (2026-10-15) defined the T-02 assertions: the window, separation, temporal and reported-metric rules below and in §8 (DECISIONS.md, "T-02 contract dispositions"). Required sets are unchanged.

Runs record the version they were evaluated under. `policy_version` names the rules, not the implementation; task records keep the reviewed commit, and earlier evidence keeps its recorded version.
- R = required.
- R† = required when `claim.sampling_unit` ≠ `row`.
- R* = required when the claim declares the named dependence (or, for the metric row, declares reported metrics).
- D = descriptive only; never affects the outcome.
- — = not applicable.

Applicability comes from the confirmed claim and declared dependence, **never** from which metadata happens to be present (Q2 rule 2).

| Assertion | same_population | unseen_group | future_time | Definition |
| --- | --- | --- | --- | --- |
| `split.evaluation_folds_nonempty` | R | R | R | Assessment prerequisite (v1.2): every declared evaluation fold contains at least one evaluation row. Valid evidence of an empty evaluation partition → NOT_ASSESSED `empty_evaluation`; zero declared folds → NOT_ASSESSED `not_executed`; missing or corrupt split evidence → ERROR; PASS only when every declared evaluation fold is nonempty. An independent valid FAIL still gives `VIOLATION_FOUND`. One row makes a fold assessable; it is not a claim of adequate sample size. |
| `split.no_row_overlap` | R | R | R | No row ID is in both the train and eval partitions of a fold. |
| `split.no_shared_source_observation` | R | R | R | Equal feature+target values identify **candidate** duplicates only. FAIL needs `observation_id` or `known_duplicates` evidence that a train row and an eval row are the same source observation. With identity declared, equal-valued rows with different IDs PASS (candidates reported). Without identity: no candidates → PASS, coverage "exact-value screen only"; unresolved candidates → NOT_ASSESSED `unresolved_duplicate_candidates`. |
| `split.no_group_overlap` | — | R | — | No `group_id` value is in both partitions of a fold. Applies to `group_id`, `unit_id`, `observation_id` and repeated-measures units alike: each rule is judged over known values first; a participating row with a missing (null) value gives NOT_ASSESSED `missing_metadata` only when no violation is already established among known values, and unknown counts are disclosed alongside any FAIL. |
| `split.sampling_unit_disjoint` | R† | R† | R† | No `unit_id` value crosses partitions. Missing `unit_id` → NOT_ASSESSED `missing_metadata`. |
| `split.repeated_measures_rule` | R* (repeated_measures) | R* | R* | v1.1: assessed through an explicit route over rows participating in the declared folds, from the route's own same-fold witnesses; aggregate group/unit statuses are never inherited. **A, sampling unit** (the repeated unit is the declared independent sampling unit): known train/eval unit overlap within each fold; group assignments not required. **B, contained group** (`unseen_group`): an observed unit spanning several groups → NOT_ASSESSED `no_supported_rule`; otherwise group intersections within each fold using only rows with both identifiers known (a `group_separation` witness records fold, row, unit and group IDs; it is not same-unit overlap or label leakage). Per route: a supported witness → FAIL (missing counts disclosed); no witness and missing assignments → NOT_ASSESSED `missing_metadata`; PASS only for a nonempty, complete assessment; no participating rows → NOT_ASSESSED `not_executed`; invalid evidence → ERROR. Known mappings support a witness but never complete containment while assignments are missing; identities are never combined across folds. Neither route → NOT_ASSESSED (`missing_metadata` if `unseen_group` lacks a group column, otherwise `no_supported_rule`). Several declared units: worst status, every unit listed. |
| `split.no_window_overlap` | R* (overlapping_windows) | R* | R* | Windows are `[start, end)` within `stream_id`. Any positive shared span (`max(start) < min(end)`) between a train window and an eval window in the same stream → FAIL. v1.3 routes, per fold. **D, direct:** complete stream identities with no stream in both partitions establish no overlap without using bounds; a stream in both partitions needs usable bounds for its rows (v1.3 lead policy: `start < end`; zero-length or reversed windows are unusable metadata). The basis of each PASS is recorded. **C, documented containment**, used only where D is incomplete: a `window_containment` declaration (`within: group_id`) and a valid `split.no_group_overlap` PASS. Its source, statement and dependency are recorded; it is conditional on the declaration and not independently verified. An observed stream in several groups disables C (→ NOT_ASSESSED `no_supported_rule`) but never suppresses a valid D FAIL or a complete D assessment. Otherwise missing stream identity or bounds → NOT_ASSESSED `missing_metadata` (never guessed). Not proof of statistical independence. |
| `split.temporal_separation` | R* (temporal_order) | R* | — | Verifies the declared `separation_rule` within each fold, two-sided: every train item and eval item in scope are at least `min_gap` apart (equality passes). `times: prediction_time` uses points, distance `abs(t_eval − t_train)`; `times: window` uses intervals, signed gap `max(start_eval − end_train, start_train − end_eval)` (negative = overlap, 0 = adjacent). `per_stream` compares within a known stream; `global` requires `time_basis.scope: global`. The basis is never guessed: an undeclared `times` or a missing named column → NOT_ASSESSED `missing_metadata`. No declared rule → NOT_ASSESSED `no_declared_rule`. It is not a test of statistical independence. |
| `split.class_support` | D | D | D | Per-fold train/eval class counts over the `class_map` keys and absent classes. Splitter minimum requirements are reported as unavailable (not recorded; §4.2). Missing class support is reported, never turned into a split violation. |
| `fit.state_dependencies_within_fold_train` | R | R | R | For every use event in fold *k* (transforms and predictions, on train or eval rows), the dependency rows of the used state version ⊆ train(*k*). Cross-fold reuse of an instance is allowed when this holds. Unknown ancestry → NOT_ASSESSED `unknown_ancestry`, never an invented FAIL. |
| `fit.coverage_complete` | R | R | R | For every declared fold: (1) exactly one written prediction, bound to its actual recorded producer — a `predict` use in the same fold, on the same rows, from an observed supported classifier state — with an artifact hash matching the verified index; (2) fully traced ancestry; (3) no coverage gap on the path (§4.3). Fold inventories in `splits.json`, provenance split events, prediction events and use events must agree; orphaned or missing folds are coverage gaps. Zero recorded fits → NOT_ASSESSED `zero_fit`. A classifier-fit count alone is insufficient. Limit: consistency cannot prove the existence of a fold erased from every source (that needs an independent expected-fold contract). |
| `metric.prediction_ids_match_eval_ids` | R | R | R | Predictions cover exactly the declared eval row IDs of each fold. The expected artifact inventory is exactly `predictions/<fold>.parquet` per declared fold: never inferred from the files that exist, and never remapped by candidate-produced events. A missing or invalid expected artifact, any unexpected prediction path (kept separate and never read as fold data), or an event naming another artifact → ERROR; a valid artifact with wrong row IDs → FAIL (which survives ERRORs elsewhere). |
| `metric.reported_matches_recomputed` | R* (reported_metrics) | R* | R* | §8 comparison rule. |
| `metric.recomputed_primary`, `metric.baselines` | D | D | D | Balanced accuracy / macro-F1 (§8); the most-frequent dummy baseline (§8). The linear baseline is deferred (not computed). |
| `temporal.training_labels_available_by_cutoff` | — | — | R | Every training row in fold *k* has `prediction_time` ≤ cutoff(*k*) and label availability ≤ cutoff(*k*). Requires `time_basis.scope: global` (a single cutoff per fold). |
| `temporal.cutoff_precedes_evaluation` | — | — | R | `temporal_gap` ≥ 0 and cutoff(*k*) + gap ≤ the earliest eval `prediction_time` in fold *k*. Requires `time_basis.scope: global`. |
| `temporal.features_available_when_used` | — | — | R | For every row used and every feature, availability ≤ that row's `prediction_time`. A same-row comparison on the row's declared clock, so it is assessable under any scope (including an unspecified or per-stream one). A feature without an availability entry → NOT_ASSESSED `missing_metadata` unless a valid FAIL exists. |
| `robustness.*` | D | D | D | Range across predeclared seeds/groups; per-group results. Descriptive in V1. |

Notes:
- **`future_time` counterexample (required test):** a training prediction at 100 with label availability 150, and an evaluation prediction at 120, must not PASS.
  - With cutoff 120: `training_labels_available_by_cutoff` FAILs.
  - With cutoff ≥ 150: `cutoff_precedes_evaluation` FAILs.
  - With the cutoff missing: NOT_ASSESSED.
- The time basis (unit and documented reference time) must be consistent across all temporal fields. Inconsistency or absence gives NOT_ASSESSED `missing_metadata` for the dependent assertions.
- **Time values (v1.3):**
  - Rows considered are the train and eval rows of every declared fold.
  - A null, non-numeric, boolean or nonfinite time value makes that row unknown for the assertion. Known values decide first: a witness among known rows → FAIL, with the unknown counts disclosed. Otherwise any unknown participating row → NOT_ASSESSED `missing_metadata`. PASS needs every participating row known.
  - A comparison that needs cross-stream comparability needs `time_basis.scope: global`. Comparisons within a known stream, or within one row, do not.
  - A null fold `training_cutoff` → NOT_ASSESSED `missing_metadata`. A non-numeric, boolean or nonfinite one is invalid candidate-produced evidence → ERROR `evidence_invalid`. A valid FAIL elsewhere still stands.
  - Cutoffs and fold membership are declared by the candidate's code. The checks test the data against those declarations; they do not verify them independently.
- A repeated-measures declaration is not automatically treated as an unseen-group claim.
- Undeclared dependence that exists in the data cannot be detected by policy. This is a stated limitation.
- There is no blanket minimum group count. Overlap assertions can establish violations with any number of groups. Protocol feasibility and class support are reported separately (`split.class_support`).
- Policy files are versioned (`policy_version` in every run). Changing a policy is a code change with review, never a runtime choice.

## 6 Scheduling and run outcome derivation (Q2, F1, F5)

**Scheduling.** The deterministic controller schedules the **full** required assertion set of the policy version for the original evaluation and for each executed candidate. Agent choices cannot remove assertions, and budget exhaustion cannot hide missing results.

**Required set when the manifest snapshot is missing or invalid.** The required set is reconstructed only from trusted context: the project manifest whose SHA-256 equals the snapshot hash recorded in the run index. The missing snapshot stays a reported evidence error: every assertion that would PASS becomes ERROR (`evidence_invalid`), so the run is `INCONCLUSIVE` unless an independently valid FAIL gives `VIOLATION_FOUND`. Without a hash-matching manifest, the run is `INCONCLUSIVE` with reason "required assertion set could not be reconstructed" and no assertion list. The set is never invented, the snapshot is never restored automatically, and nothing defaults to a clean result.

**Finalization.** Every evaluation first removes earlier outputs (`outcome.json`, `report.json`, `checks/`) and their index entries. Normal and recovery paths then share one finalization step, which writes the outputs and indexes exactly those files with current hashes.

**Materialization.** Every required assertion without a computed result is materialized as NOT_ASSESSED with a specific reason:
- `unimplemented_assertion`;
- `not_executed` (including budget exhaustion and execution failure before evidence existed);
- `missing_metadata`;
- `unknown_ancestry`;
- `zero_fit`;
- `coverage_gap`;
- `no_supported_rule`;
- `no_declared_rule`;
- `unresolved_duplicate_candidates`;
- `empty_evaluation` (v1.2: a declared evaluation fold has no evaluation rows).

Invalid, missing or hash-mismatched evidence gives **ERROR**, not NOT_ASSESSED.

```text
if not supported(project, claim):                    -> NOT_SUPPORTED
R := policy.required_assertions(claim)               # full set for the policy version; never agent- or build-selected
materialize every a in R without a result as NOT_ASSESSED(reason)
valid(a) := a's evidence exists, hashes verify, and a does not depend on failed/corrupt evidence
downgrade any FAIL/PASS with not valid(a) to ERROR
if any a in R: a.status == FAIL and valid(a):        -> VIOLATION_FOUND
    (also display every ERROR/NOT_ASSESSED in R prominently as incomplete coverage)
if R is empty or no a in R has a valid PASS/FAIL:    -> INCONCLUSIVE   (empty set never yields NO_VIOLATION_FOUND)
if any a in R: status in {NOT_ASSESSED, ERROR}:      -> INCONCLUSIVE
if all a in R: status == PASS and valid(a):          -> NO_VIOLATION_FOUND (with coverage + limitations shown)
```

A valid FAIL in one assertion is preserved regardless of ERRORs or NOT_ASSESSED elsewhere. A build that has not implemented some required assertions therefore yields `INCONCLUSIVE` for an otherwise clean run; there is no "scoped" clean outcome (F1, T-01). Every outcome is displayed with its plain-language label (PRD) and limitations.

## 7 Runs, evidence, artifacts

- **Run directory:** `runs/<run_id>/` (git-ignored). `run_id` derives from a hash of the project snapshot, the confirmed claim, the policy version and a timestamp.
- **Artifacts:** `manifest.snapshot.json`, `claim.json`, `provenance.jsonl` (ancestry records, fitted-state versions, use events), `splits.json`, `predictions/<fold>.parquet`, `checks/<check_id>.json`, `outcome.json`, `agent_log.jsonl`, `report.json`, `report.md`. Each is hashed into `index.json`.
  - T-01 writes `manifest.snapshot.json`, `execution.json`, `runtime.json`, `provenance.jsonl`, `splits.json`, `predictions/<fold>.parquet`, `checks/<check_id>.json`, `outcome.json`, `report.json` and `index.json`. `claim.json`, `agent_log.jsonl` and `report.md` are not yet produced.
  - From T-02 (policy-v1.3), `outcome.json` and the check files also list **descriptive** results (`split.class_support`, `metric.recomputed_primary`, `metric.baselines`), separately from required assertions. They never enter outcome derivation, and they are marked unavailable when the run's evidence is not confirmed.
  - Fitted-state violations report their **origins**: the fitted states on the recorded ancestry whose own fit rows fall outside the fold's training set (instance/version, class, fit scope, contributing rows, label use, affected folds and uses). Downstream mentions are listed under the one assertion, not counted as separate findings.
- **Integrity:** a missing or hash-mismatched artifact makes dependent assertions ERROR. Assertions with independent evidence keep their valid results. A prediction artifact whose bytes match but that its consumers cannot read (not decodable as Parquet; repeated column names; no `row_id` or `y_pred`; row IDs that are not strings) is likewise invalid for its dependants and recorded in the outcome reason; it never stops finalization (T-06 repair pass 1).
- **Reproducibility:** the report records dependency versions (from `uv.lock`), the evaluator version, the policy version, the adapter version, the model ID and the seed list.
- **Curation:** sanitized example reports are curated explicitly into the repo; raw runs are not committed.

## 8 Trusted evaluator, label stores, metric comparison (Q3.4, Q6, F5)

- The evaluator runs **after** the candidate process exits, in a separate trusted step outside the candidate container. It reads predictions and its own label store.
- **Development-evaluation labels** are part of the project table and visible to the project. The evaluator still scores from its own snapshot copy.
- **Final-holdout labels** and held-out answer keys live only in the evaluator's store. They are never mounted into candidates and never placed in model prompts. For the Q6 held-out cases, the store sits outside this repo and is referenced by path and hash at evaluation time only.
- **Recomputation:** balanced accuracy, macro-F1 and the dummy baseline on identical partitions, with predictions matched by row ID. Never compare across different protocols as if they were identical.
- **Metric definitions (policy-v1.3):**
  - **Class universe:** the `class_map` keys. A true or predicted value maps to a key if it is a string equal to the key, an integer whose decimal form equals it, or an integral finite float (`1.0` → `"1"`). Anything else is invalid: other floats, booleans, null, or a class *name* instead of its key.
  - **Balanced accuracy:** the mean of recall `TP_c/(TP_c+FN_c)` over the classes present in the evaluated true labels.
  - **Macro-F1:** the mean of `2·TP_c/(2·TP_c+FP_c+FN_c)` over the classes present in the evaluated true labels or predictions.
  - **Aggregation:** `single_fold` is one fold's value; `mean_over_folds` is the unweighted mean of per-fold values over every declared fold of the partition; `pooled` is the metric over the concatenated (fold, row) observations, so a row evaluated in several folds counts once per evaluation occurrence.
  - **Completeness:** an empty, invalid or missing required fold is never silently omitted. A fold identifier declared more than once is ambiguous evidence (prediction artifacts are named by fold): every fold with that identifier is unusable (ERROR `evidence_invalid`), and is never overwritten or counted twice. An incomplete aggregate cannot support PASS: it gives ERROR `evidence_invalid` for invalid or missing evidence, and NOT_ASSESSED with the specific reason otherwise. Valid per-fold values are still shown separately. A `final_holdout` entry is NOT_ASSESSED `not_executed` until the evaluator-only holdout label store exists.
  - **Comparison:** `abs(reported − recomputed) <= 1e-6` in float64 (below). A decimal-intended equality may land on either side after binary representation: `5/9 + 1e-6` differs from `5/9` by 1.0000000000287557e-06 and FAILs.
- **Dummy baseline (descriptive):**
  - Each fold's baseline predicts the most frequent class among that fold's training labels from the evaluator's copy, with ties broken by the declared `class_map` order (not claimed to match scikit-learn's tie rule).
  - Empty or invalid training labels make the baseline unavailable for that fold; no prediction is invented.
  - The linear baseline is deferred.
- **Reported-versus-recomputed comparison** (`metric.reported_matches_recomputed`):
  - Each reported metric is a canonical numeric value with a named metric definition, partition, fold (or all) and aggregation.
  - Comparison uses a fixed, versioned **absolute tolerance of 1e-6**, with no relative tolerance.
  - Nonfinite or out-of-range values are rejected.
  - The tolerance is never inferred from the decimal representation of a JSON float, and rounded display text is not the comparison input.
  - This is an engineering comparison rule for deterministic classification scores, not a scientific confidence threshold.
- Development validation can guide a revision. Final-holdout outcomes cannot select candidates or parameters.

## 9 Candidate revisions and approval (Q4)

1. The model emits a unified diff against the immutable original snapshot.
2. **Allowed path:** the manifest's `entry_point` only. Changes are never allowed to the adapter, evaluator, labels, policy, dependencies, manifest, instruction files or anything outside the project snapshot.
3. **Validation (hygiene, not the boundary):** allowed-path check, rejection of symlinks and path escapes, rejection of new files and deletions, a size cap, `ast.parse` of the result, and checking that the diff applies cleanly.
4. **Candidate hash:** `sha256(base_snapshot_hash ‖ resulting entry_point bytes)`.
5. **Approval:** the user explicitly approves one exact candidate. The record is `{candidate_hash, base_snapshot_hash, approved_at}`. The runner refuses to execute unless the hash matches, so any change needs fresh approval.
   - **CLI approval (T-06 lead disposition):** the CLI shows the diff and requires the first 12 hex characters of the candidate hash; the full hash is recorded. With no terminal, the run ends `NEEDS_INPUT` and nothing executes. Implemented in T-06 slice 3 (`agent/approval.py`): the same step authorizes the original before it runs; model-written text is displayed inert (control characters shown as escapes); any input other than the 12-character prefix declines.
   - Waiting for approval is excluded from the active execution budget; total elapsed time is recorded separately. The approved bytes are revalidated before execution.
   - **Preflight (T-06 repair passes 1 and 2):** first, the supplied snapshot must be the approved one (its recorded inventory hashes to its base hash, which is the approval's). Otherwise nothing runs, and the outcome states that the approved required set cannot be reconstructed and lists no assertion: the unapproved snapshot's manifest is never used, intact or offered for recovery. Then the snapshot's manifest must still have the hash recorded when the snapshot was built. A missing, changed or invalid manifest is a recorded refusal before Docker is touched (an execution record, outcome and report). The required set then comes only from a manifest whose canonical bytes have that recorded hash; otherwise the outcome states that the set cannot be reconstructed and lists no assertion.
6. **Execution and re-checking:** the candidate runs only in the isolated runner (§10). The controller then schedules the full required set (§6) on the result. The model never declares success.
7. **Limits:** at most two candidate revisions per run.
8. **Without isolation:** candidates are displayed and labeled "not executed (isolation unavailable)". No host fallback.
9. Container restrictions reduce execution risk. They do not prove provenance integrity or scientific correctness (Q4).

## 10 Isolation contract and runner capability

**Capability states** (shown in the UI and the report):
- `isolated_available`: the contract below is verified by the runner's own tests;
- `trusted_pipeline_only`: repo-authored trusted fixtures and trusted evaluation functions only;
- `unavailable`.

**Container policy (initial adapter: Docker):**
- non-root user;
- read-only root filesystem;
- run-specific writable scratch (tmpfs, size-capped);
- outputs directory with a size cap;
- `--network none`;
- no environment secrets;
- `--cap-drop ALL`;
- `no-new-privileges`;
- memory/CPU/PID limits;
- 30 s candidate timeout and output-size cap;
- no Docker socket;
- mounts limited to the project snapshot (read-only), the adapter/recorder (read-only), scratch, and outputs;
- the dependency image is built separately and pinned (`Dockerfile.runner`).

**Fixture rule:** repo-authored, reviewed trusted fixtures may run in a host subprocess during development. Candidate or generated code never does. A temp directory, `shell=False`, a timeout or a reduced environment is not a sandbox, and neither is the launcher below.
- **Trust** is bound to the fixture's complete file inventory (every file, LF-normalized SHA-256) in `src/atlas/runner/trusted_fixtures.json`. Any extra or changed file is refused before execution.
- **Import resolution is controlled:** the child starts in Python isolated mode (`-I`: safe path, no `PYTHON*` variables, no user site), so neither the fixture directory nor the cwd is on `sys.path`. The parent's resolved `atlas` package directory is inserted explicitly.
- **Evidence:** the child records `runtime.json` (atlas origin, isolated/safe-path flags, path membership). The evaluator verifies and schema-validates `execution.json` and `runtime.json`, and checks them semantically: the expected runner and capability; `isolated=1`, `safe_path=true`; neither the project directory nor the cwd on `sys.path`; and `atlas` imported from the explicitly selected trusted root. Without a verified, completed, import-controlled execution, no PASS is established (it becomes ERROR, or NOT_ASSESSED `not_executed` for a verified non-completion), while valid FAILs from independently verified artifacts stand.

**Docker candidate evidence (T-06 slice 1).** A candidate's evidence reaches the trusted evaluator only through a *candidate view* built on the host after the runner returns (`src/atlas/docker_evidence.py`, `src/atlas/agent/execute.py`):
- **Host-owned records:** `approval.json` and `candidate.json` (written before execution), `execution.json` (a byte copy of the runner's own record), `manifest.snapshot.json` (the snapshot's manifest), `view.json` (the mapping applied) and `index.json`. Collected candidate files enter only through an explicit mapping (`runtime.json`, `provenance.jsonl`, `splits.json`, `predictions/<fold>.parquet`), after their bytes match the hashes the runner recorded at collection. Names that collide with host-owned records (case-insensitively) are rejected, and every view file is created exclusively.
- **Anchors outside the record:** the approval file; the snapshot re-hashed from disk; the staged project and staged code re-hashed from disk (the code must equal the evaluator's own copy of the mounted modules); the trusted runner limits; the `docker run` command rebuilt from those limits and the view's own paths; and the image confirmed by Docker itself (recipe label, non-root user). A limit changed together with its recorded command is refused.
- **Order and mapping:** shared integrity and binding first: the record, the approval, the snapshot, the staged bytes, the configuration, the view record, host-name collisions and indexed files that were never collected. A failure there makes every PASS and FAIL ERROR (`evidence_invalid`): no evidence of that execution can be attributed to the approved candidate. **Individual collected artifacts are separate (T-06 repair pass 1):** the host collection record is the authority for each artifact's hash; an artifact the view lacks (for example, a failed copy), whose indexed hash differs from the collection record, or whose bytes no longer match is unavailable, and only the assertions that depend on it lose their evidence (ERROR), while findings from separately verified artifacts stand. A mismatched artifact is never accepted. Then: `completed` is evaluated normally, with `runtime.json` as corroboration only; `failed`/`timed_out` are verified non-completions (PASS becomes NOT_ASSESSED `not_executed`; FAILs with valid evidence stand; missing or corrupt evidence stays ERROR); `collection_failed`, `cleanup_failed` and `runner_error` establish no PASS (ERROR); `refused` and `not_executed` produce no evidence, so every required assertion is NOT_ASSESSED `not_executed` and the outcome is INCONCLUSIVE.
- **Limits of these checks:** matching hashes establish consistency, not authenticity against an attacker who controls the host. Container evidence remains candidate-produced (§9.9). The trusted-fixture path is unchanged; a run without the view marker is checked only as trusted-fixture evidence, which a Docker record cannot satisfy.

Any other runtime must pass the same contract tests before it replaces Docker. Isolation reduces risk and is not a claim that hostile code is safe; the public demo remains curated.

## 11 Agent loop and model integration

- **States:** `INTAKE → CONTRACT_REVIEW → INSPECT → CHECK → PROPOSE_PATCH → (APPROVAL) → EXECUTE → VERIFY → REPORT`, with optional `SAVE_PROCEDURE`. Any state can end in `NEEDS_INPUT`, `NOT_SUPPORTED`, `BUDGET_EXHAUSTED` or `ERROR`. `CHECK` and `VERIFY` always run the controller's full required set (§6), whatever the agent chose.
- **Tools (typed, normalized paths, no shell):** `list_project_files`, `read_project_file`, `profile_table`, `run_check`, `propose_patch`, `evaluate_candidate` (approval-gated), `inspect_evidence`, `retrieve_procedure`, `propose_procedure`. `run_check` can add inspection; it cannot remove scheduled assertions.
- **Ceilings (initial; tune only with measurements, recorded in DECISIONS.md):** 6 model calls, 12 tool operations, 1 retry per transient model call, 2 candidate revisions, 5 min per run, 30 s per candidate execution. On exhaustion, unscheduled or incomplete required assertions are materialized as NOT_ASSESSED `not_executed`. Waiting for human approval is excluded from the active run budget; total elapsed time is recorded separately (T-06 lead disposition). The per-stage token ceilings in `docs/HOSTING_PROBE.md` remain proposed until reviewed before live execution.
- **Model:** one verified NVIDIA model via Nebius (`NEBIUS_BASE_URL`, `ATLAS_MODEL_PRIMARY`; `.env.example`). IDs come only from the authenticated `GET /models`.
  - **Client (T-06 slice 3, offline-verified only):** `agent/nebius.py`, SDK retries disabled (the controller owns retries and the six-attempt limit), explicit timeout, every ceiling and price required in configuration, a conservative pre-send input bound, usage above a ceiling failing closed, errors classified by type and status only, and conservative cost accounting (`budget.CostLedger`: the ceiling cost stays reserved when a dispatched request's usage is unknown). The per-call ceiling values and the input-bound approach are open lead decisions before any live run (TASKS.md T-06 slice 3).
  - Structured JSON output where supported, validated by Pydantic, with a deterministic dispatcher.
  - Invalid output is a recorded schema failure, never an unconstrained fallback. A schema failure terminates the model attempt without an action and without a format-repair retry; completed audit results remain intact (T-06 lead disposition).
  - `ATLAS_MODEL_MODE=fixture` runs are visibly labeled non-live.
- **Prompt inputs:** contract, relevant snippets, check summaries, allowed actions, artifact references. Public/synthetic summaries only; never final-holdout labels or answer keys. Source files and logs are untrusted data.
- **Logged per call:** model ID, parameters, request ID if returned, usage, timestamps, elapsed time, retries, schema failures, chosen tool, result.
- **Modes (Q4):**
  - `audit`: deterministic; no model; detection and reporting only.
  - `agent`: the bounded patch workflow. The original and every candidate run in Docker; original execution is explicitly authorized and bound to its snapshot (T-06 lead disposition).
  - `agent+memory`: the same as `agent`, plus `retrieve_procedure`. Retrieval and prerequisite checks count toward its budget.
  - The agent modes are matched on inputs, policy, tools, model settings and budgets.

## 12 Procedures (Q4, L1; playbook §8)

- **Record:** JSON following the playbook §8 example: claim pattern, schema prerequisites, verification assertions, patch template (constrained recipe with parameters and allowed paths), invalidation conditions, provenance and validation. Records are immutable once versioned.
- **Admission (L1):** the model may propose. Only the trusted validator sets `verified_for_recorded_scope`, and only when:
  - **every applicable required assertion has a valid PASS** on the corrected evaluation (no FAIL, ERROR or NOT_ASSESSED);
  - the required set is non-empty and coverage is complete;
  - the template hash, evaluator version and policy version resolve;
  - provenance is complete.
- **Retrieval:** metadata filter first, then optional ranking. The result carries explicit applicability reasons. Text similarity never overrides a schema, claim-type or temporal mismatch.
- **Reuse:**
  - A claim-type mismatch rejects reuse (`reuse_rejected(claim_mismatch)`) before any execution. A temporal-feature violation is reported separately, and only when its check actually establishes one.
  - Prerequisites are re-checked and the template is bound to the new schema.
  - The rendered candidate goes through §9 (validation, hash-bound approval, isolation).
  - `reuse_succeeded` requires the same full required set to have valid PASSes **after execution**. Otherwise the outcome is `reuse_rejected(failed_prerequisite | failed_assertion)`.
- **After a rejected reuse:** a later fresh repair is recorded separately (`fresh_attempt_after_rejection`), never counted as reuse.
- **Optional guidance:** memory is never a forced template.

## 13 Hosting and access (Q5)

| Mode | Executes | Required labeling |
| --- | --- | --- |
| Limited hosted (baseline) | Curated examples; trusted, reviewed evaluation functions with schema-validated parameters; live capped model calls via server-side key | Generated diffs: "not executed here". Corrected-protocol results: "computed by ATLAS's trusted evaluation functions", never presented as validating the displayed diff |
| Full hosted (only if the probe demonstrates it) | Candidate execution on a separately isolated worker meeting §10 | Same isolation evidence as local |
| Local build | Full workflow | Capability state shown |

**Server-side controls:**
- per-session, per-route and daily caps;
- a reserved judge route or capacity that public traffic can't exhaust;
- defined behavior on budget exhaustion and a restoration procedure through Dec 15, 2026;
- replay only as a disclosed fallback.

Keys never reach the browser, prompts, fixtures, Git or candidate containers. The open checks are listed in DECISIONS.md.

**Decided (2026-10-16, DECISIONS.md "T-03 hosting decisions"):**
- V1 is limited hosted plus full local Docker execution; full hosted is a stretch goal.
- The budget store is Neon Postgres. The server-side controls above are planned, not yet built.
- The hosted app is not "ready" until Nebius connectivity from the host and the full locked-environment build on the host are tested (T-12).

## 14 Step 8 dispositions and remaining gated questions

Gemini findings F1–F5 and lead findings L1–L2 were recorded in DECISIONS.md on 2026-10-14 and applied throughout this file. The reviewed packet `handoffs/science-01.md` is preserved unchanged as the snapshot that was reviewed.

| Open item | Owner | Gate | Until resolved |
| --- | --- | --- | --- |
| Implementation of `split.no_window_overlap`, `split.temporal_separation`, the three `temporal.*` assertions and `metric.reported_matches_recomputed` (contract decided 2026-10-15: DECISIONS.md "T-02 contract dispositions"; policy-v1.3) | Claude (T-02) | T-02 acceptance | Under policy-v1.2: NOT_ASSESSED `unimplemented_assertion` |
| Synthetic 2×2 generator settings (subjects, sessions, windows, signal and confounding strengths, seeds) | Claude proposes; lead approves | Fixed and recorded **before any benchmark measurement** (T-01 test fixtures excepted, which are recorded but not measurements) | No benchmark result is reported |
| UCI HAR containment evidence for windows within subjects; attribution text | Claude (T-09); lead review | T-09 acceptance | `split.no_window_overlap` stays NOT_ASSESSED on that dataset |
| Expected violated assertion IDs per labeled case (answer keys) for scoring | Lead/Codex (authors) | Before any scored measurement (T-10, T-11) | No precision/recall reported |
| Frozen procedure-store hash for the transfer repetitions | Claude (T-11) | Before the first T-11 repetition | T-11 does not start |
| Hosting and access checks | Claude (T-03); lead decides | Before choosing a host or paid usage | Limited hosted baseline |

Closed by Step 8: the T-01 outcome policy (no scoped clean outcome; §6); the instrumentation contract (§4.3); duplicate semantics; the window and `future_time` rules; the metric tolerance; procedure admission; no blanket group minimum; robustness descriptive in V1.

Closed by the lead on 2026-10-15 (DECISIONS.md, "Repeated-measures scope for V1"): V1 adds no repeated-measures rule beyond routes A (sampling unit) and B (contained group) of `split.repeated_measures_rule`. Other repeated-measures structures stay NOT_ASSESSED `no_supported_rule`.

## 15 Known limitations (to be stated in the README and reports)

- Fit provenance covers only the bounded supported path. The in-process recorder is not tamper-proof, fingerprints don't prove arbitrary preprocessing was observed, and missing traces don't prove absence.
- Provenance begins at the supplied feature table; upstream feature extraction and normalization are not verified.
- Policy cannot detect dependence the user did not declare. Some declared dependence has no supported rule in V1 and stays NOT_ASSESSED.
- Duplicate detection without source-observation identity is an exact-value screen and can leave unresolved candidates.
- Temporal assertions verify declared availability and separation rules, and `split.no_window_overlap` verifies declared stream identity and window intervals. None of them is proof of statistical independence, and reports must not present them as such.
- A green outcome means only that the listed assertions passed within the stated coverage.
- Held-out evidence comes from two cases: limited and descriptive. Their separation is procedural, not access-enforced.
- Container isolation reduces risk; it is not proof of safety, provenance integrity or scientific correctness.

## 16 Proposed CLI (playbook §10)

Implemented: `python -m atlas.cli audit <project> --mode audit` (T-01) and `--mode agent --fixture-script FILE` (T-06 slice 3: fixture replies only; live mode refused). The rest is proposed.

```text
atlas doctor
atlas audit <project> --mode audit|agent|agent+memory
atlas compare <run_id_a> <run_id_b>
atlas procedures check <procedure_id> <project>
atlas evaluate --suite acceptance
```

## 17 Evaluation protocol rules (F2, F4, F5)

**Synthetic 2×2 benchmark (F2).**
- All four runs use the same generated dataset and the predeclared seeds. Generator settings are fixed and recorded before measurement; no settings are adopted from review examples as scientifically established.
- Within each split protocol (random or grouped), the global and fold-local preprocessing runs use identical train/eval partitions and matched model settings.
- Across split protocols, differences are shown explicitly as protocol differences. Score subtraction is not claimed to isolate a causal contribution.
- Planted violations are demonstrated with overlap and fitted-state-dependency evidence. A score drop, changed selected features or changed predictions are not required. Zero and reversed score differences are reported as measured.
- Robustness is descriptive in V1.

**UCI HAR example (F4).**
- Claim `unseen_group` by subject.
- The official subject-based test partition is reserved from development and tuning; development uses grouped folds within the training subjects.
- Any deliberately flawed evaluation is described as ATLAS-authored, not as a flaw alleged in the original study.
- `split.no_window_overlap` may PASS through disjoint groups only with documented containment evidence (§5); otherwise it stays NOT_ASSESSED.
- Provenance coverage begins at the supplied feature table.
- With no timestamps in the dataset, temporal assertions can't be established. The general rule for missing evidence is unchanged.
- Source: https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones. The lead verified on 2026-10-14 that it documents subject-based splitting, overlapping windows and a CC BY 4.0 license; attribution is required. Global fitting of upstream normalization has **not** been established.

**Finding-level scoring (F5).**
- Findings are scored per case and canonical assertion ID. Repeated mentions are deduplicated, and fold-level evidence is retained.
- Expected violated assertion IDs per labeled case are defined before measurement.
- Report TP/FP/FN, coverage gaps (NOT_ASSESSED) and errors separately.
- On clean cases, report false-positive counts and the false-violation run rate (the share of clean runs whose outcome is `VIOLATION_FOUND`).
- When a denominator is zero, precision or recall is reported as undefined, never manufactured.

**Matched agent comparison (F5).**
- Freeze and hash the procedure store before the three paired transfer repetitions.
- Each repetition uses the same immutable store and fresh run state. No target-specific procedures are admitted between repetitions.
- Report all scheduled trials, failures, budgets and procedure-creation costs.
- Three repetitions support descriptive observations only, not significance or broad generalization.
