Tutte le dimensioni sono token-equivalenti stimati (`caratteri renderizzati / 4`) sul prompt finale copiabile dalla UI, non token esatti né JSON canonico grezzo.

# Report Phase 0 - AI Export Semantic Composition V1

**Data**: 31 luglio 2026
**Run autorevole corrente**: `real_prompt_probe/20260731T165707.644762Z`
**Run baseline**: `real_prompt_probe/20260731T102457.551232Z`
**Run FX parziale finale**: `targeted_partial_fx_probe/20260731T172828.344713Z`
**Comparatore FX parziale precedente**: `targeted_partial_fx_probe/20260731T171520.013608Z`
**Tabelle/dati aggregati**: `/tmp/libreFolio_ai_export_semantic_report.md` e `.json`
**Profilo**: `tuning-v2` · **Utente**: `marco`
**Stato**: cutover V2, proiezioni, dataset, FX parziale, guida localizzata, test, docs e report completati; commit/cleanup/wiki/release fuori scope

---

## 1. Executive summary

Il problema residuo non era sintattico ma semantico: alcune Analysis finanziarie
includevano l'intero dataset tecnico e diventavano quasi interamente tecniche
(fino a ~606.000 token-equivalenti stimati e quota tecnica >98%). È stato eseguito
un **hard cutover V2** dello stack runtime (nessun fallback V1):

- `schema_version = 2`, `catalog_version = 2`;
- catalogo passato a **56 componenti, 25 dataset, 16 Analysis**;
- **11 nuovi componenti** backend focalizzati di contesto/copertura tecnica;
- **7 nuovi dataset pubblici** semantici, selezionabili in Export Data ed **esclusi
  dalle tuple `source_specs` di `*.all_data`** per evitare duplicazione;
- correzione FX con storia sorgente parziale (6M/1Y non falliscono più se esiste
  un dataset coerente costruibile);
- guida Additional LibreFolio Data **guidata dal catalogo e localizzata EN/IT/FR/ES**.

Il corpus autorevole corrente è **285/285 prompt, 0 fallimenti** (il baseline aveva
21 fallimenti FX 6M/1Y). Le Analysis finanziarie dominate dalla tecnica sono state
ridotte drasticamente (Portfolio Description -97,46%, Rebalancing -96,28%, Broker
Review -95,22%, Broker Concentration -98,51%, Asset Position Review -87,57%, FX
Exposure Impact -80,17% sulla mediana), mentre le Analysis tecniche esplicite
(`portfolio.technical_breadth`, `asset.trend_analysis`, `fx.trend_review`,
`fx.conversion_timing`) mantengono Signal, history, summary, latest ed eventi
completi e restano Heavy dove appropriato.

---

## 2. Problema iniziale

Nel run baseline `20260731T102457.551232Z`, sul caso rappresentativo:

| Analysis | Mediana baseline (token-eq. stimati) | Quota tecnica mediana |
|---|---:|---:|
| `portfolio.description` | 262.243,88 | 97,99% |
| `portfolio.rebalancing` | 262.282,38 | 97,97% |
| `broker.review` | 232.038,25 | 96,86% |
| `broker.concentration_context` | 226.928,00 | 98,94% |
| `asset.position_review` | 27.278,50 | 91,83% |

Queste Analysis ricevevano l'intero dataset `*.technical` (tutti i 20 Signal Asset
o 12 Signal FX, history completa, eventi completi) come dataset opzionale, pur
avendo obiettivi finanziari o di concentrazione. `asset.position_review` riceveva
la stessa profondità di `asset.trend_analysis`. Le soluzioni escluse per contratto
erano: token cap silenziosi, troncamento finale, proiezioni tecniche costruite nel
frontend, eliminazione indiscriminata dei Signal, riduzione globale del dataset
tecnico, abbassamento generalizzato di Compact/Standard/Full. La soluzione richiesta
era migliorare la **composizione backend** e i **contratti delle Analysis**.

---

## 3. Confine architetturale (frontend non calcola/seleziona)

Il backend possiede: calcoli e dati finanziari; Signal e metadata plugin-owned;
selezione delle proiezioni tecniche; Signal/output inclusi; profondità history per
componente; event policy task-specific; coverage/staleness/omission reasons;
composizione Component → Dataset → Analysis; contratto dei suggerimenti Additional
Export.

Il frontend possiede: rendering sicuro; tabelle e ordine del prompt; localizzazione
EN/IT/FR/ES; label e percorsi UI; istruzioni e response contract; riferimenti
pubblici A#/B#/F#; clipboard e metriche finali. **Non calcola metriche finanziarie,
non sceglie i Signal, non filtra righe tecniche.** Tutta la selezione è dichiarata
dai contratti backend (`AnalysisSpec.required_dataset_ids`/`optional_dataset_ids`)
o da dataset/componenti backend dedicati; nel renderer non esiste alcuna logica del
tipo «se analysis == rebalancing seleziona EMA50/RSI/NATR».

