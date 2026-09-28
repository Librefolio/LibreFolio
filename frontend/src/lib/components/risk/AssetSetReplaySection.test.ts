// @vitest-environment jsdom
//
// The docblock above is load-bearing: the section builds a real panel controller, and
// under the default `node` environment its `$effect`s never fire — no base wave, no
// run, and every "the section shows nothing" below would pass about a component that
// never did anything. `assertEffectsRun()` in the first test turns that into a message.
/**
 * AssetSetReplaySection — component test (Vitest + jsdom).
 *
 * The laboratory's historical replay (Asset Global, L4°) is the one on-demand analysis
 * of the page, and it runs beside the page's live price polling, which invalidates the
 * risk cache every 30 s: an answer in flight at that moment comes back from `queryRisk`
 * as `null` — *discarded*, not empty. The controller re-asks once, and when the second
 * answer is discarded too it records the fact (`discarded.replay`) for its host to say
 * so, the way the Dashboard's L4 does through `discardedErrorCodes`. Two things this
 * section owes the reader are pinned here, both on the section itself:
 *
 *   1. **A discarded answer is disclosed.** Twice discarded, the replay leaves an empty
 *      form behind: without the sentence the reader cannot tell "the data moved under
 *      the answer, run it again" from "nothing to show". The sentence is the level's own
 *      error line, `risk.errors.answer_discarded`, under `data-code`. The complement is
 *      pinned too — a discard the re-ask recovered from is not a lost answer.
 *   2. **Its warnings are in the reader's language.** A replay warning carries its
 *      catalogue key and its values (`message_i18n_key`, `message_params`); the section
 *      words it through them, like the Dashboard, rather than printing the backend's
 *      English `message`. Checked in the four shipped locales.
 *
 * **How a sentence is asserted without writing one down**: it is resolved from the
 * shipped catalogue through the same `$_` the component uses, with the same values
 * (the pattern of `L4Replay.test.ts` and `RiskResultFrame.test.ts`). The harness case
 * and each locale's first lines guard the ways that could go vacuous: a key missing
 * from the catalogue (svelte-i18n echoes the id back), and sentences that read alike
 * (then "which branch rendered" has no answer).
 *
 * **The controller is the real one, observed, never replaced**: its factory is wrapped
 * only to hand this file the instance the section created, so each red can first say
 * "the controller did record the discard" before saying "and the section did not tell".
 * `queryRisk` is scripted per question — the base wave the mount fires is answered
 * empty and never counted; the replay is answered from a queue, and a question past
 * the queue's end throws rather than inventing an answer.
 *
 * ⚠️ Every figure and name below is invented. The payloads are shaped to be emittable —
 * an asset-set replay (`stress.py::_historical`: no aggregate return on an unweighted
 * scope, the excluded asset `omitted_from_replay`), and the exclusion warning as
 * `_replay_exclusion_warning` builds it and `service.py` completes it with `names` and
 * `count` — but nothing here was read off a running backend.
 *
 * Left elsewhere: the discard/re-ask rules themselves (`riskPanelController.test.ts`),
 * the helper's wording rules (`levels/levelHelpers.test.ts`), the source gate that every
 * section passes a translator (`warningTranslatorSites.test.ts`), and the page end to end
 * (`e2e/portfolio/risk-lab.spec.ts`).
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());
/** Every controller the section creates, in order. Observed, never replaced. */
const created = vi.hoisted(() => ({controllers: [] as unknown[]}));

vi.mock('$lib/stores/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/risk/riskStore.svelte')>();
    return {
        ...actual,
        fetchRiskCatalog,
        fetchRiskScenarioCatalog,
        queryRisk,
        invalidateRisk,
        // Capability gating is the panel's business, not this section's: stubbed open so
        // the replay is always asked, and the subject stays what the section does with it.
        hasRiskCapability: () => true,
    };
});

