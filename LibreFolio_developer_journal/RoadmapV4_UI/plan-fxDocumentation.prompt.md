# Plan: FX Documentation — MkDocs, i18n Globale, Traduzioni

**Data creazione**: 12 Marzo 2026
**Status**: 📋 ACCENNATO — da dettagliare dopo testing
**Priorità**: Media (ultima fase di Phase 5)
**Stima**: ~3 giorni
**Dipendenze**: `plan-fxTestingCleanup.prompt.md` completato (screenshot da E2E)
**Riferimenti**:
- `phases/phase-05-subplan/05FX_outofdate_plan/plan-phase05Fx.prompt.md` Steps 7, 8 — interamente pendenti
- `phases/phase-05-subplan/05FX_outofdate_plan/phase05-pending-audit.md` §B (Documentazione)

---

## Contesto

La documentazione MkDocs va completata DOPO i test e gli screenshot. Include: infrastruttura i18n globale, nuove pagine utente, documentazione backend FX, e traduzioni progressive.

## Task pendenti (da vecchio master plan)

### B1-B4. i18n MkDocs Globale (Step 7 del vecchio master)
- Plugin `mkdocs-static-i18n` in `mkdocs.yml` (dipendenza già nel Pipfile)
- Rename ~18 file `.md` → `.en.md` (sezioni traducibili)
- Rinominare `gallery-lang-selector.js` → `site-lang-selector.js`
- Rimuovere check `isGalleryPage()`, aggiungere navigazione tradotta
- Aggiornare `gallery-img-loader.js` per leggere lingua da path URL
- Testare con `./dev.py mkdocs serve`

### B5-B11. Documentazione Utente GUI (Step 8 del vecchio master)
- `user/brokers.en.md` — broker, BRIM, sharing
- `user/files.en.md` — upload, tabella, filtri
- `user/settings.en.md` — profilo, preferenze, password
- `admin/global-settings.en.md` — parametri globali
- `user/fx-rates.en.md` — pagina FX, chart, sync, edit, provider, **chain**
- `user/fx-csv-import.en.md` — **Guida import CSV per FX** (vedi sotto)
- Aggiornare `user/index.en.md` + nav in `mkdocs.yml`

### B5b. Pagina manuale utente: Import CSV FX

**Rif.**: [`plan-csvImportRefinement.prompt.md`](plan-csvImportRefinement.prompt.md)

Pagina dedicata che spiega all'utente come importare dati FX via CSV. Deve coprire:

1. **Come arrivarci**: navigare a `/fx` → cliccare su una coppia → entrare in Edit mode (icona matita) → cliccare "Import CSV"
2. **Struttura del file CSV**:
   - Formato 2 colonne: `date;VAL1>VAL2`
   - Header obbligatorio con direzione (es. `date;EUR>USD`)
   - Separatore `;`, date in formato `YYYY-MM-DD`, rate positivi
   - Supporto `<` come alternativa a `>` (normalizzato automaticamente)
3. **Esempi concreti**:
   - Esempio file minimo valido
   - Esempio con errori e come correggerli
   - Esempio con direzione invertita (`date;USD>EUR` vs `date;EUR>USD`)
4. **Direzione e swap**:
   - Cosa significano i currency label nel modale
   - Come usare il pulsante swap `⇄`
   - Come l'header determina la direzione automaticamente
5. **Errori comuni**:
   - Header con valute non della pagina
   - Header mancante o malformato
   - Date duplicate
   - Rate non numerici o negativi
6. **Screenshot**: modale import con drop zone, direction bar, CsvEditor preview, errori

### B12. Documentazione Backend FX
- Flusso sync con fallback e chain
- Provider MANUAL sentinel pattern
- Nuovo endpoint sync pair-based + route-based config
- SNB provider (JSON API, dati mensili)
- Currency utils (flag emoji, pycountry, babel)
- Traduzione endpoints (parametro `lang`)

### B13. Documentazione Algoritmo DFS Chain (developer docs)
- `developer/fx-chain-algorithm.en.md` — spiegazione del grafo valute-provider
- Vincoli custom (archi non ripetuti, max 2 usi per provider)
- Pseudo-codice DFS con backtracking completo
- Motivazione scelta DFS vs BFS vs librerie shortest-path
- Uso di `graphology` MultiDirectedGraph come struttura dati

