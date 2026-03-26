# Plan: FX Documentation — User Guide, Admin Guide, Provider Docs & i18n Pipeline

**Data creazione**: 12 Marzo 2026
**Ultimo aggiornamento**: 20 Marzo 2026
**Status**: ✅ COMPLETATO — Fasi 1, 2, 2.5 completate. Fase 3 (i18n) delegata a `plan-mkdocsI18nPipeline.prompt.md`, completata.
**Completato**: 22 Marzo 2026
**Priorità**: Media (ultima fase di Phase 5)
**Stima**: ~4-5 giorni
**Dipendenze**: `phases/phase-05-subplan/plan-fxTestingCleanup.prompt.md` completato ✅ (screenshot da E2E, JWT, gallery)
**Riferimenti**:
- `phases/phase-05-subplan/05FX_outofdate_plan/plan-phase05Fx.prompt.md` Steps 7, 8 — interamente pendenti
- `phases/phase-05-subplan/05FX_outofdate_plan/phase05-pending-audit.md` §B (Documentazione)

---

## Contesto

La documentazione MkDocs va completata DOPO i test e gli screenshot. Include: nuove pagine User Guide, Admin Guide, Provider docs dettagliate, documentazione JWT auth, e pipeline i18n globale.

La documentazione si divide in 3 macro-fasi:

1. **Nuove pagine** — User Guide (onboarding, broker sharing, files, FX, crop-image) + Admin Guide (settings, filesystem)
2. **Aggiornamento docs esistenti** — Provider docs dettagliate, JWT auth, tabelle API endpoint, nav mkdocs
3. **i18n Pipeline** — Plugin `mkdocs-static-i18n`, rename file, traduzioni progressive

**Ordine globale di esecuzione Phase 5:**
```
1. plan-fxConversionChain.prompt.md       ✅ (chain/route-based)
2. plan-fxDetailPageRedesign.prompt.md    ✅ (chart unificato, DataEditor, MeasureSignal, pannelli inline)
3. plan-fxTestingCleanup.prompt.md        ✅ (E2E, unit test, i18n audit, gallery, JWT migration)
4. plan-fxDocumentation.prompt.md         📋 (MkDocs, docs utente, traduzioni) ← QUESTO PIANO
```

---

## Fase 1 — Nuove pagine (User Guide)

### 1.1 User Onboarding: Registrazione, Login, Primo Broker

**File**: `mkdocs_src/docs/user/getting-started.en.md`

Guida passo-passo in tono semplice, con screenshot dalla gallery:

1. **Registrazione**: Come registrarsi (primo utente diventa automaticamente admin). Screenshot del form di registrazione.
2. **Login**: Come effettuare il login. Screenshot della pagina di login.
3. **Creare il primo Broker**: Navigare a `/brokers`, cliccare "New Broker", compilare i campi (nome, icona, valuta base). Screenshot della pagina broker list e del form di creazione.
4. **Perché serve un Broker**: Spiegare brevemente che il broker è il contenitore delle transazioni e serve sia per la gestione operativa che per i calcoli di patrimonio. _Non entrare nel dettaglio del portfolio aggregation (non ancora implementato)._

### 1.2 Broker Sharing

**File**: `mkdocs_src/docs/user/broker-sharing.en.md`

1. **Cos'è il Broker Sharing**: Spiegare il sistema RBAC (Owner, Editor, Viewer) con la tabella permessi.
2. **Share Percentage**: Cos'è la percentuale di possesso e perché serve per i calcoli di patrimonio aggregato. Esempio: conto cointestato con coniuge → 50% ciascuno.
3. **Come condividere**: Mostrare il modale `BrokerSharingModal` con screenshot — cercare utenti, assegnare ruolo, impostare percentuale.
4. **Scenari d'uso**: Consulente finanziario (Viewer), coniuge (Editor/co-Owner), commercialista (Viewer).
5. _Non entrare nel dettaglio dei calcoli di patrimonio aggregato (Phase futura)._

### 1.3 Pagina Files

**File**: `mkdocs_src/docs/user/files.en.md`

1. **Introduzione**: La pagina `/files` ha due tab:
   - **Risorse Statiche** (`custom-uploads/`): file accessibili a tutti gli utenti (avatar, icone, documenti condivisi). Chiunque con accesso al sistema può vederli.
   - **Broker Reports** (`broker_reports/`): file visibili solo agli utenti con accesso a quel broker specifico (Owner, Editor, Viewer).
