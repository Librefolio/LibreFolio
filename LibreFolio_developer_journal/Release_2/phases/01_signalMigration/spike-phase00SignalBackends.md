# Phase 0 — Spike stack segnali `pandas-ta-classic + TA-Lib`

**Stato**: ✅ completato il 22 Luglio 2026

**Piani di riferimento**:

- [plan-phase00SignalsBackendMigration.prompt.md](./plan-phase00SignalsBackendMigration.prompt.md)
- [plan-phase00SignalsBackendMigrationImplementation.prompt.md](./plan-phase00SignalsBackendMigrationImplementation.prompt.md)

**Harness riproducibile**:

- `scripts/spikes/signals/run_signal_backend_spike.py`
- `backend/test_scripts/fixtures/signals/backend_spike_datasets.json`

## 1. Verdetto

Lo stack composito è adottabile:

- `pandas-ta-classic==0.6.52`;
- `TA-Lib==0.7.1`;
- Python `3.13`;
- NumPy `2.5.0`;
- pandas `3.0.3`.

I pin sono nel normale `Pipfile`/`Pipfile.lock`. Il lock conserva tutte le
versioni precedenti e aggiunge soltanto:

- `pandas-ta-classic`;
- `TA-Lib`;
- `build`;
- `pyproject-hooks`.

Un ambiente Pipenv pulito creato dal lock importa entrambe le librerie e rileva
`pandas_ta_classic.Imports["talib"] == True`.

## 2. Risultati dei gate

| Gate | Risultato |
|---|---|
| Python 3.13 macOS arm64 | ✅ |
| `python:3.13-slim` Linux arm64 | ✅ |
| `python:3.13-slim` Linux amd64 | ✅ |
| Wheel cp313 macOS arm64 | ✅ |
| Wheel cp313 manylinux arm64 | ✅ |
| Wheel cp313 manylinux amd64 | ✅ |
| Lock Pipenv pulito | ✅ |
| 17 indicatori invocabili | ✅ |
| 16 path TA-Lib osservati | ✅ |
| Donchian nativo | ✅ |
| Fallback silenzioso riprodotto | ✅ |
| Fail-fast probe | ✅ |
| Output/index alignment | ✅ |
| Fixture cross-platform | ✅ |
| Batch/performance | ✅ |
| Concorrenza/stabilità | ✅ |
| Avvio app macOS test | ✅ |
| Avvio immagine Docker release-equivalent | ✅ |

## 3. Evidenza backend effettivo

Il harness sostituisce temporaneamente le funzioni del modulo `talib` con wrapper
contatori. Ogni chiamata usa esplicitamente `talib=True`; una chiamata separata
con `talib=False` e una senza parametro verificano che nessuna funzione C venga
invocata.

| Segnale | Chiamate TA-Lib osservate |
|---|---|
| EMA | `EMA` |
| SMA | `SMA` |
| RSI | `RSI` |
| MACD | `MACD` |
| Bollinger | `BBANDS` |
| ROC | `ROC` |
| StochRSI | `STOCHRSI` |
| KAMA | `KAMA` |
| PPO | `PPO` |
| ATR | `ATR` |
| ADX | `ADX`, `MINUS_DI`, `PLUS_DI` |
| NATR | `NATR` |
| Aroon | `AROON`, `AROONOSC` |
| Donchian | nessuna; path nativo |
| CCI | `CCI` |
| OBV | `OBV` |
| MFI | `MFI` |

Il codice installato conferma che il default reale è nativo:

```python
mode_talib = bool(talib) if isinstance(talib, bool) else False
```

La documentazione PyPI della stessa release descrive invece un default
automatico. Per LibreFolio prevalgono codice installato e prova runtime:
`talib=True` resta obbligatorio nei plugin delegati.

## 4. Fallback silenzioso e fail-fast

Impostando temporaneamente `Imports["talib"] = False`, una chiamata EMA con
`talib=True`:

- non solleva errore;
- produce output;
- produce lo stesso fingerprint del path nativo.

Quindi il fallback silenzioso è confermato. Il probe fail-fast:

```text
TA-Lib is required for delegated LibreFolio signal plugins
```

lo trasforma correttamente in errore evidente. Il controllo production verrà
integrato in A3, senza adapter o dependency registry.

## 5. Fixture

Le fixture coprono:

- flat;
- trend;
- volatile;
- scala prezzo `0.001`;
- scala prezzo `1_000_000`;
- date mancanti;
- NaN su close;
- NaN su high/low/close;
- NaN su volume;
- serie corta.

La prima versione usava PCG64 e funzioni trigonometriche NumPy. Il confronto
Linux/macOS ha rilevato differenze agli ultimi bit. È stata sostituita con
`librefolio-lcg-v1`, LCG e onda triangolare pure Python. I dieci fingerprint
sono ora identici su macOS arm64, Linux arm64 e Linux amd64.

