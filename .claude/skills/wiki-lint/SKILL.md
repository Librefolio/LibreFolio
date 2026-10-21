---
name: wiki-lint
description: "Use this skill (historian agent) when the user wants to health-check the devWiki. Combines graphify GRAPH_REPORT analysis with traditional wiki checks: orphan pages, drift, contradictions, missing cross-refs, concept debt, index drift. Produces a prioritized repair list."
---

# Wiki Lint Skill

> Periodic health check of `LibreFolio_devWiki/`.
> Uses **graphify GRAPH_REPORT** as primary analysis + traditional file-based checks.
> Run after 5-10 ingests, at phase boundaries, or when re-entering after a long break.

## Lint Workflow

### Step 1 — Read GRAPH_REPORT (Graphify Analysis)

```bash
cat /Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_devWiki/graphify-out/GRAPH_REPORT.md
```

Extract from the report:
- **God nodes** — highest-betweenness nodes: are they well-documented wiki pages?
- **Surprising connections** — INFERRED edges that may be wrong or reveal missing links
- **Suggested questions** — cross-community bridges that may indicate missing concept pages
- **Weakly-connected nodes** — possible documentation gaps or orphan concepts

### Step 2 — Check Graph Coverage vs Wiki Pages

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
import json
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')

# Find nodes with high degree but no wiki page (only from roadmap/mkdocs)
high_degree = [(G.degree(n), n, G.nodes[n]) for n in G.nodes() if G.degree(n) >= 5]
high_degree.sort(reverse=True)
print('High-degree nodes without wiki pages:')
for deg, nid, d in high_degree[:20]:
    src = d.get('source_file', '')
    if 'wiki/' not in src:
        print(f'  [{deg}] {d.get(\"label\", nid)} — {src}')
"
```

High-degree non-wiki nodes are candidates for new wiki pages.

### Step 3 — Traditional File Checks

#### Check 1 — Orphan Pages
Pages with no inbound `[[link]]` from any other wiki page.
```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_devWiki
for f in wiki/**/*.md; do
  slug=$(basename "$f" .md)
  count=$(grep -rl "\[\[$slug\]\]" wiki/ 2>/dev/null | wc -l)
  if [ "$count" -eq 0 ]; then echo "ORPHAN: $f"; fi
done
```

#### Check 2 — Drift Detection
Read `raw/ingest-registry.md`. For each row:
```bash
git --no-pager diff {hash} HEAD -- {source-path}
```
Flag sources with >5 lines changed as "possibly stale — re-ingest recommended".

#### Check 3 — Index Drift
Files in `wiki/` not listed in `index.md`, or index rows pointing to non-existent files:
```bash
# Files not in index
for f in wiki/**/*.md; do
  slug=$(basename "$f" .md)
  grep -q "$slug" index.md || echo "NOT IN INDEX: $f"
done
```

#### Check 4 — INFERRED Edge Verification
From GRAPH_REPORT, extract the list of INFERRED edges (confidence < 1.0).
For edges with confidence ≤ 0.7, verify they are plausible or flag for correction.

#### Check 5 — Concept Debt (from Graph)
Terms recurring in 3+ wiki pages that have no `wiki/concepts/` page:
```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_devWiki
$(cat graphify-out/.graphify_python) -c "
import json
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path
from collections import Counter

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')

# Find conceptually_related_to clusters with no rationale node
relations = [(G.nodes[u].get('label',''), G.nodes[v].get('label',''), d.get('relation',''))
             for u,v,d in G.edges(data=True) if d.get('relation') == 'conceptually_related_to']
concepts_mentioned = Counter()
for u, v, _ in relations:
    concepts_mentioned[u] += 1
    concepts_mentioned[v] += 1

print('Top recurring concepts without concept pages:')
for concept, count in concepts_mentioned.most_common(10):
    if count >= 3:
        print(f'  [{count}x] {concept}')
"
```

#### Check 6 — Problem Debt
Gotchas or bugs mentioned in source/entity pages never extracted into `wiki/problems/`.
Read recent source pages and entity pages, look for phrases like "gotcha", "issue", "bug", "workaround".

#### Check 7 — Missing Cross-References
Entity/concept names appearing as plain text instead of `[[links]]` in pages that reference them.

### Step 4 — Report

```markdown
## Wiki Lint Report — [YYYY-MM-DD]

### Graph Analysis (GRAPH_REPORT)
- God nodes: N high-centrality nodes identified. [List top 5 with wiki coverage status]
- Surprising connections: N INFERRED edges to verify
- Weakly connected: N isolated nodes (possible documentation gaps)

### 🔴 High Priority
1. **Stale source**: `plan-phase07...md` changed since ingest — re-ingest recommended
2. **Missing wiki page**: Node `[X]` has degree N but no wiki page — high-value gap
3. **INFERRED edge to verify**: `A --conceptually_related_to--> B` (confidence 0.62)

### 🟡 Medium Priority
4. **Orphan**: [[sources/old-plan]] — no inbound links
5. **Missing concept page**: "FIFO at runtime" in 4 graph nodes, no dedicated concept page
6. **Concept debt**: "[term]" appears in N wiki pages without a concept page

### 🟢 Low Priority
7. **Missing cross-ref**: [[entities/fx-service]] mentions "MANUAL provider" 3× without link
8. **Index drift**: wiki/concepts/async-io.md exists but not in index.md
```

### Step 5 — Execute Repairs (if user confirms)
Fix top-priority issues: resolve contradictions, create missing concept pages, fix index drift, add links.
After repairs, run `graphify corpus/ --update` to incorporate changes.

### Step 6 — Log the Lint Pass
```markdown
## [YYYY-MM-DD] lint | Health check
Graph: N nodes, N edges, N communities.
Issues found: N (X high, Y medium, Z low).
Repaired: [...].
Deferred: [...].
Next recommended: [topic to ingest or pages to create].
```
