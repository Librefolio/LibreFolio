<script lang="ts">
    /**
     * How safely this browser talks to LibreFolio: one line in the sidebar, details on demand.
     * The level and reason come from `connectionSecurityStore` (plan 36); the details carry the
     * reason, a line for administrators when the session cookie is not Secure on HTTPS, and the
     * user page. Collapsed, the line is its icon: a click asks the sidebar to expand (D3).
     */
    import {onMount} from 'svelte';
    import {BookOpen, ShieldAlert, ShieldCheck, ShieldHalf} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {auth} from '$lib/stores/app/auth';
    import {currentLanguage} from '$lib/stores/app/language';
    import {connectionSecurity, refreshConnectionSecurity} from '$lib/stores/app/connectionSecurityStore';
    import {connectionSecurityDocsUrl, type ConnectionLevel, type ConnectionReason} from '$lib/utils/security/connectionSecurity';

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
    // Readable on the sidebar's green, in both themes: the sidebar keeps its colour.
    const LEVEL_TONES: Record<ConnectionLevel, string> = {
        secure: 'text-emerald-300',
        local: 'text-lime-200',
        insecure: 'text-red-300',
    };

    let detailsOpen = $state(false);

    const level = $derived($connectionSecurity.level);
    const label = $derived($_(LEVEL_KEYS[level]));
    const Icon = $derived(LEVEL_ICONS[level]);
    const showAdminWarning = $derived($auth.user?.is_superuser === true && $connectionSecurity.cookieWarning);

    onMount(() => {
        void refreshConnectionSecurity();
    });

    function toggle(): void {
        if (collapsed) {
            onExpand();
            detailsOpen = true;
            return;
        }
        detailsOpen = !detailsOpen;
    }
</script>

<div data-testid="connection-security" data-level={level} data-reason={$connectionSecurity.reason} data-server-checked={$connectionSecurity.serverChecked ? 'true' : 'false'}>
    <button
        type="button"
        class="w-full flex items-center rounded-lg px-2 py-1.5 text-xs transition-colors hover:bg-white/10 {collapsed ? 'justify-center' : 'gap-2'} {level === 'insecure' ? 'bg-red-500/20' : ''}"
        data-testid="connection-security-toggle"
        aria-expanded={detailsOpen}
        aria-controls={collapsed ? undefined : 'connection-security-details'}
        aria-label={collapsed ? label : undefined}
        title={collapsed ? label : undefined}
        onclick={toggle}
    >
        <Icon size={16} class="flex-shrink-0 {LEVEL_TONES[level]}" aria-hidden="true" />
        {#if !collapsed}
            <span class="flex-1 truncate text-left text-white/80" data-testid="connection-security-label">{label}</span>
        {/if}
    </button>

    {#if detailsOpen && !collapsed}
        <div id="connection-security-details" class="mt-1 space-y-2 rounded-lg bg-white/10 px-3 py-2 text-xs leading-relaxed text-white/80" data-testid="connection-security-details">
            <p data-testid="connection-security-reason">{$_(REASON_KEYS[$connectionSecurity.reason])}</p>
            {#if showAdminWarning}
                <p class="rounded bg-amber-500/20 px-2 py-1 text-amber-100" data-testid="connection-security-admin-warning">{$_('connectionSecurity.cookieWarning')}</p>
            {/if}
            <a class="inline-flex items-center gap-1 underline transition-colors hover:text-white" data-testid="connection-security-docs-link" href={connectionSecurityDocsUrl($currentLanguage)} target="_blank" rel="noopener noreferrer">
                <BookOpen size={12} aria-hidden="true" />
                {$_('connectionSecurity.learnMore')}
            </a>
        </div>
    {/if}
</div>
