---
title: "Docs Mermaid: the ELK layout self-hosted again, and every filled node declares its text colour"
category: decision
status: open
date: 2026-11-07
tags: [docs, mkdocs, mermaid, dark-mode, vendoring, release-1.3]
related:
  - problems/mathjax-fonts-missing-from-local-copy
  - problems/derived-css-properties-resolve-where-declared
---

# Decision: ELK self-hosted, text colour on every filled node

> **Status: open.** At this ingest (07/11/2026) the work is in review in a preview of lot E9, not yet on the release
> branch. On the branch, `.claude/rules/mkdocs.md` still says the site serves Mermaid **without** the ELK layout, and
> `mermaid-early.js` registers no layout. Re-ingest after the merge and set the status to `resolved`.

## Context

Since 30/10/2026 the documentation serves Mermaid from its own pinned copy (`./dev.py cache js`), no CDN at page load.
That copy had no ELK layout, so a diagram whose frontmatter said `layout: elk` was drawn with Dagre, and the rule told
writers not to use the key. Separately, Material draws a diagram's text in the theme's colour, which is light in the dark
theme: a node that sets its own pale `fill` and no `color` showed white text on a white box. The documentation had 127
such `style`/`classDef` lines in 24 pages and four languages.

## Decision (as proposed in the preview)

- **ELK served from a pinned copy too**, beside Mermaid (`@mermaid-js/layout-elk`, checked against a pinned hash by
  `./dev.py cache js`); `mermaid-early.js` registers the layout before Material draws. A diagram may say `layout: elk`
  when it reads better than Dagre (many nodes, nested subgraphs); diagrams stay small either way.
- **A node that sets `fill` also sets `color:`** — dark text (`#1b1b1b`) on a light fill, white on a dark one. A pure
  test gate scans every Mermaid block of every page.

## Consequences

- Writers get ELK back without any network request at page load.
- Diagrams read in both themes; the gate keeps new offenders out.

## Links

- [[problems/mathjax-fonts-missing-from-local-copy]] — the earlier vendoring of MathJax and Mermaid.
- Source: the coordinator's brief of 07/11/2026. Summary: [[sources/wave8-9-release-1.3-closing-2026-11]]

## Source files

| Role | Path |
|------|------|
| Mermaid registration before Material draws | `mkdocs_src/docs/javascripts/mermaid-early.js` |
| Pinned copies of the docs' scripts | `scripts/update_js_cache.py` |
| Diagram rules for writers | `.claude/rules/mkdocs.md` |
| Vendored Mermaid | `mkdocs_src/docs/javascripts/vendor/mermaid/mermaid.min.js` |
