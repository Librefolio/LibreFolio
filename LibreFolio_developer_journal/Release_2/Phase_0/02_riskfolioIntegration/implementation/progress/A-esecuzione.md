# A — piano di esecuzione

> Oracolo di test e migrazione matematica. Questo è il **piano vivo**: si aggiorna dopo
> ogni passo. Il brief in [`../A-backend-oracolo-e-migrazione.md`](../A-backend-oracolo-e-migrazione.md)
> è in **sola lettura** e non viene spuntato.

| | |
|---|---|
| **Mandato** | [`../A-backend-oracolo-e-migrazione.md`](../A-backend-oracolo-e-migrazione.md) |
| **Branch** | `e-alfy-risk-oracle-math-migration` ⚠️ *rinominato dall'app da `e-alfy-improved-meme`* |
| **Worktree** | `e-alfy-improved-meme` (il percorso **non** è cambiato col branch) |
| **Baseline** | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` — verificata, coincide |
| **Lane** | porta `6240` · data dir `backend/data/test-risk-a` |
| **Coordinatore** | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |
| **Autorizzazione** | delega permanente del developer, trasmessa dal coordinatore |

Forma canonica dei comandi, senza eccezioni:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6240 --data-dir backend/data/test-risk-a <CAT> <AZIONE>
```

---

## Confini

Concessi dal coordinatore dopo l'analisi, oltre a quelli del brief §6:

- **§2.10(a)** — i quattro `signal_plugins/rolling_{sharpe,beta,return,volatility}.py`
  (M1 è impossibile senza: le funzioni rolling prendono un `metric` callable opaco e
  tutti e quattro i chiamanti passano lambda).
- **§2.10(b)** — `risk_plugins/historical_var.py` e `risk_plugins/drawdown_summary.py`
  (K1 è inconsegnabile senza: sono i due produttori dei campi).

**Nient'altro.** In particolare: nessun altro file di `risk_plugins/` (di N), nessun
file di `ai_export/`, nessuna pagina MkDocs (di I).

---

## Passi

- [x] **A0. Piano vivo** — ✅ 2026-09-18
  > **Note implementazione**: creato questo file. Sono il primo mandato ad aprirne uno,
  > quindi il formato qui usato fa da precedente per gli altri.

- [x] **A1. W0 — l'oracolo riskfolio** — ✅ 2026-09-18
  Nuovo `backend/test_scripts/test_services/test_risk_metrics_oracle.py`, selettore
  `risk-oracle`, registrazione in `RISK_SERVICE_TEST_PATHS`.
  Cinque blocchi: (a) coppie caso A, (b) composti caso B, (c) le quattro trappole di
  nome, (d) 🆕 `undefined_windows`, (e) 🆕 coerenza interna matrice/scalare.
  > **Note implementazione**: 572 righe, **25 test**, scritti da `test-author` su brief
  > dettagliato e rivisti da me. Registrato in `_backend_services.py` con
  > `isolation="pure"` — il file non tocca database, server, rete o filesystem, e ogni
  > campione nasce da un seed fisso. Aggiunto un **test di identità del campione** che
  > fallisce se qualcuno cambia il generatore: le costanti misurate valgono solo per
  > quel sorteggio. La barriera di processo (riskfolio mai nel processo web) è scritta
  > nel docstring del modulo, perché è il posto dove verrà letta.
  >
  > **Fuori pista** — tre contraddizioni fra il brief e il codice, tutte a favore del
  > codice:
  > 1. **La diagonale di `correlation_matrix` non è esattamente 1.0**: misurata
  >    `0.9999999999999999`. `pearson_correlation(x, x)` è `cov/(sd·sd)` e
  >    `sqrt(v)·sqrt(v) != v` in virgola mobile; il clamp `min(1.0, …)` taglia sopra ma
  >    non risolleva. Asserito `approx(1.0, rel=1e-12)`, non `== 1.0`.
  > 2. **A T=750 il VaR *non* diverge** (scarto ~1e-15). Non contraddice la mia misura
  >    dei 21/400: la divergenza del VaR è un effetto **di campione piccolo**, che morde
  >    quando `α·T` cade vicino a un intero. Quella del CVaR è invece sistematica. La
  >    distinzione è ora scritta nel test.
  > 3. 🔴 **`horizon_returns` a `horizon_days=1` non è bit-identico all'input**:
  >    `compounded_return([v])` calcola `1.0*(1.0+v) - 1.0`, che differisce da `v`
  >    nell'ultimo bit. **Una riscrittura NumPy che scorciatoi l'orizzonte 1 all'identità
  >    sposterebbe il VaR pubblicato alla 16ª cifra.** Da ricordare in M2 e M6.

- [x] **A2. K1 — i due campi e i loro produttori** — ✅ 2026-09-18
  Consegna che sblocca **E**. Contratto trasmesso al coordinatore: definitivo.
  > **Note implementazione**: quattro file toccati.
  > `schemas/risk.py` → `RiskVarCvarBin` + `RiskDrawdownPoint`, i due campi additivi
  > (`return_bins`/`var_bin_edge` e `underwater_series`), un validator di ordinamento
  > crescente, e due voci in `__all__`. **La regione a tre scrittori `__all__` è stata
  > bucata in due punti**: `RiskDrawdownPoint` dopo `RiskDrawdownOutput`,
  > `RiskVarCvarBin` prima di `RiskVarCvarOutput` — ordine alfabetico rispettato, quindi
  > la risoluzione meccanica autorizzata (unione + riordino) funzionerà con C e N.
  > `metrics.py` → campo `drawdowns` su `DrawdownEpisodeReport` riempito a **entrambi**
  > i siti di costruzione, dataclass `ReturnHistogram`, funzione
  > `return_distribution_histogram`, primo import di `numpy` nel modulo.
  > `drawdown_summary.py` → costruisce `underwater_series` da `report.drawdowns[1:]`.
  > `historical_var.py` → costruisce i bin e `var_bin_edge = -value_at_risk`.
  >
  > **La serie underwater esisteva già e veniva buttata via**: `drawdown_episodes` la
  > calcolava internamente e la scartava a fine funzione. K1 non ha aggiunto matematica,
  > ha smesso di gettare un risultato già pagato.
  >
  > **`algorithm_version`** — verificato che è **metadato di provenienza e non entra in
  > nessuna chiave di cache** (`service.py:818`), quindi nessun rischio di
  > invalidazione. `drawdown_summary` → **`1.1.0`** (payload più ricco, numeri
  > invariati: il MINOR distingue «serie piatta» da «server vecchio»).
  > `historical_var` **resta `1.0.0`**: lì la matematica cambia in A3 e va dritta a
  > `2.0.0`. ⚠️ **Se M2 venisse rinviato, `historical_var` va comunque portato a
  > `1.1.0`** — altrimenti spedisce due campi nuovi sotto una versione vecchia.
  >
  > **Fuori pista 1 — D21 mi ha corretto, e la correzione era sostanziale.**
  > Stavo per **non** ancorare il bordo del bin al VaR, ragionando che un bin di
  > larghezza irregolare falsa la lettura di un istogramma. La preoccupazione era
  > giusta, la conclusione sbagliata: `06` §7.2 **trasla** il reticolo invece di
  > deformarlo, quindi larghezze uniformi **e** bordo esatto sul taglio. Senza rileggere
  > la decisione avrei consegnato a E un grafico in cui la percentuale dichiarata e
  > l'area rossa non coincidono — **invisibile a occhio**, e quindi permanente.
  >
  > **Fuori pista 2 — la sonda numerica ha trovato un bug vero prima dei test.**
  > Primo tentativo: reticolo costruito solo sull'intervallo dei dati. Funziona sul caso
  > normale (ancoraggio `0.000e+00`), **fallisce quando il pavimento a zero morde**:
  > con una serie che ha solo guadagnato il VaR è `0.0`, quindi il taglio cade **fuori**
  > dai dati e non può essere un bordo. Misurato `pin_err = 3,75e-04`. Corretto
  > estendendo il reticolo fino ad abbracciare anche il taglio. È il caso previsto da
  > `06` §3.3, e ora è coperto invece che subito.
  >
  > **Fuori pista 3 — `black` voleva riformattare codice non mio.**
  > `_backend_services.py` non era black-pulito **alla baseline** (un blocco in
  > `services_tools_lifecycle`, ~:959). Ho annullato quella riformattazione: il mio
  > diff su un file condiviso resta di **12 righe aggiunte**, così H e N non trovano
  > rumore che non è loro.
  >
  > **Residuo**: copertura oracolo del binning affidata a `test-author`.
  >
  > **Fuori pista 4 — `test-author` ha trovato tre difetti reali nel mio istogramma,
  > prima che la suite girasse.** Tutti e tre erano miei, non fraintendimenti del brief:
  > 1. **Il tetto dei bin non tettava**: `_MAX_HISTOGRAM_BINS = 200` produceva **201**
  >    bin. Il reticolo è allineato all'ancoraggio, non alla campata, quindi **entrambi**
  >    gli estremi arrotondano verso l'esterno e costano fino a due bin. Il divisore
  >    corretto è `_MAX_HISTOGRAM_BINS - 2`.
  > 2. 🔴 **Una serie costante produceva una barra larga 100 punti percentuali.**
  >    NumPy imbottisce di **±0,5** un campione a range nullo, quindi
  >    `histogram_bin_edges` restituiva `1.0` — positivo e finito, quindi la mia guardia
  >    `width <= 0.0` non scattava **mai** e il ripiego documentato era codice morto.
  >    È l'unico dei tre che sarebbe arrivato a un utente. Corretto controllando
  >    `highest > lowest` **prima** di interrogare NumPy.
  > 3. **`pinned_edge` non finito non sollevava su input vuoto**: la scorciatoia per la
  >    serie vuota precedeva il controllo di finitezza. Trappola latente verso un campo
  >    `FiniteFloat`. Corretto invertendo l'ordine delle guardie.
  >
  > Verificati su **505 posizioni di ancoraggio**: peggior conteggio 199 ≤ 200, mai
  > un'osservazione persa, ancoraggio esatto ovunque. Il caso canonico non si è mosso
  > di un bit (22 bin, 750/750, coda 37/750 = 0,0493).
  >
  > **Fuori pista 5 — il primo rosso vero è arrivato all'esecuzione, non alla scrittura.**
  > `zip(edges, edges[1:], strict=True)` non può funzionare: le due sequenze differiscono
  > di uno **per costruzione**. Difetto del test, non del prodotto — la griglia era
  > crescente. `test-author` non poteva vederlo perché non ha la lane e non esegue la
  > suite: è esattamente il motivo per cui la separazione «chi scrive i test ≠ chi li
  > esegue» richiede che l'esecuzione avvenga davvero.
  >
  > Ridotto lo sweep da 501 a 101 ancoraggi: **2,28 s → 0,49 s**, stesso caso peggiore
  > (199) verificato a 505/205/105/55 posizioni. L'evidenza non cambia, il costo sì.

- [x] **A3. M2 — VaR *e* CVaR allo stimatore coerente** — ✅ 2026-09-18
  Comprende la riscrittura di `test_risk_metrics.py:142-158`, `algorithm_version` a
  `2.0.0`, e la rinomina della stringa `method`.
  > **Note implementazione**: dettaglio completo, cifre per J e I, e le due trappole di
  > virgola mobile nella sezione **✅ A3** più sotto. `services risk-all` **177 passed**.
  > Cancello `api risk` non eseguibile per infrastruttura — vedi sezione dedicata.

- [x] **A4. M1 — vettorializzazione dei segnali rolling** — ✅ 2026-09-18
  > **Note implementazione**: quattro helper vettorializzati specifici per metrica in
  > `signal_helpers.py`, più `_assemble_rolling_values` che riporta il risultato al
  > contratto `(values, undefined_windows)`. Quattro call site scambiati
  > (`rolling_{return,volatility,sharpe,beta}.py`, una riga ciascuno).
  > `_ZERO_TOLERANCE` promossa a `ZERO_TOLERANCE` pubblica (11 siti).
  > **T = 1250: 80,4 ms → 1,26 ms, 64×** (sharpe 106×, beta 90×).
  > Conteggi `undefined` **identici** in tutti e cinque gli scenari con buchi
  > (91, 91, 211, 211, 61) e su tutti i bordi (T<W, W=1, serie vuota).
  > Test differenziale durevole delegato a `test-author`: **19 funzioni / 88 casi**,
  > Blocco (g). L'oracolo passa da 43 a 131 casi, `risk-all` da 177 a **265**.

- [x] **A5. M3 — matrici** (`metrics.py` + doppio ciclo di `correlation.py`) — ✅ 2026-09-18
  > **Note implementazione**: `covariance_matrix` → `np.cov(ddof=1)`; `correlation_matrix`
  > → nuova `_vectorised_pearson_matrix`; nuova `pairwise_correlation_matrix` che sostituisce
  > il doppio ciclo N² del plugin. **N=100, T=2500: 15 987 ms → 21,6 ms (742×)**.
  > Comportamento invariato: stessa collocazione dei `None`, delta max 1,11e-16.
  > Rete durevole delegata a `test-author`: **14 funzioni / 27 casi**, Blocco (h).
  > L'oracolo passa da 131 a **158** casi, `risk-all` da 265 a **292**.
  > **Tutti verdi alla prima esecuzione**, comprese le otto ipotesi che `test-author`
  > aveva classificato come a rischio — in particolare il **cancello di simmetria a
  > `rel_tol=1e-12`**, che sarebbe stato un difetto reale di `np.cov` e non del test.

- [x] **A6. M6 — i nove composti** — ✅ 2026-09-18 · **chiuso con ZERO migrazioni**
  > **Note implementazione**: misurati tutti e nove (tutti sub-6 ms a T=2500) ed esclusi
  > tutti e nove, ognuno con una ragione misurata. **Fuori pista 13**: la Fascia 1
  > (`wealth_index` → `np.cumprod`) si è autodistrutta — l'oracolo la confronta **già**
  > contro `np.cumprod`, quindi migrarla renderebbe il test tautologico. La bit-identità
  > che la rendeva sicura è la stessa cosa che svuoterebbe il suo oracolo.
  > `comparison_summary`: **90,9 %** del costo è nei chiamati, tutti esclusi per ragioni
  > indipendenti; codice proprio **0,295 ms**. Nessun file sorgente modificato.

- [x] **A7. M5 + D39** — ✅ 2026-09-18 · **M5 declinata, D39 dichiarata NON bloccata da M5**
  Se rinviata, **D39 la segue e va dichiarato**.

- [ ] **A8. Chiusura** — `risk-all` verde, porta libera, messaggio di commit proposto.

- [ ] **A9. Tasso privo di rischio coerente con la frequenza** — ✅ **AUTORIZZATO**
  2026-09-18 come **passo separato dopo M6**. Terza estensione di confine concessa
  (dopo i quattro `rolling_*.py` e i due `risk_plugins/`).
  Segnalato dal coordinatore su scoperta di I, confermato **e ridiagnosticato** da me.
  `daily_risk_free_rate` divide per **365 cablato**, mentre `annualization_factor` è
  **misurato**. Correzione: derivare il tasso di periodo da `f`
  (`expm1(log1p(rate)/f)`), tre righe.
  > ⚠️ **NON dentro M6.** M6 è il passo la cui proprietà definente è che i numeri non
  > si muovano, ed è l'unica cosa che l'oracolo garantisce lì. Infilarci una correzione
  > che *deve* muovere i numeri renderebbe indistinguibile una regressione della
  > vettorializzazione dalla correzione voluta. Va **dopo** M6, isolata, così ogni
  > numero spostato ha una sola causa possibile. Argomento accettato dal coordinatore
  > e citato come principio valido per l'intera campagna.
  > Bump di `algorithm_version` su **`historical_kpi`** (oggi `2.0.0`) **e su
  > `rolling_sharpe`** — quest'ultimo è mio dall'estensione di M1 e la correzione lo
  > tocca. Voce CHANGELOG per J, con la formulazione **«può invertire il segno»** e
  > **non** una percentuale.
  > 📌 **Debito verso A3 — ESTINTO E RITIRATO.** Chiedeva di misurare la **copertura
  > reale** di un portafoglio vero. **È la variabile sbagliata**: `coverage` e `f` si
  > calcolano con denominatori diversi (Fuori pista 6), e su dati perfettamente sani
  > `coverage ≈ 1,000` mentre `f ≈ 252`. Misurarla avrebbe prodotto una cifra
  > **rassicurante e falsa**. Sostituita dall'effetto diretto misurato su
  > `annualized_sharpe` a f=252: **+0,03…+0,08 di Sharpe sovrastimato**, stabile fra
  > 1 e 3 anni. J calibra il CHANGELOG su questa, I lo spazio da darle.

---

## Evidenza

