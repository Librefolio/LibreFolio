# Piano Applicativo: Phase 0 — Migrazione Segnali Backend

**Stato**: 🚧 IN CORSO — implementazione approvata il 22 Luglio 2026.

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

**Stato**: ✅ COMPLETATO — 22 Luglio 2026.

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

> **Note implementazione**: pin production `pandas-ta-classic==0.6.52` e
> `TA-Lib==0.7.1` aggiunti con lock chirurgico; harness e fixture deterministiche
> creati. Validati 17 segnali, 16 path TA-Lib + Donchian nativo, fallback,
> warm-up cross-platform, gap/NaN, short input, performance, concorrenza, wheel
> cp313 macOS/Linux amd64/arm64, clean Pipenv sync, full app macOS e Docker.
> Evidenze e policy candidate:
> [spike-phase00SignalBackends.md](./spike-phase00SignalBackends.md).

> **⚠️ Fuori pista**: `./dev.py docker build` su macOS passa GID host `20`, già
> occupato da `dialout` nella base Debian; l'entrypoint fallisce perché il gruppo
> `librefolio` non esiste (`dev.py:1434-1435`, `Dockerfile:65-66`,
> `entrypoint.sh:25`). Bug preesistente non corretto fuori scope; immagine
> release-equivalent `1000:1000` validata. `pip check` espone inoltre conflitti
> transitive preesistenti non collegati allo stack segnali.

---

### A2 — Schemi backend neutrali

**Stato**: ✅ COMPLETATO — 22 Luglio 2026.

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

Semantica status:

- `ok`: input completi, compute riuscito, warm-up completo, output valido;
- `partial`: almeno un output visibile valido, warm-up incompleto o copertura temporale
  parziale esplicitamente ammessa, warning obbligatorio;
- `unavailable`: compute non avviabile per dominio, campi, coverage o storia minima;
- `failed`: input sufficienti ma eccezione, output invalido o contract violation.

Gap policy:

- nessuna compattazione arbitraria delle date;
- indice cronologico preservato;
- gap e missing field inclusi nelle metriche di coverage;
- default strict/contiguous;
- porzione temporale parziale ammessa solo dalla policy del plugin.

**Test**

- `extra="forbid"`;
- discriminated union;
- params/catalog serialization;
- invalid date/cardinality/status;
- structured errors;
- backward-compatible default-empty signal fields quando integrati;
- status matrix;
- gap/coverage metadata;
- partial con warning obbligatorio.

**Dipendenze**: A1 per i campi warm-up candidate, non per la struttura generale.

**Accettazione**

- OpenAPI generabile;
- nessun tipo pandas/TA-Lib;
- modelli sufficienti a tutti i 17 output;
- availability per instance rappresentabile.

**Rischi**

- output spec troppo specifico per un indicatore.

> **Note implementazione**: creato `backend/app/schemas/signals.py` con input
> OHLCV/event neutrali, execution context, warm-up, requirements anche event-only,
> catalogo schema-driven, line/bar/band discriminati, composite flat, assi/unità,
> reference levels, value regions, annotations, coverage/gap e availability.
> Congelata la matrice `ok|partial|unavailable|failed`: `ok` non ammette valori
> mancanti; `partial` richiede causa reale + warning; errori pre-compute non
> fabbricano availability/warm-up; metadata duplicati devono coincidere. Aggiunti
> barrel export, runner `./dev.py test schemas signals` e 54 test; intera suite
> schemas 6/6 verde e OpenAPI discriminata generabile.

> **⚠️ Fuori pista**: review logica pre-freeze ha rilevato tre blocker nel primo
> draft (failure unknown/invalid con metadata finti, `ok` con null, impossibilità
> di plugin event-only). Corretti prima del gate insieme a invarianti su
> `used_points`, coverage, gap interni e ordinamento band.

---

### A3 — `SignalPlugin`, registry e fail-fast

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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

> **Note implementazione**: introdotti `SignalPlugin` library-agnostic,
> `AbstractPluginRegistry`, `SignalPluginRegistry`, `@register_plugin`,
> discovery strict con errori aggregati, duplicate rejection e catalogo
> statico. `AbstractProviderRegistry` resta specializzazione compatibile:
> test Asset/FX/BRIM invariati. Aggiunto fail-fast minimale in
> `signal_runtime.py` e nel lifespan prima di DB/startup. Verificati 12 test
> registry, 6 runtime, 5 provider registry, 6 helper registry e 373 contratti
> provider. Startup/health validati su macOS arm64, Linux arm64 e Linux amd64;
> entrambe le immagini Linux rilevano stack `0.6.52 + 0.7.1` e catalogo vuoto
> atteso prima dei plugin production.

> **⚠️ Fuori pista**: Docker Desktop si è bloccato durante una build locale ed
> è stato ripristinato dall'utente. Il build successivo `./dev.py docker build`
> è verde. L'immagine locale GID `20` usa ancora il workaround numerico già
> documentato in A1; l'immagine amd64 release-equivalent `1000:1000` parte
> normalmente non-root.

---

### A4 — Infrastruttura test con plugin fixture

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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

> **Note implementazione**: aggiunto path/namespace discovery overridabile
> mantenendo invariato il default production. Creato registry test-only in
> `backend/test_scripts/fixtures/signal_plugins/` con 5 plugin:
> rolling line, band + composite flat, warm-up parameter-aware, compute failure
> e close + events. Aggiunte serie OHLCV/event deterministiche condivise e 10
> contract test su catalogo, params, requirements, output, alignment, failure e
> isolamento dal catalogo production. Regressioni signal/provider registry:
> 23 test verdi.

---

### A5 — `SignalService` con fixture plugin

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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
- complete/partial/insufficient coverage;
- internal gap senza date compaction;
- contiguous suffix ammesso/non ammesso;
- warning obbligatorio per partial;
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

