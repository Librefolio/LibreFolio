---
name: wiki-lint
description: "Use this skill (historian agent) when the user wants to health-check the devWiki. Finds orphan pages, drift from source changes (via git hash registry), contradictions, stale content, missing cross-references, concept debt, and index drift. Produces a prioritized repair list."
---

# Wiki Lint Skill

> Periodic health check of `LibreFolio_devWiki/`.
> Run after 5-10 ingests, at phase boundaries, or when re-entering after a long break.

## Lint Workflow

### Step 1 — Load the Index
Read `LibreFolio_devWiki/index.md` completely.

### Step 2 — Run Checks

#### Check 1 — Orphan Pages
Pages with no inbound `[[link]]` from any other wiki page.
Grep all `.md` files in `wiki/` for `[[{page-slug}]]` references.

#### Check 2 — Drift Detection
Read `raw/ingest-registry.md`. For each row, run:
```bash
git diff {hash} HEAD -- {source-path}
```
Flag sources with non-trivial changes (>5 lines or structural changes) as "possibly stale — re-ingest recommended".

#### Check 3 — Missing Cross-References
Entity/concept names appearing as plain text instead of `[[links]]` in pages that reference them.

#### Check 4 — Contradictions
Two pages making conflicting claims about the same topic.
Flag: "[[page-A]] says X but [[page-B]] says Y".

#### Check 5 — Concept Debt
Terms recurring across 3+ pages that have no `wiki/concepts/` page.
Suggest top 5 most impactful missing concept pages.

#### Check 6 — Problem Debt
Gotchas or bugs mentioned in source/entity pages never extracted into `wiki/problems/`.

#### Check 7 — Index Drift
Files in `wiki/` not listed in `index.md`, or index rows pointing to non-existent files.

### Step 3 — Report

```markdown
## Wiki Lint Report — [YYYY-MM-DD]

### 🔴 High Priority
1. **Stale source**: `plan-phase07...md` changed since ingest — re-ingest recommended
2. **Contradiction**: [[decisions/foo]] says X, [[entities/bar]] says Y

### 🟡 Medium Priority
3. **Orphan**: [[sources/old-plan]] — no inbound links
4. **Missing concept page**: "FIFO at runtime" in 4 pages, no dedicated page

### 🟢 Low Priority
5. **Missing cross-ref**: [[entities/fx-service]] mentions "MANUAL provider" 3× without link
6. **Index drift**: wiki/concepts/async-io.md exists but not in index.md
```

### Step 4 — Execute Repairs (if user confirms)
Fix top-priority issues: resolve contradictions, create missing concept pages, fix index drift, add links.

### Step 5 — Log the Lint Pass
```markdown
## [YYYY-MM-DD] lint | Health check
Issues found: N (X high, Y medium, Z low).
Repaired: [...].
Deferred: [...].
```
