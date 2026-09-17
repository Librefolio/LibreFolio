# 06 — Matematica: librerie installate e reimplementazioni

**Data**: 16 Settembre 2026
**Stato**: analisi conclusa, verificata eseguendo codice
**Domanda di partenza**: il segnale drawdown prende la matematica da
`services/risk/metrics.py` e non da una delle due librerie di rischio installate.
È corretto? E in generale: abbiamo riscritto utility che le librerie già offrono?

> Ogni numero in questo documento viene da un'esecuzione reale, non da lettura del
> codice. Gli script di confronto sono riproducibili: vedi §7.

---

## 1. Risposta breve

Sì, abbiamo reimplementato molto. **Non è un errore di qualità** — il codice è
corretto quasi ovunque — ma **non fu nemmeno una decisione**, e il conto lo paghiamo
in tre punti misurati.

Cinque fatti, in ordine di importanza:

1. I **segnali rolling** ricalcolano una funzione scalare a ogni finestra, in un
   ciclo Python con copia di fetta: fino a **1 514× più lento di `pandas.rolling`, a
   valori identici**. Girano a ogni caricamento di grafico. È il guadagno più libero
   del progetto.
2. Il **CVaR è distorto verso il basso**: più basso di Riskfolio **2000 volte su
   2000**, in media −0,27%. Riskfolio implementa lo stimatore coerente di
   Acerbi-Tasche; noi lo stimatore plug-in ingenuo, con in più un off-by-one quando
   `α·T` è intero. Per una misura di rischio, sottostimare è la direzione peggiore.
3. Le **matrici** sono O(N²·T) in Python puro: 3,7 s su cento asset contro 0,2 ms di
   NumPy — e la pagina Asset Global ne seleziona esattamente cento di default.
4. Tutto il resto è **corretto**: coincide con Riskfolio fino all'ottavo decimale su
   VaR, max drawdown, Sharpe e risk contribution.
5. **Non tutto va migrato.** Sul max drawdown il nostro Python puro è **quattro volte
   più veloce di Riskfolio**, perché `MDD_Rel` è anch'essa interpretata. «Usare la
   libreria» non equivale a «usare il C».

I 17 plugin di analisi tecnica, invece, delegano alla libreria in modo impeccabile:
una chiamata ciascuno, zero aritmetica a mano (§5).

---

## 2. Cosa abbiamo installato e dove lo usiamo davvero

`Pipfile` dichiara **quattro** librerie di calcolo, non tre:

| Pacchetto | Versione | Natura | Usato in |
|---|---|---|---|
| `riskfolio-lib` | 7.0.1 | Python + NumPy | `risk_plugins/portfolio_optimization.py`, `risk/quant/riskfolio_worker.py` |
| `quantlib` | 1.43 | **C++** | `risk/quant/quantlib_worker.py` |
| `ta-lib` | 0.7.1 | **C** | mai importata a mano — arriva via `pandas_ta_classic` (§2.2) |
| `scipy` | * | C/Fortran | `utils/financial/roi_utils.py` — e sotto `riskfolio` (§2.1) |

Le due librerie di rischio servono **una sola analitica ciascuna** — rispettivamente
`portfolio_optimization` e `simulation`.

Le altre **sette** analitiche (`historical_kpi`, `correlation`,
`risk_contribution`, `historical_var`, `comparison`, `drawdown_summary`, `stress`)
non importano nulla. Verificato:

```bash
grep -rln "import numpy\|import pandas" app/services/risk_plugins/
# nessun risultato
```

### 2.1 `scipy`: un solo import nostro, ma non è opzionale

Domanda legittima: la usiamo davvero solo per il ROI? **Sì, direttamente.** Un unico
import in tutto il backend:

```bash
grep -rn "import scipy\|from scipy" backend/ --include=*.py
# backend/app/utils/financial/roi_utils.py:19: from scipy.optimize import newton as scipy_newton
```

Ma sarebbe sbagliato concluderne che `scipy` pesi 96 MB per una sola funzione di
Newton. **`scipy` è dipendenza obbligatoria di `riskfolio-lib`**, e con lei di tutta
la catena del solutore:

```text
Riskfolio-Lib  -> scipy>=1.10.0
cvxpy          -> scipy>=1.13.0
scs, clarabel, osqp, qdldl -> scipy
scikit-learn   -> scipy>=1.10.0   (usata da riskfolio per Ledoit-Wolf e OAS)
statsmodels    -> scipy
```

Quindi `scipy` gira **ogni volta che gira l'ottimizzatore**. Il nostro `newton` per
l'IRR è un passeggero, non il motivo del viaggio. Rimuoverla è impossibile finché
c'è riskfolio, e questo chiude anche l'ipotesi «togliamo scipy per alleggerire
l'immagine».

> **Dettaglio da non perdere.** Esiste un test che *vieta* a `scipy` di comparire nel
> percorso PAC: `test_pac_analyze_schemas.py:1486` elenca `"scipy"` tra i moduli
> proibiti e fallisce se risulta caricato. È una guardia sull'import pigro, scritta
> da qualcuno che sapeva quanto costa importarla. Vale la pena estendere la stessa
> guardia alle rotte rischio leggere.

### 2.2 TA-Lib: i plugin tecnici girano già in C

Questo è il pezzo che mancava al quadro. `pandas_ta_classic` **non calcola da sé**
quando TA-Lib è presente: la usa come motore. Verificato a runtime:

```text
pandas_ta_classic: 0.6.52
ta.Imports["talib"]: True
talib 0.7.1, estensione compilata .so -> C
ema, rsi, macd, bbands, atr, adx, stoch, obv: tutte instradano su talib
```

E i nostri plugin non si affidano al default: **16 su 17 passano `talib=True`
esplicito** (`adx`, `macd`, `ema`, `natr`, `atr`, `roc`, `cci`, `mfi`, `obv`,
`kama`, `sma`, `rsi`, `stoch_rsi`, `ppo`, `aroon`, `bollinger`).

Il diciassettesimo è `donchian.py`, e ha una buona ragione: **TA-Lib non ha il canale
di Donchian**. Ha `MIN` e `MAX`, non il composito. Là pandas_ta calcola in proprio
perché non c'è alternativa.

Il significato per noi è netto: nel dominio tecnico il progetto è già sul C, per
scelta consapevole e annotata nel codice. Il dominio rischio è l'unico rimasto in
Python interpretato.

### 2.3 La divisione è coerente, non accidentale

Il progetto ha **due sorgenti matematiche** e la linea che le separa è netta:

| Dominio | Sorgente | Conteggio |
|---|---|---|
| Analisi tecnica | `pandas_ta_classic` | 17 signal plugin su 25 |
| Rischio | `metrics.py`, Python puro | 6 signal plugin + 9 risk analytic |

I sei plugin che non importano una libreria sono **esattamente** i sei segnali di
rischio: `drawdown`, `rolling_beta`, `rolling_sharpe`, `rolling_volatility`,
`rolling_return`, `calendar_rolling_return`. Nessuna eccezione, nessun ibrido.

Quindi la sorpresa iniziale — «mi aspettavo che il drawdown usasse una delle due
librerie» — trova una risposta strutturale: il plugin drawdown **importa da
`risk/metrics.py` perché lì vive la matematica del rischio**, esattamente come
`rsi.py` importa da `pandas_ta_classic` perché lì vive la matematica dell'analisi
tecnica. Il plugin è un consumatore in entrambi i casi. Cambia solo il fornitore.

### 2.4 La scelta fu deliberata? No — e questo cambia tutto

> **Correzione, 16 Settembre 2026.** Una prima stesura di questo paragrafo citava il
> recap archiviato e concludeva: «Non è deriva: è una decisione presa, scritta e poi
> eseguita con disciplina». **Era una lettura sbagliata**, e va detto perché è
> esattamente il tipo di errore che un archivio dovrebbe impedire.

La frase citata è:

> NumPy solo per algebra, aggregazione e oracle;

Sta sotto l'intestazione **«§3.2 QuantLib P11»**, in un elenco che comincia con
«stato iniziale asset normalizzato a `1`», «griglia giornaliera, `dt=1/365`», «GBM
correlato multi-asset». È una regola per il **motore di simulazione**: dentro il
worker QuantLib, NumPy può fare algebra e aggregazione ma non l'evoluzione
stocastica.

Allo stesso modo «nessun adapter production NumPy/SciPy» (§1) si riferisce a un
**Monte Carlo alternativo basato su NumPy** che fu proposto e respinto in favore di
QuantLib — lo dice la riga successiva: «Le vecchie conclusioni *NumPy più veloce
quindi production* […] sono superseded».

**Nessuna delle due frasi parla di `metrics.py`.**

Cercando una decisione esplicita sul Python puro per le primitive di rischio si
trovano solo tre menzioni del file, tutte descrittive:

| Documento | Riga | Cosa dice |
|---|---|---|
| `plan-phase01Step3RollingRiskBackend` | 81 | nota di implementazione, il file è stato creato |
| `plan-phase01Step4MultiAssetRiskBackend` | 113 | nota di implementazione, il file è stato esteso |
| `report-phase01RiskBackendAuditAndRemediation` | 330 | «Le formule Risk sono già centralizzate in `risk/metrics.py`» |

L'audit constata la centralizzazione. Non ne discute il *linguaggio*.

Conclusione onesta: **lo stile in Python puro di `metrics.py` non fu mai deciso.
Successe.** Il file nacque scalare, in un contesto dove essere scalari andava
benissimo, e poi ha continuato a crescere per inerzia mentre il dominio d'uso
diventava matriciale e rolling.

Questo non toglie nulla alla qualità del codice — §3 mostra che è corretto. Cambia il
peso dell'argomento conservativo: non stiamo valutando se rovesciare una decisione
architetturale motivata. Stiamo valutando se **continuare** una scelta che nessuno ha
mai preso.

---

## 3. Verifica numerica: il nostro codice è corretto?

Metodo: stessa serie di rendimenti (750 giorni, seed 42), nostre funzioni contro
`riskfolio.RiskFunctions` e NumPy.

