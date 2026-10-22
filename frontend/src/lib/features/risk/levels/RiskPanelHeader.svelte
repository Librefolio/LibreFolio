<script lang="ts">
    import {onDestroy} from 'svelte';
    import {goto} from '$app/navigation';

    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import {_ as t} from '$lib/i18n';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {fxRoutesVersion, getConfiguredPairSlugs} from '$lib/stores/reference/fxRoutesStore';
    import type {RiskPanelController} from '$lib/features/risk/riskPanelController.svelte';
    import {addPairSides, labQualityAction} from '$lib/features/risk/syncTargets';

    import {RotateCw} from 'lucide-svelte';

    /**
     * Everything above the answer: what it is, how stale it is, how to refresh it.
     *
     * Extracted rather than copied. The scope picker changed, the four levels are
     * new, but "these prices are three days old and here is the button that fixes
     * it" is the same sentence on every risk surface — and two copies of one
     * sentence is how two pages begin to disagree about it.
     */
    interface Props {
        controller: RiskPanelController;
        title?: string;
        subtitle?: string;
        internalSubset?: boolean;
        /** Asset ids whose prices this answer rests on. */
        assetIds?: number[];
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        showActions?: boolean;
    }

    let {controller, title = '', subtitle = '', internalSubset = false, assetIds = [], dateStart, dateEnd, targetCurrency, showActions = true}: Props = $props();

    let syncOpen = $state(false);

    let syncAssets = $derived.by(() => {
        void $assetStoreVersion;
        return [...new Set(assetIds)]
            .sort((left, right) => left - right)
            .map((assetId) => getAssetInfo(assetId))
            .filter((asset) => Boolean(asset))
            .map((asset) => ({
                id: asset!.id,
                display_name: asset!.display_name,
                currency: asset!.currency,
                icon_url: asset!.icon_url,
                asset_type: asset!.asset_type,
                provider_code: asset!.provider_code,
            }));
    });

    let syncFxPairs = $derived.by(() => {
        void $fxRoutesVersion;
        const configured = getConfiguredPairSlugs();
        const pairs = new Set<string>();
        for (const asset of syncAssets) {
            if (!asset || asset.currency === targetCurrency) continue;
            const slug = [asset.currency, targetCurrency].sort().join('-');
            if (configured.has(slug)) pairs.add(slug);
        }
        return [...pairs].sort();
    });

    /** The «add FX pair» dialog an `add_fx_pair` chip opens (TC-23), and the sides it opens on. */
    let addPairOpen = $state(false);
    let addPairInitial = $state({base: '', quote: ''});
    let alive = true;
    onDestroy(() => (alive = false));

    /** The banner's actions, through the one rule every risk panel reads (`labQualityAction`). */
    function handleQualityAction(action: string, target: string | null): void {
        const next = labQualityAction(action, target);
        if (next?.kind === 'sync') syncOpen = true;
        else if (next?.kind === 'navigate') void goto(next.href);
        else if (next?.kind === 'add_pair') {
            addPairInitial = addPairSides(next.pair);
            addPairOpen = true;
        }
    }

    /**
     * Once the pair is saved, and again once its rates are synced, the answer is asked again, as
     * after this panel's own sync. Not once the panel is gone: the dialog's rate sync can outlive it.
     */
    async function refreshAfterPair(): Promise<void> {
        if (alive) await controller.handleSynced();
    }
</script>

<div class="flex flex-wrap items-start justify-between gap-3">
    <div>
        <h2 class="text-lg font-semibold text-lf-primary" data-testid="risk-levels-title">{title || $t('risk.title')}</h2>
        {#if subtitle || internalSubset}
            <p class="text-sm text-lf-muted" data-testid="risk-scope-label">
                {internalSubset ? $t('risk.internalSubset') : subtitle}
            </p>
        {/if}
    </div>
    {#if showActions}
        <div class="flex items-center gap-2">
            <button type="button" class="flex items-center gap-1.5 rounded-lg border border-lf-subtle bg-lf-card px-3 py-1.5 text-xs text-lf-secondary disabled:opacity-50" onclick={() => (syncOpen = true)} disabled={syncAssets.length === 0 && syncFxPairs.length === 0} data-testid="risk-sync-button">
                <RotateCw size={14} />
                {$t('common.sync')}
            </button>
        </div>
    {/if}
</div>

{#if controller.loadError}
    <div class="rounded-xl border border-lf-danger-line bg-lf-danger-soft p-4 text-sm text-lf-danger-on-soft" data-testid="risk-load-error">
        {$t('risk.states.loadFailed')}
    </div>
{/if}

{#if controller.dataQualityIssues.length > 0}
    <DataQualityBanner issues={controller.dataQualityIssues} mode="grouped" onaction={(action, target) => handleQualityAction(action, target)} />
{/if}

<PageSyncModal bind:open={syncOpen} {dateStart} {dateEnd} assets={syncAssets} fxPairs={syncFxPairs} onsynced={() => controller.handleSynced()} onclose={() => (syncOpen = false)} />

{#if addPairOpen}
    <FxPairAddModal bind:open={addPairOpen} initialBase={addPairInitial.base} initialQuote={addPairInitial.quote} oncreated={refreshAfterPair} onsynced={refreshAfterPair} />
{/if}
