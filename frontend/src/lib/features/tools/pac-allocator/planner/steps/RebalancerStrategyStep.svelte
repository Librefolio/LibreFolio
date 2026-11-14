<!--
  Step «Strategia» of the Rebalancer (F3a of project 67, step 10b; M29–M33, decisioni-REB §7.3; mockup screen 6).

  Two strategies as cards: «Invest only», the only one before F3b (S1), and «Invest and sell», shown off, «coming soon».
  The target fidelity as five cards: the three levels («Balanced» the default), «Target first», «Custom». «Custom» has one
  field in euros, inside its card: the most the user accepts to spend for the reference row of the table. The euros go to
  the preview, which gives λ back to the draft: the draft keeps λ, never the euros, so a new total gives other euros back
  for the same λ (§7.3). An empty, zero or negative field is an error on the field and a local problem of the step. Without
  the preview's table (a total that cannot be counted yet) the field is off and the table's line says why. No figure is
  computed here (N1).
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {isPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
    import {canonicalDecimal, canonicalInput, decimalSign} from '$lib/utils/core/exactDecimal';
    import type {DraftFidelity, PlannerDraft} from '../draft.svelte';
    import {cldrCurrencyDigits, exactMoneyDisplay, formatExactMoneyPlain, formatPlannerMoneyPlain} from '../format';
    import type {PlannerPreview} from '../preview.svelte';
    import {fidelityName, rebalancerStrategyName} from '../strategyText';
    import HelpTip from '../shared/HelpTip.svelte';
    import {BADGE, INPUT, SECTION_TITLE, TOGGLE_CARD, TOGGLE_OFF, TOGGLE_ON} from '../ui';
    import FidelityTable from './FidelityTable.svelte';
    import {domId, getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        draft: PlannerDraft;
        /** The scenario preview (step 8): the table, and λ for the euros typed for «Custom». */
        preview: PlannerPreview | null;
    }

    let {draft, preview}: Props = $props();

    const S = 'tools.portfolioRebalancer.planner.strategy';
    type Choice = 'cost_aware' | 'balanced' | 'faithful' | 'target_first' | 'custom';
    const CHOICES: Choice[] = ['cost_aware', 'balanced', 'faithful', 'target_first', 'custom'];

    const fidelity = $derived(draft.data.fidelity);
    const chosen = $derived<Choice>(fidelity.kind === 'level' ? fidelity.level : fidelity.kind);
    const table = $derived(preview?.numbers?.table ?? null);
    const reference = $derived(table?.rows.find((row) => row.reference) ?? null);

    /** The euros as typed; `null` until the user types, so the field shows the preview's euros for the draft's λ. */
    let typed = $state<string | null>(null);
    const answered = $derived.by(() => {
        const amount = preview?.numbers?.custom?.reference_amount;
        if (!amount || fidelity.kind !== 'custom') return '';
        return canonicalDecimal(exactMoneyDisplay(amount.value, cldrCurrencyDigits(amount.currency)).text) ?? '';
    });
    const fieldText = $derived(typed ?? answered);
    const fieldInvalid = $derived(typed !== null && !positive(typed));

    function positive(text: string): boolean {
        const value = canonicalInput(text);
        return value !== null && decimalSign(value) === 1;
    }

    function choose(next: Choice): void {
        if (next === chosen) return;
        if (next === 'custom') {
            draft.data.fidelity = {kind: 'custom', lambda: ''};
            // Euros typed before another choice go again, so the user finds the field as they left it.
            if (typed !== null && positive(typed)) preview?.setCustomEuros(draft, typed);
            return;
        }
        draft.data.fidelity = next === 'target_first' ? {kind: 'target_first'} : ({kind: 'level', level: next} as DraftFidelity);
    }

    function typeEuros(text: string): void {
        typed = text;
        // The draft's λ belongs to the figure the preview converted: a new figure has none until its answer lands, so a
        // calculation never runs on the λ of an older figure (a problem of the step meanwhile).
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        // A figure above zero goes to the preview; anything else withdraws the euros on their way.
        preview?.setCustomEuros(draft, positive(text) ? text : '');
    }

    function choiceName(choice: Choice): string {
        if (choice === 'custom') return fidelityName($t, {kind: 'custom', lambda: ''});
        if (choice === 'target_first') return fidelityName($t, {kind: 'target_first'});
        return fidelityName($t, {kind: 'level', level: choice});
    }

    function choiceNote(choice: Choice): string {
        switch (choice) {
            case 'cost_aware':
                return $t(`${S}.fidelityNote.costAware`);
            case 'balanced':
                return $t(`${S}.fidelityNote.balanced`);
            case 'faithful':
                return $t(`${S}.fidelityNote.faithful`);
            case 'target_first':
                return $t(`${S}.fidelityNote.targetFirst`);
            default:
                return '';
        }
    }
</script>

<div class="space-y-6" data-testid={testId('strategy', profile)}>
    <div class="grid max-w-3xl gap-3 sm:grid-cols-2">
        <button type="button" class="{TOGGLE_CARD} {TOGGLE_ON} p-3 text-left" aria-pressed="true" data-testid={testId('strategy-card', profile)} data-strategy="invest_only" data-selected="true">
            <span class="block font-medium text-lf-primary">{rebalancerStrategyName($t, 'invest_only')}</span>
            <span class="mt-1 block text-sm text-lf-secondary">{$t(`${S}.investOnlyHelp`)}</span>
        </button>
        <button type="button" class="{TOGGLE_CARD} {TOGGLE_OFF} cursor-not-allowed p-3 text-left opacity-60" disabled aria-pressed="false" data-testid={testId('strategy-card', profile)} data-strategy="invest_and_sell" data-selected="false">
            <span class="flex flex-wrap items-center gap-2 font-medium text-lf-primary">
                {$t(`${S}.investAndSell`)}
                <span class={BADGE.neutral} data-testid={testId('strategy-coming-soon', profile)}>{$t(`${S}.comingSoon`)}</span>
            </span>
            <span class="mt-1 block text-sm text-lf-secondary">{$t(`${S}.investAndSellHelp`)}</span>
        </button>
    </div>

    <section class="space-y-3" aria-labelledby={domId('fidelity-title', profile)}>
        <div class="flex items-center gap-1">
            <h3 id={domId('fidelity-title', profile)} class={SECTION_TITLE}>{$t(`${S}.fidelityTitle`)}</h3>
            <HelpTip label={$t(`${S}.fidelityTitle`)} help={$t(`${S}.fidelityHelp`)} />
        </div>
        <p class="text-sm text-lf-secondary">{$t(`${S}.fidelityLead`)}</p>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {#each CHOICES as choice (choice)}
                {@const selected = choice === chosen}
                {#if choice === 'custom'}
                    <div class="{TOGGLE_CARD} {selected ? TOGGLE_ON : TOGGLE_OFF} p-3 sm:col-span-2 lg:col-span-4" data-testid={testId('fidelity-choice', profile)} data-choice={choice} data-selected={selected ? 'true' : 'false'}>
                        <button type="button" class="block w-full cursor-pointer text-left font-medium text-lf-primary" aria-pressed={selected} data-testid={testId('fidelity-choice-button', profile)} onclick={() => choose(choice)}>
                            {choiceName(choice)}
                        </button>
                        {#if selected}
                            <div class="mt-2 flex flex-wrap items-center gap-2 text-sm text-lf-secondary">
                                <span>{$t(`${S}.customSentence`, {values: {reference: reference ? formatExactMoneyPlain(reference.misplaced, {digits: () => 0}) : '—'}})}</span>
                                <span class="flex w-36 shrink-0 items-center gap-1 whitespace-nowrap">
                                    {#if isPrivacyEnabled()}
                                        <!-- The figure derives from the user's total: masked, as the table's; editable again once privacy is off. -->
                                        <span class="font-mono text-lf-primary" data-testid={testId('fidelity-custom-masked', profile)}>{formatPlannerMoneyPlain(fieldText || null, draft.data.valuationCurrency)}</span>
                                    {:else}
                                        <input
                                            type="text"
                                            inputmode="decimal"
                                            class="{INPUT} text-right aria-invalid:border-lf-danger"
                                            value={fieldText}
                                            disabled={!table}
                                            aria-invalid={fieldInvalid ? 'true' : 'false'}
                                            aria-label={$t(`${S}.customLabel`)}
                                            data-testid={testId('fidelity-custom-input', profile)}
                                            oninput={(event) => typeEuros(event.currentTarget.value)}
                                        />
                                        <span class="text-xs text-lf-muted">{draft.data.valuationCurrency}</span>
                                    {/if}
                                </span>
                            </div>
                            {#if fieldInvalid}
                                <p class="mt-1 text-xs text-lf-danger" role="alert" data-testid={testId('fidelity-custom-error', profile)}>{$t(`${S}.customInvalid`)}</p>
                            {/if}
                        {/if}
                    </div>
                {:else}
                    <button type="button" class="{TOGGLE_CARD} {selected ? TOGGLE_ON : TOGGLE_OFF} cursor-pointer p-3 text-left" aria-pressed={selected} data-testid={testId('fidelity-choice', profile)} data-choice={choice} data-selected={selected ? 'true' : 'false'} onclick={() => choose(choice)}>
                        <span class="flex flex-wrap items-center gap-2 font-medium text-lf-primary">
                            {choiceName(choice)}
                            {#if choice === 'balanced'}<span class={BADGE.neutral} data-testid={testId('fidelity-default', profile)}>{$t(`${S}.defaultBadge`)}</span>{/if}
                        </span>
                        <span class="mt-1 block text-sm {choice === 'target_first' ? 'text-lf-warning' : 'text-lf-secondary'}">{choiceNote(choice)}</span>
                    </button>
                {/if}
            {/each}
        </div>
    </section>

    <FidelityTable {preview} {fidelity} />
</div>
