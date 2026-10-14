# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase. Layout: **single-context**.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root.
- **`DECISIONS.md`** at the repo root: the decision index. Routine decisions live here directly.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in.

If `GLOSSARY.md` or `docs/adr/` don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs`) creates them lazily when terms or decisions actually get resolved. Never create an empty glossary or a placeholder ADR.

## File structure

```
/
├── GLOSSARY.md        (created when the first term is resolved)
├── DECISIONS.md       (decision index; dated entries)
├── docs/adr/          (created with the first ADR)
│   └── 0001-<slug>.md
└── src/
```

## Decisions: DECISIONS.md vs ADRs

- **Routine decisions** go in `DECISIONS.md` as dated entries with a reason.
- **ADRs** (`docs/adr/NNNN-slug.md`, format per the domain-modeling skill's `ADR-FORMAT.md`) are only for consequential architectural decisions that pass that skill's test: hard to reverse, surprising without context, and the result of a real trade-off.
- Every ADR gets a dated one-line pointer in `DECISIONS.md` (for example, `- **<title>:** see docs/adr/0001-<slug>.md`), so `DECISIONS.md` stays the single index.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag decision conflicts

If your output contradicts an existing ADR or a `DECISIONS.md` entry, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_
