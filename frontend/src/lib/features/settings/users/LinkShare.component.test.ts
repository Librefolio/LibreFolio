// @vitest-environment jsdom
/**
 * LinkShare — component test (Vitest + jsdom). Accounts lot A6b, workstream A (plan A6b.1, «LinkShare»).
 *
 * The panel an administrator copies a one-time link from — an invitation, or a password reset. It shows the address
 * the link starts with: the public address of the instance when the server knows it (`LIBREFOLIO_PUBLIC_URL`, that is
 * a `url` that ends with `path`), otherwise the address this page was opened at. The administrator may correct that
 * address; the panel then checks, in the background, that this very instance answers there, and copies the link
 * whatever the verdict (decision D-A3): a mismatch is information, not a lock.
 *
 * File name. `LinkShare.component.test.ts`, not `LinkShare.test.ts`: the plan's pure lot (V1, `core-unit`) names
 * `linkShare.test.ts` for `./linkShare.ts` in this same folder, and on a case-insensitive volume — macOS APFS, the
 * default — the two names are one and the same file.
 *
 * The contract (A6b.1):
 *   - props `{purpose, path, url, expiresAt, context?}`; root `link-share` with `data-purpose`;
 *   - `link-share-address` (editable) holds `initialBase(url, path, window.location.origin)`; `link-share-link`
 *     (readonly) holds `composeLink(normalized address, path)`; `link-share-expires` shows the expiry;
 *   - the probe runs only when the normalized address differs from the initial one, 500 ms after the last keystroke:
 *     `zodiosApi.issue_address_probe_api_v1_users_address_probe_post()` for a nonce, then `checkAddress` through the
 *     global `fetch` — `GET <base>/api/v1/auth/address-probe?nonce=…`, a CORS simple request: no headers, no
 *     credentials; `link-share-probe` publishes `data-state` ∈ idle | checking | match | mismatch | unverifiable |
 *     invalid; back to the initial address → idle; an address `normalizeBase` refuses → invalid, and `link-share-copy`
 *     disabled; every other state can copy;
 *   - each verdict is notified as `accounts.address.checked` `{state}`, without a toast;
 *   - `link-share-copy` writes the link through `writeTextToClipboard` (`$lib/utils/clipboard`, the only transport
 *     `clipboardSink.gate.test.ts` allows) and notifies `accounts.link.copied` `{purpose}` with a success toast; when
 *     no copy is possible the link input is selected instead, for the user to copy by hand;
 *   - `link-share-actions` draws every visible `LINK_SHARE_ACTIONS` entry as `<component link purpose context />`.
 *
 * Held still:
 *   - the clock, in every case that types into the address: `vi.useFakeTimers()` before the mount, and
 *     `advanceTimersByTimeAsync` to reach the debounce. Its async form fires the due timers and then yields one real
 *     macrotask, so the promise chain a timer starts (nonce, fetch, verdict, Svelte's microtask flush) has settled when
 *     it returns. `waitFor` is never used on a frozen clock: its own interval is a faked timer, so it would hang
 *     instead of failing;
 *   - `fetch`, stubbed with `vi.stubGlobal` (the contract has `checkAddress` read `globalThis.fetch` at call time).
 *     Every call stays pending until the case answers it — `askedAt(base)` finds it by address, never by position —
 *     and, like a real fetch, rejects with an `AbortError` when its signal aborts, so an implementation that aborts a
 *     superseded request is held to the same "no stale verdict" as one that only ignores it. Answers are real
 *     `Response` objects: their body is read through microtasks only (undici closes the stream with `queueMicrotask`,
 *     which Vitest never fakes), so the frozen clock cannot stall them;
 *   - the nonce endpoint, through the `$lib/api` Proxy mock (each alias a lazily created `vi.fn`);
 *   - the browser clipboard surface — `navigator.clipboard`, `window.isSecureContext`, `document.execCommand` —
 *     defined per case and put back exactly as jsdom had it (it has none of the three), as `clipboard.test.ts` does.
 *     The helper itself is the real one: the case observes what reaches the browser;
 *   - the registry: entries are pushed into the real `LINK_SHARE_ACTIONS` and the array is put back after each case.
 *     Each entry is `SettingsTabProbe` (`src/__tests__/harness`) wrapped as a component, the technique of
 *     `routes/(app)/settings/page.tabs.test.ts`: the probe publishes the props it was drawn with in `data-received`;
 *   - `$lib/i18n`, an identity translator: labels render as their key, and nothing here reads a label anyway.
 *
 * Not asserted: the probe's own ladder (non-2xx, invalid JSON, a non-boolean `match`, the 8 s timeout) and the exact
 * `init` beyond headers and credentials — `addressProbe.test.ts` (V1) owns them; `initialBase`/`composeLink` edge
 * cases — `linkShare.test.ts` (V1); the state shown *during* the debounce window, which the contract leaves open; the
 * wording and format of `link-share-expires`, which publishes no machine-readable value.
 *
 * Red today: `./LinkShare.svelte` and `./linkShareActions` do not exist (nor does the `users/` folder), so the import
 * fails and every case is red on that.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import SettingsTabProbe from '$test/harness/SettingsTabProbe.svelte';

// --- Mocks --------------------------------------------------------------

// The identity translator: a label renders as its own key, in no language at all.
vi.mock('$lib/i18n', () => {
    const identity = readable((key: string) => key);
    return {
        _: identity,
        t: identity,
        locale: writable('en'),
        date: readable((v: unknown) => String(v)),
        time: readable((v: unknown) => String(v)),
        number: readable((v: unknown) => String(v)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it', 'fr', 'es'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT', fr: 'FR', es: 'ES'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

// The language dates are written in (`formatDateTime` → `uiLocale` → `currentLanguage`), held at English.
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));

vi.mock('$lib/api', () => {
    const cache = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

const notify = vi.fn();
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: (...args: unknown[]) => notify(...args)}));

import LinkShare from './LinkShare.svelte';
import {LINK_SHARE_ACTIONS} from './linkShareActions';
import {zodiosApi} from '$lib/api';

// --- Fixtures -----------------------------------------------------------

type Purpose = 'invite' | 'password_reset';

interface LinkShareProps {
    purpose: Purpose;
    path: string;
    url: string | null;
    expiresAt: string;
    context?: {username?: string; email?: string | null; userId?: number};
}

/** Where the instance says it lives (`LIBREFOLIO_PUBLIC_URL`), behind a reverse proxy's sub-path: a prefix to keep. */
const PUBLIC_BASE = 'https://lf.example/librefolio';
/** The paths the server returns: the page that takes the token, the token in the fragment (`token_service.token_path`). */
const INVITE_PATH = '/invite#token=aW52aXRlLXRva2Vu';
const RESET_PATH = '/reset-password#token=cmVzZXQtdG9rZW4';
const INVITE_URL = `${PUBLIC_BASE}${INVITE_PATH}`;
const RESET_URL = `${PUBLIC_BASE}${RESET_PATH}`;
const EXPIRES_AT = '2026-10-22T15:00:00Z';
const INVITE_CONTEXT = {email: 'dave@example.com'};
const RESET_CONTEXT = {username: 'carol', email: 'carol@example.com', userId: 7};

