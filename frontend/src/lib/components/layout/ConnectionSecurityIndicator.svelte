<script lang="ts">
    /**
     * How safely this browser talks to LibreFolio: one line in the sidebar, details on demand.
     * The level and reason come from `connectionSecurityStore` (plan 36); the details carry the
     * reason, a line for administrators when the session cookie is not Secure on HTTPS, and the
     * user page. Collapsed, the line is its icon: a click asks the sidebar to expand (D3).
     *
     * The details close on a click on the reason, and by themselves 30 s after they open (plan 48, C3). The pointer
     * anywhere on the indicator holds the countdown, and so does the focus inside the details, not on the toggle,
     * where a mouse click leaves it in Chrome (choice (b)). Once nothing holds it, the countdown starts again from 30 s.
     */
    import {onMount, untrack} from 'svelte';
    import {BookOpen, ShieldAlert, ShieldCheck, ShieldHalf} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {auth} from '$lib/stores/app/auth';
    import {currentLanguage} from '$lib/stores/app/language';
    import {connectionSecurity, refreshConnectionSecurity} from '$lib/stores/app/connectionSecurityStore';
    import {connectionSecurityDocsUrl, type ConnectionLevel, type ConnectionReason} from '$lib/utils/security/connectionSecurity';
    import {securityChecks} from '$lib/features/settings/security/securityChecks.svelte';

    interface Props {
        /** The sidebar shows icons only. */
        collapsed?: boolean;
        /** Asks the sidebar to expand, so the details have room. */
        onExpand?: () => void;
    }

    let {collapsed = false, onExpand = () => {}}: Props = $props();

    // Whole-key literals, so the i18n audit sees every key as read.
    const LEVEL_KEYS: Record<ConnectionLevel, string> = {
        secure: 'connectionSecurity.level.secure',
        local: 'connectionSecurity.level.local',
        insecure: 'connectionSecurity.level.insecure',
    };
    const REASON_KEYS: Record<ConnectionReason, string> = {
        https: 'connectionSecurity.reason.https',
        localhost: 'connectionSecurity.reason.localhost',
        vpn: 'connectionSecurity.reason.vpn',
        lan: 'connectionSecurity.reason.lan',
        uncertain: 'connectionSecurity.reason.uncertain',
        internet: 'connectionSecurity.reason.internet',
    };
    const LEVEL_ICONS = {secure: ShieldCheck, local: ShieldHalf, insecure: ShieldAlert};
    // On the green bar, in both themes: the bright statuses of the dark theme (designer, round 2; D-T17).
    const LEVEL_TONES: Record<ConnectionLevel, string> = {
        secure: 'text-lf-bar-success',
        local: 'text-lf-bar-warning',
        insecure: 'text-lf-bar-danger',
    };

    const AUTO_CLOSE_MS = 30_000;

    let detailsOpen = $state(false);
    let pointerInside = $state(false);
    let focusInDetails = $state(false);
    let toggleEl: HTMLButtonElement | undefined = $state();

    // The handle lives in the closure: a teardown clears the timer its own run armed, never one a later run replaced.
    $effect(() => {
        if (!detailsOpen || pointerInside || focusInDetails) return;
        const timer = setTimeout(closeDetails, AUTO_CLOSE_MS);
        return () => clearTimeout(timer);
    });

    const level = $derived($connectionSecurity.level);
    const label = $derived($_(LEVEL_KEYS[level]));
    const Icon = $derived(LEVEL_ICONS[level]);
    const showAdminWarning = $derived($auth.user?.is_superuser === true && $connectionSecurity.cookieWarning);

    // An administrator's security checks (N69-1): the errors and warnings the Security tab counts, as a dot on the icon
    // and a link in the details to their list. Anyone else has none, and the page never asks for them.
    const isAdmin = $derived($auth.user?.is_superuser === true);
    const attention = $derived(isAdmin ? securityChecks.attentionCount : 0);
    const severity = $derived(attention > 0 ? securityChecks.attentionSeverity : null);
    const attentionText = $derived(attention > 0 ? $_('connectionSecurity.attention', {values: {count: attention}}) : '');
    // Colour is not the only sign (WCAG 1.4.1): the count joins the line's name, and its tooltip when collapsed.
    const toggleName = $derived(attention > 0 ? `${label} — ${attentionText}` : collapsed ? label : undefined);

    // Once per page load. Untracked: the read moves the store's status, which must not run this again (a failed read
    // would be retried for ever); the next page load tries again.
    $effect(() => {
        if (isAdmin) untrack(() => void securityChecks.ensureLoaded());
    });

    onMount(() => {
        void refreshConnectionSecurity();
    });

    function closeDetails(): void {
        detailsOpen = false;
        // The details leave the page with the focus they held, and not every browser fires a focusout for that.
        focusInDetails = false;
    }

    function toggle(): void {
        if (collapsed) {
            onExpand();
            detailsOpen = true;
            return;
        }
        if (detailsOpen) closeDetails();
        else detailsOpen = true;
    }

    /** A keyboard user keeps their place: a reason that held the focus hands it back to the toggle. */
    function closeFromReason(event: MouseEvent & {currentTarget: EventTarget & HTMLButtonElement}): void {
        const heldFocus = document.activeElement === event.currentTarget;
        closeDetails();
        if (heldFocus) toggleEl?.focus();
    }

    function releaseFocus(event: FocusEvent & {currentTarget: EventTarget & HTMLDivElement}): void {
        // From the reason to the link, the focus stays inside the details.
        if (event.relatedTarget instanceof Node && event.currentTarget.contains(event.relatedTarget)) return;
        focusInDetails = false;
    }
