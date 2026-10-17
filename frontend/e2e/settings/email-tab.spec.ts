/**
 * Settings › Administration › Email E2E (workstream E, lot E2b): the administrators' Email tab.
 *
 * Two halves:
 *   - on the lane's own backend: an administrator opens the tab through `?tab=email` and finds email off — the lane runs
 *     without an SMTP server, a precondition read from `GET /api/v1/email/status` before anything is asserted on screen —
 *     explained, with the administrators' guide one click away; a user has no Email tab, and `?tab=email` opens the
 *     first tab a user sees instead;
 *   - on a simulated server (`page.route` on `/api/v1/email/status` and `/api/v1/email/test`, owned by each test and
 *     unrouted by it): email ready, 48 of 50 emails left this hour, a warning notice; a test email accepted (200),
 *     refused by the SMTP server (502 EMAIL_DELIVERY_FAILED, AUTH_FAILED) and refused by the hourly limit (429
 *     EMAIL_RATE_LIMITED). Each answer reaches the tab through the generated client as it really rejects — the
 *     composition that once read every refusal as UNKNOWN (lot E2) — and is recorded as an event of `notify()`; the
 *     status is read again after every attempt. The routes answer their path and their method only — `GET` the status,
 *     `POST` the test email — and let anything else fall back. What a success sends is checked against the generated
 *     schemas (`EmailStatusResponse`, `EmailTestResponse`), as the client checks it on arrival; a refusal is a plain
 *     `detail` error, which has no generated schema.
 *
 * Nothing here sends an email or writes a row: the real backend is only read, and the test email only ever reaches the
 * simulated server. No test shares state with another, so the file runs in parallel (the config's default).
 * Assertions read test ids, `data-*`, `aria-selected` and the events, never a translated text.
 *
 * Prerequisites: test users created (`e2e_test_admin` an administrator, `e2e_test_user` not); no SMTP server configured
 * on the lane (`LIBREFOLIO_SMTP_HOST` unset).
 */
import type {Route} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, type Locator, type Page, test} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';

const STATUS_PATH = '/api/v1/email/status';
const TEST_PATH = '/api/v1/email/test';
const isStatus = (url: URL): boolean => url.pathname === STATUS_PATH;
const isTest = (url: URL): boolean => url.pathname === TEST_PATH;

/** What the two endpoints answer on success, as the generated client types it. */
type EmailStatusResponse = ReturnType<typeof schemas.EmailStatusResponse.parse>;
type EmailTestResponse = ReturnType<typeof schemas.EmailTestResponse.parse>;

/** The administrators' page on email, in English or under a language prefix: what the tab's DocsLink opens. */
const DOCS_PAGE = /\/mkdocs\/(?:[a-z]{2}\/)?admin\/email\/$/;

/**
 * A status as `GET /api/v1/email/status` answers it (`backend/app/schemas/email.py`): ready, this budget, a warning
 * notice. Checked against the generated schema when it is built: a contract that moved fails here, with Zod's message.
 */
function readyStatus(remaining: number, retryAfterSeconds = 0): EmailStatusResponse {
    return schemas.EmailStatusResponse.parse({
        state: 'ready',
        problem: null,
        variable: null,
        checks: [
            {check_id: 'email.smtp', severity: 'ok', i18n_key: 'email.checks.smtp.ok', detail: {}},
            {check_id: 'email.smtp_encryption', severity: 'warning', i18n_key: 'email.checks.smtpEncryption.plain', detail: {}},
        ],
        budget: {max_per_hour: 50, remaining, retry_after_seconds: retryAfterSeconds},
    });
}

/** How the simulated server answers `POST /api/v1/email/test`: the email sent, or a refusal (a plain `detail` error). */
interface TestAnswer {
    status: number;
    body: EmailTestResponse | {detail: Record<string, unknown>};
    headers?: Record<string, string>;
}

/** The test email sent, in this language: checked against the generated schema. */
function sentAnswer(language: EmailTestResponse['language']): TestAnswer {
    return {status: 200, body: schemas.EmailTestResponse.parse({language, message: 'Test email sent'})};
}

interface SimulatedServer {
    /** How many times the tab has read the status (`GET`s answered). */
    statusReads: () => number;
    /** The method of every request the test email path received, answered or fallen back. */
    testRequests: string[];
    /** Let a held test email be answered. */
    release: () => void;
    /** Drop both routes (releasing a held answer first): each test owns its own. */
    unroute: () => Promise<void>;
}

