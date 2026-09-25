<script lang="ts">
    import {Pencil, Plus, Trash2} from 'lucide-svelte';
    import {t, locale} from '$lib/i18n';
    import {CopyFlow} from '../copyFlow.svelte';
    import {decimalSign} from '../decimal';
    import type {DraftBroker, DraftMode, FundingSourceRef, PlannerDraft, RemovalImpact} from '../draft.svelte';
    import {formatPlannerPlainDecimal, formatPlannerPricePlain, formatPlannerTimestamp} from '../format';
    import {MODE_KIND_FALLBACKS} from '../labels';
    import {BADGE, BUTTON_DANGER, BUTTON_SECONDARY, CARD, HINT, NOTICE} from '../ui';
    import CopyFlowView from '../shared/CopyFlowView.svelte';
    import OriginBadge from '../shared/OriginBadge.svelte';
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

    function modeStep(mode: DraftMode): string {
        return mode.kind === 'whole_quantity'
            ? $t('tools.pacAllocator.planner.brokers.stepUnits', {default: 'step {step} units', values: {step: formatPlannerPlainDecimal(mode.step)}})
            : $t('tools.pacAllocator.planner.brokers.stepAmount', {default: 'step {step}', values: {step: formatPlannerPricePlain(mode.step, mode.currency)}});
    }

    function modeFee(mode: DraftMode): string {
        const zero = (value: string) => decimalSign(value.trim() || '0') === 0;
        if (zero(mode.fixedFee) && zero(mode.ratePercent) && zero(mode.floor) && mode.cap.trim() === '') {
            return $t('tools.pacAllocator.planner.brokers.feeZero', {default: 'BUY fee 0'});
        }
        return $t('tools.pacAllocator.planner.brokers.fee', {
            default: 'BUY fee {fixed} + {rate}% · min {floor} · max {cap}',
            values: {
                fixed: formatPlannerPricePlain(mode.fixedFee, mode.currency),
                rate: formatPlannerPlainDecimal(mode.ratePercent),
                floor: formatPlannerPricePlain(mode.floor, mode.currency),
                cap: mode.cap.trim() === '' ? '—' : formatPlannerPricePlain(mode.cap, mode.currency),
            },
        });
    }

    function sourceLabel(source: FundingSourceRef): string {
        if (source.kind === 'contribution') return draft.contribution(source.contributionKey)?.label || source.contributionKey;
        const cash = draft.cashRow(source.cashKey);
        return cash ? [draft.broker(cash.brokerKey)?.name ?? cash.brokerKey, cash.currency].join(' ') : source.cashKey;
    }

    function fundingText(broker: DraftBroker): string {
        const local = draft.data.cash.filter((cash) => cash.brokerKey === broker.key).map((cash) => $t('tools.pacAllocator.planner.brokers.localCash', {default: 'local cash {currency}', values: {currency: cash.currency}}));
        const routes = broker.funding.filter((item) => item.enabled).map((item) => sourceLabel(item.source));
        const all = [...local, ...routes];
        return all.length === 0 ? $t('tools.pacAllocator.planner.brokers.noFunding', {default: 'none yet'}) : all.join(' + ');
    }

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

    <CopyFlowView {flow} {draft} testid="pac-planner-brokers-notice" />

    {#each draft.operativeBrokers as broker (broker.key)}
        <section class="{CARD} space-y-2" data-testid="pac-planner-broker" data-broker-key={broker.key} data-origin={broker.origin}>
            <div class="flex flex-wrap items-start justify-between gap-2">
                <h3 class="font-semibold text-gray-900 dark:text-gray-100">{broker.name || '—'}</h3>
                <div class="flex flex-wrap gap-1">
                    {#if !broker.active}<span class={BADGE.warning} data-testid="pac-planner-broker-inactive">{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>{/if}
                    <OriginBadge origin={broker.origin} when={broker.origin === 'copied' ? formatPlannerTimestamp(draft.copyRecord(broker.stamp)?.capturedAt, $locale) : null} testid="pac-planner-broker-origin" />
                </div>
            </div>
            <ul class="space-y-1 text-sm">
                {#each broker.modes as mode (mode.key)}
                    <li data-testid="pac-planner-broker-mode" data-currency={mode.currency}>
                        <span class="font-medium">{mode.currency}:</span>
                        {$t(`tools.pacAllocator.planner.modeKinds.${mode.kind}`, {default: MODE_KIND_FALLBACKS[mode.kind]})} · {modeStep(mode)} · {modeFee(mode)}
                    </li>
                {:else}
                    <li class="text-red-700 dark:text-red-300">{$t('tools.pacAllocator.planner.problems.brokerNoMode', {default: 'The Broker has no order mode.'})}</li>
                {/each}
            </ul>
            <p class={HINT}>{$t('tools.pacAllocator.planner.brokers.conversions', {default: 'Conversions: global rate + spread (FX step)'})}</p>
            <p class="text-sm" data-testid="pac-planner-broker-funding">{$t('tools.pacAllocator.planner.brokers.funding', {default: 'Funding: {sources}', values: {sources: fundingText(broker)}})}</p>
            <div class="flex flex-wrap gap-2">
                <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-broker-edit" onclick={() => (editing = broker.key)}>
                    <Pencil class="h-4 w-4" aria-hidden="true" />{$t('common.edit', {default: 'Edit'})}
                </button>
                <button type="button" class={BUTTON_DANGER} data-testid="pac-planner-broker-remove" onclick={() => askRemove(broker)}>
                    <Trash2 class="h-4 w-4" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
                </button>
            </div>
        </section>
    {/each}

    {#each draft.fundingOnlyBrokers as broker (broker.key)}
        <section class="{CARD} space-y-1" data-testid="pac-planner-broker-funding-only" data-broker-key={broker.key}>
            <div class="flex flex-wrap items-start justify-between gap-2">
                <h3 class="font-semibold text-gray-900 dark:text-gray-100">{broker.name || '—'}</h3>
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
