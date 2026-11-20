/**
 * currencyGraph — the route-search depth rule (lane 75, wave 2, lot L20b; plan `plan-phase02FxCentralBanksOndata2.prompt.md`,
 * developer decision Q6 of 19/11/2026). Written before the code: `ROUTE_DEPTH_CAP`, `hasChainOfLength`, `routeSearchDepth`,
 * `buildConfiguredCurrencyGraph` and `findRoutePaths` do not exist yet.
 *
 * The rule: levels are chain lengths 1..4. Find the first level with a chain, then search up to the next level that has
 * chains (direct → 2, first at 2 → 3, first at 3 → 4); with no next level within the cap, search up to the cap. The levels
 * come from the graph of the CONFIGURED providers, the chains shown from the FULL graph (an unconfigured provider's routes
 * still show, disabled). No configured chain up to the cap → the levels come from the full graph. No chain anywhere → 0.
 *
 * The oracle is the old search: `findAllPaths(full, s, t, 4)` filtered to the chosen depth, in the same order.
 */
import {describe, expect, it} from 'vitest';

import {ROUTE_DEPTH_CAP, buildConfiguredCurrencyGraph, buildCurrencyGraph, findAllPaths, findRoutePaths, hasChainOfLength, routeSearchDepth, type ChainStep, type ProviderInfo} from './currencyGraph';
import {UNIVERSE, todayProviders, wave2Providers} from './currencyGraph.scaleFixture';

/** A hand-built provider: one base, the given targets, `configured` left out unless given. */
function prov(code: string, base: string, targets: string[], configured?: boolean): ProviderInfo {
    return {code, name: `Test ${code}`, base_currency: base, base_currencies: [base], target_currencies: targets, ...(configured === undefined ? {} : {configured})};
}

const CODES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'Z'];

/** Both graphs of a provider list, as the store/worker build them. */
function graphsOf(providers: ProviderInfo[], codes: string[] = CODES) {
    return {full: buildCurrencyGraph(providers, codes), configured: buildConfiguredCurrencyGraph(providers, codes)};
}

/** The oracle: the old depth-4 search cut at `depth`, same order. */
function oracle(providers: ProviderInfo[], depth: number, source = 'A', target = 'Z'): ChainStep[][] {
    return findAllPaths(buildCurrencyGraph(providers, CODES), source, target, 4).filter((path) => path.length <= depth);
}

/** The depth the rule picks, and the routes it returns, for A→Z. */
function run(providers: ProviderInfo[], cap?: number) {
    const {full, configured} = graphsOf(providers);
    return {depth: routeSearchDepth(configured, full, 'A', 'Z', cap), paths: findRoutePaths(full, configured, 'A', 'Z', cap)};
}

/** Direct A→Z by P0. */
const DIRECT = prov('P0', 'A', ['Z']);
/** Two steps A→B→Z. */
const TWO = [prov('P1', 'A', ['B']), prov('P2', 'B', ['Z'])];
/** Three steps A→C→D→Z. */
const THREE = [prov('P3', 'A', ['C']), prov('P4', 'C', ['D']), prov('P5', 'D', ['Z'])];
/** Four steps A→E→F→G→Z. */
const FOUR = [prov('P6', 'A', ['E']), prov('P7', 'E', ['F']), prov('P8', 'F', ['G']), prov('P9', 'G', ['Z'])];

describe('ROUTE_DEPTH_CAP', () => {
    it('is 4', () => {
        expect(ROUTE_DEPTH_CAP).toBe(4);
    });
});

