# ATLAS UI: manual walkthrough (T-07; HUD look, UI design pass phase 2)

A five-minute check of the local browser build. Every run here is **NON-LIVE**: model replies come from fixture scripts, and no model or provider is called. The spec is `docs/UI_SPEC.md` (its §1 truth rules are unchanged; the build decisions are in its §12); the look is `docs/UI_DESIGN_HUD.md` (phase 1 for the recorded-run viewer, §11 for every other view).

## Start

Docker Desktop must be running (agent runs execute the original and every candidate in the isolated runner, with no host fallback).

```powershell
$env:ATLAS_MODEL_MODE = 'fixture'
uv run --locked streamlit run app.py
```

Open http://localhost:8501. The server binds to localhost only, and usage statistics are off. Runs are written under `runs/ui/` (set `ATLAS_UI_RUNS_DIR` to use another folder). The page is dark only, in IBM Plex (vendored; nothing is fetched).

## The main path (s01_faulty)

1. **Select.** The rail lists the development fixtures ("synthetic, not benchmark evidence"). `s01_faulty` is selected. The Capability block should read `Docker: isolated_available`; Live is disabled ("Live runs need the lead's explicit go-ahead"). If Docker is not reachable, the claim card shows an amber "Docker: …" state with its reason and "Next action: start Docker, then reload this page."; agent runs never fall back to the host.
2. **Confirm the claim.** Card 1 shows the manifest's claim, read-only. Keep the mode "Agent, fixture replies (NON-LIVE)" and the script "Propose a grouped, fold-local revision". Click **Confirm & run**.
3. **Approve the original.** The approval panel is the page's active frame (cyan corner brackets). It says "Run the ORIGINAL, unmodified project code in the isolated Docker runner." and shows the full snapshot hash and code hash (all 64 characters, wrapping, never shortened). The decision sits in its own inset: type the first 12 characters of the code hash, then **Submit confirmation**. "Close without deciding" sits below a rule (the run ends NEEDS_INPUT, nothing executed). With the keyboard: Tab reaches the confirmation field, then Submit confirmation, then Close without deciding.
4. **Watch the analysis.** Card 2's mission track lists the stages `agent_log.jsonl` has recorded so far; each new one lights once, and the latest is outlined as current. Counters read "<n> so far".
5. **Approve the candidate.** The second panel adds the model's rationale and the proposed diff, each in the dashed model-written frame with the amber "MODEL-WRITTEN · UNTRUSTED" badge first. Type that code hash's first 12 characters.
6. **Read the briefing.** The finished run is verified first (every recorded hash recomputed). The **Briefing** leads: "Evidence intact: <n> of <n> recorded hashes verified now.", "Original outcome: VIOLATION_FOUND. Required checks: 4 FAIL, 0 NOT_ASSESSED, 0 ERROR (of 9).", the four failing checks in the policy's own words (`split.no_group_overlap (FAIL): No group_id value is in both partitions of a fold.` …), "Revision candidates/c1, executed and verified: NO_VIOLATION_FOUND; 4 FAIL → PASS.", the descriptive metric line, and "This does not say the scientific claim is true or false." It contains nothing the model wrote.
7. **Read the HUD.** The integrity ring (all segments lit), the two outcome reticles (before → verified revision), then the leak maps and fit-scope flows side by side, and the check matrix. Click (or Tab to and press Enter on) a FAIL tile: its inspection frame opens in place with the recorded status, reason, evidence_valid, limitations, each evidence file's full SHA-256 and the observed values (lists show their full count, then "and <k> more"). Space or Enter closes it.
8. **Read the cards.** Card 3 (finding: headline, FAIL rows first, "Check details" with the same field rows), card 4 (the persisted `proposals/r1.diff` in the model-written frame, its SHA-256 recomputed and matched), card 5 (comparison; the candidate's lower metric, 0.6687 against 0.6812, shown as plainly; four "FAIL → PASS" rows highlighted), card 6 (cost "not a bill", limitations, the export table with recomputed hashes and the downloads).

## States worth trying

Every failure or empty state shows its code in its status colour, the reason, and a "Next action"; none uses success styling.

| Try | Expect |
| --- | --- |
| `s02_clean`, "Inspect only, no revision" | `NO_VIOLATION_FOUND`, no FAIL row, "No candidate proposed"; the briefing lists no failing check |
| `s06_missing_metadata`, deterministic audit | `INCONCLUSIVE` (amber), three NOT_ASSESSED rows `missing_metadata`, next actions, an amber `incomplete_coverage` state; the audit run gets its own briefing |
| `s08a_combined_claim` | `NOT_SUPPORTED` (stone), the intake reason and "Next action: Split the claim into one supported type…"; nothing executes |
| `s01_faulty`, "Provider timeout" | A violet `ERROR` state "Terminal state. Reason: `model_timeout (after one retry)`" with its next action; 2 of 6 attempts on the track; the original's finding stays; **Start a new run** repeats it |
| **Close without deciding** at an approval | An amber `NEEDS_INPUT` state; nothing executed |
| `s01_faulty`, "Propose a malformed revision" | The proposal is rejected `malformed_diff`; the validator message under its own label; the persisted diff in the model-written frame |
| Open a recorded run, `live6/…` | The briefing, the hero and an amber `BUDGET_EXHAUSTED` terminal state (the recorded run hit its revision limit) |
| A recorded run with one changed byte | The broken ring and a red `EVIDENCE CHANGED` state with the differing items; no briefing, no outcome, no diagram |
| Open a recorded run with none recorded | A `NO RECORDED RUNS` state naming the folder and what to do |
| A phone-width window | The rail collapses; the before/after pairs switch with the Original / Verified revision toggle; the inspection frame stacks its field names above the values; no sideways page scroll |

## Hosted mode (ATLAS_HOSTED=1)

The sidebar picks Recorded runs (the default) or Live session. The live view shows the recorded original's ring and reticle (original only), then either the start form or, with live calls off, a `LIVE UNAVAILABLE` state. While a session runs, its mission track and budget gauge follow the session's own log (requests and estimated cost so far, against the decided 6 requests and $0.0648 estimate cap, "estimate, not billing"). The finished session shows the Route line, its briefing (with "Proposals were checked by ATLAS validation and not executed here."), its HUD, and each proposal "not executed here" in the model-written frame. A spent daily budget is an amber `BUDGET_EXHAUSTED` state.

## Automated checks

```powershell
$env:ATLAS_REQUIRE_DOCKER = '1'
uv run --locked pytest tests -q -p no:cacheprovider -rs --basetemp=runs/ui-hud/t2
```

Set `ATLAS_UI_SCREENS` to a folder to save settled screenshots of each state (scenarios 10 and 11 and the hosted HUD test save every phase 2 state at 1440 × 900, 1280 × 800 and 390 × 844, the keyboard tab orders, and two motion captures).
