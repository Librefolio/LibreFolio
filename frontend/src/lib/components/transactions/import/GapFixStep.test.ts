// @vitest-environment jsdom
/**
 * GapFixStep — the "Align with the bank" step of the import wizard (report sets, phase C3, reworked
 * in phase F2 · U4-B). Component test (Vitest + jsdom).
 *
 * The step shows, per broker and plugin, what the bank states at each truth point next to what
 * LibreFolio will know, the corrections that close the difference (selected by default, D-S14)
 * and the verifications. It is a controlled component: the wizard owns the selection, and the step
 * asks to flip one key (`onToggle`) or to set many at once (`onSetSelected`, new in F2).
 *
 * Kept from C3: the root `import-wizard-gapfix` (data-proposal-count, data-selected-count),
 * `gapfix-group` (data-broker-id, data-plugin-code), `gapfix-error` (a failed group shows its error,
 * no cards, no table) and `gapfix-info-hidden-titles`.
 *
 * F2 (plan F2.0, U4-B), per group:
 *   gapfix-summary — a button per checkpoint and per verification, ordered by as-of date (on a shared
 *     date the checkpoint first): data-key, data-kind (opening | gap | verification), data-as-of,
 *     aria-pressed; on a checkpoint data-proposals, data-positions (rows with a non-zero difference),
 *     data-notes; on a verification data-ok. It shows the non-zero cash differences (CurrencyAmount).
 *   One click makes a card the group's active point, a second click clears it; one active per group.
 *   gapfix-point-details (data-key) — the active point's full comparison, with the testids of C3:
 *     gapfix-checkpoint · gapfix-cash-row · gapfix-position-row · gapfix-explanation · gapfix-note, or
 *     gapfix-verification · gapfix-verification-cash-row. Nothing for the points that are not active.
 *   gapfix-table — one DataTable of the group's corrections (only when there are some), rows
 *     tr[data-row-id=<proposal key>]; an active checkpoint keeps only its own, a verification (or
 *     nothing) keeps them all.
 *   gapfix-proposal-toggle — a button per row: aria-pressed, data-key, data-type, data-date, data-point.
 *   gapfix-select-all · gapfix-deselect-all · gapfix-select-visible — onSetSelected(keys, true|false).
 *   `gapfix-proposal` is gone.
 *
 * Reading of the contract (where the plan leaves a choice): the step opens with no active point — the
 * plan's "a click on a card filters the table, a second click removes the filter" starts unfiltered —
 * and each group has its own active point. "Visible" rows are the rows the table renders.
 *
 * The view is built by the real `buildGapFixView` (gapFixModel.ts), from outcomes shaped like the
 * responses of `POST /brokers/import/gap-fix` (decimals as strings): what the step receives in the
 * wizard, and no hand-made guess of the view's layout.
 *
 * Privacy (D5′). Money goes through CurrencyAmount (masked), a position's quantity next to the bank's
 * figures is masked, a correction's quantity is a transaction's and stays visible. The test toggles
 * privacy in place, in both directions, on one mount.
 *
 * Nothing here reads translated text: the assertions are on testids, data/ARIA attributes, the
 * privacy placeholder, and values the test itself passed in (amounts formatted the way the app
 * formats them, quantities, the names the callbacks return, the server's error message).
 *
 * Both the model and the component are loaded once, in a `beforeAll` with its own timeout: the
 * component's first transform is cold and takes seconds, which no test's budget should pay.
 */
import {afterEach, beforeAll, describe, expect, it, vi, type Mock} from 'vitest';
import {flushSync, tick, type Component} from 'svelte';

