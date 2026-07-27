# Piano Applicativo: Phase 0 — AI Export Backend Snapshot e Hard Cutover

**Stato**: ✅ COMPLETATO — review manuale approvata il 27 luglio 2026
**Data**: 26 luglio 2026

← Analisi architetturale:
[AI Export F1 — Architettura e fotografia dati curata](../analysis-phase00AiExportArchitectureAndSnapshot.md)

← Piano padre:
[Phase 0 — Migrazione Segnali Backend](../plan-phase00SignalsBackendMigrationImplementation.prompt.md)

## 1. Obiettivo

Sostituire integralmente l'AI Export corrente con una piattaforma:

```text
Frontend task/detail/render mode
    ↓
GET /api/v1/ai-export/catalog
    ↓ compatibilità fail-closed
POST /api/v1/ai-export/snapshot
    ↓
AiExportSnapshotService
    ├── Portfolio Engine / Service
    ├── LotsAnalysisService
    ├── Asset service
    ├── FX service
    └── SignalService / annotations
    ↓
Snapshot JSON tipizzato e versionato
    ↓
Frontend prompt renderer sicuro
    ↓
Clipboard + privacy feedback
```

Il risultato finale deve:

- coprire Portfolio, Asset, FX e Broker;
- implementare i 18 task approvati;
- supportare `compact`, `standard` e `full` per ogni task;
- produrre esattamente 54 combinazioni allow-listed;
- mantenere prompt, response contract, lingua e user notes nel frontend;
- spostare nel backend dati e calcoli finanziari/tecnici;
- essere invocabile senza UI e riusabile dal futuro MCP;
- eseguire un hard cutover senza feature flag o fallback runtime;
- eliminare il vecchio AI Export e i quattro engine tecnici TypeScript;
- lasciare intatti comparison, benchmark, Measure e renderer backend dei grafici;
- chiudere F1, F2 e la parte residua di F3 del piano padre.

## 2. Decisioni confermate

1. Ogni task supporta tutti e tre i detail level.
2. I 54 profili derivano da 18 task spec + 3 overlay condivisi.
3. Ogni profilo risolto ha `profile_id` e `profile_version` stabili.
4. Nessun dual path production.
5. Il legacy può vivere solo come oracle/fixture di parità.
6. Asset e FX possono essere migrati separatamente.
7. Portfolio e Broker vengono tagliati insieme perché condividono builder e clipboard.
8. La parità legacy si applica soltanto alle capacità realmente esistenti.
9. Task/detail/domain greenfield usano test di conformità.
10. Nessun top-N implicito in `standard` o `full`.
11. Ogni profilo `compact` dichiara limite e regola di selezione.
12. Nessun plugin tecnico viene auto-arruolato nei profili AI.
13. Nessun DB schema change è previsto.
14. Portfolio Risk Review resta esclusa.

## 3. Scope

### 3.1 Incluso

- catalogo statico compatibilità;
- snapshot endpoint autenticato;
- request/response discriminate per dominio;
- profile resolver allow-listed;
- 54 profili deterministici;
- auth, user scope e broker access;
- dati finanziari, FIFO, segnali, annotazioni, coverage e breadth;
- normalized return compatibile;
- valuation reference ultima BUY;
- cash decomposition engine-owned;
- signal semantics canoniche backend;
- band-boundary annotations;
- sampling, rounding, omission e telemetria backend;
- prompt catalog e response contract frontend;
- rendering Markdown/YAML sicuro;
- modalità `data_only` e `full_prompt`;
- lingua, web research e user notes frontend;
- privacy feedback post-copy;
- migrazione delle quattro superfici UI;
- rimozione legacy AI Export;
- rimozione EMA/RSI/MACD/Bollinger TypeScript;
- docs, instructions, devWiki e graph.

### 3.2 Escluso

- chiamate LLM;
- MCP transport/server;
- persistenza o cache snapshot;
- storico export;
- trading automation;
- raccomandazioni buy/sell;
- Risk Engine;
- look-through valutario completo;
- plugin/parametri tecnici arbitrari dal browser;
- deduzione non autorevole dell'ultimo import broker;
- nuova provenance DB per import/transazioni;
- modifica della matematica del Portfolio Engine.

## 4. Baseline verificata

### Backend

- `PortfolioHistoryPoint` espone già la cash decomposition;
- il cash context va mappato dall'ultimo history point;
- `PortfolioEngine` espone `valuation_price`, currency e source;
- `LAST_BUY_PRICE` è già user/broker scoped e quote-base aware;
- `SignalService` possiede calcolo, warm-up, coverage e output canonico;
- `SignalAnnotationService` non risolve ancora componenti band;
- `LotsAnalysisService` fornisce sintesi FIFO riusabili;
- non esiste un legame autorevole import BRIM → broker → timestamp;
- `Transaction.created_at` non identifica un import;
- `AssetEvent.provider_assignment_id` distingue provider/manual;
- `Broker.description` è user-authored;
- asset short description non distingue sempre provider/user.