describe('routeSearchDepth and findRoutePaths — the rule on hand-built graphs', () => {
    it('direct + 2 steps → depth 2: the first level and the next one', () => {
        const providers = [DIRECT, ...TWO];
        const {depth, paths} = run(providers);
        expect(depth).toBe(2);
        expect(paths).toEqual(oracle(providers, 2));
        expect(paths.map((p) => p.length)).toEqual([1, 2]);
    });

    it('2 + 3 steps (no direct) → depth 3', () => {
        const providers = [...TWO, ...THREE];
        const {depth, paths} = run(providers);
        expect(depth).toBe(3);
        expect(paths).toEqual(oracle(providers, 3));
        expect(paths.map((p) => p.length)).toEqual([2, 3]);
    });

    it('3 + 4 steps → depth 4', () => {
        const providers = [...THREE, ...FOUR];
        const {depth, paths} = run(providers);
        expect(depth).toBe(4);
        expect(paths).toEqual(oracle(providers, 4));
        expect(paths.map((p) => p.length)).toEqual([3, 4]);
    });

    it('direct + 3 steps, none at 2 (a gap) → depth 3, the first full level after the gap', () => {
        const providers = [DIRECT, ...THREE];
        const {depth, paths} = run(providers);
        expect(depth).toBe(3);
        expect(paths).toEqual(oracle(providers, 3));
        expect(paths.map((p) => p.length)).toEqual([1, 3]);
    });

    it('direct + 4 steps, none at 2 or 3 → depth 4', () => {
        const providers = [DIRECT, ...FOUR];
        const {depth, paths} = run(providers);
        expect(depth).toBe(4);
        expect(paths).toEqual(oracle(providers, 4));
        expect(paths.map((p) => p.length)).toEqual([1, 4]);
    });

    it('direct + 2 + 3 + 4 steps → depth 2: the deeper levels are left out', () => {
        const providers = [DIRECT, ...TWO, ...THREE, ...FOUR];
        const {depth, paths} = run(providers);
        expect(depth).toBe(2);
        expect(paths).toEqual(oracle(providers, 2));
        expect(paths.every((p) => p.length <= 2)).toBe(true);
    });

    it.each([
        ['direct only', [DIRECT]],
        ['2 steps only', TWO],
        ['3 steps only', THREE],
        ['4 steps only', FOUR],
    ])('a single level (%s), no next level → the cap, 4', (_name, providers) => {
        const {depth, paths} = run(providers);
        expect(depth).toBe(4);
        expect(paths).toEqual(oracle(providers, 4));
        expect(paths.length).toBeGreaterThan(0);
    });

    it('with a lower cap, a next level beyond the cap is not reached: the search stops at the cap', () => {
        const providers = [DIRECT, ...THREE];
        const {depth, paths} = run(providers, 2);
        expect(depth).toBe(2);
        expect(paths).toEqual(oracle(providers, 2));
        expect(paths.map((p) => p.length)).toEqual([1]);
    });

    it('no chain at all → depth 0 and no routes (also for a currency absent from the graph)', () => {
        const providers = [prov('P1', 'A', ['B']), prov('P2', 'C', ['D'])];
        const {depth, paths} = run(providers);
        expect(depth).toBe(0);
        expect(paths).toEqual([]);

        const {full, configured} = graphsOf(providers);
        expect(routeSearchDepth(configured, full, 'A', 'NOPE')).toBe(0);
        expect(findRoutePaths(full, configured, 'A', 'NOPE')).toEqual([]);
    });

    it('a chain longer than the cap does not count: depth 0', () => {
        const five = [prov('Q1', 'A', ['B']), prov('Q2', 'B', ['C']), prov('Q3', 'C', ['D']), prov('Q4', 'D', ['E']), prov('Q5', 'E', ['Z'])];
        const {depth, paths} = run(five);
        expect(depth).toBe(0);
        expect(paths).toEqual([]);
    });
});

