# ATLAS build playbook

Prepared for Adnan Hossain on October 14, 2026. Revision 5 adopts confirmed full-day availability, lean local handoffs, and explicit safe deployment alternatives while preserving the full evaluation/UI scope. Planning and handoff only; application implementation has not started. All targets below are proposed engineering targets, not measured results. Begin with the 14 steps in ATLAS_Start_Here.md. Sections 17–21 govern collaboration; Section 22 guides tool installation; Section 23 governs submission; Section 24 defines executable task cards; Section 25 covers UI design and verification. Start Here owns the sequence, while this file supplies technical detail.

## 1 Product and scope

ATLAS is an Experimental Verification Workspace. LENS is its first specialist capability: investigating whether a small ML experiment supports its stated deployment claim, testing revisions, and remembering verified evaluation procedures.

Primary user: a student researcher or small applied-ML team with a Python classification experiment and a concrete generalization claim. Example: “This activity classifier should work on people who were absent from the training data.”

The useful outcome is a reproducible finding and a defensible evaluation protocol. Lower accuracy after correcting the protocol is a valid outcome. The product does not attempt to improve scores at the expense of honest evaluation.

V1 supports small CSV/Parquet feature tables, explicit target and metadata columns, CPU scikit-learn estimators, and a documented adapter. Raw-waveform processing, arbitrary notebooks, deep learning, causal validity, every form of leakage, and unrestricted uploads are out of scope. The dashboard must make this coverage visible.

The first user workflow:

1. Select a supported example or locally prepared project and state the intended deployment claim.
2. Review the inferred task contract and confirm ambiguous deployment assumptions.
3. Inspect evidence from executable checks.
4. Preview a candidate code change and run it in an isolated copy.
5. Compare evaluation protocols and measured results.
6. Export an evidence report and optionally save an applicable procedure.

Public demo: curated examples, an editable claim, live bounded model calls, and no arbitrary user code execution. Local developer mode can inspect supported projects with explicit approval and isolation. Replay is labeled; it must not impersonate a live model call.

## 2 Competition and completion requirements

Checked October 14 against official rules and FAQ. Recheck before submission. Deadline: October 30, 2026 at 10 a.m. Pacific / 1 p.m. New York; internal target October 29. Choose Coding and Agentic Engineering. The submitted app must call an NVIDIA open-source model through Nebius Token Factory or run on Nebius AI Cloud. Other coding assistants can help development; they do not replace this runtime requirement. [S1, S2]

Deliver a working demo URL or test build, public licensed source, setup instructions, project description, public YouTube demo under three minutes, and sponsor-tool feedback. Disclose prior work and significant changes if applicable. Keep the submitted version available for judging through December 15, 2026 under the currently published schedule. A local test build is a fallback; a polished hosted curated demo is preferred. [S1]

No claim that using several models, a particular skill, or a particular track increases selection odds. The project must demonstrate implementation quality, coherent design, practical impact, and a thoughtful idea. [S1]

## 3 Tools and purchases

| Item | Decision | Purpose and limitation |
| --- | --- | --- |
| Existing ChatGPT/Codex | Use first | Project lead and independent review; temporary builder until Claude Code is ready. Verify actual repo access and local versus cloud execution at kickoff. |
| Claude Max with Claude Code | Family-funded plan, activation/tier unconfirmed | Main builder after setup. Max 5x is currently $100/month and Max 20x $200/month on the web; usage limits remain. Default to 5x if the tier is undecided, then assess actual usage. This purchase does not fund Nebius. [S4, S15] |
| Gemini through existing student membership | Use existing access | Review assumptions, tests, and product explanation. Do not assume chat membership grants API credits or unattended repo access. Model availability must be checked in the user's account. |
| Nebius Token Factory | Required runtime account | Claim $25 promotional credit using NEBIUS-DEVPOST-GLOBAL26 and the additional $25 offered through the Builders Program. Credit arrival/eligibility must be confirmed. These are inference credits, not an unlimited GPU grant. [S5, S2] |
| Git and GitHub | Use | Checkpoints, issue-sized work, public final source, release tag, reproducible instructions. Start private if desired; publication remains a deliberate release step. |
| VS Code | Proposed editor | One local workspace, diff inspection, terminal, and a coding-agent extension if desired. No additional paid IDE needed. |
| WSL2 and Docker or equivalent Linux container runtime | Verify early | Reproducible execution of candidate experiments. Prefer an already working environment. Do not spend days rebuilding the PC or dual boot. |
| Python and uv | Proposed build environment | Python 3.11 baseline, isolated environment, resolved lockfile. Resolve package compatibility on Day 1. |
| pytest and Ruff | Use | Functional regression checks, negative cases, formatting/static checks. |
| Streamlit | Proposed UI | Fast Python implementation with clear evidence panels. Keep scientific engine separate. |
| Browser verification | Use Playwright for repeatable UI scenarios | Python browser tests plus available browser/MCP tooling for exploration and failure evidence. Do not add Puppeteer for duplicate coverage. |
| OBS or existing screen recorder | Use | Record a legible demo with clear narration. No subscription required. |
| Ponytail | Optional after the first working slice | Simplification review using canonical source; not a prerequisite or a guarantee of savings. |
| Other agent frameworks, vector databases, MCP bundles | Defer | Add only for a demonstrated missing capability. V1 needs a bounded controller, not a framework collection. |

Planning budget, not authorization to purchase: existing subscriptions plus the family's chosen Claude Max tier, currently $100 or $200/month on the web. The user's sister offered to fund Max; purchase has not been verified. Begin runtime work with granted Nebius credits. Reserve up to $30 for additional inference and $20 for hosting if actually needed and approved. Hosting must cover judging availability, not merely the recording day. No domain purchase, GPU rental, or new hardware is required. Max has limits; leave automatic overage disabled unless deliberately authorized. Any included Claude API credits have separate terms and are unnecessary for the NVIDIA runtime. [S15]

The AMD GPU is not a blocker for remote inference or these small CPU experiments. Do not design around local CUDA. No API keys should enter browser code, screenshots, prompt transcripts, fixtures, Git history, or candidate-code containers.

## 4 AI workflow and useful skills

Distinguish three concepts:

- Development agents help us build ATLAS: Codex, Claude Code, and Gemini.
- The application agent is ATLAS's bounded Nemotron tool loop.
- Evaluation procedures are validated application data. They are not the development assistant's SKILL.md files and do not fine-tune model weights.

Default collaboration after Max activation: Claude Code owns implementation and integration; ChatGPT/Codex coordinates milestones and independently reviews consequential diffs; Gemini reviews experimental design and the demo using sanitized artifacts. Codex can be the temporary writer while Claude is being configured or when usage is exhausted. Explicitly transfer ownership before switching. These roles are interchangeable; they do not imply benchmark superiority. Sections 17–21 define the precise model, handoff, and evaluation rules.

Parallel work is useful only when ownership is clear. A reviewer can inspect a committed diff while the writer works elsewhere. Independent implementation requires separate branches/worktrees and file ownership. Never have three tools edit the same working tree concurrently. Keep final acceptance with executed tests and the human owner.

Repository instruction design:

- AGENTS.md: project scope, commands, evidence policy, isolation, cost limits, prohibited edits, source-of-truth files; aim for less than one page.
- CLAUDE.md: short pointer to shared rules and tool-specific commands. Do not duplicate the entire spec.
- PROJECT_BRIEF.md: stable one-page product/user/scope/constraints summary for first contact with any assistant.
- docs/PRD.md: user requirements and acceptance criteria; docs/SPEC.md: implementation contracts; docs/TOOLING.md: installed tool/skill revision and capability records.
- STATUS.md: commit, completed items, exact working commands, current failures, next task, unresolved questions; update at every handoff.
- DECISIONS.md: brief dated decisions with reasons. Reopen a decision only with new evidence.
- TASKS.md: small tasks with acceptance criteria, each sized to one focused session.

Official Codex local skill discovery includes .agents/skills, and Claude Code supports project skills in .claude/skills. Verify installed client behavior before configuring shared files. [S6, S7]

Create on-demand runbooks during implementation, then package as skills only if repetition justifies it:

| Runbook | Trigger | Required output |
| --- | --- | --- |
| Scientific review | Changing splits, metrics, checks, or fixtures | Distinguish leakage from deployment mismatch; identify oracle, coverage, negative case, and unknowns. |
| Execute verification | Before merging a meaningful change | Commands executed, outcomes, failure evidence, and remaining limits. Never invent results. |
| Simplify change | After a vertical slice works | Identify unnecessary dependencies/abstractions without weakening tests or provenance. |
| Prepare handoff | End of session or tool switch | Commit, exact files, verified commands, blockers, next acceptance condition. |
| Release review | Before deployment/submission | Fresh install, secret scan, license/data notices, example run, UI checks, source tag, demo links. |

These are proposed procedures, not installed skills. Any custom skill files should be reviewed and version-controlled with the project. Keep one canonical runbook text; tool-specific wrappers reference it.

Ponytail is an actual open-source coding ruleset. The author identifies DietrichGebert/ponytail as canonical. Inspect the chosen revision and its hooks before installing; review the current INSTALL instructions. Begin with an optional manual review on one small change. Its published savings are author-reported and not a forecast for this project. Remove it if it adds overhead or conflicts with scientific correctness. [S8]

