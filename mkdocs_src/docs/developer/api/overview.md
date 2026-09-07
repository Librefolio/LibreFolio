# 🌐 API & Frontend Communication

This section explains how the SvelteKit frontend communicates with the FastAPI backend, ensuring type safety and consistency across the stack.

## 🏗️ Architecture

LibreFolio uses a strict **OpenAPI-first** approach (generated from code) to synchronize the backend and frontend.

```mermaid
graph LR
    Backend[FastAPI Backend] -- "Generates" --> OpenAPI[openapi.json]
    OpenAPI -- "openapi-zod-client" --> TSClient[generated.ts]
    TSClient -- "Imports" --> Frontend[SvelteKit Frontend]
    
    Frontend -- "Calls" --> TSClient
    TSClient -- "Validates (Zod)" --> TSClient
    TSClient -- "HTTP Request" --> Backend
```

## 🔄 The Synchronization Workflow

The synchronization process is automated via `dev.py`:

1. **Backend Definition**: API endpoints and Pydantic models are defined in Python (`backend/app/api/`).
2. **Schema Export**: `./dev.py api schema` starts a temporary backend process to export the `openapi.json` file.
3. **Client Generation**: `./dev.py api client` uses `openapi-zod-client` to read the JSON schema and generate a TypeScript client (`frontend/src/lib/api/generated.ts`).

!!! tip "One-step sync"

    Use `./dev.py api sync` to run both steps (schema export + client generation) in a single command. This is the recommended workflow after any backend API change.

### 💻 CLI Commands

```bash
# Export OpenAPI schema only
./dev.py api schema

# Generate TypeScript client from existing schema
./dev.py api client

# Both in one step (recommended)
./dev.py api sync
```

### ⚡ Generated Client Features

The generated client provides:

- **TypeScript Interfaces**: Matching the Pydantic models (e.g., `AssetRead`, `TransactionCreate`).
- **Zod Schemas**: Runtime validation schemas for API responses.
- **API Functions**: Typed functions for each endpoint (e.g., `api.getAssets()`).

## 🖥️ Usage in Frontend

In the SvelteKit frontend, developers import the generated client to make API calls.

```typescript
import { api } from '$lib/api';

async function loadPortfolio() {
    // 'data' is fully typed as PortfolioResponse
    const data = await api.getPortfolio();
    return data;
}
```

This ensures that if the backend API changes (e.g., a field is renamed), the frontend build will fail with a type error, preventing runtime crashes.

---

## 📜 Contract Rules

Three rules the pipeline depends on. Breaking any of them fails the **frontend build**, not a
backend test — which is why they are written down here.

### 1. Every endpoint declares `response_model`

Every API endpoint declares an explicit `response_model` Pydantic schema: the generated client
is only as typed as the OpenAPI schema, and an endpoint without a model silently degrades to
`unknown`. The audit (08) closed the last stragglers; the deliberate exceptions are endpoints
that do not return JSON documents — the SSE stream (`GET /assets/provider/search/stream`),
binary file downloads (`FileResponse` under `/uploads/file/…`, `/brim/files/…/download`), and a
handful of legacy `dict` returns.

### 2. New discriminated-union members register in `fix-openapi-discriminators.mjs`

Pydantic discriminated unions (`Annotated[A | B, Field(discriminator="kind")]`) generate
correct OpenAPI, but `openapi-zod-client` exports each member as
`const Member: z.ZodType<Member> = …` — the exported `z.ZodType<T>` annotation **hides the
`ZodObject` methods** that `z.discriminatedUnion` needs, and the generated client fails to
compile. The post-processor `frontend/scripts/fix-openapi-discriminators.mjs` strips that
annotation for a hardcoded list of schemas (**40 today**), letting TypeScript infer the
concrete type while keeping the exported alias. It runs as part of `npm run generate-api`
(which `./dev.py api sync` / `./dev.py api client` wrap) and **throws** if a registered schema
is not found exactly once — a stale entry fails loud, never silently.

> When you add a new member to a discriminated union, add its schema name to
> `discriminatedSchemas` in `frontend/scripts/fix-openapi-discriminators.mjs`, then re-run
> `./dev.py api sync`.

### 3. Discriminator fields carry an explicit `enum`

The discriminator field of each union member must pin its value with
`Field(json_schema_extra={"enum": [...]})`:

```python
class SchedulerLogCurrentPriceEntry(BaseModel):
    job: Literal["current_price"] = Field(json_schema_extra={"enum": ["current_price"]})
```

Without the extra, the discriminator is emitted without an enum constraint and the generated
TypeScript client fails to compile (real incident, 03/09 — the scheduler log union). This
pattern is used across `schemas/signals.py`, `schemas/ai_export_runtime.py`, `schemas/risk.py`,
`schemas/risk_scenarios.py`, and `schemas/settings.py`.

---

## 📡 Notable Endpoints

### `POST /api/v1/assets/prices/current` — Bulk Current Price

Returns the **live current price** for a list of asset IDs. The response is designed for the `LiveTicker` frontend component.

**Request body**: `List[int]` — asset IDs.

**Response** (`FACurrentPriceResponse`):

```json
{
  "results": [
    {
      "asset_id": 1,
      "value": "123.45",
      "currency": "EUR",
      "source": "justetf",
      "timestamp": "2026-04-10T12:00:00Z",
      "error": null
    }
  ]
}
```

**Resolution strategy** (per asset):

1. Ask the assigned provider's `get_current_value()` (live quote from JustETF WebSocket, Yahoo Finance `ticker.info`, etc.)
2. **Fallback**: if the provider fails or has no live feed, return the latest close price from the database.

This endpoint is used by the `LiveTicker` component in the Dashboard and Asset Detail pages, and by the Asset List page for inline live prices in cards.

