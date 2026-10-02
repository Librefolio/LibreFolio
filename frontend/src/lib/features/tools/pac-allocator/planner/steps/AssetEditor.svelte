<script lang="ts">
    import {untrack} from 'svelte';
    import {Plus} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import DistributionEditor from '$lib/components/ui/input/DistributionEditor.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import AssetTypeSelect from '$lib/components/ui/select/AssetTypeSelect.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {ASSET_TYPES} from '$lib/utils/assetTypes';
    import {plannerAssetClass} from '../copies';
    import {canonicalInput, compareDecimal, fractionToPercent, percentToFraction, sumControlPercentages} from '../decimal';
    import {nowTimestamp, type DraftAsset, type DraftExposure, type ExposureDimension, type PlannerDraft} from '../draft.svelte';
    import {DIMENSION_FALLBACKS} from '../labels';
    import {BUTTON_LINK, BUTTON_PRIMARY, BUTTON_SECONDARY, INPUT, LABEL_ROW, NOTICE, SECTION_TITLE} from '../ui';
    import HelpTip from '../shared/HelpTip.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';
    const KEY = 'tools.pacAllocator.planner.assetEditor';

    /** Only a manual Asset is edited here: an Asset of LibreFolio keeps the data LibreFolio stores (R8.3). */
    interface Props {
        draft: PlannerDraft;
        /** `null` opens an empty manual Asset. */
        assetKey: string | null;
        onclose: () => void;
    }

    let {draft, assetKey, onclose}: Props = $props();

    const ids = $props.id();

    function emptyManual(): DraftAsset {
        return {
            key: '',
            origin: 'manual',
            sourceAssetId: null,
            name: '',
            ticker: '',
            assetClass: 'etf',
            iconUrl: null,
            active: true,
            price: {amount: '', currency: draft.data.valuationCurrency, quoteBaseQuantity: '1', referenceDate: draft.data.asOf},
            priceManual: false,
            copiedPrice: null,
            priceStamp: null,
            priceSource: null,
            // Like an Asset of LibreFolio, a manual one is wholly of its own type until the user says otherwise.
            exposures: [{key: draft.nextId('exposure'), dimension: 'asset_type', categoryId: 'ETF', label: 'ETF', weightPercent: '100', provenanceId: null}],
            copiedExposures: null,
            exposureStamp: null,
            enteredAt: nowTimestamp(),
        };
    }

    // Mount = open: the editor works on a copy taken once, and writes it back only on apply.
    const initial = untrack(() => {
        const found = assetKey ? draft.asset(assetKey) : undefined;
        return found ? (structuredClone($state.snapshot(found)) as DraftAsset) : emptyManual();
    });
    const isNew = initial.key === '';
    let working = $state<DraftAsset>(initial);
    let error = $state<{key: string; fallback: string; values?: Record<string, string>} | null>(null);

    /** The type is one value, edited beside the identity; the composition is sector and geography. */
    const COMPOSITION: readonly ExposureDimension[] = ['sector', 'geography'];

    /** The shared distribution editor works on fractions keyed by category; the draft keeps exact percent text. */
    let sectorValue = $state<Record<string, number>>(distributionOf('sector'));
    let geographyValue = $state<Record<string, number>>(distributionOf('geography'));

    function addPrice(): void {
        working.price = {amount: '', currency: draft.data.valuationCurrency, quoteBaseQuantity: '1', referenceDate: draft.data.asOf};
    }

    function dimensionName(dimension: ExposureDimension): string {
        return $t(`tools.pacAllocator.planner.dimensions.${dimension}`, {default: DIMENSION_FALLBACKS[dimension]});
    }

    function rowsOf(dimension: ExposureDimension): DraftExposure[] {
        return working.exposures.filter((row) => row.dimension === dimension);
    }

    function distributionOf(dimension: ExposureDimension): Record<string, number> {
        const value: Record<string, number> = {};
        for (const row of rowsOf(dimension)) {
            const category = row.categoryId.trim();
            const fraction = Number(percentToFraction(canonicalInput(row.weightPercent) ?? '') ?? Number.NaN);
            if (category !== '' && Number.isFinite(fraction)) value[category] = fraction;
        }
        return value;
    }

    /** Rows the editor sends back replace the dimension; a category already present keeps its identity. */
    function writeDimension(dimension: ExposureDimension, value: Record<string, number>): void {
        const previous = new Map(rowsOf(dimension).map((row) => [row.categoryId.trim(), row]));
        const rows: DraftExposure[] = Object.entries(value).map(([category, fraction]) => {
            const old = previous.get(category);
            return {
                key: old?.key ?? draft.nextId('exposure'),
                dimension,
                categoryId: category,
                label: old?.label.trim() ? old.label : category,
                weightPercent: Number.isFinite(fraction) ? (fractionToPercent(fraction.toFixed(6)) ?? '') : '',
                provenanceId: old?.provenanceId ?? null,
            };
        });
        working.exposures = [...working.exposures.filter((row) => row.dimension !== dimension), ...rows];
    }

    /** One type row at 100%, matching the type: a picked type replaces the previous one. */
    function withTypeRow(rows: readonly DraftExposure[], assetClass: string): DraftExposure[] {
        const code = assetClass.trim().toUpperCase();
        if (!(ASSET_TYPES as readonly string[]).includes(code)) return [...rows];
        const same = rows.find((row) => row.dimension === 'asset_type' && row.categoryId.trim().toUpperCase() === code);
        const typeRow: DraftExposure = same ? {...same, weightPercent: '100'} : {key: draft.nextId('exposure'), dimension: 'asset_type', categoryId: code, label: code, weightPercent: '100', provenanceId: null};
        return [typeRow, ...rows.filter((row) => row.dimension !== 'asset_type')];
    }

    function setType(value: string): void {
        const next = plannerAssetClass(value);
        if (next === '') return;
        working.assetClass = next;
        working.exposures = withTypeRow(working.exposures, next);
    }

    function pickCategory(dimension: ExposureDimension): string {
        return $t(`${KEY}.pickCategory`, {default: '{dimension, select, asset_type {Choose a type} sector {Choose a sector} other {Choose a country}}', values: {dimension}});
    }

    function compositionHelp(): string {
        const what = $t('tools.pacAllocator.planner.assets.compositionHelp', {default: 'What the Asset holds, by sector and geography. It is used only by the result report, to show the portfolio before and after: it does not change the orders. A share that is not indicated counts as “Uncategorised”.'});
        const weights = $t(`${KEY}.weightsHelp`, {default: 'For each dimension, give the shares in percent. They may add up to less than 100%; over 100% the calculation rejects the data.'});
        return `${what}\n\n${weights}`;
    }

    function apply(): void {
        error = null;
        const next = $state.snapshot(working) as DraftAsset;
        next.name = next.name.trim();
        next.ticker = next.ticker.trim();
        next.assetClass = next.assetClass.trim();
        next.exposures = withTypeRow(next.exposures, next.assetClass);
        if (next.name === '') {
            error = {key: 'tools.pacAllocator.planner.problems.assetNameMissing', fallback: 'The Asset name is empty.'};
            return;
        }
        for (const dimension of COMPOSITION) {
            const total = sumControlPercentages(next.exposures.filter((row) => row.dimension === dimension).map((row) => row.weightPercent));
            if (total !== null && compareDecimal(total, '100') === 1) {
                error = {key: `${KEY}.totalOver`, fallback: '{dimension}: the shares add up to more than 100%. Lower one of them before applying.', values: {dimension: dimensionName(dimension)}};
                return;
            }
        }
        // A manual Asset is its own identity: the draft names it, and two Assets are never merged by name or code.
        if (isNew) {
            next.key = draft.nextId('manual-asset');
            draft.addAsset(next);
        } else draft.replaceAsset(next);
        onclose();
    }

    const title = $t('tools.pacAllocator.planner.assetEditor.manualTitle', {default: 'Manual Asset'});
