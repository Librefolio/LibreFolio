<!--
  An Asset's positions, Broker by Broker (F3a of project 67, the Rebalancer, mockup screen 9): the project's `DataTable`,
  under the Asset's card. The quantity is the user's to change (`PositionQuantityCell`); the units in custody and the
  user's share of a shared account are facts of the copy. Quantities are personal: masked in privacy mode
  (`formatPlannerQuantity`), the quantity field included (it shows the masked quantity until privacy is off). The average purchase price and the columns that need prices come with F3b and F4a.
-->
<script lang="ts">
    import {MediaQuery} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {compareDecimal, fractionToPercent} from '$lib/utils/core/exactDecimal';
    import type {DraftPosition, PlannerDraft} from '../draft.svelte';
    import {formatPlannerPercentUnits, formatPlannerQuantity} from '../format';
    import HelpTip from '../shared/HelpTip.svelte';
    import PositionQuantityCell from '../shared/PositionQuantityCell.svelte';
    import {withHelpCues} from '../shared/columnHelp';
    import {getPlannerProfile, storageKey, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile. */
    const profile = getPlannerProfile();
    const KEY = 'tools.portfolioRebalancer.planner.positions';

    interface Props {
        draft: PlannerDraft;
        assetKey: string;
        assetLabel: string;
    }

    let {draft, assetKey, assetLabel}: Props = $props();

    const phone = new MediaQuery('max-width: 768px');
    const positions = $derived(draft.positionsOf(assetKey));

    function custodyText(position: DraftPosition): string {
        const custody = formatPlannerQuantity(position.custody);
        if (compareDecimal(position.ownershipShare, '1') !== -1) return custody;
        const share = formatPlannerPercentUnits(fractionToPercent(position.ownershipShare));
        return `${custody} · ${$t(`${KEY}.share`, {values: {share}})}`;
    }

    const columns = $derived.by((): ColumnDef<DraftPosition>[] =>
        withHelpCues<DraftPosition>([
            {
                id: 'broker',
                header: () => $t(`${KEY}.broker`),
                type: 'text',
                sortable: false,
                filterable: false,
                minWidth: phone.current ? 90 : 160,
                getValue: (position) => position.brokerName,
                cell: (position) => position.brokerName,
            },
            {
                id: 'quantity',
                header: () => $t(`${KEY}.quantity`),
                headerTooltip: () => $t(`${KEY}.quantityHelp`),
                type: 'custom',
                sortable: false,
                filterable: false,
                align: 'right',
                width: 220,
                minWidth: phone.current ? 150 : 200,
                cell: (position) => ({type: 'custom', component: PositionQuantityCell, props: {draft, positionKey: position.key, assetLabel}}),
            },
            {
                id: 'custody',
                header: () => $t(`${KEY}.custody`),
                headerTooltip: () => $t(`${KEY}.custodyHelp`),
                type: 'text',
                sortable: false,
                filterable: false,
                align: 'right',
                minWidth: 120,
                hiddenByDefault: phone.current,
                getValue: (position) => custodyText(position),
                cell: (position) => custodyText(position),
            },
        ]),
    );
</script>

{#if positions.length > 0}
    <div class="space-y-2 border-t border-lf-subtle pt-3" data-testid={testId('positions', profile)} data-asset-key={assetKey}>
        <div class="flex items-center gap-0.5">
            <h4 class="text-sm font-semibold text-lf-primary">{$t(`${KEY}.title`)}</h4>
            <HelpTip label={$t(`${KEY}.title`)} help={$t(`${KEY}.help`)} />
        </div>
        <DataTable
            data={positions}
            {columns}
            getRowId={(position) => position.key}
            storageKey={storageKey('positions', profile)}
            enableSorting={false}
            enablePagination={false}
            enableSelection={false}
            selectionMode="none"
            enableColumnVisibility={false}
            enableColumnFilters={false}
            enableActions={false}
            tableLayout="auto"
        />
    </div>
{/if}
