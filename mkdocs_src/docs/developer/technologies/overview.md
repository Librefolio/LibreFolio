# Technologies Overview

LibreFolio is built with a modern, robust, and efficient technology stack. This page provides an overview of the key libraries and frameworks used in the project.

## Backend

- **[FastAPI](https://fastapi.tiangolo.com/)**: A high-performance web framework for building APIs with Python 3.11+, based on standard Python type hints. It provides automatic
  interactive documentation (Swagger UI and ReDoc).

- **[SQLAlchemy](https://www.sqlalchemy.org/)**: The SQL toolkit and Object-Relational Mapper (ORM) used for all database interactions. LibreFolio uses SQLAlchemy's **asyncio
  support** for non-blocking database queries.

- **[Pydantic](https://docs.pydantic.dev/)**: A data validation and settings management library. It is used extensively for defining data schemas, validating API requests, and
  managing application settings.

- **[Alembic](https://alembic.sqlalchemy.org/)**: A lightweight database migration tool for SQLAlchemy. It allows for the management of database schema changes over time.

- **[SQLite](https://www.sqlite.org/)**: The default database engine. It is simple, serverless, and perfect for a self-hosted application. The database is configured to run in
  WAL (Write-Ahead Logging) mode for better concurrency.

## Frontend

- **[SvelteKit](https://kit.svelte.dev/)**: A web application framework for building fast, modern user interfaces. It provides server-side rendering (SSR), routing, and a great
  developer experience.

- **[TypeScript](https://www.typescriptlang.org/)**: A statically typed superset of JavaScript that adds type safety to the frontend codebase.

- **[TailwindCSS](https://tailwindcss.com/)**: A utility-first CSS framework for rapidly building custom designs.

- **[Vite](https://vitejs.dev/)**: The build tool and development server used for the frontend. It provides extremely fast Hot Module Replacement (HMR).

## Testing

- **[Pytest](https://docs.pytest.org/)**: The framework used for writing and running backend tests.
- **[Playwright](https://playwright.dev/)**: A framework for end-to-end testing of the web application.
- **[Coverage.py](https://coverage.readthedocs.io/)**: A tool for measuring code coverage of Python programs.
