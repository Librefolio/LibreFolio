<!--
  The backups the instance keeps (lot FB-24): a table of the finished backups on the server, with their origin, type,
  size and SHA-256, and a download and a delete for each.

  Self-contained: it reads the list when it mounts and again whenever the backup card says a backup ended or was
  deleted (`backupListSignal`), so the Backup tab of Settings and the Files page can show it as it is.

  «Restore» on a row opens `RestoreKeptModal`, here (A10).

  Published state: `data-state` (`loading` until the first list comes, `ready`, `error` after a read that failed),
  `data-busy` while a read is out. Events: `backup.list.sha.copied`, `backup.download.started`, `backup.deleted`,
  `backup.delete.failed`.
-->
<script lang="ts">
    import {onMount, untrack} from 'svelte';
    import {ArchiveRestore, Download, RefreshCw, Trash2, TriangleAlert} from 'lucide-svelte';
    import {DataTable, type ColumnDef, type RowAction} from '$lib/components/table';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {backupFailureCode, backupKind, deleteInstanceBackupJob, instanceBackupFileUrl, listInstanceBackups, type InstanceBackupEntry} from './backupApi';
    import {backupListSignal, shortHash} from './backupList.svelte';
    import RestoreKeptModal from './RestoreKeptModal.svelte';

    let entries = $state<InstanceBackupEntry[] | null>(null);
    let failed = $state(false);
    let errorCode = $state('');
    let reading = $state(0);
    // Only the answer of the latest read counts: an older one that lands late must not undo a newer list.
    let latestRead = 0;

    const listState = $derived(failed ? 'error' : entries === null ? 'loading' : 'ready');
    const rows = $derived([...(entries ?? [])].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)));

    async function load() {
        const read = ++latestRead;
        reading += 1;
        try {
            const list = await listInstanceBackups();
            if (read !== latestRead) return;
            entries = list;
            failed = false;
            errorCode = '';
        } catch (error) {
            if (read !== latestRead) return;
            failed = true;
            errorCode = backupFailureCode(error);
        } finally {
            reading -= 1;
        }
    }

    // The first read, and one more at every change of the signal.
    $effect(() => {
        void backupListSignal.version;
        untrack(() => void load());
    });

    function copyHash(entry: InstanceBackupEntry) {
        void writeTextToClipboard(entry.file_sha256 ?? '').then(
            () => notify({name: 'backup.list.sha.copied', detail: {job_id: entry.job_id}, toast: {variant: 'success', message: $_('backup.list.sha.copied')}}),
            () => undefined,
        );
    }

    function download(entry: InstanceBackupEntry) {
        // A link followed by the browser: the archive streams to disk, never through the page's memory.
        const link = document.createElement('a');
        link.href = instanceBackupFileUrl(entry.job_id);
        link.download = entry.file_name ?? '';
        document.body.appendChild(link);
        link.click();
        link.remove();
        notify({name: 'backup.download.started', detail: {job_id: entry.job_id}});
    }

    // A10 (T-15): restore a kept backup without downloading it, in a modal of its own, here (C9-9 sent it to the card).
    let restoring = $state<InstanceBackupEntry | null>(null);

    function restore(entry: InstanceBackupEntry) {
        restoring = entry;
    }

    async function remove(entry: InstanceBackupEntry) {
        try {
            await deleteInstanceBackupJob(entry.job_id);
        } catch (error) {
            const code = backupFailureCode(error);
            notify({name: 'backup.delete.failed', detail: {code, what: 'remove', job_id: entry.job_id}, toast: {variant: 'error', message: $_(`backup.download.errors.${code}`)}});
            return;
        }
        notify({name: 'backup.deleted', detail: {job_id: entry.job_id}});
        await load();
    }

    const columns: ColumnDef<InstanceBackupEntry>[] = [
        {
            id: 'date',
            header: () => $_('backup.list.columns.date'),
            cell: (row) => ({type: 'date', value: row.created_at, format: 'datetime'}),
            type: 'date',
            width: 170,
            getValue: (row) => row.created_at,
        },
        {
            id: 'origin',
            header: () => $_('backup.list.columns.origin'),
            cell: (row) => ({type: 'badge', text: $_(`backup.list.origin.${row.origin}`), variant: 'default'}),
            type: 'enum',
            enumOptions: (['ui', 'cli', 'pre-restore', 'panel'] as const).map((origin) => ({value: origin, label: $_(`backup.list.origin.${origin}`)})),
            width: 150,
            getValue: (row) => row.origin,
        },
        {
            id: 'kind',
            header: () => $_('backup.list.columns.kind'),
            cell: (row) => ({type: 'badge', text: $_(`backup.list.kind.${backupKind(row)}`), variant: backupKind(row) === 'clear' ? 'warning' : 'info'}),
            type: 'enum',
            enumOptions: (['clear', 'password', 'sealed'] as const).map((kind) => ({value: kind, label: $_(`backup.list.kind.${kind}`)})),
            width: 150,
            getValue: (row) => backupKind(row),
        },
        {
            id: 'size',
            header: () => $_('backup.list.columns.size'),
            cell: (row) => ({type: 'size', bytes: row.file_size ?? 0}),
            type: 'size',
            width: 110,
            getValue: (row) => row.file_size ?? 0,
        },
        {
            id: 'sha256',
            header: () => $_('backup.list.columns.sha256'),
            cell: (row) => ({
                type: 'html',
                html: `<code>${escapeHtml(shortHash(row.file_sha256 ?? ''))}</code>`,
                tooltip: {text: row.file_sha256 ?? ''},
                onClick: () => copyHash(row),
                testId: `backup-sha-copy-${row.job_id}`,
            }),
            type: 'text',
            filterable: false,
            sortable: false,
            width: 150,
            getValue: (row) => row.file_sha256 ?? '',
        },
    ];

    const rowActions: RowAction<InstanceBackupEntry>[] = [
        {id: 'download', icon: Download, label: () => $_('backup.list.actions.download'), onClick: download},
        // C9-9: a sealed backup opens only with its recipients' private key: it is not restored here.
        // A10: no «are you sure?» here: the modal says what a restore does, and its report asks for a typed word.
        {id: 'restore', icon: ArchiveRestore, label: () => $_('backup.list.actions.restore'), onClick: restore, visible: (row) => !row.sealed},
        {id: 'delete', icon: Trash2, label: () => $_('backup.list.actions.delete'), onClick: remove, requireConfirm: true, confirmMessage: () => $_('backup.list.deleteConfirm')},
    ];

    onMount(() => {
        latestRead = Math.max(latestRead, 0);
    });
