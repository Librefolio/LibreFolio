// @vitest-environment jsdom
/**
 * whatsNewStore.svelte.ts — when «What's new since your last version» shows, and how it goes away (workstream A,
 * lot C-54).
 *
 * The backend adds to the user payload of the login and of `GET /auth/me` `whats_new: {since, release} | null`;
 * closing the popup sends `POST /api/v1/auth/whats-new/seen`. The store sits between the two. The contract under test
 * (approved by the coordinator, 17/10):
 *   - WNS-00, the premise (green before the store exists): the auth store's user is the payload as the backend sent
 *     it, `whats_new` included, through `/auth/me` and through the login — the seam the store reads;
 *   - WNS-01: the module sits next to this test and exports `whatsNew`, with `shouldShow`, `chapters` and `dismiss()`;
 *   - WNS-02..07: `shouldShow` is true exactly when an account is signed in, its `whats_new` is not null,
 *     `whatsNewChapters(changelogChapters, whats_new)` is not empty and nothing was dismissed in this session;
 *     `chapters` are those English chapters (a payload of the login as much as of `/auth/me`);
 *   - WNS-08: `dismiss()` closes at once — before the server answers — and sends the POST once;
 *   - WNS-09: a failed POST is only logged: `dismiss()` neither throws nor rejects, nothing retries, and the popup stays
 *     closed for this session;
 *   - WNS-10: …and comes back on the next page load: the dismissal is not stored anywhere;
 *   - WNS-11: signing out resets it (`registerClientSessionReset('whatsNew', …)`): the next session — another account,
 *     or the same one again — is shown what its payload says;
 *   - WNS-12: reactive — read inside an effect (the arbiter of DeferredAppPopups reads it so), `shouldShow` and
 *     `chapters` follow the sign-in, the dismissal and the sign-out.
 * Every case that expects nothing to show also shows something with the same store, so a store that never shows
 * passes none of them.
 *
 * The REAL stores. A case is a page load: a freshly imported module graph (`vi.resetModules()` + `import()`, as
 * `instance/profile.test.ts` and `auth/openRegistrationNotice.test.ts` do) — the auth store, the client session, the
 * store under test and the rune helpers of the same graph —, so no case inherits a neighbour's session. The account is
 * set through the auth store's own seams: `checkAuth()` against a programmed `GET /auth/me`, `login()` against a
 * programmed login, `logout()`. `$lib/api` is mocked: the POST is matched by its URL, whatever name the generated client
 * gives the operation (FastAPI names it `<function>_api_v1_auth_whats_new_seen_post`); any other operation is an inert
 * spy, pending forever. The bundled changelog is a fixture: the real module imports CHANGELOG.md through `?raw`, which
 * the jsdom pipeline refuses. `$lib/debug` and the console are spies: a failure must be logged, and nothing printed.
 *
 * Written red-first, before `whatsNewStore.svelte.ts` exists: the store is loaded lazily through a glob, so every case
 * fails on its own, naming the missing module.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import type {ChangelogChapter} from './changelog';
import type {AuthUser} from '$lib/types';

const api = vi.hoisted(() => ({
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    /** `POST /api/v1/auth/whats-new/seen`, whatever the generated client calls it. */
    seen: vi.fn(),
}));

