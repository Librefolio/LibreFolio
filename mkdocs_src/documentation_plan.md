# LibreFolio Documentation Plan (Revised v4)

This report outlines the intended structure and content for the documentation, incorporating architectural changes (BRIM, Registry), administrative tools, and localization
strategies.

---

## 🌍 Localization Strategy (i18n)

To support **English, Italian, Spanish, and French**, the documentation structure for user-facing sections will be replicated.

- **Technical Documentation** (Developer/Admin): Primarily **English** (to ensure accuracy and maintainability).
- **User Documentation** (Getting Started/User Manual): **Multilingual**.
- **Implementation**: Use `mkdocs-static-i18n` or Material for MkDocs i18n features.
    - Structure: `docs/en/`, `docs/it/`, `docs/es/`, `docs/fr/`.

---

## 🎨 Visual Identity & Navigation

- **Theme**: Matches LibreFolio Frontend color scheme.
- **Assets**: Uses application **Logo** and **Favicon**.
- **Homepage Links**: Prominent link to the running application dashboard.

---

## 1. Root Directory (`index.md`)

- **Purpose**: Main landing page.
- **Key Sections**: Project Mission, Quick Links (User/Dev/Admin), **Launch Dashboard**.

---

## 2. Getting Started (Multilingual)

- **`introduction.md`**: High-level project overview, goals, and tech stack.
- **`installation.md`**: Instructions for setting up a local **development** environment.

---

## 3. User Manual (Multilingual)

- **`index.md`**: Entry point for end-users.
- **`installation.md`**: Standard deployment guide (Docker simple).
- *(Other user-facing guides pending)*

---

## 4. Admin Manual

- **`index.md`**: Overview of administrative tasks.
- **`cli_tools.md`**:
    - **`dev.sh`**: The master orchestration script (setup, run, test, clean).
    - **`user_cli.py`**: User management (create superuser, reset passwords) and system maintenance.
    - **`test_runner.py`**: How to run specific test suites manually.
- **`docker_advanced.md`**:
    - Deep dive into `docker-compose.yml`.
    - Networking, Volumes, and production considerations.
    - Difference between the "User" installation and "Dev" Docker setup.

---

## 5. Developer Manual

### `developer/index.md`

- Entry point for technical documentation.

### `developer/technologies/` (Tech Stack & Implementation)

- **`overview.md`**: Summary of libraries used (FastAPI, SQLAlchemy, Pydantic, SvelteKit, etc.).
- **`async_architecture.md`**:
    - Why Async? (Efficiency, non-blocking I/O).
    - How it's implemented in LibreFolio (AsyncSession, async providers).
- **`alembic.md`**:
    - Database migrations guide.
    - Constraints encountered (SQLite limitations) and solutions (batch mode).
    - Workflow for schema changes.
- **`configuration.md`**:
    - **Environment Variables**: Full list of `.env` variables and their effects.

### `developer/architecture/` (Core Concepts)

- **`overview.md`**: High-level diagram (Frontend <-> API <-> DB).
- **`database.md`**:
    - **ER Diagram**: Visual representation of the schema.
    - **Logic**: Relationships, constraints, and design philosophy.
- **`users_and_brokers.md`**:
    - **Auth Model**: JWT, OAuth2 flows.
    - **Roles**: Superuser vs. Normal User.
    - **Mapping**: How Users are mapped to Brokers (1:N relationship) and data segregation.
- **`settings.md`**:
    - **Global Settings**: System-wide configs (read-only for users).
    - **User Settings**: User-specific preferences (stored in DB).
- **`registry_pattern.md`**:
    - Explanation of `ProviderRegistry`.
    - `@register_provider` decorator.
    - **Guide**: "How to create a new Plugin".
- **`security.md`**:
    - **Threat Model**: Host assumed secure.
    - **Boundary**: HTTPS/Vault.
    - **Reporting**: GitHub Issues for API vulnerabilities.

### `developer/backend/brim/` (Broker Report Import Manager)

- **`architecture.md`**: Workflow (`Upload` -> `Parse` -> `Import`), File Lifecycle, Deduplication.
- **`generic_csv.md`**: Case Study of `broker_generic_csv` (Header mapping, fallback logic).
- **`providers_list.md`**: Table of Broker Plugins (Code, Formats, Test Level).

### `developer/backend/assets/` (Asset Pricing & Metadata)

- **`architecture.md`**: `AssetSourceManager`, Metadata Service, Backward-fill logic.
- **`system_providers.md`**:
    - **CSS Scraper**: Selector config.
    - **Scheduled Investment**: Synthetic value math (bonds/loans).
- **`providers_list.md`**: Table of External Providers (e.g., `yfinance`, `justetf`).

### `developer/backend/fx/` (Foreign Exchange)