| Nostra funzione | Equivalente libreria | Nostro | Libreria | Esito |
|---|---|---|---|---|
| `historical_var_cvar` → VaR | `rk.VaR_Hist` | 0.018211567 | 0.01821157 | **identico** |
| `historical_var_cvar` → CVaR | `rk.CVaR_Hist` | 0.022233518 | 0.02228714 | **diverge 0,24%** |
| `summarize_drawdown.max_drawdown` | `rk.MDD_Rel` | −0.29853042 | 0.29853042 | **identico** (segno opposto) |
| — | `rk.MDD_Abs` | — | 0.33176209 | **non confrontabile**: usa `cumsum` |
| `sample_standard_deviation` | `np.std(ddof=1)` | 0.010831370 | 0.010831370 | **identico** |
| `annualized_sharpe` | `rk.Sharpe`×√252 | −0.29102537 | −0.29102537 | **identico** |
| `annualized_sortino` | `rk.Sharpe(rm='SLPM')`×√252 | −0.40607522 | −0.40580442 | differisce 0,07% |
| `risk_contributions_from_covariance` | `rk.Risk_Contribution` | `[0.00425593, 0.00221400, 0.00127603]` | identico | **identico** |
| `correlation_matrix` | `np.corrcoef` | — | — | valori identici |

**Nove confronti, sette coincidenze esatte.** Per un corpo di 661 righe scritto a
mano è un risultato notevole, e va detto: chi ha scritto `metrics.py` sapeva cosa
stava facendo.

### 3.1 Perché `MDD_Abs` non è confrontabile

Non è una differenza di convenzione, è una funzione diversa:

```python
prices = np.insert(np.array(a), 0, 1, axis=0)
NAV = np.cumsum(np.array(prices), axis=0)   # somma, non prodotto
```

`MDD_Abs` accumula i rendimenti **per somma**: è il drawdown di un conto in cui
guadagni e perdite non compongono. `MDD_Rel` usa il prodotto ed è quello che
corrisponde al nostro. Chi cercasse un giorno di «sostituire il nostro drawdown con
quello della libreria» prendendo il primo nome plausibile otterrebbe 0,33 invece di
0,30 — uno scarto dell'11% senza nessun errore visibile.

È la ragione per cui questa tabella esiste: **i nomi delle librerie non sono
autoesplicativi.**

### 3.2 Il CVaR: la nostra è sbagliata

> **Correzione, 16 Settembre 2026.** Una prima stesura concludeva «teniamo la
> nostra», motivandola con la spiegabilità. La verifica numerica successiva dice il
> contrario e va seguita la verifica.

La nostra (`metrics.py:608`):

```python
losses = sorted(max(-value, 0.0) for value in horizon_returns)
quantile_index = max(0, math.ceil(confidence_level * len(losses)) - 1)
value_at_risk = losses[quantile_index]
tail = [loss for loss in losses if loss >= value_at_risk]
conditional_value_at_risk = math.fsum(tail) / len(tail)
```

Media aritmetica delle perdite osservate oltre il VaR. È lo stimatore **plug-in
ingenuo**: traduce letteralmente `E[L | L ≥ VaR]` su un campione finito.

Riskfolio usa la forma **Rockafellar-Uryasev**. Ho verificato che coincide
esattamente con lo stimatore **coerente di Acerbi-Tasche**, che integra
l'osservazione frazionaria alla soglia:

```
ES_α = (1/αT) · [ Σ_{i=1..k} L_(i) + (αT − k)·L_(k+1) ],   k = ⌊αT⌋
```

Scarto misurato fra Riskfolio e Acerbi-Tasche: **< 10⁻¹²** su T = 733, 740, 750 e
1000. Non sono due formule simili, è la stessa formula.

**Il nostro stimatore è distorto verso il basso.** Su 2000 campioni indipendenti:

| Misura | Valore |
|---|---|
| Delta medio (nostro − Riskfolio) | **−5,97 · 10⁻⁵** ≈ **−0,27%** |
| Deviazione standard del delta | 8,77 · 10⁻⁶ |
| Volte in cui il nostro è più basso | **2000 / 2000** |

Media a sette deviazioni standard dallo zero, e nessuna singola inversione in
duemila prove. Non è rumore di campionamento: è una distorsione strutturale.

**Per una misura di rischio, sottostimare è la direzione peggiore in cui sbagliare.**

### 3.2.1 Perché il nostro è più basso

Due cause distinte, che si sommate.

La prima è il denominatore. Con T = 750 e α = 0,05 la coda nominale vale `α·T` =
37,5 osservazioni. Noi dividiamo per il conteggio reale, 38; Acerbi-Tasche divide per
37,5 e pesa l'ultima osservazione per la sola frazione 0,5. Poiché l'ultima
osservazione della coda è la **più piccola** delle perdite in coda, contarla intera
abbassa la media.

La seconda è un **off-by-one all'indice del quantile**. Noi calcoliamo
`ceil(0.95·T) − 1` su perdite ordinate crescenti; Riskfolio calcola `ceil(0.05·T) − 1`
su rendimenti ordinati crescenti. I due coincidono **solo quando `0,05·T` non è
intero**. Verificato:

| T | α·T | nostro CVaR | Riskfolio | delta |
|---:|---:|---:|---:|---:|
| 740 | 37,00 (intero) | 0.02150704 | 0.02161077 | −1,04·10⁻⁴ |
| 760 | 38,00 (intero) | 0.02308410 | 0.02323598 | −1,52·10⁻⁴ |
| 800 | 40,00 (intero) | 0.02218756 | 0.02229035 | −1,03·10⁻⁴ |
| 733 | 36,65 (frazionario) | 0.02194336 | 0.02198864 | −4,53·10⁻⁵ |

Quando `α·T` è intero prendiamo la 38ª perdita invece della 37ª: **lo scarto
raddoppia proprio nei casi che sembrerebbero più semplici.**

### 3.2.2 Il contratto non è colpevole, l'implementazione sì

Il contratto matematico archiviato
([`contract-phase01RiskMetricsMathematical.md`](./_archive-backendFirst-G0G6/contract-phase01RiskMetricsMathematical.md),
riga 538) specifica:

```
CVaR_α(L) = E[L | L ≥ VaR_α(L)]          (media della coda)
```

Questa definizione è **corretta** — per una distribuzione continua. Su un campione
finito la stessa scrittura ammette più stimatori, e ne è stato scelto uno senza che
la scelta fosse posta come tale.

Il contratto definiva il bersaglio. L'implementazione ha preso la mira più ovvia,
che non è quella coerente.

### 3.2.3 E la spiegabilità?

L'argomento a favore del nostro stimatore era che «media delle giornate peggiori» si
spiega in una frase, mentre dividere per 37,5 osservazioni quando ne hai 38 no.

**L'argomento non regge**, per due motivi.

Primo: la frase resta vera. Acerbi-Tasche *è* la media delle giornate peggiori, con
l'ultima contata in proporzione a quanto rientra nel 5%. Chi non vuole il dettaglio
legge la frase; chi lo vuole trova la pagina wiki (Q5).

Secondo, e decisivo: lo scarto è **0,27%**. Nessun utente lo vedrà mai. Stavamo
barattando correttezza contro una chiarezza che nessuno percepisce.

### 3.2.4 Non è una questione di C++

Va detto perché è una trappola naturale: le funzioni di Riskfolio **non sono
compilate**. `inspect.getsourcefile` le colloca in
`riskfolio/src/RiskFunctions.py` — Python e NumPy, come il nostro.

Anzi, sulla pura aritmetica in virgola mobile **il nostro è marginalmente più
preciso**: `math.fsum` esegue una sommatoria esattamente compensata, mentre
`np.sum` usa una sommatoria a coppie che è ottima ma non esatta.

La conclusione «migrare a Riskfolio» è giusta. La ragione non è la precisione
numerica: è che **stiamo stimando la grandezza sbagliata**.

### 3.3 Una nota sul pavimento a zero

`max(-value, 0.0)` significa che il VaR non può essere negativo. Se un portafoglio
salisse così stabilmente da avere il 5° percentile positivo, noi mostreremmo `0`
mentre Riskfolio mostrerebbe un valore negativo — un «guadagno a rischio».

È una scelta di presentazione difendibile: «non puoi perdere meno di niente». Va
però ricordata quando si disegna l'istogramma (D16), perché la linea del VaR in quel
caso cadrebbe sullo zero e non su un quantile dei dati.

---

## 4. Il costo vero: complessità, non correttezza

### 4.0 Confronto a tre vie sulle funzioni scalari

Stessa serie di 750 punti, valore e tempo insieme:

| Funzione | nostro | NumPy | Riskfolio | ms nostro | ms libreria |
|---|---:|---:|---:|---:|---:|
| VaR 95% | 0.01699629 | 0.01699629 | 0.01699629 | 0,535 | 0,030 |
| CVaR 95% | 0.02147076 | — | **0.02153042** | 0,518 | 0,057 |
| max drawdown | 0.11786158 | — | 0.11786158 | **0,208** | **0,914** |
| std campionaria | 0.01084244 | 0.01084244 | — | 0,108 | 0,006 |
| Sharpe annualizzato | 0.83347797 | — | 0.83347797 | 0,201 | 0,024 |

Tre osservazioni, in ordine di sorpresa crescente.

**Sono tutte sotto il millisecondo.** Su una serie singola il divario relativo non ha
alcun significato pratico: 0,5 ms contro 0,03 ms sono entrambi invisibili dentro una
richiesta HTTP.

**Sul max drawdown il nostro Python puro batte Riskfolio di oltre quattro volte.**
Non è un caso: `MDD_Rel` è anch'essa un ciclo Python interpretato — l'ho letta, ha la
stessa struttura di `MDD_Abs` riportata in §3.1. È il correttivo più importante a
tutto questo documento: **«usare la libreria» non equivale a «usare il C»**, e chi
migrasse in blocco per velocità peggiorerebbe questa riga.

**La migrazione del CVaR non è una questione di prestazioni.** È l'unica riga dove il
valore differisce, ed è l'unica ragione per cui va toccata.

### 4.1 Dove il divario diventa reale

Il divario conta quando la funzione scalare viene invocata **molte volte**. Succede
in due modi, entrambi presenti nel codice.

**Matrici — O(N²·T).** `correlation_matrix`, `covariance_matrix` e il doppio ciclo di
`risk_plugins/correlation.py:72`:

| Dimensione | `correlation_matrix` | `np.corrcoef` | Rapporto |
|---|---:|---:|---:|
| 10 asset × 750 giorni | 37 ms | ~0 ms | 1 025× |
| 30 asset × 750 giorni | 340 ms | 0,1 ms | 3 143× |
| 60 asset × 750 giorni | 1 330 ms | 0,1 ms | 11 612× |
| **100 asset × 750 giorni** | **3 682 ms** | 0,2 ms | **18 640×** |
| 100 asset × 2500 giorni | 12 832 ms | 0,5 ms | 24 698× |

| Dimensione | `covariance_matrix` | `np.cov` | Rapporto |
|---|---:|---:|---:|
| 100 asset × 750 giorni | 1 408 ms | 0,2 ms | 8 097× |
| 100 asset × 2500 giorni | 4 871 ms | 0,5 ms | 9 990× |

**Finestre mobili — O(T·W).** È il caso più importante, e non era nel mirino.
`risk/signal_helpers.py:69-84`:

```python
def rolling_single_values(returns, window, metric):
    for end_index in range(len(returns)):
        if end_index + 1 < window:
            ...
        value = metric(returns[end_index + 1 - window : end_index + 1])
```

Un ciclo Python che a ogni passo **copia una fetta** e richiama la funzione scalare.
Confronto con `pandas.Series.rolling`, che calcola la stessa cosa in C:

| Serie × finestra | nostro | pandas | Rapporto | Valori identici |
|---|---:|---:|---:|:---:|
| 750 × 20 | 2,89 ms | 0,068 ms | 43× | **sì** |
| 750 × 60 | 6,80 ms | 0,059 ms | 115× | **sì** |
| 2500 × 60 | 24,11 ms | 0,084 ms | 286× | **sì** |
| 2500 × 250 | 87,14 ms | 0,089 ms | 975× | **sì** |
| 5000 × 250 | 182,62 ms | 0,121 ms | **1 514×** | **sì** |

`np.allclose` su tutti i valori definiti: **identici**. Nessuna scelta da fare,
nessuna convenzione da discutere, nessun rischio semantico sulla matematica.

E la differenza con le matrici è la frequenza. La matrice di correlazione vive nella
pagina di laboratorio di Asset Global. **I segnali rolling girano a ogni caricamento
di grafico**, su ogni asset, per ogni utente.

### 4.2 Perché proprio cento asset

`AssetSetRiskPanel.svelte` fa `.slice(0, 100)` all'apertura. **Il default della
pagina Asset Global è la riga peggiore della tabella.**

Questo lega due problemi che finora erano separati. Nel documento
[`05`](./05-grammatica-visiva-e-rappresentazioni.md) §8 il seed a cento asset era
censito come difetto di *usabilità* — matrice illeggibile, novantaquattro click per
disfarla. È anche un difetto di *prestazioni*, e la correzione è la stessa: D19,
selezione persistita con fallback agli asset posseduti.

### 4.3 L'event loop non è bloccato, ma la GIL sì

Prima verifica istintiva: un ciclo Python da 3,7 secondi dentro un `async def`
congelerebbe l'applicazione. **Controllato: non accade.**
`RiskAnalytic.execute` (`risk/base.py:242`) avvolge ogni `compute`:

```python
async def execute(self, params, context) -> RiskComputation:
    """Execute lightweight analytics without blocking the event loop."""
    return await asyncio.to_thread(self.compute, params, context)
```

L'architettura è corretta e la regola async del progetto è rispettata.

Resta però una differenza che `to_thread` non cancella: **il Python puro trattiene
la GIL, NumPy la rilascia** entrando nel BLAS. Tre secondi e sette di ciclo
interpretato in un thread non bloccano l'event loop, ma contendono l'interprete con
ogni altra richiesta del processo.

È un sintomo peggiore di un freeze, perché non si presenta come un errore: si
presenta come «ogni tanto l'app è lenta», senza una richiesta colpevole evidente.

---

## 5. Audit dei signal plugin: delegano davvero?

Dire «i 17 plugin di analisi tecnica importano `pandas_ta_classic`» non basta:
importare una libreria e poi rifare i conti a mano è un classico. Verificato.

### 5.1 I 17 di analisi tecnica: delega pulita ✅

| Plugin | Righe | Chiamate `ta.*` |
|---|---:|---:|
| `rsi.py` | 287 | 1 |
| `macd.py` | 254 | 1 |
| `adx.py` | 229 | 1 |
| `bollinger.py` | 180 | 1 |
| `atr.py` | 176 | 1 |
| `ema.py` | 176 | 1 |
| `obv.py` | 166 | 1 |
| `sma.py` | 158 | 1 |

**Esattamente una chiamata per plugin.** Le restanti duecentottanta righe sono
schema dei parametri, metadati di catalogo, validazione e rilevamento degli eventi
(incroci, soglie) — non matematica.

Ricerca di aritmetica a mano dopo la chiamata alla libreria
(`statistics.`, `math.sqrt`, `math.fsum`, `sum(`, `/ len(`, `** 0.5`, `mean(`) su
tutti i plugin: **un solo riscontro**, e non è matematica —

```python
"unavailable_points": sum(unavailable_counts.values()),
```

un conteggio di punti mancanti in `calendar_rolling_return.py:231`.

**Verdetto: nessun debito, ed è più forte di così.** Non solo delegano — delegano al
**C**. Sedici plugin su diciassette passano `talib=True` esplicito, quindi
`pandas_ta_classic` instrada su TA-Lib 0.7.1 compilata (§2.2). L'unico senza è
`donchian.py`, perché TA-Lib il canale di Donchian non ce l'ha.

Questi plugin sono il modello. Non vanno toccati.

### 5.2 I 6 di rischio: delegano a `metrics.py`, che è scalare

| Plugin | Importa da `risk/metrics.py` |
|---|---|
| `drawdown.py` | `underwater_drawdown` |
| `rolling_beta.py` | `beta` |
| `rolling_sharpe.py` | `annualized_sharpe` |
| `rolling_volatility.py` | `annualized_volatility` |
| `rolling_return.py` | `compounded_return` |
| `calendar_rolling_return.py` | — (calendario proprio) |

Anche questi delegano correttamente: nessuno reimplementa in loco. Il problema non è
il plugin, è che **la funzione delegata è scalare e viene chiamata in un ciclo** —
il caso O(T·W) di §4.1, fino a 1 514 volte più lento a parità esatta di valori.

Quindi la domanda «i segnali usano davvero le librerie?» ha due risposte diverse:

- analisi tecnica: **sì, pienamente**;
- rischio: **delegano bene a una sorgente che non è vettorializzata**.

Il difetto non sta nel confine fra plugin e matematica. Sta un piano sotto.

---

## 6. Pesi reali dei pacchetti — chiude Q2

Q2 chiedeva quanto pesasse Riskfolio nell'immagine da 2,78 GB, per decidere se
rimuoverlo insieme a `portfolio_optimization` (differita in `TODO_FUTURI.md`).

Misurato sui pacchetti installati:

| Pacchetto | Peso | Note |
|---|---:|---|
| `scipy` | 96,6 MB | serve a `roi_utils`, non al rischio |
| `pandas` | 66,8 MB | `pandas_ta_classic`, `yfinance` |
| `QuantLib` | 59,6 MB | solo `simulation` |
| `numpy` | 32,2 MB | |
| `cvxpy` | 10,1 MB | dipendenza Riskfolio |
| **`riskfolio`** | **2,5 MB** | |
| `clarabel` | 2,4 MB | solver Riskfolio |
| `osqp` | 1,1 MB | solver Riskfolio |
| `scs` | 0,3 MB | solver Riskfolio |

Riskfolio con l'intera closure di solver: **circa 16 MB su 2 780**, lo 0,6%.
Rimuoverlo non risolve niente.

**Q2 chiusa in negativo: Riskfolio resta installata.** La premessa della domanda era
sbagliata e solo la misura poteva dirlo.

---

## 7. Piano di migrazione

### 7.-1 Il piano in una pagina

Questo capitolo è stato corretto tre volte durante l'analisi, e chi lo legge di
seguito vede le correzioni prima della conclusione. Questa è la versione valida;
tutto il resto del capitolo la motiva.

**Il criterio** (D36, che ha revocato D30): non è la velocità, è **quanta matematica
possediamo**. Ogni formula scritta da noi è una formula che possiamo sbagliare da
soli — e il CVaR dimostra che succede, in silenzio, per anni.

| # | Cosa | Con cosa | Perché | Rischio |
|---|---|---|---|---|
| **M4** | Test-oracolo su `metrics.py` | Riskfolio | Rete di sicurezza per tutto il resto | nullo — solo test |
| **M2** | `historical_var_cvar`, parte CVaR | `CVaR_Hist` | **Il nostro è distorto**: −0,27%, 2000 volte su 2000 | i numeri mostrati cambiano |
| **M1** | `rolling_single_values`, `rolling_pair_values` | `pandas.rolling` | Fino a **1 514×** a valori identici, su ogni grafico | semantica dei buchi |
| **M3** | `correlation_matrix`, `covariance_matrix` | **NumPy** | 3 682 ms → 0,2 ms su cento asset | `coverage`, e `None` contro `nan` |
| **M5** | `risk_contributions_from_covariance` | `Risk_Contribution(rm="MV")` | Doppione verificato identico | serve portare i rendimenti a quel livello |
| **M6** | I nove composti che la libreria non ha | **NumPy / SciPy** | Non esiste ragione per tenerli in `math` puro | segno, `None`, buchi nei dati |

**L'ordine è vincolato, non arbitrario.** M4 va per prima perché è la rete sotto tutte
le altre: senza oracolo, M1 e M3 sono riscritture non verificate di formule che
nessuno ha mai confrontato con un riferimento esterno. M2 subito dopo, perché è
l'unica che corregge un errore invece di spostare del codice.

**M6 sostituisce la vecchia lista «cosa NON migrare».** Il fatto che Riskfolio non
abbia una funzione non è una ragione per lasciarla scritta a mano in Python
interpretato: significa solo che il fornitore è un altro. Nove funzioni —
`summarize_drawdown`, `drawdown_episodes`, `pairwise_correlation`,
`comparison_summary`, `wealth_index`, `period_returns_from_cumulative`,
`horizon_compounded_returns`, `current_buy_and_hold_returns`, `annualized_sortino` —
passano a NumPy mantenendo firma e semantica. `np.maximum.accumulate` fa il picco
progressivo in una riga, `np.cumprod` fa l'indice di ricchezza, `np.corrcoef` con
maschera fa la correlazione a coppie. Restano **nostre** — è la composizione che ci
appartiene, non l'aritmetica — ma sotto oracolo M4 e vettorializzate.

