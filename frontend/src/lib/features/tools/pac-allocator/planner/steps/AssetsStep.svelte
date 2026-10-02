<script lang="ts">
    import {onDestroy, onMount, untrack} from 'svelte';
    import {Briefcase, ExternalLink, LoaderCircle, Pencil, Plus, Trash2} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {getAssetInfo} from '$lib/stores/reference/assetStore';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {AddedAssetFacts} from '../assetRead.svelte';
    import {CategoryLabels} from '../categoryLabels.svelte';
    import {draftAssetFromInfo, domainAssetKey, setPriceManual} from '../copies';
    import {compareDecimal} from '../decimal';
    import {EXPOSURE_DIMENSIONS, type DraftAsset, type DraftExposure, type ExposureDimension, type PlannerDraft, type RemovalImpact} from '../draft.svelte';
    import {formatPlannerDate, formatPlannerPercentUnits, formatPlannerPlainDecimal, formatPlannerPricePlain} from '../format';
    import {DIMENSION_FALLBACKS} from '../labels';
    import {BADGE, BUTTON_DANGER, BUTTON_LINK, BUTTON_SECONDARY, HINT, INPUT, NOTICE} from '../ui';
    import AutoManualToggle from '../shared/AutoManualToggle.svelte';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import RemovalConfirm from '../shared/RemovalConfirm.svelte';
    import AssetEditor from './AssetEditor.svelte';
    import OwnedAssetsDialog from './OwnedAssetsDialog.svelte';
    const KEY = 'tools.pacAllocator.planner.assets';
    /** Categories shown on a card line; the rest open in a tooltip. */
    const VISIBLE_CATEGORIES = 3;
    /** The type is a single value, already in the card header: the composition lists only these. */
    const COMPOSITION_DIMENSIONS = EXPOSURE_DIMENSIONS.filter((dimension) => dimension !== 'asset_type');

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
    }

    let {draft, accountGeneration}: Props = $props();

    const reader = new AddedAssetFacts();
    const labels = new CategoryLabels();
    onDestroy(() => reader.stop());
    let owning = $state(false);
    let editing = $state<{key: string | null} | null>(null);
    let removal = $state<{key: string; name: string; impact: RemovalImpact} | null>(null);
    let searchValue = $state<number | null>(null);

    const inDraft = $derived(new Set(draft.data.assets.map((asset) => asset.key)));

    $effect(() => {
        const language = $currentLanguage;
        untrack(() => labels.load(language));
    });

    // Assets restored with the draft, or left mid-read when the step was closed, are read once here.
    onMount(() => {
        const pending = reader.pending(draft);
        if (pending.length > 0) readFacts(pending);
    });

    function addFromSearch(id: number | null): void {
        if (id === null) return;
        const info = getAssetInfo(id);
        if (info && !inDraft.has(domainAssetKey(id))) {
            draft.addAsset(draftAssetFromInfo(info));
            readFacts([id]);
        }
        queueMicrotask(() => (searchValue = null));
    }

    function readFacts(assetIds: number[]): void {
        void reader.read(draft, assetIds, accountGeneration);
    }

    function title(asset: DraftAsset): string {
        return [asset.ticker, asset.name].filter((part) => part.trim() !== '').join(' ');
    }

    /** No price, or a manual one still empty: the calculation will ask for it. */
    function priceMissing(asset: DraftAsset): boolean {
        return !asset.price || asset.price.amount.trim() === '';
    }

    function typeText(asset: DraftAsset): string {
        const code = asset.assetClass.trim();
        return code === '' ? '—' : labels.text($t, 'asset_type', code);
    }

    function dimensionName(dimension: ExposureDimension): string {
        return $t(`tools.pacAllocator.planner.dimensions.${dimension}`, {default: DIMENSION_FALLBACKS[dimension]});
    }

    function rowsOf(asset: DraftAsset, dimension: ExposureDimension): DraftExposure[] {
        return asset.exposures.filter((row) => row.dimension === dimension).sort((a, b) => compareDecimal(b.weightPercent, a.weightPercent) ?? 0);
    }

    function isWhole(rows: readonly DraftExposure[]): boolean {
        return rows.length === 1 && compareDecimal(rows[0].weightPercent, '100') === 0;
    }

    function categoryText(row: DraftExposure, whole: boolean): string {
        const name = labels.text($t, row.dimension, row.label || row.categoryId);
        if (whole) return name;
        return `${name} ${formatPlannerPercentUnits(row.weightPercent, compareDecimal(row.weightPercent, '1') === -1 ? 1 : 0)}`;
    }

    function priceHelp(asset: DraftAsset): string {
        return $t(`${KEY}.priceCopiedHelp`, {
            default: 'Latest price stored in LibreFolio, dated {date}{hasSource, select, yes { (source: {source})} other {}}. It is read again just before the calculation.',
            values: {date: formatPlannerDate(asset.price?.referenceDate, $locale), hasSource: asset.priceSource ? 'yes' : 'no', source: asset.priceSource ?? ''},
        });
    }

    function manualPriceHelp(asset: DraftAsset): string {
        const copied = asset.copiedPrice;
        return $t(`${KEY}.priceManualHelp`, {
            default: 'Your price: the calculation uses it as typed and never reads it again. {hasCopy, select, yes {LibreFolio has {price}, dated {date}: «Auto» brings it back.} other {LibreFolio has no stored price for this Asset.}}',
            values: {hasCopy: copied ? 'yes' : 'no', price: copied ? formatPlannerPricePlain(copied.amount, copied.currency) : '', date: formatPlannerDate(copied?.referenceDate, $locale)},
        });
    }

    function unitsText(price: NonNullable<DraftAsset['price']>): string {
        return $t(`${KEY}.perUnits`, {default: '/ {units} {count, plural, one {unit} other {units}}', values: {units: formatPlannerPlainDecimal(price.quoteBaseQuantity), count: Number(price.quoteBaseQuantity)}});
    }

    /** Manual starts from the price on screen; without one, in the currency LibreFolio prices the Asset in. */
    function switchPrice(asset: DraftAsset, manual: boolean): void {
        const currency = asset.copiedPrice?.currency || (asset.sourceAssetId !== null ? getAssetInfo(asset.sourceAssetId)?.currency : '') || draft.data.valuationCurrency;
        setPriceManual(draft, asset.key, manual, currency);
        // Back to Auto with nothing stored yet: try the read again now, not only at «Calcola».
        if (!manual && asset.sourceAssetId !== null && asset.price === null) readFacts([asset.sourceAssetId]);
    }

    function setPriceAmount(asset: DraftAsset, value: string): void {
        if (asset.price) asset.price.amount = value;
    }

    function askRemove(asset: DraftAsset): void {
        removal = {key: asset.key, name: asset.name, impact: draft.assetRemovalImpact(asset.key)};
    }

    function confirmRemoval(): void {
        if (removal) draft.removeAsset(removal.key);
        removal = null;
    }
