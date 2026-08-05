# 06B — Teoria finanziaria: indicatori tecnici e benchmark sintetici

> **Release 2 · Phase 0 · 05_cleanAudit / mkdocsAudit**
>
> Baseline: [00_BASELINE](00_BASELINE.md) — commit `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103`,
> branch `dev_release2`, worktree dirty (elenco invariato rispetto al manifest).
> Modalità: sola lettura. Nessuna correzione applicata, nessun server avviato.

## Scope assegnato (27 pagine EN pubblicate)

- `technical-analysis/index.en.md` (1)
- `technical-analysis/indicators/*.en.md` (22): `index`, `adx`, `aroon`, `atr`,
  `bollinger-bands`, `cci`, `donchian-channels`, `ema`, `kama`, `macd`, `mfi`,
  `momentum`, `natr`, `obv`, `ppo`, `roc`, `rsi`, `sma`, `stochastic-rsi`, `trend`,
  `volatility`, `volume`
- `technical-analysis/synthetic-benchmarks/*.en.md` (4): `index`, `compound`,
  `linear`, `sine-wave`

Esclusi per mandato: `performance-metrics/**`, `risk-metrics/**` (report 06C),
developer guide, traduzioni, manuale utente, admin, AI Export, FX, community.

## Codice/sorgenti confrontati

- `backend/app/services/signal_plugins/{ema,sma,kama,adx,aroon,bollinger,atr,natr,
  donchian,rsi,macd,roc,stoch_rsi,ppo,cci,obv,mfi}.py` (17 plugin "legacy", esclusi i
  5 plugin di rischio `drawdown`, `rolling_beta`, `rolling_return`, `rolling_sharpe`,
  `rolling_volatility`, fuori scope)
- `backend/app/schemas/signals.py`, `backend/app/services/signal_service.py`
- `backend/test_scripts/test_services/test_signal_plugin_matrix.py` (conferma
  cardinalità e comportamento "16 delegati a TA-Lib + 1 nativo — Donchian")
- `frontend/src/lib/charts/signals/{LinearSignal,CompoundSignal,SineSignal,
  ChartSignal,registry}.ts`
- `frontend/src/lib/stores/signalCatalogStore.svelte.ts`

## Sintesi

Il gruppo **indicatori** (22 pagine) è risultato molto accurato: le 17 formule, i
default dei parametri, le categorie (trend/momentum/volatility/volume), i requisiti
dati (close-only vs OHLC/volume) e la compatibilità Asset/FX dichiarati nelle pagine
corrispondono esattamente al codice — nessun reperto di correzione necessario oltre a
quanto elencato sotto (nessuno, in realtà: zero contraddizioni sul gruppo indicatori).

Il gruppo **benchmark sintetici** (4 pagine) contiene invece un reperto rilevante:
`compound.en.md` afferma che "il backend di LibreFolio supporta" sei frequenze di
capitalizzazione (annuale/semestrale/trimestrale/mensile/giornaliera/continua), ma
l'intera famiglia di benchmark sintetici (`linear`, `compound`, `sine`) è calcolata
**esclusivamente lato frontend** (`source: 'local'` in `registry.ts:119`) — non esiste
alcun backend per questi segnali, né un parametro di frequenza configurabile. Si
aggiungono tre difetti minori sui valori di default documentati (rate, ampiezza,
periodo) che non coincidono con i default reali nel codice frontend.

Totale reperti: **5** (1 major, 3 minor, 1 info). Nessun link rotto rilevato: tutti i
`docs_path` dei plugin combaciano 1:1 con i file `.en.md` effettivi, e i riferimenti
incrociati verso `user/assets/detail/{chart,signals}.en.md` risolvono correttamente.

---

## Copertura per pagina

