# Code Reality Check
> Generato da analisi graphify del corpus completo (backend + frontend + wiki + docs + roadmap)  
> Data: 2025-05-24 | Grafo: 8341 nodi, 13328 edge, 691 comunità  
> **Regola**: il codice è la fonte di verità. Ogni entry che riporta divergenze va intesa come "il codice prevale sulla wiki/docs."

---

## Legenda
- ❌ **Conflitto reale** — la wiki dice A ma il codice è B
- ⚠️ **Wiki incompleta** — il codice implementa X, la wiki non lo menziona
- ✅ **Conforme** — codice e wiki concordano
- ℹ️ **Solo info** — dato utile senza contraddizioni

---

## [DB / MODELLI]

### ✅ DB Models — schema completo verificato
Alembic: 1 sola migrazione (`001_initial.py`) — conforme alle istruzioni "no incremental migrations".

Modelli in codice (`backend/db/models.py`):
- `User`, `GlobalSetting`
- `Broker`, `BrokerUserAccess`
- `Asset`, `AssetType`, `AssetIdentifierType`, `AssetEvent`, `AssetEventType`, `AssetProviderAssignment`
- `FxRate`, `FxConversionRoute`
- `Transaction`, `PricePoint`

32 nodi nel grafo da `alembic/` — confermano struttura single-migration.

### ✅ BrokerUserAccess — modello multi-utente presente
Il modello `BrokerUserAccess` (relazione many-to-many User↔Broker) è nel codice.  
La wiki menziona l'architettura multi-utente — conforme.

---

## [COSTO BASE / FIFO / WAC]

### ⚠️ WAC aggiunto ma wiki parla ancora solo di FIFO
**Cosa dice il codice:**  
- `compute_weighted_avg_cost()` in `backend/services/transaction_service.py`  
- `WacPreviewSection.svelte` frontend component  
- `cost_basis_override` workflow nel TransactionFormModal  
- Roadmap Phase 7 contiene piani specifici per WAC preview architecture  

**Cosa dice la wiki:**  
- La sezione "Transactions Domain" e le decisioni architetturali menzionano FIFO runtime  
- `KB-08` e le notes di i18n menzionano cost basis come FIFO-only

**Realtà:**  
Il sistema supporta **sia FIFO sia WAC**. WAC è calcolato per la preview di nuove transazioni, non sostituisce FIFO per il portfolio storico. La wiki va aggiornata per documentare la coesistenza.

**Azione suggerita:** Aggiornare `wiki/decisions/` con una nota su WAC preview vs FIFO historical.

---

## [FX PROVIDERS]

### ✅ Chain ECB→FED→BOE→SNB + MANUAL confermata dal codice
Trovati in `backend/services/fx_providers/`:
- `ecb.py` → `ECBProvider`
- `fed.py` → `FEDProvider`  
- `boe.py` → `BOEProvider`
- `snb.py` → `SNBProvider`
- `manual.py` → `ManualProvider` (sentinel MANUAL_RATE)

Il grafo ha il hyperedge **"FX Provider Family"** che li raggruppa tutti — EXTRACTED confidence 1.0.  
Wiki e codice concordano sulla chain di fallback.

### ✅ FxConversionRoute — routing multi-hop verificato
Modello `FxConversionRoute` nel DB. API `/api/v1/fx/routes` confermata.  
Hyperedge **"FX route and sync management"** (8 nodi, EXTRACTED 1.0).

---

## [ASSET PROVIDERS]

### ✅ Asset source providers in codice
Trovati in `backend/services/asset_source_providers/`:
- `justetf.py` → `JustETFProvider`
- `yahoo_finance.py` → `YahooFinanceProvider`
- `css_scraper.py` → `CSSScraperProvider`
- `scheduled_investment.py` → `ScheduledInvestmentProvider`
- `mock_provider.py` → `MockProvider`

Wiki documenta tutti i provider principali — conforme.

### ✅ Async I/O — yfinance wrappato correttamente
Grafo rileva esplicitamente "Core Thread Offload for Sync yfinance" in `yahoo_finance.py`.  
Il nodo documenta il pattern `asyncio.to_thread()` già applicato.  
**Nessuna violazione dell'Async I/O Rule rilevata dal grafo**.

---

## [BRIM BROKER IMPORT PLUGINS]

### ⚠️ Schwab e Trading212 — presenti in codice, potenzialmente assenti dalla wiki
Plugin trovati in `backend/services/brim_providers/`:
- `broker_coinbase.py` → `CoinbaseBrokerProvider`
- `broker_degiro.py` → `DegiroBrokerProvider`
- `broker_directa.py` → `DirectaBrokerProvider`
- `broker_etoro.py` → `EtoroBrokerProvider`
- `broker_finpension.py` → `FinpensionBrokerProvider`
- `broker_freetrade.py` → `FreetradeBrokerProvider`
- `broker_generic_csv.py` → `GenericCsvBrokerProvider`
- `broker_ibkr.py` → `IBKRBrokerProvider`
- `broker_revolut.py` → `RevolutBrokerProvider`
- `broker_schwab.py` → `CharlesSchwabBrokerProvider`
- `broker_trading212.py` → `Trading212BrokerProvider`

**Totale: 11 broker plugins** — la wiki/docs menzionava "11+ brokers". ✅ Conforme.  
Verificare che tutti e 11 siano documentati nella wiki `features/brim.md`.

---

## [AUTH / SESSIONI]

### ✅ Session cookie + JWT confermato
Grafo hyperedge **"Zodios Request Pipeline"** include:
- `zodios_client_session_cookie_auth`  
- `zodios_client_401_redirect_interceptor`
- `zodios_client_accept_language_header`

