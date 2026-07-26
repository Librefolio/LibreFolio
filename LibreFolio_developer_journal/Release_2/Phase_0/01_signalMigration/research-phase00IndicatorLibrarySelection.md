# Phase 0 — Selezione Libreria Indicatori Tecnici

**Stato**: ricerca completata; spike implementativo obbligatorio prima della scelta finale.

**Piano collegato**: [plan-phase00SignalsBackendMigration.prompt.md](./plan-phase00SignalsBackendMigration.prompt.md)

## Obiettivo

Selezionare una sola dipendenza di analisi tecnica per il nuovo layer backend dei
segnali. Il runtime finale non deve installare librerie di indicatori sovrapposte.

## Vincoli LibreFolio

- Python 3.13.
- Immagine unica basata su `python:3.13-slim`.
- `numpy`, `pandas` e `scipy` sono già dipendenze del progetto.
- Linux x86_64 e arm64 devono restare supportabili.
- I plugin devono nascondere la libreria dietro contratti di proprietà LibreFolio.
- Catalogo iniziale: EMA, RSI, MACD, Bollinger, SMA, ROC, StochRSI, ATR, ADX, OBV.
- Output deterministici, allineati per data e JSON-safe.
- Nessun endpoint pubblico generico di calcolo: Asset e FX restano i punti d'ingresso.

## Confronto candidati

| Libreria | Fit | Punti forti | Rischi principali | Esito |
|---|---|---|---|---|
| `pandas-ta-classic` | Alto | Pure Python, Python 3.13 esplicito, API pandas/OHLCV, catalogo molto ampio, nessuna dipendenza OS | Fork community, API pre-1.0, nessuna API universale per lookback parametrico | Finalista |
| `TA-Lib` | Alto | Riferimento diffuso, 150+ indicatori, C veloce, lookback parametrico, wheel moderne con C incluso | Fallback da sorgente, versioning a rami, API numpy | Finalista |
| `talipp` | Medio | Pure Python, Python 3.13, aggiornamento incrementale O(1), OHLCV tipizzato | Catalogo minore, warm-up/output accorciato, batch più lento | Fallback documentato |
| `pandas-ta` | Basso | Catalogo ampio | `numba` hard-pinned incompatibile con la linea numpy corrente; beta | Scartata |
| `ta` | Basso | API pandas semplice | Release e classifier Python obsoleti | Scartata |
| `stock-indicators` | Basso | Catalogo ampio e documentato | Richiede .NET/pythonnet; costo immagine/deploy | Scartata |

## Raccomandazione provvisoria

`pandas-ta-classic` è la prima candidata: usa lo stack pandas/numpy già presente,
installa senza pacchetti OS, dichiara Python 3.13 e offre il catalogo più ampio.

`TA-Lib` è la seconda candidata: semantica di riferimento, lookback esplicito e
prestazioni batch migliori. Le wheel moderne includono la libreria C, riducendo il
vecchio problema di installazione.

La documentazione non basta per la scelta finale. Il primo step implementativo deve
misurare entrambe nel contesto reale LibreFolio.

## Spike obbligatorio

### Ambienti

Testare ogni candidata separatamente:

1. ambiente locale Python 3.13 tramite dependency manager del progetto;
2. Dockerfile corrente `python:3.13-slim`;
3. percorsi x86_64/arm64 già disponibili nei workflow di sviluppo/release.

### Dataset

- serie daily close-only lunga;
- serie daily OHLCV;
- serie piatta;
- serie con gap e punti backward-filled;
- serie corta, con warm-up insufficiente;
- campi `high`/`low`/`volume` mancanti;
- serie multi-anno per benchmark.

### Matrice indicatori

| Plugin | Input richiesto | Output atteso |
|---|---|---|
| EMA | close | linea |
| RSI | close | oscillatore |
| MACD | close | linea MACD, signal line, istogramma |
| Bollinger | close | upper/middle/lower band |
| SMA | close | linea |
| ROC | close | oscillatore percentuale |
| StochRSI | close | `%K`, `%D` |
| ATR | high, low, close | linea volatilità |
| ADX | high, low, close | ADX, `+DI`, `-DI` |
| OBV | close, volume | linea cumulativa |

### Misure

- risoluzione dipendenze rispetto a `Pipfile.lock`;
- import/runtime Python 3.13;
- build Docker e delta dimensione immagine;
- lunghezza output e allineamento date;
- semantica NaN/lookback/warm-up;
- ergonomia parametri e validazione;
- delta numerici rispetto al TypeScript attuale dopo warm-up adeguato;
- delta numerici tra candidate;
- runtime batch singola serie e più asset/coppie;
- errori su input mancanti e parametri non validi;
- licenza, manutenzione, release cadence e stabilità API.

### Regola di scelta

Scegliere la libreria che:

1. supera i gate Python/Docker/dipendenze;
2. copre tutti i dieci plugin senza seconda libreria;
3. offre warm-up e allineamento stabili e spiegabili;
4. resta confinata nei plugin;
5. ha costo batch accettabile secondo le misure reali.

Aggiornare questo documento con versione fissata, candidata scartata e misure prima di
creare i plugin production.

## Contenimento architetturale

- Solo `backend/app/services/signal_plugins/` può importare la libreria scelta.
- Schemi API, `SignalService`, Asset, FX e frontend dipendono solo da contratti
  LibreFolio.
- Ogni plugin dichiara params, input richiesti, output, warm-up e adapter libreria.
- Cambiare libreria in futuro non deve cambiare REST payload o rendering frontend.
- NaN e infinity vengono convertiti in `None` o errore prima di uscire dal plugin.

## Fonti

- TA-Lib PyPI: <https://pypi.org/project/TA-Lib/>
- TA-Lib Python: <https://github.com/TA-Lib/ta-lib-python>
- pandas-ta-classic PyPI: <https://pypi.org/project/pandas-ta-classic/>
- pandas-ta-classic: <https://github.com/xgboosted/pandas-ta-classic>
- talipp PyPI: <https://pypi.org/project/talipp/>
- Python plugin discovery: <https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/>

