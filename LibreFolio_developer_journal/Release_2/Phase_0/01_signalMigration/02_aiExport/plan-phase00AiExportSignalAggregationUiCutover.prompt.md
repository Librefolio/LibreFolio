# Phase 0 — Signal aggregation e AI Export UI/clipboard cutover

**Stato**: 🟢 IMPLEMENTAZIONE OGGETTIVA COMPLETATA — STOP PER REVIEW UTENTE
**Data**: 29 luglio 2026

← Checkpoint:
[AI Export e aggregazione Signal Plugin](./plan-phase00AiExportCheckpointSignalAggregation.prompt.md)

← Piano architetturale:
[AI Export dataset/analysis refinement](./plan-phase00AiExportRefinementImplementation.prompt.md)

## 1. Obiettivo e stop obbligatorio

Completare il sistema dal contratto backend fino a una UI funzionante sulle quattro
pagine, in cui l'utente possa:

- scegliere fotografia/analisi, detail e periodo;
- vedere i Signal aggregati correttamente daily/weekly/monthly;
- vedere Drawdown come area riempita da zero;
- generare e copiare data-only o prompt completo;
- ispezionare nel testo copiato bucket Signal con date e statistiche.

Dopo unit test oggettivi, API sync, type-check e build:

```text
STOP
→ nessuna valutazione qualitativa dei prompt
→ nessun test visuale/E2E
→ nessun cleanup legacy
→ nessuna Developer Guide estesa
→ nessun wiki ingest/lint/graph
→ handoff all'utente per review
```

## 2. Confine architetturale

```text
Backend SignalService
    → carica slice completo + warm-up
    → calcola serie completa
    → restituisce serie visibile completa

Frontend chart
    → raggruppa daily/weekly/monthly
    → sceglie un rappresentante per bucket dal profilo enum

Backend AI Export
    → usa stesso range completo + warm-up
    → applica BucketPlan adattivo
    → emette statistiche complete first/min/max/last

Frontend prompt renderer
    → compone istruzioni + contract + snapshot YAML
    → formatta date tecniche YYYY/MM/DD
    → copia negli appunti
```

Vietato:

- chiedere al backend soltanto date puntuali;
- calcolare Signal sui soli punti rappresentativi;
- aggiungere logica per `signal_code` nel frontend;
- introdurre hook custom di aggregazione;
- far costruire/inviare prompt finali al backend;
- chiamare un LLM da LibreFolio.

## 3. Profilo enum unico

```python
class SignalAggregationProfile(StrEnum):
    LAST_WITH_RANGE = "last_with_range"
    FIRST_WITH_RANGE = "first_with_range"
    MIN_WITH_RANGE = "min_with_range"
    MAX_WITH_RANGE = "max_with_range"
    BAND_ENVELOPE = "band_envelope"
    EVENTS_VERBATIM = "events_verbatim"
```

| Profilo | UI chart | AI text |
|---|---|---|
| `LAST_WITH_RANGE` | ultimo valore | first/min/max/last + date |
| `FIRST_WITH_RANGE` | primo valore | first/min/max/last + date |
| `MIN_WITH_RANGE` | minimo | first/min/max/last + date |
| `MAX_WITH_RANGE` | massimo | first/min/max/last + date |
| `BAND_ENVELOPE` | lower=min, middle=last, upper=max | stats complete per componente |
| `EVENTS_VERBATIM` | tutti marker | eventi completi con data |

Nessun `CUSTOM`. Nuovo caso futuro richiede enum + dispatcher Python/TypeScript + test.

## 4. Statistica canonica

Per ogni output continuo:

```text
bucket_start
bucket_end
calendar_days
observation_count
first = {value, observed_date}
min   = {value, observed_date}
max   = {value, observed_date}
last  = {value, observed_date}
```

Regole:

- tie min/max → prima osservazione cronologica;
- zero osservazioni → bucket esplicito/null;
- una osservazione → `{value, date}`;
- date osservazioni reali;
- first non sostituito da previous_last;
- niente weekday/day-of-year;
- `calendar_days` + `observation_count`.

Multi-output: una riga per bucket, una colonna per output.

Bande:

- colonne lower/middle/upper;
- ogni cella ha statistiche/date proprie;
- testo AI non finge simultaneità;
- UI envelope sintetico validato `lower <= middle <= upper`.

## 5. Mapping plugin iniziale

`MIN_WITH_RANGE`:

- `RISK_DRAWDOWN`.

`MAX_WITH_RANGE`:

- `ATR`;
- `NATR`;
- altre misure peak-risk solo dopo audit.

`LAST_WITH_RANGE`:

- SMA/EMA/KAMA;
- RSI/MFI/CCI/Stoch RSI/ROC;
- MACD/PPO;
- ADX/Aroon;
- OBV;
- altri continui non classificati.

`BAND_ENVELOPE`:

- Bollinger;
- Donchian.

`EVENTS_VERBATIM`:

- annotation/transizioni.

Ogni output auto-discovered deve dichiarare esplicitamente il profilo.

## 6. Drawdown AREA

```python
class SignalSeriesKind(StrEnum):
    LINE = "line"
    AREA = "area"
    BAR = "bar"
    BAND = "band"
```

Drawdown:

- `kind=AREA`;
- `aggregation=MIN_WITH_RANGE`;
- asse massimo `0`;
- fill da `0` al valore negativo;
- `fill_opacity=0.20` iniziale;
- tooltip: bucket start/end + data reale trough.

Frontend:

- AREA = ECharts line series;
- `areaStyle.origin = 0`;
- nessun controllo sul signal code.

## 7. Allineamento category axis

Bug corrente:

- prezzo e Signal aggregati separatamente;
- Signal filtrato per date finali del prezzo;
- calendari divergenti possono rimuovere bucket/serie.

Target:

1. chiave logica `bucket_start|bucket_end`;
2. prezzo e Signal usano stessa mappa bucket;
3. una coordinata UI per bucket;
4. data renderizzata = data bucket prezzo;
5. `representative_date` = data reale min/max/last;
6. join per bucket key, non date equality;
7. tooltip espone representative date.

## 8. Composizione prompt

Backend:

- produce dati/manifest/contract identities;
- non costruisce prompt;
- non riceve prompt;
- non chiama AI.

Frontend:

```text
1. Analysis Objective
2. Shared Verification Instructions
3. Response Contract
4. Snapshot Metadata / Dataset Manifest
5. Snapshot Data YAML
6. Additional LibreFolio Data
7. Domain Notes
8. User Notes
9. Response Language
```

Dataset → data-only.
Analysis → full prompt.

Date tecniche nel testo copiato: `YYYY/MM/DD`.

## 9. Step P0 — Piano e baseline

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

- materializzare questo piano;
- cross-linkare checkpoint/refinement/README;
- verificare fragment 25 Portfolio/Broker + 20 Asset/FX;
- verificare import-cycle/parity;
- fotografare baseline post-checkpoint.

Gate:

- zero agenti attivi;
- fragment importabili;
- counts/parity corretti;
- central registry ancora non modificato.

> **Note implementazione**: piano materializzato/cross-linkato. Fragment verificati:
> 25 componenti Portfolio/Broker e 20 Asset/FX, metadata parity e placeholder
> fail-closed corretti. Aggiunto al runner canonico il file integration Asset/FX,
> precedentemente escluso; gate parity: 5 test passati su 872 raccolti. Central
> registry non toccato.

## 10. Step P1 — Contratto backend Signal

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

1. `SignalAggregationProfile`.
2. `SignalSeriesKind.AREA`.
3. `SignalOutputSpec.aggregation_profile`.
4. `SignalOutputStyle.fill_opacity`.
5. Dichiarazione esplicita su ogni plugin output.
6. Drawdown AREA + MIN.
7. Catalog/OpenAPI.

Gate:

- tutti plugin espliciti;
- nessun default implicito production;
- SignalService produce ancora full slice.

> **Note implementazione**: aggiunti `SignalAggregationProfile`,
> `SignalSeriesKind.AREA`, `SignalAreaSeries` discriminato e
> `SignalOutputStyle.fill_opacity`. Tutti i 22 plugin production dichiarano il
> profilo per ogni output: Drawdown = AREA/MIN, ATR+NATR = MAX,
> Bollinger+Donchian = BAND_ENVELOPE, gli altri output continui = LAST.
> Registry fail-closed sugli output production impliciti; consumer scalar
> backend (annotation, AI Export legacy e fixture) estesi ad AREA. Gate:
> 94 schema, 19 registry, 65 matrix, 45 SignalService, 20 annotation,
> 74 Risk e 872 AI Export test passati.
>
> **⚠️ Fuori pista**: le fixture plugin di test dipendevano dal precedente
> default implicito e i test schema consideravano ancora `area` un discriminator
> sconosciuto; aggiornati entrambi al nuovo contratto esplicito.

## 11. Step P2 — Canonical bucket stats Python

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

