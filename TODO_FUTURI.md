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

---

## 🔗 Multi-Merge Promote Suggest

**Data aggiunta**: 14 Maggio 2026
**Priority**: P3

Currently, promote-suggest shows at most one candidate per standalone TX. A future improvement would be to handle N-way merge suggestions (e.g. 3+ standalone rows that can be grouped into multiple pairs) and present a UI for the user to pick which pair to merge first before proceeding with the next.

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

## 📊 Aggiornamento Automatico Prezzi/FX

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 🔄 PARZIALMENTE COMPLETATO  
**Priorità**: Media

### Contesto
~~Sia per i prezzi degli asset che per i tassi di cambio, il grafico deve avere un pulsante per richiedere l'aggiornamento automatico dei valori.~~ Implementato: Sync button con progress modal (FX Sync All, Asset sync individuale). Resta da implementare:
- Dialog con selezione frame temporale specifico
- Warning che l'operazione sovrascrive valori nel range
- Progress bar granulare durante l'aggiornamento

---

## 🏦 Regime Fiscale — Metodo di Vendita (FIFO, LIFO, PMC, Select ID)

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Alta (architettura core)

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

## 📚 Documentazione Per-Plugin FX Provider

**Data aggiunta**: 15 Marzo 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Bassa

### Contesto
Attualmente esiste solo una pagina generica che elenca tutti i provider FX:
- `/mkdocs/developer/backend/fx/providers_list/`

Ogni provider (ECB, FED, BOE, SNB) dovrebbe avere una **pagina dedicata** nella documentazione MkDocs con:
- Descrizione dettagliata del provider
- URL dell'API sorgente e formato dati
- Base currency e valute supportate
- Frequenza di aggiornamento (giornaliera vs mensile)
- Eventuali limitazioni note (es. SNB solo mensile, nessun dato giornaliero)
- Parametri di configurazione
- Esempio di risposta API

### Azione
1. Creare una pagina MkDocs per ogni provider in `mkdocs_src/docs/developer/backend/fx/providers/`
2. Aggiornare la property `docs_url` in ogni provider per puntare alla pagina specifica
3. Il frontend già usa `docs_url` per il link nell'info bar del FxProviderSelect (cliccando sull'icona del provider)

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
- Implementare il filtro `?asset_id=` nella pagina transazioni

---

## 📊 AssetEvent: Dividendi/Eventi da Provider Esterni

**Data aggiunta**: 1 Aprile 2026
**Status**: 📋 PIANIFICATO
**Priorità**: Media (post Phase 7)

### Contesto

La tabella `AssetEvent` e il campo `supports_events` nella classe base `AssetSourceProvider`
sono stati introdotti come infrastruttura cross-provider. Attualmente solo `scheduled_investment`
genera eventi. I provider market dovranno essere estesi per catturare:

- **Yahoo Finance**: dividendi e split (disponibili via `yfinance` Ticker.dividends/.splits)
- **justETF**: distribuzioni ETF (disponibili sulla pagina profilo)

### Azione Futura

1. Yahoo Finance: parsare `.dividends` e `.splits` in `get_history_value`, ritornare come `FAAssetEventPoint`
2. justETF: scraping pagina profilo per date e importi distribuzioni
3. Override `supports_events = True` nei provider aggiornati
4. Il sync layer già gestisce l'upsert — basta ritornare gli eventi nel `FAHistoricalData.events`
5. Il frontend (pagina Asset Detail, Phase 8) dovrà mostrare gli eventi sul grafico come marker

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


## 🌍 Normalizzazione Paese Multilingua (endpoint user-facing)

**Data aggiunta**: 13 Aprile 2026
**Status**: 📋 PIANIFICATO
**Priorità**: Bassa

### Contesto

La funzione `normalize_country_to_iso3()` in `backend/app/utils/geo_utils.py` gestisce la normalizzazione ISO-2 → ISO-3, ISO-3 → ISO-3, e nomi paese → ISO-3 (fuzzy search). È già usata internamente per il parsing dei dati asset.

Se in futuro servisse un endpoint API `/api/v1/utilities/normalize-country` per consentire agli utenti di cercare paesi in lingue diverse, la funzione base è già pronta. Basterebbe estenderla con un parametro `language` per il matching multilingua (la vecchia `normalize_country_multilang()` è stata rimossa in C14a come dead code — da riscrivere se necessario).

### Azione Futura

1. Se il TODO viene implementato: estendere `normalize_country_to_iso3()` con supporto multilingua
2. Se il TODO viene scartato: nessuna azione necessaria, la funzione attuale è comunque in uso

---

