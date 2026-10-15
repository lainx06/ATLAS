# ATLAS — shared agent rules

Applies to every coding agent in this repo (Claude Code, Codex). Keep under one page.

## Scope
ATLAS checks whether a small Python/scikit-learn tabular classification experiment supports its stated deployment claim. LENS is the first capability: inspect, run evidence checks, propose a bounded evaluation-code revision, compare evidence, save a procedure only with verified prerequisites. Out of scope for V1: hardware, voice, deep learning, arbitrary notebooks/uploads, autonomous package installation.

## Source of truth (read before editing)
1. `STATUS.md`: current writer, checkpoint, working commands, blockers, next task.
2. `TASKS.md`: the current task and its acceptance criteria.
3. `PROJECT_BRIEF.md`, `docs/PRD.md`, `docs/SPEC.md`: product and contracts.
4. `DECISIONS.md`: settled decisions; reopen only with new evidence.
5. `docs/handoff/`: original kickoff documents (reference; do not edit).

## Commands (verified ones are listed in STATUS.md)
- Sync env: `uv sync --locked`
- Tests: `uv run pytest`  (exit 5 = no tests collected; that is not a pass)
- Lint/format: `uv run ruff check .` / `uv run ruff format --check .`

## Evidence policy
- Check statuses: PASS, FAIL, NOT_ASSESSED, ERROR. Unsupported or uninstrumented code is NOT_ASSESSED, never PASS.
- Report only commands actually run, with their real output. Mark proposals as proposed.
- Separate deployment mismatch from train/test contamination. A lower score can be the honest result.
- Reviewer approval never substitutes for execution evidence.

## Isolation
- Candidate/generated code runs only in a disposable restricted container (no network, no credentials, bounded CPU/memory/PIDs/time, minimal mounts). A temp dir, subprocess timeout, `shell=False`, or reduced env is not a sandbox.
- If isolation is unavailable, use trusted fixtures only and fail closed. Never fall back to host execution.

## Cost and secrets
- Never read, print, or commit `.env` or API keys. `.env.example` holds placeholders only.
- Enforce run/call/retry/output caps. No billing changes, purchases, publishing, or pushes without explicit user approval.

## Prohibited edits
- Agents and candidate patches must not modify the trusted evaluator, holdout labels, pass criteria, or run policies to make a check pass.
- Do not edit `docs/handoff/`. Do not install third-party skills/hooks outside playbook Section 22.
- One writer at a time (see WRITER in STATUS.md). Reviewers do not edit implementation files.

## Learning guide
- `docs/ATLAS_Learning_Guide.md` explains ATLAS to the user. The builder updates it at task boundaries when architecture, implemented behavior, setup, acceptance status or important limitations change.
- Write for someone who knows basic Python and is learning C++ fundamentals; connect concepts to actual code and small examples.
- Keep planned, implemented (self-tested), independently verified and accepted behavior clearly separate.
- Reviewers flag material inaccuracies introduced by the reviewed change; read-only reviews do not edit the guide.
- The guide is explanatory and has no authority over `docs/SPEC.md`, `DECISIONS.md` or this file.
- Never include secrets or sealed held-out material.

## Agent skills

### Issue tracker

Local files only; nothing is published. Durable specs live in `docs/`; `TASKS.md` holds the task index and concise structured task entries (playbook Section 24); `handoffs/` is only for Section 19 external/substantial transfers. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: root `GLOSSARY.md` and `docs/adr/`, both created lazily. Routine decisions go in `DECISIONS.md`; ADRs only for consequential architectural decisions, each with a dated pointer in `DECISIONS.md`. See `docs/agents/domain.md`.
