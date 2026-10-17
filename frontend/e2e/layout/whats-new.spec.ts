/**
 * «What’s new since your last version» (C-54, lot A11 of workstream A): after an update, the chapters of the bundled
 * changelog a signed-in user has not seen yet, in a modal. Written RED-FIRST, before the code, on the contract the
 * coordinator approved (17/10):
 *
 *   - `GET /api/v1/auth/me` — and the login answer — carry `user.whats_new: {since: string | null, release: string} | null`;
 *   - the app shows the modal once per page load until it is marked seen: the released chapters of the bundled CHANGELOG.md
 *     with `since < version ≤ release` (`since` null: the `release` chapter alone), never `[Unreleased]`; it waits for the
 *     guides and the other modals — one automatic popup at a time;
 *   - its DOM: `whats-new-modal`; one `whats-new-chapter` per chapter, its version in `data-version`; `whats-new-close`;
 *     `whats-new-full-changelog`, an external link whose `rel` holds `noopener` and `noreferrer`. While it shows, the host
 *     of the automatic popups (`deferred-app-popups`) says `data-active-popup="whats-new"`;
 *   - closing it — the button, Esc — sends `POST /api/v1/auth/whats-new/seen` once.
 *
 * The lane runs with the feature switched off (LIBREFOLIO_DISABLE_WHATS_NEW=1, set by `dev.py server --test` beside the
 * donation popup's switch): its `/auth/me` says `user.whats_new: null`, so no spec signing in as e2e_test_user meets the
 * modal. This spec gives the value to its own page, and writes nothing:
 *   - `GET /api/v1/auth/me` is answered with the real response, `user.whats_new` replaced (`route.fetch()`, then fulfil).
 *     As in fixtures/instance-config.ts, the field is changed in the real answer, never added to one that lacks it — the
 *     backend of C-54 missing is reported by name, in the stub's `problems` —, and the changed answer is checked against
 *     the generated schema, as the client checks it on arrival;
 *   - `POST /api/v1/auth/whats-new/seen` is answered 204 by the spec itself, and counted. It is installed before the sign-in,
 *     so no request of the page to that path ever reaches the lane: nothing is marked seen for the shared user.
 * `page.route()` binds the browser context that installs it (devWiki, problems/playwright-route-stub-is-per-context): no
 * other test sees either stub.
 *
 * Which page load. e2e_test_user signs in untouched — the login answer included —, then the stubs answer a fresh load of
 * /dashboard: a session that outlived an update, whose one user payload is the stubbed `/auth/me`.
 *
 * What to expect is read at run time from the repository's CHANGELOG.md, the file the build bundles: its released chapters
 * (`## [x.y.z] - date` with a body — the app's parser drops an empty one —; `## [Unreleased]` never), the newest one the
 * `release`, the one before it the `since`. No version is written down here. A CHANGELOG.md changed after the last build is
 * not what the running app bundles until the build is redone (the runner rebuilds a stale frontend).
 *
 * An absence is asserted behind presences: this load's `/auth/me` answered through the stub with `user.whats_new` null, the
 * app shell drawn, the dashboard settled (`data-busy` false, well past the point where a due modal shows), the popup host
 * there and not holding the modal. "Exactly one POST" is read once the modal is gone, every request to the path answered by
 * the stub and the host released; WNE-02 reads it again after a reload, when the closed page can send nothing more.
 *
 * Covered (desktop):
 *   WNE-01  `{since, release}`: the modal, the host saying `whats-new`; exactly the chapters `since < v ≤ release` by
 *           `data-version` — the release alone, not the `since` one —; the close button; the full-changelog link, off the
 *           app's origin, `rel` with `noopener` and `noreferrer`, never clicked; nothing posted while it shows; the close
 *           button → the modal gone, the host released, exactly one POST;
 *   WNE-02  after that close, a reload whose `/auth/me` now answers `whats_new: null`: no modal, the host not `whats-new`;
 *           still exactly one POST;
 *   WNE-03  `{since: null, release}`: the release chapter alone — not the one before —; nothing posted while it shows;
 *   WNE-04  Esc, pressed as the user presses it with the modal on screen: the modal gone, the host released, exactly one POST;
 *   WNE-05  on a managed instance (`serveInstanceConfig`: `profile` managed, and two legal pages of this spec's own whose link
 *           in the sidebar proves the managed answer in force before anything else is read): the same modal — host,
 *           chapters, close button, link —, closed by its button, exactly one POST;
 *   WNE-06  `whats_new: null`: never shown; nothing posted.
 * Each test ends on both stubs clean, and on the precondition read through them: the lane's own answer is null.
 *
 * Expected before the code lands: all six red. WNE-01…05 on the modal that never shows — the message quotes the stub's
 * report, which names the missing `user.whats_new` —, WNE-06 on that missing field itself: a negative case does not pass on a
 * lane that does not carry the field it is about.
 *
 * Read-only, parallel by default: the sign-ins of e2e_test_user (a fixture user of the runner, an ordinary member whose
 * onboarding is read back — never changed — so that no guide holds the popup back), GET requests, and POSTs answered by the
 * spec. No link is clicked, no setting written, the language never touched; assertions read test ids, attributes and the
 * stubs' records, never a translated text.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `whats-new` of front-utility.
 */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import type {APIResponse} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login} from '../fixtures/auth-helpers';
