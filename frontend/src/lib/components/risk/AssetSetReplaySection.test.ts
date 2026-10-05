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
 * so, the way the Dashboard's L4 does through `discardedErrorCodes`. Three things this
 * section owes the reader are pinned here, all on the section itself:
 *
 *   1. **A discarded answer is disclosed.** Twice discarded, the replay leaves an empty
 *      form behind: without the sentence the reader cannot tell "the data moved under
 *      the answer, run it again" from "nothing to show". The sentence is the level's own
 *      error line, `risk.errors.answer_discarded`, under `data-code`. The complement is
 *      pinned too — a discard the re-ask recovered from is not a lost answer.
 *   2. **The warnings it keeps are in the reader's language.** A replay warning carries
 *      its catalogue key and its values (`message_i18n_key`, `message_params`); the
 *      section words it through them, like the Dashboard, rather than printing the
 *      backend's English `message`. Checked in the four shipped locales, on a warning the
 *      section keeps after D372: stale prices, which `service.py` attaches to any
 *      degraded answer, the replay's included.
 *   3. **What the block explains, the section does not repeat (D372).** The replay's
 *      exclusion and coverage warnings are shown in the block, beside the number they
 *      qualify, and a replay with nothing left to run is explained there too. So the
 *      mount hands the section `replaySectionView` of the answer: its reasons and errors
 *      leave those out, while its status line still says the replay is partial or
 *      unavailable. A refusal the block does not explain — a timeout — the section now
 *      discloses, where it used to disclose only a discarded answer.
 *
 * And one thing it owes the lab panel (decision B, the developer, 05/10/2026): **its
 * data-quality issues.** The lab draws one data-quality banner above its one notice, over the
 * issues of every section — the replay's included, since its controller holds answers no other
 * section holds: its own runs. So the section publishes `qualitySource()`, as the correlation
 * section and the levels do: no results and no labels — the replay keeps its own disclosure, as
 * the Dashboard's L4 does, so the notice reads none of it — and its controller's
 * `dataQualityIssues`. Pinned by the last block; written red first, against a section that
 * exports nothing.
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
 * `count` — but nothing here was read off a running backend. One warning rides a payload
 * of this scope that the engine would not send, on purpose: the coverage warning, which
 * it emits on weighted scopes only. It is there to prove the section reads
 * `replaySectionView` — both of the block's warnings — rather than a filter of its own
 * that knows one of them.
 *
 * Left elsewhere: the discard/re-ask rules themselves (`riskPanelController.test.ts`),
 * the helper's wording rules (`levels/levelHelpers.test.ts`), what `replaySectionView`
 * keeps and drops (`levels/l4/scenarioHelpers.test.ts`), the block itself
 * (`levels/l4/L4Replay.test.ts`), the source gate that every section passes a translator
 * (`warningTranslatorSites.test.ts`), how issues merge (`mergeQualityIssues`, in
 * `riskPanelController.test.ts`), and the page end to end, the banner included
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

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {assertEffectsRun, recordReads} from '$test/runes.svelte';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import type {RiskQueryRequest} from '$lib/risk/riskRequest';
import type {RiskDataQualityReport, RiskResultMetadata, RiskStressOutput} from '$lib/risk/riskTypes';
import {ANSWER_DISCARDED_CODE, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import type {AssetSetQualitySource} from './assetSetLevels';
import AssetSetReplaySection from './AssetSetReplaySection.svelte';
import {warningSentence} from './levels/warningSentence';

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

/** The exclusion warning of an asset the engine left out of the window, with the names `service.py` adds. The block shows it (D372). */
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
 * The strong warning — the replay describes only part of the portfolio. The block shows
 * it too (D372). Not emittable on this scope (see the header): it rides one answer to
 * prove the section reads `replaySectionView` rather than a filter of its own.
 */
const COVERAGE_WARNING: Warning = {
    code: 'historical_replay_mostly_excluded',
    message: 'Historical replay describes only 40% of the portfolio: the rest is excluded.',
    details: {excluded_weight_total: 0.6, threshold: 0.5},
    degrades_result: true,
    message_i18n_key: 'risk.warnings.historical_replay_mostly_excluded',
    message_params: {covered: 0.4},
};

/**
 * A warning the section keeps: stale prices, as `service.py::_data_quality_warnings`
 * attaches it to any degraded answer — the replay's included — with the names
 * `_with_warning_asset_names` adds.
 */
const STALE_KEY = 'risk.warnings.data_quality_stale_prices';
const STALE_PARAMS = {days: 7, names: 'Synthetic Holding A', count: 1};
const STALE_MESSAGE = 'Risk result uses incomplete or carried-forward source data.';
const STALE_WARNING: Warning = {
    code: 'data_quality_degraded',
    message: STALE_MESSAGE,
    details: {status: 'carried_forward', cause: 'stale_prices', asset_ids: [HOLDING_A]},
    degrades_result: true,
    message_i18n_key: STALE_KEY,
    message_params: STALE_PARAMS,
};

/**
 * An asset-set replay answer. The two impacts are declared against the tornado's sort
 * (worst first), so the rendered order is evidence that the output parsed and sorted —
 * the barrier every assertion about the answer stands on.
 *
 * By default the third holding was left out of the window (`omitted_from_replay`, as on
 * every unweighted scope) and the answer carries its exclusion warning; `excluded: false`
 * answers for all three, which leaves the answer `ok` unless a warning degrades it.
 */
function replayAnswer({excluded = true, warnings}: {excluded?: boolean; warnings?: Warning[]} = {}): RiskAnalyticResult {
    const answerWarnings = warnings ?? (excluded ? [EXCLUDED_WARNING] : []);
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
            excluded_count: excluded ? 1 : 0,
            excluded_assets: excluded ? [{asset_id: UNPRICED, reason: 'no_prices_in_window', weight: null, treatment: 'omitted_from_replay'}] : [],
            excluded_weight_total: 0,
            missing_history_policy: 'manual_proxy_or_exclude',
            composition_policy: 'current_buy_and_hold',
            proxy_series_usage: 'returns_only',
        },
    };
    const degraded = excluded || answerWarnings.some((warning) => warning?.degrades_result);
    return {instance_id: 'single-stress', analytic_code: 'stress', status: degraded ? 'partial' : 'ok', output, metadata, warnings: answerWarnings};
}

