<script lang="ts">
    import {Pencil, Plus, Trash2} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import {getAssetInfo} from '$lib/stores/reference/assetStore';
    import {CopyFlow} from '../copyFlow.svelte';
    import {draftAssetFromInfo, domainAssetKey} from '../copies';
    import {sameExposures, samePrice, type DraftAsset, type PlannerDraft, type RemovalImpact} from '../draft.svelte';
    import {formatPlannerPercentUnits, formatPlannerPlainDecimal, formatPlannerPricePlain, formatPlannerTimestamp} from '../format';
    import {DIMENSION_FALLBACKS} from '../labels';
    import {BADGE, BUTTON_DANGER, BUTTON_SECONDARY, CARD, HINT, NOTICE} from '../ui';
    import AgeLabel from '../shared/AgeLabel.svelte';
    import CopyFlowView from '../shared/CopyFlowView.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import RemovalConfirm from '../shared/RemovalConfirm.svelte';
    import AssetEditor from './AssetEditor.svelte';
    import SourceCopyDialog from './SourceCopyDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
    }

    let {draft, accountGeneration}: Props = $props();

    const flow = new CopyFlow();
    let copying = $state<'prices' | 'classifications' | null>(null);
    let editing = $state<{key: string | null} | null>(null);
    let removal = $state<{key: string; name: string; impact: RemovalImpact} | null>(null);
    let searchValue = $state<number | null>(null);

    const copyDisabled = $derived(!/^[A-Z]{3}$/.test(draft.data.valuationCurrency) || !draft.data.assets.some((asset) => asset.sourceAssetId !== null));
    const inDraft = $derived(new Set(draft.data.assets.map((asset) => asset.key)));

    function addFromSearch(id: number | null): void {
        if (id === null) return;
        const info = getAssetInfo(id);
        if (info && !inDraft.has(domainAssetKey(id))) draft.addAsset(draftAssetFromInfo(info));
        queueMicrotask(() => (searchValue = null));
    }

    function title(asset: DraftAsset): string {
        return [asset.ticker, asset.name].filter((part) => part.trim() !== '').join(' ');
    }

    function exposureSummary(asset: DraftAsset): string {
        return asset.exposures.map((row) => [$t(`tools.pacAllocator.planner.dimensions.${row.dimension}`, {default: DIMENSION_FALLBACKS[row.dimension]}), formatPlannerPercentUnits(row.weightPercent, 0), row.label].join(' ')).join(' · ');
    }

    function askRemove(asset: DraftAsset): void {
        removal = {key: asset.key, name: asset.name, impact: draft.assetRemovalImpact(asset.key)};
    }

    function confirmRemoval(): void {
        if (removal) draft.removeAsset(removal.key);
        removal = null;
    }
</script>

