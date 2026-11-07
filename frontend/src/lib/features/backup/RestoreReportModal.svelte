<!--
  The report of a checked archive: what a restore would do, and its confirmation (lot B5b). Developer decision P8: a real
  word of the interface language, picked at random, typed by hand: paste and drop are refused on the field.

  Every value read from the archive (version, names, migration messages, currencies) is shown as text, never as markup.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {CircleCheck, CircleX, Database, FileArchive, HardDrive, KeyRound, LoaderCircle, ShieldAlert, TriangleAlert, Users, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {_} from '$lib/i18n';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import {formatBytes} from '$lib/utils/files/upload';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import LinkedStackedBar from '$lib/components/ui/display/LinkedStackedBar.svelte';
    import type {LinkedSegment} from '$lib/components/ui/display/linkedStackedBar';
    import {restoreAdminAvatarUrl} from './backupApi';
    import type {RestoreStageReport} from './backupApi';
    import OwnerChoiceModal, {type OwnerCandidate} from './OwnerChoiceModal.svelte';
    import {confirmationMatches, confirmationWords, pickConfirmationWord} from './restoreFlow.svelte';
    import {WARNINGS_SHOWN_APART, restoreTotalsKey, restoreWarningKey} from './restoreText';

    interface Props {
        open: boolean;
        report: RestoreStageReport;
        /** The confirmation is out: nothing can be clicked. */
        busy?: boolean;
        /** `ownerUserId`: the account the owner chose (B5-1), `null` when the report asks for none. */
        onConfirm: (ownerUserId: number | null) => void;
        onDrop: () => void;
        /** «I'll decide later» (C9-6): the report closes, its check stays on the server. Without it, no such button. */
        onLater?: () => void;
        /** The check this report is of: the avatars of the backup's administrators are read from its copy (C9-10). */
        stageId?: string | null;
        /** C9-8: whether a password is the one an administrator of the backup signs in with after the restore. Without it,
         * no such check. */
        onVerify?: (username: string, password: string) => Promise<boolean>;
        onClose: () => void;
        /** Where the word is picked: a test fixes it. */
        random?: () => number;
    }

    let {open, report, busy = false, onConfirm, onDrop, onLater, onClose, stageId = null, onVerify, random = Math.random}: Props = $props();

    let typed = $state('');
    // Picked once, when the report opens: the same word while it stays open (a change of language picks in the new list).
    const seed = untrack(() => random());
    const word = $derived(pickConfirmationWord(confirmationWords($_('backup.restore.confirm.words')), () => seed));
    // The server says whether the archive can be restored; a blocker (an archive with no administrator) stops it here too.
    const BYTES_PER_MB = 1024 * 1024;

    // C8: the data after the restore would pass the space limit: what to raise (or whom to ask) and, when the disk lacks room
    // for it, how much more it needs free. The numbers come from the check's report, in the interface's language.
    const storageLimitBlocker = $derived.by(() => {
        const required = formatBytes(Math.ceil((report.storage_required_bytes ?? 0) / BYTES_PER_MB) * BYTES_PER_MB, $_);
        const missing = formatBytes(report.storage_disk_missing_bytes ?? 0, $_);
        const sentence = $_(report.storage_limit_locked ? 'backup.restore.blocker.storage_limit_locked' : 'backup.restore.blocker.storage_limit', {values: {required}});
        return (report.storage_disk_missing_bytes ?? 0) > 0 ? `${sentence} ${$_('backup.restore.blocker.storage_limit_disk', {values: {missing}})}` : sentence;
    });
    const confirmable = $derived(report.restorable && report.blockers.length === 0);
    const canConfirm = $derived(!busy && confirmable && confirmationMatches(typed, word));
    const changedTables = $derived(Object.entries(report.tables).filter(([, rows]) => (rows.before ?? 0) !== (rows.after ?? 0)));
    const hiddenDifferences = $derived(Math.max(0, report.control_totals_differences_count - report.control_totals_differences.length));
    // Decision 39: the saved keys of the data providers this instance cannot read, to enter again after the restore.
    const unreadableSecrets = $derived(report.secrets_unreadable.system + report.secrets_unreadable.user);
    // L3: «sign in with the backup's credentials» is the sentence under the administrators; the account that reads the
    // report missing from the backup is a red notice of its own. Neither is a line of the warnings box.
    const listedWarnings = $derived(report.warnings.filter((warning) => !WARNINGS_SHOWN_APART.has(warning)));
    const ownAccountMissing = $derived(report.warnings.includes('confirming_account_not_in_backup'));
    // B5-1k2: more active accounts than the instance accepts is said, never refused: the administrator chooses at the first sign-in.
    const usersOverLimit = $derived((report.users_over_limit ?? 0) > 0);

    // B5-1: on a managed instance the confirmation names the backup's account that becomes the owner's. Offered: the one
    // with the owner's address when there is one, otherwise the backup's active administrators.
    const ownerChoice = $derived(report.owner_choice ?? null);
    const ownerUsers = $derived.by((): OwnerCandidate[] => {
        if (ownerChoice === null) return [];
        const forced = ownerChoice.forced_user_id;
        const offered = ownerChoice.candidates.filter((candidate) => (forced !== null ? candidate.user_id === forced : candidate.administrator));
        return offered.map((candidate) => ({id: candidate.user_id, username: candidate.username, email: candidate.email ?? '', is_superuser: candidate.is_superuser, is_active: candidate.is_active}));
    });
    let ownerOpen = $state(false);

    function confirm() {
        if (!canConfirm) return;
        if (ownerChoice === null) onConfirm(null);
        else ownerOpen = true;
    }

    function confirmOwner(userId: number) {
        ownerOpen = false;
        onConfirm(userId);
    }

    const REFUSED_INPUT = new Set(['insertFromPaste', 'insertFromPasteAsQuotation', 'insertFromDrop']);

    /** The word is typed: what is pasted or dropped is refused. */
    function refuse(event: Event) {
        event.preventDefault();
    }

    function refusePasted(event: InputEvent) {
        if (REFUSED_INPUT.has(event.inputType)) event.preventDefault();
    }

    // --- C9-8: a password tried against an administrator of the backup --------------------------------------------------
    type VerifyState = 'idle' | 'checking' | 'match' | 'mismatch' | 'failed';
    let verifyUser = $state('');
    let verifyPassword = $state('');
    let verifyState = $state<VerifyState>('idle');
    const canVerify = $derived(onVerify !== undefined && report.administrators.length > 0 && !report.blockers.includes('storage_limit'));
    $effect(() => {
        if (verifyUser === '' && report.administrators.length > 0) verifyUser = report.administrators[0];
    });

    async function verify() {
        if (onVerify === undefined || verifyUser === '' || verifyPassword === '' || verifyState === 'checking') return;
        const password = verifyPassword;
        verifyState = 'checking';
        try {
            verifyState = (await onVerify(verifyUser, password)) ? 'match' : 'mismatch';
        } catch {
            verifyState = 'failed';
        }
    }

    // --- C9-10: the avatars and what the backup holds -----------------------------------------------------------------
    const brokenAvatars = $state<Record<string, boolean>>({});
    const partsFill: Record<string, string> = {database: 'bg-lf-brand', uploads: 'bg-lf-info', brokerReports: 'bg-lf-success', dataOther: 'bg-lf-checked'};
    const parts = $derived.by((): LinkedSegment[] => {
        const other = Math.max(0, report.files_size - (report.uploads_size ?? 0) - (report.broker_reports_size ?? 0));
        const sizes: Array<[string, number]> = [
            ['database', report.database_size],
            ['uploads', report.uploads_size ?? 0],
            ['brokerReports', report.broker_reports_size ?? 0],
            ['dataOther', other],
        ];
        const total = sizes.reduce((sum, [, bytes]) => sum + bytes, 0);
        return sizes.filter(([, bytes]) => bytes > 0).map(([id, bytes]) => ({id, percent: total > 0 ? Math.round((bytes / total) * 10000) / 100 : 0, fill: partsFill[id], attrs: {'data-bytes': bytes}}));
    });
</script>

<ModalBase {open} maxWidth="2xl" onRequestClose={onClose} testId="restore-report" labelledBy="restore-report-title" trapFocus restoreFocus>
    <div class="max-h-[85vh] space-y-4 overflow-y-auto p-5 text-lf-primary" data-restorable={report.restorable ? 'true' : 'false'} data-action={report.action}>
        <header class="flex items-start justify-between gap-3">
            <div class="flex items-start gap-3">
                <FileArchive class="mt-0.5 shrink-0 text-lf-secondary" size={22} aria-hidden="true" />
                <div class="space-y-1">
                    <h2 id="restore-report-title" class="text-base font-semibold text-lf-primary">{$_('backup.restore.report.title')}</h2>
                    <p class="text-sm text-lf-secondary" data-testid="restore-report-backup">
                        {$_('backup.restore.report.madeBy', {values: {version: report.backup_app_version, date: formatDateTime(report.backup_created_at)}})}
                    </p>
                </div>
            </div>
            <button class="rounded-lg p-1 text-lf-muted hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus" type="button" aria-label={$_('backup.restore.report.close')} data-testid="restore-report-close" onclick={onClose}>
                <X size={18} aria-hidden="true" />
            </button>
        </header>

        <section class="space-y-2 text-sm" data-testid="restore-report-migrations" data-count={report.migrations.length}>
            <p class="flex items-start gap-2">
                <Database class="mt-0.5 shrink-0 text-lf-secondary" size={16} aria-hidden="true" />
                <span>{report.action === 'same' ? $_('backup.restore.report.same') : $_('backup.restore.report.upgrade', {values: {count: report.migrations.length}})}</span>
            </p>
            {#if report.migrations.length > 0}
                <ul class="list-disc space-y-1 pl-10 text-lf-secondary">
                    {#each report.migrations as migration (migration.revision)}
                        <li data-testid="restore-report-migration" data-revision={migration.revision}><span class="font-mono text-xs">{migration.revision}</span> {migration.message}</li>
                    {/each}
                </ul>
            {/if}
            {#if report.post_migration_fixes.length > 0}
                <p class="text-lf-secondary" data-testid="restore-report-fixes">{$_('backup.restore.report.fixes', {values: {fixes: report.post_migration_fixes.join(', ')}})}</p>
            {/if}
        </section>

        <section class="space-y-1 text-sm text-lf-secondary" data-testid="restore-report-tables" data-count={changedTables.length}>
            <p>{$_('backup.restore.report.contents', {values: {files: report.files, filesSize: formatBytes(report.files_size, $_), databaseSize: formatBytes(report.database_size, $_)}})}</p>
            {#if parts.length > 0}
                <!-- C9-10: what the backup holds, as the space bar of Files draws the instance. -->
                <div class="space-y-1 pt-1" data-testid="restore-report-parts">
                    <p class="text-xs font-medium text-lf-muted">{$_('backup.restore.report.partsTitle')}</p>
                    <LinkedStackedBar
                        segments={parts}
                        barClass="flex h-2.5 w-full overflow-hidden rounded-full border border-lf-subtle bg-lf-field"
                        legendClass="grid gap-x-4 gap-y-0.5 text-xs text-lf-secondary sm:grid-cols-2"
                        itemClass="rounded-md px-1 py-0.5"
                        testIds={{bar: 'restore-report-parts-bar', segment: (id) => `restore-report-part-${id}`, item: (id) => `restore-report-part-legend-${id}`}}
                    >
                        {#snippet row(segment)}
                            <span class="min-w-0 flex-1">{$_(`storage.parts.${segment.id}`)}</span>
                            <span class="tabular-nums text-lf-primary">{formatBytes(Number(segment.attrs?.['data-bytes'] ?? 0), $_)}</span>
                        {/snippet}
                    </LinkedStackedBar>
                </div>
            {/if}
            {#if changedTables.length > 0}
                <p>{$_('backup.restore.report.tablesChanged')}</p>
                <ul class="list-disc space-y-1 pl-6">
                    {#each changedTables as [name, rows] (name)}
                        <li data-testid="restore-report-table" data-table={name}><span class="font-mono text-xs">{name}</span> {rows.before ?? '—'} → {rows.after ?? '—'}</li>
                    {/each}
                </ul>
            {/if}
            <p class="flex items-center gap-2" data-testid="restore-report-key" data-included={report.instance_key_included ? 'true' : 'false'}>
                <KeyRound class="shrink-0" size={14} aria-hidden="true" />
                {report.instance_key_included ? $_('backup.restore.report.keyIncluded') : $_('backup.restore.report.keyNotIncluded')}
            </p>
            {#if report.secrets_rekeyed > 0}
                <p class="flex items-start gap-2" data-testid="restore-report-secrets-rekeyed" data-count={report.secrets_rekeyed}>
                    <KeyRound class="mt-0.5 shrink-0" size={14} aria-hidden="true" />
                    <span>{$_('backup.restore.report.secretsRekeyed', {values: {count: report.secrets_rekeyed}})}</span>
                </p>
            {/if}
            {#if unreadableSecrets > 0}
                <p class="flex items-start gap-2 text-lf-warning" data-testid="restore-report-secrets-unreadable" data-count={unreadableSecrets}>
                    <TriangleAlert class="mt-0.5 shrink-0" size={14} aria-hidden="true" />
                    <span>{$_('backup.restore.report.secretsUnreadable', {values: {count: unreadableSecrets}})}</span>
                </p>
            {/if}
        </section>

        <section class="space-y-1 text-sm" data-testid="restore-report-totals" data-status={report.control_totals}>
            <p class={report.control_totals === 'changed' || report.control_totals === 'unreadable' ? 'text-lf-warning' : 'text-lf-secondary'}>{$_(restoreTotalsKey(report.control_totals), {values: {count: report.control_totals_differences_count}})}</p>
            {#if report.control_totals === 'changed'}
                <ul class="list-disc space-y-1 pl-6 text-lf-secondary">
                    {#each report.control_totals_differences as line, index (index)}
                        <li data-testid="restore-report-totals-line" data-kind={line.kind}>
                            {line.kind === 'cash'
                                ? $_('backup.restore.report.totals.cashLine', {values: {broker: line.broker_id, currency: line.currency ?? '', before: line.before ?? '—', after: line.after ?? '—'}})
                                : $_('backup.restore.report.totals.quantityLine', {values: {broker: line.broker_id, asset: line.asset_id ?? '', before: line.before ?? '—', after: line.after ?? '—'}})}
                        </li>
                    {/each}
                </ul>
                {#if hiddenDifferences > 0}
                    <p class="text-lf-muted" data-testid="restore-report-totals-more" data-more={hiddenDifferences}>{$_('backup.restore.report.totals.more', {values: {count: hiddenDifferences}})}</p>
                {/if}
            {/if}
        </section>

        {#if report.administrators.length > 0}
            <section class="space-y-1 text-sm" data-testid="restore-report-admins" data-count={report.administrators.length}>
                <p class="flex items-start gap-2">
                    <Users class="mt-0.5 shrink-0 text-lf-secondary" size={16} aria-hidden="true" />
                    <span>{$_('backup.restore.report.admins', {values: {names: report.administrators.join(', ')}})}</span>
                </p>
                <p class="text-lf-secondary">{$_('backup.restore.report.signInAgain')}</p>
                {#if stageId}
                    <!-- C9-10: each administrator with the avatar of the backup's copy; the name stays text, for the eye and the screen reader. -->
                    <ul class="flex flex-wrap gap-2 pt-1" data-testid="restore-report-admin-list">
                        {#each report.administrators as name (name)}
                            <li class="inline-flex items-center gap-2 rounded-full border border-lf-subtle bg-lf-panel py-1 pl-1 pr-3 text-sm text-lf-primary" data-testid="restore-report-admin" data-username={name}>
                                {#if brokenAvatars[name]}
                                    <span class="inline-flex h-6 w-6 items-center justify-center rounded-full bg-lf-neutral text-xs font-semibold text-lf-secondary" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</span>
                                {:else}
                                    <img class="h-6 w-6 rounded-full object-cover" src={restoreAdminAvatarUrl(stageId, name)} alt="" width="24" height="24" onerror={() => (brokenAvatars[name] = true)} data-testid="restore-report-admin-avatar" />
                                {/if}
                                <span>{name}</span>
                            </li>
                        {/each}
                    </ul>
                {/if}
            </section>
        {/if}

        {#if canVerify}
            <!-- C9-8: the password an administrator of the backup signs in with after the restore, tried before confirming. -->
            <section class="space-y-2 rounded-lg border border-lf-subtle p-3 text-sm" data-testid="restore-verify" data-state={verifyState}>
                <p class="flex items-center gap-2 font-medium text-lf-primary">
                    <KeyRound class="shrink-0 text-lf-secondary" size={16} aria-hidden="true" />
                    {$_('backup.restore.verify.title')}
                </p>
                <div class="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end">
                    <label class="space-y-1">
                        <span class="block text-xs font-medium text-lf-secondary">{$_('backup.restore.verify.admin')}</span>
                        <select class="w-full rounded-lg border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary focus:border-lf-focus focus:outline-none focus:ring-1 focus:ring-lf-focus" bind:value={verifyUser} onchange={() => (verifyState = 'idle')} data-testid="restore-verify-user">
                            {#each report.administrators as name (name)}
                                <option value={name}>{name}</option>
                            {/each}
                        </select>
                    </label>
                    <div class="space-y-1">
                        <label class="block text-xs font-medium text-lf-secondary" for="restore-verify-password">{$_('backup.restore.verify.password')}</label>
                        <PasswordInput neverSaved bind:value={verifyPassword} id="restore-verify-password" name="restore-verify-password" testId="restore-verify-password" on:input={() => (verifyState = 'idle')} />
                    </div>
                    <button
                        class="inline-flex items-center justify-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm font-medium text-lf-primary enabled:hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                        type="button"
                        disabled={verifyPassword === '' || verifyState === 'checking' || busy}
                        data-testid="restore-verify-button"
                        onclick={() => void verify()}
                    >
                        {#if verifyState === 'checking'}<LoaderCircle class="animate-spin" size={16} aria-hidden="true" />{/if}
                        {$_('backup.restore.verify.button')}
                    </button>
                </div>
                {#if verifyState === 'match'}
                    <p class="flex items-center gap-2 text-lf-success" role="status" data-testid="restore-verify-result" data-result="match"><CircleCheck size={16} aria-hidden="true" />{$_('backup.restore.verify.match')}</p>
                {:else if verifyState === 'mismatch'}
                    <p class="flex items-center gap-2 text-lf-danger" role="status" data-testid="restore-verify-result" data-result="mismatch"><CircleX size={16} aria-hidden="true" />{$_('backup.restore.verify.mismatch')}</p>
                {:else if verifyState === 'failed'}
                    <p class="flex items-center gap-2 text-lf-danger" role="alert" data-testid="restore-verify-result" data-result="failed"><TriangleAlert size={16} aria-hidden="true" />{$_('backup.restore.verify.failed')}</p>
                {/if}
            </section>
        {/if}

        <!-- Developer decision P11: one notice on the invitations and links, nothing more. -->
        <p class="text-sm text-lf-secondary" data-testid="restore-report-links">{$_('backup.restore.report.linksExpired')}</p>

        {#if ownAccountMissing}
            <p class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="restore-report-own-account">
                <ShieldAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{$_('backup.restore.report.ownAccountMissing')}</span>
            </p>
        {/if}

        {#if usersOverLimit}
            <p class="flex items-start gap-2 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" role="note" data-testid="restore-users-over-limit">
                <Users class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{$_('backup.restore.report.usersOverLimit', {values: {active: report.users_active ?? 0, limit: report.users_limit ?? null}})}</span>
            </p>
        {/if}

        {#if listedWarnings.length > 0}
            <div class="rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-sm text-lf-warning-on-soft" data-testid="restore-report-warnings">
                <p class="flex items-center gap-2 font-medium">
                    <TriangleAlert class="shrink-0" size={16} aria-hidden="true" />
                    {$_('backup.restore.report.warningsTitle')}
                </p>
                <ul class="mt-2 list-disc space-y-1 pl-6">
                    {#each listedWarnings as warning (warning)}
                        <li data-testid="restore-report-warning" data-warning={warning}>{$_(restoreWarningKey(warning))}</li>
                    {/each}
                </ul>
            </div>
        {/if}

        {#if report.blockers.includes('storage_limit')}
            <p class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="restore-report-blocker" data-blocker="storage_limit" data-limit-locked={report.storage_limit_locked ? 'true' : 'false'}>
                <HardDrive class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{storageLimitBlocker}</span>
            </p>
        {/if}

        {#if report.blockers.includes('no_administrator')}
            <p class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="restore-report-blocker" data-blocker="no_administrator">
                <ShieldAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{$_('backup.restore.blocker.no_administrator')}</span>
            </p>
        {/if}

        {#if !report.blockers.includes('storage_limit')}
            <!-- A check refused by the space limit gave its archive's room back at once (C9-5): nothing is kept to expire. -->
            <p class="text-xs text-lf-muted" data-testid="restore-report-expiry">{$_('backup.restore.report.expires', {values: {date: formatDateTime(report.expires_at)}})}</p>
        {/if}

        <!-- C9-5: with a blocker nothing can be confirmed: neither the word nor «Restore and restart» is drawn. -->
        {#if report.blockers.length === 0}
            <div class="space-y-2 border-t border-lf-subtle pt-4">
                <p class="flex items-start gap-2 text-sm text-lf-primary">
                    <CircleCheck class={confirmable ? 'mt-0.5 shrink-0 text-lf-success' : 'mt-0.5 shrink-0 text-lf-muted'} size={16} aria-hidden="true" />
                    <span>{$_('backup.restore.confirm.instruction')}</span>
                </p>
                <p class="select-none text-center font-mono text-lg font-semibold tracking-widest text-lf-primary" data-testid="restore-confirm-word">{word}</p>
                <input
                    class="w-full rounded-lg border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:border-lf-focus focus:outline-none focus:ring-1 focus:ring-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    aria-label={$_('backup.restore.confirm.label')}
                    bind:value={typed}
                    disabled={busy || !confirmable}
                    data-testid="restore-confirm-input"
                    onpaste={refuse}
                    ondrop={refuse}
                    onbeforeinput={refusePasted}
                    onkeydown={(event) => {
                        if (event.key === 'Enter') confirm();
                    }}
                />
            </div>
        {/if}

        <footer class="flex flex-wrap items-center justify-end gap-2">
            <button
                class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary enabled:hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                disabled={busy}
                data-testid="restore-drop"
                onclick={onDrop}
            >
                {$_('backup.restore.report.drop')}
            </button>
            {#if onLater && !report.blockers.includes('storage_limit')}
                <button
                    class="inline-flex items-center gap-2 rounded-lg border border-lf-subtle px-4 py-2 text-sm text-lf-secondary enabled:hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                    type="button"
                    disabled={busy}
                    data-testid="restore-later"
                    onclick={onLater}
                >
                    {$_('backup.restore.report.later')}
                </button>
            {/if}
            {#if report.blockers.length === 0}
                <button
                    class="inline-flex items-center gap-2 rounded-lg bg-lf-danger-solid px-4 py-2 text-sm font-medium text-lf-on-danger-solid enabled:hover:bg-lf-danger-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                    type="button"
                    disabled={!canConfirm}
                    data-testid="restore-confirm"
                    onclick={confirm}
                >
                    {$_('backup.restore.confirm.button')}
                </button>
            {/if}
        </footer>
    </div>
</ModalBase>

{#if ownerChoice !== null}
    <OwnerChoiceModal open={open && ownerOpen} ownerEmail={ownerChoice.owner_email} users={ownerUsers} {busy} onConfirm={confirmOwner} onCancel={() => (ownerOpen = false)} />
{/if}
