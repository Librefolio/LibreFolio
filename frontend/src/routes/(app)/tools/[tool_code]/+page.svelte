<script lang="ts">
    import {page} from '$app/state';
    import ToolHost from '$lib/features/tools/ToolHost.svelte';

    const toolCode = $derived(page.params.tool_code ?? '');
</script>

<ToolHost {toolCode} />
