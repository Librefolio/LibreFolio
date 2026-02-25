# Plan: Broker Sharing GUI (Phase 4.8 — BrokerSharingModal)

**Durata**: ~5 giorni  
**Dipendenze**: Schema pre-work (share_percentage già implementato)  
**Status**: ⏳ TODO  
**Priorità**: ALTA — Deve essere completato PRIMA di Phase 5  
**Riferimento 05-08**: Sezioni 3.5, 10, 11 di `plan-phase05-to-08-upgrade.md`

---

## 📋 Contesto

Il backend ha già le API CRUD complete per il broker access control:

- `GET /api/v1/brokers/{broker_id}/access` — lista accessi
- `POST /api/v1/brokers/{broker_id}/access` — aggiungi utente
- `PATCH /api/v1/brokers/{broker_id}/access/{target_user_id}` — modifica ruolo/share%
- `DELETE /api/v1/brokers/{broker_id}/access/{target_user_id}` — rimuovi accesso

I test API (16/16) passano. Manca:

1. **Nessun endpoint per cercare altri utenti** (necessario per "Add User")
2. **`avatar_url` non incluso** in `BRAccessItem` (necessario per mostrare avatar)
3. **`user_role` non incluso** in `BRSummary` (necessario per mostrare/nascondere il bottone Share)
4. **Nessun componente frontend** per gestire lo sharing

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

- [ ] Eseguire `./dev.py test api broker-access` — verificare che passi
- [ ] Eseguire `./dev.py test api broker-multi` — verificare che passi
- [ ] Eseguire `./dev.py test api transactions` — verificare che passi
- [ ] Eseguire `./dev.py front check` — 0 errori
- [ ] Verificare su API Docs che `share_percentage` appare negli endpoint broker access
- [ ] Verificare su API Docs che `cost_basis_override` appare negli endpoint transactions
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

## 1. Backend — Nuovo endpoint ricerca utenti (~0.5 giorni)

> **Rif. 05-08**: Sezione 3.5 "Phase 4.8 — Broker Sharing GUI" — Questo endpoint è necessario anche per Phase 8 (Dashboard) dove si mostrano gli utenti condivisi per ogni broker
> nel breakdown KPI.

### 1.1 Nuovo file `backend/app/api/v1/users.py`

Creare un nuovo router per gli endpoint utente (separazione di responsabilità):

```
GET /api/v1/users/search?q={query}&exclude_broker_id={id}
```

**Specifiche**:

- Parametro `q`: stringa minimo 2 caratteri, ricerca `ILIKE` su username e email
- Parametro opzionale `exclude_broker_id`: esclude gli utenti che hanno già accesso al broker
- Limite: max 10 risultati
- Richiede autenticazione (qualsiasi utente loggato può cercare altri utenti)
- **Non esporre email** per privacy — solo username + avatar + id

### 1.2 Schema `UserSearchItem`

In `backend/app/schemas/auth.py` o nuovo file `backend/app/schemas/users.py`:

```python
class UserSearchItem(BaseModel):
    """Minimal user info for search results."""
    id: int
    username: str
    avatar_url: Optional[str] = None  # from UserSettings


class UserSearchResponse(BaseModel):
    """Response for user search endpoint."""
    users: List[UserSearchItem]
    total: int
```

### 1.3 Service: `search_users` in `user_service.py`

```python
async def search_users(
        session: AsyncSession,
        query: str,
        exclude_broker_id: Optional[int] = None,
        limit: int = 10
        ) -> list[dict]:
    """Search users by username (ILIKE). Optionally exclude users already on a broker."""
```

- JOIN con `UserSettings` per `avatar_url`
- Se `exclude_broker_id` fornito, LEFT JOIN + WHERE filter per escludere utenti già con accesso

### 1.4 Registrare router in `router.py`

Aggiungere il nuovo router `users_router` in `backend/app/api/v1/router.py`.

### Tasks

- [ ] Creare `backend/app/api/v1/users.py` con endpoint `GET /users/search`
- [ ] Creare schema `UserSearchItem` + `UserSearchResponse`
- [ ] Aggiungere `search_users()` in `user_service.py`
- [ ] Registrare `users_router` in `router.py`
- [ ] Test: `backend/test_scripts/test_api/test_users_search.py`

---

## 2. Backend — Aggiungere campi mancanti (~0.5 giorni)

> **Rif. 05-08**: Sezione 2.1 "share_percentage" + Sezione 10 "GDPR/Sharing Architecture" — `avatar_url` e `user_role` servono anche a Phase 8 (Dashboard) per mostrare avatar
> utenti nel breakdown e decidere se un broker pesa sul Net Worth dell'utente corrente (share > 0%).

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

- [ ] Aggiungere `avatar_url: Optional[str] = None` a `BRAccessItem` schema
- [ ] Modificare `list_accesses()` per JOIN con UserSettings e popolare avatar_url
- [ ] Aggiungere `user_role: Optional[str] = None` a `BRSummary` schema
- [ ] Modificare `get_summary()` per popolare user_role
- [ ] Verificare test API esistenti (16/16 devono continuare a passare)
- [ ] `./dev.py api sync` per rigenerare il client TypeScript

