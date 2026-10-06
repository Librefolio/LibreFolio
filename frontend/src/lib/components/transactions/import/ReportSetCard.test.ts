// @vitest-environment jsdom
/**
 * ReportSetCard — one report set in the import wizard's step 2 (phase F2 of the Danske Bank
 * workstream, U1-B and U2-B). Component test (Vitest + jsdom).
 *
 * The props do not change in F2 (set, plugin, previewState, selection, expanded, analysed,
 * uploadingRole and the seven callbacks). What changes is how an open card shows the set, and the
 * contract pinned here is the plan's (F2.0):
 *
 * U1-B — the files of a role in a table:
 *   report-set-role-table (data-role) — one per role with members, holding a DataTable whose body
 *     rows are tr[data-row-id=<file_id>], ordered by period start (the earliest start among the
 *     member's coverage entries), then file name; members without coverage last. No selection
 *     column: the set is chosen whole with report-set-select.
 *   Row actions: the DataTable menu row-actions-<file_id> → context-menu → context-menu-action-preview
 *     (onPreviewFile(file_id)) and context-menu-action-delete (onDeleteFile(the SetFileInfo of
 *     set.files)); a double click on a row previews it.
 *   report-set-unrecognised (data-file-id) — a member without a role, outside every role table.
 *   report-set-member is gone. A role without members keeps its report-set-missing block.
 *
 * U2-B — the timeline (report-set-timeline):
 *   report-set-timeline-bar (data-role, data-file-id, data-start, data-end, data-rows) — one per
 *     coverage entry; report-set-timeline-gap (data-role, data-start, data-end) — a hole between two
 *     files of a role; report-set-timeline-history (data-start = H0, data-end = history_end,
 *     data-count) — absent without H0; report-set-timeline-legend with
 *     report-set-timeline-legend-item (data-kind = file, and history / gap only when there are some).
 *   Infobox: a click on a bar, a gap or the history opens a Tooltip (tooltip-content) with its start
 *     and end (formatIsoDay), and the file's rows or the history's count.
 *
 * Everything else of the card stays: the guards at the end are true before F2 too.
 *
 * Nothing here reads translated text: the assertions are on testids, data attributes, the order of
 * rows, the callbacks, and values the test itself passed in — file ids, row counts, and dates
 * formatted by the app's own `formatIsoDay`, so the expected strings follow the runtime locale.
 *
 * Two jsdom gaps, filled here and nowhere in the product:
 *   - no layout: every rect is 0×0, and the row menu closes itself at once when its anchor has no
 *     size; the ⋮ button gets a rect inside jsdom's viewport before it is clicked;
 *   - no hit testing: a pointer click lands on the innermost element under the pointer and bubbles
 *     up; the infobox tests click the innermost first descendant of a bar, so the event crosses the
 *     bar and any Tooltip trigger wrapped around it or inside it.
 * Two fixture guards at the end prove both techniques on DataTable and Tooltip alone: a red above
 * is about the card, not about the harness.
 *
 * The component is loaded once, in a `beforeAll` with its own timeout (the first transform is cold
 * and takes seconds); a load failure is recorded and every test then fails on its own, saying so.
 *
 * Phase G (plan §14 G.2, A + B + C) — the user chooses how the set is read. Existing props unchanged;
 * new ones: `plugins` (the catalogue, with names and report roles), `brokerDefaultPlugin`,
 * `onReadAs(code | null)`, `onReadAlone(fileId, code)`, `onRemoveFromSet(fileId)`. `mountCard` passes
 * them to every mount, so the F2 tests above keep their meaning once the card reads them.
 *   A  report-set-read-as — a native <select> in the header, valued at the set's plugin: one option per
 *      report-set plugin that reads every member (setPluginChoices, the set's own first) and one
 *      value="" to read the files one by one; a change calls onReadAs(code), or onReadAs(null) for "".
 *   B  in each role table's row menu: read-alone-<code> for each single-file plugin that reads the row's
 *      file (readAlonePlugins), calling onReadAlone(fileId, code); remove-from-set on every row, calling
 *      onRemoveFromSet(fileId). Preview and Delete stay.
 *   C1 report-set-default-note[data-default-plugin] when defaultPluginNote is not null.
 *   C2 report-set-also-recognised[data-file-id][data-plugins] for each member another report-set plugin
 *      also reads (otherSetPlugins, codes comma-separated).
 * The invented catalogue: the set's plugin, a single-file plugin that reads the cash statements, and a
 * second report-set plugin that reads one custody export only (cu-early) — every member of the
 * one-file set, so A has a second plugin to offer there.
 *
 * Plan: `LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md`, F2.0 and §14 G.2.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, type Component} from 'svelte';

// Every API method is inert: the card receives its data as props.
vi.mock('$lib/api', async () => {
    const generated = await vi.importActual<{schemas: unknown}>('$lib/api/generated');
    const inert = () =>
        new Proxy(
            {},
            {
                get(_target, property) {
                    if (typeof property !== 'string' || property === 'then') return undefined;
                    return vi.fn(async () => undefined);
                },
            },
        );
    class ApiError extends Error {}
    return {zodiosApi: inert(), axiosInstance: inert(), ApiError, schemas: generated.schemas};
});

import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {formatIsoDay} from '$lib/utils/transactions/importReportSets';

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

const CARD_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./ReportSetCard.svelte');
// The fixture guards mount the two shared pieces the jsdom techniques of this file go through.
const DATA_TABLE_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('../../table/DataTable.svelte');
const TOOLTIP_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('../../ui/feedback/Tooltip.svelte');

let loaded: {ReportSetCard: Component<Record<string, unknown>>} | {error: unknown} | undefined;
let harnessLoaded: {DataTable: Component<Record<string, unknown>>; Tooltip: Component<Record<string, unknown>>} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = CARD_MODULES['./ReportSetCard.svelte'];
        if (!load) throw new Error('ReportSetCard.svelte cannot be found next to this test');
        loaded = {ReportSetCard: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
    try {
        const loadTable = DATA_TABLE_MODULES['../../table/DataTable.svelte'];
        const loadTooltip = TOOLTIP_MODULES['../../ui/feedback/Tooltip.svelte'];
        if (!loadTable || !loadTooltip) throw new Error('DataTable.svelte / Tooltip.svelte cannot be found');
        harnessLoaded = {DataTable: (await loadTable()).default, Tooltip: (await loadTooltip()).default};
    } catch (error) {
        harnessLoaded = {error};
    }
}, 60_000);

function card(): Component<Record<string, unknown>> {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.ReportSetCard;
}

function harness(): {DataTable: Component<Record<string, unknown>>; Tooltip: Component<Record<string, unknown>>} {
    if (harnessLoaded === undefined) throw new Error('the fixture-guard components were never loaded: their beforeAll did not run');
    if ('error' in harnessLoaded) {
        const {error} = harnessLoaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return harnessLoaded;
}

beforeAll(async () => {
    await setupI18n();
    setPrivacyEnabled(false);
});

// ---------------------------------------------------------------------------
// Fixtures: an invented two-role plugin and two previews of one of its sets
// ---------------------------------------------------------------------------

const BROKER = 7;
const PLUGIN_CODE = 'broker_probe_set';
const BATCH = '6f1c2d3e-4a5b-4c6d-8e7f-901a2b3c4d5e';
const SET_KEY = `set:${BROKER}:${PLUGIN_CODE}:${BATCH}`;

const CUSTODY_ROLE = {code: 'custody', required: true, multiple: true, extensions: ['.xlsx'], description: 'Probe custody export', max_history: 'P1Y'};
const CASH_ROLE = {code: 'cash', required: true, multiple: true, extensions: ['.csv'], description: 'Probe cash statement', max_history: 'P5Y', must_cover: 'custody'};
const PLUGIN = {code: PLUGIN_CODE, name: 'Probe Set Bank', docs_url: null, report_roles: [CUSTODY_ROLE, CASH_ROLE]};
// G: a single-file plugin that reads the cash statements, and a second report-set plugin that reads one custody export.
const SINGLE_CODE = 'broker_probe_single_csv';
const SECOND_SET_CODE = 'broker_probe_second_bank';
const SINGLE_PLUGIN = {code: SINGLE_CODE, name: 'Probe Single CSV', docs_url: null, report_roles: []};
const SECOND_SET_PLUGIN = {code: SECOND_SET_CODE, name: 'Probe Second Bank', docs_url: null, report_roles: [{code: 'statement', required: true, multiple: false, extensions: ['.xlsx'], description: 'Probe second-bank statement'}]};
const CATALOGUE = [PLUGIN, SINGLE_PLUGIN, SECOND_SET_PLUGIN];

type Coverage = {axis: 'trade' | 'value'; start: string; end: string};

/** An uploaded original of the set; `second` orders the uploads; `compatible` adds plugins to the set's own. */
function setFile(file_id: string, filename: string, second: number, compatible: string[] = []) {
    return {
        file_id,
        filename,
        uploaded_at: `2026-09-30T10:00:${String(second).padStart(2, '0')}Z`,
        status: 'uploaded',
        target_broker_id: BROKER,
        batch_id: BATCH,
        kind: 'original',
        compatible_plugins: [PLUGIN_CODE, ...compatible],
    };
}

