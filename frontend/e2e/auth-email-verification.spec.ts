/**
 * Email verification E2E (workstream E, lot E5b; developer decision 44): what an account that waits for its link meets
 * on the sign-in page, and the administrators' switch that turns the option on.
 *
 * EVE-E-01…03 run signed out on simulated answers (`page.route`, owned by each test and removed by it): nothing reaches a
 * write path of the shared backend, nothing is created.
 *   - `GET /api/v1/system/instance`: the real answer with `accounts.registration_mode` set to `open` (workstream A's
 *     `serveRegistrationMode`), so the register link shows whatever mode the lane runs;
 *   - `POST /api/v1/auth/register`, `/api/v1/auth/login` and `/api/v1/email/verification/resend`: simulated servers that
 *     record every request and answer as E5b's backend does — a success checked against its generated schema, as the
 *     client checks it on arrival; a refusal a plain `detail` error.
 * EVE-E-04/05 sign the lane's real `e2e_test_admin` in and simulate only `GET /api/v1/system/instance`
 * (`serveInstanceEmail`: the real answer with `email` replaced). They open Settings › Admin and unlock it; nothing is
 * toggled, nothing is saved: the lane's database is shared.
 *
 * Covered:
 *   EVE-E-01  sign-up, the simulated 201 saying `verification_required: true` with an inactive user: back to the sign-in
 *             with its success line (`login-success`), nobody signed in — no `POST /auth/login`, still on `/`. The line
 *             differs from the one a 201 without verification brings back on the same page: the card tells the two
 *             apart. Which key each one is, `RegisterCard.verification.test.ts` (RCV) pins: the line has no handle here.
 *   EVE-E-02  sign-up refused with 409 EMAIL_VERIFICATION_UNAVAILABLE: the register card stays, its error banner shown
 *             (`info-banner-error`), nobody signed in; its words differ from those of a refusal the client does not name
 *             (the generic failure). The key itself: `registrationErrors.verification.test.ts` (RVR).
 *   EVE-E-03  sign-in of a waiting account, the simulated 403 EMAIL_NOT_VERIFIED: the verification notice
 *             (`email-verification-notice`) instead of the danger box (`login-error`); «send the link again» posts the
 *             credentials just typed, and the simulated 200 `{language}` is confirmed (`data-outcome="sent"`) and
 *             recorded as `email.verification.resent`.
 *   EVE-E-04  Settings › Admin unlocked, `email.links` false (email available, no public URL): the «require email
 *             verification» switch is disabled — not a placeholder, and the sibling `scheduler_enabled` switch usable,
 *             so what turns it off is the email gate. Its `settingNeedsEmail` hint has no handle: the Vitest of the tab
 *             (GVR, `GlobalSettingsTab.verification.test.ts`) asserts it.
 *   EVE-E-05  the same with `email.links` true: the switch is usable.
 * EVE-E-04/05 read their precondition first, through the administrator's session: the option is saved off on the lane
 * (no spec turns it on). Saved on, the switch would be usable either way: the saved value decides, not the edited one.
 *
 * Assertions read test ids, `data-*`, request bodies and events, never a translated text: where two lines of text are
 * compared, it is with each other, on the same page, in whatever language the page runs. Parallel by default: no test
 * shares state with another.
 *
 * Prerequisites: test users created (`e2e_test_admin` an administrator); no SMTP server on the lane;
 * `require_email_verification` saved off. Registered in scripts/test_runner/_frontend_utility.py, action
 * `email-verification` of front-utility.
 */
import type {Route} from '@playwright/test';
import {schemas} from '../src/lib/api/generated';
import {expect, test, type Locator, type Page} from './fixtures/playwright';
import {eventSeq, waitForEvent, waitForSettled} from './fixtures/app-events';
import {login, navigateTo} from './fixtures/auth-helpers';
import {serveRegistrationMode} from './fixtures/instance-config';
import {serveInstanceEmail, type InstanceEmail, type InstanceEmailStub} from './fixtures/instance-email';
import {TEST_ADMIN} from './fixtures/test-users';
import {uniqueSuffix} from './fixtures/unique';

