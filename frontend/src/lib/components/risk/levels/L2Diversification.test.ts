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
 * And why it has a second subject, the share rule (developer's decision of 01/10/2026):
 * L2 words every share through `share()`, which hands it to `formatShare`, so that a
 * small share is never printed as zero. The rule is unit-tested on its own
 * (`shareFormat.test.ts`); L2's use of it was not. Reverting `share()` to the old
 * `formatPercent(fraction, {scale: 100, signed: false, digits: 1})` turned nothing red,
 * and the residual line would go back to calling 0.04 % of the portfolio «0.0%».
 *
 * What is pinned, on testids and data attributes, plus one sentence resolved from the
 * shipped catalogue through the component's own `$_`, never written down:
 *
 * - with a usable contribution, `ok` or `partial` alike — `okOutput` reads both, and
 *   `partial` is the ordinary answer of a portfolio with excluded holdings — the
 *   residual line publishes `cash_weight` as sent, and the card and its grid render;
 * - without one — none at all, or a stale output riding on an `unavailable` or
 *   `failed` result — the residual line, the card and the grid are not in the DOM.
 *   All three are removed with `{#if}`, so absent means "not rendered", never
 *   "not visible";
 * - a residual below 0.1 % reads the catalogue sentence filled with the share the rule
 *   prints for it, «0.04%», where the old wiring printed «0.0%».
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
import {get} from 'svelte/store';

import {render, screen, setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import L2Diversification from './L2Diversification.svelte';

/** The residual line under the cards; publishes the raw fraction in `data-uncovered`. */
const UNCOVERED_LINE = 'risk-l2-uncovered';
/** The catalogue sentence the residual line is worded with; its `{share}` is the formatted residual. */
const RESIDUAL_KEY = 'risk.levels.l2.uncovered.residual';
/** The card the residual was promoted to (`RiskMetricCard`'s root). */
const UNCOVERED_CARD = 'risk-l2-card-uncovered';
/** The grid of L2's cards (`RiskCardGrid`'s root): with no concentration pair, only the uncovered share opens it. */
const METRICS_GRID = 'risk-l2-metrics';

/** The cash share every fixture states unless a case asks for another: the whole residual, since nothing is excluded. */
const CASH_WEIGHT = 0.05;
/** A residual below 0.1 % of the portfolio, where one decimal — L2's base — would read zero. */
const SMALL_CASH_WEIGHT = 0.0004;
/**
 * `formatShare(SMALL_CASH_WEIGHT, 1)`: the share rule's output at L2's base of one decimal.
 * Written down, not computed: deriving it with `formatShare` would make the case re-derive
 * the rule it checks, and agree with that rule whatever it became.
 */
const SMALL_SHARE = '0.04%';

type ResultStatus = 'ok' | 'partial' | 'unavailable' | 'failed';

/**
 * A `risk_contribution` result, shaped like the API's, whose output states a cash share and
 * nothing else to draw. The output rides along on every status: on `unavailable` and
 * `failed` it is the stale answer a result must not be read from.
 */
function contribution(status: ResultStatus, cashWeight = CASH_WEIGHT): RiskAnalyticResult {
    return {
        analytic_code: 'risk_contribution',
        instance_id: 'base-current_composition-risk_contribution',
        status,
        output: {kind: 'contribution', portfolio_volatility: 0.13, cash_weight: cashWeight, excluded_weight: 0, items: []},
    } as unknown as RiskAnalyticResult;
}

function mountLevel(contributionResult: RiskAnalyticResult | null) {
    return render(L2Diversification, {props: {contributionResult, correlationResult: null}});
}

/** Whitespace between template nodes comes from the markup, not from the sentence. */
function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence formatted as the component formats it, through the same `$_` store. */
function resolve(key: string, values: Record<string, string>): string {
    return normalize(get(_)(key, {values}));
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

    // The rule's wiring, not the rule: `shareFormat.test.ts` owns the rule, this case owns
    // L2's use of it. With the barrier green, a red on the last assertion means the residual
    // line no longer words its share through `formatShare` at L2's one decimal.
    it('words a residual below 0.1 % through the share rule, never as a zero', () => {
        mountLevel(contribution('ok', SMALL_CASH_WEIGHT));

        // Barrier: the fraction this case sent reached the line untouched, so a red below is
        // about how the share is worded, never about which share arrived.
        const line = screen.getByTestId(UNCOVERED_LINE);
        expect(line, 'the residual line does not publish the cash_weight this case sent').toHaveAttribute('data-uncovered', String(SMALL_CASH_WEIGHT));

        // Vacuity guards on the expected sentence. A key that no longer resolves echoes itself,
        // and a sentence that lost its `{share}` matches whatever number the line holds: either
        // way the comparison below would pass under the old wiring too.
        const expected = resolve(RESIDUAL_KEY, {share: SMALL_SHARE});
        expect(expected, `${RESIDUAL_KEY} does not resolve: the catalogue is not loaded or the key is gone`).not.toBe(RESIDUAL_KEY);
        expect(expected, `${RESIDUAL_KEY} no longer interpolates its share: the number would go unread`).toContain(SMALL_SHARE);

        // The subject. The old wiring printed «0.0%» here: a share the data states, read as none.
        expect(normalize(line.textContent), `the residual line does not word ${SMALL_CASH_WEIGHT} as ${SMALL_SHARE}: it is no longer formatted through formatShare at one decimal`).toBe(expected);
    });
});
