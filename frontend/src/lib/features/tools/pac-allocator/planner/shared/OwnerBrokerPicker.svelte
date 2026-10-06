<script lang="ts">
    import {t} from '$lib/i18n';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import {compareDecimal} from '../decimal';
    import {formatPlannerPercent} from '../format';
    import type {ScopeBroker} from '../scope';
    import {BADGE, HINT} from '../ui';

    interface Props {
        scope: readonly ScopeBroker[];
        selected: number[];
        testid: string;
        disabled?: boolean;
        onchange?: (selected: number[]) => void;
    }

    let {scope, selected = $bindable(), testid, disabled = false, onchange}: Props = $props();

    function toggle(id: number, checked: boolean): void {
        selected = checked ? [...selected, id] : selected.filter((item) => item !== id);
        onchange?.(selected);
    }

    function partial(share: string | null): boolean {
        return share !== null && compareDecimal(share, '1') === -1;
    }
</script>

<ul class="space-y-1" data-testid={testid}>
    {#each scope as broker (broker.id)}
        <li class="flex flex-wrap items-center gap-2 text-sm" data-testid="{testid}-broker" data-broker-id={broker.id} data-selectable={broker.selectable ? 'true' : 'false'}>
            {#if broker.selectable}
                <label class="flex items-center gap-2">
                    <input type="checkbox" class="rounded border-gray-300 text-libre-green focus:ring-libre-green" checked={selected.includes(broker.id)} {disabled} data-testid="{testid}-check" onchange={(event) => toggle(broker.id, event.currentTarget.checked)} />
                    <BrokerIcon brokerId={broker.id} iconUrl={broker.iconUrl} portalUrl={broker.portalUrl} pluginCode={broker.pluginCode} altText="" size={20} />
                    <span class="font-medium text-gray-900 dark:text-gray-100">{broker.name}</span>
                </label>
                {#if partial(broker.share)}
                    <span class={HINT}>· {$t('tools.pacAllocator.planner.scope.share', {default: 'share {share}', values: {share: formatPlannerPercent(broker.share)}})}</span>
                {/if}
                {#if !broker.active}
                    <span class={BADGE.warning}>{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>
                {/if}
            {:else}
                <span class="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                    <input type="checkbox" class="rounded border-gray-300" disabled checked={false} aria-hidden="true" tabindex="-1" />
                    <span class="inline-flex opacity-60"><BrokerIcon brokerId={broker.id} iconUrl={broker.iconUrl} portalUrl={broker.portalUrl} pluginCode={broker.pluginCode} altText="" size={20} /></span>
                    <span>{broker.name}</span>
                </span>
                <span class={HINT} data-testid="{testid}-blocked">
                    {$t('tools.pacAllocator.planner.scope.notSelectable', {default: 'Not selectable: {role} access, not read', values: {role: broker.role ?? '—'}})}
                </span>
            {/if}
        </li>
    {:else}
        <li class={HINT} data-testid="{testid}-empty">{$t('tools.pacAllocator.planner.scope.none', {default: 'No Broker you can read.'})}</li>
    {/each}
</ul>
