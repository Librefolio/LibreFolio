<script lang="ts">
    import {untrack} from 'svelte';
    import {Plus, Trash2} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {DEFAULT_QUANTITY_STEP} from '../defaults';
    import {defaultMode, type DraftBroker, type DraftFunding, type DraftMode, type FundingSourceRef, type ModeKind, type PlannerDraft} from '../draft.svelte';
    import {cldrCurrencyStep, formatPlannerMoneyPlain, formatPlannerTimestamp} from '../format';
    import {MODE_KIND_FALLBACKS} from '../labels';
    import {BUTTON_LINK, BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, INPUT, LABEL, SECTION_TITLE} from '../ui';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        brokerKey: string;
        onclose: () => void;
    }

    let {draft, brokerKey, onclose}: Props = $props();

    const ids = $props.id();
    // Mount = open: the editor works on a copy taken once, and writes it back only on apply.
    const original = untrack(() => draft.broker(brokerKey));
    let working = $state<DraftBroker | null>(original ? structuredClone($state.snapshot(original)) : null);
    let newCurrency = $state('');

    const kindOptions = $derived((['whole_quantity', 'monetary_amount'] as const).map((kind) => ({value: kind, label: $t(`tools.pacAllocator.planner.modeKinds.${kind}`, {default: MODE_KIND_FALLBACKS[kind]})})));

    const usedCurrencies = $derived(new Set(working?.modes.map((mode) => mode.currency) ?? []));

    function setKind(mode: DraftMode, kind: string): void {
        if (kind !== 'whole_quantity' && kind !== 'monetary_amount') return;
        if (mode.kind === kind) return;
        mode.kind = kind as ModeKind;
        mode.step = kind === 'whole_quantity' ? DEFAULT_QUANTITY_STEP : cldrCurrencyStep(mode.currency);
    }

    function addMode(): void {
        if (!working || !/^[A-Z]{3}$/.test(newCurrency) || usedCurrencies.has(newCurrency)) return;
        working.modes.push(defaultMode(draft.nextId('mode'), newCurrency));
        newCurrency = '';
    }

    function removeMode(key: string): void {
        if (working) working.modes = working.modes.filter((mode) => mode.key !== key);
    }

    function restoreProposed(): void {
        if (working) working.modes = draft.defaultModes(working.observedCurrencies);
    }

    function sourceLabel(source: FundingSourceRef): string {
        if (source.kind === 'contribution') {
            const item = draft.contribution(source.contributionKey);
            return [item?.label || item?.currency || source.contributionKey, $t('tools.pacAllocator.planner.contribution.kind', {default: 'contribution'})].join(' · ');
        }
        const cash = draft.cashRow(source.cashKey);
        return cash ? [draft.broker(cash.brokerKey)?.name ?? cash.brokerKey, cash.currency].join(' · ') : source.cashKey;
    }

    function sourceAmount(source: FundingSourceRef): {amount: string; currency: string} | null {
        if (source.kind === 'contribution') {
            const item = draft.contribution(source.contributionKey);
            return item ? {amount: item.amount, currency: item.currency} : null;
        }
        const cash = draft.cashRow(source.cashKey);
        return cash ? {amount: cash.selected, currency: cash.currency} : null;
    }

    const candidates = $derived(working ? draft.fundingCandidates(working.key) : []);
    const localCash = $derived(working ? draft.data.cash.filter((cash) => cash.brokerKey === working!.key) : []);

    function fundingOf(source: FundingSourceRef): DraftFunding | undefined {
        return working ? draft.fundingFor(working, source) : undefined;
    }

    function toggleFunding(source: FundingSourceRef, enabled: boolean): void {
        if (!working) return;
        const existing = fundingOf(source);
        if (existing) existing.enabled = enabled;
        else if (enabled) working.funding.push({...draft.newFunding(source), enabled: true});
    }

    function apply(): void {
        if (!working) return;
        draft.replaceBroker($state.snapshot(working) as DraftBroker);
        onclose();
    }
</script>

