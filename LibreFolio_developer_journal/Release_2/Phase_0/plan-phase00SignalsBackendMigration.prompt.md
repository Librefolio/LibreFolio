# Plan: Phase 0 — Migrazione Segnali al Backend

**Stato**: 📋 REVISIONATO — in attesa di validazione; implementazione non iniziata.

**Data revisione**: 22 Luglio 2026

## Contesto e fonti

- [Roadmap & Signals Brainstorm](../Ai_ideas/roadmap_and_signals_brainstorm.md)
- [Phase 0 Detailed Roadmap](../Ai_ideas/phase_0_detailed_roadmap.md)
- [AI Feature Decisions](../Ai_ideas/brainstorming_ai_features.md)
- [MCP Architecture Draft](../Ai_ideas/mcp_server_architecture_draft.md)
- [Simbiosi pandas-ta-classic + TA-Lib](./research-phase00PandasTaTalibSymbiosis.md)
- [Mappa delegazione pandas-ta → TA-Lib](./pandas-ta-talib-delegation.json)
- [Backend previsti per i segnali LibreFolio](./librefolio-signal-backends.json)
- [Analisi architetturale precedente](./analysis-phase00SignalsBackendArchitecture.md)
- [Ricerca librerie precedente](./research-phase00IndicatorLibrarySelection.md)

Le due analisi precedenti restano fonti storiche. In caso di conflitto, le decisioni
definitive contenute in questo piano prevalgono. In particolare, i dati tecnici della
ricerca sulla delegazione sono confermati, mentre la proposta di un adapter centrale
delle librerie è esplicitamente rifiutata.

## Obiettivo

Spostare i segnali tecnici dal frontend TypeScript a un sistema backend Python
plugin-centrico, riutilizzabile da:

- Asset;
- FX;
- AI Export;
- futuri consumer backend;
- futuri tool MCP.

Il frontend smette di eseguire i calcoli matematici dei segnali tecnici, ma continua a
possedere:

- stile;
- colori;
- ordine;
- visibilità;
- selezione;
- rendering;
- tooltip;
- trasformazioni di visualizzazione;
- configurazione session-local.

I risultati restano calcolati on demand. Non sono previste persistenza dei risultati o
migration DB.

## Scope

### Dentro Phase 0

- Nuovo `SignalService` indipendente da Asset, FX e librerie terze.
- Nuovo `SignalPluginRegistry` auto-discovered.
- Classe astratta `SignalPlugin` come unica astrazione comune.
- Adapter di dominio Asset e FX dentro le API esistenti.
- Input interno OHLCV-compatible più event points.
- FX adattato allo stesso formato, con solo `close` valorizzato.
- Stack production composito `pandas-ta-classic` + `TA-Lib`.
- Catalogo backend di 17 segnali.
- Cataloghi Asset e FX con disponibilità statica e dinamica.
- Frontend schema-driven per parametri e output standard.
- Cutover Asset e FX nello stesso ciclo.
- AI Export alimentato dai risultati backend.
- Test numerici e di delegazione per ogni plugin.

### Fuori scope

- Endpoint pubblico generico per calcolare segnali da array arbitrari.
- Persistenza di config o risultati.
- Migration Alembic.
- Cache frontend o backend dei risultati.
- Calcolo incrementale.
- Adapter centrale delle librerie.
- Manifest runtime delle dipendenze per plugin.
- `required_dependencies` o registry paralleli a Pipenv.
- Vincoli generali sugli import di `pandas-ta-classic` o `TA-Lib`.
- Benchmark sintetici `linear`, `compound`, `sine`.
- Comparison signal `fx-pair`, `asset-comparison`.
- Measure interattivo.
- Risk metrics, Monte Carlo, watchlist e rolling return.

## Principio architetturale fondamentale

`SignalPlugin` è l'unità completa e autonoma di implementazione di uno specifico
segnale.

Ogni plugin possiede integralmente:

- codice e versione del segnale;
- modello e validazione dei parametri;
- input richiesti;
- output prodotti;
- semantica di assi e unità;
- reference levels standard;
- minimum lookback;
- stabilization requirement;
- funzione di calcolo;
- libreria o algoritmo usato;
- normalizzazione nel formato canonico LibreFolio;
- errori specifici;
- test numerici;
- scelta del backend computazionale.