**Cosa non è migrazione affatto**: le acquisizioni (NEA + diversification ratio,
`Sharpe(rm=)`, UCI) sono funzionalità nuove, vivono in Q7, e non entrano in questo
piano.

**Regola trasversale, da applicare a ogni sostituzione**: prima dimostrare
numericamente che i due valori coincidano. `MDD_Abs`, `numBins`, il Sortino e
`Kurtosis` sono **quattro** casi, trovati in questa sola analisi, in cui il nome
combaciava e la grandezza no.

---

### 7.0 Perché NumPy e pandas se abbiamo Riskfolio

Obiezione giusta e va risolta con l'inventario dell'API, non con le preferenze. Ho
enumerato cosa Riskfolio 7.0.1 espone davvero.

**Per i segnali rolling (M1): Riskfolio non ha la funzione.**

```text
riskfolio.src.RiskFunctions -> funzioni con "roll"/"window" nel nome: NESSUNA
```

Non è una mancanza: è la sua natura. Riskfolio è una libreria di **ottimizzazione di
portafoglio**. Prende un campione intero e produce un numero o dei pesi. La finestra
mobile — «la volatilità degli ultimi 20 giorni, giorno per giorno» — è un concetto di
*serie storica*, e la libreria delle serie storiche è pandas. Qui pandas non è un
ripiego rispetto a riskfolio: è **l'unica delle due che abbia la capacità**.

**Per le matrici (M3): Riskfolio ce l'ha, ed è letteralmente NumPy.**

`ParamsEstimation.covar_matrix(X, method='hist')` contiene, nel sorgente:

```python
cov = np.cov(X, rowvar=False)
```

Misurato, con risultati identici (`np.allclose` vero in tutti i casi):

| Caso | Riskfolio | NumPy | Note |
|---|---:|---:|---|
| 10 asset × 750d | 0,451 ms | 0,050 ms | |
| 60 asset × 750d | 0,238 ms | 0,117 ms | |
| 100 asset × 750d | 0,533 ms | 0,207 ms | il default della pagina |
| 100 asset × 2500d | 0,754 ms | 0,540 ms | |

Passare da riskfolio costa **2-3×** in più e obbliga a costruire un `DataFrame`
(rifiuta un array: `ValueError: X must be a DataFrame`). Rispetto ai 3 682 ms
attuali entrambe le strade sono una vittoria totale, quindi la differenza è
irrilevante — ma non c'è alcun vantaggio nel guscio.

> **Però qui Riskfolio offre qualcosa che NumPy non ha, e non è la velocità.**
> `covar_matrix` espone **quindici stimatori**: `ledoit`, `oas`, `shrunk`, `gl`,
> `jlogo`, `gerber1`, `gerber2`, `ewma1/2`, `semi`, più tre metodi di *denoising*.
>
> Ledoit-Wolf è il più noto: restringe la matrice campionaria verso una struttura
> semplice. Serve perché con cento asset e 750 giorni si stimano 5 050 parametri da
> 75 000 osservazioni, e la matrice risultante è **instabile** — piccole variazioni
> nei dati muovono molto i risultati. Misurato: 25,4 ms contro 0,2 ms, scarto
> massimo 1,2·10⁻⁵ dalla storica.
>
> È un miglioramento di **qualità della stima**, non di prestazioni, e costa cento
> volte il tempo. Non entra in M3, che è un intervento di velocità a comportamento
> invariato. Va discusso a parte, quando la pagina correlazioni avrà una direzione
> (→ TODO, vedi `04`).

Nota: Riskfolio **non** ha uno stimatore di correlazione diretto. Ha `cov2corr` per
convertire. Quindi la via sarebbe `cov2corr(covar_matrix(df))` — due chiamate contro
un `np.corrcoef`.

> **Conclusione operativa: M3 si fa in NumPy.** Riskfolio, per la matrice storica,
> è NumPy incapsulato: stessi numeri, 2-3× di tempo, obbligo di `DataFrame`, e sulla
> correlazione nemmeno una funzione diretta. Nessun vantaggio, tre svantaggi.
>
> Riskfolio **non viene scartato**: entra quando servirà uno stimatore che NumPy non
> ha. Poiché NumPy resta confinato dentro `covariance_matrix`, quel passaggio è la
> sostituzione di un corpo di funzione (vedi M3).

### 7.0.1 I quindici stimatori: che problema risolvono

Vale la pena capirli, perché il problema che affrontano **ce l'abbiamo già** e tre di
essi sono **già cablati nel progetto** (lo scopro sotto).

**Il problema.** Una matrice di covarianza su `N` asset contiene `N(N+1)/2` numeri
distinti da stimare. Misurato sui nostri casi reali:

| Caso | Parametri da stimare | Osservazioni | Rapporto T/N |
|---|---:|---:|---:|
| 10 asset × 750g | 55 | 7 500 | 75,0 |
| 60 asset × 750g | 1 830 | 45 000 | 12,5 |
| **100 asset × 750g** | **5 050** | **75 000** | **7,5** ⚠️ |
| 100 asset × 250g | 5 050 | 25 000 | **2,5** ⚠️ |

La regola pratica è che sotto un rapporto di dieci la stima diventa fragile. **Il
default della pagina Asset Global è 7,5.** Con un solo anno di storia, 2,5.

**Perché «fragile» e non solo «imprecisa».** Il rumore non sbaglia a caso: deforma la
matrice in modo *sistematico*. Gli autovalori più grandi vengono sovrastimati, i più
piccoli schiacciati verso lo zero (fenomeno di Marchenko-Pastur). Misurato sugli
stessi dati generati dallo stesso mercato:

```text
100 asset,  750 giorni -> rapporto autovalore max/min = 407
100 asset, 5000 giorni -> rapporto autovalore max/min = 228
```

Stesso mercato, stessa struttura vera: **la differenza è tutta rumore di stima**.

**Il caso patologico, che non è teorico.** Quando gli asset superano i giorni la
matrice diventa *singolare*:

```text
100 asset, 60 giorni -> 41 autovalori su 100 sono <= 0
                     -> matrice NON invertibile
con Ledoit-Wolf      ->  0 autovalori <= 0  -> invertibile
```

E qui c'è la conseguenza concreta per noi, verificata nel codice:

```python
# risk/quant/riskfolio_worker.py:146
if minimum_eigenvalue < -1e-10:
    raise RuntimeError("Riskfolio covariance is not positive semidefinite")

# risk/quant/quantlib_worker.py:33
if float(np.min(eigenvalues)) < (-_PSD_RELATIVE_TOLERANCE * scale):
    raise ValueError("simulation covariance must be positive semidefinite")
```

Un utente con molti asset e poca storia **non ottiene numeri imprecisi: ottiene un
errore**. Gli stimatori restretti sono la cura di quell'errore.

> Nota importante: `risk_contributions_from_covariance` calcola solo `Σw`, un
> prodotto matrice-vettore. **Non inverte nulla**, quindi non è esposta a questo
> problema. La singolarità colpisce ottimizzazione e simulazione, non la
> scomposizione del rischio.

**Le cinque famiglie.** I quindici metodi non sono quindici idee, sono cinque:

| Famiglia | Metodi | Idea in una frase |
|---|---|---|
| **Restringimento** | `ledoit`, `oas`, `shrunk` | Mescola la matrice campionaria con una struttura semplice: accetta un po' di distorsione in cambio di molta meno varianza |
| **Ponderazione temporale** | `ewma1`, `ewma2` | Il passato recente pesa di più: la volatilità di oggi somiglia a quella di ieri, non a quella di tre anni fa |
| **Robustezza** | `gerber1`, `gerber2` | Conta *quante volte* due asset si muovono insieme oltre una soglia, invece di moltiplicare gli scarti: un singolo giorno estremo non domina la stima |
| **Denoising** | `fixed`, `spectral`, `shrink`, `jlogo` | Separa gli autovalori «segnale» da quelli «rumore» e sostituisce i secondi con la loro media |
| **Asimmetria** | `semi` | Usa solo i movimenti al ribasso: misura il co-crollo, non la co-variazione |

**Misurato fuori campione** — stima su 750 giorni, confronto con la covarianza
realizzata nei 750 successivi, 100 asset:

| Stimatore | Tempo | Errore vs futuro |
|---|---:|---:|
| `shrunk` | 3,2 ms | **0,000790** |
| `ledoit` | 3,6 ms | 0,000976 |
| `oas` | 3,2 ms | 0,000978 |
| `hist` | 0,5 ms | 0,001022 |
| `ewma1` | 870,5 ms | 0,002742 |
| `gerber1` | **19 395 ms** | 0,003251 |
| `semi` | 1,1 ms | 0,003920 |

**Come leggere questa tabella senza farsi ingannare**, perché due righe sono
ingiuste:

- `semi` e `gerber1` sembrano pessimi, ma **misurano un'altra cosa**. `semi` stima la
  co-variazione *al ribasso*: confrontarla con la covarianza piena è come dare
  dell'impreciso a un termometro perché non misura la pressione.
- `gerber1` è progettato per resistere agli **outlier**, e i miei dati sintetici sono
  gaussiani puliti: non ha nulla da cui difendere. Su dati veri con crolli
  improvvisi il confronto cambierebbe.
- I 19,4 secondi di `gerber1` invece **sono un fatto** e vanno ricordati: è O(N²·T)
  con confronti a soglia. Se mai entrasse, va in un worker, mai in linea.
- Il guadagno dei restringimenti sull'errore è reale ma **modesto**: da 0,001022 a
  0,000790, circa il 23%. Non è una rivoluzione. **Il loro vero valore è la riga
  precedente: rendere invertibile una matrice che non lo sarebbe.**

**E qui la scoperta.** Cercando dove collegarli, ho trovato che **ci sono già**:

```python
# risk/quant/riskfolio_worker.py:28
_ESTIMATOR_METHODS = {
    RiskCovarianceEstimator.HISTORICAL: "hist",
    RiskCovarianceEstimator.LEDOIT_WOLF: "ledoit",
    RiskCovarianceEstimator.OAS: "oas",
}
```

