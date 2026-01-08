# Plan: Frontend Development - LibreFolio UI

**Data Creazione**: 8 Gennaio 2026  
**Versione**: 2.3 (Phase 1.1 Completata)  
**Target**: Implementazione completa UI per Phase 9  
**Status**: 🟢 PHASE 1.1 COMPLETATA - Pronto per Phase 1.2 (OpenAPI Schema Generation)

---

## 📊 Stato Attuale

### ✅ Backend Completato (Phase 0-5)

- **Phase 0-2**: Database, FX, Asset Providers (100%)
- **Phase 3-5**: Brokers, Transactions, BRIM Import (100%)
- **API Endpoints**: 60+ operativi
- **Test Coverage**: Tutti i test passano
- **⚠️ Auth System**: **NON IMPLEMENTATO** - Da fare dopo frontend (Phase 9)

### 🎨 Frontend - Stato Corrente (Aggiornato 8 Gen 2026)

**Stack Effettivo** (semplificato da plan originale):
- **Framework**: SvelteKit 2.48+ 
- **Styling**: Tailwind CSS 4.1+ (config via CSS `@theme`, NO file tailwind.config.ts)
- **UI Components**: Custom (Skeleton UI rimosso - non compatibile con Tailwind v4)
- **Icons**: lucide-svelte 0.559+