</script>

<div
    data-testid="connection-security"
    data-level={level}
    data-reason={$connectionSecurity.reason}
    data-server-checked={$connectionSecurity.serverChecked ? 'true' : 'false'}
    data-security-attention={attention}
    data-security-severity={severity ?? 'none'}
    onpointerenter={() => (pointerInside = true)}
    onpointerleave={() => (pointerInside = false)}
>
    <button
        bind:this={toggleEl}
        type="button"
        class="w-full flex items-center rounded-lg px-2 py-1.5 text-xs transition-colors hover:bg-lf-bar-hover focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus {collapsed ? 'justify-center' : 'gap-2'} {level === 'insecure' ? 'bg-lf-bar-danger/20' : ''}"
        data-testid="connection-security-toggle"
        aria-expanded={detailsOpen}
        aria-controls={collapsed ? undefined : 'connection-security-details'}
        aria-label={toggleName}
        title={collapsed ? toggleName : undefined}
        onclick={toggle}
    >
        <span class="relative inline-flex flex-shrink-0">
            <Icon size={16} class={LEVEL_TONES[level]} aria-hidden="true" />
            {#if severity}
                <span class="absolute -right-1 -top-1 h-2 w-2 rounded-full ring-2 ring-lf-bar {severity === 'error' ? 'bg-lf-bar-danger' : 'bg-lf-bar-warning'}" data-testid="connection-security-attention-dot" data-severity={severity} aria-hidden="true"></span>
            {/if}
        </span>
        {#if !collapsed}
            <span class="flex-1 truncate text-left text-lf-bar-text" data-testid="connection-security-label">{label}</span>
        {/if}
    </button>

    {#if detailsOpen && !collapsed}
        <div id="connection-security-details" class="mt-1 space-y-2 rounded-lg bg-lf-bar-hover px-3 py-2 text-xs leading-relaxed text-lf-bar-text" data-testid="connection-security-details" onfocusin={() => (focusInDetails = true)} onfocusout={releaseFocus}>
            <button type="button" class="block w-full cursor-pointer text-left rounded focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus" data-testid="connection-security-reason" title={$_('common.close')} onclick={closeFromReason}
                >{$_(REASON_KEYS[$connectionSecurity.reason])}</button
            >
            {#if severity}
                <a
                    class="flex items-center gap-1.5 rounded border px-2 py-1 transition-colors hover:text-lf-on-bar-active focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus {severity === 'error' ? 'border-lf-bar-danger' : 'border-lf-bar-warning'}"
                    data-testid="connection-security-attention-link"
                    data-severity={severity}
                    href="/settings?tab=security"
                    onclick={closeDetails}
                >
                    <ShieldAlert size={12} class="flex-shrink-0 {severity === 'error' ? 'text-lf-bar-danger' : 'text-lf-bar-warning'}" aria-hidden="true" />
                    {attentionText}
                </a>
            {/if}
            {#if showAdminWarning}
                <p class="rounded border border-lf-bar-warning px-2 py-1 text-lf-bar-warning" data-testid="connection-security-admin-warning">{$_('connectionSecurity.cookieWarning')}</p>
            {/if}
            <a
                class="inline-flex items-center gap-1 underline transition-colors hover:text-lf-on-bar-active rounded focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus"
                data-testid="connection-security-docs-link"
                href={connectionSecurityDocsUrl($currentLanguage)}
                target="_blank"
                rel="noopener noreferrer"
            >
                <BookOpen size={12} aria-hidden="true" />
                {$_('connectionSecurity.learnMore')}
            </a>
        </div>
    {/if}
</div>
