"""Fixed product copy for the story layout (UI restructure, slice 1), in one reviewed place.

Every user-visible sentence the story pages add lives here; the assertion copy (each canonical
assertion's failure label and description) lives in `assertion_labels.json` beside this file.
Nothing here is generated at runtime or by a model. Templates take only values read from a
run's verified files (`atlas.ui.story` and `atlas.ui.hud` fill them); a template whose field is
not recorded is not shown, so no sentence ever says "null" or "not recorded" in its place.

Rules for this file (docs/UI_DESIGN_HUD.md §12.3): no claim stronger than its source (hashes
detect changes since recording, they do not prove there was no cheating); NO_VIOLATION_FOUND
keeps its caveat (`atlas.ui.artifacts.CAVEAT`); descriptive metrics never get causal words.
"""

from dataclasses import dataclass

# -- header ------------------------------------------------------------------------------------
APP_NAME = "ATLAS"
TAGLINE = (
    "ATLAS checks a machine-learning evaluation for leaks between training and test data, "
    "shows its evidence, and tests a proposed fix in an isolated container."
)
WHY_LABEL = "Why it matters"
WHY_TEXT = (
    "Data leakage has been found in 294 published papers across 17 scientific fields "
    "(Kapoor & Narayanan, Patterns, 2023)."
)
WHY_URL = (
    "https://collaborate.princeton.edu/en/publications/"
    "leakage-and-the-reproducibility-crisis-in-machine-learning-based-/"
)
WHY_LINK = "Source"

# -- navigation ----------------------------------------------------------------------------------
PAGE_OVERVIEW = "Overview & Cases"
PAGE_LIVE = "Try It Live"
PAGE_AGENT = "ATLAS Checks vs. Model Alone"
PAGE_LIMITS = "How It Works & Limits"
RUN_WAITING = "A run is waiting for your approval."
RUN_WAITING_LINK = "Open Try It Live"


# -- cases ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Case:
    key: str  # ASCII letters and digits (used in widget keys and CSS hooks)
    title: str
    run: str  # the run's path inside the recorded bundle (demo/recorded)
    description: str  # what the case is; never its outcome (that comes from its files)


CASES = (
    Case(
        "live6",
        "A leak caught and fixed",
        "live6/agent-s01_faulty-877f8245a8a2",
        "A small synthetic project with a planted leak, recorded in a live run with the AI "
        "agent.",
    ),
    Case(
        "harflawed",
        "A real-data leak",
        "t09/agent-har_flawed-1e2267f662c0",
        "Real smartphone sensor data (UCI HAR) with a deliberately flawed evaluation written "
        "by ATLAS's authors.",
    ),
    Case(
        "harclean",
        "A clean evaluation",
        "t09/agent-har_clean-ac63eaecd7a8",
        "The same real sensor data with a clean evaluation written by ATLAS's authors: each "
        "person on one side of the split, and every step fit inside each fold.",
    ),
)
CASES_LABEL = "Cases"
CARD_CHANGED = "evidence changed"
CARD_SHOWING = "Showing this case"
CARD_MISSING = "not bundled"

# -- banner (plain) ------------------------------------------------------------------------------
BANNER_LIVE = "Recorded live run · {model} · finished {date} · not re-run here"
BANNER_FIXTURE = "Recorded run · scripted replies, no model called · finished {date} · not re-run here"
BANNER_AUDIT = "Recorded deterministic audit · finished {date} · not re-run here"
BANNER_TAG = "Recorded run"
MODEL_NAMES = {"nvidia/nemotron-3-super-120b-a12b": "Nemotron"}
FIXTURE_PROPOSER = "a scripted fixture reply"
UNNAMED_MODEL = "the model"
NO_DATE = "date not recorded"
ORIGINAL_TITLE = (
    "Original, trusted evaluator"  # the Finding card's heading (Expert view)
)
# The replay disclosure and the HAR citation (shown with every bundled case; moved here from
# atlas.hosted.page, which keeps them under the same names).
REPLAY_DISCLOSURE = (
    "Replay: these are recorded runs. Every recorded hash is recomputed from the bundled "
    "files before anything is shown; nothing is re-executed here and no model is called."
)
HAR_CITATION = (
    "UCI HAR: Reyes-Ortiz, J., Anguita, D., Ghio, A., Oneto, L., & Parra, X. (2013). Human "
    "Activity Recognition Using Smartphones [Dataset]. UCI Machine Learning Repository. "
    "https://doi.org/10.24432/C54S4K. The dataset page grants CC BY 4.0; the archive's 2012 "
    'README.txt adds "Any commercial use is prohibited." This demo shows precomputed results '
    "only and does not distribute the data (benchmarks/real_sensor/ATTRIBUTION.md)."
)
# The HAR citation without its repository file reference (the full citation, with the file,
# is shown in Expert view: atlas.hosted.page.HAR_CITATION).
HAR_CITATION_PLAIN = (
    "UCI HAR: Reyes-Ortiz, J., Anguita, D., Ghio, A., Oneto, L., & Parra, X. (2013). Human "
    "Activity Recognition Using Smartphones [Dataset]. UCI Machine Learning Repository. "
    "https://doi.org/10.24432/C54S4K. The dataset page grants CC BY 4.0; the archive's 2012 "
    'README.txt adds "Any commercial use is prohibited." This demo shows precomputed results '
    "only and does not distribute the data."
)

