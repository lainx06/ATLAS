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
| T-02 | 11 | **Accepted by the lead at `75a98f4`** within its documented trusted-fixture scope (2026-10-15), on Codex's independent verification of every repair pass. Contract policy-v1.3, manifest schema 0.3. Limitations stand (see ACCEPTANCE) | Independent metrics, conditional split rules (windows, separation), `future_time` assertions, reported-metric comparison |
| T-03 | 11 (early) | **Accepted by the lead at `51d3dd8`** within its documented research-and-feasibility scope (2026-10-16). Limited hosted plus local Docker for V1; Neon selected as the budget store; stages B/C and production budget controls are carried by T-12. Not established: production readiness, guaranteed availability, credit eligibility, remote isolation compliance | Hosting and isolated-worker probe (docs/evidence only) |
| T-04 | 10 | **Accepted by the user within its documented smoke-test scope** (2026-10-14). Model `nvidia/nemotron-3-super-120b-a12b`; prompt-requested JSON, application-validated | Nebius access: model list, capped structured-output smoke call |
| T-05 | 10 | **Accepted by the lead at `eed73ee`** within its documented scope (2026-10-15), on Codex's independent verification of repair pass 2: both remaining parser findings verified fixed; contract suite 28/28 with Docker required. Limitations stand, including a P3 Windows path-length limit (see ACCEPTANCE). Candidate re-evaluation and `audit.py` integration are T-06 | Isolated runner and hash-bound candidate approval |
| T-06 | 11 | **Accepted (2026-10-18)** by the lead within its documented scope, at `199a173` on `main`: live run 6 end to end (an approved isolated candidate re-checked NO_VIOLATION_FOUND, 4 FAIL -> PASS), the recorded failure states of live runs 2-6, Gates 1-3 PASS, Gate 4 and combined review 1 FAIL resolved. Limitations stand (see ACCEPTANCE) | Bounded live agent loop end to end |
| T-07 | 12 | **Built** (`03eab30`…`822ee27`, on `main` 2026-10-17): 17 acceptance scenarios passed with Docker required. Awaiting the combined Codex review | UI spec, one complete Streamlit path, Playwright scenarios |
| T-08 | 11 | **CUT** (lead, 2026-10-17; DECISIONS.md "Lead decisions, 2026-10-17" item 2) | Procedures: admission, reuse, refusal; transfer benchmark |
| T-09 | 11 | **Built** (`5e4c22f`…`f5d76c9`, on `main` 2026-10-17): `har_flawed` VIOLATION_FOUND, `har_clean` NO_VIOLATION_FOUND, both in Docker; in the UI with typed approval (2 scenarios passed). License terms OPEN (user decision before T-12). Awaiting the combined Codex review | Real-data example, clean control, robustness reporting |
| T-10 | 11 | **REDUCED** (lead, 2026-10-17): at most 3 unfamiliar cases | Held-out cases (Codex, outside repo) and predeclared campaign |
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
- **INPUT STATE:** T-01 accepted and committed. The lead's decision on any extra repeated-measures rule (SPEC §14) is recorded before acceptance. **Recorded 2026-10-15:** no rule beyond routes A and B (DECISIONS.md, "Repeated-measures scope for V1").
- **CONTRACT (decided by the lead 2026-10-15):** `docs/specs/t02-contract.md` was reviewed in full and approved with corrections (DECISIONS.md, "T-02 contract dispositions"; SPEC §3, §4.2, §5, §8; policy-v1.3, manifest schema 0.3). Implementation is authorized on trusted fixtures only, with no inference calls and no Docker-runner integration. The ACCEPTANCE tests below are unchanged; the decided contract adds tests for its corrections.
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
- **RESULT (2026-10-15; self-tested, awaiting Codex review; NOT accepted):**
  - **Checkpoints:** base `52c99c8` (T-05 acceptance); head = the local commit "T-02: time, window and metric checks (policy-v1.3)" (parent `52c99c8`). `policy_version` names the rules, not the code; this commit is the reviewed implementation.
  - **Same commit, documents:** the lead's repeated-measures scope decision and the T-02 contract dispositions (DECISIONS.md), SPEC §3, §4.2, §5, §8 and §14, and `docs/specs/t02-contract.md` (the decided contract with worked examples).
  - **Files:**
    - New: `src/atlas/checks/temporal.py`, `src/atlas/checks/independent_metrics.py`, `src/atlas/evaluator.py`.
    - Changed: `src/atlas/contracts.py`, `intake.py`, `policy.py`, `audit.py`, `runner/trusted.py`.
    - New tests: `tests/unit/test_temporal.py`, `test_independent_metrics.py`, `test_manifest_schema.py`, `tests/integration/test_t02_scenarios.py`.
    - New fixtures: `benchmarks/t02/` (generator, README, 5 fixtures); the allowlist was regenerated over both roots.
    - Not changed: `split_integrity.py`, `fit_provenance.py`, `recorder.py` (the mutation-check targets), `adapter.py`, the Docker runner, and every T-01 fixture byte.
  - **Implemented (policy-v1.3):**
    - **Manifest schema 0.3:** typed temporal and metric fields. Booleans, strings, nonfinite and out-of-range values are rejected at intake as `NOT_SUPPORTED`, with the failing fields named. Legacy 0.2 is accepted with an unspecified scope; other versions are rejected.
    - **`split.no_window_overlap`:** route D (stream membership or interval comparison, with the basis recorded) and route C (documented containment, conditional on a valid `split.no_group_overlap` PASS, with the declaration recorded verbatim). A contradiction gives `no_supported_rule`. Needed bounds must satisfy `start < end`.
    - **`split.temporal_separation`:** two-sided, per fold, with a declared point or window basis.
    - **The three `temporal.*` assertions:** the cutoff checks need a global clock; feature availability is checked row by row on any clock.
    - **`metric.reported_matches_recomputed`:** per entry, worst-of, using the literal float64 rule.
    - **Descriptive results** (`metric.recomputed_primary`, `metric.baselines` with the most-frequent dummy and the linear baseline deferred, `split.class_support`) are written to `outcome.json` and the check files, separately from required assertions. They never enter outcome derivation.
  - **Tests and evidence** (logs git-ignored in `runs/t02/`):
    - New unit tests:
      - `test_temporal.py` (51): window routes; the start < end policy; contradictions; separation direction and basis; the 100/150/120 counterexample; global versus local clocks; invalid cutoffs; FAIL preservation.
      - `test_independent_metrics.py` (38): E1–E3 by hand and against scikit-learn; label canonicalization; completeness of aggregates; the tolerance boundary and adjacent floats; the 5/9 + 1e-6 example; baselines and class support.
      - `test_manifest_schema.py` (64): every field rule; booleans, nonfinite values and strings; intake explanations; all 19 committed manifests.
    - `tests/integration/test_t02_scenarios.py` (14), on the 5 fixtures:
      - s11a label leak → VIOLATION_FOUND (24 witnesses);
      - s11b clean → NO_VIOLATION_FOUND, with the reported metrics equal to scikit-learn's own values;
      - s11c misreported by 0.01 → VIOLATION_FOUND (the other entry still PASSes);
      - s12a random windows → VIOLATION_FOUND;
      - s12b blocked windows → NO_VIOLATION_FOUND, with the smallest gap exactly 5;
      - also: descriptive results never decide the outcome; a corrupted prediction artifact → ERROR; a NaN reported value → NOT_SUPPORTED before execution; the generator reproduces the tables.
    - **Approved expectation changes (DECISIONS items 8 and 9), not weakenings:**
      - s07 → window PASS (basis `stream_membership_disjoint`) and `NO_VIOLATION_FOUND`. Its policy-v1.2 result, INCONCLUSIVE, remains the historical record. A new test checks the basis.
      - The policy-version assertion now expects v1.3.
      - The unimplemented-assertion test now models a build without the window check, so the unimplemented path keeps independent coverage.
      - The allowlist test now covers both fixture roots, which is stricter.
    - `uv run --locked pytest tests/unit tests/integration --deselect tests/integration/test_runner_contract.py` → **500 passed, 1 skipped** (the existing symlink-permission skip). Log: `runs/t02/unit-integration.log`.
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py` → **28 passed**, rerun because `contracts.Manifest` (used by `candidates.py`) changed. Log: `runs/t02/contract.log`. No `atlas.runner=t05` containers remained.
    - **Sensitivity probe** (ad hoc; not `scripts/mutation_check.py`): 10 defects applied to a temporary copy of the new code were each caught by the new unit tests (`runs/t02/probe_mutations.py`, `probe_mutations.log`). The defects were: adjacent windows as overlap, zero-length windows accepted, one-sided separation, a global clock demanded for feature availability, label equality failing, route C ignoring the group result, an aggregate dropping unusable folds, a strict `<` tolerance, balanced accuracy averaging absent classes, and baseline ties by sorted label.
    - `ruff check .` and `ruff format --check .` → clean. Regenerating `benchmarks/t02` is byte-identical.
    - **Not rerun:** `scripts/mutation_check.py`. Its targets (`fit_provenance.py`, `split_integrity.py`, `recorder.py`) and the script are unchanged, and the meaning of its must-fail tests (s01, s03a, the reuse rule) is unchanged. 0 inference calls; no Docker-runner integration.
  - **Limitations:**
    - Times are compared as float64: integers beyond 2^53 lose precision. There is no date parsing or unit conversion.
    - Cutoffs and fold membership are declared by the evaluated code; the checks test the data against them, not the declarations themselves.
    - Route C relies on a documented declaration that ATLAS neither verifies nor fetches. UCI HAR containment needs the T-09 review.
    - `final_holdout` reported metrics are NOT_ASSESSED until the evaluator-only label store exists.
    - Splitter minimum requirements are unavailable (not recorded), and the linear baseline is deferred.
    - Window and separation checks compare all train × eval pairs per stream (chunked): fine at fixture scale, untested at large scale.
    - The checks verify declared rules, not statistical independence. They run on trusted fixtures only (`trusted_pipeline_only`).

- **CODEX REVIEW 1 (local Codex, of `487664e`, 2026-10-15) and REPAIR PASS 1 (Claude Code, Opus 5.5 high):**
  - **Review evidence:** preserved unchanged at `runs/review-t02/r487/` (git-ignored). A hash manifest of `runs/review-t02/` (2,314 lines) was identical before and after this repair. Key files:
    - `review.md` (`b785a7bf…ae7bdff9`);
    - `probe.py` (`ae01bbf9…8b7b7ca6`) and `probe-results.json` (`9efcd5b3…160d9baa`);
    - `evaluate_probes.py` (`fb13e20b…25285ab3`) and `evaluate-results.json` (`720d93dc…7b43665b`).

    Codex's run: 500 passed, 1 skipped. The 14 T-01 allowlist entries were unchanged. Verdict: request changes. Four P2 findings; every other route and all nine dispositions behaved as specified.
  - **Checkpoints:** base `487664e`; head = the local commit "Repair T-02 after Codex review 1" (parent `487664e`).
  - **Findings, causes and repairs:**
    1. **A missing value suppressed a demonstrated cutoff violation.**
       - *Cause:* `_labels_by_cutoff` treated a row as unknown when either its prediction time or its label time was missing, before comparing either one. A known prediction time after the cutoff with a missing label time (or the converse) gave NOT_ASSESSED, and the full evaluator reported INCONCLUSIVE instead of VIOLATION_FOUND. An absent label column returned early in the same way.
       - *Repair:* each known value is compared on its own. A witness records which values are after the cutoff. Missing prediction and label times are counted separately, per fold, and a row with no known late value and a missing value is "undecided", which prevents PASS. A missing prediction-time column or label source now gives unknown values instead of an early return. The global-clock prerequisite is unchanged.
    2. **A shared stream/group column crashed the window check.**
       - *Cause:* `_stream_group_contradictions` selected `[stream_col, group_col]`. When both name one physical column, pandas created two columns with the same name and `groupby` raised. The crash was reachable whenever the direct route was incomplete, with or without a containment declaration, and the evaluator left no `outcome.json`.
       - *Repair:* each role is selected as its own named Series, the pattern already used by `split_integrity._roles`. A shared column cannot show a stream in two groups. Missing-data semantics are unchanged.
    3. **An integer beyond the float64 range escaped validation and reporting.**
       - *Cause:* `math.isfinite(10**400)` and `float(10**400)` raise `OverflowError`, which neither pydantic nor the evaluator treated as invalid input.
       - *Repair:* `contracts._finite_number` converts with an overflow guard and reports "must be finite (outside the float64 range)", so intake gives `NOT_SUPPORTED` naming the field. `temporal.time_value` maps overflow to unknown, so a cutoff becomes invalid (ERROR `evidence_invalid`) and a table time becomes unknown.
       - *Nearby paths, same cause:* `evaluator.canonical_label` now treats float overflow (for example a huge `Fraction`) and Python's integer-to-string digit limit as "not a label".
       - Large finite values (10**300) stay valid.
    4. **Duplicate fold identifiers overwrote invalid metric evidence.**
       - *Cause:* metric scores were keyed by fold name, so a later same-named fold replaced an earlier unusable one. The aggregate then counted the later fold twice and reported `complete: true` and PASS.
       - *Repair:* repeated identifiers are detected before anything is keyed by name. Scores stay aligned with the declared splits, and every fold with a repeated name is unusable (ERROR `evidence_invalid`, "fold identifier declared more than once"). Aggregates including them are incomplete, single-fold entries naming them are ERROR, and unrelated folds keep their values. The dummy baseline marks them unusable, class support flags them, and both outputs list the duplicate identifiers.
  - **Tests.** RED at `487664e`, from a temporary `git archive` copy of `src/atlas` placed first on `PYTHONPATH`: **31 failed, 3 passed** (`runs/t02r/red-at-base.log`). 34 new test items; the 3 that pass at base are guards by design:
    - complete direct routes with a shared column;
    - large finite values staying valid;
    - the 5,000-digit JSON case.

    All pass after the repair.
    - `tests/unit/test_temporal.py`:
      - `test_known_late_value_fails_despite_the_other_value_missing[both directions]`;
      - `test_absent_label_source_still_preserves_a_late_prediction`;
      - `test_missing_value_without_a_known_late_value_is_missing_metadata` (fails at base only on the new disclosure field);
      - `test_shared_stream_group_column_*` (complete direct routes; incomplete with and without a declaration; unknown stream);
      - `test_integer_beyond_float64_is_not_a_time`;
      - `test_oversized_cutoff_is_an_evidence_error`;
      - `test_oversized_cutoff_does_not_hide_a_fail_in_another_fold`.
    - `tests/unit/test_independent_metrics.py`: `test_duplicate_fold_identifiers_*[invalid_first|valid_first]` (entries, aggregates, descriptive results) and `test_oversized_numbers_are_not_labels`.
    - `tests/unit/test_manifest_schema.py`: `test_integer_beyond_float64_is_rejected[5 fields]`, `test_large_but_finite_values_stay_valid`, `test_intake_names_an_oversized_reported_value[401|5000]`.
    - `tests/integration/test_t02_scenarios.py` (full evaluator; executes trusted s11b, then evaluates changed and re-hashed copies of its evidence):
      - `test_known_cutoff_violation_with_a_missing_value_is_violation_found[3 cases]`;
      - `test_shared_stream_group_column_writes_an_outcome[undeclared|declared]`;
      - `test_oversized_cutoff_is_recorded_and_a_supported_fail_is_preserved`;
      - `test_oversized_reported_value_is_not_supported_with_the_field_named`;
      - `test_duplicate_fold_identifier_is_an_evidence_error[invalid_first|valid_first]`.
  - **Actual results (2026-10-15):**
    - `uv run --locked pytest tests/unit tests/integration -q --ignore=tests/integration/test_runner_contract.py --basetemp=runs/t02r/f` → **534 passed, 1 skipped** (the existing symlink-permission skip). Log: `runs/t02r/full-suite.log`.
    - Codex's probes, run from copies in `runs/t02r/probes/` (originals not run or modified). `probe.py` ran unchanged. `evaluate_probes.py` was adapted twice (`adaptation.diff`): it reads Codex's preserved runs read-only, and its duplicate-fold setup no longer finds a complete aggregate value to copy, which is the repaired behavior.
      - *After:* partial label → labels FAIL, VIOLATION_FOUND; aliased columns → window NOT_ASSESSED, outcome written; huge cutoff → ERROR, outcome written; oversized manifest → NOT_SUPPORTED naming `reported_metrics.0.value`; duplicate fold → reported ERROR. See `summary.txt`.
    - `ruff check .` and `ruff format --check .` → clean.
    - **Not rerun:**
      - The Docker contract suite. The only shared dependency, `contracts._finite_number`, changes behavior only for integers beyond float64, which no runner manifest uses. No runner, candidate or container code changed.
      - `scripts/mutation_check.py`. Its targets (`fit_provenance.py`, `split_integrity.py`, `recorder.py`) are unchanged.
      - 0 inference calls. No fixture, expected value or policy changed.
  - **Remaining limitations (repair pass 1):**
    - A number with more digits than the JSON parser accepts (about 4,300 or more) is rejected by pydantic's JSON parser before field validation. Intake still gives `NOT_SUPPORTED`, but the reason names a position ("number out of range at line 1 column N"), not the field.
    - Duplicate fold identifiers are refused only by the metric assertions. The adapter still accepts them. Other checks surface their effects in Codex's reproduction (row-overlap FAIL, coverage gaps), but they do not name the duplication.
    - The RESULT limitations above stand. **T-02 remains unaccepted** pending independent verification of this repair.
- **CODEX VERIFICATION OF REPAIR PASS 1 (local Codex, at `0cf955d`, 2026-10-15) and REPAIR PASS 2 (Claude Code, Opus 5.5 high):**
  - **Review evidence:** preserved unchanged at `runs/review-t02/r0cf/` (git-ignored). A hash manifest of `runs/review-t02/` (4,885 lines) was identical before and after this repair. Key files:
    - `review.md` (`716457dd…88ec8ee3`);
    - `focused.py` (`22ccd7e1…a583eb40`) and `focused-results.json` (`0fb8682a…457b8f39`).

    Codex's run: 534 passed, 1 skipped.
  - **Codex's disposition:**
    - All four review-1 findings are **verified fixed**: independent cutoff comparisons, the shared stream/group column, numeric overflow at the three helpers, and duplicate fold identifiers in both orderings.
    - No fixture, allowlist, policy, existing expected value or existing assertion changed.
    - **One more P2:** a 5,000-digit integer `training_cutoff` in hash-matching `splits.json` raised an uncaught `ValueError` from `json.loads` in `audit._compute`, before `time_value` could classify it. Outputs had already been cleared, so no `outcome.json` was written. This is newly demonstrated pre-existing behavior, not a regression.
    - The paired 5,000-digit *manifest* case is safe: `NOT_SUPPORTED`, with a position-based diagnostic.
  - **Checkpoints:** base `0cf955d`; head = the local commit "Repair T-02 split-evidence decoding after Codex verification" (parent `0cf955d`).
  - **Cause:** `splits.json` was hash-verified and then decoded with an unguarded `json.loads`. Python refuses to convert integer strings longer than 4,300 digits, and the resulting `ValueError` escaped `evaluate()`. Malformed JSON, invalid UTF-8 (both `ValueError` subclasses) and nesting deep enough for `RecursionError` escaped the same line.
  - **Repair:**
    - A new helper, `audit._load_splits`, decodes the verified bytes and turns `ValueError`/`RecursionError` into a recorded problem. `splits_ok` becomes false, so every assertion that depends on the splits takes the existing invalid-evidence path, ERROR(`evidence_invalid`), and the descriptive results are unavailable.
    - The problem, "splits.json could not be decoded (…)", is added to the outcome's reason. Finalization writes `outcome.json`, `report.json` and the check files, and indexes them with current hashes.
    - Python's digit limit is not raised. No fold is dropped or partially parsed, and policy is unchanged.
    - Every required T-02 and T-01 assertion depends on the split evidence, so no independent FAIL can survive undecodable splits. The finer-grained case of a cutoff beyond float64, where an independent FAIL in another fold survives, is still covered by repair pass 1's regression.
  - **Tests:**
    - `tests/integration/test_t02_scenarios.py::test_undecodable_hash_matching_splits_is_an_evidence_error[integer_5000_digits|malformed_json|invalid_utf8|deep_nesting]`, a full-evaluator regression.
    - It executes trusted s11b, evaluates once, writes hash-matching undecodable `splits.json`, and evaluates again. It asserts that:
      - evaluation returns;
      - every required assertion is ERROR(`evidence_invalid`) and the outcome is INCONCLUSIVE;
      - the reason names `splits.json`, and the descriptive results are unavailable;
      - `outcome.json` lists the required assertions;
      - the indexed outputs equal the files on disk, with current hashes.
    - **RED at `0cf955d`**, from a temporary `git archive` copy placed first on `PYTHONPATH`: **4 failed** (`runs/t02r2/red-at-base.log`), with `ValueError` (the 4,300-digit limit), `JSONDecodeError`, `UnicodeDecodeError` and `RecursionError`. All 4 pass after the repair.
  - **Actual results (2026-10-15):**
    - Audit and evidence-error suites: `uv run --locked pytest tests/integration/test_t01_scenarios.py tests/integration/test_review_t01.py tests/integration/test_review_t01_repair.py tests/integration/test_t02_scenarios.py tests/integration/test_cli.py tests/unit/test_policy.py --basetemp=runs/t02r2/c` → **108 passed** (`runs/t02r2/audit-tests.log`).
    - A copy of Codex's `json5000_runtime` case (`runs/t02r2/json5000_runtime.py`; paths only adapted) → INCONCLUSIVE; every assertion ERROR(`evidence_invalid`); `outcome.json` written.
    - `ruff check .` and `ruff format --check .` → clean.
    - **Not run, as instructed:** the full suite, Docker and the mutation check. The change is confined to how `audit.py` decodes `splits.json`; the decoding of valid splits is byte-for-byte unchanged. 0 inference calls.
  - **Remaining limitations (repair pass 2):**
    - **Sibling decoder, identified by inspection and not demonstrated or repaired** (this pass was scoped to the split boundary): `audit._read_events` decodes `provenance.jsonl` with the same unguarded `json.loads`. A hash-matching provenance line with an over-limit integer would likely escape `evaluate()` the same way.
    - The repair pass 1 limitations stand. **T-02 remains unaccepted** pending independent verification of this repair.
- **CODEX VERIFICATION OF REPAIR PASS 2 (local Codex, at `bb9bac8`, 2026-10-15) and REPAIR PASS 3 (Claude Code, Opus 5.5 high):**
  - **Review evidence:** preserved unchanged at `runs/review-t02-pass2/bb9/` (git-ignored). Hash manifests of `runs/review-t02/` (4,885 lines) and `runs/review-t02-pass2/` (664 lines) were identical before and after this repair. Key files:
    - `review.md` (`b2e9337f…53694b47`);
    - `decoder_probes.py` (`d8e569b3…1286e97a`) and `decoder-results.json` (`86cb8049…5f581ce4`).
  - **Codex's disposition:**
    - The split-decoding repair is **verified**: 4/4 regressions, the original `json5000_runtime` case, valid splits decoded unchanged, and the digit limit unchanged.
    - The other JSON boundaries are safe: snapshot, project-manifest fallback, execution and runtime.
    - **Two P2s remained, both pre-existing sibling defects:**
      - **A. Provenance:** `_read_events` let a 5,000-digit integer, malformed JSON, invalid UTF-8 and excessive nesting escape from hash-matching `provenance.jsonl`. Every probe left no outcome, report or check files. The hash-mismatch control already gave fit ERRORs while keeping the temporal FAIL and VIOLATION_FOUND.
      - **B. Index:** `_load_index` missed `RecursionError`, so a deeply nested `index.json` escaped before outputs were cleared and left the previous outcome in place.
    - **P3:** guide line 92 still called the four original repairs unverified.
  - **Checkpoints:** base `bb9bac8`; head = the local commit "Repair T-02 provenance and index decoding after Codex verification" (parent `bb9bac8`).
  - **Repairs:**
    - **Provenance:** `_read_events` decodes the whole stream inside one guarded step and returns `(events, problem)`. On `ValueError`/`RecursionError` it returns no events, so a decoded prefix is never used, and the problem is "provenance.jsonl could not be decoded (…)". `prov_ok` becomes false, so only the provenance-dependent fit assertions take ERROR(`evidence_invalid`). Split, table, metric and temporal findings keep their status, and the problem is added to the outcome's reason. The split and provenance messages share `_decode_problem`.
    - **Index:** `_load_index` also handles `RecursionError`, which routes to the existing index-unavailable path. That path clears stale outputs, writes a fresh INCONCLUSIVE outcome and report with no invented assertion set, and does not rebuild the index.
    - Only `ValueError` and `RecursionError` are caught, at the two decoding calls; nothing broader. No policy, fixture, numeric limit or existing assertion changed.
  - **Tests** (`tests/integration/test_t02_scenarios.py`, full evaluator):
    - **`test_undecodable_provenance_is_wholly_invalid_and_independent_fail_stands[integer_5000_digits|malformed_json|invalid_utf8|deep_nesting]`:**
      - The setup is the partial-label run, where separate split/table evidence shows a late training prediction, so the control is VIOLATION_FOUND. The test appends one undecodable line *after* the valid events and re-hashes.
      - It asserts that both fit assertions are ERROR(`evidence_invalid`), which proves the decoded prefix is not used, and that the temporal FAIL stands with valid evidence.
      - Every other assertion matches the control, the outcome is VIOLATION_FOUND, the reason names `provenance.jsonl`, and the indexed outputs equal the files on disk with current hashes.
    - **`test_index_recursion_uses_the_index_unavailable_recovery_path`:** after a VIOLATION_FOUND control, `index.json` becomes 100,000-deep nesting. The test asserts a fresh INCONCLUSIVE outcome with no assertions and a reason naming the index, a fresh report, stale check files removed, and the index left unrebuilt (the existing recovery contract).
    - **RED at `bb9bac8`**, from a temporary `git archive` copy placed first on `PYTHONPATH`: **5 failed** (`runs/t02r3/red-at-base.log`), with `ValueError`, `JSONDecodeError`, `UnicodeDecodeError` and `RecursionError` ×2. All pass after the repair.
  - **Actual results (2026-10-15):**
    - Evidence-error and recovery suites: `uv run --locked pytest tests/integration/test_t01_scenarios.py tests/integration/test_review_t01.py tests/integration/test_review_t01_repair.py tests/integration/test_t02_scenarios.py tests/integration/test_cli.py tests/unit/test_policy.py --basetemp=runs/t02r3/c` → **113 passed** (`runs/t02r3/audit-tests.log`).
    - An unchanged copy of Codex's `decoder_probes.py` (`runs/t02r3/probes/`, `initial` and `siblings`; `summary.txt`):
      - all four provenance payloads → fit ERROR, temporal FAIL, VIOLATION_FOUND, current output hashes;
      - all four index payloads, including deep nesting → a fresh INCONCLUSIVE, with no stale outcome;
      - snapshot, fallback, execution and runtime cases are unchanged and safe;
      - the original `json5000_runtime` case is still INCONCLUSIVE with all assertions ERROR.
    - `ruff check .` and `ruff format --check .` → clean.
    - **Not run:** the full suite, Docker and mutation. Only the two loaders in `audit.py` changed, and valid inputs decode exactly as before. 0 inference calls.
  - **Newly demonstrated, NOT repaired (outside this pass's decoding scope; lead decision needed):** `runs/t02r3/shape_probe.py` (`shape-results.json`) shows that hash-matching evidence which decodes but has the wrong JSON shape still escapes.
    - An `index.json` that decodes to a list raises `AttributeError` in `_load_index` (`.get` on a list), and the previous outcome is left in place.
    - A `provenance.jsonl` line that decodes to a number raises `TypeError` in the fit check, and no outcome is written.
    - A `splits.json` that decodes to an object is handled (INCONCLUSIVE, no crash).
    - The smallest likely fix is a type check at each loader (index a dict; each provenance event a dict), routed through the same invalid-evidence or recovery paths.
  - **Remaining limitations:** the repair pass 1 limitations stand. **T-02 remains unaccepted** pending independent verification of this repair. The wrong-shape defects were repaired in repair pass 4 (below).
- **REPAIR PASS 4 (Claude Code, Opus 5.5 high; follow-up to `5af1b6e` before independent verification): wrong-shape evidence.**
  - **Evidence:** `runs/t02r3/shape_probe.py` and `shape-results.json`. An `index.json` that decodes to a list raised `AttributeError` in `_load_index` and left a stale outcome. A provenance line that decodes to a number raised `TypeError` in `fit_provenance`, and no outcome was written.
  - **Checkpoints:** base `5af1b6e`; head = the local commit "Repair T-02 wrong-shape provenance and index evidence" (parent `5af1b6e`).
  - **Cause:** both loaders checked decoding but not structure. `audit` and `fit_provenance` then indexed fields directly (`index["artifacts"]`, `index.get("table")`, `e["type"]`, `use["effective_deps"]`, …), so a wrong JSON type raised an error or, worse, was silently misread. For example, a string `effective_deps` became a set of characters, and a string `version` or `classifier` was used as recorded.
  - **Consumed fields (from reading the consumers and the writers):**
    - **index:** a JSON object; `artifacts` mapping names to sha256 strings (these become `EvidenceRef.sha256`); an optional `table` object with an optional string `sha256`. `outputs` is regenerated, so it is not checked.
    - **provenance:** every event is an object with a string `type`. Per type, as written by `recorder.py` and `adapter.py`:
      - **load:** `token`.
      - **take:** `token`, `input_token`, `input_status`.
      - **fit:** `instance`, `version` (int), `fold`, `class`, `classifier`, `supported`, `labels_supplied`, `labels_used` (bool), `input_token`, `input_status`, `labels_token`, `rows`/`deps` (string lists or null).
      - **use:** `instance`, `version` (int or null), `state_fit_fold`, `class`, `method`, `fold`, `input_token`, `input_status`, `input_known`, `output_token`, `rows`/`effective_deps`.
      - **split:** `fold`, `train_sha256`, `eval_sha256`.
      - **predictions:** `fold`, `pred_token`, `pred_status`, `rows`, `artifact`, `artifact_sha256`.
    - Fields read with `.get` are optional. Fields the consumers never read (`n_rows`, `object`, `role`, `kind`, gap details) are not checked, and extra fields are allowed. Event types the evaluator ignores, such as `gap`, need only a string `type`.
  - **Repair:**
    - `contracts.py` adds `RunIndex` and per-type provenance event models, next to the existing `ExecutionRecord`/`RuntimeRecord`. They are pydantic models with `strict=True` and `extra="allow"`; recorded values are validated, never coerced or rewritten. No existing event schema existed to reuse.
    - `_load_index` validates the decoded index with `RunIndex`. A `ValidationError` takes the existing index-unavailable path: stale outputs are cleared, a fresh INCONCLUSIVE outcome is written, no assertion set is invented, and the index is not rebuilt. This replaces the earlier `isinstance(index.get("artifacts"), dict)` check, which itself raised on a list.
    - `_read_events` validates every decoded event with `validate_provenance_event`. The first invalid event makes the whole artifact invalid ("provenance.jsonl event N has an invalid structure (…)"): no prefix is kept and nothing is skipped. Then `prov_ok` is false, the fit assertions are ERROR(`evidence_invalid`), and independent findings stand.
    - Only `ValidationError`/`ValueError` from these validation calls is caught. `fit_provenance.py` (a mutation-check target) is unchanged, and policy, fixtures and existing assertions are unchanged.
  - **Tests** (`tests/integration/test_t02_scenarios.py`, full evaluator, on the partial-label control with its independent temporal FAIL):
    - **`test_wrong_shape_provenance_event_invalidates_the_whole_artifact`, 11 cases:**
      - JSON-type cases: number (demonstrated), list, string, no `type`, non-string `type`;
      - consumed fields with the wrong type, copied from real recorded events: `use.effective_deps` as a string, `use.rows` as a number, `fit.version` as a string, `fit.classifier` as a string, `split` missing `train_sha256`, `predictions.pred_token` as a list.

      Each appends the bad event after the valid prefix and asserts: fit ERROR(`evidence_invalid`), so the prefix is rejected; the temporal FAIL stands with valid evidence; every other assertion is unchanged; VIOLATION_FOUND; the reason names the event; and current output hashes.
    - **`test_wrong_shape_index_uses_the_index_unavailable_recovery_path`, 5 cases:** list (demonstrated), `artifacts` as a list, an artifact hash as a number, `table` as a list, `table.sha256` as a number. Each asserts a fresh INCONCLUSIVE outcome with no assertions, a fresh report, stale check files removed, and the index not rebuilt.
    - **`test_recorded_provenance_from_real_runs_passes_the_structure_check`:** every event from executed s11b, s12a, s01, s03b and s05a validates. This guards against requirements stricter than real evidence.
    - **RED at `5af1b6e`**, from a temporary `git archive` copy placed first on `PYTHONPATH`: **15 failed, 1 passed** (`runs/t02r4/red-at-base.log`). The pass, `artifacts_a_list`, was already handled. Failures were `TypeError`, `KeyError` and `AttributeError` crashes, and assertion failures where wrong types were silently accepted.
  - **Actual results (2026-10-15):**
    - The decoding, shape and recovery suites (T-01 scenarios, both T-01 review suites, T-02 scenarios, CLI, policy and manifest schema) → **206 passed** (`runs/t02r4/audit-tests.log`).
    - A copy of `shape_probe.py` in `runs/t02r4/`:
      - `index_is_a_list` → INCONCLUSIVE (recovery path);
      - `provenance_line_is_a_number` → VIOLATION_FOUND, with the reason naming event 1;
      - `splits_is_an_object` → INCONCLUSIVE (unchanged).
    - A copy of Codex's `decoder_probes.py` in `runs/t02r4/probes/` gives results identical to repair pass 3.
    - `ruff check .` and `ruff format --check .` → clean.
    - **Not run:** the full suite, Docker and mutation. The changes are confined to `audit`'s two loaders and new models in `contracts.py`, and `fit_provenance.py`, the recorder and the runner are unchanged. 0 inference calls.
  - **Evidence-handling correction:** while verifying, I mistakenly reran `runs/t02r3/shape_probe.py` in place. It overwrote `shape-results.json` and its `shape/` run copies.
    - They were restored by rerunning the probe against a `git archive` copy of `5af1b6e`, which reproduced the two crash cases byte-identically. The `splits_is_an_object` case and `shape-results.json` were then regenerated with the original logic and recorded values.
    - A comparison with the pre-repair hash manifest shows every file's hash, size and path identical. Only modification times differ.
    - All later reruns used `runs/t02r4/`. `runs/review-t02/` and `runs/review-t02-pass2/` were never written.
  - **Remaining limitations:**
    - `splits.json` structure is still checked only by decoding. A JSON object instead of a list gives INCONCLUSIVE safely, as the shape probe shows, but other wrong field types in split entries were not probed in this pass.
    - The repair pass 1 limitations stand. **T-02 remains unaccepted** pending independent verification of repair passes 3 and 4.
- **CODEX VERIFICATION OF REPAIR PASSES 3–4 (local Codex, at `3bc38ff`, 2026-10-15) and REPAIR PASS 5 (Claude Code, Opus 5.5 high):**
  - **Review evidence:** preserved at `runs/verify-t02/3bc/` (git-ignored). Key files:
    - `review.md` (`e038f57b…caf72abb`);
    - `consumer_shapes.py` (`dc646eda…6802f1cb`) and `consumer-results.json` (`e2fb611d…1f4bf182`).

    Pre-repair hash manifests of `runs/review-t02/`, `runs/review-t02-pass2/`, `runs/verify-t02/`, `runs/t02r3/` and `runs/t02r4/` were saved **before any change** in `runs/t02r5/preservation/`, with `captured-at.txt` recording the capture time, and compared after the repair.
  - **Codex's disposition:**
    - Repair pass 3's decoding fixes are **verified**: whole-stream provenance decoding with no prefix, and index `ValueError`/`RecursionError` recovery.
    - Pass 4 fixes the demonstrated index and provenance shape cases. `RunIndex` matches its consumers, the per-type models match ordinary recorder types, and the guards are narrow.
    - **Two P2s remained:**
      - **(1) Split structure:** ten hash-matching malformed-entry cases crashed the evaluator and left no `outcome.json`:
        - `fold` as a list, or missing;
        - `train_ids` null, missing or a string;
        - `eval_ids` a scalar, or nested lists;
        - `kind` as a list;
        - a null entry;
        - a non-empty object at the top level.
      - **(2) Fit `input_status`:** it was optional in `_FitEvent`, but `fit_provenance._walk` reads `fit['input_status']` directly when `deps` is null. Its absence raised `KeyError`, no outcome was written, and the independent temporal FAIL went unreported. An explicit null was accepted correctly.
    - TASKS.md's pass-4 field inventory, which listed fit `input_status` among fields read with `.get` and therefore optional, is corrected by this pass.
  - **Restoration finding (Codex's exact distinction):** the `runs/t02r3` shape evidence is "overwritten and reconstructed, with content matching the retained pre-repair manifest. These are builder-produced records. This independent content comparison does not independently establish when the purported pre-repair snapshot was captured and does not erase the overwrite incident." No further restoration investigation was done.
  - **Checkpoints:** base `3bc38ff`; head = the local commit "Repair T-02 split structure and fit input_status presence" (parent `3bc38ff`).
  - **Requirements, derived from producers and consumers:**
    - **Splits:** `adapter.declare_split` writes `fold`, `kind`, `train_ids`, `eval_ids` and `training_cutoff`, and refuses unknown or repeated IDs within a list (SPEC §4.1). The consumers (`audit`, `split_integrity`, `fit_provenance`, `metric_ids`, `temporal`, `independent_metrics`) read `s["fold"]`, `s["train_ids"]` and `s["eval_ids"]` directly, and `kind` and `training_cutoff` through `.get`.
      - `SplitDeclaration` therefore requires a string `fold`, and `train_ids`/`eval_ids` as lists of strings with no repeats within a list. Empty lists stay valid.
      - `kind` is optional and must be a string when present; the consumers' missing-kind default is never written back.
      - `training_cutoff` is deliberately unchecked: the cutoff assertions keep judging it per fold.
      - Extra fields are allowed. The top level is a list (`SPLITS`, a pydantic `TypeAdapter`).
      - Row IDs must exist in the evaluator's table (checked when the table is valid).
    - **Provenance:** the recorder always writes fit `input_status` (a string). It is now required and nullable, since the schema has always accepted null and the explicit-null control stays valid.
  - **Repair:**
    - `_load_splits` validates the decoded artifact with `SPLITS`. `_compute` now reads the table first and refuses split rows absent from it.
    - Any problem gives "splits.json has an invalid structure (entry.field: message)" or "… names N row(s) absent from the table". The splits are not used at all: no entry is dropped or assessed alone. `splits_ok` is false, so the existing invalid-evidence path applies: every split-dependent assertion is ERROR(`evidence_invalid`), the run is INCONCLUSIVE, descriptive results are unavailable, and outputs and index are fresh.
    - `_FitEvent.input_status` is now required. Only `ValidationError` from these validation calls is caught. Policy, fixtures and `fit_provenance.py` are unchanged.
  - **Bounded schema/consumer check, for these two structures only:** every field read directly by subscript, including inside f-strings, was listed in `audit.py`, `fit_provenance.py` and the split consumers, and compared with its schema for required presence, type and nullability.
    - Accesses that follow a `.get` truthiness or membership check (`e["token"]`, `e["output_token"]`, `event["labels_token"]`, `pred["artifact"]`) are guarded by that check.
    - The only mismatch was fit `input_status`.
    - This is not a complete validation of every possible content; other artifacts (execution, runtime, snapshot) were outside this pass.
  - **Tests** (`tests/integration/test_t02_scenarios.py`, full evaluator, on the partial-label control with its independent temporal FAIL):
    - **`test_structurally_invalid_splits_are_wholly_invalid_evidence`, 16 cases:** Codex's ten; `kind` null and an `eval_ids` number; unknown and repeated rows in `train_ids` and `eval_ids` (producer guarantees). Each asserts that every assertion is ERROR(`evidence_invalid`), the outcome is INCONCLUSIVE (an evidence error, not a violation), the reason names `splits.json`, descriptive results are unavailable, and outputs and hashes are current.
    - **Valid controls:**
      - `test_valid_split_variants_are_still_assessed[kind_missing|extra_field|empty_evaluation_partition]`;
      - `test_invalid_cutoff_keeps_its_per_fold_handling` (an object cutoff: only the two cutoff checks are ERROR);
      - `test_fit_event_null_input_status_stays_valid_unknown_ancestry`.
    - **`test_fit_event_missing_input_status_is_invalid_provenance`:** Codex's exact case (`deps` null, `input_status` missing). Fit ERROR(`evidence_invalid`); the independent temporal FAIL stands; every other assertion is unchanged; VIOLATION_FOUND.
    - **RED at `3bc38ff`**, from a temporary `git archive` copy placed first on `PYTHONPATH`: **17 failed** (all invalid cases), and the 5 valid controls passed as designed (`runs/t02r5/red-at-base.log`). The failures were `KeyError`/`TypeError` crashes and silent acceptance of a null `kind` and of repeated rows.
  - **Actual results (2026-10-15):**
    - The decoding, shape and recovery suites (T-01 scenarios, both T-01 review suites, T-02 scenarios, CLI, policy and manifest schema) → **228 passed** (`runs/t02r5/audit-tests.log`).
    - A copy of Codex's `consumer_shapes.py` (`runs/t02r5/`; only `SOURCE` repointed read-only at Codex's `valid_control`; `consumer_shapes-adaptation.diff`):
      - all ten split cases → INCONCLUSIVE with current outputs;
      - missing `input_status` → VIOLATION_FOUND, with provenance invalid;
      - every control is unchanged (missing kind → VIOLATION_FOUND; object cutoff → INCONCLUSIVE; null `input_status` and optional/extra fields valid; index cases as before).
    - `runs/t02r5/referential_probe.py` (report-only, at `3bc38ff`) shows unknown split rows crashing with `KeyError` and no outcome, while repeated rows were silently accepted. Both are now covered.
    - `ruff check .` and `ruff format --check .` → clean.
    - **Not run:** the full suite, Docker and mutation. The changes are confined to `audit`'s split loading and new or tightened models in `contracts.py`, which the runner and candidate code do not use. 0 inference calls.
  - **Remaining limitations:**
    - Structural checks cover the fields the evaluator reads in `splits.json`, `provenance.jsonl` and `index.json`, not every possible content.
    - Duplicate fold names across entries remain accepted and are handled downstream, as before.
    - The repair pass 1 limitations stand. **T-02 remains unaccepted** pending independent verification of repair passes 4 and 5.

- **CODEX VERIFICATION OF REPAIR PASS 5 (local Codex, at `75a98f4`, 2026-10-15):**
  - **Review evidence:** `runs/t02-verification-final/` (git-ignored): `review.md` (`3d9149bb…9d7ebdc3`) and `tests-elevated.log` (`11713e0f…321d3fd5`).
  - **Disposition:** both prior P2 blockers are **verified fixed**, and no remaining implementation blocker or new regression was demonstrated in the requested boundaries.
    - **Split boundary:** the consumed-field inventory is complete, and the no-repeat and row-existence rules are justified by SPEC §4.1. Cross-partition overlap stays an assessable FAIL, an empty training partition is accepted, an invalid final entry invalidates the whole artifact, and an invalid cutoff in another fold keeps the earlier FAIL.
    - **Provenance:** fit `input_status` is required and nullable. Every subscripted event field matches its schema, and guarded accesses are safe.
    - **Unchanged:** decoding and recovery.
    - Codex judged T-02's acceptance criteria met within its documented trusted-fixture scope, together with the earlier verification records.
  - **Results (as reported by Codex):**
    - `uv run --locked pytest tests/integration/test_t02_scenarios.py -k "structurally_invalid or valid_split_variants or invalid_cutoff_keeps or input_status or undecodable or wrong_shape or recorded_provenance"` → **51 passed, 24 deselected** (145.09 s).
    - The copied probes `consumer_shapes.py`, `referential_probe.py`, the new `compatibility_probe.py` and `check_results.py` all exited 0.
    - This was a focused run. **The full suite was not rerun at `75a98f4`**; the last full unit + integration run was 534 passed, 1 skipped, at repair pass 1. No Docker or mutation rerun.
  - **P3 (documentation):** STATUS.md still called repair pass 3 unverified. Corrected in the acceptance commit.
- **ACCEPTANCE (2026-10-15):** the lead accepted T-02 at `75a98f4` within its documented scope. The decision rests on `runs/t02-verification-final/review.md` and the earlier independent verification records: review 1 at `487664e` (`runs/review-t02/r487/`), and the verifications at `0cf955d` (`r0cf/`), `bb9bac8` (`runs/review-t02-pass2/bb9/`) and `3bc38ff` (`runs/verify-t02/3bc/`).
  - **Accepted scope:**
    - The policy-v1.3 assertions `split.no_window_overlap` (routes D and C), `split.temporal_separation`, the three `temporal.*` checks and `metric.reported_matches_recomputed`.
    - Descriptive recomputation, the most-frequent baseline and class support.
    - Manifest schema 0.3 intake.
    - Evidence decoding, and the structural checks of the fields the evaluator reads in `splits.json`, `provenance.jsonl` and `index.json`.
    - All of this on trusted synthetic fixtures (`benchmarks/t01/`, `benchmarks/t02/`), under the declared clock, cutoff and containment semantics, the supported provenance path and the metric contracts (DECISIONS.md "T-02 contract dispositions"; `docs/specs/t02-contract.md`).
  - **Not covered by this acceptance (documented limitations):**
    - Window and separation checks verify declared rules; they are not proof of statistical independence.
    - Cutoffs and fold membership are declared by the evaluated code and not verified independently.
    - Route C relies on a documented, unverified containment declaration; UCI HAR evidence needs T-09.
    - Times are compared as float64, so integers beyond 2^53 lose precision. There is no date parsing or unit conversion.
    - `final_holdout` reported metrics are NOT_ASSESSED: no evaluator-only label store exists.
    - Splitter minimum requirements are unavailable, and the linear baseline is deferred.
    - Pairwise window and separation comparison is untested at large scale.
    - Manifest numbers longer than the JSON parser accepts are rejected with a position-only diagnostic.
    - The adapter accepts duplicate fold names; only the metric checks refuse them.
    - Structural validation covers the fields the evaluator reads, not every possible content. Candidate-produced provenance is not independently trustworthy.
    - Audits stay `trusted_pipeline_only`; candidate re-evaluation and Docker-runner integration are T-06.
    - The `runs/t02r3` shape evidence was overwritten and reconstructed (see repair pass 5).

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
- **RESULT (2026-10-15; research and local design only; NOT accepted):** `docs/HOSTING_PROBE.md`. Sonnet 5.5 medium. No deployment, account linking, repository creation, secret change or API call.
  - **Hosts, documented 2026-10-15:**
    - **Streamlit Community Cloud:**
      - free;
      - honors `uv.lock` first among dependency files;
      - has a Secrets field;
      - an app from a private repository is private by default, but its privacy is set independently and can be made public without making the repository public;
      - private repos need a deploy key, the `repo` OAuth scope and admin rights, with one private app at a time;
      - apps sleep after 12 hours without traffic;
      - resource figures are dated Feb 2024.
    - **Hugging Face Spaces:**
      - creating a Docker or Gradio Space needs PRO ($9/month);
      - "protected" visibility keeps source private with a public app;
      - free CPU Basic sleeps;
      - the container runs as user 1000, and secrets are environment variables.
  - **Recommendation (proposed):** Streamlit Community Cloud for a limited hosted demo; fallback HF protected Docker Space; last resort recorded examples plus the local build.
  - **Execution:**
    - limited hosted stays the default;
    - running candidates in the Community Cloud app is unsupported by that host (documented absence, untested);
    - an HF Docker Space launching sibling containers is not demonstrated;
    - a separate Linux worker running the T-05 runner is not demonstrated, its cost is unknown, and T-05 was accepted only on this Windows/Docker Desktop host.
    - None of these is "infeasible"; none was shown.
  - **Costs:**
    - price $0.30 / $0.90 per 1M tokens, observed 2026-10-14;
    - observed smoke cost about $0.00005 per call;
    - estimated normal run about $0.021;
    - proposed worst case $0.051 per run at 59,000 in / 37,000 out tokens over 6 calls;
    - up to about $0.102 if retries were extra requests, which is why the retry rule needs fixing in DECISIONS.md.

    Calculation: `hosting_probe/cost_calc.py`. The smoke script's 1,024-token cap is not a production cap.
  - **Credits:**
    - Nebius Builder terms (documented): promotional credits "expire 90 days from the date of issuance", must not be used for production workloads, and the account may be auto-paused if monthly use exceeds the allocation by more than 30%.
    - Whether the user's credits fall under these terms, their issue dates, balance and expiry are unknown. If issued on 2026-10-14, 90 days ends about 2027-01-12 (illustration only).
    - A negative balance leads to an automatic card charge (documented). The lead recorded that payment information is already on the account and billing settings stay unchanged, so the credit balance is not a hard ceiling and in-application caps are the control.
  - **Judge access (proposed):**
    - live, recorded-example and unavailable modes;
    - budgets reserved atomically before each call and settled afterwards, with leases;
    - separate judge and public pools;
    - a private judge access code checked server-side (a hidden URL is not access control);
    - all counters in one external durable store with atomic updates, failing closed to recorded mode.

    The store is not chosen, and Community Cloud memory is cleared on restart.
  - **Probe stub (local only):** `hosting_probe/` (`app.py`, `requirements.txt`, `test_stub.py`, `cost_calc.py`). It runs no ATLAS code. Three checks are kept apart: build/import, secret canary, optional `GET /models`. 4 local AppTest tests passed in the locked environment, with the Nebius call mocked. The stub's `requirements.txt` installs Streamlit only, so a host deployment would not verify the full locked environment.
  - **Missing, so T-03 stays unaccepted:**
    - no deployed build, cold start or outbound-network observation;
    - secret store untested on a host;
    - credit balance and expiry unknown;
    - zero-balance behavior unknown;
    - durable store not chosen;
    - availability through 15 December not established.
  - **Approval needed (stage A):** a new, separate public repository with the two stage A files, a Streamlit sign-in via GitHub, a deployment and a harmless `CANARY` secret entered by the owner. No spending, no API call. Stage B (one free `GET /models`) and stage C (full locked build) need separate approvals.
  - **Lead decisions, 2026-10-15 (DECISIONS.md "Hosting probe decisions"):**
    - the six-call limit counts every attempted request, retries included;
    - a dispatched request's reservation is not released by lease expiry, and unknown usage stays conservatively reserved until reconciled;
    - billing is unchanged (payment information already present);
    - the deployed probe is kept until initial and sleep/wake observations are recorded, and deletion is a later explicit action.
  - **Stage A publication set prepared locally (2026-10-15; nothing created or published):** `hosting_probe/stage_a/app.py` (1,362 bytes) and `requirements.txt` (10 bytes, `streamlit`).
    - `hosting_probe/check_publication.py` confirms the set is exactly those two files with no ATLAS source, personal documentation, credential, key-shaped string, email, local path, Nebius reference or network import.
    - `hosting_probe/test_stage_a.py` renders the app with every non-loopback connection and lookup blocked (the guard has a self-test) and checks that only a hash prefix of the canary is shown. The first stub (with the optional Nebius check) is not published in stage A.
    - 9 local probe tests passed. T-03 stays unaccepted.
  - **Stage A deployed by the owner (2026-10-15 18:41 -0400) and first observations recorded** (`docs/HOSTING_PROBE.md` §7a): public repository `lainx06/atlas-hosting-probe` with the two files (byte-identical to the local set), `https://atlas-hosting-probe.streamlit.app/`.
    - Build about 14 s; no extra permission; Python 3.11.17 and Streamlit 1.66.0 on Linux.
    - The canary was present and its hash prefix matched.
    - Still pending: the sleep/wake observation (earliest about 2026-10-16 06:54 -0400 with no visits in between, after the owner's signed-out check at about 18:44 -0400 showed the page loads), outbound network, the full locked build, and the credit facts.
    - **T-03 remains unaccepted.**
  - **Credit screenshot (owner-reported, 2026-10-15):** account balance $50.00; a separate $1.00 trial credit with 29 days remaining (ends about 2026-11-13); Token Factory usage under $0.01; no expiry shown for the $50, which stays **unknown**. Billing settings and spending authorization unchanged.
  - **Durable budget store (research only; selected provisionally by the lead 2026-10-15, pending a connection test):** **Neon serverless Postgres, Free plan** (no card required, documented; 100 CU-hours a month = compute size 0.25–2 CU × active time, with the compute suspending 5 minutes after the last query) (1 GB, 100 compute-unit-hours a month, compute suspends after 5 minutes and resumes in a few hundred milliseconds, no inactivity deletion documented, atomic conditional `UPDATE`). Supabase rejected (pauses after 7 days of low activity); Upstash rejected (no persistence on the free plan). Open: outbound port 5432 from Community Cloud is unknown, and account terms and card requirement were not established, so a separately approved stage D canary is proposed. `docs/HOSTING_PROBE.md` §5a.
  - **Stage D probe prepared locally (2026-10-15):** `hosting_probe/stage_d/` (`app.py`, `budget_probe.py`, `requirements.txt`), a later update to the existing Streamlit probe (not a second app). It uses synthetic integer units and scratch tables, with no provider key or request. Operations: reserve all cap rows plus the reservation record in one transaction (sorted lock order, unique request ID, full rollback on refusal), dispatched-before-send, idempotent settle, release only if never dispatched. Scenarios: two concurrent requests for a budget admitting one; a refused multi-cap reservation leaving no partial change; opposite cap orders; duplicate IDs; uncertain dispatched cost retained across a new connection (§5b).
  - **Neon project (owner-reported, 2026-10-15):** `atlas-budget-probe`, Free plan, AWS US East 2 (Ohio), **PostgreSQL 18**, Postgres only; agent/CLI setup skipped; no connection string shared; project kept. The five scenarios have been run only on **local PostgreSQL 17.11**; **verification on Neon 18 is pending**.
  - **Access gate (2026-10-15):** the deployed probe is public, so a signed-out visitor could have pressed the stage D button. `hosting_probe/stage_d/app.py` now runs the database tests only when `DATABASE_URL` and `PROBE_ACCESS_CODE` secrets exist and the visitor has typed the matching code (constant-time comparison); without a configured code the section is disabled. Tests with a stand-in driver that counts connection attempts show **zero attempts** with no code configured, nothing typed, a wrong code, a near-miss and no database URL, no button present, and no URL or code in the output; a correct code enables the button and a failure shows only the error type. Against a deliberately ungated copy of the page, those tests fail (5 failed). The first-connection measurement is described as a combined connection/startup time, not a region comparison. 18 passed, 1 skipped offline; no database test was run. The deployed Streamlit probe is untouched.
  - **Retention rule (lead, 2026-10-15):** unresolved dispatched reservations stay accounted for. Pruning old records never releases reserved funds or resets cumulative spending; only settled or released rows, whose effect is already in the cap totals, may be deleted, and a dispatched reservation is never pruned before reconciliation (`docs/HOSTING_PROBE.md` §5a).
  - **Local PostgreSQL results (2026-10-15; approved by the lead):** the five scenarios passed in 3 of 3 runs against a disposable `postgres:17-alpine` container (digest `sha256:b0f9560a…552b24`, PostgreSQL 17.11, psycopg 3.3.6 in a disposable `uv run --isolated` environment). Loopback-only port, throwaway credentials, no mounts, bounded timeouts. Three deliberately defective `reserve` variants (check-then-write, no single transaction, unsorted lock order) were each caught by their scenario, with 20 `deadlock detected` errors in the server log from the last. No defect was found in the shipped operations; one test defect was fixed. `pyproject.toml` and `uv.lock` unchanged; container and image removed. **These are local PostgreSQL results, not evidence of Neon connectivity, Neon durability or hosted concurrency.** No account created, nothing deployed or published, no inference call; the sleeping stage A probe was not touched. T-03 remains unaccepted. Details: `docs/HOSTING_PROBE.md` §5b.
  - **Sleep/wake observed once (2026-10-16; owner-reported):** visit at 12:01 -0400 in a fresh signed-out incognito window, 17 h 17 min after the previous visit (2026-10-15 18:44 -0400). The page showed a wake-up button; waking took about 23–24 s, and `process_uptime_s` was 0.1 (a fresh process). Recorded as **one observed successful public sleep/wake cycle**, not guaranteed future availability or full ATLAS deployment feasibility (`docs/HOSTING_PROBE.md` §7a).
  - **Stage D run once on the host (2026-10-16 about 13:15 -0400; user-observed on Neon PostgreSQL 18):**
    - The repository update holds exactly the three stage D files, byte-identical to `hosting_probe/stage_d/` (builder's read-only download from GitHub; commit 2026-10-16 16:57 UTC, after the sleep/wake visit).
    - The owner entered `DATABASE_URL`, `PROBE_ACCESS_CODE` and kept `CANARY`. A wrong code showed "Not authorized." with no button; the correct code enabled it.
    - All results `ok: true`: first connection 1.04 s (combined lookup/TLS/login/compute start); race 20 rounds, one admitted and 60 units held each round; multi-cap refusal left caps unchanged and no reservation row; opposite lock orders 20 rounds, no failures; duplicate request ID reserved and settled once; uncertain dispatched reservation retained across a new connection, blocked another request, then settled. App-measured total 57.2 s.
    - **Not established:** production readiness, durability across a database restart, long-term availability, compute-hour use, outbound HTTPS to Nebius (stage B) and the full locked build (stage C). The PostgreSQL version comes from the project settings; the page does not show it. Scratch tables with synthetic rows remain in Neon.
    - Nothing was rerun or redeployed by the builder, nothing was deleted, and no Nebius call was made.
  - **Remaining gaps (assessed 2026-10-16; `docs/HOSTING_PROBE.md` §9):** every open check now has a dated source, an observation or an explicit "unknown". Still open:
    - the lead's decisions: limited vs. full hosted (criterion 2), confirming Neon, and whether one wake cycle plus the fallback is enough for availability through 15 December;
    - credit expiry stays **marked unknown**, which criterion 3 allows; whether a public demo is "production" under the Builder terms is also unknown;
    - two untested hosted paths, to be required or deferred by the lead: outbound HTTPS to Nebius (stage B) and the hosted dependency build (stage C).
  - **T-03 remains unaccepted.**
  - **Lead decisions (2026-10-16; DECISIONS.md "T-03 hosting decisions"):**
    - V1 is limited hosted mode plus full local Docker execution; full hosted is a stretch goal.
    - Neon is selected as the budget store; production integration still needs implementation and review.
    - The availability plan through 15 December is accepted, with recorded examples and the local build as fallbacks; no uptime guarantee.
    - The judge-access and budget design is accepted for planning scope only. In-app caps are planned controls, not an existing hard spending ceiling. Billing is unchanged and no additional spending is authorized.
    - The $50 credit expiry and promotional-use eligibility stay explicitly unknown; unknown eligibility is not approval.
    - Stages B (Nebius connectivity from the host) and C (full locked build on the host) are deferred to T-12 and are required there before the hosted app is declared ready.
  - **Mapping against the acceptance criteria (`docs/HOSTING_PROBE.md` §9; criteria unchanged):**
    - criterion 2 (recommendation with evidence): met, and the lead chose limited hosted;
    - criterion 3 (expiry confirmed or marked unknown): met, marked unknown;
    - criterion 1 (each open check answered with a dated source or an observed test): met for five of the six open checks. The isolated-worker check is answered for Community Cloud (documented absence) and the HF Space (documented constraints, not demonstrated), but **the cost and delivery time of a separate worker were not researched** and are recorded as unknown.
  - **Readiness (builder's assessment):** ready for the lead's acceptance decision within the research-and-feasibility scope, provided the lead judges that residue acceptable because full hosted is a stretch goal. The alternative is a short documentation-only price search first. **T-03 is not accepted.**
  - **Separate-worker check (2026-10-16; documentation only; `docs/HOSTING_PROBE.md` §3a):** one option, a DigitalOcean Droplet with the Docker 1-Click image (Ubuntu 22.04). Dated official sources were fetched 2026-10-16. No account, spending or API call.
    - **Smallest suitable plan (proposed, untested):** 2 GiB / 1 vCPU at $12.00/month ($0.01786/h), because the runner gives each container 1 GiB and 1 CPU. 4 GiB / 2 vCPU at $24.00/month is more comfortable.
    - **Billing:** per second, 60 s / $0.01 minimum; still billed while powered off. Bundled plans are capped at 672 h a month, but the docs do not say which plans are bundled (inferred from the price).
    - **Restrictions:** a payment method is required, and there is a team Droplet limit. The default limit for a new account and any verification are not stated.
    - **Estimate:** from 2026-10-19 at 24/7, about $24.00 (2 GiB) or $48.00 (4 GiB) through 15 December; from 2026-11-01, $18.43 or $36.86. Taxes, transfer overage and snapshots are excluded. This is not an authorization.
    - **Delivery:** provisioning time is unknown (not documented). Our implementation and verification is a rough estimate of about 5.5–13 working days, not demonstrated.
    - A VM with Docker does not establish isolation-contract compliance; that needs the T-05 suite on Linux plus a security review.
  - **Readiness after the worker check:** criterion 1 is now met at documentation level: cost answered by dated sources, contract compliance answered as "not demonstrated", and delivery split into an unknown provisioning time and a labelled estimate. Criteria 2 and 3 are met. Ready for the lead's acceptance decision. **T-03 is not accepted.**
- **ACCEPTANCE (2026-10-16):** **accepted by the lead at `51d3dd8` within its documented research-and-feasibility scope.**
  - **Covers:** the hosting recommendation; the observed probe results (stage A build and canary, one sleep/wake cycle, one stage D run on Neon PostgreSQL 18); the selected budget store (Neon); and the documented costs, risks and unknowns.
  - **Does not establish:** production readiness, guaranteed availability, promotional-credit eligibility, or isolation-contract compliance on any remote worker.
  - **Stays in force:**
    - Limited hosted mode remains the V1 mode.
    - The worker sizing and cost figures (`docs/HOSTING_PROBE.md` §3a) remain **provisional**, including the unconfirmed 672-hour billing cap.
    - No new spending, account creation or deployment is authorized.
  - **Carried forward, unchanged:**
    - T-12 must test Nebius connectivity from the host (stage B) and the full locked-environment build on the host (stage C) before the hosted app is declared ready.
    - T-12 must implement and review the production budget controls (accounting, caps, judge and public pools, leases, reconciliation, retention) on Neon. Until then the caps are planned controls, not a spending ceiling.
  - **Kept as they are:** the deployed probe app, its Secrets, the Neon project and its scratch tables. Deletion and credential rotation remain later explicit actions.

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
- **RESULT (2026-10-14; calls at 2026-10-15 UTC):** all four criteria demonstrated. **Accepted by the user within its documented smoke-test scope** (2026-10-14). Evidence is local and git-ignored, in `runs/nebius_smoke/`.
  - [x] `GET /models?verbose=true` (free) listed 25 models, four NVIDIA: `nvidia/nemotron-3-super-120b-a12b`, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3_5-Lightning`, `nvidia/Nemotron-3-Ultra-550b-a55b` (`models-verbose-20261014.json`).
  - [x] One capped JSON call succeeded, and its whole reply passed a strict Pydantic schema (`json-20261015T023413Z.json`). **Qualification:** the JSON was prompt-requested and **application-validated**. It was not provider-enforced structured output, because no NVIDIA model on Nebius advertises it (DECISIONS.md "Initial model and response approach"). A separate text connectivity call also succeeded (`call-20261015T023151Z.json`).
  - [x] Sanitized evidence saved: the model list and both call records. Each was checked to be free of the key before it was written.
  - [x] The key was never echoed: it was checked only as booleans and hashes. Committed: no (`.env` is ignored and untracked); the staged files and full history were scanned for the key value before the T-04 commit.
  - Handoff done: model ID and response approach recorded in DECISIONS.md; `ATLAS_MODEL_PRIMARY` set in the local `.env`; STATUS.md updated.
  - **Outside T-04 (not done, by design):** `ATLAS_MODEL_MODE` stays `fixture` until the T-06 client exists. Diagnosis, tool use and repair quality are untested. The validation path has no unit test (it lives in the script; T-06 owns the production client and schemas).
- **RUN (as built):** `uv run --locked python scripts/nebius_smoke.py [--test text|json]` (dry run: free price re-check, no inference); `--execute` sends exactly one capped request.
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
- **CHANGE:** `src/atlas/runner/docker.py`, `Dockerfile.runner`, candidate validation and hash-bound approval (SPEC §9), `tests/integration/test_runner_contract.py`. (As built, see RESULT.)
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
- **RESULT (2026-10-14; self-tested, awaiting Codex review; NOT accepted):**
  - **Built (decisions A–C):**
    - Image `atlas-runner:t05`, ID `sha256:e13f91a3c9baa52e2314b91a0b17c2437033acd98cbb396a104b9c3545b5f625`, recipe `f67fd121afc1a2aa…`.
    - Base `python:3.11-slim@sha256:e88e9763…`, Python 3.11.17.
    - 11 hash-pinned wheels matching `uv.lock`. The Docker CLI is resolved as `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin\docker.exe` and recorded per run.
  - **Files:**
    - `src/atlas/runner/docker.py`: CLI resolution, probe, build, staging, lifecycle, bounded IO, frame and archive checks.
    - `src/atlas/runner/container_entry.py`: the in-container supervisor and child.
    - `src/atlas/candidates.py` (SPEC §9).
    - `src/atlas/tables.py`: the `read_table` logic moved out of `intake.py`, which now delegates to it, so the container needs no policy code.
    - `Dockerfile.runner`, `docker/runner-requirements.{in,txt}` and `scripts/runner_requirements.py`.
    - `tests/unit/test_candidates.py`, `test_runner_collection.py`, `test_runner_config.py` and `tests/integration/test_runner_contract.py`.
    - `audit.py` is **unchanged**.
  - **Requirements 1–6:**
    1. **Build context:** the build context is a temporary directory holding exactly `Dockerfile` and `runner-requirements.txt` (tested). Nothing from the repository is sent.
    2. **Dependency set:** derived from the AST imports of the mounted code (numpy, pandas, scikit-learn) plus the Parquet engine for `to_parquet` (pyarrow), resolved for Linux by uv against `uv.lock`. Transitive dependencies resolved: scipy, joblib, cloudpickle, threadpoolctl, narwhals, python-dateutil and six. pandas' `tzdata` is Windows-only. `pip check` runs in the build. The tests assert pins equal `uv.lock`, hashes are present, and openai, dotenv, streamlit and pydantic are absent.
    3. **Mounted code:** only `atlas/{__init__,adapter,recorder,reports,tables}.py` and the entry script, read-only. In the container, policy, audit, contracts, intake, checks and candidates are not importable (tested). The snapshot is built only from the manifest (re-serialized from the validated model), the declared table and the entry point; extra project files such as `.env` are never copied (tested).
    4. **Output collection:** outputs are collected before the container stops. The PID-1 supervisor (non-dumpable, so the candidate cannot reach its stdout) emits one frame: a header plus a tar of regular files under caps.
       - The host bounds stdout (≈32.8 MiB), stderr (1 MiB), archive size, expanded bytes (32 MiB), file count (256) and total time (exec + 30 s).
       - It rejects absolute, `..`, backslash, drive and reserved names, links, devices and directories, and duplicate or case-duplicate or file/dir-conflicting destinations, validating everything before writing.
       - The container is removed on every path (inspect, `rm --force`, confirm gone).
    5. **Probes:** probes are bounded (fork up to 200 and stop at the first refusal; allocate at most 32 × 64 MiB).
       - The cgroup limits are read back in a module fixture before the stress tests run, and the tests run sequentially.
       - Only containers labelled `atlas.runner=t05` and named by this task are listed or removed.
    6. **Approval and no fallback:**
       - Approval and hashes follow SPEC §9. The runner recomputes the snapshot and candidate hashes, then re-hashes the staged bytes before mounting.
       - No host fallback: the Docker module never imports the trusted runner (tested). A missing CLI, unreachable daemon, or missing or other-recipe image gives `not_executed`, with no container start and no host execution (spied and marker-checked).
  - **Acceptance:** `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py` → **28 passed** in 38.56 s (final code) (log: `runs/t05/acceptance.log`, run records under `runs/t05/acceptance-tmp/`, git-ignored). Observed:
    - [x] **No network:** only `lo`; TCP to 1.1.1.1:53 failed with errno 101; DNS raised `gaierror`.
    - [x] **No secrets:** the candidate environment is exactly the allowlist (plus 2 `KMP_*` variables scikit-learn sets at import). Host canaries, both secret-named and plain-named, were absent from the probe and the record. No `.env` files; `/proc/1/environ` gives EACCES.
    - [x] **Read-only root:** `/` is mounted `ro`, and every write to the root filesystem, code and snapshot fails with EROFS. Only `/tmp` and `/work/out` are writable (tmpfs, `noexec`). uid/gid 10001, all capability sets 0, NoNewPrivs 1, seccomp 2.
    - [x] **Limits trigger:**
      - Memory (max 1 GiB, swap max 0): the probe was OOM-killed (child −9, `oom_kill`=1) after 13 × 64 MiB.
      - PIDs (max 128): EAGAIN after 124 forks, `pids.max` event 1.
      - Execution timeout: 3 s configured, killed at ≈3.7 s elapsed.
      - Host deadline: 8 s configured, container killed and removed at 8.2 s.
      - Scratch and outputs: ENOSPC at exactly 64 MiB and ≈32 MiB.
      - Output file cap: 300 files → `collection_failed`.
    - [x] **Refusals:** path escapes, evaluator, label, manifest and table targets, changed candidate bytes, a changed or extra-file snapshot, and an approval for another snapshot are all refused before any Docker call.
    - [x] **Unavailable isolation → no execution:** CLI missing, daemon unreachable, image missing, image from another recipe.
    - **Behaves like the trusted runner:** an approved trivial change to s02 ran in the container, and its `provenance.jsonl` and `splits.json` are byte-identical to the trusted host runner's on the unmodified fixture. The four prediction frames are equal.
    - **Mutation sanity check (scratch only, repository untouched):** dropping `--network none` or `--pids-limit` made the network and PID probes observe a connection and 200 forks. Dropping `--read-only` turned root writes into EACCES, which the tightened write test now rejects.
  - **Other runs:**
    - The new offline unit tests: 96 passed, 1 skipped (symlink creation is not permitted for this Windows account; a directory-junction test covers reparse-point refusal).
    - The existing T-01 suite, run once: **165 passed**.
    - `ruff check`/`format --check`: clean.
    - The mutation check was not rerun: `intake.read_table` only delegates now, and no mutation target (fit_provenance, split_integrity, recorder) changed.
  - **Limitations:**
    - The runner does **not** re-evaluate candidates: no required-set scheduling, and `audit.py` does not accept Docker execution records yet (T-06).
    - Approval is programmatic (`approve()`); there is no user-facing approval step yet.
    - The recorder runs inside the candidate process, so container evidence is candidate-produced (SPEC §9.9).
    - The probe's `isolated_available` checks the CLI, daemon, Linux server and image recipe/user. It does not rerun the contract tests per run; their pass is tied to this commit and image.
    - Docker Desktop: the daemon is root inside its VM. Bind mounts reach the VM through a 9p share of `C:\` (the container sees only the two bound directories). CPU is limited (`cpu.max` read back) but not stress-tested.
    - `--ipc none` removes `/dev/shm`, so joblib runs serially (warning recorded).
    - PID 1 inherits the base image's public `GPG_KEY` variable; the candidate cannot see it.
    - The archive is held in memory (≤ ≈33 MiB).
    - Only tested on this Windows 11 Home / Docker Desktop host.
    - Building the image requires network access (approved). The base image's Debian packages are pinned only through the image digest.
- **REVIEW 1 (local Codex, of `f494c95`, 2026-10-15) and REPAIR PASS 1 (Claude Code, Opus 5.5 high):**
  - **Review evidence:** preserved unchanged at `runs/review-t05/session-f494c95-20261015/` (git-ignored). A hash manifest of all files there was identical before and after the repair (516 lines). The directory holds Codex's probes, their results and `verification-summary.json` (sha256 `c466d8a8…5689baa1`); it contains no separate narrative review text. Key files: `bounded_probes.py` (`7e677e7a…c6e735b7`), `bounded-results.json` (`d9cad12a…dcf1bef7`), `lifecycle_probes.py` (`e7e96337…d30d1f28`) and `lifecycle-results.json` (`347a7aa9…d2596178`). Codex's run: 28 contract tests and 96 unit tests passed, 1 skipped; 0 inference calls.
  - **Checkpoints:** repair base `f494c95`; head = the local commit "Repair T-05 after Codex review 1" (parent `f494c95`).
  - **Findings (three, P2), causes and repairs.** Each regression test below failed at `f494c95`: 25 failed, 82 passed, 1 skipped (log `runs/t05-repair1/red-at-base.log`). All pass after the repair.
    1. **Cleanup reported removal on Docker/API failure.**
       - *Cause:* `_remove_container` took any non-zero `docker container inspect` exit as "gone", so an unreachable daemon looked like a removed container. `run_candidate` also reported `completed` even when `container_removed` was false.
       - *Repair:* absence is now confirmed only by a successful `docker ps --all --filter name=…` listing that does not show the exact name. A failing CLI, timeout or unreachable daemon gives `cleanup: unknown`; a container still listed gives `still_present`; `removed` is true only for `confirmed_absent`. `docker rm --force` returns 0 even for a missing container (observed), so its exit code is recorded but never used as evidence.
       - *Recording:* every run that started (or tried to start) a container records `cleanup {status, errors}`, `container_removed` and `docker_state`, inside the `finally` that removes the container. When removal is unconfirmed, the final status becomes `cleanup_failed`, with the outcome it replaced kept in `execution_status`/`execution_reason`. This applies to every outcome, including `completed`, `not_executed` after a launch failure, and `runner_error`.
       - *Tests:* `tests/unit/test_runner_lifecycle.py`:
         - `test_daemon_failure_does_not_confirm_removal` (Codex's reproduction);
         - `test_cli_launch_failure_does_not_confirm_removal`;
         - `test_absence_is_confirmed_by_a_successful_listing`;
         - `test_container_still_listed_is_not_removed`;
         - `test_unconfirmed_cleanup_prevents_completion[daemon_unreachable|still_present]` (Codex's reproduction);
         - `test_unconfirmed_cleanup_after_launch_failure_is_explicit`;
         - `test_confirmed_cleanup_allows_completion`.
    2. **Snapshot limits applied after whole-file reads and AST parsing.**
       - *Cause:* `build_snapshot` called `intake.load_project`, which read and `ast.parse`d the whole entry point (and read the manifest) before any size check. `_permitted_file` used `Path.read_bytes()` and compared the length afterwards. Revalidation (`current_inventory`) enumerated the whole tree with `rglob` and hashed every file with whole-file reads.
       - *Repair:* `build_snapshot` decides supportedness itself, on bounded in-memory reads. The order is: read the manifest (new cap `MAX_MANIFEST_BYTES` = 64 KiB) → validate it → `intake.manifest_reason` → validate both paths with `safe_relpath` and check for collisions → read the entry point and table → AST adapter check (`intake.source_uses_adapter`). `intake.load_project` keeps its behavior; its checks were factored into those two helpers.
       - *Checked reads:* every read goes through `_open_permitted`. It lstat-checks each path component (no symlink/reparse point) and requires a regular file inside the root whose lstat size is within the cap. It opens the file, requires `fstat` to show the same device and inode, regular, and within the cap. It then reads at most cap + 1 bytes. OS errors become `SnapshotError`.
       - *Revalidation:* `current_inventory(root, limits)` takes a cap per expected path. It refuses at the first unexpected entry (enumeration stops early) and streams hashes through the same checked open with the same bound. `stage_project`, the staged-entry re-read and `validate_diff`'s base read use the bounded reader too. A staging-time `SnapshotError` is now a `refused`/`staged_invalid` record rather than an exception.
       - *Normalized parse failures:* AST failures in the snapshot (`RecursionError`, `MemoryError`, `ValueError`) are `SnapshotError`. In `validate_diff` they are `CandidateRejected` with `too_complex`, or `syntax_error` for `ValueError`. Before, `"x" + ".a" * 30000` escaped as `RecursionError`. This is the same class of defect, found while repairing finding 2.
       - *Tests:* in `tests/unit/test_candidates.py`:
         - `test_oversized_entry_is_refused_before_intake_parsing` (Codex's `entry_cap_after_AST`; no `ast.parse` call, ≤ cap + 1 bytes read);
         - `test_oversized_table_is_refused_with_a_bounded_read` (Codex's `snapshot_read_before_cap`);
         - `test_oversized_manifest_is_refused_with_a_bounded_read`;
         - `test_input_replaced_after_its_checks_is_refused`;
         - `test_deeply_nested_entry_point_is_refused_not_crashed`;
         - `test_too_deeply_nested_candidate_is_refused_not_crashed`.

         In `tests/unit/test_runner_lifecycle.py`: `test_revalidation_hashes_with_bounded_reads` and `test_revalidation_stops_at_the_first_unexpected_entry` (203 lstat calls before the repair; now ≤ 20).
    3. **Nested JSON and PAX input escaped as `RecursionError`, leaving the saved status null.**
       - *Cause:* `parse_frame` gave a 4 KB, 2000-deep header straight to `json.loads`. `tarfile` recurses once per consecutive extension header, so 600 chained PAX records (616 KB, under the 34 MB archive cap) overflowed the stack. Only `CollectionError`/`OSError` were caught, so the exception escaped `_run`, and `execution.json` was written with `status: null`.
       - *Header repair:* `parse_frame` checks bracket depth outside strings without recursion (`MAX_HEADER_DEPTH` = 8; the supervisor's header uses 3) before `json.loads`, and also maps `RecursionError` to `malformed_header`.
       - *Archive repair:* `extract_archive` first walks the raw tar headers (`_check_tar_structure`), one loop iteration per header. It verifies checksums and octal numbers (base-256 is refused). It allows at most one PAX `x` header per member (≤ 8 KiB, well-formed records, no `size` or `GNU.sparse` override) and refuses global PAX, Solaris and GNU long-name/link/sparse headers, a PAX header without a member, entries extending past the archive, and any non-zero data after the end marker. The member count is capped before `tarfile` runs. `TarError`/`RecursionError`/`ValueError` from `tarfile` still become `malformed_archive`. This accepts exactly the layout the supervisor writes (PAX format, a PAX header only for non-ASCII or long names).
       - *Final records:* any other exception during collection becomes `collection_failed` with problem `unexpected_error`, and partial outputs are removed. An exception anywhere else in `_run` is recorded as `runner_error` (or `cleanup_failed`) before it is re-raised. Cleanup always runs first, since it sits in the `finally` around the container's IO.
       - *Tests:* in `tests/unit/test_runner_collection.py`:
         - `test_deeply_nested_header_is_a_collection_error` and `test_consecutive_pax_headers_are_a_collection_error` (Codex's reproductions);
         - `test_unexpected_tar_structure_is_rejected[global_pax|gnu_longname|pax_size_override|pax_without_member|bad_pax_record|data_after_end]`;
         - `test_single_pax_header_for_a_non_ascii_name_is_accepted`.

         In `tests/unit/test_runner_lifecycle.py`:
         - `test_nested_header_is_a_recorded_collection_failure` (Codex's `parser_lifecycle`);
         - `test_chained_pax_archive_is_a_recorded_collection_failure`;
         - `test_unexpected_collection_error_is_recorded`;
         - `test_lifecycle_error_still_cleans_up_and_saves_a_final_status`.
  - **Actual results after the repair (2026-10-15):**
    - `uv run --locked pytest tests/unit -q` → 219 passed, 1 skipped (the existing symlink-permission skip). Log: `runs/t05-repair1/unit.log`.
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py` → **28 passed** in 38.20 s. Log: `runs/t05-repair1/contract.log`; records: `runs/t05-repair1/contract-tmp/`.
      - Every live run's `cleanup.status` is `confirmed_absent`, confirmed by a real Docker listing: 8 completed, 2 failed, 2 timed_out, 1 collection_failed.
      - Afterwards, `docker ps --all --quiet --filter label=atlas.runner=t05` → empty.
    - **T-01 dependants of `intake.py`:** `intake.py` was refactored (a concrete changed dependency of `audit.py`), so the four intake-dependent T-01 integration files were run once: `test_cli`, `test_review_t01`, `test_review_t01_repair` and `test_t01_scenarios` → 67 passed. Log: `runs/t05-repair1/t01-intake-dependents.log`.
    - The full T-01 acceptance run and `scripts/mutation_check.py` were not rerun: no mutation target (fit_provenance, split_integrity, recorder) or mutation script changed.
    - Copies of Codex's probes (scratch only; the preserved originals were not run or modified) now give:
      - `snapshot_read_before_cap` → 0 bytes read, `SnapshotError`;
      - `nested_json` → `CollectionError malformed_header`;
      - `nested_pax` → `CollectionError malformed_archive` ("consecutive PAX headers");
      - `cleanup_daemon_unreachable` → `removed: false, cleanup: unknown`;
      - `parser_lifecycle` → saved `collection_failed` with cleanup recorded;
      - `entry_cap_after_AST` → no AST call;
      - `injected_cleanup_failure` → `cleanup_failed`;
      - the live case-collision probe → `collection_failed`/`duplicate_entry`, removal confirmed.

      The copies' stubs of `_remove_container` needed the new `cleanup`/`errors` keys.
    - `ruff check .` and `ruff format --check .` → clean. No image rebuild was needed: the recipe and `container_entry.py` are unchanged. 0 inference calls.
  - **Remaining limitations (repair pass 1):**
    - The same-file check uses (st_dev, st_ino). On Windows these come from the volume serial and file index, which matched lstat/fstat on this host. A swap between a component's check and the final lstat is not detected for intermediate directories. A swap to a link before the open is detected (the opened file differs).
    - Docker's `name=` filter is a substring/regex match; the runner compares the exact name in the output. Absence is confirmed by a listing at one instant; a container recreated under the same random name afterwards would not be seen.
    - `cleanup_failed` runs keep any validated outputs in `out/` for diagnosis. Consumers must gate on `status`, as before.
    - The JSON depth pre-check counts brackets outside strings. An unterminated string is scanned as structure, which can only over-count (it refuses more, never less).
    - The other T-05 limitations listed above stand. **T-05 remains unaccepted** pending Codex's verification of this repair.
- **CODEX VERIFICATION OF REPAIR PASS 1 (local Codex, at `44c5a84`, 2026-10-15) and REPAIR PASS 2 (Claude Code, Opus 5.5 high):**
  - **Review evidence:** preserved unchanged at `runs/review-t05/repair1-44c5a84/` (git-ignored). Hash manifests of it (283 lines) and of `session-f494c95-20261015/` (516 lines) were identical before and after this repair. Key files:
    - `review.md` (`72ec2efd…62dbdf68`);
    - `parser_disagreement.py` (`50062399…bbf2a8ce`) and `parser-disagreement-results.json` (`b801c475…5f021060`);
    - `lifecycle_matrix.py` (`b8f29e14…375e0620`) and `lifecycle-matrix-results.json` (`71a3ac0b…efa237a2`);
    - `pax_padding_size.tar` (`6eef07b1…bf096b36`) and `pax_padding_hidden_chain.tar` (`65c05032…d2bc4d13`).
  - **Codex's disposition:**
    - Cleanup (finding 1), bounded snapshot reads (finding 2) and the related candidate-diff fix: **verified fixed**.
    - Parser hardening (finding 3): **partially fixed**. Two P2 structural-limit bypasses remained, both offline host-parser reproductions; neither showed a candidate replacing the supervisor's frame or escaping the container.
    - The guide overstated parser enforcement and container removal.
    - The intermediate-directory race stays a trusted/stable-host-directory assumption (see the repair pass 1 limitations).
  - **Checkpoints:** base `44c5a84`; head = the local commit "Repair T-05 parser findings after Codex verification" (parent `44c5a84`).
  - **Findings, causes and repairs.** Each was a check and a parser reading different representations of the same input.
    1. **PAX padding.**
       - *Cause:* `_check_tar_structure` validated only a PAX header's declared payload. Python 3.11.17's `tarfile._proc_pax` reads and parses the whole padded 512-byte block, so records hidden in the padding reached `tarfile` unchecked.
       - *Codex's reproductions:*
         - `9 size=0` in the padding made a 1-byte member extract as an empty file, and the run completed.
         - The same override exposed 600 chained PAX headers hidden in a member's data. The pre-check accepted it; `tarfile` hit `RecursionError`.
       - *Repair, pre-check:* the padding after the declared payload must be zero. Records are parsed with `tarfile`'s own rules (`[0-9]{1,20} ` length prefix, length ≥ 5, newline-terminated, non-empty key, `=`) and must be UTF-8, with only the key `path`, at most once; that is all the supervisor writes. This replaces the old size/`GNU.sparse` deny-list. Every numeric header field (mode, uid, gid, size, mtime, devmajor, devminor) is checked as octal, because `tarfile` silently ends its member list at an invalid one after the first header. Next-header positions follow `tarfile`'s rule: data blocks follow only regular and unknown types, and a v7 directory has none.
       - *Repair, cross-check:* `_check_tar_structure` returns the layout it read: per member, the first-header offset, data offset, size, PAX records and next-header offset (`TarEntry`). `_validated_members` steps `tarfile` with `tar.next()` one member at a time. Each member, and `tar.offset` afterwards, must equal the pre-checked entry, and `tarfile` must then find only the end marker. So `tarfile` only starts reading at a header the pre-check accepted, and any remaining interpretation difference is refused as `malformed_archive` before it reads further. Rejection still happens before anything is written.
    2. **JSON encoding.**
       - *Cause:* `_json_depth_exceeds` scanned the raw bytes with ASCII string rules, while `json.loads(bytes)` auto-detects UTF-16/UTF-32. In UTF-16 an escaped quote made the scan misplace string boundaries and skip the nesting.
       - *Codex's reproductions:* a 386-byte, 20-deep header was accepted. A 2000-deep one reached `json.loads` and was stopped only by its `RecursionError`.
       - *Repair:* `_header_text` refuses a UTF-8/UTF-16 byte-order mark (UTF-32's starts with UTF-16's) or any NUL byte. UTF-16 and UTF-32 always contain one, so these are "unsupported encoding". It decodes strict UTF-8 ("not UTF-8" otherwise), and both the depth scan and `json.loads` read that one `str`. The supervisor writes ASCII JSON, so no legitimate header is refused.
       - *Why the two now agree:* on any prefix `json.loads` accepts, the scan finds the same strings and brackets, so `json.loads` cannot nest deeper than the count before it fails or returns. A correction to repair pass 1's note: a malformed string *can* make the scan under-count later brackets, but only after a point where `json.loads` has already failed.
  - **Tests.** RED at `44c5a84`: **31 failed**, 67 passed (`runs/t05-repair2/red-at-base.log`). 42 new test items: 31 failed at the base, and 11 passed there by design (the over-rejection guards and checks the base already met). All pass after the repair.
    - `tests/unit/test_runner_collection.py`:
      - `test_non_utf8_header_is_refused_before_parsing[utf-16-le|utf-16-be|utf-16|utf-32 × 20|2000]`: Codex's UTF-16 bypass. It asserts `json.loads` is never called.
      - `test_header_must_be_plain_utf8[utf8_bom|invalid_utf8|nul_byte]`.
      - `test_escaped_strings_cannot_hide_nesting[escaped_quote|escaped_backslash|brackets_after_quote|unicode_escape|utf8]`: passed at base.
      - `test_valid_utf8_headers_with_escapes_are_accepted[brackets_in_strings|non_ascii|every_escape|depth_at_the_limit]`: the over-rejection guard; passed at base.
      - `test_header_depth_check_agrees_with_the_parsed_value`: 400 generated headers full of quotes, backslashes and brackets inside strings. Accepted exactly when the real depth is ≤ 8. Passed at base, which had no UTF-8 bypass.
      - `test_nonzero_pax_padding_is_refused_before_tarfile[hidden_size_zero|hidden_header_chain|hidden_path|nonzero_byte]`: Codex's two archives plus two variants. Asserts `tarfile.open` is never called and nothing is written.
      - `test_pax_records_other_than_one_utf8_path_are_refused[mtime|hdrcharset|uname|duplicate_path|non_utf8_path|empty_key|nul_after_records]`: `nul_after_records` passed at base.
      - `test_member_tarfile_would_silently_drop_is_refused`.
      - `test_tarfile_must_agree_with_the_prechecked_layout[size|next_offset|pax|tarfile_has_more|tarfile_has_fewer]`: the stepped cross-check, given a tampered layout.
      - `test_prechecked_layout_matches_tarfile_for_supervisor_archives`.
    - `tests/unit/test_runner_lifecycle.py`:
      - `test_pax_padding_archive_is_a_recorded_collection_failure[hidden_size_zero|hidden_header_chain]` and `test_utf16_header_is_a_recorded_collection_failure`: Codex's lifecycle cases.
      - Each asserts a saved `collection_failed`, no `out/`, `tarfile` not opened (archives) and cleanup `confirmed_absent`.
  - **Actual results (2026-10-15):**
    - `uv run --locked pytest tests/unit -q` → **261 passed, 1 skipped** (the existing symlink-permission skip). Log: `runs/t05-repair2/unit.log`.
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_runner_contract.py` → **28 passed** in 42.23 s. Log: `runs/t05-repair2/contract.log`; records: `runs/t05-repair2/contract-tmp/`.
      - The 13 runs that started a container all have `cleanup.status` `confirmed_absent`: 8 completed, 2 failed, 2 timed_out, 1 collection_failed. 8 more were refused or not executed without a container.
      - Afterwards, `docker ps --all --quiet --filter label=atlas.runner=t05` → empty.
      - Real supervisor archives pass the stricter pre-check.
    - Copies of Codex's probes are in `runs/t05-repair2/probes/`; the originals were not run or modified.
      - `parser_disagreement.py`: both padding archives → pre-check `malformed_archive: non-zero PAX padding`, nothing written, lifecycle `collection_failed` with removal confirmed. Both UTF-16 headers → `malformed_header: unsupported encoding`.
      - The copy was adapted once: it called the private `_json_depth_exceeds` directly with bytes, and that helper now takes the decoded text.
      - `lifecycle_matrix.py` (unchanged copy): `utf16_depth20` → `collection_failed`, where it previously completed. The eight unknown-cleanup paths are still `cleanup_failed`, and the deep candidate diff is still `too_complex`.
    - **Differential fuzz** (`runs/t05-repair2/fuzz_parsers.py`, log `runs/t05-repair2/fuzz.log`). 4 seeds × (3000 mutated archives + 3000 generated headers): **0 problems**.
      - *Archives:* mutated supervisor-style archives (padding junk, PAX records, header bytes with fixed checksums, type and size fields, numeric fields, arbitrary bytes). For about 1,800 archives per seed the pre-check accepted, and an independent full `tarfile` read produced exactly the pre-checked layout, with header processing nested at most 2 deep.
      - *Headers:* every encoding refusal happened before `json.loads`. No accepted header was deeper than 8, no valid UTF-8 header within the limit was refused, and `json.loads` only ever received `str`.
      - One harness false positive was resolved: a mutation inserted a newline that cut a UTF-32 header to a short NUL-free prefix, which really is UTF-8.
      - This is randomized evidence, not a proof.
    - `ruff check .` and `ruff format --check .` → clean.
      - *Correction:* the documentation commit `44c5a84` had broken `ruff format --check .`. Ruff also formats Python code blocks in Markdown, and the guide's new excerpts were not formatted; that commit had not been checked with ruff. Fixed here.
    - **Not rerun:** T-01 and `scripts/mutation_check.py`. Only `runner/docker.py` and its tests changed, and no T-01 or mutation dependency did. No image rebuild was needed (recipe and `container_entry.py` unchanged). 0 inference calls.
  - **Remaining limitations (repair pass 2):**
    - The accepted archive layout is deliberately narrow: PAX headers may carry only `path`. A future supervisor that writes other PAX records (a float `mtime`, a non-ASCII `uname`) would be refused until this allowlist changes.
    - The pre-check mirrors Python 3.11.17's `tarfile` rules. A later `tarfile` that interprets headers differently would be refused by the stepped cross-check rather than trusted. The cross-check compares `TarInfo.offset`, `offset_data`, `size` and `pax_headers` and `TarFile.offset`; the last is an undocumented attribute of this `tarfile`.
    - Within one `tar.next()` call, `tarfile` reads a PAX header and the header after it. The pre-check computes that second position the same way; this is backed by the cross-check after the call and by the fuzz, not by a proof.
    - The repair pass 1 limitations stand: the intermediate-directory race, a single-instant absence listing, and `cleanup_failed` runs keeping validated outputs. **T-05 remains unaccepted** pending independent verification of this repair.
- **CODEX VERIFICATION OF REPAIR PASS 2 (local Codex, at `eed73ee`, 2026-10-15):**
  - **Review evidence:** preserved unchanged at `runs/review-t05/repair2-eed73ee/` (git-ignored; 1,605 files). Codex's own preservation check found all 1,006 earlier files under `runs/review*` unchanged (`preservation-result.json`, `3d1e0d05…799ee71b`). Key files:
    - `review.md` (`d9cc589f…0a051cb7`);
    - `unit.log` (`df4bd4ee…37016703`) and `unit-short-path.log` (`df358e76…93a26650`);
    - `runner-contract.log` (`05c46ce2…84658069`) and `execution-inspection.json` (`9e5eef2b…c64bef39`);
    - `check_failure_records.py` (`da19961f…969f9385`) and `failure-record-results.json` (`0a8d31f6…530e24a8`);
    - `parser-disagreement-results.json` (`d908a443…5e4ca68f`), `lifecycle-matrix-results.json` (`623c10d7…1e90ec86`) and `probe-adaptation.diff` (`655d992e…36dd73d7`).
  - **Codex's disposition:**
    - PAX padding and archive layout: **verified fixed**. Both original archives now fail with `malformed_archive: non-zero PAX padding`, with no collected files and a final `collection_failed` record after confirmed cleanup. No boundary, size or unsafe-path disagreement that bypasses validation was demonstrated.
    - JSON encoding/depth: **verified fixed**. Both UTF-16 cases fail as an unsupported encoding, and valid UTF-8 headers with escapes are still accepted.
    - Failure records: all eight repaired-input × cleanup combinations save the record they return. Unknown cleanup gives `cleanup_failed`, with the collection failure kept in `execution_reason`. The 21 contract-run records show 13 containers, all with removal confirmed.
    - No existing assertion, isolation flag or cleanup behavior was weakened. The guide was found accurate for this repair.
    - No remaining parser blocker; the six T-05 acceptance criteria are demonstrated by the required Docker suite on this host and image.
  - **Codex's results:**
    - `uv run --locked pytest tests/unit -q`, first run: 1 failed, 260 passed, 1 skipped (see the P3 below).
    - The same command with only a shorter temporary directory: 261 passed, 1 skipped.
    - Contract suite with `ATLAS_REQUIRE_DOCKER=1`: 28 passed in 42.44 s.
    - The copied probes ran with exit 0. 0 inference calls; no commits or pushes.
  - **P3 (pre-existing, not a parser regression): Windows path length.**
    - *Observed:* `test_prechecked_layout_matches_tarfile_for_supervisor_archives` writes a valid file named `d/` + 150 characters + `.txt`. Under Codex's longer temporary-directory prefix (`runs/review-t05/repair2-eed73ee/unit-tmp/…`), its absolute path was 260 characters. `open(target, "xb")` in `_write_members` (`src/atlas/runner/docker.py:776`) raised `FileNotFoundError`. Shortening `unit-tmp` to `u` (253 characters) made the unchanged suite pass. Nothing else changed between the two runs.
    - *Cause:* output writes use ordinary Windows paths, which this host limits to 259 characters, and there is no extended-length (`\\?\`) handling. The pre-check limits archive layout, not the length of the final host path.
    - *Effect:* a file name the archive checks accept can still fail to write under a long destination directory. By code inspection (not exercised in a live run), the `OSError` becomes `collection_failed` with problem `write_failed`, and the partial outputs are removed. It does not produce a false success.
    - *Disposition:* accepted as a documented limitation; no code change. A fix would use extended-length paths for output writes, with a regression test. Until then, keep run directories short on Windows.
- **ACCEPTANCE (2026-10-15):** the lead accepted T-05 at `eed73ee` within its documented scope, based on Codex's independent verification of repair pass 2.
  - **Accepted scope:**
    - the restricted Docker runner and its contract on this Windows 11 Home / Docker Desktop host and image `atlas-runner:t05`: no network, no secrets, read-only root, memory/PID/time limits, path-escape and changed-hash refusals, and no execution without isolation;
    - bounded snapshot and candidate validation and the SPEC §9 hash-bound approval check;
    - bounded collection of the supervisor's frame and archive, always ending in a saved final status;
    - fail-closed cleanup reporting.
  - **Not covered by this acceptance (documented limitations):**
    - **Stable, trusted host directories:** the same-file check does not detect an intermediate directory swapped partway along a path.
    - **Narrow archive format and `tarfile` assumptions:** only the supervisor's layout is accepted (PAX may carry only `path`). The cross-check mirrors Python 3.11.17's `tarfile` and uses its undocumented `TarFile.offset`. It is not a proof about other parser versions.
    - **Programmatic approval:** `approve()` exists; there is no user-facing approval step.
    - **Candidate-produced provenance:** the recorder runs inside the candidate process, so container evidence is candidate-produced (SPEC §9.9).
    - **Unknown physical cleanup:** when Docker APIs fail, cleanup is `unknown` and the run is `cleanup_failed`. That is honest reporting; it cannot confirm that the container was removed. Absence is confirmed by a listing at one instant.
    - **Windows path length (P3, above).**
    - The other RESULT and repair limitations stand. These include: `cleanup_failed` runs keep validated outputs; the archive is held in memory; it was tested only on this host; and the image's Debian packages are pinned only through its digest.
    - **T-06:** the runner does not re-evaluate candidates, and `audit.py` does not accept Docker execution records. Audits stay `trusted_pipeline_only` until T-06 integrates them.

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
- **RUN:** *(create)* `uv run --locked python -m atlas.cli audit benchmarks/t01/s01_faulty --mode agent` (slice 3: plus `--fixture-script FILE` until live inference is authorized)
  - **Amended (lead, 2026-10-15):** the original command named `benchmarks/sensor_generalization`, which does not exist. T-06 integration acceptance uses `benchmarks/t01/s01_faulty`. This does not replace the later `sensor_generalization` benchmark or its generator-freeze requirement (SPEC §14).
- **EVIDENCE:** agent log with model ID, usage and timings.
- **HANDOFF:** Codex review.
- **RECOVERY:** two focused repairs, then Codex diagnosis.
- **TOOLING NOTE (2026-10-18): compaction hooks.** `.claude/settings.json` (project, tracked) runs `scripts/handoff_snapshot.py` on PreCompact (`manual|auto`; writes the git-ignored `runs/handoff/<UTC>.md` and `latest.md`, at most 8 KB: branch, HEAD, porcelain status, last 5 commits, the 5 newest `runs/**/*.log` tails, STATUS.md CURRENT STEP) and its `--context` mode on SessionStart (`compact`; the invariants, the checkout rule and where to resume, 14 lines). Both commands end `|| true`, so neither can fail or block a compaction; the script never opens `.env`. `.claude/settings.local.json` is unchanged.
- **LEAD DISPOSITIONS (2026-10-15):** recorded in DECISIONS.md "T-06 dispositions and slice 1 authorization": CLI approval by the first 12 hex characters of the candidate hash (full hash recorded; no terminal means `NEEDS_INPUT`, no execution); approval waiting excluded from the active budget (total elapsed recorded separately; approved bytes revalidated); `benchmarks/t01/s01_faulty` for integration acceptance (RUN amended above); Docker for both original and candidates in the finished workflow, with original execution explicitly authorized and bound to its snapshot; a schema failure ends the model attempt with no action and no format-repair retry; per-stage token ceilings stay proposed. **No inference is authorized.** Only slice 1 is authorized.
- **SLICE 1 RESULT (2026-10-15): implemented and self-tested; awaiting Codex review; T-06 not accepted.**
  - **Scope:** an approved candidate runs in Docker and the trusted evaluator re-evaluates the full required set. No model client, no live inference, no CLI agent mode or approval prompt, no hosting change, no budget-store work. Approval is programmatic in tests.
  - **Files:**
    - new: `src/atlas/docker_evidence.py` (evaluator-side trust of Docker evidence), `src/atlas/agent/__init__.py`, `src/atlas/agent/execute.py` (approved candidate -> runner -> candidate view -> `evaluate`), `src/atlas/agent/report.py` (original-versus-candidate report);
    - changed: `src/atlas/audit.py` (dispatch by view marker; `_invalidate`; runner-specific limitations; the trusted-fixture check is unchanged and renamed `_fixture_execution_trust`), `src/atlas/contracts.py` (strict `ApprovalRecord`, `DockerExecutionRecord`, `ContainerRuntimeRecord`);
    - tests: `tests/unit/test_candidate_reevaluation.py` (43, offline), `tests/integration/test_candidate_reevaluation_docker.py` (6, Docker);
    - `scripts/mutation_check.py` (copy layout and origin probe, below);
    - docs: DECISIONS.md, SPEC §9.5, §10, §11, this entry, STATUS.md, the learning guide.
    - Not changed: `runner/docker.py`, `candidates.py`, `checks/*`, `policy.py` (still `policy-v1.3`), `hosting_probe/`.
  - **Candidate view and trust anchors** (SPEC §10 "Docker candidate evidence"):
    - host-owned `approval.json` and `candidate.json` are written before execution; `execution.json` is a byte copy of the runner's record, compared with it;
    - collected files enter only through an explicit mapping, after their bytes match the runner's collection hashes; names colliding with host-owned records (case-insensitively) are rejected; every view file is created exclusively (`"xb"`);
    - anchors outside the record: the approval file; the snapshot re-hashed from disk; the staged project and code re-hashed (the code must equal the evaluator's own copy of the mounted modules); the trusted limits; the `docker run` command rebuilt from those limits and the view's own paths; the image confirmed by Docker (`probe(image_id)`: recipe label, non-root user);
    - integrity and binding first, then the status mapping; `runtime.json` corroborates only.
  - **Builder choices for review** (not lead decisions):
    1. On the Docker path an integrity or binding failure makes every PASS **and FAIL** ERROR (`evidence_invalid`), because such evidence cannot be attributed to the approved candidate. The trusted-fixture path is unchanged (an unexpected record there still degrades only PASS). *(Narrowed in repair pass 1: this now applies only to shared failures; an individual artifact affects only its dependants.)*
    2. An inconsistent or missing container `runtime.json` on a completed run, and `collection_failed`, `cleanup_failed` or `runner_error`, establish no PASS (ERROR) but keep FAILs with valid evidence. `failed`/`timed_out` are verified non-completions: PASS becomes NOT_ASSESSED `not_executed`, valid FAILs stand, missing evidence stays ERROR. `runtime.json` is not checked for non-completed runs.
    3. `refused`/`not_executed`: no view and no evaluation; every required assertion is NOT_ASSESSED `not_executed` and the outcome INCONCLUSIVE.
    4. Re-evaluating a view asks Docker to confirm the image; without Docker the evidence is not trusted (fails closed). The recorded command contains absolute staging paths, so a moved view is not trusted.
    5. A run without the view marker is checked only as trusted-fixture evidence, which a Docker record cannot satisfy (cross-runner confusion fails closed).
  - **Evidence (all commands run; logs git-ignored in `runs/t06s1/`):**
    - `uv run --locked pytest tests/unit/test_candidate_reevaluation.py`: 43 passed. The runner's host code runs for real; Docker, the container process and its frame are fakes; the evidence is real adapter output from the trusted host runner on the allowlisted T-01 fixtures. Each negative test changes one thing in a view that passes as a positive control, including **coordinated tampering** (a limit changed together with its recorded command; mounted code changed together with its recorded hashes).
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_candidate_reevaluation_docker.py`: 6 passed, 4 real containers, each removal confirmed. On `s01_faulty` (original: `VIOLATION_FOUND` from the trusted host-fixture audit):

      | Candidate | Execution status | Scientific outcome |
      | --- | --- | --- |
      | fold-local selection and grouped folds (s02's entry point) | `completed` | `NO_VIOLATION_FOUND` |
      | a comment only | `completed` | `VIOLATION_FOUND` |
      | raises before any evidence | `failed` | `INCONCLUSIVE`, no PASS or FAIL |
      | raises after writing the faulty evidence | `failed` | `VIOLATION_FOUND`, no PASS |
    - **Weakened variants** (`runs/t06s1/variants.py`, `variants.log`): an unmodified temporary copy passes, and each of 10 deliberately weakened copies is caught by its targeted test: limits taken from the record, no command check, no mounted-code check, collisions mapped, untrusted evidence keeping FAILs, image not verified, approval taken from the record, runtime not corroborated, failure not treated as non-completion, execution copy unchecked.
    - No host fallback: with isolation unavailable or a missing image, nothing runs; a `subprocess.Popen` guard allows only Docker CLI programs (the real capability probe ran) and fails on any other program; the trusted-fixture runner and bootstrap are patched to fail. Approval binding: changed candidate bytes, a snapshot changed after approval and an approval for another snapshot are refused before Docker is touched.
    - Reporting: the comparison report shows the full required set, execution status and scientific outcome separately, runner-specific limitations, evidence hashes and timing (`active_s` excludes approval waiting; `total_elapsed_s` from the proposal time when given). It labels the slice 1 basis "host trusted-fixture baseline versus Docker candidates". A completed, a refused and a failed candidate leave the original audit's files byte-identical.
    - **Full suite, run once:** `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests -q -p no:cacheprovider --basetemp=runs/t06s1/full` -> **663 passed, 1 skipped** (exit 0, 7 min 51 s).
    - `uv run --locked ruff check .` and `ruff format --check .`: clean.
  - **Mutation-check regression found and repaired:**
    - **Cause:** `scripts/mutation_check.py` copied the package to `<tmp>/atlas`, but `runner/docker.py` locates its build recipe relative to the package (`REPO_ROOT = parents[3]`), so in the copy `recipe_sha256()` read `%TEMP%\..\Dockerfile.runner` and raised `FileNotFoundError`. The new offline tests compute the recipe hash, so the baseline would always fail; the T-05 Docker contract tests already had the same exposure whenever Docker was running (not noticed because the mutation check had not run since T-01).
    - **Demonstration on an unmutated copy** (`runs/t06s1/layout_demo.py`, `layout-demo.log`; the affected tests: the two new files, the T-05 contract tests and the package-origin test): old layout **9 failed, 40 errors**, every one a missing `Dockerfile.runner`; T-05 contract tests alone in the old layout: **14 passed, 14 errors** (`layout-old-t05-contract.log`). Repaired layout: **78 passed**, copy imported.
    - **Fix (test-resource setup only; no runner-design change):** the copy mirrors the repository layout, `<tmp>/src/atlas` plus `Dockerfile.runner` and `docker/runner-requirements.txt` at `<tmp>/`, so the runner reads the copied recipe and its hash equals the repository's (the real runner image is used). `PYTHONPATH` points at `<tmp>/src`. New checks: an origin probe before each suite (the script's child, a trusted-fixture grandchild and the runner's mounted package are the copy; the child's package holds the mutation; the recipe is the copied one with an unchanged hash); pytest `ERROR` lines are parsed and must be absent from the baseline; output naming the recipe files counts as unrelated; temporary test files stay in the run's temporary directory (`--basetemp`). The pre-repair script is kept as `runs/t06s1/mutation_check.pre-repair.py`. No test was skipped, removed or weakened.
    - **Result** (`ATLAS_REQUIRE_DOCKER=1 uv run --locked python scripts/mutation_check.py`, run once, exit 0, `runs/t06s1/mutation_check.log`): every origin check passed in all four runs. Baseline: **663 passed, 1 skipped, 0 errors**. m1: 1 failed, caught by `test_whole_model_fitted_in_one_fold_and_reused_to_predict_another_fails`. m2: 13 failed, caught by `s01_faulty`. m3: 2 failed, caught by `s03a_rebuilt_frame`. No errors and no unrelated recipe-path or package-origin failures in any run. **Mutations caught cleanly: 3/3.**
  - **Limitations:** approval is programmatic (no CLI approval yet); the original runs on the trusted host-fixture runner, so the comparison mixes runners (labelled; final acceptance requires Docker for both); container evidence is candidate-produced; hash and configuration checks establish consistency, not authenticity against an attacker who controls the host; tested only on this Windows/Docker Desktop host; no run-level budget clock, model client or agent CLI mode yet.
  - **Codex review scope:** `src/atlas/docker_evidence.py`, `src/atlas/agent/`, the `audit.py` and `contracts.py` changes, both new test files, **`scripts/mutation_check.py` (layout, resources and origin probe)**, and the DECISIONS/SPEC/TASKS/STATUS/guide text.
- **CODEX REVIEW 1 (slice 1 at `e23e67d`; record `runs/r6/review.md`, preserved unchanged): request changes, three P2.** Verified: coordinated tampering rejected against independent expectations; no host fallback; four live containers removed; execution status separate from scientific outcome; mixed-runner basis labelled; baseline audits unchanged; the mutation-script repair and its saved evidence (not rerun). Findings:
  1. Malformed collected predictions (`audit.py`, unguarded `pd.read_parquet` and `row_id` access): non-Parquet bytes raised `ArrowInvalid`, Parquet without `row_id` raised `KeyError`, leaving no outcome, report or checks after earlier outputs were cleared.
  2. One unavailable collected file (provenance deleted or changed, or runtime deleted, between collection and the view) made the whole view untrusted, erasing valid group-overlap FAILs from separately verified split/table evidence; the same absence at other times kept them.
  3. A manifest removed or corrupted after approval raised `SnapshotError`/`ValidationError` in the bridge before the runner's revalidation, leaving no execution record, outcome or report.
- **REPAIR PASS 1 (2026-10-15): self-tested; awaiting Codex verification; T-06 not accepted.**
  - **Finding 1:** `audit._load_predictions` guards the read (the built-in bases of Arrow's errors: `OSError`, `ValueError`, `TypeError`, `NotImplementedError`; only around the read, so evaluator programming errors still raise) and validates what the consumers read: unique column names, `row_id` and `y_pred` present, row IDs that are strings (as the adapter writes). An unusable artifact is invalid for its dependants (as a hash mismatch is) and named in the outcome reason; finalization always runs. Applies to both runners. `pyarrow` is not imported directly (it is not a declared dependency).
  - **Finding 2:** `docker_evidence.docker_trust` returns a `Trust` (record, problem, mode, evidence index, artifact problems). Shared failures (record, approval, snapshot, staged bytes, configuration, `view.json`, host-name collisions, and **indexed files that were never collected**) stay `UNTRUSTED`. Per artifact, the evidence index takes each collected artifact's hash from the **host collection record**, only if the view indexed exactly that hash; an artifact missing from the view or indexed differently is left out (its dependants see it as missing), and `verified` still checks the bytes on read. Missing runtime is corroboration only: no PASS, FAILs kept. The fixed mapping, host-record protections and collection-hash copy checks are unchanged.
  - **Finding 3:** the bridge's preflight reads the manifest (bounded), requires the hash recorded at snapshot time, then parses it. A missing, changed or invalid manifest writes `execution.json` (`stage: preflight`, `status: refused`, `docker_used: false`), `outcome.json` and `report.json` before Docker is touched. The required set comes only from an optional `trusted_manifest` whose canonical bytes have the snapshot's recorded hash; otherwise the outcome is INCONCLUSIVE with no assertions and the reason "required assertion set could not be reconstructed". This also stops a **valid but changed** manifest from supplying the required set of a refused candidate (previously parsed before the runner's refusal).
  - **Test changed:** `test_collected_file_changed_and_reindexed_is_refused` became `..._is_never_used`: a changed, re-indexed `splits.json` is now unavailable (its dependants ERROR, no PASS) instead of making the view untrusted. It is still never accepted.
  - **Regressions (17, with valid controls):** six malformed-prediction cases through the bridge (non-Parquet, truncated, no `row_id`, no `y_pred`, integer row IDs, repeated column names), each compared with the control and with the established hash-mismatch path (same dependants: `metric.*` and `fit.coverage_complete`), split FAILs unchanged, fresh outputs; the same guard on the trusted-fixture path; provenance missing or changed after collection and runtime missing, through the real bridge; splits lost after collection (never used); an indexed file never collected and a broken shared binding (still global); the manifest missing, malformed or valid-but-changed after approval, with the original audit byte-identical; a trusted manifest bound to the snapshot used, an unbound one refused.
  - **Red at the pre-repair commit:** against a `git archive` copy of `e23e67d` (repository layout, recipe files included): 17 failed, 2 passed (the shared-binding control and an older isolation test) (`runs/t06r1/red-at-base.log`).
  - **Codex's cases reproduced from copies** (`runs/t06r1-codex/`, unchanged copies of `probe.py`, `bridge_probe.py`, `snapshot_probe.py` with a copy of the review's evidence folder): invalid Parquet and missing `row_id` now give VIOLATION_FOUND with all 4 FAILs and fresh outputs; the three bridge cases give VIOLATION_FOUND (provenance: the 3 split FAILs kept, the provenance-dependent fit FAIL lost; runtime: all 4 FAILs kept, no PASS); the provenance controls are unchanged; `limit_and_command` and `mounted_code_and_hash` remain fully untrusted; the manifest cases end INCONCLUSIVE with outputs written.
  - **Focused tests** (`ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/unit/test_candidate_reevaluation.py tests/integration -q -p no:cacheprovider --deselect tests/integration/test_runner_contract.py --basetemp=runs/t06r1/f`): **213 passed, 28 deselected (the runner contract suite), exit 0, 7 min 2 s**. That covers every consumer of `audit.evaluate` (T-01 and T-02 scenarios and reviews, CLI, fixtures) and the Docker re-evaluation tests (4 real containers). The runner contract suite was not rerun: `runner/docker.py` and the container code are unchanged.
  - **Not rerun, with reasons:** the full suite (the changed code's consumers are all in the focused run); the mutation check (targets and script unchanged); the weakened-variant script (its targets are unchanged apart from the per-artifact rule, now covered by direct regressions).
    - **Corrected in repair pass 2 (Codex P3):** this entry first said that m1/m2/m3's catching tests "passed unmutated in the focused run". That was too broad. The 213-test command selected only `tests/unit/test_candidate_reevaluation.py` and `tests/integration` (without the runner contract suite). It included the designated catchers of **m2** (`tests/integration/test_t01_scenarios.py::test_scenario_assertion_statuses_and_outcome[s01_faulty]`) and **m3** (`...[s03a_rebuilt_frame]`). It did **not** include **m1**'s catcher, `tests/unit/test_fit_provenance.py::test_whole_model_fitted_in_one_fold_and_reused_to_predict_another_fails`, which is outside that selection. The evidence for m1 is the mutation check run once on the slice 1 code (`runs/t06s1/mutation_check.log`, before repair pass 1): caught by that test. Neither `checks/fit_provenance.py` nor that test changed in repair pass 1 or 2, and neither has been rerun since.
  - **Not weakened:** `policy-v1.3`, fixtures, the isolation requirements, the runner and every existing assertion are unchanged; the stricter prediction structure check applies to both runners.
- **CODEX VERIFICATION OF REPAIR PASS 1 (`75f7000`; record `runs/r6v/review.md`, preserved unchanged): request changes.** Verified: the prediction, per-artifact integrity and manifest-crash repairs (including six malformed-prediction shapes, per-artifact behavior for provenance, predictions, runtime and splits, global shared failures, the coordinated-tampering probes, the four live containers). Remaining:
  - **P2, approval binding in refusal reports:** the preflight checked the manifest only against the *supplied* snapshot's inventory, and a later runner refusal derived the required set from that already loaded manifest. With approval A (s01) and a valid snapshot B (s11b), the refusal `approval_for_other_snapshot` reported B's 10 required assertions instead of A's 9, intact or with B's manifest missing and B's own manifest offered for recovery. No execution and no PASS: an attribution/contract defect.
  - **P3:** the m1/m2/m3 coverage claim above (corrected there).
- **REPAIR PASS 2 (2026-10-15): self-tested; awaiting Codex verification; T-06 not accepted.**
  - **Fix (`agent/execute.py`):** before any required set is derived, `_approval_binding_problem` requires that the supplied snapshot be the approved one: its recorded inventory must hash to its base hash, and that base hash must be the approval's. If not, nothing runs (the runner is never called), `execution.json` records `stage: preflight`, `status: refused` with `approval_for_other_snapshot` (or `snapshot_inconsistent`), and the outcome is INCONCLUSIVE with **no assertions** and "the approved required assertion set could not be reconstructed". Neither the supplied snapshot's manifest nor an offered recovery manifest is used. The same order applies to the normal and recovery paths: binding, then the manifest hash, then parsing; a matching pair behaves as before.
  - **Test changed:** `test_approval_for_another_snapshot_never_runs` had expected the full required set from the unapproved snapshot (s01 and s02 have identical manifests, so it could not detect substitution). It now expects no assertions.
  - **Regressions (7):** approval A (s01, 9 required) with valid snapshot B (s11b, 10 required): B's manifest intact; B's manifest missing with B's own bound manifest offered for recovery; B's manifest missing with A's manifest offered. Each: preflight refusal, the runner and Docker never started (`exec/` absent; Docker and host entry points patched to fail), no assertions, the baseline audit byte-identical. A sanity test that the two required sets differ in both directions. Matching-pair controls: intact manifest with candidate bytes changed after approval (runner refusal), and a missing manifest with A's bound manifest (recovery); both keep A's required set. An internally inconsistent snapshot object (A's base hash, B's inventory) is refused.
  - **Red at `75f7000`** (`git archive` copy, repository layout): the 5 behavior tests failed; the 3 controls and one unrelated test the filter matched passed (`runs/t06r2/red-at-base.log`).
  - **Codex's reproduction from a copy** (`runs/t06r2-codex/approval_probe.py`, byte-identical to `runs/r6v/approval_probe.py`): both cases now `refused`, INCONCLUSIVE, required set `[]` (neither B's 10 nor A's 9).
  - **Tests run:** `uv run --locked pytest tests/unit/test_candidate_reevaluation.py -q -p no:cacheprovider --basetemp=runs/t06r2/u` -> 67 passed (all preflight and refusal tests); `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_candidate_reevaluation_docker.py -q -p no:cacheprovider --basetemp=runs/t06r2/d` -> 6 passed (the preflight now precedes every live run; matching pairs unchanged). Ruff check and format clean.
  - **Not rerun:** the full suite, the Docker contract suite and the mutation check. The change is confined to the bridge's preflight; no evaluator, runner, check or mutation target changed, and no further dependency was found.
- **CODEX VERIFICATION OF REPAIR PASS 2 (`1d58b20`; record `runs/r6w/review.md`, preserved unchanged): no remaining demonstrated blocker.** The P2 approval-binding defect and the P3 coverage statement are fixed; with the earlier verified repairs, slice 1 is ready for slice 2 within its documented scope. This is not T-06 acceptance and authorizes no inference. The lead gave the go-ahead for slice 2 on 2026-10-15.
  - **What Codex ran:** an unchanged copy of `runs/r6v/approval_probe.py` (both original cases now refused with no assertions); **17 focused regressions** (`-k 'approval or preflight or foreign_snapshot or matching_pair or inconsistent_snapshot or two_snapshots'`: 17 passed, 50 deselected); a new `matrix.py` that replaces the runner with a counted forbidden call (5 boundary cases, zero runner invocations; its first harness version had a probe `KeyError`, corrected and rerun, recorded as a probe error).
  - **What Codex inspected without rerunning:** the builder's Docker log (6 passed) and its four saved execution/outcome pairs (all removals `confirmed_absent`), and the red-at-base log (5 failed, 4 passed, 58 deselected). No base run, live Docker run, full suite, runner contract or mutation run was repeated.
  - **Evidence distinction:** the builder's **67-test unit total has no located standalone log**; it remains builder-reported, not independently confirmed as a complete run. It was not rerun solely to recreate a log.
  - **Preservation:** 51,892 existing evidence files plus the root guide unchanged (Codex's inventory).
  - **Remaining slice 1 limitations** (documented, not new defects): development-fixture evidence; the mixed host-fixture baseline and Docker candidates; Docker availability and unchanged absolute paths for re-evaluation; no model loop yet (slice 2).
- **SLICE 2 RESULT (2026-10-15): offline fixture/stub model controller, implemented and self-tested; awaiting Codex review; T-06 not accepted.**
  - **Scope:** the bounded controller with fixture model replies only. No Nebius transport, no interactive CLI approval, no `--mode agent` CLI wiring, no live inference, no API call, no hosting change. The sleeping Streamlit probe was not touched.
  - **Files (all new; no existing module changed):** `src/atlas/agent/schemas.py` (reply schemas and whole-reply validation), `client.py` (client interface, classified errors, `FixtureClient`, fixture-mode gate), `budget.py` (ceilings and the active-time clock), `network.py` (fixture-mode network denial), `controller.py` (states, tools, approval boundary, log and report); tests `tests/unit/test_agent_schemas.py`, `tests/unit/test_agent_controller.py`, `tests/integration/test_agent_fixture_docker.py`.
  - **Replies:** one JSON object `{"action": {...}}` with exactly one action (`list_project_files`, `read_project_file`, `inspect_evidence`, `propose_patch`, `finish`), validated over the whole reply after removing only surrounding whitespace. Strict types, unknown fields forbidden at every level, every string bounded (paths 200 characters, text 4,000, diff 64 KiB, reply 128 KiB), duplicate JSON keys rejected. No action can approve, execute, change the required assertions or set an outcome; `evaluate_candidate` is a controller step, not a model action. An invalid reply (including `finish_reason` other than `stop` or missing content) ends the run as `ERROR` `schema_failure` with no action and no format-repair retry.
  - **Ceilings:** 6 model attempts per run, each reserved before it is sent and counted even when it fails; at most 1 retry per transient call (timeout, transport, rate limit, server error), only while an attempt remains (otherwise `BUDGET_EXHAUSTED`); a second transient failure ends the run (`ERROR`); a permanent error is not retried. 12 tool operations (the candidate's execution counts as one), 2 revisions, 5 active minutes with approval waits excluded (`budget.paused()`; total elapsed and approval wait recorded). With 6 attempts the default 12-operation ceiling cannot be reached, so its enforcement is tested with a configured ceiling of 2. The `max_completion_tokens` parameter sent with each request (8,000) is recorded as *proposed*; per-stage token ceilings remain unreviewed.
  - **Controller:** INTAKE and the deterministic audit (CHECK) run before any model request; the audit's outputs are never touched afterwards, and every terminal state (`REPORT`, `NEEDS_INPUT`, `NOT_SUPPORTED`, `BUDGET_EXHAUSTED`, `ERROR`) writes `agent_report.json` with the original findings and any completed candidate re-evaluations. Tools read only the snapshot's permitted files (bounded, marked untrusted) and the original audit's check files when they still match their indexed hashes. Outcomes come only from the trusted evaluator (`scientific_outcomes.source`); model text is reported under `model_text` labelled "model-written text; not evidence and not an outcome".
  - **Approval boundary:** a proposed diff is validated (`validate_diff`), then shown to an `Approver` (exact diff, candidate hash, base snapshot hash) with the clock paused. The candidate runs only if the approver returns an `Approval` bound to exactly that candidate and snapshot, and then only through the verified slice 1 executor (Docker, no host fallback, approved bytes revalidated). The default `NoApprover` ends the run `NEEDS_INPUT` with nothing executed; a declined or unbound approval executes nothing. The model client never supplies approvals, and no reply field can carry one. Approvers in tests are explicit test objects; the interactive CLI approver (12 hex characters) is a later slice.
  - **Fixture labelling and network:** `run_agent` refuses `ATLAS_MODEL_MODE` other than `fixture` and any client not marked `live: False` (`LiveModeUnavailable`, before any run directory or audit; no fallback). Every log entry and the report carry `live: false` and `model_id: fixture:<script>`, and the report opens with a NON-LIVE banner. The whole run executes under `deny_network()`, an in-process fixture-testing safeguard (not a sandbox): *as first committed it covered only connections and two resolver functions, so a UDP `sendto` got through (Codex review, below); repair pass 1 extends it*. It does not govern the Docker CLI process, which talks to the local daemon.
  - **Log (`agent_log.jsonl`):** states; per attempt: number, retry flag, parameters, prompt SHA-256, start time, elapsed time, request ID, usage, finish reason, result (`ok`, `schema_failure` with its code, or the error class) and chosen tool; per tool: operation number, arguments (diffs by hash), result hash and size; approvals with their decision.
  - **Tests (all run; logs in `runs/t06s2/`):**
    - One saved run of both unit files (`runs/t06s2/unit-final.log`): **64 passed** (34 + 30).
    - `uv run --locked pytest tests/unit/test_agent_schemas.py`: 34 passed (each action accepted exactly; 27 invalid shapes rejected, including prose, fences, two actions, self-approval, outcome and assertion fields, unknown and execution tools, duplicate keys, oversize, deep nesting, truncation, null and non-string content).
    - `uv run --locked pytest tests/unit/test_agent_controller.py`: 30 passed: invalid replies (no action, one attempt, audit preserved); retry once and counted; second transient failure; permanent error; the seventh attempt never sent; an early retry using one of the six attempts; a retry needing a seventh attempt; a retry that fits as the sixth; tool-operation, revision and active-time ceilings with approval waits excluded; no approver, declined and unbound approvals; fixture text claiming approval; live mode and live clients refused; network denial for `create_connection`, `getaddrinfo` and `socket.connect`; unsupported projects never reach the model; reads limited to permitted files; the baseline audit's files byte-identical to its index; model text cannot set outcomes; and an end-to-end run through the real slice 1 executor with the fake Docker harness, where the host-fixture runner is reached only for the original.
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_agent_fixture_docker.py`: 1 passed (`runs/t06s2/docker-e2e.log`; one real container: fixture replies -> audit -> patch -> test approver -> Docker -> re-evaluation; `completed`, removal confirmed, `NO_VIOLATION_FOUND`, labelled non-live).
    - **Weakened variants** (`runs/t06s2/variants.py`): first run (`runs/t06s2/variants-run1.log`): the unmodified baseline copy passed (63 tests) and 8 of the 9 weakened variants were caught by their targeted tests; `retry_not_counted` was caught only incidentally (an `attempts == 2` assertion), which exposed a weak test: the targeted test put the failure on attempt 6, where the remaining-attempt check stops the retry whether or not retries are counted. Added `test_a_retry_uses_one_of_the_six_attempts` (an early retry, then actions: exactly 6 requests). Second run of the baseline and that variant (`runs/t06s2/variants-run2.log`): the unmodified copy passed (64 tests) and `retry_not_counted` was caught by the new test, so all 9 weakened variants are now caught by targeted tests (plus the passing unmodified baseline; corrected count, Codex P3). Variants: retries not counted, more than one retry, replies extracted from prose, extra fields ignored, duplicate keys allowed, approval not bound to the candidate, a missing approver auto-approving, network not denied, approval waits counted as active time.
    - Ruff check and format clean. Not run: the full suite, the Docker contract suite and the mutation check (no existing module changed).
  - **Limitations:** fixture replies say nothing about a real model's behavior; the original is audited by the trusted host-fixture runner (allowlisted projects only; a non-allowlisted project ends `NOT_SUPPORTED` until the original runs in Docker), so comparisons mix runners and are labelled; approval is programmatic in this slice; the network denial covers this Python process only; prompt contents are logged by hash, not stored.
- **CODEX REVIEW OF SLICE 2 (`4232cc5`; record `runs/r6s/review.md`, preserved unchanged): request changes, four P2 and one P3.** Verified: the six-attempt and retry accounting (including the strengthened early-retry test), the post-approval time check, approval binding across revisions, the allowlisted host baseline and candidate Docker routing, safe finalization for bounded malformed, nested and alternate-encoding replies, restored socket patches, and the saved Docker evidence. Codex ran the 64 schema/controller tests and its own probes; it did not rerun live Docker, the full suite or mutations.
  1. A bounded diff with a 5,000-digit hunk number raised `ValueError` in the shared diff parser, and an approver raising `OSError` escaped too; neither run wrote `agent_report.json` (the baseline audit stayed intact).
  2. The fixture network guard missed UDP: a fixture client sent one byte to a loopback receiver, and the report still said "no network was used". No external service was contacted. `gethostbyname` also stayed callable.
  3. A `finish` reply returning after the 300-second active ceiling ended `REPORT` (only tool actions re-checked time).
  4. The diff schema limited characters, not bytes: an 80,000-byte diff of 40,000 "é" passed, reached the proposal tool and allowed another request (downstream validation still prevented execution).
  - P3: the weakened-variant count included the baseline (nine variants plus one baseline, not ten).
- **SLICE 2 REPAIR PASS 1 (2026-10-15): self-tested; awaiting Codex verification; T-06 not accepted. Slice 3 stays paused.**
  - **1. Error finalization.** `candidates._parse_hunks` (the shared diff parser) now matches hunk numbers as ASCII digits only (`re.ASCII`: `\d` also matched other scripts' digits, which `int()` accepts) and refuses more than 9 digits *before* `int()` *(as first repaired, the new-start field was missed; repair pass 2 bounds all four)*, as `CandidateRejected("malformed_diff", "hunk line number out of range")`: a recorded proposal rejection, not a crash, and Python's digit limit is unchanged. In the controller, a failing approver is a recorded `ERROR` (`approver_error: <type>`), never an approval; any other unexpected exception is finalized first (`agent_report.json` with `ERROR`, `internal_error in <stage>: <type>`, the original findings and completed candidates) and then **re-raised**, never reported as success. Only exception types are recorded, never messages (which may hold paths or secrets). The report's comparison section is built defensively so the report is still written. *(Superseded in repair pass 2: that swallowed a reporting failure as normal completion; a reporting failure is now an ERROR with a minimal report, then re-raised.)*
  - **2. Network guard.** `deny_network()` now also patches `socket.socket.send`, `sendall`, `sendto`, `sendmsg` (where present) and `sendfile`, on the class, so sockets created before the guard are covered, and the resolvers `gethostbyname`, `gethostbyname_ex`, `gethostbyaddr` and `getnameinfo`, besides `connect`, `connect_ex`, `create_connection` and `getaddrinfo`. Every patch is restored in a `finally`, after success or an exception. Its documented scope: an in-process safeguard for fixture tests, **not** a sandbox; it does not govern other processes (the Docker CLI), raw `_socket` use or native code, and is not evidence that no traffic occurred. The report banner no longer says "no network was used".
  - **3. Active time.** Time is checked immediately after every reply returns, before the reply is validated or any action (including `finish`) consumed; a late reply is logged as `late` and ends the run `BUDGET_EXHAUSTED`. The deadline refuses further work; it does not interrupt a call already in progress (a live transport's own timeout bounds that). The post-approval check and the exclusion of only actual approval-wait time are unchanged.
  - **4. Diff bytes.** `ProposePatch` validates the diff's UTF-8 byte length (encoding failures are schema failures) during reply validation, before dispatch; an oversized diff ends the run `ERROR` `schema_failure` with no action, no revision and no further request. The character bound, the 128 KiB reply cap and `validate_diff` stay as further limits.
  - **Regressions (21 new, with controls):** schemas: a diff of exactly 65,536 bytes accepted (multibyte, ASCII, mixed), one byte over, 80,000 bytes and ASCII-then-multibyte rejected, a lone surrogate rejected. Controller: the 5,000-digit hunk as a recorded rejection followed by a normal finish; a failing approver (`ERROR`, report saved, no execution, the exception message absent from log and report); an executor failing on the second revision (report saved with `internal_error in EXECUTE: RuntimeError`, the first candidate kept, the exception re-raised, the guard restored); UDP `sendto` to a loopback receiver (denied, nothing received); `sendall` on a loopback TCP connection opened before the run (denied, nothing received, works again after the run); `gethostbyname`, `gethostbyname_ex`, `gethostbyaddr` and `getnameinfo` denied; the banner without the no-network claim; late `finish` and late tool replies (one request, nothing consumed, no tool operation, attempt logged `late`); a 10,000-second approval wait alone does not exhaust time; the oversized multibyte diff through the controller (one request, no tool operation or revision). The baseline audit is checked byte-for-byte against its index in the failure cases.
  - **Red at `4232cc5`** (`git archive` copy, repository layout): 15 failed; 6 passed, all controls or cases the old code already handled (the three at-limit acceptances, the ASCII-then-multibyte case that exceeded the old character limit, the surrogate that Pydantic already rejected, and the excluded approval wait) (`runs/t06s2r1/red-at-base.log`).
  - **Codex's reproductions from copies** (`runs/t06s2r1-codex/`): byte-identical copies of `probe.py`, `additional.py` and `multibyte.py`, run from the repository root. `probe.py` (exit 0): `late_finish` now `BUDGET_EXHAUSTED` after one request; `approver_error` now `ERROR` with a report; the other cases unchanged (surrogate, UTF-16, deep nesting, 5,000-digit integer: `ERROR` with reports; non-ASCII text, wrong snapshot, stale revision: `REPORT`; untrusted project: `NOT_SUPPORTED`). `multibyte.py` (exit 0): `ERROR` after one request, no execution. `additional.py` exits 1 *by design of the probe*: `hunk5000` now `REPORT` with no execution and `post_approval_time` `BUDGET_EXHAUSTED` before execution, but after the UDP case the script calls `recvfrom` expecting the datagram that used to arrive; none arrives now, so it times out. A clearly labelled adapted copy (`additional_adapted.py`, changing only those two reporting lines) records the UDP case as `client_error: NetworkDenied` with nothing received and literal `gethostbyname` as denied (its report counts include the identical run's reports in the shared folders).
  - **Tests (saved log `runs/t06s2r1/tests-final.log`):** `uv run --locked pytest tests/unit/test_agent_schemas.py tests/unit/test_agent_controller.py tests/unit/test_candidates.py -q -p no:cacheprovider --basetemp=runs/t06s2r1/final` -> **136 passed, 1 skipped** (41 schema, 44 controller, 52 diff-parser tests; the skip is the existing symlink test). `test_candidates.py` was included because the shared diff parser changed. Ruff check and format clean.
  - **Not rerun:** the full suite, live Docker, the Docker contract suite, the mutation check and the weakened variants. The parser change only rejects inputs that previously crashed or used non-ASCII digits; its direct tests passed.
  - **Limitations (unchanged or clarified):** fixture-only evidence; programmatic approval; the mixed host-fixture/Docker basis; the network guard's in-process scope; prompts logged by hash.
- **CODEX VERIFICATION OF SLICE 2 REPAIR PASS 1 (`dedf5e2`; record `runs/r6u/review.md`, preserved unchanged): request changes, one P2 and one P3.** Verified: the four original reproductions are prevented (the 5,000-digit old-start hunk is a recorded rejection; the failing approver is `ERROR` with a report; faults before and during intake finalize and re-raise; the guard denies every listed send and resolver path on loopback, including sockets opened before it, and restores after success and exceptions, with `sendmsg` absent on this Windows runtime and so not exercised; late `finish` and late tool replies are refused; exactly 65,536 UTF-8 bytes accepted and 65,537 rejected). Codex reran the 136 schema/controller/parser tests and its copied probes (`additional.py` exits 1 on its obsolete `recvfrom` expectation; its adapted copy exits 0).
  - **P2:** `_report` caught a `comparison_report` exception, saved `comparison: {unavailable: ...}` and still finished `REPORT` without re-raising: a reporting failure looked like normal completion (`comparison_error` case of `boundary.py`).
  - **P3:** the hunk's new-start number (group 3) was not passed through `_hunk_number`, so 5,000 ASCII digits there still produced an accepted candidate that reached APPROVAL (no crash, no execution); the other three fields were bounded, and non-ASCII digits were refused in all four.
- **SLICE 2 REPAIR PASS 2 (2026-10-15): self-tested; awaiting Codex verification; T-06 not accepted. Slice 3 stays paused.**
  - **Reporting failure.** `_report` no longer swallows a `comparison_report` exception. If building the report fails, the run becomes `ERROR` (`internal_error in REPORT: <type>`) unless an earlier error is already being finalized, which stays primary. A minimal report is then written from state the run already holds, **without calling the report builders again**: the terminal state and reason, `report_failure` (stage and exception type, no message), the states, the original's outcome and required-set statuses, and each candidate's execution status and scientific outcome. Then the primary exception is re-raised. If the minimal report cannot be built or written, the original exception still propagates, with an `add_note` saying `agent_report.json was NOT saved (<type>)`, and no report is claimed. *(Too broad as committed: a failure logging the terminal state could still replace the primary exception and skip the report; fixed in repair pass 3.)*
  - **Hunk numbers.** `_parse_hunks` now bounds all four numbers, including the new start (validated, then unused), with the existing ASCII and 9-digit limits; omitted-count forms (`@@ -L +L @@`) still work.
  - **Regressions (22 new, with controls):** controller: a successful-report control; the injected `RuntimeError` in `comparison_report` (ERROR, minimal report with findings, no `comparison`, the builder called once, no raw message in report or log, baseline byte-identical, re-raised); a reporting failure during an earlier executor error (the executor error stays primary and is re-raised, the reporting failure recorded); the fallback write also failing (the original raised with the note, no report file); each of the four header positions with 5,000 digits refused before APPROVAL (the approver never asked, no execution). Diff parser: a 4 x 3 matrix (5,000 digits, 10 digits and a non-ASCII digit in each position) rejected as `malformed_diff`; controls: the unchanged diff, a 9-digit new start (within the bound) and the omitted-count form accepted.
  - **Red at `dedf5e2`** (`git archive` copy, repository layout): 6 failed (the three reporting-failure tests, the controller new-start case, and the 5,000- and 10-digit new-start parser cases); 17 passed: 16 new tests (the other positions and the non-ASCII cases, which the earlier repair already covered, and the controls) plus the existing `test_live_mode_is_refused_without_fallback`, which the selection also matched (clarified after Codex's verification) (`runs/t06s2r2/red-at-base.log`).
  - **Codex's boundary reproductions from copies** (`runs/t06s2r2-codex/`, byte-identical `probe.py`, `boundary.py`, `guard_schema.py`, run from the repository root; all exit 0): all eight hunk cases rejected, with the oversized field never converted by `int()`; `oversized_new_start` now a recorded rejection followed by `REPORT`, no execution; `comparison_error` now saves `ERROR` "internal_error in REPORT: RuntimeError" with no raw message and re-raises, the baseline unchanged; `error_before_intake` and `error_during_intake` unchanged (ERROR in START and INTAKE, re-raised); `guard_schema.py` boundaries unchanged.
  - **Tests (saved log `runs/t06s2r2/tests-final.log`):** `uv run --locked pytest tests/unit/test_agent_schemas.py tests/unit/test_agent_controller.py tests/unit/test_candidates.py -q -p no:cacheprovider --basetemp=runs/t06s2r2/final` -> **158 passed, 1 skipped** (41 schema, 52 controller, 66 diff-parser; the skip is the existing symlink test). Ruff check and format clean.
  - **Not rerun:** live Docker, the full suite, the Docker contract suite and the mutation check. The parser change only adds the bound to the new-start field, which applying does not use; valid diffs are unaffected (its direct tests passed).
- **CODEX VERIFICATION OF SLICE 2 REPAIR PASS 2 (`4e3afae`; record `runs/r6z/review.md`, preserved unchanged): request changes, one P2.** Verified: the standalone comparison failure now saves a minimal ERROR report and re-raises; the earlier-error, triple-failure (executor + comparison + write) and pre-intake controls keep the primary exception; the minimal report reads held state only; all four hunk fields are bounded (no oversized value reaches `int()`). Codex ran 29 selected controller/parser tests (`-k 'report or hunk or fallback or unexpected_error'`) and its copied `boundary.py` plus a new `combined.py`.
  - **P2:** the two terminal-state log calls (`enter(terminal)` and, after a report failure, `enter(ERROR)`) ran outside any protection and before the primary exception was retained. An injected failure writing the terminal ERROR log entry made the *secondary* `OSError` escape, with no report and no note, after a comparison failure or an executor failure (`combined.py`: `comparison_and_log`, `executor_and_log`).
  - **Count clarification:** the repair pass 2 red run selected 23 tests: the 22 new ones plus the existing `test_live_mode_is_refused_without_fallback`, which the filter also matched. So 6 new failures, 16 new passes and 1 existing passing test (corrected above).
- **SLICE 2 REPAIR PASS 3 (2026-10-15): self-tested; awaiting Codex verification; T-06 not accepted. Slice 3 stays paused.**
  - **Fix.** Finalization is one step, `_Run._finalize`, entered with the run's exception (if any) already retained as primary, before any finalization I/O. The terminal state is set in memory (`_set_state`) independently of logging. Logging it is a single best-effort attempt; a failure is recorded and never retried, and after one logging failure nothing more is logged (no recursion). The full report is built once; if that fails, the minimal report is built from held state without calling the builders again. The first failure in finalization becomes primary only if there was none (the run then ends ERROR naming that stage: `TERMINAL_LOG` or `REPORT`); otherwise it is secondary. Every finalization failure is recorded by stage and exception type, never by message, in the report's `finalization_failures`. The report is written once; if that fails, the primary exception carries the existing note `agent_report.json was NOT saved (<type>)` and no report is claimed; with no earlier failure, the write failure itself propagates. *(As committed, that path skipped the ERROR state and the note; fixed in repair pass 4.)*
  - **Failure matrix (8 new tests; fault injection only: a pre-built exception raised when writing a terminal-state log entry, from `comparison_report`, or when writing `agent_report.json`; no disk filling or permission changes):** executor failure + terminal-log failure; comparison failure + terminal-log failure; terminal-log failure alone; each with the report destination usable and with the report write also failing; plus normal completion and normal completion with an unwritable report as controls. Each checks the propagated exception's identity, at most one failed log attempt, the comparison builder called once, the report's terminal state, reason and `finalization_failures` (or no report and the note), no raw message in report, note or log, the baseline audit byte-identical to its index, and the network guard restored.
  - **Red at `4e3afae`** (`git archive` copy, repository layout): all 6 matrix cells failed; the 2 controls passed (`runs/t06s2r3/red-at-base.log`).
  - **Codex's probes from copies** (`runs/t06s2r3-codex/`: byte-identical `probe.py`, `boundary.py`, `combined.py`, run from the repository root; both exit 0): all four combined cases keep the primary exception's identity; `comparison_and_log` and `executor_and_log` now save ERROR reports (`internal_error in REPORT: RuntimeError` and `internal_error in EXECUTE: ValueError`) with the secondary failures by stage and type and no raw message; `executor_comparison_write` still propagates the `ValueError` with the NOT-saved note; `early_and_reporting` unchanged; baselines unchanged and the guard restored throughout. `boundary.py` results unchanged.
  - **Tests (saved log `runs/t06s2r3/tests-final.log`):** `uv run --locked pytest tests/unit/test_agent_controller.py -q -p no:cacheprovider --basetemp=runs/t06s2r3/final` -> **60 passed** (52 earlier + 8 new). Only the controller changed (the schemas and diff parser did not). Ruff check and format clean. Not rerun: Docker, the full suite and the mutation check.
- **CODEX VERIFICATION OF SLICE 2 REPAIR PASS 3 (`1266b44`; record `runs/r6y/review.md`, preserved unchanged): request changes, one P2.** Verified: the terminal-log defect is fixed; a pending exception is retained before finalization; logging failures disable further terminal-log attempts and never stop the report attempt; the full report is attempted once and the fallback never calls the failed builder; exact primary identity in every combination of executor, terminal-log, comparison and write failures (all six matrix cells and Codex's copied `combined.py` cases); baselines preserved and patches restored. Codex reran the 60 controller tests, its copied `combined.py` and a new `order_probe.py`.
  - **P2:** when report writing was the *first* failure, the write branch re-raised immediately: the exact exception propagated and no report existed, but the run's in-memory and logged terminal state stayed `REPORT` and the promised NOT-saved note was missing (`order_probe.py`, case `write_first`). The unwritable-report control checked only identity and absence of output, so it passed.
  - Documentation: the module docstring and the repair record promised ERROR and the NOT-saved note for every unwritable report, which was too broad for this path.
- **SLICE 2 REPAIR PASS 4 (2026-10-15): self-tested; awaiting Codex verification; T-06 not accepted. Slice 3 stays paused.**
  - **Fix.** A report-write failure now goes through the same `fail()` path as the other finalization stages, under its own stage `REPORT_WRITE`. As the first failure it is retained as primary (the exact exception), the in-memory terminal state becomes ERROR (`internal_error in REPORT_WRITE: <type>`), the log is corrected once if it is still usable (a correction failure is recorded as a secondary `TERMINAL_LOG` failure and the write exception stays primary), and the primary exception gets the note `ATLAS: agent_report.json was NOT saved (<type>)`. After an earlier failure, behavior is unchanged: the earlier exception stays primary, keeps its ERROR state and reason, and gets the note. Report construction and writing are attempted once; a logging operation that failed is not retried.
  - **Remaining exits inspected:** after a successful write the run either returns (`REPORT` or another intended terminal state) or re-raises a primary exception whose ERROR state was already set by `run()` or `fail()`; the write-failure exit is the one fixed here. The other finalization steps do no I/O (in-memory state, dictionary updates, `add_note`). `BaseException` (keyboard interrupt, `SystemExit`) is deliberately not intercepted.
  - **Tests.** The unwritable-report control is replaced by `test_an_unwritable_report_ends_error_with_the_note`, which checks the exact exception, the exact notes, no report, the in-memory terminal state and reason, the logged states, no raw message and the baseline, for (1) a first write failure with logging available (REPORT logged, then corrected to ERROR once), (2) a first write failure whose log correction also fails (one attempt; the write exception stays primary; the log keeps REPORT) and (3) an earlier executor error followed by a write failure (unchanged: the executor error stays primary with its reason, one ERROR entry, the note). Plus `test_report_construction_and_writing_are_not_retried` (one build, one write) and a normal-completion control checking the in-memory, logged and reported state.
  - **Red at `1266b44`** (`git archive` copy, repository layout): the two first-write-failure cases failed; passed: the earlier-error case and the no-retry and normal controls (correct before too), plus the existing `test_a_permanent_error_is_not_retried`, which the selection also matched (`runs/t06s2r4/red-at-base.log`: 2 failed, 4 passed).
  - **Codex's reproduction from a copy** (`runs/t06s2r4-codex/`: byte-identical `probe.py` and `order_probe.py`, run from the repository root, exit 0): `write_first` now calls `log:REPORT, comparison, write:REPORT, log:ERROR`; the exact `OSError` propagates with the NOT-saved note; memory and log both end ERROR `internal_error in REPORT_WRITE: OSError`; no report; baseline unchanged; patches restored. `log_then_comparison` and `pending_then_all` unchanged.
  - **Tests run (saved log `runs/t06s2r4/tests-final.log`):** `uv run --locked pytest tests/unit/test_agent_controller.py -q -p no:cacheprovider --basetemp=runs/t06s2r4/final` -> **64 passed** (60 earlier, minus the replaced control, plus 5 new). Only the controller changed. Ruff check and format clean. Not rerun: Docker, the full suite and the mutation check.
- **CODEX VERIFICATION OF SLICE 2 REPAIR PASS 4 (`69042a1`; record `runs/r6x/review.md`, preserved unchanged): verified within the requested ordinary-exception scope; no remaining demonstrated blocker.** With the earlier verified repairs, slice 2 is ready for slice 3 within its documented scope. This is not T-06 acceptance and authorizes no inference or hosting change. The lead authorized slice 3 on 2026-10-15.
  - **What Codex ran:** 16 focused controller tests (`-k 'unwritable_report or finalization_failure_matrix or report_construction_and_writing or normal_completion or reporting_failure or fallback_cannot or unexpected_error'`: 16 passed, 48 deselected) and an unchanged copy of `runs/r6y/order_probe.py` (`write_first` now ERROR in memory and log with the note, the exact exception, no report; `log_then_comparison` and `pending_then_all` unchanged).
  - **What Codex inspected without rerunning:** the builder's 64-test log and the red-at-base log. The whole controller suite, Docker, the full suite and mutations were not rerun.
  - **Documented limits (not defects):** handling covers ordinary `Exception`s, not `BaseException`; a persistent log or report cannot be guaranteed on an unusable sink (memory and the propagated exception are); failed logging is not retried. Earlier limitations stand: fixture-only replies, programmatic approval, the mixed baseline, the in-process network guard, deadlines between operations.
  - **Preservation:** 66,149 entries unchanged (Codex's inventory).
- **SLICE 3 RESULT (2026-10-16): Docker baseline, CLI approval and the production Nebius client (offline only); implemented and self-tested; awaiting Codex review; T-06 not accepted.**
  - **Scope:** no real Nebius request (not even metadata), no live inference, no hosting change, no procedure memory or hosted budget store; the sleeping Streamlit probe untouched. The s01 fixture is a development fixture, not independent benchmark evidence.
  - **Files:** new `src/atlas/agent/approval.py` (terminal approver, inert display), `src/atlas/agent/nebius.py` (production client, offline-verified), `tests/unit/test_agent_slice3.py`; changed `src/atlas/agent/controller.py` (Docker original, `_decide`, live gating, cost ledger, runner-specific labels), `src/atlas/agent/client.py` (errors carry `code`, `dispatched`, `usage`; replies carry `served_model`; the mode message), `src/atlas/agent/budget.py` (`CostLedger`), `src/atlas/cli.py` (`--mode agent`), `tests/unit/test_agent_controller.py` (an explicit test-only host baseline), `tests/integration/test_agent_fixture_docker.py`, `tests/integration/test_cli.py`.
  - **1. Docker baseline.** In agent mode the run goes INTAKE -> snapshot -> APPROVAL of the original (kind `original`, the unmodified entry point's hash on that snapshot) -> CHECK: the original runs through the slice 1 executor exactly like a candidate (Docker, hash-bound, approved bytes revalidated) and is evaluated by the same trusted path -> MODEL loop. The report's basis then reads "Original and candidates all executed in the isolated Docker runner". **No host baseline exists in production:** if Docker is unavailable the original is not executed, the run ends `ERROR` `original_not_executed: not_executed: isolation unavailable: ...; no host fallback` (builder choice of terminal state), no model request is made and the original is reported INCONCLUSIVE with every assertion `not_executed`. Declined, unbound or unavailable authorization ends `NEEDS_INPUT` with nothing executed. Audit mode (`--mode audit`, the trusted host-fixture runner) is unchanged. The slice 2 controller tests now pass an explicit, documented **test-only** host-fixture baseline (autouse fixture in that module), since they test the model loop.
  - **2. CLI and approval.** `python -m atlas.cli audit <project> --mode agent --fixture-script FILE` (fixture replies only; `ATLAS_MODEL_MODE` other than `fixture` is refused with exit 2 and nothing runs; `agent+memory` remains unimplemented). `approval.TerminalApprover` shows the kind, entry point, snapshot hash and full code hash, and for candidates the model-written rationale and the diff, **rendered inert** (every control or format character other than newline, such as escape sequences, carriage returns, backspaces and bidirectional overrides, is shown as a visible escape, so model text cannot move the cursor, hide lines or recolor the prompt). The person must type the first 12 characters of the code hash (whitespace stripped, case-insensitive, one attempt); the approval records the full hash and snapshot hash. No terminal or closed input -> `NEEDS_INPUT`, nothing executed; any other input declines (logged `confirmation_mismatch`). Only the approval wait is excluded from active time; binding and the time budget are rechecked after approval. Exit codes: 0 REPORT, 1 ERROR, 3 NEEDS_INPUT, 4 BUDGET_EXHAUSTED, 5 NOT_SUPPORTED, 2 refused before running.
  - **3. Nebius client (`nebius.NebiusClient`), mocked transport only.** OpenAI SDK 3.31.0 (on `httpx2`) with `max_retries=0` and an explicit `httpx2.Timeout`; the request body is exactly `model`, `messages`, `max_completion_tokens`, `n=1` (no `response_format`, tools or streaming: prompt-requested JSON, application-validated). Errors are classified by type and HTTP status only (`model_timeout`, `transport_error`, `rate_limited`, `server_error_<status>` transient; `http_<status>` and client errors permanent) and raised **outside** the `except` blocks, so no SDK exception, request or header is chained; the SDK's own messages, which can echo provider text, are never used. Before sending, `check_request` refuses a prompt whose *estimated* token count exceeds `max_input_tokens` (not dispatched, not counted). *[Corrected in repair pass 1: this is an assumption-dependent estimate, not a proven bound.]* After a reply, exactly one choice is required, usage above either ceiling fails closed (`usage_over_ceiling`, charged at the reported usage), and the served model is recorded. The key is read from the git-ignored `.env` only when a caller asks (`load_api_key`) and goes only to the SDK; the client's `repr` omits it. The controller accepts a live client only with `live_authorized=True`, which nothing in this build passes; the CLI cannot reach it.
  - **Cost accounting (`budget.CostLedger`).** Before each dispatched attempt the ceiling cost (both ceilings at the configured listed prices) is reserved; complete usage settles it; a dispatched request with unknown usage (timeout, connection failure, missing usage) keeps the full ceiling; only a request refused before sending is released. The report's `cost` section gives the conservative total, the unknown-usage count and per-attempt entries, labelled "accounting only; not a spending authorization". Fixture runs show the ledger as not applicable.
  - **Open decisions for the lead (flagged, not encoded; needed before any live run):**
    1. **Per-call ceilings.** The proposed table in `docs/HOSTING_PROBE.md` is per *stage* (claim 3,000/3,000; diagnosis 12,000/6,000; two revisions 12,000/8,000; report 8,000/4,000; spare 12,000/8,000 input/output tokens), totalling 59,000/37,000 tokens = **$0.0510** at the listed $0.30/$0.90 per 1M (recomputed exactly, matching `hosting_probe/cost_calc.py`). The controller's turns are uniform (every reply chooses one action), so the table does not map onto them. Applying the largest stage ceiling (12,000/8,000) to all six attempts gives 72,000/48,000 tokens = **$0.0648**, above the $0.051 estimate. `NebiusConfig` therefore requires every ceiling, timeout, price and the template allowance explicitly; this build sets no values. The $0.051 figure is a planning estimate, not a spending authorization.
    2. **Input bound versus prompt size.** Without the provider's tokenizer, the pre-send input estimate used here (*[corrected in repair pass 1: an estimate, not a proven or "safe" bound]*) assumes no token covers less than one UTF-8 byte of message text, plus a configured per-message template allowance (unverified for this tokenizer). Measured for s01 with a 16-token allowance, the bound is about 4,100 to 6,100 per turn over three turns, within a 12,000-token ceiling; but the controller allows prompts up to 96,000 characters (`MAX_PROMPT_CHARS`, several 16,000-character file reads plus history), which this bound would refuse. The prompt bound and the input ceiling must be aligned (or another bound adopted) before slice 4. A refused prompt is never sent and is not counted as an attempt.
  - **Tests (all run; logs in `runs/t06s3/`):**
    - `uv run --locked pytest tests/unit/test_agent_controller.py tests/unit/test_agent_slice3.py -q -p no:cacheprovider --basetemp=runs/t06s3/final` -> **111 passed** (64 + 47; `tests-final.log`). The 47 slice 3 tests cover: the approver (typed prefix with full hash recorded; eleven characters, the full hash, `yes`, empty and wrong input decline; no terminal and closed input; inert display of escape, carriage-return, backspace, right-to-left-override and zero-width characters; the original request); the client with a mocked transport under the network guard (request shape and the bearer header only in the outgoing request; timeout, connection, 429, 503, 400 and 401 each classified once with no SDK retry, no chained exception and no key or SDK text in the error; the pre-send input refusal; usage over ceiling; two choices; missing usage; cost figures; explicit configuration validation; the key file); the controller with the mocked client (refused without `live_authorized`; a live run labelled live with costs settled and request IDs logged, the key absent from log and report; two timeouts keeping both ceilings reserved; retry exhaustion at the sixth attempt; prose, `length` and missing-content replies authorizing nothing; an oversized prompt never sent or counted; usage over ceiling charged; a reporting failure finalized); the Docker baseline through the real slice 1 executor with fake Docker and the host runner patched to fail (original then candidate approved, both in Docker, basis and limitations labelled; no, declined and unbound authorization; Docker unavailable: no execution, no model request, no fallback; the post-approval time check refusing the original); and the CLI (typed approvals for both, a wrong confirmation, no terminal, no Docker, live mode and missing script refused).
    - `ATLAS_REQUIRE_DOCKER=1 uv run --locked pytest tests/integration/test_agent_fixture_docker.py tests/integration/test_cli.py -q -p no:cacheprovider --basetemp=runs/t06s3/d` -> **4 passed** (`docker.log`): the controller with real Docker for the original and the candidate, and the complete local CLI path with approvals typed at a simulated terminal (two containers each, removals confirmed, full hashes recorded).
    - Ruff check and format clean. Not rerun: the full suite, the Docker contract suite and the mutation check (no evaluator, runner, check, schema or diff-parser change); the slice 2 schema tests (unchanged).
  - **Limitations:** no real model has been called by this controller; the live configuration values and the input-bound approach are open (above); the terminal approver trusts the local terminal session; deadlines apply between operations; the in-process network guard covers fixture runs only.
- **CODEX REVIEW OF SLICE 3 (`runs/s3v/review.md`, at HEAD `5aad204`, target `943f046`): request changes; slice 3 not fully verified within its offline scope.** Three P2 defects and two P3 issues. Codex independently ran 110 unit tests (1 deselected: the key-file test, excluded to honour the literal `.env` rule) and a mocked-transport probe. Its Docker-required run gave 2 passed and 2 setup errors (daemon unavailable); it inspected the builder's saved Docker evidence (hashes matching, removal confirmed). Verified by Codex: approval binding, no-host-fallback routing, inert display (227 control and format characters, none unescaped), and the earlier finalization controls.
  - **P2-1, invalid usage bypasses validation:** negative counts settled a negative cost; a fractional over-ceiling count still reached REPORT; a synthetic key in a usage field reached the log.
  - **P2-2, partial usage understates known cost:** 1,000,000 known input tokens with missing output usage kept only the $0.0672 reservation instead of the known $0.30.
  - **P2-3, invalid configuration accepted:** an infinite or `True` timeout, and negative, NaN or infinite prices.
  - **P3-1, refusal reports misdescribe execution:** with no Docker, or a snapshot changed after approval, the report said the original ran in Docker and the comparison basis claimed a host baseline. Neither ran.
  - **P3-2, the token estimate was described as a safe bound** (`nebius.py`, this entry, SPEC §11, the guide), and the guide had a stale slice 2 paragraph.
- **SLICE 3 REPAIR PASS 1 RESULT (2026-10-16): implemented and self-tested; awaiting Codex verification; T-06 not accepted.** No provider request, no secret inspection (the key-file test reads only a synthetic temporary file), no hosting change; slice 4 not started.
  - **P2-1, usage validated first.**
    - `client.sanitize_usage` admits a count only as a genuine non-negative `int` (`type(value) is int`, so `bool`, floats including `1000.0`, strings, NaN, infinities, negatives and objects are invalid). A missing or null count is explicitly unknown.
    - `NebiusClient._reply` validates usage before the ceiling check, the choice check or anything else. Invalid usage raises `invalid_usage` with only the validated counts and the invalid fields' names.
    - The controller sanitizes again for **any** client (fixture replies included), and for errors as well as replies. This happens before the ledger, the log, the time check or any action. Invalid usage ends the run `ERROR invalid_usage` *[corrected by repair pass 2: in pass 1 this held for replies and permanent errors only; a transient error carrying invalid usage was still retried]*; the reply's action is not consumed; the log records `invalid_usage_fields`, never a rejected value.
    - **Same path, adjacent values:** the request ID and served model are kept only as short plain identifiers that do not contain the key (otherwise withheld, with `withheld_fields` logged), and the finish reason only from a known set (otherwise `unrecognized`).
    - The ledger validates counts itself too (`component_costs`), so no caller can settle a negative or fractional amount.
  - **P2-2, partial usage.** `CostLedger` charges each validated known count at its listed price, even above its ceiling, and holds each unknown count at its component ceiling. An entry with any unknown count never drops below the original reservation (`partial_usage` / `unknown_usage`). The summary reports `known_usd`, `unresolved_usd` and `estimated_total_usd` (replacing `conservative_total_usd`), with `unresolved_note`: held amounts are estimates from configured ceilings, not a guaranteed maximum charge, because the input ceiling rests on an unverified estimate. Known usage over a ceiling still ends the run `usage_over_ceiling`, so no further work happens. Codex's case now gives known $0.30 plus $0.0072 held for the missing output count.
  - **P2-3, configuration.** `NebiusConfig.validate()` runs on construction and again in `NebiusClient.__init__`, before any SDK object exists. It requires:
    - `https://` base URL and a non-empty model ID;
    - integer token ceilings of at least 1 and an integer template allowance of at least 0 (`bool` and floats rejected);
    - a finite positive timeout (`bool` and strings rejected);
    - finite non-negative `Decimal` prices (zero allowed).
    A configuration altered after construction is rejected by the client without a request.
  - **P3-1, observed execution.** `OriginalRun` has a required `executed` field, set from the executor's result.
    - Limitations, the comparison basis (new `ORIGINAL_NOT_EXECUTED_BASIS`, `DOCKER_PARTIAL_BASIS`) and the CLI line (`original: INCONCLUSIVE (not executed)`) are generated from execution status, not the selected runner.
    - The comparison now also reads the Docker runner's own record when no host-owned copy exists, and reports `executed` and `execution_status` for the original.
    - A refused candidate is reported as "0 of 1 candidates executed".
  - **P3-2, wording.** The module docstring, `input_bound`, `check_request`, SPEC §11, this task entry (inline corrections above) and the guide now call the pre-send figure an assumption-dependent **estimate**, not a proven bound. The stale guide paragraph is corrected. **Justifying a bound and choosing the ceilings stay open lead decisions; no live authorization is implied.**
  - **Tests (logs in git-ignored `runs/s3r/`):**
    - New `tests/unit/test_agent_slice3_repair.py`, 49 tests, each with valid controls:
      - nine invalid-usage kinds at the client;
      - valid, zero, one-missing and absent usage controls;
      - four invalid kinds through the controller (no action, no key or raw value in log or report, baseline outcome kept, amounts non-negative);
      - controller-level validation for a fixture client, and the ledger given raw counts directly;
      - withheld identifiers and an unrecognized finish reason;
      - three partial-usage cases, including a known component larger than the whole reservation;
      - eighteen invalid configurations, plus a post-construction bypass and valid controls;
      - no-Docker, refused-original and refused-candidate prose, and the CLI line.
    - **Red at the pre-repair commit:** a fresh `git archive 943f046` copy with this file added gave **36 failed, 13 passed** (`red.log`).
      - 33 failures are the defects themselves: `DID NOT RAISE` for invalid usage and configuration; an action consumed or REPORT on invalid usage; the key in the log; the old execution prose; `unknown_usage` instead of the known partial cost.
      - 3 are shape-only, because the fields are new: the `absent` control (`{}` vs explicit unknown counts) and two `KeyError: 'known_usd'`.
      - The 13 that passed are controls and configuration cases the old code already rejected.
    - **Codex's probe, copied fresh** (`runs/s3r/red/` before, `runs/s3r/green/` after):
      - before: Codex's results reproduced;
      - after: every invalid configuration rejected;
      - negative, fractional and key-echo usage end `invalid_usage` with no key in log or report and non-negative amounts;
      - partial usage: known $0.3000000 plus $0.0072000 held;
      - no-Docker and tamper bases say the original was not executed;
      - inert display still 227/0; network patches restored.
    - **Affected unit suites:** `uv run --locked pytest tests/unit/test_agent_controller.py tests/unit/test_agent_slice3.py tests/unit/test_agent_slice3_repair.py tests/unit/test_candidate_reevaluation.py tests/unit/test_agent_schemas.py tests/unit/test_candidates.py -q -p no:cacheprovider --basetemp=runs/s3r/final` -> **333 passed, 1 skipped (the existing symlink-permission skip in test_candidates.py)** (`tests-final.log`). Existing tests changed only for the new fields: `executed=True` on the two test-only host baselines, `estimated_total_usd`/`known_usd`/`unresolved_usd`, explicit unknown counts, and the new limitation wording.
    - **Docker integration: not run as tests; setup errors only.** `docker info` showed the Docker Desktop engine pipe absent (daemon not running). With `ATLAS_REQUIRE_DOCKER=1`, `test_agent_fixture_docker.py`, `test_cli.py` and `test_candidate_reevaluation_docker.py` gave **2 passed, 8 errors, 0 failures** (`docker.log`). All 8 errors are the module fixture's `isolated runner unavailable: Docker daemon unreachable`, a setup failure, not a test failure. No container ran; Docker was not started or reconfigured. Real-Docker behaviour after this repair is therefore **not verified**. The report change touches the Docker paths, so these tests should be rerun once the daemon is available.
    - Ruff check and format clean. Not rerun: the full suite, the Docker contract suite and the mutation check. No evaluator, runner, check, schema or diff-parser code changed; `report.py` changed only its prose and basis selection, and its slice 1 tests are in the run above.
    - **Preservation:** all 70,230 paths in Codex's `runs/s3v/before.json` inventory (`runs/`, excluding `runs/s3v/` and `.env` files, plus the root guide) are unchanged, with none missing (`runs/s3r/preservation.json`, checked read-only). The newest file under `runs/s3v/` predates this repair's first write. The root guide hash is `b08d74c4…`.
  - **Still open before slice 4 (unchanged):** the per-call ceilings (per-stage $0.0510 vs. uniform $0.0648), a justified prompt-token bound and its alignment with `MAX_PROMPT_CHARS` (96,000), Docker availability, and separate explicit live authorization.
- **CODEX VERIFICATION OF REPAIR PASS 1 (`runs/s3w/review.md`, target `756bb57`, parent `5aad204`): three P2 findings remain; slice 3 not yet fully verified offline.**
  - **Codex's results:**
    - focused units 333 passed, 1 skipped;
    - Docker engine ready (linux 29.8.2) and the focused Docker integrations 10 passed, which closes the builder's daemon gap;
    - the copied original probe and a new edge probe were run;
    - preservation: 83,523 entries, no changes.
  - **Dispositions:** P2-1 partly fixed; P2-2 fixed at ordinary magnitudes but not at all admitted values; P2-3 field validation fixed, with computed-arithmetic defects remaining; P3-1 and P3-2 verified fixed. Codex also separated the three shape-only red failures from the behavioural evidence, and noted that the records' blanket claims overstated pass 1 (corrected inline above).
  - **P2, transient invalid usage** (`controller.py:574`): a `TransientModelError` carrying invalid usage was retried, and the next reply's action ran (REPORT after two requests).
  - **P2, echoed model ID** (`controller.py:625`): `reply.model_id` was copied raw into the attempt record and logged on the mislabelled rejection (the synthetic marker reached the log).
  - **P2, money arithmetic** (`budget.py:207`):
    - with 10**40 known input tokens, `(known + held) - known` rounded the $0.0072 hold to 0;
    - a finite price `1e999999` was accepted, its reservation overflowed (or became `Infinity` with traps off);
    - a settlement under a reduced ambient Emax became `Infinity` and was marked `settled`.
- **SLICE 3 REPAIR PASS 2 RESULT (2026-10-16): implemented and self-tested; awaiting Codex verification; T-06 not accepted.** No provider request, no real `.env` read, no hosting change; slice 4 not started; token ceilings and prompt-bound enforcement remain separate open decisions.
  - **1. Invalid usage ends the run before any retry decision** (`controller._model_turn`). For any client's error, the order is:
    1. validate its usage (`sanitize_usage`, plus the error's own `invalid_fields` through `error_usage_fields`);
    2. settle the ledger, which keeps the valid known component and holds the rest;
    3. if anything was invalid, log only fixed codes and field names and end `ERROR invalid_usage`, before the transient/retry branch.

    A permanent error with invalid usage is now reported as `invalid_usage` (it was `model_error`). Only an explicit `dispatched is False` releases a reservation (`None`, `0` or text no longer do).
  - **2. Identifiers checked on every logging path.**
    - The reply's model ID is never logged: the attempt records the configured ID only on a match, plus `reply_identity` `match`/`mismatch`. `reply_live` is recorded only if it is the expected boolean.
    - The request ID and served model are logged only when the client set `identifiers_checked` (the production client, after comparing them with its key, which the controller never sees) and they are plain identifiers; otherwise they are withheld and named in `withheld_fields`.
    - Error codes are recorded and reported only in fixed shapes (`safe_error_code`), otherwise `unrecognized_error`. The production client's SDK-error code is now the fixed `client_error`.
    - The finish reason comes only from the known set, and the incomplete-reply message uses the checked value.
  - **3. Exact money, independent of the ambient `decimal` context** (new `agent/money.py`).
    - Every multiplication, sum, comparison and text conversion runs in a private context: 400 digits, `ROUND_HALF_EVEN`, with `Inexact`, `Rounded`, `Overflow`, `Underflow`, `InvalidOperation`, `DivisionByZero` and `Clamped` all trapped. Any signal becomes `MoneyError`; nothing is ever rounded or infinite.
    - **Supported range (documented choice, checked before any client exists):**
      - token counts, configured or reported: integers from 0 to 10**100 (ceilings from 1);
      - prices: finite, non-negative `Decimal` (negative zero rejected), at most 10**100 USD per token and at most 30 decimal places;
      - timeout: positive and at most 86,400 s, compared before any float conversion.

      In this range every amount has at most 231 significant digits, so results are exact. A reported count above 10**100 is invalid usage: the run ends, and the count is not silently clamped. Known incurred costs are never capped.
    - The unknown components' hold is computed directly. The reservation floor adds only the shortfall while usage is unresolved, so a small hold survives a huge known cost.
    - `CostLedger` checks its ceiling at construction, before any request (an unrepresentable ceiling raises and nothing runs).
    - An amount that cannot be represented marks the entry `unrepresentable` (no figure, never `settled`), withholds the summary totals and ends the run `ERROR cost_unrepresentable` before any retry or action.
    - Complete valid usage still settles at the actual cost, below the reservation (for example $0.0000075).
  - **Tests (logs in git-ignored `runs/s3x/`):**
    - **New `tests/unit/test_agent_slice3_repair2.py`, 37 tests, with valid controls,** using synthetic markers and in-process fakes or the production client over a mock transport:
      - transient, permanent and priced invalid-usage errors;
      - mismatched model IDs (key, key in a path, escape, bidi);
      - a non-boolean live label, unchecked identifiers and fixed error codes;
      - the huge-known/small-held hold, directly and in a live run;
      - accounting under five adversarial ambient contexts (precision 1, 2 and 3, rounding up, Emax 9 with traps off, every signal trapped), compared with the default context;
      - out-of-range configurations (including `1e999999` with and without ambient overflow traps) and the range boundaries (`1e100` price, 10**100 counts, one-day timeout, zero prices);
      - an out-of-range reported count;
      - unrepresentable amounts and ceilings;
      - the explicit-release rule.
    - **Red at the parent:** a fresh `git archive 756bb57` copy with this file added gave **34 failed, 3 passed** (`red.log`; the 3 passes are controls). Classified by first failure:
      - **25 behavioural:**
        - REPORT after a retry, or `model_error` / `transport_error (after one retry)`, instead of `invalid_usage`;
        - the raw model ID, live label, request ID or served model in the attempt record;
        - raw error codes;
        - a lost hold: `Decimal('0')` instead of `0.0072000`, or instead of `1E+70` at the range boundary;
        - ambient-context results differing from the default, including `Infinity` and a `decimal.Rounded` exception;
        - `1e999999` accepted, in three cases;
        - an infinite amount consumed (the run continued to a second request);
        - an infinite ceiling not rejected;
        - `None` and `0` releasing a reservation.
      - **7 new bounds:** values the old code accepted and the new range rejects (`1e101` and `1e-31` prices, negative zero, `10**100 + 1` ceilings and allowance, a 86,401 s timeout, a reported count above 10**100).
      - **1 different error type:** a 10**400 timeout raised `OverflowError` instead of `ValueError`.
      - **1 shape-only:** `KeyError: 'reply_identity'`, a new field.
    - **Codex's probes, fresh copies** (`runs/s3x/green/`; `probe.py`, `edge_probe.py` and `finite_controls.py` byte-identical to `runs/s3w/`):
      - `probe.py` and `finite_controls.py` exit 0 (zero and `1e100` prices finite).
      - The unchanged `edge_probe.py` now stops with `ValueError: price_input_per_token must be at most 1e100 USD per token`. That is the intended rejection of its `1e999999` configuration, raised outside the probe's `try`.
      - A labelled adapted copy (`edge_probe_adapted.py`, made by `adapt_edge.py`; it only wraps that construction) exits 0 with these results:
        - transient and permanent invalid usage end `ERROR invalid_usage` after 1 call;
        - the echoed model ID is rejected with no marker in log or report;
        - both overflow configurations are rejected before any client;
        - reduced-Emax settlements are exact (`10000000000`) with traps on or off;
        - 10**40 known input keeps the `0.0072000` hold;
        - complete usage settles at `0.0000075`;
        - small partial usage gives `0.0672000`;
        - fully unknown usage holds `0.0672000`;
        - network patches are restored.
    - **Affected unit suites:** `uv run --locked pytest tests/unit/test_agent_controller.py tests/unit/test_agent_slice3.py tests/unit/test_agent_slice3_repair.py tests/unit/test_agent_slice3_repair2.py tests/unit/test_candidate_reevaluation.py tests/unit/test_agent_schemas.py tests/unit/test_candidates.py -q -p no:cacheprovider --basetemp=runs/s3x/final -rs` -> **370 passed, 1 skipped (the existing symlink-permission skip in test_candidates.py)** (`tests-final.log`). One existing pass 1 assertion was corrected: it checked that `-5` was absent from the whole log, which a random run-directory hash can contain; it now checks the recorded usage value.
    - **Docker:** rerun because the model-turn loop these integrations pass through changed. `docker info` showed linux 29.8.2 (`docker-info.log`). With `ATLAS_REQUIRE_DOCKER=1`, `test_agent_fixture_docker.py`, `test_cli.py` and `test_candidate_reevaluation_docker.py` gave **10 passed** (`docker.log`).
    - Ruff check and format clean. Not rerun: the full suite, the Docker contract suite and the mutation check. No evaluator, runner, check, schema, diff-parser or report code changed.
    - **Preservation:** all 83,523 paths in Codex's `runs/s3w/before.json` inventory are unchanged, with none missing (`runs/s3x/preservation.json`, read-only check). The newest file under `runs/s3w/` (20:04:48) predates this pass's first write (20:23). The root guide hash is `b08d74c4…`. Pass-local scratch test directories `runs/s3x-pre`, `-pre2`, `-new` and `-new2` are new and contain only test output.

- **CODEX VERIFICATION OF REPAIR PASS 2 (`runs/s3y/review.md`, target `5e63fc4`, parent `756bb57`): slice 3 verified within its documented offline scope; no remaining P1/P2 blocker or new demonstrated defect.**
  - All five original findings are now verified fixed within the supported contracts (P2-1 usage and metadata, P2-2 partial accounting, P2-3 configuration and derived arithmetic, P3-1 execution prose, P3-2 estimate wording), including the three defects left by repair pass 1.
  - **Codex's independent results:**
    - focused units **370 passed, 1 skipped** (the existing symlink-permission skip);
    - Docker engine checked first (linux 29.8.2), then the focused Docker integrations **10 passed**;
    - the copied original probe, the adapted edge probe and the finite controls exit 0. The unchanged edge probe exits 1 at the now-rejected `1e999999` configuration, which is expected;
    - an in-memory sensitivity check (`money.exact` replaced by the ambient context) made the precision-1 regression fail, so the regression detects loss of context isolation;
    - the new real-Docker artifacts (original VIOLATION_FOUND, candidate NO_VIOLATION_FOUND, executions completed, removal confirmed, hashes matching) were inspected;
    - preservation: 98,632 entries, no changes.
  - **Codex's qualifications:**
    - this is development-fixture and mocked-transport evidence, not real-provider or independent benchmark evidence;
    - the builder's parent-commit red run was inspected, not rerun, and its last nine failures (new bounds, an exception type and a new field) are not evidence of old behavioural defects;
    - the identifier checks do not protect against a malicious trusted client implementation or secret-bearing operator configuration;
    - the 10**100 / 1e100 limits are representational, not operational token caps or spending authorization.
  - **Slice 4 is still not authorized.** It needs explicit per-call token-ceiling and cost-authorization decisions, a justified prompt-token bound (or another safe enforcement design) aligned with `MAX_PROMPT_CHARS`, and separate explicit live authorization. **T-06 is not accepted.**
- **SLICE 4 PROPOSAL (2026-10-16; builder's proposal for the lead; nothing decided, enabled or sent).** *[Gate 2, 2026-10-16: the ceilings, estimate cap, $0.51 authorization, pre-run check and entry-point design are now **decided**; see DECISIONS.md "T-06 slice 4 live-run decisions (lead)". The 60 s timeout remains proposed. Nothing live is authorized.]* One live run on the s01 development fixture.
  - **Per-call ceilings (proposed): uniform for all six attempts.** The controller's turns are uniform (each reply chooses one action), so the per-stage table ($0.0510) does not map onto them.
    - **Output:** `max_completion_tokens = 8,000`, sent with every request. The Nebius API reference documents it as an upper bound on generated tokens, reasoning included (STATUS.md). This is provider-enforced and documented, not verified by us.
    - **Input:** an *estimated* ceiling `max_input_tokens = 12,000`, with the estimate = UTF-8 bytes + `template_overhead_tokens = 16` per message.
  - **Prompt-size alignment (proposed code change for slice 4, to be reviewed):**
    - Replace `MAX_PROMPT_CHARS = 96,000` with a budget derived from the input ceiling: 12,000 − 489 (system prompt bytes) − 2 × 16 = **11,479 bytes** for the user message.
    - The user message is `json.dumps` output with ASCII escaping, so its characters equal its bytes. The existing history truncation then keeps every prompt inside the estimate, and a base context that cannot fit is refused before sending (not counted).
    - Lower `MAX_TOOL_RESULT_CHARS` from 16,000 to 6,000 so one file read fits (s01's `evaluate.py` is 1,059 bytes). *[As implemented in the slice 4 controls below: derived, not fixed: half the user-message budget, 5,739 at the proposed ceiling, for live runs only.]*
    - Measured s01 prompt estimates (slice 3): about 4,100 to 6,100 per turn over three turns.
  - **Why the input figure stays an estimate, not a guarantee.**
    - Every prompt byte is ASCII (the system prompt is ASCII; JSON escaping makes the rest ASCII). Byte-level BPE and SentencePiece-with-byte-fallback tokenizers produce at most one token per ASCII byte, plus template and special tokens.
    - But the provider lists this model's tokenizer only as "Other" (model metadata, 2026-10-14), and the 16-token template allowance is unverified.
    - Sample evidence fits the estimate but proves nothing: the two smoke calls used 32 prompt tokens for a 72-byte message and 47 for a 124-byte one, both well below bytes + 16.
    - After each reply, reported `prompt_tokens` above 12,000 ends the run (`usage_over_ceiling`). That detects a failure afterwards; it does not prevent it.
  - **Limits and what enforces them:**

    | Limit | Enforced by | Status |
    | --- | --- | --- |
    | At most 6 requests per run (retries included), and one run | ATLAS code | Implemented and verified offline |
    | Prompt bytes within the 11,479-byte budget | ATLAS code | Proposed change (above) |
    | Output ≤ 8,000 tokens per request | Provider (`max_completion_tokens`) | Documented, not verified |
    | Input + output ≤ 262,144 tokens per request | Provider (`context_length`, model metadata 2026-10-14) | Documented, not verified |
    | Input ≤ 12,000 tokens per request | ATLAS estimate | **Not guaranteed** |
    | Prices $0.30 / $0.90 per 1M tokens | Provider listing (2026-10-14) | Re-check before the run |

  - **Expenditure at listed prices:**
    - **Expected for s01:** about 3 requests of roughly 2,000–6,000 input and 1,000–3,000 output tokens, about **$0.005–$0.014** (estimate).
    - **Estimated maximum, if the input estimate holds:** 6 × (12,000 × $0.30 + 8,000 × $0.90) / 1M = 6 × $0.0108 = **$0.0648**.
    - **Provider-enforced maximum, if the input estimate failed entirely** (relying only on the documented context length and output bound): the worst single request is 254,144 input + 8,000 output tokens, which costs $0.0762432 + $0.0072 = $0.0834432. Six of them total **$0.5006592**.
  - **Proposed authorization (the lead's decision):**
    - **one live run, with a maximum authorized expenditure of $0.51** (the provider-enforced maximum, rounded up);
    - expected spend about $0.005–$0.014; billing unchanged;
    - the owner-observed balance is $50.00, so $0.51 is about 1% of it;
    - credit expiry and promotional-use eligibility stay unknown.
  - **Proposed run-level stop (code change):** before each dispatch, if the ledger's known plus unresolved amount plus the next request's ceiling would exceed **$0.0648**, end the run `BUDGET_EXHAUSTED` without sending. With uniform ceilings this never blocks a normal run.
  - **Preconditions for the run:**
    - a free authenticated `GET /models`, needing its own approval, run immediately before. Abort if the model is absent or its listed prices or context length differ from the configuration;
    - the key read from `.env` only by `load_api_key`;
    - Docker running;
    - an explicit live entry point (proposed: the CLI refuses unless `ATLAS_MODEL_MODE=live` and `--authorize-spend-usd 0.51` match the configured cap);
    - typed approvals for the original and each candidate, as now.
  - **Alternative (not recommended now):** count input exactly with the model's published tokenizer and chat template, checked against reported usage after the first call. This would need a new dependency, a download and confirmation that the template matches the provider's. The provider-enforced maximum of $0.51 is already small.
  - **Decisions needed from the lead:**
    1. uniform 12,000 / 8,000 ceilings (instead of the per-stage table);
    2. the prompt-size alignment and run-level stop as slice 4 code changes;
    3. the $0.51 maximum authorized expenditure for one run;
    4. the pre-run `GET /models` check;
    5. separate explicit go-ahead for the live request itself.
- **OWNER-OBSERVED NON-LIVE DEMONSTRATION (2026-10-16; owner-reported, builder-checked read-only).**
  - The owner ran the fixture-mode CLI by hand on the s01 development fixture with the existing three fixture replies (`runs/demo-s01/`, git-ignored), typing both approvals.
  - Run `runs/demo-s01/runs/agent-s01_faulty-6face8361824`: `REPORT`, labelled NON-LIVE (`fixture:s01-demo`).
  - The original ran in Docker: `VIOLATION_FOUND`.
  - Candidate `81f691409a67`: execution completed, `NO_VIOLATION_FOUND`. The executed bytes matched the approved code hash, container removal was confirmed, elapsed 1.891 s.
  - Four FAILs (`split.no_group_overlap`, `split.sampling_unit_disjoint`, `split.repeated_measures_rule`, `fit.state_dependencies_within_fold_train`) became PASS; the five existing PASSes stayed PASS.
  - The builder's read-only check of the report and log agrees (two `confirmed` approvals). Not rerun.
  - This shows the fixture pipeline working end to end, not a real model's behaviour or independent benchmark evidence.
- **SLICE 4 CONTROLS RESULT (2026-10-16): prompt budget and spending controls prepared offline; implemented and self-tested; awaiting Codex review. No live request, provider metadata request or spending; the token ceilings and amounts remain PROPOSED; no live entry point was added (the CLI still refuses live mode).**
  - **Proposed values are labelled, never defaults.** `budget.PROPOSED_SLICE4` records the proposal (12,000 / 8,000 / 16 tokens, context length 262,144, listed prices, estimate cap $0.0648, authorized $0.51). Nothing reads it at run time; a test checks that the controller, client and model-client modules do not reference it and that `run_agent`'s `spend` has no default.
  - **Spending limits are required for a live run** (`budget.SpendLimits(authorized_usd, estimate_cap_usd)`; exact, finite, non-negative amounts in the money range; the cap may not exceed the authorization). `run_agent` refuses a live client without them (`LiveModeUnavailable`), in addition to `live_authorized=True`.
  - **Checked before anything runs** (`SpendLimits.check`, no run directory, no Docker, no request):
    - the provider-enforced worst case must not exceed `authorized_usd`. That is `max_attempts` × `NebiusClient.worst_case_request_cost()`, the costlier of all-input or input-plus-maximum-output within `context_length_tokens`, at listed prices;
    - the estimate cap must cover at least one request's ceiling.

    Otherwise `SpendRefused`. The report's `spending` section labels each figure: the authorization; the cap, "not a guaranteed charge"; and the worst case, which relies on provider enforcement "ATLAS has not verified".
  - **Per-request stop:** before each attempt is reserved, including a retry, the ledger's committed amount (known plus held) plus the next request's ceiling must not exceed `estimate_cap_usd`. Otherwise the run ends `BUDGET_EXHAUSTED` (`spend_cap`) without sending, and the refusal is not an attempt.
  - **Prompt budget (live runs):**
    - `NebiusClient.user_message_budget(SYSTEM_PROMPT)` = input ceiling − (system prompt bytes + allowance) − allowance, which is 11,479 bytes at the proposed values.
    - History truncation measures the exact UTF-8 bytes of the user message against it, and a single tool result is limited to half of it (5,739).
    - A base context that cannot fit is still refused before sending.
    - Fixture runs keep `MAX_PROMPT_CHARS` (96,000) and `MAX_TOOL_RESULT_CHARS` (16,000); the report's `prompt_budget` section shows which applied.
  - **Configuration:** `NebiusConfig` has a new required `context_length_tokens` field (2 to 10**100). Input plus output ceilings must fit within it.
  - **Tests (logs in git-ignored `runs/s4/`):**
    - **New `tests/unit/test_agent_slice4_controls.py`, 24 tests (`slice4-file.log`: 24 passed):**
      - the proposal's arithmetic: $0.0108 per request, $0.0648 cap, $0.0834432 and $0.5006592 worst case, 11,479 bytes;
      - proposed values never used as defaults;
      - live prompts staying within the estimate as history grows (six requests, history truncated, every estimate ≤ 12,000);
      - fixture limits unchanged;
      - a base context that cannot fit;
      - the budget formula;
      - refusal without limits, and both insufficient-limit refusals with a tripwire original that never runs and no run directory;
      - the proposed limits accepted and reported;
      - six invalid `SpendLimits`;
      - the cap stopping after two unknown-usage requests, and blocking a retry;
      - small known usage not tripping the cap (control);
      - the context-length rule;
      - the worst case choosing the costlier token kind.
    - **Red at the parent** (fresh `git archive 5932b6a` copy plus this file; `red.log`): **22 failed, 2 passed**. The 2 passes are controls.
      - **4 behavioural:**
        - growing history was refused mid-run (`input_over_ceiling`);
        - a live run without limits was accepted;
        - with unknown usage the parent sent 6 requests where the cap now stops after 2 (`cap_probe.py`: `cap-parent.log` vs `cap-head.log`);
        - after a timeout the parent sent the retry (2 requests) where the cap now blocks it (1).
      - **18 new-interface failures:** missing `worst_case_request_cost`, `user_message_budget`, `SpendLimits`, the `spend` parameter, the `prompt_budget` / `spending` report fields and the `context_length_tokens` field.
    - **Existing tests adapted** for the new requirements, with behaviour unchanged:
      - the slice 3 live-run helpers pass a generous `SpendLimits` ($1000 / $1000) so that they never bind;
      - the test configuration gains `context_length_tokens = 262,144`;
      - the priced fake gains a worst-case method;
      - the range-boundary test now uses ceilings of 10**100 / 2 each within a 10**100 context (hold 5e69 instead of 1e70).
    - **Affected unit suites** (controller, slice 3 and both repair files, the slice 4 file, candidate re-evaluation, schemas, candidates; `tests-final.log`): **394 passed, 1 skipped** (the existing symlink-permission skip). That run collected the slice 4 file before a test-only compatibility edit for the red run; the final file was rerun separately (24 passed).
    - **Docker:** daemon checked first (linux 29.8.2); the focused integrations `test_agent_fixture_docker.py`, `test_cli.py` and `test_candidate_reevaluation_docker.py` gave **10 passed** (`docker.log`). They were rerun because the controller's prompt path changed.
    - Ruff check and format clean. Not rerun: the full suite, the Docker contract suite and the mutation check. No evaluator, runner, check, schema, diff-parser or report-builder code changed.
    - **Preservation:** all 98,632 paths in Codex's `runs/s3y/before.json` inventory are unchanged, with none missing (`runs/s4/preservation.json`, read-only check). The owner's demo run was only read. The root guide hash is `b08d74c4…`. New output is confined to `runs/s4/`, `runs/s4-new`, `runs/s4-new2`, `runs/s4-pre`, `runs/demo-rehearsal-20261016/` and `runs/demo-s01/` (script and viewer).
  - **Still not decided or authorized:**
    - the ceiling values, the estimate cap and the $0.51 authorization (all proposed);
    - the pre-run `GET /models` check;
    - a live entry point;
    - the live request itself.

    The input figure remains an estimate; the worst case relies on provider enforcement that has not been verified.
- **SLICE STATUS (reconciled 2026-10-17; Gate 3 PASS at `f327565`):**

  | Slice | Commit | State | Evidence |
  | --- | --- | --- | --- |
  | 1. Approved candidate → Docker → trusted re-evaluation | `1d58b20` | **Verified** by Codex within scope | `runs/r6w/review.md` |
  | 2. Offline fixture controller | `69042a1` | **Verified** by Codex within scope | `runs/r6x/review.md` |
  | 3. Docker baseline, CLI approval, offline Nebius client | `5e63fc4` | **Verified** by Codex within its offline scope | `runs/s3y/review.md`: 370 passed, 1 skipped; Docker 10 passed |
  | 4a. Prompt budget and spending controls (offline) | `96f6fc6`, repaired at `8c79e5a` | **Verified by Codex within its offline scope (Gate 1 PASS)** | `runs/g1-1016/review.md` (FAIL); `runs/g1v3/review.md` (PASS) |
  | 4b. Entry point, preflight and one live run | `f327565` (offline implementation) | **Entry point and preflight verified by Codex (Gate 3 PASS)**; live run **not started**, awaiting the lead's separate explicit go-ahead for ONE pre-run call and ONE live run (at most $0.51) | `runs/g3w/review.md` (FAIL); `runs/g3x/review.md` (FAIL); `runs/g3y/review.md` (PASS); "NEXT CARD: SLICE 4" below |

- **FULL-SUITE VERIFICATION AT `96f6fc6` (2026-10-16, builder):** after `docker info` → `linux 29.8.2`, PowerShell `$env:ATLAS_REQUIRE_DOCKER = '1'; uv run --locked pytest tests -q -p no:cacheprovider --basetemp=runs/status-20261016/t -rs` gave **965 passed, 1 skipped** (the existing symlink-permission skip) in 743.88 s, exit 0. `ruff check` and `ruff format --check` are clean. Logs: `runs/status-20261016/`. This includes the Docker runner contract suite and all T-06 integration tests. It is the builder's run, not an independent verification.

- **GATE 1 REVIEW (`runs/g1-1016/review.md`, Codex, 2026-10-16, on an archive of `96f6fc6`): FAIL, two P2 prompt-truncation defects.** Not T-06 acceptance; no inference, metadata request or spending authorized.
  - **P2-1 (controller `_messages`):** after evicting an older history item, the 27-byte `history_truncated` marker was added without re-measuring. A fitting prompt then exceeded the budget, and a valid run ended `ERROR input_over_ceiling`. It failed closed; nothing over budget was sent. Reproduced at input estimate 4,824 (final 4,320 bytes vs a 4,303 budget) and at 12,000 (11,469 → 11,496 vs 11,479).
  - **P2-2 (controller `_record_tool`):** the truncated result was a character slice of already-serialized JSON, escaped again when embedded. A 5,739-character quote-heavy read became 11,450 bytes, and `_messages` then dropped the newest result entirely.
  - **Codex's other results:**
    - focused units 393 passed, 1 failed (`WinError 5` accessing Docker in the sandbox; the targeted escalated retry passed), 1 skipped;
    - Docker integrations 10 passed;
    - independent probes confirmed the spending and worst-case arithmetic (including a 495-case Fraction oracle) and found only the two defects.
  - **Codex's environment note:** NumPy 2.4.6 installed "versus lockfile 2.5.4". *[Builder, 2026-10-16: `uv.lock` has two NumPy entries, 2.4.6 for Python < 3.12 and 2.5.4 for Python ≥ 3.12. The environment (Python 3.11.17) is lock-matched: `uv sync --locked --dry-run` → "Would make no changes".]*
- **GATE 1 REPAIR PASS 1 RESULT (2026-10-16): self-tested; awaiting independent Codex verification. Gate 1 is not passed; T-06 not accepted.** Repair commit **`8c79e5a`** (`8c79e5afffbc4bd9db7969a955a21f26d96c2988`), parent `d929863`. *[Verified by Codex in re-verification attempt 3, below.]* Only `src/atlas/agent/controller.py` changed in production code; spending, approval, retry, fixture-mode and fail-closed behaviour are unchanged. No provider request, credential, spending or live execution.
  - **P2-1:** `_fitting_history` builds every candidate as the exact user message that would be sent (`_user_message`), including the marker whenever older results are left out. A prompt that is accepted is therefore never enlarged afterwards, and eviction continues until it fits. If even the base context plus the marker does not fit, the prompt is refused before sending (fail closed, unchanged).
  - **P2-2:**
    - `_record_tool` bounds a too-large result as it is embedded: `_bounded_envelope` gives the longest prefix whose envelope `{"text", "truncated": true}` serializes, escaping included, to at most `tool_result_chars` UTF-8 bytes. Small results are stored unchanged.
    - When the newest result still does not fit beside the base context, `_messages` keeps the longest prefix that does (`_largest_fitting_prefix`), provided at least `MIN_TOOL_PREFIX_CHARS` (200) characters of it fit. Older results are evicted whole.
  - **Tests (logs in git-ignored `runs/g1r/`):**
    - **New `tests/unit/test_agent_slice4_prompt.py`, 80 tests:**
      - Codex's end-to-end marker reproduction;
      - marker boundaries at the 12,000 estimate with 0/1/26/27/28/40 spare bytes, plus an exact fit with no marker;
      - large reads of plain, quote, backslash, quote-backslash, accented, emoji, control and mixed content, each checked for the embedded envelope ≤ the limit, true prefix, kept in the prompt, and whole prompt within the estimate;
      - Codex's quote-heavy `_read` shape;
      - the newest result shortened rather than dropped (four content kinds);
      - controls: no usable space, several results, small result unchanged;
      - 56 maximality and limit checks of the bounding helper.
    - **Red at `96f6fc6`** (fresh `git archive` plus this file, `red.log`): **73 failed, 7 passed.**
      - 17 behavioural failures: `input_over_ceiling` refusals, embedded sizes of 5,777 to 11,451 bytes against 5,739, and the newest result dropped.
      - 56 new-interface failures (`_bounded_envelope` absent).
      - The 7 passes are controls.
    - **Codex's three probes, byte-identical fresh copies** (`runs/g1r/codex/`, helpers from a `git archive HEAD` copy): **39 passed** (previously 4 failed).
      - The marker case gives REPORT, 3 requests, final 4,303 bytes = budget.
      - At 12,000 the final prompt is 8,430 bytes with the newest result kept.
      - The quote-heavy envelope is 5,738 ≤ 5,739 bytes, with the newest result kept.
    - **Affected unit suites** (controller, slice 3 and both repairs, both slice 4 files, candidate re-evaluation, schemas, candidates; `unit.log`): **474 passed, 1 skipped** (the existing symlink skip), exit 0.
    - **Docker** (`docker info` → linux 29.8.2; `ATLAS_REQUIRE_DOCKER=1`): the three focused integration files **10 passed** (`docker.log`).
    - Ruff check and format clean.
    - Environment: Python 3.11.17, NumPy 2.4.6, openai 3.31.0, httpx2 2.13.1, pydantic 2.14.1, pandas 3.0.6, scikit-learn 1.9.1, pytest 9.1.1, all lock-matched (`environment.txt`).
    - No environment failures in these runs.
  - **Limitations:**
    - the input figure is still an estimate (unverified tokenizer and template);
    - a base context that cannot fit with the marker is refused, not trimmed;
    - an evicted older result is dropped whole;
    - the 200-character minimum prefix is a builder choice;
    - the full suite and mutation check were not rerun.
  - **Values:** Codex's review refers to "the user's decided values". DECISIONS.md has no slice 4 decision record yet, so these records keep them labelled proposed until the lead records them.
- **CODEX RE-VERIFICATION ATTEMPT 1 (`runs/g1v/review.md`): halted at Step 0; not a review result.** The preservation inventory instruction conflicted with the `.env` constraint: the inventory reached a test-fixture `.env` at `runs/g1-1016/unit-temp/test_snapshot_ignores_extra_pr0/project/.env`, and Codex stopped without reading or hashing it. No checks were run.
- **CODEX RE-VERIFICATION ATTEMPT 2 (`runs/g1v2/review.md`): halted at Step 0; not a review result.** Recursive `os.scandir` enumeration failed with `WinError 5` on `runs/g1-1016/docker-temp`, and on `runs/g1-1016/boundary-temp` in an escalated read-only retry. No checks were run.
  - **Builder read-only listing (2026-10-16):** `Get-ChildItem runs -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue` showed 17 junctions. All were `test_input_behind_a_directory_0/project/data`, left by the junction test in `tests/unit/test_candidates.py`, and none were under `runs/g1-1016/`.
  - *[Corrected from attempt 3:]* Codex's inventory found one junction under `runs/g1-1016/` (`runs/g1-1016/unit-temp/test_input_behind_a_directory_0/project/data`), which the builder's listing did not show; that listing suppressed errors, so it was not complete.
  - Neither listing shows a junction at the failing paths (`docker-temp`, `boundary-temp`). **The cause of the `WinError 5` is not established.**
- **CODEX VERIFICATION OF GATE 1 REPAIR PASS 1 (attempt 3, `runs/g1v3/review.md`, at `8c79e5a`): GATE 1 PASS.**
  - **Identity:** HEAD `8c79e5a`, parent `d929863`; the repair's code scope is exactly `controller.py` and `test_agent_slice4_prompt.py`.
  - **P2-1** (marker escape) and **P2-2** (tool-result escaping) are independently verified closed. No new P1 or P2 was demonstrated, and Codex reported no P3.
  - **Below 200 useful prefix characters**, the result is evicted with `history_truncated: true` (or refused before dispatch when even the marked base context cannot fit); no silent drop was observed.
  - **Older results** are evicted whole, with the omission marked.
  - **Fixture mode:** limits unchanged (96,000 / 16,000) and small results unchanged. Large-result truncation now uses the repaired algorithm in both modes, so legacy truncated payloads are not claimed byte-for-byte unchanged.
  - **Spending, retry and approval paths:** an AST comparison found only `_Run._messages` and `_Run._record_tool` changed.
  - **Results:**
    - `tests/unit/test_agent_slice4_prompt.py` **80 passed**;
    - `tests/unit/test_agent_slice4_controls.py` **24 passed**;
    - independent probes **51 passed** (`runs/g1v3/probes/results.json`);
    - all three scratch mutations detected (marker left out of the measurement: 4 failures; envelope measured before final escaping: 24; newest result evicted instead of shortened: 10);
    - ruff passed.

    Codex's first prompt-suite invocation hit a missing temporary directory (`WinError 3`, 56 passed with 24 setup errors), and its first probe harness had three incorrect assumptions. Both were corrected and are retained; neither is a product defect.
  - **Not run** (outside this gate's scope): Docker integrations, the full suite and the mutation check. The builder figures (474, 39, 73/7) were inspected as claims, not rerun.
  - **Preservation (partial evidence, NOT "all evidence preserved"):**
    - 18,008 files are unchanged before and after;
    - 3 `.env*` paths were excluded by name;
    - 1 reparse point was skipped without traversal;
    - **117 inaccessible paths are documented and not inventoried.**

    The builder's listing found 17 junctions where Codex recorded 1, most likely because the others lie inside the inaccessible subtrees (not confirmed).
  - **Safety:** no network call, `.env*` read or hash, spend, permission change, elevated retry, reparse-point traversal or tracked-file change.
  - Codex also corrected its earlier NumPy note: 2.4.6 is the correct lock variant for Python 3.11.
  - **Scope:** this verifies only the slice 4a controls repair. It is not T-06 acceptance and authorizes nothing live. All ceilings and amounts remain **PROPOSED** (no DECISIONS.md record).
- **FOLLOW-UPS (low priority, not scheduled):**
  - Junction teardown: the junction test in `tests/unit/test_candidates.py` leaves junctions in pytest base-temp directories under `runs/`, and 117 `runs/` paths were unreadable from Codex's sandbox in that review. Both reduce future preservation coverage. No action in this task.
  - `0E+200` rejection (`money.py`; deferred P3): an unsigned zero with a large exponent is rejected; fails closed. Accepted as a known limitation in DECISIONS.md "Gate 3 re-verification dispositions (lead, 2026-10-17)".
- **GATE 3 IMPLEMENTATION RESULT (2026-10-16): the live entry point and pre-run model check, offline. Awaiting Codex Gate 3 review; no pre-run call or live run executed or authorized; no network request, `.env` read or spending.**
  - **Files:**
    - `src/atlas/cli.py`: `--live`, `--authorize-spend-usd`, `_live`, exit codes;
    - new `src/atlas/agent/preflight.py`;
    - `src/atlas/agent/budget.py`: `DECIDED_SLICE4` replaces `PROPOSED_SLICE4`, and `DECIDED_SLICE4_PROPOSED = ("timeout_s",)`;
    - `src/atlas/agent/nebius.py`: the cost methods moved onto `NebiusConfig` so that limits can be checked before any client or key exists; the client delegates;
    - `src/atlas/agent/controller.py`: an optional `preflight` evidence parameter, reported as given;
    - new `scripts/live_preflight.py`;
    - new `tests/unit/test_agent_slice4_live_entry.py` and `tests/fixtures/nebius_models_verbose.json` (synthetic, with the shape of the archived listing);
    - `tests/unit/test_agent_slice4_controls.py` (constant renamed; the test client keeps its synthetic URL and model).
  - **Decided configuration:** one constant, `budget.DECIDED_SLICE4` (citing DECISIONS.md), with `timeout_s` 60 labelled proposed. Its `base_url` is the playbook's documented runtime API base, because `.env` and `.env.example` may not be read. Only `atlas.cli` (the live path) and `scripts/live_preflight.py` read it. A test checks that `controller.py`, `nebius.py`, `client.py` and `preflight.py` do not mention it, and that `run_agent`'s `spend` and `preflight` default to None.
  - **Refusal order (exit 2, before any run directory, Docker call, key read, client construction or network access):**
    1. `--live` (or `--authorize-spend-usd`) without `--mode agent`; `--live` with `--fixture-script`; `--authorize-spend-usd` without `--live`;
    2. `ATLAS_MODEL_MODE` not exactly `live`;
    3. `--authorize-spend-usd` missing, not a finite decimal, or not equal (Decimal comparison) to the decided 0.51. The message states both values;
    4. `SpendLimits.check` against the decided `NebiusConfig` fails.

    Only then: `load_api_key`, the pre-run check, `NebiusClient`, and `run_agent(live_authorized=True, spend=decided limits, budget=Budget(max_attempts=6), preflight=evidence)` with typed approvals.
  - **Exit codes:** 0, 1, 3, 4 and 5 for completed runs (unchanged); 2 for a refusal; **6 for a pre-run abort** (`PREFLIGHT_ABORT_EXIT`).
  - **Pre-run check (`preflight.run_preflight`):**
    - one `GET {base_url}models?verbose=true` with the bearer key, the configured timeout, no retries, no redirects and no completion;
    - it passes only if the configured model is listed once and its listed prompt/completion prices (Decimal) and context length (an exact integer) equal the configuration;
    - it aborts on a missing model, any mismatch (naming each field with expected and listed values), a transport error, a timeout, a non-200 status, malformed JSON, or a missing or malformed field.

    The evidence is sanitized: the URL without the query, status, request ID (only a plain, key-free identifier), model, expected and listed values, result, reason and mismatches; never the key, a header or provider text. The CLI writes it to `<runs-dir>/preflight-<UTC>.json` on abort, or to the run's report `preflight` section and `preflight.json` on pass. `scripts/live_preflight.py` is a dry run by default, sending nothing and reading no key; `--execute` writes `runs/preflight-<UTC>.json`. **It was not executed.**
  - **Tests (logs in git-ignored `runs/g3/`):**
    - `uv run --locked pytest tests/unit/test_agent_slice4_live_entry.py -q -p no:cacheprovider --basetemp=runs/g3/e1` → **46 passed**, exit 0 (`live-entry.log`). Each CLI call runs under the network guard, with a mock provider and a synthetic key file. Covered:
      - seven flag and mode refusals, nine amount refusals (missing, 0.50, 0.52, abc, NaN, Infinity, -0.51, empty, malformed) and both spending-limit refusals, each with tripwires on the key read, client, pre-run check, `run_agent` and Docker, and no run directory;
      - 0.51, 0.510 and " 0.51" accepted (reaching the pre-run check);
      - fixture mode unchanged;
      - thirteen pre-run aborts (model absent; input price, output price and context length mismatched; 503 and 401; timeout; connection error; malformed JSON; missing `data`; missing price; missing or float context length), each exiting 6 with exactly one GET and no completion, and the key in no output or evidence;
      - mismatch messages naming expected and listed values; the request shape; equal prices in another notation; a key-shaped request ID withheld;
      - the live path end to end: fake Docker and typed approvals, a LIVE report with the decided limits and the pre-run evidence, 1 GET then 2 completions whose bodies are exactly `max_completion_tokens`, `messages`, `model` and `n` (8000, 1), and the key in no file;
      - the decided constant read only by the CLI and the script;
      - the script's dry run and its mocked execute path.
    - **Focused suites** (the new file, the two other slice 4 files, the three slice 3 files and the controller tests; `focused.log`): **347 passed**, exit 0.
    - **Red at the Part 1 commit** (fresh `git archive a296199` plus this file and its fixture; `red.log`): **10 failed, 35 errors, 1 passed.**
      - All 45 are new-interface failures: `atlas.agent.preflight`, `cli.LIVE_ENV_FILE` and `cli.REFUSED_EXIT`, `scripts/live_preflight.py` and `preflight.py` are absent.
      - 0 are behavioural: no live path existed to compare against.
      - The 1 pass is the fixture-mode control.
    - **Full suite** with Docker required (`docker info` → linux 29.8.2; `$env:ATLAS_REQUIRE_DOCKER='1'; uv run --locked pytest tests -q -p no:cacheprovider --basetemp=runs/g3/t -rs`; `full.log`): **1091 passed, 1 skipped (the existing symlink-permission skip) in 832.52 s, exit 0**.
    - `uv run --locked ruff check .` and `uv run --locked ruff format --check .` are clean.
    - The first controls run errored only because `runs/g3/` did not exist yet (`WinError 3`, environment); it was rerun after creating the folder.
  - **Limitations:**
    - the pre-run check confirms the listing, not the provider's actual billing or enforcement;
    - the tokenizer and template remain unverified, so the 12,000 input figure is an estimate;
    - the 60 s timeout is proposed;
    - the base URL is the documented one, not read from `.env`;
    - the key is read from the repository `.env` by `load_api_key` only after every refusal check;
    - nothing was run against Nebius.
- **GATE 3 REVIEW (`runs/g3v/review.md`, Codex, at `54feca6`): FAIL, three P2 and one P3.**
  - **P2-1, unbounded evidence formatting** (`preflight.py:40, :150, :180`; `money.py:131`): a listed price was length-checked as text but not range-checked. `"1E+100000"` (9 characters) was formatted into 100,001 characters, about 200 KB of evidence. It failed closed (abort, no completion), but resource use was unbounded.
  - **P2-2, test gap: authorization compared as floats** (variant b, `cli.py:207`): a scratch mutation `float(amount) != float(decided)` passed all 70 existing live-entry and control tests. `0.51000000000000001` would have been accepted.
  - **P2-3, test gap: a raised pre-run check** (variant c, `cli.py:237`): a scratch mutation that caught an exception and substituted passing evidence passed all 70 existing tests and reached the client. The production code failed closed with an uncaught exception, not a sanitized exit 6.
  - **P3, fixture report field:** fixture reports gained `"preflight": {"applicable": false, ...}`, so the report is not byte-for-byte unchanged. *Accepted by the lead* (DECISIONS.md, Gate 3 dispositions, 2026-10-17).
  - **Lead confirmations requested:** the 60 s timeout, and the base URL and model coming only from the constant. *Both decided* (DECISIONS.md, Gate 3 dispositions).
  - **Codex's harness limitations (not product defects):**
    - its outer network guard conflicted with the tests that check the guard is restored (13 assertion failures and 1 refused loopback setup);
    - its `.env*` guard blocked the synthetic `.env` key-file test;
    - `docker` was not on its PATH, so the Docker integrations were not run;
    - early trusted-fixture child processes were not covered by its guard.

    Codex verified the refusal order, the constant-only configuration source, the real listing's shape (it passes), and five other weakened variants (a, d, e, f, g caught).
- **GATE 3 REPAIR PASS 1 RESULT (2026-10-17): self-tested; awaiting Codex verification; nothing live authorized.** No network request, `.env` read, pre-run call, live run or spending.
  - **Files:** `src/atlas/agent/preflight.py`, `src/atlas/agent/money.py`, `src/atlas/cli.py`, `tests/unit/test_agent_slice4_live_entry.py`. Commit 1 (`0a601d9`) recorded the dispositions and relabelled the timeout as decided.
  - **P2-1, bounds as implemented:**
    - **Body:** read incrementally with `client.stream`, capped at `MAX_BODY_BYTES` = 1 MiB (`preflight.py:48`, `_read_capped` `:144`). The cap applies to both the declared Content-Length and the bytes actually received. Over the cap is `response_too_large`, with no parse.
    - **JSON:** a `ValueError` (bad JSON or UTF-8, or the 4,300-digit integer limit) or a `RecursionError` (deep nesting) is `response_malformed` (`_listed_values` `:234`), never an exception.
    - **Prices** (`_price` `:77`):
      - absent is `missing_field`;
      - a non-string, a string over 64 characters or an unparseable value is `price_malformed`;
      - an integer over 400 bits is never converted;
      - anything else must pass `money.price_problem` **before** any formatting or comparison: finite, non-negative, no negative zero, at most 30 decimal places, at most 1e100 USD per token. That check (`money._decimal_problem` `:67`) now works from the `Decimal` tuple alone: `adjusted = len(digits) - 1 + exponent` (`:81`), with no comparison or formatting. It is the same range `NebiusConfig` enforces, and it now enforces it the same way. Failures are `price_out_of_range`.
    - **Context length** (`_context_length` `:100`): a genuine `int`, not a bool, from 2 to 10**100. Otherwise `context_length_out_of_range`; absent is `missing_field`.
    - **Evidence:** a rejected value is recorded as `{"field", "raw"}`, with the raw text cut to 64 characters (large integers as `<int of N bits>`), never a formatted expansion. The whole record is kept under `MAX_EVIDENCE_BYTES` = 16 KiB (`:49`) by `_bounded` (`:260`), a fallback that cannot trigger with these bounds. Previously the abort code for bad JSON was `malformed_json`, and a float context length was `missing_field`.
  - **P2-3:** `cli.py:239` wraps `run_preflight`. Any `Exception` becomes abort evidence (`preflight.error_evidence`: `preflight_error: <TypeName>`, the type name only) and exit 6; no client, `run_agent`, Docker call or completion follows. `BaseException` is not caught.
  - **P2-2:** amount-refusal tests for `0.51000000000000001` and `0.50999999999999999` (distinct Decimals, equal floats), with the existing tripwires.
  - **Tests (logs in git-ignored `runs/g3r/`):**
    - `tests/unit/test_agent_slice4_live_entry.py` → **72 passed** (46 + 26 new):
      - the 2 near-equal amounts;
      - 3 raised pre-run checks (`RuntimeError`, `OSError`, `ValueError`, each with a synthetic marker, exit 6, the marker and key in no output or evidence);
      - 19 bounded cases, each exiting 6 with one GET, no completion, a fixed code and evidence ≤ 16 KiB:
        - prices `1E+100000`, `1E-100000`, `1e101`, `-0`, `-1E-7`, NaN, a 10**200 integer, 31 decimal places and a 65-character string;
        - in-range `1E+31` and a 64-digit string, which reach the normal mismatch;
        - context lengths 10**100+1, 1, negative and bool;
        - a 5,000-digit integer;
        - a body just over 1 MiB, an understated Content-Length and 100,000-deep nesting;
      - 2 controls (the synthetic listing, and the archived real listing read only from `runs/nebius_smoke/`, which **passed**, not skipped).

      Every existing abort test now also asserts evidence ≤ 16 KiB.
    - **Focused** (`uv run --locked pytest tests/unit/test_agent_slice4_live_entry.py tests/unit/test_agent_slice4_controls.py tests/unit/test_agent_slice4_prompt.py tests/unit/test_agent_controller.py -q -p no:cacheprovider --basetemp=runs/g3r/t/u -rs`): **240 passed**, exit 0 (`focused.log`).
    - **Red at `54feca6`** (fresh `git archive` plus this file; `red.log`): **25 failed, 46 passed, 1 skipped** (the archived-listing control; the archive copy has no `runs/`).
      - **9 behavioural:**
        - three raised checks escaped as exceptions;
        - 100,000-deep nesting crashed with `RecursionError`;
        - the over-1 MiB and understated-length bodies were accepted and the run was reached;
        - `1E+100000` and `1E-100000` wrote 200,834- and 200,836-byte evidence;
        - a 31-decimal price equal in value was accepted and the run was reached.
      - **13 reason-code differences** (the parent already aborted safely, under `mismatch`, `missing_field` or `malformed_json`).
      - **2 new-interface failures** (the `rejected` evidence field).
      - **1 label** (the timeout now decided).
      - The two near-equal amounts **passed** at the parent, which already compared Decimals: Codex's P2-2 was a test gap, shown only by the mutation.
    - **Codex's variants rerun from a scratch copy** (`runs/g3r/m/`, made by `make_g3r_mutations.py` from `runs/g3v/mutations.py`; the adaptations are in `ADAPTATIONS.txt`: paths, `ROOT`, its review guard not imported, and variant c targeting the repaired call site). Both are now **caught**:
      - **b** (float comparison): 2 failed, 94 passed (`mut-b.log`), namely the two near-equal amounts;
      - **c** (passing evidence substituted): 3 failed, 93 passed (`mut-c.log`), namely the three raised checks.
    - **Full suite** with Docker required (`docker info` → linux 29.8.2; `$env:ATLAS_REQUIRE_DOCKER='1'; uv run --locked pytest tests -q -p no:cacheprovider --basetemp=runs/g3r/t/f -rs`; `full.log`): **1117 passed, 1 skipped (the existing symlink-permission skip) in 856.05 s, exit 0**.
    - `uv run --locked ruff check .` and `uv run --locked ruff format --check .` are clean.
  - **Not changed (not owned in this pass):** `scripts/live_preflight.py` still prints the timeout as "(proposed)" in its dry-run plan; the label is stale since the Gate 3 dispositions.
  - **Limitations:**
    - the bounds protect the pre-run check, not the completion path (bounded separately by the slice 3 usage checks);
    - the 1 MiB cap and 64-character raw cut are builder choices;
    - the 12,000 input figure remains an estimate;
    - provider enforcement and actual billing remain unverified;
    - nothing was run against Nebius.
- **GATE 3 RE-VERIFICATION (`runs/g3w/review.md`, Codex, at `f327565`): FAIL on one literal criterion.** The three original P2s were verified closed: unbounded listed-value expansion, the float-comparison test gap, and the raised-preflight test gap. No new P1/P2 was found.
  - **Two P3s:** in-range `1E+31` renders as a bounded 32-digit fixed-point value, contrary to the old "no expanded value anywhere" wording; `money.py` rejects `0E+200` despite its zero value. Both fail closed. The lead's re-verification dispositions revise the first criterion and defer the second limitation.
  - **Verification:** **213 focused tests passed**, exit 0; selected Ruff check passed. The initial attempt had 97 passed and 116 setup errors because the temporary parent directory was missing; the unchanged selection passed after that directory was created.
  - **Mutations caught:** b (float comparison), **2 failed / 70 passed**; c (substituted passing evidence), **3 failed / 69 passed**; both exit 1, with precisely the intended regression tests failing.
  - **Controls and safety:** archived real-listing control **PASS** through a mocked transport; **0 probe network attempts**. Preservation: **7,388 hashes unchanged**, 0 added/removed/changed, 7 identical inaccessible paths, 0 reparse points. The builder's full-suite and earlier mutation evidence was inspected, not rerun.
- **GATE 3 FOLLOW-UP (`runs/g3x/review.md`): FAIL on one requested probe outcome.** The revised P2-1 criterion clauses (a)–(d) pass; no new P1/P2 was found.
  - **Trace and bounds:** **14 relevant formatting calls and paths** traced; longest rendered value **101 characters**, largest evidence **1,699 bytes**; **0 network attempts**.
  - **P3:** the 64-character raw-string cap rejects the maximum-digit input as `price_malformed`, instead of the prompt's requested normal mismatch. Four cases produced three normal mismatches and one outcome assertion failure, with 0 errors; all exited 6 with one mocked GET and no completion. This fail-closed outcome is accepted by the lead's third re-verification disposition.
- **GATE 3 CONFIRMATION (`runs/g3y/review.md`): GATE 3 PASS** at `f327565`, under DECISIONS.md "Gate 3 re-verification dispositions (lead, 2026-10-17)".
  - The prior verified checks stand; no tests or prior probes were rerun. The single archived-listing check found **1** matching model: `pricing.prompt` and `pricing.completion` are strings of **9 characters each** (both within 64); `context_length` is an **int**. The string-length check precedes Decimal parsing and rendering.
  - **No unresolved blocking findings.** PASS means ready for the lead's explicit go-ahead; it authorizes no preflight call, live run or spending. **T-06 is not accepted; nothing live run.**
- **LIVE RUN 1 (`runs/live1/agent-s01_faulty-3f18e12af383/`, 2026-10-17).** The user's go-ahead covered one pre-run check and one live run, at most $0.51.
  - **Result:**
    - terminal state REPORT, exit 0 (observed when the run ended; the exit code is not stored in the run's files);
    - the original is **VIOLATION_FOUND**, executed in the isolated Docker runner (`docker_isolated`, completed) after its typed approval;
    - the report is labelled LIVE, model `nvidia/nemotron-3-super-120b-a12b`.
  - **Pre-run check:** `GET /models`, status 200, request ID `a7001ce743b634d15c09664ed9939fa9`. It passed with no mismatch: prices $0.0000003 / $0.0000009 per token, context 262,144.
  - **Budget:**
    - **5 of 6** requests, **0 retries**;
    - 2 of 2 revisions, 4 of 12 tool operations;
    - 34.845 of 300 active seconds; approval wait 43.093 s; 77.938 s in all.
  - **Cost:**
    - **estimated $0.0087333**, from provider-reported usage at listed prices; this is not billing. Unresolved $0; below the $0.0648 estimate cap and the $0.51 authorization;
    - the user observed about one cent of credit used;
    - the user's literal-key search found 0 matches. Gate 4's own key-hygiene counts were also all 0.
  - **Proposals:** two, both rejected by `validate_diff`, so **no candidate executed**. The rejection reasons were not recorded; slice 4c fixes that (below).
- **GATE 4 REVIEW (`runs/g4/review.md`, Codex, at `d870275`): FAIL, two P2, 0 P1.** The verdict and findings, exactly as Codex wrote them:

    > Verdict: GATE 4 FAIL
    >
    > Findings: **2 P2; 0 P1.** The recorded live boundaries hold within the stated evidence limits, but the two honest-reporting defects block this gate. The original's scientific outcome remains `VIOLATION_FOUND`; this review does not rehabilitate it.
    >
    > 1. **P2 — LIVE report contradicts its model provenance.** `src/atlas/agent/report.py:157` hardcodes `comparison.model` to “none (T-06 slice 1 has no model client; candidate diffs are supplied inputs)”. This appears at `E/agent_report.json:28`, despite the LIVE banner, configured model and five successful live attempts. Evidence: `evidence-checks.json` (stale model label demonstrated), `report-support-counts.txt`, and the report itself. A consumer of the comparison receives a false provenance claim. **Fails closed: no, for reporting; no execution/approval bypass demonstrated.** Derive the comparison's model provenance from the actual run context.
    > 2. **P2 — rejected proposals and their reasons disappear from durable reporting.** `src/atlas/agent/controller.py:931`–935 catches validation rejection and returns; `_record_tool` at `:864`–875 keeps the body in memory but persists only its hash and length. `_limitations` at `:1067` omits the zero-candidate case. Both revisions reached `propose_patch` (`E/agent_log.jsonl:17` and `:21`), neither reached candidate approval/execution, and both returned to the model. Together with the saved control-flow check, this identifies the validation-rejection path; the precise rejection reasons cannot be recovered from the stored artifacts. The report retains two rationales (`E/agent_report.json:174`, `:179`) but states neither rejection nor that no candidate executed. Empty candidate arrays and the non-evidence labels do not explain what happened to the proposals. Evidence: `deep-checks.json`, `final-checks.json`, `boundary-checks.json`, `function-_propose.txt`, `function-_record_tool.txt`, `function-_limitations.txt`; `reconstructed-rejections.json` contains zero reconstructed reasons. **Fails closed: yes for candidate execution; no for durable explanation.** Persist a bounded rejection status/reason per revision and explicitly report zero candidates executed.
    >
    > The unmerged `t06-s4c` fixes were not reviewed and do not change this verdict on the recorded live evidence.
    >
    > Gate 4 decides whether this evidence supports the lead considering T-06 acceptance. **It does not yet support acceptance because two P2 reporting defects remain. This review authorizes no further run or spending.**

  - **Disposition:** slice 4c addresses both findings and is reviewed in the combined Codex review (DECISIONS.md "Lead decisions, 2026-10-17", items 3 and 4):
    - `comparison.model` now names the live model or the fixture replies;
    - every proposal is recorded with its outcome and a bounded reason;
    - a run-level line counts the proposals that were rejected, declined and executed.
- **SLICE 4c RESULT (`2ce5dd5`, `292ed81`, branch `t06-s4c`; on `main` by fast-forward, 2026-10-17).**
  - **Design** (DECISIONS.md "Lead decisions, 2026-10-17" item 4):
    - `propose_patch` takes exactly one of `diff` or `new_source`. For `new_source`, ATLAS builds the diff with `difflib`, and the unchanged `validate_diff` remains the only gate;
    - every proposal is recorded in `agent_report.json` `proposals` and mirrored in the tool log, with its outcome (`rejected`, `declined`, `unavailable`, `executed`) and a bounded reason. Its diff and source are kept under `<run>/proposals/`, labelled model-written and untrusted;
    - `comparison.model` names the live model or the fixture replies;
    - each `model_attempt` log event carries its ledger entry, or a fixture note;
    - `292ed81`: the JSON schema shown to the model gives `diff` and `new_source` as plain strings with their length limits, under a `oneOf` that requires exactly one. Runtime validation is unchanged.
  - **Tests** (logs in the `atlas-s4c` worktree, git-ignored `runs/s4c/`):
    - red at the parent: 20 failed, 9 passed;
    - full suite with Docker required: **1145 passed, 2 skipped** at `2ce5dd5`, and **1156 passed, 2 skipped** after the follow-up;
    - targeted: 184 passed;
    - ruff clean.

    The second skip is the archived-listing control, absent in a worktree.
  - **Not done:** live run 2 has not run, so no live run yet shows a candidate executing.
- **LIVE RUN 2 (`runs/live2/agent-s01_faulty-93583d9e48b5/`, 2026-10-17).** The user gave the go-ahead by starting the run themselves on 2026-10-17.
  - **Result:**
    - terminal state ERROR, `schema_failure: not_json` on attempt 2 (1,606 completion tokens);
    - attempt 1 read `evaluate.py`;
    - the original is **VIOLATION_FOUND** (`docker_isolated`).
  - **Budget:** 2 requests, 0 retries.
  - **Cost:** estimated **$0.0025863** (provider-reported usage at listed prices; not billing).
  - **Proposals:** none.
  - `comparison.model` names the live model and each attempt carries its cost: the slice 4c fixes confirmed live.
  - **Cause unknown:** the raw replies were not stored. Slice 4d stores them (below).
- **SLICE 4d RESULT (`0b7bcce`, branch `t06-s4d`; not merged).**
  - **Design** (DECISIONS.md "Lead decisions, 2026-10-17" item 10):
    - **raw replies:** every reply's text is written to `<run>/replies/a<N>.txt` as received and before it is parsed, at most `MAX_REPLY_BYTES` (beyond that the first `MAX_REPLY_BYTES`, marked truncated). Its SHA-256 and size go into the `model_attempt` log event and the report's `replies` list, labelled "model-written (untrusted); never evidence". No request, header or key is stored. Fixture runs too;
    - **one corrective turn:** a content failure from `parse_reply` is recorded (code and attempt, in the report's `schema_failures`), and the next request carries a bounded correction: the code, a fixed explanation per code and at most 200 characters of the parser's message. The reply is never quoted. That request is an ordinary attempt within the 6-attempt budget, reserved before dispatch, and authorizes nothing;
    - **when the run still ends ERROR:** two consecutive schema failures, a schema failure on the final attempt, or a reply-metadata failure (`mislabelled`, `incomplete`). A valid reply resets the count. The limitations line reads "N replies failed validation; M corrected on the next turn";
    - **prompt:** one raw JSON object only, no Markdown code fences and no text before or after, with one valid `read_project_file` example. `diff` for small edits, `new_source` for rewrites, with newlines and quotes escaped inside the JSON string. Generic: no benchmark hints. The prompt-budget figures are derived from the prompt in the tests, not pinned;
    - **unchanged:** exact reply validation (one action, no duplicate keys, no extra fields, no format repair); 6 requests per run, each reserved before dispatch; `validate_diff` as the only candidate gate; Docker-only execution; the spend controls and the live entry point.
  - **Changed assertions** (expected behaviour changes, none weakened: each still asserts that no invalid reply authorizes or executes anything):
    - `test_agent_controller.py::test_invalid_reply_is_a_recorded_schema_failure_with_no_action`: the invalid reply is scripted twice; 3 requests for content failures (was 2), 2 for `truncated_by_length` (metadata, unchanged). Added: no failure is marked corrected. Reason: a content failure now gets one corrective turn, and the second in a row ends the run;
    - `test_agent_controller.py::test_an_oversized_multibyte_diff_is_a_schema_failure_with_no_action`: REPORT after 2 requests (was ERROR after 1), with `schema_failures` `[{attempt 1, schema, corrected}]`, no execution and 0 tool operations or revisions. Reason: the failure is corrected once and the scripted `finish` follows;
    - `test_agent_slice3.py::test_invalid_live_replies_authorize_nothing` (`prose`, `no_content`, `length`): the body is sent twice; 2 requests for content failures (was 1), 1 for `length`. Reason: as above, over the mocked production client;
    - `tests/acceptance/test_scenario4_failures.py::test_invalid_reply_is_a_schema_failure_without_repair`: 2 attempts (was 1), two `schema_failure` trace rows, neither corrected. Reason: the UI's "Invalid reply" script now sends two non-JSON replies;
    - `test_agent_slice4_controls.py` (`PROMPT_BYTES`, `BUDGET`) and `test_agent_slice4c_proposals.py::test_the_prompt_figures_are_unchanged_by_the_schema_fix`: the prompt-budget figures are derived from `SYSTEM_PROMPT` (and checked through the client's `user_message_budget`) instead of pinned. Reason: the new prompt is 945 bytes (635 in slice 4c), so the user-message budget is 11,023 bytes (11,333 in slice 4c).
  - **Tests** (logs in git-ignored `runs/s4d/`):
    - red at the base `ddab0ae` (`red_summary.log`): **17 failed, 2 passed** of the 19 new tests (18 unit, 1 Docker integration). The 2 passes are controls that already held (a schema failure on the final attempt, and a reply-metadata failure, both end the run). The prompt-figures test was later rewritten to derive its figures;
    - full suite with Docker required (`full.log`): **1212 passed, 1 skipped**;
    - ruff check and format clean.
  - **Not done:** live run 3, which needs the user's go-ahead.
- **LIVE RUN 3 (`runs/live3/agent-s01_faulty-03181c39282f/`, 2026-10-17).**
  - The original's typed approval was **declined** (`confirmation_mismatch`; the user typed the snapshot hash prefix), so the run ended **NEEDS_INPUT** ("execution of the original was not authorized").
  - **0 requests**, 0 retries; estimated **$0**.
  - The user renewed the go-ahead for the retry (live run 3b).
- **LIVE RUN 3b (`runs/live3b/agent-s01_faulty-7de5564eab88/`, 2026-10-17).**
  - **Result:** ERROR, `schema_failure: incomplete`. The original is **VIOLATION_FOUND** (`docker_isolated`).
  - **Budget:** 3 requests, 0 retries, 1 tool operation, 0 revisions.
  - **Cost:** estimated **$0.0094995** (provider-reported usage at listed prices; not billing).
  - **Causes, diagnosed from the persisted replies** (slice 4d):
    - attempt 1 (`replies/a1.txt`): a valid `read_project_file` of `evaluate.py`;
    - attempt 2 (`replies/a2.txt`): valid JSON for `list_project_files` plus a `rationale`, which that action did not declare, so `schema` (extra field). The corrective turn was sent;
    - attempt 3: finish reason `length` at 8,000 completion tokens with no content, so `incomplete`, which ended the run.
- **SLICE 4e RESULT (`67c5ed0`, branch `t06-s4e`; not merged).**
  - **Design** (DECISIONS.md "Lead decisions, 2026-10-17" item 11):
    - **optional rationale:** every action may carry an optional `rationale`, a non-null string of at most `MAX_TEXT_CHARS` (4,000) characters; `propose_patch` still requires it. The schema shown to the model gives it as an optional plain string (no null type, no default). It is recorded in `model_text` with the model-written label (`action_rationale`; a proposal keeps its single `patch_rationale`), is excluded from tool arguments and changes nothing the action does. A null, non-string or over-long rationale and every other undeclared field are still rejected;
    - **empty length replies:** a reply with finish reason `length` and no text (absent, empty or only whitespace) is the schema failure `incomplete_length`, eligible for the one corrective turn with the fixed explanation "The reply hit the output limit before any action was written. Reason briefly and reply with one short JSON object." A `length` reply with text is still `incomplete` and ends the run, as do `mislabelled` and every other unfinished reply. The consecutive and final-attempt rules are unchanged;
    - **prompt:** one added sentence, "Keep any reasoning brief and the reply short." The prompt stays generic; the budget figures are derived in the tests;
    - **unchanged:** exact reply validation (one action, no duplicate keys, undeclared fields forbidden, no format repair); 6 requests per run, each reserved before dispatch; `validate_diff` as the only candidate gate; Docker-only execution; the request body (model, messages, `max_completion_tokens` 8,000, `n` 1; no reasoning-control parameter); the spend controls and the live entry point.
  - **Changed assertions** (expected changes, none weakened):
    - `test_agent_slice4d_replies.py::test_every_parse_reply_code_has_a_fixed_explanation`: the explanation set is the 7 `parse_reply` codes plus `incomplete_length`. Reason: the new correctable metadata code;
    - `test_agent_slice4c_proposals.py::test_the_shown_schema_states_exactly_one_non_null_source`: `required` is compared as a set (`rationale`, `tool`). Reason: `rationale` is now inherited, so it is listed first; JSON Schema `required` is unordered;
    - `test_agent_slice4c_proposals.py::test_the_prompt_figures_are_unchanged_by_the_schema_fix`: the shown schema is 2,915 bytes (2,619 in slice 4c). Reason: the optional rationale on every action.
  - **Tests** (logs in git-ignored `runs/s4e/`):
    - new: `tests/unit/test_agent_slice4e_rationale.py` (64 tests) and the Docker replay of live run 3b (`test_the_live_run_3b_replay_runs_a_candidate_in_docker`: the exact a1 and a2 bytes, then a valid `new_source` revision, approved by the scripted test approver, executed in Docker and recorded `executed`);
    - red at the base `2b85715` (`red_summary.log`): **27 failed, 38 passed** of the 65 new tests. Every failure is the missing behaviour; the 38 passes are controls that already held (rejections of invalid rationales and other fields, `propose_patch` with a rationale, a `length` reply with text, other unfinished replies, `mislabelled`);
    - full suite with Docker required (`full.log`): **1277 passed, 1 skipped**;
    - ruff check and format clean.
  - **Not done:** live run 4, which needs the user's go-ahead.
- **LIVE RUN 4 (`runs/live4/agent-s01_faulty-8dcf4c7b3c37/`, 2026-10-18). The first live end-to-end loop:** live model replies, two proposals validated by `validate_diff`, both approved, both executed in the isolated Docker runner and judged by the trusted evaluator.
  - **Result:** terminal state **BUDGET_EXHAUSTED** (`candidate_revisions: 2 revisions already proposed`). The original is **VIOLATION_FOUND**; both candidates **INCONCLUSIVE** (execution failed: each exited 1).
  - **Budget:** 5 requests, 0 retries, 2 of 2 revisions, 6 tool operations.
  - **Cost:** estimated **$0.0166986** (provider-reported usage at listed prices; not billing).
  - **Both candidates' failure:** each `new_source` read `X['subject_id']`, but `adapter.load_table()` returns only the feature columns (`KeyError: 'subject_id'`). The group IDs come from `adapter.load_metadata()`.
  - **Why the model repeated it:** the supervisor captured the traceback (`supervisor.candidate_output_tail` in `candidates/c1/execution.json`), but the evaluate_candidate result carried only the status and outcome, and the record's `stderr_tail` (the docker CLI's own stderr) was `""`. Slice 4f returns a bounded summary.
  - **Key check (the user's literal-key search):** 0 matches for live run 4, as reported by the user; live runs 1 to 3b were also 0.
- **SLICE 4f RESULT (`61e10af`, branch `t06-s4f`; not merged).**
  - **The stderr cause:** nothing is discarded. The in-container supervisor starts the candidate child with `stderr=subprocess.STDOUT` (`src/atlas/runner/container_entry.py:177-178`) and keeps the last 16 KiB of that combined stream as `candidate_output_tail` in its frame header (`:209`, `TAIL_BYTES` at `:36`). The record's `stderr_tail` is the docker CLI process's stderr (`src/atlas/runner/docker.py:1005`, read at `:444`), which carries only the supervisor's or Docker's own messages, so it is empty when only the candidate fails. **No runner change:** `src/atlas/runner/` is untouched; the summary uses the existing captured output.
  - **Design** (DECISIONS.md "Lead decisions, 2026-10-17" item 12):
    - **error feedback:** `agent/failure.py` summarizes a failing candidate's captured output: the exception line of the last traceback (type and message) plus at most its last 20 lines (or the output's last 20 lines when there is no traceback), at most 2,000 characters in all, keeping the end. Host paths (the run, runs, project, home, working and temp directories, and any Windows drive or UNC path) and host environment values of 8 or more characters are redacted; the key is removed by the client itself (`NebiusClient.redact_secret`, a text-only method; the request path is unchanged); every control or format character except the line separator is escaped. Labelled "candidate output (untrusted)", it is added to the evaluate_candidate tool result and stored as `failure_summary` in the candidate's comparison entry. The raw output stays in memory (`CandidateResult.candidate_output`) and is never reported;
    - **adapter reference:** `agent/adapter_reference.py` derives a fixed, generic reference from the source of `atlas.adapter`: `load_table`, `load_metadata`, `take`, `declare_split` and `write_predictions` (every public function except the harness-only `session`), each with its signature and the first line of its docstring, plus the rule that row selection of the loaded X and y goes through `adapter.take`. Rendered as text, it ends the system prompt (`SYSTEM_PROMPT = SYSTEM_INSTRUCTIONS + blank line + ADAPTER_REFERENCE_TEXT`), identical for every project;
    - **why the system prompt:** the first full run placed the reference in the user message, and 9 tests of the reviewed prompt-budget repair (`test_agent_slice4_prompt.py`: the newest maximal result must survive whole) failed, because the fixed user message left 5,197 bytes against a 5,488-character per-result limit. In the system prompt the reference is counted before the user-message budget and the per-result limit (half of it) are derived, so that property holds again; no test was weakened;
    - **prompt-budget figures** (derived, at the decided 12,000-token input estimate): system prompt **2,075 bytes** (instructions 991, reference 1,082, separator 2; 991 in slice 4e); user-message budget **9,893 bytes** (12,000 - 2,075 - 2 x 16; 10,977 in slice 4e); per-result limit **4,946 characters** (5,488 in slice 4e). Every request stays within the budget, and the fixed user message leaves room for one whole result;
    - **unchanged:** exact reply validation; 6 requests, each reserved before dispatch; `validate_diff` as the only candidate gate; Docker-only execution; the decided request body; the spend controls and the live entry point; outcomes only from the trusted evaluator.
  - **Changed assertions** (none weakened): `test_agent_slice4d_replies.py::test_the_prompt_asks_for_one_raw_object_with_a_valid_example` and `test_agent_slice4e_rationale.py::test_the_prompt_asks_for_brief_reasoning_and_a_short_reply` check the same benchmark-hint list against `SYSTEM_INSTRUCTIONS` instead of the whole prompt. Reason: the adapter reference now ends the system prompt and names `fold` as its own API parameter (`declare_split(fold: str, ...)`); the reference has its own genericity test (no `s01`, `s02`, `subject`, `evaluate.py`, `SelectKBest`, `GroupKFold`, `HAR`).
  - **Tests** (logs in git-ignored `runs/s4f/`):
    - new: `tests/unit/test_agent_slice4f_feedback.py` (17 tests), the fixtures `tests/fixtures/live4_r1_new_source.txt` and `live4_c1_candidate_output.txt` (live run 4's exact bytes, pinned by SHA-256), and the Docker replay `test_the_live_run_4_replay_feeds_the_error_back_and_the_fix_runs`: the exact c1 source fails in the real runner; the next request's evaluate_candidate result shows `KeyError: 'subject_id'` (838 characters, untrusted label); the revision corrected to take the groups from `adapter.load_metadata()` executes, and the trusted evaluator gives **NO_VIOLATION_FOUND**;
    - red at the base `9295d19` (`red_summary.log`, `red2.log`; the final tests with `src/` set back to the base): **16 failed, 2 passed** of the 18 new tests. Every failure is the missing behaviour; the passes are controls (the fixture bytes, and the maximal-history budget, which already held at base);
    - full suite with Docker required (`full.log`): **1295 passed, 1 skipped**, including the runner contract suite (`tests/integration/test_runner_contract.py`) and the UI acceptance tests. The first run (`full_attempt1.log`, reference in the user message) had 9 failures, described above;
    - ruff check and format clean.
  - **Not done:** live run 5, which needs the user's go-ahead.
- **LIVE RUN 5 (`runs/live5/agent-s01_faulty-a53e65ecf004/`, 2026-10-18).**
  - **Result:** ERROR, `schema_failure: not_json`. The original is **VIOLATION_FOUND**; no proposals.
  - **Budget:** 2 requests, 0 retries, 0 tool operations.
  - **Cost:** estimated **$0.0014256** (provider-reported usage at listed prices; not billing).
  - **Causes, from the persisted replies:**
    - attempt 1 (`replies/a1.txt`): `read_project_file` with `path` and `rationale` plus an undeclared `summary` field, so `schema` (`action.read_project_file.summary: extra_forbidden`). The one corrective turn was sent;
    - attempt 2 (`replies/a2.txt`): `list_project_files` with a `rationale` followed by a trailing comma, so `not_json`. It was the second consecutive failure, which ended the run under slice 4d's rule.
  - **Key check:** pending the user's literal-key search.
- **SLICE 4g RESULT (`baf7c04`; on `main`).**
  - **Design** (DECISIONS.md "Lead decisions, 2026-10-17" item 13):
    - **two corrective turns:** up to two consecutive eligible schema failures are corrected; a third consecutive one, or a schema failure on the final attempt, ends the run ERROR with the existing reason format. A valid reply resets the count. The eligible codes are unchanged (the `parse_reply` content codes plus `incomplete_length`); `mislabelled` and the other metadata failures still end the run at once. Each corrective turn is an ordinary attempt within the 6-request budget, reserved before dispatch;
    - **schema-derived corrections** (`controller.correction`): the code, its fixed explanation, the parser's message cut at 200 characters, and the note. A `schema` failure also gets `allowed fields for <tool>: ...` (`schemas.allowed_fields`, from that action's JSON schema: `tool` first, required fields marked, `propose_patch`'s exactly-one rule) when the reply named one of the five literal tool names (`ReplyRejected.tool`, set from the already strictly parsed JSON, so the name is always one of ours), else the five tool names. The `not_json` explanation now names Markdown fences, text around the object, an unescaped newline or quote, a trailing comma and comments. The whole serialized correction is at most 1,000 characters (the parser's message is cut further if JSON escaping would exceed it);
    - **how reply text is bounded:** a correction never quotes the reply. Reply text can reach it only through the parser's message, which carries pydantic's error location (a field name the reply wrote, for an undeclared field) or, for `duplicate_key`, the repeated keys. That message is cut at 200 characters, and no other field of the correction is built from the reply. Tested with a 590-character injected field name: it appears only in `parser_message`, cut to 200 characters; values (path, rationale, summary) never appear;
    - **prompt:** two sentences ("Valid JSON only: no trailing commas, no comments." and "Use only the fields listed for the chosen tool; finish is the only tool with summary."), and the example `{"action": {"tool": "read_project_file", "path": "src/train.py", "rationale": "see how the data is split"}}`. Generic: no benchmark hints;
    - **prompt-budget figures** (derived, at the decided 12,000-token input estimate): instructions 1,169 bytes (991 in slice 4f); system prompt with the adapter reference **2,253 bytes** (2,075); user-message budget **9,715 bytes** (9,893); per-result limit **4,857 characters** (4,946);
    - **unchanged:** exact reply validation (one action, no duplicate keys, undeclared fields forbidden, no format repair: reply text never altered or leniently parsed); 6 requests, each reserved before dispatch; `validate_diff` as the only candidate gate; Docker-only execution; the decided request body; the spend controls and the live entry point; outcomes only from the trusted evaluator.
  - **Example corrections** (live run 5's exact replies):
    - a1 (551 characters): `schema`, parser message `schema: action.read_project_file.summary: extra_forbidden`, tool `read_project_file`, `allowed fields for read_project_file: tool (required), path (required), rationale`;
    - a2 (480 characters): `not_json`, parser message `not_json: JSONDecodeError`, and the explanation naming trailing commas and comments.
  - **Changed assertions** (expected: two consecutive failures now get a second correction; none weakened, each still asserts that nothing invalid is acted on):
    - `test_agent_slice4d_replies.py`: `test_two_consecutive_schema_failures_end_the_run` became `test_three_consecutive_schema_failures_end_the_run` (three malformed replies, 4 requests, three failures, none corrected);
    - `test_agent_slice4e_rationale.py`: `test_two_empty_length_replies_in_a_row_end_the_run` became `test_three_empty_length_replies_in_a_row_end_the_run` (3 requests); `test_a_schema_failure_then_an_empty_length_reply_is_consecutive` became `test_schema_failures_then_an_empty_length_reply_are_consecutive` (two prose replies, then the empty `length` reply ends it: 3 requests);
    - `test_agent_controller.py::test_invalid_reply_is_a_recorded_schema_failure_with_no_action`: the invalid reply three times; 4 requests for content failures (was 3), 2 for `truncated_by_length` (unchanged);
    - `test_agent_slice3.py::test_invalid_live_replies_authorize_nothing`: the body three times; 3 requests (was 2), 1 for `length` (unchanged);
    - UI: the "Invalid reply" script sends three non-JSON replies, and `test_scenario4_failures.py::test_invalid_reply_is_a_schema_failure_without_repair` expects 3 attempts and three `schema_failure` trace rows (was 2). `docs/UI_SPEC.md` B8 and `docs/UI_WALKTHROUGH.md` updated.
  - **Tests** (logs in git-ignored `runs/s4g/`):
    - new: `tests/unit/test_agent_slice4g_corrections.py` (33 tests) and the Docker replay `test_the_live_run_5_replay_recovers_and_a_candidate_runs_in_docker`: live run 5's exact a1 (corrected with `read_project_file`'s allowed fields) and a2 (corrected, naming trailing commas), then a valid read and a valid `new_source` revision, approved by the scripted test approver, executed in Docker (**NO_VIOLATION_FOUND**) and recorded `executed`;
    - red at the base `70d82e6` (`red_summary.log`): **31 failed, 3 passed** of the 34 new tests. Every failure is the missing behaviour; the passes are controls (live run 5's bytes fail as recorded; failures on attempts 5 and 6 end the run; a metadata failure ends it at once);
    - full suite with Docker required (`full.log`): **1329 passed, 1 skipped**, UI acceptance included;
    - ruff check and format clean.
  - **Not done:** live run 6, which needs the user's go-ahead.
- **LIVE RUN 6 (`runs/live6/agent-s01_faulty-877f8245a8a2/`, 2026-10-18).** **First complete live end-to-end success: violation found -> model-proposed fix -> human approval -> isolated execution -> trusted re-evaluation NO_VIOLATION_FOUND.**
  - **Result:** BUDGET_EXHAUSTED (`candidate_revisions: 2 revisions already proposed`). The original is **VIOLATION_FOUND**.
  - **Budget:** 5 requests, 0 retries, 0 schema failures, 5 tool operations, 2 revisions.
  - **Cost:** estimated **$0.0190884** (provider-reported usage at listed prices; not billing).
  - **Revision 1** (`new_source`): approved by the user and executed in Docker (`docker_isolated`, completed, container removed). The trusted evaluator judged it **NO_VIOLATION_FOUND**. Four required checks went FAIL -> PASS: `split.no_group_overlap`, `split.sampling_unit_disjoint`, `split.repeated_measures_rule` and `fit.state_dependencies_within_fold_train`.
  - **Balanced accuracy, pooled** (descriptive, never part of an outcome): original 0.68125, candidate 0.675.
  - **Revision 2** (`new_source`): rejected by `validate_diff` (`syntax_error`). Attempt 5 hit the 2-revision limit, so the run ended BUDGET_EXHAUSTED instead of finishing after the success.
  - **Key checks** (the user's literal-key search): live run 5 0, live run 6 0.
- **SLICE 4h RESULT (`b900373`, branch `t06-s4h`; not merged).** T-06 slice 4h plus a T-07 follow-up.
  - **Design** (DECISIONS.md "Lead decisions, 2026-10-17" item 14):
    - **finish-after-success guidance** (generic): when the trusted evaluator judges a candidate NO_VIOLATION_FOUND, its evaluate_candidate result adds one fixed line, `next_step`: "The trusted evaluator found no violation for this candidate. Call finish with a summary unless a further revision is needed." (`controller.FINISH_AFTER_SUCCESS`). One system-prompt sentence: "After a candidate is judged NO_VIOLATION_FOUND, finish." No other change to the loop: the model still chooses its next action, and no other result, the report or the log carries the line;
    - **prompt-budget figures** (derived, at the decided 12,000-token input estimate): instructions 1,225 bytes (1,169 in slice 4g); system prompt with the adapter reference **2,309 bytes** (2,253); user-message budget **9,659 bytes** (9,715); per-result limit **4,829 characters** (4,857);
    - **a recorded-run viewer** (T-07 follow-up; `src/atlas/ui/recorded.py`, `src/atlas/ui/results.py`; docs/UI_SPEC.md §12 B25-B29). The UI gains the view "Open a recorded run", which lists finished run directories under a configured root (`ATLAS_UI_RECORDED_DIR`, default `runs/`; `live*/agent-*` and `ui/*`). It is read-only: nothing executes, no approval is asked, and there is no run or restart button. Before anything is shown, every hash the run recorded is recomputed from disk (`agent_log.sha256`, each reply's and proposal file's hash, each evaluated run's `evidence_sha256` and `index.json` artifacts and outputs), and each reported outcome is compared with its verified `outcome.json`. A mismatch, a missing file or a recorded path outside the run shows "evidence changed since recording", the failing items, and no outcome headline or result card. An intact run renders every existing card from its own artifacts: the claim from its own `original/manifest.snapshot.json`, the finding, the trace (approvals from its log), the revision with every proposal (rejected ones with their codes; persisted diffs labelled model-written (untrusted)), the comparison, trust and export. The banner shows the run's own LIVE or NON-LIVE label from `agent_report.json` and "Recorded run, finished <time>; not re-executed here". It is the basis for hosted replay (T-12). It detects changes since recording; it does not authenticate a run whose files and recorded hashes were both rewritten;
    - **refactor, no behaviour change:** the finished-run cards moved from `app.py` into `results.finished_run`, shared by both views; `catalogue.claim_view` builds the claim fields from a validated manifest; `short_time` moved from `app.py` to `artifacts`;
    - **unchanged:** exact reply validation (one action, no duplicate keys, undeclared fields forbidden, no format repair: reply text never altered or leniently parsed); 6 requests, each reserved before dispatch; `validate_diff` as the only candidate gate; Docker-only execution; the decided request body; the spend controls and the live entry point; outcomes only from the trusted evaluator.
  - **Tests** (logs in git-ignored `runs/s4h/`):
    - new: `tests/unit/test_agent_slice4h_finish.py` (12 tests: the line only for NO_VIOLATION_FOUND candidates, not for VIOLATION_FOUND, INCONCLUSIVE, a failed execution or NOT_SUPPORTED; guidance only; the prompt sentence and the budget figures; live run 6's replies 1-3 byte for byte (`tests/fixtures/live6_a1.txt` to `a3.txt`, hashes equal to the report's), then success -> finish -> REPORT);
    - new: `tests/unit/test_ui_recorded.py` (12 tests: listing, intact, one changed byte, a missing file, a report-only outcome change, a path outside the run, an audit run, the claim, time and decisions from the run);
    - new: the Docker replay `test_the_live_run_6_replay_finishes_after_success_in_docker` (live run 6's replies 1-3, the candidate executed in the real runner and judged NO_VIOLATION_FOUND, the line in the next request, finish, REPORT);
    - new: Playwright `tests/acceptance/test_scenario7_recorded.py` (3 tests on copies of runs/live6 in the basetemp: the LIVE banner and the recorded label, headlines equal to the artifacts, the four FAIL -> PASS rows, both proposals, nothing startable; a copy with one byte changed in `candidates/c1/outcome.json` shows "evidence changed since recording" and no headline; runs/live6 itself unchanged, by a hash of every file before and after). The acceptance `app` fixture takes optional per-module environment (`app_env(base)`); existing modules are unaffected;
    - red at the base `baa355c` (`red_summary.log`): **21 failed, 7 passed** of the 28 new tests. Every failure is the missing behaviour (no `next_step`, no `FINISH_AFTER_SUCCESS`, the prompt sentence and figures absent, no viewer); the passes are controls (the four non-success outcomes get no line, the line stays out of the report, the fixture bytes, runs/live6 unchanged);
    - screenshots at 1440 x 900 in `runs/s4h/screens/` (`s7_01` to `s7_05` for the viewer, with the existing scenarios' screenshots);
    - full suite with Docker required (`full.log`): **1357 passed, 1 skipped**, UI acceptance included;
    - ruff check and format clean.
  - **Not done:** the combined Codex review (slices 4c-4h, T-07, T-09, live runs 2-6), then the lead's T-06 acceptance decision.
- **COMBINED REVIEW 1 (runs/cr1/review.md): COMBINED FAIL** (Codex, 2026-10-18; read-only review of `bc2ef58` against `d870275`). Three P2 findings, verbatim:
  - "**F1 — P2, host-path redaction bypass**, `src/atlas/agent/failure.py:33-34,92-93`; outbound use at `src/atlas/agent/controller.py:1256-1259`." `summarize('//server/private/customer.csv', env={})` returned the path unchanged; `C:\Users\Alice Smith\private\customer.csv` kept ` Smith\private\customer.csv`; a newline-split drive path kept its second line. The output is labelled untrusted but still forwarded to the model; no evaluator or approval bypass.
  - "**F2 — P2, missing approval regression test**, `tests/unit/test_ui_core.py:106-110`; production rule at `src/atlas/ui/approver.py:158`." Mutation (d), "also accept `base_snapshot_hash[:12]`", survived all 17 UI-core tests. Production fails closed; a verification gap.
  - "**F3 — P2, byte-exact replay test fails on this Windows checkout**, `tests/unit/test_agent_slice4h_finish.py:49,216-219`." The `tests/fixtures/live6_a*.txt` working copies were CRLF (system `core.autocrlf=true`); the blobs are LF and correct. 211 passed, 1 failed on the required unit command.
  - Everything else checked passed or was NOT ASSESSED after the stop rule (reparse points, full T-09 adversarial pass, hooks executed). It does not support T-06 acceptance.
- **FIX PASS 1 (branch `fix-cr1`; not merged).** DECISIONS.md "Lead decisions, 2026-10-17" item 15.
  - **F3, `ad69a97`:** `.gitattributes` (`* text=auto eol=lf`; `tests/fixtures/** -text`; png, jpg, parquet, zip binary), committed alone. **23** tracked files had CRLF working copies (the task expected about 16): `.claude/settings.json`, `DECISIONS.md`, `STATUS.md`, `TASKS.md`, `app.py`, `docs/SPEC.md`, `docs/UI_SPEC.md`, `scripts/handoff_snapshot.py`, `src/atlas/agent/controller.py`, `src/atlas/ui/{__init__,artifacts,catalogue,recorded,results,views}.py`, `tests/acceptance/conftest.py`, `tests/acceptance/test_scenario7_recorded.py`, `tests/fixtures/live6_a{1,2,3}.txt`, `tests/integration/test_agent_fixture_docker.py`, `tests/unit/test_agent_slice4h_finish.py`, `tests/unit/test_ui_recorded.py`. Each differed from HEAD only by CR; each was deleted and restored from HEAD (the index's stale stat sizes were then refreshed with `git add` of the identical content; no staged change). After: **0** tracked `w/crlf`, before and after the full suite. `tests/fixtures/live6_a1.txt` SHA-256 = `deb06356e1e2f7ca70f41bd99c7c370cb0553cb739eee8de694712a79ac98485`.
  - **F1, `2519efa`:** `failure.py` recognizes a drive path (`C:\`, `C:/`, repr-doubled) and a UNC path in every slash style (`\\host`, `//host/`, `\\host/`, `/\host\`, repr-doubled). A quoted string that starts with one is replaced whole, keeping its quotes; an unquoted one is redacted to the end of its line, spaces included. A forward-slash UNC path needs its share separator and may not follow a word character, `:` or a slash, so URLs, `x//2` and container paths are kept. Host strings, environment values and the key are redacted as before. The guarantee is narrowed to best-effort in the module docstring and SPEC §11: the container's only mounts are under `/work`; path text split or encoded across lines is not guaranteed to be redacted; the output stays labelled untrusted.
  - **F2, `2519efa`:** the snapshot prefix (lower and upper case) declines in `test_ui_core.py` (BrowserApprover: no approval, decision `declined`) and `test_agent_slice3.py` (TerminalApprover); `test_agent_slice4c_proposals.py` adds controller-level runs through each approver in which the revision is declined (`confirmation_mismatch`) and only the original executes.
  - **Tests** (logs in git-ignored `runs/fixcr1/`):
    - 23 new: 15 redaction (`test_agent_slice4f_feedback.py`), 2 BrowserApprover, 2 TerminalApprover, 4 controller-level approval;
    - red before the F1 fix: **12 failed, 3 passed** of the 15 redaction tests (the passes are controls: backslash and repr-doubled UNC, and kept URLs/container paths). The F2 tests pass on production by design; their red is the mutation;
    - mutation (d) in scratch copies (`runs/fixcr1/m/`, `mutations.json`; tracked files untouched): browser variant **CAUGHT**, 4 failed, 17 passed; terminal variant **CAUGHT**, 4 failed, 5 passed; every failure is a new test's behavioural assertion (an approval returned, or `['original', 'c1']` executed);
    - full suite with Docker required (`full.log`): **1380 passed, 1 skipped**, exit 0; ruff check and format clean.
  - **Observation (not fixed; outside this pass):** on Windows, a reader holding `pending.json` open while the approver deletes or replaces it makes the approver raise `PermissionError` (seen in the new browser test before its polling was changed). The page polls that file (`ui/worker.py:89`), so a coinciding poll could end a UI run in ERROR (`approver_error`). It fails closed (nothing executes).
  - **No Nebius call, no `.env` read, no live run.**
  - **Next:** a focused Codex re-verification of F1-F3.
- **COMBINED RE-VERIFICATION (runs/cr2/review.md): F2, F3 closed; F1 open (apostrophe in quoted path) -> fixed in `d2110c1`; lead re-runs Codex's unchanged probe.**
  - **F1 as found:** `'C:\Users\O'Brien\private\customer.csv'` gave `'<host-path>'Brien\private\customer.csv'`; SPEC §11 lacked the known-value fragment limit stated in the module docstring.
  - **Fix (`d2110c1`, branch `fix-cr1`; not merged):** a quoted host path ends only at the same quote followed by the end of the line, whitespace or one of `, ) ] } : ;`; any other quote is part of the path. With no such closing quote on the line, the path is redacted to the end of the line, as an unquoted one. SPEC §11 adds "only exact known values are replaced, not fragments of them".
  - **Tests** (logs in git-ignored `runs/fixcr1b/`): 6 new in `tests/unit/test_agent_slice4f_feedback.py` (Codex's `quoted_apostrophe` and `repr_list_apostrophe`, a double-quoted path with an inner `"`, a traceback `File "..."` line, a repr list of two paths, a quote with no valid close); red before the fix: **4 failed, 2 passed** (controls). Codex's 21 probe inputs replayed (`replay.json`): only `quoted_apostrophe` changed, now `'<host-path>'`; the URL, `x//2`, `/work` and `/usr` controls are unchanged. Codex's targeted command (`targeted.log`): **161 passed** (155 + 6), exit 0; ruff check and format clean; 0 tracked `w/crlf`.
  - **No Nebius call, no `.env` read, no live run.**
- **END-OF-LINE REDACTION (`199a173`, the lead's final F1 hardening; merged to `main` by fast-forward, `bc2ef58..199a173`).**
  - **Rule:** on any line where a host path starts (a drive or UNC path in any slash style, quoted or not), everything from that start to the end of the line becomes `<host-path>`. A traceback frame line, `File "<anything>", line <digits>[, in <name>]`, becomes `File "<host-path>"` with its tail kept as written (the name must be an identifier, a dotted name or `<module>`-style, so the kept tail can hold no path). The quoted-path rule is removed. Host-string, environment-value and secret redaction, escaping, bounds and the label are unchanged. Module docstring and SPEC §11 updated.
  - **Tests:** 12 new in `tests/unit/test_agent_slice4f_feedback.py` (quotes followed by a space or a comma inside a path, a repr list, three frame lines kept, two non-frame tails redacted, four over-redaction controls); red before the change: **4 failed, 8 passed** (`runs/fixcr1c/red_summary.log`). Six existing assertions expected text after a path on the same line and were changed to expect the line to end at `<host-path>` (`runs/fixcr1c/changed_assertions.log`): `open('<host-path>', 'rb')`, `open('<host-path>') + x`, `'<host-path>'`, `["<host-path>"]`, `"<host-path>"` and `['<host-path>', '<host-path>']` now end at `<host-path>`; the quoted test was renamed `test_a_quote_inside_a_path_does_not_end_its_redaction`. Codex's 21 cr2 probe inputs replayed: 4 outputs changed, each only by losing the closing quote or bracket after the path; none leaks; the controls are unchanged.
  - **Verification:** targeted command (`runs/fixcr1c/targeted.log`) **173 passed**, exit 0; full suite with Docker required (`runs/fixcr1c/full.log`) **1398 passed, 1 skipped**, exit 0; ruff check and format clean; 0 tracked `w/crlf`.
- **ACCEPTANCE (lead, 2026-10-18).** T-06 is **accepted within its documented scope**, at `199a173` on `main` (DECISIONS.md "Lead decisions, 2026-10-17" item 16), on:
  - **live run 6** (`runs/live6/agent-s01_faulty-877f8245a8a2/`): real NVIDIA model calls (5 requests, 0 schema failures) -> valid actions -> the checks -> an approved candidate executed in the isolated Docker runner -> the trusted re-check NO_VIOLATION_FOUND, four checks FAIL -> PASS (`split.no_group_overlap`, `split.sampling_unit_disjoint`, `split.repeated_measures_rule`, `fit.state_dependencies_within_fold_train`) -> a report citing the evidence;
  - **recorded failure states:** schema failures end ERROR (live runs 2, 3b, 5); budget exhaustion (live runs 4, 6); a declined approval ends NEEDS_INPUT (live run 3). Timeouts are verified offline (provider timeouts `tests/unit/test_agent_slice3.py`, UI scenario 4; execution timeouts `tests/integration/test_runner_contract.py`, `tests/unit/test_candidate_reevaluation.py`);
  - **fixture runs labelled NON-LIVE;**
  - **reviews:** Gates 1-3 PASS (`8c79e5a`, `f327565`); Gate 4 FAIL (`runs/g4/review.md`) resolved by slices 4c-4h; combined review 1 FAIL (`runs/cr1/review.md`) resolved: the re-verification (`runs/cr2/review.md`) closed F2 and F3; F1 is closed by the lead re-running the reviewer's probes after the end-of-line fix.
  - **Limitations:**
    - the input-token figure is an estimate; provider enforcement and billing are unverified;
    - model format reliability varies (schema failures in 3 of 6 live runs);
    - raw replies are stored only from live run 3b onward;
    - candidate-output redaction is best-effort, with the documented limits (SPEC §11);
    - tested on this Windows host only;
    - total estimated live spend about $0.058 ($0.0580317; not billing); key checks 0 for every run.
- **NEXT CARD: SLICE 4 (one authorized live run).**
  - **OWNER:** Claude Code (writer). Codex reviews. The lead decides and authorizes; the owner enters nothing new (the key is already in `.env`).
  - **MODEL DECISION:** STAY on Opus High (live boundary, spending and credential handling).
  - **MODEL / EFFORT:** Claude Opus 5.5 high; Codex High review.
  - **READ FIRST:** this entry's "SLICE 4 PROPOSAL" and "SLICE 4 CONTROLS RESULT"; SPEC §11; DECISIONS.md 2026-10-15 "Hosting probe decisions" (retries count, dispatched reservations kept) and 2026-10-16 "T-03 hosting decisions" (no additional spending authorized).
  - **REVIEW GATES (in order; each is a stop):**
    1. Codex review of the controls at `96f6fc6`, with every finding dispositioned. **Passed at `8c79e5a`** (`runs/g1v3/review.md`; review 1 had failed with two P2, repaired).
    2. The lead's recorded decisions (DECISIONS.md): **recorded 2026-10-16** ("T-06 slice 4 live-run decisions (lead)"). The decisions:
       - the ceilings (12,000 input estimate / 8,000 output);
       - the estimate cap ($0.0648);
       - the maximum authorized expenditure ($0.51 for one run);
       - the pre-run `GET /models` check;
       - the live entry point design.

       The timeout (60 s) and base URL were decided in the Gate 3 dispositions (2026-10-17).
    3. Implementation and Codex verification of the entry point and pre-run check: **GATE 3 PASS at `f327565`** (`runs/g3y/review.md`, under the lead's re-verification dispositions). The original three P2s are closed; the re-verification and follow-up prompt outcomes are dispositioned above. **Next: the lead's explicit go-ahead for ONE pre-run call and ONE live run (at most $0.51), as a separate instruction. Nothing live is authorized by this record.**
    4. After the run: Codex review of the live evidence before T-06 acceptance is considered. **Done 2026-10-17: GATE 4 FAIL** (`runs/g4/review.md`; LIVE RUN 1 and GATE 4 REVIEW above). The user gave the go-ahead for live run 1.
  - **INPUT STATE:** slices 1–3 verified; the controls at `96f6fc6` reviewed; Docker running; the `.env` key present (never printed).
  - **CHANGE (owned paths):**
    - `src/atlas/cli.py`: a live entry point that refuses unless `ATLAS_MODEL_MODE=live` and an explicit authorized amount equal to the configured cap are given;
    - `src/atlas/agent/` (`nebius.py`, `budget.py`, `controller.py`): only what the decisions require;
    - `scripts/nebius_smoke.py` or a new `scripts/live_preflight.py`: the free `GET /models` check, extended to compare the model, prices and context length with the configuration;
    - tests in `tests/unit/` (new or extended slice 4 files) and `tests/integration/`;
    - docs: TASKS.md, STATUS.md, `docs/SPEC.md` §11, `docs/ATLAS_Learning_Guide.md`, DECISIONS.md (the decisions only).

    Not owned: the evaluator, runner, policy, fixtures, `docs/handoff/` and hosting.
  - **ACCEPTANCE:**
    - **Offline, before any request:**
      - tests show that the live entry point refuses without live mode, without the explicit authorized amount, with a mismatched amount and with limits that do not cover the provider-enforced worst case. In each case nothing runs, nothing is sent and no run directory is created;
      - the pre-run check aborts when the model is absent or the prices or context length differ;
      - the full suite passes with Docker required.
    - **The live run (only after gate 3), on `benchmarks/t01/s01_faulty`:**
      - one real NVIDIA model call yields a valid action;
      - the checks run; an approved candidate runs in the isolated runner; it is re-checked; the report cites evidence (T-06 ACCEPTANCE);
      - at most 6 requests;
      - the ledger's estimated total stays within the estimate cap, and the known spend within the authorized maximum;
      - usage, request IDs, the served model and timings are recorded, while the key appears in no log, report or evidence file;
      - the report is labelled LIVE.
    - **Any failure** (invalid output, timeout, budget or spend cap) ends in a recorded state with the original findings intact. A failed live run is reported as measured; it is not retried without a new go-ahead.
  - **RUN (verification commands):**
    - offline: `uv run --locked pytest tests/unit/test_agent_slice4_controls.py tests/unit/test_agent_slice3.py tests/unit/test_agent_slice3_repair.py tests/unit/test_agent_slice3_repair2.py tests/unit/test_agent_controller.py -q` (*existing*), plus the new entry-point tests (*create*);
    - full: `docker info`, then `$env:ATLAS_REQUIRE_DOCKER = '1'; uv run --locked pytest tests -q` (*existing*);
    - pre-run (free, needs gate 3): `uv run --locked python scripts/nebius_smoke.py` dry run (*existing*: `GET /models` and the price check; it sends no completion), or the extended preflight (*create*);
    - live (needs gate 3): `uv run --locked python -m atlas.cli audit benchmarks/t01/s01_faulty --mode agent --live --authorize-spend-usd <decided amount>` (*create*; the flag names are proposed).
  - **EVIDENCE:** the agent log and report (model ID, served model, usage, request IDs, timings, the cost ledger and its spending section) under git-ignored `runs/`; the preflight output; Codex's review record.
  - **HANDOFF:** Codex review at gates 1, 3 and 4; then the lead's T-06 acceptance decision.
  - **RECOVERY:** if a gate fails, repair offline and re-review; nothing live without a fresh go-ahead. If live behaviour is poor, record it as measured (a lower result can be the honest one) and keep the fixture demonstration as the documented fallback.

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
- **RESULT (2026-10-17): built; on `main` by fast-forward; awaiting the combined Codex review.**
  - **Commits** (branch `t07-ui`):
    - `03eab30` UI skills and test dependencies;
    - `c1a8adc` UI spec corrections;
    - `928312b` s01 happy path;
    - `a3a648b` states and polish;
    - `822ee27` acceptance tests and walkthrough.
  - **Scenarios:** Playwright against the running app, scenarios 1, 2, 3, 4 and 6 plus the label checks: **17 passed** with Docker required. Scenario 5 was dropped with T-08.
  - **Full suite at `822ee27`:** **1189 passed, 2 skipped**, exit 0.
  - **Screenshots and logs:** worktree `C:\Users\Lain\source\atlas-t07b`, git-ignored `runs/t07/` (`screens/` at 1440x900, plus `acceptance.log` and `full_suite.log`). Walkthrough: `docs/UI_WALKTHROUGH.md`.
  - **Build decisions:** `docs/UI_SPEC.md` §12, B1–B24. These include the worker process, the typed browser approval over a file channel, one run per server, and the disabled live mode.
  - **Model:** Opus 5.5 high, not Sonnet medium (DECISIONS.md "Lead decisions, 2026-10-17" item 5).

### T-08 Procedures and transfer benchmark
- **CUT (lead, 2026-10-17;** DECISIONS.md "Lead decisions, 2026-10-17" item 2). The Session 5 scenario is dropped. The entry below is kept as the record of what was planned.
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
- **RESULT (2026-10-17): built; on `main` by fast-forward; awaiting the combined Codex review.**
  - **Commits** (branch `t09-har`):
    - `5e4c22f` retrieval and attribution;
    - `c5de1b0` flawed variant and clean control;
    - `13ad59f` audits, containment note and robustness;
    - `f5d76c9` HAR projects in the UI.
  - **Outcomes:** both projects run in Docker through the agent path (`docs/T09_CONTAINMENT.md` §6):
    - `har_flawed` is **VIOLATION_FOUND**, with group, sampling-unit, repeated-measures and fit-state FAILs, and window overlap NOT_ASSESSED;
    - `har_clean` is **NO_VIOLATION_FOUND**; its window-overlap PASS rests only on documented containment, so it is conditional.
  - **Robustness:** three repeats each gave identical outcomes, statuses, evidence and metrics (§7).
  - **Descriptive comparison:** balanced accuracy 0.906 for the flawed variant against 0.875 for the clean control; not causal (DECISIONS.md "Lead decisions, 2026-10-17" item 7).
  - **UI** (`f5d76c9`):
    - both projects are in the catalogue; the flawed one is labelled "ATLAS-authored flawed variant";
    - they show as unavailable, with the retrieval command, when the data is absent;
    - the original's approval is typed in the browser;
    - the UI shows the conditional PASS, the provenance scope and the descriptive comparison.

    Timings with the 35 MB table: 2.5 s to the approval panel; 6.9 s (flawed) and 7.9 s (clean) from approval to the finished report.
  - **Tests:**
    - HAR UI scenarios: **2 passed**;
    - UI acceptance plus UI unit tests: **36 passed**;
    - full suite at `13ad59f`: **1189 passed, 2 skipped**;
    - on `main` at `f5d76c9` with the data retrieved: **1193 passed, 1 skipped**.
  - **Screenshots and logs:** worktree `C:\Users\Lain\source\atlas-t09`, git-ignored `runs/t09/`. That includes `screens/`, with nine `har_*_1440x900.png` files, plus `audit/`, `har_ui_timings.json` and the test logs.
  - **Build decisions:** `docs/T09_CONTAINMENT.md` §8, D1–D10. D9's follow-up, putting the projects in the UI, is done in `f5d76c9`.
  - **Approvals:** the offline evidence runs use the original-only scripted approver; the UI keeps typed approval (DECISIONS.md "Lead decisions, 2026-10-17" item 6).
  - **Open:** the license terms are a user decision before T-12 (item 8).

### T-10 Held-out cases and campaign protocol (Q6)
- **REDUCED (lead, 2026-10-17;** DECISIONS.md "Lead decisions, 2026-10-17" item 2): at most 3 unfamiliar cases. The rest of the entry stands.
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
- **INPUT STATE:** T-03 decision (recorded 2026-10-16: limited hosted plus local Docker; Neon budget store); T-07 UI; verified prices.
- **CHANGE:** deployment configuration, server-side caps on the Neon budget store, judge route or reserved capacity, exhaustion and restoration behavior, labels.
- **ACCEPTANCE:**
  - a signed-out browser completes the curated workflow;
  - caps trigger correctly in a test;
  - the judge route survives exhaustion of the public budget;
  - keys stay server-side;
  - replay is disclosed;
  - **before the hosted app is declared ready** (moved from T-03 stages B and C; DECISIONS.md 2026-10-16):
    - Nebius connectivity from the deployed host is tested and recorded;
    - the full locked environment builds and imports on the host, and that is recorded;
    - each needs its own approval when run;
  - the Neon budget-store integration (accounting, caps, pools, leases, reconciliation, retention) is implemented and reviewed. Until then the caps are planned controls, not a spending ceiling.
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