</script>

<div class="space-y-4" data-testid="pac-planner-assets" aria-busy={reader.busy} data-busy={reader.busy ? 'true' : 'false'}>
    <div class="flex flex-wrap items-center gap-2">
        <div class="w-full max-w-sm">
            <AssetSelect bind:value={searchValue} filter={(info) => !inDraft.has(domainAssetKey(info.id))} placeholder={$t(`${KEY}.search`, {default: 'Search Asset'})} testid="pac-planner-asset-search" onchange={addFromSearch} />
        </div>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-owned-assets-open" onclick={() => (owning = true)}>
            <Briefcase class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.ownedAssets.open', {default: 'Your Assets'})}
        </button>
        <HelpTip
            label={$t(`${KEY}.autoLabel`, {default: 'Data from LibreFolio'})}
            help={$t(`${KEY}.priceAuto`, {default: 'An Asset added from LibreFolio arrives with its latest stored price and its composition. The composition is the one of LibreFolio and is not changed here. The price is «Auto»: read again just before the calculation; switch it to «Manual» to use a price of your own. No provider is called: the prices are the ones LibreFolio already has.'})}
            testid="pac-planner-assets-auto-help"
        />
        <button type="button" class="{BUTTON_SECONDARY} ml-auto" data-testid="pac-planner-asset-add" onclick={() => (editing = {key: null})}>
            <Plus class="h-4 w-4" aria-hidden="true" />{$t(`${KEY}.addManual`, {default: 'Manual Asset'})}
        </button>
    </div>

    {#if reader.error}
        <div class="{NOTICE.warning} flex flex-wrap items-start justify-between gap-2" role="alert" data-testid="pac-planner-assets-price-error">
            <p>{$t(reader.error.key, {default: reader.error.fallback})}</p>
            <div class="flex shrink-0 gap-3">
                {#if reader.canRetry}
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-assets-read-retry" onclick={() => reader.retry(draft, accountGeneration)}>{$t('common.retry', {default: 'Retry'})}</button>
                {/if}
                <button type="button" class={BUTTON_LINK} data-testid="pac-planner-assets-price-error-dismiss" onclick={() => reader.dismiss()}>{$t('common.close', {default: 'Close'})}</button>
            </div>
        </div>
    {/if}

    {#if draft.orderedAssets.length > 0}
        <OrderableList items={draft.orderedAssets} keyFn={(asset) => asset.key} onReorder={(next) => draft.reorderAssets(next.map((asset) => asset.key))}>
            {#snippet children({item: asset})}
                {@const reading = reader.isReading(asset.sourceAssetId)}
                {@const priceNotStored = !asset.price && reader.notStored(draft, asset.sourceAssetId)}
                {@const lacking = reader.lackingOf(draft, asset.sourceAssetId)}
                <section
                    class="space-y-3 p-1 sm:p-2"
                    data-testid="pac-planner-asset"
                    data-asset-key={asset.key}
                    data-origin={asset.origin}
                    data-price={priceMissing(asset) ? 'missing' : 'set'}
                    data-price-mode={asset.sourceAssetId === null ? 'manual-asset' : asset.priceManual ? 'manual' : 'auto'}
                    data-price-read={!asset.price && reading ? 'reading' : priceNotStored ? 'not-stored' : 'idle'}
                    data-exposures={asset.exposures.length > 0 ? 'set' : reading ? 'reading' : 'missing'}
                >
                    <div class="flex flex-wrap items-start justify-between gap-2">
                        <div class="flex min-w-0 flex-1 basis-56 items-center gap-2.5">
                            <AssetIcon iconUrl={asset.iconUrl} assetType={asset.assetClass.toUpperCase()} altText="" size="md" />
                            <div class="min-w-0 flex-1">
                                <h3 class="min-w-0 font-semibold text-gray-900 dark:text-gray-100" data-testid="pac-planner-asset-title">
                                    <span use:scrollOnOverflow class={overflowScrollTextClass} title={title(asset)}>{title(asset) || '—'}</span>
                                </h3>
                                <p class="flex flex-wrap items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                                    <span data-testid="pac-planner-asset-type">{typeText(asset)}</span>
                                    {#if asset.origin === 'manual'}<OriginBadge origin="manual" testid="pac-planner-asset-origin" />{/if}
                                    {#if !asset.active}<span class={BADGE.warning}>{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>{/if}
                                    {#if priceMissing(asset) && !reading}<span class={BADGE.danger} data-testid="pac-planner-asset-alert" aria-label={$t(`${KEY}.priceMissingShort`, {default: 'Price missing'})}>!</span>{/if}
                                </p>
                            </div>
                        </div>
                        <div class="flex shrink-0 gap-2">
                            {#if asset.origin === 'manual'}
                                <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-asset-edit" onclick={() => (editing = {key: asset.key})}>
                                    <Pencil class="h-4 w-4" aria-hidden="true" />{$t('common.edit', {default: 'Edit'})}
                                </button>
                            {/if}
                            <button type="button" class={BUTTON_DANGER} data-testid="pac-planner-asset-remove" onclick={() => askRemove(asset)}>
                                <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
                            </button>
                        </div>
                    </div>

                    <dl class="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-4 gap-y-2 text-sm">
                        <dt class="text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.planner.assetEditor.price', {default: 'Price'})}</dt>
                        <dd class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                            {#if asset.priceManual && asset.price}
                                <span class="flex flex-wrap items-center gap-2" data-testid="pac-planner-asset-price-manual">
                                    <span class="w-36">
                                        <ExactDecimalInput
                                            value={asset.price.amount}
                                            step="0.01"
                                            className={INPUT}
                                            ariaLabel={$t('tools.pacAllocator.planner.assetEditor.price', {default: 'Price'})}
                                            testid="pac-planner-asset-price-input"
                                            onchange={(value) => setPriceAmount(asset, value)}
                                        />
                                    </span>
                                    <CurrencyCode code={asset.price.currency} />
                                    <span class={HINT}>{unitsText(asset.price)}</span>
                                    <HelpTip label={$t('tools.pacAllocator.planner.assetEditor.price', {default: 'Price'})} help={manualPriceHelp(asset)} testid="pac-planner-asset-price-help" />
                                </span>
                            {:else if asset.price}
                                <span class="flex flex-wrap items-center gap-2" data-testid="pac-planner-asset-price">
                                    <span class="tabular-nums text-gray-900 dark:text-gray-100">
                                        {$t(`${KEY}.priceLine`, {
                                            default: '{price} / {units} {count, plural, one {unit} other {units}}',
                                            values: {price: formatPlannerPricePlain(asset.price.amount, asset.price.currency), units: formatPlannerPlainDecimal(asset.price.quoteBaseQuantity), count: Number(asset.price.quoteBaseQuantity)},
                                        })}
                                    </span>
                                    {#if asset.priceStamp}
                                        <HelpTip label={$t('tools.pacAllocator.planner.assetEditor.price', {default: 'Price'})} help={priceHelp(asset)} testid="pac-planner-asset-price-help" />
                                    {/if}
                                </span>
                            {:else if reading}
                                <span class="flex items-center gap-2 {HINT}" role="status" data-testid="pac-planner-asset-price-reading">
                                    <LoaderCircle class="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />{$t(`${KEY}.priceReading`, {default: 'Reading the data stored in LibreFolio…'})}
                                </span>
                            {:else if priceNotStored}
                                <span class="flex flex-wrap items-center gap-x-2 gap-y-1" data-testid="pac-planner-asset-no-price">
                                    <span class="text-amber-800 dark:text-amber-200">{$t(`${KEY}.priceNotStored`, {default: 'LibreFolio has no stored price for this Asset: add one on its page, or switch to «Manual» and type it. In «Auto» it is read again just before the calculation.'})}</span>
                                    {#if asset.sourceAssetId !== null}
                                        <a class={BUTTON_LINK} href="/assets/{asset.sourceAssetId}" target="_blank" rel="noopener noreferrer" data-testid="pac-planner-asset-open-page">
                                            {$t(`${KEY}.openAssetPage`, {default: 'Open the Asset page'})}<ExternalLink class="h-3.5 w-3.5" aria-hidden="true" />
                                        </a>
                                    {/if}
                                </span>
                            {:else}
                                <span class="text-amber-800 dark:text-amber-200" data-testid="pac-planner-asset-no-price">{$t(`${KEY}.priceMissing`, {default: 'Price missing: it stays in the draft, the calculation will ask for it.'})}</span>
                            {/if}
                            {#if asset.sourceAssetId !== null}
                                <span class="ml-auto">
                                    <AutoManualToggle
                                        manual={asset.priceManual}
                                        label={$t(`${KEY}.priceMode`, {default: 'Price of {name}', values: {name: title(asset)}})}
                                        testid="pac-planner-asset-price-mode"
                                        onchange={(manual) => switchPrice(asset, manual)}
                                    />
                                </span>
                            {/if}
                        </dd>

                        <dt class="flex items-center gap-0.5 text-gray-500 dark:text-gray-400">
                            {$t(`${KEY}.composition`, {default: 'Composition'})}
                            <HelpTip
                                label={$t(`${KEY}.composition`, {default: 'Composition'})}
                                help={$t(`${KEY}.compositionHelp`, {default: 'What the Asset holds, by sector and geography. It is used only by the result report, to show the portfolio before and after: it does not change the orders. A share that is not indicated counts as “Uncategorised”.'})}
                            />
                        </dt>
                        <dd class="min-w-0 space-y-0.5" data-testid="pac-planner-asset-exposures">
                            {#if asset.exposures.length === 0 && reading}
                                <span class="flex items-center gap-2 {HINT}" role="status">
                                    <LoaderCircle class="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />{$t(`${KEY}.priceReading`, {default: 'Reading the data stored in LibreFolio…'})}
                                </span>
                            {:else}
                                {#each COMPOSITION_DIMENSIONS as dimension (dimension)}
                                    {@const rows = rowsOf(asset, dimension)}
                                    {@const whole = isWhole(rows)}
                                    <p class="text-gray-900 dark:text-gray-100" data-testid="pac-planner-asset-dimension" data-dimension={dimension} data-state={rows.length > 0 ? 'set' : lacking.includes(dimension) ? 'not-stored' : 'missing'}>
                                        <span class="text-gray-500 dark:text-gray-400">{dimensionName(dimension)}:</span>
                                        {#if rows.length > 0}
                                            {rows
                                                .slice(0, VISIBLE_CATEGORIES)
                                                .map((row) => categoryText(row, whole))
                                                .join(' · ')}
                                            {#if rows.length > VISIBLE_CATEGORIES}
                                                <Tooltip text={rows.slice(VISIBLE_CATEGORIES).map((row) => categoryText(row, false)).join(' · ')} position="top" maxWidth="360px">
                                                    <span class={BADGE.neutral} data-testid="pac-planner-asset-dimension-more">+{rows.length - VISIBLE_CATEGORIES}</span>
                                                </Tooltip>
                                            {/if}
                                        {:else if lacking.includes(dimension)}
                                            <span class="text-gray-500 dark:text-gray-400">{$t(`${KEY}.dimensionNotStored`, {default: 'no data in LibreFolio'})}</span>
                                        {:else}
                                            <span class="text-gray-500 dark:text-gray-400">{$t(`${KEY}.dimensionNone`, {default: '{dimension, select, geography {not indicated} other {not indicated}}', values: {dimension}})}</span>
                                        {/if}
                                    </p>
                                {/each}
                            {/if}
                        </dd>
                    </dl>
                </section>
            {/snippet}
        </OrderableList>
    {/if}

    {#if draft.data.assets.length === 0}
        <p class={NOTICE.info} data-testid="pac-planner-assets-empty">{$t('tools.pacAllocator.planner.assets.empty', {default: 'Search an Asset of the database or add a manual one: the Tool works without any Asset in the database.'})}</p>
    {/if}
</div>

{#if owning}
    <OwnedAssetsDialog {draft} {accountGeneration} onadded={readFacts} onclose={() => (owning = false)} />
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
