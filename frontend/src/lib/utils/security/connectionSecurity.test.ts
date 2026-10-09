/**
 * Connection security — the pure rule and the shared store (plan 36, §2.2–§2.3).
 *
 * The browser knows its own protocol and the host it was pointed at; the server
 * (`GET /api/v1/system/connection`) adds the class of the address it sees. The rule, in Q's words: the server can
 * confirm the browser's verdict or make it uncertain, but never make it secure.
 *
 *   - `classifyHost(hostname)` → loopback, vpn, lan or public. Case, a trailing dot and IPv6 brackets do not count; a
 *     name without a dot is a LAN name; a suffix counts only as whole labels (`ts.net.example.com` and
 *     `lan.example.com` are public).
 *   - `assessConnection({protocol, hostname, server})` → `{level, reason, cookieWarning}`, by the table of §2.3, read
 *     with both cookie decisions so that `cookieSecure` is seen to move nothing but `cookieWarning`; then the
 *     invariant, over the whole matrix, with positive controls (a constant verdict satisfies it vacuously).
 *   - `connectionSecurityDocsUrl(lang)` → the user page at its root, in the documentation language.
 *   - the store: the browser's verdict at once, the server's answer folded in, a failed answer kept silent, the server
 *     asked once per page load.
 *
 * Written RED-FIRST against the stubs of plan 36 (step 2): every red fails on an assertion, never on an import. The
 * environment is `node`: the store is a plain `svelte/store` writable. The network is never reached — every refresh
 * injects its `location` and its `fetchServerView`, and `$lib/api` is mocked so that the default fetch, should a
 * refresh ever fall back to it, fails loudly instead of leaving the process.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

const connectionApi = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: {get_connection_security_api_v1_system_connection_get: connectionApi},
}));

import {assessConnection, classifyHost, connectionSecurityDocsUrl, type ConnectionLevel, type ConnectionReason, type HostClass, type ServerClientClass, type ServerView} from './connectionSecurity';
import {connectionSecurity, fetchServerViewFromApi, refreshConnectionSecurity, resetConnectionSecurity, type LocationLike} from '$lib/stores/app/connectionSecurityStore';

/** Table A of the plan: every host name the classifier must place, by class. */
const HOSTS: Record<HostClass, readonly string[]> = {
    loopback: ['localhost', 'LOCALHOST', 'localhost.', 'app.localhost', '127.0.0.1', '127.1.2.3', '::1', '[::1]'],
    vpn: ['100.64.0.1', '100.127.255.254', '[fd7a:115c:a1e0::1]', 'server.tailnet-abc.ts.net', 'SERVER.TS.NET'],
    lan: ['10.1.2.3', '172.16.0.1', '172.31.255.255', '192.168.1.10', '169.254.1.1', '[fe80::1]', '[fd00::1]', 'nas.local', 'lf.lan', 'lf.home.arpa', 'lf.internal', 'nas'],
    public: ['example.com', 'lf.example', '8.8.8.8', '172.32.0.1', '100.128.0.1', '[2001:db8::1]', 'ts.net.example.com', 'lan.example.com'],
};
const HOST_CLASSES = Object.keys(HOSTS) as HostClass[];
const ALL_HOSTNAMES: readonly string[] = HOST_CLASSES.flatMap((hostClass) => HOSTS[hostClass]);

/** The classes the server may report: the four of the browser, and `unknown`. */
const SERVER_CLASSES: readonly ServerClientClass[] = ['loopback', 'vpn', 'lan', 'public', 'unknown'];
/** Every answer the server can give: none yet (`null`), or a class with either cookie decision. */
const SERVER_ANSWERS: readonly (ServerView | null)[] = [null, ...SERVER_CLASSES.flatMap((clientClass) => [true, false].map((cookieSecure) => ({clientClass, cookieSecure})))];
const PROTOCOLS = ['https:', 'http:'] as const;

/** One host per class for the rule (the classifier has its own table). */
const HOST_OF: Record<HostClass, string> = {loopback: 'localhost', vpn: 'server.tailnet-abc.ts.net', lan: 'nas.local', public: 'lf.example'};

function describeServer(server: ServerView | null): string {
    return server === null ? 'no answer' : `${server.clientClass}, cookie ${server.cookieSecure ? 'Secure' : 'not Secure'}`;
}

