# LibreFolio Documentation Plan (Revised v2)

This report outlines the intended structure and content for each file in the `mkdocs_src/docs/` directory, incorporating the latest user feedback.

---

## ⭐️ Overarching Principle

All technical documentation **must be written by reading the final, definitive version of the source code**. The existing content in `docs/` and `LibreFolio_developer_journal/` should be used as **inspiration and for historical context only**.

---

## 1. Root Directory (`index.md`)

-   **Purpose**: Main landing page.
-   **Key Sections**: Welcome message, logo, and **prominent links** to the **User Manual** and **Developer Manual**.

---

## 2. Getting Started

-   **`introduction.md`**: High-level project overview, goals, and tech stack.
-   **`installation.md`**: Instructions for setting up a local **development** environment.

---

## 3. User Manual

-   **`index.md`**: Main entry point for end-user guides.
-   **`installation.md`**: User-friendly guide for deployment and updates (e.g., via Docker).
-   *(Other user-facing guides to be added here)*

---

## 4. Developer Manual

### `developer/index.md`

-   **Purpose**: The main entry point for all technical documentation.

### `developer/architecture/`

-   **Purpose**: High-level architectural documentation.
-   **Files**: `overview.md`, `backend.md`, `frontend.md`, `async.md`, `database.md`.

### `developer/backend/`

-   **Purpose**: Guides for backend-specific development.
-   **Files**:
    -   `getting-started.md`: Local development setup.
    -   `testing.md`: Overview of the testing philosophy and structure.

### `developer/backend/plugins/` (New Section)

-   **Purpose**: To explain the plugin system and document implemented providers.
-   **Files**:
    -   `index.md`: An overview of the plugin architecture, the registration logic (`@register_provider`), and the base classes (`AssetSourceProvider`, `FXRateProvider`).
    -   `yfinance.md`: Detailed documentation for the `yfinance` provider.
    -   `cssscraper.md`: Detailed documentation for the `cssscraper` provider.
    -   `scheduled-investment.md`: Detailed documentation for the `scheduled_investment` provider.
-   **Interlinking**: This section will be linked from the "Contributing" guide and vice-versa.

### `developer/api/` (Restructured)

-   **Purpose**: Granular API reference, broken down by subsystem.
-   **Files**:
    -   `index.md`: A summary of the API and a link to the interactive Swagger UI.
    -   `assets/index.md`, `assets/create.md`, `assets/read.md`, `assets/update.md`, `assets/delete.md`: CRUD operations for assets.
    -   `fx/index.md`, `fx/sync.md`, `fx/convert.md`: Endpoints for the FX system.
    -   *(Other subsystems as they are developed)*

### `developer/financial-calculations/` (New Section)

-   **Purpose**: To explain the mathematical theory behind the financial operations. This is technical content for developers.
-   **Files**:
    -   `index.md`: Overview of the financial math utilities.
    -   `day-count.md`: Explains day-count conventions.
    -   `interest-types.md`: Simple vs. Compound interest.
    -   `compounding.md`: Compounding frequencies.

### `developer/test-walkthrough/`

-   **Purpose**: To guide new developers through the project's logic by explaining the test suite.
-   **Structure**: A series of small, focused markdown files, one for each category in `test_runner.py`.
-   **Content**: Each file will detail the purpose of the tests, the command to run them, a sample of the output, and an explanation of what is being verified.

### `developer/contributing/`

-   **Purpose**: Guides for contributing to the project.
-   **Files**:
    -   `new-fx-provider.md`: How to add a new FX provider.
    -   `new-asset-provider.md`: How to add a new asset pricing provider.
-   **Interlinking**: This section will link to the `developer/backend/plugins/` section for implementation details.

---

## 5. Tutorials

-   Placeholders for user-facing tutorials (`track-first-stock.md`, `track-p2p-loan.md`).
