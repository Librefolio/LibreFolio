# Task: FX Implied Rate & Market Spread — Frontend-Only

**Parent plan**: [`plan-R2-SP-C-BulkModalSuggestUX`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BulkModalSuggestUX.prompt.md)
**Depends on**: SP-C walktest complete, BugfixRound1 (BUG-C7 suggest redesign)
**Triggered by**: BUG-C12 fix revealing FX_CONVERSION suggestions in banner

## Context

After fixing BUG-C12 (promote-suggest $effect sent unsigned amounts), the banner correctly shows FX_CONVERSION suggestions (e.g. WITHDRAWAL EUR ↔ DEPOSIT USD, same broker, different currency). The user wants to enrich the banner and FormModal with:
- **Implied rate**: derived from the two TX amounts (`|amountTo| / |amountFrom|`)
- **Market rate**: from the FX system (via `POST /fx/currencies/convert`)
- **Spread**: difference between implied and market (broker markup)

Architecture: uniform frontend approach using `lookupFxRate()` in `fxStoreRegistry.ts`. Covers all scenarios (edit+edit, new+new, new+edit, FormModal) with a single pattern. No backend modifications needed.

### Why not backend-driven?

We evaluated having `promote-suggest` return `fx_info` in its response. Rejected because:
- It only covers **edit+edit** (both TX from DB, sent to promote-suggest)
- **new+new** TX (unsaved creates matched locally) never pass through promote-suggest
- **FormModal** is completely unrelated to suggest
- `lookupFxRate()` is needed anyway for FormModal and new+new
- One uniform path = less code, less bugs, less tests
- Promote-suggest stays lightweight (no FX lookups adding latency)

## Key files to read first

- `frontend/src/lib/stores/fxStoreRegistry.ts` — FX store registry (TimeSeriesStore cache, `getFxStoreByPair`, `apiResultToFxDataPoint`)
- `frontend/src/lib/stores/TimeSeriesStore.ts` — Generic time-series cache (`.get(date)`, `.merge()`, `.getMissingIntervals()`)
- `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` — BulkModal (banner suggest, `SuggestEntry`, `bannerSuggestions` $derived)
- `frontend/src/lib/components/transactions/TransactionFormModal.svelte` — FormModal (dual-form FX layout, `pairLayout === 'fx'`)
- `frontend/src/lib/utils/currencyFormat.ts` — `formatCurrencyCodeHtml()`, `formatCurrencyAmountHtml()`
- `frontend/src/lib/components/ui/Tooltip.svelte` — Tooltip component (html prop, fixed positioning)
- `frontend/src/lib/api/generated.ts` — Zodios API client (`convert_currency_bulk_api_v1_fx_currencies_convert_post`)
- `mkdocs_src/docs/financial-theory/instruments/transaction-types/fx-conversion.en.md` — FX Conversion docs
- `mkdocs_src/docs/developer/architecture/database/brokers_transactions.md` — DB architecture docs

## Architecture Overview

### FX Store Current Flow (pages)

```
Page → store.getMissingIntervals(start, end) → gaps?
  → YES: fetch POST /fx/currencies/convert → store.merge(results) → read from cache
  → NO:  read from cache directly
```

The store is a **passive cache** — never auto-fetches. Fetch responsibility is on the caller.

### New: `lookupFxRate()` — Self-Fetching Spot Lookup

```
lookupFxRate(base, quote, date)
  → getFxStoreByPair(base, quote).get(date) → cache hit? return immediately
  → cache miss: fetch POST /fx/currencies/convert (amount=1, single date)
  → merge into TimeSeriesStore → return FxDataPoint
  → error (404 / no pair) → return null
```

Caches in TimeSeriesStore = subsequent calls for same pair+date are instant.

### Banner Suggest — Reactive FX Enrichment

