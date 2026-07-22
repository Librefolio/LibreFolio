# Piano Applicativo: Phase 0 — Migrazione Segnali Backend

**Stato**: 📋 DRAFT — in attesa di validazione; nessuna implementazione production avviata.

**Data**: 22 Luglio 2026

← Piano architetturale:
[plan-phase00SignalsBackendMigration.prompt.md](./plan-phase00SignalsBackendMigration.prompt.md)

## 1. Obiettivo applicativo

Trasformare l'architettura approvata in una migrazione incrementale e verificabile:

```text
Backend framework
    ↓
Backend test framework
    ↓
SignalService validato con plugin fixture
    ↓
Plugin reali + test
    ↓
API bulk Asset/FX complete
    ↓
Frontend condiviso
    ↓
Asset Detail
    ↓
Asset List
    ↓
FX Detail
    ↓
FX List
    ↓
AI Export
    ↓
Cutover e cleanup
```

Nessuna fase frontend inizia prima del gate backend completo. I calcoli TypeScript
restano disponibili fino alla parità funzionale e visuale delle viste migrate.

## 2. Baseline del codice corrente

### 2.1 Backend

| Area | Stato reale | File/seam |
|---|---|---|
| Registry | Decorator + filesystem auto-discovery già usati da FX, Asset e BRIM | `backend/app/services/provider_registry.py` |
| Startup | Lifespan crea DB/settings, prewarma provider e avvia scheduler; nessun signal dependency check | `backend/app/main.py` |
| Asset query | `get_prices_bulk()` fa una query globale, partition per asset, seed query, backward fill, eventi condizionali e conversione FX | `backend/app/services/asset_source.py` |
| Asset API | `POST /api/v1/assets/prices/query` restituisce `FAPriceQueryResponse` | `backend/app/api/v1/assets.py` |
| FX conversion | `convert_bulk()` distingue esplicitamente identity e non-identity, usa backward fill e restituisce `None` su failure parziale | `backend/app/services/fx.py` |
| FX API | `/currencies/convert` espande il range in giorni e restituisce un risultato daily | `backend/app/api/v1/fx.py` |
| Schemi | Price/event/FX hanno già `DateRangeModel`, `BackwardFillInfo`, bulk response e Decimal validation | `backend/app/schemas/` |
| Dipendenze | Pipenv + lock; Docker usa `python:3.13-slim`; CI installa dal lock | `Pipfile`, `Pipfile.lock`, `Dockerfile`, `.github/workflows/` |

### 2.2 Frontend

Non esiste una route o un componente chiamato **Global Detail**.

I consumer reali dei segnali sono:

1. Asset List, card grid e settings globali/per-card:
   `frontend/src/routes/(app)/assets/+page.svelte`.
2. Asset Detail:
   `frontend/src/routes/(app)/assets/[id]/+page.svelte`.
3. FX List, card grid e settings globali/per-card:
   `frontend/src/routes/(app)/fx/+page.svelte`.
4. FX Detail:
   `frontend/src/routes/(app)/fx/[pair]/+page.svelte`.
5. `ChartSettingsModal` preview globale/per-target.
6. AI Export tecnico.

Componenti già condivisi:

- `ChartSignalsSection.svelte`;
- `ChartSettingsModal.svelte`;
- `ChartSignal.ts` e `registry.ts`;
- `chartSettingsStore.svelte.ts`;
- `PriceChartFull.svelte` / `LineChart.svelte`;
- `signalLabel.ts`;
- `loadComparisonData.ts`.

Duplicazioni principali:

- ogni page costruisce e risolve `signalFromConfig()` autonomamente;
- Asset List e FX List calcolano i segnali nelle card;
- Asset Detail e FX Detail mantengono wiring proprio;
- `ChartSignalsSection` usa registry e i18n map hardcoded;
- `ChartSettingsModal` calcola preview tecniche TypeScript su dati sintetici o locali.

### 2.3 Scoperte che cambiano il piano

1. **Global Detail non esiste**: viene sostituita dalle superfici Asset List e FX List,
   che applicano settings globali/per-card.
2. **Le list card sono consumer production**: non basta migrare le detail page.
3. **Preview globale senza dominio**: non può calcolare segnali backend senza creare
   l'endpoint raw esplicitamente rifiutato.
4. **Asset List usa un worker**: `priceProcessing.worker.ts` valida e trasforma la
   response; deve preservare anche i risultati segnali.
5. **Price cache ≠ signal cache**: anche con prezzi già nel `TimeSeriesStore`, i segnali
   devono essere richiesti alla POST perché la cache risultati è fuori scope.
6. **`include_price` esiste nello schema Asset** ma il servizio corrente restituisce
   comunque i prezzi; può essere reso effettivo per richieste signal-only senza
   duplicare il payload.
7. **Renderer incompleto**: line/bar/band esistono; reference levels e metadata
   canonici richiedono un'estensione generica.
8. **RSI corrente usa zone colorate**: il contratto A2 deve includere `value_regions`
   generiche, risolte per instance dai params, prima del freeze backend.

## 3. Decisioni confermate