> **Note implementazione**: creato `SignalService` con piano pre-load
> (`max_history_points_before_visible`, union campi/eventi), dedup
> code+normalized params, fan-out per instance ID, availability dinamica,
> coverage observed/backfilled/gap, strict policy e contiguous suffix opt-in.
> Batch intero eseguito con una sola `asyncio.to_thread`; plugin sequenziali,
> errori planning/compute/output isolati. NaN convertiti a `None`, infinity
> rifiutata, metadata/date/cardinalità verificati, output tagliato sul range
> visibile. Event load esplicito, inclusi plugin event-only. 29 test dedicati
> + regressioni schemas/registry/contracts/runtime verdi; doppio audit
> rubber-duck senza blocker residui.

> **⚠️ Fuori pista**: primo audit ha rilevato warm-up erroneamente calcolato
> sull'intera serie caricata. Corretto usando soltanto unità contigue prima di
> `requested_start`: nessun valore visibile → `unavailable`; ramp-up con almeno
> un valore → `partial`, mai `failed`. Corretti nello stesso pass event-only e
> `requires_events=True` senza tipi espliciti.

---

### A6 — Primitive tecniche di annotazione

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

**Obiettivo**

Derivare on-demand eventi tecnici da price point e output canonici, senza logica
specifica nel frontend.

**File**

- nuovo `backend/app/services/signal_annotations.py`;
- nuovo `backend/test_scripts/test_services/test_signal_annotations.py`;
- eventuali request/result option in `backend/app/schemas/signals.py`.

**Comportamento atteso**

- line crossover;
- threshold crossing upward/downward;
- equality/epsilon;
- dedup e min-gap;
- ordinamento per data;
- missing points;
- observed-only/data-policy filtering;
- calcolo sull'output esteso;
- slicing eventi sul range visibile;
- limit/sampling opzionali.

Le annotazioni vengono calcolate solo se il consumer invia `annotation_requests`.
Le regole request-level riferiscono instance ID/series key e threshold o altra serie.
I plugin non devono conoscere AI Export.

> **Note implementazione**: aggiunti source discriminati `price|signal`,
> request `line_crossover|threshold_crossing`, direction, epsilon, min-gap,
> observed-only, limit e sampling `recent|uniform`. `SignalAnnotationService`
> opera su price point e output canonici estesi, resetta lo stato su missing/gap,
> gestisce equality esatta, filtra/slicia/ordina e produce warning strutturati
> per source indisponibili. Integrato nel batch `SignalService` prima dello
> slicing: annotazioni attach per instance, source/target validate, failure
> isolate. Test: 60 schema, 13 primitive, 34 service verdi.

> **⚠️ Fuori pista**: audit ha trovato un touch esatto pre-visibile seguito da
> conferma al primo punto visibile che perdeva l'evento perché datato al touch.
> Ora usa la data del touch se visibile, altrimenti la data di conferma. Nel
> medesimo pass il merge plugin/batch viene ordinato globalmente per data.

**Test**

- crossing esatto;
- sopra/sotto;
- uguaglianza soglia;
- punti mancanti;
- serie corta;
- evento al bordo del range;
- observed-only;
- dedup/min-gap;
- order;
- limit.

**Dipendenze**: A2, A5.

**Accettazione**

- price/EMA, EMA/EMA, RSI threshold e MACD histogram/zero rappresentabili;
- nessuna dipendenza da librerie TA;
- nessun calcolo annotation se non richiesto;
- AI Export può dichiarare le proprie regole senza matematica frontend.

**Rischi**

- perdere un cross sul primo punto visibile se si annota dopo lo slicing;
- confondere AssetEvent con annotation tecnica.

### Gate A — Framework backend

**Stato**: ✅ SUPERATO — 23 Luglio 2026.

Non iniziare B1 finché:

- A1-A6 sono ✅;
- schema, registry, fixture e `SignalService` sono stabili;
- primitive annotation sono testate;
- test schema/services sono verdi;
- fail-fast stack composito è dimostrato;
- availability e slicing sono provati senza plugin production.

> **Note implementazione**: A1-A6 completati. Gate finale eseguito con
> `./dev.py test schemas all` (6/6 gruppi) e
> `./dev.py test services all` (44/44 gruppi), entrambi verdi. Framework,
> registry provider-compatible, runtime fail-fast, fixture test-only,
> SignalService, availability/warm-up/gap policy e annotations estese sono
> congelati per B1.

## Macrofase B — Plugin reali

### B1 — Quattro indicatori esistenti

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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

> **Note implementazione**: creati plugin autonomi `EMA`, `RSI`, `MACD`,
> `BOLLINGER`, tutti con chiamata locale esplicita `talib=True`, params
> schema-driven compatibili con chiavi frontend, output canonici e version.
> RSI risolve levels/regions dai params; MACD produce 2 line + histogram flat;
> Bollinger produce band; EMA applica offset dopo il calcolo. Sweep
> multi-parametro su trend/volatile/scale ha corretto e validato warm-up:
> EMA `6×period`, RSI `16×period`, MACD
> `8×max(slowPeriod, signalPeriod)`, Bollinger `period`, tolleranza `1e-6`.
> 46 test core, parity TA-Lib diretta e TypeScript convergente, short/gap,
> 45/45 gruppi service verdi. Startup reale: `plugin_count=4`, health 200.
> Audit dedicato: nessun blocker.

### Gate B1 — Pattern plugin

B2-B4 possono partire in parallelo solo dopo B1 validato.

**Stato**: ✅ SUPERATO — 23 Luglio 2026.

---

### B2 — Close-only aggiuntivi

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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

> **Note implementazione**: aggiunti `SMA`, `ROC`, `STOCH_RSI`, `KAMA`, `PPO`;
> catalogo close-only totale `9`, Asset+FX. Tutte le chiamate delegano con
> `talib=True` e testano anche la funzione C effettiva. StochRSI espone solo
> params realmente efficaci (`period`, `dPeriod`, thresholds), KAMA solo
> `period`; PPO normalizza composite 2 line + histogram e verifica
> `histogram = ppo - signal`. Warm-up multi-parametro a `1e-6`: SMA `N`,
> ROC `N+1`, StochRSI `16×max(period,d)`, KAMA
> `max(30,12×period)`, PPO `8×max(slow,signal)`. 62 test verdi inclusi
> direct TA-Lib, flat/trend/scale, short/gap e parità Asset/FX.

