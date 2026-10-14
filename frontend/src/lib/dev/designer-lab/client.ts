/**
 * Designer Lab — the client every page of a debug build loads (from the root layout).
 *
 * It must cost nothing when the Lab is unused: E2E and the gallery run on debug builds. With no saved state it only
 * listens for the `storage` event; the engines (stylesheets, charts, variables) are separate chunks, loaded the first
 * time a state with an effect appears.
 */

import {hasEffect, readState, STORAGE_KEY} from './store';
import type {LabHook} from './types';

type Engine = typeof import('./engine');

let engine: Engine | null = null;
let started = false;

async function sync(): Promise<void> {
    const state = readState();
    if (!engine) {
        if (!hasEffect(state)) return;
        engine = await import('./engine');
    }
    await engine.applyState(state);
}

const hook: LabHook = {
    active: () => engine?.isActive() ?? false,
    chartColors: async (selector) => (await import('./engine/charts')).chartColorsOf(selector),
    stats: () => engine?.stats() ?? {cssRules: 0, chartInstances: 0, varOverrides: 0},
};

/** Start the client: re-apply the saved state, then follow the changes other tabs write. Idempotent. */
export function start(): void {
    if (started || typeof window === 'undefined') return;
    started = true;
    window.__lfDesignerLab = hook;
    window.addEventListener('storage', (event) => {
        if (event.key === STORAGE_KEY || event.key === null) void sync();
    });
    void sync();
}

/** For the Lab page, which writes the state itself and gets no `storage` event for its own writes. */
export async function applyNow(): Promise<void> {
    await sync();
}