Token discipline: provide task-specific files and diffs, not the entire chat; parse logs in code; truncate routine output; retain full evidence on disk; use offline tests; limit revisions; summarize tool results; load skills only when relevant. Extra agents and tools can increase usage. Measure cost per accepted change rather than rewarding shorter code by itself.

## 5 Proposed technical architecture

Suggested dependencies: Python 3.11, uv, numpy, pandas, scikit-learn, Pydantic, Streamlit, pytest, Ruff, and an OpenAI-compatible client configured exclusively for Nebius in application runtime. Use pathlib, sqlite3, hashlib, json, logging, and subprocess from the standard library where sufficient. Pin actual compatible versions after installation; none are pinned by this document.

| Module | Owns | Does not own |
| --- | --- | --- |
| Intake and task contract | File inventory, dataset schema, deployment claim, declared split policy | Guessing ground truth or trusting repository instructions |
| Agent controller | Bounded state transitions and validated tool proposals | Arbitrary host commands or final validity judgments |
| Verification engine | Assertions, evidence artifacts, independent metrics | Free-form scientific opinions |
| Candidate workspace | Immutable original snapshot, patch candidate, diff, rollback | Host secrets or changing trusted evaluator rules |
| Isolated runner | Executing supported candidate code with resource limits | Network access or arbitrary dependency installation |
| Procedure store | Versioned workflow records and applicability checks | Blindly reusing a fix because text sounds similar |
| UI and reporting | Claim, plan, evidence, diff, metrics, limitations, exports | Concealing model failures or replay mode |

Bounded state machine: INTAKE -> CONTRACT_REVIEW -> INSPECT -> CHECK -> PROPOSE_PATCH -> EXECUTE -> VERIFY -> REPORT. Optional SAVE_PROCEDURE follows verified evidence. Any stage can end NEEDS_INPUT, NOT_SUPPORTED, BUDGET_EXHAUSTED, or ERROR. Retry at most once per transient model call; permit at most two candidate patch revisions in a default run. Initial ceilings: six model calls, twelve tool operations, a five-minute whole-run timeout, and a thirty-second candidate subprocess timeout. Tune after measured latency; document changes.

Tool allowlist: list_project_files, read_project_file, profile_table, run_check, propose_patch, evaluate_candidate, inspect_evidence, retrieve_procedure, propose_procedure. Arguments use typed schemas and normalized paths. No raw host shell tool. Model-produced patches cannot touch evaluator code, holdout labels, run policies, dependencies, or instruction files. Reject symlinks/path escapes, oversize files, unexpected artifacts, and unauthorized deletion.

Container starting policy: disposable non-root execution, read-only base filesystem, writable run-specific scratch, no network, no keys, dropped capabilities, no-new-privileges, bounded memory/CPU/PIDs/output size, no Docker socket, and only minimal input mounts. Build the known dependency image separately. Candidate code never shares the credential-bearing controller process. A container reduces risk but is not a claim that arbitrary hostile code is safe; public execution remains curated. Docker is the initial adapter; another runtime may replace it only after verifying the same isolation contract. If isolation is unavailable, do trusted fixture-only development until it is available. A temporary directory, shell=False, timeout, or reduced environment does not confine generated Python code. A subprocess may launch a sandbox; it is not itself the sandbox. [S43, S44]

Supported adapter contract: table plus a schema/claim manifest; explicit train/validation/test row IDs; a fit/predict entry point; preprocessing provenance events; predictions keyed by stable row ID. Version the contract. Do not import candidate code into the backend to inspect it. Original arbitrary code without instrumented provenance may be inspected statically, but fit-boundary claims remain unassessed until the relevant execution path is observed.

## 6 Five deterministic checks

Each check returns check_id, version, status, assertion, applicability, observed values, evidence paths/hashes, coverage, and limitations. Status is PASS, FAIL, NOT_ASSESSED, or ERROR. Findings include a separate category such as deployment_mismatch, contamination, instability, or missing_evidence. A missing field never silently passes.

| Check | Inputs and executable assertion | What it establishes and does not establish |
| --- | --- | --- |
| Split integrity | Stable row IDs, declared folds, subject/session IDs, task contract. Test row disjointness and group disjointness only where required; record duplicate-row/overlapping-window evidence when metadata permits. | Establishes observed overlap relative to the claim. Random splitting is not inherently wrong. Within-person future prediction and unseen-person prediction require different policies. |
| Preprocessing fit provenance | Instrumented fit/fit_transform events with fold, component, input row IDs and label-use flag. Assert all fit rows belong to that fold's training partition; include inner-fold tuning. | Establishes observed contamination of supported transforms. Source-code patterns alone are suspicion. An uninstrumented custom transformer must be NOT_ASSESSED, not clean. |
| Independent metric and baseline | Predictions keyed by row ID, trusted labels, class map, declared primary metric, identical partitions. Recompute balanced accuracy/macro-F1 and a simple dummy baseline; add a small meaningful linear baseline when appropriate. | Tests reported metrics and context. Beating a baseline is not proof of usefulness; falling below one is not proof of leakage. Never compare different protocols as if they were identical. |
| Temporal availability | Prediction times, feature-availability times and label horizons, optional window spans, declared forward-looking task. Assert no future feature access and required chronology/gaps. | Establishes availability violations in explicit metadata. Do not invent timestamps for a dataset without them. For unseen subjects without a temporal claim, record not applicable. |
| Robustness and reproducibility | Predeclared small set of splits/seeds, metric, group counts, dependency versions and hashes. Repeat development evaluation and report range/variation and per-group results. | Tests sensitivity over the stated trials. Three seeds do not establish statistical significance. Do not compute overconfident uncertainty by treating correlated windows as independent. |

scikit-learn's guidance supports learning preprocessing only from training data and using pipelines to prevent common leakage. ATLAS must still measure the affected execution path rather than assume that adding Pipeline resolves every problem. [S9]

Scientific boundaries: development validation can guide a revision; final test outcomes cannot select patches or parameters. Grouped/temporal splitting must preserve sufficient classes and groups. Stop and explain if the available data cannot support the requested claim. Any group ID, target proxy, or metadata column included as a feature needs explicit examination rather than automatic acceptance.

## 7 Model integration and routing

Runtime API base: https://api.tokenfactory.nebius.com/v1/. Query GET /models using a backend-held key; use POST /chat/completions with an actual NVIDIA model ID. Record a successful inference request and capability test. Public Nebius material lists Nemotron Ultra, Super, and Nano-family offerings, but account availability, IDs, pricing, and response-format support must be checked. [S10, S11, S12]

Environment contract to implement:

```text
NEBIUS_API_KEY=local_secret_not_committed
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
ATLAS_MODEL_PRIMARY=verified_model_id
ATLAS_MODEL_FAST=optional_verified_model_id
ATLAS_MODEL_MODE=live_or_explicit_fixture
```

Use structured JSON output where the selected model supports it and validate locally with Pydantic. JSON validity is not semantic correctness. If native tool calls are unreliable, use validated structured action proposals and a deterministic dispatcher. Never silently downgrade to unconstrained execution. Nebius documents model-dependent structured-output support. [S13]

Initial route: one suitable NVIDIA model for contract translation, planning checks, adapting supported evaluation code, and evidence-grounded reporting. Full-day availability permits a later routing experiment, not an assumption that routing improves results. Compare the routed and single-model versions on matched tasks for completed-task quality, latency, tokens/cost, and failures; keep routing only if the tradeoff is worthwhile. Use actual available IDs. Later optional route:

| Work | Preferred implementation |
| --- | --- |
| File inventory, schema extraction, metric calculation, log parsing | Deterministic Python |
| Semantic schema hints or ranking procedure candidates | Optional smaller NVIDIA model, followed by hard validators |
| Ambiguous claim translation and code patch synthesis | Available stronger NVIDIA model, measured against the simpler route |
| Report explanation | Same primary model with only verified evidence and explicit unknowns |
| Final prerequisite/acceptance checks | Deterministic validators, never a model vote |

Prompt inputs include the contract, relevant snippets, check summaries, allowed actions, and artifact references. Send public/synthetic data summaries by default, not entire tables or private research datasets. Source files and logs are untrusted data; embedded instructions must not change permissions or goals.

Record model ID, parameters, request ID if returned, prompt/completion usage, timestamp, elapsed time, retries, schema failures, chosen tools, and result status. Exclude secrets and unnecessary raw data. Price estimates require dated provider rates; returned tokens remain useful even if price is unknown. An application estimate is not a provider billing hard cap. Keep one active run per user/session initially and enforce call/output limits.

## 8 Verified evaluation procedure data contract

The first version can be a Pydantic model serialized to JSON. This is a concrete design example, not an implemented schema or a real saved procedure:

