<script lang="ts">
    /**
     * DataTable.svelte - Generic data table with TanStack Table v9
     *
     * Features:
     * - Sorting (click header)
     * - Pagination
     * - Dark mode support
     */
    import { createTable, FlexRender, getCoreRowModel, getSortedRowModel, getPaginationRowModel } from '@tanstack/svelte-table';
    import type { ColumnDef, SortingState, PaginationState, TableOptions } from '@tanstack/table-core';
    import { _ } from '$lib/i18n';
    import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-svelte';

    // Generic type for row data
    type T = $$Generic;

    // Props
    export let data: T[] = [];
    export let columns: ColumnDef<T, any>[] = [];
    export let pageSize: number = 10;
    export let enableSorting: boolean = true;
    export let enablePagination: boolean = true;
    export let emptyMessage: string = '';

    // State
    let sorting: SortingState = $state([]);
    let pagination: PaginationState = $state({
        pageIndex: 0,
        pageSize: pageSize
    });

    // Page size options
    const pageSizeOptions = [10, 25, 50, 100];

    // Table options
    const options: TableOptions<T> = {
        get data() { return data; },
        columns,
        state: {
            get sorting() { return sorting; },
            get pagination() { return pagination; }
        },
        onSortingChange: (updater: any) => {
            sorting = typeof updater === 'function' ? updater(sorting) : updater;
        },
        onPaginationChange: (updater: any) => {
            pagination = typeof updater === 'function' ? updater(pagination) : updater;
        },
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
        getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
    };

    // Create table
    const table = createTable(options);

    // Computed values
    $: pageCount = table.getPageCount();
    $: currentPage = pagination.pageIndex + 1;
    $: totalRows = data.length;
    $: startRow = pagination.pageIndex * pagination.pageSize + 1;
    $: endRow = Math.min((pagination.pageIndex + 1) * pagination.pageSize, totalRows);

    function handlePageSizeChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        pagination = {
            ...pagination,
            pageSize: parseInt(target.value),
            pageIndex: 0
        };
    }
</script>

<div class="data-table w-full">
    <!-- Table -->
    <div class="overflow-x-auto border border-gray-200 dark:border-slate-700 rounded-lg">
        <table class="w-full text-sm">
            <thead class="bg-gray-50 dark:bg-slate-800">
                {#each table.getHeaderGroups() as headerGroup}
                    <tr>
                        {#each headerGroup.headers as header}
                            <th
                                class="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300
                                       {header.column.getCanSort() ? 'cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-slate-700' : ''}"
                                onclick={header.column.getToggleSortingHandler()}
                            >
                                <div class="flex items-center gap-2">
                                    {#if !header.isPlaceholder}
                                        <FlexRender content={header.column.columnDef.header} context={header.getContext()} />
                                    {/if}

                                    {#if header.column.getCanSort()}
                                        <span class="text-gray-400">
                                            {#if header.column.getIsSorted() === 'asc'}
                                                <ChevronUp size={14} />
                                            {:else if header.column.getIsSorted() === 'desc'}
                                                <ChevronDown size={14} />
                                            {:else}
                                                <ChevronsUpDown size={14} />
                                            {/if}
                                        </span>
                                    {/if}
                                </div>
                            </th>
                        {/each}
                    </tr>
                {/each}
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-slate-700">
                {#if table.getRowModel().rows.length === 0}
                    <tr>
                        <td colspan={columns.length} class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                            {emptyMessage || $_('common.noData')}
                        </td>
                    </tr>
                {:else}
                    {#each table.getRowModel().rows as row}
                        <tr class="bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
                            {#each row.getVisibleCells() as cell}
                                <td class="px-4 py-3 text-gray-700 dark:text-gray-300">
                                    <FlexRender content={cell.column.columnDef.cell} context={cell.getContext()} />
                                </td>
                            {/each}
                        </tr>
                    {/each}
                {/if}
            </tbody>
        </table>
    </div>

    <!-- Pagination -->
    {#if enablePagination && totalRows > 0}
        <div class="flex items-center justify-between mt-4 px-2">
            <!-- Page size selector -->
            <div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span>{$_('table.rowsPerPage')}:</span>
                <select
                    value={pagination.pageSize}
                    onchange={handlePageSizeChange}
                    class="px-2 py-1 border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300"
                >
                    {#each pageSizeOptions as size}
                        <option value={size}>{size}</option>
                    {/each}
                </select>
            </div>

            <!-- Showing indicator -->
            <div class="text-sm text-gray-600 dark:text-gray-400">
                {$_('table.showing')} {startRow}-{endRow} {$_('table.of')} {totalRows}
            </div>

            <!-- Navigation -->
            <div class="flex items-center gap-1">
                <button
                    onclick={() => table.setPageIndex(0)}
                    disabled={!table.getCanPreviousPage()}
                    class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-600 dark:text-gray-400"
                    title={$_('table.firstPage')}
                >
                    <ChevronsLeft size={16} />
                </button>
                <button
                    onclick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                    class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-600 dark:text-gray-400"
                    title={$_('table.previousPage')}
                >
                    <ChevronLeft size={16} />
                </button>

                <span class="px-3 py-1 text-sm text-gray-700 dark:text-gray-300">
                    {currentPage} / {pageCount}
                </span>

                <button
                    onclick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                    class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-600 dark:text-gray-400"
                    title={$_('table.nextPage')}
                >
                    <ChevronRight size={16} />
                </button>
                <button
                    onclick={() => table.setPageIndex(pageCount - 1)}
                    disabled={!table.getCanNextPage()}
                    class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-600 dark:text-gray-400"
                    title={$_('table.lastPage')}
                >
                    <ChevronsRight size={16} />
                </button>
            </div>
        </div>
    {/if}
</div>
