<script lang="ts">
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import {INPUT, INPUT_ADORNMENT} from '../ui';

    interface Props {
        draft: PlannerDraft;
        assetKey: string;
        label: string;
    }

    let {draft, assetKey, label}: Props = $props();
</script>

<div class="relative ml-auto w-28" data-testid="pac-planner-target" data-asset-key={assetKey}>
    <ExactDecimalInput value={draft.data.targets[assetKey] ?? ''} step="1" max="100" ariaLabel={label} className="{INPUT} pr-7 text-right" testid="pac-planner-target-input" onchange={(value) => (draft.data.targets[assetKey] = value)} />
    <span class={INPUT_ADORNMENT} aria-hidden="true">%</span>
</div>
