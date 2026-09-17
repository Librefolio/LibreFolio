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
| D48 | 17 Set 2026 | **Il benchmark è un catalogo condiviso, non una scelta singola** — riformula Q1 | Il confronto è plurimo: misurare un portafoglio azionario contro un obbligazionario dà un numero corretto e privo di significato. Quindi una casella sull'asset lo qualifica come riferimento predefinito, **condivisa fra tutti gli utenti** — coerente per costruzione, dato che `Asset` (`models.py:464`) **non ha `user_id`**: è già globale. Restano selezionabili tutti gli asset; i riferimenti stanno in cima |
| D49 | 17 Set 2026 | **Il flag è ortogonale ad `AssetType.INDEX`, non lo riusa** | `INDEX` esiste già e il suo docstring dice «Market indices and benchmarks… no transactions allowed», ma è usato in **un solo punto** del backend (`transaction_batch_stages.py:502`) e solo per vietare le transazioni. Riusarlo romperebbe il caso principale: un ETF S&P 500 è un ottimo benchmark **e** un asset che si possiede davvero. Da valutare la regola `è_benchmark = flag OR asset_type == INDEX`, dato che un `INDEX` esiste solo per il confronto |
| D50 | 17 Set 2026 | **Un solo selettore serve quattro punti** | `SignalAssetParamControl` (64 righe) è raggiunto da `ChartSignalsSection`, presente sia in `/assets/[id]` sia in `/fx/[pair]`, ed è **già usato** da `RiskAnalysisPanel` alle righe 891 (asset di confronto) e 1091 (proxy di replay). L'ordinamento è oggi alfabetico puro (riga 31). E `SelectOption.header` esiste già, con la semantica giusta: sparisce quando la ricerca svuota la sua sezione. Mettere i benchmark in cima è un `sort` più due intestazioni, **non** un componente nuovo |
| D41 | 16 Set 2026 | **`BrinsonAttribution` e `Factors_Risk_Contribution` restano fuori** | La prima scompone il rendimento in effetto allocazione ed effetto selezione: è la risposta più completa a L3, ma pretende un benchmark **con i suoi pesi per classe** → bloccata dietro Q1 e priva di tassonomia. La seconda richiede una matrice di fattori esterni, che senza provider dati non esiste |
| D42 | 16 Set 2026 | **Le misure entropiche e di Gini non entrano** | `EDaR`, `RLDaR`, `RLVaR`, `Entropic_RM`, `L_Moment_CRM`, `TG`, `TGRG`, `GMD` e la famiglia range. Invocano un solutore — 26,9 ms misurati su EDaR — e richiedono di spiegare l'entropia a chi voleva sapere quanto può perdere. Esistono per gli ottimizzatori, non per le persone. Nota: `EVRG`, `RVRG` e `VRG` portano **docstring copiate** da `CVRG`, quindi la loro documentazione non è affidabile |
| D51 | 17 Set 2026 | **`asset_type` è quasi inerte: il docstring su `valuation_model` mente** | `grep` su tutto `backend/app` trova `valuation_model` **solo** in `models.py:162`, dentro il docstring di `AssetType`. Zero codice: la mappatura dichiarata (CROWDFUND→SCHEDULED_YIELD, HOLD→MANUAL, INDEX→MARKET_PRICE) non esiste. Verificato branch per branch, `asset_type` fa filtro nelle query (`crud.py:180-181`), raggruppamento ed esposizione, etichetta, AI export — e **una sola regola di comportamento**: `INDEX` vieta le transazioni (`transaction_batch_stages.py:501-502`). Conseguenza: aggiungere sottotipi **non cambia alcun comportamento**. Il docstring va corretto nella stessa migrazione |
| D52 | 17 Set 2026 | **I sottotipi ETF entrano in `AssetType`** — revoca la proposta di colonna ortogonale | Avevo proposto una colonna `asset_class` separata con tre argomenti, tutti caduti. (1) «I provider non sanno riempirla» — `justetf.py:614` scrive `AssetType.ETF` fisso e `borsa_italiana.py` mappa segmenti di mercato: vero, ma irrilevante, perché il generico resta un valore legittimo e la specializzazione è un gesto dell'utente; nel selettore benchmark si sceglie comunque fra tutti gli asset, quindi il tipo serve a **trovare**, non a vincolare. (2) «`asset_type` pilota comportamenti» — falso, vedi D51. (3) «L'icona vuole due strati» — si risolve con una seconda costante accanto a `PNG_MAP` in `assetTypes.ts`: icona grande dal contenitore, **pastiglia piccola sovrapposta** dalla classe, lo stesso schema che l'altro worktree applica a broker + asset nel tool pacchetti. Si estendono **solo i tipi dove la distinzione ha senso**; `ETF` generico resta come residuo |
| D53 | 17 Set 2026 | **`AssetType.INDEX` implica benchmark, in automatico e in sola lettura** | Precisa la riserva lasciata da D49: non `flag OR asset_type == INDEX` ricalcolato a ogni lettura, ma flag **materializzato**. Nella migrazione Alembic, ogni asset già `INDEX` riceve il flag a `true` (backfill). A regime, creando un asset `INDEX` il flag si accende da solo ed è **readonly**: un indice esiste solo per il confronto, non lo si possiede |
| D54 | 17 Set 2026 | **Le colonne di rischio entrano nascoste e attivabili** — chiude Q3 | Tutti i segnali utili diventano colonne di Asset Global, **nascoste per default**; visibile di default solo il **max drawdown**, facile da capire e ad alto impatto. Non serve alcun meccanismo nuovo: `DataTable` ha già `hiddenByDefault` per colonna e persiste in localStorage **solo gli override espliciti** (`DataTable.svelte:193-196`), così un default che cambia resta vivo e un valore vecchio non può congelare una colonna che dovrebbe vedersi. Si rivedrà insieme ad Asset Detail (D47) |
| D55 | 17 Set 2026 | **La documentazione nasce come scheletro inglese e si traduce in fondo** — chiude Q5 | All'inizio dello sviluppo si crea **una pagina mock di due righe, solo in inglese**, per ogni voce che servirà, registrata subito nell'indice di `mkdocs_src/mkdocs.yml` secondo le regole già fissate nelle skill. Mentre gli agenti di sviluppo lavorano, un agente di documentazione riempie le pagine **in inglese**. Le traduzioni si fanno **in un blocco solo a fine documentazione**, non pagina per pagina |
| D56 | 17 Set 2026 | **Dalla famiglia drawdown entrano quattro misure** — chiude Q7 | `MDD`, `DaR`, `CDaR`, `UCI`, nella variante **`_Rel`**. Semantica verificata sul sorgente e ricostruita a mano: `_Abs` usa `cumsum` e misura in punti di rendimento cumulato, `_Rel` usa `cumprod` e misura in **% dal picco** — l'unica che la gente intende (`MDD_Abs` lib 0,227822 = mano 0,227822; `MDD_Rel` lib 0,212860 = mano 0,212860). Costano 1,6-3,0 ms. Fuori: `ADD` per scelta del developer; `EDaR` e `RLDaR` **confermando D42**, con una prova in più — `EDaR` restituisce una tupla e invoca un solutore (27 ms), `RLDaR` costa 89-166 ms e su un seme ha prodotto `RLDaR_Rel = 0,000000` esatto, su un altro 0,1939. Un solutore che degenera in silenzio è peggio di una misura assente |
| D57 | 17 Set 2026 | **Il contributo al rischio è automatico: l'utente non seleziona nulla** | `RiskContributionParams` è vuoto — `extra="forbid"`, nessun campo. Scope solo `PORTFOLIO`, modo solo `CURRENT_COMPOSITION`. Legge `context.scope_asset_ids` e `context.weights`: prende la composizione corrente con i pesi reali in valuta di destinazione. È questa proprietà — il plugin riceve la lista **già risolta**, non il filtro — a rendere quasi gratuito D58 |
| D58 | 17 Set 2026 | **Il portafoglio si affetta per asset, non solo per broker** | Oggi `PortfolioRiskScope` filtra **solo** per `broker_ids`: per *dove* si tiene una cosa, non per *cosa* è. E `AssetSetRiskScope` non è la risposta — significa «questi N asset affiancati», senza pesi, ed è accettato da **tre plugin su nove** (`correlation`, `portfolio_optimization`, `stress`); tutto L1 (VaR, CVaR, drawdown) e L3 (KPI, confronto) accetta solo `asset` o `portfolio`, e `risk_contribution` **solo** `portfolio`. Si aggiunge quindi un filtro per asset **su `PortfolioRiskScope`**: resta uno scope `portfolio`, tutti e nove i plugin lo accettano senza modifiche e la fetta si propaga da sola (D57). Motivo: è il gemello di D48 — se confrontare un 60/40 con un indice azionario è sbagliato, lo è per due ragioni simmetriche, il riferimento sbagliato **e** la fetta sbagliata; sceglierne bene uno solo risolve metà del disallineamento |
| D59 | 17 Set 2026 | **Affettando, i pesi si rinormalizzano al 100% della fetta** — chiude Q8 | La fetta esiste per essere confrontata con il riferimento giusto (D48), quindi va guardata come se fosse tutto il portafoglio. Coi pesi reali una fetta al 60% risulterebbe **sempre** meno rischiosa del suo indice, e il confronto — cioè l'intero motivo per cui D58 esiste — si romperebbe in silenzio. Conseguenza: i contributi al rischio della fetta sommano al 100% della fetta. Va **dichiarato nella UI**, non lasciato intuire: la domanda a cui la vista risponde è «com'è fatta la mia parte azionaria», non «quanto pesa sul totale» — per quella c'è già il contributo al rischio sull'intero portafoglio |
| D60 | 17 Set 2026 | **Il flag benchmark è condiviso per scelta, non per compromesso** — chiude Q1(b) | Chiunque lo accenda cambia la lista a tutti, ed è il comportamento voluto: non ha senso che lo stesso ETF sia un buon riferimento per un utente e no per un altro. È coerente col resto del modello — `Asset` non ha `user_id` (`models.py:464`) e un asset marcato benchmark, **purché non sia `INDEX`**, resta assegnabile alle transazioni come qualunque altro, cosa a sua volta globale. Nessun permesso speciale, nessuna riserva all'amministratore |
| D61 | 17 Set 2026 | **Il secondo livello non è una tassonomia nuova: è l'insieme dei tipi base** | Riformula D52 in modo più stretto. La specializzazione di un ETF è «**quale tipo base contiene**»: azionario, obbligazionario, materie prime, immobiliare, monetario, cripto. Non serve un elenco parallelo, e ne discende la regola meccanica dell'icona: **pastiglia = icona del tipo base**, nessuna serie nuova da disegnare. Conseguenze: (1) *bilanciato/multi-asset* non è un sottotipo, è l'`ETF` generico — che resta come residuo e come valore che i provider scrivono; (2) `FUND` **non** si suddivide: gli ETF sono già fondi, passivi, e la distinzione utile è quella sul contenuto; (3) servono due **tipi base nuovi**, `COMMODITY` e `REAL_ESTATE`, che oggi mancano del tutto; (4) *monetario* si sovrappone a liquidità — e `LIQUIDITY` è già mezzo costruito: **non è nell'enum del backend**, ma esiste in `PNG_MAP` (`assetTypes.ts:30`), come `liquidity.png`, nelle quattro lingue (riga 143 di `en/it/fr/es.json`) e come emoji `💰` in `AllocationHistoryChart.svelte:129`. Orfano innocuo, perché `ASSET_TYPES` deriva dallo schema Zod e quindi non compare nel menù — ma icona ed etichette sono pronte. Da disegnare solo `commodity` e `real-estate` |
| D62 | 17 Set 2026 | **Il selettore a due livelli esiste già: `SignalTreeSelect`** | 359 righe in `components/charts/`. Interfaccia `groups: SignalTreeGroup[]`, ogni gruppo con `items: SignalTreeItem[]` — **esattamente due livelli**, espandibili, con ricerca che attraversa entrambi e navigazione da tastiera. Vince sulle altre due ipotesi: un secondo selettore che appare dopo ETF costa poco ma richiede due gesti; un pulsante che apre una modale anniderebbe una modale dentro `AssetModal` (2427 righe). Costo del riuso, da non nascondere: va **generalizzato** — spostato in `components/ui/select/`, privato del nome «Signal», col contenuto dell'opzione passato come snippet invece che via `SignalOptionContent`. E `SignalTreeItem` ha un solo campo `icon`: per la pastiglia serve un secondo slot |
| D63 | 17 Set 2026 | **`LIQUIDITY` NON entra in `AssetType`** — revoca l'indicazione data in D61 | D61 diceva «il monetario è già mezzo costruito, icona ed etichette pronte». **Falso**: non è un tipo a metà, è un **secchio sintetico**. `portfolio_engine.py:1039-1041` inietta la cassa nell'allocazione come pseudo-tipo (`by_type["Liquidity"] = … + cumulative_cash + it_cash`), quindi le voci in `PNG_MAP`, nelle quattro lingue e in `AllocationHistoryChart` servono a disegnare *quel* secchio, non un tipo di asset. Aggiungerlo all'enum creerebbe un doppione visibile: gli asset veri finiscono in `by_type` con `asset_type.value`, cioè **maiuscolo** (`:1448`, alimentato da `:2155`), la cassa entra come `"Liquidity"` — due chiavi distinte per la stessa cosa, due fette nel grafico, e con la **stessa icona** perché `getAssetTypeIconUrl` normalizza in maiuscolo. Sembrerebbe un bug, e lo sarebbe. Resta aperto come rappresentare il monetario → **Q10** |
| D64 | 17 Set 2026 | **La scelta del benchmark vive solo nella cache locale del client** — chiude Q1(c) | Nessuna colonna su `UserSettings`: la preferenza sta in `localStorage`, coerente con la scelta architetturale già in uso per i toggle vista-doppia. Se non c'è nulla in cache, la zona **non mostra numeri vuoti**: mostra un testo che spiega cosa scegliere o aggiungere. Regola implementativa che ne discende: se l'asset in cache viene **cancellato o privato del flag**, la zona deve degradare allo stesso stato vuoto, non andare in errore — la cache locale non può assumere che il server sia rimasto d'accordo con lei. Conseguenza sul confronto: il benchmark viaggia nella richiesta a ogni chiamata, quindi il backend resta senza stato e non serve persistenza lato server |
| D65 | 17 Set 2026 | **I suggerimenti sono testi fissi tradotti, non un catalogo risolvibile** — chiude Q1(d) | Cade l'ipotesi della lista curata (YAML o costante con identificatori) risolta dai provider: niente chiamate ai provider, niente file di ISIN da mantenere. Restano **banner e testi tradotti nelle quattro lingue**, mostrati quando la zona è vuota, che spiegano quali riferimenti ha senso aggiungere; l'utente li aggiunge a mano col flusso di creazione asset già esistente. Resta da decidere quanto siano specifici → **Q11** |
| D66 | 17 Set 2026 | **La conversione valutaria del benchmark è obbligatoria** — chiude Q1(e) | Se il benchmark è in USD e la valuta base è EUR, il beta misura **anche il cambio**. Si converte con il sistema FX che esiste già: non è una funzione nuova, è l'uso di una che c'è. Senza, il numero è contaminato in silenzio — la stessa classe di errore del CVaR distorto (D28), dove il risultato era plausibile e sbagliato |
| D67 | 17 Set 2026 | **Il monetario è solo un sottotipo di ETF, non un tipo base** — chiude Q10 | Scartata la strada A (nuovo tipo base `MONETARY`): esiste `ETF_MONETARY` ma **non** un `MONETARY` di primo livello. Conseguenza da dichiarare, perché **incrina la regola di D61**: il secondo livello non è più *esattamente* l'insieme dei tipi base, è l'insieme dei tipi base **più il monetario**, che base non ha. La regola resta valida per tutti gli altri sottotipi, e l'eccezione è motivata: un fondo monetario è uno strumento che si compra — prezzo, emittente, rischio piccolo ma non nullo — mentre la cassa (D63) è il saldo di un conto. Non essendo un investimento tenuto da solo con quel tipo, non gli serve una casa al primo livello. Per la pastiglia si riusa **`liquidity.png`**, che esiste già, significa denaro e — appropriatamente — **non** è un tipo base |
| D68 | 17 Set 2026 | **I testi di suggerimento nominano indici, mai prodotti** — chiude Q11 | «Un ETF sull'S&P 500», «uno sull'EuroStoxx 600», «un obbligazionario globale»: nomi di indici e categorie, **nessun ISIN, nessun ticker**. Due ragioni. Un ISIN in una stringa tradotta è di fatto un consiglio d'acquisto, e sposta LibreFolio da strumento di misura a strumento di consiglio. E quando quel prodotto viene delistato o sostituito, l'errore è in quattro lingue contemporaneamente: un indice è un fatto pubblico e stabile, un prodotto è la scelta di un emittente |
| D73 | 17 Set 2026 | **I selettori ad hoc mostrano l'id invece del nome: si riusa `AssetSelect`** | Segnalato dal developer sul segnale **beta**, dove il menù elenca «9 / Amundi Core MSCI World UCI…» — id in cima, nome come sottotitolo. La causa **non** è nel controllo del segnale, che passa già `label: asset.display_name`: è il **rendering di default** di `SearchSelect` (`:496-497`), che stampa `option.value` in **`font-mono`** come riga principale e `option.label` come sottotitolo. Quel default è corretto per i selettori dove il valore **è** un codice leggibile — valuta, paese, settore — e il `font-mono` lo dichiara. Diventa un difetto quando il valore è una **chiave primaria di database**. Verificato chi lo sa e chi no: **tutti** i selettori dedicati in `ui/select/` sovrascrivono il default con gli snippet `item` e `selectedItem` — `AssetSelect`, `BrokerSearchSelect`, `UserSearchSelect` — mentre i due costruiti **fuori** da quella cartella cadono nel default: `SignalAssetParamControl.svelte` (segnali) e **`AssetSetRiskPanel.svelte`**, che sbaglia **due volte**, sul broker (`:49`) e sull'asset (`:55`). Non è un caso isolato: è ciò che succede quando si costruisce un picker ad hoc invece di riusare quello che c'è. **Cura: migrare a `AssetSelect`**, che è il picker «decente» già scritto (187 righe: icona, ticker, valuta con bandiera, asset inattivi ordinati in fondo e marcati) e il cui stesso commento d'intestazione invita a farlo — *«Migrate other asset_id pickers to use this when convenient»*. L'esclusione oggi fatta con `excludeAssetIds` si esprime col suo `filter?: (a: AssetInfo) => boolean` |
| D74 | 17 Set 2026 | **Migrando si corregge anche una ricerca che sembrava rotta** | Effetto collaterale della cura di D73, trovato leggendo i due `searchText`. `SignalAssetParamControl` mette **valuta e tipo** fra i termini cercabili; `AssetSelect` li **esclude deliberatamente**, con la ragione scritta nel codice: valuta e tipo sono proprietà condivise da centinaia di righe, quindi una query che è prefisso di una di esse — `eur`, `bon`, `etf` — **restituiva l'intero elenco**, e la ricerca sembrava cominciare a funzionare solo dalla quarta lettera. *«Un identificatore nomina uno strumento; una valuta lo descrive.»* Il picker dei segnali ha oggi quel difetto e nessuno l'aveva collegato alla sensazione di ricerca inutile |
| D75 | 17 Set 2026 | **Nasce il mandato N: le acquisizioni decise non avevano un proprietario** | Trovato verificando i dieci mandati contro il registro. **D38** (NEA e diversification ratio, KPI di L2), **D45** (`WR`, KPI di L1) e **D56** (MDD, DaR, CDaR, UCI in variante `_Rel`) erano **decise e assegnate a nessuno**: il mandato A le espelle esplicitamente nella sezione *Fuori* — «qualunque acquisizione … sono funzionalità nuove, non migrazione» — mentre il mandato E costruisce L1 e L2 **assumendo che quei campi arrivino nel payload**. Verificato con `grep` su tutto `backend/app`: `diversification` **zero occorrenze in tutto il backend**, `worst_realization`/`worst_day`/`worst_return` **zero** in `risk/`, `risk_plugins/` e `schemas/risk.py`, `herfindahl` presente **solo dentro AI Export**. Senza questo mandato E avrebbe scoperto a metà lavoro che tre dei KPI da disegnare non esistono, e A sarebbe già stato chiuso. **D39 (`Sharpe(rm=…)`) resta ad A**: pretende la matrice dei rendimenti, cioè esattamente l'idraulica mancante di M5 — chi fa M5 ha già pagato metà del lavoro, duplicarla sarebbe farla due volte. Lane `6248`, taglia M, nessuna dipendenza in ingresso |
| D76 | 17 Set 2026 | **Riskfolio restituisce magnitudini positive, il nostro schema usa negativi** | Misurato su 750 rendimenti: `WR` = **+0,03851726** mentre `min(r)` = **−0,03851726**; `MDD_Rel` +0,5499, `DaR_Rel` +0,5208, `CDaR_Rel` +0,5308, `UCI_Rel` +0,3490 — tutte positive. Ma `RiskKpiOutput.max_drawdown` è dichiarato `Field(..., le=0)` (`schemas/risk.py:644`): **deve essere negativo o zero**. Passare una funzione direttamente al campo fa fallire la validazione, ed è il caso **fortunato**. Il caso sfortunato: qualcuno «risolve» invertendo il vincolo su **un campo solo**, e dentro lo stesso oggetto convivono due convenzioni di segno opposte — la UI le disegna una sotto l'altra e **nessun test se ne accorge**, perché ogni campo è internamente coerente. È la stessa classe di difetto del CVaR (D28): una grandezza plausibile e sbagliata. Regola: **una convenzione per output**, dichiarata nel contratto K8, con un test che la afferma per **ogni** campo nuovo |
| D77 | 17 Set 2026 | **NEA deve coincidere con l'Herfindahl di AI Export: non è una cortesia, è un vincolo** | AI Export calcola già la concentrazione in `ai_export/components/portfolio_financial.py:208`, con semantica dichiarata nel campo: *«Sum of squared nav_weight_percent across all positions. 10000 is fully concentrated in one position»* e *«Cash is included in the denominator but is not itself an HHI term»*. L'identità è **esatta e verificata numericamente** su `w = [0,5 · 0,3 · 0,15 · 0,05]`: `NEA(w)` = `1/Σwᵢ²` = `10000/HHI_points` = **2,73972602739726** per tre vie, con HHI = 3 650. Non c'è quindi alcuna libertà di definizione: sono la stessa grandezza in due unità. Ma **una scelta semantica vera resta**, e va presa esplicitamente: la cassa entra o no nel denominatore? Se il rischio sceglie diversamente da AI Export, **la stessa applicazione dice due numeri diversi sulla concentrazione dello stesso portafoglio** e l'utente non ha modo di sapere quale credere. Si adotta la convenzione di AI Export, o si diverge con una ragione scritta e una nota in documentazione |
| D78 | 17 Set 2026 | **Il file di mandato è un brief in sola lettura; il piano vivo sta in `progress/`** | Difetto trovato rileggendo `implementation/README.md` §5.5, che diceva «ogni mandato apre il proprio file di piano in `implementation/`» — ma **i mandati stanno già lì con quei nomi**. Un agente che avesse seguito l'istruzione alla lettera avrebbe aperto il proprio brief e cominciato a spuntarci sopra i passi, **distruggendo l'unica copia delle proprie istruzioni**, e se ne sarebbe accorto solo dopo un azzeramento di contesto — cioè nel momento peggiore. Cura: il brief non si modifica (se deve cambiare, lo cambia il coordinatore e lo comunica); il piano vivo è un file **nuovo**, `implementation/progress/<LETTERA>-esecuzione.md`, aggiornato dopo ogni passo con `Note implementazione` e `Fuori pista` |
| D79 | 17 Set 2026 | **I contratti si materializzano in `contracts/`, di proprietà del coordinatore** | I mandati girano in **worktree separati**: un file scritto da A nel suo worktree **non è visibile a E**, e finché non c'è un commit integrato non condividono nemmeno la storia. Quindi un contratto non può essere consegnato «mettendolo in un file» — e se resta solo dentro un messaggio fra sessioni **sparisce al primo azzeramento di contesto**, esattamente quando serve. Regola: il produttore **comunica**, il coordinatore **scrive** nel proprio worktree, il consumatore **riceve**. Un file per contratto, `K1.md`…`K8.md`. Effetto secondario e altrettanto utile: un contratto **cambiato** diventa un diff invece che un ricordo contraddittorio |
| D80 | 17 Set 2026 | **Tre fatti misurati sul bootstrap di un worktree, e uno che costa 3,8 GB** | (1) **I data dir sono già isolati per worktree**: `get_project_root()` è `Path(__file__).parent.parent`, cioè relativo al file, quindi ogni worktree risolve il proprio `backend/data/…`. **La porta è l'unica risorsa davvero globale**, e le lane servono per quella. (2) **`.env` non serve**: nessuno dei cinque worktree attivi ne ha uno, solo il checkout principale — quindi la sua assenza è corretta e non va mai colmata copiandolo da un altro checkout. (3) **Le lane non toccano la produzione**: `DEFAULT_PROD_DATA_DIR` è `backend/data/prod`, **non** `backend/data`, quindi `backend/data/test-risk-*` non si sovrappone e la guardia passa. (4) Il costo vero è **`node_modules`**: **636 MB** misurati, in `.gitignore`, assente in un worktree nuovo. I sei mandati frontend (B, D, E, F, G, J) non possono chiudere la propria definizione di finito senza, e il contratto vieta ai figli di installare dipendenze: lo installa il **coordinatore**, `npm ci` dal lock, uno per volta. Sei worktree frontend sono ~**3,8 GB** su un disco misurato al **90%** con 42 GiB liberi — sostenibile, ma da verificare prima dell'ondata 2 |
| D81 | 17 Set 2026 | **Anche gli spec di test hanno proprietari, e `risk-analysis.spec.ts` va diviso da D** | Secondo buco trovato nella verifica: la mappa di proprietà copriva i file **sorgente** e non quelli di **test**. `e2e/portfolio/risk-analysis.spec.ts` conta **817 righe in un solo `test.describe`**, e i suoi sei test appartengono a tre padroni: tre sono di **E** (dashboard `:587`, unavailable `:619`, broker tab `:687`), uno è di **F** (asset global `:628`), e **due coprono Asset Detail** (`:698`, `:719`) che è parcheggiato per D8 e D47. Sopra, ~580 righe di impalcatura condivisa (`installRiskMocks`, `resultFor`, `definition`, `openDashboardRisk`, `brokerWithHoldings`). Senza divisione E ed F riscrivono lo stesso file nello stesso momento e lo scoprono a lavoro fatto. **Lo divide D**, perché è l'unico mandato che gira prima di entrambi ed esiste proprio per preparare loro il terreno: `risk-mocks.ts` (impalcatura, di E, consumata da F), `risk-analysis.spec.ts` (E), `risk-lab.spec.ts` (F), `risk-asset-detail.spec.ts` (**di nessuno**). Vincolo: solo spostamento, stesso numero di test prima e dopo, nessuna asserzione cambiata. Gli altri due spec contesi restano da coordinare senza divisione: `dashboard.spec.ts` (210 righe, G ed E) e `asset-list.spec.ts` (692 righe, B ed F) |
| D82 | 17 Set 2026 | **I due test su Asset Detail non sono un residuo: sono la rete** | Corollario di D81, e va scritto perché l'istinto opposto è fortissimo. Asset Detail resta fuori ambito (**D8**, **D47**) e deve restare **identico**: quei due test sono l'unica cosa che lo **dimostrerà** quando E ed F avranno finito. Vanno isolati in un file proprio perché nessuno sia tentato di «adattarli per farli passare» — adattarli cancellerebbe esattamente la prova che si sta cercando. Verifica in J: `git log` su quel file mostra **solo** lo spostamento fatto da D |
| D83 | 17 Set 2026 | **`resultFor` codifica la forma del payload: K1 e K8 lo rendono stantio** | Terza scoperta della verifica, e la più insidiosa perché non produce alcun rosso. L'impalcatura di `risk-analysis.spec.ts` (`:210-463`) costruisce le risposte finte del backend, cioè **congela la forma del payload**. Quando A consegna K1 (serie underwater, bin dell'istogramma) e N consegna K8 (WR, famiglia drawdown, NEA, diversification ratio), quel mock va aggiornato — altrimenti i test **passano** servendo una forma che il backend non produce più. **Un mock stantio non fallisce: rassicura.** È la stessa famiglia del CVaR rimasto sbagliato per un anno (D28) e dell'`undefined_windows` che può sparire senza rossi: un sistema che sembra coperto e non lo è. Clausola aggiunta ai contratti K1 e K8 |
| D84 | 17 Set 2026 | **G invalida gli screenshot della galleria, che non possiede: li rigenera J** | Dipendenza invisibile, non un conflitto — nessuno scrive lo stesso file. `e2e/gallery.spec.ts:605` genera *«dashboard allocation charts — all languages and themes»*, cioè le immagini della documentazione. Il mandato **G** cambia i colori di quei due grafici, quindi le immagini mostrano una tavolozza che il prodotto non usa più. G **non** deve rigenerarle: fotograferebbe uno stato intermedio, prima che gli altri mandati frontend siano integrati. Le rigenera **J**, dopo l'integrazione, e G si limita a **dichiararlo** nel checkpoint |
| D72 | 17 Set 2026 | **Se un anello solo non basta, si annida: ciambella a due anelli. Scartata la barra polare** | Ripiego registrato per D71. (1) **Anello annidato** — due serie `pie` sullo stesso centro con bande di raggio diverse, idioma nativo di ECharts. Costa poco perché **il grafico è già una ciambella** (`radius: ['35%', '70%']`, riga 274): c'è già il buco in cui infilare il secondo anello. Gli angoli combaciano per costruzione — l'arco di un genitore è la somma dei figli — quindi la lettura «quota sul totale» resta esatta. **Primari all'interno, sottotipi all'esterno**: l'anello esterno ha più lunghezza d'arco per grado, quindi la suddivisione fine va dove c'è spazio, e l'interno resta il riassunto che l'occhio legge per primo. (2) **Barra impilata polare** (`bar-polar-stack`) — grafico legittimo, ma risponde a un'altra domanda: in coordinate polari il valore si mappa sul **raggio**, e l'area cresce con il quadrato, quindi due valori uguali a raggi diversi occupano aree diverse. Per una torta di allocazione, dove tutto il senso è «quanta parte del totale», è una trappola percettiva. È il grafico giusto per confrontare categorie lungo una dimensione ciclica — mesi, ore — non per parti di un tutto |
| D71 | 17 Set 2026 | **I sottotipi si vedono come sfumature dentro la fetta del primario** — chiude il residuo di Q12 | Quarta strada, proposta dal developer: nessuna delle tre che avevo messo in tabella. Il sottotipo **non** diventa una fetta indipendente né sparisce dentro il contenitore: resta dentro la massa del tipo primario, con un **colore lievemente diverso**, e i numeri si leggono distinti nel tooltip. Stessa regola nello storico: le sotto-serie impilate prendono tonalità vicine a quella del genitore. **Un asset non specializzato usa il colore primario puro** — non è un caso da gestire, è il grado zero della scala. Risolve il compromesso che avevo posto (informare contro frammentare) invece di sceglierne un corno: la lettura d'insieme resta sulla massa cromatica, il dettaglio sta nel tooltip per chi lo cerca. Vale sia per `AllocationPieChart` sia per `AllocationHistoryChart` |
| D70 | 17 Set 2026 | **Gli scenari di stress sono un compito, non un vincolo** — declassa Q12 | I due YAML predefiniti (`equity_crash`, `global_risk_off`) sono file nostri: si riscrivono insieme all'enum, e l'adeguamento del sistema di rischio esistente è parte del lavoro, non un ostacolo. Quello che resta di Q12 è la **modalità di fallimento**, non lo scenario: `_resolve_bucket` ritorna `UNCONFIGURED_ZERO` senza avvisare, `getAssetTypeIconUrl` ripiega su `other.png`, l'etichetta mancante mostra la chiave grezza. Tre coperture affidate alla buona volontà e tre ripieghi silenziosi: il piano esecutivo deve chiedere **un test che leghi l'enum alle tre tabelle**, non un aggiornamento manuale. Resta da decidere solo se la **torta di allocazione** si specializza (strade A/B/C di Q12), che è dashboard e non rischio |
| D69 | 17 Set 2026 | **Le due icone mancanti esistono e sono in famiglia** | `commodity.png` (barile + lingotti, oro `#BF9332` contro `#C09030` di famiglia) e `real-estate.png` (casa con tetto a falde + annesso, verde `#54BC7D`), installate in `frontend/static/icons/asset-types/`. Tavolozza e trasparenza dentro i valori misurati sulla serie esistente; dimensioni 271×248 e 296×199, coerenti con `liquidity.png` (275×227) dato che **la serie non è normalizzata** (da 79×79 a 275×227). Restano **non referenziate** finché l'enum non riceve i tipi corrispondenti. Osservazione onesta sulla resa a 20px, dove serviranno da pastiglia: `commodity` regge, `real-estate` è mediocre perché le due masse si fondono — ma è la stessa debolezza di `bond`, e comunque migliore di `etf`, che a quella dimensione diventa rumore illeggibile. Se la pastiglia risulterà confusa, il problema è **di tutta la serie**, non di questi due file |

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

