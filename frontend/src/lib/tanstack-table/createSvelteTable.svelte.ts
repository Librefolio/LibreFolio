/**
 * TanStack Table Svelte 5 Adapter
 *
 * Questo adapter permette di usare @tanstack/table-core (v8 stabile)
 * con Svelte 5, senza dipendere dall'adapter ufficiale @tanstack/svelte-table
 * che è compatibile solo con Svelte 3/4 o richiede la versione alpha v9.
 *
 * Approccio ispirato a:
 * - https://github.com/TanStack/table/discussions/4454
 * - Community adapters per Svelte 5
 *
 * @see TODO_FUTURI.md per la nota sulla migrazione a v9 quando sarà stabile
 */

import {
	createTable,
	type RowData,
	type TableOptions,
	type TableOptionsResolved,
	type Table,
} from '@tanstack/table-core';

/**
 * Crea una tabella TanStack Table reattiva per Svelte 5.
 *
 * Utilizza $state per la gestione reattiva e wrappa le API di table-core.
 *
 * @param options - Opzioni della tabella (può essere una funzione che ritorna le opzioni)
 * @returns Oggetto Table reattivo
 *
 * @example
 * ```svelte
 * <script lang="ts">
 *   import { createSvelteTable, getCoreRowModel } from '$lib/tanstack-table';
 *
 *   const data = $state([...]);
 *   const columns = [...];
 *
 *   const table = createSvelteTable({
 *     get data() { return data },
 *     columns,
 *     getCoreRowModel: getCoreRowModel(),
 *   });
 * </script>
 * ```
 */
export function createSvelteTable<TData extends RowData>(
	options: TableOptions<TData>
): Table<TData> {
	// Risolvi le opzioni con i default
	const resolvedOptions: TableOptionsResolved<TData> = {
		state: {},
		onStateChange: () => {},
		renderFallbackValue: null,
		...options,
	};

	// Crea la tabella base
	const table = createTable(resolvedOptions);

	// Stato reattivo Svelte 5
	let tableState = $state(table.initialState);

	// Override dell'opzione setOptions per gestire la reattività
	table.setOptions((prev) => ({
		...prev,
		...options,
		state: {
			...tableState,
			...options.state,
		},
		onStateChange: (updater) => {
			// Aggiorna lo stato locale
			if (typeof updater === 'function') {
				tableState = updater(tableState);
			} else {
				tableState = updater;
			}

			// Chiama il callback originale se esiste
			options.onStateChange?.(updater);
		},
	}));

	// Effetto per sincronizzare le opzioni quando cambiano
	$effect(() => {
		table.setOptions((prev) => ({
			...prev,
			...options,
			state: {
				...tableState,
				...options.state,
			},
			onStateChange: (updater) => {
				if (typeof updater === 'function') {
					tableState = updater(tableState);
				} else {
					tableState = updater;
				}
				options.onStateChange?.(updater);
			},
		}));
	});

	return table;
}
