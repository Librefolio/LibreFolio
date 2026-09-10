<script lang="ts">
    import {page} from '$app/state';
    import {t} from '$lib/i18n';
    import ToolHost from '$lib/features/tools/ToolHost.svelte';

    const toolCode = $derived(page.params.tool_code ?? '');
</script>

<svelte:head>
    <title>{$t('tools.title', {default: 'Tools'})} · LibreFolio</title>
</svelte:head>

<ToolHost {toolCode} />
