# Phase 6: Assets Management — Progress Summary

**Status**: ✅ COMPLETATA (Step 1–4 ✅, Part C ✅, Step 6 ✅, BMC ✅)  
**Durata stimata**: ~8 giorni  
**Priorità**: P0 (MVP)  
**Dipendenze**: Phase 5 (PriceChartFull, Signal Library), Phase 4.8 (user_role)

---

## 📌 Piano di Riferimento

> **Il piano di dettaglio attuale è**: [`plan-phase06-assets.md`](phase-06-subplan/plan-phase06-assets.md)
>
> Sotto-piani di implementazione:
> - [`plan-phase06Step4AssetDetailPage.prompt.md`](phase-06-subplan/plan-phase06Step4AssetDetailPage.prompt.md) — Step 4 (Part 0, A, B, C)
> - [`plan-partBDataEditorUnificato.prompt.md`](phase-06-subplan/Bugfix-Step4/PlanB/plan-partBDataEditorUnificato.prompt.md) — Part B (Data Editor + CSV Import + Test E2E) ✅
> - [`plan-partCCurrencyConversion.prompt.md`](phase-06-subplan/Bugfix-Step4/PlanC/plan-partCCurrencyConversion.prompt.md) — Part C (Currency Conversion + Bugfix + Polish) ✅
> - [`plan-phase06Step6-Polish-Test-Docs.prompt.md`](phase-06-subplan/Bugfix-Step6/plan-phase06Step6-Polish-Test-Docs.prompt.md) — Step 6 (i18n, Test, Docs, Coverage, BMC) ✅

---

## 🎯 Obiettivo

Implementare il sistema grafico per gli asset finanziari: lista con doppia visualizzazione
(card grid + tabella), CRUD con smart search multi-provider, pagina dettaglio con
`PriceChartFull` + segnali tecnici, import CSV prezzi OHLCV, e `AssetMatchingWizard`
condiviso con Phase 7.

**Escluso**: gain/loss, transazioni, regimi fiscali (Phase 7/8).

---

## 📋 Step di Implementazione

| Step | Descrizione | Stima | Status |
|------|-------------|-------|--------|
| **1** | Backend: `params_schema` su provider, fix perf `list_providers`, pre-warm async cache | 0.5g | ✅ |
| **2** | Asset List: dual view (card grid + DataTable), poi replica su FX (FxTable + ViewModeToggle) | 1g | ✅ |
| **2b** | [**Rientro**](../plan-phase06BugfixMigration.prompt.md): bugfix `.toFixed`, BrokerIcon Svelte 5, localStorage user-scoped, FX delete 422, manual-only UX, ViewModeToggle header, bulk prices endpoint + colonne Δ multi-periodo + test migration, test upload, i18n | 0.5g | ✅ |
| **2c** | [**Rientro 2**](phase-06-subplan/plan-phase06Step2cSyncDeleteRefactor.prompt.md): fix chart refresh, stopPropagation azioni tabella, rimuovere edit ridondante + sync/refresh, bulk actions multi-select, blocco 2×2 Assets, fix colonne Δ visibilità | 1g | ✅ |
| **3** | AssetModal + Search + Probe + ScheduledInvestment Engine (12 round). Sotto-piani in [`phase-06-subplan/`](phase-06-subplan/) | 5g | ✅ |
| **4** | Asset Detail: PriceChartFull + segnali + Data Editor + CSV Import + Test E2E + Docs Financial Theory | 2g | ✅ |
| **4b** | [**Part B fix**](phase-06-subplan/Bugfix-Step4/PlanB/plan-partBDataEditorUnificato.prompt.md): B6 test fix (Apple search), perf fix (chunk fallback), B7 polish, B8 docs reorg, B9 portfolio theory | 1.5g | ✅ |
| **4c** | Financial Theory docs: traduzione IT/FR/ES via pipeline AI | 0.5g | ✅ |
| **4d** | [**Infra**] Gallery headless default + traduzioni nav mkdocs (Mutual Fund, Commodities, Other in IT/FR) | - | ✅ |
 **4e**  [**Part C**](../phases/phase-06-subplan/Bugfix-Step4/PlanC/plan-partCCurrencyConversion.prompt.md): Currency conversion backend+frontend, fix docs links, tooltip/measure mobile, tail banner, docker env warning  2g  ✅ 
