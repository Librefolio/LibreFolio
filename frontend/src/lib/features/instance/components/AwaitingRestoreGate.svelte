<!--
  The gate of the root layout (H-62): while the instance awaits its restore (`mode: awaiting_restore` of
  `GET /system/instance`), the waiting page instead of every route, the login included; while the state of its restore
  cannot be read or the owner of the restored data has no account yet (`restore_interrupted`, B-33 and H5-3), the page
  that asks for the administrator, which wins; otherwise the
  routes.
-->
<script lang="ts">
    import {onMount, type Snippet} from 'svelte';
    import {instanceConfig} from '../instanceConfig.svelte';
    import InstanceAwaitingRestorePage from './InstanceAwaitingRestorePage.svelte';
    import InstanceRestoreInterruptedPage from './InstanceRestoreInterruptedPage.svelte';

    type InterruptedReason = 'restore_state' | 'owner_assignment';

    /** The generated type of a nullable enum with a description also admits an array (the client generator's quirk, as for
     *  `support_url`); the response's validator accepts only one of the two reasons or null. */
    function configuredReason(): InterruptedReason | null {
        const configured = instanceConfig.config.restore_interrupted_reason;
        return configured === 'restore_state' || configured === 'owner_assignment' ? configured : null;
    }

    interface Props {
        /** The routes; optional, as the root layout is a legacy component that passes its `<slot />` (H-62). */
        children?: Snippet;
        /** Reads the instance's configuration; `instanceConfig.load()` by default. */
        loadConfig?: () => Promise<void>;
        /** The instance's mode; `instanceConfig.config.mode` by default (read loosely: an older server does not send it). */
        readMode?: () => string | undefined;
        /** Whether the instance serves no data (B-33); `instanceConfig.config.restore_interrupted` by default. */
        readRestoreInterrupted?: () => boolean;
        /** Why (H5-3); `instanceConfig.config.restore_interrupted_reason` by default. */
        readRestoreInterruptedReason?: () => InterruptedReason | null | undefined;
    }

    let {children, loadConfig = () => instanceConfig.load(), readMode = () => (instanceConfig.config as {mode?: string}).mode, readRestoreInterrupted = () => instanceConfig.config.restore_interrupted === true, readRestoreInterruptedReason = configuredReason}: Props = $props();

    const restoreInterrupted = $derived(readRestoreInterrupted() === true);
    const awaitingRestore = $derived(readMode() === 'awaiting_restore');

    onMount(() => {
        void loadConfig();
    });
</script>

{#if restoreInterrupted}
    <InstanceRestoreInterruptedPage reason={readRestoreInterruptedReason() ?? null} />
{:else if awaitingRestore}
    <InstanceAwaitingRestorePage />
{:else}
    {@render children?.()}
{/if}
