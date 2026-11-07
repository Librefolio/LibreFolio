<!--
  A refusal of the space limit, said where the user is (C9-1): inside the dialog of the upload, the import wizard, the backup
  card. An administrator reads the limit to raise and gets «Open the settings» (Files › Advanced, its panel open); a member
  reads how much to free, or to ask an administrator. A limit the hosting provider fixes reads «ask whoever hosts it», with
  no button: nobody here can raise it.

  Published state: `data-viewer` (`admin|member`), `data-limit-locked` (`true|false`); the button is `storage-limit-open-settings`.
-->
<script lang="ts">
    import {Settings, TriangleAlert} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {auth} from '$lib/stores/app/auth';
    import {STORAGE_LIMIT_SETTINGS_HREF, storageLimitMessage, type StorageLimitNumbers, type StorageLimitViewer} from '$lib/utils/files/storageLimit';

    interface Props {
        numbers: StorageLimitNumbers;
        testId?: string;
    }

    let {numbers, testId = 'storage-limit-refusal'}: Props = $props();

    const viewer = $derived<StorageLimitViewer>($auth.user?.is_superuser ? 'admin' : 'member');
    const message = $derived(storageLimitMessage(numbers, $_, viewer));
</script>

<div class="flex flex-wrap items-start gap-3 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid={testId} data-viewer={viewer} data-limit-locked={numbers.limitLocked ? 'true' : 'false'}>
    <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
    <span class="min-w-0 flex-1">{message}</span>
    {#if viewer === 'admin' && !numbers.limitLocked}
        <a
            class="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-lf-danger-line bg-lf-card px-3 py-1.5 text-sm font-medium text-lf-primary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
            href={STORAGE_LIMIT_SETTINGS_HREF}
            data-testid="storage-limit-open-settings"
        >
            <Settings size={14} aria-hidden="true" />
            {$_('storage.limit.openSettings')}
        </a>
    {/if}
</div>
