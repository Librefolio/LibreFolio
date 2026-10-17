---
title: "utils/ holds leaf functions only; anything that calls services lives in a service layer (D-P7)"
category: decision
status: resolved
date: 2026-10-12
updated: 2026-10-12
tags: [backend, architecture, layering, utils, financial-math, refactor, workstream-t, release-1.2]
related:
  - decisions/financial-math-one-home
  - decisions/financial-math-single-average-cost
  - problems/docker-system-info-missing-deps
  - sources/phase00-financial-math-home-2026-10
---

# Decision: `utils/` holds leaf functions only

## Context

Part 2 of workstream T's plan (plan 43 §P2.3, «Code reordering») proposed to empty `backend/app/utils/` by domain:
the asset helpers (`sector_fin_utils`, `geo_utils`, `identifier_utils`) towards the asset services, `currency_utils`
towards a `services/fx/` package, `network_utils` towards the API, the rest into a `platform/` folder — items BU1 and
BU2 of the post-1.2 backlog. On 2026-10-12 the developer answered (decision D-P7):

> «diciamo che utils era nata come logica per essere quello che tu vuoi fare in domain, sarebbero le funzioni "foglie"
> quelle più basiche, non serve quindi spostare o rinominare, al più creare dentro utils delle cartelle per
> raggruppare le tipologie di utility, quello sarebbe inteligente. Ti ho fatto creare un service layer per la finanza,
> perchè se iniziamo a chiedere cambi, asset e altro, non è più una funzione terminale, ma diventa parte dello stack di
> servizi e ha senso raccogliere queste cose in dei layer ordinati che si usano l'un l'altro»

