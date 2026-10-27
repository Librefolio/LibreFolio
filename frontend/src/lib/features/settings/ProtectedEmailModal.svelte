<!--
ProtectedEmailModal — what the paying administrator of a managed instance reads when it tries to change its own email
address from the profile (lot A5-1b): the address is the subscription owner's, so it cannot be changed here — the server
refuses with 409 `ACCOUNT_PROTECTED` — and the host does it.

One link to the host: the billing page (`GET /system/block`, administrators only), else the support address of the public
configuration (an http(s) page or mailto:), else none. Nothing here ever throws at the profile.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {ExternalLink, Lock} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';

    interface Props {
        open: boolean;
        onClose: () => void;
        /** The details of the block, `GET /system/block` (its `billing_url`); injectable for tests. */
        fetchBlock?: () => Promise<{blocked?: boolean; billing_url?: string | null} | null | undefined>;
    }

    let {open, onClose, fetchBlock = () => zodiosApi.get_instance_block_api_v1_system_block_get()}: Props = $props();

    let billingUrl = $state<string | null>(null);

    const uid = $props.id();

    /** Checked again before it becomes a link: only a web page or, for support, one mailbox. */
    const webAddress = (value: unknown): string | null => (typeof value === 'string' && /^https?:\/\//i.test(value) ? value : null);
    const supportAddress = (value: unknown): string | null => webAddress(value) ?? (typeof value === 'string' && /^mailto:/i.test(value) ? value : null);

    const supportUrl = $derived(supportAddress(instanceConfig.config.support_url));
    const link = $derived(billingUrl ? {kind: 'billing', href: billingUrl, label: 'settings.usersTab.billing'} : supportUrl ? {kind: 'support', href: supportUrl, label: 'settings.protectedEmail.support'} : null);

    $effect(() => {
        if (!open) {
            return;
        }
        untrack(() => {
            billingUrl = null;
        });
        let current = true;
        void (async () => {
            try {
                const block = await fetchBlock();
                if (current) {
                    billingUrl = webAddress(block?.billing_url);
                }
            } catch {
                // The support address, or no link: the message is enough
            }
        })();
        return () => {
            current = false;
        };
    });
</script>

<ModalBase {open} labelledBy="{uid}-title" maxWidth="md" onRequestClose={onClose} testId="protected-email-modal">
    <div class="space-y-4 p-6 text-lf-primary">
        <div class="flex items-start gap-3">
            <Lock aria-hidden="true" class="mt-0.5 h-5 w-5 shrink-0 text-lf-warning" />
            <div class="space-y-2">
                <h2 class="text-lg font-semibold" id="{uid}-title">{$_('settings.protectedEmail.title')}</h2>
                <p class="text-sm text-lf-secondary">{$_('settings.protectedEmail.message')}</p>
            </div>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-3">
            {#if link}
                <a class="inline-flex items-center gap-1 text-sm font-medium text-lf-link hover:underline" data-kind={link.kind} data-testid="protected-email-link" href={link.href} rel="noopener noreferrer" target="_blank">
                    {$_(link.label)}<ExternalLink aria-hidden="true" class="h-3.5 w-3.5" />
                </a>
            {:else}
                <span></span>
            {/if}
            <button class="rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover" data-testid="protected-email-close" onclick={onClose} type="button">{$_('common.close')}</button>
        </div>
    </div>
</ModalBase>
