# Plan: Phase 5–8 Upgrade & GDPR/Broker Sharing Architecture

**Data creazione**: 25 Febbraio 2026  
**Ultimo aggiornamento**: 25 Febbraio 2026 (aggiunto pre-step verifica, riferimenti incrociati, note per plan di dettaglio)  
**Status**: 🟡 IN CORSO (Phase 4.8 ✅ COMPLETATO, Phase 5 FX 🔄 IN CORSO — sub-plan completati, chain/detail/docs/test pendenti)  
**Dipendenze**: Phase 4 COMPLETATA  
**Stima totale**: ~30 giorni (~6 settimane lavorative, include Phase 4.8)

---

## 1. Overview

Phase 4 (Brokers, Files, Image Crop, ModalBase, code dedup) è completata con 109+ test E2E, 280+ screenshot gallery, e una solida component library. Le fasi 5–8 originali erano "
blande" — tabelle custom, modali custom, nessun chart avanzato, nessun regime fiscale, nessuna aggregazione pesata.

### Motivazione della riscrittura

1. **Modelli DB incompleti**: Manca `share_percentage` su `BrokerUserAccess` (serve per aggregazione portfolio) e `cost_basis_override` su `Transaction` (serve per freeze PMC ai
   trasferimenti).
2. **Component library non sfruttata**: Le fasi originali usano tabelle e modali custom invece di `DataTable`, `ModalBase`, `SearchSelect`, `SimpleSelect`, etc.
3. **Chart avanzati**: Serve un componente chart condiviso con gradiente opacità per dati stale e click-to-edit.
4. **Regimi fiscali**: L'architettura deve supportare FIFO, LIFO, PMC, Select ID — configurabile per broker e utente.
5. **Aggregazione pesata**: Dashboard deve usare `share_percentage` per calcolare NAV/PnL/ROI per utente.
6. **GDPR/Sharing**: Il broker è il contenitore — condividere = dare accesso all'intero storico.

### Principi chiave

- **Tutti i calcoli nel backend** — frontend pura presentazione
- **Riuso component library** — DataTable, ModalBase, SearchSelect, SimpleSelect, ConfirmModal, FileUploader, AssetPickerModal, ImagePickerWrapper, LazyImage
- **i18n completo** (EN/IT/FR/ES) via `./dev.py i18n add`
- **Svelte 5 runes** ($state, $derived, $effect) per tutti i nuovi componenti
- **URL-based filters** (urlFilters.ts) per tutte le tabelle
- **Dark mode** coerente con design system
- **E2E test** per ogni feature critica

### 🗺️ Indice rapido — Riferimenti tra Plan

Questo file è il **Master Plan** per le fasi 5-8. Ogni fase futura avrà un piano di dettaglio dedicato
che verrà creato al momento dell'inizio della fase, partendo dalla sezione corrispondente di questo file.

| Sezione | Contenuto                                                             | Plan dedicato (futuro)                                   |
|---------|-----------------------------------------------------------------------|----------------------------------------------------------|
| §2      | Schema changes (pre-work) — `share_percentage`, `cost_basis_override` | ✅ Completato                                             |
| §3      | API changes (nuovi + modificati)                                      | Distribuito nelle fasi                                   |
| §3.5    | **Phase 4.8** — Broker Sharing GUI                                    | `phases/phase-04-subplan/plan-brokerSharing.md` (✅ completato) |
| §4      | **Phase 5** — FX Management + PriceChartShared                        | `plan-phase05-fx.md` (da creare)                         |
| §5      | **Phase 6** — Assets Management                                       | `plan-phase06-assets.md` (da creare)                     |
| §6      | **Phase 7** — Transactions Management                                 | `plan-phase07-transactions.md` (da creare)               |
| §7      | **Phase 7.5** — File Preview                                          | `plan-phase7b-filePreview.md` (esistente, da aggiornare) |
| §8      | **Phase 8** — Dashboard                                               | `plan-phase08-dashboard.md` (da creare)                  |
| §9      | Spec dettagliata `PriceChartShared`                                   | Incluso nel plan Phase 5                                 |
| §10     | GDPR/Sharing Architecture                                             | Incluso nel plan Phase 4.8                               |
| §11     | Dependency Graph — Componenti condivisi tra fasi                      | Riferimento globale                                      |
| §12     | Timeline stimata e Milestones                                         | Riferimento globale                                      |

---

## 2. Backend Schema Changes (Pre-work — 1 giorno)

### 2.1 `BrokerUserAccess` — Aggiungere `share_percentage`

**File**: `backend/app/db/models.py` (linea ~366)

```python
class BrokerUserAccess(SQLModel, table=True):
    # ...existing fields...
    role: UserRole = Field(default=UserRole.VIEWER)
    share_percentage: Decimal = Field(
        default=Decimal("100"),
        sa_column=Column(
            Numeric(5, 2), nullable=False, default=100,
            info={"check": "share_percentage >= 0 AND share_percentage <= 100"}
        ),
        description="Ownership percentage (0-100%). OWNER defaults to 100%, EDITOR to 0%"
    )
```

**Semantica**:

- `OWNER`: default 100% (può essere ridotto per cointestazione)
- `EDITOR`: default 0% (delegato operativo, es. coniuge o consulente)
- `VIEWER`: default 0% (commercialista, sola lettura)
- La somma dei share% per un broker PUÒ superare 100% (es. coppie dove entrambi vogliono vedere il 100% del valore per motivi di tracking personale) — il sistema mostrerà un
  warning ma non lo impedirà.

### 2.2 `Transaction` — Aggiungere `cost_basis_override`

**File**: `backend/app/db/models.py` (linea ~504)

```python
class Transaction(SQLModel, table=True):
    # ...existing fields...
    cost_basis_override: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(18, 6), nullable=True),
        description="Frozen cost basis for TRANSFER_IN. When set, this value is used "
                    "as the acquisition price instead of calculating from source broker history."
    )
```

**Semantica**:

- `None` per transazioni normali — il backend calcola il costo dalla storia
- Valorizzato per `TRANSFER_IN` — il backend calcola il PMC sul broker sorgente al momento del trasferimento e lo congela qui
- Può essere sovrascritto manualmente (es. Exit Tax, successioni dove si usa il valore di mercato)

### 2.3 `UserSettings` — Aggiungere preferenze fiscali

**File**: `backend/app/db/models.py`

Aggiungere un campo JSON alle preferenze utente per le impostazioni fiscali di default:

```python
# In UserSettings o come campo JSON nella tabella users
fiscal_preferences: Optional[str] = Field(
    default=None,
    sa_column=Column(Text),
    description="JSON: {default_method: 'PMC', per_broker: {1: 'FIFO', 2: 'PMC'}}"
)
```

### 2.4 Migrazione

**File**: `backend/alembic/versions/001_initial.py`

- Aggiungere colonna `share_percentage NUMERIC(5,2) NOT NULL DEFAULT 100` con `CHECK(share_percentage >= 0 AND share_percentage <= 100)` alla tabella `broker_user_access`
- Aggiungere colonna `cost_basis_override NUMERIC(18,6)` alla tabella `transactions`
- Aggiungere colonna `fiscal_preferences TEXT` alla tabella dove risiedono le user settings
- Dopo la modifica: `./dev.py db create-clean` per ricreare il DB da zero

### 2.5 Schema Changes (Pydantic)

**File**: `backend/app/schemas/brokers.py`

- `BRAccessItem`: aggiungere `share_percentage: Decimal`
- `BRAccessCreateRequest`: aggiungere `share_percentage: Decimal = 100`
- `BRAccessUpdateRequest`: aggiungere `share_percentage: Optional[Decimal] = None`

**File**: `backend/app/schemas/transactions.py`

