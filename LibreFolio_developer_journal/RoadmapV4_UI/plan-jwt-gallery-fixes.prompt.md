# Plan: JWT Auth Migration + Gallery Screenshot Fixes + Provider Icon Fallback

**Data creazione**: 19 Marzo 2026
**Status**: 📋 PIANIFICATO
**Priorità**: Alta (blocca gallery multi-worker + miglioramento UX provider icons)
**Stima**: ~3-4 ore
**Dipendenze**: `plan-fxTestingCleanup.prompt.md` Step 11 (gallery screenshots) completato

---

## Contesto

### Problema 1: Sessioni in-memory incompatibili con multi-worker
Le sessioni auth (`_sessions: dict` in `auth_service.py`) sono per-processo.
Con `--workers N` uvicorn, ogni processo ha il proprio dict → login su worker A,
richiesta successiva su worker B → sessione non trovata → 401 → 36/64 gallery test falliscono.

**Decisione**: Migrare a **JWT (JSON Web Tokens)** stateless.
- Il JWT contiene `user_id` + `exp` (scadenza), firmato con HMAC-SHA256
- Il secret viene generato randomicamente ad ogni avvio del server (uguale al comportamento attuale: riavvio = sessioni perse)
- Nessun storage server-side → funziona con qualsiasi numero di worker
- Logout = cancellazione cookie client-side (nessuna revoca server-side necessaria per ora)

### Problema 2: Gallery screenshots mancanti per FX
- **Add Pair (routes/chain)**: lo screenshot viene preso prima che il route picker sia aperto. Bisogna cliccare il bottone "Add Conversion Route" per espandere il picker e mostrare le rotte trovate dal DFS.
- **Provider Config**: l'icona del provider non è caricata. Bisogna dare più tempo al caricamento.

### Problema 3: Provider icon senza fallback
In `FxProviderSelect.svelte` (riga 601), le icone provider usano un semplice `<img>` senza fallback.
Se l'URL non carica (o è lento), si vede un'immagine rotta. Serve un fallback con `LazyImage` o un SVG
simile all'icona `Coins` usata nella sidebar per FX.

---

## Step 0 — Dipendenza: installare PyJWT

**File da modificare**: `Pipfile`

Aggiungere `PyJWT = "*"` nella sezione `[packages]`, poi `pipenv install`.

**Verifica**: `pipenv run python -c "import jwt; print(jwt.__version__)"`

---

## Step 1 — Migrare auth_service.py da session dict a JWT

**File da modificare**: `backend/app/services/auth_service.py`

### 1A. Rimuovere il session store in-memory

Eliminare completamente:
- `_sessions: dict[str, dict] = {}`
- `DEFAULT_SESSION_EXPIRE_HOURS = 24`
- `SESSION_ID_LENGTH = 64`
- `get_session(session_id)` 
- `get_user_id_from_session(session_id)`
- `delete_session(session_id)`
- `delete_user_sessions(user_id)`
- `cleanup_expired_sessions()`
- `get_active_session_count()`

### 1B. Aggiungere JWT functions

```python
import jwt  # PyJWT
import secrets

# Generate a random JWT secret at startup.
# This means all tokens are invalidated on server restart — same behavior
# as the previous in-memory session store, and acceptable for this app.
_JWT_SECRET: str = secrets.token_urlsafe(64)
_JWT_ALGORITHM: str = "HS256"

def create_jwt_token(user_id: int, ttl_hours: int) -> str:
    """Create a signed JWT token with user_id and expiration."""
    now = utcnow()
    payload = {
        "sub": user_id,          # subject = user ID
        "iat": now,              # issued at
        "exp": now + timedelta(hours=ttl_hours),  # expiration
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Optional[int]:
    """Decode and validate a JWT token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
```

### 1C. Funzioni legacy → stub o rimozione

| Vecchia funzione | Nuova | Note |
|---|---|---|
| `create_session(user_id, ttl)` | `create_jwt_token(user_id, ttl)` | Stesso contratto, ritorna stringa |
| `get_user_id_from_session(sid)` | `decode_jwt_token(token)` | Stesso contratto, ritorna `Optional[int]` |
| `delete_session(sid)` | **Rimuovere** | JWT stateless, il logout cancella solo il cookie |
| `delete_user_sessions(uid)` | **Rimuovere** | Non necessario con JWT stateless |
| `cleanup_expired_sessions()` | **Rimuovere** | JWT scade automaticamente (campo `exp`) |
| `get_active_session_count()` | **Rimuovere** | Non tracciabile con JWT stateless |

