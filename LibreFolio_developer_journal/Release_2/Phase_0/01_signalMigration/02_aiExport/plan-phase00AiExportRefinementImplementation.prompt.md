# Piano applicativo: Phase 0 — AI Export dataset/analysis refinement

**Stato**: ⏸️ PAUSA — checkpoint 28 luglio 2026
**Data**: 28 luglio 2026

← Documento di consenso:
[GPT-5.6 refinement](./gpt5.6_refinementPlan.md)

← Piano precedente:
[AI Export Backend Snapshot](./plan-phase00AiExportBackendSnapshotImplementation.prompt.md)

← Piano padre:
[Phase 0 — Migrazione Segnali Backend](../plan-phase00SignalsBackendMigrationImplementation.prompt.md)

→ Checkpoint corrente:
[AI Export e aggregazione Signal Plugin](./plan-phase00AiExportCheckpointSignalAggregation.prompt.md)

## 1. Obiettivo

Sostituire il modello task → snapshot monolitico con:

```text
componenti granulari → fotografie dati composte/versionate → data-only
componenti granulari → fotografie richieste → istruzioni/contract → prompt
```

Backend possiede dati, calcoli, dipendenze, composizione, sampling e semantica.
Frontend possiede presentazione localizzata, prompt, memoria e clipboard.

## 2. Decisioni congelate

1. API resta `/api/v1`; schema/cataloghi/fotografie/analisi/contract restano versione
   `1`. Feature non rilasciata: hard replacement, nessuna compatibilità artificiale.
2. Due cataloghi: fotografie dati e analisi.
3. Periodo AI unico, indipendente dalla pagina, default 3M; 3M/6M/1Y/Custom.
4. Compact/Standard/Full mantengono stesso universo finanziario; bucket massimo
   30/14/7 giorni.
5. Nessun top-N, limite lotti/eventi, troncamento token o downgrade automatico.
6. FIFO: tutti open/partial + tutti closed nel periodo AI.
7. `All Applicable Data` = composizione ordinata/deduplicata.
8. `supports_web_research` e relativo contratto vengono eliminati. Prompt analisi
   ordina uso di sandbox/calcolatore e ricerca web quando disponibili, con fonti,
   data, separazione dati esterni/LibreFolio e divieto di inventare dati assenti.
9. Signal Plugin: auto-discovery/auto-description sì; inclusione automatica nei
   dataset no.
10. Nessun DB change previsto: provenance prezzo usa `source_plugin_key`.
11. Nessun frontend test prima della review manuale esplicita.
12. Wiki ingest/lint solo dopo approvazione funzionale.

## 3. Architettura target

### 3.1 Componenti granulari

Ogni `ComponentSpec` dichiara:

- `component_id` e versione;
- dominio/scope;
- output model Pydantic;
- dipendenze;
- semantica periodo;
- ordine canonico;
- builder;
- comportamento required/optional;
- aggregatore temporale eventuale.

`ComponentRegistry` valida unicità, modelli, dipendenze e cicli.
`AiExportBuildContext` request-scoped memoizza componenti/dipendenze.

Envelope pubblico:

```text
component_id
component_version
schema_id
schema_version
payload JSON-safe validato dal modello del componente
```

### 3.2 Fotografie dati

Ogni `DatasetSpec` dichiara ID/versione, dominio, i18n/icon, pagine/scope,
componenti required/optional, ordine, requisiti tecnici, period semantics, detail
supportati e applicabilità.

Composer:

1. risolve required/optional;
2. costruisce DAG;
3. memoizza;
4. deduplica per component ID/version;
5. emette ordine canonico;
6. fallisce sui required;
7. omette optional non disponibili, motivo solo in diagnostica interna.

`*.all_data` unisce i dataset applicabili, esclude se stesso e deduplica.

Semantica required:

- source disponibile con risultato vuoto = successo valido, con sezioni vuote/zero;
- source indisponibile o eccezione = source failure;
- analisi che richiede contenuto non vuoto = regola di applicabilità separata, 422;
- un portafoglio/broker vuoto non produce mai 503 soltanto perché vuoto.

### 3.3 Analisi

Ogni `AnalysisSpec` dichiara ID/versione, dominio/applicabilità, dataset
required/optional, instruction template ID/version, response contract ID/version e
supporto note. Backend risolve dati; frontend possiede template localizzati e fa
handshake fail-closed.