describe('routeSearchDepth and findRoutePaths — configured and unconfigured providers', () => {
    it('a direct route only through an UNCONFIGURED provider does not set the levels, but is still returned', () => {
        // Configured: 3 and 4 steps → depth 4 (a gap-from-direct reading of the full graph would give 3).
        const unconfiguredDirect = prov('OFF', 'A', ['Z'], false);
        const providers = [unconfiguredDirect, ...THREE, ...FOUR];
        const {full, configured} = graphsOf(providers);

        expect(routeSearchDepth(configured, full, 'A', 'Z')).toBe(4);
        const paths = findRoutePaths(full, configured, 'A', 'Z');
        expect(paths).toEqual(oracle(providers, 4));
        expect(
            paths.some((p) => p.length === 1 && p[0].provider === 'OFF'),
            'the unconfigured provider route is returned',
        ).toBe(true);
        expect(paths.map((p) => p.length)).toEqual([1, 3, 4]);
    });

    it('configured 2 + 3 steps and an unconfigured 4-step chain: the depth is 3, the 4-step chain is beyond it', () => {
        const off = [prov('OFF1', 'A', ['E'], false), prov('OFF2', 'E', ['F'], false), prov('OFF3', 'F', ['G'], false), prov('OFF4', 'G', ['Z'], false)];
        const providers = [...TWO, ...THREE, ...off];
        const {depth, paths} = run(providers);
        expect(depth).toBe(3);
        expect(paths).toEqual(oracle(providers, 3));
        expect(paths.every((p) => p.length <= 3)).toBe(true);
    });

    it('an unconfigured provider on the 2-step chain still shows it, the configured levels decide the depth', () => {
        // Configured: direct + 3 steps → depth 3. The 2-step chain goes through an unconfigured provider: shown, not counted.
        const providers = [DIRECT, ...THREE, prov('P1', 'A', ['B']), prov('OFF', 'B', ['Z'], false)];
        const {depth, paths} = run(providers);
        expect(depth).toBe(3);
        expect(paths).toEqual(oracle(providers, 3));
        expect(paths.map((p) => p.length)).toEqual([1, 2, 3]);
    });

    it('no configured chain at all → the levels come from the full graph', () => {
        const providers = [prov('OFF0', 'A', ['Z'], false), prov('OFF1', 'A', ['B'], false), prov('OFF2', 'B', ['Z'], false), prov('ON', 'C', ['D'])];
        const {full, configured} = graphsOf(providers);

        expect(findAllPaths(configured, 'A', 'Z', 4)).toEqual([]);
        expect(routeSearchDepth(configured, full, 'A', 'Z')).toBe(2);
        expect(findRoutePaths(full, configured, 'A', 'Z')).toEqual(oracle(providers, 2));
    });

    it('every provider unconfigured, a single level → the cap', () => {
        const providers = [prov('OFF0', 'A', ['Z'], false)];
        const {depth, paths} = run(providers);
        expect(depth).toBe(4);
        expect(paths).toEqual(oracle(providers, 4));
    });

    it('a provider without the `configured` field reads as configured', () => {
        const withField = [prov('P0', 'A', ['Z'], true), ...THREE];
        const without = [prov('P0', 'A', ['Z']), ...THREE];
        expect(run(without).depth).toBe(run(withField).depth);
        expect(run(without).depth).toBe(3);
    });
});

describe('buildConfiguredCurrencyGraph', () => {
    it('keeps only the providers with `configured !== false`, and the same nodes as the full graph', () => {
        const providers = [prov('ON', 'A', ['B']), prov('OFF', 'A', ['C'], false), prov('EXPLICIT', 'B', ['C'], true)];
        const configured = buildConfiguredCurrencyGraph(providers, CODES);
        const full = buildCurrencyGraph(providers, CODES);

        expect(configured.size).toBe(2);
        expect(full.size).toBe(3);
        expect(configured.order).toBe(full.order);
        expect(new Set(configured.mapEdges((_k, attrs) => attrs.provider))).toEqual(new Set(['ON', 'EXPLICIT']));
    });

    it('equals buildCurrencyGraph when every provider is configured', () => {
        const providers = [...TWO, ...THREE];
        const configured = buildConfiguredCurrencyGraph(providers, CODES);
        const full = buildCurrencyGraph(providers, CODES);
        expect(findAllPaths(configured, 'A', 'Z', 4)).toEqual(findAllPaths(full, 'A', 'Z', 4));
    });
});