function member(file: ReturnType<typeof setFile>, role: string | null, rows: number, coverage: Coverage[]) {
    return {file_id: file.file_id, filename: file.filename, role, rows, coverage};
}

// The uploads, in upload order. The custody files arrive out of period order; two start on the same
// day (the name decides); one has no coverage at all (its name would sort it first). G: the cash
// statements are also read by the single-file plugin, cu-early by the second report-set plugin.
const CU_LATE = setFile('cu-late', 'probe-custody-b.xlsx', 1);
const CU_EMPTY = setFile('cu-empty', 'probe-custody-0.xlsx', 2);
const CU_EARLY = setFile('cu-early', 'probe-custody-c.xlsx', 3, [SECOND_SET_CODE]);
const CU_TIE = setFile('cu-tie', 'probe-custody-a.xlsx', 4);
// The second cash statement has two axes: its trade axis starts first, before the older statement.
const CA_OLD = setFile('ca-old', 'probe-cash-z.csv', 5, [SINGLE_CODE]);
const CA_TWO = setFile('ca-two', 'probe-cash-y.csv', 6, [SINGLE_CODE]);
const STRAY = setFile('stray', 'probe-notes.csv', 7);
const FILES = [CU_LATE, CU_EMPTY, CU_EARLY, CU_TIE, CA_OLD, CA_TWO, STRAY];

