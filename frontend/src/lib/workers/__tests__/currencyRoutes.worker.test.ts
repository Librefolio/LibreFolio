/**
 * currencyRoutes.worker — `computeRoutePaths`, the pure half of the route-search Web Worker (lane 75, wave 2, lot L20b;
 * plan `plan-phase02FxCentralBanksOndata2.prompt.md`, decision Q6 of 19/11/2026). Written before the module exists.
 *
 * The worker gets plain data (providers, currency codes, the pair, the cap), rebuilds both graphs on every call and
 * answers with `findRoutePaths`. Tested here in-thread; the `self.onmessage` glue is the same shape as
 * `priceProcessing.worker.ts`.
 */
import {describe, expect, it} from 'vitest';

import {buildConfiguredCurrencyGraph, buildCurrencyGraph, findRoutePaths, routeSearchDepth, type ProviderInfo} from '$lib/utils/currency/currencyGraph';
import {UNIVERSE, todayProviders} from '$lib/utils/currency/currencyGraph.scaleFixture';
import {computeRoutePaths, type CurrencyRoutesRequest} from '../currencyRoutes.worker';

function prov(code: string, base: string, targets: string[], configured?: boolean): ProviderInfo {
    return {code, name: `Test ${code}`, base_currency: base, base_currencies: [base], target_currencies: targets, ...(configured === undefined ? {} : {configured})};
}

const CODES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'Z'];

describe('computeRoutePaths', () => {
    it('equals findRoutePaths on the two graphs built from the same plain data', () => {
        const providers = [prov('P0', 'A', ['Z']), prov('P1', 'A', ['B']), prov('P2', 'B', ['Z']), prov('P3', 'A', ['C']), prov('P4', 'C', ['D']), prov('P5', 'D', ['Z'])];
        const request: CurrencyRoutesRequest = {providers, currencyCodes: CODES, source: 'A', target: 'Z'};

        const full = buildCurrencyGraph(providers, CODES);
        const configured = buildConfiguredCurrencyGraph(providers, CODES);
        expect(computeRoutePaths(request)).toEqual(findRoutePaths(full, configured, 'A', 'Z'));
        expect(computeRoutePaths(request).map((p) => p.length)).toEqual([1, 2]);
    });

    it('equals findRoutePaths on a catalogue of the real size (today, EUR→BDT)', () => {
        const providers = todayProviders();
        const request: CurrencyRoutesRequest = {providers, currencyCodes: [...UNIVERSE], source: 'EUR', target: 'BDT'};

        const full = buildCurrencyGraph(providers, [...UNIVERSE]);
        const configured = buildConfiguredCurrencyGraph(providers, [...UNIVERSE]);
        expect(computeRoutePaths(request)).toEqual(findRoutePaths(full, configured, 'EUR', 'BDT'));
    });

    it('reads `configured`: an unconfigured provider changes the depth, not the presence of its routes', () => {
        // Configured: 3 and 4 steps. Unconfigured: a direct route.
        const chain = (names: string[]) => names.slice(0, -1).map((from, i) => prov(`C${names.join('')}${i}`, from, [names[i + 1]]));
        const base = [...chain(['A', 'C', 'D', 'Z']), ...chain(['A', 'E', 'F', 'G', 'Z'])];
        const withOff = [prov('OFF', 'A', ['Z'], false), ...base];
        const withOn = [prov('OFF', 'A', ['Z'], true), ...base];

        const off = computeRoutePaths({providers: withOff, currencyCodes: CODES, source: 'A', target: 'Z'});
        const on = computeRoutePaths({providers: withOn, currencyCodes: CODES, source: 'A', target: 'Z'});

        expect(
            off.some((p) => p.length === 1 && p[0].provider === 'OFF'),
            'the unconfigured provider route is returned',
        ).toBe(true);
        expect(off.map((p) => p.length)).toEqual([1, 3, 4]);
        // Configured, the direct route sets the first level and the 3-step chains the next one: the 4-step chain drops out.
        expect(on.map((p) => p.length)).toEqual([1, 3]);
    });

    it('passes the cap on', () => {
        const providers = [prov('P0', 'A', ['Z']), prov('P3', 'A', ['C']), prov('P4', 'C', ['D']), prov('P5', 'D', ['Z'])];
        const full = buildCurrencyGraph(providers, CODES);
        const configured = buildConfiguredCurrencyGraph(providers, CODES);

        const capped = computeRoutePaths({providers, currencyCodes: CODES, source: 'A', target: 'Z', cap: 2});
        expect(routeSearchDepth(configured, full, 'A', 'Z', 2)).toBe(2);
        expect(capped).toEqual(findRoutePaths(full, configured, 'A', 'Z', 2));
        expect(capped.map((p) => p.length)).toEqual([1]);
    });

    it('answers [] when no chain exists', () => {
        const providers = [prov('P1', 'A', ['B'])];
        expect(computeRoutePaths({providers, currencyCodes: CODES, source: 'A', target: 'Z'})).toEqual([]);
    });

    it('does not mutate the request', () => {
        const providers = [prov('P0', 'A', ['Z']), prov('P1', 'A', ['B']), prov('P2', 'B', ['Z'], false)];
        const request: CurrencyRoutesRequest = {providers, currencyCodes: [...CODES], source: 'A', target: 'Z', cap: 3};
        const before = structuredClone(request);

        computeRoutePaths(request);
        computeRoutePaths(request);

        expect(request).toEqual(before);
    });

    it('builds the graphs on every call: a changed provider list changes the answer', () => {
        const one = [prov('P0', 'A', ['Z'])];
        const two = [prov('P0', 'A', ['Z']), prov('P1', 'A', ['B']), prov('P2', 'B', ['Z'])];
        expect(computeRoutePaths({providers: one, currencyCodes: CODES, source: 'A', target: 'Z'}).map((p) => p.length)).toEqual([1]);
        expect(computeRoutePaths({providers: two, currencyCodes: CODES, source: 'A', target: 'Z'}).map((p) => p.length)).toEqual([1, 2]);
    });
});