```json
{
  "schema_version": "1.0",
  "procedure_id": "unseen_group_classification_v1",
  "status": "candidate",
  "intended_claim_pattern": {
    "task": "classification",
    "deployment_unit": "unseen_subject",
    "temporal_requirement": "none_declared"
  },
  "required_schema_prerequisites": {
    "required_roles": ["row_id", "target", "group_id"],
    "row_id_unique": true,
    "minimum_distinct_groups": 3,
    "class_coverage_check": "required",
    "adapter_version": "1.0",
    "supported_estimator_family": "sklearn_cpu"
  },
  "verification_assertions": [
    {"check": "split_integrity", "assertion": "no_row_overlap", "expected": true},
    {"check": "split_integrity", "assertion": "no_group_overlap", "expected": true},
    {"check": "fit_provenance", "assertion": "fit_rows_subset_of_fold_train", "expected": true},
    {"check": "independent_metrics", "assertion": "prediction_ids_match_evaluation_ids", "expected": true}
  ],
  "patch_template": {
    "template_id": "group_split_train_only_pipeline",
    "template_version": "1.0",
    "parameters": ["target_column", "group_column", "feature_columns", "development_seed"],
    "allowed_paths": ["candidate/evaluate.py"],
    "execution_policy": "review_then_isolated_run",
    "template_sha256": null
  },
  "invalidation_conditions": [
    "deployment_claim_changes",
    "group_role_is_missing_or_ambiguous",
    "insufficient_groups_or_class_coverage",
    "future_prediction_requires_temporal_protocol",
    "adapter_or_template_hash_changes",
    "fit_provenance_coverage_is_incomplete"
  ],
  "provenance": {
    "created_at": null,
    "source_run_ids": [],
    "source_commit": null,
    "dataset_hashes": [],
    "evaluator_version": null,
    "model_id": null
  },
  "validation": {
    "evidence_artifacts": [],
    "passed_assertion_ids": [],
    "tested_scope": [],
    "known_limitations": []
  }
}
```

Minimum group count here is an eligibility floor, not a guarantee of valid class coverage or meaningful generalization. Never insert production-specific thresholds by copying this example without checking the chosen protocol.

Admission rule: a model can propose a candidate record; only the trusted validator can set verified_for_recorded_scope after the evidence exists. Required assertions may not be ERROR or NOT_ASSESSED. Template hash, evaluator version, and provenance must resolve. Preserve the original immutable record when producing a new version. Verification is scoped to the recorded tests; recheck prerequisites and re-execute assertions on every reuse.

Retrieval starts with metadata filtering, then optional semantic ranking. It must return explicit applicability reasons. Templates are constrained patch recipes, not executable arbitrary Python stored in memory. Similar text cannot override a temporal or schema mismatch.

## 9 Benchmark and evaluation design

Separate development fixtures, demo examples, and held-out evaluation. The runtime must not read expected-findings manifests. Keep the trusted evaluator and hidden labels outside candidate writable mounts. Ground-truth descriptions for planted flaws are authored independently of the model's generated diagnosis.

### Example one sensor generalization

Create a small seeded synthetic sensor-feature classification table with subjects, sessions, correlated windows, a modest genuine class signal, and subject/session-specific confounding. Use an intentionally flawed random-row evaluation and a deliberately observed global supervised feature-selection step. These are separate defects. Include feature-selection label use in provenance; do not rely on global StandardScaler alone to cause a dramatic accuracy change.

Run a small factorial comparison: original split/original preprocessing; original split/correct preprocessing; grouped split/original preprocessing; grouped split/correct preprocessing. This helps attribute changes instead of blaming every score difference on one cause. Keep the demo concise but retain the full evidence. Document synthetic generation and why it represents a failure mechanism. Do not market it as actual biomedical data.

Use simple CPU estimators and small tables. Target less than ten seconds for the numerical evaluation after environment startup, excluding model/network latency. Measure on the actual machine. Record cold-start and full wall-clock separately. No artificial score targets.

### Example two transfer and refusal

Create an independently seeded related machine/sensor feature dataset with renamed schema and a different group/session structure. Variant A has a compatible unseen-group claim: ATLAS binds the saved procedure to the new schema and reruns assertions. Variant B changes the task to future prediction with a feature available only after the prediction time: the grouped procedure must be rejected or adapted under a new validated temporal protocol.

Use Variant A for the memory performance comparison and Variant B for the refusal demonstration. Do not claim token savings from a case that merely exits early on a mismatch. Clearly disclose planted flaws and synthetic data.

### Real data and clean controls

Add a licensed public sensor dataset with actual subject metadata. UCI Human Activity Recognition Using Smartphones is the preferred candidate to inspect and license-check during implementation. Its source page provides the dataset and attribution information. Preserve subject IDs and original split metadata, document any sampling and precomputed-feature limitations, and do not invent session timestamps it does not supply. [S14]

A clean control uses an appropriate grouped protocol and fold-local preprocessing with observed provenance. Expected outcome: no supported overlap/fit violations, with remaining limits visible. An unfamiliar evaluation fixture should differ in code structure and schema; freeze it before prompt tuning. If it is examined to debug failures, it becomes development data and requires a new holdout for subsequent generalization claims.

### Measuring agent value

Compare three modes under the same supported contract: fixed deterministic audit; agent without procedure memory; same agent with procedure memory. Keep inputs and environment matched across modes; keep model versions and token caps matched between the agent modes. Randomize run order where practical; report cache and warm-start state. Start with three paired repetitions as a small descriptive pilot, not statistical proof. Increase only if a concrete remaining question justifies cost.

Distinguish audit quality from the underlying classifier's predictive accuracy. An honest protocol correction may lower classifier accuracy. The deterministic audit has no model-token use; it is a quality/coverage/latency baseline, not a token-saving target. Compare procedure-memory token savings primarily against the same agent without memory, including overhead.

Metrics: supported-finding precision/recall on labeled cases, false positives on clean cases, unsupported-case handling, patch validity, task completion, tool calls, returned tokens, wall-clock, retries, and cost estimates. Procedure-creation cost is reported separately and included in break-even analysis. A target is to retain finding quality while reducing repeated work; do not promise savings.

## 10 Repository structure

This is a proposed layout. Create files as their functionality arrives, not empty framework layers.

| Path | Purpose |
| --- | --- |
| README.md, LICENSE, pyproject.toml, uv.lock | Install, license, dependencies, reproducibility |
| AGENTS.md, CLAUDE.md, PROJECT_BRIEF.md, STATUS.md, TASKS.md, DECISIONS.md | Shared development context |
| docs/PRD.md, docs/TOOLING.md, docs/reviews/, handoffs/ | Requirements, tool provenance, review evidence, cross-tool packets |
| docs/handoff/, docs/UI_SPEC.md, docs/SUBMISSION_CHECKLIST.md | Kickoff files, visual/interaction specification, and deliverable evidence |
| .agents/skills/, .claude/skills/ | Selected verified development skills, with required references/licenses |
| docs/SPEC.md, docs/EVALUATION.md, docs/THREAT_MODEL.md | Scope, scientific protocol, execution boundaries |
| docs/runbooks/ | Focused verification, review, handoff, and release procedures |
| src/atlas/contracts.py | Task/check/procedure data contracts |
| src/atlas/intake.py | File and schema inventory |
| src/atlas/checks/ | The five deterministic check modules |
| src/atlas/runner/ | Container adapter, resource limits, snapshots |
| src/atlas/agent/ | Nebius client, prompts, state machine, validated tools |
| src/atlas/procedures/ | Admission, applicability, retrieval, versioning |
| src/atlas/reports.py, src/atlas/cli.py | Evidence export and repeatable commands |
| app.py | Streamlit interface calling the engine |
| benchmarks/sensor_generalization/ | First transparent flawed example |
| benchmarks/procedure_transfer/ | Compatible reuse and temporal mismatch variants |
| benchmarks/clean_control/ | Nonfaulty reference case |
| benchmarks/real_sensor/ | Dataset retrieval/attribution and real-data adapter |
| tests/unit/, tests/integration/, tests/acceptance/ | Invariants, isolated execution, full workflows |
| evaluation/ | Evaluation harness; holdout assets excluded from candidate access |
| scripts/ | Environment/model smoke check, reproducible evaluation, release checks |
| .env.example, .gitignore | Placeholder configuration and private-file exclusions |
| Dockerfile.runner | Pinned isolated candidate runtime |
| .github/workflows/ | Offline CI first; secret-bearing live calls manual only |
| artifacts/ | Generated logs/reports, ignored by default; sanitized examples explicitly curated |

Proposed CLI interface to implement, not commands available today:

```text
atlas doctor
atlas audit benchmarks/sensor_generalization --mode deterministic
atlas audit benchmarks/sensor_generalization --mode live
atlas compare <run_id_a> <run_id_b>
atlas procedures check <procedure_id> <project_path>
atlas evaluate --suite acceptance
```

## 11 Day one through day three

### Day one October 14

- Confirm workspace location, Git status, actual tools, and account status. Full-day availability is already confirmed. Avoid assuming a cloud terminal is the user's PC.
- Establish a reproducible Python environment, locked dependencies, shared instructions, and the task/check contracts. First close only unresolved PRD/spec questions in a roughly 20-minute requirements interview; ask Gemini for one focused scientific challenge. Use existing handoff decisions as defaults. Do not restart product selection.
- Build seeded faulty and clean fixtures; implement row/group overlap and fit-provenance checks with positive and negative tests.
- Produce an actual evidence JSON report from each fixture. Unsupported provenance must return NOT_ASSESSED.
- Claim Nebius credits and configure the key privately. If available, list models and execute one minimal structured-response call; otherwise continue offline and mark the external blocker.
- Inspect a viable container runtime; no candidate arbitrary-code execution until isolation works.

