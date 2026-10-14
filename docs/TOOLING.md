# Tooling record

Observed versions and settings. Only values actually printed by a command or shown in a client are recorded; anything else is marked unknown.

## Host (observed 2026-10-14)
| Tool | Version | How observed |
| --- | --- | --- |
| OS | Windows 11 Home 10.0.26200 | session environment |
| Windows PowerShell | 5.1.26100.9444 | `$PSVersionTable.PSVersion` |
| WinGet | 1.29.380 | `winget --version` |
| Git | 2.55.0.windows.5 | `git --version` |
| uv | 0.13.1 (62faed335 2026-10-13) | `uv --version` |
| Claude Code (application) | 2.1.292 | `claude --version` |
| VS Code | 1.99.3 | `code --version` |
| Python (project) | CPython 3.11.17, uv-managed | `uv python install 3.11` |
| Python (system, unused) | CPython 3.12.10 | `uv python list --only-installed` |
| Docker | not on PATH (not installed or not configured) | `Get-Command docker` |

Notes: MSYS2 Pythons at `C:\msys64\ucrt64\bin` are on PATH; uv prints "Failed to inspect Python interpreter" warnings for them. Harmless, as the project uses the uv-managed 3.11. `C:\Users\Lain\.local\bin` is not on PATH; irrelevant because commands use `uv run`.

## Builder model (Claude Code session)
- Model: Opus 5.5 (`claude-opus-5-5`), set via `/model opus` in this session.
- Effort: high, set via `/effort high` in this session.
- The Claude Code application version (2.1.292) is a separate thing from the model version.

## Python dependencies (resolved in `uv.lock`, 61 packages)
Direct runtime: numpy 2.4.6, pandas 3.0.6, scikit-learn 1.9.1, pydantic 2.14.1, streamlit 1.66.0, openai 3.31.0, python-dotenv 1.2.4.
Dev group: pytest 9.1.1, ruff 0.17.0.
Notable transitive: scipy 1.17.1, pyarrow 26.0.0.
Build backend: `uv_build>=0.13.1,<0.14.0`.

## Development skills
None installed. Start Here Step 6 (playbook Section 22.2) will record sources, pinned commit SHAs, copied dependencies, destinations, and load status here.

| Skill | Source | Commit | Destinations | State |
| --- | --- | --- | --- | --- |
| (none yet) | | | | deferred to Step 6 |
