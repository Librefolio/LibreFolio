// @vitest-environment node
/**
 * cspNotice — the notice of a script the browser blocked and the instance did not send (H-55 v2, step 4).
 *
 * The enforced Content-Security-Policy blocks a script nobody of this instance sent: a proxy that injects one, a CDN
 * that rewrites the page, a browser extension. The page keeps working without it, and nobody would ever learn that it
 * was refused. `cspNotice.ts` makes it visible, in the place a developer or an administrator looks first, and nowhere
 * else: one line of the browser console, and a note in the tab's `sessionStorage` that the Security tab of Settings
 * reads (`platform.blockedScript`). No report endpoint, no request of any kind: the browser's report never leaves it.
 *
 * Where the violations come from, in the order a page meets them:
 *   - `window.__lfCspViolations`, an array `app.html` starts in its head, before any bundle loads, with a listener of
 *     `securitypolicyviolation` that pushes `{directive, blockedURI, sample, sourceFile}` for each ENFORCED violation
 *     (`cspEarlyListener.gate.test.ts` reads that half): the module drains it first;
 *   - the listener of its own, for what comes next — `securitypolicyviolation` events, whose `disposition` says whether
 *     the policy blocked (`enforce`) or only reported (`report`: the managed profile's report-only policy, which this
 *     notice is not about);
 *   - where the browser has one, a `ReportingObserver` of `csp-violation` reports, `buffered: true`, so a violation that
 *     came before the module started is delivered too.
 *
 * The contract under test, `startCspNotice({win?, storage?, log?})` and `KNOWN_CSP_VIOLATIONS`:
 *   - `win` is the window (`window`), `storage` the `sessionStorage` (`win.sessionStorage`), `log` the console's `error`
 *     (`console.error`). Everything is injected here: no case touches a real browser object;
 *   - `KNOWN_CSP_VIOLATIONS` holds cheetah-grid's probe of the global object (`new Function("return this")()`, in a
 *     try/catch that falls back to `window`): `script-src`, `eval`, the sample Chromium gives it. It is never reported,
 *     whichever way it arrives — the buffer, the listener or the observer. Any other eval is;
 *   - any other enforced violation is reported ONCE per page load, whichever way it arrives and however many there are,
 *     as `log(text)` with the text
 *     `LibreFolio blocked a script it did not send (<source>): a proxy, a CDN or a browser extension adds it. Guide: <docs>/admin/configuration/#csp`,
 *     `<source>` being the origin of the blocked address (`https://cdn.example.com`), or `inline`, or `eval`;
 *   - every distinct source, the first included, is added once to `sessionStorage['librefolio-csp-blocked']`, a JSON
 *     array of distinct strings, what is already there kept;
 *   - a storage that throws, or holds what is no JSON array, never throws through the module: the line is logged all the
 *     same.
 *
 * Fakes, all owned here: a window made of two event targets (the document, and the window the event bubbles to: a
 * listener of either is reached once), a `ReportingObserver` class that records how it was built, a storage over a Map,
 * a `log` spy. The module is loaded again for every page load (`vi.resetModules`), so that neither a flag nor a count it
 * keeps for the page can leak from one case into the next. The network is a failing stub in every case: nothing here
 * waits on the clock, and nothing may be sent.
 *
 * Red today: `cspNotice.ts` does not exist. It is loaded by a computed specifier, so each case fails on its own with the
 * contract in its message.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';

const MODULE = './cspNotice';

/** The probe of cheetah-grid's bundle, as Chromium reports it: the source the Function constructor builds, 39 characters. */
const GLOBAL_PROBE_SAMPLE = '(function anonymous(\n) {\nreturn this\n})';
const STORAGE_KEY = 'librefolio-csp-blocked';
const CDN = 'https://cdn.example.com';
const CDN_SCRIPT = `${CDN}/lib/inject.js?v=3#top`;

