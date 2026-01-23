<!--
  DataTablePagination - Floating pagination controls for DataTable
-->
<script lang="ts">
	import { t } from '$lib/i18n';
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';

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

	$effect(() => { pageInputValue = String(currentPage); });

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

	function handlePageSizeChange(e: Event) {
		const newSize = parseInt((e.target as HTMLSelectElement).value, 10);
		onPageSizeChange(newSize === 0 ? 999999 : newSize);
	}

	function getDisplayPageSize(): number {
		return pageSize >= 999999 ? 0 : pageSize;
	}
</script>

<div class="pagination-container">
	<div class="pagination-balloon">
		<div class="page-size-selector">
			<select class="page-size-select" value={getDisplayPageSize()} onchange={handlePageSizeChange}>
				{#each pageSizeOptions as size}
					<option value={size}>{size === 0 ? '∞' : size}</option>
				{/each}
			</select>
			<span class="page-size-label">{$t('table.perPage') || 'per page'}</span>
		</div>
		<div class="divider"></div>
		<div class="page-nav">
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
		<div class="divider"></div>
		<div class="total-info"><span class="total-text">{totalItems} {$t('table.items') || 'items'}</span></div>
	</div>
</div>

<style>
	.pagination-container { position: sticky; bottom: 1rem; display: flex; justify-content: center; padding: 0.5rem 0; pointer-events: none; z-index: 20; }
	.pagination-balloon { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 1rem; background: white; border: 1px solid #e2e8f0; border-radius: 9999px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); pointer-events: auto; }
	:global(.dark) .pagination-balloon { background: #1e293b; border-color: #334155; }
	.page-size-selector { display: flex; align-items: center; gap: 0.5rem; }
	.page-size-select { padding: 0.25rem 1.5rem 0.25rem 0.5rem; font-size: 0.8125rem; border: 1px solid #e2e8f0; border-radius: 6px; background: white url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E") no-repeat right 0.25rem center; color: #475569; cursor: pointer; appearance: none; }
	:global(.dark) .page-size-select { background-color: #0f172a; border-color: #334155; color: #e2e8f0; }
	.page-size-select:focus { outline: none; border-color: #1a4031; }
	:global(.dark) .page-size-select:focus { border-color: #4ade80; }
	.page-size-label { font-size: 0.75rem; color: #94a3b8; }
	.divider { width: 1px; height: 1.5rem; background: #e2e8f0; }
	:global(.dark) .divider { background: #334155; }
	.page-nav { display: flex; align-items: center; gap: 0.25rem; }
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
	@media (max-width: 480px) { .page-size-selector, .total-info, .divider { display: none; } }
</style>
