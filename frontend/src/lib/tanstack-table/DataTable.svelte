<!--
  DataTable - Componente tabella riutilizzabile basato su TanStack Table v8

  Questo componente wrappa l'adapter custom Svelte 5 per TanStack Table
  e fornisce una UI consistente con lo stile LibreFolio.

  Features supportate:
  - Sorting (cliccando sugli header)
  - Pagination
  - Styling dark/light mode

  @example
  ```svelte
  <script>
    import DataTable from '$lib/tanstack-table/DataTable.svelte';
    import { createColumnHelper } from '$lib/tanstack-table';

    const columnHelper = createColumnHelper<MyData>();
    const columns = [
      columnHelper.accessor('name', { header: 'Name' }),
      columnHelper.accessor('email', { header: 'Email' }),
    ];

    let data = $state([...]);
  </script>

  <DataTable {columns} {data} />
  ```
-->
<script lang="ts" generics="TData extends Record<string, unknown>">
	import {
		createSvelteTable,
		getCoreRowModel,
		getSortedRowModel,
		getPaginationRowModel,
		type ColumnDef,
		type SortingState,
		type PaginationState,
	} from '$lib/tanstack-table';
	import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-svelte';

	interface Props {
		/** Dati della tabella */
		data: TData[];
		/** Definizione delle colonne */
		columns: ColumnDef<TData, unknown>[];
		/** Abilita sorting (default: true) */
		enableSorting?: boolean;
		/** Abilita pagination (default: true) */
		enablePagination?: boolean;
		/** Righe per pagina (default: 10) */
		pageSize?: number;
		/** Classe CSS aggiuntiva per il container */
		class?: string;
	}

	let {
		data,
		columns,
		enableSorting = true,
		enablePagination = true,
		pageSize = 10,
		class: className = '',
	}: Props = $props();

	// Stato sorting
	let sorting = $state<SortingState>([]);

	// Stato pagination - uso derivato per pageSize
	let pagination = $state<PaginationState>({
		pageIndex: 0,
		pageSize: 10,
	});

	// Sincronizza pageSize prop con stato pagination
	$effect(() => {
		pagination = { ...pagination, pageSize };
	});

	// Creazione tabella con opzioni reactive
	const table = createSvelteTable({
		get data() {
			return data;
		},
		get columns() {
			return columns;
		},
		getCoreRowModel: getCoreRowModel(),
		get getSortedRowModel() {
			return enableSorting ? getSortedRowModel() : undefined;
		},
		get getPaginationRowModel() {
			return enablePagination ? getPaginationRowModel() : undefined;
		},
		onSortingChange: (updater) => {
			sorting = typeof updater === 'function' ? updater(sorting) : updater;
		},
		onPaginationChange: (updater) => {
			pagination = typeof updater === 'function' ? updater(pagination) : updater;
		},
		state: {
			get sorting() {
				return sorting;
			},
			get pagination() {
				return pagination;
			},
		},
	});

	// Funzioni di navigazione
	function goToFirstPage() {
		table.setPageIndex(0);
	}

	function goToPreviousPage() {
		table.previousPage();
	}

	function goToNextPage() {
		table.nextPage();
	}

	function goToLastPage() {
		table.setPageIndex(table.getPageCount() - 1);
	}

	// Helper per renderizzare contenuto cella
	function renderContent(content: unknown, context: unknown): string {
		if (typeof content === 'string') {
			return content;
		}
		if (typeof content === 'function') {
			const result = content(context);
			return typeof result === 'string' ? result : String(result ?? '');
		}
		return String(content ?? '');
	}
</script>

<div class="w-full {className}">
	<!-- Tabella -->
	<div class="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
		<table class="w-full text-sm">
			<thead class="bg-slate-50 dark:bg-slate-800">
				{#each table.getHeaderGroups() as headerGroup}
					<tr>
						{#each headerGroup.headers as header}
							<th
								class="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300
									{enableSorting && header.column.getCanSort()
									? 'cursor-pointer select-none hover:bg-slate-100 dark:hover:bg-slate-700'
									: ''}"
								onclick={() => enableSorting && header.column.toggleSorting()}
							>
								<div class="flex items-center gap-2">
									{#if !header.isPlaceholder}
										{renderContent(header.column.columnDef.header, header.getContext())}
										{#if enableSorting && header.column.getCanSort()}
											{@const sorted = header.column.getIsSorted()}
											{#if sorted === 'asc'}
												<ChevronUp class="h-4 w-4" />
											{:else if sorted === 'desc'}
												<ChevronDown class="h-4 w-4" />
											{:else}
												<ChevronsUpDown class="h-4 w-4 text-slate-400" />
											{/if}
										{/if}
									{/if}
								</div>
							</th>
						{/each}
					</tr>
				{/each}
			</thead>
			<tbody class="divide-y divide-slate-200 dark:divide-slate-700">
				{#each table.getRowModel().rows as row}
					<tr class="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800">
						{#each row.getVisibleCells() as cell}
							<td class="px-4 py-3 text-slate-600 dark:text-slate-400">
								{renderContent(cell.column.columnDef.cell, cell.getContext())}
							</td>
						{/each}
					</tr>
				{:else}
					<tr>
						<td
							colspan={table.getAllColumns().length}
							class="px-4 py-8 text-center text-slate-500 dark:text-slate-400"
						>
							Nessun dato disponibile
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<!-- Pagination -->
	{#if enablePagination && data.length > pagination.pageSize}
		<div
			class="mt-4 flex items-center justify-between text-sm text-slate-600 dark:text-slate-400"
		>
			<div>
				Pagina {table.getState().pagination.pageIndex + 1} di {table.getPageCount()}
				<span class="ml-2 text-slate-400">({data.length} elementi totali)</span>
			</div>
			<div class="flex items-center gap-2">
				<button
					type="button"
					class="rounded p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={!table.getCanPreviousPage()}
					onclick={goToFirstPage}
					title="Prima pagina"
				>
					<ChevronLeft class="h-4 w-4" />
					<ChevronLeft class="h-4 w-4 -ml-3" />
				</button>
				<button
					type="button"
					class="rounded p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={!table.getCanPreviousPage()}
					onclick={goToPreviousPage}
					title="Pagina precedente"
				>
					<ChevronLeft class="h-4 w-4" />
				</button>
				<button
					type="button"
					class="rounded p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={!table.getCanNextPage()}
					onclick={goToNextPage}
					title="Pagina successiva"
				>
					<ChevronRight class="h-4 w-4" />
				</button>
				<button
					type="button"
					class="rounded p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={!table.getCanNextPage()}
					onclick={goToLastPage}
					title="Ultima pagina"
				>
					<ChevronRight class="h-4 w-4" />
					<ChevronRight class="h-4 w-4 -ml-3" />
				</button>
			</div>
		</div>
	{/if}
</div>
