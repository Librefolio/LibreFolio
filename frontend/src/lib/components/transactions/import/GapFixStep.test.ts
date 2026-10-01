// @vitest-environment jsdom
/**
 * GapFixStep — the "Align with the bank" step of the import wizard (report sets, phase C3).
 * Component test (Vitest + jsdom).
 *
 * The step shows, per broker and plugin, what the bank states at each truth point next to what
 * LibreFolio will know, the corrections that close the difference (selected by default, D-S14)
 * and the verifications. It is a controlled component: the wizard owns the selection and the
 * step only asks to flip a key (`onToggle`). Props, testids and data attributes are the ones
 * pinned in the plan (C3.0):
 *   import-wizard-gapfix (data-proposal-count, data-selected-count)
 *   gapfix-group (data-broker-id, data-plugin-code) · gapfix-error
 *   gapfix-checkpoint (data-as-of, data-kind) · gapfix-cash-row (data-currency, data-difference)
 *   gapfix-position-row (data-asset-id, data-exactness) · gapfix-explanation · gapfix-note (data-code)
 *   gapfix-proposal (data-key, data-type, data-date, data-selected) · gapfix-proposal-toggle
 *   gapfix-verification (data-as-of, data-ok) · gapfix-info-hidden-titles
 *
 * The view is built by the real `buildGapFixView` (gapFixModel.ts), from outcomes shaped like
 * the responses of `POST /brokers/import/gap-fix` (decimals as strings): what the step receives
 * in the wizard, and no hand-made guess of the view's layout.
 *
 * Privacy (D5′). A quantity next to prices is masked: the position rows go through
 * `maskableQuantity`. The proposals are transactions, and their quantity stays visible. The
 * test toggles privacy in place, in both directions, on one mount; the masked position is the
 * control that the toggle reached the step, the visible proposal is the subject.
 *
 * Nothing here reads translated text: the assertions are on testids and data attributes, on the
 * privacy placeholder, and on values the test itself passed in (quantities, the broker and asset
 * names the callbacks return, the server's error message).
 *
 * Both the model and the component are loaded once, in a `beforeAll` with its own timeout: the
 * component's first transform is cold and takes seconds, which no test's budget should pay. While
 * either does not exist, every test still fails on its own and says which one is missing.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick, type Component} from 'svelte';

// The step formats cash through CurrencyAmount, which reads the currency catalogue. Every other
// API method is inert: the step receives its data as props.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({items: [{code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []}]}));
                }
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
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

// Lazy globs rather than literal imports: Vite resolves a literal import (an alias, or a `.svelte`
// file) while it transforms this test, so a missing module would fail the whole file at collection.
// A glob is empty until its file exists, and then each test fails on its own, naming what is missing.
const MODEL_MODULES = import.meta.glob<Partial<GapFixModelApi>>('../../../utils/transactions/gapFixModel.ts');
const STEP_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./GapFixStep.svelte');

async function loadModel(): Promise<GapFixModelApi> {
    const load = MODEL_MODULES['../../../utils/transactions/gapFixModel.ts'];
    if (!load) throw new Error('gapFixModel.ts is not implemented yet (gap-fix, phase C3)');
    const mod = await load();
    if (typeof mod.buildGapFixView !== 'function' || typeof mod.defaultGapFixSelection !== 'function') throw new Error('gapFixModel.buildGapFixView / defaultGapFixSelection are not implemented yet (gap-fix, phase C3)');
    return mod as GapFixModelApi;
}

async function loadStep(): Promise<Component<Record<string, unknown>>> {
    const load = STEP_MODULES['./GapFixStep.svelte'];
    if (!load) throw new Error('GapFixStep.svelte is not implemented yet (gap-fix step, phase C3)');
    return (await load()).default;
}

interface Pieces {
    model: GapFixModelApi;
    GapFixStep: Component<Record<string, unknown>>;
}

/** What the loading hook found: the pieces, or why they could not be loaded. */
let loaded: Pieces | {error: unknown} | undefined;

/**
 * Load the pieces once, before any test. The first load of the component is a cold transform —
 * vite-plugin-svelte compiles it and everything it imports (the icon barrel included) — measured
 * at ~7.7 s: inside a test it ran past that test's 5 s budget, and its late mount then leaked into
 * the next test. Here it has a timeout of its own. A load failure is recorded, not thrown, so that
 * each test still fails on its own, through `pieces()`, with the message naming what is missing.
 */
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
// Fixtures: two outcomes of POST /gap-fix — one answered, one failed
// ---------------------------------------------------------------------------