</script>

{#snippet typePicker()}
    <div data-testid="pac-planner-asset-editor-class">
        <div class={LABEL_ROW}>
            <span>{$t('common.type', {default: 'Type'})} *</span>
            <HelpTip label={$t('common.type', {default: 'Type'})} help={$t(`${KEY}.typeHelp`, {default: 'The kind of instrument, as on the Asset page. It is shown in the result and does not change the orders.'})} />
        </div>
        <AssetTypeSelect
            value={working.assetClass.trim().toUpperCase()}
            testId="pac-planner-asset-editor-type"
            placeholder={pickCategory('asset_type')}
            onchange={setType}
        />
    </div>
{/snippet}

<PlannerDialog open {title} testid="pac-planner-asset-editor" {onclose} maxWidth="4xl">
    <section class="space-y-2" aria-labelledby="{ids}-identity">
        <h3 id="{ids}-identity" class={SECTION_TITLE}>{$t(`${KEY}.identity`, {default: 'Identity'})}</h3>
        <div class="grid gap-3 sm:grid-cols-2">
            <div>
                <div class={LABEL_ROW}><label for="{ids}-name">{$t('common.name', {default: 'Name'})} *</label></div>
                <input id="{ids}-name" class={INPUT} bind:value={working.name} maxlength="128" data-testid="pac-planner-asset-editor-name" />
            </div>
            {@render typePicker()}
            <div>
                <div class={LABEL_ROW}>
                    <label for="{ids}-ticker">{$t(`${KEY}.ticker`, {default: 'Ticker / ISIN'})}</label>
                    <HelpTip label={$t(`${KEY}.ticker`, {default: 'Ticker / ISIN'})} help={$t(`${KEY}.tickerHelp`, {default: 'Optional: a ticker, an ISIN or any code that helps you recognise the Asset in the result. It does not link the Asset to LibreFolio, and two manual Assets are never merged by name or code.'})} />
                </div>
                <input id="{ids}-ticker" class={INPUT} bind:value={working.ticker} maxlength="128" data-testid="pac-planner-asset-editor-ticker" />
            </div>
        </div>
    </section>

    <section class="space-y-2" aria-labelledby="{ids}-price">
        <h3 id="{ids}-price" class={SECTION_TITLE}>{$t(`${KEY}.price`, {default: 'Price'})}</h3>
        {#if working.price}
            <div class="grid gap-3 sm:grid-cols-3">
                <div>
                    <div class={LABEL_ROW}><label for="{ids}-amount">{$t(`${KEY}.priceAmount`, {default: 'Price'})} *</label></div>
                    <ExactDecimalInput id="{ids}-amount" bind:value={working.price.amount} step="0.01" className={INPUT} testid="pac-planner-asset-editor-price" />
                </div>
                <div>
                    <div class={LABEL_ROW}><span>{$t(`${KEY}.priceCurrency`, {default: 'Currency'})} *</span></div>
                    <CurrencySearchSelect bind:value={working.price.currency} compact testId="pac-planner-asset-editor-price-currency" />
                </div>
                <div>
                    <div class={LABEL_ROW}>
                        <label for="{ids}-basis">{$t(`${KEY}.quoteBasis`, {default: 'Units per price'})} *</label>
                        <HelpTip label={$t(`${KEY}.quoteBasis`, {default: 'Units per price'})} help={$t(`${KEY}.quoteBasisHint`, {default: "'Units per price' says how many units the source price represents; it is not an order step."})} />
                    </div>
                    <ExactDecimalInput id="{ids}-basis" bind:value={working.price.quoteBaseQuantity} step="1" className={INPUT} testid="pac-planner-asset-editor-basis" />
                </div>
            </div>
            <button type="button" class={BUTTON_LINK} data-testid="pac-planner-asset-editor-price-clear" onclick={() => (working.price = null)}>
                {$t(`${KEY}.priceClear`, {default: 'No price: the calculation will ask for it'})}
            </button>
        {:else}
            <p class={NOTICE.warning} data-testid="pac-planner-asset-editor-no-price">{$t('tools.pacAllocator.planner.assets.priceMissing', {default: 'Price missing: it stays in the draft, the calculation will ask for it.'})}</p>
            <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-asset-editor-price-add" onclick={addPrice}>
                <Plus class="h-4 w-4" aria-hidden="true" />{$t(`${KEY}.priceAdd`, {default: 'Enter a price'})}
            </button>
        {/if}
    </section>

    <section class="space-y-3" aria-labelledby="{ids}-exposures" data-testid="pac-planner-asset-editor-composition">
        <h3 id="{ids}-exposures" class="flex items-center gap-1 {SECTION_TITLE}">
            {$t('tools.pacAllocator.planner.assets.composition', {default: 'Composition'})}
            <HelpTip label={$t('tools.pacAllocator.planner.assets.composition', {default: 'Composition'})} help={compositionHelp()} />
        </h3>
        <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid="pac-planner-exposure-block" data-dimension="sector">
            <DistributionEditor kind="sector" bind:value={sectorValue} onchange={(value) => writeDimension('sector', value)} zIndex={70} />
        </div>
        <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid="pac-planner-exposure-block" data-dimension="geography">
            <DistributionEditor kind="geographic" bind:value={geographyValue} onchange={(value) => writeDimension('geography', value)} zIndex={70} />
        </div>
    </section>

    {#if error}
        <p class={NOTICE.danger} role="alert" data-testid="pac-planner-asset-editor-error">{$t(error.key, {default: error.fallback, values: error.values})}</p>
    {/if}

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-asset-editor-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-asset-editor-apply" onclick={apply}>{$t('tools.pacAllocator.planner.applyToDraft', {default: 'Apply to the draft'})}</button>
    {/snippet}
</PlannerDialog>
