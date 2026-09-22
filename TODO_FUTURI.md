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

#### PAC `min_fragmentation` — differita (decisione developer, 21/09/2026)

**Status**: 📋 DIFFERITA — non entra nella prima versione operativa.

Quarta policy dichiarata nel contratto (`PlannerPolicy`,
`backend/app/services/pac_allocator/models.py`) e **già specificata**: la sua
cascata obiettivo esiste ed è scorata in aritmetica esatta
(`evaluator.py`, ordine `fixed_l2 → shortfall → split_asset_count →
active_order_rows → route_priority → explicit_cost`). Oggi è risolvibile
**provatamente** dall'oracolo esaustivo sui domini piccoli; manca solo la
compilazione dello stage `split_asset_count` verso SCIP, quindi
`compiler._require_supported_scope` la rifiuta.

**Perché è differita e non "da progettare"**: la funzione obiettivo non è una
domanda aperta — è scritta e testata. Il rinvio è di priorità: la decisione
developer del 21/09 mette il **Rebalancer completo** davanti a tutto, perché il
PAC ne è il caso particolare a distribuzione iniziale nulla.

**Se si volesse ridiscutere l'obiettivo**: `split_asset_count` minimizza il
numero di Asset spezzati fra più route. Un'alternativa sensata sarebbe pesare la
frammentazione per valore anziché per conteggio, così che spezzare un Asset da
10 € non costi quanto spezzarne uno da 10 000 €. È una proposta, non una
raccomandazione: richiede una decisione di prodotto.

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

## 🔎 Gate sui campi di contratto senza consumatore

**Data aggiunta**: 21 Settembre 2026
**Status**: 📋 DIFFERITO — decisione developer del 21/09/2026
**Priorità**: Media

Oggi un campo aggiunto al contratto backend e **mai consumato dal frontend** non
produce alcun errore: né a compile time, né a `svelte-check`, né in esecuzione.
Il contratto cresce, il consumatore resta indietro, e nulla lo dice.

**Il caso che l'ha reso visibile** (21/09/2026): `memory` in `ToolItemMetrics`,
introdotto da `4a38b9061`, mai letto da `ToolExecutionMetrics.svelte`. È stato
trovato **per caso**: è inciampato in `duration()`, un helper tipizzato
genericamente su `ToolItemMetrics[keyof ToolItemMetrics]`, che si è allargato da
solo al nuovo campo e si è ritrovato un oggetto dentro una funzione che formatta
millisecondi.

> Il punto che rende il debito reale: **se quell'helper fosse stato tipizzato in
> modo specifico, il campo sarebbe passato in silenzio.** Non esiste un gate —
> esiste un inciampo fortuito. Un controllo che funziona per effetto collaterale
> dice quanto era vistoso il difetto, non quanto siamo attenti.

**Precedente con esito** (21/09/2026): `monetary_step`, campo del contratto P1
compilato a mano dall'utente e **mai letto dalla matematica** — zero occorrenze
in `constraints`/`objectives`/`solver`/`compiler`/`evaluator`, e scartato
nell'unpack di `models.py`. È stato **rimosso** nella cancellazione di P1, e la
sua unità minima di valuta è ora derivata da Babel (`minor_unit`), che è nel
contratto v2 e che il motore legge davvero. È il primo campo che la regola
condanna, ed è quello che l'ha generata.

**Secondo precedente, con il segno invertito** (21/09/2026): `ToolDocumentation.path`
nel descrittore di un Tool. Il modello ne valida **la forma** — relativo, niente
`..` — e **non l'esistenza**. Il frontend lo consuma davvero (`ToolAboutPanel`,
`ToolDiagnosticsPanel`, `presentation.ts`) e ci porta l'utente con un pulsante.
Quindi un path verso una pagina cancellata **supera ogni gate**.

> **Aggiornamento del 21/09, sera — la conseguenza è ora misurata, e c'è un gate
> che avrebbe dovuto coprirlo.** `dev.py mkdocs check-links` esiste e verifica i
> link fra codice e documentazione, ma per costruzione non vede questo:
> `dev.py:1073-1195` cerca stringhe letterali `/mkdocs/` nei `.ts`/`.svelte` del
> frontend (Scope 1) e `docs_url` nei soli `fx_providers` /
> `asset_source_providers` (Scope 2). Il path dei Tool non sta in nessuno dei
> due — vive in `ToolDocumentation(path=…)` sotto `tool_plugins/` ed è letto a
> runtime. Misurato: `grep -rl 'user/tools' frontend/src` → **0**,
> `grep -c 'tool_plugins' dev.py` → **0**.
>
> Quindi cancellando o rinominando la pagina PAC, `check-links` sarebbe rimasto
> **verde** mentre il pulsante *Documentation* del prodotto dava 404. Non è
> l'assenza di un gate: è **un gate che esiste e il cui perimetro esclude
> precisamente il riferimento che nessuno verifica** — la forma più difficile da
> vedere, perché la sua esistenza è essa stessa una rassicurazione. Verificato a
> mano che il path risolva in tutte e quattro le lingue del sito buildato: a
> mano, perché non c'è altro modo.

