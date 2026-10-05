/**
 * Report sets in the import wizard (phase C2 of the Danske Bank workstream) — the pure module.
 *
 * `importReportSets.ts` decides, outside the 5000-line wizard, how the files of a broker fall
 * into report sets (one per upload batch and report-set plugin, A18), whether a set is
 * selected, whether it blocks the analysis, what the analysis runs on (one unit per set) and
 * how its timeline is drawn. Every shape below is the structural contract pinned in the plan
 * (C2.0): the module accepts plain objects, so these tests build plain objects.
 *
 * The module is loaded inside each test, through `c2()`: while it — or one of its exports —
 * does not exist, every test fails on its own with "not implemented yet", instead of the whole
 * file failing at collection and hiding which pieces are missing.
 *
 * Phase C3 adds the badges of the files page and of the broker's import files (`FilesTable`):
 * `setsOfFiles` and `fileSetBadges`, at the end of the file, loaded the same way through `c3()`.
 *
 * Phase F2 (plan F2.0, U2-B) reworks the timeline: each bar carries its file's `rows` and the bars
 * of a role come in order of start, then end; each role row gains its `gaps` (the holes between its
 * bars, never before the first or after the last); the history runs from H0 to `history_end` — no
 * longer to the end of the timeline — and carries `history_count`; `history_end` may stretch the span.
 */
import {describe, expect, it} from 'vitest';

// ---------------------------------------------------------------------------
// The pinned shapes
// ---------------------------------------------------------------------------

interface SetRoleInfo {
    code: string;
    required: boolean;
    multiple: boolean;
    extensions: string[];
    description: string;
    max_history?: string | null;
    must_cover?: string | null;
}
interface SetPluginInfo {
    code: string;
    name: string;
    docs_url?: string | null;
    report_roles?: SetRoleInfo[] | null;
}
interface SetFileInfo {
    file_id: string;
    filename: string;
    uploaded_at: string;
    status: string;
    target_broker_id?: number | null;
    batch_id?: string | null;
    kind?: string | null;
    compatible_plugins?: string[] | null;
    // Read by the badges (phase C3).
    derived_from?: Array<{file_id: string; role?: string | null; filename: string; deleted?: boolean}> | null;
    combined_into?: string[] | null;
    combine_is_stale?: boolean | null;
}
interface ReportSetGroup {
    key: string;
    brokerId: number;
    pluginCode: string;
    batchId: string;
    uploadedAt: string;
    files: SetFileInfo[];
}
interface SelectedFileLike {
    fileId: string;
    fileName: string;
    brokerId: number;
    pluginCode: string;
}
type ParseUnit = {kind: 'file'; file: SelectedFileLike} | {kind: 'set'; set: ReportSetGroup; members: SelectedFileLike[]};
interface SetPreviewState {
    status: 'loading' | 'ready' | 'error';
    preview?: {complete: boolean} | null;
    error?: string | null;
}
interface TimelineBar {
    start: string;
    end: string;
    leftPct: number;
    widthPct: number;
    fileId?: string;
    /** F2: the rows of the bar's file; null when the member does not say. */
    rows?: number | null;
}
/** F2: a stretch of a role's row that none of its files covers, between two of its bars. */
interface TimelineGap {
    start: string;
    end: string;
    leftPct: number;
    widthPct: number;
}
/** F2: the history LibreFolio holds, from H0 to its newest tagged transaction, and how many it has. */
interface TimelineHistory {
    start: string;
    end: string;
    leftPct: number;
    widthPct: number;
    count: number;
}
interface SetTimeline {
    start: string;
    end: string;
    rows: Array<{role: string; bars: TimelineBar[]; gaps: TimelineGap[]}>;
    history: TimelineHistory | null;
}
interface TimelinePreview {
    members: Array<{file_id: string; role?: string | null; rows?: number | null; coverage: Array<{axis: string; start: string; end: string}>}>;
    history_start?: string | null;
    history_end?: string | null;
    history_count?: number | null;
}

interface ReportSetsModule {
    isReportSetPlugin(plugin: SetPluginInfo | null | undefined): boolean;
    setPluginFor(file: SetFileInfo, plugins: SetPluginInfo[], override?: string | null): string | null;
    reportSetKey(brokerId: number, pluginCode: string, batchId: string): string;
    groupBrokerFiles(brokerId: number, files: SetFileInfo[], plugins: SetPluginInfo[], overrides?: ReadonlyMap<string, string>): {sets: ReportSetGroup[]; singles: SetFileInfo[]};
    setSelectionState(set: ReportSetGroup, selectedIds: ReadonlySet<string>): 'all' | 'some' | 'none';
    combinedFileForSet(set: ReportSetGroup, files: SetFileInfo[]): SetFileInfo | null;
    buildParseUnits(selected: SelectedFileLike[], sets: ReportSetGroup[]): ParseUnit[];
    setBlocksAnalysis(set: ReportSetGroup, selectedIds: ReadonlySet<string>, state?: SetPreviewState): boolean;
    parseIsoPeriod(value: string | null | undefined): {years: number; months: number; days: number} | null;
    dayBefore(isoDate: string): string;
    buildSetTimeline(preview: TimelinePreview, roleOrder: string[]): SetTimeline | null;
}

/** One export of the module, loaded for the test that needs it. */
async function c2<K extends keyof ReportSetsModule>(name: K): Promise<ReportSetsModule[K]> {
    let mod: Partial<ReportSetsModule>;
    try {
        mod = (await import('./importReportSets')) as unknown as Partial<ReportSetsModule>;
    } catch (error) {
        throw new Error(`importReportSets.ts cannot be loaded — not implemented yet (report sets, phase C2): ${String(error)}`);
    }
    const fn = mod[name];
    if (typeof fn !== 'function') throw new Error(`importReportSets.${name} is not implemented yet (report sets, phase C2)`);
    return fn as ReportSetsModule[K];
}

// ---------------------------------------------------------------------------
// Fixtures: two invented report-set plugins and the single-file ones
// ---------------------------------------------------------------------------

const BROKER = 7;
const DANSKE = 'broker_danske_bank';
const GENERIC = 'broker_generic_csv';
/** A second report-set plugin, invented: a file two set plugins can read goes to the first one. */
const OTHER_SET = 'broker_other_bank';
/** Upload batches are UUIDs (C1); fixed values keep the keys readable in a failure. */
const BATCH_NEW = '6f1c2d3e-4a5b-4c6d-8e7f-901a2b3c4d5e';
const BATCH_OLD = '0a1b2c3d-4e5f-4a6b-8c7d-8e9f0a1b2c3d';

const CUSTODY_ROLE: SetRoleInfo = {code: 'custody', required: true, multiple: true, extensions: ['.xlsx'], description: 'Custody transactions', max_history: 'P1Y'};
const CASH_ROLE: SetRoleInfo = {code: 'cash', required: true, multiple: true, extensions: ['.csv'], description: 'Cash statement', max_history: 'P5Y', must_cover: 'custody'};

const PLUGINS: SetPluginInfo[] = [
    {code: GENERIC, name: 'Generic CSV', report_roles: []},
    {code: DANSKE, name: 'Danske Bank', docs_url: '/mkdocs/user/transactions/import/danske-bank/', report_roles: [CUSTODY_ROLE, CASH_ROLE]},
    {code: OTHER_SET, name: 'Other Bank', report_roles: [{code: 'statement', required: true, multiple: false, extensions: ['.csv'], description: 'Statement'}]},
    {code: 'broker_legacy', name: 'Legacy', report_roles: null},
    {code: 'broker_bare', name: 'Bare'},
];

