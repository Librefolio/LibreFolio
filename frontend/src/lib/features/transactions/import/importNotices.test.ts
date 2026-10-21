// @vitest-environment jsdom
/**
 * importNotices — the two kinds of BRIM notice, counted as they are shown (lot B-51). Unit test (Vitest + jsdom).
 *
 * A BRIM plugin's notices (`response.warnings`, `BrimNotice`) are of two kinds: an `info` is a blue NOTE — the plugin
 * explains a choice it made on purpose — and any other severity is an amber WARNING, which asks for attention. The rule
 * lives in `BrimNoticeList.svelte` (`severityOf`); step 3 of the import wizard ignored it in three places — the results
 * column, the stats tile, the parse detail — and counted every note as a warning: a Fineco file whose only notice is a
 * note read «⚠️ 1». The cure puts the rule and the counts in one pure module, `importNotices.ts`, next to this test.
 * Its contract (plan 04, B-51):
 *
 *   noticeSeverity(notice) — exactly `'info'` is `'info'`; `'warning'`, no severity, `null` and any other string
 *     (`'error'`, `'INFO'`…) are `'warning'`. The rule of BrimNoticeList: one case asks the list itself;
 *   noticeCounts(notices) — `{warnings, notes}` by that rule; `null`, `undefined` and `[]` count `{warnings: 0, notes: 0}`;
 *   splitNotices(notices) — `{warnings, notes}`: the very objects given, each list in their original relative order;
 *     nothing given, two empty lists;
 *   noticeSortValue(notices) — `null` for a missing list (a row not analysed, which the table sorts last); otherwise a
 *     finite number that orders by warnings and, at equal warnings, by notes. Pinned by order, never by formula;
 *   noticeCountsCell(notices) — `'—'` for a missing list; otherwise the DataTable custom cell
 *     `{type: 'custom', component: NoticeCounts, props: {warnings, notes}}`, an empty list included (zeros, not a dash).
 *
 * Every list and every notice handed in is frozen: the signatures take `readonly` lists, and a function that wrote into
 * one would throw here.
 *
 * jsdom, although the functions are pure: `noticeCountsCell` hands the table `NoticeCounts.svelte` itself — compared by
 * identity with the component this test loads, compiled as the browser gets it — and the agreement case renders
 * BrimNoticeList. Nothing reads translated text: the notices carry invented codes (`probe_*`) that no catalogue names, so
 * the list shows each one's own message, and the message carries its code as a needle.
 *
 * Written red-first, before `importNotices.ts` and `NoticeCounts.svelte` exist: both are loaded lazily through
 * `import.meta.glob`, each on its own, in a `beforeAll` with its own budget — a missing module fails every case that uses
 * it, on its own and naming it, instead of failing the whole file at collection.
 *
 * Registered in `scripts/test_runner/_frontend_transaction.py`, in the Vitest list of `front_tx_unit` (action
 * `front-transaction tx-unit`).
 *
 * Plan: `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md`,
 * section «B-51».
 */
import {beforeAll, describe, expect, it} from 'vitest';
import type {Component} from 'svelte';
import {render, screen, setupI18n} from '$test/component';
import type {BrimNotice} from '$lib/types';
import BrimNoticeList from './BrimNoticeList.svelte';

// ---------------------------------------------------------------------------
// Loading the pieces under test
// ---------------------------------------------------------------------------

/** A notice as these functions read it: its severity, whatever a plugin wrote there. */
interface SeverityBearer {
    severity?: string | null;
}

interface Counts {
    warnings: number;
    notes: number;
}

/** The DataTable custom cell (`CustomCell`, `$lib/components/table/types`). */
interface CountsCell {
    type: 'custom';
    component: unknown;
    props: Record<string, unknown>;
}

interface ImportNoticesApi {
    noticeSeverity(notice: SeverityBearer): 'info' | 'warning';
    noticeCounts(notices: readonly SeverityBearer[] | null | undefined): Counts;
    splitNotices<N extends SeverityBearer>(notices: readonly N[] | null | undefined): {warnings: N[]; notes: N[]};
    noticeSortValue(notices: readonly SeverityBearer[] | null | undefined): number | null;
    noticeCountsCell(notices: readonly SeverityBearer[] | null | undefined): string | CountsCell;
}

const EXPORTS = ['noticeSeverity', 'noticeCounts', 'splitNotices', 'noticeSortValue', 'noticeCountsCell'] as const;

// Lazy globs rather than literal imports: neither module exists yet, and a missing file must fail each case on its own.
const NOTICES_MODULES = import.meta.glob<Partial<ImportNoticesApi>>('./importNotices.ts');
const COUNTS_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./NoticeCounts.svelte');