### Frontend

- Dashboard e Broker condividono `aiExportBuilder.ts`;
- Asset e FX hanno builder/renderer/clipboard propri;
- `technical/` ricalcola EMA/RSI/MACD e rileva eventi;
- `yamlSerializer.ts` è custom;
- non esistono test AI Export dedicati;
- non è installata una libreria YAML;
- Broker non ha task propri;
- FX non ha exposure impact;
- `AiExportMenu.svelte` è condiviso dalle quattro route.

### Engine TypeScript da rimuovere

- `EmaSignal.ts`;
- `RsiSignal.ts`;
- `MacdSignal.ts`;
- `BollingerSignal.ts`.

Restano `ChartSignal`, comparison, benchmark, Measure, registry locale non tecnico,
catalog mapper e renderer generico backend.

### Worktree concorrente

Prima di ogni modifica:

- leggere status e diff dei file assegnati;
- integrare cambi utente già presenti;
- non ripristinare modifiche parallele;
- trattare `portfolio_engine.py`, DB models e BRIM come hotspot concorrenti.

## 5. Gap v3 risolti nel piano

| Gap | Decisione |
|---|---|
| Cash decomposition | ultimo `PortfolioHistoryPoint`; nessuna formula duplicata |
| Normalized return | fixture condivise + parity backend |
| Band source | source `band` con `lower/middle/upper` |
| Ultimo import broker | omesso senza fonte; usare `latest_transaction_date` |
| Matrice | 18 task × 3 overlay = 54 |
| Token estimate | canonical JSON + `chars_div_4_v1`; prompt finale frontend |
| FX exposure | cash/posizioni collegabili; no look-through |
| Note provenance | broker=user; asset=provider_or_user; event provider/manual |
| Last BUY | position snapshot del Portfolio Engine |
| Warm-up | piano reale di `SignalService` |
| Signal semantics | contratto output generico backend |
| YAML | dipendenza mantenuta `yaml` |
| Metric semantics | unità, denominatore, periodo, annualizzazione |
| DB migration | nessuna |

## 6. Contratti target

### Catalog

```text
GET /api/v1/ai-export/catalog
```

Restituisce soltanto:

- schema version;
- domain/task/detail;
- profile id/version;
- frontend response contract id/version attesi;
- applicability code;
- supporto user notes/web research.

Non restituisce prompt, label, traduzioni o dati utente.

### Snapshot request

Union discriminata da `domain`.

Campi comuni:

- domain;
- task;
- detail level;
- date range;
- target currency.

Campi dominio:

- Portfolio: broker IDs opzionali;
- Broker: broker ID;
- Asset: asset ID e broker IDs opzionali;
- FX: base/quote e broker IDs opzionali.

Regole:

- `user_id` non accettato;
- extra forbid;
- broker access server-side;
- nessun signal code/parametro libero;
- applicability non soddisfatta → problema typed.

### Snapshot response

Union discriminata da `domain`:

```yaml
meta:
facts:
states:
technical:
events:
coverage:
semantics:
domain_notes:
export_stats:
```

Meta:

- schema/profile/response-contract version;
- generated/snapshot timestamps;
- selected range;
- technical window;
- calculation warm-up start;
- target currency.

### Error contract

- `unsupported_profile`;
- `profile_contract_mismatch`;
- `task_not_applicable`;
- `broker_access_denied`;
- `entity_not_found`;
- `snapshot_source_failure`.

Un singolo indicatore non calcolabile non fallisce lo snapshot.
Una fonte finanziaria required fallita non produce una response success-shaped.

## 7. Matrice task

Ogni riga supporta `compact`, `standard`, `full`.

| Dominio | Task | Migrazione/parità | Applicability |
|---|---|---|---|
| Portfolio | `pac_planning` | legacy diretto | portfolio accessibile |
| Portfolio | `rebalancing` | legacy diretto | portfolio accessibile |
| Portfolio | `performance_attribution` | greenfield | range con dati |
| Portfolio | `income_review` | legacy diretto | portfolio accessibile |
| Portfolio | `technical_breadth` | evolve `market_trend` | tecnica opzionale |
| Portfolio | `portfolio_description` | evolve describe/snapshot data-only | portfolio accessibile |
| Asset | `asset_snapshot` | legacy snapshot/classification facts | asset esistente |
| Asset | `asset_trend_analysis` | evolve `asset_classify` | storia opzionale |
| Asset | `position_review` | greenfield | asset posseduto |
| Asset | `asset_pac_timing_context` | greenfield | asset esistente |
| Asset | `drawdown_recovery` | greenfield | storia sufficiente |
| FX | `fx_trend_review` | evolve snapshot/trend | coppia valida |
| FX | `fx_exposure_impact` | greenfield | cash/posizioni collegabili |
| FX | `fx_conversion_timing_context` | greenfield | coppia valida |
| Broker | `broker_review` | greenfield; parity fatti filtrati | accesso broker |
| Broker | `broker_cost_efficiency` | greenfield | accesso broker |
| Broker | `broker_concentration_context` | greenfield | accesso broker |
| Broker | `broker_fifo_lot_review` | greenfield | accesso broker |