// The step formats cash through CurrencyAmount, which reads the currency catalogue. Every other API
// method is inert: the step receives its data as props.
vi.mock('$lib/api', async () => {
    const generated = await vi.importActual<{schemas: unknown}>('$lib/api/generated');
    const answers: Record<string, unknown> = {
        list_currencies_api_v1_utilities_currencies_get: {
            items: [
                {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
                {code: 'USD', name: 'US dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: [], country_names: []},
            ],
        },
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

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {isPrivacyEnabled, setPrivacyEnabled, togglePrivacy} from '$lib/stores/app/privacyStore.svelte';
import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';

// ---------------------------------------------------------------------------
// Loading the pieces under test
// ---------------------------------------------------------------------------

interface GapFixModelApi {
    buildGapFixView(outcomes: unknown[], localizeTodo: (reasonCode: string, message: string) => string): unknown;
    defaultGapFixSelection(view: unknown): Iterable<string>;
}

// Lazy globs rather than literal imports: the first transform of the component is cold, and here it
// runs in a hook with its own budget; a missing module fails each test on its own, naming it.
const MODEL_MODULES = import.meta.glob<Partial<GapFixModelApi>>('../../../utils/transactions/gapFixModel.ts');
const STEP_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./GapFixStep.svelte');

async function loadModel(): Promise<GapFixModelApi> {
    const load = MODEL_MODULES['../../../utils/transactions/gapFixModel.ts'];
    if (!load) throw new Error('gapFixModel.ts cannot be found');
    const mod = await load();
    if (typeof mod.buildGapFixView !== 'function' || typeof mod.defaultGapFixSelection !== 'function') throw new Error('gapFixModel.buildGapFixView / defaultGapFixSelection are missing');
    return mod as GapFixModelApi;
}

async function loadStep(): Promise<Component<Record<string, unknown>>> {
    const load = STEP_MODULES['./GapFixStep.svelte'];
    if (!load) throw new Error('GapFixStep.svelte cannot be found next to this test');
    return (await load()).default;
}

interface Pieces {
    model: GapFixModelApi;
    GapFixStep: Component<Record<string, unknown>>;
}

/** What the loading hook found: the pieces, or why they could not be loaded. */
let loaded: Pieces | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        loaded = {model: await loadModel(), GapFixStep: await loadStep()};
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

function pieces(): Pieces {
    if (loaded === undefined) throw new Error('the pieces under test were never loaded: their beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded;
}

// ---------------------------------------------------------------------------
// Fixtures: three outcomes of POST /gap-fix — answered, failed, and verifications only
// ---------------------------------------------------------------------------

const DANSKE = 'broker_danske_bank';
const TAGS = ['import', 'danske_bank', 'gap_fix'];
const ERROR_MESSAGE = 'HTTP 500: gap-fix failed';
/** A quantity no date, amount or name of this fixture contains: its presence is the quantity's. */
const POSITION_QTY = '137';

/**
 * Broker 7: an opening checkpoint (two currencies, one of them without a difference; one position
 * with a difference, one without; two corrections; one note), a gap checkpoint (one correction), a
 * verification that does not hold and one that holds, dated like the gap checkpoint.
 * Broker 8: the request failed. Broker 9: nothing to correct, one verification that does not hold.
 */
const OUTCOMES = [
    {
        brokerId: 7,
        pluginCode: DANSKE,
        response: {
            checkpoints: [
                {
                    as_of: '2020-02-02',
                    kind: 'opening',
                    cash: [
                        {currency: 'EUR', bank: '2699.50', librefolio: '0.00', difference: '2699.50'},
                        {currency: 'USD', bank: '10.00', librefolio: '10.00', difference: '0.00'},
                    ],
                    positions: [
                        {asset_id: 41, exactness: 'exact', bank: POSITION_QTY, librefolio: '0', difference: POSITION_QTY},
                        {asset_id: 42, exactness: 'at_least', bank: '180', librefolio: '200', difference: '0'},
                    ],
                    proposals: [
                        {broker_id: 7, type: 'DEPOSIT', date: '2020-02-02', cash: {code: 'EUR', amount: '2699.50'}, tags: TAGS, description: 'Gap-fix 2020-02-02'},
                        {broker_id: 7, type: 'ADJUSTMENT', date: '2020-02-02', asset_id: 41, quantity: POSITION_QTY, tags: TAGS, description: 'Gap-fix 2020-02-02'},
                    ],
                    todos: [{tx_index: 1, field: 'cost_basis_override', severity: 'blocker', reason_code: 'gap_fix_cost', message: 'Enter the per-unit cost of this position'}],
                    explanation: {
                        absorbed_count: 14,
                        absorbed_missing_count: 14,
                        absorbed_missing_cash: [{currency: 'EUR', amount: '2699.50'}],
                        opening_cash: [{currency: 'EUR', amount: '0.00'}],
                        unexplained_cash: [],
                        notes: [{severity: 'warning', code: 'unresolved_asset', message: 'A position of the bank refers to a security that is not resolved yet: it was left out', evidence: [], context: {asset_id: 2147483640}}],
                    },
                },
                {
                    as_of: '2020-08-31',
                    kind: 'gap',
                    cash: [{currency: 'EUR', bank: '500.00', librefolio: '380.00', difference: '120.00'}],
                    positions: [],
                    proposals: [{broker_id: 7, type: 'DEPOSIT', date: '2020-08-31', cash: {code: 'EUR', amount: '120.00'}, tags: TAGS, description: 'Gap-fix 2020-08-31'}],
                    todos: [],
                    explanation: {absorbed_count: 3, absorbed_missing_count: 1, absorbed_missing_cash: [{currency: 'EUR', amount: '120.00'}], opening_cash: [], unexplained_cash: [], notes: []},
                },
            ],
            verifications: [
                {as_of: '2020-06-26', ok: false, cash: [{currency: 'EUR', bank: '1994.46', librefolio: '2010.00', difference: '-15.54'}]},
                {as_of: '2020-08-31', ok: true, cash: [{currency: 'EUR', bank: '500.00', librefolio: '500.00', difference: '0.00'}]},
            ],
        },
    },
    {brokerId: 8, pluginCode: DANSKE, error: ERROR_MESSAGE},
    {
        brokerId: 9,
        pluginCode: DANSKE,
        response: {checkpoints: [], verifications: [{as_of: '2021-03-31', ok: false, cash: [{currency: 'EUR', bank: '10.00', librefolio: '12.00', difference: '-2.00'}]}]},
    },
];

// The keys of the view (gapFixModel): group `<broker>:<plugin>`, `<group>:cp:<i>`, `<checkpoint>:p:<j>`, `<group>:v:<i>`.
const G7 = `7:${DANSKE}`;
const CP_OPENING = `${G7}:cp:0`;
const CP_GAP = `${G7}:cp:1`;
const V_KO = `${G7}:v:0`;
const V_OK = `${G7}:v:1`;
const KEY_DEPOSIT = `${CP_OPENING}:p:0`;
const KEY_ADJUSTMENT = `${CP_OPENING}:p:1`;
const KEY_GAP_DEPOSIT = `${CP_GAP}:p:0`;
const G7_KEYS = [KEY_DEPOSIT, KEY_ADJUSTMENT, KEY_GAP_DEPOSIT];
const V9 = `9:${DANSKE}:v:0`;

const BROKER_NAMES: Record<number, string> = {7: 'Owned broker seven', 8: 'Owned broker eight', 9: 'Owned broker nine'};
const ASSET_NAMES: Record<number, string> = {41: 'Asset Alpha', 42: 'Asset Beta'};

/** An amount as CurrencyAmount writes its digits (the sign and the currency stay outside the mask). */
function money(amount: string): string {
    return Math.abs(Number(amount)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

// ---------------------------------------------------------------------------
// Mounting and reading
// ---------------------------------------------------------------------------

async function mountStep(choose?: (all: string[]) => string[]) {
    const {model, GapFixStep} = pieces();
    const view = model.buildGapFixView(OUTCOMES, (_reasonCode, message) => message);
    const keys = [...model.defaultGapFixSelection(view)];
    const onToggle = vi.fn();
    const onSetSelected = vi.fn();
    const props = {
        view,
        selected: new Set(choose ? choose(keys) : keys),
        onToggle,
        onSetSelected,
        assetName: (assetId: number) => ASSET_NAMES[assetId] ?? `#${assetId}`,
        brokerName: (brokerId: number) => BROKER_NAMES[brokerId] ?? `#${brokerId}`,
    };
    const rendered = render(GapFixStep, props);
    // Barrier: the step is mounted before anything is read.
    await screen.findByTestId('import-wizard-gapfix');
    return {rendered, props, keys, onToggle, onSetSelected};
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

const group = (brokerId: number) => the('gapfix-group', {'broker-id': String(brokerId), 'plugin-code': DANSKE});
const card = (key: string) => the('gapfix-summary', {key});
const toggle = (key: string) => the('gapfix-proposal-toggle', {key});
/** The table row of a correction, by its key. */
function row(key: string, scope: ParentNode = document): HTMLElement {
    const found = [...scope.querySelectorAll<HTMLElement>('tr[data-row-id]')].filter((tr) => tr.dataset.rowId === key);
    if (found.length !== 1) throw new Error(`expected exactly one table row ${key}, found ${found.length}`);
    return found[0];
}
/** The keys of the rows the table of a group renders, in order. */
function rowKeys(scope: ParentNode): string[] {
    return [...scope.querySelectorAll<HTMLElement>('[data-testid="gapfix-table"] tbody tr[data-row-id]')].map((tr) => tr.dataset.rowId ?? '');
}
/** The same keys as a set (sorted): the contract says which corrections a table shows, not in which order. */
function shownKeys(scope: ParentNode): string[] {
    return sorted(rowKeys(scope));
}
function sorted(keys: readonly string[]): string[] {
    return [...keys].sort();
}
/** Every summary card of a scope, keyed, with its aria-pressed. */
function pressedState(scope: ParentNode): Record<string, string | null> {
    return Object.fromEntries(all('gapfix-summary', scope).map((el) => [el.dataset.key ?? '', el.getAttribute('aria-pressed')]));
}

/** onSetSelected was called once, with exactly these keys (in any order) and this flag. */
function expectSetSelectedOnce(onSetSelected: Mock, keys: string[], selected: boolean): void {
    expect(onSetSelected).toHaveBeenCalledTimes(1);
    const [calledKeys, calledSelected] = onSetSelected.mock.calls[0] as [Iterable<string>, boolean];
    expect([...calledKeys].sort()).toEqual([...keys].sort());
    expect(calledSelected).toBe(selected);
}

async function togglePrivacyInPlace(): Promise<void> {
    togglePrivacy();
    flushSync();
    await tick();
}

beforeAll(async () => {
    await setupI18n();
    await ensureCurrenciesLoaded('en');
    setPrivacyEnabled(false);
});

afterEach(() => {
    // Module-level state shared by every test of this file: a leftover `true` would mount the next step masked.
    setPrivacyEnabled(false);
});

// ---------------------------------------------------------------------------
// Kept from C3
// ---------------------------------------------------------------------------

describe('GapFixStep — kept from C3 (guards: true before F2 too)', () => {
    it('the root counts the proposals of the view and the selected ones', async () => {
        await mountStep();

        const root = the('import-wizard-gapfix');
        expect(root).toHaveAttribute('data-proposal-count', '3');
        expect(root).toHaveAttribute('data-selected-count', '3');
    });

    it('one group per outcome, named through brokerName; the failed one shows its error and nothing else', async () => {
        await mountStep();

        expect(all('gapfix-group')).toHaveLength(3);
        expect(text(group(7))).toContain(BROKER_NAMES[7]);
        expect(text(group(9))).toContain(BROKER_NAMES[9]);
        const failed = group(8);
        expect(text(failed)).toContain(BROKER_NAMES[8]);
        expect(text(the('gapfix-error', {}, failed))).toContain(ERROR_MESSAGE);
        expect(all('gapfix-error', group(7))).toHaveLength(0);
        for (const testId of ['gapfix-summary', 'gapfix-table', 'gapfix-point-details', 'gapfix-checkpoint', 'gapfix-verification', 'gapfix-proposal-toggle']) {
            expect(all(testId, failed), `${testId} in the failed group`).toHaveLength(0);
        }
    });

    it('closes with the note on the titles a file cannot show', async () => {
        await mountStep();

        expect(all('gapfix-info-hidden-titles')).toHaveLength(1);
    });
});

// ---------------------------------------------------------------------------
// F2 · U4-B — the summary cards
// ---------------------------------------------------------------------------

describe('GapFixStep — F2: one summary card per truth point', () => {
    it('one card per checkpoint and per verification, in date order, the checkpoint first on a shared date', async () => {
        await mountStep();

        const cards = all('gapfix-summary', group(7));
        expect(cards.map((el) => [el.dataset.key, el.dataset.kind, el.dataset.asOf])).toEqual([
            [CP_OPENING, 'opening', '2020-02-02'],
            [V_KO, 'verification', '2020-06-26'],
            [CP_GAP, 'gap', '2020-08-31'],
            [V_OK, 'verification', '2020-08-31'],
        ]);
        for (const el of cards) expect(el.tagName, `${el.dataset.key} is a button`).toBe('BUTTON');
        expect(all('gapfix-summary', group(9)).map((el) => [el.dataset.key, el.dataset.kind, el.dataset.asOf])).toEqual([[V9, 'verification', '2021-03-31']]);
    });

    it('a checkpoint card counts its corrections, its positions with a difference and its notes; a verification card says whether it holds', async () => {
        await mountStep();

        const opening = card(CP_OPENING);
        expect(opening).toHaveAttribute('data-proposals', '2');
        expect(opening).toHaveAttribute('data-positions', '1');
        expect(opening).toHaveAttribute('data-notes', '1');
        const gap = card(CP_GAP);
        expect(gap).toHaveAttribute('data-proposals', '1');
        expect(gap).toHaveAttribute('data-positions', '0');
        expect(gap).toHaveAttribute('data-notes', '0');
        expect(card(V_KO)).toHaveAttribute('data-ok', 'false');
        expect(card(V_OK)).toHaveAttribute('data-ok', 'true');
        expect(card(V9)).toHaveAttribute('data-ok', 'false');
    });

    it('a card shows the non-zero cash differences of its point, and only those', async () => {
        await mountStep();

        const opening = text(card(CP_OPENING));
        expect(opening, 'the opening difference').toContain(money('2699.50'));
        expect(opening).toContain('EUR');
        expect(opening, 'the currency without a difference is left out').not.toContain('USD');
        expect(text(card(CP_GAP)), 'the gap difference').toContain(money('120.00'));
        expect(text(card(V_KO)), 'the difference of a verification that does not hold').toContain(money('-15.54'));
    });

    it('nothing is active on arrival: every card unpressed, no details, the whole table', async () => {
        await mountStep();

        expect(pressedState(group(7))).toEqual({[CP_OPENING]: 'false', [V_KO]: 'false', [CP_GAP]: 'false', [V_OK]: 'false'});
        expect(all('gapfix-point-details')).toHaveLength(0);
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted(G7_KEYS)));
    });
});

// ---------------------------------------------------------------------------
// F2 · U4-B — the active point
// ---------------------------------------------------------------------------

describe('GapFixStep — F2: a card is the active point of its group', () => {
    it('a click on a checkpoint card makes it active: its full comparison opens and the table keeps its corrections', async () => {
        await mountStep();

        await fireEvent.click(card(CP_OPENING));

        expect(pressedState(group(7))).toEqual({[CP_OPENING]: 'true', [V_KO]: 'false', [CP_GAP]: 'false', [V_OK]: 'false'});
        const details = the('gapfix-point-details', {key: CP_OPENING});
        expect(all('gapfix-point-details')).toHaveLength(1);
        const checkpoint = the('gapfix-checkpoint', {'as-of': '2020-02-02', kind: 'opening'}, details);
        the('gapfix-cash-row', {currency: 'EUR', difference: '2699.50'}, checkpoint);
        the('gapfix-cash-row', {currency: 'USD', difference: '0.00'}, checkpoint);
        expect(text(the('gapfix-position-row', {'asset-id': '41', exactness: 'exact'}, checkpoint))).toContain(ASSET_NAMES[41]);
        the('gapfix-position-row', {'asset-id': '42', exactness: 'at_least'}, checkpoint);
        the('gapfix-note', {code: 'unresolved_asset'}, the('gapfix-explanation', {}, checkpoint));
        // The points that are not active show nothing of their comparison.
        expect(all('gapfix-checkpoint')).toHaveLength(1);
        expect(all('gapfix-verification')).toHaveLength(0);
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted([KEY_DEPOSIT, KEY_ADJUSTMENT])));
    });

    it('a second click on the active card clears it: no details, the whole table again', async () => {
        await mountStep();
        await fireEvent.click(card(CP_OPENING));
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted([KEY_DEPOSIT, KEY_ADJUSTMENT])));

        await fireEvent.click(card(CP_OPENING));

        expect(pressedState(group(7))).toEqual({[CP_OPENING]: 'false', [V_KO]: 'false', [CP_GAP]: 'false', [V_OK]: 'false'});
        expect(all('gapfix-point-details')).toHaveLength(0);
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted(G7_KEYS)));
    });

    it('one active point per group: another card of the group takes over', async () => {
        await mountStep();
        await fireEvent.click(card(CP_OPENING));

        await fireEvent.click(card(CP_GAP));

        expect(pressedState(group(7))).toEqual({[CP_OPENING]: 'false', [V_KO]: 'false', [CP_GAP]: 'true', [V_OK]: 'false'});
        const details = the('gapfix-point-details', {key: CP_GAP});
        expect(all('gapfix-point-details')).toHaveLength(1);
        the('gapfix-cash-row', {currency: 'EUR', difference: '120.00'}, the('gapfix-checkpoint', {'as-of': '2020-08-31', kind: 'gap'}, details));
        expect(all('gapfix-checkpoint')).toHaveLength(1);
        await waitFor(() => expect(shownKeys(group(7))).toEqual([KEY_GAP_DEPOSIT]));
    });

    it('a verification card opens its comparison and leaves the whole table: a verification corrects nothing', async () => {
        await mountStep();

        await fireEvent.click(card(V_KO));

        expect(pressedState(group(7))).toEqual({[CP_OPENING]: 'false', [V_KO]: 'true', [CP_GAP]: 'false', [V_OK]: 'false'});
        const verification = the('gapfix-verification', {'as-of': '2020-06-26', ok: 'false'}, the('gapfix-point-details', {key: V_KO}));
        the('gapfix-verification-cash-row', {currency: 'EUR', difference: '-15.54'}, verification);
        expect(all('gapfix-checkpoint')).toHaveLength(0);
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted(G7_KEYS)));
    });

    it('a verification that holds shows no cash row', async () => {
        await mountStep();

        await fireEvent.click(card(V_OK));

        const verification = the('gapfix-verification', {'as-of': '2020-08-31', ok: 'true'}, the('gapfix-point-details', {key: V_OK}));
        expect(all('gapfix-verification-cash-row', verification)).toHaveLength(0);
    });

    it('each group has its own active point', async () => {
        await mountStep();

        await fireEvent.click(card(CP_OPENING));
        await fireEvent.click(card(V9));

        expect(card(CP_OPENING)).toHaveAttribute('aria-pressed', 'true');
        expect(card(V9)).toHaveAttribute('aria-pressed', 'true');
        the('gapfix-point-details', {key: CP_OPENING}, group(7));
        the('gapfix-verification', {'as-of': '2021-03-31', ok: 'false'}, the('gapfix-point-details', {key: V9}, group(9)));
    });
});