```
bannerSuggestions ($derived) → [{tempIdA, tempIdB, targetType}]
  ↓
$effect watches bannerSuggestions:
  for each FX_CONVERSION entry:
    read ops[].fields → compute impliedRate locally
    check fxMarketCache Map → 'pending' | FxDataPoint | null
    if not in cache → launch lookupFxRate() → on return (with generation guard) → update Map
  ↓
Template reads:
  - impliedRate: from ops[].fields (always available, synchronous)
  - marketRate: from fxMarketCache (reactive $state Map)
    - 'pending' → show only implied
    - FxDataPoint → show implied + market + spread + stale
    - null → show implied + "market not available"
```

### FormModal FX — Same Pattern, Simpler

```
$effect watches [draft.cash, dualTo.cash, draft.date]:
  if pairLayout === 'fx' && both have cash with different currencies:
    compute impliedRate
    launch lookupFxRate() → update local $state fxMarketPoint
  ↓
Template:
  <Tooltip> with implied + market + spread (same rendering as banner)
```

## Steps

### Step 1: `lookupFxRate()` in fxStoreRegistry.ts

**File**: `frontend/src/lib/stores/fxStoreRegistry.ts`

Add two new exports:

```typescript
/**
 * Synchronous cache-only lookup. Returns the FxDataPoint if already cached,
 * undefined otherwise. Use for instant reads without triggering fetches.
 */
export function lookupFxRateSync(base: string, quote: string, date: string): FxDataPoint | undefined {
    const slug = createPairSlug(base, quote);
    const store = fxStores.get(slug);
    if (!store) return undefined;
    const point = store.get(date);
    if (!point) return undefined;
    // If the stored rate is in canonical direction (alphabetical), we may need to invert
    const {base: canonBase} = parsePairSlug(slug);
    if (canonBase === base.toUpperCase()) return point;
    // Invert: stored is canonBase→canonQuote, we need base→quote where base > quote alphabetically
    return {...point, rate: point.rate !== 0 ? 1 / point.rate : 0};
}

/**
 * Async lookup with auto-fetch. Checks cache first, fetches from backend if miss.
 * Result is merged into TimeSeriesStore for future cache hits.
 * Returns null if the pair is not configured (404) or fetch fails.
 */
export async function lookupFxRate(base: string, quote: string, date: string): Promise<FxDataPoint | null> {
    // Check cache first
    const cached = lookupFxRateSync(base, quote, date);
    if (cached) return cached;
    
    // Fetch from backend
    const slug = createPairSlug(base, quote);
    const {base: canonBase, quote: canonQuote} = parsePairSlug(slug);
    try {
        const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post([{
            from_amount: {code: canonBase, amount: 1},
            to: canonQuote,
            date_range: {start: date, end: date},
        }]);
        const results = (response as any)?.results || [];
        if (results.length === 0) return null;
        const point = apiResultToFxDataPoint(results[0]);
        // Merge into cache
        const store = getFxStore(slug);
        store.merge([point]);
        // Return in requested direction
        if (canonBase === base.toUpperCase()) return point;
        return {...point, rate: point.rate !== 0 ? 1 / point.rate : 0};
    } catch {
        return null;
    }
}
```

Import `zodiosApi` from `$lib/api/client` (or wherever the zodios instance is exported).

### Step 2: `computeFxConversionInfo()` in fxConversionHelper.ts

**File**: `frontend/src/lib/utils/fxConversionHelper.ts` (new)

