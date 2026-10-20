/**
 * Gallery, every page: an administrator's security checks (`GET /api/v1/security/checks`), answered as a well-configured
 * self-hosted instance answers them — every one `ok`.
 *
 * The sidebar's connection line (`layout/ConnectionSecurityIndicator.svelte`, on every app page) reads the checks once per
 * page load for an administrator (N69b, `securityChecks.ensureLoaded()`). With an `error` or a `warning` among them it
 * draws a dot on its shield and, in its details, a link to them; the header puts the dot on the phone's menu button too,
 * and the same count is the badge of «Administration» and «Security» in Settings (`securityFindings.ts`,
 * `attentionCount`: errors and warnings; an `info` is not counted). The gallery's lane runs with the login limit off, so
 * its own answer holds a warning, `accounts.login_limit`: nearly every shot signs in as an administrator, and each would
 * carry the dot — drawn once a read the page makes on its own comes back, so caught by one run and missed by the next.
 * The browser adds no finding of its own: the open-registration notice needs a host outside the local network
 * (`features/auth/localHost.ts`), and the gallery's hosts are `localhost` and the Security shot's `lf-e2e.lan`.
 *
 * So the gallery's outer beforeEach has every page of every test read {@link GALLERY_SECURITY_CHECKS}: every check of the
 * platform, in its order — `CONFIG_CHECKS` of `backend/app/services/platform/config_audit.py`, then
 * `platform.plugin_secrets`, which `backend/app/api/v1/security.py` appends —, each on the branch the backend takes for a
 * well-configured self-hosted instance, with that branch's own message key. Those branches are the self-hosted profile's
 * defaults — frame protection and the report-only CSP off, a generated instance key, no hosting panel's backup token, no
 * size limit on a backup's upload or restore, test mode off —, the login limit on, and email configured, as
 * galleryEmail.ts simulates it for the Email tab. A check the backend adds later is missing here until it is written in:
 * that matters only to a picture of the Security tab's list of passed checks, never to the dot or to the badge, which
 * count what is not `ok`.
 *
 * {@link serveGallerySecurityChecks} answers that read and nothing else: `GET` on the checks' path, whatever the origin —
 * the Security shot opens the app under a LAN name of the lane. Any other method falls back to the routes registered
 * before it (the gallery's offline guard), then to the backend; nothing is continued by hand. The body is the shape the
 * backend sends (`backend/app/schemas/security.py`, `SecurityChecksResponse`), typed with the generated client's type and
 * checked against its Zod schema once, at registration: a contract that moved fails the test there, with Zod's own
 * message. A test that needs findings registers its own route after this one: Playwright tries the latest route first.
 *
 * Each page counts the reads answered ({@link gallerySecurityReads}). Before its answer the line says 0 too, so a shot
 * that asserts the zero first waits for a read answered after its load ({@link expectGallerySecurityServed}).
 *
 * Registered before the first navigation, the route stays with the page for the whole test, and the gallery's outer
 * afterEach drops it once the page has left (`leaveGalleryPage`).
 */
import {schemas} from '../../src/lib/api/generated';
import {expect, type Page} from './playwright';

/** The path the security checks are read from (`features/settings/security/securityChecksApi.ts`, `fetchSecurityChecks`). */
const SECURITY_CHECKS_PATH = '/api/v1/security/checks';

/** What `GET /api/v1/security/checks` answers, as the generated client types it. */
type SecurityChecksResponse = ReturnType<typeof schemas.SecurityChecksResponse.parse>;