### 3.4 Dipendenze automatiche

Resolver centralizzato per Portfolio Engine/Service, LotsAnalysisService, Asset
prices/events, FX diretti/inversi/triangolati, SignalService, warm-up, conversioni e
provenance. Nessuna formula engine duplicata. Sync I/O dentro async usa
`asyncio.to_thread`.

## 4. Catalogo fotografie congelato

Tutte supportano Compact/Standard/Full.

| Dominio | Dataset ID | Contenuto |
|---|---|---|
| Portfolio | `portfolio.overview` | summary, tutte positions, allocations, cash, semantics/provenance |
| Portfolio | `portfolio.performance_flows` | performance, tutti contributori, flows, income, fees, taxes, reconciliation |
| Portfolio | `portfolio.technical` | prices/returns, indicators, states, breadth, events per tutte positions |
| Portfolio | `portfolio.fifo` | FIFO summary, tutti open/partial, closed nel periodo |
| Portfolio | `portfolio.all_data` | union deduplicata |
| Broker | `broker.overview` | summary, tutte positions, allocation/concentration, provenance |
| Broker | `broker.performance_flows` | performance, contributors, flows, income/costs, reconciliation |
| Broker | `broker.technical` | technical/breadth/events broker-scoped |
| Broker | `broker.fifo` | tutti lotti applicabili broker-scoped |
| Broker | `broker.all_data` | union deduplicata |
| Asset | `asset.overview` | identity, current market snapshot, position scope, provenance |
| Asset | `asset.position_performance` | positions per broker, cost/value/P&L, performance, lot detail applicabile |
| Asset | `asset.market_technical` | OHLC buckets, returns, indicators, states/events |
| Asset | `asset.all_data` | union deduplicata |
| FX | `fx.overview` | pair identity, current rate, conversion/provenance |
| FX | `fx.market_technical` | rate OHLC, returns/volatility, indicators, states/events |
| FX | `fx.direct_exposure` | esposizioni dirette base/quote e provenance conversioni |
| FX | `fx.all_data` | union deduplicata |

Totale: **18 dataset**. Nessun FIFO autonomo Asset/FX.

## 5. Catalogo analisi congelato

| Analysis ID | Required | Optional |
|---|---|---|
| `portfolio.pac_planning` | overview, performance_flows | — |
| `portfolio.rebalancing` | overview | performance_flows, technical |
| `portfolio.performance_attribution` | overview, performance_flows | — |
| `portfolio.income_review` | overview, performance_flows | — |
| `portfolio.fifo_review` | overview, fifo | — |
| `portfolio.technical_breadth` | overview, technical | — |
| `portfolio.description` | overview | performance_flows, technical |
| `broker.review` | overview, performance_flows | technical, fifo |
| `broker.cost_efficiency` | overview, performance_flows | — |
| `broker.concentration_context` | overview | technical |
| `broker.fifo_review` | overview, fifo | — |
| `asset.trend_analysis` | overview, market_technical | — |
| `asset.position_review` | overview, position_performance | market_technical |
| `asset.drawdown_recovery` | overview, market_technical | position_performance |
| `fx.trend_review` | overview, market_technical | — |
| `fx.conversion_timing` | overview, market_technical | direct_exposure |
| `fx.exposure_impact` | overview, direct_exposure | market_technical |

Totale: **17 analisi**.

- `asset_snapshot` → `asset.overview`, non analisi;
- `asset_pac_timing_context` rimosso;
- `fx.exposure_impact` visibile solo con dati reali `fx.direct_exposure`;
- synthetic snapshot e hidden-task list rimossi.

Il catalogo resta statico e descrive capability potenziali. `fx.exposure_impact`
diventa visibile quando il componente reale è implementato; per una coppia senza
esposizione la selezione fallisce a runtime come non applicabile (422), mai come source
failure (503). Non viene aggiunto un endpoint applicability separato in Phase 0.

## 6. API v1 target

`GET /api/v1/ai-export/catalog` restituisce schema/catalog versions, dataset catalog,
analysis catalog, i18n/icon/applicabilità/detail e riferimenti template/contract.

`POST /api/v1/ai-export/snapshot`:

