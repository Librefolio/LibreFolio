// @vitest-environment jsdom
/**
 * riskBenchmarkStore — read inside a component's `$derived`, as any page may read the shared benchmark.
 *
 * Svelte forbids writing state inside a derivation (`state_unsafe_mutation`), so the first read — the one that loads
 * the stored choice — must load it without writing a `$state`, and a later `set` must still reach the reader. The same
 * defect was found and fixed in `riskFreeRateStore` (RN-21); this store had it latent: its readers today read outside
 * any derivation.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

const backing = vi.hoisted(() => {
    const map = new Map<string, string>();
    Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        writable: true,
        value: {
            getItem: (key: string) => map.get(key) ?? null,
            setItem: (key: string, value: string) => void map.set(key, value),
            removeItem: (key: string) => void map.delete(key),
            clear: () => map.clear(),
        },
    });
    return map;
});

import {flushSync} from 'svelte';
import {cleanup, render, screen} from '$test/component';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import RiskBenchmarkProbe from '$test/harness/RiskBenchmarkProbe.svelte';
import {riskBenchmark} from './riskBenchmarkStore.svelte';

afterEach(() => cleanup());

describe('riskBenchmark — read inside a component’s $derived', () => {
    it('loads a stored choice on its first read, and follows a later set', () => {
        backing.set('lf_risk-benchmark-reads-u1_risk_benchmark_asset', '42');
        transitionClientSession('risk-benchmark-reads-u1');

        render(RiskBenchmarkProbe);
        expect(screen.getByTestId('risk-benchmark-probe').textContent).toBe('42');

        riskBenchmark.set(7);
        flushSync();
        expect(screen.getByTestId('risk-benchmark-probe').textContent).toBe('7');
    });
});
