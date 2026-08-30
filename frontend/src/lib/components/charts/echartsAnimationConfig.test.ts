/**
 * echartsAnimationConfig — unit test (Vitest, node).
 *
 * The shared animation constants and the `namedPoint` adapter that every 2D
 * chart feeds ECharts. Pure data, no DOM, so it stays in the node environment.
 * The constants are asserted for the two properties the diff-animation contract
 * actually depends on — `notMerge: false` and `replaceMerge: ['series']` — not
 * for every numeric easing value, which is a tunable, not a contract.
 */
import {describe, expect, it} from 'vitest';
import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS, namedPoint} from './echartsAnimationConfig';

describe('echartsAnimationConfig', () => {
    it('keeps the setOption flags that enable ECharts name-based diffing', () => {
        // Both are load-bearing: notMerge:false lets ECharts diff against the
        // previous state, replaceMerge:['series'] matches series by name.
        expect(CHART_SET_OPTION_OPTS.notMerge).toBe(false);
        expect(CHART_SET_OPTION_OPTS.replaceMerge).toEqual(['series']);
    });

    it('enables animation in the base config', () => {
        expect(CHART_ANIMATION_CONFIG.animation).toBe(true);
    });

    it('names a point by its date so ECharts can diff it across updates', () => {
        expect(namedPoint('2026-07-23', 42)).toEqual({name: '2026-07-23', value: ['2026-07-23', 42]});
    });

    it('preserves a null value (a gap) instead of coercing it', () => {
        const p = namedPoint('2026-07-24', null);
        expect(p.name).toBe('2026-07-24');
        expect(p.value[1]).toBeNull();
    });
});
