/**
 * The legal notice of the instance (F09) and the managed profile's effects on the account side (F05): release 1.3,
 * workstream A, lot A9, through the real pages and the lane's real backend.
 *
 * `GET /api/v1/system/instance` (public) carries `legal: {terms_url, privacy_url}` — both null on the lane, which sets
 * neither LIBREFOLIO_TOS_URL nor LIBREFOLIO_PRIVACY_URL — beside `profile`, `selfhosted` on the lane. A test that needs
 * another instance answers its own page's read with the real response patched (`serveInstanceConfig`,
 * fixtures/instance-config.ts); the lane's own answer is observed through the same stub with an empty patch. `page.route()`
 * binds the browser context that installs it: no other test sees it, and nothing is written.
 *
 * What the product shows:
 *   - the compact notice (`legal-links`) under the card of every sign-in page (`auth-legal-links`, AuthPageFrame) and in
 *     the expanded sidebar's footer after the version (`sidebar-legal-links`); the full one (`legal-notice`) in
 *     Settings › About (`about-legal-card`). Each links the instance's terms and privacy pages when it sets them
 *     (`legal-terms-link`, `legal-privacy-link`), in a new tab, without opener or referrer;
 *   - the invitations to donate — `auth-donate-link` (the sign-in pages' bar), `header-donate-link`, `help-donate-link`
 *     (the Help menu), `support-coffee` (About's support card) — only once the server said self-hosted
 *     (`donationsVisible()`), so a managed instance never flashes one; the sharing buttons (`support-share-*`) stay;
 *   - on a managed instance, besides: the changelog offers no update check (`changelog-check-update`), its operator
 *     updates it; the forgot-password card sends the user to the administrator (`forgot-ask-admin`), without the
 *     server's commands (`forgot-reset-commands`) or the «no email» warning (`forgot-email-unavailable`).
 *
 * An absence is asserted only behind two presences: the configuration the page read is the one asked for (the stub's
 * own record, read once its handler has finished), and the region is drawn (a sibling every profile shows). A donation
 * link is absent both before the answer and on a managed instance — and so is the changelog's update check once it
 * follows the donations' rule (the developer's decision, 17/10) —, so on the signed-in managed page the proof that the
 * managed answer is in force comes first, from the answer itself: the stub sets `legal` to two https pages of this
 * spec's own beside `profile: 'managed'`, and the sidebar's legal line linking the stubbed terms page is that answer
 * applied. The links come from it alone — the lane sets no legal page, and the defaults the app holds until the server
 * answers carry none —, and the store takes an answer whole, its `profile` in the same step. Every absence is then read
 * in the same app runtime — a client-side hop to Settings, checked by a mark on `window` set before the proof: a page
 * load would bring the defaults back. Each donation absence is read twice, by test id and as no link to the donation
 * page (its host, from supportLinks.ts), so a renamed test id cannot pass for a hidden link.
 *
 * Covered (desktop):
 *   LGM-E-01  signed out, the lane's answer: `auth-legal-links` under the login card — after it in the frame and below it
 *             on screen —, holding `legal-links` and no legal link (the lane sets none); `auth-donate-link` once the
 *             configuration is in (self-hosted);
 *   LGM-E-02  signed out, `legal` stubbed with two https pages of this spec's own: both links in `auth-legal-links`, to
 *             exactly those pages, `target="_blank"`, `rel` with `noopener` and `noreferrer`; never clicked;
 *   LGM-E-03  signed in as e2e_test_user, the lane's answer: `header-donate-link`; `sidebar-legal-links` after
 *             `sidebar-version` in the footer, below it; Settings › About's `about-legal-card` holding a `legal-notice`. The
 *             contrast of LGM-E-04 on the same paths: the changelog's update check, the Help menu's coffee and About's
 *             coffee, all there when self-hosted;
 *   LGM-E-04  signed in, `profile` stubbed managed and `legal` set to the same two pages, before the page loads: the
 *             sidebar's legal line links exactly the stubbed terms page (the proof, first); then the changelog opened from
 *             `sidebar-version` has no update check; no donation link in the header, none in the open Help menu — whose
 *             GitHub issues item, found by its link, stays —, none in About's support card, whose sharing buttons stay
 *             (About's legal notice linking the same pages), none anywhere on the page;
 *   LGM-E-05  signed out, `profile` stubbed managed: the forgot card shows `forgot-ask-admin` — drawn only once the
 *             server said managed —, and neither `forgot-reset-commands` nor `forgot-email-unavailable`; no
 *             `auth-donate-link`, no donation link anywhere on the sign-in page.
 *
 * Read-only, parallel by default: GET requests and the sign-ins of e2e_test_user, a fixture user of the runner, whose
 * onboarding is read back (never changed) so that no guide competes for the clicks; no external link is clicked, no
 * setting is written, the language is never touched. Assertions read test ids, attributes and the stub's record, never
 * a translated text.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `legal-managed` of front-utility.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {serveInstanceConfig, type InstanceConfigStub, type ServedInstanceConfig} from '../fixtures/instance-config';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {openSettingsTab} from '../fixtures/settings-tabs';
import {TEST_USER} from '../fixtures/test-users';
import {BUY_ME_A_COFFEE_URL, SOCIAL_SHARE_ORDER} from '../../src/lib/features/support/supportLinks';

/** The lane's legal part: it sets neither LIBREFOLIO_TOS_URL nor LIBREFOLIO_PRIVACY_URL. */
const LANE_LEGAL = {terms_url: null, privacy_url: null};
/** Two pages of this spec's own, on a reserved domain, served by the stub alone and never opened. */
const TERMS_URL = 'https://legal.example.org/librefolio-e2e/terms?lot=a9';
const PRIVACY_URL = 'https://legal.example.org/librefolio-e2e/privacy?lot=a9';
/** The legal part a test stubs: the lane sets no legal page, so a link to one of these comes from the stubbed answer alone. */
const SPEC_LEGAL = {terms_url: TERMS_URL, privacy_url: PRIVACY_URL};
/** «Report a bug», the Help menu item every profile keeps: HelpMenu.svelte's `githubIssuesUrl`, found by its link. */
const GITHUB_ISSUES_URL = 'https://github.com/Librefolio/LibreFolio/issues';
/** Any link to the donation page, whatever its test id: every invitation to donate leads to BUY_ME_A_COFFEE_URL's site. */
const DONATION_LINK = `a[href^="${new URL(BUY_ME_A_COFFEE_URL).origin}/"]`;