<PlannerDialog open title={$t('tools.pacAllocator.planner.brokerEditor.title', {default: 'Configure {name} · scenario data (the Broker is not changed)', values: {name: working?.name || '—'}})} testid="pac-planner-broker-editor" {onclose} maxWidth="4xl">
    {#if working}
        <section class="space-y-2" aria-labelledby="{ids}-origin">
            <h3 id="{ids}-origin" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.brokerEditor.origin', {default: 'Origin'})}</h3>
            <div class="flex flex-wrap items-center gap-2 text-sm">
                <OriginBadge origin={working.origin} when={working.origin === 'copied' ? formatPlannerTimestamp(draft.copyRecord(working.stamp)?.capturedAt, $locale) : null} testid="pac-planner-broker-editor-origin" />
                {#if working.origin === 'copied'}
                    <span>{working.name}</span>
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-broker-editor-restore" onclick={restoreProposed}>
                        {$t('tools.pacAllocator.planner.brokerEditor.restore', {default: 'Restore the copied values'})}
                    </button>
                {:else}
                    <label class="flex-1">
                        <span class={LABEL}>{$t('common.name', {default: 'Name'})} *</span>
                        <input class={INPUT} bind:value={working.name} maxlength="120" data-testid="pac-planner-broker-editor-name" />
                    </label>
                {/if}
            </div>
        </section>

        <section class="space-y-2" aria-labelledby="{ids}-modes">
            <h3 id="{ids}-modes" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.brokerEditor.modes', {default: 'Order modes (one per currency)'})}</h3>
            <ul class="space-y-3">
                {#each working.modes as mode (mode.key)}
                    <li class="grid gap-2 rounded-lg border border-gray-200 p-3 md:grid-cols-[4rem_minmax(0,12rem)_minmax(0,10rem)_minmax(0,1fr)_auto] dark:border-gray-700" data-testid="pac-planner-mode" data-currency={mode.currency} data-kind={mode.kind}>
                        <div class="font-semibold">{mode.currency}</div>
                        <div>
                            <span class={LABEL}>{$t('tools.pacAllocator.planner.brokerEditor.kind', {default: 'In the Broker you enter'})}</span>
                            <SimpleSelect value={mode.kind} options={kindOptions} compact testId="pac-planner-mode-kind" onchange={(value) => setKind(mode, value)} />
                        </div>
                        <label for="{ids}-{mode.key}-step">
                            <span class={LABEL}>{$t('tools.pacAllocator.planner.brokerEditor.step', {default: 'Step'})} * <span class={HINT}>{mode.kind === 'whole_quantity' ? $t('tools.pacAllocator.planner.units.shares', {default: 'units'}) : mode.currency}</span></span>
                            <ExactDecimalInput id="{ids}-{mode.key}-step" bind:value={mode.step} step={mode.kind === 'whole_quantity' ? '1' : cldrCurrencyStep(mode.currency)} className={INPUT} testid="pac-planner-mode-step" />
                        </label>
                        <fieldset class="grid grid-cols-2 gap-2 sm:grid-cols-4">
                            <legend class={LABEL}>{$t('tools.pacAllocator.planner.brokerEditor.fee', {default: 'BUY fee (in the mode currency)'})}</legend>
                            <label for="{ids}-{mode.key}-fixed">
                                <span class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.feeFixed', {default: 'fixed'})}</span>
                                <ExactDecimalInput id="{ids}-{mode.key}-fixed" bind:value={mode.fixedFee} step={cldrCurrencyStep(mode.currency)} className={INPUT} testid="pac-planner-mode-fee-fixed" />
                            </label>
                            <label for="{ids}-{mode.key}-rate">
                                <span class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.feeRate', {default: 'rate %'})}</span>
                                <ExactDecimalInput id="{ids}-{mode.key}-rate" bind:value={mode.ratePercent} step="0.01" className={INPUT} testid="pac-planner-mode-fee-rate" />
                            </label>
                            <label for="{ids}-{mode.key}-floor">
                                <span class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.feeFloor', {default: 'min'})}</span>
                                <ExactDecimalInput id="{ids}-{mode.key}-floor" bind:value={mode.floor} step={cldrCurrencyStep(mode.currency)} className={INPUT} testid="pac-planner-mode-fee-floor" />
                            </label>
                            <label for="{ids}-{mode.key}-cap">
                                <span class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.feeCap', {default: 'max (empty = none)'})}</span>
                                <ExactDecimalInput id="{ids}-{mode.key}-cap" bind:value={mode.cap} step={cldrCurrencyStep(mode.currency)} className={INPUT} testid="pac-planner-mode-fee-cap" />
                            </label>
                        </fieldset>
                        <div class="flex items-end">
                            <button type="button" class={BUTTON_LINK} data-testid="pac-planner-mode-remove" onclick={() => removeMode(mode.key)}>
                                <Trash2 class="h-4 w-4" aria-hidden="true" /><span class="sr-only md:not-sr-only">{$t('common.remove', {default: 'Remove'})}</span>
                            </button>
                        </div>
                    </li>
                {:else}
                    <li class={HINT} data-testid="pac-planner-mode-empty">{$t('tools.pacAllocator.planner.problems.brokerNoMode', {default: 'The Broker has no order mode.'})}</li>
                {/each}
            </ul>
            <div class="flex flex-wrap items-end gap-2">
                <div class="w-56">
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.brokerEditor.addCurrency', {default: 'Add currency'})}</span>
                    <CurrencySearchSelect bind:value={newCurrency} excludedCurrencies={usedCurrencies} testId="pac-planner-mode-add-currency" compact />
                </div>
                <button type="button" class={BUTTON_SECONDARY} disabled={!newCurrency || usedCurrencies.has(newCurrency)} data-testid="pac-planner-mode-add" onclick={addMode}>
                    <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.add', {default: 'Add'})}
                </button>
            </div>
            <p class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.feeRule', {default: 'Fee = 0 when the amount is 0, otherwise fixed + clamp(rate × amount, min, max).'})}</p>
            <p class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.stepRule', {default: 'The step currency of an amount mode is the mode currency, locked. A fee has the currency of the price.'})}</p>
        </section>

        <section class="space-y-2" aria-labelledby="{ids}-funding">
            <h3 id="{ids}-funding" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.brokerEditor.funding', {default: 'Funding allowed to {name}', values: {name: working.name || '—'}})}</h3>
            <ul class="space-y-2 text-sm">
                {#each localCash as cash (cash.key)}
                    <li class="flex items-center gap-2" data-testid="pac-planner-funding-local">
                        <input type="checkbox" checked disabled class="rounded border-gray-300" aria-hidden="true" tabindex="-1" />
                        {$t('tools.pacAllocator.planner.brokerEditor.localCash', {default: 'Local cash {name} {currency} · no transfer', values: {name: working.name, currency: cash.currency}})}
                    </li>
                {/each}
                {#each candidates as source (source.kind === 'cash' ? source.cashKey : source.contributionKey)}
                    {@const funding = fundingOf(source)}
                    {@const amount = sourceAmount(source)}
                    <li class="space-y-2 rounded-lg border border-gray-200 p-2 dark:border-gray-700" data-testid="pac-planner-funding" data-source={source.kind === 'cash' ? source.cashKey : source.contributionKey} data-enabled={funding?.enabled ? 'true' : 'false'}>
                        <label class="flex flex-wrap items-center gap-2">
                            <input type="checkbox" class="rounded border-gray-300 text-libre-green focus:ring-libre-green" checked={funding?.enabled ?? false} data-testid="pac-planner-funding-toggle" onchange={(event) => toggleFunding(source, event.currentTarget.checked)} />
                            <span>{sourceLabel(source)} → {working.name || '—'}</span>
                            {#if amount}<span class={HINT}>· {$t('tools.pacAllocator.planner.brokerEditor.sourceAmount', {default: 'source {amount}', values: {amount: formatPlannerMoneyPlain(amount.amount, amount.currency)}})}</span>{/if}
                        </label>
                        {#if funding?.enabled}
                            <div class="grid gap-2 pl-6 sm:grid-cols-2">
                                <label for="{ids}-{funding.key}-priority">
                                    <span class={LABEL}>{$t('tools.pacAllocator.planner.route.priority', {default: 'Priority'})}</span>
                                    <ExactDecimalInput id="{ids}-{funding.key}-priority" bind:value={funding.priority} step="1" maxFractionDigits={0} className={INPUT} testid="pac-planner-funding-priority" />
                                    <span class={HINT}>{$t('tools.pacAllocator.planner.route.priorityHint', {default: '0 = preferred'})}</span>
                                </label>
                                <label for="{ids}-{funding.key}-cap">
                                    <span class={LABEL}>{$t('tools.pacAllocator.planner.brokerEditor.fundingCap', {default: 'Transfer cap'})} <span class={HINT}>{amount?.currency ?? ''}</span></span>
                                    <ExactDecimalInput id="{ids}-{funding.key}-cap" bind:value={funding.cap} step={amount?.currency ? cldrCurrencyStep(amount.currency) : '0.01'} className={INPUT} testid="pac-planner-funding-cap" />
                                    <span class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.fundingCapHint', {default: 'Empty = the whole amount of the source.'})}</span>
                                </label>
                            </div>
                        {/if}
                    </li>
                {:else}
                    {#if localCash.length === 0}
                        <li class={HINT} data-testid="pac-planner-funding-empty">{$t('tools.pacAllocator.planner.brokerEditor.noFunding', {default: 'No liquidity can reach this Broker yet: add cash or a contribution in the Liquidity step.'})}</li>
                    {/if}
                {/each}
            </ul>
        </section>

        <p class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.notIn200', {default: 'Not in 2.0.0: FX handling per currency, tax regime, losses, SELL fees.'})}</p>
    {/if}

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-broker-editor-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} disabled={!working} data-testid="pac-planner-broker-editor-apply" onclick={apply}>{$t('tools.pacAllocator.planner.applyToDraft', {default: 'Apply to the draft'})}</button>
    {/snippet}
</PlannerDialog>
