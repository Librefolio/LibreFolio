---
title: "utils/ holds leaf functions only; anything that calls services lives in a service layer (D-P7)"
category: decision
status: resolved
date: 2026-10-12
tags: [backend, architecture, layering, utils, financial-math, refactor, workstream-t, release-1.2]
related:
  - decisions/financial-math-one-home
  - decisions/financial-math-single-average-cost
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
  service.

### What follows in release 1.2 (planned, not yet in the code at `5d0585595`)

- **BU1** — subfolders by type inside `utils/`, renames only: `utils/asset/` (sector, geo, identifier, translation),
  `utils/fx/` (currency), `utils/runtime/` (version, network, cache). The developer chose `runtime`; the `platform`
  name in T's journal was the earlier proposal (coordinator, 2026-10-12).
- **BU2** — the two exceptions to the leaf rule: the truncation of `decimal_utils` leaves `utils/` for
  `backend/app/db/precision.py` (`parse_decimal_value` stays), and the lazy `clear_cache` imports in `fx.py` go, once no
  utils→services cycle remains.
- **Method**, the same as T-1: first the exact grouping and the list of importers (76 files across the app, tests,
  scripts and `dev.py`), then one commit of renames only and one for BU2, with the backend suite identical as the gate.

## Consequences

- The layering question has one answer for every new helper: a function that calls a service is not a utility.
- The devWiki's «Source files» rows that cite the renamed modules (10 rows in 9 pages at `5d0585595`) are realigned
  after BU1 lands, by the historian.

## Links

- [[decisions/financial-math-one-home]] — the service layer for the math
- [[decisions/financial-math-single-average-cost]] — the first function placed by the same reasoning
- Source: [[sources/phase00-financial-math-home-2026-10]]

## Source files

| Role | Path |
|------|------|
| The rule | `.github/instructions/backend.instructions.md` |
| The exception: truncation importing `db.models` | `backend/app/utils/decimal_utils.py` |
| The lazy `clear_cache` imports | `backend/app/services/fx.py` |
| The cache helpers (no service import) | `backend/app/utils/cache_utils.py` |
| Plan (§P2.3, D-P7, BU1/BU2) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
| Backlog row T-BU1+BU2 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