const API = '/api/v1';
const REGISTER_PATH = `${API}/auth/register`;
const LOGIN_PATH = `${API}/auth/login`;
const RESEND_PATH = `${API}/email/verification/resend`;
const SETTINGS_PATH = `${API}/settings/global`;
/** The option, and the other boolean of Settings › Admin: the same row and switch, without the email gate. */
const OPTION_KEY = 'require_email_verification';
const SIBLING_KEY = 'scheduler_enabled';

// Budgets: deadlines, never delays.
/** The first paint of `/`: `login-page` renders once the root page's GET /auth/me has answered. */
const FIRST_PAINT_MS = 30_000;
/** From a navigation to a settled tab: the SPA's load, the auth check, then GET /settings/global. */
const LOAD_MS = 20_000;
/** A request's round trip to a simulated server, and what the page draws of its answer. */
const ACTION_MS = 15_000;
/** The reaction to a click on something already on screen. */
const UI_MS = 5_000;

/** Passes every rule of the register form: eight characters or more, upper and lower case, a digit, a special one. */
const PASSWORD = 'Zq-Verify-2026!';

/** How a simulated route answers one request. */
interface Answer {
    status: number;
    body: unknown;
}

interface Recorded {
    /** Every request the path received, its method and JSON body. */
    requests: Array<{method: string; body: unknown}>;
    unroute: () => Promise<void>;
}

/**
 * Answer `POST <path>` — that path and that method only — with `answer(body, index)`, `index` counting the POSTs from 0;
 * anything else falls back. Without `answer` every request falls back: the route only records.
 */
async function simulate(page: Page, path: string, answer?: (body: unknown, index: number) => Answer): Promise<Recorded> {
    const requests: Recorded['requests'] = [];
    let posts = 0;
    const matches = (url: URL): boolean => url.pathname === path;
    const handler = async (route: Route) => {
        const request = route.request();
        const post = request.method() === 'POST';
        const body: unknown = post ? request.postDataJSON() : null;
        requests.push({method: request.method(), body});
        if (!post || answer === undefined) return route.fallback();
        const answered = answer(body, posts);
        posts += 1;
        await route.fulfill({status: answered.status, json: answered.body});
    };
    await page.route(matches, handler);
    return {requests, unroute: () => page.unroute(matches, handler)};
}

/** The 201 of `POST /auth/register` as E5b answers it: the new account, inactive while it waits for its link. */
function registered(body: unknown, verificationRequired: boolean): Answer {
    const {username, email} = body as {username: string; email: string};
    const user = {id: 990_001, username, email, is_active: !verificationRequired, is_superuser: false, created_at: '2026-10-16T00:00:00Z'};
    return {status: 201, body: schemas.AuthRegisterResponse.parse({user, message: 'Registration successful', verification_required: verificationRequired})};
}

/** The refusal of E5b when the option is on and no email with a link can go out. */
const SIGN_UP_UNAVAILABLE: Answer = {status: 409, body: {detail: {error_code: 'EMAIL_VERIFICATION_UNAVAILABLE', message: 'Sign-up needs an email with a link, and none can go out now'}}};
/** A refusal whose code the client does not name: what the register card says of any other failure. */
const UNNAMED_REFUSAL: Answer = {status: 409, body: {detail: {error_code: 'ZQ_NOT_A_KNOWN_CODE', message: 'Refused'}}};
/** The sign-in of an account that waits for its link, with its right password. */
const NOT_VERIFIED: Answer = {status: 403, body: {detail: {error_code: 'EMAIL_NOT_VERIFIED', message: 'Open the link of the email we sent to verify the address'}}};

/** What the register form sends for `username`. */
function registration(username: string): {username: string; email: string; password: string} {
    return {username, email: `${username}@example.com`, password: PASSWORD};
}

