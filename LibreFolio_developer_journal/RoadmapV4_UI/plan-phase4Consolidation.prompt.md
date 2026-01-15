# Plan: Fix Critici + Upload System + Multi-Utenza + Cache JS + Plugin Static (Phase 4 Consolidamento)

Piano strutturato per risolvere bug bloccanti, implementare sistema upload con resize frontend, filtraggio multi-utente, cache locale librerie JS, static assets per plugin, e polish UX. Ordine: backend fix → backend nuovo → test API → frontend.

---

## Steps

### 1. Fix bug critici Backend (bloccanti) ✅ COMPLETATO

- ✅ [broker_service.py](../../backend/app/services/broker_service.py) `get_summary()` linea ~213: aggiunto `is_active`, `opened_at`, `icon_url`, `default_import_plugin` nel return `BRSummary`
- ✅ [broker_service.py](../../backend/app/services/broker_service.py) `create_bulk()` linea ~93: passato `icon_url`, `default_import_plugin`, `is_active`, `opened_at` al costruttore `Broker()`
- ✅ [dashboard-check.js](../../mkdocs_src/docs/javascripts/dashboard-check.js): path relativi (`/api/v1/system/health`), logica offline-first (mostra versione statica, poi aggiorna se server OK)
- ✅ [mkdocs.yml](../../mkdocs_src/mkdocs.yml) linea ~68: cambiato link Dashboard da `http://localhost:8000` a `/`

---

### 2. Backend: Global Settings Service (phase-final #2) ✅ COMPLETATO

- ✅ Creato `backend/app/services/global_settings_service.py` con funzioni:
  - `get_session_ttl_hours(session) -> int`
  - `get_max_upload_mb(session) -> int`
  - `is_registration_enabled(session) -> bool`
  - `get_setting_value(session, key, default) -> Any`
- ✅ Lettura diretta da DB ad ogni chiamata (no cache TTL per evitare inconsistenze multi-worker)
- ✅ Integrato in [auth.py](../../backend/app/api/v1/auth.py) per TTL sessioni dinamico

---

### 3. Backend: Sistema Upload Risorse Statiche (phase-final #10) ✅ COMPLETATO

- ✅ Creato `backend/app/services/static_uploads.py` con:
  - Storage in `backend/data/custom-uploads/`
  - Metadata JSON: `user_id`, `mime_type`, `original_name`, `size`, `uploaded_at`
  - Funzioni: `save_upload()`, `list_uploads()`, `get_upload_info()`, `delete_upload()`, `get_upload_path()`
- ✅ Creato `backend/app/schemas/uploads.py` con DTOs:
  - `UploadFileInfo`
  - `UploadResponse`
  - `UploadListResponse`
- ✅ Creato `backend/app/api/v1/uploads.py` con endpoints:
  - `POST /uploads` - upload file
  - `GET /uploads` - lista file
  - `GET /uploads/{id}` - info file
  - `DELETE /uploads/{id}` - elimina file
  - `GET /uploads/file/{id}` - serve binary
- ✅ Registrato router in [router.py](../../backend/app/api/v1/router.py)

---

### 4. Backend: Static Assets per Plugin + `generate_static_url()` ✅ COMPLETATO

- ✅ Aggiunto metodo `generate_static_url(relative_path: str) -> str` alle 3 classi base:
  - [BRIMProvider](../../backend/app/services/brim_provider.py)
  - [FXRateProvider](../../backend/app/services/fx.py)
  - [AssetSourceProvider](../../backend/app/services/asset_source.py)
- ✅ Formato URL: `/api/v1/uploads/plugin/{provider_type}/{relative_path}`
  - Esempio: `/api/v1/uploads/plugin/brim/directa/logo.png`
- ✅ Create directory `static/` per brim_providers, fx_providers, asset_source_providers
- ✅ Endpoint `GET /api/v1/uploads/plugin/{provider_type}/{path:path}` in uploads.py per servire static assets

---

### 5. Backend: Filtraggio Multi-Utente Broker/Transazioni ✅ COMPLETATO