import {serveInstanceConfig, type InstanceConfigStub, type ServedInstanceConfig} from '../fixtures/instance-config';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';

/** What `user.whats_new` carries when there is something to show: the last release the user saw (null: none recorded), and the running one. */
type WhatsNew = {since: string | null; release: string};

/** The user payload the app reads on every page load (the (app) layout's `auth.checkAuth()`). */
const AUTH_ME_PATH = '/api/v1/auth/me';
/** Where closing the modal marks it seen. */
const SEEN_PATH = '/api/v1/auth/whats-new/seen';

/** Two pages of this spec's own, on a reserved domain, served by the instance stub alone and never opened: WNE-05's proof. */
const TERMS_URL = 'https://legal.example.org/librefolio-e2e/terms?lot=c54';
const PRIVACY_URL = 'https://legal.example.org/librefolio-e2e/privacy?lot=c54';

/** The popup host's `data-active-popup` once the modal has let go: present, and anything but `whats-new`. */
const NOT_WHATS_NEW = /^(?!whats-new$).+$/;
const NO_OPENER = /(?:^|\s)noopener(?:\s|$)/;
const NO_REFERRER = /(?:^|\s)noreferrer(?:\s|$)/;

// Budgets: deadlines, never delays.
/** A load of an app page to its shell: GET /auth/me, then the bootstrap's reads (login()'s ARRIVAL_MS on a loaded lane). */
const APP_MS = 30_000;
/** The stub's handler done with the load's GET /auth/me: the shell needs that answer, so this is a formality once it shows. */
const STUB_MS = 15_000;
/** From the app shell to the modal on screen: the popup host's turn, and the modal's chunk on a loaded lane. */
const POPUP_MS = 15_000;
/** What waits for the instance configuration: GET /api/v1/system/instance, through the stub. */
const CONFIG_MS = 15_000;
/** The dashboard's load waves (report, contributions): the late barrier of an absence (fx-flag-font.spec.ts gives it the same). */
const SETTLE_MS = 30_000;
/** The reaction to a click or a key on something already on screen. */
const UI_MS = 5_000;

// A red must end on its own assertion, not on the test timeout: login() may take 70 s and still return (app-start-auth's
// account: 10 s, a 10 s retry, 20 s on the sign-in, 30 s on the arrival), then one wait of this file may run out (APP_MS,
// 30 s) while the rest goes at a loaded pace. WNE-02, with a second load and the dashboard's waves, raises its own.
test.setTimeout(120_000);