## 6. Warm-up candidate

Metodo:

1. riferimento TA-Lib su 4096 punti;
2. finestra visibile di 128 punti;
3. storico precedente crescente;
4. confronto su trend, volatile, scala bassa e scala alta;
5. errore massimo normalizzato sulla scala dell'output;
6. stesso risultato dei punti-candidato su tutte le piattaforme testate.

La tolleranza candidate production è `1e-6` normalizzata. `1e-8` resta misura
strict per i test numerici. I valori sono riferiti ai parametri default dello
spike: ogni plugin dovrà produrre una formula parameter-aware e rivalidarla.

`minimum_points` è la serie standalone più corta con ultima riga completa.
`measured history` sono i punti precedenti richiesti per l'intera finestra
visibile. Per il contratto conservativo:

```text
total_points = max(minimum_points, measured_history_1e-6)
stabilization_points = total_points - minimum_points
```

| Segnale | `minimum_points` | History misurata `1e-6` | `stabilization_points` candidate | `total_points` candidate | History strict `1e-8` |
|---|---:|---:|---:|---:|---:|
| ADX | 28 | 192 | 164 | 192 | 264 |
| Aroon | 15 | 14 | 0 | 15 | 14 |
| ATR | 15 | 136 | 121 | 136 | 196 |
| Bollinger | 20 | 19 | 0 | 20 | 19 |
| CCI | 14 | 13 | 0 | 14 | 13 |
| Donchian | 20 | 19 | 0 | 20 | 19 |
| EMA | 20 | 100 | 80 | 100 | 144 |
| KAMA | 30 | 28 | 0 | 30 | 50 |
| MACD | 34 | 200 | 166 | 200 | 248 |
| MFI | 15 | 14 | 0 | 15 | 14 |
| NATR | 15 | 124 | 109 | 124 | 196 |
| OBV | 1 | 0 | 0 | 1 | 0 |
| PPO | 34 | 76 | 42 | 76 | 96 |
| ROC | 13 | 12 | 0 | 13 | 12 |
| RSI | 15 | 164 | 149 | 164 | 216 |
| SMA | 20 | 19 | 0 | 20 | 19 |
| StochRSI | 30 | 192 | 162 | 192 | 216 |

### OBV

L'OBV assoluto non converge con storico limitato: il livello è una somma
cumulativa dipendente dall'origine della serie. La forma del segnale converge
esattamente se viene ribasata a zero alla prima data visibile.

Decisione candidate per il plugin OBV:

- calcolare sul range esteso;
- sottrarre il valore alla `requested_start`;
- restituire OBV ribasato;
- dichiarare questa semantica nel catalogo.

Nessun caricamento di tutta la storia è necessario.

## 7. Differenze native vs TA-Lib

Dopo storico lungo, 15 indicatori hanno errore normalizzato inferiore a `1e-8`.
Due differiscono materialmente:

| Segnale | Errore massimo normalizzato | Causa |
|---|---:|---|
| NATR | `0.0511` | path nativo costruito da ATR con smoothing diverso dal riferimento TA-Lib |
| StochRSI | `0.5626` | pipeline e smoothing nativi diversi dalla funzione TA-Lib |

Conseguenze:

- nessun fallback production è accettabile;
- TA-Lib è il riferimento numerico dei plugin delegati;
- i golden test non devono usare il path nativo come oracle.

### Parametri StochRSI

Il path `pandas-ta-classic` delegato usa:

```python
STOCHRSI(
    close,
    timeperiod=length,
    fastk_period=length,
    fastd_period=d,
)
```

`rsi_length`, `k` e `mamode` non governano quel ramo come nel path nativo.
Il plugin non deve esporre parametri ignorati. B2 dovrà:

1. limitare lo schema ai parametri realmente effettivi; oppure
2. usare direttamente TA-Lib/comporre la pipeline nel plugin.

La scelta resta interna al plugin, coerente con l'architettura approvata.

### PPO

La linea PPO usa `talib.PPO`; signal line e histogram vengono completati dalla
pipeline pandas-ta-classic. Il plugin dovrà verificare numericamente l'intero
composite, non soltanto la chiamata C principale.

## 8. Gap, NaN, serie corte e campi mancanti

- Un gap di date senza NaN preserva indice e cardinalità.
- Un NaN interno tronca fino a fine serie molti path TA-Lib: EMA, SMA, RSI,
  MACD, Bollinger, KAMA, ATR, ADX, NATR, MFI e OBV.
- PPO e StochRSI possono produrre colonne con recovery diverso nello stesso
  composite.
- I 31 probe con campo obbligatorio `None` restituiscono `None`, senza errore.
- La fixture corta da 10 punti restituisce `None` per i segnali non calcolabili.
- PPO, tra 26 e 33 punti, può sollevare
  `IndexError: iloc cannot enlarge its target object`.

