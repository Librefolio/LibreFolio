<!--
  STAND-IN for workstream A's OwnerChoiceModal (A5-2), with A's props and data-testid only. At the merge of A's branch
  this file is replaced whole by A's component: take A's version. It calls no server and returns only the chosen id.
-->
<script lang="ts" module>
    export interface OwnerCandidate {
        /** The account's id in the restored database. */
        id: number;
        username: string;
        email: string;
        is_superuser: boolean;
        is_active: boolean;
    }
</script>

<script lang="ts">
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {_} from '$lib/i18n';

    interface Props {
        open: boolean;
        ownerEmail: string;
        users: OwnerCandidate[];
        onConfirm: (userId: number) => void;
        onCancel: () => void;
        busy?: boolean;
    }

    let {open, ownerEmail, users, onConfirm, onCancel, busy = false}: Props = $props();

    const fold = (email: string) => email.replace(/[A-Z]/g, (letter) => letter.toLowerCase());
    const forced = $derived(users.find((user) => fold(user.email) === fold(ownerEmail)) ?? null);
    let picked = $state<number | null>(null);
    const selected = $derived(forced?.id ?? picked);
</script>

<ModalBase {open} zIndex={60} maxWidth="md" onRequestClose={() => !busy && onCancel()} testId="owner-choice-modal-frame" trapFocus restoreFocus>
    <div class="space-y-3 p-5 text-sm text-lf-primary" data-testid="owner-choice-modal" data-locked={forced !== null ? 'true' : 'false'}>
        <p class="text-lf-secondary" data-testid="owner-choice-notice">{$_('backup.restore.report.signInAgain')}</p>
        {#if users.length === 0}
            <p class="text-lf-muted" data-testid="owner-choice-empty">{$_('common.noResults')}</p>
        {:else}
            <ul class="space-y-1">
                {#each users as user (user.id)}
                    <li>
                        <button
                            class="w-full rounded-lg border border-lf-subtle px-3 py-2 text-left enabled:hover:bg-lf-hover disabled:cursor-not-allowed"
                            type="button"
                            disabled={busy || (forced !== null && forced.id !== user.id)}
                            data-testid="owner-choice-option"
                            data-user-id={user.id}
                            data-matches-owner={forced?.id === user.id ? 'true' : 'false'}
                            data-selected={selected === user.id ? 'true' : 'false'}
                            onclick={() => (picked = user.id)}
                        >
                            {user.username}
                        </button>
                    </li>
                {/each}
            </ul>
        {/if}
        <footer class="flex justify-end gap-2">
            <button class="rounded-lg border border-lf-subtle px-4 py-2 text-lf-secondary disabled:opacity-50" type="button" disabled={busy} data-testid="owner-choice-cancel" onclick={onCancel}>{$_('common.cancel')}</button>
            <button class="rounded-lg bg-lf-danger-solid px-4 py-2 font-medium text-lf-on-danger-solid disabled:opacity-50" type="button" disabled={busy || selected === null} data-testid="owner-choice-confirm" onclick={() => selected !== null && onConfirm(selected)}>
                {$_('common.confirm')}
            </button>
        </footer>
    </div>
</ModalBase>
