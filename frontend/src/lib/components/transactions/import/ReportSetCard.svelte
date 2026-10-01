<!--
  ReportSetCard.svelte — one report set in the import wizard's file selection (step 2).

  A report-set plugin imports several exports of the same bank as one: the files uploaded
  together for a broker and recognised by the plugin form a set (design D-S22). The set is one
  row with its card: the files by role and the period each covers, what is missing and for
  which period, the plugin's notices, the broker history LibreFolio already holds, and the
  actions that make the set importable — upload the missing export into the same set, or
  exclude the set from this import.

  Everything is rendered as Svelte text: file names and plugin notices are user/provider data.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ChevronDown, ChevronRight, Eye, FileText, Layers, Trash2, Upload, ExternalLink, AlertTriangle, Info} from 'lucide-svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import {buildSetTimeline, dayBefore, parseIsoPeriod, type ReportSetGroup, type SetFileInfo, type SetPluginInfo, type SetPreviewState, type SetRoleInfo} from '$lib/utils/transactions/importReportSets';
    import type {BrimSetPreview} from '$lib/types';

    interface Props {
        set: ReportSetGroup;
        plugin: SetPluginInfo | null;
        previewState: (SetPreviewState & {preview?: BrimSetPreview | null}) | undefined;
        selection: 'all' | 'some' | 'none';
        expanded: boolean;
        /** A combined file of this set has already been parsed. */
        analysed: boolean;
        /** The role whose missing export is being uploaded, or null. */
        uploadingRole: string | null;
        onToggleSelected: () => void;
        onToggleExpanded: () => void;
        onUploadMissing: (roleCode: string, file: globalThis.File) => void;
        onExclude: () => void;
        onPreviewFile: (fileId: string) => void;
        onDeleteFile: (file: SetFileInfo) => void;
    }

    let {set, plugin, previewState, selection, expanded, analysed, uploadingRole, onToggleSelected, onToggleExpanded, onUploadMissing, onExclude, onPreviewFile, onDeleteFile}: Props = $props();

    let preview = $derived(previewState?.preview ?? null);
    let status = $derived<'loading' | 'complete' | 'incomplete' | 'error'>(!previewState || previewState.status === 'loading' ? 'loading' : previewState.status === 'error' ? 'error' : previewState.preview?.complete ? 'complete' : 'incomplete');
    let roles = $derived<SetRoleInfo[]>(plugin?.report_roles ?? []);
    let missingByRole = $derived(new Map((preview?.missing ?? []).map((item) => [item.role, item])));
    let blocks = $derived(selection !== 'none' && status !== 'complete');
    let unrecognised = $derived((preview?.members ?? []).filter((member) => !member.role));
    let timeline = $derived(
        preview
            ? buildSetTimeline(
                  {
                      members: (preview.members ?? []).map((member) => ({file_id: member.file_id, role: member.role ?? null, coverage: (member.coverage ?? []).map((c) => ({axis: c.axis, start: String(c.start), end: String(c.end)}))})),
                      history_start: preview.history_start ? String(preview.history_start) : null,
                  },
                  roles.map((role) => role.code),
              )
            : null,
    );

    /** The history note: a first import gets the opening proposal, a later one the duplicates warning. */
    let history = $derived.by<{kind: 'first' | 'later'; date: string} | null>(() => {
        if (!preview) return null;
        if (preview.history_start) return {kind: 'later', date: String(preview.history_start)};
        const segments = preview.segments ?? [];
        if (segments.length === 0) return null;
        // The opening checkpoint is the eve of the first segment, or of the first day the
        // balance-providing exports cover when they start later (design A13).
        let start = String(segments[0].start);
        for (const role of roles.filter((r) => r.must_cover)) {
            for (const member of (preview.members ?? []).filter((m) => m.role === role.code)) {
                for (const coverage of member.coverage ?? []) {
                    if (String(coverage.start) > start) start = String(coverage.start);
                }
            }
        }
        return {kind: 'first', date: dayBefore(start)};
    });

    const inputs: Record<string, HTMLInputElement | undefined> = $state({});

    /** `indeterminate` is a DOM property, not an attribute: a partly selected set shows the dash. */
    function indeterminate(node: HTMLInputElement, value: boolean) {
        node.indeterminate = value;
        return {
            update(next: boolean) {
                node.indeterminate = next;
            },
        };
    }

    function formatDay(iso: string | null | undefined): string {
        if (!iso) return '—';
        const day = String(iso).slice(0, 10);
        const [year, month, date] = day.split('-').map(Number);
        if (!year || !month || !date) return day;
        return new Date(Date.UTC(year, month - 1, date)).toLocaleDateString(undefined, {timeZone: 'UTC', year: 'numeric', month: '2-digit', day: '2-digit'});
    }

    function translateOr(key: string, fallback: string, values?: Record<string, unknown>): string {
        const translated = $t(key, values ? {values: values as Record<string, string | number | boolean | Date | null | undefined>} : undefined);
        return translated === key ? fallback : translated;
    }

    function roleName(role: SetRoleInfo | undefined, code: string): string {
        return translateOr(`importWizard.reportSet.roleName.${code}`, role?.description ?? code);
    }

    function extensionsLabel(role: SetRoleInfo | undefined): string {
        return (role?.extensions ?? []).map((ext) => ext.replace(/^\./, '').toUpperCase()).join(', ');
    }

    function maxHistoryLabel(role: SetRoleInfo): string | null {
        const period = parseIsoPeriod(role.max_history);
        if (!period) return null;
        const parts: string[] = [];
        if (period.years) parts.push($t('importWizard.reportSet.period.years', {values: {n: period.years}}));
        if (period.months) parts.push($t('importWizard.reportSet.period.months', {values: {n: period.months}}));
        if (period.days) parts.push($t('importWizard.reportSet.period.days', {values: {n: period.days}}));
        return parts.length ? $t('importWizard.reportSet.maxHistory', {values: {period: parts.join(' ')}}) : null;
    }

    function membersOf(code: string) {
        return (preview?.members ?? []).filter((member) => member.role === code);
    }

    function fileOf(fileId: string): SetFileInfo | undefined {
        return set.files.find((file) => file.file_id === fileId);
    }

    /** Notice context, with role codes named and ISO dates shown in the user's format. */
    function noticeValues(context: Record<string, unknown> | null | undefined): Record<string, unknown> {
        const values: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(context ?? {})) {
            if ((key === 'role' || key === 'covered_role') && typeof value === 'string')
                values[key] = roleName(
                    roles.find((role) => role.code === value),
                    value,
                );
            else values[key] = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? formatDay(value) : value;
        }
        return values;
    }

    function pickFile(roleCode: string, event: Event) {
        const input = event.currentTarget as HTMLInputElement;
        const file = input.files?.[0];
        if (file) onUploadMissing(roleCode, file);
        input.value = '';
    }

    const statusClass: Record<string, string> = {
        loading: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-300',
        complete: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
        incomplete: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
        error: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    };
