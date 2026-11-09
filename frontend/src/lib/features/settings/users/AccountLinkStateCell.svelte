<!--
AccountLinkStateCell — where an account link stands (lot UA3): its state as a pill, then, for a closed link, when it
closed and, for a used one, by whom. The state is the backend's (`GET /users/account-links`).
-->
<script lang="ts">
    import {Ban, CircleCheck, CircleDot, Clock} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import type {AccountLink} from './types';

    interface Props {
        link: AccountLink;
    }

    let {link}: Props = $props();

    const TONES = {
        open: {icon: CircleDot, classes: 'border-lf-info-line bg-lf-info-soft text-lf-info-on-soft'},
        used: {icon: CircleCheck, classes: 'border-lf-success-line bg-lf-success-soft text-lf-success-on-soft'},
        expired: {icon: Clock, classes: 'border-lf-warning-line bg-lf-warning-soft text-lf-warning-on-soft'},
        revoked: {icon: Ban, classes: 'border-lf-subtle bg-lf-panel text-lf-secondary'},
    } as const;
    const tone = $derived(TONES[link.state]);
    const Icon = $derived(tone.icon);
    // When the link closed: used, revoked, or the expiry it reached
    const closedAt = $derived(link.state === 'used' ? link.used_at : link.state === 'revoked' ? link.revoked_at : link.state === 'expired' ? link.expires_at : null);
</script>

<span class="inline-flex max-w-full flex-wrap items-center gap-x-1.5 gap-y-0.5" data-state={link.state} data-testid="account-link-state">
    <span class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium {tone.classes}">
        <Icon aria-hidden="true" class="h-3 w-3 shrink-0" />{$_(`settings.usersTab.links.state.${link.state}`)}
    </span>
    {#if closedAt}
        <span class="text-xs text-lf-muted" data-testid="account-link-state-detail">
            {formatDateTime(closedAt)}{#if link.state === 'used' && link.used_by_username}&nbsp;{$_('settings.usersTab.links.usedBy', {values: {username: link.used_by_username}})}{/if}
        </span>
    {/if}
</span>
