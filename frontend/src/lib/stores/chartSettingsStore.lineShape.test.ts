import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$app/environment', () => ({browser: true}));

import {transitionClientSession} from '$lib/stores/app/clientSession';
import {DEFAULT_CHART_SETTINGS, getGlobalLineShape, getGlobalSettings, getSettingsForPair, resolveLineShape, setGlobalLineShape, setGlobalSettings, setPairSettings, type ChartSettings} from './chartSettingsStore.svelte';

/** Y2 FB-3: the shape of the lines is one global setting that every chart follows, and one chart may override. */

let backing = new Map<string, string>();
let userSeq = 0;

function freshUser(): string {
    const userId = `line-shape-u${++userSeq}`;
    transitionClientSession(userId);
    return userId;
}

function storedPayload(userId: string): Record<string, unknown> | null {
    const raw = backing.get(`lf_${userId}_chartSettingsStore`);
    return raw === undefined ? null : JSON.parse(raw);
}

beforeEach(() => {
    backing = new Map();
    Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        writable: true,
        value: {
            getItem: (key: string) => backing.get(key) ?? null,
            setItem: (key: string, value: string) => void backing.set(key, value),
            removeItem: (key: string) => void backing.delete(key),
            clear: () => backing.clear(),
        },
    });
    vi.useFakeTimers();
});

afterEach(() => {
    vi.useRealTimers();
});

describe('chartSettingsStore — the line shape (Y2 FB-3)', () => {
    it('opens on segments, and no chart carries a shape of its own', () => {
        freshUser();
        expect(getGlobalLineShape()).toBe('segments');
        expect(resolveLineShape(getSettingsForPair('asset-1', 'assets'))).toBe('segments');
        expect(DEFAULT_CHART_SETTINGS.lineShape).toBeUndefined();
    });

    it('a global choice reaches every chart, the ones with settings of their own too', () => {
        freshUser();
        setPairSettings('asset-5', {...DEFAULT_CHART_SETTINGS, areaFill: false});
        setGlobalLineShape('spline');
        expect(getGlobalLineShape()).toBe('spline');
        expect(resolveLineShape(getSettingsForPair('asset-5', 'assets'))).toBe('spline');
        expect(resolveLineShape(getGlobalSettings('fx'))).toBe('spline');
        expect(getSettingsForPair('asset-5', 'assets').areaFill, 'nothing else of the chart is touched').toBe(false);
    });

    it('a chart that chose its own shape keeps it until the global choice is made again', () => {
        freshUser();
        setPairSettings('EUR-USD', {...DEFAULT_CHART_SETTINGS, lineShape: 'steps'});
        expect(resolveLineShape(getSettingsForPair('EUR-USD', 'fx'))).toBe('steps');
        expect(resolveLineShape(getSettingsForPair('USD-GBP', 'fx'))).toBe('segments');
        setGlobalLineShape('spline');
        expect(resolveLineShape(getSettingsForPair('EUR-USD', 'fx')), 'the global choice is the newer word').toBe('spline');
    });

    it('is written to storage and read back by the next session of the same account', () => {
        const user = freshUser();
        setGlobalLineShape('steps');
        setPairSettings('asset-9', {...DEFAULT_CHART_SETTINGS, lineShape: 'spline'});
        vi.advanceTimersByTime(300);
        expect(storedPayload(user)?.lineShape).toBe('steps');

        transitionClientSession(null);
        transitionClientSession(user);
        expect(getGlobalLineShape()).toBe('steps');
        expect(getSettingsForPair('asset-9', 'assets').lineShape).toBe('spline');
    });

    it('reads a shape it does not know as segments, global and per chart', () => {
        const user = `line-shape-garbage-${++userSeq}`;
        const override: Partial<ChartSettings> & Record<string, unknown> = {...DEFAULT_CHART_SETTINGS, lineShape: 'wavy' as never};
        backing.set(`lf_${user}_chartSettingsStore`, JSON.stringify({version: 3, lineShape: 'wavy', globalSettings: DEFAULT_CHART_SETTINGS, pairOverrides: [['asset-3', override]]}));
        transitionClientSession(user);
        expect(getGlobalLineShape()).toBe('segments');
        expect(resolveLineShape(getSettingsForPair('asset-3', 'assets'))).toBe('segments');
    });

    it('saving the global settings of a scope does not change the shape', () => {
        freshUser();
        setGlobalLineShape('spline');
        setGlobalSettings({...DEFAULT_CHART_SETTINGS, gridLines: false}, 'assets');
        expect(getGlobalLineShape()).toBe('spline');
        expect(resolveLineShape(getGlobalSettings('assets'))).toBe('spline');
    });
});