### Q1 — Il catalogo dei benchmark 🟢 chiusa → D48-D50, D53, D60, D64-D66

**La riformulazione viene dal developer, ed è migliore della domanda originale.**

La versione precedente chiedeva «dove salviamo *il* benchmark», dando per scontato che
ne bastasse uno. Ma il confronto è **plurimo**: se investo in azionario, confrontarmi
con un buono fruttifero postale non dice niente — è ovvio che l'azionario renda di
più e oscilli di più. Il numero uscirebbe, sarebbe pure corretto, e non
significherebbe nulla. È lo stesso errore che questa ripianificazione esiste per non
ripetere.

**La proposta**: il sistema *suggerisce* di aggiungere asset di riferimento — un ETF
S&P 500, un EuroStoxx 600, un world, e qualche obbligazionario. Un menù a tendina
lascia scegliere quale usare. Restano selezionabili **tutti** gli asset in database,
ma i riferimenti stanno **in cima**. A qualificarli è una casella nel footer del form
asset, **condivisa fra tutti gli utenti**: spenta di default ovunque, accesa di
default quando l'asset viene aggiunto da questa pagina.

E lo stesso selettore, con lo stesso ordinamento, serve i segnali di Asset Detail e
Forex Detail.

#### Verifica sul codice: quattro conferme e un avvertimento