# -- the verdict line ----------------------------------------------------------------------------
VERDICT_ORIGINAL = {
    "VIOLATION_FOUND": "ATLAS found a violation in this evaluation.",
    "NO_VIOLATION_FOUND": "ATLAS found no violation in this evaluation.",
    "INCONCLUSIVE": "ATLAS could not complete its assessment: required evidence is "
    "incomplete.",
    "NOT_SUPPORTED": "ATLAS cannot assess this claim or project.",
}
VERDICT_ALL_PASS = (
    "A revision proposed by {model} was executed in isolation and passes every required "
    "check within the coverage shown."
)
VERDICT_CANDIDATE = (
    "A revision proposed by {model} was executed in isolation; ATLAS's outcome for it is "
    "{outcome}."
)
VERDICT_CANDIDATE_RUNNER = (
    "A revision proposed by {model} was executed (runner {runner}); ATLAS's outcome for it "
    "is {outcome}."
)
VERDICT_NONE_EXECUTED = {
    1: "The revision proposed by {model} was not executed in this run.",
    "n": "None of the {n} revisions proposed by {model} was executed in this run.",
}
VERDICT_NO_PROPOSAL = "No revision was proposed."
VERDICT_CONDITIONAL = {
    1: "1 check passed on a documented declaration that ATLAS did not verify.",
    "n": "{n} checks passed on a documented declaration that ATLAS did not verify.",
}

# -- the five steps ------------------------------------------------------------------------------
STEP_TITLES = {
    1: "The claim",
    2: "What the checks found",
    3: "The AI's fix (untrusted)",
    4: "Human approval & sealed run",
    5: "Verified evidence",
}
STEP_LABEL = "**{n} · {title}** — {summary}"
SHOW_EXPERT = "Show expert detail"
SHOW_EVIDENCE = "Show me the evidence"
EXPERT_TOGGLE = "Expert view"
EXPERT_HELP = "Adds assertion IDs, hashes, run-relative file paths, sources, costs and request counts."

# step 1
NO_MANIFEST = "No manifest was recorded for this run."
MANIFEST_UNREADABLE = "The recorded manifest could not be read."
CLAIM_INTRO = "What the project says its model can do:"
CLAIM_SOURCE = (
    "Read-only, from the run's own `{path}` (the manifest the run evaluated)."
)
NO_OUTCOME = "This run recorded no outcome for the original."

# step 2 (summary)
LEAK_FAILS = "{k} of {n} required checks FAIL in the original evaluation"
LEAK_ALL_PASS = "All {n} required checks PASS in the original evaluation"
LEAK_NONE_FAIL = "No required check FAILs in the original evaluation"
LEAK_NOT_ASSESSED = {1: "1 could not be assessed", "n": "{m} could not be assessed"}
LEAK_ERROR = {1: "1 ended in ERROR", "n": "{m} ended in ERROR"}
ANALOGY_LABEL = "In everyday terms"
ANALOGY_GROUP = (
    "Like testing a medical AI on new scans of the same patients it studied: it can "
    "recognise those people, so the score says little about patients it has never met."
)
ANALOGY_FIT = (
    "Like deciding what to study by looking at the final exam first: the score looks better "
    "than it would on an exam you had never seen."
)
# The assertions whose FAIL shows each analogy (the same text for every run).
ANALOGIES = (
    (
        (
            "split.no_group_overlap",
            "split.sampling_unit_disjoint",
            "split.repeated_measures_rule",
        ),
        ANALOGY_GROUP,
    ),
    (("fit.state_dependencies_within_fold_train",), ANALOGY_FIT),
)

# step 3
NO_PROPOSAL = "No revision was proposed."
PROPOSED_BY = "Proposed by {model}; ATLAS does not trust this text."
PROPOSALS_SUMMARY = {
    1: "{model} proposed 1 revision: {parts}",
    "n": "{model} proposed {n} revisions: {parts}",
}
PROPOSAL_PARTS = {
    "executed": "{k} executed",
    "rejected": "{k} rejected by ATLAS validation",
    "declined": "{k} declined at approval",
    "unavailable": "{k} not run (runner unavailable)",
    "not_executed_here": "{k} not executed here",
    "other": "{k} with another recorded outcome",
}
PROPOSAL_HEAD = "Revision {n}"
PROPOSAL_OUTCOME = {
    "executed": "Passed ATLAS validation and was executed after approval (step 4).",
    "rejected": "Rejected by ATLAS validation before it could run.",
    "declined": "Declined at approval, so it did not run.",
    "unavailable": "Not run: the isolated runner was unavailable.",
    "not_executed_here": "Passes ATLAS validation; not executed here.",
}
PROPOSAL_UNKNOWN = "Recorded outcome: {code}."
DIFF_CAPTION = "Proposed change (diff)"
NO_DIFF = "No diff was stored for this revision."
RATIONALE_CAPTION = "The model's explanation"
DRILLDOWN_TITLE = "Evidence drill-down · {side}"