const DANSKE = 'broker_danske_bank';
const TAGS = ['import', 'danske_bank', 'gap_fix'];
const ERROR_MESSAGE = 'HTTP 500: gap-fix failed';
/** A quantity no date, amount or name of this fixture contains: its presence is the quantity's. */
const POSITION_QTY = '137';

const OUTCOMES = [
    {
        brokerId: 7,
        pluginCode: DANSKE,
        response: {
            checkpoints: [
                {
                    as_of: '2020-02-02',
                    kind: 'opening',
                    cash: [{currency: 'EUR', bank: '2699.50', librefolio: '0.00', difference: '2699.50'}],
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
            ],
            verifications: [
                {as_of: '2020-06-26', ok: false, cash: [{currency: 'EUR', bank: '1994.46', librefolio: '2010.00', difference: '-15.54'}]},
                {as_of: '2020-12-31', ok: true, cash: [{currency: 'EUR', bank: '100.00', librefolio: '100.00', difference: '0.00'}]},
            ],
        },
    },
    {brokerId: 8, pluginCode: DANSKE, error: ERROR_MESSAGE},
];

const KEY_DEPOSIT = `7:${DANSKE}:cp:0:p:0`;
const KEY_ADJUSTMENT = `7:${DANSKE}:cp:0:p:1`;
const BROKER_NAMES: Record<number, string> = {7: 'Owned broker seven', 8: 'Owned broker eight'};
const ASSET_NAMES: Record<number, string> = {41: 'Asset Alpha', 42: 'Asset Beta'};

// ---------------------------------------------------------------------------
// Mounting and reading
// ---------------------------------------------------------------------------

async function mountStep(choose?: (all: string[]) => string[]) {
    const {model, GapFixStep} = pieces();
    const view = model.buildGapFixView(OUTCOMES, (_reasonCode, message) => message);
    const all = [...model.defaultGapFixSelection(view)];
    const onToggle = vi.fn();
    const props = {
        view,
        selected: new Set(choose ? choose(all) : all),
        onToggle,
        assetName: (assetId: number) => ASSET_NAMES[assetId] ?? `#${assetId}`,
        brokerName: (brokerId: number) => BROKER_NAMES[brokerId] ?? `#${brokerId}`,
    };
    const rendered = render(GapFixStep, props);
    // Barrier: the step is mounted before anything is read.
    await screen.findByTestId('import-wizard-gapfix');
    return {rendered, props, all, onToggle};
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
// Tests
// ---------------------------------------------------------------------------

describe('GapFixStep — structure', () => {
    it('the root counts the proposals of the view and the selected ones', async () => {
        await mountStep();

        const root = the('import-wizard-gapfix');
        expect(root).toHaveAttribute('data-proposal-count', '2');
        expect(root).toHaveAttribute('data-selected-count', '2');
    });

    it('one group per outcome, by broker and plugin, named through brokerName; the failed one shows its error and nothing else', async () => {
        await mountStep();

        expect(all('gapfix-group')).toHaveLength(2);
        const answered = the('gapfix-group', {'broker-id': '7', 'plugin-code': DANSKE});
        const failed = the('gapfix-group', {'broker-id': '8', 'plugin-code': DANSKE});

        expect(text(answered)).toContain(BROKER_NAMES[7]);
        expect(text(failed)).toContain(BROKER_NAMES[8]);
        expect(text(the('gapfix-error', {}, failed))).toContain(ERROR_MESSAGE);
        expect(all('gapfix-error', answered)).toHaveLength(0);
        for (const row of ['gapfix-checkpoint', 'gapfix-proposal', 'gapfix-verification']) expect(all(row, failed), `${row} in the failed group`).toHaveLength(0);
    });

    it('a checkpoint shows its cash and position comparison, its notes and its proposals', async () => {
        await mountStep();

        const answered = the('gapfix-group', {'broker-id': '7'});
        const checkpoint = the('gapfix-checkpoint', {'as-of': '2020-02-02', kind: 'opening'}, answered);
        expect(all('gapfix-checkpoint')).toHaveLength(1);

        the('gapfix-cash-row', {currency: 'EUR', difference: '2699.50'}, checkpoint);
        const exact = the('gapfix-position-row', {'asset-id': '41', exactness: 'exact'}, checkpoint);
        the('gapfix-position-row', {'asset-id': '42', exactness: 'at_least'}, checkpoint);
        expect(all('gapfix-position-row', checkpoint)).toHaveLength(2);
        expect(text(exact)).toContain(ASSET_NAMES[41]);

        const explanation = the('gapfix-explanation', {}, checkpoint);
        the('gapfix-note', {code: 'unresolved_asset'}, explanation);

        const deposit = the('gapfix-proposal', {key: KEY_DEPOSIT}, checkpoint);
        const adjustment = the('gapfix-proposal', {key: KEY_ADJUSTMENT}, checkpoint);
        expect(deposit).toHaveAttribute('data-type', 'DEPOSIT');
        expect(deposit).toHaveAttribute('data-date', '2020-02-02');
        expect(deposit).toHaveAttribute('data-selected', 'true');
        expect(adjustment).toHaveAttribute('data-type', 'ADJUSTMENT');
        expect(adjustment).toHaveAttribute('data-date', '2020-02-02');
        expect(adjustment).toHaveAttribute('data-selected', 'true');
        expect(text(adjustment)).toContain(ASSET_NAMES[41]);
        expect(text(adjustment)).toContain(POSITION_QTY);
        expect(all('gapfix-proposal')).toHaveLength(2);
    });

    it('one verification per truth point that is only compared, with whether it holds', async () => {
        await mountStep();

        const answered = the('gapfix-group', {'broker-id': '7'});
        the('gapfix-verification', {'as-of': '2020-06-26', ok: 'false'}, answered);
        the('gapfix-verification', {'as-of': '2020-12-31', ok: 'true'}, answered);
        expect(all('gapfix-verification')).toHaveLength(2);
    });

    it('closes with the note on the titles a file cannot show', async () => {
        await mountStep();

        expect(all('gapfix-info-hidden-titles')).toHaveLength(1);
    });
});

describe('GapFixStep — selection', () => {
    it('the toggle of a proposal asks the wizard to flip that key, and only that one', async () => {
        const {onToggle} = await mountStep();

        await fireEvent.click(the('gapfix-proposal-toggle', {}, the('gapfix-proposal', {key: KEY_ADJUSTMENT})));

        expect(onToggle).toHaveBeenCalledTimes(1);
        expect(onToggle).toHaveBeenCalledWith(KEY_ADJUSTMENT);
    });

    it('the selection is the prop: data-selected and the count follow it', async () => {
        const {rendered, props} = await mountStep((keys) => keys.filter((key) => key === KEY_DEPOSIT));

        expect(the('gapfix-proposal', {key: KEY_DEPOSIT})).toHaveAttribute('data-selected', 'true');
        expect(the('gapfix-proposal', {key: KEY_ADJUSTMENT})).toHaveAttribute('data-selected', 'false');
        expect(the('import-wizard-gapfix')).toHaveAttribute('data-selected-count', '1');
        expect(the('import-wizard-gapfix')).toHaveAttribute('data-proposal-count', '2');

        await rendered.rerender({...props, selected: new Set<string>()});

        expect(the('gapfix-proposal', {key: KEY_DEPOSIT})).toHaveAttribute('data-selected', 'false');
        expect(the('import-wizard-gapfix')).toHaveAttribute('data-selected-count', '0');

        await rendered.rerender({...props, selected: new Set([KEY_DEPOSIT, KEY_ADJUSTMENT, 'a-key-of-no-proposal'])});

        expect(the('gapfix-proposal', {key: KEY_ADJUSTMENT})).toHaveAttribute('data-selected', 'true');
        expect(the('import-wizard-gapfix')).toHaveAttribute('data-selected-count', '2');
    });
});

describe('GapFixStep — privacy (D5′): a position is masked, a proposal is a transaction', () => {
    const position = () => the('gapfix-position-row', {'asset-id': '41'});
    const adjustment = () => the('gapfix-proposal', {key: KEY_ADJUSTMENT});

    async function expectState(step: string, privacyOn: boolean): Promise<void> {
        expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(privacyOn);
        // Control: the position row follows the flag (quantity next to prices).
        if (privacyOn) {
            expect(text(position()), `${step} — the position quantity is masked`).toContain(PRIVACY_PLACEHOLDER);
            expect(text(position()), `${step} — no digit of the position quantity`).not.toContain(POSITION_QTY);
        } else {
            expect(text(position()), `${step} — the position quantity is in the clear`).toContain(POSITION_QTY);
            expect(text(position()), `${step} — no placeholder in the position`).not.toContain(PRIVACY_PLACEHOLDER);
        }
        // Subject: the proposal is a transaction, its quantity stays visible either way.
        expect(text(adjustment()), `${step} — the proposal quantity stays visible`).toContain(POSITION_QTY);
    }

    it('mounted in the clear, then privacy on and off in place', async () => {
        await mountStep();
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
        await expectState('mount, privacy on', true);

        await togglePrivacyInPlace();
        await expectState('on → off', false);
    });
});
