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