const INVITE_PROPS: LinkShareProps = {purpose: 'invite', path: INVITE_PATH, url: INVITE_URL, expiresAt: EXPIRES_AT, context: INVITE_CONTEXT};
const RESET_PROPS: LinkShareProps = {purpose: 'password_reset', path: RESET_PATH, url: RESET_URL, expiresAt: EXPIRES_AT, context: RESET_CONTEXT};

/** Addresses the administrator types instead of the public one. Each has a path prefix of its own. */
const OTHER_BASE = 'https://other.example/lf';
const FIRST_BASE = 'https://first.example/lf';
const SECOND_BASE = 'https://second.example/lf';

const PROBE_PATH = '/api/v1/auth/address-probe';
/** A nonce with characters a query string must encode, and what it must look like once encoded. */
const NONCE = 'n0nce+/=';
const NONCE_IN_URL = 'n0nce%2B%2F%3D';

const issued = (nonce: string) => ({nonce, expires_at: '2026-10-15T15:05:00Z'});

/** The nonce endpoint, as the Proxy mock hands it out. */
const issueNonce = () => vi.mocked(zodiosApi.issue_address_probe_api_v1_users_address_probe_post as never) as ReturnType<typeof vi.fn>;

/** A refusal from our own API, axios-shaped. */
function apiRefusal(status: number): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, name: 'AxiosError', response: {status, data: {detail: 'Not allowed'}}});
}

