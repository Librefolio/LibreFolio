<!--
  AllocationDimensionSelect — the four things the allocation can be grouped by: Sector, Area, Type, Asset (lane 80, F3).
  Four buttons on a wide screen, one select on a phone (below `sm`); the same choice either way, and only one of the two is
  mounted, so the test ids exist once. Test ids: `{testId}` (the group), `{testId}-{dimension}` (a button: `aria-pressed`),
  `{testId}-select` (the phone's select, its options `{testId}-select-option-{dimension}`).
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {createMediaQuery} from './matchMedia.svelte';
    import type {AllocationDimension} from './allocationQuery';
    import {ALLOCATION_DIMENSIONS} from './allocationView';

    interface Props {
        value: AllocationDimension;
        onchange: (next: AllocationDimension) => void;
        testId: string;
    }

    let {value, onchange, testId}: Props = $props();

    const roomy = createMediaQuery('(min-width: 640px)');
    const options = $derived(ALLOCATION_DIMENSIONS.map((dimension) => ({value: dimension, label: $_(`allocation.dimension.${dimension}`)})));
</script>

{#if roomy.matches}
    <div class="inline-flex overflow-hidden rounded-lg border border-lf-subtle text-xs font-medium" role="group" aria-label={$_('allocation.dimension.label')} data-testid={testId}>
        {#each ALLOCATION_DIMENSIONS as dimension (dimension)}
            <button type="button" class="px-3 py-1.5 transition-colors {value === dimension ? 'bg-lf-action text-lf-on-action' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}" aria-pressed={value === dimension} onclick={() => onchange(dimension)} data-testid="{testId}-{dimension}">
                {$_(`allocation.dimension.${dimension}`)}
            </button>
        {/each}
    </div>
{:else}
    <div data-testid={testId}>
        <SimpleSelect {value} {options} compact={true} ariaLabel={$_('allocation.dimension.label')} testId="{testId}-select" optionTestId={(option) => `${testId}-select-option-${option.value}`} onchange={(next) => onchange(next as AllocationDimension)} />
    </div>
{/if}