| Comando | Esito |
|---|---|
| `git rev-parse HEAD` | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` — baseline confermata |
| `… services risk-oracle` | **25 passed in 3,23 s** (A1) |
| `… utils test-runner-cli` | **19 passed in 0,11 s** (A1 — contratto del runner dopo il nuovo selettore) |
| `… services risk-oracle` | **39 passed in 3,12 s** (A2 — blocco istogramma incluso) |
| `… services risk-all` | **173 passed in 29,73 s** (A2) |
| `… schemas risk` | **14 passed in 0,14 s** (A2 — lo schema è cambiato) |
| `… services ai-export` | **922 passed in 208,97 s** (A2 — consumatore di `RiskDrawdownOutput`) |
| `… utils test-runner-cli` | **19 passed in 0,10 s** (A2 — dopo il ripristino del blocco non mio) |
| `pipenv run python dev.py api schema` | rigenerato; i due campi presenti, **nessuno in `required`** |
| `ruff check` / `black --check` | puliti su tutti i file toccati |
| `lsof -nP -iTCP:6240 -sTCP:LISTEN` | nessun processo in ascolto |

---

## Contratti

| # | Verso | Stato |
|---|---|---|
| **K1** | E (via coordinatore → `contracts/K1.md`) | ✅ consegnato 2026-09-18 (passo A2) · ⚠️ ri-verificato in **Fuori pista 9**: il file non è committato, verifica invertita, **tre correzioni** trasmesse |
| cifre M2 | J (CHANGELOG) e I (pagina CVaR) | ✅ consegnate 2026-09-18 (passo A3) — tabella per confidenza, 2000 campioni |
| copertura reale | J e I, via coordinatore | ❌ **ritirato**: è la variabile sbagliata (Fuori pista 6). `coverage` ≈ 1,000 su dati sani mentre `f` ≈ 252 → misurarla restituirebbe un rassicurante **falso**. Sostituito dall'effetto diretto su Sharpe: **+0,03…+0,08** |

---

## Scoperte dell'analisi che vincolano l'esecuzione

Riassunte qui perché un agente con la memoria azzerata deve ritrovarle senza rileggere
tutto. L'analisi completa è stata consegnata al coordinatore.

1. **M2 sposta anche il VaR**, non solo il CVaR — 21/400 divergenze al 95%, peggio 5,56%.
   `06` §3 lo dichiarava «identico»: falso fuori dal singolo campione provato.
2. **«0,27%» è una media al 95%, non un limite** — al 99% il peggio misurato è 11,11%.
   Le cifre vere le produce l'oracolo, e vanno a J e a I: nessuno dei due le inventa.
3. **Il pavimento a zero è cablato nello schema** (`ge=0` a `schemas/risk.py:824-825`),
   non solo in `metrics.py`. **Tenuto** per decisione del coordinatore, e dichiarato a E.
4. **`undefined_windows` decide lo *stato* dell'API**, non un avviso
   (`signal_service.py:845`). Va coperto **prima** di M1.
5. **`MDD_Abs/MDD_Rel` = 1,0841 sul mio campione, non 1,11**: il rapporto dipende dai
   dati. Il test deve asserire «diversi», non «diversi dell'11%».
6. **I moltiplicatori di velocità di `06` §4.1 non sono stabili** (riscaldamento BLAS
   nelle misure a colpo singolo). Il caso regge — 1,4 s a 60 asset — ma i numeri precisi
   non vanno citati come se fossero riproducibili.
7. **Il tasso privo di rischio è cablato a 365 e l'errore vale `f = 365 × coverage`.**
   Segnalato come «sbagliato su serie settimanali o mensili»: **quel caso non esiste**,
   `RiskDataFrequency` ha la sola `DAILY`. Il difetto vive altrove ed è peggiore.
   LibreFolio riporta i prezzi in avanti sui weekend, quindi una serie **sana** ha
   `coverage = 1` e `f = 365`: il 365 cablato è **esattamente corretto**, errore zero.
   Ecco perché è sopravvissuto alla migrazione dal 252 — a copertura piena le due
   costanti coincidono, e nessuna fixture sana poteva vederlo.
   **L'errore compare quando la qualità dei dati peggiora, e lusinga sempre il Sharpe**:
   a `coverage = 2/3` con rf 5% il calcolo attuale pubblica **+0,1014** dove il valore
   corretto è **−0,0053** — *il segno si inverte*. La percentuale non va pubblicata
   (vicino allo zero esplode a valori privi di senso): si dice «può invertire il segno».
   ⚠️ Misurato sul codice e sulle fixture, **non su un portafoglio reale**: la copertura
   tipica in produzione non la conosco, quindi la gravità è da misurare, non da dedurre.

---

## ⚠️ Fuori pista 6 — la scoperta 7 qui sopra è SBAGLIATA. La ritratto.

Data: 2026-09-18. Origine: il coordinatore mi chiede di misurare la copertura reale
in A3; verificando *dove* leggerla ho scoperto che la relazione su cui poggiava tutta
la mia stima di gravità **non esiste sul ramo dove il difetto vive**.

### L'identità `f = 365 × coverage` vale su UN SOLO ramo, e lì il difetto è inerte

Ci sono **due sorgenti diverse** di `coverage`, e calcolano due rapporti diversi:

| Ramo | `coverage` | `f` | `f = 365·c`? |
|---|---|---|---|
| TWRR (`_portfolio_twrr_returns`, `service.py:872`) | `N/D` | `365·N/D` | ✅ sì |
| preparato (`series_preparation.py:345`) | `N/\|candidati\|` | `365·N/D` | ❌ **no** |

Sul ramo preparato **i denominatori sono diversi**: `coverage` misura la densità di
*quotazioni*, `f` la densità di *calendario*. Non sono la stessa cosa e non lo
diventano mai.

E sul ramo TWRR — l'unico dove l'identità regge — `coverage` vale **1,0 esatto per
costruzione** (`portfolio_engine.py:796,1074`: `current += timedelta(days=1)`, senza
filtro sui feriali), quindi `f = 365` esatto e **l'errore è esattamente zero, sempre**.

> **Cioè: dove l'identità vale, il difetto non morde. Dove il difetto morde,
> l'identità è falsa.** La mia cifra «a `coverage = 2/3` il segno si inverte» è stata
> ottenuta applicando l'identità sul ramo dove è falsa: **non descrive nulla di reale**.

### Il difetto non «compare quando i dati peggiorano»: è attivo su dati SANI

`candidate_quote_dates` (`series_preparation.py:236`) tiene solo i punti che passano
`_price_is_fresh` (`:123-125`), cioè **quotazioni vere, non riportate in avanti**.
Un sabato entra fra i candidati solo se un titolo ha scambiato davvero quel giorno.
Per un portafoglio azionario/ETF i weekend **sono esclusi per costruzione**:

```
candidati ≈ 252/anno   →   coverage = N/|candidati| ≈ 1,000
D = 365/anno           →   f = 365·N/D ≈ 252
```

**`coverage` segna 1,000 — salute perfetta — mentre `f ≈ 252`.** Il tasso diviso per
365 sottrae circa il 31 % in meno del dovuto, **su ogni Sharpe di ambito titolo con
rf ≠ 0, sempre, su dati perfettamente sani.**

Misurato con la funzione vera (`annualized_sharpe`, f = 252, coverage 1,000):

| rf | pubblicato | corretto | lusinga |
|---|---|---|---|
| 2 % | +1,2750 | +1,2420 | **+0,033** |
| 3 % | +1,2388 | +1,1897 | **+0,049** |
| 5 % | +1,1675 | +1,0864 | **+0,081** |

Stabile fra 1 e 3 anni (+0,0316 contro +0,0329 a rf 2 %): è una **distorsione
strutturale**, non un effetto di campione piccolo. Sempre a favore del portafoglio.

### Perché nessun test poteva vederlo — la trappola tautologica, seconda faccia

Il coordinatore mi aveva avvisato che misurare la copertura sarebbe stato tautologico
perché la griglia è di calendario. **Vale anche per le fixture**: quella di
`test_series_preparation.py:159-176` asserisce `f == 365,0` su una finestra
venerdì→lunedì, il che richiede quotazioni **fresche** di sabato e domenica.
La fixture **fabbrica un calendario contiguo** che il mercato non produce.
Nessuna suite esistente può osservare `f ≠ 365`.

### Conseguenze operative

1. **Non misurerò «la copertura reale» in A3**: è la variabile sbagliata. La gravità
   la governa `f`, cioè `N/D`, che il campo `coverage` **non riflette**.
2. **La direzione rivista di C è confermata, ma per un altro motivo**: il totale sta a
   `f = 365` esatto (non distorto), la fetta a `f < 365` (lusingata). Non perché la
   fetta abbia `coverage < 1` — può averla a 1,000 ed essere comunque distorta.
3. **A9 cambia peso**: non è una correzione per dati degradati, è una correzione che
   muove **ogni** Sharpe e Sortino di ambito titolo con rf ≠ 0. Per J la voce di
   CHANGELOG è una nota di rilascio vera, non una curiosità.
4. La cifra da citare è **+0,03…+0,08 di Sharpe lusingato**, non una percentuale.

---

## ✅ A3 — M2: CVaR allo stimatore coerente (2026-09-18)

> **Note implementazione**: `historical_var_cvar` adotta Acerbi-Tasche /
> Rockafellar-Uryasev. Perdite ordinate dal peggio, coda nominale
> `m = (1 − confidenza)·T`, osservazione di confine pesata per la **frazione** che
> ricade dentro la coda invece che contata intera. Aggiornati i due test che
> fissavano i valori vecchi, riscritto il test d'oracolo che fissava la divergenza,
> `historical_var.py` → `algorithm_version = "2.0.0"` e `method` da
> `historical_simulation_higher_quantile` a `historical_simulation_acerbi_tasche`
> (nessun consumatore: verificato su backend, frontend, test e documentazione).

**Verifica contro riskfolio** — la distorsione è sparita:

| misura | prima | dopo |
|---|---|---|
| delta medio (nostro − riskfolio) | −5,97·10⁻⁵ | **−4,27·10⁻¹⁸** |
| massimo \|delta\| su 2000 campioni | — | **2,78·10⁻¹⁷** |
| volte in cui il nostro è più basso | **2000/2000** | 1283/2000 (testa o croce) |

### Cifre per J (CHANGELOG) e I (pagina CVaR) — 2000 campioni, T = 750

| confidenza | VaR mediana | VaR peggiore | CVaR mediana | CVaR peggiore | CVaR sempre in su |
|---|---|---|---|---|---|
| 90 % | +0,435 % | **+4,587 %** | +0,364 % | +0,476 % | 2000/2000 |
| 95 % | 0,000 % | 0,000 % | **+0,267 %** | +0,404 % | 2000/2000 |
| 99 % | 0,000 % | 0,000 % | **+0,727 %** | +1,748 % | 2000/2000 |

**Il CVaR sale sempre** — 2000/2000 a ogni livello: stavamo sottostimando, e la
correzione va nella direzione prudente. L'entità **cresce con la confidenza** (meno
osservazioni in coda → il peso frazionario conta di più). **Il VaR si muove solo
quando `(1−c)·T` è intero**: a 90 % con 750 osservazioni `0,1·750 = 75`, e infatti
si muove; a 95 % (37,5) e 99 % (7,5) non si muove affatto.

> **⚠️ Consegnando queste cifre (2026-09-18) ho misurato la regola invece di dedurla.**
> La tabella qui sopra è a **T = 750** e gli `0,000 %` a 95 % e 99 % si prestano a essere
> letti come *«il VaR non cambia a quei livelli»* — che è **falso**. 24 combinazioni di
> confidenza × lunghezza di storia, 300 campioni ciascuna, **7 200 prove**:
>
> | conf | T=740 | 745 | 750 | 760 | 800 | 1000 | 1250 | 2000 |
> |---|---|---|---|---|---|---|---|---|
> | 90 % | **100 %** | 0 % | **100 %** | **100 %** | **100 %** | **100 %** | **100 %** | **100 %** |
> | 95 % | **100 %** | 0 % | 0 % | **100 %** | **100 %** | **100 %** | 0 % | **100 %** |
> | 99 % | 0 % | 0 % | 0 % | 0 % | **100 %** | **100 %** | 0 % | **100 %** |
>
> **Sempre 100 % o 0 %, mai una via di mezzo**: non è una tendenza, è deterministico.
> Spiega anche perché l'analisi iniziale riportava **21/400** al 95 % e questa tabella
> **0/2000** allo stesso livello: la prima era a T = 740 (`0,05·740 = 37`, intero), la
> seconda a T = 750 (`37,5`). Due misure indipendenti che concordano **solo** sotto questa
> regola.
>
> 🔴 **E la conseguenza è rovesciata rispetto all'intuizione.** La condizione è una
> **divisibilità** — multipli di 10 al 90 %, di 20 al 95 %, di 100 al 99 %. Quindi sono
> colpiti gli utenti con la storia più **tonda**: chi chiede esattamente 1 000 giorni è
> colpito a **tutti e tre** i livelli, chi ne ha 1 003 a nessuno. Un anno (250), due (500),
> tre (750) sono tutti multipli di 10. Non è una coda rara: i numeri tondi sono esattamente
> i divisibili, e sono ciò che un'interfaccia propone.
> Probe: `/tmp/libreFolio_A_m2_varrule.py`.

> **Il pavimento a zero resta, e ora la decisione è documentata invece che ereditata.**
> `06` §M2 chiedeva di mantenerlo o rimuoverlo *consapevolmente*. Va mantenuto perché
> **non è una scelta di presentazione**: `schemas/risk.py:854-855` dichiara entrambi i
> campi `Field(..., ge=0)` e un validatore `cvar >= var`. Senza pavimento una serie di
> soli guadagni produrrebbe un VaR negativo che Pydantic **rifiuterebbe al confine
> API**. Ai livelli di confidenza usuali il pavimento sulla coda non morde mai.

> **⚠️ Fuori pista 7 — la correzione era giusta in aritmetica esatta e sbagliata in
> virgola mobile.**
> `1.0 - 0.95` vale `0.050000000000000044`. A T = 740 la coda nominale diventa
> `37.00000000000003`, `ceil` sale a 38 e **rimette esattamente l'off-by-one che M2
> esiste per togliere**. Il CVaR quasi non se ne accorge (peso di confine ~3·10⁻¹⁴);
> il VaR è una **funzione a gradini** di quell'indice e si sposta di un'intera
> statistica d'ordine: **−1,31·10⁻⁴ misurati a T = 740**. Risolto agganciando il
> conteggio all'intero che sta cercando di essere.

> **⚠️ Fuori pista 8 — l'oracolo riproduceva il difetto che doveva arbitrare.**
> Il test nuovo è fallito al primo giro su tutti e quattro i T. Causa: `_TAIL_ALPHA`
> era scritto `1.0 - _CONFIDENCE_LEVEL`, e riskfolio moltiplica alpha per T e fa
> `ceil` — ricevendo il valore sottratto **cade sullo stesso indice sbagliato**.
> `_TAIL_ALPHA` ora è `0.05` esatto, con la spiegazione accanto alla costante.
> **Un oracolo è un oracolo solo se gli si passa il parametro esatto.**

### Evidenza

| Comando | Esito |
|---|---|
| `… services risk-all` (1ª) | 2 failed, 171 passed — **i due test che fissavano il comportamento vecchio**, come previsto |
| `… services risk-all` (2ª) | 4 failed, 173 passed — il test nuovo, `_TAIL_ALPHA` sottratto |
| `… services risk-all` (3ª) | **177 passed in 29,83 s** |
| `ruff` + `black` | puliti su tutti e 4 i file toccati |

### 🔴 Il cancello `api risk` NON è eseguibile in questo worktree

```
❌ Failed to download https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js:
   [SSL: CERTIFICATE_VERIFY_FAILED] Missing Authority Key Identifier