`portfolio_optimization.py:57` li espone come parametro scelto dall'utente. Tre dei
quindici sono cablati, tipizzati e raggiungibili dall'API.

Questo chiude il ragionamento meglio di qualunque argomento mio: **chi scrisse quel
codice aveva già tracciato la linea giusta**. Gli stimatori restretti stanno
nell'ottimizzatore — dove la matrice va *invertita* e dove il risultato è
*prescrittivo* — e non stanno nella pagina correlazioni, dove il compito è
*descrivere* cosa hanno fatto i prezzi.

Se la vista correlazioni mostrasse una matrice restretta, mostrerebbe numeri che i
prezzi non hanno mai prodotto, senza dirlo. Per una pagina che risponde a «sono
diversificato come credo?» sarebbe una bugia elegante.

**Conseguenza per il piano**: nessun lavoro nuovo qui. M3 resta NumPy a comportamento
invariato; gli stimatori restano dove già sono; il TODO copre solo l'ipotesi futura
in cui la pagina correlazioni diventi prescrittiva.

**Per il binning (§7.2): Riskfolio lo espone, ma non è suo.**

`AuxFunctions.freedman_bin_width` esiste, e `inspect.getmodule` dice da dove viene:
**`astropy.stats.histogram`**. Riskfolio la ri-esporta. Verificato che dia lo stesso
risultato di NumPy: larghezza 0,00307 → 21 bin, esattamente i 21 di
`np.histogram_bin_edges(x, bins='fd')`.

Attenzione invece a `AuxFunctions.numBins`: il nome inganna. La docstring dice
«optimal number of bins for discretization of **mutual information and variation of
information**». È la formula di Hacine-Gharbi per l'entropia, **non** per un
istogramma di rendimenti. Usarla qui darebbe un numero plausibile e sbagliato — la
stessa trappola di `MDD_Abs` (§3.1).

**Per l'analisi tecnica: la libreria giusta è già in uso, ed è C.**

Qui la domanda si rovescia. Non «perché pandas_ta invece di riskfolio», ma: pandas_ta
instrada su **TA-Lib**, C compilato, e i plugin lo chiedono esplicitamente
(§2.2). Riskfolio non ha né RSI né MACD né Bollinger: sono domini diversi.

**Riepilogo — quale libreria per quale mestiere:**

| Mestiere | Libreria | Perché lei |
|---|---|---|
| Indicatori tecnici | `pandas_ta_classic` → **TA-Lib (C)** | è l'unica che li ha; già in uso |
| Finestre mobili | **pandas** | Riskfolio non ha rolling; pandas è il dominio serie storiche |
| Algebra di matrici | **NumPy** | Riskfolio incapsula `np.cov` con 2-3× di sovrapprezzo |
| Stimatori robusti di covarianza | **Riskfolio** | Ledoit-Wolf, Gerber, denoising: NumPy non ce li ha |
| Misure di rischio scalari | **Riskfolio** | CVaR coerente, EVaR, RLVaR: definizioni accademiche già corrette |
| Ottimizzazione di portafoglio | **Riskfolio** (+ cvxpy, scipy) | è il suo mestiere |
| Simulazione di processi | **QuantLib (C++)** | già in uso nel worker |
| Bin dell'istogramma | **NumPy** | `bins='fd'` nativo; riskfolio ri-esporta astropy |

Quattro interventi, in ordine di rapporto valore/rischio.

### M1 — Segnali rolling a pandas 🔴 priorità massima

**Cosa**: `risk/signal_helpers.py:69-108` (`rolling_single_values`,
`rolling_pair_values`) passa da ciclo Python a operazioni `pandas.rolling`.

**Perché primo**: gira a ogni caricamento di grafico, su ogni asset, per ogni utente.
Da 43× a 1 514× più veloce **a valori identici** (`np.allclose` verificato). Nessuna
convenzione da scegliere, nessun rischio matematico.

**Mappatura**:

| Segnale | Forma vettorializzata |
|---|---|
| `rolling_volatility` | `s.rolling(W).std(ddof=1) * sqrt(ann)` |
| `rolling_sharpe` | media e deviazione standard rolling |
| `rolling_beta` | `s.rolling(W).cov(b) / b.rolling(W).var()` |
| `rolling_return` | `expm1(log1p(s).rolling(W).sum())` — **non** `.apply(prod)`, che resta interpretato |
| `drawdown` | già O(T): `np.maximum.accumulate` |

**Il vero costo non è la matematica, è la semantica dei buchi.** L'attuale ciclo
restituisce `None` per le finestre indefinite e ne tiene il conteggio
(`undefined_windows`), che alimenta un warning utente. `annualized_sharpe` restituisce
`None` quando la volatilità è nulla; pandas produrrebbe `inf` o `NaN`. **La versione
vettorializzata deve riprodurre esattamente `None` e il conteggio**, altrimenti
sparisce un avviso senza che nessun test se ne accorga.

È qui che va speso il tempo di revisione, non sulle formule.

### M2 — CVaR allo stimatore coerente 🔴 correttezza

**Cosa**: `historical_var_cvar` adotta lo stimatore Acerbi-Tasche / Rockafellar-Uryasev,
e l'indice del quantile smette di essere off-by-one a `α·T` intero (§3.2.1).

**Perché**: sottostimiamo del 0,27%, 2000 volte su 2000. Non è velocità, è la
grandezza sbagliata.

**Come**: la formula sono quattro righe di NumPy e non richiede di chiamare Riskfolio
a runtime — ma **Riskfolio va usata come oracolo nel test** (M4), che è il modo di
non sbagliarla una seconda volta.

**Attenzione al pavimento a zero.** `max(-value, 0.0)` va discusso separatamente:
è una scelta di presentazione, non fa parte di questo difetto, e va mantenuta o
rimossa consapevolmente.

### M3 — Matrici a NumPy 🟠

**Decisione: NumPy, non Riskfolio.** Quattro ragioni, in ordine.

1. **Riskfolio qui non aggiunge matematica.** `covar_matrix(X, method='hist')`
   contiene `cov = np.cov(X, rowvar=False)`. È NumPy con un guscio.
2. **Costa di più**: 2-3× di tempo, e obbliga a costruire un `DataFrame` per ogni
   chiamata (rifiuta un array: `ValueError: X must be a DataFrame`).
3. **Sulla correlazione non ce l'ha proprio**: servirebbe
   `cov2corr(covar_matrix(df))`, due chiamate contro un `np.corrcoef`.
4. **M3 è un intervento a comportamento invariato.** Cambia il tempo, non i numeri.
   Riskfolio entrerebbe in gioco solo con gli stimatori restretti — che i numeri li
   cambiano, e per questo stanno in un TODO separato (§7.0).

**Cosa**: `correlation_matrix`, `covariance_matrix` e il doppio ciclo di
`risk_plugins/correlation.py:72`.

**Perché**: da 1 025× a 24 698×, e NumPy rilascia la GIL dove il Python puro la
trattiene (§4.3).

**La firma non cambia — ed è il punto.** Oggi:

```python
def covariance_matrix(series: Sequence[Sequence[float]]) -> list[list[float]]
def correlation_matrix(series: Sequence[Sequence[float]]) -> list[list[float | None]]
```

Entrano liste di float, escono liste di liste. NumPy resta **dentro** la funzione e
non risale mai nei plugin. Questa è la giuntura che rende reversibile la scelta: il
giorno in cui servisse Ledoit-Wolf, si sostituisce il corpo di `covariance_matrix` e
nient'altro nel progetto se ne accorge. Scegliere NumPy ora non chiude la porta a
Riskfolio dopo.

**Il costo nascosto**: `pairwise_correlation` restituisce anche `observations` e
`coverage`, che gestiscono i calendari disallineati. La versione vettorializzata deve
produrre gli **stessi** valori di copertura, non solo gli stessi coefficienti. Va
fatta con una maschera di validità, non con `np.corrcoef` crudo.

Si noti il tipo di ritorno: `float | None`. Dove la varianza è nulla
`pearson_correlation` dà `None`, `np.corrcoef` dà `nan`. Stessa classe di problema
dei buchi in M1 — la matematica è identica, la semantica dell'indefinito no, e va
ritradotta a mano.

Più delicata di M1, e serve meno spesso. Da fare dopo.

### M4 — Riskfolio come oracolo di test ⭐ da fare per primo in assoluto

`test_risk_metrics.py` (297 righe) importa solo `math`. Verifica proprietà interne —
additività del PCTR, identità con TE nullo e beta unitario — che sono test *buoni*,
ma tutti autoreferenziali: **nessun controllo indipendente**.

Riskfolio è già installata e già pagata in spazio (§6). Venti righe danno il
confronto incrociato che oggi manca.

**Va scritto prima di M1-M3**, non dopo: è la rete che rende sicure le altre tre
migrazioni. Ed è lo stesso strumento che ha scoperto il difetto del CVaR.

### Cosa NON migrare 🟢 — e perché il criterio della velocità era sbagliato

Questa sezione diceva: «restano in Python perché sono sotto il millisecondo, e sul
max drawdown siamo perfino quattro volte più veloci». **L'argomento non regge**, e
l'obiezione che lo ha smontato è di principio: *se una cosa sta in libreria, va usata
la libreria*.

Ha ragione, e la prova più forte è in questo stesso documento. Il CVaR lo abbiamo
scritto noi, ed è **sbagliato** (§3.2) — non per incapacità, ma perché la matematica
scritta in casa sbaglia in silenzio: nessun test fallisce, nessun utente se ne
accorge, lo scarto è dello 0,27%. La velocità era il criterio sbagliato. Il criterio
giusto è **quanto codice matematico possediamo**, perché ogni riga che possediamo è
una riga che possiamo sbagliare da soli.

Però «usare la libreria» non è un'istruzione sola: sono **tre casi diversi**, e
confonderli fa danni.

#### Caso A — Doppioni veri: migrare ✅

La libreria produce lo **stesso identico output**. Qui non c'è discussione.

| Nostra | Gemella | Verificato |
|---|---|---|
| `historical_var_cvar` (parte VaR) | `VaR_Hist` | identiche |
| `historical_var_cvar` (parte CVaR) | `CVaR_Hist` | **la nostra è distorta** → M2 |
| `annualized_sharpe` | `Sharpe` | identiche |
| `sample_standard_deviation` | `np.std(ddof=1)` | identiche |
| `correlation_matrix` / `covariance_matrix` | `np.corrcoef` / `np.cov` | identiche → M3 |
| `risk_contributions_from_covariance` | `Risk_Contribution(rm="MV")` | **identiche**, verificato sotto |

