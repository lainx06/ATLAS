# ATLAS UI specification (T-07, draft)

Status: **draft for review; nothing here is built.** No `app.py` exists yet. This spec describes the first complete browser path for the local build (Streamlit, playbook §25) and the labels the limited hosted demo must carry. Every displayed value is tied to an existing report or log key. Anything the engine does not produce today is marked **GAP** and listed in §11. The UI invents no engine feature, and styling never manufactures a result.

Sources read: TASKS.md T-07; docs/PRD.md "Workflow" and "Outcomes the user sees"; docs/SPEC.md §6 and §13; docs/handoff/ATLAS_Build_Playbook.md §20 and §25. Field names were checked against the engine at `d870275` (`src/atlas/agent/controller.py`, `report.py`, `budget.py`, `preflight.py`, `approval.py`, `checks/independent_metrics.py`) and against a real NON-LIVE run's artifacts.

**Key notation.** `agent_report.json:a.b` is a key path in the run's report. `[]` is a list element, and `[k=v]` is the element whose `k` equals `v`. `agent_log.jsonl:event=X.f` is field `f` of log lines whose `event` is `X`. `<run>` is the agent run directory (`runs/agent-<project>-<id>/`), `<run>/original/` the original's evaluated run, and `<run>/candidates/cN/` candidate N.

---

## 1. Truth rules (they override layout and style)

1. **Exact vocabulary.**
   - Run outcomes are shown as their code plus the PRD plain-language label, never paraphrased into "valid", "correct", "pass" or "fixed":

     | Code (`scientific_outcomes.*`, `outcome.json:outcome`) | Label shown with it |
     | --- | --- |
     | `VIOLATION_FOUND` | The evaluation breaks at least one requirement of this claim. |
     | `NO_VIOLATION_FOUND` | Every required check passed within the coverage shown. |
     | `INCONCLUSIVE` | No violation established, but required evidence is incomplete. |
     | `NOT_SUPPORTED` | ATLAS can't assess this claim or project in V1. |

     Under every outcome, a fixed line: "This does not say the scientific claim is true or false."
   - Check statuses are `PASS`, `FAIL`, `NOT_ASSESSED` and `ERROR`, each with its reason code (`outcome.json:assertions[].reason`).
   - Colour is never the only signal; the code is always printed.
2. **Model-written text is labelled.** Text from `agent_report.json:model_text[]` is shown in a distinct "model-written" style with the engine's own label (`model_text[].label`: "model-written text; not evidence and not an outcome"). This covers the patch rationale and the finish summary.
3. **Spend is an estimate, never a bill.**
   - Costs come only from `agent_report.json:cost` and are headed **"Estimated cost (not a bill)"**.
   - `known_usd` is shown as "from reported usage at listed prices" and `unresolved_usd` as "held for unknown usage".
   - `cost.unresolved_note` and `cost.note` are shown verbatim.
   - For fixture runs, `cost.applicable == false` displays `cost.reason` ("fixture replies: no provider request").
4. **Live or not, always visible.** A persistent banner shows `agent_report.json:banner` and `mode` / `live`. A NON-LIVE run can never look live.
5. **Execution is not the outcome.**
   - Each candidate's execution status (`comparison.candidates[].execution.status`) is shown next to, never instead of, its scientific outcome (`comparison.candidates[].scientific_outcome`).
   - The comparison basis (`comparison.comparison_basis`) is printed above the comparison.
6. **Hosted mode** (planned, GAP-5). Every generated diff carries "**not executed here**", and corrected-protocol results carry "computed by ATLAS's trusted evaluation functions" (SPEC §13). Neither is presented as validating the displayed diff.
7. **Errors stay errors.** `terminal_state` ERROR, BUDGET_EXHAUSTED or NEEDS_INPUT is never rendered with success styling or a check mark.

---

## 2. Judge-first layout: the 30-second read

One screen answers, top to bottom: **what was claimed**, **what ATLAS found**, **what the revision changed**, and **how far to trust it**.

