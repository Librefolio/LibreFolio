/**
 * currencyGraph — the FX route picker's graph and its path search, as pure logic.
 *
 * `buildCurrencyGraph` turns the providers' capabilities (`GET /fx/providers`) into one directed edge per provider,
 * base → target, labelled with the provider's code. `findAllPaths` walks every edge both ways — outbound in the
 * provider's native direction, inbound backwards — and keeps the simple paths of at most `maxDepth` steps, each provider
 * on at most two of them. `FxProviderSelect` offers one route per path: a path that goes missing is a route the user
 * cannot pick, and a graph that refuses to build is a picker showing nothing but «Failed to load conversion routes».
 *
 * X-R75. The graph was graphology's default export, the plain `Graph` (mixed, `multi: false`), imported under the local
 * name `MultiDirectedGraph`. Two providers on the same direction — both base EUR, both serving NIO — are two parallel
 * edges, and the second one threw `UsageGraphError: … an edge linking "EUR" to "NIO" already exists`. The real catalogue
 * never had two providers on one base (ECB, FED, BOE and SNB each have their own), so nobody saw it; the provider
 * editor's E2E met it the first time it offered two providers for one pair. The graph is now the named
 * `MultiDirectedGraph` export (`multi: true`, `type: 'directed'`).
 *
 * A path is compared through the key the picker gives its route — every step's `from-to:provider`, joined with `|` —
 * and the paths of a search as the sorted list of those keys: a set, never a position, because the DFS follows
 * graphology's edge order, which is not a contract. Every graph is built here, so every count is this file's own.
 */
import {describe, expect, it} from 'vitest';

import {buildCurrencyGraph, findAllPaths, type ChainStep, type ProviderInfo} from './currencyGraph';

type CurrencyGraph = ReturnType<typeof buildCurrencyGraph>;

/** The currencies the backend lists (`GET /utilities/currencies`) in these fixtures: every one a node of the graph. */
const CODES = ['EUR', 'GBP', 'NIO', 'SRD', 'USD'];

/** A provider as `GET /fx/providers` describes it, reduced to what the graph reads: its code, its base, its targets. */
function provider(code: string, base: string, targets: string[]): ProviderInfo {
    return {code, name: `Fixture ${code}`, base_currency: base, base_currencies: [base], target_currencies: targets};
}

/** The key `FxProviderSelect` gives the route of a path. */
function routeKey(path: ChainStep[]): string {
    return path.map(({from, to, provider: code}) => `${from}-${to}:${code}`).join('|');
}

/** The routes the picker would offer from `source` to `target`, as the sorted list of their keys. */
function routeKeys(graph: CurrencyGraph, source: string, target: string): string[] {
    return findAllPaths(graph, source, target).map(routeKey).sort();
}

describe('currencyGraph — two providers on the same direction (X-R75)', () => {
    const sameDirection = [provider('P1', 'EUR', ['NIO']), provider('P2', 'EUR', ['NIO'])];

    it('builds the graph: the second provider on EUR→NIO is a second edge, not a refused one', () => {
        const build = () => buildCurrencyGraph(sameDirection, CODES);
        expect(build, 'two providers on EUR→NIO are two parallel edges, which only a multigraph holds').not.toThrow();
        expect(build().size, 'one edge per provider').toBe(2);
    });

    it('offers one direct route per provider, from EUR to NIO and, walked backwards, from NIO to EUR', () => {
        const graph = buildCurrencyGraph(sameDirection, CODES);
        expect(routeKeys(graph, 'EUR', 'NIO'), 'EUR→NIO, through either provider').toEqual(['EUR-NIO:P1', 'EUR-NIO:P2']);
        expect(routeKeys(graph, 'NIO', 'EUR'), 'NIO→EUR, both edges walked backwards').toEqual(['NIO-EUR:P1', 'NIO-EUR:P2']);
    });
});

