/**
 * Gallery — the settle every shot of gallery.spec.ts goes through (`screenshot()`), so that two runs of a shot may differ in
 * their content — a figure, a time, the seed's order, data another test moved — and never in their style or their frame
 * (plan 56, step 1). The developer's principle: what changes the style or the frame is made deterministic — the phase of an
 * animation, the scroll, the header, a modal's entrance, a chart, an image, the pointer — and what changes only the content
 * is accepted as noise. So nothing here touches data: it waits for the page, or fixes how it looks.
 *
 * ## The wait it replaces
 *
 * `screenshot()` used to wait for `waitForLoadState('networkidle')` and 200 ms. In a single-page app that lifecycle state is
 * reached once per document: after the first load it is already reached, the call returns at once, and the 200 ms were the
 * whole wait. Shots were taken with their panels still loading — a spinner in Settings › Preferences, skeletons and a
 * spinning Refresh on a broker's page, a sharing donut not drawn yet, grey thumbnails.
 *
 * ## What a shot waits for ({@link settleShot})
 *
 * 1. The pointer parked where nothing reacts to it, no tooltip left: otherwise it stays where the last click was, and
 *    whatever it rests on is hovered in the picture. A shot that hovers on purpose keeps it (`keepPointer`); a shot of the
 *    one tooltip a click pinned on purpose parks it too, and has exactly that tooltip, standing still (`pinnedTooltip`).
 * 2. No `/api/` request in flight for {@link API_QUIET_MS} ({@link apiQuiet}), counted by a tracker the spec installs on
 *    the page before its first load ({@link trackApiRequests}).
 * 3. No loader on screen ({@link noLoaderOnScreen}): nothing that says it is busy, no spinner or skeleton. A shot of a
 *    loading state says so (`allowLoaders`).
 * 4. The fonts in.
 * 5. Every animation that ends, ended ({@link finishFiniteAnimations}): a modal's entrance runs on the Web Animations API
 *    (Svelte's `transition:`), which the gallery's CSS cannot pause.
 * 6. Every image on screen arrived, or failed ({@link imagesInViewComplete}).
 * 7. The charts on screen drawn and standing still ({@link chartsStill}): ECharts animates every drawing.
 * 8. The page's text standing still ({@link textStill}): a figure counting up runs on no animation either.
 * 9. The scroll, the page's height and the header standing still ({@link scrollStill}).
 * 10. The shot's subject standing still, when it names one.
 * 11. No toast over the page (`allowToast` for a shot of one).
 * 12. Every looping animation pinned at the same moment of its own run ({@link pinLoopingAnimations}): the last change
 *     before the picture.
 *
 * Each step has its own deadline, and its failure names the shot. Then one line in the run's log, 🔎
 * ({@link shotFingerprint}): what decides the frame, so two runs of one shot can be compared on it. The picture itself
 * ({@link captureShot}) is taken on a budget of its own, and a slow one is logged (⚠️).
 *
 * ## On screen
 *
 * A step that reads the page reads what the picture holds: an element counts when it is drawn — it has a box, and no
 * `display: none` or `visibility: hidden` takes it off the page — and that box meets the viewport. A spinner below the fold
 * or a chart in a hidden tab is no reason to wait.
 *
 * ## Before the shot
 *
 * Two things the settle cannot fix afterwards, so a test does them before it shoots. The frame: {@link frameTarget} brings
 * a block to the top of the screen the same way in every run, and waits for the frame to stand still — the page's end may
 * stop the scroll short of the top, with the header still on screen: the same frame every time, logged (↕️); a dialog locks
 * the page where its trigger's scroll left it, so that trigger is brought into view from the top of a settled page, the
 * same way in every run ({@link bringIntoViewFromTop}). An open dropdown: one placed once, from its trigger's box, stays
 * where it was put when the layout above the trigger moves afterwards — so it is opened on a settled page only
 * ({@link settledToOpen}), and asserted where its component puts it before the shot ({@link expectDropdownAt}).
 *
 * ## Looping animations
 *
 * freezeAnimations() (gallery.spec.ts) pauses every CSS animation when it is called — after the page has loaded, wherever
 * each animation had got to: a phase that changes with the machine's speed. It used to force `animation-delay: -0.1s` as
 * well, which also wiped out the stagger an animation is designed with: the login background (AnimatedBackground.svelte)
 * draws three chart lines of 12 s, started 0, 4 and 8 s apart. The designed delays stay now, and right before the picture
 * every animation that never ends is paused at {@link LOOP_TIME_MS} of its own run. An animation's current time counts from
 * its start, its delay included, so each one shows the frame it shows that long after it started — the second line still
 * 4 s behind the first. The moment is 3.6 s, the developer's choice of 14/10 on previews (D1, plan 56, step 4);
 * `GALLERY_ANIMATION_TIME_MS`, which exists for previews, sets another for a run.
 *
 * ## Evidence when a test fails
 *
 * The first afterEach logs ({@link logApiOnFailure}) the requests still in flight when a test failed, with their age, and the
 * slowest `/api/` requests that came back: the evidence for the loads that never ended — `login()` held on `auth-loading`
 * for 30 s (plan 56, G-2). Requests other than `/api/` — a document, a script chunk — are listed as well: a page held by its
 * code rather than its data shows there. They are never waited for. An `/api/` request is named by its path, and by its host
 * as well when it went to another origin than the page's current one: one left over from a document the page has left
 * stands out. The requests of a document closed by a navigation to another origin are forgotten as it closes, and the log
 * says how many (🧹, {@link trackApiRequests}).
 */

import type {TestInfo} from '@playwright/test';
import {expect, type Locator, type Page, type Request} from './playwright';
import {fontsLoaded} from './galleryFiles';
import {recordMixedElements} from './galleryMixed';
import {ANY_TOAST, expectNoToast, waitForStillness} from './galleryReportSets';
import {parkPointer, renderedFrames} from './galleryRiskLab';

// ---------------------------------------------------------------------------
// Budgets
// ---------------------------------------------------------------------------

/** How long no `/api/` request may be in flight before the page counts as answered: a reply often sets off the next request. */
const API_QUIET_MS = 300;

/** How long the page's requests may take, on a busy lane: the slowest of the gallery's (a risk wave, a parse) stay under it. */
const API_TIMEOUT = 45_000;

/** How long a loader may stay on screen. */
const LOADER_TIMEOUT = 30_000;

/** How long the animations that end are given to end on their own, before what is left is finished by hand. */
const FINITE_WAIT_MS = 5_000;

/** How long the images on screen may take: the server resizes a preview on its first request. */
const IMAGES_TIMEOUT = 15_000;

/** How long the charts may take to draw and stop. */
const CHARTS_TIMEOUT = 15_000;

/**
 * How long the page's text must stand still. A count-up (`TweenedValue`: 900 ms, cubic-out, two decimals) changes its figure
 * on nearly every frame while it runs, so half a second without a change finds none running — and a figure ticking once a
 * second still leaves room between two ticks.
 */
const TEXT_QUIET_MS = 500;

/** How long the text may take to stand still. */
const TEXT_TIMEOUT = 20_000;

/** How long the scroll, the page's height and the header must stand still. */
const SCROLL_QUIET_MS = 300;