Exit condition: one demonstrated finding, one clean pass, one unsupported case, and reproducible commands. A small Nebius response is a separate access gate, not grounds to delay all deterministic work.

### Day two October 15

- Implement independent prediction evaluation and dummy baseline; preserve row identity through transforms.
- Add temporal assertions and metadata coverage handling.
- Implement snapshots, isolated execution, artifact capture, explicit timeouts and failure reporting.
- Prove missing files, malformed output, changed row IDs, and attempts to alter trusted evaluation artifacts are rejected.
- Run original and revised evaluation without any LLM and capture the protocol differences.
- Probe the intended hosting/execution arrangement now: establish whether it supports the isolation contract or needs the separate-worker/limited-demo approach in Section 22.5. Do not defer this discovery to recording week.

Exit condition: a manual candidate revision can be evaluated reproducibly; failure cannot silently turn into a clean finding.

### Day three October 16

- Integrate one actual NVIDIA model with typed actions and a bounded loop.
- Translate a supplied claim, run the right supported checks, propose one constrained evaluation patch, execute it, and assemble a report that cites evidence artifacts.
- Log actual tokens, tool calls, retries, and latency; test timeout and invalid-output handling.
- Expose the result in a minimal Streamlit page or CLI if UI time would delay the engine.

Exit condition: one live end-to-end path with a genuine model call. If model access is still blocked, record it explicitly, finish the deterministic path, and prioritize resolving access before adding features.

## 12 Remaining sprint

| Dates | Milestone and acceptance |
| --- | --- |
| Oct 17–18 | Complete bounded evidence modules and original-versus-revised comparison. First end-to-end UI by Oct 18. Start a deployable curated demo early. |
| Oct 19–20 | Procedure schema, admission, retrieval, compatible reuse, and explicit mismatch rejection. No vector DB. |
| Oct 21–22 | Real-data adapter, clean controls, frozen unfamiliar evaluation, and first paired memory comparison. Ask one or two available peers to try a concrete task; record feedback only if actually obtained. |
| Oct 23–24 | Repair observed correctness/usability failures, test clean install, confirm server-side secrets, deploy bounded demo. Test hosted cold starts and rate limits. |
| Oct 25–26 | Feature freeze. Scientific review, evidence exports, README, license/data attribution, runtime failure behavior, and submission draft. |
| Oct 27–28 | Record the demo, check readable text/audio, rehearse under three minutes, verify public links and independent setup. Fix blockers only. |
| Oct 29 | Publish/finalize chosen release and submit. Verify confirmation and submitted links. Keep a timestamped receipt/screenshot privately. |
| Oct 30 before 1 p.m. New York | Emergency correction buffer only. Never plan core implementation for deadline morning. |
| After submission through judging | Maintain the submitted version and required availability; track uptime/credits. Keep later development separate and follow rules for post-deadline changes. |

Availability update from Adnan, October 14: full days are available and his schedule is managed. Do not impose the former 2–3-hour assumption or ask for confirmation again. Keep the five checks, 2×2 synthetic benchmark, real-data example, clean/unfamiliar cases, three-way comparison, and UI/browser verification in planned scope. Use full-day milestones made of bounded tasks; reserve meaningful time for debugging, deployment, and submission. Do not equate all available time with productive engineering time or infer a competition ranking. Dates remain delivery gates, not guarantees. If actual progress slips, remove optional model routing and extra features before weakening core correctness or release evidence.

## 13 Review and quality gates

Correctness: trusted metrics recomputed, claim/split distinction preserved, no fabricated performance drop, no unsupported PASS, meaningful negative controls, final test untouched by tuning.

Reliability: malformed inputs and API failures surface clearly; bounded retries; deterministic artifact IDs/hashes; original files preserved; reproducible setup; no hidden required paid account beyond documented runtime setup.

User experience: one clear primary action; visible run progress; concise evidence cards; code diff accessible; original and revised protocols labeled; limitations near conclusions; replay visibly marked; no decorative dashboard that obscures results.

Evidence: each finding links to its observed inputs and check version. Reports describe what was checked, what failed, what was unassessed, and what changed. Every quoted metric can be regenerated from the release.

Agent contribution: demonstrate adaptation to changed schemas/claims and refusal of invalid reuse, not just narration over a predetermined script. Measure against a fixed audit. Do not claim novelty without a focused related-work comparison.

Scope cuts: no hardware, OS, voice, agents talking to agents indefinitely, arbitrary cloud shell, autonomous package installation, training new models, personal-data ingestion, or unrelated search integrations for a side prize. A dependency or framework must solve a specific observed problem.

## 14 Demo and release package

Video target: about 2 minutes 40 seconds, leaving timing margin. Suggested allocation: 20 seconds problem and claim; 40 seconds evidence investigation; 45 seconds isolated revision and measured result; 35 seconds reuse and mismatch; 20 seconds scope, reproducibility, and closing product view. Show actual executions. If edited for time, label time compression; do not imply an edited run was instantaneous.

The memorable moment is an evidence-backed correction of a research conclusion. A large score drop is optional. A precise, reproducible finding is necessary.

Release assets: tagged public source, MIT license for original code, separate data/dependency notices, pinned setup, container recipe, .env.example, at least one fully offline deterministic example, working live integration instructions, hosted bounded demo or downloadable test build, sanitized example evidence report, architecture explanation, limitations, model-use notes, sponsor feedback, and public video. State where AI coding assistance was used without implying the assistants are NVIDIA runtime components.

README must explain that the project is an early research tool, the supported adapter, the meaning of every check status, the limits of static inspection, and how to reproduce results. No inferred medical efficacy or guarantee that research is valid.

## 15 Ready-to-use collaboration task formats

These are prompt templates, not commands or installed skills.

Implementation task: “Read AGENTS.md and STATUS.md. Implement [one behavior] in [owned paths]. Acceptance: [observable checks]. Preserve [invariants]. Run [relevant tests]. Return changed files, actual results, limitations, and the next task. Do not expand scope.”

Independent review: “Review commit [hash] and these evidence artifacts. Do not edit. Find correctness failures, scientific overclaims, missing negative cases, and unsafe execution paths. Give severity, exact location, a reproducible example where possible, and the smallest fix. Do not approve based only on another model's explanation.”

Scientific challenge: “Given the deployment claim and evaluation protocol, identify conclusions the evidence does not support. Propose one clean control, one applicability mismatch, and one disconfirming experiment. Do not assume a lower score proves leakage.”

Handoff: “Update STATUS.md with commit, working commands, completed acceptance tests, failures, unresolved decisions, and one next task. Separate proposed work from observed results. Do not copy the entire conversation.”

## 16 Sources and verification notes

Links are provenance for checked facts, not a substitute for the build plan. Checked October 14, 2026. Account access, prices, model IDs, rules, and tool interfaces can change. Runtime model access, installation, benchmarks, and billing have not been tested in this planning task.

- S1 Official hackathon rules: https://nebiusglobalaihackathon.devpost.com/rules
- S2 Official FAQ and runtime/credits clarification: https://nebiusglobalaihackathon.devpost.com/details/faqs
- S3 Claude Pro plan: https://support.claude.com/en/articles/8325606-what-is-the-pro-plan
- S4 Claude Code subscription access: https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan
- S5 Official hackathon resources and credits: https://nebiusglobalaihackathon.devpost.com/resources
- S6 OpenAI skill documentation: https://learn.chatgpt.com/docs/build-skills
- S7 Claude Code skills: https://code.claude.com/docs/en/skills
- S8 Canonical Ponytail source: https://github.com/DietrichGebert/ponytail
- S9 scikit-learn common pitfalls: https://scikit-learn.org/stable/common_pitfalls.html
- S10 Nebius API introduction: https://docs.tokenfactory.nebius.com/api-reference/introduction
- S11 Nebius model catalog API: https://docs.tokenfactory.nebius.com/api-reference/models/list-models
- S12 Nebius NVIDIA model offerings: https://nebius.com/services/token-factory/nemotron
- S13 Nebius structured output: https://docs.tokenfactory.nebius.com/ai-models-inference/json
- S14 UCI sensor dataset candidate: https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones

Open questions to settle at kickoff: where the repo will run; whether container execution works; whether Nebius credits and the chosen NVIDIA model are accessible; hosting budget and platform; and the exact independently held-out evaluation case. None requires reopening the overall product choice.

## 17 Model and reasoning effort policy

The following settings are proposed defaults for this sprint, not controlled comparisons of the models. Product UI controls and API fields are not interchangeable. Select the supported setting in the actual application and record the resolved model/version. A chat assistant cannot change settings in another provider's app unless it has a tool that actually performs that action.

Official sources establish that Astra supports low, medium, high, xhigh, and max API reasoning efforts; Gemini Argon supports low/medium/high thinking; Claude Code's available effort levels depend on its selected model. Use the user's actual displayed controls. Never invent an unavailable setting to match this table. [S16, S17, S18]