```typescript
/**
 * FX Conversion Helper — compute implied rate, spread, and tooltip data
 * for FX_CONVERSION transaction pairs.
 */

import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';

export interface FxConversionInfo {
    impliedRate: number;
    /** Currency being converted FROM */
    base: string;
    /** Currency being converted TO */
    quote: string;
}

export interface FxSpreadInfo {
    /** implied - market */
    absolute: number;
    /** (implied - market) / market * 100 */
    percent: number;
}

export interface FxTooltipData {
    impliedRate: number;
    base: string;
    quote: string;
    marketRate: number | null;
    marketDate: string | null;
    staleDays: number | null;
    spread: FxSpreadInfo | null;
}

/**
 * Compute implied FX rate from two transaction amounts.
 * 
 * @param amountFrom - Amount leaving (should be negative in DB, pass absolute value)
 * @param currencyFrom - Currency of the "from" side
 * @param amountTo - Amount arriving (should be positive in DB, pass absolute value)
 * @param currencyTo - Currency of the "to" side
 * @returns FxConversionInfo or null if amounts are invalid (zero/missing)
 */
export function computeFxConversionInfo(
    amountFrom: number,
    currencyFrom: string,
    amountTo: number,
    currencyTo: string,
): FxConversionInfo | null {
    const absFrom = Math.abs(amountFrom);
    const absTo = Math.abs(amountTo);
    if (absFrom === 0 || absTo === 0) return null;
    if (currencyFrom === currencyTo) return null;
    return {
        impliedRate: absTo / absFrom,
        base: currencyFrom,
        quote: currencyTo,
    };
}

/**
 * Compute spread between implied and market rate.
 */
export function computeSpread(impliedRate: number, marketRate: number): FxSpreadInfo {
    const absolute = impliedRate - marketRate;
    const percent = marketRate !== 0 ? (absolute / marketRate) * 100 : 0;
    return {absolute, percent};
}

/**
 * Build structured tooltip data from FxDataPoint (or lack thereof).
 * Handles 3 cases: fresh rate, stale rate, no rate available.
 *
 * @param info - Implied rate info from computeFxConversionInfo
 * @param fxPoint - Result from lookupFxRate: FxDataPoint (has rate), null (pair not configured), undefined (pending/not fetched)
 */
export function buildFxTooltipData(
    info: FxConversionInfo,
    fxPoint: FxDataPoint | null | undefined,
): FxTooltipData {
    if (fxPoint === null || fxPoint === undefined) {
        return {
            impliedRate: info.impliedRate,
            base: info.base,
            quote: info.quote,
            marketRate: null,
            marketDate: null,
            staleDays: null,
            spread: null,
        };
    }
    const marketRate = fxPoint.rate;
    const staleDays = fxPoint.backwardFillInfo?.daysBack ?? null;
    const marketDate = fxPoint.backwardFillInfo?.actualRateDate ?? null;
    const spread = marketRate !== 0 ? computeSpread(info.impliedRate, marketRate) : null;
    return {
        impliedRate: info.impliedRate,
        base: info.base,
        quote: info.quote,
        marketRate,
        marketDate,
        staleDays,
        spread,
    };
}
```

### Step 3: Reduce `SuggestEntry` in TransactionBulkModal.svelte

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Change `SuggestEntry` type from:
```typescript
type SuggestEntry = {tempIdA: string; tempIdB: string; labelA: string; labelB: string; targetLabel: string; typeA: string; typeB: string; targetType: string; dateA: string; dateB: string; deltaDays: number; isDB?: boolean; dbCandidateId?: number};
```
To:
```typescript
type SuggestEntry = {tempIdA: string; tempIdB: string; targetType: string};
```

Update `localSuggestions` and `bannerSuggestions` to only produce these 3 fields. All other data (type, icon, date, deltaDays, cash) is read live from `ops[]` in the template via:
```svelte
{@const opA = ops.find(o => o.tempId === sug.tempIdA)}
{@const opB = ops.find(o => o.tempId === sug.tempIdB)}
{@const deltaDays = opA && opB ? daysDiff(opA.fields.date, opB.fields.date) : 0}
```

### Step 4: FX Suffix in Banner + Tooltip (BulkModal)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

#### 4a. Reactive FX market cache

Add state + effect:
```typescript
import {lookupFxRate} from '$lib/stores/fxStoreRegistry';
import {computeFxConversionInfo, buildFxTooltipData} from '$lib/utils/fxConversionHelper';
import Tooltip from '$lib/components/ui/Tooltip.svelte';

/** Reactive bridge for async FX market rates. Key: "BASE-QUOTE-DATE" */
let fxMarketCache = $state<Map<string, FxDataPoint | null>>(new Map());
let fxFetchGeneration = 0;
```

