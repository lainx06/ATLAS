# Tasks

Task index plus a concise structured entry per task under "Implementation tasks" (playbook Section 24 fields; see `docs/agents/issue-tracker.md`). Each implementation task needs: acceptance criteria, owned files, model/effort, verification commands (or an instruction to create them), and its next review gate. `handoffs/` is only for Section 19 external/substantial transfers.

**RUN convention.** Commands marked *(create)* do not exist yet. The builder must create them and show them working (real output, exit code) before citing them as evidence. Commands marked *(existing)* run today. `uv run --locked pytest` exits 5 when no tests are collected, and that is not a pass.

| ID | Start Here step | Status | Summary |
| --- | --- | --- | --- |
| S-05 | 5 | Done (`7a0f155`) | Git, uv/Python 3.11 env, locked deps, shared state files, import check |
| S-06 | 6 | Done (`4b3cab6`, `6c06d5e`) | Selected skills installed; Matt skill workflow configured |
| S-07 | 7 | Done (`698ffd8`) | Requirements interview → `docs/PRD.md`, `docs/SPEC.md`, `GLOSSARY.md`, this task list |
| S-08 | 8 | Done (dispositions recorded 2026-10-14) | Scientific review packet `handoffs/science-01.md`; Gemini review; lead dispositions F1–F5, L1–L2 |
| T-01 | 9 | **Accepted by the lead at `f5aa4dc`** within its documented scope (2026-10-14), on Codex's independent verification: 165 tests passed, no remaining blocker in the reviewed scope. Limitations stand (see RESULT and review records) | First deterministic slice: `unseen_group` fixtures, split/group integrity, bounded fit provenance, prediction IDs, outcome derivation, evidence JSON |
| T-02 | 11 | Proposed | Independent metrics, conditional split rules (windows, separation), `future_time` assertions, reported-metric comparison |
| T-03 | 11 (early) | Proposed | Hosting and isolated-worker probe (docs/evidence only) |
| T-04 | 10 | Preparation done (placeholder `.env`, git-ignored). **Blocked: Nebius credits not yet received** (form submitted; Builder Program pending); no paid calls | Nebius access: model list, capped structured-output smoke call |
| T-05 | 10 | Prerequisites checked (read-only): Docker and WSL 2 absent; first action `wsl --install` (user, admin, restart). Runner not started | Isolated runner and hash-bound candidate approval |
| T-06 | 11 | Proposed | Bounded live agent loop end to end |
| T-07 | 12 | Proposed | UI spec, one complete Streamlit path, Playwright scenarios |
| T-08 | 11 | Proposed | Procedures: admission, reuse, refusal; transfer benchmark |
| T-09 | 11 | Proposed | Real-data example, clean control, robustness reporting |
| T-10 | 11 | Proposed | Held-out cases (Codex, outside repo) and predeclared campaign |
| T-11 | 11 | Proposed | Three-way comparison pilot |
| T-12 | 11 | Proposed | Limited hosted demo and judge access |
| T-13 | 13–14 | Proposed | Release package and submission evidence |

## Implementation tasks

### S-08 Scientific review (Start Here Step 8)
- **OWNER:** Claude Code (packet author, read-only on code) → Gemini (reviewer, no edits) → lead (dispositions).
- **MODEL DECISION:** SWITCH for the review (Gemini Argon High; scientific challenge). Claude stays Opus High to write the packet.
- **MODEL / EFFORT:** Claude Opus 5.5 high (packet); Gemini 4 Argon High (review), selected in Gemini's own picker.
- **READ FIRST:** `PROJECT_BRIEF.md`, `docs/PRD.md`, `docs/SPEC.md` (§5, §6, §14), `DECISIONS.md` (Q1–Q6).
- **INPUT STATE:** S-07 committed; no implementation.
- **RESULT (2026-10-14):** done. Dispositions F1–F5 (Gemini) and L1–L2 (lead) are recorded in DECISIONS.md and applied to SPEC/PRD/GLOSSARY/ADR 0001 and T-01. The packet is preserved unchanged as the reviewed snapshot.
- **CHANGE:** create `handoffs/science-01.md` (brief, evaluation design, benchmark definitions, the five priority questions from SPEC §14). No secrets, labels or answer keys.
- **ACCEPTANCE:** every Gemini finding has an accepted/rejected/deferred disposition in DECISIONS.md, and T-01 is updated to match. The first build task is unambiguous.
- **RUN:** none (document task).
- **EVIDENCE:** the packet; Gemini's verbatim findings; dispositions.
- **HANDOFF:** the packet to Gemini via upload; the findings back to the lead.
- **RECOVERY:** if a finding needs a design change, update SPEC/PRD and DECISIONS.md before T-01 starts.

### T-01 First deterministic slice (Start Here Step 9)
- **OWNER:** Claude Code (writer). Local Codex reviews afterwards.
- **MODEL DECISION:** STAY on Opus High. Provenance and outcome logic is core scientific code.
- **MODEL / EFFORT:** Claude Opus 5.5, high (`/model`, `/effort` in Claude Code).
- **READ FIRST:** `AGENTS.md`, `STATUS.md`, `docs/SPEC.md` §3–§7 and §10 (fixture rule), `GLOSSARY.md`, DECISIONS.md "Step 8 scientific review dispositions".
- **INPUT STATE:** Step 8 dispositions recorded (F1–F5, L1–L2). Only trusted, repo-authored synthetic fixtures run, in a host subprocess under the fixture hash allowlist (SPEC §10). Excluded: model calls, generated or candidate code, hosted deployment, and any Docker prerequisite.
- **CHANGE (owned paths):**
  - `src/atlas/contracts.py`, `src/atlas/adapter.py`, `src/atlas/recorder.py`, `src/atlas/checks/split_integrity.py`, `src/atlas/checks/fit_provenance.py`, `src/atlas/checks/metric_ids.py`, `src/atlas/policy.py`, `src/atlas/reports.py`, `src/atlas/runner/trusted.py`, `src/atlas/cli.py`;
  - `benchmarks/t01/` (fixture projects, each with its manifest and a README recording generator seed and settings);
  - `tests/unit/`, `tests/integration/`.

  **Scope:**
  - Claim type `unseen_group` only.
  - Policy `policy-v1` is loaded in full (now `policy-v1.2`). These assertions are implemented: `split.evaluation_folds_nonempty` (added in v1.2), `split.no_row_overlap`, `split.no_shared_source_observation`, `split.no_group_overlap`, `split.sampling_unit_disjoint`, `split.repeated_measures_rule` (unit/group/containment rules only), `fit.state_dependencies_within_fold_train`, `fit.coverage_complete`, `metric.prediction_ids_match_eval_ids`.
  - Also in scope: the bounded supported path and recorder (SPEC §4); scheduling and materialization of every other applicable required assertion as NOT_ASSESSED with a reason (SPEC §6); outcome derivation; evidence JSON (SPEC §7).