# step 4 (summary)
TYPED_APPROVALS = {1: "1 typed approval", "n": "{n} typed approvals"}
UNTYPED_ONLY = "Approved without a typed confirmation"
# A run whose only approvals were given by the T-09 audit script (its recorded approval
# reason; no typed confirmation, no AI agent): the whole step 4 summary (slice 2, A2).
SCRIPT_ONLY = (
    "No AI agent took part: the audit script approved and ran the original in the isolated "
    "Docker runner."
)
MIXED_APPROVALS = "{t} typed and {u} untyped approvals"
NO_APPROVAL = "No approval recorded"
RAN_ORIGINAL = "the original ran in the isolated Docker runner"
RAN_BOTH = {
    1: "the original and 1 revision ran in the isolated Docker runner",
    "n": "the original and {k} revisions ran in the isolated Docker runner",
}
RAN_OTHER = "the original ran in runner {runner}"
NOT_RUN = "the original was not run"
NOT_HERE_SUFFIX = {
    1: "; 1 revision not executed here",
    "n": "; {n} revisions not executed here",
}
# step 4 (body)
WHO_ORIGINAL = "The original project code"
WHO_REVISION = "Revision {n}"
WHO_REVISION_UNKNOWN = "A revision"
APPROVED_TYPED = "{who}: approved by typing the start of its code hash."
APPROVED_UNTYPED = "{who}: approved without a typed confirmation."
APPROVED_SCRIPT = "{who}: approved by the audit script, without a typed confirmation."
NOT_APPROVED = "{who}: not approved, so it did not run."
EXEC_ISOLATED = "{who} ran in the isolated Docker runner"
EXEC_WITH = " with {facts}"
EXEC_FACTS = {
    "network": "no network",
    "user": "a non-root user",
    "read_only": "a read-only filesystem",
}
EXEC_REMOVED = " The container was removed afterwards."
EXEC_OTHER = "{who} ran in runner {runner} (status {status})."
NOT_EXECUTED_HERE = "{who}: not executed here."
AND = " and "
APPROVALS_HEAD = "Approvals"
EXECUTIONS_HEAD = "Sealed runs"
EXEC_SOURCE = (
    "{sub}/execution.json · runner, status, docker_args (--network, --user, --read-only), "
    "container_removed; agent_log.jsonl · event approval (kind, decision, approver_reason, "
    "candidate_hash)"
)

# step 5 (summary)
PROOF_MOVED = {
    1: "1 check moved from FAIL to PASS · evidence intact, {v} of {t} recorded items",
    "n": "{k} checks moved from FAIL to PASS · evidence intact, {v} of {t} recorded items",
}
PROOF_INTACT = "Evidence intact: {v} of {t} recorded items verified now"
PROOF_TILES = "Every check, before and after"
PROOF_TILES_SINGLE = "Every check"

# -- HUD plain-mode text (atlas.ui.hud) -----------------------------------------------------------
RING_PLAIN = "recomputed now"
RING_DIFFER = "{d} of {t} recorded items differ"
HEAD_BEFORE = "Before"
HEAD_AFTER = "After · verified revision"
HEAD_ORIGINAL = "Original"
PANE_REVISION = "verified revision"
LEAK_TITLE = "Leak map · {side}"
FLOW_TITLE = "Fit-scope flow · {side}"
SIDE_ORIGINAL = "original"
LEAK_Y_PLAIN = "Groups on both sides of the split, by test fold"
LEAK_LEGEND_BOTH = "filled red: on both sides of the split in that fold"
LEAK_LEGEND_NONE = "dotted outline: no shared groups"
LEAK_NONE_LISTED = "No group is on both sides of the split in any fold."
FOLD_LANE = "recorded fits"
FOLD_LANES_SOURCE = "{base}/provenance.jsonl · events type fit · fold, class"
TILES_TITLE = "Required checks · {side}"
TILE_FAILED = "Found: {label}"
REASON_LABEL = "Reason"
CONDITIONAL_PASS = "PASS rests on a documented declaration that ATLAS did not verify."
INTEGRITY_NOTE_PLAIN = (
    "Each hash the run recorded is recomputed from the bytes on disk, and each reported "
    "outcome is compared with the recorded result. This detects changes since recording; it "
    "does not authenticate a run whose files and recorded hashes were both rewritten."
)
BRIEF_INTACT_PLAIN = "Evidence intact: {v} of {t} recorded items verified now."
BRIEF_FAIL_PLAIN = "FAIL: {label}"
BRIEF_REVISION_PLAIN = (
    "The AI's revision, executed and verified: {outcome}; {k} FAIL → PASS."
)
BRIEF_SOURCE_PLAIN = (
    "From the run's verified files and fixed labels only; no model-written text."
)
TRACK_TITLE_PLAIN = "What happened, in order"

