---
title: "Material for MkDocs tables resist styling: an image leaves the column's minimum width, `vertical-align` loses to Material's rule, and the table is only as wide as its content"
category: problem
status: resolved
date: 2026-10-12
tags: [docs, mkdocs, material, css, tables, mobile, playwright, workstream-m]
related:
  - features/F-069
  - features/F-102
  - decisions/scalable-two-accounts-two-plugins
  - sources/phase00-translation-round12-2026-10
---

# Problem: three CSS traps in Material's tables

## Symptom

During the developer's live review of two user pages (batch 23, 2026-10-12), his requests on two tables did not take
effect as written:

- on the Scalable import page he asked for larger account icons and the account's name on one line, «anche su schermi
  mobile»: on a 390 px screen «Conto deposito» spilled into the second column, and the cells stayed aligned to the
  top of the taller icon row;
- on the connection-security guide he asked for the three pros-and-cons tables «50-50 su ogni schermo»: each table
  was only as wide as its content, with uneven columns.

M found the causes in a browser with Playwright and measured the result at 1280 and 390 px, in the four languages.

## Root Cause

1. **Images leave the column's minimum width.** Material sets `.md-typeset img { max-width: 100% }`; a percentage
   width does not count toward a table column's minimum width, so on a narrow screen the column shrank below the icon
   plus the name, and the name spilled.
2. **`vertical-align` loses.** Material's `.md-typeset table:not([class]) td { vertical-align: top }` is more specific
   than a plain `td` rule, so `vertical-align: middle` did nothing until the selector matched its specificity
   (`table td` inside the wrapper class, in `extra.css`, which loads after Material's stylesheet).
3. **The table wrapper is an inline block.** Material wraps each table in `.md-typeset__table`, as wide as its
   content: a `width: 100%` on the table has nothing to fill.

## Solution

`11339afa6` («docs: review Scalable and the security guide»), styles scoped to a wrapper class, never to all tables:

- **`lf-accounts-table`** (`<div class="lf-accounts-table" markdown>` on the Scalable page): `white-space: nowrap` on
  the first two columns, `vertical-align: middle` on `table td`, `max-width: none` on the icons, a minimum width on the
  third column. Material's own scroll wrapper scrolls the table sideways on a phone.
- **`lf-pros-cons`** (the connection-security guide): `display: block` on the wrapper, `table-layout: fixed` and
  `width: 100%` on the table, `width: 50%` on every cell — two equal columns on every screen, whatever the cells hold.

The developer approved the Scalable page («vista la pagina di scalable, approvata a pieni voti») and the guide («il
resto mi piace!»).

## Prevention

Scope table styles with a `<div class="…" markdown>` wrapper, match the specificity of Material's
`table:not([class])` rules, and check a table at a phone's width in every language before calling it done: the
longest label is not in the same language for every column.

## Source files

| Role | Path |
|------|------|
| The two table styles | `mkdocs_src/docs/static/extra.css` |
| Scalable import page (accounts table) | `mkdocs_src/docs/user/transactions/import/scalable.en.md` |
| Connection-security guide (pros-and-cons tables) | `mkdocs_src/docs/user/connection-security.en.md` |
| Journal (§14.5, §14.8) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