Render mode frontend:

- `data_only`;
- `full_prompt`.

Il render mode non modifica il profilo backend.

Detail overlay:

| Livello | Cardinalità | Tecnica | Serie/eventi |
|---|---|---|---|
| compact | limite e selector profile-owned | latest/breadth | minime |
| standard | tutte le posizioni | standard bundle | 7 daily + 8 weekly |
| full | tutte le entità/contribution | tutti i curati | weekly window + recent daily |

Ogni compact profile dichiara limite, metrica, ordering e coverage incluso/totale.

## 8. Struttura target

### Backend

```text
backend/app/
├── api/v1/ai_export.py
├── schemas/ai_export.py
└── services/ai_export/
    ├── models.py
    ├── service.py
    ├── resolver.py
    ├── technical.py
    ├── normalization.py
    ├── sampling.py
    ├── coverage.py
    ├── telemetry.py
    ├── profiles/{base,portfolio,asset,fx,broker}.py
    └── assemblers/{shared,portfolio,asset,fx,broker}.py
```

### Frontend

```text
frontend/src/lib/features/ai-export/
├── AiExportMenu.svelte
├── AiExportOptionsPanel.svelte
├── aiExportClient.ts
├── aiExportClipboard.ts
├── snapshotRenderer.ts
├── markdownEscaping.ts
├── types.ts
├── catalog/{shared,portfolioTasks,assetTasks,fxTasks,brokerTasks}.ts
└── templates/{sharedInstructions,responseContracts,promptRenderer}.ts
```

### Test

```text
backend/test_scripts/
├── fixtures/ai_export/{legacy_semantics,snapshots,prompts}/
├── test_schemas/test_ai_export_schemas.py
├── test_services/test_ai_export_profiles.py
├── test_services/test_ai_export_technical.py
├── test_services/test_ai_export_asset_fx.py
├── test_services/test_ai_export_portfolio_broker.py
└── test_api/test_ai_export_api.py

frontend/src/lib/features/ai-export/__tests__/
├── catalogCompatibility.test.ts
├── snapshotRenderer.test.ts
├── promptRenderer.test.ts
├── markdownEscaping.test.ts
└── aiExportClient.test.ts
```

## 9. Convenzioni esecuzione

Per ogni step:

1. todo SQL `in_progress`;
2. leggere diff/worktree;
3. modificare soltanto lo scope;
4. test target minimo;
5. aggiornare subito questo piano con stato/data/note/fuori pista;
6. aggiornare todo/dipendenze;
7. non anticipare il gate successivo.

Ogni modifica API richiede `./dev.py api sync`.

## Macrofase A — Artefatti, baseline e freeze

### A1 — Materializzare e cross-linkare il piano

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Creare questo piano, collegarlo ad analisi/piano padre, correggere V2→V3 e sostituire
`token-bounded` con telemetria non distruttiva.

> **Note implementazione**: creato il piano esecutivo in `01_signalMigration/02_aiExport`; aggiunti i
> cross-link; il piano padre ora punta all'analisi v3 e al presente piano.

### A2 — Fixture e mappa compatibilità legacy

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Creare dataset/expected deterministici per normalized return, sampling, eventi,
allocazioni/PAC, Asset snapshot e FX snapshot/trend.

Classificare ogni capacità come migration-parity o greenfield conformance.
Broker task, FX exposure e detail level a tre stati non usano falsa parità.

> **Note implementazione**: aggiunte fixture JSON versionate per normalized return,
> sampling, eventi tecnici e mapping prompt/task in
> `backend/test_scripts/fixtures/ai_export/legacy_semantics/`; aggiunti test Vitest
> legacy-oracle e catalog compatibility, 12/12 verdi.
>
> **⚠️ Fuori pista**: il legacy usa il prezzo precedente alla technical window quando
> manca il punto iniziale e può eliminare dal sample il punto base 0%. Entrambi i casi
> sono fixture `known-legacy-discrepancy`: il backend nuovo deve usare il primo prezzo
> osservato on-or-after e preservare primo/ultimo punto.

