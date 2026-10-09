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
 * Design: `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md`, §4.
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
    // Read by the file badges (FilesTable).
    derived_from?: unknown;
    combined_into?: unknown;
    combine_is_stale?: unknown;
    // Read by the memory of the last analysis (rememberedChoices).
    processed_at?: unknown;
    parsed_plugin_code?: unknown;
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
    preview?: {complete?: boolean | null; missing?: unknown} | null;
    error?: string | null;
}

/** One bar of a set's timeline, in percent of the timeline's span. */
export interface TimelineBar {
    start: string;
    end: string;
    leftPct: number;
    widthPct: number;
    fileId?: string;
    /** The rows of the bar's file; `null` when the preview does not say. */
    rows?: number | null;
}

/** Days that no export of a role covers, between two of its files. */
export interface TimelineGap {
    start: string;
    end: string;
    leftPct: number;
    widthPct: number;
}

/** One role of a set's timeline: its bars in date order, and the gaps between them. */
export interface TimelineRow {
    role: string;
    bars: TimelineBar[];
    gaps: TimelineGap[];
}

/** A set's timeline: one row of bars per role, plus the broker history LibreFolio already holds. */
export interface SetTimeline {
    start: string;
    end: string;
    rows: TimelineRow[];
    /** From H0 to the last day LibreFolio holds, with how many transactions it holds. */
    history: (TimelineBar & {count: number}) | null;
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
 * then explains that the set needs its files uploaded together); a failed original is no member
 * either, as on the server (A2). A file a report-set plugin recognises joins that plugin's set
 * even when a generic plugin could read it too (A18). A manual choice wins: a report-set plugin
 * puts the file in that set, any other plugin keeps it out of every set, and `''` keeps it out
 * with no plugin at all (removed from its set). `null`/`undefined` mean no choice.
 */