- **Fixture declarations:** truthful, never trimmed to reach an outcome.
  - Base fixtures: claim `unseen_group`; `group_id` = `unit_id` = subject; `sampling_unit` = subject; dependence `repeated_measures(subject_id)` and `repeated_measures(session_id)` (sessions nested in subjects); `observation_id` declared.
  - The generator writes non-overlapping window rows, so `overlapping_windows` is not declared on base fixtures.
  - For the base declarations, the full required set is exactly the implemented assertions: eight under policy-v1, nine under policy-v1.2 with `split.evaluation_folds_nonempty`. So a clean base fixture may reach `NO_VIOLATION_FOUND` only if all of them are implemented and pass.
- **ACCEPTANCE:** expected assertion statuses per scenario. These are **planned tests**; nothing is passing until they run.

  Columns: RO `no_row_overlap`, SO `no_shared_source_observation`, GO `no_group_overlap`, SU `sampling_unit_disjoint`, RM `repeated_measures_rule`, SD `state_dependencies_within_fold_train`, CC `coverage_complete`, PI `prediction_ids_match_eval_ids`. NA(reason) = NOT_ASSESSED with that reason.

  | # | Scenario | RO | SO | GO | SU | RM | SD | CC | PI | Other | Outcome |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | 1 | Faulty: random-row split + global `SelectKBest(f_classif)` fit on all rows, used in every fold | PASS | PASS | FAIL | FAIL | FAIL (v1.1 own witnesses: subject overlap, group separation) | FAIL (labels_used=true) | PASS | PASS | — | VIOLATION_FOUND |
  | 2 | Clean: `GroupKFold`, `take`, `Pipeline` fit per fold, fully observed | PASS | PASS | PASS | PASS | PASS (v1.1: complete, no same-fold witness) | PASS | PASS | PASS | — | NO_VIOLATION_FOUND |
  | 3a | Unknown ancestry: like 2, but the training frame is rebuilt with the same valid index before fitting | PASS | PASS | PASS | PASS | PASS | NA(unknown_ancestry) | NA(coverage_gap) | PASS | — | INCONCLUSIVE |
  | 3b | Unexplained mutation: like 2, but a tracked frame is modified in place | PASS | PASS | PASS | PASS | PASS | NA(unknown_ancestry) | NA(coverage_gap) | PASS | — | INCONCLUSIVE |
  | 4 | Zero fit: predictions written without any observed supported classifier fit | PASS | PASS | PASS | PASS | PASS | NA(zero_fit) | NA(zero_fit) | PASS | — | INCONCLUSIVE |
  | 5a | Contaminated reuse: a grouped split, but a selector fitted on fold 1's training rows (which include fold 2's eval subjects) is reused in fold 2 | PASS | PASS | PASS | PASS | PASS | FAIL (fold 2) | PASS | PASS | — | VIOLATION_FOUND |
  | 5b | Benign reuse: one instance fitted only on subjects that are in every fold's training set, reused across folds | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | — | NO_VIOLATION_FOUND |
  | 6 | Missing metadata: like 2, but the manifest omits `group_id` and `unit_id` | PASS | PASS | NA(missing_metadata) | NA(missing_metadata) | NA(missing_metadata) | PASS | PASS | PASS | — | INCONCLUSIVE |
  | 7 | Unimplemented required assertion: like 2, plus a truthful `overlapping_windows` declaration with `stream_id` and bounds | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `split.no_window_overlap` NA(unimplemented_assertion) | INCONCLUSIVE |
  | 8a | Unsupported claim: combined unseen-group-plus-future-time | — | — | — | — | — | — | — | — | no checks judged | NOT_SUPPORTED |
  | 8b | Entry point does not use the adapter | — | — | — | — | — | — | — | — | static suspicions only | NOT_SUPPORTED |
  | 9a | Corrupted evidence plus an independent valid FAIL: scenario 1 with the provenance artifact's hash broken | PASS | PASS | FAIL | FAIL | FAIL | ERROR | ERROR | PASS | incomplete coverage displayed | VIOLATION_FOUND |
  | 9b | Corrupted evidence alone: scenario 2 with the provenance artifact's hash broken | PASS | PASS | PASS | PASS | PASS | ERROR | ERROR | PASS | incomplete coverage displayed | INCONCLUSIVE |
  | 10a | Identical-valued independent observations: like 2, with equal feature+target rows across partitions and distinct `observation_id` | PASS | PASS (candidates reported) | PASS | PASS | PASS | PASS | PASS | PASS | — | NO_VIOLATION_FOUND |
  | 10b | As 10a, but no `observation_id` and no `known_duplicates` | PASS | NA(unresolved_duplicate_candidates) | PASS | PASS | PASS | PASS | PASS | PASS | — | INCONCLUSIVE |
  | 10c | As 10b, plus `known_duplicates` documenting one cross-partition pair | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | PASS | — | VIOLATION_FOUND |

  Further acceptance points:
  - Every assertion records which artifacts it depends on. A broken artifact makes exactly its dependent assertions ERROR (9a, 9b), and leaves independent valid results intact.
  - Every run lists every applicable required assertion; none is omitted.
  - policy-v1.2: `split.evaluation_folds_nonempty` is PASS in every executed scenario (1–7, 10a–10c; 9a/9b keep valid split evidence). The fixtures truthfully declare nonempty evaluation folds.
  - NOT_ASSESSED always carries its reason, and no FAIL is invented from unknown ancestry.
  - **Mutation check** (each mutation applied to a copy, then restored; each must make at least one scenario test fail):
    - (m1) the dependency check uses the fold where a state was *fitted* instead of where it was *used*. Planned as "caught by 5a", but that was wrong: under m1, 5a still FAILs, because its classifier is refit in the use fold on the reused selector's output and the dependency propagates. It is caught by the added test `test_whole_model_fitted_in_one_fold_and_reused_to_predict_another_fails`;
    - (m2) group overlap compares row IDs instead of group IDs; caught by 1;
    - (m3) a valid index is accepted as ancestry; caught by 3a.
- **RUN:**
  - *(existing)* `uv run --locked ruff check .`
  - *(existing)* `uv run --locked ruff format --check .`
  - *(create)* `uv run --locked pytest tests/unit tests/integration -q`. It must collect the scenario tests above and pass; exit 5 (no tests collected) is a failure.
  - *(create)* `uv run --locked python -m atlas.cli audit benchmarks/t01/<scenario> --mode audit` for at least scenarios 1, 2 and 7.
  - *(create)* a recorded mutation-check procedure (script or documented commands) producing a log for m1–m3.
