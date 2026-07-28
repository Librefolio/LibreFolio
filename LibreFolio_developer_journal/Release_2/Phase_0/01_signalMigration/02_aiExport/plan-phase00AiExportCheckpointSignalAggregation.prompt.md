# Checkpoint Phase 0 — AI Export e aggregazione Signal Plugin

**Stato**: ⏸️ PAUSA ESPLICITA — 28 luglio 2026
**Scopo**: congelare lavoro svolto, decisioni, problemi scoperti e ordine di ripresa.

← Piano precedente:
[AI Export dataset/analysis refinement](./plan-phase00AiExportRefinementImplementation.prompt.md)

← Requisiti di consenso:
[GPT-5.6 refinement](./gpt5.6_refinementPlan.md)

## 1. Decisione operativa: semplificare il flusso dati

Il service layer non deve ricevere una lista di date puntuali selezionate dal bucket.
Una richiesta puntuale perderebbe minimi, massimi, transizioni ed eventi intermedi.

Flusso corretto:

```text
range visibile + parametri signal
    → backend carica slice completo + warm-up
    → SignalService calcola la serie completa
    → UI riceve la serie visibile completa
    → frontend aggrega per daily/weekly/monthly usando la policy del plugin

range AI + detail level
    → backend carica slice completo + warm-up
    → SignalService calcola la serie completa
    → AI Export applica la stessa policy ai propri BucketPlan adattivi
```

Regole:

- mai calcolare il signal soltanto sui punti finali del bucket;
- mai chiedere al service soltanto le date rappresentative;
- warm-up interno, mai esportato;
- il chart continua a fare aggregazione daily/weekly/monthly nel frontend;
- AI Export applica l'aggregazione nel backend;
- entrambi consumano la stessa dichiarazione del plugin.

## 2. Bug Drawdown confermato

Il backend produce correttamente un punto Drawdown per ogni osservazione.

Il bug è frontend:

`frontend/src/lib/components/charts/timeSeriesAggregation.ts`

`downsampleRenderedSignal()` tratta Drawdown come una line generica e usa
`aggregateLineSeries()`, che conserva soltanto l'ultimo punto del bucket.

Esempio:

```text
[-0.5, -8.2, -6.0, -1.0] → weekly LAST → -1.0
```

Il trough `-8.2` scompare. Questo conferma che `SignalSeriesKind.LINE` non descrive
la semantica temporale necessaria.

Possibile secondo problema da verificare: il filtro sui `bucketedDates` del prezzo
principale può eliminare un bucket Signal se i calendari non hanno lo stesso ultimo
giorno osservato.

## 3. Decisione: aggregazione solo tramite enum

Non viene introdotto un hook custom nel plugin.

Ogni output dichiara un algoritmo enum. Quando emergerà un caso non coperto,
l'enum e la relativa implementazione generica verranno estesi nel frontend e nel
backend AI Export.

Contratto iniziale consigliato:

```python
class SignalAggregationAlgorithm(StrEnum):
    LAST = "last"
    FIRST_LAST = "first_last"
    MIN_LAST = "min_last"
    MAX_LAST = "max_last"
    MIN_MAX_LAST = "min_max_last"
    OHLC = "ohlc"
    BAND_ENVELOPE = "band_envelope"
    EVENTS_VERBATIM = "events_verbatim"
```

Semantica:

| Algoritmo | Output bucket |
|---|---|
| `LAST` | ultimo valore osservato |
| `FIRST_LAST` | inizio e fine |
| `MIN_LAST` | minimo reale + fine |
| `MAX_LAST` | massimo reale + fine |
| `MIN_MAX_LAST` | minimo, massimo e fine |
| `OHLC` | inizio, minimo, massimo e fine |
| `BAND_ENVELOPE` | policy coordinata per lower/middle/upper |
| `EVENTS_VERBATIM` | tutti gli eventi, nessuna media/troncamento |

Per gli algoritmi multi-point:

- conservare la data reale di ogni punto selezionato;
- deduplicare se first/min/max/last coincidono;
- ordinare cronologicamente;
- non spostare tutti i punti alla fine del bucket;
- il frontend mostra la geometria reale intrabucket;
- AI Export serializza valore e data degli estremi.

## 4. Mapping iniziale per famiglia

Da verificare output per output, poi congelare nei plugin:

| Famiglia | Policy iniziale |
|---|---|
| SMA, EMA, KAMA | `LAST` |
| RSI, MFI, CCI, Stoch RSI, ROC, PPO, MACD, Aroon, ADX | `MIN_MAX_LAST` |
| ATR, NATR e misure di volatilità | `MAX_LAST` |
| OBV e altre cumulative | `FIRST_LAST` |
| Drawdown | `MIN_LAST` |
| Bollinger, Donchian | `BAND_ENVELOPE` |
| annotazioni/transizioni | `EVENTS_VERBATIM` |
| prezzo/rate grezzi | `OHLC` |

`BAND_ENVELOPE` non deve combinare componenti in modo semanticamente impossibile.
Prima dell'implementazione va congelata una policy esplicita, inizialmente:

- lower: minimo;
- middle: ultimo;
- upper: massimo;
- opzionalmente first/last delle tre componenti se serve ricostruire il percorso;
- validare sempre `lower <= middle <= upper` per ogni rappresentazione emessa.

## 5. Decisione grafica Drawdown

Aggiungere un nuovo tipo visuale all'enum:

```python
class SignalSeriesKind(StrEnum):
    LINE = "line"
    AREA = "area"
    BAR = "bar"
    BAND = "band"
```

Drawdown:

- `kind = AREA`;
- linea superiore/baseline = `0`;
- area riempita fra `0` e il valore negativo;
- asse massimo `0`;
- fill opacity dichiarata nello style backend;
- weekly/monthly usa `MIN_LAST`, quindi mostra trough e chiusura/recupero.

Frontend renderer:

- `AREA` usa una ECharts line series;
- `areaStyle.origin = 0`;
- nessuna logica specifica per `RISK_DRAWDOWN`;
- comportamento guidato soltanto da `kind` + aggregation enum.

## 6. Contratto target Signal Plugin

Estendere `SignalOutputSpec`:

```python
class SignalOutputSpec(...):
    kind: SignalSeriesKind
    aggregation: SignalAggregationAlgorithm
```

Il catalogo backend espone entrambi.

Responsabilità:

- plugin: sceglie `kind` e `aggregation` per ogni output;
- SignalService: continua a produrre serie complete;
- frontend: applica l'enum a daily/weekly/monthly;
- AI Export: applica lo stesso enum ai bucket adattivi;
- nessuna duplicazione indicator-specific in TypeScript;
- nessun hook custom.

## 7. Stato implementazione AI Export alla pausa

### Completato

1. Freeze architettura: 18 dataset, 17 analisi, API/contract v1.
2. Signal/source:
   - descrizioni AI plugin;
   - validation hook;
   - capability volume provider/serie;
   - MFI/OBV fail-closed.
3. Temporal engine:
   - periodo inclusivo;
   - BucketPlan adattivo;
   - K 30/14/7;
   - aggregatori ed eventi;
   - 98 test focalizzati.
4. Runtime componenti:
   - Component/Dataset/Analysis registry;
   - composer e `all_data`;
   - envelope JSON-safe;
   - required/optional;
   - 118 test focalizzati.
5. Build context:
   - BuildScope;
   - cache raw request-scoped;
   - AsyncSession serializzata;
   - deadlock nested DB corretto.
6. Componenti dominio:
   - Portfolio/Broker financial;
   - Asset core;
   - FX core;
   - technical shared.