- **`architecture.md`**: Multi-provider support, Priority System, Normalization.
- **`providers_list.md`**: Table of FX Plugins (ECB, FED, etc.).

### `developer/api/`

- **`index.md`**:
    - Dynamic route generation explanation.
    - Links to running docs:
        - 🚀 **Swagger UI**: `http://localhost:6040/api/v1/docs`
        - 💻 **ReDoc**: `http://localhost:6040/api/v1/redoc`

### `developer/financial-calculations/`

- **`index.md`**: Overview.
- **`day-count.md`**: Day-count conventions.
- **`interest-types.md`**: Simple vs. Compound.
- **`compounding.md`**: Frequencies.

### `developer/test-walkthrough/`

- **Structure**: One file per test category.
- **Content**: Purpose, command, output, verification.

---

## 6. Tutorials

- Placeholders for user-facing tutorials (`track-first-stock.md`, `track-p2p-loan.md`).

---

## 📅 Pianificazione Riallineamento (Post-Audit Gennaio 2026)

Questa sezione definisce le azioni correttive necessarie per allineare la documentazione allo stato attuale del codice (visto nell'audit `backend_documentation_audit.md`).

### 1. Correzioni Critiche (Backend Core)

Queste modifiche sono prioritarie perché la documentazione attuale è **errata** o **fuorviante**.

- **Autenticazione (`developer/architecture/users_and_brokers.md`)**
    -   [x] **Correggere**: Rimuovere ogni riferimento a JWT/OAuth2 Bearer Token.
    -   [x] **Scrivere**: Documentare il sistema basato su `HttpOnly Session Cookies`.
    -   [x] **Spiegare**: Il flusso di login/logout e la gestione della sessione lato server (`backend/app/services/auth_service.py`).

- **Database Schema (`developer/architecture/database.md`)**
    -   [x] **Aggiornare**: Rigenerare il diagramma Mermaid ER.
    -   [x] **Aggiungere**: Tabella `BrokerUserAccess` (cruciale per il multi-user).
    -   [x] **Aggiungere**: Tabella `FxConversionRoute` (cruciale per FX routing e catene di conversione, sostituisce `FxCurrencyPairSource`).
    -   [x] **Aggiornare**: Tabella `Asset` con i nuovi campi `identifier_*` e `classification_params`.
    -   [x] **Aggiornare**: Tabella `Transaction` con `related_transaction_id` (per Transfer/FX).

### 2. Nuove Funzionalità Backend (Mancanti)

Funzionalità implementate e funzionanti ma completamente assenti dalla documentazione.

- **Access Control (`developer/architecture/access_control.md` - NUOVO)**
    -   [x] **Creare**: Documentare il sistema RBAC per i Broker.
    -   [x] **Dettagliare**: Ruoli `OWNER`, `EDITOR`, `VIEWER`.
    -   [x] **Spiegare**: Come funziona la condivisione di un broker tra utenti.

- **FX Configuration (`developer/backend/fx/configuration.md` - NUOVO)**
    -   [x] **Creare**: Documentare la logica di routing delle coppie valutarie.
    -   [x] **Spiegare**: Come il sistema sceglie tra ECB, FED, etc. in base alla priorità.
    -   [x] **API**: Documentare gli endpoint per configurare le sorgenti (`/api/v1/fx/providers/pair-sources`).

### 3. Espansione Frontend (SvelteKit)

Il piano originale sottostimava la complessità del frontend. Ora abbiamo componenti ricchi che necessitano di docs.

- **Architettura Frontend (`developer/frontend/architecture.md`)**
    -   [x] **Aggiornare**: Struttura directory aggiornata (`lib/components/`, `routes/(app)/`).
    -   [x] **Spiegare**: Gestione dello stato con Svelte 5 Runes (`$state`, `$derived`).

- **Componenti Chiave**
    -   [x] **`developer/frontend/components/data-table.md`**: Documentare il componente `DataTable` (filtri, sort, paginazione server-side).
    -   [x] **`developer/frontend/components/auth.md`**: Documentare i modali di Login/Register e il `PasswordStrengthMeter`.
    -   [x] **`developer/frontend/components/settings.md`**: Documentare il sistema di settings a tab e la gestione "edit-lock".

### 4. Cleanup & Manutenzione

-   [x] **API Reference**: Verificare che i link a Swagger/ReDoc siano corretti e funzionanti.
-   [x] **Tutorials**: Rimuovere o marcare come "WIP" i tutorial utente se le feature UI non sono ancora complete (es. grafici dashboard).

### 5. Future Enhancements

-   [ ] **Automated Screenshots**: Implementare uno script (basato su Playwright) per generare screenshot aggiornati del frontend e includerli automaticamente nella documentazione.
-   [ ] **Tailscale Guide**: Scrivere la guida completa per l'esposizione sicura tramite Tailscale (placeholder creato).