async function loadImportNotices(): Promise<ImportNoticesApi> {
    const load = NOTICES_MODULES['./importNotices.ts'];
    if (!load) throw new Error(`importNotices.ts cannot be found next to this test (src/lib/features/transactions/import/): it should export ${EXPORTS.join(', ')}`);
    const mod = await load();
    const missing = EXPORTS.filter((name) => typeof mod[name] !== 'function');
    if (missing.length > 0) throw new Error(`importNotices.ts does not export ${missing.join(', ')} as a function`);
    return mod as ImportNoticesApi;
}

async function loadNoticeCounts(): Promise<Component<Record<string, unknown>>> {
    const load = COUNTS_MODULES['./NoticeCounts.svelte'];
    if (!load) throw new Error('NoticeCounts.svelte cannot be found next to this test (src/lib/features/transactions/import/)');
    return (await load()).default;
}

/** What a loading hook found: the piece, or why it could not be loaded. */
type Loaded<T> = {piece: T} | {error: unknown};

async function attempt<T>(load: () => Promise<T>): Promise<Loaded<T>> {
    try {
        return {piece: await load()};
    } catch (error) {
        return {error};
    }
}

function unwrap<T>(name: string, loaded: Loaded<T> | undefined): T {
    if (loaded === undefined) throw new Error(`${name} was never loaded: its beforeAll did not run`);
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.piece;
}

let noticesModule: Loaded<ImportNoticesApi> | undefined;
let countsComponent: Loaded<Component<Record<string, unknown>>> | undefined;

// Each piece on its own, in a hook with its own budget (a component's first transform is cold): a case fails only on
// the pieces it uses.
beforeAll(async () => {
    noticesModule = await attempt(loadImportNotices);
    countsComponent = await attempt(loadNoticeCounts);
}, 60_000);

beforeAll(async () => {
    // Only the agreement case renders (BrimNoticeList): the store must be up before it mounts.
    await setupI18n();
});

/** The module under test. */
function api(): ImportNoticesApi {
    return unwrap('importNotices.ts', noticesModule);
}

/** The component the cell must name: the default export of NoticeCounts.svelte, as this test loads it. */
function noticeCountsComponent(): Component<Record<string, unknown>> {
    return unwrap('NoticeCounts.svelte', countsComponent);
}

// ---------------------------------------------------------------------------
// Fixtures: invented notices, frozen — codes no catalogue names, each message carrying its code as a needle
// ---------------------------------------------------------------------------

type Kind = 'info' | 'warning';

interface ProbeNotice extends SeverityBearer {
    code: string;
    message: string;
}

/** A notice with exactly the severity field given (absent when `severity` is `{}`), frozen. */
function noticeWith(code: string, severity: {severity?: string | null}): ProbeNotice {
    return Object.freeze({...severity, code, message: `Probe notice [${code}]`});
}

const note = (code: string): ProbeNotice => noticeWith(code, {severity: 'info'});
const warning = (code: string): ProbeNotice => noticeWith(code, {severity: 'warning'});
/** A notice that states no severity at all: the key is absent. */
const unstated = (code: string): ProbeNotice => noticeWith(code, {});

/** A list as the signatures take it, `readonly`: frozen, so that a function writing into it throws. */
function frozen<T>(list: T[]): readonly T[] {
    return Object.freeze(list);
}

/** Every form a plugin's severity can take, and the kind it is: exactly `'info'` is a note, anything else a warning. */
const SEVERITIES: readonly [label: string, kind: Kind, notice: ProbeNotice][] = [
    ["'info'", 'info', noticeWith('probe_severity_info', {severity: 'info'})],
    ["'warning'", 'warning', noticeWith('probe_severity_warning', {severity: 'warning'})],
    ['no severity (the key absent)', 'warning', noticeWith('probe_severity_absent', {})],
    ['an undefined severity', 'warning', noticeWith('probe_severity_undefined', {severity: undefined})],
    ['a null severity', 'warning', noticeWith('probe_severity_null', {severity: null})],
    ["'error', a severity no plugin may send", 'warning', noticeWith('probe_severity_error', {severity: 'error'})],
    ["'INFO', upper case", 'warning', noticeWith('probe_severity_upper', {severity: 'INFO'})],
    ["'Info', capitalised", 'warning', noticeWith('probe_severity_capital', {severity: 'Info'})],
    ["' info', padded", 'warning', noticeWith('probe_severity_padded', {severity: ' info'})],
    ["'', empty", 'warning', noticeWith('probe_severity_empty', {severity: ''})],
];

/** The notices of SEVERITIES, in its order. */
const EVERY_SEVERITY = frozen(SEVERITIES.map(([, , notice]) => notice));