/** How long they may take to stand still. */
const SCROLL_TIMEOUT = 10_000;

/** How long a toast may take to leave: a success or an info toast stays 8 s (toastStore.svelte.ts), a warning 10 s. */
const TOAST_TIMEOUT = 10_000;

/**
 * How long the browser may take to capture a shot ({@link captureShot}). A budget of its own: the 20 s action timeout of
 * gallery.spec.ts is for the steps of the test, which can hang on our logic, and a capture is not one of them. Past «fonts
 * loaded», Playwright 1.61 makes two calls inside the browser, `Page.getLayoutMetrics` and `Page.captureScreenshot`, and the
 * second waits for the browser's compositor, which a loaded machine can stall for seconds. On 14/10 one did, in the smoke
 * run (6 workers, `/api/` calls of 2.5 s): `desktop/fr/light/assets/detail-chart` went past the 20 s after a complete
 * settle, on a page idle and answering, and the failure screenshot taken right after was normal — 1 shot in that run's 521,
 * none in the 5,625 of the day's baseline runs.
 */
export const CAPTURE_TIMEOUT_MS = 60_000;

/** A capture slower than this is logged (⚠️): the budget above lets a stall pass, the log keeps it in sight. */
const CAPTURE_SLOW_MS = 5_000;

/** How many finished `/api/` requests the tracker keeps, slowest first. */
const SLOWEST_KEPT = 20;

/** How many of them, and how many requests other than `/api/` in flight, a failed test logs. */
const FAILURE_LISTED = 8;

/** How much of a request's path and query a record keeps. */
const PATH_KEPT = 120;

/**
 * The moment every looping animation is pinned at, in milliseconds of its own run ({@link pinLoopingAnimations}): 3.6 s,
 * the developer's choice of 14/10 (D1, plan 56, step 4), made on previews of the login page at 0, 3.6, 5.4 and 7.6 s — at
 * 3.6 s the login background shows its first chart line whole (30 % of its 12 s run, where `drawAndFade` completes the
 * stroke), the other two still in their 4 s and 8 s delays, and the waves mid-movement. `GALLERY_ANIMATION_TIME_MS` exists
 * for previews: it overrides the moment for a run, as a whole number of milliseconds; anything else fails the file when it
 * loads, rather than shooting at a moment nobody chose.
 */
export const LOOP_TIME_MS = loopTime(process.env.GALLERY_ANIMATION_TIME_MS);

function loopTime(raw: string | undefined): number {
    if (raw === undefined || raw.trim() === '') return 3_600;
    const ms = Number(raw.trim());
    if (!Number.isInteger(ms) || ms < 0) throw new Error(`GALLERY_ANIMATION_TIME_MS must be a whole number of milliseconds (0 or more), not "${raw}"`);
    return ms;
}

// ---------------------------------------------------------------------------
// What a shot may opt out of
// ---------------------------------------------------------------------------

/** What a shot may opt out of, and the part of the page it is about: {@link settleShot}. */
export type ShotOptions = {
    /** The shot hovers on purpose — a popover, a panel held at full strength: the pointer stays where the test left it. */
    keepPointer?: boolean;
    /**
     * The shot shows the one tooltip a click pinned on purpose — the promote button's, over the merge dialog it opened.
     * Tooltip.svelte pins its tooltip on a click on its trigger, and keeps it until a click outside it — which a click inside
     * a dialog never is: ModalBase stops it — or 30 s after the pointer left. The pointer is still parked, where
     * {@link parkPointer} parks it, but instead of no tooltip exactly one `tooltip-content` is on screen, and it stands
     * still. Real behaviour: kept in the picture, not hidden by a click no user made. Nothing brings it back without a
     * click, so the test checks it is still there after the shot. Not with `keepPointer`.
     */
    pinnedTooltip?: boolean;
    /** The shot is of a loading state: the loaders on screen are its subject, not a reason to wait. */
    allowLoaders?: boolean;
    /** The shot is of a toast: toasts are not waited out. */
    allowToast?: boolean;
    /** The part of the page the shot is about: it must stand still as well. */
    subject?: Locator;
};

// ---------------------------------------------------------------------------
// The requests in flight
// ---------------------------------------------------------------------------

/** A request on its way: what it asked, of which origin, and when it left. */
type RequestRecord = {method: string; path: string; origin: string; startedAt: number};

/** A request still on its way, the origin it went to, and for how long. */
export type InFlightRequest = {method: string; path: string; origin: string; ageMs: number};

/** An `/api/` request that came back, or failed: the origin it went to, how long it took, and its status (`failed`, or `?` while unknown). */
export type FinishedRequest = {method: string; path: string; origin: string; ms: number; status: string};

type ApiTracker = {
    /** The `/api/` requests on their way. */
    api: Map<Request, RequestRecord>;
    /** Every other request on its way — a document, a script, an image: evidence for a failure, never waited for. */
    other: Map<Request, RequestRecord>;
    /** The slowest `/api/` requests that came back, slowest first. */
    slowest: FinishedRequest[];
    /** Since when (`Date.now()`) no `/api/` request has been on its way; null while one is. */
    quietSince: number | null;
    /** The origin of the page's main frame as of its last navigation: `null` on `about:blank`. */
    origin: string;
};

/** A live connection, not a request that ends: never counted. */
const UNTRACKED_RESOURCE_TYPES = new Set(['eventsource', 'websocket']);

/** One tracker per page, installed once ({@link trackApiRequests}). */
const trackers = new WeakMap<Page, ApiTracker>();

/** What the last settle of each page did, for the line it logs ({@link shotFingerprint}). */
const lastSettle = new WeakMap<Page, {forced: number; pinned: number}>();

/** The tests whose failure {@link logApiOnFailure} has logged: once per test, whichever afterEach comes first. */
const loggedFailures = new WeakSet<TestInfo>();

function isApi(url: string): boolean {
    try {
        return new URL(url).pathname.startsWith('/api/');
    } catch {
        return false;
    }
}

/** The origin of `url`: `null` for `about:blank`, a `data:` URL or an error page, as for anything the parser does not take. */
function originOf(url: string): string {
    try {
        return new URL(url).origin;
    } catch {
        return 'null';
    }
}

/** The path and query of an `/api/` request; the host as well for any other, where it says whose the request is. */
function pathOf(url: string, api: boolean): string {
    let path = url;
    try {
        const parsed = new URL(url);
        path = `${api ? '' : parsed.host}${parsed.pathname}${parsed.search}`;
    } catch {
        // Not a URL the parser takes: kept as it is.
    }
    return path.length > PATH_KEPT ? `${path.slice(0, PATH_KEPT - 1)}…` : path;
}

/**
 * How a line names an `/api/` request: by its path and query, as always, when it went to the page's current origin; with its
 * host in front when it went to another — a request of a document the page has since left reads `localhost:6153/api/v1/…`
 * on a page under the LAN name, at a glance. Any other request carries its host already ({@link pathOf}).
 */
function apiPathFor(request: {path: string; origin: string}, pageOrigin: string): string {
    if (request.origin === pageOrigin) return request.path;
    let host = request.origin;
    try {
        host = new URL(request.origin).host;
    } catch {
        // An opaque origin has no host: it is shown as it is.
    }
    return `${host}${request.path}`;
}

