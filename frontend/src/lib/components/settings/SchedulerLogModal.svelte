<!--
  SchedulerLogModal.svelte — Svelte 5

  Modal showing scheduler execution history.
  Fetches from GET /api/v1/settings/scheduler/log?since=ISO.
  Client-side filters for job type and status; temporal filter drives API param.
  Collapsible per-item detail (auto-expanded if errors > 0).
  Uses SyncModalBase-like patterns for result item rendering.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl, getFxProviderIconUrl, parseProviderChain, PROVIDER_COLORS, DEFAULT_PROVIDER_COLOR} from '$lib/utils/providerHelpers';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {ChevronDown, ChevronRight, CheckCircle, XCircle, ClipboardList, X} from 'lucide-svelte';

    // =========================================================================
    // Types matching backend JSONL format
    // =========================================================================

    interface LogItemCurrentPrice {
        asset_id: number;
        name: string;
        ok: boolean;
        error?: string;
        icon_url?: string;
    }

    interface LogItemHistory {
        asset_id?: number;
        name?: string;
        pair?: string;
        base?: string;
        quote?: string;
        status: string;
        provider?: string;
        points_changed?: number;
        prices_changed?: number;
        events_changed?: number;
        errors?: string[];
        icon_url?: string;
    }

    interface LogEntry {
        ts: string;
        job: string;
        duration_s: number;
        status: string;
        summary: {
            ok?: number;
            err?: number;
            assets_ok?: number;
            assets_err?: number;
            fx_ok?: number;
            fx_err?: number;
        };
        items?: LogItemCurrentPrice[];
        assets?: LogItemHistory[];
        fx?: LogItemHistory[];
    }

    // =========================================================================
    // Props & State
    // =========================================================================

    interface Props {
        open: boolean;
    }

    let {open = $bindable(false)}: Props = $props();

    let entries = $state<LogEntry[]>([]);
    let loading = $state(false);
    let filterJob = $state('all');
    let filterStatus = $state('all');
    let filterTime = $state('24h');
    let expandedKeys = $state<Set<string>>(new Set());

    // =========================================================================
    // Filter options with emojis
    // =========================================================================

    let jobSelectOptions = $derived([
        {value: 'all', label: $_('settings.global.scheduler.log.allJobs')},
        {value: 'current_price', label: '💰 ' + $_('settings.global.scheduler.log.currentPrice')},
        {value: 'history_sync', label: '📊 ' + $_('settings.global.scheduler.log.historySync')},
    ]);

    let statusSelectOptions = $derived([
        {value: 'all', label: $_('settings.global.scheduler.log.allStatuses')},
        {value: 'ok', label: '🟢 ' + $_('settings.global.scheduler.log.ok')},
        {value: 'partial', label: '🟡 ' + $_('settings.global.scheduler.log.partial')},
        {value: 'error', label: '🔴 ' + $_('settings.global.scheduler.log.error')},
    ]);

    let timeSelectOptions = $derived([
        {value: 'all', label: '🕐 ' + $_('settings.global.scheduler.log.allTime')},
        {value: '1h', label: $_('settings.global.scheduler.log.last1h')},
        {value: '6h', label: $_('settings.global.scheduler.log.last6h')},
        {value: '24h', label: $_('settings.global.scheduler.log.last24h')},
        {value: '7d', label: $_('settings.global.scheduler.log.last7d')},
        {value: '30d', label: $_('settings.global.scheduler.log.last30d')},
    ]);

    // =========================================================================
    // Derived
    // =========================================================================

    function getSinceParam(): string | undefined {
        const now = Date.now();
        switch (filterTime) {
            case '1h':
                return new Date(now - 3600_000).toISOString();
            case '6h':
                return new Date(now - 6 * 3600_000).toISOString();
            case '24h':
                return new Date(now - 24 * 3600_000).toISOString();
            case '7d':
                return new Date(now - 7 * 24 * 3600_000).toISOString();
            case '30d':
                return new Date(now - 30 * 24 * 3600_000).toISOString();
            default:
                return undefined;
        }
    }

    let filteredEntries = $derived(
        entries.filter((e) => {
            if (filterJob !== 'all' && e.job !== filterJob) return false;
            if (filterStatus !== 'all' && e.status !== filterStatus) return false;
            return true;
        }),
    );

    // =========================================================================
    // Data fetching
    // =========================================================================

    // Fetch on open and refetch when time filter changes
    $effect(() => {
        if (open) {
            // Track filterTime to refetch when it changes
            void filterTime;
            expandedKeys = new Set();
            ensureAssetProvidersCached();
            fetchEntries();
        }
    });

    async function fetchEntries() {
        loading = true;
        try {
            const params: Record<string, string> = {};
            const since = getSinceParam();
            if (since) params.since = since;

            const resp = await zodiosApi.axios.get('/api/v1/settings/scheduler/log', {params});
            const data = resp.data as {entries: LogEntry[]};
            entries = data.entries || [];
        } catch (e) {
            console.error('Failed to fetch scheduler log:', e);
        } finally {
            loading = false;
        }
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    function entryKey(e: LogEntry): string {
        return `${e.ts}_${e.job}`;
    }

    function toggleEntry(e: LogEntry) {
        const key = entryKey(e);
        const newSet = new Set(expandedKeys);
        if (newSet.has(key)) {
            newSet.delete(key);
        } else {
            newSet.add(key);
        }
        expandedKeys = newSet;
    }

    function isExpanded(e: LogEntry): boolean {
        return expandedKeys.has(entryKey(e));
    }

    function statusDotClass(status: string): string {
        switch (status) {
            case 'ok':
                return 'bg-green-500';
            case 'partial':
                return 'bg-yellow-500';
            case 'error':
                return 'bg-red-500';
            default:
                return 'bg-gray-400';
        }
    }

    function jobLabel(job: string): string {
        switch (job) {
            case 'current_price':
                return '💰 ' + $_('settings.global.scheduler.log.currentPrice');
            case 'history_sync':
                return '📊 ' + $_('settings.global.scheduler.log.historySync');
            default:
                return job;
        }
    }

    function formatTimestamp(iso: string): string {
        try {
            return new Intl.DateTimeFormat(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            }).format(new Date(iso));
        } catch {
            return iso;
        }
    }

    function formatDuration(seconds: number): string {
        if (!seconds && seconds !== 0) return '—';
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        const m = Math.floor(seconds / 60);
        const s = Math.round(seconds % 60);
        return `${m}m${s}s`;
    }

    function summaryText(entry: LogEntry): string {
        const s = entry.summary;
        if (entry.job === 'current_price') {
            const ok = s.ok ?? 0;
            const err = s.err ?? 0;
            const total = ok + err;
            if (err === 0) return `${ok}/${total} ✓`;
            return `${ok}/${total} ✓ · ${err} ✗`;
        }
        // history_sync
        const aOk = s.assets_ok ?? 0;
        const aErr = s.assets_err ?? 0;
        const fOk = s.fx_ok ?? 0;
        const fErr = s.fx_err ?? 0;
        const parts = [];
        if (aOk + aErr > 0) parts.push(`${aOk}/${aOk + aErr} assets`);
        if (fOk + fErr > 0) parts.push(`${fOk}/${fOk + fErr} FX`);
        if (aErr + fErr > 0) parts.push(`${aErr + fErr} ✗`);
        return parts.join(' · ');
    }

    /** First N names for preview */
    function previewNames(entry: LogEntry, max = 3): string {
        const names: string[] = [];
        if (entry.items) {
            for (const it of entry.items) names.push(it.name);
        }
        if (entry.assets) {
            for (const a of entry.assets) names.push(a.name || '?');
        }
        if (entry.fx) {
            for (const f of entry.fx) names.push(f.pair || '?');
        }
        if (names.length <= max) return names.join(', ');
        return names.slice(0, max).join(', ') + ` (+${names.length - max})`;
    }

    function hasDetail(entry: LogEntry): boolean {
        return (entry.items?.length ?? 0) > 0 || (entry.assets?.length ?? 0) > 0 || (entry.fx?.length ?? 0) > 0;
    }

    /** Copy text to clipboard and show a toast */
    async function copyErrorToClipboard(text: string) {
        try {
            await navigator.clipboard.writeText(text);
            toasts.info($_('common.copiedToClipboard'));
        } catch {
            /* clipboard not available */
        }
    }

    /** Long-press timer for mobile copy */
    let longPressTimer: ReturnType<typeof setTimeout> | null = null;

    function handleTouchStart(text: string) {
        longPressTimer = setTimeout(() => copyErrorToClipboard(text), 500);
    }

    function handleTouchEnd() {
        if (longPressTimer) {
            clearTimeout(longPressTimer);
            longPressTimer = null;
        }
    }