Il plugin può scegliere autonomamente:

- `pandas-ta-classic` con `talib=True`;
- `pandas-ta-classic` nativo;
- `TA-Lib` direttamente;
- una futura libreria;
- una formula LibreFolio.

La scelta è interna e versionata dal plugin. Non attraversa API, cataloghi pubblici o
frontend.

## Architettura target

```text
Asset / FX / AI Export / futuri consumer
                  │
                  ▼
            SignalService
                  │
                  ▼
       SignalPluginRegistry
                  │
                  ▼
        Singolo SignalPlugin
        ├─ contratto e metadata
        ├─ params model
        ├─ input requirements
        ├─ warm-up
        ├─ scelta implementazione
        ├─ calcolo
        ├─ errori specifici
        └─ output canonico
                  │
                  ├─ pandas-ta-classic → TA-Lib
                  ├─ pandas-ta-classic nativo
                  ├─ TA-Lib diretta
                  ├─ futura libreria
                  └─ formula LibreFolio
```

## Nessun adapter centrale delle librerie

Non creare `PandasTaAdapter`, `TechnicalAnalysisAdapter` o componenti equivalenti
incaricati di:

- conoscere le funzioni dei singoli indicatori;
- mappare signal code verso funzioni della libreria;
- scegliere il backend dei singoli indicatori;
- normalizzare output specifici;
- contenere switch centrali;
- esporre `compute_ema()`, `compute_rsi()`, `compute_macd()` o metodi analoghi.

Un simile adapter duplicherebbe la conoscenza dei plugin, aumenterebbe il coupling e
obbligherebbe ogni contributor a modificare un file centrale.

Helper condivisi sono ammessi solo quando emerge duplicazione reale e
library-independent. Esempi legittimi:

- conversione generica point-array → representation columnar/DataFrame;
- sanitizzazione generica di NaN/infinity;
- validazione generica dell'allineamento date;
- semplice fail-fast dell'ambiente production.

Gli helper non devono conoscere la mappa degli indicatori o decidere quale funzione
chiamare.

## Classe astratta comune

La classe astratta definisce soltanto il contratto generale:

```python
class SignalPlugin(ABC):
    signal_code: ClassVar[str]
    implementation_version: ClassVar[str]
    category: ClassVar[SignalCategory]
    display_name_key: ClassVar[str]
    icon: ClassVar[str]
    docs_path: ClassVar[str | None]
    params_model: ClassVar[type[BaseModel]]
    required_price_fields: ClassVar[frozenset[SignalPriceField]]
    output_specs: ClassVar[tuple[SignalOutputSpec, ...]]

    @classmethod
    @abstractmethod
    def warmup_requirement(
        cls,
        params: BaseModel,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        """Return minimum, stabilization and total required points."""

    @abstractmethod
    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: BaseModel,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        """Compute and normalize this signal using the plugin-owned implementation."""
```

La base class non importa e non conosce `pandas-ta-classic`, `TA-Lib` o altre librerie.

## Modelli input neutrali

```python
class SignalPricePoint(BaseModel):
    date: date
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal
    volume: Decimal | None = None
    backward_fill_info: BackwardFillInfo | None = None


class SignalEventPoint(BaseModel):
    date: date
    type: str
    value: Decimal | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
```

Asset adatta `FAPricePoint` e gli eventi esistenti.

FX adatta ogni effective rate come:

```python
SignalPricePoint(
    date=result.conversion_date,
    open=None,
    high=None,
    low=None,
    close=result.rate or Decimal("1"),
    volume=None,
    backward_fill_info=result.backward_fill_info,
)
```

Le conversioni identità usano `close=1`.

## Dipendenze e ambiente

LibreFolio continua a usare esclusivamente il normale sistema production:

- `Pipfile`;
- `Pipfile.lock`;
- Docker costruito dal lock;
- CI installata dal lock.

Lo stack target comprende entrambe:

- `pandas-ta-classic`;
- `TA-Lib`.

Le versioni analizzate sono `pandas-ta-classic==0.6.52` e `TA-Lib==0.7.1`; lo Step 0
deve confermare i pin definitivi nel contesto reale del progetto.