// Budgets: deadlines, never delays.
/** The first paint of `/`: `login-page` renders once the root page's GET /auth/me has answered. */
const FIRST_PAINT_MS = 30_000;
/** What waits for the instance configuration: GET /api/v1/system/instance, through the stub. */
const CONFIG_MS = 15_000;
/** From a client-side hop to the next page drawn. */
const PAGE_MS = 20_000;
/** The reaction to a click on something already on screen. */
const UI_MS = 5_000;

// A sign-in on a loaded lane can take most of 30 s by itself (login()'s ARRIVAL_MS); a signed-in test then opens a modal,
// a menu and a second page.
test.setTimeout(90_000);

// Desktop only, as the runner runs it (_run_playwright's default project): on a phone the sidebar — its version, its
// legal line — is off-canvas, and the subject does not depend on the viewport.
test.skip(({isMobile}) => isMobile, 'Desktop only: on a phone the sidebar footer, with sidebar-version and sidebar-legal-links, is off-canvas');

/**
 * The configuration the page read is the one meant: the stub's handler has finished a read — polled, since the page may
 * draw the answer before the handler has recorded it —, nothing went wrong on the way, and every answer carried
 * `expected`.
 */
async function expectServed(instance: InstanceConfigStub, expected: Partial<ServedInstanceConfig>, what: string): Promise<void> {
    await expect.poll(() => instance.answered, {message: 'the page read GET /api/v1/system/instance through the stub', timeout: CONFIG_MS}).toBeGreaterThan(0);
    expect(instance.problems, 'the stub answered every read as asked').toEqual([]);
    expect(instance.served.length, 'the stub served at least one answer').toBeGreaterThan(0);
    for (const [index, answer] of instance.served.entries()) expect(answer, `${what} (read ${index + 1} of GET /api/v1/system/instance)`).toMatchObject(expected);
}