// `$lib/api`: the auth store's three operations, the POST of this lot matched by its URL — the generated alias
// (`…_api_v1_auth_whats_new_seen_post`) or a bare `post(url)` —, and an inert spy for any other operation a transitive
// import may touch, pending forever so that nothing it starts can settle behind the assertions or reach the network.
vi.mock('$lib/api', () => {
    const SEEN_ALIAS = /_api_v1_auth_whats_new_seen_post$/;
    const SEEN_URL = /\/api\/v1\/auth\/whats-new\/seen\/?$/;
    const programmed: Record<string, unknown> = {
        get_me_api_v1_auth_me_get: api.me,
        login_api_v1_auth_login_post: api.login,
        logout_api_v1_auth_logout_post: api.logout,
    };
    const inert = new Map<string, unknown>();
    const pending = () => new Promise(() => {});
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (operation in programmed) return programmed[operation];
                if (SEEN_ALIAS.test(operation)) return api.seen;
                if (operation === 'post') return (url: unknown, ...rest: unknown[]) => (typeof url === 'string' && SEEN_URL.test(url) ? api.seen(...rest) : pending());
                if (!inert.has(operation)) inert.set(operation, vi.fn(pending));
                return inert.get(operation);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

const logs = vi.hoisted(() => ({
    log: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    group: vi.fn(),
    groupEnd: vi.fn(),
    time: vi.fn(),
    timeEnd: vi.fn(),
}));

vi.mock('$lib/debug', () => ({debug: logs, isDebugEnabled: () => false}));

// The bundled changelog, newest first with the upcoming chapter on top: the real module's `?raw` import of the
// repository's CHANGELOG.md is refused by the jsdom pipeline.
const fixture = vi.hoisted(() => {
    const chapter = (version: string, date: string) => {
        const body = `- what changed in ${version}\n`;
        return {version, date, body, sections: [{title: null, body, subsections: []}]};
    };
    return {chapters: [chapter('Unreleased', ''), chapter('1.2.1', '2026-10-15'), chapter('1.2.0', '2026-10-14'), chapter('1.1.0', '2026-09-07'), chapter('1.0.0', '2026-07-20')]};
});

vi.mock('$lib/features/changelog/changelog', () => ({
    changelogChapters: fixture.chapters,
    CHANGELOG_REMOTE_URL: 'https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md',
    baseLanguage: (locale: string | null | undefined) => (locale ?? '').trim().toLowerCase().split(/[-_]/)[0] || 'en',
    localizedChangelog: {
        peek: () => fixture.chapters.map((c) => ({...c, lang: 'en'})),
        load: async () => fixture.chapters.map((c) => ({...c, lang: 'en'})),
    },
}));

// ---------------------------------------------------------------------------
// The store under test, in a page load of its own
// ---------------------------------------------------------------------------

interface WhatsNewStore {
    readonly shouldShow: boolean;
    readonly chapters: readonly ChangelogChapter[];
    dismiss(): unknown;
}

// A lazy glob rather than a literal import: the module does not exist yet, and a missing file must fail each case on its
// own, naming it, instead of failing the whole file at collection.
const STORE_MODULES = import.meta.glob<{whatsNew?: unknown}>('./whatsNewStore.svelte.ts');

async function importStore(): Promise<WhatsNewStore> {
    const load = STORE_MODULES['./whatsNewStore.svelte.ts'];
    if (!load) throw new Error('whatsNewStore.svelte.ts cannot be found next to this test (src/lib/features/changelog/): it should export `whatsNew` with shouldShow, chapters and dismiss()');
    const {whatsNew} = await load();
    if (typeof whatsNew !== 'object' || whatsNew === null) throw new Error('whatsNewStore.svelte.ts does not export `whatsNew`');
    const missing = ['shouldShow', 'chapters'].filter((name) => !(name in whatsNew));
    if (typeof (whatsNew as {dismiss?: unknown}).dismiss !== 'function') missing.push('dismiss()');
    if (missing.length > 0) throw new Error(`whatsNew does not expose ${missing.join(', ')}`);
    return whatsNew as WhatsNewStore;
}

/** The auth store of a page load that has just begun. */
async function freshAuth() {
    vi.resetModules();
    const {auth, getAuthState} = await import('$lib/stores/app/auth');
    return {auth, getAuthState};
}

/** A page load that has just begun: the auth store, the store under test — which reads that very auth store — and the rune helpers of the same graph. */
async function freshPageLoad() {
    const {auth, getAuthState} = await freshAuth();
    const whatsNew = await importStore();
    const runes = await import('$test/runes.svelte');
    const {flushSync} = await import('svelte');
    runes.assertEffectsRun();
    return {auth, getAuthState, whatsNew, flushSync, recordReads: runes.recordReads};
}

/** What the sign-in helpers need of a page load. */
type Page = Awaited<ReturnType<typeof freshAuth>>;

// ---------------------------------------------------------------------------
// Accounts, and the auth store's own seams
// ---------------------------------------------------------------------------

/** What the backend sends in the user payload: `null` when there is nothing to show. */
interface WhatsNewInfo {
    since: string | null;
    release: string;
}

/** The user of the login and of `/auth/me`, with this lot's field. */
type Account = AuthUser & {whats_new: WhatsNewInfo | null};

/** A range the fixture has chapters for: 1.2.1 and 1.2.0. */
const RANGE: WhatsNewInfo = {since: '1.1.0', release: '1.2.1'};

let nextId = 5400;

/** A new account each time: a sign-in after another account's is a new client session. */
function account(whatsNew: WhatsNewInfo | null): Account {
    const id = nextId++;
    return {id, username: `whats-new-${id}`, email: `whats-new-${id}@example.com`, is_active: true, is_superuser: false, created_at: '2026-10-17T00:00:00Z', whats_new: whatsNew};
}

/** Signs `user` in through `checkAuth()` against a programmed `GET /auth/me` (a page load of a signed-in browser). */
async function signIn(page: Page, user: Account): Promise<void> {
    api.me.mockResolvedValueOnce({user});
    expect(await page.auth.checkAuth(), 'premise: the auth store signed the account in').toBe('authenticated');
    expect(page.getAuthState().user?.id, 'premise: the account of this step is the one signed in').toBe(user.id);
}

/** Signs `user` in through `login()` against a programmed login. */
async function logIn(page: Page, user: Account): Promise<void> {
    api.login.mockResolvedValueOnce({user, user_settings: null, show_donation_popup: false});
    expect(await page.auth.login(user.username, 'password'), 'premise: the sign-in succeeds').toBe(true);
    expect(page.getAuthState().user?.id, 'premise: the account of this step is the one signed in').toBe(user.id);
}

async function signOut(page: Page): Promise<void> {
    await page.auth.logout();
    expect(page.getAuthState().user, 'premise: nobody is signed in').toBeNull();
}

/** The fixture's English chapter of `version`. */
function chapterOf(version: string): ChangelogChapter {
    const found = fixture.chapters.find((c) => c.version === version);
    if (!found) throw new Error(`the fixture has no chapter ${version}`);
    return found;
}

function versionsOf(chapters: readonly ChangelogChapter[]): string[] {
    return chapters.map((c) => c.version);
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((resolvePromise, rejectPromise) => {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return {promise, resolve, reject};
}

let consoleWarn: MockInstance<typeof console.warn>;
let consoleError: MockInstance<typeof console.error>;

/** Whether `error` was logged — through `$lib/debug` or the console —, as itself or by its message. */
function logged(error: Error): boolean {
    const calls: unknown[][] = [...Object.values(logs).flatMap((fn) => fn.mock.calls), ...consoleWarn.mock.calls, ...consoleError.mock.calls];
    return calls.some((args) => args.some((arg) => arg === error || (arg instanceof Error && arg.message === error.message) || (typeof arg === 'string' && arg.includes(error.message))));
}

beforeEach(() => {
    api.me.mockReset();
    api.login.mockReset();
    api.logout.mockReset().mockResolvedValue(undefined);
    api.seen.mockReset().mockResolvedValue(undefined);
    for (const fn of Object.values(logs)) fn.mockClear();
    consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
    consoleWarn.mockRestore();
    consoleError.mockRestore();
});

// ---------------------------------------------------------------------------
// The cases
// ---------------------------------------------------------------------------

describe('whatsNewStore — the premise', () => {
    // Not the store: the seam it reads. The store finds `whats_new` on the auth store's user, so that user must be the
    // payload as the backend sent it — through `/auth/me` and through the login. Green before the store exists, it also
    // proves this file's harness: a red below is the store's, not the sign-in's.
    it("WNS-00: the auth store keeps the payload's whats_new as the backend sends it, through /auth/me and through the login", async () => {
        const graph = await freshAuth();

        const viaMe = account(RANGE);
        await signIn(graph, viaMe);
        expect(graph.getAuthState().user, 'GET /auth/me').toEqual(viaMe);

        await signOut(graph);
        const viaLogin = account({since: null, release: '1.2.1'});
        await logIn(graph, viaLogin);
        expect(graph.getAuthState().user, 'the login').toEqual(viaLogin);
    });
});

describe('whatsNewStore — the module', () => {
    it('WNS-01: exports `whatsNew` with shouldShow, chapters and dismiss()', async () => {
        const {whatsNew} = await freshPageLoad();

        expect(typeof whatsNew.shouldShow).toBe('boolean');
        expect(Array.isArray(whatsNew.chapters)).toBe(true);
        expect(typeof whatsNew.dismiss).toBe('function');
    });
});

describe('whatsNewStore — when it shows', () => {
    it('WNS-02: nobody signed in → nothing to show; an account with something new, once signed in, is shown it', async () => {
        const page = await freshPageLoad();
        expect(page.getAuthState().user, 'premise: a page load, before any sign-in').toBeNull();

        expect(page.whatsNew.shouldShow).toBe(false);
        expect(page.whatsNew.chapters).toEqual([]);

        await signIn(page, account(RANGE));
        expect(page.whatsNew.shouldShow, 'control: the same store shows it once the account is in').toBe(true);
    });

    it('WNS-03: an account whose payload says whats_new: null → nothing to show', async () => {
        const page = await freshPageLoad();
        await signIn(page, account(null));

        expect(page.whatsNew.shouldShow).toBe(false);
        expect(page.whatsNew.chapters).toEqual([]);

        await signOut(page);
        await signIn(page, account(RANGE));
        expect(page.whatsNew.shouldShow, 'control: another account, with something new, is shown it').toBe(true);
    });

    it('WNS-04: since 1.1.0, release 1.2.1 → shown, with the English chapters released after 1.1.0 up to 1.2.1, newest first', async () => {
        const page = await freshPageLoad();
        await signIn(page, account({since: '1.1.0', release: '1.2.1'}));

        expect(page.whatsNew.shouldShow).toBe(true);
        expect(page.whatsNew.chapters).toEqual([chapterOf('1.2.1'), chapterOf('1.2.0')]);
    });

    it('WNS-05: since null (an account from before the feature), release 1.2.1 → shown, with the 1.2.1 chapter alone', async () => {
        const page = await freshPageLoad();
        await signIn(page, account({since: null, release: '1.2.1'}));

        expect(page.whatsNew.shouldShow).toBe(true);
        expect(page.whatsNew.chapters).toEqual([chapterOf('1.2.1')]);
    });

    it.each([
        ['nothing released since', {since: '1.2.1', release: '1.2.1'}],
        ['a downgrade', {since: '1.2.1', release: '1.2.0'}],
        ['a release the bundled changelog has no chapter for', {since: null, release: '9.9.9'}],
    ])('WNS-06: whats_new set, but no chapter to show (%s) → nothing to show', async (_label, whatsNew) => {
        const page = await freshPageLoad();
        await signIn(page, account(whatsNew));

        expect(page.whatsNew.shouldShow).toBe(false);
        expect(page.whatsNew.chapters).toEqual([]);

        await signOut(page);
        await signIn(page, account(RANGE));
        expect(page.whatsNew.shouldShow, 'control: an account with chapters to show is shown them').toBe(true);
    });

    it('WNS-07: the payload of the login carries it as much as the one of /auth/me', async () => {
        const page = await freshPageLoad();
        await logIn(page, account(RANGE));

        expect(page.whatsNew.shouldShow).toBe(true);
        expect(versionsOf(page.whatsNew.chapters)).toEqual(['1.2.1', '1.2.0']);
    });
});

describe('whatsNewStore — dismiss()', () => {
    it('WNS-08: closes at once, before the server answers, and sends POST /auth/whats-new/seen once', async () => {
        const page = await freshPageLoad();
        await signIn(page, account(RANGE));
        expect(page.whatsNew.shouldShow, 'premise: shown').toBe(true);
        const answer = deferred<unknown>();
        api.seen.mockImplementation(() => answer.promise);

        page.whatsNew.dismiss();

        expect(page.whatsNew.shouldShow, 'closed at once: nothing waits for the server').toBe(false);
        await vi.waitFor(() => expect(api.seen, 'POST /api/v1/auth/whats-new/seen').toHaveBeenCalledTimes(1));

        answer.resolve(undefined);
        await answer.promise;
        page.flushSync();
        expect(page.whatsNew.shouldShow, 'still closed once the server answered').toBe(false);
        expect(api.seen, 'one POST, never a second').toHaveBeenCalledTimes(1);
    });

    it('WNS-09: a failed POST is only logged — no throw, no rejection, no retry — and it stays closed for this session', async () => {
        const page = await freshPageLoad();
        await signIn(page, account(RANGE));
        expect(page.whatsNew.shouldShow, 'premise: shown').toBe(true);
        const failure = new Error('POST /api/v1/auth/whats-new/seen failed with 503 (whatsNewStore.test)');
        api.seen.mockRejectedValue(failure);

        let outcome: unknown;
        expect(() => {
            outcome = page.whatsNew.dismiss();
        }, 'dismiss() does not throw').not.toThrow();
        expect(page.whatsNew.shouldShow, 'closed at once').toBe(false);
        let rejection: unknown = null;
        await Promise.resolve(outcome).catch((reason: unknown) => {
            rejection = reason ?? 'rejected';
        });
        expect(rejection, 'what dismiss() returns, if anything, does not reject').toBeNull();

        await vi.waitFor(() => expect(logged(failure), 'the failure is logged, through $lib/debug or the console').toBe(true));
        page.flushSync();
        expect(page.whatsNew.shouldShow, 'still closed for this session').toBe(false);
        expect(api.seen, 'no retry').toHaveBeenCalledTimes(1);
    });

    it('WNS-10: the dismissal is not stored: after a failed POST, the next page load shows it again', async () => {
        const user = account(RANGE);
        const first = await freshPageLoad();
        await signIn(first, user);
        const failure = new Error('POST /api/v1/auth/whats-new/seen failed with 503 (whatsNewStore.test, first page)');
        api.seen.mockRejectedValue(failure);
        first.whatsNew.dismiss();
        expect(first.whatsNew.shouldShow, 'premise: dismissed on the first page').toBe(false);
        await vi.waitFor(() => expect(logged(failure), 'premise: the failure was handled').toBe(true));

        // The server never recorded it, so the same account's payload still says so on the next page load.
        const next = await freshPageLoad();
        await signIn(next, user);
        expect(next.whatsNew.shouldShow, 'shown again on the next page load').toBe(true);
        expect(versionsOf(next.whatsNew.chapters)).toEqual(['1.2.1', '1.2.0']);
    });
});

describe('whatsNewStore — a new session', () => {
    it.each([
        ['another account', false],
        ['the same account again (its POST failed, so the server still reports it)', true],
    ])('WNS-11: dismissed, then signed out — the sign-in of %s is shown what its payload says', async (_label, sameAccount) => {
        const page = await freshPageLoad();
        const first = account(RANGE);
        await signIn(page, first);
        if (sameAccount) api.seen.mockRejectedValue(new Error('POST /api/v1/auth/whats-new/seen failed with 503 (whatsNewStore.test)'));
        page.whatsNew.dismiss();
        expect(page.whatsNew.shouldShow, 'premise: dismissed in the first session').toBe(false);
        await vi.waitFor(() => expect(api.seen, 'premise: the POST of the first session was sent').toHaveBeenCalledTimes(1));

        await signOut(page);
        expect(page.whatsNew.shouldShow, 'nobody signed in').toBe(false);

        await signIn(page, sameAccount ? first : account(RANGE));
        expect(page.whatsNew.shouldShow, 'the dismissal of the previous session does not carry over').toBe(true);
    });

    it('WNS-12: reactive — read inside an effect, shouldShow and chapters follow the sign-in, the dismissal and the sign-out', async () => {
        const page = await freshPageLoad();
        const reads = page.recordReads(() => ({show: page.whatsNew.shouldShow, versions: versionsOf(page.whatsNew.chapters)}));
        try {
            expect(reads.values.at(-1), 'a page load, nobody signed in').toEqual({show: false, versions: []});

            await signIn(page, account(RANGE));
            page.flushSync();
            expect(reads.values.at(-1), 'signed in, with something new: the effect read it again').toEqual({show: true, versions: ['1.2.1', '1.2.0']});

            page.whatsNew.dismiss();
            page.flushSync();
            expect(reads.values.at(-1), 'dismissed: the effect read it again').toMatchObject({show: false});

            await signOut(page);
            page.flushSync();
            expect(reads.values.at(-1), 'signed out').toMatchObject({show: false});

            await signIn(page, account({since: null, release: '1.2.1'}));
            page.flushSync();
            expect(reads.values.at(-1), 'a new session, an account from before the feature').toEqual({show: true, versions: ['1.2.1']});

            expect(
                reads.values.filter((value) => value instanceof Error),
                'every read answered',
            ).toEqual([]);
        } finally {
            reads.stop();
        }
    });
});