- `SignalPlugin` è l'unica astrazione comune.
- Ogni plugin possiede backend, params, warm-up, calcolo, normalizzazione e test.
- Nessun adapter centrale delle librerie.
- Dipendenze solo tramite Pipenv/lock/Docker/CI.
- Stack composito `pandas-ta-classic + TA-Lib`.
- 16 plugin passano `talib=True`; Donchian usa il path nativo.
- Cataloghi GET esclusivamente statici.
- Disponibilità dinamica soltanto nelle POST bulk.
- Eventi caricati solo quando realmente richiesti.
- DataFrame/columnar condiviso solo come ottimizzazione interna.
- Nessuna cache risultati in Phase 0.
- Nessun DB schema change.
- Frontend schema-driven e backend autorità finale.

## 4. Correzioni applicate al piano architetturale

- Rimossi cataloghi GET contestuali.
- Spostata availability dinamica nelle POST Asset/FX.
- Step 0 produce policy warm-up **candidate**, non policy plugin definitive.
- Sostituito il termine ambiguo “adapter” con mapping/integrazione di dominio.
- Reso esplicito il mapping FX identity/non-identity.
- Reso condizionale il caricamento eventi.
- Resa opzionale la preparazione DataFrame condivisa.
- Corretto il dependency graph: SignalService blocca integrazione Asset/FX, non adapter
  centrali.

## 5. Convenzioni per l'esecuzione

Per ogni task:

1. segnare `in_progress` prima di iniziare;
2. modificare solo i file assegnati;
3. eseguire i test target;
4. aggiornare immediatamente questo piano con:
   - ✅ e data;
   - `> **Note implementazione**: ...`;
   - `> **⚠️ Fuori pista**: ...`;
5. non anticipare task oltre il gate corrente.

## Macrofase A — Fondazione backend

### A1 — Spike tecnico stack composito

**Obiettivo**

Validare ambiente, backend computazionali e policy warm-up candidate prima del codice
production.

**File**

- `Pipfile`;
- `Pipfile.lock`;
- harness non-production versionato in `scripts/spikes/signals/`;
- eventuali launcher lunghi temporanei `/tmp/libreFolio_signal_spike_*.sh`;
- nuovo artefatto
  `LibreFolio_developer_journal/Release_2/Phase_0/spike-phase00SignalBackends.md`;
- fixture deterministiche versionate in `backend/test_scripts/fixtures/signals/`.

**Comportamento atteso**

- installare `pandas-ta-classic` e `TA-Lib` tramite Pipenv;
- validare Python 3.13 e Docker;
- verificare wheel amd64/arm64 concretamente disponibili;
- esercitare 17 segnali;
- verificare `talib=True` per 16 e Donchian native;
- rendere osservabile il silent fallback;
- produrre minimum lookback, stabilization e tolleranza candidate;
- misurare batch e concorrenza senza assumere GIL/thread safety;
- avviare l'app completa su macOS arm64 dev e sui runtime Linux concretamente
  supportati, perché il fail-fast renderà lo stack necessario a ogni boot backend.

**Test/misure**

- flat, trend, volatile, gap, NaN, short series, scale diverse;
- reference TA-Lib long-history vs warm-up crescente;
- native pandas-ta vs TA-Lib;
- installazione da lock;
- Docker build;
- missing TA-Lib fail-fast probe;
- riproducibilità da seed e dataset registrati nell'artefatto.

**Dipendenze**: nessuna.

**Accettazione**

- entrambe le dipendenze lockate;
- 17 funzioni disponibili;
- path 16+1 dimostrati;
- policy candidate e limiti documentati;
- strategia concorrente basata su misure;
- nessuna soglia non misurata elevata a requisito;
- app completa avviabile in dev/CI/Docker prima del merge del fail-fast globale.

**Rischi**

- wheel non disponibile su una piattaforma reale;
- fallback nativo non rilevato;
- warm-up diverso per dataset/parametri;
- API della release diversa dalla ricerca;
- stack nativo mancante che blocca tutto il backend, non soltanto i segnali.

---

### A2 — Schemi backend neutrali

**Obiettivo**

Definire contratti Pydantic stabili prima di registry/service/plugin.

**File**

- nuovo `backend/app/schemas/signals.py`;
- `backend/app/schemas/__init__.py`;
- nuovo `backend/test_scripts/test_schemas/test_signal_schemas.py`.

**Comportamento atteso**

- `SignalPricePoint`, `SignalEventPoint`;
- request instance con ID/code/params;
- catalog definition;
- line/bar/band + flat composite;
- axis/unit/reference levels;
- `value_regions` generiche, semanticamente nominate e senza colori;
- default/capability statici nel catalogo;
- reference levels e regions effettivi, risolti dai params, nel result per instance;
- availability/result/error/warm-up metadata;
- JSON-safe `float | None`, mai NaN/infinity.

**Test**

- `extra="forbid"`;
- discriminated union;
- params/catalog serialization;
- invalid date/cardinality/status;
- structured errors;
- backward-compatible default-empty signal fields quando integrati.

**Dipendenze**: A1 per i campi warm-up candidate, non per la struttura generale.

**Accettazione**

- OpenAPI generabile;
- nessun tipo pandas/TA-Lib;
- modelli sufficienti a tutti i 17 output;
- availability per instance rappresentabile.

**Rischi**

- output spec troppo specifico per un indicatore.

---

### A3 — `SignalPlugin`, registry e fail-fast

**Obiettivo**

Creare il contratto autonomo e l'auto-discovery senza logica di libreria centrale.

**File**

