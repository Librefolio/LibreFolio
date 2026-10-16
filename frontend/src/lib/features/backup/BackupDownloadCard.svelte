<!--
  The backup card: start a backup of the whole instance, follow it, download the archive.

  Self-contained (it reads nothing from the page around it), so the Backup tab of Settings and any other admin screen
  can show it. The archive downloads through a plain link: the browser streams it to disk.

  Published state: `data-state` (`idle`, `loading`, `starting`, `running`, `done`, `deleting`, `failed`),
  `data-error-code`, `data-busy`.
  Events: `backup.created`, `backup.failed`, `backup.delete.failed`, `backup.deleted`, `backup.download.started`.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {CircleCheck, DatabaseBackup, Download, LoaderCircle, RefreshCw, ShieldAlert, Trash2, TriangleAlert} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import {formatBytes} from '$lib/utils/files/upload';
    import {instanceBackupFileUrl, type BackupPhase, type BackupWarning} from './backupApi';
    import {BackupJobController} from './backupJob.svelte';

    const PHASE_KEYS: Record<BackupPhase, string> = {
        preparing: 'backup.download.phase.preparing',
        database: 'backup.download.phase.database',
        files: 'backup.download.phase.files',
        finalizing: 'backup.download.phase.finalizing',
    };

    const WARNING_KEYS: Record<BackupWarning, string> = {
        database_integrity: 'backup.download.warnings.database_integrity',
        foreign_key_violations: 'backup.download.warnings.foreign_key_violations',
        files_skipped: 'backup.download.warnings.files_skipped',
    };

    const ERROR_KEYS: Record<string, string> = {
        backup_busy: 'backup.download.errors.backup_busy',
        backup_no_space: 'backup.download.errors.backup_no_space',
        backup_folder_unusable: 'backup.download.errors.backup_folder_unusable',
        backup_failed: 'backup.download.errors.backup_failed',
        backup_interrupted: 'backup.download.errors.backup_interrupted',
        backup_job_not_found: 'backup.download.errors.backup_job_not_found',
        network: 'backup.download.errors.network',
        unexpected: 'backup.download.errors.unexpected',
    };

    function errorKey(code: string | null): string {
        return (code !== null ? ERROR_KEYS[code] : undefined) ?? ERROR_KEYS.unexpected;
    }

    const controller = new BackupJobController({
        onDone: (job) =>
            notify({
                name: 'backup.created',
                detail: {job_id: job.job_id, file_size: job.file_size ?? null, warnings: [...job.warnings]},
                // A complete archive is visible on the card; one with warnings is partial, and says so.
                toast: job.warnings.length > 0 ? {variant: 'warning', message: $_('backup.download.toast.warnings')} : undefined,
            }),
        onFailed: (code, what, job) =>
            notify({
                name: what === 'remove' ? 'backup.delete.failed' : 'backup.failed',
                detail: {code, what, job_id: job?.job_id ?? null},
                toast: {variant: 'error', message: $_(errorKey(code))},
            }),
    });

    onMount(() => {
        void controller.resume();
        return () => controller.dispose();
    });

    const percent = $derived(controller.progress === null ? null : Math.round(controller.progress * 100));

    async function removeArchive() {
        const jobId = controller.job?.job_id;
        await controller.remove();
        if (jobId !== undefined && controller.state === 'idle') notify({name: 'backup.deleted', detail: {job_id: jobId}});
    }

    function downloadStarted(jobId: string) {
        notify({name: 'backup.download.started', detail: {job_id: jobId}});
    }
</script>

