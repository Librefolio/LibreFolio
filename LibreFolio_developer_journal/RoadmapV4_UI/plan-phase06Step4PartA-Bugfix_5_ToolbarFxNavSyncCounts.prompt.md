# Plan: Bugfix 5 — Toolbar order, FX modal/link, tablet-s FX, sync counts, smart back

Sette fix: invertire ordine bottoni, tablet-s FX, FX modal/link da asset, troncamento backend, test sync, e navigazione "indietro" con history multi-livello.

---

## Step 1: Creare `navigationStore.ts`

**File**: `frontend/src/lib/stores/navigationStore.ts`

Uno store che tiene traccia della profondità di navigazione SPA. Espone `trackNavigation()` (da chiamare in `afterNavigate`) e `goBack(fallbackPath: string)` che usa `history.back()` se c'è storia SPA, altrimenti `goto(fallbackPath)`. Integrare `afterNavigate` nel layout `(app)/+layout.svelte` per incrementare il contatore ad ogni navigazione intra-app. Così la navigazione indietro funziona su N livelli (asset→FX→back→asset→back→lista), con fallback alla pagina padre solo se si accede da deep-link diretto.

```typescript
/**
 * Navigation history store for smart back-navigation.
 *
 * Tracks SPA navigation depth so that goBack() can use history.back()
 * when there IS previous SPA history, or fall back to a parent path
 * when the user arrived via direct link / bookmark.
 */
import { goto } from '$app/navigation';

let depth = 0;

/**
 * Call this inside afterNavigate() in the app layout.
 * Only counts navigations that are NOT popstate (back/forward) events.
 */
export function trackNavigation(navigationType: string | undefined) {
    if (navigationType === 'popstate') {
        // User pressed back/forward — decrement depth
        depth = Math.max(0, depth - 1);
    } else {
        // link, goto, form, etc. — increment depth
        depth++;
    }
}

/**
 * Navigate back using browser history if available, otherwise goto fallbackPath.
 *
 * @param fallbackPath - The parent route to navigate to if there's no SPA history
 *                       (e.g. '/assets' for asset detail, '/fx' for FX detail)
 */
export function goBack(fallbackPath: string) {
    if (depth > 1) {
        history.back();
    } else {
        goto(fallbackPath);
    }
}

/**
 * Reset navigation depth. Call this when navigating via sidebar (top-level navigation)
 * to avoid stale depth from previous deep-link chains.
 */
export function resetNavDepth() {
    depth = 0;
}
```

---

## Step 2: Integrare `trackNavigation` nel layout e sidebar

### 2a — Layout `(app)/+layout.svelte`

Aggiungere `afterNavigate` e chiamare `trackNavigation`:

```svelte
<script lang="ts">
    // ...existing imports...
    import { afterNavigate } from '$app/navigation';
    import { trackNavigation } from '$lib/stores/navigationStore';

    // ...existing code...

    afterNavigate((nav) => {
        trackNavigation(nav.type);
    });
</script>
```

### 2b — Sidebar: reset depth on top-level navigation

**File**: `frontend/src/lib/components/layout/Sidebar.svelte`

Nelle funzioni di navigazione della sidebar (click su menu items), chiamare `resetNavDepth()` prima di `goto()`:

```svelte
<script lang="ts">
    // ...existing imports...
    import { resetNavDepth } from '$lib/stores/navigationStore';

    // In ogni nav link della sidebar, wrappare con reset:
    function navigateTo(path: string) {
        resetNavDepth();
        goto(path);
    }
</script>
```

---

## Step 3: Sostituire i 3 `goto('/...')` hardcoded con `goBack(fallback)`

### 3a — `assets/[id]/+page.svelte` (riga 565)

```svelte
<script lang="ts">
    // ...existing imports...
    import { goBack } from '$lib/stores/navigationStore';
</script>

<!-- DA -->
onclick={() => goto('/assets')}
<!-- A -->
onclick={() => goBack('/assets')}
```

### 3b — `fx/[pair]/+page.svelte` (riga 614)