Backend: `auth_auth_api`, `authservice_auth_service`, `userservice_user_service` (EXTRACTED 1.0).  
Wiki documenta session-based auth — conforme.

---

## [FRONTEND / SVELTE 5]

### ✅ Svelte 5 Runes adottati nei nuovi componenti
Grafo rileva nodi runes-related in `frontend/src/lib/`. Il hyperedge **"Frontend Stack Conventions"** include:
- `svelte5_runes_reactivity_convention`
- `svelte5_runes_tailwind4_theme_config`
- `zodios_api_client_type_safe_api_client`

Tutti EXTRACTED confidence 1.0 — il codice usa runes nei componenti moderni.

### ℹ️ TanStack Table — adapter Svelte 5 custom presente
Hyperedge **"TanStack Table Svelte 5 Adapter Group"** (EXTRACTED 1.0):
- `tanstack_svelte5_adapter`
- `createsveltetable_create_svelte_table`
- `flexrender_flex_render`

Questo adapter custom è documentato nella wiki? Verificare.

### ✅ Dual View pattern (card + table) confermato
Hyperedges estratti:
- **"FX List Dual View"**: `fxcard_fx_pair_card`, `fxtable_fx_pair_table`, `fx_dual_view_pattern`
- **"Asset List Dual View"**: `assetcard_asset_card`, `assettable_asset_table`, `asset_dual_view_pattern`

Entrambi INFERRED 0.85 — pattern coerente tra FX e Asset.

---

## [PROVIDER REGISTRY PATTERN]

### ✅ Auto-discovery con params_schema confermato
Grafo hyperedge **"Provider Registry Family"** (EXTRACTED 1.0):
- `providerregistry_abstract_provider_registry`
- `providerregistry_fx_provider_registry`
- `providerregistry_asset_provider_registry`
- `providerregistry_brim_provider_registry`
- `providerregistry_auto_discovery_pattern`

Hyperedge **"Metadata-Driven Extensibility Patterns"** (INFERRED 0.79) collega:
- `provider_registry_pattern`
- `provider_registry_params_schema_dynamic_forms`
- `signals_registry_type_hierarchy`

Wiki `decisions/provider-registry-decision.md` e codice concordano. ✅

---

## [TECHNICAL ANALYSIS / SIGNALS]

### ✅ Signals implementati: EMA, MACD, RSI, Bollinger
Comunità C26 "Technical Analysis Signals" (50 nodi, cohesion 0.11 — la più alta):
- `AssetComparisonSignal.ts`
- `BollingerSignal.ts`
- `ChartSignal.ts`
- `CompoundSignal.ts`
- `EmaSignal.ts`

Hyperedges per signal groups (tutti EXTRACTED 1.0):
- **"Indicator Overlay Signals"**: EMA, MACD, RSI, Bollinger
- **"Benchmark Overlay Signals"**: Linear, Compound, Sine
- **"Comparison Overlay Signals"**: FX pair signal, Asset comparison signal

---

## [API ENDPOINTS]

### ✅ API v1 surface map (dal grafo)
Hyperedge **"API v1 surface"** (INFERRED 0.82):
`/auth`, `/settings`, `/system`, `/uploads`, `/users`, `/utilities`, `/fx`, `/transactions`, `/brokers`

Hyperedge **"Broker import preview flow"** (EXTRACTED 1.0):
`POST /brokers/import/upload` → parse → get plugins → BRIM service → registry

Hyperedge **"FX route and sync management"** (EXTRACTED 1.0):  
`POST /fx/sync-rates`, `POST|DELETE /fx/rate`, `POST /fx/convert`, `GET|POST|DELETE /fx/routes`

---

## [ARCHITETTURA GENERALE]

### ✅ God nodes confermano il design
I nodi più connessi del grafo sono:
1. `Currency` (197 edge) — valuta è il pivot di tutto (FX, Assets, Transactions)
2. `TransactionFormModal.svelte` (154 edge) — componente modale centrale UI
3. `BaseDeleteResult`, `BaseListResponse`, `BaseBulkResponse` (~120 edge) — contratti API condivisi
4. `BackwardFillInfo` (111 edge) — gestione gap nei prezzi storici
5. `DateRangeModel` (96 edge) — range date pervasivo in tutto il sistema

### ✅ Portfolio Valuation Flow — hyperedge chiave (EXTRACTED 1.0)
```
dashboard_unified_portfolio_view 
  → fifo_runtime_cost_basis_runtime 
  → fx_currency_triangulation_graph 
  → dashboard_share_percentage_weighting
```
Architettura FIFO-at-runtime + FX triangulation confermata dal grafo.

---

## SUMMARY INCONGRUENZE PRIORITARIE

| # | Severità | Area | Azione |
|---|----------|------|--------|
| 1 | ⚠️ | Cost Basis: WAC coesiste con FIFO | Aggiornare wiki per documentare WAC preview |
| 2 | ⚠️ | BRIM: 11 plugin → verificare wiki li documenti tutti | Check `features/brim.md` |
| 3 | ℹ️ | TanStack Table Svelte 5 adapter custom | Documentare in wiki se non presente |
| 4 | ✅ | FX chain, async I/O, providers, auth | Tutti conformi |
| 5 | ✅ | DB models, API surface, signal system | Tutti conformi |

---

*Report generato da graphify BFS traversal su graph.json (8341 nodi).  
I nodi codice sono la fonte di verità per tutte le incongruenze segnalate.*
