# Phase 1: Foundation & Frontend Auth

**Status**: ✅ COMPLETATA (8 Gennaio 2026)  
**Durata**: 3 giorni  
**Priorità**: P0 (Critica)

---

## Obiettivo

Setup delle fondamenta frontend: internazionalizzazione, generazione schema API, client API, e store autenticazione.

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili, seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli del componente.

**Componenti/Stores creati in questa fase**:

- `language.ts` store - Gestione lingua app
- `auth.ts` store - Gestione autenticazione
- `api/client.ts` - API client base

---

## 1.1 i18n Setup (0.5 giorni) ✅

### Implementazione

1. **Dipendenze Installate**:
   ```bash
   npm install svelte-i18n date-fns
   ```

2. **Struttura Traduzioni**:
   ```
   src/lib/i18n/
   ├── index.ts      # Config e init
   ├── en.json       # English
   ├── it.json       # Italiano  
   ├── fr.json       # Français
   └── es.json       # Español
   ```

3. **Language Store** (`src/lib/stores/language.ts`):
    - Store `currentLanguage` con sync a svelte-i18n
    - `currentLanguageName`, `currentLanguageFlag` derived stores
    - `availableLanguages` array per UI selectors

4. **Funzionalità**:
    - Auto-detect lingua browser con fallback a English
    - Persistenza preferenza in localStorage
    - Language selector con bandiere emoji

### File Creati

- `frontend/src/lib/i18n/index.ts`
- `frontend/src/lib/i18n/en.json`
- `frontend/src/lib/i18n/it.json`
- `frontend/src/lib/i18n/fr.json`
- `frontend/src/lib/i18n/es.json`
- `frontend/src/lib/stores/language.ts`

---

## 1.2 OpenAPI Schema Generation (1 giorno) ✅

### Approccio Scelto

**Opzione B: Generazione statica da codice Python** (senza server running)

- Veloce e CI/CD-friendly
- Esteso script esistente `list_api_endpoints.py`

### Implementazione

1. **Script Esteso** (`backend/test_scripts/list_api_endpoints.py`):
    - `--list` / `-l`: Lista endpoints (default)
    - `--openapi` / `-o`: Export OpenAPI a stdout
    - `--openapi-file PATH` / `-f PATH`: Export a file

2. **Nuovi Comandi dev.sh**:
    - `api:schema` - Esporta a `frontend/src/lib/api/openapi.json`
    - `api:client` - Genera TypeScript client con openapi-zod-client
    - `api:sync` - Esegue entrambi

3. **Dipendenze Frontend**:
   ```bash
   npm install -D openapi-zod-client@1.18.3 zod@3.24.1 @zodios/core@10.9.6
   ```

### File Generati

- `frontend/src/lib/api/openapi.json` (8100+ righe)

---

## 1.3 API Client Base (1 giorno) ✅

### Implementazione

**File**: `src/lib/api/client.ts`

```typescript
// Funzionalità implementate:
-apiCall<T>()
generic
wrapper
- credentials
:
'include'
per
session
cookie
- Header
Accept - Language
da
localStorage
- Custom
ApiError

class con

status / statusText / data
- Timeout
handling
con
AbortController
- Error
handling: 401→login, 403, 404, 422, network
errors
- Convenience
methods: api.get(),
.
post(),
.
put(),
.
patch(),
.
delete()
```

### Export

```typescript
// src/lib/api/index.ts
export {api, apiCall, ApiError} from './client';
```

### File Creati

- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/api/index.ts`

---

## 1.4 Authentication Store (0.5 giorni) ✅

### Implementazione

**File**: `src/lib/stores/auth.ts`

```typescript
// Store State:
interface AuthState {
    user: User | null;
    isLoading: boolean;
    error: string | null;
    isInitialized: boolean;
}

// Actions:
-login(username, password) → POST / auth / login
- logout() → POST / auth / logout + redirect
- checkAuth() → GET / auth / me
- clearError()
- reset()

// Derived Stores:
- currentUser
- isAuthenticated
- isAuthLoading
- authError
- isAuthInitialized
```

### Route Protection

**File**: `src/hooks.server.ts`

- Intercetta navigazione
- Redirect a `/login?redirect=...` se non autenticato
- Lista route pubbliche configurabile

### Login Page Updated

**File**: `src/routes/+page.svelte`

- Integrato con auth store
- Error display da `$authError`
- Loading state da `$isAuthLoading`
- Redirect a dashboard dopo successo

### File Creati/Modificati

- `frontend/src/lib/stores/auth.ts`
- `frontend/src/hooks.server.ts`
- `frontend/src/routes/+page.svelte` (aggiornato)

---

## Dipendenze Installate (Riepilogo)

```json
{
  "dependencies": {
    "svelte-i18n": "^4.0.0",
    "date-fns": "^3.0.0",
    "lucide-svelte": "^0.559.0"
  },
  "devDependencies": {
    "openapi-zod-client": "^1.18.3",
    "zod": "^3.24.1",
    "@zodios/core": "^10.9.6"
  }
}
```

---

## Note Importanti

⚠️ **Gli endpoint backend auth (`/auth/login`, `/auth/logout`, `/auth/me`) NON esistevano ancora in questa fase!**

Il frontend era pronto ma **non poteva funzionare** senza il backend.
→ Phase 2 implementa il backend auth.

---

## Verifica Completamento

### Test Manuali ✅

- [x] Language selector cambia lingua UI
- [x] Lingua persiste dopo refresh (localStorage)
- [x] `./dev.sh api:schema` genera openapi.json
- [x] API client compilabile senza errori
- [x] Auth store importabile senza errori
- [x] Login page mostra errori se API non disponibile

---

## Prossimi Passi

→ **Phase 2**: Implementare backend auth (DB, Service, API, CLI, Tests)