```svelte
<script lang="ts">
    // ...existing imports...
    import { goBack } from '$lib/stores/navigationStore';
</script>

<!-- DA -->
onclick={() => goto('/fx')}
<!-- A -->
onclick={() => goBack('/fx')}
```

### 3c — `brokers/[id]/+page.svelte` (riga 66)

```svelte
<script lang="ts">
    // ...existing imports...
    import { goBack } from '$lib/stores/navigationStore';
</script>

<!-- DA -->
goto('/brokers');
<!-- A -->
goBack('/brokers');
```

---

## Step 4: Invertire ordine bottoni toolbar chart → 📏✏️⚙️

**File**: `frontend/src/routes/(app)/assets/[id]/+page.svelte` (righe 807-848) e `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (righe 801-856)

Riordinare i 3 `<button>` nel `<div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">`:

1. **Ruler** (📏 Measure) — primo
2. **Pencil** (✏️ Editor) — centro
3. **Settings** (⚙️ Aesthetics) — ultimo

### In `assets/[id]/+page.svelte`:

```svelte
                <div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">
                    <!-- Measure -->
                    <button
                            data-testid="asset-detail-measure-btn"
                            class="p-1.5 rounded-lg transition-colors {measureMode
                            ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={async () => {
                            if (measureMode) { measurePanel?.stopMeasureMode(); }
                            else { showMeasures = true; await tick(); measurePanel?.startMeasureMode(); }
                        }}
                            title={measureMode ? $t('assetDetail.exitMeasure') : $t('assetDetail.addMeasure')}
                    >
                        <Ruler size={16}/>
                    </button>
                    <!-- Edit data -->
                    <button
                            data-testid="asset-detail-editdata-btn"
                            class="p-1.5 rounded-lg transition-colors {showDataEditor
                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => {
                            if (showDataEditor) {
                                showDataEditor = false;
                                if (savedPanelStates) { showAesthetics = savedPanelStates.aesthetics; showMeasures = savedPanelStates.measures; showSignals = savedPanelStates.signals; savedPanelStates = null; }
                            } else {
                                savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                showAesthetics = false; showMeasures = false; showSignals = false; showDataEditor = true;
                            }
                        }}
                            title={showDataEditor ? $t('assetDetail.closeEditor') : $t('assetDetail.editData')}
                    >
                        <Pencil size={16}/>
                    </button>
                    <!-- Aesthetics -->
                    <button
                            data-testid="asset-detail-aesthetics-toggle"
                            class="p-1.5 rounded-lg transition-colors {showAesthetics
                            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-300 dark:ring-emerald-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => showAesthetics = !showAesthetics}
                            title={$t('common.aesthetics')}
                    >
                        <Settings size={16}/>
                    </button>
                </div>
```

### In `fx/[pair]/+page.svelte`:

Stessa struttura, con test-id `fx-detail-*`:

```svelte
                <div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">
                    <!-- Measure -->
                    <button
                            data-testid="fx-detail-measure-btn"
                            class="p-1.5 rounded-lg transition-colors {measureMode
                            ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={async () => {
                            if (measureMode) {
                                measurePanel?.stopMeasureMode();
                            } else {
                                showMeasures = true;
                                await tick();
                                measurePanel?.startMeasureMode();
                            }
                        }}
                            title={measureMode ? $t('fxDetail.exitMeasure') : $t('fxDetail.addMeasure')}
                    >
                        <Ruler size={16}/>
                    </button>
                    <!-- Edit data -->
                    <button
                            data-testid="fx-detail-edit-btn"
                            class="p-1.5 rounded-lg transition-colors {showDataEditor
                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => {
                            if (showDataEditor) {
                                showDataEditor = false;
                                pendingPreviewSignal = null;
                                if (savedPanelStates) {
                                    showAesthetics = savedPanelStates.aesthetics;
                                    showMeasures = savedPanelStates.measures;
                                    showSignals = savedPanelStates.signals;
                                    savedPanelStates = null;
                                }
                            } else {
                                savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                showAesthetics = false;
                                showMeasures = false;
                                showSignals = false;
                                showDataEditor = true;
                            }
                        }}
                            title={showDataEditor ? $t('fxDetail.closeEditor') : $t('fxDetail.editRates')}
                    >
                        <Pencil size={16}/>
                    </button>
                    <!-- Aesthetics -->
                    <button
                            data-testid="fx-detail-aesthetics-toggle"
                            class="p-1.5 rounded-lg transition-colors {showAesthetics
                            ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-300 dark:ring-emerald-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => showAesthetics = !showAesthetics}
                            title={$t('common.aesthetics')}
                    >
                        <Settings size={16}/>
                    </button>
                </div>
```