# -- reason sentences ----------------------------------------------------------------------------
# One fixed template per assertion that records observed counts (`atlas.ui.hud.reasons` fills
# them from that assertion's own observed object only; every field must be recorded, or no
# sentence is shown). Assertions without counts show their status only.
REASONS = {
    "split.evaluation_folds_nonempty": "{empty} of {folds} test folds have no rows to "
    "evaluate",
    "split.no_row_overlap": "{k} rows appear in both training and testing in {m} of {n} "
    "folds",
    "split.no_shared_source_observation": "{k} original observations appear in both "
    "training and testing, in {m} folds",
    "split.no_group_overlap": "{k} {column} values appear on both sides of the split in "
    "{m} of {n} folds",
    "split.sampling_unit_disjoint": "{k} {column} values (the sampling unit) appear on both "
    "sides of the split in {m} of {n} folds",
    "split.repeated_measures_rule": "{k} {column} values have measurements on both sides of "
    "the split, in {m} folds",
    "split.temporal_separation": "{w} training and test item pairs are closer in time than "
    "the declared minimum gap, across {f} folds",
    "fit.state_dependencies_within_fold_train": "{cls} was fit once on {rows} rows "
    "(scope: {scope}) and reused in {folds} folds",
    "fit.state_dependencies_within_fold_train.pass": "{judged} uses of a fitted step were "
    "checked; {v} relied on rows outside their fold's training data",
    "fit.coverage_complete": "{fits} classifier fits traced across {folds} folds; {gaps} "
    "folds have gaps",
    "metric.prediction_ids_match_eval_ids": "{m} of {folds} folds have predictions that do "
    "not match their test rows",
    "metric.reported_matches_recomputed": "Reported {reported}, recomputed {recomputed}: "
    "difference {diff} (tolerance {tol})",
    "temporal.cutoff_precedes_evaluation": "{w} test rows have a prediction time before the "
    "training cutoff plus the gap, across {f} folds",
    "temporal.features_available_when_used": "{w} feature values were used before they "
    "became available, across {f} features",
    "temporal.training_labels_available_by_cutoff": "{w} training rows, or their labels, are "
    "dated after their fold's cutoff, across {f} folds",
}
# The same sentences when nothing overlaps (k = 0), so none reads "0 ... in 0 of N folds"
# (`atlas.ui.hud.reasons` picks these; the fields are the same).
REASONS_NONE = {
    "split.no_row_overlap": "No row appears in both training and testing in any of the {n} "
    "folds",
    "split.no_shared_source_observation": "No original observation appears in both training "
    "and testing in any fold",
    "split.no_group_overlap": "No {column} value appears on both sides of the split in any of "
    "the {n} folds",
    "split.sampling_unit_disjoint": "No {column} value (the sampling unit) appears on both "
    "sides of the split in any of the {n} folds",
    "split.repeated_measures_rule": "No {column} value has measurements on both sides of the "
    "split in any fold",
}


def plural(table: dict, count: int, **fields) -> str:
    """The singular (key 1) or plural ("n") entry of a template table, filled."""
    return table[1 if count == 1 else "n"].format(**fields)


# -- the local page (atlas.ui.local_page): the recorded-runs folder, never as a local path ----------
RECORDED_ROOT_REPO = "the repository's `{path}/` folder"
RECORDED_ROOT_ENV = "the folder named by ATLAS_UI_RECORDED_DIR"


# ================================================================================================
# Slice 2 (2026-10-20): ATLAS Checks vs. Model Alone, How It Works & Limits, the tamper demo.
# ================================================================================================

# -- shared ------------------------------------------------------------------------------------
EVIDENCE_CHANGED_CODE = "EVIDENCE CHANGED"
SOURCE_LABEL = "Source"
DIAGRAM_LABEL = "Diagram"

