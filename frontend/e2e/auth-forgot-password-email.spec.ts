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
 *   FPE-E-01  links ready: the card shows the form in the warning's place (`forgot-email-unavailable` gone) and no server
 *             command at all — no `forgot-commands-panel`, no `forgot-reset-commands` (developer's decision, 09/11/2026,
 *             lot UA1: the administrator's guide keeps them); a fixture user's username, typed between spaces, gets the
 *             accepted notice and `email.forgot.accepted`, then the submit waits (disabled, `forgot-email-countdown` with
 *             `data-seconds` in (0, 300]); a reload, the card opened again, still waits — the deadline is kept in
 *             `sessionStorage`; with that cleared (the five minutes are never waited out here) and the page reloaded, a
 *             name no account has, typed between spaces, gets the same notice; each identifier went once, trimmed;
 *   FPE-E-02  links ready, the simulated server says 429 with `retry_after` 840: «failed», `email.forgot.refused` with the
 *             wait; the field keeps what was typed, and the form may ask again at once — a refusal starts no countdown;
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
import {FORGOT_COOLDOWN_KEY, FORGOT_RESEND_WAIT_S} from '../src/lib/features/email/forgotCooldown';

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

/** «Forgot password?» on the sign-in page already loading; ends on the card drawn. */
async function clickForgot(page: Page): Promise<void> {
    await expect(page.getByTestId('login-page')).toBeVisible({timeout: FIRST_PAINT_MS});
    await page.getByTestId('goto-forgot').click();
    await expect(page.getByTestId('forgot-modal')).toBeVisible({timeout: UI_MS});
}

/** Open `/` signed out and «Forgot password?»; ends on the card drawn. */
async function openForgotCard(page: Page): Promise<void> {
    await page.goto('/');
    await clickForgot(page);
}

/** Reload the page and open «Forgot password?» again; ends on the email form on view. */
async function reloadToForm(page: Page): Promise<void> {
    await page.reload();
    await clickForgot(page);
    await expect(page.getByTestId('forgot-email-form')).toBeVisible({timeout: CONFIG_MS});
}

/** The submit waits: disabled, its countdown on view with whole seconds in (0, FORGOT_RESEND_WAIT_S]. */
async function expectWaiting(page: Page, why: string): Promise<void> {
    const submit = page.getByTestId('forgot-email-submit');
    const countdown = submit.getByTestId('forgot-email-countdown');
    await expect(countdown, why).toBeVisible({timeout: UI_MS});
    await expect(submit, why).toBeDisabled();
    const seconds = Number(await countdown.getAttribute('data-seconds'));
    expect(Number.isInteger(seconds) && seconds > 0 && seconds <= FORGOT_RESEND_WAIT_S, `data-seconds ${seconds} in (0, ${FORGOT_RESEND_WAIT_S}]`).toBe(true);
}

test.setTimeout(90_000);

test.describe('«Forgot password» by email — links ready', () => {
    test('FPE-E-01: the form in the warning’s place, no server command; an accepted request starts a wait a reload keeps; a username and a name no account has get the same accepted notice, each sent once, trimmed', async ({page}) => {
        const nobody = `zq_nobody_${uniqueSuffix()}`;
        const instance = await serveInstanceEmail(page, {available: true, links: true});
        const server = await simulateForgotServer(page, ACCEPTED);
        try {
            await openForgotCard(page);
            const form = page.getByTestId('forgot-email-form');
            await expect(form, 'the form, once the instance says links can go').toBeVisible({timeout: CONFIG_MS});
            expectServed(instance, true);
            // Presence first — the form and «back to login» on view —, then the absences: the card is drawn, and what is
            // missing is the warning and every server command (developer's decision, 09/11/2026, lot UA1).
            await expect(page.getByTestId('forgot-back-to-login')).toBeVisible();
            await expect(page.getByTestId('forgot-email-unavailable'), 'the form takes the warning’s place').toHaveCount(0);
            await expect(page.getByTestId('forgot-commands-panel'), 'no panel of server commands').toHaveCount(0);
            await expect(page.getByTestId('forgot-reset-commands'), 'no server command').toHaveCount(0);
            const field = form.getByTestId('forgot-email-identifier');
            const outcome = form.getByTestId('forgot-email-outcome');
            const submit = form.getByTestId('forgot-email-submit');

            /** Type `identifier` between spaces and send it; ends on the accepted notice, its text returned. */
            const askFor = async (identifier: string): Promise<string> => {
                await field.fill(`  ${identifier}  `);
                await expect(field).toHaveValue(`  ${identifier}  `);
                await expect(submit, 'no wait before this request').toBeEnabled();
                const since = await eventSeq(page);
                await submit.click();
                await waitForEvent(page, 'email.forgot.accepted', {since, timeout: ACTION_MS});
                await expect(outcome).toHaveAttribute('data-outcome', 'accepted');
                await expect(form).toHaveAttribute('data-busy', 'false');
                return (await outcome.textContent()) ?? '';
            };

            const notices: string[] = [await askFor(TEST_USER.username)];
            await expectWaiting(page, 'accepted: the submit waits the server’s interval');

            // A reload keeps the wait: the deadline is in sessionStorage. The field typed again, so the wait alone disables.
            await reloadToForm(page);
            await field.fill(nobody);
            await expect(field).toHaveValue(nobody);
            await expectWaiting(page, 'after a reload, still waiting');

            // The five minutes are not waited out here: the deadline cleared, as if they had passed, and the page reloaded.
            await page.evaluate((key) => sessionStorage.removeItem(key), FORGOT_COOLDOWN_KEY);
            await reloadToForm(page);
            notices.push(await askFor(nobody));
            await expectWaiting(page, 'the second accepted request waits too');

            expect(notices[1], 'one notice for everyone: nothing tells the accounts apart').toBe(notices[0]);
            expectServed(instance, true);
            expect(server.requests, 'each identifier once, trimmed; nothing sent while waiting').toEqual([
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
            await expect(form.getByTestId('forgot-email-submit'), 'a refusal starts no wait').toBeEnabled();
            await expect(form.getByTestId('forgot-email-countdown')).toHaveCount(0);
            expect(await page.evaluate((key) => sessionStorage.getItem(key), FORGOT_COOLDOWN_KEY), 'no deadline stored').toBeNull();
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
