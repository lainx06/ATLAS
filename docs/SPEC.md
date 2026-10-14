# ATLAS technical specification (V1, LENS)

Status: **pending scientific review** (Step 8 packet: `handoffs/science-01.md`). Step 7 draft, 2026-10-14. These are proposed contracts, **not implemented** and not accepted until the Step 8 dispositions are recorded. Product requirements are in `docs/PRD.md`; vocabulary in `GLOSSARY.md`; decision history in `DECISIONS.md` (Q1–Q6). Anything marked *(Step 8)* is an open scientific question (§14).

## 1 Conventions

- "Planned" means specified here, not built. No command in this file exists yet unless it is marked existing.
- Check statuses: `PASS | FAIL | NOT_ASSESSED | ERROR`.
- Run outcomes: `NOT_SUPPORTED | VIOLATION_FOUND | INCONCLUSIVE | NO_VIOLATION_FOUND`.
- Contracts are Pydantic models serialized to JSON. Every contract has a `schema_version`, and evidence artifacts carry SHA-256 hashes.
- The engine (`src/atlas/`) is independent of the UI (`app.py`). The UI only calls engine APIs and renders their results.

## 2 Modules (planned layout, from playbook §5/§10)

| Module | Owns | Must not |
| --- | --- | --- |
| `atlas.contracts` | Manifest, claim, check, run, candidate, procedure, policy schemas | — |
| `atlas.intake` | File/schema inventory, manifest validation, supportedness decision | Trust repository instructions or guess ground truth |
| `atlas.adapter` + `atlas.recorder` | Candidate-side data loading, split/prediction declaration, fit tracing (§4) | Score anything; hold final-holdout labels |
| `atlas.checks.*` | The five checks (§5) | Free-form judgments |
| `atlas.policy` | Versioned evaluation policy and outcome derivation (§6) | Accept agent-selected assertion subsets |
| `atlas.evaluator` | Trusted metric recomputation and label stores (§8) | Run inside the candidate process |
| `atlas.runner` | Snapshots, isolated execution, capability reporting (§10) | Fall back to host execution of candidate code |
| `atlas.agent` | Nebius client, bounded state machine, typed tools (§11) | Execute raw shell; declare success |
| `atlas.procedures` | Admission, applicability, retrieval, versioning (§12) | Reuse on textual similarity |
| `atlas.reports`, `atlas.cli` | Evidence export, repeatable commands | Hide failures, replay or limits |

## 3 Project manifest and claim

A supported project directory contains `atlas_manifest.json`, a table (`.csv`/`.parquet`) and an entry script (default `evaluate.py`).

```text
ProjectManifest (schema_version "0.1", draft)
  table: path, format (csv|parquet)
  columns:
    row_id            required, unique
    target            required; class_map required (classification only)
    features          explicit list (no implicit "all other columns")
    group_id          required for unseen_group; optional otherwise
    prediction_time   required for future_time
    feature_available_time: per-feature column or per-feature lag declaration (future_time)  (Step 8: exact form)
    label_horizon     required for future_time
    window_start / window_end   optional; required when dependence includes overlapping_windows
  claim:
    type              same_population | unseen_group | future_time
    statement         the user's plain-language claim (kept verbatim)
    sampling_unit     row | window | session | subject | other(text)
    dependence        list of: none_declared | repeated_measures(group col) | overlapping_windows | temporal_order | other(text)
  primary_metric      balanced_accuracy | macro_f1
  development_seeds   predeclared list (robustness)
  entry_point         path relative to project root (allowed-path for candidates)
  reported_metrics    optional {metric: value} the project claims  (Step 8: comparison tolerance)
```

**Supportedness (run-level).** The run outcome is `NOT_SUPPORTED` when any of these hold:
- the claim type is not one of the three, or is combined;
- the task is not classification;
- the manifest or table is absent or unparseable;
- the table format is unsupported;
- the entry point doesn't use the adapter at all.

In the last case, static suspicions may still be shown; they never change statuses (Q3). Missing *metadata* for a supported claim type is **not** NOT_SUPPORTED: the affected required assertions become NOT_ASSESSED (Q1, Q2 rule 2).

**Claim confirmation.** The model may pre-fill a `Claim` from the statement. It is a proposal until the user confirms it. Only a confirmed claim reaches the policy, and an edit invalidates any prior results for the run.

## 4 Adapter, supported operations, lineage (Q3)

### 4.1 Adapter API (candidate side, read-only package mounted into the container)