**Fatto:**
- ✅ [brokers.py](../../backend/app/api/v1/brokers.py): Aggiunto `Depends(get_current_user)` su tutti endpoint
- ✅ [broker_service.py](../../backend/app/services/broker_service.py): Auto-create `BrokerUserAccess(role=OWNER)` in `create_bulk()`
- ✅ TTL Sessioni semplificato: rimossi variabili globali, `create_session(user_id, ttl_hours)` con ttl_hours obbligatorio
- ✅ Aggiunto `EDITOR` a `UserRole` enum (OWNER > EDITOR > VIEWER)
- ✅ Parametro `as_user_id` per superuser su tutti gli endpoint (`int` o `"all"`)
- ✅ Metodi service con `user_id: int` obbligatorio + `as_user_id: Optional[int|str]`
- ✅ `_check_user_access()` aggiornato con `min_role` per gerarchia ruoli

---

### 5b. Backend: API Gestione Accessi Broker (BrokerUserAccess) ✅ COMPLETATO

**Endpoint implementati in `brokers.py`:**

- ✅ `GET /brokers/{broker_id}/access` - Lista utenti con accesso
- ✅ `POST /brokers/{broker_id}/access` - Aggiungi accesso
- ✅ `PATCH /brokers/{broker_id}/access/{target_user_id}` - Modifica ruolo
- ✅ `DELETE /brokers/{broker_id}/access/{target_user_id}` - Rimuovi accesso

**Metodi aggiunti a `BrokerService`:**
- ✅ `list_accesses()` - Lista accessi con user info (username, email)
- ✅ `add_access()` - Aggiunge accesso con validazione
- ✅ `update_access()` - Modifica ruolo con controllo ultimo OWNER
- ✅ `remove_access()` - Rimuove accesso con controllo ultimo OWNER
- ✅ `_count_owners()` - Helper per contare OWNER

**Schema in `brokers.py`:**
- ✅ `BRAccessItem` - {user_id, username, email, role, created_at}
- ✅ `BRAccessListResponse` - {accesses, total}
- ✅ `BRAccessCreateRequest` - {user_id, role}
- ✅ `BRAccessUpdateRequest` - {role}
- ✅ `BRAccessCreateResponse` - {success, message, access}
- ✅ `BRAccessDeleteResponse` - {success, message}
- ✅ Rimossi schema legacy (BRUserAccessCreateItem, BRUserAccessReadItem, BRUserAccessUpdateItem)

**Modifiche DB:**
- ✅ CHECK constraint per UserRole in `001_initial.py`: `role IN ('OWNER', 'EDITOR', 'VIEWER')`

**Regole di business implementate e verificate:**
- ✅ Un broker può avere più OWNER
- ✅ EDITOR può modificare broker/transazioni (`min_role=EDITOR` in `update_bulk`)
- ✅ EDITOR non può eliminare broker (`min_role=OWNER` in `delete_bulk`)
- ✅ EDITOR non può condividere broker (`min_role=OWNER` in `add_access`)
- ✅ EDITOR può rimuovere solo se stesso (logica self-remove in `remove_access`)
- ✅ VIEWER solo lettura (blocchi `min_role`)
- ✅ Ultimo OWNER non può essere rimosso/degradato (`_count_owners()` check)


---

### 6. Test API Backend (dopo tutti i fix backend) ✅ COMPLETATO + REFACTORING

**Refactoring test_runner.py:**
- ✅ Creato `TEST_REGISTRY` come dizionario a 2 livelli (categoria → action → info)
- ✅ Ogni action ha: `func`, `test_names`, `name`, `desc`, `prereq`, `tests`, `note`
- ✅ Funzione `get_category_choices(category)` genera choices da registry
- ✅ Funzione `generate_epilog(category)` genera descrizione automatica per parser
- ✅ Funzione `run_test_from_registry(category, action, ...)` esegue test
- ✅ Funzione `create_subparser_from_registry(subparsers, category, extra_args)` crea parser automaticamente
- ✅ Rimossi ~500 linee di codice duplicato negli elif del main
- ✅ Singola fonte di verità: aggiungere test = aggiornare solo registry