| Work item | First choice | Escalation and stop condition |
| --- | --- | --- |
| Initial project decisions and PRD consistency | ChatGPT/Codex Astra High | Extra high for ambiguous scientific claims or conflicting requirements; finish once an executable acceptance condition is agreed. |
| Routine coordination, documentation, handoff compression | Available GPT-6 workhorse Medium; Light/Low for simple summaries | Escalate only if important context is being lost. Preserve exact model name rather than assuming GPT-6 means one variant. |
| Scientific correctness or execution-boundary review | Astra Extra high | Max only for a specific unresolved blocker with a small reproduction. Not a default whole-repo reread. |
| Main implementation of evaluator, provenance, or agent loop | Claude Code Opus 5.5 High if offered | Extra high for a difficult reproduced bug; Max for one isolated problem if cheaper attempts fail. |
| Bounded adapters, simple UI plumbing, documentation | Claude Code Sonnet 5.5 Medium if offered | High if coupling or ambiguity appears; move to Opus for a persistent architectural problem. |
| Independent experimental challenge | Gemini 4 Argon High | Ask for counterexamples and checks, not unlimited brainstorming. |
| Demo narration and usability explanation | Gemini Argon Medium | High only if reviewing the scientific accuracy of the claims; Low for formatting or short summaries. |
| Application runtime | Verified NVIDIA model through Nebius | Separate from these development subscriptions and their effort sliders. Use actual provider-supported controls only. |

For Claude, `/model` and `/effort` are documented controls; verify the client and available choices. The current official configuration documents Opus/Sonnet 5.5 among models with low through max support. A subscription named Max does not imply max effort. [S18]

User-visible convention: say “Open Claude Code, select Opus High” followed by the actual packet/task. Do not say only “use a stronger model.” If an exact version is absent, choose the available family member, record it, and do not claim a comparison to the absent version.

Escalation procedure: preserve the failing command and evidence; reduce the problem; ask the existing model for one hypothesis-driven correction; if still blocked, increase effort or give the same bounded case to the independent reviewer. After two unsuccessful repair rounds, reconsider the assumption or simplify scope. Higher effort cannot compensate for missing files, fabricated evidence, or an unavailable tool.

## 18 Sourced development skills and installation policy

The referenced creator is Addy Osmani, not Andy Osmanti. His current canonical repository lists 25 skills. This establishes a real public toolkit; it does not establish that all Google/Amazon engineers use it, that it reproduces their internal workflow, or that installing it makes generated code equivalent to expert-reviewed production code. [S19]

Use a small selected set. Do not run overlapping interview, planning, review, or autonomous execution systems on every change.

| Source | ATLAS decision | Exact occasion |
| --- | --- | --- |
| mattpocock/skills | Use a bounded requirements interview and local spec synthesis | Once at kickoff; again only for a major unresolved product or architectural change. Current source exposes grill-me/grill-with-docs, to-spec and to-tickets; older names may differ. [S20] |
| addyosmani/agent-skills | Selected code-review-and-quality, debugging-and-error-recovery, and test-driven-development | Review substantive changes; diagnose actual failures; test scientific logic and behavior with meaningful negative cases. Keep routine copy edits lightweight. [S19, S21] |
| DietrichGebert/ponytail | Manual simplification pass after correctness | Once per working milestone when code is unnecessarily complex. Preserve provenance, sandbox limits, and error handling. |
| phthomas/pstack | Alternative orchestration, deferred by default | It coordinates specification, execution, and review; it is not just a debloating check. Adopt only if replacing the overlapping workflow rather than adding another controller. [S22] |
| kunchenguid/no-mistakes | Optional later release gate, deferred by default | It can coordinate fixes and Git/PR delivery. Evaluate after the core workflow works; do not install automatic push/PR behavior as a casual review helper. [S23] |
| Playwright Python and microsoft/playwright-mcp | Use repeatable browser tests; optional MCP for agent exploration | When UI behavior exists, then on meaningful user-flow changes and release checks. Prefer existing browser capabilities if sufficient. [S24, S25] |

Matt's current grill-me wrapper delegates to grilling; grill-with-docs delegates to grilling and domain-modeling. Companion skills must be present. Source inspection is required before installation; a seven-line wrapper is not the complete capability. Use a local issue/spec target for this project, respecting the user's authorization rather than a plugin's default publishing behavior. [S26, S27]

Addy's source warns that a per-skill install may omit shared references. Inspect every selected skill's referenced paths and include the required references from the same pinned revision. A skill can be discoverable but incomplete. A full pack can also add lifecycle hooks and commands: review those before enabling. [S19]

Installation procedure for the builder:

1. Confirm the real host/client version and supported skill/plugin format. Do not assume a website chat loads local CLI skills.
2. Inspect the canonical repository, chosen SKILL.md, companion files, hooks, and license. Record an actual commit SHA in docs/TOOLING.md; do not invent one.
3. Install only the selected capability using the host's supported mechanism; keep one canonical copy and deliberate wrappers where necessary. Do not overwrite existing global instructions.
4. Verify discovery, referenced-file resolution, and a small harmless invocation. Record observed outputs and installation state.
5. Disable redundant automatic triggers. Keep one requirements interviewer, one main task controller, and one simplification routine per occasion.
6. If setup exceeds a short session, use the reviewed runbook manually and continue building. Never claim a plugin is installed if only its source was read.

Current local discovery paths include `.claude/skills` for Claude Code and `.agents/skills` for Codex; verify the installed version. Gemini website reviews use an explicit attached rubric and context packet. A Gemini CLI/extension installation is a separate optional workflow, not implied by the student chat subscription. [S6, S7]

Third-party skills remain subordinate to project scope and user instructions. If a skill would publish, modify remote settings, install background services, or perform expensive autonomous runs, assess that concrete action separately. Do not loosen access controls to make a skill run.

## 19 Exact cross-tool handoff protocol

Each provider's chat history is separate. A shared Git repo shares files, not conversations. Local Claude and Codex read the current task/status and exact checkpoint directly; browser reviewers receive an explicit packet when needed.

Stable context, prepared once: PROJECT_BRIEF.md, docs/PRD.md, docs/SPEC.md and AGENTS.md. The first file should fit roughly one page and contain the product, intended user, current scope, runtime requirement, deadline, and main invariants.

Formal packet, prepared for a major architectural/scientific browser review, unavailable shared access, or a substantial ownership transfer: task ID, role, base/head commit or patch ID, exact accessible files, acceptance conditions, what changed, commands actually executed, result artifacts, remaining uncertainty, and requested output. Keep the task packet roughly one to two pages; link/attach evidence rather than pasting all logs. Include negative evidence, not only the success summary.

Proposed packet template:

```text
TASK: A-___
RECIPIENT: Claude builder / Codex reviewer / Gemini challenger
ROLE: implement / read-only review / scientific critique
SOURCE: branch ___; base ___; head ___; uncommitted patch ___
ACCESS: repo path actually accessible OR attached files list
OBJECTIVE: one behavior or decision
ACCEPTANCE: observable assertions
INVARIANTS: scientific, permission, cost and scope constraints
INPUTS: brief/spec sections and relevant files
ACTUAL RESULTS: commands, exit codes, artifact paths, known failures
UNKNOWN: what has not been tested or cannot be inspected
REQUEST: exact work and required return format
WRITE OWNERSHIP: allowed paths or read-only
```

For those external/substantial handoffs, save to handoffs/A-___-recipient.md. For routine same-repo Claude/Codex work, use the existing TASKS.md/STATUS.md entry, a source checkpoint, test artifacts, and a short prompt; no separate handoff file. Record consequential findings once in the task/status record or a dedicated review file if substantial. Before applying findings, check that the reviewed branch/patch still matches.

| Transition | When | Share | Bring back |
| --- | --- | --- | --- |
| Lead -> Claude | First setup and each scoped implementation task | Brief once; current spec/task/status and actual repo access | Diff/commit, tests, artifacts, unresolved issues |
| Lead -> Gemini | After PRD/evaluation design; before public result claims | Brief, claim/protocol, benchmark design or measured evidence | Prioritized counterexamples and checks; no code edits |
| Claude -> Codex | After substantive evaluator, isolation, memory, or UI changes | Task/acceptance, base/head diff, relevant files, actual test artifacts | Severity-ranked findings with evidence and minimum fixes |
| Codex -> Claude | Confirmed review findings | Exact repro, source version, failing assertion, intended behavior | Focused fix plus rerun evidence |
| Builder -> UI evaluator | After behavior-changing UI work | Build ID, URL, test scenario, expected outcomes, test-only data | Browser trace, console/network evidence, screenshots, pass/fail |
| Gemini -> Lead -> Builder | A scientific challenge changes the plan | Original finding and lead's disposition | Updated spec/decision and one bounded task |
| Any writer -> next writer | Usage limit, session end, or deliberate switch | Clean checkpoint, STATUS.md, open errors, next task | New writer acknowledges exact source and ownership |

When services cannot access the same repo, attach the relevant source files and patch or a sanitized snapshot. A GitHub URL works only if the receiving tool actually has access. For private repositories use an authorized connection or explicit attachments. Do not claim access from a link alone. The project lead should generate the packet rather than make Adnan manually reconstruct context.

