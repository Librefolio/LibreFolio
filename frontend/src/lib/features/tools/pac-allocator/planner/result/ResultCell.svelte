<script lang="ts" module>
    import type {DraftAsset, DraftBroker} from '../draft.svelte';
    import type {CurrencyDigits} from '../format';
    import type {PacExactMoney, PacExactNumber, PacExactPrice, PacNumberAvailability, PacObjectiveUnit, PacOrderRow} from '../types';

    /**
     * R9.8: one cell of the result tables. The table picks the column, this component draws it,
     * so every amount is formatted inside a template and follows the privacy switch.
     */
    export type ResultCellContent =
        | {type: 'broker'; brokerId: string; label: string; broker: DraftBroker | null; currency?: string | null; testid?: string}
        | {type: 'contribution'; label: string; currency: string | null}
        | {type: 'asset'; assetId: string; label: string; asset: DraftAsset | null; sequence?: number; orderId?: string; testid?: string}
        | {type: 'weight'; value: PacExactNumber | PacNumberAvailability}
        | {type: 'bars'; target: PacExactNumber; final: PacNumberAvailability; scale: number}
        | {type: 'money'; amount: string | null; currency: string; digits: CurrencyDigits; signed?: boolean; testid?: string}
        | {type: 'exactMoney'; money: PacExactMoney; digits: CurrencyDigits; signed?: boolean; testid?: string}
        | {type: 'price'; price: PacExactPrice; digits: CurrencyDigits}
        | {type: 'instruction'; order: PacOrderRow; digits: CurrencyDigits; autoConversion?: boolean}
        | {type: 'label'; text: string; sequence?: number; testid?: string; attrs?: Record<string, string>}
        | {type: 'solver'; value: string | null; unit: PacObjectiveUnit; digits?: CurrencyDigits; testid?: string};
</script>

<script lang="ts">
    import {t} from '$lib/i18n';
    import {PiggyBank} from 'lucide-svelte';
    import AssetNameCell from '../shared/AssetNameCell.svelte';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import MarqueeName from '../shared/MarqueeName.svelte';
    import PlannerBrokerIcon from '../shared/PlannerBrokerIcon.svelte';
    import {formatExactMoneyPlain, formatExactPercent, formatPlannerMoneyPlain, formatSolverNumber} from '../format';
    import {BADGE, ICON_BUBBLE, STEP_NUMBER} from '../ui';
    import {UNAVAILABLE_FALLBACKS, weightWidth} from './model';
    import {instructionText, priceText} from './text';

    interface Props {
        cell: ResultCellContent;
    }

    let {cell}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result';
    const TRACK = 'block h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-slate-700';
</script>

{#if cell.type === 'broker'}
    <span class="flex min-w-0 items-center gap-2" data-testid={cell.testid} data-broker={cell.brokerId} data-currency={cell.currency ?? undefined}>
        <PlannerBrokerIcon broker={cell.broker} size={24} />
        <MarqueeName text={cell.label} />
        {#if cell.currency}<CurrencyCode code={cell.currency} />{/if}
    </span>
{:else if cell.type === 'contribution'}
    <span class="flex min-w-0 items-center gap-2">
        <span class={ICON_BUBBLE} style="width: 24px; height: 24px;"><PiggyBank class="h-3.5 w-3.5" aria-hidden="true" /></span>
        <MarqueeName text={cell.label} />
        {#if cell.currency}<CurrencyCode code={cell.currency} />{/if}
    </span>
{:else if cell.type === 'asset'}
    <span class="flex min-w-0 items-center gap-2" data-testid={cell.testid} data-asset={cell.assetId} data-order={cell.orderId}>
        {#if cell.sequence != null}<span class={STEP_NUMBER}>{cell.sequence}</span>{/if}
        <AssetNameCell label={cell.label} iconUrl={cell.asset?.iconUrl ?? null} assetType={cell.asset?.assetClass ? cell.asset.assetClass.toUpperCase() : null} />
    </span>
{:else if cell.type === 'weight'}
    {@const value = cell.value}
    <span class="tabular-nums">
        {#if value.kind === 'unavailable'}
            {@const reason = $t(`${KEY}.unavailable.${value.reason}`, {default: UNAVAILABLE_FALLBACKS[value.reason]})}
            <span title={reason}>—</span>
            <span class="sr-only">{reason}</span>
        {:else if value.kind === 'available'}
            {formatExactPercent(value.value)}
        {:else}
            {formatExactPercent(value)}
        {/if}
    </span>
{:else if cell.type === 'bars'}
    <span class="flex w-full min-w-24 flex-col gap-1" aria-hidden="true">
        <span class={TRACK}><span class="block h-full rounded-full bg-gray-400 dark:bg-gray-500" style="width: {weightWidth(cell.target, cell.scale)}"></span></span>
        <span class={TRACK}><span class="block h-full rounded-full bg-libre-green" style="width: {weightWidth(cell.final, cell.scale)}"></span></span>
    </span>
{:else if cell.type === 'money'}
    <span class="tabular-nums" data-testid={cell.testid}>{formatPlannerMoneyPlain(cell.amount, cell.currency, {digits: cell.digits, signed: cell.signed})}</span>
{:else if cell.type === 'exactMoney'}
    <span class="tabular-nums" data-testid={cell.testid}>{formatExactMoneyPlain(cell.money, {digits: cell.digits, signed: cell.signed})}</span>
{:else if cell.type === 'price'}
    <span class="tabular-nums">{priceText(cell.price, $t, cell.digits)}</span>
{:else if cell.type === 'instruction'}
    <span class="flex flex-wrap items-center gap-1.5">
        <span class="font-medium text-gray-900 dark:text-gray-100" data-testid="pac-planner-plan-instruction">{instructionText(cell.order, $t, cell.digits)}</span>
        {#if cell.autoConversion}<span class={BADGE.info} data-testid="pac-planner-plan-order-auto-conversion">{$t(`${KEY}.plan.autoConversion`, {default: 'Automatic conversion'})}</span>{/if}
    </span>
{:else if cell.type === 'label'}
    <span class="flex min-w-0 items-center gap-2" data-testid={cell.testid} {...cell.attrs ?? {}}>
        {#if cell.sequence != null}<span class={STEP_NUMBER}>{cell.sequence}</span>{/if}
        <MarqueeName text={cell.text} />
    </span>
{:else}
    <span class="tabular-nums" data-testid={cell.testid}>{formatSolverNumber(cell.value, cell.unit, cell.digits)}</span>
{/if}
