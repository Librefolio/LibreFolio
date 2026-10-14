/**
 * Connection security, shared by the sidebar indicator and the header's menu dot.
 *
 * The browser's verdict is ready at once; `refreshConnectionSecurity()` then asks the server
 * once per page load and folds its answer in. A failed request keeps the browser's verdict.
 */

import {type Readable, writable} from 'svelte/store';
import {zodiosApi} from '$lib/api';
import {assessConnection, type ConnectionAssessment, type ServerView} from '$lib/utils/security/connectionSecurity';

export interface ConnectionSecurityState extends ConnectionAssessment {
    /** True once the server answered; until then the browser decides alone. */
    serverChecked: boolean;
}

/** The parts of `window.location` the verdict reads. */
export type LocationLike = Pick<Location, 'protocol' | 'hostname'>;

export interface RefreshConnectionSecurityOptions {
    /** Defaults to `window.location`. */
    location?: LocationLike;
    /** Defaults to `GET /api/v1/system/connection`. */
    fetchServerView?: () => Promise<ServerView>;
    /** Ask the server again even if it already answered on this page load. */
    force?: boolean;
}

export async function fetchServerViewFromApi(): Promise<ServerView> {
    const response = await zodiosApi.get_connection_security_api_v1_system_connection_get();
    return {clientClass: response.client_class, cookieSecure: response.cookie_secure};
}

function verdict(location: LocationLike, server: ServerView | null): ConnectionSecurityState {
    return {...assessConnection({protocol: location.protocol, hostname: location.hostname, server}), serverChecked: server !== null};
}

/** The browser's verdict on the page it is showing; without a window, the most cautious one. */
function browserVerdict(): ConnectionSecurityState {
    if (typeof window === 'undefined') return {level: 'insecure', reason: 'internet', cookieWarning: false, serverChecked: false};
    return verdict(window.location, null);
}

const state = writable<ConnectionSecurityState>(browserVerdict());

/** Whether this page load already asked the server, and which request may still fold its answer in. */
let asked = false;
let generation = 0;

export const connectionSecurity: Readable<ConnectionSecurityState> = {subscribe: state.subscribe};

/** Compute the browser's verdict, then ask the server once and fold its answer in. */
export async function refreshConnectionSecurity(options: RefreshConnectionSecurityOptions = {}): Promise<void> {
    if (asked && !options.force) return;
    const location = options.location ?? (typeof window === 'undefined' ? null : window.location);
    if (!location) return;
    asked = true;
    const request = ++generation;
    state.set(verdict(location, null));
    let server: ServerView;
    try {
        server = await (options.fetchServerView ?? fetchServerViewFromApi)();
    } catch {
        return; // the browser's verdict stands: the indicator shows no error of its own (plan 36, D4)
    }
    if (request === generation) state.set(verdict(location, server));
}

/** Forget the server's answer, so the next refresh asks again. */
export function resetConnectionSecurity(): void {
    asked = false;
    generation += 1;
    state.set(browserVerdict());
}
