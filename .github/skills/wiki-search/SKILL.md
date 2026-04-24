---
name: wiki-search
description: "Use this skill when the main dev agent needs to enrich its context before starting a coding task. Searches the devWiki for relevant accumulated knowledge — decisions, patterns, known problems, entity documentation — so the agent doesn't rediscover what's already been learned."
---

# Wiki Search Skill

> Quick context enrichment from `LibreFolio_devWiki/` before coding.
> Use this at the START of a task to avoid re-deriving known knowledge.

## When to Use

- Before starting work on a feature/module that has prior history
- When approaching code that has known gotchas or past problems
- When a task touches architectural decisions (FIFO, provider pattern, async I/O, etc.)
- When the user says "remember when we..." or "as we discussed..."
- Whenever you want to check if a decision has already been made

## Search Workflow

### Step 1 — Read index.md
Read `LibreFolio_devWiki/index.md`.
Identify rows relevant to the current task by matching:
- Task keywords vs. page titles and summaries
- Affected system areas (backend, frontend, db, specific service name, etc.)

### Step 2 — Read Relevant Pages
Read the 2-5 most relevant pages. Prioritize:
1. **Problems** — don't repeat known mistakes
2. **Decisions** — don't re-debate settled choices
3. **Entities** — understand the design intent before modifying
4. **Concepts** — understand the patterns in use

**Time limit**: spend no more than 2-3 reads. If nothing useful is found in 3 pages, stop.

### Step 3 — Summarize Context
Provide a brief "wiki context" block before proceeding with the task:

```markdown
**Wiki context for this task:**
- [[problems/event-loop-blocking]]: yfinance calls must be wrapped in `asyncio.to_thread()`
- [[decisions/fifo-runtime-decision]]: FIFO is computed on-demand, never persisted
- [[entities/asset-service]]: providers run in isolated threads via `_run_provider_in_thread()`
```

Then proceed with the task informed by this context.

### Step 4 — Note Gaps (Optional)
If the wiki should have coverage of something but doesn't, note it briefly:
```
Note: No wiki page found for [topic]. Consider filing one after this task (use wiki-file skill).
```

## What NOT to Do

- Don't do a full wiki audit — this is a quick lookup, not a lint pass
- Don't read more than 5 pages — if you need more, the task is probably better served by `wiki-query`
- Don't block the coding task waiting for perfect wiki coverage

## Output Format

Keep it short. The goal is 3-6 bullet points of context that directly affect the current task.
If nothing relevant is found, say: "Wiki check: no relevant pages found for [topic]" and proceed.
