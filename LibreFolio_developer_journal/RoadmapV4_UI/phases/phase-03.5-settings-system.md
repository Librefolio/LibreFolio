# Phase 3.5: Settings System (Global + Personal)

**Status**: ⏳ IN PROGRESS  
**Durata Stimata**: 4-5 giorni  
**Priorità**: P0 (MVP)
**Dipendenze**: Phase 3

---

## Progresso

| Sezione | Status |
|---------|--------|
| 3.5.1-3.5.5 (Backend) | ⏳ TODO |
| 3.5.6-3.5.9 (Frontend Settings + CLI) | ⏳ TODO |
| 3.5.10 (Icone) | ⏳ TODO |
| 3.5.11 (Logo/Favicon) | ⏳ TODO |
| 3.5.12 (Fix Navigazione) | ✅ DONE |
| 3.5.13 (Sidebar) | ⏳ TODO |
| 3.5.14 (Language Selector) | ⏳ TODO |
| 3.5.15 (Dashboard Nome) | ⏳ TODO |

---

## Obiettivo

Implementare un sistema completo di settings con:

1. **Settings Personali** (per utente): lingua, valuta base, tema, preferenze UI
2. **Settings Globali** (per installazione): TTL session, limiti, configurazioni server
3. **Distinzione Admin/User**: Solo gli admin possono modificare i settings globali

---

## Analisi Impatto

### Backend

| Componente        | Modifica Richiesta                             |
|-------------------|------------------------------------------------|
| `001_initial.py`  | Aggiungere tabella `global_settings`           |
| `models.py`       | Aggiungere model `GlobalSetting`               |
| `models.py`       | Estendere `UserSettings` con nuovi campi       |
| `models.py`       | Aggiungere campo `is_admin` a `User`           |
| `schemas/`        | Nuovi schema per settings                      |
| `services/`       | Nuovo `settings_service.py`                    |
| `api/v1/`         | Endpoint `/settings/global` e `/settings/user` |
| `auth_service.py` | Modificare TTL cookie basato su setting        |

### Frontend

| Componente                 | Modifica Richiesta                     |
|----------------------------|----------------------------------------|
| `PreferencesTab.svelte`    | Collegare a API reali                  |
| `stores/settings.ts`       | Nuovo store per settings               |
| `SettingsGlobalTab.svelte` | Nuovo tab per admin (settings globali) |

### Database

Nuova tabella `global_settings`:

```sql
CREATE TABLE global_settings
(
    key                VARCHAR(100) PRIMARY KEY,
    value              TEXT        NOT NULL,
    value_type         VARCHAR(20) NOT NULL, -- 'string', 'int', 'bool', 'json'
    description        TEXT,
    updated_at         TIMESTAMP,
    updated_by_user_id INTEGER REFERENCES users (id)
);
```

Estensione `user_settings`:

```sql
ALTER TABLE user_settings
    ADD COLUMN base_currency VARCHAR(3) DEFAULT 'EUR';
ALTER TABLE user_settings
    ADD COLUMN theme VARCHAR(10) DEFAULT 'light';
-- language già presente
```

Estensione `users`:

```sql
ALTER TABLE users
    ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
```

---

## 3.5.1 Backend: Model e Migration

### Tasks

- [ ] Modificare `001_initial.py`:
    - Aggiungere campo `is_admin` a tabella `users`
    - Aggiungere campi `base_currency`, `theme` a `user_settings`
    - Creare tabella `global_settings`

- [ ] Aggiornare `models.py`:
  ```python
  class User(SQLModel, table=True):
      # ...existing fields...
      is_admin: bool = Field(default=False)
  
  class UserSettings(SQLModel, table=True):
      # ...existing fields...
      base_currency: str = Field(default="EUR", max_length=3)
      theme: str = Field(default="light", max_length=10)  # light, dark, auto
  
  class GlobalSetting(SQLModel, table=True):
      __tablename__ = "global_settings"
      key: str = Field(primary_key=True, max_length=100)
      value: str = Field(...)
      value_type: str = Field(max_length=20)  # string, int, bool, json
      description: str | None = Field(default=None)
      updated_at: datetime = Field(default_factory=datetime.utcnow)
      updated_by_user_id: int | None = Field(foreign_key="users.id")
  ```

