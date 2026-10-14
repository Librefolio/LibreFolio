---
title: "Release 1.2.0 (2026-10-14): what it brings, the decisions of its cycle, what it leaves open, how it was verified"
category: source
source_type: release
status: released
date_ingested: 2026-10-13
original_path: CHANGELOG.md
tags: [release, release-1.2, changelog, features, decisions, open-problems, verification, backlog]
related:
  - decisions/changelog-entry-rules
  - sources/r-full-run-coverage-2026-10-12
  - decisions/gallery-is-a-release-gate-with-real-data
  - features/registry
---

# Source: release 1.2.0

> **Released on 2026-10-14**: tag `v1.2.0` on `cf00fac7d` (`main`), the same tree as `a3fe2eb04` on `dev_release2`.
> Every count on this page is the state of `dev_release2` at `a28beed92`.

## Summary

1.2.0 is the second feature release after 1.0, built on `dev_release2` after `v1.1.0` (2026-09-07) and dated
2026-10-14. Its chapter in `CHANGELOG.md` was checked line by line against the code and against `v1.1.0`
(`60f734e08`, under the rules of [[decisions/changelog-entry-rules]]), then completed up to the release. At
`a28beed92` it holds **25 ✨ Added** entries (with 27 sub-items), **152 🐛 Fixed** in 13 groups (9 of them 🔒
Security), **32 🔄 Changed** and **7 ⚠️ Breaking changes**, under the header `## [1.2.0] - 2026-10-14`. The line
«Preparing v1.2.0» gave way to the approved introduction (`a28beed92`), quoted here as it stands in the chapter:

