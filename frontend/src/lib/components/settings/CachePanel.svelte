<!--
  CachePanel.svelte — Svelte 5 (runes)

  Admin panel showing the status of every named backend cache (theine registry).
  Status is readable by any authenticated user; clear actions are admin-only
  (gated by the `canEdit` prop, mirroring the Global settings lock).

  Both clear actions require confirmation: after a clear, the next fetch of
  that data hits the providers again — slowdowns comparable to a server restart.

  Endpoints used:
    GET  /api/v1/settings/cache/status
    POST /api/v1/settings/cache/clear/{name}
    POST /api/v1/settings/cache/clear-all
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {get} from 'svelte/store';
    import {onMount} from 'svelte';
    import {debug} from '$lib/debug';
    import {Database, RefreshCw, Trash2} from 'lucide-svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';

    interface CacheStatusEntry {
        name: string;
        current_size: number;
        maxsize: number;
        ttl_seconds: number;
    }

    interface Props {
        /** Enables the admin-only clear actions (mirrors the Global settings lock). */
        canEdit?: boolean;
    }

    let {canEdit = false}: Props = $props();

    let caches: CacheStatusEntry[] = $state([]);
    let loading = $state(true);
    let clearing = $state(false);
    /** Clear awaiting confirmation: a cache name, 'all', or null (modal closed). */
    let confirmTarget: string | 'all' | null = $state(null);

    /** Table sorting: clickable column headers (name / size / TTL). */
    type SortKey = 'name' | 'size' | 'ttl';
    let sortKey: SortKey = $state('name');
    let sortAsc = $state(true);

    const sortedCaches = $derived.by(() => {
        const list = [...caches];
        const dir = sortAsc ? 1 : -1;
        if (sortKey === 'name') list.sort((a, b) => a.name.localeCompare(b.name) * dir);
        else if (sortKey === 'size') list.sort((a, b) => (a.current_size - b.current_size || a.name.localeCompare(b.name)) * dir);
        else list.sort((a, b) => (a.ttl_seconds - b.ttl_seconds || a.name.localeCompare(b.name)) * dir);
        return list;
    });

    function toggleSort(key: SortKey) {
        if (sortKey === key) sortAsc = !sortAsc;
        else {
            sortKey = key;
            sortAsc = key === 'name';
        }
    }

    onMount(loadStatus);

    async function loadStatus() {
        loading = true;
        try {
            const resp = await zodiosApi.axios.get('/api/v1/settings/cache/status');
            caches = resp.data?.items ?? [];
        } catch (e) {
            debug.log('CachePanel', 'Failed to load cache status', e);
            caches = [];
            notify({
                name: 'settings.cache.load.failed',
                toast: {variant: 'error', message: get(t)('settings.cache.loadFailed')},
            });
        } finally {
            loading = false;
        }
    }

    /** Human-friendly TTL: seconds under a minute, minutes under an hour, else hours. */
    function formatTtl(seconds: number): string {
        if (seconds >= 3600) {
            const hours = seconds / 3600;
            return `${Number.isInteger(hours) ? hours : hours.toFixed(1)}h`;
        }
        if (seconds >= 60) return `${Math.round(seconds / 60)}min`;
        return `${seconds}s`;
    }

    async function confirmClear() {
        if (confirmTarget === null) return;
        const target = confirmTarget;
        confirmTarget = null;
        clearing = true;
        try {
            if (target === 'all') {
                const resp = await zodiosApi.axios.post('/api/v1/settings/cache/clear-all');
                const count = resp.data?.cleared_count ?? 0;
                notify({
                    name: 'settings.cache.cleared.all',
                    detail: {count},
                    toast: {variant: 'success', message: get(t)('settings.cache.clearedAll', {values: {count}})},
                });
            } else {
                await zodiosApi.axios.post(`/api/v1/settings/cache/clear/${encodeURIComponent(target)}`);
                notify({
                    name: 'settings.cache.cleared',
                    detail: {cache: target},
                    toast: {variant: 'success', message: get(t)('settings.cache.cleared', {values: {name: target}})},
                });
            }
        } catch (e) {
            debug.log('CachePanel', 'Failed to clear cache', e);
            notify({
                name: 'settings.cache.clear.failed',
                detail: {cache: target},
                toast: {variant: 'error', message: get(t)('settings.cache.clearFailed')},
            });
        } finally {
            clearing = false;
        }
        await loadStatus();
    }
</script>

