<script lang="ts">
    import {onMount} from 'svelte';
    import {ExternalLink, Lock} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {auth} from '$lib/stores/app/auth';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {instanceBlock} from '../instanceBlock.svelte';

    interface Props {
        onlogout: () => void;
        /** The details of the block, `GET /system/block`; injectable for tests. */
        fetchBlock?: () => Promise<{blocked: boolean; deletion_date?: string | null; billing_url?: string | null}>;
    }

    let {onlogout, fetchBlock = () => zodiosApi.get_instance_block_api_v1_system_block_get()}: Props = $props();

    let deletionDate = $state<string | null>(null);
    let billingUrl = $state<string | null>(null);
    const isAdmin = $derived($auth.user?.is_superuser === true);

    // The backend sends the billing address to administrators only, and only an http(s) one: checked again before it
    // becomes a link.
    function httpAddress(value: string | null | undefined): string | null {
        return value && /^https?:\/\//i.test(value) ? value : null;
    }

    // An ISO day, written in the interface locale: read at midnight UTC and formatted in UTC, so no time zone moves it.
    function formatDay(isoDay: string): string {
        return new Intl.DateTimeFormat(uiLocale(), {dateStyle: 'long', timeZone: 'UTC'}).format(new Date(`${isoDay}T00:00:00Z`));
    }

    onMount(async () => {
        try {
            const block = await fetchBlock();
            if (!block.blocked) {
                // Lifted meanwhile: start the app again from a clean page.
                instanceBlock.clear();
                window.location.reload();
                return;
            }
            deletionDate = block.deletion_date ?? null;
            billingUrl = httpAddress(block.billing_url);
        } catch {
            // The page stands without the date: the refusal that showed it is enough.
        }
    });
</script>

<div class="flex min-h-screen items-center justify-center bg-lf-page p-4" data-testid="instance-blocked">
    <section class="w-full max-w-lg rounded-2xl border border-lf-subtle bg-lf-card p-6 shadow-xl" role="alert">
        <div class="flex items-start gap-3">
            <Lock class="mt-0.5 h-6 w-6 shrink-0 text-lf-warning" aria-hidden="true" />
            <div>
                <h1 class="text-xl font-semibold text-lf-primary">{$_('instance.block.title')}</h1>
                <p class="mt-2 text-sm text-lf-secondary" data-testid="instance-blocked-description">
                    {isAdmin ? $_('instance.block.adminDescription') : $_('instance.block.userDescription')}
                </p>
                {#if deletionDate}
                    <p class="mt-3 rounded-lg border border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-sm text-lf-warning-on-soft" data-testid="instance-blocked-deletion-date">
                        {$_('instance.block.deletionDate', {values: {date: formatDay(deletionDate)}})}
                    </p>
                {/if}
            </div>
        </div>
        <div class="mt-5 flex flex-wrap items-center justify-end gap-2">
            {#if isAdmin && billingUrl}
                <a href={billingUrl} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-lf-link hover:bg-lf-hover hover:underline" data-testid="instance-blocked-billing">
                    {$_('instance.block.manageSubscription')}
                    <ExternalLink class="h-4 w-4" aria-hidden="true" />
                </a>
            {/if}
            <button type="button" class="rounded-lg px-4 py-2 text-sm text-lf-secondary hover:bg-lf-hover" onclick={onlogout} data-testid="instance-blocked-logout">
                {$_('auth.logout')}
            </button>
        </div>
    </section>
</div>
