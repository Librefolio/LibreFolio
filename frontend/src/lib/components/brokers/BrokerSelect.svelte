<!--
  BrokerSelect - Custom dropdown for broker selection with:
  - Broker icon display
  - Inline search field (replaces button text when open)
  - Mobile-friendly styling
-->
<script lang="ts">
	import { ChevronDown, Check, Search } from 'lucide-svelte';
	import { t } from '$lib/i18n';
	import BrokerIcon from './BrokerIcon.svelte';

	/**
	 * Minimum broker info needed for the select component.
	 * This allows accepting both full Broker objects and simplified BrokerInfo.
	 */
	interface BrokerSelectItem {
		id: number;
		name: string;
		icon_url?: string | null;
		portal_url?: string | null;
		default_import_plugin?: string | null;
	}

	interface Props {
		brokers: BrokerSelectItem[];
		value: number | null;
		placeholder?: string;
		disabled?: boolean;
		dropdownDirection?: 'up' | 'down';
		onchange?: (brokerId: number | null) => void;
	}

	let { brokers, value, placeholder, disabled = false, dropdownDirection = 'up', onchange }: Props = $props();

	// Unique ID for this instance
	const instanceId = Math.random().toString(36).substring(2, 9);

	// Dropdown state
	let showDropdown = $state(false);
	let dropdownRef = $state<HTMLDivElement | null>(null);
	let searchInputRef = $state<HTMLInputElement | null>(null);
	let highlightedIndex = $state(-1);

	// Search state
	let searchQuery = $state('');

	// Filtered brokers based on search
	let filteredBrokers = $derived(
		searchQuery.trim() === ''
			? brokers
			: brokers.filter(b => b.name.toLowerCase().includes(searchQuery.toLowerCase()))
	);

	// Get selected broker
	let selectedBroker = $derived(
		value != null ? brokers.find(b => b.id === value) : null
	);

	// Close dropdown on click outside - using mousedown for better UX
	$effect(() => {
		if (showDropdown) {
			const handleClickOutside = (e: MouseEvent) => {
				if (dropdownRef && !dropdownRef.contains(e.target as Node)) {
					closeDropdown();
				}
			};
			document.addEventListener('mousedown', handleClickOutside, true);
			return () => document.removeEventListener('mousedown', handleClickOutside, true);
		}
	});

	// Listen for other BrokerSelect instances opening
	$effect(() => {
		const handleOtherOpen = (e: CustomEvent<string>) => {
			if (e.detail !== instanceId && showDropdown) {
				closeDropdown();
			}
		};
		window.addEventListener('broker-select-open' as any, handleOtherOpen);
		return () => window.removeEventListener('broker-select-open' as any, handleOtherOpen);
	});

	// Focus search input when dropdown opens
	$effect(() => {
		if (showDropdown && searchInputRef) {
			setTimeout(() => searchInputRef?.focus(), 10);
		}
	});

	function closeDropdown() {
		showDropdown = false;
		highlightedIndex = -1;
		searchQuery = '';
	}

	function openDropdown() {
		showDropdown = true;
		searchQuery = '';
		highlightedIndex = -1;
		window.dispatchEvent(new CustomEvent('broker-select-open', { detail: instanceId }));
	}

	function toggleDropdown(e: MouseEvent) {
		e.stopPropagation();
		if (disabled) return;
		if (showDropdown) {
			closeDropdown();
		} else {
			openDropdown();
		}
	}

	function selectBroker(brokerId: number) {
		onchange?.(brokerId);
		closeDropdown();
	}

	function handleSearchKeyDown(e: KeyboardEvent) {
		switch (e.key) {
			case 'Escape':
				closeDropdown();
				break;
			case 'ArrowDown':
				e.preventDefault();
				highlightedIndex = Math.min(highlightedIndex + 1, filteredBrokers.length - 1);
				scrollToHighlighted();
				break;
			case 'ArrowUp':
				e.preventDefault();
				highlightedIndex = Math.max(highlightedIndex - 1, 0);
				scrollToHighlighted();
				break;
			case 'Enter':
				e.preventDefault();
				if (highlightedIndex >= 0 && highlightedIndex < filteredBrokers.length) {
					selectBroker(filteredBrokers[highlightedIndex].id);
				}
				break;
		}
	}

	function scrollToHighlighted() {
		setTimeout(() => {
			const dropdown = dropdownRef?.querySelector('.broker-options');
			const highlighted = dropdown?.querySelector('.dropdown-option.highlighted');
			if (highlighted) {
				highlighted.scrollIntoView({ block: 'nearest' });
			}
		}, 0);
	}

	// Handle keyboard on the combobox button
	function handleButtonKeyDown(e: KeyboardEvent) {
		switch (e.key) {
			case 'Enter':
			case ' ':
				e.preventDefault();
				if (!showDropdown) {
					openDropdown();
				}
				break;
			case 'Escape':
				if (showDropdown) {
					closeDropdown();
				}
				break;
			case 'ArrowDown':
				e.preventDefault();
				if (!showDropdown) {
					openDropdown();
				}
				break;
		}
	}
