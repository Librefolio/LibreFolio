/**
 * Report sets in the import wizard: which uploaded files belong together, and what the wizard
 * may do with them.
 *
 * A report-set plugin (Danske Bank today) reads several exports of the same bank as one import:
 * the files uploaded together for a broker and recognised by the same plugin form a set
 * (design D-S22). Grouping, selection and the analysis units are pure functions of the file
 * list, the plugin catalogue and the user's choices, so they live here, tested without the
 * wizard; the component keeps the reactive state and the server calls.
 *
 * Design: `LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/design-phase00BrimReportSets.md`, §4.
 */

/** One export a report-set plugin reads (from `GET /brokers/import/plugins`). */
export interface SetRoleInfo {
    code: string;
    required: boolean;
    multiple: boolean;
    extensions: string[];
    description: string;
    max_history?: string | null;
    must_cover?: string | null;
}

/** The plugin fields the grouping reads. */
export interface SetPluginInfo {
    code: string;
    name: string;
    docs_url?: string | null;
    report_roles?: SetRoleInfo[] | null;
}

/** The file fields the grouping reads (a subset of `BrimFile`). */
export interface SetFileInfo {
    file_id: string;
    filename: string;
    uploaded_at: string;
    status: string;
    // The generated API types widen nullable fields (`T | null | Array<T | null>`): read, never trusted.
    target_broker_id?: unknown;
    batch_id?: unknown;
    kind?: unknown;
    compatible_plugins?: string[] | null;
}

/** The files of one broker uploaded together and recognised by one report-set plugin. */
export interface ReportSetGroup {
    key: string;
    brokerId: number;
    pluginCode: string;
    batchId: string;
    /** The earliest upload time of its files: the set's date in the UI. */
    uploadedAt: string;
    files: SetFileInfo[];
}

/** The selection fields the analysis units read (the wizard's `FileSelection`). */
export interface SelectedFileLike {
    fileId: string;
    fileName: string;
    brokerId: number;
    pluginCode: string;
}

/** What the analysis step runs: a file on its own, or a whole set through its combined file. */
export type ParseUnit = {kind: 'file'; file: SelectedFileLike} | {kind: 'set'; set: ReportSetGroup; members: SelectedFileLike[]};

/** The wizard's knowledge of a set's preview. */
export interface SetPreviewState {
    status: 'loading' | 'ready' | 'error';
    preview?: {complete?: boolean | null} | null;
    error?: string | null;
}

/** One bar of a set's timeline, in percent of the timeline's span. */
export interface TimelineBar {
    start: string;
    end: string;
    leftPct: number;
    widthPct: number;
    fileId?: string;
}

/** A set's timeline: one row of bars per role, plus the broker history LibreFolio already holds. */
export interface SetTimeline {
    start: string;
    end: string;
    rows: Array<{role: string; bars: TimelineBar[]}>;
    history: TimelineBar | null;
}

const DAY_MS = 86_400_000;

/** True when the plugin combines several exports into one import. */
export function isReportSetPlugin(plugin: SetPluginInfo | null | undefined): boolean {
    return (plugin?.report_roles?.length ?? 0) > 0;
}

/**
 * The report-set plugin a file joins, or null.
 *
 * A combined file is derived from a set and never a member; a file uploaded without a batch
 * cannot be told apart from the others of its broker, so it stays a single file (its parse
 * then explains that the set needs its files uploaded together). A file a report-set plugin
 * recognises joins that plugin's set even when a generic plugin could read it too (A18); a
 * manual choice wins, and a non-set choice keeps the file out of every set.
 */
export function setPluginFor(file: SetFileInfo, plugins: SetPluginInfo[], override?: string | null): string | null {
    if (file.kind === 'combined' || typeof file.batch_id !== 'string' || file.batch_id === '') return null;
    const isSet = (code: string) => isReportSetPlugin(plugins.find((plugin) => plugin.code === code));
    if (override) return isSet(override) ? override : null;
    return (file.compatible_plugins ?? []).find(isSet) ?? null;
}

/** The stable key of a set: one per broker, plugin and upload batch. */
export function reportSetKey(brokerId: number, pluginCode: string, batchId: string): string {
    return `set:${brokerId}:${pluginCode}:${batchId}`;
}

function byUploadThenName(a: SetFileInfo, b: SetFileInfo): number {
    return a.uploaded_at.localeCompare(b.uploaded_at) || a.filename.localeCompare(b.filename);
}

/** Splits one broker's files into report sets and single files; combined files are in neither. */
export function groupBrokerFiles<F extends SetFileInfo>(brokerId: number, files: F[], plugins: SetPluginInfo[], overrides?: ReadonlyMap<string, string>): {sets: ReportSetGroup[]; singles: F[]} {
    const sets = new Map<string, ReportSetGroup>();
    const singles: F[] = [];
    for (const file of files) {
        if (file.kind === 'combined') continue;
        const pluginCode = setPluginFor(file, plugins, overrides?.get(file.file_id));
        if (pluginCode === null) {
            singles.push(file);
            continue;
        }
        const batchId = file.batch_id as string;
        const key = reportSetKey(brokerId, pluginCode, batchId);
        const set = sets.get(key) ?? {key, brokerId, pluginCode, batchId, uploadedAt: file.uploaded_at, files: []};
        set.files.push(file);
        if (file.uploaded_at < set.uploadedAt) set.uploadedAt = file.uploaded_at;
        sets.set(key, set);
    }
    const ordered = [...sets.values()].map((set) => ({...set, files: [...set.files].sort(byUploadThenName)}));
    ordered.sort((a, b) => b.uploadedAt.localeCompare(a.uploadedAt) || a.key.localeCompare(b.key));
    return {sets: ordered, singles};
}

