<!--
  Step «Strategia» of the Rebalancer (F3a of project 67, step 10b; M29–M33, decisioni-REB §7.3; mockup screen 6).

  Two strategies as cards: «Invest only», the only one before F3b (S1), and «Invest and sell», shown off, «coming soon».
  The target fidelity as five cards: the three levels («Balanced» the default), «Target first», «Custom». «Custom» has one
  field in euros, inside its card: the most the user accepts to spend for the reference row of the table. The preview
  class turns the euros into the draft's λ on the preview's total (`acceptableCost.ts`, R1-F (b) of project 67): at once
  when its numbers are current, with no call. The draft keeps λ, never the euros, so a new total gives other euros back
  for the same λ (§7.3). An empty, zero or negative field is an error on the field and a local problem of the step.
  Without the preview's total (one that cannot be counted yet) the field is off and the table's line says why. No figure
  is computed in this component.

  Both choices are `ChoiceCards` (G6-3, M6): a group of native radios, the arrow keys moving the choice; «Custom»'s field
  sits in its card through `extra`, outside the radio's label.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {isPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
    import {canonicalDecimal, canonicalInput, decimalSign} from '$lib/utils/core/exactDecimal';
    import type {DraftFidelity, PlannerDraft} from '../draft.svelte';
    import {cldrCurrencyDigits, exactMoneyDisplay, formatExactMoneyPlain, formatPlannerMoneyPlain} from '../format';
    import type {PlannerPreview} from '../preview.svelte';
    import {referenceAmountFor, referenceMisplaced} from '../acceptableCost';
    import {fidelityName, rebalancerStrategyName} from '../strategyText';
    import ChoiceCards from '$lib/features/brokers/profile/ChoiceCards.svelte';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import {INPUT, SECTION_TITLE} from '../ui';
    import FidelityTable from './FidelityTable.svelte';
    import {domId, getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        draft: PlannerDraft;
        /** The scenario preview (step 8): the total, and λ for the euros typed for «Custom». */
        preview: PlannerPreview | null;
    }

    let {draft, preview}: Props = $props();

    const S = 'tools.portfolioRebalancer.planner.strategy';
    type Choice = 'cost_aware' | 'balanced' | 'faithful' | 'target_first' | 'custom';
    const CHOICES: Choice[] = ['cost_aware', 'balanced', 'faithful', 'target_first', 'custom'];
    type Strategy = 'invest_only' | 'invest_and_sell';

    const fidelity = $derived(draft.data.fidelity);
    const chosen = $derived<Choice>(fidelity.kind === 'level' ? fidelity.level : fidelity.kind);
    const total = $derived(preview?.numbers?.total ?? null);
    /** The reference row's misplaced money; `null` without a total to count it on (the field is then off). */
    const reference = $derived(total ? referenceMisplaced(total) : null);

    /** The euros as typed; `null` until the user types, so the field shows the euros of the draft's λ on the total. */
    let typed = $state<string | null>(null);
    const answered = $derived.by(() => {
        const amount = total && fidelity.kind === 'custom' ? referenceAmountFor(total, fidelity.lambda) : null;
        if (!amount) return '';
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
        // The draft's λ belongs to the figure converted: a new figure has none until it is converted (at once on a current
        // total), so a calculation never runs on the λ of an older figure (a problem of the step meanwhile).
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        // A figure above zero becomes λ; anything else withdraws the euros waiting.
        preview?.setCustomEuros(draft, positive(text) ? text : '');
    }

    function choiceName(choice: Choice): string {
        if (choice === 'custom') return fidelityName($t, {kind: 'custom', lambda: ''});
        if (choice === 'target_first') return fidelityName($t, {kind: 'target_first'});
        return fidelityName($t, {kind: 'level', level: choice});
    }

    const strategies = $derived([
        {value: 'invest_only' as Strategy, label: rebalancerStrategyName($t, 'invest_only'), description: $t(`${S}.investOnlyHelp`)},
        // Off until F3b (S1): shown, never chosen.
        {value: 'invest_and_sell' as Strategy, label: $t(`${S}.investAndSell`), description: $t(`${S}.investAndSellHelp`), disabled: true, badge: $t(`${S}.comingSoon`)},
    ]);
    const choices = $derived(
        CHOICES.map((choice) => ({
            value: choice,
            label: choiceName(choice),
            description: choiceNote(choice) || undefined,
            tone: choice === 'target_first' ? ('warning' as const) : undefined,
            wide: choice === 'custom',
        })),
    );

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
    <div class="max-w-3xl">
        <ChoiceCards
            name={domId('strategy-group', profile)}
            legend={$t('tools.pacAllocator.planner.steps.strategy')}
            options={strategies}
            value="invest_only"
            testid={testId('strategies', profile)}
            cardTestid={testId('strategy-card', profile)}
            radioTestid={testId('strategy-radio', profile)}
            valueAttribute="strategy"
            onchange={() => {
                // «Invest only» is the only strategy before F3b: nothing to change.
            }}
        />
    </div>

    <section class="space-y-3" aria-labelledby={domId('fidelity-title', profile)}>
        <div class="flex items-center gap-1">
            <h3 id={domId('fidelity-title', profile)} class={SECTION_TITLE}>{$t(`${S}.fidelityTitle`)}</h3>
            <HelpTip label={$t(`${S}.fidelityTitle`)} help={$t(`${S}.fidelityHelp`)} />
        </div>
        <p class="text-sm text-lf-secondary">{$t(`${S}.fidelityLead`)}</p>
        <ChoiceCards
            name={domId('fidelity-group', profile)}
            legend={$t(`${S}.fidelityTitle`)}
            options={choices}
            value={chosen}
            defaultValue="balanced"
            defaultLabel={$t(`${S}.defaultBadge`)}
            testid={testId('fidelity-choices', profile)}
            cardTestid={testId('fidelity-choice', profile)}
            radioTestid={testId('fidelity-choice-radio', profile)}
            valueAttribute="choice"
            wideGrid
            extra={customField}
            onchange={choose}
        />
    </section>

    <FidelityTable {preview} {fidelity} />
</div>

{#snippet customField(choice: Choice, selected: boolean)}
    {#if choice === 'custom' && selected}
        <div class="px-3 pb-3 pl-9">
            <div class="flex flex-wrap items-center gap-2 text-sm text-lf-secondary">
                <span>{$t(`${S}.customSentence`, {values: {reference: reference ? formatExactMoneyPlain(reference, {digits: () => 0}) : '—'}})}</span>
                <span class="flex w-52 max-w-full shrink-0 items-center gap-1.5 whitespace-nowrap">
                    {#if isPrivacyEnabled()}
                        <!-- The figure derives from the user's total: masked, as the table's; editable again once privacy is off. -->
                        <span class="font-mono text-lf-primary" data-testid={testId('fidelity-custom-masked', profile)}>{formatPlannerMoneyPlain(fieldText || null, draft.data.valuationCurrency)}</span>
                    {:else}
                        <input
                            type="text"
                            inputmode="decimal"
                            class="{INPUT} min-w-0 flex-1 text-right aria-invalid:border-lf-danger"
                            value={fieldText}
                            disabled={!reference}
                            aria-invalid={fieldInvalid ? 'true' : 'false'}
                            aria-label={$t(`${S}.customLabel`)}
                            data-testid={testId('fidelity-custom-input', profile)}
                            oninput={(event) => typeEuros(event.currentTarget.value)}
                        />
                        <!-- G6-5: the field's unit in the project's form, `€ 🇪🇺 EUR`. -->
                        <span class="shrink-0 text-xs text-lf-muted"><CurrencyCode code={draft.data.valuationCurrency} testid={testId('fidelity-custom-unit', profile)} /></span>
                    {/if}
                </span>
            </div>
            {#if fieldInvalid}
                <p class="mt-1 text-xs text-lf-danger" role="alert" data-testid={testId('fidelity-custom-error', profile)}>{$t(`${S}.customInvalid`)}</p>
            {/if}
        </div>
    {/if}
{/snippet}