❌ Resource cache incomplete - aborting frontend build
❌ Frontend build failed. Server not started.
```

`server --test` ricostruisce il frontend. Mancano **due** pezzi, non uno:
`mkdocs_src/docs/javascripts/vendor/tex-mml-chtml.js` **assente** (la directory ha il
solo `.cache_manifest.json`) e `frontend/node_modules` **assente**. I font
noto-color-emoji invece ci sono: la semina è arrivata a metà.

Non scarico, non copio da un altro checkout, non lancio `npm ci` senza autorizzazione.
**Rosso d'infrastruttura prima di pytest, non un fallimento di prodotto.**

Esposizione reale: `test_risk_api.py:448` asserisce **solo**
`cvar >= var >= 0` — invariante che la mia implementazione garantisce per costruzione
e che l'oracolo già fissa a livello di servizio. È una lacuna sul **trasporto**, non
sulla matematica.

---

## ⚠️ Fuori pista 9 — K1 verificato al contrario, e tre correzioni (2026-09-18)

Il coordinatore ha messo il contratto su `implementation/contracts/K1.md`, trascritto
dal mio messaggio, chiedendomi di rileggerlo «fra un passo e l'altro» perché un errore
di trascrizione sarebbe peggio del contratto mancante.

**Non ho potuto leggerlo, e la ragione è strutturale.**

```
git ls-tree e-alfy-risk-management-replan …/contracts/   →  solo README.md
git log --oneline -1 e-alfy-risk-management-replan       →  cc33120eb  (= la mia baseline)
```

Il file è un file di lavoro **non committato** nel worktree del coordinatore, e leggere
il worktree di un altro mandato è vietato. L'object store condiviso in sola lettura —
che è lecito — non lo contiene.

> **La lezione, per la campagna intera**: un contratto scambiato fra mandati esiste solo
> quando è **committato**. Finché resta nel working tree di chi lo scrive, è invisibile a
> chiunque debba verificarlo, e la verifica incrociata che gli dà valore non può avvenire.

Ho quindi **invertito la direzione**: invece di rileggere la prosa altrui, ho estratto la
firma dal codice vivo e l'ho rimandata al coordinatore perché diffi lui. È comunque più
solido dell'originale, perché la fonte di verità è `schemas/risk.py`, non il mio
messaggio precedente — che poteva a sua volta contenere un errore mio.

### Tre correzioni trovate, in ordine di pericolo

1. 🔴 **I campi additivi sono TRE, non due**: `return_bins`, `var_bin_edge`,
   `underwater_series`. Il coordinatore ne annunciava due. Il candidato più probabile a
   essere caduto è `var_bin_edge`, che è **l'unico ponte fra le due convenzioni di
   segno**: senza, E non può disegnare la linea del VaR sull'istogramma, perché il
   pavimento a zero è una funzione **non invertibile** e non si può risalire dal valore
   positivo al taglio firmato.
2. **Lo stato «concordato, non ancora implementato» è invecchiato**: lato produttore K1
   è chiuso da A2 e verde. La firma non è più a costo zero da cambiare — è fissata dai
   test e da due `algorithm_version` già incrementate.
3. **Nessuna delle due liste è limitata dallo schema**: il tetto di 200 bin è solo lato
   produttore (`metrics.py:13`), e `underwater_series` **non è decimato** —
   `drawdown_summary.py:61` emette un punto per osservazione, ~750 per tre anni daily.
   Scelta giusta (una curva underwater decimata mente sui minimi) ma da dichiarare.

### Garanzie confermate sul codice, su cui E può costruire

| Garanzia | Dove |
|---|---|
| `return_bins` ordinato per `lower_bound` crescente | validatore `risk.py:866` |
| intervallo semiaperto `[lower, upper)`, ultimo bin chiuso | docstring `risk.py:820` |
| rapporti decimali ovunque, mai percentuali | docstring, entrambi i modelli |
| `drawdown` mai positivo | `le=0` + `min(0.0, value)` a `drawdown_summary.py:61` |

Quel `min(0.0, value)` è **portante, non cosmetico**: un nuovo massimo può calcolare
`+1e-17` e Pydantic rifiuterebbe il payload. Stessa famiglia del `max(cvar, var)` di A3.

---

## ✅ A4 — M1: vettorializzazione dei segnali rolling (2026-09-18)

### Due presupposti del piano, falsificati prima di scrivere codice

**1. 🔴 M1 non è implementabile dove il piano lo colloca.**
Doc 06 §M1 indica `signal_helpers.py:69-108`, cioè `rolling_single_values` e
`rolling_pair_values`. Ma quelle sono **funzioni di ordine superiore generiche**: prendono
`metric: Callable` e non sanno quale metrica stiano applicando. L'unico modo di
vettorializzare un callable arbitrario è `.rolling().apply(f)`, che resta **interpretato** —
cioè non migra niente. La tabella di doc 06 è **per segnale**, e il segnale è noto solo ai
quattro call site. L'estensione di confine ai quattro `rolling_*.py` era quindi
**strutturalmente necessaria, non una comodità**.
`calendar_rolling_return.py` non usa gli helper e resta fuori: i plugin rolling sono cinque,
i migrati sono quattro.

**2. 🔴 «A valori identici» è falso.** Zero su quattro sono bit-identici. Le metriche usano
`math.fsum` (somma esattamente arrotondata), pandas usa somme incrementali.
Deriva relativa massima misurata:

| Segnale | Deriva rel. max |
|---|---|
| `rolling_return` | 9,77e-12 |
| `rolling_beta` | 1,06e-13 |
| `rolling_sharpe` | 6,08e-14 |
| `rolling_volatility` | 1,24e-15 |

`np.allclose` (rtol 1e-5) passa con **sette ordini di margine** sulla soglia del piano
stesso. Accettato — ma ha una conseguenza operativa: **la baseline di M6 è post-M1**,
altrimenti un delta a 1e-12 verrà attribuito a M6 che non l'ha prodotto.

### La regola di M1, in una riga

L'indefinito si prova **sul denominatore**, mai leggendo il `NaN` in uscita; il warm-up si
decide **per indice** (`< window-1`). Warm-up e indefinito sono lo **stesso float**, e non
sono distinguibili a valle — già fissato da
`test_pandas_rolling_cannot_distinguish_warm_up_from_undefined_windows` (scritto in A1).

I buchi restano riproducibili: `pandas.rolling().var()` su 61 finestre perfettamente
costanti dopo una regione volatile ha restituito **esattamente 0.0, 61 volte su 61**. Il
test `abs(x) <= ZERO_TOLERANCE` continua quindi a scattare.

### ⚠️ Fuori pista 10 — `window=1`: il vettoriale pubblicava NaN dove il ciclo rifiutava

Trovato dal test differenziale di `test-author`, **non** dal mio probe: il probe confrontava
valori, e due `NaN` non sono mai uguali, quindi non si accorgeva di niente.

- **Ciclo**: `sample_variance` rifiuta — `ValueError("sample variance requires at least two
  observations")` — per volatility, sharpe, beta.
- **Vettoriale**: `calc_var` di pandas pretende `nobs > ddof` → `NaN` ovunque. E il test
  dell'indefinito guarda il **denominatore**, com'è giusto; `NaN <= 1e-15` è `False`.
  Risultato: **ogni cella pubblicata come valore, con `undefined_windows == 0`**.
  Beta ci arriva per un'altra strada: `count/(count-ddof)` in `cov` → `0.0 * inf` → `NaN`.
- **Non raggiungibile via API**: volatility, sharpe e beta dichiarano tutti
  `window: int = Field(..., ge=2)`.

**Chiuso comunque**, per due ragioni. Il contratto di M1 è che il comportamento non cambia,
e un `NaN` silenzioso dove prima c'era un'eccezione **è** un cambiamento. E il `NaN` non
restava silenzioso a lungo: `SignalValuePoint.value` è `Optional[FiniteFloat]`, quindi
sarebbe riemerso come errore Pydantic in fase di costruzione dell'output — lontano dalla
causa e illeggibile.

Fix: `_require_dispersion_window(window)` nei tre helper `ddof=1`, **dopo** il
corto-circuito `observations < window`. **L'ordine è portante**: il ciclo con
`observations=0, window=1` non entra mai nel corpo e quindi **non** solleva; invertire i due
controlli creerebbe una divergenza nuova al posto di quella chiusa. Il caso è fissato in
coda al test.

> Il test `test_a_window_of_one_is_the_only_place_…` fissava la divergenza e avvisava in
> docstring che «rendere gli helper eccezionali non può succedere in silenzio». Ha fatto
> esattamente il suo mestiere: l'ho riscritto deliberatamente in
> `test_a_window_of_one_refuses_a_dispersion_statistic_on_both_paths`, che ora pretende
> **lo stesso messaggio** sui due rami, non solo un pattern compatibile.

### ⚠️ Fuori pista 11 — restringimento deliberato sul rendimento composto

`compounded_return` accetta esattamente `-1.0` e risponde `-1.0`: perdita totale.
`rolling_compounded_return_values` **non può seguirlo lì**. `log1p(-1)` è `-inf`, e un
accumulatore rolling che somma e poi **toglie** `-inf` resta con `NaN` per ogni finestra
successiva: il danno sopravvive alla finestra che l'ha causato. In forma scalare `-1` è
innocuo, in forma vettoriale è **contagioso**.

Restringimento dichiarato: `finite` **e** `> -1.0` (lo scalare tollera `>= -1.0`).
Non osservabile in produzione — `AssetReturnPoint.value` è `FiniteFloat` con `gt=-1`
(`schemas/risk.py:305`) — quindi il guard protegge solo i chiamanti diretti.
**Va segnalato al coordinatore come divergenza voluta**, non come equivalenza.

### Evidenza

| Comando | Esito |
|---|---|
| `services risk-oracle` | **131 passed** in 4,39 s |
| `services risk-all` | **265 passed** in 27,79 s (era 177) |
| `services signal-contracts` | 10 passed |
| `services signal-service` | 45 passed |
| `services signal-plugin-matrix` | 65 passed |
| `services signal-registry` | 68 passed |
| `ruff check` · `black` | puliti sui file toccati |
| `git diff --check` | pulito |
| `lsof -nP -iTCP:6240 -sTCP:LISTEN` | **porta libera** |

Forma: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
--test-port 6240 --data-dir backend/data/test-risk-a services <SEL>`.

**Le 19 funzioni di `test-author` sono passate tutte alla prima esecuzione**, comprese le
due derivazioni che lui stesso aveva marcato ad alto rischio non avendo una lane per
misurarle: il modello delle maschere `isna`/`isinf` (12 parametrizzazioni) e l'asserzione
beta a primario piatto con appena ~2,5× di margine su `abs=1e-12`.

### Costo misurato, che il piano dava solo in rapporti

| Finestra | Prima (ms) | — |
|---|---|---|
| 1 anno | 11,6 | |
| 3 anni | **45,9** | caso tipico |
| 5 anni | 81,2 | |
| 10 anni | 168,5 | |
| peggiore ammesso dallo schema (W=500, T=2500) | sharpe 289 + beta 355 | |

Dopo, a T=1250: **80,4 ms → 1,26 ms**.

### Non fatto

`api risk` resta **non eseguibile in questo worktree** per la ragione infrastrutturale già
registrata sopra (mathjax + `node_modules`), che **non** è un rosso di prodotto e **non** è
stata introdotta da A4.

---

## ✅ A5 — M3: matrici a NumPy (2026-09-18)

### 🔴 Scoperta 1 — `correlation_matrix` non ha NESSUN chiamante di produzione

Doc 06 §M3 intesta l'intervento a «`correlation_matrix`, `covariance_matrix`» e gli
attribuisce «3 682 ms → 0,2 ms su cento asset». Ma:

| Funzione | Chiamanti reali in `backend/app/` |
|---|---|
| `correlation_matrix` | **nessuno** — compare solo in `__all__` |
| `covariance_matrix` | `risk_plugins/risk_contribution.py:58` ✅ |
| `pairwise_correlation` | `risk_plugins/correlation.py:72`, in un doppio ciclo **N²** ✅ |

Il plugin di correlazione **non usa** `correlation_matrix`: chiama `pairwise_correlation`
N² volte. Quindi il guadagno intestato a `correlation_matrix` **nessun utente lo vedrebbe**:
il costo vero è nel doppio ciclo, che doc 06 nomina ma come terzo elemento.
`correlation_matrix` è stata vettorializzata comunque — è API pubblica ed è nel mandato —
ma **il beneficio misurabile viene tutto dal ciclo del plugin**.

### 🔴 Scoperta 2 — `min_coverage` è un controllo INERTE, e `coverage` è sempre 1.0

`CorrelationParams.min_coverage` è un parametro utente con chiave i18n
(`risk.params.minCoverage`), `x-control-order: 2` e step 0,05 — cioè **uno slider visibile
nell'interfaccia**. È dichiarato `Field(0.6, ge=0, le=1)`.

Ma `coverage` nel plugin vale **identicamente 1.0**, sempre. La catena, tutta verificata:

1. `prepared_asset_returns` restituisce `tuple[float, ...]` — **nessun `None`**;
2. il validatore di `PreparedAssetSeriesSet` (`schemas/risk.py:424`) **rifiuta** qualunque
   set i cui membri non condividano il calendario: *«every asset series must use the same
   joint calendar and target currency»*;
3. quindi `len(serie) == n_observations` per ogni asset, e `expected == n_observations`;
4. quindi `coverage = observations / expected = 1.0`;
5. `service.py:230` non esegue nemmeno l'analitica sotto `min_observations = 2`, quindi il
   caso degenere `n_observations = 0` non arriva mai a `compute()`.

Con `coverage ≡ 1.0` e `min_coverage ≤ 1`, la condizione `coverage < min_coverage` è
**sempre falsa**. L'avviso `low_coverage` **non può scattare**.

**Prova empirica** (`/tmp/libreFolio_A_m3_coverage_probe.py`), non lettura del codice:
costruito un set reale a 3 asset che il validatore **accetta**, eseguito il plugin col
valore **più severo che Pydantic consenta**, `min_coverage=1.0`:

```
distinct coverage values across 9 cells: [1.0]
distinct observations values: [40]
warnings emitted at min_coverage=1.0: ['flat_series']
VERDICT low_coverage reachable: NO
```

e, sull'altro lato, un set volutamente irregolare viene **rifiutato**:

```
REJECTED -> Value error, every asset series must use the same joint calendar and target currency
```

> **Non l'ho rimosso.** Togliere un parametro utente tocca i18n e frontend, ed è una
> decisione di prodotto, non mia. **Va deciso dal coordinatore.** Stessa famiglia della
> scoperta A9: una grandezza che *sembra* per-cella ed è strutturalmente costante.
> Qui però il controllo è **visibile all'utente**, il che la rende peggiore.

### 🔴 Scoperta 3 — la trappola del quasi-piatto, peggiore di quella di M1

| Serie | `sample_standard_deviation` | ciclo scalare | `np.corrcoef` |
|---|---|---|---|
| esattamente piatta | 0,000e+00 | `None` | `nan` |
| **quasi piatta** | 1,001e-17 | `None` | **−0,02010614683967737** |

Sulla serie esattamente piatta le due letture **coincidono per caso**, perché `0/0` è `nan`.
Su una serie con dispersione soltanto **trascurabile**, NumPy divide due quantità denormali
e restituisce **un numero finito, plausibile e privo di significato**.

In M1 leggere il `nan` in uscita dava comunque un `nan`, cioè qualcosa di **visibile**. Qui
darebbe **−0,02**: una correlazione che nessuno metterebbe in dubbio guardandola.
**La regola è la stessa di M1, e qui vale di più**: l'indefinito si prova sul
**denominatore** — le deviazioni standard contro `ZERO_TOLERANCE` — mai sul `nan` in uscita.

Corollari verificati:
- **nessuna contaminazione**: aggiungere un asset piatto sposta le altre celle di
  **esattamente 0.0**, e i `nan` restano confinati alla sua riga e colonna;
- una serie **costante non nulla** (tutti `0.004`) è piatta anch'essa → `None`, non 1.0;
- **la diagonale non è esattamente 1.0 su nessuno dei due rami** — preesistente, entrambi
  si affidano al clamp in `[-1, 1]`. Da non «aggiustare»: sposterebbe numeri pubblicati.

### Equivalenza e deriva

| Confronto | Deriva massima |
|---|---|
| correlazione, ciclo vs vettoriale | 1,11e-16 assoluta |
| covarianza, ciclo vs `np.cov` | 1,185e-13 **relativa** |
| collocazione dei `None`, 5 scenari | **identica** (11 · 11 · 20 · 11 celle) |

Ancora `math.fsum` contro somma incrementale: **non** bit-identiche, ben dentro
`rel=1e-9`.

### Misura end-to-end, sul cammino che l'utente percorre davvero

| Asset | Prima (ciclo N²) | Dopo | Guadagno |
|---:|---:|---:|---:|
| 5 | 11,9 ms | 0,317 ms | 37× |
| 10 | 47,1 ms | 0,608 ms | 77× |
| 25 | 296,7 ms | 1,523 ms | 195× |
| 50 | 1 195,9 ms | 4,637 ms | 258× |
| 100 | 4 754,7 ms | 8,746 ms | 544× |
| **100, T=2500 (10 anni)** | **15 987 ms** | **21,6 ms** | **742×** |

Sedici secondi. `compute()` gira in `asyncio.to_thread` (`base.py:242`), quindi non
bloccava il loop — ma l'utente li aspettava comunque.

### Una micro-ottimizzazione che ho deciso di NON fare

Scomposizione del residuo a N=100, T=2500:

| Fase | Costo |
|---|---|
| `_finite_values` (validazione pura-Python) | **13,22 ms — 61 %** |
| `np.asarray` | 4,32 ms |
| **la matematica vera** | **2,76 ms** |

La validazione costa cinque volte il calcolo. Vettorializzarla porterebbe a ~8 ms.
**Non l'ho fatto**, per tre ragioni: `_finite_values` è condivisa da tre funzioni; l'ordine
attuale dei controlli fa vincere *«must be finite»* su *«common calendar»* su un input
patologico, e qualunque riscrittura lo cambierebbe; e 13 ms su un'operazione che avviene
una volta per richiesta **non li percepisce nessuno**. Il guadagno percepibile è già
incassato. Resta scritto qui, se il coordinatore la vuole.

### Evidenza

| Comando | Esito |
|---|---|
| `services risk-all` (prima della rete durevole) | **265 passed** in 28,95 s |
| probe plugin (post-migrazione) | coverage `[1.0]`, observations `[40]`, warning `['flat_series']` — invariato |
| probe design, 5 scenari | `ALL SCENARIOS AGREE` |
| `ruff` · `black` | puliti su `metrics.py` e `correlation.py` |

### Chiusura di A5 — la rete durevole (Blocco h)

`test-author` ha consegnato **14 funzioni / 27 casi** senza mai eseguirli (non ha la lane),
accompagnati da una **classifica delle otto ipotesi più a rischio**. Eseguiti nella lane:

| Comando | Esito |
|---|---|
| `services risk-oracle` | **158 passed** in 5,54 s (era 131) |
| `services risk-all` | **292 passed** in 39,55 s (era 265) |
| `ruff check` · `black --check` sull'oracolo | puliti |
| `git diff --check` | pulito |
| `lsof -nP -iTCP:6240 -sTCP:LISTEN` | **porta libera** |

**Tutte e otto le ipotesi a rischio sono passate.** Tre meritano di essere registrate,
perché erano affermazioni che nessuno di noi due poteva provare a tavolino:

1. **`drift == 0.0` sull'append 6→7 asset.** Passare da `(6,120)@(120,6)` a
   `(7,120)@(120,7)` cambia M ed N ma non l'ordine di accumulazione su K=120 dentro il
   micro-kernel BLAS. L'ipotesi regge: **l'aggiunta di un asset piatto lascia le celle
   esistenti bit-identiche**, non «quasi». È la stessa proprietà che avevo misurato nel
   probe, ora fissata da un test.
2. **Il cancello di simmetria a `rel_tol=1e-12`.** Prima di M3 la simmetria era gratis,
   garantita dal determinismo di `math.fsum`; dopo M3 è un'affermazione **nuova**, e
   `risk_contribution.py` solleverebbe *«covariance matrix must be symmetric»* a runtime
   se cadesse. Verde: `np.cov` è simmetrica bit a bit qui, e **non serve** il
   `c = (c + c.T) / 2` che avremmo dovuto aggiungere in `metrics.py`.
3. **Il collasso dimensionale su un asset solo.** `np.cov` termina con `c.squeeze()` e
   `np.corrcoef` intercetta il `ValueError` di `diag`: entrambe restituiscono uno **0-d**.
   L'`np.atleast_2d` che avevo messo non era prudenza, era necessario — e ora c'è un test
   che lo dice, invece di un commento.

> **Nota di manutenzione**: due asserzioni del blocco leggono interni di `numpy 2.5.3`
> (`ndim == 0` su `cov`/`corrcoef` a riga singola). Documentano *perché* esiste
> `atleast_2d`; il contratto vero sono le asserzioni di forma sotto di esse. Se un
> aggiornamento di NumPy le rompe, si tolgono quelle due righe — non si tocca il resto.

---

## 🔍 A6 — M6: analisi PRIMA di toccare, e la raccomandazione che ne esce

M6 è l'unico passo del mandato la cui giustificazione è **estetica** e non misurata:
«Non esiste ragione per tenerli in `math` puro» (doc 06 `:575`). Ho misurato.

### I nove composti, con i chiamanti veri

| Funzione | Riga | Chiamanti di produzione |
|---|---|---|
| `wealth_index` | 241 | **interni**: `summarize_drawdown:257`, `drawdown_episodes:315`, `comparison_summary:670-671` |
| `summarize_drawdown` | 251 | `historical_kpi.py:72` |
| `drawdown_episodes` | 292 | `drawdown_summary.py:53` **e `ai_export/components/drawdown_context.py:499`** |
| `pairwise_correlation` | 440 | **nessuno** — glielo ho tolto io in A5 |
| `comparison_summary` | 650 | `comparison.py:88` |
| `period_returns_from_cumulative` | 417 | `service.py:867` |
| `horizon_compounded_returns` | 687 | `metrics.py:735`, dentro `historical_var_cvar` |
| `current_buy_and_hold_returns` | 588 | `stress.py:485` **e** `service.py:617` |
| `annualized_sortino` | 195 | `historical_kpi.py:81` |

> Mi ero appuntato che `wealth_index` e `horizon_compounded_returns` fossero morte.
> **Era sbagliato, e l'ho verificato prima di dirlo**: la prima è la primitiva condivisa da
> tre composti, la seconda sta sul cammino caldo del VaR. Il `grep` sui soli
> `risk_plugins/` non le vedeva perché sono chiamate **dentro `metrics.py`**.

### La misura che cambia il giudizio su M6

| Funzione | T=750 (3 anni) | T=2500 (10 anni) |
|---|---:|---:|
| `wealth_index` | 0,078 ms | 0,252 ms |
| `summarize_drawdown` | 0,218 ms | 0,740 ms |
| `drawdown_episodes` | 0,267 ms | 0,879 ms |
| `comparison_summary` | 1,343 ms | **4,404 ms** |
| `period_returns_from_cumulative` | 0,093 ms | 0,315 ms |
| `horizon_compounded_returns` h=1 | 0,454 ms | 1,596 ms |
| `horizon_compounded_returns` h=10 | 0,973 ms | 3,296 ms |
| `current_buy_and_hold_returns` | 1,479 ms | **5,127 ms** |
| `annualized_sortino` | 0,124 ms | 0,406 ms |
| `pairwise_correlation` (una coppia) | 0,463 ms | 1,556 ms |

**Nessuna supera i 6 ms a dieci anni.** Nessuna è dentro un ciclo: ho verificato che
`current_buy_and_hold_returns` in `stress.py` sta **dopo** il ciclo sugli asset (riga 473
contro ciclo a 451), quindi è chiamata una volta per analitica.

Il confronto è impietoso:

| Passo | Cosa ha comprato |
|---|---|
| M1 | 80,4 ms → 1,26 ms |
| M3 | **15 987 ms → 21,6 ms** |
| **M6 così com'è** | **~20 ms in tutto**, sparsi su nove funzioni |

E sono le nove funzioni con la semantica **più delicata** del modulo: convenzioni di segno,
`None`, buchi, una macchina a stati con ramo di recupero che porta già un
`# noqa: C901 — TODO(P2-refactor)`.

### Raccomandazione — M6 va diviso in quattro fasce, non eseguito in blocco

**Fascia 0 — ESCLUDERE per ragioni strutturali: `pairwise_correlation`.**
Dopo M3 non ha chiamanti di produzione: **è la semantica scalare di riferimento** contro
cui la matrice vettoriale viene testata. Vettorializzarla trasformerebbe il test
differenziale in NumPy-contro-NumPy, che **non dimostra niente**. Vale identico per i due
helper a ciclo che M1 ha lasciato in `signal_helpers.py`.
> La lista di M6 è stata scritta **prima** che M1 e M3 esistessero nella forma finale.
> **M6 non deve migrare ciò che M1 e M3 hanno deliberatamente lasciato indietro come
> oracolo.**

**Fascia 1 — FARE, rischio zero: `wealth_index` → `np.cumprod`.**
Verificato **bit-identico**, 6 casi su 6, T=750 e T=2500, compresa una perdita totale a
`-1.0`: `max|delta| = 0.000e+00`, nessun `nan`. È l'**unica** migrazione della campagna a
deriva nulla, perché `cumprod` esegue le stesse moltiplicazioni nello stesso ordine — non
c'è riassociazione, a differenza di `fsum` contro somma incrementale.
Ed è la primitiva di **tre** composti: si velocizzano `summarize_drawdown`,
`drawdown_episodes` e `comparison_summary` **senza toccarne le macchine a stati**.

**Fascia 2 — solo con una ragione vera**: `comparison_summary` (4,4 ms) e
`current_buy_and_hold_returns` (5,1 ms), le due maggiori. Restano 5 ms.

**Fascia 3 — raccomando di NON fare**:
- `horizon_compounded_returns` — 🔴 a `horizon_days=1` **non** è identità
  (`compounded_return([v])` = `1.0*(1.0+v)-1.0`). Una riscrittura che scorciatoi l'orizzonte 1
  **sposta il VaR pubblicato**. Rischio alto per 1,6-3,3 ms.
- `summarize_drawdown` / `drawdown_episodes` — sensibilità a **1 ULP** già documentata
  contro `MDD_Rel`, convenzioni di segno opposte dentro riskfolio stesso, macchina a stati
  con ramo di recupero. 0,7-0,9 ms.
- `annualized_sortino`, `period_returns_from_cumulative` — 0,3-0,4 ms: non c'è niente da
  vincere.

**Non decido io**: M6 è nel mandato e il taglio è una scelta di campagna.
Consegno la misura e aspetto.

---

## 🤝 Contratti inversi richiesti da C e da N (2026-09-18)

Due mandati si appoggiano a funzioni che M6 avrebbe potuto toccare e chiedono garanzia di
invarianza **prima** che M6 atterri. Verificato sul codice vivo + probe in sola lettura
(`/tmp/libreFolio_A_contract_probe.py`). **Entrambe le garanzie concesse.**

### C — `current_buy_and_hold_returns`: semantica confermata, firma smentita

**Non rinormalizza dentro** — provato per differenza, non per lettura: pesi grezzi
`{0.30, 0.20}` + cash `0.50` danno `0.0320…`, gli stessi rinormalizzati `{0.60, 0.40}` +
cash `0.0` danno `0.0640…`. Rapporto **≈ 2,0**. Se rinormalizzasse, sarebbero identici.

Ma la firma citata da C **non esiste**: `rows` e `usable_weights` sono le variabili locali di
`service.py:608`, non i parametri. I veri nomi sono `returns_by_asset` e `weights`, e la
chiamata per nome dà `TypeError`. `cash_weight` è `float | None`, e col `None` viene derivato
**senza** il pavimento a zero che il chiamante attuale applica.

🔴 **La trappola è altrove.** C teme una doppia rinormalizzazione silenziosa. Ma la funzione
*valida* `Σpesi + cash == 1` a `abs_tol=1e-9, rel_tol=0.0`: una somma sbagliata **solleva**,
non mente. Il silenzio vero è che **rinormalizzare a monte e passare `cash_weight=0.0` è
accettato senza protesta e risponde a una domanda diversa** — «cosa sarebbe successo se
avessi tenuto solo questi» invece di «cosa hanno fatto questi dentro il portafoglio vero».
Entrambe corrette prese da sole, diverse del doppio. Il pericolo vive nel codice di C, non in
M6.

> **Conseguenza su M6**: `current_buy_and_hold_returns` **esce dalla Fascia 2 ed è ESCLUSA**.
> 5,1 ms non valgono un contratto condiviso, e un rischio che era solo mio ora sarebbe anche
> di C.

### N — `summarize_drawdown`: l'argomento regge alla prova che poteva ucciderlo

N sostiene che `max_drawdown ≡ −MDD_Rel` è vero **per costruzione**. L'algebra è giusta, ma
poggia su un'assunzione tacita: che **anche riskfolio** cumuli includendo il punto
pre-rendimento. Se partisse da `1+r₀`, un crollo alla **prima** osservazione sarebbe
invisibile a lui e visibile a noi. Il campione originale non conteneva quel caso: l'ho
costruito.

| Caso | Esito |
|---|---|
| random, drawdown interno (T=400) | identici |
| **peggiore alla prima osservazione** | **identici** |
| monotona crescente / decrescente | identici |
| quasi-perdita totale · recupero esatto al picco | identici |

**6/6 bit-identici** (`delta == 0.0`, non `approx`). `drawdowns` è **T+1**, `drawdowns[0] == 0.0`.

### 🔴 Fuori pista 12 — `summarize_drawdown` solleva sulla perdita totale

Non cercato: caduto dal probe.

```
ValueError: drawdown values must be finite and positive
  metrics.py:231 underwater_drawdown ← metrics.py:267 summarize_drawdown
```

**Due funzioni dello stesso modulo non sono d'accordo sullo stesso valore**: `wealth_index`
ammette esplicitamente `-1.0` (`if value < -1.0: raise`) e produce ricchezza `0.0`;
`underwater_drawdown` rifiuta lo `0.0` che l'altra ha appena prodotto. La perdita totale è
rappresentabile a metà strada e non arriva in fondo.

Irraggiungibile per la via preparata (`AssetReturnPoint.value` è `gt=-1`) — **stessa classe
di protezione trovata in M1**, terza volta che uno schema salva un difetto di `metrics.py`.
**Non verificata la via TWRR** (`_portfolio_twrr_returns`): segnalata a N, che integra CDaR e
UCI proprio sulla coda dei drawdown. Non lo tocco: fuori mandato, e cambierebbe un
comportamento pubblicato.

> Nota per M6: la perdita totale che ho verificato bit-identica su `np.cumprod` è
> **irraggiungibile attraverso `summarize_drawdown`**. La migrazione resta sicura; la
> copertura di quel caso è più teorica di quanto sembrasse.

### Catalogo dei test — la diagnosi di N è metà sbagliata

✅ `RISK_SERVICE_TEST_PATHS` è una tupla **letterale**, nessuna discovery: un file non
elencato non gira sotto `risk-all`.
❌ Ma il gate **non** resta verde: `dev.py test check-orphans` (`_cli.py:155`) scandisce le
directory reali e segnala i non registrati come **rosso esplicito**.
⚠️ Due cautele: è un **comando a sé**, non incluso in nessuna suite; e accerta la
registrazione con una **regex sul testo** dei runner — prova che il percorso è *nominato*,
non *raggiungibile* (per quello c'è `_check_unreachable_tests()` a `:653`).

**Riga concessa a N** appena mi dà il nome del file. Che apra il file che gli serve invece di
comprimere i test in `test_risk_analytics.py` per schivare un problema che ha un rilevatore.

### 🟠 Buco di K1 che la nuova regola di proprietà mi impedisce di tappare

I tre campi K1 compaiono in **un solo** file di test — il mio oracolo, 10 occorrenze. In
`test_risk_schemas.py`, ora dichiarato di **C**: **zero**.

L'oracolo copre il lato **produttore** (contiguità, conservazione dei conteggi,
`var_bin_edge == -value_at_risk`, il bordo che cade su un confine). Scoperto il lato **schema**:

- il validatore a `schemas/risk.py:866` (*«return_bins must be ordered by ascending
  lower_bound»*) non ha un test che ne provi il **sollevamento**;
- `RiskDrawdownPoint.drawdown le=0` non ha un test di rifiuto;
- 🔴 **che un `RiskVarCvarOutput` costruito senza i tre campi validi ancora** grazie ai
  `default_factory` — l'affermazione su cui poggia **tutto** il disegno additivo di K1, quella
  che garantisce che E, il client generato e i mock E2E non si rompano. **È l'unica non
  provata.**

Proposto al coordinatore: scrivo io un blocco in coda concordato con C. Non entro nel file
senza il suo assenso.

---

## 🔬 A9 — dove morde davvero il 365 cablato (2026-09-18)

Il coordinatore ha relayato una scoperta di **I**: `portfolio_engine` avanza
`current += timedelta(days=1)` senza filtro sui feriali, quindi `D = N` e la copertura è
**1,0 per costruzione**. Da lì ha concluso che la domanda è cambiata — non *«quanto vale la
copertura»* ma *«in quali casi reali `D > N`»* — e che se la risposta è «nessuno sul percorso
di portafoglio», allora il difetto ha **ampiezza zero sul totale** e lo subisce **solo la
fetta**.

**La conclusione è giusta per un ramo e sbagliata per l'altro, perché i reticoli sono due.**

### I due reticoli non sono lo stesso reticolo

| Ramo | Da dove nasce la griglia | Riferimento |
|---|---|---|
| **TWRR / portafoglio storico** | `portfolio_engine`, giorno di calendario per giorno | `service.py:871` |
| **preparato** | **unione delle date di quotazione reali** degli asset | `series_preparation.py:236` |

Il secondo non cammina su un calendario: prende le date che i **provider** hanno davvero
prodotto. Per azioni ed ETF sono **giorni di borsa**.

### Misurato

| reticolo | anni | N | D | fattore | 365 giusto? |
|---|---:|---:|---:|---:|---|
| calendario pieno (TWRR) | 1 / 3 / 5 | 365 / 1095 / 1825 | = N | **365,00** | ✅ esatto |
| giorni di borsa (preparato) | 1 / 3 / 5 | 261 / 783 / 1304 | 365 / 1095 / 1824 | **261,00** | ❌ **1,3985×** |

Il tasso giornaliero cablato è **sottostimato del 28,5 %** sul ramo preparato
(`rf=2 %`: `0,0000542552` invece di `0,0000758750`).

### Lo scarto sullo Sharpe pubblicato

| rf annuo | TWRR (365) | preparato (261) |
|---:|---:|---:|
| 0 % | 0,0000 | 0,0000 |
| 1 % | 0,0000 | **+0,0165** |
| 2 % | 0,0000 | **+0,0328** |
| 3 % | 0,0000 | **+0,0489** |
| 4 % | 0,0000 | **+0,0649** |
| 5 % | 0,0000 | **+0,0807** |

**Conferma e localizza** la misura originale (+0,03…+0,08): il difetto è **interamente** del
ramo preparato. Sul TWRR l'errore è **esattamente zero** — non piccolo: zero, perché
`N × 365 / D` con `D = N` dà 365 e il cablato coincide.

> **Quindi A9 morde**: scope asset **sempre**; scope portafoglio in modo **non**-`HISTORICAL`
> (il ramo `service.py:594` usa `prepared.annualization_factor`); **mai** su portafoglio
> `HISTORICAL`. La direzione che il coordinatore aveva intuito — *«la fetta appare
> sistematicamente migliore»* — è **confermata**, ma la causa è `annualization_factor`, non
> `calendar_coverage`.

### 🔴 `calendar_coverage` NON è 1,0 per costruzione — è un rapporto fra due calendari

Sono due grandezze diverse, con **denominatori diversi**, ed è facile scambiarle:

```python
annualization_factor = n_observations * 365 / (final_date - baseline_date).days
calendar_coverage    = n_observations / len(coverage_candidates)
```

Letto il codice (`series_preparation.py:236, 286-288, 344-345`):

- `candidate_quote_dates` = **unione** delle date di quotazione degli asset attivi;
- `included_return_dates` = quelle in cui **tutti** gli asset hanno un punto → **intersezione**;
- quindi `calendar_coverage = |intersezione| / |unione|`, un rapporto alla Jaccard **fra i
  calendari degli asset**.

Vale 1,0 **se e solo se tutti gli asset attivi quotano esattamente negli stessi giorni**: un
asset solo → sempre 1,0; più asset sulla stessa borsa → 1,0. **Ma un portafoglio che mescola
calendari no**: cripto (quota 365 giorni) + azioni (261) darebbe `261/365 ≈ 0,715`. Lo stesso
vale per borse con festività diverse.

**Questa è la risposta alla domanda «in quali casi reali `D > N`»**: i portafogli a
**calendario misto**. Dedotto dal codice, **non eseguito su dati veri** — va confermato con
un portafoglio cripto+azioni prima di pubblicarlo.

### ✅ E risolve l'interrogativo aperto di A5

In A5 avevo trovato `min_coverage` **inerte** e non sapevo dire perché la copertura fosse
sempre 1,0 nel plugin. Ora si spiega: **le date irregolari vengono già scartate a monte**
(`included_return_dates` tiene solo l'intersezione) e la misura di quanto si è perso è
registrata **un livello più su, sotto un altro nome** — `calendar_coverage` più
`incomplete_valuation_dates`. Il plugin riceve un blocco già rettangolare, quindi la sua
copertura non ha più niente da misurare.

> Il cursore inerte non è inutile *per sbaglio*: è inutile perché **misura una cosa già
> misurata altrove**. Il che cambia la raccomandazione — non «togliere un controllo rotto»,
> ma «il controllo giusto esiste già e si chiama `calendar_coverage`».

Probe: `/tmp/libreFolio_A_a9_probe.py`, log accanto.

---

## ✅ A6 — M6: chiuso con ZERO migrazioni, e la ragione è misurata (2026-09-18)

Il taglio d'ambito è stato chiesto al coordinatore **quattro volte** senza risposta, mentre
M6 era l'unico blocco del mandato. Ho proceduto col default che avevo raccomandato —
strettamente **meno** rischioso di M6 come scritto, e ogni esclusione reversibile. Ma
eseguendolo ho trovato due cose che hanno chiuso anche il default.

### 🔴 Fuori pista 13 — la Fascia 1 si è autodistrutta, e per la stessa ragione che la rendeva sicura

Stavo per scrivere `wealth_index` come `[1.0, *np.cumprod(1.0 + array)]`. Prima di toccarla
ho guardato chi la testa. `test_risk_metrics_oracle.py:206`:

```python
reference_wealth = np.concatenate([[1.0], np.cumprod(1.0 + array)])
...
assert index == pytest.approx(list(reference_wealth), rel=1e-12)
```

**L'oracolo confronta già `wealth_index` contro esattamente l'implementazione che stavo per
scrivere.** Migrarla renderebbe quel test `np.cumprod(x) == np.cumprod(x)`.

> **La bit-identità che rendeva la migrazione sicura è la stessa cosa che renderebbe
> tautologico il suo oracolo.** Sono un fatto solo, visto da due lati. Avevo classificato
> `wealth_index` in Fascia 1 *proprio perché* `max|delta| = 0.000e+00` su 6 casi — e quel
> numero, che leggevo come «rischio nullo», è la prova che il test non distinguerebbe più i
> due rami.

È la **stessa trappola della Fascia 0** (`pairwise_correlation`, gli helper a ciclo di M1) —
ma stavo per caderci sull'unica funzione che avevo dichiarato immune. La differenza è che
lì l'avevo prevista, qui l'ho evitata solo perché ho letto il test prima del codice.

### Il costo di `comparison_summary` è quello dei suoi chiamati — misurato

Restava l'ultima candidata, la più grossa della Fascia 2. T=2500, 40 ripetizioni:

| | ms | quota |
|---|---:|---:|
| **`comparison_summary` intero** | **4,880** | 100 % |
| nei **chiamati** | 4,434 | **90,9 %** |
| codice **proprio** (tre comprehension) | **0,295** | **6,0 %** |

Dettaglio dei chiamati: `pearson_correlation` 1,382 · `beta` 0,972 · `wealth_index` ×2 0,593
· `underwater_drawdown` ×2 0,513 · `sample_standard_deviation` 0,512 · `compounded_return`
×2 0,462.

**Sono tutti esclusi per ragioni indipendenti**: `pearson_correlation`, `beta` e
`sample_standard_deviation` sono la **semantica di riferimento** di M1 e M3;
`underwater_drawdown` è Fascia 3; `wealth_index` è la tautologia appena trovata.

Vettorializzare **solo** `comparison_summary` comprerebbe al massimo **0,295 ms**.

### Esito di M6

| Funzione | ms | Esito | Ragione |
|---|---:|---|---|
| `pairwise_correlation` | 1,556 | ❌ esclusa | semantica di riferimento del test differenziale di M3 |
| `wealth_index` | 0,252 | ❌ esclusa | **tautologia col proprio oracolo** (`:206`) |
| `comparison_summary` | 4,880 | ❌ esclusa | 90,9 % del costo è nei chiamati, tutti esclusi |
| `current_buy_and_hold_returns` | 5,127 | ❌ esclusa | **contratto con C**, firma e semantica congelate |
| `horizon_compounded_returns` | 1,6-3,3 | ❌ esclusa | a `horizon=1` non è identità: **sposterebbe il VaR pubblicato** |
| `summarize_drawdown` | 0,740 | ❌ esclusa | **contratto con N** + sensibilità a 1 ULP |
| `drawdown_episodes` | 0,879 | ❌ esclusa | macchina a stati `TODO(P2-refactor)`, chiamante in **AI Export** |
| `period_returns_from_cumulative` | 0,315 | ❌ esclusa | niente da vincere |
| `annualized_sortino` | 0,406 | ❌ esclusa | niente da vincere — **e A9 la tocca** |

**Nove su nove escluse. Guadagno rinunciato: ~0,3 ms** di codice realmente migrabile.

> **M6 non è stato evitato: è stato misurato.** La sua giustificazione nel documento `06` è
> dichiaratamente estetica — *«non esiste ragione per tenerli in `math` puro»*. La ragione
> esiste, ed è tripla: **due terzi di quelle funzioni sono la rete che prova le migrazioni
> già fatte**, due sono sotto contratto con altri mandati, e il resto vale frazioni di
> millisecondo.
>
> La lista di M6 è stata scritta **prima** che M1 e M3 esistessero. Eseguirla alla lettera
> oggi smonterebbe la rete che M1 e M3 hanno steso — pagando ~20 ms su richieste che ne
> costano migliaia.

**Nessun file sorgente modificato in A6.** La consegna è la misura e la decisione.
Probe: `/tmp/libreFolio_A_m6_cost.py`, `/tmp/libreFolio_A_m6_cumprod.py`,
`/tmp/libreFolio_A_m6_close.py`.

### Conseguenza su A9

`annualized_sortino` esce da M6 ma **entra in A9**: il coordinatore ha misurato che il
difetto del tasso la colpisce **più** dello Sharpe (+0,130 contro +0,094 a rf 5 %), e
verificando il meccanismo l'ho confermato sul codice — `metrics.py:206, 211` usa
`target_daily` **due volte**, nella varianza al ribasso *e* nell'eccesso. Bersaglio troppo
basso → numeratore gonfiato **e** denominatore sgonfiato, stessa direzione.

> **A9 è due funzioni, non una**: `annualized_sharpe` e `annualized_sortino`, entrambe
> attraverso `daily_risk_free_rate`.

---

## 🔨 A9 — il tasso privo di rischio: codice fatto, gate cieco, test in scrittura (2026-09-18)

Isolata subito dopo M6, come deciso da D94. Con M6 a zero righe, l'isolamento è perfetto
per costruzione: **nel diff di A9 non c'è nient'altro**.

### 🔴 Fuori pista 14 — il difetto è TRE chiamanti, non due

Avevo riportato «A9 è due funzioni». Cercando i chiamanti prima di scrivere:

| # | Chiamante | |
|---|---|---|
| 1 | `metrics.py:201` `annualized_sharpe` | previsto |
| 2 | `metrics.py:217` `annualized_sortino` | previsto |
| 3 | **`signal_helpers.py:263` `rolling_annualized_sharpe_values`** | 🔴 **non previsto** |

Il terzo è **la funzione vettorializzata che ho scritto io in M1**. Il difetto tocca
quindi anche il **grafico dello Sharpe rolling** — una superficie visibile all'utente che
non era nel quadro di nessuno, né mio né del coordinatore.

> Che il difetto avesse un chiamante *dentro il mio stesso lavoro di M1* è il motivo per
> cui la ricerca dei chiamanti va fatta **prima** di scrivere, non dopo: se avessi corretto
> solo le due funzioni di `metrics.py`, il grafico rolling sarebbe rimasto lusingato mentre
> la card KPI si correggeva — **due numeri sullo stesso schermo in disaccordo**, ciascuno
> difendibile da solo.

### La scelta di firma: obbligatorio, non con default

```python
def daily_risk_free_rate(annual_rate: float, periods_per_year: float) -> float:
```

Un default a `365.0` avrebbe mantenuto verdi i test senza toccarli. L'ho rifiutato.

> È esattamente il modello della **difesa inerte** che questa campagna ha già trovato
> cinque volte: la guardia `width <= 0.0` mai raggiunta, il gate che non guarda, il mock
> stantio, la fixture che guarda un mondo inesistente. Un default lascerebbe un futuro
> chiamante reintrodurre il difetto **in silenzio**. Obbligatorio lo rende
> **irrappresentabile**: non si può più chiamare la funzione senza dichiarare il periodo.

Costo: due righe in `test_risk_signal_plugins.py` (file non rivendicato — **lo dichiaro
mio per primo-tocco**) e due nell'oracolo. Entrambe già verdi, perché usavano 365.

Sollevata anche la chiamata fuori dal generatore in `annualized_sharpe`: era valutata
**T volte per serie**. Funzione pura ad argomenti costanti → identica al bit.

### 🔴 Fuori pista 15 — il gate è verde PRIMA e DOPO. Sesta istanza della famiglia

| | prima | dopo |
|---|---|---|
| `services risk-oracle` | 158 passed | **158 passed** |
| `services risk-all` | 292 passed | **292 passed** |

Nessuna attesa cambiata. Nessun test toccato se non per la firma.

**Perché**: ogni test esistente usa fattore **365** — l'unico regime dove vecchio ≡ nuovo.

> A9 **deve** muovere i numeri (D94), e il gate non ne ha visto muovere nemmeno uno. È la
> sesta istanza della famiglia del gate cieco e la più tagliente delle sei: le altre non
> guardavano, o guardavano la cosa sbagliata. **Questa è verde prima e dopo una correzione
> che cambia numeri visibili all'utente.** Dichiarare A9 fatto su «292 passed» sarebbe
> stato dichiarare verificata una correzione da una suite strutturalmente incapace di
> osservarla.

Criterio consegnato a `test-author`: **ogni test deve fallire se si ripristina il
`/365.0`**. Un test che passa in entrambi i mondi non serve.

### Le cifre — per J e I

**L'enunciato più netto: l'utente scrive 5 % e il motore addebitava 3,55 %.**

| factor | rf chiesto | corretto | **vecchio** |
|---|---|---|---|
| 365 | 2 % | 0,0200000 | 0,0200000 |
| **261** | 2 % | 0,0200000 | **0,0142610** |
| **261** | 5 % | 0,0500000 | **0,0355040** |
| 12 | 5 % | 0,0500000 | 0,0016053 |

Rapporto corretto/vecchio a 261: **1,3985 costante** — il corretto è 39,8 % più alto,
cioè il vecchio era 28,5 % più basso del dovuto.

Lusinga rimossa (vecchio − corretto), fattore 261, 200 serie:

| rf | Sharpe med. | Sharpe peggiore | Sortino med. | Sortino peggiore |
|---|---|---|---|---|
| **0 %** | **+0,0000** | **+0,0000** | **+0,0000** | **+0,0000** |
| 1 % | +0,0146 | +0,0157 | +0,0217 | +0,0255 |
| 2 % | +0,0291 | +0,0313 | +0,0430 | +0,0506 |
| 5 % | +0,0718 | +0,0772 | **+0,1047** | **+0,1230** |

1. **Sortino colpito più dello Sharpe a ogni tasso non nullo** — `target_daily` entra
   **due volte**, nella varianza al ribasso *e* nell'eccesso: numeratore gonfiato e
   denominatore sgonfiato, stessa direzione.
2. **Ramo TWRR immobile al bit**: `0,000e+00` su 200 serie × 3 tassi. Nessun utente in
   modo `HISTORICAL` di ambito portafoglio vede cambiare un numero.
3. **Inversione di segno misurata, non teorizzata: 131/8000 = 1,64 %.**

Probe: `/tmp/libreFolio_A_a9_delta.py`.

---

## ✅ A7 — M5 declinata, e **D39 non è bloccata da M5**: la premessa era falsa (2026-09-18)

Il brief pre-autorizza il rinvio: *«Se M5 viene rinviata, D39 la segue — e va dichiarato,
non lasciato cadere.»* Ma prima di dichiarare ho verificato **eseguendo**, e l'argomento
per cui M5 era a bassa priorità si è rivelato falso. Il che cambia la conclusione su D39,
non su M5.

### 🔴 Fuori pista 16 — l'idraulica dichiarata mancante esiste già

Tre documenti dicono la stessa cosa:

> `06` §Caso A: *«`Risk_Contribution` vuole la matrice dei rendimenti, la nostra vuole solo
> covarianza e pesi. Migrare significa far arrivare i rendimenti fino a quel livello. È
> lavoro di idraulica, non di matematica, ma va messo a preventivo.»*
> `06` §M5 e il mio brief §M5 ripetono l'affermazione.

`risk_plugins/risk_contribution.py:55-58`:

```python
rows = [prepared_asset_returns(context, asset_id)[1] for asset_id in asset_ids]
weights = [context.weights[asset_id] for asset_id in asset_ids]
summary = risk_contributions_from_covariance(covariance_matrix(rows), weights, ...)
```

**`rows` è la matrice dei rendimenti. Il chiamante la costruisce e la consuma una riga
sopra.** Provato eseguendo: una trasposizione, `shape (750, 6)`, `rk.Risk_Contribution`
gira e dà gli stessi numeri. **Nessun dato nuovo, nessuna query, nessun parametro in più.**

> La premessa confonde **la firma di `risk_contributions_from_covariance`** — che davvero
> prende covarianza e pesi — con **la disponibilità dei rendimenti presso il chiamante**,
> che li ha. Un argomento sulla firma è stato letto come un argomento sull'architettura, ed
> è sopravvissuto a tre documenti perché nessuno ha aperto il plugin.

### Le altre quattro misure

**1. Coincidono, ma non alla tolleranza dell'oracolo.** Scarto massimo `1,903e-11`. `06`
dice «`np.allclose` vero» — vero alle tolleranze **predefinite** (`rtol=1e-5`). Al nostro
standard (`rel=1e-9`, `abs=1e-12`) `np.allclose` è **`False`**. Praticamente identici,
formalmente no: se M5 si facesse, l'asserzione andrebbe scritta a `1e-7` relativo, non a
`1e-9`.

**2. 🔴 Il rapporto di velocità di `06` è invertito a N=6.** `06` §Caso A riporta *«Nostro
0,022 ms, riskfolio 0,058 ms»* — misurato a **N=3** (la tabella §3 mostra tre contributi).
A N=6, T=750: **nostro 0,563 ms, riskfolio 0,09-0,12 ms**, cioè **riskfolio è ~4,6× più
veloce**, non 2,6× più lento. La *conclusione* di `06` («differenza irrilevante») resta
giusta — sono tutti sotto il millisecondo su richieste che costano secondi — ma **la
direzione dipende da N e non va citata**.

**3. 🔴 I contributi non-MV non «possono» essere negativi: lo sono sempre.**

| `rm=` | contributi in % | negativi | costo |
|---|---|---|---|
| `MV` | `[0,7 · 9,81 · 1,54 · 0,51 · 41,46 · 45,99]` | no | 0,09 ms |
| `MAD` | `[0,52 · 8,83 · 1,25 · 0,42 · 42,55 · 46,44]` | no | 0,20 ms |
| `CVaR` | `[1,21 · 12,48 · 2,3 · 0,8 · 36,07 · 47,15]` | no | 0,61 ms |
| **`MDD`** | `[−3,89 · −3,62 · 14,0 · −4,31 · 33,33 · 64,49]` | **SÌ** | 8,49 ms |
| **`ADD`** | `[−3,66 · 7,92 · 11,72 · −2,61 · −27,05 · **113,68**]` | **SÌ** | 15,70 ms |
| **`UCI`** | `[−3,99 · 5,98 · 12,99 · −2,44 · −20,44 · **107,89**]` | **SÌ** | 18,41 ms |

Tre misure drawdown su tre, su un portafoglio casuale **senza alcuna patologia**. Non è un
caso limite: è la norma. **Una torta con una fetta da 113,68 % e una da −27,05 % non è una
torta.**

E il colpevole **cambia**: l'asset 4 passa da **+41,46 % con `MV` a −27,05 % con `ADD`**.
È l'inversione che `06` §7.1 descriveva — ora misurata.

### Esito

**M5: declinata.** Non per l'idraulica — che non manca — ma perché:

1. l'output è identico (a `1e-11`), quindi non corregge nulla;
2. la velocità è irrilevante in entrambe le direzioni;
3. l'unico valore vero, lo sblocco di `rm=`, è **dichiarato fuori mandato dal brief
   stesso** e rimandato a **Q7**;
4. e ora si sa che quello sblocco **romperebbe la UI in 3 casi su 3**, non «potrebbe».

Farla significherebbe sostituire codice nostro corretto e testato con una chiamata di
libreria che dà gli stessi numeri più lentamente o più velocemente a seconda di N, per
abilitare una funzionalità che **nessuno ha deciso di mostrare**.

**D39: NON segue M5 — e questa è la correzione che conta.**

> Il brief dice: *«Calmar e Martin pretendono la matrice dei rendimenti, che è esattamente
> l'idraulica mancante di M5. Chi fa M5 ha già pagato metà del lavoro. Quindi: dopo M5, e
> solo allora.»*
>
> **Se l'idraulica non manca, D39 non è dietro M5.** È dietro **Q7**, che è una decisione
> di prodotto: come si mostra un contributo negativo. Tecnicamente D39 è a una
> trasposizione e un `rm=` di distanza — l'ho eseguita.

Dichiarazione formale, come il brief richiede: **D39 non viene consegnata in questo
mandato**, non perché manchi l'infrastruttura, ma perché **manca la decisione Q7**. Chi la
riprenderà non deve preventivare idraulica: deve preventivare **un grafico che sappia
disegnare valori negativi e somme oltre il 100 %**, e le cifre qui sopra dicono
esattamente quanto estremi.

Probe: `/tmp/libreFolio_A_m5_plumbing.py`.

---

## ⚠️ Rettifica ad A9 — avevo misurato una funzione e parlato di un sistema (2026-09-18)

Avevo consegnato al coordinatore, per J:

> *«Il ramo TWRR non si muove di un bit. **Nessun utente in modo `HISTORICAL` di ambito
> portafoglio vedrà cambiare un numero.** È l'enunciato che J può scrivere senza riserve.»*

**«Senza riserve» è sbagliato.** Avevo misurato il comportamento della *funzione* a fattore
365 e dedotto il comportamento del *sistema*, assumendo che il ramo TWRR passi sempre 365
esatti. `service.py:862, 871`:

```python
points = [point for point in report.history if point.twrr is not None]
annualization_factor = len(returns) * 365 / calendar_days if calendar_days > 0 else None
```

Il fattore è 365 **esatti solo se `len(returns) == calendar_days`** — cioè se nessun punto
è filtrato *in mezzo*. E la riga sopra filtra proprio quello.

| Meccanismo | Effetto |
|---|---|
| `lots_analysis_service.py:1013` — flusso esterno non valido → `twrr=None` **da lì in poi** | 🟢 innocuo: tronca la **coda**, `calendar_days` si misura sul `points[-1]` superstite → fattore 365 |
| **`portfolio_service.py:1388` — `twrr = twrr_map.get(d)`** | 🔴 **`None` per ogni data assente dalla mappa**. Date **interne** mancanti → `len(returns) < calendar_days` → **fattore < 365** |

(`:1429` forza `history_points[0].twrr = 0`: il primo punto non è mai nullo.)

**Non provabile dal codice** se `twrr_map` copra sempre ogni giorno interno: servirebbe
eseguire il motore su un portafoglio con un buco, e non ho dati reali.

### La direzione però è quella buona, e questo salva la correzione

Fattore < 365 ⟹ `log1p(r)/fattore > log1p(r)/365` ⟹ il tasso corretto è **più alto** del
vecchio ⟹ **il vecchio lusingava**. Esattamente come sul ramo preparato.

> **Ovunque il fattore sia sotto 365, il codice vecchio lusingava. La correzione toglie
> lusinga dappertutto.** Non esiste un caso in cui peggiori qualcosa: l'unica variabile è
> **se** un dato portafoglio si muova, non **in che direzione**.

### Enunciato corretto consegnato a J

> «Su una cronologia TWRR senza buchi interni — il caso normale, perché il motore avanza di
> un giorno solare alla volta — il fattore è 365 esatti e nulla si muove. Un portafoglio
> con date interne in cui il TWRR non è calcolabile ha un fattore sotto 365, e lì la
> correzione toglie lusinga come sull'ambito titolo.»

Tutte le altre cifre di A9 **restano valide**: sono misurate sulle funzioni.

> **Nota di metodo.** È la stessa classe di errore che avevo contestato al coordinatore su
> `calendar_coverage`: misurare una funzione e parlare di un sistema. Che sia capitata **a
> me** poche ore dopo è il motivo per cui l'ho ricontrollata — e il motivo per cui
> un'affermazione consegnata a un altro mandato va riletta sul codice **prima** di essere
> scritta in un CHANGELOG, non dopo.

---

## A9 — chiusura dei test ✅ 2026-09-18

**Blocco (i)** scritto da `test-author`, righe `2587-2965`: **9 funzioni, 42 casi
parametrizzati**. Oracolo **158 → 200**. `services risk-all` **292 → 334**.

> **Note implementazione.** Un solo mio intervento sul blocco: il docstring del test
> preesistente a `:1800` dichiarava il difetto «fuori ambito, separatamente tracciato».
> Il difetto è riparato, quindi la nota descriveva il codice in modo falso. Riscritta
> come **nota storica** — non cancellata, perché è il verbale di un punto cieco e vale
> più da conservata che da rimossa.

### 🔴 Fuori pista — la mia diagnosi era giusta nella conclusione e falsa nel meccanismo

Avevo scritto al coordinatore che il gate era cieco perché **«ogni test esistente usa
il fattore 365»**. `test-author` l'ha falsificata in una riga:

```
backend/test_scripts/test_services/test_risk_metrics_oracle.py:84
_ANNUALIZATION = 252.0
```

Il test rf del blocco (g) **girava già a 252** — un fattore non solare — e **lo stesso
non vedeva il difetto**. Quindi il fattore non c'entrava.

Il motivo vero è un altro, ed è peggiore:

> **Le aspettative erano formulate chiamando la funzione sotto esame.**
> `annualized_sharpe` chiama `daily_risk_free_rate(rf, fattore)` da sé. Se l'aspettativa
> del test chiama anch'essa `daily_risk_free_rate`, **entrambi i lati dell'identità
> usano lo stesso tasso** — giusto o sbagliato che sia — e il test resta verde su
> qualunque corpo. Misurato: con l'aspettativa formulata sul soggetto i due codici
> concordano a `rel ≈ 2e-15`; con un tasso indipendente il codice vecchio sbaglia del
> **28,5 %**.

Ed è la stessa trappola di M6 — `wealth_index` confrontato con `np.cumprod` mentre la
migrazione voleva farlo diventare `np.cumprod` — **due volte nella stessa giornata, in
due travestimenti diversi**. Non è un caso: è la modalità di guasto caratteristica di
un oracolo. Un oracolo protegge **solo** finché la sua aspettativa ha una fonte
indipendente dal soggetto.

Conseguenza pratica: **quattro delle mie cinque proprietà erano cieche come le avevo
enunciate** (2, 3, 7, 8 oltre alla 5). `test-author` ha aggiunto a ognuna una metà «in
contrasto», con conversione `pow` che non condivide una riga col soggetto.

### La discriminazione: eseguita, non creduta

`test-author` non lancia suite. Ho ripristinato il difetto io — corpo a `/365.0`,
firma invariata — e lanciato la lane:

| | esito |
|---|---|
| copia di sicurezza | `/tmp/libreFolio_A_metrics_backup.py`, md5 `88c0b331eed477c6841c7017d4aaf4eb` |
| con il difetto | **33 failed, 167 passed** |
| ripristino | md5 **identico**, nessun residuo di `365.0` né del marcatore |
| dopo il ripristino | **200 passed** |

I 33 coincidono **esattamente** con la tabella dichiarata da `test-author` (9+6+1+5+3+3+4+2).
E passano **solo** i casi a fattore 365 — cioè l'unico regime in cui il codice vecchio
era corretto. La rete distingue il difetto dalla riparazione, **misurato**.

> Un test che non ho verificato discriminante è un test di cui conosco il colore, non il
> valore. La regola di campagna — «`test-author` scrive, il mandato **esegue**» — non
> basta a fermarsi all'esecuzione sul codice buono: va eseguita **anche sul codice
> cattivo**, altrimenti si misura che la suite è verde, non che è sveglia.

### Il «no» onesto

Il test 5 (guardia sul tasso ≤ −100 %) **non discrimina**: 5/5 verdi da entrambe le
parti. `test-author` l'ha dichiarato invece di nasconderlo. **Tenuto**, etichettato per
quello che è: una guardia di regressione sul cambio di firma, non sulle unità.

### Cose dichiarate e non scritte

- Nessun caso con fattore **> 365**: invertirebbe il segno dell'errore. Le asserzioni
  «la carica corretta è strettamente maggiore» valgono **solo per fattori ≤ 365**, e il
  commento lo dice.
- Nessun test di Sortino rolling: **`rolling_annualized_sortino_values` non esiste**,
  solo lo Sharpe passa da `signal_helpers`. Verificato, non è una lacuna.
- 🟠 **`rel=1e-12` è inutilizzabile per il giro di andata e ritorno**: l'errore relativo
  peggiore di `(1+p)**f − 1` contro `r` è **2,02e-12**, e lo scarto `pow`/`expm1`
  arriva a **2,6e-11**. Usato `rel=1e-9, abs=1e-12`, lo standard del file, con nota di
  non stringere.

### Evidenza

| Comando | Esito |
|---|---|
| `services risk-oracle` | **200 passed** in 3,42 s |
| `services risk-oracle` col difetto ripristinato | **33 failed, 167 passed** |
| `services risk-all` | **334 passed** in 27,49 s |
| `ruff check` sull'oracolo | All checks passed |
| `black --check` sull'oracolo | 1 file would be left unchanged |

---

## A8 — chiusura del mandato ✅ 2026-09-18 · **FROZEN**

### Inventario

13 file modificati, 2 nuovi, **+580 / −73**. Nessun artefatto generato, nessun dato
privato, nessuna directory di dati, nessun `node_modules`.

| Area | File |
|---|---|
| Schema (K1) | `schemas/risk.py` |
| Matematica | `risk/metrics.py` · `risk/signal_helpers.py` |
| Produttori | `risk_plugins/{correlation,drawdown_summary,historical_var}.py` |
| Segnali (M1) | `signal_plugins/rolling_{beta,return,sharpe,volatility}.py` |
| Test | `test_risk_metrics.py` · `test_risk_signal_plugins.py` · **`test_risk_metrics_oracle.py`** (nuovo) |
| Catalogo | `scripts/test_runner/_backend_services.py` |
| Piano | `progress/A-esecuzione.md` (nuovo) |

### Evidenza finale

| Verifica | Esito |
|---|---|
| `services risk-oracle` | **200 passed** |
| `services risk-all` | **334 passed** (baseline: 292) |
| `ruff check` su tutti e 14 i file | All checks passed |
| `black --check` | 13/14 puliti |
| `black` su `_backend_services.py` | protesta a `:962`, **blocco non mio** — provato preesistente lanciando black sulla versione di `HEAD`: stesso rosso senza una mia riga |
| `git diff --check` | pulito |
| `lsof -nP -iTCP:6240 -sTCP:LISTEN` | **nessun listener** |
| sonde in `/tmp` | 83 rimosse, 0 rimaste |

### Cosa è stato consegnato, e cosa è stato **rifiutato con misura**

Quattro dei nove passi si chiudono **senza scrivere codice**, ognuno con una misura che
lo giustifica. Questa è la parte del mandato di cui rispondo più volentieri: un piano
eseguito alla lettera avrebbe smontato la rete che M1 e M3 avevano appena steso.

| Passo | Esito |
|---|---|
| A1 W0 · A2 K1 · A3 M2 · A4 M1 · A5 M3 | **fatti** |
| A6 **M6** | **zero migrazioni su nove**, ognuna esclusa con una misura. `comparison_summary`: il 90,9 % del suo tempo è nei chiamati, già esclusi; il suo codice proprio vale **0,295 ms**. `wealth_index`: il suo test dell'oracolo **confronta già** con `np.cumprod` — migrare l'avrebbe reso tautologico |
| A7 **M5** | **declinato**: l'idraulica mancante **non esiste**, `risk_contribution.py:55` costruisce già la matrice dei rendimenti. Premessa falsa in tre documenti |
| A7 **D39** | **dichiarato non bloccato da M5**, ma da **Q7**: i contributi non-MV sono **sempre negativi**, con fette misurate del **113,68 %** e del **−27,05 %**. È una decisione di prodotto su un grafico, non un problema di idraulica |
| A9 | **fatto**, con la rete che lo discrimina **verificata ripristinando il difetto** |

### Messaggio di commit proposto — **non eseguito**

```
feat(risk): add a reference oracle and migrate the risk mathematics

Pin metrics.py and signal_helpers.py against riskfolio, NumPy and SciPy
in a dedicated oracle (200 cases, isolation="pure"), then migrate the
mathematics the oracle now protects.

- VaR/CVaR move to the Acerbi-Tasche estimator: both numbers change, not
  only the CVaR. The naive estimator biased the tail low by up to 11% at
  99% confidence, not the 0.27% average measured at the 95% default.
- Rolling signals and the covariance/correlation matrices are vectorised,
  preserving undefined-window counts, coverage and the None returns that
  drive plugin status.
- The per-period risk-free rate now takes the annualization factor as a
  required argument: it was always dividing by 365 while the series was
  annualized over trading days, flattering Sharpe and Sortino whenever the
  user set a non-zero rate.
- Histogram bins, the forced VaR edge and the underwater series are exposed
  on the risk schemas for the charts to consume.

Nine composite functions were measured and deliberately left in Python, and
the risk-contribution migration was declined: the returns matrix it was said
to need is already at the call site.
```

### Lasciato aperto, onestamente

- **M6, M5, D39** — esclusi con misura, non dimenticati. D39 attende **Q7**.
- **`api client`** non rigenerato: `frontend/node_modules` assente in questo worktree.
  Eseguito `api schema`. Rigenera chi ha le dipendenze.
- Il **pavimento a zero** su VaR/CVaR resta, dichiarato a E come vincolo noto.
- Il **debito black** su `_backend_services.py:962` resta dov'era.

---

## Coda — i due cancelli riaperti dalla semina ✅ 2026-09-18 03:10

Il coordinatore ha seminato `frontend/node_modules` (291 voci) e mathjax, chiudendo
il rosso d'infrastruttura che avevo consegnato come bloccante aperto. Riaperti e chiusi
i due cancelli a cui avevo rinunciato.

### `api risk` — **10 passed**

Ordine obbligato rispettato (`risk-all` era già l'ultimo comando di lane, quindi le
fixture erano da ricreare):

```
test db populate --force --clean   → 5 612 record
test api risk                      → 10 passed in 10,40 s
```

Complemento pieno, non gli `8 passed, 2 failed` che l'ordine sbagliato produce.
Conferma la valutazione data in analisi: `test_risk_api.py` asserisce solo
`cvar >= var >= 0`, che l'oracolo già fissa a livello di servizio — **lacuna sul
trasporto, non sulla matematica**.

### `api sync` — K1 verificato **nel TypeScript**, non solo nello schema

Con `node_modules` presente, rigenerato il client invece di fermarsi a `api schema`.
È la verifica che conta per **E**, perché E costruisce sul generato, non sul Pydantic:

```ts
generated.ts:7954   return_bins?: Array<RiskVarCvarBin> | undefined;
generated.ts:7957   type RiskVarCvarBin = { ... }
generated.ts:8217   underwater_series?: Array<RiskDrawdownPoint> | undefined;
generated.ts:14320  z.object({lower_bound: z.number(), upper_bound: z.number(),
                              count: z.number().int().gte(0)})
generated.ts:14391  z.object({date: z.string(), drawdown: z.number().lte(0)})
```

**I vincoli sopravvivono al giro**: `ge=0` → `.int().gte(0)`, `le=0` → `.lte(0)`.
Entrambi i tipi esportati (`:15187`, `:15203`). K1 è consumabile.

> **Nota per E, perché non la scambi per una stranezza mia.** Il tipo TypeScript di
> `var_bin_edge` esce come `((number | null) | Array<number | null>) | undefined` — con
> un ramo `Array` che non può mai verificarsi. **È il comportamento di casa del
> generatore**: misurati **42 campi preesistenti** con la stessa identica forma
> (`broker_id`, `count`, `minimum`, `maximum`…). Lo zod è corretto
> (`z.union([z.number(), z.null()]).optional()`). Nessuna difesa da scrivere.

### 🟠 Fuori pista — la semina ha portato rumore che non è mio

Dopo la semina, `git status` mostra due file non tracciati in più, **estranei al mio
mandato**:

```
?? mkdocs_src/docs/static/icons/asset-types/commodity.png
?? mkdocs_src/docs/static/icons/asset-types/real-estate.png
```

Misurato, non dedotto:

| Fatto | Evidenza |
|---|---|
| Non li crea `api sync` | mtime **23:44:09**, identico agli altri dieci del checkout; `api sync` è girato alle 03:07 |
| Arrivati per copia che preserva i metadati | `cp -Rc` (clonefile APFS) conserva il mtime del donatore |
| **Non ignorati** | `git check-ignore` → «NON ignorati» |
| **Non tracciati** | `git ls-files` ne elenca **dieci** su dodici |
| Appartengono al lavoro di qualcun altro | presenti in commit `copilot checkpoint` su **altri rami**, uno della sessione del coordinatore |
| Non referenziati | nessun `.md`/`.yml` di `mkdocs_src/` li cita |

Il coordinatore aveva verificato che **i percorsi voluti** fossero gitignorati. Lo sono.
Ma la copia ha portato anche ciò che nei percorsi non era ignorato: **verificare la
destinazione non verifica il contenuto**. È la stessa classe di difetto che la semina
serviva a riparare, ricomparsa dentro la riparazione.

**Non li tocco**: non sono miei. Ma chi mette in stage il mio checkpoint deve saperlo —
un `git add -A` committerebbe **due icone di un altro mandato** dentro un commit di
matematica del rischio. E la stessa semina è stata fatta al worktree di **I**.

---

## Coda — `fresh_quote_coverage`: l'anello che avevo lasciato aperto ✅ 2026-09-18 03:14

Segnalazione di **I** via coordinatore, verificata sul codice. **Confermata, e più netta
di come era stata enunciata.**

### Il fatto

```
series_preparation.py:347   fresh_quote_coverage = fresh_quote_points / fresh_quote_denominator
series_preparation.py:379   → posato sul modello
schemas/risk.py:401         fresh_quote_coverage: FiniteFloat = Field(0.0, ge=0, le=1)

grep -rn "fresh_quote_coverage" backend/app/services/risk/   →  ZERO
```

Gli unici lettori in tutto il backend sono **il produttore, lo schema e sei file di
test**. Nessuna logica lo consulta. **È calcolato a ogni preparazione, viaggia nella
risposta API, e non decide nulla.**

### Perché chiude l'anello che avevo aperto

Avevo detto al coordinatore che misurare `calendar_coverage` avrebbe prodotto «un numero
rassicurante e falso». Ora si vede **perché**, mettendo le due definizioni una sotto
l'altra:

```python
:345  calendar_coverage    = n_observations / len(coverage_candidates)
:346  fresh_quote_denominator = len(active) * n_observations
:347  fresh_quote_coverage = fresh_quote_points / fresh_quote_denominator
```

| | `calendar_coverage` | `fresh_quote_coverage` |
|---|---|---|
| Unità | **date** | **celle** (titolo × data) |
| Denominatore | `coverage_candidates`, che viene da `candidate_quote_dates` `:236` — **filtrato per freschezza** | la griglia piena, **nessun filtro** |
| Conseguenza | **esclude dal denominatore esattamente la prova che dovrebbe contare** → inchiodato vicino a 1,0 | può stare ovunque in [0, 1] |

> **Il sistema calcola il numero onesto e ne guarda un altro.** Non manca la misura:
> manca la lettura. Per chi dovrà ripararlo non è «calcolare qualcosa di nuovo», è
> **leggere un campo che è già nella risposta**.

### Il denominatore è **esatto** — e qui una mia ipotesi è caduta

Avevo sospettato che `len(active) * n_observations` fosse un'assunzione ottimistica, e
che un titolo entrato tardi abbassasse il rapporto per motivi strutturali invece che di
freschezza. **Falso**, verificato:

- `:287` `included_return_dates` tiene solo le date in cui **tutti** i titoli attivi
  hanno un punto — è un'intersezione;
- `:289` `joint_valuation_dates = [baseline_date, *included_return_dates]`;
- `:298` i `valuation_points` di **ogni** titolo sono costruiti su quella stessa griglia.

Quindi ogni titolo ha esattamente `n_observations + 1` punti, e il numeratore — che
salta la baseline con `index > 0` — ha per tetto esattamente il denominatore.
**Il rapporto è una frazione vera.** Un titolo entrato tardi non abbassa il numero:
**accorcia la finestra**, e compare in `incomplete_valuation_dates`, che è un segnale
diverso e già riportato.

### 🟠 La riserva di I, con la riga esatta

```python
:318   if index > 0 and not point.is_price_carried_forward:
:319       fresh_quote_points += 1
```

`is_fx_carried_forward` esiste (`:315`, alimenta `carried_fx_points`) ed è **mai
consultato qui**. Quindi una cella con **prezzo fresco e cambio portato avanti conta
come fresca**, mentre il valore convertito — prezzo × cambio — è stantio.

**È il segnale migliore che abbiamo, non un segnale completo.** Va citato con la riserva
attaccata, altrimenti sostituisce un numero rassicurante con un altro numero
rassicurante.

### Nessuna azione da parte mia

A9 è chiuso e questo non lo cambia: A9 riguardava il tasso privo di rischio, non la
copertura. La misura che avevo **rifiutato** di fare resta giustamente rifiutata — e
questa scoperta rafforza la ragione del rifiuto invece di indebolirla: la variabile
giusta esisteva, e non era quella che mi era stato chiesto di misurare.

---

## Coda — il divieto `SemiDeviation`, misurato sul Sortino 🔴 2026-09-18 03:17

Divieto di campagna emesso dal coordinatore (trovato da I). L'ho misurato **un livello
più in là**: non sulla deviazione, ma sul **Sortino**, che è il numero che finisce a
schermo.

| serie, 250 oss. | nostra dd | `rk.SemiDeviation` | **Sortino vero** | **se sostituito** |
|---|---:|---:|---:|---:|
| centrata a zero | 0,006331 | 0,006609 | 1,1853 | 1,1355 |
| **perde −0,5 % ogni giorno** | 0,005000 | **0,000000** | **−15,8745** | **+∞ (div/0)** |
| −0,2 %/giorno + rumore | 0,002234 | 0,000716 | −14,1581 | **−44,1432** |
| sale +0,5 % ogni giorno | 0,000000 | 0,000000 | `None` | **+∞** |

### Due aggiunte alla diagnosi ricevuta

**🔴 Non è «rischio di ribasso zero»: è Sortino `+∞`.** Un denominatore esattamente
nullo dentro un rapporto non produce un numero rassicurante, produce **il punteggio
migliore rappresentabile**. Il portafoglio che perde lo 0,5 % ogni giorno per un anno
verrebbe mostrato come **il miglior rendimento corretto per il rischio del prodotto**.
Il vero è **−15,87**.

**🔴 Il caso silenzioso batte quello catastrofico.** `−0,2 %/giorno + rumore` — un
portafoglio che scende davvero, con rumore normale, cioè **il caso realistico** — non
divide per zero: restituisce **−44,14 invece di −14,16**, sbagliato di un fattore
**3,1**, senza infiniti, senza eccezioni, senza traccia. Il caso a `+∞` è vistoso.
Questo no.

**📌 Correzione al `1,002` ricevuto**: su dati centrati a zero ma *realistici* il
rapporto è **1,0439**. Il `1,002` è il solo effetto del divisore su una serie
perfettamente simmetrica. La conclusione non cambia — il 4 % resta dentro il rumore di
qualunque test di sostituzione — ma «due parti su mille» come margine di sicurezza
sarebbe il caso più favorevole spacciato per tipico.

### Il difetto nel mio stesso oracolo

La guardia esiste da A1 (`test_sortino_is_not_the_mean_over_riskfolio_semideviation`,
`:398`) e **fallisce sulla sostituzione**: fissa il valore atteso a `rel=1e-12`, quindi
la rete regge. Ma il suo docstring, scritto da me, dice **«happens to land nearby»** —
ed è **esattamente la cornice di D40** che il coordinatore ha appena criticato: mette in
fila la differenza millesimale del divisore e quella illimitata del riferimento come se
fossero paragonabili.

> **La prova era quella forte, la motivazione quella debole.** Un test che fallisce per
> la ragione giusta ma *spiega* la ragione sbagliata protegge il codice e diseduca il
> lettore — e il lettore è chi deciderà la prossima sostituzione.

Irrobustimento affidato a `test-author` insieme ai tre casi K1.

### ⚠️ Attrito sul vincolo «solo in coda» di `test_risk_schemas.py`

I simboli K1 vanno importati, e il blocco `from backend.app.schemas.risk import (...)`
è **in testa**. Opzioni: import locale con `# noqa: PLC0415` (regola attiva a
`pyproject.toml:80`, precedente a `test_fx_route_schemas.py:210`) oppure due nomi
aggiunti al blocco esistente in ordine alfabetico.

**Scelto il secondo**: è la stessa **unione meccanica** già autorizzata per `__all__` e
non lascia rumore di `noqa` nel file di un altro mandato. **Dichiarato al coordinatore**
invece di farlo passare per «append in coda».

---

## A10 — i tre casi K1 e l'irrobustimento del divieto ✅ 2026-09-18 03:45

Due lavori additivi assegnati dal coordinatore dopo `FROZEN`. Scritti da `test-author`,
**eseguiti e verificati da me** — compresa la discriminazione per mutazione, che è la
regola che ho scritto io e che vale anche quando il rapporto ricevuto è ottimo.

### Consegnato

| file | da → a | test |
|---|---|---|
| `test_schemas/test_risk_schemas.py` (di **C**) | 671 → 944 | 5 |
| `test_services/test_risk_metrics_oracle.py` | 2 969 → 3 237 | 4 + docstring riscritto |

**`git diff --stat` sul file di C: `273 insertions(+)`, zero cancellazioni.** Nessun
test, nessun helper, nessun ordine toccato. L'unica modifica sopra la coda sono **tre**
nomi nel blocco `import` esistente, in ordine alfabetico già rispettato.

> ⚠️ **Tre, non due**, come avevo dichiarato al coordinatore: oltre a `RiskVarCvarBin` e
> `RiskDrawdownPoint` serve **`RiskComparisonPoint`**, perché il caso 1 verifica l'unità
> **contro il proprio precedente** invece di riasserirla da sola. La correzione è mia e
> l'ho dichiarata.

### Discriminazione — misurata, non creduta

**Oracolo**, sostituzione vietata applicata a `annualized_sortino` (semantica
`rk.SemiDeviation` riprodotta in `math`/`numpy` puri, per non importare riskfolio nel
processo web nemmeno per un minuto):

```
md5 prima    88c0b331eed477c6841c7017d4aaf4eb
md5 mutato   ac3de0edc387333a7f4fa7c3d3b36e49
→ services risk-oracle:  12 failed, 192 passed
md5 dopo     88c0b331eed477c6841c7017d4aaf4eb   ← identico
```

I 12 rossi sono **tutti e quattro i nuovi**, **più la guardia preesistente**, più sette
test A9 che dipendono dal Sortino. La rete prende la sostituzione da cinque lati.

**Schema**, mutazione **a un solo lato** — il caso che `test-author` ha trovato cieco nel
proprio primo tentativo e ha corretto:

```
value_at_risk perde ge=0  (conditional_value_at_risk intatto)
→ schemas risk:  2 failed, 17 passed
md5 ripristinato ee75e29f8a3ca839386e9d9d0d0c05c9   ← identico
```

### Cancelli

| comando | esito |
|---|---|
| `schemas risk` | **19 passed** (14 di C + 5 miei) |
| `services risk-oracle` | **204 passed** (era 200) |
| `services risk-all` | **338 passed** (era 334) |
| `ruff check` sui due file | All checks passed |
| `black --check` sui due file | 2 files would be left unchanged |
| `git diff --check` | pulito |

### 🔴 Fuori pista — due mie affermazioni false, falsificate da `test-author` e verificate da me

**(a) Il segno del Sortino sostituito è `−∞`, non `+∞`.** Avevo consegnato al
coordinatore *«il miglior punteggio rappresentabile mostrato al portafoglio peggiore»*
mentre diffondeva il divieto a dieci mandati. Il numeratore porta il proprio segno:
`−0,005 / 0,0 = −inf`. Il `+∞` esiste **solo sulla serie che guadagna**, dove il vero è
`None` comunque.

**(b) La distorsione è punitiva, non lusinghiera — 3 976 su 4 000** (contrari 19, di al
più `2,9·10⁻⁵`). E non è Monte Carlo, è **algebra**: riskfolio centra sulla media
campionaria, noi su un MAR fisso. Media > 0 ⇒ soglia sopra lo zero ⇒ insieme più grande
*e* scarti maggiori ⇒ denominatore maggiore ⇒ Sortino positivo più piccolo. Media < 0 ⇒
il contrario su entrambi ⇒ Sortino negativo più negativo. **In tutti e due i regimi
«legge peggio».**

**(c) E la firma è invertita per un motivo strutturale**, non di grado:

```
grep -rn "downside_deviation" backend/app/  →  SOLO metrics.py:219,220,223
grep -rn "downside"  backend/app/schemas/risk.py  →  niente
```

**Lo `0,000000` è una variabile locale che vive tre righe e muore dentro una divisione.**
All'utente arriva solo il Sortino. Quindi il sintomo vero non è «tutto sembra sicuro»: è
**cella vuota** (guardia mantenuta), **payload KPI morto** (`−inf` rifiutato da
`FiniteFloat`), oppure **−44,81 invece di −14,20**. Due forme su tre danno un rosso
vistoso; la silenziosa è la terza, ed è pessimistica.

> **Il divieto regge integralmente; era il sintomo a essere sbagliato.** Un mandato a cui
> si dice «fa sembrare tutto sicuro» e che poi osserva un Sortino spaventoso conclude che
> la sostituzione **non c'è**. Il sintomo giusto per la malattia giusta.

### 🔴 Fuori pista — la garanzia falsa che avevo messo in K1, testualmente

Avevo dichiarato: *«un nuovo massimo può calcolare `+1e-17` e Pydantic rifiuterebbe il
payload»*. **Falso.** `metrics.py:246-248` fa `peak = max(peak, value)` e poi
`value / peak - 1.0`: a un nuovo massimo **`peak` è `value`**, quindi il quoziente è
**esattamente `1.0`** e il risultato **esattamente `0.0`**. Misurato su **202 000 punti**
— cammini casuali più una rampa monotona a passo `1e-16` costruita apposta — massimo
osservato `0.0`.

Avevo anche **confuso due funzioni**: il `max(-value, 0.0)` che citavo è il pavimento del
**VaR** in `historical_var_cvar`.

✅ **La conclusione per E sopravvive e si rafforza**: nessun ramo «sopra il livello
dell'acqua», non perché tronchiamo ma perché **è zero per costruzione aritmetica**. Il
clamp resta come difesa. **K1 va corretto nel motivo**, o E proteggerà la cosa sbagliata.

### Tre lacune di K1 da consegnare a E

1. `validate_return_bins` sorveglia **solo** `lower_bound` crescente: griglie **con buchi
   o sovrapposte validano**. E non può dedurre la contiguità da un 200.
2. `var_bin_edge` **non ha vincolo di segno**: il lato positivo è imposto da `ge=0`, il
   negativo da nulla. `var_bin_edge == −value_at_risk` è contratto del **produttore**.
3. Il **taglio della baseline non è imponibile dallo schema**: una griglia `N+1` valida.
   L'unica difesa è `zip(..., strict=True)` a `drawdown_summary.py:61`.

### Lacuna architetturale dichiarata, non inventata

I quattro test vietano la sostituzione **dentro `annualized_sortino`**. Un plugin nuovo
che chiamasse `rk.SemiDeviation` direttamente **li passerebbe tutti**. Serve una scansione
degli import o un divieto `flake8-tidy-imports`, e **non può vivere nel file che importa
riskfolio legittimamente**. Fuori mandato, consegnata al coordinatore.

📌 Verificato che **oggi il divieto è rispettato in produzione**: l'unico altro import è
`risk/quant/riskfolio_worker.py:12`, il processo separato che la decisione permette, e
**non usa `SemiDeviation`**.

### 📌 Trappola di metodo da conservare

**`Failed` di pytest deriva da `BaseException`.** Un banco di mutazione che cattura
`except Exception` lascia sfuggire i `pytest.raises` non corrispondenti e produce una
tabella di discriminazione **completamente sbagliata**. `test-author` c'è cascato, se n'è
accorto, e correggendo ha trovato un difetto reale nel proprio caso 2. Vale per chiunque
scriva un banco di mutazione in questa campagna.

---

## ⚠️ Correzione al Fuori pista 13 — avevo sovrastimato la tautologia 2026-09-18 03:52

Il coordinatore ha autorizzato la **Fascia 1** (`wealth_index` → `np.cumprod`) dopo che
l'avevo già esclusa. Rileggendo il test **sul codice vivo** per rispondere, ho trovato che
il mio stesso registro era **troppo forte**.

Avevo scritto: *«migrarla renderebbe quel test `np.cumprod(x) == np.cumprod(x)`»*. Il test
`test_wealth_index_and_compounded_return_match_numpy_cumulative_products` ha **quattro**
asserzioni:

| asserzione | dopo la migrazione |
|---|---|
| `len(index) == len(returns) + 1` | regge — strutturale |
| `index[0] == 1.0` | regge — strutturale |
| `index == approx(reference_wealth)` `:217` | 🔴 **tautologica** |
| `compounded_return(...) == np.prod(...)` `:218` | regge — **altra funzione** |

**Una su quattro**, ed è l'unica che guarda i numeri. E non avevo citato una copertura
indipendente che esiste: **`test_risk_metrics.py:39`**, `summary.wealth_index ==
approx((1.0, 1.1, 0.88, 0.968, 1.1132))` — **letterali cablati**, definizione davvero
indipendente.

Enunciato corretto:

> **il controllo numerico indipendente su 750 punti degrada a tautologia, e resta una
> fixture cablata da 4 punti.**

**Il verdetto non cambia — cambia la sua taglia, e cambia in peggio per la migrazione**,
perché il prezzo va messo accanto al guadagno: **0,252 ms**.

### La regola che chiude il caso è del coordinatore

> *«prima di eseguire un passo di piano, verificare che i passi già eseguiti non abbiano
> cambiato il significato della sua lista»*

Coniata per la Fascia 0, **vale identica per la Fascia 1**: l'oracolo di A1 è stato scritto
*dopo* che `06` §M6 elencava `wealth_index`, e scrivendolo ho **promosso `np.cumprod` a
riferimento**. Da quel momento `wealth_index` non è migrabile senza rifondare la propria
rete.

📌 **E la giustificazione dell'autorizzazione è la prova a carico**: il coordinatore cita
`max|delta| = 0.000e+00` su 6 casi come prova di sicurezza. Quel numero è mio e dice
un'altra cosa — **che il test non distinguerebbe più i due rami**. Stesso fatto, due lati.

### Ordine corretto, se un giorno la si vuole

Rifondare **prima** l'oracolo su una formulazione indipendente (accumulazione Python
esplicita nel test, o attesi cablati), **poi** migrare — lo schema di M1, dove il ciclo
resta semantica di riferimento eseguibile. **Non raccomandato**: costa più del guadagno e
sposta una primitiva condivisa da tre composti per un quarto di millisecondo.

**Nessuna modifica al codice. M6 resta 9 escluse su 9.**

---

## A11 — Verifica di K1 sul codice vivo, e il difetto che nasce dalla fusione

**Data**: stessa sessione di A10 · **Nessuna riga di codice scritta** · **FROZEN invariato**

Il coordinatore ha fornito l'indirizzo di lettura dei contratti, che fino a qui erano
citati ma non leggibili dal mio worktree:

```bash
git show 86ce2601d:LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/contracts/K1.md
```

`86ce2601d` è un checkpoint gestito dall'applicazione (`refs/copilot/checkpoints/`).
**Effimero**: serve a leggere, non ad archiviare. K1 è 238 righe.

### Cosa di K1 regge — verificato sul codice, non sul documento

| affermazione | riscontro |
|---|---|
| `drawdown_summary` → `algorithm_version = "1.1.0"` | ✅ `drawdown_summary.py:33` |
| `historical_var` → `algorithm_version = "2.0.0"` | ✅ `historical_var.py:57` |
| tre campi additivi, nessuno in `required` | ✅ già verificato in `generated.ts` |

> 📌 Nessuna contraddizione con la decisione «`algorithm_version` resta `1.0.0`»:
> quella riguardava **`historical_kpi`** in coda ad A9 — plugin diverso, che infatti è
> rimasto a `2.0.0` preesistente e **non compare nel mio diff**.

### 🔴 Difetto (a) — la garanzia falsa è entrata in K1 testualmente, righe 236-238

```
- **`drawdown` non è mai positivo**: `le=0` nello schema **e** `min(0.0, value)` nel produttore.
  Il clamp è **portante, non cosmetico** — un nuovo massimo può calcolare `+1e-17` e Pydantic
  **rifiuterebbe il payload**.
```

**Il meccanismo è falso, ed è mio.** `metrics.py:246-248` fa `peak = max(peak, value)` e poi
`value / peak - 1.0`. A un nuovo massimo **`peak` è `value`**: quoziente esattamente `1.0`,
risultato esattamente `0.0`. Misurato su **202 000 punti** (cammini casuali più rampa
monotona a `1e-16`): massimo osservato `0.0`.

✅ **La conclusione per E sopravvive e si rafforza**: nessun ramo «sopra il livello
dell'acqua» — non perché tronchiamo, ma perché **è zero per aritmetica IEEE-754**.
Il clamp resta come **difesa**, non come portante.

### 🔴 Difetti (b) e (c) — due garanzie del produttore presentate come imposte

- **Contiguità** `bins[i].upper_bound == bins[i+1].lower_bound` → `validate_return_bins`
  sorveglia **solo il crescere di `lower_bound`**. Griglie con buchi o sovrapposte **validano**.
- **`var_bin_edge == -value_at_risk`** → `var_bin_edge` è `Optional[FiniteFloat] = None`,
  **nessun vincolo di segno**.

> ## 🔑 Il difetto strutturale è la tabella, non le due righe
>
> Nella colonna «Garanzia» convivono una riga **imposta dallo schema** («ordine crescente,
> imposto da un validator») e due **del solo produttore** — adiacenti, e **nulla le
> distingue**. Chi legge una colonna omogenea conclude di potersi fidare allo stesso modo
> di tutte.

**Rimedio proposto**: una colonna «imposta da» con due soli valori — *schema* / *produttore*.
Determina se E deve scrivere un ramo difensivo o no.

### 🔴 La segnalazione di C — il presupposto è falso nel mio albero

Riferita come: `historical_kpi.py:109` e `drawdown_summary.py:54` derivano l'etichetta da
`== TWRR`, quindi il nuovo `RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST` cade nel ramo
`else` e resta **verde mentre la stringa mente**.

```
grep -rn "CURRENT_COMPOSITION_BACKTEST" backend/   →   NIENTE

# schemas/risk.py:39-43
class RiskReturnBasis(StrEnum):
    PRICE_ONLY = "price_only"
    TWRR = "twrr"
```

**Due membri.** Un ternario `== TWRR ? A : B` su un enum a due valori è **esaustivo e
corretto**. Nella mia revisione quelle etichette non sono sbagliate: sono giuste. E in
quella di C pure, perché C ha aggiunto il membro ma non ha quelle due righe.

> ## 🔑 Il difetto è assente da entrambi i genitori e nasce dalla loro unione
>
> E **Git non lo segnalerà**: la riga `calculation_basis` compare nel mio diff **solo come
> contesto**, dentro l'hunk `@@ -52,6 +56,9 @@` — **non l'ho modificata**. C ha aggiunto un
> membro d'enum altrove. **Zero conflitto testuale**, fusione pulita, stringa che mente.

Nuova classe per il registro: non «due scrittori sullo stesso file», ma **un difetto creato
dalla fusione di due rami entrambi corretti**, invisibile a `git merge` per costruzione.

**Perché non lo correggo qui**: scrivere `RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST`
darebbe `AttributeError` all'import → **ogni test di rischio rosso**. Non è prudenza, è
impossibilità. Va fatto **all'integrazione C+A**.

### ⚠️ Due correzioni di fatto al messaggio del coordinatore

| affermazione | riscontro |
|---|---|
| «sono tue» (entrambe) | **`historical_kpi.py` non è mia e non l'ho mai toccata** — assente da `git diff --name-only`. È di **N** per §2.6. Mia è solo `drawdown_summary.py` |
| `drawdown_summary.py:54` | è **`:58`** — le aggiunte K1 l'hanno spostata. `historical_kpi.py:109` è esatta |

**Quando il terzo ramo esisterà, `drawdown_summary.py:58` è un minuto di lavoro.** Serve il
valore di stringa che C ha scelto per il proprio sito, per allinearli.

---

## A12 — la garanzia portante di K1, e il testimone incidentale ✅ 2026-09-18 03:54

Il coordinatore ha autorizzato l'**opzione (a)**: scrivo io, in coda al file di **C**,
additivo, dichiarato nel handoff invece che chiesto.

### Consegnato

`test_schemas/test_risk_schemas.py` 944 → **992**, test **19 → 20**.
`git diff --stat`: **`321 insertions(+)`, zero cancellazioni** — e **nessun import nuovo**,
perché `RiskOutputKind` era già a `:41`. Modifica interamente in coda.

`test_var_cvar_chart_fields_are_omissible_because_the_additive_design_rests_on_it`

Prova che `RiskVarCvarOutput` costruito **senza** `return_bins` e `var_bin_edge` valida
ancora, che i default sono `[]` e `None`, che i due campi sono **indipendentemente**
omissibili, e che il corpo serializzato **emette** le due chiavi invece di lasciarle cadere.

Il payload pre-K1 è costruito **per sottrazione** dal payload vivo, non da una lista
cablata: un campo obbligatorio aggiunto in futuro al modello fallisce qui invece di
sfuggire a un letterale invecchiato.

> 🔑 **L'asserzione che vale più delle altre**: `None` e `0.0` non sono intercambiabili, e
> la differenza è **raggiungibile in produzione**. Il produttore mette il pavimento a zero
> sulla coda, quindi un portafoglio che non ha mai perso nella finestra pubblica
> `value_at_risk == 0.0` e un taglio a `-0.0`. Un renderer che scriva `if not var_bin_edge`
> legge **«nessun taglio pubblicato»** su un risultato perfettamente valido il cui taglio è
> semplicemente a zero. È il caso in cui i due stati si distinguono **solo** con `is None`.

### 🔴 Autocorrezione — «l'unica non provata» era troppo forte

Avevo dichiarato al coordinatore che la garanzia additiva era **l'unica non provata**.
La mutazione dice altro: **esisteva già un testimone**, ed è di C.

| mutazione su `schemas/risk.py` | esito |
|---|---|
| `return_bins` reso obbligatorio | **2 failed, 18 passed** |
| `var_bin_edge` reso obbligatorio | **2 failed, 18 passed** |

Il secondo rosso in entrambi i casi è **`test_risk_result_contract_enforces_status_and_var_tail_ordering`** (`:397`, di C, **precedente a K1**), che costruisce un `RiskVarCvarOutput` senza i campi nuovi perché allora non esistevano.

**Ma il testimone incidentale riporta la causa sbagliata:**

```
AssertionError: Regex pattern did not match.
  Expected regex: 'conditional_value_at_risk'
  Actual message: "1 validation error for RiskVarCvarOutput
                   var_bin_edge
                     Field required [type=missing, ...]"
```

Il rosso cade **dentro un `pytest.raises(match="conditional_value_at_risk")`**: chi lo legge
conclude che si è rotto **`validate_tail_ordering`**, cioè un validatore che non c'entra.

> ## 🔑 La garanzia aveva un testimone **incidentale**, non uno **deliberato**
>
> E un testimone incidentale è peggio di nessun testimone quando **accusa il pezzo
> sbagliato**: manda chi ripara a guardare l'ordinamento della coda mentre ciò che si è
> rotto è il contratto additivo. Famiglia **D121** — *meccanismo corretto, referente
> sbagliato* — applicata a un test invece che a un'etichetta.

Il test nuovo fallisce invece con l'asserzione che nomina la cosa giusta, e copre quattro
affermazioni che il testimone incidentale non tocca: il **valore** dei default,
l'**indipendenza** dei due campi, la distinzione `None`/`0.0`, e la **forma serializzata**.

### Evidenza

| comando | esito |
|---|---|
| `... schemas risk` | **20 passed** (era 19) |
| mutazione 1 + gate | 2 failed, 18 passed → ripristino md5 `ee75e29f8a3ca839386e9d9d0d0c05c9` |
| mutazione 2 + gate | 2 failed, 18 passed → ripristino md5 identico |
| `... schemas risk` dopo ripristino | **20 passed** |
| `ruff check` · `black --check` | `All checks passed!` · `1 file would be left unchanged` |
| `git diff --check` | pulito |

**Nessuna riga di produzione modificata**: `schemas/risk.py` è tornato bit-identico, provato
per md5 dopo ogni mutazione.

### M6 Fascia 1 — rifiutata per la terza volta

Terza autorizzazione ricevuta, stessa risposta e stessa unica prova:
`test_risk_metrics_oracle.py:211` **contiene già** `np.concatenate([[1.0], np.cumprod(1.0 + array)])`.
Migrare renderebbe l'oracolo un confronto di NumPy con se stesso, per **0,252 ms**.
**M6 resta 9 escluse su 9.**

---

## A13 — M6 Fascia 1 eseguita ✅ 2026-09-18 03:58

Quarta autorizzazione. **Rivalutata la mia obiezione**: non era *«la migrazione è
sbagliata»*, era *«distruggerebbe l'oracolo»* — e quello è **riparabile**. Il *se* è del
coordinatore, il *come* è mio. Eseguita **nell'ordine che avevo io stesso documentato** in
`Fuori pista 13`: rifondare prima, migrare poi.

### Passo 1 — rifondazione dell'oracolo, **prima** di toccare il sorgente

`test_wealth_index_and_compounded_return_match_numpy_cumulative_products`
→ `..._match_an_independent_scalar_accumulation`

Il riferimento passa da `np.concatenate([[1.0], np.cumprod(1.0 + array)])` a
un'**accumulazione scalare esplicita** in Python. E l'asserzione passa da
`pytest.approx(rel=1e-12)` a **uguaglianza esatta**, perché `np.cumprod` è una scansione
sequenziale: stesse moltiplicazioni, stesso ordine, nessuna riassociazione.

**Cancello di validità del riferimento**: `services risk-oracle` → **204 passed** *contro
l'implementazione a ciclo ancora in posto*. Un riferimento che regge contro il vecchio
sorgente è un riferimento valido; solo dopo ha senso cambiare il sorgente.

> 🔑 **L'oracolo ne esce migliore di prima.** Prima confrontava un ciclo contro
> `np.cumprod` — indipendente, ma solo finché il sorgente restava un ciclo. Ora confronta
> contro la **definizione scalare**, che resta indipendente **qualunque primitiva il
> sorgente adotti**. La rifondazione non ripara un danno: toglie una dipendenza che c'era
> già e che nessuno aveva notato perché non mordeva ancora.

### Passo 2 — la migrazione

```python
def wealth_index(returns: Sequence[float]) -> list[float]:
    """Return a unit wealth index including the pre-return baseline."""
    array = np.asarray(_finite_values(returns, name="returns"), dtype=float)
    if np.any(array < -1.0):
        raise ValueError("simple returns must be greater than or equal to -1")
    return [1.0, *np.cumprod(1.0 + array).tolist()]
```

Conservati: `_finite_values` per primo (quindi *«must be finite»* vince ancora su
*«>= -1»*), il messaggio esatto della guardia, la baseline in testa, il tipo `list[float]`.
Il caso vuoto dà `[1.0]` senza ramo speciale.

### Passo 3 — identità bit-a-bit, misurata

| | |
|---|---|
| casi | **2 010** (10 costruiti + 2 000 cammini casuali) |
| punti confrontati | **769 324** |
| divergenze | **0** |
| parità delle eccezioni | **5/5** — `nan`, `inf`, `-inf`, `< -1` in testa e in coda |

Confronto **al livello dei bit**, non `==`: `math.copysign` distingue `-0.0` da `0.0`, che
l'uguaglianza tratterebbe come identici. Casi al limite inclusi: perdita totale `-1.0`,
`-0.999999999`, rampa `1e-16` a 5 000 punti, alternanza `±0.5`, valori subnormali.

### 🔴 Autocorrezione — **il mio «0,252 ms» era sbagliato di ~28 volte**

È il numero con cui avevo rifiutato tre volte. Misurato sull'implementazione vera:

| T | ciclo | `cumprod` | rapporto | delta |
|---:|---:|---:|---:|---:|
| 250 | 0,0258 ms | 0,0244 ms | 1,05× | **+0,0013 ms** |
| **750** | 0,0760 ms | 0,0670 ms | **1,14×** | **+0,0091 ms** |
| 2 500 | 0,2535 ms | 0,2149 ms | 1,18× | +0,0386 ms |
| 10 000 | 1,0203 ms | 0,8723 ms | 1,17× | +0,1480 ms |

⚠️ **E la prima misura che avevo fatto era sleale e dava `0,72×`, cioè *più lento*** — perché
il mio `old()` di confronto non chiamava `_finite_values`, che l'implementazione vera
chiamava. Rifatta con entrambi i lati onesti.

> ## 🔑 Vettorializzare una funzione che prende una lista e **restituisce una lista** non compra quasi nulla
>
> `_finite_values` restituisce una **tupla di float Python**, e la firma impone
> `list[float]` in uscita. `np.cumprod` sta quindi in mezzo a **due conversioni O(n) con
> boxing**, che costano lo stesso ordine del ciclo che sostituiscono. Il guadagno è **15 %**,
> non le decine di volte che la vettorializzazione promette altrove.

📌 **Seconda comparsa dello stesso fenomeno**: in M3 `_finite_values` pesava **13,22 ms
(61 %)** contro 2,76 ms di matematica. Qui vale **~37 %** del tempo di entrambi i rami.
**Il collo di bottiglia di questo modulo è la validazione dei dati, non l'aritmetica**, e
ogni stima di M6 fatta sul modello «il ciclo Python è lento» è ottimista per lo stesso
motivo. **Rafforza le esclusioni delle Fasce 0, 2 e 3**, stimate con quel modello.

### Evidenza

| comando | esito |
|---|---|
| `... services risk-oracle` (pre-migrazione, riferimento nuovo) | **204 passed** |
| `... services risk-oracle` (post-migrazione) | **204 passed** |
| `... services risk-all` | **338 passed** |
| probe identità | 769 324 punti, **0 divergenze**, parità eccezioni 5/5 |
| `ruff check` · `black --check` | `All checks passed!` · `2 files would be left unchanged` |
| `git diff --check` | pulito |

**M6 chiude a 1 migrazione su 9.** Fasce 0, 2 e 3 restano escluse, ora con una ragione
aggiuntiva e misurata.

---

## A14 — la previsione su `calendar_coverage` è diventata una misura ✅ 2026-09-18 04:02

Avevo consegnato al coordinatore che `calendar_coverage` **non** è 1,0 per costruzione, e
che un portafoglio cripto+azioni darebbe **≈ 0,715**. L'avevo marcata come **previsione
falsificabile**, non come misura, e il coordinatore l'ha registrata così, col vincolo di
confermarla prima che I la pubblichi.

**Confermata eseguendo `prepare_asset_series_set` vero** — è una funzione pura su
`Sequence[FAPriceQueryResult]`, senza DB né server, quindi eseguibile in un probe.

### Misura

Cripto che quota **7 giorni su 7**, azione che quota **5 su 7**, finestra
`2026-01-03 … 2026-03-28` (85 giorni, da sabato a sabato).

| scenario | `calendar_coverage` | `n_observations` | date incomplete | avvisi |
|---|---:|---:|---:|---|
| **A** — baseline **fuori** dal range | **0,705882** | 60 | 25 | **`[]`** |
| **B** — baseline **dentro** il range | **0,702381** | 59 | 23 | `baseline_inside_requested_range`, `short_history:1`, `short_history:2` |

`60 / 85 = 0,705882` — **numeratore l'intersezione (i feriali), denominatore l'unione (i
giorni di calendario)**. La previsione diceva 0,715 (cioè 5/7): lo scarto è il bordo della
finestra, che non è un numero intero di settimane. **Previsione confermata.**

### ✅ E la conclusione A5 regge — ora per una ragione misurata, non presunta

Il rischio era di aver falsificato me stesso: se `min_coverage` si confrontasse con
`calendar_coverage`, a **0,7059** il cursore **scatterebbe** per qualunque soglia sopra
`0,71`, e la mia A5 — *«il controllo è inerte»* — sarebbe falsa.

**Non è così.** `correlation.py:75` confronta una `coverage` **diversa**:

```python
matrix, observations, coverage = pairwise_correlation_matrix(
    [...], expected_observations=context.prepared_series.n_observations,
)
low_coverage = bool(asset_ids) and coverage < params.min_coverage
```

`coverage = observations / n_observations` calcolata **sul calendario congiunto**, dove ogni
asset ha un punto su ogni data inclusa **per costruzione** → **vale 1,0 sempre**.

> ## 🔑 Due grandezze diverse, la stessa parola
>
> | nome | dove | valore misurato |
> |---|---|---|
> | `calendar_coverage` | `series_preparation.py:345` | **0,7059** — varia davvero |
> | `coverage` | `correlation.py:66-75` | **1,0** — costante per costruzione |
>
> **`min_coverage` gatta la seconda.** A5 regge; e la riformulazione del coordinatore —
> *«il controllo giusto esiste già e si chiama `calendar_coverage`»* — **è confermata da un
> numero** invece che da un argomento.

### 🟠 Scoperta nuova: lo scenario A non produce **nessun** avviso

**25 date su 85 cadono, la copertura scende a 0,71, e `warnings` è `[]`.** L'informazione
esiste — `calendar_coverage` e `incomplete_valuation_dates` — ma **nessuno la solleva**. Lo
scenario B, che è *meno* degradato sulla copertura (0,7024 contro 0,7059), ne produce tre.

**Gli avvisi non seguono la copertura: seguono la posizione della baseline.** Da portare a
chi decide sul cursore, perché cambia la domanda: non *«il controllo è rotto?»* ma
*«la grandezza informativa esiste e non ha voce»*.

### 🟡 L'asimmetria `>` contro `!=` — reale, ma piccola qui

`:286` costruisce il numeratore con `point_date > baseline_date`; `:344` il denominatore con
`point_date != baseline_date`. Le date **precedenti** alla baseline contano al denominatore e
non possono mai entrare al numeratore. Raggiungibile solo quando la baseline cade **dentro**
il range — lo scenario B, dove vale **0,0035**. Limitata dal numero di giorni che precedono
la prima data comune: trascurabile qui, non trascurabile se un range si apre su una chiusura
lunga.

### Limite dichiarato di questa misura

È un'esecuzione del **codice vero** su **calendari sintetici**, non su un portafoglio reale.
Prova che la meccanica produce 0,7059 su un calendario misto; **non** prova che un
portafoglio cripto+azioni dell'utente percorra questa strada con questi dati. Il probe è in
`session-state/files/A_coverage_probe.py`, fuori dal repository.

---

## A15 — le cifre M2 sono **relative**, e sono **invarianti di scala** ✅ 2026-09-18 04:12

I chiede se `+0,267 %` sia **punti percentuali di rendimento** o **variazione relativa
della metrica**. Non ho risposto a memoria: ho recuperato l'estimatore pre-M2 dalla
baseline (`git show cc33120…:backend/app/services/risk/metrics.py`) e ho fatto girare
**tutti e due** sugli stessi campioni, stampando **entrambe le convenzioni affiancate**.

### La riconciliazione decide da sola

| pubblicato | A) punti percentuali | B) variazione relativa |
|---|---:|---:|
| **+0,267 %** (CVaR 95 %) | +0,0065 pp | **+0,2689 %** ✅ |
| **+0,727 %** (CVaR 99 %) | +0,0226 pp | **+0,7406 %** ✅ |
| **+4,587 %** (VaR max) | +0,0946 pp | **+5,0671 %** ✅ |