| # | Pagina | Esito | Reperti |
|---|---|---|---|
| 1 | `technical-analysis/index.en.md` | ✅ Verificata, nessun reperto | — |
| 2 | `indicators/index.en.md` | ✅ Verificata, nessun reperto | — |
| 3 | `indicators/trend.en.md` | ✅ Verificata, nessun reperto | — |
| 4 | `indicators/momentum.en.md` | ✅ Verificata, nessun reperto | — |
| 5 | `indicators/volatility.en.md` | ✅ Verificata, nessun reperto | — |
| 6 | `indicators/volume.en.md` | ✅ Verificata, nessun reperto | — |
| 7 | `indicators/ema.en.md` | ✅ Verificata, nessun reperto | — |
| 8 | `indicators/sma.en.md` | ✅ Verificata, nessun reperto | — |
| 9 | `indicators/kama.en.md` | ✅ Verificata, nessun reperto | — |
| 10 | `indicators/adx.en.md` | ✅ Verificata, nessun reperto | — |
| 11 | `indicators/aroon.en.md` | ✅ Verificata, nessun reperto | — |
| 12 | `indicators/rsi.en.md` | ✅ Verificata, nessun reperto | — |
| 13 | `indicators/macd.en.md` | ✅ Verificata, nessun reperto | — |
| 14 | `indicators/roc.en.md` | ✅ Verificata, nessun reperto | — |
| 15 | `indicators/stochastic-rsi.en.md` | ✅ Verificata, nessun reperto | — |
| 16 | `indicators/ppo.en.md` | ✅ Verificata, nessun reperto | — |
| 17 | `indicators/cci.en.md` | ✅ Verificata, nessun reperto | — |
| 18 | `indicators/bollinger-bands.en.md` | ✅ Verificata, nessun reperto | — |
| 19 | `indicators/atr.en.md` | ✅ Verificata, nessun reperto | — |
| 20 | `indicators/natr.en.md` | ✅ Verificata, nessun reperto | — |
| 21 | `indicators/donchian-channels.en.md` | ✅ Verificata, nessun reperto | — |
| 22 | `indicators/obv.en.md` | ✅ Verificata, nessun reperto | — |
| 23 | `indicators/mfi.en.md` | ✅ Verificata, nessun reperto | — |
| 24 | `synthetic-benchmarks/index.en.md` | ⚠️ Omissione architetturale | B0 |
| 25 | `synthetic-benchmarks/linear.en.md` | ⚠️ Default errato | B2 |
| 26 | `synthetic-benchmarks/compound.en.md` | ❌ Claim non veritiera + default errato | B1, B3 |
| 27 | `synthetic-benchmarks/sine-wave.en.md` | ⚠️ Due default errati | B4 |

---

## Reperti

### 🟠 B1 — `compound.en.md` afferma un supporto backend a frequenze di capitalizzazione che non esiste

**Dove**: `mkdocs_src/docs/financial-theory/technical-analysis/synthetic-benchmarks/compound.en.md`,
sezione "🔢 Mathematical Formula":

> "LibreFolio's backend supports the following compounding frequencies: **Annual**
> ($n=1$), **Semiannual** ($n=2$), **Quarterly** ($n=4$), **Monthly** ($n=12$),
> **Daily** ($n=365$), and **Continuous** ($n \to \infty$)."

**Controprova nel codice**:

- Il segnale `compound` è registrato come definizione **locale** (frontend), non
  backend: `frontend/src/lib/charts/signals/registry.ts:119` —
  `source: 'local'` all'interno di `definitionFromConstructor`, applicata a tutte le
  classi con `category === 'benchmark'` (`getLocalSignalDefinitions`, righe 122-125).
- `backend/app/services/signal_plugins/` (22 file) non contiene alcun plugin
  `linear`/`compound`/`sine`/benchmark — solo i 17 indicatori + 5 plugin di rischio.
  Non esiste nessun endpoint backend che calcoli un benchmark sintetico.
