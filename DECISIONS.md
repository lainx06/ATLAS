# Decisions

Brief dated decisions with reasons. Reopen only with new evidence.

## 2026-10-14 — Setup (Start Here Step 5)
- **Workspace:** native Windows, single local folder `C:\Users\Lain\source\atlas`. No WSL, no cloud copy. (KICKOFF.md)
- **Python 3.11 baseline:** uv-managed CPython 3.11.17, pinned in `.python-version`. The only system Python was 3.12.10; using uv-managed 3.11 keeps the baseline without touching system installs. `requires-python = ">=3.11"`.
- **Package layout:** `uv init --lib` (src layout, `uv_build` backend, importable `atlas` package). No `atlas` console entry point yet; add `[project.scripts]` when the CLI is actually implemented rather than ship a stub executable.
- **Model client:** `openai` Python package, configured only with the Nebius base URL from env (Nebius Token Factory is OpenAI-compatible per playbook Section 7). Reason: avoid a hand-written HTTP client; revisit if Nebius-specific features require it.
- **Env-file loading:** `python-dotenv` for local `.env`. Credentials stay out of Git (`.gitignore`) and out of candidate containers.
- **Ruff excludes `docs/handoff/`:** Ruff 0.17 formats Markdown files too; excluding the handoff keeps the original documents unmodified.
- **Writer:** Claude Code is the primary writer from Step 5 (STATUS.md WRITER).