#### 4b. $effect for FX lookups

```typescript
$effect(() => {
    const currentGen = ++fxFetchGeneration;
    const fxEntries = bannerSuggestions.filter(s => s.targetType === 'FX_CONVERSION');
    
    for (const entry of fxEntries) {
        const opA = ops.find(o => o.tempId === entry.tempIdA);
        const opB = ops.find(o => o.tempId === entry.tempIdB);
        if (!opA?.fields.cash || !opB?.fields.cash) continue;
        
        // Determine from/to (negative amount = from)
        const aAmt = Number(opA.fields.cash.amount);
        const bAmt = Number(opB.fields.cash.amount);
        const [from, to] = aAmt < 0 ? [opA, opB] : [opB, opA];
        const base = from.fields.cash!.code;
        const quote = to.fields.cash!.code;
        const date = from.fields.date; // use "from" side date for lookup
        const cacheKey = `${base}-${quote}-${date}`;
        
        if (fxMarketCache.has(cacheKey)) continue; // already fetched or pending
        fxMarketCache.set(cacheKey, null); // mark as pending (prevents duplicate launches)
        
        lookupFxRate(base, quote, date).then(result => {
            if (currentGen !== fxFetchGeneration) return; // generation changed, discard
            // Verify entry still exists
            if (!bannerSuggestions.some(s => s.tempIdA === entry.tempIdA && s.tempIdB === entry.tempIdB)) return;
            fxMarketCache = new Map(fxMarketCache).set(cacheKey, result);
        });
    }
});
```

#### 4c. Template suffix (after ΔNd)

In the banner `{#each}` loop, for FX_CONVERSION entries:

```svelte
{#if sug.targetType === 'FX_CONVERSION' && opA?.fields.cash && opB?.fields.cash}
    {@const aAmt = Number(opA.fields.cash.amount)}
    {@const bAmt = Number(opB.fields.cash.amount)}
    {@const fromOp = aAmt < 0 ? opA : opB}
    {@const toOp = aAmt < 0 ? opB : opA}
    {@const fxInfo = computeFxConversionInfo(
        Number(fromOp.fields.cash.amount), fromOp.fields.cash.code,
        Number(toOp.fields.cash.amount), toOp.fields.cash.code
    )}
    {#if fxInfo}
        {@const cacheKey = `${fxInfo.base}-${fxInfo.quote}-${fromOp.fields.date}`}
        {@const fxPoint = fxMarketCache.get(cacheKey)}
        {@const tooltipData = buildFxTooltipData(fxInfo, fxPoint)}
        <span class="text-gray-400 mx-0.5">·</span>
        <Tooltip html={buildFxTooltipHtml(tooltipData, $t)} position="bottom">
            <span class="inline-flex items-center gap-0.5 text-[11px] text-violet-600 dark:text-violet-400 cursor-help">
                {@html formatCurrencyCodeHtml(fxInfo.base)}
                <span>→</span>
                {@html formatCurrencyCodeHtml(fxInfo.quote)}
                <span class="font-mono">@ {fxInfo.impliedRate.toFixed(4)}</span>
                {#if tooltipData.staleDays != null && tooltipData.staleDays > 0}
                    <span class="text-amber-500">⚠️</span>
                {/if}
            </span>
        </Tooltip>
    {/if}
{/if}
```

#### 4d. Tooltip HTML builder function