/** A violation as `app.html`'s early listener buffers it. */
interface Buffered {
    directive: string;
    blockedURI: string;
    sample: string;
    sourceFile: string;
}

interface NoticeModule {
    startCspNotice(options?: {win?: unknown; storage?: unknown; log?: (message: string) => void}): unknown;
    KNOWN_CSP_VIOLATIONS: ReadonlyArray<{directive: string; blockedURI: string; sample: string}>;
}

/** The module for one page load: loaded again, so that a flag it keeps for the page is not the previous case's. */
async function load(): Promise<NoticeModule> {
    vi.resetModules();
    let loaded: Record<string, unknown>;
    try {
        loaded = (await import(/* @vite-ignore */ MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/features/security/cspNotice.ts cannot be loaded (red until H-55 v2 step 4: it does not exist yet), so a script the policy blocks is never made visible — ${String(error)}`, {cause: error});
    }
    expect(typeof loaded.startCspNotice, 'cspNotice.ts exports startCspNotice()').toBe('function');
    expect(Array.isArray(loaded.KNOWN_CSP_VIOLATIONS), 'cspNotice.ts exports KNOWN_CSP_VIOLATIONS, an array').toBe(true);
    return loaded as unknown as NoticeModule;
}

// --- The fakes ---------------------------------------------------------------------------------------------------------

type Listener = (event: unknown) => void;

class FakeTarget {
    readonly listeners = new Map<string, Listener[]>();
    addEventListener(type: string, listener: Listener): void {
        this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
    }
    removeEventListener(type: string, listener: Listener): void {
        this.listeners.set(
            type,
            (this.listeners.get(type) ?? []).filter((candidate) => candidate !== listener),
        );
    }
    dispatch(type: string, event: unknown): void {
        for (const listener of [...(this.listeners.get(type) ?? [])]) listener(event);
    }
}

/** A `ReportingObserver` that records how it was built and lets the case deliver reports. */
class FakeReportingObserver {
    static instances: FakeReportingObserver[] = [];
    observing = false;
    constructor(
        readonly callback: (reports: unknown[], observer: FakeReportingObserver) => void,
        readonly options: unknown,
    ) {
        FakeReportingObserver.instances.push(this);
    }
    observe(): void {
        this.observing = true;
    }
    disconnect(): void {
        this.observing = false;
    }
    takeRecords(): unknown[] {
        return [];
    }
    deliver(...reports: unknown[]): void {
        this.callback(reports, this);
    }
}

interface FakeWindow {
    __lfCspViolations?: Buffered[] | null;
    document: FakeTarget;
    addEventListener(type: string, listener: Listener): void;
    removeEventListener(type: string, listener: Listener): void;
    location: {origin: string};
    ReportingObserver?: unknown;
    sessionStorage?: unknown;
}

/** A window: the event target of the document, and the window the event bubbles to, and nothing else of a browser. */
function makeWindow(extra: Partial<FakeWindow> = {}): FakeWindow & {dispatchViolation(init: Partial<LiveViolation>): void} {
    const doc = new FakeTarget();
    const self = new FakeTarget();
    return {
        document: doc,
        addEventListener: (type, listener) => self.addEventListener(type, listener),
        removeEventListener: (type, listener) => self.removeEventListener(type, listener),
        location: {origin: 'http://localhost:6041'},
        ...extra,
        // A violation is dispatched at the document and bubbles to the window: a listener of either is reached once
        dispatchViolation(init) {
            const event = {type: 'securitypolicyviolation', effectiveDirective: 'script-src-elem', blockedURI: 'inline', sample: '', sourceFile: '', disposition: 'enforce', ...init};
            doc.dispatch('securitypolicyviolation', event);
            self.dispatch('securitypolicyviolation', event);
        },
    };
}

interface LiveViolation {
    effectiveDirective: string;
    blockedURI: string;
    sample: string;
    sourceFile: string;
    disposition: string;
}

/** A storage over a Map, with a log of what was written. */
function makeStorage(initial: Record<string, string> = {}) {
    const data = new Map(Object.entries(initial));
    return {
        data,
        getItem: vi.fn((key: string) => data.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => void data.set(key, value)),
        removeItem: vi.fn((key: string) => void data.delete(key)),
    };
}

/** The sources the storage holds, as the Security tab reads them. */
function stored(storage: ReturnType<typeof makeStorage>): unknown {
    const raw = storage.data.get(STORAGE_KEY);
    return raw === undefined ? undefined : JSON.parse(raw);
}

/** An enforced violation as the early listener buffers it. */
function early(overrides: Partial<Buffered> = {}): Buffered {
    return {directive: 'script-src-elem', blockedURI: 'inline', sample: 'window.__injected = 1;', sourceFile: 'http://localhost:6041/', ...overrides};
}

/** A `csp-violation` report of the Reporting API: the body names the blocked address `blockedURL`. */
function report(body: Partial<{effectiveDirective: string; blockedURL: string; sample: string; sourceFile: string; disposition: string}> = {}, type = 'csp-violation') {
    return {type, url: 'http://localhost:6041/', body: {effectiveDirective: 'script-src-elem', blockedURL: 'inline', sample: '', sourceFile: '', disposition: 'enforce', ...body}};
}

/** The pattern of the one line, for `source`: the text of the contract, the guide path at its end. */
function lineFor(source: string): RegExp {
    const escaped = source.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
    return new RegExp(`^LibreFolio blocked a script it did not send \\(${escaped}\\): a proxy, a CDN or a browser extension adds it\\. Guide: \\S*/admin/configuration/#csp$`);
}

let log: Mock<(message: string) => void>;
let network: {fetch: Mock; beacon: Mock; xhr: Mock};

beforeEach(() => {
    FakeReportingObserver.instances = [];
    log = vi.fn<(message: string) => void>();
    network = {
        fetch: vi.fn(async () => {
            throw new Error('the notice sends nothing: no report endpoint');
        }),
        beacon: vi.fn(() => false),
        xhr: vi.fn(),
    };
    vi.stubGlobal('fetch', network.fetch);
    vi.stubGlobal('XMLHttpRequest', network.xhr);
    vi.stubGlobal('navigator', {sendBeacon: network.beacon});
});

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

/** Starts the notice on `win` and `storage`, `log` the spy: what every case does first. */
async function start(win: FakeWindow, storage: ReturnType<typeof makeStorage> | unknown = makeStorage()): Promise<void> {
    const {startCspNotice} = await load();
    startCspNotice({win, storage, log});
}

describe('KNOWN_CSP_VIOLATIONS — what is never reported', () => {
    it('CSN-01: cheetah-grid’s probe of the global object — script-src, eval, the sample Chromium reports — is the one known violation', async () => {
        const {KNOWN_CSP_VIOLATIONS} = await load();

        expect(KNOWN_CSP_VIOLATIONS, 'the probe of cheetah-grid 1.16.7, harmless under an enforced policy: new Function("return this")() in a try/catch that falls back to window').toContainEqual(expect.objectContaining({directive: 'script-src', blockedURI: 'eval', sample: GLOBAL_PROBE_SAMPLE}));
    });
});

describe('startCspNotice — what it reads, and the one line it writes', () => {
    it('CSN-02: drains the early buffer of app.html: one line for what the page blocked before any bundle loaded, its source noted', async () => {
        const win = makeWindow({__lfCspViolations: [early()]});
        const storage = makeStorage();

        await start(win, storage);

        expect(log, 'one line, a single string: the text of the contract').toHaveBeenCalledTimes(1);
        expect(log.mock.calls[0]).toEqual([expect.stringMatching(lineFor('inline'))]);
        expect(stored(storage), 'the source is in the tab’s sessionStorage for the Security tab').toEqual(['inline']);
    });

    it('CSN-03: listens for what comes after: an enforced violation dispatched once the notice runs — at the document, bubbling to the window — is reported once', async () => {
        const win = makeWindow({__lfCspViolations: []});
        const storage = makeStorage();
        await start(win, storage);
        expect(log, 'premise: an empty buffer reports nothing').not.toHaveBeenCalled();

        win.dispatchViolation({effectiveDirective: 'script-src-elem', blockedURI: CDN_SCRIPT, sample: '', sourceFile: 'http://localhost:6041/'});

        expect(log).toHaveBeenCalledTimes(1);
        expect(log.mock.calls[0]).toEqual([expect.stringMatching(lineFor(CDN))]);
        expect(stored(storage)).toEqual([CDN]);
    });

    it.each<[string, string, string]>([
        ['an address: its origin, without path, query or fragment', CDN_SCRIPT, CDN],
        ['an address with a port', 'http://127.0.0.1:8080/x/y.js', 'http://127.0.0.1:8080'],
        ['an inline script', 'inline', 'inline'],
        ['an eval that is not cheetah-grid’s', 'eval', 'eval'],
    ])('CSN-04: a violation that blocked %s names %s as its source', async (_what, blockedURI, source) => {
        const win = makeWindow({__lfCspViolations: []});
        const storage = makeStorage();
        await start(win, storage);

        win.dispatchViolation({effectiveDirective: blockedURI === 'eval' ? 'script-src' : 'script-src-elem', blockedURI, sample: blockedURI === 'eval' ? '1 + 1' : ''});

        expect(log).toHaveBeenCalledTimes(1);
        expect(log.mock.calls[0]).toEqual([expect.stringMatching(lineFor(source))]);
        expect(stored(storage)).toEqual([source]);
    });

    it('CSN-05: a report-only violation is none of its business: neither the listener nor the observer reports it — and the listener is alive, which the next enforced one proves', async () => {
        const win = makeWindow({__lfCspViolations: [], ReportingObserver: FakeReportingObserver});
        const storage = makeStorage();
        await start(win, storage);

        win.dispatchViolation({blockedURI: CDN_SCRIPT, disposition: 'report'});
        FakeReportingObserver.instances[0].deliver(report({blockedURL: CDN_SCRIPT, disposition: 'report'}));

        expect(log, 'the managed profile’s report-only policy reports what an enforced one would block: the notice is about what WAS blocked').not.toHaveBeenCalled();
        expect(storage.setItem, 'and notes nothing').not.toHaveBeenCalled();

        win.dispatchViolation({blockedURI: 'inline', disposition: 'enforce'});
        expect(log, 'control: an enforced one, the same way, is reported').toHaveBeenCalledTimes(1);
        expect(stored(storage)).toEqual(['inline']);
    });

    it('CSN-06: cheetah-grid’s probe is never reported — from the buffer, the listener or the observer — while another eval is', async () => {
        const probe = {directive: 'script-src', blockedURI: 'eval', sample: GLOBAL_PROBE_SAMPLE, sourceFile: `${CDN}/chunk.js`};
        const win = makeWindow({__lfCspViolations: [early(probe)], ReportingObserver: FakeReportingObserver});
        const storage = makeStorage();
        await start(win, storage);

        win.dispatchViolation({effectiveDirective: 'script-src', blockedURI: 'eval', sample: GLOBAL_PROBE_SAMPLE});
        FakeReportingObserver.instances[0].deliver(report({effectiveDirective: 'script-src', blockedURL: 'eval', sample: GLOBAL_PROBE_SAMPLE}));

        expect(log, 'the known probe, three ways: nothing').not.toHaveBeenCalled();
        expect(storage.setItem, 'nothing noted').not.toHaveBeenCalled();

        // Known by directive, blocked URI and sample, all three: anything that differs in one is another violation
        win.dispatchViolation({effectiveDirective: 'script-src', blockedURI: 'eval', sample: '1 + 1'});
        expect(log, 'an eval of other code').toHaveBeenCalledTimes(1);
        expect(log.mock.calls[0]).toEqual([expect.stringMatching(lineFor('eval'))]);
        expect(stored(storage)).toEqual(['eval']);
    });

    it.each<[string, Partial<LiveViolation>]>([
        ['an inline script whose sample begins as the probe’s', {effectiveDirective: 'script-src-elem', blockedURI: 'inline', sample: GLOBAL_PROBE_SAMPLE}],
        ['the probe’s sample at another directive', {effectiveDirective: 'script-src-elem', blockedURI: 'eval', sample: GLOBAL_PROBE_SAMPLE}],
        ['the same eval with no sample (a policy without report-sample)', {effectiveDirective: 'script-src', blockedURI: 'eval', sample: ''}],
        ['the probe’s sample and more', {effectiveDirective: 'script-src', blockedURI: 'eval', sample: `${GLOBAL_PROBE_SAMPLE};`}],
    ])('CSN-07: %s is not the known probe: reported', async (_what, violation) => {
        const win = makeWindow({__lfCspViolations: []});
        await start(win);

        win.dispatchViolation(violation);

        expect(log).toHaveBeenCalledTimes(1);
    });

    it('CSN-08: one line per page load, however many scripts are blocked and however they arrive — and every distinct source noted, once, in the order met', async () => {
        const win = makeWindow({__lfCspViolations: [early(), early({sample: 'another();'})], ReportingObserver: FakeReportingObserver});
        const storage = makeStorage();
        await start(win, storage);
        expect(log, 'premise: the buffer produced its line').toHaveBeenCalledTimes(1);
        const first = log.mock.calls[0][0];

        win.dispatchViolation({blockedURI: CDN_SCRIPT});
        win.dispatchViolation({blockedURI: CDN_SCRIPT, sample: 'again();'});
        win.dispatchViolation({effectiveDirective: 'script-src', blockedURI: 'eval', sample: '2 + 2'});
        FakeReportingObserver.instances[0].deliver(report({blockedURL: 'https://other.example/y.js'}), report({blockedURL: 'inline'}));

        expect(log, 'one console.error per page load').toHaveBeenCalledTimes(1);
        expect(log.mock.calls[0][0], 'about the first source it met').toBe(first);
        expect(first).toMatch(lineFor('inline'));
        expect(stored(storage), 'each distinct source once: inline twice, the CDN twice, and the observer’s repeat of inline, are one entry each').toEqual(['inline', CDN, 'eval', 'https://other.example']);
    });

    it('CSN-09: a new page load logs again — the count is the page’s, not the tab’s — and the storage, kept by the tab, takes no source twice', async () => {
        const storage = makeStorage();
        await start(makeWindow({__lfCspViolations: [early()]}), storage);
        expect(log).toHaveBeenCalledTimes(1);
        const reloaded = vi.fn<(message: string) => void>();

        const {startCspNotice} = await load();
        startCspNotice({win: makeWindow({__lfCspViolations: [early(), early({blockedURI: CDN_SCRIPT})]}), storage, log: reloaded});

        expect(reloaded, 'the reloaded page: its own line').toHaveBeenCalledTimes(1);
        expect(stored(storage), 'inline was noted already: kept once, the CDN added').toEqual(['inline', CDN]);
    });

    it('CSN-10: what the tab already holds is kept: a source noted by an earlier page stays, and a repeat adds nothing', async () => {
        const storage = makeStorage({[STORAGE_KEY]: JSON.stringify(['https://earlier.example'])});

        await start(makeWindow({__lfCspViolations: [early(), early()]}), storage);

        expect(stored(storage)).toEqual(['https://earlier.example', 'inline']);
    });

    it.each<[string, string]>([
        ['text that is no JSON', 'not json'],
        ['a JSON object', '{"inline": true}'],
    ])('CSN-11: a storage that holds %s is treated as empty: the line is logged and a valid array written', async (_what, raw) => {
        const storage = makeStorage({[STORAGE_KEY]: raw});

        await start(makeWindow({__lfCspViolations: [early()]}), storage);

        expect(log).toHaveBeenCalledTimes(1);
        expect(stored(storage)).toEqual(['inline']);
    });
});

describe('startCspNotice — the Reporting API, where the browser has it', () => {
    it('CSN-12: a ReportingObserver of csp-violation reports, buffered, is built and observes; its enforced report is the source of its blockedURL', async () => {
        const win = makeWindow({__lfCspViolations: [], ReportingObserver: FakeReportingObserver});
        const storage = makeStorage();

        await start(win, storage);

        expect(FakeReportingObserver.instances, 'one observer').toHaveLength(1);
        const [observer] = FakeReportingObserver.instances;
        expect(observer.options, 'csp-violation reports only, and those that came before the module started').toEqual({types: ['csp-violation'], buffered: true});
        expect(observer.observing, 'observing').toBe(true);

        observer.deliver(report({blockedURL: CDN_SCRIPT}));

        expect(log).toHaveBeenCalledTimes(1);
        expect(log.mock.calls[0]).toEqual([expect.stringMatching(lineFor(CDN))]);
        expect(stored(storage)).toEqual([CDN]);
    });

    it('CSN-13: a report of another type is no violation: ignored', async () => {
        const win = makeWindow({__lfCspViolations: [], ReportingObserver: FakeReportingObserver});
        await start(win);

        FakeReportingObserver.instances[0].deliver(report({blockedURL: CDN_SCRIPT}, 'deprecation'));

        expect(log).not.toHaveBeenCalled();
    });

    it('CSN-14: a browser without ReportingObserver is no problem: the buffer and the listener do the work', async () => {
        const win = makeWindow({__lfCspViolations: [early()]});
        expect('ReportingObserver' in win, 'premise: the window has none').toBe(false);

        await expect(start(win)).resolves.toBeUndefined();

        expect(log, 'the buffer’s line').toHaveBeenCalledTimes(1);
        win.dispatchViolation({blockedURI: CDN_SCRIPT});
        expect(FakeReportingObserver.instances, 'no observer was built').toHaveLength(0);
    });

    it('CSN-15: a ReportingObserver whose construction throws does not take the notice with it', async () => {
        class Refusing {
            constructor() {
                throw new TypeError('csp-violation is not a type this browser reports');
            }
        }
        const win = makeWindow({__lfCspViolations: [early()], ReportingObserver: Refusing});

        await expect(start(win)).resolves.toBeUndefined();

        expect(log, 'the buffer is still read').toHaveBeenCalledTimes(1);
        expect(() => win.dispatchViolation({blockedURI: CDN_SCRIPT}), 'and the listener is alive').not.toThrow();
    });
});

describe('startCspNotice — a storage that fails, and a page that sends nothing', () => {
    it('CSN-16: a storage whose getItem and setItem throw (blocked site data, a private window) is swallowed: the line is logged all the same', async () => {
        const storage = {
            getItem: vi.fn(() => {
                throw new DOMException('The operation is insecure.', 'SecurityError');
            }),
            setItem: vi.fn(() => {
                throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
            }),
        };
        const win = makeWindow({__lfCspViolations: [early()]});

        await expect(start(win, storage)).resolves.toBeUndefined();

        expect(log, 'the console line does not depend on the storage').toHaveBeenCalledTimes(1);
        expect(() => win.dispatchViolation({blockedURI: CDN_SCRIPT}), 'nor does the listener').not.toThrow();
        expect(storage.setItem, 'premise: the module did try to write').toHaveBeenCalled();
    });

    it('CSN-17: a window whose sessionStorage cannot even be read (the getter throws), with no storage given, is swallowed too', async () => {
        const win = makeWindow({__lfCspViolations: [early()]});
        Object.defineProperty(win, 'sessionStorage', {
            get() {
                throw new DOMException('The operation is insecure.', 'SecurityError');
            },
        });
        const {startCspNotice} = await load();

        expect(() => startCspNotice({win, log})).not.toThrow();

        expect(log).toHaveBeenCalledTimes(1);
    });

    it('CSN-18: no network request of any kind: no fetch, no XMLHttpRequest, no beacon — the browser’s report stays in the browser', async () => {
        const win = makeWindow({__lfCspViolations: [early()], ReportingObserver: FakeReportingObserver});
        await start(win);

        win.dispatchViolation({blockedURI: CDN_SCRIPT});
        FakeReportingObserver.instances[0].deliver(report({blockedURL: 'eval', effectiveDirective: 'script-src', sample: '3 + 3'}));

        expect(log, 'premise: there was something to report').toHaveBeenCalledTimes(1);
        expect(network.fetch).not.toHaveBeenCalled();
        expect(network.xhr).not.toHaveBeenCalled();
        expect(network.beacon).not.toHaveBeenCalled();
    });
});

describe('startCspNotice — the defaults, and a page with nothing to read', () => {
    it('CSN-19: with no options it reads window, window.sessionStorage and console.error', async () => {
        const storage = makeStorage();
        const win = makeWindow({__lfCspViolations: [early()], sessionStorage: storage});
        vi.stubGlobal('window', win);
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
        const {startCspNotice} = await load();

        startCspNotice();

        expect(consoleError, 'console.error, with the line').toHaveBeenCalledTimes(1);
        expect(consoleError.mock.calls[0]).toEqual([expect.stringMatching(lineFor('inline'))]);
        expect(stored(storage), 'window.sessionStorage').toEqual(['inline']);
    });

    it('CSN-20: where there is no window (prerendering, a worker) it does nothing and does not throw', async () => {
        const {startCspNotice} = await load();

        expect(typeof window, 'premise: the node environment has no window').toBe('undefined');
        expect(() => startCspNotice({log})).not.toThrow();
        expect(log).not.toHaveBeenCalled();
    });

    it('CSN-21: a window with no buffer (app.html’s block failed, or a build without it) still listens', async () => {
        const win = makeWindow();
        expect('__lfCspViolations' in win, 'premise: no early buffer').toBe(false);
        const storage = makeStorage();

        await expect(start(win, storage)).resolves.toBeUndefined();
        win.dispatchViolation({blockedURI: CDN_SCRIPT});

        expect(log).toHaveBeenCalledTimes(1);
        expect(stored(storage)).toEqual([CDN]);
    });

    it.each<[string, Buffered[], string[]]>([
        ['with entries', [early()], ['inline', 'https://late.example']],
        ['empty', [], ['https://late.example']],
    ])('CSN-22: once the buffer is drained (%s) the window global is null — the early listener of app.html stops collecting — and a violation that comes next reaches the notice through its own listener, once', async (_what, buffer, expected) => {
        const win = makeWindow({__lfCspViolations: buffer});
        const storage = makeStorage();
        await start(win, storage);
        const before = log.mock.calls.length;

        expect(win.__lfCspViolations, 'null, not an emptied array: the early listener pushes only while the global is an array').toBeNull();

        win.dispatchViolation({blockedURI: 'https://late.example/x.js'});

        expect(log.mock.calls.length, 'the notice saw the late violation: its first line if the buffer was empty, none more if the buffer already logged').toBe(Math.max(before, 1));
        expect(stored(storage), 'noted once, although the event bubbles from the document to the window: one listener of the notice, at the document').toEqual(expected);
        expect(win.__lfCspViolations, 'and it did not go back to the buffer').toBeNull();
    });
});