| **5** | AssetMatchingWizard 3-step (condiviso Phase 7) | 1g | ⏳ |
| **6** | i18n (30 keys × 4 lingue), E2E test, gallery, docs MkDocs | 1g | ⏳ |

---

## 🗂️ File da Creare/Modificare

### Backend (modifiche)

| File | Modifica |
|------|----------|
| `backend/app/services/asset_source.py` | `params_schema` property nella base class |
| `backend/app/services/asset_source_providers/css_scraper.py` | Override `params_schema` |
| `backend/app/services/asset_source_providers/scheduled_investment.py` | Override `params_schema` |
| `backend/app/schemas/provider.py` | `FAProviderParamField` + `FAProviderInfo` esteso |
| `backend/app/api/v1/assets.py` | `list_providers`: filtro `providers` param + fix `supports_search` |
| `backend/app/main.py` | `asyncio.create_task(_prewarm_provider_caches)` in lifespan |

### Frontend (nuovi)

| File | Descrizione |
|------|-------------|
| `src/lib/components/ui/ViewModeToggle.svelte` | Toggle grid/table riusabile |
| `src/lib/components/assets/AssetIcon.svelte` | Icon con fallback chain (pattern BrokerIcon) |
| `src/lib/components/assets/AssetCard.svelte` | Card con mini chart (pattern FxCard) |
| `src/lib/components/assets/AssetTable.svelte` | DataTable wrapper per assets |
| `src/lib/components/assets/AssetModal.svelte` | Create/Edit modale con ModalBase |
| `src/lib/components/assets/AssetSearchAutocomplete.svelte` | Smart search multi-provider |
| `src/lib/components/assets/AssetDataEditorSection.svelte` | DataEditor con colonne OHLCV |
| `src/lib/components/assets/AssetMatchingWizard.svelte` | Wizard 3-step (condiviso Phase 7) |
| `src/lib/components/fx/FxTable.svelte` | DataTable wrapper per FX pairs |
| `src/routes/(app)/assets/[id]/+page.svelte` | Detail page |
| `src/routes/(app)/assets/[id]/+page.ts` | Detail load function |
| `src/routes/(app)/assets/+page.ts` | List load function |

### Frontend (riscritture)

| File | Modifica |
|------|----------|
| `src/routes/(app)/assets/+page.svelte` | Placeholder → dual view page completa |
| `src/routes/(app)/fx/+page.svelte` | Aggiunta toggle grid/table + FxTable |

---

## 📊 Componenti Condivisi Prodotti

| Componente | Riusato in |
|-----------|-----------|
| `ViewModeToggle.svelte` | Assets, FX, future pages |
| `AssetCard.svelte` | Assets list, Phase 8 dashboard |
| `AssetMatchingWizard.svelte` | Assets, **Phase 7 import BRIM** |
| `FxTable.svelte` | FX list page |

---

## ✅ Checklist Completamento

### Backend
- [ ] `params_schema` implementato su tutti i provider
- [ ] `FAProviderInfo` esteso con `params_schema` field
- [ ] `list_providers` fix: no `search("")`, usa `test_search_query`
- [ ] `list_providers` filtro: query param `providers`
- [ ] Pre-warm cache async in `main.py`
- [ ] `./dev.py api sync` completato
- [ ] Test API esistenti passano

### Frontend — Asset List
- [ ] Dual view: card grid + DataTable
- [ ] ViewModeToggle con localStorage persistence
- [ ] Filtri: search, type, currency, active
- [ ] Empty state
- [ ] Click card/row → `/assets/[id]`
- [ ] VIEWER: no edit/delete/add buttons

### Frontend — FX List (aggiornamento)
- [ ] FxTable.svelte con DataTable
- [ ] Toggle grid/table nella pagina FX
- [ ] Colonne FX: pair (flags), rate, variazione, provider, actions