### Traduzioni progressive
- Le traduzioni `.it.md`, `.fr.md`, `.es.md` vengono create progressivamente
- Phase 5 include solo l'infrastruttura (plugin, rename, selettore, pagine EN)
- Documentare in TODO_FUTURI.md la roadmap traduzioni

---

## Note

Questo plan è l'ultimo della catena Phase 5 FX. Una volta completato, Phase 5 può essere chiusa.

### ⚠️ Aggiornamento necessario: Auth JWT

La documentazione backend deve essere aggiornata per riflettere la migrazione
da sessioni in-memory a **JWT tokens** (vedi `plan-jwt-gallery-fixes.prompt.md`).

Punti da documentare:
1. **Come funziona il login**: `POST /api/v1/auth/login` → ritorna un cookie `session`
   che contiene un JWT firmato (HMAC-SHA256), non più un session ID opaco
2. **Come inviare richieste autenticate con curl**:
   ```bash
   # Login e salva cookie
   curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "user", "password": "pass"}'

   # Usa il cookie per endpoint protetti
   curl -b cookies.txt http://localhost:8000/api/v1/auth/me
   ```
3. **JWT_SECRET env var**: in multi-worker, deve essere settato dal launcher
   (dev.py lo genera automaticamente). In produzione può essere un valore fisso.
4. **Scadenza**: il token scade dopo N ore (configurabile in global_settings).
   Al riavvio del server il secret cambia → tutti i token vengono invalidati.
