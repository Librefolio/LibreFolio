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
 * And a third, the uncovered card itself (developer's decision of 05/10/2026). Its caption
 * was one fixed sentence naming both things the share can hold, whatever it held: the
 * reader learnt what the number MIGHT be made of, never what it was. It now says so, off
 * `uncoveredWeight` — cash beside unpriced holdings, each with its share (`split`), only
 * unpriced holdings (`allUnpriced`), only cash (`allCash`) — and keeps the old sentence
 * where the split is unknown or there is nothing to split. The number does not move: it
 * stays the whole `cash_weight`. And the card's manual icon goes where that number is
 * explained, the excluded-weight section of the data-quality page.
 *
 * What is pinned, on testids and data attributes, plus catalogue sentences resolved from
 * the shipped catalogue through the component's own `$_`, never written down:
 *
 * - with a usable contribution, `ok` or `partial` alike — `okOutput` reads both, and
 *   `partial` is the ordinary answer of a portfolio with excluded holdings — the
 *   residual line publishes `cash_weight` as sent, and the card and its grid render;
 * - without one — none at all, or a stale output riding on an `unavailable` or
 *   `failed` result — the residual line, the card and the grid are not in the DOM.
 *   All three are removed with `{#if}`, so absent means "not rendered", never
 *   "not visible";
 * - a residual below 0.1 % reads the catalogue sentence filled with the share the rule
 *   prints for it, «0.04%», where the old wiring printed «0.0%»;
 * - the uncovered card is captioned with the sentence of the case its fixture is in, one
 *   case per branch, its number unchanged, and its manual icon opens the excluded-weight
 *   section;
 * - the three new captions ship in all four catalogues, `split` with exactly its two
 *   shares as arguments, and the four captions read differently in each.
 *
 * The three new keys arrive in the catalogue with the code that reads them: until then the
 * catalogue guard and the four cases that need them are red on the missing sentence, and
 * the cases also on the caption the card prints instead.
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
 * Mounted alone, with props only: no controller, no store, and no mock but `window.open`,
 * spied by the one case that clicks the manual icon.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

import {fireEvent, render, screen, setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
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
/** The caption under the uncovered card's number (`RiskMetricCard` publishes `{testId}-caption`). */
const UNCOVERED_CAPTION = 'risk-l2-card-uncovered-caption';
/** The uncovered card's manual icon (`RiskMetricCard` renders its `DocsLink` as `{testId}-docs`). */
const UNCOVERED_DOCS = 'risk-l2-card-uncovered-docs';

/** The caption the uncovered card always had: kept where the split is unknown, or there is nothing to split. */
const CAPTION_KEY = 'risk.levels.l2.uncovered.caption';
/** Cash beside holdings without a usable price series; `{cash}` and `{unpriced}` are their shares. */
const SPLIT_KEY = 'risk.levels.l2.uncovered.split';
/** Only holdings without a usable price series. */
const ALL_UNPRICED_KEY = 'risk.levels.l2.uncovered.allUnpriced';
/** Only cash. */
const ALL_CASH_KEY = 'risk.levels.l2.uncovered.allCash';
/** The four captions the uncovered card can carry: the caption is the one place it says which case it is in. */
const CAPTION_KEYS = [CAPTION_KEY, SPLIT_KEY, ALL_UNPRICED_KEY, ALL_CASH_KEY];
/** A pair to fill `split` with where only its difference from the other three captions is asked. */
const SAMPLE_SPLIT = {cash: '5.0%', unpriced: '2.0%'};
const CATALOGUES = {en, it: itCatalogue, fr, es};

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
 * A `risk_contribution` result, shaped like the API's, whose output states a cash share, the
 * part of it left without a usable price series, and nothing else to draw. The output rides
 * along on every status: on `unavailable` and `failed` it is the stale answer a result must
 * not be read from.
 *
 * `excludedWeight` defaults to 0, the value every fixture sent before the caption read it, so
 * the callers that pass none are unchanged: with it, the whole residual is cash.
 */
function contribution(status: ResultStatus, cashWeight = CASH_WEIGHT, excludedWeight = 0): RiskAnalyticResult {
    return {
        analytic_code: 'risk_contribution',
        instance_id: 'base-current_composition-risk_contribution',
        status,
        output: {kind: 'contribution', portfolio_volatility: 0.13, cash_weight: cashWeight, excluded_weight: excludedWeight, items: []},
    } as unknown as RiskAnalyticResult;
}

/**
 * A contribution that does not state `excluded_weight` at all. Written out rather than built by
 * `contribution()`, because the missing key is the subject: without it `uncoveredWeight` cannot
 * tell cash from unpriced holdings (`unpriced: null`), and the caption must not pretend it can.
 */
const WITHOUT_EXCLUDED_WEIGHT = {
    analytic_code: 'risk_contribution',
    instance_id: 'base-current_composition-risk_contribution',
    status: 'ok',
    output: {kind: 'contribution', portfolio_volatility: 0.13, cash_weight: CASH_WEIGHT, items: []},
} as unknown as RiskAnalyticResult;

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

/** The four captions as `$_` resolves them, `split` filled with a sample pair. */
function captionSentences(): string[] {
    return [resolve(CAPTION_KEY, {}), resolve(SPLIT_KEY, SAMPLE_SPLIT), resolve(ALL_UNPRICED_KEY, {}), resolve(ALL_CASH_KEY, {})];
}

/** The leaf behind a dotted key in one catalogue, read from the file on disk. */
function leaf(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
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

describe('L2Diversification — the uncovered card says what its share is made of', () => {
    // One case per branch of the caption, as `uncoveredWeight` splits the share: `unpriced` is the
    // `excluded_weight` sent, `cash` what is left of `cash_weight`. The shares are written down,
    // not computed: they are `formatShare` at L2's base of one decimal — 0.05 → 5.0%, 0.02 → 2.0%,
    // 0.0004 → 0.04%, 0.3 → 30.0% — and deriving them here would make each case re-derive the rule
    // it relies on. Tuples and `%s`, as above.
    //
    // The first four are red until the code lands with its three catalogue keys. The last two pin
    // the fallback to the caption the card always had, and are green today on purpose.
    const captionCases: [situation: string, result: RiskAnalyticResult, key: string, values: Record<string, string>][] = [
        // 0.306 − 0.306: the whole share is holdings without a usable price series.
        ['unpriced holdings and no cash', contribution('ok', 0.306, 0.306), ALL_UNPRICED_KEY, {}],
        // 0.05 − 0: the whole share is cash.
        ['cash and no unpriced holding', contribution('ok', 0.05, 0), ALL_CASH_KEY, {}],
        // 0.07 − 0.02 leaves 0.05 of cash beside 0.02 unpriced.
        ['cash beside unpriced holdings', contribution('ok', 0.07, 0.02), SPLIT_KEY, {cash: '5.0%', unpriced: '2.0%'}],
        // 0.3004 − 0.3 leaves 0.0004 of cash: below 1 %, where one decimal alone would print a zero.
        ['cash below 1 % beside unpriced holdings', contribution('ok', 0.3004, 0.3), SPLIT_KEY, {cash: '0.04%', unpriced: '30.0%'}],
        ['a split the payload does not state', WITHOUT_EXCLUDED_WEIGHT, CAPTION_KEY, {}],
        ['a share of zero', contribution('ok', 0, 0), CAPTION_KEY, {}],
    ];

    it.each(captionCases)('captions the uncovered card for %s', (situation, result, key, values) => {
        mountLevel(result);

        // Barrier: the big number did not move. The residual line still publishes the whole
        // `cash_weight` the fixture sent, so a red below is about the caption, never about which
        // share reached the card.
        const sent = String((result.output as unknown as {cash_weight: number}).cash_weight);
        expect(screen.getByTestId(UNCOVERED_LINE), `the residual line no longer publishes the whole cash_weight with ${situation}: the card's number moved`).toHaveAttribute('data-uncovered', sent);

        // Vacuity guards on the expected sentence, as in the residual case above, but soft: until
        // the keys land, a red names the missing sentence AND, through the comparison that still
        // runs below, the caption the card printed instead. A key that does not resolve echoes
        // itself; a `split` that lost a share would match whatever number the caption holds; two
        // captions alike would let the card print the wrong case and pass.
        const expected = resolve(key, values);
        expect.soft(expected, `${key} does not resolve: the catalogue is not loaded, or the key has not landed with the code yet`).not.toBe(key);
        for (const share of Object.values(values)) expect.soft(expected, `${key} does not interpolate ${share}: that share would go unsaid`).toContain(share);
        expect.soft(new Set(captionSentences()).size, 'two of the four captions resolve alike: the case the share is in could not be read off the card').toBe(4);

        // The subject.
        expect(normalize(screen.getByTestId(UNCOVERED_CAPTION).textContent), `the uncovered card is not captioned with ${key} for ${situation}`).toBe(expected);
    });

    // The manual icon goes where the number is explained: the excluded-weight section of the
    // data-quality page, no longer the risk-contribution page. `DocsLink` is a button, not an
    // anchor — it opens the page in a new tab through `window.open` — so there is no `href` to
    // read: the destination is the URL that call receives. Read by its end, because what precedes
    // the docs path is the locale's segment.
    it('opens the manual at the excluded-weight section of the data-quality page', async () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null);
        try {
            mountLevel(contribution('ok'));
            await fireEvent.click(screen.getByTestId(UNCOVERED_DOCS));

            // Barrier: the click opened one page, so a red below is about where it leads, never whether.
            expect(open, 'the manual icon of the uncovered card opened nothing').toHaveBeenCalledTimes(1);
            expect(String(open.mock.calls[0][0]), 'the manual icon of the uncovered card does not open the excluded-weight section of the data-quality page').toMatch(/data-quality\/#excluded-weight$/);
        } finally {
            open.mockRestore();
        }
    });
});

describe('L2Diversification — the catalogue the uncovered caption is worded with', () => {
    it.each(Object.keys(CATALOGUES) as (keyof typeof CATALOGUES)[])('ships the three captions that say what the share is made of in %s.json, and four different captions', (locale) => {
        const catalogue = CATALOGUES[locale];
        // Positive control: the caption the card always had, which this reader must find, so a red
        // below is a missing key and not a guard reading the wrong place.
        expect(typeof leaf(catalogue, CAPTION_KEY), `${CAPTION_KEY} is not a sentence in ${locale}.json: this guard reads the wrong place`).toBe('string');

        for (const key of [SPLIT_KEY, ALL_UNPRICED_KEY, ALL_CASH_KEY]) {
            const value = leaf(catalogue, key);
            expect(typeof value, `${key} is missing from ${locale}.json: the card would print its key`).toBe('string');
            expect(String(value).trim(), `${key} is empty in ${locale}.json`).not.toBe('');
        }

        // `split` takes exactly the two shares the card passes, each once: a missing one would leave
        // a share unsaid, an extra one would print raw. Nor any other brace: an ICU construct around
        // a share is not the plain argument the card fills.
        const split = String(leaf(catalogue, SPLIT_KEY));
        expect((split.match(/\{[^{}]*\}/g) ?? []).sort(), `${SPLIT_KEY} does not take exactly {cash} and {unpriced} in ${locale}.json`).toEqual(['{cash}', '{unpriced}']);
        expect(split.replace('{cash}', '').replace('{unpriced}', ''), `${SPLIT_KEY} carries a brace besides its two arguments in ${locale}.json`).not.toMatch(/[{}]/);
        for (const key of [ALL_UNPRICED_KEY, ALL_CASH_KEY]) expect(String(leaf(catalogue, key)), `${key} takes ICU arguments in ${locale}.json, but the card words it without values`).not.toMatch(/[{}]/);

        // Pairwise different: the caption is the one place the card says which case the share is in.
        expect(new Set(CAPTION_KEYS.map((key) => leaf(catalogue, key))).size, `two of the uncovered card's four captions read alike in ${locale}.json: the reader could not tell which case the share is in`).toBe(4);
    });
});
