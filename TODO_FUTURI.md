# TODO FUTURI

Questo file documenta miglioramenti futuri, migrazioni pianificate, e note tecniche importanti per il progetto LibreFolio.
I TODO completati sono in `TODO_Completati.md`.

---

## 🔌 Arricchimento asset da fonti esterne — ESMA FIRDS, OpenFIGI, JustETF (F16)

**Data aggiunta**: 1 Settembre 2026
**Status**: 📋 FUTURO — da riprendere a consolidamento finito
**Origine**: feedback Giuseppe + Alfy 07/08/2026; skill di riferimento: `asset-plugin`

### Contesto

Giuseppe scarica cataloghi da ESMA (FIRDS) e Yahoo Finance (quotazioni attuali e storiche) e usa OpenFIGI per arricchire gli ISIN. Twelve Data sarebbe ideale ma è a pagamento. Domanda aperta: esistono API JustETF?

### Idea architetturale (Alfy)

- Funzione di **arricchimento dati asset esterna al provider prezzo**, come **libreria interna**:
  i plugin provider la usano per arricchire il proprio output — più gestibile di un plugin standalone.
- ESMA FIRDS: `https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_firds_files`
  — publication date ultima settimana, type "full file" → restituisce i cataloghi.
- OpenFIGI: concettualmente simile agli altri provider → integrazione più semplice.

### Collegamenti

- Piano in pausa correlato: `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00AssetIdentityAndIdentifiers.prompt.md` (identità asset, identificativi).

---

## 🔄 Self-update in-app (da F14)

**Data aggiunta**: 1 Settembre 2026
**Status**: 📋 FUTURO — F14 è stato rilasciato in scope 1 (modale + guida); il self-update richiede un piano dedicato
**Origine**: discussione F14 del 01/09/2026

### Obiettivo

Pulsante nel frontend (modale "nuova versione") che fa aggiornare e riavviare il backend.

### Fattibilità analizzata

- **Docker**: un container non può aggiornare la propria immagine da solo, ma può farlo se
  `/var/run/docker.sock` è montato (opt-in in compose): Docker API → pull nuova immagine →
  ricreazione del container. È ciò che fa **Watchtower** (documentato nella guida come alternativa).
  Attenzione: docker.sock montato = root sull'host → montaggio opt-in esplicito, endpoint admin-only,
  script fisso senza input utente. LibreFolio è single-image → caso semplice.
- **Git clone**: script guardato — `git fetch`, `git pull` solo se work-tree pulito
  (`git status --porcelain` vuoto), rebuild, restart. Il restart richiede un supervisore
  (systemd o Docker restart policy). Candidato: `scripts/self_update.sh` documentato.
- Distinguere le varianti di immagine full/light se necessario (F13).

---

## 📧 Server email — verifica account, inviti, recupero password (da P2-1)

**Data aggiunta**: 3 Settembre 2026
**Status**: 📋 FUTURO — non prioritario; nel frattempo l'opzione `require_email_verification` è marcata come placeholder (read-only + badge "coming soon") nella UI admin
**Origine**: audit 08_newCleanAndDocumentation_audit (P2-1) + decisione utente 03/09/2026

### Obiettivo

Connettere LibreFolio a un server email (SMTP configurabile dalle impostazioni admin) e
costruirci sopra tre funzioni:

1. **Verifica email** — rende vera l'opzione `require_email_verification` (oggi placeholder:
   la chiave esiste ma nessuna verifica avviene).
2. **Link di invito** — un admin genera un invito via email; utile soprattutto quando la
   registrazione libera dalla pagina di login è disattivata (l'utente si registra solo
   tramite invito).
3. **Recupero password via email** — reset self-service invece del reset manuale admin.

### Note

- Configurazione SMTP nelle impostazioni globali (host, porta, auth, mittente) con
  test di connessione stile "Test Configuration" dei provider.
- Il flusso invito/reset richiede token monouso a scadenza (tabella dedicata o
  riuso del pattern dei settings con TTL).