I riferimenti pubblici usano **A#/B#/F#/L#** (Asset/Broker/FX/lotto FIFO); nessun
ID DB numerico compare nei payload, incluse `broker_scope`, `broker_ids`,
`asset_ids`, array, liste, tabelle e valori isolati (`FX1` → `F1`).

---

## 4. Inventario dei mattoncini e riuso

### 4.1 Componenti/risorse esistenti riutilizzati (nessun ricalcolo)

I nuovi builder leggono gli **stessi resource bundle già memoizzati**; non leggono né
filtrano payload già renderizzati e non duplicano I/O o calcolo dei Signal:

| Risorsa condivisa | Ruolo | Riutilizzata da |
|---|---|---|
| `TechnicalUniverseBundle` (`load_technical_universe_bundle`) | universo Asset eleggibili, pesi, price results, Signal | coverage/market-context/events Portfolio e Broker |
| `PriceResultsResource` (`load_asset_price_results`) | serie prezzi e Signal per Asset | coverage e position-context Asset |
| `FxTechnicalBundle` (`load_fx_technical_bundle`) | rate series + Signal FX | coverage e market-summary FX |
| `FxRateSeriesResource` | serie rate FX osservate/backfilled | coverage FX e volatilità |
| metadata `SignalPlugin` | codici Signal, stati plugin-owned | tutte le aggregazioni di coverage |
| `signal_results_to_discrete_events` | derivazione eventi discreti dai Signal | context-events, event-digest, latest-event |

I dataset e componenti finanziari e FIFO (`*.overview`, `*.performance_flows`,
`*.fifo`, `*.direct_exposure`) sono **riutilizzati invariati**. I dataset tecnici
completi (`*.technical`, `*.market_technical`) restano intatti e continuano a usare
tutti i 20/12 Signal Asset/FX.

### 4.2 Disaccoppiamento delle dipendenze envelope false

Dove il builder legge già il resource cache, sono state rimosse le dipendenze
envelope che ricostruivano l'intero payload indicator completo: breadth ed eventi
Portfolio/Broker e gli eventi Asset/FX non costruiscono più il payload indicator
completo. Le dipendenze raw restano nei loader condivisi; il full technical mantiene
ordine e output invariati.

---

## 5. Nuovi mattoncini creati (11 componenti)

Tutti i componenti sono `PeriodBehavior.WINDOWED`, deterministici, con `extra=forbid`.
Le famiglie di payload sono: `TechnicalCoveragePayload` (coverage),
`TechnicalMarketContextPayload` (schede sintetiche + history/eventi opzionali),
`TechnicalContextEventsPayload` (eventi strutturali ristretti) e
`TechnicalEventDigestPayload` (digest aggregato per annotazione).

