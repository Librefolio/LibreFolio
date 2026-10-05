<script lang="ts">
    import {onDestroy, onMount} from 'svelte';
    import {t} from '$lib/i18n';
    import {applyClassificationCopy, applyFxCopy, applyPriceCopy, newCopyRecord, type CopyOutcome} from '../copies';
    import type {PlannerDraft} from '../draft.svelte';
    import {loadCopyScope, selectableIds} from '../scope';
    import type {PlannerSource, SourceSection} from '../source';
    import {SourceLoad} from '../sourceLoad.svelte';
    import {BADGE, BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, NOTICE} from '../ui';
    import PlannerDialog from '../shared/PlannerDialog.svelte';

    type Kind = 'prices' | 'classifications' | 'fx';

    interface Props {
        kind: Kind;
        draft: PlannerDraft;
        accountGeneration: number;
        onclose: () => void;
        oncopied: (outcome: CopyOutcome, source: PlannerSource) => void;
    }

    let {kind, draft, accountGeneration, onclose, oncopied}: Props = $props();

    const SECTIONS: Record<Kind, SourceSection[]> = {prices: ['assets', 'prices'], classifications: ['assets', 'classifications'], fx: ['fx_quotes']};
    const testid = $derived(`pac-planner-${kind}-copy`);
    const load = new SourceLoad();
    let owners = $state<number[] | null>(null);
    let scopeFailed = $state(false);

    onMount(async () => {
        try {
            owners = selectableIds(await loadCopyScope());
        } catch {
            scopeFailed = true;
        }
    });

    onDestroy(() => load.stop());

    const dbAssets = $derived(draft.data.assets.filter((asset) => asset.sourceAssetId !== null));
    const manualAssets = $derived(draft.data.assets.filter((asset) => asset.sourceAssetId === null));
    const pairs = $derived(draft.fxPairs);
    const itemCount = $derived(kind === 'fx' ? pairs.length : dbAssets.length);
    const ready = $derived(owners !== null && owners.length > 0 && itemCount > 0 && load.status !== 'loading');

    async function copy(): Promise<void> {
        if (!ready || !owners) return;
        draft.refreshAsOf();
        const source = await load.load(
            {
                asOf: draft.data.asOf,
                targetCurrency: draft.data.valuationCurrency,
                sections: SECTIONS[kind],
                brokerIds: owners,
                assetIds: kind === 'fx' ? [] : dbAssets.map((asset) => asset.sourceAssetId as number),
                fxPairs: kind === 'fx' ? pairs : [],
            },
            accountGeneration,
        );
        if (!source) return;
        const record = newCopyRecord(draft, kind, source);
        const outcome = kind === 'prices' ? applyPriceCopy(draft, source, record) : kind === 'classifications' ? applyClassificationCopy(draft, source, record) : applyFxCopy(draft, source, record);
        oncopied(outcome, source);
        onclose();
    }

    const title = $derived(
        kind === 'prices'
            ? $t('tools.pacAllocator.planner.pricesCopy.title', {default: 'Copy prices'})
            : kind === 'classifications'
              ? $t('tools.pacAllocator.planner.classificationsCopy.title', {default: 'Copy classifications'})
              : $t('tools.pacAllocator.planner.fxCopy.title', {default: 'Copy FX rates'}),
    );
</script>

<PlannerDialog open {title} {testid} {onclose}>
    <div class="space-y-3" data-testid="{testid}-body" data-state={load.status} aria-busy={load.status === 'loading'}>
        <p class={HINT}>
            {kind === 'prices'
                ? $t('tools.pacAllocator.planner.pricesCopy.source', {default: 'Source: the latest prices stored in LibreFolio. No provider is called.'})
                : kind === 'classifications'
                  ? $t('tools.pacAllocator.planner.classificationsCopy.source', {default: 'Source: the Asset classifications (type, sector, geography) stored in LibreFolio.'})
                  : $t('tools.pacAllocator.planner.fxCopy.source', {default: 'Source: the latest FX rates stored in LibreFolio. No provider is called.'})}
        </p>
        <p class={HINT}>{$t('tools.pacAllocator.planner.copy.ownerScope', {default: 'The Portfolio API reads through the Brokers you own; these values do not depend on the Broker.'})}</p>

        {#if scopeFailed}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-scope-error">{$t('tools.pacAllocator.planner.copy.scopeError', {default: 'The Broker list could not be loaded. Nothing was copied.'})}</div>
        {:else if owners === null}
            <p class={HINT} role="status" data-testid="{testid}-loading">{$t('common.loading', {default: 'Loading…'})}</p>
        {:else if owners.length === 0}
            <div class={NOTICE.info} data-testid="{testid}-no-owner">{$t('tools.pacAllocator.planner.copy.noOwner', {default: 'Copying needs at least one Broker you own. Enter the values by hand instead.'})}</div>
        {/if}

        {#if kind === 'fx'}
            {#if pairs.length === 0}
                <p class={NOTICE.info} data-testid="{testid}-empty">{$t('tools.pacAllocator.planner.fxCopy.empty', {default: 'No currency pair is needed yet.'})}</p>
            {:else}
                <ul class="flex flex-wrap gap-2" data-testid="{testid}-items">
                    {#each pairs as pair (pair)}<li class={BADGE.neutral} data-pair={pair}>{pair}</li>{/each}
                </ul>
            {/if}
        {:else if dbAssets.length === 0}
            <p class={NOTICE.info} data-testid="{testid}-empty">{$t('tools.pacAllocator.planner.assetCopy.empty', {default: 'No Asset of the database is in the draft: nothing to copy.'})}</p>
        {:else}
            <ul class="space-y-1 text-sm" data-testid="{testid}-items">
                {#each dbAssets as asset (asset.key)}<li data-asset-key={asset.key}>{[asset.ticker, asset.name].filter((part) => part.trim() !== '').join(' ')}</li>{/each}
                {#each manualAssets as asset (asset.key)}
                    <li class="text-gray-500 dark:text-gray-400" data-asset-key={asset.key} data-manual="true">
                        {asset.name} · {$t('tools.pacAllocator.planner.assetCopy.manual', {default: 'manual, not copied'})}
                    </li>
                {/each}
            </ul>
        {/if}

        {#if load.status === 'loading'}
            <p class={HINT} role="status" data-testid="{testid}-reading">{$t('tools.pacAllocator.planner.copy.reading', {default: 'Reading the snapshot…'})}</p>
        {:else if load.status === 'error' && load.error}
            <div class={NOTICE.danger} role="alert" data-testid="{testid}-error">{$t(load.error.key, {default: load.error.fallback})}</div>
        {/if}

        <p class={HINT}>{$t('tools.pacAllocator.planner.copy.rule', {default: 'Nothing is live: a copy is a snapshot you can edit. Copying again updates only what you have not changed and lists the rest.'})}</p>
    </div>

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="{testid}-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        {#if load.status === 'loading'}
            <button type="button" class={BUTTON_SECONDARY} data-testid="{testid}-stop" onclick={() => load.stop()}>{$t('tools.pacAllocator.planner.copy.stop', {default: 'Stop'})}</button>
        {/if}
        <button type="button" class={BUTTON_PRIMARY} disabled={!ready} data-testid="{testid}-apply" onclick={copy}>
            {$t('tools.pacAllocator.planner.copy.apply', {default: '{count, plural, one {Copy # item} other {Copy # items}}', values: {count: itemCount}})}
        </button>
    {/snippet}
</PlannerDialog>
