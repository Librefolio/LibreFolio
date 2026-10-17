<script generics="T" lang="ts">
    /**
     * DataTable — the content of one data-column header (`th.th-data`): the sort button, the header HTML, the
     * tooltip icon (a link or a gesture), the filter button with its popover, the resize handle.
     *
     * Cut out of `DataTable.svelte` (release 1.3, Y2). The `th` and everything structural stay in the parent, and
     * so do the state, the effects and the handlers: they arrive as props under their parent names, so the markup
     * moved verbatim. `openFilterColumnId` is bound: the parent owns it. The header tooltip's long-press timer stays
     * in the parent too, whose `onDestroy` cancels it.
     */
    import {ChevronDown, ChevronsUpDown, ChevronUp, Filter, Info} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import DataTableColumnFilter from './DataTableColumnFilter.svelte';
    import type {ColumnDef, FilterValue, SortState} from './types';
    import {getColumnMinMax, getCurrencyMinMaxByCode, getCurrencyOptions, getEnumOptionsWithCounts, getMultiEnumOptions, getMultiEnumOptionsWithCounts} from './dataTableLogic';

    interface Props {
        column: ColumnDef<T>;
        sortDir: SortState['direction'] | null | undefined;
        hasFilter: boolean;
        enableSorting: boolean;
        enableColumnFilters: boolean;
        enableColumnResize: boolean;
        resizing: {columnId: string} | null;
        columnFilters: Record<string, FilterValue>;
        data: T[];
        boundaryData: T[];
        openFilterColumnId: string | null;
        toggleSort: (columnId: string) => void;
        applyColumnFilter: (columnId: string, filter: FilterValue | null) => void;
        startResize: (columnId: string, event: PointerEvent) => void;
        handleHeaderTooltipGestureClick: (event: MouseEvent) => void;
        handleHeaderTooltipDblClick: (event: MouseEvent, url: string) => void;
        handleHeaderTooltipKeydown: (event: KeyboardEvent, url: string) => void;
        handleHeaderTooltipTouchStart: (url: string) => void;
        cancelHeaderTooltipLongPress: () => void;
    }

    let {
        column,
        sortDir,
        hasFilter,
        enableSorting,
        enableColumnFilters,
        enableColumnResize,
        resizing,
        columnFilters,
        data,
        boundaryData,
        openFilterColumnId = $bindable(),
        toggleSort,
        applyColumnFilter,
        startResize,
        handleHeaderTooltipGestureClick,
        handleHeaderTooltipDblClick,
        handleHeaderTooltipKeydown,
        handleHeaderTooltipTouchStart,
        cancelHeaderTooltipLongPress,
    }: Props = $props();

    /** The filter button: the anchor of the fixed-position filter popover. */
    let filterBtn = $state<HTMLButtonElement | null>(null);

    /** Empty currency min/max map — extracted to avoid generic syntax `<string, …>` in
     *  Svelte template `{@const}` blocks where `<` is parsed as an HTML tag. */
    const EMPTY_CURRENCY_MIN_MAX: Map<string, {min: number; max: number}> = new Map();

    function getColumnLabel(col: ColumnDef<T>): string {
        return typeof col.header === 'function' ? col.header() : col.header;
    }

    function getColumnHeaderHtml(col: ColumnDef<T>): string | null {
        if (!col.headerHtml) return null;
        return typeof col.headerHtml === 'function' ? col.headerHtml() : col.headerHtml;
    }

    function getColumnTooltip(col: ColumnDef<T>): string | null {
        if (!col.headerTooltip) return null;
        return typeof col.headerTooltip === 'function' ? col.headerTooltip() : col.headerTooltip;
    }

    function getColumnTooltipUrl(col: ColumnDef<T>): string | null {
        if (!col.headerTooltipUrl) return null;
        return typeof col.headerTooltipUrl === 'function' ? col.headerTooltipUrl() : col.headerTooltipUrl;
    }