describe('classifyHost — the class of the host the browser was pointed at', () => {
    const CASES = HOST_CLASSES.flatMap((expected) => HOSTS[expected].map((hostname): [string, HostClass] => [hostname, expected]));

    it.each(CASES)('%s → %s', (hostname, expected) => {
        expect(classifyHost(hostname)).toBe(expected);
    });
});

/**
 * Table B of the plan (§2.3), one row per browser view: the server classes it applies to, and the verdict. Read with
 * both cookie decisions, since `cookieSecure` must move `cookieWarning` alone.
 */
describe('assessConnection — the level and its reason (§2.3)', () => {
    type Row = {protocol: (typeof PROTOCOLS)[number]; host: HostClass; servers: readonly (ServerClientClass | null)[]; level: ConnectionLevel; reason: ConnectionReason};
    const ANY: readonly (ServerClientClass | null)[] = [null, ...SERVER_CLASSES];
    const NOT_PUBLIC: readonly (ServerClientClass | null)[] = [null, 'loopback', 'vpn', 'lan', 'unknown'];
    const RULE: readonly Row[] = [
        {protocol: 'https:', host: 'loopback', servers: ANY, level: 'secure', reason: 'https'},
        {protocol: 'https:', host: 'vpn', servers: ANY, level: 'secure', reason: 'https'},
        {protocol: 'https:', host: 'lan', servers: ANY, level: 'secure', reason: 'https'},
        {protocol: 'https:', host: 'public', servers: ANY, level: 'secure', reason: 'https'},
        {protocol: 'http:', host: 'loopback', servers: ANY, level: 'secure', reason: 'localhost'},
        {protocol: 'http:', host: 'vpn', servers: NOT_PUBLIC, level: 'secure', reason: 'vpn'},
        {protocol: 'http:', host: 'vpn', servers: ['public'], level: 'local', reason: 'uncertain'},
        {protocol: 'http:', host: 'lan', servers: NOT_PUBLIC, level: 'local', reason: 'lan'},
        {protocol: 'http:', host: 'lan', servers: ['public'], level: 'local', reason: 'uncertain'},
        {protocol: 'http:', host: 'public', servers: [null, 'public', 'unknown'], level: 'insecure', reason: 'internet'},
        {protocol: 'http:', host: 'public', servers: ['loopback', 'vpn', 'lan'], level: 'local', reason: 'uncertain'},
    ];

    const CASES: Array<{label: string; protocol: string; hostname: string; server: ServerView | null; level: ConnectionLevel; reason: ConnectionReason}> = [];
    for (const row of RULE) {
        for (const clientClass of row.servers) {
            const answers: (ServerView | null)[] = clientClass === null ? [null] : [true, false].map((cookieSecure) => ({clientClass, cookieSecure}));
            for (const server of answers) {
                const hostname = HOST_OF[row.host];
                CASES.push({label: `${row.protocol}//${hostname} (${row.host}), server: ${describeServer(server)}`, protocol: row.protocol, hostname, server, level: row.level, reason: row.reason});
            }
        }
    }

    it('premise: the table covers every protocol × host class × server answer exactly once', () => {
        const seen = CASES.map(({protocol, hostname, server}) => `${protocol}//${hostname} ${describeServer(server)}`);
        const expected = PROTOCOLS.flatMap((protocol) => HOST_CLASSES.flatMap((host) => SERVER_ANSWERS.map((server) => `${protocol}//${HOST_OF[host]} ${describeServer(server)}`)));
        expect([...seen].sort()).toEqual([...expected].sort());
    });

    // Titled through `%s`: a `$label` interpolation is truncated at 40 characters, which would merge the two cookie
    // decisions of one row under a single name.
    it.each(CASES.map((testCase): [string, (typeof CASES)[number]] => [`${testCase.label} → ${testCase.level} / ${testCase.reason}`, testCase]))('%s', (_title, {protocol, hostname, server, level, reason}) => {
        expect(assessConnection({protocol, hostname, server})).toMatchObject({level, reason});
    });
});