/** An uploaded original of broker 7 in the new batch; every test overrides what it is about. */
const file = (over: Partial<SetFileInfo> & {file_id: string}): SetFileInfo => ({
    filename: `${over.file_id}.csv`,
    uploaded_at: '2026-09-30T10:00:00Z',
    status: 'uploaded',
    target_broker_id: BROKER,
    batch_id: BATCH_NEW,
    kind: 'original',
    compatible_plugins: [DANSKE],
    ...over,
});

const ids = (files: SetFileInfo[]) => files.map((f) => f.file_id);

// The files of broker 7, in the order the API listed them.
const GEN_1 = file({file_id: 'gen-1', filename: 'generic_simple.csv', uploaded_at: '2026-09-30T10:00:00Z', compatible_plugins: [GENERIC]});
const CUSTODY_NEW = file({file_id: 'custody-new', filename: 'Transactions.xlsx', uploaded_at: '2026-09-30T10:00:07Z', compatible_plugins: [DANSKE]});
const COMBINED_OLD = file({file_id: 'combined-old', filename: 'Danske Bank — combined 2025-08-01…2026-07-31.csv', uploaded_at: '2026-08-15T09:05:00Z', batch_id: BATCH_OLD, kind: 'combined', compatible_plugins: [DANSKE]});
const CASH_OLD = file({file_id: 'cash-old', filename: 'statement-2025.csv', uploaded_at: '2026-08-15T09:00:00Z', batch_id: BATCH_OLD, compatible_plugins: [DANSKE, GENERIC]});
const CASH_NEW = file({file_id: 'cash-new', filename: 'statement.csv', uploaded_at: '2026-09-30T10:00:03Z', compatible_plugins: [DANSKE, GENERIC]});
const LEGACY = file({file_id: 'legacy', filename: 'old-export.csv', uploaded_at: '2026-01-10T08:00:00Z', batch_id: null, compatible_plugins: [DANSKE, GENERIC]});
const GEN_2 = file({file_id: 'gen-2', filename: 'manual.csv', uploaded_at: '2026-09-29T18:00:00Z', batch_id: undefined, compatible_plugins: [GENERIC]});
const BROKER_FILES = [GEN_1, CUSTODY_NEW, COMBINED_OLD, CASH_OLD, CASH_NEW, LEGACY, GEN_2];

const KEY_NEW = `set:${BROKER}:${DANSKE}:${BATCH_NEW}`;
const KEY_OLD = `set:${BROKER}:${DANSKE}:${BATCH_OLD}`;

/** The sets of broker 7 as the wizard holds them; built by hand so these tests do not lean on groupBrokerFiles. */
const SET_NEW: ReportSetGroup = {key: KEY_NEW, brokerId: BROKER, pluginCode: DANSKE, batchId: BATCH_NEW, uploadedAt: '2026-09-30T10:00:03Z', files: [CASH_NEW, CUSTODY_NEW]};
const SET_OLD: ReportSetGroup = {key: KEY_OLD, brokerId: BROKER, pluginCode: DANSKE, batchId: BATCH_OLD, uploadedAt: '2026-08-15T09:00:00Z', files: [CASH_OLD]};

const sel = (fileId: string, pluginCode = DANSKE): SelectedFileLike => ({fileId, fileName: `${fileId}.name`, brokerId: BROKER, pluginCode});

/** A unit reduced to what tells two units apart: its kind, and the files it analyses. */
const unitShape = (unit: ParseUnit) => (unit.kind === 'file' ? ['file', unit.file.fileId] : ['set', unit.set.key, unit.members.map((m) => m.fileId)]);

// ---------------------------------------------------------------------------
// isReportSetPlugin
// ---------------------------------------------------------------------------

describe('isReportSetPlugin', () => {
    it('is true for a plugin that declares report roles', async () => {
        const isReportSetPlugin = await c2('isReportSetPlugin');
        expect(isReportSetPlugin(PLUGINS[1])).toBe(true);
        expect(isReportSetPlugin(PLUGINS[2])).toBe(true);
    });

    it('is false for a single-file plugin: empty, null or absent roles', async () => {
        const isReportSetPlugin = await c2('isReportSetPlugin');
        expect(isReportSetPlugin({code: GENERIC, name: 'Generic CSV', report_roles: []})).toBe(false);
        expect(isReportSetPlugin({code: 'broker_legacy', name: 'Legacy', report_roles: null})).toBe(false);
        expect(isReportSetPlugin({code: 'broker_bare', name: 'Bare'})).toBe(false);
    });

    it('is false for no plugin at all', async () => {
        const isReportSetPlugin = await c2('isReportSetPlugin');
        expect(isReportSetPlugin(null)).toBe(false);
        expect(isReportSetPlugin(undefined)).toBe(false);
    });
});

// ---------------------------------------------------------------------------
// setPluginFor (A18)
// ---------------------------------------------------------------------------

describe('setPluginFor', () => {
    it('picks the report-set plugin that reads the file', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [DANSKE, GENERIC]}), PLUGINS)).toBe(DANSKE);
    });

    it('A18: the set plugin wins wherever it sits in compatible_plugins, even behind the generic CSV', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [GENERIC, DANSKE]}), PLUGINS)).toBe(DANSKE);
    });

    it('takes the first report-set plugin of the list when two can read the file', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [GENERIC, OTHER_SET, DANSKE]}), PLUGINS)).toBe(OTHER_SET);
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [DANSKE, OTHER_SET]}), PLUGINS)).toBe(DANSKE);
    });

    it('is null when only single-file plugins read the file', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [GENERIC, 'broker_legacy', 'broker_bare']}), PLUGINS)).toBeNull();
    });

    it('is null when no plugin reads the file', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: []}), PLUGINS)).toBeNull();
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: null}), PLUGINS)).toBeNull();
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: undefined}), PLUGINS)).toBeNull();
    });

    it('does not take a code missing from the plugin catalogue for a set plugin', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: ['broker_not_in_catalogue', DANSKE]}), PLUGINS)).toBe(DANSKE);
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: ['broker_not_in_catalogue']}), PLUGINS)).toBeNull();
    });

    it('is null for a combined file: it is the result of a set, never a member', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', kind: 'combined', compatible_plugins: [DANSKE]}), PLUGINS)).toBeNull();
        expect(setPluginFor(file({file_id: 'x', kind: 'combined', compatible_plugins: [DANSKE]}), PLUGINS, DANSKE)).toBeNull();
    });

    it('is null for a file with no upload batch (uploaded before report sets, or empty)', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', batch_id: null}), PLUGINS)).toBeNull();
        expect(setPluginFor(file({file_id: 'x', batch_id: undefined}), PLUGINS)).toBeNull();
        expect(setPluginFor(file({file_id: 'x', batch_id: ''}), PLUGINS)).toBeNull();
        expect(setPluginFor(file({file_id: 'x', batch_id: null}), PLUGINS, DANSKE)).toBeNull();
    });

    it('a manual choice of a report-set plugin is the set plugin, ahead of the priority order', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [DANSKE, OTHER_SET]}), PLUGINS, OTHER_SET)).toBe(OTHER_SET);
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [DANSKE, GENERIC]}), PLUGINS, DANSKE)).toBe(DANSKE);
    });

    it('a manual choice of a single-file plugin takes the file out of every set', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [DANSKE, GENERIC]}), PLUGINS, GENERIC)).toBeNull();
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [DANSKE, GENERIC]}), PLUGINS, 'broker_not_in_catalogue')).toBeNull();
    });

    it('a null override means no manual choice', async () => {
        const setPluginFor = await c2('setPluginFor');
        expect(setPluginFor(file({file_id: 'x', compatible_plugins: [GENERIC, DANSKE]}), PLUGINS, null)).toBe(DANSKE);
    });
});