**Conteggio Test Totali:**
| File | Test | Passati | Skip |
|------|------|---------|------|
| test_brokers_api.py | 21 | 21 | 0 |
| test_broker_access_api.py | 25 | 24 | 1 |
| test_broker_multiuser_api.py | 8 | 8 | 0 |
| test_uploads_api.py | 14 | 14 | 0 |
| test_transactions_api.py | 14 | 13 | 1 |
| test_broker_schemas.py | 29 | 29 | 0 |
| test_broker_service.py | 30 | 30 | 0 |
| **TOTALE** | **141** | **~139** | **~2** |

**File aggiornati:**

1. ✅ **`test_brokers_api.py`** (21 test):
   - Classi: TestBrokerCreate, TestBrokerRead, TestBrokerUpdate, TestBrokerDelete
   - NEW: TestBrokerBulkOperations (bulk create/delete, partial failure, duplicate name)
   - NEW: TestMultipleOwners (multiple owners, one removes another)
   - Tutti richiedono autenticazione

2. ✅ **`test_broker_access_api.py`** (25 test):
   - Classi: TestAccessList, TestAddAccess, TestUpdateAccess, TestRemoveAccess
   - Classi: TestMultiUserIsolation, TestSuperuserAccess, TestSelfModification
   - test_superuser_sees_all_brokers_with_as_user_id_all (SKIP se DB non pulito - corretto)
   - test_non_superuser_cannot_use_as_user_id
   - test_owner_cannot_degrade_self_if_last
   - test_owner_can_degrade_self_if_not_last

3. ✅ **`test_broker_multiuser_api.py`** (8 test):
   - Tutti i test ruoli (OWNER/EDITOR/VIEWER)
   - test_editor_can_create_transactions
   - test_viewer_cannot_create_transactions ✅ FIX APPLICATO

4. ✅ **`test_uploads_api.py`** (14 test):
   - Classi: TestUpload, TestListUploads, TestFileInfo, TestDownload, TestDelete
   - TestPluginStatic
   - TestFileSizeLimit (max_file_upload_mb check)
   - TestSuperuserDelete (SKIP se DB non pulito)
   - NEW: TestUploadSecurity (3 test: exe blocked, script blocked, image allowed)

5. ✅ **`test_transactions_api.py`** (14 test) - AGGIORNATO:
   - FIX: Tutti i test ora si autenticano prima di usare le API
   - FIX: Ogni test crea il proprio broker per isolamento
   - FIX: test_post_transactions_balance_error gestisce errori
   - FIX: Backend cattura Exception generica in _validate_broker_balances
   - FIX: Endpoint transactions.py ha try-catch globale per prevenire 500

6. ✅ **`test_broker_schemas.py`** (29 test):
   - FIX: Aggiunto `is_active` a TestBrokerReadItem

7. ✅ **`test_broker_service.py`** (30 test):
   - FIX: Aggiunta fixture `test_user` per creare utente test
   - FIX: Tutti i metodi service ora ricevono `user_id=test_user.id`

**Bug fixati:**
- ✅ Transactions API ora verifica ruoli broker (VIEWER bloccato)
- ✅ Upload security validation (blocca exe/script, valida MIME type)
- ✅ Test service broker aggiornati per nuova signature con user_id
- ✅ transaction_service.py: catch Exception in balance validation per evitare 500
- ✅ transactions.py endpoint: try-catch globale restituisce errore invece di 500

**Refactoring test_runner.py:**
- ✅ Creato `TEST_REGISTRY` come dizionario a 2 livelli con struttura completa:
  - `_meta`: info parser (`help`, `description`)
  - action: `{func, test_names, name, desc, prereq, tests, note}`
- ✅ `get_category_choices(category)` - genera choices da registry
- ✅ `generate_epilog(category)` - genera descrizione automatica per parser
- ✅ `run_test_from_registry()` - esegue test dal registry
- ✅ `create_subparser_from_registry()` - crea parser automaticamente da registry
- ✅ `_get_category_tests_for_all()` - genera lista test per funzioni `*_all`
- ✅ `_generate_main_epilog()` - genera epilog principale da registry
- ✅ `create_parser()` - itera su TEST_REGISTRY per creare tutti i subparser
- ✅ Tutte le funzioni `*_all` ora usano il registry (non più liste hardcoded):
  - `external_all()`, `db_all()`, `utils_all()`, `schemas_all()`
  - `services_all()`, `api_test()`, `e2e_test()`, `run_all_tests()`