> **⚠️ Fuori pista**: audit ha rilevato KAMA `minimum_points` off-by-one per
> periodi ≥30. Corretto da `max(30, period)` a
> `max(30, period + 1)` con boundary test dedicato.

---

### B3 — OHLC

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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

> **Note implementazione**: aggiunti `ATR`, `ADX`, `NATR`, `AROON`,
> `DONCHIAN`, `CCI`, tutti Asset-only con required fields rigorosi. I primi 5
> delegabili usano `talib=True` e spy delle funzioni C; Donchian usa
> esclusivamente il path nativo pandas-ta. ADX normalizza ADX/+DI/-DI, Aroon
> Up/Down/Oscillator, Donchian band; CCI include levels/regions ±100.
> Missing/partial OHLC e FX producono `unavailable`, senza sintesi/compaction.
> Warm-up a `1e-6`: ATR/NATR `12×period`, ADX `18×period`, Aroon
> `period+1`, Donchian/CCI `period`. 75 test verdi.

> **⚠️ Fuori pista**: audit full-range period 2–200 ha trovato ADX
> `16×period` insufficiente su 32 valori intermedi. Portato a `18×period`
> (worst-case misurato ~`2.7e-7`) e aggiunti periodi 95/150/200 ai test.

---

### B4 — Volume

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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

> **Note implementazione**: aggiunti `OBV` e `MFI`, Asset-only,
> `talib=True` + spy funzioni C. OBV viene ribasato a zero sulla prima data
> disponibile `>= requested_start`, eliminando la dipendenza dalla storia
> completa; MFI usa OHLCV e levels/regions dinamici 20/80. Volume zero resta
> input valido e produce output zero; volume assente/parziale produce
> `unavailable`, mai sintesi o compaction. Warm-up: OBV `1`, MFI `period+1`.
> 30 test verdi; audit senza blocker.

> **⚠️ Fuori pista**: il test short generico assumeva erroneamente che un solo
> punto OBV fosse insufficiente; il contratto matematico produce invece output
> valido ma warm-up incompleto → `partial`. Separato boundary test. Audit ha
> inoltre segnalato un edge difensivo futuro con cadence `IRREGULAR` e range
> interamente oltre i dati; da coprire esplicitamente in B5.

---

### B5 — Matrice regressiva completa

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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

**Test**: matrice completa richiesta dal piano architetturale, inclusi:

- `ok|partial|unavailable|failed`;
- complete/partial/insufficient coverage;
- gap interno;
- nessuna date compaction;
- warning obbligatorio per `partial`.

**Dipendenze**: B2-B4.

**Accettazione**

- 17/17 passano;
- catalog definition completa;
- output canonici stabili.

**Rischi**

- test parametrico troppo generico nasconde bug specifici; mantenere anche test dedicati.

> **Note implementazione**: aggiunta matrice registry-driven su 17/17 plugin:
> catalogo/schema/defaults, 16 path `talib=True` + Donchian native, batch Asset
> completo, FX 9 close-only + 8 incompatible, exact minimum → `partial`,
> required field missing/partial, gap interno, cardinalità/spec/output JSON,
> invalid instance isolation e warm-up invariants. 63 test verdi, mantenendo
> tutte le suite dedicate B1-B4.

> **⚠️ Fuori pista**: l'edge B4 cadence `IRREGULAR` con range interamente
> fuori dai dati produceva output vuoto/failed. `SignalService` ora conta una
> boundary absence minima anche per serie irregolari e restituisce
> `unavailable` senza inventare date.

### Gate B — Catalogo plugin

**Stato**: ✅ SUPERATO — 23 Luglio 2026.

Non iniziare il frontend. Richiede:

- B1-B5 ✅;
- 17 plugin e test verdi;
- catalog metadata completi;
- contratti canonici congelati per Phase 0;
- warm-up verificato nei plugin.

> **Note implementazione**: 17 plugin production auto-discovered, 16 delegati
> TA-Lib + Donchian nativo. Suite finali:
> `./dev.py test schemas all` 6/6,
> `./dev.py test services all` 49/49,
> matrice uniforme 63/63. Startup test reale logga `plugin_count=17` e health
> 200. Gate C autorizzato; frontend resta bloccato.

## Macrofase C — Integrazione backend Asset e FX

### C1 — Cataloghi GET statici

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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

> **Note implementazione**: aggiunti GET auth-protected
> `/assets/prices/signals` e `/fx/currencies/signals`, filtrati dal registry
> statico per domain. Asset restituisce 17 definizioni, FX 9; ordine/codici
> deterministici, params/output/axis/unit/capability completi, nessuna
> availability o dependency DB/history. 4 test live API verdi.

---

### C2 — POST Asset bulk

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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
- status matrix e coverage;
- gap interno senza compattazione;
- events not loaded;
- partial plugin failure;
- response payload cap/size.

**Dipendenze**: Gate B, A5-A6.

**Accettazione**

- vecchi client verdi;
- signal result per instance;
- un solo load esteso;
- status/coverage conformi alla semantica A2;
- nessuna compattazione arbitraria delle date;
- errori segnale non compromettono prezzi.

**Rischi**

- `get_prices_bulk()` già grande;
- global range molto ampio per un solo plugin;
- worker/frontend dipendono dalla response completa.

> **Note implementazione**: `FAPriceQueryItem` ora accetta `signals` e
> `annotation_requests` default-empty con validazione ID/ref; result include
> `signals=[]`. `get_prices_bulk()` prepara un plan per item, estende ogni
> range del max warm-up, conserva una sola query globale, seed/backfill,
> event load condizionale e FX conversion prima del compute. Risultati segnale
> sono per instance, poi prices/events vengono sliciati al range originale;
> `include_price=false` omette solo la response. FX miss blocca il compute
> mixed-unit e produce unavailable. 9 service test, 2 live API, legacy
> Asset/source/API verdi.