| Component | Purpose | Source calculations | Consumers | Fields (principali) | History policy | Event policy | Coverage semantics |
|---|---|---|---|---|---|---|---|
| `portfolio.technical_coverage` | copertura tecnica dell'universo Portfolio | `TechnicalUniverseBundle`, osservazioni prezzo, aggregazione Signal | `portfolio.technical_summary`, `portfolio.asset_snapshot`, `portfolio.asset_comparison` | considered/eligible/covered entity count, eligible/covered weight ratio, per-entity observation_count, available_start/end, staleness, requested/included/omitted signal count, omission_reasons; per-signal ok/partial/unavailable/failed | nessuna | nessuno | copre = ≥1 Signal incluso; pesi eligible vs covered |
| `portfolio.asset_market_context` | scheda tecnica sintetica per Asset (confronto orizzontale) | universe bundle, ritorni sintetici, Signal latest | `portfolio.asset_snapshot`, `portfolio.asset_comparison` | current value/date, return 1M/3M/periodo, min/max+date, EMA20/50/200, KAMA20, RSI14+stato, NATR14, ATR14, volatilità, Bollinger, relazioni price/EMA, latest event | opzionale via detail (schede: 0) | 1 latest event per entità (`max_per_entity=1`) | ereditata dal coverage; value_unit = valuta coerente o `unavailable` |
| `portfolio.context_events` | eventi strutturali recenti per Asset, ristretti | eventi discreti dai Signal, allowlist strutturale | `portfolio.asset_comparison` | detected/exported count, eventi per entità (date, key, signal_code, semantic_description, direction, values) | nessuna | ≤4 eventi strutturali per entità, allowlist chiavi | conteggio detected vs exported |
| `portfolio.event_digest` | digest aggregato eventi recenti del Portfolio | eventi discreti raggruppati per (signal_code, key) | `portfolio.technical_summary` | detected/included count, per annotazione: event_count, latest_date, upward/downward count | nessuna | tutti gli eventi negli ultimi 30 giorni, altrimenti l'ultimo per annotazione (`all_last_30d_else_latest_per_annotation_v1`) | conteggio detected vs included |
| `broker.technical_coverage` | copertura tecnica degli Asset broker-scoped | universe bundle broker-scoped | `broker.technical_summary`, `broker.asset_comparison` | come `portfolio.technical_coverage` | nessuna | nessuno | copertura aggregata broker-scoped |
| `broker.asset_market_context` | scheda tecnica uniforme per Asset del Broker | universe bundle broker-scoped | `broker.asset_comparison` | come `portfolio.asset_market_context` | opzionale via detail | 1 latest event per entità | ereditata dal coverage |
| `broker.context_events` | eventi strutturali ristretti degli Asset del Broker | eventi discreti allowlist | `broker.asset_comparison` | come `portfolio.context_events` | nessuna | ≤4 per entità | detected vs exported |
| `asset.technical_coverage` | copertura tecnica della singola posizione | `PriceResultsResource`, Signal dell'Asset | `asset.position_context` | 1 entità: observation_count, available_start/end, staleness, requested/included/omitted signal count, omission_reasons | nessuna | nessuno | considered/eligible/covered = 1; covered se ≥1 Signal incluso |
| `asset.position_market_context` | contesto tecnico mirato della posizione | Signal dell'Asset, ritorni, short trend + volatilità | `asset.position_context` | scheda con short trend, EMA20/ATR14/Bollinger quando disponibili, RSI, NATR | limitata per detail: Compact 0 / Standard 6 / Full 12 righe | ≤12 eventi strutturali per Asset (`asset_position_context_v1`) | 1 entità, value_unit coerente |
| `fx.technical_coverage` | copertura tecnica della coppia FX + storia sorgente parziale | `FxTechnicalBundle`, `FxRateSeriesResource` | `fx.market_context` | 1 entità: observation_count (osservate), available_start/end, staleness, requested/included/omitted signal count | nessuna | nessuno | supporta history_coverage parziale (vedi §8) |
| `fx.market_summary` | rate/return/volatility/trend/event sintetici FX | bundle FX, volatilità daily-return, momentum | `fx.market_context` | current rate+provenance, return 1M/3M/periodo, volatilità, EMA50/200/KAMA20, RSI14, PPO/ROC quando disponibili, latest event | limitata per detail: Compact 0 / Standard 4 / Full 8 righe | ≤8 eventi strutturali (`fx_market_context_v1`) | 1 entità; volatilità solo con ≥2 daily returns |

I minimi prezzi mancanti restano invariati: *latest available observation on or
before the requested date; never use future data*. Le osservazioni «vere» escludono
i backward-fill nel calcolo di coverage e volatilità.

---

## 6. Nuovi dataset pubblici (7) e composizione

Il catalogo passa da 18 a 25 dataset. I 7 nuovi dataset sono selezionabili, hanno
label/description i18n e sono **esclusi dalle `source_specs` di `*.all_data`**
(`*.all_data` continua a comporre solo overview/performance_flows/technical/fifo o gli
equivalenti di dominio):

| Dataset nuovo | Componenti | Consumer principale (optional) | Mediana / max (token-eq. stimati) |
|---|---|---|---:|
| `portfolio.technical_summary` | technical_coverage, technical_breadth, event_digest | `portfolio.description` | 1.873,00 / 1.874,00 |
| `portfolio.asset_snapshot` | technical_coverage, asset_market_context | `portfolio.pac_planning` | 2.458,00 / 2.463,25 |
| `portfolio.asset_comparison` | technical_coverage, asset_market_context, technical_breadth, context_events | `portfolio.rebalancing` | 4.899,25 / 4.904,50 |
| `broker.technical_summary` | technical_coverage, technical_breadth | `broker.concentration_context` | 1.501,25 / 1.502,25 |
| `broker.asset_comparison` | technical_coverage, asset_market_context, technical_breadth, context_events | `broker.review` | 4.252,25 / 4.257,00 |
| `asset.position_context` | technical_coverage, position_market_context | `asset.position_review` | 1.400,00 / 1.516,00 |
| `fx.market_context` | technical_coverage, market_summary | `fx.exposure_impact` | 1.205,50 / 1.311,25 |

**Tutti i 63 prompt dei nuovi dataset semantici sono Light**; massimo assoluto
**4.904,50** (`portfolio.asset_comparison`). Sono proiezioni derivate: escluderle da
`*.all_data` evita di duplicare i medesimi dati nel dataset aggregato.

---

## 7. Composizione prima/dopo per ogni Analysis

Token-equivalenti = mediana della matrice period/detail salvo diversa indicazione.
`Tech` = quota tecnica %. `History`/`Events` = righe history / eventi (mediana).