### A3 — Freeze matrice/profili

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Ogni task spec dichiara facts/states/events, signal bundle, annotations, metric
semantics, note, applicability, response contract e web/user-note support.

Ogni overlay dichiara cardinalità, sampling, precisione, event limits e compact
selection.

> **Note implementazione**: creato
> [contract-phase00AiExportTaskProfiles.md](./contract-phase00AiExportTaskProfiles.md)
> con 18 task, tre overlay, bundle tecnici statici, annotazioni, selector compact,
> applicability, note/web support e response contract ID/version.

**Gate A**

**Stato**: ✅ SUPERATO — 26 luglio 2026.

- fixture legacy disponibili;
- count profile = 54;
- ID univoci;
- nessun auto-enrollment;
- nessun compact limit implicito.

## Macrofase B — Contratti, catalogo e sicurezza

### B1 — Schemi request/response/problem

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Implementare `backend/app/schemas/ai_export.py`: union discriminate, extra forbid,
range/currency semantics, facts dominio, meta/versioning e typed problem.

> **Note implementazione**: creato il contratto completo request/catalog/snapshot/problem
> con union discriminate per domain/code, 18 task tipizzati, target multi-asset/FX,
> signal instances parametrizzate, normalized-return invariants, position valuation
> nullable, WAC/FIFO separati e 78 test schema verdi.

### B2 — Profile registry/resolver

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Implementare manifest immutabili, 18 task spec, 3 overlay, 54 profili, version policy
e completeness metadata.

> **Note implementazione**: aggiunto package `services/ai_export` con manifest frozen,
> sei bundle tecnici statici, annotazioni inclusa fonte band, selector compact,
> overlay deterministici, resolver exact e catalog conversion. Verificati 18 task,
> 54 profili, compatibilità reale params/componenti con i 17 plugin e limiti eventi
> espliciti 10/40/120; 20 test verdi.

### B3 — Catalog endpoint

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Registrare GET catalogo ordinato e privo di prompt/dati utente.

> **Note implementazione**: aggiunto `GET /api/v1/ai-export/catalog`, statico e
> user-data-free, con 54 entry validate e ordine deterministico.

### B4 — Service/API skeleton e auth

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Creare service standalone, POST autenticata, user scope, broker access, applicability
typed e no broad catch.

> **Note implementazione**: creati `AiExportSnapshotService` e
> `POST /api/v1/ai-export/snapshot`; lo scope broker viene caricato in bulk e ogni ID
> negato produce 403 typed senza filtro silenzioso. Finché gli assembler non esistono,
> una richiesta valida fallisce esplicitamente 503 `assembler_not_implemented`.
> Gli errori dichiarano l'envelope FastAPI `detail` anche in OpenAPI; 111 test
> cumulativi contract/profile/service/API verdi.

### B5 — OpenAPI gate

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Eseguire `./dev.py api sync`; verificare discriminatori Zodios senza cast insicuri.

> **Note implementazione**: sincronizzato OpenAPI/Zodios. Esteso il fixup generator
> per request/response/target/problem AI Export e aggiunti enum discriminator espliciti:
> il client genera `z.literal(...)`, `z.discriminatedUnion(...)` e type literal, senza
> cast. `svelte-check` chiude a 0 errori/0 warning.
>
> **⚠️ Fuori pista**: il primo sync conservava il discriminator OpenAPI ma generava
> `domain/code: string`, rendendo invalida la union Zod runtime. Corretto il contratto
> Pydantic e il fixup codegen prima di proseguire.

**Gate B**

**Stato**: ✅ SUPERATO — 26 luglio 2026.

- catalogo 54;
- endpoint autenticato;
- service standalone;
- client typed;
- broker scope coperto.

## Macrofase C — Fondazione tecnica

### C1 — Signal semantics canoniche

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Aggiungere semantic ID e descrizione inglese neutrale al contratto output generico.
Tutti i 17 plugin devono coprire ogni output.

> **Note implementazione**: esteso il contratto generico Signal con semantica
> canonica plugin/output-owned. I 17 plugin e 26 output dichiarano ID/descriptions
> neutrali, propagati fino alle serie e al catalogo; uniqueness e linguaggio
> non-prescrittivo sono validati.

### C2 — Band-boundary source

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Creare `SignalBandValueSource(instance_id, series_key, component)` con
`lower/middle/upper`; estendere schema, resolver e test.

> **Note implementazione**: aggiunto source discriminato `band`, resolver
> lower/middle/upper, preflight su output band e test Bollinger/Donchian
> plugin-agnostici. Errori strutturali usano `SignalRequestValidationError` e sono
> mappati a HTTP 422 da Asset/FX; i request model validano anche reference band.
> API client sincronizzato con union Zod band e semantic fields; backend signal
> target 220 test verdi, frontend catalog 10/10 e check 0/0.
>
> **⚠️ Fuori pista**: il primo pass lasciava i nuovi errori band come `ValueError`
> destinati a HTTP 500 e il codegen non includeva `SignalBandValueSource`; aggiunti
> errore typed, mapping 422, barrel exports e fixup discriminator.