Su `Risk_Contribution` la verifica è netta: CCTR coincidenti, `np.allclose` vero, e
la somma dei contributi riproduce la volatilità di portafoglio in entrambe. Nostro
0,022 ms, riskfolio 0,058 ms — differenza irrilevante, come dicevo io stesso.

> Un attrito reale da registrare, non un'obiezione: `Risk_Contribution` vuole la
> **matrice dei rendimenti**, la nostra vuole solo covarianza e pesi. Migrare
> significa far arrivare i rendimenti fino a quel livello. È lavoro di idraulica,
> non di matematica, ma va messo a preventivo.

#### Caso B — Composti: la libreria non li esprime 🟡

Qui il principio si applica, ma **non nella forma «sostituisci la chiamata»**.

`summarize_drawdown` non è «il max drawdown». In **una sola passata** produce massimo,
**durata più lunga sott'acqua**, indice di ricchezza e serie underwater completa:
0,223 ms. `MDD_Rel` restituisce un solo float in 0,904 ms, e **la durata non ce l'ha
affatto** — verificato, non esiste in riskfolio.

Sostituirla significherebbe chiamare riskfolio per il numero *e* tenere comunque il
nostro ciclo per tutto il resto: stesso risultato, calcolato due volte, quattro volte
più lento. Non è «usare la libreria», è duplicare il lavoro.

**La libreria entra come oracolo (M4), non come dipendenza a runtime.** Se un giorno
il nostro `summarize_drawdown` divergesse da `MDD_Rel`, il test lo direbbe subito: è
esattamente la protezione che al CVaR è mancata.

**Ma non restano in `math` puro.** Che Riskfolio non le abbia non è una ragione per
tenerle scritte a mano in Python interpretato: significa solo che il fornitore è un
altro. **Diventano M6**, riscritte in NumPy a firma e semantica invariate —
`np.maximum.accumulate` per il picco progressivo, `np.cumprod` per l'indice di
ricchezza, `np.corrcoef` con maschera per `coverage`.

In questa categoria: `summarize_drawdown`, `drawdown_episodes`, `pairwise_correlation`
(restituisce anche `observations` e `coverage`), `comparison_summary`, `wealth_index`,
`period_returns_from_cumulative`, `horizon_compounded_returns`,
`current_buy_and_hold_returns`, `annualized_sortino`.

Restano **nostri**: ci appartiene la composizione, non l'aritmetica.

#### Caso C — Acquisizioni: la libreria ha cose che non abbiamo ⭐

È il caso in cui il principio **crea valore** invece di spostare codice, e per il
rischio è il più interessante dei tre. Vedi §7.1.

#### Regola risultante

> Non possedere matematica che si può prendere in prestito (A).
> Possedere i composti che la libreria non sa esprimere, ma **validarli** contro di
> lei (B).
> Prendere ciò che non abbiamo (C).

Delle quattordici funzioni che questa sezione dichiarava intoccabili, **sei passano
al caso A** e vanno migrate. Le altre otto restano, ma per una ragione diversa da
quella che avevo scritto: non perché siano veloci, ma perché la libreria non le
contiene.

### M5 — Contributi al rischio a `Risk_Contribution` 🟡

Doppione accertato: `np.allclose` vero contro il nostro
`risk_contributions_from_covariance`, somma pari alla volatilità di portafoglio.
Caso A puro, quindi si migra per principio.

Bassa priorità per un attrito concreto: **riskfolio vuole la matrice dei rendimenti,
noi le passiamo solo covarianza e pesi**. Il valore vero non è il numero — identico —
ma il `rm=` che si sblocca dopo (§7.1): contributi al rischio di coda e al drawdown,
non solo alla volatilità. Da fare quando si affronta quella funzionalità, non prima.

> **Avvertenza per la UI**: i contributi con `rm=` diverso da `MV` **possono essere
> negativi**. È corretto — un asset può ridurre il rischio complessivo — ma rompe
> l'ipotesi implicita di un grafico a torta.

### 7.1 La famiglia drawdown: sette misure, non una

L'intuizione che riskfolio avesse «un altro drawdown, di tipo relativo» è corretta e
sottostima il caso. `RiskFunctions` espone **48 callable — di cui 42 sue** (§7.3), e
la famiglia drawdown ne occupa quattordici: sette misure × due varianti.

**Prima cosa da chiarire: `Abs` e `Rel` non sono due drawdown.** Sono lo stesso
drawdown su due curve diverse. Dal sorgente:

```python
# MDD_Abs                          # MDD_Rel
NAV = np.cumsum(prices)            NAV = np.cumprod(1 + returns)
DD  = peak - i                     DD  = (peak - i) / peak
```

`Rel` è la curva **composta** con il buco espresso in percentuale del picco: è il
drawdown che tutti intendono. `Abs` è la curva **non composta**, con il buco in unità
assolute di capitale iniziale. Serve agli ottimizzatori perché resta *lineare* nei
pesi, quindi il solutore la digerisce; per un utente non significa niente di
naturale.

Verificato: la nostra funzione **è già `MDD_Rel`**, cifra per cifra, a meno del segno
(noi restituiamo negativo, riskfolio positivo).

```text
nostro max_drawdown : -0.2106056094
MDD_Rel             :  0.2106056094   -> |nostro| == MDD_Rel: True
MDD_Abs             :  0.2319957870   -> altra grandezza
nostro max_duration :  217 giorni     -> riskfolio NON ce l'ha
```

**Quindi no, `MDD_Abs` non è il secondo segnale giusto**: è un artificio di
ottimizzazione, e mostrarlo accanto al primo produrrebbe due numeri diversi per la
stessa domanda, senza che nessuno sappia spiegare perché.

**I candidati veri sono altri tre**, e rispondono a una domanda che il massimo
drawdown non può toccare: il massimo dice *quanto in profondità*, mai *quanto a
lungo*.

#### Due portafogli identici sulla carta, opposti nel vissuto

Dodici mesi. Partono da 100, finiscono a 100, e **tutti e due toccano −20%**.

```text
A — crollo breve
  mese      1    2    3    4    5    6    7    8    9   10   11   12
  valore  100  100  100  100   80   90  100  100  100  100  100  100
  sotto%    0    0    0    0  -20  -10    0    0    0    0    0    0

B — erosione lenta
  mese      1    2    3    4    5    6    7    8    9   10   11   12
  valore  100   97   94   91   88   85   82   80   84   89   94  100
  sotto%    0   -3   -6   -9  -12  -15  -18  -20  -16  -11   -6    0
```

| | A | B |
|---|---:|---:|
| MDD — il buco più profondo | 20,0% | 20,0% |
| mesi passati sotto il picco | **2** | **10** |
| ADD — media di tutti i «sotto%» | 2,5% | 9,7% |
| UCI — Ulcer Index | 6,5% | 11,7% |

**Il MDD dà lo stesso identico numero.** Eppure A è una brutta settimana, B è un anno
di erosione. Oggi mostriamo il numero che non distingue i due casi.

#### Che cos'è l'Ulcer Index

Il nome è letterale: nasce per misurare **quanto un investimento fa venire l'ulcera a
chi lo tiene**, non quanto è rischioso in astratto.

Si legge dalla riga `sotto%`: per ogni giorno si prende di quanto si è sotto il
picco precedente, si eleva al quadrato, si fa la media **su tutti i giorni** — anche
quelli a zero — e si prende la radice.

Il quadrato e la media fanno due lavori diversi:

- il **quadrato** rende un buco profondo più che proporzionalmente grave: −20% pesa
  quattro volte −10%, non due;
- la **media su tutti i giorni** fa contare anche la durata: stare sotto dieci mesi
  alza il risultato, stare sotto due lo diluisce.

Quattro mesi, a mano:

| Storia | MDD | ADD | UCI |
|---|---:|---:|---:|
| Un solo mese a −20% | 20% | 5,0% | **10,0%** |
| Quattro mesi a −5% | 5% | 5,0% | **5,0%** |

L'ADD dice che sono uguali — è una media semplice, non distingue un buco concentrato
da uno diluito. Il MDD dice che il primo è quattro volte peggio. L'UCI dice che il
primo è due volte peggio: **né l'uno né l'altro estremo**, ed è il motivo per cui è
utile.

Per noi vale soprattutto questo: l'UCI è in **un numero solo** ciò che oggi diciamo
con due campi separati, `max_drawdown` e `max_duration`.

| Misura | Cosa dice | Costo |
|---|---|---:|
| **ADD** — Average Drawdown | Quanto si sta sotto il picco *in media* | 1,49 ms |
| **UCI** — Ulcer Index | Profondità e durata in un numero solo | 1,76 ms |
| **DaR** 95% | Il drawdown superato solo nel 5% dei giorni: il «brutto tipico» | 1,10 ms |
| **CDaR** 95% | La media di quel 5% peggiore — sta a DaR come CVaR sta a VaR | 1,02 ms |
| EDaR / RLDaR | Varianti entropiche, per l'ottimizzazione | **26,9 ms** ⚠️ solutore |

#### Il parametro `rm=`: scegliere *quale* rischio scomporre

La pagina Risk Contribution risponde a «**chi**, fra i miei asset, è responsabile del
mio rischio?». Ma «rischio» non è una parola sola, e `rm` (*risk measure*) è
l'argomento con cui si sceglie **quale definizione usare**. Stessa funzione, stessi
pesi, stessi dati: cambia solo la domanda.

Serve però verificare se la risposta cambia davvero, altrimenti è un vezzo
accademico. Tre asset costruiti con **la stessa identica volatilità** (0,0120) e tre
difetti diversi:

- **BALLERINO** — oscilla e basta, peggior giorno −4,4%;
- **TRANQUILLO** — calmo, ma un giorno perde il 33,8%;
- **LENTO** — calmo, ma scende per trecento giorni di fila.

Pesi uguali, 33% ciascuno. Chi è il colpevole?