/** One plugin's notices in the order it raised them: a note first, the kinds interleaved — 2 warnings, 3 notes. */
const RAISED = frozen([note('probe_note_a'), warning('probe_warning_b'), note('probe_note_c'), unstated('probe_warning_d'), note('probe_note_e')]);

/** `warnings` warnings and `notes` notes, interleaved, a note first: a value must count them, not read positions. */
function listOf(warnings: number, notes: number): readonly ProbeNotice[] {
    const list: ProbeNotice[] = [];
    for (let i = 0; i < Math.max(warnings, notes); i++) {
        if (i < notes) list.push(note(`probe_note_${i}`));
        if (i < warnings) list.push(warning(`probe_warning_${i}`));
    }
    return frozen(list);
}

/** No list: a row not analysed. */
const MISSING: readonly [label: string, list: null | undefined][] = [
    ['null', null],
    ['undefined', undefined],
];

/** No notice: the missing lists, and the empty list of an analysed row. */
const NOTHING: readonly [label: string, list: readonly ProbeNotice[] | null | undefined][] = [...MISSING, ['an empty list', frozen([])]];

/** «—», the dash the other columns of the results table show for a row not analysed. */
const DASH = '\u2014';

// ---------------------------------------------------------------------------
// Reading
// ---------------------------------------------------------------------------

/** `actual` holds the very objects of `expected`, in that order: identity, not a copy that looks alike. */
function expectSameNotices(actual: readonly ProbeNotice[], expected: readonly ProbeNotice[], what: string): void {
    expect(
        actual.map((notice) => notice.code),
        `${what}: which notices, in which order`,
    ).toEqual(expected.map((notice) => notice.code));
    expected.forEach((notice, index) => expect(actual[index], `${what}[${index}]: the very object given, not a copy`).toBe(notice));
}

/** The sort value of a list that exists: a finite number, or the case fails saying what it got. */
function finiteSortValue(list: readonly ProbeNotice[], what: string): number {
    const value = api().noticeSortValue(list);
    expect(Number.isFinite(value), `${what}: the sort value is a finite number, got ${String(value)}`).toBe(true);
    return value as number;
}