2. **Come caricare un file**: Drag & drop o click per sfogliare. Le immagini aprono automaticamente il modale di editing (vedi [Image Crop](misc/image-crop.en.md)).
3. **Caricare report del broker**: Spiegare che i report del proprio broker (CSV, Excel) possono essere caricati qui e verranno poi usati dal sistema BRIM per importare automaticamente le transazioni. _Accennare senza entrare nel dettaglio perché il sistema UI BRIM va ancora completato._
4. **Screenshot** dalla gallery: tab risorse statiche, tab broker reports, upload in corso.

### 1.4 Tassi di Cambio (FX)

**File**: `mkdocs_src/docs/user/fx-rates.en.md`

1. **Introduzione alla pagina FX**: Navigare a `/fx`, panoramica delle card con coppie di valute.
2. **Creare una coppia FX da zero**:
   - Cliccare "Add Pair"
   - Scegliere le due valute (CurrencySearchSelect)
   - Il sistema mostra automaticamente le route disponibili (Direct Routes e Chain Routes)
   - Scegliere un provider e confermare
3. **Autosync**: Spiegare brevemente che il sistema può sincronizzare automaticamente i tassi dal provider scelto.
4. **Chain di approvvigionamento dati**: Accennare che per coppie esotiche (es. RON/JPY) il sistema può costruire catene multi-provider (es. RON→EUR→JPY). Rimandare alla documentazione tecnica per approfondire: [FX Configuration & Routing](../developer/backend/fx/configuration.md).
5. **Dettaglio coppia**: Chart interattivo, vista dati, editing manuale, import CSV.
6. **Screenshot** dalla gallery FX (12 scene × 2 temi disponibili).

### 1.5 Import CSV FX

**File**: `mkdocs_src/docs/user/fx-csv-import.en.md`

**Rif.**: [`plan-csvImportRefinement.prompt.md`](phases/phase-05-subplan/plan-csvImportRefinement.prompt.md)

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

### 1.6 Image Crop (sezione Varie)

**File**: `mkdocs_src/docs/user/misc/image-crop.en.md`

Guida all'uso del componente di crop interattivo:

1. **Quando appare**: Automaticamente quando si carica un'immagine nella pagina Files o quando si modifica l'avatar nel profilo.
2. **Preset disponibili**: Avatar (200×200 1:1), Broker Icon (64×64 1:1), Custom (libero).
3. **Controlli**: Zoom (pulsanti, rotellina mouse, pinch), Rotazione (15° step), Flip H/V, maniglie di crop agli angoli.
4. **Output**: Selezione formato (PNG, JPEG, WebP), controllo qualità per formati lossy (10-100%), anteprima ellisse per crop circolari.
5. **Screenshot**: Modale `ImageEditModal` con crop attivo, preset selector, quality slider.

---

## Fase 2 — Nuove pagine (Admin Guide) + Provider Docs

### 2.1 Espansione CLI Tools

**File**: `mkdocs_src/docs/admin/cli_tools.md` (aggiornamento)

Aggiungere/aggiornare:

- `./dev.py server --force`: Uccide processi sulla porta prima di avviare
- `./dev.py server --workers N`: Multi-worker Uvicorn (auto-calcolato come `2 × (CPU-1)`)
- Aggiornare tabella test_runner con le nuove categorie:

| Category       | Command                            | Description                          |
|----------------|------------------------------------|--------------------------------------|
| External       | `./dev.py test external all`       | Provider tests (FX, assets, BRIM)    |
| Database       | `./dev.py test db all`             | Database layer tests                 |
| Services       | `./dev.py test services all`       | Service logic tests                  |
| Utils          | `./dev.py test utils all`          | Utility tests                        |
| Schemas        | `./dev.py test schemas all`        | Schema validation tests              |
| API            | `./dev.py test api all`            | API endpoint tests                   |
| E2E            | `./dev.py test e2e all`            | Backend end-to-end tests             |
| Front-Utility  | `./dev.py test front-utility all`  | Auth, settings, files, select, crop  |
| Front-User     | `./dev.py test front-user all`     | Brokers, multi-user                  |
| Front-FX       | `./dev.py test front-fx all`       | FX unit + 7 E2E spec files           |
| **All**        | `./dev.py test all`                | Run everything                       |

- Flag `--list` per elencare i test disponibili senza eseguirli
- `./dev.py i18n audit --duplicates --save-xlsx` per audit i18n avanzato

### 2.2 Admin Settings

**File**: `mkdocs_src/docs/admin/settings.en.md`

