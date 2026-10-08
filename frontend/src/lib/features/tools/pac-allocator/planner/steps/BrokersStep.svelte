<script lang="ts">
    import {Pencil, PiggyBank, Plus, Trash2} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {CopyFlow} from '../copyFlow.svelte';
    import type {DraftBroker, FundingSourceRef, PlannerDraft, RemovalImpact} from '../draft.svelte';
    import {fundingSourceHelp, modeFeeText, modeIncrementText, modeKindText} from '../modeText';
    import {BADGE, BUTTON_DANGER, BUTTON_SECONDARY, CARD, HINT, ICON_BUBBLE, LABEL_ROW, NOTICE} from '../ui';
    import CopyFlowView from '../shared/CopyFlowView.svelte';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import PlannerBrokerIcon from '../shared/PlannerBrokerIcon.svelte';
    import RemovalConfirm from '../shared/RemovalConfirm.svelte';
    import BrokerEditor from './BrokerEditor.svelte';
    import BrokerScopeCopyDialog from './BrokerScopeCopyDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        accountGeneration: number;
    }

    let {draft, accountGeneration}: Props = $props();

    const flow = new CopyFlow();
    let copyOpen = $state(false);
    let editing = $state<string | null>(null);
    let removal = $state<{key: string; name: string; impact: RemovalImpact} | null>(null);

    const copyDisabled = $derived(!/^[A-Z]{3}$/.test(draft.data.valuationCurrency));

    function addManual(): void {
        const count = draft.data.brokers.filter((item) => item.origin === 'manual' && !item.fundingOnly).length + 1;
        const broker = draft.addManualBroker($t('tools.pacAllocator.planner.brokers.manualName', {default: 'Manual Broker {count}', values: {count}}));
        editing = broker.key;
    }

    /** Where a funding chip points: a Broker account (with its icon) or a contribution. */
    function sourceOf(source: FundingSourceRef): {broker: DraftBroker | undefined; label: string; currency: string | null} {
        if (source.kind === 'contribution') {
            const contribution = draft.contribution(source.contributionKey);
            return {broker: undefined, label: contribution?.label || source.contributionKey, currency: contribution?.currency ?? null};
        }
        const cash = draft.cashRow(source.cashKey);
        const broker = cash ? draft.broker(cash.brokerKey) : undefined;
        return {broker, label: broker?.name ?? cash?.brokerKey ?? source.cashKey, currency: cash?.currency ?? null};
    }

    const CHIP = 'inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 py-0.5 pl-0.5 pr-2 text-xs text-gray-800 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200';

    function askRemove(broker: DraftBroker): void {
        removal = {key: broker.key, name: broker.name, impact: draft.brokerRemovalImpact(broker.key)};
    }

    function confirmRemoval(): void {
        if (removal) draft.removeBroker(removal.key);
        removal = null;
    }
</script>