// --- fetch: every request stays pending until the case answers it --------

interface Asked {
    url: string;
    init: RequestInit | undefined;
    resolve: (answer: Response) => void;
    reject: (reason: unknown) => void;
}

/** Every request the stub received, in the order received. */
const asked: Asked[] = [];

const abortError = () => new DOMException('The operation was aborted.', 'AbortError');

const fetchStub = vi.fn(
    (input: string | URL | Request, init?: RequestInit): Promise<Response> =>
        new Promise<Response>((resolve, reject) => {
            asked.push({url: String(input), init, resolve, reject});
            // A real fetch gives up on an aborted signal: so does this one.
            if (init?.signal?.aborted) {
                reject(abortError());
                return;
            }
            init?.signal?.addEventListener('abort', () => reject(abortError()), {once: true});
        }),
);

/** The one probe request made for `base`; fails loudly when there is none, or more than one. */
function askedAt(base: string): Asked {
    const hits = asked.filter((entry) => entry.url.startsWith(`${base}${PROBE_PATH}?`));
    if (hits.length !== 1) throw new Error(`expected exactly one probe of ${base}, found ${hits.length} among: ${asked.map((entry) => entry.url).join(', ') || 'none'}`);
    return hits[0];
}

/** A 200 answer of the probe endpoint: a real `Response`, as `fetch` resolves with. */
function probeAnswer(match: boolean): Response {
    return new Response(JSON.stringify({match}), {status: 200, headers: {'content-type': 'application/json'}});
}

// --- The clipboard surface: defined per case, put back as jsdom had it ---

const ORIGINAL_SURFACE = [
    {target: navigator, key: 'clipboard', descriptor: Object.getOwnPropertyDescriptor(navigator, 'clipboard')},
    {target: window, key: 'isSecureContext', descriptor: Object.getOwnPropertyDescriptor(window, 'isSecureContext')},
    {target: document, key: 'execCommand', descriptor: Object.getOwnPropertyDescriptor(document, 'execCommand')},
] as const;

function restoreClipboardSurface(): void {
    for (const {target, key, descriptor} of ORIGINAL_SURFACE) {
        if (descriptor) Object.defineProperty(target, key, descriptor);
        else Reflect.deleteProperty(target, key);
    }
}

function setClipboard(writeText?: (text: string) => Promise<void>): void {
    Object.defineProperty(navigator, 'clipboard', {value: writeText ? {writeText} : undefined, configurable: true, writable: true});
}

function setSecureContext(value: boolean): void {
    Object.defineProperty(window, 'isSecureContext', {value, configurable: true, writable: true});
}

function setExecCommand(fn?: (command: string) => boolean): void {
    Object.defineProperty(document, 'execCommand', {value: fn, configurable: true, writable: true});
}

// --- The registry -------------------------------------------------------

type LinkShareAction = (typeof LINK_SHARE_ACTIONS)[number];

/** What the registry held before this file touched it: put back after every case. */
const ORIGINAL_ACTIONS = [...LINK_SHARE_ACTIONS];

/**
 * A registry action that is `SettingsTabProbe`, told its name. A Svelte 5 component is a function of an anchor and a
 * props object, so this one mounts the probe in its place and hands it the props object LinkShare drew it with,
 * through a getter so it stays live: the probe publishes those props as JSON in `data-received`.
 */
function probeAction(name: string): LinkShareAction['component'] {
    const mountProbe = SettingsTabProbe as unknown as (anchor: unknown, props: object) => unknown;
    return ((anchor: unknown, props: Record<string, unknown>) =>
        mountProbe(anchor, {
            probe: name,
            get received() {
                return props;
            },
        })) as unknown as LinkShareAction['component'];
}

/** The probe of the action named `name` under `root`, or null when it is drawn nowhere under it. */
function actionNamed(name: string, root: HTMLElement = document.body): HTMLElement | null {
    return (
        within(root)
            .queryAllByTestId('settings-tab-probe')
            .find((element) => element.getAttribute('data-probe') === name) ?? null
    );
}

/** The props an action was drawn with, as its probe publishes them. */
function receivedBy(probe: HTMLElement | null): Record<string, unknown> {
    if (!probe) throw new Error('the action is not drawn');
    return JSON.parse(probe.getAttribute('data-received') ?? 'null') as Record<string, unknown>;
}

