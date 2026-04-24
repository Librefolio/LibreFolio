---
name: wiki-query
description: "Use this skill (historian agent) when the user asks a question that should be answered from the accumulated devWiki knowledge base. Searches index.md, reads relevant pages, synthesizes a cited answer, and optionally files the answer back as a new wiki page."
---

# Wiki Query Skill

> Answers questions by reading from `LibreFolio_devWiki/` and synthesizing across pages.
> Good answers are filed back into the wiki — explorations compound knowledge.

## When to Use

- "Why did we choose X?"
- "What's the history of [component]?"
- "Have we had this problem before?"
- "What patterns do we use for [topic]?"
- "Summarize what we know about [topic]"
- "Compare approach A vs B based on what we've learned"

## Query Workflow

### Step 1 — Read index.md
Read `LibreFolio_devWiki/index.md` completely.
Identify which sections and pages are potentially relevant to the question.

### Step 2 — Check for Drift (Optional but Recommended)
For pages citing sources, check `raw/ingest-registry.md` to see if those sources have changed since ingest:
```bash
git diff {hash} HEAD -- {source-path}
```
If significant drift exists, note it in the answer: "This may be outdated — source changed since ingest."

### Step 3 — Read Relevant Pages
Read the 2-5 most relevant pages. Follow `[[links]]` up to 2 levels deep.
Prioritize: problems → decisions → entities → concepts.

### Step 4 — Synthesize with Citations
```
The FIFO calculation happens at runtime (see [[concepts/fifo-at-runtime]]) because...
This was decided in phase 6 (see [[decisions/fifo-runtime-decision]]).
```

### Step 5 — Choose Output Format

| Question type | Format |
|--------------|--------|
| Factual / historical | Prose with inline citations |
| Comparison | Markdown table |
| Architecture overview | Mermaid diagram + prose |
| How-to | Numbered list |

### Step 6 — File Back (if non-trivial)
If the answer required synthesizing 3+ pages or revealed a new connection, file it back:
1. Determine the right category (concept, decision, entity, or synthesis page)
2. Create `wiki/{category}/{slug}.md` using the appropriate template from `SCHEMA.md`
3. Update `index.md`
4. Append to `log.md`:
   ```markdown
   ## [YYYY-MM-DD] query | {question summary}
   Answer from: [[page1]], [[page2]].
   Filed as: [[concepts/new-page]] (if applicable).
   ```

## When to File Back

**Always file back if**: answer required synthesizing 3+ pages, revealed a new connection, corrects an existing page.
**Skip if**: single direct fact from one page, purely exploratory question.

## Handling "Not Found"

If the wiki doesn't have coverage:
1. Say so clearly: "The wiki doesn't have coverage of X yet."
2. Suggest which source to ingest: "Consider ingesting `developer_journal/RoadmapV3/...`"
3. Optionally fall back to codebase search and note the result isn't yet in the wiki.
