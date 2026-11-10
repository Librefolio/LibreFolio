<script lang="ts">
    /**
     * The page of a password-reset link, `/reset-password#token=…`.
     *
     * The token leaves the address bar at once; the server says what it is worth. A valid link opens the form for the
     * account it belongs to; once the new password is set every session of that account has ended, and the page sends
     * the user to the sign-in with a message.
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
    import AuthPageFrame from '$lib/features/auth/AuthPageFrame.svelte';
    import LinkStatusCard from '$lib/features/auth/LinkStatusCard.svelte';
    import ResetPasswordCard from '$lib/features/auth/ResetPasswordCard.svelte';
    import {replaceAddress} from '$lib/features/auth/addressBar';
    import {setAuthFlash} from '$lib/features/auth/authFlash';
    import {inspectLinkToken, takeLinkToken, type LinkPageStatus} from '$lib/features/auth/linkToken';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';

    let token = $state<string | null>(null);
    let status = $state<LinkPageStatus | 'form'>('checking');
    let username = $state<string | null>(null);

    async function check(): Promise<void> {
        if (!token) {
            status = 'missing';
            return;
        }
        status = 'checking';
        try {
            const inspection = await inspectLinkToken(token, 'password_reset');
            if (inspection.status !== 'valid') {
                status = inspection.status;
                return;
            }
            username = inspection.username ?? null;
            status = 'form';
        } catch {
            status = 'error';
        }
    }

    onMount(() => {
        // The password rules come from the server (decision 37); the meter follows them when they arrive, so the
        // form does not wait for this request.
        void instanceConfig.load();
        token = takeLinkToken(new URL(window.location.href), replaceAddress);
        void check();
        // A link pasted into a tab already on this page changes only the fragment: no reload, so read it here
        const onHashChange = (): void => {
            const next = takeLinkToken(new URL(window.location.href), replaceAddress);
            if (next === null) return;
            token = next;
            void check();
        };
        window.addEventListener('hashchange', onHashChange);
        return () => window.removeEventListener('hashchange', onHashChange);
    });

    function handleDone(): void {
        setAuthFlash($_('auth.resetPassword.done'));
        void goto('/');
    }
</script>

<svelte:head>
    <meta content="no-referrer" name="referrer" />
</svelte:head>

<AnimatedBackground />

<AuthPageFrame testId="reset-password-page">
    {#if status === 'form' && token}
        <ResetPasswordCard ondone={handleDone} oninvalid={() => (status = 'unknown')} {token} {username} />
    {:else}
        <LinkStatusCard onretry={check} status={status === 'form' ? 'checking' : status} />
    {/if}
</AuthPageFrame>