/** Row counts that no date of the fixture contains as a number of its own. */
const ROWS = {late: 63, early: 58, tie: 47, old: 129, two: 386} as const;
const HISTORY = {start: '2020-02-10', end: '2020-09-15', count: 74} as const;
const CUSTODY_GAP = {start: '2020-04-01', end: '2020-06-30'} as const;

const MEMBERS = [
    member(CU_LATE, 'custody', ROWS.late, [{axis: 'trade', start: '2020-07-01', end: '2020-12-30'}]),
    member(CU_EMPTY, 'custody', 0, []),
    member(CU_EARLY, 'custody', ROWS.early, [{axis: 'trade', start: '2020-01-02', end: '2020-03-31'}]),
    member(CU_TIE, 'custody', ROWS.tie, [{axis: 'trade', start: '2020-01-02', end: '2020-02-14'}]),
    member(CA_OLD, 'cash', ROWS.old, [{axis: 'value', start: '2019-06-03', end: '2019-11-29'}]),
    member(CA_TWO, 'cash', ROWS.two, [
        {axis: 'value', start: '2019-06-04', end: '2020-12-31'},
        {axis: 'trade', start: '2019-06-01', end: '2020-12-30'},
    ]),
    member(STRAY, null, 0, []),
];

const SET = {key: SET_KEY, brokerId: BROKER, pluginCode: PLUGIN_CODE, batchId: BATCH, uploadedAt: CU_LATE.uploaded_at, files: FILES};

/** A complete set with a history in LibreFolio and a hole between two custody files. */
const PREVIEW = {
    broker_id: BROKER,
    plugin_code: PLUGIN_CODE,
    batch_id: BATCH,
    members: MEMBERS,
    roles: [
        {code: 'custody', required: true, multiple: true, status: 'present', file_ids: ['cu-late', 'cu-empty', 'cu-early', 'cu-tie']},
        {code: 'cash', required: true, multiple: true, status: 'present', file_ids: ['ca-old', 'ca-two']},
    ],
    missing: [],
    segments: [
        {start: '2020-01-02', end: '2020-03-31'},
        {start: '2020-07-01', end: '2020-12-30'},
    ],
    gaps: [CUSTODY_GAP],
    history_start: HISTORY.start,
    history_end: HISTORY.end,
    history_count: HISTORY.count,
    warnings: [{severity: 'warning', code: 'probe_warning_code', message: 'Probe warning message', context: null}],
    complete: true,
};

/** The same set before its cash statement: one custody file, nothing in LibreFolio yet. */
const SET_INCOMPLETE = {...SET, files: [CU_EARLY]};
const PREVIEW_INCOMPLETE = {
    broker_id: BROKER,
    plugin_code: PLUGIN_CODE,
    batch_id: BATCH,
    members: [member(CU_EARLY, 'custody', ROWS.early, [{axis: 'trade', start: '2020-01-02', end: '2020-03-31'}])],
    roles: [
        {code: 'custody', required: true, multiple: true, status: 'present', file_ids: ['cu-early']},
        {code: 'cash', required: true, multiple: true, status: 'missing', file_ids: []},
    ],
    missing: [{role: 'cash', start: '2020-01-01', end: '2020-03-31'}],
    segments: [],
    gaps: [],
    history_start: null,
    history_end: null,
    history_count: 0,
    warnings: [],
    complete: false,
};

// ---------------------------------------------------------------------------
// Mounting and reading
// ---------------------------------------------------------------------------

