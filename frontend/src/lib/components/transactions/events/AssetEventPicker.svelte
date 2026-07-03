<!--
  AssetEventPicker.svelte — Svelte 5

  Custom dropdown picker for linking a transaction to an asset event.
  Self-contained: no SimpleSelect dependency.
  Features:
  - Fixed-position dropdown (avoids overflow clipping)
  - Integrated slider header (± N days range)
  - Card-style event items with emoji, date, amount, delta
  - Keyboard navigation (↑↓ Enter Escape)
  - Click-outside to close
-->
<script lang="ts">
    import {onDestroy} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {Plus} from 'lucide-svelte';

    interface Props {
        assetId: number;
        txDate: string;
        value: number | null;
        disabled?: boolean;
        onChange: (eventId: number | null) => void;
        txCash?: {amount: string; code: string} | null;
        onCreateNew?: () => void;
    }

    let {assetId, txDate, value, disabled = false, onChange, txCash = null, onCreateNew}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    const LS_KEY = 'librefolio-event-picker-days';
    const DEFAULT_DAYS = 7;
    const MAX_DAYS = 30;

    let isOpen = $state(false);
    let daysRange = $state(loadDays());
    let events: Array<{id: number; date: string; type: string; amount: string; code: string; notes: string | null}> = $state([]);
    let loading = $state(false);
    let fetchKey = $state('');
    let highlightedIndex = $state(-1);

    // DOM refs
    let triggerRef: HTMLButtonElement | null = $state(null);
    let dropdownRef: HTMLDivElement | null = $state(null);

    // Fixed positioning state
    let fixedTop = $state(0);
    let fixedLeft = $state(0);
    let fixedWidth = $state(0);
    let dropdownMaxHeight = $state('15rem');
    let computedPosition: 'top' | 'bottom' = $state('bottom');

    const _uid = `event-picker-${Math.random().toString(36).slice(2, 8)}`;

    function loadDays(): number {
        try {
            const v = localStorage.getItem(LS_KEY);
            if (v) {
                const n = Number(v);
                if (n >= 1 && n <= MAX_DAYS) return n;
            }
        } catch {}
        return DEFAULT_DAYS;
    }

    function saveDays(n: number) {
        try {
            localStorage.setItem(LS_KEY, String(n));
        } catch {}
    }

    // =========================================================================
    // Event type config
    // =========================================================================

    const typeConfig: Record<string, {icon: string; bg: string}> = {
        DIVIDEND: {icon: '💰', bg: 'bg-amber-50 dark:bg-amber-900/20'},
        INTEREST: {icon: '🏦', bg: 'bg-blue-50 dark:bg-blue-900/20'},
        SPLIT: {icon: '✂️', bg: 'bg-purple-50 dark:bg-purple-900/20'},
        PRICE_ADJUSTMENT: {icon: '📊', bg: 'bg-gray-100 dark:bg-gray-800'},
        MATURITY_SETTLEMENT: {icon: '📅', bg: 'bg-green-50 dark:bg-green-900/20'},
    };

    function getTypeConfig(type: string) {
        return typeConfig[type] ?? {icon: '📋', bg: 'bg-gray-100 dark:bg-gray-800'};
    }

    function typeLabel(type: string): string {
        const key = `assets.events.types.${type}`;
        const translated = $t(key);
        return translated !== key ? translated : type.replace(/_/g, ' ').toLowerCase();
    }

    // =========================================================================
    // Fetch logic
    // =========================================================================

    let fetchTimer: ReturnType<typeof setTimeout> | null = null;

    function computeDateRange(date: string, days: number): {start: string; end: string} {
        const d = new Date(date);
        const start = new Date(d);
        start.setDate(start.getDate() - days);
        const end = new Date(d);
        end.setDate(end.getDate() + days);
        return {start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10)};
    }

    async function fetchEvents(aid: number, date: string, days: number) {
        const key = `${aid}:${date}:${days}`;
        if (key === fetchKey) return;
        fetchKey = key;
        loading = true;
        try {
            const {start, end} = computeDateRange(date, days);
            const resp = (await zodiosApi.query_events_bulk_api_v1_assets_events_query_post([{asset_id: aid, date_range: {start, end}}])) as any;
            const items = resp?.items?.[0]?.events ?? [];
            events = items.map((e: any) => ({
                id: e.id,
                date: e.date,
                type: e.type,
                amount: e.value?.amount ?? '0',
                code: e.value?.code ?? '',
                notes: e.notes ?? null,
            }));
        } catch (err) {
            console.error('[AssetEventPicker] fetch failed', err);
            events = [];
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        const aid = assetId;
        const date = txDate;
        const days = daysRange;
        if (!aid || !date) {
            events = [];
            fetchKey = '';
            return;
        }
        if (fetchTimer) clearTimeout(fetchTimer);
        fetchTimer = setTimeout(() => fetchEvents(aid, date, days), 200);
    });

    onDestroy(() => {
        if (fetchTimer) clearTimeout(fetchTimer);
    });

    // =========================================================================
    // Delta calculation
    // =========================================================================

    interface DeltaResult {
        value: number;
        label: string;
        color: string;
        crossCurrency: boolean;
    }

    function computeDelta(eventAmount: string, eventCode: string): DeltaResult | null {
        if (!txCash?.amount) return null;
        const txAmt = parseFloat(txCash.amount);
        const evtAmt = parseFloat(eventAmount);
        if (isNaN(txAmt) || isNaN(evtAmt) || txAmt === 0) return null;

        const diff = txAmt - evtAmt;
        const crossCurrency = txCash.code !== eventCode;
        const close = Math.abs(diff) < 0.05;

        return {
            value: diff,
            label: `${diff >= 0 ? '+' : ''}${diff.toFixed(2)}${crossCurrency ? ' ≠' : ''}`,
            color: crossCurrency ? 'text-gray-400' : close ? 'text-green-600 dark:text-green-400' : 'text-amber-500 dark:text-amber-400',
            crossCurrency,
        };
    }

    function shortDate(dateStr: string): string {
        try {
            const d = new Date(dateStr + 'T00:00:00');
            return d.toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'});
        } catch {
            return dateStr;
        }
    }

    // =========================================================================
    // Selected event data
    // =========================================================================

    // Pinned event: fetched independently when value points to an event outside the slider range
    let pinnedEvent: {id: number; date: string; type: string; amount: string; code: string; notes: string | null} | null = $state(null);

    let selectedEvent = $derived.by(() => {
        if (value == null) return null;
        return events.find((e) => e.id === value) ?? pinnedEvent ?? null;
    });

    // When value changes or events load, if the selected event isn't in the list, fetch it directly
    $effect(() => {
        if (value == null) {
            pinnedEvent = null;
            return;
        }
        if (events.find((e) => e.id === value)) {
            pinnedEvent = null;
            return;
        }
        if (loading) return;
        // Fetch the specific event by querying a wide range around txDate
        if (!assetId || !txDate) return;
        const fetchPinned = async () => {
            try {
                const {start, end} = computeDateRange(txDate, 365);
                const resp = (await zodiosApi.query_events_bulk_api_v1_assets_events_query_post([{asset_id: assetId, date_range: {start, end}}])) as any;
                const items = resp?.items?.[0]?.events ?? [];
                const found = items.find((e: any) => e.id === value);
                if (found) {
                    pinnedEvent = {
                        id: found.id,
                        date: found.date,
                        type: found.type,
                        amount: found.value?.amount ?? '0',
                        code: found.value?.code ?? '',
                        notes: found.notes ?? null,
                    };
                }
            } catch {}
        };
        fetchPinned();
    });

    // Items list: "none" first, then events
    type PickerItem = {type: 'none'} | {type: 'event'; event: (typeof events)[0]};
    let items = $derived.by<PickerItem[]>(() => {
        const list: PickerItem[] = [{type: 'none'}];
        for (const e of events) list.push({type: 'event', event: e});
        return list;
    });

    // =========================================================================
    // Dropdown positioning (fixed, like SimpleSelect)
    // =========================================================================

    function updateDropdownPosition() {
        if (!triggerRef) return;
        const rect = triggerRef.getBoundingClientRect();
        const padding = 20;
        const vh = window.innerHeight;
        const vw = window.innerWidth;

        const spaceBelow = vh - rect.bottom - padding;
        const spaceAbove = rect.top - padding;
        computedPosition = spaceBelow < 200 && spaceAbove > spaceBelow ? 'top' : 'bottom';

        const available = computedPosition === 'top' ? spaceAbove : spaceBelow;
        dropdownMaxHeight = `${Math.max(140, Math.min(280, available))}px`;

        fixedWidth = Math.max(rect.width, 240);
        fixedLeft = Math.max(padding, Math.min(rect.left, vw - fixedWidth - padding));
        fixedTop = computedPosition === 'top' ? rect.top : rect.bottom + 4;
    }

    function adjustForTopPosition(el: HTMLDivElement) {
        if (!triggerRef || computedPosition !== 'top') return;
        const rect = triggerRef.getBoundingClientRect();
        const dropdownRect = el.getBoundingClientRect();
        fixedTop = rect.top - dropdownRect.height - 4;
    }

    // =========================================================================
    // Open / Close
    // =========================================================================

    function open() {
        if (disabled) return;
        updateDropdownPosition();
        isOpen = true;
        highlightedIndex = -1;
    }

    function close() {
        isOpen = false;
        highlightedIndex = -1;
    }

    function toggle() {
        if (isOpen) close();
        else open();
    }

    function selectItem(item: PickerItem) {
        if (item.type === 'none') {
            onChange(null);
        } else {
            onChange(item.event.id);
        }
        close();
    }

    // Click outside
    $effect(() => {
        if (!isOpen) return;
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as Node;
            if (triggerRef && triggerRef.contains(target)) return;
            const dd = document.querySelector(`[data-event-picker-dropdown="${_uid}"]`);
            if (dd && dd.contains(target)) return;
            close();
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    });

    // =========================================================================
    // Keyboard navigation
    // =========================================================================

    function handleKeydown(e: KeyboardEvent) {
        if (!isOpen) {
            if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
                e.preventDefault();
                open();
            }
            return;
        }
        switch (e.key) {
            case 'Escape':
                e.preventDefault();
                close();
                triggerRef?.focus();
                break;
            case 'ArrowDown':
                e.preventDefault();
                highlightedIndex = Math.min(highlightedIndex + 1, items.length - 1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                highlightedIndex = Math.max(highlightedIndex - 1, 0);
                break;
            case 'Enter':
                e.preventDefault();
                if (highlightedIndex >= 0 && highlightedIndex < items.length) {
                    selectItem(items[highlightedIndex]);
                }
                break;
        }
    }

    // Slider handler
    function handleSlider(e: Event) {
        const v = Number((e.currentTarget as HTMLInputElement).value);
        daysRange = v;
        saveDays(v);
    }
