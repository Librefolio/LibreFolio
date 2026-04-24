---
title: "Responsive Layout 4-Mode Pattern"
category: concept
tags: [frontend, responsive, layout, breakpoints, ux]
related_features: [F-021, F-032]
---

# Concept: Responsive Layout 4-Mode Pattern

## Definition

LibreFolio's list pages with filter bars (Assets, FX) use a **4-breakpoint responsive layout system** instead of the traditional 3 (desktop/tablet/mobile). The addition of `tablet-s` (small tablet) provides better adaptation to intermediate screen widths where neither `tablet` nor `mobile` layouts work well.

## Breakpoint Modes

| Mode | Width Range | Layout Strategy |
|------|-------------|----------------|
| `wide` | ≥1100px | All filters and action buttons in single horizontal row |
| `tablet` | 770-1100px | Filters on 2 rows, action buttons in 2×2 grid on right |
| `tablet-s` | 500-770px | Filters stacked below datepicker, action buttons in vertical column (icon-only) |
| `mobile` | <500px | Everything stacked vertically and centered, icon-only buttons |

## Rationale for `tablet-s`

**Problem**: The 500-770px range is problematic:
- **Too narrow for `tablet` layout**: Filters and buttons don't fit in row, causing wrapping or overflow
- **Too wide for `mobile` layout**: Stacking everything wastes horizontal space, poor UX on landscape phones/small tablets

**Solution**: Intermediate `tablet-s` layout:
- Datepicker and filters aligned left, stacked vertically (2 rows)
- Action buttons in a right-aligned vertical column
- Buttons show icon-only (no text labels) to save horizontal space
- Clean left-right split utilizes available width efficiently

## Implementation Pattern

### 1. State Variable

```typescript
let layoutMode: 'wide' | 'tablet' | 'tablet-s' | 'mobile' = $state('wide');
```

### 2. ResizeObserver

```typescript
onMount(() => {
  const observer = new ResizeObserver((entries) => {
    const width = entries[0].contentRect.width;
    if (width >= 1100) layoutMode = 'wide';
    else if (width >= 770) layoutMode = 'tablet';
    else if (width >= 500) layoutMode = 'tablet-s';  // ← the key addition
    else layoutMode = 'mobile';
  });
  observer.observe(filterBarRef);
  return () => observer.disconnect();
});
```

### 3. Conditional CSS Classes

```svelte
<!-- Container -->
<div class:layout-wide={layoutMode === 'wide'}
     class:layout-tablet={layoutMode === 'tablet'}
     class:layout-tablet-s={layoutMode === 'tablet-s'}
     class:layout-mobile={layoutMode === 'mobile'}>
  
  <!-- Filters block -->
  <div class="filters"
       class:flex-row={layoutMode === 'wide'}
       class:flex-col={layoutMode === 'tablet' || layoutMode === 'tablet-s'}
       class:items-center={layoutMode === 'mobile'}>
    <!-- DateRangePicker, search, type/currency filters, reset -->
  </div>
  
  <!-- Actions block -->
  <div class="actions"
       class:flex-row={layoutMode === 'wide'}
       class:grid-cols-2={layoutMode === 'tablet'}
       class:flex-col={layoutMode === 'tablet-s'}
       class:items-center={layoutMode === 'mobile'}>
    <!-- Settings, Sync, Refresh, etc. -->
  </div>
</div>
```

### 4. Action Button Labels

```typescript
// Show labels in wide/tablet, hide in tablet-s/mobile
let showActionLabels = $derived(layoutMode === 'wide' || layoutMode === 'tablet');
```

```svelte
<button>
  <Icon class="lucide" />
  {#if showActionLabels}<span>{$t('common.sync')}</span>{/if}
</button>
```

## Visual Layout Examples

### Wide (≥1100px)
```
┌──────────────────────────────────────────────────────────────┐
│  📅 [datepicker]  🔍[search] [active] [▾type] [▾cur] [×]    │
│                   [Abs/%] [⚙ Settings] [⟳ Sync] [↻ Refresh] │
└──────────────────────────────────────────────────────────────┘
```

