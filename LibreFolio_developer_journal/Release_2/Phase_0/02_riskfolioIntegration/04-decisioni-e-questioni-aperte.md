# 04 — Decisioni e questioni aperte

**Data apertura**: 16 Settembre 2026
**Natura**: documento **vivo**. Ogni decisione presa si registra qui con data e
motivazione; ogni questione aperta resta qui finché non è chiusa.

---

## 1. Decisioni prese

| # | Data | Decisione | Motivazione |
|---|---|---|---|
| D1 | 16 Set 2026 | **Tesi adottata**: Risk risponde a *«il mio portafoglio è quello che credo che sia?»*, non a *«quanto rischio ho?»* | Un numero isolato non produce decisioni; una discrepanza sì |
| D2 | 16 Set 2026 | **Quattro livelli di domanda** (L1 fatti · L2 struttura · L3 relatività · L4 proiezione) | L1/L2/L4 sono autoreferenziali; serviva la domanda comparativa, altrimenti Sharpe/beta/TE restano senza casa |
| D3 | 16 Set 2026 | **Regola dei pesi**: con pesi → euro → «io»; senza pesi → percentuali → «questi» | Rende impossibile per costruzione confondere Asset Global con Broker Detail |
| D4 | 16 Set 2026 | **VaR/CVaR restano**, riformulati in scala temporale con CVaR primario | Sono oggettivi e basati sui dati; il difetto era l'assenza di scala dichiarata |
| D5 | 16 Set 2026 | **TE e IR rimossi dalla UI** (backend intatto) | Misurano l'aderenza a un mandato che un investitore privato non ha |
| D6 | 16 Set 2026 | **Portfolio optimization rinviata** a tempo indeterminato | Output prescrittivo non giustificabile; LibreFolio è un tracker, non un consulente |
| D7 | 16 Set 2026 | **Monte Carlo rifondato fino al livello 3** (bootstrap, GJR-GARCH, preset prescritti); livelli 4-5 rinviati | Il bootstrap batte il GBM su onestà, realismo, spiegabilità e costo |
| D8 | 16 Set 2026 | **Asset Detail parcheggiato in beta**, fuori da questo giro | Priorità su Dashboard, Broker Detail e Asset Global |
| D9 | 16 Set 2026 | **Segnali rolling restano nella Overview di Asset Detail** | Stanno bene dove sono; una card con un solo valore puntuale perde la forma nel tempo |
| D10 | 16 Set 2026 | **Broker Detail = stessa grammatica di Dashboard**, stesso componente con scope diverso | Già vero nel codice; va reso esplicito e preservato |
| D11 | 16 Set 2026 | **Asset Global = laboratorio**, non «un'altra vista del portafoglio» | Il pannello `analysis` rende il concetto già di prima classe nel modello dati |
| D12 | 16 Set 2026 | **Catena G6 abbandonata**, non ripresa | 23 item a catena singola con gate bloccanti: un solo stop congela tutto |
| D13 | 16 Set 2026 | **L3 con benchmark persistente** scelto fra gli asset in DB, da subito | Senza benchmark persistente il beta è un numero senza contesto e L3 resta la domanda debole |
| D14 | 16 Set 2026 | **Serie di drawdown dal backend**, non derivata client-side | Una curva calcolata nel browser può contraddire lo scalare del motore: due numeri discordi sullo stesso schermo costano più fiducia di quanta ne dia il grafico. Costo minore del previsto: `RiskComparisonPoint.primary_drawdown` già la calcola |
| D15 | 16 Set 2026 | **Ricostruire i componenti risk** sulle primitive condivise, dopo aver promosso quelle generiche in `components/ui/` | Ridisegnare il layout sopra gli stessi mattoni storti non risolve nulla |
| D16 | 16 Set 2026 | **Istogramma della distribuzione dei rendimenti** in v1, con VaR e CVaR marcati sopra; nuovo campo backend per i bin | Rende visibile la *definizione* delle due metriche: il CVaR è la media della coda rossa. Nessun testo lo spiega meglio |
| D17 | 16 Set 2026 | **Sei rappresentazioni adottate**: underwater, istogramma, barre appaiate peso/contributo, heatmap rifatta, scatter rischio-rendimento, tornado degli scenari | Ogni numero ha una forma che lo spiega; la card numerica è il ripiego, non il default |
| D18 | 16 Set 2026 | **`SignalDomain.PORTFOLIO` non serve per la v1** | Le sei rappresentazioni scelte usano dati che il backend già produce. Per la volatilità l'istogramma dice più di una sparkline del suo rolling |
| D19 | 16 Set 2026 | **Selezione di Asset Global persistita in `localStorage`**, con fallback agli asset posseduti | Il seed a cento asset apre una matrice di diecimila celle e non offre alcun modo di disfarla |
| D20 | 16 Set 2026 | **Nessuna generalizzazione della piattaforma segnali** per l'underwater chart | `underwater_drawdown` vive già in `services/risk/metrics.py` ed è il *segnale* a importarla dal rischio, non il contrario. `drawdown_episodes()` calcola già la serie in una variabile locale e ne butta via tutto tranne gli scalari |
| D21 | 16 Set 2026 | **Bin dell'istogramma secondo Freedman-Diaconis**, con un bordo forzato sul quantile del VaR e binning sulla stessa serie a `horizon_days` | L'IQR è robusto agli outlier; deviazione standard e normalità userebbero la coda per decidere come disegnare la coda. Il bordo forzato rende l'area rossa esattamente il 5% |
| D22 | 16 Set 2026 | **Nessuna gaussiana sovrapposta all'istogramma** (chiude Q6) | Il VaR mostrato è un quantile empirico: la campana confronterebbe i dati con un modello che non usiamo, e suggerirebbe che lo scarto sia un'anomalia mentre le code grasse sono la norma |
| D23 | 16 Set 2026 | **Riskfolio-Lib resta installata** (chiude Q2) | Misurata: 2,5 MB, closure solver ~16 MB su 2 780 totali. Lo 0,6% dell'immagine. I pesi veri sono scipy, pandas e QuantLib |
| D24 | 16 Set 2026 | **Le funzioni scalari di `metrics.py` non si toccano** | Coincidono con Riskfolio fino all'ottavo decimale su VaR, max drawdown, Sharpe e risk contribution; costano microsecondi; `math.fsum` dà una sommatoria compensata che `np.sum` non garantisce |
| D25 | 16 Set 2026 | **Riskfolio diventa oracolo di test per `metrics.py`** | `test_risk_metrics.py` verifica solo proprietà interne: nessun controllo indipendente. Venti righe coprono il buco e avrebbero intercettato da sole la trappola `MDD_Abs`/`MDD_Rel` |
| D26 | 16 Set 2026 | **`correlation_matrix` e `covariance_matrix` vanno vettorializzate** | O(N²·T) in Python puro: 3,7 s su cento asset contro 0,2 ms di NumPy. Il Python puro trattiene la GIL, NumPy la rilascia nel BLAS |
| ~~D27~~ | ~~16 Set 2026~~ | ~~Convenzione CVaR nostra confermata~~ | **REVOCATA lo stesso giorno da D28.** Motivata dalla spiegabilità, senza aver misurato la distorsione |
| D28 | 16 Set 2026 | **CVaR migra allo stimatore coerente** (Acerbi-Tasche / Rockafellar-Uryasev), off-by-one incluso | Il nostro è più basso di Riskfolio **2000 volte su 2000**, in media −0,27%, a sette deviazioni standard dallo zero. Non è convenzione: è distorsione. L'argomento della spiegabilità non regge, perché Acerbi-Tasche *è* «la media delle giornate peggiori» e lo scarto è invisibile |
| D29 | 16 Set 2026 | **Segnali rolling migrano a `pandas.rolling`** — priorità massima | `signal_helpers.py:69-84` copia una fetta e richiama la funzione scalare a ogni passo: fino a **1 514× più lento a valori identici**, e gira a ogni caricamento di grafico |
| ~~D30~~ | ~~16 Set 2026~~ | ~~Le funzioni scalari a chiamata singola restano in Python puro~~ | **REVOCATA da D36.** Motivata dalla velocità, che è il criterio sbagliato |
| D36 | 16 Set 2026 | **Criterio di possesso, non di velocità: A migra, B si valida, C si acquisisce** | (A) doppioni veri → migrare: VaR, CVaR, Sharpe, deviazione standard, matrici, **risk contribution** (verificata identica a `Risk_Contribution(rm="MV")`). (B) composti che la libreria non esprime → restano, ma con oracolo M4: `summarize_drawdown` dà massimo **e durata** in una passata (0,223 ms) mentre `MDD_Rel` dà un float in 0,904 ms e la durata **non ce l'ha**. (C) ciò che non abbiamo → Q7. Argomento decisivo: il CVaR l'abbiamo scritto noi ed è sbagliato in silenzio |
| D37 | 16 Set 2026 | **`MDD_Abs` non diventa un secondo segnale** | Non è «un altro drawdown»: è lo stesso su curva **non composta**, con il buco in unità assolute anziché in percentuale del picco. Resta lineare nei pesi, quindi serve ai solutori; per un utente non significa nulla di naturale. La nostra funzione **è già `MDD_Rel`**, cifra per cifra a meno del segno |
| D31 | 16 Set 2026 | **I 17 plugin di analisi tecnica non si toccano** | Audit: una sola chiamata `ta.*` ciascuno, zero aritmetica a mano dopo. E 16 su 17 passano `talib=True`, quindi girano già su TA-Lib 0.7.1 in C. Sono il modello, non il debito |
| D32 | 16 Set 2026 | **La libreria si sceglie per mestiere, non per marca** | pandas per le finestre mobili (Riskfolio **non ha** funzioni rolling), NumPy per l'algebra (`covar_matrix('hist')` *è* `np.cov` con 2-3× di sovrapprezzo e obbligo di `DataFrame`), Riskfolio per le misure di rischio e l'ottimizzazione, TA-Lib per gli indicatori |
| D33 | 16 Set 2026 | **`scipy` non è rimovibile e non va contata come peso del ROI** | Un solo import nostro (`roi_utils.py:19`), ma è dipendenza obbligatoria di `riskfolio-lib`, `cvxpy`, `scs`, `clarabel`, `osqp`, `scikit-learn`. Gira a ogni ottimizzazione |
| D34 | 16 Set 2026 | **Gli stimatori robusti di covarianza restano fuori da M3** | Ledoit-Wolf, Gerber e denoising sono un miglioramento di *qualità della stima*, non di velocità: 25,4 ms contro 0,2 ms. M3 è un intervento a comportamento invariato. → TODO separato |
| D35 | 16 Set 2026 | **`AuxFunctions.numBins` non si usa per l'istogramma** | Il nome inganna: è la formula di Hacine-Gharbi per la discretizzazione della mutua informazione, non per un istogramma di rendimenti. `freedman_bin_width` di riskfolio è invece astropy ri-esportata e dà gli stessi 21 bin di NumPy: si resta su `np.histogram(x, bins='fd')` |
| D38 | 16 Set 2026 | **`NEA` entra come KPI di L2, non come metrica di punta** | Indice di concentrazione dei pesi: `1/Σwᵢ²`, inverso di Herfindahl. Solo i pesi, 0,0025 ms. Su «3 grossi + 20 briciole» dà **4,12 su 23 posizioni**. Sta **accanto** a correlazione e contributo al rischio, non al loro posto: è cieco alla correlazione — tre portafogli di 10 asset equipesati con ρ 0 / 0,5 / 0,95 danno NEA **10,00 in tutti e tre** mentre la volatilità reale va da 0,0038 a 0,0116 (nemmeno sui contributi cambia: 9,97 contro 10,00). Va accoppiato al **diversification ratio** (3,15 → 1,35 → 1,02), che riskfolio non ha: tre righe di NumPy sulla covarianza già calcolata |
| D45 | 16 Set 2026 | **`WR` entra come KPI di L1, `RG` come colonna di Asset Global** | `WR` è la peggior giornata **realmente accaduta**: non una stima. Sta accanto al VaR per contrasto — il VaR dice «una su venti va peggio di così», `WR` dice «e la peggiore è stata questa». `RG` (escursione massimo-minimo) aggiunge poco su un portafoglio ma funziona come colonna di confronto fra strumenti. `MAD` resta fuori: misura la stessa cosa della volatilità |
| D43 | 16 Set 2026 | **`Kurtosis` non entra: non è stimabile su una singola storia** | Due ragioni indipendenti. (1) La versione riskfolio non è standardizzata: `sqrt(Σ(μ−x)⁴/T)`, confermato dal docstring dell'ottimizzatore `'KT': Square Root of Kurtosis`; su gaussiana dà 0,00034462 = `sqrt(m₄)` esatto mentre la kurtosi vera è 2,989. (2) **Decisiva**: è un momento di ordine quarto, la sua incertezza dipende dall'ottavo. Con eccesso vero 6,0 e tre anni di storia la stima cade **fra 1,2 e 10,8**; con cinquant'anni la mediana è ancora 4,02, distorta verso il basso. Togliere 10 giorni su 750 porta 3,88 → 0,63. E non discrimina: obbligazionario 0,6-2,4, ETF 2,2-**19,9**, azione singola 4,2-48,1 — intervalli sovrapposti, tutti sopra zero. **Dove serve davvero**: come misura per l'ottimizzatore (`rm="KT"`) alimentata da `cokurt_matrix`, cioè su universi ampi dove la media cancella il rumore. Per «quanto sono brutte le mie giornate brutte?» su pochi asset la risposta migliore resta il **CVaR**, che è una percentuale leggibile |
| D39 | 16 Set 2026 | **`Sharpe(rm=...)` entra come risposta a L3** | L3 contiene un buco — pagato per *quale* rischio? `rm="MDD"` **è** il Calmar ratio, `rm="UCI"` **è** il Martin ratio. Non sono decorazioni: **la classifica cambia**. Su due asset costruiti apposta, Sharpe premia B (0,89 contro 0,60) mentre Calmar (0,48 contro 0,28) e Martin (1,15 contro 0,55) premiano A. Nessuna matematica nuova da scrivere. Vincolo UI: si sceglie «rispetto a cosa», non si mostrano tutti in fila |
| D40 | 16 Set 2026 | **`annualized_sortino` NON è un doppione di `SemiDeviation`** e resta nostro | Noi misuriamo gli scarti sotto il **MAR** dividendo per `T`; riskfolio sotto la **media campionaria** dividendo per `T−1`. Verificato: 1,66294 contro 1,57093. Il Sortino è *definito* contro un MAR, quindi il nostro è corretto per il suo scopo → **guardia obbligatoria: ogni sostituzione va provata numericamente prima** |
| D44 | 16 Set 2026 | **Ciò che la libreria non ha si riscrive in NumPy/SciPy — non resta in `math` puro** (M6) | Corregge l'assunzione implicita di D36 caso B: «Riskfolio non ce l'ha» diceva solo che il fornitore è un altro, non che si tiene un ciclo interpretato. Nove funzioni — `summarize_drawdown`, `drawdown_episodes`, `pairwise_correlation`, `comparison_summary`, `wealth_index`, `period_returns_from_cumulative`, `horizon_compounded_returns`, `current_buy_and_hold_returns`, `annualized_sortino` — passano a NumPy a firma e semantica invariate, sotto oracolo M4. Restano nostre: ci appartiene la composizione, non l'aritmetica |
| D46 | 16 Set 2026 | **Si rilascia solo a catena completa, dal worktree separato** — chiude Q4 | Niente stati intermedi su `dev_release2`: il lavoro resta isolato finché non è pronto. Il banner beta si toglie **in un colpo solo** a fine catena, con la regola di Q4 (via da L1/L2/L3, resta sul solo gradino «simulazione» di L4). Il CHANGELOG si scrive una volta sola, e lì dentro va la nota su M2, che **cambia il CVaR già mostrato agli utenti** |
| D47 | 16 Set 2026 | **Asset Detail si riapre a fine catena, non si cancella** | Conferma e data D8, che lo parcheggiava senza dire quando. Si torna a parlarne **dopo** che sistema e idee saranno chiari — quando i quattro livelli, le rappresentazioni e la migrazione saranno in piedi, così la pagina eredita una grammatica già decisa invece di inventarsene una propria. Le sue due lacune note restano registrate: non può mostrare il contributo al rischio del proprio portafoglio (`00` §riga 145) e la card rolling mostra un solo valore puntuale invece della forma nel tempo (`00` §riga 149) |
| D41 | 16 Set 2026 | **`BrinsonAttribution` e `Factors_Risk_Contribution` restano fuori** | La prima scompone il rendimento in effetto allocazione ed effetto selezione: è la risposta più completa a L3, ma pretende un benchmark **con i suoi pesi per classe** → bloccata dietro Q1 e priva di tassonomia. La seconda richiede una matrice di fattori esterni, che senza provider dati non esiste |
| D42 | 16 Set 2026 | **Le misure entropiche e di Gini non entrano** | `EDaR`, `RLDaR`, `RLVaR`, `Entropic_RM`, `L_Moment_CRM`, `TG`, `TGRG`, `GMD` e la famiglia range. Invocano un solutore — 26,9 ms misurati su EDaR — e richiedono di spiegare l'entropia a chi voleva sapere quanto può perdere. Esistono per gli ottimizzatori, non per le persone. Nota: `EVRG`, `RVRG` e `VRG` portano **docstring copiate** da `CVRG`, quindi la loro documentazione non è affidabile |