// --- Helpers ------------------------------------------------------------

interface Notified {
    name: string;
    detail?: Record<string, unknown>;
    toast?: {variant: string; message: string; duration?: number};
}

/** Every notification of `name`, in order. */
function notified(name: string): Notified[] {
    return notify.mock.calls.map(([options]) => options as Notified).filter((options) => options.name === name);
}

/** The verdicts notified so far, in order. */
const checkedStates = () => notified('accounts.address.checked').map((event) => event.detail?.state);

function mountLinkShare(props: LinkShareProps = INVITE_PROPS) {
    return render(LinkShare, {props: {...props, context: props.context && {...props.context}}});
}

const root = () => screen.getByTestId('link-share');
const address = () => screen.getByTestId('link-share-address') as HTMLInputElement;
const link = () => screen.getByTestId('link-share-link') as HTMLInputElement;
const probeState = () => screen.getByTestId('link-share-probe').getAttribute('data-state');
const copyButton = () => screen.getByTestId('link-share-copy');

/** Types `value` into the address field, as one keystroke that leaves it holding `value`. */
async function typeAddress(value: string): Promise<void> {
    await fireEvent.input(address(), {target: {value}});
}

/** Moves the frozen clock by `ms`; what the elapsed timers start settles before it returns. */
const elapse = (ms: number) => vi.advanceTimersByTimeAsync(ms);

/** Lets the answers a case just gave propagate, without moving the clock: one real macrotask, every microtask first. */
const settle = () => vi.advanceTimersByTimeAsync(0);

// --- Lifecycle ----------------------------------------------------------

beforeAll(async () => {
    // Only a component importing svelte-i18n directly would need it: `$lib/i18n` is mocked above.
    await setupI18n();
});

beforeEach(() => {
    vi.clearAllMocks();
    asked.length = 0;
    issueNonce().mockReset();
    issueNonce().mockResolvedValue(issued(NONCE));
    vi.stubGlobal('fetch', fetchStub);
    // jsdom has no clipboard surface at all; each case that copies says which one it has.
    setClipboard(undefined);
    setSecureContext(true);
    setExecCommand(undefined);
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    restoreClipboardSurface();
    LINK_SHARE_ACTIONS.splice(0, LINK_SHARE_ACTIONS.length, ...ORIGINAL_ACTIONS);
});

// --- The address it starts from -------------------------------------------

describe('LinkShare — the address it starts from', () => {
    it('LSH-C-01: starts from the public address the server returned — its url minus the path, the path prefix kept — and asks nothing', () => {
        mountLinkShare();

        expect(root()).toHaveAttribute('data-purpose', 'invite');
        expect(address().value).toBe(PUBLIC_BASE);
        expect(address()).not.toHaveAttribute('readonly');
        expect(link().value).toBe(INVITE_URL);
        expect(link()).toHaveAttribute('readonly');
        expect(probeState()).toBe('idle');
        expect(copyButton()).toBeEnabled();
        expect(screen.getByTestId('link-share-expires')).toBeInTheDocument();
        expect(issueNonce()).not.toHaveBeenCalled();
        expect(fetchStub).not.toHaveBeenCalled();
    });

    it.each([
        {why: 'the server knows no public address (url is null)', url: null},
        {why: 'the url the server returned does not end with the path', url: 'https://elsewhere.example/'},
    ])('LSH-C-02: starts from the address this page was opened at when $why', ({url}) => {
        mountLinkShare({...RESET_PROPS, url});
        const origin = window.location.origin;

        expect(root()).toHaveAttribute('data-purpose', 'password_reset');
        expect(address().value).toBe(origin);
        expect(link().value).toBe(`${origin}${RESET_PATH}`);
        expect(probeState()).toBe('idle');
    });
});

// --- The address check ------------------------------------------------------