**1. Gli asset sono già globali.** `Asset` (`backend/app/db/models.py:464`) non ha
`user_id` né alcun campo di proprietà. Una colonna sull'asset è **condivisa per
costruzione**: non serve inventare un meccanismo di condivisione, è già così che
funziona il resto.

**2. Il selettore è già quello.** `RiskAnalysisPanel.svelte` usa **già**
`SignalAssetParamControl` in due punti — riga 891 per l'asset di confronto, riga 1091
per il proxy del replay. L'intuizione «userei quello stesso componente» descrive lo
stato di fatto: manca solo l'ordinamento.

**3. Un solo componente copre quattro punti.** `SignalAssetParamControl` (64 righe) è
raggiunto da `ChartSignalsSection`, che vive sia in `/assets/[id]` sia in
`/fx/[pair]`. Quindi Asset Detail, Forex Detail, confronto di rischio e proxy di
replay passano tutti di lì. Una modifica, quattro benefici.

**4. I titoli di sezione esistono già.** `SelectOption` espone `header?: boolean`, e
il commento nel tipo descrive esattamente la semantica che serve: la voce è saltata
dalla tastiera, ignorata da Invio, e **sparisce quando la ricerca svuota la sua
sezione** — «un titolo sopra il nulla è peggio di nessun titolo». Mettere i benchmark
in cima è quindi un `sort` più due intestazioni, non un componente nuovo.

