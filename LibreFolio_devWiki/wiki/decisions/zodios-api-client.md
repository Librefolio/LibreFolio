---
title: "Zodios for type-safe API client"
category: decision
status: resolved
date: 2026-01-01
tags: [frontend, api, typescript, zodios, openapi, zod]
related: [decisions/sveltekit-over-react, entities/api-router]
---

# Decision: Zodios for Type-Safe API Client

## Context
Phase 1 needed a robust API client strategy. The frontend must communicate with the FastAPI backend and needs TypeScript types, runtime validation, and easy maintenance as the API evolves.

## Options Considered
1. **Raw `fetch` with manual types** — no runtime validation, types drift from backend over time, no interceptor support.
2. **Axios + manual TS types** — adds interceptors but still no runtime validation; types still drift.
3. **Zodios (`@zodios/core`)** — generates Axios-backed client from OpenAPI spec, Zod runtime validation of responses, types auto-generated from `generated.ts`.
4. **TanStack Query + openapi-typescript** — heavier setup, different mental model.

## Decision
**Zodios** was chosen. Key reasons:
- `frontend/src/lib/api/generated.ts` is auto-generated from the FastAPI OpenAPI schema via `./dev.py api sync`
- Zod runtime validation catches response mismatches at the boundary — fails loudly instead of silently passing bad data
- TypeScript types flow from OpenAPI → `generated.ts` → all components without manual maintenance
- Interceptors handle 401 (redirect to login) and inject `Accept-Language` header for i18n

## Consequences
- **Rule**: after any backend API change, `./dev.py api sync` must be run to regenerate `generated.ts`
- `frontend/src/lib/api/index.ts` exports `zodiosApi`, `ApiError`, `axiosInstance`
- `frontend/src/lib/api/zodios-client.ts` wraps `createApiClient` from `./generated`
- All API calls go through `zodiosApi.*` — never raw fetch or raw axios
- Axios is the underlying transport (accessible via `axiosInstance` for edge cases)

## Links
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-01-foundation.md`

## Source files

| Role | Path |
|------|------|
| Zodios client wrapper | `frontend/src/lib/api/zodios-client.ts` |
| Auto-generated API types | `frontend/src/lib/api/generated.ts` |
| API exports | `frontend/src/lib/api/index.ts` |
| Phase 1 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-01-foundation.md` |