// ---------------------------------------------------------------------------
// reportSetKey
// ---------------------------------------------------------------------------

describe('reportSetKey', () => {
    it('is set:<broker>:<plugin>:<batch>', async () => {
        const reportSetKey = await c2('reportSetKey');
        expect(reportSetKey(BROKER, DANSKE, BATCH_NEW)).toBe(`set:7:broker_danske_bank:${BATCH_NEW}`);
        expect(reportSetKey(12, OTHER_SET, 'b')).toBe('set:12:broker_other_bank:b');
    });
});

// ---------------------------------------------------------------------------
// groupBrokerFiles
// ---------------------------------------------------------------------------

describe('groupBrokerFiles', () => {
    it('one set per upload batch and set plugin; combined files in neither list; singles in input order', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const {sets, singles} = groupBrokerFiles(BROKER, BROKER_FILES, PLUGINS);

        expect(sets.map((s) => s.key)).toEqual([KEY_NEW, KEY_OLD]);
        expect(ids(singles)).toEqual(['gen-1', 'legacy', 'gen-2']);
        const listed = [...sets.flatMap((s) => ids(s.files)), ...ids(singles)];
        expect(listed).not.toContain('combined-old');
    });

    it('describes each set: broker of the argument, plugin, batch, earliest upload, members by upload time', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const {sets} = groupBrokerFiles(BROKER, BROKER_FILES, PLUGINS);
        const fresh = sets.find((s) => s.key === KEY_NEW);
        const old = sets.find((s) => s.key === KEY_OLD);

        expect(fresh).toMatchObject({brokerId: BROKER, pluginCode: DANSKE, batchId: BATCH_NEW, uploadedAt: '2026-09-30T10:00:03Z'});
        // cash-new was uploaded at :03, custody-new at :07 — the input listed them the other way round.
        expect(ids(fresh?.files ?? [])).toEqual(['cash-new', 'custody-new']);
        // A batch with one export is still a set: the incomplete one of the design (case D).
        expect(old).toMatchObject({brokerId: BROKER, pluginCode: DANSKE, batchId: BATCH_OLD, uploadedAt: '2026-08-15T09:00:00Z'});
        expect(ids(old?.files ?? [])).toEqual(['cash-old']);
    });

    it('orders the members of a set by upload time, then by file name', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const at = '2026-09-30T10:00:00Z';
        const files = [file({file_id: 'b', filename: 'b-custody.xlsx', uploaded_at: at}), file({file_id: 'c', filename: 'c-cash.csv', uploaded_at: '2026-09-30T09:59:59Z'}), file({file_id: 'a', filename: 'a-cash.csv', uploaded_at: at})];
        const {sets} = groupBrokerFiles(BROKER, files, PLUGINS);

        expect(sets).toHaveLength(1);
        expect(ids(sets[0].files)).toEqual(['c', 'a', 'b']);
        expect(sets[0].uploadedAt).toBe('2026-09-30T09:59:59Z');
    });

    it('orders the sets from the newest upload; on a tie, by key', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const at = '2026-09-30T10:00:00Z';
        const files = [file({file_id: 'old', uploaded_at: '2026-01-01T00:00:00Z', batch_id: BATCH_OLD}), file({file_id: 'other', uploaded_at: at, compatible_plugins: [OTHER_SET]}), file({file_id: 'danske', uploaded_at: at, compatible_plugins: [DANSKE]})];
        const {sets} = groupBrokerFiles(BROKER, files, PLUGINS);

        expect(sets.map((s) => s.key)).toEqual([KEY_NEW, `set:${BROKER}:${OTHER_SET}:${BATCH_NEW}`, KEY_OLD]);
    });

    it('A18: a member the generic CSV could also read stays in the set of its report-set plugin', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const files = [file({file_id: 'cash', compatible_plugins: [GENERIC, DANSKE]}), file({file_id: 'custody', compatible_plugins: [DANSKE]})];
        const {sets, singles} = groupBrokerFiles(BROKER, files, PLUGINS);

        expect(sets.map((s) => [s.key, ids(s.files).sort()])).toEqual([[KEY_NEW, ['cash', 'custody']]]);
        expect(singles).toEqual([]);
    });

    it('an override to a single-file plugin turns a member into a single, in its input position', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const {sets, singles} = groupBrokerFiles(BROKER, BROKER_FILES, PLUGINS, new Map([['cash-new', GENERIC]]));
        const fresh = sets.find((s) => s.key === KEY_NEW);

        expect(ids(fresh?.files ?? [])).toEqual(['custody-new']);
        expect(fresh?.uploadedAt).toBe('2026-09-30T10:00:07Z');
        expect(ids(singles)).toEqual(['gen-1', 'cash-new', 'legacy', 'gen-2']);
    });

    it('an override to another report-set plugin moves the member into that plugin\u2019s set of the same batch', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const files = [file({file_id: 'custody', uploaded_at: '2026-09-30T10:00:07Z', compatible_plugins: [DANSKE]}), file({file_id: 'cash', uploaded_at: '2026-09-30T10:00:03Z', compatible_plugins: [DANSKE, OTHER_SET]}), CASH_OLD];
        const {sets} = groupBrokerFiles(BROKER, files, PLUGINS, new Map([['cash', OTHER_SET]]));

        expect(sets.map((s) => [s.key, ids(s.files)])).toEqual([
            [KEY_NEW, ['custody']],
            [`set:${BROKER}:${OTHER_SET}:${BATCH_NEW}`, ['cash']],
            [KEY_OLD, ['cash-old']],
        ]);
    });

    it('keys every set on the broker it is given', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const {sets} = groupBrokerFiles(42, [file({file_id: 'only'})], PLUGINS);

        expect(sets.map((s) => [s.key, s.brokerId])).toEqual([[`set:42:${DANSKE}:${BATCH_NEW}`, 42]]);
    });

    it('returns two empty lists for a broker without files', async () => {
        const groupBrokerFiles = await c2('groupBrokerFiles');
        expect(groupBrokerFiles(BROKER, [], PLUGINS)).toEqual({sets: [], singles: []});
    });
});

// ---------------------------------------------------------------------------
// setSelectionState
// ---------------------------------------------------------------------------

describe('setSelectionState', () => {
    it('is all, some or none of the set members', async () => {
        const setSelectionState = await c2('setSelectionState');
        expect(setSelectionState(SET_NEW, new Set(['cash-new', 'custody-new']))).toBe('all');
        expect(setSelectionState(SET_NEW, new Set(['custody-new', 'gen-1']))).toBe('some');
        expect(setSelectionState(SET_NEW, new Set(['gen-1', 'cash-old']))).toBe('none');
        expect(setSelectionState(SET_NEW, new Set())).toBe('none');
    });
});

// ---------------------------------------------------------------------------
// combinedFileForSet
// ---------------------------------------------------------------------------

describe('combinedFileForSet', () => {
    const combined = (file_id: string, uploaded_at: string, over: Partial<SetFileInfo> = {}) => file({file_id, uploaded_at, kind: 'combined', compatible_plugins: [DANSKE], ...over});

    it('is the newest combined file of the same broker, batch and plugin', async () => {
        const combinedFileForSet = await c2('combinedFileForSet');
        const files = [
            combined('combined-noon', '2026-09-30T12:00:00Z'),
            combined('other-broker', '2026-09-30T13:00:00Z', {target_broker_id: 8}),
            combined('combined-eleven', '2026-09-30T11:00:00Z'),
            combined('other-batch', '2026-09-30T14:00:00Z', {batch_id: BATCH_OLD}),
            combined('other-plugin', '2026-09-30T15:00:00Z', {compatible_plugins: [OTHER_SET]}),
            file({file_id: 'an-original', uploaded_at: '2026-09-30T16:00:00Z'}),
        ];

        expect(combinedFileForSet(SET_NEW, files)?.file_id).toBe('combined-noon');
    });

    it('is null while the set was never combined', async () => {
        const combinedFileForSet = await c2('combinedFileForSet');
        expect(combinedFileForSet(SET_NEW, [CASH_NEW, CUSTODY_NEW, COMBINED_OLD])).toBeNull();
        expect(combinedFileForSet(SET_NEW, [])).toBeNull();
    });

    it('finds the combined file of an older batch for that batch\u2019s set', async () => {
        const combinedFileForSet = await c2('combinedFileForSet');
        expect(combinedFileForSet(SET_OLD, BROKER_FILES)?.file_id).toBe('combined-old');
    });
});

