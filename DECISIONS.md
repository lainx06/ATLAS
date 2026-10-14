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
