# API Reference

LibreFolio provides a comprehensive RESTful API built with **FastAPI**.

## Quick Links

- [API Overview](overview.md) - Architecture and design patterns
- [cURL Testing Guide](curl-testing.md) - How to test APIs from terminal

## Interactive Documentation

When the LibreFolio server is running, you can access the auto-generated interactive documentation. These pages allow you to explore the API endpoints, see the expected
request/response schemas, and even execute requests directly from your browser.

- 🚀 [**Swagger UI**](/api/v1/docs) : Best for exploring and testing endpoints.
- 💻 [**ReDoc**](/api/v1/redocs): Best for reading the documentation in a structured format.

## Dynamic Route Generation

FastAPI generates the API routes dynamically at startup based on the Python function definitions. This ensures that the documentation is always perfectly in sync with the code.

The API is structured into routers, each handling a specific domain:

- `/auth`: Authentication (login, token refresh).
- `/users`: User management.
- `/assets`: Asset management (CRUD, price history).
- `/transactions`: Transaction management.
- `/portfolio`: Portfolio analysis and metrics.
- `/fx`: Foreign exchange operations.
- `/brim`: Broker report import.

## Pydantic Schemas

The API uses **Pydantic** models for data validation and serialization. These schemas define the structure of the data exchanged between the frontend and backend. You can find the
schema definitions in the `backend/app/schemas/` directory.
