# Plan: Broker Sharing GUI (Phase 4.8 — BrokerSharingModal)

**Durata**: ~5 giorni  
**Dipendenze**: Schema pre-work (share_percentage già implementato)  
**Status**: ✅ COMPLETATO — Step 0-8 completati + 3 round di enhancement estetico/UX. Backend: user search, bulk endpoint, schema standardization. Frontend: BrokerSharingModal con ECharts half-donut, 3-column layout, edit via modal overlay, search combobox unificato, integrazione broker detail, i18n 24 chiavi in 4 lingue. 0 errori svelte-check.
**Priorità**: ALTA — Deve essere completato PRIMA di Phase 5  
**Riferimento 05-08**: Sezioni 3.5, 10, 11 di `plan-phase05-to-08-upgrade.md`

---

## 📋 Contesto

Il backend ha già le API CRUD complete per il broker access control:

- `GET /api/v1/brokers/{broker_id}/access` — lista accessi
- `POST /api/v1/brokers/{broker_id}/access` — aggiungi utente
- `PATCH /api/v1/brokers/{broker_id}/access/{target_user_id}` — modifica ruolo/share%
- `DELETE /api/v1/brokers/{broker_id}/access/{target_user_id}` — rimuovi accesso
- `GET /api/v1/users/search?q={query}&exclude_broker_id={id}` — cerca utenti (Step 1 ✅)

I test API (17/17 + 9 users_search + 9 bulk/share) passano. Serve ancora:

1. ~~**Endpoint `PUT /brokers/{id}/access/bulk`**~~ — ✅ COMPLETATO (Step 2b)
2. **Nessun componente frontend** per gestire lo sharing

---

## 🔍 PRE-STEP 0: Verifica Schema e API (prima di iniziare)

Prima di iniziare lo sviluppo, verificare che tutto il pre-work di schema sia effettivamente in produzione.

### 0.01 ✅ Debug e pulizia del vecchio dopo aver svolto [plan-data-separation.md](phases/phase-04-subplan/plan-data-separation.md)

**Completato**: 25 Feb 2026

Pulizia effettuata:

- **`.env` e `.env.example`**: Rimossi `DATABASE_URL`, `TEST_DATABASE_URL`, `VERSION`, `PROJECT_NAME`, `API_V1_PREFIX`. Struttura riorganizzata in sezioni Production/Test con
  `LIBREFOLIO_DATA_DIR` sempre presente.
- **`config.py`**: `VERSION`, `PROJECT_NAME`, `API_V1_PREFIX` rimossi da `Settings` model (erano sovrascitti o inutili). Ora sono costanti nel modulo. `VERSION` derivata da
  `get_git_version()`. Aggiunto `extra="ignore"` al model per evitare errori con env vars non mappate su campi.
- **`main.py`**: Usa `PROJECT_NAME`, `API_V1_PREFIX` come costanti importate da config e `get_version()` per la versione (da git tags).
- **Test comments**: Aggiornati path vecchi (`backend/data/sqlite/test_app.db` → `./dev.py db create-clean --test`) in `test_broker_access_api.py`.

### 0.1 Verifica colonne DB

Controllare con il DB browser o con query diretta che le colonne esistano:

```sql
-- Verifica share_percentage in broker_user_access
PRAGMA
table_info(broker_user_access);
-- Deve contenere: share_percentage NUMERIC(5,2) NOT NULL DEFAULT 100

-- Verifica cost_basis_override in transactions
PRAGMA
table_info(transactions);
-- Deve contenere: cost_basis_override NUMERIC(18,6) nullable

-- Verifica CHECK constraint
SELECT sql
FROM sqlite_master
WHERE name ='broker_user_access';
-- Deve contenere: CHECK (share_percentage >= 0 AND share_percentage <= 100)
```

### 0.2 Verifica API esistenti

Aprire 🚀 **API Docs**: `http://localhost:8000/api/v1/docs` e verificare:

| Endpoint                               | Cosa controllare                                      | Sezione API Docs            |
|----------------------------------------|-------------------------------------------------------|-----------------------------|
| `GET /brokers/{id}/access`             | Response include `share_percentage` in ogni item      | Brokers → Access Management |
| `POST /brokers/{id}/access`            | Body accetta `share_percentage` (Decimal)             | Brokers → Access Management |
| `PATCH /brokers/{id}/access/{user_id}` | Body accetta `share_percentage` (Optional Decimal)    | Brokers → Access Management |
| `GET /transactions?broker_id={id}`     | Response include `cost_basis_override` in ogni item   | Transactions                |
| `POST /transactions`                   | Body accetta `cost_basis_override` (Optional Decimal) | Transactions                |

### 0.3 Test manuali API (da fare con Swagger UI)

1. **Creare un broker** → `POST /brokers`
2. **Verificare accesso owner** → `GET /brokers/{id}/access` → deve ritornare l'owner con `share_percentage: 100`
3. **Aggiungere un utente** → `POST /brokers/{id}/access` con `{ "user_id": X, "role": "VIEWER", "share_percentage": 0 }`
4. **Modificare share%** → `PATCH /brokers/{id}/access/{user_id}` con `{ "share_percentage": 50 }`
5. **Verificare modifica** → `GET /brokers/{id}/access` → utente con `share_percentage: 50`
6. **Rimuovere accesso** → `DELETE /brokers/{id}/access/{user_id}`

### 0.4 Verifica test suite

```bash
./dev.py test api broker-access   # Deve passare (verifica share_percentage nei test)
./dev.py test api broker-multi    # Deve passare (verifica multi-user isolation)
./dev.py test api transactions    # Deve passare (verifica cost_basis_override)
./dev.py front check              # 0 errori (frontend generato coerente)
```

### 0.5 Endpoint NUOVI da analizzare dopo lo Step 1

Dopo aver implementato lo Step 1 (search users), tornare su API Docs e verificare:

| Endpoint NUOVO                                        | Cosa controllare                                         |
|-------------------------------------------------------|----------------------------------------------------------|
| `GET /api/v1/users/search?q=test`                     | Ritorna utenti con "test" nel username, NO email esposta |
| `GET /api/v1/users/search?q=test&exclude_broker_id=1` | Esclude utenti già con accesso al broker 1               |
| `GET /api/v1/users/search?q=a`                        | Errore 422 (min 2 caratteri)                             |

### Tasks Pre-Step

- [x] Eseguire `./dev.py test api broker-access` — ✅ PASS
- [x] Eseguire `./dev.py test api broker-multi` — ✅ PASS
- [x] Eseguire `./dev.py test api transactions` — ✅ PASS
- [x] Eseguire `./dev.py front check` — ✅ 0 errori
- [x] Verificare su API Docs che `share_percentage` appare negli endpoint broker access
- [x] Verificare su API Docs che `cost_basis_override` appare negli endpoint transactions
- [ ] Test manuale: creare broker → verificare owner access con share_percentage=100
- [ ] Test manuale: aggiungere utente con share_percentage custom → verificare persistenza

### Principio GDPR

