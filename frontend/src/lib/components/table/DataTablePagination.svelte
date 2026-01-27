<!--
  DataTablePagination - Floating pagination controls for DataTable
-->
<script lang="ts">
	import { t } from '$lib/i18n';
	import { ChevronLeft, ChevronRight, ChevronDown } from 'lucide-svelte';

	interface Props {
		pageIndex: number;
		pageSize: number;
		totalItems: number;
		pageSizeOptions: number[];
		onPageChange: (pageIndex: number) => void;
		onPageSizeChange: (pageSize: number) => void;
	}

	let { pageIndex, pageSize, totalItems, pageSizeOptions, onPageChange, onPageSizeChange }: Props = $props();

	let totalPages = $derived(Math.max(1, Math.ceil(totalItems / pageSize)));
	let currentPage = $derived(pageIndex + 1);
	let canPrevPage = $derived(pageIndex > 0);
	let canNextPage = $derived(pageIndex < totalPages - 1);
	let pageInputValue = $state('');

	// Custom dropdown state
	let showDropdown = $state(false);
	let dropdownRef = $state<HTMLDivElement | null>(null);

	$effect(() => { pageInputValue = String(currentPage); });

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
		if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
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

<div class="pagination-container">
	<div class="pagination-balloon">
		<!-- Row 1: Page size + label + total (groups together on mobile) -->
		<div class="pagination-row-top">
			<div class="page-size-selector" bind:this={dropdownRef}>
				<button
					type="button"
					class="page-size-btn"
					onclick={() => showDropdown = !showDropdown}
				>
					<span>{formatPageSize(getDisplayPageSize())}</span>
					<ChevronDown size={14} />
				</button>
				{#if showDropdown}
					<div class="page-size-dropdown">
						{#each pageSizeOptions as size}
							<button
								type="button"
								class="dropdown-option"
								class:selected={getDisplayPageSize() === size}
								onclick={() => selectPageSize(size)}
							>
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
			<button type="button" class="nav-btn" disabled={!canPrevPage} onclick={() => goToPage(currentPage - 1)}>
				<ChevronLeft size={16} />
			</button>
			<div class="page-numbers">
				{#each getPageNumbers() as page}
					{#if page === 'ellipsis'}
						<span class="ellipsis">…</span>
					{:else if page === currentPage}
						<input type="text" class="page-input" bind:value={pageInputValue} onkeydown={handlePageInputKeydown} onblur={handlePageInputBlur} onclick={(e) => (e.target as HTMLInputElement).select()} />
					{:else}
						<button type="button" class="page-btn" onclick={() => goToPage(page)}>{page}</button>
					{/if}
				{/each}
			</div>
			<button type="button" class="nav-btn" disabled={!canNextPage} onclick={() => goToPage(currentPage + 1)}>
				<ChevronRight size={16} />
			</button>
		</div>
	</div>
</div>

<style>
	.pagination-container { position: sticky; bottom: 1rem; display: flex; justify-content: center; padding: 0.5rem 0; pointer-events: none; z-index: 20; }
	.pagination-balloon { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background: white; border: 1px solid #e2e8f0; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); pointer-events: auto; max-width: calc(100vw - 2rem); }
	:global(.dark) .pagination-balloon { background: #1e293b; border-color: #334155; }

	/* Row layout */
	.pagination-row-top { display: flex; align-items: center; gap: 0.75rem; }
	.pagination-row-bottom { display: flex; align-items: center; gap: 0.25rem; }

	/* Custom page size dropdown */
	.page-size-selector { position: relative; display: flex; align-items: center; gap: 0.5rem; }
	.page-size-btn { display: flex; align-items: center; gap: 0.25rem; padding: 0.25rem 0.5rem; font-size: 0.8125rem; border: 1px solid #e2e8f0; border-radius: 6px; background: white; color: #475569; cursor: pointer; transition: all 0.15s; }
	.page-size-btn:hover { border-color: #cbd5e1; background: #f8fafc; }
	:global(.dark) .page-size-btn { background: #0f172a; border-color: #334155; color: #e2e8f0; }
	:global(.dark) .page-size-btn:hover { border-color: #475569; background: #1e293b; }

	.page-size-dropdown { position: absolute; bottom: 100%; left: 0; margin-bottom: 0.25rem; min-width: 60px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); overflow: hidden; z-index: 50; }
	:global(.dark) .page-size-dropdown { background: #1e293b; border-color: #334155; }

	.dropdown-option { display: block; width: 100%; padding: 0.5rem 0.75rem; font-size: 0.8125rem; text-align: left; border: none; background: transparent; color: #475569; cursor: pointer; transition: all 0.1s; }
	.dropdown-option:hover { background: #f1f5f9; }
	.dropdown-option.selected { background: #f0fdf4; color: #1a4031; font-weight: 500; }
	:global(.dark) .dropdown-option { color: #e2e8f0; }
	:global(.dark) .dropdown-option:hover { background: #334155; }
	:global(.dark) .dropdown-option.selected { background: #1a4031; color: #4ade80; }

	.page-size-label { font-size: 0.75rem; color: #94a3b8; white-space: nowrap; }
	.divider { width: 1px; height: 1.5rem; background: #e2e8f0; }
	:global(.dark) .divider { background: #334155; }

	.nav-btn { display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; border: none; border-radius: 6px; background: transparent; color: #64748b; cursor: pointer; transition: all 0.15s; }
	.nav-btn:hover:not(:disabled) { background: #f1f5f9; color: #0f172a; }
	.nav-btn:disabled { opacity: 0.4; cursor: not-allowed; }
	:global(.dark) .nav-btn { color: #94a3b8; }
	:global(.dark) .nav-btn:hover:not(:disabled) { background: #334155; color: #f1f5f9; }
	.page-numbers { display: flex; align-items: center; gap: 0.125rem; }
	.page-btn { display: flex; align-items: center; justify-content: center; min-width: 28px; height: 28px; padding: 0 0.375rem; font-size: 0.8125rem; border: none; border-radius: 6px; background: transparent; color: #64748b; cursor: pointer; transition: all 0.15s; }
	.page-btn:hover { background: #f1f5f9; color: #0f172a; }
	:global(.dark) .page-btn { color: #94a3b8; }
	:global(.dark) .page-btn:hover { background: #334155; color: #f1f5f9; }
	.page-input { width: 36px; height: 28px; text-align: center; font-size: 0.8125rem; font-weight: 500; border: 1px solid #1a4031; border-radius: 6px; background: #f0fdf4; color: #1a4031; }
	.page-input:focus { outline: none; box-shadow: 0 0 0 2px rgba(26, 64, 49, 0.2); }
	:global(.dark) .page-input { background: #1e293b; border-color: #4ade80; color: #4ade80; }
	:global(.dark) .page-input:focus { box-shadow: 0 0 0 2px rgba(74, 222, 128, 0.2); }
	.ellipsis { display: flex; align-items: center; justify-content: center; width: 20px; height: 28px; color: #94a3b8; font-size: 0.75rem; }
	.total-info { display: flex; align-items: center; }
	.total-text { font-size: 0.75rem; color: #94a3b8; white-space: nowrap; }

	/* Desktop: single row */
	@media (min-width: 481px) {
		.pagination-balloon { flex-direction: row; border-radius: 9999px; gap: 0.75rem; }
		.pagination-row-top { gap: 0.75rem; }
	}

	/* Mobile */
	@media (max-width: 480px) {
		.pagination-container { bottom: 0.5rem; padding: 0.5rem; }
		.pagination-balloon { padding: 0.75rem 1rem; }
		.page-size-btn { padding: 0.375rem 0.625rem; font-size: 0.875rem; min-height: 36px; }
		.desktop-only { display: none; }
	}
</style>