---

## Step 5: Aggiungere breakpoint `tablet-s` alla FX detail page

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

### 5a — Espandere il tipo di `layoutMode` (riga 94)

```typescript
// DA
let layoutMode = $state<'wide' | 'tablet' | 'mobile'>('tablet');
// A
let layoutMode = $state<'wide' | 'tablet' | 'tablet-s' | 'mobile'>('tablet');
```

### 5b — Aggiungere soglia nel ResizeObserver (riga 236)

```typescript
    $effect(() => {
        const el = filterBarRef;
        if (!el) return;
        const ro = new ResizeObserver(([entry]) => {
            const w = entry.contentRect.width;
            if (w >= 730) layoutMode = 'wide';
            else if (w >= 550) layoutMode = 'tablet';
            else if (w >= 400) layoutMode = 'tablet-s';
            else layoutMode = 'mobile';
            showActionLabels = w >= 600;
        });
        ro.observe(el);
        return () => ro.disconnect();
    });
```

### 5c — Usare `flex-col` per tablet-s nella sezione Actions (riga 689)

```svelte
<!-- DA -->
<div class="flex shrink-0 gap-1.5
            {layoutMode === 'mobile' ? 'flex-row justify-center' : 'grid grid-cols-2'}">
<!-- A -->
<div class="flex shrink-0 gap-1.5
            {layoutMode === 'mobile' || layoutMode === 'tablet-s' ? 'flex-col items-stretch' : 'grid grid-cols-2'}">
```

---

## Step 6: FX warning → FxPairAddModal + link a FX detail

**File**: `frontend/src/routes/(app)/assets/[id]/+page.svelte`

### 6a — Import e stato

```svelte
<script lang="ts">
    // ...existing imports...
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import { ArrowLeftRight } from 'lucide-svelte'; // add to existing import if not present

    // ...existing state...
    let showFxPairAddModal = $state(false);
</script>
```

### 6b — Derived: slug della coppia FX

Aggiungere dopo `fxConversionMissing` (riga ~209):

```typescript
    /** Canonical FX pair slug (alphabetically ordered) for linking */
    let fxPairSlug = $derived.by(() => {
        if (!assetInfo || !displayCurrency || displayCurrency === assetInfo.currency) return '';
        const a = assetInfo.currency < displayCurrency ? assetInfo.currency : displayCurrency;
        const b = assetInfo.currency < displayCurrency ? displayCurrency : assetInfo.currency;
        return `${a}-${b}`;
    });
```

### 6c — Template: sostituire il blocco FX warning (righe 681-697)

```svelte
                {#if fxConversionMissing}
                    <div class="flex items-center gap-1">
                        <button
                            class="p-1 rounded transition-colors {fxWarningToastVisible
                                ? 'text-amber-300 dark:text-amber-700 cursor-not-allowed opacity-50'
                                : 'text-amber-500 dark:text-amber-400 hover:text-amber-600 dark:hover:text-amber-300 cursor-pointer'}"
                            disabled={fxWarningToastVisible}
                            onclick={showFxWarningToast}
                            title={$t('assetDetail.fxPairMissing', {values: {base: assetInfo.currency, quote: displayCurrency}})}
                        >
                            <AlertTriangle size={16}/>
                        </button>
                        <button
                            class="text-[10px] text-amber-500 dark:text-amber-400 hover:underline cursor-pointer"
                            onclick={() => showFxPairAddModal = true}
                            title={$t('assetDetail.addFxPair')}
                        >
                            FX +
                        </button>
                    </div>
                {:else if displayCurrency && assetInfo && displayCurrency !== assetInfo.currency && fxPairSlug}
                    <a
                        href="/fx/{fxPairSlug}"
                        class="p-1 rounded text-gray-400 dark:text-gray-500 hover:text-libre-green dark:hover:text-emerald-400 transition-colors"
                        title={$t('assetDetail.goToFxPair')}
                    >
                        <ArrowLeftRight size={14}/>
                    </a>
                {/if}
```