// ---------------------------------------------------------------------------
// F2 · U4-B — the table of the corrections
// ---------------------------------------------------------------------------

describe('GapFixStep — F2: one table of the corrections per group', () => {
    it('a table for a group with corrections, one row per correction keyed by its proposal key; none for a group without', async () => {
        await mountStep();

        the('gapfix-table', {}, group(7));
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted(G7_KEYS)));
        expect(all('gapfix-table', group(9)), 'broker 9 proposes nothing').toHaveLength(0);
        expect(all('gapfix-table', group(8)), 'broker 8 failed').toHaveLength(0);
        expect(all('gapfix-table')).toHaveLength(1);
    });

    it("each row's toggle is a button carrying its key, type, date and point, pressed when selected", async () => {
        await mountStep();
        await waitFor(() => expect(all('gapfix-proposal-toggle')).toHaveLength(3));

        const expected = [
            {key: KEY_DEPOSIT, type: 'DEPOSIT', date: '2020-02-02', point: CP_OPENING},
            {key: KEY_ADJUSTMENT, type: 'ADJUSTMENT', date: '2020-02-02', point: CP_OPENING},
            {key: KEY_GAP_DEPOSIT, type: 'DEPOSIT', date: '2020-08-31', point: CP_GAP},
        ];
        for (const facts of expected) {
            const button = the('gapfix-proposal-toggle', {}, row(facts.key, group(7)));
            expect(button.tagName, facts.key).toBe('BUTTON');
            expect(button).toHaveAttribute('aria-pressed', 'true');
            expect(button).toHaveAttribute('data-key', facts.key);
            expect(button).toHaveAttribute('data-type', facts.type);
            expect(button).toHaveAttribute('data-date', facts.date);
            expect(button).toHaveAttribute('data-point', facts.point);
        }
    });

    it('a correction shows its asset, and its quantity', async () => {
        await mountStep();
        await waitFor(() => expect(all('gapfix-proposal-toggle')).toHaveLength(3));

        const adjustment = text(row(KEY_ADJUSTMENT, group(7)));
        expect(adjustment).toContain(ASSET_NAMES[41]);
        expect(adjustment).toContain(POSITION_QTY);
    });

    it('the toggle asks the wizard to flip that key, once, and nothing else', async () => {
        const {onToggle, onSetSelected} = await mountStep();
        await waitFor(() => expect(all('gapfix-proposal-toggle')).toHaveLength(3));

        await fireEvent.click(toggle(KEY_ADJUSTMENT));

        expect(onToggle).toHaveBeenCalledTimes(1);
        expect(onToggle).toHaveBeenCalledWith(KEY_ADJUSTMENT);
        expect(onSetSelected).not.toHaveBeenCalled();
    });

    it('the selection is the prop: aria-pressed and the counts follow it', async () => {
        const {rendered, props} = await mountStep((keys) => keys.filter((key) => key === KEY_DEPOSIT));
        await waitFor(() => expect(all('gapfix-proposal-toggle')).toHaveLength(3));

        expect(toggle(KEY_DEPOSIT)).toHaveAttribute('aria-pressed', 'true');
        expect(toggle(KEY_ADJUSTMENT)).toHaveAttribute('aria-pressed', 'false');
        expect(toggle(KEY_GAP_DEPOSIT)).toHaveAttribute('aria-pressed', 'false');
        expect(the('import-wizard-gapfix')).toHaveAttribute('data-selected-count', '1');
        expect(the('import-wizard-gapfix')).toHaveAttribute('data-proposal-count', '3');

        await rendered.rerender({...props, selected: new Set<string>()});

        await waitFor(() => expect(toggle(KEY_DEPOSIT)).toHaveAttribute('aria-pressed', 'false'));
        expect(the('import-wizard-gapfix')).toHaveAttribute('data-selected-count', '0');

        await rendered.rerender({...props, selected: new Set([...G7_KEYS, 'a-key-of-no-proposal'])});

        await waitFor(() => expect(toggle(KEY_ADJUSTMENT)).toHaveAttribute('aria-pressed', 'true'));
        expect(toggle(KEY_GAP_DEPOSIT)).toHaveAttribute('aria-pressed', 'true');
        expect(the('import-wizard-gapfix')).toHaveAttribute('data-selected-count', '3');
    });

    it('the list of C3 is gone: no gapfix-proposal', async () => {
        await mountStep();
        await waitFor(() => expect(all('gapfix-proposal-toggle')).toHaveLength(3));

        expect(all('gapfix-proposal')).toHaveLength(0);
    });
});