- **EVIDENCE:** `runs/<run_id>/` outcome and check JSON for scenarios 1, 2 and 7 (hashes recorded in STATUS.md); the pytest output; the mutation-check log; fixture generator settings in `benchmarks/t01/README.md`.
- **HANDOFF:** a local Codex review of the diff and evidence (Start Here Step 9 prompt). No browser packet.
- **RECOVERY:** preserve the failing fixture and output. Two focused repair rounds, then diagnosis by Codex. Never edit an expected status to make a test pass without recording the reason in DECISIONS.md.
- **RESULT (2026-10-14, Claude Code, Opus 5.5 high; self-tested, not independently reviewed):**
  - **Checkpoints:** base `35016bb`; head = the local commit "Implement T-01 deterministic audit slice" (parent `35016bb`).
  - **Changed files:**
    - `src/atlas/`: `contracts.py`, `policy.py`, `adapter.py`, `recorder.py`, `intake.py`, `audit.py`, `reports.py`, `cli.py`, `checks/{split_integrity,fit_provenance,metric_ids}.py`, `runner/{trusted,bootstrap}.py`, `runner/trusted_fixtures.json`;
    - `benchmarks/t01/` (`generate.py`, `README.md`, 14 scenario directories);
    - `tests/unit/` (4 files), `tests/integration/` (3 files);
    - `scripts/mutation_check.py`;
    - `docs/SPEC.md` (adapter `load_metadata()` row; T-01 artifact list).
  - **Beyond the planned owned paths:** `intake.py`, `audit.py`, `reports.py`, `runner/bootstrap.py`, the allowlist JSON and `scripts/mutation_check.py` (small modules needed for the slice). Scenario fixtures live under `benchmarks/t01/<scenario>/`.
  - **Commands actually run and their results:**
    - `uv run --locked pytest tests/unit tests/integration -q` → **83 passed**, exit 0. This covers all 16 scenario rows (statuses per assertion and outcome) plus listing and reason checks, 9a/9b corruption, the CLI, fixture integrity and unit tests.
    - `uv run --locked python scripts/mutation_check.py` → **3/3 caught**, exit 0. m1 is caught by the added whole-model reuse test, m2 by s01, m3 by s03a. Each run confirmed the mutated package was imported from its temporary copy, including in the fixture child (m3).
    - `uv run --locked python -m atlas.cli audit benchmarks/t01/<s> --mode audit --runs-dir runs` for s01, s02 and s07 → `VIOLATION_FOUND`, `NO_VIOLATION_FOUND` and `INCONCLUSIVE` (`split.no_window_overlap` unimplemented). Each exited 0. Evidence is in git-ignored `runs/`; hashes are in STATUS.md.
    - `uv run --locked ruff check .` → All checks passed. `uv run --locked ruff format --check .` → 57 files already formatted.
    - `uv run --locked python scripts/sync_skills.py --check` → problems 0.
  - **Defects found and fixed during the task:**
    1. **Relative `--runs-dir`:** the fixture child (cwd = fixture folder) wrote its evidence into the fixture folder, and every assertion became ERROR (failing closed). The root cause was a relative output path. The fix resolves the run directory to an absolute path and the runner passes absolute paths; regression test `tests/integration/test_cli.py`. One repair cycle; the stray outputs were removed.
    2. **m1 not caught by the planned scenario:** fixed by adding a discriminating test (above).
  - **Limitations (stated, not hidden):**
    - Host execution is limited to allowlisted trusted fixtures; the capability is `trusted_pipeline_only`, with no isolation.
    - The recorder runs in the candidate process and is not tamper-proof. Fingerprints detect changes to tracked objects only, and missing traces don't prove absence.
    - Fitted-state violations are reported at the use event (for example, the scaler or classifier in s01). The upstream origin (the global selector) is visible in `provenance.jsonl` but not summarized in the check output.
    - No static analyzer: s08b reports `NOT_SUPPORTED` with no suspicions.
    - `load_holdout_features()`, the T-02 assertions and `report.md` are not implemented.
    - Planned-later assertions are materialized as NOT_ASSESSED `unimplemented_assertion`.
    - Fixture settings are test fixtures, not benchmark measurements.

- **REVIEW 1 (local Codex, 2026-10-14) and REPAIR PASS 1 (Claude Code, Opus 5.5 high):**
  - **Review setup:** Codex discovered the `code-review-and-quality` review skill through its normal skill catalog (reported by the user). The full review text was not supplied to the builder. The findings below are as listed by the user; Codex's reproductions are preserved unchanged at `runs/review-t01/probe.py` (sha256 `c4811335…725f`) and `runs/review-t01/results.json` (sha256 `5fa603e4…ac0f`). The probe was not re-run, so its results were not overwritten.
  - **Checkpoints:** repair base `216f3ff`; head = the local commit "Repair T-01 after Codex review" (parent `216f3ff`).
  - **Findings and dispositions** (all accepted and repaired; each has a regression test that failed on `216f3ff`):
    1. **Trusted-fixture import loophole.** An extra `atlas.py` in a fixture folder was still trusted and would have shadowed `atlas` (probe: `is_trusted: true`, `atlas_resolves_to: …allowlist_inspection_only\atlas.py`).
       - *Repair:* the allowlist binds every fixture's complete file inventory, and the child runs in isolated mode (`-I`) with the parent's resolved `atlas` inserted explicitly. The child records `runtime.json`, which the evaluator verifies.
       - *Tests:* `test_fixture_with_an_extra_file_is_not_trusted_and_does_not_run`, `test_fixture_child_imports_atlas_from_the_trusted_package_not_the_fixture`.
       - No bypass was executed. The runner is not described as a sandbox.
    2. **Undeclared or orphaned folds.** Dropping fold0 from `splits.json` still gave `NO_VIOLATION_FOUND`.
       - *Repair:* provenance split events (with ID-list hashes) are reconciled with `splits.json`, prediction events and use events. Any orphaned, missing or mismatched fold is a coverage gap. SD gives NOT_ASSESSED `coverage_gap` for uses in undeclared folds.
       - *Test:* `test_fold_removed_from_splits_but_present_elsewhere_prevents_complete_coverage` (now CC `coverage_gap`, PI ERROR, `INCONCLUSIVE`).
       - *Documented limit:* consistency cannot prove the existence of a fold erased from every source; that needs an independent expected-fold contract.
    3. **Null identifier values.** A NaN subject on a participating row still PASSed.
       - *Repair:* overlap is judged over known identities; unknown values on participating rows give NOT_ASSESSED `missing_metadata`, for group, unit, observation and repeated-measures columns. An overlap among known identities stays FAIL.
       - *Tests:* four in `tests/unit/test_split_integrity.py`.
    4. **Predictions bound to an unrelated producer.** A prediction re-pointed at a `global`-fold producer still PASSed coverage.
       - *Repair:* each fold needs exactly one prediction event bound to a `predict` use in the same fold, on the same rows, from a supported classifier state, with an artifact SHA-256 matching the verified index.
       - *Tests:* three in `tests/unit/test_fit_provenance.py`.
    5. **Unverified execution evidence.** A hash-mismatched `execution.json` still gave `NO_VIOLATION_FOUND`.
       - *Repair:* `execution.json` and `runtime.json` must verify and pass strict schemas, and the runtime must show controlled imports. Otherwise PASS becomes ERROR (or NOT_ASSESSED `not_executed` for a verified non-completion), and valid FAILs stand.
       - *Tests:* hash-mismatch, schema-invalid-but-rehashed, and FAIL-preservation (s01).
    6. **Missing prediction artifacts.** These gave FAIL instead of ERROR.
       - *Repair:* the expected inventory is the declared folds. A missing or invalid artifact, or one for an undeclared fold, is ERROR; a valid artifact with wrong IDs is FAIL, which survives ERRORs elsewhere.
       - *Tests:* `test_missing_prediction_artifact_is_error_not_fail`, plus `tests/unit/test_metric_ids.py`. Two earlier unit expectations ("declared fold without predictions → FAIL") were replaced by this disposition, not weakened.
    7. **Missing or unparseable manifest snapshot.** This crashed evaluation (`FileNotFoundError`).
       - *Repair:* evaluation first clears earlier outputs. It reconstructs the required set only from the project manifest whose hash matches the recorded snapshot hash, noting that in the outcome reason. Otherwise it is `INCONCLUSIVE` with "required assertion set could not be reconstructed", an empty assertion list and no checks output.
       - *Tests:* two (reconstruction; unreconstructable plus stale-outcome replacement).
  - **Reporting improvement (accepted):** SD FAILs now list `origins` from recorded lineage: the fitted states whose own fit rows fall outside the fold's training set (instance/version, class, fit scope, contributing rows, label use, affected folds, rows outside per fold, affected uses). In s01 this is one origin: `SelectKBest` i2 v1, fit scope `global`, 160 rows, `labels_used=true`, four folds. Its eight downstream uses are listed under the one assertion. Test: `test_violation_report_names_the_originating_global_fit_once`.
  - **Results actually run after the repairs:**
    - `uv run --locked pytest tests/unit tests/integration -q` → **103 passed** (83 previous plus 20 regression tests).
    - `scripts/mutation_check.py` → **3/3 caught** under the isolated launcher.
    - CLI s01/s02/s07 → `VIOLATION_FOUND` / `NO_VIOLATION_FOUND` / `INCONCLUSIVE`, unchanged.
    - `ruff check` → passed; `ruff format --check` → 58 files formatted.
    - `sync_skills.py --check` → problems 0.
    - Every finding was fixed in its first repair cycle. *Superseded by verification below: findings 3, 6 and 7 were only partly fixed, and this mutation run carried a hidden, unrelated runtime-origin failure.*
  - **Remaining limitations:**
    - There is still no isolation: the runner is `trusted_pipeline_only`.
    - The in-process recorder is not tamper-proof.
    - There is no expected-fold contract.
    - Inventory binding covers fixture files, not the installed environment.
    - Evaluation is limited to T-01 scope.