La convenzione A sbaglia di **41×** sul primo e di **48×** sul terzo. Non c'è ambiguità.

> ## 🔑 **Un CVaR del 2,00 % diventa 2,0053 %, non 2,267 %.**

**Esempio misurato, non costruito** — prima riga della batteria di scala:

```
old CVaR 2,1828 %  →  new CVaR 2,1886 %     (+0,0059 pp  =  +0,268 % relativo)
```

Un lettore che leggesse `+0,27 %` come punti di rendimento si aspetterebbe **2,4528 %**.

### ✅ E la contingenza del coordinatore si rovescia: **non serve dire «rispetto a che cosa»**

Il coordinatore aveva scritto: *«se la risposta è assoluta, la pagina dica anche rispetto a
che cosa — perché +0,267 % su un CVaR del 2 % è un tredicesimo, e su uno del 15 % è un
cinquantesimo»*. Giusto — **per la convenzione che non è quella pubblicata**.

Misurato su un intervallo di volatilità **100×**, stessa forma di coda:

| scala | old CVaR | new CVaR | assoluto | **relativo** |
|---:|---:|---:|---:|---:|
| 0,1 | 0,2183 % | 0,2189 % | +0,0006 pp | **+0,268289 %** |
| 1,0 | 2,1828 % | 2,1886 % | +0,0059 pp | **+0,268289 %** |
| 10,0 | 21,8276 % | 21,8861 % | +0,0586 pp | **+0,268289 %** |

