<!--
  The gate of the root layout (H-62): while the instance awaits its restore (`mode: awaiting_restore` of
  `GET /system/instance`), the waiting page instead of every route, the login included; otherwise the routes.
-->
<script lang="ts">
    import {onMount, type Snippet} from 'svelte';
    import {instanceConfig} from '../instanceConfig.svelte';
    import InstanceAwaitingRestorePage from './InstanceAwaitingRestorePage.svelte';

    interface Props {
        /** The routes; optional, as the root layout is a legacy component that passes its `<slot />` (H-62). */
        children?: Snippet;
        /** Reads the instance's configuration; `instanceConfig.load()` by default. */
        loadConfig?: () => Promise<void>;
        /** The instance's mode; `instanceConfig.config.mode` by default (read loosely: an older server does not send it). */
        readMode?: () => string | undefined;
    }

    let {children, loadConfig = () => instanceConfig.load(), readMode = () => (instanceConfig.config as {mode?: string}).mode}: Props = $props();

    const awaitingRestore = $derived(readMode() === 'awaiting_restore');

    onMount(() => {
        void loadConfig();
    });
</script>

{#if awaitingRestore}
    <InstanceAwaitingRestorePage />
{:else}
    {@render children?.()}
{/if}
