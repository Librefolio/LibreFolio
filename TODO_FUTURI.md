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
Aggiungere la feature di analisi che permette di impostare una target allocation sia per broker che generale.
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
