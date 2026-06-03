<script lang="ts">
    /**
     * CurrencyChip — compact currency selector chip for WAC target currency.
     *
     * Shows current currency with flag/symbol or 🏳️ when null.
     * Click opens a small dropdown with available currencies.
     * Always fully opaque (never inherits parent opacity).
     */
    import {getCurrencyInfo} from '$lib/stores/currencyStore';
    import {formatCurrencyCodeHtml} from '$lib/utils/currencyFormat';

    interface Props {
        /** Current currency code — null shows placeholder flag */
        value: string | null;
        /** Available currencies for the dropdown */
        options: string[];
        /** Show loading spinner */
        loading?: boolean;
        /** Called when user selects a currency */
        onChange: (code: string) => void;
        /** data-testid */
        testid?: string;
    }

    let {value, options, loading = false, onChange, testid = 'currency-chip'}: Props = $props();

    let dropdownOpen = $state(false);

    let displayInfo = $derived(value ? getCurrencyInfo(value) : null);

    function select(code: string) {
        dropdownOpen = false;
        if (code !== value) onChange(code);
    }

    function toggle(e: MouseEvent) {
        e.preventDefault();
        e.stopPropagation();
        if (options.length > 1) dropdownOpen = !dropdownOpen;
    }

    function handleClickOutside(e: MouseEvent) {
        const target = e.target as HTMLElement;
        if (!target.closest(`[data-testid="${testid}"]`)) {
            dropdownOpen = false;
        }
    }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="relative inline-flex items-center opacity-100" data-testid={testid}>
    <!-- Chip button -->
    <button
        type="button"
        class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium
               bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200
               hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors
               {options.length <= 1 ? 'cursor-default' : 'cursor-pointer'}"
        onclick={toggle}
        data-testid="{testid}-btn"
    >
        {#if displayInfo}
            <span class="font-emoji">{displayInfo.flag_emoji}</span>
            <span>{displayInfo.code}</span>
        {:else}
            <span class="font-emoji">🏳️</span>
        {/if}
        {#if options.length > 1}
            <span class="text-[8px] ml-0.5">▼</span>
        {/if}
    </button>

    {#if loading}
        <span class="ml-0.5 text-[10px] text-gray-400 animate-pulse" data-testid="{testid}-loading">⏳</span>
    {/if}

    <!-- Dropdown -->
    {#if dropdownOpen}
        <div
            class="absolute top-full left-0 mt-1 z-50 min-w-[120px] rounded-md shadow-lg
                   bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600
                   py-1 text-[11px]"
            data-testid="{testid}-dropdown"
        >
            {#each options as code}
                {@const info = getCurrencyInfo(code)}
                <button
                    type="button"
                    class="w-full flex items-center gap-1.5 px-2 py-1 hover:bg-gray-50 dark:hover:bg-slate-700
                           {code === value ? 'bg-gray-50 dark:bg-slate-700 font-medium' : ''}"
                    onclick={() => select(code)}
                    data-testid="{testid}-option-{code}"
                >
                    <span class="font-emoji">{info.flag_emoji}</span>
                    <span>{info.symbol}</span>
                    <span class="text-gray-500 dark:text-gray-400">{info.code}</span>
                    {#if code === value}
                        <span class="ml-auto text-libre-green">✓</span>
                    {/if}
                </button>
            {/each}
        </div>
    {/if}
</div>