</script>

<div
	class="broker-select"
	class:disabled
	bind:this={dropdownRef}
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="select-btn"
		class:open={showDropdown}
		onclick={toggleDropdown}
		onkeydown={handleButtonKeyDown}
		role="combobox"
		tabindex={disabled ? -1 : 0}
		aria-expanded={showDropdown}
		aria-haspopup="listbox"
		aria-controls={`broker-listbox-${instanceId}`}
	>
		{#if showDropdown}
			<!-- Search mode: show search icon + input -->
			<Search size={14} class="search-icon" />
			<input
				type="text"
				class="inline-search"
				placeholder={$t('common.search') || 'Search...'}
				bind:value={searchQuery}
				bind:this={searchInputRef}
				onkeydown={handleSearchKeyDown}
				onclick={(e) => e.stopPropagation()}
			/>
		{:else if selectedBroker}
			<!-- Selected broker display -->
			<div class="selected-broker">
				<BrokerIcon
					iconUrl={selectedBroker.icon_url}
					portalUrl={selectedBroker.portal_url}
					pluginCode={selectedBroker.default_import_plugin}
					altText={selectedBroker.name}
					size="sm"
				/>
				<span class="broker-name">{selectedBroker.name}</span>
			</div>
		{:else}
			<!-- Placeholder -->
			<span class="placeholder">{placeholder || $t('uploads.selectBroker')}</span>
		{/if}
		<span class="chevron-icon" class:open={showDropdown}>
			<ChevronDown size={14} />
		</span>
	</div>

	{#if showDropdown}
		<div class="broker-dropdown" class:dropdown-up={dropdownDirection === 'up'} class:dropdown-down={dropdownDirection === 'down'}>
			<div class="broker-options" id={`broker-listbox-${instanceId}`} role="listbox">
				{#if filteredBrokers.length === 0}
					<div class="no-results">{$t('common.noResults') || 'No results'}</div>
				{:else}
					{#each filteredBrokers as broker, index}
						<button
							type="button"
							class="dropdown-option"
							class:selected={value === broker.id}
							class:highlighted={highlightedIndex === index}
							onmousedown={() => selectBroker(broker.id)}
							onmouseenter={() => highlightedIndex = index}
						>
							<BrokerIcon
								iconUrl={broker.icon_url}
								portalUrl={broker.portal_url}
								pluginCode={broker.default_import_plugin}
								altText={broker.name}
								size="sm"
							/>
							<span class="option-name">{broker.name}</span>
							{#if value === broker.id}
								<span class="check-mark"><Check size={14} /></span>
							{/if}
						</button>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.broker-select {
		position: relative;
		min-width: 180px;
	}

	.broker-select.disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.select-btn {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 0.5rem 0.75rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.15s;
		gap: 0.5rem;
		min-height: 38px;
	}

	.select-btn:hover {
		border-color: #cbd5e1;
		background: #f8fafc;
	}

	.select-btn.open {
		border-color: #1a4031;
		box-shadow: 0 0 0 2px rgba(26, 64, 49, 0.15);
	}

	:global(.dark) .select-btn {
		background: #0f172a;
		border-color: #334155;
		color: #e2e8f0;
	}

	:global(.dark) .select-btn:hover {
		border-color: #475569;
		background: #1e293b;
	}

	:global(.dark) .select-btn.open {
		border-color: #4ade80;
		box-shadow: 0 0 0 2px rgba(74, 222, 128, 0.15);
	}

	/* Search icon */
	.select-btn :global(.search-icon) {
		flex-shrink: 0;
		color: #94a3b8;
	}

	/* Inline search input - flex-grow without forcing expansion */
	.inline-search {
		flex: 1 1 0;
		width: 0;
		border: none;
		background: transparent;
		font-size: 0.875rem;
		outline: none;
		color: inherit;
		padding: 0;
		min-width: 0;
	}

	.inline-search::placeholder {
		color: #94a3b8;
	}

	:global(.dark) .inline-search::placeholder {
		color: #64748b;
	}

	.selected-broker {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex: 1;
		min-width: 0;
	}

	.broker-name {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		font-size: 0.875rem;
	}

	.placeholder {
		color: #94a3b8;
		font-size: 0.875rem;
	}

	:global(.dark) .placeholder {
		color: #64748b;
	}

	.chevron-icon {
		flex-shrink: 0;
		color: #64748b;
		transition: transform 0.15s;
		display: flex;
		align-items: center;
	}

	.chevron-icon.open {
		transform: rotate(180deg);
	}

	/* Dropdown */
	.broker-dropdown {
		position: absolute;
		left: 0;
		right: 0;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		overflow: hidden;
		z-index: 100;
	}

	.broker-dropdown.dropdown-up {
		bottom: 100%;
		margin-bottom: 0.25rem;
	}

	.broker-dropdown.dropdown-down {
		top: 100%;
		margin-top: 0.25rem;
	}

	:global(.dark) .broker-dropdown {
		background: #1e293b;
		border-color: #334155;
	}

	/* Options list - max 3 visible */
	.broker-options {
		max-height: 132px;
		overflow-y: auto;
	}

	.no-results {
		padding: 0.75rem;
		text-align: center;
		color: #94a3b8;
		font-size: 0.875rem;
	}

	.dropdown-option {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 100%;
		padding: 0.5rem 0.75rem;
		background: transparent;
		border: none;
		cursor: pointer;
		transition: background 0.1s;
		text-align: left;
	}

	.dropdown-option:hover,
	.dropdown-option.highlighted {
		background: #f1f5f9;
	}

	.dropdown-option.selected {
		background: #ecfdf5;
	}

	.dropdown-option.selected.highlighted {
		background: #d1fae5;
	}

	:global(.dark) .dropdown-option:hover,
	:global(.dark) .dropdown-option.highlighted {
		background: #334155;
	}

	:global(.dark) .dropdown-option.selected {
		background: rgba(74, 222, 128, 0.15);
	}

	:global(.dark) .dropdown-option.selected.highlighted {
		background: rgba(74, 222, 128, 0.25);
	}

	.option-name {
		flex: 1;
		font-size: 0.875rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.check-mark {
		flex-shrink: 0;
		color: #059669;
		display: flex;
		align-items: center;
	}

	:global(.dark) .check-mark {
		color: #4ade80;
	}

	/* Mobile adjustments */
	@media (max-width: 640px) {
		.broker-select {
			min-width: 150px;
		}

		.select-btn {
			padding: 0.375rem 0.5rem;
		}

		.dropdown-option {
			padding: 0.625rem 0.5rem;
		}
	}
</style>
