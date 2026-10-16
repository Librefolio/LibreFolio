/**
 * «Forgot password» by email E2E (workstream E, lot E4b): on the sign-in page, «Forgot password?» opens A's card, which
 * hosts E's form while emails with a link can go out.
 *
 * Signed out, on the lane's real frontend and backend, with two reads of the page simulated (`page.route`, owned by each
 * test and removed by it):
 *   - `GET /api/v1/system/instance`: the real answer with `email` replaced (`fixtures/instance-email.ts`);
 *   - `POST /api/v1/email/password-reset`: a simulated server recording each body and answering 202 (checked against the
 *     generated `PasswordResetEmailAccepted`) or 429 EMAIL_RATE_LIMITED. The real route is never reached — the lane has
 *     no SMTP server —: nothing is sent, nothing is counted.
 * Covered:
 *   FPE-E-01  links ready: the card shows the form in the warning's place (`forgot-email-unavailable` gone), the command
 *             box still there, in a panel closed by default (`forgot-commands-panel`, the developer's decision P1, 16/10)
 *             that a click on its summary (`forgot-commands-toggle`) opens; a fixture user's username and a name no
 *             account has, each typed between spaces, get the same accepted notice and `email.forgot.accepted`; each
 *             identifier went once, trimmed;
 *   FPE-E-02  links ready, the simulated server says 429 with `retry_after` 840: «failed», `email.forgot.refused` with the
 *             wait; the field keeps what was typed, and the form may ask again;
 *   FPE-E-03  email available but links not: the warning (`forgot-email-unavailable`) in the form's place, the command box
 *             and «back to login» there — the card drawn, so the absence is of the form alone —, and nothing asked of the
 *             simulated server.
 * Nothing is written: the page never signs in, and the only write it could make is simulated. Parallel by default.
 * Assertions read test ids, `data-*`, the request bodies and the events, never a translated text.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `forgot-password-email` of front-utility.
 */
import type {Route} from '@playwright/test';
import {schemas} from '../src/lib/api/generated';
import {expect, test, type Page} from './fixtures/playwright';
import {eventSeq, waitForEvent} from './fixtures/app-events';
import {serveInstanceEmail, type InstanceEmailStub} from './fixtures/instance-email';
import {TEST_USER} from './fixtures/test-users';
import {uniqueSuffix} from './fixtures/unique';

const RESET_PATH = '/api/v1/email/password-reset';
const isReset = (url: URL): boolean => url.pathname === RESET_PATH;

// Budgets: deadlines, never delays.
/** The first paint of `/`: `login-page` renders once the root page's GET /auth/me has answered. */
const FIRST_PAINT_MS = 30_000;
/** The form appears once the instance configuration is in. */
const CONFIG_MS = 15_000;
/** A request's round trip to the simulated server. */
const ACTION_MS = 15_000;
/** The reaction to a click on something already on screen. */
const UI_MS = 5_000;

/** How the simulated `POST /api/v1/email/password-reset` answers. */
interface ForgotAnswer {
    status: number;
    body: unknown;
    headers?: Record<string, string>;
}

/** The 202, the same for everyone: checked against the generated schema, as the client checks it on arrival. */
const ACCEPTED: ForgotAnswer = {
    status: 202,
    body: schemas.PasswordResetEmailAccepted.parse({message: 'If an active account matches, its owner gets an email with a link to choose a new password'}),
};

interface ForgotServer {
    /** Every request the path received, its method and JSON body: answered when `POST`, fallen back otherwise. */
    requests: Array<{method: string; body: unknown}>;
    unroute: () => Promise<void>;
}

/** Answer `POST /api/v1/email/password-reset` from a simulated server — that path and that method only — with `answer`. */
async function simulateForgotServer(page: Page, answer: ForgotAnswer): Promise<ForgotServer> {
    const requests: ForgotServer['requests'] = [];
    const handler = async (route: Route) => {
        const request = route.request();
        const post = request.method() === 'POST';
        requests.push({method: request.method(), body: post ? request.postDataJSON() : null});
        if (!post) return route.fallback();
        await route.fulfill({status: answer.status, headers: answer.headers, json: answer.body});
    };
    await page.route(isReset, handler);
    return {requests, unroute: () => page.unroute(isReset, handler)};
}

/** The instance read as asked, at least once, by this page. */
function expectServed(instance: InstanceEmailStub, links: boolean): void {
    expect(instance.problems, 'the simulated GET /system/instance answered as asked').toEqual([]);
    expect(instance.served.length, 'the page read the instance configuration through the stub').toBeGreaterThan(0);
    const asAsked = instance.served.every((email) => email.links === links);
    expect(asAsked, `every read said email.links ${links}`).toBe(true);
}

/** Open `/` signed out and «Forgot password?»; ends on the card drawn. */
async function openForgotCard(page: Page): Promise<void> {
    await page.goto('/');
    await expect(page.getByTestId('login-page')).toBeVisible({timeout: FIRST_PAINT_MS});
    await page.getByTestId('goto-forgot').click();
    await expect(page.getByTestId('forgot-modal')).toBeVisible({timeout: UI_MS});
}

test.setTimeout(90_000);

