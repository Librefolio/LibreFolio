import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$app/environment', () => ({browser: true}));

// The line shape is read from the user settings store (lot UIP). A writable-based fake stands in for it: the real one
// pulls `globalSettings`, which reads localStorage at module init. The fake's `updateUiPreference` applies the same pure
// helper the real one uses, so the chart store reads back what it wrote; it is a spy, so the calls are pinned too.
vi.mock('$lib/stores/app/settings', async () => {
    const {writable, get} = await import('svelte/store');
    const {withUiPreference} = await import('$lib/stores/app/uiPreferences');
    const store = writable<unknown>(null);
    const fallback = {language: 'en', base_currency: 'EUR', avatar_url: null, ui_preferences: {}, ui_preference_defaults: {theme: 'auto', chart_line_shape: 'segments'}};
    return {
        userSettings: {
            subscribe: store.subscribe,
            set: store.set,
            updateUiPreference: vi.fn(async (key: string, value: unknown) => {
                const current = get(store);
                if (current) store.set(withUiPreference(current as never, key as never, value as never));
                return true;
            }),
        },
        isFallbackUserSettings: (s: unknown) => s === fallback,
        __fallback: fallback,
    };
});

import * as settingsModule from '$lib/stores/app/settings';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import type {UserSettings} from '$lib/types';
import {DEFAULT_CHART_SETTINGS, clearGlobalLineShape, getGlobalLineShape, getGlobalSettings, getSettingsForPair, lineShapeFollowsGlobal, resolveLineShape, setGlobalLineShape, setGlobalSettings, setPairSettings, type ChartSettings} from './chartSettingsStore.svelte';

/** Y2 FB-3 + lot UIP: the shape of the lines is one global setting (kept by the server) that every chart follows, and one chart may override. */

const fake = settingsModule.userSettings as unknown as {set: (s: unknown) => void; updateUiPreference: ReturnType<typeof vi.fn>};
const fallbackSettings = (settingsModule as unknown as {__fallback: UserSettings}).__fallback;

let backing = new Map<string, string>();
let userSeq = 0;

function freshUser(): string {
    const userId = `line-shape-u${++userSeq}`;
    transitionClientSession(userId);
    return userId;
}

/** Server settings: the user's own keys and the administrator's defaults. */
function serverSettings(own: UserSettings['ui_preferences'] = {}, defaults: UserSettings['ui_preference_defaults'] = {theme: 'auto', chart_line_shape: 'segments'}): UserSettings {
    return {language: 'en', base_currency: 'EUR', avatar_url: null, ui_preferences: own, ui_preference_defaults: defaults};
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
    fake.set(serverSettings());
    fake.updateUiPreference.mockClear();
});

afterEach(() => {
    vi.useRealTimers();
});

