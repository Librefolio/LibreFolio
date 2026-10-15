---
title: "The documentation described things the code did not do: found while rewriting the 1.2 pages from the code"
category: problem
status: resolved
date: 2026-10-08
updated: 2026-10-09
tags: [docs, mkdocs, drift, user-docs, developer-docs, fx, scheduler, auth, risk, brim, docker, workstream-q, release-1.2]
related:
  - decisions/user-docs-plain-dev-manual-technical
  - problems/devpy-unusable-in-docker-image
  - features/F-069
  - features/F-102
  - sources/phase00-docs-english-12-2026-10
---

# Problem: pages that promised what the code did not do

## Symptom

When workstream Q aligned the English documentation for 1.2, each page was rewritten from the code rather than from
the previous text ([[decisions/user-docs-plain-dev-manual-technical]]). Pages that had looked right turned out to
describe behaviour the code did not have — some since before v1.1.0, some only for the user who followed them.

## Root Cause

The pages had been written from plans and earlier pages, and nothing compared them with the code: the strict build
and `check-links` prove that links and anchors exist, not that a sentence is true. Each finding below was proved on
the code before the page changed.

| Page | What it said | What the code does | Fixed in |
|------|--------------|--------------------|----------|
| `user/transactions/import/generic-csv` | The Generic CSV importer lets you map columns by hand | Columns are recognised from their headers and aliases (`HEADER_MAPPINGS`) | `dfcbc0003` (Q1) |
| `user/transactions/import/ibkr` | Export the Activity Statement; dividends, taxes and deposits are imported | The parser does not read the Activity Statement; the page now says so | `eee56b42a` (wave 1) |
| `developer/backend/fx/providers/snb` | Wrong from top to bottom | SNB publishes monthly averages, dated on the 1st of the month, through a JSON API, for about 25 currencies | `1c2f88d67` (wave 2) |
| `developer/backend/scheduler` | A file lock elects the leader | The lowest PID among the uvicorn workers leads (`leader.py`); the price function, the 500-entry log and `LIBREFOLIO_NO_SCHEDULER` were also wrong | `22d80282a` (wave 3) |
| `developer/architecture/users_and_brokers` | Sessions live in memory | A stateless JWT cookie; a restart without `JWT_SECRET` signs everyone out | `22d80282a` (wave 3) |
| `admin/docker_advanced` | Run `./dev.py docker exec db upgrade` after an update | That command never worked in the image ([[problems/devpy-unusable-in-docker-image]]); the server applies pending migrations at every start, and a failure stops it — so the right procedure is no command | `22d80282a` (wave 3) |
| `user/fx/providers/ecb` | About 45 currencies | The daily reference feed of 2026-10-08 had 29; BGN is gone | `ef1397227` (S19) |
| Sharpe and Sortino ratio pages | The annual risk-free rate is converted with 1/365 | The code converts it with the series' own annualisation factor, the one that scales the volatility (`daily_risk_free_rate`) | `1fdcaef38` |
| `developer/test-walkthrough` | `./dev.py test --coverage all` runs everything with coverage | It stopped with «test category required»: `all` was read as the language; the command is `--coverage all all` | `664fe9687` (S23) |

On the auth row: on 2026-10-08 the session cookie was also never `Secure`. That changed the next day, in the code:
`11be06988` made it follow `SESSION_COOKIE_SECURE` (`auto`, `always`, `never`) — [[features/F-102]].

## Solution

Each page was corrected in the commit named in the table, with the evidence in the journal. The urgent case was the
Docker one, reported to the coordinator before the evening gate: an admin following the page would hit an error on
a production install. Workstream L made `dev.py` usable in the image in train 19, and the admin page now says that
migrations need no command.

## Prevention

- Rewrite a page from the code, not from the previous page, and cite the file that proves each claim.
- A drift found outside the batch's scope is reported with its proof, or fixed when the risk for the user is high —
  the IBKR page was one of Q's «⚠️ Fuori pista» notes.
- Not every drift was in the pages: with `mkdocs serve`, MkDocs rewrote `site_url` to the local address and the gallery
  images fell back to the local server instead of the online site; `overrides/main.html` now reads the canonical URL
  (`bb48d7e0a`).

## Source files

| Role | Path |
|------|------|
| Generic CSV header mapping | `backend/app/services/brim_providers/broker_generic_csv/plugin.py` |
| Scheduler leader election | `backend/app/services/platform/scheduler/leader.py` |
| Risk-free rate per period | `backend/app/services/risk/metrics.py` |
| Session cookie setting | `backend/app/config/__init__.py` |
| ECB provider | `backend/app/services/fx_providers/ecb/plugin.py` |
| SNB provider | `backend/app/services/fx_providers/snb/plugin.py` |
| Migrations at startup | `backend/app/services/platform/database_bootstrap.py` |
| Gallery fallback base | `mkdocs_src/overrides/main.html` |
| Admin page (migrations need no command) | `mkdocs_src/docs/admin/docker_advanced.en.md` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md` |