- Valutare dipendenza: `aiosmtplib` (async, non blocca l'event loop — regola Async I/O).
- Fino a questo task, nessuna promessa UI sulla verifica email (P2-1 chiuso come placeholder).

---

## 🔗 Suggerimento eventi collegabili nella bulk modal (da P2-6)

**Data aggiunta**: 3 Settembre 2026
**Status**: 📋 FUTURO — feature pronta al 70% (backend già fatto e testato); manca il frontend
**Origine**: audit 08 (P2-6) + idea originale utente (luglio 2026) + indagine 03/09/2026

### La feature voluta

Nella **bulk modal** delle transazioni, in stile riga-notifica "promote": quando una riga
(transazione) può essere collegata a un **evento** di un asset (dividendo, interesse…)
entro un range temporale compatibile, compare una riga di notifica con i candidati;
l'utente conferma il collegamento. Il range riusa il valore dello **slider delta-days**
già presente nella bulk modal.

### Cosa esiste già (da riusare, NON riscrivere)

- **Backend pronto**: `POST /api/v1/transactions/suggest-events`
  (`backend/app/api/v1/transactions.py` ~:257) → `suggest_events_bulk` in
  `transaction_service.py` ~:558-621. Fa: mappa tipo transazione → tipo evento compatibile,
  filtra per tolleranza ±N giorni, ordina per distanza, accetta batch (lista di transazioni).
  Coperto da 8 test API (`backend/test_scripts/test_api/test_events_suggest.py`), mai cablato
  al frontend dal commit `c3faae19` (luglio).
- **UX di riferimento**: la riga-notifica "promote" nella bulk modal
  (`TransactionBulkModal.svelte` ~:2994-3094) come template di presentazione.
- **Pattern picker esistente**: `AssetEventPicker.svelte` + `EventCreateMiniModal.svelte`
  nella sezione avanzata della modale di edit transazione.

### ⚠️ Duplicazione da sanare nell'occasione

`AssetEventPicker` (edit modal) **NON usa** `suggest_events`: interroga gli eventi con
`query_events_bulk` (query generica per asset+range) e manca della mappa di compatibilità
tipo-transazione→tipo-evento e dell'ordinamento per distanza che `suggest_events` ha.
Chi riprende il lavoro deve **fattorizzare**: un unico motore di matching (quello di
`suggest_events`) consumato sia dall'edit modal sia dalla nuova riga-notifica bulk.

### Note di implementazione (dall'indagine)

- Il collegamento si scrive su `asset_event_id` della transazione (poi re-validate).
- Servono: utility frontend condivisa (batch + cache + debounce), componente banner,
  chiavi i18n ×4, E2E `event-suggest-bulk.spec.ts`.
- L'analisi completa (forme, rischi, piano in 4 fasi) è nel report dell'indagine del
  03/09/2026 in questa sessione — recuperabile anche rieseguendo il confronto
  `suggest_events` vs `AssetEventPicker`.

---

## 📊 Risk Analysis — evoluzioni scenario catalog e replay

**Data aggiunta**: 29 Luglio 2026
**Status**: 📋 FUTURO — escluso da G6 iniziale
**Priorità**: Da valutare dopo il rilascio del catalogo statico
**Piano corrente**:
`LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md`

### Catalogo scenari dinamico

- rilevamento dei file senza riavvio;
- reload manuale o hot reload;
- CRUD scenari personali;
- salvataggio delle modifiche effettuate dalla UI;
- import/export YAML;
- override espliciti dei preset built-in;
- validazione e diagnostica amministrativa.

La prima implementazione G6 resta startup-loaded, senza CRUD, database o watcher.

### Proxy historical replay

- persistenza delle associazioni asset → proxy;
- proposta di proxy solo esplicita e confermata dall'utente;
- riuso delle associazioni nei replay successivi;
- diagnostica di copertura/qualità prima di proporre il proxy.

G6 richiede invece scelta manuale per singola esecuzione o esclusione.

### RQMC

Resta a priorità bassa: eventuale scrambling deve avere contratto separato da
`sobol_start_index`, oracle di convergenza e processo `spawn`, senza fallback
SciPy production.

---

## 📉 Risk Analysis — Tracking Error / Information Ratio con benchmark selezionabile

**Data aggiunta**: 16 Settembre 2026
**Status**: 📋 FUTURO — tagliato dalla riorganizzazione Risk
**Priorità**: 🔽 BASSA

### Contesto

`ComparisonAnalytic` (`backend/app/services/risk_plugins/comparison.py`) calcola già
active return, tracking error, information ratio, correlazione e beta contro un asset
reale di confronto. Nella riorganizzazione della UI Risk, **beta e active return
restano**; **tracking error e information ratio vengono rimossi dalla UI**.

Motivo: TE e IR nascono per valutare un gestore attivo contro un **mandato dichiarato**.
Un investitore privato non ha né mandato né benchmark ufficiale, quindi i due numeri
non sono interpretabili e occupano spazio accanto a metriche che decidono.
Il backend non viene toccato: il calcolo resta disponibile via API.

### Azione futura

Riabilitarli **solo dopo** aver introdotto una vera selezione di benchmark:

- scelta del benchmark fra gli asset già presenti in DB (non un ticker libero);
- possibilità di dichiarare un benchmark **persistente** per portafoglio/broker,
  non scelto al volo a ogni esecuzione;
- avviso esplicito quando il benchmark ha valuta o storico non allineati allo scope;
- wording che chiarisca che TE/IR misurano **scostamento dal benchmark**, non qualità.

Senza benchmark persistente e dichiarato, riesporli riproduce il problema attuale.

### Riferimenti

- `backend/app/services/risk_plugins/comparison.py`
- `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte` (sezione comparison)

---

## 🧮 Risk Analysis — Portfolio optimization / frontiera efficiente (Riskfolio)

**Data aggiunta**: 16 Settembre 2026
**Status**: 📋 FUTURO LONTANO — rinviato a tempo indeterminato
**Priorità**: 🔽 MOLTO BASSA

### Contesto

`PortfolioOptimizationAnalytic` (`backend/app/services/risk_plugins/portfolio_optimization.py`)
è implementato e testato (Riskfolio-Lib 7.0.1 + CVXPY, solver CLARABEL/SCS, strategie
min-variance / max-Sharpe / ERC, covarianze historical / Ledoit-Wolf / OAS) ma **non ha
alcuna UI**: oggi è raggiungibile solo via API ed è quindi costo puro per ogni
installazione.

### Perché è rinviato — il motivo vero

Non è la potenza di calcolo: il benchmark misurato dà **0,0159 s warm**. Non è nemmeno
l'ampiezza del paniere in sé. Il problema è che l'ottimizzatore media-varianza produce
un **output prescrittivo** ("i pesi giusti sono questi") che lo strumento non è in grado
di giustificare onestamente:

- è un *error maximizer*: preferisce gli asset il cui rendimento atteso è stato
  sovrastimato dal campione;
- i pesi sono instabili — cambia la finestra di stima e l'allocazione si ribalta;
- più asset significa **più parametri da stimare** (N medie + N(N+1)/2 covarianze) e
  quindi più errore, non meno — motivo per cui esistono gli shrinkage estimator;
- LibreFolio è un tracker, non un consulente: è un confine di prodotto, non tecnico.

### Precondizioni per riprenderlo

1. provider dati esteso (verosimilmente a pagamento) con universo ampio e storia lunga,
   pulita e sovrapposta;
2. una semantica di presentazione non prescrittiva: output come **confronto** con
   l'allocazione attuale, mai come "allocazione consigliata";
3. esclusione di max-Sharpe in-sample; ammesse solo min-variance ed ERC/risk parity,
   che non usano i rendimenti attesi;
4. documentazione utente che spieghi instabilità e limiti prima di mostrare i pesi.

### Decisione pendente sulle dipendenze

Finché resta non esposto, va deciso se **rimuovere** Riskfolio-Lib, CVXPY, CLARABEL e
SCS (più il pool `optimization`) dall'immagine, misurando prima quanto pesano davvero
sui 2.781.625.742 byte totali dell'immagine. Il pool `simulation` (QuantLib) resta
comunque necessario.

Nota: la variante onesta e a basso costo — **ERC come diagnostica**, non come consiglio
("se ogni asset contribuisse allo stesso rischio i pesi sarebbero questi, i tuoi sono
questi") — è un complemento naturale di `risk_contribution` e **non richiede Riskfolio**:
è risolvibile in poche decine di righe di NumPy.

### Riferimenti

- `backend/app/services/risk_plugins/portfolio_optimization.py`
- `backend/app/services/risk/quant/optimization_engine.py`
- `LibreFolio_devWiki/wiki/problems/riskfolio-numpy-vectorbt-dependency-trap.md`

---

## 🎲 Risk Analysis — Monte Carlo avanzato: regimi calibrati e volatilità stocastica

**Data aggiunta**: 16 Settembre 2026
**Status**: 📋 FUTURO — livelli **2, 4 e 5** della scaletta simulazione
**Priorità**: 🔽 BASSA

### Contesto

La riorganizzazione Risk prevede di rilavorare la simulazione ai **livelli 1 e 3**
della scaletta seguente, e di rinviare i livelli 2, 4 e 5:

| # | Approccio | Stato |
|---|---|---|
| 1 | Block bootstrap (rimescolo a blocchi della storia reale) | ✅ in scope |
| 2 | GJR-GARCH (cluster di volatilità + effetto leva) | 📋 **rinviato — non calibrabile da QuantLib** (D88) |
| 3 | Preset di regime **prescritti** (ipotesi dichiarate, non stimate) | ✅ in scope |
| 4 | Markov-switching / HMM **calibrato** | 📋 rinviato — questo TODO |
| 5 | Heston / Bates / Merton (volatilità stocastica, salti) | 📋 rinviato — questo TODO |

### Livello 2 — GJR-GARCH: perché è uscito dalla v1

**Data**: 17 Settembre 2026 · misurato su QuantLib 1.43, non dedotto.

Il piano dava per scontato che il GJR-GARCH fosse «nativo QuantLib, calibrabile
dalla sola serie prezzi». **È falso.** Misura eseguita sul runtime reale:

```text
hasattr(ql, 'Garch11')                              -> False
GJRGARCHModel.calibrate(self, CalibrationHelperVector, OptimizationMethod, ...)
issubclass(GJRGARCHProcess, ql.StochasticProcess1D) -> False    factors() -> 2
```

Due fatti, entrambi bloccanti:

1. `ql.GJRGARCHModel` è un modello di **pricing di opzioni**: il suo
   `calibrate()` accetta `CalibrationHelperVector`, cioè quotazioni di opzioni —
   la stessa identica API di `HestonModel`. `GJRGARCHProcess` **pretende**
   `v0, omega, alpha, beta, gamma, lambda` già stimati. L'obiezione con cui
   questo stesso documento rinvia il livello 5 («richiede una superficie di
   volatilità implicita da opzioni») si applica **identica** al livello 2.
2. `ql.Garch11` — l'unica classe QuantLib che calibra per massima verosimiglianza
   da una serie di **rendimenti** — non è esposta nei binding Python SWIG.
   Esiste in C++, non nel nostro runtime.
3. Anche avendo i parametri, `GJRGARCHProcess` non entra nell'architettura
   attuale: non è un `StochasticProcess1D` e ha due fattori, mentre il motore
   costruisce `StochasticProcessArray`, che accetta **solo** componenti 1-D.

### La strada, quando si riaprirà

La libreria `arch` fa esattamente ciò che serve: un GJR-GARCH(1,1,1) su 1 250
osservazioni si stima in **22 ms**. È già presente nell'ambiente come
**dipendenza transitiva** di `riskfolio-lib` (`arch>=7.0`), ma **non è dichiarata
nel `Pipfile`**.

Nessuna delle due scorciatoie è accettabile:

- **appoggiarsi alla transitiva** significa che il giorno in cui `riskfolio-lib`
  smette di dipendere da `arch`, il nostro GARCH sparisce **senza che nulla
  fallisca** in modo visibile;
- **promuoverla al volo** tocca l'ambiente Python condiviso da tutte le lane di
  sviluppo attive, e va fatto dal developer a lane congelate.

Precondizione per riprendere il livello 2: `arch` promossa a dipendenza diretta
in `Pipfile` con lock rigenerato. Da lì il lavoro è contenuto — univariato
sull'aggregato di portafoglio, innestato sul campionatore esistente.


### Preset di crisi — la forma preferita per il seguito

Il preset «crisi prolungata» consegnato in v1 usa un **pavimento scalare**:
oscillazioni ×2,5 e deriva −20% annuo applicate ai blocchi ricampionati. È
onesto — l'ipotesi è dichiarata a schermo con i suoi numeri — ma i numeri sono
**prescritti**, non osservati.

La forma preferita, quando si riaprirà, è il **ricampionamento condizionato**:
estrarre i blocchi **solo** dalle finestre del decile peggiore della storia
reale del portafoglio. Il vantaggio non è di precisione, è di natura:

- l'ipotesi a schermo non conterrebbe **nessun numero dichiarato** — direbbe
  «ricampionati i tuoi periodi peggiori», e sarebbe verificabile dall'utente;
- la correlazione salirebbe **perché è salita davvero** nelle crisi vissute da
  quel portafoglio, invece di restare invariata come impone una trasformazione
  scalare (vedi la nota su `resampling.py`: su un ricampionamento congiunto
  scalare e traslare lasciano la correlazione di Pearson matematicamente
  invariata).

Condizione vincolante, da rispettare il giorno in cui si implementa: se la
storia disponibile **non contiene** un periodo abbastanza severo, il risultato
**si dichiara**, non si fabbrica. Un decile peggiore calcolato su tre anni di
mercato toro non è una crisi, ed è esattamente il tipo di numero che questa
campagna esiste per non produrre.

### Livello 4 — Markov-switching calibrato

Concettualmente è la risposta esatta a «simula i cambi di fase di mercato»: due o tre
regimi (calma / stress / crisi), ciascuno con media, volatilità e matrice di
correlazione proprie, più una matrice di probabilità di transizione stimata dai dati.

Rinviato perché con la storia tipicamente disponibile a un privato (3-5 anni) la stima
EM **overfitta**: i regimi trovati esistono solo nel campione e cambiano se sposti la
finestra. Richiederebbe inoltre `hmmlearn` o `statsmodels` (QuantLib non lo supporta
nativamente).

Precondizioni per riprenderlo: storia lunga e verificata, diagnostica di stabilità dei
regimi fra finestre diverse, e una presentazione che dichiari l'incertezza della stima
invece di nasconderla.

### Livello 5 — Heston / Bates / Merton

QuantLib li supporta nativamente (`HestonProcess`, `BatesProcess`, `Merton76Process`),
ma la loro calibrazione richiede una **superficie di volatilità implicita da opzioni**,
dato che LibreFolio non ha e non prevede di avere. Usarli con parametri inventati
produce sofisticazione apparente senza contenuto informativo.

Da riprendere **solo** se in futuro esistesse una fonte dati di opzioni; altrimenti
resta fuori scope in modo permanente.

### Riferimenti

- `backend/app/services/risk/quant/quantlib_worker.py`
- `backend/app/services/risk_plugins/simulation.py`

---

## 📈 Gestione Stock Splits nel Calcolo FIFO

**Data aggiunta**: 10 Giugno 2026
**Priority**: Bassa (P4)
**Scope**: Backend (Servizi Matematici)

### Contesto
Attualmente il sistema di calcolo FIFO in `fifo_utils.py` accetta in input esclusivamente operazioni di `BUY` e `SELL`. Nel mondo reale, avvengono frequentemente frazionamenti azionari (Stock Splits, es. Apple 1:4).
A livello teorico uno Stock Split non altera i capitali investiti né crea o distrugge valore monetario, ma **altera retroattivamente i lotti**. Se non gestiti, un utente che tenta di vendere 4 azioni (nate da uno split 1:4 di 1 azione acquistata) manderà il FIFO in `ValueError` per "Oversell".

### Soluzione Proposta
1. Aggiungere un nuovo `TransactionType.SPLIT` al modello dati backend.
2. Modificare il motore FIFO: quando incontra cronologicamente un'operazione `SPLIT` con un determinato `ratio` (es. 4):
   - Mette in pausa il normale match BUY/SELL.
   - Itera su tutti i lotti "aperti" (Open Lots) in quella esatta data.
   - Moltiplica la `remaining_quantity` di ogni lotto per il `ratio`.
   - Divide il `buy_price` originale di ogni lotto per il `ratio`.
   - Riprende l'elaborazione cronologica.
3. Questo garantisce che eventuali `SELL` successivi trovino le quantità corrette ed estraggano capital gain esatti.
4. Prevedere anche la gestione di Reverse Splits (ratio < 1).

### Verifica 17 Luglio 2026 — risolta la domanda gemella ("basta ADJUSTMENT?")
Risposta: **no, serve SPLIT esplicito.** `ADJUSTMENT` esiste già ed è documentato anche per "splits, gifts, etc." (`models.py:221-225`), ma il motore FIFO (`fifo_utils.py`) filtra solo BUY/SELL — un ADJUSTMENT non tocca la coda dei lotti. Prova diretta nel codice: il messaggio d'errore di oversell dice letteralmente *"Possible unrecognized stock split or missing BUY transactions"* (`fifo_utils.py:103`) — il bug è reale e già "annunciato" dal sistema stesso. TODO confermato pienamente valido, non risolvibile con l'infrastruttura attuale.

---

## 📦 TanStack Table v9 Migration

**Data aggiunta**: 22 Gennaio 2026  
**Status**: ⏳ IN ATTESA (v9 in alpha)  
**Priorità**: Bassa (fino a release stabile)

### Contesto

Abbiamo scelto di usare **TanStack Table v8** con un **adapter custom Svelte 5** invece dell'adapter ufficiale `@tanstack/svelte-table` per i seguenti motivi:

1. **v8 adapter ufficiale** (`@tanstack/svelte-table`): Non compatibile con Svelte 5 (usa API interne Svelte 3/4)
2. **v9 con supporto Svelte 5**: Ancora in versione **alpha** (`9.0.0-alpha.x`)

### Soluzione Attuale

- **Libreria**: `@tanstack/table-core@^8.21.3` (stabile)
- **Adapter**: Custom in `frontend/src/lib/tanstack-table/`

### Azione Futura

Quando TanStack Table v9 sarà **rilasciato come stabile** con supporto ufficiale Svelte 5:

1. Installare l'adapter ufficiale `@tanstack/svelte-table`
2. Aggiornare import in tutti i componenti
3. Rimuovere la cartella `src/lib/tanstack-table/` (adapter custom)
4. Testare tutte le tabelle (Files, Assets, Transactions, FX)

---



## 🔒 Ripensare struttura di accesso ai broker Utente-SuperUtente per essere GDPR compliant

**Data aggiunta**: Gennaio 2026  
**Status**: 📋 PIANIFICATO → Architettura definita in `plan-phase05-to-08-upgrade.md` §10 (GDPR/Sharing)  
**Priorità**: Media

### Contesto
La visibilità dei dati di altri utenti da parte del superuser deve essere ripensata per essere GDPR compliant.

### Possibili Approcci
- Superuser non vede dati personali di altri utenti senza consenso esplicito
- Log di accesso ai dati di altri utenti
- Anonimizzazione dei dati visualizzati (solo statistiche aggregate)
- Meccanismo di "data request" invece di accesso diretto (utente concede accesso all'assistenza per x tempo)

---

## 🏦 Regime Fiscale — Metodo di Vendita (FIFO, LIFO, PMC, Select ID)

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Alta (architettura core)

> **Cross-link**: stesso motore FIFO (`fifo_utils.py`) del TODO "BRIM: FEE/TAX non collegati all'asset" qui sopra — entrambi toccano come i lotti calcolano il proprio cost basis. Da coordinare se pianificati insieme.

### Contesto
Diverse giurisdizioni usano metodi diversi per determinare quale lotto vendere in caso di vendita parziale:
- **Italia**: Prezzo Medio di Carico (PMC)
- **USA**: FIFO, LIFO, Select ID (scelta specifica dell'utente)
- **Altre**: HIFO (Highest In First Out), etc.

### Requisiti
1. **Impostazioni Broker**: Nella zona short/long del broker, selettore per il metodo di vendita supportato (FIFO, LIFO, PMC, Select ID)
2. **Preferenze Utente**: Impostazioni di default per metodo di vendita
3. **Impostazioni Admin**: Default globale per nuovi utenti
4. **Collegamento Transazioni**: Il sell deve essere collegato ai buy tramite `link_transactions_id`:
   - FIFO/LIFO: collegamento algoritmico
   - Select ID: scelto dall'utente
   - PMC: nessun collegamento (calcolo on-the-fly)

### Note Tecniche
- Analizzare le strade per lo split dei buy: slittare buy e connettere la parte residua, tabella di appoggio, lista di link
- Deve essere possibile identificare transazioni già importate per evitare doppio import
- Per PMC il problema del collegamento non sussiste, basta calcolare il valore on-the-fly
- I plugin BRIM in fase di vendita devono fornire un dizionario di remap con le transazioni linkate più probabili
- Il vincolo di over-sell va esteso nell'import

---

## 💸 PAC/Rebalancer — Profili Commissionali Avanzati per Broker e Mercato

**Data aggiunta**: 15 Settembre 2026
**Status**: 📋 FUTURO — estensione successiva al primo planner operativo
**Priorità**: Media

**Target v1 correlato:** [suite PAC/Rebalancer — piano maestro](LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerTargetDesign.prompt.md).

### Confine della Prima Versione

Il primo planner PAC/Rebalancer deve mantenere due profili indipendenti,
`fee_buy` e `fee_sell`. Ciascuno supporta:

- componente fissa;
- componente percentuale sul controvalore;
- minimo e massimo opzionali per la componente percentuale;
- valore `0` valido.

Questa separazione copre i PAC con acquisti gratuiti e vendite soggette alle normali
commissioni. Non implica ancora regole diverse per mercato o formule dipendenti dalla
sequenza giornaliera degli ordini.

### Estensioni Future

- Override dei profili per mercato, sede di negoziazione o classe di strumento.
- Profili dinamici/degressivi nei quali la fee dipende dal numero progressivo degli
  eseguiti nella giornata.
- Calendario, timezone, valuta, data di validità e provenance del tariffario.
- Regole esplicite per eseguiti parziali, ordini annullati e conteggi condivisi fra
  mercati/strumenti.
- Integrazione nel solver: una tariffa dipendente dal numero d'ordine rende il costo
  non separabile e richiede di ottimizzare anche sequenza e numero degli ordini.

Directa documenta, per alcuni mercati, un profilo dinamico giornaliero che parte da
8 EUR sul primo eseguito, scende progressivamente fino a 3 EUR dal 6° al 25°, passa a
2 EUR dal 26° al 50° e a 1,50 EUR dal 51°; disponibilità e valori dipendono dal mercato.
Questa famiglia di policy non rientra nella prima versione.

### Gate Futuri

- Nessuna tariffa implicita o scelta automaticamente senza conferma utente.
- Distinguere ordine pianificato da eseguito reale: il planner non deve fingere di
  conoscere il contatore giornaliero.
- Mostrare profilo, mercato, data e assunzioni usate nel costo stimato.
- Testare discontinuità delle soglie, min/max, BUY/SELL e pareggi fra Broker.

### Riferimenti

- [Directa — Commissioni](https://www.directa.it/commissioni), consultato il
  15 settembre 2026.

---

## 🧭 PAC/Rebalancer — Profili Persistenti e Strategie Estese

**Data aggiunta**: 15 Settembre 2026
**Status**: 📋 FUTURO — fuori dal primo planner operativo
**Priorità**: Media

**Target v1 correlato:** [suite PAC/Rebalancer — piano maestro](LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerTargetDesign.prompt.md).

### Confine della Prima Versione

La prima versione mantiene nello snapshot del singolo calcolo:

- parametri operativi dei Broker;
- fee BUY/SELL;
- supporto agli ordini frazionati e relativo step monetario;
- regime fiscale e minusvalenze pregresse;
- aliquota sulle plusvalenze per Asset, pre-popolata al `26%` e modificabile;
- route Asset×Broker e priorità;
- trasferimenti dichiarati, gratuiti e immediati;
- FX single-hop e `fx_buffer_rate` esplicito (label UI “Margine di sicurezza FX”).

Questi dati non diventano automaticamente impostazioni persistenti. Il Tool resta
atomico e riceve sempre uno snapshot completo.

### Persistenza da Valutare

1. **Profilo operativo personale del Broker**
   - salvare per utente×Broker valute operative, FX mode, supporto frazioni,
     step monetario, min/max, fee BUY/SELL, regime e minus pregresse;
   - usare il profilo solo come prefill modificabile del singolo scenario;
   - non trasformarlo in un lookup del worker Tool;
   - mantenere i Broker manuali scenario-only salvo futura azione di salvataggio
     esplicita.
2. **Aliquota plusvalenze sull'Asset**
   - aggiungere un campo Asset configurabile e versionabile;
   - pre-popolare il planner dal dato persistito, con origine/data visibili;
   - mantenere override per-run;
   - definire default, permessi, provenienza e migrazione prima di aggiungere la
     colonna.

### Strategie Future

- Distribuzione proporzionale esplicita degli acquisti fra più Broker.
- Vendita proporzionale dello stesso Asset fra più custodie.
- Chiusura Broker: svuotamento controllato di una custodia.
- Consolidamento: trasferire il portafoglio verso uno o più Broker scelti.
- Minimizzazione delle plusvalenze realizzate.
- Compensazione di minusvalenze pregresse con plus compatibili.
- Tax-loss harvesting e minimizzazione del realizzo fiscale.
- Bucket di minusvalenze per categoria, compensabilità e scadenza.

### Modello Operativo Futuro

- Fee, limiti e tempi di settlement dei trasferimenti.
- Route FX multi-hop, solo con protezioni anti-ciclo e anti-arbitraggio.
- Buffer FX dinamico per Asset/volatilità invece del solo `fx_buffer_rate`
  esplicito.
- Persistenza opzionale delle fonti manuali.

Profili commissionali per mercato e formule intraday/degressive sono già descritti
nella sezione precedente e non vengono duplicati qui.

### Gate Futuri

- Nuova review matematica se cambiano input, vincoli, fiscalità, fee, FX o
  obiettivi.
- Nessuna compensazione fiscale senza categoria dello strumento, regole di
  compensabilità, scadenza, regime e perimetro Broker espliciti.
- Nessun profilo persistito può diventare un default silenzioso: provenance,
  data e override per-run restano visibili.
- Le strategie di chiusura/consolidamento non possono introdurre short, leverage,
  BUY+SELL dello stesso Asset o vendite oltre inventario.

### Riuso futuro del solver discreto — senza migrazione Riskfolio

PySCIPOpt/SCIP è il candidato additivo approvato per il planner fixed-L2
(primo tier MIQP, tier lessicografici successivi convex-MIQCP); la dipendenza non
è ancora installata e resta subordinata al freeze coordinato, all'update
developer-owned/autorizzato e ai gate packaging/capacità. Dopo l'adozione
effettiva, valutarne il riuso solo
per nuovi problemi realmente misto-interi: cardinalità, lotti minimi, turnover,
costi fissi, distribuzione proporzionale BUY/SELL fra Broker, chiusura o
consolidamento di custodie, strategie fiscali discrete, fee dipendenti dalla
sequenza e routing operativo di trasferimenti, settlement e FX.

Riskfolio-Lib resta il motore di dominio per covariance, risk parity, frontiera
efficiente e analisi rischio; SciPy resta disponibile per XIRR e calcolo numerico.
Non reimplementare queste funzioni per eliminare una dipendenza. Un eventuale
secondo backend richiede spike separato, parità completa degli output esistenti e
benchmark che dimostri un vantaggio misurabile di capacità, latenza o memoria.

---

## 🤖 QuarkAI — Assistente AI (MCP Server)

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Bassa (futuro)

### Contesto
Creare un assistente AI basato su MCP server chiamato "QuarkAI".

### Funzionalità Future
- Raccolta automatizzata notizie mercati azionari
- Notifiche su Telegram (o simili) quando rileva eventi che richiedono attenzione
- Recap giornaliero (es. alle 20:00) con sommario eventi rilevanti

---

## 📁 Template per Nuovi TODO

```markdown
## 📌 [Titolo]

**Data aggiunta**: [Data]  
**Status**: [⏳ IN ATTESA | 📋 PIANIFICATO | 🔄 IN CORSO | ✅ COMPLETATO]  
**Priorità**: [Alta | Media | Bassa]

### Contesto
[Descrizione del problema o motivazione]

### Azione Futura
[Passi da eseguire quando sarà il momento]

### Riferimenti
[Link a documentazione, issue, PR]
```

---


## 🔍 BRIM Auto-Detect Broker via Account Code

**Status**: ❌ SCARTATA (07/09/2026, decisione utente) — pochi broker rilasciano dati che
identificano il conto, e l'utente divide già da sé i file in fase di upload. Nessuna azione;
registrata qui solo perché l'idea non ritorni.

## 💰 Futura policy cedola (coupon_policy)

**Data aggiunta**: 3 Aprile 2026 (Round 12 Finale)
**Status**: 📋 IDEA FUTURA
**Priorità**: Bassa

### Concetto

Colonna `coupon_policy` su `FAInterestRatePeriod` con opzioni:
- **FULL_RESET** (attuale): torna a `initial_value` dopo coupon
- **CUSTOM_RATE**: tasso cedola diverso dal tasso di accumulo
- **PARTIAL**: percentuale del valore accumulato

Per ora solo FULL_RESET è implementato.

---

## 🗄️ Cache Server Centralizzato per Multi-Worker Uvicorn

**Tema correlato (da fare PRIMA o insieme)**: audit del **necessario delle cache** — con il
pannello admin (P2-4, 03/09) ora si vedono tutte le 16 cache nominali in un colpo d'occhio.
Prima di investire nella condivisione multi-worker, vale la pena spendere tempo a capire se
servono tutte o se ci sono refusi storici (cache aggiunte per colli di bottiglia poi spariti,
TTL mai rivisti, cache mai popolate davvero). Il pannello "Server Caches" in Global Settings
è lo strumento di osservazione già pronto per questa analisi (size/TTL/hit per nome).

**Fuse qui (07/09) le code residue della voce "Web search / link-finder"** (voce eliminata:
la parte search è completa con `ddgs`): (a) la cache dei risultati del link-finder
(`web_link_finder._cache`) è un dict in-process → non condivisa tra worker: valutarla dentro
questo stesso studio (TTL/invalidazione, degradazione graceful al dict in-process se nessuna
cache esterna è configurata); (b) la Fase B SearXNG resta archiviata
(`phases/04_webSearchEngine/`) come riferimento se mai servisse un primario self-hosted —
nessuna azione finché `ddgs` regge.
**Nota**: questa voce chiede l'analisi, non la soluzione.

**Data aggiunta**: 14 Aprile 2026  
**Status**: 📋 PIANIFICATO (quando si passerà a multi-worker)  
**Priorità**: Bassa (oggi 1 worker è sufficiente con SQLite)

### Contesto

Le cache in-memory (theine) sono per-processo. Con `--workers 1` (default attuale) funzionano perfettamente. Con `--workers N` (N > 1), ogni worker ha la propria cache isolata: un cache miss su worker 2 non beneficia di un cache hit su worker 1. Uvicorn non garantisce sticky sessions.

### Soluzione Proposta

Spawning di un **processo cache dedicato** dal `lifespan()` di FastAPI, che usa theine internamente e espone un'interfaccia socket Unix ai worker via `multiprocessing.managers.BaseManager`:

```
┌─────────────────────────────────────────────────┐
│  uvicorn master process                          │
│  └── lifespan() spawna CacheServer process       │
│       ├── theine Cache instances (in-memory)     │
│       └── Unix socket /tmp/librefolio-cache.sock │
├──────────────────────────────────────────────────┤
│  Worker 1 ──proxy──┐                             │
│  Worker 2 ──proxy──┼──► Unix socket ──► CacheServer
│  Worker N ──proxy──┘                             │
└──────────────────────────────────────────────────┘
```

### Implementazione (~100 righe)

1. **`backend/app/utils/cache_server.py`** (nuovo): `CacheManager(BaseManager)` con metodi `cache_get/set/delete/clear/get_or_create` registrati. Il server process usa theine direttamente.

2. **`cache_utils.py`**: `NamedCache` riceve un flag `_remote_manager`. Se attivo, delega get/set/delete via proxy al cache server. Se non attivo (single-worker), usa theine locale come oggi. Zero cambiamenti nei callsite (`get_ttl_cache()` API invariata).

3. **`main.py` `lifespan()`**: Se `workers > 1`, spawna il cache server subprocess prima di avviare l'app. Passa l'indirizzo socket via env var. Shutdown: termina il subprocess.

### Trade-off

- **Latenza**: ~200-500μs per op (vs ~1μs theine locale). Irrilevante per cache di API call da 1-5s.
- **Serializzazione**: Valori devono essere pickleable (Pydantic model, dict, list — tutti OK).
- **Fault tolerance**: Se il cache server crasha, i worker perdono solo la cache (no data loss). Restart automatico possibile.
- **Alternativa**: `diskcache` (SQLite+filesystem, process-safe, ~50μs, ma persistente — non necessario).

### Prerequisiti

- Passaggio a **PostgreSQL** (SQLite non supporta bene multi-writer)
- Necessità reale di N > 1 worker (>50 utenti concorrenti)

### File coinvolti

- `backend/app/utils/cache_server.py` (nuovo)
- `backend/app/utils/cache_utils.py` (adattare `NamedCache`)
- `backend/app/main.py` (spawn/shutdown cache process)


---

## 📅 Scheduled Investment — Frequenze disaccoppiate (prezzi vs cedola) + anchor day

**Data aggiunta**: 24 Aprile 2026 (retest Batch 4 sezione 3)
**Status**: ⏳ IDEA — non in roadmap immediata
**Priorità**: Media (UX, non bloccante)

### Contesto

Durante il retest del fix I-bis #26 (Batch 4.c — riordino Step 2/4 in
`scheduled_investment.py`) è emerso un limite di design attuale del
provider `scheduled_investment`:

> **La frequenza di generazione dei prezzi coincide con la frequenza di
> maturazione della cedola** (`maturation_frequency`). Attivando
> `generate_interest=True`, ogni volta che viene generato un evento
> INTEREST il valore si resetta al principal. Non esiste oggi un modo
> per scegliere _separatamente_ la granularità del grafico prezzi e la
> frequenza di payout.

Inoltre la data in cui cade la cedola (anchor day of month / week /
year) è determinata dalla `start_date` del periodo — non c'è controllo
UX su "cedola ogni 1 del mese" o "cedola ogni lunedì" indipendentemente
da quando parte lo schedule.

### Cosa serve (design a alto livello)

**Schema Pydantic** (`FAInterestRatePeriod`):
- `price_frequency: MaturationFrequency` — granularità grafico (DAILY
  come default ragionevole).
- `coupon_frequency: MaturationFrequency | None` — **solo se**
  `generate_interest=True`; disaccoppiata da price_frequency.
- `coupon_anchor: CouponAnchor | None` — enum opzionale:
  - `SCHEDULE_START` (comportamento corrente: conta dalla start_date)
  - `FIRST_OF_MONTH` / `LAST_OF_MONTH`
  - `SPECIFIC_DAY_OF_MONTH(day: int 1-28|"last")`
  - `SPECIFIC_WEEKDAY` (MON..SUN)
  - `SPECIFIC_DATE(month: int, day: int)` per ANNUAL/SEMIANNUAL
- Validator Pydantic: `coupon_frequency` e `coupon_anchor` devono
  essere coerenti (es. `SPECIFIC_WEEKDAY` solo con WEEKLY,
  `SPECIFIC_DATE` solo con ANNUAL/SEMIANNUAL).

**Engine** (`_generate_schedule_values`):
- Calcolare due set di date separati:
  `price_emission_dates` (dal `price_frequency`) e `coupon_dates`
  (dal `coupon_frequency + coupon_anchor`, se abilitati).
- Step 3 (emit value) ora su `price_emission_dates` invece di
  `all_maturation_dates`.
- Step 4 (auto-coupon reset) ora su `coupon_dates` invece di
  `all_maturation_dates`.
- I due set possono sovrapporsi (es. DAILY prezzi + MONTHLY coupon:
  ogni giorno ha un punto, solo il 1° del mese c'è anche il reset).

**Frontend** (`ScheduledInvestmentEditor`):
- Nuova riga per `price_frequency`.
- Riga condizionale `coupon_frequency` (visibile solo se
  `generate_interest=true`).
- Nuovo campo `coupon_anchor` con tendina contestuale
  (day-of-month picker per MONTHLY, weekday picker per WEEKLY, ecc.).
- Retrocompatibilità: se `price_frequency` manca nello schema JSON
  esistente → migrare a `price_frequency = maturation_frequency`
  (no breaking change per gli asset già configurati).

### Benefici attesi

- **UX**: un utente può vedere l'andamento daily del grafico anche se
  la cedola è pagata semestralmente (oggi il grafico è sparso su 2
  punti/anno, confondendo chi guarda).
- **Modello fedele**: BTP Italia 2028 ha cedole semestrali ma il
  valore di mercato varia ogni giorno — dovremmo riflettere entrambi
  i ritmi.
- **Anchor date**: un'obbligazione che paga cedola il 15 marzo e 15
  settembre NON può oggi essere modellata fedelmente se l'asset è
  stato "creato" con start_date diversa da quelle.

### Non in questo plan perché

- Estende schema Pydantic + migrazione dati esistenti +
  retrocompatibilità — costo 4-6h.
- Aggiunge ~3 campi FE + validazione contestuale — costo 3-4h.
- Test coverage estesa (cross-product di freq × anchor × event types).
- **Non bloccante**: il comportamento attuale è coerente se
  `generate_interest=False` (retta crescente pulita) o se l'utente
  accetta la coincidenza prezzi/cedola.

### File candidati (quando si apre il ticket)

- `backend/app/schemas/assets.py` — `FAInterestRatePeriod`,
  nuovo enum `CouponAnchor`.
- `backend/app/services/asset_source_providers/scheduled_investment.py`
  — Step 3/4 rifattorizzati.
- `frontend/src/lib/components/assets/editors/ScheduledInvestmentEditor.svelte`.
- Test: `test_synthetic_yield_integration.py` — parametric su
  `(price_frequency, coupon_frequency, coupon_anchor)`.
- Alembic: **nessuna** migrazione (campo in JSON `provider_params`,
  retro-compat via default sull'assenza).

### ⚠️ Caveat current_price (retest Batch 4, 2026-04-24)

Durante il retest 3.2/3.3 (BTP DAILY/WEEKLY regen) è emerso che il
**current_price** del provider Scheduled Investment **non è ancora
del tutto coerente con gli eventi intermedi** (coupon reset +
price_adjustment) quando la frequenza coupon e la frequenza prezzi
sono disaccoppiate — anche dopo i fix #R6-2 (`_compute_value_at`
backward-walk) e #R6-4 (event wipe simmetrico).

**Sintomo osservato**: dopo rigenerazione DAILY/WEEKLY il chart
storico è corretto (sawtooth visibile), la tab Events è pulita
(niente coupon stantii), ma il **valore "oggi"** mostrato nelle
card asset può divergere rispetto a quanto ricostruibile a mano
dalla schedule — tipicamente perché il ramo "intra-cycle" di
`get_current_value` assume coincidenza tra evento coupon e punto
di emissione prezzo, che nel modello disaccoppiato non vale più.

**Cosa fare quando si apre il ticket #R6-3**:

1. **Ripensare `get_current_value`** insieme a `_compute_value_at`:
   deve camminare lo schedule reale con i due set indipendenti
   (`price_emission_dates` ≠ `coupon_dates`) e applicare gli
   eventi nel loro ordine cronologico reale, non presumendo
   lockstep.
2. **Estendere `test_synthetic_yield_integration.py`** con casi
   parametrici che verifichino `current_price` in date "scomode":
   - il giorno dopo un coupon (deve scendere)
   - a metà ciclo con rateo parziale
   - nel gap tra due price-emission date consecutive (nessun
     evento nel mezzo)
   - con `price_frequency=DAILY` + `coupon_frequency=ANNUAL`
     (il caso realistico BTP) — verifica che il valore cambi
     ogni giorno ma il reset avvenga solo alla data cedola.
3. **Includere `current_price` nella matrice di regressione** del
   provider, non solo gli storici. Oggi le 4 regression aggiunte
   in 4.c coprono solo il passato.

### Cross-link

- Rilevato durante retest Batch 4 sezione 3 (I-bis #26):
  [`LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure_2.prompt.md`](LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure_2.prompt.md)
  §"Retest Batch 4 — sezione 3".
- Fix correlato già applicato in 4.c:
  `_generate_schedule_values` Step 2/4 reorder — emette valore
  pre-reset.

---

## ⚡ Migrazione a ORJSONResponse per performance JSON

**Data aggiunta**: 11 Giugno 2026
**Priority**: P4 (ottimizzazione, non urgente)
**Scope**: Backend (`app/main.py`, serializzazione)

### Contesto

`orjson` è un serializzatore JSON scritto in Rust, 5–10× più veloce di `json` stdlib per la serializzazione e 2–3× per la deserializzazione. FastAPI supporta nativamente `ORJSONResponse` come `default_response_class`.

### Problema attuale: incompatibilità con `SafeDecimal`

Il progetto usa `SafeDecimal = Annotated[Decimal, PlainSerializer(..., when_used="json")]` su tutti gli schemi di transazioni, FX e portafoglio. Questo `PlainSerializer` garantisce che i `Decimal` arrivino al frontend come stringhe senza notazione scientifica (es. `"0.00500000"` invece di `5e-3`).

**`orjson` bypassa i `PlainSerializer` di Pydantic** quando serializza direttamente, convertendo i `Decimal` in float nativi — con rischio di perdita di precisione e notazione scientifica silenziosa sul frontend.

### Come implementarlo correttamente

Non è sicuro usare `ORJSONResponse` come `default_response_class` senza prima risolvere questo punto. Le opzioni:

1. **Subclass `ORJSONResponse`** che chiama `model.model_dump(mode='json')` prima di passare a `orjson` → applica i `PlainSerializer` prima della serializzazione Rust.
2. **Custom `orjson` default function** che intercetta `Decimal` e lo serializza come stringa.
3. **Rendere `orjson` l'encoder di Pydantic v2** via `model_config = ConfigDict(json_encoders=...)` — ma deprecato in v2.

**Approccio consigliato**: opzione 1. Creare `SafeORJSONResponse(ORJSONResponse)` che fa `jsonable_encoder(content)` prima di `orjson.dumps()`, e usarla come `default_response_class`.

### Benefici attesi

Endpoint pesanti (bulk import, FIFO calc, portfolio summary) potrebbero guadagnare 20–50ms su payload grandi. Serializzazione nativa di `datetime`, `UUID`, `Enum` senza `jsonable_encoder`.

### Prerequisiti

- Test coverage sugli endpoint con campi `SafeDecimal` per verificare output identico
- Benchmark prima/dopo su `/api/v1/transactions` con dataset reale

---

Aree di miglioramento dopo aver visto compeditor:
Tra i provider di prezzo, oltre ai siti da aumentare, ha senso fare olgre al css selector (che potrebbe essere rinominato web page) anche json api, html table e csv
aggiungere i provider AI, olre a ollama e openrouter, anche tutti gli altri per l'installazione locale.
pensare un sistema di addon che permetta al forontend di aggiungere tab. Capendo come creare un market place.
aggiungere nella dashboard e nei broker dei tab che fanno anche altri tipi di analisi oltre quelli pensati. Altri tipi di analisi restano da definire (allocazione % con quadrettoni/treemap già fatta, vedi TODO_Completati.md).
La vecchia idea di target allocation per Broker è ora precisata nella sezione
“PAC/Rebalancer — Profili Persistenti e Strategie Estese”: la v1 usa target
globali per Asset e route/priorità; una distribuzione proporzionale esplicita per
Broker resta futura.
Aggiungere la possibilità di creare "Portafogli" che dovrebbero essere gruppi di broker o asset o entrambi, da approfondire.
Fare delle pagine di dettaglio per analizzare i trade, le fee 
Aggiungere un calcolatore FIRE non solo da oggi al futuro, ma anche fissando una data di inizio per aver modo di vedere la differenza tra andamento teorico e reale.


---

## Risk Analysis

### RQMC with explicit scrambling contract (low priority — 2026-07-28)
- **What**: re-evaluate randomized quasi-Monte Carlo only when the QuantLib Python
  binding exposes a complete scrambling path suitable for production.
- **Why deferred**: production now supports MC and QMC entirely in QuantLib. The
  previous SciPy RQMC path was removed, and its overloaded `seed` mixed random seed,
  Sobol offset and scrambling semantics.
- **Required contract**: separate scramble seed from `sobol_start_index`; never
  overload either field.
- **Required gate**: convergence across randomized replicates, QuantLib-only
  execution inside the `spawn` worker and no silent SciPy production fallback.
- **Trigger to revisit**: a newer QuantLib binding exposes the required scrambling
  primitives or a separately approved production engine is adopted.

### Dynamic scenario catalog (future — 2026-07-29)
- **What**: evolve the initial static, typed, startup-loaded built-in/host YAML
  catalog with file detection without restart, manual/hot reload, personal
  scenario CRUD, persistence of UI edits, YAML import/export, explicit built-in
  overrides and administrative diagnostics.
- **Why deferred**: G6 first needs a small deterministic contract with no database,
  watcher or generic form engine.
- **Trigger to revisit**: the static catalog and typed editors are stable in
  production and users need scenario lifecycle management.
- **Reference**:
  `Phase_0/02_riskfolioIntegration/plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md`.

### Persistent historical-replay proxies (future — 2026-07-29)
- **What**: persist asset→proxy associations, optionally propose proxies only with
  explicit user confirmation, and reuse confirmed mappings in later replays.
- **Why deferred**: G6 deliberately keeps proxy choice explicit and ephemeral;
  automatic or silent substitution is forbidden.
- **Trigger to revisit**: repeated replay use demonstrates stable, auditable proxy
  mappings and the persistence UX has been designed.

---

## 💱 Settlement multicurrency ed esposizione — feedback 2026-09-08

**Status**: FUTURO — progettazione separata, non autorizzata come hotfix del parser.
**Origine**: nuovo feedback utente del 2026-09-08; correzioni urgenti import/asset/FX
affidate alla corsia E in un worktree separato. Qui si tracciano soltanto i tre temi
architetturali rinviati; le altre voci di questo file restano invariate.

### F-MC-1 — Acquisti multicurrency con conversione del broker “on-the-fly”

**Problema riportato:** alcuni broker convertono liquidità al momento dell'acquisto
senza una riga FX separata nel ledger. Una rappresentazione incompleta o una valuta cash
attribuita male può portare il consistency checker a rilevare cassa negativa.

**Target:** rappresentare correttamente il settlement multicurrency e, se necessario,
una policy esplicita per i broker interessati, senza perdere conservazione e audit dei saldi.

**Prima del design:** distinguere valuta della quotazione dell'asset, valuta del cash
effettivamente addebitato e valuta di regolamento. Verificare quanto il modello corrente
già supporta e quanto invece manca nel report/parser; non assumere che ogni acquisto
di un asset quotato in USD debba addebitare una cassa USD.

**Gate e rischi:** scegliere fonti e struttura delle eventuali gambe di settlement,
date, arrotondamenti e costi; mantenere quantità/importi originali e tracciabilità.
Credito/margine o permesso di saldo negativo non sono sinonimi di conversione implicita.
Niente disabilitazione del checker o deposito inventato per nascondere un deficit.

**Superfici candidate:** schemi transazione, normalizzazione BRIM/core, paired-leg
workflow, validazione saldi e wizard. Piano dedicato dopo esempi reali anonimizzati;
nessuna nuova conversione dentro il parser in questa tornata.

### F-MC-2 — Proposte FX automatiche opt-in per import Generic CSV

**Idea:** offrire un toggle che proponga transazioni collegate di cambio valuta per
deficit di liquidità spiegabili da conversioni non esplicitate nel file.

**Confine:** generazione in uno strato di preparazione/core o nel workflow di review,
DOPO la trascrizione del CSV. **BRIM resta un parser verbatim: niente FX o ricalcolo
monetario nel plugin.** Le proposte entrano nel draft normale della bulk, non in un
nuovo percorso di commit nascosto.

**Dati:** riusare il motore FX e i tassi storici disponibili (BCE quando pertinente,
con fonti/fallback già supportati), indicando data, provenance e staleness. Un tasso
stimato non va presentato come quello realmente applicato dal broker.

**Gate:** scelta esplicita di valuta/conto di finanziamento, fondi disponibili, date,
fee e rounding; preview modificabile/rifiutabile prima del salvataggio. Mancanza dati
o fondi resta un problema visibile. Reparse/riprova non deve duplicare gambe già presenti
o approvate; conservare collegamento alla motivazione e alla riga originaria.

**Dipendenza:** chiarire il modello F-MC-1 e la distinzione fra ricostruzione documentata
e simulazione assistita. Nessuna generazione FX automatica autorizzata dai bug E1-E4.

### F-MC-3 — Valuta base dell'asset ed esposizione valutaria economica

**Richiesta:** conservare un'informazione di valuta nativa/originale distinta dalla
valuta della quota del feed/provider e aggiungere una vista a torta della composizione
valutaria del portafoglio.

**Distinzioni da progettare:** valuta di quotazione, valuta base/denominazione dello
strumento ed esposizione economica sottostante non sono la stessa cosa. Un ETF sul
Giappone non implica automaticamente valuta base JPY né esposizione JPY pura; holdings,
share class e coperture valutarie possono cambiare il risultato.

**Target dati:** valutare una colonna per valuta base/originale SOLO con semantica e
fonte chiare. Per l'esposizione effettiva può servire una distribuzione valutaria
look-through, con data, copertura/hedging e quota Unknown, non un unico codice dedotto
dalla geografia.

**Target UI:** grafico Dashboard con metodo e denominatore dichiarati, cash e
posizioni trattati coerentemente, dati incompleti visibili e nessun peso ricavato da
una falsa precisione. Calcoli backend; prima ASCII e decisione del dev, poi review
operativa su esempi sintetici multi-valuta e hedged.

**Gate:** fonte e refresh dei metadati, aggregazione/normalizzazione, disponibilità,
FX e criteri di esposizione. Eventuali colonne/tabelle nuove tramite migrazione Alembic
incrementale generica. Nessuna modifica Asset o grafico di esposizione in questo hotfix.

## Espandere i provider aggiungendo extraetf.com e mettendo anche la distribuzione valutaria, potrebbe sposarsi con l'idea della valuta originaria del fondo, trasformandola di fatto in una distribuzione anche lei.
Possibilità di integrare queste informazioni nella UI e nei calcoli backend, mantenendo la tracciabilità delle fonti e la coerenza con le regole di esposizione valutaria già definite.

## Come per la valuta di esposizione, studiare come fare per aggiungere anche la distribuzione delle aziende, ma capendo come garantire di non avere Apple e apple SRL che sembrano diverse, ma in realtà sono la stessa.
Possibile approccio: normalizzazione dei nomi, utilizzo di identificatori univoci (es. ISIN per le aziende quotate), e gestione dei casi ambigui tramite regole di matching o intervento manuale.

## Stimatori robusti di covarianza per la matrice di correlazione (Riskfolio)
**Priorità:** 🔽 bassa — dopo che la pagina correlazioni avrà una direzione chiara.

`riskfolio.src.ParamsEstimation.covar_matrix` espone quindici stimatori oltre a quello
storico: `ledoit`, `oas`, `shrunk`, `gl`, `jlogo`, `gerber1/2`, `ewma1/2`, `semi`, più
tre metodi di denoising. Servono quando gli asset sono molti e le osservazioni poche —
con cento asset e 750 giorni si stimano 5 050 parametri da 75 000 osservazioni, e la
matrice campionaria diventa instabile: piccole variazioni nei dati muovono molto il
risultato.

**Perché non ora:** è un miglioramento di *qualità della stima*, non di prestazioni.
Misurato: Ledoit-Wolf 25,4 ms contro 0,2 ms di `np.cov`, scarto massimo 1,2e-05.
La migrazione M3 (vedi `02_riskfolioIntegration/06`) è deliberatamente a comportamento
invariato: cambia il tempo, non i numeri mostrati. Mescolare le due cose renderebbe
impossibile dire quale delle due ha causato una differenza.

**Gate:** decidere prima se la pagina correlazioni serve la domanda L2 («sono
diversificato come credo?») o una domanda di ottimizzazione. Se resta descrittiva, lo
stimatore storico è quello onesto da mostrare. Se diventa prescrittiva, uno stimatore
restretto è obbligatorio, e va dichiarato in UI con link alla wiki.

## 🔄 Rivalutare le otto misure reimplementate da N contro riskfolio-lib

**Posizione dello sviluppatore, 18 Set 2026** — da riprendere nel prossimo sprint:

> *« Anche se è un wrapper di NumPy, è meglio usare una libreria collaudata, anche perché
> nel tempo, se arrivano migliorie, le abbiamo **for free**. »*

**Stato attuale**: `backend/app/services/risk/acquired.py` reimplementa otto misure
(`worst_realization`, `maximum_drawdown`, `drawdown_at_risk`, `conditional_drawdown_at_risk`,
`ulcer_index`, `effective_number_of_assets`, `diversification_ratio`) che **esistono già nel
catalogo di riskfolio**.

**La ragione data da N**: riskfolio è importabile **solo dentro il worker spawnato**
(`risk/quant/riskfolio_worker.py`, decisione devWiki `risk-quant-engine-process-boundary`),
mentre le analitiche che consumano queste misure implementano `RiskAnalytic.compute()`
**sincrono**. Non si può chiamare un processo separato da lì.

**La domanda vera da porsi, quindi, non è «reimplementare o delegare» ma**:

1. Il confine processo/worker è ancora quello giusto, o si può allargare?
2. Quanto costa davvero l'import (~340 MB nativi) in un processo che già carica NumPy/SciPy?
3. Le due convenzioni piegate da N — **segno** (perdite negative) e **baseline** (la serie
   underwater porta un elemento pre-rendimento che `MDD`/`UCI` consumano e `DaR`/`CDaR` no) —
   sono esprimibili come adattatore sottile sopra la libreria, invece che come reimplementazione?

⚠️ **Da non perdere nella rivalutazione**: `test_risk_metrics_oracle.py` **già confronta** le
nostre implementazioni con riskfolio. **La rete per fare il passaggio in sicurezza esiste già** —
è lo stesso oracolo, usato in direzione opposta.

🔴 **E un divieto che resta valido comunque** (D130/D244): `riskfolio.SemiDeviation` **non** è la
nostra deviazione di ribasso. Misura lo scarto dalla **propria media**, non da un MAR fisso: su
un portafoglio che perde lo 0,5 % ogni giorno vale **esattamente zero**. **Quella sostituzione
resta vietata indipendentemente dall'esito di questa rivalutazione.**

**Priorità**: media. **Non blocca il rilascio** — è un lavoro di miglioramento.

## 🔢 Separatore decimale — l'helper esiste, ma è legato alla lingua sbagliata

**Verificato il 18 Set 2026**, su richiesta dello sviluppatore (*«credo ci sia già un helper in
tal senso, se non esiste mettilo in TODO_FUTURI altrimenti usiamolo»*).

**Il sintomo**: con l'app in italiano, la stessa riga mostra due separatori.

```
−1.3%        ← punto     (formatPercent → toFixed)
−175,91 €    ← virgola   (currencyFormat → toLocaleString)
```

Non è un difetto del sottosistema rischio: la **panoramica** della dashboard fa lo stesso
(`-9.47%` accanto a `-392,75 €`). È un difetto di progetto, preesistente.

### 🔴 Perché «usiamo l'helper esistente» non basta

`utils/currency/currencyFormat.ts:36,57` chiama:

```ts
Math.abs(amount).toLocaleString(undefined, {…})
                 ^^^^^^^^^
```

**`undefined` significa «la lingua del BROWSER»**, non quella scelta nell'app.

### Quando divergono — non è un caso limite, **è l'uso normale del selettore di lingua**

`frontend/src/lib/i18n/index.ts:65-84` risolve la lingua in quest'ordine:

```
1.  localStorage 'librefolio-locale'   ← la scelta esplicita dell'utente   (vince)
2.  getLocaleFromNavigator()           ← il browser, solo come RIPIEGO
3.  DEFAULT_LOCALE
```

> 🔑 **Il browser è il ripiego, non la fonte.** Appena l'utente tocca il selettore di lingua,
> `librefolio-locale` viene scritto e **la lingua dell'app si stacca da quella del browser**.
> `toLocaleString(undefined)` continua però a leggere **solo** il browser: le due si separano
> **per costruzione**, non per incidente.

### 🔴 Divergenza RIPRODOTTA dal vivo, 18 Set 2026

Selettore di lingua → *English*, su un browser `it-IT`:

```
app_lang      "en"            ← scelta dell'utente, onorata
browser       "it-IT"
interfaccia   "How much can it hurt?"      ✅ inglese, corretto
denaro        "−175,91 €"                  🔴 formato ITALIANO sotto interfaccia inglese
```

**Non è un'ipotesi: è uno screenshot.** E funziona in entrambi i versi — un utente italiano con
il sistema operativo in inglese (caso comunissimo) che sceglie 🇮🇹 ottiene **interfaccia italiana
e numeri inglesi**.

**Adottare questo helper in `formatPercent` propagherebbe un secondo difetto invece di
chiuderne uno.**

### Il lavoro vero, in tre passi

1. **Decidere la fonte della lingua**: il locale dell'app (`librefolio-locale`), non quello
   del browser. Serve un accessor unico che entrambi i formattatori consumano.
2. Legare **`currencyFormat`** e **`formatPercent`** a quell'accessor.
3. Aggiornare le asserzioni che oggi fissano il punto: **2** negli unitari di `formatPercent`,
   **~23 negli E2E** (di cui 20 in `risk-analysis.spec.ts`).

📌 **Raggio piccolo sul lato chiamanti** — `formatPercent` ha **5** consumatori — **ma il
cambio è osservabile ovunque**, perché il formattatore del denaro è usato in tutta l'app.

**Priorità**: media. **Non blocca il rischio**, e va fatto come lavoro di progetto con la sua
verifica, non infilato dentro un pacchetto di superficie.

---

## Il generatore di dati di prova non onora i bersagli `end_price`, e lo scarto è sistematico

**Misurato da N il 18 Set**, corsia 6151, finestra dichiarata.

| asset | bersaglio | ottenuto | scarto |
|---|---:|---:|---:|
| Apple | 185,00 | 264,57 | **+43,0 %** |
| Bitcoin | 45 000 | 25 889,81 | **−42,5 %** |
| Ethereum | 2 650 | 1 290,41 | **−51,3 %** |
| RE Loan Roma | 5 000 | 5 010,52 | +0,2 % |

### 🔴 La causa — e l'etichetta che le avevo dato era sbagliata

> **Correzione del 18 Set, di N.** Questa voce diceva *«deriva di Jensen: `uniform(−a,+a)`
> applicato moltiplicativamente ha media logaritmica negativa `≈ −σ²/2`»*. **Non è Jensen**,
> e l'etichetta manderebbe chi apre il lavoro a cercare un bias che non c'è.

**I segni sono discordi**, e Jensen spingerebbe tutti dalla stessa parte:

| asset | bersaglio | consegnato | scarto |
|---|---:|---:|---:|
| Apple | 185,00 | 264,57 | **+43,0 %** |
| Microsoft | 390,00 | 322,03 | **−17,4 %** |
| Bitcoin | 45 000 | 25 889,81 | **−42,5 %** |

Le ampiezze sono **esattamente quelle che la volatilità configurata prevede**: rumore
uniforme su ±2σ dà deviazione `2σ/√3` al giorno, che su 267 giorni fa **≈ 30 %** per le
azioni e **≈ 91 %** per la cripto su 373. **Tutti e tre cadono entro ~1,2 σ.**

> 🔑 **Non è un difetto di calcolo: `end_price` è un'attesa, non un bersaglio.**
> `drift_per_day = (end/start)^(1/n) − 1` centra il valore **in media sulle realizzazioni**, e
> ogni popolamento ne pesca **una sola**. Il commento nel codice dice *«so the final price
> arrives near end_price»*, e su una cripto «near» significa **±91 %**.

### E la forma vera, che è più interessante del difetto

Gli **indici centrano il bersaglio** (`6399,99999999994`, `3949,99999999998`) perché
`_populate_benchmark_indices` **normalizza**. Gli altri no, perché **nessuno li normalizza**.

> **Due metà dello stesso generatore trattano la stessa configurazione in due modi diversi**
> — una la onora esattamente, l'altra solo in media — **e la struttura dati non distingue i
> due casi.** È la stessa famiglia delle due convenzioni coerenti ciascuna con sé e
> incoerenti a vista dentro lo stesso oggetto.

**Il lavoro vero**, quindi, non è «correggere una deriva»: è **decidere se `end_price` è un
contratto o un'aspettativa, e renderlo esplicito nella struttura dati** — oppure normalizzare
anche le serie non-indice, come già si fa per gli indici.

### ⛔ Perché non è stato riparato subito

Ripararlo porterebbe Apple da **264,57 a 185,00** e Bitcoin da **25 890 a 45 000**. Al momento
della scoperta, **cinque superfici stavano misurando e pubblicando numeri su quelle serie**:
ogni misura presa quel giorno sarebbe stata invalidata **senza che nessuno sapesse perché**.

📌 È lo stesso criterio per cui non si infila uno spostamento grande di numeri già pubblicati
dentro un passo che ha un'altra proprietà definente.

### Quando farlo, e con cosa

**Dopo la fase 2**, come lavoro suo, con il raffronto ante/post su tutte le superfici che
leggono quelle serie. La correzione naturale è compensare la deriva logaritmica nel
`drift_per_day` (aggiungere `+σ²/2`), oppure applicare il rumore in forma additiva sui
log-rendimenti invece che moltiplicativa sui prezzi.

**Priorità**: media. **Non blocca nulla oggi** — i dati sono plausibili, semplicemente non
sono quelli dichiarati.

---

## Un commento di test è un'asserzione senza cancello

`frontend/e2e/gallery.spec.ts:710-716` motiva la scelta di non usare `.first()` così:

> *«"RE Loan Milano" … has exactly ONE PriceHistory row ever (see populate_mock_data.py
> populate_price_history() `loan_price_points`) so its WAC/Market chart renders empty»*

Dopo F1 quell'asset ha **267 righe di prezzo**, e `loan_price_points` **non esiste più in quella
forma**. Il test **non fallisce** — punta ad Apple per nome — ma **la ragione scritta è falsa e
cita un simbolo che non c'è**.

🔑 **Il fatto generale**: un commento che spiega *perché* un test è scritto in un certo modo
**è un'asserzione che nessuno esegue**, quindi nessuno la vede scadere. È il secondo caso nella
campagna in cui una modifica ai dati di prova invalida in silenzio un presupposto scritto
altrove.

**Priorità**: bassa come riparazione, **alta come avvertimento**. Da sistemare quando si tocca
`gallery.spec.ts`.

---

## Avanzamento della simulazione Monte Carlo — si può fare, e si sa già dove è difficile

**Misurato da S4 il 18 Set.** Non è più *«forse si può»*: la domanda binaria è chiusa.

### ✅ Il worker sa a che punto è, su tutti e tre i rami

```
resampling.py:172        for start in range(0, path_count, chunk_size)   ← BLOCK BOOTSTRAP (default)
quantlib_worker.py:143   for path_index in range(request.path_count)     ← GBM / MC
quantlib_worker.py:199   for path_index in range(request.path_count)     ← GBM / QMC
```

**Nessuno è una scala finta**: il contatore *è* l'unità di lavoro reale. `path_index / path_count`
è esatto e monotono — niente «finzione a scalini».

### 🔑 E il ramo predefinito ha l'aggancio di forma migliore

```python
chunk_size = max(1, _CELL_BUDGET // max(1, horizon_days * asset_count))
```

Il bootstrap è **già affettato**, con blocchi derivati dalla taglia del problema. Una callback sul
confine del chunk costa **una chiamata per chunk**, e **il numero di tick si autoregola**:
problema grande → più chunk → più avanzamenti.

> ⚠️ Ribalta la previsione ragionevole — il ramo *nuovo* è il comodo, i due GBM (per-cammino)
> richiederebbero una soglia. E la ragione non c'entra con l'avanzamento: il chunking esiste per
> il **budget di memoria** (`:169`), e `:116` dichiara che *«la riproducibilità non deve dipendere
> da come il lavoro è affettato»*. **Un aggancio lì riusa una garanzia già difesa invece di
> introdurne una nuova.**

### ⚠️ Il criterio di accettazione, da rispettare o non farlo

Il sorteggio degli inizi di blocco (`resampling.py:148-155`) è **fuori dal ciclo**, vettorizzato;
nel GBM stanno fuori `_validated_covariance` e `_build_process`. Una barra guidata dal solo
contatore **resta a 0 % per tutta quella fase, poi parte**.

> **Una barra ferma a 0 % è peggio di nessuna barra: l'utente conclude che è bloccata.**

✅ **Il numero per deciderlo esiste già nel payload** — `rng_seconds`,
`process_evolution_seconds`, `generation_evolution_seconds`, `path_aggregation_seconds`: il worker
**già misura dove è finito il tempo**. Se le fasi fuori ciclo pesano, la strumentazione giusta è
**un avanzamento a fasi, non a cammini**.

### 🔴 Il costo vero non è il worker

Il salto worker→web ha tre soluzioni (multi-frame sul pipe · canale laterale · contatore
condiviso). ⚠️ Ma `SpawnWorkerPool` è generico e ha **due utenti** — simulazione **e
ottimizzazione**: toccare il protocollo tocca anche l'ottimizzazione.

**Il salto web→client non ha un appiglio.** `query_risk` è **sincrona, richiesta/risposta**, e
**non esiste un id di lavoro**: non c'è nulla da interrogare né a cui abbonarsi. SSE, websocket e
polling **richiedono tutti e tre lo stesso prerequisito che oggi manca**. E la richiesta è
**bulk**: «la simulazione» è *una* analitica dentro un lotto, quindi una percentuale della
richiesta non è la percentuale della simulazione.

**Il lavoro vero è invertire l'API in «invia → segui», o trasmettere dentro la stessa risposta
HTTP.** È architetturale.

**Priorità**: media-bassa. **Prerequisito**: leggere i quattro tempi di fase da un payload reale
prima di scegliere la forma della barra.

---

## 🔴 La simulazione risponde alla finestra, non al portafoglio — e non si annuncia

**Misurato il 21 Set da S4, su corsia pulita** (rilevatore v2: arco `0,1 s`), intercettando la
`SimulationEngineRequest` vera invece di ricostruirla.

### Il fatto

**Stesso asset, stesso orizzonte, stesso giorno, stesso motore. Cambia solo la finestra:**

| finestra | mediana a 365 giorni | probabilità di perdita |
|---|---:|---:|
| **95 giorni** | **+1 400,4 %** | **0,01 %** |
| **365 giorni** | **−39,1 %** | **70,74 %** |

> **Da +1 400 % a −39 %, e da «non puoi perdere» a «perdi sette volte su dieci», per una
> tendina che l'utente legge come «quanta storia guardo».**
>
> **E nessuno dei due numeri, preso da solo, si annuncia come sbagliato.**

### ✅ Non è matematica rotta, e non sono i dati finti

**Il motore estrapola fedelmente.** Confronto fra la mediana simulata e l'estrapolazione
ingenua `(1 + r_finestra)^(365/n)` su **sei** finestre:

| finestra | ripetizioni | ingenua | mediana | rapporto |
|---|---:|---:|---:|---:|
| 95 g | **3,92×** | +31,57 % | +33,22 % | **1,013** |
| 140 g | 2,64× | +8,54 % | +10,28 % | 1,016 |
| 190 g | 1,94× | +1,97 % | +2,92 % | 1,009 |
| 250 g | 1,47× | +8,21 % | +9,49 % | 1,012 |
| 365 g | 1,01× | +8,76 % | +9,93 % | 1,011 |

**Le ripetizioni variano di quattro volte, il rapporto resta fra 1,009 e 1,016.** Il motore
aggiunge l'1 %, sempre lo stesso.

🔑 **La causa è il rapporto, non la lunghezza**: il bootstrap **ripesca ogni osservazione
`orizzonte / n_osservazioni` volte per cammino**. Con 93 osservazioni su 365 giorni sono
**3,92 ripetizioni** — cioè si assume che quel trimestre duri quattro volte tanto.

⚠️ **E morde un utente vero**: il portafoglio di prova lo nasconde perché è **per metà
liquido**, ma sullo scope asset no. **Chi tiene crypto e clicca «3M» riceve questo.**

### ⚠️ Il denominatore è gonfiato e saturabile — da sapere PRIMA di scrivere la soglia

```
finestra 540 giorni  →  n_osservazioni 360   ← identico alla finestra da 365
series_preparation.py riporta i prezzi in avanti  →  93 dove la borsa ha 66 giorni
```

**Chiedere più storia restituisce in silenzio la stessa storia**, e il riporto in avanti
inserisce rendimenti nulli che **abbassano la σ per giorno e gonfiano il conteggio**.
`n_observations` conta **giorni di calendario, non osservazioni indipendenti**, ed è il
denominatore di qualunque guardia a rapporto.

### Il lavoro, e cosa NON è

**Non è** «aggiusta il calcolo»: l'aritmetica è corretta.
**Non è** «rifai i dati»: si riproduce su dati puliti con volatilità realistiche
(BTC `4,58 %`/giorno, che è il valore vero).

**È** decidere cosa fare quando `orizzonte ≫ finestra`: **rifiutare**, **avvisare**, o
**lasciar fare e dichiarare l'incertezza**. ⚠️ **Nessuna soglia ovvia esiste**: a ripetizione
`1,00×` Bitcoin dà comunque **+100 %**. **La monotonia è il dato, la soglia è una scelta.**

📌 **Parzialmente mitigato nel round 2**: l'incertezza di stima della deriva viene resa accanto
alla banda — su un asset volatile a finestra corta vale **×/÷ 29,9** contro una banda di
**×11,4**, quindi **si dichiara inutile da sola**. **Resta da decidere se serve anche la
guardia.**

**Priorità**: media-alta. **Non blocca il rilascio** — la funzione è dietro banner beta — ma è
il difetto di prodotto più grande trovato nella review della fase 2.

---

## 🔴 L'audit i18n non può dire «inutilizzata» su un terzo del catalogo

**Misurato da S4 il 21 Set**, interrogando **la funzione dell'audit** invece di leggerne la regex.

### La causa, in una riga

```js
RiskResultFrame.svelte:27     const key = `risk.${prefix}.${code}`
                                           ↑ l'interpolazione è al PRIMO segmento
```

L'audit estrae come prefisso tutto ciò che precede la prima `${`, cioè `risk.`, toglie il punto
→ **`risk`**. E `is_key_potentially_used` fa `key.startswith(prefix)`.

> **Nessuna chiave `risk.*` può comparire nell'elenco degli inutilizzati. Mai. Per costruzione.**

### La taglia

```
prefissi radice NUDI: 12     →     954 chiavi su 2 886     =     33,1 % del catalogo
```

| namespace | chiavi rese non verificabili |
|---|---:|
| `risk` | **282** |
| `importWizard` | 273 |
| `signals` | 148 |
| `common` | 120 |
| `chartSettings` | 102 |
| `providerErrors` · `sectors` · `fileStatus` | 29 |

⚠️ **Il `2 886 / 2 886 complete · 0 incomplete` riportato più volte in questa campagna era vero
come uscita del comando, e su un terzo del catalogo non misurava niente.**

### 🔑 Perché è peggio del cancello dei link

`dev.py:1238` salta i `path={espressione}` e **tace**. Questo **risponde «usata»**.

> **Non un silenzio letto come assoluzione: un'assoluzione esplicita.**

### La riparazione è nella stessa riga che causa il difetto

```ts
function translatedCode(prefix: 'errors' | 'warnings', …)
```

**L'insieme esatto dei prefissi è già scritto nel codice, come unione tipizzata.** L'audit lo
butta via e ripiega sul troncamento alla prima interpolazione.

> **La cecità non è fondamentale: è una rinuncia.**

Il lavoro è insegnare all'audit a leggere le unioni tipizzate dove ci sono, e a **dichiarare
"non verificabile"** dove non ci sono — invece di dire «usata».

### ⚠️ E una trappola per chi lo raccoglie

La regola ancorata al punto (`risk.` invece di `risk`) dà **63 chiavi `risk.*` orfane**.
**Almeno 14 sono vive**: `risk.errors.*` (8) e `risk.warnings.*` (6) sono legittimamente
dinamiche. **«Non verificate» e «morte» sono due parole diverse.**

L'unica orfana **provata per grep** è `risk.simulation.regimeTruncated` — presente in quattro
lingue, con i campi che la alimenterebbero (`regime_declared_days`/`applied`) **già letti dieci
volte dal frontend**, e resa da nessuno.

**Priorità**: media. **Non blocca nulla**, ma ogni misura i18n fatta finora su quei dodici
namespace va riletta come «non verificata» invece che come «pulita».