| Analysis | Dataset baseline | Dataset V2 | Nuovi componenti | Prev token-eq. | Curr token-eq. | Δ% | Tech prev/curr | History prev/curr | Events prev/curr | Quality assessment |
|---|---|---|---|---:|---:|---:|---|---|---|---|
| `portfolio.description` | overview, performance_flows, technical | overview, performance_flows, **technical_summary** | technical_coverage + technical_breadth + event_digest | 262.243,88 | 6.654,50 | **-97,46** | 97,99/16,01 | 5.316/0 | 2.076/0 | direzione/momentum aggregati senza history per-Asset; ora Light |
| `portfolio.rebalancing` | overview, performance_flows, technical | overview, performance_flows, **asset_comparison** | technical_coverage + asset_market_context + technical_breadth + context_events | 262.282,38 | 9.761,62 | **-96,28** | 97,97/41,97 | 5.316/0 | 2.076/48 | confronto orizzontale uniforme; Light(3M)/Medium |
| `portfolio.technical_breadth` | overview, technical | overview, technical (completo) | — | 259.643,00 | 260.357,50 | +0,28 | 98,87/98,82 | 5.316/5.316 | 2.076/2.074,5 | tecnica esplicita preservata; resta Heavy |
| `portfolio.pac_planning` | overview, performance_flows | overview, performance_flows, **asset_snapshot** | technical_coverage + asset_market_context | 5.310,12 | 7.191,38 | +35,43 | 0/23,02 | 0/0 | 0/0 | aggiunge contesto per-Asset subordinato; resta Light |
| `portfolio.performance_attribution` | overview, performance_flows | overview, performance_flows | — | 5.270,38 | 5.396,12 | +2,39 | 0/0 | 0/0 | 0/0 | nessuna tecnica; stabile Light |
| `portfolio.income_review` | overview, performance_flows | overview, performance_flows | — | 5.242,38 | 5.225,62 | -0,32 | 0/0 | 0/0 | 0/0 | invariato; stabile Light |
| `portfolio.fifo_review` | overview, fifo | overview, fifo | — | 6.184,38 | 6.327,50 | +2,31 | 0/0 | 0/0 | 0/0 | invariato; stabile Light |
| `broker.review` | overview, performance_flows, technical, fifo | overview, performance_flows, **asset_comparison**, fifo | technical_coverage + asset_market_context + technical_breadth + context_events | 232.038,25 | 11.093,38 | **-95,22** | 96,86/32,59 | 4.873/0 | 1.907/44 | holdings/performance/costi/FIFO primari; Medium |
| `broker.concentration_context` | overview, technical | overview, **technical_summary** | technical_coverage + technical_breadth | 226.928,00 | 3.391,12 | **-98,51** | 98,94/25,31 | 4.873/0 | 1.907/0 | dominato dalla concentrazione; Light |
| `broker.cost_efficiency` | overview, performance_flows | overview, performance_flows | — | 4.629,38 | 4.774,50 | +3,13 | 0/0 | 0/0 | 0/0 | invariato; stabile Light |
| `broker.fifo_review` | overview, fifo | overview, fifo | — | 4.943,50 | 5.093,25 | +3,03 | 0/0 | 0/0 | 0/0 | invariato; stabile Light |
| `asset.position_review` | overview, position_performance, market_technical | overview, position_performance, **position_context** | technical_coverage + position_market_context | 27.278,50 | 3.391,88 | **-87,57** | 91,83/28,08 | 443/6 | 173/6,5 | più profondo del Rebalancing, più mirato del Trend Analysis; Light |
| `asset.trend_analysis` | overview, market_technical | overview, market_technical (completo) | — | 26.889,75 | 27.324,38 | +1,62 | 93,15/92,64 | 443/443 | 173/172 | tecnica esplicita completa; Medium/Heavy per detail |
| `fx.trend_review` | overview, market_technical | overview, market_technical (completo) | — | 16.698,50 | 20.972,62 | +25,60 | 92,17/92,34 | 232/286 | 127/177 | recupera 6M/1Y parziale + coverage; Medium |
| `fx.conversion_timing` | overview, market_technical, direct_exposure | overview, market_technical (completo), direct_exposure | — | 17.883,50 | 22.045,88 | +23,27 | 86,07/87,85 | 232/286 | 127/177 | tecnica centrale; recupera 6M/1Y; Medium |
| `fx.exposure_impact` | overview, direct_exposure, market_technical | overview, direct_exposure, **market_context** | technical_coverage + market_summary | 17.889,25 | 3.547,12 | **-80,17** | 86,03/22,19 | 232/4 | 127/6,5 | contesto direzionale senza history completa; Light |

