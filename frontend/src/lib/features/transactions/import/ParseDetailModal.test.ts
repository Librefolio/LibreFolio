// @vitest-environment jsdom
/**
 * ParseDetailModal — the «Manual fields» section (F1, D2 of the Danske Bank workstream, issue 26).
 * Component test (Vitest + jsdom).
 *
 * The analysis detail lists the plugin's field todos. Until F1 a todo was one line ending in
 * `JSON.stringify(todo.context)`: the developer read a raw object where the trade-charges warning
 * of Danske Bank should have told him the total, the charges and what to check. The section is
 * generic — every plugin's todos go through it — and the contract pinned here is the plan's (F.0):
 *
 *   parse-detail-todo (data-reason-code, data-severity) — one per todo, showing:
 *     · the row (importWizard.todoRow, tx_index + 1) and the field (translateFieldName);
 *     · the message: `importWizard.brimNotice.<reason_code>` when that i18n key exists, else the
 *       plugin's `message` — the rule of `todoMessage` in FixFlaggedStep.svelte;
 *     · the context keys the frontend understands, as facts: the total (`cash`) and the charges
 *       (`charges`), each with its `currency`, and `split_suggestions` as a list;
 *     · every `todo.evidence` through BrimEvidenceTable (`brim-evidence`);
 *     · any other context key only inside parse-detail-todo-technical: a <details> block, closed.
 *   No inline JSON anywhere else.
 *
 * Nothing here reads translated text: the assertions are on testids, data attributes, the element
 * kinds of the contract (<details>, list items) and on values the test passed in — amounts, the
 * plugin's messages, the suggestions, the evidence cells, and one i18n entry the test registers
 * itself (`importWizard.brimNotice.probe_localized_blocker`), so that "the key exists" does not
 * depend on the catalogue of the day.
 *
 * The component is loaded once, in a `beforeAll` with its own timeout (the first transform is cold
 * and takes seconds); a load failure is recorded and every test then fails on its own, saying so.
 *
 * Phase F2 (U3) adds, at the end of the file, the pairing section of a report set's detail: the
 * outcome chips, the reasons table and the preview / download of the combined file.
 *
 * Lot B-51 adds, last, the notices section: the plugin's warnings and notes apart, each kind in a
 * subsection of its own (plan 04, `plan-phase01ImportTransactions.prompt.md`, section «B-51»).
 *
 * Plan: `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md`, F.0 (F1 · D2).
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import type {Component} from 'svelte';

// Every API method is inert: the modal receives its data as props. The currency catalogue answers
// for the two currencies of the fixtures (a money fact may be rendered through it); the plugin list
// is empty (BrokerIcon asks for the plugin icons).
vi.mock('$lib/api', async () => {
    const generated = await vi.importActual<{schemas: unknown}>('$lib/api/generated');
    const answers: Record<string, unknown> = {
        list_currencies_api_v1_utilities_currencies_get: {
            items: [
                {code: 'CHF', name: 'Swiss franc', symbol: 'CHF', flag_emoji: '🇨🇭', country_codes: [], country_names: []},
                {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
            ],
        },
        list_plugins_api_v1_brokers_import_plugins_get: [],
    };
    const inert = (byName: Record<string, unknown>) =>
        new Proxy(
            {},
            {
                get(_target, property) {
                    if (typeof property !== 'string' || property === 'then') return undefined;
                    return vi.fn(async () => byName[property]);
                },
            },
        );
    class ApiError extends Error {}
    return {zodiosApi: inert(answers), axiosInstance: inert({}), ApiError, schemas: generated.schemas};
});

import {fireEvent, render, screen, setupI18n} from '$test/component';
import {addMessages} from 'svelte-i18n';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

// A lazy glob rather than a literal import: the first transform of the modal is cold, and here it
// runs in a hook with its own budget instead of inside the first test's.
const MODAL_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./ParseDetailModal.svelte');

let loaded: {ParseDetailModal: Component<Record<string, unknown>>} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = MODAL_MODULES['./ParseDetailModal.svelte'];
        if (!load) throw new Error('ParseDetailModal.svelte cannot be found next to this test');
        loaded = {ParseDetailModal: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

function modal(): Component<Record<string, unknown>> {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.ParseDetailModal;
}

// ---------------------------------------------------------------------------
// Fixtures: invented todos, shaped like BRIMFieldTodo in a parse response
// ---------------------------------------------------------------------------

/** The i18n entry this test registers: "the key exists" for the blocker's reason code. */
const LOCALIZED_REASON = 'probe_localized_blocker';
const LOCALIZED_WORDING = 'Probe localized wording for the blocker';