```text
+--------------------------------------------------------------------------------------------+
| ATLAS · LENS              [NON-LIVE RUN: fixture replies]   policy-v1.3   run agent-s01_…  |  <- banner
+-----------------------+--------------------------------------------------------------------+
| Projects              |  CLAIM  "The activity classifier works on people absent from      |
|  > s01_faulty         |          training."   unseen_group · unit: subject · repeated      |
|    s02_clean          |          measures (subject_id, session_id)        [Confirm & run] |
|    s06_missing_meta   +--------------------------------------------------------------------+
|    s08a_combined      |  FINDING   VIOLATION_FOUND                                         |
|                       |  The evaluation breaks at least one requirement of this claim.     |
| Runs                  |  4 of 9 required checks FAIL · 0 NOT_ASSESSED · 0 ERROR            |
|  agent-s01_…  REPORT  |  FAIL split.no_group_overlap · FAIL fit.state_dependencies_within_…|
|                       +--------------------------------------------------------------------+
| Capability            |  REVISION   candidate 81f691409a67 · executed in Docker · completed|
|  Docker: available    |  ORIGINAL  VIOLATION_FOUND  ->  CANDIDATE  NO_VIOLATION_FOUND      |
|  Live: needs go-ahead |  4 checks FAIL -> PASS · 5 unchanged PASS   [View diff] [Compare]  |
|                       +--------------------------------------------------------------------+
|                       |  TRUST  Fixture replies only · development fixture · limitations(5)|
|                       |  Estimated cost (not a bill): none, fixture replies   [Export]     |
+-----------------------+--------------------------------------------------------------------+
```

- The left rail holds navigation (projects, runs, capability). The main column has four stacked cards (Claim, Finding, Revision, Trust), each expandable into its detail view (§4).
- The headline is one line of code plus label; it is never a score.
- A judge who reads only the first line of each card has the claim, the outcome, the change and the caveats.

---

## 3. Modes the UI offers