```text
domain
selection: { kind: dataset|analysis, id, version }
detail_level
period: inclusive [start, snapshot_as_of]
target_currency
scope domain-specific
expected catalog/template/contract versions
```

Rimuovere `task`, `date_range`, `technical_window`, web flags, compact selection e
event limits.

Response: selection identity/version, target, exported period, calculation/warm-up
metadata, dataset manifest, sezioni deduplicate, methodology/semantics/provenance e
statistiche dimensionali informative.

Il payload delle sezioni è deliberatamente opaco nel client OpenAPI (`JsonValue`):
il backend lo valida tramite il modello Pydantic registrato, il frontend lo serializza
senza interpretarlo. Cataloghi, identity/versioni e manifest restano fortemente tipizzati.

Errori:

- version/template mismatch → 409;
- non applicabile → 422;
- broker access → 403;
- entity missing → 404;
- required source failure → 503;
- optional component/signal unavailable → omissione + diagnostica interna.

## 7. Periodo e adaptive buckets

Default 3M; 3M/6M/1Y/Custom DateRangePicker-style. Fine sempre
`snapshot_as_of`; frontend invia date ISO esatte. `calculation_range` può iniziare
prima per warm-up; output solo dentro `period`.

Convenzione:

- `T = (end-start).days + 1`;
- bucket offset half-open `[x_n,x_n+1)`;
- output oldest → newest;
- ultimo bucket parte esattamente da requested start;
- nessun overlap.

```text
f(x;P,M,K) = 1 + (K-1) * max(x-7,0)^P /
             (M^P + max(x-7,0)^P)
D(x;P,M,K) = max(1, round(f(x;P,M,K)))
```

| Detail | P | M | K |
|---|---:|---:|---:|
| Compact | 2 | 30 | 30 |
| Standard | 2 | 30 | 14 |
| Full | 2 | 30 | 7 |

| Detail | 90d | 180d | 365d |
|---|---:|---:|---:|
| Compact | 20 | 23 | 29 |
| Standard | 26 | 33 | 46 |
| Full | 35 | 49 | 75 |

Un `BucketPlan` condiviso per tutte le sezioni temporali della request.
I conteggi acceptance usano durate letterali T=90/180/365, non i preset calendario
3M/6M/1Y che possono variare per lunghezza mese/anno.

Aggregatori:

- price/FX: first/max/min/last/count;
- flows/income/fees/taxes: total/count;
- performance: start/end/min/max/return/P&L/external flows/reconciliation;
- continuous indicators: first/min/max/last per output;
- current state non bucketizzato;
- transitions/events mai mediati o troncati;
- dedup eventi solo plugin-defined;
- empty bucket esplicito con count 0 e null/zero semanticamente corretto.

## 8. Signal Plugin e volume

Riutilizzare `input_requirements`, `warmup_requirement()`, `compute()` e validazione
centrale SignalService.

Aggiungere:

- `validate_input()`;
- `validate_output()` più validazione centrale;
- `describe_for_ai()` obbligatorio;
- `describe_events_for_ai()` default vuoto;
- dedup eventi AI deterministico opzionale;
- descrizioni nel catalogo signal auto-discovered.

Volume:

- `AssetSourceProvider`/`FAProviderInfo`: `supports_meaningful_volume`, `volume_kind`;
- default false/unknown;
- audit esplicito provider;
- capability serie derivata dalle sorgenti osservate, mai dall'asset type;
- mixed/unknown/manual → false salvo dichiarazione autorevole;
- capability in `SignalExecutionContext`;
- MFI/OBV: capability AND validazione strutturale completa.

## 9. Frontend e prompt

```text
Export Data → fotografie applicabili
Request Analysis → analisi applicabili
```

Selector custom categorizzato, `SimpleSelect`; categoria determina data-only/full
prompt. Rimuovere render-mode artificiale e synthetic snapshot.

Memoria per user + page/entity: selection kind/id, detail, periodo, notes e
token-warning override fingerprint. Bump storage schema; vecchie entry ignorate.

Prompt order:

1. Analysis Objective and Task Steps.
2. Shared Verification Instructions: calculation sandbox, web search, unità/valute/
   segni/periodi, reconciliation, assumptions/limits.
3. Response Contract.
4. Snapshot Metadata and Dataset Manifest.
5. Snapshot Data YAML.
6. Additional LibreFolio Data.
7. Domain Notes.
8. User Notes.
9. Response Language.