| Call | Contract |
| --- | --- |
| `load_table()` | Returns `(X: DataFrame, y: Series)` for **development** rows. Index = `row_id` (unique, validated against the manifest). `X` holds only the declared feature columns. |
| `load_holdout_features()` | Returns final-holdout `X` only (no target), for evaluation runs. Holdout labels never enter the container (§8). |
| `declare_split(fold, train_ids, eval_ids, kind)` | Opens fold context `fold`. `kind` ∈ {development_eval, final_holdout}. Validated: IDs exist, no duplicates within a list. |
| `write_predictions(fold, row_ids, y_pred[, y_score])` | Writes predictions keyed by row ID to the run output directory. Validated against the declared `eval_ids`. |

### 4.2 Supported operations (initial enumerated list; tested before being claimed)

- Composition: `Pipeline`.
- Unsupervised: `StandardScaler`, `SimpleImputer`.
- Supervised selection: `SelectKBest(score_func=f_classif)`.
- Classifiers: `LogisticRegression`, `RandomForestClassifier`, `DummyClassifier`.
- Splitters (no fitting; read for split evidence only): `GroupKFold`, `KFold`, `StratifiedKFold`, `train_test_split` (sklearn.model_selection).

An operation enters this list only with tests for attribution, lineage preservation and label-use classification. There is no promise to intercept every scikit-learn fit (Q3.1).

### 4.3 Recording and lineage rules

1. The recorder wraps `fit`, `fit_transform` and `partial_fit` of the supported classes and sets scikit-learn `transform_output="pandas"`.
2. **Attributable input:** `X` is a DataFrame whose index is unique and a subset of the table's row IDs. If `y` is supplied, its index equals `X`'s index. Anything else is recorded as an `unattributable` fit, which is a coverage gap.
3. Each fit produces a **fit trace**:
   - component class and parameters hash;
   - fold context (the open fold, or `global` if fit outside any fold context);
   - the supplied row-ID set (sorted list plus hash);
   - `labels_supplied` (bool);
   - `labels_used`: true only when the component is on the known-supervised list (e.g. `SelectKBest(f_classif)`, classifiers) and `y` was supplied;
   - call order.
4. **Transform lineage:** for supported transforms, the output index must equal the input index; this is checked on every recorded call. A mismatch, reset or rebuilt index is a lineage break, so affected traces are unverifiable and cannot PASS (Q3.2).
5. A supported-class fit on an attributable input whose ancestry crossed an unsupported operation is recorded as `unsupported_component`, which is a coverage gap.
6. **Coverage:** the run records counts of attributable, unattributable and unsupported fits. Any gap makes the coverage assertion (§5) NOT_ASSESSED.
7. **Known limitation (Q3.5, documented):** the recorder runs inside candidate Python. It is **not** a tamper-proof observation boundary, and missing traces cannot establish that no unobserved fits occurred. Exact instrumentation and bypass tests are a Step 8 item and must be agreed before the recorder's implementation is accepted.

## 5 Checks and the draft evaluation policy

Each check returns `CheckResult`:
- `check_id`, `check_version`;
- `assertions[]`, each with `assertion_id`, status, observed values and evidence refs;
- check-level `status`;
- `applicability` (`applicable`, or `not_applicable` with a policy reason);
- `coverage`, `limitations`, `category` (`deployment_mismatch | contamination | instability | missing_evidence | metric_discrepancy`);
- evidence paths and hashes.

A missing field never passes. A check's status is the worst of its required assertions (FAIL > ERROR > NOT_ASSESSED > PASS), and every assertion stays visible.

**Draft evaluation policy `policy-v0`.** R = required, R* = required when the claim declares the matching dependence, D = descriptive only, — = not applicable. Applicability comes from the confirmed claim and declared dependence, **never** from which metadata happens to be present (Q2 rule 2).

