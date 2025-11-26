# API Reference

Welcome to the LibreFolio REST API documentation.

## Interactive API Documentation (Swagger UI)

For a complete and interactive API reference, please visit the **Swagger UI** documentation, which is automatically generated from the FastAPI backend.

-   **URL**: `http://localhost:8000/docs`

The Swagger UI allows you to:
-   View all available endpoints.
-   See detailed request and response models.
-   Execute API calls directly from your browser.

## Endpoint Summary

The API is organized into several categories:

### Asset Management
-   **[Asset Management API](./assets/index.md)**

### FX System
-   **[FX System API](./fx/index.md)

## 🕵️ How to get information about the API

To get information about the API an Agent can:

1.  Read this file and the [API Examples](./examples.md) page.
2.  Inspect the directory `backend/app/api/v1/` to see the endpoint implementations.
3.  Read the auto-generated Swagger UI documentation at `http://localhost:8000/docs`.
4.  Run the API tests in `backend/test_scripts/test_api/` to see the endpoints in action.