async function mountCard(options: {set?: unknown; preview?: unknown; expanded?: boolean; selection?: 'all' | 'some' | 'none'; brokerDefaultPlugin?: string | null} = {}) {
    const callbacks = {
        onToggleSelected: vi.fn(),
        onToggleExpanded: vi.fn(),
        onUploadMissing: vi.fn(),
        onExclude: vi.fn(),
        onPreviewFile: vi.fn(),
        onDeleteFile: vi.fn(),
        // G: how the set is read.
        onReadAs: vi.fn(),
        onReadAlone: vi.fn(),
        onRemoveFromSet: vi.fn(),
    };
    render(card(), {
        set: options.set ?? SET,
        plugin: PLUGIN,
        previewState: {status: 'ready', preview: options.preview ?? PREVIEW, error: null},
        selection: options.selection ?? 'all',
        expanded: options.expanded ?? true,
        analysed: false,
        uploadingRole: null,
        plugins: CATALOGUE,
        brokerDefaultPlugin: options.brokerDefaultPlugin ?? null,
        ...callbacks,
    });
    // Barrier: the card is mounted before anything is read.
    await screen.findByTestId('report-set-card');
    return callbacks;
}

/** The one element with this testid and these data attributes; anything else fails with what was there. */
function the(testId: string, attributes: Record<string, string> = {}, scope: ParentNode = document): HTMLElement {
    const selector = `[data-testid="${testId}"]${Object.entries(attributes)
        .map(([name, value]) => `[data-${name}="${value}"]`)
        .join('')}`;
    const found = [...scope.querySelectorAll<HTMLElement>(selector)];
    if (found.length !== 1) {
        const present = [...scope.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`)].map((el) => ({...el.dataset}));
        throw new Error(`expected exactly one ${selector}, found ${found.length}; the ${testId} elements present: ${JSON.stringify(present)}`);
    }
    return found[0];
}

function all(testId: string, scope: ParentNode = document): HTMLElement[] {
    return [...scope.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`)];
}

/** Text as a reader sees it: whitespace runs collapsed. */
function text(el: Element): string {
    return (el.textContent ?? '').replace(/\s+/g, ' ').trim();
}

const roleTable = (role: string) => the('report-set-role-table', {role});

/** The body rows of a table, by their row id, in order. */
function bodyRowIds(scope: ParentNode): string[] {
    return [...scope.querySelectorAll<HTMLElement>('tbody tr[data-row-id]')].map((tr) => tr.dataset.rowId ?? '');
}

/** The one body row of a file. */
function rowOf(fileId: string, scope: ParentNode = document): HTMLElement {
    const found = [...scope.querySelectorAll<HTMLElement>('tbody tr[data-row-id]')].filter((tr) => tr.dataset.rowId === fileId);
    if (found.length !== 1) throw new Error(`expected exactly one row ${fileId}, found ${found.length}; rows: ${JSON.stringify(bodyRowIds(scope))}`);
    return found[0];
}

/** jsdom has no layout: give the ⋮ button a rect inside the 1024×768 viewport, or its menu closes at once. */
function withLayout(el: HTMLElement): HTMLElement {
    vi.spyOn(el, 'getBoundingClientRect').mockReturnValue({x: 100, y: 100, top: 100, left: 100, right: 124, bottom: 124, width: 24, height: 24, toJSON: () => ({})} as DOMRect);
    return el;
}

/** Open a file's row menu in its role table and pick one action. */
async function runRowAction(role: string, fileId: string, actionId: 'preview' | 'delete'): Promise<void> {
    await fireEvent.click(withLayout(the(`row-actions-${fileId}`, {}, roleTable(role))));
    const menu = await screen.findByTestId('context-menu');
    await fireEvent.click(within(menu).getByTestId(`context-menu-action-${actionId}`));
}

/** G: open a file's row menu in its role table, and leave it open. */
async function openRowMenu(role: string, fileId: string): Promise<HTMLElement> {
    await fireEvent.click(withLayout(the(`row-actions-${fileId}`, {}, roleTable(role))));
    return screen.findByTestId('context-menu');
}

/** G: the actions an open row menu offers, by the id in their testid, sorted. */
function menuActions(menu: HTMLElement): string[] {
    return [...menu.querySelectorAll<HTMLElement>('[data-testid^="context-menu-action-"]')].map((item) => (item.dataset.testid ?? '').replace(/^context-menu-action-/, '')).sort();
}

/** G: the select that says how the set is read. */
function readAsSelect(): HTMLSelectElement {
    return the('report-set-read-as') as HTMLSelectElement;
}

function optionValues(select: HTMLSelectElement): string[] {
    return [...select.options].map((option) => option.value);
}

/** Where a pointer click on an element lands: its innermost first descendant (see the header). */
function landingPoint(el: Element): Element {
    let node = el;
    while (node.firstElementChild) node = node.firstElementChild;
    return node;
}

/** Click an element of the timeline and read the one infobox it opens. */
async function openInfobox(el: Element): Promise<string> {
    await fireEvent.click(landingPoint(el));
    const tooltips = await screen.findAllByTestId('tooltip-content');
    expect(tooltips, 'one click opens one infobox').toHaveLength(1);
    return text(tooltips[0]);
}

/** `n` appears in `haystack` as a number of its own, not as part of a longer one. */
function hasNumber(haystack: string, n: number): boolean {
    return new RegExp(`(^|\\D)${n}(\\D|$)`).test(haystack);
}

