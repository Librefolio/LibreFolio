<!--
  TxEntryModeToggle — «Total / Unit price» (#47, FB-16): how the number written in the amount field is read.

  Two buttons on the label row of the amount, so the form stays amount + currency. The selector only says what the number
  means: the amount field never changes its text, the form calculates the other value (`txTradeAmount.ts`) and shows it under
  the field (`TxCashDerived`). The total is what is saved, whichever reading is on.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {TradeAmountDriver} from './txTradeAmount';

    interface Props {
        /** How the number is read: the pressed button. */
        mode: TradeAmountDriver;
        onModeChange: (mode: TradeAmountDriver) => void;
    }

    let {mode, onModeChange}: Props = $props();

    const BUTTON = 'px-1.5 py-0.5 rounded';
    const ON = 'bg-lf-selected text-lf-link font-medium';
    const OFF = 'text-lf-muted hover:text-lf-secondary';
</script>

<span class="flex items-center gap-1 text-[10px]" role="group" aria-label={$t('transactions.form.entryModeLabel')} data-testid="tx-form-entry-mode">
    <button type="button" class="{BUTTON} {mode === 'amount' ? ON : OFF}" aria-pressed={mode === 'amount'} onclick={() => onModeChange('amount')} data-testid="tx-form-entry-mode-amount">{$t('transactions.form.entryModeAmount')}</button>
    <span class="text-lf-muted" aria-hidden="true">|</span>
    <button type="button" class="{BUTTON} {mode === 'unit_price' ? ON : OFF}" aria-pressed={mode === 'unit_price'} onclick={() => onModeChange('unit_price')} data-testid="tx-form-entry-mode-unit-price">{$t('transactions.form.entryModeUnitPrice')}</button>
</span>