> Vale la pena tenerli accoppiati, perché insieme dicono una cosa che nessuno
> dei due dice da solo: `monetary_step` era **dichiarato e mai consumato**,
> `ToolDocumentation.path` è **consumato e mai verificato**. Il difetto non sta
> in una direzione particolare — sta nel **non controllare l'estremo**. Una
> regola con due casi opposti è più forte di una con un caso solo, perché il
> lettore capisce dov'è il buco invece di imparare un esempio.

**Terzo precedente, con la prova accanto** (21/09/2026): `RebalancerPolicy`,
`type RebalancerPolicy = Literal["invest_only", "invest_and_sell"]` in
`services/pac_allocator/models.py`. Zero consumatori in tutto il repository, e i
suoi due valori sono **interamente contenuti** in `PlannerPolicy`, che è il tipo
davvero usato (campo `policy` in due dataclass).

L'argomento che lo ha condannato non è il conteggio, che si poteva leggere come
«predisposizione per il lavoro che viene»: è che il disegno del Rebalancer v2 —
`plan-phase00PacRebalancerArchitecture.prompt.md`, **1226 righe** — non lo nomina
mai. `RebalancerPolicy` 0 occorrenze, `PlannerPolicy` 0 occorrenze,
`invest_and_sell` 1 sola occorrenza in §12.4 e come nome di un *programma
ristretto del solver*, cioè un concetto diverso da un valore di policy.

> Registrato **con la misura, non con la conclusione**: chi lo rileggerà saprà
> che è stato deciso su una prova e non su una preferenza. Se il Rebalancer avrà
> bisogno di un tipo ristretto, nascerà con il disegno in mano — un tipo
> ereditato da un'epoca precedente arriva con le sue assunzioni e nessuno che le
> ricordi.

**Quarto precedente, nel runner** (21/09/2026): `pac-analyze` registrato **due
volte** — `_backend_services.py` e `_backend_schemas.py` — contro file di test
cancellati nello stesso commit che li rimuoveva. Chiunque avesse eseguito quelle
due azioni avrebbe avuto un rosso da un pytest su un percorso inesistente.

`dev.py test check-orphans` era **verde**, e correttamente: verifica
*registrazione → raggiungibilità da un `all`*. Nessuno verifica *azione → il file
esiste*. Sweep manuale dei 211 percorsi citati da `scripts/test_runner/`: zero
mancanti dopo la rimozione, due falsi positivi (un commento d'esempio e un glob).

> I quattro insieme coprono le quattro caselle, ed è il motivo per cui vale la
> pena tenerli tutti: `monetary_step` dichiarato-e-mai-consumato,
> `ToolDocumentation.path` consumato-e-mai-verificato con un gate che lo esclude,
> `RebalancerPolicy` dichiarato-e-superato, `pac-analyze` registrato-e-morto con
> un gate che guarda la direzione opposta. **Due dei quattro hanno un gate che
> passa**: non basta chiedersi se un controllo esiste, bisogna chiedersi da che
> parte guarda.

**Perché è differito e non dimenticato**: decisione developer del 21/09 —
*«buona idea, ma da fare solo alla fine, quando il sistema è funzionante e si
passa alla fase di condensazione e potenziamento»*. Costruire il gate adesso
irrigidirebbe contratti che cambiano ogni giorno e produrrebbe rumore su campi
legittimamente non ancora consumati. Ha senso quando la superficie si
stabilizza: a quel punto «dichiarato e non usato» smette di essere una fase
normale dello sviluppo e torna a essere il segnale che è.

**Collocazione**: debito trasversale fra contratto backend e consumatori
frontend. Non appartiene a PAC/Rebalancer né alla piattaforma Tool: il caso che
l'ha rivelato viene da lì, ma la lacuna riguarda qualunque coppia
contratto/consumatore.

---

## ⚖️ Asimmetria della piattaforma Tool sull'assenza

**Data aggiunta**: 21 Settembre 2026
**Status**: 📋 OSSERVAZIONE — nessuna delle due scelte è sbagliata
**Priorità**: Bassa

La piattaforma Tool modella l'assenza in **due modi opposti** ai suoi due
estremi, e la differenza ha conseguenze UX visibili:

| lato | meccanismo | effetto dell'assenza |
|---|---|---|
| backend | `ToolDescriptor.operations` ha `min_length=1` | un servizio **senza operazioni è irrappresentabile**: va rimosso del tutto, e il tool sparisce dal catalogo |
| frontend | `ToolRendererUnavailableCode = 'renderer_missing'` | un tool **senza UI è rappresentato**, con messaggio tradotto in quattro lingue e la precisazione che nessun calcolo è partito |

**Il backend vieta l'assenza, il frontend la descrive.**

La conseguenza concreta, osservata il 21/09/2026 alla rimozione di P1: il
**Rebalancer sparisce** dal catalogo (nessuna operazione v2 ancora) mentre il
**PAC resta visibile e si spiega** (`operation="plan"` esiste, la UI no). Due
tool nella stessa condizione logica — «backend pronto a metà, frontend assente»
— hanno due destini UX diversi **per un dettaglio di modellazione**, non per una
decisione di prodotto.

Non è un difetto: entrambe le scelte sono difendibili. Ma se un giorno si vorrà
uniformare — per esempio rappresentare anche il servizio senza operazioni, così
che un tool in costruzione resti elencato e si spieghi invece di sparire — è qui
che va guardato. Vale anche il contrario: rendere irrappresentabile il renderer
mancante, obbligando a spedire UI e backend insieme.

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