describe('hasChainOfLength', () => {
    it('is true only for the exact lengths a chain exists at', () => {
        const {full} = graphsOf([DIRECT, ...TWO]);
        expect(hasChainOfLength(full, 'A', 'Z', 1)).toBe(true);
        expect(hasChainOfLength(full, 'A', 'Z', 2)).toBe(true);
        expect(hasChainOfLength(full, 'A', 'Z', 3)).toBe(false);
        expect(hasChainOfLength(full, 'A', 'Z', 4)).toBe(false);
    });

    it('walks an edge against its native direction, as findAllPaths does', () => {
        const {full} = graphsOf([prov('P1', 'Z', ['B']), prov('P2', 'B', ['A'])]);
        expect(hasChainOfLength(full, 'A', 'Z', 2)).toBe(true);
        expect(hasChainOfLength(full, 'A', 'Z', 1)).toBe(false);
    });

    it('respects the limit of two uses of one provider per chain', () => {
        // One provider covering A, B, C → Z: every 3-step chain A-B-C-Z or A-C-B-Z uses it three times.
        const one = prov('P', 'A', ['B', 'C', 'Z']);
        const onlyP = buildCurrencyGraph([{...one, base_currencies: ['A', 'B', 'C'], target_currencies: ['B', 'C', 'Z']}], CODES);
        expect(hasChainOfLength(onlyP, 'A', 'Z', 1)).toBe(true);
        expect(hasChainOfLength(onlyP, 'A', 'Z', 2)).toBe(true);
        expect(hasChainOfLength(onlyP, 'A', 'Z', 3), 'the only 3-step chains use P three times').toBe(false);
        expect(findAllPaths(onlyP, 'A', 'Z', 3).filter((p) => p.length === 3)).toEqual([]);

        // A second provider on one inner edge makes a 3-step chain with P twice: allowed.
        const withQ = buildCurrencyGraph([{...one, base_currencies: ['A', 'B', 'C'], target_currencies: ['B', 'C', 'Z']}, prov('Q', 'B', ['C'])], CODES);
        expect(hasChainOfLength(withQ, 'A', 'Z', 3)).toBe(true);
    });

    it('is false for a currency absent from the graph', () => {
        const {full} = graphsOf([DIRECT]);
        expect(hasChainOfLength(full, 'A', 'NOPE', 1)).toBe(false);
        expect(hasChainOfLength(full, 'NOPE', 'Z', 1)).toBe(false);
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// The scale fixture: the rule equals the brute force on every sampled pair (all providers configured, so both graphs are one)
// ---------------------------------------------------------------------------------------------------------------------

/** Pairs of scale scenario 0 (copied from `currencyGraph.scale.test.ts`, which does not export them). */
const TODAY_PAIRS: [string, string][] = [
    ['EUR', 'USD'],
    ['CZK', 'JPY'],
    ['NOK', 'USD'],
    ['EUR', 'BDT'],
    ['CHF', 'NOK'],
];

/** Pairs of scale scenario 3 (copied from `currencyGraph.scale.test.ts`). */
const WAVE2_PAIRS: [string, string][] = [
    ['EUR', 'NGN'],
    ['KES', 'USD'],
    ['CZK', 'JPY'],
    ['ZAR', 'KRW'],
    ['MXN', 'INR'],
    ['NOK', 'USD'],
    ['EUR', 'USD'],
];

/** S3 pairs whose depth-4 brute force builds ~200 000 chains: only their depth is asserted. */
const HEAVY_WAVE2_PAIRS = new Set(['EUR→USD', 'NOK→USD']);

/** The depth by brute force: the second distinct chain length, the cap when only one exists, 0 when none. */
function bruteForceDepth(paths: ChainStep[][]): number {
    const lengths = [...new Set(paths.map((p) => p.length))].sort((a, b) => a - b);
    if (lengths.length === 0) return 0;
    return lengths.length === 1 ? 4 : lengths[1];
}

describe('the rule on the scale fixture', () => {
    const scenarios: [string, () => ProviderInfo[], [string, string][]][] = [
        ['S0 — today', todayProviders, TODAY_PAIRS],
        ['S3 — wave 1 + wave 2', wave2Providers, WAVE2_PAIRS.filter(([s, t]) => !HEAVY_WAVE2_PAIRS.has(`${s}→${t}`))],
    ];

    for (const [scenario, providers, pairs] of scenarios) {
        it.each(pairs)(
            `${scenario}: %s→%s returns the old depth-4 chains cut at the depth the brute force finds`,
            (source, target) => {
                const g = buildCurrencyGraph(providers(), [...UNIVERSE]);
                const all = findAllPaths(g, source, target, 4);
                const depth = bruteForceDepth(all);

                expect(routeSearchDepth(g, g, source, target)).toBe(depth);
                expect(findRoutePaths(g, g, source, target)).toEqual(all.filter((p) => p.length <= depth));
            },
            60_000,
        );
    }

    it('S3: EUR→USD and NOK→USD stop at 2 steps, far from their ~200 000 chains at 4', () => {
        const g = buildCurrencyGraph(wave2Providers(), [...UNIVERSE]);
        expect(routeSearchDepth(g, g, 'EUR', 'USD')).toBe(2);
        expect(routeSearchDepth(g, g, 'NOK', 'USD')).toBe(2);
        expect(findRoutePaths(g, g, 'EUR', 'USD').every((p) => p.length <= 2)).toBe(true);
    }, 60_000);
});
