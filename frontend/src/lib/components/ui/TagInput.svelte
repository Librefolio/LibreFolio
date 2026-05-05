<!--
  TagInput.svelte — Chip input with autocomplete dropdown.

  Usage:
    <TagInput value={tags} availableTags={allTags} onchange={(v) => tags = v} />

  Features:
  - Type text → Enter/Space/Comma → creates chip
  - Click × on chip → removes
  - Dropdown with filtered available tags
  - Arrow Up/Down navigate suggestions, Enter selects highlighted
  - Arrow Left/Right navigate between tag chips (when input empty)
  - Backspace/Delete on focused chip removes it
  - Colored chips via getStringColor()
  - data-testid on all interactive elements
-->
<script lang="ts">
    import {ChevronDown, X} from 'lucide-svelte';
    import {getStringBadgeStyle} from '$lib/utils/colors';

    interface Props {
        value: string[];
        availableTags?: string[];
        placeholder?: string;
        disabled?: boolean;
        onchange?: (value: string[]) => void;
    }

    let {value = [], availableTags = [], placeholder = '', disabled = false, onchange}: Props = $props();

    let inputBuffer = $state('');
    let dropdownOpen = $state(false);
    let inputEl: HTMLInputElement | undefined = $state();
    let highlightedIndex = $state(-1);
    /** Index of the currently focused tag chip (-1 = none, cursor in input). */
    let focusedTagIndex = $state(-1);

    // Reset highlight when input changes
    $effect(() => {
        void inputBuffer;
        highlightedIndex = -1;
    });

    let suggestions = $derived.by<string[]>(() => {
        const q = inputBuffer.trim().toLowerCase();
        const used = new Set(value);
        return availableTags
            .filter((tg) => !used.has(tg) && (q === '' || tg.toLowerCase().includes(q)))
            .slice(0, 20);
    });

    function addTag(raw: string) {
        const v = raw.trim();
        if (!v) return;
        if (value.includes(v)) return;
        const next = [...value, v];
        onchange?.(next);
    }

    function removeTag(idx: number) {
        const next = [...value];
        next.splice(idx, 1);
        // Adjust focused tag index after removal
        if (focusedTagIndex >= next.length) {
            focusedTagIndex = next.length > 0 ? next.length - 1 : -1;
        }
        onchange?.(next);
        // If no tags left to focus, return focus to input
        if (next.length === 0) {
            focusedTagIndex = -1;
            inputEl?.focus();
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        // Tag chip navigation (only when input is empty)
        if (inputBuffer === '' && value.length > 0) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                if (focusedTagIndex === -1) {
                    // From input, move to last tag
                    focusedTagIndex = value.length - 1;
                } else if (focusedTagIndex > 0) {
                    focusedTagIndex--;
                }
                return;
            }
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                if (focusedTagIndex >= 0 && focusedTagIndex < value.length - 1) {
                    focusedTagIndex++;
                } else {
                    // From last tag or beyond, return to input
                    focusedTagIndex = -1;
                    inputEl?.focus();
                }
                return;
            }
            if ((e.key === 'Backspace' || e.key === 'Delete') && focusedTagIndex >= 0) {
                e.preventDefault();
                removeTag(focusedTagIndex);
                return;
            }
        }

        // Suggestion navigation (ArrowUp/Down)
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (!dropdownOpen) dropdownOpen = true;
            highlightedIndex = Math.min(highlightedIndex + 1, suggestions.length - 1);
            // Scroll into view
            const el = document.querySelector(`[data-testid="tag-suggestion-idx-${highlightedIndex}"]`);
            el?.scrollIntoView({block: 'nearest'});
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlightedIndex = Math.max(highlightedIndex - 1, -1);
            if (highlightedIndex >= 0) {
                const el = document.querySelector(`[data-testid="tag-suggestion-idx-${highlightedIndex}"]`);
                el?.scrollIntoView({block: 'nearest'});
            }
        } else if (e.key === 'Enter' || e.key === ',' || e.key === ' ') {
            e.preventDefault();
            if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
                addTag(suggestions[highlightedIndex]);
                inputBuffer = '';
                highlightedIndex = -1;
            } else if (inputBuffer.trim()) {
                addTag(inputBuffer);
                inputBuffer = '';
            }
        } else if (e.key === 'Escape') {
            highlightedIndex = -1;
            focusedTagIndex = -1;
            dropdownOpen = false;
        } else if (e.key === 'Backspace' && inputBuffer === '' && value.length > 0 && focusedTagIndex === -1) {
            // No tag focused → remove last tag (original behavior)
            removeTag(value.length - 1);
        }
    }

    function handleSuggestionClick(tag: string) {
        addTag(tag);
        inputBuffer = '';
        highlightedIndex = -1;
        dropdownOpen = false;
        inputEl?.focus();
    }

    function toggleDropdown() {
        dropdownOpen = !dropdownOpen;
        if (dropdownOpen) inputEl?.focus();
    }

    function handleBlur(e: FocusEvent) {
        // If focus moves to an element inside our wrapper, don't close
        const wrapper = (e.currentTarget as HTMLElement)?.closest('[data-testid="tag-input-wrapper"]');
        const related = e.relatedTarget as HTMLElement | null;
        if (related && wrapper?.contains(related)) return;
        dropdownOpen = false;
        highlightedIndex = -1;
        focusedTagIndex = -1;
    }

    function handleChipClick(idx: number) {
        focusedTagIndex = idx;
        inputEl?.focus(); // Keep keyboard focus on input for keydown handling
    }