### C3 — Technical profile runner

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Usare SignalService e loader bulk; warm-up plugin-derived; calcolo esteso; slice;
stati/eventi; nessuna matematica duplicata.

> **Note implementazione**: creato runner domain-neutral manifest→SignalService con
> piano warm-up/load range, conversione annotation incluse band, output scalar/band,
> depth task-specific, stati neutrali, eventi deduplicati/capped, semantiche presenti,
> volume eligibility e combine multi-target sullo stesso profilo.
>
> **⚠️ Fuori pista**: la prima versione ignorava `technical_depth`, marcava eleggibili
> target senza osservazioni e permetteva combine di profili diversi. Corretto con
> policy state-only/latest/sampled, eligibility osservata e identity gate.

### C4 — Sampling/rounding/omission/telemetry

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Sampling dopo slice, rounding dopo sampling, omissione tecnica vuota, canonical JSON
e token estimate deterministici.

> **Note implementazione**: aggiunte utility pure Decimal per sampling standard/full,
> first/base/last preservation, precisione, omission, canonical JSON, token estimate,
> coverage volume e breadth ponderata direzionale sull'intero universo eleggibile.
>
> **⚠️ Fuori pista**: corretti un punto weekly parziale quando il daily tail divideva
> la settimana e la breadth che aggregava overbought/oversold o ometteva below/negative.

**Gate C**

**Stato**: ✅ SUPERATO — 26 luglio 2026.

- semantics complete;
- band annotations verdi;
- warm-up plugin-derived;
- output deterministico.

## Macrofase D — Asset e FX backend

### D1 — Normalized return e valuation reference

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

3M; base exact/on-or-after prima del sampling; no backward fill; young incomplete;
last BUY separata; parity fixture.

> **Note implementazione**: aggiunti helper observed-only per normalized return,
> metriche relative e valuation reference BUY/seed. Il Portfolio Engine ora usa
> source tipizzate `MARKET_PRICE/LAST_BUY_PRICE/LAST_SEED_COST/MISSING`, history
> reference date-aware, seed `(broker, asset)`, split-adjusted effective price e
> metadata reference originale separata. NAV-at-cost/zero unrealized resta invariato.
>
> **⚠️ Fuori pista**: il lavoro parallelo seed iniziale condivideva il booleano
> `LAST_BUY_PRICE`, perdeva reference storiche e gonfiava BUY/seed dopo split.
> Su decisione utente, refactor strutturale completato: history, split ratios deduplicati,
> effective/reference separation, zero-cost seed e in-transit cost fallback.

### D2 — Asset assembler: 15 profili

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Identità/classificazione, currency, price/fallback, drawdown/return, serie, posizione,
FIFO, eventi, tecnica, coverage e descrizione.

> **Note implementazione**: assembler Asset completo per 5 task × 3 detail con asset
> unowned/no-price preservati, portfolio context opzionale, aggregazione multi-broker
> completa, source mixed esplicita, BUY/seed reference uniforme, range tecnico/warm-up,
> SignalService, normalized return, FIFO summary affidabile, note provenance e stats.

### D3 — FX assembler: 9 profili

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Pair/rate/provider, returns, extrema/volatility, serie, inversion/triangulation,
tecnica/coverage ed exposure non look-through.

> **Note implementazione**: assembler FX completo per 3 task × 3 detail con un solo
> `convert_bulk`, actual/requested date, observed dedup, normalized return, extrema,
> sample volatility, drawdown, technical runner ed exposure cash/position
> trading/valuation-only; qualsiasi link non valorizzabile fallisce typed.
>
> **⚠️ Fuori pista**: corretti durante review asset unowned rifiutati, prehistory
> eliminata dalla completezza return, contribution multi-broker parziali, FIFO FAILED,
> drawdown su range errato, exposure conversion silenziosamente saltate, flag
> look-through contraddittorio e volatilità zero con un solo return.

### D4 — Fixture/API

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Testare 24 profili, fallback/applicability, FX paths, malicious notes e determinismo.

> **Note implementazione**: `AiExportSnapshotService` dispatcha Asset/FX reali;
> l'API mappa errori typed 404 entity, 409 applicability e 503 source, mantenendo
> 403/422 e Portfolio/Broker 503 esplicito. OpenAPI/Zodios sincronizzato; 265 test
> assembler/core e frontend check 0/0.

**Gate D**

