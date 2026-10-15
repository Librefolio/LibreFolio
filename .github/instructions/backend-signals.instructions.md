---
applyTo: "backend/app/services/signal_plugins/**,backend/app/services/signal_*.py,backend/app/services/series_preparation.py"
---

# Technical Signals (backend)

## Architecture

- **Plugins**: one folder per indicator, `services/signal_plugins/<code>/` (`__init__.py` with the docstring only,
  `plugin.py` with the code, `i18n/` with its `signals.<ns>.*` texts), extending `SignalPlugin` (`signal_plugins/base.py`,
  which discovery skips) and registered with `@register_plugin(SignalPluginRegistry)` (`services/signals/registry.py`; the decorator is in
  `services/provider_registry.py`).
  Import and patch from `….signal_plugins.<code>.plugin`. Keys several indicators share (`signals.reference.*`,
  `signals.riskRollingReturn.*`) stay in the `charts` subsystem of the catalogue.
- **Runtime**: `signal_service.py` (planning, execution, annotations, validation), `signal_runtime.py`,
  `signal_annotations.py`, `signal_series_preparation.py` (quote days, prepared series). `series_preparation.py` is
  shared with the risk engine.
- **API**: the Asset and FX catalogs and executions are served by `api/v1/assets/prices.py` and `api/v1/fx/currencies.py`. The frontend
  renders the declaration with no indicator-specific code (`frontend-signals.instructions.md`).

## Rules

- A plugin is a pure calculator: no database access, provider call, currency conversion or HTTP inside it.
- The declaration is the contract: codes, versions, i18n keys, `params_model` (`extra="forbid"`), input requirements,
  output specs, compatible domains and AI Export temporal rules are what the catalog, the UI and AI Export read.
- Never compact missing fields or dates. The status (`ok`, `partial`, `unavailable`, `failed`) comes from the service's
  status matrix; a plugin returns a `SignalComputation` or raises `SignalUnavailableError`.
- Periods count sessions by default (`computes_on_quote_days = True`); calendar days only for calendar spans.
- Bump `implementation_version` whenever the values change.
- AI Export never branches on a signal code: temporal classes come from the plugin's `ai_export_temporal_rules`.
- The indicator's own formula stays in the plugin. Common financial math (returns, annualization, FX conversion,
  valuation) comes from its one home, `services/financial_math/` and the map in `backend.instructions.md`.

## Adding a Signal

Read the skill `signal-plugin` and the guide
`mkdocs_src/docs/developer/architecture/patterns/signal_plugin_guide.md` ("Adding a Plugin"). The registry pins
(code sets, versions, parameter units) live in `backend/test_scripts/test_services/test_signal_plugin_matrix.py`.

## Testing

`./dev.py test services signal-plugin-matrix`, `./dev.py test services signal-service`,
`./dev.py test api signal-catalogs`; `./dev.py api sync` after a catalog change.