// Desktop only, as the runner runs it (_run_playwright's default project): the subject does not depend on the viewport,
// and WNE-05's proof is the sidebar's legal line, off-canvas on a phone.
test.skip(({isMobile}) => isMobile, 'Desktop only: the modal does not depend on the viewport, and WNE-05’s proof (sidebar-legal-links) is off-canvas on a phone');

// ── The changelog the build bundles ─────────────────────────────────────────────────────────────────────────────────────

/** A chapter heading, as src/lib/features/changelog/changelog.ts reads it (CHAPTER_HEADING, copied): the version between the brackets, then an optional date. */
const CHAPTER_HEADING = /^## \[([^\]]+)\](?:\s*-\s*(.+?))?\s*$/;
/** A released version: three numbers. `Unreleased` is none. */
const RELEASED_VERSION = /^\d+\.\d+\.\d+$/;

/** `a` against `b`, number by number: negative when `a` is older. Both are x.y.z. */
function compareVersions(a: string, b: string): number {
    const left = a.split('.').map(Number);
    const right = b.split('.').map(Number);
    for (let i = 0; i < 3; i += 1) {
        const delta = (left[i] ?? 0) - (right[i] ?? 0);
        if (delta !== 0) return delta;
    }
    return 0;
}

/**
 * The released chapters of the repository's CHANGELOG.md, newest first: a heading with an x.y.z version and a date, and a
 * body — the app's parser drops a chapter whose body is blank. `## [Unreleased]` has neither number nor date.
 */
function releasedVersions(): string[] {
    const path = fileURLToPath(new URL('../../../CHANGELOG.md', import.meta.url));
    const chapters: Array<{version: string; date: string | undefined; body: boolean}> = [];
    for (const line of readFileSync(path, 'utf8').split('\n')) {
        const heading = CHAPTER_HEADING.exec(line);
        if (heading) chapters.push({version: heading[1], date: heading[2], body: false});
        else if (chapters.length > 0 && line.trim().length > 0) chapters[chapters.length - 1].body = true;
    }
    const released = chapters.filter((chapter) => RELEASED_VERSION.test(chapter.version) && chapter.date !== undefined && chapter.body).map((chapter) => chapter.version);
    return [...new Set(released)].sort((a, b) => compareVersions(b, a));
}

/** What a test reads from the changelog: every released version (newest first), the newest one, and the one before it. */
function changelogPlan(): {versions: string[]; release: string; previous: string} {
    const versions = releasedVersions();
    expect(versions.length, 'positive control: CHANGELOG.md has at least two released chapters (`## [x.y.z] - date`, with a body)').toBeGreaterThanOrEqual(2);
    return {versions, release: versions[0], previous: versions[1]};
}

/** The chapters the modal must show for `whatsNew`: the released ones with since < v ≤ release; with no `since`, the release alone. */
function chaptersFor(versions: readonly string[], whatsNew: WhatsNew): string[] {
    const {since, release} = whatsNew;
    if (since === null) return versions.filter((version) => compareVersions(version, release) === 0);
    return versions.filter((version) => compareVersions(version, since) > 0 && compareVersions(version, release) <= 0);
}

// ── The stubs ───────────────────────────────────────────────────────────────────────────────────────────────────────────

/**
 * The real answer's headers, without the two that describe its body as it travelled (fixtures/instance-config.ts,
 * `servableHeaders`): `route.fetch()` hands the body over decoded, and a fulfilled body is served exactly as given.
 */
function servableHeaders(response: APIResponse): Record<string, string> {
    const headers = {...response.headers()};
    delete headers['content-encoding'];
    delete headers['content-length'];
    return headers;
}

const isPlainObject = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);

/**
 * What the GET /auth/me stub saw. Every counter is written by the route handler itself, so a poll on it reads what the
 * handler has done (devWiki, problems/request-counter-read-before-the-handler-counted).
 */
