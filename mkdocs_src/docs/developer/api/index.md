# 📖 API Reference

LibreFolio provides a comprehensive RESTful API built with **FastAPI**.

## 🔗 Quick Links

- [API Overview](overview.md) - Architecture and design patterns
- [cURL Testing Guide](curl-testing.md) - How to test APIs from terminal

## 🖥️ Interactive Documentation

When the LibreFolio server is running, you can access the auto-generated interactive documentation. These pages allow you to explore the API endpoints, see the expected
request/response schemas, and even execute requests directly from your browser.

- 🚀 [**Swagger UI**](http://localhost:6040/api/v1/docs){:target="_blank"} : Best for exploring and testing endpoints.
- 💻 [**ReDoc**](http://localhost:6040/api/v1/redocs){:target="_blank"}: Best for reading the documentation in a structured format.

## 🔀 Dynamic Route Generation

FastAPI generates the API routes dynamically at startup based on the Python function definitions. This ensures that the documentation is always perfectly in sync with the code.

The API is structured into routers, each handling a specific domain (all mounted under `/api/v1` by `backend/app/api/v1/router.py`):

- `/auth`: Authentication (login, token refresh).
- `/users`: User management.
- `/settings`: User settings, admin-managed global settings, scheduler state/logs, and the cache admin routes (`/settings/cache/status`, `/settings/cache/clear/{name}`, `/settings/cache/clear-all` — see [Cache Registry & Admin](../architecture/settings_cache.md)).
- `/system`: Server info and plugin diagnostics (`/system/plugin-diagnostics`).
- `/uploads`: File uploads and media serving.
- `/assets`: Asset management (CRUD, price history) — includes `/prices`, `/provider` (search, live quotes), `/events`.
- `/transactions`: Transaction management.
- `/brokers`: Broker management and sharing — includes `/import` (BRIM broker report import).
- `/backup`: Backup & export.
- `/portfolio`: Portfolio analysis and metrics.
- `/fx`: Foreign exchange operations — includes `/fx/providers` and `/fx/currencies`.
- `/signals`: Domain-agnostic signal preview (`POST /signals/preview`).
- `/risk`: Risk analysis (beta) — analytics catalog, queries, scenario catalog.
- `/ai-export`: Versioned AI Export datasets and analyses.
- `/utilities`: Reference data (ISO currencies, etc.).

## 📋 Pydantic Schemas

The API uses **Pydantic** models for data validation and serialization. These schemas define the structure of the data exchanged between the frontend and backend. You can find the
schema definitions in the `backend/app/schemas/` directory.