Non introdurre:

- `required_dependencies`;
- `frozenset` di package richiesti;
- manifest runtime per plugin;
- dependency registry;
- sistema di fallback applicativo parallelo a Pipenv.

Se un nuovo plugin richiede una libreria, il contributor modifica normalmente
`Pipfile` e `Pipfile.lock`.

L'assenza di una dipendenza prevista è un errore di installazione/deployment.

### Fail-fast anti fallback silenzioso

`pandas-ta-classic` usa il percorso nativo di default e, anche con `talib=True`, può
ripiegare silenziosamente se `TA-Lib` non è importabile.

Phase 0 deve introdurre un controllo semplice, non un adapter:

1. FastAPI startup/import verifica che entrambi i package siano importabili.
2. Verifica che `pandas_ta_classic.Imports["talib"] is True`.
3. Se il target stack è incompleto, startup/test fallisce con errore esplicito.
4. I 16 plugin delegabili passano `talib=True` nella propria chiamata.
5. I test verificano che il parametro sia realmente passato e che il percorso nativo
   non venga usato silenziosamente.

Il controllo può essere un piccolo helper comune perché rappresenta una reale policy
environment-wide. Non contiene mapping di segnali, backend registry o compute methods.

## Nessun vincolo artificiale sugli import

Non aggiungere test che vietino import di `pandas-ta-classic` o `TA-Lib` fuori da
`signal_plugins`.

Il vincolo corretto è sui contratti:

- nessun tipo terzo attraversa API o frontend;
- `SignalService`, Asset, FX e consumer pubblici usano solo modelli LibreFolio;
- ogni componente incapsula la libreria che usa;
- nessuna scelta di backend computazionale appare nei payload pubblici.

## Stack composito pandas-ta-classic + TA-Lib

Decisione production:

- `pandas-ta-classic` offre API pandas, catalogo, index alignment e normalizzazione;
- `TA-Lib` calcola in C gli indicatori supportati;
- `pandas-ta-classic` nativo copre indicatori non presenti in TA-Lib;
- ogni plugin governa esplicitamente la propria chiamata.

Per la release analizzata:

- 16 segnali approvati delegano tramite `talib=True`;
- Donchian usa l'implementazione nativa `pandas-ta-classic`;
- `talib=True` non è un parametro frontend;
- cambiare backend richiede bump di `implementation_version` e test regressivi.

## Catalogo target: 17 segnali

### Close-only: Asset + FX

| Segnale | Input | Output canonico | Backend previsto |
|---|---|---|---|
| EMA | close | line | pandas-ta-classic `ema(..., talib=True)` |
| SMA | close | line | pandas-ta-classic `sma(..., talib=True)` |
| RSI | close | line, bounds 0-100 | pandas-ta-classic `rsi(..., talib=True)` |
| MACD | close | MACD line + signal line + histogram | `macd(..., talib=True)` |
| Bollinger Bands | close | lower/middle/upper band | `bbands(..., talib=True)` |
| ROC | close | percentage line | `roc(..., talib=True)` |
| Stochastic RSI | close | `%K` + `%D` | `stochrsi(..., talib=True)` |
| KAMA | close | line | `kama(..., talib=True)` |
| PPO | close | PPO + signal + histogram | `ppo(..., talib=True)` |

### High/low oppure high/low/close: Asset

| Segnale | Input | Output canonico | Backend previsto |
|---|---|---|---|
| ATR | high, low, close | line | `atr(..., talib=True)` |
| ADX | high, low, close | ADX + `+DI` + `-DI` | `adx(..., talib=True)` |
| NATR | high, low, close | percentage line | `natr(..., talib=True)` |
| Aroon | high, low | Up + Down + Oscillator | `aroon(..., talib=True)` |
| Donchian Channels | high, low | lower/middle/upper band | `donchian(...)` nativo |
| CCI | high, low, close | line + reference levels standard | `cci(..., talib=True)` |

### Volume: Asset

| Segnale | Input | Output canonico | Backend previsto |
|---|---|---|---|
| OBV | close, volume | cumulative line | `obv(..., talib=True)` |
| MFI | high, low, close, volume | line, bounds 0-100 | `mfi(..., talib=True)` |

