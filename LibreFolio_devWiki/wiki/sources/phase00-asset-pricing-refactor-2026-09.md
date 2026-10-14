---
title: "Phase 0 / 22 — SP08: asset pricing split into responsibility modules"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/22_assetPricingRefactor/plan-phase00AssetPricingRefactor.prompt.md
tags: [phase0, release2, refactor, assets, pricing, providers, architecture]
related:
  - entities/asset-sources-package
  - concepts/prices-current-side-effect
  - decisions/three-phase-pipeline
---

# Source: Phase 0 / 22 — asset pricing refactor (SP08)

## Summary

One plan (~440 lines), shipped in `3c85866dd` (2026-09-11; journal closed in `73d207b90`) and archived on 2026-10-09.
It split the monolithic asset pricing service into the `asset_sources/` package behind a permanent thin facade,
without changing any contract; it closed backlog items P4-1, P4-4 and S6 6.4.

## Key takeaways

- The module map, the facade, the one-way dependency rule and the PREPARE → FETCH → PERSIST refresh:
  [[entities/asset-sources-package]].
- Characterisation first, then extraction; identities of caches, threads and errors preserved.
- Rejected / out of scope: normalising cache keys or `source_plugin_key`, FX and BRIM refactors, other providers.
- Off-track: the new core first logged outside the project logger — fixed by using `get_logger` like every module.

## Residuals

`get_prices_bulk` keeps a `noqa: C901 — TODO(P2-refactor)` (verified at `586a4f0ea`).

## Wiki pages updated

- [[entities/asset-sources-package]] — new.
- [[concepts/prices-current-side-effect]] — source paths moved from the monolith to `price_query.py` / `refresh.py`.

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/phases/22_assetPricingRefactor/plan-phase00AssetPricingRefactor.prompt.md` |
| Facade | `backend/app/services/asset_source.py` |
| Package | `backend/app/services/asset_sources/core.py` |
| Developer doc | `mkdocs_src/docs/developer/backend/assets/architecture.md` |
