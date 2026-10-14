# ATLAS project brief

Stable one-page context for any assistant's first contact. Details: `docs/handoff/`, `docs/PRD.md`, `docs/SPEC.md`.

**Product.** ATLAS is an Experimental Verification Workspace. Its first capability, LENS, determines whether a small ML experiment supports its stated deployment claim (for example, "works on people absent from training"). It inspects a supported project, runs executable evidence checks, proposes a bounded evaluation-code revision, runs it in isolation, compares evidence, and saves a reusable evaluation procedure only when its prerequisites are machine-verified. It is not a universal validity certificate.

**User.** Student researchers or small applied-ML teams with a Python classification experiment and a concrete generalization claim.

**V1 scope.** Small CSV/Parquet feature tables, explicit target/metadata columns, CPU scikit-learn estimators, a documented adapter contract. Five deterministic checks: split integrity, preprocessing fit provenance, independent metric/baseline, temporal availability, robustness across predeclared seeds/groups. Status values: PASS / FAIL / NOT_ASSESSED / ERROR. Streamlit UI over an engine that is independent of the UI.

**Central demonstration.** A misleading evaluation is diagnosed and corrected, followed by justified reuse of the procedure on a compatible project and refusal on a mismatched one. A lower score can be the honest result.

**Runtime requirement.** The app must call a real NVIDIA open model through Nebius Token Factory; model IDs come from the authenticated catalog only.

**Invariants.** Trusted evaluator and holdout labels are immutable to the agent. Candidate code runs only in a restricted container; no host fallback. No secrets in Git, prompts, fixtures, or containers. Synthetic data is labeled synthetic.

**Competition.** Nebius x NVIDIA Global AI Hackathon, Coding and Agentic Engineering track. Internal target Oct 29, 2026; official deadline Oct 30, 2026, 13:00 America/New_York (re-verify before submitting).

**Stack.** Python 3.11, uv, numpy/pandas/scikit-learn, Pydantic, Streamlit, pytest, Ruff, OpenAI-compatible client pointed at Nebius, Docker for isolation.

**Status.** Setup only; no application behavior is implemented. See `STATUS.md`.