# -- ATLAS Checks vs. Model Alone (atlas.ui.versus) ----------------------------------------------
# Every number on this page comes from the tracked T-11 result files (evaluation/results/
# t11-live-20261019/) and evaluation/expected.json, after their SHA-256 match the recorded ones.
VS_QUESTION = (
    "Does ATLAS's deterministic checking add anything over the same AI model reading the "
    "same files?"
)
VS_SETUP = (
    "The same AI model (Nemotron) read the same project files, with no executable checks and "
    "no ATLAS results, and said which of each project's listed checks are violated: {r} tries "
    "for each of {c} development projects. ATLAS audited the same {c} projects once each."
)
VS_CHANGED = (
    "**evidence changed since recording**: {d} of {t} recorded result files differ, so no "
    "result is shown."
)
VS_CHANGED_ACTION = (
    "restore the files in `evaluation/results/t11-live-20261019/` and `evaluation/expected.json` "
    "from the repository and open this page again; the table lists each differing file."
)
VS_GATE_NOTE = (
    "Each result file's SHA-256 is recomputed now and compared with the value recorded in "
    "evaluation/results/t11-live-20261019/README.md (and expected.json with the hash recorded "
    "in suite.json). This detects changes since recording; it does not authenticate files "
    "whose recorded hashes were rewritten too."
)
VS_INTACT = "Result files intact: {v} of {t} recomputed now."
# The chart
VS_CHART_TITLE = "What each found, on the same {c} development projects"
VS_SERIES_ATLAS = "ATLAS"
VS_SERIES_MODEL = "Model alone"
VS_PANELS = {
    "found": "Predeclared violations found",
    "false": "False alarms",
    "invalid": "Invalid answers",
}
VS_PANEL_NOTES = {
    "found": "share of the predeclared violations each could be scored on",
    "false": "violations named that were not predeclared",
    "invalid": "replies that broke the answer format and were not scored",
}
VS_ROW_SAME = "Model alone, same {m} problems"
VS_ROW_ALL = "Model alone, all {n} problems"
VS_FOUND_ATLAS = "{k} of {n} assessable"
VS_FOUND_ATLAS_GAP = "{k} of {n} assessable ({x} of {t} not assessed)"
# The model's figures are detections summed over its usable answers (one chance per planted
# problem per usable answer on that problem's project), not distinct problems.
VS_FOUND_SAME = "{k} of {n} detections"
VS_FOUND_ALL = "{k} of {n} detections"
VS_FOUND_MODEL = (
    "{ks} of {ns} detections on the same {m} problems; {ka} of {na} on all {t}"
)
VS_CHART_NOTE = (
    "The model's figures count each planted problem once per usable answer on its project "
    "({v} usable answers on the two flawed projects), so they are detections, not distinct "
    "problems."
)
VS_NONE = "none"
VS_OF = "{k} of {n}"
VS_ALT = (
    "Bar chart in three panels. Predeclared violations found: ATLAS {fa}; model alone {fm}. "
    "False alarms: ATLAS {xa}; model alone {xm}. Invalid answers: ATLAS {ia}; model alone "
    "{im}."
)
VS_TABLE_MEASURE = "Measure"
VS_TABLE_SEP = "; "
# What this means: the reviewed findings, copied exactly from docs/EVALUATION.md, "Results
# (live, 2026-10-19)", "Findings (descriptive)" (a test compares them). Expert view shows them;
# plain view shows VS_MEANS_PLAIN below.
VS_MEANS_HEAD = "What this means"
T11_FINDINGS = (
    (
        "On these four development cases, Nemotron alone, reading the same files with no "
        "executable checks, named 19 of the 23 predeclared violations across its 9 valid trials "
        "(recall 0.83), with 2 false positives (fit.coverage_complete, twice, on har_flawed) and "
        "no false violation on either clean control (0 in 4 valid clean trials)."
    ),
    (
        "ATLAS's deterministic audit found all 8 assessable predeclared violations with no false "
        "positive and no false violation on the clean controls. It left split.no_window_overlap "
        "NOT_ASSESSED on har_flawed (missing window metadata), which the scoring rules exclude "
        "from leg (a)'s FN (8/8 = 1.0000 recall on assessable violations, or 8/9 = 0.8889 against "
        "all 9 expected violations), whereas leg (b) counts it as 3 of its 4 FNs (19/23 = 0.8261 "
        "overall, or 19/20 = 0.9500 on the 8 ATLAS-assessable violations). Nemotron alone did not "
        "name it in any of its 3 valid har_flawed trials."
    ),
    (
        "Nemotron alone varied between repetitions (s01_faulty: 4 of 4, then 3 of 4) and 3 of its "
        "12 replies (including 2 of the 6 clean-control trials) were invalid (rationale_too_long, "
        "over 600 characters) and excluded from scoring, which could change leg (b)'s rates; "
        "ATLAS's checks are deterministic by design (evaluated once per case here: 3 recorded "
        "runs, 1 re-run) and rest on executed evidence."
    ),
    (
        "har_flawed reports balanced accuracy 0.9064, which ATLAS reproduces for the mean over "
        "folds (0.9064; pooled 0.9063) against har_clean's 0.8752 (pooled 0.8746); for s01_faulty "
        "(no metric reported), ATLAS recomputes 0.6824 (pooled 0.6812) against s02_clean's 0.6688 "
        "(pooled 0.6687). The gaps are descriptive protocol comparisons."
    ),
    (
        "These are development cases on which ATLAS's checks were built: not held-out, small in "
        "number, and not evidence of generalization. The comparison evaluates violation detection "
        "only and does not test repair; repair evidence is reported separately (TASKS.md T-06, "
        "live run 6)."
    ),
    (
        "Two asymmetries the reader needs: the files given to leg (b) describe the project's "
        "deliberate flaws in plain text (s01_faulty: `benchmarks/t01/s01_faulty/evaluate.py:1`, "
        "and the comment at line 12; har_flawed: `benchmarks/real_sensor/har_flawed/evaluate.py:4`, "
        "and `benchmarks/real_sensor/har_flawed/atlas_manifest.json:586`), which leg (b) can read "
        "and which leg (a)'s executed checks do not use, so leg (b)'s detection on those cases may "
        "be helped by that text; and leg (a) executes the evaluation against the data in Docker, "
        "whereas leg (b) reads only the manifest and source, without the data table."
    ),
    (
        "Amendment 1 (leg (b) input ceiling 40,000, made before any live trial) prevented the two "
        "HAR cases from being refused before dispatch; leg (b) receives the files in one prompt, "
        "whereas the agent reads them through bounded tools."
    ),
)
# Plain view (slice 3): four plain-words items in place of the findings; every number in them
# is checked against scores.json and the findings above (tests/unit/test_ui_slice3.py).
VS_MEANS_PLAIN = (
    (
        "The two flawed projects contain 9 planted problems. The model on its own gave 5 usable "
        "answers on those projects, so there were 23 chances to name a planted problem; it named "
        "19. It raised 2 false alarms on the flawed real-data project and none in its 4 usable "
        "answers on the two clean projects."
    ),
    (
        "ATLAS found all 8 of the planted problems its checks can assess, with no false alarms. One "
        "planted problem (overlapping time windows in the real-data project) needs information the "
        "project did not record, so ATLAS reported it as not assessed instead of guessing. The model "
        "on its own did not name it in any of its 3 usable answers for that project."
    ),
    (
        "The model's answers varied from try to try, and 3 of its 12 answers broke the required "
        "format and could not be scored. ATLAS's checks are deterministic by design."
    ),
    (
        "This compares finding problems only, not fixing them, on the small set of projects ATLAS "
        "was built on."
    ),
)
VS_FINDINGS_SOURCE = (
    'Copied exactly from docs/EVALUATION.md, "Results (live, 2026-10-19)", "Findings '
    '(descriptive)". In the findings, leg (a) is ATLAS and leg (b) is the model alone.'
)
VS_MEANS_PLAIN_SOURCE = (
    "In plain words, from scores.json and the reviewed findings; Expert view shows the "
    "findings exactly as reviewed."
)
# The caveats, in plain words, always visible (sources: docs/EVALUATION.md §9 and the findings)
VS_CAVEATS_HEAD = "Read these before the numbers"
VS_CAVEATS = (
    (
        "Development cases, not held-out: ATLAS's checks were built and debugged on these "
        "projects, so its results on them are not evidence that it works on new projects."
    ),
    (
        "The flawed projects' own files describe their flaws in plain text, and the model could "
        "read that text; ATLAS's executed checks do not use it."
    ),
    (
        "ATLAS evaluated each project once ({rec} recorded runs, {rerun} re-run): its checks are "
        "deterministic by design, and this comparison did not repeat them. The model's answers "
        "varied between tries."
    ),
    (
        "Invalid replies were not scored: {k} of the model's {n} replies broke the answer format, "
        "which could change its rates."
    ),
    "Small numbers: {c} projects and {r} tries each support descriptive observations only.",
    (
        "ATLAS ran each evaluation against its data in an isolated container; the model alone read "
        "only the manifest and the code, without the data table."
    ),
)
VS_COST = "Estimated cost of this comparison: ${usd} (estimate, not billing)."
VS_REVIEW = "Claims reviewed by Gemini (2026-10-19)"
VS_REVIEW_FULL = (
    "Claims review: Gemini Argon (high effort), 2026-10-19, SUPPORTED WITH CHANGES; changes "
    "applied."
)
# Expert view
VS_EXPERT_RUN = (
    "Run `{run_dir}` (git-ignored), model `{model}`, seed {seed}, policy {policy}; {r} "
    "repetitions per case, at most {q} requests per case run."
)
VS_FILES_HEAD = "Result files and their hashes"
VS_EXPECTED_HEAD = (
    "Expected violated assertion IDs (predeclared, evaluation/expected.json)"
)
VS_ATLAS_HEAD = "ATLAS deterministic audit, per case (scores.json)"
VS_TRIALS_HEAD = "Model alone, every trial (scores.json)"
VS_TOTALS_HEAD = "Totals (scores.json)"
VS_SOURCES = (
    "Sources: evaluation/results/t11-live-20261019/scores.json (the chart, the tables), "
    "suite.json (run settings, sources, cost), results.md, evaluation/expected.json; protocol "
    "and findings: docs/EVALUATION.md."
)

