---
title: "OpenAPI Zod discriminator type erasure"
category: problem
status: resolved
date: 2026-07-23
tags: [frontend, openapi, zodios, zod, pydantic, codegen]
related: [zodios-api-client, signal-backend-plugin-architecture]
---

# Problem: OpenAPI Zod discriminator type erasure

## Symptom

`./dev.py api sync` generated valid-looking `z.discriminatedUnion()` calls, but `svelte-check` failed because each referenced option had been annotated as `z.ZodType<T>` rather than a concrete `ZodObject`. Pydantic `Literal` discriminators with defaults also became optional OpenAPI fields and `const` alone was widened to `z.string()`.

## Root Cause

`openapi-zod-client` 1.18.3 combines `--export-types` with `const Name: z.ZodType<Name> = z.object(...)`. That annotation erases the object methods required by Zod's discriminated-union type signature. The generator also does not preserve OpenAPI 3.1 `const` as a TypeScript/Zod literal unless it sees a singleton `enum`.

## Solution

Signal discriminator fields are required `Literal` fields with singleton-enum JSON Schema metadata. Pre-validators inject the known discriminator for internal Python constructors, while wire schemas remain required. After generation, `frontend/scripts/fix-openapi-discriminators.mjs` removes the generic annotation only from the seven discriminated option schemas, with an exact-occurrence fail-fast check. All other exported types remain unchanged, avoiding regressions in existing Zodios request/default semantics.

## Prevention

- Always run `./dev.py api sync` followed by `./dev.py front check` when adding discriminated Pydantic unions.
- Keep discriminator fields required in OpenAPI and represent their value as a singleton enum.
- Do not remove `--export-types` globally: it changes established input/default/read-only typing elsewhere.
- Update the post-processor's explicit schema list only when a new referenced discriminated option is added.

## Source files

| Role | Path |
|------|------|
| Pydantic discriminators | `backend/app/schemas/signals.py` |
| Codegen post-processor | `frontend/scripts/fix-openapi-discriminators.mjs` |
| Generator command | `frontend/package.json` |
| Generated client | `frontend/src/lib/api/generated.ts` |
| Runtime contract tests | `frontend/src/lib/charts/signals/__tests__/backendTypes.test.ts` |
