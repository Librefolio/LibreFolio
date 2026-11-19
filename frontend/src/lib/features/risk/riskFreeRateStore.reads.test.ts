// @vitest-environment jsdom
/**
 * riskFreeRateStore — the first read happens where a page reads it: inside a component's `$derived` (RN-21).
 *
 * `RiskLevelsPanel` and the lab read the shared rate as `$derived(riskFreeRate.percent)`. Svelte forbids writing state
 * inside a derivation, so the first read — the one that loads the stored value — must load it without writing a
 * `$state`, and a later `set` must still reach the reader.
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
import RiskFreeRateProbe from '$test/harness/RiskFreeRateProbe.svelte';
import {riskFreeRate} from './riskFreeRateStore.svelte';

afterEach(() => cleanup());

describe('riskFreeRate — read inside a component’s $derived', () => {
    it('loads a stored value on its first read, and follows a later set', () => {
        backing.set('lf_risk-free-reads-u1_risk_free_rate_percent', '2.5');
        transitionClientSession('risk-free-reads-u1');

        render(RiskFreeRateProbe);
        expect(screen.getByTestId('risk-free-rate-probe').textContent).toBe('2.5');

        riskFreeRate.set(3);
        flushSync();
        expect(screen.getByTestId('risk-free-rate-probe').textContent).toBe('3');
    });
});
