<script lang="ts">
    import {Briefcase, Landmark, PenLine, PiggyBank, Plus, Trash2} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import {CopyFlow} from '../copyFlow.svelte';
    import {canonicalInput, compareDecimal, decimalSign} from '../decimal';
    import {selectionExceedsAvailable, type DraftCash, type PlannerDraft, type RemovalImpact} from '../draft.svelte';
    import {cldrCurrencyStep, formatPlannerMoneyPlain, formatPlannerPercent} from '../format';
    import {BUTTON_DANGER, BUTTON_SECONDARY, CHOICE_CARD, HINT, ICON_BUBBLE, INPUT, LABEL, NOTICE, TITLE_INPUT} from '../ui';
    import CopyFlowView from '../shared/CopyFlowView.svelte';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import PlannerBrokerIcon from '../shared/PlannerBrokerIcon.svelte';
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

    /** «All» fills the amount to use with the whole available amount, the most the plan accepts. */
    function allAvailable(cash: DraftCash): string | null {
        const available = canonicalInput(cash.available);
        return available !== null && decimalSign(available) === 1 ? available : null;
    }

    function useAll(cash: DraftCash): void {
        const available = allAvailable(cash);
        if (available !== null) cash.selected = available;
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

    /** «New contribution N», with the first N not already taken; the user renames it in the card title. */
    function addContribution(): void {
        const taken = new Set(draft.data.contributions.map((item) => item.label.trim()));
        const labelFor = (n: number): string => $t('tools.pacAllocator.planner.contribution.defaultLabel', {default: 'New contribution {n}', values: {n: String(n)}});
        let n = draft.data.contributions.length + 1;
        while (taken.has(labelFor(n))) n += 1;
        draft.addContribution(draft.data.valuationCurrency, labelFor(n));
    }
</script>

<div class="space-y-4" data-testid="pac-planner-liquidity">
    <div class="space-y-2">
        <p class="text-sm text-gray-700 dark:text-gray-300">{$t('tools.pacAllocator.planner.liquidity.intro', {default: 'Where does the money to invest come from? You can combine several sources.'})}</p>
        <div class="grid gap-2 sm:grid-cols-3">
            <button type="button" class={CHOICE_CARD} disabled={copyDisabled} data-testid="pac-planner-liquidity-copy-open" onclick={() => (copyOpen = true)}>
                <span class="flex w-full items-center gap-2 font-medium text-gray-900 dark:text-gray-100">
                    <span class={ICON_BUBBLE}><Briefcase class="h-4 w-4" aria-hidden="true" /></span>
                    <span class="flex-1">{$t('tools.pacAllocator.planner.liquidity.copy', {default: 'From your Brokers'})}</span>
                    <Plus class="h-4 w-4 text-gray-400" aria-hidden="true" />
                </span>
                <span class={HINT}>{$t('tools.pacAllocator.planner.liquidity.copyHint', {default: 'Cash already on the Brokers registered in LibreFolio. You choose how much to use.'})}</span>
            </button>
            <button type="button" class={CHOICE_CARD} data-testid="pac-planner-contribution-add" onclick={addContribution}>
                <span class="flex w-full items-center gap-2 font-medium text-gray-900 dark:text-gray-100">
                    <span class={ICON_BUBBLE}><PiggyBank class="h-4 w-4" aria-hidden="true" /></span>
                    <span class="flex-1">{$t('tools.pacAllocator.planner.liquidity.addContribution', {default: 'New contribution'})}</span>
                    <Plus class="h-4 w-4 text-gray-400" aria-hidden="true" />
                </span>
                <span class={HINT}>{$t('tools.pacAllocator.planner.liquidity.contributionHint', {default: 'New money you add, for example the PAC instalment. In the Broker step you choose which Broker receives it.'})}</span>
            </button>
            <button type="button" class={CHOICE_CARD} data-testid="pac-planner-manual-account-open" onclick={() => (manualOpen = true)}>
                <span class="flex w-full items-center gap-2 font-medium text-gray-900 dark:text-gray-100">
                    <span class={ICON_BUBBLE}><Landmark class="h-4 w-4" aria-hidden="true" /></span>
                    <span class="flex-1">{$t('tools.pacAllocator.planner.liquidity.addManual', {default: 'External account'})}</span>
                    <Plus class="h-4 w-4 text-gray-400" aria-hidden="true" />
                </span>
                <span class={HINT}>{$t('tools.pacAllocator.planner.liquidity.manualHint', {default: 'A balance you already have on an account not registered in LibreFolio, for example at your bank. You declare how much is there and how much to use.'})}</span>
            </button>
        </div>
    </div>
    {#if copyDisabled}
        <p class={HINT} data-testid="pac-planner-copy-needs-currency">{$t('tools.pacAllocator.planner.copy.needsCurrency', {default: 'Choose the valuation currency in the Scenario step to copy from the system.'})}</p>
    {/if}

    <CopyFlowView {flow} {draft} testid="pac-planner-liquidity-notice" quiet />

    {#if draft.liquidityEntries.length > 0}
        <OrderableList items={draft.liquidityEntries} keyFn={(entry) => entry.key} onReorder={(next) => draft.reorderLiquidity(next.map((entry) => entry.key))}>
            {#snippet children({item: entry})}
                {#if entry.kind === 'cash'}
                    {@const cash = entry.cash}
                    {@const broker = draft.broker(cash.brokerKey)}
                    {@const exceeds = selectionExceedsAvailable(cash)}
                    <section class="space-y-3 p-1 sm:p-2" data-testid="pac-planner-cash" data-cash-key={cash.key} data-origin={cash.origin} aria-labelledby="{ids}-{cash.key}-title">
                        <div class="flex flex-wrap items-start justify-between gap-2">
                            <div class="flex min-w-0 items-center gap-2">
                                <PlannerBrokerIcon {broker} />
                                <h3 id="{ids}-{cash.key}-title" class="flex min-w-0 flex-wrap items-center gap-x-2 font-semibold text-gray-900 dark:text-gray-100">
                                    <span>
                                        {#if broker?.fundingOnly}
                                            {$t('tools.pacAllocator.planner.cash.manualTitle', {default: '{name} · external account', values: {name: brokerName(cash)}})}
                                        {:else}
                                            {$t('tools.pacAllocator.planner.cash.title', {default: '{name} · cash', values: {name: brokerName(cash)}})}
                                        {/if}
                                    </span>
                                    <CurrencyCode code={cash.currency} testid="pac-planner-cash-currency" />
                                </h3>
                            </div>
                            {#if cash.origin === 'manual'}<OriginBadge origin="manual" testid="pac-planner-cash-origin" />{/if}
                        </div>
                        {#if cash.origin === 'copied'}
                            <p class="text-sm tabular-nums" data-testid="pac-planner-cash-available">
                                {$t('tools.pacAllocator.planner.cash.custody', {default: 'Available (custody) {amount}', values: {amount: formatPlannerMoneyPlain(cash.available, cash.currency)}})}
                                ·
                                {#if partial(cash.ownershipShare)}
                                    {$t('tools.pacAllocator.planner.cash.share', {default: 'share {share} · yours {amount}', values: {share: formatPlannerPercent(cash.ownershipShare), amount: formatPlannerMoneyPlain(cash.economicAmount, cash.currency, {minorUnit: true})}})}
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
                                    <span class={LABEL}>{$t('tools.pacAllocator.planner.manualAccount.declared', {default: 'Declared liquidity'})} * <CurrencyCode code={cash.currency} /></span>
                                    <ExactDecimalInput id="{ids}-{cash.key}-available" bind:value={cash.available} step={cldrCurrencyStep(cash.currency)} className={INPUT} testid="pac-planner-cash-declared" />
                                </label>
                            </div>
                        {/if}
                        <div class="max-w-sm space-y-1">
                            <label class={LABEL} for="{ids}-{cash.key}-selected">{$t('tools.pacAllocator.planner.cash.selected', {default: 'Amount to use'})} * <CurrencyCode code={cash.currency} /></label>
                            <div class="flex gap-2">
                                <div class="min-w-0 flex-1">
                                    <ExactDecimalInput id="{ids}-{cash.key}-selected" bind:value={cash.selected} step={cldrCurrencyStep(cash.currency)} className={INPUT} externalInvalid={exceeds} ariaDescribedby="{ids}-{cash.key}-hint" testid="pac-planner-cash-selected" />
                                </div>
                                <button type="button" class={BUTTON_SECONDARY} disabled={allAvailable(cash) === null} title={$t('tools.pacAllocator.planner.cash.useAllHint', {default: 'Use the whole available amount'})} data-testid="pac-planner-cash-use-all" onclick={() => useAll(cash)}>
                                    {$t('tools.pacAllocator.planner.cash.useAll', {default: 'All'})}
                                </button>
                            </div>
                            <p id="{ids}-{cash.key}-hint" class={HINT}>
                                {#if cash.origin === 'copied'}
                                    {$t('tools.pacAllocator.planner.cash.selectedAll', {default: 'It starts from the whole available amount: lower it if you want to invest less.'})}
                                {:else}
                                    {$t('tools.pacAllocator.planner.cash.noPrefill', {default: 'Write how much of this cash you want to invest.'})}
                                {/if}
                            </p>
                        </div>
                        {#if exceeds}
                            <p class="text-sm text-red-700 dark:text-red-300" role="alert" data-testid="pac-planner-cash-exceeds">{$t('tools.pacAllocator.planner.problems.selectedExceedsAvailable', {default: "'Amount to use' exceeds the available amount in the same currency."})}</p>
                        {/if}
                        {#if broker?.fundingOnly}
                            <p class={HINT}>{$t('tools.pacAllocator.planner.cash.fundingOnly', {default: 'Nothing is bought from this account: in the Broker step you choose which Broker receives this money.'})}</p>
                        {/if}
                        <button type="button" class={BUTTON_DANGER} data-testid="pac-planner-cash-remove" onclick={() => askRemoveCash(cash)}>
                            <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
                        </button>
                    </section>
                {:else}
                    {@const item = entry.contribution}
                    <section class="space-y-3 p-1 sm:p-2" data-testid="pac-planner-contribution" data-contribution-key={item.key} aria-labelledby="{ids}-{item.key}-title">
                        <div class="flex items-start justify-between gap-2">
                            <div class="flex min-w-0 flex-1 items-center gap-2">
                                <span class={ICON_BUBBLE}><PiggyBank class="h-4 w-4" aria-hidden="true" /></span>
                                <h3 id="{ids}-{item.key}-title" class="group relative min-w-0 flex-1">
                                    <input
                                        class="{TITLE_INPUT} pr-7"
                                        bind:value={item.label}
                                        maxlength="120"
                                        placeholder={$t('tools.pacAllocator.planner.contribution.untitled', {default: 'New contribution'})}
                                        aria-label={$t('tools.pacAllocator.planner.contribution.label', {default: 'Label'})}
                                        data-testid="pac-planner-contribution-label"
                                    />
                                    <PenLine class="pointer-events-none absolute top-1/2 right-2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400 opacity-60 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100" aria-hidden="true" />
                                </h3>
                            </div>
                            <OriginBadge origin="manual" testid="pac-planner-contribution-origin" />
                        </div>
                        <div class="grid gap-3 sm:grid-cols-2">
                            <label for="{ids}-{item.key}-amount">
                                <span class={LABEL}>{$t('common.amount', {default: 'Amount'})} *</span>
                                <ExactDecimalInput id="{ids}-{item.key}-amount" bind:value={item.amount} step={item.currency ? cldrCurrencyStep(item.currency) : '0.01'} className={INPUT} testid="pac-planner-contribution-amount" />
                            </label>
                            <div>
                                <span class={LABEL}>{$t('common.currency', {default: 'Currency'})} *</span>
                                <CurrencySearchSelect bind:value={item.currency} testId="pac-planner-contribution-currency" compact />
                            </div>
                        </div>
                        <p class={HINT}>{$t('tools.pacAllocator.planner.contribution.destination', {default: 'In the Broker step you choose which Broker receives this contribution.'})}</p>
                        <button type="button" class={BUTTON_DANGER} data-testid="pac-planner-contribution-remove" onclick={() => askRemoveContribution(item.key, item.label.trim() || item.currency)}>
                            <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
                        </button>
                    </section>
                {/if}
            {/snippet}
        </OrderableList>
    {:else}
        <p class={NOTICE.info} data-testid="pac-planner-liquidity-empty">{$t('tools.pacAllocator.planner.liquidity.empty', {default: 'No liquidity yet: pick one of the sources above.'})}</p>
    {/if}
    <p class={HINT}>{$t('tools.pacAllocator.planner.liquidity.noConversion', {default: 'Each amount stays in its own currency; conversions, if needed, are worked out by the plan.'})}</p>
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