/** Open `/` signed out; ends on the sign-in drawn. */
async function openSignIn(page: Page): Promise<void> {
    await page.goto('/');
    await expect(page.getByTestId('login-page')).toBeVisible({timeout: FIRST_PAINT_MS});
    await expect(page.getByTestId('login-modal')).toBeVisible({timeout: UI_MS});
}

/** From the sign-in, «register here»; ends on the register card drawn. */
async function openRegisterCard(page: Page): Promise<Locator> {
    await page.getByTestId('goto-register').click();
    const card = page.getByTestId('register-modal');
    await expect(card).toBeVisible({timeout: UI_MS});
    return card;
}

/** Type the registration of `username` — its address on example.com, the password twice — each field read back. */
async function fillRegistration(card: Locator, username: string): Promise<void> {
    const values: Array<[string, string]> = [
        ['register-username', username],
        ['register-email', `${username}@example.com`],
        ['register-password', PASSWORD],
        ['register-confirm-password', PASSWORD],
    ];
    for (const [testId, value] of values) {
        const field = card.getByTestId(testId);
        await field.fill(value);
        await expect(field).toHaveValue(value);
    }
}

/** The text a locator shows now, trimmed: read only after a retrying assertion has proved it is the one meant. */
async function wordsOf(locator: Locator): Promise<string> {
    return ((await locator.textContent()) ?? '').trim();
}

/** The option is saved off on the lane (no spec turns it on): the precondition of the gate, read through the session. */
async function expectOptionSavedOff(page: Page): Promise<void> {
    const response = await page.request.get(SETTINGS_PATH);
    expect(response.status(), `GET ${SETTINGS_PATH}: ${await response.text()}`).toBe(200);
    const items = ((await response.json()) as {items?: Array<{key: string; value: string}>}).items ?? [];
    const saved = items.find((item) => item.key === OPTION_KEY)?.value;
    expect(saved, `precondition: ${OPTION_KEY} saved off on the lane; saved on, the switch is usable whatever email.links says`).toBe('false');
}

/** The instance configuration read through the stub at least once, every answer with the email part asked for. */
async function expectServed(instance: InstanceEmailStub, email: InstanceEmail): Promise<void> {
    await expect.poll(() => instance.answered, {timeout: LOAD_MS}).toBeGreaterThan(0);
    expect(instance.problems, 'the simulated GET /system/instance answered as asked').toEqual([]);
    const asAsked = instance.served.every((served) => served.available === email.available && served.links === email.links);
    expect(asAsked, `every read said email ${JSON.stringify(email)}`).toBe(true);
}

/**
 * Sign the administrator in, check the precondition, open Settings › Admin and unlock it. The tab mounts locked, every
 * switch off: asserted first, then one click, then the end state — the sibling switch usable. Ends on the option's row,
 * nothing toggled, nothing saved.
 */
async function openAdminUnlocked(page: Page): Promise<Locator> {
    await login(page, TEST_ADMIN);
    await expectOptionSavedOff(page);
    await navigateTo(page, '/settings?tab=admin');
    await expect(page.getByTestId('settings-tab-admin'), '?tab=admin opens Settings › Admin').toHaveAttribute('aria-selected', 'true', {timeout: LOAD_MS});
    const tab = page.getByTestId('global-settings-tab');
    await waitForSettled(tab, LOAD_MS);
    const option = tab.getByTestId(`global-setting-${OPTION_KEY}`);
    const sibling = tab.getByTestId(`global-setting-${SIBLING_KEY}`).getByTestId('setting-toggle-switch');
    await expect(option, 'the option has its row').toBeVisible();
    await expect(sibling, 'the tab mounts locked: every switch is off').toBeDisabled();
    await tab.getByTestId('settings-lock-toggle').click();
    await expect(sibling, 'unlocked: an ordinary switch is usable').toBeEnabled({timeout: UI_MS});
    return option;
}

