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
    "ATLAS checks whether an AI model's test results can be trusted, shows its evidence, and "
    "safely tests a fix."
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
PAGE_AGENT = "AI Agent vs. Model Alone"
PAGE_LIMITS = "How It Works & Limits"
PLACEHOLDER = "Coming in slice 2"
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
        "by ATLAS.",
    ),
    Case(
        "harclean",
        "A clean evaluation",
        "t09/agent-har_clean-ac63eaecd7a8",
        "The same real sensor data with an evaluation designed to keep each person on one "
        "side of the split.",
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
    "check."
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
    2: "The leak",
    3: "The AI's fix (untrusted)",
    4: "Human approval & sealed run",
    5: "Verified proof",
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
LEAK_Y_PLAIN = "Groups on both sides of the split in the original, by test fold"
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


def plural(table: dict, count: int, **fields) -> str:
    """The singular (key 1) or plural ("n") entry of a template table, filled."""
    return table[1 if count == 1 else "n"].format(**fields)


# -- the local page (atlas.ui.local_page): the recorded-runs folder, never as a local path ----------
RECORDED_ROOT_REPO = "the repository's `{path}/` folder"
RECORDED_ROOT_ENV = "the folder named by ATLAS_UI_RECORDED_DIR"
