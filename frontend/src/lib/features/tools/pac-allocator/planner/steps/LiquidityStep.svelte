<script lang="ts">
    import {Plus, Trash2} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import {CopyFlow} from '../copyFlow.svelte';
    import {compareDecimal} from '../decimal';
    import {selectionExceedsAvailable, type DraftCash, type PlannerDraft, type RemovalImpact} from '../draft.svelte';
    import {cldrCurrencyStep, formatPlannerMoneyPlain, formatPlannerPercent, formatPlannerTimestamp} from '../format';
    import {BUTTON_DANGER, BUTTON_SECONDARY, CARD, HINT, INPUT, LABEL, NOTICE} from '../ui';
    import CopyFlowView from '../shared/CopyFlowView.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import RemovalConfirm from '../shared/RemovalConfirm.svelte';
    import BrokerScopeCopyDialog from './BrokerScopeCopyDialog.svelte';
    import ManualAccountDialog from './ManualAccountDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
    }

    let {draft, accountGeneration}: Props = $props();

    const ids = $props.id();
    const flow = new CopyFlow();
    let copyOpen = $state(false);
    let manualOpen = $state(false);
    let removal = $state<{kind: 'cash' | 'account' | 'contribution'; key: string; label: string; impact: RemovalImpact} | null>(null);

    const copyDisabled = $derived(!/^[A-Z]{3}$/.test(draft.data.valuationCurrency));

    function brokerName(cash: DraftCash): string {
        return draft.broker(cash.brokerKey)?.name ?? cash.brokerKey;
    }

    function partial(share: string | null): boolean {
        return share !== null && compareDecimal(share, '1') === -1;
    }

    function cashImpact(cash: DraftCash): RemovalImpact {
        const funding = draft.data.brokers.flatMap((broker) => broker.funding.filter((item) => item.source.kind === 'cash' && item.source.cashKey === cash.key).map((item) => ({broker, funding: item})));
        return {routes: [], cash: [cash], funding, target: false};
    }

    function askRemoveCash(cash: DraftCash): void {
        const broker = draft.broker(cash.brokerKey);
        const label = `${brokerName(cash)} · ${cash.currency}`;
        if (cash.origin === 'manual' && broker?.fundingOnly) removal = {kind: 'account', key: broker.key, label, impact: draft.brokerRemovalImpact(broker.key)};
        else removal = {kind: 'cash', key: cash.key, label, impact: cashImpact(cash)};
    }

    function askRemoveContribution(key: string, label: string): void {
        const funding = draft.data.brokers.flatMap((broker) => broker.funding.filter((item) => item.source.kind === 'contribution' && item.source.contributionKey === key).map((item) => ({broker, funding: item})));
        removal = {kind: 'contribution', key, label, impact: {routes: [], cash: [], funding, target: false}};
    }

    function confirmRemoval(): void {
        if (!removal) return;
        if (removal.kind === 'account') draft.removeBroker(removal.key);
        else if (removal.kind === 'cash') draft.removeCash(removal.key);
        else draft.removeContribution(removal.key);
        removal = null;
    }

    function addContribution(): void {
        draft.addContribution(draft.data.valuationCurrency, '');
    }
</script>

