<!--
  AssetEventSelect.svelte — Svelte 5

  Picker for linking a transaction to an asset event (DIVIDEND, INTEREST, etc.).
  Fetches events near the TX date and presents them in a SimpleSelect dropdown.
  Includes a range slider (±N days) persisted in localStorage.
-->
<script lang="ts">
    import {onDestroy} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {zodiosApi} from '$lib/api';

    interface Props {
        assetId: number;
        txDate: string;
        value: number | null;
        disabled?: boolean;
        onChange: (eventId: number | null) => void;
    }

    let {assetId, txDate, value, disabled = false, onChange}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    const LS_KEY = 'librefolio-event-picker-days';
    const DEFAULT_DAYS = 7;

    let daysRange = $state(loadDays());
    let events = $state<Array<{id: number; date: string; type: string; amount: string; code: string; notes: string | null}>>([]);
    let loading = $state(false);
    let fetchKey = $state('');

    function loadDays(): number {
        try {
            const v = localStorage.getItem(LS_KEY);
            if (v) {
                const n = Number(v);
                if (n >= 1 && n <= 90) return n;
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
    // Event type → emoji map
    // =========================================================================

    const typeIcons: Record<string, string> = {
        DIVIDEND: '💰',
        INTEREST: '🏦',
        SPLIT: '✂️',
        PRICE_ADJUSTMENT: '📊',
        MATURITY_SETTLEMENT: '📅',
    };

    function eventIcon(type: string): string {
        return typeIcons[type] ?? '📋';
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
        return {
            start: start.toISOString().slice(0, 10),
            end: end.toISOString().slice(0, 10),
        };
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
            console.error('[AssetEventSelect] fetch failed', err);
            events = [];
        } finally {
            loading = false;
        }
    }

    // Debounced fetch on dependency changes
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
    // Options building
    // =========================================================================

    let options = $derived.by<SelectOption[]>(() => {
        const none: SelectOption = {value: '', label: '—'};
        const mapped: SelectOption[] = events.map((e) => {
            const icon = eventIcon(e.type);
            const noteSuffix = e.notes ? ` ${e.notes}` : '';
            return {
                value: String(e.id),
                label: `${icon} ${e.date} — ${e.amount} ${e.code}${noteSuffix}`,
                icon,
            };
        });
        return [none, ...mapped];
    });

    // If current value is not in the fetched events (out of range), show it as selected but let user clear
    let selectValue = $derived(value != null ? String(value) : '');

    function handleChange(v: string) {
        onChange(v === '' ? null : Number(v));
    }

    function handleSlider(e: Event) {
        const v = Number((e.currentTarget as HTMLInputElement).value);
        daysRange = v;
        saveDays(v);
    }
</script>

<div class="flex flex-col gap-2" data-testid="tx-form-event-select">
    <div class="flex items-center gap-2">
        <span class="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">{$t('transactions.form.linkedEvent')}</span>
        <div class="flex-1">
            <SimpleSelect value={selectValue} {options} {disabled} {loading} placeholder={$t('transactions.form.eventPickerPlaceholder') || 'Select event...'} testId="tx-form-event-select" onchange={handleChange} compact />
        </div>
    </div>
    {#if !disabled}
        <div class="flex items-center gap-2 pl-32" data-testid="tx-form-event-slider">
            <span class="text-[10px] text-gray-400 dark:text-gray-500 whitespace-nowrap">± {daysRange}d</span>
            <input type="range" min="1" max="90" value={daysRange} oninput={handleSlider} class="flex-1 h-1 accent-libre-green cursor-pointer" />
        </div>
    {/if}
</div>