### Tablet (770-1100px)
```
┌──────────────────────────────────────────────────────────────┐
│  📅 [datepicker]  🔍[search]  [active]  │  [Abs/%] [⚙ Set]  │
│                   [▾type] [▾cur] [×]    │  [⟳ Sync] [↻ Ref] │
└──────────────────────────────────────────────────────────────┘
```

### Tablet-S (500-770px) ← The Key Addition
```
┌──────────────────────────────────────────────────────────────┐
│  📅 [datepicker]                        │  [Abs/%]           │
│  🔍 [search]  [active]  [▾ type]  [×]  │  [⚙]              │
│                  [▾ currency]           │  [⟳]              │
│                                          │  [↻]              │
└──────────────────────────────────────────────────────────────┘
```

### Mobile (<500px)
```
┌──────────────────────────────────────────────────────────────┐
│                  📅 [datepicker]                             │
│                  🔍 [search...]                              │
│                  [active]  [▾ type]  [×]                     │
│                  [▾ currency]                                 │
│                  [Abs/%]  [⚙]  [⟳]  [↻]                    │
└──────────────────────────────────────────────────────────────┘
```

## Filter Bar Behavior Refinement

**Issue**: In `tablet` mode, if filters block used `flex-row flex-wrap`, filters would return to single row when space allowed → inconsistent with the 2-row design.

**Fix**: Force 2-row layout in `tablet` and `tablet-s` modes:
- Datepicker always on first row
- Search, type, currency filters always on second row
- Only `wide` mode uses flexible single-row with wrapping

**CSS**:
```svelte
<!-- Filters container -->
<div class:flex-row={layoutMode === 'wide'}
     class:flex-col={layoutMode === 'tablet' || layoutMode === 'tablet-s'}>
  
  <!-- Inner filters (search, type, currency) -->
  <div class:flex-row={layoutMode === 'wide'}
       class:flex-col={layoutMode === 'tablet' || layoutMode === 'tablet-s'}>
```

## Where Applied

| Page | Implementation File | Notes |
|------|---------------------|-------|
| Assets List | `frontend/src/routes/(app)/assets/+page.svelte` | Full 4-mode support with type filter counts |
| FX List | `frontend/src/routes/(app)/fx/+page.svelte` | Full 4-mode support with currency selectors |

## Benefits

1. **Better UX**: No awkward wrapping or overflow in intermediate widths
2. **Efficient space use**: `tablet-s` layout uses left-right split effectively
3. **Consistent pattern**: Same 4-mode logic across all list pages with filter bars
4. **Graceful degradation**: Each breakpoint optimized for its range

## Trade-offs

1. **More code**: 4 modes instead of 3 → more conditional logic
2. **Testing complexity**: Must verify layout at 4+ widths manually
3. **Additional breakpoint to maintain**: If design changes, 4 modes to update instead of 3

## Future Use

**Recommendation**: Use this 4-mode pattern for any new list page with:
- Datepicker + multiple filter controls
- 3+ action buttons
- Expectation of use on tablets and large phones

**Helper**: Consider extracting `responsiveLayout.svelte.ts` (already created in Step 2c) into a reusable Runes-based store for consistent breakpoint detection.

## Related

- [[features/F-021]] — FX List View (uses 4-mode)
- [[features/F-032]] — Asset List View (uses 4-mode)
- [[concepts/dual-view-pattern]] — Grid/table toggle pattern (works with any layout mode)
- Source: [[sources/phase06-bugfix-migration]]

## Source files

| Role | Path |
|------|------|
| Assets page | `frontend/src/routes/(app)/assets/+page.svelte` |
| FX page | `frontend/src/routes/(app)/fx/+page.svelte` |
| Responsive helper | `frontend/src/lib/utils/responsiveLayout.svelte.ts` |
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step1/plan-phase06BugfixMigration-part2.md` |