/** A replay that did not run: `unavailable` and no output, as `schemas/risk.py` demands of it. */
function refusal(code: 'execution_timeout' | 'insufficient_history', message: string, details?: Record<string, unknown>): RiskAnalyticResult {
    return {instance_id: 'single-stress', analytic_code: 'stress', status: 'unavailable', output: null, error: {code, message, ...(details === undefined ? {} : {details})}};
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
    return (await mountOpenKeepingInstance()).controller;
}

/** {@link mountOpen}, keeping the instance as well: `qualitySource()` is reached through it, as the panel reaches it through `bind:this`. */
async function mountOpenKeepingInstance() {
    const view = render(AssetSetReplaySection, {props: {assetIds: [HOLDING_A, HOLDING_B, UNPRICED], assetLabels: LABELS, dateStart: DATE_START, dateEnd: DATE_END, targetCurrency: 'EUR'}});
    expect(created.controllers, 'the section did not create a controller of its own').toHaveLength(1);
    const controller = created.controllers[0] as RiskPanelController;
    await waitFor(() => expect(controller.initialLoading, 'the base wave the mount fires never settled').toBe(false));

    await fireEvent.click(screen.getByTestId(`${TEST_ID}-toggle`));
    expect(screen.getByTestId(TEST_ID), 'the drawer did not open').toHaveAttribute('data-open', 'true');
    expect(screen.getByTestId('risk-replay-run')).toBeEnabled();
    return {view, controller};
}

async function runReplay(): Promise<void> {
    await fireEvent.click(screen.getByTestId('risk-replay-run'));
}

/**
 * The barrier on an answer: its bars in the tornado's order, so its output parsed and the
 * run finished. What the metadata says is the block's to show (`risk-replay-excluded`),
 * and the tests that are about it look there; the one-line audit this barrier used to read
 * is retired with D372.
 */
async function expectAnswerOnScreen(): Promise<void> {
    await waitFor(() =>
        expect(
            screen.getAllByTestId('risk-replay-tornado-row').map((row) => row.getAttribute('data-row-key')),
            'the replay answer never reached the screen: its output did not parse, or the run never finished',
        ).toEqual([`asset:${HOLDING_A}`, `asset:${HOLDING_B}`]),
    );
}