/**
 * Answer the Email tab from a simulated server: the status (`before` until a test email has been asked for, `after` from
 * then on) and the test email (`answer`). Each route answers its path and its method only — `GET` the status, `POST`
 * the test email — and lets anything else fall back. With `hold`, the test email's answer waits for `release()`, so
 * that "in flight" is a state the test controls rather than a moment it races.
 */
async function simulateEmailServer(page: Page, {before, after, answer, hold = false}: {before: EmailStatusResponse; after: EmailStatusResponse; answer: TestAnswer; hold?: boolean}): Promise<SimulatedServer> {
    let reads = 0;
    let asked = false;
    const testRequests: string[] = [];
    let release: () => void = () => undefined;
    const released = new Promise<void>((resolve) => {
        release = () => resolve();
    });
    if (!hold) release();

    const status = async (route: Route) => {
        if (route.request().method() !== 'GET') return route.fallback();
        reads += 1;
        await route.fulfill({json: asked ? after : before});
    };
    const sendTest = async (route: Route) => {
        testRequests.push(route.request().method());
        if (route.request().method() !== 'POST') return route.fallback();
        asked = true;
        await released;
        await route.fulfill({status: answer.status, headers: answer.headers, json: answer.body});
    };
    await page.route(isStatus, status);
    await page.route(isTest, sendTest);
    return {
        statusReads: () => reads,
        testRequests,
        release: () => release(),
        unroute: async () => {
            release();
            await page.unroute(isStatus, status);
            await page.unroute(isTest, sendTest);
        },
    };
}

/** Sign the administrator in and open Settings › Administration › Email through its URL; the tab, once its first read has landed. */
async function openEmailTab(page: Page): Promise<Locator> {
    await login(page, TEST_ADMIN);
    await navigateTo(page, '/settings?tab=email');
    await expect(page.getByTestId('settings-tab-email'), '?tab=email opens the Email tab').toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
    const tab = page.getByTestId('email-tab');
    await waitForSettled(tab);
    return tab;
}

test.describe('Settings › Administration › Email — on the lane’s backend', () => {
    test('an administrator opens it with ?tab=email: email is off, explained, and the guide is one click away', async ({page}) => {
        await login(page, TEST_ADMIN);
        // The precondition, read before anything on screen: this lane runs without an SMTP server.
        const answer = await page.request.get('/api/v1/email/status');
        expect(answer.status(), 'GET /api/v1/email/status answers an administrator').toBe(200);
        const status = (await answer.json()) as {state?: unknown};
        expect(status.state, 'precondition: the lane has no SMTP server (LIBREFOLIO_SMTP_HOST unset), so its email is off — what this test asserts on screen').toBe('off');

        await navigateTo(page, '/settings?tab=email');

        await expect(page.getByTestId('settings-tab-email'), '?tab=email opens the Email tab').toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
        await waitForSettled(page.getByTestId('email-tab'));
        await expect(page.getByTestId('email-state')).toHaveAttribute('data-state', 'off');
        await expect(page.getByTestId('email-off-explanation')).toBeVisible();
        await expect(page.getByTestId('email-test'), 'no test email while email is off').toHaveCount(0);

        const opened = page.waitForEvent('popup');
        await page.getByTestId('email-docs').click();
        const docs = await opened;
        await docs.waitForURL(DOCS_PAGE, {waitUntil: 'commit'});
        await docs.close();
    });

    test('a user has no Email tab, and ?tab=email opens the first tab instead', async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/settings?tab=email');

        // Presence first: the bar is drawn, its right-hand group included, and the first tab a user sees (profile: the
        // registry's order, pinned by settingsTabs.test.ts) is the one open.
        await expect(page.getByTestId('settings-tab-administration'), 'the right-hand group, where Email would stand, is drawn').toBeVisible({timeout: 10_000});
        await expect(page.getByTestId('settings-tab-profile'), '?tab=email names no tab of a user: the first one opens').toHaveAttribute('aria-selected', 'true');
        await expect(page.getByTestId('profile-tab')).toBeVisible();
        // Then the absence: no Email tab in the bar, and its body never mounted. «Administration» stands for Global
        // Settings alone here (decision P13 b): no second bar, no member tab at all.
        await expect(page.getByTestId('settings-tab-admin')).toHaveCount(0);
        await expect(page.getByTestId('settings-tab-email')).toHaveCount(0);
        await expect(page.getByTestId('email-tab')).toHaveCount(0);
    });
});

