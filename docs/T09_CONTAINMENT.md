# T-09: UCI HAR real-data example, clean control and containment evidence

Status: built and audited offline on 2026-10-17 (worktree `atlas-t09`, branch `t09-har`). For the lead's review of the containment evidence, and Gemini's review of the claims. Nothing here changes the engine, evaluator, runner, policy, checks, intake limits or an existing benchmark.

## 1. Data and attribution

- **Dataset:** UCI HAR, "Human Activity Recognition Using Smartphones" (UCI dataset 240). Citation, license and changes: `benchmarks/real_sensor/ATTRIBUTION.md`.
- **Retrieval:** `uv run --locked python benchmarks/real_sensor/retrieve.py` downloads into the git-ignored `benchmarks/real_sensor/data/` (`git check-ignore` confirmed). It verifies every hash in the committed `checksums.json` and fails closed on any difference: a deliberately altered hash gave exit 1 with nothing written.

  | Item | SHA-256 |
  | --- | --- |
  | Archive (61,005,872 bytes) | `c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031` |
  | Inner `UCI HAR Dataset.zip` | `2045e435c955214b38145fb5fa00776c72814f01b203fec405152dac7d5bfeb0` |
  | Built `table.parquet` (identical for both projects; git-ignored) | `cc31bdb1e20f734e1866ee3547b824fbd66b23ee6e097d9ef4287073188bd02a` |

  The ten extracted files' hashes are in `checksums.json`.
- **License terms, flagged for the lead.** The dataset page grants CC BY 4.0 (attribution required). The archive's own `README.txt` (2012) adds "Any commercial use is prohibited." The use here is non-commercial, local and attributed, and no data is redistributed, so it complies with both. Which terms govern must be decided before any public or hosted use (for example a T-12 demo).

## 2. Protocol (SPEC §17 "UCI HAR example", DECISIONS.md F4)

- **Claim:** "The activity classifier works on people absent from training." Type `unseen_group`, sampling unit `subject`, `group_id` = `unit_id` = `subject_id`.
- **Dependence:**
  - `repeated_measures` on `subject_id`: many windows per volunteer;
  - `overlapping_windows`: 2.56 s windows with 50% overlap.
- **Primary metric:** balanced accuracy over the six activities.
- **Partitions:**
  - The tables hold only the official **training** partition: 21 subjects (S01, S03, S05–S08, S11, S14–S17, S19, S21–S23, S25–S30), 7,352 windows, 561 features.
  - The official **test** partition (9 subjects, 2,947 windows) is downloaded and hashed, so its identity is recorded. **Neither project reads it**, and no final held-out score is computed.
  - Why: no evaluator-only label store exists yet (`final_holdout` reported metrics are NOT_ASSESSED until it does), and a project-computed test score would put holdout labels on the project's path. Development uses folds within the training subjects only.
- **The two projects** (both in `benchmarks/real_sensor/`). Both use the same model family: StandardScaler, then SelectKBest(f_classif, k=50), then LogisticRegression(max_iter=1000).

  | | `har_flawed`: **ATLAS-authored flawed variant** | `har_clean`: clean control |
  | --- | --- | --- |
  | Folds | random row-level `KFold(5, shuffle, seed 0)` over windows | `GroupKFold(5)` by `subject_id` |
  | Fitting | scaler and selector fit on **all** 7,352 rows before splitting | scaler, selector and classifier fit inside each fold, on its training rows only |
  | Reported metric | its own balanced accuracy, mean over its 5 folds: 0.906396437268804 | none |

  The flawed variant's flaws are ours, not alleged of the original study. Its manifest statement and its code comments say so.
- **No temporal assertions are claimed:** the dataset has no timestamps, and the claim is `unseen_group`, so policy-v1.3 schedules none.

## 3. Window-overlap containment evidence

`split.no_window_overlap` is required, because `overlapping_windows` is declared.

- **Why the direct route cannot run:** the HAR release gives no per-window start/end times and no recording-stream identifiers. No `stream_id`, `window_start` or `window_end` is declared, so each fold is "incomplete" on the direct route.
- **Route C (documented containment).** Each manifest carries a `window_containment` declaration:
  - **Within:** `group_id` (= `subject_id`).
  - **Source:** UCI HAR `README.txt`, in the archive with the SHA-256 above. It says each of 30 volunteers performed the activities wearing a smartphone; "The sensor signals … were … sampled in fixed-width sliding windows of 2.56 sec and 50% overlap (128 readings/window)"; and "70% of the volunteers was selected for generating the training data and 30% the test data".
  - **Statement:** every window is cut from one volunteer's own recording, so a window can overlap only windows of the same subject. Subject-disjoint folds therefore keep every pair of overlapping windows on one side of the split.