---

## 2. Rinvii registrati in `TODO_FUTURI.md`

| Voce | Priorità | Precondizione dichiarata |
|---|---|---|
| Tracking Error / Information Ratio con benchmark selezionabile | 🔽 bassa | Benchmark persistente **e** una ragione semantica, non solo tecnica |
| Portfolio optimization / frontiera efficiente (Riskfolio) | 🔽 molto bassa | Provider dati esteso, semantica non prescrittiva, esclusione del max-Sharpe |
| Monte Carlo avanzato: Markov calibrato e volatilità stocastica | 🔽 bassa | Storia lunga e verificata (liv. 4); fonte dati di opzioni (liv. 5) |
| Stimatori robusti di covarianza (Ledoit-Wolf, Gerber, denoising) | 🔽 bassa | Direzione della pagina correlazioni decisa; M3 completata separatamente |
| Catalogo scenari dinamico, proxy persistenti, RQMC | — | Preesistenti alla ripianificazione, invariati |

---

## 3. Questioni aperte

### Q1 — Dove vive il benchmark persistente 🔵 aperta

Decisione D13 presa; l'implementazione no.

**Casa naturale individuata**: `UserSettings` (`backend/app/db/models.py:330`), tabella
per-utente con colonne tipizzate (`base_currency`, `language`, `theme`, `avatar_url`).
Un benchmark è esattamente della stessa natura di `base_currency`: **l'unità di misura
personale dell'utente**.

