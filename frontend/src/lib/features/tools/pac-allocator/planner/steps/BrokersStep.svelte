<script lang="ts">
    import {onDestroy} from 'svelte';
    import {Pencil, PiggyBank, Plus, Trash2} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import {CopyFlow} from '../copyFlow.svelte';
    import {applyBrokerCopy, newCopyRecord} from '../copies';
    import {SourceLoad} from '../sourceLoad.svelte';
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
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

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

    const CHIP = 'inline-flex items-center gap-1.5 rounded-full border border-lf-subtle bg-lf-panel py-0.5 pl-0.5 pr-2 text-xs text-lf-primary';

    // -- «Positions only» Brokers (Q-F3a-5b): a position held at a Broker outside the scenario --------------------------

    const brokerRead = new SourceLoad();
    onDestroy(() => brokerRead.stop());
    let addingBroker = $state<string | null>(null);
    let addFailed = $state<string | null>(null);

    /** «Add to the plan»: reads the Broker from LibreFolio and copies it as any copied Broker, operating profile included (P3). */
    async function addToPlan(item: {brokerKey: string; sourceBrokerId: number}): Promise<void> {
        addingBroker = item.brokerKey;
        addFailed = null;
        draft.refreshAsOf();
        const source = await brokerRead.load({asOf: draft.data.asOf, targetCurrency: draft.data.valuationCurrency, sections: ['brokers'], brokerIds: [item.sourceBrokerId], assetIds: [], fxPairs: []}, accountGeneration);
        addingBroker = null;
        if (!source || !source.brokers.some((row) => row.source_broker_id === item.sourceBrokerId)) {
            addFailed = item.brokerKey;
            return;
        }
        // The same notice as a copy from «Copy from a Broker»: a Broker without an operating profile says so (Q-P3b).
        flow.accept(applyBrokerCopy(draft, source, newCopyRecord(draft, 'brokers', source), [item.sourceBrokerId]), source);
    }

    function askRemove(broker: DraftBroker): void {
        removal = {key: broker.key, name: broker.name, impact: draft.brokerRemovalImpact(broker.key)};
    }

    function confirmRemoval(): void {
        if (removal) draft.removeBroker(removal.key);
        removal = null;
    }
</script>

