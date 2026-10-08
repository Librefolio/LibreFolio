# 👨‍💻 Developer Manual

Welcome to the Developer Manual. This section contains in-depth technical documentation about the LibreFolio architecture, codebase, and development practices.

---

## 🚀 Getting Started

Set up your local development environment and learn the daily workflow:

- 📦 **[Host Installation](../admin/host_installation.md)** — Set up Python, Node.js, and Pipenv environment
- 🔄 **[Developer Workflow](dev_workflow.md)** — Start Vite dev server and view all development CLI commands
- 🚦 **[Lint Gates & Code Policy](lint_gates.md)** — The ruff gate list, justified-noqa conventions, and code policies the linter can't express

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
    - 🧰 [Tool Plugins](architecture/patterns/tool_plugins.md) — Atomic, typed calculations behind a versioned catalogue (first tool: the PAC allocator), each computed in a spawned process the executor owns
    - 🗄️ [Database Migrations](architecture/patterns/alembic.md) — Alembic workflow, SQLite batch mode
    - ⚙️ [Configuration](architecture/settings.md) — `.env` loading, Pydantic `BaseSettings`, global settings (admin options: [Configuration](../admin/configuration.md))
- 🔐 **Core Systems**:
    - 🛡️ [Security & Authentication](architecture/security.md) — JWT cookies, endpoint protection
    - 👤 [Users & Roles](architecture/users_and_brokers.md) — Login flow, session, user roles
    - 🔑 [Access Control (RBAC)](architecture/access_control.md) — Broker sharing permissions
    - ⚙️ [Settings System](architecture/settings.md) — SETTINGS_REGISTRY, user vs global storage, base-currency resolution
    - 🧹 [Cache Registry & Admin](architecture/settings_cache.md) — named theine caches, `/settings/cache/*` admin endpoints
- 🗃️ **Database Schema**:
    - 📊 [Overview](architecture/database/index.md) — ER diagram, design philosophy
    - 👤 [Users & Access](architecture/database/users_access.md) · 🏦 [Brokers & Transactions](architecture/database/brokers_transactions.md) · 📈 [Assets & Pricing](architecture/database/assets_pricing.md) · 💱 [FX Rates & Routes](architecture/database/fx_rates.md)

---

## ⚙️ Backend

- 📥 **[BRIM (Broker Report Import Manager)](backend/brim/architecture.md)** — CSV/Excel import pipeline, plugin architecture
- 📈 **[Asset Pricing & Metadata](backend/assets/architecture.md)** — How asset prices and metadata are fetched and managed
- 📏 **[Price Resolver](backend/transactions/price_resolver.md)** — The single daily valuation-mark source behind NAV/MWRR/TWRR/ROI
- 💱 **[Foreign Exchange (FX)](backend/fx/architecture.md)** — Multi-provider currency conversion system
    - 🔀 [FX Configuration & Routing](backend/fx/configuration.md) — Chain routing algorithm
    - 🔌 [FX Providers](backend/fx/providers/index.md) — ECB, FED, BOE, SNB technical details
- 📉 **[Risk Engine](backend/risk/architecture.md)** — Bulk risk analytics behind `/api/v1/risk`: plugin catalogue, eligibility verdicts, simulation and optimization in spawned worker pools
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
- 🧭 **[Onboarding Guides](frontend/onboarding.md)** — Welcome setup, intro tour and contextual guides, with versioned per-user progress kept by the backend

---

## 🌐 API

- 📋 **[API Overview](api/overview.md)** — OpenAPI-first workflow, schema export, TypeScript client generation
- 📖 **[API Reference](api/index.md)** — FastAPI endpoint documentation

---

## 🧪 Testing

- 🔍 **[Test Walkthrough](test-walkthrough/index.md)** — Full guide to the 10-category test suite
    - 🔧 **Backend**: External, Database, Services, Utils, Schemas, API, E2E
    - 🎭 **[Frontend (Playwright)](test-walkthrough/front-overview.md)**: Front-Utility, Front-User, Front-FX