# -- How It Works & Limits (atlas.ui.limits) -----------------------------------------------------
HOW_HEAD = "How it works"
HOW_INTRO = "Five steps, in order. Only the deterministic checks decide an outcome."
HOW_STEPS = (
    (
        "The evaluation is run",
        (
            "ATLAS runs the project's own evaluation in an isolated container and records what "
            "happened: which rows each step learned from, which rows were tested, and the "
            "predictions."
        ),
        "docs/SPEC.md §4.3, §10",
    ),
    (
        "Deterministic checks decide",
        (
            "Fixed checks read that record and decide whether the evaluation breaks a rule of "
            "the claim, for example the same person on both sides of the split. No AI model "
            "takes part in this decision."
        ),
        "docs/SPEC.md §5, §6; README.md, Roles",
    ),
    (
        "The AI may propose a revision, which ATLAS does not trust",
        (
            "An AI model (Nemotron) may read the project and propose a revised evaluation script. "
            "The proposal is only checked for allowed changes, and the model's text is never "
            "evidence."
        ),
        "docs/SPEC.md §9 items 1-3, §11; README.md, Roles",
    ),
    (
        "A human approves by typing the code hash",
        (
            "A person approves the original code and each exact revision by typing the start "
            "of its code hash; the approval is bound to the snapshot and code hashes. Any "
            "change to the code needs a new approval."
        ),
        (
            "docs/SPEC.md §9 item 5; README.md, Safety controls and their reviews, and Setup "
            "and running"
        ),
    ),
    (
        "The revision runs sealed and is re-checked",
        (
            "The approved revision runs sealed in the isolated container, and the same checks "
            "judge it again. The model never declares success."
        ),
        "docs/SPEC.md §9 item 6, §6",
    ),
)
HOW_DIAGRAM_ALT = (
    "Diagram of the five steps in order: the evaluation is run, deterministic checks decide, "
    "the AI may propose a revision (untrusted), a human approves by typing the code hash, the "
    "revision runs sealed and is re-checked by the same checks."
)
HOW_DIAGRAM_SHORT = (
    "Evaluation is run",
    "Checks decide",
    "AI proposes (untrusted)",
    "Human approves",
    "Sealed run, re-checked",
)
SAFETY_HEAD = "Safety, in plain words"
SAFETY = (
    (
        (
            "Isolated Docker runner: no network, a non-root user and a read-only filesystem, with "
            "limits on memory, CPU, processes and time. If the container runner is unavailable, "
            "ATLAS stops and never runs code directly on the host computer."
        ),
        "docs/SPEC.md §10; README.md, Safety and honesty rules",
    ),
    (
        (
            "Typed approval bound to the snapshot and code hashes: an approval names the exact "
            "original or revision code, and the runner refuses to run any other code."
        ),
        (
            "docs/SPEC.md §9 item 5; README.md, Safety controls and their reviews, and Setup "
            "and running"
        ),
    ),
    (
        (
            "The AI's text is never evidence: its diffs, explanations and raw replies are "
            "labelled untrusted, and outcomes come only from the trusted evaluator."
        ),
        "README.md, Safety and honesty rules and Roles",
    ),
    (
        (
            "Spending is reserved before every request, with caps: per run locally, and per "
            "session, per day and per route on the hosted demo. Totals are estimates, not "
            "billing."
        ),
        (
            "README.md, How ATLAS uses NVIDIA Nemotron (Cost accounting); "
            "docs/HOSTED_OPERATIONS.md §1, §4"
        ),
    ),
    (
        (
            "The hosted demo executes no project or candidate code: it replays recorded runs, "
            "and in a hosted live session it checks the AI's proposals and shows them as not "
            "executed here."
        ),
        "README.md, Architecture; docs/HOSTED_OPERATIONS.md §1; docs/SPEC.md §13",
    ),
    (
        (
            "Recorded runs are re-verified before display: every recorded hash is recomputed "
            'from the files, and a changed file shows "evidence changed" instead of a result. '
            "This detects changes since recording; it does not authenticate a run whose files "
            "and recorded hashes were both rewritten."
        ),
        "docs/HOSTED_OPERATIONS.md §1; README.md, Architecture",
    ),
)
LIMITS_HEAD = "Limits"
LIMITS_INTRO = (
    "The README's limitations, in plain words; none is softened. Expert view shows the "
    "original wording."
)
LIMITS_SOURCE = (
    'README.md, "Limitations" (copied from docs/SPEC.md §15 and the acceptance records)'
)
# The plain wording of each README "Limitations" item, in the README's order (a test checks
# that every README item has exactly one plain counterpart and its original wording).
LIMITS_PLAIN = (
    (
        "ATLAS can trace which rows each step learned from only for the supported steps. Its "
        "recorder runs inside the project's own process and is not tamper-proof; its "
        "fingerprints do not prove that every kind of preprocessing was observed; and a missing "
        "trace does not prove that a step did not happen."
    ),
    (
        "Tracing starts at the feature table the project supplies. How those features were "
        "extracted or normalised before that is not checked."
    ),
    (
        "ATLAS cannot detect a dependence between rows (for example, the same person) that the "
        "project did not declare. Some declared dependences have no rule in this version and are "
        "reported as not assessed."
    ),
    (
        "Without IDs for the original observations, duplicate detection only compares exact "
        "values, and it can leave possible duplicates unresolved."
    ),
    (
        "The time-based checks verify only the availability and separation rules the project "
        "declares, and the window check verifies only the declared recording streams and window "
        "intervals. None of them proves that training and test data are statistically "
        "independent."
    ),
    "A green result means only that the listed checks passed, within the coverage stated.",
    (
        "There are no held-out test projects: they were cut for the submission, so every "
        "detection result here is on the development projects ATLAS was built on."
    ),
    (
        "Running code in an isolated container reduces risk. It does not prove that the code is "
        "safe, that the recorded traces are intact, or that the science is correct."
    ),
    (
        "The live AI agent was accepted within its scope with these limits: the input-token "
        "figure is ATLAS's own estimate, and the provider's enforcement and billing are not "
        "verified; the model's reply format is not always reliable (schema failures in 5 of the "
        "8 live runs: runs 1 to 8, with 3 and 3b counted as one); raw replies are stored only "
        "from live run 3b onward; hiding secrets in a "
        "revision's output is best-effort; and it was tested on one Windows computer only."
    ),
    (
        "For the real-data (UCI HAR) projects, the declaration of how the recordings are "
        "contained is documented, not verified; whether the dataset's own normalisation was fit "
        "only on training data is not established; and both HAR projects were written by ATLAS's "
        "authors, so they are not independent benchmark evidence."
    ),
    (
        "ATLAS supports only small tabular classification projects with scikit-learn on a CPU, "
        "and exactly three kinds of claim: the same population, groups (such as people) not seen "
        "in training, and future time. Any other claim is reported as not supported. There is no "
        "store for final held-out labels yet."
    ),
    (
        "Established on 19 October 2026 for the private hosted app: it reaches Nebius and "
        "builds from the locked dependencies on the host, and a smoke test passed on the public "
        "and judge routes. Not yet established: a check of the public app by a signed-out "
        "visitor, and availability through 15 December 2026 (both at publication)."
    ),
    "Saving and reusing evaluation procedures was cut from this version.",
)
NOT_DO_HEAD = "What ATLAS does not do"
NOT_DO = (
    (
        (
            "It does not prove a claim true: a clean result means only that the listed checks "
            "passed within the coverage shown."
        ),
        'README.md, "Limitations"; docs/SPEC.md §15',
    ),
    (
        (
            "It does not check how the data was collected or labelled, or how features were "
            "extracted or normalised before the feature table the project supplies: its tracing "
            "starts at that table."
        ),
        'README.md, "Limitations" (provenance begins at the supplied feature table)',
    ),
    (
        (
            "It supports only small tabular classification, with three claim types (same "
            "population, unseen group, future time)."
        ),
        'README.md, "Limitations" (Scope)',
    ),
)

