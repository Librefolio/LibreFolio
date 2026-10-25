<!--
  TxFormPairSection — the paired form (FX, transfer of an asset, transfer of cash): shared fields, then the From and To sides.

  Cut from TransactionFormModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ArrowRight, ArrowDown, Info} from 'lucide-svelte';
    import {getRoleIcon, getRoleIconColor} from '$lib/utils/broker/brokerRoleHelpers';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import BrokerSearchSelect from '$lib/components/ui/select/BrokerSearchSelect.svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import ExactQuantityInput from '$lib/components/ui/input/ExactQuantityInput.svelte';
    import TxCellMark from '$lib/features/transactions/form/TxCellMark.svelte';
    import type {TxFormCell, TxFormCheckKind} from '$lib/features/transactions/form/txFormChecks';
    import CompactCashCell from '$lib/features/transactions/form/CompactCashCell.svelte';
    import TransactionTypeSearchSelect from '../TransactionTypeSearchSelect.svelte';
    import WacPreviewSection from '../wac/WacPreviewSection.svelte';
    import {getBrokerInfo, getBrokerRole, type BrokerInfo} from '$lib/stores/reference/brokerStore';
    import {getTransactionTypeIconUrl, type PairFormLayout, type TransactionTypeCode} from '$lib/features/transactions/transactionTypeStore';
    import {computeFxConversionInfo, buildFxTooltipData, buildFxTooltipHtml} from '$lib/utils/currency/fxConversionHelper';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import {exceedsSignificantDigits, REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';
    import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import type {TXReadItem} from '../types';
    import type {DualDraftTo, FormDraft, TxFormWacResult} from './txFormTypes';

    interface Props {
        open: boolean;
        openKey: number;
        pendingTxIds: Set<number> | null;
        costBasisMode: 'auto' | 'manual';
        createAssetOpen: boolean;
        createBrokerOpen: boolean;
        draft: FormDraft;
        dualTo: DualDraftTo;
        fxMarketPoint: FxDataPoint | null | undefined;
        inaccessiblePartnerBrokerId: number | null;
        partnerRow: TXReadItem | null;
        wacCurrencyHint: string | null;
        allowedTypes: TransactionTypeCode[] | undefined;
        autocompleteNonce: string;
        brokerIdValue: number | null;
        rowSaved: boolean;
        brokerImmutable: boolean;
        brokerToIdValue: number | null;
        brokers: BrokerInfo[];
        brokersForFrom: Array<{id: number; name: string; icon_url?: string | null}>;
        brokersForSelect: Array<{id: number; name: string; icon_url?: string | null}>;
        brokersForTo: Array<{id: number; name: string; icon_url?: string | null}>;
        displayedCostBasis: {code: string; amount: string} | null;
        effectiveDualTo: DualDraftTo;
        externalWacResult: TxFormWacResult | null;
        isReadonly: boolean;
        pairLayout: PairFormLayout | null;
        quantityInputId: string;
        quantityInputSignRule: 'positive' | 'nonzero' | 'zero' | 'any';
        /** V-37b: the cells «Validate now» found wrong, and why. */
        markedCells: Partial<Record<TxFormCell, TxFormCheckKind>>;
        typeImmutable: boolean;
        wacAvailableCurrencies: string[];
        handleSyncFx: () => Promise<void>;
        onCostBasisChange: (next: {code: string; amount: string} | null) => void;
        onDateMainValidityChange: (state: {valid: boolean}) => void;
        onDateToValidityChange: (state: {valid: boolean}) => void;
        onQuantityValidityChange: (state: {valid: boolean}) => void;
        onWacCurrencyChange: (code: string) => void;
        setAsset: (v: number | null) => void;
        setBroker: (v: number) => void;
        setBrokerTo: (v: number) => void;
        setCash: (v: {code: string; amount: string} | null) => void;
        setCashTo: (v: {code: string; amount: string} | null) => void;
        setDate: (v: string) => void;
        setDateTo: (v: string) => void;
        setQuantity: (v: string) => void;
        setType: (v: string) => void;
        swapDualSides: () => void;
    }

    let {
        open,
        openKey,
        pendingTxIds,
        costBasisMode = $bindable(),
        createAssetOpen = $bindable(),
        createBrokerOpen = $bindable(),
        draft = $bindable(),
        dualTo,
        fxMarketPoint,
        inaccessiblePartnerBrokerId,
        partnerRow,
        wacCurrencyHint,
        allowedTypes,
        autocompleteNonce,
        brokerIdValue,
        rowSaved,
        brokerImmutable,
        brokerToIdValue,
        brokers,
        brokersForFrom,
        brokersForSelect,
        brokersForTo,
        displayedCostBasis,
        effectiveDualTo,
        externalWacResult,
        isReadonly,
        pairLayout,
        quantityInputId,
        quantityInputSignRule,
        markedCells,
        typeImmutable,
        wacAvailableCurrencies,
        handleSyncFx,
        onCostBasisChange,
        onDateMainValidityChange,
        onDateToValidityChange,
        onQuantityValidityChange,
        onWacCurrencyChange,
        setAsset,
        setBroker,
        setBrokerTo,
        setCash,
        setCashTo,
        setDate,
        setDateTo,
        setQuantity,
        setType,
        swapDualSides,
    }: Props = $props();

    // B-48: the reason a quantity or a cash amount past the significant digits is refused, said under the field.
    let quantitySignificantError = $derived(exceedsSignificantDigits(draft.quantity, REAL_SIGNIFICANT_DIGITS));
    let cashSignificantError = $derived(exceedsSignificantDigits(draft.cash?.amount, REAL_SIGNIFICANT_DIGITS));
    let cashToSignificantError = $derived(exceedsSignificantDigits(dualTo.cash?.amount, REAL_SIGNIFICANT_DIGITS));
</script>

<fieldset class="border border-lf-subtle rounded-lg p-4" data-testid="tx-form-required" use:guideAnchor={'transaction.create.amounts'}>
    <legend class="text-xs font-semibold uppercase tracking-wide text-lf-muted px-1">{$t('transactions.form.sectionRequired')}</legend>

    <!-- Type (date is now inside Da/A panels) -->
    <div class="text-sm">
        <!-- Type: editable in create dual mode (W41), readonly in edit/view -->
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

    <!-- FX: shared broker -->
    {#if pairLayout === 'fx'}
        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-broker-wrap">
            <span class="text-xs text-lf-muted">{$t('transactions.table.broker')}</span>
            {#if brokerImmutable}
                {@const b = brokers.find((br) => br.id === draft.broker_id)}
                <div class="flex items-center gap-2 px-3 py-2 bg-lf-panel border border-lf-subtle rounded-lg text-sm text-lf-secondary" data-testid="tx-form-broker-readonly">
                    <BrokerIcon brokerId={b?.id ?? null} iconUrl={b?.icon_url ?? null} portalUrl={b?.portal_url ?? null} pluginCode={b?.default_import_plugin ?? null} altText={b?.name ?? ''} size="sm" />
                    <span class="font-medium">{b?.name ?? `#${draft.broker_id}`}</span>
                </div>
            {:else}
                <TxCellMark cell="broker" marks={markedCells}><BrokerSearchSelect brokers={brokersForSelect} value={brokerIdValue} onchange={(id) => setBroker(id ?? 0)} createLabel={$t('common.createNew') || 'Create new'} onCreateNew={() => (createBrokerOpen = true)} /></TxCellMark>
            {/if}
        </div>
    {/if}

    <!-- Transfer Asset: shared asset + quantity -->
    {#if pairLayout === 'transfer_asset'}
        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-asset-wrap">
            <span class="text-xs text-lf-muted">{$t('common.asset')} *</span>
            <TxCellMark cell="asset" marks={markedCells}
                ><AssetSelect
                    bind:value={draft.asset_id}
                    disabled={isReadonly || rowSaved}
                    onchange={setAsset}
                    testid="tx-form-asset"
                    createLabel={isReadonly || rowSaved ? undefined : $t('assets.create') || 'New asset'}
                    onCreateNew={isReadonly || rowSaved ? undefined : () => (createAssetOpen = true)}
                /></TxCellMark
            >
        </div>
        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-quantity-wrap">
            <span class="text-xs text-lf-muted">
                {$t('transactions.table.quantity')} <span class="text-lf-warning">(+)</span>
            </span>
            <TxCellMark cell="quantity" marks={markedCells}
                ><ExactQuantityInput
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
                    ariaErrormessage={quantitySignificantError ? `${quantityInputId}-significant-error` : undefined}
                    className="qty-input !rounded-lg !px-3 !py-2 text-right tabular-nums focus:!ring-2 focus:!ring-lf-focus/30"
                    disabled={isReadonly}
                    testid="tx-form-quantity"
                /></TxCellMark
            >
            {#if quantitySignificantError}
                <p id="{quantityInputId}-significant-error" class="mt-1 text-xs text-lf-danger" data-testid="tx-form-quantity-significant-error">{$t('transactions.errors.significantDigitsExceeded', {values: {max: REAL_SIGNIFICANT_DIGITS}})}</p>
            {/if}
        </div>
    {/if}

    <!-- Transfer Cash: shared cash -->
    {#if pairLayout === 'transfer_cash'}
        <div class="mt-3 flex flex-col gap-1" data-testid="tx-form-cash-wrap">
            <span class="text-xs text-lf-muted">
                {$t('transactions.table.cash')} *
            </span>
            <TxCellMark cell="cash" marks={markedCells}><CompactCashCell value={draft.cash} onChange={setCash} signHint="positive" disabled={isReadonly} testid="tx-form-cash" defaultCode="EUR" maxSignificantDigits={REAL_SIGNIFICANT_DIGITS} /></TxCellMark>
            {#if cashSignificantError}
                <p class="mt-1 text-xs text-lf-danger" data-testid="tx-form-cash-significant-error">{$t('transactions.errors.significantDigitsExceeded', {values: {max: REAL_SIGNIFICANT_DIGITS}})}</p>
            {/if}
        </div>
    {/if}

    <!-- ============================================================= -->
    <!-- Da / A split section -->
    <!-- ============================================================= -->
    <div class="mt-4 grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-3 items-start overflow-hidden" data-testid="tx-form-dual-split">
        <!-- DA (From) -->
        <div class="border border-lf-subtle rounded-lg p-3 min-w-0" data-testid="tx-form-dual-from">
            <div class="text-xs font-semibold uppercase tracking-wide text-lf-muted mb-2">{$t('common.from')}</div>
            <!-- Date (from side) -->
            <div class="flex flex-col gap-1 mb-2">
                <span class="text-xs text-lf-muted">{$t('common.date')}</span>
                {#if isReadonly}
                    <div class="px-3 py-2 bg-lf-panel border border-lf-subtle rounded-lg text-sm text-lf-secondary">{draft.date || '—'}</div>
                {:else}
                    <TxCellMark cell="date" marks={markedCells}><SingleDatePicker bind:value={draft.date} label="" inputStyle={true} onchange={(d) => setDate(d)} onvaliditychange={onDateMainValidityChange} /></TxCellMark>
                {/if}
            </div>
            {#if pairLayout === 'fx'}
                <TxCellMark cell="cash" marks={markedCells}><CompactCashCell value={draft.cash} onChange={setCash} signHint="positive" disabled={isReadonly} testid="tx-form-cash-from" defaultCode="EUR" maxSignificantDigits={REAL_SIGNIFICANT_DIGITS} /></TxCellMark>
                {#if cashSignificantError}
                    <p class="mt-1 text-xs text-lf-danger" data-testid="tx-form-cash-from-significant-error">{$t('transactions.errors.significantDigitsExceeded', {values: {max: REAL_SIGNIFICANT_DIGITS}})}</p>
                {/if}
            {:else}
                <!-- transfer_asset / transfer_cash: broker from -->
                <div class="flex flex-col gap-1">
                    <span class="text-xs text-lf-muted">{$t('transactions.table.broker')}</span>
                    <TxCellMark cell="broker" marks={markedCells}
                        ><BrokerSearchSelect brokers={brokersForFrom} value={brokerIdValue} onchange={(id) => setBroker(id ?? 0)} disabled={isReadonly || rowSaved} createLabel={$t('common.createNew') || 'Create new'} onCreateNew={() => (createBrokerOpen = true)} /></TxCellMark
                    >
                </div>
            {/if}
        </div>

        <!-- Arrow (clickable to swap Da↔A) -->
        <button
            type="button"
            class="hidden sm:flex items-center justify-center text-lf-muted hover:text-lf-link self-center p-1 rounded-full hover:bg-lf-hover transition-colors"
            onclick={swapDualSides}
            title={$t('transactions.form.swapSides') || 'Swap sides'}
            data-testid="tx-form-dual-swap"
            disabled={isReadonly || rowSaved}
        >
            <ArrowRight size={20} />
        </button>
        <button
            type="button"
            class="flex sm:hidden items-center justify-center text-lf-muted hover:text-lf-link p-1 rounded-full hover:bg-lf-hover transition-colors"
            onclick={swapDualSides}
            title={$t('transactions.form.swapSides') || 'Swap sides'}
            data-testid="tx-form-dual-swap-mobile"
            disabled={isReadonly || rowSaved}
        >
            <ArrowDown size={20} />
        </button>

        <!-- A (To) -->
        <div class="border border-lf-subtle rounded-lg p-3 min-w-0" data-testid="tx-form-dual-to">
            <div class="text-xs font-semibold uppercase tracking-wide text-lf-muted mb-2">{$t('common.to')}</div>
            <!-- Date (to side) — hidden when partner is inaccessible (role=null or not in store) -->
            {#if inaccessiblePartnerBrokerId != null || (isReadonly && !partnerRow && dualTo.broker_id > 0 && getBrokerRole(dualTo.broker_id) == null)}
                <!-- partner inaccessible — hide date -->
            {:else}
                <div class="flex flex-col gap-1 mb-2">
                    <span class="text-xs text-lf-muted">{$t('common.date')}</span>
                    {#if isReadonly}
                        <div class="px-3 py-2 bg-lf-panel border border-lf-subtle rounded-lg text-sm text-lf-secondary">{effectiveDualTo.date || '—'}</div>
                    {:else}
                        <TxCellMark cell="dateTo" marks={markedCells}><SingleDatePicker value={effectiveDualTo.date} label="" inputStyle={true} onchange={setDateTo} onvaliditychange={onDateToValidityChange} /></TxCellMark>
                    {/if}
                </div>
            {/if}
            {#if pairLayout === 'fx'}
                <TxCellMark cell="cashTo" marks={markedCells}><CompactCashCell value={dualTo.cash} onChange={setCashTo} signHint="positive" disabled={isReadonly} testid="tx-form-cash-to" defaultCode="USD" maxSignificantDigits={REAL_SIGNIFICANT_DIGITS} /></TxCellMark>
                {#if cashToSignificantError}
                    <p class="mt-1 text-xs text-lf-danger" data-testid="tx-form-cash-to-significant-error">{$t('transactions.errors.significantDigitsExceeded', {values: {max: REAL_SIGNIFICANT_DIGITS}})}</p>
                {/if}
            {:else}
                <!-- transfer_asset / transfer_cash: broker to -->
                <div class="flex flex-col gap-1">
                    {#if inaccessiblePartnerBrokerId == null}
                        <span class="text-xs text-lf-muted">{$t('transactions.table.broker')}</span>
                    {/if}
                    {#if inaccessiblePartnerBrokerId != null}
                        {@const pInfo = getBrokerInfo(inaccessiblePartnerBrokerId)}
                        {@const RoleIconC = getRoleIcon(null)}
                        <div class="flex flex-col gap-1.5 px-3 py-2 bg-lf-danger-soft border border-lf-danger-line rounded-lg text-sm text-lf-danger-on-soft" data-testid="tx-form-partner-locked">
                            <div class="flex items-center gap-1.5">
                                {#if pInfo?.icon_url || pInfo?.portal_url || pInfo?.default_import_plugin}
                                    <BrokerIcon brokerId={pInfo.id} iconUrl={pInfo.icon_url} portalUrl={pInfo.portal_url} pluginCode={pInfo.default_import_plugin} altText={pInfo.name ?? ''} size="sm" />
                                {/if}
                                <strong>{pInfo?.name ?? `#${inaccessiblePartnerBrokerId}`}</strong>
                                <RoleIconC size={14} class="{getRoleIconColor(null)} shrink-0" />
                            </div>
                            <span class="text-xs leading-relaxed">{$t('transactions.access.partnerNotAccessible')}</span>
                        </div>
                    {:else if isReadonly}
                        <!-- Bug10/13-fix: in view mode show static broker info -->
                        {@const toInfo = getBrokerInfo(dualTo.broker_id)}
                        {@const toRole = toInfo ? getBrokerRole(dualTo.broker_id) : null}
                        <div
                            class="flex {toRole == null && toInfo ? 'flex-col gap-1.5' : 'items-center gap-2'} px-3 py-2 {toRole == null && toInfo ? 'bg-lf-danger-soft border-lf-danger-line text-lf-danger-on-soft' : 'bg-lf-panel border-lf-subtle text-lf-secondary'} border rounded-lg text-sm"
                            data-testid="tx-form-broker-to-readonly"
                        >
                            {#if toInfo && toRole != null}
                                <!-- Accessible broker (OWNER/EDITOR/VIEWER) -->
                                {@const RoleIcon = getRoleIcon(toRole)}
                                <BrokerIcon brokerId={toInfo.id} iconUrl={toInfo.icon_url} portalUrl={toInfo.portal_url} pluginCode={toInfo.default_import_plugin} altText={toInfo.name} size="sm" />
                                <span class="font-medium">{toInfo.name}</span>
                                <RoleIcon size={14} class="{getRoleIconColor(toRole)} shrink-0" />
                            {:else if toInfo && toRole == null}
                                <!-- Broker in store but role=null (hidden/admin) — show lock -->
                                {@const LockIcon = getRoleIcon(null)}
                                {@const lockColor = getRoleIconColor(null)}
                                <div class="flex items-center gap-1.5">
                                    {#if toInfo.icon_url || toInfo.portal_url || toInfo.default_import_plugin}
                                        <BrokerIcon brokerId={toInfo.id} iconUrl={toInfo.icon_url} portalUrl={toInfo.portal_url} pluginCode={toInfo.default_import_plugin} altText={toInfo.name ?? ''} size="sm" />
                                    {/if}
                                    <strong>{toInfo.name}</strong>
                                    <LockIcon size={14} class="{lockColor} shrink-0" />
                                </div>
                                <span class="text-xs leading-relaxed">{$t('transactions.access.partnerNotAccessible')}</span>
                            {:else if dualTo.broker_id > 0}
                                <!-- Broker not in store at all -->
                                {@const LockIcon2 = getRoleIcon(null)}
                                {@const lockColor2 = getRoleIconColor(null)}
                                <LockIcon2 size={14} class="{lockColor2} shrink-0" />
                                <span class="text-lf-muted">#{dualTo.broker_id} — {$t('transactions.access.partnerNotAccessible')}</span>
                            {:else}
                                <span class="text-lf-muted">—</span>
                            {/if}
                        </div>
                    {:else}
                        <TxCellMark cell="brokerTo" marks={markedCells}
                            ><BrokerSearchSelect brokers={brokersForTo} value={brokerToIdValue} onchange={(id) => setBrokerTo(id ?? 0)} disabled={isReadonly || rowSaved} createLabel={$t('common.createNew') || 'Create new'} onCreateNew={() => (createBrokerOpen = true)} /></TxCellMark
                        >
                    {/if}
                </div>
            {/if}
        </div>
    </div>

    {#if pairLayout === 'fx'}
        <p class="mt-2 text-xs text-lf-muted" data-testid="tx-form-fx-dates-hint">{$t('transactions.form.fxDatesHint')}</p>
    {/if}

    <!-- FX Implied Rate info marker -->
    {#if pairLayout === 'fx' && draft.cash?.amount && dualTo.cash?.amount && draft.cash.code !== dualTo.cash?.code}
        {@const fxInfo = computeFxConversionInfo(Number(draft.cash.amount), draft.cash.code, Number(dualTo.cash.amount), dualTo.cash.code)}
        {#if fxInfo}
            {@const tooltipData = buildFxTooltipData(fxInfo, fxMarketPoint)}
            <div class="flex justify-center mt-2" data-testid="tx-form-fx-info">
                <Tooltip html={buildFxTooltipHtml(tooltipData, $t)} position="bottom">
                    <span class="inline-flex items-center gap-1 text-xs text-violet-600 dark:text-violet-400 cursor-help px-2 py-0.5 rounded bg-violet-50 dark:bg-violet-900/20">
                        <Info size={12} />
                        <span class="font-mono">{formatFixed(fxInfo.impliedRate, 4)}</span>
                        {#if tooltipData.staleDays != null && tooltipData.staleDays > 0}
                            <span class="text-lf-warning">⚠️</span>
                        {/if}
                    </span>
                </Tooltip>
            </div>
        {/if}
    {/if}

    <!-- Cost basis override for transfer_asset -->
    {#if pairLayout === 'transfer_asset'}
        <div class="mt-3">
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
        </div>
    {/if}
</fieldset>
