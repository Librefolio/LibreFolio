---
name: wiki-query
description: "Use this skill (historian agent) when the user asks a question that should be answered from the accumulated devWiki knowledge base. Uses graphify BFS/DFS graph traversal as primary lookup, supplemented by direct wiki page reads. Synthesizes a cited answer and optionally files it back as a new wiki page."
---

# Wiki Query Skill

> Answers questions by traversing `LibreFolio_devWiki/graphify-out/graph.json` and reading source wiki pages.
> Uses graphify BFS/DFS for efficient retrieval. Good answers are filed back — explorations compound.

## When to Use

- "Why did we choose X?"
- "What's the history of [component]?"
- "Have we had this problem before?"
- "What patterns do we use for [topic]?"
- "Summarize what we know about [topic]"
- "Compare approach A vs B based on what we've learned"
- "What features are related to [concept]?"

## Query Workflow

### Step 1 — Graph Traversal (Primary)

Run from `LibreFolio_devWiki/`:

**BFS query (broad context — default for most questions):**
```bash
cd LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
import json, sys
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')

question = 'QUESTION'
terms = [t.lower() for t in question.split() if len(t) > 3]

scored = []
for nid, ndata in G.nodes(data=True):
    label = ndata.get('label', '').lower()
    score = sum(1 for t in terms if t in label)
    if score > 0:
        scored.append((score, nid))
scored.sort(reverse=True)
start_nodes = [nid for _, nid in scored[:3]]

if not start_nodes:
    print('No matching nodes'); sys.exit(0)

subgraph_nodes = set(start_nodes)
frontier = set(start_nodes)
for _ in range(3):
    next_f = set()
    for n in frontier:
        for nb in G.neighbors(n):
            if nb not in subgraph_nodes:
                next_f.add(nb)
    subgraph_nodes.update(next_f)
    frontier = next_f

print(f'BFS: {len(subgraph_nodes)} nodes from {[G.nodes[n].get(\"label\",n) for n in start_nodes]}')
for nid in sorted(subgraph_nodes, key=lambda n: -sum(1 for t in terms if t in G.nodes[n].get('label','').lower()))[:20]:
    d = G.nodes[nid]
    print(f'  {d.get(\"label\", nid)} [{d.get(\"file_type\",\"\")}] — {d.get(\"source_file\",\"\")}')
"
```

**DFS query (trace a specific path):**
Same as BFS but replace the BFS loop with:
```python
visited = set(); stack = [(n, 0) for n in reversed(start_nodes)]
while stack:
    node, depth = stack.pop()
    if node in visited or depth > 6: continue
    visited.add(node); subgraph_nodes.add(node)
    for nb in G.neighbors(node):
        if nb not in visited: stack.append((nb, depth+1))
```

**Shortest path between two concepts:**
```bash
cd LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
import json, sys
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')

def find_node(term):
    term = term.lower()
    scored = sorted([(sum(1 for w in term.split() if w in G.nodes[n].get('label','').lower()), n) for n in G.nodes()], reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else None

src = find_node('NODE_A')
tgt = find_node('NODE_B')
if not src or not tgt: print('Nodes not found'); sys.exit(0)

try:
    path = nx.shortest_path(G, src, tgt)
    for i, nid in enumerate(path):
        label = G.nodes[nid].get('label', nid)
        if i < len(path) - 1:
            edge = G[nid][path[i+1]]
            print(f'  {label} --{edge.get(\"relation\",\"\")}[{edge.get(\"confidence\",\"\")}]--> ')
        else:
            print(f'  {label}')
except nx.NetworkXNoPath:
    print('No path found')
"
```

### Step 2 — Read Source Pages (Targeted)

The graph returns `source_file` paths for each node. Read only the 2-4 most relevant files.
Do NOT read all pages — the graph already pre-filtered the relevant ones.

### Step 3 — Check for Drift (Optional)

For pages citing plans that may have changed:
```bash
git --no-pager diff {hash} HEAD -- {source-path}
```
Get hash from `raw/ingest-registry.md`. If significant drift, note: "This may be outdated."

### Step 4 — Synthesize with Citations

```
The FIFO calculation happens at runtime (see [[concepts/fifo-at-runtime]]) because...
This was decided in phase 6 (see [[decisions/fifo-runtime-decision]]).
Graph: FX Rate Sync --enables--> FIFO Cost Calculation [INFERRED, 0.82]
```

Always cite: wiki page slug, source_file from graph, edge relation.

### Step 5 — Choose Output Format

| Question type | Format |
|--------------|--------|
| Factual / historical | Prose with inline citations |
| Comparison | Markdown table |
| Architecture overview | Mermaid diagram + prose |
| How-to | Numbered list |
| Feature relationships | Graph traversal output + prose |

### Step 6 — File Back (if non-trivial)

If the answer required synthesizing 3+ sources or revealed a new connection:
1. Determine category (concept, decision, entity, synthesis)
2. Create `wiki/{category}/{slug}.md` using template from `SCHEMA.md`
3. Update `index.md`
4. Append to `log.md`:
   ```markdown
   ## [YYYY-MM-DD] query | {question summary}
   Answer from graph traversal + [[page1]], [[page2]].
   Filed as: [[concepts/new-page]] (if applicable).
   ```

## When to File Back

**Always file back if**: required synthesizing 3+ sources, revealed a new connection, corrects an existing page.
**Skip if**: single direct fact, purely exploratory.

## Handling "Not Found"

If the graph returns no matching nodes AND index.md has no coverage:
1. Say clearly: "The wiki doesn't have coverage of X yet."
2. Suggest what to ingest: "Consider ingesting `developer_journal/RoadmapV4_UI/...`"
3. Optionally fall back to codebase search, noting the result isn't in the wiki yet.