describe('assessConnection — cookieWarning: HTTPS in the browser, a session cookie the server does not mark Secure', () => {
    /** Every https: page and every class the server may see, with the cookie decision `cookieSecure`. */
    function httpsPages(cookieSecure: boolean): Array<{label: string; hostname: string; server: ServerView}> {
        return HOST_CLASSES.flatMap((host) => SERVER_CLASSES.map((clientClass) => ({label: `https://${HOST_OF[host]}, server: ${clientClass}`, hostname: HOST_OF[host], server: {clientClass, cookieSecure}})));
    }

    it('true on https: whenever the server reports cookieSecure false, whatever the host and the class it sees', () => {
        const unwarned = httpsPages(false)
            .filter(({hostname, server}) => assessConnection({protocol: 'https:', hostname, server}).cookieWarning !== true)
            .map(({label}) => label);

        expect(unwarned, 'the browser is on HTTPS and the session cookie is not Secure: the warning is due').toEqual([]);
    });

    it('false on https: when the server reports cookieSecure true', () => {
        const warned = httpsPages(true)
            .filter(({hostname, server}) => assessConnection({protocol: 'https:', hostname, server}).cookieWarning !== false)
            .map(({label}) => label);

        expect(warned, 'a Secure cookie is consistent with HTTPS').toEqual([]);
    });

    it('false on https: while the server has not answered', () => {
        const warned = HOST_CLASSES.filter((host) => assessConnection({protocol: 'https:', hostname: HOST_OF[host], server: null}).cookieWarning !== false).map((host) => HOST_OF[host]);

        expect(warned, 'without an answer there is no cookie decision to contradict').toEqual([]);
    });

    it('false on http:, even when the cookie is not Secure: there is no HTTPS to be inconsistent with', () => {
        const warned = HOST_CLASSES.flatMap((host) => SERVER_CLASSES.map((clientClass) => ({host, clientClass})))
            .filter(({host, clientClass}) => assessConnection({protocol: 'http:', hostname: HOST_OF[host], server: {clientClass, cookieSecure: false}}).cookieWarning !== false)
            .map(({host, clientClass}) => `http://${HOST_OF[host]}, server: ${clientClass}`);

        expect(warned).toEqual([]);
    });
});

describe('assessConnection — the server can confirm the verdict or make it uncertain, never make it secure', () => {
    it('over every protocol × host × server answer: what the browser alone does not call secure never turns secure', () => {
        const upgraded: string[] = [];
        /** Browser-only verdicts that are not secure, each met with every server answer: what the invariant protects. */
        let guarded = 0;
        /** Of those, how many a server answer moved at all. */
        let moved = 0;

        for (const protocol of PROTOCOLS) {
            for (const hostname of ALL_HOSTNAMES) {
                const alone = assessConnection({protocol, hostname, server: null});
                if (alone.level === 'secure') continue;
                for (const server of SERVER_ANSWERS) {
                    if (server === null) continue;
                    guarded += 1;
                    const answered = assessConnection({protocol, hostname, server});
                    if (answered.level === 'secure') upgraded.push(`${protocol}//${hostname} is ${alone.level} alone, secure with ${describeServer(server)}`);
                    if (answered.level !== alone.level || answered.reason !== alone.reason) moved += 1;
                }
            }
        }

        expect(upgraded, 'a server answer turned a verdict the browser does not call secure into secure').toEqual([]);
        expect(guarded, 'positive control: the matrix holds browser-only verdicts that are not secure').toBeGreaterThan(0);
        expect(moved, 'positive control: a server answer moves some of them (a public name seen from a LAN is uncertain), so the invariant is not satisfied by a constant verdict').toBeGreaterThan(0);
    });
});

describe('connectionSecurityDocsUrl — the user page at its root, in the documentation language', () => {
    it.each([
        ['en', '/mkdocs/user/connection-security/'],
        ['it', '/mkdocs/it/user/connection-security/'],
        ['fr', '/mkdocs/fr/user/connection-security/'],
        ['es', '/mkdocs/es/user/connection-security/'],
    ])('%s → %s', (lang, url) => {
        expect(connectionSecurityDocsUrl(lang)).toBe(url);
    });
});

/**
 * The store both the legacy Sidebar and the runes Header read. The browser's verdict is there at once;
 * `refreshConnectionSecurity()` asks the server once per page load and folds its answer in; a failed request keeps
 * the browser's verdict and shows no error (D4). Every case starts from `resetConnectionSecurity()`.
 */