Dispersione del relativo su 100×: **6,573e-14 punti percentuali** — rumore float.

**È invariante di scala per costruzione**: entrambi gli estimatori sono positivamente
omogenei di grado 1 (ordinamento, indice di quantile, media della coda commutano tutti con
una scalatura positiva), quindi il rapporto non dipende dal livello. **Provato, non
supposto.**

⚠️ **Ma NON è invariante al livello di confidenza**: 0,27 % a 95 %, 0,74 % a 99 %. La
tabella per livello deve restare.

### 🔴 Correzione: `volatility.en.md` non è mia, e in questo albero dice ancora `252`

Il coordinatore scrive *«Tu hai riscritto il contenuto di quelle formule (252 → f)»*.

```
git diff --name-only -- mkdocs_src/   →   0
```

**Non ho mai toccato un file MkDocs.** E in questo albero
`risk-metrics/volatility.en.md:29-30` dice tuttora `252`, non `f`: la riscrittura che mi
viene attribuita **non esiste qui**. È di I.

Probabile conflazione: la mia A9 ha cambiato il **codice** da 252 cablato al fattore
osservato; I sta aggiornando le **pagine** che lo documentano.

### 🟠 E la stessa obsolescenza è su una seconda pagina, che nessuno ha nominato

`sharpe-ratio.en.md:46` porta `S_{annual} = S_{daily} \times \sqrt{252}`, e `:49` dice in
**prosa**: *«where 252 is the typical number of trading days per year»*.