1. **Global Settings**: Elenco dei parametri globali (max upload size, JWT token expiration, ecc.).
2. **Come inizializzare da CLI**: `./dev.py user init-settings`
3. **Come modificare dalla UI**: Navigare a Settings → tab Admin (solo per superuser).
4. **Parametri disponibili**: Tabella con key, tipo, default, descrizione.

### 2.3 Filesystem Structure

**File**: `mkdocs_src/docs/admin/filesystem.en.md`

Documentare la struttura dati su filesystem:

```
backend/data/
├── prod/                       # Dati di produzione
│   ├── sqlite/app.db           # Database SQLite (WAL mode)
│   ├── custom-uploads/         # File caricati dagli utenti
│   │   ├── {uuid}.{ext}       # File binario
│   │   └── {uuid}.json        # Metadata sidecar
│   ├── broker_reports/
│   │   ├── uploaded/           # Report caricati, in attesa di parsing
│   │   ├── parsed/            # Report già processati con successo
│   │   └── failed/            # Report il cui parsing è fallito
│   └── logs/                   # Log applicazione
└── test/                       # Dati di test (isolati, stessa struttura)
```

- Spiegare cosa contiene ogni cartella (senza dettagli implementativi)
- Come fare backup del volume Docker (copia di `backend/data/prod/`)
- Come accedere al container via `docker exec` per operazioni di manutenzione
- Variabile d'ambiente `LIBREFOLIO_DATA_DIR` per override del path di produzione
- Variabile d'ambiente `LIBREFOLIO_TEST_MODE=1` per usare dati di test

### 2.4 Documentazione JWT Auth

**File**: `mkdocs_src/docs/developer/architecture/security.md` (aggiornamento/espansione)

Documentare la migrazione da sessioni in-memory a JWT tokens:

1. **Come funziona il login**: `POST /api/v1/auth/login` → ritorna `{"access_token": "...", "token_type": "bearer"}`
2. **Come inviare richieste autenticate**:
   - Frontend: header `Authorization: Bearer <token>`, `localStorage` persistence
   - curl:
     ```bash
     # Login
     TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
       -H "Content-Type: application/json" \
       -d '{"username": "user", "password": "pass"}' | jq -r '.access_token')

     # Usa il token per endpoint protetti
     curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
     ```
3. **JWT_SECRET**: In multi-worker Uvicorn, `dev.py` genera un secret random condiviso tra tutti i worker. In produzione può essere un valore fisso via env var.
4. **Scadenza**: Token scade dopo N ore (configurabile in global_settings). Al riavvio del server con nuovo secret, tutti i token precedenti vengono invalidati.
5. **Logout**: Il frontend cancella il token dal `localStorage`. Non c'è blacklist server-side (stateless by design).
6. **Multi-worker**: Il secret JWT viene generato una volta e passato a tutti i worker Uvicorn, garantendo che un token emesso da un worker sia valido per qualsiasi altro worker.

### 2.5 Tabelle API Endpoint

**File**: `mkdocs_src/docs/developer/api/overview.md` (aggiornamento)

Aggiornare con le tabelle complete degli endpoint privati e pubblici:

#### Endpoint privati (richiedono `Authorization: Bearer <token>`)

| Modulo | Endpoint | Metodo | Note |
|--------|----------|--------|------|
| **Auth** | `/auth/me` | GET | Info utente corrente |
| **Auth** | `/auth/change-password` | POST | |
| **Auth** | `/auth/profile` | PUT | Modifica username/email |
| **Auth** | `/auth/users/me` | DELETE | Cancellazione account |
| **Settings** | `/settings/user` | GET/PUT | Preferenze utente |
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
| **Transactions** | `/transactions` | POST/GET/PATCH/DELETE | CRUD transazioni (bulk) |
| **Transactions** | `/transactions/types` | GET | Metadata tipi transazione |
| **Transactions** | `/transactions/{id}` | GET | Dettaglio singola transazione |
| **Uploads** | `/uploads` | POST/GET | Upload e lista file |
| **Uploads** | `/uploads/{id}` | GET/DELETE | Dettaglio/elimina file |
| **Users** | `/users` | GET | Ricerca utenti |
| **FX** | `/fx/providers` | GET | Lista provider FX installati |
| **FX** | `/fx/providers/routes` | GET/POST/DELETE | CRUD conversion routes |
| **FX** | `/fx/currencies/sync` | POST | Sync tassi FX |
| **FX** | `/fx/currencies/rate` | POST/DELETE | Upsert/elimina tassi FX |
| **FX** | `/fx/currencies/convert` | POST | Conversione valuta |
| **Assets** | `/assets` | POST/GET/PATCH/DELETE | CRUD asset (bulk) |
| **Assets** | `/assets/all` | GET | Lista completa asset |
| **Assets** | `/assets/query` | GET | Ricerca asset |
| **Assets** | `/assets/prices` | POST/DELETE | Upsert/elimina prezzi |
| **Assets** | `/assets/prices/{id}` | GET | Storico prezzi |
| **Assets** | `/assets/prices/sync` | POST | Refresh prezzi da provider |
| **Assets** | `/assets/provider` | GET/POST/DELETE | Provider assignments |
| **Assets** | `/assets/provider/search` | GET | Cerca asset su provider |
| **Assets** | `/assets/provider/assignments` | GET | Lista assegnazioni |
| **Assets** | `/assets/provider/refresh` | POST | Refresh metadata |
| **Backup** | `/backup/export` | POST | Esporta dati utente |
| **Backup** | `/backup/restore` | POST | Ripristina da backup |
| **Backup** | `/backup/formats` | GET | Formati export disponibili |
| **Backup** | `/backup/status` | GET | Stato ultimo backup |