// ---------------------------------------------------------------------------
// F2 · U4-B — the review commands
// ---------------------------------------------------------------------------

describe('GapFixStep — F2: select all, deselect all, select visible', () => {
    it('select all asks for every correction of the group, once', async () => {
        const {onSetSelected, onToggle} = await mountStep(() => []);

        await fireEvent.click(the('gapfix-select-all', {}, group(7)));

        expectSetSelectedOnce(onSetSelected, G7_KEYS, true);
        expect(onToggle).not.toHaveBeenCalled();
    });

    it('deselect all lets go of every correction of the group, once', async () => {
        const {onSetSelected, onToggle} = await mountStep();

        await fireEvent.click(the('gapfix-deselect-all', {}, group(7)));

        expectSetSelectedOnce(onSetSelected, G7_KEYS, false);
        expect(onToggle).not.toHaveBeenCalled();
    });

    it('select visible, with no active point: the rows the table shows, which are all of them here', async () => {
        const {onSetSelected} = await mountStep(() => []);
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted(G7_KEYS)));
        const shown = rowKeys(group(7));

        await fireEvent.click(the('gapfix-select-visible', {}, group(7)));

        expectSetSelectedOnce(onSetSelected, shown, true);
    });

    it('select visible, with a checkpoint active: exactly that checkpoint\u2019s corrections', async () => {
        const {onSetSelected} = await mountStep(() => []);
        await fireEvent.click(card(CP_GAP));
        await waitFor(() => expect(shownKeys(group(7))).toEqual([KEY_GAP_DEPOSIT]));

        await fireEvent.click(the('gapfix-select-visible', {}, group(7)));

        expectSetSelectedOnce(onSetSelected, [KEY_GAP_DEPOSIT], true);
    });

    it('select visible, with the opening checkpoint active: its two corrections', async () => {
        const {onSetSelected} = await mountStep(() => []);
        await fireEvent.click(card(CP_OPENING));
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted([KEY_DEPOSIT, KEY_ADJUSTMENT])));

        await fireEvent.click(the('gapfix-select-visible', {}, group(7)));

        expectSetSelectedOnce(onSetSelected, [KEY_DEPOSIT, KEY_ADJUSTMENT], true);
    });
});

