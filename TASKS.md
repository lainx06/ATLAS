# Tasks

Task index plus a concise structured entry per task under "Implementation tasks" (playbook Section 24 fields; see `docs/agents/issue-tracker.md`). Each implementation task needs: acceptance criteria, owned files, model/effort, verification commands (or an instruction to create them), and its next review gate. `handoffs/` is only for Section 19 external/substantial transfers.

| ID | Start Here step | Status | Summary |
| --- | --- | --- | --- |
| S-05 | 5 | Done (`7a0f155`) | Git, uv/Python 3.11 env, locked deps, shared state files, import check |
| S-06 | 6 | Done (`4b3cab6`); Matt skill configuration committed locally | Install selected project-local skills per playbook Section 22.2; record in `docs/TOOLING.md`; configure via `/setup-matt-pocock-skills` |
| S-07 | 7 | Next | Requirements interview → `docs/PRD.md`, `docs/SPEC.md`, first implementation task entries |

## Implementation tasks

Pending Step 7. The first implementation slice (seeded faulty/clean/unsupported fixtures, group-overlap and fit-provenance checks, evidence JSON, tests) is defined in the handoff but has no accepted task entry yet. Entries will be added below with the Section 24 fields.
