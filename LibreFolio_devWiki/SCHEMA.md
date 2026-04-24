# LibreFolio devWiki — Schema & Conventions

> This document is the authoritative configuration for the LLM wiki layer.
> The main coding agent and the historian agent both read it to understand how to operate.

## Purpose

This wiki is the **persistent knowledge layer** for the LibreFolio development process.
It is NOT the source of truth (the code is) and NOT the user documentation (mkdocs is).
It is the **accumulated understanding** that compounds across sessions:
decisions, patterns, problems solved, architectural rationale.

## Relationship to Other Layers

```
Source code          → immutable truth
developer_journal/   → working plans during active sessions (short-lived, operational)
devWiki/             → persistent accumulated knowledge (this layer, long-lived)
mkdocs_src/          → formal human documentation (final, polished)
```

A plan in `developer_journal/` becomes a wiki page once the work is done and the insight is worth keeping.
A wiki page eventually feeds mkdocs when the topic matures into stable documentation.

## Directory Structure

```
LibreFolio_devWiki/
├── SCHEMA.md              # This file — conventions and workflows
├── index.md               # Master catalog — updated on every ingest
├── log.md                 # Chronological append-only log
├── raw/                   # Source tracking layer (NOT the raw sources themselves)
│   ├── ingest-registry.md # Git-hash snapshot index for all ingested sources
│   └── (optional: clipped external articles not tracked by git)
└── wiki/                  # LLM-generated pages (LLM writes and maintains)
    ├── decisions/         # Architectural and technical decisions
    ├── entities/          # Components, services, modules, APIs, providers
    ├── concepts/          # Patterns, approaches, principles, techniques
    ├── problems/          # Problems encountered and solved
    └── sources/           # Summaries of ingested sources (plans, articles, etc.)
```

### The raw/ Layer — Source Tracking with Git Hashes

The `raw/` directory serves a specific purpose: **tracking which version of each source was ingested**.

The actual sources (plans, code, knowledge base files) live in their natural locations:
- `LibreFolio_developer_journal/` — development plans
- `backend/`, `frontend/` — the codebase itself
- `LibreFolio_developer_journal/knowledge_base/` — accumulated notes

**Session isolation reality**: the historian agent runs while the rest of the project is frozen.
But between sessions, source files can change significantly (plans get completed, code evolves, notes get updated).

`raw/ingest-registry.md` records the git hash of each source file **at the moment it was ingested**.
This enables drift detection in future sessions:

```bash
# Check if a source has changed since it was ingested
git diff {hash_at_ingest} HEAD -- path/to/source.md
```

If the diff is significant → the wiki page derived from that source may be stale → consider re-ingesting.

External files not tracked by git (PDFs, clipped articles) can live in `raw/` directly,
with hash recorded as `untracked` in the registry.

## Page Formats

### Decision page (`wiki/decisions/`)

```markdown
---
title: "Short decision title"
category: decision
status: resolved | open | superseded
date: YYYY-MM-DD
tags: [backend, frontend, db, auth, ...]
related: [other-page, another-page]
---

# Decision: [Title]

## Context
What problem or need triggered this decision.

## Options Considered
1. **Option A** — description, pros/cons
2. **Option B** — description, pros/cons

## Decision
What was chosen and why.

## Consequences
What changed, what was gained, what was traded off.

## Links
- [[related-page]]
- Source: `developer_journal/RoadmapVX/plan-name.md`
```

### Entity page (`wiki/entities/`)

```markdown
---
title: "Entity name"
category: entity
type: service | component | module | api | provider | store
tags: [...]
related: [...]
---

# [Entity Name]

## Role
One-paragraph description of what this entity does.

## Location
`backend/app/services/foo.py` or `frontend/src/lib/components/Foo.svelte`

## Key Interfaces
(methods, props, events, API endpoints)

## Design Notes
Patterns used, important constraints, known gotchas.

## History
Notable changes or decisions that shaped this entity.
```

### Problem page (`wiki/problems/`)

```markdown
---
title: "Problem short title"
category: problem
status: resolved | workaround | accepted | recurs
date: YYYY-MM-DD
tags: [build, async, db, frontend, ...]
related: [...]
---

# Problem: [Title]

## Symptom
What went wrong / what was observed.

## Root Cause
Why it happened.

## Solution
What fixed it (or workaround if permanent fix wasn't possible).

## Prevention
How to avoid this in the future.

## Impact
Dev time lost, user-facing consequences.
```

### Source summary page (`wiki/sources/`)

```markdown
---
title: "Source title"
category: source
source_type: plan | article | external_doc | meeting | journal_entry
date_ingested: YYYY-MM-DD
original_path: developer_journal/RoadmapVX/plan-name.md
tags: [...]
related: [...]
---

# Source: [Title]

## Summary
3-5 sentence summary of the key content.

## Key Takeaways
- Bullet 1
- Bullet 2

## Wiki Pages Updated
- [[decision/foo]] — reason
- [[entity/bar]] — reason
```

### Concept page (`wiki/concepts/`)

```markdown
---
title: "Concept name"
category: concept
tags: [...]
related: [...]
---

# Concept: [Title]

## Definition
What this concept means in the LibreFolio context.

## Where It Applies
Which parts of the codebase embody this concept.

## Examples
Code snippets or references.
```

## index.md Conventions

`index.md` is the LLM's navigation map. Format:

```markdown
## Decisions
| Page | Summary | Date | Tags |
|------|---------|------|------|
| [[decisions/foo]] | Why we chose X | 2025-01-10 | backend, db |

## Entities
...

## Concepts
...

## Problems
...

## Sources
...
```

Updated on every ingest and every time a new page is created.

## log.md Conventions

Append-only. Every entry starts with:
```
## [YYYY-MM-DD] {operation} | {title}
```

Operations: `ingest`, `query`, `lint`, `file`, `update`

Example:
```markdown
## [2026-04-24] ingest | plan-phase07-transaction-Part1
Ingested from developer_journal/RoadmapV4_UI/. Created source summary page.
Updated: [[decisions/transaction-model]], [[entities/transaction-service]].

## [2026-04-24] query | What drives the FIFO cost calculation?
Synthesized answer from 3 pages. Filed as [[concepts/fifo-runtime]].
```

Parseable: `grep "^## \[" log.md | tail -10` gives last 10 entries.

## Workflows

### Ingest Workflow (historian agent)

1. Get git hash of source: `git log -1 --format="%H" -- path/to/source.md`
2. Read the source
3. Discuss key takeaways with user (optional)
4. Record in `raw/ingest-registry.md` (path + hash + date + wiki page link)
5. Write source summary in `wiki/sources/`
6. Update/create entity, concept, decision, problem pages as needed
7. Update `index.md`
8. Append entry to `log.md`

### Query Workflow (historian agent)

1. Read `index.md` to find relevant pages
2. Optionally check `raw/ingest-registry.md` for drift on cited sources
3. Read the relevant pages
4. Synthesize answer with citations
5. Optionally file the answer back as a new wiki page

### Lint Workflow (historian agent)

Check for: orphan pages, contradictions, drift (via `raw/ingest-registry.md` + `git diff`), stale claims, missing cross-refs, concept debt.

### Search Workflow (main agent, before coding)
See skill: `wiki-search`

1. Read `index.md`
2. Identify pages relevant to the current task
3. Read them and return a context summary

### File Workflow (main agent, during/after coding)
See skill: `wiki-file`

1. Determine category (decision, entity, concept, problem)
2. Create or update the appropriate page
3. Update cross-references
4. Update `index.md` and `log.md`
