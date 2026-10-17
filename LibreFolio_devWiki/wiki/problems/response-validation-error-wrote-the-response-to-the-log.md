---
title: "A response that broke its model was written to the server log: FastAPI has no handler for `ResponseValidationError`"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, api, fastapi, logging, security, privacy, workstream-h, release-1.3]
related:
  - concepts/fastapi-0141-routing-and-validation-gotchas
  - decisions/request-floats-refuse-inf-and-nan
---

# Problem: a 500 from a response model left the response in the log

## Symptom

From a security review (workstream E, R13-SEC4): when an endpoint returns what its `response_model` refuses, the client
gets `500 Internal Server Error`, and uvicorn logs «Exception in ASGI application» with the traceback. Its message
lists the response's content.

## Root Cause

- FastAPI 0.141 registers default handlers for `HTTPException`, `RequestValidationError` and the WebSocket one, but
  **none** for `ResponseValidationError`.
- `ValidationException.__str__` writes every error dict, **`input` included**: the response itself, the data of the
  user who asked. The exception also carries the whole `body`.
- `SecurityHeadersMiddleware` already answered that 500 with the security headers, then re-raised the exception, so it
  still reached uvicorn's log.

## Solution

Lot H-33 (17/10). `install_response_validation_handler(app)` (`backend/app/api/response_validation.py`) runs right after
A's 422 handler in `backend/app/main.py`. It writes one ERROR event, «A response does not match its model», with:

- the method;
- the **full** route template, from the exception's public `endpoint_path` («GET /api/v1/…»): `scope["route"]` lacks
  the prefix of an included router;
- the endpoint's name, from `scope["endpoint"]`;
- for each error, its `type` and `loc` only.

It never logs the `input`, the `msg` (a validator may build it from the value) or the traceback, whose message is
`str(exc)`. The handler deliberately uses `logger.error`, not `logger.exception`, against the TRY400 convention of
`lint_gates.md`, and a comment in the code says why. The answer is the same plain-text 500, and the exception now stops
at the handler.

## Prevention

- A handler for a FastAPI or pydantic validation exception logs the errors by `type` and `loc`, never with
  `exc_info`.
- Latent: a typed generator endpoint (FastAPI streaming) would fail validation after the response has started; then
  Starlette raises a chained `RuntimeError`, with `str(exc)` back in the traceback. LibreFolio has none today.

## Impact

User data could reach the server log whenever a response broke its model; no client-visible change.

## Source files

| Role | Path |
|------|------|
| The handler and its install | `backend/app/api/response_validation.py` |
| Where it is installed, after the 422 handler | `backend/app/main.py` |
| The sibling handler: a 422 without the request's input | `backend/app/api/validation_errors.py` |
| The middleware that already answered the 500 with headers | `backend/app/services/platform/security_headers.py` |
| Tests (fresh apps, the real app's handler table, captured logs) | `backend/test_scripts/test_services/test_response_validation.py` |
| «Request Logs» | `mkdocs_src/docs/developer/architecture/security.md` |
| Lot H-33 | `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md` |