> **⚠️ Fuori pista**: audit ha trovato seed condiviso troppo vecchio quando
> lo stesso asset appare più volte con range/warm-up diversi. Ora ogni item usa
> l'ultimo prezzo già nel `price_map` precedente al proprio start, fallback al
> seed DB globale; regression dedicata. Event values futuri sono inoltre
> gated sulla conversione target completa prima di `events_loaded=true`.

---

### C3 — POST FX bulk

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

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
- missing non-identity rate → `unavailable`;
- grouped signal results per original request;
- daily conversion results invariati;
- availability dinamica nelle POST.

**Test**

- identity;
- direct/inverse;
- backward fill;
- missing rate;
- status matrix e coverage;
- gap/short history;
- multi-pair;
- 9 close-only;
- rejection dei plugin OHLC/volume;
- no duplication per giorno;
- no-signal regression.

**Dipendenze**: Gate B, A5-A6.

**Accettazione**

- parity con Asset su serie close equivalente;
- response daily invariata;
- status/coverage conformi alla semantica A2;
- grouped results stabili.

**Rischi**

- confondere `rate=None` identity con missing rate;
- range expansion costosa.

> **Note implementazione**: `FXConversionRequest` accetta signals/annotations;
> `FXConvertResponse.signal_results=[]` raggruppa per request index, pair e
> range, mentre `FXConversionResult` daily resta invariato. Handler prepara un
> plan per request e invia una sola `convert_bulk` combinata: amount originale
> sul range visibile + amount `1` sul range esteso. Identity → close `1`;
> nonidentity → effective rate; missing points → unavailable. Errori signal
> estesi non contaminano gli errori daily; all-daily-failed con signal request
> restituisce grouped unavailable. 6 test nuovi + legacy FX API/service verdi;
> audit senza blocker.

---

### C4 — Compatibilità API e OpenAPI

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

> **Note implementazione**: suite complete verdi
> (`schemas` 6/6, `services` 50/50, `api` 46/46), OpenAPI rigenerata con
> `./dev.py api sync`, union `line|bar|band`, value-source e annotation request
> generate come `z.discriminatedUnion()` con discriminator `z.literal()`;
> `./dev.py front check` chiude con 0 errori e 0 warning.
>
> **⚠️ Fuori pista**: `openapi-zod-client` 1.18.3 con `--export-types` tipizza
> ogni option come `z.ZodType<T>`, nascondendo i metodi `ZodObject` richiesti da
> `z.discriminatedUnion()`. I discriminator backend sono ora required e
> descritti anche come enum singleton; un post-process fail-fast rimuove
> l'annotazione generica solo dalle sette option discriminate, preservando gli
> export type e la compatibilità del client esistente.

**Obiettivo**

Congelare i contratti prima del frontend.

**File**

- test schema/API;
- `frontend/src/lib/api/openapi.json` e `generated.ts` solo tramite
  `./dev.py api sync`;
- `frontend/scripts/fix-openapi-discriminators.mjs`.

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

**Stato**: ✅ SUPERATO — 23 Luglio 2026.

> **Note implementazione**: Gate A/B verdi; cataloghi espongono 17 plugin Asset
> e 9 FX; Asset/FX bulk restituiscono availability, serie e annotazioni senza
> regressioni no-signal; OpenAPI e client Zodios sono compilabili. Macrofase D
> autorizzata.

Il frontend può iniziare solo quando:

- Gate A e B superati;
- C1-C4 ✅;
- 17 Asset / 9 FX esposti;
- POST bulk calcolano availability e serie;
- backward compatibility verde;
- OpenAPI stabile.

## Macrofase D — Fondazione frontend condivisa

### D1 — Client generato e tipi runtime

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

> **Note implementazione**: aggiunti alias `z.input`/`z.output` in
> `backendTypes.ts`, separato `SignalDefinition` da `SignalConfig` e
> `SignalResult`, mantenendo invariato il formato persistito di `SignalConfig`.
> Fixture runtime line/bar/band/composite 4/4 e frontend check 0/0.

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

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

> **Note implementazione**: creati mapper catalogo e store session-level unico
> con cache per dominio, dedup delle fetch concorrenti, error state e retry
> esplicito. Il merge include cataloghi backend + soli signal locali
> comparison/benchmark, preserva compatibilità dominio e rifiuta collisioni.
> Test catalog/store 7/7 (inclusi Asset 17 / FX 9), frontend check 0/0.

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

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

> **Note implementazione**: `schemaMapper.ts` supporta
> number/integer/boolean/enum/string, required/default/min/max/step e metadata
> `x-*`; schema non supportato genera errore typed. `SignalParamControl.svelte`
> è il controllo unico per i backend signal; `ChartSignalsSection` riceve
> definizioni remote, usa i18n/docs dal catalogo e conserva i controlli dinamici
> locali comparison. Test mapper/config 7/7, frontend check 0/0.

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

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

> **Note implementazione**: `backendRenderer.ts` converte genericamente
> line/bar/band e composite flat, applica `base_percentage`, salta punti null,
> preserva status/warning/error e applica stile locale. Gli helper chart
> allocano assi dinamici per `role:key`, mantengono gli indici legacy e
> costruiscono `markLine`/`markArea` da reference levels/value regions.
> Coperti MACD, Bollinger, PPO, ADX, Aroon, Donchian, missing points,
> multi-axis e percent transform: 10/10 test, frontend check 0/0.

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

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

> **Note implementazione**: request planner separa config local/backend/unknown,
> rimuove params transienti, deduplica code+params e conserva tutti gli
> instance ID tramite alias. Il result mapper fanna il risultato canonico,
> preserva `ok|partial|unavailable|failed`, mantiene config rimosse come
> unavailable e usa uno state helper page-local con token stale-response.
> Test request/result 7/7, frontend check 0/0.

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

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

