<!--
  TxCashDerived — the other value of a trade, under the amount field and in place of the sign hint (#47, FB-16).

  Read as a unit price, the field's number gives a total: «= 1,000.80 in total». Read as the total, it gives a unit price:
  «= 83.40 per unit» (per `base` units for an asset quoted on a base other than 1, a bond on 100). The value is the exact decimal
  the form calculated (`data-value`); the text only localises it. In view mode the unit price is shown, so a saved trade reads in
  both forms.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {formatExactDecimal} from '$lib/utils/core/formatFixed';

    interface Props {
        /** What is shown: the total, or the unit price. */
        mode: 'total' | 'unit_price';
        /** The calculated value, a plain decimal. */
        value: string;
        /** The asset's `quote_base_quantity`, for the unit price's «per N units». */
        base: number;
    }

    let {mode, value, base}: Props = $props();

    // The total keeps the 6 decimals of an amount, the unit price the 12 of a price; at least 2, as money is read.
    let shown = $derived(formatExactDecimal(value, {minFrac: 2, maxFrac: mode === 'total' ? 6 : 12}));
</script>

<span class="text-[10px] text-lf-muted" data-testid="tx-form-cash-derived" data-mode={mode} data-value={value}>
    {mode === 'total' ? $t('transactions.form.entryDerivedTotal', {values: {value: shown}}) : $t('transactions.form.entryDerivedUnit', {values: {value: shown, base}})}
</span>
