<!--
  OwnerChoiceModal — which user of an uploaded backup becomes the paying administrator (lot A5-2; mounted by the restore of
  workstream B, on a managed instance only).

  The chosen account gets the owner's email (`LIBREFOLIO_ADMIN_EMAIL`), is made an administrator and protected, and its password
  is reset through a link sent to that email: the notice says so. A user who already has the owner's email is selected at once
  and the choice is forced; otherwise the person chooses. The modal calls no server: it answers with the user's id.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {Crown, ShieldCheck, UserX} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {sameEmail} from '$lib/features/auth/emailCase';

    /** A user of the backup. `id` is the one in the restored database. */
    export interface OwnerCandidate {
        id: number;
        username: string;
        email: string;
        is_superuser: boolean;
        is_active: boolean;
    }

    interface Props {
        open: boolean;
        /** The owner's email (`LIBREFOLIO_ADMIN_EMAIL`): the notice names it. */
        ownerEmail: string;
        users: OwnerCandidate[];
        /** «Confirm» with a choice made: the id of the user. */
        onConfirm: (userId: number) => void;
        /** «Cancel», Escape, a click outside: the restore does not go on. */
        onCancel: () => void;
        /** The restore is working: every control is off. */
        busy?: boolean;
    }

    let {open, ownerEmail, users, onConfirm, onCancel, busy = false}: Props = $props();

    const uid = $props.id();
    let chosen = $state<number | null>(null);

    // The account that already has the owner's email, in any A–Z case: the choice is forced
    const holder = $derived(users.find((user) => sameEmail(user.email, ownerEmail)) ?? null);
    const locked = $derived(holder !== null);
    const selected = $derived(holder ? holder.id : chosen);

    $effect(() => {
        if (open) {
            untrack(() => {
                chosen = null;
            });
        }
    });

    function choose(user: OwnerCandidate): void {
        if (busy || locked) {
            return;
        }
        chosen = user.id;
    }

    function confirm(): void {
        if (busy || selected === null) {
            return;
        }
        onConfirm(selected);
    }
</script>

<ModalBase closeOnBackdropClick={!busy} closeOnEscape={!busy} labelledBy="{uid}-title" maxWidth="lg" {open} onRequestClose={onCancel}>
    <div class="space-y-4 p-6 text-lf-primary" data-locked={String(locked)} data-testid="owner-choice-modal">
        <div class="space-y-1">
            <h2 class="text-lg font-semibold" id="{uid}-title">{$_('backup.ownerChoice.title')}</h2>
            <p class="text-sm text-lf-secondary">{$_('backup.ownerChoice.intro')}</p>
            {#if locked}
                <p class="text-xs text-lf-muted">{$_('backup.ownerChoice.locked')}</p>
            {/if}
        </div>

        {#if users.length === 0}
            <p class="rounded-md border border-lf-subtle bg-lf-panel px-3 py-2 text-sm text-lf-muted" data-testid="owner-choice-empty">{$_('backup.ownerChoice.empty')}</p>
        {:else}
            <div aria-labelledby="{uid}-title" class="max-h-72 space-y-2 overflow-y-auto" role="radiogroup">
                {#each users as user (user.id)}
                    {@const matches = holder !== null && user.id === holder.id}
                    <button
                        aria-checked={selected === user.id}
                        class="flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left text-sm disabled:cursor-not-allowed disabled:opacity-50 {selected === user.id ? 'border-lf-focus bg-lf-selected' : 'border-lf-input bg-lf-card hover:bg-lf-hover'}"
                        data-active={String(user.is_active)}
                        data-admin={String(user.is_superuser)}
                        data-matches-owner={String(matches)}
                        data-selected={String(selected === user.id)}
                        data-testid="owner-choice-option"
                        data-user-id={user.id}
                        disabled={busy || (locked && !matches)}
                        onclick={() => choose(user)}
                        role="radio"
                        type="button"
                    >
                        <span class="min-w-0 flex-1">
                            <span class="block truncate font-medium">{user.username}</span>
                            <span class="block truncate text-xs text-lf-muted">{user.email}</span>
                        </span>
                        {#if matches}
                            <span class="inline-flex items-center gap-1 rounded-full border border-lf-subtle bg-lf-neutral px-2 py-0.5 text-xs text-lf-secondary"><Crown aria-hidden="true" class="h-3 w-3" />{$_('backup.ownerChoice.ownerBadge')}</span>
                        {/if}
                        {#if user.is_superuser}
                            <span class="inline-flex items-center gap-1 rounded-full border border-lf-info-line bg-lf-info-soft px-2 py-0.5 text-xs text-lf-info-on-soft"><ShieldCheck aria-hidden="true" class="h-3 w-3" />{$_('backup.ownerChoice.adminBadge')}</span>
                        {/if}
                        {#if !user.is_active}
                            <span class="inline-flex items-center gap-1 rounded-full border border-lf-subtle bg-lf-neutral px-2 py-0.5 text-xs text-lf-secondary"><UserX aria-hidden="true" class="h-3 w-3" />{$_('backup.ownerChoice.inactiveBadge')}</span>
                        {/if}
                    </button>
                {/each}
            </div>
        {/if}

        <div class="rounded-md border border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-sm text-lf-warning-on-soft" data-testid="owner-choice-notice" role="note">
            {$_('backup.ownerChoice.notice', {values: {email: ownerEmail}})}
        </div>

        <div class="flex flex-wrap justify-end gap-2">
            <button class="rounded-md border border-lf-input px-3 py-1.5 text-sm font-medium text-lf-secondary hover:bg-lf-hover disabled:cursor-not-allowed disabled:opacity-50" data-testid="owner-choice-cancel" disabled={busy} onclick={onCancel} type="button">
                {$_('backup.ownerChoice.cancel')}
            </button>
            <button class="rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50" data-testid="owner-choice-confirm" disabled={busy || selected === null} onclick={confirm} type="button">
                {$_('backup.ownerChoice.confirm')}
            </button>
        </div>
    </div>
</ModalBase>
