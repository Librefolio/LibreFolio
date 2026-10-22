---
name: wiki-ingest
description: "Use this skill (historian agent) when a new source needs to be processed and integrated into the LibreFolio devWiki. Sources can be: completed plans from developer_journal/, external articles, journal entries, architecture notes. Produces: source summary page, updated entity/decision/concept/problem pages, updated index.md and log.md. Triggers graphify --update at the end to keep the knowledge graph current."
---

# Wiki Ingest Skill

> Integrates a new source into the `LibreFolio_devWiki/` persistent knowledge layer.
> **Always read `LibreFolio_devWiki/SCHEMA.md` before first use in a session.**
> **Runs graphify `--update` at end** so new pages are immediately queryable from the graph.

## Preconditions

- Wiki root: `LibreFolio_devWiki/`
- Schema: `LibreFolio_devWiki/SCHEMA.md`
- Index: `LibreFolio_devWiki/index.md`
- Log: `LibreFolio_devWiki/log.md`
- Registry: `LibreFolio_devWiki/raw/ingest-registry.md`
- Graph: `LibreFolio_devWiki/graphify-out/graph.json`

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

### Step 1 — Graph Check (Pre-Ingest Context)

Before reading the source, query the graph to see what's already known about the topic:

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
import json
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')
terms = 'TOPIC_KEYWORDS'.lower().split()

scored = [(sum(1 for t in terms if t in G.nodes[n].get('label','').lower()), n) for n in G.nodes()]
top = sorted(scored, reverse=True)[:5]
for score, nid in top:
    if score > 0:
        print(f'  [{score}] {G.nodes[nid].get(\"label\", nid)} — {G.nodes[nid].get(\"source_file\",\"\")}')
"
```

This shows existing graph coverage — helps identify which wiki pages to update vs create.

### Step 2 — Read and Discuss

Read the source document completely.
Identify: decisions, entities, problems, patterns, concepts it contains.
Briefly discuss key takeaways with the user if the source is complex.

### Step 3 — Record Git Hash in Registry

Before writing any wiki page, record the source in `raw/ingest-registry.md`.

```bash
git log -1 --format="%H" -- path/to/source.md
```

If not git-tracked (external file in `raw/`), record `untracked`.

Append a row to `raw/ingest-registry.md`:
```markdown
| `path/to/source.md` | `abc1234` | YYYY-MM-DD | [[sources/slug]] |
```

### Step 4 — Write Source Summary

Create `wiki/sources/{slug}.md` using the source page format from `SCHEMA.md`:
- 3-5 sentence summary
- Bullet list of key takeaways
- List of wiki pages created/updated

### Step 5 — Create or Update Domain Pages

For each significant piece of knowledge extracted:

| Content type | Target dir | Action |
|-------------|-----------|--------|
| Architectural choice | `wiki/decisions/` | Create or update |
| Component / service / module | `wiki/entities/` | Create or update History section |
| Pattern / approach / principle | `wiki/concepts/` | Create or update |
| Bug / issue / gotcha | `wiki/problems/` | Create problem page |

Cross-referencing rule: every new page links to related pages via `[[page-slug]]`.
Every page MUST have a `## Source files` table.

### Step 6 — Update index.md

Add a row to the appropriate section for each new page.
Update rows for pages that changed substantially.

### Step 7 — Append to log.md

```markdown
## [YYYY-MM-DD] ingest | {source title}
Source: `path/to/source.md` @ git:`abc1234`.
{1-2 sentence summary of what was extracted.}
Created: [[sources/slug]], [[decisions/foo]].
Updated: [[entities/bar]], [[concepts/baz]].
```

### Step 8 — Run graphify --update

After creating all new pages, update the knowledge graph:

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
from graphify.detect import detect_incremental
from pathlib import Path
import json
result = detect_incremental(Path('corpus/'))
new_total = result.get('new_total', 0)
print(f'Changed files: {new_total}')
"
```

If `new_total > 0`, run the graphify `--update` pipeline:
- Steps 3B-3C (re-extract only changed files, merge with cache)
- Step 4 (rebuild graph with new nodes, recluster)
- Step 5 (re-label communities)
- Step 6 (regenerate graph.html)
- Step 9 (save manifest, cleanup)

This ensures newly ingested wiki pages become part of the graph's queryable knowledge.

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
- [ ] All new pages have `## Source files` table
- [ ] `index.md` updated
- [ ] `log.md` entry appended
- [ ] No orphan pages (every new page linked from at least one other)
- [ ] `graphify --update` run (or queued for end of session)
