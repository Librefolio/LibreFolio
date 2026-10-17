<script lang="ts">
    /**
     * The page of the setup link of the initial administrator (F02), `/setup#token=…`.
     *
     * The token leaves the address bar at once; the server says what it is worth. A valid link opens the form for the
     * account it belongs to; once the password is set the account is active and signed in, and the page goes into the
     * app. A link that cannot be used says what to do: no administrator exists yet to send a new one.
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
    import AuthPageFrame from '$lib/features/auth/AuthPageFrame.svelte';
    import LinkStatusCard from '$lib/features/auth/LinkStatusCard.svelte';
    import SetupCard from '$lib/features/auth/SetupCard.svelte';
    import {replaceAddress} from '$lib/features/auth/addressBar';
    import {inspectLinkToken, takeLinkToken, type LinkPageStatus} from '$lib/features/auth/linkToken';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
    import {auth} from '$lib/stores/app/auth';

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
            const inspection = await inspectLinkToken(token, 'admin_setup');
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

    async function handleDone(): Promise<void> {
        // The setup answers like the login: the session cookie is set, the store reads it, and the app opens.
        await auth.checkAuth();
        await goto('/dashboard');
    }
</script>

<svelte:head>
    <meta content="no-referrer" name="referrer" />
</svelte:head>

<AnimatedBackground />

<AuthPageFrame testId="setup-page">
    {#if status === 'form' && token}
        <SetupCard ondone={() => void handleDone()} oninvalid={() => (status = 'unknown')} {token} {username} />
    {:else}
        <LinkStatusCard hintKey="auth.setup.newLinkHint" onretry={check} status={status === 'form' ? 'checking' : status} />
    {/if}
</AuthPageFrame>