> **Note implementazione**: policy isolata in `previewPolicy.ts`: global renderizza
> solo signal locali e mostra il messaggio “target reale”; per-target usa
> esclusivamente gli ultimi `backendPreviewSignals` forniti dalla page e segnala
> “applica per aggiornare” o unavailable. Nessuna POST raw e nessuna chiamata
> al renderer TypeScript per definizioni backend. Aggiunte traduzioni EN/IT/FR/ES;
> test policy 4/4, frontend check 0/0, i18n 1778/1778 in tutte le lingue.

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

**Stato**: ✅ SUPERATO — 23 Luglio 2026.

> **Note implementazione**: D1-D6 verdi; catalog, mapper, configuratore,
> renderer, request/result state e preview policy sono condivisi e testati.
> Suite frontend completa 25 file / 240 test, `svelte-check` 0/0 e build
> production riuscita. Comparison, benchmark e Measure coperti da regression
> test; Macrofase E autorizzata.

Non migrare pagine finché:

- D1-D6 ✅;
- catalog, mapper, configuratore, renderer e request builder testati;
- preview policy validata;
- frontend check/build puliti;
- local benchmark/comparison/Measure invariati.

## Macrofase E — Migrazione viste reali

### E1 — Asset Detail

**Stato**: ✅ IMPLEMENTAZIONE COMPLETATA — 23 Luglio 2026
(`manual chart review` accorpata al Gate E).

> **Note implementazione**: Asset Detail carica il catalogo 17, separa config
> local/backend, invia tutte le istanze tecniche nella stessa POST prezzi,
> usa `include_price=false` su cache hit, fanna i dedup per instance e renderizza
> solo via renderer canonico. Range, currency e params rifanno la richiesta;
> modifiche di solo stile non chiamano il backend. Catalog/request error sono
> espliciti e i prezzi restano visibili. Suite frontend 240/240 e check 0/0.

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

**Stato**: ✅ COMPLETATO — 23 Luglio 2026.

> **Note implementazione**: `fetchAllPriceData()` costruisce un unico array
> bulk con ogni asset che necessita prezzi e/o signal; cache piena usa
> `include_price=false`. Ogni item porta tutte le instance applicabili e viene
> inviato da una sola `axiosInstance.post`. Worker Zod valida e preserva
> `signals`, inclusi payload signal-only, e segnala item invalidi. Card e modal
> usano risultati page-local + renderer canonico; comparison/benchmark restano
> locali. Test worker/request 9/9 e frontend check 0/0; Playwright conferma
> esattamente una POST bulk Asset per refresh.

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

- una singola POST bulk contenente tutti gli asset che richiedono prezzi e/o segnali;
- ogni item contiene le signal instance applicabili al relativo asset;
- nessuna richiesta per asset, card o segnale;
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
- worker invalid payload;
- network interception: esattamente una POST `/api/v1/assets/prices/query` per refresh
  della view.

**Dipendenze**: E1.

**Accettazione**

- card non calcolano tecnici TS;
- esattamente una POST bulk, non una per asset/segnale/card;
- UI resta responsiva.

**Rischi**

- payload/compute elevato su molti asset;
- worker drop dei signal results.

---

### E3 — FX Detail

**Stato**: ✅ IMPLEMENTAZIONE COMPLETATA — 23 Luglio 2026
(`manual chart review` accorpata al Gate E).

> **Note implementazione**: FX Detail carica il catalogo close-only 9 e, quando
> richiesto, usa una POST convert full-range con tutte le instance; estrae il
> grouped result `request_index=0` e renderizza via contratto canonico. La
> richiesta usa l'orientamento visualizzato, mentre i daily rates vengono
> reinvertiti prima del merge nello store canonico; lo swap URL forza il
> ricalcolo tecnico. Cache senza signal resta sul path esistente. Test
> direct/inverted/identity/backfill + mapping 16/16, frontend check 0/0.

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

**Stato**: ✅ IMPLEMENTAZIONE COMPLETATA — 23 Luglio 2026
(`manual chart review` accorpata al Gate E).

> **Note implementazione**: nuovo bulk helper raccoglie tutte le pair che
> richiedono rate e/o signal e invia esattamente una POST convert. Pair cached
> con tecnici restano nella request; rates sono normalizzati nello store
> canonico e signal grouped restano page-local. Card/modal usano il renderer
> condiviso; inversione card/table forza un signal-only bulk refresh.
> Test helper dimostra 2 pair/1 POST, grouped request-index, cache+signals e
> inversione: FX store/request 18/18, frontend check 0/0; Playwright conferma
> esattamente una POST bulk FX per refresh.

**Obiettivo**

Migrare card, settings globali/per-pair e bulk multi-pair.

**File**

- `frontend/src/routes/(app)/fx/+page.svelte`;
- `frontend/src/lib/stores/fxStoreRegistry.ts`;
- FX card;
- `frontend/e2e/fx/fx-list.spec.ts`;
- `frontend/e2e/fx/fx-chart-settings.spec.ts`.

**Comportamento atteso**

- una singola POST bulk contenente tutte le coppie FX che richiedono tassi e/o segnali;
- ogni item contiene le signal instance applicabili alla relativa pair;
- nessuna richiesta per pair, card o segnale;
- price store e signal results separati;
- global/per-pair settings;
- 9 close-only;
- modal preview policy.

**Test**

- multi-pair;
- cached rates + signals;
- inversion;
- settings globali/per-card;
- partial pair failure;
- network interception: esattamente una POST `/api/v1/fx/currencies/convert` per
  refresh della view.

**Dipendenze**: E3.

**Accettazione**

- card non calcolano tecnici TS;
- esattamente una POST bulk, non una per pair/segnale/card;
- nessuna duplicazione configuratore/renderer.

**Rischi**

- response grouping per original request;
- molti range daily espansi.

### Gate E — Parità viste

**Stato**: ✅ SUPERATO — 25 Luglio 2026.