```typescript
function buildFxTooltipHtml(data: FxTooltipData, t: Function): string {
    let html = `<div class="space-y-1">`;
    html += `<div><span class="text-gray-400">${t('transactions.fxInfo.impliedRate')}:</span> <strong>${data.impliedRate.toFixed(4)}</strong></div>`;
    if (data.marketRate != null) {
        html += `<div><span class="text-gray-400">${t('transactions.fxInfo.marketRate')}:</span> ${data.marketRate.toFixed(4)}`;
        if (data.staleDays != null && data.staleDays > 0) {
            html += ` <span class="text-amber-400">⚠️ ${t('transactions.fxInfo.stale', {values: {days: data.staleDays}})}</span>`;
        }
        if (data.marketDate) html += ` <span class="text-gray-500">(${data.marketDate})</span>`;
        html += `</div>`;
        if (data.spread) {
            const sign = data.spread.absolute >= 0 ? '+' : '';
            html += `<div><span class="text-gray-400">${t('transactions.fxInfo.spread')}:</span> ${sign}${data.spread.absolute.toFixed(4)} (${sign}${data.spread.percent.toFixed(2)}%)</div>`;
        }
    } else {
        html += `<div class="text-gray-500 italic">${t('transactions.fxInfo.marketNotAvailable')}</div>`;
    }
    html += `</div>`;
    return html;
}
```

### Step 5: Info Marker in FormModal FX

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

#### 5a. State + effect

```typescript
import {lookupFxRate} from '$lib/stores/fxStoreRegistry';
import {computeFxConversionInfo, buildFxTooltipData} from '$lib/utils/fxConversionHelper';
import {Info} from 'lucide-svelte';
import Tooltip from '$lib/components/ui/Tooltip.svelte';

let fxMarketPoint = $state<FxDataPoint | null | undefined>(undefined);
let fxLookupKey = $state('');
```

```typescript
$effect(() => {
    if (pairLayout !== 'fx') { fxMarketPoint = undefined; return; }
    const fromCode = draft.cash?.code;
    const toCode = dualTo.cash?.code;
    const fromDate = draft.date;
    if (!fromCode || !toCode || fromCode === toCode || !fromDate) {
        fxMarketPoint = undefined;
        return;
    }
    const key = `${fromCode}-${toCode}-${fromDate}`;
    if (key === fxLookupKey) return; // no change
    fxLookupKey = key;
    fxMarketPoint = undefined; // reset
    lookupFxRate(fromCode, toCode, fromDate).then(result => {
        if (`${fromCode}-${toCode}-${fromDate}` === fxLookupKey) {
            fxMarketPoint = result;
        }
    });
});
```

#### 5b. Template (below the swap arrow, ~line 1540)

Between the swap button and the "To" card, when `pairLayout === 'fx'`:

```svelte
{#if pairLayout === 'fx' && draft.cash?.amount && dualTo.cash?.amount && draft.cash?.code !== dualTo.cash?.code}
    {@const fxInfo = computeFxConversionInfo(
        Number(draft.cash.amount), draft.cash.code,
        Number(dualTo.cash.amount), dualTo.cash.code
    )}
    {#if fxInfo}
        {@const tooltipData = buildFxTooltipData(fxInfo, fxMarketPoint)}
        <div class="flex justify-center -my-1" data-testid="tx-form-fx-info">
            <Tooltip html={buildFxTooltipHtml(tooltipData, $t)} position="bottom">
                <span class="inline-flex items-center gap-1 text-[11px] text-violet-600 dark:text-violet-400 cursor-help px-2 py-0.5 rounded bg-violet-50 dark:bg-violet-900/20">
                    <Info size={12} />
                    <span class="font-mono">{fxInfo.impliedRate.toFixed(4)}</span>
                    {#if tooltipData.staleDays != null && tooltipData.staleDays > 0}
                        <span class="text-amber-500">⚠️</span>
                    {/if}
                </span>
            </Tooltip>
        </div>
    {/if}
{/if}
```

Note: `buildFxTooltipHtml` shared — extract to the helper file or import from a shared location.

### Step 6: i18n Keys

Via `./dev.py i18n add` — 4 lingue:

| Key | EN | IT | FR | ES |
|-----|----|----|----|----|
| `transactions.fxInfo.impliedRate` | Implied rate | Tasso implicito | Taux implicite | Tasa implícita |
| `transactions.fxInfo.marketRate` | Market rate | Tasso di mercato | Taux de marché | Tasa de mercado |
| `transactions.fxInfo.spread` | Spread | Spread | Spread | Spread |
| `transactions.fxInfo.stale` | stale {days}d | non agg. {days}g | obsolète {days}j | obsoleto {days}d |
| `transactions.fxInfo.marketNotAvailable` | Market rate not available | Tasso di mercato non disponibile | Taux de marché non disponible | Tasa de mercado no disponible |
| `transactions.fxInfo.pairNotConfigured` | FX pair not configured | Coppia FX non configurata | Paire FX non configurée | Par FX no configurado |

