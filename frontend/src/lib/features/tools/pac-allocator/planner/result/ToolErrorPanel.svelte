<script lang="ts">
    import {CircleX} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {toolErrorMessage} from '$lib/features/tools/presentation';
    import {clientErrorRetryable, presentToolError} from '../issues';
    import type {RunOutcome} from '../run.svelte';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, NOTICE} from '../ui';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        outcome: Extract<RunOutcome, {kind: 'tool_error' | 'client_error'}>;
        disabled: boolean;
        onretry: () => void;
        onedit: () => void;
    }

    let {outcome, disabled, onretry, onedit}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.platform';
    const message = $derived.by(() => {
        if (outcome.kind === 'tool_error') {
            const presented = presentToolError(outcome.error);
            return {code: presented.code, key: presented.messageKey, fallback: presented.fallback, retryable: presented.retryable};
        }
        const presented = toolErrorMessage(outcome.error);
        return {code: outcome.error.code, key: presented.key, fallback: presented.fallback, retryable: clientErrorRetryable(outcome.error)};
    });
    // Only `execution_failed` leaves a line in the server log (the plugin writes it), and that line carries this id.
    const reference = $derived(outcome.kind === 'tool_error' && outcome.error.code === 'execution_failed' ? outcome.executionId : null);
</script>

<div class="{NOTICE.danger} space-y-3" role="alert" data-testid="pac-planner-platform-error" data-kind={outcome.kind} data-code={message.code} data-retryable={message.retryable ? 'true' : 'false'}>
    <p class="flex items-center gap-2 font-semibold">
        <CircleX size={18} aria-hidden="true" />
        {$t(`${KEY}.title`, {default: 'Calculation failed'})}
    </p>
    <p>
        <code class="rounded bg-white/60 px-1 text-xs dark:bg-black/30">{message.code}</code>
        · {$t(message.key, {default: message.fallback, values: {code: message.code}})}
    </p>
    {#if reference}
        <p class={HINT} data-testid="pac-planner-platform-reference">
            {$t(`${KEY}.reference`, {default: 'Reference in the server log:'})}
            <code class="break-all rounded bg-white/60 px-1 text-xs dark:bg-black/30">{reference}</code>
        </p>
    {/if}
    <div class="flex flex-wrap gap-2">
        {#if message.retryable}
            <button type="button" class={BUTTON_PRIMARY} data-testid="pac-planner-platform-retry" {disabled} onclick={onretry}>{$t(`${KEY}.retry`, {default: 'Retry'})}</button>
        {/if}
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-platform-edit" {disabled} onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
    </div>
    <p class={HINT}>{$t(`${KEY}.draftIntact`, {default: 'The draft is intact.'})}</p>
</div>