Non generare OHLCV sintetico per abilitare un segnale.

## Output canonici

Conservare i primitivi:

- `line`;
- `bar`;
- `band`;
- composite come insieme flat di più serie.

Esempi:

- MACD: MACD line, signal line, histogram;
- StochRSI: `%K`, `%D`;
- ADX: ADX, `+DI`, `-DI`;
- Aroon: Up, Down, Oscillator;
- Bollinger: lower, middle, upper;
- Donchian: lower, middle, upper;
- PPO: PPO, signal, histogram.

Ogni risultato include:

- signal instance ID;
- signal code;
- implementation version;
- params normalizzati;
- status `ok|partial|unavailable|failed`;
- serie canoniche;
- warnings/errori strutturati;
- warm-up metadata;
- annotations standard opzionali.

Ogni serie dichiara:

- key e i18n key;
- kind;
- unit;
- axis role;
- axis bounds opzionali;
- reference levels opzionali;
- view transform.

Nessuno stile grafico proviene dal backend.

## Registry

Il registry auto-discovered rimane coerente con il pattern provider:

1. estrarre, se utile e senza rompere i provider, le meccaniche comuni in
   `AbstractPluginRegistry`;
2. conservare `AbstractProviderRegistry` come compatibilità;
3. non cambiare `@register_provider(...)`;
4. aggiungere `SignalPluginRegistry`;
5. aggiungere `@register_plugin(...)`;
6. auto-discover `backend/app/services/signal_plugins/*.py`;
7. rifiutare signal code duplicati;
8. rendere espliciti discovery/import error.

Il registry conosce classi e metadata. Non conosce funzioni `pandas-ta-classic`, flag
`talib`, dipendenze o mapping backend.

## Backend autorità sulla disponibilità

Endpoint:

- `GET /api/v1/assets/prices/signals`
- `GET /api/v1/fx/currencies/signals`

Il catalogo comunica almeno:

- codice/versione;
- i18n keys;
- docs;
- schema parametri;
- input richiesti;
- output specs;
- unità/assi/reference levels;
- compatibilità dominio.

### Disponibilità statica

Indica se il dominio può fornire in generale gli input richiesti:

- FX: solo segnali close-only;
- Asset: close-only, OHLC e volume secondo capability dichiarate.

### Disponibilità dinamica

Indica se, per uno specifico asset/pair/range:

- i campi richiesti sono presenti con copertura sufficiente;
- la storia disponibile copre minimum + stabilization points;
- il segnale può essere calcolato.

I cataloghi accettano contesto opzionale:

```text
GET /assets/prices/signals?asset_id=...&start=...&end=...&target_currency=...
GET /fx/currencies/signals?base=...&quote=...&start=...&end=...
```

Senza contesto restituiscono definizioni e compatibilità statica.

Con contesto aggiungono:

- `availability`;
- `missing_fields`;
- `available_points`;
- `required_points`;
- `reason_code`;
- warning di warm-up.

Il frontend usa questi dati per disabilitare o limitare preventivamente le opzioni.
Le API di calcolo ripetono sempre la validazione: il backend resta autorità finale.

## Frontend schema-driven

Il frontend non aggiunge codice per ogni nuovo indicatore se parametri e output sono
esprimibili nei primitivi supportati.

### Fonte dello schema

Ogni plugin definisce un Pydantic `params_model`.

Il catalogo espone:

- `params_model.model_json_schema()`;
- metadata UI standard in `json_schema_extra`, per esempio:
  - `x-i18n-key`;
  - `x-control-order`;
  - `x-suffix`;
  - `x-step`;
  - `x-tooltip-key`.

### Mapping JSON Schema → controlli

Il frontend applica una trasformazione generica:

| JSON Schema | Controllo |
|---|---|
| `integer` / `number` | number input con default, minimum, maximum, multipleOf/step |
| `boolean` | toggle |
| `enum` string/number | select |
| field in `required` | controllo obbligatorio |
| metadata `x-*` | label, ordine, suffix, tooltip |