const CASH = '312.45';
const CHARGES = '7.89';
const CURRENCY = 'CHF';
const SUGGESTIONS = ['Probe suggestion one: compare quantity and price', 'Probe suggestion two: the contract note has the exact figures'];

/** A trade-charges warning, as Danske Bank raises it on every trade: the frontend's context keys and an evidence table. */
const TODO_CHARGES = {
    tx_index: 776,
    field: 'cash',
    severity: 'warning',
    reason_code: 'probe_trade_charges',
    message: 'Probe plugin message: the total includes the charges',
    context: {
        row: 31,
        cash: CASH,
        currency: CURRENCY,
        charges: CHARGES,
        compare_nominal: false,
        split_hint: 'trade_charges',
        split_suggestions: SUGGESTIONS,
    },
    evidence: [
        {
            title: 'Probe evidence title',
            headers: ['Probe column A', 'Probe column B'],
            rows: [['probe-cell-a1', 'probe-cell-b1']],
            row_numbers: [31],
            comment: 'Probe evidence comment',
        },
    ],
} as const;

/** A blocker with no context and no evidence, whose reason code has an i18n entry (registered below). */
const TODO_BLOCKER = {
    tx_index: 887,
    field: 'cost_basis_override',
    severity: 'blocker',
    reason_code: LOCALIZED_REASON,
    message: 'Probe plugin message: enter the cost of the new line',
} as const;

/** A warning whose only context key is unknown to the frontend. */
const UNKNOWN_KEY = 'probe_unknown_key';
const UNKNOWN_VALUE = 'probe-unknown-value-c';
const TODO_UNKNOWN = {
    tx_index: 998,
    field: 'quantity',
    severity: 'warning',
    reason_code: 'probe_unknown_context',
    message: 'Probe plugin message: check this quantity',
    context: {[UNKNOWN_KEY]: UNKNOWN_VALUE},
} as const;

function parsedFile(fileId: string, fileName: string, fieldTodos: readonly unknown[]) {
    return {
        fileId,
        fileName,
        brokerId: 7,
        brokerName: 'Probe broker',
        brokerIconUrl: null,
        brokerPortalUrl: null,
        pluginUsed: 'broker_probe',
        pluginName: 'Probe plugin',
        status: 'done',
        response: {
            file_id: fileId,
            plugin_code: 'broker_probe',
            broker_id: 7,
            transactions: [],
            asset_mappings: [],
            duplicates: null,
            warnings: [],
            validation_issues: [],
            field_todos: fieldTodos,
        },
        set: null,
    };
}

// ---------------------------------------------------------------------------
// Mounting and reading
// ---------------------------------------------------------------------------

