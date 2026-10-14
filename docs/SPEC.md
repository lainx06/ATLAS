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
ProjectManifest (schema_version "0.2", draft)
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
  time_basis            required for future_time and for window/temporal rules: {unit, reference_time (documented)}
  feature_availability  future_time: per feature, either an availability-time column or an offset from prediction_time
  label_availability    future_time: an availability-time column, or {horizon, reporting_delay} added to prediction_time
  temporal_gap          future_time: declared nonnegative gap (time-basis units)
  separation_rule       optional: declared temporal separation rule for temporal_order dependence {scope: global|per_stream, min_gap}
  known_duplicates      optional: documented groups of row IDs that are the same source observation
  claim:
    type                same_population | unseen_group | future_time
    statement           the user's plain-language claim (kept verbatim)
    sampling_unit       row | window | session | subject | other(text)
    dependence          list of: none_declared | repeated_measures(column) | overlapping_windows | temporal_order | other(text)
  primary_metric        balanced_accuracy | macro_f1
  development_seeds     predeclared list (robustness)
  entry_point           path relative to project root (allowed path for candidates)
  reported_metrics      optional list of {metric_definition, partition, fold|all, aggregation, value} (canonical numeric; §8)
```

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
| `take(obj, row_ids)` | **Supported row selection.** Returns a tracked subset of a tracked frame/series. `row_ids` must be a subset of `obj`'s rows. Splitter output is turned into row IDs and passed through `take`. |
| `declare_split(fold, train_ids, eval_ids, kind[, training_cutoff])` | Opens fold context `fold`. `kind` ∈ {development_eval, final_holdout}. `training_cutoff` is required for `future_time`. Validated: IDs exist, no duplicates within a list. |
| `write_predictions(fold, row_ids, y_pred[, y_score])` | Writes predictions keyed by row ID. Validated against the declared `eval_ids`. `y_pred` must be a tracked output of a recorded prediction use in that fold; otherwise prediction ancestry is missing (a coverage gap). |

### 4.2 Supported operations (initial enumerated list; tested before being claimed)

- Adapter: `load_table`, `load_holdout_features`, `take`, `declare_split`, `write_predictions`.
- Composition: `Pipeline`.
- Unsupervised: `StandardScaler`, `SimpleImputer`.
- Supervised selection: `SelectKBest(score_func=f_classif)`.
- Classifiers: `LogisticRegression`, `RandomForestClassifier`, `DummyClassifier`.
- Splitters (no fitting; they produce indices for `take`): `GroupKFold`, `KFold`, `StratifiedKFold`, `train_test_split`. Each records its minimum requirements (for example, `GroupKFold` needs `n_splits` ≤ number of groups).

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

**Evaluation policy `policy-v1` (draft, post-review).**
- R = required.
- R† = required when `claim.sampling_unit` ≠ `row`.
- R* = required when the claim declares the named dependence (or, for the metric row, declares reported metrics).
- D = descriptive only; never affects the outcome.
- — = not applicable.

Applicability comes from the confirmed claim and declared dependence, **never** from which metadata happens to be present (Q2 rule 2).

| Assertion | same_population | unseen_group | future_time | Definition |
| --- | --- | --- | --- | --- |
| `split.no_row_overlap` | R | R | R | No row ID is in both the train and eval partitions of a fold. |
| `split.no_shared_source_observation` | R | R | R | Equal feature+target values identify **candidate** duplicates only. FAIL needs `observation_id` or `known_duplicates` evidence that a train row and an eval row are the same source observation. With identity declared, equal-valued rows with different IDs PASS (candidates reported). Without identity: no candidates → PASS, coverage "exact-value screen only"; unresolved candidates → NOT_ASSESSED `unresolved_duplicate_candidates`. |
| `split.no_group_overlap` | — | R | — | No `group_id` value is in both partitions of a fold. |
| `split.sampling_unit_disjoint` | R† | R† | R† | No `unit_id` value crosses partitions. Missing `unit_id` → NOT_ASSESSED `missing_metadata`. |
| `split.repeated_measures_rule` | R* (repeated_measures) | R* | R* | Assessed only through a supported rule. The unit equals the sampling unit → follows `sampling_unit_disjoint`. Under `unseen_group`, the unit is contained in groups (containment shown from the table) → follows `no_group_overlap`. Otherwise NOT_ASSESSED `no_supported_rule`. The dependency is recorded. |
| `split.no_window_overlap` | R* (overlapping_windows) | R* | R* | Windows are `[start, end)` within `stream_id`. Any positive shared span between a train window and an eval window in the same stream → FAIL. Missing stream identity or bounds → NOT_ASSESSED `missing_metadata` (never guessed). PASS via disjoint groups is allowed only with documented containment evidence that streams cannot cross groups; that evidence and the dependency on `no_group_overlap` PASS are recorded. |
| `split.temporal_separation` | R* (temporal_order) | R* | — | Verifies the declared `separation_rule` (a minimum gap between train and eval times, globally or per stream). It is not a test of statistical independence. No declared rule → NOT_ASSESSED `no_declared_rule`. |
| `split.class_support` | D | D | D | Per-fold class counts and the splitter/estimator minimum requirements. Missing class support is reported, never turned into a split violation. |
| `fit.state_dependencies_within_fold_train` | R | R | R | For every use event in fold *k* (transforms and predictions, on train or eval rows), the dependency rows of the used state version ⊆ train(*k*). Cross-fold reuse of an instance is allowed when this holds. Unknown ancestry → NOT_ASSESSED `unknown_ancestry`, never an invented FAIL. |
| `fit.coverage_complete` | R | R | R | For every evaluated fold: (1) at least one observed supported classifier fit whose state produced the written predictions; (2) traceable prediction ancestry; (3) no coverage gap on the path (§4.3). Zero recorded fits → NOT_ASSESSED `zero_fit`. A classifier-fit count alone is insufficient. |
| `metric.prediction_ids_match_eval_ids` | R | R | R | Predictions cover exactly the declared eval row IDs of each fold. |
| `metric.reported_matches_recomputed` | R* (reported_metrics) | R* | R* | §8 comparison rule. |
| `metric.recomputed_primary`, `metric.baselines` | D | D | D | Balanced accuracy / macro-F1; dummy baseline (linear where appropriate). |
| `temporal.training_labels_available_by_cutoff` | — | — | R | Every training row in fold *k* has `prediction_time` ≤ cutoff(*k*) and label availability ≤ cutoff(*k*). |
| `temporal.cutoff_precedes_evaluation` | — | — | R | `temporal_gap` ≥ 0 and cutoff(*k*) + gap ≤ the earliest eval `prediction_time` in fold *k*. |
| `temporal.features_available_when_used` | — | — | R | For every row used and every feature, availability ≤ that row's `prediction_time`. |
| `robustness.*` | D | D | D | Range across predeclared seeds/groups; per-group results. Descriptive in V1. |

Notes:
- **`future_time` counterexample (required test):** a training prediction at 100 with label availability 150, and an evaluation prediction at 120, must not PASS.
  - With cutoff 120: `training_labels_available_by_cutoff` FAILs.
  - With cutoff ≥ 150: `cutoff_precedes_evaluation` FAILs.
  - With the cutoff missing: NOT_ASSESSED.
- The time basis (unit and documented reference time) must be consistent across all temporal fields. Inconsistency or absence gives NOT_ASSESSED `missing_metadata` for the dependent assertions.
- A repeated-measures declaration is not automatically treated as an unseen-group claim.
- Undeclared dependence that exists in the data cannot be detected by policy. This is a stated limitation.
- There is no blanket minimum group count. Overlap assertions can establish violations with any number of groups. Protocol feasibility and class support are reported separately (`split.class_support`).
- Policy files are versioned (`policy_version` in every run). Changing a policy is a code change with review, never a runtime choice.

## 6 Scheduling and run outcome derivation (Q2, F1, F5)

**Scheduling.** The deterministic controller schedules the **full** required assertion set of the policy version for the original evaluation and for each executed candidate. Agent choices cannot remove assertions, and budget exhaustion cannot hide missing results.

**Materialization.** Every required assertion without a computed result is materialized as NOT_ASSESSED with a specific reason:
- `unimplemented_assertion`;
- `not_executed` (including budget exhaustion and execution failure before evidence existed);
- `missing_metadata`;
- `unknown_ancestry`;
- `zero_fit`;
- `coverage_gap`;
- `no_supported_rule`;
- `no_declared_rule`;
- `unresolved_duplicate_candidates`.

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
- **Integrity:** a missing or hash-mismatched artifact makes dependent assertions ERROR. Assertions with independent evidence keep their valid results.
- **Reproducibility:** the report records dependency versions (from `uv.lock`), the evaluator version, the policy version, the adapter version, the model ID and the seed list.
- **Curation:** sanitized example reports are curated explicitly into the repo; raw runs are not committed.

## 8 Trusted evaluator, label stores, metric comparison (Q3.4, Q6, F5)

- The evaluator runs **after** the candidate process exits, in a separate trusted step outside the candidate container. It reads predictions and its own label store.
- **Development-evaluation labels** are part of the project table and visible to the project. The evaluator still scores from its own snapshot copy.
- **Final-holdout labels** and held-out answer keys live only in the evaluator's store. They are never mounted into candidates and never placed in model prompts. For the Q6 held-out cases, the store sits outside this repo and is referenced by path and hash at evaluation time only.
- **Recomputation:** balanced accuracy, macro-F1 and the dummy baseline on identical partitions, with predictions matched by row ID. Never compare across different protocols as if they were identical.
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

**Fixture rule:** repo-authored, reviewed trusted fixtures, identified by a hash allowlist, may run in a host subprocess during development. Candidate or generated code never does. A temp directory, `shell=False`, a timeout or a reduced environment is not a sandbox.

Any other runtime must pass the same contract tests before it replaces Docker. Isolation reduces risk and is not a claim that hostile code is safe; the public demo remains curated.

## 11 Agent loop and model integration

- **States:** `INTAKE → CONTRACT_REVIEW → INSPECT → CHECK → PROPOSE_PATCH → (APPROVAL) → EXECUTE → VERIFY → REPORT`, with optional `SAVE_PROCEDURE`. Any state can end in `NEEDS_INPUT`, `NOT_SUPPORTED`, `BUDGET_EXHAUSTED` or `ERROR`. `CHECK` and `VERIFY` always run the controller's full required set (§6), whatever the agent chose.
- **Tools (typed, normalized paths, no shell):** `list_project_files`, `read_project_file`, `profile_table`, `run_check`, `propose_patch`, `evaluate_candidate` (approval-gated), `inspect_evidence`, `retrieve_procedure`, `propose_procedure`. `run_check` can add inspection; it cannot remove scheduled assertions.
- **Ceilings (initial; tune only with measurements, recorded in DECISIONS.md):** 6 model calls, 12 tool operations, 1 retry per transient model call, 2 candidate revisions, 5 min per run, 30 s per candidate execution. On exhaustion, unscheduled or incomplete required assertions are materialized as NOT_ASSESSED `not_executed`.
- **Model:** one verified NVIDIA model via Nebius (`NEBIUS_BASE_URL`, `ATLAS_MODEL_PRIMARY`; `.env.example`). IDs come only from the authenticated `GET /models`.
  - Structured JSON output where supported, validated by Pydantic, with a deterministic dispatcher.
  - Invalid output is a recorded schema failure, never an unconstrained fallback.
  - `ATLAS_MODEL_MODE=fixture` runs are visibly labeled non-live.
- **Prompt inputs:** contract, relevant snippets, check summaries, allowed actions, artifact references. Public/synthetic summaries only; never final-holdout labels or answer keys. Source files and logs are untrusted data.
- **Logged per call:** model ID, parameters, request ID if returned, usage, timestamps, elapsed time, retries, schema failures, chosen tool, result.
- **Modes (Q4):**
  - `audit`: deterministic; no model; detection and reporting only.
  - `agent`: the bounded patch workflow.
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

## 14 Step 8 dispositions and remaining gated questions

Gemini findings F1–F5 and lead findings L1–L2 were recorded in DECISIONS.md on 2026-10-14 and applied throughout this file. The reviewed packet `handoffs/science-01.md` is preserved unchanged as the snapshot that was reviewed.

| Open item | Owner | Gate | Until resolved |
| --- | --- | --- | --- |
| Whether V1 adds a supported rule for repeated measures not covered by unit or group disjointness | Lead (Gemini consulted if needed) | Before T-02 acceptance | `split.repeated_measures_rule` → NOT_ASSESSED `no_supported_rule` |
| Implementation of `split.no_window_overlap`, `split.temporal_separation`, the three `temporal.*` assertions and `metric.reported_matches_recomputed` | Claude (T-02) | T-02 acceptance | NOT_ASSESSED `unimplemented_assertion` |
| Synthetic 2×2 generator settings (subjects, sessions, windows, signal and confounding strengths, seeds) | Claude proposes; lead approves | Fixed and recorded **before any benchmark measurement** (T-01 test fixtures excepted, which are recorded but not measurements) | No benchmark result is reported |
| UCI HAR containment evidence for windows within subjects; attribution text | Claude (T-09); lead review | T-09 acceptance | `split.no_window_overlap` stays NOT_ASSESSED on that dataset |
| Expected violated assertion IDs per labeled case (answer keys) for scoring | Lead/Codex (authors) | Before any scored measurement (T-10, T-11) | No precision/recall reported |
| Frozen procedure-store hash for the transfer repetitions | Claude (T-11) | Before the first T-11 repetition | T-11 does not start |
| Hosting and access checks | Claude (T-03); lead decides | Before choosing a host or paid usage | Limited hosted baseline |

Closed by Step 8: the T-01 outcome policy (no scoped clean outcome; §6); the instrumentation contract (§4.3); duplicate semantics; the window and `future_time` rules; the metric tolerance; procedure admission; no blanket group minimum; robustness descriptive in V1.

## 15 Known limitations (to be stated in the README and reports)

- Fit provenance covers only the bounded supported path. The in-process recorder is not tamper-proof, fingerprints don't prove arbitrary preprocessing was observed, and missing traces don't prove absence.
- Provenance begins at the supplied feature table; upstream feature extraction and normalization are not verified.
- Policy cannot detect dependence the user did not declare. Some declared dependence has no supported rule in V1 and stays NOT_ASSESSED.
- Duplicate detection without source-observation identity is an exact-value screen and can leave unresolved candidates.
- Temporal assertions verify declared availability and separation rules, not statistical independence.
- A green outcome means only that the listed assertions passed within the stated coverage.
- Held-out evidence comes from two cases: limited and descriptive. Their separation is procedural, not access-enforced.
- Container isolation reduces risk; it is not proof of safety, provenance integrity or scientific correctness.

## 16 Proposed CLI (not implemented; playbook §10)

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