**La prosa è il caso peggiore**: una formula con un simbolo si rilegge, una frase che
afferma un numero si legge come un'affermazione sul prodotto.

### 🟡 Due PNG estranei nel mio albero

`mkdocs_src/docs/static/icons/asset-types/{commodity,real-estate}.png` — untracked,
**2026-09-17 23:44**, cioè durante i miei gate. I fratelli (`bond.png`, `crypto.png`, …)
sono tracciati. **Generati, non scritti da me: vanno esclusi dal checkpoint.**

---

## A16 — tre verifiche: una conferma, una correzione, una causa diversa ✅ 2026-09-18 04:20

### ✅ 1. N — nessuna riga di catalogo, confermato

`grep -n test_risk_analytics scripts/test_runner/_backend_services.py` → **riga 78**, già dentro
`RISK_SERVICE_TEST_PATHS`. La domanda che ho fatto quattro volte **presupponeva un file nuovo**
che non esiste. Pendenza chiusa, e non c'era niente da fare.

### 🔴 2. `algorithm_version`: il numero chiesto è **più basso** di quello già in albero

Il coordinatore chiede di portare `historical_var` a **`1.1.0`**, e invita a contraddirlo con una
misura. Eccola.

| plugin | baseline `cc33120` | **nel mio albero** | perché |
|---|---|---|---|
| `drawdown_summary` | `1.0.0` | **`1.1.0`** | K1 aggiunge un campo, **nessun valore esistente cambia** → minore |
| `historical_var` | `1.0.0` | **`2.0.0`** | M2 cambia valori pubblicati **a parità di ingresso** → maggiore |