### 1D. Impatto multi-worker

Con JWT, `_JWT_SECRET` è generato a livello di modulo. Con uvicorn multi-worker (fork), il
secret è generato nel processo parent PRIMA del fork → tutti i worker ereditano lo stesso
secret → i token sono validi su qualsiasi worker. ✅

**Verifica**: Il `_JWT_SECRET` viene inizializzato a livello di modulo (top-level), quindi
il parent process lo crea, poi `fork()` lo copia in tutti i figli.

---

## Step 2 — Aggiornare auth.py (API endpoints)

**File da modificare**: `backend/app/api/v1/auth.py`

### 2A. Aggiornare imports

```python
# Rimuovere:
from backend.app.services.auth_service import (
    verify_password,
    hash_password,
    create_session,           # → create_jwt_token
    get_user_id_from_session, # → decode_jwt_token
    delete_session,           # → rimuovere (logout = cookie delete only)
)

# Aggiungere:
from backend.app.services.auth_service import (
    verify_password,
    hash_password,
    create_jwt_token,
    decode_jwt_token,
)
```

### 2B. Endpoint `login` (riga 98)

Cambiare `session_id = create_session(user.id, ttl_hours)` → `token = create_jwt_token(user.id, ttl_hours)`.
Nel `response.set_cookie`, `value=session_id` → `value=token`.

### 2C. Endpoint `logout` (riga 158)

Rimuovere la chiamata `delete_session(session_id)`. Logout = solo cancellazione cookie.

### 2D. Dependency `get_current_user` (riga 56)

Cambiare `user_id = get_user_id_from_session(session_id)` → `user_id = decode_jwt_token(session_id)`.
(La variabile si chiama `session_id` perché viene dal cookie "session", ma ora contiene un JWT token.)

### 2E. Rinominare variabile per chiarezza (opzionale)

`session_id = get_session_cookie(request)` → `token = get_session_cookie(request)` per coerenza.
Il nome del cookie resta `"session"` per backward compatibility client-side.

---

## Step 3 — Aggiornare user_service.py

**File da modificare**: `backend/app/services/user_service.py`

Riga 14: `from backend.app.services.auth_service import hash_password, delete_user_sessions`

`delete_user_sessions` non esiste più. Rimuovere l'import e tutti i call-site.
Cercare dove viene chiamata `delete_user_sessions()` e rimuovere/commentare quelle chiamate.

---

## Step 4 — Rimuovere il warning in auth_service.py

Il commento `⚠️ WARNING: Sessions are stored in a per-process dict...` (righe 65-74)
va sostituito con un commento che spiega la strategia JWT.

---

## Step 5 — Fix gallery screenshots FX

**File da modificare**: `frontend/e2e/gallery.spec.ts`

### 5A. Add Pair - Direct Routes (riga 635)

Dopo aver selezionato entrambe le valute (riga 674), il route picker non è ancora visibile.
Bisogna:
1. Attendere il bottone "Add Conversion Route" (`fx-route-select` + button con `$_('fx.route.addRoute')`)
2. Cliccare il bottone per espandere il picker
3. Attendere che le rotte DFS siano calcolate e renderizzate (~1-2s)
4. Fare lo screenshot

```typescript
// After selecting both currencies, wait for route select to appear
await page.waitForTimeout(1500);
// Open the route picker
const addRouteBtn = modal.locator('[data-testid="fx-route-select"] button').filter({hasText: /add/i}).first();
if (await addRouteBtn.isVisible({timeout: 3000}).catch(() => false)) {
    await addRouteBtn.click();
    await page.waitForTimeout(2000); // Wait for DFS pathfinding + render
}
await screenshot(...);
```

### 5B. Add Pair - Chain (riga 683)

Stessa fix di 5A per il test chain (NOK/CHF).

### 5C. Provider Config (riga 923)

Dopo aver aperto il modal con `goToFxDetailPage` + click su provider button, aggiungere
un `waitForTimeout(2000)` extra prima dello screenshot per permettere il caricamento delle
icone provider.

---

## Step 6 — Fallback icona provider con LazyImage

**File da modificare**: `frontend/src/lib/components/ui/select/FxProviderSelect.svelte`

### 6A. Import LazyImage

Aggiungere: `import LazyImage from '$lib/components/ui/media/LazyImage.svelte';`

