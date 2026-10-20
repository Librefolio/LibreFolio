<!--
UserRow — one account of the Users tab: who it is, and the administrator's actions, in a panel that opens under it.

The backend decides every action (it refuses the last active administrator, a protected account, a full instance);
the row only turns off, with the reason, what would certainly be refused. One's own account has no action here: it is
managed from the Profile tab.
-->
<script lang="ts">
    import {ChevronRight, KeyRound, Link2Off, LogOut, RotateCcw, ShieldCheck, ShieldOff, Trash2, UserCheck, UserX} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import UserAvatar from '$lib/components/ui/media/UserAvatar.svelte';
    import type {AdminAccount, UserAction} from './types';

    interface Props {
        account: AdminAccount;
        isSelf: boolean;
        /** The account is the only active administrator of the instance. */
        isOnlyActiveAdmin: boolean;
        /** The instance has no free place. */
        full: boolean;
        onAction: (action: UserAction, account: AdminAccount) => void;
    }

    let {account, isSelf, isOnlyActiveAdmin, full, onAction}: Props = $props();

    type Reason = 'protected' | 'last-admin' | 'limit' | 'demote-first' | 'pending-setup';

    const REASON_KEY: Record<Reason, string> = {
        protected: 'settings.usersTab.reasons.protected',
        'last-admin': 'settings.usersTab.reasons.lastAdmin',
        limit: 'settings.usersTab.reasons.limit',
        'demote-first': 'settings.usersTab.reasons.demoteFirst',
        'pending-setup': 'settings.usersTab.reasons.pendingSetup',
    };

    const uid = $props.id();
    let expanded = $state(false);

    // The initial administrator waiting for its setup (F02) activates through its link only: no reactivation, no reason
    // for one; it keeps its role until then, and deleting it needs no demotion (A-43)
    const pendingSetup = $derived(account.pending_setup === true);
    const deactivateReason = $derived<Reason | null>(account.protected ? 'protected' : account.is_superuser && isOnlyActiveAdmin ? 'last-admin' : null);
    // An account waiting for its email verification with a live link already holds its place (workstream E)
    const reactivateReason = $derived<Reason | null>(full && !account.holds_place ? 'limit' : null);
    const cancelReason = $derived<Reason | null>(account.protected ? 'protected' : null);
    const demoteReason = $derived<Reason | null>(account.protected ? 'protected' : pendingSetup ? 'pending-setup' : account.is_active && isOnlyActiveAdmin ? 'last-admin' : null);
    const deleteReason = $derived<Reason | null>(account.protected ? 'protected' : account.is_superuser && !pendingSetup ? 'demote-first' : null);
    const reasons = $derived([...new Set([account.is_active ? deactivateReason : pendingSetup ? cancelReason : reactivateReason, account.is_superuser ? demoteReason : null, deleteReason].filter((reason): reason is Reason => reason !== null))]);

    const ACTION_BUTTON = 'inline-flex items-center gap-1.5 rounded-md border border-lf-input bg-lf-card px-2.5 py-1.5 text-xs font-medium text-lf-secondary hover:bg-lf-hover disabled:cursor-not-allowed disabled:opacity-50';
    const DANGER_BUTTON = 'inline-flex items-center gap-1.5 rounded-md border border-lf-danger-line bg-lf-danger-soft px-2.5 py-1.5 text-xs font-medium text-lf-danger-on-soft disabled:cursor-not-allowed disabled:opacity-50';
</script>

<li
    class="py-3 text-lf-primary"
    data-active={String(account.is_active)}
    data-admin={String(account.is_superuser)}
    data-pending-setup={String(pendingSetup)}
    data-protected={String(account.protected)}
    data-self={String(isSelf)}
    data-testid="users-row"
    data-user-id={account.id}
    data-username={account.username}
