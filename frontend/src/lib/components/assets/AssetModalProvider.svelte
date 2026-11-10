<!--
  AssetModalProvider — the provider assignment of the asset in AssetModal: a collapsible header with the test status
  and the "No provider" switch, and the assignment form (ProviderAssignmentSection). The provider fields are bound to
  the modal; every change asks the modal to reconcile its provider context.
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ChevronDown, ChevronRight, Loader2, Minus} from 'lucide-svelte';
    import ProviderAssignmentSection from './ProviderAssignmentSection.svelte';
    import type {ProviderProbeState, ProviderTestStatus} from './providerProbeState.svelte';

    interface Props {
        /** The assignment form is open. */
        expanded: boolean;
        noProvider: boolean;
        providerCode: string;
        identifier: string;
        identifierType: string;
        providerParams: Record<string, any> | null;
        providerUrl: string | null;
        probeState: ProviderProbeState;
        testStatus: ProviderTestStatus;
        saving: boolean;
        /** The provider configuration changed. */
        onreconcile: () => void;
    }

    let {expanded = $bindable(), noProvider = $bindable(), providerCode = $bindable(), identifier = $bindable(), identifierType = $bindable(), providerParams = $bindable(), providerUrl, probeState, testStatus, saving, onreconcile}: Props = $props();
</script>

<!-- Provider Assignment (collapsible) -->
<div class="border border-lf-subtle rounded-lg">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        data-testid="asset-modal-provider-header"
        data-expanded={expanded}
        class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-lf-secondary bg-lf-panel transition-colors select-none {noProvider ? '' : 'hover:bg-lf-neutral cursor-pointer'}"
        role="button"
        tabindex="0"
        onclick={() => {
            if (!noProvider) expanded = !expanded;
        }}
        onkeydown={(e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !noProvider) {
                e.preventDefault();
                expanded = !expanded;
            }
        }}
    >
        <div class="flex items-center gap-2" data-testid="asset-modal-provider-status" data-status={testStatus}>
            {#if !noProvider}
                {#if expanded}
                    <ChevronDown size={16} />
                {:else}
                    <ChevronRight size={16} />
                {/if}
            {:else}
                <Minus size={16} class="text-lf-muted" />
            {/if}
            <span>{$t('assets.provider.assignment')}</span>
            {#if testStatus === 'passed'}
                <span class="text-lf-success text-xs ml-1">✅</span>
            {:else if testStatus === 'failed'}
                <span class="text-lf-danger text-xs ml-1">❌</span>
            {:else if testStatus === 'testing'}
                <Loader2 size={12} class="animate-spin text-lf-muted ml-1" />
            {/if}
        </div>
        <!-- No Provider checkbox in header -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="flex items-center gap-1.5 text-xs text-lf-muted cursor-pointer" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
            <input
                type="checkbox"
                id="no-provider-checkbox"
                data-testid="asset-modal-no-provider"
                checked={noProvider}
                onchange={() => {
                    noProvider = !noProvider;
                    if (noProvider) {
                        expanded = false;
                    }
                    onreconcile();
                }}
                class="rounded border-lf-input text-lf-link focus:ring-lf-focus/50"
            />
            <label for="no-provider-checkbox">{$t('assets.provider.noProvider')}</label>
        </div>
    </div>

    {#if expanded && !noProvider}
        <div class="px-4 py-3 border-t border-lf-subtle">
            <ProviderAssignmentSection bind:providerCode bind:identifier bind:identifierType bind:providerParams {providerUrl} {probeState} bind:noProvider onchange={onreconcile} disabled={saving} />
        </div>
    {/if}
</div>