type AuthMeStub = {
    /** Reads that reached the stub. */
    readonly requested: number;
    /** Reads the stub has finished with, answered as asked or not: compare `problems`. */
    readonly answered: number;
    /** The `user.whats_new` each changed answer carried, in order. */
    readonly served: readonly (WhatsNew | null)[];
    /** The `user.whats_new` the lane's own answer carried, read by read, before the change. */
    readonly lane: readonly unknown[];
    /** Why a read was not answered as asked: a broken precondition, reported by name. */
    readonly problems: readonly string[];
    /** The value the next reads carry; a read in flight keeps the one it arrived with. */
    set(value: WhatsNew | null): void;
    /** Remove the route. Call it in `finally`. */
    dispose(): Promise<void>;
};

const isAuthMe = (url: URL): boolean => url.pathname === AUTH_ME_PATH;

/**
 * Answer this page's `GET /api/v1/auth/me` — that path only — with the real response and `user.whats_new` set to `value`.
 * The field is changed in the real answer, never added: a real answer without `user.whats_new` (the backend of C-54
 * missing), or without a `user`, or not OK, is passed through as it came, with the reason in `problems`. The changed answer
 * is checked against the generated schema before it is served, as the client checks it on arrival: a refusal is recorded
 * in `problems` too. Any other method falls through: nothing here writes.
 */
async function serveWhatsNew(page: Page, value: WhatsNew | null): Promise<AuthMeStub> {
    let current = value;
    let requested = 0;
    let answered = 0;
    const served: (WhatsNew | null)[] = [];
    const lane: unknown[] = [];
    const problems: string[] = [];

    const handler: Parameters<Page['route']>[1] = async (route, request) => {
        if (request.method() !== 'GET') {
            await route.fallback();
            return;
        }
        requested += 1;
        const asked = current;
        try {
            const response = await route.fetch();
            const asItCame = async () => route.fulfill({status: response.status(), headers: servableHeaders(response), body: await response.body()});
            if (!response.ok()) {
                problems.push(`the real GET ${AUTH_ME_PATH} answered ${response.status()}`);
                await asItCame();
                return;
            }
            const body = (await response.json()) as Record<string, unknown>;
            const user = body.user;
            if (!isPlainObject(user)) {
                problems.push(`the real GET ${AUTH_ME_PATH} has no user object (keys: ${Object.keys(body).join(', ') || 'none'})`);
                await asItCame();
                return;
            }
            if (!('whats_new' in user)) {
                problems.push(`the real GET ${AUTH_ME_PATH} has no user.whats_new (user keys: ${Object.keys(user).join(', ') || 'none'}): the backend of C-54 is missing — the stub changes the field, never adds it`);
                await asItCame();
                return;
            }
            lane.push(user.whats_new);
            const changed = {...body, user: {...user, whats_new: asked}};
            const checked = schemas.AuthMeResponse.safeParse(changed);
            if (!checked.success) problems.push(`the answer with user.whats_new ${JSON.stringify(asked)} fails the generated schema: ${checked.error.message}`);
            await route.fulfill({status: response.status(), headers: servableHeaders(response), json: changed});
            served.push(asked);
        } catch (error) {
            // Nobody awaits a route callback: what it throws would surface as an unhandled rejection on whatever the worker
            // runs next. Recorded instead, and asserted by the test.
            problems.push(`the stub failed: ${String(error)}`);
        } finally {
            answered += 1;
        }
    };
    await page.route(isAuthMe, handler);

    return {
        get requested() {
            return requested;
        },
        get answered() {
            return answered;
        },
        get served() {
            return served;
        },
        get lane() {
            return lane;
        },
        get problems() {
            return problems;
        },
        set: (next) => {
            current = next;
        },
        dispose: async () => {
            await page.unroute(isAuthMe, handler);
        },
    };
}

/** What the POST /auth/whats-new/seen stub saw, counted by its handler (as above). */
type SeenStub = {
    /** Requests that reached the path, whatever their method. */
    readonly requested: number;
    /** POSTs among them, counted on arrival: the order the page sent them in is the order they are counted in. */
    readonly posts: number;
    /** Requests the stub has finished with. */
    readonly answered: number;
    /** Anything but a POST, or a request the stub failed to answer. */
    readonly problems: readonly string[];
    /** Remove the route. Call it in `finally`. */
    dispose(): Promise<void>;
};

