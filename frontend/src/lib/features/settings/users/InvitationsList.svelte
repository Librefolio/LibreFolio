<!--
InvitationsList — the invitations still open (neither used, revoked nor expired), each revocable at any time.
-->
<script lang="ts">
    import {Mail, ShieldCheck, X} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import type {OpenInvite} from './types';

    interface Props {
        invites: OpenInvite[];
        onRevoke: (invite: OpenInvite) => void;
    }

    let {invites, onRevoke}: Props = $props();
</script>

{#if invites.length === 0}
    <p class="text-sm text-lf-muted" data-testid="users-invites-empty">{$_('settings.usersTab.invites.empty')}</p>
{:else}
    <ul class="divide-y divide-lf-subtle text-lf-primary">
        {#each invites as invite (invite.id)}
            <li class="flex items-center gap-3 py-2.5" data-admin={String(invite.grants_admin)} data-email={invite.email ?? ''} data-invite-id={invite.id} data-testid="users-invite-row">
                <Mail class="h-4 w-4 shrink-0 text-lf-muted" />
                <span class="min-w-0 flex-1">
                    <span class="flex flex-wrap items-center gap-1.5">
                        <span class="truncate text-sm font-medium">{invite.email || $_('settings.usersTab.invites.noEmail')}</span>
                        {#if invite.grants_admin}
                            <span class="inline-flex items-center gap-1 rounded-full border border-lf-info-line bg-lf-info-soft px-2 py-0.5 text-xs text-lf-info-on-soft">
                                <ShieldCheck class="h-3 w-3" />{$_('settings.usersTab.badges.admin')}
                            </span>
                        {/if}
                    </span>
                    <span class="block text-xs text-lf-muted">
                        {$_('settings.usersTab.invites.dates', {values: {created: formatDateTime(invite.created_at), expires: formatDateTime(invite.expires_at)}})}
                    </span>
                </span>
                <button class="inline-flex shrink-0 items-center gap-1 rounded-md border border-lf-input bg-lf-card px-2.5 py-1.5 text-xs font-medium text-lf-secondary hover:bg-lf-hover" data-testid="users-invite-revoke" onclick={() => onRevoke(invite)} type="button">
                    <X class="h-3.5 w-3.5" />{$_('settings.usersTab.invites.revoke')}
                </button>
            </li>
        {/each}
    </ul>
{/if}