**✅ Completato**:
- Login page funzionante con styling corretto
- AnimatedBackground.svelte con onde animate e linee grafici a loop
- Colori brand applicati (#1a4031 verde, #f5f4ef beige, #9caf9c sage)
- Comandi dev.sh per frontend: `fe:dev`, `fe:build`, `fe:check`, `fe:preview`

**📁 Struttura package.json**:
- **Root `/package.json`**: Solo tool di progetto (Playwright E2E tests)
- **Frontend `/frontend/package.json`**: Tutte le dipendenze UI (SvelteKit, Tailwind, etc.)
- Motivazione: Compartimentazione pulita, deploy indipendente, aggiornamenti separati

**⚠️ Da Implementare**:
- Integrazione build frontend in backend (FastAPI serve static files)
- i18n (en/it/fr/es)
- Connessione API backend

### 📐 Design System Confermato

- **Palette**:
    - Dark Forest Green (#1A4D3E) - Primary
    - Mint Green (#A8D5BA) - Accent/Success
    - Cream/Beige (#FDFBF7) - Background
    - Dark Grey (#2C2C2C) - Text
- **Layout**: Sidebar navigation + main content area
- **Style**: Modern, clean, Material UI inspired
- **Responsive**: Mobile-first approach

---

## 🎯 Obiettivi Frontend

### Principi Fondamentali

1. **Zero Calcoli nel Frontend**: Tutti i calcoli avvengono nel backend
2. **API-First**: Frontend è solo presentazione dati
3. **Session-Based Auth**: Cookie HttpOnly per sicurezza
4. **Multi-Language**: Supporto en/it/fr/es tramite i18n
5. **Responsive**: Desktop + Mobile + Tablet
6. **⚠️ IMPORTANTE**: **Tutto il codice frontend DEVE stare dentro `/frontend`**
    - Nessun file frontend nella root del progetto
    - Nessun file frontend misto con backend
    - Struttura pulita: `backend/` per Python, `frontend/` per SvelteKit
    - Se esiste codice fuori posto: eliminare o spostare in `/frontend`

---

## 🔧 Decisioni Tecniche Confermate

### Stack Completo

```typescript
{
    // Core
    "framework"
:
    "SvelteKit 2.48+",
        "styling"
:
    "Tailwind CSS 4.1+",
        "ui"
:
    "Skeleton UI 4.7+",

        // Charting
        "charts"
:
    "Apache ECharts 5.5+", // via echarts-for-svelte

        // State Management
        "dataLoading"
:
    "SvelteKit load functions", // Per data fetching
        "uiState"
:
    "Svelte Stores", // Per UI logic

        // Form Validation
        "validation"
:
    "openapi-zod-client", // Auto-generato da FastAPI OpenAPI
        "schema"
:
    "Zod 3.22+",

        // Date Handling
        "dates"
:
    "date-fns 3.0+",

        // Icons
        "icons"
:
    "lucide-svelte 0.559+ + custom SVG",

        // i18n
        "internationalization"
:
    "svelte-i18n 4.0+",
        "languages"
:
    ["en", "it", "fr", "es"]
}
```

### Dependencies da Installare

**✅ Già Installate** (in `frontend/package.json`):
```json
{
  "devDependencies": {
    "@sveltejs/adapter-auto": "^7.0.0",
    "@sveltejs/kit": "^2.48.5",
    "@sveltejs/vite-plugin-svelte": "^6.2.1",
    "@tailwindcss/postcss": "^4.1.17",
    "autoprefixer": "^10.4.22",
    "postcss": "^8.5.6",
    "svelte": "^5.43.8",
    "svelte-check": "^4.3.4",
    "tailwindcss": "^4.1.17",
    "typescript": "^5.9.3",
    "vite": "^7.2.2"
  },
  "dependencies": {
    "lucide-svelte": "^0.559.0"
  }
}
```

**⏳ Da Installare** (nelle prossime fasi):
```json
{
  "dependencies": {
    "svelte-i18n": "^4.0.0",
    "date-fns": "^3.0.0",
    "echarts": "^5.5.0",
    "echarts-for-svelte": "^2.0.0"
  },
  "devDependencies": {
    "openapi-zod-client": "^1.14.0",
    "zod": "^3.22.0"
  }
}
```

---

## 📋 Piano di Sviluppo Dettagliato

### Phase 0: Fix Login Page Esistente & Build Integration (1 giorno)

**Rationale**: La login page attuale non funziona correttamente. Prima di procedere con nuove features, bisogna assicurarsi che il setup base funzioni.

#### 0.1 Diagnosi e Fix Login Page (0.5 giorni)

**Obiettivo**: Far funzionare la login page esistente con sfondo dinamico e styling corretto

**Problema Attuale**:

- `npm run dev` mostra componenti senza sfondo dinamico
- Grafica rotta / styling non applicato
- Componenti visibili ma senza theme corretto

**Tasks**:

- [x] ~~Verificare configurazione Tailwind CSS~~ → **RISOLTO**: Tailwind v4 usa `@theme` in app.css, non serve tailwind.config.ts
- [x] ~~Verificare import CSS~~ → **RISOLTO**: Usa `@import "tailwindcss"` + `@theme {}` per colori custom
- [x] ~~Verificare `AnimatedBackground.svelte`~~ → **RISOLTO**: Riscritto con onde animate, linee grafici a loop
- [x] ~~Fix `lucide-svelte` icons~~ → **OK**: Funziona correttamente
- [x] ~~Test completo~~ → **PASS**: Login page con sfondo animato funzionante

**Modifiche Implementate (8 Gen 2026)**:

1. **Rimosso Skeleton UI** - Non compatibile con Tailwind v4
2. **Riscritto `tailwind.config.ts`** → Eliminato (Tailwind v4 non lo usa)
3. **Aggiornato `app.css`**:
   ```css
   @import "tailwindcss";
   @theme {
     --color-libre-green: #1a4031;
     --color-libre-beige: #f5f4ef;
     --color-libre-sage: #9caf9c;
     --color-libre-dark: #111111;
   }
   ```
4. **Riscritto `AnimatedBackground.svelte`**:
   - 3 onde animate con clip-path e scaleY (bordi sempre attaccati)
   - 3 linee grafici che si disegnano e sfumano a loop
   - Niente frecce o griglia (rimossi su richiesta)
5. **Aggiornato `+layout.svelte`**: Rimosso `bg-libre-beige` (background viene da AnimatedBackground)
6. **Semplificato `frontend/package.json`**: Rimossi `@skeletonlabs/skeleton` e `@skeletonlabs/tw-plugin`
7. **Semplificato `vite.config.ts`**: Rimossi optimizeDeps per skeleton

**Package.json Riorganizzati**:

- **Root `/package.json`** (semplificato):
  ```json
  {
    "scripts": {
      "install:all": "npm install && cd frontend && npm install",
      "test:e2e": "playwright test"
    },
    "devDependencies": {
      "@playwright/test": "^1.48.2"
    }
  }
  ```
- **Frontend rimane completo** con tutte le dipendenze UI

**dev.sh Aggiornato**:
- Nuova funzione `install_deps()` migliorata con 4 step separati
- Nuovi comandi frontend: `fe:dev`, `fe:build`, `fe:check`, `fe:preview`
- Help aggiornato con sezione "Frontend:"

**Code Checklist**:

```typescript
// tailwind.config.ts - Verificare colori custom
export default {
    content: [
        './src/**/*.{html,js,svelte,ts}' // ← Importante!
    ],
    theme: {
        extend: {
            colors: {
                'libre-green': '#1A4D3E',
                'libre-mint': '#A8D5BA',
                'libre-beige': '#FDFBF7',
                'libre-dark': '#2C2C2C'
            }
        }
    }
}
```

**Files**:

- `tailwind.config.ts` (o `.js`)
- `src/app.css` (o `app.postcss`)
- `src/routes/+layout.svelte`
- `src/routes/(auth)/login/+page.svelte`
- `src/lib/components/AnimatedBackground.svelte`

---

#### 0.2 Integrazione Build in dev.sh (0.5 giorni) - ✅ COMPLETATO

**Obiettivo**: Automatizzare build frontend quando si avvia il backend

**✅ Completato (8 Gen 2026)**:
- [x] Comando `fe:dev` per development server frontend
- [x] Comando `fe:build` per build production
- [x] Comando `fe:check` per type checking (svelte-check)
- [x] Comando `fe:preview` per preview build
- [x] Help aggiornato con sezione "Frontend:"
- [x] Funzione `install_deps()` migliorata
- [x] **Auto-build frontend in `start_server()`** - Rileva modifiche e rebuilda
- [x] **Nuove funzioni**: `frontend_needs_rebuild()`, `auto_build_frontend()`
- [x] **Console output migliorato** con tutti gli endpoint disponibili
- [x] **FastAPI serve frontend** da `frontend/build/` come file statici
- [x] **SPA fallback** - Tutte le route non-API servono `index.html`
- [x] **Adapter-static** per generare build statica

**Modifiche Implementate**:

1. **`backend/app/main.py`**:
   - Aggiunto import `StaticFiles`
   - Funzione `frontend_available()` per check build
   - Endpoint `/` serve frontend se build esiste
   - Mount `/_app` per asset statici SvelteKit
   - Catch-all `/{path:path}` per SPA routing

2. **`dev.sh`**:
   - Nuova funzione `frontend_needs_rebuild()`:
     - Controlla se `frontend/build/index.html` esiste
     - Confronta timestamp src vs build
     - Controlla modifiche a `package.json`
   - Nuova funzione `auto_build_frontend()`:
     - Chiamata da `start_server()` e `start_server_test()`
     - Rebuilda solo se necessario
   - Console output migliorato con emoji e URL completi

3. **`frontend/svelte.config.js`**:
   - Cambiato da `adapter-auto` a `adapter-static`
   - Configurato fallback per SPA

4. **`frontend/src/routes/+layout.ts`** (nuovo):
   - `prerender = true` per build statica
   - `ssr = false` per client-side only

**Architettura Risultante**:

```
Development:
├── Backend:  ./dev.sh server    → http://localhost:8000
│   └── Auto-builds frontend se modifiche rilevate
└── Frontend: ./dev.sh fe:dev    → http://localhost:5173 (con HMR)

Production (Docker):
└── Backend:  ./dev.sh server    → http://localhost:8000
    ├── /api/v1/*  → FastAPI routes
    ├── /mkdocs/*  → User documentation
    └── /*         → Frontend SPA (da frontend/build/)
```

**Tasks**:

- [ ] Aggiungere comando `frontend:build` in `dev.sh`:
  ```bash
  # In dev.sh
  frontend:build)
    echo "🎨 Building frontend..."
    cd frontend
    npm run build
    cd ..
    echo "✅ Frontend build complete"
    ;;
  ```
- [ ] Aggiungere comando `frontend:dev` per development:
  ```bash
  frontend:dev)
    echo "🎨 Starting frontend dev server..."
    cd frontend
    npm run dev
    ;;
  ```
- [ ] **Importante**: Aggiungere auto-build nel comando `server:start`:
  ```bash
  server:start)
    # Check if frontend/build exists or is outdated
    if [ ! -d "frontend/build" ] || [ frontend/src -nt frontend/build ]; then
      echo "🎨 Frontend changes detected, rebuilding..."
      cd frontend && npm run build && cd ..
    fi
    
    echo "🚀 Starting backend server..."
    pipenv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
    ;;
  ```
- [ ] Aggiungere comando `dev:full` per frontend + backend insieme:
  ```bash
  dev:full)
    echo "🚀 Starting full stack development..."
    # Start backend in background
    ./dev.sh server:start &
    BACKEND_PID=$!
    
    # Start frontend (foreground)
    cd frontend && npm run dev
    
    # Cleanup on exit
    kill $BACKEND_PID
    ;;
  ```
- [ ] Documentare in `dev.sh --help`:
  ```
  Frontend Commands:
    frontend:build     - Build frontend for production
    frontend:dev       - Start frontend dev server (port 5173)
    dev:full          - Start backend + frontend together
  ```

**Integration con FastAPI**:

- [ ] Verificare che FastAPI serva static files da `frontend/build`:
  ```python
  # backend/app/main.py
  from fastapi.staticfiles import StaticFiles
  
  # Serve frontend static files
  app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")
  ```
- [ ] Assicurare che `/api/*` routes abbiano priorità su static files

**Files**:

- `dev.sh`
- `backend/app/main.py` (verificare static files mounting)

---

### Phase 1: Foundation & Authentication (3 giorni)

#### 1.1 Setup i18n (0.5 giorni) - ✅ COMPLETATO

**Obiettivo**: Internazionalizzazione 4 lingue + sync con API

**✅ Completato (8 Gen 2026)**:
- [x] Installato `svelte-i18n` e `date-fns`
- [x] Creata struttura traduzioni:
  ```
  src/lib/i18n/
  ├── index.ts      # Config e init
  ├── en.json       # English
  ├── it.json       # Italiano  
  ├── fr.json       # Français
  └── es.json       # Español
  ```
- [x] Creato `src/lib/stores/language.ts` per gestione lingua
- [x] Language selector con bandiere emoji nella login page
- [x] Persistenza preferenza lingua in localStorage
- [x] Auto-detect lingua browser con fallback a English
- [x] Integrazione in `+layout.svelte` con loading state

**Modifiche Implementate**:

1. **`frontend/src/lib/i18n/index.ts`**:
   - `initI18n()` per inizializzazione
   - `SUPPORTED_LOCALES`, `LOCALE_NAMES`, `LOCALE_FLAGS`
   - Re-export di `_`, `t`, `locale` da svelte-i18n
   - `saveLocalePreference()` per localStorage

2. **`frontend/src/lib/stores/language.ts`**:
   - Store `currentLanguage` con sync a svelte-i18n
   - `currentLanguageName`, `currentLanguageFlag` derived stores
   - `availableLanguages` array per UI selectors

3. **`frontend/src/routes/+layout.svelte`**:
   - Inizializzazione i18n on mount
   - Loading state durante caricamento traduzioni

4. **`frontend/src/routes/+page.svelte`** (Login):
   - Language selector in alto a destra
   - Tutti i testi tradotti con `$_('key')`
   - Loading state e error handling

**Files**:

- `src/lib/i18n/index.ts`
- `src/lib/i18n/{en,it,fr,es}.json`
- `src/lib/stores/language.ts`
- `src/routes/+layout.svelte`
- `src/routes/+page.svelte`

---

#### 1.2 OpenAPI Schema Generation (1 giorno)

**Obiettivo**: Auto-generare Zod schemas da FastAPI OpenAPI

**Tasks**:

- [ ] Installare `openapi-zod-client` e `zod`
- [ ] Creare script `scripts/generate-schemas.sh`:
  ```bash
  #!/bin/bash
  # Fetch OpenAPI spec from backend
  curl http://localhost:8000/api/v1/openapi.json > openapi.json
  
  # Generate Zod schemas + typed client
  npx openapi-zod-client ./openapi.json \
    --output ./src/lib/api/generated.ts \
    --with-alias
  
  echo "✅ Generated Zod schemas and typed API client"
  ```
- [ ] Eseguire dopo ogni modifica backend schema
- [ ] Aggiungere a `package.json`:
  ```json
  {
    "scripts": {
      "generate-schemas": "./scripts/generate-schemas.sh"
    }
  }
  ```

**Files**:

- `scripts/generate-schemas.sh`
- `src/lib/api/generated.ts` (auto-generated)

---

#### 1.3 API Client Base (1 giorno)

**Obiettivo**: Wrapper fetch con session cookie + language header

**Tasks**:

- [ ] Creare `src/lib/api/client.ts`:
    - Base URL da env: `PUBLIC_API_BASE_URL`
    - Wrapper fetch con:
        - `credentials: 'include'` (session cookie)
        - Header `Accept-Language: {currentLanguage}`
        - Error handling centralizzato (401 → redirect login)
        - Response parsing JSON
        - Timeout handling
- [ ] Creare helpers per ogni endpoint group:
    - `src/lib/api/auth.ts`
    - `src/lib/api/brokers.ts`
    - `src/lib/api/assets.ts`
    - `src/lib/api/transactions.ts`
    - `src/lib/api/fx.ts`

**Code Example**:

```typescript
// src/lib/api/client.ts
import {currentLanguage} from '$lib/stores/language';
import {get} from 'svelte/store';
import {goto} from '$app/navigation';

export async function apiCall<T>(
    endpoint: string,
    options?: RequestInit
): Promise<T> {
    const baseUrl = import.meta.env.PUBLIC_API_BASE_URL || '/api/v1';
    const lang = get(currentLanguage);

    const response = await fetch(`${baseUrl}${endpoint}`, {
        ...options,
        credentials: 'include', // Session cookie
        headers: {
            'Content-Type': 'application/json',
            'Accept-Language': lang, // Sync language with backend
            ...options?.headers
        }
    });

    if (!response.ok) {
        if (response.status === 401) {
            // Unauthorized - redirect to login
            goto('/login');
            throw new Error('Unauthorized');
        }
        throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
}
```

**Files**:

- `src/lib/api/client.ts`
- `src/lib/api/auth.ts`
- `src/lib/api/brokers.ts`
- `src/lib/api/assets.ts`
- `src/lib/api/transactions.ts`
- `src/lib/api/fx.ts`

---

#### 1.4 Authentication Store & Login Page (0.5 giorni)

**Obiettivo**: Gestione auth + login funzionante

**Tasks**:

- [ ] Creare `src/lib/stores/auth.ts`:
    - `isAuthenticated` (writable)
    - `currentUser` (writable)
    - `login(username, password)` function
    - `logout()` function
    - `checkAuth()` function (verifica session)
- [ ] Implementare `src/hooks.server.ts`:
    - Server-side session check
    - Redirect a `/login` se route protetta e non autenticato
- [ ] Refactoring login page esistente (`src/routes/(auth)/login/+page.svelte`):
    - Connettere form a `POST /api/v1/auth/login`
    - Error display
    - Loading state
    - Redirect a `/dashboard` dopo successo

**Files**:

- `src/lib/stores/auth.ts`
- `src/hooks.server.ts`
- `src/routes/(auth)/login/+page.svelte`

---

### Phase 2: Backend Authentication System (3 giorni)

**Rationale**: Il frontend auth (Phase 1.4) è pronto MA gli endpoint backend NON esistono. **Senza backend auth, il login non può funzionare!** Questa fase implementa l'intero
sistema di autenticazione lato server PRIMA di procedere con il resto del frontend.

#### 2.1 Database Schema & Models (0.5 giorni)

**Obiettivo**: Tabella users + modelli Pydantic

**Tasks**:

- [ ] Creare migration Alembic per tabella `users`:
  ```sql
  CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,  -- Future: per password reset
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- [ ] Creare `backend/app/db/models.py` - model `User`
- [ ] Eseguire migration: `./dev.sh db:migrate`

**Files**:

- `backend/alembic/versions/XXX_add_users_table.py`
- `backend/app/db/models.py` (aggiornare)

---

#### 2.2 Auth Service (Password Hashing) (0.5 giorni)

**Obiettivo**: Utility per hash/verify password con bcrypt

**Tasks**:

- [ ] Installare `passlib[bcrypt]`: `pipenv install 'passlib[bcrypt]'`
- [ ] Creare `backend/app/services/auth_service.py` (hash_password, verify_password)
- [ ] Creare `backend/app/services/session_service.py` (in-memory sessions)

**Files**:

- `backend/app/services/auth_service.py`
- `backend/app/services/session_service.py`

---

#### 2.3 Auth Endpoints (1 giorno)

**Obiettivo**: POST /auth/login, POST /auth/logout

**Tasks**:

- [ ] Creare `backend/app/api/v1/auth.py`:
    - `POST /api/v1/auth/login` - Username/password → session cookie (HttpOnly, Secure, SameSite=Lax)
    - `POST /api/v1/auth/logout` - Destroy session
- [ ] Registrare router in `backend/app/api/v1/router.py`
- [ ] Test manuale con curl

**Files**:

- `backend/app/api/v1/auth.py`
- `backend/app/api/v1/router.py` (aggiornare)

---

#### 2.4 Auth Middleware (Route Protection) (0.5 giorni)

**Obiettivo**: Proteggere `/api/*` routes (tranne `/auth/*`)

**Tasks**:

- [ ] Creare `backend/app/middleware/auth_middleware.py`
- [ ] Verificare session cookie su ogni richiesta → 401 se mancante
- [ ] Registrare middleware in `backend/app/main.py`
- [ ] Test: `/api/v1/brokers` senza cookie → 401

**Files**:

- `backend/app/middleware/auth_middleware.py`
- `backend/app/main.py` (aggiornare)

---

#### 2.5 CLI Commands (User Management) (0.5 giorni)

**Obiettivo**: Comandi terminale per creare/resettare utenti

**Tasks**:

- [ ] Creare `backend/app/cli/user_commands.py` con comandi:
    - `create_user(username, password, email, superuser)`
    - `reset_password(username, new_password)` ⭐ **Password reset pragmatico**
    - `delete_user(username)`
    - `list_users()`
- [ ] Aggiungere in `dev.sh`:
  ```bash
  ./dev.sh user:create <username> <password> [--superuser]
  ./dev.sh user:reset <username> <new_password>
  ./dev.sh user:delete <username>
  ./dev.sh user:list
  ```

**Rationale per reset via terminale**:

- ✅ **Sicurezza**: Hash bcrypt irrecuperabile (impossibile "recuperare" password)
- ✅ **Pragmatico**: Reset via CLI dentro Docker container è sufficiente per ora
- ✅ **Logica**: Se hacker accede al server → ha già DB access → CLI non peggiora security
- 🔮 **Future**: Email-based password reset (Phase 10+)

**Files**:

- `backend/app/cli/user_commands.py`
- `dev.sh` (aggiornare)

---

#### 2.6 Tests (0.5 giorni)

**Obiettivo**: Test auth flow completo

**Tasks**:

- [ ] Creare `backend/test_scripts/test_api/test_auth_api.py`:
    - Test login valido
    - Test login errato → 401
    - Test logout
    - Test endpoint protetto senza cookie → 401
    - Test endpoint protetto CON cookie → 200
- [ ] Aggiungere test category in `test_runner.py`

**Files**:

- `backend/test_scripts/test_api/test_auth_api.py`
- `test_runner.py` (aggiornare)

---

### Phase 3: Layout & Settings (3 giorni)

**Ora che auth funziona, possiamo procedere con il resto del frontend**

#### 3.1 Layout Principale con Sidebar (1.5 giorni)

**Obiettivo**: Struttura app con navigazione laterale responsive

**Tasks**:

- [ ] Creare `src/routes/(app)/+layout.svelte`:
    - Sidebar dark green (#1A4D3E) a sinistra
    - Logo LibreFolio in alto
    - Menu navigation items con icone (lucide):
        - 🏠 Dashboard
        - 🏦 Brokers
        - 📊 Assets
        - 💸 Transactions
        - 💱 FX Rates
        - ⚙️ Settings
    - User info box in basso:
        - Username
        - Language selector dropdown
        - Logout button
    - Main content area (cream background)
    - **Responsive**:
        - Desktop: sidebar sempre visibile
        - Mobile: hamburger menu, sidebar collapsible
- [ ] Creare componenti:
    - `src/lib/components/Sidebar.svelte`
    - `src/lib/components/Header.svelte` (breadcrumb + user dropdown)

**Riferimento**: `site/POC_UX/dashboard/Gemini_Generated_Image_dashboard*.png`

**Files**:

- `src/routes/(app)/+layout.svelte`
- `src/lib/components/Sidebar.svelte`
- `src/lib/components/Header.svelte`

---

#### 2.2 Settings Page (1.5 giorni)

**Obiettivo**: Configurazione utente e preferenze

**Tasks**:

- [ ] Creare `src/routes/(app)/settings/+page.svelte`
- [ ] Sezioni (tabs):
    - **Profile**:
        - Username (read-only per ora)
        - Email (future - Phase 8)
        - Change Password (future - Phase 8)
    - **Preferences**:
        - Language selector (en/it/fr/es) con flag emoji
        - Base currency dropdown (da `GET /api/v1/utilities/currencies`)
        - Timezone (future)
    - **About**:
        - App version
        - License (OSS)
        - GitHub link
- [ ] Salvare preferenze in localStorage
- [ ] Sync language con backend API calls

**Riferimento**: `site/POC_UX/settings/`

**Files**:

- `src/routes/(app)/settings/+page.svelte`
- `src/lib/components/settings/ProfileTab.svelte`
- `src/lib/components/settings/PreferencesTab.svelte`
- `src/lib/components/settings/AboutTab.svelte`

---

### Phase 4: Brokers Management (3 giorni)

**Rationale**: Brokers PRIMA di transactions (dipendenza logica)

#### 4.1 Brokers List (1 giorno)

**Obiettivo**: Lista broker con summary

**Tasks**:

- [ ] Creare `src/routes/(app)/brokers/+page.svelte`
- [ ] Creare `src/routes/(app)/brokers/+page.ts` (load function):
  ```typescript
  export async function load() {
    const brokers = await apiCall('/brokers');
    return { brokers };
  }
  ```
- [ ] Grid di card per broker:
    - Nome + Description
    - Cash balances per currency (card con flag emoji)
    - Portal URL (link esterno con icona)
    - Actions: View, Edit, Delete
- [ ] Button "Add Broker" (apre modal)
- [ ] API: `GET /api/v1/brokers`

**Riferimento**: `site/POC_UX/brokers/broker_management_*.jpg`

**Files**:

- `src/routes/(app)/brokers/+page.svelte`
- `src/routes/(app)/brokers/+page.ts`
- `src/lib/components/brokers/BrokerCard.svelte`

---

#### 3.2 Add/Edit Broker Modal (1 giorno)

**Obiettivo**: CRUD broker

**Tasks**:

- [ ] Creare `src/lib/components/brokers/AddBrokerModal.svelte`
- [ ] Form fields:
    - Name (text input, required)
    - Description (textarea)
    - Portal URL (text input, optional)
    - **Initial Balances** (multi-currency):
        - Lista dinamica di (currency dropdown + amount input)
        - Button "Add Currency"
    - Toggles:
        - Allow Overdraft (default: false)
        - Allow Shorting (default: false)
- [ ] Validazione con Zod (schema auto-generato)
- [ ] API:
    - `POST /api/v1/brokers` (create)
    - `PATCH /api/v1/brokers/{id}` (edit)
- [ ] Modal "Edit Broker" (stesso componente, pre-filled)

**Riferimento**: `site/POC_UX/brokers/add-edit_broker_modal.jpg`

**Files**:

- `src/lib/components/brokers/AddBrokerModal.svelte`
- `src/lib/components/brokers/BrokerForm.svelte`

---

#### 3.3 Broker Detail Page (1 giorno)

**Obiettivo**: Vista dettagliata broker + cash management

**Tasks**:

- [ ] Creare `src/routes/(app)/brokers/[id]/+page.svelte`
- [ ] Load data: `GET /api/v1/brokers/{id}/summary`
- [ ] Sezioni:
    - **Header**: Nome, description, portal link, Edit button
    - **Cash Balances**:
        - Card per ogni currency con flag emoji
        - Amount + currency code
        - Buttons "Deposit" / "Withdraw" (aprono modal transaction)
    - **Recent Transactions**:
        - Lista ultime 10 transazioni di questo broker
        - Link "View All" → `/transactions?broker_id={id}`

**Riferimento**: `site/POC_UX/cash/` per cash cards

**Files**:

- `src/routes/(app)/brokers/[id]/+page.svelte`
- `src/routes/(app)/brokers/[id]/+page.ts`
- `src/lib/components/brokers/CashBalanceCard.svelte`
- `src/lib/components/brokers/CashTransactionModal.svelte`

---

### Phase 5: FX Management (3 giorni)

#### 4.1 FX Currencies List (1 giorno)

**Obiettivo**: Visualizzare valute supportate per provider

**Tasks**:

- [ ] Creare `src/routes/(app)/fx/+page.svelte`
- [ ] Sezione "Supported Currencies":
    - Tabs per provider (ECB, FED, BOE, SNB)
    - Grid di card per valuta:
        - Flag emoji (da `/api/v1/utilities/currencies?language={lang}`)
        - Currency code (EUR, USD, etc.)
        - Nome localizzato
    - API: `GET /api/v1/fx/currencies?provider={provider}`

**Files**:

- `src/routes/(app)/fx/+page.svelte`
- `src/lib/components/fx/CurrencyGrid.svelte`
- `src/lib/components/fx/CurrencyCard.svelte`

---

#### 4.2 Currency Pair Sources CRUD (1 giorno)

**Obiettivo**: Gestire coppie valutarie configurate

**Tasks**:

- [ ] Sezione "Currency Pair Sources" in `/fx`
- [ ] DataGrid con colonne:
    - Base Currency (con flag)
    - Quote Currency (con flag)
    - Provider
    - Priority (0-10)
    - Actions (Edit, Delete)
- [ ] Modal "Add Pair Source":
    - Base currency dropdown (con search + flag)
    - Quote currency dropdown (con search + flag)
    - Provider dropdown (ECB, FED, BOE, SNB, FALLBACK)
    - Priority slider (0-10)
    - Validazione: base != quote
- [ ] Modal "Edit Pair Source"
- [ ] Dialog conferma Delete
- [ ] API:
    - `GET /api/v1/fx/providers/pair-sources`
    - `POST /api/v1/fx/providers/pair-sources`
    - `DELETE /api/v1/fx/providers/pair-sources`

**Riferimento**: `site/POC_UX/fx/fx_pair_*.jpg`

**Files**:

- `src/lib/components/fx/PairSourceTable.svelte`
- `src/lib/components/fx/AddPairModal.svelte`
- `src/lib/components/fx/EditPairModal.svelte`

---

#### 4.3 FX Sync Tool + Manual Entry (1 giorno)

**Obiettivo**: Tool sincronizzazione tassi + inserimento manuale

**Tasks**:

- [ ] Sezione "Sync FX Rates" in `/fx`
- [ ] Form:
    - Date range picker (start, end)
    - Multi-select currencies (con flag emoji)
    - Dropdown provider (optional - usa pair sources se vuoto)
    - Button "Sync Now"
- [ ] Progress bar durante sync
- [ ] Display risultati: "X rates fetched, Y changed"
- [ ] API: `GET /api/v1/fx/currencies/sync?start_date=&end_date=&currencies=&provider=`
- [ ] Modal "Add Manual Rate":
    - Date picker
    - Base currency dropdown
    - Quote currency dropdown
    - Rate input (decimal, min=0)
    - API: `POST /api/v1/fx/currencies/rate`

**Files**:

- `src/lib/components/fx/SyncTool.svelte`
- `src/lib/components/fx/ManualRateModal.svelte`

---

### Phase 6: Assets Management (4 giorni)

#### 5.1 Assets List (Query & Filter) (1 giorno)

**Obiettivo**: Tabella asset con ricerca e filtri

**Tasks**:

- [ ] Creare `src/routes/(app)/assets/+page.svelte`
- [ ] Filtri in alto:
    - Search bar (cerca per nome/ticker/ISIN)
    - Dropdown "Asset Type" (STOCK, ETF, BOND, etc.)
    - Dropdown "Currency"
    - Toggle "Active Only" (default: true)
    - Button "Reset Filters"
- [ ] DataGrid con colonne:
    - Icon (tipo asset - custom SVG)
    - Display Name
    - Type (badge con colore)
    - Currency (con flag)
    - Active (badge verde/grigio)
    - Provider Assigned (badge se ha provider)
    - Actions (View, Edit, Delete)
- [ ] Ordinamento per colonna
- [ ] API: `GET /api/v1/assets/query?search=&asset_type=&currency=&active=`

**Riferimento**: Adattare da `site/POC_UX/portfolio/`

**Files**:

- `src/routes/(app)/assets/+page.svelte`
- `src/lib/components/assets/AssetTable.svelte`
- `src/lib/components/assets/AssetFilters.svelte`

---

#### 5.2 Add/Edit Asset Modal (Smart Search) (2 giorni)

**Obiettivo**: CRUD asset con ricerca multi-provider

**Tasks**:

- [ ] Modal "Add Asset" con **Smart Search**:
    - **Search Field**:
        - Autocomplete input con debounce (300ms)
        - Multi-select dropdown "Search Providers" sopra:
            - Checkboxes: yfinance, justetf, mockprov, etc.
            - API: `GET /api/v1/assets/provider` per lista provider
        - Durante typing: `GET /api/v1/assets/provider/search?query={q}&providers={p1,p2}`
        - Dropdown risultati con:
            - Icon tipo asset
            - Display name
            - Ticker/ISIN
            - Currency
            - Source provider
    - **Form Fields** (auto-popolati dopo selezione):
        - Display Name (editabile)
        - Asset Type dropdown (STOCK, ETF, BOND, etc.)
        - Currency dropdown (con flag)
        - Icon URL (optional)
        - **Identifier Fields** (collapsible section):
            - ISIN (text input)
            - Ticker (text input)
            - CUSIP, SEDOL, FIGI, UUID, Other (text inputs)
    - API: `POST /api/v1/assets`
- [ ] Modal "Edit Asset":
    - Stessi campi ma pre-compilati
    - Identifier fields read-only se già impostati
    - API: `PATCH /api/v1/assets`

**Riferimento**: `artwork/Prompt_gemini.md` sezione "Add Asset"

**Files**:

- `src/lib/components/assets/AddAssetModal.svelte`
- `src/lib/components/assets/EditAssetModal.svelte`
- `src/lib/components/assets/AssetSearchAutocomplete.svelte`

---

#### 5.3 Asset Detail Page (1 giorno)

**Obiettivo**: Vista dettagliata singolo asset

**Tasks**:

- [ ] Creare `src/routes/(app)/assets/[id]/+page.svelte`
- [ ] Load data:
    - Asset: `GET /api/v1/assets?ids={id}`
    - Provider: `GET /api/v1/assets/provider/assignments?asset_ids={id}`
    - Prices: `GET /api/v1/assets/prices/{id}?start={-1year}&end={today}`
- [ ] Sezioni:
    - **Header**:
        - Icon + Display Name + Type badge
        - Currency (con flag)
        - Active status
        - Edit button
    - **Provider Assignment**:
        - Badge "Provider: yfinance" o "No Provider"
        - Button "Assign Provider" / "Change Provider"
        - Modal con form:
            - Provider dropdown
            - Identifier input
            - Identifier type dropdown (TICKER, ISIN, etc.)
            - Provider params (JSON textarea - advanced)
        - API: `POST /api/v1/assets/provider`
    - **Price History Chart**:
        - ECharts line chart (close prices)
        - Range selector: 1M, 3M, 6M, 1Y, ALL
    - **Metadata**:
        - Classification params (sector, geographic area)
        - Identifiers (ISIN, Ticker, etc.)
    - **Transactions** (future - Phase 6):
        - Lista transazioni per questo asset

**Files**:

- `src/routes/(app)/assets/[id]/+page.svelte`
- `src/lib/components/assets/AssetDetailHeader.svelte`
- `src/lib/components/assets/ProviderAssignmentSection.svelte`
- `src/lib/components/assets/PriceChart.svelte` (ECharts)

---

### Phase 7: Transactions Management (5 giorni)

#### 6.1 Transactions List (1.5 giorni)

**Obiettivo**: Log cronologico transazioni con filtri

**Tasks**:

- [ ] Creare `src/routes/(app)/transactions/+page.svelte`
- [ ] Filtri in alto:
    - Date range picker (start, end)
    - Dropdown "Transaction Type" (usa `GET /api/v1/transactions/types` per options)
    - Dropdown "Broker" (lista da `GET /api/v1/brokers`)
    - Asset search autocomplete
    - Button "Reset Filters"
- [ ] DataGrid con colonne:
    - Date (sortable)
    - Type (icon + label tradotto)
    - Asset (con icon tipo)
    - Quantity (se applicabile)
    - Cash (amount + currency con flag)
    - Broker
    - Actions (Edit, Delete)
- [ ] Ordinamento default: date DESC (più recenti prima)
- [ ] Paginazione se > 50 risultati
- [ ] API: `GET /api/v1/transactions?start_date=&end_date=&type=&broker_id=&asset_id=`

**Riferimento**: `artwork/Prompt_gemini.md` sezione "Transactions"

**Files**:

- `src/routes/(app)/transactions/+page.svelte`
- `src/lib/components/transactions/TransactionTable.svelte`
- `src/lib/components/transactions/TransactionFilters.svelte`

---

#### 6.2 Add/Edit Transaction Modal (1.5 giorni)

**Obiettivo**: Form transazione manuale con validazione dinamica

**Tasks**:

- [ ] Modal "Add Transaction":
    - **Type Selector** (dropdown):
        - BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL, etc.
        - Load types da `GET /api/v1/transactions/types` per labels + validation rules
    - **Broker Selector** (dropdown)
    - **Asset Field** (autocomplete):
        - Visible solo se type richiede asset (BUY, SELL, DIVIDEND, etc.)
        - Hidden per DEPOSIT, WITHDRAWAL
    - **Date Picker**
    - **Quantity** (number input):
        - Visible solo se type richiede quantity (BUY, SELL, etc.)
    - **Cash** (amount + currency):
        - Amount input
        - Currency dropdown (default: broker base currency)
        - Visible sempre tranne ADJUSTMENT
    - **Fee/Tax** (optional, collapsible):
        - Fee amount + currency
        - Tax amount + currency
    - **Description** (textarea, optional)
    - **Toggle "Deduct from Cash"** (default: true per BUY)
- [ ] Validazione dinamica in base a type:
    - BUY: asset required, quantity required, cash required
    - SELL: asset required, quantity required, cash required
    - DIVIDEND: asset required, cash required, quantity = 0
    - DEPOSIT/WITHDRAWAL: no asset, no quantity, cash required
    - Validazione con Zod schemas auto-generated
- [ ] API: `POST /api/v1/transactions`
- [ ] Modal "Edit Transaction":
    - Stesso form pre-compilato
    - API: `PATCH /api/v1/transactions`

**Riferimento**: `artwork/Prompt_gemini.md` sezione "Add Transaction"

**Files**:

- `src/lib/components/transactions/AddTransactionModal.svelte`
- `src/lib/components/transactions/TransactionForm.svelte`

---

#### 6.3 Broker Report Import Flow (2 giorni)

**Obiettivo**: Upload → Parse → Review → Import

**Tasks**:

- [ ] Creare `src/routes/(app)/transactions/import/+page.svelte`
- [ ] **Step 1 - Upload**:
    - Drag & drop area (o file picker)
    - Broker selector dropdown (required)
    - Button "Upload"
    - API: `POST /api/v1/brokers/import/upload` (multipart/form-data)
    - Response: `{file_id, filename, compatible_plugins[]}`
- [ ] **Step 2 - Parse**:
    - Auto-select plugin se 1 solo compatibile
    - Altrimenti dropdown "Select Plugin"
    - Button "Parse File"
    - API: `POST /api/v1/brokers/import/files/{file_id}/parse`
    - Response:
      ```json
      {
        "transactions": [...],  // TXCreateItem[]
        "asset_mappings": {...}, // fake_id → BRIMAssetMapping
        "duplicates_report": {...}
      }
      ```
- [ ] **Step 3 - Review**:
    - **Transactions Preview Table**:
        - Checkbox per ogni transazione (user può deselezionare)
        - Colonne: Type, Date, Asset, Quantity, Cash, Description
        - Warning icon se asset non riconosciuto
    - **Asset Mapping Section**:
        - Per ogni asset con candidates vuoto (non trovato):
            - Mostra extracted info (symbol, ISIN, name)
            - Button "Search Asset" → apre asset search autocomplete
            - Button "Create New" → apre add asset modal
        - Per asset con 1+ candidates:
            - Dropdown con candidati
            - User seleziona il match corretto
    - **Duplicate Warnings**:
        - Lista "Possible Duplicates" (collapsible)
        - Lista "Likely Duplicates" (collapsible)
        - Per ogni duplicato: mostra existing transaction + new transaction
        - Checkbox "Import Anyway"
- [ ] **Step 4 - Import**:
    - Button "Import Selected Transactions"
    - Disabilitato se asset mapping incompleto
    - API: `POST /api/v1/transactions` (bulk)
    - Progress bar durante import
    - Success message: "X transactions imported"
    - Error handling: mostra quale transazione ha fallito

**Riferimento**: `site/POC_UX/brokers/` + `site/POC_UX/transactions/`

**Files**:

- `src/routes/(app)/transactions/import/+page.svelte`
- `src/lib/components/import/UploadStep.svelte`
- `src/lib/components/import/ParseStep.svelte`
- `src/lib/components/import/ReviewStep.svelte`
- `src/lib/components/import/ImportStep.svelte`

---

### Phase 8: Dashboard (3 giorni)

**Rationale**: Dashboard ALLA FINE perché aggrega dati da tutti i moduli

#### 7.1 Dashboard Overview (3 giorni)

**Obiettivo**: Pagina principale con KPI + charts

**Tasks**:

- [ ] Creare `src/routes/(app)/dashboard/+page.svelte`
- [ ] **KPI Cards** (top row):
    - **Total Net Worth**:
        - Amount in base currency
        - Variazione % giornaliera (verde/rosso)
        - Small trend sparkline
    - **Weighted ROI**:
        - Percentage
        - Time period selector (1M, 3M, 6M, 1Y, ALL)
    - **Available Cash**:
        - Total cash across all brokers
        - Per-currency breakdown (collapsible)
- [ ] **Charts** (Apache ECharts):
    - **Dual Line Chart "Portfolio Growth"**:
        - Line 1: Invested (cumulative BUY outflows)
        - Line 2: Market Value (current valuation)
        - X-axis: Date
        - Y-axis: Amount in base currency
        - Range selector: 1M, 3M, 6M, 1Y, ALL
        - Tooltip con dettagli
    - **Donut Chart "Asset Allocation"**:
        - By Asset Type (STOCK, ETF, BOND, etc.)
        - Percentages + amounts
        - Click slice → filter assets list
- [ ] **Recent Transactions**:
    - Lista ultime 5-10 transazioni
    - Link "View All" → `/transactions`
- [ ] **Quick Actions** (floating buttons o cards):
    - "Add Transaction"
    - "Upload Broker Report"
    - "Add Asset"
- [ ] **API** (future - Phase 7 backend):
    - `GET /portfolio/overview` ← NON ANCORA IMPLEMENTATO
    - Per ora: **mock data** o aggregare da endpoint esistenti:
        - Cash: `GET /api/v1/brokers` → somma cash balances
        - Transactions: `GET /api/v1/transactions?limit=10`
        - Assets: `GET /api/v1/assets/query`

**Code Example - ECharts**:

```typescript
// src/lib/components/dashboard/PortfolioChart.svelte
import * as echarts from 'echarts';
import {onMount} from 'svelte';

let chartContainer: HTMLDivElement;
let chartInstance: echarts.ECharts;

onMount(() => {
    chartInstance = echarts.init(chartContainer);

    chartInstance.setOption({
        title: {text: 'Portfolio Growth'},
        tooltip: {trigger: 'axis'},
        legend: {data: ['Invested', 'Market Value']},
        xAxis: {type: 'category', data: dates},
        yAxis: {type: 'value', name: 'Amount (€)'},
        series: [
            {
                name: 'Invested',
                type: 'line',
                data: investedSeries,
                itemStyle: {color: '#1A4D3E'}
            },
            {
                name: 'Market Value',
                type: 'line',
                data: marketSeries,
                itemStyle: {color: '#A8D5BA'}
            }
        ]
    });

    return () => chartInstance.dispose();
});
```

**Riferimento**: `site/POC_UX/dashboard/Gemini_Generated_Image_dashboard*.png`

**Files**:

- `src/routes/(app)/dashboard/+page.svelte`
- `src/lib/components/dashboard/KPICard.svelte`
- `src/lib/components/dashboard/PortfolioChart.svelte` (ECharts)
- `src/lib/components/dashboard/AllocationChart.svelte` (ECharts donut)
- `src/lib/components/dashboard/RecentTransactions.svelte`

---

### Phase 9: Polish & Responsive (2 giorni)

**Importante**: Questo NON è fatto alla fine come blocco unico, ma **iterativamente durante tutte le fasi**.

#### 8.1 Componenti UI Riutilizzabili (continuo)

**Obiettivo**: Libreria componenti interni consistenti

**Tasks** (da fare incrementalmente):

- [ ] `Button.svelte` (variants: primary, secondary, danger, ghost)
- [ ] `Modal.svelte` (wrapper con backdrop, ESC close, click outside)
- [ ] `Card.svelte`
- [ ] `Badge.svelte` (variants: success, warning, danger, info, neutral)
- [ ] `DataTable.svelte` (sort, filter, pagination generico)
- [ ] `DatePicker.svelte`
- [ ] `Dropdown.svelte` / `Select.svelte`
- [ ] `SearchBox.svelte` (con debounce)
- [ ] `LoadingSpinner.svelte`
- [ ] `Toast.svelte` / `Notification.svelte` (feedback utente)

**Files**:

- `src/lib/components/ui/*.svelte`

---

#### 8.2 Responsive Mobile (continuo)

**Obiettivo**: Adattamento mobile per ogni pagina

**Checklist per ogni page**:

- [ ] Sidebar collapsible con hamburger menu (mobile)
- [ ] Bottom navigation bar (mobile) per azioni rapide
- [ ] Touch-friendly buttons (min 44x44px)
- [ ] Tabelle con scroll orizzontale o card view (mobile)
- [ ] Modal full-screen su mobile
- [ ] Form inputs stacked verticalmente (mobile)

**Riferimento**: `site/POC_UX/mobile/`

---

#### 8.3 Accessibility & UX Polish (continuo)

**Obiettivo**: A11y e refinement

**Checklist per ogni page**:

- [ ] Keyboard navigation (Tab, Enter, ESC)
- [ ] Focus visible (outline chiaro)
- [ ] ARIA labels su elementi interattivi
- [ ] Loading states su tutte le API calls (spinner)
- [ ] Error handling visibile (toast notifications con auto-dismiss)
- [ ] Success feedback (toast notifications)
- [ ] Conferma azioni distruttive (Delete → dialog "Are you sure?")
- [ ] Empty states (quando lista vuota, mostra messaggio + CTA)

---

## 🏗️ Struttura File Finale

```
frontend/
├── scripts/
│   └── generate-schemas.sh           # OpenAPI → Zod
├── src/
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts             # Base API wrapper
│   │   │   ├── generated.ts          # Auto-generated Zod schemas
│   │   │   ├── auth.ts
│   │   │   ├── brokers.ts
│   │   │   ├── assets.ts
│   │   │   ├── transactions.ts
│   │   │   └── fx.ts
│   │   ├── components/
│   │   │   ├── ui/                   # Reusable (Button, Modal, etc.)
│   │   │   ├── brokers/
│   │   │   ├── assets/
│   │   │   ├── transactions/
│   │   │   ├── fx/
│   │   │   ├── dashboard/
│   │   │   └── import/
│   │   ├── stores/
│   │   │   ├── auth.ts               # isAuthenticated, currentUser
│   │   │   └── language.ts           # currentLanguage (en/it/fr/es)
│   │   ├── i18n/
│   │   │   ├── index.ts
│   │   │   ├── en.json
│   │   │   ├── it.json
│   │   │   ├── fr.json
│   │   │   └── es.json
│   │   └── utils/
│   │       ├── formatters.ts         # Currency, Date, Number formatters
│   │       └── validators.ts
│   └── routes/
│       ├── (auth)/                   # Layout senza sidebar
│       │   └── login/
│       │       └── +page.svelte
│       └── (app)/                    # Layout con sidebar
│           ├── +layout.svelte        # Sidebar + header
│           ├── dashboard/
│           │   └── +page.svelte
│           ├── settings/
│           │   └── +page.svelte
│           ├── brokers/
│           │   ├── +page.svelte
│           │   └── [id]/+page.svelte
│           ├── fx/
│           │   └── +page.svelte
│           ├── assets/
│           │   ├── +page.svelte
│           │   └── [id]/+page.svelte
│           └── transactions/
│               ├── +page.svelte
│               └── import/+page.svelte
```

---

## 📅 Timeline Dettagliata (Aggiornata)

| Phase   | Descrizione                         | Giorni  | Cumulativo | Priorità |
|---------|-------------------------------------|---------|------------|----------|
| **0.1** | **Fix Login Page Esistente**        | **0.5** | **0.5**    | **P0**   |
| **0.2** | **Build Integration in dev.sh**     | **0.5** | **1**      | **P0**   |
| 1.1     | i18n Setup + Language Store         | 0.5     | 1.5        | P0       |
| 1.2     | OpenAPI → Zod Schema Generation     | 1       | 2.5        | P0       |
| 1.3     | API Client Base                     | 1       | 3.5        | P0       |
| 1.4     | Auth Store + Login Page Integration | 0.5     | 4          | P0       |
| **2.1** | **Backend Auth: DB Schema**         | **0.5** | **4.5**    | **P0** ⭐ |
| **2.2** | **Backend Auth: Service Layer**     | **0.5** | **5**      | **P0** ⭐ |
| **2.3** | **Backend Auth: API Endpoints**     | **1**   | **6**      | **P0** ⭐ |
| **2.4** | **Backend Auth: Middleware**        | **0.5** | **6.5**    | **P0** ⭐ |
| **2.5** | **Backend Auth: CLI Commands**      | **0.5** | **7**      | **P0** ⭐ |
| **2.6** | **Backend Auth: Tests**             | **0.5** | **7.5**    | **P0** ⭐ |
| 3.1     | Layout + Sidebar                    | 1.5     | 9          | P0       |
| 3.2     | Settings Page                       | 1.5     | 10.5       | P0       |
| 4.1     | Brokers List                        | 1       | 11.5       | P0       |
| 4.2     | Add/Edit Broker Modal               | 1       | 12.5       | P0       |
| 4.3     | Broker Detail Page                  | 1       | 13.5       | P1       |
| 5.1     | FX Currencies List                  | 1       | 14.5       | P1       |
| 5.2     | FX Pair Sources CRUD                | 1       | 15.5       | P1       |
| 5.3     | FX Sync + Manual Entry              | 1       | 16.5       | P1       |
| 6.1     | Assets List + Filters               | 1       | 17.5       | P0       |
| 6.2     | Add/Edit Asset (Smart Search)       | 2       | 19.5       | P0       |
| 6.3     | Asset Detail + Chart                | 1       | 20.5       | P2       |
| 7.1     | Transactions List                   | 1.5     | 22         | P0       |
| 7.2     | Add/Edit Transaction Modal          | 1.5     | 23.5       | P0       |
| 7.3     | Import Flow (Upload → Review)       | 2       | 25.5       | P1       |
| 8.1     | Dashboard (KPI + ECharts)           | 3       | 28.5       | P1       |
| 9.1-3   | Polish (iterativo)                  | 2       | 30.5       | P1       |

**Total: ~30.5 giorni (6+ settimane)**

**Note Importanti**:

- ⭐ **Phase 2 (Backend Auth) SUBITO DOPO LOGIN FRONTEND** - Senza backend auth, il login non può funzionare!
- **Phase 0 è FONDAMENTALE**: Prima di procedere, il setup base DEVE funzionare
- Phase 0.2 (build integration) garantisce frontend sempre aggiornato
- **Ordine critico**: 0 → 1 (frontend auth) → **2 (backend auth)** → 3+ (resto frontend)
- Priorità P0 = MVP essenziale, P1 = Importante, P2 = Nice-to-have

---

## 🎯 MVP Scope (Prime 2-3 settimane)

Per un **MVP funzionante rapidamente**, focus su **P0 only**:

### Must-Have (P0):

1. ✅ Login + Auth (Phase 1)
2. ✅ Layout + Settings (Phase 2)
3. ✅ Brokers List + Add/Edit (Phase 3.1-3.2)
4. ✅ Assets List + Add/Edit (Phase 5.1-5.2)
5. ✅ Transactions List + Add/Edit (Phase 6.1-6.2)

### Should-Have (P1 - Post-MVP):

6. Broker Detail avanzato
7. FX Management completo
8. Import Flow
9. Dashboard con grafici

### Could-Have (P2 - Future):

10. Asset Detail con chart
11. Mobile optimization completa

---

## ✅ Acceptance Criteria

### Per ogni pagina implementata:

- [ ] Responsive (desktop + mobile)
- [ ] Traduzioni en/it/fr/es complete
- [ ] Loading states visibili
- [ ] Error handling con toast
- [ ] Success feedback con toast
- [ ] Accessibility (keyboard navigation, ARIA)
- [ ] Coerente con design system (palette verde/crema)

### Per l'intero frontend:

- [ ] `npm run build` genera static files senza errori
- [ ] Static files serviti da FastAPI su `/`
- [ ] Session cookie funziona (login persistente tra reload)
- [ ] Language setting sincronizzato con `Accept-Language` header in API calls
- [ ] Tutti i 60+ endpoint backend integrati
- [ ] ECharts rendering corretto (no SSR issues)
- [ ] Logout funziona (clear cookie + redirect)
- [ ] Protezione route (redirect `/login` se non autenticato)
- [ ] No errori console in production build

---

## 🚀 Next Steps Immediati

### Step 0: Fix Login Page (PRIORITÀ ASSOLUTA)

1. **Verificare stato attuale**:
   ```bash
   cd frontend
   npm install  # Assicurarsi che tutte le deps siano installate
   npm run dev  # Testare login page
   ```

2. **Diagnosi problemi**:
    - [ ] Controllare console browser per errori
    - [ ] Verificare Network tab per CSS/JS non caricati
    - [ ] Ispezionare elementi per vedere se classi Tailwind applicate

3. **Fix Tailwind + AnimatedBackground**:
    - [ ] Verificare `tailwind.config.ts` (colori custom + content paths)
    - [ ] Verificare `src/app.css` (import Tailwind directives)
    - [ ] Verificare `AnimatedBackground.svelte` (import ed esecuzione)
    - [ ] Test: login page deve mostrare sfondo animato + styling corretto

4. **Integrare build in dev.sh**:
    - [ ] Aggiungere comandi `frontend:build`, `frontend:dev`, `dev:full`
    - [ ] Modificare `server:start` per auto-build se frontend modificato
    - [ ] Test: `./dev.sh server:start` deve servire frontend aggiornato

---

### Step 1: Dependencies & Setup (dopo Phase 0)

5. 📦 **Installare dependencies**:
   ```bash
   cd frontend
   npm install svelte-i18n date-fns echarts echarts-for-svelte
   npm install -D openapi-zod-client zod
   ```

6. 🛠️ **Creare script OpenAPI**:
   ```bash
   mkdir -p scripts
   cat > scripts/generate-schemas.sh << 'SCRIPT'
   #!/bin/bash
   curl http://localhost:8000/api/v1/openapi.json > openapi.json
   npx openapi-zod-client ./openapi.json \
     --output ./src/lib/api/generated.ts \
     --with-alias
   echo "✅ Generated schemas"
   SCRIPT
   chmod +x scripts/generate-schemas.sh
   ```

7. 🎨 **Iniziare Phase 1.1**: i18n setup (solo DOPO che Phase 0 è completata)

---

### Ordine di Priorità

1. ✅ **Phase 0.1**: Fix login page esistente (MUST DO FIRST)
2. ✅ **Phase 0.2**: Build integration in dev.sh
3. ✅ **Phase 1+**: Procedere con piano normale

---

## 📚 Riferimenti

- **Design Mockups**: `/site/POC_UX/`
- **Design Guide**: `/artwork/Prompt_gemini.md`
- **Architecture**: `/artwork/Struttura_sicurezza_programma.md`
- **Backend Roadmap**: `/LibreFolio_developer_journal/RoadmapV3/00_plan-roadmapToPublicRelease.prompt.md`
- **API Endpoints**: Output di `./dev.sh info:api` (60 endpoints disponibili)

---

**Status**: 🟢 PRONTO PER IMPLEMENTAZIONE