| Assertion | same_population | unseen_group | future_time |
| --- | --- | --- | --- |
| `split.no_row_overlap` (train vs eval row IDs) | R | R | R |
| `split.no_exact_duplicate_across_partitions` (identical feature+target vectors, different IDs) | R | R | R |
| `split.no_group_overlap` | — (whether it is ever required here: §14 item 3) | R | — |
| `split.no_overlapping_windows_across_partitions` | R* (overlapping_windows) | R* | R* |
| `split.temporal_dependence_respected` | R* (temporal_order); definition *(Step 8)*, NOT_ASSESSED until defined | R* | — (covered below) |
| `split.chronological_order` (all eval prediction times after training data, plus declared gap) | — | — | R |
| `fit.rows_subset_of_fold_train` (every attributable fit's rows ⊆ its fold's train IDs; a `global` fit must not include any row from any declared eval partition) | R | R | R |
| `fit.coverage_complete` (no unattributable/unsupported/lineage-broken fits on the observed path) | R | R | R |
| `metric.prediction_ids_match_eval_ids` | R | R | R |
| `metric.reported_matches_recomputed` | R if `reported_metrics` declared; tolerance *(Step 8)* | same | same |
| `metric.recomputed_primary`, `metric.baselines` (dummy; linear where appropriate) | D | D | D |
| `temporal.features_available_at_prediction_time` | — | — | R |
| `temporal.label_horizon_respected` | — | — | R |
| `robustness.*` (range across predeclared seeds/groups, per-group results) | D | D | D |

Notes:
- Missing required metadata (e.g. no `group_id` under `unseen_group`, no window bounds when `overlapping_windows` is declared) makes the affected assertion **NOT_ASSESSED**, never not-applicable.
- Undeclared dependence that exists in the data cannot be detected by policy. This is a stated limitation, and static suspicions may hint at it.
- Robustness stays descriptive until a justified rule is predeclared (Q2 rule 5).
- Policy files are versioned (`policy_version` in every run). Changing a policy is a code change with review, never a runtime choice.

## 6 Run outcome derivation (Q2)

```text
if not supported(project, claim):                    -> NOT_SUPPORTED
R := policy.required_assertions(claim)               # fixed by policy version; never agent-selected
valid(a) := a's evidence exists, hashes verify, and a does not depend on failed/corrupt evidence
if any a in R: a.status == FAIL and valid(a):        -> VIOLATION_FOUND
    (also display any ERROR/NOT_ASSESSED in R prominently as incomplete coverage)
if R is empty or no a in R was assessed:             -> INCONCLUSIVE   (empty set never yields NO_VIOLATION_FOUND)
if any a in R: status in {NOT_ASSESSED, ERROR} or not valid(a): -> INCONCLUSIVE
if all a in R: status == PASS and valid(a):          -> NO_VIOLATION_FOUND (with coverage + limitations shown)
```

A FAIL or PASS whose evidence is invalid is downgraded to ERROR before derivation. Every outcome is displayed with its plain-language label (PRD) and limitations.

## 7 Runs, evidence, artifacts

- **Run directory:** `runs/<run_id>/` (git-ignored). `run_id` derives from a hash of the project snapshot, the confirmed claim, the policy version and a timestamp.
- **Artifacts:** `manifest.snapshot.json`, `claim.json`, `fit_traces.jsonl`, `splits.json`, `predictions/<fold>.parquet`, `checks/<check_id>.json`, `outcome.json`, `agent_log.jsonl`, `report.json`, `report.md`. Each is hashed into `index.json`.
- **Integrity:** a missing or hash-mismatched artifact makes dependent assertions ERROR.
- **Reproducibility:** the report records dependency versions (from `uv.lock`), the evaluator version, the policy version, the adapter version, the model ID and the seed list.
- **Curation:** sanitized example reports are curated explicitly into the repo; raw runs are not committed.

## 8 Trusted evaluator and label stores (Q3.4, Q6)

- The evaluator runs **after** the candidate process exits, in a separate trusted step outside the candidate container. It reads predictions and its own label store.
- **Development-evaluation labels** are part of the project table and visible to the project. The evaluator still scores from its own snapshot copy, so the project's scoring code is never trusted.
- **Final-holdout labels** and held-out answer keys live only in the evaluator's store. They are never mounted into candidates and never placed in model prompts. For the Q6 held-out cases, the store sits outside this repo and is referenced by path and hash at evaluation time only.
- **Recomputation:** balanced accuracy, macro-F1 and the dummy baseline on identical partitions, with predictions matched by row ID. Never compare across different protocols as if they were identical.
- Development validation can guide a revision. Final-holdout outcomes cannot select candidates or parameters.

## 9 Candidate revisions and approval (Q4)