describe('currencyGraph — what the search keeps and what it refuses (guards)', () => {
    it('opposite directions: P1 on EUR→NIO and P2 on NIO→EUR are both routes, either way', () => {
        const graph = buildCurrencyGraph([provider('P1', 'EUR', ['NIO']), provider('P2', 'NIO', ['EUR'])], CODES);
        expect(graph.size, 'one edge per provider').toBe(2);
        expect(routeKeys(graph, 'EUR', 'NIO'), 'P1 native, P2 walked backwards').toEqual(['EUR-NIO:P1', 'EUR-NIO:P2']);
        expect(routeKeys(graph, 'NIO', 'EUR'), 'P1 walked backwards, P2 native').toEqual(['NIO-EUR:P1', 'NIO-EUR:P2']);
    });

    it('the MANUAL sentinel adds no edge, not even on a direction a provider serves', () => {
        const graph = buildCurrencyGraph([provider('P1', 'EUR', ['NIO']), provider('MANUAL', 'EUR', ['NIO', 'SRD'])], CODES);
        expect(graph.size, 'P1’s edge alone').toBe(1);
        expect(routeKeys(graph, 'EUR', 'NIO'), 'the route P1 serves, and no MANUAL one beside it').toEqual(['EUR-NIO:P1']);
        expect(routeKeys(graph, 'EUR', 'SRD'), 'served by MANUAL alone: no route').toEqual([]);
    });

    it('a self-loop (base = target) adds no edge', () => {
        const graph = buildCurrencyGraph([provider('P1', 'EUR', ['EUR', 'NIO'])], CODES);
        expect(graph.size, 'EUR→NIO alone, not EUR→EUR').toBe(1);
        expect(routeKeys(graph, 'EUR', 'NIO')).toEqual(['EUR-NIO:P1']);
    });

    it('a currency the graph does not hold has no route, as source or as target; nor has one it holds that nobody serves', () => {
        const graph = buildCurrencyGraph([provider('P1', 'EUR', ['NIO'])], CODES);
        // Presence first: the graph answers for the pair it serves, so the empty answers below are refusals.
        expect(routeKeys(graph, 'EUR', 'NIO')).toEqual(['EUR-NIO:P1']);
        expect(graph.hasNode('JPY'), 'precondition: JPY is neither listed nor named by a provider').toBe(false);
        expect(findAllPaths(graph, 'JPY', 'NIO'), 'an unknown source').toEqual([]);
        expect(findAllPaths(graph, 'EUR', 'JPY'), 'an unknown target').toEqual([]);
        expect(findAllPaths(graph, 'EUR', 'SRD'), 'SRD is a node no provider serves').toEqual([]);
    });

    it('a two-step chain through an intermediate currency is found, each leg walked in its direction or backwards', () => {
        // P1 is native EUR→USD; P2 is native NIO→USD, so the second leg of EUR→NIO walks it backwards.
        const graph = buildCurrencyGraph([provider('P1', 'EUR', ['USD']), provider('P2', 'NIO', ['USD'])], CODES);
        expect(routeKeys(graph, 'EUR', 'NIO'), 'EUR→USD by P1, then USD→NIO by P2 backwards').toEqual(['EUR-USD:P1|USD-NIO:P2']);
        expect(routeKeys(graph, 'NIO', 'EUR'), 'NIO→USD by P2, then USD→EUR by P1 backwards').toEqual(['NIO-USD:P2|USD-EUR:P1']);
    });

    it('a provider serves at most two legs of one path (findAllPaths, constraint 2)', () => {
        // One provider on three legs, written as three entries with one code: the graph knows a provider only by the code
        // on its edges, and a single multi-base entry would add shortcuts (its targets apply to every one of its bases).
        const thrice = buildCurrencyGraph([provider('P1', 'EUR', ['USD']), provider('P1', 'USD', ['GBP']), provider('P1', 'GBP', ['NIO'])], CODES);
        expect(routeKeys(thrice, 'EUR', 'GBP'), 'two legs by P1: allowed').toEqual(['EUR-USD:P1|USD-GBP:P1']);
        expect(routeKeys(thrice, 'EUR', 'NIO'), 'the only path would take P1 a third time: refused').toEqual([]);
        const twice = buildCurrencyGraph([provider('P1', 'EUR', ['USD']), provider('P1', 'USD', ['GBP']), provider('P2', 'GBP', ['NIO'])], CODES);
        expect(routeKeys(twice, 'EUR', 'NIO'), 'P1 twice, then P2: found').toEqual(['EUR-USD:P1|USD-GBP:P1|GBP-NIO:P2']);
    });
});