> What 1.2 adds to 1.1:
>
> - 🧰 **Tools**: a new section, with its first tool, the **PAC allocator**, which works out the purchases that bring your allocation closer to its target weights.
> - 📉 **Risk**: the Risk tab of the Dashboard and broker pages answers four questions, and Risk Analysis leaves beta, except the simulation.
> - 💰 **Purchase cost and P&L**: thanks to the report in [#32](https://github.com/Librefolio/LibreFolio/issues/32), we found a problem in how the cost of each purchase was calculated when exchange rates were involved, so metrics on the KPI cards such as the P&L were wrong. The algorithm is now fixed: each purchase is converted at its own date's rate, and the totals are right.
> - 💱 **Cash in other currencies**: cash held in another currency is now valued at each day's rate, and the Period view shows how much the exchange rate made it gain or lose.
> - 📊 **Dashboard**: privacy mode, the P&L view in the Growth chart, Yield on Cost and benchmarks are new, and the pie chart shows the nine new asset types grouped in their families.
> - 📥 **Imports**: Scalable Capital, Danske Bank (alpha), and DEGIRO statements in any language; and if you upload a file to the wrong broker, the app now tells you right away.
> - 🌍 **Languages**: numbers, dates and the changelog follow the interface language.
> - 👋 **First sign-in**: new users now get a quick tour and guides that show them the interface the first time they sign in.
> - ⚡ **Performance**: pages download less data, and reports no longer stall on very long exchange-rate histories.
> - 🔒 **Security**: a cross-site scripting (XSS) issue is closed, some API endpoints now require signing in, and the sidebar tells you whether your connection is secure.
> - 🐛 **Fixes**: many defects are fixed, some of them present since v0.9.0.

| | |
|---|---|
| Version | 1.2.0 |
| Tag | `v1.2.0`, 2026-10-14, on `cf00fac7d` — the merge of PR #46 (`dev` into `main`) |
| Previous release | `v1.1.0`, 2026-09-07 |
| Database | one Alembic revision, `004_release_1_2_0_schema` (benchmark flag, widened taxonomy, onboarding progress); at the first start an existing database rebuilds six tables so that ids are never reused — [[problems/reused-ids-after-delete]] |
| AI Export | at most one version step per component over 1.1.0 — [[decisions/ai-export-version-bump-once-per-release]] |

## What 1.2.0 brings

Every feature page below has a status row dated 2026-10-13 that names its CHANGELOG line by section and beginning,
with the commit or the train.

| Area | Feature pages | CHANGELOG (✨ Added unless noted) |
|---|---|---|
| Risk | [[features/F-110]] engine, [[features/F-111]] the Risk tab in four levels, [[features/F-112]] the Correlation workbench, [[features/F-113]] the asset page's tab (still beta), [[features/F-114]] benchmark assets | «The Risk tab of the Dashboard and broker pages answers four…», «The Correlation tab of the Assets page becomes a workbench», «Mark an asset as a benchmark»; 🔄 «Risk Analysis leaves beta, except the simulation and the asset page» |
| Tools | [[features/F-106]] Tool platform, [[features/F-107]] PAC allocator | «A new Tools page in the sidebar», «PAC allocator is the first packaged tool» |
| Portfolio and charts | [[features/F-055]], [[features/F-097]], [[features/F-100]], [[features/F-088]], [[features/F-033]] | «P&L view in the Growth chart», «Exchange-rate results on cash in the Period view», Yield on Cost in the holdings tables, «Rolling Return in the asset chart», «Step through assets from their page»; 🔄 «Purchase cost is what you paid, in the display currency» |
| Imports and transactions | [[features/F-013]], [[features/F-103]], [[features/F-049]], [[features/F-048]] | «Scalable Capital importers», «Danske Bank (Finland) importer, alpha», «A file uploaded to the wrong broker is caught», «The bulk editor merges transfers more safely» |
| Interface | [[features/F-008]], [[features/F-101]], [[features/F-102]], [[features/F-105]], [[features/F-104]], [[features/F-109]] | 🔄 «Numbers and dates follow the interface language everywhere»; «Privacy mode», «Connection security in the sidebar», «New users now get a Welcome setup», «Settings › About has a new Support LibreFolio card», «The changelog speaks your language» |
| Assets and FX | [[features/F-024]], [[features/F-020]] | «Asset types: nine new types», «FX route metadata in the API» |

### Fixes, changes and breaking notes

- **🐛 Fixed**, by group: imports and transaction editing 38, sign-in, language, app icons and small screens 25,
  exchange rates and the Dashboard 20, Docker and self-hosting 13, asset providers and feedback 12, 🔒 security 9,
  dialogs and menus 8, AI Export 7, Risk Analysis 7, documentation 5, asset events and the data editor 4, charts 3,
  faster reports 1. A 🐛 fixes a defect that existed in the last release; «Present since» names the release it was born in.
- **Released defects with a page of their own**: the stored XSS of `v1.1.0` ([[decisions/html-escape-at-the-source]]);
  `POST /portfolio/wac` answering anyone since its first version ([[problems/portfolio-wac-endpoint-answered-anyone]]);
  the hidden half of a removed pair (V-29, [[problems/hidden-pair-half-survived-row-removal]]); `dev.py` unusable in
  the 1.1.0 image ([[problems/devpy-unusable-in-docker-image]]); the 1.1 images with a debug frontend
  ([[problems/release-images-shipped-debug-frontend]]); event markers lost in the last, open period at weekly or monthly
  resolution, since v1.0.0 (R-5, [[problems/event-markers-lost-in-the-last-partial-period]]; its 🐛 line, with the open
  period's tooltip and every chart's running period, is in the chapter since `fcc4ac96f`, `ef666fdee` and `10e646f79`);
  the transaction form that saved a refused date and said *valid* next to a red field, since v1.1.0
  ([[problems/transaction-form-saved-a-refused-date]], V-37, two 🐛 lines in `f8dbdddaf`).
- **🔄 Changed**: besides the three lines in the table, the risk API, `/api/v1/risk`, leaves beta with the panels: from
  1.2 it changes only with a major version, except the simulation (`4de042cfe`); the figures of CVaR and Sharpe change
  on purpose, so they stay in 🔄; ids are never reused after the database conversion; the server compresses its responses
  ([[decisions/http-gzip-in-the-app]]).
- **⚠️ Breaking changes (7)**: the cost fields of `GET /brokers/{id}/summary` and the amounts of
  `POST /portfolio/lots/analysis` can be empty; purchase cost and P&L change value for assets in another currency; the
  risk API changed in two visible ways; two endpoints now require signing in; `PATCH /api/v1/settings/global/bulk`
  refuses invalid values; behind a proxy that reports HTTPS for a plain-HTTP address, signing in no longer sticks
  ([[decisions/connection-security-server-never-upgrades]]).

## Decisions of the cycle

Sixty-two decision pages are dated between 2026-09-07 and 2026-10-13:

| Theme | Decisions |
|---|---|
| Risk (8) | [[decisions/risk-answers-four-questions]], [[decisions/risk-library-versus-own-maths]], [[decisions/risk-tool-verdicts]], [[decisions/histogram-grid-pinned-to-var-cut]], [[decisions/l3-reads-current-composition]], [[decisions/asset-set-one-preparation-not-fan-out]], [[decisions/lab-eligibility-from-risk-engine]], [[decisions/heatmap-emphasis-is-hue-free]] |
| Tools and PAC (10) | [[decisions/tool-calculation-without-authority]], [[decisions/tool-contract-from-pydantic-compiled-renderer]], [[decisions/tool-item-runs-in-owned-process]], [[decisions/pac-draft-copies-from-owned-data]], [[decisions/pac-lexicographic-fixed-l2-objective]], [[decisions/pac-fx-one-rate-map-direct-conversions]], [[decisions/pac-p1-prototype-removed]], [[decisions/pac-scip-searches-exact-replay-certifies]], [[decisions/pac-contract-compacted-before-release]], [[decisions/pac-rounding-against-the-plan]] |
| Onboarding (6) | [[decisions/onboarding-guide-observes-never-acts]], [[decisions/onboarding-versioned-progress-per-flow]], [[decisions/automatic-popups-wait-for-guides]], [[decisions/onboarding-existing-users-seeded-skipped]], [[decisions/guide-text-never-announces-another-guide]], [[decisions/onboarding-positions-in-browser-per-account]] |
| Portfolio maths and cost (8) | [[decisions/yield-on-cost-definition]], [[decisions/portfolio-pnl-series-contracts]], [[decisions/financial-math-single-average-cost]], [[decisions/financial-math-one-home]], [[decisions/utils-leaf-functions-only]], [[decisions/native-cash-daily-revaluation]], [[decisions/auto-cost-basis-zero-without-position]], [[decisions/transfer-auto-cost-from-sending-broker]] |
| Transactions, imports and assets (9) | [[decisions/transfer-pair-same-asset-opposite-quantity]], [[decisions/orphan-transfer-becomes-an-adjustment]], [[decisions/promote-respects-asset-event-link]], [[decisions/bulk-pairs-new-with-saved]], [[decisions/brim-report-sets]], [[decisions/scalable-two-accounts-two-plugins]], [[decisions/import-wizard-default-plugin-check]], [[decisions/broker-icon-order-dedicated-plugin-first]], [[decisions/asset-type-two-level-taxonomy]] |
| Interface, privacy and security (7) | [[decisions/figures-in-the-interface-language]], [[decisions/privacy-mask-at-the-formatter]], [[decisions/html-escape-at-the-source]], [[decisions/connection-security-server-never-upgrades]], [[decisions/security-details-close-after-30-seconds]], [[decisions/clipboard-through-one-helper-with-a-gate]], [[decisions/pdf-preview-viewer-only-local-assets]] |
| Plugins, translations and docs (5) | [[decisions/plugin-folders-and-split-i18n]], [[decisions/changelog-translated-by-chapter]], [[decisions/changelog-translated-by-heading-pieces]], [[decisions/fr-typography-at-build-time]], [[decisions/docs-anchors-from-the-render]] |
| Release, tests and process (9) | [[decisions/python-stays-on-3-13]], [[decisions/gallery-is-a-release-gate-with-real-data]], [[decisions/release-image-tags-latest-light]], [[decisions/http-gzip-in-the-app]], [[decisions/user-docs-plain-dev-manual-technical]], [[decisions/e2e-gaps-of-1-2-before-release]], [[decisions/data-quality-proved-on-real-data]], [[decisions/ai-export-version-bump-once-per-release]], [[decisions/changelog-entry-rules]] |

## What the release leaves open

### Open problems

| Page | Open part | Backlog |
|---|---|---|
| [[problems/e2e-writes-leaked-into-shared-state]] | the rest of V-21, V-17's two runner points, V-18 | V-21, V-17, V-18 |
| [[problems/schwab-favicon-blocked-by-orb]] | accepted (developer, 13/10): the site blocks our bursts of requests, the briefcase is acceptable | U-B3, without Schwab |
| [[problems/dirty-days-ignore-fx-only-moves]] | the securities half of the FX-only days | T-U1, T-U5 |
| [[problems/broker-icon-race-condition]] | the icon loading race | C-56, C-57 |
| [[problems/bulk-modal-sticky-z-index]] | the row-selector toolbar after an import | C-61 |
| [[problems/datatable-column-resize-noop]] | the resize handle in some tables | C-62 |
| [[problems/datatable-actions-column-on-mobile]] | the actions column on a phone | — |
| [[problems/generated-client-widens-nullable-scalar]] | the generated client's widened types | — |
| [[problems/stale-version-file-shadows-git-describe]] | a leftover `VERSION` file on a development host | R2 |
| [[problems/justetf-websocket-disconnect]], [[problems/tab-writes-after-the-look]] | workarounds in place | — |
| [[problems/testid-grep-false-negative]] | recurs | — |

Under observation, without a page: V-35, the FX page's aesthetics panel that stayed open once under load; instruments
wait for the next red ([[sources/phase00-data-quality-e2e-2026-10]]).

[[problems/release-shots-show-dirty-version]] is resolved and verified on the first pipeline after the push (M-25, a
local image build, stays in the backlog). *Resolved since the first draft* (train 87): [[problems/jscoverage-teardown-spends-the-test-budget]]
(V-28) and [[problems/login-returns-before-the-app-has-started]] (V-27).

### The backlog after 1.2

`BACKLOG_POST_1.2.md` keeps the open work by workstream (C coordinator, Risk, D PAC and Tools, I broker P&L,
P transactions and bulk, T financial maths, M translations and gallery, Q docs and onboarding, S Scalable, V E2E data
quality, 09 feedback, U plugins) — among them every PAC test lot, after 1.2 by the developer's decision, with the
defects C-73…C-76 ([[features/F-107]]), and V-37b, the form's full pre-step; `TODO_FUTURI.md` keeps the deliberate
future. From R's final run and the release day:

- C-79 — deleting a broker leaves its lock file and an empty upload folder behind (no report file is orphaned);
- C-80 — backend modules below 80 %: the scheduler, two importers, `api/v1/assets.py`, the FED provider, the tools'
  resources;
- C-81 — frontend files never executed and the largest uncovered ones, to measure again once the coverage fixture
  stops losing counters (C-69);
- C-82 — the load cures (V-27, V-28, V-33, V-36) are proven at normal load only: a run under high load before the next
  release;
- C-83 — a page that asks for the current price writes the day's bar into `price_history`, so a test must count bars
  relatively;
- C-84 — `pyproject.toml` and `frontend/package.json` still say 1.1.0: nobody reads them, the app's version comes
  from `git describe`; to align at each release, or to remove;
- M-33 — no gallery shot shows the Yield on Cost column. In the feature registry, ten features
stay `planned` ([[features/F-077]], [[features/F-079]], [[features/F-081]], [[features/F-082]], [[features/F-084]], [[features/F-087]], [[features/F-090]], [[features/F-091]], [[features/F-094]], [[features/F-108]]) and three are ideas.

## Verification

- **R's final run with coverage** (evening of 2026-10-13, on `10e646f79`: train 97 plus the CHANGELOG): **0 reds**,
  15 of 15 categories green, no retry, 2 h 44 min. pytest **12 936**, vitest **11 515** and Playwright **1 221**
  passed. Coverage: backend 91.54 % from its tests (91.55 % combined with the E2E), frontend 71.17 % of statements,
  a lower bound for its E2E part while the coverage fixture loses counters (C-69); 78.34 % without
  `features/tools`. The load was low — 8.9 on average, against 37.9 on 12/10 —, so the load cures are proven at
  normal load only (C-82). Between `10e646f79` and `a28beed92` no application code changed: only the gallery's
  fixture, its normalizer and their tests, the gallery spec, the documentation and the CHANGELOGs.
- **R's run before it** (2026-10-12, train 68, `a5653f9ef`) — [[sources/r-full-run-coverage-2026-10-12]]:
  pytest 12 627 and vitest 10 760 passed with no red; Playwright 1 163 passed and 29 failed, 27 of them load and 2
  already cured. Coverage: backend 91.51 % from its tests, frontend 71.24 % of statements (78.4 % without
  `features/tools`, where the PAC planner lives).
- **The gallery** ([[decisions/gallery-is-a-release-gate-with-real-data]]): M's full run of 2026-10-13 on train 80
  (`cea8a478d`), with the frontend built as `v1.2.0`: 242 passed, 9 failed, 1 skipped by design, in 1.4 hours. Four
  causes: Schwab's favicon (4, first read as the environment, then found to be our own favicon mark in the gallery,
  cured in `6bb79fecd` — [[problems/schwab-favicon-blocked-by-orb]]), a test hook that read `data-dist-pct` in the
  interface language (2, cured in `dfc4f9ccc` — [[problems/test-hooks-read-the-localized-text]]), and two fixed waits
  (1 and 2, the clock, cured in `6bb79fecd`). The targeted rerun of the touched tests passed 42 of 42. M's report is
  kept outside the repository. **The final gallery** (2026-10-13, on `baabbf7a2`, frontend built as `v1.2.0`): 251
  passed, 0 failed, 1 skipped; after I's lot 52 the nine groups it changed were shot again: 20 passed, 0 failed
  ([[sources/phase00-translation-round12-2026-10]]). One defect lived in the shots only, never in the app: the
  allocation-history stacks — [[problems/gallery-fixture-normalizer-scaled-ratios]]; after its cure, M shot the
  allocation and positions groups again (2026-10-14, on `bae15c3cf`): 10 passed, 0 failed, the stacks at 100 %.
  **The fixture**: the developer decided on 2026-10-14 — option (a) — that it is published as it is.
