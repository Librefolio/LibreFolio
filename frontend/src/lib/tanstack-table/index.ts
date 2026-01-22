/**
 * TanStack Table - Svelte 5 Custom Adapter
 *
 * Questo modulo esporta l'adapter custom per usare TanStack Table v8
 * con Svelte 5 in modo stabile.
 *
 * NOTA: Quando TanStack Table v9 sarà stabile con supporto ufficiale Svelte 5,
 * questo adapter dovrà essere sostituito con l'adapter ufficiale.
 * @see TODO_FUTURI.md
 *
 * @example
 * ```svelte
 * <script>
 *   import {
 *     createSvelteTable,
 *     getCoreRowModel,
 *     getSortedRowModel,
 *     getPaginationRowModel
 *   } from '$lib/tanstack-table';
 *   import FlexRender from '$lib/tanstack-table/FlexRender.svelte';
 * </script>
 * ```
 */

// Adapter Svelte 5 custom
export { createSvelteTable } from './createSvelteTable.svelte.js';

// Re-export delle funzionalità core da @tanstack/table-core
export {
	// Core
	createTable,
	// Row Models
	getCoreRowModel,
	getFilteredRowModel,
	getSortedRowModel,
	getGroupedRowModel,
	getExpandedRowModel,
	getPaginationRowModel,
	getFacetedRowModel,
	getFacetedUniqueValues,
	getFacetedMinMaxValues,
	// Column helpers
	createColumnHelper,
	// Types (re-export per comodità)
	type Table,
	type Row,
	type Cell,
	type Column,
	type Header,
	type HeaderGroup,
	type RowData,
	type ColumnDef,
	type TableOptions,
	type TableState,
	type SortingState,
	type PaginationState,
	type ColumnFiltersState,
	type VisibilityState,
	type RowSelectionState,
	type ExpandedState,
	type GroupingState,
	type Updater,
	type OnChangeFn,
} from '@tanstack/table-core';