</script>

<div class="relative" data-testid="tag-input-wrapper">
    <div
        class="flex flex-wrap items-center gap-1.5 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg min-h-[38px] {disabled ? 'opacity-60 cursor-not-allowed' : ''}"
        data-testid="tag-input-container"
    >
        {#each value as tag, i}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <span
                class="tag-chip inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded cursor-pointer transition-all {i === focusedTagIndex ? 'ring-2 ring-blue-500 ring-offset-1 dark:ring-offset-slate-800' : ''}"
                style={getStringBadgeStyle(tag)}
                data-testid={`tag-chip-${i}`}
                onclick={() => handleChipClick(i)}
            >
                {tag}
                {#if !disabled}
                    <button type="button" class="opacity-70 hover:opacity-100 leading-none" aria-label="remove tag" onclick={(e) => { e.stopPropagation(); removeTag(i); }} data-testid={`tag-chip-remove-${i}`}>
                        <X size={12} />
                    </button>
                {/if}
            </span>
        {/each}
        {#if !disabled}
            <input
                bind:this={inputEl}
                type="text"
                autocomplete="off"
                class="flex-1 min-w-[5rem] bg-transparent text-xs outline-none"
                {placeholder}
                bind:value={inputBuffer}
                onkeydown={handleKeydown}
                onfocus={() => { dropdownOpen = true; }}
                onblur={handleBlur}
                oninput={() => { focusedTagIndex = -1; }}
                data-testid="tag-input-field"
            />
            {#if availableTags.length > 0}
                <button
                    type="button"
                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0 p-0.5"
                    onclick={toggleDropdown}
                    data-testid="tag-input-toggle"
                    aria-label="Toggle tag suggestions"
                >
                    <ChevronDown size={14} class={dropdownOpen ? 'rotate-180 transition-transform' : 'transition-transform'} />
                </button>
            {/if}
        {/if}
    </div>

    {#if dropdownOpen && suggestions.length > 0 && !disabled}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="absolute z-50 mt-1 w-full max-h-48 overflow-y-auto bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg"
            data-testid="tag-input-dropdown"
            role="listbox"
        >
            {#each suggestions as suggestion, idx}
                <button
                    type="button"
                    class="w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200 transition-colors {idx === highlightedIndex ? 'bg-blue-100 dark:bg-blue-900/50' : 'hover:bg-gray-100 dark:hover:bg-slate-700'}"
                    onmousedown={(e) => { e.preventDefault(); handleSuggestionClick(suggestion); }}
                    data-testid={`tag-suggestion-${suggestion}`}
                    aria-selected={idx === highlightedIndex}
                    role="option"
                >
                    {suggestion}
                </button>
            {/each}
        </div>
    {/if}
</div>

<style>
    .tag-chip {
        background: var(--badge-bg, #e2e8f0);
        color: var(--badge-text, #334155);
    }
    :global(.dark) .tag-chip {
        background: var(--badge-dark-bg, #334155);
        color: var(--badge-dark-text, #e2e8f0);
    }
</style>

