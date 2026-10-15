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
