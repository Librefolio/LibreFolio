<script lang="ts">
    import {untrack} from 'svelte';
    import {Plus, Trash2} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {restoreCopiedExposures, restoreCopiedPrice} from '../copies';
    import {EXPOSURE_DIMENSIONS, nowTimestamp, sameExposures, samePrice, type DraftAsset, type ExposureDimension, type PlannerDraft} from '../draft.svelte';
    import {formatPlannerTimestamp} from '../format';
    import {DIMENSION_FALLBACKS} from '../labels';
    import {toPlannerId} from '../source';
    import {BUTTON_LINK, BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, INPUT, LABEL, NOTICE, SECTION_TITLE} from '../ui';
    import AgeLabel from '../shared/AgeLabel.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        /** `null` opens an empty manual Asset. */
        assetKey: string | null;
        onclose: () => void;
    }

    let {draft, assetKey, onclose}: Props = $props();

    const ids = $props.id();
    const CLASS_SUGGESTIONS = ['etf', 'stock', 'bond', 'fund', 'crypto', 'commodity', 'cash', 'real_estate'];

    function emptyManual(): DraftAsset {
        return {
            key: '',
            origin: 'manual',
            sourceAssetId: null,
            manualId: '',
            name: '',
            ticker: '',
            assetClass: 'etf',
            iconUrl: null,
            active: true,
            price: {amount: '', currency: draft.data.valuationCurrency, quoteBaseQuantity: '1', referenceDate: draft.data.asOf},
            copiedPrice: null,
            priceStamp: null,
            priceSource: null,
            exposures: [],
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
    let error = $state<{key: string; fallback: string} | null>(null);

    const dimensionOptions = $derived(EXPOSURE_DIMENSIONS.map((dimension) => ({value: dimension, label: $t(`tools.pacAllocator.planner.dimensions.${dimension}`, {default: DIMENSION_FALLBACKS[dimension]})})));
    const priceModified = $derived(working.priceStamp !== null && !samePrice(working.price, working.copiedPrice));
    const exposuresModified = $derived(working.exposureStamp !== null && !sameExposures(working.exposures, working.copiedExposures));

    function addPrice(): void {
        working.price = {amount: '', currency: draft.data.valuationCurrency, quoteBaseQuantity: '1', referenceDate: draft.data.asOf};
    }

    function addExposure(): void {
        working.exposures.push({key: draft.nextId('exposure'), dimension: 'asset_type', categoryId: '', label: '', weightPercent: '', provenanceId: null});
    }

    function setDimension(index: number, value: string): void {
        if ((EXPOSURE_DIMENSIONS as readonly string[]).includes(value)) working.exposures[index].dimension = value as ExposureDimension;
    }

    function removeExposure(key: string): void {
        working.exposures = working.exposures.filter((row) => row.key !== key);
    }

    function restorePrice(): void {
        restoreCopiedPrice(working);
    }

    function restoreExposures(): void {
        restoreCopiedExposures(draft, working);
    }

    function apply(): void {
        error = null;
        const next = $state.snapshot(working) as DraftAsset;
        next.name = next.name.trim();
        next.ticker = next.ticker.trim();
        next.assetClass = next.assetClass.trim();
        if (next.name === '') {
            error = {key: 'tools.pacAllocator.planner.problems.assetNameMissing', fallback: 'The Asset name is empty.'};
            return;
        }
        if (next.origin === 'manual') {
            const manualId = (next.manualId ?? '').trim();
            const key = manualId === '' ? null : toPlannerId(['manual-asset', manualId].join(':'));
            if (manualId === '') {
                error = {key: 'tools.pacAllocator.planner.assetEditor.idMissing', fallback: 'The instrument ID is required.'};
                return;
            }
            if (key === null) {
                error = {key: 'tools.pacAllocator.planner.assetEditor.idTooLong', fallback: 'The instrument ID is too long.'};
                return;
            }
            if (isNew && draft.asset(key)) {
                error = {key: 'tools.pacAllocator.planner.assetEditor.idDuplicate', fallback: 'This ID is already in the draft: edit that Asset instead of adding it twice.'};
                return;
            }
            next.manualId = manualId;
            if (isNew) next.key = key;
        }
        if (isNew) draft.addAsset(next);
        else draft.replaceAsset(next);
        onclose();
    }

    const title = $derived(working.origin === 'manual' ? $t('tools.pacAllocator.planner.assetEditor.manualTitle', {default: 'Manual Asset'}) : $t('tools.pacAllocator.planner.assetEditor.title', {default: 'Configure {name} · scenario data (the Asset is not changed)', values: {name: working.name}}));
</script>

<PlannerDialog open {title} testid="pac-planner-asset-editor" {onclose} maxWidth="4xl">
    <section class="space-y-2" aria-labelledby="{ids}-identity">
        <h3 id="{ids}-identity" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.assetEditor.identity', {default: 'Identity'})}</h3>
        {#if working.origin === 'manual'}
            <div class="grid gap-3 sm:grid-cols-2">
                <label>
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.manualId', {default: 'Instrument ID'})} *</span>
                    <input class={INPUT} bind:value={working.manualId} disabled={!isNew} maxlength="110" placeholder={$t('tools.pacAllocator.planner.assetEditor.manualIdPlaceholder', {default: 'ISIN or a unique ID of the scenario'})} data-testid="pac-planner-asset-editor-id" />
                </label>
                <label>
                    <span class={LABEL}>{$t('common.name', {default: 'Name'})} *</span>
                    <input class={INPUT} bind:value={working.name} maxlength="128" data-testid="pac-planner-asset-editor-name" />
                </label>
                <label>
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.ticker', {default: 'Ticker'})}</span>
                    <input class={INPUT} bind:value={working.ticker} maxlength="128" data-testid="pac-planner-asset-editor-ticker" />
                </label>
                <label>
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.class', {default: 'Class'})} * <span class={HINT}>{$t('tools.pacAllocator.planner.assetEditor.classHint', {default: '(lowercase code)'})}</span></span>
                    <input class={INPUT} bind:value={working.assetClass} list="{ids}-classes" maxlength="96" data-testid="pac-planner-asset-editor-class" />
                </label>
            </div>
            <p class={HINT}>{$t('tools.pacAllocator.planner.assetEditor.neverByName', {default: 'Never merge Assets by name: the same ID reuses the same identity in the draft.'})}</p>
        {:else}
            <div class="flex flex-wrap items-center gap-2 text-sm">
                <OriginBadge origin="copied" testid="pac-planner-asset-editor-origin" />
                <span class="font-medium">{working.ticker ? [working.ticker, working.name].join(' ') : working.name}</span>
            </div>
            <label class="block max-w-xs">
                <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.class', {default: 'Class'})} * <span class={HINT}>{$t('tools.pacAllocator.planner.assetEditor.classHint', {default: '(lowercase code)'})}</span></span>
                <input class={INPUT} bind:value={working.assetClass} list="{ids}-classes" maxlength="96" data-testid="pac-planner-asset-editor-class" />
            </label>
        {/if}
        <datalist id="{ids}-classes">
            {#each CLASS_SUGGESTIONS as code (code)}<option value={code}></option>{/each}
        </datalist>
    </section>

    <section class="space-y-2" aria-labelledby="{ids}-price">
        <h3 id="{ids}-price" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.assetEditor.price', {default: 'Price'})}</h3>
        {#if working.price}
            {#if working.priceStamp}
                <div class="flex flex-wrap items-center gap-2 text-sm">
                    <OriginBadge origin="copied" modified={priceModified} when={formatPlannerTimestamp(draft.copyRecord(working.priceStamp)?.capturedAt, $locale)} testid="pac-planner-asset-editor-price-origin" />
                    {#if working.priceSource}<span class={HINT}>{working.priceSource}</span>{/if}
                    {#if priceModified}
                        <button type="button" class={BUTTON_LINK} data-testid="pac-planner-asset-editor-price-restore" onclick={restorePrice}>{$t('tools.pacAllocator.planner.restoreCopied', {default: 'Restore the copied value'})}</button>
                    {/if}
                </div>
            {/if}
            <div class="grid gap-3 sm:grid-cols-4">
                <label for="{ids}-amount">
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.priceAmount', {default: 'Price'})} *</span>
                    <ExactDecimalInput id="{ids}-amount" bind:value={working.price.amount} step="0.01" className={INPUT} testid="pac-planner-asset-editor-price" />
                </label>
                <div>
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.priceCurrency', {default: 'Currency'})} *</span>
                    <CurrencySearchSelect bind:value={working.price.currency} testId="pac-planner-asset-editor-price-currency" />
                </div>
                <label for="{ids}-basis">
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.quoteBasis', {default: 'Units per price'})} *</span>
                    <ExactDecimalInput id="{ids}-basis" bind:value={working.price.quoteBaseQuantity} step="1" className={INPUT} testid="pac-planner-asset-editor-basis" />
                </label>
                <div>
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.priceDate', {default: 'Date'})} *</span>
                    <SingleDatePicker
                        value={working.price.referenceDate}
                        label={$t('tools.pacAllocator.planner.assetEditor.priceDate', {default: 'Date'})}
                        inputStyle
                        testid="pac-planner-asset-editor-price-date"
                        onchange={(date) => {
                            if (working.price) working.price.referenceDate = date;
                        }}
                    />
                </div>
            </div>
            <div class="flex flex-wrap items-center gap-2">
                <AgeLabel date={working.price.referenceDate || null} asOf={draft.data.asOf} manual={!working.priceStamp} testid="pac-planner-asset-editor-price-age" />
                <span class={HINT}>{$t('tools.pacAllocator.planner.assetEditor.quoteBasisHint', {default: "'Units per price' says how many units the source price represents; it is not an order step."})}</span>
            </div>
            <button type="button" class={BUTTON_LINK} data-testid="pac-planner-asset-editor-price-clear" onclick={() => (working.price = null)}>
                {$t('tools.pacAllocator.planner.assetEditor.priceClear', {default: 'No price: the calculation will ask for it'})}
            </button>
        {:else}
            <p class={NOTICE.warning} data-testid="pac-planner-asset-editor-no-price">{$t('tools.pacAllocator.planner.assets.priceMissing', {default: 'Price missing: it stays in the draft, the calculation will ask for it.'})}</p>
            <div class="flex flex-wrap gap-2">
                <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-asset-editor-price-add" onclick={addPrice}>
                    <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.assetEditor.priceAdd', {default: 'Enter a price'})}
                </button>
                {#if working.copiedPrice}
                    <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-asset-editor-price-restore" onclick={restorePrice}>{$t('tools.pacAllocator.planner.restoreCopied', {default: 'Restore the copied value'})}</button>
                {/if}
            </div>
        {/if}
    </section>

    <section class="space-y-2" aria-labelledby="{ids}-exposures">
        <h3 id="{ids}-exposures" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.assetEditor.exposures', {default: 'Exposures (optional)'})}</h3>
        {#if working.exposureStamp}
            <div class="flex flex-wrap items-center gap-2 text-sm">
                <OriginBadge origin="copied" modified={exposuresModified} when={formatPlannerTimestamp(draft.copyRecord(working.exposureStamp)?.capturedAt, $locale)} testid="pac-planner-asset-editor-exposures-origin" />
                {#if exposuresModified && working.copiedExposures}
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-asset-editor-exposures-restore" onclick={restoreExposures}>{$t('tools.pacAllocator.planner.restoreCopied', {default: 'Restore the copied value'})}</button>
                {/if}
            </div>
        {/if}
        <ul class="space-y-2">
            {#each working.exposures as exposure, index (exposure.key)}
                <li class="grid items-end gap-2 sm:grid-cols-[10rem_minmax(0,1fr)_minmax(0,1fr)_7rem_auto]" data-testid="pac-planner-exposure" data-dimension={exposure.dimension}>
                    <div>
                        <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.dimension', {default: 'Dimension'})}</span>
                        <SimpleSelect value={exposure.dimension} options={dimensionOptions} compact testId="pac-planner-exposure-dimension" onchange={(value) => setDimension(index, value)} />
                    </div>
                    <label>
                        <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.categoryId', {default: 'Category ID'})}</span>
                        <input class={INPUT} bind:value={exposure.categoryId} maxlength="120" data-testid="pac-planner-exposure-category" />
                    </label>
                    <label>
                        <span class={LABEL}>{$t('tools.pacAllocator.planner.assetEditor.categoryLabel', {default: 'Label'})}</span>
                        <input class={INPUT} bind:value={exposure.label} maxlength="128" data-testid="pac-planner-exposure-label" />
                    </label>
                    <label for="{ids}-{exposure.key}-weight">
                        <span class={LABEL}>%</span>
                        <ExactDecimalInput id="{ids}-{exposure.key}-weight" bind:value={exposure.weightPercent} step="1" max="100" className={INPUT} testid="pac-planner-exposure-weight" />
                    </label>
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-exposure-remove" onclick={() => removeExposure(exposure.key)}>
                        <Trash2 class="h-4 w-4" aria-hidden="true" /><span class="sr-only">{$t('common.remove', {default: 'Remove'})}</span>
                    </button>
                </li>
            {/each}
        </ul>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-exposure-add" onclick={addExposure}>
            <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.assetEditor.exposureAdd', {default: 'Add exposure row'})}
        </button>
        <p class={HINT}>{$t('tools.pacAllocator.planner.assetEditor.unclassified', {default: "The share not declared goes to the backend 'Uncategorised' row."})}</p>
        <p class={HINT}>{$t('tools.pacAllocator.planner.assetEditor.overHundred', {default: 'A dimension summing over 100%: the backend rejects it as invalid input.'})}</p>
    </section>

    {#if error}
        <p class={NOTICE.danger} role="alert" data-testid="pac-planner-asset-editor-error">{$t(error.key, {default: error.fallback})}</p>
    {/if}

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-asset-editor-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-asset-editor-apply" onclick={apply}>{$t('tools.pacAllocator.planner.applyToDraft', {default: 'Apply to the draft'})}</button>
    {/snippet}
</PlannerDialog>
