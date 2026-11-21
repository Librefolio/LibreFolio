<script lang="ts">
    import {CircleX, Copy} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import {toolErrorMessage} from '$lib/features/tools/presentation';
    import {clientErrorRetryable, presentToolError} from '../issues';
    import type {RunOutcome} from '../run.svelte';
    import {BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, NOTICE} from '../ui';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
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

    /**
     * R1-B of project 67: the request this run sent, as it was sent, to the clipboard, so a failure can be replayed. It
     * holds the user's amounts: it goes only to the clipboard, never to the server, a log or an event. The write starts
     * inside the click (the shared writer's rule); a refusal, at once or later, gets its toast.
     */
    function copyRequest(): void {
        const failed = () => toasts.error($t(`${KEY}.copyRequestFailed`, {default: 'Could not copy the request. Allow clipboard access and try again.'}));
        let written: Promise<void>;
        try {
            written = writeTextToClipboard(JSON.stringify(outcome.built.request, null, 2));
        } catch {
            failed();
            return;
        }
        written.then(() => toasts.success($t('common.copiedToClipboard', {default: 'Copied to clipboard'})), failed);
    }
</script>

<div class="{NOTICE.danger} space-y-3" role="alert" data-testid={testId('platform-error', profile)} data-kind={outcome.kind} data-code={message.code} data-retryable={message.retryable ? 'true' : 'false'}>
    <p class="flex items-center gap-2 font-semibold">
        <CircleX size={18} aria-hidden="true" />
        {$t(`${KEY}.title`, {default: 'Calculation failed'})}
    </p>
    <p>
        <code class="rounded bg-lf-card/60 px-1 text-xs">{message.code}</code>
        · {$t(message.key, {default: message.fallback, values: {code: message.code}})}
    </p>
    {#if reference}
        <p class={HINT} data-testid={testId('platform-reference', profile)}>
            {$t(`${KEY}.reference`, {default: 'Reference in the server log:'})}
            <code class="break-all rounded bg-lf-card/60 px-1 text-xs">{reference}</code>
        </p>
    {/if}
    <div class="flex flex-wrap gap-2">
        {#if message.retryable}
            <button type="button" class={BUTTON_PRIMARY} data-testid={testId('platform-retry', profile)} {disabled} onclick={onretry}>{$t(`${KEY}.retry`, {default: 'Retry'})}</button>
        {/if}
        <button type="button" class={BUTTON_SECONDARY} data-testid={testId('platform-edit', profile)} {disabled} onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
        <button
            type="button"
            class={BUTTON_SECONDARY}
            data-testid={testId('platform-copy-request', profile)}
            title={$t(`${KEY}.copyRequestHint`, {default: 'Copies the data sent for this calculation, amounts included, so you can attach it to a report. Nothing is kept on the server.'})}
            onclick={copyRequest}
        >
            <Copy size={14} aria-hidden="true" />
            {$t(`${KEY}.copyRequest`, {default: 'Copy the request'})}
        </button>
    </div>
    <p class={HINT}>{$t(`${KEY}.draftIntact`, {default: 'The draft is intact.'})}</p>
</div>
