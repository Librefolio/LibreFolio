---
title: "Waves 8 and 9 — the 1.3 closing: space limit enforced, restore from a kept backup, colours by asset, P&L day change, WebP gallery, October notes"
category: source
source_type: meeting
date_ingested: 2026-11-07
original_path: "DECISIONI-ondata8-20261106.md, DECISIONI-giro2-backup-20261107.md, TRIAGE-feedback-ottobre-20261107.md, kickoff-w8.md, kickoff-w9-backup.md, kickoff-w9-email-guida.md, kickoff-w9-ottobre.md (coordinator files, outside the repository); commits of dev_release2 06–07/11/2026; LibreFolio_developer_journal/Release_2/Phase_2/ATTIVITA_INIZIO_1.4.md"
tags: [release-1.3, wave-8, wave-9, backup, restore, storage, dashboard, risk, pac, email, docs, gallery]
related:
  - decisions/storage-limit-enforced
  - decisions/restore-waits-and-restores-from-kept-backup
  - decisions/pnl-day-change-against-yesterdays-nav
  - decisions/one-colour-rank-per-asset
  - decisions/gallery-webp-with-png-fallback
  - decisions/docs-home-badges-match-project-site
  - decisions/mermaid-elk-layout-and-node-text-colour
  - problems/derived-css-properties-resolve-where-declared
  - problems/body-background-covers-negative-z-fixed-layer
  - problems/exact-key-tests-break-when-response-gains-a-field
  - problems/pipefail-makes-grep-q-pipe-guards-unreliable
  - problems/portfolio-cache-ignored-role-and-share
---

# Source: waves 8 and 9 — the 1.3 closing (06–07/11/2026)

## Summary

The last two waves of release 1.3 came from the developer's test lists of 06 and 07/11/2026. The coordinator wrote
one decision file per round, with answers, proposals and questions; the developer answered in the same file, and his
answers win over the proposals. Wave 8 (lots B8, C8, F8, E8) fixed the colours by asset, enforced the space limit,
reshaped the risk loss cards and moved the gallery to WebP. Wave 9 (lots C9, E9, G9, R9, P9) let a restore wait and start
from a kept backup, added the logo to emails and clarified `LIBREFOLIO_PUBLIC_URL`, and closed most of the developer's
October notes, the P&L day change included. About 180 commits landed on `dev_release2` on 06–07/11, then the four-language
changelog chapters.

| Source | What it adds |
|---|---|
| `DECISIONI-ondata8-20261106.md` | Answers on image size, colours, backup retention; proposals for the loss cards and the horizon; questions 1–7 and the developer's answers (space limit in 1.3, dashes, ECharts infobox, no pie legend, no Tailscale change) |
| `kickoff-w8.md` | Lots B8 (positions and allocation), C8 (space limit), F8 (risk), E8 (WebP gallery, measured q85) |
| `DECISIONI-giro2-backup-20261107.md` | The stage id lost with the tab; what the limit counts; the password check without extra rules; proposals 1–10 in steps A and B |
| `kickoff-w9-backup.md` | Lot C9, steps A and B, and the rule «grep for exact-key tests before adding a field» |
| `kickoff-w9-email-guida.md` | Lot E9: guide wording, inline logo, the `LIBREFOLIO_PUBLIC_URL` example, admin pages reformatted in Italian |
| `TRIAGE-feedback-ottobre-20261107.md` | 27 October notes checked on the code: 4 already solved, 15 small for 1.3, 6 for 1.4, 6 developer decisions |
| `kickoff-w9-ottobre.md` | Lots G9 (charts), R9 (risk, Dashboard, AI Export), P9 (PAC) |
| `ATTIVITA_INIZIO_1.4.md` | What is certain for 1.4 |

## Key takeaways

- **Space limit enforced** — uploads, reports, manual backups and restores refused past it; automatic, panel and
  command-line backups always made; transactions, prices and the database never stopped
  ([[decisions/storage-limit-enforced]]). The developer reversed two rows of the proposal.
- **Restore** — waiting checks listed by the server, a check refused for space deleted at once, restore from a kept
  backup, password verified against the opened copy, avatars and a parts bar
  ([[decisions/restore-waits-and-restores-from-kept-backup]]).
- **P&L day change** — shown against yesterday's NAV; the share of the total P&L removed from the API without
  deprecation ([[decisions/pnl-day-change-against-yesterdays-nav]]). The October kickoff first said «D8 is not done»;
  the developer decided the same day.