export function setPluginFor(file: SetFileInfo, plugins: SetPluginInfo[], override?: string | null): string | null {
    if (file.kind === 'combined' || typeof file.batch_id !== 'string' || file.batch_id === '' || file.status === 'failed') return null;
    const isSet = (code: string) => isReportSetPlugin(plugins.find((plugin) => plugin.code === code));
    if (override !== undefined && override !== null) return isSet(override) ? override : null;
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

/** The ids of a combined file's originals that still exist (a deleted one keeps its ref, marked deleted). */
function liveMemberIds(combined: SetFileInfo): Set<string> {
    const refs = Array.isArray(combined.derived_from) ? combined.derived_from : [];
    const ids = new Set<string>();
    for (const ref of refs) {
        if (isRecordValue(ref) && typeof ref.file_id === 'string' && ref.deleted !== true) ids.add(ref.file_id);
    }
    return ids;
}

/**
 * The combined file built from a set — same broker, batch and plugin, and exactly the set's members
 * among its live originals — the newest one; null when none exists. A combined file built before a
 * member was left out, or before one was added, is another set's.
 */
export function combinedFileForSet(set: ReportSetGroup, files: SetFileInfo[]): SetFileInfo | null {
    const memberIds = new Set(set.files.map((file) => file.file_id));
    const sameMembers = (combined: SetFileInfo) => {
        const live = liveMemberIds(combined);
        return live.size === memberIds.size && [...live].every((id) => memberIds.has(id));
    };
    const combined = files.filter((file) => file.kind === 'combined' && file.target_broker_id === set.brokerId && file.batch_id === set.batchId && (file.compatible_plugins ?? []).includes(set.pluginCode) && sameMembers(file));
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

/**
 * True when a selected set cannot be analysed yet: it is ticked only in part (R6 — it waits until it
 * is ticked whole or unticked, nothing ticks it for the user), or its preview is still running,
 * failed, or says it is incomplete.
 */
export function setBlocksAnalysis(set: ReportSetGroup, selectedIds: ReadonlySet<string>, state?: SetPreviewState): boolean {
    const selection = setSelectionState(set, selectedIds);
    if (selection === 'none') return false;
    if (selection === 'some') return true;
    return !(state?.status === 'ready' && state.preview?.complete === true);
}

/**
 * The selected files the analysis would read alone with a report-set plugin (#26). A report-set plugin
 * reads its exports only through the set's combined file, and the server refuses one read alone; such a
 * file is in no set — uploaded with no batch (before report sets, or by an older client), or failed — yet
 * a set plugin is still chosen for it. In selection order.
 */
export function ungroupedSetFiles(units: ParseUnit[], plugins: SetPluginInfo[]): SelectedFileLike[] {
    const isSet = (code: string) => isReportSetPlugin(plugins.find((plugin) => plugin.code === code));
    return units.flatMap((unit) => (unit.kind === 'file' && isSet(unit.file.pluginCode) ? [unit.file] : []));
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

/** The day of an ISO date or instant, in the browser's locale like the tables' dates; `—` when absent. */
export function formatIsoDay(iso: string | null | undefined): string {
    if (!iso) return '—';
    const day = String(iso).slice(0, 10);
    const [year, month, date] = day.split('-').map(Number);
    if (!year || !month || !date) return day;
    return new Date(Date.UTC(year, month - 1, date)).toLocaleDateString(undefined, {timeZone: 'UTC', year: 'numeric', month: '2-digit', day: '2-digit'});
}

interface TimelinePreview {
    members: Array<{file_id: string; role?: unknown; rows?: number | null; coverage: Array<{axis: string; start: string; end: string}>}>;
    history_start?: string | null;
    history_end?: string | null;
    history_count?: number | null;
}

/**
 * The timeline of a set: one row per role (in the plugin's order) with a bar for each file's
 * coverage, in date order, and the days no file of the role covers between two of them; then the
 * history LibreFolio already holds, from H0 to its last day. Positions are percentages of the span
 * from the oldest to the newest date shown.
 */
export function buildSetTimeline(preview: TimelinePreview, roleOrder: string[]): SetTimeline | null {
    const spans = preview.members.flatMap((member) => member.coverage.map((coverage) => ({member, coverage})));
    if (spans.length === 0) return null;
    const days = spans.flatMap(({coverage}) => [dayNumber(coverage.start), dayNumber(coverage.end)]);
    const historyStart = preview.history_start ? dayNumber(preview.history_start) : null;
    // A history whose last transaction is the opening correction, dated on the eve of H0, ends on H0.
    const historyEnd = historyStart === null ? null : Math.max(historyStart, preview.history_end ? dayNumber(preview.history_end) : historyStart);
    if (historyStart !== null && historyEnd !== null) days.push(historyStart, historyEnd);
    const first = Math.min(...days);
    const last = Math.max(...days);
    const span = last - first;
    const place = (from: number, to: number) => ({
        leftPct: span === 0 ? 0 : ((from - first) / span) * 100,
        widthPct: span === 0 ? 100 : ((to - from) / span) * 100,
    });

    const rows = roleOrder
        .map((role): TimelineRow => {
            const bars = spans
                .filter(({member}) => member.role === role)
                .map(
                    ({member, coverage}): TimelineBar => ({
                        start: coverage.start.slice(0, 10),
                        end: coverage.end.slice(0, 10),
                        ...place(dayNumber(coverage.start), dayNumber(coverage.end)),
                        fileId: member.file_id,
                        rows: typeof member.rows === 'number' ? member.rows : null,
                    }),
                )
                .sort((a, b) => dayNumber(a.start) - dayNumber(b.start) || dayNumber(a.end) - dayNumber(b.end));
            return {role, bars, gaps: gapsBetween(bars, place)};
        })
        .filter((row) => row.bars.length > 0);

    const history = historyStart !== null && historyEnd !== null ? {start: isoOfDay(historyStart), end: isoOfDay(historyEnd), ...place(historyStart, historyEnd), count: typeof preview.history_count === 'number' ? preview.history_count : 0} : null;
    return {start: isoOfDay(first), end: isoOfDay(last), rows, history};
}

/** The stretches no bar covers between the first and the last bar, the furthest end reached so far counting as covered. */
function gapsBetween(bars: TimelineBar[], place: (from: number, to: number) => {leftPct: number; widthPct: number}): TimelineGap[] {
    const gaps: TimelineGap[] = [];
    let reached: number | null = null;
    for (const bar of bars) {
        const from = dayNumber(bar.start);
        if (reached !== null && from > reached + 1) gaps.push({start: isoOfDay(reached + 1), end: isoOfDay(from - 1), ...place(reached + 1, from - 1)});
        reached = reached === null ? dayNumber(bar.end) : Math.max(reached, dayNumber(bar.end));
    }
    return gaps;
}

// ---------------------------------------------------------------------------
// The badges of the files page and of the broker's import files (FilesTable, design §5)
// ---------------------------------------------------------------------------

/** One badge of a file, about its report set. */
export interface FileSetBadge {
    kind: 'combined' | 'stale' | 'usedInCombined' | 'set' | 'incomplete';
    /** combined: the originals it was built from, and those of them since deleted. */
    names?: string[];
    deleted?: string[];
    /** set: when the set was uploaded. */
    uploadedAt?: string;
    /** incomplete: the roles the set lacks. */
    roles?: string[];
}

/** What the badges read: the set of each member file, every listed file, and the previews by set key. */
export interface FileSetBadgeContext {
    sets: ReadonlyMap<string, ReportSetGroup>;
    files: SetFileInfo[];
    previews: ReadonlyMap<string, SetPreviewState>;
}

function isRecordValue(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Every member of a report set, mapped to its set: the sets `groupBrokerFiles` builds, broker by
 * broker, with the memory of the last analysis (`rememberedChoices`). Files without a broker belong to none.
 */
export function setsOfFiles<F extends SetFileInfo>(files: F[], plugins: SetPluginInfo[]): Map<string, ReportSetGroup> {
    const byBroker = new Map<number, F[]>();
    for (const file of files) {
        if (typeof file.target_broker_id !== 'number') continue;
        const list = byBroker.get(file.target_broker_id) ?? [];
        list.push(file);
        byBroker.set(file.target_broker_id, list);
    }
    const setOfFile = new Map<string, ReportSetGroup>();
    for (const [brokerId, brokerFiles] of byBroker) {
        for (const set of groupBrokerFiles(brokerId, brokerFiles, plugins, rememberedChoices(brokerFiles, plugins)).sets) {
            for (const file of set.files) setOfFile.set(file.file_id, set);
        }
    }
    return setOfFile;
}

/**
 * The badges of one file, in a fixed order: combined · stale · usedInCombined · set · incomplete.
 *
 * `incomplete` needs the set's preview, ready and saying `complete: false`; while it loads, after
 * it failed, or when the set has an up-to-date combined file (which still holds a deleted
 * original, v5.3), the set is not called incomplete.
 */
export function fileSetBadges(file: SetFileInfo, ctx: FileSetBadgeContext): FileSetBadge[] {
    const badges: FileSetBadge[] = [];
    if (file.kind === 'combined') {
        const originals = Array.isArray(file.derived_from) ? file.derived_from.filter(isRecordValue) : [];
        badges.push({
            kind: 'combined',
            names: originals.map((original) => String(original.filename ?? '')),
            deleted: originals.filter((original) => original.deleted === true).map((original) => String(original.filename ?? '')),
        });
    }
    if (file.combine_is_stale === true) badges.push({kind: 'stale'});
    if (Array.isArray(file.combined_into) && file.combined_into.length > 0) badges.push({kind: 'usedInCombined'});
    const set = ctx.sets.get(file.file_id);
    if (!set) return badges;
    badges.push({kind: 'set', uploadedAt: set.uploadedAt});
    const state = ctx.previews.get(set.key);
    const preview = state?.status === 'ready' ? state.preview : null;
    if (preview?.complete !== false) return badges;
    const combined = combinedFileForSet(set, ctx.files);
    if (combined !== null && combined.combine_is_stale !== true) return badges;
    const missing = Array.isArray(preview.missing) ? preview.missing.filter(isRecordValue) : [];
    badges.push({kind: 'incomplete', roles: missing.map((item) => String(item.role ?? '')).filter((role) => role !== '')});
    return badges;
}

// ---------------------------------------------------------------------------
// The user's choice of how a set is read (phase G): the memory of the last analysis, what the
// card offers, and the request that tells the server which originals were left out
// ---------------------------------------------------------------------------

/** A plugin as the card offers it. */
export interface PluginChoice {
    code: string;
    name: string;
}

function choiceOf(code: string, plugins: SetPluginInfo[]): PluginChoice {
    return {code, name: plugins.find((plugin) => plugin.code === code)?.name ?? code};
}

function isSetPluginCode(code: unknown, plugins: SetPluginInfo[]): boolean {
    return typeof code === 'string' && isReportSetPlugin(plugins.find((plugin) => plugin.code === code));
}

/** An ISO instant in milliseconds; NaN when absent or unreadable (such an event is ignored). */
function instant(value: unknown): number {
    return typeof value === 'string' ? Date.parse(value) : Number.NaN;
}

/**
 * The memory of the last analysis: for each original of an upload, the choice it implies — a
 * report-set plugin (in that set), another plugin (read alone with it), or `''` (left out of the
 * set, no plugin). Files never analysed have no entry, and detection decides for them.
 *
 * Nothing is remembered while files are only uploaded. An analysis leaves three kinds of events,
 * read from what the server already saves:
 * - E1, member: a parsed combined file of the same broker and upload lists the file among its
 *   originals — its plugin, at the combined file's `processed_at`;
 * - E2, alone: the file itself was parsed by a single-file plugin — that plugin, at its own `processed_at`;
 * - E3, left out: a parsed combined file of the same broker and upload does not list it, although
 *   its plugin reads the file and the file was already there when it was built — `''`, at the
 *   combined file's `processed_at`.
 * The newest member event wins when it is newer than every other; otherwise a lone parse newer
 * than it gives its plugin (a lone parse and a set analysis that left the file out say the same
 * thing: out of the set); otherwise being left out gives `''`.
 */
export function rememberedChoices(files: SetFileInfo[], plugins: SetPluginInfo[]): Map<string, string> {
    const analysed = files.filter((file) => file.kind === 'combined' && file.status === 'parsed' && typeof file.batch_id === 'string' && file.batch_id !== '' && isSetPluginCode(file.parsed_plugin_code, plugins) && !Number.isNaN(instant(file.processed_at)));
    const memory = new Map<string, string>();
    for (const file of files) {
        if (file.kind === 'combined' || typeof file.batch_id !== 'string' || file.batch_id === '') continue;
        let member: {plugin: string; at: number} | null = null;
        let leftOut: number | null = null;
        for (const combined of analysed) {
            if (combined.batch_id !== file.batch_id || combined.target_broker_id !== file.target_broker_id) continue;
            const at = instant(combined.processed_at);
            const plugin = combined.parsed_plugin_code as string;
            if (liveMemberIds(combined).has(file.file_id)) {
                if (member === null || at > member.at) member = {plugin, at};
            } else if ((file.compatible_plugins ?? []).includes(plugin) && instant(file.uploaded_at) <= instant(combined.uploaded_at)) {
                if (leftOut === null || at > leftOut) leftOut = at;
            }
        }
        const aloneAt = instant(file.processed_at);
        const alone = file.status === 'parsed' && typeof file.parsed_plugin_code === 'string' && file.parsed_plugin_code !== '' && !isSetPluginCode(file.parsed_plugin_code, plugins) && !Number.isNaN(aloneAt) ? {plugin: file.parsed_plugin_code, at: aloneAt} : null;

        if (member !== null && (alone === null || member.at > alone.at) && (leftOut === null || member.at > leftOut)) memory.set(file.file_id, member.plugin);
        else if (alone !== null && (member === null || alone.at >= member.at)) memory.set(file.file_id, alone.plugin);
        else if (leftOut !== null) memory.set(file.file_id, '');
    }
    return memory;
}

/** «Read as»: the report-set plugins that read every member of the set, the set's own first. */
export function setPluginChoices(set: ReportSetGroup, plugins: SetPluginInfo[]): PluginChoice[] {
    const readsEvery = (code: string) => set.files.length > 0 && set.files.every((file) => (file.compatible_plugins ?? []).includes(code));
    const codes = plugins.filter((plugin) => isReportSetPlugin(plugin) && readsEvery(plugin.code)).map((plugin) => plugin.code);
    const ordered = codes.includes(set.pluginCode) ? [set.pluginCode, ...codes.filter((code) => code !== set.pluginCode)] : codes;
    return ordered.map((code) => choiceOf(code, plugins));
}

/** «Read alone with»: the single-file plugins that read the file, the broker's default first when it is one of them. */
export function readAlonePlugins(file: SetFileInfo, plugins: SetPluginInfo[], brokerDefault?: string | null): PluginChoice[] {
    const codes = (file.compatible_plugins ?? []).filter((code) => !isSetPluginCode(code, plugins));
    const ordered = brokerDefault && codes.includes(brokerDefault) ? [brokerDefault, ...codes.filter((code) => code !== brokerDefault)] : codes;
    return ordered.map((code) => choiceOf(code, plugins));
}

/** The other report-set plugins that read the file: the set could be read another way. */
export function otherSetPlugins(file: SetFileInfo, setPluginCode: string, plugins: SetPluginInfo[]): PluginChoice[] {
    return (file.compatible_plugins ?? []).filter((code) => code !== setPluginCode && isSetPluginCode(code, plugins)).map((code) => choiceOf(code, plugins));
}

/** The broker's default plugin, when it is another plugin that reads a member: the set is not read the broker's usual way. */
export function defaultPluginNote(set: ReportSetGroup, brokerDefault: string | null, plugins: SetPluginInfo[]): PluginChoice | null {
    if (!brokerDefault || brokerDefault === set.pluginCode) return null;
    if (!set.files.some((file) => (file.compatible_plugins ?? []).includes(brokerDefault))) return null;
    return choiceOf(brokerDefault, plugins);
}

/** The body of `/sets/preview` and `/sets/combine`. */
export interface SetRequest {
    broker_id: number;
    plugin_code: string;
    batch_id: string;
    exclude_file_ids: string[];
}

/**
 * The set as the server must read it: the originals of the same broker and upload that the set's
 * plugin reads but that are no members — read alone, or removed from the set — are left out
 * (`exclude_file_ids`). A failed original is no member on the server anyway, and is not listed.
 */
export function setRequest(set: ReportSetGroup, files: SetFileInfo[]): SetRequest {
    const members = new Set(set.files.map((file) => file.file_id));
    const excluded = files.filter((file) => file.kind !== 'combined' && file.target_broker_id === set.brokerId && file.batch_id === set.batchId && file.status !== 'failed' && (file.compatible_plugins ?? []).includes(set.pluginCode) && !members.has(file.file_id)).map((file) => file.file_id);
    return {broker_id: set.brokerId, plugin_code: set.pluginCode, batch_id: set.batchId, exclude_file_ids: excluded};
}
