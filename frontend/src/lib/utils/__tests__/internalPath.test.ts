/**
 * internalPath — the only destinations the app follows out of a URL it did not build itself (K, step 19).
 *
 * Two places take a destination from a query string and navigate to it: the login page, after a
 * sign-in (`/?redirect=…`), and the welcome flow (`returnTo`). Whoever wrote the link chose that value:
 * `/?redirect=//evil.example` must not turn a LibreFolio sign-in into a hop to another site.
 * `safeInternalPath` is the one rule both apply. `loginUrl` is how the app writes the `?redirect=` it will
 * read back later: the requested page survives the trip through the login, and a value the rule would
 * refuse is never written at all.
 *
 * The rule, as approved: a value is kept, unchanged, only when it is a string that starts with exactly one
 * `/` (not `//`), contains no `\` and no ASCII control character (U+0000–U+001F, U+007F), and, resolved
 * against a dummy origin, stays on that origin. Anything else becomes the fallback. The control characters
 * are not pedantry: the URL parser strips a tab or a newline, so `/\t/evil.example` is `//evil.example`
 * by the time a browser follows it. NUL, U+001F and DEL are the edges of the stated range; the parser
 * percent-encodes them rather than leaving the origin, so only the explicit rule refuses them.
 *
 * The module is loaded inside each test rather than imported at the top: while it does not exist, a
 * static import would fail the whole file at collection with no case reported, where this way every case
 * fails on its own and names the missing module or export.
 *
 * Pure functions — no DOM, no store, no network — so this is a unit test in the default `node` environment.
 */
import {describe, expect, it} from 'vitest';

interface InternalPathModule {
    safeInternalPath: (value: string | null | undefined, fallback?: string) => string;
    loginUrl: (requested: string | null | undefined) => string;
}

/** One export of `$lib/utils/internalPath`, or a failure that says which part of the module is missing. */
async function exported<K extends keyof InternalPathModule>(name: K): Promise<InternalPathModule[K]> {
    let module: Record<string, unknown>;
    try {
        module = (await import('../internalPath')) as unknown as Record<string, unknown>;
    } catch (error) {
        throw new Error(`$lib/utils/internalPath is missing or does not load: ${error instanceof Error ? error.message : String(error)}`);
    }
    expect(typeof module[name], `$lib/utils/internalPath must export a function named ${name}`).toBe('function');
    return module[name] as InternalPathModule[K];
}

/** Values the rule keeps as they are: internal paths, with a query, an encoded query value or a hash. */
const KEPT: string[] = ['/assets/34?tab=risk', '/dashboard', '/welcome?returnTo=%2Fassets', '/assets/34?tab=risk#chart'];

/** Values the rule refuses, each with the reason it must, as [reason, value]. */
const REFUSED: [string, string | null | undefined][] = [
    ['a protocol-relative URL', '//evil.example'],
    ['an absolute URL', 'https://evil.example'],
    ['a backslash, which a browser reads as a slash', '/\\evil'],
    ['a tab, which the URL parser strips into //', '/\t/evil.example'],
    ['a newline, which the URL parser strips the same way', '/\n/evil'],
    ['a javascript: URL', 'javascript:alert(1)'],
    ['a relative path', 'assets/34'],
    ['an empty string', ''],
    ['null', null],
    ['undefined', undefined],
    ['U+0000, the first control character', '/assets/\u0000'],
    ['U+001F, the last C0 control character', '/assets/\u001f'],
    ['U+007F (DEL), a control character too', '/assets/\u007f'],
];

describe('safeInternalPath', () => {
    it.each(KEPT)('keeps the internal path %s unchanged', async (path) => {
        const safeInternalPath = await exported('safeInternalPath');
        expect(safeInternalPath(path), `${path} is an internal path and must be followed as it is`).toBe(path);
    });

    it.each(REFUSED)('refuses %s → /dashboard', async (_reason, value) => {
        const safeInternalPath = await exported('safeInternalPath');
        expect(safeInternalPath(value), `${JSON.stringify(value)} must not be followed`).toBe('/dashboard');
    });

    it('returns the fallback it is given, and a kept value still wins over it', async () => {
        const safeInternalPath = await exported('safeInternalPath');
        expect(safeInternalPath('//evil.example', '/assets'), 'a refused value falls back to the given fallback').toBe('/assets');
        expect(safeInternalPath(null, '/assets'), 'a missing value falls back to the given fallback').toBe('/assets');
        expect(safeInternalPath('/fx', '/assets'), 'a kept value is returned, not the fallback').toBe('/fx');
    });
});

describe('loginUrl', () => {
    it('carries the requested path and query to the login page, encoded as one ?redirect= value', async () => {
        const loginUrl = await exported('loginUrl');
        expect(loginUrl('/assets/34?tab=risk')).toBe('/?redirect=%2Fassets%2F34%3Ftab%3Drisk');
    });

    it.each([
        ['the root (already the login page)', '/'],
        ['a value the rule refuses', '//evil.example'],
        ['null', null],
        ['undefined', undefined],
    ] as [string, string | null | undefined][])('%s → the bare login page /', async (_reason, requested) => {
        const loginUrl = await exported('loginUrl');
        expect(loginUrl(requested), `${JSON.stringify(requested)} has nothing worth bringing back after the sign-in`).toBe('/');
    });

    it.each(['/assets/34?tab=risk', '/welcome?returnTo=%2Fassets'])('round trip: the login page reads %s back from ?redirect=, and the rule keeps it', async (path) => {
        const loginUrl = await exported('loginUrl');
        const safeInternalPath = await exported('safeInternalPath');
        const url = new URL(loginUrl(path), 'http://librefolio.test');
        expect(url.pathname, 'the login URL points at the login page').toBe('/');
        const readBack = url.searchParams.get('redirect');
        expect(readBack, 'the login page reads back exactly the page that was asked for').toBe(path);
        expect(safeInternalPath(readBack), 'and the rule lets it through on the way back').toBe(path);
    });
});