- **The reasoning, and its limit:** sliding windows are cut from a continuous signal, and each signal is one volunteer's recording, so two windows can share samples only if they come from the same volunteer. The README does not say this sentence literally; it follows from how the windows are described. ATLAS records the declaration and does **not** verify it: no raw signal is checked, and the source is not fetched by the engine.
- **The rule that applies (F4):** route C may PASS only with this documented evidence **and** a valid `split.no_group_overlap` PASS. The window result records that dependency (`depends_on: ["split.no_group_overlap"]`).
- **What happened:**
  - **`har_clean`:** **PASS** via route C. Every fold is `established_by: documented_containment`, and the engine's limitation says the PASS "is conditional on documented containment, not independently verified … It also depends on the valid split.no_group_overlap PASS."
  - **`har_flawed`:** **NOT_ASSESSED** (`missing_metadata`): "route C needs a valid split.no_group_overlap PASS, which is absent". Its group check FAILs, so the containment declaration cannot make the window check pass, and nothing pretends it does.

## 4. Upstream preprocessing and provenance

Provenance coverage begins at the supplied feature table; every report says "Provenance begins at the supplied feature table."

The 561 features were computed upstream by the dataset authors, with noise filtering, Butterworth separation of gravity, time- and frequency-domain features, and "Features are normalized and bounded within [-1,1]". **Whether that normalization was fit globally (across subjects, or across the training and test partitions) is not established.** If it was, every evaluation of this table inherits that dependence. ATLAS checks only the fitting done by the evaluated code (`fit.state_dependencies_within_fold_train`), from the table onward.

## 5. How the audit was run

- **Command:** `uv run --locked python benchmarks/real_sensor/run_audit.py --repeat 3 --runs-dir runs/t09/audit`, with Docker Desktop 29.8.2 and runs under `runs/t09/` (git-ignored).
- **Why not `atlas.cli audit --mode audit`:** that mode executes only allowlisted, repo-authored trusted fixtures, **on the host** (`trusted_pipeline_only`). For both projects it refused before executing anything, exit 1: "… is not an allowlisted trusted fixture; refusing to execute" (`runs/t09/cli/*.log`). Admitting them would need a runner allowlist change and host execution of project code, both out of bounds.
- **The Docker path used:** the engine's agent loop, which runs the unmodified original in the isolated runner (`--network none`, non-root, read-only rootfs) and judges it with the trusted evaluator.
  - It is given **one fixture reply, `finish`**: NON-LIVE, no model is called, no candidate is proposed. The result is the trusted evaluator's verdict on the original alone.
  - The original's execution needs an approval bound to its hashes. `OriginalOnly` grants exactly the original request (kind `original`, empty diff) and refuses anything else; it records `t09_task_authorized_original`.
  - The authority for that approval is the T-09 instruction to run these two ATLAS-authored projects in Docker.

## 6. Results

Repeat 1 of each project, under `runs/t09/audit/`; all three repeats agree (§7).

### `har_flawed`: **VIOLATION_FOUND**

- **Run:** `agent-har_flawed-1e2267f662c0`; snapshot `36089ef2…0fb6`; `outcome.json` SHA-256 `dc4a4b10c2be86d232f364ded8893018a85ad3a09119a82ed0193110c24dc6d5`.
- **FAIL:**
  - `split.no_group_overlap`: all 21 subjects are on both sides of every fold;
  - `split.sampling_unit_disjoint`;
  - `split.repeated_measures_rule`;
  - `fit.state_dependencies_within_fold_train`: both global fits are detected, the StandardScaler (7,352 contributing rows) and SelectKBest (7,352 rows, labels used), and each affects all five folds' predictions.
- **NOT_ASSESSED:** `split.no_window_overlap` (`missing_metadata`; see §3). Incomplete coverage: `split.no_window_overlap`.
- **PASS:**
  - `split.evaluation_folds_nonempty`, `split.no_row_overlap`;
  - `split.no_shared_source_observation`: an exact-value screen only, since no source-observation identity is declared;
  - `fit.coverage_complete`, `metric.prediction_ids_match_eval_ids`;
  - `metric.reported_matches_recomputed`: reported 0.906396437268804, recomputed 0.906396437268804, |difference| 0.0, at the 1e-6 tolerance.

### `har_clean`: **NO_VIOLATION_FOUND**

"Every required check passed within the coverage shown." This does not say the claim is true, and it is not a "valid" verdict.

- **Run:** `agent-har_clean-ac63eaecd7a8`; snapshot `03eeac4e…3db2`; `outcome.json` SHA-256 `4fa8c28b16cf883ebf3c6b9222995f4c13315beefe2989b45101240aa99b44e4`.
- **All 10 required assertions PASS:** `split.no_window_overlap` only through documented containment, conditional and not independently verified (§3), and `split.no_shared_source_observation` as the exact-value screen above.
- **NOT_ASSESSED:** none. Incomplete coverage: none.

### Reported against independent metrics (balanced accuracy, development folds)

| | Mean over folds | Pooled (7,352 rows) | Per fold |
| --- | --- | --- | --- |
| `har_flawed`, as reported by its own protocol | 0.906396437268804 | | |
| `har_flawed`, recomputed independently by ATLAS from its predictions | 0.906396437268804 | 0.906335 | 0.9136, 0.9068, 0.8984, 0.9132, 0.9000 |
| `har_clean`, recomputed independently, subject-grouped folds | **0.875188** | 0.874635 | 0.8265, 0.8607, 0.9265, 0.9022, 0.8600 |

