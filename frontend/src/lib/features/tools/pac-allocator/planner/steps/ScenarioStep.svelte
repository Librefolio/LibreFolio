<script lang="ts">
    import {t} from '$lib/i18n';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import {LABEL, NOTICE} from '../ui';

    interface Props {
        draft: PlannerDraft;
    }

    let {draft}: Props = $props();

    const ids = $props.id();
</script>

<div class="space-y-4" data-testid="pac-planner-scenario">
    <p class="text-sm text-gray-700 dark:text-gray-300">{$t('tools.pacAllocator.planner.scenario.intro', {default: 'PAC allocator · initial quantities zero (pure PAC).'})}</p>
    <div class="grid max-w-xl gap-4 sm:grid-cols-2">
        <div>
            <span id="{ids}-date" class={LABEL}>{$t('tools.pacAllocator.planner.scenario.asOf', {default: 'Reference date'})} *</span>
            <div aria-labelledby="{ids}-date">
                <SingleDatePicker value={draft.data.asOf} label={$t('tools.pacAllocator.planner.scenario.asOf', {default: 'Reference date'})} inputStyle testid="pac-planner-scenario-date" onchange={(date) => (draft.data.asOf = date)} />
            </div>
        </div>
        <div>
            <span class={LABEL}>{$t('tools.pacAllocator.planner.scenario.currency', {default: 'Valuation currency'})} *</span>
            <CurrencySearchSelect bind:value={draft.data.valuationCurrency} testId="pac-planner-scenario-currency" />
        </div>
    </div>
    <p class={NOTICE.info} data-testid="pac-planner-scenario-no-values">{$t('tools.pacAllocator.planner.scenario.noValues', {default: 'No financial value in this step.'})}</p>
</div>
