<script lang="ts">
    import {Plus, Trash2} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {restoreCopiedRate} from '../copies';
    import {CopyFlow} from '../copyFlow.svelte';
    import {compareDecimal} from '../decimal';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatPlannerTimestamp} from '../format';
    import {canonicalPair} from '../source';
    import {BUTTON_LINK, BUTTON_SECONDARY, CARD, HINT, INPUT, LABEL} from '../ui';
    import AgeLabel from '../shared/AgeLabel.svelte';
    import CopyFlowView from '../shared/CopyFlowView.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import SourceCopyDialog from './SourceCopyDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
    }

    let {draft, accountGeneration}: Props = $props();

    const ids = $props.id();
    const flow = new CopyFlow();
    let copying = $state(false);
    let addFrom = $state('');
    let addTo = $state('');

    const required = $derived(new Set(draft.requiredPairs));
    const copyDisabled = $derived(!/^[A-Z]{3}$/.test(draft.data.valuationCurrency) || draft.fxPairs.length === 0);
    const addPair = $derived(addFrom && addTo && addFrom !== addTo ? canonicalPair(addFrom, addTo) : null);

    function sides(pair: string): [string, string] {
        const [base, quote] = pair.split('/');
        return [base ?? '', quote ?? ''];
    }

    function setRate(pair: string, value: string): void {
        draft.ensureFx(pair).rate = value;
    }

    function add(): void {
        if (!addPair) return;
        draft.ensureFx(addPair);
        addFrom = '';
        addTo = '';
    }
</script>

<div class="space-y-4" data-testid="pac-planner-fx">
    <p class="text-sm text-gray-700 dark:text-gray-300">{$t('tools.pacAllocator.planner.fx.intro', {default: 'The backend decides whether and how much to convert. You provide the rates.'})}</p>
    <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled} data-testid="pac-planner-fx-copy-open" onclick={() => (copying = true)}>
        {$t('tools.pacAllocator.planner.fx.copy', {default: 'Copy FX rates'})}
    </button>
    <CopyFlowView {flow} {draft} testid="pac-planner-fx-notice" />

    {#if draft.fxPairs.length === 0}
        <p class={HINT} data-testid="pac-planner-fx-empty">{$t('tools.pacAllocator.planner.fx.none', {default: 'No conversion needed: every currency in play is the valuation currency.'})}</p>
    {/if}

    {#each draft.fxPairs as pair (pair)}
        {@const fx = draft.fx(pair)}
        {@const [base, quote] = sides(pair)}
        {@const modified = !!fx?.stamp && fx.copiedRate !== null && compareDecimal(fx.rate || '0', fx.copiedRate) !== 0}
        <div class={CARD} data-testid="pac-planner-fx-pair" data-pair={pair} data-required={required.has(pair) ? 'true' : 'false'}>
            <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="font-medium">{pair}</p>
                {#if fx?.rate}
                    <OriginBadge origin={fx.stamp ? 'copied' : 'manual'} {modified} when={formatPlannerTimestamp(fx.enteredAt)} testid="pac-planner-fx-origin" />
                {/if}
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-2 text-sm">
                <label for="{ids}-{pair}">1 {base} =</label>
                <div class="w-40">
                    <ExactDecimalInput id="{ids}-{pair}" value={fx?.rate ?? ''} step="0.0001" className={INPUT} testid="pac-planner-fx-rate" onchange={(value) => setRate(pair, value)} />
                </div>
                <span>{quote}</span>
                {#if fx?.stamp}
                    <span class={HINT}>{[fx.source, fx.referenceDate].filter((part) => !!part).join(' · ')}</span>
                    <AgeLabel date={fx.referenceDate} asOf={draft.data.asOf} testid="pac-planner-fx-age" />
                {/if}
            </div>
            <div class="mt-2 flex flex-wrap gap-3">
                {#if modified}
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-fx-restore" onclick={() => restoreCopiedRate(draft, pair)}>
                        {$t('tools.pacAllocator.planner.restoreCopied', {default: 'Restore the copied value'})}
                    </button>
                {/if}
                {#if !required.has(pair) && fx}
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-fx-remove" onclick={() => draft.removeFx(pair)}>
                        <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.fx.remove', {default: 'Remove pair (no longer in play)'})}
                    </button>
                {/if}
            </div>
        </div>
    {/each}

    <div class="flex flex-wrap items-end gap-2" data-testid="pac-planner-fx-add">
        <div class="w-40">
            <span class={LABEL}>{$t('tools.pacAllocator.planner.fx.addFrom', {default: 'Pair: first currency'})}</span>
            <CurrencySearchSelect bind:value={addFrom} testId="pac-planner-fx-add-from" compact />
        </div>
        <div class="w-40">
            <span class={LABEL}>{$t('tools.pacAllocator.planner.fx.addTo', {default: 'second currency'})}</span>
            <CurrencySearchSelect bind:value={addTo} testId="pac-planner-fx-add-to" compact />
        </div>
        <button type="button" class={BUTTON_SECONDARY} disabled={!addPair || !!draft.fx(addPair)} data-testid="pac-planner-fx-add-apply" onclick={add}>
            <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.add', {default: 'Add'})}
        </button>
    </div>

    <label for="{ids}-spread" class="block max-w-xs">
        <span class={LABEL}>{$t('tools.pacAllocator.planner.fx.spread', {default: 'Conversion spread *'})} (%)</span>
        <ExactDecimalInput id="{ids}-spread" bind:value={draft.data.fxSpreadPercent} step="0.01" max="100" className={INPUT} testid="pac-planner-fx-spread" />
    </label>
    <p class={HINT}>{$t('tools.pacAllocator.planner.fx.spreadHint', {default: 'One per scenario, applied once to every conversion; the valuation uses the official rate.'})}</p>
    <p class={HINT}>{$t('tools.pacAllocator.planner.fx.pairsHint', {default: 'Pairs are proposed from the currencies of Assets, cash and order modes; a key only comes from the pair selector, in canonical order.'})}</p>
    <p class={HINT}>{$t('tools.pacAllocator.planner.fx.notInVersion', {default: 'Not in 2.0.0: FX per Broker, safety margin, conversion fee, multi-hop.'})}</p>
</div>

{#if copying}
    <SourceCopyDialog kind="fx" {draft} {accountGeneration} onclose={() => (copying = false)} oncopied={(outcome, source) => flow.accept(outcome, source)} />
{/if}