describe('chartSettingsStore — the line shape (Y2 FB-3, lot UIP)', () => {
    it('opens on segments, and no chart carries a shape of its own', () => {
        freshUser();
        expect(getGlobalLineShape()).toBe('segments');
        expect(resolveLineShape(getSettingsForPair('asset-1', 'assets'))).toBe('segments');
        expect(DEFAULT_CHART_SETTINGS.lineShape).toBeUndefined();
    });

    it('follows the effective shape of the store: the default while the user has no own key, the own key otherwise', () => {
        freshUser();
        fake.set(serverSettings({}, {theme: 'auto', chart_line_shape: 'steps'}));
        expect(getGlobalLineShape(), 'the global default').toBe('steps');
        expect(lineShapeFollowsGlobal()).toBe(true);

        fake.set(serverSettings({chart_line_shape: 'spline'}, {theme: 'auto', chart_line_shape: 'steps'}));
        expect(getGlobalLineShape(), 'the own key wins').toBe('spline');
        expect(lineShapeFollowsGlobal()).toBe(false);
    });

    it('reads a shape it does not know as segments', () => {
        freshUser();
        fake.set(serverSettings({chart_line_shape: 'wavy' as never}));
        expect(getGlobalLineShape()).toBe('segments');
    });

    it('a global choice is written as the interface preference chart_line_shape and reaches every chart', async () => {
        freshUser();
        setPairSettings('asset-5', {...DEFAULT_CHART_SETTINGS, areaFill: false});
        expect(await setGlobalLineShape('spline')).toBe(true);
        expect(fake.updateUiPreference).toHaveBeenCalledExactlyOnceWith('chart_line_shape', 'spline');
        expect(getGlobalLineShape()).toBe('spline');
        expect(lineShapeFollowsGlobal()).toBe(false);
        expect(resolveLineShape(getSettingsForPair('asset-5', 'assets'))).toBe('spline');
        expect(resolveLineShape(getGlobalSettings('fx'))).toBe('spline');
        expect(getSettingsForPair('asset-5', 'assets').areaFill, 'nothing else of the chart is touched').toBe(false);
    });

    it('a chart that chose its own shape keeps it until the global choice is made again', () => {
        freshUser();
        setPairSettings('EUR-USD', {...DEFAULT_CHART_SETTINGS, lineShape: 'steps'});
        expect(resolveLineShape(getSettingsForPair('EUR-USD', 'fx'))).toBe('steps');
        expect(resolveLineShape(getSettingsForPair('USD-GBP', 'fx'))).toBe('segments');
        void setGlobalLineShape('spline');
        expect(resolveLineShape(getSettingsForPair('EUR-USD', 'fx')), 'the global choice is the newer word: the override is cleared').toBe('spline');
        expect(getSettingsForPair('EUR-USD', 'fx').lineShape).toBeUndefined();
    });

    it('clearing the global shape sends null, so the administrator default applies again', async () => {
        freshUser();
        fake.set(serverSettings({chart_line_shape: 'spline'}, {theme: 'auto', chart_line_shape: 'steps'}));
        expect(await clearGlobalLineShape()).toBe(true);
        expect(fake.updateUiPreference).toHaveBeenCalledExactlyOnceWith('chart_line_shape', null);
        expect(lineShapeFollowsGlobal()).toBe(true);
        expect(getGlobalLineShape()).toBe('steps');
    });

    it('refuses a shape it does not know, without writing', async () => {
        freshUser();
        expect(await setGlobalLineShape('wavy' as never)).toBe(false);
        expect(fake.updateUiPreference).not.toHaveBeenCalled();
    });

    it('stores the per-chart overrides only: the persisted payload carries no lineShape of its own', () => {
        const user = freshUser();
        void setGlobalLineShape('steps');
        setPairSettings('asset-9', {...DEFAULT_CHART_SETTINGS, lineShape: 'spline'});
        vi.advanceTimersByTime(300);
        expect(storedPayload(user), 'premise: something was stored').not.toBeNull();
        expect(storedPayload(user)).not.toHaveProperty('lineShape');

        transitionClientSession(null);
        transitionClientSession(user);
        expect(getGlobalLineShape(), 'read from the store, not from storage').toBe('steps');
        expect(getSettingsForPair('asset-9', 'assets').lineShape).toBe('spline');
    });

    it('reads a per-chart shape it does not know as segments, and a legacy global one it does not know is not adopted', () => {
        const user = `line-shape-garbage-${++userSeq}`;
        const override: Partial<ChartSettings> & Record<string, unknown> = {...DEFAULT_CHART_SETTINGS, lineShape: 'wavy' as never};
        backing.set(`lf_${user}_chartSettingsStore`, JSON.stringify({version: 3, lineShape: 'wavy', globalSettings: DEFAULT_CHART_SETTINGS, pairOverrides: [['asset-3', override]]}));
        transitionClientSession(user);
        fake.set(serverSettings());
        expect(getGlobalLineShape()).toBe('segments');
        expect(resolveLineShape(getSettingsForPair('asset-3', 'assets'))).toBe('segments');
        expect(fake.updateUiPreference).not.toHaveBeenCalled();
    });

    it('saving the global settings of a scope does not change the shape', () => {
        freshUser();
        void setGlobalLineShape('spline');
        setGlobalSettings({...DEFAULT_CHART_SETTINGS, gridLines: false}, 'assets');
        expect(getGlobalLineShape()).toBe('spline');
        expect(resolveLineShape(getGlobalSettings('assets'))).toBe('spline');
    });
});

describe('chartSettingsStore — adoption of the line shape this browser kept before lot UIP', () => {
    /** A browser that stored `lineShape` in its payload, then the server settings arrive. */
    function arrive(legacy: string, settings: UserSettings): string {
        const user = `line-shape-legacy-${++userSeq}`;
        backing.set(`lf_${user}_chartSettingsStore`, JSON.stringify({version: 3, lineShape: legacy, globalSettings: DEFAULT_CHART_SETTINGS, pairOverrides: []}));
        transitionClientSession(user);
        fake.set(settings);
        vi.advanceTimersByTime(300);
        return user;
    }

    it("hands a legacy 'steps' to the server once when the server has no own key, and drops it from storage", () => {
        const user = arrive('steps', serverSettings());
        expect(fake.updateUiPreference).toHaveBeenCalledExactlyOnceWith('chart_line_shape', 'steps');
        expect(storedPayload(user)).not.toHaveProperty('lineShape');

        fake.set(serverSettings({chart_line_shape: 'steps'}));
        expect(fake.updateUiPreference, 'once: the next settings do not write again').toHaveBeenCalledTimes(1);
    });

    it("drops a legacy 'segments' without writing: it was the old default, not a choice", () => {
        const user = arrive('segments', serverSettings());
        expect(fake.updateUiPreference).not.toHaveBeenCalled();
        expect(storedPayload(user)).not.toHaveProperty('lineShape');
    });

    it('drops a legacy shape without writing when the server already has a key', () => {
        const user = arrive('steps', serverSettings({chart_line_shape: 'spline'}));
        expect(fake.updateUiPreference).not.toHaveBeenCalled();
        expect(storedPayload(user)).not.toHaveProperty('lineShape');
        expect(getGlobalLineShape()).toBe('spline');
    });

    it('never writes from the fallback settings the store uses when the server could not be read', () => {
        arrive('steps', fallbackSettings);
        expect(fake.updateUiPreference).not.toHaveBeenCalled();
    });
});