#### Endpoint pubblici (nessun login richiesto)

| Modulo | Endpoint | Metodo | Note |
|--------|----------|--------|------|
| **Auth** | `/auth/login` | POST | Login |
| **Auth** | `/auth/logout` | POST | Logout |
| **Auth** | `/auth/register` | POST | Registrazione |
| **System** | `/system/health` | GET | Health check |
| **System** | `/system/info` | GET | Info sistema |
| **Utilities** | `/utilities/*` | GET | Dati di riferimento (paesi, valute, settori) |
| **Uploads** | `/uploads/file/{id}` | GET | Serve file statico |
| **Uploads** | `/uploads/plugin/{type}/{path}` | GET | Plugin assets |
| **BRIM** | `/brim/plugins` | GET | Lista plugin disponibili |

### 2.6 Provider Core — Documentazione dettagliata

**File**: `mkdocs_src/docs/developer/backend/fx/providers_list.md` (espansione)

Mantenere la **tabella riassuntiva** in cima alla pagina, poi aggiungere un **capitoletto dedicato** per ciascun provider core installato di default:

#### ECB — European Central Bank

- **Codice**: `ECB`
- **Base Currency**: EUR
- **URL sorgente API**: `https://www.ecb.europa.eu/stats/eurofxref/` (XML)
- **Valute supportate**: ~30 (tutte le principali + emergenti)
- **Frequenza aggiornamento**: Giornaliera, ~16:00 CET nei giorni lavorativi
- **API key**: Non richiesta
- **Formato risposta**: XML con namespace ECB, parsato con `lxml`
- **Storico**: Disponibile dal 1999
- **Limitazioni note**: Nessun dato nei weekend/festivi BCE
- **Esempio risposta**: Snippet XML con 2-3 valute

#### FED — Federal Reserve (FRED)

- **Codice**: `FED`
- **Base Currency**: USD
- **URL sorgente API**: `https://fred.stlouisfed.org/graph/fredgraph.csv` (CSV, nessuna API key)
- **Valute supportate**: ~20 principali (EUR, GBP, JPY, CAD, CHF, AUD, INR, BRL, MXN, ZAR, SGD, HKD, KRW, TWD, NZD, THB, SEK, NOK, DKK, CNY)
- **Serie IDs**: Format `DEXXX` (es. `DEXUSEU` = USD per 1 EUR)
- **Frequenza aggiornamento**: Giornaliera, giorni lavorativi US
- **Quotazione**: USD per 1 unità estera → il provider inverte automaticamente per ottenere il formato LibreFolio
- **Multi-unit currencies**: Nessuna (FRED quota tutto per 1 unità)
- **Limitazioni note**: Una richiesta HTTP per valuta (sequenziale)

#### BOE — Bank of England

- **Codice**: `BOE`
- **Base Currency**: GBP
- **URL sorgente API**: Bank of England Statistical Interactive Database (XML)
- **Valute supportate**: ~60 (la lista più ampia tra i provider core)
- **Frequenza aggiornamento**: Giornaliera, giorni lavorativi UK
- **Storico**: Molto profondo (decenni per le valute principali)
- **Limitazioni note**: API XML complessa, parsing robusto necessario

#### SNB — Swiss National Bank