- [ ] Rimuovere vecchi DB e ricreare: `./dev.sh db:upgrade`

---

## 3.5.2 Backend: Schema Pydantic

### Tasks

- [ ] Creare `schemas/settings.py`:
  ```python
  from pydantic import BaseModel
  from typing import Literal
  
  # User Settings
  class UserSettingsRead(BaseModel):
      language: str
      base_currency: str
      theme: Literal["light", "dark", "auto"]
  
  class UserSettingsUpdate(BaseModel):
      language: str | None = None
      base_currency: str | None = None
      theme: Literal["light", "dark", "auto"] | None = None
  
  # Global Settings
  class GlobalSettingRead(BaseModel):
      key: str
      value: str
      value_type: str
      description: str | None
  
  class GlobalSettingUpdate(BaseModel):
      value: str
  
  # Predefined Global Settings
  GLOBAL_SETTINGS_DEFAULTS = {
      "session_ttl_hours": {"value": "24", "type": "int", "desc": "Session cookie TTL in hours"},
      "max_file_upload_mb": {"value": "10", "type": "int", "desc": "Max file upload size in MB"},
      "enable_registration": {"value": "true", "type": "bool", "desc": "Allow new user registration"},
  }
  ```

---

## 3.5.3 Backend: Service Layer

### Tasks

- [ ] Creare `services/settings_service.py`:
  ```python
  async def get_user_settings(user_id: int, session: AsyncSession) -> UserSettings
  async def update_user_settings(user_id: int, updates: UserSettingsUpdate, session: AsyncSession) -> UserSettings
  
  async def get_global_setting(key: str, session: AsyncSession) -> GlobalSetting | None
  async def get_all_global_settings(session: AsyncSession) -> list[GlobalSetting]
  async def update_global_setting(key: str, value: str, user_id: int, session: AsyncSession) -> GlobalSetting
  async def initialize_global_settings(session: AsyncSession) -> None  # Popola defaults
  
  def get_session_ttl() -> int  # Legge da global_settings o default
  ```

- [ ] Modificare `auth_service.py`:
    - Usare `get_session_ttl()` invece di valore hardcoded
    - Cookie TTL dinamico basato su setting globale

---

## 3.5.4 Backend: API Endpoints

### Tasks

- [ ] Creare/Estendere `api/v1/settings.py`:

  **User Settings**:
  ```
  GET  /api/v1/settings/user          → Ritorna settings utente corrente
  PUT  /api/v1/settings/user          → Aggiorna settings utente
  ```

  **Global Settings** (solo admin):
  ```
  GET  /api/v1/settings/global        → Lista tutti (pubblico per lettura)
  GET  /api/v1/settings/global/{key}  → Singolo setting
  PUT  /api/v1/settings/global/{key}  → Aggiorna (solo admin)
  ```

- [ ] Middleware/Decorator per controllo admin:
  ```python
  async def require_admin(user: User = Depends(get_current_user)):
      if not user.is_admin:
          raise HTTPException(403, "Admin access required")
      return user
  ```

---

## 3.5.5 Backend: Tests

### Tasks

- [ ] Test unit per settings_service
- [ ] Test API per endpoints settings
- [ ] Test che non-admin non possa modificare global settings
- [ ] Test che session TTL si aggiorni correttamente

---

## 3.5.6 Frontend: Settings Store

### Tasks

- [ ] Creare `stores/settings.ts`:
  ```typescript
  interface UserSettings {
      language: string;
      base_currency: string;
      theme: 'light' | 'dark' | 'auto';
  }
  
  interface GlobalSettings {
      session_ttl_hours: number;
      max_file_upload_mb: number;
      enable_registration: boolean;
  }
  
  export const userSettings = writable<UserSettings | null>(null);
  export const globalSettings = writable<GlobalSettings | null>(null);
  
  export async function loadUserSettings(): Promise<void>
  export async function updateUserSettings(updates: Partial<UserSettings>): Promise<void>
  export async function loadGlobalSettings(): Promise<void>
  export async function updateGlobalSetting(key: string, value: string): Promise<void>
  ```

