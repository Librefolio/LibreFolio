---
title: "A multi-line docstring with backticks breaks the generated client"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, frontend, api-client, openapi, zodios, pydantic, generated-code, tools]
related:
  - problems/generated-client-widens-nullable-scalar
  - problems/openapi-zod-discriminator-type-erasure
  - problems/front-check-does-not-check-what-you-think
  - decisions/zodios-api-client
---

# A multi-line docstring with backticks breaks the generated client

## Summary

A Pydantic model's docstring becomes its schema's `description` in the OpenAPI document. The client generator copies
that description into the generated Zod code through `.describe(...)`: single-line text goes between single quotes,
multi-line text into a JS template literal, **without escaping its backticks**. One multi-line docstring that
mentions a field the reST way, between double backticks, leaves `frontend/src/lib/api/generated.ts` syntactically
broken, and everything that imports the client fails with it.

## Symptom

J-19 (17/10) gave `ToolItemMetrics` (`backend/app/schemas/tools.py`) a second docstring paragraph that named the new
field between double backticks. After `./dev.py api sync`:

- `front check`: 2 errors, both in `generated.ts` («This expression is not callable. Type 'String' has no call
  signatures», at the two `metrics: ToolItemMetrics.describe(...)` sites);
- `front-utility core-unit`: dozens of suites failed to load, from assets to backup, email and risk, because they
  import the client.

The backend tests stayed green: only the generated frontend code was broken.

## Root cause

```text
metrics: ToolItemMetrics.describe(`Monotonic durations; …

``worker_exit_code`` (J-19) is …`)
```

The first inner backtick closes the template literal; what follows parses as a tagged template on a string.

The same file already held a backtick docstring that never broke: `ToolMemoryMetrics`, «enforcement strength is
explicit in ``mode``». It is a single line, so the generator wrote it between single quotes, where a backtick is
just a character.

## Solution

The `ToolItemMetrics` docstring went back to its single line, and the new field is explained in a code comment above
it. A comment never reaches the schema.

## Prevention

- In an API schema model (anything under `backend/app/schemas/` that reaches a response), keep the class docstring
  to one line, or keep backticks out of a multi-line one. Explain fields in comments, or in a one-line
  `Field(description=...)`.
- After any change to a schema docstring, run `./dev.py api sync` and then `./dev.py front check`. The backend suites
  cannot see this breakage.

## Source files

| Role | Path |
|------|------|
| The model whose docstring broke the client | `backend/app/schemas/tools.py` (`ToolItemMetrics`) |
| The single-line docstring that never broke | `backend/app/schemas/tools.py` (`ToolMemoryMetrics`) |
| Generated client (git-ignored) | `frontend/src/lib/api/generated.ts` |