- typed first/min/max/last + date;
- tie-breaking;
- empty/single;
- band component stats;
- event passthrough;
- enum dispatcher;
- fixture JSON comune Python/TS.

> **Note implementazione**: il temporal engine espone statistiche scalari
> immutabili con date reali, tie-break cronologico, bucket empty/single,
> aggregazione indipendente lower/middle/upper e envelope validato
> lower=min/middle=last/upper=max. `aggregate_signal_buckets()` dispatcha
> esclusivamente il profilo enum e riusa il passthrough/dedup eventi esistente.
> `aggregate_ohlc()` ora proietta le nuove statistiche senza cambiare il suo
> contratto. Fixture condivisa:
> `backend/test_scripts/fixtures/signals/aggregation_profiles.v1.json`.
> Gate completo AI Export: 877 test passati; ruff/black mirati verdi.

## 12. Step P3 — AI Export technical rows

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

- row-oriented buckets;
- columns per output;
- cells single/range stats;
- variable bucket metadata;
- same 20 Asset/PB + 12 FX signals;
- no event/entity truncation.

> **Note implementazione**: hard replacement del payload indicatori con una
> tabella per istanza plugin: colonne per output/componente band, righe per
> `BucketPlan`, `calendar_days`, observation count e celle `single` oppure
> `range` con first/min/max/last e date reali. MACD/PPO/ADX/Aroon/StochRSI
> preservano località temporale; Bollinger/Donchian espongono lower/middle/upper
> indipendenti; `aggregation_profile`, kind e latest datato restano
> plugin-owned. Eventi restano verbatim e senza cap. Il metadata aggregatore
> indicatori è ora `signal_profile_bucket`, distinto da OHLC prezzi/rate.
> Gate completo AI Export: 880 test passati; ruff/black verdi.
>
> **⚠️ Fuori pista**: il catalogo placeholder descriveva ancora gli indicatori
> come `ohlc_bucket`; aggiornato il solo metadata a
> `signal_profile_bucket` per mantenere parity col fragment, senza anticipare
> la sostituzione dei builder placeholder prevista in P4.

## 13. Step P4 — Real component registry

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

- chiudere fragment verification;
- sostituire 45 placeholder;
- costruire 18 dataset/17 analisi;
- all_data dedup;
- no import cycles/I/O duplicate.

> **Note implementazione**: `build_component_registry()` restituisce ora i 45
> builder reali in ordine canonico, unendo i fragment 25 Portfolio/Broker e 20
> Asset/FX dopo parity validation completa. `ALL_FOUNDATION_COMPONENTS` resta
> soltanto baseline fail-closed immutabile per i test; nessun
> `FoundationComponentPayload` è presente nel registry production. I default
> Dataset/Analysis registry costruiscono 18/17 spec sul registry reale; gli
> integration context dei quattro domini usano il central registry, mantenendo
> dedup `all_data`, cache request-scoped, assenza deadlock/import-cycle e I/O
> singolo. Gate AI Export: 883 test passati; ruff/black verdi.

## 14. Step P5 — Public API v1

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

- selection `dataset|analysis`;
- periodo unico;
- scope domain-specific;
- manifest/envelopes;
- catalog separato;
- contract v1;
- problemi 403/404/409/422/503;
- no web flag;
- hard replacement, no fallback.

> **Note implementazione**: nuovo contratto pubblico v1 component-based in
> `ai_export_runtime.py`: selection discriminata `dataset|analysis`, periodo
> unico, scope per dominio, catalogo separato 18/17, manifest dataset, section
> envelope JSON-safe, contract identity frontend-owned e telemetria informativa.
> `runtime_service.py` costruisce `BuildScope`/`BucketPlan`, applica broker
> access fail-closed, compone dataset/analisi sul registry reale e gestisce
> applicability concreta (`no_position`, `insufficient_price_history`,
> `no_direct_exposure`). Endpoint `/api/v1/ai-export/snapshot` rifiuta il vecchio
> payload task/date_range/technical_window e mappa 403/404/409/422/503 con
> problemi discriminati. Gate: 111 schema, 14 API e 892 service test passati;
> ruff/black verdi.
>
> **⚠️ Fuori pista**: schema/service/assembler task-profile restano come oracle
> morto per i test legacy fino al cleanup post-feedback; nessun endpoint o
> runtime production li importa.

## 15. Step P6 — API sync

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

```text
./dev.py api sync
```

Verificare discriminatori, AREA/profile, cataloghi e Risk post-processing.

