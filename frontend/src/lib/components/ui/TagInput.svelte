<!--
  TagInput.svelte — Chip input with autocomplete dropdown.

  Usage:
    <TagInput value={tags} availableTags={allTags} onchange={(v) => tags = v} />

  Features:
  - Type text → Enter/Space/Comma → creates chip
  - Click × on chip → removes
  - Dropdown with filtered available tags
  - data-testid on all interactive elements
-->
<script lang="ts">
    import {ChevronDown, X} from 'lucide-svelte';

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
        onchange?.(next);
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter' || e.key === ',' || e.key === ' ') {
            if (inputBuffer.trim()) {
                e.preventDefault();
                addTag(inputBuffer);
                inputBuffer = '';
            }
        } else if (e.key === 'Escape') {
            dropdownOpen = false;
        } else if (e.key === 'Backspace' && inputBuffer === '' && value.length > 0) {
            removeTag(value.length - 1);
        }
    }

    function handleSuggestionClick(tag: string) {
        addTag(tag);
        inputBuffer = '';
        dropdownOpen = false;
        inputEl?.focus();
    }

    function toggleDropdown() {
        dropdownOpen = !dropdownOpen;
        if (dropdownOpen) inputEl?.focus();
    }

    function handleBlur() {
        // Delay to allow click on dropdown items
        setTimeout(() => {
            dropdownOpen = false;
        }, 200);
    }
</script>

<div class="relative" data-testid="tag-input-wrapper">
    <div
        class="flex flex-wrap items-center gap-1.5 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg min-h-[38px] {disabled ? 'opacity-60 cursor-not-allowed' : ''}"
        data-testid="tag-input-container"
    >
        {#each value as tag, i}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200" data-testid={`tag-chip-${i}`}>
                {tag}
                {#if !disabled}
                    <button type="button" class="text-gray-400 hover:text-red-500 leading-none" aria-label="remove tag" onclick={() => removeTag(i)} data-testid={`tag-chip-remove-${i}`}>
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
                onfocus={() => (dropdownOpen = true)}
                onblur={handleBlur}
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
        <div class="absolute z-50 mt-1 w-full max-h-48 overflow-y-auto bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg" data-testid="tag-input-dropdown">
            {#each suggestions as suggestion}
                <button
                    type="button"
                    class="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-700 dark:text-gray-200 transition-colors"
                    onmousedown={(e) => { e.preventDefault(); handleSuggestionClick(suggestion); }}
                    data-testid={`tag-suggestion-${suggestion}`}
                >
                    {suggestion}
                </button>
            {/each}
        </div>
    {/if}
</div>