- `TXCreateItem`: aggiungere `cost_basis_override: Optional[Decimal] = None`
- `TXReadItem`: aggiungere `cost_basis_override: Optional[Decimal] = None`
- `TXPatchItem`: aggiungere `cost_basis_override: Optional[Decimal] = None`

### Tasks

- [x] Aggiungere `share_percentage` a `BrokerUserAccess` in models.py ✅ (25 Feb 2026)
- [x] Aggiungere `cost_basis_override` a `Transaction` in models.py ✅ (25 Feb 2026)
- [ ] Aggiungere `fiscal_preferences` alle user settings (→ Phase 7)
- [x] Aggiornare `001_initial.py` con nuove colonne ✅ (25 Feb 2026)
- [x] Aggiornare schemas Pydantic (brokers.py, transactions.py) ✅ (25 Feb 2026)
- [x] Aggiornare populate_mock_data con share_percentage di esempio ✅ (25 Feb 2026)
- [x] `./dev.py db create-clean` + `./dev.py test all` → tutti verdi ✅ (25 Feb 2026)
- [x] `./dev.py api sync` per rigenerare client TypeScript ✅ (25 Feb 2026)

**Note implementazione (25 Feb 2026)**:

- `share_percentage`: NUMERIC(5,2) con CHECK constraint, default 100, in models.py, schemas, broker_service, API
- `cost_basis_override`: NUMERIC(18,6) nullable, in models.py, schemas, transaction_service
- 16/16 API test passano, 0 errori frontend check
- `fiscal_preferences` rimandato a Phase 7 (dipende da endpoint `/settings/fiscal`)

---

## 3. Backend API Changes

### 3.1 Nuovi Endpoint

| Endpoint                             | Metodo | Fase      | Descrizione                                        |
|--------------------------------------|--------|-----------|----------------------------------------------------|
| `GET /api/v1/portfolio/overview`     | GET    | Phase 8   | Aggregazione NAV/PnL pesata per share_percentage   |
| `GET /api/v1/portfolio/gains`        | GET    | Phase 6/8 | Gain/loss per transazione con metodo selezionabile |
| `POST /api/v1/transactions/validate` | POST   | Phase 7   | Validazione pre-import (over-sell, regole)         |
| `GET /api/v1/settings/fiscal`        | GET    | Phase 7   | Preferenze regimi fiscali utente                   |
| `PATCH /api/v1/settings/fiscal`      | PATCH  | Phase 7   | Aggiorna preferenze fiscali                        |

### 3.2 Endpoint Modificati

| Endpoint                                      | Modifica                    | Fase     |
|-----------------------------------------------|-----------------------------|----------|
| `POST /api/v1/brokers/{id}/access`            | Accetta `share_percentage`  | Pre-work |
| `PATCH /api/v1/brokers/{id}/access/{user_id}` | Aggiorna `share_percentage` | Pre-work |
| `GET /api/v1/brokers/{id}/access`             | Ritorna `share_percentage`  | Pre-work |

### 3.3 Logica di Aggregazione Portfolio (Phase 8)

```python
# Pseudocode per GET /portfolio/overview
async def get_portfolio_overview(user_id: int):
    accesses = get_user_broker_accesses(user_id)
    total_nav = Decimal("0")
    total_pnl = Decimal("0")
    total_invested = Decimal("0")
    
    for access in accesses:
        broker_nav = calculate_broker_nav(access.broker_id)
        broker_pnl = calculate_broker_pnl(access.broker_id)
        broker_invested = calculate_broker_invested(access.broker_id)
        weight = access.share_percentage / Decimal("100")
        
        total_nav += broker_nav * weight
        total_pnl += broker_pnl * weight
        total_invested += broker_invested * weight
    
    roi = (total_pnl / total_invested * 100) if total_invested > 0 else Decimal("0")
    return PortfolioOverview(nav=total_nav, pnl=total_pnl, roi=roi)
```

---

## 3.5 Phase 4.8 — Broker Sharing GUI (PRIMA di Phase 5)

**Durata**: ~5 giorni  
**Dipendenze**: Schema pre-work (share_percentage GIÀ implementato)  
**Status**: ✅ COMPLETATO (1 Mar 2026)  
**Piano dettagliato**: `phases/phase-04-subplan/plan-brokerSharing.md`

Senza la GUI di sharing, il sistema multi-utente resta inutilizzabile dall'utente.
Questo step DEVE essere completato prima di Phase 5 (FX).

### Cosa include

1. **Backend**: Nuovo endpoint `GET /api/v1/users/search` per cercare utenti
2. **Backend**: Aggiungere `avatar_url` a `BRAccessItem`, `user_role` a `BRSummary`
3. **Frontend**: Nuovo componente `BrokerSharingModal.svelte` con DataTable, SearchSelect, ConfirmModal
4. **Frontend**: Bottone "Share" in broker detail (solo OWNER)
5. **i18n**: ~15 chiavi per sharing in 4 lingue
6. **E2E test**: ~14 scenari test
7. **Gallery**: Screenshot della modale sharing

### File da creare

```
backend/app/api/v1/users.py                                    # Endpoint search users
backend/app/schemas/users.py                                    # UserSearchItem schema
backend/test_scripts/test_api/test_users_search.py              # API tests
frontend/src/lib/components/brokers/BrokerSharingModal.svelte   # Modale sharing
```

### Tasks

- [x] Backend: endpoint search users + schema + service
- [x] Backend: avatar_url in BRAccessItem, user_role in BRSummary
- [x] Frontend: BrokerSharingModal con DataTable inline edit
- [x] Frontend: bottone Share in broker detail
- [x] i18n: chiavi sharing in EN/IT/FR/ES
- [x] E2E tests
- [x] Gallery screenshots

---

## 4. Phase 5 — FX Management (Riscritta)

**Durata**: ~4 giorni  
**Dipendenze**: Schema changes (pre-work), PriceChartShared, **Phase 4.8 (Broker Sharing GUI)**  
**Status**: 🔄 IN CORSO — Pagina lista FX ✅, sub-plan completati, chain/detail/docs/test pendenti.

> **📌 Plan modulari Phase 5** (soppiantano il vecchio `plan-phase05Fx.prompt.md`, ora in `phases/phase-05-subplan/05FX_outofdate_plan/`):
> 1. `plan-fxConversionChain.prompt.md` ✅ — Route-based multi-step conversion (data model → frontend)
> 2. `plan-fxDetailPageRedesign.prompt.md` ✅ — Redesign completo: chart unificato, DataEditor duale, MeasureSignal, pannelli inline, provider edit
> 3. `plan-fxTestingCleanup.prompt.md` ✅ — E2E Playwright, unit test, i18n audit, gallery, JWT migration
> 4. `plan-fxDocumentation.prompt.md` ✅ — MkDocs i18n globale, documentazione utente, traduzioni
> Tutti i plan completati sono in `phases/phase-05-subplan/`.
> Il componente PriceChartShared (§5.0) DEVE essere creato come primo step (§9 per la spec dettagliata).
> Il gradiente opacità per dati stale deve seguire la formula: `max(0.3, 1.0 - staleDays * 0.15)`.
> Verificare che `user_role` dal broker condizioni i permessi (VIEWER = sola lettura chart, no sync).

### 5.0 Chart Component (Shared) — 1 giorno

Componente condiviso tra FX e Assets. DEVE essere implementato per primo.

#### Tasks

- [ ] Creare `src/lib/components/charts/PriceChartShared.svelte`
- [ ] Installare `echarts` nel frontend: `cd frontend && npm install echarts`
- [ ] Implementare gradiente opacità per dati stale
- [ ] Implementare click-to-edit su data point
- [ ] Implementare range selector (1W, 1M, 3M, 6M, 1Y, ALL)
- [ ] Dark mode support
- [ ] Responsive (resize observer)

