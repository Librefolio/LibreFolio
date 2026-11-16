/**
 * currencyGraph at the catalogue size expected after wave 1 of lane 75 (FX central banks) — lots L2 and L2b.
 *
 * The route picker (`FxProviderSelect`) offers one route per path `findAllPaths` returns, at depth 4. L2 measured the
 * search on a synthetic catalogue the size of the real one after wave 1 (~180 currencies, ~550 edges): the unpruned
 * depth-4 walk took 120-200 ms for some pairs, even for USD→XU5, which has one chain. L2b prunes the walk with the steps
 * from each node to the target (a BFS on the undirected graph): a lower bound, so the result cannot change.
 *
 * What is asserted, and why:
 * - the fixture's shape (provider sizes, distinct currencies, MANUAL adding no edge, every pair reachable), so a wrong
 *   fixture cannot hide a wrong result;
 * - **the pruned search returns exactly the chains, in exactly the order, of the algorithm before L2b**, kept below as
 *   `findAllPathsUnpruned`, on a sample of pairs of today's catalogue (S0) and of wave 1 (S1, S2), and at depths 1-4;
 * - a very wide bound on the time (500 ms per pair, median of 5), against a gross regression only. The time is printed
 *   (`[scale]`), never held to a tight bound: a time assertion fails under load (lane 75, developer threshold
 *   rewritten in L2b — the number of chains is the catalogues', not the code's, so it is no threshold either).
 *
 * Run with the measurements printed:
 * `node_modules/.bin/vitest run --reporter=verbose --silent=false src/lib/utils/currency/currencyGraph.scale.test.ts`
 */
import type {MultiDirectedGraph} from 'graphology';
import {beforeAll, describe, expect, it} from 'vitest';

import {buildCurrencyGraph, findAllPaths, type ChainStep, type EdgeAttributes, type ProviderInfo} from './currencyGraph';
import {UNIVERSE, todayProviders, wave1PlusCbrProviders, wave1Providers} from './currencyGraph.scaleFixture';

type CurrencyGraph = ReturnType<typeof buildCurrencyGraph>;

/** Against a gross regression only: the pruned search runs in tens of ms at worst (L2b checkpoint). */
const MAX_MS = 500;

/** The depth the app searches at (`currencyGraphStore.findConversionPaths` default). */
const DEPTH = 4;

/**
 * `findAllPaths` as it was before L2b (lane 75): the same walk, both directions, simple paths, at most two uses of a
 * provider, results sorted by length — without the pruning. The reference the pruned search must equal.
 */
function findAllPathsUnpruned(graph: MultiDirectedGraph<Record<string, never>, EdgeAttributes>, source: string, target: string, maxDepth: number): ChainStep[][] {
    const valid: ChainStep[][] = [];
    if (!graph.hasNode(source) || !graph.hasNode(target) || source === target) return [];
    function dfs(node: string, path: ChainStep[], visited: Set<string>, uses: Map<string, number>): void {
        if (node === target) {
            valid.push([...path]);
            return;
        }
        if (path.length >= maxDepth) return;
        function tryEdge(neighbor: string, provider: string): void {
            if (visited.has(neighbor)) return;
            const used = uses.get(provider) ?? 0;
            if (used >= 2) return;
            path.push({from: node, to: neighbor, provider});
            visited.add(neighbor);
            uses.set(provider, used + 1);
            dfs(neighbor, path, visited, uses);
            path.pop();
            visited.delete(neighbor);
            if (used === 0) uses.delete(provider);
            else uses.set(provider, used);
        }
        graph.forEachOutboundEdge(node, (_key, attrs, _src, tgt) => tryEdge(tgt, attrs.provider));
        graph.forEachInboundEdge(node, (_key, attrs, src) => tryEdge(src, attrs.provider));
    }
    dfs(source, [], new Set([source]), new Map());
    valid.sort((a, b) => a.length - b.length);
    return valid;
}

/** Median wall time of `run`, in ms, over `runs` calls after one warm-up call. */
function medianMs(run: () => void, runs = 5): number {
    run();
    const samples: number[] = [];
    for (let i = 0; i < runs; i++) {
        const start = performance.now();
        run();
        samples.push(performance.now() - start);
    }
    samples.sort((a, b) => a - b);
    return samples[Math.floor(runs / 2)];
}

/**
 * Pairs of wave 1: the plan's three (EUR→NGN, KES→USD, CZK→JPY), two rare currencies covered only by the global
 * providers (XAF→XOF), the largest count (NOK→USD, two bases joined by every major), a base to a currency only BDI covers
 * (NOK→XT3) and a currency only BCB covers (USD→XU5: one chain, the slowest pair before L2b).
 */
const PAIRS: [string, string][] = [
    ['EUR', 'NGN'],
    ['KES', 'USD'],
    ['CZK', 'JPY'],
    ['XAF', 'XOF'],
    ['NOK', 'USD'],
    ['NOK', 'XT3'],
    ['USD', 'XU5'],
];

/** Today's pairs: the largest counts of today's graph (EUR→USD, CHF→NOK), a pair with no direct route, and BDT, which only NORGES covers. */
const TODAY_PAIRS: [string, string][] = [
    ['EUR', 'USD'],
    ['CZK', 'JPY'],
    ['NOK', 'USD'],
    ['EUR', 'BDT'],
    ['CHF', 'NOK'],
];

