<script lang="ts">
    /**
     * ServerUnreachable — what a full load of an app page shows when the server has not said who is
     * signed in: slow (past the layout's wait), down, or answering 5xx. It is not a sign-out: the URL
     * stays the one asked for, and Retry runs the check again. Only a 401 leads to the login.
     */
    import {_} from '$lib/i18n';
    import {ServerCrash} from 'lucide-svelte';
    import Button from '$lib/components/ui/button/Button.svelte';

    interface Props {
        /** A check is in flight: Retry would only overtake it. */
        busy: boolean;
        onretry: () => void;
    }

    let {busy, onretry}: Props = $props();
</script>

<div class="min-h-screen flex items-center justify-center bg-lf-page text-lf-primary p-4" role="alert" data-testid="server-unreachable" data-busy={busy ? 'true' : 'false'}>
    <div class="max-w-md text-center space-y-4">
        <ServerCrash size={40} class="mx-auto text-lf-link" aria-hidden="true" />
        <h1 class="text-xl font-semibold text-lf-primary">{$_('auth.serverUnreachable.title')}</h1>
        <p class="text-sm text-lf-secondary">{$_('auth.serverUnreachable.body')}</p>
        <!-- Busy while a check is in flight: it keeps the focus and turns, and a second Retry never overtakes it (85). -->
        <Button label={$_('common.retry')} variant="primary" {busy} onclick={onretry} data-testid="server-unreachable-retry" />
    </div>
</div>