</script>

<ModalBase {open} maxWidth="2xl" testId="scheduler-log-modal" onRequestClose={() => (open = false)}>
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
        <div class="flex items-center gap-2.5">
            <div class="flex items-center justify-center w-9 h-9 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <ClipboardList class="text-blue-600 dark:text-blue-400" size={18} />
            </div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {$_('settings.global.scheduler.log.title')}
            </h2>
        </div>
        <button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" onclick={() => (open = false)}>
            <X size={18} />
        </button>
    </div>

    <!-- Body -->
    <div class="px-6 py-4 space-y-3">
        <!-- Filters -->
        <div class="flex items-center gap-3 flex-wrap">
            <SimpleSelect value={filterJob} options={jobSelectOptions} compact testId="scheduler-log-filter-job" onchange={(v) => (filterJob = v)} />
            <SimpleSelect value={filterStatus} options={statusSelectOptions} compact testId="scheduler-log-filter-status" onchange={(v) => (filterStatus = v)} />
            <SimpleSelect value={filterTime} options={timeSelectOptions} compact testId="scheduler-log-filter-time" onchange={(v) => (filterTime = v)} />
        </div>

        <!-- Entries -->
        <div class="space-y-2 max-h-[60vh] overflow-y-auto pr-1" data-testid="scheduler-log-entries">
            {#if loading && entries.length === 0}
                <div class="flex justify-center py-8">
                    <span class="w-6 h-6 border-2 border-gray-300 border-t-libre-green rounded-full animate-spin"></span>
                </div>
            {:else if filteredEntries.length === 0}
                <p class="text-center text-sm text-gray-500 dark:text-gray-400 py-8">
                    {$_('settings.global.scheduler.log.noEntries')}
                </p>
            {:else}
                {#each filteredEntries as entry (entryKey(entry))}
                    {@const expanded = isExpanded(entry)}
                    {@const detail = hasDetail(entry)}

                    <div class="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden" data-testid="scheduler-log-entry">
                        <!-- Entry header (clickable if has detail) -->
                        {#if detail}
                            <button type="button" class="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-slate-800 cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-left" onclick={() => toggleEntry(entry)}>
                                <span class="w-2.5 h-2.5 rounded-full shrink-0 {statusDotClass(entry.status)}"></span>
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 flex-wrap">
                                        <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{jobLabel(entry.job)}</span>
                                        <span class="text-xs text-gray-400 dark:text-gray-500">·</span>
                                        <span class="text-xs text-gray-500 dark:text-gray-400">{formatTimestamp(entry.ts)}</span>
                                        <span class="text-xs text-gray-400 dark:text-gray-500">·</span>
                                        <span class="text-xs text-gray-400 dark:text-gray-500">{formatDuration(entry.duration_s)}</span>
                                    </div>
                                    <div class="flex items-center gap-2 mt-0.5">
                                        <span class="text-xs font-medium {entry.status === 'ok' ? 'text-green-600 dark:text-green-400' : entry.status === 'partial' ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}">
                                            {summaryText(entry)}
                                        </span>
                                        <span class="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[300px]">
                                            {previewNames(entry)}
                                        </span>
                                    </div>
                                </div>
                                <span class="text-gray-400 dark:text-gray-500 shrink-0">
                                    {#if expanded}
                                        <ChevronDown size={16} />
                                    {:else}
                                        <ChevronRight size={16} />
                                    {/if}
                                </span>
                            </button>
                        {:else}
                            <div class="flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-slate-800">
                                <span class="w-2.5 h-2.5 rounded-full shrink-0 {statusDotClass(entry.status)}"></span>
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 flex-wrap">
                                        <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{jobLabel(entry.job)}</span>
                                        <span class="text-xs text-gray-400 dark:text-gray-500">·</span>
                                        <span class="text-xs text-gray-500 dark:text-gray-400">{formatTimestamp(entry.ts)}</span>
                                        <span class="text-xs text-gray-400 dark:text-gray-500">·</span>
                                        <span class="text-xs text-gray-400 dark:text-gray-500">{formatDuration(entry.duration_s)}</span>
                                    </div>
                                    <span class="text-xs font-medium {entry.status === 'ok' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
                                        {summaryText(entry)}
                                    </span>
                                </div>
                            </div>
                        {/if}

                        <!-- Collapsible detail -->
                        {#if expanded && detail}
                            <div class="px-4 py-3 border-t border-gray-200 dark:border-slate-700 space-y-3" data-testid="scheduler-log-entry-detail">
                                <!-- current_price items (table) -->
                                {#if entry.items && entry.items.length > 0}
                                    <div>
                                        <h4 class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                                            💰 {$_('settings.global.scheduler.log.currentPrice')}
                                        </h4>
                                        <table class="w-full text-xs">
                                            <thead>
                                                <tr class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                                                    <th class="text-left py-1 w-5"></th>
                                                    <th class="text-left py-1">{$_('settings.global.scheduler.log.colName')}</th>
                                                    <th class="text-left py-1">{$_('settings.global.scheduler.log.colDetail')}</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {#each entry.items as item}
                                                    <tr class="border-t border-gray-100 dark:border-slate-700/50">
                                                        <td class="py-1 pr-2">
                                                            {#if item.ok}
                                                                <CheckCircle size={13} class="text-green-500" />
                                                            {:else}
                                                                <XCircle size={13} class="text-red-500" />
                                                            {/if}
                                                        </td>
                                                        <td class="py-1 pr-2">
                                                            <span class="font-medium text-gray-700 dark:text-gray-300">{item.name}</span>
                                                        </td>
                                                        <td class="py-1">
                                                            {#if !item.ok && item.error}
                                                                <Tooltip text={item.error} position="top" maxWidth="500px">
                                                                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                                                                    <span class="text-red-500 truncate max-w-[250px] cursor-help inline-block" ondblclick={() => copyErrorToClipboard(item.error ?? '')} ontouchstart={() => handleTouchStart(item.error ?? '')} ontouchend={handleTouchEnd}
                                                                        >— {item.error}</span
                                                                    >
                                                                </Tooltip>
                                                            {:else}
                                                                <span class="text-green-600 dark:text-green-400">✓</span>
                                                            {/if}
                                                        </td>
                                                    </tr>
                                                {/each}
                                            </tbody>
                                        </table>
                                    </div>
                                {/if}

                                <!-- history_sync assets (table) -->
                                {#if entry.assets && entry.assets.length > 0}
                                    <div>
                                        <h4 class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                                            📈 {$_('settings.global.scheduler.log.assetsSection')}
                                        </h4>
                                        <table class="w-full text-xs">
                                            <thead>
                                                <tr class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                                                    <th class="text-left py-1 w-5"></th>
                                                    <th class="text-left py-1">{$_('settings.global.scheduler.log.colName')}</th>
                                                    <th class="text-left py-1">{$_('settings.global.scheduler.log.colProvider')}</th>
                                                    <th class="text-left py-1">{$_('settings.global.scheduler.log.colDelta')}</th>
                                                    <th class="text-left py-1"></th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {#each entry.assets as item}
                                                    {@const provIconUrl = item.provider ? getAssetProviderIconUrl(item.provider) : null}
                                                    <tr class="border-t border-gray-100 dark:border-slate-700/50">
                                                        <td class="py-1 pr-2">
                                                            {#if item.status === 'ok'}
                                                                <CheckCircle size={13} class="text-green-500" />
                                                            {:else}
                                                                <XCircle size={13} class="text-red-500" />
                                                            {/if}
                                                        </td>
                                                        <td class="py-1 pr-2">
                                                            <div class="flex items-center gap-1.5">
                                                                {#if item.icon_url}
                                                                    <img src={item.icon_url} alt="" class="w-4 h-4 rounded-sm object-contain shrink-0" />
                                                                {/if}
                                                                <span class="font-medium text-gray-700 dark:text-gray-300">{item.name || '?'}</span>
                                                            </div>
                                                        </td>
                                                        <td class="py-1 pr-2">
                                                            {#if item.provider}
                                                                <span class="inline-flex items-center gap-1 text-gray-400 dark:text-gray-500">
                                                                    {#if provIconUrl}
                                                                        <img src={provIconUrl} alt="" class="w-3.5 h-3.5 rounded-sm object-contain" />
                                                                    {/if}
                                                                    {item.provider}
                                                                </span>
                                                            {/if}
                                                        </td>
                                                        <td class="py-1 pr-2 text-left whitespace-nowrap">
                                                            {#if item.status === 'ok'}
                                                                {#if (item.prices_changed ?? 0) > 0}
                                                                    <span class="text-emerald-600 dark:text-emerald-400">+{item.prices_changed}📈</span>
                                                                {/if}
                                                                {#if (item.events_changed ?? 0) > 0}
                                                                    <span class="text-blue-600 dark:text-blue-400 ml-1">+{item.events_changed}📋</span>
                                                                {/if}
                                                                {#if (item.prices_changed ?? 0) === 0 && (item.events_changed ?? 0) === 0 && item.points_changed != null}
                                                                    <span class="text-emerald-600 dark:text-emerald-400">+{item.points_changed}Δ</span>
                                                                {/if}
                                                            {/if}
                                                        </td>
                                                        <td class="py-1">
                                                            {#if item.errors && item.errors.length > 0}
                                                                <Tooltip text={item.errors.join('\n')} position="top" maxWidth="500px">
                                                                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                                                                    <span
                                                                        class="text-red-500 truncate max-w-[200px] cursor-help inline-block"
                                                                        ondblclick={() => copyErrorToClipboard(item.errors?.join('; ') ?? '')}
                                                                        ontouchstart={() => handleTouchStart(item.errors?.join('; ') ?? '')}
                                                                        ontouchend={handleTouchEnd}>— {item.errors[0]}</span
                                                                    >
                                                                </Tooltip>
                                                            {/if}
                                                        </td>
                                                    </tr>
                                                {/each}
                                            </tbody>
                                        </table>
                                    </div>
                                {/if}

                                <!-- history_sync FX (table) -->
                                {#if entry.fx && entry.fx.length > 0}
                                    <div>
                                        <h4 class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                                            💱 {$_('settings.global.scheduler.log.fxSection')}
                                        </h4>
                                        <table class="w-full text-xs">
                                            <thead>
                                                <tr class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                                                    <th class="text-left py-1 w-5"></th>
                                                    <th class="text-left py-1">{$_('settings.global.scheduler.log.colPair')}</th>
                                                    <th class="text-left py-1">{$_('settings.global.scheduler.log.colProvider')}</th>
                                                    <th class="text-left py-1">{$_('settings.global.scheduler.log.colDelta')}</th>
                                                    <th class="text-left py-1"></th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {#each entry.fx as item}
                                                    {@const chain = parseProviderChain(item.provider)}
                                                    {@const baseFlag = item.base ? getCurrencyInfo(item.base).flag_emoji : ''}
                                                    {@const quoteFlag = item.quote ? getCurrencyInfo(item.quote).flag_emoji : ''}
                                                    <tr class="border-t border-gray-100 dark:border-slate-700/50">
                                                        <td class="py-1 pr-2">
                                                            {#if item.status === 'ok'}
                                                                <CheckCircle size={13} class="text-green-500" />
                                                            {:else}
                                                                <XCircle size={13} class="text-red-500" />
                                                            {/if}
                                                        </td>
                                                        <td class="py-1 pr-2">
                                                            <span class="font-medium text-gray-700 dark:text-gray-300">
                                                                {#if baseFlag}<span class="emoji-flag">{baseFlag}</span>{/if}
                                                                {item.pair || '?'}
                                                                {#if quoteFlag}<span class="emoji-flag">{quoteFlag}</span>{/if}
                                                            </span>
                                                        </td>
                                                        <td class="py-1 pr-2">
                                                            {#if chain.length > 0}
                                                                <span class="inline-flex items-center gap-0.5">
                                                                    {#each chain as prov, i}
                                                                        {@const iconUrl = getFxProviderIconUrl(prov)}
                                                                        <span class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] font-medium rounded {PROVIDER_COLORS[prov] ?? DEFAULT_PROVIDER_COLOR}" title={prov}>
                                                                            {#if iconUrl}
                                                                                <img src={iconUrl} alt={prov} class="w-3.5 h-3.5 rounded-sm object-contain" />
                                                                            {:else}
                                                                                {prov}
                                                                            {/if}
                                                                        </span>
                                                                        {#if i < chain.length - 1}
                                                                            <span class="text-gray-400 text-[8px]">→</span>
                                                                        {/if}
                                                                    {/each}
                                                                </span>
                                                            {/if}
                                                        </td>
                                                        <td class="py-1 pr-2 text-left whitespace-nowrap">
                                                            {#if item.status === 'ok' && item.points_changed != null}
                                                                <span class="text-emerald-600 dark:text-emerald-400">+{item.points_changed}Δ</span>
                                                            {/if}
                                                        </td>
                                                        <td class="py-1">
                                                            {#if item.errors && item.errors.length > 0}
                                                                <Tooltip text={item.errors.join('\n')} position="top" maxWidth="500px">
                                                                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                                                                    <span
                                                                        class="text-red-500 truncate max-w-[200px] cursor-help inline-block"
                                                                        ondblclick={() => copyErrorToClipboard(item.errors?.join('; ') ?? '')}
                                                                        ontouchstart={() => handleTouchStart(item.errors?.join('; ') ?? '')}
                                                                        ontouchend={handleTouchEnd}>— {item.errors[0]}</span
                                                                    >
                                                                </Tooltip>
                                                            {/if}
                                                        </td>
                                                    </tr>
                                                {/each}
                                            </tbody>
                                        </table>
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/each}
            {/if}
        </div>
    </div>

    <!-- Footer -->
    <div class="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 dark:border-slate-700">
        <button type="button" data-testid="scheduler-log-close" class="px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors" onclick={() => (open = false)}>
            {$_('settings.global.scheduler.log.close')}
        </button>
    </div>
</ModalBase>