**Stato**: ✅ SUPERATO — 26 luglio 2026.

- 15 Asset + 9 FX verdi;
- normalized return parity;
- valuation reference corretta;
- FX exposure non inventata.

## Macrofase E — Portfolio e Broker backend

### E1 — Portfolio assembler: 18 profili

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Engine/report/history point; NAV/cash/book; cash decomposition; capital/P&L;
income/costi; performance; sei allocazioni; posizioni; contribution; breadth.

> **Note implementazione**: assembler Portfolio completo con un report engine e un
> bulk prezzi, tutte le posizioni standard/full, compact selector espliciti,
> contribution position/unallocated/other, sei allocazioni, cash decomposition
> dall'ultimo history point, technical breadth full-universe, note provenance e stats.

### E2 — Broker assembler: 12 profili

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Summary/description, cash/capital/performance, costi, posizioni, concentration,
latest transaction, FIFO, breadth/coverage. Nessun falso `last_import_at`.

> **Note implementazione**: assembler Broker completo con report single-scope,
> contribution gated per task, concentration su gross exposure, latest transaction
> privacy-safe, FIFO sequenziale sintetico affidabile, compact selector, technical
> coverage full-universe e note selezionate.

### E3 — Breadth/coverage/metric semantics

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Count e total/eligible NAV weight; denominatori/periodi/annualizzazione espliciti.

> **Note implementazione**: pesi posizione/allocazione signed e coverage gross
> non-negative supportano short/leverage; concentration normalizza su gross absolute
> exposure, breadth mantiene denominator eligible e direzioni separate.

### E4 — Note/provenance

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Broker=user; asset=provider_or_user; event provider/manual; user notes frontend;
transaction descriptions ambigue escluse.

> **Note implementazione**: Broker.description e asset short description entrano
> come context con provenance; compact filtra entity notes; transaction
> description/tags/account/import metadata non vengono esportati.

### E5 — Fixture/API

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Testare 30 profili, multi-user/access, cardinalità, allocazioni, cash, FIFO, breadth e
note malicious.

> **Note implementazione**: servizio/API dispatchano ora tutti i quattro domini;
> 18 Portfolio + 12 Broker profili coperti. Suite backend AI Export completa 459/459,
> OpenAPI/Zodios sincronizzato e frontend check 0/0.
>
> **⚠️ Fuori pista**: le review hanno corretto lifetime-vs-period capital, cash
> currency native, sidecar contribution, leak compact, raw ranking, aggregate FIFO,
> quota eventi post-filtro, `broker_ids=[]`, short/leverage weights, fully-sold cost
> candidates e closed-only FIFO.

**Gate E**

**Stato**: ✅ SUPERATO — 26 luglio 2026.

- backend completo 54;
- quattro domini ready;
- auth/security verdi;
- service MCP-ready.

## Macrofase F — Frontend catalog/rendering/UX

### F1 — Catalogo e handshake

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

18 task, tre detail, response contract version, backend intersection e fail-closed.

> **Note implementazione**: creato catalogo locale per i quattro domini e handshake
> raw+Zod fail-closed contro i 54 profili backend.

### F2 — Serializer/Markdown boundary

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Installare `yaml`; deterministic emitter; dynamic fence; escaping; test adversariali.

> **Note implementazione**: aggiunta dipendenza `yaml`, serializer deterministico e
> boundary Markdown con fence dinamiche e casi adversariali.

### F3 — Client/orchestrazione unificata

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Un client/clipboard flow; zero builder finanziario/tecnico; lingua/render mode/note e
prompt stats frontend.

> **Note implementazione**: creati client typed, canonicalizzazione request,
> orchestrazione clipboard unica e stats backend/finali senza calcoli finanziari.

### F4 — Menu/opzioni

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Task, detail, data-only/full, lingua, note, web research, size warning e privacy toast.

> **Note implementazione**: creati menu/pannello V2 condivisi con focus/loading sicuri,
> detail reconciliation, size severity e feedback privacy localizzato.

### F5 — Prompt/response contract

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Sezioni separate: instructions, response contract, snapshot, domain notes, user notes,
language; boundary anti-injection.

> **Note implementazione**: implementati 18 instruction template, 18 response contract e
> renderer sezionato con user notes trattate sempre come dati YAML.

### F6 — Unit gate

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Catalog compatibility, 18 prompt contract, serializer, errors, clipboard e stats.

> **Note implementazione**: suite AI Export frontend completa a 95 test; `svelte-check`
> senza errori o warning; audit i18n completo sulle quattro lingue.

**Gate F**

**Stato**: ✅ SUPERATO — 26 luglio 2026.

- prompt solo da snapshot;
- catalogo 54 fail-closed;
- serializer robusto;
- zero matematica AI frontend.