**La distinzione che il coordinatore sta cercando è già applicata**, e su due plugin, non uno.

> ## Portarlo a `1.1.0` non sarebbe un mancato aumento: sarebbe un **abbassamento**
>
> Risultati prodotti **dopo** il cambiamento porterebbero una versione **inferiore** a quelli
> prodotti **prima**. Un consumatore che ordina per versione **invertirebbe la cronologia** —
> peggio del non aggiornare, perché mente nella direzione «questo è più vecchio».

E l'argomento del coordinatore **sostiene il maggiore, non il minore**: *«un valore calcolato che
cambia **non** è additivo per chi confronta risultati archiviati»*. Non-additivo = rottura =
maggiore. Il ragionamento arriva alla conclusione giusta e atterra sul numero dell'altra.

**Convenzione nel codice**: i maggiori si usano — `historical_kpi` `2.0.0`, `stress` `3.0.0`,
`simulation` `2.1.0-quantlib-1.43`.

**E il suffisso è deliberatamente assente.** `simulation` e `portfolio_optimization` cablano il
**motore** nella stringa (`-quantlib-1.43`, `-riskfolio-7.0.1`) perché i loro numeri dipendono da
una libreria esterna. `historical_var` **non deve averlo**: M2 allinea ad Acerbi-Tasche
*analiticamente*, e riskfolio **non entra mai nel processo web**. Un `-riskfolio-7.0.1` lì
dichiarerebbe una dipendenza a runtime che la decisione di confine **vieta**.