> **Il Broker è la stanza.** Se dai le chiavi, si vede tutto lo storico.

| Ruolo      | `share_percentage` default | Permessi                                        | Caso d'uso                   |
|------------|----------------------------|-------------------------------------------------|------------------------------|
| **OWNER**  | 100%                       | Tutto: CRUD tx, gestione accessi, delete broker | Intestatario conto           |
| **EDITOR** | 0%                         | CRUD tx (no gestione accessi, no delete broker) | Coniuge delegato, consulente |
| **VIEWER** | 0%                         | Sola lettura                                    | Commercialista               |

---

## 1. ✅ Backend — Nuovo endpoint ricerca utenti (~0.5 giorni) — COMPLETATO 27 Feb 2026

> **Rif. 05-08**: Sezione 3.5 "Phase 4.8 — Broker Sharing GUI" — Questo endpoint è necessario anche per Phase 8 (Dashboard) dove si mostrano gli utenti condivisi per ogni broker
> nel breakdown KPI.

**Implementazione effettiva**:

.- **`backend/app/api/v1/users.py`**: `GET /users/search?q={query}&exclude_broker_id={id}` — min 2 char, ILIKE su username, no email esposta, no limite risultati (rimosso per semplicità)

- **`backend/app/schemas/users.py`**: `UserSearchItem(id, username, avatar_url)` + `UserSearchResponse(users, count)` — usa `count` standardizzato (non `total`)
- **`backend/app/services/user_service.py`**: `search_users()` con JOIN UserSettings per avatar_url, subquery exclude
- **`backend/app/api/v1/router.py`**: users router registrato
- **`scripts/test_runner.py`**: test `users-search` registrato nel runner
- **Standardizzazione `count`**: Migrati tutti gli schemi da `total` a `count` (UploadListResponse, BRAccessListResponse, FXPairSourcesResponse, FXCurrenciesResponse, CountryListResponse, CurrencyListResponse, SectorListResponse). Test aggiornati di conseguenza.

### Tasks

- [x] Creare `backend/app/api/v1/users.py` con endpoint `GET /users/search`
- [x] Creare schema `UserSearchItem` + `UserSearchResponse` (in `users.py` separato)
- [x] Aggiungere `search_users()` in `user_service.py`
- [x] Registrare `users_router` in `router.py`
- [x] Test: `backend/test_scripts/test_api/test_users_search.py`
- [x] Standardizzare `count` in tutti gli schemi (da `total`)

---

## 2. ✅ Backend — Aggiungere campi mancanti (~0.5 giorni) — COMPLETATO 27 Feb 2026

> **Rif. 05-08**: Sezione 2.1 "share_percentage" + Sezione 10 "GDPR/Sharing Architecture" — `avatar_url` e `user_role` servono anche a Phase 8 (Dashboard) per mostrare avatar
> utenti nel breakdown e decidere se un broker pesa sul Net Worth dell'utente corrente (share > 0%).

**Implementazione effettiva**:

- **`BRAccessItem`**: Aggiunto `avatar_url: Optional[str]` — JOIN con UserSettings in `list_accesses()`
- **`BRSummary`**: Aggiunto `user_role: Optional[str]` e `user_share_percentage: Optional[Decimal]` — popolati da `get_summary()`
- **Share % validation**: `_sum_share_percentages()` helper + validazione in `add_access()` e `update_access()` — somma ≤ 100% enforced
- **Test aggiornati**: `test_broker_access_api.py`, `test_broker_multiuser_api.py`, `test_brokers_api.py`, `test_uploads_api.py` tutti aggiornati per il cambio `total` → `count`

### 2.1 `avatar_url` in `BRAccessItem`

In `backend/app/schemas/brokers.py`, aggiungere:

```python
class BRAccessItem(BaseModel):
    user_id: int
    username: str
    email: str
    role: UserRole
    share_percentage: Decimal
    avatar_url: Optional[str] = None  # NEW
    created_at: UTCDateTime
```

In `broker_service.py → list_accesses()`, fare JOIN con `UserSettings` per popolare `avatar_url`:

```python
from backend.app.db.models import User, UserSettings

stmt = (
    select(BrokerUserAccess, User, UserSettings)
    .join(User, BrokerUserAccess.user_id == User.id)
    .outerjoin(UserSettings, UserSettings.user_id == User.id)
    .where(BrokerUserAccess.broker_id == broker_id)
    .order_by(BrokerUserAccess.role, User.username)
)
# ... e nel return aggiungere "avatar_url": settings.avatar_url if settings else None
```

### 2.2 `user_role` in `BRSummary`

In `backend/app/schemas/brokers.py`, aggiungere a `BRSummary`:

```python
user_role: Optional[str] = Field(
    None, description="Current user's role on this broker (OWNER/EDITOR/VIEWER)"
    )
```

In `broker_service.py → get_summary()`, popolare `user_role` dalla query access:

```python
# Dopo aver ottenuto il broker, determinare il ruolo dell'utente corrente
access = await self._check_user_access(broker_id, user_id)
summary.user_role = access.value if access else None
```

### Tasks

- [x] Aggiungere `avatar_url: Optional[str] = None` a `BRAccessItem` schema
- [x] Modificare `list_accesses()` per JOIN con UserSettings e popolare avatar_url
- [x] Aggiungere `user_role: Optional[str] = None` a `BRSummary` schema
- [x] Aggiungere `user_share_percentage: Optional[Decimal]` a `BRSummary` schema
- [x] Modificare `get_summary()` per popolare user_role e user_share_percentage
- [x] Implementare `_sum_share_percentages()` helper per validazione ≤ 100%
- [x] Validazione share_percentage sum in `add_access()` e `update_access()`
- [x] Verificare test API esistenti aggiornati per `count`
- [x] `./dev.py api sync` per rigenerare il client TypeScript

---

## 2b. ✅ Backend — Bulk Endpoint + Schema Standardization (~0.5 giorni) — COMPLETATO 27 Feb 2026

> Questo step era originariamente "Step 3pre" ma è diventato uno step a sé per la mole di lavoro di standardizzazione schema.

**Implementazione effettiva**:

### 2b.1 Bulk Access Endpoint

- **`PUT /api/v1/brokers/{broker_id}/access`**: Atomic replace di tutta la configurazione accessi
- **`BRAccessBulkItem`** schema: user_id, role, share_percentage (0-1 fraction, validator per OWNER-only share > 0)
- **`BRAccessBulkUpdateRequest`**: RIMOSSO — l'endpoint accetta direttamente `List[BRAccessBulkItem]` (nessun wrapper, coerente col resto del progetto)
- **`BRAccessBulkResponse(BaseBulkResponse[BRAccessItem])`**: usa la classe base generica, eredita results/success_count/errors
- **`bulk_update_access()` in `broker_service.py`**: diff vs. stato attuale, transazione atomica, validazione (≤100% sum, almeno 1 OWNER, no duplicati, no utenti inesistenti)
- **Protezioni**: solo OWNER/superuser, no auto-rimozione last OWNER, no share>0 per EDITOR/VIEWER