> **Note implementazione**: `./dev.py api sync` rigenera OpenAPI/client sul
> contratto v1 definitivo. Request domain e selection kind, target e problem
> code sono `z.literal` dentro union discriminate; `AiExportPeriod` espone
> start/end obbligatori; `broker_ids` è `number[]` opzionale senza union
> array-of-array. Client include catalogo 18/17, manifest/section response,
> AREA e `SignalAggregationProfile`; post-processor Risk conserva una sola
> union output discriminata, senza discriminator duplicati. Codegen completato
> senza errori.
>
> **⚠️ Fuori pista**: il primo import Vitest del client ha esposto anche
> `RiskScenarioCatalogEntry.kind` non literal e l'assenza di AREA/selection
> nell'elenco post-processato. Corretti schema Risk scenario e post-processor;
> il client generato ora importa senza crash.

## 16. Step P7 — Frontend Signal chart

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

- catalog/schema mapper;
- enum dispatcher;
- join bucket key;
- representative date metadata;
- AREA renderer;
- Drawdown MIN;
- BAND_ENVELOPE;
- events;
- local signal default esplicito.

> **Note implementazione**: mapper/catalogo trasportano kind AREA,
> `aggregationProfile` esplicito e fill opacity. Tutti i local
> comparison/benchmark/preview dichiarano `last_with_range`. Il downsampler
> condivide la mappa logica `bucketStart|bucketEnd` del prezzo, proietta sulla
> data renderizzata del bucket e conserva `representativeDate` reale; dispatcher
> FIRST/LAST/MIN/MAX e BAND_ENVELOPE senza switch su signal code. Drawdown usa
> MIN e non perde il trough settimanale/mensile; bande usano lower=min,
> middle=last, upper=max con ordering fail-closed. ECharts AREA è una line con
> fill `origin: 0`; tooltip mostra la data osservata quando differisce dalla
> coordinata. Fixture Python/TS condivisa consumata. Gate unit chart/signal:
> 91 test passati, nessun E2E.

## 17. Step P8 — Prompt/catalog/client frontend

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

- 17 instruction template;
- 17 response contract;
- sandbox + web search;
- Additional Data catalog-driven;
- safe YAML;
- technical dates `YYYY/MM/DD`;
- data-only/full prompt;
- mismatch fail-closed.

> **Note implementazione**: catalogo frontend ricostruito sul response backend
> 18 dataset/17 analisi; dataset validati per ID/version/detail, analisi
> abilitate solo se instruction e response contract locali v1 coincidono.
> Client tipizzato invia selection/periodo/scope nuovi e verifica request,
> response, catalog version e contract identity. Implementati 17 objective
> template e 17 response contract. Prompt analysis segue ordine 1–9,
> include sandbox/calculator e web-search instructions sempre, Additional Data
> dal catalogo reale, anti-injection, note e lingua; dataset produce data-only.
> Serializer YAML/fence esistente riusato; tutte le date ISO pure sono copiate
> `YYYY/MM/DD`. Gate AI Export + Signal: 119 unit test passati, nessun giudizio
> qualitativo e nessun E2E.

## 18. Step P9 — UI/clipboard quattro pagine

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

- Export Data / Request Analysis;
- 18 dataset/17 analisi per pagina;
- Compact/Standard/Full;
- 3M/6M/1Y/Custom;
- memory user/context/entity;
- notes solo analysis;
- token warning inline;
- Use Compact quando utile;
- Copy Anyway senza seconda request;
- clipboard;
- rename V2 senza alias;
- EN/IT/FR/ES.

> **Note implementazione**: introdotti i nomi definitivi `AiExportMenu.svelte` e
> `aiExportClipboard.ts`; menu categorizzato Export Data/Request Analysis, catalogo
> 18 dataset/17 analisi, detail e periodo unico 3M/6M/1Y/Custom, memoria v2 per
> utente/contesto/entità, note solo per analisi, warning inline e riuso del payload
> preparato per `Copy Anyway`. Dashboard, Broker, Asset e FX usano lo stesso client
> discriminato e lo stesso flusso clipboard. Aggiornate le traduzioni runtime
> EN/IT/FR/ES e rimossi import/chiavi/file V2 e task-catalog dal runtime.
>
> **⚠️ Fuori pista**: il crash dashboard segnalato proveniva da un bundle precedente
> in cui il fallback della memoria poteva fallire con catalogo vuoto. Il fallback
> corrente resta non distruttivo e il bundle statico è stato rigenerato.

## 19. Step P10 — Controlli oggettivi e stop