/** The custom cell of NoticeCounts, with these counts as its props. */
function expectCountsCell(cell: unknown, expected: Counts): void {
    expect(cell, `a custom cell, not a plain value: got ${JSON.stringify(cell)}`).toBeTypeOf('object');
    expect(cell).not.toBeNull();
    const custom = cell as CountsCell;
    expect(custom.type).toBe('custom');
    expect(custom.component, 'the component is NoticeCounts.svelte itself').toBe(noticeCountsComponent());
    expect(custom.props).toEqual(expected);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('noticeSeverity — exactly «info» is a note, anything else a warning', () => {
    it.each(SEVERITIES)('%s → %s', (_label, kind, notice) => {
        expect(api().noticeSeverity(notice)).toBe(kind);
    });

    it('agrees with BrimNoticeList, case by case: each notice is the kind the list draws it as', () => {
        const {noticeSeverity} = api();
        render(BrimNoticeList, {notices: EVERY_SEVERITY as unknown as BrimNotice[]});

        const items = screen.getAllByTestId('brim-notice');
        expect(items, 'presence barrier: one item per notice').toHaveLength(SEVERITIES.length);
        for (const [label, kind, notice] of SEVERITIES) {
            const shown = items.filter((item) => item.textContent?.includes(`[${notice.code}]`));
            expect(shown, `${label}: exactly one item shows its message`).toHaveLength(1);
            expect(shown[0], `${label}: the list draws it as ${kind}`).toHaveAttribute('data-severity', kind);
            expect(noticeSeverity(notice), `${label}: noticeSeverity says what the list draws`).toBe(shown[0].dataset.severity);
        }
    });
});

describe('noticeCounts — the warnings and the notes, by the rule of noticeSeverity', () => {
    it.each(NOTHING)('%s: no warning and no note', (_label, list) => {
        expect(api().noticeCounts(list)).toEqual({warnings: 0, notes: 0});
    });

    it("a plugin's mixed list: 2 warnings — one stated, one not — and 3 notes", () => {
        expect(api().noticeCounts(RAISED)).toEqual({warnings: 2, notes: 3});
    });

    it('every form of severity: the one «info» is a note, the nine others are warnings', () => {
        const expected = {warnings: SEVERITIES.filter(([, kind]) => kind === 'warning').length, notes: SEVERITIES.filter(([, kind]) => kind === 'info').length};
        expect(expected, 'control: the table holds both kinds').toEqual({warnings: 9, notes: 1});

        expect(api().noticeCounts(EVERY_SEVERITY)).toEqual(expected);
    });

    it('notes alone count no warning — one note, the Fineco case, is 0 warnings and 1 note', () => {
        expect(api().noticeCounts(frozen([note('probe_note_fineco')]))).toEqual({warnings: 0, notes: 1});
        expect(api().noticeCounts(listOf(0, 4))).toEqual({warnings: 0, notes: 4});
    });

    it('warnings alone count no note', () => {
        expect(api().noticeCounts(listOf(3, 0))).toEqual({warnings: 3, notes: 0});
    });
});

describe('splitNotices — the very notices, each kind in the order raised', () => {
    it('a mixed list: the warnings and the notes, the same objects, each list in its original relative order', () => {
        const {warnings, notes} = api().splitNotices(RAISED);

        expectSameNotices(warnings, [RAISED[1], RAISED[3]], 'the warnings');
        expectSameNotices(notes, [RAISED[0], RAISED[2], RAISED[4]], 'the notes');
    });

    it('every form of severity: each notice in exactly one list, the one its kind names', () => {
        const {warnings, notes} = api().splitNotices(EVERY_SEVERITY);

        expectSameNotices(
            warnings,
            SEVERITIES.filter(([, kind]) => kind === 'warning').map(([, , notice]) => notice),
            'the warnings',
        );
        expectSameNotices(
            notes,
            SEVERITIES.filter(([, kind]) => kind === 'info').map(([, , notice]) => notice),
            'the notes',
        );
    });

    it.each(NOTHING)('%s: two empty lists', (_label, list) => {
        expect(api().splitNotices(list)).toEqual({warnings: [], notes: []});
    });
});

describe('noticeSortValue — by warnings, then by notes; a missing list has no value', () => {
    /** The ladder of the plan, in the order the column must sort it. */
    const LADDER: readonly [warnings: number, notes: number][] = [
        [0, 0],
        [0, 3],
        [1, 0],
        [1, 5],
        [2, 0],
    ];
    const label = ([warnings, notes]: readonly [number, number]) => `(${warnings} warnings, ${notes} notes)`;

    it.each(MISSING)('%s (a row not analysed): null, which the table sorts last', (_label, list) => {
        expect(api().noticeSortValue(list)).toBeNull();
    });

    it('an empty list — an analysed row with nothing to say — is a number, not null', () => {
        finiteSortValue(frozen([]), 'an empty list');
    });

    it('sorts (0, 0) < (0, 3) < (1, 0) < (1, 5) < (2, 0), whatever order the rows come in', () => {
        // The rows in a shuffled order, so that a sort which changes nothing cannot pass.
        const rows = [3, 0, 4, 2, 1].map((index) => ({label: label(LADDER[index]), value: finiteSortValue(listOf(...LADDER[index]), label(LADDER[index]))}));

        const sorted = [...rows].sort((a, b) => a.value - b.value);
        expect(
            sorted.map((row) => row.label),
            `the values: ${JSON.stringify(rows)}`,
        ).toEqual(LADDER.map(label));
        // …and no two of them tie: a tie would leave their order to the stability of the sort.
        sorted.slice(1).forEach((row, index) => expect(row.value, `${row.label} sorts after ${sorted[index].label}`).toBeGreaterThan(sorted[index].value));
    });

    it('one warning outweighs many notes: (1, 0) sorts after (0, 99)', () => {
        expect(finiteSortValue(listOf(1, 0), '(1, 0)')).toBeGreaterThan(finiteSortValue(listOf(0, 99), '(0, 99)'));
    });

    it('equal counts sort together: the same value, whatever the order, the codes and the form of the severities', () => {
        const stated = frozen([note('probe_note_x'), warning('probe_warning_y'), note('probe_note_z')]);
        const otherwise = frozen([unstated('probe_warning_q'), note('probe_note_r'), note('probe_note_s')]);

        expect(finiteSortValue(otherwise, 'an unstated warning first, then 2 notes')).toBe(finiteSortValue(stated, 'a note, a warning, a note'));
    });
});

describe('noticeCountsCell — the results column: NoticeCounts for an analysed row, the dash for the others', () => {
    it.each(MISSING)('%s (a row not analysed): the dash «—», as in the other columns', (_label, list) => {
        expect(api().noticeCountsCell(list)).toBe(DASH);
    });

    it('an empty list: the NoticeCounts cell at 0 and 0 — an analysed row, not the dash', () => {
        expectCountsCell(api().noticeCountsCell(frozen([])), {warnings: 0, notes: 0});
    });

    it('a mixed list: the NoticeCounts cell with its two counts', () => {
        expectCountsCell(api().noticeCountsCell(RAISED), {warnings: 2, notes: 3});
    });

    it('one note alone — the Fineco case — is 0 warnings and 1 note, never one number', () => {
        expectCountsCell(api().noticeCountsCell(frozen([note('probe_note_fineco')])), {warnings: 0, notes: 1});
    });
});
