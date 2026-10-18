# ATLAS UI: manual walkthrough (T-07)

A five-minute check of the local browser build. Every run here is **NON-LIVE**: model replies come from fixture scripts, and no model or provider is called. The spec is `docs/UI_SPEC.md`; the build decisions are in its §12.

## Start

Docker Desktop must be running (agent runs execute the original and every candidate in the isolated runner, with no host fallback).

```powershell
$env:ATLAS_MODEL_MODE = 'fixture'
uv run --locked streamlit run app.py
```

Open http://localhost:8501. The server binds to localhost only, and usage statistics are off. Runs are written under `runs/ui/` (set `ATLAS_UI_RUNS_DIR` to use another folder).

## The main path (s01_faulty)

1. **Select.** The rail lists five development fixtures ("synthetic, not benchmark evidence"). `s01_faulty` is selected. The Capability block should read `Docker: isolated_available`; Live is disabled ("Live runs need the lead's explicit go-ahead").
2. **Confirm the claim.** Card 1 shows the manifest's claim, read-only: "The activity classifier works on people absent from training.", `unseen_group`, sampling unit `subject`, the dependence entries and the column roles. Keep the mode "Agent, fixture replies (NON-LIVE)" and the script "Propose a grouped, fold-local revision". Click **Confirm & run**.
3. **Approve the original.** A blocking panel says "Run the ORIGINAL, unmodified project code in the isolated Docker runner." and shows the full snapshot hash and code hash. Type the first 12 characters of the code hash, then click **Submit confirmation**. (Anything else declines. "Close without deciding" ends the run NEEDS_INPUT, with nothing executed.)
4. **Watch the analysis.** Card 2 follows `agent_log.jsonl`: stages, model attempts *N of 6*, tool calls and approvals. Fixture attempts read "No provider cost (fixture replies)".
5. **Approve the candidate.** The second panel shows the model's rationale and the proposed diff, both labelled untrusted. Type that code hash's first 12 characters.
6. **Read the finding.** Card 3 shows `VIOLATION_FOUND`, "The evaluation breaks at least one requirement of this claim." and "This does not say the scientific claim is true or false." The FAIL rows come first: `split.no_group_overlap`, `split.sampling_unit_disjoint`, `split.repeated_measures_rule`, `fit.state_dependencies_within_fold_train`. Open "Check details" for the observed values and evidence hashes. The independent primary metric (`balanced_accuracy`, pooled over 160 rows) is labelled descriptive only.
7. **Read the revision.** Card 4 shows the persisted `proposals/r1.diff` under "model-written (untrusted)", with its SHA-256 recomputed and matched, and the line "1 proposal: 0 rejected by validation, 0 declined, 1 executed".
8. **Compare.** Card 5 prints the basis ("Original and candidates all executed in the isolated Docker runner."), then original against candidate: outcome, execution, failed assertions, the independent metric (the candidate's is lower, 0.6687 against 0.6812, and is shown as plainly), and the per-assertion change (four rows "FAIL → PASS", highlighted). There is no "fixed" or "improved" anywhere.
9. **Export.** Card 6 shows "Estimated cost (not a bill)" (fixture: "fixture replies: no provider request") and the limitations. The download table lists each file's recomputed SHA-256 and whether it matches the hash the engine recorded. "Download readable report (Markdown)" is labelled with the report's own SHA-256.

## States worth trying

| Try | Expect |
| --- | --- |
| `s02_clean`, "Inspect only, no revision" | `NO_VIOLATION_FOUND`, no FAIL row, "No candidate proposed", limitations visible |
| `s06_missing_metadata` (either mode) | `INCONCLUSIVE`, three NOT_ASSESSED rows `missing_metadata`, a next action, incomplete coverage listed |
| `s08a_combined_claim` | `NOT_SUPPORTED`, its label, the intake reason and "Split the claim into one supported type…"; nothing executes |
| `s01_faulty`, "Provider timeout" | ERROR `model_timeout (after one retry)`, 2 of 6 attempts, one retry; the original's finding stays; **Start a new run** repeats it |
| `s01_faulty`, "Invalid reply" | ERROR `schema_failure: not_json` after three attempts: the first two invalid replies are corrected (slice 4g), the third in a row ends the run; nothing is repaired |
| `s01_faulty`, "Propose a malformed revision" | The proposal is rejected `malformed_diff`; the validator message is shown under its own label, and the persisted diff is shown with its hash; no comparison card |
| A wrong prefix at the candidate panel | "Confirmation did not match: NOT approved."; the proposal is `declined` (`confirmation_mismatch`); nothing executes |
| Refresh during an approval | The same request reappears; no second run starts |
| Double-click **Confirm & run** | Exactly one new `runs/ui/agent-*` folder |
| Pick another project after a run | "Results below are from a different project (…)" |
| A phone-width window | The rail collapses into the menu; the cards stack; wide tables scroll inside their own region |

## Automated checks

```powershell
$env:ATLAS_REQUIRE_DOCKER = '1'
uv run --locked pytest tests/acceptance -q -p no:cacheprovider --basetemp=runs/t07/t -rs
```

Set `ATLAS_UI_SCREENS` to a folder to save a screenshot of each major state (1440 × 900 and 390 × 844).