<div class="space-y-4" data-testid="pac-planner-brokers">
    <div class="flex flex-wrap gap-2">
        <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled} data-testid="pac-planner-broker-copy-open" onclick={() => (copyOpen = true)}>
            {$t('tools.pacAllocator.planner.brokers.copy', {default: 'Choose existing Broker'})}
        </button>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-broker-add" onclick={addManual}>
            <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.brokers.addManual', {default: 'Manual Broker'})}
        </button>
    </div>
    {#if copyDisabled}
        <p class={HINT}>{$t('tools.pacAllocator.planner.copy.needsCurrency', {default: 'Choose the valuation currency in the Scenario step to copy from the system.'})}</p>
    {/if}

    <CopyFlowView {flow} {draft} testid="pac-planner-brokers-notice" quiet />

    {#each draft.operativeBrokers as broker (broker.key)}
        {@const localCash = draft.data.cash.filter((cash) => cash.brokerKey === broker.key)}
        {@const routes = broker.funding.filter((item) => item.enabled)}
        <section class="{CARD} space-y-4" data-testid="pac-planner-broker" data-broker-key={broker.key} data-origin={broker.origin}>
            <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex min-w-0 items-center gap-2">
                    <PlannerBrokerIcon {broker} />
                    <h3 class="truncate font-semibold text-gray-900 dark:text-gray-100">{broker.name || '—'}</h3>
                    {#if !broker.active}<span class={BADGE.warning} data-testid="pac-planner-broker-inactive">{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>{/if}
                </div>
                <div class="flex shrink-0 flex-wrap gap-2">
                    <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-broker-edit" onclick={() => (editing = broker.key)}>
                        <Pencil class="h-4 w-4" aria-hidden="true" />{$t('common.edit', {default: 'Edit'})}
                    </button>
                    <button type="button" class={BUTTON_DANGER} data-testid="pac-planner-broker-remove" onclick={() => askRemove(broker)}>
                        <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
                    </button>
                </div>
            </div>

            {#if broker.modes.length === 0}
                <p class="text-sm text-red-700 dark:text-red-300">{$t('tools.pacAllocator.planner.problems.brokerNoMode', {default: 'The Broker has no order mode.'})}</p>
            {:else}
                <div class="space-y-3">
                    {#each broker.modes as mode (mode.key)}
                        <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid="pac-planner-broker-mode" data-currency={mode.currency}>
                            <p class="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100"><CurrencyCode code={mode.currency} /></p>
                            <dl class="grid grid-cols-[auto_minmax(0,1fr)] items-baseline gap-x-3 gap-y-1.5 text-sm">
                                <dt class="flex items-center gap-0.5 text-gray-500 dark:text-gray-400">
                                    {$t('tools.pacAllocator.planner.brokerEditor.kind', {default: 'Order type'})}
                                    <HelpTip label={$t('tools.pacAllocator.planner.brokerEditor.kind', {default: 'Order type'})} help={$t('tools.pacAllocator.planner.brokers.orderKindHelp', {default: 'How you enter an order at this Broker: by number of units (you buy 3 units) or by amount (you invest 150). It sets the unit of the increment and of the limits on each order.'})} />
                                </dt>
                                <dd class="text-gray-900 dark:text-gray-100" data-testid="pac-planner-broker-mode-kind">{modeKindText($t, mode.kind)}</dd>
                                <dt class="flex items-center gap-0.5 text-gray-500 dark:text-gray-400">
                                    {$t('tools.pacAllocator.planner.brokerEditor.step', {default: 'Increment'})}
                                    <HelpTip label={$t('tools.pacAllocator.planner.brokerEditor.step', {default: 'Increment'})} help={$t('tools.pacAllocator.planner.brokers.incrementHelp', {default: 'Every proposed order is a multiple of this value. By number of units: a whole number, for example 1. By amount: the smallest amount you can enter, for example 0.01; this is how you buy fractions of a unit.'})} />
                                </dt>
                                <dd class="tabular-nums text-gray-900 dark:text-gray-100" data-testid="pac-planner-broker-mode-step">{modeIncrementText($t, mode)}</dd>
                                <dt class="flex items-center gap-0.5 text-gray-500 dark:text-gray-400">
                                    {$t('tools.pacAllocator.planner.brokerEditor.fee', {default: 'Purchase fee'})}
                                    <HelpTip label={$t('tools.pacAllocator.planner.brokerEditor.fee', {default: 'Purchase fee'})} help={$t('tools.pacAllocator.planner.brokers.feeHelp', {default: 'What the Broker charges on each purchase: the percentage of the amount, kept between minimum and maximum, plus the fixed part. No purchase, no fee. It is paid from your liquidity and is not invested.\n\nExamples, in the currency of the purchase:\n• 0.19%, minimum 1.50, maximum 18: on 500 you pay 1.50, on 2,000 you pay 3.80, on 20,000 you pay 18.\n• Only a fixed part of 2.95: 2.95 on any purchase.\n• Fixed part 1 plus 0.10%: on 1,000 you pay 2.\n• Everything at 0: no fee.'})} />
                                </dt>
                                <dd class="tabular-nums text-gray-900 dark:text-gray-100" data-testid="pac-planner-broker-mode-fee">{modeFeeText($t, mode)}</dd>
                            </dl>
                        </div>
                    {/each}
                </div>
            {/if}

            <div class="space-y-1">
                <p class={LABEL_ROW}>
                    {$t('tools.pacAllocator.planner.brokers.conversionLabel', {default: 'Currency conversion'})}
                    <HelpTip label={$t('tools.pacAllocator.planner.brokers.conversionLabel', {default: 'Currency conversion'})} help={$t('tools.pacAllocator.planner.brokers.conversionHelp', {default: 'When a purchase needs a currency you do not hold here, money is converted at the rate and spread of the FX step. If you convert yourself, the plan gives the conversion as a numbered step before the orders; if the Broker converts when you buy, the plan shows it next to its orders. The calculation is the same either way.'})} />
                </p>
                <p class="text-sm text-gray-800 dark:text-gray-200" data-testid="pac-planner-broker-conversion" data-mode={broker.conversionMode}>
                    {broker.conversionMode === 'automatic'
                        ? $t('tools.pacAllocator.planner.brokers.conversionValueAuto', {default: 'The Broker converts when you buy, at the rate of the FX step minus the spread.'})
                        : $t('tools.pacAllocator.planner.brokers.conversionValue', {default: 'You convert before buying, at the rate of the FX step minus the spread.'})}
                </p>
            </div>

            <div class="space-y-1.5" data-testid="pac-planner-broker-funding">
                <p class={LABEL_ROW}>
                    {$t('tools.pacAllocator.planner.brokers.fundingLabel', {default: 'Usable liquidity'})}
                    <HelpTip label={$t('tools.pacAllocator.planner.brokers.fundingLabel', {default: 'Usable liquidity'})} help={$t('tools.pacAllocator.planner.brokers.fundingHelp', {default: 'The money the plan may use to buy on this Broker: its own cash, plus the contributions and the cash of other accounts you allow in Edit. Everything is allowed at first; in Edit, click a source to exclude it.'})} />
                </p>
                {#if localCash.length === 0 && routes.length === 0}
                    <p class="text-sm text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.planner.brokers.noFunding', {default: 'none yet'})}</p>
                {:else}
                    <ul class="flex flex-wrap gap-1.5">
                        {#each localCash as cash (cash.key)}
                            <li data-testid="pac-planner-broker-funding-local" data-currency={cash.currency}>
                                <Tooltip text={fundingSourceHelp($t, 'local', broker.name, cash.currency)} maxWidth="320px">
                                    <span class={CHIP}>
                                        <PlannerBrokerIcon {broker} size={20} />
                                        <span class="max-w-40 truncate">{broker.name || '—'}</span>
                                        <CurrencyCode code={cash.currency} />
                                    </span>
                                </Tooltip>
                            </li>
                        {/each}
                        {#each routes as item (item.key)}
                            {@const source = sourceOf(item.source)}
                            <li data-testid="pac-planner-broker-funding-route" data-source-kind={item.source.kind}>
                                <Tooltip text={fundingSourceHelp($t, item.source.kind === 'contribution' ? 'contribution' : 'account', source.label, source.currency ?? '')} maxWidth="320px">
                                    <span class={CHIP}>
                                        {#if item.source.kind === 'contribution'}
                                            <span class={ICON_BUBBLE} style="width: 20px; height: 20px;"><PiggyBank size={12} aria-hidden="true" /></span>
                                        {:else}
                                            <PlannerBrokerIcon broker={source.broker} size={20} />
                                        {/if}
                                        <span class="max-w-40 truncate">{source.label}</span>
                                        {#if source.currency}<CurrencyCode code={source.currency} />{/if}
                                    </span>
                                </Tooltip>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>
        </section>
    {/each}

    {#each draft.fundingOnlyBrokers as broker (broker.key)}
        <section class="{CARD} space-y-1" data-testid="pac-planner-broker-funding-only" data-broker-key={broker.key}>
            <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="flex min-w-0 items-center gap-2">
                    <PlannerBrokerIcon {broker} />
                    <h3 class="truncate font-semibold text-gray-900 dark:text-gray-100">{broker.name || '—'}</h3>
                </div>
                <div class="flex gap-1">
                    <OriginBadge origin={broker.origin} testid="pac-planner-broker-origin" />
                    <span class={BADGE.neutral}>{$t('tools.pacAllocator.planner.brokers.fundingOnly', {default: 'funding only'})}</span>
                </div>
            </div>
            <p class={HINT}>{$t('tools.pacAllocator.planner.brokers.fundingOnlyHint', {default: 'No order: it funds other Brokers through routes. Edit it in the Liquidity step.'})}</p>
        </section>
    {/each}

    {#if draft.operativeBrokers.length === 0}
        <p class={NOTICE.info} data-testid="pac-planner-brokers-empty">{$t('tools.pacAllocator.planner.problems.noOperativeBroker', {default: 'Add at least one Broker on which orders can be proposed.'})}</p>
    {/if}
</div>

{#if copyOpen}
    <BrokerScopeCopyDialog kind="brokers" {draft} {accountGeneration} onclose={() => (copyOpen = false)} oncopied={(outcome, source) => flow.accept(outcome, source)} />
{/if}
{#if editing}
    <BrokerEditor {draft} brokerKey={editing} onclose={() => (editing = null)} />
{/if}
<RemovalConfirm
    open={removal !== null}
    {draft}
    title={$t('tools.pacAllocator.planner.removal.title', {default: 'Remove {name}?', values: {name: removal?.name ?? ''}})}
    message={$t('tools.pacAllocator.planner.removal.message', {default: 'It leaves the draft only; nothing changes in the system.'})}
    impact={removal?.impact ?? null}
    testId="pac-planner-broker-removal"
    onConfirm={confirmRemoval}
    onCancel={() => (removal = null)}
/>