describe('LinkShare — checking a corrected address', () => {
    it('LSH-C-03: asks nothing until 500 ms after the last keystroke, then asks once, for the last address only', async () => {
        vi.useFakeTimers();
        mountLinkShare();

        await typeAddress(FIRST_BASE);
        await elapse(300);
        await typeAddress(SECOND_BASE);
        // 799 ms after the first keystroke, 499 after the last: the first one's check must have been called off.
        await elapse(499);
        expect(issueNonce()).not.toHaveBeenCalled();
        expect(fetchStub).not.toHaveBeenCalled();

        await elapse(1);
        expect(issueNonce()).toHaveBeenCalledTimes(1);
        expect(fetchStub).toHaveBeenCalledTimes(1);
        expect(askedAt(SECOND_BASE).url).toBe(`${SECOND_BASE}${PROBE_PATH}?nonce=${NONCE_IN_URL}`);
        expect(asked.filter((entry) => entry.url.startsWith(FIRST_BASE))).toEqual([]);
    });

    it('LSH-C-04: the link follows the address at once; once asked, the probe is checking — a credential-less, header-less GET of the normalized address', async () => {
        vi.useFakeTimers();
        mountLinkShare();

        // A trailing slash, as people type it: the link and the probe both use the normalized address.
        await typeAddress(`${OTHER_BASE}/`);
        // Not debounced: what the user would copy right now is the link of what they typed.
        expect(link().value).toBe(`${OTHER_BASE}${INVITE_PATH}`);

        await elapse(500);
        expect(probeState()).toBe('checking');
        expect(issueNonce()).toHaveBeenCalledTimes(1);

        const request = askedAt(OTHER_BASE);
        expect(request.url).toBe(`${OTHER_BASE}${PROBE_PATH}?nonce=${NONCE_IN_URL}`);
        // A CORS simple request to a foreign origin: no cookie goes with it, and no header that would need a preflight.
        expect(request.init).toEqual(expect.objectContaining({credentials: 'omit'}));
        expect(request.init).not.toHaveProperty('headers');
    });

    it.each([
        {verdict: 'match', answer: (request: Asked) => request.resolve(probeAnswer(true))},
        {verdict: 'mismatch', answer: (request: Asked) => request.resolve(probeAnswer(false))},
        // What a browser gives for a CORS refusal, a closed port or mixed content alike.
        {verdict: 'unverifiable', answer: (request: Asked) => request.reject(new TypeError('Failed to fetch'))},
    ])('LSH-C-05: an answer that means $verdict shows $verdict, is notified as accounts.address.checked without a toast, and leaves the link copyable', async ({verdict, answer}) => {
        vi.useFakeTimers();
        mountLinkShare();

        await typeAddress(OTHER_BASE);
        await elapse(500);
        expect(probeState()).toBe('checking');

        answer(askedAt(OTHER_BASE));
        await settle();

        expect(probeState()).toBe(verdict);
        const checked = notified('accounts.address.checked');
        expect(checked).toHaveLength(1);
        expect(checked[0].detail).toEqual(expect.objectContaining({state: verdict}));
        expect(checked[0].toast).toBeUndefined();
        expect(copyButton()).toBeEnabled();
    });

    it('LSH-C-06: a nonce our own server refuses makes the address unverifiable, and nothing is fetched from it', async () => {
        vi.useFakeTimers();
        issueNonce().mockRejectedValueOnce(apiRefusal(403));
        mountLinkShare();

        await typeAddress(OTHER_BASE);
        await elapse(500);
        await settle();

        // The check did run: it asked for its nonce.
        expect(issueNonce()).toHaveBeenCalledTimes(1);
        expect(probeState()).toBe('unverifiable');
        expect(fetchStub).not.toHaveBeenCalled();
        expect(checkedStates()).toEqual(['unverifiable']);
    });

    it('LSH-C-07: back to the initial address after a verdict, the probe is idle again and nothing new is asked', async () => {
        vi.useFakeTimers();
        mountLinkShare();

        await typeAddress(OTHER_BASE);
        await elapse(500);
        askedAt(OTHER_BASE).resolve(probeAnswer(false));
        await settle();
        expect(probeState()).toBe('mismatch');

        // The initial address as typed by hand, trailing slash included: equal once normalized.
        await typeAddress(`${PUBLIC_BASE}/`);
        await elapse(1_000);

        expect(probeState()).toBe('idle');
        expect(link().value).toBe(INVITE_URL);
        expect(issueNonce()).toHaveBeenCalledTimes(1);
        expect(fetchStub).toHaveBeenCalledTimes(1);
    });

    it('LSH-C-08: an address changed and changed back within the debounce is never asked about — while a new one still is', async () => {
        vi.useFakeTimers();
        mountLinkShare();

        await typeAddress(OTHER_BASE);
        await elapse(200);
        await typeAddress(PUBLIC_BASE);
        await elapse(1_000);

        expect(probeState()).toBe('idle');
        expect(issueNonce()).not.toHaveBeenCalled();
        expect(fetchStub).not.toHaveBeenCalled();

        // The silence above is the debounce, not a dead probe.
        await typeAddress(SECOND_BASE);
        await elapse(500);
        expect(issueNonce()).toHaveBeenCalledTimes(1);
        expect(askedAt(SECOND_BASE).init).toEqual(expect.objectContaining({credentials: 'omit'}));
    });

    it('LSH-C-09: an address that is not an http(s) base is invalid: nothing is asked and the link cannot be copied — until the address is valid again', async () => {
        vi.useFakeTimers();
        mountLinkShare();
        expect(copyButton()).toBeEnabled();

        await typeAddress('ftp://x');
        await elapse(1_000);

        expect(probeState()).toBe('invalid');
        expect(copyButton()).toBeDisabled();
        expect(issueNonce()).not.toHaveBeenCalled();
        expect(fetchStub).not.toHaveBeenCalled();

        await typeAddress(OTHER_BASE);
        await elapse(500);
        expect(probeState()).toBe('checking');
        expect(copyButton()).toBeEnabled();
        expect(askedAt(OTHER_BASE).url).toBe(`${OTHER_BASE}${PROBE_PATH}?nonce=${NONCE_IN_URL}`);
    });

    it.each([
        {order: 'the older answer lands first', olderFirst: true},
        {order: 'the older answer lands last', olderFirst: false},
    ])('LSH-C-10: a newer address supersedes a pending check — $order — and no stale verdict is shown or notified', async ({olderFirst}) => {
        vi.useFakeTimers();
        issueNonce().mockResolvedValueOnce(issued('nonce-older')).mockResolvedValueOnce(issued('nonce-newer'));
        mountLinkShare();

        await typeAddress(OTHER_BASE);
        await elapse(500);
        const older = askedAt(OTHER_BASE);
        await typeAddress(SECOND_BASE);
        await elapse(500);
        const newer = askedAt(SECOND_BASE);
        expect(newer.url).toBe(`${SECOND_BASE}${PROBE_PATH}?nonce=nonce-newer`);

        if (olderFirst) {
            older.resolve(probeAnswer(true));
            await settle();
            // The address on screen is still being checked: the older verdict is about another one.
            expect(probeState()).toBe('checking');
            expect(checkedStates()).toEqual([]);

            newer.resolve(probeAnswer(false));
            await settle();
        } else {
            newer.resolve(probeAnswer(false));
            await settle();
            expect(probeState()).toBe('mismatch');

            older.resolve(probeAnswer(true));
            await settle();
        }

        expect(probeState()).toBe('mismatch');
        expect(checkedStates()).toEqual(['mismatch']);
    });
});