Additional LibreFolio Data deriva dal catalogo reale/localizzato e mostra soltanto
dataset applicabili non già inclusi.

Token estimate informativa. Sopra soglia: warning inline, non modale, con
`Use Compact` e `Copy Anyway`; nessuna seconda request o modifica payload.
`Use Compact` compare soltanto se il manifest contiene sezioni bucketizzate per cui il
detail riduce davvero la granularità; per overview/FIFO non temporali resta solo
`Copy Anyway`.

Il catalogo espone ID e chiavi i18n, mai testo localizzato. Frontend validation deve
fallire se una chiave dataset/analysis/category non risolve in ogni locale supportata,
incluso l'elenco `Additional LibreFolio Data`.

Cleanup:

- `AiExportMenuV2.svelte` → `AiExportMenu.svelte`;
- `aiExportClipboardV2.ts` → `aiExportClipboard.ts`;
- nessun alias legacy.

## 10. Implementazione

### A — Freeze e artefatti

**Stato**: ✅ COMPLETATO — 28 luglio 2026.

- piano materializzato e cross-linkato;
- congelati 18 dataset, 17 analisi, IDs/versioni, periodo/detail e acceptance;
- vecchi todo contratto marcati superseded.

> **Note implementazione**: il piano è ora source of truth della seconda fase della
> migrazione segnali. API e contratti restano v1.

> **⚠️ Fuori pista**: rubber-duck architetturale ha confermato formula e conteggi, ma
> ha richiesto chiarimenti vincolanti: empty required ≠ source failure; FX exposure
> non applicabile = 422; section payload volutamente opaco in OpenAPI; i18n catalog
> completo e fail-closed; `Use Compact` solo quando riduce sezioni temporali; test
> conteggi su T letterale e mapping oldest/newest esplicito.

### B — Signal/source contracts

**Stato**: ✅ COMPLETATO — 28 luglio 2026.

- AI descriptions e validation hooks;
- volume capability provider/serie;
- MFI/OBV;
- registry/plugin/provider tests.

> **Note implementazione**: Signal Plugin ora espone descrizioni AI/eventi e hook
> input/output; SignalService li esegue con isolamento. Provider e serie dichiarano
> capability volume; MANUAL/unknown/mixed fail-closed. MFI/OBV richiedono capability
> semantica e validazione strutturale. Tutte le suite signal/provider/asset in scope
> passano; review read-only finale senza finding.

> **⚠️ Fuori pista**: un test Borsa history resta rosso per dipendenza
> `borsa_italiana_scraping` non allineata a un workstream concorrente; riproducibile
> anche senza queste modifiche, quindi non corretto in questo scope.

> **⚠️ Fuori pista — integrazione AI Export**: il gate aggregato ha rilevato che il
> runner tecnico legacy perdeva `SignalSourceCapability` dopo il caricamento prezzi:
> `volume_eligible=True` ma `volume_analyzed=False`. Corretto con derivazione unica
> e riusabile da `source_plugin_key` osservati e threading esplicito nel piano al momento
> dell'esecuzione, senza tornare alla regola errata “volume numerico = capability”.
> Gate canonico AI Export: 641 test passati.

### C — Temporal engine

**Stato**: ✅ COMPLETATO — 28 luglio 2026.

- periodo inclusivo;
- formula/delta/confini;
- `BucketPlan`;
- aggregatori;
- property/count tests.

> **Note implementazione**: aggiunto package `ai_export/temporal` con policy Decimal
> round-half-up, `BucketPlan` inclusivo e validato, aggregatori OHLC/flow/multi-output/
> eventi, slicing rigoroso `[start,end]` e warm-up clamp a `date.min`. Payload eventi
> JSON-safe e immutabili. 98 test focalizzati passano; il file è incluso nel gate
> canonico `./dev.py test services ai-export` e il selector runner è stato verificato.

### D — Catalog/component runtime

**Stato**: ✅ COMPLETATO — 28 luglio 2026.

- Component/Dataset/Analysis registries;
- cycle/version/applicability checks;
- dependency resolver/memoization;
- composer/all-data;
- section envelope e API schemas.

