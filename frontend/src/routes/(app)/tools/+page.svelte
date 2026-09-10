<script lang="ts">
    import {t} from '$lib/i18n';
    import ToolsHub from '$lib/features/tools/ToolsHub.svelte';
</script>

<svelte:head>
    <title>{$t('tools.title', {default: 'Tools'})} · LibreFolio</title>
</svelte:head>

<ToolsHub />