**Expected against actual.** The task expected the flawed variant's independent metric to be visibly below its reported metric. **That did not happen, and it cannot here:** ATLAS recomputes the metric from the flawed variant's own predictions, which are the same predictions its reported score came from. The two agree exactly, and the reported-metric check correctly PASSes.

The inflation shows instead **against the clean control**. The flawed protocol's 0.9064 is 0.0312 above the subject-grouped estimate of 0.8752 for the same model family on the same subjects. The flawed protocol's fold-to-fold range is also narrower (0.898–0.914 against 0.827–0.927): random row folds put every subject in every fold.

This difference is descriptive. Two protocols on the same data are compared, and the metric is never part of an outcome (SPEC §17: protocol differences are not causal decompositions). Nothing was tuned to reach the expected outcomes: these are the first and only settings run.

## 7. Robustness (three repeats per project, descriptive)

`benchmarks/real_sensor/robustness.py runs/t09/audit/t09_audit_20261017T200009Z.json` (results in `…_robustness.json`):

| | `har_flawed` | `har_clean` |
| --- | --- | --- |
| Outcome across repeats | VIOLATION_FOUND ×3 | NO_VIOLATION_FOUND ×3 |
| Every assertion's status and reason | identical | identical |
| Evidence files compared | 28 | 28 |
| Files with differing SHA-256 | only timed or approval records: `approval.json`, `candidate.json` (its `approved_at`), `execution.json` (×2), `index.json`, `report.json` | the same |
| `outcome.json`, `splits.json`, `provenance.jsonl`, predictions | identical SHA-256 in all three | identical in all three |
| Metric spread (max − min), pooled and mean over folds | 0.0 | 0.0 |
| Per-fold values | identical | identical |

The runs are deterministic at this setting (one CPU in the container, a fixed `random_state` for the flawed KFold, deterministic GroupKFold and lbfgs). Three repeats show stability on this machine and image, nothing more.

## 8. Build decisions

| # | Decision | Why |
| --- | --- | --- |
| D1 | Audit in Docker through the agent loop with a finish-only fixture reply and an original-only approver (`run_audit.py`), not `atlas.cli audit --mode audit`. | Audit mode runs only allowlisted trusted fixtures, on the host. It refused both projects; admitting them would need a runner allowlist change and host execution. |
| D2 | The tables hold the training partition only; the test partition is hashed but never read; no final held-out score. | SPEC §17 and F4 reserve it from development and tuning; no evaluator-only label store exists. |
| D3 | Route C containment declaration, with no `stream_id` or window bounds. | HAR gives neither, so the direct route cannot run. Declaring `stream_id = subject_id` would assert containment silently as stream identity. Route C records it as a declaration, with its dependency on the group result. |
| D4 | No `observation_id` column. | Overlapping windows share raw samples, so declaring each row its own source observation would be untrue. The check runs its exact-value screen and says so. |
| D5 | The "ATLAS-authored flawed variant" label goes in the flawed manifest's `claim.statement`, as a bracketed suffix, and in the code comments. | The manifest schema forbids extra fields; the statement is the only free-text field that is shown with the claim. The clean control's statement is the same sentence without the label. |
| D6 | The flawed variant's reported value (0.906396437268804) was taken from its own predictions in a calibration run (`runs/t09/calibration/`), before `reported_metrics` was added. | Project code runs only in Docker, and the engine has no channel for a project to emit its own score. The value is what the flawed protocol itself produces (mean over its folds); ATLAS's recomputation of the same predictions necessarily agrees. |
| D7 | The same model family for both, with SelectKBest(k=50) and LogisticRegression(max_iter=1000); 5 folds each. | It is the same pattern as s01/s02, and it fits the runner's 30 s, 1 CPU, 1 GiB limits: the calibration audit of both projects took 14 s in all, start-up included. |
| D8 | Parquet (zstd), 35.2 MB, under the 64 MiB snapshot limit; feature columns named `f<index>_<name>`. | CSV would be larger, and upstream feature names are not unique. |
| D9 | Projects are not added to the UI catalogue. | `atlas.ui.catalogue` is a fixed list of `benchmarks/t01` fixtures, not a convention-based scan of `benchmarks/`. Follow-up: add `har_flawed`/`har_clean` entries (UI code only) and an approval-flow check for the 35 MB table. |
| D10 | Robustness is reported by comparing artifact hashes and metric values across repeats; timed and approval records are listed separately. | They differ by design (timestamps); everything an outcome depends on was compared. |

## 9. Limitations

- The containment declaration is documented, not verified; the window PASS on `har_clean` is conditional on it (§3).
- Upstream normalization's fit scope is not established (§4).
- `split.no_shared_source_observation` is an exact-value screen only; near-duplicates and shared raw samples are not assessed.
- Both projects are ATLAS-authored and run on a public dataset; neither is independent benchmark evidence for ATLAS's detection rates.
- The audit's execution approval is scripted under the task's authority (D1), not typed by a person.