test.describe('Settings › Administration › Email — a test email, on a simulated server', () => {
    test('ready, 48 of 50 left, a warning: the test email is sent, recorded, and the status read again', async ({page}) => {
        const server = await simulateEmailServer(page, {before: readyStatus(48), after: readyStatus(47), answer: sentAnswer('en'), hold: true});
        try {
            const tab = await openEmailTab(page);
            await expect(page.getByTestId('email-state')).toHaveAttribute('data-state', 'ready');
            const budget = page.getByTestId('email-budget');
            await expect(budget).toHaveAttribute('data-remaining', '48');
            await expect(budget).toHaveAttribute('data-max', '50');
            await expect(page.locator('[data-testid="email-check"][data-check-id="email.smtp_encryption"]'), 'the warning is listed').toHaveAttribute('data-severity', 'warning');
            await expect(page.locator('[data-testid="email-check"][data-check-id="email.smtp"]'), 'an ok check is not').toHaveCount(0);
            const button = page.getByTestId('email-test-button');
            await expect(button).toBeEnabled();

            const since = await eventSeq(page);
            await button.click();

            // In flight: the simulated server holds its answer until the tab has been seen busy.
            await expect.poll(() => server.testRequests, {message: 'the test email reached the server'}).toEqual(['POST']);
            await expect(tab).toHaveAttribute('data-busy', 'true');
            await expect(button, 'one test email at a time').toBeDisabled();
            server.release();

            await expect(page.getByTestId('email-test-outcome')).toHaveAttribute('data-outcome', 'sent');
            const sent = await waitForEvent(page, 'email.test.sent', {since});
            expect(sent.detail, 'the event says in which language the email went').toEqual({language: 'en'});
            await expect(budget, 'the status is read again after the attempt: one email fewer').toHaveAttribute('data-remaining', '47');
            await waitForSettled(tab);
            await expect(button).toBeEnabled();
            expect(server.statusReads(), 'the status was read on opening, and once after the test email').toBe(2);
        } finally {
            await server.unroute();
        }
    });

    test('a 502 EMAIL_DELIVERY_FAILED (AUTH_FAILED): the outcome is failed, the failure recorded, the status read again', async ({page}) => {
        const server = await simulateEmailServer(page, {
            before: readyStatus(48),
            after: readyStatus(47),
            answer: {status: 502, body: {detail: {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 'AUTH_FAILED', message: 'The SMTP server did not take the message'}}},
        });
        try {
            const tab = await openEmailTab(page);
            const since = await eventSeq(page);
            await page.getByTestId('email-test-button').click();

            await expect(page.getByTestId('email-test-outcome')).toHaveAttribute('data-outcome', 'failed');
            const failed = await waitForEvent(page, 'email.test.failed', {since});
            expect(failed.detail, 'read from the refusal as the generated client raises it').toEqual({errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode: 'AUTH_FAILED'});
            await expect(page.getByTestId('email-budget'), 'the status is read again after the attempt').toHaveAttribute('data-remaining', '47');
            await waitForSettled(tab);
            expect(server.testRequests, 'one test email asked for').toEqual(['POST']);
            expect(server.statusReads(), 'the status was read on opening, and once after the test email').toBe(2);
        } finally {
            await server.unroute();
        }
    });

    test('a 429 EMAIL_RATE_LIMITED: the outcome is failed, the wait recorded, and the status read again shows the limit reached', async ({page}) => {
        const server = await simulateEmailServer(page, {
            before: readyStatus(48),
            after: readyStatus(0, 1800),
            answer: {status: 429, headers: {'Retry-After': '1800'}, body: {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 1800, message: 'The hourly email limit of the instance is reached'}}},
        });
        try {
            const tab = await openEmailTab(page);
            const since = await eventSeq(page);
            await page.getByTestId('email-test-button').click();

            await expect(page.getByTestId('email-test-outcome')).toHaveAttribute('data-outcome', 'failed');
            const failed = await waitForEvent(page, 'email.test.failed', {since});
            expect(failed.detail, 'read from the refusal as the generated client raises it, the wait included').toEqual({errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 1800});
            await expect(page.getByTestId('email-budget'), 'the status read again: the hourly limit is reached').toHaveAttribute('data-remaining', '0');
            await waitForSettled(tab);
            await expect(page.getByTestId('email-test-button'), 'still offered: the budget is per server process, and a refusal says so').toBeEnabled();
            expect(server.testRequests, 'one test email asked for').toEqual(['POST']);
            expect(server.statusReads(), 'the status was read on opening, and once after the test email').toBe(2);
        } finally {
            await server.unroute();
        }
    });
});
