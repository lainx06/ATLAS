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

### Step 8 scientific-review agenda (accumulating)
- (from Q3) Exact instrumentation design and bypass tests for the in-process recorder; required before implementation is accepted.
- Consolidated list with priorities: docs/SPEC.md §14 (five priority questions for `handoffs/science-01.md`, plus further items).
- **ADR pointer (2026-10-14):** Q3's architecture is recorded as docs/adr/0001-project-owned-evaluation-with-in-container-recorder.md (proposed until Step 8).