| Definizione di «rischio» | BALLERINO | TRANQUILLO | LENTO |
|---|---:|---:|---:|
| volatilità (`rm="MV"`) — quello che mostriamo oggi | 33,1% | 31,9% | 34,9% |
| code, giornate peggiori (`rm="CVaR"`) | **38,3%** | 23,7% | 38,0% |
| drawdown prolungati (`rm="CDaR"`) | 22,2% | 35,6% | **42,2%** |
| fastidio, profondità × durata (`rm="UCI"`) | 20,7% | 33,8% | **45,6%** |

Le risposte non si somigliano nemmeno.

- Per la **volatilità** i tre sono equivalenti: un terzo a testa. La pagina di oggi
  direbbe «sei perfettamente diversificato», e sarebbe vero — di quella grandezza.
- Per le **code** il colpevole è BALLERINO. Curiosamente non TRANQUILLO, malgrado il
  crollo del 33%: il CVaR al 95% media le cinquanta giornate peggiori su mille, e un
  singolo disastro ci si perde dentro.
- Per i **drawdown** la classifica si ribalta: BALLERINO scende a 22,2% perché
  rimbalza sempre, e LENTO sale a 42,2%.
- Per il **fastidio**, LENTO da solo vale quasi metà del problema: 45,6%.

**BALLERINO passa dal 38,3% al 20,7% a seconda della domanda.** Non è una sfumatura:
è un asset che sembra il maggiore imputato o il minore, secondo cosa si considera
rischio.

Il valore per il progetto è che la pagina potrebbe rispondere a **«chi contribuisce
ai miei drawdown»** invece che «chi contribuisce alla volatilità», e la seconda è la
domanda che un utente si pone davvero — senza una riga di matematica nuova, perché
`Risk_Contribution` accetta già `rm=`.

> **Nota sui contributi non-MV**: alcuni risultano **negativi** — è corretto, perché
> un asset può *ridurre* il rischio di coda del portafoglio, ma rompe l'assunto della
> UI attuale, che tratta i contributi come fette di una torta. Va deciso *prima* di
> mostrarli, non dopo.

**Conseguenza per il piano**: nessuna di queste è migrazione. Sono acquisizioni, e
vanno decise in base alle quattro domande, non alla disponibilità. Registrate come
Q7 in `04`; l'UCI e i contributi su CDaR sono i due candidati con il rapporto
valore/costo migliore.

### 7.3 Il resto delle 42: cosa risponde alle quattro domande

Prima una correzione al mio stesso conteggio: le callable in `RiskFunctions` sono 48,
ma **sei non sono di riskfolio** — `Bounds`, `minimize`, `null_space` (scipy), `PCA`,
`StandardScaler` (sklearn), `pinv` (numpy) finiscono nello spazio dei nomi per via
degli import. Le funzioni proprie sono **42**.

Passate al setaccio delle quattro domande, non dell'entusiasmo.

#### Tre KPI da aggiungere, ciascuno al suo livello

Non sono metriche di punta: sono **righe in più nel pannello KPI**, ognuna nel
capitolo giusto. Costano pochissimo e chiudono un buco ciascuna.

| KPI | Livello | Pagina | Che cosa aggiunge |
|---|---|---|---|
| `NEA` | **L2** | Dashboard, Broker Detail | quanto sono concentrati i pesi |
| `WR` | **L1** | tutte e tre | la peggior giornata realmente accaduta |
| `RG` | **L1** | Asset Global | escursione fra il giorno migliore e il peggiore |

##### `NEA` — indice di concentrazione (L2)

*Number of Effective Assets*: `1 / (w₁² + … + wₙ²)`, l'inverso dell'indice di
Herfindahl — lo stesso che gli antitrust usano per dire se un mercato è concentrato.
Elevare al quadrato punisce i pesi grandi.

| Portafoglio | Posizioni | NEA |
|---|---:|---:|
| 10 asset equipesati | 10 | 10,00 |
| 10 asset, uno al 60% | 10 | 2,65 |
| **3 grossi + 20 briciole** | **23** | **4,12** |

Solo i pesi, 0,0025 ms. In L2 sta accanto alla correlazione e al contributo al
rischio, **non al loro posto**: è cieco alla correlazione, e questa è la prova —
tre portafogli di dieci asset equipesati, stessa volatilità individuale, cambia solo
quanto si muovono insieme:

| Caso | NEA | Volatilità reale | Diversification ratio |
|---|---:|---:|---:|
| 10 asset indipendenti | **10,00** | 0,00380 | 3,15 |
| 10 asset mediamente legati (ρ≈0,5) | **10,00** | 0,00892 | 1,35 |
| 10 asset quasi identici (ρ≈0,95) | **10,00** | 0,01164 | 1,02 |

Stesso numero, volatilità tripla. Nemmeno applicarlo ai contributi al rischio salva
(9,97 contro 10,00). Il **diversification ratio** — media pesata delle volatilità
divisa per la volatilità di portafoglio — vede invece esattamente ciò che NEA non
vede: vale 1,00 quando gli asset sono intercambiabili. Riskfolio non ce l'ha: tre
righe di NumPy sulla covarianza che già calcoliamo, e va nello stesso pannello.

##### `WR` e `RG` — ancore concrete (L1)

`WR` (*worst realization*) è la singola giornata peggiore della storia disponibile.
Non è una stima: è successo. Sta bene accanto al VaR proprio per questo — il VaR dice
«una giornata su venti va peggio di così», `WR` dice «e la peggiore di tutte è stata
questa».

`RG` (*range*) è la distanza fra il giorno migliore e il peggiore. Serve poco su un
portafoglio, dove il VaR dice già di più; ha senso su **Asset Global**, come colonna
di confronto fra strumenti — dice a colpo d'occhio chi è nervoso.

Misurati su due asset — A oscilla molto senza disastri, B oscilla poco ma passa un
anno in discesa:

| Misura | A | B | In italiano |
|---|---:|---:|---|
| volatilità | 0,01410 | 0,00699 | quanto si muove in un giorno **tipico** |
| `MAD` | 0,01122 | 0,00565 | idem, senza elevare al quadrato → pesa meno gli estremi |
| `WR` | **−4,29%** | −2,28% | la **singola** giornata peggiore mai vista |
| `RG` | 0,09480 | 0,04498 | distanza fra il giorno migliore e il peggiore |

`MAD` resta fuori: misura la stessa cosa della volatilità, che già mostriamo.

#### ⚫ `Kurtosis` — non è un KPI di portafoglio

Due ragioni indipendenti, entrambe verificate.

**Prima: la versione riskfolio non è quella che ci si aspetta.** Il sorgente fa
`sqrt(Σ(μ−x)⁴/T)` — la radice del momento quarto, **non adimensionale**. Il docstring
dell'ottimizzatore lo conferma: `'KT': Square Root of Kurtosis`. Verificato su
200 000 punti gaussiani: 0,00034462, esattamente `sqrt(m₄)`, mentre la kurtosi vera è
2,989 e l'eccesso −0,011. Per la domanda «ho le code grasse?» servirebbe
`scipy.stats.kurtosis(x, fisher=True)`, dove **0 = normale**.

**Seconda, e decisiva: su una singola storia il numero non è stimabile.** È un momento
di ordine quarto, quindi la sua incertezza dipende dall'ottavo momento — cioè proprio
dalla grandezza che sta cercando di misurare. Stessa identica distribuzione (t di
Student, df=5, **eccesso vero = 6,0**), ricampionata 500 volte:

| Storia | Mediana stimata | 5° pct | 95° pct |
|---|---:|---:|---:|
| 1 anno (250 gg) | 2,01 | 0,55 | 9,10 |
| **3 anni (750 gg)** | **2,82** | **1,19** | **10,85** |
| 10 anni (2500 gg) | 3,47 | 1,97 | 11,20 |
| 50 anni (12500 gg) | 4,02 | 2,78 | 10,12 |

Con tre anni di storia — quanto ha un utente tipico — il valore vero 6,0 viene stimato
fra 1,2 e 10,8. E anche con cinquant'anni la mediana è ancora 4,02: **distorta verso
il basso**, perché i campioni finiti non contengono abbastanza eventi rari.

Il perché è visibile a occhio nudo: il numero è ostaggio di una manciata di giorni.

| Su 750 giorni | Eccesso di kurtosi |
|---|---:|
| tutti | 3,88 |
| togliendo il giorno più estremo | 3,23 |
| togliendo i 3 più estremi | 2,20 |
| togliendo i 10 più estremi | **0,63** |

Dieci osservazioni su 750 — l'1,3% dei dati — fanno crollare il numero di sei volte.

**E non discrimina.** Quattro profili realistici, 750 giorni, 200 ripetizioni ciascuno:

| Profilo | Eccesso tipico | Ma oscilla fra |
|---|---:|---|
| obbligazionario tranquillo | 1,2 | 0,6 e 2,4 |
| ETF azionario globale | 4,8 | 2,2 e **19,9** |
| azione singola | 9,9 | 4,2 e 48,1 |
| cripto | 21,0 | 8,2 e 111,4 |

Sono **tutti sopra zero** — le code grasse sono un fatto stilizzato di ogni serie
finanziaria, quindi la risposta è sempre «sì» — e gli intervalli **si sovrappongono**:
un ETF può misurare 19,9 e un'azione singola 4,2, invertendo l'ordine vero.

**Dove serve davvero, ed è dove l'intuizione era giusta.** Riskfolio la espone come
misura di rischio per l'**ottimizzatore** (`rm="KT"`, `rm="SKT"`), alimentata da
`ParamsEstimation.cokurt_matrix` — la matrice di **co**kurtosi. Lì la domanda non è
«questo asset ha code grasse» ma «quali asset hanno le code grasse *insieme*», e si
risponde mediando su molti strumenti, il che cancella il rumore che rende inutile la
stima singola. È uno strumento da universo ampio, non un KPI da pannello.

> Su un portafoglio di pochi asset, la domanda «quanto sono brutte le mie giornate
> brutte?» ha già una risposta migliore: il **CVaR**, che è una percentuale di perdita
> — stimabile, leggibile, e in unità che significano qualcosa.

#### ⭐ `Sharpe(rm=...)` — L3 non ha una risposta sola

L3 chiede «sto venendo pagato per questo rischio?». La domanda contiene un buco:
**pagato per *quale* rischio?** Lo Sharpe classico risponde sempre «per
l'oscillazione», perché ha la volatilità al denominatore. Ma chi sta male per le
discese lunghe non sta chiedendo quello.