// ---------------------------------------------------------------------------
// buildParseUnits
// ---------------------------------------------------------------------------

describe('buildParseUnits', () => {
    it('the selected members of a set become one unit, at the position of the first one', async () => {
        const buildParseUnits = await c2('buildParseUnits');
        const units = buildParseUnits([sel('gen-1', GENERIC), sel('custody-new'), sel('gen-2', GENERIC), sel('cash-new')], [SET_NEW, SET_OLD]);

        expect(units.map(unitShape)).toEqual([
            ['file', 'gen-1'],
            ['set', KEY_NEW, ['custody-new', 'cash-new']],
            ['file', 'gen-2'],
        ]);
    });

    it('carries the set and the selected members themselves', async () => {
        const buildParseUnits = await c2('buildParseUnits');
        const custody = sel('custody-new');
        const cash = sel('cash-new');
        const units = buildParseUnits([cash, custody], [SET_NEW]);

        expect(units).toMatchObject([{kind: 'set', set: SET_NEW, members: [cash, custody]}]);
    });

    it('a member selected with another plugin is analysed alone', async () => {
        const buildParseUnits = await c2('buildParseUnits');
        const units = buildParseUnits([sel('cash-new', GENERIC), sel('custody-new')], [SET_NEW]);

        expect(units.map(unitShape)).toEqual([
            ['file', 'cash-new'],
            ['set', KEY_NEW, ['custody-new']],
        ]);
    });

    it('two sets selected are two units, each at its first member', async () => {
        const buildParseUnits = await c2('buildParseUnits');
        const units = buildParseUnits([sel('cash-old'), sel('gen-1', GENERIC), sel('custody-new'), sel('cash-new')], [SET_NEW, SET_OLD]);

        expect(units.map(unitShape)).toEqual([
            ['set', KEY_OLD, ['cash-old']],
            ['file', 'gen-1'],
            ['set', KEY_NEW, ['custody-new', 'cash-new']],
        ]);
    });

    it('a file of no set is a file unit carrying the selection', async () => {
        const buildParseUnits = await c2('buildParseUnits');
        const only = sel('gen-1', GENERIC);

        expect(buildParseUnits([only], [SET_NEW])).toMatchObject([{kind: 'file', file: only}]);
        expect(buildParseUnits([], [SET_NEW])).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// setBlocksAnalysis
// ---------------------------------------------------------------------------

describe('setBlocksAnalysis', () => {
    const ALL = new Set(['cash-new', 'custody-new']);
    const SOME = new Set(['custody-new']);
    const READY_COMPLETE: SetPreviewState = {status: 'ready', preview: {complete: true}};
    const READY_INCOMPLETE: SetPreviewState = {status: 'ready', preview: {complete: false}};

    it('never blocks a set none of whose files is selected (excluded from the import)', async () => {
        const setBlocksAnalysis = await c2('setBlocksAnalysis');
        expect(setBlocksAnalysis(SET_NEW, new Set(['gen-1']), READY_INCOMPLETE)).toBe(false);
        expect(setBlocksAnalysis(SET_NEW, new Set(), {status: 'loading'})).toBe(false);
        expect(setBlocksAnalysis(SET_NEW, new Set())).toBe(false);
    });

    it('blocks a selected set until its preview is known', async () => {
        const setBlocksAnalysis = await c2('setBlocksAnalysis');
        expect(setBlocksAnalysis(SET_NEW, ALL)).toBe(true);
        expect(setBlocksAnalysis(SET_NEW, ALL, {status: 'loading'})).toBe(true);
    });

    it('blocks a selected set whose preview failed', async () => {
        const setBlocksAnalysis = await c2('setBlocksAnalysis');
        expect(setBlocksAnalysis(SET_NEW, ALL, {status: 'error', error: 'HTTP 500'})).toBe(true);
    });

    it('blocks a selected set the preview calls incomplete, or that came back without a preview', async () => {
        const setBlocksAnalysis = await c2('setBlocksAnalysis');
        expect(setBlocksAnalysis(SET_NEW, ALL, READY_INCOMPLETE)).toBe(true);
        expect(setBlocksAnalysis(SET_NEW, SOME, READY_INCOMPLETE)).toBe(true);
        expect(setBlocksAnalysis(SET_NEW, ALL, {status: 'ready', preview: null})).toBe(true);
    });

    it('lets a selected complete set through, wholly or partly selected', async () => {
        const setBlocksAnalysis = await c2('setBlocksAnalysis');
        expect(setBlocksAnalysis(SET_NEW, ALL, READY_COMPLETE)).toBe(false);
        expect(setBlocksAnalysis(SET_NEW, SOME, READY_COMPLETE)).toBe(false);
    });
});

// ---------------------------------------------------------------------------
// parseIsoPeriod and dayBefore
// ---------------------------------------------------------------------------

describe('parseIsoPeriod', () => {
    it.each([
        ['P1Y', {years: 1, months: 0, days: 0}],
        ['P5Y', {years: 5, months: 0, days: 0}],
        ['P6M', {years: 0, months: 6, days: 0}],
        ['P90D', {years: 0, months: 0, days: 90}],
        ['P1Y6M', {years: 1, months: 6, days: 0}],
        ['P1Y2M3D', {years: 1, months: 2, days: 3}],
    ])('reads %s', async (value, expected) => {
        const parseIsoPeriod = await c2('parseIsoPeriod');
        expect(parseIsoPeriod(value)).toEqual(expected);
    });

    it.each([[null], [undefined], [''], ['garbage'], ['PT5H'], ['1Y']])('is null for %j', async (value) => {
        const parseIsoPeriod = await c2('parseIsoPeriod');
        expect(parseIsoPeriod(value)).toBeNull();
    });
});

describe('dayBefore', () => {
    it.each([
        ['2020-03-01', '2020-02-29'],
        ['2021-03-01', '2021-02-28'],
        ['2020-01-01', '2019-12-31'],
        ['2020-02-03', '2020-02-02'],
        ['2020-03-30', '2020-03-29'],
        ['2020-10-26', '2020-10-25'],
        ['2020-11-02', '2020-11-01'],
    ])('the day before %s is %s, on the calendar', async (value, expected) => {
        const dayBefore = await c2('dayBefore');
        expect(dayBefore(value)).toBe(expected);
    });
});

// ---------------------------------------------------------------------------
// buildSetTimeline
// ---------------------------------------------------------------------------

describe('buildSetTimeline', () => {
    const ROLES = ['custody', 'cash'];
    // The Danske shape: one custody export inside a longer cash statement.
    const custody = {file_id: 'f-custody', role: 'custody', coverage: [{axis: 'trade', start: '2020-02-03', end: '2020-06-26'}]};
    const cash = {file_id: 'f-cash', role: 'cash', coverage: [{axis: 'value', start: '2019-07-01', end: '2020-06-30'}]};
    // 2019-07-01 → 2020-06-30 is 365 days; the custody export starts 217 days in and lasts 144.
    const SPAN = 365;

    const rowOf = (timeline: SetTimeline | null, role: string) => timeline?.rows.find((row) => row.role === role);

    it('spans the oldest to the newest covered day, one row per role in the plugin order', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [cash, custody], history_start: null}, ROLES);

        expect(timeline).not.toBeNull();
        expect(timeline?.start).toBe('2019-07-01');
        expect(timeline?.end).toBe('2020-06-30');
        expect(timeline?.rows.map((row) => row.role)).toEqual(['custody', 'cash']);
        expect(timeline?.history).toBeNull();
    });

    it('places each coverage as a bar, in percent of the span counted in days', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [custody, cash]}, ROLES);
        const [custodyBar] = rowOf(timeline, 'custody')?.bars ?? [];
        const [cashBar] = rowOf(timeline, 'cash')?.bars ?? [];

        expect(rowOf(timeline, 'custody')?.bars).toHaveLength(1);
        expect(custodyBar).toMatchObject({start: '2020-02-03', end: '2020-06-26', fileId: 'f-custody'});
        expect(custodyBar.leftPct).toBeCloseTo((217 / SPAN) * 100, 6);
        expect(custodyBar.widthPct).toBeCloseTo((144 / SPAN) * 100, 6);
        expect(rowOf(timeline, 'cash')?.bars).toHaveLength(1);
        expect(cashBar).toMatchObject({start: '2019-07-01', end: '2020-06-30', fileId: 'f-cash'});
        expect(cashBar.leftPct).toBeCloseTo(0, 6);
        expect(cashBar.widthPct).toBeCloseTo(100, 6);
    });

    it('F2: draws the LibreFolio history from H0 to history_end — no longer to the end — with its count', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [custody, cash], history_start: '2020-01-01', history_end: '2020-03-31', history_count: 42}, ROLES);

        expect(timeline?.start).toBe('2019-07-01');
        expect(timeline?.end).toBe('2020-06-30');
        expect(timeline?.history).toMatchObject({start: '2020-01-01', end: '2020-03-31', count: 42});
        // H0 is 184 days into the span; the history lasts 90 days to its newest transaction.
        expect(timeline?.history?.leftPct).toBeCloseTo((184 / SPAN) * 100, 6);
        expect(timeline?.history?.widthPct).toBeCloseTo((90 / SPAN) * 100, 6);
    });

    it('F2: stretches the span to an H0 older than every file; the history still ends on history_end', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [custody, cash], history_start: '2019-01-01', history_end: '2019-12-31', history_count: 5}, ROLES);
        // 2019-01-01 → 2020-06-30 is 546 days.
        const [cashBar] = rowOf(timeline, 'cash')?.bars ?? [];
        const [custodyBar] = rowOf(timeline, 'custody')?.bars ?? [];

        expect(timeline?.start).toBe('2019-01-01');
        expect(timeline?.end).toBe('2020-06-30');
        expect(timeline?.history).toMatchObject({start: '2019-01-01', end: '2019-12-31', count: 5});
        expect(timeline?.history?.leftPct).toBeCloseTo(0, 6);
        expect(timeline?.history?.widthPct).toBeCloseTo((364 / 546) * 100, 6);
        expect(cashBar.leftPct).toBeCloseTo((181 / 546) * 100, 6);
        expect(cashBar.widthPct).toBeCloseTo((365 / 546) * 100, 6);
        expect(custodyBar.leftPct).toBeCloseTo((398 / 546) * 100, 6);
        expect(custodyBar.widthPct).toBeCloseTo((144 / 546) * 100, 6);
    });

    it('F2: a history_end newer than every file stretches the span to it', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [custody, cash], history_start: '2020-01-01', history_end: '2020-09-30', history_count: 12}, ROLES);
        // 2019-07-01 → 2020-09-30 is 457 days; the history lasts 273 of them.
        const [cashBar] = rowOf(timeline, 'cash')?.bars ?? [];

        expect(timeline?.start).toBe('2019-07-01');
        expect(timeline?.end).toBe('2020-09-30');
        expect(timeline?.history).toMatchObject({start: '2020-01-01', end: '2020-09-30', count: 12});
        expect(timeline?.history?.leftPct).toBeCloseTo((184 / 457) * 100, 6);
        expect(timeline?.history?.widthPct).toBeCloseTo((273 / 457) * 100, 6);
        expect(cashBar.leftPct).toBeCloseTo(0, 6);
        expect(cashBar.widthPct).toBeCloseTo((365 / 457) * 100, 6);
    });

    it('F2: a history_end before H0 (the opening correction alone, dated on the eve) ends the history on H0', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [custody, cash], history_start: '2020-01-01', history_end: '2019-12-31', history_count: 1}, ROLES);

        expect(timeline?.start).toBe('2019-07-01');
        expect(timeline?.end).toBe('2020-06-30');
        expect(timeline?.history).toMatchObject({start: '2020-01-01', end: '2020-01-01', count: 1});
        expect(timeline?.history?.leftPct).toBeCloseTo((184 / SPAN) * 100, 6);
        expect(timeline?.history?.widthPct).toBeCloseTo(0, 6);
    });

    it('F2: without history_end the history is H0 alone, and without history_count it counts 0', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [custody, cash], history_start: '2020-01-01', history_end: null}, ROLES);

        expect(timeline?.end).toBe('2020-06-30');
        expect(timeline?.history).toMatchObject({start: '2020-01-01', end: '2020-01-01', count: 0});
        expect(timeline?.history?.leftPct).toBeCloseTo((184 / SPAN) * 100, 6);
        expect(timeline?.history?.widthPct).toBeCloseTo(0, 6);
    });

    it('F2: no history without H0 (guard: true before F2 too)', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [custody, cash], history_start: null, history_end: null, history_count: 0}, ROLES);

        expect(timeline).not.toBeNull();
        expect(timeline?.history).toBeNull();
    });

    it('one bar per coverage entry: several files of a role, several axes of a file', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const firstYear = {file_id: 'f-c1', role: 'custody', coverage: [{axis: 'trade', start: '2020-01-02', end: '2020-03-31'}]};
        const secondYear = {file_id: 'f-c2', role: 'custody', coverage: [{axis: 'trade', start: '2020-07-01', end: '2020-12-30'}]};
        const twoAxes = {
            file_id: 'f-cash',
            role: 'cash',
            coverage: [
                {axis: 'trade', start: '2020-01-02', end: '2020-12-30'},
                {axis: 'value', start: '2020-01-03', end: '2020-12-31'},
            ],
        };
        const timeline = buildSetTimeline({members: [firstYear, twoAxes, secondYear]}, ROLES);
        // 2020-01-02 → 2020-12-31 is 364 days; the second custody file starts 181 days in and lasts 182.
        const custodyBars = rowOf(timeline, 'custody')?.bars ?? [];
        const second = custodyBars.find((bar) => bar.fileId === 'f-c2');

        expect(custodyBars.map((bar) => bar.fileId).sort()).toEqual(['f-c1', 'f-c2']);
        expect(second?.leftPct).toBeCloseTo((181 / 364) * 100, 6);
        expect(second?.widthPct).toBeCloseTo((182 / 364) * 100, 6);
        expect(rowOf(timeline, 'cash')?.bars.map((bar) => [bar.fileId, bar.start])).toEqual(
            expect.arrayContaining([
                ['f-cash', '2020-01-02'],
                ['f-cash', '2020-01-03'],
            ]),
        );
        expect(rowOf(timeline, 'cash')?.bars).toHaveLength(2);
    });

    it('skips members without a known role, and roles without members', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        // The unknown members sit inside the span of the others, so they change nothing else.
        const unknown = {file_id: 'f-unknown', role: null, coverage: [{axis: 'trade', start: '2020-03-01', end: '2020-03-31'}]};
        const mystery = {file_id: 'f-mystery', role: 'mystery', coverage: [{axis: 'trade', start: '2020-04-01', end: '2020-04-30'}]};
        const timeline = buildSetTimeline({members: [unknown, cash, mystery]}, ['custody', 'cash', 'statement']);

        expect(timeline?.rows.map((row) => row.role)).toEqual(['cash']);
        expect(timeline?.rows.flatMap((row) => row.bars.map((bar) => bar.fileId))).toEqual(['f-cash']);
    });

    it('a one-day span puts every bar at 0 with full width', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const timeline = buildSetTimeline({members: [{file_id: 'f-day', role: 'cash', coverage: [{axis: 'value', start: '2020-05-05', end: '2020-05-05'}]}]}, ROLES);
        const [bar] = rowOf(timeline, 'cash')?.bars ?? [];

        expect(timeline?.start).toBe('2020-05-05');
        expect(timeline?.end).toBe('2020-05-05');
        expect(bar.leftPct).toBeCloseTo(0, 6);
        expect(bar.widthPct).toBeCloseTo(100, 6);
    });

    it('is null when no member has a coverage', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        expect(buildSetTimeline({members: []}, ROLES)).toBeNull();
        expect(buildSetTimeline({members: [{file_id: 'f-empty', role: 'cash', coverage: []}], history_start: '2020-01-01'}, ROLES)).toBeNull();
        // F2: the history fields do not draw a timeline on their own either.
        expect(buildSetTimeline({members: [{file_id: 'f-empty', role: 'cash', rows: 0, coverage: []}], history_start: '2020-01-01', history_end: '2020-06-30', history_count: 9}, ROLES)).toBeNull();
    });

    // -----------------------------------------------------------------------
    // F2 (U2-B): the rows of each bar, the order of the bars, the gaps of each role
    // -----------------------------------------------------------------------

    it('F2: each bar carries the rows of its file, every axis of a file the same; null when the member does not say', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const counted = {...custody, rows: 15};
        const twoAxes = {
            file_id: 'f-cash-2',
            role: 'cash',
            rows: 32,
            coverage: [
                {axis: 'trade', start: '2019-07-01', end: '2020-06-29'},
                {axis: 'value', start: '2019-07-02', end: '2020-06-30'},
            ],
        };
        const timeline = buildSetTimeline({members: [counted, twoAxes]}, ROLES);
        const silent = buildSetTimeline({members: [cash]}, ROLES);

        expect(rowOf(timeline, 'custody')?.bars.map((bar) => [bar.fileId, bar.rows])).toEqual([['f-custody', 15]]);
        expect(rowOf(timeline, 'cash')?.bars.map((bar) => [bar.fileId, bar.rows])).toEqual([
            ['f-cash-2', 32],
            ['f-cash-2', 32],
        ]);
        expect(rowOf(silent, 'cash')?.bars).toHaveLength(1);
        expect(rowOf(silent, 'cash')?.bars[0].rows).toBeNull();
    });

    it('F2: the bars of a role come in order of start, then end, whatever the order of the members and of their axes', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const late = {file_id: 'f-late', role: 'custody', coverage: [{axis: 'trade', start: '2020-07-01', end: '2020-12-30'}]};
        const long = {file_id: 'f-long', role: 'custody', coverage: [{axis: 'trade', start: '2020-01-02', end: '2020-03-31'}]};
        const short = {file_id: 'f-short', role: 'custody', coverage: [{axis: 'trade', start: '2020-01-02', end: '2020-02-14'}]};
        const twoAxes = {
            file_id: 'f-cash',
            role: 'cash',
            coverage: [
                {axis: 'value', start: '2020-01-03', end: '2020-12-31'},
                {axis: 'trade', start: '2020-01-02', end: '2020-12-30'},
            ],
        };
        const timeline = buildSetTimeline({members: [late, twoAxes, long, short]}, ROLES);

        expect(rowOf(timeline, 'custody')?.bars.map((bar) => [bar.fileId, bar.start, bar.end])).toEqual([
            ['f-short', '2020-01-02', '2020-02-14'],
            ['f-long', '2020-01-02', '2020-03-31'],
            ['f-late', '2020-07-01', '2020-12-30'],
        ]);
        expect(rowOf(timeline, 'cash')?.bars.map((bar) => [bar.start, bar.end])).toEqual([
            ['2020-01-02', '2020-12-30'],
            ['2020-01-03', '2020-12-31'],
        ]);
    });

    it('F2: a gap runs from the day after the furthest end reached to the eve of the next bar, placed like a bar', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const first = {file_id: 'f-c1', role: 'custody', coverage: [{axis: 'trade', start: '2020-01-02', end: '2020-03-31'}]};
        const second = {file_id: 'f-c2', role: 'custody', coverage: [{axis: 'trade', start: '2020-07-01', end: '2020-12-30'}]};
        const wholeYear = {file_id: 'f-cash', role: 'cash', coverage: [{axis: 'value', start: '2020-01-02', end: '2020-12-31'}]};
        const timeline = buildSetTimeline({members: [second, wholeYear, first]}, ROLES);
        // 2020-01-02 → 2020-12-31 is 364 days; the hole starts 90 days in and lasts 90.
        const gaps = rowOf(timeline, 'custody')?.gaps ?? [];

        expect(gaps).toHaveLength(1);
        expect(gaps[0]).toMatchObject({start: '2020-04-01', end: '2020-06-30'});
        expect(gaps[0].leftPct).toBeCloseTo((90 / 364) * 100, 6);
        expect(gaps[0].widthPct).toBeCloseTo((90 / 364) * 100, 6);
        expect(rowOf(timeline, 'cash')?.gaps).toEqual([]);
    });

    it('F2: one gap per hole, in date order', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        const january = {file_id: 'f-jan', role: 'custody', coverage: [{axis: 'trade', start: '2020-01-02', end: '2020-01-31'}]};
        const march = {file_id: 'f-mar', role: 'custody', coverage: [{axis: 'trade', start: '2020-03-02', end: '2020-03-31'}]};
        const june = {file_id: 'f-jun', role: 'custody', coverage: [{axis: 'trade', start: '2020-06-01', end: '2020-06-30'}]};
        const halfYear = {file_id: 'f-cash', role: 'cash', coverage: [{axis: 'value', start: '2020-01-02', end: '2020-06-30'}]};
        const timeline = buildSetTimeline({members: [june, january, halfYear, march]}, ROLES);
        // 2020-01-02 → 2020-06-30 is 180 days.
        const gaps = rowOf(timeline, 'custody')?.gaps ?? [];

        expect(gaps.map((gap) => [gap.start, gap.end])).toEqual([
            ['2020-02-01', '2020-03-01'],
            ['2020-04-01', '2020-05-31'],
        ]);
        expect(gaps[0].leftPct).toBeCloseTo((30 / 180) * 100, 6);
        expect(gaps[0].widthPct).toBeCloseTo((29 / 180) * 100, 6);
        expect(gaps[1].leftPct).toBeCloseTo((90 / 180) * 100, 6);
        expect(gaps[1].widthPct).toBeCloseTo((60 / 180) * 100, 6);
    });

    it('F2: bars that touch or overlap leave no gap; the walk keeps the furthest end, not the previous bar\u2019s', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        // Cash: the second statement starts the day after the first ends.
        const cashQ1 = {file_id: 'f-cash-q1', role: 'cash', coverage: [{axis: 'value', start: '2020-01-02', end: '2020-03-31'}]};
        const cashRest = {file_id: 'f-cash-rest', role: 'cash', coverage: [{axis: 'value', start: '2020-04-01', end: '2020-12-30'}]};
        // Custody: a year-long export, and two short ones inside it — between those two, no hole.
        const year = {file_id: 'f-year', role: 'custody', coverage: [{axis: 'trade', start: '2020-01-02', end: '2020-12-30'}]};
        const march = {file_id: 'f-mar', role: 'custody', coverage: [{axis: 'trade', start: '2020-03-01', end: '2020-03-31'}]};
        const june = {file_id: 'f-jun', role: 'custody', coverage: [{axis: 'trade', start: '2020-06-01', end: '2020-06-30'}]};
        const timeline = buildSetTimeline({members: [june, cashRest, year, cashQ1, march]}, ROLES);

        expect(rowOf(timeline, 'custody')?.bars).toHaveLength(3);
        expect(rowOf(timeline, 'custody')?.gaps).toEqual([]);
        expect(rowOf(timeline, 'cash')?.bars).toHaveLength(2);
        expect(rowOf(timeline, 'cash')?.gaps).toEqual([]);
    });

    it('F2: never a gap before the first bar or after the last, whatever stretches the span', async () => {
        const buildSetTimeline = await c2('buildSetTimeline');
        // Custody sits inside a longer cash statement, and the history reaches past both.
        const timeline = buildSetTimeline({members: [custody, cash], history_start: '2019-01-01', history_end: '2020-09-30', history_count: 3}, ROLES);

        expect(timeline?.start).toBe('2019-01-01');
        expect(timeline?.end).toBe('2020-09-30');
        expect(rowOf(timeline, 'custody')?.gaps).toEqual([]);
        expect(rowOf(timeline, 'cash')?.gaps).toEqual([]);
    });
});

