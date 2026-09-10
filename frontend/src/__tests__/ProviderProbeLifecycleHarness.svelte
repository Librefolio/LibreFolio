<!--
  Test-only owner for the real provider section. Bindings and conditional
  mounting model a parent panel; all probe lifecycle rules stay in the product
  controller. No status/result mirrors or replacement business logic.
-->
<script lang="ts">
    import {onDestroy, type ComponentProps} from 'svelte';
    import ProviderAssignmentSection from '$lib/components/assets/ProviderAssignmentSection.svelte';
    import {createProviderProbeState} from '$lib/components/assets/providerProbeState.svelte';

    type Props = Pick<ComponentProps<typeof ProviderAssignmentSection>, 'providerCode' | 'identifier' | 'identifierType' | 'providerParams' | 'providerUrl' | 'noProvider' | 'onchange'> & {shared?: boolean};

    let {providerCode = $bindable(''), identifier = $bindable(''), identifierType = $bindable('TICKER'), providerParams = $bindable(null), providerUrl = $bindable(null), noProvider = $bindable(false), onchange, shared = true}: Props = $props();
    let mounted = $state(true);
    const probeState = createProviderProbeState(() => ({
        providerCode,
        identifier,
        identifierType,
        providerParams,
        noProvider,
    }));

    onDestroy(() => probeState.dispose());
</script>

<button type="button" data-testid="provider-probe-collapse" disabled={!mounted} onclick={() => (mounted = false)}>Collapse</button>
<button type="button" data-testid="provider-probe-expand" disabled={mounted} onclick={() => (mounted = true)}>Expand</button>
<output data-testid="provider-probe-bound-url">{providerUrl ?? ''}</output>
<button
    type="button"
    data-testid="provider-probe-auto"
    disabled={!shared}
    onclick={() => {
        void probeState.run('auto');
    }}
>
    Probe automatically
</button>

{#if mounted}
    <ProviderAssignmentSection bind:providerCode bind:identifier bind:identifierType bind:providerParams bind:providerUrl bind:noProvider probeState={shared ? probeState : undefined} {onchange} />
{/if}
