<script lang="ts">
    /**
     * The page of the link that confirms the new email address of the paying administrator of a managed instance,
     * `/confirm-email-change#token=…` (lot A5-1b). The hosting provider changes the address; the instance emails this link
     * to the NEW one, and the address changes only after the click.
     *
     * Like `/verify-email` (E-25): the token leaves the address bar at once, but only its owner's click spends it (a mail
     * filter that opens the links of a message must not confirm in place of its owner). Confirmed, the owner's sessions
     * have ended: the page sends it to the sign-in with a message. A link that cannot be used says why, after the click.
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
    import AuthPageFrame from '$lib/features/auth/AuthPageFrame.svelte';
    import {replaceAddress} from '$lib/features/auth/addressBar';
    import {setAuthFlash} from '$lib/features/auth/authFlash';
    import {takeLinkToken} from '$lib/features/auth/linkToken';
    import EmailChangeCard from '$lib/features/email/EmailChangeCard.svelte';
    import type {VerifyPageStatus} from '$lib/features/email/emailText';
    import {confirmOwnerEmailChange, readLinkRefusal} from '$lib/features/email/emailChangeApi';

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
            await confirmOwnerEmailChange(token);
            if (mine !== generation) return;
            setAuthFlash($_('email.emailChange.changed'));
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

<AuthPageFrame testId="email-change-page">
    <EmailChangeCard onconfirm={confirm} onretry={confirm} {status} />
</AuthPageFrame>