### 2b.2 Schema Standardization

- **`BaseListResponse[T]`**: rimosso `count` (ridondante con `len(items)`). Usata in: `UploadListResponse`, `BRAccessListResponse`, `FXPairSourcesResponse`, `FXCurrenciesResponse`, `CountryListResponse`, `CurrencyListResponse`, `SectorListResponse`, `GlobalSettingsListResponse`, `UserSearchResponse`
- **`BRAccessBulkUpdateRequest(BaseListResponse[BRAccessBulkItem])`**: request body usa `items` (non `accesses`)
- **`BRAccessBulkResponse(BaseBulkResponse[BRAccessItem])`**: response body usa `results`/`success_count`/`errors` dalla classe base generica
- **Migrazione `total` → rimosso**: tutti gli endpoint che ritornano liste ora usano `BaseListResponse` con campo `items`
- **Migrazione `"accesses"` → `"items"` nei test**: tutti i test API che inviavano `json={"accesses": [...]}` ora inviano `json={"items": [...]}`
- **Frontend fix `PreferencesTab.svelte`**: `response.currencies` → `response.items ?? []`, `response.items` con nullish coalescing
- **Frontend fix `GlobalSettingsTab.svelte`**: già usava `response.items`, aggiunto `?? []` per safety
- **API sync**: `openapi.json` rigenerato, Zodios client aggiornato

### 2b.3 Test Suite

- **9 nuovi test** in `test_users_search.py`:
  - BULK-001: Bulk replace sets exact configuration
  - BULK-002: At least one OWNER required
  - BULK-003: Unlisted users removed
  - BULK-004: Non-OWNER rejected (403)
  - BULK-005: Duplicate user_ids rejected
  - SHARE-001: Sum > 100% blocked
  - SHARE-002: Sum = 100% allowed
  - SHARE-003: Sum < 100% allowed (phantom co-owner)
  - SHARE-004: share% > 0 rejected for EDITOR/VIEWER (422)
- **17/17 API tests pass** (tutti gli endpoint)
- **0 errori svelte-check** (frontend type-safe)
- **Fix select-components E2E test**: currency Escape close timing fix

### Tasks

- [x] Implementare `BRAccessBulkItem`, `BRAccessBulkUpdateRequest`, `BRAccessBulkResponse` in schemas
- [x] Implementare `bulk_update_access()` in `broker_service.py`
- [x] Creare endpoint `PUT /brokers/{id}/access` in `brokers.py`
- [x] Standardizzare `BaseListResponse` in tutti gli schemi (rimuovere `count`)
- [x] Fix frontend `PreferencesTab.svelte` per nuovo schema currencies
- [x] Fix E2E test `select-components.spec.ts` (Escape timing)
- [x] `./dev.py api sync` per rigenerare client TypeScript
- [x] 9 nuovi test per bulk endpoint + share validation
- [x] Tutti i 17 test API verdi
- [x] svelte-check 0 errori

---

## 3. Frontend — BrokerSharingModal (~2 giorni)

> **Rif. 05-08**: Sezione 10 "GDPR/Sharing Architecture" — Questo è il componente centrale per la condivisione. In Phase 5-8, `user_role` condiziona la visibilità di: bottone
> Share (solo OWNER), edit transazioni (OWNER/EDITOR), sync FX/Prices (OWNER/EDITOR), delete broker (solo OWNER). In Phase 8, `share_percentage` è usato per calcolare NAV/PnL/ROI
> pesato nella Dashboard (sezione 8.1 "KPI Cards").

### 3.0 Pre-requisito: Installare Apache ECharts

Apache ECharts è necessario per il grafico semi-circolare di ownership. Questa installazione anticipa anche Phase 5-8 dove ECharts verrà usato estensivamente per grafici FX, Asset prices e Dashboard KPIs.

```bash
cd frontend && npm install echarts
```

> **Nota**: L'installazione di ECharts era originariamente pianificata in Phase 5/8, ma la necessitiamo qui per il grafico di ownership. Aggiornare i plan Phase 5-8 di conseguenza.

### 3.1 Componente `BrokerSharingModal.svelte`

Percorso: `frontend/src/lib/components/brokers/BrokerSharingModal.svelte`

**Layout della modale (AGGIORNATO con input utente)**:

```
┌─────────────────────────────────────────────────────┐
│  Share Broker — "Nome Broker"                   ⟲ ✕ │
├─────────────────────────────────────────────────────┤
│                                                     │
│        ┌─────────────────────────┐                  │
│        │                         │                  │
│        │   [Half-Donut Chart]    │                  │
│        │   Owner ██ 50%          │                  │
│        │   Mario ██ 30%          │                  │
│        │   Free  ░░ 20%          │                  │
│        │                         │                  │
│        │   Allocated: 80%  [+]   │                  │
│        │   Available: 20%        │                  │
│        └─────────────────────────┘                  │
│                                                     │
│   📝 Editors:  [mario badge]                        │
│   👁 Viewers:  [anna badge]                         │
│                                                     │
│   ⚠️ Sum exceeds 100% (optional warning)            │
│                                                     │
│   ℹ️ OWNER: Full control                            │
│      EDITOR: Can modify transactions                │
│      VIEWER: Read only                              │
└─────────────────────────────────────────────────────┘
```

**Grafico Semi-Circolare (Half-Donut ECharts)**:

- Basato su `pie-half-donut` di Apache ECharts (tipo: `pie`, startAngle: 180, endAngle: 360)
- Ogni OWNER con share% > 0 ha un arco colorato con la sua icona/avatar vicino all'arco
- L'area "non allocata" (100% - Σshare%) è un arco grigio trasparente
- **Al centro del grafico**: "Allocated: XX%" e "Available: YY%" + pulsante "+" per aggiungere un utente
- Cliccando sull'icona di un utente vicino l'arco → apre modale di edit (modifica %, ruolo, rimuovi)
- Passando il mouse sull'arco → tooltip con info utente (già fornito da ECharts)
- **Sotto il grafico**: lista badge degli Editor e dei Viewer (non hanno arco perché share=0%)
- Ogni badge ha un "−" per rimuovere l'accesso

**Modale "Add/Edit User"**:

Quando si clicca "+" (add) o un'icona utente (edit), si apre una sotto-modale con:

- **Search/Select utente** (solo in Add, simile a SearchSelect broker con icona + nome e campo ricerca)
- **Ruolo** (SimpleSelect: OWNER/EDITOR/VIEWER)
- **Percentuale** (input numerico, non può superare la % residua)
- **Pulsante "Aggiungi"** (in add) o "Salva"/"Rimuovi" (in edit)

**Comportamento (BATCH SAVE — configurazione locale + salva tutto)**:

> ⚠️ **IMPORTANTE**: La modale opera in modalità "configurazione locale". NESSUNA API viene chiamata
> finché l'utente non clicca "Salva". Questo permette di comporre l'intera configurazione di sharing
> prima di inviarla al backend in un'unica transazione atomica.