- **The gates**: `./dev.py test utils` runs five — `gate-i18n-catalog`, `gate-i18n-usage`,
  `gate-plugin-i18n-ownership`, `gate-plugin-layout`, `gate-docs-links` — and vitest runs the `*.gate.test.ts` files
  (clipboard sink, flag font, HTML interpolation and HTML sink, the layout guards). All green in R's final run, among
  its 15 categories.

### To fill at the tag

Filled on 2026-10-14; the last two rows after the publication.

| Item | State |
|---|---|
| Tag date | 2026-10-14 |
| R's final run (counts, coverage, reds and their triage) | done: `10e646f79`, 0 reds, pytest 12 936, vitest 11 515, Playwright 1 221 (above) |
| Gates | green in R's final run; no application code changed after it |
| Gallery | green: 251 passed, 0 failed, 1 skipped (2026-10-13, `baabbf7a2`); the nine groups changed by I's lot 52, 20 of 20; the allocation and positions groups after I-M30, 10 of 10 (2026-10-14, `bae15c3cf`) |
| First pipeline after the push (the dirty version) | done: run 77, on PR #42's merge into `main`, reports `v1.1.0-1648-g1ee978788`, no `-dirty` — question 11 closed ([[problems/release-shots-show-dirty-version]]) |
| CHANGELOG counts and header date at the tag | done: `## [1.2.0] - 2026-10-14`; 25 ✨ (27 sub-items), 152 🐛 in 13 groups, 32 🔄, 7 ⚠️ at `a28beed92` |
| The tagged commit (SHA) | `cf00fac7d` on `main`, the merge of PR #46; its tree is the tree of `a3fe2eb04` on `dev_release2`. The GitHub release was published at 09:07 UTC |
| The release pipeline's run | run 38540086298, «Release v1.2.0»: success, finished at 10:40 UTC. Images `1.2.0`, `1.2.0-light` and `latest` on GHCR, their `docker pull` lines appended to the GitHub release, the docs site deployed from `cf00fac7d` |

## Source files

| Role | Path |
|------|------|
| The chapter | `CHANGELOG.md` (`## [1.2.0]`) |
| Backlog after 1.2 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| R's final report | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-final-run-coverage-20261013.md` |
| R's report of 12/10 | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md` |
| Migration | `backend/alembic/versions/004_release_1_2_0_schema.py` |
| CLI gates and their tests | `backend/test_scripts/test_utilities/` |
| Deliberate future | `TODO_FUTURI.md` |
| Feature registry | `LibreFolio_devWiki/wiki/features/registry.md` |