## 2026-10-14 — Skills and Step 7 workflow (Start Here Step 6)
- **Selective pinned skill copies:** 8 skills (Matt: setup-matt-pocock-skills, grill-with-docs, to-spec, plus companions grilling and domain-modeling; Addy: code-review-and-quality, debugging-and-error-recovery, test-driven-development) and 3 Addy shared references, copied from pinned commits into `.claude/` and `.agents/` by `scripts/sync_skills.py`. No plugins, packs, or hooks. Pins and statuses are in docs/TOOLING.md.
- **Step 7 uses local files:** durable specifications live in `docs/` (e.g. `docs/PRD.md`, `docs/SPEC.md`); `TASKS.md` is the task index. `.scratch/` is **not** the canonical spec location. When a Matt skill would "publish to the issue tracker", write to these local files instead. Reason: ATLAS forbids publishing without approval, and the project already has its source-of-truth files (AGENTS.md "Source of truth").
- **Instruction placement:** shared workflow instructions belong in `AGENTS.md`. `CLAUDE.md` stays a short pointer plus Claude-specific instructions. If `/setup-matt-pocock-skills` proposes an `## Agent skills` block for CLAUDE.md, put the shared content in AGENTS.md instead and keep CLAUDE.md a pointer. Reason: one shared rule set for Claude and Codex, no duplication.
- **Task entries in `TASKS.md` (correction):** an earlier same-day decision to put every task card in `handoffs/` was superseded. The lead had read playbook Revision 4; the local handoff documents are Revision 5 and are authoritative. Per Revision 5 Section 24, `TASKS.md` holds the index and concise structured task entries; per Section 19, `handoffs/` is only for external/substantial transfers, and routine local Claude/Codex reviews use `TASKS.md`, `STATUS.md`, the reviewed checkpoint/diff, and actual evidence.
- **ADRs vs DECISIONS.md:** routine decisions stay in `DECISIONS.md`. Create `docs/adr/NNNN-slug.md` only for consequential architectural decisions (domain-modeling's test: hard to reverse, surprising, real trade-off), each with a dated pointer here. No empty ADRs or glossary are created in advance.
- **Matt skill configuration:** `/setup-matt-pocock-skills` was run with an "other" tracker: local files (specs in `docs/`, task index and entries in `TASKS.md`), single-context domain docs, no triage labels (`triage` not installed). Output: `docs/agents/issue-tracker.md`, `docs/agents/domain.md`, and an `## Agent skills` block in AGENTS.md (not CLAUDE.md, overriding the skill's default per the instruction-placement decision above).

## 2026-10-14 — Step 7 requirements interview (running record; consolidated into docs/PRD.md and docs/SPEC.md at the end)
Process: `grill-with-docs` was followed manually. Its body is "Call the Skill tool twice, for grilling and domain-modeling", and both companions loaded natively. The `/grill-with-docs` slash command itself was not invoked; it arrived as pasted text. User override of `grilling`: one question at a time.
- **Q1, claim types:** V1 supports exactly three: `same_population`, `unseen_group`, `future_time`. A combined unseen-group-plus-future-time claim is unsupported in V1.
  - `same_population` means new observations from the declared sampling population, with no unseen-group or future-time generalization claimed. The claim records its sampling unit and dependence assumptions.
  - A random row split is conditionally appropriate under `same_population`, never automatically valid. Known duplicates, overlapping windows, or temporal dependence are not waived by choosing this claim type, and missing evidence stays visible as NOT_ASSESSED where applicable.
  - The `unseen_group` clean control is kept.
  - An unsupported claim type is a **run-level** `NOT_SUPPORTED` outcome. A supported check lacking evidence is a **check-level** `NOT_ASSESSED`. Terms are in GLOSSARY.md.
- **Q2, run outcome:** every run has one headline that summarizes the evaluation checks. It says nothing about whether the underlying scientific claim is true. Plain-language labels and limitations are displayed beside it.
  - `NOT_SUPPORTED`: the claim or project is outside the supported contract.
  - `VIOLATION_FOUND`: at least one applicable required assertion has a valid, evidence-backed FAIL.
  - `INCONCLUSIVE`: no established violation, but required evidence or assessment is incomplete.
  - `NO_VIOLATION_FOUND`: all applicable required assertions passed within explicitly stated coverage.
  - Rules:
    1. An independent check's ERROR does not erase a valid finding; both the finding and the incomplete coverage are shown prominently. A result that depends on failed or corrupt evidence cannot count as an established FAIL or PASS.
    2. Missing metadata never makes a required check "not applicable".
    3. An empty set of assessed required assertions cannot yield `NO_VIOLATION_FOUND`.
    4. Required assertions come from a versioned evaluation policy, not an agent-selected subset.
    5. Robustness stays descriptive until a justified rule is predeclared.
- **Q3, adapter and provenance:** projects supply a table, a manifest and their own `evaluate.py`, which uses the ATLAS adapter and runs in the isolated container under trusted instrumentation. Static suspicions about unadapted code stay separate from evidence-backed check results and never affect run outcomes. The adapter must let ATLAS observe the deliberately flawed development evaluation and test a correction to `evaluate.py`. Boundaries:
  1. An enumerated, tested set of supported estimators, transformers and adapter operations. No promise of intercepting every scikit-learn fit, and no universal provenance coverage.
  2. Pandas output helps preserve row IDs but does not prove lineage. The spec defines how supported operations preserve and validate row identity. Lost, rebuilt or unverifiable lineage never PASSes.
  3. Record which rows and labels were supplied to supported fit operations, distinguishing labels supplied from labels demonstrably used by a known supervised component.
  4. Trusted metric recomputation runs outside the candidate process. Final-holdout labels never enter candidate mounts or model prompts. Development-evaluation labels (available to the project) are distinct from the untouched final holdout.
  5. A read-only recorder imported into candidate Python is **not** a tamper-proof observation boundary; this is documented as a known limitation. Missing traces cannot establish that no unobserved fits occurred.
- **Q4, code revision (full local workflow):** the model writes a free-form unified diff limited to `evaluate.py`. It may never touch the adapter, the evaluator, labels, the policy, dependencies, the manifest or instruction files. Public-demo behavior is decided in Q5.
  - **Before execution:** validation (path allowlist, size cap, Python parse, symlink/path-escape rejection) is hygiene, not the boundary.
  - **Approval:** you explicitly approve each exact candidate diff before its isolated execution. Approval is bound to the candidate hash, so a changed candidate needs fresh approval.
  - **Limits:** at most two revisions per run. Without working isolation, nothing executes.
  - **What isolation does and doesn't prove:** container restrictions reduce execution risk. They do not by themselves prove provenance integrity or scientific correctness, and the Q3 instrumentation limitations still apply.
  - **The model never declares success;** outcomes come from the evaluation policy.
  - **Comparison modes:**
    - Deterministic audit: the detection and reporting baseline, with no repair.
    - Agent without memory: the standard bounded patch workflow.
    - Agent with memory: the same workflow and capabilities, plus access to validated procedures.
  - **Memory:** optional guidance, not a forced template. An inapplicable procedure's reuse is rejected explicitly. A fresh repair attempt is recorded separately from successful reuse.
  - **Fairness:** inputs, policy, tools, model settings and budgets are matched between the agent modes. Retrieval and prerequisite checking count in the memory mode's budget, and procedure-creation cost is reported separately. The deterministic mode has no model-token budget.
  - **What is compared:** detection quality across all three modes; repair success and token savings between the two agent modes only.
- **Q5, demo and judge access:** the baseline delivery plan is a limited hosted demo plus a full local build. At the early hosting probe, full hosted execution through a separately isolated worker is also evaluated, and adopted only if isolation, cost, reliability and delivery time are demonstrated to be practical.
  - **Limited hosted mode:**
    - Generated diffs are marked "not executed here".
    - Trusted corrected-protocol results are labeled separately and never imply they validate the displayed generated patch.
    - Actual patch execution is demonstrated in the isolated local build, and the video identifies which environment is shown.
  - **Judge access:**
    - Bounded workloads with server-side cost controls; all provider keys stay server-side.
    - Replay is a disclosed fallback, not a substitute for a working judging path.
    - A separate judge-access route or reserved capacity, so public traffic cannot exhaust live judging access.
    - Defined behavior when budgets are exhausted, and how access is restored through the end of judging.
  - **Correction to the option framing:** a local build could use an authenticated, controlled inference backend without exposing a provider key or making judges buy credits. (a) was chosen for ease of access, not because (c) is impossible.
  - **Budget:** $30 inference and $20 hosting are planning allowances, not authorization to purchase.
- **Q6, held-out cases:** two held-out cases, one flawed and one clean, authored and validated by Codex in a separate session, outside the builder's repo.
  - **Separation:** procedural, not access-enforced. The independent author/evaluator may inspect and validate the cases. The builder must not receive their contents, answer keys or case-specific feedback before the final evaluation.
  - **What the runtime sees:** the permitted project inputs needed to assess each case. Expected findings and final held-out labels are accessible only to the trusted evaluator.
  - **Freeze:** the cases are frozen before any use for development feedback, recording hashes, contract/evaluator versions and the freeze date. Hashes establish file identity, not independence.
  - **Predeclaration:** the evaluation protocol, model and settings, budgets, repetitions and the handling of infrastructure failures are fixed before results are revealed. "Run once" means one predeclared evaluation campaign, not picking a successful attempt. All scheduled results are reported, including failures.
  - **Retirement:** if case-specific findings guide fixes or prompt changes, those cases are retired from the untouched holdout, and replacements are obtained before any fresh held-out claim.
  - **Scope of the evidence:** two cases give limited descriptive evidence, not broad proof of generalization.
  - **Correction to the option framing:** Gemini can generate code; whether it can execute and independently validate the cases depends on its available environment. It was not chosen as the author.
- **Interview complete (2026-10-14):** the six decisions above are settled and consolidated into docs/PRD.md and docs/SPEC.md (Step 7 drafts, pending Step 8 scientific review).

### Open hosting and access checks (before choosing a host or enabling paid usage)
- Nebius promotional credit amount, arrival and **expiry** relative to the end of judging (Dec 15, 2026).
- Actual per-token prices for the selected NVIDIA model; cost per bounded demo run.
- Cost and reliability of keeping judging access available through Dec 15 (hosting plan limits, sleep/cold-start behavior).
- Whether a candidate host can run a separately isolated worker meeting the execution contract; its cost and delivery time.
- Mechanism for the judge-access route or reserved capacity (e.g., separate credentialed URL or quota), and the restoration procedure when budgets run out.
- Server-side cost-control implementation (per-session, per-route and daily caps) and how exhaustion is shown to users.

### Step 8 scientific-review agenda (closed 2026-10-14)
- (from Q3) Exact instrumentation design and bypass tests for the in-process recorder. Resolved by F1 below.
- The five packet questions in `handoffs/science-01.md` (the reviewed snapshot, preserved unchanged) are resolved by F1–F5 below. The remaining gated items, with owners, are in docs/SPEC.md §14.
- **ADR pointer (2026-10-14):** Q3's architecture is recorded as docs/adr/0001-project-owned-evaluation-with-in-container-recorder.md, now accepted with the F1 narrowing.

## 2026-10-14 — Step 8 scientific review dispositions
Gemini reviewed `handoffs/science-01.md` (commit `698ffd8`; preserved unchanged as the reviewed snapshot). The lead supplied the dispositions below. Gemini's verbatim findings were not provided to the builder and are not stored in the repo. Applied to docs/SPEC.md (policy `policy-v1`, §4, §5, §6, §8, §12, §14, §17), docs/PRD.md, GLOSSARY.md, ADR 0001 and TASKS.md (T-01, T-02, T-08–T-11).

- **F1, provenance — ACCEPTED, with a narrower contract.**
  - **Identity vs ancestry:** a valid pandas index establishes row identity, not preprocessing ancestry. Index preservation alone never establishes `fit.coverage_complete`.
  - **Bounded supported path:** adapter-loaded data → enumerated operations and supported row selection (`take`) → predictions. Along it the recorder records operation/instance identity, fitted-state versions, input/output lineage and the training rows contributing to each fitted state.
  - **Coverage gaps:** unexplained mutation, reconstructed frames, unsupported operations and missing prediction ancestry are coverage gaps.
  - **Fingerprints** detect unexpected changes; they don't prove arbitrary preprocessing was observed. The in-process recorder limitation stays explicit.
  - **Where contamination is judged:** fitted-state dependencies are checked against the training partition of the fold where the state is **used** (transforms and predictions). Cross-fold instance reuse is a violation only when the reused state learned from rows outside that fold's training set. Unknown ancestry → NOT_ASSESSED, not an invented FAIL.
  - **Zero fits:** zero recorded fits cannot give complete coverage. Every evaluated fold needs an observed supported classifier fit and a traceable prediction path; a fit count alone is insufficient.
  - **Missing results:** missing required results are materialized as NOT_ASSESSED with a specific reason (including `unimplemented_assertion`, `not_executed`). Invalid evidence is ERROR, and valid independent FAILs are preserved.
  - **Packet Q1(b), the T-01 outcome:** there is no scoped clean outcome. Unimplemented required assertions make a clean run INCONCLUSIVE.
- **F2, factorial benchmark — ACCEPTED (comparison distinctions); REJECTED (forced effects).**
  - The 2×2 uses one generated dataset and predeclared seeds. Within a split protocol, the global and fold-local runs use identical partitions and matched model settings.
  - Across split protocols, differences are shown as protocol differences, with no causal score-subtraction claim.
  - Planted violations are shown by overlap and fitted-state-dependency evidence. A score drop, changed selected features or changed predictions are not required; zero and reversed differences are reportable.
  - Generator settings are fixed and recorded before measurement; Gemini's example numbers are not adopted as established. Robustness is descriptive in V1.
- **F3, dependence and temporal semantics — PARTIALLY ACCEPTED.**
  - **Sampling unit:** when a claim treats subjects or sessions as independent draws, the unit identifier is required and the unit must not cross partitions (`split.sampling_unit_disjoint`); a missing identifier → NOT_ASSESSED.
  - **Repeated measures:** not automatically equated with unseen-group generalization. Without a supported assessment rule, the coverage gap is exposed (`split.repeated_measures_rule` → `no_supported_rule`).
  - **Windows:** source-stream identity plus half-open intervals `[start, end)`. A positive shared span in the same stream is overlap; missing stream identity is never guessed.
  - **REJECTED:** "non-interleaving implies independence". `split.temporal_separation` verifies a declared separation rule, not statistical independence, and an undefined rule stays NOT_ASSESSED with a milestone (T-02).
  - **`future_time`:** consistent time units and a documented reference time; per-feature availability timestamps or offsets; training-label availability (horizon plus reporting delay); a per-fold training cutoff and a nonnegative declared gap. Required: training labels available by the cutoff, cutoff + gap no later than the first evaluation prediction, and features available when used. The counterexample (training prediction 100, label available 150, evaluation prediction 120) must not pass.
  - **Variant B:** procedure reuse is rejected on claim mismatch; a temporal-feature violation is reported separately, only when its check establishes one.
  - **REJECTED:** a blanket three-group minimum. Overlap checks can establish violations with fewer groups. Splitter/estimator minimum requirements and class support are reported (`split.class_support`, descriptive), never as fabricated split violations.
- **F4, UCI HAR — ACCEPTED as a scoped example; shortcuts REVISED.**
  - Claim `unseen_group` by subject. The official subject-based test partition is reserved from development and tuning; development uses grouped folds within the training subjects.
  - Any deliberately flawed evaluation is described as ATLAS-authored.
  - **Windows:** window overlap may PASS through disjoint groups only with documented source-containment evidence, recorded together with its dependency on the group-disjointness result. Claim type alone is insufficient; otherwise NOT_ASSESSED.
  - **Provenance scope:** coverage begins at the supplied feature table.
  - **Source:** the lead verified https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones (subject-based splitting, overlapping windows, CC BY 4.0; attribution required). Global fitting of upstream normalization has **not** been established.
  - **Timestamps:** absent, so temporal assertions can't be established. The general missing-evidence rule is unchanged.
- **F5, scoring and comparisons — ACCEPTED, with a revised metric comparison.**
  - **Scheduling:** the deterministic controller schedules the full required set for the original evaluation and each executed candidate. Agent choices cannot remove assertions, and budget exhaustion cannot hide missing results.
  - **Scoring:**
    - findings are scored per case and canonical assertion ID, deduplicated, with fold-level evidence retained;
    - expected violated assertions are defined before measurement;
    - TP/FP/FN, coverage gaps and errors are reported;
    - on clean cases, false-positive counts and the false-violation run rate;
    - no manufactured precision/recall when a denominator is zero.
  - **Transfer repetitions:** the procedure store is frozen and hashed before the three paired transfer repetitions; each uses the same immutable store with fresh run state, and no target-specific admissions happen between them. All scheduled trials, failures, budgets and creation costs are reported. The evidence is descriptive only.
  - **REJECTED:** a tolerance inferred from JSON float decimals. Reported metrics are canonical numerics with a named definition, partition/fold and aggregation, compared with a fixed, versioned **absolute tolerance of 1e-6** (no relative tolerance). Nonfinite or out-of-range values are rejected, and display rounding is separate. This is an engineering comparison rule, not a scientific confidence threshold.
- **L1 (lead), procedure admission:** every applicable required assertion must have a valid PASS (no FAIL, ERROR or NOT_ASSESSED) before `verified_for_recorded_scope`. No empty required set or incomplete coverage qualifies. Reuse success requires the same checks to pass after execution.
- **L2 (lead), duplicate observations:** identical feature/target values identify candidate duplicates only. A violation needs source-observation identity (`observation_id`) or documented duplication evidence (`known_duplicates`); unresolved equal rows → NOT_ASSESSED `unresolved_duplicate_candidates`. `split.no_exact_duplicate_across_partitions` is replaced by `split.no_shared_source_observation`. A clean fixture with independently observed identical-valued rows must not receive a violation.
- **T-01 definition:**
  - **Scope:** trusted repo-authored synthetic fixtures; `unseen_group`; split/group integrity; bounded fit provenance; prediction-ID matching; evidence JSON; deterministic outcome derivation.
  - **Excluded:** model calls, generated-code execution, hosted deployment, any Docker prerequisite.
  - **Clean outcome:** the clean fixture reaches `NO_VIOLATION_FOUND` only when all its required assertions are implemented and pass. Truthful dependence declarations are never removed to get that outcome.
  - **Expected statuses** are recorded per assertion in TASKS.md. All tests are planned, not run.
- **Assertion-ID changes (`policy-v0` → `policy-v1`):**
  - Renamed: `fit.rows_subset_of_fold_train` → `fit.state_dependencies_within_fold_train`; `split.no_exact_duplicate_across_partitions` → `split.no_shared_source_observation`; `split.no_overlapping_windows_across_partitions` → `split.no_window_overlap`; `split.temporal_dependence_respected` → `split.temporal_separation`.
  - Replaced: `split.chronological_order`, `temporal.label_horizon_respected` and `temporal.features_available_at_prediction_time` → `temporal.training_labels_available_by_cutoff`, `temporal.cutoff_precedes_evaluation`, `temporal.features_available_when_used`.
  - Added: `split.sampling_unit_disjoint`, `split.repeated_measures_rule`, `split.class_support` (descriptive).
  - The five-check product scope is unchanged.

## 2026-10-14 — Repeated-measures policy clarification (policy-v1.1; T-01 review)
Lead decision, accepted after Codex's containment probe (`runs/review-t01-containment/`) showed `split.repeated_measures_rule` FAILing by inheriting an aggregate group FAIL that only unknown-session rows supported.
- **Scope:** containment is assessed over rows participating in the declared folds.
- **Known mappings:** consistent known mappings may support a same-fold group-overlap witness for FAIL, but never establish complete containment when assignments are missing. Both witness rows must have known repeated-unit and group IDs. An observed mapping contradiction prevents the contained-group route; missing assignments alone don't erase an otherwise supported witness.
- **Route A, sampling unit:** when the repeated unit is the declared independent sampling unit, its known train/eval overlap is computed within each fold; group assignments are not required.
- **Route B, contained group** (`unseen_group`): a unit observed in several groups → NOT_ASSESSED `no_supported_rule`; otherwise group intersections within each fold from rows with both identifiers known, preserving row, unit and group IDs and the fold.
- **Statuses, either route:** a supported witness → FAIL, with missing counts disclosed; no witness plus missing assignments → NOT_ASSESSED `missing_metadata`; PASS needs a nonempty, complete, supported assessment; no folds or no participating rows → NOT_ASSESSED `not_executed`; invalid evidence → ERROR. Identities are never combined across folds. Multiple declared units aggregate without hiding valid FAILs or incomplete coverage.
- **No inheritance:** aggregate group/unit statuses are never substitutes for witnesses. A group-separation witness is not labeled same-session overlap or label leakage.
- **Versioning:** policy `policy-v1` → `policy-v1.1` (assertion IDs unchanged), per SPEC §5's rule that policy changes are versioned code changes.

## 2026-10-14 — Evaluation-fold prerequisite (policy-v1.2; T-01 review)
Lead-approved rule, after Codex's `runs/review-t01-rm-v11/` boundary input (`empty_eval_evaluator_boundary`) showed empty evaluation partitions reaching `NO_VIOLATION_FOUND` with every assertion passing vacuously.
- **Rule:** every declared evaluation fold must contain at least one evaluation row. It is an assessment prerequisite, not a claim that one row is scientifically adequate.
- **Assertion:** `split.evaluation_folds_nonempty`, required for every claim type and enforced by the deterministic evaluator through the versioned policy.
- **Statuses:** valid evidence of an empty evaluation partition → NOT_ASSESSED with reason `empty_evaluation`; zero declared folds → NOT_ASSESSED `not_executed`; missing or corrupt split evidence → ERROR; PASS only when every declared evaluation fold is nonempty. An independent valid FAIL still determines `VIOLATION_FOUND`.
- **Versioning:** policy `policy-v1.1` → `policy-v1.2`. All T-01 fixtures truthfully declare nonempty evaluation folds and were not changed.
- **Same review, also fixed:** with the repeated unit and the group on the same column, route B of `split.repeated_measures_rule` no longer raises. The two semantic roles are kept while physical column selection is deduplicated; policy-v1.1 semantics are unchanged.

## 2026-10-14 — Initial model and response approach (T-04)
Lead decision, based on the free `GET /models?verbose=true` and two user-authorized smoke calls (2026-10-15 UTC; evidence in git-ignored `runs/nebius_smoke/`; details in STATUS.md "Nebius smoke").
- **Initial model:** `nvidia/nemotron-3-super-120b-a12b` (`ATLAS_MODEL_PRIMARY`). Listed price $0.30 / $0.90 per 1M input / output tokens, $0 per request; context 262,144; advertised features `tools` and `reasoning`. Reasoning tokens are counted in `completion_tokens` (billed at the output rate); Nebius documents `max_completion_tokens` as capping them. Chosen over Ultra on cost and over Nano/Lightning on expected capability; that capability is assumed, not measured.
- **Initial response approach:** prompt-requested JSON, validated against a task-specific strict Pydantic schema (`extra="forbid"`, strict types, literal values where fixed), over the whole reply with only surrounding whitespace removed. No extraction from prose, no repair.
- **Application validation, not provider-enforced structured output:** no NVIDIA model on Nebius lists `json_mode` or `structured_outputs`, so no `response_format` is sent and nothing on the provider side constrains the format. This applies SPEC §11's "structured JSON output where supported".
- **Invalid output:** invalid or incomplete output (failed validation, `finish_reason` other than `stop`, missing content, transport error or timeout) never authorizes an action and never counts as success; it is recorded as a schema failure or error (SPEC §11). Any future retry counts against the existing attempt and spending ceilings (SPEC §11: 1 retry per transient model call, 6 model calls per run); no retry may raise a cap.
- **Not yet tested:** diagnosis quality, tool use (`tools` is advertised but unused) and repair quality. The smoke calls show only connectivity, pricing behavior and compliance with one fixed JSON object, once. Compliance rates and task quality need the T-06/T-10/T-11 measurements.

## 2026-10-15 — Repeated-measures scope for V1 (SPEC §14; T-02 input)
Lead scope decision, closing the SPEC §14 question "whether V1 adds a supported rule for repeated measures not covered by unit or group disjointness".
- **No new rule:** V1 adds no repeated-measures rule beyond the existing routes of `split.repeated_measures_rule` (policy-v1.1): A, the sampling unit, and B, the contained group.
- **Other dependence structures stay unsupported** under the existing policy. A declared repeated unit that neither route covers stays NOT_ASSESSED `no_supported_rule`, and the run cannot be `NO_VIOLATION_FOUND` (SPEC §6).
- **Not independence:** `split.no_window_overlap` and `split.temporal_separation` verify declared stream/interval and separation rules. They must not be presented as proof of statistical independence, in reports, the UI or documentation (SPEC §15).
- **Versioning:** no assertion's semantics change, so the policy stays `policy-v1.2`. The T-02 contract proposal (`docs/specs/t02-contract.md`, awaiting review) is separate from this decision.

## 2026-10-15 — T-02 contract dispositions (policy-v1.3, manifest schema 0.3)
Lead review of the complete proposal `docs/specs/t02-contract.md`. Approved with the corrections below; the contract text there and SPEC §3, §4.2, §5 and §8 now follow these dispositions. T-02 is authorized for implementation on trusted fixtures only (no inference calls, no Docker-runner integration). It is not accepted.
1. **Time representation and scope (approved with corrections).**
   - Times are finite numbers in one declared unit. There is no date parsing and no automatic unit conversion, and booleans are excluded.
   - Schema 0.3 requires an explicit `time_basis.scope` (`global` or `per_stream`) whenever `time_basis` is supplied. In legacy 0.2, an absent scope means **unspecified**; it does not assert per-stream clocks.
   - Global comparability is never inferred from `reference_time` prose.
   - Missing or `per_stream` scope blocks only comparisons that need cross-stream comparability; it does not block comparisons within a known stream.
   - Feature availability compares one row's availability with that same row's prediction time on its declared local clock, as do offsets, so it is not marked NOT_ASSESSED merely because the clock is per-stream or unspecified.
   - The two single-cutoff-per-fold checks (`training_labels_available_by_cutoff`, `cutoff_precedes_evaluation`) keep the global-clock requirement.
2. **Invalid reported metrics (approved).** Malformed, nonfinite, out-of-range or boolean manifest values are rejected at intake, through the existing `NOT_SUPPORTED` path, with a specific validation explanation. Missing or corrupted runtime evidence is different and gives ERROR.
3. **Separation direction (approved).** Two-sided, within each fold, only for the applicable `same_population`/`unseen_group` rule. `future_time` stays directional and separate. A one-sided rule would exclude designs that train after evaluation; it would not fail every blocked-CV design.
4. **Named separation times (approved).** The rule must declare its basis, `prediction_time` points or `window` intervals; it is never guessed. The point and interval distance formulas and the equality rules stand.
5. **Window routes (approved with qualifications).**
   - **Route D (direct)** may establish no overlap from complete stream identities and disjoint stream membership, without needing unused bounds. The evidence that established each PASS is recorded.
   - **Route C (containment)** is conditional on *documented* containment; it is not independent verification. Its source, its statement, and its dependency on a valid `split.no_group_overlap` PASS are recorded prominently. Non-empty strings show only that a declaration was supplied, not that its source proves the claim. Sources are never fetched. Actual UCI HAR containment evidence still needs the T-09 review.
   - A contradiction disables route C. It never suppresses a valid direct-route FAIL or an independently complete direct assessment.
   - **Lead policy change:** any window whose bounds are needed must have `start < end`. Zero-length or reversed windows are unusable metadata, not evidence of a successful assessment.
6. **Metrics (approved, with explicit completeness rules).**
   - The per-fold class sets and formulas, the unweighted `mean_over_folds`, and pooled (fold, row) observations stand. Pooled repeated rows count once per evaluation occurrence, not once per unique row.
   - An empty, invalid or missing required fold is never silently omitted from an aggregate. An incomplete aggregate cannot support PASS, and its reason is reported. Valid per-fold results may still be shown separately.
   - Comparison is `abs(reported - recomputed) <= 1e-6` in float64, with no relative tolerance, no rounding and no undocumented epsilon.
   - Equality and the adjacent representable values are tested, for example with `recomputed = 0`, as is `5/9 + 1e-6` under the literal rule. A decimal-intended equality may fall on either side after binary representation.
7. **Baseline (approved).**
   - The baseline predicts the most frequent training class, with ties broken by the declared `class_map` order. This tie rule is not claimed to match scikit-learn's.
   - Empty or invalid training labels make the baseline unavailable; no prediction is invented. Baselines stay descriptive, and the linear baseline is explicitly deferred.
   - Splitter minimum requirements are reported as unavailable, and SPEC §4.2's claim that they are recorded is corrected. Avoiding a mutation-check target is not a reason to leave documentation inaccurate.
8. **Versions (approved).**
   - Manifest schema 0.3, with 0.2 compatibility as qualified in item 1. Unsupported schema versions are rejected.
   - The policy becomes `policy-v1.3`. Historical evidence is not rewritten.
   - `policy_version` does not uniquely identify implementation code; task records keep the reviewed commit.
9. **s07 (approved).** Its `split.no_window_overlap` may become PASS, and its outcome `NO_VIOLATION_FOUND`, once the implementation shows that every required assertion passes. Fixture bytes and the historical policy-v1.2 results are preserved, and required-but-unimplemented assertions keep independent test coverage.

## 2026-10-15 — Hosting probe decisions (T-03; SPEC §11, §13)
Lead decisions after reading `docs/HOSTING_PROBE.md`. T-03 is not accepted; these settle design points, not the host choice.
- **Run limit includes retries.** The six-call limit (SPEC §11) counts every attempted inference request, including each retry. A retry is therefore not an extra call, and the proposed worst case stays at 6 requests (about $0.051 per run at the proposed ceilings, not $0.102). A request that was dispatched counts even if it fails or returns no usage.
- **Dispatched reservations are not released by lease expiry.** A budget reservation exists before a request is dispatched. Once dispatched, its lease expiring is not a reason to release it: if its usage is unknown (crash, timeout, lost response), the ceiling-cost reservation stays reserved until reconciled with the actual usage. A reservation that was never dispatched may expire. This replaces the draft lease rule in `docs/HOSTING_PROBE.md` §5.
- **Billing:** payment information is already present on the Nebius account. Billing settings are not changed. Consequence recorded: the credit balance is not a hard spending ceiling, because Nebius documents automatic card charging when the balance goes negative. In-application caps are therefore the control, and the $30 inference and $20 hosting figures remain planning allowances, not authorization to spend.
- **Probe retention:** the deployed stage A probe is kept until its initial observations and a sleep/wake observation are recorded. Deleting the app and repository is a later, explicit action.
- **Stage A scope:** two files (`app.py`, `requirements.txt`) in a new public repository `lainx06/atlas-hosting-probe`; no ATLAS source, no credentials, and no Nebius request. No Nebius key is requested for the canary test.
- **Retention:** unresolved dispatched reservations remain accounted for. Pruning old records never releases reserved funds or resets cumulative spending; a dispatched reservation is not pruned before reconciliation.
- **Neon project and probe protection (2026-10-15):** the owner's Neon project `atlas-budget-probe` (PostgreSQL 18) is kept; Neon 18 verification is pending and local PostgreSQL 17.11 results are labelled as such. Because the deployed probe is public, database tests run only after a server-side `PROBE_ACCESS_CODE` check. The first-connection time is a combined connection/startup measurement, not a region comparison.

## 2026-10-15 — T-06 dispositions and slice 1 authorization
Lead decisions on the T-06 implementation plan. Slice 1 only is authorized; it has no model client, no live inference, no hosting change and no production budget-store work. Settled policy (retries count toward the six calls, no host fallback, application-validated JSON, dispatched reservations not released by lease expiry) is unchanged.
- **CLI approval:** the CLI shows the diff and requires the first 12 hex characters of the candidate hash; the full hash is recorded. With no terminal, the run ends `NEEDS_INPUT` and nothing executes. (Not implemented in slice 1, which approves programmatically in tests.)
- **Approval waiting:** time spent waiting for a human approval is excluded from the active execution budget. Total elapsed time is recorded separately, and the approved bytes are revalidated before execution.
- **Integration acceptance project:** `benchmarks/t01/s01_faulty` is used for T-06 integration acceptance; the T-06 RUN command naming the nonexistent `benchmarks/sensor_generalization` is amended. This does not replace that later benchmark or its generator-freeze requirement (SPEC §14).
- **Docker for both:** the finished agent workflow runs both the original and the candidates in Docker. Original execution must be explicitly authorized and bound to its snapshot. A slice 1 comparison of a host-fixture baseline with a Docker candidate is labelled as such; final agent acceptance requires Docker for both.
- **Schema failure:** a schema failure terminates the model attempt without an action and without a format-repair retry; completed audit results remain intact.
- **Token ceilings:** the per-stage token ceilings (`docs/HOSTING_PROBE.md`) remain proposed until reviewed before live execution. No inference is authorized.
- **Slice 1 corrections:**
  - Trust is anchored outside candidate outputs. The bridge receives the host runner's result and the actual approved candidate and snapshot. Candidate-collected files never overwrite host execution, approval, manifest or index records: an explicit artifact mapping, collisions with reserved host-owned names rejected, and copied bytes verified against the host collection hashes before indexing.
  - No circular trust checks: Docker configuration is validated against the trusted runner requirements and the authorized invocation context, not only against settings in `execution.json`; changing a limit together with its recorded command must still be rejected. `runtime.json` corroborates only. Matching hashes establish consistency, not authenticity against an attacker who controls the host.
  - Record integrity and binding are validated first, then the documented status mapping. FAILs are preserved only when their supporting evidence remains valid; missing or corrupt evidence stays ERROR and is not downgraded to "not executed". A later failure does not erase an already supported violation.
  - Reports show the full required set, execution status, scientific outcome and runner-specific limitations. A failed or refused candidate never alters the completed original audit.
  - No-host-fallback tests distinguish the Docker CLI subprocesses used for availability checks from candidate Python on the host.
  - The mutation-testing decision follows changed behavior and dependencies, not only whether mutation-target lines changed.

## 2026-10-16 — T-03 hosting decisions (SPEC §13; Q5)
Lead decisions after reading `docs/HOSTING_PROBE.md` §9, which includes the owner-observed sleep/wake cycle and the stage D run on Neon PostgreSQL 18. T-03 is **not accepted** by these decisions; acceptance is a separate act by the lead.
- **Execution mode for V1:** limited hosted mode, plus full local Docker execution. Full hosted execution (a separately isolated worker) stays a **stretch goal**. It is adopted only if it is demonstrated under SPEC §10, as Q5 already requires.
- **Budget store:** Neon serverless Postgres (Free plan) is **selected**, replacing the provisional selection. Basis: the hosted probe passed once (`docs/HOSTING_PROBE.md` §5b). Production integration (real accounting, caps, judge and public pools, leases, reconciliation, pruning, monitoring) still needs implementation and review.
- **Availability through 15 December:** the plan is accepted. Streamlit Community Cloud is used with its documented 12-hour sleep, and one wake cycle was observed (about 23–24 s). Recorded examples and the local build are the fallbacks. **This is not a guarantee of uptime.**
- **Judge access and budget design:** accepted for T-03's **planning scope** only (`docs/HOSTING_PROBE.md` §5, §5a). Implementing and verifying the controls is later work (T-12, and T-06 for the run-level ledger). In-application caps are **planned controls, not an existing hard spending ceiling**. Billing stays unchanged, and **no additional spending is authorized**; raising a cap or topping up credits during restoration needs its own approval.
- **Credits:** the expiry of the $50 and its eligibility for promotional use in a public judging demo stay **explicitly unknown**. Unknown eligibility is not approval.
- **Stages B and C deferred to deployment integration (T-12):** the hosted app may not be declared ready until (a) Nebius connectivity from the host and (b) the full locked-environment build on the host have both been tested and recorded. Each test needs its own approval when it is run.

## 2026-10-16 — T-06 slice 4 live-run decisions (lead)
Lead decisions at Gate 2, based on TASKS.md T-06 "SLICE 4 PROPOSAL" and the Gate 1 PASS at `8c79e5a` (`runs/g1v3/review.md`). **This record authorizes neither the pre-run check, nor the live run, nor any spending;** those need the Gate 3 go-ahead after Codex reviews the implementation.
1. **Per-call ceilings, uniform for all 6 attempts:**
   - `max_input_tokens` 12,000. This is an ATLAS estimate (UTF-8 bytes + 16 tokens per message), **not a guarantee**.
   - `max_completion_tokens` 8,000. The provider enforces it as documented; ATLAS has not verified that.

   These replace the per-stage table for live runs.
2. **Estimate cap:** $0.0648 per run, enforced by the per-request stop already implemented.
3. **Maximum authorized expenditure:** $0.51 for **one** live run on `benchmarks/t01/s01_faulty`.
   - This is the provider-enforced worst case ($0.5006592, rounded up), which ATLAS has not verified.
   - Expected spend is about $0.005–$0.014.
   - Billing is unchanged.
   - Any further live run needs a new explicit go-ahead.
4. **Pre-run check:** a free, authenticated `GET /models` immediately before the run. If the model is absent, or its listed input price, output price or context length differs from the configuration, the run aborts with no completion sent. The pre-run call itself needs the Gate 3 go-ahead.
5. **Live entry point:** the CLI refuses unless `ATLAS_MODEL_MODE=live`, the explicit `--live` flag and `--authorize-spend-usd` equal to the decided $0.51 are all present, and the spending limits cover the provider-enforced worst case. The original and each candidate need typed approvals, as now.

**Fixed configuration:**
- model `nvidia/nemotron-3-super-120b-a12b`;
- listed prices $0.30 / $0.90 per 1M input/output tokens (re-checked by the pre-run check);
- context length 262,144;
- template allowance 16;
- `max_attempts` 6 (retries count; "Hosting probe decisions").
- Request timeout 60 s is **PROPOSED** (the T-04 smoke value), to be confirmed by the lead at Gate 3.

**Explicitly not authorized by this record:** the pre-run call, the live run, any spending.

### Gate 3 dispositions (lead, 2026-10-17)
After Codex's Gate 3 review (`runs/g3v/review.md`, at `54feca6`: FAIL, three P2 and one P3):
1. **Request timeout 60 s: DECIDED** (previously proposed; the T-04 smoke value).
2. **Base URL `https://api.tokenfactory.nebius.com/v1/`: DECIDED** (STATUS.md "Nebius configuration"; the official docs used in T-04). For the live entry point, the base URL and model ID come **only** from `DECIDED_SLICE4`, never from `NEBIUS_BASE_URL` or `ATLAS_MODEL_PRIMARY`; the key is the only value read from `.env`.
3. **Fixture reports carrying `"preflight": {"applicable": false, ...}`: ACCEPTED** as an additive, honest report field (Codex P3). Fixture execution and evaluation are unchanged.

**Still not authorized:** the pre-run call, the live run, any spending.

### Gate 3 re-verification dispositions (lead, 2026-10-17)
These dispositions resolve the prompt-outcome findings in `runs/g3w/review.md` and `runs/g3x/review.md`. Codex's confirmation, `runs/g3y/review.md`, records **GATE 3 PASS at `f327565`** under them.
1. **P2-1 acceptance criterion: REVISED.** The earlier wording, "no expanded value anywhere", contradicted the required in-range mismatch case. Out-of-range or malformed listed values are rejected from their tuple or raw form without expansion; fixed-point rendering happens only after the range check accepts that same value, is at most **132 characters** per value, and preflight evidence stays within **16 KiB**.
2. **`money.py` rejecting `"0E+200"`: known limitation, DEFERRED (P3).** This is a zero with a large exponent; the rejection fails closed.
3. **Listed price strings longer than 64 characters rejected as `price_malformed` (`preflight.py:77`): ACCEPTED.** The rejection fails closed and replaces the follow-up prompt's requested mismatch outcome for the maximum-digit input.

**Still not authorized:** the preflight call, the live run, any spending. Gate 3 PASS means ready for the lead's explicit go-ahead; it is not that go-ahead.

## Lead decisions, 2026-10-17
Recorded after live run 1 (`runs/live1/agent-s01_faulty-3f18e12af383/`), Codex's Gate 4 review (`runs/g4/review.md`: **GATE 4 FAIL**, two P2, 0 P1), and the fast-forward of `t06-s4c`, `t07-ui` and `t09-har` into `main` (HEAD `f5d76c9`).
1. **Delegation.** The user delegated scope and priority decisions to the tech lead. Spending (each live run), anything public (the repository, a hosted demo, a video) and the final submission remain explicit user actions.
2. **Scope.**
   - T-08 is **cut**; the Session 5 scenario is dropped.
   - T-10 is **reduced** to at most 3 unfamiliar cases.
   - Model routing is cut.
   - The Tavily prize is out of scope.
3. **Codex review budget: five gates only.**
   1. Gate 4 (done: FAIL, `runs/g4/review.md`).
   2. Slice 4c, T-07 and T-09, reviewed together.
   3. T-12.
   4. T-11, with any remaining T-09 claims.
   5. Release.

   Every other check is builder tests plus the lead's direct reads.
4. **Slice 4c** (`2ce5dd5`, `292ed81`).
   - `propose_patch` accepts exactly one of `diff` or `new_source`. For `new_source`, ATLAS builds the diff, and the unchanged `validate_diff` decides.
   - Each proposal is recorded with its outcome and a bounded reason.
   - The schema shown to the model states the exactly-one rule.
   - No separate Codex gate: slice 4c is reviewed in the combined review (item 3.2).
5. **T-07 model.** T-07 was built on Opus 5.5 high instead of Sonnet medium, because Design is a judging criterion.
6. **T-09 approvals.** The offline evidence runs of the ATLAS-authored benchmark projects use a scripted approver that grants only the unmodified original (`benchmarks/real_sensor/run_audit.py`). Every judge- or user-facing path keeps typed approval.
7. **T-09 inflation is shown as a descriptive protocol comparison, not a causal one.**
   - Balanced accuracy, mean over the development folds:
     - flawed variant (random row-level folds): **0.906**;
     - clean control (subject-grouped folds): **0.875**.
   - The reported-metric check correctly PASSes, because ATLAS recomputes the metric from the flawed project's own predictions.
   - Source: `docs/T09_CONTAINMENT.md` §6.
8. **The HAR license terms** (resolved by the user on 2026-10-18: "T-12 decisions (user, 2026-10-18)" item 1 below).
   - The UCI dataset page grants CC BY 4.0.
   - The archive's 2012 `README.txt` adds "Any commercial use is prohibited."
   - Lead recommendation:
     - no redistribution of the data;
     - the hosted demo shows precomputed HAR results;
     - the README cites both terms.
9. **Record.** `d870275` was committed from a Codex session at the lead's direction. The lead verified its content before approving it.
10. **One corrective turn after a schema failure, within the 6-request budget; no format repair; raw replies persisted as untrusted.** Recorded after live run 2 (`runs/live2/agent-s01_faulty-93583d9e48b5/`: ERROR, `schema_failure: not_json`, reply not stored). Implemented in T-06 slice 4d (TASKS.md T-06 "SLICE 4d RESULT").
11. **Optional bounded rationale on every action (model-written, authorizes nothing); an empty length-limited reply is eligible for the one corrective turn; the request body stays as decided (no reasoning-control parameter).** Recorded after live run 3b (`runs/live3b/agent-s01_faulty-7de5564eab88/`: a rationale on `list_project_files` rejected as an extra field, then an empty reply at the 8,000-token output limit). Implemented in T-06 slice 4e (TASKS.md T-06 "SLICE 4e RESULT").
12. **A failing candidate's bounded, sanitized error summary is returned to the model as untrusted candidate output; a fixed, generic adapter reference is part of the model's context.** Recorded after live run 4 (`runs/live4/agent-s01_faulty-8dcf4c7b3c37/`: both candidates failed with the same `KeyError: 'subject_id'`, which the model never saw). Implemented in T-06 slice 4f (TASKS.md T-06 "SLICE 4f RESULT").
13. **Up to two consecutive corrective turns within the 6-request budget; corrections derived from the schema and fixed text, never quoting the reply. Native tool calling is held in reserve (it changes the decided request contract and would need its own decision and review).** Recorded after live run 5 (`runs/live5/agent-s01_faulty-a53e65ecf004/`: an undeclared `summary` field, then a trailing comma). Implemented in T-06 slice 4g (TASKS.md T-06 "SLICE 4g RESULT").
14. **Finish-after-success guidance; a recorded-run viewer that re-verifies hashes and never re-executes.** Recorded after live run 6 (`runs/live6/agent-s01_faulty-877f8245a8a2/`: revision 1 judged NO_VIOLATION_FOUND, then a second revision rejected and the 2-revision limit reached). The guidance is a fixed line in a NO_VIOLATION_FOUND candidate's evaluate_candidate result and one prompt sentence; the model still decides. The viewer is the basis for hosted replay (T-12). Implemented in T-06 slice 4h (TASKS.md T-06 "SLICE 4h RESULT").
15. **LF line endings pinned by .gitattributes, test fixtures byte-exact; redaction of candidate output is best-effort, with the documented limits.** Recorded after combined review 1 (`runs/cr1/review.md`: COMBINED FAIL, three P2). `.gitattributes` sets `* text=auto eol=lf` and `tests/fixtures/** -text`, so a Windows checkout with `core.autocrlf=true` no longer rewrites the byte-exact reply fixtures (F3). `agent/failure.py` redacts Windows drive and UNC paths in either slash style; a quoted path is replaced whole and an unquoted one to the end of its line. The guarantee is narrowed (module docstring, SPEC §11): the candidate runs in a container whose only mounts are under `/work`, so host paths reach its output only through text the candidate itself constructs; path text deliberately split or encoded across lines is not guaranteed to be redacted; the output stays labelled untrusted (F1). Both approvers have a regression test that the snapshot hash's prefix declines (F2). Implemented on branch `fix-cr1` (`ad69a97`, `2519efa`; TASKS.md T-06 "FIX PASS 1").
16. **T-06 accepted by the lead within documented scope (2026-10-18).** At `199a173` on `main` (`fix-cr1` merged by fast-forward), after the end-of-line redaction rule (a host path redacted from its start to the end of its line; a traceback frame keeps its tail). Basis, scope and limitations: TASKS.md T-06 "ACCEPTANCE (lead, 2026-10-18)".

**Not authorized by this record:** live run 2 or any other spending, and anything public.

## T-12 decisions (user, 2026-10-18)

Recorded at the user's direction for T-12 (SPEC §13). They resolve "Lead decisions, 2026-10-17" item 8.

1. **HAR data.**
   - The hosted demo shows precomputed HAR results only.
   - No dataset download and no redistribution.
   - The README cites CC BY 4.0 and the archive README's non-commercial note.
2. **Hosted mode (SPEC §13, limited hosted).**
   - Recorded runs are shown in the hash-verifying viewer, plus **one** live Nemotron session per visitor session.
   - The model inspects and proposes. Every proposal passes `validate_diff`, and nothing executes on the host ("not executed here").
   - The original's findings shown in a hosted session come from a recorded, hash-verified trusted evaluation, labelled as such.
3. **Spending (authorized by the user).**
   - Total **$8.00**: a public pool of **$3.00** (daily cap **$1.00**) and a judge pool of **$5.00** behind a private access code.
   - Per session: the decided estimate cap **$0.0648** and at most **6 requests**.
   - A kill switch secret, `HOSTED_LIVE_ENABLED`: false when absent.
   - All caps are enforced server-side in Neon Postgres and fail closed.
4. **Approved for later (not in T-12's offline build):**
   - one `GET /models` from the deployed host (stage B);
   - the full locked build on the host (stage C).

**Builder's implementation choices** (T-12 build, for the Codex security-and-spend review and the lead; not user decisions):

- **B1. The HAR feature table is left out of the bundle** (`table.parquet`, two copies per HAR run), per item 1.
  - Each left-out file is listed with its size and SHA-256 in `demo/recorded/BUNDLE.json`.
  - The viewer does not verify the table, so the copies stay intact.
  - Kept as precomputed results: row and subject identifiers in split and check records, predicted classes, check results and per-fold class counts. No feature values and no per-row labels.
- **B2. Each hosted live session runs the decided pre-run check** (one free authenticated `GET /models`) before its first completion, as the CLI live path does (2026-10-16, decision 4). If it does not pass, no completion is sent. This is a `GET /models` from the host in every session; whether to keep it is the lead's call.
- **B3. Reservation ordering.**
  - The store reserves before the in-memory attempt is counted, so a refusal or store failure is not an attempt and nothing is sent.
  - `dispatched` is committed before sending.
  - A request the client itself refused before sending (dispatched=False) is settled at $0, mirroring the in-memory ledger.
  - Known usage above the reservation is charged exactly (a cap can be overrun by that excess; later requests are then refused).
  - A store failure after a request was sent (settle or hold) is recorded in the run log, and the amount stays held at the ceiling. The next reservation fails closed if the store is still down.
- **B4. The judge code allows one attempt per visitor session** (one live session each). Failed attempts are events with time only. A wrong code falls back to the public route.
- **B5. Dependencies and configuration.**
  - `psycopg[binary]` 3.3.6 was added (`uv.lock` resolved from PyPI).
  - `requirements.txt` is `uv export --frozen --no-dev --no-hashes` (`-e .` rules out hash pinning).
  - Hosted session runs go to a temporary directory on the host (ephemeral; `ATLAS_HOSTED_RUNS_DIR` overrides it).
- **B6. The bundle is byte-exact and is not edited.** `scripts/check_recorded.py` reports host paths and the local user name in the recorded run records (46 each). Its key-shaped findings (12) are only provenance `token =` variables in the copied ATLAS sources. The lead decides whether to publish as is or to re-record.

**Not authorized by this record:** any live call, deployment, stage B or C run, or cap change beyond the values above.

## T-12 review 1 dispositions (lead, 2026-10-18)

Codex review 1 (`runs/t12r/review.md`): "Verdict: T-12 FAIL", one P2.

1. P2 execution boundary: fixed in fix pass 1 (guard at six entry points); re-verification by Codex required.
2. P3 paths outside the allowlist (.gitattributes, app.py, DECISIONS.md, STATUS.md, TASKS.md): accepted; necessary integration changes and normal records.
3. P3 publication metadata in demo/recorded/: user decision A (2026-10-18): publish the recorded bundle as-is. The 12 key_shaped hits are false positives (provenance registration and token= keyword arguments), confirmed by the review.
4. Absolute charged-dollar maximum NOT VERIFIED: accepted known limitation; caps are reservation bounds (see docs/HOSTED_OPERATIONS.md "Spend bounds").
5. Judge-code guessing: mitigated by the 32-character minimum and a random code generated at deployment.
6. Prior work (user, 2026-10-18): the submission period began before 2026-10-14; no ATLAS code, data or documents existed before the first commit 7a0f155 (2026-10-14).

## User and lead decisions (2026-10-19)

User decisions:

1. License: Apache-2.0 for ATLAS, replacing the MIT plan (TASKS.md T-13). LICENSE (unmodified Apache License 2.0 text) at the repository root so GitHub detects it, plus a NOTICE file. The official rules require a public repository under an OSI-approved license; source-available licenses would disqualify. Vendored MIT- and Apache-licensed agent skills keep their own license files and are compatible.
2. IP ownership: the submission is solely owned by the entrant (user statement, 2026-10-19). ATLAS was built on the user's personal equipment and every commit is authored by the user. No repository action.

Lead decisions:

3. T-12 acceptance addition: the judge path must stay free, unrestricted and functional through 2026-12-15 12:00 PT (end of the judging period, an official rule). Checked before acceptance: the daily-reset timezone and date rollover, prune and retention logic, any date-dependent code or expiry, and that the database and host do not sleep or expire in a way that blocks judges. No paywall or access restriction before then.
4. Next gate: the Codex T-12 security-and-spend review includes a fault-injection matrix C1-C10 (kill or restart between dispatch and settlement; tab close or reload mid-session; a reply claiming completion with no valid action; a render failure after the run completes; the store unreachable between requests; a provider timeout or 5xx after dispatch; the kill switch turned off mid-session; a race for the last cents; a bundle tamper; the availability window through 2026-12-15). It also re-verifies the review 1 P2 fix (c3a2805).
5. Not adopted: additional LLM "tester" or "customer" agents or an orchestrator layer. They would contradict "deterministic checks dictate outcomes" and add no truth; failure-path hardening goes through fault-injection review.

Notes (no action before 2026-10-30): any commercialization is after submission and separate from the submitted engine, which stays Apache-2.0; the UCI HAR non-commercial note means a future commercial showcase needs different or synthetic data; the Nemotron model is used under the NVIDIA Nemotron Open Model License.

## T-12 review 2 dispositions (lead, 2026-10-19)

Codex review 2 (`runs/t12-review/review.md`): "Verdict: T-12 REVIEW 2 FAIL", two P2, no demonstrated P1.

1. P2-1 Docker maintenance entries: fixed in fix pass 2 (guard at every process start in runner/docker.py); re-verification by Codex required.
2. P2-2 partial headline after a render failure: fixed in fix pass 2 (clearable results container, fixed error, record unchanged); re-verification by Codex required.
3. E1's failure is a stale exception expectation in the review 1 probe (it catches ValueError, the guard raises HostedExecutionRefused before the executor); not a regression. Review 1 P2 confirmed fixed by 34 boundary tests and 10 independent tripwires.
4. C10 operational availability (host and database sleep, free-tier expiry, wake latency, credits) is not testable offline; it is checked during deployment and in the hosted smoke test before submission.
5. The exact-"1" ATLAS_HOSTED rule stands (decided); deployment must set exactly ATLAS_HOSTED=1, verified in the hosted smoke test.

## T-11 re-scope and T-10 (lead, 2026-10-19)

1. T-11 is re-scoped because T-08 (procedures, agent+memory) was cut: a three-way comparison on the four development cases benchmarks s01_faulty, s02_clean (synthetic) and the T-09 har_flawed, har_clean projects (ATLAS-authored, real UCI HAR data): (a) ATLAS deterministic audit; (b) Nemotron alone, the same model reading the same files with no executable checks, three repetitions per case; (c) the project's reported metric against ATLAS's recomputed metric and the clean control. Results are descriptive.
2. These are development cases, not held-out: ATLAS's checks were built and debugged on them, so ATLAS's results on them are not evidence of generalization. Every report of T-11 states this.
3. Expected violated assertion IDs per case are fixed in evaluation/expected.json and committed before any live trial; they come from the existing benchmark records, never from a T-11 result.
4. T-10 (held-out cases) is cut for the submission: its cases must be authored outside Claude's view (Codex), and Codex capacity is reserved for gates. Recorded as a limitation.
5. Live T-11 trials need the user's explicit go-ahead; each Nemotron-alone case run makes at most 3 requests (within the 6-request run limit), reserved before dispatch, under the decided per-run estimate cap $0.0648 and $0.51 authorization.
6. Leg (b) of T-11 (Nemotron alone, one request per trial, no tools) uses its own input-token ceiling of 40,000 (an ATLAS estimate), because the HAR cases' manifest and source estimate about 34,600 tokens and omitting the manifest would make the comparison unfair (ATLAS reads it). The agent's 12,000-token ceiling (DECIDED_SLICE4) is unchanged. Each leg (b) request is reserved at its ceiling, 40,000 x $0.30/M + 8,000 x $0.90/M = $0.0192; three requests reserve $0.0576, within the unchanged per-run estimate cap of $0.0648 and $0.51 authorization. The model's listed context is 262,144 tokens.

Builder notes for the lead (Claude Code, 2026-10-19; recorded with the predeclaration, decide before any live trial). The first and third notes are superseded by item 6 (T-11 fix pass 1): all four cases now reach leg (b), and the suite can send 12 requests.

- **(Superseded by item 6.) The two HAR cases cannot reach the model under the decided input ceiling.** Their manifests list 561 feature names, so the leg (b) input estimate is 34,605 (`har_flawed`) and 33,726 (`har_clean`) against the decided 12,000; each such case is refused before dispatch and its three trials are recorded NOT_SENT `input_over_ceiling`. The inputs were not shortened to fit. `s01_faulty` and `s02_clean` are at 8,293 and 8,264.
- **`har_flawed`'s expected set includes `split.no_window_overlap`**, sourced from the variant's own docstring (deliberate flaw 2) and `benchmarks/real_sensor/README.md`; ATLAS records it NOT_ASSESSED (T-09 §3), scored as a coverage gap. The other expected IDs are the T-01 scenario table and the T-09 §6 FAIL list.
- **The $0.51 authorization is applied per case run** (as item 5 states it): the provider worst case of one case run is $0.2503296. With the HAR cases refused the suite sends at most 6 requests (provider worst case $0.5006592); with all four cases sendable it would be 12 ($1.0013184). (Updated by item 6: all four are sendable, so the suite can send 12 requests, reserved at $0.0192 each, $0.2304 in all; the provider worst case is unchanged per request, $0.0834432, because it rests on the 262,144-token context, so $1.0013184 for the suite. The $0.51 and $0.0648 still apply per case run.)
- **The case files label their own flaws** (docstrings, comments, `har_flawed`'s claim statement); leg (b) reads them unchanged. Protocol: `docs/EVALUATION.md`.
