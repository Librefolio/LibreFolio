/**
 * Gallery, Settings › Administration › Email (`settings/email`): the administrators' Email tab on an instance whose email works.
 *
 * The gallery's lane runs without an SMTP server, so its own `GET /api/v1/email/status` answers `off`. The shot shows
 * the tab as an administrator sees it where email is set up: ready, 47 of 50 emails left this hour, every configuration
 * check `ok` — so no notice — and the test email offered. It is never pressed: nothing is sent, nothing is written.
 *
 * {@link serveGalleryEmailStatus} answers that read and nothing else: `GET` on the status path. Any other method falls
 * back to the routes registered before it (the gallery's offline guard), then to the backend; nothing is continued by
 * hand. The body is the shape the backend sends (`backend/app/schemas/email.py`, `EmailStatusResponse`), typed with the
 * generated client's type and checked against its Zod schema once, at registration: a contract that moved fails the
 * test there, with Zod's own message, rather than as a page that keeps its loading state. Its data are fixed — no
 * clock, no random value, no external URL — and the budget has emails left, whose sentence names no time (a spent
 * budget would name the minutes until the next email).
 *
 * Registered before the first navigation, the route stays with the page for the whole test — every load of the tab
 * reads the status — and the gallery's outer afterEach drops it once the page has left (`leaveGalleryPage`).
 */
import {schemas} from '../../src/lib/api/generated';
import {expect, type Page} from './playwright';

/** The path the Email tab reads its status from (`features/email/emailApi.ts`, `fetchEmailStatus`). */
const EMAIL_STATUS_PATH = '/api/v1/email/status';

/** What `GET /api/v1/email/status` answers, as the generated client types it. */
type EmailStatusResponse = ReturnType<typeof schemas.EmailStatusResponse.parse>;

/** The status the shot shows: ready, 47 of 50 emails left this hour, every check ok. */
export const GALLERY_EMAIL_STATUS = {
    state: 'ready',
    problem: null,
    variable: null,
    checks: [
        {check_id: 'email.smtp', severity: 'ok', i18n_key: 'email.checks.smtp.ok', detail: {}},
        {check_id: 'email.smtp_encryption', severity: 'ok', i18n_key: 'email.checks.smtpEncryption.ok', detail: {}},
    ],
    budget: {max_per_hour: 50, remaining: 47, retry_after_seconds: 0},
} satisfies EmailStatusResponse;

/**
 * Answer the Email tab's status read with {@link GALLERY_EMAIL_STATUS}, on every load of the test. Call it inside the
 * test — after the gallery's outer beforeEach, so that it is tried before the offline guard — and before the first
 * navigation.
 */
export async function serveGalleryEmailStatus(page: Page): Promise<void> {
    // Checked once, here: a schema that moved fails the test now, with Zod's own message.
    const body = schemas.EmailStatusResponse.parse(GALLERY_EMAIL_STATUS);
    await page.route(
        (url) => url.pathname === EMAIL_STATUS_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            await route.fulfill({json: body});
        },
    );
}

/**
 * The simulated status reached the page: ready, the budget left on show, no notice, the test email offered. A route
 * that stopped matching would let the lane's own answer through — email off — and the shot would show that, in silence.
 */
export async function expectGalleryEmailStatus(page: Page): Promise<void> {
    await expect(page.getByTestId('email-state'), 'the simulated status is drawn').toHaveAttribute('data-state', 'ready');
    await expect(page.getByTestId('email-budget'), 'the budget left is on show').toHaveAttribute('data-remaining', String(GALLERY_EMAIL_STATUS.budget.remaining));
    await expect(page.getByTestId('email-checks'), 'no notice: every check is ok').toHaveCount(0);
    await expect(page.getByTestId('email-test-button'), 'the test email is offered').toBeEnabled();
}