L'ordinamento attuale è alfabetico puro (`SignalAssetParamControl.svelte:31`):

```javascript
.sort((left, right) => left.label.localeCompare(right.label));
```

**⚠️ L'avvertimento: `AssetType.INDEX` esiste già.** Il suo docstring dice
testualmente *«Market indices and benchmarks (e.g., S&P 500, MSCI World) — no
transactions allowed»*. Ma è usato in **un solo punto** di tutto il backend
(`transaction_batch_stages.py:502`), e solo per **vietare le transazioni**. Non è un
catalogo di benchmark: è un tipo che blocca gli acquisti.

E non può diventare il flag, per la ragione che rende giusta la casella separata: un
ETF S&P 500 è un ottimo benchmark **e** un asset che puoi possedere davvero.
Marcandolo `INDEX` non potresti più registrarci sopra una transazione. **Il flag deve
essere ortogonale al tipo.**

Resta però una domanda onesta: un asset `INDEX` non è acquistabile, quindi esiste
*solo* per il confronto. Vale la regola `è_benchmark = flag OR asset_type == INDEX`?
**Risolta il 17 Set → D53**: non una regola calcolata a ogni lettura, ma flag
**materializzato** — backfill in migrazione per gli `INDEX` esistenti, e accensione
automatica **in sola lettura** alla creazione di un nuovo `INDEX`.