function keepIfSlow(tracker: ApiTracker, finished: FinishedRequest): void {
    tracker.slowest.push(finished);
    tracker.slowest.sort((a, b) => b.ms - a.ms);
    if (tracker.slowest.length > SLOWEST_KEPT) tracker.slowest.length = SLOWEST_KEPT;
}

function inFlightOf(requests: Map<Request, RequestRecord>): InFlightRequest[] {
    const now = Date.now();
    return Array.from(requests.values(), (record) => ({method: record.method, path: record.path, origin: record.origin, ageMs: now - record.startedAt})).sort((a, b) => b.ageMs - a.ageMs);
}

function installTracker(page: Page): ApiTracker {
    const tracker: ApiTracker = {api: new Map(), other: new Map(), slowest: [], quietSince: Date.now(), origin: originOf(page.url())};
    trackers.set(page, tracker);
    // Off the books, whatever became of it: the last `/api/` request leaving starts the quiet.
    const forget = (request: Request): RequestRecord | undefined => {
        tracker.other.delete(request);
        const record = tracker.api.get(request);
        if (!record) return undefined;
        tracker.api.delete(request);
        if (tracker.api.size === 0) tracker.quietSince = Date.now();
        return record;
    };
    const ended = (request: Request, failed: boolean): void => {
        const record = forget(request);
        if (!record) return;
        const finished: FinishedRequest = {method: record.method, path: record.path, origin: record.origin, ms: Date.now() - record.startedAt, status: failed ? 'failed' : '?'};
        keepIfSlow(tracker, finished);
        if (!failed) {
            request
                .response()
                .then((response) => {
                    if (response) finished.status = String(response.status());
                })
                .catch(() => undefined);
        }
    };
    page.on('request', (request) => {
        // A redirect goes on as a new request: its predecessor is not on its way any more.
        const predecessor = request.redirectedFrom();
        if (predecessor) forget(predecessor);
        if (UNTRACKED_RESOURCE_TYPES.has(request.resourceType())) return;
        const url = request.url();
        const api = isApi(url);
        const record: RequestRecord = {method: request.method(), path: pathOf(url, api), origin: originOf(url), startedAt: Date.now()};
        if (api) {
            tracker.api.set(request, record);
            tracker.quietSince = null;
        } else {
            tracker.other.set(request, record);
        }
    });
    page.on('requestfinished', (request) => ended(request, false));
    page.on('requestfailed', (request) => ended(request, true));
    // A navigation to another site moves the page to another renderer process, and Playwright reports no end for the
    // requests of the document it closes: neither `requestfinished` nor `requestfailed` comes, and left on the books they
    // would be in flight for good. The Security shot meets it (gallery.spec.ts): login() opens the Dashboard on the
    // baseURL, then signInThroughFormUnder() opens the app under the LAN name. In the smoke run of 14/10 (lane 6153) its
    // settle waited 45 s, on a page under `lf-e2e.lan` by then, for `GET /api/v1/brokers/import/plugins` (on a phone
    // `GET /api/v1/brokers?include_inaccessible=true`), in flight for nearly a minute beside an icon of `localhost:6153` and
    // the release check: requests of the closed Dashboard, started within 0.4 s of each other. So when the main frame
    // commits a document of another origin, every request on the books is forgotten except the navigation requests — the
    // new document's own is one — and at once: no request of the new document is reported before it commits. The origin is
    // what is compared: every cross-site navigation changes it, a same-document one never does. A navigation that keeps it
    // changes nothing — a reload reports the cancellations of the document it closes (`failed` in the 🐢 lines), and
    // SvelteKit's routing, which fires `framenavigated` too, closes none. The first load, from `about:blank`, counts as a
    // change, with nothing on the books yet.
    page.on('framenavigated', (frame) => {
        if (frame !== page.mainFrame()) return;
        const origin = originOf(frame.url());
        if (origin === tracker.origin) return;
        let dropped = 0;
        for (const requests of [tracker.api, tracker.other]) {
            for (const request of Array.from(requests.keys())) {
                if (request.isNavigationRequest()) continue;
                requests.delete(request);
                dropped += 1;
            }
        }
        // As in forget(): the last `/api/` request leaving the books starts the quiet.
        if (tracker.api.size === 0 && tracker.quietSince === null) tracker.quietSince = Date.now();
        const closed = tracker.origin;
        tracker.origin = origin;
        if (dropped > 0) console.log(`  🧹 ${dropped} request(s) of the closed document on ${closed} forgotten (a cross-site navigation reports no end for them)`);
    });
    return tracker;
}

/**
 * Count the page's requests in flight, from now on: every request whose path starts with `/api/` — on any origin, the
 * Security shot runs under a LAN name — except a live connection (an event stream, a WebSocket). Installed once per page,
 * by the outer beforeEach, before the first load: a request that left before it would never be seen. Every other request
 * is recorded too, for the evidence of a failure only ({@link logApiOnFailure}). When the main frame commits a document of
 * another origin, the requests of the document it closed are forgotten — Playwright reports no end for them — and the log
 * says how many (🧹).
 */
export function trackApiRequests(page: Page): void {
    if (!trackers.has(page)) installTracker(page);
}

/** The page's `/api/` requests in flight, oldest first, with the origin they went to and their age. */
export function apiInFlight(page: Page): InFlightRequest[] {
    const tracker = trackers.get(page);
    return tracker ? inFlightOf(tracker.api) : [];
}

/** The `n` slowest `/api/` requests of the page that came back (or failed), slowest first. */
export function apiSlowest(page: Page, n: number): FinishedRequest[] {
    return (trackers.get(page)?.slowest ?? []).slice(0, n);
}

function describeInFlight(request: InFlightRequest, pageOrigin: string): string {
    return `${request.method} ${apiPathFor(request, pageOrigin)} (${(request.ageMs / 1000).toFixed(1)} s)`;
}

/**
 * No `/api/` request of the page has been in flight for `quietMs` in a row: the page's answers are in, and so are the
 * requests they set off. On the deadline the failure names the requests still in flight and their age, with their host
 * when they went to another origin than the page's. A page nobody tracked is tracked from now on, and the log says so:
 * what left before cannot be seen.
 */
export async function apiQuiet(page: Page, shot: string, quietMs = API_QUIET_MS, timeout = API_TIMEOUT): Promise<void> {
    let tracker = trackers.get(page);
    if (!tracker) {
        console.log(`  ⚠️ ${shot}: the page's /api/ requests were not tracked — only those from now on are seen (trackApiRequests belongs in the outer beforeEach)`);
        tracker = installTracker(page);
    }
    const watched = tracker;
    await expect
        .poll(
            () => {
                if (watched.api.size > 0) {
                    const inFlight = inFlightOf(watched.api).map((request) => describeInFlight(request, watched.origin));
                    return `${watched.api.size} in flight: ${inFlight.join(', ')}`;
                }
                const quietFor = Date.now() - (watched.quietSince ?? Date.now());
                return quietFor >= quietMs ? 'quiet' : `quiet for ${quietFor} of ${quietMs} ms`;
            },
            {message: `${shot}: an /api/ request is still in flight`, timeout, intervals: [50, 100, 150]},
        )
        .toBe('quiet');
}