Context exclusions: API keys, session tokens, personal/private research data, hidden final-test labels, and unnecessary whole-repository dumps. An independent reviewer may create/evaluate a holdout without giving its answer key to the implementation agent. Expected test outcomes can be shared for development checks, not final hidden evaluation.

## 20 ATLAS adversarial and browser evaluation loop

The user requested an adversarial review organized across the full product. Use this ATLAS-specific rubric. It is a proposed rubric, not a claim about any company's internal practices.

| Layer | Reviewer question | Evidence and blocking failure |
| --- | --- | --- |
| User claim | Does the contract match the intended deployment? | Confirmed claim and schema; blocking if the system silently changes the question. |
| Data and protocol | Are rows, groups, chronology, and fit boundaries correctly handled? | Independent assertions; blocking if unsupported coverage is reported as clean. |
| Evaluation authority | Can a candidate influence the oracle or final test? | Mount/access checks and trusted recomputation; blocking if acceptance is self-graded. |
| Agent behavior | Does the model choose useful checks and respect tool limits? | Recorded actions, malformed-output and budget tests; blocking if it executes unvalidated commands. |
| Procedure memory | Is reuse supported by current prerequisites and evidence? | Compatible and mismatch cases; blocking if semantic resemblance overrides a hard mismatch. |
| Interface | Can the user understand status, evidence, changes, and limits? | Browser flows and exports; blocking if an error appears as a verified result. |
| Reproduction and delivery | Can another person run the submitted version? | Fresh install and independent example; blocking if missing keys/dependencies are concealed. |

Return findings as: severity; layer; exact assertion; source version/location; reproduction or evidence; smallest fix; remaining uncertainty. Use BLOCKER for integrity, isolation, or core-flow failure; IMPORTANT for a meaningful reliability/usability defect; OPTIONAL for polish. Do not force numeric “99/100 quality” scores. Independent means fresh evidence and a different review task, not that a second model cannot share the first model's blind spots.

Start with one focused reviewer. Split scientific review from code/browser review only where the change warrants it. Default maximum: one writer and one active reviewer; a separate Gemini scientific review can occur at a milestone. No continuous three-provider debate.

Browser scenarios to implement:

1. Select a supported faulty project, confirm its claim, run the investigation, inspect evidence, preview the revision, and export a report. Assert both visible content and agreement with engine artifacts.
2. Run the clean control. No fabricated leakage finding; limitations remain visible.
3. Open unsupported/missing metadata. Show NOT_ASSESSED and a useful next action, not a green pass.
4. Force a provider timeout or invalid response in a test environment. End in a clear recoverable state; no hidden endless retry.
5. Retrieve a procedure for the temporal mismatch case. Refuse or require a new protocol; explain the failed prerequisite.
6. Refresh/rerun or double-click the action. Ensure stale results are labeled and duplicate costly execution is prevented according to the defined UI policy.

Repeatable tests should use Playwright Python with deliberate assertions. Browser-agent tools/MCP are useful for exploratory diagnosis; merely clicking around is not an automated regression suite. A screenshot proves appearance at a moment, not that calculations or server state are correct. Playwright is sufficient initially; Puppeteer is an alternative, not a required second stack. [S24, S25]

For a UI change, follow this exact bounded loop:

1. Freeze the acceptance scenario and source/build ID.
2. Builder implements and runs targeted engine checks.
3. Evaluator starts a clean browser session against the actual running build.
4. Save failed assertions, reproduction steps, console/network errors, and traces/screenshots.
5. Builder fixes the smallest established cause; it may not weaken the acceptance requirement merely to pass.
6. Evaluator reruns the same scenario and affected regressions on the new build.
7. After two unsuccessful repair cycles, stop automatic iteration. Reproduce/minimize, check whether the test or implementation is wrong, and obtain a specific design decision if needed.

Use deterministic offline provider fixtures for routine UI tests and a separately capped real Nebius smoke run before release. Offline fixtures must not be presented as live runtime proof. Browser testing cannot certify scientific validity; both layers are required.

## 21 Sequential operating rules and new sources

The lead assistant's next-action format is mandatory for this beginner-friendly workflow:

```text
STEP: number and one objective
MODEL DECISION: STAY or SWITCH, with a concrete reason
OPEN: exact application or terminal context
SELECT: available model and effort, plus the actual control to change
SHARE: exact packet/files or accessible repo
DO/PASTE: one bounded action
DONE WHEN: observable result
RETURN: exact result and destination
IF BLOCKED: a concrete fallback that preserves the goal
```

Do not dump all setup commands at once or require Adnan to remember provider-specific chat history. The lead executes steps it can access and only asks him to perform account/device actions it cannot. Do not ask for confirmation repeatedly for already authorized reversible work. Buying a plan is Adnan's account action; the plan does not authorize the agent to make purchases or publish material without the relevant request.

Skill/tool choices should be frozen after the first working end-to-end slice unless a specific missing capability blocks delivery. A new skill discovery is not a reason to restart the architecture. The current workflow can be revised with evidence, but keep one documented source of truth.

Additional sources checked October 14, 2026:

- S15 Claude Max tiers: https://support.claude.com/en/articles/11049741-what-is-the-max-plan
- S16 Astra model controls: https://developers.openai.com/api/docs/models/gpt-6-astra and model selection guidance https://learn.chatgpt.com/docs/model-selection
- S17 Gemini Argon controls: https://ai.google.dev/gemini-api/docs/models/gemini-4-argon
- S18 Claude Code model and effort configuration: https://code.claude.com/docs/en/model-config
- S19 Addy Osmani canonical toolkit: https://github.com/addyosmani/agent-skills
- S20 Matt Pocock canonical toolkit: https://github.com/mattpocock/skills
- S21 Addy debugging skill source: https://raw.githubusercontent.com/addyosmani/agent-skills/main/skills/debugging-and-error-recovery/SKILL.md
- S22 pstack: https://github.com/phthomas/pstack
- S23 no-mistakes: https://github.com/kunchenguid/no-mistakes
- S24 Playwright Python: https://playwright.dev/python/docs/intro
- S25 Microsoft Playwright MCP: https://github.com/microsoft/playwright-mcp
- S26 Matt grill-me wrapper: https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity/grill-me/SKILL.md
- S27 Matt grill-with-docs wrapper: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/grill-with-docs/SKILL.md

Source review establishes identities and documented behavior, not successful installation or measured effectiveness on ATLAS. No reviewed third-party skill was installed during this handoff revision.

## 22 Installation recipe for the coding agent

Adnan follows Start Here. This section is the builder's technical task, not another list he must execute manually. Perform each reachable action yourself, explain only the next manual/account step, and record observed results in docs/TOOLING.md. Confirm whether the terminal is native Windows PowerShell, Git Bash, WSL, or cloud before choosing commands.

### 22.1 Base environment

Start Here supplies the native Windows package-manager commands for VS Code, Git, Claude Code, and uv. Reuse installed tools. Sign into Claude Code with the account holding Max; the runtime Nebius key is unrelated. Install the official Codex extension in the same local VS Code folder for reviews; a second CLI installation is optional. [S28–S33]

For a new repository, the builder initializes Git and the uv Python project without overwriting files. Use Python 3.11 unless an observed dependency conflict requires a recorded change. Resolve numpy, pandas, scikit-learn, Pydantic, Streamlit, the selected HTTP/OpenAI-compatible client, and private environment-file loading. Add pytest and Ruff as development dependencies. Commit the dependency manifest and lockfile. Configure imports and a package entry point before writing commands that assume an atlas executable exists.

Verify by actually importing dependencies, running the initial test command, and recording it. Prefer uv run so the user does not have to manage virtual-environment activation. Do not report a test command as passing when no tests were collected. An initial import check proves setup, not product behavior.

Set up .gitignore before credentials or vendor clones appear. Exclude .env, caches, virtual environments, raw private data, generated artifacts by default, and .dev/skill-sources/. Keep .env.example with placeholders. Confirm exclusions with Git before asking the user to insert secrets. Configure Git name/email only with the user's supplied identity.

### 22.2 Selected skills: default installation route

Use project-local skill folders so the setup travels with the repository. Codex discovers .agents/skills; Claude Code discovers .claude/skills. Keep supporting references and license notices with the selected material. A web chat does not acquire these folders merely because it uses the same provider account. [S6, S29]

The default is a selective local copy, not a whole-plugin install. This is an ATLAS packaging choice, not an assertion that upstream recommends it for every user.

