# Backend Architecture

The backend is a Python application built with FastAPI, designed for performance, type safety, and clear separation of concerns.

## 🏗️ 3-Layer Architecture

The backend follows a classic 3-layer architecture:

```
┌─────────────────────────────────────────┐
│  API Layer (FastAPI Endpoints)         │  ← Request validation, response formatting
│  Location: backend/app/api/v1/         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Service Layer (Business Logic)        │  ← Core logic, calculations
│  Location: backend/app/services/       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Database Layer (SQLModel/SQLAlchemy)  │  ← Data persistence
│  Location: backend/app/db/             │
└─────────────────────────────────────────┘
```

1.  **API Layer**: Defines the REST endpoints using FastAPI. Its only job is to handle HTTP requests, validate incoming data using Pydantic models, call the appropriate service, and format the response. It contains no business logic.
2.  **Service Layer**: The core of the application. This layer contains all business logic, such as:
    *   Portfolio and asset analysis.
    *   FX rate conversion.
    *   Orchestration of data fetching from external providers.
    *   Database transaction management.
3.  **Database Layer**: Defines the database schema using SQLModel and manages database sessions.

## 🔌 Plugin-Based Provider System

A key feature is the modular provider system for fetching external data (both for assets and FX rates).

- **Location**: `backend/app/services/{asset_source_providers|fx_providers}/`
- **Pattern**: Providers are auto-discovered at startup. Any Python file dropped into these folders containing a class that inherits from the correct base class and is decorated with `@register_provider` will be automatically available.
- **Extensibility**: This makes it easy for the community to add new data sources without touching the core application logic.

##  asynchronous by a-syncio library and it is used for all the I/O bound operations.

The entire backend is built on an `async` foundation to handle concurrent requests efficiently.

- **FastAPI** is an async-native framework.
- **Database access** uses `aiosqlite` and `AsyncSession` from SQLAlchemy.
- **External API calls** use the `httpx` async client.

This non-blocking approach allows the server to handle many simultaneous user requests with minimal resources. For more details, see the [Async Architecture](./async.md) guide.

## 🕵️ How to get information about the backend architecture

To get information about the backend architecture an Agent can:
- [ ] Read this file.
- [ ] Read the `docs/async-architecture.md` file to understand the async implementation.
- [ ] Inspect the directories `backend/app/api/`, `backend/app/services/`, and `backend/app/db/`.
- [ ] Run the tests for each layer to see them in action:
    - `./test_runner.py api all`
    - `./test_runner.py services all`
    - `./test_runner.py db all`
