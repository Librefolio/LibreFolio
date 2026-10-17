<script lang="ts">
    /**
     * The page of an invitation link, `/invite#token=…`.
     *
     * The token leaves the address bar at once; the server says what it is worth. A valid invitation opens the
     * registration form, with the role it grants and the address the administrator wrote (a suggestion: it can be
     * changed). A closed registration refuses even a valid invitation, so the page says so before the form.
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
    import AuthPageFrame from '$lib/features/auth/AuthPageFrame.svelte';
    import LinkStatusCard from '$lib/features/auth/LinkStatusCard.svelte';
    import RegisterCard from '$lib/features/auth/RegisterCard.svelte';
    import {replaceAddress} from '$lib/features/auth/addressBar';
    import {setAuthFlash} from '$lib/features/auth/authFlash';
    import {inspectLinkToken, takeLinkToken, type LinkInspection, type LinkPageStatus} from '$lib/features/auth/linkToken';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';

    let token = $state<string | null>(null);
    let status = $state<LinkPageStatus | 'form'>('checking');
    let invitation = $state<LinkInspection | null>(null);

    async function check(): Promise<void> {
        if (!token) {
            status = 'missing';
            return;
        }
        status = 'checking';
        try {
            const [inspection] = await Promise.all([inspectLinkToken(token, 'invite'), instanceConfig.load()]);
            if (inspection.status !== 'valid') {
                status = inspection.status;
                return;
            }
            if (instanceConfig.config.accounts.registration_mode === 'disabled') {
                status = 'closed';
                return;
            }
            invitation = inspection;
            status = 'form';
        } catch {
            status = 'error';
        }
    }

    onMount(() => {
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

    function handleGotoLogin(event: CustomEvent<{message?: string}>): void {
        if (event.detail?.message) setAuthFlash(event.detail.message);
        void goto('/');
    }
</script>

<svelte:head>
    <meta content="no-referrer" name="referrer" />
</svelte:head>

<AnimatedBackground />

<AuthPageFrame testId="invite-page">
    {#if status === 'form' && invitation}
        <RegisterCard grantsAdmin={invitation.grants_admin ?? false} initialEmail={invitation.email ?? ''} inviteToken={token} on:gotoLogin={handleGotoLogin} />
    {:else}
        <LinkStatusCard onretry={check} status={status === 'form' ? 'checking' : status} />
    {/if}
</AuthPageFrame>