>
    <button aria-controls="{uid}-panel" aria-expanded={expanded} class="flex w-full min-w-0 items-center gap-3 text-left" data-testid="users-row-toggle" onclick={() => (expanded = !expanded)} type="button">
        <ChevronRight class="h-4 w-4 shrink-0 text-lf-muted transition-transform {expanded ? 'rotate-90' : ''}" />
        <UserAvatar username={account.username} avatarUrl={account.avatar_url ?? null} testId="users-row-avatar" />
        <span class="min-w-0 flex-1">
            <span class="flex flex-wrap items-center gap-1.5">
                <span class="truncate font-medium text-lf-primary">{account.username}</span>
                {#if isSelf}
                    <span class="rounded-full border border-lf-subtle bg-lf-selected px-2 py-0.5 text-xs text-lf-primary">{$_('settings.usersTab.badges.you')}</span>
                {/if}
                {#if account.is_superuser}
                    <span class="rounded-full border border-lf-info-line bg-lf-info-soft px-2 py-0.5 text-xs text-lf-info-on-soft">{$_('settings.usersTab.badges.admin')}</span>
                {/if}
                {#if pendingSetup}
                    <span class="rounded-full border border-lf-subtle bg-lf-neutral px-2 py-0.5 text-xs text-lf-secondary" data-testid="users-badge-pending-setup">{$_('settings.usersTab.badges.pendingSetup')}</span>
                {:else if !account.is_active}
                    <span class="rounded-full border border-lf-subtle bg-lf-neutral px-2 py-0.5 text-xs text-lf-secondary">{$_('settings.usersTab.badges.inactive')}</span>
                {/if}
                {#if account.protected}
                    <span class="rounded-full border border-lf-warning-line bg-lf-warning-soft px-2 py-0.5 text-xs text-lf-warning-on-soft">{$_('settings.usersTab.badges.protected')}</span>
                {/if}
            </span>
            <span class="block truncate text-xs text-lf-muted">
                {account.email} · {$_('settings.usersTab.createdOn', {values: {date: formatDateTime(account.created_at)}})}
            </span>
        </span>
    </button>

    {#if expanded}
        <div class="mt-3 pl-7" id="{uid}-panel">
            {#if isSelf}
                <p class="text-sm text-lf-muted" data-testid="users-self-hint">
                    {$_('settings.usersTab.selfHint')}
                    <a class="text-lf-link hover:underline" href="/settings?tab=profile">{$_('settings.profile')}</a>
                </p>
            {:else}
                <div class="flex flex-wrap gap-2">
                    {#if account.is_active}
                        <button class={ACTION_BUTTON} data-disabled-reason={deactivateReason ?? undefined} data-testid="users-action-deactivate" disabled={deactivateReason !== null} onclick={() => onAction('deactivate', account)} type="button">
                            <UserX class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.deactivate')}
                        </button>
                    {:else if pendingSetup}
                        <!-- The waiting initial administrator's setup link revoked: the cancellation (A-43) -->
                        <button class={ACTION_BUTTON} data-disabled-reason={cancelReason ?? undefined} data-testid="users-action-cancel-setup" disabled={cancelReason !== null} onclick={() => onAction('cancel-setup', account)} type="button">
                            <Link2Off class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.cancelSetup')}
                        </button>
                    {:else}
                        <button class={ACTION_BUTTON} data-disabled-reason={reactivateReason ?? undefined} data-testid="users-action-reactivate" disabled={reactivateReason !== null} onclick={() => onAction('reactivate', account)} type="button">
                            <UserCheck class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.reactivate')}
                        </button>
                    {/if}
                    {#if account.is_superuser}
                        <button class={ACTION_BUTTON} data-disabled-reason={demoteReason ?? undefined} data-testid="users-action-demote" disabled={demoteReason !== null} onclick={() => onAction('demote', account)} type="button">
                            <ShieldOff class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.demote')}
                        </button>
                    {:else}
                        <button class={ACTION_BUTTON} data-testid="users-action-promote" onclick={() => onAction('promote', account)} type="button">
                            <ShieldCheck class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.promote')}
                        </button>
                    {/if}
                    <button class={ACTION_BUTTON} data-testid="users-action-reset-link" onclick={() => onAction('reset-link', account)} type="button">
                        <KeyRound class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.resetLink')}
                    </button>
                    <button class={ACTION_BUTTON} data-testid="users-action-sign-out" onclick={() => onAction('sign-out', account)} type="button">
                        <LogOut class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.signOut')}
                    </button>
                    <button class={ACTION_BUTTON} data-testid="users-action-restart-guides" onclick={() => onAction('restart-guides', account)} type="button">
                        <RotateCcw class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.restartGuides')}
                    </button>
                    <button class={DANGER_BUTTON} data-disabled-reason={deleteReason ?? undefined} data-testid="users-action-delete" disabled={deleteReason !== null} onclick={() => onAction('delete', account)} type="button">
                        <Trash2 class="h-3.5 w-3.5" />{$_('settings.usersTab.actions.delete')}
                    </button>
                </div>
                {#if pendingSetup}
                    <p class="mt-2 text-xs text-lf-muted" data-testid="users-pending-setup-hint">{$_('settings.usersTab.pendingSetupHint')}</p>
                {/if}
                {#each reasons as reason (reason)}
                    <p class="mt-2 text-xs text-lf-muted">{$_(REASON_KEY[reason])}</p>
                {/each}
            {/if}
        </div>
    {/if}
</li>