**Stato**: ✅ COMPLETATO — 29 luglio 2026.

Consentiti:

- backend unit/integration mirati;
- frontend unit aggregazione/renderer/AI Export/clipboard;
- API sync;
- type-check;
- build.

Vietati:

- test visuali/E2E;
- gallery/screenshot;
- giudizi qualità prompt;
- review manuale autonoma;
- cleanup;
- docs estese;
- wiki/graph.

> **Note implementazione**: gate backend corrente: 112 schema, 892 service e 14 API
> test passati. Gate frontend corrente: 130 unit AI Export/Signal passati,
> `svelte-check` 0 errori/0 warning, API sync e build production completati.
> Ruff è verde sui file backend modificati; Black è verde dopo la formattazione del
> test schema runtime. La ricerca runtime non trova riferimenti V2/task-hidden/web/
> technical-window rimasti nel nuovo frontend. Nessun E2E, screenshot, review
> qualitativa, cleanup, docs estese, wiki o graph eseguiti.
>
> **⚠️ Fuori pista**: l'audit i18n conferma 2139/2139 chiavi in ciascuna lingua e
> nessuna traduzione mancante, ma termina non-zero per 11 nuove chiavi backend-driven
> del lavoro Risk concorrente. Non sono state corrette dentro questo task AI Export.
>
> **⚠️ Bugfix post-handoff — 29 luglio 2026**: l'apertura del menu generava
> `effect_update_depth_exceeded`. `AiExportOptionsPanel` rileggeva il prop reattivo
> `initialOptions.responseLanguage`; il suo `ondraftchange` faceva ricreare quel prop
> nel parent, chiudendo un loop child→parent→child. La lingua è ora un prop separato e
> gli update draft semanticamente identici non riscrivono lo stato. Ripristinato anche
> il reposition su resize/scroll/resize del pannello. Smoke isolato reale: pannello
> portaled e ancorato a `(652,160)`, nessun page error, click esterno chiude.
>
> **⚠️ Bugfix post-handoff — 29 luglio 2026**: la severità
> `incomplete_warmup` è ora relativa alla finestra visibile. Shortfall warm-up
> almeno pari al 5% dei punti richiesti → `warning`; sotto il 5% → `notice`.
> Il caso reale 2/9292 diventa notice, mentre 2/7 resta warning. Gate aggiornato:
> 131 unit AI Export/Signal, type-check 0/0 e build production verdi.
>
> **⚠️ Follow-up UI — 30 luglio 2026**: ripristinate le icone nel selettore
> dataset/analisi. Il frontend usa direttamente `entry.icon` del catalogo backend,
> con mapping Lucide per i 18 nomi correnti e fallback `FileText`; l'icona è visibile
> sia nel valore selezionato sia in ogni opzione. Gate invariato: 131 unit,
> type-check 0/0 e build production verdi.
>
> **⚠️ Follow-up contenuti — 30 luglio 2026**: rinominata in italiano
> `portfolio.pac_planning` da “Piano di investimento ricorrente” a
> “Pianificazione PAC”. Creato
> [il report dei contenuti selezionabili](./report-phase00AiExportSelectableContentComposition.md)
> con struttura comune del prompt e composizione completa per pagina, dataset,
> analisi e componenti.

## 20. Handoff

Stop quando:

- backend objective gates verdi;
- API sync verde;
- frontend unit/type-check/build verdi;
- quattro pagine cablate;
- copy data-only/full prompt disponibile.

Consegna:

- pagine/URL da aprire;
- selection da provare;
- cosa copiare;
- punti qualitativi da valutare;
- problemi noti.

Attendere feedback utente.

## 21. Deferred post-feedback

- correzioni qualitative;
- docs complete;
- E2E/visual review;
- cleanup legacy;
- wiki ingest/lint;
- graph update;
- archiviazione/final validation.

## 22. Dipendenze

```text
P0
└── P1 backend contract
    ├── P2 plugin declarations/matrix
    └── P3 Python stats
        ├── P4 AI technical rows
        └── P5 registry/API
            └── P6 API sync
                ├── P7 chart
                └── P8 prompt/client
                    └── P9 UI/clipboard
                        └── P10 objective checks
                            └── STOP
```

P2/P3 parallelizzabili dopo P1.
P7/P8 parallelizzabili dopo API sync.

## 23. Regola avanzamento

Dopo ogni step:

1. stato + data;
2. `> **Note implementazione**: ...`;
3. `> **⚠️ Fuori pista**: ...`;
4. update README/todo immediato.
