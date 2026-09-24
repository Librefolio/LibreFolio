<!--
  CurrencyAmountLegacyHost — test-only legacy-mode parent for CurrencyAmount (Vitest + jsdom).

  CurrencyAmount exists for legacy-mode parents (R20, see its header): a legacy template
  compiles a call inside an expression to `$.untrack(() => …)`, so the privacy flag the
  formatter reads inside the call is never tracked there. The property worth testing is
  therefore not that CurrencyAmount follows the flag on its own, but that it does so under a
  legacy parent that does not. `export let` makes this host legacy by construction: the
  compiler rejects `export let` in runes mode, so it cannot quietly become a runes parent.

  The second span renders the same call inline, the way BrokerCard did before the fix. It is
  the control for the premise: it keeps its mount-time markup while the child follows the
  toggle. The day it follows too, legacy templates track calls, and CurrencyAmount's reason
  to exist has changed.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    import CurrencyAmount from '$lib/components/ui/display/CurrencyAmount.svelte';
    import {formatCurrencyAmountHtml, type CurrencyAmountFormatOptions} from '$lib/utils/currency/currencyFormat';

    export let amount: number;
    export let code: string;
    export let options: CurrencyAmountFormatOptions | undefined = undefined;
</script>

<span data-testid="legacy-host-child"><CurrencyAmount {amount} {code} {options} /></span>
<span data-testid="legacy-host-inline">{@html formatCurrencyAmountHtml(amount, code, options)}</span>
