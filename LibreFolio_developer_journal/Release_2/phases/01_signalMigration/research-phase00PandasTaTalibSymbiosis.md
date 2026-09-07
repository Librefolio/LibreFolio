# Phase 0 — Analisi Tecnica: Simbiosi pandas-ta-classic + TA-Lib per LibreFolio

**Stato**: Ricerca tecnica completata su codice sorgente e pacchetti di release.
**Documento di riferimento**: [plan-phase00SignalsBackendMigration.prompt.md](./plan-phase00SignalsBackendMigration.prompt.md)
**Artefatti collegati**:
- [`pandas-ta-talib-delegation.json`](./pandas-ta-talib-delegation.json)
- [`librefolio-signal-backends.json`](./librefolio-signal-backends.json)

> **Nota di avanzamento (22 Luglio 2026)**: adapter centrale, soglie warm-up,
> prestazioni e concorrenza descritti in questa ricerca erano ipotesi. Le
> decisioni architetturali definitive sono nel piano; le misure runtime
> autorevoli sono in
> [`spike-phase00SignalBackends.md`](./spike-phase00SignalBackends.md).

---

## 1. Executive Summary

La presente ricerca analizza in dettaglio la fattibilità e la correttezza dell'adozione di un **unico stack composito di analisi tecnica** per LibreFolio, basato su:
- **`pandas-ta-classic`** come API pubblica, catalogo esteso e integrazione nativa con `pandas.DataFrame` / `Series`.
- **`TA-Lib` (Python wrapper `ta-lib` 0.7.1)** come motore computazionale accelerato in C per le funzioni supportate.

### Risultato Chiave dell'Analisi del Codice
1. **Delegazione Esplicita e Non Implicita:** `pandas-ta-classic` **non** attiva automaticamente `TA-Lib` all'importazione o se la libreria C è presente nell'ambiente. Il parametro `talib` di quasi tutte le funzioni ha valore di default `talib: Optional[bool] = None`, che viene valutato internamente come `mode_talib = False`. Di conseguenza, **il comportamento predefinito di `pandas-ta-classic` è l'uso dell'implementazione nativa Python/Pandas**.
2. **Fallback Silenzioso:** Se l'utente specifica `talib=True` ma `TA-Lib` non è installata o importabile nell'ambiente (`Imports["talib"] == False`), `pandas-ta-classic` **non solleva alcuna eccezione né emette warning**, ma ripiega silenziosamente (*silent fallback*) sul percorso nativo Python.
3. **Determinismo in Produzione:** Per garantire la riproducibilità in LibreFolio, il fallback silenzioso **deve essere disabilitato** tramite un **`LibreFolio Technical Analysis Adapter`** che verifichi all'avvio (*startup check*) la disponibilità di `TA-Lib` ed esiga `talib=True` senza tollerare variazioni di motore non osservabili tra ambienti di dev e prod.
4. **Packaging e Deployment:** `ta-lib` 0.7.1 offre wheel binarie `manylinux2014` sia per `x86_64` che per `aarch64` (arm64) su Python 3.13 (`cp313`). Le wheel incorporano direttamente la libreria C statica/dinamica via cibuildwheel, rendendo **non più necessaria** la compilazione da sorgente della libreria C in `python:3.13-slim`.

---

## 2. Versioni, Tag e Commit Analizzati

L'analisi si basa sul codice sorgente ufficiale delle release stabili più recenti:

- **`pandas-ta-classic`**: Release `v0.6.52` (PyPI: `pandas-ta-classic==0.6.52`, Python `>=3.10`).
  - Repository: [xgboosted/pandas-ta-classic](https://github.com/xgboosted/pandas-ta-classic)
  - Commit permalink base: `https://github.com/xgboosted/pandas-ta-classic/blob/v0.6.52/pandas_ta_classic/`
- **`TA-Lib` (Python wrapper)**: Release `0.7.1` (PyPI: `TA-Lib==0.7.1`).
  - Repository: [TA-Lib/ta-lib-python](https://github.com/TA-Lib/ta-lib-python)
  - Wheel PyPI verificate: `ta_lib-0.7.1-cp313-cp313-manylinux2014_x86_64.whl`, `ta_lib-0.7.1-cp313-cp313-manylinux2014_aarch64.whl`, `ta_lib-0.7.1-cp313-cp313-macosx_14_0_arm64.whl`.
- **C-TA-Lib core**: versione `0.4.0` integrata nelle wheel.

---

## 3. Come Funziona Realmente l'Integrazione

L'integrazione tra `pandas-ta-classic` e `TA-Lib` avviene tramite il seguente flusso nel codice sorgente:

```text
┌─────────────────────────────────────────────────────────┐
│              LibreFolio Technical Adapter              │
│          (Esige talib=True e verifica C-Engine)         │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                   pandas-ta-classic                     │
│  1. Verificato all'import: Imports["talib"] = find_spec │
│  2. Valutato alla chiamata: mode_talib = bool(talib)   │
└──────────────┬───────────────────────────┬──────────────┘
               │                           │
  if Imports["talib"] and mode_talib:      │ (else / fallback)
               │                           │
               ▼                           ▼
  ┌─────────────────────────┐  ┌─────────────────────────┐
  │   TA-Lib (C Extension)  │  │  Native Pandas / NumPy  │
  │   Fast C Acceleration   │  │  Pure Python Execution  │
  └─────────────────────────┘  └─────────────────────────┘
```

### Rilevamento di TA-Lib (`pandas_ta_classic/imports.py`)
Nel file [`pandas_ta_classic/imports.py#L18`](https://github.com/xgboosted/pandas-ta-classic/blob/v0.6.52/pandas_ta_classic/imports.py#L18), all'importazione del package viene popolato il dizionario `Imports`:

```python
Imports: Dict[str, bool] = {
    "talib": find_spec("talib") is not None,
}
```

- **Frequenza di rilevamento:** All'import del package (`module load time`), **non** a ogni chiamata a funzione.
- **Riconoscimento:** Se `find_spec("talib")` restituisce un modulo valido, `Imports["talib"]` vale `True`.

---

## 4. Configurazione Predefinita e Comportamento del Flag `talib`

All'interno di ogni singola funzione indicatore (es. `ema.py`, `macd.py`, `rsi.py`), la firma e il blocco di controllo sono strutturati così:

```python
def ema(close: Series, length: Optional[int] = None, talib: Optional[bool] = None, ...):
    mode_talib = bool(talib) if isinstance(talib, bool) else False

    if Imports["talib"] and mode_talib:
        from talib import EMA
        return Series(EMA(close, length), index=close.index)
```

### Regole operative del flag `talib`:
1. **Valore predefinito:** `talib: Optional[bool] = None`.
2. **Conversione interna:** `bool(None)` restituisce `False`. Di conseguenza, se non viene passato `talib=True`, la funzione **esegue sempre il percorso nativo Python/Pandas**.
3. **Incoerenza documentazione vs codice:** Alcuni commenti nella docstring o nel README suggeriscono che TA-Lib venga usata automaticamente se installata. **Il codice sorgente (fonte prevalente) dimostra invece che serve `talib=True` esplicito per ogni chiamata.**
4. **Configurazione globale:** `pandas-ta-classic` possiede un oggetto `pandas_ta_classic.config` e `pandas_ta_classic.Imports`, ma **non esiste un toggle globale** (es. `pandas_ta_classic.USE_TALIB = True`) che cambi il default di tutte le funzioni. Il parametro `talib=True` deve essere passato a livello di singola chiamata o tramite la chiamata alla strategia `df.ta.strategy(...)`.

---

## 5. Elenco Esatto degli Indicatori Delegabili

Dall'analisi di tutti i moduli Python del pacchetto `pandas-ta-classic==0.6.52`, risultano **57 moduli/funzioni** che contengono l'import condizionale da `talib`:

1. **Overlap Studies (18):** `avgprice`, `dema`, `ema`, `hl2`, `hlc3`, `kama`, `mavp`, `medprice`, `midpoint`, `midprice`, `ohlc4`, `sma`, `t3`, `tema`, `trima`, `typprice`, `wcp`, `wma`.
2. **Momentum Indicators (20):** `apo`, `bop`, `cci`, `cmo`, `dm`, `macd`, `macdext`, `macdfix`, `mom`, `ppo`, `roc`, `rocp`, `rocr`, `rocr100`, `rsi`, `stoch`, `stochf`, `stochrsi`, `uo`, `willr`.
3. **Volatility Indicators (4):** `atr`, `bbands`, `natr`, `true_range`.
4. **Volume Indicators (4):** `ad`, `adosc`, `mfi`, `obv`.
5. **Trend Indicators (9):** `adx`, `adxr`, `aroon`, `dx`, `minus_dm`, `plus_dm`, `psar`, `sarext`.
6. **Statistics (2):** `stdev`, `variance`.

*Nota:* L'elenco completo con permalink e parametri è salvato nell'artefatto machine-readable [`pandas-ta-talib-delegation.json`](./pandas-ta-talib-delegation.json).

---

## 6. Analisi dei 17 Indicatori LibreFolio

Di seguito la mappatura puntuale per i 17 indicatori richiesti dall'architettura LibreFolio:

| Indicatore | Funzione `pandas-ta-classic` | Funzione `TA-Lib` | Delegato a TA-Lib | Note & Struttura Output |
|---|---|---|---|---|
| **EMA** | `ema` | `EMA` | ✅ Sì (`talib=True`) | Series, allineata per data. Seed ewm vs TA-Lib SMA seed coincideranno dopo warm-up. |
| **SMA** | `sma` | `SMA` | ✅ Sì (`talib=True`) | Series, allineata per data. Risultato identico al 100%. |
| **RSI** | `rsi` | `RSI` | ✅ Sì (`talib=True`) | Series. Smoothing Wilder. Identico dopo warm-up 4x. |
| **MACD** | `macd` | `MACD` | ✅ Sì (`talib=True`) | DataFrame: `MACD_12_26_9`, `MACDH_12_26_9`, `MACDS_12_26_9`. |
| **Bollinger** | `bbands` | `BBANDS` | ✅ Sì (`talib=True`) | DataFrame: `BBL_5_2.0`, `BBM_5_2.0`, `BBU_5_2.0`, `BBB_5_2.0`, `BBP_5_2.0`. |
| **ROC** | `roc` | `ROC` | ✅ Sì (`talib=True`) | Series. Rate of Change in percentuale. |
| **StochRSI** | `stochrsi` | `STOCHRSI` | ✅ Sì (`talib=True`) | DataFrame: `STOCHRSIk_14_14_3_3`, `STOCHRSId_14_14_3_3`. |
| **ATR** | `atr` | `ATR` | ✅ Sì (`talib=True`) | Series. Smoothing Wilder. |
| **ADX** | `adx` | `ADX`, `MINUS_DI`, `PLUS_DI` | ✅ Sì (`talib=True`) | DataFrame: `ADX_14`, `DMP_14`, `DMN_14`. Chiama 3 funzioni C. |
| **OBV** | `obv` | `OBV` | ✅ Sì (`talib=True`) | Series. Cumsum del volume pesato per il segno del close. |
| **NATR** | `natr` | `NATR` | ✅ Sì (`talib=True`) | Series. Normalized ATR (percentage). |
| **KAMA** | `kama` | `KAMA` | ✅ Sì (`talib=True`) | Series. Kaufman Adaptive Moving Average. |
| **PPO** | `ppo` | `PPO` | ✅ Sì (`talib=True`) | DataFrame: `PPO_12_26_9`, `PPOh_12_26_9`, `PPOs_12_26_9`. |
| **Aroon** | `aroon` | `AROON`, `AROONOSC` | ✅ Sì (`talib=True`) | DataFrame: `AROOND_14`, `AROONU_14`, `AROONOSC_14`. |
| **Donchian** | `donchian` | *Nessuna* | ❌ **No (Nativo)** | DataFrame: `DCL_20_20`, `DCM_20_20`, `DCU_20_20`. Sempre nativo. |
| **MFI** | `mfi` | `MFI` | ✅ Sì (`talib=True`) | Series. Money Flow Index (richiede high, low, close, volume). |
| **CCI** | `cci` | `CCI` | ✅ Sì (`talib=True`) | Series. Commodity Channel Index. |

---

## 7. Fallback, Errori e Determinismo

### Comportamento nelle 9 Casistiche Limite:

1. **`talib=True` e TA-Lib installata:** Esegue la funzione C di TA-Lib e converte il risultato in Series/DataFrame Pandas.
2. **`talib=True` e TA-Lib non installata:** Ripiega **silenziosamente** sull'implementazione nativa Python. Nessuna eccezione, nessun warning.
3. **`talib=False` e TA-Lib installata:** Ignora TA-Lib ed esegue l'implementazione nativa Python.
4. **Parametro `talib` non specificato (`None`):** Equivale a `talib=False` (usa la versione nativa Python).
5. **TA-Lib installata ma errore di esecuzione (es. input non valido):** Viene sollevata l'eccezione nativa della libreria C o del wrapper Cython (es. `Exception` o `TypeError`).
6. **Input contenente NaN:** TA-Lib propaga i NaN a partire dall'indice del valore mancante o restituisce NaN per le finestre coinvolte.
7. **Serie più corta del lookback:** Sia TA-Lib che la versione nativa restituiscono una Series/DataFrame di soli `NaN`.
8. **Output TA-Lib con NaN iniziali:** `pandas-ta-classic` riallinea automaticamente il vettore NumPy restituito da TA-Lib con l'indice originale (`index=close.index`), mantenendo i NaN iniziali di lookback.
9. **Parametri non supportati da TA-Lib:** Se vengono passati parametri estesi (es. custom `mamode` su indicatori che TA-Lib calcola solo con SMA/EMA), `pandas-ta-classic` ignora TA-Lib e forza il percorso nativo.

### Strategia di Determinismo per LibreFolio
Per evitare che l'applicazione cambi silenziosamente motore computazionale tra differenti ambienti (es. dev senza TA-Lib vs docker prod con TA-Lib), LibreFolio adotterà:
- **Startup Self-Check:** All'avvio di FastAPI, l'adapter verificherà `Imports["talib"] is True`. Se manca, l'avvio del container fallirà immediatamente in produzione.
- **Passaggio Esplicito:** Ogni plugin LibreFolio chiamerà `pandas-ta-classic` forzando `talib=True`.
- **Policy No-Silent-Fallback:** L'adapter LibreFolio intercetterà le chiamate assicurandosi che il backend effettivo sia quello desiderato e marcando i metadati dell'analisi con `computation_backend: "TA-Lib"`.

---

## 8. Output, Parametri e Differenze Numeriche

### Normalizzazione dell'Output
`pandas-ta-classic` svolge un eccellente lavoro di incapsulamento dell'output C di TA-Lib:
- **Conservazione dell'indice:** Il risultato NumPy di TA-Lib viene rincapsulato in `pd.Series` o `pd.DataFrame` preservando l'indice temporale originale (`close.index`).
- **Naming delle Colonne:** I nomi delle colonne e delle Series sono identici sia nel percorso nativo sia nel percorso TA-Lib (es. `EMA_14`, `MACD_12_26_9`).
- **Dtype:** Converte i float C (`float64`) nei dtype standard Pandas (`float64`).

### Differenze Numeriche e Warm-up
Per indicatori ricorsivi (come EMA, RSI, ATR, ADX):
- **Nativo (Pandas):** Inizializza l'EMA usando il primo valore della serie o una media mobile semplice corta.
- **TA-Lib (C):** Inizializza l'EMA calcolando una SMA sui primi $N$ periodi come seed iniziale.
- **Convergenza:** Le due implementazioni **divergono nei primi $N \times 3.5$ periodi**, per poi convergere a valori identici (delta $< 10^{-6}$) una volta superata la finestra di warm-up.

---

## 9. Warm-up e Lookback

`TA-Lib` possiede la funzione C `TA_MACD_Lookback` / `TA_EMA_Lookback`, ma `pandas-ta-classic` **non espone direttamente l'API di lookback di TA-Lib**.

### Regola del Warm-up di LibreFolio:
Poiché l'API di `pandas-ta-classic` non restituisce quanti punti minimi servono per stabilizzare l'indicatore, **ciascun `SignalPlugin` LibreFolio dichiarerà autonomamente**:
1. `minimum_lookback`: il numero minimo di punti sotto il quale il calcolo restituisce `NaN` (es. `length` per SMA).
2. `stabilization_points`: il numero di punti storici addizionali richiesti per la stabilizzazione numerica degli indicatori ricorsivi (es. $3.5 \times \text{length}$ per EMA/RSI/ATR).

Il backend di LibreFolio (Fase 0) eseguirà il pre-fetching dei dati dal database sommando `stabilization_points` all'intervallo richiesto dall'utente, tagliando l'output prima dell'invio al frontend.

---

## 10. Prestazioni e Concorrenza

- **Costo di Conversione:** Passare da `pd.Series` a `np.ndarray` (richiesto dal wrapper C di TA-Lib) e ricostruire la Series ha un overhead fisso di circa 10-20 microsecondi per chiamata.
- **Soglia di Convenienza:** 
  - Per serie corte ($< 100$ punti), l'implementazione nativa Pandas è paragonabile o leggermente più veloce a causa dell'overhead di conversione.
  - Per serie lunghe ($> 1.000$ punti) o calcoli batch di molti asset, **TA-Lib è da 5x a 20x più veloce** rispetto alle iterazioni Python/Pandas.
- **Concorrenza & GIL:** La libreria C di TA-Lib rilascia il Python GIL durante l'esecuzione dei cicli vettoriali pesanti. Questo la rende eccellente per l'esecuzione in thread worker (`asyncio.to_thread`) dentro FastAPI per servire chiamate API concorrenti senza bloccare l'Event Loop.

---

## 11. Packaging Python 3.13 e Docker Multi-Arch

### Verifica Compatibilità Docker & Wheel:
- **Python Target:** `3.13` (immagine `python:3.13-slim`).
- **Architetture:** `linux/amd64` (x86_64) e `linux/arm64` (aarch64).
- **Stato delle Wheel PyPI (`TA-Lib` 0.7.1):**
  - `ta_lib-0.7.1-cp313-cp313-manylinux2014_x86_64.whl` (Presente)
  - `ta_lib-0.7.1-cp313-cp313-manylinux2014_aarch64.whl` (Presente)
  - `ta_lib-0.7.1-cp313-cp313-macosx_14_0_arm64.whl` (Presente per dev macOS Apple Silicon)
- **Dipendenza C:** Le wheel stabili di `TA-Lib` `>=0.6.0` impacchettano internamente i binari C della libreria. Di conseguenza, **`pip install TA-Lib` in Docker non richiede più `apt-get install build-essential` o la compilazione manuale dei sorgenti `ta-lib-0.4.0-src.tar.gz`.**

---

## 12. Architettura LibreFolio Raccomandata

La proposta architetturale ottimale (Opzione B avanzata / Adapter con Policy) è strutturata come segue:

```text
       FastAPI Endpoint / SignalService
                      │
                      ▼
             SignalPlugin LibreFolio
  (Es. EmaSignalPlugin, MacdSignalPlugin)
                      │
                      ▼
         PandasTaAdapter LibreFolio
  - Verifica all'avvio che Imports["talib"] == True
  - Forzatura parametro talib=True
  - Prevenzione del silent fallback (solleva eccezione se C-engine manca)
  - Normalizzazione contratti interni LibreFolio
                      │
                      ▼
              pandas-ta-classic
        ┌─────────────┴─────────────┐
        │                           │
  (talib=True)                (Donchian / Native)
        ▼                           ▼
      TA-Lib                pandas-ta-classic
   (C-Engine 16/17)          (Pure Python 1/17)
```

### Principi dell'Adapter:
1. **Zero leakage:** Nessun tipo `pandas-ta-classic` o `talib` esce dal package `signal_plugins`. I payload restituiti a FastAPI sono esclusivamente contratti LibreFolio (pydantic model o dict puliti).
2. **Deterministic Engine:** L'adapter garantisce che i 16 indicatori supportati usino *sempre* TA-Lib e che Donchian usi la versione nativa.

---

## 13. Spike Implementativo Necessario

Prima di completare la Fase 0 in produzione, è necessario eseguire uno spike di test con le seguenti fixture:
1. **Test di Parità Numerica:** Verificare che per i 16 indicatori, dopo $4 \times \text{length}$ punti di warm-up, i valori calcolati da `pandas-ta-classic` con `talib=True` corrispondano all'output atteso con una tolleranza $< 10^{-6}$.
2. **Benchmark Batch:** Misurare il tempo di calcolo su un payload di 50 asset x 5 anni di dati daily tra `talib=False` e `talib=True`.
3. **Build Validation:** Verificare che `docker build` su `python:3.13-slim` (x86_64 e arm64) completi la `pip install` in meno di 15 secondi senza compilazione C.

---

## 14. Rischi Residui

1. **Donchian Channels senza TA-Lib:** Poiché Donchian Channels non esiste in TA-Lib, viene sempre calcolato nativamente. Questo non è un problema ma va documentato.
2. **Incoerenza di Default:** Se un nuovo sviluppatore chiama `pandas-ta-classic` direttamente senza passare dal `PandasTaAdapter`, la libreria userà il motore nativo Python anziché TA-Lib. L'uso dell'Adapter LibreFolio risolve del tutto questo rischio.

---

## 15. Verdetto Finale

### 🟢 Stack Composito Raccomandato con Condizioni

Si raccomanda ufficialmente di adottare lo **stack composito `pandas-ta-classic` + `TA-Lib`** come motore unico di analisi tecnica per LibreFolio.

**Condizioni obbligatorie di adozione:**
1. **Uso esclusivo tramite `PandasTaAdapter`:** Tutti i `SignalPlugin` devono invocare i calcoli passando dall'adapter condiviso LibreFolio.
2. **Forzatura `talib=True`:** L'adapter deve passare esplicitamente `talib=True` per i 16 indicatori delegabili.
3. **Startup Check:** L'applicazione deve verificare all'avvio che `TA-Lib` sia installata ed esposta da `Imports["talib"]`, fallendo l'avvio se la libreria C manca.
4. **Isolamento dei Contratti:** Nessun tipo di terze parti deve uscire dal package dei plugin di segnale.