#### Chart Gradient Spec — Dati Stale

Quando il backend ritorna un price point, include info sulla "freschezza" del dato. Se un dato del lunedì è in realtà il dato di venerdì (perché il mercato era chiuso), la linea
deve sfumare:

```typescript
// Props del componente
interface PricePoint {
    date: string;           // ISO date
    value: number;          // price/rate
    staleDays?: number;     // 0 = fresh, 1 = 1 day old, etc.
    source?: string;        // provider key
}

interface PriceChartProps {
    data: PricePoint[];
    currency: string;
    onEdit?: (date: string, newValue: number) => void;
    showGradient?: boolean;     // default true
    rangeOptions?: string[];    // default ['1W','1M','3M','6M','1Y','ALL']
    editable?: boolean;         // default false
    title?: string;
}
```

**Implementazione gradiente**: ECharts `visualMap` con segmenti `lineStyle.opacity` calcolata come `max(0.3, 1.0 - staleDays * 0.15)`. Dopo ~5 giorni stale, opacità fissa a 0.3.

#### Click-to-Edit

- Click su data point → tooltip espanso con input numerico
- Conferma → chiama `onEdit(date, newValue)` callback
- Il parent decide se chiamare l'API (FX o Asset)

#### Props

```svelte
<PriceChartShared 
    data={priceData}
    currency="EUR"
    onEdit={handleEdit}
    editable={true}
    showGradient={true}
    title={$t('fx.chart.title')}
/>
```

### 5.1 FX Currencies Grid — 0.5 giorni

#### Tasks

- [ ] Riscrivere `src/routes/(app)/fx/+page.svelte` con layout a tab (provider) + chart + pair sources
- [ ] Creare `src/lib/components/fx/CurrencyGrid.svelte` con card e flag emoji
- [ ] Usare `SearchSelect` per filtro provider
- [ ] i18n per tutti i label

### 5.2 FX Rate Chart — 0.5 giorni

#### Tasks

- [ ] Creare `src/lib/components/fx/FxRateChart.svelte` wrapper per `PriceChartShared`
- [ ] Integrazione con `GET /fx/currencies/rate` per storico
- [ ] Click-to-edit → chiama `POST /fx/currencies/rate`
- [ ] Gradiente su weekend gaps

### 5.3 Pair Sources CRUD — 1 giorno

#### Tasks

- [ ] Creare `src/lib/components/fx/FxPairSourcesSection.svelte` con `DataTable`
- [ ] Column: Base (flag+code), Quote (flag+code), Provider (badge), Priority (number)
- [ ] Sorting su tutte le colonne
- [ ] Add button → `ModalBase` con `SearchSelect` per valute + `SimpleSelect` per provider
- [ ] Edit in-place o via modale
- [ ] Delete con `ConfirmModal`
- [ ] Priority con drag-reorder o input numerico

### 5.4 Sync Tool — 1 giorno

#### Tasks

- [ ] Creare `src/lib/components/fx/FxSyncModal.svelte` con `ModalBase`
- [ ] Date range picker (start + end)
- [ ] Multi-currency selector (chips)
- [ ] Provider override (opzionale)
- [ ] **Warning banner**: "Questa operazione sovrascriverà i tassi esistenti nel range selezionato"
- [ ] Progress bar durante sync
- [ ] Risultato: "N rates fetched, M changed"
- [ ] Conferma con `ConfirmModal` (arancione/warning)

### Componenti (nuovi per Phase 5)

| Componente                    | Descrizione                     | Riusa                                 |
|-------------------------------|---------------------------------|---------------------------------------|
| `PriceChartShared.svelte`     | Chart condiviso FX/Assets       | ECharts (nuovo)                       |
| `FxRateChart.svelte`          | Wrapper FX per PriceChartShared | PriceChartShared                      |
| `FxPairSourcesSection.svelte` | CRUD pair sources               | DataTable, ConfirmModal, ModalBase    |
| `FxSyncModal.svelte`          | Dialog sync date range          | ModalBase, SimpleSelect, ConfirmModal |
| `CurrencyGrid.svelte`         | Grid valute con flag            | SearchSelect                          |

### API Endpoints

| Endpoint                                       | Metodo          | Descrizione             |
|------------------------------------------------|-----------------|-------------------------|
| `/api/v1/fx/currencies?provider={p}`           | GET             | Valute per provider     |
| `/api/v1/utilities/currencies?language={lang}` | GET             | Nomi localizzati + flag |
| `/api/v1/fx/providers/pair-sources`            | GET/POST/DELETE | CRUD pair sources       |
| `/api/v1/fx/currencies/sync`                   | GET             | Sync rates              |
| `/api/v1/fx/currencies/rate`                   | POST            | Manual rate entry       |

### i18n Keys

```
fx.title, fx.currencies, fx.pair_sources, fx.sync.title, fx.sync.warning_overwrite,
fx.sync.date_range, fx.sync.start_date, fx.sync.end_date, fx.sync.currencies,
fx.sync.provider_override, fx.sync.syncing, fx.sync.result, fx.sync.rates_fetched,
fx.sync.rates_changed, fx.chart.title, fx.chart.stale_data, fx.chart.edit_point,
fx.pair.base, fx.pair.quote, fx.pair.provider, fx.pair.priority,
fx.pair.add, fx.pair.edit, fx.pair.delete_confirm,
fx.manual.title, fx.manual.date, fx.manual.rate
```

### E2E Test Ideas

- [ ] Grid valute visibile con flag corretti per ogni provider tab
- [ ] Add pair source → appare in DataTable
- [ ] Edit/delete pair source
- [ ] Sync con date range → progress → risultato
- [ ] Chart mostra gradiente su weekend gap
- [ ] Click chart point → editor visibile (se editable)
- [ ] Range selector cambia periodo visualizzato
- [ ] Dark mode coerente

---

## 5. Phase 6 — Assets Management (Riscritta)

**Durata**: ~5 giorni  
**Dipendenze**: Phase 5 (PriceChartShared), Schema changes, **Phase 4.8 (user_role per permessi)**  
**Status**: ⏳ TODO

> **📌 Nota per il plan di dettaglio futuro**: Quando si arriva a creare il plan dedicato per Phase 6,
> ripartire da questa sezione (§5). Include: Asset list con DataTable e filtri URL-based, AssetModal CRUD
> con ImagePickerWrapper per icona, AssetSearchAutocomplete multi-provider, AssetDetail con PriceChartShared
> (riusato da Phase 5), AssetGainLossTable con metodo selezionabile (PMC formale + FIFO/LIFO analitico),
> AssetMatchingWizard a 3 step (search DB → search providers → create new).
> Il wizard di matching è **CONDIVISO** con Phase 7 (import BRIM), quindi deve essere progettato come
> componente standalone riusabile. Il regime fiscale mostra un **disclaimer PMC** per conformità italiana.
> `user_role` condiziona: VIEWER non può creare/editare asset, EDITOR/OWNER sì.

### Nota su Gain/Loss e Regimi Fiscali

Il dettaglio asset mostra:

- **Dashboard generale + reportistica tasse (Italia)**: sempre **Costo Medio Ponderato (CMP/PMC)**
- **Vista analitica UX (dettaglio vendita)**: metodo selezionabile (**FIFO** default per valore psicologico)
- **Disclaimer sempre presente**: "I calcoli fiscali usano sempre il Prezzo Medio di Carico"
- Il selettore metodo cambia solo la vista, NON il calcolo fiscale

### 6.1 Asset List — 1 giorno

#### Tasks

- [ ] Riscrivere `src/routes/(app)/assets/+page.svelte` con `DataTable`
- [ ] Colonne: Icon (ImageCell con preview), Name, Type (badge), Currency (flag), Identifiers, Provider (badge), Status, Actions
- [ ] Column filters: search (text), type (select), currency (select), active (toggle)
- [ ] URL-based filters con `urlFilters.ts`
- [ ] Empty state se nessun asset
- [ ] Sorting su tutte le colonne