// ===========================================================================
// Phase C3 — the badges of FilesTable (files page and the broker's import files)
// ===========================================================================
//
// Pinned in the plan (C3.0): `setsOfFiles(files, plugins)` maps every member of a set to its set,
// with `groupBrokerFiles` broker by broker; `fileSetBadges(file, ctx)` gives the badges of one
// file in the fixed order combined · stale · usedInCombined · set · incomplete. What the plan
// leaves open is pinned here, from what FilesTable holds: the context is `{sets, files, previews}`
// — the map of `setsOfFiles`, every listed file (a set's combined file is among them) and the
// previews by set key (`SetPreviewState`, its preview carrying `missing`) — and a badge is
// `{kind}` plus `names`/`deleted` (combined), `uploadedAt` (set) and `roles` (incomplete).

interface BadgePreviewState {
    status: 'loading' | 'ready' | 'error';
    preview?: {complete?: boolean | null; missing?: Array<{role: string; start?: string | null; end?: string | null}> | null} | null;
    error?: string | null;
}
interface FileSetBadge {
    kind: 'combined' | 'stale' | 'usedInCombined' | 'set' | 'incomplete';
    names?: string[];
    deleted?: string[];
    uploadedAt?: string;
    roles?: string[];
}
interface BadgeContext {
    sets: ReadonlyMap<string, ReportSetGroup>;
    files: SetFileInfo[];
    previews: ReadonlyMap<string, BadgePreviewState>;
}
interface ReportSetBadgesModule {
    setsOfFiles(files: SetFileInfo[], plugins: SetPluginInfo[]): Map<string, ReportSetGroup>;
    fileSetBadges(file: SetFileInfo, ctx: BadgeContext): FileSetBadge[];
}

