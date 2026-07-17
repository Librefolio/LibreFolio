# TODO FUTURI

Questo file documenta miglioramenti futuri, migrazioni pianificate, e note tecniche importanti per il progetto LibreFolio.
I TODO completati sono in `TODO_Completati.md`.

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



## 👥 Filtro Utente nella Files Page

**Data aggiunta**: 20 Febbraio 2026  
**Status**: ⏳ IN ATTESA (richiede API backend)  
**Priorità**: Media  
**Dipendenza**: Endpoint `/api/v1/users` o `/api/v1/admin/users`  
**Codice correlato**: `get_upload_by_user()` in `backend/app/services/static_uploads.py` (predisposta per colonna "Uploaded by" + filtro)

### Contesto
L'UploadedFile ha il campo `uploaded_by_user_id` ma non esiste un endpoint per risolvere gli ID utente in username/email. Serve per:
- Aggiungere colonna "Uploaded by" nella tabella files (come la colonna Broker in BRIM)
- Filtro dropdown per utente in modalità grid (accanto al search per nome)
- Badge colorati come nel BRIM (stessa funzione calcolo colori)

### Azione Futura
1. Creare endpoint backend `GET /api/v1/admin/users` (lista utenti, admin only)
2. Nel frontend, colonna utente visibile se `users.length > 1`
3. Filtro frontend-only con dropdown
4. Riutilizzare pattern filtri di `FilesTable`/`urlFilters`

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

## 📈 Asset Page — Prezzo e Transazioni

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 🔄 PARZIALMENTE COMPLETATO (Phase 6 + Phase 7 done)  
**Priorità**: Media (Phase 8 Dashboard)

### Contesto
~~La pagina dell'asset dovrebbe mostrare il prezzo corrente in alto~~ ✅ con ~~la possibilità, cliccando su un punto del grafico, di aprire un'interfaccia piccola per modificare il valore di quel giorno.~~ ✅ Data Editor implementato. ~~Sotto il grafico, per ogni transazione (slot per slot), mostrare il prezzo d'acquisto e la variazione rispetto ad oggi (guadagno/perdita), con uno storico del guadagno di quella transazione.~~ ⏳ Phase 7 completata — ora implementabile come feature Phase 8.

### Dettagli UI — Parti mancanti
- Lista slot transazioni con prezzo d'acquisto, variazione %, storico guadagno
- Richiede: aggregazione portfolio + calcolo P&L (Phase 8 Dashboard scope)

---

---

## 💸 BRIM: FEE/TAX non collegati all'asset — verifica e consolidamento transazioni

**Data aggiunta**: 17 Luglio 2026
**Status**: 🐛 BUG CONFERMATO (Directa, con export reale) + sospetto sistemico su altri plugin
**Priorità**: Alta
**Scope**: Backend (11 plugin BRIM) + Motore FIFO/Lotti + Portfolio Engine

### Contesto

I plugin BRIM, quando generano transazioni `FEE`/`TAX`, in molti casi **non collegano `asset_id`** anche quando il broker fornisce ISIN/ticker sulla stessa riga — il costo finisce "generico di broker" invece che attribuito all'asset che lo ha causato (es. ritenuta su cedola obbligazionaria, commissione di vendita).

### Evidenza concreta (Directa — confermato con export reale dell'utente)

CSV reale (`Movimenti_K6245_15-6-2026.csv`), righe cedola BTP:
```
20-05-2026;25-05-2026;Cedola obb.;M.511743;IT0005634792;65035044;BTP PIU SC FB33 EUR CUM;0;71,25;0;EUR;
20-05-2026;25-05-2026;Rit.cedola obb.;M.511743;IT0005634792;65035045;BTP PIU SC FB33 EUR CUM;0;-8,91;0;EUR;
```
Il ticker (`M.511743`) e l'ISIN (`IT0005634792`) sono presenti e identici a quelli della riga di acquisto originale (`17-02-2025;25-02-2025;Acquisto;M.511743;IT0005634792;...;10000;-10000;...`). Nonostante questo, `backend/app/services/brim_providers/broker_directa.py:306-312` esclude esplicitamente `FEE`/`TAX` (e anche `TRANSFER`/`ADJUSTMENT`/`WITHDRAWAL`/ecc.) dalla lista `asset_required`:
```python
asset_required = tx_type in [
    TransactionType.BUY,
    TransactionType.SELL,
    TransactionType.DIVIDEND,
    TransactionType.INTEREST,
]
```
`ticker`/`isin` vengono letti dalla riga (righe 300-301) ma **buttati via** per FEE/TAX — `asset_id` resta sempre `None` per questi tipi, anche quando il dato sorgente lo renderebbe risolvibile 1:1.

