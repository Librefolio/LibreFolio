<!--
  ReportSetCard.svelte — one report set in the import wizard's file selection (step 2).

  A report-set plugin imports several exports of the same bank as one: the files uploaded
  together for a broker and recognised by the plugin form a set (design D-S22). The set is one
  row with its card: the files of each role in a table, ordered by the period they cover; what
  is missing and for which period; a timeline of the files, of the gaps between them and of the
  broker history LibreFolio already holds, each with an infobox; the plugin's notices; and the
  actions that make the set importable — upload the missing export into the same set, or
  exclude the set from this import.

  The user chooses how the set is read (phase G): «Read as» in the header switches to another
  report-set plugin that reads every member, or reads the files one by one; a file's row menu
  reads it alone with a single-file plugin that can, or removes it from the set. Notes say when
  the set is not read with the broker's default plugin, and when another report-set plugin also
  recognises a file. The card only asks: the wizard owns the choices.

  Everything is rendered as Svelte text: file names and plugin notices are user/provider data.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ChevronDown, ChevronRight, Eye, FileText, Layers, Trash2, Upload, ExternalLink, AlertTriangle, Info, FileOutput, Unlink} from 'lucide-svelte';
    import LoadingSpinner from '$lib/components/ui/feedback/LoadingSpinner.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';
    import {
        buildSetTimeline,
        dayBefore,
        defaultPluginNote,
        formatIsoDay,
        otherSetPlugins,
        parseIsoPeriod,
        readAlonePlugins,
        setPluginChoices,
        setPluginFor,
        type ReportSetGroup,
        type SetFileInfo,
        type SetPluginInfo,
        type SetPreviewState,
        type SetRoleInfo,
        type TimelineBar,
        type TimelineGap,
    } from '$lib/utils/transactions/importReportSets';
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
        /** The plugin catalogue: names, and which plugins read report sets. */
        plugins: SetPluginInfo[];
        /** The broker's default import plugin, if it has one. */
        brokerDefaultPlugin: string | null;
        /** «Read as»: another report-set plugin, or `null` to read the files one by one. */
        onReadAs: (code: string | null) => void;
        /** Read one file alone with a single-file plugin: it leaves the set. */
        onReadAlone: (fileId: string, code: string) => void;
        /** Remove one file from the set, with no plugin. */
        onRemoveFromSet: (fileId: string) => void;
    }

    let {set, plugin, previewState, selection, expanded, analysed, uploadingRole, onToggleSelected, onToggleExpanded, onUploadMissing, onExclude, onPreviewFile, onDeleteFile, plugins, brokerDefaultPlugin, onReadAs, onReadAlone, onRemoveFromSet}: Props = $props();

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
                      members: (preview.members ?? []).map((member) => ({file_id: member.file_id, role: member.role ?? null, rows: typeof member.rows === 'number' ? member.rows : null, coverage: (member.coverage ?? []).map((c) => ({axis: c.axis, start: String(c.start), end: String(c.end)}))})),
                      history_start: preview.history_start ? String(preview.history_start) : null,
                      history_end: preview.history_end ? String(preview.history_end) : null,
                      history_count: typeof preview.history_count === 'number' ? preview.history_count : 0,
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

    const formatDay = formatIsoDay;

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

    /** A file of the set as its role table lists it: the period is the union of its coverages. */
    interface MemberRow {
        fileId: string;
        filename: string;
        start: string | null;
        end: string | null;
        rows: number | null;
    }

    function compareIso(a: string, b: string): number {
        return a < b ? -1 : a > b ? 1 : 0;
    }

    /** The files of a role by period start, then name; a file without coverage last (U1-B). */
    function memberRows(code: string): MemberRow[] {
        return membersOf(code)
            .map((member) => {
                const starts = (member.coverage ?? []).map((c) => String(c.start).slice(0, 10)).sort(compareIso);
                const ends = (member.coverage ?? []).map((c) => String(c.end).slice(0, 10)).sort(compareIso);
                return {fileId: member.file_id, filename: member.filename, start: starts[0] ?? null, end: ends[ends.length - 1] ?? null, rows: typeof member.rows === 'number' ? member.rows : null};
            })
            .sort((a, b) => {
                if (a.start !== b.start) {
                    if (a.start === null) return 1;
                    if (b.start === null) return -1;
                    return compareIso(a.start, b.start);
                }
                return a.filename.localeCompare(b.filename, undefined, {numeric: true});
            });
    }

    // Fixed order and no selection: the set is chosen whole, and the developer asked for the files by period.
    let memberColumns = $derived<ColumnDef<MemberRow>[]>([
        {id: 'file', header: () => $t('importWizard.reportSet.column.file'), type: 'text', sortable: false, filterable: false, minWidth: 160, cell: (row) => row.filename},
        {id: 'period', header: () => $t('importWizard.reportSet.column.period'), type: 'text', sortable: false, filterable: false, width: 200, minWidth: 150, cell: (row) => (row.start ? `${formatDay(row.start)} → ${formatDay(row.end)}` : '—')},
        {id: 'rows', header: () => $t('importWizard.reportSet.column.rows'), type: 'number', sortable: false, filterable: false, width: 80, minWidth: 60, cell: (row) => row.rows ?? '—'},
    ]);

    /** «Read as»: the report-set plugins that read every member, and which of them detection picks. */
    let readAsChoices = $derived(setPluginChoices(set, plugins));
    let detectedPlugin = $derived(set.files.length > 0 ? setPluginFor(set.files[0], plugins) : null);
    /** The «one by one» entry of «Read as»: a value no plugin code can take (an empty value means «nothing chosen» to the select). */
    const ONE_BY_ONE = '__one_by_one__';
    let readAsOptions = $derived<SelectOption[]>([...readAsChoices.map((choice) => ({value: choice.code, label: choice.code === detectedPlugin ? `${choice.name} (${$t('importWizard.reportSet.detected')})` : choice.name})), {value: ONE_BY_ONE, label: $t('importWizard.reportSet.readAsOneByOne')}]);

    function readAs(value: string) {
        onReadAs(value === ONE_BY_ONE ? null : value);
    }

    /** The single-file plugins that can read each member alone, by file id. */
    let readAloneByFile = $derived(new Map(set.files.map((file) => [file.file_id, readAlonePlugins(file, plugins, brokerDefaultPlugin)])));
    let readAloneOptions = $derived([...readAloneByFile.values()].flat().filter((choice, index, list) => list.findIndex((other) => other.code === choice.code) === index));

    let memberActions = $derived<RowAction<MemberRow>[]>([
        {id: 'preview', icon: Eye, label: $t('common.preview'), onClick: (row) => onPreviewFile(row.fileId)},
        ...readAloneOptions.map(
            (choice): RowAction<MemberRow> => ({
                id: `read-alone-${choice.code}`,
                icon: FileOutput,
                label: $t('importWizard.reportSet.readAloneWith', {values: {plugin: choice.name}}),
                visible: (row) => (readAloneByFile.get(row.fileId) ?? []).some((option) => option.code === choice.code),
                onClick: (row) => onReadAlone(row.fileId, choice.code),
            }),
        ),
        {id: 'remove-from-set', icon: Unlink, label: $t('importWizard.reportSet.removeFromSet'), onClick: (row) => onRemoveFromSet(row.fileId)},
        {
            id: 'delete',
            icon: Trash2,
            label: $t('common.delete'),
            variant: 'danger',
            onClick: (row) => {
                const file = fileOf(row.fileId);
                if (file) onDeleteFile(file);
            },
        },
    ]);

    /** C1: the broker's default plugin, when it is another one that reads a member. */
    let defaultNote = $derived(defaultPluginNote(set, brokerDefaultPlugin, plugins));
    /** C2: the members another report-set plugin also recognises. */
    let alsoRecognised = $derived(set.files.map((file) => ({file, others: otherSetPlugins(file, set.pluginCode, plugins)})).filter((entry) => entry.others.length > 0));

    let hasTimelineGaps = $derived((timeline?.rows ?? []).some((row) => row.gaps.length > 0));

    function period(start: string, end: string): string {
        return `${formatDay(start)} → ${formatDay(end)}`;
    }

    /** The span a timeline row covers, from its first start to its furthest end. */
    function rowSpan(bars: TimelineBar[]): string {
        if (bars.length === 0) return '';
        const end = bars.map((bar) => bar.end).sort(compareIso)[bars.length - 1];
        return period(bars[0].start, end);
    }

    function barInfo(roleCode: string, bar: TimelineBar): string {
        const name = (preview?.members ?? []).find((member) => member.file_id === bar.fileId)?.filename ?? '';
        const lines = [
            roleName(
                roles.find((role) => role.code === roleCode),
                roleCode,
            ),
            name,
            period(bar.start, bar.end),
        ];
        if (typeof bar.rows === 'number') lines.push($t('importWizard.reportSet.rows', {values: {n: bar.rows}}));
        return lines.filter((line) => line !== '').join('\n');
    }

    function gapInfo(gap: TimelineGap): string {
        return `${period(gap.start, gap.end)}\n${$t('importWizard.reportSet.timeline.gapInfo')}`;
    }

    function historyInfo(history: TimelineBar & {count: number}): string {
        return `LibreFolio\n${period(history.start, history.end)}\n${$t('importWizard.reportSet.timeline.historyCount', {values: {n: history.count}})}`;
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
        <div class="flex shrink-0 items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
            <span class="hidden sm:inline">{$t('importWizard.reportSet.readAs')}</span>
            <SimpleSelect
                class="max-w-52"
                value={set.pluginCode}
                options={readAsOptions}
                onchange={readAs}
                compact
                ariaLabel={$t('importWizard.reportSet.readAs')}
                testId="report-set-read-as"
                optionTestId={(option) => `report-set-read-as-option-${option.value === ONE_BY_ONE ? 'one-by-one' : option.value}`}
            />
        </div>
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

            {#if defaultNote}
                <p class="flex items-start gap-1.5 text-xs text-sky-700 dark:text-sky-300" data-testid="report-set-default-note" data-default-plugin={defaultNote.code}>
                    <Info size={12} class="mt-0.5 shrink-0" />
                    <span>{$t('importWizard.reportSet.defaultPluginNote', {values: {plugin: plugin?.name ?? set.pluginCode, defaultPlugin: defaultNote.name}})}</span>
                </p>
            {/if}
            {#each alsoRecognised as entry (entry.file.file_id)}
                <p class="flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-300" data-testid="report-set-also-recognised" data-file-id={entry.file.file_id} data-plugins={entry.others.map((other) => other.code).join(',')}>
                    <AlertTriangle size={12} class="mt-0.5 shrink-0" />
                    <span>{$t('importWizard.reportSet.alsoRecognisedBy', {values: {file: entry.file.filename, plugins: entry.others.map((other) => other.name).join(', ')}})}</span>
                </p>
            {/each}

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
                    {#if membersOf(role.code).length > 0}
                        <div class="overflow-hidden rounded-md border border-gray-100 dark:border-gray-800" data-testid="report-set-role-table" data-role={role.code}>
                            <DataTable
                                data={memberRows(role.code)}
                                columns={memberColumns}
                                getRowId={(row) => row.fileId}
                                storageKey={`import-wizard-set-role-${role.code}`}
                                enableSelection={false}
                                enableActions={true}
                                actionsColumnWidth="48px"
                                rowActions={memberActions}
                                onRowDoubleClick={(row) => onPreviewFile(row.fileId)}
                                enableSorting={false}
                                enableColumnFilters={false}
                                enableColumnResize={false}
                                enablePagination={false}
                                enableColumnVisibility={false}
                                tableLayout="auto"
                                stickyActions={false}
                                enableContextMenu={true}
                            />
                        </div>
                    {/if}
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
                        <div class="flex items-center gap-2 pl-3 text-xs text-gray-500" data-testid="report-set-unrecognised" data-file-id={member.file_id}>
                            <FileText size={12} class="shrink-0" />
                            <span class="min-w-0 flex-1 truncate">{member.filename}</span>
                        </div>
                    {/each}
                </div>
            {/if}

            {#if timeline}
                <!-- One grid for every row: the label column is as wide as the longest name (it wraps only past
                     40% of the card), so every row's bars start and end at the same point. -->
                <div class="grid grid-cols-[fit-content(40%)_minmax(0,1fr)_max-content] items-center gap-x-2 gap-y-1.5" data-testid="report-set-timeline">
                    <div class="col-start-2 flex justify-between text-[10px] tabular-nums text-gray-400">
                        <span>{formatDay(timeline.start)}</span>
                        <span>{formatDay(timeline.end)}</span>
                    </div>
                    <span aria-hidden="true"></span>
                    {#each timeline.rows as row (row.role)}
                        <span class="text-xs text-gray-500" data-testid="report-set-timeline-label" data-role={row.role}
                            >{roleName(
                                roles.find((role) => role.code === row.role),
                                row.role,
                            )}</span
                        >
                        <div class="relative h-3 rounded bg-gray-100 dark:bg-slate-800">
                            {#each row.gaps as gap, index (index)}
                                <div class="absolute inset-y-0" style="left: {gap.leftPct}%; width: {Math.max(gap.widthPct, 1)}%">
                                    <Tooltip text={gapInfo(gap)} wrapperClass="h-full w-full" showDelayMs={200}>
                                        <div class="h-full w-full rounded border border-dashed border-amber-500 bg-amber-50/60 dark:border-amber-400 dark:bg-amber-900/20" data-testid="report-set-timeline-gap" data-role={row.role} data-start={gap.start} data-end={gap.end}></div>
                                    </Tooltip>
                                </div>
                            {/each}
                            {#each row.bars as bar, index (index)}
                                <div class="absolute inset-y-0" style="left: {bar.leftPct}%; width: {Math.max(bar.widthPct, 1)}%">
                                    <Tooltip text={barInfo(row.role, bar)} wrapperClass="h-full w-full" showDelayMs={200}>
                                        <div class="h-full w-full rounded bg-libre-green/70 hover:bg-libre-green" data-testid="report-set-timeline-bar" data-role={row.role} data-file-id={bar.fileId} data-start={bar.start} data-end={bar.end} data-rows={bar.rows ?? ''}></div>
                                    </Tooltip>
                                </div>
                            {/each}
                        </div>
                        <span class="text-right text-[10px] tabular-nums text-gray-500">{rowSpan(row.bars)}</span>
                    {/each}
                    {#if timeline.history}
                        {@const history = timeline.history}
                        <span class="text-xs text-gray-500" data-testid="report-set-timeline-label" data-role="history">LibreFolio</span>
                        <div class="relative h-3 rounded bg-gray-100 dark:bg-slate-800">
                            <div class="absolute inset-y-0" style="left: {history.leftPct}%; width: {Math.max(history.widthPct, 1)}%">
                                <Tooltip text={historyInfo(history)} wrapperClass="h-full w-full" showDelayMs={200}>
                                    <div class="h-full w-full rounded bg-gray-400/80 hover:bg-gray-500 dark:bg-gray-500/80" data-testid="report-set-timeline-history" data-start={history.start} data-end={history.end} data-count={history.count}></div>
                                </Tooltip>
                            </div>
                        </div>
                        <span class="text-right text-[10px] tabular-nums text-gray-500">{period(history.start, history.end)}</span>
                    {/if}
                    <div class="col-span-2 col-start-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-gray-500" data-testid="report-set-timeline-legend">
                        <span class="inline-flex items-center gap-1" data-testid="report-set-timeline-legend-item" data-kind="file"><span class="inline-block h-2 w-4 rounded bg-libre-green/70"></span>{$t('importWizard.reportSet.timeline.legendFile')}</span>
                        {#if timeline.history}
                            <span class="inline-flex items-center gap-1" data-testid="report-set-timeline-legend-item" data-kind="history"><span class="inline-block h-2 w-4 rounded bg-gray-400/80 dark:bg-gray-500/80"></span>{$t('importWizard.reportSet.timeline.legendHistory')}</span>
                        {/if}
                        {#if hasTimelineGaps}
                            <span class="inline-flex items-center gap-1" data-testid="report-set-timeline-legend-item" data-kind="gap"><span class="inline-block h-2 w-4 rounded border border-dashed border-amber-500 dark:border-amber-400"></span>{$t('importWizard.reportSet.timeline.legendGap')}</span
                            >
                        {/if}
                    </div>
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