async function mountSingle(fieldTodos: readonly unknown[] = [TODO_CHARGES, TODO_BLOCKER, TODO_UNKNOWN]) {
    const ParseDetailModal = modal();
    render(ParseDetailModal, {open: true, parseResult: parsedFile('probe-file-1', 'probe-report.csv', fieldTodos), onClose: vi.fn()});
    // Barrier: the modal is mounted before anything is read.
    return screen.findByTestId('parse-detail-modal');
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

const TECHNICAL = '[data-testid="parse-detail-todo-technical"]';

/** What the user reads without opening anything: the element's text, its technical-details blocks left out. */
function textOutsideTechnical(el: Element): string {
    const clone = el.cloneNode(true) as Element;
    for (const technical of clone.querySelectorAll(TECHNICAL)) technical.remove();
    return text(clone);
}

/** The elements of `scope` that do not sit inside a technical-details block. */
function elementsOutsideTechnical(scope: Element): Element[] {
    const technical = [...scope.querySelectorAll(TECHNICAL)];
    return [...scope.querySelectorAll('*')].filter((el) => !technical.some((block) => block.contains(el)));
}

/** The todo element of a fixture, by its reason code and severity. */
function todoOf(fixture: {reason_code: string; severity: string}, scope: ParentNode = document): HTMLElement {
    return the('parse-detail-todo', {'reason-code': fixture.reason_code, severity: fixture.severity}, scope);
}

beforeAll(async () => {
    await setupI18n();
    // "When that i18n key exists": the test owns the entry, the catalogue of the day does not matter.
    addMessages('en', {importWizard: {brimNotice: {[LOCALIZED_REASON]: LOCALIZED_WORDING}}});
    await ensureCurrenciesLoaded('en');
    setPrivacyEnabled(false);
});

afterEach(() => {
    // Module-level state: a leftover `true` would mount the next modal masked.
    setPrivacyEnabled(false);
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ParseDetailModal — one parse-detail-todo per field todo', () => {
    it('each todo is a parse-detail-todo carrying its reason code and severity', async () => {
        await mountSingle();

        expect(all('parse-detail-todo')).toHaveLength(3);
        todoOf(TODO_CHARGES);
        todoOf(TODO_BLOCKER);
        todoOf(TODO_UNKNOWN);
    });

    it('a todo shows its row: tx_index + 1', async () => {
        await mountSingle();

        expect(text(todoOf(TODO_CHARGES))).toContain(String(TODO_CHARGES.tx_index + 1));
        expect(text(todoOf(TODO_BLOCKER))).toContain(String(TODO_BLOCKER.tx_index + 1));
        expect(text(todoOf(TODO_UNKNOWN))).toContain(String(TODO_UNKNOWN.tx_index + 1));
    });

    it("the message is importWizard.brimNotice.<reason_code> when the key exists, the plugin's message otherwise", async () => {
        await mountSingle();

        const blocker = todoOf(TODO_BLOCKER);
        expect(text(blocker), 'the i18n entry of the reason code is shown').toContain(LOCALIZED_WORDING);
        expect(text(blocker), "the plugin's message gives way to the i18n entry").not.toContain(TODO_BLOCKER.message);

        expect(text(todoOf(TODO_CHARGES)), 'no i18n entry: the plugin message').toContain(TODO_CHARGES.message);
        expect(text(todoOf(TODO_UNKNOWN)), 'no i18n entry: the plugin message').toContain(TODO_UNKNOWN.message);
        expect(text(screen.getByTestId('parse-detail-modal')), 'never a raw i18n key').not.toContain('importWizard.brimNotice');
    });
});

describe('ParseDetailModal — the context the frontend understands, as facts', () => {
    it('the total and the charges are two facts, each with its currency, outside the technical details', async () => {
        await mountSingle();

        const todo = todoOf(TODO_CHARGES);
        const outside = elementsOutsideTechnical(todo);
        const cashFact = outside.find((el) => text(el).includes(CASH) && text(el).includes(CURRENCY) && !text(el).includes(CHARGES));
        const chargesFact = outside.find((el) => text(el).includes(CHARGES) && text(el).includes(CURRENCY) && !text(el).includes(CASH));

        expect(cashFact, `an element shows the total ${CASH} with ${CURRENCY}, apart from the charges; the todo reads: ${textOutsideTechnical(todo)}`).toBeDefined();
        expect(chargesFact, `an element shows the charges ${CHARGES} with ${CURRENCY}, apart from the total; the todo reads: ${textOutsideTechnical(todo)}`).toBeDefined();
    });

    it('split_suggestions are a list: one list item per suggestion, outside the technical details', async () => {
        await mountSingle();

        const items = elementsOutsideTechnical(todoOf(TODO_CHARGES))
            .filter((el) => el.tagName === 'LI')
            .map(text);
        for (const suggestion of SUGGESTIONS) {
            expect(
                items.filter((item) => item.includes(suggestion)),
                `exactly one list item holds "${suggestion}"; the list items: ${JSON.stringify(items)}`,
            ).toHaveLength(1);
        }
    });

    it('the evidence goes through BrimEvidenceTable, outside the technical details, and opens on its rows', async () => {
        await mountSingle();

        const todo = todoOf(TODO_CHARGES);
        const evidence = the('brim-evidence', {}, todo);
        expect(
            all('parse-detail-todo-technical', todo).some((technical) => technical.contains(evidence)),
            'the evidence is not hidden in the technical details',
        ).toBe(false);
        expect(text(evidence)).toContain(TODO_CHARGES.evidence[0].title);

        // Closable or not is the modal's call: open it only if its rows are not on screen yet.
        if (!text(evidence).includes('probe-cell-a1')) await fireEvent.click(the('brim-evidence-toggle', {}, evidence));
        expect(text(evidence)).toContain('probe-cell-a1');
        expect(text(evidence)).toContain('probe-cell-b1');
        expect(text(evidence)).toContain(TODO_CHARGES.evidence[0].comment);
    });

    it('a todo with no context and no evidence has neither technical details nor an evidence table', async () => {
        await mountSingle();

        const blocker = todoOf(TODO_BLOCKER);
        expect(all('parse-detail-todo-technical', blocker)).toHaveLength(0);
        expect(all('brim-evidence', blocker)).toHaveLength(0);
    });
});

describe('ParseDetailModal — any other context key lives in the closed technical details, never as inline JSON', () => {
    it('an unknown key is inside parse-detail-todo-technical: a <details> block, closed, with the key and its value', async () => {
        await mountSingle();

        const todo = todoOf(TODO_UNKNOWN);
        const technical = the('parse-detail-todo-technical', {}, todo);
        expect(technical.tagName, 'the technical details are a <details> block').toBe('DETAILS');
        expect((technical as HTMLDetailsElement).open, 'closed until the user opens it').toBe(false);
        expect(text(technical)).toContain(UNKNOWN_KEY);
        expect(text(technical)).toContain(UNKNOWN_VALUE);

        // Closed means not visible: the value is there for whoever opens the block, and only then.
        // The innermost element holding it — the block itself when the value is one of its own text nodes.
        const holder = [...technical.querySelectorAll('*')].reverse().find((el) => text(el).includes(UNKNOWN_VALUE)) ?? technical;
        expect(holder, 'the value is not readable while the block is closed').not.toBeVisible();
        (technical as HTMLDetailsElement).open = true;
        expect(holder, 'the value is readable once the block is open').toBeVisible();
    });

    it('outside the technical details the unknown key and its value appear nowhere', async () => {
        const root = await mountSingle();

        expect(textOutsideTechnical(todoOf(TODO_UNKNOWN))).not.toContain(UNKNOWN_KEY);
        expect(textOutsideTechnical(todoOf(TODO_UNKNOWN))).not.toContain(UNKNOWN_VALUE);
        expect(textOutsideTechnical(root)).not.toContain(UNKNOWN_VALUE);
    });

    it('no todo prints its context as JSON outside the technical details', async () => {
        await mountSingle();

        for (const fixture of [TODO_CHARGES, TODO_UNKNOWN]) {
            const outside = textOutsideTechnical(todoOf(fixture));
            expect(outside, `${fixture.reason_code}: no JSON of its context`).not.toContain(JSON.stringify(fixture.context));
            expect(outside, `${fixture.reason_code}: no JSON object in the line`).not.toMatch(/\{\s*"/);
        }
    });
});

describe('ParseDetailModal — the summary of several files lists the same todos', () => {
    it('in the aggregate view every todo of every file is a parse-detail-todo, the unknown key in its closed technical details', async () => {
        const ParseDetailModal = modal();
        render(ParseDetailModal, {
            open: true,
            parseResult: null,
            allResults: [parsedFile('probe-file-1', 'probe-report-1.csv', [TODO_CHARGES, TODO_UNKNOWN]), parsedFile('probe-file-2', 'probe-report-2.csv', [TODO_BLOCKER])],
            onClose: vi.fn(),
        });
        await screen.findByTestId('parse-detail-modal');

        expect(all('parse-detail-todo')).toHaveLength(3);
        todoOf(TODO_CHARGES);
        todoOf(TODO_BLOCKER);
        const unknown = todoOf(TODO_UNKNOWN);
        const technical = the('parse-detail-todo-technical', {}, unknown);
        expect(technical.tagName).toBe('DETAILS');
        expect((technical as HTMLDetailsElement).open).toBe(false);
        expect(textOutsideTechnical(unknown)).not.toContain(UNKNOWN_VALUE);
    });
});

// ===========================================================================
// F2 · U3 — the pairing of a report set: outcome chips, reasons table, preview and download
// ===========================================================================
//
// Pinned in the plan (F2.0, U3), section `parse-detail-pairing` (its data attributes stay):
//   parse-detail-pairing-outcome (data-outcome, data-count) — all five outcomes, in the order
//     pair · standalone · summarized · deferred · excluded, the zero ones included;
//   parse-detail-pairing-reasons — a table, one row parse-detail-pairing-reason (data-reason,
//     data-count) per reason; no table without reasons;
//   parse-detail-preview-combined — a button, only when `onPreview` is given, calling it once;
//   parse-detail-download-combined — the link stays: /api/v1/brokers/import/files/<id>/download.
// The reason codes are invented: their label falls back to the code, which is never asserted on.

const SET_OUTCOMES = ['pair', 'standalone', 'summarized', 'deferred', 'excluded'] as const;
/** A combined file id that needs encoding in a URL: the download link must encode it. */
const SET_FILE_ID = 'probe combined/1';
/** `excluded` is absent from the summary: its chip still shows, at 0. */
const SET_SUMMARY = {outcomes: {pair: 12, standalone: 15, summarized: 7, deferred: 1}, reasons: {probe_reason_alpha: 3, probe_reason_beta: 5}};

function parsedSet(summary: Record<string, unknown> | null) {
    return {...parsedFile(SET_FILE_ID, 'Probe Bank — combined 2020-02-03…2020-06-26.csv', []), set: {memberNames: ['probe-custody.xlsx', 'probe-cash.csv'], summary, reused: false}};
}

/** Mount the detail of a set's analysis row; returns its pairing section. */
async function mountSet(summary: Record<string, unknown> | null = SET_SUMMARY, extra: Record<string, unknown> = {}): Promise<HTMLElement> {
    render(modal(), {open: true, parseResult: parsedSet(summary), onClose: vi.fn(), ...extra});
    await screen.findByTestId('parse-detail-modal');
    return the('parse-detail-pairing');
}

describe('ParseDetailModal — F2 · U3: the pairing of a report set', () => {
    it('keeps the counts of the combine on the section (guard: true before F2 too)', async () => {
        const pairing = await mountSet();

        expect(pairing).toHaveAttribute('data-pair', '12');
        expect(pairing).toHaveAttribute('data-standalone', '15');
        expect(pairing).toHaveAttribute('data-summarized', '7');
        expect(pairing).toHaveAttribute('data-deferred', '1');
        expect(pairing).toHaveAttribute('data-excluded', '0');
    });

    it('every outcome is a chip, all five in reading order, the zero ones included, each with its count', async () => {
        const pairing = await mountSet();

        const chips = all('parse-detail-pairing-outcome', pairing).map((chip) => [chip.dataset.outcome, chip.dataset.count]);
        expect(chips).toEqual([
            ['pair', '12'],
            ['standalone', '15'],
            ['summarized', '7'],
            ['deferred', '1'],
            ['excluded', '0'],
        ]);
        expect(chips.map(([outcome]) => outcome)).toEqual([...SET_OUTCOMES]);
    });

    it('the reasons are a table: one row per reason, with its count', async () => {
        const pairing = await mountSet();

        const table = the('parse-detail-pairing-reasons', {}, pairing);
        const rows = all('parse-detail-pairing-reason', table);
        expect(rows.map((row) => [row.dataset.reason, row.dataset.count])).toEqual(
            expect.arrayContaining([
                ['probe_reason_alpha', '3'],
                ['probe_reason_beta', '5'],
            ]),
        );
        expect(rows).toHaveLength(2);
        for (const row of rows) {
            expect(row.tagName, `${row.dataset.reason}: a row of the table`).toBe('TR');
            expect(text(row), `${row.dataset.reason}: the count is shown, not only stored`).toContain(row.dataset.count ?? '∅');
        }
        // Nowhere else: no reason line outside the table.
        expect(all('parse-detail-pairing-reason', pairing)).toHaveLength(2);
    });

    it('no reasons, no table — the chips are there all the same', async () => {
        const pairing = await mountSet({outcomes: {pair: 2, standalone: 1}});

        expect(all('parse-detail-pairing-outcome', pairing).map((chip) => chip.dataset.count)).toEqual(['2', '1', '0', '0', '0']);
        expect(all('parse-detail-pairing-reasons')).toHaveLength(0);
        expect(all('parse-detail-pairing-reason')).toHaveLength(0);
    });

    it('the preview of the combined file is a button that asks for it once', async () => {
        const onPreview = vi.fn();
        const pairing = await mountSet(SET_SUMMARY, {onPreview});

        const preview = the('parse-detail-preview-combined', {}, pairing);
        expect(preview.tagName).toBe('BUTTON');
        await fireEvent.click(preview);

        expect(onPreview).toHaveBeenCalledTimes(1);
    });

    it('without onPreview there is no preview button; the download link is there all the same', async () => {
        const pairing = await mountSet();

        the('parse-detail-download-combined', {}, pairing);
        expect(all('parse-detail-preview-combined')).toHaveLength(0);
    });

    it('the download link stays: the encoded download URL of the combined file (guard: true before F2 too)', async () => {
        const pairing = await mountSet(SET_SUMMARY, {onPreview: vi.fn()});

        const download = the('parse-detail-download-combined', {}, pairing);
        expect(download).toHaveAttribute('href', `/api/v1/brokers/import/files/${encodeURIComponent(SET_FILE_ID)}/download`);
    });
});

// ===========================================================================
// B-51 — the notices of a parse: the warnings and the notes apart
// ===========================================================================
//
// Pinned in plan 04 (section «B-51»). A BRIM plugin's notices (`response.warnings`) are of two kinds: `info` is a blue
// note — the plugin explains a choice it made on purpose — and any other severity, none included, an amber warning (the
// rule of BrimNoticeList; `noticeSeverity` in importNotices.ts). The modal had one «Warnings» section listing them all,
// so a note read as a warning. Now:
//   parse-detail-notices (data-warnings, data-notes) — the section, with the two counts;
//   parse-detail-notice-section (data-severity warning | info, data-count) — one per kind present, the warnings first,
//     never an empty one; inside, that kind's notices as BrimNoticeList items (`brim-notice`, the same data-severity),
//     in the order raised, and no other;
//   parse-detail-notices-empty — no notice at all: this and no subsection. Read here as living inside the section,
//     which then counts 0 and 0 (as every other section of the modal keeps its title over its «none» line);
//   the summary of several files splits the notices of all of them the same way, and sums the counts.
// The codes are invented (`probe_*`): no catalogue names them, so each item shows the plugin's own message, which is
// how a test finds it.

/** Notes (`info`): the plugin explains a choice it made on purpose. */
const NOTE_TRANSFERS = {severity: 'info', code: 'probe_note_transfers', message: 'Probe note: the transfers are booked as adjustments, on purpose', evidence: [], context: null} as const;
const NOTE_RATE = {severity: 'info', code: 'probe_note_rate', message: 'Probe note: the exchange rate is the one the bank applied', evidence: [], context: null} as const;
const NOTE_BETA = {severity: 'info', code: 'probe_note_beta', message: 'Probe note: this reading is in beta, compare the totals', evidence: [], context: null} as const;
/** Warnings: something needs the user's attention. */
const WARNING_CASH = {severity: 'warning', code: 'probe_warning_cash', message: 'Probe warning: the cash of two rows does not add up', evidence: [], context: null} as const;
const WARNING_LEFT_OUT = {severity: 'warning', code: 'probe_warning_left_out', message: 'Probe warning: three rows were left out', evidence: [], context: null} as const;
/** A notice that states no severity at all: a warning, by the rule of BrimNoticeList. */
const WARNING_UNSTATED = {code: 'probe_warning_unstated', message: 'Probe warning: a notice that states no severity', evidence: [], context: null} as const;

/** One plugin's notices in the order it raised them: a note first, the kinds interleaved — 2 warnings, 3 notes. */
const NOTICES_RAISED = [NOTE_TRANSFERS, WARNING_CASH, NOTE_RATE, WARNING_LEFT_OUT, NOTE_BETA] as const;

/** A parsed file whose plugin raised these notices (`response.warnings`), and no field todo. */
function parsedFileWithNotices(fileId: string, fileName: string, notices: readonly unknown[]) {
    const file = parsedFile(fileId, fileName, []);
    return {...file, response: {...file.response, warnings: notices}};
}

/** Mount the detail of one file with these notices; returns the modal once it is there. */
async function mountNotices(notices: readonly unknown[]): Promise<HTMLElement> {
    render(modal(), {open: true, parseResult: parsedFileWithNotices('probe-file-notices', 'probe-notices.csv', notices), onClose: vi.fn()});
    return screen.findByTestId('parse-detail-modal');
}

/** The messages of the `brim-notice` items in `scope`, in the order drawn. */
function noticeMessages(scope: ParentNode): string[] {
    return all('brim-notice', scope).map((item) => text(the('brim-notice-message', {}, item)));
}

/** The notice subsections in the order drawn, as `[data-severity, data-count]`. */
function noticeSections(scope: ParentNode = document): [string | undefined, string | undefined][] {
    return all('parse-detail-notice-section', scope).map((section) => [section.dataset.severity, section.dataset.count]);
}

describe('ParseDetailModal — B-51: the warnings and the notes apart', () => {
    it('every notice is one brim-notice item of its kind, showing its own message (guard: true before B-51 too)', async () => {
        const root = await mountNotices(NOTICES_RAISED);

        const items = all('brim-notice', root);
        expect(items, 'one item per notice').toHaveLength(NOTICES_RAISED.length);
        for (const notice of NOTICES_RAISED) {
            const showing = items.filter((item) => text(item).includes(notice.message));
            expect(showing, `${notice.code}: exactly one item shows its message`).toHaveLength(1);
            expect(showing[0], `${notice.code}: drawn as its kind`).toHaveAttribute('data-severity', notice.severity);
        }
    });

    it('the section carries the two counts: 2 warnings, 3 notes', async () => {
        await mountNotices(NOTICES_RAISED);

        const section = the('parse-detail-notices');
        expect(section).toHaveAttribute('data-warnings', '2');
        expect(section).toHaveAttribute('data-notes', '3');
    });

    it('one subsection per kind present, the warnings first although a note was raised first, each with its count', async () => {
        await mountNotices(NOTICES_RAISED);

        expect(noticeSections(the('parse-detail-notices'))).toEqual([
            ['warning', '2'],
            ['info', '3'],
        ]);
    });

    it("each subsection lists its own kind's notices, as items of that kind, in the order raised — and every item sits in one", async () => {
        await mountNotices(NOTICES_RAISED);

        const warnings = the('parse-detail-notice-section', {severity: 'warning'});
        const notes = the('parse-detail-notice-section', {severity: 'info'});
        expect(noticeMessages(warnings), 'the warnings subsection').toEqual([WARNING_CASH.message, WARNING_LEFT_OUT.message]);
        expect(noticeMessages(notes), 'the notes subsection').toEqual([NOTE_TRANSFERS.message, NOTE_RATE.message, NOTE_BETA.message]);
        for (const item of all('brim-notice', warnings)) expect(item, 'an item of the warnings subsection').toHaveAttribute('data-severity', 'warning');
        for (const item of all('brim-notice', notes)) expect(item, 'an item of the notes subsection').toHaveAttribute('data-severity', 'info');
        // No notice outside the subsections: the single list of all notices is gone.
        for (const item of all('brim-notice')) {
            expect(
                [warnings, notes].filter((section) => section.contains(item)),
                `"${text(item)}" sits in exactly one subsection`,
            ).toHaveLength(1);
        }
    });

    it('a note is never under the warnings: one note alone counts 0 warnings and 1 note, in a notes subsection', async () => {
        await mountNotices([NOTE_RATE]);

        const section = the('parse-detail-notices');
        expect(section).toHaveAttribute('data-warnings', '0');
        expect(section).toHaveAttribute('data-notes', '1');
        expect(noticeSections(section)).toEqual([['info', '1']]);
        expect(noticeMessages(the('parse-detail-notice-section', {severity: 'info'}))).toEqual([NOTE_RATE.message]);
    });

    it('notes alone: one subsection, the notes — no empty warnings subsection', async () => {
        await mountNotices([NOTE_TRANSFERS, NOTE_RATE, NOTE_BETA]);

        expect(noticeSections()).toEqual([['info', '3']]);
        expect(all('parse-detail-notice-section').filter((section) => section.dataset.severity === 'warning')).toHaveLength(0);
    });

    it('warnings alone: one subsection, the warnings — no empty notes subsection', async () => {
        await mountNotices([WARNING_CASH, WARNING_LEFT_OUT]);

        const section = the('parse-detail-notices');
        expect(section).toHaveAttribute('data-warnings', '2');
        expect(section).toHaveAttribute('data-notes', '0');
        expect(noticeSections(section)).toEqual([['warning', '2']]);
        expect(all('parse-detail-notice-section').filter((subsection) => subsection.dataset.severity === 'info')).toHaveLength(0);
    });

    it('a notice that states no severity is a warning here too, as BrimNoticeList draws it', async () => {
        await mountNotices([WARNING_UNSTATED, NOTE_RATE]);

        const section = the('parse-detail-notices');
        expect(section).toHaveAttribute('data-warnings', '1');
        expect(section).toHaveAttribute('data-notes', '1');
        expect(noticeSections(section)).toEqual([
            ['warning', '1'],
            ['info', '1'],
        ]);
        expect(noticeMessages(the('parse-detail-notice-section', {severity: 'warning'}))).toEqual([WARNING_UNSTATED.message]);
    });

    it('no notice at all: the empty marker, and no subsection, no item', async () => {
        await mountNotices([]);

        the('parse-detail-notices-empty');
        expect(all('parse-detail-notice-section')).toHaveLength(0);
        expect(all('brim-notice')).toHaveLength(0);
    });

    it('no notice at all: the section is still there, counting 0 and 0, the empty marker inside it', async () => {
        await mountNotices([]);

        const section = the('parse-detail-notices');
        expect(section).toHaveAttribute('data-warnings', '0');
        expect(section).toHaveAttribute('data-notes', '0');
        expect(section.contains(the('parse-detail-notices-empty')), 'the empty marker is inside the section').toBe(true);
    });

    describe('the summary of several files', () => {
        /** Two files: a note and a warning in the first, a warning and two notes in the second. */
        async function mountAggregate(): Promise<HTMLElement> {
            render(modal(), {
                open: true,
                parseResult: null,
                allResults: [parsedFileWithNotices('probe-file-1', 'probe-notices-1.csv', [NOTE_TRANSFERS, WARNING_CASH]), parsedFileWithNotices('probe-file-2', 'probe-notices-2.csv', [WARNING_LEFT_OUT, NOTE_RATE, NOTE_BETA])],
                onClose: vi.fn(),
            });
            return screen.findByTestId('parse-detail-modal');
        }

        it('lists every notice of every file, one item each, of its kind (guard: true before B-51 too)', async () => {
            const root = await mountAggregate();

            const items = all('brim-notice', root);
            expect(items, 'one item per notice, both files').toHaveLength(NOTICES_RAISED.length);
            for (const notice of NOTICES_RAISED) {
                const showing = items.filter((item) => text(item).includes(notice.message));
                expect(showing, `${notice.code}: exactly one item shows its message`).toHaveLength(1);
                expect(showing[0], `${notice.code}: drawn as its kind`).toHaveAttribute('data-severity', notice.severity);
            }
        });

        it('splits the notices of both files the same way, and sums the counts', async () => {
            await mountAggregate();

            const section = the('parse-detail-notices');
            expect(section).toHaveAttribute('data-warnings', '2');
            expect(section).toHaveAttribute('data-notes', '3');
            expect(noticeSections(section)).toEqual([
                ['warning', '2'],
                ['info', '3'],
            ]);
            expect(noticeMessages(the('parse-detail-notice-section', {severity: 'warning'})), 'the warnings, file by file').toEqual([WARNING_CASH.message, WARNING_LEFT_OUT.message]);
            expect(noticeMessages(the('parse-detail-notice-section', {severity: 'info'})), 'the notes, file by file').toEqual([NOTE_TRANSFERS.message, NOTE_RATE.message, NOTE_BETA.message]);
        });
    });
});