1. Fetch canonical repositories over HTTPS into ignored .dev/skill-sources/ subfolders. Use Git to record each actual commit SHA; never type a guessed SHA into the manifest. Read the relevant license, SKILL.md files, references, scripts, hooks, and companion-skill calls before enabling them. Do not run fetched setup scripts merely to inspect source.
2. Start with Matt's setup-matt-pocock-skills, grill-with-docs, and to-spec. Include the complete dependency closure discovered in the chosen revision, including grilling and domain-modeling where called. The source tree groups engineering/productivity skills; locate the actual folders rather than assuming every skill sits directly under skills/. [S20, S27, S34]
3. Select Addy's code-review-and-quality, debugging-and-error-recovery, and test-driven-development. Include required shared references. Upstream explicitly documents a missing-shared-reference issue with single-skill installs; discovery alone is insufficient. [S19]
4. Copy each selected skill to .agents/skills/<name>/ and .claude/skills/<name>/, preserving SKILL.md and required assets. Use ordinary copies on Windows to avoid requiring privileged symlinks. Keep both copies generated from the same pinned source and compare their checksums. If adapting a source-relative reference to a project-local destination, document the adaptation and verify the new path; do not silently drop referenced instructions. Do not overwrite an existing skill with the same name.
5. Keep dependency-only skills as dependencies rather than adding duplicate workflow controllers. Do not enable third-party lifecycle hooks, automatic release commands, global Git URL rewrites, or whole-pack meta-prompts for this initial setup. Do not modify global user instructions.
6. Preserve attribution and applicable licenses. Record repo URL, commit, selected paths, copied dependencies, any adaptation, local destinations, invocation name, and loading status in docs/TOOLING.md. The project's MIT license does not replace upstream notices.
7. Restart the relevant agent session if discovery is stale. Use each client's actual skill selector/help; verify Claude can invoke the installed setup skill and Codex can discover the review skill. Do not guess that a Claude slash command is also a Codex command.
8. Run one harmless verification: ask the review skill to explain which supplied acceptance criteria it would inspect, without editing or publishing. Require it to load a referenced checklist successfully. Record whether that invocation happened through the native loader or by manually reading the runbook.

This can be executed by Claude after the Step 6 prompt. It may create a small project script to sync the selected copies from pinned sources if that saves repeated manual work. Do not build a general skill manager.

Suggested source-fetch commands for the builder, executed from the actual repository root if the destinations do not already exist:

~~~powershell
git clone https://github.com/mattpocock/skills.git .dev/skill-sources/matt
git clone https://github.com/addyosmani/agent-skills.git .dev/skill-sources/addy
git -C .dev/skill-sources/matt rev-parse HEAD
git -C .dev/skill-sources/addy rev-parse HEAD
~~~

Do not pull new revisions automatically during the sprint. Revalidate a deliberate update. When adding Ponytail after the first successful slice, fetch DietrichGebert/ponytail, inspect skills/ponytail/SKILL.md and its dependencies, and apply the same installation/verification procedure. Begin with one explicit review task; do not activate an always-on policy that conflicts with ATLAS's evidence requirements.

Fallback: if loading is blocked, keep the inspected text in a documented local runbook and invoke it by explicit file reference. Mark it manual-only. Do not spend the first day debugging optional plugin plumbing.

### 22.3 Optional packaged installation

Packaged installation is an alternative if selective copies become harder to maintain; do not install both copies and plugins for the same skills. Current upstream documentation lists these routes:

| Toolkit | Documented route | ATLAS condition |
| --- | --- | --- |
| Matt | Claude CLI: claude plugin install mattpocock-skills@claude-plugins-official | Inspect the installed scope and configure local files before invoking setup |
| Addy | Claude chat: /plugin marketplace add addyosmani/agent-skills, then /plugin install agent-skills@addy-agent-skills | Whole pack; use only if deliberately replacing selected copies |
| Addy for Codex | Terminal: codex plugin marketplace add addyosmani/agent-skills, then codex plugin add agent-skills@agent-skills | Requires a compatible installed Codex CLI; not needed for the initial extension-only path |

Check the current upstream/client help before execution. These commands are documented examples, not installation results. Addy's Codex setup warns against pasting its entire meta-router into always-on AGENTS.md. [S19, S34, S35] No need to add pstack, no-mistakes, Puppeteer, a second IDE subscription, or a Gemini CLI for the default sprint workflow.

### 22.4 Browser verification

At Start Here Step 12, the builder adds Playwright testing to the existing Python environment. These are proposed commands to execute when the UI/test infrastructure exists:

~~~powershell
uv add --dev pytest-playwright
uv run playwright install chromium
~~~

Implement tests in tests/acceptance/ using stable labels/roles where possible. Start the local app, wait until it is ready, run the actual tests, and capture failure artifacts. Run this in a second terminal or managed process so the app keeps running during tests. Record the tested URL/port and exact launch/test commands. Use fixture-backed browser tests routinely, plus a separately capped live-provider smoke test. [S24]

An evaluation agent can execute these tests with its terminal; browser MCP is optional for exploratory interaction. If the available browser integration already works, use it.

If MCP is needed, give the builder this task:

> Inspect the current Microsoft Playwright MCP installation and this client's MCP configuration. Install a supported Node LTS only if missing. Add one project-scoped browser connection using a pinned package version and an isolated test browser profile. Preserve existing settings. Verify that the agent can open our local test app and inspect a page. Record the exact connection, package version, and observed result. Do not connect it to my personal browsing profile or make it a deployment dependency.

The upstream Claude registration pattern uses claude mcp add with npx and @playwright/mcp; the builder should resolve the actual package version and confirm CLI arguments/scope with installed help. An MCP registered in one client is not automatically registered in another. Python Playwright tests do not require this MCP server or a Gemini installation. [S25]

### 22.5 Docker and deployment prerequisites

On native Windows, Docker Desktop can supply Linux containers using its supported backend. Confirm Windows/virtualization requirements, then guide the user through the official installer and any required restart. Keep OS changes explicit. After Docker starts, check both client/server availability and an ordinary container run. Then test ATLAS's actual restricted runner; installation alone is not isolation validation. [S36]

At the first deployable slice, identify whether the host permits the required isolated execution. A simple Python host is adequate only if its implemented demo does not need prohibited child-container privileges. Do not mount a host Docker socket into a public app or claim replay is live. If deployment is blocked, preserve a working local test build and resolve a concrete judging-access plan before release.

The rules require a URL to a working demo, hosted application, or test build; they do not mandate a fully hosted application. We still prefer a convenient hosted experience. Do not weaken execution boundaries to satisfy an incorrectly inferred hosting requirement. [S1]

Choose among these explicit delivery modes after the early hosting probe:

| Mode | What executes | Required disclosure and verification |
| --- | --- | --- |
| Full live hosted workflow | UI/controller calls a separately isolated execution worker or suitable job service | Verify per-run boundaries, credentials separation, resource limits, cleanup, and costs. Do not assume a provider isolates arbitrary code merely because it offers jobs. |
| Limited hosted workflow plus full local build | Hosted app uses reviewed, fixed evaluation functions with schema-validated parameters; generated patches are displayed but not executed there | Label the hosted limitation. Demonstrate and test full patch execution in the isolated local build. A curated input dataset does not make newly generated code trusted. |
| Downloadable test build | Judges run the documented full workflow in a supported environment with verified isolation | Provide a working URL, clean-install evidence, and a free judging-access arrangement for required inference; a repository alone is not an adequate substitute for a tested build path. |

For the limited mode, parameters must select only allowed operations and bounded values. No eval/exec, generated Python imports, arbitrary shell strings, or uploaded executable artifacts enter the trusted host path. Merely changing the subprocess working directory leaves ordinary process access in place; timeouts bound duration, not file/network permissions. Our engineering conclusion is that these conveniences do not meet ATLAS's isolation contract. [S43] Docker's own documentation also distinguishes kernel isolation from daemon/configuration risks; its default presence is not proof of the full contract. [S44]

The runner should report capability explicitly: isolated execution available, trusted-pipeline-only, or unavailable. If isolated execution fails, fail closed for candidate code. Never retry the same generated code through an unsandboxed subprocess as an automatic fallback.

### 22.6 Additional setup sources

- S28 Claude Code Windows installation: https://code.claude.com/docs/en/setup
- S29 Claude skill discovery/invocation: https://code.claude.com/docs/en/skills
- S30 uv installation: https://docs.astral.sh/uv/getting-started/installation/
- S31 Git for Windows: https://git-scm.com/install/windows
- S32 VS Code on Windows: https://code.visualstudio.com/docs/setup/windows
- S33 Codex IDE extension: https://learn.chatgpt.com/docs/codex/ide
- S34 Matt installation/configuration: https://raw.githubusercontent.com/mattpocock/skills/main/README.md
- S35 Addy Codex setup: https://raw.githubusercontent.com/addyosmani/agent-skills/main/docs/codex-setup.md
- S36 Docker Desktop Windows prerequisites: https://docs.docker.com/desktop/setup/install/windows-install/
- S37 Hackathon submission page: https://nebiusglobalaihackathon.devpost.com/

## 23 Devpost checklist tied to actual artifacts

Create docs/SUBMISSION_CHECKLIST.md during setup. Each row needs status, evidence path or submitted URL, last-checked date, and a concrete next action. Keep it current at milestones rather than discovering missing assets on the last day. Sources S1, S2, and S37 establish the requirements; artifact names below are our implementation choices.