<section class="space-y-4 rounded-xl border border-lf-subtle bg-lf-panel p-4 text-lf-primary sm:p-5" data-testid="backup-download-card" data-state={controller.state} data-error-code={controller.errorCode ?? ''} data-busy={controller.busy ? 'true' : 'false'} aria-busy={controller.busy}>
    <header class="flex items-start gap-3">
        <DatabaseBackup class="mt-0.5 shrink-0 text-lf-secondary" size={22} aria-hidden="true" />
        <div class="space-y-1">
            <h3 class="text-base font-semibold text-lf-primary">{$_('backup.download.title')}</h3>
            <p class="text-sm text-lf-secondary">{$_('backup.download.description')}</p>
        </div>
    </header>

    <p class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="backup-privacy-notice">
        <ShieldAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
        <span>{$_('backup.download.privacy')}</span>
    </p>

    {#if controller.state === 'loading'}
        <p class="flex items-center gap-2 text-sm text-lf-secondary" data-testid="backup-loading">
            <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
            {$_('backup.download.checking')}
        </p>
    {/if}

    {#if controller.state === 'starting' || controller.state === 'running'}
        <div class="space-y-2" data-testid="backup-progress" data-phase={controller.job?.phase ?? ''}>
            <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span class="flex items-center gap-2 text-lf-secondary">
                    <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
                    {controller.job?.phase ? $_(PHASE_KEYS[controller.job.phase]) : $_('backup.download.creating')}
                </span>
                {#if controller.job && percent !== null}
                    <span class="tabular-nums text-lf-muted" data-testid="backup-progress-bytes">
                        {$_('backup.download.progress', {values: {done: formatBytes(controller.job.done_bytes, $_), total: formatBytes(controller.job.total_bytes, $_)}})}
                    </span>
                {/if}
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-lf-neutral" role="progressbar" aria-label={$_('backup.download.creating')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent ?? undefined}>
                {#if percent === null}
                    <div class="h-full w-1/3 animate-pulse rounded-full bg-lf-checked"></div>
                {:else}
                    <div class="h-full rounded-full bg-lf-checked transition-[width] duration-300" style:width="{percent}%"></div>
                {/if}
            </div>
        </div>
    {/if}

    {#if (controller.state === 'done' || controller.state === 'deleting') && controller.job}
        {@const job = controller.job}
        <div class="space-y-3" data-testid="backup-ready">
            <div class="flex items-start gap-2 text-sm">
                <CircleCheck class="mt-0.5 shrink-0 text-lf-success" size={16} aria-hidden="true" />
                <div class="min-w-0">
                    <p class="font-medium text-lf-primary">{$_('backup.download.ready')}</p>
                    <p class="break-all text-lf-secondary" data-testid="backup-file-details">
                        {$_('backup.download.readyDetails', {values: {name: job.file_name ?? '', size: formatBytes(job.file_size ?? 0, $_), date: formatDateTime(job.finished_at ?? job.created_at)}})}
                    </p>
                </div>
            </div>

            {#if job.warnings.length > 0}
                <div class="rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="backup-warnings">
                    <p class="flex items-center gap-2 font-medium">
                        <TriangleAlert class="shrink-0" size={16} aria-hidden="true" />
                        {$_('backup.download.warningsTitle')}
                    </p>
                    <ul class="mt-2 list-disc space-y-1 pl-6">
                        {#each job.warnings as warning (warning)}
                            <li data-testid="backup-warning" data-warning={warning}>{$_(WARNING_KEYS[warning])}</li>
                        {/each}
                    </ul>
                </div>
            {/if}

            {#if controller.state === 'deleting'}
                <p class="flex items-center gap-2 text-sm text-lf-secondary" data-testid="backup-deleting">
                    <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
                    {$_('backup.download.deleting')}
                </p>
            {:else}
                <div class="flex flex-wrap items-center gap-2">
                    <a
                        class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                        href={instanceBackupFileUrl(job.job_id)}
                        download={job.file_name ?? ''}
                        data-testid="backup-download-link"
                        onclick={() => downloadStarted(job.job_id)}
                    >
                        <Download size={16} aria-hidden="true" />
                        {$_('backup.download.download')}
                    </a>
                    <button
                        class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                        type="button"
                        data-testid="backup-delete"
                        onclick={removeArchive}
                    >
                        <Trash2 size={16} aria-hidden="true" />
                        {$_('backup.download.delete')}
                    </button>
                </div>
            {/if}
            <p class="text-xs text-lf-muted" data-testid="backup-retention">{$_('backup.download.retention')}</p>
        </div>
    {/if}

    {#if controller.errorCode !== null && (controller.state === 'failed' || controller.state === 'done')}
        <div class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="backup-error" data-error-code={controller.errorCode ?? ''}>
            <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
            <span>{$_(errorKey(controller.errorCode))}</span>
        </div>
    {/if}

    {#if !controller.busy}
        <div class="flex flex-wrap items-center gap-2">
            {#if controller.canRecheck}
                <button
                    class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                    type="button"
                    data-testid="backup-recheck"
                    onclick={() => controller.recheck()}
                >
                    <RefreshCw size={16} aria-hidden="true" />
                    {$_('backup.download.recheck')}
                </button>
            {/if}
            {#if controller.state === 'done'}
                <button
                    class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary hover:bg-lf-neutral focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                    type="button"
                    data-testid="backup-create"
                    onclick={() => controller.start()}
                >
                    <DatabaseBackup size={16} aria-hidden="true" />
                    {$_('backup.download.createAgain')}
                </button>
            {:else}
                <button
                    class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                    type="button"
                    data-testid="backup-create"
                    onclick={() => controller.start()}
                >
                    <DatabaseBackup size={16} aria-hidden="true" />
                    {controller.state === 'failed' ? $_('backup.download.retry') : $_('backup.download.create')}
                </button>
            {/if}
        </div>
    {/if}
</section>
