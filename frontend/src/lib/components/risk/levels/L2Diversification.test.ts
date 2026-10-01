// @vitest-environment jsdom
/**
 * L2Diversification — the share of the portfolio the risk model does not speak for,
 * present or absent (Vitest + jsdom).
 *
 * Why this file exists (mutation M16): replacing
 * `uncoveredWeight(contributionResult)?.total ?? null` with `?? 0` survived all 13 E2E
 * tests it was run against, and the mutant is not equivalent. With no usable
 * contribution, `?? 0` draws the uncovered card and publishes `data-uncovered="0"`: a
 * false "nothing uncovered", the very reassurance the comment above that line forbids.
 * The E2E reach L2 with a usable contribution only, so none of them could see an
 * absence, and no test pinned it.
 *
 * What is pinned, on testids and data attributes only (no translated sentence):
 *
 * - with a usable contribution, `ok` or `partial` alike — `okOutput` reads both, and
 *   `partial` is the ordinary answer of a portfolio with excluded holdings — the
 *   residual line publishes `cash_weight` as sent, and the card and its grid render;
 * - without one — none at all, or a stale output riding on an `unavailable` or
 *   `failed` result — the residual line, the card and the grid are not in the DOM.
 *   All three are removed with `{#if}`, so absent means "not rendered", never
 *   "not visible".
 *
 * The present cases are also the positive control of the selectors: the three testids
 * the absent cases look for are found there, so no absence below can be the product of
 * a misspelt testid.
 *
 * The fixtures keep out what this round does not cover: no correlation (the matrix, and
 * ECharts with it, renders only for one), no items (the divergence bars render only for
 * a row), and no `effective_number_of_assets` / `diversification_ratio`, so the
 * uncovered card is the only card the present cases can draw.
 *
 * Mounted alone, with props only: no controller, no store, no mock.
 */
import {beforeAll, describe, expect, it} from 'vitest';

import {render, screen, setupI18n} from '$test/component';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import L2Diversification from './L2Diversification.svelte';

/** The residual line under the cards; publishes the raw fraction in `data-uncovered`. */
const UNCOVERED_LINE = 'risk-l2-uncovered';
/** The card the residual was promoted to (`RiskMetricCard`'s root). */
const UNCOVERED_CARD = 'risk-l2-card-uncovered';
/** The grid of L2's cards (`RiskCardGrid`'s root): with no concentration pair, only the uncovered share opens it. */
const METRICS_GRID = 'risk-l2-metrics';

/** The cash share every fixture states: the whole residual, since nothing is excluded. */
const CASH_WEIGHT = 0.05;

type ResultStatus = 'ok' | 'partial' | 'unavailable' | 'failed';

/**
 * A `risk_contribution` result, shaped like the API's, whose output states a cash share and
 * nothing else to draw. The output rides along on every status: on `unavailable` and
 * `failed` it is the stale answer a result must not be read from.
 */
function contribution(status: ResultStatus): RiskAnalyticResult {
    return {
        analytic_code: 'risk_contribution',
        instance_id: 'base-current_composition-risk_contribution',
        status,
        output: {kind: 'contribution', portfolio_volatility: 0.13, cash_weight: CASH_WEIGHT, excluded_weight: 0, items: []},
    } as unknown as RiskAnalyticResult;
}

function mountLevel(contributionResult: RiskAnalyticResult | null) {
    return render(L2Diversification, {props: {contributionResult, correlationResult: null}});
}

beforeAll(async () => {
    await setupI18n();
});

describe('L2Diversification — the share the risk model does not speak for', () => {
    it.each(['ok', 'partial'] as const)('publishes the share and draws its card on a contribution that came back %s', (status) => {
        mountLevel(contribution(status));

        expect(screen.getByTestId(UNCOVERED_LINE), `the residual line does not publish the cash_weight the ${status} contribution sent`).toHaveAttribute('data-uncovered', String(CASH_WEIGHT));
        expect(screen.queryByTestId(UNCOVERED_CARD), `the uncovered card is missing on a ${status} contribution that states its share`).not.toBeNull();
        expect(screen.queryByTestId(METRICS_GRID), `the card grid is missing on a ${status} contribution that states its share`).not.toBeNull();
    });

    // Tuples and `%s`, not objects and `$situation`: the latter truncates a title at 40 characters.
    const unusable: [situation: string, result: RiskAnalyticResult | null][] = [
        ['no contribution at all', null],
        ['an unavailable contribution still carrying a stale output', contribution('unavailable')],
        ['a failed contribution still carrying a stale output', contribution('failed')],
    ];

    it.each(unusable)('says nothing about the share when there is %s', (situation, result) => {
        mountLevel(result);

        // Barrier: the level mounted and took its body branch — the one the residual line, the card
        // and the grid live in — and not the loading skeleton. `risk-l2-empty` is drawn there whenever
        // there is no row, so it is on screen without a contribution as well as with one.
        expect(screen.queryByTestId('risk-l2'), 'the level did not mount: the absences below would be about nothing').not.toBeNull();
        expect(screen.queryByTestId('risk-l2-empty'), 'the level did not render its body: the absences below would be about a skeleton').not.toBeNull();

        // Soft, so a regression names every block that leaked, not only the first.
        expect.soft(screen.queryByTestId(UNCOVERED_LINE), `the residual line was drawn with ${situation}: a share nobody measured reads as "nothing uncovered"`).toBeNull();
        expect.soft(screen.queryByTestId(UNCOVERED_CARD), `the uncovered card was drawn with ${situation}: a share nobody measured reads as "nothing uncovered"`).toBeNull();
        expect.soft(screen.queryByTestId(METRICS_GRID), `the card grid was drawn with ${situation}: with no concentration pair, only a share nobody measured could open it`).toBeNull();
    });
});
