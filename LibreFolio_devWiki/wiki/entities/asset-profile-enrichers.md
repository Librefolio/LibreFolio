---
title: "Asset profile and enrichers"
category: entity
type: subsystem
date: 2026-11-19
tags: [backend, frontend, assets, profile, enrichers, plugins, history]
related:
  - entities/market-data-scheduler
  - entities/asset-sources-package
  - problems/layout-read-before-a-late-list
---

# Asset profile and enrichers

## Summary

The **profile** is an asset's descriptive data (description, countries, sectors, key figures such as TER, fund size,
yields, duration, and details by group), kept as a **history of steps**. Each row has a day from which it holds, who
gave it (an enricher or a user), and the read that confirmed it. **Enrichers** are the plugins that read it from
outside sources: justETF, Yahoo Finance, Borsa Italiana, and `mockenrich` in tests. An asset's enrichers are an ordered
dictionary: the first that gives a voice wins it, and a source down hands the voice to the next. Built by project 68
(release 1.4): A (store), B (bindings, read and merge, weekly job), C (plugins), D (read API, history), E (UI), F (docs).

## Details

### Backend

- **Catalogue.** Each voice declares its shape (number, percentage, amount, text, choice, map, date…), groups, whether
  it is a key figure, whether it is volatile, and its topic. The store refuses a value the catalogue does not accept,
  and B5 checks each voice before writing.
- **Store.** It writes only what changed, as a new step. «Dimentica» deletes rows as if never written, and sends back
  the `as_of` of the read the page showed. The row ids are not AUTOINCREMENT, so a page left open could otherwise
  delete a newer row that reused an id; the server refuses 409/404 as a typed result.
- **Bindings.** `asset_enrichers` holds two columns, so that the user and the reads never overwrite each other:
  - `config` is the user's ordered dictionary, written only by the user;
  - `state` is the last read and outcome of each plugin, written only by the reads.
- **Read and merge.** `read_bindings` runs the plugins together, each in `asyncio.to_thread`, with a 30-minute cache
  (`enricher_read`). `refresh_assets` merges and saves each asset in its own transaction.
- **Who reads.** The weekly job (default Saturday 03:00, `scheduler_profile_read_*`) has a second round after a
  `RATE_LIMITED` refusal. «Aggiorna» uses `POST /assets/profile/refresh`. A save that sets the enrichers starts a
  background read. «Chiedi» (`POST /assets/profile/ask`) merges without saving.
- **Turned off or not configured** (`LIBREFOLIO_ENRICHERS_ENABLED`, `plugin_readiness()`). The binding and the state
  stay, and the read skips the enricher. Each refresh result counts `enrichers_read` (E6c2): the weekly job skips in
  silence, while «Aggiorna» tells the user when nothing was read.

### Frontend

- **Memory.** `profileStore.ts` loads the catalogue once and remembers each read per request; a write forgets the
  asset's reads.
- **The «Profilo» tab.**
  - Classification with a «dati al» day chooser, description, key figure cards and details.
  - «Aggiorna» and «Modifica i dati»; without enrichers, the box «Nessun arricchitore configurato» with «Configura».
  - «Ultime variazioni»: one `ProfileChangesTable` with «Dimentica».
  - «Storia del dato», opened from the history clocks (`ProfileHistoryClock`) or a detail row: a chart only for
    numbers, and the same table.
- **The asset window.** The «Arricchitori» button opens `AssetEnrichersModal`. At creation «Riconosci» runs and the
  automatic «Chiedi» fills the form; everything is saved with the asset (`enrichersOnOpen` opens it for «Configura»).

## Source files

| Role | Path |
|------|------|
| Catalogue of the voices | `backend/app/services/assets/profile/catalogue.py` |
| Read, merge, refresh | `backend/app/services/enrichers/refresh.py` |
| Bindings (config, state) | `backend/app/services/enrichers/bindings.py` |
| Routes (ask, refresh, query, forget) | `backend/app/api/v1/assets/profile.py` |
| Enricher plugins | `backend/app/services/enricher_providers/` |
| Weekly read settings | `backend/app/services/platform/scheduler/settings.py` |
| Profile memory and calls | `frontend/src/lib/features/assets/profile/profileStore.ts` |
| «Profilo» tab | `frontend/src/lib/features/assets/detail/AssetProfileTab.svelte` |
| History window | `frontend/src/lib/features/assets/profile/ProfileHistoryModal.svelte` |
| Changes table | `frontend/src/lib/features/assets/profile/ProfileChangesTable.svelte` |
| Enrichers window | `frontend/src/lib/features/assets/enrichers/AssetEnrichersModal.svelte` |
| Developer guide | `mkdocs_src/docs/developer/architecture/patterns/enricher_plugin_guide.en.md` |
| User guide | `mkdocs_src/docs/user/assets/detail/profile.en.md` |