---

## 3. Frontend — BrokerSharingModal (~2 giorni)

> **Rif. 05-08**: Sezione 10 "GDPR/Sharing Architecture" — Questo è il componente centrale per la condivisione. In Phase 5-8, `user_role` condiziona la visibilità di: bottone
> Share (solo OWNER), edit transazioni (OWNER/EDITOR), sync FX/Prices (OWNER/EDITOR), delete broker (solo OWNER). In Phase 8, `share_percentage` è usato per calcolare NAV/PnL/ROI
> pesato nella Dashboard (sezione 8.1 "KPI Cards").

### 3.1 Componente `BrokerSharingModal.svelte`

Percorso: `frontend/src/lib/components/brokers/BrokerSharingModal.svelte`

**Layout della modale**:

```
┌─────────────────────────────────────────────────┐
│  Share Broker — "Nome Broker"              ⟲  ✕ │
├─────────────────────────────────────────────────┤
│                                                 │
│  👤 Search user to add...            [Add ▸]    │
│                                                 │
│  ┌─────────────────────────────────────────────┐│
│  │ Avatar │ Username │ Role    │ Share% │ ✕    ││
│  │────────┼──────────┼─────────┼────────┼──────││
│  │ 🟢     │ admin    │ [OWNER▼]│ [100 ] │  —   ││
│  │ 🔵     │ mario    │ [EDITOR]│ [ 50 ] │ [🗑] ││
│  │ 🟣     │ anna     │ [VIEWER]│ [  0 ] │ [🗑] ││
│  └─────────────────────────────────────────────┘│
│                                                 │
│  ⚠️ La somma delle % di possesso è 150%        │
│     (consentito ma potrebbe sovrastimare il     │
│      patrimonio)                                │
│                                                 │
│  ℹ️ OWNER: Controllo totale                    │
│     EDITOR: Modifica transazioni                │
│     VIEWER: Sola lettura                        │
└─────────────────────────────────────────────────┘
```

**Comportamento**:

- **Save inline**: ogni modifica di ruolo/share% chiama subito PATCH API
- **Add user**: SearchSelect con debounce 300ms → chiama `GET /users/search?q=...&exclude_broker_id=X` → click su risultato → chiama POST → refresh lista
- **Remove**: ConfirmModal ("Rimuovere l'accesso di {username}?") → DELETE API → refresh
- **Protezioni**:
    - Non si può rimuovere l'ultimo OWNER
    - Non si può degradare l'ultimo OWNER
    - Il ruolo OWNER self-demotion mostra warning extra
    - Warning giallo se Σ(share%) > 100%

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

- [ ] Creare `BrokerSharingModal.svelte` con `ModalBase`
- [ ] Sezione "Add User" con `SearchSelect` e API search
- [ ] DataTable (o tabella leggera) per lista accessi con colonne:
    - Avatar (LazyImage con preview) + Username
    - Role (SimpleSelect inline — OWNER/EDITOR/VIEWER)
    - Share % (input numerico con frecce ↑↓)
    - Azione rimuovi (icona 🗑 con ConfirmModal)
- [ ] Save inline su ogni modifica (PATCH per role/share%, DELETE per remove)
- [ ] Warning banner se somma share% > 100%
- [ ] Protection: last OWNER non rimovibile/degradabile
- [ ] Loading states per ogni operazione
- [ ] Error handling con toast/banner
- [ ] Legenda ruoli in fondo alla modale
- [ ] Dark mode completo
- [ ] Esportare da `frontend/src/lib/components/brokers/index.ts` (se esiste)

---

## 4. Frontend — Integrazione in Broker Detail (~0.5 giorni)

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

- [ ] Importare `BrokerSharingModal` e `Share2` in broker detail page
- [ ] Aggiungere stato `sharingModalOpen`
- [ ] Bottone Share visibile solo per OWNER
- [ ] Passare `brokerId` e `brokerName` al modal
- [ ] Callback `onChanged` per refresh broker data dopo modifiche
- [ ] `data-testid="broker-share-button"` per E2E test
- [ ] (Opzionale) Badge "shared" nella lista broker

---

## 5. i18n — Chiavi di traduzione (~0.5 giorni)

### Chiavi da aggiungere

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

- [ ] Usare `./dev.py i18n add` per aggiungere tutte le chiavi
- [ ] Verificare con `./dev.py i18n audit`
- [ ] Test visuale in tutte e 4 le lingue

---

## 6. Backend Test — API Test Suite (~0.5 giorni)

### 6.1 Nuovo file `backend/test_scripts/test_api/test_users_search.py`

Test:

- [ ] `GET /users/search?q=test` → ritorna utenti con "test" nel nome
- [ ] `GET /users/search?q=ab` → funziona (min 2 char)
- [ ] `GET /users/search?q=a` → errore 422 (troppo corto)
- [ ] `GET /users/search` senza `q` → errore 422
- [ ] `GET /users/search?q=xxx&exclude_broker_id=1` → esclude utenti già con accesso
- [ ] Non ritorna email per privacy
- [ ] Richiede autenticazione (401 senza session)

### 6.2 Aggiornamento test esistenti

- [ ] Verificare che test `test_broker_access.py` passi con il nuovo campo `avatar_url`
- [ ] Verificare che test `test_broker_multi_user.py` passi con `user_role` nel summary

---

## 7. E2E Test — Frontend (~0.5 giorni)

### 7.1 Estendere `frontend/e2e/brokers.spec.ts` o nuovo file

Test group `Broker Sharing`:

- [ ] **S1**: Share button visibile solo per OWNER (user1 crea broker → vede Share, user2 non loggato → no Share)
- [ ] **S2**: Click Share → BrokerSharingModal si apre con lista accessi
- [ ] **S3**: Lista mostra almeno l'OWNER corrente (avatar/username/role/share%)
- [ ] **S4**: Ricerca utente → risultati appaiono in dropdown
- [ ] **S5**: Aggiunta utente → appare nella lista con ruolo default VIEWER
- [ ] **S6**: Modifica ruolo da VIEWER a EDITOR → salva inline
- [ ] **S7**: Modifica share% → salva inline
- [ ] **S8**: Rimuovi utente → ConfirmModal → conferma → utente rimosso dalla lista
- [ ] **S9**: Warning se Σ(share%) > 100%
- [ ] **S10**: Non si può rimuovere l'ultimo OWNER → messaggio errore
- [ ] **S11**: Dark mode → modale e componenti coerenti

### 7.2 Multi-user test

- [ ] **S12**: User2 aggiunto come VIEWER → login con user2 → vede il broker nella lista
- [ ] **S13**: User2 VIEWER → non vede bottone Share
- [ ] **S14**: User2 VIEWER → non vede bottone Edit (se implementato)

---

## 8. Gallery Screenshot (~0.5 giorni)

### Nuovi screenshot

- [ ] Broker detail con bottone Share visibile
- [ ] BrokerSharingModal aperta con lista accessi
- [ ] BrokerSharingModal con ricerca utente aperta
- [ ] BrokerSharingModal con warning >100%

### Tasks

- [ ] Aggiungere scenario in `gallery.spec.ts` sezione Brokers
- [ ] Generate per desktop + mobile, light + dark, 4 lingue

---

## 📊 Timeline Stimata

| Task                              | Giorni        | Cumulativo |
|-----------------------------------|---------------|------------|
| 0. Pre-step verifica schema e API | 0.25          | 0.25       |
| 1. Backend endpoint search users  | 0.5           | 0.75       |
| 2. Backend avatar_url + user_role | 0.5           | 1.25       |
| 3. Frontend BrokerSharingModal    | 2.0           | 3.25       |
| 4. Integrazione broker detail     | 0.5           | 3.75       |
| 5. i18n chiavi                    | 0.25          | 4.0        |
| 6. Backend tests                  | 0.5           | 4.5        |
| 7. E2E tests                      | 0.5           | 5.0        |
| 8. Gallery screenshots            | 0.25          | 5.25       |
| **Totale**                        | **~5 giorni** |            |

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
backend/app/api/v1/router.py                    # Registrare users_router
backend/app/services/user_service.py            # search_users()
backend/app/schemas/brokers.py                  # avatar_url in BRAccessItem, user_role in BRSummary
backend/app/services/broker_service.py          # list_accesses() + get_summary() aggiornati
frontend/src/routes/(app)/brokers/[id]/+page.svelte  # Bottone Share
frontend/src/lib/i18n/en.json                   # i18n keys
frontend/src/lib/i18n/it.json                   # i18n keys
frontend/src/lib/i18n/fr.json                   # i18n keys
frontend/src/lib/i18n/es.json                   # i18n keys
frontend/e2e/brokers.spec.ts                    # E2E tests sharing
frontend/e2e/gallery.spec.ts                    # Gallery screenshots
```

---

## Dependency Check

✅ Backend CRUD API per broker access — GIÀ IMPLEMENTATO  
✅ `share_percentage` nel model/schema — GIÀ IMPLEMENTATO  
✅ Frontend ModalBase, DataTable, SearchSelect, SimpleSelect, ConfirmModal — GIÀ IMPLEMENTATI  
✅ LazyImage per avatar preview — GIÀ IMPLEMENTATO  
✅ Multi-user test infrastructure — GIÀ IMPLEMENTATA  
⬜ Endpoint search users — DA CREARE  
⬜ avatar_url in BRAccessItem — DA AGGIUNGERE  
⬜ user_role in BRSummary — DA AGGIUNGERE  
⬜ BrokerSharingModal — DA CREARE  