## Macrofase G — Migrazione e hard cutover

### G1 — Asset

**Stato**: 🟡 CUTOVER + E2E COMPLETATI — review manuale in I2.

Cutover diretto; parity legacy analog; greenfield conformance; E2E/review manuale.

> **Note implementazione**: Asset Detail usa esclusivamente catalogo/menu/client V2;
> request contestuale, opzioni persistenti, stats anti-stale e feedback localizzato.

### G2 — FX

**Stato**: 🟡 CUTOVER + E2E COMPLETATI — review manuale in I2.

Cutover diretto; snapshot/trend parity; exposure/conversion conformance.

> **Note implementazione**: FX Detail usa la coppia canonica, range corrente e valuta
> portfolio target; rimosso il requisito locale `latestPoint`.

### G3 — Portfolio + Broker

**Stato**: 🟡 CUTOVER + E2E COMPLETATI — review manuale in I2.

Cutover accoppiato; portfolio parity; broker facts parity dove valida; task Broker
greenfield; multi-user E2E; zero runtime legacy.

> **Note implementazione**: Dashboard e Broker Detail sono stati migrati nello stesso
> gate; Broker usa il catalogo dedicato e le quattro superfici non importano più il
> runtime legacy.

### G4 — Equivalence report

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Mappare legacy → nuovo task/mode, parity, differenze deliberate e greenfield evidence.

> **Note implementazione**: creato
> [Migration Equivalence Report](report-phase00AiExportMigrationEquivalence.md) con
> mapping completo, fixture di evidenza, differenze approvate e scope greenfield.

**Gate G**

**Stato**: 🟡 CUTOVER ED E2E SUPERATI — review manuale accorpata in I2.

- quattro superfici sul nuovo endpoint;
- nessun fallback runtime;
- parity solo dove valida;
- Portfolio/Broker migrati insieme.

## Macrofase H — Cleanup

### H1 — Legacy AI Export

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Rimuovere builder/renderer/types/compaction/asset label/custom YAML/technical/domain
clipboard e template superati.

> **Note implementazione**: eliminato l'intero sottografo legacy Portfolio/Asset/FX,
> inclusi builder, renderer, clipboard, serializer custom e calcolo tecnico AI Export.
> Le fixture JSON oracle restano; il test catalogo ora verifica fixture→contratto V2
> senza importare codice production legacy.

### H2 — Engine TypeScript

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Rimuovere EMA/RSI/MACD/Bollinger, registry/barrel/test/import. Conservare
comparison/benchmark/Measure e backend renderer.

> **Note implementazione**: rimossi i quattro engine e relativi export/test; registry
> locale ridotto a FX/Asset comparison e benchmark sintetici. Measure resta separato e
> il renderer backend generico copre gli indicatori tecnici.

> **⚠️ Fuori pista**: il gate completo ha rilevato fixture frontend obsolete rispetto
> ai nuovi `semantic_id`/`semantic_description` obbligatori. Aggiornati solo i dati test;
> nessuna modifica production. Signal suite finale: 45/45.

### H3 — i18n/dead code

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

EN/IT/FR/ES, rimozione chiavi orfane, audit backend keys, zero-import e zero-file audit.

> **Note implementazione**: rimosse le chiavi legacy AI Export/engine locale e aggiunte
> le nuove label Snapshot/help in tutte le lingue; audit finale 1954/1954 per lingua,
> zero traduzioni mancanti e zero backend key mancanti. Nessun file/import legacy o
> engine tecnico resta.

**Gate H**

**Stato**: ✅ SUPERATO — 26 luglio 2026.

- zero calcolo tecnico TS;
- zero builder AI frontend;
- comparison/benchmark/Measure verdi;
- i18n completo.

## Macrofase I — Verifica, docs e knowledge

### I1 — Backend validation

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

Schema/service/API AI Export, signal annotation, portfolio engine/service, auth.
Escalare al full backend soltanto se necessario.

> **Note implementazione**: gate mirato finale a 686 test backend verdi su schemi,
> profili, quattro assembler, API/auth scope, SignalService/annotations e
> Portfolio Engine/Service.

### I2 — Frontend validation

**Stato**: ✅ COMPLETATO — 27 luglio 2026.

Unit, signal regression, check, build, i18n ed E2E target.

Review manuale desktop/mobile per menu/detail/applicability/mode/note/size/clipboard/
privacy/dark/fail-closed.

> **Note implementazione**: 141 test AI Export+signals, 61 asset unit, check senza
> errori/warning, build production, i18n 1954/1954 × 4 e 10 cross-domain E2E
> desktop/mobile verdi. L'E2E verifica request/response e clipboard reali sulle quattro
> superfici.