vi.mock('$lib/stores/risk/riskPanelController.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/risk/riskPanelController.svelte')>();
    return {
        ...actual,
        createRiskPanelController: (...args: Parameters<typeof actual.createRiskPanelController>) => {
            const controller = actual.createRiskPanelController(...args);
            created.controllers.push(controller);
            return controller;
        },
    };
});

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import type {RiskQueryRequest} from '$lib/risk/riskRequest';
import type {RiskResultMetadata, RiskStressOutput} from '$lib/risk/riskTypes';
import {ANSWER_DISCARDED_CODE, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import AssetSetReplaySection from './AssetSetReplaySection.svelte';

type Warning = NonNullable<RiskAnalyticResult['warnings']>[number];
type ReplayAnswer = {items: RiskAnalyticResult[]} | null;

const TEST_ID = 'risk-replay-section';
const DISCARDED_KEY = `risk.errors.${ANSWER_DISCARDED_CODE}`;
const UNKNOWN_ERROR_KEY = 'risk.errors.unknown';

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

// Invented: a window and a laboratory selection of three, the third unpriced in the window.
const DATE_START = '2020-02-01';
const DATE_END = '2020-03-31';
const HOLDING_A = 7;
const HOLDING_B = 9;
const UNPRICED = 11;
const LABELS: ReadonlyMap<number, string> = new Map([
    [HOLDING_A, 'Synthetic Holding A'],
    [HOLDING_B, 'Synthetic Holding B'],
    [UNPRICED, 'Synthetic Holding C'],
]);

/** The exclusion warning of an asset the engine left out of the window, with the names `service.py` adds. */
const EXCLUDED_KEY = 'risk.warnings.historical_replay_excluded_no_prices';
const EXCLUDED_PARAMS = {treatment: 'omitted_from_replay', names: 'Synthetic Holding C', count: 1};
const EXCLUDED_MESSAGE = 'Historical replay excluded assets with no prices in the replay window.';
const EXCLUDED_WARNING: Warning = {
    code: 'historical_replay_assets_excluded',
    message: EXCLUDED_MESSAGE,
    details: {asset_ids: [UNPRICED], treatment: 'omitted_from_replay', reason: 'no_prices_in_window'},
    degrades_result: true,
    message_i18n_key: EXCLUDED_KEY,
    message_params: EXCLUDED_PARAMS,
};

/**
 * An asset-set replay answer. The two impacts are declared against the tornado's sort
 * (worst first), so the rendered order is evidence that the output parsed and sorted —
 * the barrier every assertion about the answer stands on.
 */
function replayAnswer(): RiskAnalyticResult {
    const output: RiskStressOutput = {
        kind: 'stress',
        method: 'historical_replay',
        portfolio_return: null,
        impact_amount: null,
        replay_range: {start: DATE_START, end: DATE_END},
        impacts: [
            {asset_id: HOLDING_B, weight: null, shock_return: 0.05, contribution_return: null, impact_amount: null, metadata_fallback: false},
            {asset_id: HOLDING_A, weight: null, shock_return: -0.2, contribution_return: null, impact_amount: null, metadata_fallback: false},
        ],
    };
    const metadata: RiskResultMetadata = {
        analyzed_range: {start: DATE_START, end: DATE_END},
        frequency: 'daily',
        n_observations: 42,
        calendar_days: 60,
        coverage: 1,
        currency: 'EUR',
        scope: 'asset_set',
        return_basis: 'current_composition_backtest',
        algorithm_version: 'test-asset-set-replay',
        computed_at: '2026-01-05T10:00:00+00:00',
        historical_replay_audit: {
            proxy_count: 0,
            proxy_assets: [],
            excluded_count: 1,
            excluded_assets: [{asset_id: UNPRICED, reason: 'no_prices_in_window', weight: null, treatment: 'omitted_from_replay'}],
            excluded_weight_total: 0,
            missing_history_policy: 'manual_proxy_or_exclude',
            composition_policy: 'current_buy_and_hold',
            proxy_series_usage: 'returns_only',
        },
    };
    return {instance_id: 'single-stress', analytic_code: 'stress', status: 'partial', output, metadata, warnings: [EXCLUDED_WARNING]};
}

/** The replay's answers, in the order it is asked; and every replay question, as asked. */
const replay = {answers: [] as ReplayAnswer[], asked: [] as RiskQueryRequest[]};

/** `L4Replay` asks a `stress` named `single-stress` with a historical method; the base wave never does. */
function isReplayQuestion(request: RiskQueryRequest): boolean {
    const [analytic] = request.analytics;
    const parameters = analytic?.parameters as Record<string, unknown> | undefined;
    return analytic?.instance_id === 'single-stress' && parameters?.method === 'historical_replay';
}

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence formatted as the component formats it: `$_`, with the same values. */
function resolve(key: string, values?: Record<string, string | number>): string {
    return normalize(get(_)(key, values === undefined ? undefined : {values}));
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/**
 * The section mounted and opened, with its replay form on screen, and the controller it made.
 *
 * Two barriers before anything is run: the controller's first wave has settled — so no
 * late base answer can land in the middle of a replay — and the drawer is open, which is
 * the only way the reader reaches the Run button.
 */
async function mountOpen(): Promise<RiskPanelController> {
    render(AssetSetReplaySection, {props: {assetIds: [HOLDING_A, HOLDING_B, UNPRICED], assetLabels: LABELS, dateStart: DATE_START, dateEnd: DATE_END, targetCurrency: 'EUR'}});
    expect(created.controllers, 'the section did not create a controller of its own').toHaveLength(1);
    const controller = created.controllers[0] as RiskPanelController;
    await waitFor(() => expect(controller.initialLoading, 'the base wave the mount fires never settled').toBe(false));

    await fireEvent.click(screen.getByTestId(`${TEST_ID}-toggle`));
    expect(screen.getByTestId(TEST_ID), 'the drawer did not open').toHaveAttribute('data-open', 'true');
    expect(screen.getByTestId('risk-replay-run')).toBeEnabled();
    return controller;
}

async function runReplay(): Promise<void> {
    await fireEvent.click(screen.getByTestId('risk-replay-run'));
}

/** The barrier on an answer: its bars in the tornado's order, and its audit parsed from the metadata. */
async function expectAnswerOnScreen(): Promise<void> {
    await waitFor(() =>
        expect(
            screen.getAllByTestId('risk-replay-tornado-row').map((row) => row.getAttribute('data-row-key')),
            'the replay answer never reached the screen: its output did not parse, or the run never finished',
        ).toEqual([`asset:${HOLDING_A}`, `asset:${HOLDING_B}`]),
    );
    expect(screen.getByTestId('risk-replay-audit'), 'the answer metadata did not parse').toHaveAttribute('data-excluded-count', '1');
}

function errorCodes(): string[] {
    return screen.queryAllByTestId(`${TEST_ID}-error`).map((line) => line.getAttribute('data-code') ?? '');
}

beforeEach(() => {
    created.controllers.length = 0;
    replay.answers = [];
    replay.asked = [];
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
    invalidateRisk.mockReset();
    queryRisk.mockReset().mockImplementation(async (request: RiskQueryRequest) => {
        if (!isReplayQuestion(request)) return {items: []};
        replay.asked.push(request);
        if (replay.answers.length === 0) throw new Error('the replay was asked more often than this test scripted');
        return replay.answers.shift() ?? null;
    });
});

describe('AssetSetReplaySection — the harness itself', () => {
    beforeAll(async () => {
        await setupI18n('en');
    });

    it('runs effects, and the discarded-answer sentence is in the catalogue and reads unlike the fallback', () => {
        expect(() => assertEffectsRun()).not.toThrow();

        expect(typeof at(en, DISCARDED_KEY), `${DISCARDED_KEY} is missing from en.json`).toBe('string');
        const discarded = resolve(DISCARDED_KEY);
        expect(discarded, `${DISCARDED_KEY} does not resolve: the catalogue is not loaded`).not.toBe(DISCARDED_KEY);
        // The level words an unknown code with this fallback: were the two alike, a line
        // rendered for some other code could pass for the one under test.
        expect(discarded, 'the discarded sentence reads like the unknown-error fallback: which line rendered could not be told').not.toBe(resolve(UNKNOWN_ERROR_KEY));
    });
});

describe('AssetSetReplaySection — a replay answer discarded twice running', () => {
    beforeAll(async () => {
        await setupI18n('en');
    });

    it('is disclosed on the section, in the words of risk.errors.answer_discarded', async () => {
        replay.answers = [null, null];
        const controller = await mountOpen();
        await runReplay();

        // The premise, first: the question was asked, re-asked once, and the controller
        // recorded the discard. What follows is then about the section alone.
        await waitFor(() => expect(controller.discarded.replay, 'the controller never recorded the discard: the path under test did not run').toBe(true));
        expect(replay.asked, 'the replay was not asked and then re-asked exactly once').toHaveLength(2);
        expect(controller.replayLoading, 'the run is still in flight').toBe(false);

        expect(errorCodes(), 'the controller recorded a discarded replay answer and the section says nothing: an empty form reads as "nothing to show", not as "run it again"').toEqual([ANSWER_DISCARDED_CODE]);
        expect(normalize(screen.getByTestId(`${TEST_ID}-error`).textContent)).toBe(resolve(DISCARDED_KEY));
    });

    it('is not claimed for a discard the re-ask recovered from', async () => {
        replay.answers = [null, {items: [replayAnswer()]}];
        const controller = await mountOpen();
        await runReplay();

        // Barrier: the re-ask's answer is on screen, so the absence below is a statement.
        await expectAnswerOnScreen();
        expect(replay.asked, 'the first answer was not discarded and re-asked: this case would be about an ordinary run').toHaveLength(2);
        expect(controller.discarded.replay).toBe(false);
        expect(errorCodes(), 'a discard the re-ask recovered from is disclosed as a lost answer').toEqual([]);
    });
});

describe.each([...SUPPORTED_LOCALES])('AssetSetReplaySection — a keyed replay warning, in %s', (locale) => {
    beforeAll(async () => {
        await setupI18n(locale);
    });

    it("is worded through its own key and values, like the Dashboard's, not in the backend's English", async () => {
        // The harness first: the sentence exists in this catalogue, takes the values the
        // warning carries, and cannot be mistaken for the backend's own.
        expect(typeof at(CATALOGUES[locale], EXCLUDED_KEY), `${EXCLUDED_KEY} is missing from ${locale}.json`).toBe('string');
        const expected = resolve(EXCLUDED_KEY, EXCLUDED_PARAMS);
        expect(expected, `${EXCLUDED_KEY} does not resolve`).not.toBe(EXCLUDED_KEY);
        expect(expected, `${EXCLUDED_KEY} still carries ICU braces once formatted with the warning's values`).not.toContain('{');
        expect(expected, "the warning's names never reached the formatter").toContain(EXCLUDED_PARAMS.names);
        expect(expected, "the catalogue sentence reads like the backend's: which one rendered could not be told").not.toBe(EXCLUDED_MESSAGE);

        replay.answers = [{items: [replayAnswer()]}];
        await mountOpen();
        await runReplay();
        await expectAnswerOnScreen();

        const reasons = screen.getAllByTestId(`${TEST_ID}-reason`).map((line) => normalize(line.textContent));
        expect(reasons, `the section printed the backend's English sentence instead of the ${locale} one its key and values give`).toEqual([expected]);
    });
});
