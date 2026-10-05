<script lang="ts">
    import {t} from '$lib/i18n';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import type {FundingSourceRef, PlannerDraft, RemovalImpact} from '../draft.svelte';

    interface Props {
        open: boolean;
        draft: PlannerDraft;
        title: string;
        message: string;
        impact: RemovalImpact | null;
        testId: string;
        onConfirm: () => void;
        onCancel: () => void;
    }

    let {open, draft, title, message, impact, testId, onConfirm, onCancel}: Props = $props();

    function sourceLabel(source: FundingSourceRef): string {
        if (source.kind === 'contribution') return draft.contribution(source.contributionKey)?.label || source.contributionKey;
        const cash = draft.cashRow(source.cashKey);
        return cash ? [draft.broker(cash.brokerKey)?.name ?? cash.brokerKey, cash.currency].join(' · ') : source.cashKey;
    }

    const items = $derived.by(() => {
        if (!impact) return [];
        const list: string[] = [];
        for (const route of impact.routes) {
            list.push(
                $t('tools.pacAllocator.planner.removal.route', {
                    default: 'Order route {asset} · {broker}',
                    values: {asset: draft.asset(route.assetKey)?.name ?? route.assetKey, broker: draft.broker(route.brokerKey)?.name ?? route.brokerKey},
                }),
            );
        }
        for (const cash of impact.cash) {
            list.push($t('tools.pacAllocator.planner.removal.cash', {default: 'Cash row {broker} · {currency}', values: {broker: draft.broker(cash.brokerKey)?.name ?? cash.brokerKey, currency: cash.currency}}));
        }
        for (const item of impact.funding) {
            list.push($t('tools.pacAllocator.planner.removal.funding', {default: 'Funding route {source} → {broker}', values: {source: sourceLabel(item.funding.source), broker: item.broker.name}}));
        }
        if (impact.target) list.push($t('tools.pacAllocator.planner.removal.target', {default: 'Its target percentage'}));
        return list;
    });
</script>

<ConfirmModal
    {open}
    {title}
    {message}
    {items}
    itemsLabel={$t('tools.pacAllocator.planner.removal.itemsLabel', {default: 'Also removed from the draft'})}
    confirmText={$t('common.remove', {default: 'Remove'})}
    cancelText={$t('common.cancel', {default: 'Cancel'})}
    danger
    zIndex={70}
    {testId}
    {onConfirm}
    {onCancel}
/>