/** The run is over and the controller holds this answer: what the section says next is about it. */
async function expectRunSettled(controller: RiskPanelController, status: RiskAnalyticResult['status']): Promise<void> {
    await waitFor(() => expect(controller.replayResult?.status, 'the replay answer never reached the controller').toBe(status));
    expect(controller.replayLoading, 'the run is still in flight').toBe(false);
    expect(replay.asked, 'the replay was not asked exactly once').toHaveLength(1);
}

function errorCodes(): string[] {
    return screen.queryAllByTestId(`${TEST_ID}-error`).map((line) => line.getAttribute('data-code') ?? '');
}

function reasonsOnScreen(): string[] {
    return screen.queryAllByTestId(`${TEST_ID}-reason`).map((line) => normalize(line.textContent));
}

/** The section's status line: one entry, the replay's, in the state the answer carries. */
function expectStatusLine(state: 'partial' | 'unavailable'): void {
    const health = screen.getByTestId(`${TEST_ID}-health`);
    expect(health, 'the status line does not name the one replay result').toHaveAttribute('data-count', '1');
    expect(health, `the status line does not say the replay is ${state}`).toHaveTextContent(resolve(`risk.states.${state}`));
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

describe.each([...SUPPORTED_LOCALES])('AssetSetReplaySection — a keyed replay warning the section keeps, in %s', (locale) => {
    beforeAll(async () => {
        await setupI18n(locale);
    });

    it("is worded through its own key and values, like the Dashboard's, not in the backend's English", async () => {
        // The harness first: the sentence exists in this catalogue, takes the values the
        // warning carries, and cannot be mistaken for the backend's own.
        expect(typeof at(CATALOGUES[locale], STALE_KEY), `${STALE_KEY} is missing from ${locale}.json`).toBe('string');
        const expected = resolve(STALE_KEY, STALE_PARAMS);
        expect(expected, `${STALE_KEY} does not resolve`).not.toBe(STALE_KEY);
        expect(expected, `${STALE_KEY} still carries ICU braces once formatted with the warning's values`).not.toContain('{');
        expect(expected, "the warning's names never reached the formatter").toContain(STALE_PARAMS.names);
        expect(expected, "the catalogue sentence reads like the backend's: which one rendered could not be told").not.toBe(STALE_MESSAGE);

        // A replay that left nothing out and carries the one warning: the section's list is
        // then exactly that warning, before D372 and after it.
        replay.answers = [{items: [replayAnswer({excluded: false, warnings: [STALE_WARNING]})]}];
        await mountOpen();
        await runReplay();
        await expectAnswerOnScreen();

        expect(reasonsOnScreen(), `the section printed the backend's English sentence instead of the ${locale} one its key and values give`).toEqual([expected]);
    });
});

describe('AssetSetReplaySection — what the block explains, the section does not repeat (D372)', () => {
    beforeAll(async () => {
        await setupI18n('en');
    });

    it('leaves the exclusion and coverage sentences to the block, keeps every other warning, and still says the replay is partial', async () => {
        replay.answers = [{items: [replayAnswer({warnings: [COVERAGE_WARNING, EXCLUDED_WARNING, STALE_WARNING]})]}];
        const controller = await mountOpen();
        await runReplay();
        await expectAnswerOnScreen();

        // The premise: the controller holds the whole answer, the block's warnings included —
        // so whatever the section leaves out, it leaves out on purpose.
        expect(controller.replayResult?.warnings?.map((warning) => warning?.code)).toEqual(['historical_replay_mostly_excluded', 'historical_replay_assets_excluded', 'data_quality_degraded']);
        expectStatusLine('partial');

        // The section's reasons, read through the helper it words them with: the data
        // warning stays — the positive control that makes the absences below statements —
        // and the block's two are not repeated, in either wording.
        const translate = get(_);
        const reasons = reasonsOnScreen();
        expect(reasons, 'a warning the block does not show was dropped from the section').toContain(normalize(warningSentence(STALE_WARNING, translate)));
        for (const warning of [EXCLUDED_WARNING, COVERAGE_WARNING]) {
            expect(reasons, `the section repeats the ${warning.code} sentence the block shows beside the figure`).not.toContain(normalize(warningSentence(warning, translate)));
            expect(reasons, `the section prints the backend's English for ${warning.code}`).not.toContain(normalize(warning.message));
        }
        expect(reasons).toEqual([normalize(warningSentence(STALE_WARNING, translate))]);

        // …while the block, beside the bars, lists who was left out and why.
        const block = screen.getByTestId('risk-replay-excluded');
        expect(
            within(block)
                .getAllByTestId('risk-replay-excluded-group')
                .map((group) => group.getAttribute('data-reason')),
        ).toEqual(['no_prices_in_window']);
        expect(
            within(block)
                .getAllByTestId('risk-replay-excluded-asset')
                .map((item) => item.getAttribute('data-asset-id')),
        ).toEqual([String(UNPRICED)]);
    });

    it('discloses a refusal the block does not explain, such as a timeout', async () => {
        const key = 'risk.errors.execution_timeout';
        // The harness: the sentence exists and is not the fallback an unknown code gets.
        expect(resolve(key), `${key} does not resolve`).not.toBe(key);
        expect(resolve(key), `${key} reads like the unknown-error fallback: which line rendered could not be told`).not.toBe(resolve(UNKNOWN_ERROR_KEY));

        replay.answers = [{items: [refusal('execution_timeout', 'Risk analytic exceeded its time limit')]}];
        const controller = await mountOpen();
        await runReplay();
        await expectRunSettled(controller, 'unavailable');
        expectStatusLine('unavailable');

        expect(errorCodes(), 'the replay timed out and the section only says it is unavailable: the reader cannot tell a limit of the engine from a limit of the data').toEqual(['execution_timeout']);
        expect(normalize(screen.getByTestId(`${TEST_ID}-error`).textContent)).toBe(resolve(key));
    });

    it('explains a replay with nothing left to run in the block, not as an insufficient-history error of the section', async () => {
        replay.answers = [
            {
                items: [
                    refusal('insufficient_history', 'No asset in the replay scope covers the replay window', {
                        excluded_asset_ids: [HOLDING_A, HOLDING_B, UNPRICED],
                        excluded_assets: [
                            {asset_id: HOLDING_A, reason: 'starts_after_window_start', weight: null},
                            {asset_id: HOLDING_B, reason: 'starts_after_window_start', weight: null},
                            {asset_id: UNPRICED, reason: 'no_prices_in_window', weight: null},
                        ],
                    }),
                ],
            },
        ];
        const controller = await mountOpen();
        await runReplay();
        await expectRunSettled(controller, 'unavailable');

        // Barrier, and the block's half of the claim: the refusal was read as "nothing left".
        expect(screen.getByTestId('risk-replay-nothing')).toBeInTheDocument();
        expectStatusLine('unavailable');
        expect(errorCodes(), 'the section calls the window that left everything out an insufficient history, beside the block that already says what happened').toEqual([]);
    });
});

/**
 * ─── `qualitySource()`: what the lab panel reads through `bind:this` (decision B) ──────────────
 *
 * The panel merges every section's `qualitySource().issues` — the correlation section's, the
 * levels', then this one's — into the one data-quality banner it draws above its notice. This
 * section's are its controller's `dataQualityIssues`: Risk's `mergeQualityIssues` over every
 * result the controller holds, its base wave and its on-demand answers, so a replay run brings
 * its own. The export hands them over as the controller holds them, with no results and no
 * labels: the replay keeps its own disclosure, as the Dashboard's L4 does, and the notice must
 * not read it. And it stays reactive: the panel calls it inside a `$derived`, so an effect
 * reading it must re-run when a new answer brings other issues.
 *
 * The issues ride on the replay's own answer — the one this harness scripts — in the shapes
 * `service.py::_asset_issue` gives an asset set's report (D373). Invented, like everything here.
 */

type QualityIssue = NonNullable<RiskDataQualityReport['issues']>[number];

/** A holding whose prices went stale: the banner's row that offers the sync. */
const STALE_ISSUE: QualityIssue = {
    domain: 'asset',
    code: 'STALE_PRICE',
    severity: 'warning',
    message_i18n_key: 'dataQuality.stalePrice',
    message_params: {count: 1},
    count: 1,
    affected_asset_ids: [HOLDING_A],
    affected_asset_names: ['Synthetic Holding A'],
    cta_action: 'sync_asset_prices',
    cta_target: String(HOLDING_A),
    group_key: 'stale_price',
};

/** A holding with no price in the window: the banner's row that opens the asset. Another code, so a second answer is told from the first. */
const MISSING_ISSUE: QualityIssue = {
    domain: 'asset',
    code: 'MISSING_PRICE',
    severity: 'error',
    message_i18n_key: 'risk.quality.missingPrice',
    message_params: {count: 1},
    count: 1,
    affected_asset_ids: [UNPRICED],
    affected_asset_names: ['Synthetic Holding C'],
    cta_action: 'navigate_asset',
    cta_target: String(UNPRICED),
    group_key: 'missing_price',
};

/** A replay answer whose report carries these issues, as the backend attaches them to every result with a report. */
function withIssues(answer: RiskAnalyticResult, issues: QualityIssue[]): RiskAnalyticResult {
    return {...answer, data_quality: {issues, data_quality_status: issues.some((issue) => issue.severity === 'error') ? 'partial' : 'carried_forward'}};
}

/** The section's `qualitySource`, reached through the instance the harness mounted — as the panel reaches it, through `bind:this`. */
function qualitySourceOf(view: {component: unknown}): () => AssetSetQualitySource {
    const read = (view.component as {qualitySource?: unknown}).qualitySource;
    expect(typeof read, "the replay section exports no qualitySource(): the lab panel has nothing to read the replay's data-quality issues through bind:this, and its banner never lists them").toBe('function');
    return read as () => AssetSetQualitySource;
}

/** The latest value an effect read, or the error its read threw. */
function lastRead<T>(values: ReadonlyArray<T | Error>): T {
    const last = values.at(-1);
    if (last === undefined) throw new Error('the effect never read qualitySource()');
    if (last instanceof Error) throw last;
    return last;
}

/** The codes of a list of issues, in order: what each case states as its premise. */
function codesOf(issues: ReadonlyArray<{code: string}>): string[] {
    return issues.map((issue) => issue.code);
}

describe('AssetSetReplaySection — qualitySource(), what the lab panel reads through bind:this', () => {
    beforeAll(async () => {
        await setupI18n('en');
    });

    it("returns no results and no labels — the replay keeps its own disclosure — and the controller's data-quality issues", async () => {
        // A replay that left one holding out: partial, so a notice that read it would have something to say.
        replay.answers = [{items: [withIssues(replayAnswer(), [STALE_ISSUE])]}];
        const {view, controller} = await mountOpenKeepingInstance();
        await runReplay();
        await expectAnswerOnScreen();
        await expectRunSettled(controller, 'partial');
        // The premise: the controller holds the issue the replay's answer carried — so the list
        // compared below is not empty, and an export that lost the replay's issues would show.
        expect(codesOf(controller.dataQualityIssues), "premise: the controller does not hold the issue planted in the replay's answer").toEqual([STALE_ISSUE.code]);

        const source = qualitySourceOf(view)();
        expect(source.results, 'the replay keeps its own disclosure: the notice must read none of its results, partial as this one is').toEqual([]);
        expect(source.labels, 'no result handed over, nothing to label').toEqual({});
        expect(source.issues, "not the controller's data-quality issues: the lab's banner would miss the replay's").toEqual(controller.dataQualityIssues);
    });

    it('answered again with other issues, returns the new ones — to a plain call, and to an effect that reads it, as the panel does', async () => {
        replay.answers = [{items: [withIssues(replayAnswer({excluded: false}), [STALE_ISSUE])]}, {items: [withIssues(replayAnswer({excluded: false}), [MISSING_ISSUE])]}];
        const {view, controller} = await mountOpenKeepingInstance();
        await runReplay();
        await expectAnswerOnScreen();
        await waitFor(() => expect(codesOf(controller.dataQualityIssues), "premise: the first answer's issue never reached the controller").toEqual([STALE_ISSUE.code]));

        const source = qualitySourceOf(view);
        const reads = recordReads(() => source());
        try {
            expect(lastRead(reads.values).issues, 'the first answer, read by an effect').toEqual(controller.dataQualityIssues);

            // The reader runs the replay again, and this answer carries another issue.
            await runReplay();
            await waitFor(() => expect(codesOf(controller.dataQualityIssues), "premise: the second answer's issue never reached the controller").toEqual([MISSING_ISSUE.code]));
            expect(controller.replayLoading, 'the second run is still in flight').toBe(false);
            expect(replay.asked, 'the replay was not asked exactly twice').toHaveLength(2);

            expect(source().issues, "a plain call after the second answer still returns the first answer's issues").toEqual(controller.dataQualityIssues);
            await waitFor(() => expect(lastRead(reads.values).issues, "an effect reading qualitySource() after the second answer — it never re-ran, so the lab's banner would keep the first answer's issues").toEqual(controller.dataQualityIssues));
        } finally {
            reads.stop();
        }
    });
});
