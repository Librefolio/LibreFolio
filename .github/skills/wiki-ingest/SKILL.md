---
name: wiki-ingest
description: "Use this skill (historian agent) when a new source needs to be processed and integrated into the LibreFolio devWiki. Sources can be: completed plans from developer_journal/, external articles, journal entries, architecture notes, or any document worth preserving. Produces: source summary page, updated entity/decision/concept/problem pages, updated index.md and log.md."
---

# Wiki Ingest Skill

> Integrates a new source into the `LibreFolio_devWiki/` persistent knowledge layer.
> Always read `LibreFolio_devWiki/SCHEMA.md` before first use in a session.

## Preconditions

- Wiki root: `LibreFolio_devWiki/`
- Schema: `LibreFolio_devWiki/SCHEMA.md`
- Index: `LibreFolio_devWiki/index.md`
- Log: `LibreFolio_devWiki/log.md`
- Registry: `LibreFolio_devWiki/raw/ingest-registry.md`

## Input

The source to ingest. Can be:
| Type | Typical Path |
|------|-------------|
| Completed plan | `LibreFolio_developer_journal/RoadmapVX/plan-*.md` |
| Archived phase | `LibreFolio_developer_journal/RoadmapV4_UI/phases/` |
| Knowledge base file | `LibreFolio_developer_journal/knowledge_base/*.md` |
| External article | `LibreFolio_devWiki/raw/` (already clipped) |
| Inline text | Provided directly in conversation |

## Ingest Workflow

### Step 1 — Read and Discuss
Read the source document completely.
Identify: decisions, entities, problems, patterns, concepts it contains.
Briefly discuss key takeaways with the user if the source is complex.

### Step 2 — Record Git Hash in Registry
Before writing any wiki page, record the source in `raw/ingest-registry.md`.

Get the current git hash of the source file:
```bash
git log -1 --format="%H" -- path/to/source.md
```
If not git-tracked (external file in `raw/`), record `untracked`.

Append a row to `raw/ingest-registry.md`:
```markdown
| `path/to/source.md` | `abc1234` | YYYY-MM-DD | [[sources/slug]] |
```

This creates a baseline. In future sessions, to check if a source has changed:
```bash
git diff abc1234 HEAD -- path/to/source.md
```

### Step 3 — Write Source Summary
Create `wiki/sources/{slug}.md` using the source page format from `SCHEMA.md`:
- 3-5 sentence summary
- Bullet list of key takeaways
- List of wiki pages created/updated

### Step 4 — Create or Update Domain Pages
For each significant piece of knowledge extracted:

| Content type | Target dir | Action |
|-------------|-----------|--------|
| Architectural choice | `wiki/decisions/` | Create or update |
| Component / service / module | `wiki/entities/` | Create or update History section |
| Pattern / approach / principle | `wiki/concepts/` | Create or update |
| Bug / issue / gotcha | `wiki/problems/` | Create problem page |

Cross-referencing rule: every new page links to related pages via `[[page-slug]]`.

### Step 5 — Update index.md
Add a row to the appropriate section for each new page.
Update rows for pages that changed substantially.

### Step 6 — Append to log.md
```markdown
## [YYYY-MM-DD] ingest | {source title}
Source: `path/to/source.md` @ git:`abc1234`.
{1-2 sentence summary of what was extracted.}
Created: [[sources/slug]], [[decisions/foo]].
Updated: [[entities/bar]], [[concepts/baz]].
```

## Naming Conventions
- Slugs: lowercase-kebab-case, `.md` extension
- Decision pages: `{topic}-decision.md`
- Entity pages: `{entity-name}.md`
- Problem pages: `{symptom-keyword}.md`
- Source pages: match the source filename when possible

## Quality Checks
- [ ] Registry row added to `raw/ingest-registry.md` with git hash
- [ ] Source summary page created in `wiki/sources/`
- [ ] Decisions, entities, concepts, problems captured
- [ ] All new pages have YAML frontmatter (title, category, tags, related)
- [ ] `index.md` updated
- [ ] `log.md` entry appended
- [ ] No orphan pages (every new page linked from at least one other)