#### Cosa resta da decidere

**(a) Piatto o per tipo.** 🟢 **Risolta → D52.** L'argomento di partenza è che il
riferimento giusto dipende da cosa si possiede. Una casella booleana produce però un
elenco piatto in cui l'ETF azionario e quello obbligazionario stanno mescolati — cioè
ripropone il problema che la proposta vuole risolvere, solo più in alto nella lista.

> ⚠️ **Autocorrezione.** Qui stava scritto «nessuna colonna in più, il tipo lo
> abbiamo». **Era falso**: `AssetType` distingue la *forma* dello strumento (STOCK,
> ETF, BOND, CRYPTO, FUND, HOLD, CROWDFUND, INDEX, OTHER), non il contenuto. Un ETF
> azionario e uno obbligazionario sono **entrambi `ETF`**, quindi raggruppare per
> `asset_type` li avrebbe lasciati nella stessa sezione: esattamente il mescolamento
> che la sezione doveva eliminare. La raccomandazione era costruita su un presupposto
> sbagliato ed è stata accettata dal developer prima che l'errore emergesse.
>
> Cercata un'alternativa nei dati esistenti: `FAClassificationParams`
> (`schemas/assets.py:533`) ha `sector_area`, e il suo enum contiene davvero
> *Corporate Bonds* e *Government Bonds*. Ma è una **distribuzione di pesi**, non
> un'etichetta, e `classification_params` è opzionale — dipende dall'arricchimento del
> provider. Servirebbe una soglia arbitraria su un campo che per molti asset è nullo.

**Esito**: si estende `AssetType` con i sottotipi dove la distinzione ha senso (D52),
si disegna l'icona a due strati, e le sezioni del selettore diventano corrette per
costruzione. L'elenco preciso dei sottotipi è **Q9**.

**(b) Chi può accendere la casella.** 🟢 **Risolta → D60.** Condivisa fra tutti gli
utenti significa che chiunque la tocchi cambia la lista **a tutti**. Il developer
conferma che è il comportamento voluto, non un compromesso: non ha senso che lo stesso
ETF sia un buon riferimento per un utente e no per un altro. È coerente col resto del
modello — `Asset` non ha `user_id`, e un asset marcato benchmark, **purché non sia
`INDEX`**, resta assegnabile alle transazioni come qualunque altro, cosa a sua volta
globale. Nessun permesso speciale, nessuna riserva all'amministratore.

**(c) La scelta si ricorda?** 🟢 **Risolta → D64.** Il catalogo dice *quali* asset sono
buoni riferimenti; non dice *quale* stai usando. L'ipotesi precedente era una colonna
su `UserSettings`, ereditata dalla versione archiviata. **Il developer la scarta**: la
scelta vive nella **cache locale del client**, e se non c'è nulla la zona resta vuota
con un testo che spiega cosa fare. Il backend resta senza stato — il benchmark viaggia
nella richiesta — e la regola di degrado è obbligatoria: asset cancellato o
de-flaggato ⇒ stato vuoto, non errore.

**(d) Da dove viene la lista dei suggerimenti.** 🟢 **Risolta → D65.** «Il sistema
suggerisce» non richiede che i suggerimenti siano risolvibili: sono **testi fissi
tradotti**, mostrati quando la zona è vuota. Cade l'ipotesi della lista curata (YAML o
costante con identificatori) e con essa le chiamate ai provider e la manutenzione di
un elenco di ISIN. Resta aperto quanto i testi debbano essere specifici → **Q11**.

**(e) La valuta.** 🟢 **Risolta → D66.** Non era nell'elenco originale ed è una trappola
vera: se il benchmark è in USD e la valuta base è EUR, il beta misura **anche il
cambio**. Va convertito con l'FX che già abbiamo — «abbiamo il sistema delle forex
apposta» — altrimenti il numero è contaminato in silenzio, esattamente il tipo di
errore che il CVaR ci ha insegnato a temere.

#### Cosa questo comporta

| Dove | Cosa |
|---|---|
| DB | colonna booleana su `assets` + **nuovi valori in `AssetType`**: due tipi base (`COMMODITY`, `REAL_ESTATE`) e i sottotipi ETF (D52, D61) + migrazione Alembic incrementale con backfill `INDEX` (D53) |
| Backend | campo negli schemi asset, filtro/ordinamento in lista; **correzione del docstring bugiardo** su `valuation_model` (D51) |
| `SignalAssetParamControl` | ordinamento a sezioni con `header` (già supportato) |
| `SignalTreeSelect` | **generalizzazione**: da `components/charts/` a `components/ui/select/`, contenuto dell'opzione come snippet, secondo slot icona per la pastiglia (D62) |
| `AssetModal` | interruttore nel footer, sul modello di `active` (riga 2126), **readonly se `INDEX`**; albero a due livelli per il tipo |
| `assetTypes.ts` | nuove voci in `PNG_MAP` + costante per le **pastiglie** sovrapposte |
| PNG | due file nuovi: `commodity`, `real-estate`. `liquidity` **esiste già** (D61) |
| i18n | etichette dei nuovi tipi in quattro lingue sotto `assets.types.*` |
| Risk page | pannello di stato vuoto con i suggerimenti |
| `UserSettings` | preferenza salvata (punto **c**) |

Nessuno di questi punti è grosso preso da solo. È **trasversale**, non profondo.

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

### Q3 — Colonne di rischio nelle tabelle di Asset Global 🟢 chiusa → D54

Ipotesi ad alto rapporto valore/costo (vedi documento 03 §4): volatilità annua, max
drawdown e correlazione media come colonne delle tre tabelle esistenti, sfruttando la
sincronizzazione già presente.

**Chiusa dal developer, in modo più ampio dell'ipotesi**: entrano **tutti** i segnali
utili, ma **nascosti per default** e attivabili dall'utente; visibile di default il
solo **max drawdown**, perché è facile da capire e ad alto impatto.

La scelta non costa nulla in meccanismo. `DataTable` espone già `hiddenByDefault` per
colonna, e la persistenza salva **solo gli override espliciti**
(`DataTable.svelte:193-196`), con una nota nel codice che spiega perché: così un
default dinamico resta la verità viva e un valore vecchio in `localStorage` non può
tenere nascosta una colonna che dovrebbe vedersi.

Si rivedrà insieme ad Asset Detail (D47), quando la grammatica sarà decisa.

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

### Q5 — Documentazione utente 🟢 chiusa → D55

D4 prevede un link alla documentazione **per riga** della scala L1. Le pagine
`mkdocs_src/docs/financial-theory/technical-analysis/risk-metrics/` esistono già per
volatilità, Sharpe, Sortino e max drawdown, ma **non** per CVaR/VaR, correlazione,
contributo al rischio, replay e simulazione.