describe('connectionSecurityStore — the browser decides first, the server is asked once per page load', () => {
    const LF_EXAMPLE: LocationLike = {protocol: 'http:', hostname: 'lf.example'};
    const LF_LAN: LocationLike = {protocol: 'http:', hostname: 'lf.lan'};

    function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
        let resolve: (value: T) => void = () => undefined;
        const promise = new Promise<T>((settle) => {
            resolve = settle;
        });
        return {promise, resolve};
    }

    beforeEach(() => {
        resetConnectionSecurity();
        connectionApi.mockReset();
        connectionApi.mockRejectedValue(new Error('the network is not part of this test: every refresh injects fetchServerView'));
    });

    afterEach(() => {
        resetConnectionSecurity();
    });

    it('a server answer folds in: http://lf.example, the server sees a public client → insecure / internet, serverChecked', async () => {
        const fetchServerView = vi.fn(async (): Promise<ServerView> => ({clientClass: 'public', cookieSecure: false}));

        await refreshConnectionSecurity({location: LF_EXAMPLE, fetchServerView});

        expect(fetchServerView, 'the refresh asked the server').toHaveBeenCalledTimes(1);
        expect(get(connectionSecurity)).toMatchObject({level: 'insecure', reason: 'internet', cookieWarning: false, serverChecked: true});
    });

    it('the browser decides first: http://lf.lan is local / lan while the server is asked, then uncertain once it reports a public client', async () => {
        const answer = deferred<ServerView>();

        const refreshing = refreshConnectionSecurity({location: LF_LAN, fetchServerView: () => answer.promise});

        await vi.waitFor(() => expect(get(connectionSecurity), 'with the request still pending, the browser verdict is already there').toMatchObject({level: 'local', reason: 'lan', cookieWarning: false, serverChecked: false}));
        answer.resolve({clientClass: 'public', cookieSecure: false});
        await refreshing;
        expect(get(connectionSecurity), 'a LAN name the server sees reached from a public address is uncertain').toMatchObject({level: 'local', reason: 'uncertain', cookieWarning: false, serverChecked: true});
    });

    it('a failed request keeps the browser verdict, serverChecked false, and nothing throws', async () => {
        const fetchServerView = vi.fn((): Promise<ServerView> => Promise.reject(new Error('503 from the reverse proxy')));

        await expect(refreshConnectionSecurity({location: LF_LAN, fetchServerView}), 'a failed request is not an error of the refresh').resolves.toBeUndefined();

        expect(fetchServerView, 'premise: the server was asked').toHaveBeenCalledTimes(1);
        expect(get(connectionSecurity)).toMatchObject({level: 'local', reason: 'lan', cookieWarning: false, serverChecked: false});
    });

    it('once per page load: a second refresh does not ask again; force does; after a reset the next refresh asks again', async () => {
        const fetchServerView = vi.fn(async (): Promise<ServerView> => ({clientClass: 'lan', cookieSecure: false}));

        await refreshConnectionSecurity({location: LF_LAN, fetchServerView});
        await refreshConnectionSecurity({location: LF_LAN, fetchServerView});
        expect(fetchServerView, 'two refreshes on one page load ask the server once').toHaveBeenCalledTimes(1);
        expect(get(connectionSecurity), 'and the second keeps the answer of the first').toMatchObject({level: 'local', reason: 'lan', serverChecked: true});

        await refreshConnectionSecurity({location: LF_LAN, fetchServerView, force: true});
        expect(fetchServerView, 'force asks again').toHaveBeenCalledTimes(2);

        resetConnectionSecurity();
        await refreshConnectionSecurity({location: LF_LAN, fetchServerView});
        expect(fetchServerView, 'after a reset, the next refresh asks again').toHaveBeenCalledTimes(3);
    });

    it('fetchServerViewFromApi, the default fetch, reads GET /api/v1/system/connection into a ServerView', async () => {
        connectionApi.mockResolvedValueOnce({client_class: 'vpn', cookie_secure: true});

        await expect(fetchServerViewFromApi()).resolves.toEqual({clientClass: 'vpn', cookieSecure: true});
        expect(connectionApi).toHaveBeenCalledTimes(1);
    });
});
