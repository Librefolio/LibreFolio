<!--
  AskAdminModal — round 7: shown to NON-admin users when a newer LibreFolio
  release exists. Lists the administrators (username + email, when available)
  with mailto + copy-email affordances. Copying shows a success toast.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Check, Copy, Mail} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {writeTextToClipboard} from '$lib/utils/clipboard';

    interface AdminEntry {
        username: string;
        email: string | null;
    }

    interface Props {
        open: boolean;
        admins: AdminEntry[];
        onClose: () => void;
    }

    let {open, admins, onClose}: Props = $props();

    let copiedUsername = $state<string | null>(null);

    async function copyEmail(admin: AdminEntry) {
        if (!admin.email) return;
        try {
            await writeTextToClipboard(admin.email);
            toasts.success($_('changelog.emailCopied'));
            copiedUsername = admin.username;
            setTimeout(() => (copiedUsername = null), 1500);
        } catch {
            toasts.error($_('common.error'));
        }
    }
</script>

<ModalBase {open} onRequestClose={onClose} maxWidth="md" testId="ask-admin-modal">
    <div class="px-6 py-6 flex flex-col gap-3 bg-lf-card">
        <div class="flex items-center gap-3">
            <Mail size={24} class="text-lf-warning shrink-0" />
            <h2 class="text-lg font-semibold text-lf-primary">{$_('changelog.askAdminTitle')}</h2>
        </div>
        <p class="text-sm text-lf-secondary leading-relaxed" data-testid="ask-admin-message">
            {$_('changelog.askAdmin')}
        </p>
        <div class="flex flex-col gap-2" data-testid="ask-admin-list">
            {#each admins as admin (admin.username)}
                <div class="flex items-center justify-between gap-2 rounded-lg border border-lf-warning-line bg-lf-panel px-3 py-2" data-testid="ask-admin-row">
                    <span class="text-sm font-medium text-lf-primary">{admin.username}</span>
                    {#if admin.email}
                        <div class="flex items-center gap-1.5">
                            <a href="mailto:{admin.email}" class="inline-flex items-center gap-1 text-xs text-lf-link hover:underline" data-testid="ask-admin-mailto">
                                <Mail size={12} />
                                {admin.email}
                            </a>
                            <button type="button" class="p-1 rounded text-lf-muted hover:text-lf-secondary transition-colors" title={$_('changelog.copyEmail')} onclick={() => copyEmail(admin)} data-testid="ask-admin-copy">
                                {#if copiedUsername === admin.username}
                                    <Check size={13} class="text-lf-success" />
                                {:else}
                                    <Copy size={13} />
                                {/if}
                            </button>
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    </div>
    <div class="px-6 py-4 bg-lf-card border-t border-lf-subtle">
        <button type="button" class="w-full px-4 py-2.5 text-sm font-medium rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover transition-colors" onclick={onClose} data-testid="ask-admin-close">
            {$_('common.close')}
        </button>
    </div>
</ModalBase>