</script>

<div class="flex flex-col gap-1" data-testid="tx-form-event-select">
    <span class="text-xs text-gray-500 dark:text-gray-400">{$t('common.linkedEvent')}</span>
    <div class="relative">
        <!-- Trigger button -->
        <button
            bind:this={triggerRef}
            type="button"
            class="w-full flex items-center gap-2 px-3 py-2 text-left bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg text-sm transition-colors hover:border-libre-green focus:outline-none focus:ring-2 focus:ring-libre-green/30 disabled:opacity-60 disabled:cursor-not-allowed"
            {disabled}
            onclick={toggle}
            onkeydown={handleKeydown}
            role="combobox"
            aria-expanded={isOpen}
            aria-controls={_uid}
            aria-haspopup="listbox"
            data-testid="tx-form-event-picker-trigger"
        >
            {#if selectedEvent}
                {@const cfg = getTypeConfig(selectedEvent.type)}
                {@const delta = computeDelta(selectedEvent.amount, selectedEvent.code)}
                <span class="shrink-0 w-5 h-5 flex items-center justify-center {cfg.bg} rounded text-xs">{cfg.icon}</span>
                <span class="truncate text-xs flex-1"
                    >{shortDate(selectedEvent.date)}{#if selectedEvent.notes}
                        · {selectedEvent.notes}{/if}</span
                >
                {#if delta}
                    <span class="text-[10px] font-mono {delta.color} shrink-0">Δ{delta.label}</span>
                {/if}
            {:else}
                <span class="text-xs text-gray-400 italic flex-1">{$t('transactions.form.eventPickerNone') || 'No linked event'}</span>
            {/if}
            <svg class="w-3.5 h-3.5 text-gray-400 shrink-0 transition-transform {isOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
        </button>
    </div>
</div>

<!-- Fixed-position dropdown portal -->
{#if isOpen}
    <div
        bind:this={dropdownRef}
        use:adjustForTopPosition
        data-event-picker-dropdown={_uid}
        id={_uid}
        class="fixed z-[9999] bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-xl overflow-hidden"
        style="top: {fixedTop}px; left: {fixedLeft}px; width: {fixedWidth}px; max-height: {dropdownMaxHeight};"
        role="listbox"
        data-testid="tx-form-event-picker-dropdown"
    >
        <!-- Slider header -->
        <div class="flex items-center gap-2 px-3 py-2 border-b border-gray-100 dark:border-slate-700 bg-gray-50 dark:bg-slate-900/50" data-testid="tx-form-event-slider">
            <span class="text-[10px] text-gray-500 dark:text-gray-400 whitespace-nowrap font-mono">± {daysRange}d</span>
            <input type="range" min="1" max={MAX_DAYS} value={daysRange} oninput={handleSlider} class="flex-1 h-1 accent-libre-green cursor-pointer" />
        </div>

        <!-- Items list -->
        <div class="overflow-y-auto" style="max-height: calc({dropdownMaxHeight} - 3rem);">
            {#if loading}
                <div class="px-3 py-4 text-center text-xs text-gray-400">⏳ {$t('common.loading') || 'Loading...'}</div>
            {:else if events.length === 0 && value == null}
                <!-- No events + nothing selected: show "none" as only option + empty hint -->
                <button type="button" class="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-slate-700 {highlightedIndex === 0 ? 'bg-gray-50 dark:bg-slate-700' : ''}" onclick={() => selectItem({type: 'none'})} role="option" aria-selected={value == null}>
                    <div class="flex items-center gap-2 text-gray-400 dark:text-gray-500">
                        <span class="w-6 h-6 flex items-center justify-center rounded border border-dashed border-gray-300 dark:border-gray-600 text-[10px]">∅</span>
                        <span class="text-sm italic">{$t('transactions.form.eventPickerNone') || 'No linked event'}</span>
                        {#if value == null}<span class="ml-auto text-xs text-libre-green">✓</span>{/if}
                    </div>
                </button>
                <div class="px-3 py-3 text-center text-[11px] text-gray-400 dark:text-gray-500">
                    😶 {$t('common.noResults') || 'No events found in this range'}
                </div>
            {:else}
                {#each items as item, idx}
                    {#if item.type === 'none'}
                        <button type="button" class="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors {highlightedIndex === idx ? 'bg-gray-50 dark:bg-slate-700' : ''}" onclick={() => selectItem(item)} role="option" aria-selected={value == null}>
                            <div class="flex items-center gap-2 text-gray-400 dark:text-gray-500">
                                <span class="w-6 h-6 flex items-center justify-center rounded border border-dashed border-gray-300 dark:border-gray-600 text-[10px]">∅</span>
                                <span class="text-sm italic">{$t('transactions.form.eventPickerNone') || 'No linked event'}</span>
                                {#if value == null}<span class="ml-auto text-xs text-libre-green">✓</span>{/if}
                            </div>
                        </button>
                    {:else}
                        {@const ev = item.event}
                        {@const cfg = getTypeConfig(ev.type)}
                        {@const delta = computeDelta(ev.amount, ev.code)}
                        {@const fmtAmt = ev.amount && ev.amount !== '0' ? formatDecimalForDisplay(ev.amount) : null}
                        {@const isSelected = value === ev.id}
                        <button
                            type="button"
                            class="w-full px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors {highlightedIndex === idx ? 'bg-gray-50 dark:bg-slate-700' : ''} {isSelected ? 'bg-libre-green/5' : ''}"
                            onclick={() => selectItem(item)}
                            role="option"
                            aria-selected={isSelected}
                        >
                            <div class="flex items-center gap-2 min-w-0">
                                <span class="shrink-0 w-6 h-6 flex items-center justify-center {cfg.bg} rounded text-sm">{cfg.icon}</span>
                                <div class="flex-1 min-w-0">
                                    <div class="text-sm font-medium truncate">{shortDate(ev.date)} · {ev.notes || typeLabel(ev.type)}</div>
                                </div>
                                {#if fmtAmt}
                                    <span class="text-xs font-mono text-gray-500 dark:text-gray-400 shrink-0">{fmtAmt} {ev.code}</span>
                                {/if}
                                {#if delta}
                                    <span class="text-[10px] font-mono shrink-0 {delta.color}">Δ{delta.label}</span>
                                {/if}
                                {#if isSelected}<span class="text-xs text-libre-green shrink-0">✓</span>{/if}
                            </div>
                        </button>
                    {/if}
                {/each}
            {/if}
        </div>
        {#if onCreateNew}
            <button
                type="button"
                class="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm text-libre-green hover:bg-libre-green/10 dark:hover:bg-libre-green/20 border-t border-gray-100 dark:border-slate-700 transition-colors"
                onclick={() => {
                    close();
                    onCreateNew?.();
                }}
                data-testid="tx-form-event-create-new"
            >
                <Plus size={14} class="shrink-0" />
                <span class="font-medium">{$t('transactions.form.eventPickerCreateNew') || '+ New event'}</span>
            </button>
        {/if}
    </div>
{/if}
