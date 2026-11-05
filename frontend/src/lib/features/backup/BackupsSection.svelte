<!--
  The backups the instance keeps (lot FB-24): the table of the backups on the server, the automatic clean-up that
  bounds them, and the reminder that a copy on the same disk as the data is not a real backup.

  Shown under the backup card of Settings › Administration › Backup (foldable, remembered) and in the Files page's
  Backup tab (always open). Administrators only: both places already are.

  Published state: `data-open` (`true|false`); the toggle `backups-section-toggle` carries `aria-expanded`.
-->
<script lang="ts">
    import {ChevronDown, ChevronRight, HardDrive, TriangleAlert} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';
    import BackupCleanupPanel from './BackupCleanupPanel.svelte';
    import BackupList from './BackupList.svelte';

    interface Props {
        /** The body folds (default), or it is always open. */
        collapsible?: boolean;
        /** Open when nobody chose yet (default: open). */
        defaultOpen?: boolean;
    }

    const STORAGE_KEY = 'backupsSection_open';

    let {collapsible = true, defaultOpen = true}: Props = $props();

    // The user's last choice is read before the first paint: a section left closed never mounts its list.
    function initialOpen(): boolean {
        if (!collapsible) return true;
        const remembered = getUserStorage(STORAGE_KEY, String(defaultOpen));
        return remembered === 'true';
    }

    let open = $state(initialOpen());

    function toggle() {
        open = !open;
        setUserStorage(STORAGE_KEY, String(open));
    }
</script>

<section class="space-y-4 rounded-xl border border-lf-subtle bg-lf-panel p-4 text-lf-primary sm:p-5" data-testid="backups-section" data-open={open ? 'true' : 'false'}>
    <header class="flex items-start gap-3">
        <HardDrive class="mt-0.5 shrink-0 text-lf-secondary" size={22} aria-hidden="true" />
        <div class="min-w-0 flex-1 space-y-1">
            <h3 class="text-base font-semibold text-lf-primary">{$_('backup.list.title')}</h3>
            <p class="text-sm text-lf-secondary">{$_('backup.list.description')}</p>
        </div>
        {#if collapsible}
            <button
                class="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-lf-subtle px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                type="button"
                data-testid="backups-section-toggle"
                aria-expanded={open}
                onclick={toggle}
            >
                {#if open}
                    <ChevronDown size={16} aria-hidden="true" />
                    {$_('backup.list.hide')}
                {:else}
                    <ChevronRight size={16} aria-hidden="true" />
                    {$_('backup.list.show')}
                {/if}
            </button>
        {/if}
    </header>

    {#if open}
        <p class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="backup-same-disk-warning">
            <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
            <span>{$_('backup.list.sameDisk')}</span>
        </p>
        <BackupList />
        <BackupCleanupPanel />
    {/if}
</section>