("utils was born to be what you want to do in a `domain` folder: the leaf functions, the most basic ones. So there is
no need to move or rename them; at most, group the kinds of utility into folders inside utils — that would be smart.
I had you create a service layer for finance because once we start asking for FX rates, assets and so on, it is no
longer a terminal function: it becomes part of the service stack, and it makes sense to gather those things into
ordered layers that use one another.")

## Options Considered

1. **Empty `utils/` into the service domains** (§P2.3: `platform/`, `services/fx/`, `api/`) — dropped.
2. **A new `backend/app/domain/` folder** for the leaf functions — rejected: that is what `utils/` already is.
3. **Keep `utils/` as the home of leaf functions, grouped into subfolders by type** — chosen.

## Decision

- **`utils/` holds leaf functions only: they never import services.** Anything that needs FX, assets or other
  services belongs to a service layer, such as `financial_math/` ([[decisions/financial-math-one-home]]). The rule is
  in `.github/instructions/backend.instructions.md`, right after the «Financial Math — One Home» section (commit
  `45691452a`).
- This is also why P put the average cost in a *service* layer and not in `utils/financial/`: it calls the FX service
  ([[decisions/financial-math-single-average-cost]], «Placement»).
- At `5d0585595` the code already follows the rule, with one exception: the `utils` modules import only other
  `utils` modules, except `decimal_utils.py`, whose truncation to the database precision imports `db.models`
  (`FxRate`, `PriceHistory`). And `fx.py` still imports `clear_cache` lazily in three places, "to avoid a utils→services
  import cycle", although it already imports `get_ttl_cache` from `cache_utils` at the top and `cache_utils` imports no
  service. *Since BU2 (below) there is no exception left.*

### BU1 — delivered (2026-10-12, train 50)

- **One commit**, `346b7e292` ("refactor(utils): group utils into typed folders"), merged with train 50 (`bdc078efc`):
  `utils/asset/{sector,geo,identifier,translation}.py`, `utils/fx/currency.py`, `utils/runtime/{version,network,cache}.py`.
  `datetime_utils`, `json_utils` and `decimal_utils` stay at the root; no `_utils` suffix inside the folders; the three
  new `__init__.py` hold only a docstring, and the root's docstring states the leaf rule and the map. The developer
  chose `runtime`; `platform` in T's analysis was the earlier proposal (coordinator, 2026-10-12).
- Imports rewritten in 32 files (of the 74 that import any `utils` module); `all-backend` 12 409 passed, 28 skipped,
  0 failed, identical to the base in each of its 23 invocations.
- **A near-miss the gates could not see.** `utils/runtime/version.py` computed the project root with four `.parent`,
  written for its old place: after the move they reached `backend/`. In development nothing showed — no `VERSION`
  file, and `git describe` finds the repository from a subfolder — but the image has no `.git`, so the app would have
  read `/app/backend/VERSION` instead of `/app/VERSION` and reported version `unknown`. The coordinator found it while
  verifying; the same commit carries the fix, `_project_root()` = `Path(__file__).resolve().parents[__name__.count(".")]`,
  derived from the module's dotted name, with two red-first tests in `test_version.py`. **Lesson: in a rename, search
  the paths a file computes from its own location (`__file__`, `parents`), not only its imports** — see
  [[problems/docker-system-info-missing-deps]], the original version-in-Docker problem.

### BU2 — delivered (2026-10-12, train 53)

- **One commit**, `8dae5cc6e` ("refactor(db): move DB precision out of utils"), merged with train 53 (`f0f3de0d9`):
  `get_model_column_precision`, `truncate_to_db_precision`, `truncate_priceHistory` and `truncate_fx_rate` moved
  unchanged from `utils/decimal_utils.py` to the new `backend/app/db/precision.py`, next to the models they read.
  `decimal_utils.py` keeps only `parse_decimal_value` and no longer imports `db.models`, SQLModel or SQLAlchemy, so
  `utils/asset/geo.py` and `utils/fx/currency.py` no longer load the database models when they are imported. Imports
  rewritten in 7 files.
- **The lazy imports went, because none of them broke a cycle**: the three of `clear_cache` in `fx.py` joined the
  top-level `from …runtime.cache import clear_cache, get_ttl_cache`, and `config/__init__.py` imports `get_git_version` at the
  top. No test patches `clear_cache`, so no patch went mute; importing `backend.app.config` and `backend.app.main`
  shows no cycle.
- `all-backend` 12 411 passed, 28 skipped, 0 failed: BU1's count plus the two tests of the `version.py` root.
- Every module of `utils/` is now a leaf.

## Consequences

- The layering question has one answer for every new helper: a function that calls a service is not a utility.
- The devWiki's «Source files» rows that cited the renamed modules — 11 rows in 10 pages, this one included — and 6
  present-tense mentions in 5 pages were realigned by the historian on 2026-10-12, after BU1 entered the target. After
  BU2 one present-tense mention of the truncation ([[features/F-017]]) and this page's own rows followed.
- The method held for both lots, as for T-1: one commit of renames only, then one for what is not a rename, with the
  backend suite identical as the gate.

## Links

- [[decisions/financial-math-one-home]] — the service layer for the math
- [[decisions/financial-math-single-average-cost]] — the first function placed by the same reasoning
- Source: [[sources/phase00-financial-math-home-2026-10]]

## Source files

| Role | Path |
|------|------|
| The rule | `.github/instructions/backend.instructions.md` |
| BU2: the truncation to the database precision | `backend/app/db/precision.py` |
| BU2: `decimal_utils`, now only `parse_decimal_value` | `backend/app/utils/decimal_utils.py` |
| BU2: `clear_cache` imported at the top | `backend/app/services/fx/sync.py`, `backend/app/services/fx/storage.py` |
| BU2: `get_git_version` imported at the top | `backend/app/config/__init__.py` |
| The cache helpers (no service import) | `backend/app/utils/runtime/cache.py` |
| BU1: the root's docstring (leaf rule and map) | `backend/app/utils/__init__.py` |
| BU1: the project root from the module's dotted name | `backend/app/utils/runtime/version.py` |
| BU1: the two tests of the near-miss | `backend/test_scripts/test_utilities/test_version.py` |
| BU2: precision and parsing tests | `backend/test_scripts/test_utilities/test_decimal_utils.py`, `backend/test_scripts/test_db/test_numeric_truncation.py` |
| Plan (§P2.3, D-P7, BU1/BU2) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
| Backlog row T-BU1+BU2 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