const isSeen = (url: URL): boolean => url.pathname === SEEN_PATH;

/**
 * Answer every request of this page to `/api/v1/auth/whats-new/seen` here: a POST 204, anything else 405 and a problem
 * recorded. None reaches the lane, so nothing is marked seen for the shared user.
 */
async function answerSeen(page: Page): Promise<SeenStub> {
    let requested = 0;
    let posts = 0;
    let answered = 0;
    const problems: string[] = [];

    const handler: Parameters<Page['route']>[1] = async (route, request) => {
        requested += 1;
        const method = request.method();
        if (method === 'POST') posts += 1;
        else problems.push(`a ${method} reached ${SEEN_PATH}: the contract has a POST alone (answered 405 by the stub, not by the lane)`);
        try {
            await route.fulfill({status: method === 'POST' ? 204 : 405});
        } catch (error) {
            problems.push(`the stub failed: ${String(error)}`);
        } finally {
            answered += 1;
        }
    };
    await page.route(isSeen, handler);

    return {
        get requested() {
            return requested;
        },
        get posts() {
            return posts;
        },
        get answered() {
            return answered;
        },
        get problems() {
            return problems;
        },
        dispose: async () => {
            await page.unroute(isSeen, handler);
        },
    };
}

/** The stub's record, for a message: what it answered and what went wrong. */
function describeStub(me: AuthMeStub): string {
    return `GET ${AUTH_ME_PATH} through the stub: ${me.answered} answered, served ${JSON.stringify(me.served)}, the lane carried ${JSON.stringify(me.lane)}; problems: ${me.problems.join(' | ') || 'none'}`;
}

/** What both stubs saw: every read answered as asked, nothing but POST on the seen path, and the lane's own answer null. */
function expectStubsClean(me: AuthMeStub, seen: SeenStub): void {
    expect(me.problems, `the GET ${AUTH_ME_PATH} stub answered every read as asked`).toEqual([]);
    expect(seen.problems, `nothing but POST reached ${SEEN_PATH}, and every request was answered by the stub`).toEqual([]);
    expect(me.lane.length, 'the stub changed at least one real answer').toBeGreaterThan(0);
    expect(me.lane, `precondition: the lane's own GET ${AUTH_ME_PATH} carries user.whats_new null — LIBREFOLIO_DISABLE_WHATS_NEW=1, set by dev.py server --test — so no other spec signing in as ${TEST_USER.username} meets the modal`).toEqual(me.lane.map(() => null));
}

/**
 * Run `body` signed in as e2e_test_user with `whatsNew` on every later GET /auth/me of the page. The seen stub goes first,
 * before the sign-in, so that no request of this page to that path can reach the lane; the /auth/me stub after it, so the
 * sign-in is the lane's own. Ends on both stubs clean; removes them whatever happens.
 */
async function withWhatsNew(page: Page, whatsNew: WhatsNew | null, body: (stubs: {me: AuthMeStub; seen: SeenStub}) => Promise<void>): Promise<void> {
    const seen = await answerSeen(page);
    let me: AuthMeStub | undefined;
    try {
        await signIn(page);
        me = await serveWhatsNew(page, whatsNew);
        await body({me, seen});
        expectStubsClean(me, seen);
    } finally {
        await me?.dispose();
        await seen.dispose();
    }
}

// ── The page ────────────────────────────────────────────────────────────────────────────────────────────────────────────