/**
 * When the test failed, log what the page was still waiting for: its `/api/` requests in flight with their age (⏳), the
 * other requests in flight (⏳, a document or a script chunk), and the slowest `/api/` requests that came back (🐢). The
 * evidence for a load that never ended — `login()` held on `auth-loading`, a page left busy. An `/api/` request that went
 * to another origin than the page's current one is named with its host ({@link apiPathFor}). Synchronous, and once per
 * test: the first afterEach to run calls it, before the page is left; a later call is silent.
 */
export function logApiOnFailure(page: Page, testInfo: TestInfo): void {
    if (testInfo.status === testInfo.expectedStatus) return;
    if (loggedFailures.has(testInfo)) return;
    const tracker = trackers.get(page);
    if (!tracker) return;
    loggedFailures.add(testInfo);
    const api = apiInFlight(page);
    const other = inFlightOf(tracker.other);
    const slowest = apiSlowest(page, FAILURE_LISTED);
    console.log(`  ⏳ ${testInfo.project.name} › ${testInfo.title}: ended ${testInfo.status} with ${api.length} /api/ request(s) and ${other.length} other request(s) in flight`);
    for (const request of api) console.log(`  ⏳ ${request.method} ${apiPathFor(request, tracker.origin)} ${request.ageMs} ms`);
    for (const request of other.slice(0, FAILURE_LISTED)) console.log(`  ⏳ (not /api/) ${request.method} ${request.path} ${request.ageMs} ms`);
    for (const request of slowest) console.log(`  🐢 ${request.method} ${apiPathFor(request, tracker.origin)} ${request.ms} ms ${request.status}`);
}

// ---------------------------------------------------------------------------
// Loaders
// ---------------------------------------------------------------------------

/** What says it is busy: the attribute a page or a panel publishes while it loads (`waitForSettled`, app-events.ts). */
const BUSY = '[aria-busy="true"], [data-busy="true"]';

/**
 * The keyframes of a loader: Tailwind's `animate-spin`, `animate-pulse` (the skeletons) and `animate-ping`, and the `spin`
 * a component scopes for itself (LoadingSpinner.svelte; Svelte renames it `svelte-<hash>-spin`). Read off the animations
 * the browser runs, not off class names.
 */
const LOADER_KEYFRAMES = /^(?:svelte-[a-z0-9]+-)?(?:spin|pulse|ping)$/;

/**
 * No loader on screen: among the elements drawn in the viewport, none says it is busy (`aria-busy` or `data-busy` true),
 * and no spinner or skeleton is animated — paused counts too: freezeAnimations() pauses a spinner, it does not take it
 * away. Under the gallery's reduced motion a few spinners drop their animation (`motion-reduce:animate-none`, the Tools
 * pages); their panels publish `aria-busy` as well. On the deadline the failure lists what is still loading, by its
 * nearest test id.
 */
export async function noLoaderOnScreen(page: Page, shot: string, timeout = LOADER_TIMEOUT): Promise<void> {
    await expect
        .poll(
            () =>
                page.locator(BUSY).evaluateAll((busy, keyframes) => {
                    const loader = new RegExp(keyframes);
                    const onScreen = (element: Element): boolean => {
                        if (element.getClientRects().length === 0 || getComputedStyle(element).visibility !== 'visible') return false;
                        const box = element.getBoundingClientRect();
                        return box.width > 0 && box.height > 0 && box.bottom > 0 && box.right > 0 && box.top < window.innerHeight && box.left < window.innerWidth;
                    };
                    const owner = (element: Element): string => element.closest('[data-testid]')?.getAttribute('data-testid') ?? element.tagName.toLowerCase();
                    const offenders = new Set<string>();
                    for (const element of busy) if (onScreen(element)) offenders.add(`busy: ${owner(element)}`);
                    for (const animation of document.getAnimations()) {
                        if (!(animation instanceof CSSAnimation) || !loader.test(animation.animationName)) continue;
                        const target = animation.effect instanceof KeyframeEffect ? animation.effect.target : null;
                        if (target && onScreen(target)) offenders.add(`${animation.animationName.replace(/^svelte-[a-z0-9]+-/, '')}: ${owner(target)}`);
                    }
                    return Array.from(offenders).sort();
                }, LOADER_KEYFRAMES.source),
            {message: `${shot}: a loader is on screen — the page is still loading (a shot of a loading state passes allowLoaders)`, timeout, intervals: [100, 250, 500]},
        )
        .toEqual([]);
}

// ---------------------------------------------------------------------------
// Animations
// ---------------------------------------------------------------------------

/**
 * Every animation that ends has ended. First the ones running are given {@link FINITE_WAIT_MS} to end on their own — a
 * modal's fade and scale (ModalBase, Svelte's `transition:`, on the Web Animations API that freezeAnimations() cannot
 * pause), a CSS transition on a page left unfrozen — then every one still unfinished is finished by hand and shows its
 * end state: those freezeAnimations() paused half-way (a toast's countdown bar, a highlight's pulse), and any still running
 * after the wait, which the log names. Returns how many were finished by hand.
 */
export async function finishFiniteAnimations(page: Page, shot: string): Promise<number> {
    const ended = await page
        .waitForFunction(
            () =>
                document.getAnimations().every((animation) => {
                    const end = animation.effect?.getComputedTiming().endTime;
                    return animation.playState !== 'running' || typeof end !== 'number' || !Number.isFinite(end);
                }),
            undefined,
            {timeout: FINITE_WAIT_MS, polling: 100},
        )
        .then(
            () => true,
            () => false,
        );
    if (!ended) {
        const running = await page.evaluate(() =>
            document
                .getAnimations()
                .filter((animation) => {
                    const end = animation.effect?.getComputedTiming().endTime;
                    return animation.playState === 'running' && typeof end === 'number' && Number.isFinite(end);
                })
                .map((animation) => {
                    const target = animation.effect instanceof KeyframeEffect ? animation.effect.target : null;
                    const owner = target ? (target.closest('[data-testid]')?.getAttribute('data-testid') ?? target.tagName.toLowerCase()) : '?';
                    const kind = animation instanceof CSSAnimation ? animation.animationName : animation instanceof CSSTransition ? `transition ${animation.transitionProperty}` : 'web animation';
                    return `${kind} on ${owner}`;
                }),
        );
        console.log(`  ⚠️ ${shot}: still running after ${FINITE_WAIT_MS / 1000} s, finished by hand: ${running.join(', ') || 'none left'}`);
    }
    return page.evaluate(() => {
        let forced = 0;
        for (const animation of document.getAnimations()) {
            if (animation.playState !== 'running' && animation.playState !== 'paused') continue;
            const end = animation.effect?.getComputedTiming().endTime;
            if (typeof end !== 'number' || !Number.isFinite(end)) continue;
            try {
                animation.finish();
                forced += 1;
            } catch {
                // A playback rate of zero has no end to jump to: left as it is.
            }
        }
        return forced;
    });
}