---

## 3.5.7 Frontend: PreferencesTab Collegato

### Tasks

- [ ] Modificare `PreferencesTab.svelte`:
    - Caricare settings da API al mount
    - Salvare modifiche via API
    - Mostrare loading/saving states
    - Gestire errori con toast

- [ ] Implementare cambio tema (light/dark/auto):
    - CSS variables per tema
    - LocalStorage per persistenza
    - System preference detection per "auto"

---

## 3.5.8 Frontend: Admin Tab (Global Settings)

### Tasks

- [ ] Creare `GlobalSettingsTab.svelte`:
    - Visibile solo se utente è admin
    - Lista tutti i settings globali
    - Form per modificare ciascuno
    - Validazione tipo (int, bool, string)
    - Conferma prima di salvare

- [ ] Modificare `settings/+page.svelte`:
    - Aggiungere tab "Admin" se `$currentUser?.is_admin`
    - Tab nascosto per utenti normali

---

## 3.5.9 CLI: Promuovere Admin

### Tasks

- [ ] Aggiungere comando a `user_cli.py`:
  ```bash
  ./dev.sh user:promote <username>   # Rende admin
  ./dev.sh user:demote <username>    # Rimuove admin
  ```

---

## Acceptance Criteria

### Backend

- [ ] Tabella `global_settings` creata con valori default
- [ ] Campo `is_admin` funzionante su users
- [ ] API settings accessibili e protette
- [ ] Session TTL configurabile
- [ ] Tests passano

### Frontend

- [ ] PreferencesTab salva su API
- [ ] Cambio lingua persiste su server
- [ ] Cambio tema funziona (light/dark/auto)
- [ ] Admin vede tab Global Settings
- [ ] Non-admin non vede tab Global Settings

### CLI

- [ ] `./dev.sh user:promote` funziona
- [ ] `./dev.sh user:demote` funziona

---

## Note Implementative

### Session TTL

Il TTL della sessione deve essere letto da `global_settings` al momento della creazione del cookie. Se il setting cambia, le sessioni esistenti mantengono il vecchio TTL fino a
logout/login.

### Primo Admin

Il primo utente registrato diventa automaticamente admin. CLI disponibile per gestire promozioni/rimozioni successive.

### Tema

Il tema deve essere applicato tramite:

1. Classe CSS su `<html>` o `<body>`
2. CSS variables che cambiano in base alla classe
3. Sync con preferenze sistema per "auto"

---

## Timeline Stimata

| Step                        | Tempo           |
|-----------------------------|-----------------|
| 3.5.1-3.5.2 (DB + Models)   | 0.5 giorni      |
| 3.5.3-3.5.4 (Service + API) | 0.5 giorni      |
| 3.5.5 (Tests)               | 0.5 giorni      |
| 3.5.6-3.5.8 (Frontend)      | 1 giorno        |
| 3.5.9 (CLI)                 | 0.25 giorni     |
| **Totale**                  | **~2.5 giorni** |

---

## Dipendenze Post-Phase

- Phase 4 (Brokers): Può usare `base_currency` per display
- Phase 8 (Dashboard): Usa `base_currency` per calcoli aggregati
- Tutte le fasi: Beneficiano del sistema tema

---

## 3.5.10 Assets: Icone Transazioni e Asset Types

### Sorgenti Icone

Le icone sono disponibili in:
- `mkdocs_src/docs/POC_UX/transactions/Transactions-icon/` - Icone transazioni
- `mkdocs_src/docs/POC_UX/design/asset_type_icons/` - Icone tipi asset

### Tasks

- [ ] Creare struttura cartelle nel frontend:
  ```
  frontend/static/icons/
  ├── transactions/
  │   ├── adjustment.png
  │   ├── buy.png
  │   ├── deposit.png
  │   ├── dividend.png
  │   ├── fee.png
  │   ├── fx_conversion.png
  │   ├── interest.png
  │   ├── sell.png
  │   ├── tax.png
  │   ├── transfer.png (rinominato da transfert.png)
  │   └── withdrawal.png
  └── asset-types/
      ├── bond.png
      ├── crypto.png
      ├── crowdfunding.png
      ├── etf.png
      ├── fund.png
      ├── hold.png
      ├── other.png
      └── stock.png
  ```