Tipi non supportati non ricevono fallback silenzioso: il catalog entry viene segnalato
come non renderizzabile finché viene aggiunto un nuovo primitivo UI.

### Runtime

Il frontend:

- carica catalogo e disponibilità;
- costruisce `SignalDefinition` generiche;
- genera i controlli;
- conserva `SignalConfig` session-local;
- invia code, instance ID e params;
- riceve contratti canonici;
- renderizza line/bar/band e serie composite;
- applica stile, ordine, visibilità e view transform;
- conserva config diventate temporaneamente unavailable, mostrandole disabilitate con
  motivazione invece di cancellarle.

Codice specifico frontend serve solo per un futuro tipo di parametro o visualizzazione
non rappresentabile dai primitivi esistenti.

## `SignalService`

`SignalService` è indipendente dalle librerie e dai singoli indicatori.

Deve:

1. risolvere plugin dal registry;
2. validare params tramite il plugin;
3. deduplicare signal code + params;
4. chiedere warm-up a ogni plugin;
5. determinare il massimo richiesto;
6. richiedere un solo range esteso;
7. costruire una representation columnar/DataFrame condivisa quando utile;
8. validare copertura input;
9. eseguire i plugin;
10. isolare errori per segnale;
11. sanitizzare NaN/infinity;
12. validare date, cardinalità e output specs;
13. effettuare slicing sul range richiesto;
14. restituire solo modelli LibreFolio.

Non deve:

- scegliere librerie;
- decidere `talib=True`;
- conoscere nomi funzione;
- normalizzare colonne specifiche di EMA/MACD/altro;
- contenere switch per signal code;
- applicare fallback tra backend computazionali.

## Warm-up

Ogni plugin dichiara:

- `minimum_points`;
- `stabilization_points`;
- `total_points`.

`SignalService` usa il massimo, carica un solo intervallo esteso, calcola e taglia sul
range visibile.

Non fissare nel piano come fatti:

- `3.5 × length`;
- `4 × length`;
- tolleranza universale `1e-6`.

Sono ipotesi da validare nello Step 0.

### Metodo di validazione

Per ogni indicatore ricorsivo:

1. calcolare il riferimento TA-Lib con storia lunga;
2. calcolare lo stesso indicatore con warm-up limitato crescente;
3. confrontare solo il range visibile;
4. trovare il minimo warm-up che mantiene l'errore entro una tolleranza documentata;
5. ripetere su serie flat, trend, volatile, gap e più scale di prezzo;
6. registrare formula e tolleranza nel plugin/test.

Per i 16 plugin configurati `talib=True`, il riferimento production è TA-Lib.
Il percorso nativo `pandas-ta-classic` serve a comprendere differenze e fallback, non a
definire il risultato production.

## Cache

Nessuna cache viene progettata o implementata in Phase 0.

L'architettura resta stateless e compatibile con un futuro layer cache, ma chiavi,
invalidazione, fingerprint e calcolo incrementale richiedono benchmark reali e un piano
separato.

## Arricchimento API Asset

```python
FAPriceQueryItem.signals: list[FASignalRequest] = []
FAPriceQueryResult.signals: list[FASignalResult] = []
```

Pipeline:

1. validazione request/plugin/params;
2. availability statica e dinamica;
3. warm-up massimo;
4. range esteso;
5. bulk DB load;
6. backward fill secondo data policy;
7. eventi richiesti;
8. target-currency conversion;
9. mapping neutro;
10. compute;
11. slicing;
12. response.

Il comportamento senza `signals` resta backward-compatible.

## Arricchimento API FX

`FXConversionRequest` riceve `signals` opzionali.

`FXConversionResult` daily resta invariato.

```python
FXConvertResponse.signal_results: list[FXSignalQueryResult] = []
```

Ogni gruppo contiene:

- original request index;
- base/quote;
- range richiesto;
- risultati completi.

Pipeline:

1. validazione close-only;
2. warm-up massimo;
3. conversione amount 1 sul range esteso;
4. mapping rate → `close`;
5. compute;
6. slicing;
7. daily conversion result invariati + signal results aggregati.

## AI Export