- **CODEX VERIFICATION OF REPAIR PASS 1, and REPAIR PASS 2 (Claude Code, Opus 5.5 high):**
  - **Evidence (preserved unchanged):**
    - `runs/review-t01-repair/probe.py` (sha256 `f0ddf8e8…337a`) and `results.json` (`f7e673b8…1950`);
    - `remaining_risks.py` (`fa310a91…f512`) and `remaining_results.json` (`02935f89…720c`).
  - **Checkpoints:** repair base `57506b1`; head = the local commit "Repair remaining T-01 review blockers" (parent `57506b1`).
  - **Blockers, traced causes and dispositions** (all accepted; each regression failed on `57506b1` and passes now):
    1. **Invalid orphan artifact invented a violation.**
       - *Cause:* `audit._compute` put unexpected prediction paths into the verified fold map keyed by file stem, with an `[]` sentinel. `predictions/orphan/fold0.parquet` overwrote fold0's verified rows, so a FAIL was produced. Repair pass 1 conflated path identity with fold identity and tested only a non-colliding stem.
       - *Repair:* the expected inventory is fixed as `predictions/<fold>.parquet` per declared fold. Unexpected paths are a separate list passed to the check and never read as rows. Events naming another artifact are inventory issues. Coverage also requires the conventional path.
       - *Same mechanism, sibling branch:* provenance could remap a fold to another fold's file; that is now an ERROR and a coverage gap.
       - *Tests:* `test_invalid_orphan_artifact_with_a_colliding_stem_is_an_evidence_error`, `test_provenance_cannot_remap_a_fold_to_another_folds_artifact`, plus two unit tests.
    2. **Null repeated-measures IDs suppressed a proven violation.**
       - *Cause:* repair pass 1 made unknown identity a precondition in `_repeated_measures`, returning NOT_ASSESSED before the rule ran. It also tested only group disjointness.
       - *Repair:* the rule is judged over known values first; unknown counts are disclosed per unit; NOT_ASSESSED is given only when no violation is established.
       - *Tests:* three on the repeated-measures assertion itself (direct unit, nested unit with a known group violation, and nested unit without one).
    3. **Recovery outputs had stale hashes.**
       - *Cause:* the unrecoverable-manifest early return wrote new outputs but kept the old `index.outputs`, including deleted check entries, because there were two finalization paths.
       - *Repair:* `_clear_outputs` also removes the index entries, and one `_finalize` (used by both paths) indexes exactly the files it wrote.
       - *Tests:* normal and unrecoverable-path integrity tests check that every indexed output exists, its hash is current, and every output is indexed.
    4. **A missing snapshot silently gave a clean result.**
       - *Cause:* the hash-matching fallback was treated as equivalent to the snapshot, which was my deliberate choice in repair pass 1, encoded in its test.
       - *Repair:* the fallback still reconstructs the required set, but every would-be PASS becomes ERROR (`evidence_invalid`). The outcome is `INCONCLUSIVE` unless an independently valid FAIL exists. No automatic restoration.
       - *Tests:* the corrected clean test (`test_missing_snapshot_reconstructs_the_required_set_without_crashing` now expects `INCONCLUSIVE`), `test_missing_snapshot_with_matching_fallback_keeps_errors_and_is_inconclusive`, `test_missing_snapshot_keeps_independent_valid_fails`.
    5. **Runtime validation ignored `safe_path`.**
       - *Cause:* omission.
       - *Repair:* `safe_path=true` is required.
       - *Same mechanism:* the execution record's `runner` and `capability` values are now checked too.
       - *Tests:* `test_rehashed_runtime_record_with_safe_path_false_is_rejected` and `test_rehashed_execution_record_claiming_another_capability_is_rejected`. These are validator tests on rehashed records; no import bypass was executed.
  - **Also done:**
    - The adapter comment now calls candidate-produced split events "corroborating", not independent.
    - **The runtime-origin test hardcoded `src/atlas`.** At base it failed against an unmutated temporary copy (reproduced: origin `…\Temp\atlas-unmutated-…\atlas` ≠ `src\atlas`), so every mutation run had an unrelated failure. It now requires the child's origin to equal the explicitly selected trusted root, which must also equal the package the test process imported (the temporary copy during mutation runs).
    - `scripts/mutation_check.py` now first runs an unmutated temporary copy, which must pass in full. Each mutation must trigger its intended test with no runtime-origin failure.
  - **Results actually run after repair pass 2:**
    - `uv run --locked pytest tests/unit tests/integration -q` → **115 passed**.
    - `scripts/mutation_check.py` → baseline copy ALL PASS; m1, m2 and m3 each CAUGHT with no unrelated runtime-origin failures ("mutations caught cleanly: 3/3"). m2's nine failures all depend on group overlap.
    - CLI → s01 `VIOLATION_FOUND`, s02 `NO_VIOLATION_FOUND`, s07 `INCONCLUSIVE`.
    - Output integrity (every indexed output exists with a current hash; no unindexed outputs) → consistent for the three CLI runs and two recovery paths (hash-matching fallback → `INCONCLUSIVE`; unrecoverable manifest → `INCONCLUSIVE`, 2 indexed outputs).
    - `ruff check` / `ruff format --check` → clean; `sync_skills.py --check` → problems 0.
  - **Remaining limitations:** no isolation (`trusted_pipeline_only`); the in-process recorder is not tamper-proof; there is no independent expected-fold contract; the inventory binds fixture files, not the installed environment; T-01 scope only.