> **⚠️ Fuori pista**: il primo E2E Portfolio ha rilevato un 503
> `cash_balance_total_mismatch`. La causa era un invariante AI errato: il cash summary
> Engine usa FX alla data transazione, mentre l'esposizione per valuta usa FX snapshot.
> Conservate entrambe le viste fattuali; `allocation_by_currency_pct` usa ora il proprio
> denominatore dichiarato senza modificare la matematica del Portfolio Engine.

> **⚠️ Fuori pista**: la review finale ha inoltre disaccoppiato `drawdown_recovery`
> dalla presenza di punti nella sola technical window, reso raggiungibile il fallback
> clipboard generico `writeText/execCommand` e registrato tutte le suite AI Export/signal
> nei runner canonici. Gate canonico finale: 597 test verdi.

> **⚠️ Fuori pista**: la review manuale ha richiesto un secondo pass UX. Il pannello usa
> ora select custom con icona/nome/descrizione, espone `Fotografia dati` come scelta
> sintetica `data_only`, rende tutte le analisi `full_prompt`, nasconde web research,
> lingua e banner compatibilità e spiega i detail level via tooltip.

> **⚠️ Fuori pista**: il confirm discard è stato poi sostituito con memoria persistente
> per utente e contesto (`portfolio`, singolo Broker/Asset/FX). Il pannello è portalizzato
> sopra i controlli grafico, il link manuale è domain-aware, Snapshot non esporta mai note
> nascoste e select/DocsLink sono accessibili da tastiera.

> **Approvazione manuale (27 luglio 2026)**: review desktop/mobile conclusa con esito
> positivo dopo i round UX; layout Dashboard, z-index Asset/FX, memoria contestuale,
> link manuale, clipboard e prompt rappresentativi approvati.

### I3 — Documentazione

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

MkDocs AI Export, developer architecture, signal guide, instructions, piano padre,
analysis v3 ed equivalence report.

> **Note implementazione**: aggiunte architettura developer, guida condivisa EN/IT/FR/ES,
> quattro pagine manuale domain-specific EN, instruction frontend dedicata e ingressi
> SignalService separati/ordinati. MkDocs build e 18/18 cross-boundary link verdi; nessun
> errore translation introdotto dallo scope.

### I4 — devWiki/graph

**Stato**: ✅ COMPLETATO — 26 luglio 2026.

File decisioni/problemi; `./dev.py graph update`; link journal.

> **Note implementazione**: ingeriti piano/contratto/report; create/aggiornate pagine
> source, decision, entity e problem per AI Export, cash FX basis, drawdown storico e
> clipboard fallback. Graph update eseguito e nuovi nodi verificati.

### I5 — Chiusura

**Stato**: ✅ COMPLETATO — 27 luglio 2026.

F1/F2/F3 e Macrofase F ✅; Phase 0 pronta per archiviazione.

> **Note implementazione**: piano padre aggiornato con F1/F2/F3 completate. Catena
> verificata e indicizzata in [README.md](./README.md); la struttura dedicata
> `Release_2/Phase_0/01_signalMigration/02_aiExport` è già la sua collocazione archivio.

## 10. Gate finale

**Stato**: ✅ SUPERATO — 27 luglio 2026.

Completamento soltanto con:

- 54 profili versionati;
- catalog/contract fail-closed;
- zero leakage;
- quattro domini backend;
- cardinalità corretta;
- omission/coverage corrette;
- normalized return parity;
- last BUY separata;
- cash engine-owned;
- currency semantics corrette;
- band/semantic metadata operative;
- serializer sicuro;
- prompt frontend-owned;
- service standalone;
- cutover completati;
- legacy e quattro engine rimossi;
- comparison/benchmark/Measure preservati;
- API/check/build/test/i18n/docs verdi;
- review manuale;
- devWiki/graph e cross-link aggiornati.

## 11. Dipendenze

```text
A1 → A2 → A3 → Gate A
Gate A → B1 → B2 → B3/B4 → B5 → Gate B
Gate B → C1/C2 → C3 → C4 → Gate C
Gate C → D1 → D2/D3 → D4 → Gate D
Gate D → E1/E2 → E3/E4 → E5 → Gate E
Gate B → F1
Gate E + F1 → F2/F3/F4/F5/F6 → Gate F
Gate D + Gate F → G1/G2
Gate E + Gate F → G3
G1 + G2 + G3 → G4 → Gate G
Gate G → H1 → H2 → H3 → Gate H
Gate H → I1/I2 → I3 → I4 → I5 → Gate finale
```

## 12. Rollback

Nessun feature flag.

- prima del deploy ogni gate deve essere verde;
- legacy fixture restano;
- cutover revertibile come change set;
- rollback post-cutover = revert;
- mismatch client/backend fallisce chiuso e richiede reload/update.