## ⚙️ Default Language/Currency per Nuovi Utenti (Registrazione)

**Data aggiunta**: 13 Aprile 2026
**Status**: 📋 PIANIFICATO
**Priorità**: Bassa (richiede refactoring registrazione)

### Contesto

Architetturalmente ha senso che il sistema assegni lingua e valuta di default ai nuovi utenti alla registrazione, leggendole dalle global settings. Le funzioni `get_default_language()` e `get_default_currency()` sono state rimosse da `global_settings_service.py` come dead code in C14a.

Quando la registrazione utenti verrà arricchita con defaults personalizzabili dall'admin:

1. Ricreare `get_default_language(session)` e `get_default_currency(session)` — sono one-liner che chiamano `get_setting_value()`
2. Usarle nel flusso di registrazione utente per inizializzare `UserSettings`

### Funzioni rimosse (riferimento per ricreazione)

```python
async def get_default_language(session: AsyncSession) -> str:
    value = await get_setting_value(session, "default_language", "en")
    return str(value) if value else "en"

async def get_default_currency(session: AsyncSession) -> str:
    value = await get_setting_value(session, "default_currency", "EUR")
    return str(value) if value else "EUR"
```

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

## 📸 Gallery Screenshots per Tipo Transazione

**Data aggiunta**: 3 Maggio 2026
**Status**: ⏳ DA FARE
**Priorità**: Media

### Descrizione

Quando si scrivono le prossime sezioni della gallery script, creare **1 screenshot per ogni tipo di transazione × ogni lingua** (EN/IT/FR/ES).
Gli screenshot vanno poi inseriti nelle pagine della documentazione mkdocs (`financial-theory/transaction-types/`) accanto alla descrizione di ciascun tipo.

### Dettagli

- Tipi: BUY, SELL, DEPOSIT, WITHDRAWAL, DIVIDEND, FEE, TAX, INTEREST, ADJUSTMENT, CASH_TRANSFER, ASSET_TRANSFER, FX_CONVERSION
- Lingue: EN, IT, FR, ES
- File gallery: `frontend/e2e/gallery.spec.ts`
- Pagine docs: `mkdocs_src/docs/*/financial-theory/transaction-types/`

---


## 🔒 TransactionPicker — Filter Inaccessible Paired TX (W4a)

**Data aggiunta**: 1 Giugno 2026
**Priority**: P3
**Status**: 📋 PIANIFICATO
**Source**: `plan-BugfixRound3-UnifiedPartnerArch.prompt.md` walktest Bug W4

### Contesto

The TransactionPickerModal allows importing paired TX where the partner is on a broker the user cannot access. The BulkModal already handles this case (shows lock icon via W4b fix), but the picker should prevent the selection in the first place.

### Azione Futura

1. In `TransactionPickerModal.svelte`, when building the list of selectable transactions:
   - If a TX has `related_transaction_id` and the partner's `broker_id` is not accessible (user has no role), disable the checkbox or show a warning tooltip
2. Alternative: allow import but show a confirmation dialog explaining that the partner is read-only

### Files Affected

- `frontend/src/lib/components/transactions/TransactionPickerModal.svelte`
- May need `partner_broker_id` from TXReadItem (already available in schema)

---

## 🔄 FormModal Items Array Refactor (Step 8/10 Deferred)

**Data aggiunta**: 1 Giugno 2026
**Priority**: P4
**Status**: 📋 PIANIFICATO
**Source**: `plan-BugfixRound3-UnifiedPartnerArch.prompt.md` Steps 8, 10

### Contesto

The FormModal still uses the legacy `initialRow + injectedPartnerRow` props interface. The `resolveFormItems.ts` helper and `FormModalItems` type already exist but aren't integrated into FormModal. The current interface works correctly — this is pure cleanup.

### Azione Futura

**Step 8**: Replace FormModal props `initialRow + injectedPartnerRow` with `items: FormModalItems | null`. Remove `fetchPartner()`, `loadingPartner`, deferred fetch logic. Init $effect reads from `items[0]` / `items[1]`.

**Step 10**: Update page `+page.svelte` to use `resolveFormItemsForView(row, txStoreGet, getBrokerRole)` when opening FormModal in view mode.

### Files Affected

- `frontend/src/lib/components/transactions/TransactionFormModal.svelte` — Props refactor
- `frontend/src/routes/(app)/transactions/+page.svelte` — Use resolveFormItemsForView
- `frontend/src/lib/components/transactions/resolveFormItems.ts` — Already exists

### Benefit

- Eliminates `fetchPartner()` async dance (store-first pattern)
- Single contract for all FormModal consumers
- Prevents future regressions when partner handling changes