/** Whether a set's files are all, some or none selected. */
export function setSelectionState(set: ReportSetGroup, selectedIds: ReadonlySet<string>): 'all' | 'some' | 'none' {
    const selected = set.files.filter((file) => selectedIds.has(file.file_id)).length;
    if (selected === 0) return 'none';
    return selected === set.files.length ? 'all' : 'some';
}

/** The combined file built from a set (same broker, batch and plugin), the newest one; null when none exists. */
export function combinedFileForSet(set: ReportSetGroup, files: SetFileInfo[]): SetFileInfo | null {
    const combined = files.filter((file) => file.kind === 'combined' && file.target_broker_id === set.brokerId && file.batch_id === set.batchId && (file.compatible_plugins ?? []).includes(set.pluginCode));
    combined.sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at));
    return combined[0] ?? null;
}

/**
 * The analysis units of a selection. The selected files of a set, read with the set's plugin,
 * become one unit placed where its first member was; every other selected file is its own unit.
 */
export function buildParseUnits(selected: SelectedFileLike[], sets: ReportSetGroup[]): ParseUnit[] {
    const setOfFile = new Map<string, ReportSetGroup>();
    for (const set of sets) for (const file of set.files) setOfFile.set(file.file_id, set);
    const units: ParseUnit[] = [];
    const setUnits = new Map<string, Extract<ParseUnit, {kind: 'set'}>>();
    for (const file of selected) {
        const set = setOfFile.get(file.fileId);
        if (!set || set.pluginCode !== file.pluginCode) {
            units.push({kind: 'file', file});
            continue;
        }
        const existing = setUnits.get(set.key);
        if (existing) {
            existing.members.push(file);
            continue;
        }
        const unit = {kind: 'set' as const, set, members: [file]};
        setUnits.set(set.key, unit);
        units.push(unit);
    }
    return units;
}

/** True when a selected set cannot be analysed yet: its preview is still running, failed, or says it is incomplete. */
export function setBlocksAnalysis(set: ReportSetGroup, selectedIds: ReadonlySet<string>, state?: SetPreviewState): boolean {
    if (setSelectionState(set, selectedIds) === 'none') return false;
    return !(state?.status === 'ready' && state.preview?.complete === true);
}

const ISO_PERIOD = /^P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?$/;

/** An ISO 8601 period such as `P1Y`, `P6M`, `P90D` or `P1Y6M` split into its parts; null otherwise. */
export function parseIsoPeriod(value: string | null | undefined): {years: number; months: number; days: number} | null {
    if (!value) return null;
    const match = ISO_PERIOD.exec(value.trim());
    if (!match || (match[1] === undefined && match[2] === undefined && match[3] === undefined)) return null;
    return {years: Number(match[1] ?? 0), months: Number(match[2] ?? 0), days: Number(match[3] ?? 0)};
}

function dayNumber(isoDate: string): number {
    const [year, month, day] = isoDate.slice(0, 10).split('-').map(Number);
    return Math.round(Date.UTC(year, month - 1, day) / DAY_MS);
}

function isoOfDay(day: number): string {
    return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

/** The day before an ISO date, as `YYYY-MM-DD`. */
export function dayBefore(isoDate: string): string {
    return isoOfDay(dayNumber(isoDate) - 1);
}

interface TimelinePreview {
    members: Array<{file_id: string; role?: unknown; coverage: Array<{axis: string; start: string; end: string}>}>;
    history_start?: string | null;
}

/**
 * The timeline of a set: one row per role (in the plugin's order) with a bar for each file's
 * coverage, and the bar of the history LibreFolio already holds, from H0 to the end. Positions
 * are percentages of the span from the oldest to the newest date shown.
 */
export function buildSetTimeline(preview: TimelinePreview, roleOrder: string[]): SetTimeline | null {
    const spans = preview.members.flatMap((member) => member.coverage.map((coverage) => ({member, coverage})));
    if (spans.length === 0) return null;
    const days = spans.flatMap(({coverage}) => [dayNumber(coverage.start), dayNumber(coverage.end)]);
    if (preview.history_start) days.push(dayNumber(preview.history_start));
    const first = Math.min(...days);
    const last = Math.max(...days);
    const span = last - first;
    const bar = (start: string, end: string, fileId?: string): TimelineBar => {
        const from = dayNumber(start);
        const to = dayNumber(end);
        const leftPct = span === 0 ? 0 : ((from - first) / span) * 100;
        const widthPct = span === 0 ? 100 : ((to - from) / span) * 100;
        return {start: start.slice(0, 10), end: end.slice(0, 10), leftPct, widthPct, ...(fileId !== undefined ? {fileId} : {})};
    };
    const rows = roleOrder
        .map((role) => ({
            role,
            bars: spans.filter(({member}) => member.role === role).map(({member, coverage}) => bar(coverage.start, coverage.end, member.file_id)),
        }))
        .filter((row) => row.bars.length > 0);
    const end = isoOfDay(last);
    const history = preview.history_start ? bar(preview.history_start, end) : null;
    return {start: isoOfDay(first), end, rows, history};
}