### 6d — Componente FxPairAddModal nel template

Aggiungere dopo `<AssetModal .../>` (riga ~1040):

```svelte
<!-- FX Pair Add Modal (opened from FX warning) -->
{#if assetInfo}
    <FxPairAddModal
        bind:open={showFxPairAddModal}
        initialBase={assetInfo.currency}
        initialQuote={displayCurrency}
        oncreated={async () => {
            showFxPairAddModal = false;
            await loadFxPairSlugs();
        }}
        onclose={() => showFxPairAddModal = false}
    />
{/if}
```

### 6e — Aggiungere chiavi i18n mancanti

Aggiungere `assetDetail.goToFxPair` ai file di traduzione (EN/IT/FR/ES):

- EN: `"Go to FX pair detail"`
- IT: `"Vai al dettaglio coppia FX"`

---

## Step 7: Aggiungere props `initialBase`/`initialQuote` a FxPairAddModal

**File**: `frontend/src/lib/components/fx/FxPairAddModal.svelte`

### 7a — Estendere Props interface (riga 33)

```typescript
    interface Props {
        open?: boolean;
        dateStart?: string;
        dateEnd?: string;
        editMode?: boolean;
        editBase?: string;
        editQuote?: string;
        editRoutes?: ChainStep[][];
        /** Initial base currency for create mode (editable, not locked) */
        initialBase?: string;
        /** Initial quote currency for create mode (editable, not locked) */
        initialQuote?: string;
        oncreated?: (detail: { base: string; quote: string; hasRealProvider: boolean }) => void;
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        dateStart = '',
        dateEnd = '',
        editMode = false,
        editBase = '',
        editQuote = '',
        editRoutes = [],
        initialBase = '',
        initialQuote = '',
        oncreated,
        onclose,
    }: Props = $props();
```

### 7b — Aggiungere $effect per pre-fill in create mode (dopo riga 92)

```typescript
    // Pre-fill currencies in create mode (editable, not locked)
    $effect(() => {
        if (open && !editMode) {
            if (initialBase && !baseCurrency) baseCurrency = initialBase;
            if (initialQuote && !quoteCurrency) quoteCurrency = initialQuote;
        }
    });
```

---

## Step 8: Fix backend — troncamento nel confronto di `_count_actual_price_changes`

**File**: `backend/app/services/asset_source.py` (riga 1884)

### Root cause

`_count_actual_price_changes` confronta `float(old_close)` (dal DB, già troncato a 6 decimali) con `float(p.close)` (grezzo dal provider, 7+ decimali). Il confronto float dà sempre `True` anche quando il valore troncato è identico, gonfiando `changed_count` a `fetched_count`.

### Fix

```python
        async def _count_actual_price_changes(
            session,
            asset_id: int,
            price_items: list,
        ) -> tuple[int, int]:
            """
            Compare fetched prices with existing DB prices.
            Returns (new_count, changed_count) — truly new inserts and actual value changes.
            """
            if not price_items:
                return 0, 0

            dates = [p.date for p in price_items]

            # Load existing prices for these dates
            stmt = select(PriceHistory.date, PriceHistory.close).where(
                and_(PriceHistory.asset_id == asset_id, PriceHistory.date.in_(dates))
            )
            result = await session.execute(stmt)
            existing: dict = {row[0]: row[1] for row in result.all()}

            new_count = 0
            changed_count = 0
            for p in price_items:
                old_close = existing.get(p.date)
                if old_close is None:
                    new_count += 1
                else:
                    # Truncate fetched value to DB precision before comparing
                    truncated_new = truncate_priceHistory(Decimal(str(p.close)), "close")
                    if float(old_close) != float(truncated_new):
                        changed_count += 1

            return new_count, changed_count
```