- **Codice**: `SNB`
- **Base Currency**: CHF
- **URL sorgente API**: `https://data.snb.ch/api/cube` (dataset `devkum`, CSV)
- **Valute supportate**: ~10 principali (USD, EUR, GBP, JPY, CAD, AUD, SEK, NOK, DKK, CNY)
- **Frequenza aggiornamento**: Giornaliera, giorni lavorativi svizzeri
- **Multi-unit currencies**: JPY, SEK, NOK, DKK quotate per 100 unità (il provider normalizza automaticamente a 1 unità)
- **Quotazione**: X CHF = 1 (o 100) unità estera → il provider inverte automaticamente
- **Limitazioni note**: Lista valute ridotta rispetto ad altri provider

#### Azione post-documentazione

Dopo aver scritto i capitoletti, aggiornare la property `docs_url` in ogni classe provider Python per puntare all'anchor specifico:

- `ecb.py` → `"/mkdocs/developer/backend/fx/providers_list/#ecb-european-central-bank"`
- `fed.py` → `"/mkdocs/developer/backend/fx/providers_list/#fed-federal-reserve-fred"`
- `boe.py` → `"/mkdocs/developer/backend/fx/providers_list/#boe-bank-of-england"`
- `snb.py` → `"/mkdocs/developer/backend/fx/providers_list/#snb-swiss-national-bank"`

Il frontend già usa `docs_url` per il link nell'info bar del `FxProviderSelect` (cliccando sull'icona del provider si apre la pagina di documentazione).

---

## Fase 2.5 — Aggiornamento docs esistenti

### 2.5.1 User Manual Overview

**File**: `mkdocs_src/docs/user/index.md` (riscrittura)

Riscrivere l'overview con link a tutte le nuove pagine:

- Getting Started (registrazione, login, primo broker)
- Broker Sharing
- Files (risorse statiche vs broker reports)
- FX Rates (coppie di valute, sync, chain)
- CSV Import (import dati FX)
- Varie: Image Crop

### 2.5.2 Admin Manual Overview

**File**: `mkdocs_src/docs/admin/index.md` (aggiornamento)

Aggiungere link a:

- Settings (global settings)
- Filesystem Structure
- Menzione del sistema JWT e multi-worker

### 2.5.3 Navigazione MkDocs

**File**: `mkdocs_src/mkdocs.yml` (aggiornamento nav)

Inserire tutte le nuove pagine nella navigazione:

```yaml
nav:
  # ...existing...
  - User Manual:
      - Overview: user/index.md
      - Installation (Docker): user/installation.md
      - Getting Started: user/getting-started.md
      - Broker Sharing: user/broker-sharing.md
      - Files & Uploads: user/files.md
      - FX Rates: user/fx-rates.md
      - FX CSV Import: user/fx-csv-import.md
      - Misc:
          - Image Crop: user/misc/image-crop.md
  - Admin Manual:
      - Overview: admin/index.md
      - CLI Tools: admin/cli_tools.md
      - Global Settings: admin/settings.md
      - Filesystem Structure: admin/filesystem.md
      - Advanced Docker: admin/docker_advanced.md
      - Exposing with Tailscale: admin/tailscale_exposure.md
  # ...existing...
```

### 2.5.4 Gallery images nelle docs

Le pagine user guide devono usare screenshot dalla gallery (320 disponibili in 4 lingue × 2 temi). Usare il sistema `gallery-img-loader.js` esistente con attributi `data-category` e `data-name`:

```html
<img class="gallery-img" data-category="fx" data-name="fx-list-overview" alt="FX List" />
```

Il loader risolve automaticamente il path basandosi su lingua e tema selezionati.

---

## Fase 3 — i18n Pipeline MkDocs

### 3.1 Configurazione plugin

- Aggiungere `mkdocs-static-i18n` in `mkdocs.yml` (dipendenza già nel Pipfile)
- Lingua default: `en`
- Lingue alternative: `it`, `fr`, `es`

### 3.2 Rename file

- Rinominare ~20+ file `.md` traducibili → `.en.md` (sezioni user-facing e admin)
- Le sezioni developer possono restare solo inglese (troppo tecniche per tradurre)

### 3.3 Selettore lingua globale

- Rinominare `gallery-lang-selector.js` → `site-lang-selector.js`
- Rimuovere check `isGalleryPage()`, rendere il selettore lingua globale su tutto il sito
- Aggiungere navigazione tradotta nel selettore

### 3.4 Aggiornamento image loader