/**
 * Pause every animation that never ends at `timeMs` of its own run: {@link LOOP_TIME_MS} unless told otherwise — 3.6 s, the
 * developer's choice of 14/10 (D1, plan 56, step 4). The current time counts from the animation's start, its delay included,
 * so each shows the frame it shows that long after it started, and the stagger it is designed with stays: at 3.6 s the login
 * background's first line is drawn whole, the second and the third still in their 4 s and 8 s delays. A spinner a shot
 * allows is pinned the same way. Returns how many were pinned.
 */
export async function pinLoopingAnimations(page: Page, timeMs = LOOP_TIME_MS): Promise<number> {
    return page.evaluate((time) => {
        let pinned = 0;
        for (const animation of document.getAnimations()) {
            if (animation.effect?.getComputedTiming().endTime !== Infinity) continue;
            try {
                animation.pause();
                animation.currentTime = time;
                pinned += 1;
            } catch {
                // An animation with nothing to pause it against is left as it is.
            }
        }
        return pinned;
    }, timeMs);
}

// ---------------------------------------------------------------------------
// Images, charts, text, scroll
// ---------------------------------------------------------------------------

/**
 * Every image on screen has finished: loaded or failed — a favicon its site never served is as settled as a loaded one, and
 * draws the same way on every run. Shadow roots included (a locator crosses them). An image counts where it is drawn, or
 * would be: one the page keeps out of the layout until it loads has no box of its own, so its holder's box decides. A lazy
 * image the page hides is left alone — the browser never asks for it — and so is every image off screen. On the deadline
 * the failure lists their sources.
 */
export async function imagesInViewComplete(page: Page, shot: string): Promise<void> {
    await expect
        .poll(
            () =>
                page.locator('img').evaluateAll((images) =>
                    images.flatMap((element) => {
                        const image = element as HTMLImageElement;
                        if (image.complete) return [];
                        const shown = image.getClientRects().length > 0;
                        if (!shown && image.loading === 'lazy') return [];
                        const box = (shown ? image : image.parentElement)?.getBoundingClientRect();
                        if (!box || box.width === 0 || box.height === 0) return [];
                        if (box.bottom <= 0 || box.right <= 0 || box.top >= window.innerHeight || box.left >= window.innerWidth) return [];
                        return [(image.currentSrc || image.getAttribute('src') || '(no source yet)').slice(0, 120)];
                    }),
                ),
            {message: `${shot}: an image on screen is still loading`, timeout: IMAGES_TIMEOUT},
        )
        .toEqual([]);
}

/**
 * The charts of `scope` on screen have drawn, and stopped drawing. Drawn: every `[data-chart-ready]` on screen says `true` —
 * ECharts finished a first drawing (chartReady.ts). Stopped: two readings in a row agree on the pixels of the canvases on
 * screen and on every render counter of the scope (`data-chart-renders`). ECharts animates every drawing for up to 800 ms
 * (echartsAnimationConfig.ts), on no animation the gallery can pause, and `data-chart-ready` stays true through every later
 * drawing, so a chart redrawn by a later answer or a resize passes it mid-animation: the shot takes the pixels, so the
 * pixels are read — galleryRiskDashboard.ts `canvasStill`, for canvases the page may not read too. The holdings map draws
 * the brokers' logos, pictures from other sites, and a canvas that holds one is closed to reading (`toDataURL` throws): its
 * size stands for it, and its render counter tells when ECharts drew it again. A scope with no chart is still at once.
 */
export async function chartsStill(scope: Locator, what: string): Promise<void> {
    let previous: string | null = null;
    await expect
        .poll(
            async () => {
                const reading = await scope.evaluate((root) => {
                    const onScreen = (element: Element): boolean => {
                        if (element.getClientRects().length === 0 || getComputedStyle(element).visibility !== 'visible') return false;
                        const box = element.getBoundingClientRect();
                        return box.width > 0 && box.height > 0 && box.bottom > 0 && box.right > 0 && box.top < window.innerHeight && box.left < window.innerWidth;
                    };
                    const drawing = Array.from(root.querySelectorAll('[data-chart-ready]'))
                        .filter((chart) => onScreen(chart) && chart.getAttribute('data-chart-ready') !== 'true')
                        .map((chart) => chart.closest('[data-testid]')?.getAttribute('data-testid') ?? chart.tagName.toLowerCase());
                    if (drawing.length > 0) return {drawing, state: null};
                    const canvases = Array.from(root.querySelectorAll('canvas')).filter(onScreen);
                    let hash = 0;
                    for (const canvas of canvases) {
                        let pixels = `${canvas.width}x${canvas.height}`;
                        if (canvas.width > 0 && canvas.height > 0) {
                            try {
                                pixels = canvas.toDataURL();
                            } catch {
                                // A picture from another site is drawn in it: its size stands for its pixels.
                            }
                        }
                        for (let index = 0; index < pixels.length; index += 1) hash = (Math.imul(hash, 31) + pixels.charCodeAt(index)) | 0;
                    }
                    const passes = Array.from(root.querySelectorAll('[data-chart-renders]'), (chart) => chart.getAttribute('data-chart-renders') ?? '').join(',');
                    return {drawing, state: canvases.length === 0 && passes === '' ? null : `${canvases.length}:${hash}:${passes}`};
                });
                if (reading.drawing.length > 0) {
                    previous = null;
                    return `not drawn yet: ${reading.drawing.join(', ')}`;
                }
                // Nothing on screen draws, and no counter can move.
                if (reading.state === null) return 'still';
                const still = reading.state === previous;
                previous = reading.state;
                return still ? 'still' : 'drawing';
            },
            {message: `${what}: a chart is still drawing`, timeout: CHARTS_TIMEOUT, intervals: [150, 250]},
        )
        .toBe('still');
}

/**
 * The page's text has not changed for `quietMs`, measured on the page's own clock — the one a count-up runs on. A figure
 * that counts up (`TweenedValue`, svelte/motion, from 0 on its first display) runs on no animation the gallery can pause and
 * publishes no end: its text is what moves. galleryRiskDashboard.ts `textStill`, on the whole page.
 */
export async function textStill(page: Page, shot: string, quietMs = TEXT_QUIET_MS): Promise<void> {
    await expect
        .poll(
            () =>
                page.evaluate(
                    (quiet) =>
                        new Promise<boolean>((resolve) => {
                            let text = document.body?.textContent ?? '';
                            let started = -1;
                            let since = -1;
                            const step = (now: number): void => {
                                if (started < 0) started = since = now;
                                const current = document.body?.textContent ?? '';
                                if (current !== text) {
                                    text = current;
                                    since = now;
                                }
                                if (now - since >= quiet) resolve(true);
                                else if (now - started >= 3 * quiet) resolve(false);
                                else requestAnimationFrame(step);
                            };
                            requestAnimationFrame(step);
                        }),
                    quietMs,
                ),
            {message: `${shot}: the page's text is still changing — a figure counting up?`, timeout: TEXT_TIMEOUT},
        )
        .toBe(true);
}

/**
 * The frame has stopped moving: the page's scroll, its height and the header's `data-scroll-state` (Header.svelte: visible,
 * hidden or pinned — it slides away after 8 px of scrolling down) have not changed for {@link SCROLL_QUIET_MS} of rendered
 * frames. A smooth scroll a component starts on its own, or a block still growing as its data arrives, moves the frame on
 * no animation the gallery can see. On the deadline the failure gives the last reading.
 */