# -- the tamper demo (atlas.ui.tamper; on the Overview, below the verdict bar) ---------------------
TAMPER_HEAD = "Try tampering: change one byte in a copy and watch the check catch it"
TAMPER_INTRO = (
    "Pick one of this run's recorded files. ATLAS copies the recorded run to a temporary "
    "folder outside the repository, changes one byte in the copy, and runs the same check "
    "this page ran before showing anything."
)
TAMPER_PICK = "File to change in the copy"
# The files the demo may change, in this order, offered only when the run recorded a hash for
# them: (path in the run, plain label).
TAMPER_FILES = (
    ("original/outcome.json", "the original's recorded result"),
    ("candidates/c1/outcome.json", "the revision's recorded result"),
    ("original/execution.json", "the original's sealed-run record"),
    ("agent_log.jsonl", "the run's event log (approvals included)"),
)
TAMPER_ITEM_OUTCOME = "a reported outcome"
TAMPER_ITEM_FILE = "a recorded file"
TAMPER_BUTTON = "Change one byte in a copy and check it"
TAMPER_STATEMENT = (
    "This copied the recorded run, changed one byte in the copy, and ran the real check on "
    "it. The original recording is untouched."
)
TAMPER_RESULT = {
    1: "1 of {t} recorded items differ: {items} — outcome withheld",
    "n": "{d} of {t} recorded items differ: {items} — outcome withheld",
}
TAMPER_NOT_DETECTED = "0 of {t} recorded items differ: the change was not detected."
TAMPER_BYTE = "Changed in the copy: the last byte of {label}, {old} into {new}."
TAMPER_BYTE_EXPERT = (
    "Changed in the copy: byte {offset} of `{rel}`, 0x{old:02x} → 0x{new:02x}."
)
TAMPER_BYTE_NAMES = {0x0A: "a line break", 0x20: "a space"}
TAMPER_BYTE_OTHER = "byte 0x{value:02x}"
TAMPER_ORIGINAL_OK = (
    "The original recording, checked again after the demo: {v} of {t} recorded items "
    "verified, and every one of its {f} files is byte-for-byte unchanged."
)
TAMPER_DELETED = "The temporary copy was deleted."
TAMPER_TABLE_HEAD = "Differing items in the copy"
TAMPER_BUSY = "A tamper demo is already running in this session; wait for it to finish."
TAMPER_RATE = (
    "Limit reached: at most {n} tamper demos per session per hour. Try again later."
)
TAMPER_TOO_LARGE = (
    "This recorded run is larger than {mb} MB, so it is not copied for the demo."
)
TAMPER_LINK = "This recorded run contains a link, so it is not copied for the demo."
TAMPER_NOT_INTACT = "The original recording does not verify, so no copy was made and nothing was changed."
TAMPER_ORIGINAL_CHANGED = "The original recording no longer verifies after the demo. Nothing from the demo is shown."
TAMPER_UNKNOWN_FILE = "That file is not one the demo may change."
TAMPER_FAILED = (
    "The demo could not run, so no result is shown. The temporary copy was deleted and the "
    "original recording is unchanged."
)
TAMPER_LIMITS = (
    "One demo at a time per session, at most {n} per session per hour, and only for recorded "
    "runs up to {mb} MB. Nothing executes except hashing: no project code, no network."
)