**Chiusa dal developer** con un ordine di lavoro, non con un elenco di pagine:

1. **All'avvio dello sviluppo**, non alla fine: per ogni pagina che servirà si crea un
   **mock di due righe, solo in inglese**, registrato subito nell'indice di
   `mkdocs_src/mkdocs.yml` secondo le regole già fissate nelle skill. Così l'indice
   nasce completo e nessun link resta appeso mentre il codice avanza.
2. **Durante lo sviluppo**: un agente di documentazione riempie le pagine **in
   inglese**, in parallelo agli agenti di codice.
3. **Alla fine di tutta la documentazione**: le traduzioni in un **blocco unico**, mai
   pagina per pagina.

Il vantaggio non è solo organizzativo: un mock in indice rende il gate `check-links`
verde fin dal primo giorno, quindi la documentazione mancante si vede come pagina
vuota invece che come collegamento rotto.

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

**✅ Scritto il 17 Set 2026**: [`07-piano-esecutivo.md`](./07-piano-esecutivo.md).
Tutte le questioni da Q1 a Q12 sono chiuse e tutti gli otto punti qui sotto sono
confluiti nel piano — l'ordine migrazione/UI in §4, la taglia in §7, l'indirizzo
dell'oracolo M4 in §5, la voce di CHANGELOG in §6, e i restanti quattro nelle schede
di flusso §8.

Elenco conservato come tracciamento di ciò che il piano doveva assorbire:

1. **Ordine fra migrazione e UI.** M1 e M3 sono invisibili all'utente ma sbloccano la
   reattività su cui poggia metà di [`05`](./05-grammatica-visiva-e-rappresentazioni.md).
2. **Una taglia.** Oggi non esiste da nessuna parte una stima di quanto sia grande
   questo lavoro. Senza, il piano esecutivo diventa una lista di desideri.
3. **Dove vivono i test dell'oracolo M4** — categoria, lane di runtime, registrazione
   nel catalogo. M4 è la chiave di volta e non ha ancora un indirizzo.
4. **La voce di CHANGELOG per M2**, che cambia un numero già mostrato agli utenti.

E, aggiunte il 17 Set, due lavorazioni di backend che prima non esistevano nel piano:

5. **Il filtro per asset su `PortfolioRiskScope`** (D58) e la scelta sui pesi (Q8).
   Tocca schema, servizio e UI, ma **nessun plugin**.
6. **L'estensione di `AssetType`** (D52), il backfill `INDEX` (D53) e la correzione
   del docstring bugiardo (D51) — tutto nella stessa migrazione incrementale, insieme
   alla colonna del flag benchmark.
7. **L'allineamento dei punti che raggruppano per tipo** (Q12, D70): i due scenari YAML
   predefiniti, `PNG_MAP`, le etichette nelle quattro lingue e l'elenco scritto a mano
   in `AssetTable.svelte:181`. Vanno consegnati **insieme** all'enum, e sorvegliati da
   un test che leghi l'enum alle tre tabelle — perché tutti e tre i punti ripiegano in
   silenzio invece di lamentarsi.
8. **La gerarchia cromatica nei due grafici di allocazione** (D71): mappa
   sottotipo → primario in `assetTypes.ts`, `hexToHsl` in `utils/colors.ts`, colore per
   dato al posto del colore per indice. Tutto frontend, nessun tocco al backend.

Risolte invece da D46 e D47: cosa si rilascia nel frattempo (nulla, si rilascia a
catena completa) e quando si riapre Asset Detail (a fine catena). E da D54 e D55: le
colonne di Asset Global e l'ordine di scrittura della documentazione.

### Q7 — Quali misure acquisire dalla famiglia drawdown 🟢 chiusa → D56

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

---

**🟢 Chiusa il 17 Set 2026 → D56**, con un esito più largo della raccomandazione.

Il developer ha obiettato al taglio proposto — «a parte ADD che mi sembra poco utile,
non capisco perché non tutte» — e l'obiezione era fondata: entrano **quattro** misure,
non una. `MDD`, `DaR`, `CDaR`, `UCI`.

**Prima però è caduta un'ambiguità sulle varianti.** `_Abs` e `_Rel` non sono due
convenzioni equivalenti. Letto il sorgente e ricostruito il numero a mano:

| variante | serie | formula del drawdown | unità |
|---|---|---|---|
| `_Abs` | `np.cumsum` | `peak − i` | punti di rendimento cumulato |
| `_Rel` | `np.cumprod` | `(peak − i) / peak` | **% dal picco** |

Riscontro esatto su 1250 giorni: `MDD_Abs` libreria 0,227822 = mano 0,227822;
`MDD_Rel` libreria 0,212860 = mano 0,212860. **Si adotta `_Rel`**: è l'unica che
corrisponde a ciò che chiunque intende dicendo «ho perso il 20%».

**Il quadro completo della famiglia**, misurato:

| misura | valore | tempo | esito |
|---|---:|---:|---|
| `MDD_Rel` | 0,5836 | 1,6 ms | ✅ entra |
| `DaR_Rel` | 0,5496 | 1,6 ms | ✅ entra |
| `CDaR_Rel` | 0,5632 | 1,7 ms | ✅ entra |
| `UCI_Rel` | 0,4197 | 3,0 ms | ✅ entra |
| `ADD_Rel` | 0,3981 | 2,8 ms | ❌ scelta del developer — l'UCI dice la stessa cosa meglio |
| `EDaR_Rel` | tupla | ~27 ms | ❌ conferma D42 |
| `RLDaR_Rel` | 0,1939 / **0,0000** | 89-166 ms | ❌ conferma D42, **più una prova nuova** |

Su `RLDaR` vale la pena essere espliciti, perché è l'unico caso in cui la prova è più
forte della motivazione originale. D42 lo escludeva per spiegabilità. Ma con un seme
restituisce `0,000000` **esatto** e con un altro 0,1939: il solutore degenera senza
segnalare nulla. Una misura di rischio che risponde «zero» in silenzio non è una
metrica poco chiara, è una metrica che **mente**. Resta fuori anche se un giorno la
spiegabilità smettesse di essere un problema.

`EDaR` è invece solo scomodo, non rotto: restituisce una tupla `(valore, parametro)`
da spacchettare. Resta fuori per D42, non per difetto.

Il punto 2 dei candidati — i contributi su misura non-MV — **non è chiuso da qui**: è
una scelta di rappresentazione, non di acquisizione, e il blocco dei contributi
negativi resta valido. Si decide quando si ridisegna la card dei contributi.

---

### Q8 — Rinormalizzazione dei pesi quando il portafoglio si affetta 🟢 chiusa → D59

Discende direttamente da D58. Una volta che si può chiedere «solo questi asset del mio
portafoglio», resta da decidere cosa siano i pesi della fetta. Le due risposte non sono
sfumature della stessa cosa: rispondono a domande diverse.

| | Pesi **rinormalizzati** al 100% della fetta | Pesi **reali** mantenuti |
|---|---|---|
| Domanda | «Com'è fatta la mia parte azionaria, guardata da sola?» | «Quanto pesa la mia parte azionaria sul rischio di tutto?» |
| Confronto sensato con un benchmark | ✅ sì — è la fetta contro il suo riferimento | ❌ no — la fetta al 60% sembra sempre meno rischiosa dell'indice |
| Contributi al rischio | sommano a 100% della fetta | sommano alla quota della fetta sul totale |
| Rischio d'equivoco | far credere di essere tutto investito in azioni | leggere un CVaR basso e pensare che la fetta sia tranquilla |

La prima serve a D48 — il confronto con il riferimento giusto è l'intero motivo per
cui D58 esiste. La seconda serve a L2, dove la domanda è quanto una parte contribuisce
all'insieme, e lì il contributo al rischio la dà già senza affettare nulla.

**Chiusa dal developer: si rinormalizza.** La colonna di destra resta comunque servita,
ma da un altro strumento: il contributo al rischio sull'intero portafoglio. Resta
l'obbligo di **dichiararlo nella UI**, perché la stessa percentuale significa due cose
diverse a seconda di cosa la sta generando.

### Q9 — Quali sottotipi di ETF, e come si chiamano 🟢 chiusa → D61, D62, D67

Discende da D52. Il developer ha fissato il criterio — «ovviamente non tutti, solo
quelli che hanno senso» — e poi, esaminando i candidati, ne è uscita una struttura più
stretta di quella proposta (**D61**): il secondo livello **non è un elenco nuovo**, è
l'insieme dei tipi base. La specializzazione di un ETF è «quale tipo base contiene».

| Candidato proposto | Esito |
|---|---|
| Azionario | ✅ `STOCK` come secondo livello |
| Obbligazionario | ✅ `BOND` come secondo livello |
| Materie prime | ✅ ma serve **`COMMODITY` come tipo base nuovo** — oggi manca |
| Immobiliare | ✅ ma serve **`REAL_ESTATE` come tipo base nuovo** — oggi manca |
| Monetario | 🟡 **solo sottotipo**, nessun tipo base — D67 incrina la regola di D61 |
| Bilanciato / multi-asset | ❌ non è un sottotipo: è l'`ETF` generico, che resta come residuo |
| Suddivisione di `FUND` | ❌ gli ETF sono già fondi, passivi; la distinzione utile è sul contenuto |