- **CODEX VERIFICATION OF REPAIR PASS 2: one new regression, with a targeted fix (Claude Code, Opus 5.5 high):**
  - **Evidence (preserved unchanged):** `runs/review-t01-pass2/verify_pass2.py` (sha256 `e5fae9ad…bede1`), `verification.json` (`3a44d97e…83f1`), case `all_null_repeated_unit`. The script was not re-run, so its results were not overwritten.
  - **Checkpoints:** base `bdcf321`; head = the local commit "Require evidence before repeated-measures containment" (parent `bdcf321`).
  - **Finding:** repeated measures were declared on `session_id`, with all 160 session IDs null and known subjects shared across partitions. The repeated-measures rule FAILed (inheriting `split.no_group_overlap`) with zero known session identities. The group and unit FAILs themselves were valid.
  - **Cause:** repair pass 2 inverted the containment test to `known.groupby(col)[group].nunique().max() > 1` → `no_supported_rule`, else "contained". With every session ID null, the known-unit table is empty and `max()` is NaN; `NaN > 1` is `False`, so execution fell through to "contained" and inherited the group FAIL without supporting evidence. Absence of a counterexample was treated as proof of containment. (The pass-1 form `<= 1` failed closed only incidentally.)
  - **Fix:** `_containment()` returns "contained" only with positive evidence from rows participating in the declared splits: at least one known unit, every known unit has at least one known group, and none has more than one. An empty table or NaN aggregate gives "no_evidence" → NOT_ASSESSED `missing_metadata`, with nothing inherited. Mixed known/null data still inherits a demonstrated group violation, as verified previously.
  - **Scope details (deliberate):** containment is judged on participating rows only, the evidence relevant to the declared partitions. A unit whose group values are all unknown counts as no evidence.
  - **Regressions** (both failed on `bdcf321` and pass now): `test_all_null_nested_unit_is_not_assessed_while_independent_fails_stand` (unit) and `test_all_null_session_ids_with_shared_subjects_mirror_of_codex_reproduction` (the fixture-table mirror of Codex's case).
  - **Nearby cases**, focused tests with reasons and outcomes; these already held at base and still hold:
    - all-null on a grouped split → NOT_ASSESSED `missing_metadata`, `INCONCLUSIVE`;
    - partially null with a mixed split → FAIL via `split.no_group_overlap`, `VIOLATION_FOUND`;
    - complete identities on a grouped split → PASS, `NO_VIOLATION_FOUND`;
    - a null only on a non-participating row → PASS;
    - all group values unknown → NOT_ASSESSED `missing_metadata`.
  - **Results actually run:**
    - affected tests (`tests/unit/test_split_integrity.py`, `tests/integration/test_review_t01_repair.py`) → 36 passed;
    - `uv run --locked pytest tests/unit tests/integration -q` → **122 passed**;
    - `ruff check .` → passed; `ruff format --check .` → 59 files formatted.
    - **Mutation check not re-run.** The change alters no mutation target (the m2 line is byte-identical and present once) and not `scripts/mutation_check.py`; an optional re-run was declined by the user.
  - **Remaining limitations:** unchanged from repair pass 2.
- **CODEX CONTAINMENT PROBE, and the REPEATED-MEASURES REPAIR under policy-v1.1 (Claude Code, Opus 5.5 high):**
  - **Evidence (preserved unchanged):** `runs/review-t01-containment/probe.py` (sha256 `20a00a70…d899`), `results.json` (`ba45cd63…696c`). The probe was not re-run.
  - **Checkpoints:** base `6348767`; head = the local commit "Repeated measures: explicit routes and same-fold witnesses (policy-v1.1)" (parent `6348767`).
  - **Demonstrated defect:** in `partly_null_unrelated_overlap`, known session IDs existed only in disjoint groups across the partitions (known-participating group overlap: 0), yet `split.repeated_measures_rule` FAILed. Boundary `one_unknown_group_with_known_group_for_same_unit` reported "contained" (complete containment) despite a missing group assignment.
  - **Cause:** `_repeated_measures` inherited the aggregate `split.no_group_overlap` (or `split.sampling_unit_disjoint`) status instead of finding its own witness, and `_containment` collapsed completeness, missing assignments and contradictions into one label. The aggregate group FAIL was supported only by rows whose session was unknown.
  - **Repair, per the lead's clarification (DECISIONS.md, SPEC §5; policy `policy-v1` → `policy-v1.1`):**
    - Two explicit routes: A, sampling unit (per-fold known unit overlap, no group needed); B, contained group (participating-row mapping contradictions, missing unit and group counts, and per-fold group intersections from rows with both IDs known).
    - Witnesses record fold, row IDs, unit IDs and group IDs; route B witnesses are labeled `group_separation`.
    - One status rule per route. Nothing is inherited (`depends_on` is empty). The lossy `_containment` label is replaced by explicit facts: `complete`, `rows_with_unknown_identity`, `rows_missing_group`, `mapping_contradictions`, `witnesses`. The unused `results` parameter was removed.
  - **Tests:**
    - The defect fails on behavior at base (FAIL instead of NOT_ASSESSED), as does empty participation (`missing_metadata` instead of `not_executed`). Both pass now.
    - New coverage includes `test_partly_null_unrelated_overlap_mirror_of_codex_containment_probe`, `test_one_missing_group_never_yields_complete_containment_or_pass`, `test_overlap_only_through_unknown_unit_rows_has_no_witness`, group overlap with different session IDs, known plus missing group assignments with and without a witness, complete overlapping and complete disjoint cases, empty participation, cross-fold-only overlap, observed multi-group mapping, the sampling-unit route with an all-unknown group column, and multiple declared units.
    - Four earlier tests asserted inherited `depends_on`; those assertions now check the route and witness facts instead (a policy change, not a weakening). All-null cases from the previous fix still give NOT_ASSESSED `missing_metadata` with `VIOLATION_FOUND` from the independent FAILs.
  - **Results actually run:**
    - focused (`tests/unit/test_split_integrity.py`, `tests/integration/test_review_t01_repair.py`) → 49 passed;
    - full T-01 suite `uv run --locked pytest tests/unit tests/integration -q` → **135 passed**;
    - `ruff check` → passed; `ruff format --check` → 59 files formatted.
    - **Mutation check re-run** (repeated measures no longer inherits group status, so m2's detection assumptions changed): the unmutated baseline passes everything; m1, m2 and m3 are each CAUGHT with no unrelated runtime-origin failures. m2's ten failures are group/unit-dependent tests, and the repeated-measures tests no longer fail under m2, which confirms the decoupling.
  - **Remaining limitations:**
    - No mutation targets the new route logic itself; it is covered by the focused tests.
    - Empty-participation handling was changed only for `split.repeated_measures_rule`. The other split assertions can still PASS a fold with no participating rows; this is outside this repair's scope and is noted for review.
    - Otherwise unchanged from repair pass 2.
- **CODEX rm-v11 REVIEW: two bounded corrections (Claude Code, Opus 5.5 high):**
  - **Evidence (preserved unchanged):** `runs/review-t01-rm-v11/targeted.py` (sha256 `5aab69f4…69ea`), `targeted-results.json` (`69263ba8…7981`). The script was not re-run.
  - **Checkpoints:** base `58e4dee`; head = the local commit "Same-column route B and evaluation-fold prerequisite (policy-v1.2)" (parent `58e4dee`).
  - **1. Identical repeated-unit/group column.**
    - *Finding:* `group_equals_repeated_row` and `group_equals_repeated_session` raised `ValueError("Grouper for 'subject_id' not 1-dimensional")`.
    - *Cause:* `_contained_group_facts` selected `table[[col, group]]` four times (participating rows, per-fold parts, train, eval). With both roles on `subject_id`, that produced duplicate physical columns, breaking `groupby` and the per-column `isna`/`astype` calls.
    - *Fix:* one role-preserving selector `_roles()` builds a frame with fixed `unit` and `group` columns from two separately selected Series; all four selections use it. Policy-v1.1 semantics are unchanged: a shared column maps each unit to itself.
    - *Regressions (row and session sampling, 10 cases):* complete disjoint → PASS; known overlap → FAIL with witness; all missing → NOT_ASSESSED `missing_metadata`; partial missing with a witness → FAIL (missing counts disclosed); partial missing without a witness → NOT_ASSESSED `missing_metadata`. All raised at base.
  - **2. Empty-evaluation policy gap (lead-approved; DECISIONS.md, SPEC §5/§6).**
    - *Finding:* `empty_eval_evaluator_boundary` reached `NO_VIOLATION_FOUND` with every assertion PASSing over empty evaluation partitions.
    - *Fix:* a new required assertion `split.evaluation_folds_nonempty` for every claim type, computed in `split_assertions` and therefore enforced by the deterministic evaluator through the versioned policy, with reason `empty_evaluation`. Policy `policy-v1.1` → `policy-v1.2`.
    - *Regressions:*
      - zero evaluation rows → NOT_ASSESSED `empty_evaluation`;
      - mixed empty and nonempty folds → NOT_ASSESSED, `INCONCLUSIVE`;
      - an independent valid FAIL is preserved → `VIOLATION_FOUND`;
      - all nonempty → PASS;
      - zero folds → `not_executed`;
      - invalid evidence → ERROR;
      - required for every claim type;
      - through `evaluate()` on recorded evidence altered and rehashed to empty evaluation partitions (Codex's boundary input) → `INCONCLUSIVE`. At base this gave `NO_VIOLATION_FOUND` under policy-v1.1.
    - *Reference updates:* required-set expectations (eight → nine) and the policy-version string (`policy-v1.2`). No test was weakened and no fixture changed. A new scenario test confirms the prerequisite is PASS for every executed fixture.
  - **Results actually run:**
    - focused (`test_split_integrity.py`, `test_policy.py`, `test_review_t01_repair.py`) → 80 passed;
    - full T-01 suite → **165 passed**;
    - `ruff check` → passed; `ruff format --check` → 59 files formatted.
    - Mutation check (the required set changed): the unmutated baseline passes everything; m1, m2 and m3 are each CAUGHT, with no unrelated runtime-origin failures.
  - **Remaining limitations:**
    - The prerequisite covers evaluation partitions only; an empty *training* partition is not a separate assertion.
    - Other assertions can still PASS vacuously on empty folds, though the run can no longer be `NO_VIOLATION_FOUND`.
    - Otherwise unchanged from repair pass 2.

- **ACCEPTANCE (2026-10-14):** the lead accepted T-01 at `f5aa4dc` within its documented scope, based on Codex's independent verification (165 tests passed; no remaining blocker demonstrated in the reviewed scope). Accepted scope: the deterministic audit of trusted synthetic fixtures under `policy-v1.2` (split/group/observation checks, bounded fit provenance, prediction-ID matching, the evaluation-fold prerequisite, evidence JSON, outcome derivation).
  - **Not covered by this acceptance (documented limitations):**
    - no isolation (`trusted_pipeline_only` host runner; not a sandbox);
    - the in-process recorder is not tamper-proof;
    - no independent expected-fold contract;
    - the fixture inventory binds fixture files, not the installed environment;
    - empty training partitions are not a separate assertion;
    - assertions planned for T-02 are materialized as NOT_ASSESSED `unimplemented_assertion`.

### T-02 Independent metrics, conditional split rules, temporal checks
- **OWNER:** Claude Code (writer); Codex reviews.
- **MODEL DECISION:** STAY. Evaluator logic is core scientific code.
- **MODEL / EFFORT:** Claude Opus 5.5 high; Codex Extra high for the review if offered.
- **READ FIRST:** SPEC §5, §6, §8; T-01 evidence; DECISIONS.md F3, F5.
- **INPUT STATE:** T-01 accepted and committed. The lead's decision on any extra repeated-measures rule (SPEC §14) is recorded before acceptance.
- **CHANGE:**
  - `src/atlas/checks/{independent_metrics,temporal}.py`, `src/atlas/evaluator.py`;
  - `split.no_window_overlap` (stream identity, half-open intervals, containment-evidence pass-through);
  - `split.temporal_separation` (declared rule);
  - `temporal.training_labels_available_by_cutoff`, `temporal.cutoff_precedes_evaluation`, `temporal.features_available_when_used`;
  - `metric.reported_matches_recomputed` (canonical metrics; fixed absolute tolerance 1e-6, versioned; nonfinite/out-of-range rejected);
  - descriptive recomputation, baselines and `split.class_support`;
  - fixtures for `future_time` and `same_population`.
- **ACCEPTANCE (planned tests):**
  - **Metric recomputation:** recomputed balanced accuracy/macro-F1 match a hand-computed fixture; the dummy baseline is reported on identical partitions.
  - **The `future_time` counterexample:** a training prediction at 100 with label availability 150 and an evaluation prediction at 120 never PASSes. Cutoff 120 → `training_labels_available_by_cutoff` FAIL; cutoff 150 → `cutoff_precedes_evaluation` FAIL; no cutoff → NOT_ASSESSED.
  - **Feature availability:** a post-prediction feature → `features_available_when_used` FAIL.
  - **Windows:**
    - windows `[0,10)` and `[10,20)` in the same stream do not overlap;
    - `[0,10)` and `[5,15)` do;
    - a missing `stream_id` → NOT_ASSESSED `missing_metadata`;
    - a pass via disjoint groups only with recorded containment evidence.
  - **Temporal separation:** a `temporal_order` declaration without a `separation_rule` → NOT_ASSESSED `no_declared_rule`.
  - **Reported metrics:** a reported metric off by 2e-6 → FAIL; off by 5e-7 → PASS; NaN → rejected.
  - **Class support:** missing class support appears in `split.class_support`, never as a split FAIL.
  - **Trusted evaluator:** runs outside the candidate process and reads its own label copy.
- **RUN:** *(create)* targeted pytest modules; *(existing)* ruff check/format.
- **EVIDENCE:** run JSON per fixture; test output.
- **HANDOFF:** Codex review of the diff and evidence.
- **RECOVERY:** preserve failing fixtures. Two focused repairs, then Codex diagnosis.

### T-03 Hosting and isolated-worker probe (early, per playbook §11 Day 2)
- **OWNER:** Claude Code (research and documentation only); the lead decides.
- **MODEL DECISION:** SWITCH to Sonnet Medium (research/docs). Switch back to Opus High if an isolation design is evaluated.
- **MODEL / EFFORT:** Claude Sonnet 5.5 medium.
- **READ FIRST:** SPEC §10, §13; DECISIONS.md "Open hosting and access checks"; playbook §22.5.
- **INPUT STATE:** independent of T-01/T-02. Start early.
- **CHANGE:** `docs/HOSTING_PROBE.md` only. No purchases, paid plans or deployment.
- **ACCEPTANCE:**
  - each open check is answered with a dated source or an observed test;
  - a recommendation between limited hosted and full hosted, stating its evidence;
  - promotional-credit expiry against Dec 15, 2026, confirmed or marked unknown.
- **RUN:** none, or *(create)* a probe script if a free tier can be tested without spend.
- **EVIDENCE:** dated sources and observations.
- **HANDOFF:** the lead decides; record it in DECISIONS.md.
- **RECOVERY:** stay with the limited hosted baseline.

### T-04 Nebius access smoke (Start Here Step 10)
- **OWNER:** Claude Code (writer); the user enters the key privately.
- **MODEL DECISION:** STAY on Opus High (credential handling plus the runtime contract).
- **MODEL / EFFORT:** Claude Opus 5.5 high.
- **READ FIRST:** SPEC §11; `.env.example`; playbook §7.
- **INPUT STATE:** Nebius credits confirmed by the user. The builder names the exact variable and file before the user enters the key.
- **CHANGE:** `scripts/nebius_smoke.py`; `.env` (user-entered, git-ignored).
- **ACCEPTANCE:**
  - the authenticated `GET /models` lists real NVIDIA model IDs;
  - one capped structured-output call succeeds and its response is validated;
  - sanitized evidence is saved;
  - the key is never echoed or committed.
- **RUN:** *(create)* `uv run --locked python scripts/nebius_smoke.py`
- **EVIDENCE:** sanitized model list and call record.
- **HANDOFF:** STATUS.md update; record the chosen model ID in DECISIONS.md.
- **RECOVERY:** if access is pending, mark the external blocker and continue offline.

### T-05 Isolated runner and approval (Start Here Step 10)
- **OWNER:** Claude Code (writer); Codex reviews.
- **MODEL DECISION:** STAY on Opus High (isolation contract).
- **MODEL / EFFORT:** Claude Opus 5.5 high; Codex Extra high for the review if offered.
- **READ FIRST:** SPEC §9, §10; AGENTS.md "Isolation".
- **INPUT STATE:** Docker Desktop installed and running (the user handles OS prompts and restarts). T-01 committed.
- **CHANGE:** `src/atlas/runner/docker.py`, `Dockerfile.runner`, candidate validation and hash-bound approval (SPEC §9), `tests/integration/test_runner_contract.py`.
- **ACCEPTANCE:** the contract tests show that:
  - there is no network;
  - no secrets exist in the environment;
  - the root filesystem is read-only;
  - the memory/PID/time limits trigger;
  - path escapes, evaluator/label writes and changed-hash execution are refused;
  - unavailable isolation results in no execution.

  A Docker hello-world alone does not count.
- **RUN:** *(create)* `uv run --locked pytest tests/integration/test_runner_contract.py`
- **EVIDENCE:** contract-test output; capability state in run JSON.
- **HANDOFF:** Codex review.
- **RECOVERY:** stay `trusted_pipeline_only`; never fall back to the host.

### T-06 Bounded live agent loop
- **OWNER:** Claude Code (writer); Codex reviews.
- **MODEL DECISION:** STAY on Opus High (agent and tool-dispatch logic).
- **MODEL / EFFORT:** Claude Opus 5.5 high; Codex High review.
- **READ FIRST:** SPEC §9, §11; T-04 evidence (model ID, response-format support).
- **INPUT STATE:** T-02, T-04, T-05 accepted.
- **CHANGE:** `src/atlas/agent/` (client, state machine, typed tools, ceilings, logging).
- **ACCEPTANCE:**
  - one real NVIDIA call → valid action → checks → approved isolated candidate → re-check → report citing evidence;
  - invalid model output, timeout and budget exhaustion each end in a recorded state;
  - fixture-mode runs are visibly labeled non-live.
- **RUN:** *(create)* `uv run --locked python -m atlas.cli audit benchmarks/sensor_generalization --mode agent`
- **EVIDENCE:** agent log with model ID, usage and timings.
- **HANDOFF:** Codex review.
- **RECOVERY:** two focused repairs, then Codex diagnosis.

### T-07 UI path and browser tests (Start Here Step 12; playbook §25)
- **OWNER:** Claude Code (writer); Codex reviews the UI.
- **MODEL DECISION:** SWITCH to Opus High for `docs/UI_SPEC.md`, then Sonnet Medium for the build. Back to Opus if failures reach core logic.
- **MODEL / EFFORT:** Opus 5.5 high, then Sonnet 5.5 medium; Codex High review.
- **READ FIRST:** PRD workflow and outcome labels; SPEC §6, §13; playbook §20, §25.
- **INPUT STATE:** engine paths from T-01/T-02 (T-06 for live runs); the UI skills installed per playbook §25 at that time.
- **CHANGE:** `docs/UI_SPEC.md`, `app.py`, `tests/acceptance/`.
- **ACCEPTANCE:**
  - one complete path (select → confirm claim → analyze → finding → revision comparison → export) with empty, running, failure, unsupported and completed states;
  - the playbook §20 scenarios pass with Playwright against the running app;
  - hosted-mode labels ("not executed here") are present.
- **RUN:** *(create)* `uv run --locked pytest tests/acceptance`, after `uv add --dev pytest-playwright` and `uv run playwright install chromium` (playbook §22.4).
- **EVIDENCE:** traces and screenshots on failure; a manual walkthrough note.
- **HANDOFF:** Codex High review; Gemini Medium for the demo later.
- **RECOVERY:** the playbook §20 bounded repair loop.

### T-08 Procedures and transfer benchmark
- **OWNER:** Claude Code (writer); Codex reviews; Gemini reviews the evaluation claims.
- **MODEL DECISION:** STAY on Opus High (memory semantics).
- **MODEL / EFFORT:** Claude Opus 5.5 high; Codex High; Gemini Argon High.
- **READ FIRST:** SPEC §12; playbook §8, §9 (Example two); DECISIONS.md L1.
- **INPUT STATE:** T-02 accepted; T-05/T-06 for executed reuse.
- **CHANGE:** `src/atlas/procedures/`, `benchmarks/procedure_transfer/` (Variants A and B).
- **ACCEPTANCE (planned tests):**
  - **Admission:** refused unless every applicable required assertion has a valid PASS. Refused on an empty required set or incomplete coverage.
  - **Variant A:** `reuse_succeeded` only when the full required set has valid PASSes after execution.
  - **Variant B:** `reuse_rejected(claim_mismatch)` before execution. A temporal violation is reported only if its check establishes one.
  - **After a rejection:** a fresh attempt is recorded separately.
- **RUN:** *(create)* `uv run --locked python -m atlas.cli procedures check <id> benchmarks/procedure_transfer/variant_b`
- **EVIDENCE:** run JSON per variant.
- **HANDOFF:** Codex review; Gemini on claims.
- **RECOVERY:** two focused repairs, then Codex diagnosis.

### T-09 Real-data example (UCI HAR) and clean control
- **OWNER:** Claude Code (writer); Gemini reviews the claims; lead reviews the containment evidence.
- **MODEL DECISION:** STAY on Opus High (scientific protocol).
- **MODEL / EFFORT:** Claude Opus 5.5 high; Gemini Argon High.
- **READ FIRST:** SPEC §17 "UCI HAR example"; DECISIONS.md F4; the dataset page (https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones).
- **INPUT STATE:** T-02 accepted.
- **CHANGE:** `benchmarks/real_sensor/` (retrieval script and CC BY 4.0 attribution; no committed raw data unless the license terms are met and attribution is included); a containment-evidence note; robustness reporting.
- **ACCEPTANCE (planned):**
  - **Claim and partitions:** claim `unseen_group` by subject. The official test partition is never used for development or tuning; development uses grouped folds within the training subjects.
  - **Flawed variant:** any flawed variant is labeled ATLAS-authored.
  - **Window overlap:** `split.no_window_overlap` PASSes only via recorded containment evidence; otherwise NOT_ASSESSED.
  - **Temporal assertions:** none claimed.
  - **Upstream preprocessing:** the report states that provenance begins at the supplied feature table, and that global fitting of upstream normalization is not established.
- **RUN:** *(create)* the retrieval and audit commands.
- **EVIDENCE:** run JSON; the limitations section; the attribution text.
- **HANDOFF:** Gemini review of the claims.
- **RECOVERY:** if the dataset is unsuitable, document why and pick the next licensed candidate with the lead.

### T-10 Held-out cases and campaign protocol (Q6)
- **OWNER:** Codex (separate session, outside this repo) authors and validates the cases and their expected violated assertion IDs. Claude writes only the predeclared campaign protocol and never receives case contents, answer keys or case-specific feedback.
- **MODEL DECISION:** SWITCH for case authoring (Codex, separate session). Claude stays Opus High for the protocol text.
- **MODEL / EFFORT:** Codex High (authoring); Claude Opus 5.5 high (protocol).
- **READ FIRST:** DECISIONS.md Q6, F5; SPEC §8, §17.
- **INPUT STATE:** adapter and policy versions frozen enough to state in the freeze record (after T-02).
- **CHANGE (this repo):** `docs/EVALUATION.md` campaign protocol: model and settings, budgets, repetitions, infrastructure-failure handling, scoring (SPEC §17), and reporting of all results.
- **ACCEPTANCE:**
  - the hashes, contract/evaluator/policy versions and freeze date are recorded in DECISIONS.md before any use;
  - expected violated assertion IDs are fixed before measurement;
  - the protocol is committed before results are revealed.
- **RUN:** none in this repo until the campaign.
- **EVIDENCE:** freeze record.
- **HANDOFF:** Codex runs the campaign at release-candidate time.
- **RECOVERY:** if a case is used for debugging, retire it and obtain a replacement before a fresh held-out claim.

### T-11 Three-way comparison pilot
- **OWNER:** Claude Code (writer); Gemini reviews the claims.
- **MODEL DECISION:** STAY on Opus High (evaluation design).
- **MODEL / EFFORT:** Claude Opus 5.5 high; Gemini Argon High.
- **READ FIRST:** DECISIONS.md Q4, F5; SPEC §17; playbook §9 "Measuring agent value".
- **INPUT STATE:** T-06 and T-08 accepted; prices verified (T-04/T-03); expected violated assertions defined.
- **CHANGE:** `evaluation/` harness for `audit` / `agent` / `agent+memory`, with matched inputs, policy, tools, model settings and budgets, randomized order and recorded cache state.
- **ACCEPTANCE:**
  - the procedure store is frozen and its hash recorded before the first repetition;
  - three paired repetitions on Variant A, each with fresh run state and no admissions in between;
  - TP/FP/FN per canonical assertion ID, coverage gaps and errors reported; precision/recall undefined when a denominator is zero;
  - repair success and token use reported across the agent modes, and procedure-creation cost separately;
  - all scheduled trials reported; results described as descriptive.
- **RUN:** *(create)* `uv run --locked python -m atlas.cli evaluate --suite comparison`
- **EVIDENCE:** results table plus raw logs.
- **HANDOFF:** Gemini review of the claims.
- **RECOVERY:** report null or negative results as measured.

### T-12 Limited hosted demo and judge access
- **OWNER:** Claude Code (writer); the lead approves any paid usage.
- **MODEL DECISION:** SWITCH to Sonnet Medium for deployment plumbing; Opus High for cost-control and key-handling logic.
- **MODEL / EFFORT:** Sonnet 5.5 medium / Opus 5.5 high.
- **READ FIRST:** SPEC §13; T-03 decision; DECISIONS.md Q5.
- **INPUT STATE:** T-03 decision; T-07 UI; verified prices.
- **CHANGE:** deployment configuration, server-side caps, judge route or reserved capacity, exhaustion and restoration behavior, labels.
- **ACCEPTANCE:**
  - a signed-out browser completes the curated workflow;
  - caps trigger correctly in a test;
  - the judge route survives exhaustion of the public budget;
  - keys stay server-side;
  - replay is disclosed.
- **RUN:** *(create)* the deployment smoke and acceptance scenarios against the hosted URL.
- **EVIDENCE:** URL, test output, cost log.
- **HANDOFF:** lead approval before any paid usage.
- **RECOVERY:** the tested local build stays the fallback.

### T-13 Release package (Start Here Steps 13–14)
- **OWNER:** Claude Code (writer); Codex checks release blockers; Gemini critiques the video.
- **MODEL DECISION:** SWITCH to Sonnet Medium (packaging, docs).
- **MODEL / EFFORT:** Sonnet 5.5 medium; Codex Extra high for the final review if offered.
- **READ FIRST:** playbook §14, §23; `docs/SUBMISSION_CHECKLIST.md`.
- **INPUT STATE:** feature freeze (Oct 25–26).
- **CHANGE:** README, LICENSE (MIT), data and dependency notices, sanitized example report, `docs/SUBMISSION_CHECKLIST.md` evidence.
- **ACCEPTANCE:** a fresh install runs the offline example; every quoted metric regenerates; the submitted links are checked signed out.
- **RUN:** *(create)* a release-check script.
- **EVIDENCE:** checklist rows with paths and URLs.
- **HANDOFF:** the user submits on Devpost.
- **RECOVERY:** fix blockers only after the freeze.