### 6.2 Add/Edit Asset — 1.5 giorni

#### Tasks

- [ ] Creare `src/lib/components/assets/AssetModal.svelte` (create+edit) con `ModalBase`
- [ ] Smart search multi-provider: `AssetSearchAutocomplete.svelte`
- [ ] Provider toggle checkboxes (yfinance, JustETF, etc.)
- [ ] Auto-fill form da risultato search
- [ ] `ImagePickerWrapper` per icon_url
- [ ] `SearchSelect` per currency
- [ ] `SimpleSelect` per asset_type
- [ ] Collapsible identifiers section (ISIN, Ticker, CUSIP, SEDOL, FIGI)
- [ ] Validazione display_name unico

### 6.3 Asset Detail Page — 1.5 giorni

#### Tasks

- [ ] Creare `src/routes/(app)/assets/[id]/+page.svelte` con header + chart + metadata
- [ ] **PriceChartShared** con dati da `GET /assets/prices/{id}`, gradiente, click-to-edit
- [ ] Provider assignment section con `ModalBase`
- [ ] **Per-transaction gain/loss table** (`AssetGainLossTable.svelte`):
    - DataTable con colonne: Date, Type (BUY/SELL), Quantity, Price, Current Value, Gain/Loss (%), Gain/Loss (abs)
    - Dati da `GET /portfolio/gains?asset_id=X&method=PMC`
    - Selettore metodo (PMC default, FIFO opzionale) — solo visualizzazione analitica
    - Disclaimer: "I calcoli fiscali usano sempre il Prezzo Medio di Carico"
- [ ] Metadata section: identifiers, classification, provider info

### 6.4 Asset Matching Wizard — 1 giorno

#### Tasks

- [ ] Creare `src/lib/components/assets/AssetMatchingWizard.svelte`
- [ ] Flow a 3 step:
    1. **Search DB**: `DataTable` con asset esistenti, ricerca per nome/ticker/ISIN
    2. **Search Providers**: risultati da `GET /assets/provider/search?q=...`
    3. **Create New**: form manuale (stesso di AssetModal)
- [ ] Usabile standalone E embedded nel BRIM import (Phase 7)
- [ ] Ritorna l'asset_id selezionato/creato

### Componenti (nuovi per Phase 6)

| Componente                       | Descrizione                 | Riusa                                                     |
|----------------------------------|-----------------------------|-----------------------------------------------------------|
| `AssetModal.svelte`              | Create/Edit asset           | ModalBase, SearchSelect, SimpleSelect, ImagePickerWrapper |
| `AssetSearchAutocomplete.svelte` | Smart search multi-provider | SearchSelect pattern                                      |
| `AssetGainLossTable.svelte`      | Gain/loss per transazione   | DataTable                                                 |
| `AssetMatchingWizard.svelte`     | Flow search → create asset  | DataTable, ModalBase, SearchSelect                        |

### API Endpoints

| Endpoint                                        | Metodo     | Descrizione          |
|-------------------------------------------------|------------|----------------------|
| `/api/v1/assets/query`                          | GET        | Lista con filtri     |
| `/api/v1/assets`                                | POST/PATCH | Create/Update        |
| `/api/v1/assets?ids={id}`                       | GET        | Dettaglio            |
| `/api/v1/assets/prices/{id}`                    | GET        | Price history        |
| `/api/v1/assets/provider/search`                | GET        | Smart search esterno |
| `/api/v1/assets/provider`                       | POST       | Assign provider      |
| `/api/v1/portfolio/gains?asset_id=X&method=PMC` | GET        | Gain/loss per tx     |

### i18n Keys

```
assets.title, assets.add, assets.edit, assets.delete_confirm,
assets.search.placeholder, assets.search.providers,
assets.detail.header, assets.detail.provider, assets.detail.prices,
assets.detail.metadata, assets.detail.identifiers,
assets.gains.title, assets.gains.per_transaction, assets.gains.method,
assets.gains.disclaimer_pmc, assets.gains.unrealized, assets.gains.realized,
assets.matching.title, assets.matching.search_db, assets.matching.search_providers,
assets.matching.create_new, assets.matching.select,
assets.chart.stale_gradient, assets.chart.edit_point
```

### E2E Test Ideas

- [ ] Lista asset con filtri funzionanti
- [ ] Smart search trova asset da yfinance
- [ ] Auto-fill form da search result
- [ ] Create/Edit/Delete asset
- [ ] Dettaglio con chart e gradient su weekend
- [ ] Click-to-edit su data point
- [ ] Gain/loss table mostra valori
- [ ] Asset matching wizard: search DB → select
- [ ] Asset matching wizard: search providers → create

---

## 6. Phase 7 — Transactions Management (Riscritta)

**Durata**: ~8 giorni  
**Dipendenze**: Phase 4 (Brokers), Phase 6 (Assets, AssetMatchingWizard), **Phase 4.8 (sharing permissions)**  
**Status**: ⏳ TODO  
**Complessità**: ⚠️ ALTA

> **📌 Nota per il plan di dettaglio futuro**: Quando si arriva a creare il plan dedicato per Phase 7,
> ripartire da questa sezione (§6). È la fase PIÙ COMPLESSA. Include:
> - **Transaction list** con DataTable e paginazione server-side (potenzialmente migliaia di tx)
> - **TransactionModal** con form dinamico per tipo (BUY/SELL/DEPOSIT/WITHDRAWAL/DIVIDEND/TRANSFER/FX_CONVERSION)
> - **FiscalRegimeSelect** (FIFO/LIFO/PMC/Select ID) — configurabile per utente e per broker
> - **SellBuyMatchingPanel** che mostra il matching sell→buy per il metodo selezionato
> - **CashSplitModal** per tracciare fonti dei soldi (stipendio, regalo, vendita)
> - **MultiImportWizard** a 5 step (Upload → Parse → Review → Validate → Import) con AssetMatchingWizard inline
> - **ValidateImportButton** con POST /transactions/validate per verificare over-sell, duplicati, errori
> - **cost_basis_override** usato per TRANSFER_IN (congelamento PMC dal broker sorgente)
> - **fiscal_preferences** in UserSettings (§2.3) — backend endpoint GET/PATCH /settings/fiscal
> - `user_role` condiziona: VIEWER non può creare/editare tx, EDITOR/OWNER sì

### Note Architetturali Chiave

**Trasferimenti tra Broker (Congelamento Fiscale)**:

- I trasferimenti di asset non innescano evento tassabile
- `TRANSFER_OUT` sul Broker A + `TRANSFER_IN` sul Broker B
- Il PMC dell'asset è calcolato sul Broker A al momento esatto del trasferimento
- Il valore viene "congelato" nel campo `cost_basis_override` della `TRANSFER_IN`
- Da quel momento il Broker B usa quel valore come costo iniziale — nessuna query al Broker A
- Gestisce anche Exit Tax e successioni (sovrascrittura manuale con valore di mercato)

**Regimi Fiscali Configurabili**:

- Supporto FIFO, LIFO, PMC, Select ID — per broker e per utente
- Default utente configurabile in Settings → Preferences
- Override per broker configurabile in BrokerModal → sezione avanzata
- In Italia: **PMC obbligatorio** per calcolo fiscale formale
- In USA: **FIFO** o **Select ID** a scelta del contribuente

**Over-Sell Protection**:

- Il backend valida che non si vendano più quote di quelle possedute
- Il vincolo si estende nell'import: non vendere asset linkati già esauriti
- Per PMC: no lotti, solo quantità totale
- Per FIFO/LIFO/Select ID: lotti specifici