`Sharpe(rm=...)` cambia il denominatore. Il numeratore resta il rendimento; cambia
l'unità di misura del rischio. Ne escono rapporti che hanno un nome proprio in
letteratura:

| `rm=` | Diventa | La domanda che risponde |
|---|---|---|
| `MV` | Sharpe classico | Sono pagato per l'**oscillazione**? |
| `MDD` | **Calmar ratio** | Sono pagato per il **buco peggiore**? |
| `UCI` | **Martin ratio** | Sono pagato per il **fastidio prolungato**? |
| `CVaR` | rapporto su rischio di coda | Sono pagato per le **giornate nere**? |
| `CDaR` | rapporto su drawdown | Sono pagato per i **periodi sott'acqua**? |

**«Su misura» significa che la classifica cambia**, altrimenti sarebbero decorazioni.
Misurato sui due asset del paragrafo precedente:

| | rendimento | buco peggiore | ulcer | Sharpe | Calmar | Martin |
|---|---:|---:|---:|---:|---:|---:|
| **A** mosso, mai a lungo giù | 54,2% | 25,4% | 11,48% | 0,60 | **0,48** | **1,15** |
| **B** calmo, un anno in discesa | 44,6% | 30,3% | 16,61% | **0,89** | 0,28 | 0,55 |

Lo Sharpe dice **B**, con distacco: oscilla la metà. Calmar e Martin dicono **A**, e
di parecchio: B ha reso meno *e* ha scavato un buco più profondo, tenendolo più a
lungo. Non si contraddicono — rispondono a due domande diverse che oggi noi poniamo
come se fossero una.

Tutti verificati funzionanti. Nessuna matematica nuova da scrivere.

> Vincolo di presentazione: mostrarli **tutti insieme in una riga** sarebbe la solita
> flatness del §05. Il modo giusto è farli scegliere — «rispetto a cosa?» — e mostrare
> un numero alla volta, con la domanda scritta accanto.

#### 🟡 Le altre della famiglia forma/coda

`MAD`, `SemiDeviation`, `SemiKurtosis`, `LPM` (momenti parziali inferiori). Guardano
il lato negativo, che è l'idea giusta, ma nessuna aggiunge una domanda rispetto a
volatilità, VaR, CVaR e famiglia drawdown. `MAD` in particolare misura la stessa cosa
della volatilità, che già mostriamo.

#### 🔵 Da tenere d'occhio, non ora

`BrinsonAttribution` scompone il rendimento in *effetto allocazione* (ho scelto le
categorie giuste?) ed *effetto selezione* (ho scelto gli strumenti giusti dentro le
categorie?). È la risposta più completa a L3, ma pretende un **benchmark con i suoi
pesi per classe** — quindi è bloccata dietro Q1, e anche dopo richiede una tassonomia
di classi che oggi non abbiamo.

`Factors_Risk_Contribution` richiede una matrice di fattori esterni (stile
Fama-French): fuori portata senza un provider dati.

#### ⚫ Da lasciare stare

`EDaR`, `RLDaR`, `RLVaR`, `Entropic_RM`, `L_Moment_CRM`, `TG`, `TGRG`, `CVRG`,
`EVRG`, `RVRG`, `VRG`, `GMD`, `Risk_Margin`.

Due motivi, entrambi sufficienti: invocano un solutore (26,9 ms misurati su EDaR) e
richiedono di spiegare l'entropia o la disuguaglianza di Gini a chi voleva sapere
quanto può perdere. Esistono per gli ottimizzatori, non per le persone.

#### ⚠️ Un caso che invita alla prudenza: il Sortino

Sembrerebbe un doppione: noi abbiamo `annualized_sortino`, riskfolio ha
`SemiDeviation`. **Non sono la stessa cosa**, e la differenza è nel codice:

```python
# nostro                              # riskfolio SemiDeviation
min(value - MAR, 0) ** 2              (mu - a)[value >= 0] ** 2
... / len(values)                     ... / (T - 1)
```

Noi misuriamo gli scarti sotto un **rendimento minimo accettabile** (il MAR, zero di
default) e dividiamo per `T`; riskfolio misura gli scarti sotto la **media
campionaria** e divide per `T−1`. Verificato: 1,66294 contro 1,57093 ricostruito.

Il Sortino è *definito* contro un MAR, quindi il nostro è corretto per il suo scopo e
il loro è corretto per il proprio (l'ottimizzazione media-semivarianza). È la stessa
trappola di `MDD_Abs` e di `numBins`: **nome simile, grandezza diversa**.

> **Guardia da applicare a ogni migrazione del caso A**: prima di sostituire, provare
> che i due numeri coincidano su dati reali. Il criterio «sta in libreria, si usa»
> vale per la *matematica*, non per il *nome*. Questo è il lavoro che M4 rende
> sistematico invece che occasionale.

### 7.2 Nota sui bin dell'istogramma

D21 resta valida ma cambia di costo: `np.histogram(x, bins='fd')` **è**
Freedman-Diaconis, nativo. Verificato: 21 bin su 750 osservazioni,
`sum(counts) == 750`. Disponibili anche `'auto'` (il massimo fra `fd` e `sturges`),
`'scott'`, `'sturges'`, `'rice'`, `'doane'`, `'sqrt'`.

**Non implementiamo la regola, la scegliamo.** L'unica parte nostra ancora la
griglia al quantile del VaR: `np.histogram_bin_edges` fornisce la larghezza, noi
trasliamo perché un bordo cada esattamente sul VaR. Cinque righe.

---

## 8. Riproducibilità

Gli script di confronto sono in `/tmp/` e non fanno parte del repository:

| Script | Log | Cosa misura |
|---|---|---|
| `/tmp/libreFolio_cmp_risk.py` | `libreFolio_cmp_risk.log` | VaR, CVaR, drawdown, volatilità |
| `/tmp/libreFolio_cmp2.py` | `libreFolio_cmp2.log` | Sharpe, Sortino, risk contribution, bin |
| `/tmp/libreFolio_perf.py` | `libreFolio_perf.log` | scaling O(N²·T) delle matrici |
| `/tmp/libreFolio_cvar.py` | `libreFolio_cvar.log` | **Acerbi-Tasche, distorsione su 2000 campioni, off-by-one** |
| `/tmp/libreFolio_3way.py` | `libreFolio_3way.log` | **confronto a tre vie, segnali rolling contro pandas** |
| `/tmp/libreFolio_talib.py` | `libreFolio_talib.log` | instradamento `pandas_ta_classic` → TA-Lib C |
| `/tmp/libreFolio_rf_api.py` | `libreFolio_rf_api.log` | inventario API Riskfolio: rolling, matrici, bin |
| `/tmp/libreFolio_rf_deep.py` | `libreFolio_rf_deep.log` | sorgente di `covar_matrix`, semantica di `numBins` |
| `/tmp/libreFolio_rf_cov.py` | `libreFolio_rf_cov.log` | `covar_matrix('hist')` contro `np.cov`, Ledoit-Wolf |
| `/tmp/libreFolio_estimators.py` | `libreFolio_estimators.log` | rapporto T/N, autovalori, singolarità, stabilità fuori campione |
| `/tmp/libreFolio_dd_family.py` | `libreFolio_dd_family.log` | le 48 funzioni di `RiskFunctions`, famiglia drawdown |
| `/tmp/libreFolio_dd_sem3.py` | `libreFolio_dd_sem3.log` | `MDD_Abs` contro `MDD_Rel`, ADD/UCI/DaR/CDaR, due storie |
| `/tmp/libreFolio_rc.py` | `libreFolio_rc.log` | `Risk_Contribution` contro la nostra, contributi su `rm=` |
| `/tmp/libreFolio_lezione.py` | — | i due portafogli a 12 mesi, MDD/ADD/UCI a mano |
| `/tmp/libreFolio_rm2.py` | — | tre asset a volatilità identica, colpevole per ogni `rm=` |
| `/tmp/libreFolio_48.py` | §7.3 | inventario classificato: 42 funzioni proprie, 6 importate |
| `/tmp/libreFolio_nea.py` | §7.3 | NEA su cinque portafogli, `Sharpe(rm=)` su cinque misure, costo |
| `/tmp/libreFolio_sortino.py` | §7.3 | il nostro Sortino contro `SemiDeviation`: denominatori diversi |
| `/tmp/libreFolio_nea2.py` | §7.3 | NEA su tre livelli di correlazione: cieco. Diversification ratio: no |
| `/tmp/libreFolio_lez2.py` | §7.3 | WR/RG/MAD/Kurtosis su due asset; flip Sharpe contro Calmar/Martin |
| `/tmp/libreFolio_kurt.py` | §7.3 | `RF.Kurtosis` = `sqrt(m₄)`, non standardizzata: controprova con t(3) |
| `/tmp/libreFolio_kurt2.py` | §7.3 | stabilità della stima a 250/750/2500/12500 gg; sensibilità ai 10 estremi |
| `/tmp/libreFolio_kurt3.py` | §7.3 | `rm="KT"`/`"SKT"` nell'ottimizzatore, `cokurt_matrix` |
| `/tmp/libreFolio_dd_all.py` | `04` Q7 | inventario delle 14 funzioni drawdown con tempi; scopre `RLDaR_Rel = 0` su un seme e la tupla di `EDaR` |
| `/tmp/libreFolio_dd_absrel.py` | `04` Q7 | legge il sorgente di `MDD_Abs`/`MDD_Rel` e ricostruisce a mano entrambi: `cumsum` contro `cumprod`, riscontro a sei decimali |

Invocazione (lane worktree):

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python /tmp/libreFolio_perf.py
```

Se M4 viene eseguita, il primo script diventa un test vero e questa sezione si può
cancellare.

---

## 9. Documenti collegati

- [`README.md`](./README.md) — indice e ordine di lettura
- [`00-analisi-stato-attuale.md`](./00-analisi-stato-attuale.md) — inventario del codice
- [`04-decisioni-e-questioni-aperte.md`](./04-decisioni-e-questioni-aperte.md) — D23-D27, Q2 chiusa
- [`05-grammatica-visiva-e-rappresentazioni.md`](./05-grammatica-visiva-e-rappresentazioni.md) — §7.2 istogramma, §8 heatmap e seed a cento asset
