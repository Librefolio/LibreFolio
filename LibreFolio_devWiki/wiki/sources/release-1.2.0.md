---
title: "Release 1.2.0 (draft): what it brings, the decisions of its cycle, what it leaves open, how it was verified — tag date: pending"
category: source
source_type: release
status: draft
date_ingested: 2026-10-13
original_path: CHANGELOG.md
tags: [release, release-1.2, changelog, features, decisions, open-problems, verification, backlog]
related:
  - decisions/changelog-entry-rules
  - sources/r-full-run-coverage-2026-10-12
  - decisions/gallery-is-a-release-gate-with-real-data
  - features/registry
---

# Source: release 1.2.0 (draft)

> **Draft — tag date: pending.** The sections marked *to fill at the tag* are completed when `v1.2.0` is tagged;
> until then every count on this page is the state of `dev_release2` on 2026-10-13.

## Summary

1.2.0 is the second feature release after 1.0, built on `dev_release2` after `v1.1.0` (2026-09-07). Its chapter in
`CHANGELOG.md` was checked line by line against the code and against `v1.1.0` (`60f734e08`, under the rules of
[[decisions/changelog-entry-rules]]). At that commit the chapter holds **25 ✨ Added** entries (with 27 sub-items),
**149 🐛 Fixed** in 13 groups (9 of them 🔒 Security), **32 🔄 Changed** and **7 ⚠️ Breaking changes**. Its header
still carries a provisional date (2026-10-19) and the line «Preparing v1.2.0».

| | |
|---|---|
| Version | 1.2.0 |
| Tag | `v1.2.0` — tag date: **pending** |
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

- **🐛 Fixed**, by group: imports and transaction editing 36, sign-in, language, app icons and small screens 25,
  exchange rates and the Dashboard 20, Docker and self-hosting 13, asset providers and feedback 12, 🔒 security 9,
  dialogs and menus 8, AI Export 7, Risk Analysis 7, documentation 5, asset events and the data editor 4, charts 2,
  faster reports 1. A 🐛 fixes a defect that existed in the last release; «Present since» names the release it was born in.
- **Released defects with a page of their own**: the stored XSS of `v1.1.0` ([[decisions/html-escape-at-the-source]]);
  `POST /portfolio/wac` answering anyone since its first version ([[problems/portfolio-wac-endpoint-answered-anyone]]);
  the hidden half of a removed pair (V-29, [[problems/hidden-pair-half-survived-row-removal]]); `dev.py` unusable in
  the 1.1.0 image ([[problems/devpy-unusable-in-docker-image]]); the 1.1 images with a debug frontend
  ([[problems/release-images-shipped-debug-frontend]]); event markers lost in the last, open period at weekly or monthly
  resolution, since v1.0.0 (R-5, [[problems/event-markers-lost-in-the-last-partial-period]]; its 🐛 line, with the open
  period's tooltip, is in the chapter since `fcc4ac96f` and `ef666fdee`).
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
| [[problems/schwab-favicon-blocked-by-orb]] | Schwab's favicon blocked by a bot check | U-B3 |
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

[[problems/release-shots-show-dirty-version]] is resolved in the code and waits for the first nightly after the push
(M-25 stays in the backlog). *Resolved since the first draft* (train 87): [[problems/jscoverage-teardown-spends-the-test-budget]]
(V-28) and [[problems/login-returns-before-the-app-has-started]] (V-27).

### The backlog after 1.2

`BACKLOG_POST_1.2.md` keeps the open work by workstream (C coordinator, Risk, D PAC and Tools, I broker P&L,
P transactions and bulk, T financial maths, M translations and gallery, Q docs and onboarding, S Scalable, V E2E data
quality, 09 feedback, U plugins); `TODO_FUTURI.md` keeps the deliberate future. In the feature registry, ten features
stay `planned` ([[features/F-077]], [[features/F-079]], [[features/F-081]], [[features/F-082]], [[features/F-084]], [[features/F-087]], [[features/F-090]], [[features/F-091]], [[features/F-094]], [[features/F-108]]) and three are ideas.

## Verification

- **R's full run with coverage** (2026-10-12, train 68, `a5653f9ef`) — [[sources/r-full-run-coverage-2026-10-12]]:
  pytest 12 627 and vitest 10 760 passed with no red; Playwright 1 163 passed and 29 failed, 27 of them load and 2
  already cured. Coverage: backend 91.51 % from its tests, frontend 71.24 % of statements (78.4 % without
  `features/tools`, where the PAC planner lives).
- **The gallery** ([[decisions/gallery-is-a-release-gate-with-real-data]]): M's full run of 2026-10-13 on train 80
  (`cea8a478d`), with the frontend built as `v1.2.0`: 242 passed, 9 failed, 1 skipped by design, in 1.4 hours. Four
  causes: Schwab's favicon (4, first read as the environment, then found to be our own favicon mark in the gallery,
  cured in `6bb79fecd` — [[problems/schwab-favicon-blocked-by-orb]]), a test hook that read `data-dist-pct` in the
  interface language (2, cured in `dfc4f9ccc` — [[problems/test-hooks-read-the-localized-text]]), and two fixed waits
  (1 and 2, the clock, cured in `6bb79fecd`). The targeted rerun of the touched tests passed 42 of 42. M's report is
  kept outside the repository.
- **The gates**: `./dev.py test utils` runs five — `gate-i18n-catalog`, `gate-i18n-usage`,
  `gate-plugin-i18n-ownership`, `gate-plugin-layout`, `gate-docs-links` — and vitest runs the `*.gate.test.ts` files
  (clipboard sink, flag font, HTML interpolation and HTML sink, the layout guards). Their state at the tagged commit
  is filled at the tag.

### To fill at the tag

| Item | State |
|---|---|
| Tag date | pending |
| R's final run (counts, coverage, reds and their triage) | pending |
| Gates at the tagged commit | pending |
| Gallery at the tagged commit | pending |
| First nightly after the push (the dirty version, M-25) | pending |
| CHANGELOG counts and header date at the tag | pending |

## Source files

| Role | Path |
|------|------|
| The chapter | `CHANGELOG.md` (`## [1.2.0]`) |
| Backlog after 1.2 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| R's report | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/report-R-full-run-coverage-20261012.md` |
| Migration | `backend/alembic/versions/004_release_1_2_0_schema.py` |
| CLI gates and their tests | `backend/test_scripts/test_utilities/` |
| Deliberate future | `TODO_FUTURI.md` |
| Feature registry | `LibreFolio_devWiki/wiki/features/registry.md` |