export async function scrollStill(page: Page, shot: string): Promise<void> {
    await expect
        .poll(
            () =>
                page.evaluate(
                    (quiet) =>
                        new Promise<string>((resolve) => {
                            const read = (): string => `scrollY ${Math.round(window.scrollY * 10) / 10} · height ${document.documentElement.scrollHeight} · header ${document.querySelector('[data-testid="app-header"]')?.getAttribute('data-scroll-state') ?? '-'}`;
                            let last = read();
                            let started = -1;
                            let since = -1;
                            const step = (now: number): void => {
                                if (started < 0) started = since = now;
                                const current = read();
                                if (current !== last) {
                                    last = current;
                                    since = now;
                                }
                                if (now - since >= quiet) resolve('still');
                                else if (now - started >= 3 * quiet) resolve(`moving: ${current}`);
                                else requestAnimationFrame(step);
                            };
                            requestAnimationFrame(step);
                        }),
                    SCROLL_QUIET_MS,
                ),
            {message: `${shot}: the frame is still moving — a scroll, the page's height or the header`, timeout: SCROLL_TIMEOUT},
        )
        .toBe('still');
}

// ---------------------------------------------------------------------------
// Before the shot: the frame, and an open dropdown
// ---------------------------------------------------------------------------

/** How long a box — a framed block, a dropdown's trigger, an open dropdown — must stand still, with the frame when asked. */
const BOX_QUIET_MS = 300;

/** How long it may take to stand still. */
const BOX_TIMEOUT = 10_000;

/** How many times a frame is taken from the top before the page that keeps moving under it fails the shot. */
const FRAME_ATTEMPTS = 3;

/**
 * The space TreeSelect leaves between its dropdown and its root, on both sides: `top: rect.bottom + 4` under it, `bottom:
 * innerHeight - rect.top + 4` above it (`updatePosition`), with no margin on the dropdown.
 */
export const DROPDOWN_GAP = 4;

/**
 * The space a table's column filter leaves between its popover and its button, under it: 8 px, two 4 px added up — not a
 * misplacement, the same in every run. DataTableColumnFilter.svelte places the popover with an inline `position: fixed; top:
 * rect.bottom + 4` (`updatePosition`, in `onMount`), and its `.filter-popover` style still carries the `margin-top: 0.25rem`
 * of the absolute layout it had before (`position: absolute; top: 100%`), which moves the box 4 px further down. Upward,
 * the same margin takes the 4 px back — `top: rect.top - popH - 4`, plus 4 — and the popover touches its button (0 px): a
 * check against this gap then fails, with the numbers. The gallery's column-filter shot opens its popover under its button.
 */
export const COLUMN_FILTER_GAP = 8;

/**
 * `target`'s box has not changed for {@link BOX_QUIET_MS} of rendered frames — and, with `withFrame`, neither have the page's
 * scroll and height, the header's `data-scroll-state` and the header's box. Read on the page's own clock, every frame, as
 * {@link scrollStill} reads the frame. On the deadline the failure gives the last reading.
 */
async function standsStill(target: Locator, what: string, withFrame: boolean): Promise<void> {
    await expect
        .poll(
            () =>
                target.evaluate(
                    (element, {quiet, frame}) =>
                        new Promise<string>((resolve) => {
                            const round = (value: number): number => Math.round(value * 10) / 10;
                            const boxOf = (box: DOMRect): string => `${round(box.left)},${round(box.top)} ${round(box.width)}×${round(box.height)}`;
                            const read = (): string => {
                                const own = `box ${boxOf(element.getBoundingClientRect())}`;
                                if (!frame) return own;
                                const header = document.querySelector('[data-testid="app-header"]');
                                const headerState = header ? `${header.getAttribute('data-scroll-state') ?? '-'} ${boxOf(header.getBoundingClientRect())}` : '-';
                                return `${own} · scrollY ${round(window.scrollY)} · height ${document.documentElement.scrollHeight} · header ${headerState}`;
                            };
                            let last = read();
                            let started = -1;
                            let since = -1;
                            const step = (now: number): void => {
                                if (started < 0) started = since = now;
                                const current = read();
                                if (current !== last) {
                                    last = current;
                                    since = now;
                                }
                                if (now - since >= quiet) resolve('still');
                                else if (now - started >= 3 * quiet) resolve(`moving: ${current}`);
                                else requestAnimationFrame(step);
                            };
                            requestAnimationFrame(step);
                        }),
                    {quiet: BOX_QUIET_MS, frame: withFrame},
                ),
            {message: `${what} is still moving`, timeout: BOX_TIMEOUT},
        )
        .toBe('still');
}

/**
 * `target`'s box has not changed for {@link BOX_QUIET_MS} of rendered frames: a block pushed down by a late banner above it,
 * a dropdown still following its trigger. Read every frame, where `waitForStillness` (galleryReportSets.ts) compares two
 * readings a poll apart.
 */
export async function boxStill(target: Locator, what: string): Promise<void> {
    await standsStill(target, what, false);
}

/**
 * Frame `target` for the shot `what`: its top `margin` px under the top of the screen — or as near as the page allows. As
 * galleryRiskLab.ts `frameFromTop` frames — the page brought to its top first, where the header sees it and is visible,
 * then down to the target at once — without asking the header to be gone at the end. The header (Header.svelte) slides
 * away on a scroll down of 8 px only once the page is past the header's own height: a page that ends before the target
 * reaches the top — a broker with few positions — clamps the scroll there, and the header may stay. The same layout clamps
 * at the same place, with the header in the same state, so that frame is as deterministic as the other: what is waited for
 * is the frame standing still — the scroll, the page's height, the header's state and box, the target's box — for
 * {@link BOX_QUIET_MS} of rendered frames. A clamped scroll says so in the log (↕️).
 *
 * Ends on the frame it promises, asserted: the target `margin` px under the top of the screen, or the page at its end, or
 * at its top. A page that changed under the scroll — it grew, or the target moved — is framed again from the top, up to
 * {@link FRAME_ATTEMPTS} times; after that, or when another scroll moved the page, the failure gives the numbers.
 */