Contratti V2 required/optional effettivi (da `analyses/catalog.py`): Description
`[overview] + (performance_flows, technical_summary)`; Rebalancing `[overview] +
(performance_flows, asset_comparison)`; PAC `[overview, performance_flows] +
(asset_snapshot)`; Broker Review `[overview, performance_flows] + (asset_comparison,
fifo)`; Concentration `[overview] + (technical_summary)`; Position Review `[overview,
position_performance] + (position_context)`; FX Exposure Impact `[overview,
direct_exposure] + (market_context)`. Le Analysis tecniche esplicite mantengono
`*.technical`/`*.market_technical` completo come required.

---

## 8. FX con storia parziale

Nel baseline, FX 6M/1Y falliva prima del payload (21 fallimenti). In V2 il loader
warm-up-inclusive usa `convert_bulk(..., raise_on_error=False)`, salta solo le date
precedenti alla prima osservazione disponibile, mantiene ordine e invariante
no-future, e resta fail-closed solo se: nessun rate valido on-or-before
`snapshot_as_of` (`fx_no_usable_rate`), coppia/direzione non risolvibile
(`fx_pair_unresolvable`), payload minimo non costruibile
(`fx_minimum_payload_unavailable`). La storia parziale è **successo con warning**.

### 8.1 Run parziale finale `20260731T172828.344713Z` (3/3, 0 failure)

| Voce | Valore |
|---|---|
| Prompt | 3/3 generati, 0 falliti; 1 Light + 2 Medium; secret scan `passed`; source/production DB invariati |
| Requested period | 2025/07/31 → 2026/07/31 (**366** giorni calendario) |
| Available period | 2026/04/30 → 2026/07/31; ultima osservazione sorgente 2026/07/30, 2026/07/31 backward-filled |
| Coverage | **93/366** giorni calendario = **25,4098%**; `complete: false`; reason/warning `insufficient_source_history` |
| Observations | 66 osservate + 27 backward-filled |
| Signals included | **10/12 come PARTIAL**: bollinger_20_2, ema_20, ema_50, kama_20, macd_12_26_9, ppo_12_26_9, roc_20, rsi_14, sma_50, stoch_rsi_14_3 |
| Signals omitted | **2/12**: `ema_200`, `sma_200` — reason `insufficient_history` (93 input giornalieri utilizzabili < minimo 200) |
| Result status | success con warning (nessun fallimento di snapshot) |
| Warning | `insufficient_source_history` |

### 8.2 Correzione rispetto al comparatore `20260731T171520.013608Z`

Nel run precedente la coverage calendario era già corretta (25,4098%, 66
osservazioni), ma **tutti i 12 Signal venivano omessi** con reason
`insufficient_input_coverage` (`included_signal_count = 0`). La correzione finale
gestisce i Signal **individualmente**: le istanze il cui requisito minimo è
soddisfatto dai 93 input giornalieri (66 osservati + 27 backward-filled) sono
calcolate come **PARTIAL e incluse**, dichiarando il warm-up di stabilizzazione
incompleto; solo le due istanze con minimo 200 punti (`ema_200`, `sma_200`) restano
omesse con `insufficient_history`. Una
singola istanza non calcolabile non fa fallire dataset o snapshot. La correzione
riguarda esclusivamente la classificazione per-istanza; coverage calendario,
osservazioni e no-future erano già corretti nel comparatore.

---

## 9. Additional LibreFolio Data (localizzata, guidata dal catalogo)

Ogni `AnalysisSpec` dichiara una lista esplicita di `AdditionalExportSuggestion`
(anche vuota). Il frontend rende, per ogni suggerimento non già incluso: label
pubblica localizzata, contenuto, motivo, percorso UI localizzato, Export Data label,
periodo/detail consigliati, necessità (tutte `optional` in V2), con il dataset ID
solo tra parentesi come riferimento tecnico secondario. Testi verificati in
`frontend/src/lib/i18n/{en,it,fr,es}.json` (`aiExport.additionalData.*`,
`aiExport.dataset.*`).

### 9.1 Esempio user-friendly (italiano)

> **Altri dati LibreFolio** — *Dati tecnici portafoglio* (Facoltativo)
> **Perché può essere utile**: usalo quando servono realmente la history tecnica
> completa e tutti i Signal disponibili.
> **Per ottenere questi dati:**
> 1. Apri LibreFolio.
> 2. Apri **Opzioni AI Export**.
> 3. Seleziona **Esporta dati**.
> 4. Pagina: **Portafoglio**.
> 5. Dataset: **Dati tecnici portafoglio**.
> 6. Periodo **3 mesi**, Dettaglio **Standard**.
> *(riferimento tecnico: `portfolio.technical`)*

Istruzione comune all'LLM (localizzata): richiedere altri dati LibreFolio solo
quando materialmente utili, usando la label pubblica localizzata, spiegando il
perché, indicando il percorso UI localizzato, raccomandando periodo/detail,
distinguendo required da optional, e senza chiedere mai il solo dataset ID interno.