> **Note implementazione**: E1-E4 implementati; 17 Asset / 9 FX disponibili
> per capability, technical path UI esclusivamente backend, rollback ancora
> possibile perché le classi TypeScript non sono state eliminate. Evidenze:
> frontend 26 file / 246 test, `svelte-check` 0/0, build production verde,
> Playwright desktop 1/1 Asset bulk + 1/1 FX bulk, i18n 1780/1780 × 4 lingue.
>
> **⚠️ Fuori pista**: code review ha rilevato e corretto un banner signal
> fuorviante causato da item price invalidi senza signal configurati.
>
> **Note review visuale — round 1 (23 Luglio 2026)**: ripristinato toggle
> dell'intera barra Segnali in Asset/FX Detail senza intercettare AI Export.
> Selector tecnici rifatto come albero ricercabile
> Trend/Momentum/Volatilità/Volume, con emoji plugin-owned, nomi e descrizioni
> brevi human-friendly, sottotitolo dei campi input e tipografia condivisa con
> Confronto/Benchmark. Corretto crash Candlestick: asse Volume non è più
> hardcoded a `yAxisIndex=3`, ma segue gli assi signal dinamici; anche gli
> overlay ricevono prima l'asse canonico. Traduzioni 1826/1826 × 4,
> test mapper/chart 8/8, check 0/0 e build production verde.
>
> **Note review visuale — round 2 (23 Luglio 2026)**: sottotitoli dei selector
> renderizzati con lo stesso helper KaTeX dei tooltip; `OrderableList` esteso con
> griglia responsive opt-in a card equi-larghe e tono warning amber; cause
> backend `partial`/`unavailable`/`failed` propagate fino alla card con dettaglio
> campi OHLCV, copertura, warm-up e gap. Corpus devWiki lasciato invariato perché
> sarà rigenerato dal Graphify finale. Test mapping 2/2, plugin matrix 63/63,
> check 0/0, build frontend e MkDocs verdi, link docs 22/22.
>
> **Note review visuale — round 3 (23 Luglio 2026)**: corretto mismatch i18n dei
> badge (`{n}` nelle quattro lingue, non `{count}`); in build debug ogni risultato
> signal problematico stampa un warning strutturato con Asset ID/nome/ticker,
> signal, params, status, warning, availability, warm-up ed errore. Probe
> read-only sul DB produzione, Apple/AAPL (1980-12-12 → 2026-07-23): su range
> 1Y e 5Y i 9 plugin close-only sono `ok`; gli 8 OHLC/volume sono
> `unavailable` per 1–2 punti finali incompleti, non per errore formula.
> `svelte-check` 0/0 e i18n 1837/1837 × 4.
>
> **Note review visuale — round 4 (23 Luglio 2026)**: probe prod completo su
> Apple/AAPL, Asset 15, range 2025-07-23→2026-07-23. Confermata qualità input
> realmente incompleta (`2026-07-22`: solo close; `2026-07-23`: volume assente),
> ma classificata come falso errore la conseguente indisponibilità totale di 8
> plugin. `ALLOW_PARTIAL_CONTIGUOUS` ora sceglie il segmento completo più recente
> con storico minimo, altrimenti il più lungo, senza mai compattare il gap.
> Risultato prod: 9 signal `ok`, 8 `partial`, 0 `unavailable`/`failed`; gli 8
> field-rich renderizzano 2025-07-23→2026-07-21 e spiegano 617/618 (99,8%) o
> 616/618 (99,6%) come punti input completi, warm-up incluso. Service 37/37,
> plugin matrix 64/64, Asset integration 9/9 e API 2/2.
>
> **Note review visuale — round 5 (24 Luglio 2026)**: i tre selector usano ora
> lo stesso `SignalTreeSelect`; Indicatori mantiene i gruppi, Confronto e Benchmark
> usano la modalità flat con ricerca e identica estetica. `SignalValueRegion`
> espone `line_style`: RSI, CCI, MFI e Stochastic RSI delegano al backend soglie,
> inclusività e stile, mentre il renderer genera slice temporali generiche
> (neutro tratteggiato, estremi solidi) senza switch per signal code e senza le
> precedenti guide orizzontali ridondanti. Il controllo line type viene nascosto
> quando lo stile è region-driven, mentre colore, spessore e marker restano
> configurabili. I problemi sono contestualizzati:
> fino a due punti edge mancanti diventano info neutra, `partial` materiale resta
> amber, `unavailable`/`failed`/assenza dati diventa rosso. Unit frontend 20/20,
> backend FIFO+signal 187/187, `svelte-check` 0/0 e build production verde.
>
> **Note review visuale — round 6 (24 Luglio 2026)**: verificato MFI prod su
> Apple: 616/618 punti completi (99,6%), con volume assente il 22 e 23 luglio
> 2026 — mercoledì e giovedì, non weekend. Lo status backend resta correttamente
> `partial`, ma il buffer UI/debug classifica fino a due difetti edge con
> copertura ≥99% e impatto ≤2 come `notice`: card neutra, icona info e
> `console.info` invece di warning. `SignalTreeSelect` supporta ora
> ArrowUp/ArrowDown, Home/End, Enter su item, Enter/ArrowLeft/ArrowRight sui
> gruppi, highlight e auto-scroll; ricerca e selector flat condividono la stessa
> navigazione. `svelte-check` 0/0 e build production verde.
>
> **Note review visuale — round 7 (24 Luglio 2026)**: policy warning coverage
> resa globale e cadence-aware. `SignalInputCoverage` espone
> `max_consecutive_missing_points`; un `partial` diventa amber solo con copertura
> ≤95% o streak mancante >7, altrimenti resta notice informativa. MFI/OBV
> Apple 616/618 (99,6%, streak 2) non generano più warning console/card.
> Introdotto contratto visuale plugin-owned unico per output e partizioni:
> `color_role`, pattern, delta spessore, opacity, label e description. ADX resta
> correttamente composto da tre linee standard (ADX, +DI verde, −DI rossa);
> MACD/PPO mantengono due linee + istogramma perché l'istogramma è un output
> matematico definito. Aroon e Stochastic RSI ricevono stili distinti. Ogni card
> backend mostra componenti e zone in una legenda responsive con tooltip, usando
> lo stesso metadata del renderer. La validazione runtime rifiuta divergenze
> style/description rispetto al catalogo; warm-up incompleto mantiene priorità
> warning anche in presenza di gap minori. Backend 165/165, frontend 21/21, i18n
> 1904/1904 × 4, `svelte-check` 0/0, build frontend e MkDocs verdi.
>
> **Note review visuale — round 8 (25 Luglio 2026)**: corretto `Δ1%` nelle tabelle
> posizioni. Prima divideva il Δ P&L giornaliero per il P&L latente del giorno
> precedente, quindi un movimento 27,81→27,84 poteva apparire come +7%; ora usa
> il valore di mercato assoluto della posizione precedente e restituisce +0,11%
> sul caso XGBE, preservando segno short e `quote_base_quantity`. Tooltip pinned
> esteso a 30 secondi, con dismiss immediato su scroll/click esterno, larghezza e
> touch target mobile maggiorati. Il selector non mostra più l'unione OHLCV del
> gruppo: ogni indicatore espone i propri campi esatti (`EMA: Close`, ecc.).
> Ripristinate e formattate integralmente le quattro risorse i18n:
> 1905/1905 EN/IT/FR/ES. Formula backend 3/3, signal unit 21/21, Tooltip E2E 6/6,
> `svelte-check` 0/0 e build production verde.
>
> **Note review visuale — round 9 (25 Luglio 2026)**: la legenda visuale è ora
> anche editor. Ogni output backend e ogni partizione/zone conserva override
> indipendenti in `SignalConfig.componentStyles` / `partitionStyles`; colore,
> pattern, spessore e marker delle linee sono separati. Il selettore comune sotto
> la card è stato rimosso per i signal backend e resta solo come fallback per
> comparison/benchmark locali e vecchie config. Istogrammi restano signed
> verde/rosso finché non personalizzati, poi usano il colore scelto; band e zone
> seguono i rispettivi editor. I soli cambi stile non modificano request params e
> non rifanno la POST. Renderer/style unit 21/21, `svelte-check` 0/0 e build
> production verde.
>
> **Note review visuale — round 10 (25 Luglio 2026)**: rimosso il parent editor
> ridondante quando le partizioni coprono l'intero dominio numerico. Il mapper
> calcola `fullyPartitioned` verificando estremi aperti e continuità/inclusività
> delle soglie, senza switch per signal code. RSI/CCI/MFI mostrano solo le zone;
> Stochastic RSI nasconde `%K` partizionato ma conserva `%D`; output con regioni
> parziali mantengono il parent. Mapper/renderer 19/19, `svelte-check` 0/0 e build
> production verde.
>
> **Note review visuale — round 11 (25 Luglio 2026)**: tradotta la chiave
> `signals.params.dPeriod` e introdotto metadata generico
> `x-affects-outputs`. La card mostra ora `Agisce su: %K · %D` per il periodo,
> `%D` per `dPeriod`, `%K` per le soglie; le partizioni sono intestate
> esplicitamente `Zone %K`. I suffix `days` sono localizzati tramite
> `signals.units.days`. L'audit i18n scansiona anche `x-i18n-key` /
> `x-tooltip-key` in `backend/app` e fallisce se una chiave backend manca:
> 1911/1911 × 4, backend missing 0. Mapper 10/10, Stochastic plugin 3/3,
> `svelte-check` 0/0.
>
> **⚠️ Fuori pista — Dettaglio Lotti FIFO (24 Luglio 2026)**: il pannello non
> eredita più il range Dashboard/Broker e richiede sempre l'intero ciclo dei
> lotti. La query prezzi è limitata dalla prima transazione, conservando un seed
> precedente per il fallback del prezzo di apertura. Il range Y PMC/prezzo
> include valore e raggio massimo delle bubble, evitando clipping ai bordi.
>
> **⚠️ Fuori pista — isolamento cache multi-utente (23 Luglio 2026)**: la review
> manuale ha scoperto che `portfolioStore` e `brokerStore` sopravvivevano al
> logout SPA e potevano mostrare dati dell'account precedente. Introdotto
> `ClientSessionState`: reset centralizzato al cambio identità, chiavi portfolio
> user-scoped, generation guard per risposte in-flight e reset di broker, asset,
> transazioni, preview file, settings utente, chart/date/navigation state e
> cache UI. Aggiunto invalidatore centrale per mutation API che influenzano il
> Portfolio Engine e token monotono sulle operazioni auth per neutralizzare
> `/auth/me` tardivi. Frontend unit 275/275, check 0/0 e build production verde.
>
> **Approvazione Gate E (25 Luglio 2026)**: review visuale conclusa con esito
> positivo dopo undici round. F1 autorizzata; rimozione engine TypeScript resta
> subordinata al cutover AI Export.

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

