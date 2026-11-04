<script lang="ts">
    /**
     * The page of an email-verification link, `/verify-email#token=…` (workstream E, lots E5 and E-25; developer
     * decision 44).
     *
     * The token leaves the address bar at once, but only its owner's click spends it (lot E-25): a mail filter that
     * opens the links of a message in a browser of its own to check them runs this page too, and must not verify the
     * address in place of its owner. Once the address is verified the account is active, and the page sends its owner
     * to the sign-in with a message. A link that cannot be used says why, after the click; signing in then offers a
     * new one.
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
    /** Only the latest link writes: an answer about an older one, arriving late, is dropped. */
    let generation = 0;

    /** A link read from the address: it waits for the click; none is `missing`. Any answer still on its way is dropped. */
    function takeLink(next: string | null): void {
        generation++;
        token = next;
        status = next ? 'ready' : 'missing';
    }

    /** Spends the link: the click on «confirm», or the retry of a check that failed. */
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
        takeLink(takeLinkToken(new URL(window.location.href), replaceAddress));
        // A link pasted into a tab already on this page changes only the fragment: no reload, so read it here
        const onHashChange = (): void => {
            const next = takeLinkToken(new URL(window.location.href), replaceAddress);
            if (next === null) return;
            takeLink(next);
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
    <VerifyEmailCard onconfirm={confirm} onretry={confirm} {status} />
</AuthPageFrame>