> **Note implementazione**: aggiunti registry immutabili Component/Dataset/Analysis,
> cataloghi congelati 18/17, composer required/optional, `all_data` con requiredness
> preservata, envelope `JsonValue`, builder production fail-closed, i18n/applicability
> metadata e memoization concorrente con diagnostica deduplicata. 118 test focalizzati
> passano; tre file test sono inclusi nel gate `./dev.py test services ai-export`.

> **⚠️ Fuori pista**: parent review ha corretto placeholder che potevano restituire
> fake data, optional promossi erroneamente a required in `all_data`, metadata analisi
> mancanti e validation enum/version debole. Review finale read-only: nessun finding.

### D2 — Domain build context

**Stato**: ✅ COMPLETATO — 28 luglio 2026.

- `BuildScope` validato: user, dominio, entity/broker scope, periodo, detail, valuta;
- `BucketPlan` condiviso;
- boundary `AsyncSession`;
- cache interna request-scoped per report/prezzi/FX/lotti/metadata raw;
- raw resources non serializzati come sezioni;
- I/O condiviso eseguito al massimo una volta.

> **⚠️ Fuori pista**: review d'integrazione pre-E ha rilevato che le sole dipendenze
> `SectionEnvelope` non bastano per condividere oggetti raw (PortfolioReport, prezzi,
> lotti) senza rieseguire I/O o esportare dati interni. D2 è quindi gate obbligatorio
> prima dei workstream dominio.

> **⚠️ Fuori pista — parent review**: `db_resource` con lock globale non reentrante
> deadlocka se un loader DB richiama un'altra resource DB con chiave diversa nello
> stesso task. Corretto con ownership/depth per-task, cleanup cancellation-safe e
> test nested/concurrent.

> **Note implementazione**: aggiunti `BuildScope`, mapping detail→bucket,
> `BucketPlan` condiviso, boundary `AsyncSession` e cache raw tipizzata request-scoped.
> `db_resource` serializza il DB ed è reentrant per stesso task con owner/depth;
> nested error/cancellation puliscono sempre lock e ownership. 106 test component
> runtime passano; regressioni nested/concurrent verificate anche tramite runner
> canonico.

### E1 — Portfolio/Broker

**Stato**: ⏳ DA ESEGUIRE.

- wave parallela `pb-financial`: summary/positions/allocations/performance/flows/
  reconciliation/FIFO/provenance;
- wave parallela `technical-shared`: prices/rates, returns/volatility,
  indicators/states/events/breadth per Portfolio/Broker/Asset/FX;
- integration gate: registry wiring, resource-key compatibility e dataset composition;
- componenti riusabili;
- nessun top-N;
- FIFO period-aware;
- technical/breadth su universo completo.

> **Note implementazione — financial wave**: completati 10 componenti Portfolio e
> 8 Broker per summary/positions/allocations/performance/flows/reconciliation/FIFO/
> provenance. Tutte le entità restano presenti; FIFO usa il periodo unico senza
> 7+3/top-N. 26 test focalizzati passano; parent review senza finding; test registrati
> nel runner canonico. E1 resta aperto in attesa technical-shared + wiring catalogo.

> **Note implementazione — technical-shared wave**: completati 14 componenti
> Portfolio/Broker/Asset/FX. Bundle fisso preserva il Full corrente: 20 signal Asset/
> Portfolio/Broker, 12 FX, rispettivamente 19/14 annotation events, uguali in tutti
> i detail level; cambia solo BucketPlan. Corretto breadth single-level:
> `below_zero/at_zero/above_zero` invece di classificare ogni ROC/PPO/AROON come
> “zero”. 43 test focalizzati passano; file nel runner canonico. E1/E2 attendono
> soltanto wiring catalogo/composer.

### E2 — Asset/FX

**Stato**: ⏳ DA ESEGUIRE.

- wave parallela Asset core: identity/position/performance/lotti;
- wave parallela FX core: identity/current/provenance/direct exposure;
- integration gate comune: registry wiring, dependency/provenance e dataset composition;
- overview, position/performance, market/technical;
- direct FX exposure;
- auto price/FX dependencies e provenance;
- Asset lots solo nella fotografia posizione.

> **Note implementazione — Asset core wave**: completati 8 componenti identity/
> market/position/performance/lotti/provenance. Tutte le righe broker restano
> presenti; aggregate cost/value/performance usano subset coerenti con coverage
> esplicita, evitando P&L/return falsi su dati parziali. Lotti closed senza
> `closing_date` vengono omessi come degraded, non trattati come open. 32 test
> focalizzati passano; regressioni registrate nel runner canonico. E2 resta aperto
> per FX fix, technical-shared e wiring catalogo.

