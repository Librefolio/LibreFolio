<!--
AccountLinkTypeBadge — what an account link is for (lot UA3), as a neutral pill with its icon: the purposes are kinds,
told apart by icon and word, never by colour.
-->
<script lang="ts">
    import {AtSign, KeyRound, MailCheck, UserCog, UserPlus} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import type {AccountLinkPurpose} from './types';

    interface Props {
        purpose: AccountLinkPurpose;
    }

    let {purpose}: Props = $props();

    const ICONS = {invite: UserPlus, password_reset: KeyRound, email_verification: MailCheck, admin_setup: UserCog, email_change: AtSign} as const;
    const Icon = $derived(ICONS[purpose]);
</script>

<span class="inline-flex max-w-full items-center gap-1 rounded-full border border-lf-subtle bg-lf-panel px-2 py-0.5 text-xs font-medium text-lf-secondary" data-purpose={purpose} data-testid="account-link-type">
    <Icon aria-hidden="true" class="h-3 w-3 shrink-0" />
    <span class="truncate">{$_(`settings.usersTab.links.purpose.${purpose}`)}</span>
</span>
