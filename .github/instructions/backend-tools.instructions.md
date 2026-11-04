---
applyTo: "backend/app/services/tools/**,backend/app/services/tool_plugins/**"
---

# Tool Platform (backend)

## Architecture

- **Plugins**: thin wrappers, one folder per tool, `services/tool_plugins/<name>/` (`__init__.py` with the docstring only,
  `plugin.py` with the code, `i18n/` with its `name_i18n_key`/`description_i18n_key` texts), extending `ToolPlugin`
  (`services/tools/base.py`) and registered with `@register_plugin(ToolPluginRegistry)`. The registry is a specialization
  in `services/tools/registry.py`: like every family's registry, it lives in its runtime package, while
  `provider_registry.py` holds the shared bases and decorators.
- **Runtime**: `services/tools/` holds the catalog, the schema export, the executor and the worker processes; each
  plugin's numerical engine lives in its own domain package (the PAC planner in `services/pac_allocator/`).
- **API**: `api/v1/tools.py` (catalog, bulk compute, diagnostics). Contracts live in `schemas/tools.py` and the plugin's
  schema module; the typed client and codecs come from `./dev.py api sync`.

## Rules

- Inputs and outputs are real Pydantic models with `extra="forbid"` at every level; `operation` is required.
- A plugin declares a non-empty tuple of `ToolService`, each with its stable `tool_code`, metadata, policies, UI
  descriptor, documentation, `input_type` and `output_type`.
- `compute()` is synchronous and isolated: no principal, database session, provider client or request inside it. Every
  datum is collected through authorized domain APIs before the item is submitted.
- Nothing computes, fetches or self-tests at import or registration; invalid declarations are quarantined.
- Each compute item is its own job; children and threads never outlive it, and cleanup covers success, failure,
  timeout, disconnect and shutdown.
- Execution limits and crashes are platform errors, never a fabricated infeasibility or a zero-valued result; timings
  belong to the platform envelope, not to the numerical result.
- Financial math stays in the backend. Common calculations come from their one home, `services/financial_math/` and
  the map in `backend.instructions.md`; a Tool engine never keeps a local copy.

## Adding a Tool

Read the skill `tool-plugin` and `mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md`.

## Testing

`./dev.py test services tools-registry`, `./dev.py test api tools`; `services tools-lifecycle` owns process groups and
runs as an exclusive unit.
