<!--
  DataTableColumnFilter - Excel-style filter popover for table columns
  
  Filter types based on column data type:
  - text: text input with match mode (contains, starts, ends, equals) - instant apply
  - number: min/max range
  - date: from/to date pickers
  - enum: checkbox list of available options
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n';
	import { X, Search, Check, RotateCcw } from 'lucide-svelte';
	import { fade } from 'svelte/transition';
	import type { ColumnType, EnumOption, FilterValue } from './types';

	type TextMatchMode = 'contains' | 'startsWith' | 'endsWith' | 'equals';

	interface Props {
		type: ColumnType;
		enumOptions?: EnumOption[];
		numberMin?: number;
		numberMax?: number;
		onApply: (filter: FilterValue | null) => void;
		onClose: () => void;
		initialValue?: FilterValue | null;
	}

	let { type, enumOptions = [], numberMin = 0, numberMax = 100, onApply, onClose, initialValue = null }: Props = $props();

	let popoverElement: HTMLDivElement;

	// Helper functions to get initial values
	function getInitialTextValue(): string {
		return initialValue?.type === 'text' ? initialValue.value : '';
	}
	function getInitialTextMatchMode(): TextMatchMode {
		return initialValue?.type === 'text' ? initialValue.matchMode : 'contains';
	}
	function getInitialNumMin(): number {
		return initialValue?.type === 'number' ? initialValue.min ?? numberMin : numberMin;
	}
	function getInitialNumMax(): number {
		return initialValue?.type === 'number' ? initialValue.max ?? numberMax : numberMax;
	}
	function getInitialDateFrom(): string {
		return initialValue?.type === 'date' ? initialValue.from ?? '' : '';
	}
	function getInitialDateTo(): string {
		return initialValue?.type === 'date' ? initialValue.to ?? '' : '';
	}
	function getInitialEnums(): Set<string> {
		return new Set(initialValue?.type === 'enum' ? initialValue.selected : enumOptions.map(o => o.value));
	}

	// Text filter state
	let textValue = $state(getInitialTextValue());
	let textMatchMode = $state<TextMatchMode>(getInitialTextMatchMode());

	// Number filter state
	let numMin = $state(getInitialNumMin());
	let numMax = $state(getInitialNumMax());

	// Date filter state
	let dateFrom = $state(getInitialDateFrom());
	let dateTo = $state(getInitialDateTo());

	// Enum filter state
	let selectedEnums = $state<Set<string>>(getInitialEnums());

	// Auto-apply for text filter with debounce
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	function autoApplyTextFilter() {
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			applyFilter();
		}, 300);
	}

	function applyFilter() {
		let filter: FilterValue | null = null;

		if (type === 'text' && textValue.trim()) {
			filter = { type: 'text', value: textValue.trim(), matchMode: textMatchMode };
		} else if (type === 'number' && (numMin > numberMin || numMax < numberMax)) {
			filter = { type: 'number', min: numMin > numberMin ? numMin : undefined, max: numMax < numberMax ? numMax : undefined };
		} else if (type === 'date' && (dateFrom || dateTo)) {
			filter = { type: 'date', from: dateFrom || undefined, to: dateTo || undefined };
		} else if (type === 'enum' && selectedEnums.size < enumOptions.length && selectedEnums.size > 0) {
			filter = { type: 'enum', selected: Array.from(selectedEnums) };
		}

		onApply(filter);
	}

	function clearFilter() {
		textValue = '';
		textMatchMode = 'contains';
		numMin = numberMin;
		numMax = numberMax;
		dateFrom = '';
		dateTo = '';
		selectedEnums = new Set(enumOptions.map(o => o.value));
		onApply(null);
	}

	function toggleEnum(value: string) {
		if (selectedEnums.has(value)) {
			selectedEnums.delete(value);
		} else {
			selectedEnums.add(value);
		}
		selectedEnums = new Set(selectedEnums); // Trigger reactivity
		applyFilter(); // Instant apply for enum
	}

	function selectAllEnums() {
		selectedEnums = new Set(enumOptions.map(o => o.value));
		applyFilter();
	}

	function clearAllEnums() {
		selectedEnums = new Set();
		applyFilter();
	}

	// Click outside to close - but NOT when clicking on the filter button itself
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		// Don't close if clicking on the filter button that opened this popover
		if (target.closest('.filter-btn')) return;

		if (popoverElement && !popoverElement.contains(target)) {
			onClose();
		}
	}

	onMount(() => {
		// Use capture phase and add listener after a small delay to avoid immediate close
		const timer = setTimeout(() => {
			document.addEventListener('click', handleClickOutside, true);
		}, 100);

		return () => {
			clearTimeout(timer);
			document.removeEventListener('click', handleClickOutside, true);
			if (debounceTimer) clearTimeout(debounceTimer);
		};
	});