// ---------------------------------------------------------------------------
// U1-B — the files of each role in a table
// ---------------------------------------------------------------------------

describe('ReportSetCard — F2 · U1-B: the files of each role in a table', () => {
    it('one role table per role with members, its body rows keyed by file id', async () => {
        await mountCard();

        expect(
            all('report-set-role-table')
                .map((table) => table.dataset.role)
                .sort(),
        ).toEqual(['cash', 'custody']);
        expect([...bodyRowIds(roleTable('custody'))].sort()).toEqual(['cu-early', 'cu-empty', 'cu-late', 'cu-tie']);
        expect([...bodyRowIds(roleTable('cash'))].sort()).toEqual(['ca-old', 'ca-two']);
    });

    it('rows in order of period start — the earliest of a file’s coverages — then name; a file without coverage last', async () => {
        await mountCard();

        expect(bodyRowIds(roleTable('custody')), 'uploaded late-first, listed by period').toEqual(['cu-tie', 'cu-early', 'cu-late', 'cu-empty']);
        expect(bodyRowIds(roleTable('cash')), 'the two-axis statement starts first, on its trade axis').toEqual(['ca-two', 'ca-old']);
    });

    it('no selection in the role tables: the set is chosen whole', async () => {
        await mountCard();

        for (const role of ['custody', 'cash']) {
            const table = roleTable(role);
            expect(bodyRowIds(table).length, `${role}: the table has rows`).toBeGreaterThan(0);
            expect(table.querySelectorAll('[data-testid^="dt-row-checkbox-"]'), `${role}: no row checkbox`).toHaveLength(0);
            expect(all('dt-select-all', table), `${role}: no select-all`).toHaveLength(0);
        }
    });

    it('the unrecognised file stands apart, in no role table; report-set-member is gone', async () => {
        await mountCard();

        const stray = the('report-set-unrecognised', {'file-id': 'stray'});
        expect(text(stray)).toContain(STRAY.filename);
        expect(
            all('report-set-role-table').some((table) => table.contains(stray)),
            'outside every role table',
        ).toBe(false);
        expect(all('report-set-role-table').flatMap((table) => bodyRowIds(table))).not.toContain('stray');
        expect(all('report-set-member')).toHaveLength(0);
    });

    it('the row menu previews a file', async () => {
        const {onPreviewFile, onDeleteFile} = await mountCard();

        await runRowAction('custody', 'cu-late', 'preview');

        expect(onPreviewFile).toHaveBeenCalledTimes(1);
        expect(onPreviewFile).toHaveBeenCalledWith('cu-late');
        expect(onDeleteFile).not.toHaveBeenCalled();
    });

    it('the row menu deletes a file: the wizard receives the file of the set', async () => {
        const {onPreviewFile, onDeleteFile} = await mountCard();

        await runRowAction('cash', 'ca-old', 'delete');

        expect(onDeleteFile).toHaveBeenCalledTimes(1);
        expect(onDeleteFile.mock.calls[0][0]).toEqual(CA_OLD);
        expect(onPreviewFile).not.toHaveBeenCalled();
    });

    it('a double click on a row previews its file', async () => {
        const {onPreviewFile} = await mountCard();

        await fireEvent.dblClick(rowOf('cu-early', roleTable('custody')));

        expect(onPreviewFile).toHaveBeenCalledTimes(1);
        expect(onPreviewFile).toHaveBeenCalledWith('cu-early');
    });

    it('a role without files keeps its missing block, and has no table', async () => {
        await mountCard({set: SET_INCOMPLETE, preview: PREVIEW_INCOMPLETE});

        expect(bodyRowIds(roleTable('custody'))).toEqual(['cu-early']);
        the('report-set-missing', {role: 'cash'});
        expect(all('report-set-role-table').map((table) => table.dataset.role)).toEqual(['custody']);
    });
});

// ---------------------------------------------------------------------------
// U2-B — the timeline
// ---------------------------------------------------------------------------