- nuovo `backend/app/services/signal_plugins/base.py`;
- nuovo `backend/app/services/signal_plugins/__init__.py`;
- `backend/app/services/provider_registry.py`;
- nuovo helper minimale `backend/app/services/signal_runtime.py`;
- `backend/app/main.py`;
- nuovi test registry/runtime.

**Comportamento atteso**

- `SignalPlugin` library-agnostic;
- `SignalPluginRegistry`;
- `@register_plugin`;
- filesystem discovery;
- duplicate/import error espliciti;
- startup check: package importabili + `Imports["talib"] is True`;
- nessun mapping signal → funzione;
- nessun dependency manifest.

A3 può essere integrato solo insieme o dopo il lock validato da A1: non è ammesso
atterrare un fail-fast globale che renda inavviabile il backend agli altri contributor.

**Test**

- registry isolato;
- duplicate code;
- broken module;
- startup missing package;
- startup `Imports["talib"] == False`;
- provider registry regression.

**Dipendenze**: A2.

**Accettazione**

- provider registry invariati;
- fixture plugin registrabile;
- startup fallisce chiaramente con stack incompleto;
- startup normale verificato su tutti gli ambienti supportati;
- base/registry non importano funzioni indicatori.

**Rischi**

- circular import con `provider_registry.py`;
- startup test contaminato dal package realmente installato.

---

### A4 — Infrastruttura test con plugin fixture

**Obiettivo**

Validare il framework prima dei 17 plugin reali.

**File**

- nuovo `backend/test_scripts/fixtures/signal_plugins/`;
- nuovo `backend/test_scripts/test_services/test_signal_registry.py`;
- nuovo `backend/test_scripts/test_services/test_signal_contracts.py`;
- fixture serie in `backend/test_scripts/fixtures/signals/`.

**Comportamento atteso**

- plugin fixture line;
- plugin fixture band/composite;
- plugin con warm-up;
- plugin che fallisce;
- plugin con input/events richiesti;
- test-only discovery path, senza esporre fixture nel catalogo production.

**Test**

- registrazione/discovery;
- params;
- requirements;
- output canonico;
- duplicate/error;
- event requirement;
- date alignment.

**Dipendenze**: A2-A3.

**Accettazione**

- test fixture non visibili in production;
- framework testabile senza DB/HTTP;
- pattern pronto per `SignalService`.

**Rischi**

- test registry accoppiato al filesystem production;
- fixture troppo semplici per trovare errori di slicing.

---

### A5 — `SignalService` con fixture plugin

**Obiettivo**

Completare orchestration e availability prima dei plugin reali.

**File**

- nuovo `backend/app/services/signal_service.py`;
- nuovo `backend/test_scripts/test_services/test_signal_service.py`.

**Comportamento atteso**

- resolve/validate plugin e params;
- dedup code+params;
- warm-up massimo;
- range esteso richiesto una volta;
- coverage campi/storia;
- eventi solo se richiesti;
- DataFrame/columnar opzionale e interno;
- esecuzione plugin;
- error isolation;
- sanitizzazione;
- validation output/date/cardinality;
- slicing;
- result per instance ID.

**Test**

- bulk multi-instance;
- dedup;
- max warm-up;
- full/partial/unavailable/failed;
- missing fields;
- incomplete history;
- event load flag;
- NaN/infinity;
- invalid plugin output;
- slicing/date alignment;
- equivalent Asset/FX neutral points.

**Dipendenze**: A2-A4.

**Accettazione**

- tutti i test service verdi;
- nessun DB/HTTP necessario;
- nessuna scelta libreria nel service;
- un plugin fallito non invalida gli altri.

**Rischi**

- DataFrame condiviso diventa accidentalmente contratto;
- dedup perde instance ID/stile;
- warm-up calcolato su calendario invece che sulla serie effettiva.

### Gate A — Framework backend

Non iniziare B1 finché:

- A1-A5 sono ✅;
- schema, registry, fixture e `SignalService` sono stabili;
- test schema/services sono verdi;
- fail-fast stack composito è dimostrato;
- availability e slicing sono provati senza plugin production.

## Macrofase B — Plugin reali

### B1 — Quattro indicatori esistenti

**Obiettivo**

Validare completamente il pattern su EMA, RSI, MACD, Bollinger.

**File**

- `backend/app/services/signal_plugins/ema.py`;
- `rsi.py`;
- `macd.py`;
- `bollinger.py`;
- nuovo `backend/test_scripts/test_services/test_signal_plugins_core.py`.

**Comportamento atteso**

Ogni plugin possiede params, input, output, candidate warm-up verificata,
`talib=True`, normalizzazione, errori e version.

**Test**

Matrice completa plugin + spy `talib=True` + regression fixture + confronto
long-history.

**Dipendenze**: Gate A.

**Accettazione**

- quattro plugin production completi;
- MACD 3 serie flat;
- Bollinger band;
- warm-up candidate confermata o corretta/documentata;
- nessun helper centrale conosce le funzioni.

**Rischi**

- seed diverso dal TypeScript corrente;
- value regions prodotte dal plugin non coerenti con thresholds parametrizzati.

### Gate B1 — Pattern plugin

B2-B4 possono partire in parallelo solo dopo B1 validato.

---

### B2 — Close-only aggiuntivi

**Obiettivo**

Implementare SMA, ROC, StochRSI, KAMA, PPO.

**File**

- `sma.py`, `roc.py`, `stoch_rsi.py`, `kama.py`, `ppo.py`;
- `test_signal_plugins_close_only.py`.