/** One C3 export of the module, loaded for the test that needs it. */
async function c3<K extends keyof ReportSetBadgesModule>(name: K): Promise<ReportSetBadgesModule[K]> {
    let mod: Partial<ReportSetBadgesModule>;
    try {
        mod = (await import('./importReportSets')) as unknown as Partial<ReportSetBadgesModule>;
    } catch (error) {
        throw new Error(`importReportSets.ts cannot be loaded: ${String(error)}`);
    }
    const fn = mod[name];
    if (typeof fn !== 'function') throw new Error(`importReportSets.${name} is not implemented yet (file-set badges, phase C3)`);
    return fn as ReportSetBadgesModule[K];
}

const kinds = (badges: FileSetBadge[]) => badges.map((badge) => badge.kind);

// ---------------------------------------------------------------------------
// setsOfFiles
// ---------------------------------------------------------------------------

describe('setsOfFiles', () => {
    // Broker 7: a set of two exports, its combined file, a generic single. Broker 8: one export of
    // the same batch id — another broker, another set. And a file with no broker at all.
    const CUSTODY_7 = file({file_id: 'custody-7', filename: 'Transactions.xlsx', uploaded_at: '2026-09-30T10:00:07Z'});
    const CASH_7 = file({file_id: 'cash-7', filename: 'statement.csv', uploaded_at: '2026-09-30T10:00:03Z', compatible_plugins: [DANSKE, GENERIC]});
    const COMBINED_7 = file({file_id: 'combined-7', filename: 'combined.csv', uploaded_at: '2026-09-30T10:05:00Z', kind: 'combined'});
    const GENERIC_7 = file({file_id: 'generic-7', filename: 'generic_simple.csv', batch_id: null, compatible_plugins: [GENERIC]});
    const CUSTODY_8 = file({file_id: 'custody-8', filename: 'Transactions.xlsx', target_broker_id: 8});
    const NO_BROKER = file({file_id: 'no-broker', filename: 'legacy.xlsx', target_broker_id: null});
    const FILES = [GENERIC_7, CUSTODY_7, CUSTODY_8, COMBINED_7, NO_BROKER, CASH_7];

    it('maps every member of a set to its set, broker by broker', async () => {
        const setsOfFiles = await c3('setsOfFiles');
        const sets = setsOfFiles(FILES, PLUGINS);

        expect([...sets.keys()].sort()).toEqual(['cash-7', 'custody-7', 'custody-8']);
        expect(sets.get('custody-7')?.key).toBe(KEY_NEW);
        expect(sets.get('cash-7')?.key).toBe(KEY_NEW);
        expect(sets.get('custody-8')?.key).toBe(`set:8:${DANSKE}:${BATCH_NEW}`);
        expect(sets.get('custody-8')?.brokerId).toBe(8);
    });

    it('each set is the one groupBrokerFiles builds for its broker', async () => {
        const setsOfFiles = await c3('setsOfFiles');
        const groupBrokerFiles = await c2('groupBrokerFiles');
        const sets = setsOfFiles(FILES, PLUGINS);
        const [expected7] = groupBrokerFiles(BROKER, [GENERIC_7, CUSTODY_7, COMBINED_7, CASH_7], PLUGINS).sets;
        const [expected8] = groupBrokerFiles(8, [CUSTODY_8], PLUGINS).sets;

        expect(sets.get('custody-7')).toEqual(expected7);
        expect(sets.get('cash-7')).toEqual(expected7);
        expect(ids(sets.get('cash-7')?.files ?? [])).toEqual(['cash-7', 'custody-7']);
        expect(sets.get('custody-8')).toEqual(expected8);
    });

    it('leaves out combined files, single files and files without a broker', async () => {
        const setsOfFiles = await c3('setsOfFiles');
        const sets = setsOfFiles(FILES, PLUGINS);

        for (const fileId of ['combined-7', 'generic-7', 'no-broker']) expect(sets.has(fileId), fileId).toBe(false);
    });

    it('is empty for no files', async () => {
        const setsOfFiles = await c3('setsOfFiles');
        expect(setsOfFiles([], PLUGINS).size).toBe(0);
    });
});