**Stato**: 🟡 REPORT ARCHITETTURALE V2 COMPLETATO — piano esecutivo pendente.

> **Nota di scope (25 Luglio 2026)**: F1 non sarà una migrazione 1:1 dei vecchi
> EMA/RSI/MACD. La nuova fotografia userà un profilo sviluppatore-curato con più
> segnali, dati e incroci, omissione totale delle sezioni senza punti e budget
> token misurati ma non distruttivi. I profili sono curati per
> `domain + task + detail_level`; `full` non applica top-N automatici. Nessun
> auto-enrollment dei plugin in questa fase.
>
> **Analisi**:
> [AI Export F1 — Architettura e fotografia dati curata](./analysis-phase00AiExportArchitectureAndSnapshot.md)

**Obiettivo**

Costruire una fotografia AI backend, curata e token-bounded, riutilizzabile da
frontend e futuro MCP; eliminare il secondo calcolo tecnico frontend.

**File**

- `backend/app/schemas/ai_export.py`;
- `backend/app/services/ai_export/`;
- `backend/app/api/v1/ai_export.py`;
- `frontend/src/lib/features/ai-export/technical/technicalExportBuilder.ts`;
- `technicalEvents.ts`;
- Asset/FX/Portfolio/Broker export builders e renderer;
- test AI Export.

