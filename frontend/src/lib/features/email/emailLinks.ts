/**
 * The check of the emailed links' base, from the administrator's browser (developer decision 45): every link an email
 * carries starts with `LIBREFOLIO_PUBLIC_URL`, and only a browser can tell whether that address reaches *this*
 * instance from where it stands — the server may sit behind a VPN, a direct IP or a DNS of its own.
 *
 * It is workstream A's address check (`settings/users/addressProbe.ts`), reused as it is: a signed nonce of this
 * instance, sent to `<base>/api/v1/auth/address-probe`. On top of it, one case the browser can tell for sure before
 * asking anything: an https page cannot fetch an http address (mixed content).
 */
import {checkAddress, normalizeBase, type ProbeVerdict} from '$lib/features/settings/users/addressProbe';

/**
 * What the check found, from this browser only:
 * - `match`: this instance answers at the base;
 * - `otherInstance`: something answers there, but not this instance;
 * - `unreachable`: nothing could be read (network, DNS, CORS, a timeout, a local-network permission);
 * - `insecure`: the page is https and the base http, so the browser would refuse the request;
 * - `invalid`: the browser cannot read the base as an http(s) address.
 */
export type LinksOutcome = 'match' | 'otherInstance' | 'unreachable' | 'insecure' | 'invalid';

/** An outcome, or the check still running. */
export type LinksProbeState = 'checking' | LinksOutcome;

const VERDICT_OUTCOMES: Record<ProbeVerdict, LinksOutcome> = {
    match: 'match',
    mismatch: 'otherInstance',
    unverifiable: 'unreachable',
};

export interface LinksProbeOptions {
    /** The protocol of the page the administrator is on: `window.location.protocol`. */
    pageProtocol: string;
    /** A nonce of this instance (`POST /users/address-probe`). */
    issueNonce: () => Promise<string>;
    fetchImpl?: typeof fetch;
    timeoutMs?: number;
}

/** Whether this instance answers, from this browser, at `base`, the base of the emailed links. Never throws. */
export async function probeEmailLinks(base: string, {pageProtocol, ...options}: LinksProbeOptions): Promise<LinksOutcome> {
    const normalized = normalizeBase(base);
    if (normalized === null) {
        return 'invalid';
    }
    if (pageProtocol === 'https:' && normalized.startsWith('http:')) {
        return 'insecure';
    }
    return VERDICT_OUTCOMES[await checkAddress(normalized, options)];
}