### Verifica sugli altri 10 plugin BRIM (17 Luglio 2026)

Stesso pattern (`asset_required`/`asset_required_types` che esclude FEE/TAX) trovato anche in:
- `broker_etoro.py:260-264`, `broker_finpension.py:191-195`, `broker_freetrade.py:232-236`, `broker_revolut.py:272-276`, `broker_trading212.py:237-241` — tutti escludono FEE/TAX (e INTEREST)
- `broker_schwab.py:274-279` — esclude FEE/TAX (include BUY/SELL/DIVIDEND/ADJUSTMENT)

Al contrario, **4 plugin già implementano il pattern corretto** (riferimento da riusare per il fix):
- `broker_ibkr.py:229-247` — la commissione generata riusa **lo stesso `asset_id`** già risolto per la riga BUY/SELL genitrice (stesso ISIN, stessa riga sorgente)
- `broker_coinbase.py:283-303` — stesso pattern: FEE riusa l'`asset_id` della transazione principale sulla stessa riga
- `broker_degiro.py:87-103` — il più sofisticato: la mappa tipo→`(TransactionType, requires_asset: bool)` distingue già caso per caso (`dividendbelasting`/ritenuta dividendo → `True`, `transactiekosten`/commissioni → `True`, ma `aansluitingskosten`/connection fee e `connection fee` → `False`, corretamente, perché sono costi di conto non legati a un asset)
- `broker_generic_csv.py:563-576` — non esclude FEE/TAX per tipo: collega l'asset se il campo "asset" della riga CSV è popolato, altrimenti no. **Nota dell'utente**: per questo plugin il gap osservato potrebbe essere dovuto a come l'utente ha generato/compilato il proprio CSV, non necessariamente a un bug di codice — da verificare caso per caso, non presumere colpa del plugin.

### Perché conta (lato calcolo, non solo dato)

Anche quando `asset_id` **è già** popolato correttamente (i 4 plugin sopra), oggi il beneficio si ferma a metà strada:
- ✅ **Portfolio Engine** (`portfolio_service.py:1698-1700`, funzione period P&L per posizione) **già** distingue FEE/TAX con `asset_id` (attribuiti alla posizione, riga `per_fees_taxes[(broker_id, tx.asset_id)]`) da FEE/TAX senza (`unalloc_fees[broker_id]`, costo generico di broker) — la docstring lo dice esplicitamente: *"Fees/taxes without asset_id go to raw unallocated buckets"* (riga 1637). Questa metà del lavoro richiesto **esiste già**.
- ❌ **Motore FIFO / Lotti** (`fifo_utils.py`, `_HOLDING_TYPES = {BUY, SELL}` in `portfolio_service.py:732`) **ignora sempre** FEE/TAX, anche quelli con `asset_id` popolato — non entrano nel calcolo del cost basis/WAC del lotto (`compute_wac_iterative`, righe 1111/1736/1791/1818 — tutte alimentate da transazioni filtrate a `_HOLDING_TYPES`). Una ritenuta su cedola o una commissione di acquisto oggi **non altera mai** il prezzo medio di carico del lotto, nemmeno quando sappiamo con certezza a quale asset appartiene.

### Direzione della richiesta (definita dall'utente, 17 Luglio 2026)

Il TODO **non è solo "fixare i plugin"**, ma un lavoro di verifica e consolidamento in 2 fasi:

1. **Verifica/consolidamento import**: passare in rassegna tutti gli 11 plugin BRIM e garantire che FEE/TAX collegano `asset_id` quando il broker fornisce un identificativo asset (ISIN/ticker) sulla stessa riga/contesto — riusando il pattern già corretto (ibkr/coinbase/degiro/generic_csv) invece di reinventarlo. Dove il broker non fornisce alcun identificativo (es. commissione di conto, bollo forfettario), il costo resta correttamente senza `asset_id`.
2. **Integrazione nel calcolo**: quando `asset_id` è dichiarato, il costo (FEE/TAX) deve confluire nella FIFO/analisi lotti (impattare cost basis/WAC del lotto specifico) — non solo nel report di periodo per-posizione come oggi. Quando `asset_id` non è dichiarato (davvero generico), deve **restare** un costo di broker nel Portfolio Engine, esattamente come già accade oggi in `positions_contribution`.

### Non fare per ora

Su richiesta esplicita dell'utente, **nessuna modifica al codice** — solo verifica e documentazione. L'implementazione (fix dei 6-7 plugin + estensione del motore FIFO) va pianificata a parte.

### File coinvolti (per il piano futuro)

- `backend/app/services/brim_providers/{broker_directa,broker_etoro,broker_finpension,broker_freetrade,broker_revolut,broker_schwab,broker_trading212}.py` — estendere `asset_required`/equivalente per includere FEE/TAX quando ISIN/ticker presente sulla riga
- `backend/app/services/brim_providers/broker_generic_csv.py` — verificare a parte se è un bug di codice o solo di dati (dubbio esplicito dell'utente)
- `backend/app/utils/financial/fifo_utils.py` — oggi `calculate_fifo_lots()` filtra solo BUY/SELL; da estendere per assorbire FEE/TAX come aggiustamento del cost basis del lotto interessato
- `backend/app/services/portfolio_service.py` — `_HOLDING_TYPES`, `get_lots()`, `compute_wac_iterative()`/`compute_wac_iterative_multi_broker()` — punti di alimentazione dati da estendere
- Test broker-specifici in `backend/test_scripts/test_external/test_brim_providers.py` (uno per plugin)

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

## 📉 Grafico Guadagni per Transazione

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Media (Phase 8)

### Contesto
Nel diagramma dei guadagni dalle varie transazioni:

- **Asse Y sinistra**: scala dei valori/percentuali dell'asset
- **Asse Y destra**: scala di guadagno/perdita delle singole transazioni di buy
- Per ogni evento di buy, un nuovo grafico parte da 0 in y a quella data
- Una linea con area che rappresenta la sommatoria cumulativa dei guadagni
- Evento di vendita + tasse + commissione: doppia freccia verso il basso (da definire)

### Sotto al Grafico
- Tabella con i buy in ogni riga
- Colonne: valore attualmente investito
- Sotto: barra con valore stimato + guadagnato
- Deve distinguere tra valore potenziale e realizzato (vendite parziali/totali)
- Selettore metodo di analisi (FIFO, LIFO, PMC, etc.)

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


### 📊 Grafico Asset con rendimento a N
Con i dati degli asset ha senso mostrare i grafici oltre che per abs e % da P0, anche il rendimento a N (anni o giorni, parametrico) con il significato che ogni punto rappresenta il guadagno/perdita di valore percentuale dell'asset se vosse stato comprato N giorni prima e venduto nel giorno attuale.
Questo da applicare sia all'asset principale che a quelli di confronto messi nel grafico, da mettere nella pagina di detail per le analisi di dettaglio.

---

## 🔍 BRIM Auto-Detect Broker via Account Code

**Data aggiunta**: 8 Giugno 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Alta (UX import flow)

### Contesto

Molti broker export includono un identificativo di conto nella prima riga o header del file (es. Directa: `Conto : CONTO COGNOME NOME`). Se il plugin BRIM durante il `detect()` ritorna anche un `account_code` estratto dal file, e se un broker dell'utente ha un campo `account_code` configurato che matcha, il sistema può pre-popolare automaticamente il broker nel wizard di import.

### Design

1. **BRIMProvider.detect()** — estendere il return type per includere `account_code: str | None` (opzionale, backward-compatible)
2. **Broker model** — aggiungere campo opzionale `account_code: str | None` (configurabile dall'utente nelle settings del broker)
3. **Frontend Import Wizard Step 1** — quando un file viene uploadato:
   - Chiama detect endpoint → riceve `{plugin, confidence, account_code?}`
   - Se `account_code` matcha con un broker dell'utente → pre-popola il dropdown broker
   - Se non matcha → user sceglie manualmente (comportamento attuale)
4. **Esempio Directa**: plugin legge riga 1, estrae "CONTO" → `account_code = "CONTO"` → matcha con broker Directa dell'utente che ha `account_code = "CONTO"`

### File coinvolti

- `backend/app/services/brim_provider.py` — `detect()` return type
- `backend/app/db/models.py` — `Broker.account_code`
- `backend/app/services/brim_providers/broker_directa.py` — implementa estrazione account_code
- `frontend/` — Import wizard Step 1 auto-fill logic

### Note

- Non bloccante per il wizard MVP — è un enhancement post-lancio
- Ogni plugin implementa l'estrazione solo se il formato lo supporta
- Il match è case-insensitive, trimmed

---




## 🔗 Link Transazioni in Asset Delete Modal

**Data aggiunta**: 26 Marzo 2026  
**Status**: 📋 ACTIONABLE (Phase 7 completata)  
**Priorità**: Bassa (UX polish)

### Contesto

Quando un asset non può essere eliminato perché ha transazioni esistenti (`error_code: HAS_TRANSACTIONS`), il messaggio è generico. Ora che la pagina transazioni esiste:

1. **Delete modal**: mostrare il conteggio transazioni e un link diretto alla pagina transazioni filtrata (es. "This asset has 3 transactions: [View → /transactions?asset_id=123]")
2. **Pagina dettaglio asset**: sezione con link alle transazioni collegate
3. **Backend**: aggiungere `transaction_count` a `FAAssetDeleteResult` quando `error_code == "HAS_TRANSACTIONS"`

### Azione Futura

- Aggiungere `transaction_count: int` a `FAAssetDeleteResult` quando `error_code == "HAS_TRANSACTIONS"`
- Nel frontend, renderizzare un link cliccabile nella ConfirmModal results e nei toast
- ~~Implementare il filtro `?asset_id=` nella pagina transazioni~~ ✅ **già esiste** — `filters.asset_id`/`asset_ids` già supportati in `/transactions` (`+page.svelte:178-179,744`), verificato 17 Luglio 2026. Scope residuo ridotto a solo campo backend + link FE.

---

---

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

## 🏷️ Transaction Form — Conteggio Asset/Cash per Broker

**Data aggiunta**: 1 Maggio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Bassa

### Contesto

Nel form di creazione/modifica transazione, quando l'utente seleziona un broker e un tipo di operazione (BUY, SELL, DIVIDEND, ecc.), sarebbe utile mostrare **accanto al nome del broker** un badge con il conteggio degli asset o del cash già presenti per quel broker, filtrati per il tipo di strumento selezionato.

Esempio: se l'utente sta facendo un SELL di un ETF, accanto al broker "Directa" mostrare `3 ETF` per indicare che quel broker ha già 3 ETF in portafoglio. Per operazioni cash (CASH_IN/CASH_OUT), mostrare il saldo cash disponibile nella valuta selezionata.

### Benefici

- **Contesto immediato**: l'utente capisce subito se il broker scelto ha già posizioni dello stesso tipo
- **Prevenzione errori**: riduce la probabilità di selezionare il broker sbagliato
- **Guida al SELL**: per le vendite, sapere quanti lotti sono disponibili aiuta a non creare over-sell

### Implementazione

1. **Backend**: endpoint o estensione di uno esistente che restituisca per ogni broker il conteggio asset raggruppato per `asset_type` e il saldo cash per valuta
2. **Frontend**: nel selettore broker del transaction form, mostrare un badge inline (es. `Directa (3 ETF)` o `Directa (€ 1.250,00)`) usando i dati caricati al cambio di asset type / valuta
3. Il conteggio deve aggiornarsi reattivamente al cambio di operazione o tipo strumento

### Note

- Il dato è derivato dalle transazioni già importate → richiede Phase 7 completata
- Valutare se il conteggio deve considerare solo posizioni aperte (qty > 0) o tutte le storiche
- Per SELL: potrebbe mostrare anche la quantità totale disponibile (somma qty dei lotti aperti)
- Già la summary del broker potrebbe bastare, da vedere
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
