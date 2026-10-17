# 03 — Semantic & dynamic color logic (TS / Svelte script)

> Snapshot: `dev_release2` @ `6d0b1266c` (v1.2), 2026-10-14. Read-only. Paths relative to `frontend/src/`.
> Coverage: targeted greps for `Record<…, string>` color maps, sign ternaries, color pickers and core helpers. **Not exhaustive**: not every `class:` directive / `style=` binding was checked; `features/onboarding`, `ai-export`, `changelog`, `update-check` only partially. Caller counts = files referencing the helper (tests excluded).
> ⚠️ In dark mode many of the `dark:text-*` classes listed here are overridden by `app.css` (see report 01 §6.0) — the *rendered* dark color may differ from the one written.

## 1. Inventory of color-deciding functions and maps

| # | Name | file:line | Input | Output (light / dark) | Callers |
|---|---|---|---|---|---|
| 1 | `getIndexColor()` | `lib/utils/colors.ts:36` | index + start hue (default 140) | Inline HSL. Golden-ratio hue step; S 35–55%. Light bg L92 / text L30; dark bg L25 / text L82. Also `vivid` (75%/50%) and `vividLight` (60%/80%) for row tints. | base generator for brokers, priority badges, `getStringColor` |
| 2 | `getProviderColor()` | `colors.ts:76` | FX provider code | `hsla`. Fixed hues ECB 220, FED 30, BOE 150, SNB 340, MANUAL 0 (red); others hashed. Light bg 12% alpha + 30% border; dark L60 15% alpha + L70 border. | `ui/select/FxProviderSelect.svelte` (7 refs) |
| 3 | `getPriorityBadgeStyle()` | `colors.ts:113` | priority index | CSS vars `--badge-bg/-text/-dark-*` from `getIndexColor(i,140)` | provider priority badges |
| 4 | `getStringColor()` / `getStringBadgeStyle()` | `colors.ts` ~208/218 | any string (djb2 hash) | same ColorSet as #1, start hue 200 | `files/FilesTable.svelte` and others |
| 5 | `hslToHex` / `hexToHsl` | `colors.ts:123`, `:153` | conversion | — | color pickers, palette shading |
| 6 | `getBrokerColor()` | `lib/utils/broker/brokerColors.ts:36` | broker id + broker list | `getIndexColor(position in id-sorted list, 200)`; unknown id → id as index | ~20 files: `TransactionsTable`, `BrokerBadge`, `UnifiedLotsTable`, `LotGanttChart`/helpers, `LotWacPriceChart`, `LotCustodyModal`, `PositionsPanel`, `ExposureTable`, `ContributionTable`, `GrowthChart`, dashboard, brokers/[id], transactions… |
| 7 | `computeSignHint()` | `lib/utils/transactions/signHintColor.ts:26` | number + `SignRule` | `{ok,bad}` only; color in CSS `ui/display/CompactCashCell.svelte:200-205` (emerald-500 / red-500 border @70%, no dark rule) | `CompactCashCell:130`, `TransactionFormModal:856-857` |
| 8 | `assetTypeBadgeClass()` / `BADGE_CLASS_MAP` | `lib/utils/assetTypes.ts:109-138` | 21 asset types | `bg-X-100 text-X-700` / `dark:bg-X-900/30 dark:text-X-400`. STOCK blue, ETF emerald, BOND amber, CRYPTO purple, FUND cyan, HOLD pink, CROWDFUND orange, COMMODITY yellow, REAL_ESTATE teal, INDEX indigo, OTHER slate, LIQUIDITY green, ETF_MONETARY sky; ETF_* inherit parent; unknown gray (`:135`) | `AssetTable`, `AssetCard` |
| 9 | `PROVIDER_COLORS` / `DEFAULT_PROVIDER_COLOR` | `lib/utils/providerHelpers.ts:22-28` | FX provider | ECB blue, FRANKFURTER indigo, FIXED_RATE emerald, MANUAL **amber**, default gray; `-100/-700`, `-900/30`/`-400` | `SchedulerLogModal`, `FxSyncModal`, HTML cell builders |
| 10 | `STATUS_COLORS` | `lib/utils/sync/syncHelpers.ts:97` | `SyncStatus` | ok emerald-500, partial amber-500, failed red-500, skipped gray-400 — **no dark variants** | `SyncResultRow`, `PageSyncModal`, `AssetSyncModal`, `FxSyncModal` |
| 11 | `BADGE` / `NOTICE` | `lib/features/tools/pac-allocator/planner/ui.ts:80-94` | neutral/success/info/warning/danger | badges `-100/-800`, dark `-900/40`/`-200`; notices `-50` + `-200` border, dark `-950/30`. success emerald, info sky, warning amber, danger red, neutral gray | PAC planner only (`OperationalPlan.svelte:39`, `FUNDING_BADGES`) |
| 12 | `BAR_CLASS` / `TOTAL_CLASS` | `features/tools/pac-allocator/planner/steps/TargetsStep.svelte:29-30` | balanced/excess/missing/unknown | bar `bg-libre-green`, `bg-red-400`, `bg-amber-400`, gray; text green-600/dark green-400, red-500, amber-500, gray — **partial dark** | local |
| 13 | `variantStyles` (toast) | `lib/components/ui/feedback/ToastContainer.svelte:16` | success/error/warning/info | solid `bg-emerald-600`, `bg-red-600`, `bg-amber-500`, `bg-blue-500` + white text, same both themes | global |
| 14 | `statusClass` | `components/transactions/import/ReportSetCard.svelte:308` | loading/complete/incomplete/error | gray/slate, **green**-100/800, amber-100/800, red-100/**700**; dark present | local |
| 15 | `badgeTone` | `components/transactions/import/AssetGroupStep.svelte:229` | isin/symbol/name | sky / violet / slate + border; dark present | local |
| 16 | `STYLE` | `components/files/FileSetBadges.svelte:17` | combined/stale/usedInCombined/set/incomplete | indigo/amber/gray/emerald/red `-100/-800`; dark present | local |
| 17 | `VARIANT_CLASSES` | `components/risk/AssetChip.svelte:42` | default/warning/excluded | gray / amber+border / dashed gray; dark present | risk panels |
| 18 | `getSeverityStyles()` | `components/ui/feedback/DataQualityBanner.svelte:80-91` | error/warning/info | **error and warning both amber**; info sky; dark present; only icon differs (`:93-97`) | dashboard etc. |
| 19 | `ROLE_COLORS` / `resolveSignalColor()` | `lib/charts/signals/signalVisualStyle.ts:3-13` | `SignalColorRole` (backend enum, `api/generated.ts:13420`) | secondary `#f59e0b`, positive `#16a34a`, negative `#dc2626`, neutral `#64748b`, accent `#8b5cf6`; primary = user color. **Same both themes** | chart signals |
| 20 | `DEFAULT_SIGNAL_COLORS` | `lib/charts/signals/ChartSignal.ts:194` | — | `#3b82f6 #f59e0b #8b5cf6 #ec4899 #06b6d4 #84cc16`; `MeasureSignal.ts:44` `#f97316`; `registry.ts:37+` picks the hue farthest from those in use | signals |
| 21 | meta theme-color | `lib/stores/app/themeStore.ts:59` | theme | `#1a4031` / `#156534` | — |
| 22 | `colorByBaseline` | `lib/stores/chartSettingsStore.svelte.ts:39,63` | bool (default true) | line green above baseline / red below (colors in chart code, see report 04) | — |

No central map transaction type (BUY/SELL/DIVIDEND/FEE…) → color found (`transactionTypeStore.ts` has none; any type coloring is inline in templates — to verify).

## 2. Semantic families and divergences

**Positive / gain**
- `emerald-600 / dark:emerald-400`: `FxTable:127`, `FxCard:224`, `FxPriceSummary:46`, `MeasurePanel:342,564,577`, `AssetTable:121`, `AssetPriceSummary:117`, `AssetCard:230,236`, `BrokerCard:156`, `app.css` price flash.
- `green-600 / dark:green-400`: `KpiSection:226,297,352,380`, `ExposureTable:145`, `ContributionTable:186`, `OtherPeriodEffectsTable:91`, `TargetsStep:30`.
- bars `bg-green-500 / dark:bg-green-400`: `KpiSection:223,264`.
- hex `#16a34a` (green-600): `signalVisualStyle.ts:5`; border emerald-500@70%: `CompactCashCell:201`.
- **Divergence: dashboard = green; assets/FX/brokers/charts = emerald.**

**Negative / loss**
- mostly `red-500 / dark:red-400`; `KpiSection:226`, `BrokerCard:156` use red-600; `KpiSection:223,264` bars `bg-red-400 / dark:bg-red-500` (inverted vs text); hex `#dc2626` in signals; `TargetsStep` red-500 / bg-red-400 no dark.

**Neutral / zero**
- `gray-500 / dark:gray-400`: `UnifiedLotsTable:205,214`, `ExposureTable:136`, `ContributionTable:169` — these ternaries treat <0 red and **everything else (incl. positive) gray**.
- hex `#64748b` (slate-500) in signals; elsewhere a gray/slate mix.

**Inverted meaning** — `L2Diversification.svelte:312`: >0 red, else emerald (higher = worse). Deliberate, undocumented.

**Correlation** — `CorrelationPairsList:64,74`, `RiskAnalysisPanel:682`: negative red, positive blue.

**Success / ok** — emerald: `STATUS_COLORS`, `BADGE/NOTICE.success`, toast, `FileSetBadges.set`; green: `ReportSetCard.complete`, `TargetsStep` (+ `bg-libre-green` bar).

**Warning** — amber consistently, but shades vary: 500 text, 400 bars, badge 100/800 vs 50/700.

**Error / danger** — red-500 text (sync), red-600 toast; badges red-100/800 vs red-100/700; **DataQualityBanner error = amber**.

**Info** — sky (`BADGE`, `NOTICE`, `DataQualityBanner`) vs blue-500 (toast).

**Pending/loading** gray/slate; **disabled/excluded/skipped** gray-400.

**Deposit/transfer** (PAC only): deposit success (emerald), transfer info (sky).

**Missing as maps:** buy, sell, dividend, fee, withdrawal, FX transaction types.

## 3. Duplicated logic

- **Gain/loss ternary** inlined ≥20 times in ~13 files, in two families; no shared `signClass()`.
- **Status/severity badge palettes** defined independently 7× (`BADGE`, `statusClass`, `STYLE`, `AssetChip`, `DataQualityBanner`, `STATUS_COLORS`, `ToastContainer`) with different shades / green vs emerald.
- **FX provider colors twice, different hues**: `providerHelpers.ts:22` (Tailwind: ECB blue, MANUAL amber) vs `colors.ts:78` (HSL: ECB blue, MANUAL red, FED orange). **MANUAL amber vs red.**
- **Hex→hue** twice: `colors.ts:153` (`hexToHsl`) and `charts/signals/registry.ts:38` (`hexToHue`).
- Asset-type badges already consolidated once (`assetTypes.ts:104-107` comment notes past drift).

## 4. Dark-mode gaps

- `STATUS_COLORS` (`syncHelpers.ts:97`): none.
- `TargetsStep.svelte:29-30`: excess/missing none.
- `RiskAnalysisPanel:682`: `bg-red-500` / `bg-blue-500` none.
- `CompactCashCell.svelte:200-205`: sign borders none (hover/disabled have).
- `ToastContainer`: solid fills same both themes (maybe intentional).
- Signal hex (`ROLE_COLORS`, `DEFAULT_SIGNAL_COLORS`): no theme lookup.
- Fully covered: `getIndexColor`/`getProviderColor` families, `BADGE_CLASS_MAP`, `PROVIDER_COLORS`, `BADGE/NOTICE`, `FileSetBadges`, `ReportSetCard`, `AssetChip`, `AssetGroupStep`, `DataQualityBanner`.

## 5. User-configurable colors

- Only native `<input type="color">` for chart signal lines: `components/charts/SignalStyleEditor.svelte:72`, `ChartSignalsSection.svelte:834` (MACD).
  - Stored as hex in `SignalStyle.color` (`ChartSignal.ts:153`), persistent overrides (l.382; storage location not confirmed).
  - Defaults `DEFAULT_SIGNAL_COLORS` by hue distance; MeasureSignal `#f97316`.
  - `colorRole ≠ primary` replaces user color with fixed `ROLE_COLORS`.
  - No validation beyond native input; no dark-mode adaptation.
- Brokers, assets, tags are **not** user-colored: derived from list position/hash. **Broker color depends on position in the id-sorted list** (`brokerColors.ts:37-40`) → deleting a lower-id broker recolors the others.
- `colorByBaseline` toggle (`chartSettingsStore.svelte.ts:39`, validated `:163`).

## 6. Tests that pin colors (will need updating)

- `lib/utils/__tests__/colors.test.ts`: palette slot count (`:68`), light/dark length parity (`:72`), hex↔HSL round-trip ±1 (`:88-96`), exact `hexToHsl('#abc')` (`:132`), primaries (`:167-170`); palettes read from source via `sourcePalettes`.
- `__tests__/sourcePalettes.ts/.test.ts`: parse `const NAME = ['#rrggbb', …]` from `.svelte` by name; fail on rename, duplicate declaration, non-literal array, non 6-digit hex. Used by `allocationHierarchy.test.ts`, `allocationRings.test.ts`, `AllocationHistoryChart.test.ts`. **Moving palettes to CSS tokens / oklch breaks these readers.**
- `signHintColor.test.ts`: logic only (`:5-38`).
- `assetTypeTables.test.ts:255`: requires `BADGE_CLASS_MAP` name/shape/file and an entry per asset type.
- `SchedulerLogModal.test.ts:45`: mocks `PROVIDER_COLORS`.
- Component/E2E class assertions (e.g. `sign-ok`) not grepped.

## 7. Open questions for the designer

1. Gain/loss: green or emerald? Shade for text vs bars? Loss red-500 or red-600?
2. Should error and warning look the same (amber) in `DataQualityBanner`?
3. Success: emerald everywhere or brand `libre-green`?
4. MANUAL provider color (amber vs red) — merge the two FX-provider schemes?
5. Introduce colors per transaction type (none centrally today)?
6. Dark-theme variants for signal hex colors; contrast check on user-picked colors?
7. Red/blue correlation and inverted `L2Diversification` coloring: accepted exceptions to document?
8. Algorithmic (golden-ratio HSL) palettes for brokers/tags vs fixed token set? Stable broker color identity?
9. Solid toasts in dark mode?
10. One badge pattern (100/700 vs 100/800; dark 900/30 vs 900/40, -400 vs -200 text)?