### 6B. Sostituire `<img>` con `<LazyImage>` (riga 601)

Attualmente:
```svelte
{#if iconUrl}
    <img src={iconUrl} alt={prov.code} class="w-4 h-4 rounded object-contain flex-shrink-0" />
{:else}
    <span class="w-4 h-4 flex items-center justify-center rounded text-[7px] font-bold flex-shrink-0">
        {getProviderInitials(prov.code)}
    </span>
{/if}
```

Nuovo: usare LazyImage con placeholder `icon` e fallback alle initials (il componente
LazyImage mostra il placeholder SVG durante il loading, e le initials se l'immagine fallisce):

```svelte
{#if iconUrl}
    <LazyImage
        src={iconUrl}
        alt={prov.code}
        placeholder="icon"
        width="16px"
        height="16px"
        rounded={true}
    />
{:else}
    <span class="w-4 h-4 flex items-center justify-center rounded text-[7px] font-bold flex-shrink-0">
        {getProviderInitials(prov.code)}
    </span>
{/if}
```

### 6C. Aggiungere placeholder "provider" a LazyImage (opzionale)

**File da modificare**: `frontend/src/lib/components/ui/media/LazyImage.svelte`

Aggiungere un nuovo placeholder type `'provider'` che usa un SVG simile all'icona `Coins`
(lucide) — due cerchi sovrapposti che rappresentano monete/valute:

```typescript
export let placeholder: 'generic' | 'avatar' | 'broker' | 'icon' | 'provider' = 'generic';
```

```typescript
provider: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
    <rect width="100" height="100" fill="#e5e7eb" rx="10"/>
    <circle cx="42" cy="45" r="20" stroke="#9ca3af" stroke-width="3" fill="none"/>
    <circle cx="58" cy="55" r="20" stroke="#9ca3af" stroke-width="3" fill="none"/>
</svg>`,
```

E usare `placeholder="provider"` nel FxProviderSelect.

---

## Step 7 — Verifica

### 7A. Test unitari auth

Eseguire i test API esistenti per verificare che login/logout/register funzionino con JWT:
```bash
pipenv run python -m pytest backend/test_scripts/test_api/ -v
```

### 7B. Gallery test

Eseguire la gallery con multi-worker per verificare che i 36 test falliti ora passino:
```bash
./dev.py mkdocs gallery
```

### 7C. Verifica manuale

1. Avviare server con `./dev.py server --workers 3`
2. Aprire browser, login
3. Navigare varie pagine (dashboard, settings, fx, brokers)
4. Verificare che non ci siano 401 inattesi
5. Logout → verificare redirect a login page

---

## Impatto sui file

| File | Tipo modifica |
|---|---|
| `Pipfile` | Aggiungere `PyJWT` |
| `backend/app/services/auth_service.py` | **Riscrittura sezione sessioni** → JWT |
| `backend/app/api/v1/auth.py` | Aggiornare import + chiamate |
| `backend/app/services/user_service.py` | Rimuovere import `delete_user_sessions` |
| `frontend/e2e/gallery.spec.ts` | Fix wait per route picker + provider icons |
| `frontend/e2e/fx/fx-helpers.ts` | Timeout già aumentati (5s→15s) ✅ |
| `frontend/e2e/fixtures/auth-helpers.ts` | Timeout già aumentati (10s→20s) ✅ |
| `frontend/src/lib/components/ui/select/FxProviderSelect.svelte` | LazyImage per icone provider |
| `frontend/src/lib/components/ui/media/LazyImage.svelte` | Nuovo placeholder `provider` |

---

## Rischi

| Rischio | Mitigazione |
|---|---|
| `_JWT_SECRET` condiviso pre-fork? | Sì: Python module-level init avviene nel parent, fork() copia la memoria → tutti i worker hanno lo stesso secret |
| JWT token nel cookie troppo grande? | ~200 bytes per un payload minimale (sub, iat, exp). Trascurabile. |
| PyJWT vs python-jose? | PyJWT è più leggero (solo HMAC), python-jose supporta JWE/JWS ma è overengineering |
| Test API rotti? | I test API usano session cookie — il cookie ora contiene JWT invece di session_id, ma il contratto HTTP è identico (set-cookie / cookie header) |
| Logout non invalida il token? | Accettato: il token scade naturalmente con il TTL. Il cookie viene cancellato client-side. Equivalente al comportamento attuale (chiudere il browser = sessione persa). Ban/blacklist è un TODO futuro se necessario. |

