/**
 * Privacy Store — global "hide values" preference.
 *
 * Device-local, not an account property (D1): the use case is contextual —
 * someone is looking at the screen, the projector is connected — so the
 * preference describes the screen being watched, not who is logged in.
 *
 * The key is therefore **bare**, not `lf_{userId}_` (D2). With a per-user key
 * an account switch would adopt the *other* account's preference, which can be
 * "off": the values would reappear during a switch made in front of the
 * projector, the exact situation the feature exists for. `librefolio-theme`
 * and `librefolio-locale` are already bare for the same reason.
 *
 * Read/write are guarded twice. `typeof`/`browser` answers "does localStorage
 * exist?"; the `try/catch` answers "can the call fail?" — and it can, while
 * existing: Safari private mode, exceeded quota, storage denied. The precedent
 * is `$lib/utils/storage.ts`, *not* `themeStore`, which guards with `typeof`
 * alone.
 *
 * A failed write matters more than a failed read. It would leave the state on
 * in memory and off on disk: the current session masks, the reload does not,
 * and the user believes a protection that is not there. `persisted` carries
 * that fact out instead of swallowing it.
 *
 * @module stores/app/privacyStore
 */

import {browser} from '$app/environment';

export const PRIVACY_STORAGE_KEY = 'librefolio-privacy';

const ON = '1';
const OFF = '0';

function readStoredPreference(): boolean {
    if (!browser) return false;
    try {
        return localStorage.getItem(PRIVACY_STORAGE_KEY) === ON;
    } catch {
        return false;
    }
}

function writeStoredPreference(value: boolean): boolean {
    if (!browser) return false;
    try {
        localStorage.setItem(PRIVACY_STORAGE_KEY, value ? ON : OFF);
        return true;
    } catch {
        return false;
    }
}

/**
 * Hydrated synchronously at module init, before any render: the module is
 * imported by the currency formatters, so it initializes while the module
 * graph loads — earlier than the first formatting call.
 *
 * An absent key means "off" (D3): there is no "masked by default", the initial
 * value is the persisted one.
 */
let enabled = $state(readStoredPreference());

/** False once a write has failed: the live value no longer matches the disk. */
let persisted = $state(true);

/**
 * Whether values must be masked right now.
 *
 * Reading the rune here is what registers the reactive dependency in the
 * caller: a component template that formats an amount re-renders on toggle
 * without subscribing to anything. Callbacks that run outside a reactive
 * context — ECharts `formatter`, for one — still read the current value, but
 * an already-painted tooltip needs explicit invalidation.
 */
export function isPrivacyEnabled(): boolean {
    return enabled;
}

/**
 * Whether the live preference survived to storage.
 *
 * Returns false when the last write threw. The preference still applies to
 * this session; it will not survive a reload.
 */
export function isPrivacyPersisted(): boolean {
    return persisted;
}

export function setPrivacyEnabled(value: boolean): void {
    enabled = value;
    persisted = writeStoredPreference(value);
}

export function togglePrivacy(): void {
    setPrivacyEnabled(!enabled);
}
