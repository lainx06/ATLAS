# Tasks

Task index plus a concise structured entry per task under "Implementation tasks" (playbook Section 24 fields; see `docs/agents/issue-tracker.md`). Each implementation task needs: acceptance criteria, owned files, model/effort, verification commands (or an instruction to create them), and its next review gate. `handoffs/` is only for Section 19 external/substantial transfers.

**RUN convention.** Commands marked *(create)* do not exist yet. The builder must create them and show them working (real output, exit code) before citing them as evidence. Commands marked *(existing)* run today. `uv run --locked pytest` exits 5 when no tests are collected, and that is not a pass.

| ID | Start Here step | Status | Summary |
| --- | --- | --- | --- |
| S-05 | 5 | Done (`7a0f155`) | Git, uv/Python 3.11 env, locked deps, shared state files, import check |
| S-06 | 6 | Done (`4b3cab6`, `6c06d5e`) | Selected skills installed; Matt skill workflow configured |
| S-07 | 7 | Done (uncommitted draft) | Requirements interview → `docs/PRD.md`, `docs/SPEC.md`, `GLOSSARY.md`, this task list |
| S-08 | 8 | Next | Scientific review packet `handoffs/science-01.md`; Gemini review; lead dispositions |
| T-01 | 9 | Proposed; blocked on S-08 | First deterministic slice: fixtures, split + fit-provenance checks, outcome derivation, evidence JSON |
| T-02 | 11 | Proposed | Independent metrics, baselines, temporal checks, remaining policy-v0 assertions |
| T-03 | 11 (early) | Proposed | Hosting and isolated-worker probe (docs/evidence only) |
| T-04 | 10 | Proposed | Nebius access: model list, capped structured-output smoke call |
| T-05 | 10 | Proposed | Isolated runner and hash-bound candidate approval |
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
- **CHANGE:** create `handoffs/science-01.md` (brief, evaluation design, benchmark definitions, the five priority questions from SPEC §14). No secrets, labels or answer keys.
- **ACCEPTANCE:** every Gemini finding has an accepted/rejected/deferred disposition in DECISIONS.md, and T-01 is updated to match. The first build task is unambiguous.
- **RUN:** none (document task).
- **EVIDENCE:** the packet; Gemini's verbatim findings; dispositions.
- **HANDOFF:** the packet to Gemini via upload; the findings back to the lead.
- **RECOVERY:** if a finding needs a design change, update SPEC/PRD and DECISIONS.md before T-01 starts.

### T-01 First deterministic slice (Start Here Step 9)
- **OWNER:** Claude Code (writer). Codex reviews.
- **MODEL DECISION:** STAY on Opus High. Evaluator and provenance logic is core scientific code.
- **MODEL / EFFORT:** Claude Opus 5.5, high (`/model`, `/effort` in Claude Code).
- **READ FIRST:** `AGENTS.md`, `STATUS.md`, `docs/SPEC.md` §3–§8 and §10 (fixture rule), `GLOSSARY.md`, S-08 dispositions.
- **INPUT STATE:** S-08 dispositions recorded, especially the recorder design and bypass tests (SPEC §14.1). No Docker required: only repo-authored trusted fixtures run, in a host subprocess, under the fixture hash allowlist. No candidate or generated code.
- **CHANGE (owned paths):**
  - `src/atlas/contracts.py`, `src/atlas/adapter.py`, `src/atlas/recorder.py`, `src/atlas/checks/split_integrity.py`, `src/atlas/checks/fit_provenance.py`, `src/atlas/checks/metric_ids.py`, `src/atlas/policy.py`, `src/atlas/reports.py`, `src/atlas/runner/trusted.py`, `src/atlas/cli.py`;
  - `benchmarks/sensor_generalization/` (seeded synthetic faulty fixture), `benchmarks/clean_control/`, `benchmarks/unsupported/`;
  - `tests/unit/`, `tests/integration/`.

  Scope:
  - **Policy:** policy-v0 assertions for `unseen_group` only: `split.no_row_overlap`, `split.no_exact_duplicate_across_partitions`, `split.no_group_overlap`, `fit.rows_subset_of_fold_train`, `fit.coverage_complete`, `metric.prediction_ids_match_eval_ids`.
  - **Recorder:** supported operations per SPEC §4.2, recorder per §4.3.
  - **Outcomes and output:** run-outcome derivation per §6, and the evidence JSON per §7.
  - **Limits:** no model calls, no UI, no temporal checks.