### 9.2 Aggregato suggerimenti per tutte le 16 Analysis

| Analysis | Export label localizzata (IT) | Motivo | Percorso UI (IT) | Periodo | Detail | Necessità |
|---|---|---|---|---|---|---|
| `portfolio.pac_planning` | Dati tecnici portafoglio | history tecnica completa e Signal | Esporta dati → Portafoglio | 3 mesi | Standard | Facoltativo |
| `portfolio.rebalancing` | Dati tecnici portafoglio | history tecnica completa e Signal | Esporta dati → Portafoglio | 1 anno | Compatto | Facoltativo |
| `portfolio.rebalancing` | Lotti FIFO portafoglio | identità/anzianità/custody/FIFO realizzato | Esporta dati → Portafoglio | 1 anno | Standard | Facoltativo |
| `portfolio.performance_attribution` | Lotti FIFO portafoglio | dettaglio FIFO realizzato | Esporta dati → Portafoglio | 1 anno | Standard | Facoltativo |
| `portfolio.income_review` | — | nessun export aggiuntivo consigliato (`none`) | — | — | — | — |
| `portfolio.fifo_review` | Performance e flussi portafoglio | performance/flussi/redditi/costi/imposte | Esporta dati → Portafoglio | 1 anno | Standard | Facoltativo |
| `portfolio.technical_breadth` | Performance e flussi portafoglio | performance/flussi del periodo | Esporta dati → Portafoglio | 1 anno | Standard | Facoltativo |
| `portfolio.description` | Dati tecnici portafoglio | history tecnica completa e Signal | Esporta dati → Portafoglio | 3 mesi | Standard | Facoltativo |
| `portfolio.description` | Lotti FIFO portafoglio | dettaglio FIFO realizzato | Esporta dati → Portafoglio | 1 anno | Compatto | Facoltativo |
| `broker.review` | Dati tecnici broker | history tecnica completa e Signal | Esporta dati → Broker | 3 mesi | Standard | Facoltativo |
| `broker.cost_efficiency` | Lotti FIFO broker | dettaglio FIFO realizzato | Esporta dati → Broker | 1 anno | Standard | Facoltativo |
| `broker.concentration_context` | Confronto Asset del Broker | confronto tecnico uniforme degli Asset | Esporta dati → Broker | 3 mesi | Standard | Facoltativo |
| `broker.fifo_review` | Performance e flussi broker | performance/flussi/costi | Esporta dati → Broker | 1 anno | Standard | Facoltativo |
| `asset.trend_analysis` | Performance posizione asset | posizione reale, costo, valore, P&L, ruolo FIFO | Esporta dati → Asset | 1 anno | Standard | Facoltativo |
| `asset.position_review` | Dati di mercato e tecnici asset | history tecnica completa e Signal | Esporta dati → Asset | 1 anno | Standard | Facoltativo |
| `fx.trend_review` | Esposizione FX diretta | esposizione diretta di cassa/posizione alla coppia | Esporta dati → FX | 3 mesi | Standard | Facoltativo |
| `fx.conversion_timing` | Esposizione FX diretta | esposizione diretta alla coppia | Esporta dati → FX | 3 mesi | Standard | Facoltativo |
| `fx.exposure_impact` | Dati di mercato e tecnici FX | history tecnica completa e Signal | Esporta dati → FX | 1 anno | Compatto | Facoltativo |

---

## 10. Confronto dimensionale col run precedente

### 10.1 Corpus corrente `20260731T165707.644762Z`

| Prodotti | Falliti | Light | Medium | Heavy | Very Heavy | Min | Mediana | P90 | Max |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 285 | 0 | 217 | 42 | 26 | 24 | 640,75 | 4.137,50 | 39.807,25 | 602.205,25 |

Catalogo scoperto dal probe: **25 dataset, 16 Analysis**; 63 prompt nuovi dataset
semantici; 4 `*.all_data` esclusi; UI/probe byte-equivalenti; source DB read-only.

### 10.2 Distribuzioni (da `/tmp/libreFolio_ai_export_semantic_report.md`)

**Per modalità**

| Mode | Count | L | M | H | VH | Mediana | P90 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| analysis | 96 | 64 | 25 | 7 | 6 | 6.586,88 | 38.773,50 | 602.205,25 |
| data | 189 | 153 | 17 | 19 | 18 | 2.457,25 | 54.417,50 | 600.027,00 |

**Per dominio**