7. Correzioni emerse:
   - capability volume persa nel runner AI;
   - doppia conversione FX position exposure;
   - aggregate Asset parziali falsamente complete;
   - breadth ROC/PPO/Aroon sempre `zero`;
   - import-cycle Portfolio/Broker;
   - fallback FX `ENGINE_VALUATION`.

### Parzialmente completato / sospeso

1. Portfolio/Broker registry integration:
   - fragment 25 componenti reali;
   - import-cycle corretto;
   - ultimo gate noto: 51 test fragment e suite AI Export verde;
   - todo lasciato `in_progress` per la pausa.
2. Asset/FX registry integration:
   - fragment e test presenti nel worktree;
   - consolidamento resource prezzi/rate in lavorazione;
   - agente fermato per la pausa;
   - non considerare concluso finché non viene letto/revisionato il risultato.
3. Central component registry:
   - non ancora sostituiti tutti i placeholder con i 45 builder reali.

### Non iniziato

1. Nuovo contratto pubblico catalog/snapshot v1.
2. Analysis/API/prompt migration.
3. Frontend hard cutover ai due cataloghi.
4. Nuovo selector Export Data / Request Analysis.
5. Warning token `Copy Anyway`.
6. Developer Guide AI Export.
7. Review manuale quattro pagine.
8. Test frontend/build/E2E post-review.
9. Cleanup legacy e knowledge layer.

## 8. Nuovo ordine di ripresa

La nuova aggregazione Signal è prerequisito del completamento AI Export technical.

```text
S1 — congelare enum + mapping per ogni output plugin
S2 — aggiungere SignalSeriesKind.AREA
S3 — estendere SignalOutputSpec/catalog/OpenAPI
S4 — dispatcher frontend daily/weekly/monthly
S5 — Drawdown AREA + MIN_LAST
S6 — dispatcher backend AI Export sugli stessi enum
S7 — test signal aggregation UI/backend
S8 — riprendere Asset/FX registry integration
S9 — central real component registry
S10 — Analysis/API/prompt
S11 — frontend AI Export
S12 — docs/review/validation/cleanup
```

## 9. Acceptance aggregation Signal

- Drawdown weekly conserva trough e ultimo valore.
- Drawdown `AREA` riempie da `0` al valore negativo.
- SMA/EMA/KAMA weekly non vengono mediate.
- Oscillatori conservano range intrabucket e fine.
- OBV non viene mediato.
- Bollinger/Donchian non violano ordine delle bande.
- eventi restano tutti presenti e datati.
- Signal set identico a daily/weekly/monthly.
- nessuna logica per signal code nel frontend.
- catalogo backend è unica fonte di `kind` + `aggregation`.
- AI Export e chart usano la stessa dichiarazione.

## 10. File da leggere alla ripresa

Decisioni/piani:

- `gpt5.6_refinementPlan.md`
- `plan-phase00AiExportRefinementImplementation.prompt.md`
- questo checkpoint

Signal:

- `backend/app/services/signal_plugins/base.py`
- `backend/app/schemas/signals.py`
- `backend/app/services/signal_service.py`
- `backend/app/services/signal_plugins/drawdown.py`
- `frontend/src/lib/components/charts/timeSeriesAggregation.ts`
- `frontend/src/lib/charts/signals/backendRenderer.ts`

AI Export:

- `backend/app/services/ai_export/temporal/`
- `backend/app/services/ai_export/components/technical_shared.py`
- `backend/app/services/ai_export/components/technical_payloads.py`
- `backend/app/services/ai_export/components/asset_fx_registry.py`
- `backend/app/services/ai_export/components/portfolio_broker_registry.py`

Test:

- `frontend/src/lib/components/charts/__tests__/timeSeriesAggregation.test.ts`
- `backend/test_scripts/test_services/test_ai_export_components_technical.py`
- `backend/test_scripts/test_services/test_signal_plugin_matrix.py`

## 11. Regola pausa

Non riprendere implementazione, test frontend, wiki ingest/lint o central registry
finché l'utente non chiede esplicitamente di continuare.