/** Sign e2e_test_user in, untouched; ends on the app shell, with no onboarding flow due (read back): a guide holds every automatic popup back. */
async function signIn(page: Page): Promise<void> {
    await login(page, TEST_USER);
    await expect(page.getByTestId('app-shell'), `${TEST_USER.username} arrives on the app shell`).toBeVisible();
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `${TEST_USER.username} must be grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

/**
 * A fresh page load — /dashboard unless `navigate` says otherwise —, ending on the app shell with this load's GET /auth/me
 * finished by the stub. The shell is drawn only once the auth store holds that answer.
 */
async function loadApp(page: Page, me: AuthMeStub, navigate: () => Promise<unknown> = () => page.goto('/dashboard')): Promise<void> {
    const before = me.answered;
    await navigate();
    await expect(page.getByTestId('app-shell'), 'the app shell, once this load’s GET /auth/me has answered').toBeVisible({timeout: APP_MS});
    await expect.poll(() => me.answered, {message: `this load read GET ${AUTH_ME_PATH} through the stub`, timeout: STUB_MS}).toBeGreaterThan(before);
}

/** The popup host: `display: contents`, so it is read by its attributes, never by its visibility. */
function popupHost(page: Page): Locator {
    return page.getByTestId('deferred-app-popups');
}

/** The modal on screen for this load, and the popup host saying it is the automatic popup showing. */
async function expectShown(page: Page, me: AuthMeStub): Promise<Locator> {
    const modal = page.getByTestId('whats-new-modal');
    await expect(modal, `the what’s new modal shows for this load (${describeStub(me)})`).toBeVisible({timeout: POPUP_MS});
    await expect(popupHost(page), 'the popup host: the what’s new modal is the automatic popup showing').toHaveAttribute('data-active-popup', 'whats-new');
    return modal;
}

function chapterOf(modal: Locator, version: string): Locator {
    return modal.locator(`[data-testid="whats-new-chapter"][data-version="${version}"]`);
}

/** The `data-version` of every chapter on show, sorted: a plain value, for expect.poll. */
async function shownVersions(modal: Locator): Promise<string[]> {
    const versions = await modal.getByTestId('whats-new-chapter').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-version') ?? '(no data-version)'));
    return versions.sort();
}

/** Exactly `expected` among the chapters, by `data-version`: each on screen once, none other — `absent` named, for the message. */
async function expectChapters(modal: Locator, expected: readonly string[], absent: readonly string[]): Promise<void> {
    for (const version of expected) await expect(chapterOf(modal, version), `the chapter of ${version}`).toBeVisible({timeout: UI_MS});
    await expect.poll(() => shownVersions(modal), {message: `exactly the chapters ${expected.join(', ')} by data-version — none other, ${absent.join(' nor ')} included, never Unreleased`, timeout: UI_MS}).toEqual([...expected].sort());
    for (const version of absent) await expect(chapterOf(modal, version), `no chapter for ${version}`).toHaveCount(0);
}

/** The close button, and the link to the full changelog: an absolute address off the app's origin, without opener or referrer. Never clicked. */
async function expectControls(page: Page, modal: Locator): Promise<void> {
    await expect(modal.getByTestId('whats-new-close'), 'the close button').toBeVisible();
    const link = modal.getByTestId('whats-new-full-changelog');
    await expect(link, 'the link to the full changelog').toBeVisible();
    await expect(link, 'an absolute address').toHaveAttribute('href', /^https?:\/\/\S+$/);
    const href = (await link.getAttribute('href')) ?? '';
    expect(new URL(href).origin, `external: ${href} is off the app’s own origin`).not.toBe(new URL(page.url()).origin);
    await expect(link, 'without opener').toHaveAttribute('rel', NO_OPENER);
    await expect(link, 'without referrer').toHaveAttribute('rel', NO_REFERRER);
}

/** After a close by `how`: the modal gone, every request to the seen path answered, the host released, exactly one POST. */
async function expectClosedOnce(page: Page, modal: Locator, seen: SeenStub, how: string): Promise<void> {
    await expect(modal, `${how}: the modal is gone`).toBeHidden({timeout: UI_MS});
    await expect.poll(() => seen.posts, {message: `${how}: POST ${SEEN_PATH} sent`, timeout: UI_MS}).toBeGreaterThan(0);
    await expect.poll(() => seen.requested - seen.answered, {message: `every request to ${SEEN_PATH} answered by the stub`, timeout: UI_MS}).toBe(0);
    await expect(popupHost(page), `${how}: the popup host no longer holds the what’s new modal`).toHaveAttribute('data-active-popup', NOT_WHATS_NEW);
    expect(seen.posts, `${how}: exactly one POST ${SEEN_PATH}`).toBe(1);
}

/**
 * No modal for this load — an absence behind presences: this load's GET /auth/me carried `user.whats_new` null, the app shell
 * is drawn (loadApp), and the dashboard has settled — its load waves start once the shell is drawn and end well past the
 * point where a due modal shows —; then the popup host is there and not holding the modal, and no modal is on screen.
 */
async function expectNotShown(page: Page, me: AuthMeStub): Promise<void> {
    expect(me.served.at(-1), `this load's GET ${AUTH_ME_PATH} carried user.whats_new null (${describeStub(me)})`).toBeNull();
    await waitForSettled(page.getByTestId('dashboard-page'), SETTLE_MS);
    await expect(popupHost(page), 'the popup host is there, and not holding the what’s new modal').toHaveAttribute('data-active-popup', NOT_WHATS_NEW);
    await expect(page.getByTestId('whats-new-modal'), 'no what’s new modal').toBeHidden();
}