// --- Copying ----------------------------------------------------------------

describe('LinkShare — copying the link', () => {
    it.each([
        {purpose: 'invite', props: INVITE_PROPS, expected: INVITE_URL},
        {purpose: 'password_reset', props: RESET_PROPS, expected: RESET_URL},
    ])('LSH-C-11: copy writes the whole $purpose link to the clipboard and announces accounts.link.copied with a success toast', async ({purpose, props, expected}) => {
        const writeText = vi.fn(async (_text: string) => undefined);
        setClipboard(writeText);
        setSecureContext(true);
        mountLinkShare(props);

        await fireEvent.click(copyButton());
        await waitFor(() => expect(notified('accounts.link.copied')).toHaveLength(1));

        expect(writeText).toHaveBeenCalledTimes(1);
        expect(writeText).toHaveBeenCalledWith(expected);
        const [copied] = notified('accounts.link.copied');
        expect(copied.detail).toEqual(expect.objectContaining({purpose}));
        expect(copied.toast).toEqual(expect.objectContaining({variant: 'success', message: expect.any(String)}));
    });

    it('LSH-C-12: a mismatch does not lock the link (D-A3): copy writes the link of the address on screen', async () => {
        const writeText = vi.fn(async (_text: string) => undefined);
        setClipboard(writeText);
        setSecureContext(true);
        vi.useFakeTimers();
        mountLinkShare();

        await typeAddress(OTHER_BASE);
        await elapse(500);
        askedAt(OTHER_BASE).resolve(probeAnswer(false));
        await settle();
        expect(probeState()).toBe('mismatch');

        await fireEvent.click(copyButton());
        await settle();

        expect(writeText).toHaveBeenCalledWith(`${OTHER_BASE}${INVITE_PATH}`);
        expect(notified('accounts.link.copied')).toHaveLength(1);
    });

    it('LSH-C-13: with no clipboard API (plain HTTP) and the legacy copy refused, the link input is focused and wholly selected, nothing throws, and no copy is announced', async () => {
        // A LAN address over plain HTTP: not a secure context, so no navigator.clipboard; and no execCommand('copy').
        setClipboard(undefined);
        setSecureContext(false);
        setExecCommand(undefined);
        mountLinkShare();

        // An exception in an event handler reaches window as an `error` event: collect them to assert there are none.
        const thrown: unknown[] = [];
        const onError = (event: ErrorEvent) => thrown.push(event.error ?? event.message);
        window.addEventListener('error', onError);
        try {
            await fireEvent.click(copyButton());

            // Focused as well as selected: a selection in an unfocused field is not what Ctrl+C copies.
            await waitFor(() => expect(document.activeElement).toBe(link()));
            expect(link().selectionStart).toBe(0);
            expect(link().selectionEnd).toBe(INVITE_URL.length);
            expect(thrown).toEqual([]);
            // Nothing reached the clipboard: a "copied" success would tell the user the opposite of what happened.
            expect(notified('accounts.link.copied')).toEqual([]);
        } finally {
            window.removeEventListener('error', onError);
        }
    });
});