---

## 🧹 Rimuovere `preview_columns` dai plugin BRIM

**Data aggiunta**: 8 Giugno 2026
**Priorità**: P4 (cleanup)

### Contesto

`BRIMPreviewColumn` e il metodo `preview_columns()` su ogni plugin BRIM (11 implementazioni) erano stati progettati per la "Staging Modal" del piano v4 — una modale che avrebbe mostrato le transazioni parsate in una tabella con colonne dinamiche per plugin.

Con il redesign v5 (ImportWizard a 4 step), questa funzionalità non serve più:
- `BRIMParseResponse.transactions` restituisce sempre `TXCreateItem[]` (schema fisso)
- Step 4 (Review) usa una DataTable con colonne universali derivate da TXCreateItem
- Non c'è variazione plugin-specifica nei dati restituiti

### File coinvolti

- `backend/app/schemas/brim.py`: classe `BRIMPreviewColumn`, campo `preview_columns` in `BRIMPluginInfo`
- `backend/app/services/brim_provider.py`: metodo astratto `preview_columns()`
- `backend/app/services/brim_providers/*.py`: 11 implementazioni (una per plugin)
- `backend/test_scripts/test_external/test_brim_providers.py`: test `test_preview_columns_baseline`

### Azione

1. Rimuovere `BRIMPreviewColumn` dallo schema
2. Rimuovere `preview_columns` da `BRIMPluginInfo`
3. Rimuovere il metodo `preview_columns()` dalla base class e dai plugin
4. Rimuovere il test relativo
5. Rigenerare il client API (`./dev.py api sync`)

**Ref**: `plan-phase07Part5-v5-ImportWizard.prompt.md` §8.5

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

## 🏷️ Centralizzazione Emoji Settori nel Backend

**Data aggiunta**: 11 Giugno 2026
**Priority**: P3
**Status**: 📋 PIANIFICATO

### Contesto
Attualmente, le emoji associate ai settori finanziari sono hardcodate nel frontend all'interno dei file di traduzione `i18n` (es. `"Technology": "💻 Tecnologia"`). Questo costringe a estrarre programmaticamente le emoji dalle stringhe di traduzione in alcuni componenti visivi (es. `SectorPieChart` / `AllocationPieChart`) e non garantisce una singola source of truth.

### Azione Futura
1. Spostare la definizione delle emoji nel backend, associandole direttamente all'enum o alla configurazione dei settori (es. endpoint `/api/v1/utilities/sectors`).
2. L'endpoint dovrà restituire oggetti strutturati (es. `{ "id": "Technology", "emoji": "💻" }`) invece di semplici stringhe, oppure fornire una mappa accessoria.
3. Rimuovere le emoji dai file di traduzione `i18n` (`en.json`, `it.json`, ecc.) del frontend.
4. Aggiornare `sectorStore.ts` per memorizzare e fornire facilmente l'abbinamento settore/emoji.
5. Aggiornare tutti i componenti frontend che mostrano i settori per usare l'emoji fornita dal backend, garantendo un'unica source of truth.


## AI Export per pagina
Dettagliare il tipo di export AI da applicare in base alla pagina in cui si è, aumentando le opzioni di promt:
- Analisi di portafoglio attuale
- Pianificazione di pac
- Analisi per ribilanciamento
- ....
E tarare ogni opzione in base alla pagina, broker e periodo visto.

---

Aree di miglioramento dopo aver visto compeditor:
Tra i provider di prezzo, oltre ai siti da aumentare, ha senso fare olgre al css selector (che potrebbe essere rinominato web page) anche json api, html table e csv
aggiungere i provider AI, olre a ollama e openrouter, anche tutti gli altri per l'installazione locale.
pensare un sistema di addon che permetta al forontend di aggiungere tab. Capendo come creare un market place.
aggiungere nella dashboard e nei broker dei tab che fanno anche altri tipi di analisi oltre quelli pensati, come ad esempio il vedere l'allocazione percentuale con i quadrettoni
Aggiungere la feature di analisi che permette di impostare una target allocation sia per broker che generale.
Aggiungere la possibilità di creare "Portafogli" che dovrebbero essere gruppi di broker o asset o entrambi, da approfondire.
Fare delle pagine di dettaglio per analizzare i trade, le fee 
Fare analisi solo sui dati
Capire se serve aggiungere esplicitamente la transazione di split o se l'adjustment è già sufficiente
Aggiungere un calcolatore FIRE non solo da oggi al futuro, ma anche fissando una data di inizio per aver modo di vedere la differenza tra andamento teorico e reale.