**Cash Split**:

- Per tracciare fonti dei soldi (es. stipendio vs. regalo vs. vendita)
- Split a livello di sotto-transazioni collegate alla transazione padre
- Il padre mantiene l'integrità per evitare doppio import

### 7.1 Transaction List — 1.5 giorni

#### Tasks

- [ ] Riscrivere `src/routes/(app)/transactions/+page.svelte` con `DataTable`
- [ ] Colonne: Date, Type (badge colorato), Asset (link), Quantity (+/- colorato), Cash (+/- colorato), Broker (badge), Tags, Description, Actions
- [ ] Column filters: date range, type (multi-select), broker (select), asset (search), tags
- [ ] URL-based filters con `urlFilters.ts`
- [ ] Paginazione server-side (se >1000 tx)
- [ ] Sorting su tutte le colonne
- [ ] Badge colori per tipo transazione

### 7.2 Add/Edit Transaction — 1.5 giorni

#### Tasks

- [ ] Creare `src/lib/components/transactions/TransactionModal.svelte` con `ModalBase`
- [ ] Form dinamico basato su tipo:
    - BUY/SELL: asset (SearchSelect) + quantity + amount + currency + date
    - DEPOSIT/WITHDRAWAL: amount + currency + date
    - DIVIDEND/INTEREST: asset (opzionale) + amount + currency + date
    - TRANSFER: quantity + asset + linked tx (SearchSelect) + cost_basis_override
    - FX_CONVERSION: amount + currency (from/to) + linked tx
    - ADJUSTMENT: quantity + asset
- [ ] `BrokerSearchSelect` per broker
- [ ] `SearchSelect` per asset
- [ ] Date picker nativo
- [ ] Tags input (comma separated)
- [ ] **Cost Basis Override field**: visibile solo per TRANSFER_IN, pre-compilato con PMC dal backend
- [ ] Validation client-side + feedback errori

### 7.3 Fiscal Regime Settings — 1 giorno

#### Tasks

- [ ] Aggiungere sezione "Fiscal Preferences" in Settings → Preferences
- [ ] `FiscalRegimeSelect.svelte` con `SimpleSelect`: FIFO, LIFO, PMC, Select ID
- [ ] Default per utente (in UserSettings/fiscal_preferences)
- [ ] Override per broker (in BrokerModal → sezione avanzata)
- [ ] Tooltip esplicativo per ogni metodo
- [ ] Disclaimer: "Il calcolo fiscale formale usa sempre PMC per conformità italiana"
- [ ] Backend: `GET/PATCH /settings/fiscal`

### 7.4 Sell-Buy Matching — 1 giorno

#### Tasks

- [ ] Creare `src/lib/components/transactions/SellBuyMatchingPanel.svelte`
- [ ] Per PMC: mostra solo "Prezzo Medio di Carico: X€" — nessun matching
- [ ] Per FIFO/LIFO: mostra matching algoritmico calcolato dal backend (read-only DataTable con lotti associati)
- [ ] Per Select ID: `DataTable` con lotti disponibili + selezione utente
- [ ] Visualizzazione link `related_transaction_id`: freccia visiva sell→buy(s)
- [ ] Integrazione nel TransactionModal quando type=SELL

### 7.5 Cash Split — 0.5 giorni

#### Tasks

- [ ] Creare `src/lib/components/transactions/CashSplitModal.svelte` con `ModalBase`
- [ ] Per DEPOSIT/WITHDRAWAL: possibilità di aggiungere N righe split
- [ ] Ogni riga: amount + description (fonte/destinazione)
- [ ] Vincolo: Σ(split amounts) = amount transazione padre
- [ ] Validazione in tempo reale
- [ ] A DB: transazione padre + sub-transazioni con link (evita doppio import)

### 7.6 Multi-File Multi-Broker Import — 1.5 giorni

#### Tasks

- [ ] Creare `src/lib/components/transactions/MultiImportWizard.svelte`
- [ ] Step 1 — **Upload**: `FileUploader` per N file, per ognuno: `BrokerSearchSelect` + `ImportPluginSelect`
- [ ] Step 2 — **Parse**: backend parsa tutti i file, ritorna transazioni raggruppate per file/broker
- [ ] Step 3 — **Review**: DataTable con tutte le transazioni parsate, per ogni riga con asset non trovato → `AssetMatchingWizard` inline
- [ ] Step 4 — **Validate**: bottone `ValidateImportButton` → `POST /transactions/validate` → errori/warning mostrati
- [ ] Step 5 — **Import**: conferma e commit
- [ ] Progress bar per ogni step
- [ ] Back button per tornare a step precedente

### 7.7 Validate Button — 0.5 giorni

#### Tasks

- [ ] Creare `src/lib/components/transactions/ValidateImportButton.svelte`
- [ ] Chiama `POST /api/v1/transactions/validate` con la lista di transazioni
- [ ] Mostra risultati: ✅ OK, ⚠️ Warning (lista), ❌ Error (lista bloccante)
- [ ] Warning: transazioni già importate (duplicati potenziali)
- [ ] Error: over-sell, currency mismatch, date impossibili
- [ ] Se errori → import disabilitato finché non risolti

### 7.8 Over-Sell Protection — 0.5 giorni

#### Tasks

- [ ] Backend: estendere validazione per impedire vendita di più quote di quelle possedute
- [ ] Frontend: mostra warning nell'import wizard se una sell supera la posizione
- [ ] Considerare il metodo fiscale: PMC non ha lotti, FIFO/LIFO/Select ID sì
- [ ] Mostrare saldo disponibile al momento della vendita

### Componenti (nuovi per Phase 7)

| Componente                    | Descrizione              | Riusa                                                           |
|-------------------------------|--------------------------|-----------------------------------------------------------------|
| `TransactionModal.svelte`     | Create/Edit transazione  | ModalBase, SearchSelect, BrokerSearchSelect                     |
| `FiscalRegimeSelect.svelte`   | Selettore regime fiscale | SimpleSelect                                                    |
| `SellBuyMatchingPanel.svelte` | Matching sell→buy        | DataTable, SearchSelect                                         |
| `CashSplitModal.svelte`       | Split cash movements     | ModalBase, DataTable                                            |
| `MultiImportWizard.svelte`    | Import multi-file wizard | FileUploader, BrokerSearchSelect, ImportPluginSelect, DataTable |
| `ValidateImportButton.svelte` | Validate pre-import      | ConfirmModal                                                    |

### API Endpoints

| Endpoint                                        | Metodo    | Descrizione                      |
|-------------------------------------------------|-----------|----------------------------------|
| `/api/v1/transactions`                          | GET       | Lista con filtri + paginazione   |
| `/api/v1/transactions`                          | POST      | Create (singola o batch)         |
| `/api/v1/transactions`                          | PATCH     | Update                           |
| `/api/v1/transactions`                          | DELETE    | Delete (singola o batch)         |
| `/api/v1/transactions/types`                    | GET       | Lista tipi disponibili           |
| `/api/v1/transactions/validate`                 | POST      | **NUOVO** Validazione pre-import |
| `/api/v1/settings/fiscal`                       | GET/PATCH | **NUOVO** Preferenze fiscali     |
| `/api/v1/portfolio/gains?asset_id=X&method=PMC` | GET       | Gain/loss per matching           |

### i18n Keys

