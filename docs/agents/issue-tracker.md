# Issue tracker: local files

This repo has no remote issue tracker. Work is tracked in version-controlled files.
Never run `gh issue` / `glab issue`, publish anywhere, or use `.scratch/` as a spec location.

## Where things live

- **Specs (durable):** markdown in `docs/`. The V1 product spec is `docs/PRD.md`; technical contracts are `docs/SPEC.md`. A later feature spec goes in `docs/specs/<feature-slug>.md`.
- **Tasks:** `TASKS.md` holds the task index and a concise structured entry per task, with the playbook Section 24 fields: task ID / Start Here step, owner, model decision, model/effort, read first, input state, change, acceptance, run, evidence, handoff, recovery.
- **Handoffs:** `handoffs/` is only for the external or substantial transfers in playbook Section 19 (e.g. `handoffs/A-<id>-<recipient>.md`, a browser-reviewer packet). Routine local Claude/Codex work and reviews use `TASKS.md`, `STATUS.md`, the reviewed checkpoint/diff, and actual evidence directly; no handoff file.
- **Decisions:** `DECISIONS.md` (see `docs/agents/domain.md` for when an ADR is warranted).

## When a skill says "publish to the issue tracker"

Write or update the spec file in `docs/` (above), and add or update the corresponding entry in `TASKS.md`. When the skill would create tickets, write them as task entries in `TASKS.md`. Show the user the diff; do not commit or push without approval.

## When a skill says "fetch the relevant ticket"

Read the referenced `docs/` spec, or the `TASKS.md` entry, by ID or path.

## Triage roles

There is no label system. Where a skill applies a role (for example, `to-spec` applies `ready-for-agent`), record it as a `Status:` line at the top of the spec and in the task's `TASKS.md` status. `ready-for-agent` means "fully specified", not "accepted": user acceptance is recorded in `DECISIONS.md` / `STATUS.md`.

## Comments and history

Consequential discussion outcomes go in `DECISIONS.md`; Git history is the log.