Ipotesi di lavoro:

```python
risk_benchmark_asset_id: Optional[int] = Field(
    default=None, foreign_key="assets.id", nullable=True
)
```

Richiede una **migrazione Alembic incrementale** (nessuna modifica a `001_initial.py`:
lo schema è già rilasciato).

Sotto-questioni da chiudere:

1. **Ambito**: uno solo per utente, oppure uno per scope (portafoglio / broker)?
   *Orientamento*: **uno solo**. Un benchmark diverso per pagina distruggerebbe la
   confrontabilità Dashboard ↔ Broker Detail stabilita in D10.
2. **Override temporaneo**: si può cambiare benchmark al volo senza salvarlo?
3. **Vincoli di ammissibilità**: storia sovrapposta minima, valuta, avviso quando il
   benchmark non copre il periodo selezionato.
4. **Default**: nessuno (L3 parziale finché non si sceglie) oppure proposta automatica?
5. **Visibilità**: che succede se l'asset scelto come benchmark viene cancellato o perde
   la condivisione?

### Q2 — Rimozione delle dipendenze di ottimizzazione 🟢 chiusa → D23

Con D6, Riskfolio-Lib, CVXPY, CLARABEL e SCS restano nell'immagine senza essere
raggiungibili dal prodotto. La domanda era se valesse la pena rimuoverle.