- Richiede EMA20/50/200, RSI14 e MACD dalle API arricchite.
- Conserva la data policy observed-only.
- Consuma annotations/cross/threshold prodotte da primitive backend condivise.
- Conserva sampling, limiti, metadata e formato payload salvo versionamento esplicito.
- Rimuove import diretti delle classi tecniche TypeScript dopo parity snapshot.

## Step 0 — Validazione stack composito, ambiente e warm-up

**Stato**: ⏳

1. Aggiungere temporaneamente nello spike entrambe le dipendenze tramite Pipenv.
2. Validare i pin candidati e produrre `Pipfile.lock`.
3. Verificare `pipenv sync --deploy`/CI dal lock.
4. Verificare Docker `python:3.13-slim`.
5. Verificare Linux amd64 e arm64.
6. Confermare installazione da wheel, senza fallback inatteso a build sorgente.
7. Eseguire tutti i 17 segnali.
8. Confermare `talib=True` per i 16 delegabili.
9. Confermare Donchian nativo.
10. Verificare fail-fast con TA-Lib assente/non rilevata.
11. Verificare output, index/date alignment, NaN, gap, serie corte e campi mancanti.
12. Eseguire sweep warm-up contro riferimento TA-Lib long-history.
13. Misurare differenze native vs TA-Lib senza assumerne la convergenza.
14. Misurare prestazioni batch.
15. Verificare comportamento concorrente e stabilità, senza assumere GIL release o
    thread safety.
16. Misurare delta dimensione immagine.
17. Salvare risultati in un artefatto Phase 0.
18. Fissare i pin production di entrambe le librerie.

Non usare come acceptance threshold fatti non misurati: speed-up 5–20x, overhead
10–20µs, build <15s, thread safety completa, warm-up 3.5x/4x.

**Accettazione**:

- entrambe le dipendenze nel lock production;
- wheel/install validati sulle architetture disponibili;
- 17 segnali invocabili;
- 16 delegation path verificati;
- Donchian native path verificato;
- silent fallback trasformato in errore evidente;
- warm-up/tolleranza documentati per plugin;
- execution/concurrency policy basata sulle misure.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 1 — Contratti, base class e registry

**Stato**: ⏳

Creare:

- `backend/app/schemas/signals.py`;
- `backend/app/services/signal_plugins/base.py`;
- `backend/app/services/signal_plugins/__init__.py`.

Definire:

- neutral price/event points;
- request/result/catalog schemas;
- line/bar/band outputs;
- flat composite series;
- params JSON Schema metadata;
- input requirements;
- axes/units/reference levels;
- warm-up metadata;
- availability static/dynamic;
- error model.

Integrare `SignalPluginRegistry` con auto-discovery, duplicate detection e import error
espliciti, senza introdurre mapping di librerie.

**Accettazione**:

- provider registry esistenti invariati;
- un plugin fixture si registra da un file;
- base class library-agnostic;
- nessun tipo terzo nei contratti;
- catalogo serializzabile e schema-driven.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 2 — `SignalService` e availability engine

**Stato**: ⏳

Creare `backend/app/services/signal_service.py`.

Implementare:

- plugin/params resolution;
- dedup;
- warm-up aggregation;
- range extension contract;
- shared columnar/DataFrame preparation;
- field/history coverage;
- static/dynamic availability;
- plugin execution;
- per-signal error isolation;
- NaN/infinity sanitization;
- output/date validation;
- slicing;
- cross/threshold primitives library-independent.

Non aggiungere adapter o cache.

**Accettazione**:

- test service senza DB/HTTP;
- equivalent close arrays Asset/FX producono gli stessi output;
- failure isolata;
- nessuna scelta libreria nel service;
- availability ricalcolata anche al compute.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 3 — Plugin tecnici esistenti

**Stato**: ⏳

Creare:

- `ema.py`;
- `rsi.py`;
- `macd.py`;
- `bollinger.py`.

Ogni plugin:

- possiede params/warm-up/call/normalizzazione/errori;
- passa `talib=True`;
- mappa output canonici;
- include test numerici e delegation-path.

**Accettazione**:

- fixture flat/trend/volatile/gap/short;
- warm-up misurato;
- backend TA-Lib verificato;
- MACD 2 line + histogram;
- Bollinger band;
- nessun calcolo TypeScript modificato prima del cutover.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 4 — Plugin close-only aggiuntivi

