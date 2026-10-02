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
 * Plan: `LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md`, F.0 (F1 · D2).
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
