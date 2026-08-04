<!--
  SimpleSelect.svelte - Svelte 5

  Simple dropdown select without search functionality.
  Supports keyboard navigation and custom item rendering via snippets.
  Uses position:fixed for dropdown to avoid clipping by overflow:hidden/auto parents.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import type {SelectOption} from './types';
    import {Check, ChevronDown} from 'lucide-svelte';
    import {_} from '$lib/i18n';

    interface Props {
        /** Currently selected value */
        value: string;
        /** Available options */
        options: SelectOption[];
        /** Placeholder when no value selected */
        placeholder?: string;
        /** Disable the select */
        disabled?: boolean;
        /** Show loading state */
        loading?: boolean;
        /** Position of dropdown */
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        /** Custom class for container */
        class?: string;
        /** Test ID for E2E testing (adds -button suffix to trigger) */
        testId?: string;
        /** Accessible field label, combined with the selected option on the trigger */
        ariaLabel?: string;
        /** Optional stable test ID for each dropdown option button */
        optionTestId?: (option: SelectOption) => string | undefined;
        /** Custom item rendering */
        item?: Snippet<[SelectOption]>;
        /** Custom selected item rendering (for trigger) */
        selectedItem?: Snippet<[SelectOption]>;
        /** Change callback */
        onchange?: (value: string) => void;
        /** Compact mode: smaller padding, text-xs, thinner border */
        compact?: boolean;
        /** Show chevron icon in trigger button (default: true) */
        showChevron?: boolean;
        /** Keep dropdown width equal to the trigger instead of sizing to content */
        matchTriggerWidth?: boolean;
    }

    let {value = $bindable(''), options, placeholder = '', disabled = false, loading = false, dropdownPosition = 'bottom', class: className = '', testId, ariaLabel, optionTestId, item, selectedItem, onchange, compact = false, showChevron = true, matchTriggerWidth = false}: Props = $props();

    // Internal state
    let isOpen = $state(false);
    let highlightedIndex = $state(-1);
    let containerRef: HTMLDivElement | null = $state(null);
    let triggerRef: HTMLButtonElement | null = $state(null);
    let computedPosition: 'top' | 'bottom' = $state('bottom');
    let dropdownMaxHeight: string = $state('15rem');

    // Fixed positioning state (viewport-relative coordinates)
    let fixedTop = $state(0);
    let fixedLeft = $state(0);
    let fixedWidth = $state(0);

    // Derived state
    const componentId = $props.id();
    const listboxId = `${componentId}-listbox`;
    let selectedOption = $derived(options.find((o) => o.value === value));
    let defaultAccessibleLabel = $derived(placeholder || $_('common.select'));
    let listboxAccessibleLabel = $derived(ariaLabel?.trim() || defaultAccessibleLabel);
    let triggerAccessibleName = $derived(buildAccessibleName([listboxAccessibleLabel, selectedOption?.label ?? defaultAccessibleLabel, selectedOption?.searchText]));
    let activeDescendantId = $derived(isOpen && highlightedIndex >= 0 && options[highlightedIndex] ? getOptionId(options[highlightedIndex]) : undefined);
    let dropdownWidth = $derived(matchTriggerWidth ? `${fixedWidth}px` : 'max-content');

    function buildAccessibleName(parts: readonly (string | undefined)[]): string {
        const uniqueParts = parts
            .map((part) => part?.trim())
            .filter((part): part is string => Boolean(part))
            .filter((part, index, allParts) => allParts.indexOf(part) === index);
        return uniqueParts.join(', ');
    }

    function getOptionId(option: SelectOption): string {
        const valueId = option.value === '' ? '__empty__' : encodeURIComponent(option.value);
        return `${listboxId}-option-${valueId}`;
    }

    function getFirstEnabledIndex(candidateOptions: readonly SelectOption[]): number {
        return candidateOptions.findIndex((option) => !option.disabled);
    }

    function getLastEnabledIndex(candidateOptions: readonly SelectOption[]): number {
        for (let index = candidateOptions.length - 1; index >= 0; index--) {
            if (!candidateOptions[index].disabled) return index;
        }
        return -1;
    }

    function getInitialHighlightedIndex(candidateOptions: readonly SelectOption[], selectedValue: string): number {
        const selectedIndex = candidateOptions.findIndex((option) => option.value === selectedValue && !option.disabled);
        return selectedIndex >= 0 ? selectedIndex : getFirstEnabledIndex(candidateOptions);
    }

    function getAdjacentEnabledIndex(candidateOptions: readonly SelectOption[], currentIndex: number, direction: 1 | -1): number {
        if (currentIndex < 0) return direction === 1 ? getFirstEnabledIndex(candidateOptions) : getLastEnabledIndex(candidateOptions);
        for (let index = currentIndex + direction; index >= 0 && index < candidateOptions.length; index += direction) {
            if (!candidateOptions[index].disabled) return index;
        }
        return currentIndex;
    }

    // Compute dropdown position when opening
    function updateDropdownPosition() {
        if (!containerRef) {
            computedPosition = dropdownPosition === 'top' ? 'top' : 'bottom';
            dropdownMaxHeight = '15rem';
            return;
        }

        const rect = containerRef.getBoundingClientRect();
        const padding = 20;
        const vw = window.innerWidth;
        const vh = window.innerHeight;

        // Fixed positioning: always use viewport bounds
        const spaceBelow = vh - rect.bottom - padding;
        const spaceAbove = rect.top - padding;

        if (dropdownPosition === 'top') {
            computedPosition = 'top';
        } else if (dropdownPosition === 'bottom') {
            computedPosition = 'bottom';
        } else {
            // auto
            computedPosition = spaceBelow < 200 && spaceAbove > spaceBelow ? 'top' : 'bottom';
        }

        const available = computedPosition === 'top' ? spaceAbove : spaceBelow;
        dropdownMaxHeight = `${Math.max(120, Math.min(240, available))}px`;

        // Calculate fixed coordinates
        fixedWidth = Math.max(rect.width, 0);
        fixedLeft = Math.max(padding, Math.min(rect.left, vw - fixedWidth - padding));
        if (computedPosition === 'top') {
            // Will be positioned above the trigger — defer to after render for actual dropdown height
            fixedTop = rect.top;
        } else {
            fixedTop = rect.bottom + 4;
        }
    }

    /**
     * Svelte action: after the dropdown is mounted, re-measure and adjust for 'top' positioning.
     */
    function adjustFixedPositionAction(dropdownEl: HTMLDivElement) {
        if (!containerRef) return;
        const rect = containerRef.getBoundingClientRect();
        const dropdownRect = dropdownEl.getBoundingClientRect();
        if (computedPosition === 'top') {
            fixedTop = rect.top - dropdownRect.height - 4;
        }
    }

    // Keep active descendant valid when selection/options change.
    $effect(() => {
        highlightedIndex = isOpen ? getInitialHighlightedIndex(options, value) : -1;
    });

    // Close on click outside
    $effect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef && !containerRef.contains(event.target as Node)) {
                // Also check if click is inside the fixed dropdown portal
                const dropdown = document.getElementById(listboxId);
                if (dropdown && dropdown.contains(event.target as Node)) return;
                closeDropdown();
            }
        };

        document.addEventListener('mousedown', handleClickOutside, true);
        return () => document.removeEventListener('mousedown', handleClickOutside, true);
    });

    // Re-position dropdown on scroll/resize while open
    $effect(() => {
        if (!isOpen) return;
        const handleReposition = () => {
            updateDropdownPosition();
        };
        window.addEventListener('scroll', handleReposition, true);
        window.addEventListener('resize', handleReposition);
        return () => {
            window.removeEventListener('scroll', handleReposition, true);
            window.removeEventListener('resize', handleReposition);
        };
    });

    function openDropdown() {
        if (disabled || loading) return;
        updateDropdownPosition();
        isOpen = true;
        highlightedIndex = getInitialHighlightedIndex(options, value);
    }

    function closeDropdown() {
        isOpen = false;
        highlightedIndex = -1;
    }

    function toggleDropdown() {
        if (isOpen) {
            closeDropdown();
        } else {
            openDropdown();
        }
    }

    function selectOption(option: SelectOption) {
        if (option.disabled) return;
        value = option.value;
        onchange?.(option.value);
        closeDropdown();
        triggerRef?.focus();
    }

    function handleKeydown(event: KeyboardEvent) {
        if (disabled || loading) return;

        if (!isOpen) {
            if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                openDropdown();
            }
            return;
        }

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                highlightedIndex = getAdjacentEnabledIndex(options, highlightedIndex, 1);
                break;
            case 'ArrowUp':
                event.preventDefault();
                highlightedIndex = getAdjacentEnabledIndex(options, highlightedIndex, -1);
                break;
            case 'Home':
                event.preventDefault();
                highlightedIndex = getFirstEnabledIndex(options);
                break;
            case 'End':
                event.preventDefault();
                highlightedIndex = getLastEnabledIndex(options);
                break;
            case 'Enter':
            case ' ':
                event.preventDefault();
                if (highlightedIndex >= 0 && options[highlightedIndex]) {
                    selectOption(options[highlightedIndex]);
                }
                break;
            case 'Escape':
                event.preventDefault();
                closeDropdown();
                break;
            case 'Tab':
                closeDropdown();
                break;
        }
    }
