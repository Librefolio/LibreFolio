<!--
  ProfileBulkRefreshSection — the «Profilo» section of the assets' sync window, under the prices (87, A5): «Aggiorna i
  profili» reads the enrichers of every asset of the window that has some, in one call. The enrichers are chosen asset by
  asset; here they are only called together.

  The server gives no progress, so none is drawn: while it reads the section says so, then it lists each asset with what
  happened. Closing the window does not stop the read (`profileBulkRefresh.svelte.ts` keeps it).

  It publishes `data-status`, `data-run`, `data-count`; a row publishes `data-outcome`.

  Pattern: Svelte 5 Runes, Tailwind CSS 4, colour roles only.
-->
<script lang="ts">
    import {IdCard, RefreshCw} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {STATUS_ICONS, type SyncStatus} from '$lib/utils/sync/syncHelpers';
    import {STATUS_TONES} from '$lib/theme/toneClasses';
    import type {ProfileBulkRefresh} from './profileBulkRefresh.svelte';
    import {failedSources, refreshOutcome, type ProfileRefreshOutcome} from './profileRefresh';
    import {loadProfileSources, profileSourceName, type ProfileSource} from './profileSources';
    import type {ProfileRefreshResult} from './profileStore';

    interface Props {
        refresh: ProfileBulkRefresh;
        /** The window's assets, by id: the name and icon of a row. */
        assets: Map<number, {display_name: string; icon_url?: string | null}>;
    }

    let {refresh, assets}: Props = $props();

    let sources = $state<Record<string, ProfileSource>>({});
    $effect(() => {
        void loadProfileSources().then((known) => (sources = known));
    });

    const STATUS: Record<ProfileRefreshOutcome, SyncStatus> = {written: 'ok', unchanged: 'ok', partial: 'partial', none: 'skipped', failed: 'failed'};

    function rowText(result: ProfileRefreshResult, outcome: ProfileRefreshOutcome): string {
        const written = $t('assets.profile.refresh.written', {values: {count: (result.written ?? []).length}});
        if (outcome === 'written') return written;
        if (outcome === 'unchanged') return $t('assets.profile.bulk.rowUnchanged');
        if (outcome === 'none') return $t('assets.profile.bulk.rowNone');
        if (outcome === 'failed') return $t('assets.profile.bulk.rowFailed');
        const names = failedSources(result).map((code) => profileSourceName(code, (key) => $t(key), sources));
        const unanswered = $t('assets.profile.bulk.rowUnanswered', {values: {sources: names.join(', ')}});
        return (result.written ?? []).length ? `${written} · ${unanswered}` : unanswered;
    }

    const running = $derived(refresh.run === 'running');
</script>

<section
    class="space-y-2 border-t border-lf-subtle pt-3 text-lf-primary"
    data-testid="asset-sync-profile"
    data-status={refresh.status}
    data-run={refresh.run}
    data-count={refresh.assetIds.length}
    data-busy={running || refresh.status === 'loading' ? 'true' : 'false'}
    aria-busy={running || refresh.status === 'loading'}
>
    <div class="flex flex-wrap items-center gap-2">
        <h3 class="mr-auto flex items-center gap-1.5 text-sm font-semibold text-lf-primary">
            <IdCard size={16} class="text-lf-muted" aria-hidden="true" />
            {$t('assets.profile.bulk.title')}
        </h3>
        {#if refresh.status === 'ready' && refresh.assetIds.length}
            <button
                type="button"
                class="inline-flex items-center gap-1.5 rounded-lg border border-lf-input bg-lf-card px-3 py-1.5 text-sm font-medium text-lf-primary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus disabled:cursor-wait disabled:opacity-60"
                disabled={running}
                data-testid="asset-sync-profile-start"
                onclick={() => void refresh.start((key, values) => $t(key, {values}))}
            >
                <RefreshCw size={14} class={running ? 'animate-spin' : ''} aria-hidden="true" />
                {$t('assets.profile.bulk.start')}
            </button>
        {/if}
    </div>

    {#if refresh.status === 'unknown'}
        <p class="text-sm text-lf-warning" role="status" data-testid="asset-sync-profile-unknown">{$t('assets.profile.bulk.unknown')}</p>
    {:else if refresh.status === 'ready' && !refresh.assetIds.length}
        <p class="text-sm text-lf-muted" data-testid="asset-sync-profile-none">{$t('assets.profile.bulk.noAssets')}</p>
    {:else if refresh.status === 'ready'}
        <p class="text-sm text-lf-secondary">
            {$t('assets.profile.bulk.description', {values: {count: refresh.assetIds.length}})}
        </p>
    {/if}

    <div aria-live="polite">
        {#if running}
            <p class="flex items-center gap-1.5 text-xs text-lf-muted" data-testid="asset-sync-profile-running">
                <RefreshCw size={12} class="animate-spin" aria-hidden="true" />
                {$t('assets.profile.bulk.running')}
            </p>
        {:else if refresh.run === 'serverRunning'}
            <p class="text-sm text-lf-info" data-testid="asset-sync-profile-server-running">{$t('assets.profile.bulk.stillRunning')}</p>
        {:else if refresh.run === 'failed'}
            <p class="text-sm text-lf-danger" data-testid="asset-sync-profile-failed">{$t('assets.profile.refresh.failed')}</p>
        {/if}
    </div>

    {#if refresh.run === 'done'}
        <ul class="space-y-1.5" data-testid="asset-sync-profile-results">
            {#each refresh.results as result (result.asset_id)}
                {@const outcome = refreshOutcome(result)}
                {@const asset = assets.get(result.asset_id)}
                {@const status = STATUS[outcome]}
                {@const StatusIcon = STATUS_ICONS[status]}
                <li class="flex items-center gap-2 text-xs text-lf-secondary" data-testid="asset-sync-profile-row" data-asset-id={result.asset_id} data-outcome={outcome}>
                    <StatusIcon size={14} class="{STATUS_TONES.syncIcon[status]} shrink-0" />
                    {#if asset?.icon_url}<img src={asset.icon_url} alt="" class="h-4 w-4 shrink-0 rounded-sm object-contain" />{/if}
                    <span class="max-w-[45%] shrink-0 truncate font-medium" title={asset?.display_name}>{asset?.display_name ?? `#${result.asset_id}`}</span>
                    <span class="min-w-0 break-words text-lf-muted">{rowText(result, outcome)}</span>
                </li>
            {/each}
        </ul>
    {/if}
</section>