/** The checks every gallery page reads: the platform's 17, in its order, each `ok` — on which branch, and why, above. */
const GALLERY_SECURITY_CHECKS = {
    items: [
        {check_id: 'platform.jwt_secret', severity: 'ok', i18n_key: 'instance.checks.jwtSecret.ok', detail: {}},
        {check_id: 'platform.secrets_set_twice', severity: 'ok', i18n_key: 'instance.checks.secretsSetTwice.ok', detail: {}},
        {check_id: 'platform.instance_key', severity: 'ok', i18n_key: 'instance.checks.instanceKey.ok', detail: {source: 'generated'}},
        {check_id: 'platform.session_cookie', severity: 'ok', i18n_key: 'instance.checks.sessionCookie.ok', detail: {}},
        {check_id: 'platform.client_address', severity: 'ok', i18n_key: 'instance.checks.clientAddress.ok', detail: {}},
        {check_id: 'platform.frame_protection', severity: 'ok', i18n_key: 'instance.checks.frameProtection.offSelfHosted', detail: {}},
        {check_id: 'platform.csp_report_only', severity: 'ok', i18n_key: 'instance.checks.cspReportOnly.offSelfHosted', detail: {}},
        {check_id: 'platform.log_level', severity: 'ok', i18n_key: 'instance.checks.logLevel.ok', detail: {}},
        {check_id: 'platform.test_mode', severity: 'ok', i18n_key: 'instance.checks.testMode.off', detail: {}},
        {check_id: 'backup.panel_token', severity: 'ok', i18n_key: 'backup.checks.panelToken.off', detail: {}},
        {check_id: 'backup.upload_limit', severity: 'ok', i18n_key: 'backup.checks.uploadLimit.unlimited', detail: {}},
        {check_id: 'backup.restore_limit', severity: 'ok', i18n_key: 'backup.checks.restoreLimit.unlimited', detail: {}},
        {check_id: 'accounts.login_limit', severity: 'ok', i18n_key: 'auth.checks.loginLimit.ok', detail: {}},
        {check_id: 'email.smtp', severity: 'ok', i18n_key: 'email.checks.smtp.ok', detail: {}},
        {check_id: 'email.smtp_encryption', severity: 'ok', i18n_key: 'email.checks.smtpEncryption.ok', detail: {}},
        {check_id: 'email.links', severity: 'ok', i18n_key: 'email.checks.links.ok', detail: {}},
        {check_id: 'platform.plugin_secrets', severity: 'ok', i18n_key: 'instance.checks.pluginSecrets.ok', detail: {}},
    ],
} satisfies SecurityChecksResponse;

/** The reads of the checks answered on each page, counted from {@link serveGallerySecurityChecks} on. */
const states = new WeakMap<Page, {reads: number}>();

/**
 * Answer every read of the security checks on `page` with {@link GALLERY_SECURITY_CHECKS}, and count it. Called by the
 * gallery's outer beforeEach on every page — after the offline guard, so that it is tried before it — and before the
 * first navigation. A test that needs findings registers its own route after this one.
 */
export async function serveGallerySecurityChecks(page: Page): Promise<void> {
    // Checked once, here: a schema that moved fails the test now, with Zod's own message.
    const body = schemas.SecurityChecksResponse.parse(GALLERY_SECURITY_CHECKS);
    const state = {reads: 0};
    states.set(page, state);
    // The path alone, never the origin: the Security shot reads the checks under a LAN name of the lane.
    await page.route(
        (url) => url.pathname === SECURITY_CHECKS_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            state.reads += 1;
            await route.fulfill({json: body});
        },
    );
}

/** How many reads of the security checks the gallery's fixture has answered on `page`: a counter a shot reads as a delta. */
export function gallerySecurityReads(page: Page): number {
    const state = states.get(page);
    if (!state) throw new Error("the gallery's security checks are not served on this page: the outer beforeEach serves them (serveGallerySecurityChecks)");
    return state.reads;
}

/**
 * The page read the security checks from the gallery's fixture after `since` — {@link gallerySecurityReads}, read before
 * the load. An administrator's page reads them once per load, and before the answer its line says 0 too: a shot asserts
 * that zero only after this. A route that stopped matching would let the lane's own answer through, its warning drawn
 * as a dot: it fails here instead.
 */
export async function expectGallerySecurityServed(page: Page, since: number): Promise<void> {
    await expect
        .poll(() => gallerySecurityReads(page), {
            message: "the page did not read the security checks from the gallery fixture after its load (gallerySecurity.ts): an administrator's page reads them once per load, and a read the route no longer matches is answered by the lane, with the login limit's warning",
            timeout: 15_000,
        })
        .toBeGreaterThan(since);
}
