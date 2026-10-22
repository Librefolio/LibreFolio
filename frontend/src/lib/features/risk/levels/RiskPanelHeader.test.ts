// @vitest-environment jsdom
/**
 * RiskPanelHeader — what its data-quality banner does with an issue that asks for an FX pair (Vitest + jsdom).
 *
 * TC-23, decision Q-TC23-1 (a), the developer: an `add_fx_pair` issue — the backend's `MISSING_FX_MARKET`, which
 * names its pairs in `affected_fx_pairs` and no `cta_target` — no longer sends the user to the FX page. The panel
 * opens the add-pair dialog itself, on the pair that was pressed, or empty when the issue names none; the answer
 * on screen is then reloaded once the dialog has created the pair, and again once its automatic sync has settled.
 * The panel reloads through `controller.handleSynced()`, the same call its sync button's modal makes.
 *
 * What is pinned:
 *   - a chip opens the dialog on its own pair, and the next chip on its own, not the first one's;
 *   - the one button of an issue with no pair opens it with nothing chosen;
 *   - `oncreated` and `onsynced` each reload, once;
 *   - an add chip never navigates, while a `navigate_fx` chip still leaves for its pair's page — the control that
 *     proves the `goto` spy is wired, so a missing call below is not a spy that was never listening.
 *
 * The dialog is replaced by `FxPairAddModalStub` (its own business is the dialog's own test, and the real one loads
 * the currency graph and the routes through the API at mount), and the sync modal by an empty component. Nothing
 * here reads a translated sentence: the banner, its folding toggle, its chips and its button are found by test id.
 * The controller is a plain object with the three fields the header reads.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
import type {RiskPanelController} from '$lib/features/risk/riskPanelController.svelte';

import RiskPanelHeader from './RiskPanelHeader.svelte';

const mocks = vi.hoisted(() => ({
    goto: vi.fn((_href: string) => Promise.resolve()).mockName('goto'),
}));

vi.mock('$app/navigation', () => ({
    goto: mocks.goto,
    replaceState: vi.fn(),
    pushState: vi.fn(),
    invalidate: vi.fn(() => Promise.resolve()),
    invalidateAll: vi.fn(() => Promise.resolve()),
    preloadCode: vi.fn(() => Promise.resolve()),
    preloadData: vi.fn(() => Promise.resolve()),
    afterNavigate: vi.fn(),
    beforeNavigate: vi.fn(),
    onNavigate: vi.fn(),
}));
// The dialog is the subject's neighbour, not the subject: a stub that publishes the props it was given.
vi.mock('$lib/components/fx/FxPairAddModal.svelte', async () => ({default: (await import('$test/harness/FxPairAddModalStub.svelte')).default}));
// The sync modal fetches providers and rates when it opens, and no case here opens it.
vi.mock('$lib/components/ui/modals/PageSyncModal.svelte', () => ({default: () => {}}));

const STUB = 'fx-pair-add-modal-stub';
const STUB_CREATED = 'fx-pair-add-modal-stub-created';
const STUB_SYNCED = 'fx-pair-add-modal-stub-synced';
const STUB_CLOSE = 'fx-pair-add-modal-stub-close';
const BANNER_TOGGLE = 'data-quality-toggle';
const ADD_CODE = 'MISSING_FX_MARKET';
const NAVIGATE_CODE = 'MISSING_FX_RATES';

/** A pair with no exchange-rate route, as `service.py::_fx_issue` builds `MISSING_FX_MARKET`: it asks for one (`add_fx_pair`) and names no target. */
function unroutedPairIssue(pairs: readonly string[]): DataQualityIssue {
    return {
        domain: 'forex',
        code: ADD_CODE,
        severity: 'warning',
        message_i18n_key: 'risk.quality.missingFx',
        message_params: {count: pairs.length},
        count: pairs.length,
        affected_fx_pairs: [...pairs],
        cta_action: 'add_fx_pair',
        cta_target: null,
        group_key: 'missing_fx',
    };
}

/** A configured pair whose rates are only manual: it asks to open the pair (`navigate_fx`) and names it as its target. */
function manualPairIssue(pair: string): DataQualityIssue {
    return {
        domain: 'forex',
        code: NAVIGATE_CODE,
        severity: 'warning',
        message_i18n_key: 'risk.quality.missingFxRatesManual',
        message_params: {count: 1},
        count: 1,
        affected_fx_pairs: [pair],
        cta_action: 'navigate_fx',
        cta_target: pair,
        group_key: 'missing_fx_rates_manual',
    };
}

/** The controller the header reads: its load error, its issues, and the reload a sync or a created pair asks for. */
function fakeController(issues: DataQualityIssue[]) {
    const handleSynced = vi.fn(async () => {}).mockName('handleSynced');
    const controller = {loadError: false, dataQualityIssues: issues, handleSynced} as unknown as RiskPanelController;
    return {controller, handleSynced};
}

/** The header mounted over one issue, with its folded banner unfolded: the chips and the button live inside it. */
async function mountHeader(issue: DataQualityIssue) {
    const {controller, handleSynced} = fakeController([issue]);
    render(RiskPanelHeader, {props: {controller, dateStart: '2026-01-01', dateEnd: '2026-06-30', targetCurrency: 'EUR', showActions: false}});
    await fireEvent.click(screen.getByTestId(BANNER_TOGGLE));
    return {handleSynced};
}