<div class="space-y-4" data-testid={testId('brokers', profile)}>
    <div class="flex flex-wrap gap-2">
        <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled} data-testid={testId('broker-copy-open', profile)} onclick={() => (copyOpen = true)}>
            {$t('tools.pacAllocator.planner.brokers.copy', {default: 'Choose existing Broker'})}
        </button>
        <button type="button" class={BUTTON_SECONDARY} data-testid={testId('broker-add', profile)} onclick={addManual}>
            <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.brokers.addManual', {default: 'Manual Broker'})}
        </button>
    </div>
    {#if copyDisabled}
        <p class={HINT}>{$t('tools.pacAllocator.planner.copy.needsCurrency', {default: 'Choose the valuation currency in the Scenario step to copy from the system.'})}</p>
    {/if}

    <CopyFlowView {flow} {draft} testid={testId('brokers-notice', profile)} quiet />

    {#each draft.operativeBrokers as broker (broker.key)}
        {@const localCash = draft.data.cash.filter((cash) => cash.brokerKey === broker.key)}
        {@const routes = broker.funding.filter((item) => item.enabled)}
        <section class="{CARD} space-y-4" data-testid={testId('broker', profile)} data-broker-key={broker.key} data-origin={broker.origin}>
            <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex min-w-0 items-center gap-2">
                    <PlannerBrokerIcon {broker} />
                    <h3 class="truncate font-semibold text-lf-primary">{broker.name || '—'}</h3>
                    {#if !broker.active}<span class={BADGE.warning} data-testid={testId('broker-inactive', profile)}>{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>{/if}
                </div>
                <div class="flex shrink-0 flex-wrap gap-2">
                    <button type="button" class={BUTTON_SECONDARY} data-testid={testId('broker-edit', profile)} onclick={() => (editing = broker.key)}>
                        <Pencil class="h-4 w-4" aria-hidden="true" />{$t('common.edit', {default: 'Edit'})}
                    </button>
                    <button type="button" class={BUTTON_DANGER} data-testid={testId('broker-remove', profile)} onclick={() => askRemove(broker)}>
                        <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
                    </button>
                </div>
            </div>

            {#if broker.modes.length === 0}
                <p class="text-sm text-lf-danger">{$t('tools.pacAllocator.planner.problems.brokerNoMode', {default: 'The Broker has no order mode.'})}</p>
            {:else}
                <div class="space-y-3">
                    {#each broker.modes as mode (mode.key)}
                        <div class="rounded-lg border border-lf-subtle p-3" data-testid={testId('broker-mode', profile)} data-currency={mode.currency}>
                            <p class="mb-2 text-sm font-semibold text-lf-primary"><CurrencyCode code={mode.currency} /></p>
                            <dl class="grid grid-cols-[auto_minmax(0,1fr)] items-baseline gap-x-3 gap-y-1.5 text-sm">
                                <dt class="flex items-center gap-0.5 text-lf-muted">
                                    {$t('tools.pacAllocator.planner.brokerEditor.kind', {default: 'Order type'})}
                                    <HelpTip
                                        label={$t('tools.pacAllocator.planner.brokerEditor.kind', {default: 'Order type'})}
                                        help={$t('tools.pacAllocator.planner.brokers.orderKindHelp', {default: 'How you enter an order at this Broker: by number of units (you buy 3 units) or by amount (you invest 150). It sets the unit of the increment and of the limits on each order.'})}
                                    />
                                </dt>
                                <dd class="text-lf-primary" data-testid={testId('broker-mode-kind', profile)}>{modeKindText($t, mode.kind)}</dd>
                                <dt class="flex items-center gap-0.5 text-lf-muted">
                                    {$t('tools.pacAllocator.planner.brokerEditor.step', {default: 'Increment'})}
                                    <HelpTip
                                        label={$t('tools.pacAllocator.planner.brokerEditor.step', {default: 'Increment'})}
                                        help={$t('tools.pacAllocator.planner.brokers.incrementHelp', {
                                            default: 'Every proposed order is a multiple of this value. By number of units: a whole number, for example 1. By amount: the smallest amount you can enter, for example 0.01; this is how you buy fractions of a unit.',
                                        })}
                                    />
                                </dt>
                                <dd class="tabular-nums text-lf-primary" data-testid={testId('broker-mode-step', profile)}>{modeIncrementText($t, mode)}</dd>
                                <dt class="flex items-center gap-0.5 text-lf-muted">
                                    {$t('tools.pacAllocator.planner.brokerEditor.fee', {default: 'Purchase fee'})}
                                    <HelpTip
                                        label={$t('tools.pacAllocator.planner.brokerEditor.fee', {default: 'Purchase fee'})}
                                        help={$t('tools.pacAllocator.planner.brokers.feeHelp', {
                                            default:
                                                'What the Broker charges on each purchase: the percentage of the amount, kept between minimum and maximum, plus the fixed part. No purchase, no fee. It is paid from your liquidity and is not invested.\n\nExamples, in the currency of the purchase:\n• 0.19%, minimum 1.50, maximum 18: on 500 you pay 1.50, on 2,000 you pay 3.80, on 20,000 you pay 18.\n• Only a fixed part of 2.95: 2.95 on any purchase.\n• Fixed part 1 plus 0.10%: on 1,000 you pay 2.\n• Everything at 0: no fee.',
                                        })}
                                    />
                                </dt>
                                <dd class="tabular-nums text-lf-primary" data-testid={testId('broker-mode-fee', profile)}>{modeFeeText($t, mode)}</dd>
                            </dl>
                        </div>
                    {/each}
                </div>
            {/if}

            <div class="space-y-1">
                <p class={LABEL_ROW}>
                    {$t('tools.pacAllocator.planner.brokers.conversionLabel', {default: 'Currency conversion'})}
                    <HelpTip
                        label={$t('tools.pacAllocator.planner.brokers.conversionLabel', {default: 'Currency conversion'})}
                        help={$t('tools.pacAllocator.planner.brokers.conversionHelp', {
                            default:
                                'When a purchase needs a currency you do not hold here, money is converted at the rate and spread of the FX step. If you convert yourself, the plan gives the conversion as a numbered step before the orders; if the Broker converts when you buy, the plan shows it next to its orders. The calculation is the same either way.',
                        })}
                    />
                </p>
                <p class="text-sm text-lf-primary" data-testid={testId('broker-conversion', profile)} data-mode={broker.conversionMode}>
                    {broker.conversionMode === 'automatic'
                        ? $t('tools.pacAllocator.planner.brokers.conversionValueAuto', {default: 'The Broker converts when you buy, at the rate of the FX step minus the spread.'})
                        : $t('tools.pacAllocator.planner.brokers.conversionValue', {default: 'You convert before buying, at the rate of the FX step minus the spread.'})}
                </p>
            </div>

            {#if profile.fundingRoutes}
                <div class="space-y-1.5" data-testid={testId('broker-funding', profile)}>
                    <p class={LABEL_ROW}>
                        {$t('tools.pacAllocator.planner.brokers.fundingLabel', {default: 'Usable liquidity'})}
                        <HelpTip
                            label={$t('tools.pacAllocator.planner.brokers.fundingLabel', {default: 'Usable liquidity'})}
                            help={$t('tools.pacAllocator.planner.brokers.fundingHelp', {
                                default: 'The money the plan may use to buy on this Broker: its own cash, plus the contributions and the cash of other accounts you allow in Edit. Everything is allowed at first; in Edit, click a source to exclude it.',
                            })}
                        />
                    </p>
                    {#if localCash.length === 0 && routes.length === 0}
                        <p class="text-sm text-lf-muted">{$t('tools.pacAllocator.planner.brokers.noFunding', {default: 'none yet'})}</p>
                    {:else}
                        <ul class="flex flex-wrap gap-1.5">
                            {#each localCash as cash (cash.key)}
                                <li data-testid={testId('broker-funding-local', profile)} data-currency={cash.currency}>
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
                                <li data-testid={testId('broker-funding-route', profile)} data-source-kind={item.source.kind}>
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
            {/if}
        </section>
    {/each}

    {#each draft.fundingOnlyBrokers as broker (broker.key)}
        <!-- The PAC's account funds other Brokers through routes; the Rebalancer's is an account with its cash (no routes). -->
        <section class="{CARD} space-y-1" data-testid={testId('broker-funding-only', profile)} data-broker-key={broker.key} data-kind={profile.fundingRoutes ? 'funding-only' : 'cash-only'}>
            <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="flex min-w-0 items-center gap-2">
                    <PlannerBrokerIcon {broker} />
                    <h3 class="truncate font-semibold text-lf-primary">{broker.name || '—'}</h3>
                </div>
                <div class="flex gap-1">
                    <OriginBadge origin={broker.origin} testid={testId('broker-origin', profile)} />
                    <span class={BADGE.neutral}>{profile.fundingRoutes ? $t('tools.pacAllocator.planner.brokers.fundingOnly', {default: 'funding only'}) : $t('tools.portfolioRebalancer.planner.brokers.cashOnly')}</span>
                </div>
            </div>
            <p class={HINT}>
                {profile.fundingRoutes ? $t('tools.pacAllocator.planner.brokers.fundingOnlyHint', {default: 'No order: it funds other Brokers through routes. Edit it in the Liquidity step.'}) : $t('tools.portfolioRebalancer.planner.brokers.cashOnlyHint')}
            </p>
        </section>
    {/each}

    {#each draft.positionOnlyBrokers as item (item.brokerKey)}
        <section class="{CARD} space-y-1" data-testid={testId('broker-positions-only', profile)} data-broker-key={item.brokerKey}>
            <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="flex min-w-0 items-center gap-2">
                    <BrokerIcon brokerId={item.sourceBrokerId} iconUrl={item.iconUrl} altText="" size={28} />
                    <h3 class="truncate font-semibold text-lf-primary">{item.name || '—'}</h3>
                </div>
                <div class="flex flex-wrap items-center gap-1">
                    <span class={BADGE.neutral}>{$t('tools.portfolioRebalancer.planner.brokers.positionsOnly')}</span>
                    <button type="button" class={BUTTON_SECONDARY} disabled={copyDisabled || addingBroker !== null} data-testid={testId('broker-positions-only-add', profile)} onclick={() => addToPlan(item)}>
                        <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.portfolioRebalancer.planner.brokers.addToPlan')}
                    </button>
                </div>
            </div>
            <p class={HINT}>{$t('tools.portfolioRebalancer.planner.brokers.positionsOnlyHint')}</p>
            {#if addFailed === item.brokerKey}
                <p class="text-sm text-lf-danger" role="alert" data-testid={testId('broker-positions-only-error', profile)}>{$t('tools.portfolioRebalancer.planner.brokers.addToPlanFailed')}</p>
            {/if}
        </section>
    {/each}

    {#if draft.operativeBrokers.length === 0}
        <p class={NOTICE.info} data-testid={testId('brokers-empty', profile)}>{$t('tools.pacAllocator.planner.problems.noOperativeBroker', {default: 'Add at least one Broker on which orders can be proposed.'})}</p>
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
    testId={testId('broker-removal', profile)}
    onConfirm={confirmRemoval}
    onCancel={() => (removal = null)}
/>