**Misurato** (vedi [`06`](./06-matematica-librerie-e-reimplementazioni.md) §5):
Riskfolio pesa **2,5 MB**, l'intera closure di solver circa **16 MB su 2 780** —
lo 0,6%. I pesi veri sono `scipy` 96,6 MB, `pandas` 66,8 MB, `QuantLib` 59,6 MB.

**Chiusa in negativo: Riskfolio resta.** Rimuoverla non risolverebbe il problema
dell'immagine, e D25 le assegna un ruolo nuovo — oracolo di test — che la rende
utile anche senza `portfolio_optimization` attiva.

La premessa della domanda era sbagliata, e solo la misura poteva dirlo.

### Q3 — Colonne di rischio nelle tabelle di Asset Global 🔵 aperta

Ipotesi ad alto rapporto valore/costo (vedi documento 03 §4): volatilità annua, max
drawdown e correlazione media come colonne delle tre tabelle esistenti, sfruttando la
sincronizzazione già presente. Da valutare nel blocco UI/UX.

### Q4 — Destino del banner beta 🟢 chiusa → D46

Orientamento coerente con la tesi: il banner si rimuove dai livelli fondati su fatti
osservati (L1, L2, L3) e **resta solo su L4**, dove è vero — e anche lì, solo sul
gradino «simulazione», non su replay e shock che sono deterministici.

