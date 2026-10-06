<script lang="ts">
    import {t} from '$lib/i18n';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import {LABEL} from '../ui';
    import HelpTip from '../shared/HelpTip.svelte';

    interface Props {
        draft: PlannerDraft;
    }

    let {draft}: Props = $props();

    const currencyLabel = $derived($t('tools.pacAllocator.planner.scenario.currency', {default: 'Valuation currency'}));
    const currencyHelp = $derived(
        $t('tools.pacAllocator.planner.scenario.currencyHint', {default: 'The currency the plan compares and summarises amounts in (weights, deviations, uninvested cash). Money stays in its own currency: every exchange needed appears in the plan as an FX operation.'}),
    );
</script>

<div class="space-y-4" data-testid="pac-planner-scenario">
    <p class="max-w-3xl text-sm text-gray-700 dark:text-gray-300">
        {$t('tools.pacAllocator.planner.scenario.intro', {default: 'You plan a new investment (pure PAC): the calculation starts from an empty portfolio, so what you already hold is not counted, and splits the cash you choose among the Assets, as close as possible to the target weights. It is a simulation: no order is sent.'})}
    </p>
    <div class="grid max-w-3xl gap-4 sm:grid-cols-2">
        <div class="space-y-1">
            <div class="flex items-center gap-1">
                <span class={LABEL}>{currencyLabel} *</span>
                <HelpTip label={currencyLabel} help={currencyHelp} testid="pac-planner-scenario-currency-help" />
            </div>
            <CurrencySearchSelect bind:value={draft.data.valuationCurrency} testId="pac-planner-scenario-currency" compact />
        </div>
    </div>
</div>