// ---------------------------------------------------------------------------
// fileSetBadges
// ---------------------------------------------------------------------------

describe('fileSetBadges', () => {
    // The set of the new batch: two originals, combined into `combined-new`.
    const ORIG_CUSTODY = file({file_id: 'orig-custody', filename: 'Transactions.xlsx', uploaded_at: '2026-09-30T10:00:07Z', combined_into: ['combined-new']});
    const ORIG_CASH = file({file_id: 'orig-cash', filename: 'statement.csv', uploaded_at: '2026-09-30T10:00:03Z', compatible_plugins: [DANSKE, GENERIC], combined_into: ['combined-new']});
    const combinedNew = (over: Partial<SetFileInfo> = {}) =>
        file({
            file_id: 'combined-new',
            filename: 'Danske Bank — combined.csv',
            uploaded_at: '2026-09-30T10:05:00Z',
            kind: 'combined',
            derived_from: [
                {file_id: 'orig-custody', role: 'custody', filename: 'Transactions.xlsx', deleted: false},
                {file_id: 'orig-cash', role: 'cash', filename: 'statement.csv', deleted: false},
            ],
            combined_into: [],
            combine_is_stale: false,
            ...over,
        });
    // The set of the old batch: a custody export alone, never combined.
    const LONE_CUSTODY = file({file_id: 'lone-custody', filename: 'Transactions-2025.xlsx', uploaded_at: '2026-08-15T09:00:00Z', batch_id: BATCH_OLD, combined_into: []});
    const SINGLE = file({file_id: 'single', filename: 'generic_simple.csv', batch_id: null, compatible_plugins: [GENERIC], combined_into: []});

    /** Built by hand, so these tests do not lean on setsOfFiles. */
    const SET_COMBINED: ReportSetGroup = {key: KEY_NEW, brokerId: BROKER, pluginCode: DANSKE, batchId: BATCH_NEW, uploadedAt: '2026-09-30T10:00:03Z', files: [ORIG_CASH, ORIG_CUSTODY]};
    const SET_LONE: ReportSetGroup = {key: KEY_OLD, brokerId: BROKER, pluginCode: DANSKE, batchId: BATCH_OLD, uploadedAt: '2026-08-15T09:00:00Z', files: [LONE_CUSTODY]};
    const SETS = new Map<string, ReportSetGroup>([
        ['orig-custody', SET_COMBINED],
        ['orig-cash', SET_COMBINED],
        ['lone-custody', SET_LONE],
    ]);

    const COMPLETE: BadgePreviewState = {status: 'ready', preview: {complete: true, missing: []}};
    const MISSING_CASH: BadgePreviewState = {status: 'ready', preview: {complete: false, missing: [{role: 'cash', start: '2025-08-01', end: '2026-07-31'}]}};

    const ctx = (previews: Array<[string, BadgePreviewState]>, combined: SetFileInfo = combinedNew()): BadgeContext => ({
        sets: SETS,
        files: [ORIG_CUSTODY, ORIG_CASH, combined, LONE_CUSTODY, SINGLE],
        previews: new Map(previews),
    });

    it('combined: the combined file, with the names of its originals and the deleted ones', async () => {
        const fileSetBadges = await c3('fileSetBadges');
        const combined = combinedNew({
            derived_from: [
                {file_id: 'orig-custody', role: 'custody', filename: 'Transactions.xlsx', deleted: false},
                {file_id: 'gone-cash', role: 'cash', filename: 'statement-2020.csv', deleted: true},
            ],
        });

        expect(fileSetBadges(combined, ctx([[KEY_NEW, COMPLETE]], combined))).toMatchObject([{kind: 'combined', names: ['Transactions.xlsx', 'statement-2020.csv'], deleted: ['statement-2020.csv']}]);
    });

    it('combined, then stale, on a combined file built by an older plugin version', async () => {
        const fileSetBadges = await c3('fileSetBadges');
        const stale = combinedNew({combine_is_stale: true});

        expect(kinds(fileSetBadges(stale, ctx([[KEY_NEW, COMPLETE]], stale)))).toEqual(['combined', 'stale']);
    });

    it('usedInCombined, then set with the date of the set, on an original of a combined set', async () => {
        const fileSetBadges = await c3('fileSetBadges');

        expect(fileSetBadges(ORIG_CUSTODY, ctx([[KEY_NEW, COMPLETE]]))).toMatchObject([{kind: 'usedInCombined'}, {kind: 'set', uploadedAt: '2026-09-30T10:00:03Z'}]);
        expect(kinds(fileSetBadges(ORIG_CASH, ctx([[KEY_NEW, COMPLETE]])))).toEqual(['usedInCombined', 'set']);
    });

    it('set, then incomplete with the missing roles, on a member of a set the preview calls incomplete', async () => {
        const fileSetBadges = await c3('fileSetBadges');

        expect(fileSetBadges(LONE_CUSTODY, ctx([[KEY_OLD, MISSING_CASH]]))).toMatchObject([
            {kind: 'set', uploadedAt: '2026-08-15T09:00:00Z'},
            {kind: 'incomplete', roles: ['cash']},
        ]);
    });

    it('no incomplete while the preview loads, after it failed, or before it was asked', async () => {
        const fileSetBadges = await c3('fileSetBadges');

        expect(kinds(fileSetBadges(LONE_CUSTODY, ctx([[KEY_OLD, {status: 'loading'}]])))).toEqual(['set']);
        expect(kinds(fileSetBadges(LONE_CUSTODY, ctx([[KEY_OLD, {status: 'error', error: 'HTTP 500'}]])))).toEqual(['set']);
        expect(kinds(fileSetBadges(LONE_CUSTODY, ctx([])))).toEqual(['set']);
        expect(kinds(fileSetBadges(LONE_CUSTODY, ctx([[KEY_OLD, COMPLETE]])))).toEqual(['set']);
    });

    it('v5.3: no incomplete on a set whose combined file is up to date, even when the preview calls it incomplete', async () => {
        const fileSetBadges = await c3('fileSetBadges');
        // The cash original was deleted after the combine: the preview misses it, the combined file still holds it.
        expect(kinds(fileSetBadges(ORIG_CUSTODY, ctx([[KEY_NEW, MISSING_CASH]])))).toEqual(['usedInCombined', 'set']);
    });

    it('incomplete again once that combined file is stale: the fixed order of an original, usedInCombined · set · incomplete', async () => {
        const fileSetBadges = await c3('fileSetBadges');
        const stale = combinedNew({combine_is_stale: true});

        expect(kinds(fileSetBadges(ORIG_CUSTODY, ctx([[KEY_NEW, MISSING_CASH]], stale)))).toEqual(['usedInCombined', 'set', 'incomplete']);
    });

    it('the combined file of another batch does not cover a set', async () => {
        const fileSetBadges = await c3('fileSetBadges');
        // combined-new is fresh, but it belongs to the new batch: the lone custody export of the old one stays incomplete.
        expect(kinds(fileSetBadges(LONE_CUSTODY, ctx([[KEY_OLD, MISSING_CASH]])))).toEqual(['set', 'incomplete']);
    });

    it('usedInCombined is about the original, whatever its set', async () => {
        const fileSetBadges = await c3('fileSetBadges');
        const combinedOutsideSets = file({file_id: 'orig-elsewhere', filename: 'elsewhere.csv', batch_id: null, compatible_plugins: [GENERIC], combined_into: ['combined-new']});

        expect(kinds(fileSetBadges(combinedOutsideSets, ctx([])))).toEqual(['usedInCombined']);
    });

    it('no badge on a single file', async () => {
        const fileSetBadges = await c3('fileSetBadges');
        expect(fileSetBadges(SINGLE, ctx([[KEY_NEW, COMPLETE]]))).toEqual([]);
        expect(fileSetBadges(file({file_id: 'bare', batch_id: null, compatible_plugins: [GENERIC]}), ctx([]))).toEqual([]);
    });
});
