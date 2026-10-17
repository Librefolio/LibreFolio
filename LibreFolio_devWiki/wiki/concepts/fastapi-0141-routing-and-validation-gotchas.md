---
title: "FastAPI 0.141: five behaviours that route-walking tests and error handlers must know"
category: concept
tags: [backend, fastapi, starlette, pydantic, testing, api, validation, workstream-h, release-1.3]
related:
  - decisions/request-floats-refuse-inf-and-nan
  - problems/response-validation-error-wrote-the-response-to-the-log
---

# Concept: what FastAPI 0.141 does that a test or a handler can get wrong

## Definition

Five behaviours of the pinned stack (fastapi 0.141.1, starlette 1.6.0, pydantic 2.13.5), each verified in process
during lots H-32 and H-33 of release 1.3 (17/10). Each has already produced, or nearly produced, a wrong test or a wrong
handler.

1. **Included routers are lazy.** `app.routes` holds `_IncludedRouter` wrappers. A loop over it with
   `isinstance(route, APIRoute)` sees only the app's own routes (4 in LibreFolio, the static site), **not** the 177 API
   routes. Walk with `fastapi.routing.iter_route_contexts(app.routes)`: `context.original_route` is the route,
   `context.dependant` the effective dependant with the router's dependencies, and the full path is
   `context.starlette_route.path` when present, else `context.path`. A route-walking guard without a barrier on the
   number of routes can pass while checking nothing.
2. **`scope["route"]` lacks the include prefix.** It is the router's own `APIRoute`, so its `path` is `/auth/login`,
   not `/api/v1/auth/login`.
   - The full template is a validation exception's public `endpoint_path`, «GET /api/v1/auth/login»;
   - `endpoint_function` is a string and may be `None`;
   - `scope["endpoint"].__name__` gives the endpoint's name more reliably.
3. **Non-finite floats in a response become `null`.**
   - A route with a `response_model` serialises through pydantic's JSON, which writes infinity and NaN as `null`:
     `200 {"x": null}`.
   - `model_dump(mode="json")` alone keeps `inf`.
   - A route without a `response_model` returning raw floats fails in Starlette's renderer (`allow_nan=False`): a 500.
4. **The stock 422 echoes the input.** FastAPI's own `RequestValidationError` handler puts each error's `input` in the
   answer.
   - A non-finite value on a field that refuses it (`FiniteFloat`) cannot be rendered, and the 422 becomes a **500**.
     That holds for `Infinity`, `NaN` and `1E+400`; the string `"inf"` still gets its 422.
   - A missing field echoes the whole object around it, a password included.
5. **No handler for `ResponseValidationError`.** Unhandled, its traceback carries `str(exc)`, every error with its
   `input`: [[problems/response-validation-error-wrote-the-response-to-the-log]].

## Where It Applies

- **Tests and guards that walk the routes**: `test_instance_block.py` (allow-list),
  `test_request_float_inputs.py` (the request floats).
- **Error handlers**:
  - A's `install_validation_error_handler()` (`backend/app/api/validation_errors.py`), which drops `input` and so
    cures behaviour 4;
  - the `NoInputEchoRoute` of `backend/app/api/no_echo.py`, the route class of the plugin-settings and backup routers;
  - `install_response_validation_handler()`, which cures behaviour 5.
- **Schemas**: [[decisions/request-floats-refuse-inf-and-nan]].

## Examples

```python
from fastapi.routing import APIRoute, iter_route_contexts

contexts = [c for c in iter_route_contexts(app.routes) if isinstance(c.original_route, APIRoute)]
assert len(contexts) >= 150  # the barrier: a FastAPI change that hides routes must fail, not pass empty
```

## Source files

| Role | Path |
|------|------|
| A route walk with `iter_route_contexts` (the allow-list of the instance block) | `backend/test_scripts/test_api/test_instance_block.py` |
| A route walk with barriers, and the floats it judges | `backend/test_scripts/test_services/test_request_float_inputs.py` |
| The 422 without the input | `backend/app/api/validation_errors.py` |
| The route class that drops the input of a 422 | `backend/app/api/no_echo.py` |
| `endpoint_path` and `scope["endpoint"]` in a handler | `backend/app/api/response_validation.py` |
| The measurements (lots H-32 and H-33) | `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md` |
