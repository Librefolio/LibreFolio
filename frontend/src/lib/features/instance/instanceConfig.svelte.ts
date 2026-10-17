/**
 * The public configuration of this instance (Svelte 5 runes): `GET /api/v1/system/instance`, read once per page load.
 *
 * It is the same for whoever asks and needs no session, so the app reads it at startup, before the sign-in: the (app)
 * layout calls `load()` on mount, and a page outside it (the login) may call it too, since concurrent and repeated
 * calls share one request. Until the server answers, and whenever it cannot, the app works with
 * `DEFAULT_INSTANCE_CONFIG`, a self-hosted instance: a failed request never blocks the interface, and the next `load()`
 * asks again.
 *
 * The backend composes the response from the workstreams that own a part of it (`api/v1/system/instance.py`). The type
 * follows the generated client, so a field added there appears here after `./dev.py api sync`.
 *
 * Usage:
 *   import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
 *   await instanceConfig.load();
 *   instanceConfig.config.profile; // 'selfhosted' | 'managed'
 */

import type {z} from 'zod';
import {zodiosApi} from '$lib/api';
import type {schemas} from '$lib/api/generated';
import {debug} from '$lib/debug';

export type InstanceConfig = z.infer<typeof schemas.InstanceConfigResponse>;

/** What the app assumes until the server answers, and when it cannot: a self-hosted instance where anyone may register. */
export const DEFAULT_INSTANCE_CONFIG: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};

export interface LoadInstanceConfigOptions {
    /** Ask the server again even if it already answered on this page load. */
    force?: boolean;
    /** Defaults to `GET /api/v1/system/instance`. */
    fetchConfig?: () => Promise<InstanceConfig>;
}

export async function fetchInstanceConfigFromApi(): Promise<InstanceConfig> {
    return zodiosApi.get_instance_config_api_v1_system_instance_get();
}

let config = $state<InstanceConfig>(DEFAULT_INSTANCE_CONFIG);
let loaded = $state(false);
let failed = $state(false);
/** The request of this page load, shared by every caller until it settles; reset after a failure. */
let pending: Promise<void> | null = null;
/** Only the latest request may write its answer: a forced reload outruns an older one. */
let generation = 0;

function load(options: LoadInstanceConfigOptions = {}): Promise<void> {
    if (pending && !options.force) return pending;
    const request = ++generation;
    const fetchConfig = options.fetchConfig ?? fetchInstanceConfigFromApi;
    // The request starts now; a fetcher that throws at once becomes a rejected promise, so its failure is handled after
    // `pending` holds this attempt and can release it for the next call.
    let answer: Promise<InstanceConfig>;
    try {
        answer = Promise.resolve(fetchConfig());
    } catch (error) {
        answer = Promise.reject(error);
    }
    const attempt: Promise<void> = answer.then(
        (next) => {
            if (request !== generation) return;
            config = next;
            loaded = true;
            failed = false;
        },
        (error: unknown) => {
            if (request !== generation) return;
            failed = true;
            if (pending === attempt) pending = null;
            debug.warn('InstanceConfig', 'GET /system/instance failed; the defaults stay', error);
        },
    );
    pending = attempt;
    return attempt;
}

export const instanceConfig = {
    /** The configuration in force: the server's answer, or `DEFAULT_INSTANCE_CONFIG` until there is one. */
    get config(): InstanceConfig {
        return config;
    },
    /** True once the server answered on this page load. */
    get loaded(): boolean {
        return loaded;
    },
    /** True when the last request failed: the configuration in force is still the last one known. */
    get failed(): boolean {
        return failed;
    },
    load,
};
