<script lang="ts">
    /**
     * The page of the link that confirms a new email address, `/confirm-email-change#token=…`. Two flows share it: the
     * paying administrator of a managed instance, whose address the hosting provider changes (lot A5-1b), and any account
     * that asked for a new address from its profile (release 1.4, project 71). The instance emails the link to the NEW
     * address, and the address changes only after the click. The page cannot tell the flows apart, and its texts do not:
     * the answer of the server does not say which one a link belongs to.
     *
     * Like `/verify-email` (E-25): the token leaves the address bar at once, but only its owner's click spends it (a mail
     * filter that opens the links of a message must not confirm in place of its owner). Confirmed, the owner's sessions
     * have ended: the page sends it to the sign-in with a message. A link that cannot be used says why, after the click.
     *
     * A link asked from Profile confirms only with the session of its account (decision D10): the server answers 403
     * `EMAIL_CHANGE_SIGN_IN_REQUIRED` otherwise, and the page says `signin`. Only then is the token kept, in this tab's
     * `sessionStorage` (`KEPT_LINK`), never in the address: the button ends this browser's session (another account may be
     * signed in here) and opens the sign-in with the way back. Back here without a `#token`, the kept token makes the page
     * `ready` and leaves the storage at once (R1, the developer, 11/11). The token alone confirms nothing any more, so
     * keeping it for the minutes of a sign-in opens nothing. A token in the address wins over a kept one.
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
    import {confirmOwnerEmailChange, endSessionBeforeSignIn, readEmailChangeRefusal, type EmailChangePageStatus} from '$lib/features/email/emailChangeApi';
    import {loginUrl} from '$lib/utils/internalPath';

    /** The key of the token kept for the sign-in, in this tab only. */
    const KEPT_LINK = 'lf-email-change-link';
    const PAGE_PATH = '/confirm-email-change';

    let token = $state<string | null>(null);
    let status = $state<EmailChangePageStatus>('checking');

    /** The tab's storage, or null where it cannot be used (a private mode that refuses it): the page then works as before. */
    function tabStorage(): Storage | null {
        try {
            return window.sessionStorage;
        } catch {
            return null;
        }
    }

    function keepLink(value: string): void {
        try {
            tabStorage()?.setItem(KEPT_LINK, value);
        } catch {
            // A full or refused storage: the sign-in still works, the link is opened again from the email
        }
    }

    function forgetKeptLink(): void {
        try {
            tabStorage()?.removeItem(KEPT_LINK);
        } catch {
            // Nothing kept, or nothing that can be removed
        }
    }

    /** The token kept before a sign-in, taken out of the storage as it is read. */
    function takeKeptLink(): string | null {
        let kept: string | null = null;
        try {
            kept = tabStorage()?.getItem(KEPT_LINK) ?? null;
        } catch {
            kept = null;
        }
        forgetKeptLink();
        return kept && kept.trim() ? kept : null;
    }
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
        const spending = token;
        try {
            await confirmOwnerEmailChange(spending);
            if (mine !== generation) return;
            forgetKeptLink();
            setAuthFlash($_('email.emailChange.changed'));
            void goto('/');
        } catch (error) {
            if (mine !== generation) return;
            const refusal = readEmailChangeRefusal(error);
            // Kept only for the way through the sign-in: never written for any other answer
            if (refusal === 'signin') keepLink(spending);
            else forgetKeptLink();
            status = refusal ?? 'error';
        }
    }

    /** `signin`: end this browser's session first, then the sign-in, which comes back here. */
    async function signIn(): Promise<void> {
        await endSessionBeforeSignIn();
        void goto(loginUrl(PAGE_PATH));
    }

    onMount(() => {
        const fromAddress = takeLinkToken(new URL(window.location.href), replaceAddress);
        // A token in the address wins; without one, the token kept before a sign-in, read once
        if (fromAddress !== null) forgetKeptLink();
        takeLink(fromAddress ?? takeKeptLink());
        // A link pasted into a tab already on this page changes only the fragment: no reload, so read it here
        const onHashChange = (): void => {
            const next = takeLinkToken(new URL(window.location.href), replaceAddress);
            if (next === null) return;
            forgetKeptLink();
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
    <EmailChangeCard onconfirm={confirm} onretry={confirm} onsignin={signIn} {status} />
</AuthPageFrame>