describe('ReportSetCard — F2 · U2-B: the timeline', () => {
    it('one bar per coverage entry, with its role, file, period and rows', async () => {
        await mountCard();

        const timeline = the('report-set-timeline');
        const bars = all('report-set-timeline-bar', timeline).map((bar) => [bar.dataset.role, bar.dataset.fileId, bar.dataset.start, bar.dataset.end, bar.dataset.rows].join(' '));
        expect([...bars].sort()).toEqual(
            [
                `custody cu-tie 2020-01-02 2020-02-14 ${ROWS.tie}`,
                `custody cu-early 2020-01-02 2020-03-31 ${ROWS.early}`,
                `custody cu-late 2020-07-01 2020-12-30 ${ROWS.late}`,
                `cash ca-old 2019-06-03 2019-11-29 ${ROWS.old}`,
                `cash ca-two 2019-06-04 2020-12-31 ${ROWS.two}`,
                `cash ca-two 2019-06-01 2020-12-30 ${ROWS.two}`,
            ].sort(),
        );
    });

    it("a gap where a role's files leave a hole — never before its first file or after its last", async () => {
        await mountCard();

        const gaps = all('report-set-timeline-gap', the('report-set-timeline')).map((gap) => [gap.dataset.role, gap.dataset.start, gap.dataset.end]);
        expect(gaps).toEqual([['custody', CUSTODY_GAP.start, CUSTODY_GAP.end]]);
    });

    it('the history LibreFolio holds runs from H0 to history_end, with its count', async () => {
        await mountCard();

        const history = the('report-set-timeline-history', {}, the('report-set-timeline'));
        expect(history).toHaveAttribute('data-start', HISTORY.start);
        expect(history).toHaveAttribute('data-end', HISTORY.end);
        expect(history).toHaveAttribute('data-count', String(HISTORY.count));
    });

    it('the legend names the files, and the history and the gaps when there are some', async () => {
        await mountCard();

        const legend = the('report-set-timeline-legend', {}, the('report-set-timeline'));
        expect(
            all('report-set-timeline-legend-item', legend)
                .map((item) => item.dataset.kind)
                .sort(),
        ).toEqual(['file', 'gap', 'history']);
    });

    it('without history and without holes: no history bar, no gap, a legend of files only', async () => {
        await mountCard({set: SET_INCOMPLETE, preview: PREVIEW_INCOMPLETE});

        const timeline = the('report-set-timeline');
        expect(all('report-set-timeline-bar', timeline).map((bar) => bar.dataset.fileId)).toEqual(['cu-early']);
        expect(all('report-set-timeline-history')).toHaveLength(0);
        expect(all('report-set-timeline-gap')).toHaveLength(0);
        expect(all('report-set-timeline-legend-item', the('report-set-timeline-legend', {}, timeline)).map((item) => item.dataset.kind)).toEqual(['file']);
    });
});

