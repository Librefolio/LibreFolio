<script lang="ts">
    /**
     * The page of an email-verification link, `/verify-email#token=…` (workstream E, lot E5; developer decision 44).
     *
     * The token leaves the address bar at once and is spent right away: there is nothing to fill in. Once the address
     * is verified the account is active, and the page sends its owner to the sign-in with a message. A link that
     * cannot be used says why; signing in then offers a new one.
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
    import AuthPageFrame from '$lib/features/auth/AuthPageFrame.svelte';
    import {replaceAddress} from '$lib/features/auth/addressBar';
    import {setAuthFlash} from '$lib/features/auth/authFlash';
    import {takeLinkToken} from '$lib/features/auth/linkToken';
    import VerifyEmailCard from '$lib/features/email/VerifyEmailCard.svelte';
    import type {VerifyPageStatus} from '$lib/features/email/emailText';
    import {confirmEmailVerification, readLinkRefusal} from '$lib/features/email/verificationApi';

    let token = $state<string | null>(null);
    let status = $state<VerifyPageStatus>('checking');
    /** Only the latest attempt writes: a link pasted meanwhile outruns an older answer. */
    let generation = 0;

    async function confirm(): Promise<void> {
        const mine = ++generation;
        if (!token) {
            status = 'missing';
            return;
        }
        status = 'checking';
        try {
            const {username} = await confirmEmailVerification(token);
            if (mine !== generation) return;
            setAuthFlash($_('email.verification.verified', {values: {username}}));
            void goto('/');
        } catch (error) {
            if (mine !== generation) return;
            status = readLinkRefusal(error) ?? 'error';
        }
    }

    onMount(() => {
        token = takeLinkToken(new URL(window.location.href), replaceAddress);
        void confirm();
        // A link pasted into a tab already on this page changes only the fragment: no reload, so read it here
        const onHashChange = (): void => {
            const next = takeLinkToken(new URL(window.location.href), replaceAddress);
            if (next === null) return;
            token = next;
            void confirm();
        };
        window.addEventListener('hashchange', onHashChange);
        return () => window.removeEventListener('hashchange', onHashChange);
    });
</script>

<svelte:head>
    <meta content="no-referrer" name="referrer" />
</svelte:head>

<AnimatedBackground />

<AuthPageFrame testId="verify-email-page">
    <VerifyEmailCard onretry={confirm} {status} />
</AuthPageFrame>
