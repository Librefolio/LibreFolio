<!--
  TxFormSingleSection — the single-row form: date, type, quantity and cash, asset, broker, and the cost basis of an adjustment.

  Cut from TransactionFormModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import BrokerSearchSelect from '$lib/components/ui/select/BrokerSearchSelect.svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import ExactQuantityInput from '$lib/components/ui/input/ExactQuantityInput.svelte';
    import CompactCashCell from '$lib/features/transactions/form/CompactCashCell.svelte';
    import TransactionTypeSearchSelect from '../TransactionTypeSearchSelect.svelte';
    import WacPreviewSection from '../wac/WacPreviewSection.svelte';
    import {getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getTransactionTypeIconUrl, type PairFormLayout, type TransactionTypeCode, getTypeRule} from '$lib/features/transactions/transactionTypeStore';
    import {exactDecimalSign} from '$lib/features/transactions/txPayloadHelpers';
    import {exceedsSignificantDigits, REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import type {BrokerInfo} from '$lib/stores/reference/brokerStore';
    import type {FormDraft, TxFormWacResult} from './txFormTypes';

    interface Props {
        open: boolean;
        openKey: number;
        pendingTxIds: Set<number> | null;
        costBasisMode: 'auto' | 'manual';
        createAssetOpen: boolean;
        createBrokerOpen: boolean;
        draft: FormDraft;
        wacCurrencyHint: string | null;
        allowedTypes: TransactionTypeCode[] | undefined;
        autocompleteNonce: string;
        brokerIdValue: number | null;
        rowSaved: boolean;
        brokerImmutable: boolean;
        brokers: BrokerInfo[];
        brokersForSelect: Array<{id: number; name: string; icon_url?: string | null}>;
        cashHint: string;
        cashLabel: string;
        displayedCostBasis: {code: string; amount: string} | null;
        externalWacResult: TxFormWacResult | null;
        isReadonly: boolean;
        pairLayout: PairFormLayout | null;
        qtyHint: string;
        qtyLabel: string;
        quantityHintId: string;
        quantityInputId: string;
        quantityInputSignRule: 'positive' | 'nonzero' | 'zero' | 'any';
        rule: ReturnType<typeof getTypeRule>;
        showCostBasisField: boolean;
        typeImmutable: boolean;
        wacAvailableCurrencies: string[];
        handleSyncFx: () => Promise<void>;
        onCostBasisChange: (next: {code: string; amount: string} | null) => void;
        onDateMainValidityChange: (state: {valid: boolean}) => void;
        onQuantityValidityChange: (state: {valid: boolean}) => void;
        onWacCurrencyChange: (code: string) => void;
        setAsset: (v: number | null) => void;
        setBroker: (v: number) => void;
        setCash: (v: {code: string; amount: string} | null) => void;
        setDate: (v: string) => void;
        setQuantity: (v: string) => void;
        setType: (v: string) => void;
    }

    let {
        open,
        openKey,
        pendingTxIds,
        costBasisMode = $bindable(),
        createAssetOpen = $bindable(),
        createBrokerOpen = $bindable(),
        draft = $bindable(),
        wacCurrencyHint,
        allowedTypes,
        autocompleteNonce,
        brokerIdValue,
        rowSaved,
        brokerImmutable,
        brokers,
        brokersForSelect,
        cashHint,
        cashLabel,
        displayedCostBasis,
        externalWacResult,
        isReadonly,
        pairLayout,
        qtyHint,
        qtyLabel,
        quantityHintId,
        quantityInputId,
        quantityInputSignRule,
        rule,
        showCostBasisField,
        typeImmutable,
        wacAvailableCurrencies,
        handleSyncFx,
        onCostBasisChange,
        onDateMainValidityChange,
        onQuantityValidityChange,
        onWacCurrencyChange,
        setAsset,
        setBroker,
        setCash,
        setDate,
        setQuantity,
        setType,
    }: Props = $props();

    // B-48: the reason a quantity or a cash amount past the significant digits is refused, said under the field.
    let quantitySignificantError = $derived(exceedsSignificantDigits(draft.quantity, REAL_SIGNIFICANT_DIGITS));
    let cashSignificantError = $derived(exceedsSignificantDigits(draft.cash?.amount, REAL_SIGNIFICANT_DIGITS));
</script>

<!-- Required section -->
<fieldset class="border border-lf-subtle rounded-lg p-4" data-testid="tx-form-required" use:guideAnchor={'transaction.create.amounts'}>
    <legend class="text-xs font-semibold uppercase tracking-wide text-lf-muted px-1">{$t('transactions.form.sectionRequired')}</legend>

    <!-- Reordered to match table column order (Bugfix-1 §U5):
         Date → Type → Quantity → Cash → Asset → Broker.
         Bugfix-5 §U21: Date+Type are kept in a 2-col mini-grid
         even on mobile (always-on, never wraps to 1-col); Qty/Cash
         get their own sub-grid that collapses to a single
         full-width Cash row when the type forces quantity=0. -->
    <div class="grid grid-cols-2 gap-3 text-sm">
        <!-- Date -->
        <div class="flex flex-col gap-1" data-testid="tx-form-date-wrap">
            <span class="text-xs text-lf-muted">{$t('common.date')}</span>
            {#if isReadonly}
                <div class="px-3 py-2 bg-lf-panel border border-lf-subtle rounded-lg text-sm text-lf-secondary" data-testid="tx-form-date-readonly">{draft.date || '—'}</div>
            {:else}
                <SingleDatePicker bind:value={draft.date} label="" inputStyle={true} onchange={(d) => setDate(d)} onvaliditychange={onDateMainValidityChange} />
            {/if}
        </div>

        <!-- Type -->
        <div class="flex flex-col gap-1" data-testid="tx-form-type-wrap" use:guideAnchor={'transaction.create.basics'}>
            <span class="text-xs text-lf-muted">{$t('common.type')}</span>
            {#if typeImmutable}
                <!-- Bugfix-4 §U17 + Bugfix-5 §U22: render the
                     readonly type as a plain inline [icon] [name]
                     row matching the table cell rendering — icon
                     enlarged (w-6 h-6) so it stays legible
                     alongside the other selectors. -->
                <div class="flex items-center gap-2 px-3 py-2 bg-lf-panel border border-lf-subtle rounded-lg text-sm text-lf-secondary" data-testid="tx-form-type-readonly">
                    <img
                        src={getTransactionTypeIconUrl(draft.type)}
                        alt=""
                        class="w-6 h-6 object-contain shrink-0"
                        onerror={(e) => {
                            const el = e.currentTarget;
                            if (el instanceof HTMLImageElement) el.style.display = 'none';
                        }}
                    />
                    <span class="font-medium">{$t(`transactions.types.${draft.type}`) || draft.type}</span>
                </div>
            {:else}
                <TransactionTypeSearchSelect value={draft.type} onchange={(v) => setType(v)} disabled={isReadonly} types={allowedTypes} compact testid="tx-form-type" />
            {/if}
        </div>
    </div>

    <!-- Quantity + Cash sub-grid.
         Symmetric visibility: forbidden fields disappear entirely,
         the remaining field takes full width (col-span-2). -->
    <div class="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        {#if rule.quantityMode !== 'forbidden' && rule.cashField !== 'forbidden'}
            <!-- Both visible: 2-col layout -->
            <div class="flex flex-col gap-1" data-testid="tx-form-quantity-wrap">
                <span class="text-xs text-lf-muted">
                    {$t('transactions.table.quantity')}{#if qtyLabel}
                        <span class="text-lf-warning">{qtyLabel}</span>{/if}
                </span>
                <ExactQuantityInput
                    value={draft.quantity}
                    onchange={setQuantity}
                    onvaliditychange={onQuantityValidityChange}
                    step="1"
                    maxIntegerDigits={15}
                    maxFractionDigits={10}
                    maxSignificantDigits={REAL_SIGNIFICANT_DIGITS}
                    allowNegative
                    signRule={quantityInputSignRule}
                    resetKey={`${open}:${openKey ?? 0}`}
                    id={quantityInputId}
                    name="qty-{autocompleteNonce}"
                    placeholder="0"
                    ariaLabel={$t('transactions.table.quantity')}
                    ariaDescribedby={qtyHint ? quantityHintId : undefined}
                    ariaErrormessage={quantitySignificantError ? `${quantityInputId}-significant-error` : undefined}
                    className="qty-input !rounded-lg !px-3 !py-2 text-right tabular-nums focus:!ring-2 focus:!ring-lf-focus/30"
                    disabled={isReadonly}
                    testid="tx-form-quantity"
                />
                {#if quantitySignificantError}
                    <p id="{quantityInputId}-significant-error" class="mt-1 text-xs text-lf-danger" data-testid="tx-form-quantity-significant-error">{$t('transactions.errors.significantDigitsExceeded', {values: {max: REAL_SIGNIFICANT_DIGITS}})}</p>
                {/if}
                {#if qtyHint}
                    <span id={quantityHintId} class="text-[10px] text-lf-muted">{qtyHint}</span>
                {/if}
            </div>
            <div class="flex flex-col gap-1" data-testid="tx-form-cash-wrap">
                <span class="text-xs text-lf-muted">
                    {$t('transactions.table.cash')}{rule.cashField === 'required' ? ' *' : ''}{#if cashLabel}
                        <span class="text-lf-warning">{cashLabel}</span>{/if}
                </span>
                <CompactCashCell
                    value={draft.cash}
                    onChange={setCash}
                    signHint={rule.cashSign}
                    disabled={isReadonly}
                    testid="tx-form-cash"
                    defaultCode={(draft.asset_id != null && getAssetInfo(draft.asset_id)?.currency) || 'EUR'}
                    originalCurrency={draft.asset_id != null ? getAssetInfo(draft.asset_id)?.currency : undefined}
                    maxSignificantDigits={REAL_SIGNIFICANT_DIGITS}
                />
                {#if cashSignificantError}
                    <p class="mt-1 text-xs text-lf-danger" data-testid="tx-form-cash-significant-error">{$t('transactions.errors.significantDigitsExceeded', {values: {max: REAL_SIGNIFICANT_DIGITS}})}</p>
                {/if}
                {#if cashHint}
                    <span class="text-[10px] text-lf-muted">{cashHint}</span>
                {/if}
            </div>
        {:else if rule.quantityMode !== 'forbidden'}
            <!-- Only quantity visible (cash forbidden) → full width -->
            <div class="flex flex-col gap-1 col-span-2" data-testid="tx-form-quantity-wrap">
                <span class="text-xs text-lf-muted">
                    {$t('transactions.table.quantity')}{#if qtyLabel}
                        <span class="text-lf-warning">{qtyLabel}</span>{/if}
                </span>
                <ExactQuantityInput
                    value={draft.quantity}
                    onchange={setQuantity}
                    onvaliditychange={onQuantityValidityChange}
                    step="1"
                    maxIntegerDigits={15}
                    maxFractionDigits={10}
                    maxSignificantDigits={REAL_SIGNIFICANT_DIGITS}
                    allowNegative
                    signRule={quantityInputSignRule}
                    resetKey={`${open}:${openKey ?? 0}`}
                    id={quantityInputId}
                    name="qty-{autocompleteNonce}"
                    placeholder="0"
                    ariaLabel={$t('transactions.table.quantity')}
                    ariaDescribedby={qtyHint ? quantityHintId : undefined}
                    ariaErrormessage={quantitySignificantError ? `${quantityInputId}-significant-error` : undefined}
                    className="qty-input !rounded-lg !px-3 !py-2 text-right tabular-nums focus:!ring-2 focus:!ring-lf-focus/30"
                    disabled={isReadonly}
                    testid="tx-form-quantity"
                />
                {#if quantitySignificantError}
                    <p id="{quantityInputId}-significant-error" class="mt-1 text-xs text-lf-danger" data-testid="tx-form-quantity-significant-error">{$t('transactions.errors.significantDigitsExceeded', {values: {max: REAL_SIGNIFICANT_DIGITS}})}</p>
                {/if}
                {#if qtyHint}
                    <span id={quantityHintId} class="text-[10px] text-lf-muted">{qtyHint}</span>
                {/if}
            </div>
        {:else if rule.cashField !== 'forbidden'}
            <!-- Only cash visible (quantity forbidden) → full width -->
            <div class="flex flex-col gap-1 col-span-2" data-testid="tx-form-cash-wrap">
                <span class="text-xs text-lf-muted flex items-center gap-2">
                    {$t('transactions.table.cash')}{rule.cashField === 'required' ? ' *' : ''}{#if cashLabel}
                        <span class="text-lf-warning">{cashLabel}</span>{/if}
                </span>
                <CompactCashCell
                    value={draft.cash}
                    onChange={setCash}
                    signHint={rule.cashSign}
                    disabled={isReadonly}
                    testid="tx-form-cash"
                    defaultCode={(draft.asset_id != null && getAssetInfo(draft.asset_id)?.currency) || 'EUR'}
                    originalCurrency={draft.asset_id != null ? getAssetInfo(draft.asset_id)?.currency : undefined}
                    maxSignificantDigits={REAL_SIGNIFICANT_DIGITS}
                />
                {#if cashSignificantError}
                    <p class="mt-1 text-xs text-lf-danger" data-testid="tx-form-cash-significant-error">{$t('transactions.errors.significantDigitsExceeded', {values: {max: REAL_SIGNIFICANT_DIGITS}})}</p>
                {/if}
                {#if cashHint}
                    <span class="text-[10px] text-lf-muted">{cashHint}</span>
                {/if}
                <span class="text-[10px] text-lf-muted italic">💡 {$t('transactions.form.cashLabelTotal')}</span>
            </div>
        {/if}
        <!-- Both forbidden: nothing rendered (no current type uses this) -->
    </div>

    <!-- Asset (full width) -->
    {#if rule.assetField !== 'forbidden'}
        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-asset-wrap">
            <span class="text-xs text-lf-muted"
                >{$t('common.asset')}{rule.assetField === 'required' ? ' *' : ''}{#if rule.assetField === 'optional'}
                    <span class="text-lf-muted italic">({$t('common.optional')})</span>{/if}</span
            >
            <AssetSelect bind:value={draft.asset_id} disabled={isReadonly || rowSaved} onchange={setAsset} testid="tx-form-asset" createLabel={isReadonly || rowSaved ? undefined : $t('assets.create') || 'New asset'} onCreateNew={isReadonly || rowSaved ? undefined : () => (createAssetOpen = true)} />
        </div>
    {/if}

    <!-- Broker (full width, last) -->
    <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-broker-wrap">
        <span class="text-xs text-lf-muted">{$t('transactions.table.broker')}</span>
        {#if brokerImmutable}
            {@const b = brokers.find((br) => br.id === draft.broker_id)}
            <!-- Bugfix-4 §U19: readonly broker also shows the icon
                 (parity with the editable BrokerSearchSelect). -->
            <div class="flex items-center gap-2 px-3 py-2 bg-lf-panel border border-lf-subtle rounded-lg text-sm text-lf-secondary" data-testid="tx-form-broker-readonly">
                <BrokerIcon brokerId={b?.id ?? null} iconUrl={b?.icon_url ?? null} portalUrl={b?.portal_url ?? null} pluginCode={b?.default_import_plugin ?? null} altText={b?.name ?? ''} size="sm" />
                <span class="font-medium">{b?.name ?? `#${draft.broker_id}`}</span>
            </div>
        {:else}
            <BrokerSearchSelect brokers={brokersForSelect} value={brokerIdValue} onchange={(id) => setBroker(id ?? 0)} createLabel={$t('common.createNew') || 'Create new'} onCreateNew={() => (createBrokerOpen = true)} />
        {/if}
    </div>

    <!-- Cost basis override — shown inline for ADJUSTMENT (inside fieldset = mandatory section) -->
    {#if !pairLayout && draft.type === 'ADJUSTMENT' && showCostBasisField}
        <div class="mt-3" data-testid="tx-form-cost-basis-inline">
            <WacPreviewSection
                value={displayedCostBasis}
                onChange={onCostBasisChange}
                mode={costBasisMode}
                defaultCode={draft.cash?.code ?? 'EUR'}
                disabled={isReadonly}
                hideTable={isReadonly}
                testid="tx-form-cost-basis"
                senderBrokerId={draft.broker_id}
                assetId={draft.asset_id}
                txDate={draft.date}
                onModeChange={(m) => (costBasisMode = m)}
                externalResult={externalWacResult}
                {pendingTxIds}
                wacCurrency={wacCurrencyHint}
                onCurrencyChange={onWacCurrencyChange}
                availableCurrencies={wacAvailableCurrencies}
                onOpenFxSync={handleSyncFx}
                quantity={draft.quantity}
            />
            {#if (exactDecimalSign(draft.quantity) ?? 0) > 0 && costBasisMode !== 'auto' && !draft.cost_basis_override?.amount?.trim()}
                <p class="text-xs text-lf-warning mt-1" data-testid="tx-form-cost-basis-warning">
                    {$t('transactions.costBasisOverride.warningAdjustment') ||
                        "The manual cost basis is empty: the transaction can't be saved without it. Enter what these units cost you: 0 for the new shares of a stock split. For a gift, enter 0, or what the donor paid for them: that keeps the weighted average cost, and the gain you may be taxed on, closer to the real ones."}
                </p>
            {/if}
        </div>
    {/if}
</fieldset>