# ================================================================================================
# Slice 3 (2026-10-20): the one-page audit report (atlas.ui.report).
# ================================================================================================
REPORT_BUTTON = "Download audit report"
REPORT_HELP = (
    "One printable HTML page built from this run's verified files only: no model-written text, "
    "no scripts, nothing fetched."
)
REPORT_TITLE = "ATLAS audit report"
REPORT_SUBJECT_CASE = "Case: {title}"
REPORT_SUBJECT_RUN = "Run: {run}"
REPORT_CLAIM = "The claim"
REPORT_CLAIM_INTRO = (
    "What the project says its model can do (from the recorded manifest):"
)
REPORT_OUTCOME = "Outcome"
REPORT_BEFORE = "Before: the original evaluation"
REPORT_AFTER = "After: the executed revision"
REPORT_NO_REVISION = "No revision was executed."
REPORT_CHECKS = "Required checks"
REPORT_COL_CHECK = "What the check verifies"
REPORT_COL_ID = "Assertion ID"
REPORT_COL_BEFORE = "Before"
REPORT_COL_AFTER = "After"
REPORT_LEAK = "What the checks found"
REPORT_APPROVAL = "Approval and sealed run"
REPORT_AUDIT_ONLY = (
    "Deterministic audit: no model was called and nothing was approved; the trusted, "
    "repository-authored pipeline ran once."
)
REPORT_EVIDENCE = "Evidence"
REPORT_INTEGRITY = "{v} of {t} recorded items verified when this report was generated."
REPORT_HASH_OUTCOME = "Recorded SHA-256 of {rel}"
REPORT_HASH_APPROVED = "Approved code hash ({who})"
REPORT_HASH_COL_ITEM = "Item"
REPORT_HASH_COL_VALUE = "SHA-256"
REPORT_DATA = "Data"
REPORT_WHY = "{label}: {text} Source: {url}"
REPORT_COMMIT = "ATLAS commit {commit}"
REPORT_POLICY = "policy {policy}"
REPORT_GENERATED = "generated {utc} (UTC)"
REPORT_MODEL_TEXT_NOTE = (
    "This report contains no model-written text: no explanation, reply or diff written by a "
    "model."
)
REPORT_SEP = " · "