/** The sides the add-pair dialog is open on, or null while it is not: absent, or present and closed, read alike. */
function openDialog(): {base: string; quote: string} | null {
    const dialog = screen.queryByTestId(STUB);
    if (dialog === null || dialog.getAttribute('data-open') !== 'true') return null;
    return {base: dialog.getAttribute('data-base') ?? '', quote: dialog.getAttribute('data-quote') ?? ''};
}

/** `waitFor` without the page dump a timeout appends: the assertion's own message is the whole diagnosis here. */
function eventually(assertion: () => void): Promise<void> {
    return waitFor(assertion, {onTimeout: (error) => error});
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    mocks.goto.mockClear();
});

describe('RiskPanelHeader — an add_fx_pair issue opens the add-pair dialog', () => {
    it('opens the dialog on the pressed pair, and on the next pressed pair afterwards', async () => {
        await mountHeader(unroutedPairIssue(['EUR-USD', 'CHF-EUR']));
        expect(openDialog(), 'the dialog starts closed').toBeNull();

        await fireEvent.click(screen.getByTestId('data-quality-fx-pair-EUR-USD'));
        await eventually(() => expect(openDialog(), 'pressing the EUR-USD chip opens the add-pair dialog on EUR / USD').toEqual({base: 'EUR', quote: 'USD'}));

        // Close it the way the dialog does, then press the other chip: fresh sides, not the first pair's.
        await fireEvent.click(screen.getByTestId(STUB_CLOSE));
        await eventually(() => expect(openDialog(), 'the dialog closes when it reports it').toBeNull());

        await fireEvent.click(screen.getByTestId('data-quality-fx-pair-CHF-EUR'));
        await eventually(() => expect(openDialog(), 'pressing the CHF-EUR chip opens it on CHF / EUR, not on the first pair').toEqual({base: 'CHF', quote: 'EUR'}));
    });

    it('opens the dialog with nothing chosen when the issue names no pair', async () => {
        await mountHeader({...unroutedPairIssue([]), affected_fx_pairs: undefined});
        expect(openDialog(), 'the dialog starts closed').toBeNull();

        await fireEvent.click(screen.getByTestId(`data-quality-cta-${ADD_CODE}`));
        await eventually(() => expect(openDialog(), "the issue's one button opens the add-pair dialog empty").toEqual({base: '', quote: ''}));
    });

    it('reloads the answer once the dialog has created the pair, and again once its sync has settled', async () => {
        const {handleSynced} = await mountHeader(unroutedPairIssue(['EUR-USD']));
        await fireEvent.click(screen.getByTestId('data-quality-fx-pair-EUR-USD'));
        await eventually(() => expect(openDialog(), 'the dialog is open before it reports back').toEqual({base: 'EUR', quote: 'USD'}));
        expect(handleSynced, 'opening the dialog reloads nothing').not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId(STUB_CREATED));
        await eventually(() => expect(handleSynced, 'oncreated reloads, once').toHaveBeenCalledTimes(1));

        await fireEvent.click(screen.getByTestId(STUB_SYNCED));
        await eventually(() => expect(handleSynced, 'onsynced reloads again, once').toHaveBeenCalledTimes(2));
    });
});

describe('RiskPanelHeader — which issues leave for the FX page', () => {
    it('never navigates for an add_fx_pair chip: the dialog is the answer', async () => {
        await mountHeader(unroutedPairIssue(['EUR-USD', 'CHF-EUR']));

        await fireEvent.click(screen.getByTestId('data-quality-fx-pair-EUR-USD'));
        expect(mocks.goto, 'an add_fx_pair chip must not leave for the FX page').not.toHaveBeenCalled();
        // Presence barrier: the press reached its handler, and what it did is open the dialog.
        await eventually(() => expect(openDialog(), 'the press opened the dialog instead').toEqual({base: 'EUR', quote: 'USD'}));
    });

    it('never navigates for the add_fx_pair button of an issue with no pair', async () => {
        await mountHeader({...unroutedPairIssue([]), affected_fx_pairs: undefined});

        await fireEvent.click(screen.getByTestId(`data-quality-cta-${ADD_CODE}`));
        expect(mocks.goto, 'an add_fx_pair button must not leave for the FX page').not.toHaveBeenCalled();
        await eventually(() => expect(openDialog(), 'the press opened the dialog instead').toEqual({base: '', quote: ''}));
    });

    it("still opens the pair's own page for a navigate_fx chip, and opens no dialog", async () => {
        await mountHeader(manualPairIssue('EUR-USD'));

        await fireEvent.click(screen.getByTestId('data-quality-fx-pair-EUR-USD'));
        await eventually(() => expect(mocks.goto).toHaveBeenCalledWith('/fx/EUR-USD'));
        expect(mocks.goto).toHaveBeenCalledTimes(1);
        expect(openDialog(), 'a navigate_fx chip opens no add-pair dialog').toBeNull();
    });
});