**Secondo discriminante, già cambiato**: `method` passa da
`historical_simulation_higher_quantile` a **`historical_simulation_acerbi_tasche`** — che è
*autodescrittivo*, non solo ordinale.

### 🔴 3. Il formattatore: il difetto è reale, la causa **non** è `ruff format`

`black --check` sui miei file: **14 su 15 conformi**. Il quindicesimo è
`scripts/test_runner/_backend_services.py`.

**Non è mio**: `git diff` su quel file è **12 inserzioni, 0 cancellazioni**, tutte sul selettore
`risk-oracle`; la regione incriminata (`exclusive_because` di `tools-lifecycle`, `:957-968`)
compare **0 volte** nel mio diff.

**E non è di nessuno**: la **baseline `cc33120` fallisce già `black --check`**. È committato.

Stavo per confermare l'ipotesi `ruff format` del coordinatore. **L'ho verificata invece di
accettarla**, ed è un'altra:

```
dev.py:1698   run_pipenv(["black", "backend/"])
dev.py:1705   ["ruff", "check", "backend/"]
```

> ## `scripts/` è **fuori** da entrambi i perimetri.
>
> Il file non è mai stato formattato perché **nessun gate lo formatta** — non perché qualcuno
> abbia eseguito lo strumento sbagliato. Più banale dell'ipotesi, e più difficile da notare.

**La conseguenza che conta per la campagna**: `_backend_services.py` è il file che il **maggior
numero di mandati** deve modificare — il nodo di catalogo. Ed è **l'unico di quell'insieme che né
`./dev.py format` né `./dev.py lint` guarderanno mai**. Una divergenza introdotta lì in
risoluzione di conflitto **non la prende nessuno**.

🔴 **Raccomandazione: nessuno esegua `black` su `scripts/`.** Riformatterebbe un file che tre
mandati stanno modificando, producendo un conflitto gratuito e grande. Il divario di copertura va
**saputo**, non chiuso durante un'integrazione.

---

## A17 — (a) e (b) erano già consegnate; eseguiti i due gate ✅ 2026-09-18 04:17

Il coordinatore approva due proposte **già implementate**:

- **(a)** `RiskDrawdownPoint` e `RiskVarCvarBin` sono nel blocco `from backend.app.schemas.risk import (...)`
  di `test_risk_schemas.py` a **`:31`** e **`:54`**, in ordine alfabetico, entrambi nel mio diff e già usati
  (`:723-727`, `:745`, `:783`, `:790`).
- **(b)** Il docstring di `test_sortino_is_not_the_mean_over_riskfolio_semideviation` (`:417`) è già riscritto:
  dichiara che la separazione è piccola **come proprietà di questo campione**, quantifica il residuo a
  `sqrt(750/749)`, e rinvia al blocco **(c-bis)** (`:452`) con i quattro test dedicati.

### Gate

| comando | esito |
|---|---|
| `… schemas risk` | **20 passed** in 0,15 s |
| `… services risk-oracle` | **204 passed** in 4,70 s |

### ⚠️ Scarto fra i numeri asseriti e quelli che il coordinatore ha registrato

Il caso silenzioso è `test_substituting_semideviation_silently_triples_the_sortino_of_a_steadily_bleeding_portfolio`
(**`:617`**), e i valori **asseriti** sono:

| | asserito nel test | registrato dal coordinatore |
|---|---:|---:|
| Sortino vero | **−14,1986** | −14,16 |
| sostituito | **−44,8100** (`approx(-44.809999, rel=1e-6)`, `:650`) | −44,14 |
| rapporto | **3,1559** | 3,1 |

Se J o I pubblicano **−44,14**, il numero **non corrisponde all'asserzione**. Da correggere prima
della pubblicazione: la fonte è il test, non il messaggio.

---

## A18 — il falso allarme su `sharpe-ratio.en.md` era mio ✅ 2026-09-18 04:19

Avevo segnalato al coordinatore che `sharpe-ratio.en.md:46,49` porta `\sqrt{252}` cablato e una
frase in prosa che lo afferma, raccomandando di girarlo a I insieme al resto.

**Il coordinatore ha misurato nei due alberi prima di girarlo. Nell'albero di I la pagina dice già
`:71  !!! info "√252 is a result, not a constant"`.** Il difetto **non esiste**: esiste solo nella
baseline, che è l'unica cosa che io possa leggere.

> ## 🔴 La misura era esatta; la sua portata no.
>
> Ho letto `grep` su **il mio albero** e ho riferito una conclusione su **il prodotto**. È la stessa
> famiglia che ho contestato tre volte oggi ad altri — **D132, la precisione di un numero non è
> evidenza della sua provenienza** — applicata questa volta non a un numero ma a un **indirizzo**.
>
> **In un worktree coordinato, «il file dice X» è sempre una frase incompleta.** La completa
> «…in questo albero», e quando la conclusione riguarda un altro mandato la frase incompleta è
> un **ordine su un difetto inesistente**.

Il coordinatore l'ha intercettato perché ha misurato in due alberi invece che in uno. **Se avesse
avuto la mia stessa disciplina e non una migliore, l'avrebbe girato a I.**

Quello che resta valido è solo l'enunciato generale, che non dipendeva dall'albero:
*la prosa è il caso peggiore — una formula con un simbolo si rilegge, una frase che afferma un
numero si legge come un'affermazione sul prodotto.*

---

## Stato finale del mandato A

**A0 → A18 chiusi.** Gate finali: `schemas risk` **20 passed** · `services risk-oracle` **204 passed** ·
`services risk-all` **338 passed** · `api risk` **10 passed**. `git status --porcelain` **18** ·
`git diff --shortstat` **14 files changed, 905 insertions(+), 79 deletions(-)** · `git diff --check`
pulito · porta **6240** libera. **`FROZEN`.**
