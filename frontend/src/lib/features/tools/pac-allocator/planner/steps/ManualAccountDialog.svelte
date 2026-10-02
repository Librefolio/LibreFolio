<script lang="ts">
    import {untrack} from 'svelte';
    import {t} from '$lib/i18n';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import {canonicalInput, compareDecimal} from '../decimal';
    import type {PlannerDraft} from '../draft.svelte';
    import {cldrCurrencyStep} from '../format';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, INPUT, LABEL, NOTICE} from '../ui';
    import PlannerDialog from '../shared/PlannerDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        onclose: () => void;
    }

    let {draft, onclose}: Props = $props();

    const ids = $props.id();
    let name = $state('');
    let currency = $state(untrack(() => draft.data.valuationCurrency));
    let available = $state('');
    let selected = $state('');
    let tried = $state(false);

    const availableValue = $derived(canonicalInput(available));
    const selectedValue = $derived(canonicalInput(selected));
    const exceeds = $derived(availableValue !== null && selectedValue !== null && compareDecimal(selectedValue, availableValue) === 1);
    const complete = $derived(name.trim() !== '' && /^[A-Z]{3}$/.test(currency) && availableValue !== null && selectedValue !== null);
    const step = $derived(currency ? cldrCurrencyStep(currency) : '0.01');

    function add(): void {
        tried = true;
        if (!complete || exceeds) return;
        draft.addManualAccount({name: name.trim(), currency, available, selected});
        onclose();
    }
</script>

<PlannerDialog open title={$t('tools.pacAllocator.planner.manualAccount.title', {default: 'Add external account'})} testid="pac-planner-manual-account" {onclose} maxWidth="lg">
    <div class="grid gap-3 sm:grid-cols-2">
        <label class="sm:col-span-2">
            <span class={LABEL}>{$t('tools.pacAllocator.planner.manualAccount.name', {default: 'Account name'})} *</span>
            <input class={INPUT} bind:value={name} maxlength="120" data-testid="pac-planner-manual-account-name" />
        </label>
        <div>
            <span class={LABEL}>{$t('common.currency', {default: 'Currency'})} *</span>
            <CurrencySearchSelect bind:value={currency} testId="pac-planner-manual-account-currency" compact />
        </div>
        <div></div>
        <label for="{ids}-available">
            <span class={LABEL}>{$t('tools.pacAllocator.planner.manualAccount.declared', {default: 'Declared liquidity'})} * <span class={HINT}>{currency}</span></span>
            <ExactDecimalInput id="{ids}-available" bind:value={available} {step} className={INPUT} testid="pac-planner-manual-account-available" />
            <span class={HINT}>{$t('tools.pacAllocator.planner.manualAccount.declaredHint', {default: 'How much is on the account: the amount to use cannot exceed it.'})}</span>
        </label>
        <label for="{ids}-selected">
            <span class={LABEL}>{$t('tools.pacAllocator.planner.cash.selected', {default: 'Amount to use'})} * <span class={HINT}>{currency}</span></span>
            <ExactDecimalInput id="{ids}-selected" bind:value={selected} {step} className={INPUT} externalInvalid={exceeds} ariaDescribedby="{ids}-selected-hint" testid="pac-planner-manual-account-selected" />
            <span id="{ids}-selected-hint" class={HINT}>{$t('tools.pacAllocator.planner.manualAccount.selectedHint', {default: 'At most the declared liquidity.'})}</span>
        </label>
    </div>
    {#if exceeds}
        <p class={NOTICE.danger} role="alert" data-testid="pac-planner-manual-account-exceeds">{$t('tools.pacAllocator.planner.problems.selectedExceedsAvailable', {default: "'Amount to use' exceeds the available amount in the same currency."})}</p>
    {:else if tried && !complete}
        <p class={NOTICE.danger} role="alert" data-testid="pac-planner-manual-account-incomplete">{$t('tools.pacAllocator.planner.manualAccount.incomplete', {default: 'Fill in every field marked *.'})}</p>
    {/if}
    <p class={HINT}>{$t('tools.pacAllocator.planner.manualAccount.quantum', {default: 'Amounts follow the smallest unit of the currency (for the euro, one cent).'})}</p>
    <p class={HINT}>{$t('tools.pacAllocator.planner.manualAccount.fundingOnly', {default: 'Nothing is bought from this account: in the Broker step you choose which Broker receives this money.'})}</p>

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-manual-account-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-manual-account-add" onclick={add}>{$t('tools.pacAllocator.planner.manualAccount.add', {default: 'Add source'})}</button>
    {/snippet}
</PlannerDialog>