</script>

<div data-testid="backup-list" data-state={listState} data-busy={reading > 0 ? 'true' : 'false'} aria-busy={reading > 0} class="space-y-3 text-lf-primary">
    {#if listState === 'error'}
        <div class="flex flex-wrap items-center gap-3 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="backup-list-error" data-error-code={errorCode}>
            <TriangleAlert class="shrink-0" size={16} aria-hidden="true" />
            <span class="min-w-0 flex-1">{$_('backup.list.errors.load')}</span>
            <button
                class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                type="button"
                data-testid="backup-list-retry"
                onclick={() => void load()}
            >
                <RefreshCw size={14} aria-hidden="true" />
                {$_('backup.list.retry')}
            </button>
        </div>
    {:else}
        <DataTable
            {columns}
            data={rows}
            emptyMessage={$_('backup.list.empty')}
            enableColumnVisibility={false}
            enablePagination={rows.length > 10}
            actionsLabel={$_('backup.list.columns.actions')}
            enableSelection={false}
            getRowDisplayName={(row) => row.file_name ?? row.job_id}
            getRowId={(row) => row.job_id}
            isLoading={listState === 'loading'}
            {rowActions}
            storageKey="backupList"
            tableLayout="auto"
        />
    {/if}
</div>

{#if restoring}
    <RestoreKeptModal jobId={restoring.job_id} createdAt={restoring.created_at} onClose={() => (restoring = null)} />
{/if}