Decisione:

- SignalService valida campi, coverage e minimum history prima di `compute`;
- i plugin non ricevono serie compattate;
- Phase 0 usa policy strict/contiguous;
- gap/NaN non recuperabili diventano `partial` o `unavailable` secondo il
  contratto A2, non eccezioni lasciate alla libreria.

## 9. Prestazioni e concorrenza

Benchmark: 50 asset, 1825 punti, 17 segnali per asset, tre round. Il test amd64
è eseguito via QEMU su host arm64, quindi il tempo assoluto non rappresenta un
host amd64 nativo; speed-up e stabilità restano utili.

| Runtime | TA-Lib median | Native median | Speed-up | 1 worker | 2 worker | 4 worker | 8 worker |
|---|---:|---:|---:|---:|---:|---:|---:|
| macOS arm64 | 0.2608s | 1.5103s | 5.79x | 0.2594s | 0.3125s | 0.3673s | 0.5160s |
| Linux arm64 | 0.3077s | 1.6819s | 5.47x | 0.3224s | 0.4459s | 0.5627s | 0.7776s |
| Linux amd64 (QEMU) | 0.5609s | 3.0417s | 5.42x | 0.5893s | 0.7166s | 0.8589s | 1.0800s |

Tutti i digest sono stabili in ogni round e numero di worker. Il fan-out thread
interno peggiora il throughput su ogni runtime.

Policy candidate:

- un singolo batch sincrono per request/item;
- esecuzione del batch con `asyncio.to_thread`;
- nessun parallelismo tra plugin dello stesso batch;
- limite iniziale di un signal batch concorrente per processo;
- rivalutazione su hardware server reale prima di aumentare il limite.

Lo spike non dimostra un rilascio GIL utile né thread scaling positivo.

## 10. Packaging e immagine

Wheel scaricate con `--only-binary=:all:`:

| Piattaforma | `pandas-ta-classic` | `TA-Lib` |
|---|---:|---:|
| macOS arm64 cp313 | 396,905 B | 1,118,848 B |
| Linux arm64 cp313 | 396,905 B | 1,325,030 B |
| Linux amd64 cp313 | 396,905 B | 1,451,665 B |

Delta immagine isolato, partendo dal precedente lock production:

| Immagine | Dimensione |
|---|---:|
| baseline | 988,358,407 B |
| baseline + stack segnali | 1,000,771,877 B |
| delta | 12,413,470 B (~11.84 MiB) |

La full image release-equivalent con UID/GID default `1000:1000`:

- importa lo stack;
- completa startup e migration su data dir pulita;
- risponde `200 {"status":"ok"}` a `/api/v1/system/health`.

Anche `./dev.py server --test` su macOS arm64 completa startup e health check.

## 11. Fuori pista rilevati

### Docker build locale con GID macOS 20

`./dev.py docker build` passa sempre UID/GID host
(`dev.py:1434-1435`). Su macOS il GID `20` esiste già come `dialout` nella
base Debian:

- `groupadd -g 20 librefolio` fallisce ma viene ignorato
  (`Dockerfile:65`);
- l'utente viene creato con gruppo `dialout` (`Dockerfile:66`);
- l'entrypoint tenta `chown librefolio:librefolio`
  (`entrypoint.sh:25`) e il container non parte.

Il problema precede questa migrazione e non è stato corretto fuori scope. Il
runtime release/CI, che usa i default Dockerfile `1000:1000`, è stato costruito
e avviato con successo.

### `pip check` baseline

`pip check` segnala conflitti già presenti fra dipendenze dev/transitive
(`protobuf`, `packaging`, `websockets`, `markdown-it-py`). Nessun conflitto
coinvolge le quattro nuove entry del lock. Non sono stati modificati in questo
task.

## 12. Decisioni che entrano negli step successivi

1. A2 deve congelare in modo non ambiguo il significato di
   `minimum_points`, `stabilization_points` e `total_points`.
2. I valori sopra sono candidate per i parametri default, non formule finali.
3. OBV viene ribasato alla prima data visibile.
4. StochRSI non espone parametri ignorati dal backend scelto.
5. NATR e StochRSI usano TA-Lib come oracle, mai il path nativo.
6. Prevalidazione input obbligatoria prima di chiamare pandas-ta-classic.
7. Policy gap iniziale strict/contiguous.
8. Un solo batch per worker thread; nessun fan-out plugin.
9. A3 integra un fail-fast semplice, non un adapter.

## 13. Riproduzione

```bash
pipenv run python scripts/spikes/signals/run_signal_backend_spike.py \
  --output /tmp/libreFolio_signal_backend_spike.json
```

Il report JSON raw non è versionato perché include timing host-specific. Harness,
manifest e fingerprint sono versionati e permettono di rigenerarlo.