export async function frameTarget(page: Page, target: Locator, what: string, margin = 8): Promise<void> {
    await expect(target, `${what}: the block to frame is not on the page`).toBeVisible();
    const round = (value: number): number => Math.round(value * 10) / 10;
    for (let attempt = 1; ; attempt += 1) {
        await page.evaluate(() => window.scrollTo({top: 0, behavior: 'instant'}));
        await renderedFrames(page);
        await expect(page.getByTestId('app-header'), `${what}: the app header is back at the top`).toHaveAttribute('data-scroll-state', 'visible');
        await target.evaluate((element, offset) => {
            window.scrollTo({top: Math.max(0, element.getBoundingClientRect().top + window.scrollY - offset), behavior: 'instant'});
        }, margin);
        await standsStill(target, `${what}: the frame — the scroll, the page's height, the header or the framed block —`, true);
        const frame = await target.evaluate((element) => {
            const root = document.scrollingElement ?? document.documentElement;
            return {
                top: element.getBoundingClientRect().top,
                scrollY: window.scrollY,
                maxScroll: root.scrollHeight - root.clientHeight,
                header: document.querySelector('[data-testid="app-header"]')?.getAttribute('data-scroll-state') ?? '-',
            };
        });
        if (Math.abs(frame.top - margin) <= 1) return;
        if (frame.top > margin && frame.scrollY >= frame.maxScroll - 1) {
            console.log(`  ↕️ ${what}: the page ends before the target reaches the top (scroll clamped at ${Math.round(frame.scrollY)} px, header ${frame.header})`);
            return;
        }
        if (frame.top < margin && frame.scrollY <= 1) {
            console.log(`  ↕️ ${what}: the target starts ${round(frame.top)} px under the top of the page, above the ${margin} px asked (scroll clamped at 0 px, header ${frame.header})`);
            return;
        }
        if (attempt === FRAME_ATTEMPTS) {
            throw new Error(
                `${what}: the framed block stands ${round(frame.top)} px under the top of the screen, not ${margin}, with the page scrolled to ${round(frame.scrollY)} of ${round(frame.maxScroll)} px, after ${FRAME_ATTEMPTS} frames taken from the top: the page keeps changing under the scroll, or another scroll moves it`,
            );
        }
    }
}

/**
 * Bring `trigger` into view for the shot `shot` the same way in every run, before the click that opens a dialog over the
 * page. A dialog locks the page where it stands (ModalBase, `lockBodyScroll`: the body fixed at `top: -<scroll>px`), so the
 * frame behind it is wherever the trigger's scroll left the page — and a bare scroll into view decided that from wherever the
 * clicks before it had left the page, on a page still laying out above the trigger: the trigger in view in one run and left
 * there, out of view in the other and centred. Behind `settings/scheduler-config` the page stood 59 px apart, unseen by the
 * shot's line (🔎) until it read the lock (plan 56). So the page is settled for it first — no `/api/` request in flight, no
 * loader on screen, the trigger's box still ({@link settledToOpen}) — then brought to its top, where the header sees it and
 * is visible, and only then is the trigger scrolled into view: from the top, the same move every time — the page left there
 * when the trigger is on the first screen, else the trigger centred. Both scheduler triggers lie below the first screen on
 * both viewports, so they are centred: behind `scheduler-config` on the desktop that is the frame of the 14/10 baseline,
 * the page locked at 880 px (measured 15/10). Ends on the frame standing still — the scroll, the page's height, the
 * header's state and box, the trigger's box — for {@link BOX_QUIET_MS} of rendered frames, and on the trigger on the
 * screen, asserted.
 */
export async function bringIntoViewFromTop(page: Page, trigger: Locator, shot: string): Promise<void> {
    await expect(trigger, `${shot}: the dialog's trigger is not on the page`).toBeVisible();
    await settledToOpen(page, trigger, shot, "the dialog's trigger");
    await page.evaluate(() => window.scrollTo({top: 0, behavior: 'instant'}));
    await renderedFrames(page);
    await expect(page.getByTestId('app-header'), `${shot}: the app header is back at the top`).toHaveAttribute('data-scroll-state', 'visible');
    await trigger.scrollIntoViewIfNeeded();
    await standsStill(trigger, `${shot}: the frame — the scroll, the page's height, the header or the dialog's trigger —`, true);
    await expect(trigger, `${shot}: the dialog's trigger is not on the screen`).toBeInViewport();
}

/**
 * The page is settled enough to open a dropdown anchored to `anchor`, for a shot of it open: no `/api/` request in flight, no
 * loader on screen, and the anchor's box standing still ({@link boxStill}). TreeSelect and the tables' column filters place
 * their dropdown once, from the anchor's box when it opens, and move it on a scroll or a resize only: opened while the layout
 * above the anchor still moved, the dropdown stayed where it was put — 4 px off its trigger in one run of
 * `assets/detail-signals-tree` and not in the other, with the trigger and the page identical (plan 56). `anchor` is the
 * element whose box the component reads: TreeSelect's root (`data-testid` of the select), a column filter's button.
 * `anchorName` names it in a failure: the trigger of a dialog ({@link bringIntoViewFromTop}) is no dropdown's.
 */
export async function settledToOpen(page: Page, anchor: Locator, shot: string, anchorName = "the dropdown's trigger"): Promise<void> {
    await apiQuiet(page, shot);
    await noLoaderOnScreen(page, shot);
    await boxStill(anchor, `${shot}: ${anchorName}`);
}

/**
 * The open `dropdown` hangs where its component puts it: `gap` px under `anchor`, or `gap` px above it when it opens upward,
 * within a pixel, both boxes read in one layout. The gap is the component's own: TreeSelect's {@link DROPDOWN_GAP} (4 px,
 * either side), a column filter's {@link COLUMN_FILTER_GAP} (8 px under its button). The side is the dropdown's own: under
 * the anchor when its middle is lower than the anchor's. A dropdown placed from a box the anchor has since left fails here
 * with both boxes, rather than being shot.
 */
export async function expectDropdownAt(anchor: Locator, dropdown: Locator, gap: number, what: string): Promise<void> {
    const handle = await dropdown.elementHandle();
    if (!handle) throw new Error(`${what}: the dropdown is not on the page`);
    try {
        const boxes = await anchor.evaluate((element, list) => {
            const own = element.getBoundingClientRect();
            const open = (list as Element).getBoundingClientRect();
            return {anchorTop: own.top, anchorBottom: own.bottom, top: open.top, bottom: open.bottom};
        }, handle);
        const round = (value: number): number => Math.round(value * 10) / 10;
        const under = boxes.top + boxes.bottom >= boxes.anchorTop + boxes.anchorBottom;
        const distance = under ? boxes.top - boxes.anchorBottom : boxes.anchorTop - boxes.bottom;
        expect(
            Math.abs(distance - gap),
            `${what}: the dropdown hangs ${round(distance)} px ${under ? 'under' : 'above'} its trigger, not ${gap} — trigger ${round(boxes.anchorTop)}–${round(boxes.anchorBottom)} px, dropdown ${round(boxes.top)}–${round(boxes.bottom)} px from the top of the screen`,
        ).toBeLessThanOrEqual(1);
    } finally {
        await handle.dispose();
    }
}

// ---------------------------------------------------------------------------
// The settle
// ---------------------------------------------------------------------------

/** Run a helper that does not name the shot, and name it in its failure. */
async function inShot<T>(shot: string, step: () => Promise<T>): Promise<T> {
    try {
        return await step();
    } catch (error) {
        throw new Error(`${shot}: ${error instanceof Error ? error.message : String(error)}`, {cause: error});
    }
}

/** Every toast has left the page — they leave on their own timer — and none is over the shot. */
async function toastsGone(page: Page, shot: string): Promise<void> {
    await expect(page.locator(ANY_TOAST), `${shot}: a toast lies over the shot and did not leave (a shot of a toast passes allowToast)`).toHaveCount(0, {timeout: TOAST_TIMEOUT});
    await inShot(shot, () => expectNoToast(page));
}