<div class="bg-gray-50 dark:bg-slate-800 rounded-lg px-4 py-3" data-testid="cache-panel">
    <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 min-w-0">
            <Database size={16} class="text-gray-500 dark:text-gray-400 shrink-0" />
            <div class="min-w-0">
                <span class="text-sm font-medium text-gray-700 dark:text-gray-200">
                    {$t('settings.cache.title')}
                </span>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {$t('settings.cache.description')}
                </p>
            </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
            <button class="text-xs text-libre-green hover:text-libre-green/80 font-medium disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1" type="button" data-testid="cache-refresh" disabled={loading || clearing} onclick={loadStatus}>
                <RefreshCw size={12} class={loading ? 'animate-spin' : ''} />
                {$t('settings.cache.refresh')}
            </button>
            {#if canEdit && caches.length > 0}
                <button class="text-xs text-red-500 hover:text-red-600 font-medium disabled:opacity-50 disabled:cursor-not-allowed" type="button" data-testid="cache-clear-all" disabled={clearing} onclick={() => (confirmTarget = 'all')}>
                    {$t('settings.cache.clearAll')}
                </button>
            {/if}
        </div>
    </div>

    {#if loading && caches.length === 0}
        <div class="flex justify-center py-4">
            <LoadingSpinner size="sm" />
        </div>
    {:else if caches.length === 0}
        <p class="text-xs text-gray-500 dark:text-gray-400 py-3" data-testid="cache-empty">
            {$t('settings.cache.empty')}
        </p>
    {:else}
        <div class="mt-3 overflow-x-auto">
            <table class="w-full text-xs">
                <thead>
                    <tr class="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-slate-700">
                        <th class="pb-1.5 font-medium">
                            <button type="button" class="inline-flex items-center gap-0.5 hover:text-gray-700 dark:hover:text-gray-200 cursor-pointer" data-testid="cache-sort-name" onclick={() => toggleSort('name')}>
                                {$t('settings.cache.colName')}{sortKey === 'name' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                            </button>
                        </th>
                        <th class="pb-1.5 font-medium text-right">
                            <button type="button" class="inline-flex items-center gap-0.5 hover:text-gray-700 dark:hover:text-gray-200 cursor-pointer ml-auto" data-testid="cache-sort-size" onclick={() => toggleSort('size')}>
                                {$t('settings.cache.colSize')}{sortKey === 'size' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                            </button>
                        </th>
                        <th class="pb-1.5 font-medium text-right">
                            <button type="button" class="inline-flex items-center gap-0.5 hover:text-gray-700 dark:hover:text-gray-200 cursor-pointer ml-auto" data-testid="cache-sort-ttl" onclick={() => toggleSort('ttl')}>
                                {$t('settings.cache.colTtl')}{sortKey === 'ttl' ? (sortAsc ? ' ▲' : ' ▼') : ''}
                            </button>
                        </th>
                        {#if canEdit}
                            <th class="pb-1.5 font-medium text-right w-16"></th>
                        {/if}
                    </tr>
                </thead>
                <tbody>
                    {#each sortedCaches as cache (cache.name)}
                        <tr class="border-b border-gray-100 dark:border-slate-700/50 last:border-0" data-testid="cache-row-{cache.name}">
                            <td class="py-1.5 pr-2 font-mono text-gray-700 dark:text-gray-300 break-all">{cache.name}</td>
                            <td class="py-1.5 pr-2 text-right text-gray-600 dark:text-gray-400 whitespace-nowrap">
                                {cache.current_size} / {cache.maxsize}
                            </td>
                            <td class="py-1.5 pr-2 text-right text-gray-600 dark:text-gray-400 whitespace-nowrap">
                                {formatTtl(cache.ttl_seconds)}
                            </td>
                            {#if canEdit}
                                <td class="py-1.5 text-right">
                                    <button class="text-red-500 hover:text-red-600 font-medium disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1" type="button" data-testid="cache-clear-{cache.name}" disabled={clearing} onclick={() => (confirmTarget = cache.name)}>
                                        <Trash2 size={12} />
                                        {$t('settings.cache.clear')}
                                    </button>
                                </td>
                            {/if}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>

<ConfirmModal
    open={confirmTarget !== null}
    testId="cache-confirm-modal"
    danger
    title={confirmTarget === 'all' ? $t('settings.cache.confirmClearAllTitle') : $t('settings.cache.confirmClearTitle', {values: {name: confirmTarget}})}
    message={$t('settings.cache.confirmWarning')}
    confirmText={$t('settings.cache.clear')}
    onConfirm={confirmClear}
    onCancel={() => (confirmTarget = null)}
/>
