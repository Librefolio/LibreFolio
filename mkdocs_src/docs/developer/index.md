# 👨‍💻 Developer Manual

Welcome to the Developer Manual. This section contains in-depth technical documentation about the LibreFolio architecture, codebase, and development practices.

---

## 🚀 Getting Started

Set up your local development environment and learn the daily workflow:

- 📦 **[Installation (Development)](dev-installation.md)** — Clone, install dependencies, start the server
- 🔄 **[Development Workflow](dev-installation.md#development-workflow)** — All `dev.py` commands at a glance

!!! tip "Quick start"

    ```bash
    ./dev.py install         # Install all dependencies
    ./dev.py db create-clean # Create fresh database
    ./dev.py server          # Start backend server
    ./dev.py front dev       # Start frontend dev server (separate terminal)
    ```

---

## 🏗️ Architecture & Technologies

- 🗺️ **[System Overview](architecture/overview.md)** — High-level system diagrams, tech stack, and design decisions
- 🧩 **Technologies & Patterns**:
    - ⚡ [Async Architecture](architecture/patterns/async.md) — async/await, aiosqlite, non-blocking I/O
    - 🔌 [Registry & Plugin System](architecture/patterns/registry_pattern.md) — Provider plugins for BRIM, Assets, FX
    - 🗄️ [Database Migrations](architecture/patterns/alembic.md) — Alembic workflow, SQLite batch mode
    - ⚙️ [Configuration](architecture/patterns/configuration.md) — `.env`, Pydantic BaseSettings
- 🔐 **Core Systems**:
    - 🛡️ [Security & Authentication](architecture/security.md) — JWT cookies, endpoint protection
    - 👤 [Users & Roles](architecture/users_and_brokers.md) — Login flow, session, user roles
    - 🔑 [Access Control (RBAC)](architecture/access_control.md) — Broker sharing permissions
    - ⚙️ [Settings System](architecture/settings.md) — Global + user settings, fallback logic
- 🗃️ **Database Schema**:
    - 📊 [Overview](architecture/database/index.md) — ER diagram, design philosophy
    - 👤 [Users & Access](architecture/database/users_access.md) · 🏦 [Brokers & Transactions](architecture/database/brokers_transactions.md) · 📈 [Assets & Pricing](architecture/database/assets_pricing.md) · 💱 [FX Rates & Routes](architecture/database/fx_rates.md)

---

## ⚙️ Backend

- 📥 **[BRIM (Broker Report Import Manager)](backend/brim/architecture.md)** — CSV/Excel import pipeline, plugin architecture
- 📈 **[Asset Pricing & Metadata](backend/assets/architecture.md)** — How asset prices and metadata are fetched and managed
- 💱 **[Foreign Exchange (FX)](backend/fx/architecture.md)** — Multi-provider currency conversion system
    - 🔀 [FX Configuration & Routing](backend/fx/configuration.md) — Chain routing algorithm
    - 🏛️ [FX Providers List](backend/fx/providers_list.md) — ECB, FED, BOE, SNB details
- 🗃️ **[Database Schema](architecture/database/index.md)** — SQLite schema split by subsystem (Users, Brokers, Assets, FX)

---

## 🎨 Frontend

- 🖥️ **[Frontend Development](frontend/index.md)** — SvelteKit architecture, Svelte 5 Runes, directory structure
    - 🧱 [Components](frontend/components/index.md) — Reusable UI component library
    - 📄 [Pages](frontend/pages/index.md) — Application pages and routing
    - 📦 [State Management](frontend/state/index.md) — Stores and reactive state
    - 🎨 [Styling](frontend/styling.md) — Tailwind CSS 4 and theming
- 🌍 **[Internationalization (i18n)](frontend/i18n.md)** — Multi-language support, audit CLI, key management
- 🔗 **[FX Chain Algorithm](frontend/fx-chain-algorithm.md)** — DFS + graphology for multi-step FX routes

---

## 🌐 API

- 📋 **[API Overview](api/overview.md)** — OpenAPI-first workflow, schema export, TypeScript client generation
- 📖 **[API Reference](api/index.md)** — FastAPI endpoint documentation

---

## 🧪 Testing

- 🔍 **[Test Walkthrough](test-walkthrough/index.md)** — Full guide to the 10-category test suite
    - 🔧 **Backend**: External, Database, Services, Utils, Schemas, API, E2E
    - 🎭 **[Frontend (Playwright)](test-walkthrough/front-overview.md)**: Front-Utility, Front-User, Front-FX