| Mode | Engine entry | Available when | Label |
| --- | --- | --- | --- |
| Deterministic audit | `atlas.audit.audit(project, runs_dir)` (the CLI's `--mode audit`) | Allowlisted trusted fixtures | "Deterministic audit: no model" |
| Agent, fixture replies | `controller.run_agent(..., FixtureClient)` (the CLI's `--fixture-script`) | Docker available (`runner.docker.probe().state`) | `banner` (NON-LIVE) |
| Agent, live | the CLI `--live` path | **Disabled in the T-07 UI.** One authorized live run was completed on 2026-10-17 (`runs/live1`); any further live run needs the lead's explicit go-ahead. Live access in a hosted UI is T-12 | Shown greyed out with "Live runs need the lead's explicit go-ahead" |
| Limited hosted | none | **GAP-5** | "not executed here" rules (§1.6) |

**Capability state** (left rail) comes from `atlas.runner.docker.probe()`: `state`, and `reason` when unavailable. The UI never falls back to host execution when Docker is unavailable; it shows the engine's `original_not_executed` result (§5).

---

## 4. The acceptance path, step by step

### 4.1 Select

- **Content:** a fixed list of curated development fixtures, labelled "development fixtures (synthetic), not benchmark evidence" (GAP-2: the engine has no catalogue API):

  | Fixture | Purpose |
  | --- | --- |
  | `benchmarks/t01/s01_faulty` | The faulty main case |
  | `s02_clean` | Clean control |
  | `s06_missing_metadata` | Missing metadata |
  | `s07_unimplemented_window` | Truthfully declared overlapping windows (NO_VIOLATION_FOUND under policy-v1.3; INCONCLUSIVE under v1.2, hence the name) |
  | `s08a_combined_claim` | NOT_SUPPORTED |

- **Fields:**
  - the project name;
  - `atlas_manifest.json:claim.statement` (read through `atlas.intake.load_project`);
  - the last run, if any (newest `runs/agent-<project>-*` directory and its `terminal_state`).
- **Empty state:** "Choose a project to see its claim." No run button.

### 4.2 Confirm claim

- **Fields** (read-only), from `atlas_manifest.json:claim` via `load_project(project).manifest.claim`:
  - `type`: one of `same_population`, `unseen_group`, `future_time`;
  - `statement`;
  - `sampling_unit`;
  - `dependence[]` (`kind`, `column`);
  - `columns` roles: `target`, `group_id`, `unit_id`, `observation_id`.

  After a run, the same values come from `<run>/original/report.json:claim`.
- **Action:** "Confirm & run", which records nothing new; it starts §4.3.
- **GAP-1:** the PRD's model-pre-filled, user-editable claim does not exist. The engine reads only the manifest's claim, so V1 shows it for confirmation and cannot edit it.
- **Unsupported:** if intake reports the claim or project unsupported, the run ends `NOT_SUPPORTED`. The card shows the code, its label, `agent_report.json:terminal_reason`, and a next-action line keyed to the reason (GAP-10).

### 4.3 Analyze (running state and live trace)

The run is started in a background worker. The UI follows `<run>/agent_log.jsonl`, which the engine appends during the run (`controller.py: log()`), and renders the **agent trace**:

| Trace element | Source |
| --- | --- |
| Stage timeline: INTAKE → APPROVAL (original) → CHECK → MODEL → INSPECT / PROPOSE_PATCH → APPROVAL (candidate) → EXECUTE → VERIFY → … → terminal | `agent_log.jsonl:event=state.state`, `.detail`, `.time_utc`; after the run `agent_report.json:states[]` |
| Model attempts **N of 6** | count of `event=model_attempt` lines; limit `agent_report.json:budget.limits.model_attempts` (6); final `budget.used.attempts` |
| Per attempt: action chosen, result, retry, elapsed, token usage | `event=model_attempt.tool`, `.result`, `.retry`, `.elapsed_s`, `.usage.prompt_tokens`, `.usage.completion_tokens` |
| Per attempt, live only: request ID, served model, identity check | `.request_id`, `.served_model`, `.reply_identity`; `.withheld_fields` shown as "withheld (unchecked)" |
| Tool calls | `event=tool.tool`, `.args`, `.result_chars`, `.result_sha256` |
| Approvals | `event=approval.kind`, `.decision`, `.approver_reason`, `.candidate_hash` |
| Refused before sending | `event=model_request_refused.result` (`input_over_ceiling`, `spend_cap`), and `.projected_usd` / `.estimate_cap_usd` for `spend_cap` |
| Tool operations and revisions used | `budget.used.tool_operations` of `budget.limits.tool_operations` (12); `budget.used.revisions` of `budget.limits.candidate_revisions` (2) |
| Active time (approval wait excluded) | `budget.active_s` of `budget.limits.active_s`; `budget.approval_wait_s` shown separately |
| **Running cost estimate** | `event=model_attempt.cost` (since slice 4c; GAP-3 closed). Live runs: that attempt's ledger entry (`status`, `known_usd`, `unresolved_usd`, the same values as `agent_report.json:cost.entries[]`), under "Estimated cost (not a bill)". Fixture runs: the value is "not applicable (fixture)", shown as "No provider cost (fixture replies)". |

The running state disables the action buttons (§6, scenario 6). An approval request appears as a blocking panel (§4.5).

### 4.4 Finding (the original's evidence)

- **Headline:** `agent_report.json:scientific_outcomes.original` (audit mode: `outcome.json:outcome`), its label, and the fixed "does not say the claim is true" line.
- **Counts:** totals by status over `comparison.original.required_set[].status`.
- **Check table**, one row per `comparison.original.required_set[]`: `assertion_id`, `status`, `reason`, `evidence_valid`. FAIL rows come first, then ERROR, NOT_ASSESSED and PASS. Expanding a row shows `<run>/original/outcome.json:assertions[assertion_id=…]`:
  - `observed`, for example `split.no_group_overlap` → `observed.overlapping_groups`;
  - `limitations`;
  - `evidence[]` (`artifact`, `sha256`).
- **Incomplete coverage:** `comparison.original.incomplete_coverage` and `outcome.json:incomplete_coverage`, shown prominently whenever they are non-empty (SPEC §6).
- **Independent metric (descriptive, never part of the outcome):** `outcome.json:descriptive[result_id=metric.recomputed_primary].observed`:
  - `primary_metric`;
  - `aggregates.development_eval.<primary_metric>.pooled.value` and `.mean_over_folds.value`, with `observations` / `folds` and `complete`;
  - `per_fold[]`.

  It is labelled with the result's `limitations` ("Descriptive only; never part of the outcome."). Baselines come from `descriptive[result_id=metric.baselines]`, and class support from `descriptive[result_id=split.class_support]`.
- **Reported metric:** only if the project declares one. Then `outcome.json:assertions[assertion_id=metric.reported_matches_recomputed].observed` gives, for each `entries[]`:
  - `entry.value` (reported) against `recomputed.value` (independent);
  - `abs_difference`, `tolerance` and the entry's status.

  Otherwise: "This project declares no reported metric." (The s01 fixture declares none.)
- **Limitations:** `comparison.original.limitations`.

### 4.5 Revision and approval in the browser

**Approval panel (blocking).** Shown whenever the engine calls the approver, for the original (kind `original`) and for each candidate (kind `candidate`). Its content is exactly the `ApprovalRequest` the engine passes (`controller.py: ApprovalRequest`):

| Shown | Field |
| --- | --- |
| "Run the ORIGINAL, unmodified project code in the isolated Docker runner" or "Run this CANDIDATE revision in the isolated Docker runner" | `request.kind` |
| Entry point | `request.entry_point` |
| Snapshot hash (full, monospaced) | `request.base_snapshot_hash` |
| Code hash (full, monospaced) | `request.candidate_hash` |
| Rationale, labelled **model-written (untrusted)** | `request.model_rationale` (candidates only) |
| Unified diff, labelled untrusted; control characters shown as escapes | `request.diff`, rendered through `atlas.agent.approval.inert()` (candidates only) |
| Input: "Type the first 12 characters of the code hash to approve; anything else declines" | `approval.CONFIRM_CHARS` (12) |

**Rule (identical to the CLI, `approval.TerminalApprover`):**
- The typed text, with whitespace stripped and lowercased, must equal `candidate_hash[:12]`.
- There is one attempt per request, and a mismatch declines ("Confirmation did not match: NOT approved.").
- Approval returns `candidates.Approval(candidate_hash, base_snapshot_hash, approved_at)` with the **full** hash.
- Closing the panel, leaving the page or a session timeout raises `ApprovalUnavailable`; the engine turns that into NEEDS_INPUT and executes nothing.

**Mapping to the existing interface (unchanged).** The engine's interface is `controller.Approver.decide(request: ApprovalRequest) -> Approval | None`, with `ApprovalUnavailable` for "nobody can be asked". The browser build adds a UI-side `BrowserApprover` implementing exactly that method:
- the run's worker thread calls `decide()`, which blocks until the panel's single submission, the panel closing, or a session timeout;
- it sets `last_reason` to the same values the CLI logs (`confirmed`, `confirmation_mismatch`, `input_closed`; a missing browser session maps to the existing "no terminal" meaning).

The engine already rechecks the binding (`controller.py` `_decide`: the hash and snapshot must match) and excludes the wait from active time (`Budget.paused()`, reported as `budget.approval_wait_s`). No engine change is needed.

**Revision detail (after execution).**
- Candidate hash: `comparison.candidates[].candidate_hash`.
- Diff hash: `comparison.candidates[].diff_sha256`.
- Approval record: `comparison.candidates[].approval` (`candidate_hash`, `base_snapshot_hash`, `approved_at`).
- The diff itself (GAP-4 closed by slice 4c): the persisted `<run>/proposals/r<N>.diff` named by `agent_report.json:proposals[revision=N].diff_path`, shown under "model-written (untrusted)" (`proposals[].files_label`). Its SHA-256 is recomputed from the file and shown against `proposals[].diff_sha256` (and, for an executed candidate, `comparison.candidates[].diff_sha256`). When the model sent the complete file, `source_kind` is `new_source`, and the diff is the one ATLAS generated; the file is `proposals[].new_source_path` (`r<N>.new_source.py`). The UI does not rebuild a diff.

**Every proposal, including rejected ones.** One row per `agent_report.json:proposals[]` (mirrored by `agent_log.jsonl:event=tool,tool=propose_patch.outcome` / `.code`), so a run with zero executed candidates explains itself:
- `revision`, `source_kind`, and `outcome` (`rejected`, `declined`, `unavailable` or `executed`);
- `code`: the validator's rejection code (for example `malformed_diff`, `no_change`, `syntax_error`), the approver's reason, or `needs_input` / `approver_error`;
- `detail` (at most 200 characters) under its own label `proposals[].detail_label`, "validator message; may quote model text";
- the persisted diff (and `new_source` file, when used) under "model-written (untrusted)", with its SHA-256; a diff over the size limit has a hash but no file;
- the run-level line from `limitations[]`: "N proposals: R rejected by validation, D declined, E executed".

### 4.6 Revision comparison (side by side)

The basis line comes first: `comparison.comparison_basis` (for example "Original and candidates all executed in the isolated Docker runner.").

| Row | Original | Candidate N |
| --- | --- | --- |
| Outcome (+ label) | `scientific_outcomes.original` | `scientific_outcomes.candidates[N]` / `comparison.candidates[N].scientific_outcome` |
| Execution | `comparison.original.runner`, `.execution_status`, `.executed` | `comparison.candidates[N].execution.status`, `.runner`, `.container_removed`, `.elapsed_s`; `.evaluated` |
| Failed assertions | `required_set[status=FAIL]` | `comparison.candidates[N].required_set[status=FAIL]` |
| Per-assertion change | `comparison.candidates[N].status_by_assertion[]` (`assertion_id`, `original`, `candidate`), with changed rows highlighted and their direction stated in text ("FAIL → PASS") | |
| Independent primary metric | `<run>/original/outcome.json:descriptive[result_id=metric.recomputed_primary]…pooled.value` | the same key in `<run>/candidates/cN/outcome.json` |
| Reported vs independent | as in §4.4, when declared | as in §4.4, when declared |
| Incomplete coverage | `comparison.original.incomplete_coverage` | `comparison.candidates[N].incomplete_coverage` |
| Limitations | `comparison.original.limitations` | `comparison.candidates[N].limitations` |
| Evidence hashes | `comparison.original.evidence_sha256` | `comparison.candidates[N].evidence_sha256` |

- **Metric unit and context:** the metric's name (`primary_metric`) and the evaluated rows (`observations`) are shown next to both values. A lower candidate value is shown as plainly as a higher one ("a lower score can be the honest result").
- **No verdict word:** no "fixed" or "improved". The reading guide, `comparison.reading_guide[]`, is shown under the table.

### 4.7 Export

- **Downloads:**
  - `<run>/agent_report.json` and `<run>/agent_log.jsonl`;
  - `<run>/original/outcome.json` and `report.json`;
  - each `<run>/candidates/cN/outcome.json`;
  - `<run>/preflight.json` when present.

  Each is shown with its SHA-256: `agent_report.json:agent_log.sha256`, and `evidence_sha256` for the evaluated runs.
- **GAP-6:** the engine writes JSON only. A human-readable report (HTML or Markdown) would be a UI rendering of the same fields, labelled "rendered from agent_report.json <sha256>", and adds no new data.

---

## 5. Component states

| Step | Empty | Running | Failure | Unsupported | Completed |
| --- | --- | --- | --- | --- | --- |
| Select | "Choose a project" | n/a | Project unreadable: the intake error, no run button | n/a | The claim card is filled |
| Claim | No project | n/a | n/a | `NOT_SUPPORTED`, its label, `terminal_reason`, and a next action (GAP-10) | The claim shown for confirmation |
| Analyze | "Not run yet" | The trace (§4.3); buttons disabled; "Run in progress (started <time>)" | `terminal_state` ERROR, BUDGET_EXHAUSTED or NEEDS_INPUT with `terminal_reason`, verbatim. For example: `original_not_executed: … no host fallback` (Docker unavailable); `model_timeout (after one retry)`; `schema_failure: …`; `invalid_usage`; `spend_cap: …`; `execution of the original was not authorized`. The original's findings stay visible if they exist, and "Start a new run" is offered | `NOT_SUPPORTED` as above | `terminal_state` REPORT |
| Finding | "No findings yet" | "Original under evaluation" while `state=CHECK` | Original not executed: `comparison.original.executed == false`, `comparison_basis` "The original was not executed …", and every assertion NOT_ASSESSED (`not_executed`) | n/a | The headline, table and metrics (§4.4) |
| Revision | "No candidate proposed" (also the honest end state when the model finished without one) | The approval panel, or "Executing in Docker" while `state=EXECUTE` | Candidate refused or not executed: `execution.status` refused or not_executed; prose from `limitations` ("0 of 1 candidates executed …"). Proposals rejected by validation, declined or unavailable: each `proposals[]` row with its `outcome`, `code` and labelled `detail` (§4.5) | n/a | §4.5 detail |
| Comparison | Hidden until a candidate was evaluated | n/a | A candidate failed in execution: its execution status next to its outcome | n/a | §4.6 |
| Export | Disabled until a report exists | Disabled | Partial report: `agent_report.json` with `finalization_failures`, or the minimal ERROR report, shown as such | n/a | Downloads and hashes |

---

## 6. Interaction policies

- **One run per session at a time.** The run action is disabled while a run is active, so a double-click cannot start a second run. A browser refresh reattaches to the active run, or shows the last finished run.
- **Stale results.** A result is labelled "Results from run <directory name>, finished <time>" (`agent_report.json:states[-1].time_utc`). When the selected project changes, earlier results are labelled "from a different project" until a new run finishes.
- **Costly actions.** A live run, once authorized, needs its own confirmation step with the amount (CLI `--authorize-spend-usd`) and can never be triggered by a refresh.

---

## 7. Visual system

- **Framework:** Streamlit with native theme configuration (`.streamlit/config.toml`). Targeted CSS only where it is documented and tested (playbook §25).
- **Typography:**
  - UI text: a neutral sans (Inter or IBM Plex Sans) at 15 px base; headings 22 / 18 / 16 px; line height 1.45;
  - hashes, diffs, assertion IDs and JSON: a monospace (JetBrains Mono or IBM Plex Mono) at 13 px;
  - long hashes are never truncated in the approval panel.
- **Colour:** a restrained neutral palette (background `#FAFAF9`, surface `#FFFFFF`, text `#1C1917`, muted `#57534E`, border `#E7E5E4`) and one accent for primary actions (`#1D4ED8`). Status colours carry meaning only and are always paired with text:

  | Meaning | Colour |
  | --- | --- |
  | VIOLATION_FOUND / FAIL | `#B91C1C` |
  | NO_VIOLATION_FOUND / PASS | `#15803D` |
  | INCONCLUSIVE / NOT_ASSESSED | `#B45309` |
  | ERROR | `#7E22CE` |
  | NOT_SUPPORTED | `#44403C` |

  Model-written text uses a tinted panel (`#F5F5F4`) with a "model-written" tag. The NON-LIVE banner is neutral grey; a LIVE banner (once authorized) is the accent colour, never a status colour.
- **Spacing:** an 8 px base grid; cards padded 16 / 24 px; 24 px between cards; tables at 36 px row height.
- **Viewports:**
  - 1440 × 900 (primary);
  - 1280 × 800 (narrow desktop);
  - 390 × 844 (phone: usable access, with the rail collapsed into a menu).

  Wide diffs and tables scroll within their own region, while navigation and the primary action stay reachable.
- **Accessibility checks:** keyboard focus order, contrast of at least 4.5:1 for text, and wrapping. Screenshots alone do not establish accessibility.

---

## 8. Hosted-mode labels (when GAP-5 is built)

- Every generated diff is shown under the heading "Proposed revision (**not executed here**)".
- Any corrected-protocol result reads "computed by ATLAS's trusted evaluation functions", next to a sentence that it does not validate the displayed diff.
- Replay of a recorded run, if used, is labelled "recorded on <date>, not live" (SPEC §13).

The acceptance test checks that "not executed here" is present whenever the app runs in hosted mode.

---

## 9. Playwright scenarios the build must pass (playbook §20)

Playwright Python against the running app, with deterministic offline fixture replies; a fixture run is never presented as live proof. Each scenario asserts visible content **and** agreement with the engine artifacts it displays.

1. **Faulty project, full path.**
   - Steps: select `s01_faulty`, confirm the claim, run, approve the original and the candidate by typing the shown prefixes, inspect the evidence, open the diff and export.
   - Assert:
     - the headline equals `agent_report.json:scientific_outcomes.original` (`VIOLATION_FOUND`);
     - the FAIL rows equal `required_set[status=FAIL]`;
     - the comparison rows equal `status_by_assertion[]`;
     - the banner says NON-LIVE;
     - the exported report's SHA-256 equals the file on disk.
2. **Clean control** (`s02_clean`): `NO_VIOLATION_FOUND`, with no FAIL rows and the limitations visible. No fabricated leakage finding.
3. **Unsupported or missing metadata** (`s06_missing_metadata` and `s08a_combined_claim`): `NOT_ASSESSED` or `INCONCLUSIVE` with reason codes, or `NOT_SUPPORTED` with its label and a next action (GAP-10). Never a green pass.
4. **Provider timeout or invalid response** (a fixture script with `{"error": "timeout"}` twice, then a reply that is not JSON):
   - the run ends ERROR with `model_timeout (after one retry)`, or with `schema_failure: …`;
   - the attempts shown equal `budget.used.attempts`;
   - there is no hidden retry beyond the one recorded;
   - "Start a new run" works.
5. **Procedure retrieval for the temporal mismatch case:** **dropped** (T-08 cut by lead decision, 2026-10-17). It is not pending, and no test is built for it.
6. **Refresh, rerun or double-click:**
   - double-clicking "Confirm & run" starts exactly one run (one new `runs/agent-*` directory);
   - a refresh during a run reattaches without starting another;
   - results after a project change are labelled stale.

Plus the label checks:
- the approval panel shows the full hash and accepts only the 12-character prefix;
- a wrong prefix declines;
- model-written text carries its label;
- costs read "Estimated cost (not a bill)";
- in hosted mode, "not executed here" is present (with GAP-5).

---

## 10. What the engine already guarantees that the UI relies on

- **Outcomes:** they come only from the trusted evaluator (`scientific_outcomes.source` = "trusted evaluator only").
- **Labels:** the NON-LIVE / LIVE labelling (`banner`, `mode`, `live`) and the run-level prose (`limitations`, `comparison_basis`) follow the observed execution (T-06 slice 3).
- **Approval:** it is hash-bound and rechecked by the engine. Without an approver, the run ends NEEDS_INPUT with nothing executed.
- **Spending, live runs only:** limits are refused or enforced before sending (`spending`, `cost`, `model_request_refused`).

---

## 11. GAPs (the engine does not produce these yet; nothing here is invented)

| ID | Gap | Effect on the UI | Owner / when |
| --- | --- | --- | --- |
| GAP-1 | Model pre-fill and user editing of the structured claim (PRD workflow step 2). The engine reads only `atlas_manifest.json:claim` | The claim is shown read-only for confirmation | Later engine task (claim translation stage) |
| GAP-2 | A project catalogue (curated list, expected purpose) | A fixed list of development fixtures in the UI | UI build (T-07) |
| GAP-3 | **Closed by T-06 slice 4c.** Each `model_attempt` log event carries `cost` (the attempt's ledger entry on live runs; "not applicable (fixture)" otherwise) | The trace shows the per-attempt estimate (§4.3) | Done (slice 4c) |
| GAP-4 | **Closed by T-06 slice 4c.** `agent_report.json:proposals[]` (outcome, code, bounded detail) and the persisted `<run>/proposals/r<N>.diff` (and `.new_source.py`) | The persisted diff is shown, rejected proposals included (§4.5); no rebuild | Done (slice 4c) |
| GAP-5 | Limited hosted mode (trusted corrected-protocol functions; "not executed here" path) | Hosted labels specified (§8) but not exercisable | T-12 |
| GAP-6 | A human-readable export (HTML or Markdown) | JSON downloads with hashes; a UI-rendered report from the same fields | UI build (T-07), with no new data |
| GAP-7 | Procedures (admission, retrieval, refusal) | Playwright scenario 5 is dropped | None: T-08 cut by lead decision, 2026-10-17 |
| GAP-8 | A browser approver | A UI-side `BrowserApprover` implementing the unchanged `Approver.decide` | UI build (T-07) |
| GAP-9 | Live runs from the UI. One authorized live run was completed on 2026-10-17 (`runs/live1`); no further live run is authorized | The T-07 UI keeps the live mode disabled, labelled "Live runs need the lead's explicit go-ahead" | Each live run: the lead's explicit go-ahead. Live access in a hosted UI: T-12 |
| GAP-10 | A structured "next action" for `NOT_SUPPORTED` and `NOT_ASSESSED` reasons | UI copy keyed to the existing reason codes (`outcome.json:assertions[].reason`, `terminal_reason`) | UI build (T-07) |
| GAP-11 | A streaming or asynchronous run API (`run_agent` is synchronous) | The run in a worker thread; progress by following `agent_log.jsonl` | UI build (T-07) |
| GAP-12 | Duplicate-run and stale-result protection | UI policy (§6) | UI build (T-07) |

---

## 12. Build decisions (T-07 build, 2026-10-17)

Choices the spec left open, made during the unattended build. Each stays within the truth rules (§1); none changes the engine.

| # | Decision | Why |
| --- | --- | --- |
| B1 | **Typefaces:** Streamlit's bundled faces (`font = "sans-serif"`, Source Sans; `codeFont = "monospace"`, Source Code Pro) at the §7 sizes (15 px base, 22 / 18 / 16 px headings, 13 px mono). | Inter or IBM Plex needs a runtime Google Fonts fetch or vendored font files. The build allows network only for dependency setup, and the bundled faces are served locally. |
| B2 | **The engine runs in a worker process** (`python -m atlas.ui.runproc`), not a thread (GAP-11). | `run_agent`'s fixture network guard is process-wide (its banner says so). In-process, it blocked the Streamlit server's own sockets: a new browser session failed with `NetworkDenied` from asyncio's `socketpair()`. |
| B3 | **BrowserApprover over a file channel** (`<runs>/.ui-channels/<id>/`): `pending.json` holds the request exactly as the engine passed it; `answer-<n>.json` is created exclusively, so only one submission counts; the `heartbeat` file's modification time shows a page is open. `decide()` runs in the worker and applies the CLI rule (strip, lowercase, compare with `candidate_hash[:12]`). | The worker process needs a channel to the page, and the rule stays inside the unchanged `Approver.decide` contract (GAP-8). |
| B4 | **Approval timeouts** (the page touches the heartbeat every second while it shows a run): no heartbeat for 30 s when asked → `ApprovalUnavailable`, `last_reason` `no_terminal`; panel closed ("Close without deciding"), page unseen for 120 s, or 900 s in all → `input_closed`. Each ends the run NEEDS_INPUT, with nothing executed. | §4.5: closing, leaving or a timeout raise `ApprovalUnavailable`; the reasons are the CLI's. |
| B5 | **One run at a time per app server**, held in a process-wide registry, not per browser session (GAP-12). A refresh reattaches to the active run, or shows the last finished one. A double-click or a second tab cannot start a second run. A server restart forgets the registry; finished runs remain on disk. | §6: "one run per session at a time" must survive a refresh, and a refresh is a new Streamlit session. |
| B6 | **The user's choices live in plain session keys.** Mode and fixture script are stored outside widget keys; widgets are seeded from them and write back on change. | Streamlit drops a widget's state on any rerun that does not render it. The blocking approval panel stops the page early, and the choices were silently reset. |
| B7 | **"Start a new run"** reruns the finished run's own project, mode and script. **"Confirm & run"** uses the current selection. | Recovery should repeat what failed (scenario 4) and not depend on later widget changes. |
| B8 | **Fixture scripts** are in `src/atlas/ui/scripts.py`, never under `benchmarks/`. `revision` is the Docker integration test's script, built the same way (`tests/unit/test_ui_core.py` checks they are identical). The curated ones: `inspect_only`, `rejected` (a miscounted diff), `timeout` (two timeouts, then a non-JSON reply that is never read) and `invalid` (a non-JSON reply). | §3: the integration test's script, plus curated failure and honest-empty cases. |
| B9 | **Runs directory:** `runs/ui/` (git-ignored), overridable with `ATLAS_UI_RUNS_DIR` (the acceptance tests use their basetemp). | It keeps UI runs apart from CLI runs, and tests isolated. |
| B10 | **Tables use `st.table`** (an HTML table), not `st.dataframe`. | `st.dataframe` draws on a canvas: Playwright cannot read its cells to compare them with the artifacts, and assistive technology cannot either. |
| B11 | **Targeted CSS** (`views.CSS`) uses only `st-key-*` classes, which `st.container(key=...)` documents. It sets: card surface `#FFFFFF`; the model-written tint `#F5F5F4`; the approval panel outline (`#1D4ED8`); scroll regions; hash wrapping in trace and export tables. Tested in `test_the_documented_css_hooks_apply`. | §7 asks for targeted, documented, tested CSS. Everything else is native theming (`.streamlit/config.toml`). |
| B12 | **Layout:** the numbered sections 1–6 follow the workflow (a real sequence). A pending approval replaces the page below the banner, so it cannot be missed. In a finished run, the trace's tables sit in an expander, open by default only for ERROR, BUDGET_EXHAUSTED or NEEDS_INPUT; stages, budget and declined approvals stay visible. | The 30-second read (§2) puts the finding near the top; a blocking panel must block. |
| B13 | **Outcome headline:** the code itself in large status-coloured text, then the PRD label and the fixed caveat. Colour never stands alone. | The one emphasised element (frontend-design "spend your boldness in one place"); §1.1. |
| B14 | **Next actions (GAP-10):** copy keyed to every `Reason` code (unit-tested to cover all of them) and to the intake reasons for NOT_SUPPORTED, with a fallback line. | §5 unsupported and missing-metadata states. |
| B15 | **Export:** one download per §4.7 file. Each hash is recomputed from disk and compared with the engine's recorded hash where one exists: `agent_log.sha256`, and `evidence_sha256` for `outcome.json` / `report.json`. `agent_report.json` has no recorded self-hash, so it reads "not recorded". GAP-6: a Markdown rendering of the same report fields, labelled "rendered from agent_report.json <sha256>". | §4.7, without new data. |
| B16 | **Changed comparison rows** are highlighted (`#EFF6FF`, bold) with pandas `Styler` in `st.table`, and the direction is written out ("FAIL → PASS"). | §4.6: highlight plus text. |
| B17 | **Server:** bound to `localhost`, with usage statistics off (`.streamlit/config.toml`). | The UI makes no outbound calls. Without the binding, Streamlit looks up the machine's external IP at startup to print an "External URL". |
| B18 | **Live mode** is a disabled "Agent, live" button with its reason in the help text and in the rail: "Live runs need the lead's explicit go-ahead". | §3, GAP-9. |
| B19 | **Deterministic audit mode** calls `atlas.audit.audit` (the CLI's `--mode audit`); the banner reads "Deterministic audit: no model". There is no agent trace; the Analysis card states the runner and its capability (`trusted_pipeline_only`). | §3. |
| B20 | **Phone (390 × 844):** the rail collapses into Streamlit's menu, and the mode control wraps. A test asserts no page-level horizontal scroll; wide diffs and tables scroll inside their own regions. | §7 viewports. |
| B21 | **Not built:** hosted-mode labels (GAP-5, T-12); scenario 5 (dropped). A Docker-unavailable run shows the engine's `terminal_reason` verbatim through the generic failure state; it is not exercised by a browser test, which needs Docker. | Scope. |
| B22 | **Status text colours are set exactly** (`redTextColor` … `grayTextColor` = the §7 values). | Streamlit otherwise derives darker text shades from the palette: NOT_SUPPORTED rendered near-black (`rgb(27, 26, 24)`), and INCONCLUSIVE rendered `rgb(107, 49, 6)`. Found by the acceptance colour checks. |
| B23 | **A worker outlives a stopped server only until its approval wait ends:** with no page heartbeat, it records NEEDS_INPUT after 120 s and exits. The acceptance fixture stops the whole process tree. | Found when an orphaned worker held its log open. No run executes after the server is gone, because a candidate needs an approval. |
| B24 | **Once the selected project has results, the claim fields fold into an expander** ("Claim fields (read-only, from atlas_manifest.json)"). The statement, mode and run controls stay visible. | At 1440 × 900 the full claim card pushed the analysis and the finding below the fold (seen in the screenshots). |