### Frontend — AssetModal
- [ ] AssetSearchAutocomplete funzionante
- [ ] Auto-fill form da search result
- [ ] Auto-assign provider post-create
- [ ] Edit mode (PATCH)
- [ ] ImagePickerWrapper per icon
- [ ] Collapsible identifiers

### Frontend — Asset Detail
- [ ] PriceChartFull con dati da API
- [ ] Segnali tecnici (EMA, MACD, RSI, Bollinger)
- [ ] Edit mode + Measure mode
- [ ] AssetDataEditorSection (OHLCV)
- [ ] CSV import con colonne mappabili
- [ ] Provider assignment con form dinamico (params_schema)
- [ ] Metadata section (readonly + refresh)
- [ ] Responsive layout

### Frontend — AssetMatchingWizard
- [ ] Step 1: search DB (DataTable)
- [ ] Step 2: search providers online
- [ ] Step 3: create manuale
- [ ] Emissione `onselect(asset_id)`
- [ ] Embeddabile standalone + inline

### Qualità
- [ ] i18n completo (30 keys × 4 lingue)
- [ ] E2E tests (~20 scenari)
- [ ] Screenshot gallery (light/dark × desktop/mobile)
- [ ] Documentazione MkDocs
- [ ] Dark mode coerente
- [ ] `npm run build` senza errori

---

## 📝 Note Storiche

### Piano Originale (Legacy — Gennaio 2026)

Il contenuto originale di questo file è stato **sostituito** dal piano aggiornato.
Il vecchio piano prevedeva: `AssetTable.svelte`, `AssetFilters.svelte`, `PriceChart.svelte`
custom, senza riuso della component library Phase 4. Quei componenti sono stati **rimpiazzati**
da `DataTable`, `ModalBase`, `PriceChartFull` etc.

### Aggiornamento Febbraio 2026 (plan-phase05-to-08-upgrade.md §5)

Il master plan `plan-phase05-to-08-upgrade.md` §5 ha ridefinito Phase 6 con:
- `AssetMatchingWizard` condiviso con Phase 7
- `AssetGainLossTable` con metodo fiscale selezionabile
- URL-based filters (`urlFilters.ts`)

### Aggiornamento Marzo 2026 (Piano Attuale)

Il piano corrente (`plan-phase06-assets.md`) include ulteriori evoluzioni:
- **Dual view** (card grid + tabella) per Assets e FX
- **Backend `params_schema`** per form dinamici provider
- **Fix performance** `list_providers` (eliminata `search("")`)
- **Pre-warm async** cache dei provider in `main.py`
- **AssetDataEditorSection** con colonne OHLCV (6 colonne)
- **Gain/loss posticipato** a Phase 7/8 (non serve senza transazioni)
- **urlFilters.ts** escluso (filtri con `$state` locale)


### Aggiornamento Aprile 2026 (Part B completata + Infra)

- **Part B (B1-B9) completata**: Data Editor unificato (2 tab Prices/Events), CSV import generico, test E2E (23+20+8), polish UX (stale toggle, dblclick chart→editor, tooltip mobile, emoji docs links)
- **B8**: Financial Theory docs riorganizzati in 4 sotto-alberi (44 file .en.md), da flat a instruments/technical-analysis/fundamentals/portfolio-theory
- **B9**: Portfolio Theory contenuto completo (8 pagine con formule LaTeX)
- **Infra**: Gallery Playwright headless di default (rimossa dipendenza xvfb-run), nuovo flag `--headed` per debug
- **Traduzioni nav mkdocs.yml**: aggiunte IT/FR per Mutual Fund, Commodities, Other (erano solo in ES)

### Aggiornamento 13 Aprile 2026 (Part C completata + validazione)

- **Part C (C1-C15) completata**: Currency conversion backend+frontend, dead code removal, test coverage, fix infrastrutturali
- **Part C completata**: Currency conversion + post-validation + UX polish + provider core cache → [PlanC/](../phases/phase-06-subplan/Bugfix-Step4/PlanC/)

