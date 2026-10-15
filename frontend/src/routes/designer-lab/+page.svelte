<script lang="ts">
    import {onMount, type Component} from 'svelte';

    // The page is a shell: the Lab is a separate chunk, imported only in debug builds (a release build drops the
    // branch, and +page.ts answers 404 before this component is reached).
    let Lab = $state<Component | null>(null);

    onMount(() => {
        if (__LF_DESIGNER_LAB__) import('$lib/dev/designer-lab/DesignerLab.svelte').then((m) => (Lab = m.default));
    });
</script>

{#if Lab}
    <Lab />
{/if}
