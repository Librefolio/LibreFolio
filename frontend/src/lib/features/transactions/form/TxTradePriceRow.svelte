<!--
  TxTradePriceRow — «Total amount / Unit price» of a BUY or SELL (#47): the badge that says which value the user types,
  and the unit price, calculated (amount mode) or typed (unit-price mode).

  The form computes nothing: the other value comes from the backend (`txTradeAmountApi.ts`). This row only shows the unit
  price it was given and reports what the user does. The amount itself stays the cash cell above, visible and editable in
  both modes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {exceedsSignificantDigits, REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';
    import type {TradeAmountDriver} from './txTradeAmount';

    interface Props {
        /** Which value the user types: the badge's pressed button. */
        mode: TradeAmountDriver;
        /** The unit price: calculated in amount mode, typed in unit-price mode. */
        unitPrice: string;
        disabled?: boolean;
        onModeChange: (mode: TradeAmountDriver) => void;
        onUnitPriceInput: (value: string) => void;
    }

    let {mode, unitPrice, disabled = false, onModeChange, onUnitPriceInput}: Props = $props();

    const BUTTON = 'px-1.5 py-0.5 rounded';
    const ON = 'bg-lf-selected text-lf-link font-medium';
    const OFF = 'text-lf-muted hover:text-lf-secondary';
</script>

<div class="mt-1 flex flex-col gap-1" data-testid="tx-form-trade-price">
    <div class="flex items-center gap-1 text-[10px]" data-testid="tx-form-entry-mode">
        <button type="button" class="{BUTTON} {mode === 'amount' ? ON : OFF}" {disabled} aria-pressed={mode === 'amount'} onclick={() => onModeChange('amount')} data-testid="tx-form-entry-mode-amount">{$t('transactions.form.entryModeAmount')}</button>
        <span class="text-lf-muted">|</span>
        <button type="button" class="{BUTTON} {mode === 'unit_price' ? ON : OFF}" {disabled} aria-pressed={mode === 'unit_price'} onclick={() => onModeChange('unit_price')} data-testid="tx-form-entry-mode-unit-price">{$t('transactions.form.entryModeUnitPrice')}</button>
    </div>
    {#if mode === 'unit_price'}
        <ExactDecimalInput
            value={unitPrice}
            maxIntegerDigits={12}
            maxFractionDigits={12}
            placeholder="0"
            ariaLabel={$t('transactions.form.entryModeUnitPrice')}
            externalInvalid={exceedsSignificantDigits(unitPrice, REAL_SIGNIFICANT_DIGITS)}
            className="!rounded-lg !px-3 !py-2 text-right tabular-nums focus:!ring-2 focus:!ring-lf-focus/30"
            {disabled}
            onchange={onUnitPriceInput}
            testid="tx-form-unit-price"
        />
        <span class="text-[10px] text-lf-muted">{$t('transactions.form.unitPriceHint')}</span>
    {:else}
        <div class="flex items-baseline justify-between gap-2 text-xs text-lf-secondary">
            <span class="text-lf-muted">{$t('transactions.form.entryModeUnitPrice')} · {$t('transactions.form.unitPriceCalculated')}</span>
            <span class="font-mono tabular-nums" data-testid="tx-form-unit-price-computed" data-value={unitPrice}>{unitPrice === '' ? '—' : formatDecimalForDisplay(unitPrice)}</span>
        </div>
    {/if}
</div>