**Comportamento atteso**

- Asset + FX;
- `talib=True`;
- StochRSI/PPO composite;
- output/reference levels generici.

**Test**

Matrice completa + backend path + regression.

**Dipendenze**: Gate B1.

**Accettazione**

- nove plugin close-only totali;
- nessun codice frontend specifico richiesto.

**Rischi**

- nomi/ordine colonne pandas-ta variabili con params.

---

### B3 — OHLC

**Obiettivo**

Implementare ATR, ADX, NATR, Aroon, Donchian, CCI.

**File**

- `atr.py`, `adx.py`, `natr.py`, `aroon.py`, `donchian.py`, `cci.py`;
- `test_signal_plugins_ohlc.py`.

**Comportamento atteso**

- input requirements rigorosi;
- 5 plugin `talib=True`;
- Donchian native;
- ADX/Aroon composite;
- Donchian band;
- nessun OHLC sintetico.

**Test**

Matrice completa + Donchian path + missing/partial fields.

**Dipendenze**: Gate B1.

**Accettazione**

- sei plugin OHLC completi;
- dynamic unavailable spiegabile.

**Rischi**

- copertura OHLC discontinua;
- assi diversi dentro Aroon composite.

---

### B4 — Volume

**Obiettivo**

Implementare OBV e MFI.

**File**

- `obv.py`, `mfi.py`;
- `test_signal_plugins_volume.py`.

**Comportamento atteso**

- no volume sintetico;
- coverage dinamica;
- `talib=True`.

**Test**

Matrice completa + zero/missing/partial volume.

**Dipendenze**: Gate B1.

**Accettazione**

- due plugin volume completi;
- unavailable distinto da failed.

**Rischi**

- provider con volume parziale o zero legittimo.

---

### B5 — Matrice regressiva completa

**Obiettivo**

Provare uniformemente tutti i 17 plugin.

**File**

- nuovo `backend/test_scripts/test_services/test_signal_plugin_matrix.py`;
- fixture versionate.

**Comportamento atteso**

- iterazione registry-driven;
- test contract comuni;
- backend path 16+1;
- warm-up policy per plugin.

**Test**: matrice completa richiesta dal piano architetturale.

**Dipendenze**: B2-B4.

**Accettazione**

- 17/17 passano;
- catalog definition completa;
- output canonici stabili.

**Rischi**

- test parametrico troppo generico nasconde bug specifici; mantenere anche test dedicati.

### Gate B — Catalogo plugin

Non iniziare il frontend. Richiede:

- B1-B5 ✅;
- 17 plugin e test verdi;
- catalog metadata completi;
- contratti canonici congelati per Phase 0;
- warm-up verificato nei plugin.

## Macrofase C — Integrazione backend Asset e FX

### C1 — Cataloghi GET statici

**Obiettivo**

Esporre definizioni statiche senza DB/history lookup.

**File**

- `backend/app/api/v1/assets.py`;
- `backend/app/api/v1/fx.py`;
- `backend/app/schemas/signals.py`;
- test API catalogo.

**Comportamento atteso**

- Asset: 17 definizioni;
- FX: 9 close-only;
- nessun query param contestuale;
- nessuna session/history load;
- params JSON Schema, input, output, axes, units, levels, docs, i18n.
- capability statiche per reference levels e value regions.

**Test**

- shape/order/code uniqueness;
- Asset/FX filtering;
- nessun accesso DB;
- auth/error behavior.

**Dipendenze**: Gate B.

**Accettazione**

- cataloghi statici e deterministici;
- nessuna availability dinamica.

**Rischi**

- confondere catalogo signal con provider catalog esistente.

---

### C2 — POST Asset bulk

**Obiettivo**

Integrare segnali nella pipeline prezzi senza rompere cache/store/client esistenti.

**File**

- `backend/app/schemas/prices.py`;
- `backend/app/services/asset_source.py`;
- `backend/app/api/v1/assets.py`;
- `test_assets_prices.py`;
- `test_asset_source.py`;
- nuovi test signal API Asset.

**Comportamento atteso**

- `signals` opzionali per item;
- max warm-up per item e global min/max load;
- una query bulk range esteso;
- seed/backward fill preservati;
- eventi caricati solo se `include_events`, plugin o consumer li richiede;
- target currency prima del compute;
- availability dinamica per instance;
- compute/slicing;
- `include_price=false` omette prezzi dalla response ma consente il loro uso interno;
- no-signal behavior invariato.

**Test**

- no signals;
- multi-asset/multi-signal;
- price cached/signal-only semantics;
- target currency;
- missing fields/history;
- events not loaded;
- partial plugin failure;
- response payload cap/size.

**Dipendenze**: Gate B, A5.

**Accettazione**

- vecchi client verdi;
- signal result per instance;
- un solo load esteso;
- errori segnale non compromettono prezzi.

**Rischi**

- `get_prices_bulk()` già grande;
- global range molto ampio per un solo plugin;
- worker/frontend dipendono dalla response completa.

---

### C3 — POST FX bulk

**Obiettivo**

Integrare i nove close-only mantenendo il contratto daily.

**File**

- `backend/app/schemas/fx.py`;
- `backend/app/services/fx.py`;
- `backend/app/api/v1/fx.py`;
- `test_fx_conversion.py`;
- `test_fx_api.py`;
- nuovi test signal API FX.

**Comportamento atteso**