- ✅ `GLOBAL_ALL_ORDER` - ordine esplicito per global all
- ✅ Rimossi ~450+ linee di codice duplicato
- ✅ Singola fonte di verità: aggiungere test = aggiornare solo registry

**Nuove dipendenze:**
- `python-magic` aggiunto a Pipfile per MIME type detection

**Esecuzione:**
```bash
./dev.sh test api brokers           # 21 test
./dev.sh test api broker-access     # 25 test  
./dev.sh test api broker-multiuser  # 8 test
./dev.sh test api uploads           # 14 test
./dev.sh test api transactions      # 14 test
./dev.sh test schemas brokers       # 29 test
./dev.sh test services broker       # 30 test
./dev.sh test all                   # Tutti i test
```

---

### 7. Cache locale librerie JS (mkdocs + frontend)

**MkDocs:**
- Scaricare in `mkdocs_src/docs/javascripts/vendor/`:
  - `mathjax@3/es5/tex-mml-chtml.js` (+ dipendenze)
  - `polyfill.min.js`
- Aggiornare [mkdocs.yml](../../mkdocs_src/mkdocs.yml): puntare a path locale
- Creare script JS loader con fallback CDN dinamico

**Frontend:**
- Se usa librerie CDN esterne, applicare stesso pattern in `frontend/static/vendor/`

---

### 8. Frontend: Componenti UI riutilizzabili

Creare in [components/ui/](../../frontend/src/lib/components/ui/):

**LazyImage.svelte:**
- Placeholder SVG generico
- Carica immagine async
- Mostra placeholder finché non arriva
- Gestisce errori con fallback

**Tooltip.svelte:**
- Apparizione istantanea (0ms delay)
- Chiude su click outside
- Posizionamento auto (evita overflow viewport)

**ImageUploader.svelte:**
- Drag&drop + file browser
- Selezione size: original / avatar (200px) / icon (50px)
- Resize client-side con canvas API (no librerie esterne)
- Preserva trasparenza PNG/WebP
- Supporta JPEG/PNG/WebP/GIF (BMP → PNG)
- Preview prima dell'upload

---

### 9. Frontend: Pagina Files + integrazione upload

- Creare `frontend/src/routes/(app)/files/+page.svelte`
- Due tab:
  - **"Risorse Statiche"**: `/api/v1/uploads`
  - **"Report Broker"**: `/api/v1/brokers/import/files`
- Features:
  - Lista file con preview (se immagine)
  - Nome, size, data upload
  - Azioni: download, delete
  - Upload con `ImageUploader.svelte`
- Posizione nel burger menu: sopra "Impostazioni"

---

### 10. Frontend: Fix UX Brokers + Polish + Gestione Accessi

**BrokerForm.svelte:**
- Fix `opened_at` che mostra "gg/mm/aaaa" in edit mode
- Sostituire `title` con `Tooltip.svelte` per info leva/short

**BrokerModal.svelte:**
- Footer sticky (Annulla/Crea sempre visibili)
- Solo form scrollabile

**BrokerCard.svelte:**
- Integrare `LazyImage.svelte` per icone

**Integrazione upload:**
- `ImageUploader.svelte` + `FuzzySelect` per selezione icona custom da uploads locali