- **Configurazione locale**: Tutte le modifiche (add user, change role, change share%, remove user) avvengono solo nello stato locale della modale
- **Salva batch**: Al click di "Salva", il frontend invia l'intera configurazione al backend tramite `PUT /brokers/{id}/access/bulk`
- **Annulla/Click fuori**: Se ci sono modifiche non salvate, modale di conferma arancione ("Annullare le modifiche?")
- **Add user**: SearchSelect con debounce 300ms → `GET /users/search?q=...&exclude_broker_id=X` → click su risultato → aggiunge all'elenco locale con ruolo/share% impostabili
- **Remove**: ConfirmModal ("Rimuovere l'accesso di {username}?") → rimuove dall'elenco locale
- **Success/Error**: Al salvataggio, il backend valida tutto e ritorna OK (toast verde) o errore (error banner con la causa del fail). Componente ErrorBanner/SuccessBanner già disponibili nel progetto.
- **Protezioni (validate sia localmente che lato backend)**:
    - Non si può rimuovere l'ultimo OWNER
    - Non si può degradare l'ultimo OWNER
    - Il ruolo OWNER self-demotion mostra warning extra
    - Warning banner SOPRA il grafico se Σ(share%) > 100%

### 3.1b ✅ Backend Endpoint — `PUT /brokers/{id}/access` — COMPLETATO (Step 2b)

> Questo endpoint è stato implementato nel Step 2b.

**Endpoint**: `PUT /api/v1/brokers/{broker_id}/access`  
**Auth**: Solo OWNER o superuser  
**Body**: `List[BRAccessBulkItem]` diretto (nessun wrapper)

```json
[
  {"user_id": 1, "role": "OWNER", "share_percentage": 0.5},
  {"user_id": 2, "role": "EDITOR", "share_percentage": 0},
  {"user_id": 3, "role": "VIEWER", "share_percentage": 0}
]
```

**Logica backend (transazione atomica)**:

1. Leggere gli accessi attuali dal DB
2. Calcolare le diff: utenti da aggiungere, da aggiornare, da rimuovere
3. Validare: Σ(share%) ≤ 100%, almeno un OWNER rimane, nessun utente inesistente
4. Applicare tutte le operazioni in un'unica transazione SQL
5. Se qualcosa fallisce → rollback totale → HTTP 400 con errore specifico
6. Se tutto OK → commit → HTTP 200 con la lista accessi aggiornata

**Schema request**: `List[BRAccessBulkItem]` diretto (nessun wrapper)  
**Schema response**: `BRAccessBulkResponse(BaseBulkResponse[BRAccessItem])`

**Tasks pre-step 3**:

- [x] Creare `BRAccessBulkItem` in `schemas/brokers.py` (BRAccessBulkUpdateRequest rimosso, endpoint usa `List[BRAccessBulkItem]` diretto)
- [x] Implementare `bulk_update_access()` in `broker_service.py`
- [x] Creare endpoint `PUT /brokers/{id}/access` in `brokers.py`
- [x] Test: 9 nuovi test in `test_users_search.py` (BULK + SHARE validation)
- [x] `./dev.py api sync` per rigenerare client TypeScript
- [x] Migrazione `"accesses"` → `"items"` in tutti i file test
- [x] `BRAccessBulkResponse` estende `BaseBulkResponse[BRAccessItem]`

### 3.2 Struttura componente

```svelte
<script lang="ts">
    import {ModalBase} from '$lib/components/ui/media';
    import {SearchSelect} from '$lib/components/ui/select';
    import {SimpleSelect} from '$lib/components/ui/select';
    import {ConfirmModal} from '$lib/components/table';
    import {zodiosApi} from '$lib/api';
    import type {BrokerAccessItem} from '$lib/types';
    // ...
</script>
```

### 3.3 Props

```typescript
interface BrokerSharingModalProps {
    open: boolean;
    brokerId: number;
    brokerName: string;
    onClose: () => void;
    onChanged?: () => void;  // per refresh broker detail
}
```

### Tasks

- [x] **Pre-step 3**: Implementare `PUT /brokers/{id}/access/bulk` nel backend (vedi 2b sopra) — ✅ COMPLETATO
- [ ] Installare `echarts` nel frontend (`npm install echarts`)
- [ ] Creare `BrokerSharingModal.svelte` con `ModalBase`
- [ ] Implementare Half-Donut Chart con ECharts (tipo `pie`, startAngle: 180, endAngle: 360)
    - Archi per ogni OWNER con share% > 0
    - Arco grigio per percentuale non allocata
    - Avatar/icona utenti vicino ai rispettivi archi
    - "Allocated: XX%" e "Available: YY%" al centro
    - Pulsante "+" al centro per aggiungere utente
- [ ] Sotto il grafico: liste badge per Editor e Viewer (con "−" per rimuovere)
- [ ] Sotto-modale "Add/Edit User":
    - SearchSelect per cercare utenti (simile a broker selector con icona + nome)
    - SimpleSelect per ruolo (OWNER/EDITOR/VIEWER)
    - Input numerico per % (limitato a residua)
    - Pulsanti Aggiungi/Salva/Rimuovi
- [ ] **Batch Save**: tutte le modifiche locali, pulsante "Salva" chiama `PUT /brokers/{id}/access/bulk`
- [ ] **Annulla con conferma**: modale arancione se ci sono modifiche non salvate
- [ ] Warning banner SOPRA il grafico se somma share% > 100%
- [ ] Success toast (verde) e Error banner al salvataggio
- [ ] Protection: last OWNER non rimovibile/degradabile (validazione locale + backend)
- [ ] Loading states per operazione di salvataggio
- [ ] Dark mode completo
- [ ] Esportare da `frontend/src/lib/components/brokers/index.ts` (se esiste)

---

## 4. ✅ Frontend — Integrazione in Broker Detail (~0.5 giorni) — COMPLETATO 1 Mar 2026

> **Rif. 05-08**: Sezione 10 "UX Flow — Broker Detail" — Il bottone Share qui diventa il punto di accesso per la configurazione multi-user. In Phase 6 (Assets), il ruolo condiziona
> se l'utente può aggiungere/modificare asset provider. In Phase 7 (Transactions), il ruolo condiziona se l'utente può creare/modificare transazioni (OWNER/EDITOR) o solo
> visualizzarle (VIEWER).

### 4.1 Bottone Share nella pagina `/brokers/[id]`

In `frontend/src/routes/(app)/brokers/[id]/+page.svelte`:

- Importare `Share2` da lucide-svelte
- Aggiungere bottone **Share** nel header, accanto al bottone Edit
- Visibile **solo se** `broker.user_role === 'OWNER'`
- Click → apre `BrokerSharingModal`

**Posizione nel layout** (accanto ai bottoni esistenti):

```svelte
{#if broker.user_role === 'OWNER'}
    <button on:click={() => sharingModalOpen = true}
            class="flex items-center space-x-2 px-4 py-2 border border-libre-green text-libre-green rounded-lg hover:bg-libre-green/10 transition-colors"
            data-testid="broker-share-button">
        <Share2 size={18}/>
        <span>{$_('brokers.sharing.title')}</span>
    </button>
{/if}
```