- signal requests opzionali per conversion request;
- amount 1 sul range esteso;
- identity esplicita → close 1;
- non-identity → effective rate;
- missing non-identity rate → unavailable/failed;
- grouped signal results per original request;
- daily conversion results invariati;
- availability dinamica nelle POST.

**Test**

- identity;
- direct/inverse;
- backward fill;
- missing rate;
- multi-pair;
- 9 close-only;
- rejection dei plugin OHLC/volume;
- no duplication per giorno;
- no-signal regression.

**Dipendenze**: Gate B, A5.

**Accettazione**

- parity con Asset su serie close equivalente;
- response daily invariata;
- grouped results stabili.

**Rischi**

- confondere `rate=None` identity con missing rate;
- range expansion costosa.

---

### C4 — Compatibilità API e OpenAPI

**Obiettivo**

Congelare i contratti prima del frontend.

**File**

- test schema/API;
- `frontend/src/lib/api/openapi.json` solo tramite `./dev.py api sync` nella fase D.

**Comportamento atteso**

- optional fields con default;
- OpenAPI discriminated unions corrette;
- error model serializzabile;
- no DB migration.

**Test**

- `./dev.py test schemas all`;
- `./dev.py test services all`;
- `./dev.py test api all`;
- API schema generation.

**Dipendenze**: C1-C3.

**Accettazione**

- backend/API verdi;
- schema pronto per codegen;
- no regressioni no-signal.

**Rischi**

- Zodios genera union difficili da consumare; risolvere prima del Gate C.

### Gate C — Backend completo

Il frontend può iniziare solo quando:

- Gate A e B superati;
- C1-C4 ✅;
- 17 Asset / 9 FX esposti;
- POST bulk calcolano availability e serie;
- backward compatibility verde;
- OpenAPI stabile.

## Macrofase D — Fondazione frontend condivisa

### D1 — Client generato e tipi runtime

**Obiettivo**

Importare i contratti backend senza logica di vista.

**File**

- `frontend/src/lib/api/openapi.json`;
- `frontend/src/lib/api/generated.ts`;
- nuovo `frontend/src/lib/charts/signals/backendTypes.ts`;
- `frontend/src/lib/charts/signals/ChartSignal.ts`.

**Comportamento atteso**

- `./dev.py api sync`;
- alias typed per catalog/request/result;
- `SignalConfig` locale invariato;
- separazione `SignalDefinition` / `SignalConfig` / `SignalResult`.

**Test**

- frontend type-check;
- compile fixture dei 4 output shapes.

**Dipendenze**: Gate C.

**Accettazione**

- nessun `any` necessario nei nuovi contratti;
- generated client compilabile.

**Rischi**

- union OpenAPI troppo complessa.

---

### D2 — Catalog store e normalizzazione definizioni

**Obiettivo**

Creare una sola fonte condivisa per cataloghi Asset/FX e definizioni locali.

**File**

- nuovo `frontend/src/lib/stores/signalCatalogStore.svelte.ts`;
- nuovo `frontend/src/lib/charts/signals/catalogMapper.ts`;
- `frontend/src/lib/charts/signals/registry.ts`;
- test catalog mapper/store.

**Comportamento atteso**

- caricare cataloghi statici;
- normalizzare remote + local benchmark/comparison definitions;
- mantenere domain compatibility;
- errori catalogo espliciti;
- nessuna availability dinamica preventiva.

**Test**

- Asset 17 / FX 9;
- merge local/remote;
- duplicate code;
- fetch error/retry;
- i18n/docs metadata.

**Dipendenze**: D1.

**Accettazione**

- una sola implementazione store;
- pagine non parsano cataloghi.

**Rischi**

- collisione code tra local e backend.

---

### D3 — JSON Schema mapper e configuratore unico

**Obiettivo**

Refactor dell'esistente `ChartSignalsSection`, non creazione di configuratori per
singolo segnale.

**File**

- nuovo `frontend/src/lib/charts/signals/schemaMapper.ts`;
- nuovo `frontend/src/lib/components/charts/SignalParamControl.svelte`;
- `frontend/src/lib/components/charts/ChartSignalsSection.svelte`;
- `frontend/src/lib/components/charts/ChartSettingsModal.svelte`;
- test mapper.

**Comportamento atteso**

- number/integer;
- boolean;
- enum/select;
- required/default/min/max/step;
- suffix/tooltip/i18n/order;
- local dynamic options per comparison signal;
- unsupported schema → errore esplicito;
- rimozione della i18n map hardcoded per i backend signal.

**Test**

- schema fixtures;
- config create/update/reorder;
- unsupported field;
- local comparison/benchmark regression.

**Dipendenze**: D2.

**Accettazione**

- nessun branch EMA/RSI/MACD specifico;
- UI attuale preservata.

**Rischi**

- mescolare JSON Schema backend e `dynamicOptionsKey` locale.

---

### D4 — Renderer canonico e reference primitives

**Obiettivo**

Mappare `SignalResult` in ECharts senza conoscenza dei 17 code.

**File**

- nuovo `frontend/src/lib/charts/signals/backendRenderer.ts`;
- `frontend/src/lib/components/charts/LineChart.svelte`;
- `frontend/src/lib/components/charts/PriceChartFull.svelte`;
- `frontend/src/lib/components/charts/lineChartHelpers.ts`;
- `frontend/src/lib/charts/signalLabel.ts`;
- test renderer/helpers.