- Aggiornare `gallery-img-loader.js` per leggere lingua da path URL (`/it/`, `/fr/`, `/es/`) anziché solo dal selettore gallery

### 3.5 Traduzioni progressive

Le traduzioni `.it.md`, `.fr.md`, `.es.md` vengono create progressivamente:
- Phase 5 include solo l'infrastruttura (plugin, rename, selettore, pagine EN)
- Le traduzioni effettive seguono dopo

**Suggerimenti per la pipeline di traduzione:**

- **Opzione A — Manuale**: Scrivere prima tutto in EN, poi tradurre file per file con assistenza AI. Massimo controllo sulla qualità, ma processo lento per ~20+ pagine × 3 lingue.

- **Opzione B — Semi-automatico con script**: Creare `./dev.py mkdocs translate <lang>` che per ogni `.en.md` senza corrispondente `.<lang>.md` genera una bozza traducendo via LLM API (OpenAI/Claude). L'output va rivisto manualmente ma il grosso del lavoro è automatizzato.

- **Opzione C — Markdown-aware translation**: Pipeline più sofisticata che:
  1. Divide ogni `.en.md` in blocchi semantici (titoli, paragrafi, tabelle, code blocks)
  2. Traduce blocco per blocco mantenendo la struttura Markdown intatta
  3. Mantiene una cache (hash per blocco) per non ri-tradurre blocchi invariati al prossimo aggiornamento
  4. Preserva i code blocks, link interni, e attributi HTML senza tradurli

- **Raccomandazione**: Partire con **Opzione A** per le prime 3-4 pagine user guide (onboarding, broker, files, FX), valutare il tempo necessario, e poi decidere se investire in Opzione B o C per il volume restante. L'Opzione C è la più robusta per manutenzione a lungo termine ma richiede sviluppo iniziale.

---

## Note implementative

### Struttura file finale prevista

```
mkdocs_src/docs/
├── user/
│   ├── index.md              # Overview (con screenshot dashboard)
│   ├── getting-started.md    # Onboarding (registrazione, login, primo broker)
│   ├── installation.md       # Esistente (Docker deploy)
│   ├── brokers/
│   │   ├── index.md          # Overview broker (card, creazione, stato features)
│   │   └── sharing.md        # RBAC sharing, share %, scenari d'uso
│   ├── files/
│   │   └── index.md          # Static uploads vs broker reports, drag&drop
│   ├── fx/
│   │   ├── index.md          # Panoramica FX, Add Pair, chain, detail
│   │   └── csv-import.md     # Import CSV formato, direzione, errori
│   └── misc/
│       └── image-crop.md     # Crop tool: preset, zoom, rotation
├── admin/
│   ├── index.md              # Overview (aggiornata con JWT mention)
│   ├── cli_tools.md          # Aggiornata (3 categorie front, --force, --workers)
│   ├── settings.md           # Global settings tabella + categorie
│   ├── filesystem.md         # Struttura dati, backup, manutenzione
│   ├── docker_advanced.md    # Esistente
│   └── tailscale_exposure.md # Esistente
└── developer/
    ├── dev-installation.md   # Spostato da getting-started/ (setup sviluppatore)
    ├── architecture/
    │   └── security.md       # Riscritta (JWT auth, endpoint tables, curl examples)
    └── backend/
        └── fx/
            └── providers_list.md  # Espansa (ECB, FED, BOE, SNB capitoletti)
```

### Dipendenze da completare prima

- ✅ Screenshot gallery disponibili (320 immagini, 64 test)
- ✅ JWT auth implementata e documentata nel piano
- ✅ Tutti gli endpoint protetti
- ✅ i18n audit pulito (590 chiavi, 100% coverage)
- ✅ Test runner riorganizzato (front-utility, front-user, front-fx)

### Ordine di esecuzione consigliato

1. **Fase 2.5.3** (mkdocs.yml nav) — setup struttura navigazione
2. **Fase 1.1-1.4** (User Guide core) — onboarding, broker, files, FX
3. **Fase 2.1-2.3** (Admin Guide) — CLI, settings, filesystem
4. **Fase 2.4** (JWT Auth docs) — security page
5. **Fase 2.6** (Provider docs) — capitoletti + `docs_url` update
6. **Fase 1.5-1.6** (User Guide secondarie) — CSV import, image crop
7. **Fase 2.5** (Aggiornamenti vari) — overview pages, API tables
8. **Fase 3** (i18n pipeline) — plugin, rename, selettore, infrastruttura