</script>

<div class="header-content" style={column.align === 'center' ? 'justify-content:center' : column.align === 'right' ? 'justify-content:flex-end' : ''}>
    {#if getColumnTooltip(column)}
        {@const tooltipText = getColumnTooltip(column) ?? ''}
        <Tooltip text={tooltipText} position="top">
            <button type="button" class="header-sort-btn" data-testid="dt-sort-{column.id}" onclick={() => toggleSort(column.id)} disabled={column.sortable === false || !enableSorting}>
                {#if getColumnHeaderHtml(column)}
                    <span class="header-text">{@html getColumnHeaderHtml(column)}</span>
                {:else}
                    <span class="header-text">{getColumnLabel(column)}</span>
                {/if}
                {#if column.sortable !== false && enableSorting}
                    <span class="sort-icon">
                        {#if sortDir === 'asc'}
                            <ChevronUp size={14} />
                        {:else if sortDir === 'desc'}
                            <ChevronDown size={14} />
                        {:else}
                            <ChevronsUpDown size={14} />
                        {/if}
                    </span>
                {/if}
            </button>
        </Tooltip>
    {:else}
        <button type="button" class="header-sort-btn" data-testid="dt-sort-{column.id}" onclick={() => toggleSort(column.id)} disabled={column.sortable === false || !enableSorting}>
            {#if getColumnHeaderHtml(column)}
                <span class="header-text">{@html getColumnHeaderHtml(column)}</span>
            {:else}
                <span class="header-text">{getColumnLabel(column)}</span>
            {/if}
            {#if column.sortable !== false && enableSorting}
                <span class="sort-icon">
                    {#if sortDir === 'asc'}
                        <ChevronUp size={14} />
                    {:else if sortDir === 'desc'}
                        <ChevronDown size={14} />
                    {:else}
                        <ChevronsUpDown size={14} />
                    {/if}
                </span>
            {/if}
        </button>
    {/if}

    <!-- Header tooltip info icon: only when the column has both a tooltip and a documentation URL -->
    {#if getColumnTooltip(column) && getColumnTooltipUrl(column)}
        {@const tooltipText = getColumnTooltip(column) ?? ''}
        {@const tooltipUrl = getColumnTooltipUrl(column) ?? ''}
        {#if column.headerTooltipLinkMode === 'gesture'}
            <Tooltip text={tooltipText} position="top" math={tooltipText.includes('$')} interactiveChild={true}>
                <button
                    type="button"
                    class="header-tooltip-icon header-tooltip-gesture"
                    aria-label={tooltipText}
                    aria-keyshortcuts="Shift+Enter"
                    data-testid={`dt-header-tooltip-${column.id}`}
                    onclick={handleHeaderTooltipGestureClick}
                    ondblclick={(event) => handleHeaderTooltipDblClick(event, tooltipUrl)}
                    onkeydown={(event) => handleHeaderTooltipKeydown(event, tooltipUrl)}
                    ontouchstart={() => handleHeaderTooltipTouchStart(tooltipUrl)}
                    ontouchend={cancelHeaderTooltipLongPress}
                    ontouchmove={cancelHeaderTooltipLongPress}
                    ontouchcancel={cancelHeaderTooltipLongPress}
                >
                    <Info size={12} />
                </button>
            </Tooltip>
        {:else}
            <Tooltip text={tooltipText} position="top" math={tooltipText.includes('$')}>
                <a href={tooltipUrl} target="_blank" rel="noopener noreferrer" class="header-tooltip-icon header-tooltip-link" data-testid={`dt-header-tooltip-${column.id}`} onclick={(e) => e.stopPropagation()}>
                    <Info size={12} />
                </a>
            </Tooltip>
        {/if}
    {/if}

    <!-- Filter button -->
    {#if column.filterable !== false && enableColumnFilters}
        <button bind:this={filterBtn} type="button" class="filter-btn" class:active={hasFilter} onclick={() => (openFilterColumnId = openFilterColumnId === column.id ? null : column.id)} data-testid={`col-filter-trigger-${column.id}`}>
            <Filter size={12} />
        </button>
    {/if}

    <!-- Resize handle -->
    {#if column.resizable !== false && enableColumnResize}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <span class="resize-handle" class:resizing={resizing?.columnId === column.id} onpointerdown={(e) => startResize(column.id, e)}></span>
    {/if}

    <!-- Filter popover -->
    {#if openFilterColumnId === column.id}
        {@const minMax = column.type === 'number' || column.type === 'size' ? getColumnMinMax(column, boundaryData) : {min: 0, max: 100}}
        {@const dynamicEnumOptions = column.type === 'multi-enum' ? (column.enumOptions && column.enumOptions.length > 0 ? getMultiEnumOptionsWithCounts(column, data) : getMultiEnumOptions(column, data)) : column.type === 'enum' ? getEnumOptionsWithCounts(column, data) : (column.enumOptions ?? [])}
        {@const currencyOptions = column.type === 'currency-stack' ? (column.currencyOptions ?? getCurrencyOptions(column, data)) : []}
        {@const currencyMinMaxByCode = column.type === 'currency-stack' ? getCurrencyMinMaxByCode(column, boundaryData) : EMPTY_CURRENCY_MIN_MAX}
        <DataTableColumnFilter
            type={column.type}
            enumOptions={dynamicEnumOptions}
            {currencyOptions}
            {currencyMinMaxByCode}
            numberMin={minMax.min}
            numberMax={minMax.max}
            integerOnly={column.integerOnly ?? false}
            initialValue={columnFilters[column.id]}
            onApply={(filter) => applyColumnFilter(column.id, filter)}
            onClose={() => (openFilterColumnId = null)}
            anchorElement={filterBtn}
        />
    {/if}
</div>

<style>
    .header-content {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .header-sort-btn {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        background: none;
        border: none;
        padding: 0;
        color: inherit;
        font: inherit;
        cursor: pointer;
    }

    .header-sort-btn:disabled {
        cursor: default;
    }

    .sort-icon {
        display: flex;
        color: var(--lf-text-muted);
    }

    .header-tooltip-icon {
        display: flex;
        align-items: center;
        color: var(--lf-text-muted);
        cursor: pointer;
        flex-shrink: 0;
    }

    .header-tooltip-link {
        text-decoration: none;
        transition: color 0.15s;
    }

    .header-tooltip-gesture {
        padding: 0;
        border: 0;
        background: transparent;
        transition: color 0.15s;
    }

    .header-tooltip-link:hover,
    .header-tooltip-gesture:hover {
        color: var(--lf-link);
    }

    /* The same rules as the "show selected only" button of DataTable.svelte's selection header, which keeps its own copy. */
    .filter-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border: none;
        border-radius: 4px;
        background: transparent;
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .filter-btn:hover {
        background: var(--lf-surface-neutral);
        color: var(--lf-text-primary);
    }

    .filter-btn.active {
        background: var(--lf-checked);
        color: var(--lf-on-checked);
    }

    .resize-handle {
        position: absolute;
        right: 0;
        top: 0;
        bottom: 0;
        width: 6px;
        background: transparent;
        cursor: col-resize;
        /* A finger dragging the handle resizes the column instead of panning the table (D-Y18). */
        touch-action: none;
        opacity: 0;
        transition: opacity 0.15s;
        z-index: 5;
    }

    /* The th belongs to DataTable.svelte: its hover reaches the handle through :global. */
    :global(th:hover) .resize-handle {
        opacity: 1;
        background: var(--lf-border-input);
    }

    .resize-handle.resizing,
    .resize-handle:active {
        opacity: 1;
        background: var(--lf-checked);
    }
</style>