```
tx.title, tx.add, tx.edit, tx.delete_confirm,
tx.type.buy, tx.type.sell, tx.type.dividend, tx.type.interest,
tx.type.deposit, tx.type.withdrawal, tx.type.fee, tx.type.tax,
tx.type.transfer, tx.type.fx_conversion, tx.type.adjustment,
tx.fiscal.title, tx.fiscal.fifo, tx.fiscal.lifo, tx.fiscal.pmc, tx.fiscal.select_id,
tx.fiscal.disclaimer_pmc, tx.fiscal.tooltip_fifo, tx.fiscal.tooltip_lifo,
tx.fiscal.tooltip_pmc, tx.fiscal.tooltip_select_id,
tx.matching.title, tx.matching.linked_buy, tx.matching.no_matching_pmc,
tx.matching.select_lot, tx.matching.available_quantity,
tx.split.title, tx.split.source, tx.split.add_row, tx.split.total_must_match,
tx.import.title, tx.import.multi_file, tx.import.step_upload,
tx.import.step_parse, tx.import.step_review, tx.import.step_validate,
tx.import.step_import, tx.import.validate, tx.import.validate_ok,
tx.import.validate_warning, tx.import.validate_error,
tx.import.oversell_warning, tx.import.duplicate_warning,
tx.transfer.cost_basis_override, tx.transfer.cost_basis_frozen
```

### E2E Test Ideas

- [ ] Lista transazioni con tutti i filtri
- [ ] Create transazione BUY con tutti i campi
- [ ] Create TRANSFER con cost_basis_override
- [ ] Fiscal select cambia visualizzazione matching
- [ ] SellBuyMatching mostra lotti per FIFO
- [ ] SellBuyMatching mostra solo PMC per PMC method
- [ ] Cash split: somma deve tornare
- [ ] Multi-file import wizard: upload → parse → review → validate → import
- [ ] Validate con over-sell → errore bloccante
- [ ] Validate con duplicato → warning
- [ ] Asset matching inline nell'import

---

## 7. Phase 7.5 — File Preview (Spostata da Phase 4.9)

**Durata**: ~2 giorni  
**Dipendenze**: Phase 7 (tutte le entità disponibili per preview contestuale)  
**Status**: 📋 PIANIFICATO  
**Riferimento**: `plan-phase7b-filePreview.md`

> **📌 Nota per il plan di dettaglio futuro**: Quando si arriva a creare il plan dedicato per Phase 7.5,
> ripartire da `plan-phase7b-filePreview.md` (piano esistente) + questa sezione. Il piano originale va
> aggiornato per: usare `PriceChartShared` per preview serie storiche CSV, usare `DataTable` per preview
> tabellari, usare `ModalBase` per la modale di preview. Integrare in Files page (entrambi i tab) e
> Broker Detail. Il contesto è ora completo: brokers, assets, transactions, FX sono tutti disponibili
> per dare significato alle preview dei file BRIM.

### Motivazione dello spostamento

Il File Preview ha più senso dopo Phase 7 perché:

1. I file BRIM ora hanno transazioni parsate da mostrare in preview
2. I CSV possono avere colonne matchate con asset/broker
3. Il contesto completo (brokers, assets, transactions, FX) è disponibile

### Piano esistente

Vedi `plan-phase7b-filePreview.md` per il piano dettagliato. Da aggiornare:

- Usare `PriceChartShared` per preview di serie storiche in CSV
- Usare `DataTable` per preview tabellari
- Usare `ModalBase` per la modale di preview
- Integrare in Files page (entrambi i tab) e Broker Detail

---

## 8. Phase 8 — Dashboard (Riscritta)

**Durata**: ~5 giorni  
**Dipendenze**: Phase 5, 6, 7 (tutti i dati + aggregazione), **Phase 4.8 (share_percentage per aggregazione)**  
**Status**: ⏳ TODO

> **📌 Nota per il plan di dettaglio futuro**: Quando si arriva a creare il plan dedicato per Phase 8,
> ripartire da questa sezione (§8). È la fase che AGGREGA tutto il lavoro precedente. Include:
> - **KPI Cards** con NAV/PnL/ROI calcolati con `share_percentage` pesato (formula: §8 intro)
> - **PortfolioChart** con ECharts: due serie (investito vs mercato), range selector
> - **AssetDualAxisChart** con dual Y-axis: prezzo asset a sinistra, gain/loss per transazione a destra,
    > linea cumulativa con area, sell events come markPoints (frecce ↓)
> - **AnalyticsMethodSelect** per FIFO/LIFO/PMC — solo vista analitica, disclaimer PMC
> - **AllocationDonut** con raggruppamento per asset_type
> - **RecentTransactions** con DataTable compatto (ultime 10 tx)
> - **QuickActions**: Add Transaction, Import Files, Sync FX, Sync Prices
> - L'aggregazione usa valori assoluti pesati, MAI la media delle percentuali ROI
> - EDITOR con share 0% → il broker NON compare nel Net Worth
> - VIEWER con share 0% → vede tx ma non impatta il patrimonio
> - Riusa: PriceChartShared (Phase 5), FiscalRegimeSelect (Phase 7), DataTable, ModalBase

### Nota su Aggregazione Pesata (GDPR/Sharing)

L'aggregazione portfolio DEVE usare valori assoluti pesati, MAI la media delle percentuali:

```
NAV_utente = Σ(NAV_broker × share_percentage / 100)
PnL_utente = Σ(PnL_broker × share_percentage / 100)  
ROI_globale = PnL_utente / Invested_utente × 100
```

- Un EDITOR con share 0% → il broker NON compare nel suo Net Worth
- Un VIEWER con share 0% → vede le transazioni ma non impatta il suo patrimonio
- Un OWNER con share 50% (cointestazione) → il broker pesa metà sul bilancio
- Se 2 co-proprietari hanno entrambi 100% → warning "sovrastima patrimonio" (già gestito in Phase 4.8)

### 8.1 KPI Cards — 1 giorno

#### Tasks

- [ ] Creare `src/lib/components/dashboard/KPICard.svelte`
- [ ] **NAV Card**: `NAV_user = Σ(NAV_broker × share_percentage/100)` — dal backend
- [ ] **PnL Card**: `PnL_user = Σ(PnL_broker × share_percentage/100)` — dal backend
- [ ] **ROI Card**: calcolato su valori assoluti aggregati (NON media di percentuali)
- [ ] **Cash Card**: cash totale pesato con breakdown per valuta
- [ ] Trend arrow (↑/↓) + variazione % giornaliera
- [ ] Period selector (1M, 3M, 6M, 1Y, ALL) integrato nella card
- [ ] Breakdown collapsible (per broker)
- [ ] Dark mode completo

### 8.2 Portfolio Growth Chart — 1 giorno

#### Tasks

- [ ] Creare `src/lib/components/dashboard/PortfolioChart.svelte`
- [ ] Due serie: "Investito" (area grigia) vs "Mercato" (area verde)
- [ ] Dati aggregati pesati da `GET /portfolio/overview`
- [ ] `RangeSelector` integrato
- [ ] Tooltip con breakdown per broker
- [ ] Dark mode

### 8.3 Dual Y-Axis Per-Transaction Gain Chart — 1.5 giorni

#### Tasks

- [ ] Creare `src/lib/components/dashboard/AssetDualAxisChart.svelte`
- [ ] **Asse Y sinistro**: prezzo asset / % variazione
- [ ] **Asse Y destro**: gain/loss per ogni transazione BUY
- [ ] Per ogni BUY: linea che parte da 0 alla data del buy, traccia il gain/loss nel tempo
- [ ] **Linea cumulativa** con area: sommatoria dei gain su tutte le transazioni — verde sopra 0, rosso sotto
- [ ] **Sell events**: frecce ↓ (ECharts `markPoint`) sul punto di vendita
    - Se vendita parziale: freccia più piccola
    - Tooltip: "Sold X shares at Y€ — Gain: Z€"
- [ ] **Method Selector** (`AnalyticsMethodSelect.svelte`): FIFO/LIFO/PMC per vista analitica
    - Disclaimer sempre presente: "I calcoli fiscali usano sempre PMC per conformità italiana"
    - Il selector cambia solo la vista analitica, NON il calcolo fiscale
