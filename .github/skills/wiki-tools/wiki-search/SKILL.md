---
name: wiki-search
description: "Use this skill to quickly search the devWiki for relevant accumulated knowledge — decisions, patterns, known problems, feature documentation — so you don't rediscover what's already been learned. Uses graphify graph query as primary lookup. Useful both before a coding task (context enrichment) and during a historical query (fast lookup without a full wiki-query pass)."
---

# Wiki Search Skill

> Quick context lookup from `LibreFolio_devWiki/` via graphify graph query.
> Use when you need targeted knowledge retrieval — not a full audit.

## When to Use

- Before starting work on a feature/module that has prior history
- When approaching code that has known gotchas or past problems
- When a task touches architectural decisions (FIFO, provider pattern, async I/O, etc.)
- When the user says "remember when we..." or "as we discussed..."
- Whenever you want to check if a decision has already been made
- When the historian needs a fast answer and a full `wiki-query` pass would be overkill

## Search Workflow (graphify-first)

### Step 1 — Query the Graph (Primary)

Run from `LibreFolio_devWiki/`:

```bash
cd LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
import sys, json
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')
question = 'QUERY_TERMS'
terms = [t.lower() for t in question.split() if len(t) > 3]

scored = []
for nid, ndata in G.nodes(data=True):
    label = ndata.get('label', '').lower()
    score = sum(1 for t in terms if t in label)
    if score > 0:
        scored.append((score, nid, ndata))
scored.sort(reverse=True)

for score, nid, ndata in scored[:8]:
    print(f'[{score}] {ndata.get(\"label\", nid)} — {ndata.get(\"source_file\", \"\")}')
    for neighbor in list(G.neighbors(nid))[:3]:
        edge = G[nid][neighbor]
        print(f'  → {G.nodes[neighbor].get(\"label\", neighbor)} [{edge.get(\"relation\", \"\")}]')
"
```

Replace `QUERY_TERMS` with the topic keywords (e.g. `"FIFO cost calculation"`, `"async io blocking"`, `"FX provider fallback"`).

This returns matching nodes with their top neighbors — the key relationships already extracted from wiki pages and plans.

### Step 2 — Explain a Specific Concept (Optional)

If Step 1 identifies a key node, get its full neighborhood:

```bash
cd LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
import json
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')
term = 'NODE_LABEL'
term_lower = term.lower()

scored = sorted([(sum(1 for w in term_lower.split() if w in G.nodes[n].get('label','').lower()), n) for n in G.nodes()], reverse=True)
if not scored or scored[0][0] == 0:
    print('Not found')
else:
    nid = scored[0][1]
    d = G.nodes[nid]
    print(f'NODE: {d.get(\"label\", nid)} ({d.get(\"source_file\",\"\")})')
    for neighbor in G.neighbors(nid):
        edge = G[nid][neighbor]
        print(f'  --{edge.get(\"relation\",\"\")}[{edge.get(\"confidence\",\"\")}]--> {G.nodes[neighbor].get(\"label\", neighbor)}')
"
```

### Step 3 — Read Source Files (Targeted)

The graph returns `source_file` paths. Read only the 1-3 most relevant files directly.
Every wiki page has a `## Source files` section linking to actual codebase paths — use those for navigation.

### Step 4 — Summarize Context

Provide a brief "wiki context" block:

```markdown
**Wiki context for this task:**
- [[problems/event-loop-blocking]]: yfinance calls must be wrapped in `asyncio.to_thread()`
- [[decisions/fifo-runtime-decision]]: FIFO is computed on-demand, never persisted
- [[entities/asset-service]]: providers run in isolated threads via `_run_provider_in_thread()`
```

### Step 5 — Note Gaps (Optional)
If the graph returns no relevant nodes, fall back to `index.md`:
```
Note: No graph nodes found for [topic]. Checked index.md: no pages found either.
Consider filing a wiki page after this task (use wiki-file skill).
```

## What NOT to Do

- Don't scan index.md manually if graphify returns useful results — the graph is faster
- Don't read more than 3 source files — if you need more, use `wiki-query`
- Don't block the coding task waiting for perfect wiki coverage

## Output Format

Keep it short. The goal is 3-6 bullet points of context that directly affect the current task.
If nothing relevant is found: "Wiki check: no graph nodes found for [topic]" and proceed.