**Il caso `LIQUIDITY`.** ⚠️ **Autocorrezione, 17 Set → D63.** Qui stava scritto che il
monetario era «già mezzo costruito, icona ed etichette pronte», sulla base del fatto
che `PNG_MAP` (`assetTypes.ts:30`), `liquidity.png`, le quattro lingue (riga 143) e
l'emoji `💰` in `AllocationHistoryChart.svelte:129` lo nominano tutti mentre l'enum del
backend no.

La lettura era sbagliata. Quelle voci **non sono orfane**: servono a disegnare un
**secchio sintetico**. `portfolio_engine.py:1039-1041` inietta la cassa
nell'allocazione come pseudo-tipo, con un commento esplicito
(*«Allocation: cash as Liquidity (type + sector, not geography)»*). La liquidità non è
un asset, è il saldo dei broker.

Aggiungerla all'enum creerebbe un doppione **visibile**: gli asset veri entrano in
`by_type` con `asset_type.value`, cioè maiuscolo (`:1448`, alimentato da `:2155`), la
cassa entra come `"Liquidity"`. Due chiavi, due fette, stessa icona — perché
`getAssetTypeIconUrl` normalizza in maiuscolo. Sembrerebbe un bug e lo sarebbe.

Restano quindi da disegnare **due** icone, `commodity` e `real-estate`, e resta aperto
come rappresentare il monetario → **Q10**.

**Resta aperto** anche il naming esatto dei valori dell'enum (`ETF_STOCK` o
`ETF_EQUITY`? il primo è coerente col tipo base che nomina, il secondo con l'uso
corrente in finanza) e le etichette tradotte sotto `assets.types.*`.

#### Come si sceglie il secondo livello — D62

Tre ipotesi valutate:

| | Costo | Note |
|---|---|---|
| Secondo selettore che appare dopo ETF | basso | `SimpleSelect` esistente, zero componenti nuovi; ma sono **due gesti** |
| Pulsante → modale | alto | annida una modale dentro `AssetModal` (2427 righe) |
| **Albero a due livelli** | medio, **già scritto** | `SignalTreeSelect.svelte` |

Vince il terzo. `SignalTreeSelect` (359 righe) espone `groups: SignalTreeGroup[]`, ogni
gruppo con `items: SignalTreeItem[]`: due livelli esatti, espandibili, con ricerca che
attraversa entrambi e navigazione da tastiera. Il costo vero è la **generalizzazione** —
oggi vive in `components/charts/` e importa `SignalOptionContent` — e il fatto che
`SignalTreeItem` ha un solo campo `icon`, mentre la pastiglia ne vuole due.

La migrazione non tocca le righe esistenti (restano `ETF`), quindi non serve backfill —
a differenza di D53, che invece lo richiede.

---

### Q10 — Come si rappresenta il monetario 🟢 chiusa → D67

Nasce da D63. D61 aveva stabilito che il secondo livello di un ETF è «quale tipo base
contiene». Il monetario rompe la regola, perché **non esiste un tipo base monetario**:
`LIQUIDITY` è la cassa, cioè il saldo dei broker, non una classe di investimento.

E la distinzione è reale, non formale. Un fondo monetario è uno strumento che si
compra, ha un prezzo, un emittente e un rischio — piccolo ma non nullo. La cassa su un
conto non ha nulla di tutto questo. Confonderli significherebbe dire che un fondo
monetario non può perdere, che è falso.

| Strada | A favore | Contro |
|---|---|---|
| **A** — nuovo tipo base `MONETARY` | Rispetta D61 senza eccezioni; separa nettamente investimento e cassa; serve anche fuori dagli ETF (fondi monetari veri) | Un tipo base in più che quasi nessuno userà da solo; serve una terza icona |
| **B** — nessun sottotipo: il monetario sta sotto `BOND` | Zero costo; difendibile in finanza — un fondo monetario è debito a brevissima scadenza | Un benchmark obbligazionario decennale e uno monetario finirebbero nella stessa sezione, con profili di rischio lontanissimi: è il problema che D48 esiste per risolvere |
| **C** — si rimanda | Non blocca nulla oggi | Lascia un sottotipo mancante proprio nella categoria dove il confronto sbagliato fa più danno |

**🟢 Chiusa dal developer → D67**, con una quarta strada che non avevo considerato:
`ETF_MONETARY` **esiste come sottotipo, senza un tipo base corrispondente**.

Tiene il pregio di A — il monetario ha una sezione sua, quindi un decennale e un
monetario non finiscono mescolati — senza pagarne il prezzo: nessun tipo di primo
livello che nessuno userebbe da solo, nessuna icona in più, perché la pastiglia riusa
`liquidity.png`, che esiste, significa denaro e non è un tipo base.

⚠️ **Va detto chiaramente**: questo **incrina la regola di D61**. Il secondo livello
non è più *esattamente* l'insieme dei tipi base, è l'insieme dei tipi base **più uno**.
La regola resta vera per tutti gli altri sottotipi e l'eccezione ha una ragione — un
fondo monetario si compra, la cassa no (D63) — ma va scritta, non lasciata scoprire a
chi implementerà.

### Q11 — Quanto sono specifici i testi di suggerimento 🟢 chiusa → D68

Nasce da D65. I suggerimenti sono testi fissi tradotti, quindi la domanda non è più
«da dove vengono» ma **cosa nominano**.

| Strada | Esempio | Nota |
|---|---|---|
| **A** — nominare l'**indice** | «un ETF che replica l'S&P 500» | Neutro, non invecchia, non indica un prodotto |
| **B** — nominare il **prodotto** | «VWCE (IE00B4L5Y983)» | Immediato da cercare, ma è di fatto una raccomandazione d'acquisto in una stringa tradotta, e gli ISIN cambiano o vengono delistati |

**🟢 Chiusa dal developer → D68**: strada A, **restando generici**. I testi nominano
indici famosi — «un ETF sull'S&P 500», «uno sull'EuroStoxx 600», «un globale tipo MSCI
World», «un obbligazionario ampio» — e **mai un ISIN o un ticker**.

Un indice è un fatto pubblico e stabile; un ISIN è la scelta di un emittente, e
metterlo in un testo dell'applicazione sposta LibreFolio da strumento di misura a
strumento di consiglio. Vale anche la manutenzione: un testo tradotto in quattro lingue
che cita un prodotto delistato è un errore in quattro punti contemporaneamente.

I testi elencano **anche le classi** («ne serve uno azionario, uno obbligazionario…»),
coerentemente con Q9 e con la struttura a sezioni di D48.


---

### Q12 — Il sottotipo cambia il raggruppamento ovunque il tipo sia una chiave 🟢 chiusa → D70, D71, D72

Nasce dal controllo chiesto dal developer dopo D67: *«verifica che queste risposte non
abbiano creato nuove domande»*. Ne hanno creata una, e non piccola.

D52 stabilisce che i sottotipi entrano **dentro `AssetType`**. D51 dice che è sicuro,
perché `asset_type` non pilota comportamenti. È vero per i *comportamenti*, ed è
**falso per i raggruppamenti**: `asset_type` non decide cosa il sistema *fa*, ma decide
in continuazione come il sistema *somma*. Cambiare l'insieme dei valori cambia ogni
somma che usa quel valore come chiave.

#### Il caso che fa danno, verificato

Lo stress test ha una dimensione `asset_class`, e quella classe è **letteralmente** il
valore dell'enum — `service.py:446`: `asset_class=asset_type.value`. Gli scenari
predefiniti sono file YAML che elencano i secchi per nome:

```yaml
# scenario_catalog/built_in/hypothetical/equity_crash.yml
bucket_shocks:
  STOCK: -0.35
  ETF: -0.25      # ← tutti gli ETF, compreso un obbligazionario
  FUND: -0.25
  INDEX: -0.35
  OTHER: 0.0
```

Se un ETF azionario diventa `ETF_STOCK`, il secchio `ETF` **non lo trova più**. E
`_resolve_bucket` (`stress.py:219-226`) non solleva errore: restituisce
`UNCONFIGURED_ZERO`, shock `0.0`. Risultato — in un crollo azionario i tuoi ETF
azionari **non si muovono**, e il portafoglio sembra molto più solido di quanto sia.
È esattamente la classe di errore di D28 (CVaR distorto) e D63 (doppia fetta di cassa):
nessuna eccezione, nessun avviso in faccia, solo un numero credibile e sbagliato.

#### Il caso che invece migliora