<div class="space-y-4" data-testid="pac-planner-liquidity">
    <div class="flex flex-wrap gap-2">
        <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled} data-testid="pac-planner-liquidity-copy-open" onclick={() => (copyOpen = true)}>
            {$t('tools.pacAllocator.planner.liquidity.copy', {default: 'Copy liquidity from Brokers'})}
        </button>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-contribution-add" onclick={addContribution}>
            <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.liquidity.addContribution', {default: 'Contribution'})}
        </button>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-manual-account-open" onclick={() => (manualOpen = true)}>
            <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.liquidity.addManual', {default: 'Manual account'})}
        </button>
    </div>
    {#if copyDisabled}
        <p class={HINT} data-testid="pac-planner-copy-needs-currency">{$t('tools.pacAllocator.planner.copy.needsCurrency', {default: 'Choose the valuation currency in the Scenario step to copy from the system.'})}</p>
    {/if}

    <CopyFlowView {flow} {draft} testid="pac-planner-liquidity-notice" />

    {#each draft.data.cash as cash (cash.key)}
        {@const broker = draft.broker(cash.brokerKey)}
        {@const exceeds = selectionExceedsAvailable(cash)}
        <section class="{CARD} space-y-3" data-testid="pac-planner-cash" data-cash-key={cash.key} data-origin={cash.origin} aria-labelledby="{ids}-{cash.key}-title">
            <div class="flex flex-wrap items-start justify-between gap-2">
                <h3 id="{ids}-{cash.key}-title" class="font-semibold text-gray-900 dark:text-gray-100">
                    {#if broker?.fundingOnly}
                        {$t('tools.pacAllocator.planner.cash.manualTitle', {default: '{name} · manual account {currency}', values: {name: brokerName(cash), currency: cash.currency}})}
                    {:else}
                        {$t('tools.pacAllocator.planner.cash.title', {default: '{name} · cash {currency}', values: {name: brokerName(cash), currency: cash.currency}})}
                    {/if}
                </h3>
                <OriginBadge origin={cash.origin} when={cash.origin === 'copied' ? formatPlannerTimestamp(draft.copyRecord(cash.stamp)?.capturedAt, $locale) : null} testid="pac-planner-cash-origin" />
            </div>
            {#if cash.origin === 'copied'}
                <p class="text-sm tabular-nums" data-testid="pac-planner-cash-available">
                    {$t('tools.pacAllocator.planner.cash.custody', {default: 'Available (custody) {amount}', values: {amount: formatPlannerMoneyPlain(cash.available, cash.currency)}})}
                    ·
                    {#if partial(cash.ownershipShare)}
                        {$t('tools.pacAllocator.planner.cash.share', {default: 'share {share} · yours {amount}', values: {share: formatPlannerPercent(cash.ownershipShare), amount: formatPlannerMoneyPlain(cash.economicAmount, cash.currency)}})}
                    {:else}
                        {$t('tools.pacAllocator.planner.liquidityCopy.allYours', {default: '100% yours'})}
                    {/if}
                </p>
            {:else}
                <div class="grid gap-3 sm:grid-cols-2">
                    <label>
                        <span class={LABEL}>{$t('tools.pacAllocator.planner.manualAccount.name', {default: 'Account name'})} *</span>
                        {#if broker}<input class={INPUT} bind:value={broker.name} maxlength="120" data-testid="pac-planner-cash-name" />{/if}
                    </label>
                    <label for="{ids}-{cash.key}-available">
                        <span class={LABEL}>{$t('tools.pacAllocator.planner.manualAccount.declared', {default: 'Declared liquidity'})} * <span class={HINT}>{cash.currency}</span></span>
                        <ExactDecimalInput id="{ids}-{cash.key}-available" bind:value={cash.available} step={cldrCurrencyStep(cash.currency)} className={INPUT} testid="pac-planner-cash-declared" />
                    </label>
                </div>
            {/if}
            <label class="block max-w-sm" for="{ids}-{cash.key}-selected">
                <span class={LABEL}>{$t('tools.pacAllocator.planner.cash.selected', {default: 'Amount to use'})} * <span class={HINT}>{cash.currency}</span></span>
                <ExactDecimalInput id="{ids}-{cash.key}-selected" bind:value={cash.selected} step={cldrCurrencyStep(cash.currency)} className={INPUT} externalInvalid={exceeds} ariaDescribedby="{ids}-{cash.key}-hint" testid="pac-planner-cash-selected" />
                <span id="{ids}-{cash.key}-hint" class={HINT}>{$t('tools.pacAllocator.planner.cash.noPrefill', {default: 'No prefill: you write the amount.'})}</span>
            </label>
            {#if exceeds}
                <p class="text-sm text-red-700 dark:text-red-300" role="alert" data-testid="pac-planner-cash-exceeds">{$t('tools.pacAllocator.planner.problems.selectedExceedsAvailable', {default: "'Amount to use' exceeds the available amount in the same currency."})}</p>
            {/if}
            {#if broker?.fundingOnly}
                <p class={HINT}>{$t('tools.pacAllocator.planner.cash.fundingOnly', {default: 'Funding only: it does not buy. It needs a funding route in the Broker step.'})}</p>
            {/if}
            <button type="button" class={BUTTON_DANGER} data-testid="pac-planner-cash-remove" onclick={() => askRemoveCash(cash)}>
                <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
            </button>
        </section>
    {/each}

    {#each draft.data.contributions as item (item.key)}
        <section class="{CARD} space-y-3" data-testid="pac-planner-contribution" data-contribution-key={item.key} aria-labelledby="{ids}-{item.key}-title">
            <div class="flex flex-wrap items-start justify-between gap-2">
                <h3 id="{ids}-{item.key}-title" class="font-semibold text-gray-900 dark:text-gray-100">
                    {item.label.trim() || $t('tools.pacAllocator.planner.contribution.untitled', {default: 'New contribution'})} · {$t('tools.pacAllocator.planner.contribution.kind', {default: 'contribution'})}
                </h3>
                <OriginBadge origin="manual" testid="pac-planner-contribution-origin" />
            </div>
            <div class="grid gap-3 sm:grid-cols-3">
                <label for="{ids}-{item.key}-amount">
                    <span class={LABEL}>{$t('common.amount', {default: 'Amount'})} * <span class={HINT}>{item.currency}</span></span>
                    <ExactDecimalInput id="{ids}-{item.key}-amount" bind:value={item.amount} step={item.currency ? cldrCurrencyStep(item.currency) : '0.01'} className={INPUT} testid="pac-planner-contribution-amount" />
                </label>
                <div>
                    <span class={LABEL}>{$t('common.currency', {default: 'Currency'})} *</span>
                    <CurrencySearchSelect bind:value={item.currency} testId="pac-planner-contribution-currency" compact />
                </div>
                <label>
                    <span class={LABEL}>{$t('tools.pacAllocator.planner.contribution.label', {default: 'Label'})} *</span>
                    <input class={INPUT} bind:value={item.label} maxlength="120" data-testid="pac-planner-contribution-label" />
                </label>
            </div>
            <p class={HINT}>{$t('tools.pacAllocator.planner.contribution.destination', {default: 'Destination: a funding route in the Broker step.'})}</p>
            <button type="button" class={BUTTON_DANGER} data-testid="pac-planner-contribution-remove" onclick={() => askRemoveContribution(item.key, item.label.trim() || item.currency)}>
                <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
            </button>
        </section>
    {/each}

    {#if draft.data.cash.length === 0 && draft.data.contributions.length === 0}
        <p class={NOTICE.info} data-testid="pac-planner-liquidity-empty">{$t('tools.pacAllocator.planner.liquidity.empty', {default: 'No liquidity yet. Copy it from your Brokers, add a contribution or a manual account.'})}</p>
    {/if}
    <p class={HINT}>{$t('tools.pacAllocator.planner.liquidity.noConversion', {default: 'No converted equivalent: FX happens only in the backend.'})}</p>
</div>

{#if copyOpen}
    <BrokerScopeCopyDialog kind="liquidity" {draft} {accountGeneration} onclose={() => (copyOpen = false)} oncopied={(outcome, source) => flow.accept(outcome, source)} />
{/if}
{#if manualOpen}
    <ManualAccountDialog {draft} onclose={() => (manualOpen = false)} />
{/if}
<RemovalConfirm
    open={removal !== null}
    {draft}
    title={$t('tools.pacAllocator.planner.removal.title', {default: 'Remove {name}?', values: {name: removal?.label ?? ''}})}
    message={$t('tools.pacAllocator.planner.removal.message', {default: 'It leaves the draft only; nothing changes in the system.'})}
    impact={removal?.impact ?? null}
    testId="pac-planner-liquidity-removal"
    onConfirm={confirmRemoval}
    onCancel={() => (removal = null)}
/>