**Chiusa dal developer**: si lavora in un worktree separato e **si rilascia solo a
catena completa**, non a stati intermedi. Il banner si toglie a quel punto, in un
colpo solo, secondo la regola qui sopra. Nessuna decisione intermedia da prendere: il
`dev_release2` non vede nulla finché il lavoro non è pronto.

Conseguenza operativa: la domanda 6 dell'elenco «mai discusso» (cosa si rilascia nel
frattempo) è risolta, e il CHANGELOG si scrive una volta sola a fine catena.

### Q5 — Documentazione utente 🔵 aperta

D4 prevede un link alla documentazione **per riga** della scala L1. Le pagine
`mkdocs_src/docs/financial-theory/technical-analysis/risk-metrics/` esistono già per
volatilità, Sharpe, Sortino e max drawdown, ma **non** per CVaR/VaR, correlazione,
contributo al rischio, replay e simulazione.

Da pianificare insieme alla UI: ogni metrica mostrata dovrebbe avere la sua pagina.

### Q6 — Curva normale sovrapposta all'istogramma 🟢 chiusa → D22

D16 adotta l'istogramma della distribuzione dei rendimenti con VaR e CVaR marcati.
Si era considerato di sovrapporre la **gaussiana** con la stessa media e deviazione
standard, per mostrare quanto le code reali siano più grasse di quelle del modello.