**Comportamento atteso**

- endpoint read-only autenticato `POST /api/v1/ai-export/snapshot`;
- `user_id` derivato dalla sessione e broker scope validato server-side;
- request `domain + task + detail_level` con combinazioni allow-listed;
- `schema_version`, `profile_id/profile_version` e range/date distinti;
- ogni task allow-listed ha backend profile e frontend response contract
  versionati;
- profili sviluppatore-curati per Asset, FX, Dashboard e Broker;
- livelli `compact`, `standard`, `full` espliciti;
- nessun top-N implicito in `full`;
- tutte le posizioni aperte previste dal detail level;
- bundle tecnici ampliati secondo l'analisi F1;
- asset/posizioni preservati anche senza indicatori tecnici;
- soltanto segnali/componenti/sezioni senza punti completamente omessi;
- coverage e breadth ponderata dichiarate;
- raw values, derived states ed events separati;
- normalized return 3M semanticamente compatibile col vecchio export;
- warm-up plugin applicato prima di slicing/normalizzazione/sampling;
- fallback ultima BUY esposto come valuation reference, non market return;
- cash decomposition mappata dal Portfolio Engine;
- currency allocation semantics esplicite;
- allocazioni PAC preservate per asset, asset type, settore, geografia, valuta e
  broker;
- nessun warning/unavailable/error testuale nel prompt standard;
- instructions, snapshot, domain notes e user notes separati;
- serializer YAML/Markdown robusto e prompt-injection aware;
- metric semantics e signal semantics canoniche;
- privacy awareness nel feedback post-copy;
- sampling e precisione applicati nel backend;
- budget restituiti come telemetria non distruttiva;
- prompt catalog e rendering finale restano frontend in F1;
- servizio snapshot invocabile direttamente dal futuro MCP;
- nessun auto-enrollment dei nuovi plugin;
- Portfolio Risk Review rinviata;
- band-boundary crossing incluso come sub-step isolato.

**Test**

- snapshot fixture per Asset, FX, Dashboard e Broker;
- auth, user scope e broker access;
- omissione componenti/sezioni tecniche vuote senza eliminare asset/posizioni;
- partial con punti incluso senza spiegazioni;
- coverage/breadth coverage;
- precisione, sampling e telemetry;
- parity normalized return vecchio/nuovo;
- long-window warm-up su technical window brevi;
- fallback ultima BUY senza serie/indicatori artificiali;
- compatibilità semantica PAC/portfolio export;
- copertura esplicita delle sei dimensioni di allocazione PAC;
- cash decomposition e currency semantics;
- event limits e deduplica;
- note con colon/quote/newline/backtick/instruction-like text;
- versionamento DTO/profilo/task contract;
- profili statici non modificati dal plugin registry;
- compatibilità semantica dei prompt catalog esistenti.

**Dipendenze**: Gate E.

**Accettazione**

- nessun import di classi tecniche TS;
- nessuna matematica tecnica AI Export nel frontend;
- quattro domini consumano snapshot backend;
- prompt/task/lingua restano frontend-owned;
- snapshot/profili/task contract versionati;
- warm-up long-window verificato su technical window brevi;
- profilo full senza top-N impliciti;
- snapshot privo di null tecnici, sezioni tecniche vuote e failure prose;
- nessuna posizione omessa per assenza indicatori;
- technical coverage dichiarata;
- normalized return compatibile;
- valuation fallback non rappresentato come market return;
- cash decomposition engine-owned;
- note trattate come contesto e serializzate in modo sicuro;
- note/descrizioni autorizzate esportabili come contesto;
- metriche e segnali con semantica/unità deterministiche;
- privacy banner post-copy;
- servizio riusabile senza UI;
- payload deliberatamente ridisegnato e coperto da fixture versionate.

**Rischi**

- differenze numerical/warm-up cambiano eventi;
- snapshot full può superare il context esterno e richiede scelta utente;
- profili compact possono nascondere dati se la profondità non è esplicita;
- endpoint AI non correttamente scoped può esporre dati cross-user;
- nuova primitive band-boundary amplia schema e annotation resolver;
- parity normalized return può divergere su finestre incomplete.

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

**Stato**: 🟡 IN CORSO — guida plugin e teoria finanziaria completate; cleanup e
knowledge layer restano dipendenti da Gate E/F1-F2.

> **Note implementazione (23 Luglio 2026)**: aggiunta la Developer Guide
> `signal_plugin_guide.md` con architettura runtime/service/annotations, lifecycle,
> contratto `SignalPlugin`, status/data policy, esempio completo, metadata JSON
> Schema, checklist e gate test. Aggiornati overview Registry Pattern e nav
> Developer Manual. MkDocs strict build e cross-boundary link check verdi.
>
> **Note implementazione (24 Luglio 2026)**: scorporati nella Signal Plugin Guide
> il diagramma del sottosistema e il sequence diagram delle chiamate; documentato
> `SignalValueRegion.line_style`. Home EN aggiornata con il quarto nodo orbitale
> Technical Signal Plugins, contributi EN collegati alla guida. MkDocs strict
> build e link check restano verdi; traduzioni rinviate alla pipeline.
>
> **Note implementazione (24 Luglio 2026, round 2)**: diagramma architetturale
> ridotto a un flusso verticale con sole relazioni dirette e frecce orientate;
> rimossi collegamenti senza punta e fan-out incrociati. Documentati
> `SignalOutputStyle`, ruoli colore semantici, legenda card condivisa, scelte
> standard ADX/MACD/PPO/Stochastic RSI e soglia warning 95%/7.

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
A1 → A2 → A3 → A4 → A5 → A6 → Gate A
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