**Comportamento atteso**

- line/bar/band;
- composite flat;
- axis role/bounds/unit;
- reference levels;
- value regions;
- view transform;
- instance ID;
- warning/unavailable;
- stile locale.

Il contratto A2 è già congelato con reference levels e `value_regions` risolti per
instance. Il renderer applica colori/stili locali alle regioni senza logica hardcoded
per signal code.

**Test**

- MACD, Bollinger, PPO, ADX, Aroon, Donchian;
- reference levels;
- value regions;
- percent transform;
- missing points;
- multi-axis.

**Dipendenze**: D1-D3.

**Accettazione**

- 17 output renderizzabili senza switch per code;
- local signals ancora renderizzabili.

**Rischi**

- ECharts band/reference-level implementation;
- assi composite incompatibili.

---

### D5 — Request builder e result state

**Obiettivo**

Condividere costruzione POST e mapping risultati, senza introdurre cache.

**File**

- nuovo `frontend/src/lib/charts/signals/requestBuilder.ts`;
- nuovo `frontend/src/lib/charts/signals/resultMapper.ts`;
- eventuale state helper non persistente;
- test request/result.

**Comportamento atteso**

- separare backend vs local config;
- dedup request conservando instance ID;
- risultati page-local;
- unavailable config preservata;
- nessuna result cache globale.

**Test**

- multi-instance stessa config;
- local-only;
- mixed local/backend;
- failed/partial/unavailable;
- stale response guard.

**Dipendenze**: D1-D4.

**Accettazione**

- pagine assemblano richieste tramite un solo helper;
- nessuna duplicazione mapping.

**Rischi**

- race su range/params change.

---

### D6 — Policy preview settings

**Obiettivo**

Risolvere il preview senza endpoint raw e senza calcoli TypeScript tecnici.

**File**

- `ChartSettingsModal.svelte`;
- `ChartSignalsSection.svelte`;
- test/E2E `fx-chart-settings.spec.ts` e Asset settings.

**Policy proposta**

- global mode: preview di aesthetics e segnali frontend-local; i tecnici backend
  mostrano “preview disponibile su un asset/coppia reale”;
- per-target mode: usare gli ultimi risultati backend forniti dalla page;
- params non ancora applicati: mostrare stato “applica per aggiornare” nella prima
  migrazione;
- nessuna POST raw/synthetic;
- eventuale preview debounced via POST domain-specific è follow-up UX, non Phase 0 core.

**Test**

- global modal;
- pair/asset modal;
- local benchmark preview;
- backend technical unavailable preview message;
- no TS compute call.

**Dipendenze**: D3-D5.

**Accettazione**

- nessun endpoint nuovo;
- nessuna regressione crash/modal;
- comportamento esplicito e traducibile.

**Rischi**

- regressione UX rispetto al live preview corrente.

### Gate D — Frontend condiviso

Non migrare pagine finché:

- D1-D6 ✅;
- catalog, mapper, configuratore, renderer e request builder testati;
- preview policy validata;
- frontend check/build puliti;
- local benchmark/comparison/Measure invariati.

## Macrofase E — Migrazione viste reali

### E1 — Asset Detail

**Obiettivo**

Prima vista end-to-end, limitata inizialmente ai quattro segnali esistenti.

**File**

- `frontend/src/routes/(app)/assets/[id]/+page.svelte`;
- eventuali helper price store;
- `frontend/e2e/assets/asset-detail.spec.ts`.

**Comportamento atteso**

- catalog Asset;
- POST price query con signal configs;
- events già richiesti dalla page restano consumer-driven;
- risultati per instance;
- generic renderer;
- refetch range/params;
- TS engine conservato ma non usato nel nuovo path.

**Test**

- EMA/RSI/MACD/Bollinger;
- target currency;
- partial/unavailable;
- config persistence;
- sync/refetch.

**Dipendenze**: Gate D.

**Accettazione**

- parità funzionale/visuale dei 4;
- altri 13 abilitabili dopo la parità;
- manual chart review completata.

**Rischi**

- page già grande;
- include_events e signal events confusi.

---

### E2 — Asset List e card

**Obiettivo**

Migrare settings globali/per-card e card charts; sostituisce l'inesistente “Global
Detail”.

**File**

- `frontend/src/routes/(app)/assets/+page.svelte`;
- `frontend/src/lib/workers/priceProcessing.worker.ts`;
- `frontend/src/lib/workers/priceProcessingPool.ts`;
- Asset card;
- `frontend/e2e/assets/asset-list.spec.ts`.

**Comportamento atteso**

- una bulk query per asset che richiedono prezzi e/o segnali;
- se prezzi cached ma segnali richiesti: `include_price=false`;
- worker preserva/valida signal results;
- settings globali/per-card invariati;
- 17 segnali secondo availability;
- local comparison/benchmark restano locali.

**Test**

- cache prezzi piena + segnali;
- cache con gap;
- global settings;
- per-card settings;
- multi-asset partial;
- worker invalid payload.

**Dipendenze**: E1.

**Accettazione**

- card non calcolano tecnici TS;
- una POST bulk, non una per segnale/card;
- UI resta responsiva.

**Rischi**

- payload/compute elevato su molti asset;
- worker drop dei signal results.

---

### E3 — FX Detail

**Obiettivo**

Migrare la vera detail FX distinta dalla list.

**File**