**Chiusa in negativo.** Il VaR mostrato è `historical_var`, cioè un quantile empirico:
nessuna assunzione di normalità entra nel calcolo, quindi la campana sarebbe il
confronto con un modello che non stiamo usando — risponde a «perché altri strumenti
sbagliano», domanda che su L1 nessuno ha posto.

Peggio, produrrebbe un danno attivo: una campana accanto ai dati suggerisce che la
campana sia il comportamento *atteso* e lo scarto un'anomalia. È rovesciato — per i
rendimenti finanziari le code grasse **sono** la norma.

La lezione resta valida e va nella pagina wiki sul VaR (Q5). L'unico punto dove si
guadagnerebbe il posto è **L4**: lì un modello lo stiamo davvero scegliendo, e mostrare
cosa assume il GBM contro cosa produce il bootstrap è decision-relevant.

---

## 4. Prossimo blocco

Il blocco UI/UX è stato svolto ed è confluito in
[`05-grammatica-visiva-e-rappresentazioni.md`](./05-grammatica-visiva-e-rappresentazioni.md),
che contiene la diagnosi estetica verificata sul codice, il contratto di primitive,
l'anatomia della card e le sei rappresentazioni con il loro costo.

**Prossimo**: il piano esecutivo (`07`), che ordina il lavoro in workstream e ne
definisce i gate. Si scrive dopo aver chiuso Q1 (dove vive il benchmark persistente),
unica questione che blocca L3.

Deve contenere anche le quattro cose finora mai affrontate:

1. **Ordine fra migrazione e UI.** M1 e M3 sono invisibili all'utente ma sbloccano la
   reattività su cui poggia metà di [`05`](./05-grammatica-visiva-e-rappresentazioni.md).