- [ ] Dati da `GET /portfolio/gains?asset_id=X&method=FIFO`

### 8.4 Asset Allocation Donut — 0.5 giorni

#### Tasks

- [ ] Creare `src/lib/components/dashboard/AllocationChart.svelte`
- [ ] ECharts donut chart
- [ ] Raggruppamento per asset_type (STOCK, ETF, CRYPTO, etc.)
- [ ] Breakdown per asset nel tooltip
- [ ] Colori consistenti per tipo
- [ ] Dark mode

### 8.5 Recent Transactions + Quick Actions — 1 giorno

#### Tasks

- [ ] Creare `src/lib/components/dashboard/RecentTransactions.svelte`
- [ ] Ultime 10 transazioni con `DataTable` compatto (no pagination)
- [ ] Link "View All →" a /transactions
- [ ] Creare `src/lib/components/dashboard/QuickActions.svelte`
- [ ] Bottoni: Add Transaction, Import Files, Sync FX, Sync Prices

### Componenti (nuovi per Phase 8)

| Componente                     | Descrizione                        | Riusa        |
|--------------------------------|------------------------------------|--------------|
| `KPICard.svelte`               | Card KPI con trend e breakdown     | Nuovo        |
| `PortfolioChart.svelte`        | Growth chart investito vs. mercato | ECharts      |
| `AssetDualAxisChart.svelte`    | Dual Y-axis per tx gain/loss       | ECharts      |
| `AllocationChart.svelte`       | Donut allocation                   | ECharts      |
| `AnalyticsMethodSelect.svelte` | Selettore metodo analitico         | SimpleSelect |
| `RangeSelector.svelte`         | Selezione range temporale          | Nuovo        |
| `RecentTransactions.svelte`    | Ultime transazioni compatte        | DataTable    |
| `QuickActions.svelte`          | Bottoni azioni rapide              | Nuovo        |

### API Endpoints

| Endpoint                                        | Metodo | Descrizione                   |
|-------------------------------------------------|--------|-------------------------------|
| `/api/v1/portfolio/overview`                    | GET    | **NUOVO** Aggregazione pesata |
| `/api/v1/portfolio/gains?asset_id=X&method=PMC` | GET    | Gain/loss per tx              |
| `/api/v1/transactions?limit=10&sort=-date`      | GET    | Recent transactions           |
| Tutti gli endpoint esistenti                    | GET    | Per dati di supporto          |

### i18n Keys

```
dashboard.title, dashboard.kpi.nav, dashboard.kpi.pnl,
dashboard.kpi.roi_weighted, dashboard.kpi.cash, dashboard.kpi.trend_today,
dashboard.kpi.breakdown, dashboard.kpi.period,
dashboard.chart.portfolio_growth, dashboard.chart.invested,
dashboard.chart.market_value, dashboard.chart.range,
dashboard.chart.dual_axis, dashboard.chart.gain_per_tx,
dashboard.chart.cumulative_gain, dashboard.chart.sell_event,
dashboard.chart.allocation, dashboard.chart.allocation_by_type,
dashboard.method.title, dashboard.method.fifo, dashboard.method.lifo,
dashboard.method.pmc, dashboard.method.select_id,
dashboard.method.disclaimer_pmc,
dashboard.recent.title, dashboard.recent.view_all,
dashboard.actions.title, dashboard.actions.add_tx,
dashboard.actions.import_files, dashboard.actions.sync_fx,
dashboard.actions.sync_prices
```

### E2E Test Ideas

- [ ] KPI mostra NAV pesato per share_percentage
- [ ] KPI mostra ROI calcolato su valori assoluti (non media %)
- [ ] Portfolio chart ha due serie (investito + mercato)
- [ ] Dual axis chart mostra entrambe le scale
- [ ] Sell arrows visibili come markPoints
- [ ] Method selector cambia valori gain
- [ ] Disclaimer PMC sempre presente
- [ ] Allocation donut mostra breakdown per tipo
- [ ] Recent transactions mostra ultime 10
- [ ] Quick actions navigano alle pagine corrette
- [ ] Dark mode coerente su tutti i componenti

---

## 9. Chart Component Spec — `PriceChartShared.svelte`

### File

`src/lib/components/charts/PriceChartShared.svelte`

### Props Interface

```typescript
interface PricePoint {
    date: string;           // ISO date (YYYY-MM-DD)
    value: number;          // price, rate, or gain
    staleDays?: number;     // 0 = fresh data, >0 = data is N days old
    source?: string;        // provider/plugin key
}

interface PriceChartSharedProps {
    data: PricePoint[];
    currency: string;
    title?: string;
    editable?: boolean;         // click-to-edit enabled
    showGradient?: boolean;     // stale data gradient (default: true)
    rangeOptions?: string[];    // default: ['1W','1M','3M','6M','1Y','ALL']
    defaultRange?: string;      // default: '1Y'
    height?: string;            // CSS height (default: '300px')
    onEdit?: (date: string, newValue: number) => Promise<void>;
    onRangeChange?: (range: string) => void;
}
```

### Gradient Implementation

```javascript
// Calcola opacità basata su staleDays
function getOpacity(staleDays: number): number {
    if (!staleDays || staleDays === 0) return 1.0;
    return Math.max(0.3, 1.0 - staleDays * 0.15);
    // 0 days → 1.0, 1 day → 0.85, 2 → 0.70, 3 → 0.55, 4 → 0.40, 5+ → 0.30
}

// ECharts: Usa segmenti con opacity diversa
series: [{
    type: 'line',
    data: data.map(d => d.value),
    lineStyle: {width: 2},
    // Custom rendering per segmenti con opacità variabile
    renderItem: (params, api) => {
        // Calcola opacità per ogni segmento basata su staleDays
    }
}]
```

### Click-to-Edit

```javascript
// ECharts click handler
chart.on('click', (params) => {
    if (!editable || !onEdit) return;
    const point = data[params.dataIndex];
    // Mostra inline editor (popup/tooltip con input)
    showEditPopup(point.date, point.value, async (newValue) => {
        await onEdit(point.date, newValue);
    });
});
```

### Used By

- **Phase 5**: `FxRateChart.svelte` — wrapper per tassi FX
- **Phase 6**: Asset Detail page — wrapper per price history
- **Phase 8**: Portfolio chart (variante senza click-to-edit)

---

## 10. GDPR/Sharing Architecture

### Principio

> **Il Broker è la stanza.** Se dai a qualcuno le chiavi della stanza, vede tutto l'arredamento, anche quello comprato prima che entrasse.

L'accesso al broker espone l'**intero storico** del contenitore. Non esiste condivisione "a partire da una data". Se l'utente vuole nascondere operazioni passate, la soluzione è
creare un nuovo broker e trasferirci i fondi.

### Ruoli e Semantica

| Ruolo      | `share_percentage` default | Permessi                                                 | Caso d'uso                   |
|------------|----------------------------|----------------------------------------------------------|------------------------------|
| **OWNER**  | 100%                       | Tutto: CRUD transazioni, gestione accessi, delete broker | Intestatario conto           |
| **EDITOR** | 0%                         | CRUD transazioni (no gestione accessi, no delete broker) | Coniuge delegato, consulente |
| **VIEWER** | 0%                         | Sola lettura                                             | Commercialista               |

### UX Flow — Broker Detail

1. Nella pagina `/brokers/[id]`, bottone **"Share"** (icona lucide `Share2`) visibile solo per OWNER
2. Click → apre `BrokerSharingModal.svelte` con `ModalBase`
3. La modale mostra:
    - Lista utenti con accesso (DataTable): Username, Email, Role (SimpleSelect), Share % (input numerico), Remove (ConfirmModal)
    - "Add User" button → SearchSelect per cercare utente per username/email
    - Warning se somma share% > 100%: "La somma delle percentuali di possesso supera il 100%. Questo è consentito ma potrebbe sovrastimare il patrimonio."