- `frontend/src/routes/(app)/fx/[pair]/+page.svelte`;
- `frontend/src/lib/stores/fxStoreRegistry.ts` o helper dedicato;
- `frontend/e2e/fx/fx-detail.spec.ts`.

**Comportamento atteso**

- catalogo FX 9;
- POST convert con signals;
- orientation/inversion coerente;
- grouped results;
- comparison signal locale invariato;
- no OHLC/volume options.

**Test**

- direct/inverted pair;
- identity;
- backward fill;
- range/params;
- partial/unavailable.

**Dipendenze**: E1 e Gate D.

**Accettazione**

- 9 close-only backend;
- assi/composite corretti;
- no TS technical path.

**Rischi**

- store API attuale restituisce solo points;
- orientation mismatch.

---

### E4 — FX List e card

**Obiettivo**

Migrare card, settings globali/per-pair e bulk multi-pair.

**File**

- `frontend/src/routes/(app)/fx/+page.svelte`;
- `frontend/src/lib/stores/fxStoreRegistry.ts`;
- FX card;
- `frontend/e2e/fx/fx-list.spec.ts`;
- `frontend/e2e/fx/fx-chart-settings.spec.ts`.

**Comportamento atteso**

- una POST bulk per pair che richiedono dati/segnali;
- price store e signal results separati;
- global/per-pair settings;
- 9 close-only;
- modal preview policy.

**Test**

- multi-pair;
- cached rates + signals;
- inversion;
- settings globali/per-card;
- partial pair failure.

**Dipendenze**: E3.

**Accettazione**

- card non calcolano tecnici TS;
- nessuna duplicazione configuratore/renderer.

**Rischi**

- response grouping per original request;
- molti range daily espansi.

### Gate E — Parità viste

Non eliminare il TypeScript finché:

- E1-E4 ✅;
- quattro segnali esistenti hanno parità su detail e list;
- 17 Asset / 9 FX sono disponibili secondo capability;
- frontend unit/E2E target verdi;
- build/check puliti;
- verifica manuale completata;
- rollback per-view ancora possibile.

## Macrofase F — Cutover, AI Export e cleanup

### F1 — AI Export

**Obiettivo**

Eliminare il secondo calcolo tecnico frontend.

**File**

- `frontend/src/lib/features/ai-export/technical/technicalExportBuilder.ts`;
- `technicalEvents.ts`;
- Asset/FX export builders;
- test AI Export.

**Comportamento atteso**

- EMA20/50/200, RSI14, MACD backend;
- observed-only;
- annotations backend;
- sampling/payload invariati.

**Test**

- snapshot/fixture payload;
- unavailable history;
- event limits;
- Asset/FX.

**Dipendenze**: Gate E.

**Accettazione**

- nessun import di classi tecniche TS;
- payload compatibile.

**Rischi**

- differenze numerical/warm-up cambiano eventi.

---

### F2 — Rimozione engine tecnico TypeScript

**Obiettivo**

Completare il cutover senza rimuovere segnali locali.

**File**

- eliminare o ridurre:
  - `EmaSignal.ts`;
  - `RsiSignal.ts`;
  - `MacdSignal.ts`;
  - `BollingerSignal.ts`;
- aggiornare `registry.ts`, `ChartSignal.ts`, barrel export e test.

**Comportamento atteso**

- benchmark/comparison/Measure restano;
- remote definitions arrivano dal catalogo;
- nessun dual engine production.

**Test**

- search import;
- frontend unit;
- build/check;
- E2E views.

**Dipendenze**: F1 + Gate E.

**Accettazione**

- zero calcolo tecnico TS production;
- local signals invariati.

**Rischi**

- preview/modal o list card conserva import nascosto.

---

### F3 — Docs, instructions e knowledge layer

**Obiettivo**

Allineare documentazione e memoria progetto.

**File**

- `.github/instructions/frontend-signals.instructions.md`;
- nuova instruction backend signals;
- MkDocs plugin/indicator/AI Export docs;
- Phase 0 plan;
- devWiki;
- graph.

**Comportamento atteso**

- stack composito/fail-fast;
- plugin autonomy;
- JSON Schema mapper;
- 17 signal catalog;
- no cache Phase 0;
- add-plugin guide.

**Test**

- docs link check se applicabile;
- `./dev.py graph update`.

**Dipendenze**: F1-F2.

**Accettazione**

- nessuna doc descrive adapter centrale, contextual GET o cache Phase 0;
- piano marcato completo con note step-by-step.

**Rischi**

- analisi storiche restano contraddittorie senza nota superseded.

### Gate F — Completamento Phase 0

Phase 0 è completa quando:

- stack Pipenv/Docker/CI validato;
- framework e test backend verdi;
- 17 plugin production verdi;
- cataloghi statici Asset/FX completi;
- POST bulk calcolano availability dinamica e risultati;
- frontend shared foundation unica;
- Asset List/Detail e FX List/Detail migrati;
- AI Export migrato;
- engine tecnico TS rimosso;
- benchmark/comparison/Measure preservati;
- nessuna cache o DB migration introdotta;
- docs/devWiki/graph aggiornati.

## 6. Strategia di test

