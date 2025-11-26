# Overall Architecture

LibreFolio is a modern web application with a decoupled frontend and backend, designed to be deployed as a single Docker container.

## 🏛️ High-Level Diagram

```
┌───────────────────┐      ┌───────────────────────────┐      ┌────────────────┐
│   Web Browser     │◄───►│        Web Server         │◄───►│    Backend     │
│ (React Frontend)  │      │  (FastAPI serves static)  │      │ (FastAPI API)  │
└───────────────────┘      └───────────────────────────┘      └───────┬────────┘
                                                                     │
                                                                     ▼
                                                          ┌────────────────┐
                                                          │    Database    │
                                                          │    (SQLite)    │
                                                          └────────────────┘
```

## 🥞 Core Components

### 1. Frontend
- **Framework**: React with TypeScript and Vite.
- **UI Components**: Material UI (MUI).
- **State Management**: React Query for server state and Zustand/Context for global UI state.
- **Functionality**: Provides the user interface for portfolio visualization, data entry, and reporting. It is a pure client-side application that communicates with the backend via a REST API.

### 2. Backend
- **Framework**: FastAPI (Python).
- **Architecture**: A 3-layer architecture is used to separate concerns:
    - **API Layer**: Handles HTTP requests, validation (Pydantic), and response formatting.
    - **Service Layer**: Contains the core business logic (e.g., portfolio analysis, FX conversion, data fetching).
    - **Database Layer**: Manages data persistence using SQLModel and SQLAlchemy.
- **Database**: SQLite for simplicity and self-hosting.
- **Async**: The entire backend is built on an `async` foundation for high performance.

### 3. Deployment
- **Containerization**: The frontend and backend are bundled into a **single Docker image**.
- **Serving**: The FastAPI backend serves the static frontend files, simplifying deployment.

## 🕵️ How to get information about the overall architecture

To get information about the overall architecture an Agent can:

1. Read this file.
2. Read the `LibreFolio_developer_journal/01-Riassunto_generale.md` file.
3. Inspect the directory structure of the project.
4. Read the `mkdocs.yml` file to understand the documentation structure.
