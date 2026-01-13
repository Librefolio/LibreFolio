# LibreFolio Documentation Plan (Revised v4)

This report outlines the intended structure and content for the documentation, incorporating architectural changes (BRIM, Registry), administrative tools, and localization strategies.

---

## 🌍 Localization Strategy (i18n)

To support **English, Italian, Spanish, and French**, the documentation structure for user-facing sections will be replicated.
-   **Technical Documentation** (Developer/Admin): Primarily **English** (to ensure accuracy and maintainability).
-   **User Documentation** (Getting Started/User Manual): **Multilingual**.
-   **Implementation**: Use `mkdocs-static-i18n` or Material for MkDocs i18n features.
    -   Structure: `docs/en/`, `docs/it/`, `docs/es/`, `docs/fr/`.

---

## 🎨 Visual Identity & Navigation

-   **Theme**: Matches LibreFolio Frontend color scheme.
-   **Assets**: Uses application **Logo** and **Favicon**.
-   **Homepage Links**: Prominent link to the running application dashboard.

---

## 1. Root Directory (`index.md`)

-   **Purpose**: Main landing page.
-   **Key Sections**: Project Mission, Quick Links (User/Dev/Admin), **Launch Dashboard**.

---

## 2. Getting Started (Multilingual)

-   **`introduction.md`**: High-level project overview, goals, and tech stack.
-   **`installation.md`**: Instructions for setting up a local **development** environment.

---

## 3. User Manual (Multilingual)

-   **`index.md`**: Entry point for end-users.
-   **`installation.md`**: Standard deployment guide (Docker simple).
-   *(Other user-facing guides pending)*

---

## 4. Admin Manual

-   **`index.md`**: Overview of administrative tasks.
-   **`cli_tools.md`**:
    -   **`dev.sh`**: The master orchestration script (setup, run, test, clean).
    -   **`user_cli.py`**: User management (create superuser, reset passwords) and system maintenance.
    -   **`test_runner.py`**: How to run specific test suites manually.
-   **`docker_advanced.md`**:
    -   Deep dive into `docker-compose.yml`.
    -   Networking, Volumes, and production considerations.
    -   Difference between the "User" installation and "Dev" Docker setup.

---

## 5. Developer Manual

### `developer/index.md`
-   Entry point for technical documentation.

### `developer/technologies/` (Tech Stack & Implementation)
-   **`overview.md`**: Summary of libraries used (FastAPI, SQLAlchemy, Pydantic, SvelteKit, etc.).
-   **`async_architecture.md`**:
    -   Why Async? (Efficiency, non-blocking I/O).
    -   How it's implemented in LibreFolio (AsyncSession, async providers).
-   **`alembic.md`**:
    -   Database migrations guide.
    -   Constraints encountered (SQLite limitations) and solutions (batch mode).
    -   Workflow for schema changes.
-   **`configuration.md`**:
    -   **Environment Variables**: Full list of `.env` variables and their effects.

### `developer/architecture/` (Core Concepts)
-   **`overview.md`**: High-level diagram (Frontend <-> API <-> DB).
-   **`database.md`**:
    -   **ER Diagram**: Visual representation of the schema.
    -   **Logic**: Relationships, constraints, and design philosophy.
-   **`users_and_brokers.md`**:
    -   **Auth Model**: JWT, OAuth2 flows.
    -   **Roles**: Superuser vs. Normal User.
    -   **Mapping**: How Users are mapped to Brokers (1:N relationship) and data segregation.
-   **`settings.md`**:
    -   **Global Settings**: System-wide configs (read-only for users).
    -   **User Settings**: User-specific preferences (stored in DB).
-   **`registry_pattern.md`**:
    -   Explanation of `ProviderRegistry`.
    -   `@register_provider` decorator.
    -   **Guide**: "How to create a new Plugin".
-   **`security.md`**:
    -   **Threat Model**: Host assumed secure.
    -   **Boundary**: HTTPS/Vault.
    -   **Reporting**: GitHub Issues for API vulnerabilities.

### `developer/backend/brim/` (Broker Report Import Manager)
-   **`architecture.md`**: Workflow (`Upload` -> `Parse` -> `Import`), File Lifecycle, Deduplication.
-   **`generic_csv.md`**: Case Study of `broker_generic_csv` (Header mapping, fallback logic).
-   **`providers_list.md`**: Table of Broker Plugins (Code, Formats, Test Level).

### `developer/backend/assets/` (Asset Pricing & Metadata)
-   **`architecture.md`**: `AssetSourceManager`, Metadata Service, Backward-fill logic.
-   **`system_providers.md`**:
    -   **CSS Scraper**: Selector config.
    -   **Scheduled Investment**: Synthetic value math (bonds/loans).
-   **`providers_list.md`**: Table of External Providers (e.g., `yfinance`, `justetf`).

### `developer/backend/fx/` (Foreign Exchange)
-   **`architecture.md`**: Multi-provider support, Priority System, Normalization.
-   **`providers_list.md`**: Table of FX Plugins (ECB, FED, etc.).

### `developer/api/`
-   **`index.md`**:
    -   Dynamic route generation explanation.
    -   Links to running docs:
        -   🚀 **Swagger UI**: `http://localhost:8000/api/v1/docs`
        -   💻 **ReDoc**: `http://localhost:8000/api/v1/redoc`

### `developer/financial-calculations/`
-   **`index.md`**: Overview.
-   **`day-count.md`**: Day-count conventions.
-   **`interest-types.md`**: Simple vs. Compound.
-   **`compounding.md`**: Frequencies.

### `developer/test-walkthrough/`
-   **Structure**: One file per test category.
-   **Content**: Purpose, command, output, verification.

---

## 6. Tutorials

-   Placeholders for user-facing tutorials (`track-first-stock.md`, `track-p2p-loan.md`).