- [ ] Copiare e normalizzare nomi file (lowercase, - invece di _):
  ```bash
  # Esempio copia
  cp mkdocs_src/docs/POC_UX/transactions/Transactions-icon/*.png frontend/static/icons/transactions/
  cp mkdocs_src/docs/POC_UX/design/asset_type_icons/*.png frontend/static/icons/asset-types/
  # Rinominare in lowercase
  ```

- [ ] Creare helper TypeScript per mappare tipi a icone:
  ```typescript
  // frontend/src/lib/utils/icons.ts
  export function getTransactionIcon(type: string): string {
      const normalized = type.toLowerCase().replace('_', '-');
      return `/icons/transactions/${normalized}.png`;
  }
  
  export function getAssetTypeIcon(type: string): string {
      const normalized = type.toLowerCase().replace('_', '-');
      return `/icons/asset-types/${normalized}.png`;
  }
  ```

- [ ] Backend: Aggiungere endpoint per servire icone se necessario (opzionale, SvelteKit può servire direttamente da `/static`)

---

## 3.5.11 Logo e Favicon

### Sorgente

Logo: `mkdocs_src/docs/POC_UX/logo/Logo_minimalista_2.png`

### Tasks

- [ ] Copiare logo in frontend:
  ```bash
  cp mkdocs_src/docs/POC_UX/logo/Logo_minimalista_2.png frontend/static/logo.png
  ```

- [ ] Generare favicon da logo:
  - Creare `frontend/static/favicon.png` (32x32 o 16x16)
  - Oppure usare tool online per generare `.ico`

- [ ] Aggiornare `app.html` con favicon:
  ```html
  <link rel="icon" type="image/png" href="/favicon.png" />
  ```

- [ ] Sostituire SVG placeholder nel header/sidebar con logo reale:
  - Modificare `Sidebar.svelte` per usare `<img src="/logo.png">`
  - Modificare login page se presente placeholder

---

## 3.5.12 Fix Navigazione e Redirect

### Problemi Identificati

1. Redirect a `/login` causa 404 (dovrebbe essere `/`)
2. Vari punti nel codice usano path sbagliati

### Tasks

- [x] Audit di tutti i redirect nel frontend:
  ```bash
  grep -rn "goto.*login" frontend/src/
  grep -rn "redirect.*login" frontend/src/
  grep -rn '"/login"' frontend/src/
  ```

- [x] Sostituire tutti `/login` con `/` (la root page gestisce i modali auth)
  - `client.ts`: goto('/') invece di goto('/login')
  - `hooks.server.ts`: redirect a `/?redirect=...` invece di `/login?redirect=...`

- [x] Verificare `hooks.server.ts`:
  - Il redirect per utenti non autenticati deve andare a `/`
  - Query param `redirect` deve funzionare per tornare alla pagina originale
  - PUBLIC_ROUTES aggiornato per usare `/` invece di `/login`

- [x] Verificare logout flow:
  - Dopo logout, redirect a `/` (già corretto in auth store)

- [x] Creare pagina 404 personalizzata:
  - `frontend/src/routes/+error.svelte` creato
  - Stile coerente con il progetto (libre-green, libre-beige)
  - Background animato (AnimatedBackground component)
  - Messaggio chiaro e link per tornare a home/dashboard
  - Traduzioni aggiunte per EN, IT, FR, ES

---

## 3.5.13 Sidebar: Stato Attivo e Toggle

### Problemi Identificati

1. Sempre selezionato "Dashboard" indipendentemente dalla pagina
2. Sidebar non si apre/chiude cliccando sul logo
3. Non c'è opzione per mostrare solo icone vs icone+testo
4. Sidebar scompare su schermi stretti

### Tasks

