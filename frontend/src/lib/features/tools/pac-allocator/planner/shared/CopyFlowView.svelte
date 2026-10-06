<script lang="ts">
    import type {CopyFlow} from '../copyFlow.svelte';
    import type {PlannerDraft} from '../draft.svelte';
    import ConflictDialog from './ConflictDialog.svelte';
    import CopyNotice from './CopyNotice.svelte';

    interface Props {
        flow: CopyFlow;
        draft: PlannerDraft;
        testid: string;
        /** See `CopyNotice`: no banner for a copy that went well. */
        quiet?: boolean;
    }

    let {flow, draft, testid, quiet = false}: Props = $props();
</script>

{#if flow.notice}
    <CopyNotice outcome={flow.notice.outcome} source={flow.notice.source} {draft} {testid} {quiet} ondismiss={() => flow.dismiss()} />
{/if}
<ConflictDialog open={flow.pending !== null} {draft} copy={flow.pending?.copy ?? null} conflicts={flow.pending?.conflicts ?? []} onresolve={(choice) => flow.resolve(draft, choice)} />