5. **Logout**: il server cancella il cookie; il token resta valido fino a scadenza
   (accettabile, non c'è blacklist server-side per ora)

### Endpoint privati (richiedono login)

Tutti gli endpoint che usano `Depends(get_current_user)` — devono avere il
cookie `session` con JWT valido. Da documentare come sezione "Private API".

| Modulo | Endpoint | Metodo | Note |
|--------|----------|--------|------|
| **Auth** | `/auth/me` | GET | Info utente corrente |
| **Auth** | `/auth/change-password` | POST | |
| **Auth** | `/auth/profile` | PUT | Modifica username/email |
| **Auth** | `/auth/users/me` | DELETE | Cancellazione account |
| **Settings** | `/settings/user` | GET | Preferenze utente |
| **Settings** | `/settings/user` | PUT | Modifica preferenze |
| **Settings** | `/settings/global` | GET | Elenco settings globali |
| **Settings** | `/settings/global/{key}` | GET/PUT | Lettura/modifica singolo setting |
| **Settings** | `/settings/global/initialize` | POST | Admin: init defaults |
| **Brokers** | `/brokers` | POST/GET/DELETE | CRUD broker (bulk) |
| **Brokers** | `/brokers/{id}` | GET/PATCH | Dettaglio/modifica broker |
| **Brokers** | `/brokers/{id}/summary` | GET | Summary broker |
| **Brokers** | `/brokers/{id}/access` | GET/PUT | Gestione accessi (sharing) |
| **BRIM** | `/brim/upload` | POST | Upload file import |
| **BRIM** | `/brim/files` | GET | Lista file importati |
| **BRIM** | `/brim/files/{id}` | GET/DELETE | Dettaglio/elimina file |
| **BRIM** | `/brim/files/{id}/download` | GET | Download file |
| **BRIM** | `/brim/files/{id}/last-parse` | GET | Ultimo risultato parse |
| **BRIM** | `/brim/files/{id}/parse` | POST | Esegui parse file |
| **Transactions** | `/transactions` | POST/PATCH/DELETE | CRUD transazioni (bulk) |
| **Uploads** | `/uploads` | POST/GET | Upload e lista file |
| **Uploads** | `/uploads/{id}` | GET/DELETE | Dettaglio/elimina file |
| **Users** | `/users` | GET | Ricerca utenti |

### Endpoint pubblici (nessun login richiesto)

| Modulo | Endpoint | Metodo | Note |
|--------|----------|--------|------|
| **Auth** | `/auth/login` | POST | Login |
| **Auth** | `/auth/logout` | POST | Logout (cancella cookie) |
| **Auth** | `/auth/register` | POST | Registrazione |
| **System** | `/system/health` | GET | Health check |
| **System** | `/system/info` | GET | Info sistema |
| **Utilities** | `/utilities/*` | GET | Dati di riferimento (paesi, valute, settori) |
| **Uploads** | `/uploads/file/{id}` | GET | Serve file statico |
| **Uploads** | `/uploads/plugin/{type}/{path}` | GET | Plugin assets |
| **BRIM** | `/brim/plugins` | GET | Lista plugin disponibili |

### Endpoint privati — FX (prefisso `/fx`)

| Sub-router | Endpoint | Metodo | Note |
|------------|----------|--------|------|
| **Providers** | `/fx/providers` | GET | Lista provider FX installati (codice, valute supportate, icon) |
| **Providers** | `/fx/providers/routes` | GET | Lista conversion routes configurate per l'utente |
| **Providers** | `/fx/providers/routes` | POST | Crea nuove conversion routes (direct o chain) |
| **Providers** | `/fx/providers/routes` | DELETE | Elimina conversion routes (bulk) |
| **Currencies** | `/fx/currencies/sync` | POST | Sync tassi FX per coppie configurate |
| **Currencies** | `/fx/currencies/rate` | POST | Upsert tassi FX (bulk) |
| **Currencies** | `/fx/currencies/rate` | DELETE | Elimina tassi FX (bulk) |
| **Currencies** | `/fx/currencies/convert` | POST | Conversione valuta (con chain/fallback) |

### Endpoint privati — Assets (prefisso `/assets`)

| Sub-router | Endpoint | Metodo | Note |
|------------|----------|--------|------|
| **CRUD** | `/assets` | POST | Creazione asset (bulk) |
| **CRUD** | `/assets` | GET | Lista asset con filtri, paginazione, ordinamento |
| **CRUD** | `/assets` | PATCH | Aggiornamento asset (bulk) |
| **CRUD** | `/assets` | DELETE | Eliminazione asset (bulk) |
| **CRUD** | `/assets/all` | GET | Lista completa asset (senza paginazione) |
| **CRUD** | `/assets/query` | GET | Ricerca asset per ISIN/ticker/nome |
| **Prices** | `/assets/prices` | POST | Upsert prezzi asset (bulk) |
| **Prices** | `/assets/prices` | DELETE | Elimina prezzi asset (bulk) |
| **Prices** | `/assets/prices/{asset_id}` | GET | Storico prezzi singolo asset |
| **Prices** | `/assets/prices/refresh` | POST | Refresh prezzi da provider esterni |
| **Provider** | `/assets/provider` | GET | Lista provider asset disponibili |
| **Provider** | `/assets/provider` | POST | Assegna provider ad asset (bulk) |
| **Provider** | `/assets/provider` | DELETE | Rimuovi assegnazioni provider (bulk) |
| **Provider** | `/assets/provider/search` | GET | Cerca asset su provider esterno |
| **Provider** | `/assets/provider/assignments` | GET | Lista assegnazioni provider correnti |
| **Provider** | `/assets/provider/refresh` | POST | Refresh metadata asset da provider |

### Endpoint privati — Transactions (prefisso `/transactions`)

| Endpoint | Metodo | Note |
|----------|--------|------|
| `/transactions` | POST | Creazione transazioni (bulk) |
| `/transactions` | GET | Lista transazioni con filtri |
| `/transactions` | PATCH | Aggiornamento transazioni (bulk) |
| `/transactions` | DELETE | Eliminazione transazioni (bulk) |
| `/transactions/types` | GET | Metadata tipi transazione |
| `/transactions/{id}` | GET | Dettaglio singola transazione |

### Endpoint privati — Backup (prefisso `/backup`)

| Endpoint | Metodo | Note |
|----------|--------|------|
| `/backup/export` | POST | Esporta dati utente |
| `/backup/restore` | POST | Ripristina dati da backup |
| `/backup/formats` | GET | Lista formati export disponibili |
| `/backup/status` | GET | Stato ultimo backup/restore |

> **Nota**: Tutti gli endpoint FX, Assets, Transactions, Brokers, BRIM,
> Settings, Backup, Uploads CRUD e Users richiedono il cookie `session`
> con JWT valido. Vedi `plan-api-auth-guard.prompt.md` per il piano di
> protezione dei ~32 endpoint attualmente pubblici.

**Ordine globale di esecuzione Phase 5:**
```
1. plan-fxConversionChain.prompt.md       (chain/route-based)
2. plan-fxDetailPageRedesign.prompt.md    (chart unificato, DataEditor, MeasureSignal, pannelli inline)
3. plan-fxTestingCleanup.prompt.md        (E2E, unit test, i18n audit, gallery)
4. plan-fxDocumentation.prompt.md         (MkDocs, docs utente, traduzioni)
```