// ---------------------------------------------------------------------------
// Privacy (D5′)
// ---------------------------------------------------------------------------

describe('GapFixStep — privacy (D5′): money and positions are masked, a correction\u2019s quantity is a transaction\u2019s', () => {
    const OPENING_DIFF = money('2699.50');

    /** Open the opening point, so its position rows are on screen, and wait for its two rows. */
    async function openOpening(): Promise<void> {
        await fireEvent.click(card(CP_OPENING));
        the('gapfix-point-details', {key: CP_OPENING});
        await waitFor(() => expect(shownKeys(group(7))).toEqual(sorted([KEY_DEPOSIT, KEY_ADJUSTMENT])));
    }

    async function expectState(step: string, privacyOn: boolean): Promise<void> {
        expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(privacyOn);
        const opening = text(card(CP_OPENING));
        const position = text(the('gapfix-position-row', {'asset-id': '41'}));
        const deposit = text(row(KEY_DEPOSIT, group(7)));
        const adjustment = text(row(KEY_ADJUSTMENT, group(7)));
        if (privacyOn) {
            expect(opening, `${step} — the card's difference is masked`).toContain(PRIVACY_PLACEHOLDER);
            expect(opening, `${step} — no digit of the card's difference`).not.toContain(OPENING_DIFF);
            expect(position, `${step} — the position quantity is masked`).toContain(PRIVACY_PLACEHOLDER);
            expect(position, `${step} — no digit of the position quantity`).not.toContain(POSITION_QTY);
            expect(deposit, `${step} — the correction's cash is masked`).toContain(PRIVACY_PLACEHOLDER);
            expect(deposit, `${step} — no digit of the correction's cash`).not.toContain(OPENING_DIFF);
        } else {
            expect(opening, `${step} — the card's difference in the clear`).toContain(OPENING_DIFF);
            expect(opening, `${step} — no placeholder on the card`).not.toContain(PRIVACY_PLACEHOLDER);
            expect(position, `${step} — the position quantity in the clear`).toContain(POSITION_QTY);
            expect(position, `${step} — no placeholder in the position`).not.toContain(PRIVACY_PLACEHOLDER);
            expect(deposit, `${step} — the correction's cash in the clear`).toContain(OPENING_DIFF);
            expect(deposit, `${step} — no placeholder in the correction`).not.toContain(PRIVACY_PLACEHOLDER);
        }
        // Subject: the correction is a transaction, its quantity stays visible either way.
        expect(adjustment, `${step} — the correction's quantity stays visible`).toContain(POSITION_QTY);
    }

    it('mounted in the clear, then privacy on and off in place', async () => {
        await mountStep();
        await openOpening();
        await expectState('mount, privacy off', false);

        await togglePrivacyInPlace();
        await expectState('off → on', true);

        await togglePrivacyInPlace();
        await expectState('on → off', false);
    });

    it('mounted with privacy already on', async () => {
        setPrivacyEnabled(true);
        flushSync();
        await mountStep();
        await openOpening();
        await expectState('mount, privacy on', true);

        await togglePrivacyInPlace();
        await expectState('on → off', false);
    });
});