/**
 * The instance configuration the page read is the one meant (legal-and-managed.spec.ts): the stub has finished a read,
 * nothing went wrong on the way, and every answer carried `expected`.
 */
async function expectServed(instance: InstanceConfigStub, expected: Partial<ServedInstanceConfig>, what: string): Promise<void> {
    await expect.poll(() => instance.answered, {message: 'the page read GET /api/v1/system/instance through the stub', timeout: CONFIG_MS}).toBeGreaterThan(0);
    expect(instance.problems, 'the instance stub answered every read as asked').toEqual([]);
    expect(instance.served.length, 'the instance stub served at least one answer').toBeGreaterThan(0);
    for (const [index, answer] of instance.served.entries()) expect(answer, `${what} (read ${index + 1} of GET /api/v1/system/instance)`).toMatchObject(expected);
}

/** What has the focus, for a message: a key goes there. */
async function focusedElement(page: Page): Promise<string> {
    return page.evaluate(() => {
        const element = document.activeElement;
        if (!element || element === document.body) return 'the page body';
        const testId = element.getAttribute('data-testid');
        return `${element.tagName.toLowerCase()}${testId ? `[data-testid="${testId}"]` : ''}`;
    });
}

// ── The tests ───────────────────────────────────────────────────────────────────────────────────────────────────────────