---

## Step 9: Test backend — sync counts accurati

**File**: `backend/test_scripts/test_services/test_asset_sync_counts.py` (nuovo)

```python
"""
Test that asset sync reports accurate points_changed counts.

Verifies that re-syncing the same data does NOT inflate points_changed.
"""
from datetime import date
import time

import pytest

from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_async_engine
from backend.app.services.asset_source import AssetSourceManager
from backend.app.db.models import Asset, AssetType, ProviderInputType
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FARefreshItem, SyncStatus
from backend.app.schemas.common import DateRangeModel


def _unique(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


async def _create_asset_with_provider(
    session: AsyncSession, name: str, provider_code: str = "mockprov", identifier: str = "MOCK"
) -> int:
    """Helper: create asset + assign provider, return asset_id."""
    asset = Asset(display_name=name, currency="USD", asset_type=AssetType.STOCK, active=True)
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    await AssetSourceManager.bulk_assign_providers(
        [
            FAProviderAssignmentItem(
                asset_id=asset.id,
                provider_code=provider_code,
                identifier=identifier,
                identifier_type=ProviderInputType.AUTO_GENERATED,
                provider_params={},
            )
        ],
        session,
    )
    return asset.id


@pytest.mark.asyncio
async def test_second_sync_reports_zero_changes():
    """
    After syncing identical data twice, the second sync should report
    points_changed == 0 (no new inserts, no value changes).
    """
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset_id = await _create_asset_with_provider(session, _unique("SyncCountTest"))

        payload = [
            FARefreshItem(
                asset_id=asset_id,
                date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 3, 31)),
            )
        ]

        # First sync — should fetch and insert data
        result1 = await AssetSourceManager.bulk_refresh_prices(payload, session)
        r1 = next((r for r in result1.results if r.asset_id == asset_id), None)
        assert r1 is not None, "First sync result missing"
        assert r1.points_fetched > 0, "First sync should fetch some points"
        assert r1.points_changed > 0, "First sync should report changes (new inserts)"

        # Second sync — same data, should report zero changes
        result2 = await AssetSourceManager.bulk_refresh_prices(payload, session)
        r2 = next((r for r in result2.results if r.asset_id == asset_id), None)
        assert r2 is not None, "Second sync result missing"
        assert r2.points_fetched > 0, "Second sync should still fetch points"
        assert r2.points_changed == 0, (
            f"Second sync should report 0 changes, got {r2.points_changed} "
            f"(inserted={r2.inserted_count}, updated={r2.updated_count})"
        )
```

---

## Riepilogo file da modificare

| File | Step |
|------|------|
| `frontend/src/lib/stores/navigationStore.ts` | #1 (nuovo) |
| `frontend/src/routes/(app)/+layout.svelte` | #2a afterNavigate |
| `frontend/src/lib/components/layout/Sidebar.svelte` | #2b resetNavDepth |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | #3a goBack, #4 toolbar order, #6 FxPairAddModal + FX link |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | #3b goBack, #4 toolbar order, #5 tablet-s |
| `frontend/src/routes/(app)/brokers/[id]/+page.svelte` | #3c goBack |
| `frontend/src/lib/components/fx/FxPairAddModal.svelte` | #7 initialBase/initialQuote props |
| `backend/app/services/asset_source.py` | #8 truncate fix |
| `backend/test_scripts/test_services/test_asset_sync_counts.py` | #9 (nuovo) |
| File i18n (en.json, it.json, fr.json, es.json) | #6e chiave `assetDetail.goToFxPair` |

## Ordine di esecuzione

1. Step 1 — navigationStore (nuovo file)
2. Step 2 — integrare nel layout + sidebar
3. Step 3 — sostituire goto hardcoded (3 file)
4. Step 4 — invertire bottoni toolbar (2 file)
5. Step 5 — tablet-s FX detail
6. Step 7 — props FxPairAddModal
7. Step 6 — FX warning/link in asset detail
8. Step 8 — fix backend troncamento
9. Step 9 — test backend