**FuzzySelect.svelte (phase-final #5):**
- Background icona valuta più visibile (cerchio/pill colorato)

**Gestione Accessi Broker (utenti normali):**
- In BrokerDetail page: tab "Accessi" o sezione dedicata
- Lista utenti con accesso, ruolo (badge colorato), azioni
- Form per aggiungere utente (ricerca fuzzy) con selezione ruolo
- Bottone rimuovi per ogni utente (OWNER può rimuovere altri)

**Gestione Accessi Broker (superuser) - Pagina dedicata in Settings:**
- Diagramma JS dinamico interattivo (libreria: vis.js network o simile)
- Nodi a sinistra: Utenti (con avatar se disponibile)
- Nodi a destra: Broker (con logo/icona se disponibile)
- Archi colorati per ruolo:
  - 🔴 Rosso/Arancione: OWNER
  - 🔵 Blu: EDITOR  
  - 🟢 Verde: VIEWER
- Interazioni:
  - Drag&drop archi per creare nuove connessioni
  - Click su arco → popup per cambiare ruolo o eliminare
  - Click su nodo → evidenzia tutte le connessioni
- Filtri: per utente, per broker, per ruolo
- Vista alternativa: tabella tradizionale con filtri e azioni bulk

---

### 11. Frontend: Temi Light/Dark (phase-final #3)

- Creare sistema tema con CSS variables in [app.css](../../frontend/src/app.css)
- Creare `ThemeToggle.svelte`:
  - Icona sole/luna
  - Posizione: tra LanguageSelector e HelpMenu
- Salvare preferenza in `localStorage`
- Rispettare `prefers-color-scheme` come default
- Applicare stile coerente con documentazione MkDocs (Material theme)

---

### 12. Frontend: User Preferences UI refresh (phase-final #4)

- Modificare pagina preferenze utente per renderla come GlobalSettings:
  - Selettore verticale "capitolo" a sinistra
  - Parte destra con voci
  - Per ogni modifica: salva, annulla, ripristina (singolo)
  - Sopra: salva tutto, annulla tutto, ripristina tutto

---

### 13. Aggiornare documentazione e roadmap

- Smarcare task completati in [phase-04-brokers.md](phases/phase-04-brokers.md)
- Smarcare in [phase-final.md](phases/phase-final.md):
  - #2 Global Settings Service
  - #3 Temi Light/Dark
  - #4 User Preferences UI
  - #5 Icona valuta background
  - #6 Cache locale librerie JS
  - #10 Sistema Upload

---

## Further Considerations

1. **Tab Plugins nei settings (phase-final #11)**: richiede API multilingua sui provider — pianificarlo come prossimo step dopo questo consolidamento?

2. **Documentazione multilingua (phase-final #7)**: scrivere docs base in EN/IT/FR/ES — da fare in batch separato dopo stabilizzazione UI?

3. Creare della documentazione in mkdocs_src per spiegare i nuovi sistemi di upload e la nuova configurazione del progetto con distinzione tra super utente e utente normale.
---

## File da Creare (Riepilogo)

### Backend

| File | Descrizione |
|------|-------------|
| `backend/app/services/global_settings_service.py` | Utility lettura global settings |
| `backend/app/services/static_uploads.py` | Gestione upload file custom |
| `backend/app/schemas/uploads.py` | DTOs per upload |
| `backend/app/api/v1/uploads.py` | Endpoints upload |
| `backend/test_scripts/test_api/test_uploads_api.py` | Test API upload |

### Frontend

| File | Descrizione |
|------|-------------|
| `frontend/src/lib/components/ui/LazyImage.svelte` | Caricamento pigro immagini |
| `frontend/src/lib/components/ui/Tooltip.svelte` | Tooltip istantaneo |
| `frontend/src/lib/components/ui/ImageUploader.svelte` | Upload + resize immagini |
| `frontend/src/lib/components/ui/ThemeToggle.svelte` | Switch tema light/dark |
| `frontend/src/routes/(app)/files/+page.svelte` | Pagina gestione files |
| `frontend/src/routes/(app)/files/+page.ts` | Load function files |

### MkDocs

| File | Descrizione |
|------|-------------|
| `mkdocs_src/docs/javascripts/vendor/` | Librerie JS cachate localmente |
| `mkdocs_src/docs/javascripts/loader.js` | Script fallback CDN |

---

## Ordine di Esecuzione

```
1. Fix bug critici Backend
   ↓
2. Global Settings Service
   ↓
3. Sistema Upload Backend
   ↓
4. Static Assets Plugin
   ↓
5. Filtraggio Multi-Utente
   ↓
6. Test API Backend
   ↓
7. Cache JS (mkdocs/frontend)
   ↓
8. Componenti UI (LazyImage, Tooltip, ImageUploader)
   ↓
9. Pagina Files
   ↓
10. Fix UX Brokers
    ↓
11. Temi Light/Dark
    ↓
12. User Preferences UI
    ↓
13. Aggiornamento docs/roadmap
```