### Step 7: Documentation — Financial Theory

**File**: `mkdocs_src/docs/financial-theory/instruments/transaction-types/fx-conversion.en.md`

Add section after "How It Works" (before "Split & Promote"):

```markdown
---

## 📈 Implied Rate & Broker Spread

LibreFolio automatically computes the **implied exchange rate** from the two linked amounts:

$$
\text{Implied Rate} = \frac{\lvert\text{Amount}_{target}\rvert}{\lvert\text{Amount}_{source}\rvert}
$$

This is compared with the **market rate** from the FX subsystem at the transaction date. The difference is the **broker spread** — the markup applied by the broker for the conversion:

$$
\text{Spread} = \text{Implied Rate} - \text{Market Rate}
$$

$$
\text{Spread \%} = \frac{\text{Spread}}{\text{Market Rate}} \times 100
$$

!!! info "Where you'll see this"

    - **Bulk Edit banner**: when two standalone transactions are detected as a potential FX conversion, the implied rate and spread are shown inline with a tooltip for details.
    - **Transaction Form**: when creating or editing an FX conversion, an info marker between the two sides shows the implied rate vs. market rate.

!!! warning "Market Rate Availability"

    The market rate comparison requires the relevant FX pair to be configured in LibreFolio's FX system. If the pair is not configured or no rate exists for the transaction date, only the implied rate is shown (the spread cannot be computed).

    When a rate from a different date is used (backward-fill), a ⚠️ stale indicator shows how many days old the rate is.
```

### Step 8: Documentation — Developer

**File**: `mkdocs_src/docs/developer/architecture/database/brokers_transactions.md`

Add paragraph at the end of "💱 Currency & FX Integration" section (before "🔗 Related Documentation"):

```markdown
### Implied FX Rate Derivation

For `FX_CONVERSION` paired transactions, the effective exchange rate applied by the broker can be derived from the two linked rows:

```
implied_rate = |amount_to| / |amount_from|
```

The frontend compares this with the market rate obtained via `POST /fx/currencies/convert` (amount=1, single date). The rate is cached in the `fxStoreRegistry` TimeSeriesStore — subsequent lookups for the same pair+date are instant.

This comparison is displayed in:
- The promote-suggest banner (BulkModal) — when two standalone TX are detected as a potential FX conversion
- The FX conversion form — as an info tooltip between the "From" and "To" panels
```

### Step 9: TODO_FUTURI Entry

**File**: `TODO_FUTURI.md`

```markdown
## 🔄 FX Store Registry — Centralize Fetch Pattern

**Data aggiunta**: 18 Maggio 2026
**Priority**: P3
**Status**: 📋 PIANIFICATO

### Contesto

Currently, 4+ pages (fx list, fx detail, asset list, asset detail) duplicate the same FX data loading pattern:
```
store.getMissingIntervals() → fetch gaps via POST /fx/currencies/convert → store.merge()
```

With the addition of `lookupFxRate()` (Step 1 of FX Implied Rate feature), the pattern is now available as a single-point-lookup. But range-based loading (charts, tables) still uses the manual pattern.

### Azione Futura

1. Create `ensureFxRangeLoaded(slug, start, end): Promise<FxDataPoint[]>` in `fxStoreRegistry.ts` that encapsulates the gap-detection + fetch + merge pattern
2. Refactor the 4 pages to use this helper instead of inline fetch logic
3. Consider a reactive version counter (`fxCacheVersion` $state) in the registry to allow `$derived` consumers to react to cache updates without $effect bridges

### Files Affected

- `frontend/src/routes/(app)/fx/+page.svelte` — FX list page
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — FX detail page
- `frontend/src/routes/(app)/assets/+page.svelte` — Asset list page
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` — Asset detail page
- `frontend/src/lib/stores/fxStoreRegistry.ts` — New helper functions