</script>

<div class="filter-popover" bind:this={popoverElement} transition:fade={{ duration: 100 }}>
	<div class="filter-header">
		<span class="filter-title">{$t('table.filter')}</span>
		<button type="button" class="reset-btn" onclick={clearFilter} title={$t('common.clear')}>
			<RotateCcw size={14} />
		</button>
	</div>

	<div class="filter-body">
		{#if type === 'text'}
			<div class="text-filter">
				<div class="search-input-wrapper">
					<Search size={14} class="search-icon" />
					<input
						type="text"
						class="filter-input"
						placeholder={$t('common.search')}
						bind:value={textValue}
						oninput={autoApplyTextFilter}
						id="text-filter-input"
					/>
					{#if textValue}
						<button type="button" class="clear-input-btn" onclick={() => { textValue = ''; applyFilter(); }}>
							<X size={12} />
						</button>
					{/if}
				</div>
				<select class="match-mode-select" bind:value={textMatchMode} onchange={applyFilter} id="text-match-mode-select">
					<option value="contains">{$t('filter.contains')}</option>
					<option value="startsWith">{$t('filter.startsWith')}</option>
					<option value="endsWith">{$t('filter.endsWith')}</option>
					<option value="equals">{$t('filter.equals')}</option>
				</select>
			</div>
		{:else if type === 'number'}
			<div class="number-filter">
				<div class="range-row">
					<label class="range-label" for="number-min-input">{$t('filter.min')}</label>
					<input type="number" class="range-input" bind:value={numMin} min={numberMin} max={numMax} onchange={applyFilter} id="number-min-input" />
				</div>
				<div class="range-row">
					<label class="range-label" for="number-max-input">{$t('filter.max')}</label>
					<input type="number" class="range-input" bind:value={numMax} min={numMin} max={numberMax} onchange={applyFilter} id="number-max-input" />
				</div>
			</div>
		{:else if type === 'date'}
			<div class="date-filter">
				<div class="date-row">
					<label class="date-label" for="date-from-input">{$t('filter.from')}</label>
					<input type="date" class="date-input" bind:value={dateFrom} onchange={applyFilter} id="date-from-input" />
				</div>
				<div class="date-row">
					<label class="date-label" for="date-to-input">{$t('filter.to')}</label>
					<input type="date" class="date-input" bind:value={dateTo} onchange={applyFilter} id="date-to-input" />
				</div>
			</div>
		{:else if type === 'enum'}
			<div class="enum-filter">
				<div class="enum-actions">
					<button type="button" class="enum-action-btn" onclick={selectAllEnums}>{$t('common.selectAll')}</button>
					<button type="button" class="enum-action-btn" onclick={clearAllEnums}>{$t('common.clearAll')}</button>
				</div>
				<div class="enum-list">
					{#each enumOptions as option}
						<button type="button" class="enum-option" onclick={() => toggleEnum(option.value)}>
							<span class="enum-checkbox" class:checked={selectedEnums.has(option.value)}>
								{#if selectedEnums.has(option.value)}
									<Check size={12} />
								{/if}
							</span>
							<span class="enum-label">{option.label}</span>
						</button>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.filter-popover { position: absolute; top: 100%; left: 0; margin-top: 0.25rem; min-width: 220px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); z-index: 60; }
	:global(.dark) .filter-popover { background: #1e293b; border-color: #334155; }
	.filter-header { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0.75rem; border-bottom: 1px solid #e2e8f0; }
	:global(.dark) .filter-header { border-bottom-color: #334155; }
	.filter-title { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
	:global(.dark) .filter-title { color: #94a3b8; }
	.reset-btn { display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border: none; border-radius: 4px; background: transparent; color: #64748b; cursor: pointer; transition: all 0.15s; }
	.reset-btn:hover { background: #f1f5f9; color: #0f172a; }
	:global(.dark) .reset-btn:hover { background: #334155; color: #f1f5f9; }
	.filter-body { padding: 0.75rem; }
	.search-input-wrapper { position: relative; display: flex; align-items: center; margin-bottom: 0.5rem; }
	.search-input-wrapper :global(.search-icon) { position: absolute; left: 0.5rem; color: #94a3b8; pointer-events: none; }
	.filter-input { width: 100%; padding: 0.375rem 1.75rem; font-size: 0.8125rem; border: 1px solid #e2e8f0; border-radius: 6px; background: white; color: #0f172a; }
	:global(.dark) .filter-input { background: #0f172a; border-color: #334155; color: #f1f5f9; }
	.filter-input:focus { outline: none; border-color: #1a4031; }
	:global(.dark) .filter-input:focus { border-color: #4ade80; }
	.clear-input-btn { position: absolute; right: 0.375rem; display: flex; align-items: center; justify-content: center; width: 18px; height: 18px; border: none; border-radius: 50%; background: #e2e8f0; color: #64748b; cursor: pointer; }
	.clear-input-btn:hover { background: #cbd5e1; color: #0f172a; }
	:global(.dark) .clear-input-btn { background: #475569; color: #94a3b8; }
	:global(.dark) .clear-input-btn:hover { background: #64748b; color: #f1f5f9; }
	.match-mode-select { width: 100%; padding: 0.375rem 0.5rem; font-size: 0.8125rem; border: 1px solid #e2e8f0; border-radius: 6px; background: white; color: #0f172a; cursor: pointer; }
	:global(.dark) .match-mode-select { background: #0f172a; border-color: #334155; color: #f1f5f9; }
	.number-filter, .date-filter { display: flex; flex-direction: column; gap: 0.5rem; }
	.range-row, .date-row { display: flex; align-items: center; gap: 0.5rem; }
	.range-label, .date-label { min-width: 35px; font-size: 0.75rem; color: #64748b; }
	:global(.dark) .range-label, :global(.dark) .date-label { color: #94a3b8; }
	.range-input, .date-input { flex: 1; padding: 0.375rem 0.5rem; font-size: 0.8125rem; border: 1px solid #e2e8f0; border-radius: 6px; background: white; color: #0f172a; }
	:global(.dark) .range-input, :global(.dark) .date-input { background: #0f172a; border-color: #334155; color: #f1f5f9; }
	.range-input:focus, .date-input:focus { outline: none; border-color: #1a4031; }
	:global(.dark) .range-input:focus, :global(.dark) .date-input:focus { border-color: #4ade80; }
	.enum-actions { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
	.enum-action-btn { flex: 1; padding: 0.25rem 0.5rem; font-size: 0.6875rem; border: 1px solid #e2e8f0; border-radius: 4px; background: #f8fafc; color: #64748b; cursor: pointer; transition: all 0.15s; }
	.enum-action-btn:hover { background: #f1f5f9; color: #0f172a; }
	:global(.dark) .enum-action-btn { background: #0f172a; border-color: #334155; color: #94a3b8; }
	:global(.dark) .enum-action-btn:hover { background: #1e293b; color: #f1f5f9; }
	.enum-list { max-height: 180px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; }
	:global(.dark) .enum-list { border-color: #334155; }
	.enum-option { display: flex; align-items: center; gap: 0.5rem; width: 100%; padding: 0.375rem 0.5rem; border: none; background: transparent; color: #475569; font-size: 0.8125rem; text-align: left; cursor: pointer; transition: background 0.15s; }
	.enum-option:hover { background: #f8fafc; }
	:global(.dark) .enum-option { color: #e2e8f0; }
	:global(.dark) .enum-option:hover { background: #334155; }
	.enum-checkbox { display: flex; align-items: center; justify-content: center; width: 16px; height: 16px; border: 1px solid #cbd5e1; border-radius: 3px; background: white; transition: all 0.15s; }
	.enum-checkbox.checked { background: #1a4031; border-color: #1a4031; color: white; }
	:global(.dark) .enum-checkbox { background: #0f172a; border-color: #475569; }
	:global(.dark) .enum-checkbox.checked { background: #4ade80; border-color: #4ade80; color: #0f172a; }
</style>
