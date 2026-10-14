<!--
  CurrencyAmount — one money amount through the D8 formatter, rendered in runes mode.

  For legacy-mode parents. A legacy template compiles a function call inside an
  expression to `$.untrack(() => …)`, tracking only the values the expression names —
  so `{@html formatCurrencyAmountHtml(…)}` written directly in a legacy component never
  sees the privacy flag that `maskable` reads inside the call. The amount keeps the
  state it had at mount: turned on in place, privacy leaves it in the clear; turned off,
  it stays masked (R20, measured 2026-09-24 on the brokers list and on broker detail).

  In runes mode the same call is tracked through, so the same markup follows the toggle
  both ways. Prefer migrating a legacy parent to runes when it is small; use this where
  it is not.
-->
<script lang="ts">
    import {formatCurrencyAmountHtml, type CurrencyAmountFormatOptions} from '$lib/utils/currency/currencyFormat';

    interface Props {
        amount: number;
        code: string;
        options?: CurrencyAmountFormatOptions;
    }

    let {amount, code, options = {}}: Props = $props();
</script>

{@html formatCurrencyAmountHtml(amount, code, options)}