- **Colours** — one rank function for every asset colour; dashes for the same asset at several brokers; icons in the
  asset pie ([[decisions/one-colour-rank-per-asset]]). The report cache then needed an asset fingerprint
  ([[problems/portfolio-cache-ignored-role-and-share]], «Seen again»).
- **Risk** — loss cards in one shape, KaTeX histogram tooltip, horizon letters in any order, Ulcer index moved into the
  worst-fall card (reversing the caption choice of 18/09), histogram zoom, L2 texts rewritten (one said «the excess is
  cash» where it came from unpriced positions). History rows in [[features/F-111]].
- **PAC** — P1–P7 of the October notes (Risk picker without INDEX, Broker tiles, phone layouts, waiting bar, «at the end
  of the plan» / «Final», funding sentence with an amount badge): [[features/F-107]].
- **Dashboard cache** — confirmed as it is ([[concepts/stale-while-revalidate-page-cache]]).
- **Docs** — WebP gallery with PNG fallback ([[decisions/gallery-webp-with-png-fallback]]); home badges of the project
  site ([[decisions/docs-home-badges-match-project-site]]); derived colours under the dark scheme
  ([[problems/derived-css-properties-resolve-where-declared]]); Mermaid ELK and node text colour still in review
  ([[decisions/mermaid-elk-layout-and-node-text-colour]], open).
- **Email** — inline logo, the `LIBREFOLIO_PUBLIC_URL` example, admin pages reformatted in Italian first
  ([[domains/email]], «Release 1.3 closing»).
- **Theme** — the scrollbar gutter strip and the lost login animation
  ([[problems/body-background-covers-negative-z-fixed-layer]]).
- **Process** — exact-key tests broke twice ([[problems/exact-key-tests-break-when-response-gains-a-field]]);
  `pipefail` and early-exiting readers ([[problems/pipefail-makes-grep-q-pipe-guards-unreliable]]).
- **Not changed** — Tailscale/Headscale proxy trust: nothing to do (the developer, question 6). Backup retention removing
  the oldest above the threshold while keeping the last one: correct, not a defect. Image size: no anomaly (only new
  layers were downloaded).

## What moved to 1.4 (`ATTIVITA_INIZIO_1.4.md`)

Certain: the rest of the code reordering of plan 43 (package splits with unchanged URLs and `operationId`s); fees linked
to their transaction (issue #25 — several fees per transaction, DIVIDEND and INTEREST too, without breaking TRANSFER,
FX_CONVERSION and CASH_TRANSFER); lot analysis in LIFO besides FIFO (PMC and specific-lot selection ruled out); the PAC
Rebalancer with one FX step per broker and pair and `fx_cost` out of the contract ([[features/F-108]]); bulk edit of
selected assets; small deferred clean-ups; small commits with real dates at the start of 1.4. To discuss again before
doing: the asset detail header, a click-fixed histogram box, a type badge row in the L2 heatmap, real progress from the
PAC solver, an `N_eff` measured on priced positions only, a backend threshold for a P&L share.

## Not filed

- «Snapshot trees cherry-picked onto a moving candidate»: no trace in the code or in these sources beyond clean
  cherry-picks of the lot branches onto the candidate (`git cherry` shows every commit applied). Needs the
  coordinator's account before a page.

## Wiki pages updated

- Created: the seven decisions and four problems listed in `related`.
- Updated: [[problems/portfolio-cache-ignored-role-and-share]] (asset fingerprint), [[decisions/backups-kept-in-backups-folder]]
  (limit now enforced), [[entities/backup-router]] (the five modules), [[features/F-073]] (documented, restore rows),
  [[features/F-054]], [[features/F-055]], [[features/F-107]], [[features/F-108]], [[features/F-111]] (status rows),
  [[concepts/stale-while-revalidate-page-cache]] (D1 confirmed), [[domains/email]] (lot E9).

## Source files

| Role | Path |
|------|------|
| Space limit | `backend/app/services/platform/storage_limit.py` |
| Restore routes | `backend/app/api/v1/backup/restore.py` |
| Day change | `backend/app/services/financial_math/portfolio/period.py` |
| Colour ranks | `frontend/src/lib/features/dashboard/positionsSeries.ts` |
| WebP conversion | `scripts/gallery_webp.py` |
| Docs theme hook | `mkdocs_src/hooks/lf_theme_tokens.py` |
| Changelog of 1.3 | `CHANGELOG.md` |
| 1.4 start list | `LibreFolio_developer_journal/Release_2/Phase_2/ATTIVITA_INIZIO_1.4.md` |
