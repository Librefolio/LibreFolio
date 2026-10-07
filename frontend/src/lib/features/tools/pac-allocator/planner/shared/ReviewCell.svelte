<script lang="ts" module>
    import type {DraftAsset, DraftBroker} from '../draft.svelte';
    import type {SnapshotFact} from '../review';
    import type {PlannerStep} from '../types';

    /** R9.7: one cell of the two Review tables. The table picks the column, this component draws it. */
    export type ReviewCellContent =
        | {type: 'step'; step: PlannerStep; blocked: boolean}
        | {type: 'summary'; text: string; currencies: readonly string[]}
        | {type: 'kind'; label: string}
        | {type: 'entity'; fact: SnapshotFact; broker: DraftBroker | null; asset: DraftAsset | null}
        | {type: 'value'; fact: SnapshotFact}
        | {type: 'origin'; fact: SnapshotFact};
</script>

<script lang="ts">
    import {CircleAlert, CircleCheck, PiggyBank} from 'lucide-svelte';
    import {locale, t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {formatPlannerDate, formatPlannerFxRate, formatPlannerMoneyPlain, formatPlannerPlainDecimal, formatPlannerPricePlain, plannerPlainDecimalCount} from '../format';
    import {STEP_FALLBACKS, stepKey} from '../labels';
    import {factOriginState} from '../review';
    import {ICON_BUBBLE} from '../ui';
    import AssetNameCell from './AssetNameCell.svelte';
    import CurrencyCode from './CurrencyCode.svelte';
    import MarqueeName from './MarqueeName.svelte';
    import OriginBadge from './OriginBadge.svelte';
    import PlannerBrokerIcon from './PlannerBrokerIcon.svelte';

    interface Props {
        cell: ReviewCellContent;
    }

    let {cell}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.review';
</script>

{#if cell.type === 'step'}
    <span class="flex items-center gap-2 font-medium text-gray-900 dark:text-gray-100" data-testid="pac-planner-review-section" data-step={cell.step} data-blocked={cell.blocked ? 'true' : 'false'}>
        {#if cell.blocked}
            <CircleAlert class="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
        {:else}
            <CircleCheck class="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
        {/if}
        {$t(stepKey(cell.step), {default: STEP_FALLBACKS[cell.step]})}
    </span>
{:else if cell.type === 'summary'}
    <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-gray-700 dark:text-gray-300">
        {#if cell.text !== ''}<span>{cell.text}</span>{/if}
        {#each cell.currencies as code (code)}<CurrencyCode {code} />{/each}
    </span>
{:else if cell.type === 'kind'}
    <span>{cell.label}</span>
{:else if cell.type === 'entity'}
    {@const fact = cell.fact}
    {@const subject = fact.subject}
    <span class="flex min-w-0 items-center gap-2" data-testid="pac-planner-review-fact" data-kind={fact.kind} data-origin={factOriginState(fact)} data-stale={fact.stale ? 'true' : 'false'}>
        {#if subject.type === 'broker' || subject.type === 'cash'}
            <PlannerBrokerIcon broker={cell.broker} size={24} />
            <MarqueeName text={fact.entity} />
            {#if subject.type === 'cash'}<CurrencyCode code={subject.currency} />{/if}
        {:else if subject.type === 'contribution'}
            <span class={ICON_BUBBLE} style="width: 24px; height: 24px;"><PiggyBank class="h-3.5 w-3.5" aria-hidden="true" /></span>
            <MarqueeName text={fact.entity} />
            <CurrencyCode code={subject.currency} />
        {:else if subject.type === 'asset'}
            <AssetNameCell label={fact.entity} iconUrl={cell.asset?.iconUrl ?? null} assetType={cell.asset?.assetClass ? cell.asset.assetClass.toUpperCase() : null} />
        {:else}
            <span class="flex items-center gap-1.5 font-medium text-gray-900 dark:text-gray-100">
                <CurrencyCode code={subject.base} />
                <span class="text-gray-400 dark:text-gray-500" aria-hidden="true">→</span>
                <CurrencyCode code={subject.quote} />
            </span>
        {/if}
    </span>
{:else if cell.type === 'value'}
    {@const value = cell.fact.value}
    <span class="flex flex-wrap items-center gap-x-2 gap-y-1 tabular-nums text-gray-700 dark:text-gray-300">
        {#if value.kind === 'money'}
            {#if value.selected === null}
                {formatPlannerMoneyPlain(value.amount, value.currency)}
            {:else}
                {$t(`${KEY}.selectedOf`, {
                    default: '{selected} of {available}',
                    values: {selected: formatPlannerMoneyPlain(value.selected, value.currency), available: formatPlannerMoneyPlain(value.amount, value.currency)},
                })}
            {/if}
        {:else if value.kind === 'price'}
            {$t(`${KEY}.price`, {
                default: '{price} / {units} {count, plural, one {unit} other {units}}',
                values: {price: formatPlannerPricePlain(value.amount, value.currency), units: formatPlannerPlainDecimal(value.units), count: plannerPlainDecimalCount(value.units)},
            })}
        {:else if value.kind === 'rate'}
            {formatPlannerFxRate(value.rate)}
        {:else if value.fundingOnly}
            {$t(`${KEY}.externalAccount`, {default: 'External account'})}
        {:else if value.currencies.length > 0}
            <span>{$t(`${KEY}.ordersIn`, {default: 'Orders in'})}</span>
            {#each value.currencies as code (code)}<CurrencyCode {code} />{/each}
        {:else}
            <span aria-hidden="true">—</span>
        {/if}
    </span>
{:else}
    {@const fact = cell.fact}
    {@const originState = factOriginState(fact)}
    <span class="flex flex-wrap items-center gap-2 text-sm" data-origin={originState}>
        {#if originState === 'librefolio'}
            <span class="text-gray-600 dark:text-gray-300">{$t(`${KEY}.origin.librefolio`, {default: 'LibreFolio'})}</span>
            {#if fact.stale && fact.referenceDate}
                <Tooltip text={$t(`${KEY}.staleTitle`, {default: 'Not of today: the calculation uses the latest value LibreFolio has.'})} position="top" maxWidth="280px">
                    <span class="text-amber-600 dark:text-amber-400" data-testid="pac-planner-review-fact-stale">{formatPlannerDate(fact.referenceDate, $locale)}</span>
                </Tooltip>
            {/if}
        {:else if originState === 'manual'}
            <OriginBadge origin="manual" />
        {:else}
            <OriginBadge origin="copied" modified />
        {/if}
    </span>
{/if}
