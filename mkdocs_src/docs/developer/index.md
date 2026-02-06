# 👨‍💻 Developer Manual

Welcome to the Developer Manual. This section contains in-depth technical documentation about the LibreFolio architecture, codebase, and development practices.

## Core Concepts

- **[Technologies](technologies/overview.md)**: An overview of the libraries and frameworks used in the project.
- **[Architecture](architecture/overview.md)**: High-level diagrams and explanations of the system architecture.

## Backend Development

- **[BRIM (Broker Report Import Manager)](backend/brim/architecture.md)**: The architecture of the CSV import system.
- **[Asset Pricing & Metadata](backend/assets/architecture.md)**: How asset prices and metadata are fetched and managed.
- **[Foreign Exchange (FX)](backend/fx/architecture.md)**: The multi-provider currency conversion system.

## Guides

- **[Creating a New Plugin](architecture/registry_pattern.md#guide-how-to-create-a-new-plugin)**: A step-by-step guide to adding a new provider for BRIM, Assets, or FX.
- **[Database Migrations (Alembic)](technologies/alembic.md)**: How to manage database schema changes.
- **[API Reference](api/index.md)**: Information on the FastAPI endpoints and how to use them.
- **[Test Walkthrough](test-walkthrough/index.md)**: An explanation of the project's test suite.