> **Note implementazione — FX core wave**: completati 5 componenti identity/current/
> provenance/direct exposure. Corretto un doppio FX sulle posizioni: `current_value`
> resta target-currency engine-owned, native amount deriva solo dalla valuta di
> valutazione autorevole con `quote_base_quantity`; mismatch usa
> `ENGINE_VALUATION` senza rate/native inventati. Cash/position rows completi,
> no look-through/top-N, empty exposure valido. 25 test focalizzati e regressioni
> forced-mismatch passano; file nel runner canonico. E2 resta aperto per
> technical-shared e wiring catalogo.

### F — Analysis/prompt/API

**Stato**: ⏳ DA ESEGUIRE.

- 17 AnalysisSpec;
- template/contract migration;
- sandbox/search instructions;
- Additional Data catalog-driven;
- endpoint v1 hard replacement;
- problem details/auth;
- `./dev.py api sync` e codegen guard.

### G — Frontend hard cutover

**Stato**: ⏳ DA ESEGUIRE.

- menu due categorie;
- periodo unico;
- tooltip/memory/clipboard;
- warning inline;
- rimozione snapshot/hidden/V2 naming;
- quattro pagine e i18n.

### H — Developer Guide

**Stato**: ⏳ DA ESEGUIRE.

Creare sezione top-level AI Export:

1. Overview and Architecture.
2. Data Components and Composed Snapshots.
3. Analysis Profiles and Prompt Composition.
4. Time Range and Adaptive Sampling.
5. Temporal Buckets and Aggregation Semantics.
6. Technical Indicators and Signal Plugins.
7. FX, Prices and Automatic Dependencies.
8. Versioning, Validation and Failure Semantics.
9. Frontend Integration and UX.
10. Testing and Extension Guide.

EN-only; aggiornare nav, assorbire il monolite esistente, aggiornare Signal Plugin
Guide e user docs.

### I — Validation, review e cleanup

**Stato**: ⏳ DA ESEGUIRE.

1. backend test/API sync;
2. review manuale Dashboard/Broker/Asset/FX;
3. solo dopo approvazione: frontend test/check/build/E2E, i18n, MkDocs;
4. dead-code cleanup;
5. report/piano;
6. wiki ingest/lint/graph.

## 11. Dipendenze

```text
A
├── B Signal/source
├── C temporal
└── D catalog/runtime

B + C + D
└── D2 BuildScope/resource cache

D2
├── E1 Portfolio/Broker
└── E2 Asset/FX

E1 + E2 + D
└── F analysis/prompt/API
    ├── G frontend
    └── H docs

F + G + H
└── backend validation
    └── manual review
        └── frontend/docs validation
            └── cleanup/knowledge
```

## 12. Acceptance

Backend:

- 18 dataset, 17 analyses;
- deterministic/versioned registries e cycle detection;
- all-data dedup/memoization;
- unified period e warm-up escluso;
- formula properties + conteggi 90/180/365;
- conteggi su T letterale e mapping oldest.start/newest.end senza off-by-one;
- aggregatori e reconciliation;
- nessun entity/event truncation;
- FIFO period semantics;
- plugin AI descriptions e semantic volume;
- automatic FX/price/warm-up;
- auth/scope/version fail-closed.

Frontend, solo post-review:

- category selector/page filtering;
- completezza chiavi catalogo in EN/IT/FR/ES;
- period/request/memory;
- prompt order + sandbox/search;
- catalog-driven Additional Data;
- data-only/analysis;
- warning/Copy Anyway;
- nessun web flag/synthetic/hidden task;
- localization;
- four-page desktop/mobile E2E.

## 13. Regola avanzamento

Dopo ogni step:

1. segnare stato e data;
2. aggiungere `> **Note implementazione**: ...`;
3. aggiungere `> **⚠️ Fuori pista**: ...` per deviazioni/scoperte;
4. aggiornare subito dipendenze e README.

→ Follow-up/checkpoint:
[AI Export e aggregazione Signal Plugin](./plan-phase00AiExportCheckpointSignalAggregation.prompt.md)