- **ACCEPTANCE (observed by running):**
  1. **Faulty fixture** (random-row split and global `SelectKBest(f_classif)` on all rows; claim `unseen_group`):
     - `split.no_group_overlap` FAIL;
     - `fit.rows_subset_of_fold_train` FAIL, with the trace showing `labels_used=true` for `SelectKBest`;
     - run outcome `VIOLATION_FOUND`.
  2. **Clean fixture** (`GroupKFold`, `Pipeline` fit per fold):
     - all implemented assertions PASS with stated coverage;
     - the run outcome follows the S-08 disposition on scoped versus full-policy outcomes (SPEC §14 item 1);
     - any policy-required assertion not implemented in T-01 is shown, never omitted or reported as passed.
  3. **Unsupported cases:**
     - (a) An adapter project whose fit receives a NumPy array → unattributable fit → `fit.coverage_complete` NOT_ASSESSED → `INCONCLUSIVE`.
     - (b) A combined unseen-group-plus-future-time claim → `NOT_SUPPORTED`.
  4. **Negative tests:**
     - a lineage break (reset index) never PASSes;
     - a missing `group_id` under `unseen_group` gives NOT_ASSESSED, not not-applicable;
     - an empty or unassessed required set never yields `NO_VIOLATION_FOUND`;
     - a FAIL whose evidence hash is corrupted becomes ERROR → `INCONCLUSIVE`;
     - `y` supplied to `StandardScaler` gives `labels_supplied=true`, `labels_used=false`;
     - the S-08 bypass tests.
  5. **Mutation check** (review skill): inverting the subset test or the group-overlap test makes at least one test fail.
- **RUN:**
  - *(existing)* `uv run --locked ruff check .`
  - *(existing)* `uv run --locked ruff format --check .`
  - *(create)* `uv run --locked pytest tests/unit tests/integration -q` (must collect and pass)
  - *(create)* `uv run --locked python -m atlas.cli audit benchmarks/sensor_generalization --mode audit` and the same for `benchmarks/clean_control` and `benchmarks/unsupported/*`
- **EVIDENCE:** `runs/<run_id>/` outcome and check JSON for each fixture, with hashes recorded in STATUS.md; the pytest output; the mutation-check log.
- **HANDOFF:** Codex review of the diff and evidence (Start Here Step 9 prompt). No browser packet.
- **RECOVERY:** preserve the failing fixture and output. Two focused repair rounds, then diagnosis by Codex.

### T-02 Independent metrics, baselines, temporal checks
- **OWNER:** Claude Code (writer); Codex reviews.
- **MODEL DECISION:** STAY. Evaluator logic is core scientific code.
- **MODEL / EFFORT:** Claude Opus 5.5 high; Codex Extra high for the review if offered.
- **READ FIRST:** SPEC §5, §6, §8; T-01 evidence; S-08 dispositions on temporal and `same_population` assertions.
- **INPUT STATE:** T-01 accepted and committed.
- **CHANGE:** `src/atlas/checks/{independent_metrics,temporal}.py`, `src/atlas/evaluator.py`, the remaining policy-v0 assertions for all three claim types (the R* rows stay NOT_ASSESSED until S-08 defines them), and fixtures for `future_time` and `same_population`.
- **ACCEPTANCE:**
  - recomputed balanced accuracy/macro-F1 match a hand-computed fixture;
  - the dummy baseline is reported on identical partitions;
  - a post-prediction feature yields `temporal.features_available_at_prediction_time` FAIL;
  - `same_population` with declared overlapping windows but no window bounds gives NOT_ASSESSED;
  - the evaluator runs outside the candidate process and reads its own label copy.
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
- **READ FIRST:** SPEC §12; playbook §8, §9 (Example two).
- **INPUT STATE:** T-02 accepted; T-05/T-06 for executed reuse.
- **CHANGE:** `src/atlas/procedures/`, `benchmarks/procedure_transfer/` (Variants A and B).
- **ACCEPTANCE:**
  - admission refuses records with ERROR or NOT_ASSESSED required assertions;
  - Variant A gives `reuse_succeeded`, with the assertions re-executed;
  - Variant B gives `reuse_rejected`, naming the failed prerequisite;
  - a fresh attempt after a rejection is recorded separately.