/** How far below the bottom edge of `upper` the top edge of `lower` lies, in CSS pixels; null while either has no box. One-shot: polled. */
async function gapBelow(upper: Locator, lower: Locator): Promise<number | null> {
    const above = await upper.boundingBox();
    const below = await lower.boundingBox();
    return above && below ? below.y - (above.y + above.height) : null;
}

/** Sign e2e_test_user in; ends on the app shell, with no onboarding flow due (read back) to put a guide over the clicks. */
async function signIn(page: Page): Promise<void> {
    await login(page, TEST_USER);
    await expect(page.getByTestId('app-shell'), `${TEST_USER.username} arrives on the app shell`).toBeVisible();
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `${TEST_USER.username} must be grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

/** Open the changelog from the sidebar's version; ends on its toolbar drawn: the search field, there in every profile. */
async function openChangelog(page: Page): Promise<Locator> {
    await page.getByTestId('sidebar-version').click();
    const modal = page.getByTestId('changelog-modal');
    await expect(modal).toBeVisible({timeout: UI_MS});
    await expect(modal.getByTestId('changelog-search'), 'the toolbar that holds the update check is drawn').toBeVisible();
    return modal;
}

/** Close the changelog with Escape, pressed in its own search field so that the key starts inside the dialog; ends on the modal gone. */
async function closeChangelog(modal: Locator): Promise<void> {
    await modal.getByTestId('changelog-search').press('Escape');
    await expect(modal).toBeHidden({timeout: UI_MS});
}

/** Open the Help menu of `bar`; ends on its panel drawn, the GitHub issues item («report a bug», every profile) in it. */
async function openHelpMenu(bar: Locator): Promise<Locator> {
    await bar.getByTestId('help-menu-button').click();
    const panel = bar.getByTestId('help-menu-panel');
    await expect(panel).toBeVisible({timeout: UI_MS});
    await expect(panel.locator(`a[href="${GITHUB_ISSUES_URL}"]`), 'the GitHub issues item, found by its link').toBeVisible();
    return panel;
}

/** Close the Help menu of `bar` with its own button; ends on the panel gone. */
async function closeHelpMenu(bar: Locator): Promise<void> {
    await bar.getByTestId('help-menu-button').click();
    await expect(bar.getByTestId('help-menu-panel')).toBeHidden({timeout: UI_MS});
}

/** Settings › About, reached through the sidebar: a client-side hop, so the app runtime and its configuration stay. */
async function openAbout(page: Page): Promise<Locator> {
    await page.getByTestId('nav-settings').click();
    await expect(page).toHaveURL(/\/settings(?:[?#]|$)/, {timeout: PAGE_MS});
    await openSettingsTab(page, 'about');
    const about = page.getByTestId('about-tab');
    await expect(about).toBeVisible({timeout: UI_MS});
    return about;
}

type MarkedWindow = Window & {__lfLegalManagedRuntime?: true};

/** Mark the running app, so that a later check proves no page load came in between: a load brings back the defaults. */
async function markRuntime(page: Page): Promise<void> {
    await page.evaluate(() => {
        (window as MarkedWindow).__lfLegalManagedRuntime = true;
    });
}

async function expectSameRuntime(page: Page, message: string): Promise<void> {
    const kept = await page.evaluate(() => (window as MarkedWindow).__lfLegalManagedRuntime === true);
    expect(kept, message).toBe(true);
}

test.describe('Legal notice — signed out', () => {
    test('LGM-E-01: the lane’s answer — the compact notice under the login card, without links; the donation link once the server said self-hosted', async ({page}) => {
        const instance = await serveInstanceConfig(page, {});
        try {
            await page.goto('/');
            const frame = page.getByTestId('login-page');
            await expect(frame).toBeVisible({timeout: FIRST_PAINT_MS});
            // Presence first: the bar's donation link shows only once the server has said self-hosted, so the configuration
            // is in — and it is the lane's own.
            await expect(frame.getByTestId('auth-page-controls').getByTestId('auth-donate-link'), 'self-hosted on the lane: the donation link, once the server said so').toBeVisible({timeout: CONFIG_MS});
            await expectServed(instance, {profile: 'selfhosted', legal: LANE_LEGAL}, 'precondition: the lane is self-hosted and sets no legal page (neither LIBREFOLIO_TOS_URL nor LIBREFOLIO_PRIVACY_URL)');

            const card = frame.getByTestId('login-modal');
            const line = frame.getByTestId('auth-legal-links');
            await expect(line, 'the compact legal notice, on the sign-in page').toBeVisible();
            await expect(line.getByTestId('legal-links'), 'holding the compact notice').toBeVisible();
            // Under the card: after it in the frame, and below it on screen.
            await expect(frame.locator('[data-testid="login-modal"] ~ [data-testid="auth-legal-links"]'), 'after the login card, in the same frame').toBeVisible();
            await expect.poll(() => gapBelow(card, line), {message: 'auth-legal-links starts below the bottom edge of the login card', timeout: UI_MS}).toBeGreaterThanOrEqual(0);
            // The notice drawn, the configuration in: no legal link, since the lane sets no legal page.
            await expect(line.getByTestId('legal-terms-link')).toHaveCount(0);
            await expect(line.getByTestId('legal-privacy-link')).toHaveCount(0);
        } finally {
            await instance.dispose();
        }
    });

    test('LGM-E-02: `legal` set to two https pages — both links in the compact notice, to exactly those pages, in a new tab without opener or referrer', async ({page}) => {
        const instance = await serveInstanceConfig(page, {legal: SPEC_LEGAL});
        try {
            await page.goto('/');
            const frame = page.getByTestId('login-page');
            await expect(frame).toBeVisible({timeout: FIRST_PAINT_MS});
            const notice = frame.getByTestId('auth-legal-links').getByTestId('legal-links');
            const links = [
                ['legal-terms-link', TERMS_URL],
                ['legal-privacy-link', PRIVACY_URL],
            ] as const;
            for (const [testId, url] of links) {
                const link = notice.getByTestId(testId);
                await expect(link, `${testId}, under the login card once the configuration is in`).toBeVisible({timeout: CONFIG_MS});
                await expect(link, `${testId} leads to exactly the page the instance set`).toHaveAttribute('href', url);
                await expect(link, 'in a new tab').toHaveAttribute('target', '_blank');
                await expect(link, 'without opener').toHaveAttribute('rel', /(?:^|\s)noopener(?:\s|$)/);
                await expect(link, 'without referrer').toHaveAttribute('rel', /(?:^|\s)noreferrer(?:\s|$)/);
            }
            await expectServed(instance, {legal: SPEC_LEGAL}, 'the stub served the two legal pages');
        } finally {
            await instance.dispose();
        }
    });
});

test.describe('Legal notice and donations — signed in, self-hosted', () => {
    test('LGM-E-03: the lane’s answer — the header’s donation link, the compact notice after the sidebar’s version, the legal card in Settings › About; and what a managed instance hides, here', async ({page}) => {
        const instance = await serveInstanceConfig(page, {});
        try {
            await signIn(page);
            const header = page.getByTestId('app-header');
            await expect(header.getByTestId('header-donate-link'), 'self-hosted on the lane: the donation link in the header').toBeVisible({timeout: CONFIG_MS});
            await expectServed(instance, {profile: 'selfhosted', legal: LANE_LEGAL}, 'precondition: the lane is self-hosted and sets no legal page (neither LIBREFOLIO_TOS_URL nor LIBREFOLIO_PRIVACY_URL)');

            // The sidebar's footer: the compact notice after the version — a later sibling in its block, and below it.
            const version = page.getByTestId('sidebar-version');
            const line = page.locator('[data-testid="sidebar-version"] ~ [data-testid="sidebar-legal-links"]');
            await expect(line, 'sidebar-legal-links, after sidebar-version in the footer').toBeVisible();
            await expect.poll(() => gapBelow(version, line), {message: 'sidebar-legal-links starts below the bottom edge of sidebar-version', timeout: UI_MS}).toBeGreaterThanOrEqual(0);
            await expect(line.getByTestId('legal-links'), 'holding the compact notice').toBeVisible();
            await expect(line.getByTestId('legal-terms-link'), 'no legal page on the lane').toHaveCount(0);
            await expect(line.getByTestId('legal-privacy-link')).toHaveCount(0);

            // The contrast of LGM-E-04, on the same paths: what a managed instance hides is here on a self-hosted one.
            const changelog = await openChangelog(page);
            await expect(changelog.getByTestId('changelog-check-update'), 'self-hosted: the changelog offers the update check').toBeVisible();
            await closeChangelog(changelog);
            const help = await openHelpMenu(header);
            await expect(help.getByTestId('help-donate-link'), 'self-hosted: the Help menu offers a coffee').toBeVisible();
            await closeHelpMenu(header);

            const about = await openAbout(page);
            const legalCard = about.getByTestId('about-legal-card');
            await expect(legalCard, 'Settings › About shows the legal card').toBeVisible();
            await expect(legalCard.getByTestId('legal-notice'), 'holding the full legal notice').toBeVisible();
            const support = about.getByTestId('about-support-card');
            await expect(support.getByTestId('support-coffee'), 'self-hosted: the coffee in About’s support card').toBeVisible();
            expect(SOCIAL_SHARE_ORDER.length, 'positive control: supportLinks.ts lists the sharing platforms').toBeGreaterThan(0);
            for (const platform of SOCIAL_SHARE_ORDER) await expect(support.getByTestId(`support-share-${platform}`), `the sharing button for ${platform}`).toBeVisible();
        } finally {
            await instance.dispose();
        }
    });
});

test.describe('Managed profile — signed in', () => {
    test('LGM-E-04: profile managed, with legal pages — once the sidebar links the stubbed terms page: no update check in the changelog, no donation link in the header, the Help menu or About’s support card (its sharing stays), none anywhere', async ({page}) => {
        const instance = await serveInstanceConfig(page, {profile: 'managed', legal: SPEC_LEGAL});
        try {
            await signIn(page);
            // Marked before the proof: the proof and every absence below are read in one runtime, checked at the end.
            await markRuntime(page);

            // The proof, before any absence: a link to the stubbed terms page comes from the stubbed answer alone, and the
            // store takes an answer whole, its `profile` in the same step. The sidebar linking that page is the managed
            // answer in force in this runtime.
            const sidebarLegal = page.getByTestId('sidebar-legal-links');
            const sidebarTerms = sidebarLegal.getByTestId('legal-terms-link');
            await expect(sidebarTerms, 'the proof: the sidebar’s legal line links the terms page only the stubbed answer carries').toHaveAttribute('href', TERMS_URL, {timeout: CONFIG_MS});
            await expect(sidebarTerms).toBeVisible();
            await expect(sidebarLegal.getByTestId('legal-privacy-link'), 'and the privacy page the same answer carries').toHaveAttribute('href', PRIVACY_URL);
            await expectServed(instance, {profile: 'managed', legal: SPEC_LEGAL}, 'the stub served a managed instance with the two legal pages');

            // The changelog, its toolbar drawn: no update check.
            const changelog = await openChangelog(page);
            await expect(changelog.getByTestId('changelog-check-update'), 'managed: no update check in the changelog — the operator updates the instance').toHaveCount(0);
            await closeChangelog(changelog);

            // The header, drawn (its Help button, every profile): no donation link.
            const header = page.getByTestId('app-header');
            await expect(header.getByTestId('help-menu-button'), 'the header is drawn').toBeVisible();
            await expect(header.getByTestId('header-donate-link'), 'managed: no donation link in the header').toHaveCount(0);
            await expect(header.locator(DONATION_LINK), 'nor any link to the donation page in it').toHaveCount(0);

            // The Help menu, open, its GitHub issues item there: no coffee.
            const help = await openHelpMenu(header);
            await expect(help.getByTestId('help-donate-link'), 'managed: no coffee in the Help menu').toHaveCount(0);
            await expect(help.locator(DONATION_LINK), 'nor any link to the donation page in it').toHaveCount(0);
            await closeHelpMenu(header);

            // Settings › About, reached client-side: its legal notice links the stubbed pages — the same answer, on this
            // page —; the sharing stays, the coffee goes.
            const about = await openAbout(page);
            const notice = about.getByTestId('about-legal-card').getByTestId('legal-notice');
            await expect(notice, 'About’s legal notice, in every profile').toBeVisible();
            await expect(notice.getByTestId('legal-terms-link'), 'linking the stubbed terms page: the same answer, on this page').toHaveAttribute('href', TERMS_URL);
            await expect(notice.getByTestId('legal-privacy-link'), 'and the privacy page').toHaveAttribute('href', PRIVACY_URL);
            const support = about.getByTestId('about-support-card');
            await expect(support, 'About’s support card is drawn').toBeVisible();
            expect(SOCIAL_SHARE_ORDER.length, 'positive control: supportLinks.ts lists the sharing platforms').toBeGreaterThan(0);
            for (const platform of SOCIAL_SHARE_ORDER) await expect(support.getByTestId(`support-share-${platform}`), `managed: the sharing button for ${platform} stays`).toBeVisible();
            await expect(support.getByTestId('support-coffee'), 'managed: no coffee in About’s support card').toHaveCount(0);
            await expect(support.locator(DONATION_LINK), 'nor any link to the donation page in it').toHaveCount(0);
            await expect(page.locator(DONATION_LINK), 'managed: no link to the donation page anywhere on the page').toHaveCount(0);

            await expectSameRuntime(page, 'the proof and every absence above were read in one app runtime: no page load in between');
            expect(instance.problems, 'the stub answered every read as asked').toEqual([]);
        } finally {
            await instance.dispose();
        }
    });
});

test.describe('Managed profile — signed out', () => {
    test('LGM-E-05: profile managed — the forgot card sends the user to the administrator, without the server’s commands or the email warning; no donation link', async ({page}) => {
        const instance = await serveInstanceConfig(page, {profile: 'managed'});
        try {
            await page.goto('/');
            const frame = page.getByTestId('login-page');
            await expect(frame).toBeVisible({timeout: FIRST_PAINT_MS});
            await frame.getByTestId('goto-forgot').click();
            const card = frame.getByTestId('forgot-modal');
            await expect(card).toBeVisible({timeout: UI_MS});

            // Presence first: «ask your administrator» is drawn only once the server has said managed — the proof that the
            // answer is in force.
            await expect(card.getByTestId('forgot-ask-admin'), 'managed: the card sends the user to the administrator').toBeVisible({timeout: CONFIG_MS});
            await expectServed(instance, {profile: 'managed'}, 'the stub served a managed instance');
            await expect(card.getByTestId('forgot-back-to-login'), 'the card is drawn around it').toBeVisible();
            await expect(card.getByTestId('forgot-reset-commands'), 'managed: no server commands — its users have no terminal').toHaveCount(0);
            await expect(card.getByTestId('forgot-email-unavailable'), 'managed: no «no email» warning either').toHaveCount(0);

            // The bar, drawn (its Help button, every profile): no donation link, and none anywhere on the page.
            const bar = frame.getByTestId('auth-page-controls');
            await expect(bar.getByTestId('help-menu-button'), 'the sign-in bar is drawn').toBeVisible();
            await expect(bar.getByTestId('auth-donate-link'), 'managed: no donation link in the sign-in bar').toHaveCount(0);
            await expect(page.locator(DONATION_LINK), 'managed: no link to the donation page anywhere on the sign-in page').toHaveCount(0);
        } finally {
            await instance.dispose();
        }
    });
});
