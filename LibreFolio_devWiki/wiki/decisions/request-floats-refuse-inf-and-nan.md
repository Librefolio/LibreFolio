---
title: "Every float a request can carry refuses infinity and NaN in its schema: field by field, not in the base model"
category: decision
status: resolved
date: 2026-10-17
tags: [backend, api, validation, pydantic, fastapi, security, workstream-h, release-1.3]
related:
  - concepts/fastapi-0141-routing-and-validation-gotchas
  - problems/response-validation-error-wrote-the-response-to-the-log
---

# Decision: a request float is finite, and a guard walks every route to keep it so

## Context

Report A-35 (workstream A, lot H-32, 17/10): a plain `float` field of a request body accepts `1E+400` and answers 200;
if a route sends it back, Starlette's renderer (`allow_nan=False`) fails with a 500. The ground under it:

- pydantic accepts `inf`, `-inf` and `nan` in a `float` by default (`allow_inf_nan=True`);
- FastAPI parses the body with Python's `json`, which reads `1E+400` as infinity and accepts the `NaN` and `Infinity`
  tokens;
- **measured on FastAPI 0.141.1**: a route **with** a `response_model` answers `200 {"x": null}` (pydantic's JSON writes
  infinity and NaN as `null`); only a route without one, returning the raw value, fails with a 500. The real risk is
  therefore silent: a value saved and used that reads back as `null`.

Inventory on the real app (`iter_route_contexts`, 177 API routes, 67 with a body): **six** floats reachable from a
request. Five signal parameters (`epsilon`, `relative_epsilon`, `threshold`) were already pydantic's `FiniteFloat`. The
sixth, `PluginSettingWriteItem.value` (`str | int | float | bool | None`, `PATCH /settings/plugins/bulk`), accepted
infinity in the schema, but its service refused it before saving (`validate_value()`, `math.isfinite`). There was no
float query or path parameter, and `Decimal`, used for money, refuses both by default.

## Options Considered

1. **`allow_inf_nan=False` in `StrictModel`** (`backend/app/schemas/common.py`). Out of proportion: the same base backs
   hundreds of response models and internal payloads (AI Export, risk), where a computed NaN would turn into an
   exception inside a service. It changes much and gains nothing on the requests.
2. **Field by field, plus a generic guard** over every route.
3. Keep the plugin field unchanged and list it in the guard as a justified exception («checked by `validate_value`»).

## Decision

Options 2 and the fix of option 3's field (the coordinator, 17/10):

- `PluginSettingPlainValue = str | int | Annotated[float, AllowInfNan(False)] | bool`. It is one line in X's file; X
  reviewed it.
- **The guard** `./dev.py test services request-float-inputs`:
  - it walks every route with `fastapi.routing.iter_route_contexts` and the effective dependant: bodies, nested
    models, query, path, header and cookie parameters, PEP 695 aliases;
  - it judges each float with a `TypeAdapter` built on the whole annotation, the field's metadata and the model's
    `allow_inf_nan`. Any of `inf`, `-inf`, `NaN`, `1E+400` passing fails the guard, named by route, model and field;
  - barriers keep it from passing empty: at least 150 routes and 60 bodies, the five signal floats found, and no
    field the walk cannot read.

## Consequences

- The OpenAPI document did not change (`AllowInfNan` adds nothing to the JSON schema): no client regeneration.
- The real route, in process, answers **422** to `Infinity`, `-Infinity`, `NaN` and `1E+400`, without echoing the
  input: the plugin-settings router drops it.
- Found on the way: FastAPI's stock 422 handler echoed each error's input, so a non-finite value on a field that was
  already finite answered **500**: the 422 could not be rendered. A's global handler (A7b-2,
  `backend/app/api/validation_errors.py`) drops the input and cures it.
- Left for their owners (backlog H-34): free-form JSON fields (`dict[str, Any]`, `JsonValue`) accept infinity
  **inside**. These are X's `provider_params` (twice) and J's `RiskAnalyticRequest.parameters`;
  `SignalRequest.params` is already guarded by `ensure_json_safe()`. And X-R43: a 401-digit integer makes
  `math.isfinite()` raise `OverflowError`, which gives a 500 on the plugin-settings write.

## Links

- [[concepts/fastapi-0141-routing-and-validation-gotchas]]: the walk that sees included routers, `null` for infinity,
  the 500 of the echoed input.
- [[problems/response-validation-error-wrote-the-response-to-the-log]].

## Source files

| Role | Path |
|------|------|
| The plugin setting's finite float | `backend/app/schemas/plugin_settings.py` |
| The signal floats, already `FiniteFloat` | `backend/app/schemas/signals.py` |
| The service's own check (`validate_value`) | `backend/app/services/plugin_settings/fields.py` |
| The guard | `backend/test_scripts/test_services/test_request_float_inputs.py` |
| «Numbers in Requests» | `mkdocs_src/docs/developer/architecture/security.md` |
| A's 422 without the input | `backend/app/api/validation_errors.py` |
| Lot H-32: inventory, measurements, decisions | `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md` |