| Livello | Scope | Comandi principali |
|---|---|---|
| Schemi | signal models/OpenAPI | `./dev.py test schemas all` |
| Service | registry, service, plugin | `./dev.py test services all` |
| API | Asset/FX compatibility | `./dev.py test api all` |
| Frontend unit | mapper, renderer, request builder | `npm test` equivalente tramite runner esistente / `./dev.py` |
| Frontend Asset | list/detail | `./dev.py test front-asset all` |
| Frontend FX | list/detail/settings | `./dev.py test front-fx all` |
| Type/build | Svelte | `./dev.py front check`, `./dev.py front build` |
| API client | OpenAPI/Zodios | `./dev.py api sync` |

Per la parte visuale: niente pixel comparison massiva. Richiedere verifica manuale di
assi, colors, bands, histogram, tooltip, reference levels, value regions, dark mode e
responsive.

## 7. Parallelizzazione

### Sequenziale obbligatorio

```text
A1 → A2 → A3 → A4 → A5 → Gate A
Gate A → B1 → Gate B1
Gate B → C1-C4 → Gate C
Gate C → D1-D6 → Gate D
Gate D → E1 → E2/E3 → E4 → Gate E
Gate E → F1 → F2 → F3
```

### Parallelizzabile

| Dopo | Attività | Ownership consigliata |
|---|---|---|
| Gate B1 | B2, B3, B4 | agenti separati, plugin/test file distinti |
| Gate B | C2 Asset e C3 FX | agenti separati; coordinator possiede schemas barrel |
| D1 | test catalog mapper e renderer helpers | agente test separato |
| E1 validato | E2 Asset List e E3 FX Detail | separati, nessun file condiviso salvo helper già congelati |
| E3 validato | E4 + test FX settings | agente FX dedicato |

### Hotspot di conflitto

- `backend/app/schemas/__init__.py`;
- `backend/app/schemas/signals.py`;
- `backend/app/services/provider_registry.py`;
- `backend/app/services/signal_service.py`;
- `backend/app/api/v1/assets.py`;
- `backend/app/api/v1/fx.py`;
- `frontend/src/lib/charts/signals/registry.ts`;
- `ChartSignalsSection.svelte`;
- `ChartSettingsModal.svelte`;
- `LineChart.svelte`;
- `PriceChartFull.svelte`;
- `chartSettingsStore.svelte.ts`;
- generated API client.

Un solo owner per hotspot per wave.

## 8. Strategia di rollback

- Nessuna migration DB: rollback schema dati non necessario.
- Campi API signal opzionali: richieste legacy continuano.
- TS engine resta fino al Gate E.
- Migrazione per-view: rollback = ripristinare wiring della singola page.
- Plugin files isolati: un plugin problematico può essere rimosso dal registry/catalogo
  senza modificare gli altri, prima del release cutover.
- Gate A fallito: rimuovere dipendenze e rigenerare lock prima di proseguire.
- A3 non può atterrare senza A1: il backend non deve diventare inavviabile durante una
  wave intermedia.
- Gate C fallito: frontend non parte.
- Gate D/E fallito: backend può restare non consumato; nessun cutover.
- Nessun fallback silenzioso production tra TA-Lib e native.

## 9. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Warm-up instabile | sweep long-history; policy candidate → plugin test |
| TA-Lib silent fallback | startup fail-fast + spy `talib=True` |
| Fail-fast blocca tutto il backend | A1 valida boot dev/CI/Docker; A3 atterra solo con lock funzionante |
| `get_prices_bulk()` cresce troppo | estrarre helper interni per fasi, non nuovi layer pubblici |
| Payload list page elevato | `include_price=false` signal-only quando cache prezzi piena |
| FX daily expansion costosa | una request bulk, dedup e range massimo; benchmark Gate C |
| Worker Asset drop dei signals | estendere schema/result worker con test invalid payload |
| Preview globale senza contesto | policy D6, nessun raw endpoint |
| RSI/oscillator zone coloring | `value_regions` congelate in A2, stile applicato genericamente in D4 |
| Schema frontend non supportato | errore esplicito, nessun fallback |
| Event load inutile | requirement-driven load |
| Race range/params | request token/stale-response guard |
| Contratti OpenAPI complessi | Gate C prima del frontend |

## 10. Questioni emerse dall'analisi

1. **Global Detail**: non esiste. Il piano usa Asset List e FX List come superfici
   globali/per-card.
2. **Preview tecnica globale**: senza dominio non è calcolabile. La policy proposta è
   configurazione visibile ma overlay tecnico non renderizzato.
3. **RSI zone**: risolto nel piano con `value_regions` generiche nel contratto A2;
   validare che coprano anche StochRSI/MFI senza metadata signal-specific.
4. **`include_price=false`**: va implementato realmente per Asset signal-only requests;
   oggi il servizio non lo usa.
5. **List pages**: devono richiedere signals anche quando i price store non hanno gap.
6. **FX helper**: `ensureFxRangeLoaded*` restituisce solo rate points; serve un path
   condiviso per i grouped signal results senza trasformarlo in cache.
7. **Eventi**: Asset Detail li richiede già per la UI; gli altri consumer non devono
   caricarli per i 17 plugin iniziali.

## 11. Definizione di pronto per l'implementazione

Questo piano è pronto solo dopo validazione esplicita di:

- sostituzione di “Global Detail” con le quattro viste reali;
- preview policy D6;
- modello reference levels/value regions di A2;
- uso di `include_price=false` per richieste Asset signal-only;
- gate e parallelizzazione;
- file ownership/hotspot.

→ Nessuna implementazione production deve iniziare prima di tale validazione.