1. The model emits a unified diff against the immutable original snapshot.
2. **Allowed path:** the manifest's `entry_point` only. Changes are never allowed to the adapter, evaluator, labels, policy, dependencies, manifest, instruction files or anything outside the project snapshot.
3. **Validation (hygiene, not the boundary):** allowed-path check, rejection of symlinks and path escapes, rejection of new files and deletions, a size cap, `ast.parse` of the result, and checking that the diff applies cleanly.
4. **Candidate hash:** `sha256(base_snapshot_hash ‖ resulting entry_point bytes)`.
5. **Approval:** the user explicitly approves one exact candidate. The record is `{candidate_hash, base_snapshot_hash, approved_at}`. The runner refuses to execute unless the hash matches, so any change needs fresh approval.
6. **Execution and re-checking:** the candidate runs only in the isolated runner (§10). The trusted evaluator and the checks re-run on the result. The model never declares success.
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

- **States:** `INTAKE → CONTRACT_REVIEW → INSPECT → CHECK → PROPOSE_PATCH → (APPROVAL) → EXECUTE → VERIFY → REPORT`, with optional `SAVE_PROCEDURE`. Any state can end in `NEEDS_INPUT`, `NOT_SUPPORTED`, `BUDGET_EXHAUSTED` or `ERROR`.
- **Tools (typed, normalized paths, no shell):** `list_project_files`, `read_project_file`, `profile_table`, `run_check`, `propose_patch`, `evaluate_candidate` (approval-gated), `inspect_evidence`, `retrieve_procedure`, `propose_procedure`.
- **Ceilings (initial; tune only with measurements, recorded in DECISIONS.md):** 6 model calls, 12 tool operations, 1 retry per transient model call, 2 candidate revisions, 5 min per run, 30 s per candidate execution.
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

## 12 Procedures (Q4; playbook §8)

- **Record:** JSON following the playbook §8 example: claim pattern, schema prerequisites, verification assertions, patch template (constrained recipe with parameters and allowed paths), invalidation conditions, provenance and validation. Records are immutable once versioned.
- **Admission:** the model may propose. Only the trusted validator sets `verified_for_recorded_scope`, and only when:
  - required assertions are not ERROR or NOT_ASSESSED;
  - the template hash, evaluator version and policy version resolve;
  - provenance is complete.
- **Retrieval:** metadata filter first, then optional ranking. The result carries explicit applicability reasons. Text similarity never overrides a schema, claim-type or temporal mismatch.
- **Reuse:**
  - prerequisites are re-checked and the template is bound to the new schema;
  - the rendered candidate goes through §9 (validation, hash-bound approval, isolation, re-checks);
  - the outcome is recorded as `reuse_succeeded` / `reuse_rejected(failed_prerequisite)`.
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

## 14 Open questions for the Step 8 scientific review

Priority items for `handoffs/science-01.md` (at most five, per Start Here Step 8):
1. **Recorder limits and the T-01 outcome policy (Q3, Q2).**
   - What can this instrumentation establish within its supported coverage, what bypasses or failures remain possible, and which executable negative tests should define its limits?
   - When a build implements only some required assertions (T-01), is a clean outcome explicitly scoped to the implemented checks, or must it remain `INCONCLUSIVE` under the full required policy? §6 does not yet say how a required-but-unimplemented assertion is handled. Either answer must not imply that unimplemented checks passed or weaken the full policy.
2. **Synthetic 2×2 design.** Do the planned generator settings (subject/session confounding, a modest genuine signal, correlated windows) separate the split defect from the global supervised-selection defect without manufacturing an effect? What clean-control expectation is defensible?
3. **`same_population` dependence assertions.** How should `temporal_dependence_respected` and overlapping-window assertions be defined, and when (if ever) should group overlap be required under `same_population`?
4. **Real-data example.** For UCI HAR (precomputed features, windows with overlap, the original subject-based split), which claim, which protocol and which clean control is honest, and which limitations must be stated?
5. **Comparison and scoring.** What is the unit of a "finding" for precision/recall against answer keys? Is the 3-repetition paired pilot with randomized order and reported cache state adequate as descriptive evidence?

Further items (not in the five-question packet unless reprioritized):
- the tolerance for `metric.reported_matches_recomputed`;
- the exact form of feature-availability metadata and label-horizon/gap rules for `future_time`, and the Variant B refusal criteria;
- minimum group and class-coverage floors for `unseen_group` feasibility ("stop and explain" thresholds);
- whether any robustness rule should ever become required, and how correlated windows affect uncertainty statements.

## 15 Known limitations (to be stated in the README and reports)

- Fit provenance covers only the enumerated supported operations, and the in-process recorder is not tamper-proof.
- Policy cannot detect dependence the user did not declare.
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