| Domain | Count | L | M | H | VH | Mediana | P90 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| asset | 48 | 33 | 13 | 2 | 0 | 1.438,62 | 35.864,75 | 55.943,25 |
| broker | 78 | 63 | 6 | 9 | 9 | 3.509,88 | 168.471,75 | 524.186,50 |
| fx | 54 | 33 | 21 | 0 | 0 | 2.542,38 | 27.911,50 | 41.949,50 |
| portfolio | 105 | 88 | 2 | 15 | 15 | 4.903,50 | 200.190,25 | 602.205,25 |

**Per detail**

| Detail | Count | L | M | H | VH | Mediana | P90 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| compact | 95 | 73 | 14 | 8 | 8 | 3.487,75 | 26.388,75 | 266.177,00 |
| standard | 95 | 72 | 15 | 8 | 8 | 3.924,00 | 37.247,75 | 396.565,50 |
| full | 95 | 72 | 13 | 10 | 8 | 4.137,50 | 54.417,50 | 602.205,25 |

**Per periodo**

| Period | Count | L | M | H | VH | Mediana | P90 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1Y | 111 | 82 | 18 | 11 | 9 | 4.686,25 | 41.949,50 | 602.205,25 |
| 3M | 111 | 84 | 18 | 9 | 9 | 4.251,50 | 21.767,25 | 254.538,00 |
| 6M | 63 | 51 | 6 | 6 | 6 | 2.424,50 | 35.864,75 | 377.811,50 |

### 10.3 Confronto stabile vs baseline

222 righe stabili: 192 changed, 21 recovered (FX 6M/1Y prima falliti), 9 unchanged.
Transizioni di categoria principali: `heavy→light` 17, `medium→light` 8,
`heavy→medium` 8, `None→medium` 12 e `None→light` 9 (i FX recuperati),
`heavy→heavy` 26 (tecniche esplicite preservate). La riduzione singola maggiore è
`broker.concentration_context` 1Y full: da 2.101.479 a 13.590 caratteri
(-99,35%), history -11.280 righe, eventi -2.605.

### 10.4 Prompt minimo, mediano, massimo

| Categoria | Token-eq. stimati | Prompt |
|---|---:|---|
| Minimo | 640,75 | `fx.overview` 3M Full |
| Mediano | 4.137,50 | `portfolio.fifo` 3M Full |
| Massimo | 602.205,25 | `portfolio.technical_breadth` 1Y Full |

Il minimo è un overview FX puro; il mediano è un dataset FIFO focalizzato senza
tecnica; il massimo è l'Analysis tecnica esplicita, che per contratto **deve**
restare completa (Signal, history, breadth, eventi) e resta quindi Very Heavy.

---

## 11. Signal di rischio/volatilità usati e metriche escluse

Sono usati solo Signal **deterministici già esistenti**: EMA20/50/200, KAMA20,
RSI14 (+stato plugin-owned neutral/overbought/oversold), NATR14, ATR14, Bollinger,
PPO/ROC (FX), volatilità daily-return calcolata dalle osservazioni. **La volatilità
non è rietichettata come "risk"**: NATR/ATR restano volatilità con semantica
dichiarata.

Metriche di rischio **escluse perché non disponibili** (nessun calcolatore attivo
affidabile nel runtime component): drawdown/recovery, VaR, CVaR, stress. Non sono
state inventate né reintrodotte. Analysis che ne beneficerebbero in futuro:
`portfolio.rebalancing`, `asset.position_review`, `broker.review` — riportate come
mattoncino futuro (`Risk Assessment`), non bloccante.

---

## 12. Revisione qualitativa

### 12.1 Finding confermati

- **Portfolio Description** (-97,46%): descrive direzione, trend prevalente,
  momentum aggregato e criticità recenti via `technical_summary` (coverage + breadth
  latest + digest eventi), senza history per-Asset. Non è più un Technical Export.
- **Portfolio Rebalancing** (-96,28%): scheda uniforme per Asset (`asset_comparison`)
  con return 1M/3M, EMA/KAMA/RSI/NATR, breadth ed eventi strutturali; consente il
  confronto orizzontale senza la history completa di tutti i Signal.
- **Portfolio Technical Breadth** (+0,28%): invariato; Signal/history/breadth/eventi
  completi preservati; resta Heavy, coerente con l'obiettivo tecnico esplicito.
- **Broker Review** (-95,22%): holdings, performance, flussi, costi e FIFO restano
  primari; la tecnica è un confronto sintetico secondario (Medium).
- **Broker Concentration** (-98,51%): dominato dalla concentrazione; solo
  coverage + breadth aggregata via `technical_summary`; Light.
- **Asset Position Review** (-87,57%): più profondo del Rebalancing sul singolo Asset
  (short trend, ATR14, Bollinger, history limitata per detail) ma più mirato del
  Trend Analysis; distinzione chiara tra Position Review (finanziaria con trend/rischio
  di supporto), Trend Analysis (tecnica approfondita) e Market Technical Export
  (fotografia tecnica completa).
