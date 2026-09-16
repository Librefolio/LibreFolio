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

`Pipfile` dichiara due librerie di rischio e una di calcolo scientifico:

| Pacchetto | Versione | Usato in |
|---|---|---|
| `riskfolio-lib` | 7.0.1 | `risk_plugins/portfolio_optimization.py`, `risk/quant/riskfolio_worker.py` |
| `quantlib` | 1.43 | `risk/quant/quantlib_worker.py` |
| `scipy` | * | `utils/financial/roi_utils.py` (Newton per l'IRR) |

Il dato che conta: **`scipy` nel dominio rischio non compare mai**, e le due
librerie di rischio servono **una sola analitica ciascuna** — rispettivamente
`portfolio_optimization` e `simulation`.

Le altre **sette** analitiche (`historical_kpi`, `correlation`,
`risk_contribution`, `historical_var`, `comparison`, `drawdown_summary`, `stress`)
non importano nulla. Verificato:

```bash
grep -rln "import numpy\|import pandas" app/services/risk_plugins/
# nessun risultato
```

### 2.1 La divisione è coerente, non accidentale

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

### 2.2 La scelta fu deliberata? No — e questo cambia tutto

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

**Verdetto: nessun debito.** Questi plugin sono il modello. Non vanno toccati.

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

Il criterio non è «libreria buona, codice nostro cattivo». È **una funzione scalare
chiamata una volta resta dov'è; una funzione scalare chiamata in un ciclo va
vettorializzata**. Più un'eccezione di correttezza.

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

**Cosa**: `correlation_matrix`, `covariance_matrix` e il doppio ciclo di
`risk_plugins/correlation.py:72`.

**Perché**: da 1 025× a 24 698×, e NumPy rilascia la GIL dove il Python puro la
trattiene (§4.3).

**Il costo nascosto**: `pairwise_correlation` restituisce anche `observations` e
`coverage`, che gestiscono i calendari disallineati. La versione vettorializzata deve
produrre gli **stessi** valori di copertura, non solo gli stessi coefficienti. Va
fatta con una maschera di validità, non con `np.corrcoef` crudo.

Più delicata di M1, e serve meno spesso. Da fare dopo.

### M4 — Riskfolio come oracolo di test ⭐ da fare per primo in assoluto

`test_risk_metrics.py` (297 righe) importa solo `math`. Verifica proprietà interne —
additività del PCTR, identità con TE nullo e beta unitario — che sono test *buoni*,
ma tutti autoreferenziali: **nessun controllo indipendente**.

Riskfolio è già installata e già pagata in spazio (§6). Venti righe danno il
confronto incrociato che oggi manca.

**Va scritto prima di M1-M3**, non dopo: è la rete che rende sicure le altre tre
migrazioni. Ed è lo stesso strumento che ha scoperto il difetto del CVaR.

### Cosa NON migrare 🟢

Le funzioni scalari invocate una volta per richiesta: `compounded_return`,
`sample_variance`, `sample_standard_deviation`, `sample_covariance`,
`annualized_volatility`, `annualized_sharpe`, `annualized_sortino`, `beta`,
`wealth_index`, `underwater_drawdown`, `summarize_drawdown`, `drawdown_episodes`,
`period_returns_from_cumulative`, `horizon_compounded_returns`.

Costano tutte **sotto il millisecondo** (§4.0). Sono corrette, leggibili e testate.
`math.fsum` dà per giunta una sommatoria esattamente compensata che `np.sum` non
garantisce.

E c'è un argomento più forte del conservatorismo: **sul max drawdown il nostro Python
puro è quattro volte più veloce di Riskfolio**, perché `MDD_Rel` è anch'essa
interpretata. Migrare in blocco «perché la libreria è più veloce» peggiorerebbe
quella riga.

Restano scalari perché è il posto giusto per una funzione scalare — non per inerzia,
questa volta, ma per misura.

### 7.1 Nota sui bin dell'istogramma

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