**Stato**: ⏳

Creare:

- `sma.py`;
- `roc.py`;
- `stoch_rsi.py`;
- `kama.py`;
- `ppo.py`.

Tutti disponibili per Asset e FX, con `talib=True`.

**Accettazione**:

- catalogo close-only totale: 9;
- output composite StochRSI/PPO validati;
- params e reference levels schema-driven;
- delegation path verificato.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 5 — Plugin OHLC

**Stato**: ⏳

Creare:

- `atr.py`;
- `adx.py`;
- `natr.py`;
- `aroon.py`;
- `donchian.py`;
- `cci.py`.

Regole:

- ATR/ADX/NATR/CCI: high+low+close;
- Aroon/Donchian: high+low;
- 5 plugin delegano con `talib=True`;
- Donchian usa il percorso nativo `pandas-ta-classic`;
- nessun OHLC sintetico.

**Accettazione**:

- ADX, Aroon e Donchian multi-output validati;
- Donchian native path verificato;
- input mancanti = unavailable;
- warm-up e date validati.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 6 — Plugin volume

**Stato**: ⏳

Creare:

- `obv.py`;
- `mfi.py`.

Regole:

- OBV: close+volume;
- MFI: high+low+close+volume;
- entrambi `talib=True`;
- nessun volume sintetico.

**Accettazione**:

- missing/partial volume coverage esplicita;
- delegation path verificato;
- output e warm-up validati.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 7 — Catalogo e API Asset

**Stato**: ⏳

Modificare:

- `backend/app/schemas/prices.py`;
- `backend/app/api/v1/assets.py`;
- `backend/app/services/asset_source.py`.

Aggiungere:

- `signals` opzionali a query/result;
- catalog endpoint Asset;
- context-aware dynamic availability;
- range esteso unico;
- mapping neutro;
- compute/slicing.

**Accettazione**:

- catalogo 17 segnali con static/dynamic availability;
- client senza signals invariati;
- target-currency signals calcolati sui valori mostrati;
- backend revalida disponibilità al compute.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 8 — Catalogo e API FX

**Stato**: ⏳

Modificare:

- `backend/app/schemas/fx.py`;
- `backend/app/api/v1/fx.py`;
- `backend/app/services/fx.py`.

Aggiungere:

- `signals` opzionali a `FXConversionRequest`;
- `signal_results` aggregati;
- catalog endpoint FX;
- context-aware history availability;
- adapter rate → close.

**Accettazione**:

- catalogo FX limitato ai 9 close-only;
- daily conversion contract invariato;
- niente array duplicati per giorno;
- parity con Asset su input close equivalente.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 9 — API sync e frontend schema-driven

**Stato**: ⏳

Eseguire `./dev.py api sync`.

Refactor:

- `SignalDefinition` separata dai constructor locali;
- catalog store Asset/FX;
- parser JSON Schema → number/boolean/enum controls;
- supporto metadata `x-*`;
- renderer canonico line/bar/band/composite;
- axis/unit/reference-level mapping;
- availability state;
- conservazione `SignalConfig` e style session-local.

**Accettazione**:

- nessun codice TS per singolo nuovo plugin standard;
- selettori visualmente coerenti;
- schema non supportato = errore esplicito;
- unavailable config conservata e spiegata;
- backend resta autorità finale.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 10 — Cutover UI Asset + FX

**Stato**: ⏳

- una POST bulk per range e segnali selezionati;
- refetch su range/params;
- result keyed by instance ID;
- style/view transforms frontend;
- warning/error/availability visibili;
- benchmark/comparison/Measure locali invariati.

**Accettazione**:

- 17 segnali renderizzabili secondo capability;
- 9 close-only su FX;
- line/bar/band/composite corretti;
- assi, levels, tooltip, dark mode e responsive verificati;
- nessun calcolo tecnico TS usato in production.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 11 — AI Export

**Stato**: ⏳

- richiedere EMA20/50/200, RSI14 e MACD dal backend;
- conservare observed-only policy;
- consumare annotations backend;
- conservare sampling, limiti, metadata e payload;
- rimuovere import tecnici TS.

