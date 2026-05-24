---
name: wiki-file
description: "Use this skill when the main dev agent needs to preserve a discovery, decision, or solved problem into the devWiki during or after a coding session. Prevents valuable knowledge from disappearing into chat history. Use after any session where something non-obvious was learned. Runs graphify --update after filing to keep the graph current."
---

# Wiki File Skill

> Files a discovery, decision, or solved problem into `LibreFolio_devWiki/`.
> Use at the END of a coding session or whenever something worth remembering is learned.
> **Always triggers a graphify `--update` pass** so the new page becomes queryable immediately.

## When to Use

- A bug was solved that had a non-obvious root cause
- An architectural decision was made (even informally)
- A pattern was established that others (or future-you) should follow
- A gotcha was discovered in a library, API, or framework
- A plan was completed and its insights should survive as wiki pages
- The user says "remember this" / "file this" / "we should document this"

## Filing Workflow

### Step 1 — Classify the Knowledge

| What happened | Category | Target dir |
|--------------|----------|-----------|
| Architectural or tech choice | Decision | `wiki/decisions/` |
| Bug fixed / issue resolved | Problem | `wiki/problems/` |
| Pattern / convention established | Concept | `wiki/concepts/` |
| Component / service described | Entity | `wiki/entities/` |
| External source processed | Source | `wiki/sources/` |

When in doubt: if it's about *why*, it's a decision. If it's about *what went wrong*, it's a problem. If it's about *how we do things*, it's a concept.

### Step 2 — Check for an Existing Page
Search `index.md` for the topic. If a page already exists:
- Add to the relevant section rather than creating a duplicate
- Update the `related` frontmatter if new connections are discovered
- Update the index row if the summary changed significantly

### Step 3 — Create or Update the Page
Use the appropriate template from `SCHEMA.md`.

**Minimum viable page** (when in a hurry):
```markdown
---
title: "Short title"
category: problem | decision | concept | entity
date: YYYY-MM-DD
tags: [relevant, tags]
---

# [Title]

## Summary
2-4 sentences explaining what this is and why it matters.

## Details
The actual content — code snippet, root cause, decision rationale, etc.

## Source files
| Role | Path |
|------|------|
| Implementation | `backend/app/...` or `frontend/src/...` |
```

**Cross-referencing**: add `[[links]]` to related pages. Every page must have a `## Source files` section.

### Step 4 — Update index.md
Add a row in the correct section. Format:
```markdown
| [[category/slug]] | One-line summary | YYYY-MM-DD | tag1, tag2 |
```

### Step 5 — Append to log.md
```markdown
## [YYYY-MM-DD] file | {page title}
{One sentence describing what was filed and why.}
Filed: [[category/slug]].
```

### Step 6 — Run graphify --update

After filing, update the knowledge graph so the new page becomes immediately queryable:

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
from graphify.detect import detect_incremental
from pathlib import Path
import json
result = detect_incremental(Path('corpus/'))
new_total = result.get('new_total', 0)
deleted = list(result.get('deleted_files', []))
if new_total == 0 and not deleted:
    print('No changes since last graph build — skipping update')
else:
    print(f'{new_total} changed files, {len(deleted)} deleted — run graphify corpus/ --update')
"
```

If new files are detected, run the full `--update` pipeline (Steps 3B-3C-4-5-6-9 from the graphify skill).

## Fast-File Mode

When the insight is simple and you're in the middle of a task, use fast-file:
1. Create the minimum viable page (frontmatter + 2-4 sentences + source files table)
2. Add one index row
3. Add one log entry
4. Queue a graphify `--update` for the end of the session

Don't let filing interrupt coding flow. A rough page is better than no page.

## Filing After a Session

At the end of a dev session, review what was learned:
1. Ask: "What did we figure out today that wasn't known before?"
2. For each item: quick classify → fast-file → done
3. Consider: should any completed plan be ingested via `wiki-ingest`?
4. Run `graphify corpus/ --update` once to incorporate all new pages

## Examples

```
Discovered: SQLModel's Decimal columns need explicit Numeric(18,6) to avoid precision loss.
→ File as: wiki/problems/sqlmodel-decimal-precision.md
→ Tags: [db, sqlmodel, decimal]

Decided: All provider calls go through _run_provider_in_thread(), no exceptions.
→ File as: wiki/decisions/provider-thread-isolation.md
→ Tags: [backend, providers, async]

Pattern established: EditBuffer<T> for any bidirectional inline editor.
→ File as: wiki/concepts/edit-buffer-pattern.md
→ Tags: [frontend, svelte, pattern]
```