/**
 * Settle the page for the shot `shot` (`viewport/lang/theme/category/name`), in the order of this module's header: the
 * pointer parked, the requests answered, no loader, the fonts in, the animations that end ended, the images in, the charts,
 * the text and the frame still, the subject still, no toast — and, last, the looping animations pinned. Then the shot's
 * line in the log (🔎). Every step has its own deadline, and its failure names the shot.
 */
export async function settleShot(page: Page, shot: string, options: ShotOptions = {}): Promise<void> {
    if (options.keepPointer && options.pinnedTooltip) throw new Error(`${shot}: keepPointer and pinnedTooltip exclude each other — the shot of a pinned tooltip parks the pointer`);
    if (!options.keepPointer) {
        await inShot(shot, () => parkPointer(page, {pinnedTooltip: options.pinnedTooltip}));
        // The hover moves with the pointer once a frame is rendered.
        await renderedFrames(page);
        // Placed from its trigger's box when it opened, and again on a scroll or a resize: it must have stopped there.
        if (options.pinnedTooltip) await waitForStillness(page.getByTestId('tooltip-content'), `${shot}: the pinned tooltip`);
    }
    await apiQuiet(page, shot);
    if (!options.allowLoaders) await noLoaderOnScreen(page, shot);
    await inShot(shot, () => fontsLoaded(page));
    const forced = await finishFiniteAnimations(page, shot);
    await imagesInViewComplete(page, shot);
    await chartsStill(page.locator('body'), shot);
    await textStill(page, shot);
    await scrollStill(page, shot);
    if (options.subject) await waitForStillness(options.subject, `${shot}: the subject`);
    // Before the pin, not after it: waiting a toast out takes seconds, and the pin is the last thing that changes the page.
    if (!options.allowToast) await toastsGone(page, shot);
    const pinned = await pinLoopingAnimations(page);
    lastSettle.set(page, {forced, pinned});
    console.log(`  🔎 ${shot} ${await shotFingerprint(page)}`);
}

/**
 * One line of what decides the frame, as compact JSON: `y` the scroll (1 decimal; while a dialog locks the page, the scroll it
 * froze — ModalBase fixes the body at `top: -<scroll>px`, and `window.scrollY` reads 0 under it — followed by `lock` 1, a key
 * written only then), `dh` the page's height, `vh` the screen's, `hdr` the header's `data-scroll-state` (or `-`), `api` the
 * `/api/` requests in flight, `loop` the looping animations the last settle pinned, `fin` the animations it finished by hand,
 * `charts` the render counters of the charts on screen, `preset` the active date preset on screen, `hover` and `focus` the
 * nearest test id of the element under the pointer and of the one with the focus (`-` for none), and `tip` the tooltips on
 * screen — written only when there is one (a shot of a pinned tooltip, `pinnedTooltip`), so the line of every other shot
 * reads as it did before. Two runs of a shot that differ here differ in their frame.
 */
export async function shotFingerprint(page: Page): Promise<string> {
    const settled = lastSettle.get(page) ?? {forced: 0, pinned: 0};
    const seen = await page.evaluate(() => {
        const onScreen = (element: Element): boolean => {
            if (element.getClientRects().length === 0 || getComputedStyle(element).visibility !== 'visible') return false;
            const box = element.getBoundingClientRect();
            return box.width > 0 && box.height > 0 && box.bottom > 0 && box.right > 0 && box.top < window.innerHeight && box.left < window.innerWidth;
        };
        const owner = (element: Element): string => element.closest('[data-testid]')?.getAttribute('data-testid') ?? element.tagName.toLowerCase();
        const hovered = Array.from(document.querySelectorAll(':hover'));
        const deepest = hovered.length > 0 ? hovered[hovered.length - 1] : null;
        const active = document.activeElement;
        const focused = active && active !== document.body && active !== document.documentElement ? active : null;
        // Under a dialog the page cannot scroll: the frame it froze is the body's offset. ModalBase writes `-${scrollY}px`, so a
        // dialog opened at the top locks the page at 0 — read back as `0px` or `-0px`, a lock all the same.
        const body = document.body;
        const lockedAt = body.style.position === 'fixed' && body.style.top.endsWith('px') ? Number.parseFloat(body.style.top) : Number.NaN;
        const locked = lockedAt <= 0;
        return {
            y: Math.round((locked ? -lockedAt : window.scrollY) * 10) / 10,
            locked,
            dh: document.documentElement.scrollHeight,
            vh: window.innerHeight,
            hdr: document.querySelector('[data-testid="app-header"]')?.getAttribute('data-scroll-state') ?? '-',
            charts:
                Array.from(document.querySelectorAll('[data-chart-renders]'))
                    .filter(onScreen)
                    .map((chart) => chart.getAttribute('data-chart-renders') ?? '?')
                    .join(',') || '-',
            preset:
                Array.from(document.querySelectorAll('[data-testid^="date-preset-"][data-active="true"]'))
                    .filter(onScreen)
                    .map((preset) => (preset.getAttribute('data-testid') ?? '').slice('date-preset-'.length))
                    .join(',') || '-',
            hover: deepest ? owner(deepest) : '-',
            focus: focused ? owner(focused) : '-',
            tips: Array.from(document.querySelectorAll('[data-testid="tooltip-content"]')).filter(onScreen).length,
        };
    });
    return JSON.stringify({
        y: seen.y,
        ...(seen.locked ? {lock: 1} : {}),
        dh: seen.dh,
        vh: seen.vh,
        hdr: seen.hdr,
        api: apiInFlight(page).length,
        loop: settled.pinned,
        fin: settled.forced,
        charts: seen.charts,
        preset: seen.preset,
        hover: seen.hover,
        focus: seen.focus,
        ...(seen.tips > 0 ? {tip: seen.tips} : {}),
    });
}

// ---------------------------------------------------------------------------
// The capture
// ---------------------------------------------------------------------------

/**
 * Capture the settled page into `file`, the picture of the shot `shot` (`viewport/lang/theme/category/name`). It is not a
 * step of the test, and has a budget of its own ({@link CAPTURE_TIMEOUT_MS}): the browser's compositor, which the capture
 * waits for, can stall for seconds on a loaded machine. A capture slower than {@link CAPTURE_SLOW_MS} says so in the log
 * (⚠️), so a stall stays visible instead of hidden under the larger budget; a capture that fails names the shot. The page's
 * mixed elements are recorded after the picture, so that the scan cannot change it ({@link recordMixedElements}).
 */
export async function captureShot(page: Page, file: string, shot: string): Promise<void> {
    const started = Date.now();
    await inShot(shot, () =>
        page.screenshot({
            path: file,
            // Never Playwright's full page: it keeps the screen and paints the rest of the page under it, so the sidebar —
            // fixed, one screen tall — stops at the screen's edge. A whole page is a screen as tall as the page
            // (galleryTallShots.ts).
            fullPage: false,
            timeout: CAPTURE_TIMEOUT_MS,
        }),
    );
    const took = Date.now() - started;
    if (took > CAPTURE_SLOW_MS) console.log(`  ⚠️ ${shot}: the browser took ${(took / 1000).toFixed(1)} s to capture the shot`);
    await recordMixedElements(page, shot);
}