</script>

<div bind:this={containerRef} class="relative {className}" data-testid={testId}>
    <!-- Trigger Button -->
    <button
        bind:this={triggerRef}
        class="w-full flex items-center justify-between {compact ? 'px-1.5 py-0.5 text-xs' : 'px-3 py-2 text-sm'} border rounded-lg transition-all text-left
               {disabled || loading
            ? 'bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-gray-400 cursor-not-allowed border-gray-200 dark:border-slate-700'
            : 'bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500'}
               {isOpen ? 'ring-2 ring-libre-green border-libre-green' : ''}"
        data-testid={testId ? `${testId}-button` : undefined}
        role="combobox"
        aria-label={triggerAccessibleName}
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-haspopup="listbox"
        aria-autocomplete="none"
        aria-activedescendant={activeDescendantId}
        {disabled}
        onclick={toggleDropdown}
        onkeydown={handleKeydown}
        type="button"
    >
        {#if selectedOption}
            {#if selectedItem}
                {@render selectedItem(selectedOption)}
            {:else if selectedOption.icon}
                <span class="truncate emoji-flag">{selectedOption.icon} {selectedOption.label}</span>
            {:else}
                <span class="truncate">{selectedOption.label}</span>
            {/if}
        {:else}
            <span class="text-gray-400">{placeholder || $_('common.select')}</span>
        {/if}
        {#if showChevron}
            <ChevronDown class="ml-2 flex-shrink-0 text-gray-400 transition-transform {isOpen ? 'rotate-180' : ''}" size={compact ? 12 : 16} />
        {/if}
    </button>

    <!-- Dropdown Menu — fixed position to escape overflow clipping -->
    {#if isOpen}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            id={listboxId}
            role="listbox"
            aria-label={listboxAccessibleLabel}
            data-simpleselect-dropdown={listboxId}
            data-testid={testId ? `${testId}-dropdown` : undefined}
            class="fixed z-[9999] bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700
                   rounded-lg shadow-lg overflow-y-auto"
            style="top: {fixedTop}px; left: {fixedLeft}px; min-width: {fixedWidth}px; width: {dropdownWidth}; max-width: calc(100vw - 40px); max-height: {dropdownMaxHeight};"
            onwheel={(e) => e.stopPropagation()}
            ontouchmove={(e) => e.stopPropagation()}
            use:adjustFixedPositionAction
        >
            {#if loading}
                <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    {$_('common.loading')}
                </div>
            {:else if options.length === 0}
                <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    {$_('common.noData')}
                </div>
            {:else}
                {#each options as option, index (option.value)}
                    <button
                        type="button"
                        role="option"
                        id={getOptionId(option)}
                        tabindex="-1"
                        aria-selected={value === option.value}
                        aria-disabled={option.disabled ?? false}
                        data-testid={optionTestId?.(option)}
                        onclick={() => selectOption(option)}
                        onmousedown={(event) => event.preventDefault()}
                        onmouseenter={() => {
                            if (!option.disabled) highlightedIndex = index;
                        }}
                        disabled={option.disabled}
                        class="w-full flex items-center justify-between px-3 py-2 text-sm text-left transition-colors
                               {option.disabled ? 'opacity-50 cursor-not-allowed' : ''}
                               {index === highlightedIndex ? 'bg-libre-green/10 dark:bg-libre-green/20' : 'hover:bg-gray-50 dark:hover:bg-slate-700'}
                               {value === option.value ? 'bg-libre-green/5 dark:bg-libre-green/10 text-libre-green dark:text-green-400' : 'text-gray-900 dark:text-gray-100'}"
                    >
                        {#if item}
                            <div class="flex-1 min-w-0">
                                {@render item(option)}
                            </div>
                        {:else if option.icon}
                            <span class="truncate emoji-flag">{option.icon} {option.label}</span>
                        {:else}
                            <span class="truncate">{option.label}</span>
                        {/if}
                        {#if value === option.value}
                            <Check size={16} class="ml-2 flex-shrink-0 text-libre-green dark:text-green-400" />
                        {/if}
                    </button>
                {/each}
            {/if}
        </div>
    {/if}
</div>
