# ATLAS project brief

Stable one-page context for any assistant's first contact. Details: `docs/handoff/`, `docs/PRD.md`, `docs/SPEC.md`.

**Product.** ATLAS is an Experimental Verification Workspace. Its first capability, LENS, determines whether a small ML experiment supports its stated deployment claim (for example, "works on people absent from training"). It inspects a supported project, runs executable evidence checks, proposes a bounded evaluation-code revision, runs it in isolation, compares evidence, and saves a reusable evaluation procedure only when its prerequisites are machine-verified. It is not a universal validity certificate.

**User.** Student researchers or small applied-ML teams with a Python classification experiment and a concrete generalization claim.

**V1 scope.** Small CSV/Parquet feature tables, explicit target/metadata columns, CPU scikit-learn estimators, a documented adapter contract. Exactly three supported claim types (DECISIONS.md Q1): `same_population`, `unseen_group` and `future_time`; any other claim, including unseen group plus future time combined, is a run-level `NOT_SUPPORTED`. Five deterministic checks: split integrity, preprocessing fit provenance, independent metric/baseline, temporal availability, robustness across predeclared seeds/groups. Status values: PASS / FAIL / NOT_ASSESSED / ERROR. Streamlit UI over an engine that is independent of the UI.

**Central demonstration.** A misleading evaluation is diagnosed and corrected, followed by justified reuse of the procedure on a compatible project and refusal on a mismatched one. A lower score can be the honest result.

**Delivery (T-03 decision, DECISIONS.md 2026-10-16; planned, not built):**
- **Limited hosted demo:** curated examples, trusted evaluation functions only and live, capped Nemotron inference through a server-side key. Generated diffs are shown labelled "not executed here".
- **Full local build:** the complete workflow, with candidate code running in the isolated Docker runner.
- Full hosted execution is a stretch goal. The hosted app is not ready until Nebius connectivity and the full locked build are tested on the host (T-12).

**Runtime requirement.** The submitted app must call an NVIDIA open-source model; the track also allows running on Nebius AI Cloud. ATLAS uses NVIDIA open models served through Nebius Token Factory, targeting `nvidia/nemotron-3-super-120b-a12b` (T-04). Model IDs come from the authenticated catalog only. Two capped smoke calls have succeeded; the agent's first live run (T-06 slice 4) is not yet authorized, so this requirement is not yet met by the application itself.

**Invariants.** Trusted evaluator and holdout labels are immutable to the agent. Candidate code runs only in a restricted container; no host fallback. No secrets in Git, prompts, fixtures, or containers. Synthetic data is labeled synthetic.

**Competition.** Nebius x NVIDIA Global AI Hackathon, Coding and Agentic Engineering track. Internal target Oct 29, 2026; official deadline Oct 30, 2026, 13:00 America/New_York (re-verify before submitting). Required deliverables (playbook §2 and §23; re-check against the current rules):
- a working demo URL or test build;
- a public, licensed repository with setup instructions;
- a project description;
- a public YouTube video under 3 minutes;
- sponsor-tool feedback (Nebius and NVIDIA);
- free judging access through December 15, 2026 (under the currently published schedule).

**Stack.** Python 3.11, uv, numpy/pandas/scikit-learn, Pydantic, Streamlit, pytest, Ruff, OpenAI-compatible client pointed at Nebius, Docker for isolation.

**Status (2026-10-16).** T-01 to T-05 accepted within their documented scopes. T-06 slices 1–3 independently verified by Codex (slice 3 offline, at `5e63fc4`). T-06 slice 4 controls (prompt budget, spending limits) implemented and self-tested offline at `96f6fc6`, awaiting Codex review. Not yet built: the UI, procedures and hosting. See `STATUS.md`.
