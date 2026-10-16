/**
 * Designer Lab — the client every page of a debug build loads (from the root layout).
 *
 * It must cost nothing when the Lab is unused: E2E and the gallery run on debug builds. With no saved state it only
 * listens for the `storage` event; the engines (stylesheets, charts, variables) and the element picker are separate
 * chunks, loaded the first time a state with an effect, or a pick request, appears. The Alt+Shift+D shortcut is
 * installed only in a browser where the Lab has been opened (`lf-designer-lab/seen`), never in a fresh context.
 */

import {isPendingStart, newPickId, PICK_KEY, readPick, SEEN_KEY, wasSeen} from './pick';
import {hasEffect, readState, STORAGE_KEY} from './store';
import type {LabHook} from './types';

type Engine = typeof import('./engine');
type Picker = typeof import('./picker/overlay');

let engine: Engine | null = null;
let picker: Picker | null = null;
let started = false;
let shortcut = false;

/** The Lab's own page never picks: the elements to point at are in the app tabs. */
const onLabPage = () => location.pathname.startsWith('/designer-lab');

async function sync(): Promise<void> {
    const state = readState();
    if (!engine) {
        if (!hasEffect(state)) return;
        engine = await import('./engine');
    }
    await engine.applyState(state);
}

async function followPick(): Promise<void> {
    if (onLabPage()) return;
    const message = readPick();
    if (!picker && !isPendingStart(message)) return;
    picker ??= await import('./picker/overlay');
    picker.follow(message);
}

function installShortcut(): void {
    if (shortcut || !wasSeen()) return;
    shortcut = true;
    window.addEventListener('keydown', (event) => {
        // `code`, not `key`: on macOS Alt+Shift+D types «Î».
        if (event.code !== 'KeyD' || !event.altKey || !event.shiftKey || event.ctrlKey || event.metaKey || event.repeat || onLabPage()) return;
        event.preventDefault();
        void import('./picker/overlay').then((module) => {
            picker = module;
            module.arm(`local-${newPickId()}`);
        });
    });
}

const hook: LabHook = {
    active: () => engine?.isActive() ?? false,
    picking: () => picker?.isArmed() ?? false,
    chartColors: async (selector) => (await import('./engine/charts')).chartColorsOf(selector),
    stats: () => engine?.stats() ?? {cssRules: 0, chartInstances: 0, varOverrides: 0, elementRules: 0, categoryOverrides: 0},
    // Asked by every chart category on every draw (contract C3): nothing until a state with an effect loads the engine.
    categoryColor: (kind, key, dark) => engine?.categoryColor(kind, key, dark),
};

/** Start the client: re-apply the saved state, then follow what other tabs write. Idempotent. */
export function start(): void {
    if (started || typeof window === 'undefined') return;
    started = true;
    window.__lfDesignerLab = hook;
    window.addEventListener('storage', (event) => {
        if (event.key === STORAGE_KEY || event.key === null) void sync();
        if (event.key === PICK_KEY || event.key === null) void followPick();
        if (event.key === SEEN_KEY) installShortcut();
    });
    installShortcut();
    void followPick();
    void sync();
}

/** For the Lab page, which writes the state itself and gets no `storage` event for its own writes. */
export async function applyNow(): Promise<void> {
    await sync();
}