La stessa riga `ETF: -0.25` è **già oggi** un difetto di modello: in un crollo
azionario un ETF obbligazionario perde il 25% come uno azionario. Con i sottotipi
quella distinzione diventa finalmente esprimibile — `ETF_STOCK: -0.35`,
`ETF_BOND: -0.05`. Vale anche per la torta di allocazione: un portafoglio tutto in ETF
oggi mostra **una fetta al 100%** che non informa di nulla, mentre «azionario 60% /
obbligazionario 30% / materie prime 10%» è la risposta alla L2, *«sono diversificato
come credo?»*.

Quindi il sottotipo non è un rischio da evitare: è un miglioramento che **richiede una
decisione esplicita su ogni punto che raggruppa**.

#### I punti che raggruppano, censiti

| Punto | Dove | Cosa succede senza decisione |
|---|---|---|
| Scenari stress predefiniti | `scenario_catalog/built_in/hypothetical/*.yml` (2 file) | Shock silenziosamente a zero |
| Torta e storico allocazione | `portfolio_engine.py:1448` → `AllocationPieChart`, `AllocationHistoryChart` | Fette nuove, etichetta cruda e icona `other` |
| Treemap esposizione | `ExposureTreemap.svelte:84` | Come sopra |
| Icone | `PNG_MAP` in `assetTypes.ts:19-31` | `getAssetTypeIconUrl` non lancia: ripiega su `other.png`, quindi un ETF azionario si disegna grigio «altro» |
| Etichette | `frontend/src/lib/i18n/{en,it,fr,es}.json` | `|| type` mostra la chiave grezza |
| Filtro della tabella asset | `AssetTable.svelte:181` — elenco **scritto a mano**, senza `INDEX` | I nuovi tipi non sono filtrabili |
| Filtro backend | `crud.py:180-181` | Un filtro `ETF` non trova più gli ETF specializzati |
| AI export | `asset_resources.py:110` e simili | ✅ **nessun problema**: viaggia come `str` libero, non come enum vincolato |

#### Le strade

| Strada | Cosa comporta |
|---|---|
| **A** — si raggruppa sempre sul valore pieno | La torta si specializza da sola, lo stress diventa corretto. Costo: icone, etichette in quattro lingue, elenco della tabella, **e la riscrittura dei due YAML** |
| **B** — si raggruppa sempre sul contenitore | Serve una funzione `base_type(asset_type)` condivisa; niente si rompe, ma si butta via il guadagno: la torta resta muta e lo stress resta sbagliato |
| **C** — dipende dal punto | Torta, treemap e stress sul **valore pieno**, perché lì la distinzione è informativa; filtri e ricerca sul **contenitore**, perché lì serve trovare. Costa una funzione in più e una regola da ricordare |

#### 🟡 Declassata dal developer → D70

*«È uno YAML che abbiamo scritto noi e mai usato, quindi non lo vedo come un problema
ma come un segnale che quello che già esiste del risk system potrebbe dover essere
adeguato.»*

Giusto, e la distinzione conta: **un file che possediamo non è un vincolo, è un
compito**. Non c'è un contratto con l'esterno da rispettare, non c'è un formato altrui
da assecondare — ci sono due file YAML da riscrivere nella stessa consegna dell'enum.
L'avevo trattato come una domanda di progetto quando era una voce di lavoro.

Va tenuto solo il perché lo avevo scovato: l'errore non è che lo scenario fosse
sbagliato, è che **fallisce in silenzio**. `UNCONFIGURED_ZERO` non avvisa nessuno. Per
questo il piano esecutivo deve pretendere non l'aggiornamento dei due file, che è
banale, ma un **test che renda impossibile dimenticarli**: ogni valore dell'enum deve
avere un secchio negli scenari, una voce in `PNG_MAP` e un'etichetta nelle quattro
lingue. Oggi tutte e tre le coperture sono affidate alla buona volontà, e tutte e tre
ripiegano senza far rumore — `other.png` per l'icona, la chiave grezza per l'etichetta,
shock zero per lo scenario.

#### Il residuo sulla torta, chiuso da D71

Restava una scelta che i due YAML non esauriscono: se la torta si specializzasse o no.
Avevo posto un compromesso — specializzare risponde alla L2, ma con pochi asset produce
otto fette da poco ciascuna — e il developer non ne ha scelto un corno: **ha eliminato
il compromesso**. I sottotipi restano dentro la massa del primario con tonalità vicine,
i numeri si leggono nel tooltip, e un asset non specializzato usa il colore pieno.

Costo verificato sul codice, perché non è gratis:

| Cosa | Dove | Nota |
|---|---|---|
| Il colore è assegnato **per indice** | `AllocationPieChart:338` (`color: palette`), `AllocationHistoryChart:531-533` e `:585` | Va sostituito con un colore **per dato**: nella torta `itemStyle.color` sul singolo item, nello storico su `lineStyle`/`areaStyle`/`itemStyle` e nel tooltip. Quattro punti nello storico, non uno |
| Serve `hexToHsl` | `utils/colors.ts` ha **solo** `hslToHex` (`:123`) | Le due tavolozze sono esadecimali scritte a mano «a massima distanza cromatica»: per ricavarne sfumature serve la conversione inversa, che oggi non c'è |
| L'alfa è una concatenazione di stringa | `AllocationHistoryChart:532` — `palette[i] + '88'` | Funziona finché il colore è un esadecimale a 6 cifre. Una sfumatura calcolata deve mantenere quel formato o passare a `rgba()` |
| Le tonalità devono reggere **due temi** | `PALETTE_LIGHT` è scura (`#1a4031`), `PALETTE_DARK` è chiara (`#4ade80`) | La sfumatura non può andare sempre verso il chiaro: va calcolata rispetto al tema, o due sottotipi diventano indistinguibili in uno dei due |
| La legenda si affolla | commento «up to 12» in `AllocationHistoryChart:107`, la torta ha già la paginazione | Con i sottotipi le voci possono superare la dozzina. Da valutare se la legenda elenca i **primari** e il dettaglio resta al tooltip |

⚠️ **Trappola di denominazione, da fissare ora**: la derivazione del tipo primario
**non può essere una divisione sulla stringa**. `rawKey` conserva gli underscore
(`AllocationPieChart:210`, regex `/[^A-Z_]/g`), quindi spezzare `ETF_STOCK` su `_`
funziona — ma `REAL_ESTATE` è un **tipo primario** e si spezzerebbe in `REAL` +
`ESTATE`, producendo un genitore inesistente. Serve una mappa esplicita accanto a
`PNG_MAP` in `assetTypes.ts`, che è anche il posto dove vive già la pastiglia (D52).

⚠️ **Condizione perché la sfumatura si veda**: oggi le fette sono ordinate per valore
decrescente (`AllocationPieChart:179`). Con quell'ordinamento due sottotipi dello
stesso genitore finiscono **lontani**, e la parentela cromatica diventa invisibile —
si vedono due colori simili in due punti scollegati del cerchio, che è peggio che non
averli sfumati. L'ordinamento deve diventare **gerarchico**: i genitori ordinati per
totale, i figli per valore dentro il genitore. Senza questo, D71 non funziona.

Nota di portata: la gerarchia si costruisce **nel frontend**. Il backend continua a
produrre `by_type` piatto (`portfolio_engine.py:1448`), quindi nessuna modifica a
motore, schema o API — solo `assetTypes.ts` e i due grafici.

#### Il ripiego a due anelli (D72)

Se un anello solo si rivelasse illeggibile, il ripiego è la **ciambella annidata**, e
costa meno di quanto sembri: il grafico **è già una ciambella** — `radius: ['35%',
'70%']` alla riga 274 — quindi il secondo anello è una banda dentro un buco che esiste
già, non una riscrittura.

⚠️ Una trappola da conoscere prima, perché questo file ne ha già collezionate tre. Il
percorso di aggiornamento veloce alla riga 193 scrive `series: [{data: chartData}]` —
**una sola serie**. Con due anelli, quel ramo aggiornerebbe l'interno e lascerebbe
l'esterno fermo all'ultimo disegno completo: dati vecchi, nessun errore, nessun
sintomo. Esattamente la famiglia di difetti che i tre commenti «Bugfix» del file
documentano (`lastRawTypeKeys`, il `$effect` che leggeva la verità dell'array invece
del contenuto, la chiave rich-text che sbagliava nelle lingue diverse dall'inglese).

Scartata invece la **barra impilata polare**: è un grafico legittimo, ma mappa il
valore sul raggio, e l'area cresce col quadrato del raggio. Due quote uguali a
distanze diverse dal centro occupano aree diverse, e in un grafico che serve a dire
«quanta parte del totale» l'occhio legge proprio l'area. È l'attrezzo giusto per
confrontare categorie lungo una dimensione ciclica — mesi, ore del giorno — non per
parti di un tutto.

⚠️ Da mettere comunque a piano, indipendentemente dalla strada scelta: `PNG_MAP` e le
quattro lingue devono coprire **ogni** valore dell'enum, e serve un test che lo
verifichi. Oggi la copertura è lasciata alla buona volontà, e il ripiego silenzioso su
`other.png` fa sì che un buco non si veda.
