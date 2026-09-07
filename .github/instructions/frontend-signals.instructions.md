---
applyTo: "frontend/src/lib/charts/signals/**"
---

# Chart Signal Architecture

## Technical Indicators: Backend Plugins

Technical indicators are Python `SignalPlugin` implementations in
`backend/app/services/signal_plugins/`. `SignalPluginRegistry` discovers them,
the backend catalog describes their parameters and outputs, and `SignalService`
calculates them.

Frontend code handles technical indicators generically:

- `catalogMapper.ts` and `schemaMapper.ts` map backend catalog metadata.
- `requestBuilder.ts` creates backend requests.
- `resultMapper.ts` and `backendRenderer.ts` map canonical backend results into chart series.
- `backendTypes.ts` contains transport schemas and types.

Never add a TypeScript technical-indicator class or calculation. Indicator-specific
math, parameters, warm-up, outputs, axes, levels, and regions belong to the backend
plugin.

## Frontend-Local Signals

`ChartSignal` subclasses and `registry.ts` are only for frontend-local comparisons
and synthetic benchmarks:

| Category   | Type               | Class                   |
| ---------- | ------------------ | ----------------------- |
| Comparison | `fx-pair`          | `FxPairSignal`          |
| Comparison | `asset-comparison` | `AssetComparisonSignal` |
| Benchmark  | `linear`           | `LinearSignal`          |
| Benchmark  | `compound`         | `CompoundSignal`        |
| Benchmark  | `sine`             | `SineSignal`            |

`getLocalSignalDefinitions()` supplies these definitions for merging with the backend
catalog. `getRegisteredSignalTypes()`, `createSignal()`, and `signalFromConfig()` are
local-only registry/factory APIs.

`MeasureSignal` is separate. It is exported for `MeasurePanel`, but it is not in
`SIGNAL_REGISTRY` or signal selectors.

## Adding a Technical Signal

1. Follow `mkdocs_src/docs/developer/architecture/patterns/signal_plugin_guide.md`.
2. Implement the Python plugin under `backend/app/services/signal_plugins/` using
   the contract in `base.py`; shared planning/execution belongs in
   `backend/app/services/signal_service.py`.
3. Add backend tests for discovery, contract validation, computation, warm-up, and
   output metadata.
4. Add the plugin-declared frontend translation keys and MkDocs indicator docs when
   applicable.
5. Change frontend generic catalog/request/result/rendering code only when the
   canonical backend contract itself expands. Never duplicate the calculation in
   TypeScript.

## Adding a Local Comparison or Benchmark

1. Create a `ChartSignal` subclass with local metadata, parameter descriptors, and
   rendering logic.
2. Register its constructor in `SIGNAL_REGISTRY`.
3. Add its local display/description keys to `LOCAL_SIGNAL_I18N_KEYS`.
4. Export the class from `index.ts`.
5. Add focused registry, serialization, and rendering tests.