### Benefit

- ~100 lines of duplicated code removed across 4 pages
- Single source of truth for FX fetch logic
- Foundation for future reactive FX cache (version counter)
```

### Step 10: Verify & Test

- `./dev.py i18n audit` → verify no missing keys
- Existing tests (`tx-bulk-suggest-ux`, `tx-split-promote`, `tx-bulk-operations`) must still pass
- No new E2E test file for this feature (visual-only enhancement, hard to assert tooltip content in E2E). Manual walktest verification.
- If desired later: add a test that verifies `data-testid="tx-form-fx-info"` is visible when creating an FX_CONVERSION with both amounts filled.

## Execution Checklist

- [x] Step 1: `lookupFxRate()` + `lookupFxRateSync()` in fxStoreRegistry.ts
- [x] Step 2: `fxConversionHelper.ts` (computeFxConversionInfo, computeSpread, buildFxTooltipData)
- [x] Step 3: Reduce SuggestEntry to `{tempIdA, tempIdB, targetType, isDB?, dbCandidateId?}` — all display data read live from ops[]
- [x] Step 4a: fxMarketCache $state + generation counter in BulkModal
- [x] Step 4b: $effect for FX lookups with generation guard (+ untrack for cache reads)
- [x] Step 4c: Template suffix + Tooltip in banner
- [x] Step 4d: buildFxTooltipHtml function (shared — in fxConversionHelper.ts)
- [x] Step 5a: FormModal state + $effect for FX lookup
- [x] Step 5b: Template info marker with Tooltip
- [x] Step 6: i18n keys (6 keys × 4 languages)
- [x] Step 7: Doc financial-theory (fx-conversion.en.md)
- [x] Step 8: Doc developer (brokers_transactions.md)
- [x] Step 9: TODO_FUTURI entry (FX Store centralize)
- [x] `./dev.py i18n audit` → 0 incomplete keys ✅
- [x] Existing E2E tests pass ✅ (2026-05-18: all 14 transaction test suites green)
- [ ] Manual walktest: banner shows FX suffix + tooltip, FormModal shows info marker

### Step 3 Implementation Note

Kept `isDB` and `dbCandidateId` as optional fields because they represent **structural flow control** (DB-candidate import flow), not display data. All other fields (`labelA`, `labelB`, `targetLabel`, `typeA`, `typeB`, `dateA`, `dateB`, `deltaDays`) removed. Template reads live from ops[] via `{@const}`. `triggerPromoteFromSuggestion` computes labels inline from ops[]. `targetLabel` derived via `$t('transactions.types.' + sug.targetType)` in template.

## Resolved Considerations

1. **`@` separator** → maintained (`.toFixed(4)` as in `FxPriceSummary`)
2. **new+new case** → covered uniformly by `lookupFxRate()` (same as edit+edit)
3. **new+edit case** → covered: banner matches both from `ops[]`, lookupFxRate for market
4. **FormModal** → covered by `lookupFxRate()` with $effect reacting to currency/date changes
5. **Generation guard** → counter incremented each time $effect runs; promise results discarded if generation changed or entry no longer exists
6. **Promise returns late (tooltip gone)** → data lands in TimeSeriesStore (not lost); fxMarketCache Map not updated if generation stale (no visual effect)
7. **Backend enrichment** → deferred to TODO_FUTURI as optional optimization (eliminates 1 call per pair+date for edit+edit, but doesn't cover all cases)
8. **Docs** → EN-only, translations via Aphra pipeline later
9. **Cache in fxStoreRegistry** → `lookupFxRate` merges into TimeSeriesStore, making subsequent calls for same pair+date instant
10. **Rate direction** → `lookupFxRate` normalizes internally (stores as alphabetical pair) but returns in the requested direction (inverts if needed)