describe('ReportSetCard — F2 · U2-B: the infobox of the timeline', () => {
    it.each([
        {what: 'a custody bar', fileId: 'cu-late', start: '2020-07-01', end: '2020-12-30', rows: ROWS.late},
        {what: 'a cash bar', fileId: 'ca-old', start: '2019-06-03', end: '2019-11-29', rows: ROWS.old},
    ])('$what: its start, its end and the rows of its file', async ({fileId, start, end, rows}) => {
        await mountCard();

        const info = await openInfobox(the('report-set-timeline-bar', {'file-id': fileId}));

        expect(info).toContain(formatIsoDay(start));
        expect(info).toContain(formatIsoDay(end));
        expect(hasNumber(info, rows), `the rows of ${fileId} (${rows}) in "${info}"`).toBe(true);
    });

    it('a gap: its start and its end', async () => {
        await mountCard();

        const info = await openInfobox(the('report-set-timeline-gap', {role: 'custody'}));

        expect(info).toContain(formatIsoDay(CUSTODY_GAP.start));
        expect(info).toContain(formatIsoDay(CUSTODY_GAP.end));
    });

    it('the history: H0, its end, and how many transactions LibreFolio holds', async () => {
        await mountCard();

        const info = await openInfobox(the('report-set-timeline-history'));

        expect(info).toContain(formatIsoDay(HISTORY.start));
        expect(info).toContain(formatIsoDay(HISTORY.end));
        expect(hasNumber(info, HISTORY.count), `the count (${HISTORY.count}) in "${info}"`).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// Everything else of the card stays (guards: true before F2 too)
// ---------------------------------------------------------------------------

describe('ReportSetCard — the rest of the card is unchanged (guards)', () => {
    it('the card publishes its set, plugin, status, selection and state', async () => {
        await mountCard();

        const root = the('report-set-card');
        expect(root).toHaveAttribute('data-set-key', SET_KEY);
        expect(root).toHaveAttribute('data-batch-id', BATCH);
        expect(root).toHaveAttribute('data-plugin-code', PLUGIN_CODE);
        expect(root).toHaveAttribute('data-set-status', 'complete');
        expect(root).toHaveAttribute('data-selected', 'all');
        expect(root).toHaveAttribute('data-analysed', 'false');
        expect(root).toHaveAttribute('data-busy', 'false');
    });

    it('the set checkbox and the toggle call back', async () => {
        const {onToggleSelected, onToggleExpanded} = await mountCard();

        expect(the('report-set-toggle')).toHaveAttribute('aria-expanded', 'true');
        await fireEvent.click(the('report-set-select'));
        await fireEvent.click(the('report-set-toggle'));

        expect(onToggleSelected).toHaveBeenCalledTimes(1);
        expect(onToggleExpanded).toHaveBeenCalledTimes(1);
    });

    it('the notices, the history note and the timeline are there', async () => {
        await mountCard();

        the('report-set-warning', {code: 'probe_warning_code'});
        the('report-set-history', {kind: 'later'});
        the('report-set-timeline');
        expect(all('report-set-exclude'), 'a complete set does not block').toHaveLength(0);
    });

    it('an incomplete set: its missing export is uploaded into the role, and the set can be excluded', async () => {
        const {onUploadMissing, onExclude} = await mountCard({set: SET_INCOMPLETE, preview: PREVIEW_INCOMPLETE});

        expect(the('report-set-card')).toHaveAttribute('data-set-status', 'incomplete');
        const missing = the('report-set-missing', {role: 'cash'});
        the('report-set-upload-missing', {}, missing);
        const upload = new File(['probe'], 'probe-cash.csv', {type: 'text/csv'});
        await fireEvent.change(the('report-set-upload-input', {}, missing), {target: {files: [upload]}});
        await fireEvent.click(the('report-set-exclude'));

        expect(onUploadMissing).toHaveBeenCalledWith('cash', upload);
        expect(onExclude).toHaveBeenCalledTimes(1);
    });

    it('a folded card shows no body', async () => {
        await mountCard({expanded: false});

        expect(the('report-set-toggle')).toHaveAttribute('aria-expanded', 'false');
        expect(all('report-set-timeline')).toHaveLength(0);
        expect(all('report-set-role-table')).toHaveLength(0);
        expect(all('report-set-unrecognised')).toHaveLength(0);
    });
});

// ---------------------------------------------------------------------------
// G — how the set is read (plan §14 G.2: A, B, C)
// ---------------------------------------------------------------------------

describe('ReportSetCard — G · A: how the set is read', () => {
    it('a native select valued at the set’s plugin: that plugin and "one by one", when no other report-set plugin reads every member', async () => {
        await mountCard();

        const select = readAsSelect();
        expect(select.tagName).toBe('SELECT');
        expect(select).toHaveValue(PLUGIN_CODE);
        expect(optionValues(select).sort()).toEqual(['', PLUGIN_CODE]);
    });

    it('every report-set plugin that reads every member is offered, the set’s own first, and "one by one" once', async () => {
        // The one-file set: its custody export is read by the second report-set plugin too.
        await mountCard({set: SET_INCOMPLETE, preview: PREVIEW_INCOMPLETE});

        const values = optionValues(readAsSelect());
        expect(values.filter((value) => value !== '')).toEqual([PLUGIN_CODE, SECOND_SET_CODE]);
        expect(values.filter((value) => value === '')).toHaveLength(1);
        expect(readAsSelect()).toHaveValue(PLUGIN_CODE);
    });

    it('choosing another report-set plugin calls onReadAs with its code, once', async () => {
        const {onReadAs, onReadAlone, onRemoveFromSet} = await mountCard({set: SET_INCOMPLETE, preview: PREVIEW_INCOMPLETE});

        await fireEvent.change(readAsSelect(), {target: {value: SECOND_SET_CODE}});

        expect(onReadAs).toHaveBeenCalledTimes(1);
        expect(onReadAs).toHaveBeenCalledWith(SECOND_SET_CODE);
        expect(onReadAlone).not.toHaveBeenCalled();
        expect(onRemoveFromSet).not.toHaveBeenCalled();
    });

    it('choosing to read the files one by one calls onReadAs(null), once', async () => {
        const {onReadAs} = await mountCard();
        const select = readAsSelect();
        expect(optionValues(select), 'the "one by one" option is there to be chosen').toContain('');

        await fireEvent.change(select, {target: {value: ''}});

        expect(onReadAs).toHaveBeenCalledTimes(1);
        expect(onReadAs).toHaveBeenCalledWith(null);
    });

    it('it sits in the header: a folded card shows it too', async () => {
        await mountCard({expanded: false});

        expect(all('report-set-role-table'), 'the card is folded').toHaveLength(0);
        expect(the('report-set-card').contains(readAsSelect())).toBe(true);
        expect(readAsSelect()).toHaveValue(PLUGIN_CODE);
    });
});

describe('ReportSetCard — G · B: one file of the set, read another way', () => {
    it('a cash statement the single-file plugin reads: "read it alone" with that plugin calls onReadAlone(file, plugin)', async () => {
        const {onReadAlone, onRemoveFromSet, onReadAs} = await mountCard();

        const menu = await openRowMenu('cash', 'ca-old');
        await fireEvent.click(within(menu).getByTestId(`context-menu-action-read-alone-${SINGLE_CODE}`));

        expect(onReadAlone).toHaveBeenCalledTimes(1);
        expect(onReadAlone).toHaveBeenCalledWith('ca-old', SINGLE_CODE);
        expect(onRemoveFromSet).not.toHaveBeenCalled();
        expect(onReadAs).not.toHaveBeenCalled();
    });

    it('"remove from the set" calls onRemoveFromSet(file)', async () => {
        const {onRemoveFromSet, onReadAlone} = await mountCard();

        const menu = await openRowMenu('custody', 'cu-tie');
        await fireEvent.click(within(menu).getByTestId('context-menu-action-remove-from-set'));

        expect(onRemoveFromSet).toHaveBeenCalledTimes(1);
        expect(onRemoveFromSet).toHaveBeenCalledWith('cu-tie');
        expect(onReadAlone).not.toHaveBeenCalled();
    });

    it.each([
        {what: 'a cash statement', role: 'cash', fileId: 'ca-two', expected: ['delete', 'preview', `read-alone-${SINGLE_CODE}`, 'remove-from-set']},
        {what: 'a custody export no single-file plugin reads', role: 'custody', fileId: 'cu-late', expected: ['delete', 'preview', 'remove-from-set']},
        {what: 'a custody export another report-set plugin reads (a set plugin is never "read alone")', role: 'custody', fileId: 'cu-early', expected: ['delete', 'preview', 'remove-from-set']},
    ])('the row menu of $what: Preview, Delete, remove-from-set, and read-alone only with a plugin that reads it', async ({role, fileId, expected}) => {
        await mountCard();

        const menu = await openRowMenu(role, fileId);

        expect(menuActions(menu)).toEqual([...expected].sort());
    });
});

describe('ReportSetCard — G · C: what else reads these files', () => {
    it('C1: the broker’s default plugin is another one and reads a member: the note names it', async () => {
        await mountCard({brokerDefaultPlugin: SINGLE_CODE});

        expect(all('report-set-default-note').map((note) => note.dataset.defaultPlugin)).toEqual([SINGLE_CODE]);
    });

    it.each([
        {what: 'no default plugin', brokerDefaultPlugin: null, set: SET, preview: PREVIEW},
        {what: 'the set’s own plugin as the default', brokerDefaultPlugin: PLUGIN_CODE, set: SET, preview: PREVIEW},
        {what: 'a default that reads no member', brokerDefaultPlugin: SINGLE_CODE, set: SET_INCOMPLETE, preview: PREVIEW_INCOMPLETE},
    ])('C1 (guard: true before G too): no note with $what', async ({brokerDefaultPlugin, set, preview}) => {
        await mountCard({brokerDefaultPlugin, set, preview});

        the('report-set-timeline'); // presence barrier: the open card has rendered its body
        expect(all('report-set-default-note')).toHaveLength(0);
    });

    it('C2: each member another report-set plugin also reads gets its note, naming those plugins', async () => {
        await mountCard();

        expect(all('report-set-also-recognised').map((note) => [note.dataset.fileId, note.dataset.plugins])).toEqual([['cu-early', SECOND_SET_CODE]]);
    });

    it('C2 (guard: true before G too): no note when no member is read by another report-set plugin', async () => {
        const plain = {...SET, files: FILES.map((file) => ({...file, compatible_plugins: file.compatible_plugins.filter((code) => code !== SECOND_SET_CODE)}))};
        await mountCard({set: plain});

        the('report-set-timeline'); // presence barrier: the open card has rendered its body
        expect(all('report-set-also-recognised')).toHaveLength(0);
    });
});

// ---------------------------------------------------------------------------
// Fixture guards: the two jsdom techniques of this file, on the shared components alone
// ---------------------------------------------------------------------------

describe('ReportSetCard — fixture guards (the harness, not the product: true before and after F2)', () => {
    it('Fixture guard: a DataTable row menu opens in jsdom once its ⋮ button has a rect, and runs the chosen action', async () => {
        const {DataTable} = harness();
        const onClick = vi.fn();
        const row = {id: 'probe-row'};
        render(DataTable, {
            data: [row],
            columns: [{id: 'name', header: 'Name', type: 'text', cell: (item: {id: string}) => item.id}],
            getRowId: (item: {id: string}) => item.id,
            storageKey: 'report-set-card-fixture-guard',
            enableSelection: false,
            rowActions: [{id: 'probe', label: 'Probe action', onClick}],
        });

        await fireEvent.click(withLayout(await screen.findByTestId('row-actions-probe-row')));
        const menu = await screen.findByTestId('context-menu');
        await fireEvent.click(within(menu).getByTestId('context-menu-action-probe'));

        expect(onClick).toHaveBeenCalledTimes(1);
        expect(onClick).toHaveBeenCalledWith(row);
    });

    it('Fixture guard: a click on the innermost descendant of an element inside a Tooltip opens that Tooltip', async () => {
        const {Tooltip} = harness();
        const bar = createRawSnippet(() => ({render: () => '<div data-testid="probe-bar"><span><i></i></span></div>'}));
        render(Tooltip, {text: 'Probe infobox 4711', children: bar});

        const info = await openInfobox(await screen.findByTestId('probe-bar'));

        expect(info).toContain('Probe infobox 4711');
    });
});