</script>

<div
    class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-900"
    data-testid="report-set-card"
    data-set-key={set.key}
    data-batch-id={set.batchId}
    data-plugin-code={set.pluginCode}
    data-set-status={status}
    data-selected={selection}
    data-analysed={analysed ? 'true' : 'false'}
    data-busy={status === 'loading' || uploadingRole !== null ? 'true' : 'false'}
>
    <div class="flex items-center gap-2 px-3 py-2">
        <input
            type="checkbox"
            class="h-4 w-4 rounded border-gray-300 text-libre-green focus:ring-libre-green dark:border-gray-600"
            checked={selection === 'all'}
            use:indeterminate={selection === 'some'}
            onchange={onToggleSelected}
            aria-label={$t('importWizard.reportSet.selectSet')}
            data-testid="report-set-select"
        />
        <button type="button" class="flex min-w-0 flex-1 items-center gap-2 text-left" onclick={onToggleExpanded} aria-expanded={expanded} data-testid="report-set-toggle">
            {#if expanded}
                <ChevronDown size={14} class="shrink-0 text-gray-400" />
            {:else}
                <ChevronRight size={14} class="shrink-0 text-gray-400" />
            {/if}
            <Layers size={14} class="shrink-0 text-libre-green" />
            <span class="truncate text-sm font-medium text-gray-800 dark:text-gray-200">{$t('importWizard.reportSet.setLabel', {values: {date: formatDay(set.uploadedAt), plugin: plugin?.name ?? set.pluginCode}})}</span>
            <span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">{$t('importWizard.reportSet.fileCount', {values: {n: set.files.length}})}</span>
        </button>
        {#if analysed}
            <span class="shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">{$t('importWizard.reportSet.status.analysed')}</span>
        {/if}
        <span class="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium {statusClass[status]}">
            {#if status === 'loading'}
                <LoadingSpinner size="sm" />
                {$t('importWizard.reportSet.status.loading')}
            {:else if status === 'complete'}
                {$t('importWizard.reportSet.status.complete')}
            {:else if status === 'error'}
                {$t('importWizard.reportSet.status.error')}
            {:else if missingByRole.size > 0}
                {$t('importWizard.reportSet.status.missing')}
            {:else}
                {$t('importWizard.reportSet.status.incomplete')}
            {/if}
        </span>
    </div>

    {#if expanded}
        <div class="space-y-3 border-t border-gray-100 px-4 py-3 text-sm dark:border-gray-800">
            {#if status === 'error'}
                <p class="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400"><AlertTriangle size={14} />{previewState?.error ?? $t('common.error')}</p>
            {/if}

            {#each roles as role (role.code)}
                {@const missing = missingByRole.get(role.code)}
                <div class="space-y-1">
                    <div class="flex flex-wrap items-baseline gap-x-2 text-xs font-medium text-gray-600 dark:text-gray-300">
                        <span>{roleName(role, role.code)}</span>
                        <span class="text-gray-400">· {extensionsLabel(role)}</span>
                        {#if maxHistoryLabel(role)}
                            <span class="font-normal text-gray-400">· {maxHistoryLabel(role)}</span>
                        {/if}
                    </div>
                    {#each membersOf(role.code) as member (member.file_id)}
                        {@const coverage = member.coverage?.[0]}
                        <div class="flex items-center gap-2 pl-3 text-xs text-gray-700 dark:text-gray-300" data-testid="report-set-member" data-file-id={member.file_id} data-role={role.code}>
                            <FileText size={12} class="shrink-0 text-gray-400" />
                            <span class="min-w-0 flex-1 truncate" title={member.filename}>{member.filename}</span>
                            {#if coverage}
                                <span class="shrink-0 tabular-nums text-gray-500">{formatDay(String(coverage.start))} → {formatDay(String(coverage.end))}</span>
                            {/if}
                            <span class="shrink-0 text-gray-400">{$t('importWizard.reportSet.rows', {values: {n: member.rows ?? 0}})}</span>
                            <button type="button" class="shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-slate-700" title={$t('common.preview')} aria-label={$t('common.preview')} onclick={() => onPreviewFile(member.file_id)}>
                                <Eye size={12} />
                            </button>
                            <button
                                type="button"
                                class="shrink-0 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30"
                                title={$t('common.delete')}
                                aria-label={$t('common.delete')}
                                onclick={() => {
                                    const file = fileOf(member.file_id);
                                    if (file) onDeleteFile(file);
                                }}
                            >
                                <Trash2 size={12} />
                            </button>
                        </div>
                    {/each}
                    {#if missing}
                        <div class="ml-3 space-y-1.5 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200" data-testid="report-set-missing" data-role={role.code}>
                            <p class="font-medium">{$t('importWizard.reportSet.missingRole', {values: {role: roleName(role, role.code), ext: extensionsLabel(role)}})}</p>
                            {#if missing.start && missing.end}
                                <p>{$t('importWizard.reportSet.missingPeriod', {values: {start: formatDay(String(missing.start)), end: formatDay(String(missing.end))}})}</p>
                            {/if}
                            <div class="flex flex-wrap items-center gap-3">
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-1.5 rounded-md bg-libre-green px-2.5 py-1 font-medium text-white hover:bg-libre-green/90 disabled:cursor-not-allowed disabled:opacity-50"
                                    onclick={() => inputs[role.code]?.click()}
                                    disabled={uploadingRole !== null}
                                    data-testid="report-set-upload-missing"
                                >
                                    {#if uploadingRole === role.code}
                                        <LoadingSpinner size="sm" />
                                    {:else}
                                        <Upload size={12} />
                                    {/if}
                                    {$t('importWizard.reportSet.uploadMissing')}
                                </button>
                                <input bind:this={inputs[role.code]} type="file" class="hidden" accept={role.extensions.join(',')} onchange={(event) => pickFile(role.code, event)} data-testid="report-set-upload-input" />
                                {#if plugin?.docs_url}
                                    <a class="inline-flex items-center gap-1 text-libre-green hover:underline" href={plugin.docs_url} target="_blank" rel="noopener noreferrer">
                                        <ExternalLink size={12} />{$t('importWizard.reportSet.howToExport')}
                                    </a>
                                {/if}
                            </div>
                        </div>
                    {/if}
                </div>
            {/each}

            {#if unrecognised.length > 0}
                <div class="space-y-1">
                    <div class="text-xs font-medium text-gray-600 dark:text-gray-300">{$t('importWizard.reportSet.unrecognised')}</div>
                    {#each unrecognised as member (member.file_id)}
                        <div class="flex items-center gap-2 pl-3 text-xs text-gray-500" data-testid="report-set-member" data-file-id={member.file_id} data-role="">
                            <FileText size={12} class="shrink-0" />
                            <span class="min-w-0 flex-1 truncate">{member.filename}</span>
                        </div>
                    {/each}
                </div>
            {/if}

            {#if timeline}
                <div class="space-y-1" data-testid="report-set-timeline">
                    <div class="flex justify-between pl-28 text-[10px] tabular-nums text-gray-400">
                        <span>{formatDay(timeline.start)}</span>
                        <span>{formatDay(timeline.end)}</span>
                    </div>
                    {#if timeline.history}
                        <div class="flex items-center gap-2">
                            <span class="w-26 shrink-0 truncate text-xs text-gray-500">LibreFolio</span>
                            <div class="relative h-2 flex-1 rounded bg-gray-100 dark:bg-slate-800">
                                <div class="absolute h-2 rounded bg-gray-400/70 dark:bg-gray-500/70" style="left: {timeline.history.leftPct}%; width: {Math.max(timeline.history.widthPct, 1)}%" title="{formatDay(timeline.history.start)} → {formatDay(timeline.history.end)}"></div>
                            </div>
                        </div>
                    {/if}
                    {#each timeline.rows as row (row.role)}
                        <div class="flex items-center gap-2">
                            <span class="w-26 shrink-0 truncate text-xs text-gray-500"
                                >{roleName(
                                    roles.find((role) => role.code === row.role),
                                    row.role,
                                )}</span
                            >
                            <div class="relative h-2 flex-1 rounded bg-gray-100 dark:bg-slate-800">
                                {#each row.bars as bar, index (index)}
                                    <div class="absolute h-2 rounded bg-libre-green/70" style="left: {bar.leftPct}%; width: {Math.max(bar.widthPct, 1)}%" title="{formatDay(bar.start)} → {formatDay(bar.end)}"></div>
                                {/each}
                            </div>
                        </div>
                    {/each}
                </div>
            {/if}

            {#if (preview?.warnings ?? []).length > 0}
                <ul class="space-y-1">
                    {#each preview?.warnings ?? [] as notice, index (index)}
                        <li class="flex items-start gap-1.5 text-xs {notice.severity === 'info' ? 'text-blue-700 dark:text-blue-300' : 'text-amber-700 dark:text-amber-300'}" data-testid="report-set-warning" data-code={notice.code}>
                            {#if notice.severity === 'info'}
                                <Info size={12} class="mt-0.5 shrink-0" />
                            {:else}
                                <AlertTriangle size={12} class="mt-0.5 shrink-0" />
                            {/if}
                            <span>{translateOr(`importWizard.reportSet.warning.${notice.code}`, notice.message, noticeValues(notice.context as Record<string, unknown> | null | undefined))}</span>
                        </li>
                    {/each}
                </ul>
            {/if}

            {#if history}
                <p class="text-xs text-gray-600 dark:text-gray-400" data-testid="report-set-history" data-kind={history.kind}>
                    {history.kind === 'first' ? $t('importWizard.reportSet.historyFirst', {values: {date: formatDay(history.date)}}) : $t('importWizard.reportSet.historyLater', {values: {date: formatDay(history.date)}})}
                    {#if plugin?.docs_url}
                        <a class="ml-1 text-libre-green hover:underline" href={plugin.docs_url} target="_blank" rel="noopener noreferrer">{$t('importWizard.reportSet.howToExportBoth')}</a>
                    {/if}
                </p>
            {/if}

            {#if blocks}
                <div class="flex items-center justify-end">
                    <button type="button" class="rounded-md border border-gray-300 px-2.5 py-1 text-xs text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-slate-800" onclick={onExclude} data-testid="report-set-exclude">
                        {$t('importWizard.reportSet.exclude')}
                    </button>
                </div>
            {/if}
        </div>
    {/if}
</div>