**Accettazione**:

- indicatori e cross/threshold backend;
- output stabile;
- unavailable reason esplicita;
- nessun calcolo duplicato frontend.

> **Note implementazione**: da compilare immediatamente al completamento.

## Step 12 — Cleanup, documentazione e knowledge layer

**Stato**: ⏳

- rimuovere classi/calcoli TS tecnici obsoleti;
- aggiornare frontend signal instructions;
- aggiungere backend signal instructions;
- aggiornare MkDocs plugin guide, indicatori e AI Export;
- documentare stack composito e fail-fast;
- documentare frontend JSON Schema mapping;
- `./dev.py graph update`;
- archiviare decisioni nel devWiki.

Non aggiungere cache.

**Accettazione**:

- search non trova calcoli tecnici TS production;
- nuovo plugin standard = file Python + i18n/docs, senza modifica a adapter centrali;
- docs complete su input/output/warm-up/backend previsto/test;
- nessun documento descrive la cache come parte di Phase 0.

> **Note implementazione**: da compilare immediatamente al completamento.

## Test richiesti per ogni plugin

- parametri validi e invalidi;
- input completi;
- input richiesti mancanti;
- copertura campi parziale;
- serie piatta;
- trend;
- volatilità;
- serie corta;
- gap e NaN;
- warm-up completo;
- warm-up incompleto;
- date/output alignment;
- NaN/infinity sanitization;
- contratto canonico;
- regression fixture numerica;
- errore specifico;
- backend computazionale previsto.

Per i 16 plugin `talib=True`:

- spy/mock della chiamata per verificare `talib=True`;
- test fail-fast con TA-Lib non disponibile;
- prova che il fallback nativo non passi inosservato.

Per Donchian:

- test esplicito del percorso nativo;
- nessuna dipendenza da TA-Lib per il calcolo;
- stesso contratto canonico degli altri band plugin.

## Validazione integrata

### Backend

- registry/discovery;
- schema/catalog;
- startup fail-fast;
- 17 plugin;
- availability statica/dinamica;
- Asset/FX no-signal backward compatibility;
- target-currency parity;
- equivalent close-series parity;
- error isolation;
- Python 3.13;
- Pipenv lock;
- Docker amd64/arm64 disponibile;
- concurrency behavior misurato.

### Frontend

- JSON Schema mapper;
- number/boolean/enum controls;
- catalog merge;
- availability UI;
- line/bar/band/composite;
- axes/units/reference levels;
- payload Asset/FX;
- AI Export;
- E2E mirati;
- verifica visuale manuale.

## Dipendenze tra step

- Step 0 blocca plugin production e definisce warm-up/concurrency.
- Step 1 blocca service, plugin e API.
- Step 2 blocca adapter e cutover.
- Step 3 blocca il cutover dei segnali già esistenti.
- Step 4-6 possono procedere in parallelo dopo Step 1-2.
- Step 7 e 8 possono procedere in parallelo dopo Step 2-3.
- Step 9 attende cataloghi e contratti API.
- Step 10 attende Step 3-9.
- Step 11 attende backend signals + API client.
- Step 12 attende cutover e AI Export validati.

## Regola progress tracking

Dopo ogni step:

1. segnare ✅ con data;
2. aggiungere `> **Note implementazione**: ...`;
3. aggiungere `> **⚠️ Fuori pista**: ...` per detour o scoperte;
4. aggiornare subito gli step dipendenti;
5. non rimandare gli aggiornamenti alla fine del piano.

## Decisioni sostituite

- **Scelta di una sola libreria** → sostituita dallo stack composito
  `pandas-ta-classic + TA-Lib`.
- **Adapter centrale delle librerie** → rifiutato; ogni plugin possiede integralmente la
  propria implementazione.
- **Manifest `required_dependencies`** → rifiutato; dipendenze gestite da
  `Pipfile`/`Pipfile.lock`.
- **Vincoli generali sugli import** → rifiutati; il vincolo riguarda l'assenza di leakage
  nei contratti pubblici.
- **Cache in Phase 0** → rinviata a un piano successivo basato su benchmark.

→ Follow-up implementativo: da creare solo dopo validazione esplicita di questa revisione.