- **Asset Trend Analysis** (+1,62%): tecnica esplicita completa preservata.
- **PAC Planning** (+35,43%): aggiunge `asset_snapshot` (1M/3M, RSI, volatilità)
  subordinato a budget/target/orizzonte; resta Light.
- **Performance Attribution** (+2,39%): nessuna tecnica aggiunta; resta focalizzato
  su contributor/realized/unrealized/income/costi/imposte/flussi/riconciliazione.
- **FX partiale finale**: 3/3, coverage 25,4098%, 10/12 Signal PARTIAL, 2 omessi con
  motivazione; nessun fallimento — coerente con lo spirito «dati parziali con
  warning quando esistono dati utilizzabili».
- **Min/median/max**: proporzionati; il massimo resta un'Analysis tecnica esplicita.

### 12.2 Finding potenziali

- Le schede uniformi (`asset_comparison`) crescono con il numero di Asset eleggibili;
  con universi molto ampi potrebbero avvicinarsi a Medium: monitorare, non è un
  problema nel caso rappresentativo (max 4.904,50).
- La history parziale FX espone `is_backward_filled=true` sul latest rate quando la
  data richiesta cade in un giorno senza osservazione: corretto ma da spiegare bene
  nella guida utente.

### 12.3 Decisioni prodotto future

- Introdurre un futuro `Risk Assessment` deterministico (drawdown/VaR/CVaR/stress)
  quando esisterà un calcolatore affidabile.
- Valutare un componente `technical_evidence` per collegare eventi a evidenze.
- Definire eventuale floor/finestra eventi per i contesti ristretti.

---

## 13. Regressioni e tradeoff (intenzionali)

- **PAC Planning +35,43%**: crescita voluta per il piccolo contesto tecnico opzionale
  per Asset; resta Light e subordinato ai vincoli di piano.
- **FX tecnici espliciti** (`fx.trend_review` +25,60%, `fx.conversion_timing`
  +23,27%): crescita moderata dovuta al **recupero dell'output 6M/1Y** (prima
  falliva) e ai metadata di coverage; è informazione prima assente, non un
  peggioramento.
- **Full technical** (`portfolio.technical_breadth`, `asset.trend_analysis`): restano
  intenzionalmente pesanti perché il contenuto è realmente richiesto.
- **Nessuna modifica globale** a Compact/Standard/Full, alla matrice P/M/K, alla
  selezione/finestra eventi dei dataset tecnici completi o al catalogo `*.all_data`
  (solo esclusione delle nuove proiezioni derivate). Nessun token cap introdotto.

---

## 14. Test e validazione

Risultati registrati durante il lavoro (verdi):

| Suite / gate | Esito |
|---|---|
| Backend focused (component decomposition, projection allowlist, history/event policy, resource build count, catalog 25/16, all_data exclusion, Analysis mapping) | 316 test |
| Backend AI Export services | 1012 test |
| Schema (`ai_export_runtime`, version/failure codes) | 112 test |
| API (OpenAPI/handshake) | 15 test |
| Frontend AI Export (compat V2, IDs/label, F1 refs, no DB IDs, guida localizzata, UI path, period/detail, required/optional) | 160 test |
| Probe (metriche stabili, nuovi dataset keys, determinismo, secret scan, source read-only, reference audit) | 32 test |
| Regressione FX parziale isolata (file di test dedicato) | 29 test |
| `./dev.py front check` | 0 errori / 0 warning |
| `./dev.py i18n audit` | 100% / 0 chiavi mancanti |
| `./dev.py mkdocs build` + `check-links` | build OK + 18 link verificati |
| Ruff / Black / Prettier mirati | passati |
| `git diff` check | coerente |

Docs architetturali aggiornati (EN-only):
`mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md`,
`ai_export_composition.md`, `ai_export_sampling.md`.

La regressione FX mirata finale è inclusa; il probe FX parziale finale
`20260731T172828.344713Z` è 3/3 senza fallimenti.

---

## 15. Problemi lasciati intenzionalmente aperti

Ciascuno resta separato e fuori scope da questa attività:

- futuro **Risk Assessment** deterministico (drawdown/VaR/CVaR/stress);
- possibile componente **`technical_evidence`**;
- **floor/finestra eventi** per i contesti ristretti;
- eventuale revisione **P/M/K** globale;
- **classificazione Signal** (volatilità vs risk) più formale;
- **tokenizer model-specific** al posto di chars/4;
- **descrizioni provider** e settore (es. **BTP**) non correlate;
- semantica di **`all_data`** rispetto alle nuove proiezioni;
- **nessun cleanup, wiki lint/update, release o commit** eseguiti.

Le dimensioni sono usate solo come indicatore diagnostico: nessun hard cap; nessun
dato necessario è stato sacrificato per raggiungere una soglia.