### 4.2 Icona share nella lista broker

Nella pagina `/brokers`, mostrare un badge/icona se il broker è condiviso con altri utenti. Opzionale ma utile per UX.

### Tasks

- [x] Importare `BrokerSharingModal` e `Share2` in broker detail page
- [x] Aggiungere stato `sharingModalOpen`
- [x] Bottone Share visibile solo per OWNER (`safeString(broker.user_role) === 'OWNER'`)
- [x] Passare `brokerId` e `brokerName` al modal
- [x] Callback `onChanged` per refresh broker data dopo modifiche
- [x] `data-testid="broker-share-button"` per E2E test
- [ ] (Opzionale) Badge "shared" nella lista broker

---

## 5. ✅ i18n — Chiavi di traduzione (~0.5 giorni) — COMPLETATO 27 Feb 2026

24 chiavi `brokers.sharing.*` aggiunte in EN/IT/FR/ES tramite `./dev.py i18n add`.

### Chiavi aggiunte

```
brokers.sharing.title                = "Share Broker" / "Condividi Broker" / "Partager le Courtier" / "Compartir Bróker"
brokers.sharing.addUser              = "Add User" / "Aggiungi Utente" / "Ajouter un Utilisateur" / "Agregar Usuario"
brokers.sharing.searchPlaceholder    = "Search by username..." / "Cerca per username..." / "Rechercher par nom d'utilisateur..." / "Buscar por nombre de usuario..."
brokers.sharing.role                 = "Role" / "Ruolo" / "Rôle" / "Rol"
brokers.sharing.sharePercentage      = "Ownership %" / "% Possesso" / "% de Propriété" / "% de Propiedad"
brokers.sharing.remove               = "Remove Access" / "Rimuovi Accesso" / "Supprimer l'Accès" / "Eliminar Acceso"
brokers.sharing.removeConfirm        = "Remove {username}'s access to this broker?" / "Rimuovere l'accesso di {username} a questo broker?" / ...
brokers.sharing.lastOwnerWarning     = "Cannot remove the last owner" / "Impossibile rimuovere l'ultimo proprietario" / ...
brokers.sharing.percentageWarning    = "Total ownership exceeds 100%. This is allowed but may overestimate net worth." / ...
brokers.sharing.selfDemoteWarning    = "You are about to change your own role. You may lose management access." / ...
brokers.sharing.noOtherUsers         = "No users found" / "Nessun utente trovato" / ...
brokers.sharing.saved                = "Access updated" / "Accesso aggiornato" / ...
brokers.sharing.added                = "User added" / "Utente aggiunto" / ...
brokers.sharing.removed              = "Access removed" / "Accesso rimosso" / ...
brokers.sharing.roleOwner            = "Owner — Full control" / "Proprietario — Controllo completo" / ...
brokers.sharing.roleEditor           = "Editor — Can modify transactions" / "Editor — Può modificare transazioni" / ...
brokers.sharing.roleViewer           = "Viewer — Read only" / "Visualizzatore — Sola lettura" / ...
brokers.sharing.legend               = "Roles explanation" / "Spiegazione ruoli" / ...
```

### Tasks

- [x] Usare `./dev.py i18n add` per aggiungere tutte le chiavi (24 chiavi `brokers.sharing.*`)
- [ ] Verificare con `./dev.py i18n audit`
- [ ] Test visuale in tutte e 4 le lingue

---

## 6. ✅ Backend Test — API Test Suite (~0.5 giorni) — COMPLETATO 27 Feb 2026

### 6.1 Nuovo file `backend/test_scripts/test_api/test_users_search.py`

Test:

- [x] `GET /users/search?q=test` → ritorna utenti con "test" nel nome
- [x] `GET /users/search?q=ab` → funziona (min 2 char)
- [x] `GET /users/search?q=a` → errore 422 (troppo corto)
- [x] `GET /users/search` senza `q` → errore 422
- [x] `GET /users/search?q=xxx&exclude_broker_id=1` → esclude utenti già con accesso
- [x] Non ritorna email per privacy
- [x] Richiede autenticazione (401 senza session)

### 6.2 Share % Validation Tests (in `test_users_search.py`)

- [x] SHARE-001: Cannot add access if sum would exceed 100%
- [x] SHARE-002: Can add access if sum exactly 100%
- [x] SHARE-003: Can add access if sum under 100%
- [x] SHARE-004: Cannot update share if sum would exceed 100%

### 6.3 Aggiornamento test esistenti

- [x] Verificare che test `test_broker_access.py` passi con il nuovo campo `avatar_url`
- [x] Verificare che test `test_broker_multi_user.py` passi con `user_role` nel summary
- [x] Tutti i test migrati da `total` a `count`

---

## 7. ✅ E2E Test — Frontend (~0.5 giorni) — COMPLETATO 1 Mar 2026

### 7.1 Nuovo file `frontend/e2e/broker-sharing.spec.ts`

**11 test implementati** — tutti passano:

Test group `Broker Sharing`:

- [x] **S1**: Share button visibile per OWNER su broker detail
- [x] **S2**: Share button apre BrokerSharingModal
- [x] **S3**: Modal mostra ownership chart section
- [x] **S4**: Modal mostra almeno l'OWNER corrente
- [x] **S5**: Add user button visibile
- [x] **S6**: Clicking add user mostra search form
- [x] **S7**: Save button disabilitato quando non ci sono modifiche
- [x] **S8**: Close modal con Escape
- [x] **S9**: Search for users returns results
- [x] **S10**: Warning se Σ(share%) > 100% (chart section visible)
- [x] **S11**: Dark mode - modale funziona in dark mode

### 7.2 Registrazione test

- [x] `front_broker_sharing()` aggiunta a `scripts/test_runner.py`
- [x] `"broker-sharing"` aggiunto a `TEST_REGISTRY`
- [x] `broker-sharing.spec.ts` aggiunto a `front_all()` specs list

---

## 8. ✅ Gallery Screenshot (~0.5 giorni) — COMPLETATO 1 Mar 2026

### Nuovi screenshot

- [x] `brokers/sharing-modal.png` — BrokerSharingModal aperta con ownership chart
- [x] Screenshot generati per desktop + mobile, light + dark, 4 lingue

### Tasks

- [x] Aggiunto test `broker sharing modal` in `gallery.spec.ts` sezione Media & Upload
- [x] Navigate to broker detail → click Share → screenshot del modal con chart

---

## 📊 Timeline Stimata

| Task                                   | Giorni        | Cumulativo | Status     |
|----------------------------------------|---------------|------------|------------|
| 0. Pre-step verifica schema e API      | 0.25          | 0.25       | ✅ DONE    |
| 1. Backend endpoint search users       | 0.5           | 0.75       | ✅ DONE    |
| 2. Backend avatar_url + user_role      | 0.5           | 1.25       | ✅ DONE    |
| 2b. Bulk endpoint + schema std + fixes | 0.5           | 1.75       | ✅ DONE    |
| 3. Frontend BrokerSharingModal         | 2.0           | 3.75       | ✅ DONE    |
| 4. Integrazione broker detail          | 0.5           | 4.25       | ✅ DONE    |
| 5. i18n chiavi                         | 0.25          | 4.5        | ✅ DONE    |
| 7. E2E tests                           | 0.5           | 5.0        | ⏳ TODO    |
| 8. Gallery screenshots                 | 0.25          | 5.25       | ⏳ TODO    |
| **Totale**                             | **~5.25 giorni** |          |            |