4. Salva → chiama `POST/PATCH/DELETE /brokers/{id}/access`

### Frontend Component

**Piano dettagliato**: vedi `phases/phase-04-subplan/plan-brokerSharing.md`

```
BrokerSharingModal.svelte
├── ModalBase (wrapper)
├── DataTable (lista accessi)
│   ├── column: Avatar + Username (LazyImage + text)
│   ├── column: Role (SimpleSelect inline — OWNER/EDITOR/VIEWER)
│   ├── column: Share % (input numerico)
│   └── column: Actions (Remove con ConfirmModal)
├── SearchSelect (add user — usa GET /users/search)
└── Warning banner (se share > 100%)
```

### Privacy Notes

- Un EDITOR con share 0% non vede il broker nel suo Net Worth, ma può operare (es. inserire transazioni per conto dell'owner)
- Un VIEWER vede le transazioni ma il valore non impatta il suo Net Worth (share 0%)
- Nessun dato personale cross-utente — ogni utente vede solo i broker a cui ha accesso
- Log di accesso: futuro TODO per audit trail

---

## 11. Dependency Graph

```
Pre-work: Schema Changes
    │
    ├── share_percentage (BrokerUserAccess)  ✅
    ├── cost_basis_override (Transaction)    ✅
    └── fiscal_preferences (UserSettings)    → Phase 7
         │
         ▼
Phase 4.8 (Broker Sharing GUI) ──── NEW: search users API ────┐
         │                          NEW: BrokerSharingModal    │
         │                          NEW: Share button          │
         ▼                                                     │
Phase 5 (FX Management) ──── builds PriceChartShared ────┐    │
         │                                                 │    │
         ▼                                                 │    │
Phase 6 (Assets) ──── builds AssetMatchingWizard ────┐    │    │
         │              reuses PriceChartShared ──────┤    │    │
         ▼                                            │    │    │
Phase 7 (Transactions) ──── reuses AssetMatchingWizard    │    │
         │                  builds FiscalRegimeSelect      │    │
         │                  builds MultiImportWizard       │    │
         ▼                                                 │    │
Phase 7.5 (File Preview)                                   │    │
         │                                                 │    │
         ▼                                                 │    │
Phase 8 (Dashboard) ←─── uses ALL ────────────────────────┘    │
                         uses share_percentage from 4.8 ───────┘
                         reuses FiscalRegimeSelect
                         reuses PriceChartShared
                         builds KPICard, AllocationChart
                         builds AssetDualAxisChart
```

### Componenti condivisi tra fasi

| Componente              | Built in           | Used in                                |
|-------------------------|--------------------|----------------------------------------|
| `BrokerSharingModal`    | Phase 4.8          | Phase 4.8, 8 (share_percentage config) |
| `PriceChartShared`      | Phase 5            | Phase 5, 6, 8                          |
| `AssetMatchingWizard`   | Phase 6            | Phase 6, 7                             |
| `FiscalRegimeSelect`    | Phase 7            | Phase 7, 8                             |
| `AnalyticsMethodSelect` | Phase 8            | Phase 8                                |
| `DataTable`             | Phase 4 (existing) | ALL                                    |
| `ModalBase`             | Phase 4 (existing) | ALL                                    |
| `SearchSelect`          | Phase 4 (existing) | ALL                                    |
| `LazyImage`             | Phase 4 (existing) | ALL (avatar, icon, preview)            |
| `ImagePickerWrapper`    | Phase 4 (existing) | Phase 4.8, 6, 8 (icon selection)       |

---

## 12. Estimated Timeline

| Fase                               | Giorni        | Cumulativo | Note                                     |
|------------------------------------|---------------|------------|------------------------------------------|
| **Schema Changes (pre-work)**      | 1             | 1          | ✅ COMPLETATO (25 Feb 2026)               |
| **Phase 4.8 (Broker Sharing GUI)** | 5             | 6          | ✅ COMPLETATO (1 Mar 2026)                |
| **Phase 5.0 (PriceChartShared)**   | 1             | 7          | ✅ Chart library completa                 |
| **Phase 5 (FX)**                   | 3             | 10         | 🔄 Core ✅, Steps 7-9 pendenti           |
| **Phase 6 (Assets)**               | 5             | 15         | List + CRUD + Detail + Matching          |
| **Phase 7 (Transactions)**         | 8             | 23         | List + CRUD + Fiscal + Matching + Import |
| **Phase 7.5 (File Preview)**       | 2             | 25         | Preview inline (già pianificato)         |
| **Phase 8 (Dashboard)**            | 5             | 30         | KPI + Charts + Aggregation               |
| **Totale**                         | **30 giorni** |            | ~6 settimane lavorative                  |

### Milestones

1. **Milestone 0** (Giorno 6): Broker Sharing GUI operativa — multi-user configurabile
2. **Milestone 1** (Giorno 10): FX funzionante con chart condiviso
3. **Milestone 2** (Giorno 15): Assets con gain/loss e matching
4. **Milestone 3** (Giorno 23): Transazioni con import completo
5. **Milestone 4** (Giorno 25): File Preview operativo
6. **Milestone 5** (Giorno 30): Dashboard aggregata operativa

---

## Appendice: File da Creare (per fase)

### Phase 4.8 (Broker Sharing GUI)

```
backend/app/api/v1/users.py                                    # Endpoint search users
backend/app/schemas/users.py                                    # UserSearchItem schema
backend/test_scripts/test_api/test_users_search.py              # API tests
frontend/src/lib/components/brokers/BrokerSharingModal.svelte   # Modale sharing
```

### Phase 5

```
src/lib/components/charts/PriceChartShared.svelte       # SHARED
src/lib/components/fx/CurrencyGrid.svelte
src/lib/components/fx/FxRateChart.svelte
src/lib/components/fx/FxPairSourcesSection.svelte
src/lib/components/fx/FxSyncModal.svelte
src/routes/(app)/fx/+page.svelte                         # rewrite
```

### Phase 6

```
src/lib/components/assets/AssetModal.svelte
src/lib/components/assets/AssetSearchAutocomplete.svelte
src/lib/components/assets/AssetGainLossTable.svelte
src/lib/components/assets/AssetMatchingWizard.svelte     # SHARED
src/routes/(app)/assets/+page.svelte                      # rewrite
src/routes/(app)/assets/[id]/+page.svelte                 # new
src/routes/(app)/assets/[id]/+page.ts                     # new
```

### Phase 7

```
src/lib/components/transactions/TransactionModal.svelte
src/lib/components/transactions/FiscalRegimeSelect.svelte  # SHARED
src/lib/components/transactions/SellBuyMatchingPanel.svelte
src/lib/components/transactions/CashSplitModal.svelte
src/lib/components/transactions/MultiImportWizard.svelte
src/lib/components/transactions/ValidateImportButton.svelte
src/routes/(app)/transactions/+page.svelte                  # rewrite
```

### Phase 8

```
src/lib/components/dashboard/KPICard.svelte
src/lib/components/dashboard/PortfolioChart.svelte
src/lib/components/dashboard/AssetDualAxisChart.svelte
src/lib/components/dashboard/AllocationChart.svelte
src/lib/components/dashboard/AnalyticsMethodSelect.svelte
src/lib/components/dashboard/RangeSelector.svelte
src/lib/components/dashboard/RecentTransactions.svelte
src/lib/components/dashboard/QuickActions.svelte
src/routes/(app)/dashboard/+page.svelte                     # rewrite
```

### GDPR/Sharing

```
src/lib/components/brokers/BrokerSharingModal.svelte        # new
```