// EVE-E-04/05 sign in through the form (login() alone may take 70 s on a loaded lane: auth.spec.ts): a budget below the
// waits a test contains would end a slow red on the test timeout, which names nothing, instead of on its own assertion.
test.setTimeout(120_000);

test.describe('Email verification — sign-up and sign-in, on simulated answers', () => {
    test('EVE-E-01: a sign-up that waits for its link goes back to the sign-in with a success line of its own, and signs nobody in', async ({page}) => {
        const suffix = uniqueSuffix();
        const waiting = `zq_wait_${suffix}`;
        const plain = `zq_plain_${suffix}`;
        const mode = await serveRegistrationMode(page, 'open');
        const register = await simulate(page, REGISTER_PATH, (body) => registered(body, (body as {username?: unknown}).username === waiting));
        const signIn = await simulate(page, LOGIN_PATH);
        try {
            await openSignIn(page);
            const success = page.getByTestId('login-success');

            const first = await openRegisterCard(page);
            await fillRegistration(first, waiting);
            await first.getByTestId('register-submit').click();
            await expect(page.getByTestId('login-modal'), 'back to the sign-in once registered').toBeVisible({timeout: ACTION_MS});
            await expect(success).toBeVisible();
            const waitingLine = await wordsOf(success);

            // The control, on the same page: a 201 that needs no verification brings the usual line back.
            const second = await openRegisterCard(page);
            await fillRegistration(second, plain);
            await second.getByTestId('register-submit').click();
            await expect(page.getByTestId('login-modal'), 'back to the sign-in once registered').toBeVisible({timeout: ACTION_MS});
            await expect(success).toBeVisible();
            const plainLine = await wordsOf(success);

            expect(register.requests, 'two registrations, each with what was typed').toEqual([
                {method: 'POST', body: registration(waiting)},
                {method: 'POST', body: registration(plain)},
            ]);
            expect(waitingLine, 'the line says something').not.toBe('');
            expect(waitingLine, 'an account that waits for its link is told so, not the usual «account created»').not.toBe(plainLine);
            expect(signIn.requests, 'a registration signs nobody in').toEqual([]);
            expect(new URL(page.url()).pathname, 'still on the sign-in page').toBe('/');
            expect(mode.problems, 'the simulated GET /system/instance answered as asked').toEqual([]);
        } finally {
            await signIn.unroute();
            await register.unroute();
            await mode.dispose();
        }
    });

    test('EVE-E-02: a sign-up refused with 409 EMAIL_VERIFICATION_UNAVAILABLE stays on the card with words of its own, and signs nobody in', async ({page}) => {
        const username = `zq_refused_${uniqueSuffix()}`;
        const mode = await serveRegistrationMode(page, 'open');
        const register = await simulate(page, REGISTER_PATH, (_body, index) => (index === 0 ? SIGN_UP_UNAVAILABLE : UNNAMED_REFUSAL));
        const signIn = await simulate(page, LOGIN_PATH);
        try {
            await openSignIn(page);
            const card = await openRegisterCard(page);
            await fillRegistration(card, username);
            const submit = card.getByTestId('register-submit');
            const banner = card.getByTestId('info-banner-error');

            await submit.click();
            await expect(banner, 'the refusal is told in the card').toBeVisible({timeout: ACTION_MS});
            const unavailableWords = await wordsOf(banner);

            // The control, on the same card: a refusal the client does not name gets the generic failure. The banner
            // clears while the request runs and the button turns off: once both answers are in, the button is back on.
            await submit.click();
            await expect.poll(() => register.requests.length, {timeout: ACTION_MS}).toBe(2);
            await expect(submit, 'the second answer is in').toBeEnabled({timeout: ACTION_MS});
            await expect(banner).toBeVisible();
            const genericWords = await wordsOf(banner);

            await expect(card, 'still on the register card').toBeVisible();
            await expect(page.getByTestId('login-modal')).toHaveCount(0);
            expect(register.requests, 'the same registration, twice').toEqual([
                {method: 'POST', body: registration(username)},
                {method: 'POST', body: registration(username)},
            ]);
            expect(unavailableWords, 'the refusal says something').not.toBe('');
            expect(unavailableWords, 'EMAIL_VERIFICATION_UNAVAILABLE has words of its own, not the generic failure').not.toBe(genericWords);
            expect(signIn.requests, 'a refused registration signs nobody in').toEqual([]);
            expect(mode.problems, 'the simulated GET /system/instance answered as asked').toEqual([]);
        } finally {
            await signIn.unroute();
            await register.unroute();
            await mode.dispose();
        }
    });

    test('EVE-E-03: the sign-in of a waiting account draws the verification notice, not the danger box; «send the link again» goes with the credentials just typed', async ({page}) => {
        const username = `zq_waiting_${uniqueSuffix()}`;
        const signIn = await simulate(page, LOGIN_PATH, () => NOT_VERIFIED);
        const resend = await simulate(page, RESEND_PATH, () => ({status: 200, body: schemas.EmailVerificationResendResponse.parse({language: 'en'})}));
        try {
            await openSignIn(page);
            const card = page.getByTestId('login-modal');
            const name = card.getByTestId('login-username');
            await name.fill(username);
            await expect(name).toHaveValue(username);
            const secret = card.getByTestId('login-password');
            await secret.fill(PASSWORD);
            await expect(secret).toHaveValue(PASSWORD);
            await card.getByTestId('login-submit').click();

            const notice = card.getByTestId('email-verification-notice');
            await expect(notice, 'a waiting account is asked to open its link, with a way to get a new one').toBeVisible({timeout: ACTION_MS});
            await expect(card.getByTestId('login-error'), 'the notice stands where the danger box would').toHaveCount(0);
            const button = notice.getByTestId('email-verification-resend');
            await expect(button, 'the credentials are there: «send the link again» is usable').toBeEnabled();

            const since = await eventSeq(page);
            await button.click();

            const resent = await waitForEvent(page, 'email.verification.resent', {since, timeout: ACTION_MS});
            expect(resent.detail, 'the language the email went in, as the server answered it').toEqual({language: 'en'});
            await expect(notice.getByTestId('email-verification-outcome')).toHaveAttribute('data-outcome', 'sent');
            await waitForSettled(notice);
            expect(signIn.requests, 'one sign-in, refused').toEqual([{method: 'POST', body: {username, password: PASSWORD}}]);
            expect(resend.requests, 'one resend, with the credentials just typed').toEqual([{method: 'POST', body: {username, password: PASSWORD}}]);
            expect(new URL(page.url()).pathname, 'nobody signed in: still on the sign-in page').toBe('/');
        } finally {
            await resend.unroute();
            await signIn.unroute();
        }
    });
});

test.describe('Email verification — the switch in Settings › Admin', () => {
    test('EVE-E-04: email.links false — the «require email verification» switch is disabled, by the email gate alone', async ({page}) => {
        const email: InstanceEmail = {available: true, links: false};
        const instance = await serveInstanceEmail(page, email);
        try {
            const option = await openAdminUnlocked(page);
            await expectServed(instance, email);
            await expect(option.getByTestId('setting-badge'), 'not a placeholder: no «coming soon» badge').toHaveCount(0);
            await expect(option.getByTestId('setting-toggle-switch'), 'saved off, and no email with a link: it cannot go on').toBeDisabled();
        } finally {
            await instance.dispose();
        }
    });

    test('EVE-E-05: email.links true — the switch is usable', async ({page}) => {
        const email: InstanceEmail = {available: true, links: true};
        const instance = await serveInstanceEmail(page, email);
        try {
            const option = await openAdminUnlocked(page);
            await expectServed(instance, email);
            await expect(option.getByTestId('setting-toggle-switch'), 'an email with a link can go: it may be turned on').toBeEnabled({timeout: UI_MS});
        } finally {
            await instance.dispose();
        }
    });
});
