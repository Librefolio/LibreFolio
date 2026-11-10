<!--
  DataTablePagination - Floating pagination controls for DataTable
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {ChevronDown, ChevronLeft, ChevronRight} from 'lucide-svelte';
    import {getFixedDropdownPosition} from '$lib/utils/layout/dropdownPosition';

    interface Props {
        pageIndex: number;
        pageSize: number;
        totalItems: number;
        pageSizeOptions: number[];
        onPageChange: (pageIndex: number) => void;
        onPageSizeChange: (pageSize: number) => void;
    }

    let {pageIndex, pageSize, totalItems, pageSizeOptions, onPageChange, onPageSizeChange}: Props = $props();

    let totalPages = $derived(Math.max(1, Math.ceil(totalItems / pageSize)));
    let currentPage = $derived(pageIndex + 1);
    let canPrevPage = $derived(pageIndex > 0);
    let canNextPage = $derived(pageIndex < totalPages - 1);
    let pageInputValue = $state('');

    // Custom dropdown state
    let showDropdown = $state(false);
    let dropdownRef: HTMLDivElement | null = $state(null);
    let dropdownPanel: HTMLDivElement | null = $state(null);
    let dropdownPosition = $state({left: 0, top: 0});

    $effect(() => {
        if (!showDropdown || !dropdownRef || !dropdownPanel) return;
        const anchor = dropdownRef;
        const panel = dropdownPanel;
        const updatePosition = () => {
            dropdownPosition = getFixedDropdownPosition(anchor, panel, 'start');
        };
        updatePosition();
        window.addEventListener('resize', updatePosition);
        window.addEventListener('scroll', updatePosition, true);
        return () => {
            window.removeEventListener('resize', updatePosition);
            window.removeEventListener('scroll', updatePosition, true);
        };
    });

    $effect(() => {
        pageInputValue = String(currentPage);
    });

    // Close dropdown on click outside
    $effect(() => {
        if (showDropdown) {
            const handleClickOutside = (e: MouseEvent) => {
                if (dropdownRef && !dropdownRef.contains(e.target as Node)) {
                    showDropdown = false;
                }
            };
            document.addEventListener('click', handleClickOutside);
            return () => document.removeEventListener('click', handleClickOutside);
        }
    });

    function getPageNumbers(): (number | 'ellipsis')[] {
        if (totalPages <= 7) return Array.from({length: totalPages}, (_, i) => i + 1);
        const pages: (number | 'ellipsis')[] = [1];
        const start = Math.max(2, currentPage - 1);
        const end = Math.min(totalPages - 1, currentPage + 1);
        if (start > 2) pages.push('ellipsis');
        for (let i = start; i <= end; i++) pages.push(i);
        if (end < totalPages - 1) pages.push('ellipsis');
        if (totalPages > 1) pages.push(totalPages);
        return pages;
    }

    function goToPage(page: number) {
        if (page >= 1 && page <= totalPages) onPageChange(page - 1);
    }

    function handlePageInputKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            const page = parseInt(pageInputValue, 10);
            if (!isNaN(page)) goToPage(page);
            (e.target as HTMLInputElement).blur();
        } else if (e.key === 'Escape') {
            pageInputValue = String(currentPage);
            (e.target as HTMLInputElement).blur();
        }
    }

    function handlePageInputBlur() {
        const page = parseInt(pageInputValue, 10);
        if (!isNaN(page) && page >= 1 && page <= totalPages) goToPage(page);
        else pageInputValue = String(currentPage);
    }

    function selectPageSize(size: number) {
        onPageSizeChange(size === 0 ? 999999 : size);
        showDropdown = false;
    }

    function getDisplayPageSize(): number {
        return pageSize >= 999999 ? 0 : pageSize;
    }

    function formatPageSize(size: number): string {
        return size === 0 ? '∞' : String(size);
    }
</script>