- L'unica implementazione reale è
  `frontend/src/lib/charts/signals/CompoundSignal.ts:29-33`, i cui unici
  `paramDescriptors` sono `annualRate` e `offset` — **non esiste alcun parametro di
  frequenza** (nessun `compoundingFrequency`, `n`, o simile). La ricerca
  `grep -rin "semiannual|quarterly|continuous compounding|compounding frequenc"` su
  `backend/` e `frontend/src` non produce alcun riscontro pertinente (gli unici hit
  su "QUARTERLY"/"SEMIANNUAL" riguardano `MaturationFrequency`, l'enum delle cedole
  obbligazionarie in `backend/app/schemas/assets.py`, dominio totalmente estraneo ai
  benchmark sintetici).
- Il calcolo reale è una capitalizzazione giornaliera fissa a fattore costante
  (`dailyFactor = (1 + rate) ** (1/365)`, righe 66-82 di `CompoundSignal.ts`), che
  corrisponde solo al caso $n=365$ del paragrafo generale — non è mai selezionabile
  l'utente non ha alcun controllo su $n$.

**Classificazione**: Contraddizione. **Gravità**: major (descrive un'architettura
backend e una funzionalità a scelta multipla che semplicemente non esistono; un
lettore/integratore che si aspetti un parametro `compoundingFrequency` lato API
resterebbe bloccato). **Confidenza**: alta (verificato sia per assenza di codice
backend sia per assenza del parametro lato frontend).

**Direzione di correzione suggerita**: sostituire il paragrafo con la descrizione
reale — un solo modello, calcolato client-side (`ChartSignal` locale, non
richiede round-trip al backend), con capitalizzazione giornaliera fissa
equivalente a $n=365$; rimuovere la tabella delle frequenze o riformularla come
"nota teorica generale sull'interesse composto", chiarendo esplicitamente che non è
un parametro configurabile in LibreFolio.

---

### 🟢 B2 — `linear.en.md`: default di `annualRate` documentato (5) non coincide con il default reale (2)

**Dove**: `mkdocs_src/docs/financial-theory/technical-analysis/synthetic-benchmarks/linear.en.md`,
tabella "⚙️ Parameters":

| Parameter | Key | Default | Description |
|---|---|---|---|
| Annual Rate | `annualRate` | **5** | Growth rate in percent per year. |

**Controprova**: `frontend/src/lib/charts/signals/LinearSignal.ts:29` —
`default: 2` nel `paramDescriptors` di `annualRate` (e ripreso in `getLabel()`,
riga 66, con fallback `?? 2`).