test.describe('«Forgot password» by email — links ready', () => {
    test('FPE-E-01: the form in the warning’s place, the commands in a panel a click opens; a username and a name no account has get the same accepted notice, each sent once, trimmed', async ({page}) => {
        const nobody = `zq_nobody_${uniqueSuffix()}`;
        const instance = await serveInstanceEmail(page, {available: true, links: true});
        const server = await simulateForgotServer(page, ACCEPTED);
        try {
            await openForgotCard(page);
            const form = page.getByTestId('forgot-email-form');
            await expect(form, 'the form, once the instance says links can go').toBeVisible({timeout: CONFIG_MS});
            expectServed(instance, true);
            await expect(page.getByTestId('forgot-email-unavailable'), 'the form takes the warning’s place').toHaveCount(0);
            // The commands stay, for whoever runs the server, in a panel closed by default (the developer's decision P1,
            // 16/10): its summary on view, the box in the panel but hidden; a click on the summary shows it.
            const panel = page.getByTestId('forgot-commands-panel');
            const toggle = panel.getByTestId('forgot-commands-toggle');
            const commands = panel.getByTestId('forgot-reset-commands');
            await expect(toggle, 'the panel’s summary, on view').toBeVisible();
            await expect(panel, 'closed by default').not.toHaveAttribute('open');
            await expect(commands, 'the commands, in the panel').toHaveCount(1);
            await expect(commands, 'hidden while the panel is closed').toBeHidden();
            await toggle.click();
            await expect(panel).toHaveAttribute('open', '', {timeout: UI_MS});
            await expect(commands, 'a click on the summary shows them').toBeVisible({timeout: UI_MS});
            const field = form.getByTestId('forgot-email-identifier');
            const outcome = form.getByTestId('forgot-email-outcome');

            const notices: string[] = [];
            for (const identifier of [TEST_USER.username, nobody]) {
                await field.fill(`  ${identifier}  `);
                await expect(field).toHaveValue(`  ${identifier}  `);
                const since = await eventSeq(page);
                await form.getByTestId('forgot-email-submit').click();

                await waitForEvent(page, 'email.forgot.accepted', {since, timeout: ACTION_MS});
                await expect(outcome).toHaveAttribute('data-outcome', 'accepted');
                await expect(form).toHaveAttribute('data-busy', 'false');
                notices.push((await outcome.textContent()) ?? '');
            }

            expect(notices[1], 'one notice for everyone: nothing tells the accounts apart').toBe(notices[0]);
            expect(server.requests, 'each identifier once, trimmed').toEqual([
                {method: 'POST', body: {identifier: TEST_USER.username}},
                {method: 'POST', body: {identifier: nobody}},
            ]);
        } finally {
            await server.unroute();
            await instance.dispose();
        }
    });

    test('FPE-E-02: a 429 EMAIL_RATE_LIMITED — «failed», the wait in the event; the field keeps what was typed and the form may ask again', async ({page}) => {
        const instance = await serveInstanceEmail(page, {available: true, links: true});
        const server = await simulateForgotServer(page, {
            status: 429,
            headers: {'Retry-After': '840'},
            body: {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 840, message: 'Too many requests: try again later'}},
        });
        try {
            await openForgotCard(page);
            const form = page.getByTestId('forgot-email-form');
            await expect(form).toBeVisible({timeout: CONFIG_MS});
            const field = form.getByTestId('forgot-email-identifier');
            await field.fill(TEST_USER.username);
            await expect(field).toHaveValue(TEST_USER.username);

            const since = await eventSeq(page);
            await form.getByTestId('forgot-email-submit').click();

            const refused = await waitForEvent(page, 'email.forgot.refused', {since, timeout: ACTION_MS});
            expect(refused.detail, 'read from the refusal as the generated client raises it, the wait included').toEqual({errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 840});
            await expect(form.getByTestId('forgot-email-outcome')).toHaveAttribute('data-outcome', 'failed');
            await expect(form).toHaveAttribute('data-busy', 'false');
            await expect(field).toHaveValue(TEST_USER.username);
            await expect(form.getByTestId('forgot-email-submit')).toBeEnabled();
            const methods = server.requests.map(({method}) => method);
            expect(methods, 'one request').toEqual(['POST']);
        } finally {
            await server.unroute();
            await instance.dispose();
        }
    });
});

test.describe('«Forgot password» by email — links not ready', () => {
    test('FPE-E-03: email available but no links — the warning in the form’s place; the commands and «back to login» there; nothing asked', async ({page}) => {
        const instance = await serveInstanceEmail(page, {available: true, links: false});
        const server = await simulateForgotServer(page, ACCEPTED);
        try {
            await openForgotCard(page);
            // The configuration read first — the page asks on load, the card shares that request —: «no form» means
            // something only once it has answered.
            await expect.poll(() => instance.answered, {timeout: CONFIG_MS}).toBeGreaterThan(0);
            expectServed(instance, false);
            // Presence, then the absence: the warning stands where the form would and the card is drawn around it, so
            // what is missing is the form alone.
            await expect(page.getByTestId('forgot-email-unavailable'), 'the warning: no reset link by email on this instance').toBeVisible();
            await expect(page.getByTestId('forgot-reset-commands')).toBeVisible();
            await expect(page.getByTestId('forgot-back-to-login')).toBeVisible();
            await expect(page.getByTestId('forgot-email-form')).toHaveCount(0);
            expect(server.requests, 'nothing asked of the server').toEqual([]);
        } finally {
            await server.unroute();
            await instance.dispose();
        }
    });
});