test.describe('What’s new since your last version — self-hosted', () => {
    test('WNE-01: {since, release} — the modal with exactly the chapters since < v ≤ release, its close button and its external link; the close button marks it seen with exactly one POST', async ({page}) => {
        const {versions, release, previous} = changelogPlan();
        const whatsNew: WhatsNew = {since: previous, release};
        const expected = chaptersFor(versions, whatsNew);
        expect(expected, `positive control: the range (${previous}, ${release}] holds the ${release} chapter alone`).toEqual([release]);

        await withWhatsNew(page, whatsNew, async ({me, seen}) => {
            await loadApp(page, me);
            const modal = await expectShown(page, me);
            await expectChapters(modal, expected, [previous]);
            await expectControls(page, modal);
            expect(seen.posts, 'showing the modal marks nothing seen: closing it does').toBe(0);

            await modal.getByTestId('whats-new-close').click();
            await expectClosedOnce(page, modal, seen, 'the close button');
        });
    });

    test('WNE-02: after the close, a reload whose /auth/me answers whats_new null — no modal, the host not holding it, still exactly one POST', async ({page}) => {
        // A second page load and the dashboard's load waves on top of WNE-01's path.
        test.setTimeout(150_000);
        const {release, previous} = changelogPlan();

        await withWhatsNew(page, {since: previous, release}, async ({me, seen}) => {
            await loadApp(page, me);
            const modal = await expectShown(page, me);
            await modal.getByTestId('whats-new-close').click();
            await expectClosedOnce(page, modal, seen, 'the close button');

            // Marked seen: from now on the server answers null.
            me.set(null);
            await loadApp(page, me, () => page.reload());
            await expectNotShown(page, me);
            expect(seen.posts, `still exactly one POST ${SEEN_PATH}: the closed page sent no other, the reloaded one none`).toBe(1);
        });
    });

    test('WNE-03: {since: null, release} — the release chapter alone, not the one before; nothing posted while it shows', async ({page}) => {
        const {versions, release, previous} = changelogPlan();
        const whatsNew: WhatsNew = {since: null, release};
        const expected = chaptersFor(versions, whatsNew);
        expect(expected, `positive control: with no since, the ${release} chapter alone`).toEqual([release]);

        await withWhatsNew(page, whatsNew, async ({me, seen}) => {
            await loadApp(page, me);
            const modal = await expectShown(page, me);
            await expectChapters(modal, expected, [previous]);
            expect(seen.posts, 'showing the modal marks nothing seen: closing it does').toBe(0);
        });
    });

    test('WNE-04: Esc, pressed with the modal on screen — the modal gone, the host released, exactly one POST', async ({page}) => {
        const {release, previous} = changelogPlan();

        await withWhatsNew(page, {since: previous, release}, async ({me, seen}) => {
            await loadApp(page, me);
            const modal = await expectShown(page, me);
            await expect(chapterOf(modal, release), 'the modal is drawn: its chapter on screen').toBeVisible({timeout: UI_MS});
            expect(seen.posts, 'showing the modal marks nothing seen: closing it does').toBe(0);

            // The key as the user presses it: wherever the open modal put the focus, nowhere chosen by the test.
            const focus = await focusedElement(page);
            await page.keyboard.press('Escape');
            await expectClosedOnce(page, modal, seen, `Esc (pressed with the focus on ${focus})`);
        });
    });

    test('WNE-06: whats_new null — never shown, nothing posted', async ({page}) => {
        await withWhatsNew(page, null, async ({me, seen}) => {
            await loadApp(page, me);
            await expectNotShown(page, me);
            expect(seen.posts, 'nothing marked seen').toBe(0);
        });
    });
});

test.describe('What’s new since your last version — managed', () => {
    test('WNE-05: profile managed — once the sidebar links the stubbed terms page, the same modal: host, chapters, close button, link; the close button, exactly one POST', async ({page}) => {
        const {versions, release, previous} = changelogPlan();
        const whatsNew: WhatsNew = {since: previous, release};
        const expected = chaptersFor(versions, whatsNew);

        await withWhatsNew(page, whatsNew, async ({me, seen}) => {
            // Before the load: the app reads the configuration once per page load (instanceConfig.svelte.ts).
            const instance = await serveInstanceConfig(page, {profile: 'managed', legal: {terms_url: TERMS_URL, privacy_url: PRIVACY_URL}});
            try {
                await loadApp(page, me);
                // The proof, before the modal is read: a link to the stubbed terms page comes from the stubbed answer alone, and
                // the store takes an answer whole, its `profile` in the same step (legal-and-managed.spec.ts, LGM-E-04). The
                // attribute is read behind the modal's backdrop: no visibility needed.
                await expect(page.getByTestId('sidebar-legal-links').getByTestId('legal-terms-link'), 'the proof: the sidebar links the terms page only the stubbed, managed answer carries').toHaveAttribute('href', TERMS_URL, {timeout: CONFIG_MS});
                await expectServed(instance, {profile: 'managed'}, 'the stub served a managed instance');

                const modal = await expectShown(page, me);
                await expectChapters(modal, expected, [previous]);
                await expectControls(page, modal);
                expect(seen.posts, 'showing the modal marks nothing seen: closing it does').toBe(0);

                await modal.getByTestId('whats-new-close').click();
                await expectClosedOnce(page, modal, seen, 'the close button, managed');
                expect(instance.problems, 'the instance stub answered every read as asked').toEqual([]);
            } finally {
                await instance.dispose();
            }
        });
    });
});