<div class="space-y-4" data-testid="pac-planner-assets">
    <div class="flex flex-wrap items-end gap-2">
        <div class="w-full max-w-sm">
            <AssetSelect bind:value={searchValue} filter={(info) => !inDraft.has(domainAssetKey(info.id))} placeholder={$t('tools.pacAllocator.planner.assets.search', {default: 'Search Asset'})} testid="pac-planner-asset-search" onchange={addFromSearch} />
        </div>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-asset-add" onclick={() => (editing = {key: null})}>
            <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.assets.addManual', {default: 'Manual Asset'})}
        </button>
        <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled} data-testid="pac-planner-prices-copy-open" onclick={() => (copying = 'prices')}>
            {$t('tools.pacAllocator.planner.assets.copyPrices', {default: 'Copy prices'})}
        </button>
        <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled} data-testid="pac-planner-classifications-copy-open" onclick={() => (copying = 'classifications')}>
            {$t('tools.pacAllocator.planner.assets.copyClassifications', {default: 'Copy classifications'})}
        </button>
    </div>
    <p class={HINT}>{$t('tools.pacAllocator.planner.assets.noAutoPrice', {default: 'Adding an Asset copies its identity only. Prices and classifications arrive with an explicit copy; no provider is called.'})}</p>

    <CopyFlowView {flow} {draft} testid="pac-planner-assets-notice" />

    <div class="grid gap-3 lg:grid-cols-2">
        {#each draft.data.assets as asset (asset.key)}
            {@const priceModified = asset.priceStamp !== null && !samePrice(asset.price, asset.copiedPrice)}
            {@const exposuresModified = asset.exposureStamp !== null && !sameExposures(asset.exposures, asset.copiedExposures)}
            <section class="{CARD} space-y-2" data-testid="pac-planner-asset" data-asset-key={asset.key} data-origin={asset.origin} data-price={asset.price ? 'set' : 'missing'}>
                <div class="flex flex-wrap items-start justify-between gap-2">
                    <h3 class="font-semibold text-gray-900 dark:text-gray-100">
                        {title(asset)}
                        <span class="font-normal text-gray-500 dark:text-gray-400">· {asset.assetClass || '—'}</span>
                    </h3>
                    <div class="flex flex-wrap gap-1">
                        {#if !asset.active}<span class={BADGE.warning}>{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>{/if}
                        <OriginBadge origin={asset.origin} testid="pac-planner-asset-origin" />
                        {#if !asset.price}<span class={BADGE.danger} data-testid="pac-planner-asset-alert" aria-label={$t('tools.pacAllocator.planner.assets.priceMissingShort', {default: 'Price missing'})}>!</span>{/if}
                    </div>
                </div>
                {#if asset.price}
                    <p class="flex flex-wrap items-center gap-2 text-sm" data-testid="pac-planner-asset-price">
                        <span class="tabular-nums">
                            {$t('tools.pacAllocator.planner.assets.priceLine', {
                                default: '{price} / {units} {count, plural, one {unit} other {units}}',
                                values: {price: formatPlannerPricePlain(asset.price.amount, asset.price.currency), units: formatPlannerPlainDecimal(asset.price.quoteBaseQuantity), count: Number(asset.price.quoteBaseQuantity)},
                            })}
                        </span>
                        {#if asset.priceStamp}
                            <OriginBadge origin="copied" modified={priceModified} when={formatPlannerTimestamp(draft.copyRecord(asset.priceStamp)?.capturedAt, $locale)} testid="pac-planner-asset-price-origin" />
                        {/if}
                        <AgeLabel date={asset.price.referenceDate || null} asOf={draft.data.asOf} manual={!asset.priceStamp} testid="pac-planner-asset-price-age" />
                    </p>
                {:else}
                    <p class="text-sm text-amber-800 dark:text-amber-200" data-testid="pac-planner-asset-no-price">{$t('tools.pacAllocator.planner.assets.priceMissing', {default: 'Price missing: it stays in the draft, the calculation will ask for it.'})}</p>
                {/if}
                <p class="text-sm" data-testid="pac-planner-asset-exposures">
                    {#if asset.exposures.length > 0}
                        {exposureSummary(asset)}
                        {#if exposuresModified}<span class={BADGE.warning}>{$t('tools.pacAllocator.planner.origin.modified', {default: 'Modified'})}</span>{/if}
                    {:else}
                        <span class={HINT}>{$t('tools.pacAllocator.planner.assets.noExposures', {default: 'No exposure: the backend counts it as Uncategorised.'})}</span>
                    {/if}
                </p>
                <div class="flex flex-wrap gap-2">
                    <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-asset-edit" onclick={() => (editing = {key: asset.key})}>
                        <Pencil class="h-4 w-4" aria-hidden="true" />{$t('common.edit', {default: 'Edit'})}
                    </button>
                    <button type="button" class={BUTTON_DANGER} data-testid="pac-planner-asset-remove" onclick={() => askRemove(asset)}>
                        <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
                    </button>
                </div>
            </section>
        {/each}
    </div>

    {#if draft.data.assets.length === 0}
        <p class={NOTICE.info} data-testid="pac-planner-assets-empty">{$t('tools.pacAllocator.planner.assets.empty', {default: 'Search an Asset of the database or add a manual one: the Tool works without any Asset in the database.'})}</p>
    {/if}
</div>

{#if copying}
    <SourceCopyDialog kind={copying} {draft} {accountGeneration} onclose={() => (copying = null)} oncopied={(outcome, source) => flow.accept(outcome, source)} />
{/if}
{#if editing}
    <AssetEditor {draft} assetKey={editing.key} onclose={() => (editing = null)} />
{/if}
<RemovalConfirm
    open={removal !== null}
    {draft}
    title={$t('tools.pacAllocator.planner.removal.title', {default: 'Remove {name}?', values: {name: removal?.name ?? ''}})}
    message={$t('tools.pacAllocator.planner.removal.message', {default: 'It leaves the draft only; nothing changes in the system.'})}
    impact={removal?.impact ?? null}
    testId="pac-planner-asset-removal"
    onConfirm={confirmRemoval}
    onCancel={() => (removal = null)}
/>
