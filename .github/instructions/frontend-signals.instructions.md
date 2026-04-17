---
applyTo: "frontend/src/lib/charts/signals/**"
---

# Chart Signal Library

## Architecture

All signals extend `ChartSignal` (abstract base in `ChartSignal.ts`) and are registered in `registry.ts`. The UI auto-discovers signals via `getRegisteredSignalTypes()`.

### Base Class

The abstract base class is `ChartSignal` in `frontend/src/lib/charts/signals/ChartSignal.ts`. Read that file for the full contract (static fields, abstract methods, `SignalParamDescriptor` interface, marker types, style types).

Key static fields: `signalType`, `displayName`, `icon`, `category`, `paramDescriptors`, `docsPath`.
Key methods: `render()` (or `renderMulti()` for composite signals like MACD).

### Registration

Signals are registered in `frontend/src/lib/charts/signals/registry.ts` — add an entry to `SIGNAL_REGISTRY` map. The UI auto-discovers via `getRegisteredSignalTypes()`.

## Signals

### Technical Indicators (`category: 'indicator'`)

| Signal | File | Type | Axis | Params |
|--------|------|------|------|--------|
| **EMA** | `EmaSignal.ts` | IIR 1st order | Primary | `period` (days) |
| **RSI** | `RsiSignal.ts` | Momentum oscillator | Secondary (0-100) | `period` (days) |
| **MACD** | `MacdSignal.ts` | Composite (3 lines) | Tertiary | `fastPeriod`, `slowPeriod`, `signalPeriod` |
| **Bollinger** | `BollingerSignal.ts` | Confidence band | Primary | `period`, `multiplier` |

### Data Comparison (`category: 'comparison'`)

| Signal | File | Axis | Params |
|--------|------|------|--------|
| **FX Pair** | `FxPairSignal.ts` | Primary | `pairKey` (dynamic options from configured pairs) |
| **Asset Comparison** | `AssetComparisonSignal.ts` | Primary | `assetId` (dynamic options from configured assets) |

### Synthetic Benchmarks (`category: 'benchmark'`)

| Signal | File | Axis | Params |
|--------|------|------|--------|
| **Linear** | `LinearSignal.ts` | Primary | `rate` (%/yr) |
| **Compound** | `CompoundSignal.ts` | Primary | `rate` (%/yr) |
| **Sine** | `SineSignal.ts` | Primary | `amplitude`, `period` (test/demo) |

### Measurement (`category: 'measure'`)

| Signal | File | Axis | Params |
|--------|------|------|--------|
| **Measure** | `MeasureSignal.ts` | Primary | Two click points → Δabs, Δ%, days |

## Design Principles

- All signals compute in **O(N)** iteratively (no full-array passes)
- `paramDescriptors` drive the UI: ChartSettingsModal renders controls dynamically
- `dynamicOptionsKey` in params enables runtime-resolved dropdowns (e.g. configured FX pairs)
- Colors are chosen to maximize perceptual hue distance from existing signals
- MACD uses `renderMulti()` for composite output (MACD line + signal line + histogram)

## Adding a New Signal

1. Create `frontend/src/lib/charts/signals/MySignal.ts`
2. Extend `ChartSignal` (read `ChartSignal.ts` for the full interface)
3. Set static fields: `signalType`, `displayName`, `icon`, `category`, `paramDescriptors`
4. Implement `render()` (or `renderMulti()` for composite signals)
5. Add to `SIGNAL_REGISTRY` in `registry.ts`
6. Done — UI auto-discovers via `getRegisteredSignalTypes()`

