<script lang="ts">
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import {INPUT, INPUT_ADORNMENT} from '../ui';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        draft: PlannerDraft;
        assetKey: string;
        label: string;
    }

    let {draft, assetKey, label}: Props = $props();
</script>

<div class="relative ml-auto w-28" data-testid={testId('target', profile)} data-asset-key={assetKey}>
    <ExactDecimalInput value={draft.data.targets[assetKey] ?? ''} step="1" max="100" ariaLabel={label} className="{INPUT} pr-7 text-right" testid={testId('target-input', profile)} onchange={(value) => (draft.data.targets[assetKey] = value)} />
    <span class={INPUT_ADORNMENT} aria-hidden="true">%</span>
</div>