// --- The actions registry -------------------------------------------------

describe('LinkShare — the actions registry (LINK_SHARE_ACTIONS)', () => {
    it.each([
        {purpose: 'invite', props: INVITE_PROPS},
        {purpose: 'password_reset', props: RESET_PROPS},
    ])('LSH-C-14: an action without `visible` is drawn inside link-share-actions for $purpose, with the link, the purpose and the context', ({props}) => {
        LINK_SHARE_ACTIONS.push({id: 'test-always', component: probeAction('always')});
        mountLinkShare(props);

        const drawn = actionNamed('always', screen.getByTestId('link-share-actions'));
        expect(drawn).not.toBeNull();
        expect(receivedBy(drawn)).toEqual(expect.objectContaining({link: `${PUBLIC_BASE}${props.path}`, purpose: props.purpose, context: props.context}));
    });

    it('LSH-C-15: an action whose `visible` says no is not drawn, while one it allows is; `visible` is asked with the purpose and the context', () => {
        const visible = vi.fn((ctx: {purpose: string}) => ctx.purpose === 'invite');
        LINK_SHARE_ACTIONS.push({id: 'test-always', component: probeAction('always')}, {id: 'test-invite-only', component: probeAction('invite-only'), visible});

        mountLinkShare(RESET_PROPS);
        // Actions are drawn here — so the missing one is refused, not merely late.
        expect(actionNamed('always', screen.getByTestId('link-share-actions'))).not.toBeNull();
        expect(actionNamed('invite-only')).toBeNull();
        expect(visible).toHaveBeenCalledWith(expect.objectContaining({purpose: 'password_reset', context: RESET_CONTEXT}));

        cleanup();
        mountLinkShare(INVITE_PROPS);
        expect(actionNamed('invite-only', screen.getByTestId('link-share-actions'))).not.toBeNull();
        expect(visible).toHaveBeenCalledWith(expect.objectContaining({purpose: 'invite', context: INVITE_CONTEXT}));
    });

    it('LSH-C-16: an action is handed the link of the address on screen, not the one the panel opened with', async () => {
        LINK_SHARE_ACTIONS.push({id: 'test-always', component: probeAction('always')});
        vi.useFakeTimers();
        mountLinkShare();
        expect(receivedBy(actionNamed('always')).link).toBe(INVITE_URL);

        await typeAddress(`${OTHER_BASE}/`);

        expect(receivedBy(actionNamed('always', screen.getByTestId('link-share-actions'))).link).toBe(`${OTHER_BASE}${INVITE_PATH}`);
    });
});