<div class="pagination-container" data-testid="data-table-pagination">
    <div class="pagination-balloon">
        <!-- Row 1: Page size + label + total (groups together on mobile) -->
        <div class="pagination-row-top">
            <div bind:this={dropdownRef} class="page-size-selector">
                <button class="page-size-btn" onclick={() => (showDropdown = !showDropdown)} type="button" data-testid="pagination-size-trigger" aria-expanded={showDropdown}>
                    <span>{formatPageSize(getDisplayPageSize())}</span>
                    <ChevronDown size={14} />
                </button>
                {#if showDropdown}
                    <div class="page-size-dropdown" bind:this={dropdownPanel} style:left={`${dropdownPosition.left}px`} style:top={`${dropdownPosition.top}px`} data-testid="pagination-size-menu">
                        {#each pageSizeOptions as size}
                            <button type="button" class="dropdown-option" class:selected={getDisplayPageSize() === size} onclick={() => selectPageSize(size)} data-testid={`pagination-size-option-${size}`}>
                                {formatPageSize(size)}
                            </button>
                        {/each}
                    </div>
                {/if}
                <span class="page-size-label">{$t('table.perPage') || 'per page'}</span>
            </div>
            <div class="divider desktop-only"></div>
            <div class="total-info"><span class="total-text">{totalItems} {$t('table.items') || 'items'}</span></div>
        </div>

        <!-- Row 2: Page navigation -->
        <div class="pagination-row-bottom">
            <button class="nav-btn" data-testid="pagination-prev" disabled={!canPrevPage} onclick={() => goToPage(currentPage - 1)} type="button">
                <ChevronLeft size={16} />
            </button>
            <div class="page-numbers">
                {#each getPageNumbers() as page}
                    {#if page === 'ellipsis'}
                        <span class="ellipsis">…</span>
                    {:else if page === currentPage}
                        <input
                            type="text"
                            class="page-input"
                            bind:value={pageInputValue}
                            onkeydown={handlePageInputKeydown}
                            onblur={handlePageInputBlur}
                            onclick={(e) => {
                                const el = e.target;
                                if (el instanceof HTMLInputElement) el.select();
                            }}
                        />
                    {:else}
                        <button type="button" class="page-btn" onclick={() => goToPage(page)}>{page}</button>
                    {/if}
                {/each}
            </div>
            <button class="nav-btn" data-testid="pagination-next" disabled={!canNextPage} onclick={() => goToPage(currentPage + 1)} type="button">
                <ChevronRight size={16} />
            </button>
        </div>
    </div>
</div>

<style>
    .pagination-container {
        position: sticky;
        bottom: 1rem;
        display: flex;
        justify-content: center;
        padding: 0.5rem 0;
        pointer-events: none;
        z-index: 30;
    }

    .pagination-balloon {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background: var(--lf-surface-card);
        border: 1px solid var(--lf-border-subtle);
        border-radius: 1rem;
        box-shadow: 0 4px 6px -1px var(--lf-shadow-card);
        pointer-events: auto;
        max-width: calc(100vw - 2rem);
    }

    /* Row layout */
    .pagination-row-top {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .pagination-row-bottom {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    /* Custom page size dropdown */
    .page-size-selector {
        position: relative;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .page-size-btn {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.25rem 0.5rem;
        font-size: 0.8125rem;
        border: 1px solid var(--lf-border-input);
        border-radius: 6px;
        background: var(--lf-surface-field);
        color: var(--lf-text-secondary);
        cursor: pointer;
        transition: all 0.15s;
    }

    .page-size-btn:hover {
        border-color: var(--lf-border-input-hover);
        background: var(--lf-surface-field);
    }

    .page-size-dropdown {
        position: fixed;
        min-width: 60px;
        background: var(--lf-surface-card);
        border: 1px solid var(--lf-border-raised);
        border-radius: 8px;
        box-shadow: 0 4px 12px var(--lf-shadow-raised);
        max-height: calc(100vh - 1rem);
        overflow-y: auto;
        z-index: 10;
    }

    .dropdown-option {
        display: block;
        width: 100%;
        padding: 0.5rem 0.75rem;
        font-size: 0.8125rem;
        text-align: left;
        border: none;
        background: transparent;
        color: var(--lf-text-secondary);
        cursor: pointer;
        transition: all 0.1s;
    }

    .dropdown-option:hover {
        background: var(--lf-surface-hover);
    }

    .dropdown-option.selected {
        background: var(--lf-selected);
        color: var(--lf-link);
        font-weight: 500;
    }

    .page-size-label {
        font-size: 0.75rem;
        color: var(--lf-text-muted);
        white-space: nowrap;
    }

    .divider {
        width: 1px;
        height: 1.5rem;
        background: var(--lf-border-subtle);
    }

    .nav-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: none;
        border-radius: 6px;
        background: transparent;
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .nav-btn:hover:not(:disabled) {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .nav-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    .page-numbers {
        display: flex;
        align-items: center;
        gap: 0.125rem;
    }

    .page-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 28px;
        height: 28px;
        padding: 0 0.375rem;
        font-size: 0.8125rem;
        border: none;
        border-radius: 6px;
        background: transparent;
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .page-btn:hover {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .page-input {
        width: 36px;
        height: 28px;
        text-align: center;
        font-size: 0.8125rem;
        font-weight: 500;
        border: 1px solid var(--lf-checked);
        border-radius: 6px;
        background: var(--lf-selected);
        color: var(--lf-link);
    }

    .page-input:focus {
        outline: none;
        box-shadow: 0 0 0 2px color-mix(in oklab, var(--lf-focus) 20%, transparent);
    }

    .ellipsis {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 28px;
        color: var(--lf-text-muted);
        font-size: 0.75rem;
    }

    .total-info {
        display: flex;
        align-items: center;
    }

    .total-text {
        font-size: 0.75rem;
        color: var(--lf-text-muted);
        white-space: nowrap;
    }

    /* Desktop: single row */
    @media (min-width: 481px) {
        .pagination-balloon {
            flex-direction: row;
            border-radius: 9999px;
            gap: 0.75rem;
        }

        .pagination-row-top {
            gap: 0.75rem;
        }
    }

    /* Mobile */
    @media (max-width: 480px) {
        .pagination-container {
            bottom: 0.5rem;
            padding: 0.5rem;
        }

        .pagination-balloon {
            padding: 0.75rem 1rem;
        }

        .page-size-btn {
            padding: 0.375rem 0.625rem;
            font-size: 0.875rem;
            min-height: 36px;
        }

        .desktop-only {
            display: none;
        }
    }
</style>
