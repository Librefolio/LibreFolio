/**
 * Designer Lab — the element picker's messages between tabs.
 *
 * The Lab and the app tabs talk through two localStorage keys, the same channel the colour state uses: a write in one
 * tab reaches every other tab of the same origin as a `storage` event, and the idle client already listens for it.
 *
 * - `lf-designer-lab/pick` holds the last message: `start` (the Lab asks the app tabs to pick), `cancel`, or `result`
 *   (an app tab reports the element picked). A result ends picking in every tab; a cancel ends the request it names
 *   (a pick started with the shortcut in one tab has its own id); removing the key ends any picking. The Lab cancels
 *   its request when it unmounts or its tab is closed.
 * - `lf-designer-lab/seen` marks a browser where the Lab has been opened: only there does an app tab install the
 *   Alt+Shift+D shortcut. E2E and gallery contexts start empty, so they never get it.
 */

import type {PickedElement} from './types';

export const PICK_KEY = 'lf-designer-lab/pick';
export const SEEN_KEY = 'lf-designer-lab/seen';

/** A tab that loads while a request is pending joins it; a request older than this is a forgotten one. */
export const PICK_FRESH_MS = 5 * 60 * 1000;

export type PickMessage = {op: 'start' | 'cancel'; id: string; at: number} | {op: 'result'; id: string; at: number; element: PickedElement};

export function newPickId(): string {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function readPick(storage: Storage = localStorage): PickMessage | null {
    let raw: string | null;
    try {
        raw = storage.getItem(PICK_KEY);
    } catch {
        return null;
    }
    if (!raw) return null;
    try {
        const message = JSON.parse(raw) as Partial<PickMessage> & {element?: unknown};
        if (!message || typeof message.id !== 'string' || typeof message.at !== 'number') return null;
        if (message.op === 'start' || message.op === 'cancel') return {op: message.op, id: message.id, at: message.at};
        if (message.op === 'result' && message.element && typeof message.element === 'object') return message as PickMessage;
        return null;
    } catch {
        return null;
    }
}

export function writePick(message: PickMessage, storage: Storage = localStorage): void {
    try {
        storage.setItem(PICK_KEY, JSON.stringify(message));
    } catch {
        // storage full or unavailable: the pick is lost, nothing else breaks
    }
}

/** Whether a `start` message is a request a tab should still answer. */
export function isPendingStart(message: PickMessage | null, now = Date.now()): boolean {
    return message?.op === 'start' && now - message.at < PICK_FRESH_MS;
}

export function markSeen(storage: Storage = localStorage): void {
    try {
        storage.setItem(SEEN_KEY, '1');
    } catch {
        // storage unavailable: no shortcut
    }
}

export function wasSeen(storage: Storage = localStorage): boolean {
    try {
        return storage.getItem(SEEN_KEY) !== null;
    } catch {
        return false;
    }
}