| Requirement | ATLAS evidence to prepare | Gate |
| --- | --- | --- |
| Eligible registered entrant and correct track | Devpost draft: Coding and Agentic Engineering | Kickoff |
| Working NVIDIA model on Nebius | Sanitized runtime trace; model ID; reproduced code-edit/check workflow | Live-agent milestone |
| Working demo/test-build URL | Hosted curated app or tested accessible build with instructions | First deployable slice; verify at release |
| Public repository and open-source license | Release commit/tag, LICENSE, visible license detection, required assets | Packaging |
| Setup and model-use explanation | README clean-install steps and exact NVIDIA/Nebius role | Fresh-install check |
| Project description | Problem, audience, implementation, measured evidence, limits | Draft before freeze |
| Public YouTube demonstration | Under-three-minute video of actual behavior | Recording |
| Sponsor-tool feedback | Specific observed benefits/problems and reproduction details | Log during development; submit at release |
| Prior-work changes, if applicable | Accurate statement of what predates the event | Packaging |
| Judging access and English materials | Free working test path through December 15; instructions and translation if needed | Release |
| Deadline and successful entry | Target October 29; verify October 30, 13:00 New York deadline and confirmation | Submission |

Our Coding track has no Physical AI URL exemption. The final test path must let judges exercise the project without buying credits; settle hosting/access and its funding explicitly. Keep runtime API keys server-side, not in public setup files or video. If a test build needs credentials, provide a suitable judging arrangement privately rather than placing a real provider key in the repo.

Pre-submit procedure: open the exact three submitted links—code, demo/build, video—from a fresh browser session; complete the advertised workflow; check the release matches the recording; fill every required form field; submit; retain confirmation. Maintain the submitted release during judging and handle post-deadline changes according to current rules.

The four judging dimensions become four product checks: implementation has real model/tool evidence; design supports a complete user task; impact is tied to a specific researcher problem; the idea demonstrates scientifically justified adaptation and invalid-reuse detection. These are our quality targets, not predicted scores or prize odds.

## 24 Task cards: turn the roadmap into executable work

The lead establishes milestone order and the builder maintains the current task in TASKS.md. A task card is a concise structured entry, not a required separate file. Use handoffs/ only when the external-review/access conditions in Section 19 apply. Do not make the user translate architecture into coding instructions. Each substantive task contains:

~~~text
TASK ID / CURRENT START-HERE STEP
OWNER: one writer or a read-only reviewer
MODEL DECISION: STAY or SWITCH, reason
MODEL / EFFORT: actual available choice and control
READ FIRST: exact accessible files
INPUT STATE: branch/checkpoint and relevant assumptions
CHANGE: one behavior, owned paths, explicit limits
ACCEPTANCE: observed success, failure, unsupported cases as applicable
RUN: commands known to exist; otherwise create and verify them first
EVIDENCE: report/log/trace paths and tests actually executed
HANDOFF: next reviewer and exact packet to send, if review is needed
RECOVERY: what to capture on failure; two repair rounds before diagnosis
~~~

At task completion the builder updates STATUS.md with the checkpoint, writer, actual model, successful commands, failures, remaining risks, next task, and relevant submission checklist changes. It supplies a short next-task/review pointer before a local model switch and creates a formal packet only when Section 19 calls for one. Routine local implementation/review does not need browser-lead approval each cycle.

Scope-change rule: routine UI/documentation stays Sonnet Medium; evaluator, isolation, tool dispatch, or procedure semantics move to Opus High. Scientific ambiguity or persistent reproduced failures can trigger Astra Extra high review. Gemini High is used when experimental conclusions need challenge, not as a mandatory daily code reviewer. Max effort gets one narrow blocker and a stop condition. A successful resolution returns to the normal setting.

Keep both source access and authority explicit. The Codex extension may read the same local repo, while a browser lead/Gemini may only see attachments. All reviewers must name the files/evidence they actually saw. A review packet cannot grant access to private holdout answers or override the immutable evaluator.

## 25 UI design: an engineering workspace worth using

The intended delivery is a browser application with a hosted curated demo and a reproducible local version. Hosting is a deployment decision still to implement. Visual quality matters in the actual analysis workflow as well as the introduction screen. Keep Streamlit for V1 unless a short prototype demonstrates that a required interaction is impractical. A separate React frontend offers more layout control but adds implementation, testing, and deployment work; it is not an automatic improvement to this sprint.

### Selected skills and tools

| Capability | Choice | Trigger and owner |
| --- | --- | --- |
| Visual direction | Anthropic frontend-design | Claude Opus High before the first full UI screen; produce a concrete visual specification |
| Framework implementation | Streamlit's bundled developing-with-streamlit guidance and relevant references | Claude during UI work; load theme, layout, state, and performance guidance as needed |
| UI engineering review | Addy frontend-ui-engineering | Codex High after a complete interaction exists; review accessibility and state handling alongside visual consistency |
| Rendered behavior and screenshots | Playwright Python, existing browser tools, optional browser MCP | Run actual user scenarios; inspect screenshots and failure evidence |

Anthropic's skill guides visual choices; it is not an installed component library. Addy's skill covers UI engineering, but framework-specific examples must be adapted to our Python application. Keep the existing scientific correctness rubric alongside the design review. [S38, S39]

Streamlit's current upstream notes move skill development into the Streamlit package. For a compatible pinned version, inspect `uv run streamlit skills --help`, then use `uv run streamlit skills` and choose the supported project-local route. Verify which files load in Claude and Codex. Check version and dependency compatibility first; do not blindly upgrade the entire environment. If Windows symlinks fail, use the inspected manual-copy/discovery fallback and record it. Record the package version and regenerate environment-linked installs on a fresh clone; machine-specific links are not portable artifacts. [S40]

Install Anthropic's selected frontend-design folder using Section 22's source/license/dependency checks. Add Addy's frontend-ui-engineering to the existing selected source revision. Do not install whole extra skill collections. Vercel's web-design-guidelines was also inspected; keep it optional because it overlaps with the chosen review and does not replace rendered tests. [S41]

### The ATLAS design brief

Audience: engineers and researchers assessing an experiment, including a judge encountering the tool for the first time. Aim for a precise, composed technical workspace with readable dense information and clear primary actions. Use a restrained palette, strong alignment, deliberate typography, and consistent component spacing. Reserve status colors for meaningful outcomes and always include text labels.

| Area | Content and purpose |
| --- | --- |
| Navigation | Projects, runs, and saved procedures; clear current selection |
| Claim header | Editable deployment claim, dataset/schema context, and one obvious analysis action |
| Findings | Prioritized evidence, check status, coverage, and limitations |
| Comparison | Original/revised protocols and measured metrics, with units and matching evaluation context |
| Revision detail | Readable patch diff and verification outcomes |
| Procedure detail | Required prerequisites, applicability result, evidence, and refusal reason where relevant |
| Run details | Actual execution stages, model identity, timings, and downloadable report |

Use charts only when they clarify a comparison. Keep precision, axes, labels, and displayed numbers consistent with the evidence report. Mark sample/mock data visibly during UI development. The backend controls scientific results; styling must not manufacture impressive numbers or progress.

Streamlit supports native theme configuration for typography, surfaces, borders, and colors. Prefer supported configuration and components; document and test any targeted CSS rather than depending on incidental generated DOM classes. [S42]

### The UI milestone, in order

1. **Claude Opus High:** write docs/UI_SPEC.md with the main analysis screen, typography/colors/spacing, actions, component states, and viewport targets. Use real ATLAS terminology and representative evidence. Limit the initial design exercise to one focused session.
2. **Claude builds one complete path:** selection → claim confirmation → analysis → finding → revision comparison → report export. Implement its empty, running, failure, unsupported, and completed states. Add procedure reuse/refusal when the engine supports it.
3. **Inspect the render:** capture the main screen and important states at 1440 × 900 and a narrower desktop width, then check a narrow phone viewport for usable access. Wide code/tables may scroll within their own regions; navigation and primary actions must remain reachable. Check keyboard focus, readable contrast, wrapping, chart labels, and loading/error recovery. Screenshots alone do not establish accessibility.
4. **Codex High reviews:** use actual rendered artifacts plus the source, selected UI skill, and acceptance criteria. Return specific defects and evidence. Claude repairs the confirmed problems; rerun affected browser scenarios. Use Section 20's bounded repair loop.
5. **Gemini Medium reviews the demo presentation:** provide screenshots/video and the intended user task. Ask whether someone unfamiliar with ATLAS can identify the claim, finding, and correction. Bring actionable feedback to the lead; do not reopen the whole design without evidence.

Exit condition: a new user can complete the supported workflow, understand what the evidence does and does not establish, and recover from a failed run. The interface remains legible in the demonstration video. Skill installation alone does not satisfy this gate.

Sources checked October 14, 2026:

- S38 Anthropic frontend-design: https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/SKILL.md
- S39 Addy frontend-ui-engineering: https://github.com/addyosmani/agent-skills/blob/main/skills/frontend-ui-engineering/SKILL.md
- S40 Streamlit skill migration and installation notes: https://github.com/streamlit/agent-skills ; maintained source: https://github.com/streamlit/streamlit
- S41 Vercel web-design-guidelines: https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills/web-design-guidelines/SKILL.md
- S42 Streamlit theming: https://docs.streamlit.io/develop/concepts/configuration/theming
- S43 Python subprocess process/working-directory semantics: https://docs.python.org/3/library/subprocess.html
- S44 Docker isolation and configuration considerations: https://docs.docker.com/engine/security/