---

## 📁 File da Creare/Modificare

### Nuovi file

```
backend/app/api/v1/users.py                              # Endpoint search users
backend/app/schemas/users.py                              # UserSearchItem, UserSearchResponse
backend/test_scripts/test_api/test_users_search.py        # Test API search
frontend/src/lib/components/brokers/BrokerSharingModal.svelte  # Modale sharing
```

### File da modificare

```
backend/app/api/v1/router.py                    # Registrare users_router — ✅ FATTO
backend/app/services/user_service.py            # search_users() — ✅ FATTO + fix import
backend/app/schemas/brokers.py                  # avatar_url in BRAccessItem, user_role in BRSummary — ✅ FATTO
                                                # + BRAccessBulkItem, BRAccessBulkResponse — ✅ FATTO
backend/app/services/broker_service.py          # list_accesses() + get_summary() aggiornati — ✅ FATTO
                                                # + bulk_update_access() — ✅ FATTO
backend/app/api/v1/brokers.py                   # + PUT /brokers/{id}/access — ✅ FATTO
frontend/src/routes/(app)/brokers/[id]/+page.svelte  # Bottone Share — TODO
frontend/src/lib/i18n/en.json                   # i18n keys — ✅ FATTO (24 chiavi brokers.sharing.*)
frontend/src/lib/i18n/it.json                   # i18n keys — ✅ FATTO
frontend/src/lib/i18n/fr.json                   # i18n keys — ✅ FATTO
frontend/src/lib/i18n/es.json                   # i18n keys — ✅ FATTO
frontend/e2e/brokers.spec.ts                    # E2E tests sharing — TODO
frontend/e2e/gallery.spec.ts                    # Gallery screenshots — TODO
```

---

## Dependency Check

✅ Backend CRUD API per broker access — GIÀ IMPLEMENTATO  
✅ `share_percentage` nel model/schema — GIÀ IMPLEMENTATO  
✅ Share % validation ≤ 100% — IMPLEMENTATO (Step 2)  
✅ Frontend ModalBase, DataTable, SearchSelect, SimpleSelect, ConfirmModal — GIÀ IMPLEMENTATI  
✅ LazyImage per avatar preview — GIÀ IMPLEMENTATO  
✅ Multi-user test infrastructure — GIÀ IMPLEMENTATA  
✅ Endpoint search users — COMPLETATO (Step 1) + bug fix import 27 Feb  
✅ `avatar_url` in BRAccessItem — COMPLETATO (Step 2)  
✅ `user_role` in BRSummary — COMPLETATO (Step 2)  
✅ `count` standardizzato in tutti gli schemi — COMPLETATO (Step 1)  
✅ Test user search + share validation — COMPLETATI + bug fix 27 Feb (9/9 pass)  
✅ `PUT /brokers/{id}/access` bulk endpoint — COMPLETATO (Step 2b, 27 Feb)  
✅ Schema standardization `BaseListResponse` — COMPLETATO (Step 2b)  
✅ Frontend type fixes — COMPLETATO (PreferencesTab currencies → items)  
✅ 17/17 API tests pass — COMPLETATO  
✅ 0 errori svelte-check — COMPLETATO  
✅ i18n 24 chiavi brokers.sharing.* — COMPLETATO (Step 5)  
✅ BRAccessBulkResponse → BaseBulkResponse[BRAccessItem] — COMPLETATO  
✅ BRAccessBulkUpdateRequest rimosso → endpoint usa List[BRAccessBulkItem] — COMPLETATO  
✅ BrokerSharingModal — COMPLETATO (Step 3, 1 Mar 2026)  
✅ Integrazione in Broker Detail — COMPLETATO (Step 4, 1 Mar 2026)  
⬜ E2E Test — DA SCRIVERE (Step 7)  
⬜ Gallery screenshots — DA GENERARE (Step 8)

---

## 9. Enhancement Estetico e Bug Fix Post-Review — 1 Mar 2026

Feedback dall'utente dopo il primo deploy funzionale della modale. Prioritizzati come P0 (bug), P1 (funzionale), P2 (estetico).

### 9.1 Bug Fix (P0)