2. **Una taglia.** Oggi non esiste da nessuna parte una stima di quanto sia grande
   questo lavoro. Senza, il piano esecutivo diventa una lista di desideri.
3. **Dove vivono i test dell'oracolo M4** — categoria, lane di runtime, registrazione
   nel catalogo. M4 è la chiave di volta e non ha ancora un indirizzo.
4. **La voce di CHANGELOG per M2**, che cambia un numero già mostrato agli utenti.

Risolte invece da D46 e D47: cosa si rilascia nel frattempo (nulla, si rilascia a
catena completa) e quando si riapre Asset Detail (a fine catena).

### Q7 — Quali misure acquisire dalla famiglia drawdown 🔵 aperta

`riskfolio.src.RiskFunctions` espone **48 callable, di cui 42 sue** — le altre sei
(`Bounds`, `minimize`, `null_space`, `PCA`, `StandardScaler`, `pinv`) sono scipy,
sklearn e numpy che filtrano dagli import. La famiglia drawdown ne occupa quattordici
(sette misure × varianti `Abs`/`Rel`). Non sono migrazioni: sono **acquisizioni**, e
vanno decise per domanda, non per disponibilità.

> **Aggiornamento**: le due candidate più forti non stanno nella famiglia drawdown.
> Sono `NEA` per L2 (D38) e `Sharpe(rm=...)` per L3 (D39), entrambe già decise. Il
> setaccio completo delle 42 sta in §7.3 di `06`; questa Q resta aperta solo per la
> scelta **dentro** la famiglia drawdown.

Il motivo per cui la questione esiste: il massimo drawdown dice *quanto in
profondità*, mai *quanto a lungo*. Misurato su due storie costruite con lo stesso
massimo (§7.1 di `06`):

| Storia (12 mesi, da 100 a 100) | MDD | Mesi sotto | ADD | UCI |
|---|---:|---:|---:|---:|
| A — crolla a 80 e recupera subito | 20,0% | **2** | 2,5% | 6,5% |
| B — scende piano a 80 e risale piano | 20,0% | **10** | 9,7% | 11,7% |

Il MDD dà lo stesso numero. A è una brutta settimana, B è un anno di erosione.

**Candidati, in ordine di rapporto valore/costo:**

1. **UCI — Ulcer Index** (1,76 ms). Media dei quadrati del «quanto sono sotto il
   picco», su **tutti** i giorni, poi radice. Il quadrato pesa la profondità, la
   media su tutti i giorni pesa la durata. È in un numero solo ciò che oggi diciamo
   con due campi separati (`max_drawdown` e `max_duration`). Nato per misurare quanto
   un investimento è stato *fastidioso da tenere* — letteralmente la domanda L1.
2. **Risk contribution su misura non-MV** (nessun costo matematico nuovo:
   `Risk_Contribution` accetta già `rm=`, il parametro che sceglie *quale* rischio
   scomporre). Oggi la pagina dice «chi contribuisce alla volatilità»; potrebbe dire
   «chi contribuisce ai miei drawdown» (`rm="CDaR"`) o «alle code» (`rm="CVaR"`).
   **La risposta cambia davvero**: su tre asset a volatilità identica, il maggiore
   imputato passa dal 38,3% (code) al 20,7% (fastidio) — da primo a ultimo. ⚠️ **Blocco noto**: i contributi non-MV possono essere
   **negativi** — corretto (un asset può ridurre il rischio di coda) ma incompatibile
   con la UI attuale, che li tratta come quote di una torta. Va deciso prima.
3. **CDaR 95%** (1,02 ms). Sta a DaR come CVaR sta a VaR. Coerente con le scelte già
   fatte su L1, ma è la terza misura di coda dopo VaR e CVaR: rischia di affollare.
4. **ADD** (1,49 ms). Onesto, ma l'UCI dice la stessa cosa meglio.

**Escluse**: `EDaR`/`RLDaR` — 26,9 ms perché invocano un solutore, e la loro lettura
richiede di spiegare l'entropia. `MDD_Abs` — vedi D37.

**Gate**: nessuna acquisizione prima che la mappa dei livelli (`03`) abbia assegnato
una casa a ciascuna. Una metrica in più senza una domanda in più è esattamente
l'errore che questa ripianificazione esiste per non ripetere.
