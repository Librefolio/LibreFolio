<script lang="ts">
    import {t} from '$lib/i18n';
    import type {ScopeBroker} from '../scope';
    import {HINT} from '../ui';
    import BrokerTile from './BrokerTile.svelte';

    interface Props {
        scope: readonly ScopeBroker[];
        selected: number[];
        testid: string;
        disabled?: boolean;
        onchange?: (selected: number[]) => void;
    }

    let {scope, selected = $bindable(), testid, disabled = false, onchange}: Props = $props();

    function toggle(id: number, pressed: boolean): void {
        selected = pressed ? [...selected, id] : selected.filter((item) => item !== id);
        onchange?.(selected);
    }
</script>

<ul class="grid grid-cols-2 gap-2 sm:grid-cols-3" data-testid={testid}>
    {#each scope as broker (broker.id)}
        <li data-testid="{testid}-broker" data-broker-id={broker.id} data-selectable={broker.selectable ? 'true' : 'false'}>
            <BrokerTile {broker} pressed={selected.includes(broker.id)} {disabled} {testid} ontoggle={(next) => toggle(broker.id, next)} />
        </li>
    {:else}
        <li class="col-span-full {HINT}" data-testid="{testid}-empty">{$t('tools.pacAllocator.planner.scope.none', {default: 'No Broker you can read.'})}</li>
    {/each}
</ul>