| # | Issue | Fix | File |
|---|-------|-----|------|
| 1 | Mobile: "+" button fisso, semicerchio trasla male | Rivedere posizionamento overlay center → usare posizionamento relativo al chart container con resize handler | BrokerSharingModal.svelte |
| 2 | Discard Changes ha bottone VERDE → deve essere GIALLO/amber | Aggiungere prop `warning` a ConfirmModal, stile amber per conferma non-distruttiva | ConfirmModal.svelte, BrokerSharingModal.svelte |
| 3 | VIEWER può cliccare Edit/Deposit/Upload/Import → deve essere disabilitato | Aggiungere `canEdit` computed basato su `user_role`, disabilitare bottoni per VIEWER. In files/ page, broker VIEWER nel selettore BRIM devono essere greyed-out | brokers/[id]/+page.svelte, files/+page.svelte, CashBalanceCard.svelte |
| 4 | Enter su input percentuale non conferma l'edit | Aggiungere `on:keydown` handler per Enter su tutti gli input % (edit + add form) | BrokerSharingModal.svelte |
| 5 | Selettore ruolo mostra descrizione completa nel bottone | Aggiungere chiavi i18n `roleOwnerShort/roleEditorShort/roleViewerShort`, usarle nei selettori, mantenere full description nella legenda | i18n/*.json, BrokerSharingModal.svelte |

### 9.2 Miglioramenti Estetici (P2)

| # | Miglioramento | Dettaglio |
|---|---------------|-----------|
| 6 | Arco chart più largo | Radius da `['50%', '80%']` → `['35%', '85%']` (spessore 50%) |
| 7 | Owners in badge come Editor/Viewer | Convertire sezione Owners da righe a badge pill con edit/remove inline |
| 8 | Avatar/icone utente vicino agli archi | Label ECharts rich text o overlay HTML per posizionare avatar sugli archi |
| 9 | Margini e bordi arrotondati tra fette | `itemStyle: {borderRadius: 6, borderColor, borderWidth: 2}`, `padAngle: 2` |
| 10 | Colori adiacenti con più distanza | Palette cromatica diversificata invece di tutte sfumature di verde |
| 11 | Drag-to-resize fette (opzionale, complesso) | Modalità edit con matita, drag archi per ridimensionare — ECharts non lo supporta nativamente, valutare alternativa con slider |

### Tasks Step 9

- [x] Fix 1: Mobile chart + center overlay responsive — posizionamento relativo con `left-0 right-0 flex justify-center`
- [x] Fix 2: ConfirmModal warning variant (amber button) — prop `warning` aggiunta, stile `btn-warning` amber
- [x] Fix 3: VIEWER role gating in broker detail + files page — `canEdit` computed, `user_role` aggiunto a `BRReadItem`, `disabledIds` in BrokerSearchSelect, CashBalanceCard gated
- [x] Fix 4: Enter key su input percentuale — `on:keydown` handler su tutti gli input % (edit, add form)
- [x] Fix 5: Role short labels i18n — 3 nuove chiavi `roleOwnerShort/roleEditorShort/roleViewerShort`, selettori usano icona + nome corto
- [x] Estetico 6: Arco chart più largo — radius `['35%', '85%']`, altezza 240px
- [x] Estetico 7: Owners in badge — convertiti a pill `rounded-full` con edit/remove, panel edit unificato sotto
- [x] Estetico 8: Label username vicino archi — ECharts rich text labels con nome e % outside
- [x] Estetico 9: Margini/bordi arrotondati fette — `borderRadius: 6`, `borderWidth: 2`, `padAngle: 2`
- [x] Estetico 10: Palette colori diversificata — 8 colori cromaticamente distanti (verde, blu, viola, rosso, arancio, teal, rosa, indaco)
- [ ] Estetico 11: Drag-to-resize (opzionale — complesso, ECharts non lo supporta nativamente, valutare slider alternativo)

---

## 10. Enhancement Round 2 — Post-Review 1 Mar 2026 (sera)

Secondo giro di feedback dopo le prime fix estetiche.

### 10.1 Bug Fix (P0)

| # | Issue | Fix | File |
|---|-------|-----|------|
| 12 | Mobile: chart ha width fissata a 640px (non responsive) — `style="height: 240px"` ma inner div forza 640px | Usare `ResizeObserver` per chart resize + rimuovere dimensioni fisse | BrokerSharingModal.svelte |
| 13 | VIEWER non vede lista file in broker detail (canEdit troppo restrittivo sui file) | Verificare che la sezione "file list" nel broker detail sia visibile anche ai VIEWER (read-only) — canEdit gating sbagliato su sezione che dovrebbe essere visible | brokers/[id]/+page.svelte |
| 14 | Mobile: bottone "Share Broker" manda nome a capo | Usare solo icona su schermi piccoli (`hidden sm:inline`), o abbreviare il testo | brokers/[id]/+page.svelte |
| 15 | Navigazione frecce nella ricerca utenti non funziona | Aggiungere keydown handler per ArrowUp/ArrowDown/Enter nel search dropdown | BrokerSharingModal.svelte |

### 10.2 Miglioramenti Estetici (P1/P2)

| # | Miglioramento | Dettaglio |
|---|---------------|-----------|
| 16 | Semicerchio ancora troppo stretto + avatar (non nome) su archi | Aumentare spessore arco a `['25%', '90%']`, usare immagini avatar come label ECharts (HTML overlay o rich text formatter con immagini) invece di testo |
| 17 | Icone ruolo nel dropdown colorate come legenda | Le icone nei selettori ruolo sono tutte nere — devono usare il colore corrispondente (amber per Owner, blue per Editor, gray per Viewer) |
| 18 | Add User form come modale sovrapposta | Il form "Add User" che si apre sotto causa problemi su schermi piccoli — convertire in ModalBase overlay |
| 19 | Files: VIEWER con broker pre-assegnato fa upload e riceve 403 | In files/ page, se solo 1 broker disponibile e è VIEWER, non pre-assegnare. Upload button deve essere disabilitato se broker selezionato è VIEWER |

### Tasks Step 10

- [x] Fix 12: Chart responsive con ResizeObserver — chart auto-resizes con parent container
- [x] Fix 14: Share button abbreviato su mobile — icona sola su schermi < sm, testo nascosto con `hidden sm:inline`
- [x] Fix 15: Arrow key navigation nel search dropdown — ArrowUp/ArrowDown/Enter handler aggiunto
- [x] Estetico 16: Arco più spesso + avatar overlay su archi — radius `['25%', '90%']`, avatar initial in colored circle con ECharts rich text
- [x] Estetico 17: Icone ruolo colorate nei dropdown — `getRoleIconColor()` helper, amber/blue/gray per Owner/Editor/Viewer
- [x] Estetico 18: Add User come modale overlay — convertito da inline form a ModalBase overlay (zIndex 60)
- [x] Fix 19: Files page VIEWER gating upload — auto-assign solo broker editabili, non VIEWER-only

---

## 11. Enhancement Round 3 — Layout Refactor & UX Improvements — 1 Mar 2026

Terzo giro di feedback: riorganizzazione completa del layout utenti, edit via modale, search unificata, fix bug ricerca utenti rimossi.

### 11.1 Miglioramenti Strutturali

| # | Miglioramento | Dettaglio |
|---|---------------|-----------|
| 20 | 3-Column layout per ruoli | Sostituire 3 sezioni separate (Owners/Editors/Viewers) con un `grid grid-cols-1 sm:grid-cols-3 gap-4`. Ogni colonna ha header con icona+label e badge impilati verticalmente. Ogni badge è un `<button>` cliccabile che apre l'edit modal. `max-h-48 overflow-y-auto` per scroll se molti utenti. |
| 21 | Edit come modal overlay | Sostituire panel inline di edit con `ModalBase` overlay (zIndex 60, maxWidth "sm"). Contiene: avatar+username in header, role dropdown, share% input (solo OWNER), bottone Delete danger nel footer sinistro, Cancel+Save nel footer destro. Apertura sia da click-su-badge sia da contesto programmatico. |
| 22 | Donut ancora più larga | Radius da `['25%', '90%']` → `['15%', '92%']` per massimizzare spessore ring |
| 23 | Bug: utente rimosso non riappare in ricerca | Rimosso `exclude_broker_id` dalla API call search. Tutto il filtraggio è ora client-side via `existingUserIds` Set reattivo. Quando un utente viene rimosso localmente, ricompare immediatamente nella ricerca. |
| 24 | Search unificata (combobox) in Add User | Search input + dropdown risultati + badge selezionato unificati in un unico widget combobox. Se utente selezionato: mostra badge inline con X per deselezionare. Se non selezionato: mostra input con dropdown. Nessun componente separato "Selected user badge". |
| 25 | Delete dentro Edit Modal | Il bottone "Remove" è nel footer sinistro dell'edit modal overlay, con icona Trash2 e stile danger. Disabilitato se si sta rimuovendo l'ultimo OWNER. |

### Tasks Step 11

- [x] Layout 20: Grid 3 colonne `grid-cols-1 sm:grid-cols-3` con Owners/Editors/Viewers separati, badge verticali cliccabili
- [x] Modal 21: Edit User come ModalBase overlay separata (`showEditModal` state), con role/share%/delete
- [x] Estetico 22: Radius donut `['15%', '92%']`
- [x] Bug 23: Rimosso `exclude_broker_id` da search API, filtraggio solo client-side via `existingUserIds`
- [x] UX 24: Search combobox unificato — selected state inline, search state con dropdown
- [x] UX 25: Delete button in edit modal footer con Trash2 icon
- [x] Fix: `div` inside `button` → `span` per validità HTML
- [x] Fix: Rimosso import `Minus` non utilizzato
- [ ] Estetico 11 (backlog): Drag-to-resize fette — opzionale, ECharts non supporta nativamente

---

## 12. Enhancement Round 4 — Avatar Fix & Multi-User Population — 1 Mar 2026

### 12.1 Bug Fix

| # | Issue | Fix | File |
|---|-------|-----|------|
| 26 | Avatar non visibile nei badge (solo iniziale mostrata) | LazyImage `display: inline-block` non occupava l'intero container `w-5 h-5`. Fix: `display: block` + rimosso `flex items-center justify-center` dal container avatar, aumentato da w-5 a w-6 (24px) e img_preview 48x48 | LazyImage.svelte, BrokerSharingModal.svelte |
| 27 | Populate DB aveva solo 3 utenti, insufficiente per demo sharing | Creati 8 utenti totali nella populate con password, avatar e assegnazioni broker diversificate. `populate_broker_user_access` crea utenti mancanti direttamente. | populate_mock_data.py, test_runner.py, test-users.ts |

### 12.2 Data Population: 8 Test Users

| Username | Avatar | Broker 1 (IBKR) | Broker 2 (DEGIRO) | Others |
|----------|--------|------------------|-------------------|--------|
| e2e_test_admin | men_01 | OWNER 40% | OWNER 100% | OWNER 100% tutti |
| e2e_test_user | woman_01 | OWNER 30% | VIEWER | EDITOR/VIEWER mix |
| e2e_test_user2 | men_02 | VIEWER | — | — |
| e2e_user_alice | woman_02 | OWNER 20% | EDITOR | — |
| e2e_user_bob | men_03 | EDITOR | — | VIEWER su Directa |
| e2e_user_carol | woman_03 | VIEWER | — | — |
| e2e_user_dave | men_04 | — | EDITOR | — |
| e2e_user_eve | woman_04 | VIEWER | VIEWER | — |

**Broker 1 (IBKR) sharing totale: 90% allocato (40+30+20), 10% disponibile**
→ Perfetto per screenshot gallery con 3 owners, 1 editor, 3 viewers.

### Tasks Step 12

- [x] Bug 26: LazyImage display block, avatar badge sizing increased to w-6 h-6 (24px), img_preview 48x48
- [x] Data 27: 8 utenti con avatar in populate_mock_data.py, test_runner.py, test-users.ts
- [x] Rimossa funzione `getRoleBadgeClass` inutilizzata
- [x] svelte-check: 0 errors, 0 warnings
- [x] Populate DB: tutti 8 utenti creati con avatar assegnati correttamente

---

## 13. Enhancement Round 5 — 3-Column Restore, Avatar in Chart, Legend Removal — 1 Mar 2026

Quinto giro di feedback: ripristino layout a 3 colonne affiancate, rimozione legenda in favore di descrizioni sotto ogni colonna, avatar reali nel grafico ECharts, badge cliccabili per edit.

### 13.1 Modifiche

| # | Miglioramento | Dettaglio |
|---|---------------|-----------|
| 28 | Ripristino 3 colonne affiancate | Il layout era tornato verticale. Ripristinato `grid grid-cols-1 sm:grid-cols-3 gap-4` con Owners, Editors, Viewers in colonne. Ogni colonna ha heading + descrizione breve sotto + badge verticali. |
| 29 | Descrizione sotto titolo colonna | Rimozione `roleHint` dall'header della modale. Aggiunta descrizione breve sotto ogni heading colonna: `ownerDesc`, `editorDesc`, `viewerDesc` (nuove chiavi i18n). |
| 30 | Avatar reali nel grafico ECharts | Usata API `image://url` di ECharts rich text per caricare l'avatar reale dell'utente sugli archi. Se avatar non disponibile, fallback a iniziale in cerchio colorato. |
| 31 | Badge cliccabili per edit | Rimossi i pulsanti edit/remove separati dai badge. Il badge intero è un `<button>` che apre il pannello di edit. Delete spostato dentro il pannello edit. |
| 32 | Nuove chiavi i18n | `brokers.sharing.ownerDesc`, `brokers.sharing.editorDesc`, `brokers.sharing.viewerDesc` in EN/IT/FR/ES |

### Tasks Step 13

- [x] Layout 28: Ripristinato grid 3 colonne con `grid-cols-1 sm:grid-cols-3`
- [x] UX 29: Rimosso roleHint dall'header, aggiunta descrizione sotto ogni heading colonna
- [x] Estetico 30: Avatar ECharts con `image://url` protocol, fallback a iniziale in cerchio
- [x] UX 31: Badge interi cliccabili, delete nel pannello edit
- [x] i18n 32: 3 nuove chiavi descrizione ruolo
- [x] Fix HTML: `span` al posto di `div` dentro `button` per validità HTML
- [x] svelte-check: 0 errors, 0 warnings
- [x] Frontend build: successo

---

## 14. Enhancement Round 6 — Circular Avatars in Chart, Contrast & DB Fix — 1 Mar 2026

Sesto giro di feedback: icone avatar circolari nel grafico ECharts, percentuale sotto icona con contrasto migliore, fix populate_mock_data per Coinbase duplicate.

### 14.1 Modifiche

| # | Miglioramento | Dettaglio |
|---|---------------|-----------|
| 33 | Avatar circolari nel grafico ECharts | `borderRadius: avatarSize/2` rende le immagini avatar circolari nel rich text. Aggiunto `borderColor` + `borderWidth: 2` per contrasto con l'arco. Dimensione aumentata da 40px a 44px. |
| 34 | Percentuale sotto icona con contrasto | Label `pct` con `fontWeight: 'bold'`, colore scuro/chiaro (dark: `#e2e8f0`, light: `#1e293b`), `textShadowColor` per leggibilità sopra i colori del grafico. |
| 35 | Fix Populate DB: UNIQUE constraint Coinbase | Aggiunto `session.flush()` prima della sezione Coinbase per rendere visibili le INSERT precedenti ai SELECT successivi. Evita duplicate INSERT per utenti già aggiunti nel loop principale. |
| 36 | Gallery: usa Coinbase per sharing modal | Il test `gallery.spec.ts` già punta a Coinbase (index 4) per lo screenshot sharing-modal con multi-user demo. |

### Tasks Step 14

- [x] Estetico 33: Avatar circolari con `borderRadius: avatarSize/2`, border bianco/scuro
- [x] Estetico 34: Label percentuale bold, colore ad alto contrasto, text-shadow
- [x] Bug 35: `session.flush()` prima della sezione Coinbase in `populate_mock_data.py`
- [x] Gallery 36: Confermato uso Coinbase per screenshot sharing-modal
- [x] svelte-check: 0 errors, 0 warnings
- [x] Populate DB: tutti 8 utenti + 27 accessi broker creati senza errori