const SCENARIOS: [string, () => ProviderInfo[], [string, string][]][] = [
    ['scenario 0 — today', todayProviders, TODAY_PAIRS],
    ['scenario 1 — wave 1', wave1Providers, PAIRS],
    ['scenario 2 — wave 1 + CBR', wave1PlusCbrProviders, PAIRS],
];

describe('currencyGraph scale fixture — the catalogue after wave 1', () => {
    it('has the planned provider sizes and ~180 distinct currencies', () => {
        const sizes = Object.fromEntries(wave1PlusCbrProviders().map((p) => [p.code, p.target_currencies.length]));
        expect(sizes).toEqual({ECB: 45, FED: 23, BOE: 15, SNB: 25, BDI: 178, BCB: 156, NORGES: 40, NBU: 41, BOC: 24, MANUAL: 0, CBR: 54});
        const distinct = new Set(wave1PlusCbrProviders().flatMap((p) => [...p.base_currencies, ...p.target_currencies]));
        expect(distinct.size, 'every code of the universe is covered by some provider').toBe(UNIVERSE.length);
        expect(new Set(UNIVERSE).size, 'the universe has no duplicate code').toBe(UNIVERSE.length);
    });

    it('lets the two global providers share ~150 currencies', () => {
        const targets = (code: string) => new Set(wave1Providers().find((p) => p.code === code)!.target_currencies);
        const bdi = targets('BDI');
        const shared = [...targets('BCB')].filter((code) => bdi.has(code));
        expect(shared.length).toBe(152);
    });

    it('adds no edge for MANUAL, as the app does', () => {
        const withoutManual: ProviderInfo[] = wave1Providers().filter((p) => p.code !== 'MANUAL');
        const manualEverywhere: ProviderInfo = {code: 'MANUAL', name: 'Manual', base_currency: 'EUR', base_currencies: ['EUR'], target_currencies: [...UNIVERSE]};
        expect(buildCurrencyGraph([...withoutManual, manualEverywhere], [...UNIVERSE]).size).toBe(buildCurrencyGraph(withoutManual, [...UNIVERSE]).size);
    });

    it('reaches every measured pair in at most two steps', () => {
        const graph = buildCurrencyGraph(wave1Providers(), [...UNIVERSE]);
        for (const [source, target] of PAIRS) {
            expect(findAllPathsUnpruned(graph, source, target, 2).length, `${source}→${target}`).toBeGreaterThan(0);
        }
    });
});

for (const [scenario, providers, pairs] of SCENARIOS) {
    describe(`currencyGraph at scale, ${scenario}`, () => {
        let graph: CurrencyGraph;

        beforeAll(() => {
            const start = performance.now();
            graph = buildCurrencyGraph(providers(), [...UNIVERSE]);
            console.log(`[scale] ${scenario}: buildCurrencyGraph ${(performance.now() - start).toFixed(2)} ms, ${graph.order} currencies, ${graph.size} edges`);
        });

        it.each(pairs)(
            'finds from %s to %s at depth 4 the same chains as the unpruned search, well within the time bound',
            (source, target) => {
                const expected = findAllPathsUnpruned(graph, source, target, DEPTH);
                let paths = findAllPaths(graph, source, target, DEPTH);
                expect(paths, `${source}→${target}: the pruned search must return the same chains in the same order`).toEqual(expected);

                const ms = medianMs(() => {
                    paths = findAllPaths(graph, source, target, DEPTH);
                });
                const unprunedMs = medianMs(() => findAllPathsUnpruned(graph, source, target, DEPTH), 3);
                const byLength = [1, 2, 3, 4].map((length) => paths.filter((path) => path.length === length).length);
                const line = `${source}→${target}: ${paths.length} chains (by length 1/2/3/4: ${byLength.join('/')}), median ${ms.toFixed(1)} ms (unpruned ${unprunedMs.toFixed(1)} ms)`;
                console.log(`[scale] ${scenario}: ${line}`);
                expect(ms, line).toBeLessThan(MAX_MS);
            },
            60_000,
        );
    });
}

describe('currencyGraph pruning — the same chains at every depth', () => {
    it.each([1, 2, 3])('equals the unpruned search at depth %i on every wave-1 pair of the sample', (depth) => {
        const graph = buildCurrencyGraph(wave1Providers(), [...UNIVERSE]);
        for (const [source, target] of PAIRS) {
            expect(findAllPaths(graph, source, target, depth), `${source}→${target} at depth ${depth}`).toEqual(findAllPathsUnpruned(graph, source, target, depth));
        }
    });

    it('finds nothing for a currency no provider covers, and nothing from a currency to itself', () => {
        const graph = buildCurrencyGraph(wave1Providers(), [...UNIVERSE, 'XZZ']);
        expect(findAllPaths(graph, 'EUR', 'XZZ', DEPTH)).toEqual([]);
        expect(findAllPaths(graph, 'XZZ', 'EUR', DEPTH)).toEqual([]);
        expect(findAllPaths(graph, 'EUR', 'EUR', DEPTH)).toEqual([]);
    });
});