- **RUN:** *(create)* `uv run --locked python -m atlas.cli procedures check <id> benchmarks/procedure_transfer/variant_b`
- **EVIDENCE:** run JSON per variant.
- **HANDOFF:** Codex review; Gemini on claims.
- **RECOVERY:** two focused repairs, then Codex diagnosis.

### T-09 Real-data example and clean control
- **OWNER:** Claude Code (writer); Gemini reviews the claims.
- **MODEL DECISION:** STAY on Opus High (scientific protocol).
- **MODEL / EFFORT:** Claude Opus 5.5 high; Gemini Argon High.
- **READ FIRST:** SPEC §14.4 disposition; playbook §9 "Real data and clean controls"; dataset license page (S14).
- **INPUT STATE:** S-08 answer on UCI HAR; T-02 accepted.
- **CHANGE:** `benchmarks/real_sensor/` (retrieval script and attribution; no committed raw data unless the license permits); robustness reporting.
- **ACCEPTANCE:**
  - license and attribution are recorded;
  - subject IDs are preserved;
  - no invented timestamps;
  - the outcome and its limitations are reported as measured.
- **RUN:** *(create)* the retrieval and audit commands.
- **EVIDENCE:** run JSON; the limitations section.
- **HANDOFF:** Gemini review of the claims.
- **RECOVERY:** if the dataset is unsuitable, document why and pick the next licensed candidate with the lead.

### T-10 Held-out cases and campaign protocol (Q6)
- **OWNER:** Codex (separate session, outside this repo) authors and validates the cases. Claude writes only the predeclared campaign protocol and never receives case contents, answer keys or case-specific feedback.
- **MODEL DECISION:** SWITCH for case authoring (Codex, separate session). Claude stays Opus High for the protocol text.
- **MODEL / EFFORT:** Codex High (authoring); Claude Opus 5.5 high (protocol).
- **READ FIRST:** DECISIONS.md Q6; SPEC §8; playbook §9.
- **INPUT STATE:** adapter and policy versions frozen enough to state in the freeze record (after T-02).
- **CHANGE (this repo):** `docs/EVALUATION.md` campaign protocol: model and settings, budgets, repetitions, infrastructure-failure handling, reporting of all results.
- **ACCEPTANCE:**
  - the hashes, contract/evaluator versions and freeze date are recorded in DECISIONS.md before any use;
  - the protocol is committed before results are revealed.
- **RUN:** none in this repo until the campaign.
- **EVIDENCE:** freeze record.
- **HANDOFF:** Codex runs the campaign at release-candidate time.
- **RECOVERY:** if a case is used for debugging, retire it and obtain a replacement before a fresh held-out claim.

### T-11 Three-way comparison pilot
- **OWNER:** Claude Code (writer); Gemini reviews the claims.
- **MODEL DECISION:** STAY on Opus High (evaluation design).
- **MODEL / EFFORT:** Claude Opus 5.5 high; Gemini Argon High.
- **READ FIRST:** DECISIONS.md Q4; PRD "Benchmarks"; playbook §9 "Measuring agent value".
- **INPUT STATE:** T-06 and T-08 accepted; prices verified (T-04/T-03).
- **CHANGE:** `evaluation/` harness for `audit` / `agent` / `agent+memory`, with matched inputs, policy, tools, model settings and budgets, randomized order and recorded cache state.
- **ACCEPTANCE:**
  - three paired repetitions on Variant A;
  - detection quality reported across all modes, and repair success and token use across the agent modes;
  - procedure-creation cost reported separately;
  - results reported as descriptive.
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