**Classificazione**: Dettaglio obsoleto. **Gravità**: minor (valore didattico errato,
nessun impatto funzionale — l'utente vede comunque il default reale nella UI).
**Confidenza**: alta.

**Direzione di correzione**: allineare la tabella al valore `2` presente nel codice,
oppure aggiornare il codice se `5` è il valore concettualmente desiderato (decisione di
prodotto, non di documentazione).

---

### 🟢 B3 — `compound.en.md`: default di `annualRate` documentato (7) non coincide con il default reale (8)

**Dove**: `mkdocs_src/docs/financial-theory/technical-analysis/synthetic-benchmarks/compound.en.md`,
tabella "⚙️ Parameters":

| Parameter | Key | Default | Description |
|---|---|---|---|
| Annual Rate | `annualRate` | **7** | Compound growth rate in percent per year. |

**Controprova**: `frontend/src/lib/charts/signals/CompoundSignal.ts:31` —
`default: 8` (ripreso anche in `computePoints`, riga 60, `?? 8`, e in `getLabel()`,
riga 89, `?? 8`).

**Classificazione**: Dettaglio obsoleto. **Gravità**: minor. **Confidenza**: alta.

**Direzione di correzione**: allineare la tabella al valore `8`.

---

### 🟢 B4 — `sine-wave.en.md`: due default documentati (amplitude 10, period 365) non coincidono con i reali (15, 45)

**Dove**: `mkdocs_src/docs/financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.en.md`,
tabella "⚙️ Parameters":

| Parameter | Key | Default | Description |
|---|---|---|---|
| Amplitude | `amplitude` | **10** | Peak oscillation range as % of base value. |
| Period | `period` | **365** | Full cycle length in days. |

**Controprova**: `frontend/src/lib/charts/signals/SineSignal.ts:34-49` —
`amplitude` default `15`, `period` default `45` (coerente con il commento di modulo
alle righe 6-8 dello stesso file: "amplitude: ... default 15%", "period: ... default
45"). Il default di `offset` (0) è invece corretto.

**Classificazione**: Dettaglio obsoleto. **Gravità**: minor, ma con una sfumatura
narrativa da segnalare: la sezione "💡 Financial Meaning" della pagina motiva il
benchmark con casi d'uso a ciclo **annuale** ("agricultural commodities,
tourism-linked currencies"), coerenti con un default `period = 365` come documentato;
il default reale (`45` giorni, un ciclo di circa un mese e mezzo) non illustra affatto
lo scenario di stagionalità annuale descritto in apertura pagina, per cui l'errore sul
default rischia di generare un disallineamento fra l'aspettativa testuale e ciò che un
utente vede all'apertura del pannello parametri. **Confidenza**: alta.

**Direzione di correzione**: allineare la tabella ai valori `15` / `45`, oppure — se si
vuole preservare la narrativa sulla stagionalità annuale — impostare il default del
codice a `365` giorni (decisione di prodotto) e aggiornare `amplitude` di conseguenza.

---

### ℹ️ B0 — Nessuna pagina del gruppo "synthetic-benchmarks" dichiara esplicitamente che i benchmark sono calcolati lato client

**Dove**: `synthetic-benchmarks/index.en.md`, sezione "🎯 Synthetic Benchmarks":

> "Unlike indicators (computed *from* market data), benchmarks are generated purely
> from parameters"

Questa frase è tecnicamente corretta ma **omette** la distinzione architetturale più
rilevante per uno sviluppatore o un contributor: gli indicatori sono un contratto
`SignalPlugin` lato backend (`backend/app/services/signal_plugins/`, esposto via API
e cache), mentre i tre benchmark sono `ChartSignal` **puramente frontend**
(`source: 'local'`, `frontend/src/lib/charts/signals/registry.ts:119`), fusi al
catalogo backend solo al momento del rendering
(`signalCatalogStore.svelte.ts:49`, `mergeSignalDefinitions(response.items ?? [],
getLocalSignalDefinitions(), domain)`). Questa distinzione (nessun round-trip API per
calcolare/validare i benchmark, nessuna persistenza server-side, nessun controllo di
range dati storico) non emerge da nessuna delle 4 pagine del gruppo.

**Classificazione**: Omissione. **Gravità**: info (nessun errore fattuale, ma
un'informazione architetturale utile e assente che avrebbe anche prevenuto il reperto
B1). **Confidenza**: alta.

**Direzione di correzione**: aggiungere una riga o un callout in
`synthetic-benchmarks/index.en.md` che chiarisca "computed client-side, no backend
round-trip" prima di descrivere i tre modelli.

---

## Aree verificate senza reperti (evidenza positiva)

Per completezza, si riportano i controlli puntuali che **non** hanno prodotto
discrepanze, a beneficio di futuri audit che tocchino lo stesso codice:

- **Conteggio "17 backend indicators"** (`index.en.md`, `indicators/index.en.md`):
  confermato da `backend/test_scripts/test_services/test_signal_plugin_matrix.py:309`
  (`plan.unique_computation_count == 17`) e `:338` (`len(results) == 17`), oltre al
  conteggio diretto dei plugin non di rischio in `signal_plugins/`.
  Il nome del test (`test_backend_path_is_sixteen_delegated_plus_native_donchian`,
  riga ~280) corrisponde esattamente alla struttura implicita del catalogo: 16
  indicatori delegati a TA-Lib (`talib=True` nel sorgente di `compute`) + Donchian
  nativo (nessuna chiamata `talib=True`).
- **Default dei parametri dei 17 indicatori** — periodo, moltiplicatore Bollinger
  (2.0), soglie overbought/oversold (RSI 70/30, StochRSI 80/20, MFI 80/20), fast/slow/
  signal di MACD e PPO (12/26/9): tutti confermati campo per campo nei rispettivi
  `*SignalParams` in `backend/app/services/signal_plugins/*.py`.
- **Requisiti dati (close-only vs OHLC/volume)** nelle tabelle "Data Requirements" di
  `trend.en.md`, `momentum.en.md`, `volatility.en.md`, `volume.en.md`,
  `indicators/index.en.md`: confermati da `input_requirements.price_fields` di ogni
  plugin.
  Anche l'affermazione generale in `indicators/index.en.md` ("Close-only indicators
  work on Assets and FX rates; indicators requiring high, low, or volume are
  Asset-only") è confermata da `compatible_domains` (`ASSET, FX` per EMA/SMA/KAMA/RSI/
  MACD/ROC/StochRSI/PPO/Bollinger; solo `ASSET` per ADX/Aroon/ATR/NATR/Donchian/CCI/
  OBV/MFI).
- **Raggruppamento per categoria** (trend/momentum/volatility/volume) in tutte le
  pagine gruppo: combacia 1:1 con `category = SignalCategory.*` dichiarato in ciascun
  plugin.
- **Claim specifiche di implementazione**, verificate riga per riga:
  - KAMA — "fast/slow constants are not exposed... internal library defaults" (
    `kama.en.md`): confermato, `ta.kama(..., talib=True)` delega a TA-Lib che usa
    costanti interne fisse (`fast=2`, `slow=30`), mai passate da LibreFolio.
  - Stochastic RSI — "LibreFolio passes `period` to TA-Lib as both the underlying RSI
    period and the stochastic %K lookback" (`stochastic-rsi.en.md`): confermato in
    `pandas_ta_classic.stochrsi` (ramo `talib=True`):
    `_STOCHRSI(close, timeperiod=length, fastk_period=length, fastd_period=d)` — lo
    stesso `length` (il `period` di LibreFolio) alimenta sia `timeperiod` sia
    `fastk_period`.
  - OBV — "no configurable parameters", "rebased to zero at the start of the
    requested chart range" (`obv.en.md`, `volume.en.md`): confermato,
    `ObvSignalParams` non ha campi, e `obv.py` righe ~133-152 sottrae
    esplicitamente il valore alla `baseline_index` corrispondente all'inizio del
    range richiesto (`context.requested_range.start`).
  - EMA `offset` — "Vertical shift as % of base value" (`ema.en.md`): confermato,
    `ema.py` applica `factor = 1.0 + params.offset / 100.0` moltiplicativamente
    sull'output.
- **Percorsi doc (`docs_path`)** dichiarati in ciascun plugin (`adx.py`, `aroon.py`,
  ..., `stoch_rsi.py`) combaciano 1:1 con i nomi reali dei file `.en.md` sotto
  `indicators/` — nessun link rotto.
- **Riferimenti incrociati fuori gruppo** — `indicators/index.en.md` rimanda a
  `../../../user/assets/detail/{chart,signals}.en.md`: entrambi i file esistono.

## Non verificabile / fuori dal perimetro locale

- Nessuna claim del gruppo assegnato è risultata non verificabile: tutte le 27 pagine
  fanno riferimento a comportamento presente nel repository (backend, frontend o
  test), non a servizi esterni o infrastruttura non ispezionabile localmente.

## Nota per la sintesi finale (00_INDEX.md)

Aggiornamento suggerito alla riga "06B" della tabella di copertura: stato da
"In corso" a completato, 27/27 pagine coperte, 5 reperti (1 major, 3 minor, 1 info),
0 non verificabili, 0 problemi di navigazione/link.