- [ ] Fix stato attivo menu:
  - Usare `$page.url.pathname` per determinare item attivo
  - Applicare classe `.active` o simile all'item corrente
  ```svelte
  <script>
    import { page } from '$app/stores';
    $: currentPath = $page.url.pathname;
  </script>
  
  <a href="/dashboard" class:active={currentPath === '/dashboard'}>
  ```

- [ ] Toggle sidebar cliccando sul logo:
  - Aggiungere stato `sidebarOpen` (store o locale)
  - `on:click` sul logo per toggle
  - Animazione di apertura/chiusura

- [ ] Setting utente per modalità sidebar:
  - Aggiungere campo `sidebar_mode` a UserSettings: `'icons' | 'full'`
  - Quando `icons`: mostra solo icone (sidebar compatta)
  - Quando `full`: mostra icone + testo
  - Hover su icona mostra tooltip con nome

- [ ] Responsive sidebar:
  - Su schermi stretti (< 768px): sidebar nascosta di default
  - Hamburger menu per aprire/chiudere
  - Overlay quando aperta su mobile
  - Swipe gesture per chiudere (opzionale)

---

## 3.5.14 Language Selector Globale

### Problema

Il selettore lingua è solo nella login page, dovrebbe essere disponibile sempre.

### Tasks

- [ ] Estrarre `LanguageSelector.svelte` come componente standalone:
  ```svelte
  <!-- frontend/src/lib/components/LanguageSelector.svelte -->
  <script>
    import { currentLanguage, availableLanguages, currentLanguageFlag } from '$lib/stores/language';
    export let position: 'top-right' | 'inline' = 'top-right';
    let showMenu = false;
  </script>
  
  <!-- Menu dropdown con bandiere -->
  ```

- [ ] Usare in login page (`+page.svelte`):
  - Sostituire codice duplicato con `<LanguageSelector position="top-right" />`

- [ ] Aggiungere in layout app (`(app)/+layout.svelte`):
  - Posizionare in alto a destra, nella header
  - O nel dropdown profilo utente

---

## 3.5.15 Dashboard: Nome Profilo

### Problema

Il nome utente non è mostrato da nessuna parte nella dashboard.

### Tasks

- [ ] Modificare `dashboard/+page.svelte`:
  - Mostrare messaggio di benvenuto con nome utente
  - Es: "Welcome back, {username}!" oppure "Ciao, {username}!"
  - Usare traduzione i18n

- [ ] Store utente corrente:
  - Assicurarsi che `$currentUser` contenga username
  - Verificare che `/api/v1/auth/me` ritorni username

- [ ] Styling:
  - Card o banner in alto con saluto
  - Eventuale avatar placeholder (iniziali)

---

## Timeline Aggiornata

| Step                               | Tempo           |
|------------------------------------|-----------------|
| 3.5.1-3.5.2 (DB + Models)          | 0.5 giorni      |
| 3.5.3-3.5.4 (Service + API)        | 0.5 giorni      |
| 3.5.5 (Tests)                      | 0.5 giorni      |
| 3.5.6-3.5.8 (Frontend Settings)    | 1 giorno        |
| 3.5.9 (CLI)                        | 0.25 giorni     |
| 3.5.10 (Icone)                     | 0.25 giorni     |
| 3.5.11 (Logo/Favicon)              | 0.15 giorni     |
| 3.5.12 (Fix Navigazione)           | 0.25 giorni     |
| 3.5.13 (Sidebar)                   | 0.5 giorni      |
| 3.5.14 (Language Selector)         | 0.25 giorni     |
| 3.5.15 (Dashboard Nome)            | 0.15 giorni     |
| **Totale**                         | **~4.3 giorni** |

---

## Ordine di Esecuzione Consigliato

1. **3.5.11** - Logo e Favicon (quick win, migliora aspetto)
2. **3.5.10** - Icone (setup struttura)
3. **3.5.12** - Fix navigazione (bug critici)
4. **3.5.14** - Language selector (quick component extraction)
5. **3.5.13** - Sidebar improvements
6. **3.5.15** - Dashboard nome profilo
7. **3.5.1-3.5.5** - Backend settings system
8. **3.5.6-3.5.9** - Frontend settings + CLI
