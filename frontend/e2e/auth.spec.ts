import {readdirSync, readFileSync} from 'node:fs';
import {expect, test, type APIRequestContext, type Page, type Request} from './fixtures/playwright';
import {login, logout, setLanguage} from './fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from './fixtures/test-users';
import {LANGUAGE_INFO, SUPPORTED_LANGUAGES, t} from './fixtures/i18n-data';
import {uniqueSuffix} from './fixtures/unique';

test.describe('Authentication', () => {
    test.describe('Core Auth Flow (language-agnostic)', () => {
        test('login page renders correctly', async ({page}) => {
            await page.goto('/');
            // Wait for auth check to complete (3s timeout for localhost)
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            // Then check login form elements
            await expect(page.getByTestId('login-modal')).toBeVisible();
            await expect(page.getByTestId('login-form')).toBeVisible();
            await expect(page.getByTestId('login-username')).toBeVisible();
            await expect(page.getByTestId('login-submit')).toBeVisible();
        });

        test('successful login redirects to dashboard', async ({page}) => {
            await login(page, TEST_USER);
            await expect(page).toHaveURL(/.*dashboard.*/);
            await expect(page.getByTestId('dashboard-page')).toBeVisible();
        });

        test('invalid credentials show error', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await page.getByTestId('login-username').fill('wronguser');
            await page.getByTestId('login-password').fill('wrongpass');
            await page.getByTestId('login-submit').click();
            // Error message should appear (any language)
            await expect(page.getByTestId('login-error')).toBeVisible({timeout: 3000});
        });

        test('logout returns to login page', async ({page}) => {
            await login(page, TEST_USER);
            await logout(page);
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await expect(page.getByTestId('login-modal')).toBeVisible();
        });

        test('admin can login', async ({page}) => {
            await login(page, TEST_ADMIN);
            await expect(page).toHaveURL(/.*dashboard.*/);
            await expect(page.getByTestId('dashboard-page')).toBeVisible();
        });
    });

    test.describe('Register Modal', () => {
        test('can open register modal from login', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await page.getByTestId('goto-register').click();
            await expect(page.getByTestId('register-modal')).toBeVisible();
        });

        test('register form has all required fields', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await page.getByTestId('goto-register').click();
            await expect(page.getByTestId('register-modal')).toBeVisible();

            // Check all form fields
            await expect(page.getByTestId('register-username')).toBeVisible();
            await expect(page.getByTestId('register-email')).toBeVisible();
            await expect(page.getByTestId('register-password')).toBeVisible();
            await expect(page.getByTestId('register-confirm-password')).toBeVisible();
            await expect(page.getByTestId('register-submit')).toBeVisible();
        });

        test('password strength meter shows when typing', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await page.getByTestId('goto-register').click();
            await expect(page.getByTestId('register-modal')).toBeVisible();

            // Password strength should not be visible initially
            await expect(page.getByTestId('password-strength-meter')).not.toBeVisible();

            // Type a password
            await page.getByTestId('register-password').fill('Test123!');

            // Password strength meter should appear
            await expect(page.getByTestId('password-strength-meter')).toBeVisible();
        });

        test('can navigate back to login from register', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await page.getByTestId('goto-register').click();
            await expect(page.getByTestId('register-modal')).toBeVisible();

            // Click back to login
            await page.getByTestId('goto-login').click();
            await expect(page.getByTestId('login-modal')).toBeVisible();
        });
    });

    // «Register here» follows the instance setting (K, step 22). Once an admin closes registration
    // (`enable_registration` = 'false') the backend refuses `POST /auth/register` with a 403, and the login page
    // offered the link anyway: the refusal came only after a filled-in form. Closed here for this page only — the real
    // `GET /api/v1/settings/global`, answered with that one value changed, never a hand-built list (Zodios validates the
    // response) — and never written: the setting is shared by every user of the lane. The open case is
    // `can open register modal from login` above, on the real setting.
    test.describe('Register link and the registration setting', () => {
        type RegistrationStub = {reads: number; problems: string[]};

        /**
         * Answer this page's `GET /api/v1/settings/global` — that path only, never `/global/{key}` or `/global/bulk` —
         * with the real response and `enable_registration` set to `'false'`. `reads` counts the reads the stub handled,
         * `problems` why one of them was not answered with registration closed. The item must be in the real list: the
         * backend creates every global setting at startup, so a list without it is a broken precondition, reported by
         * name instead of as a link that stayed. Any other method falls through: nothing here writes a setting.
         */
        async function closeRegistrationForThisPage(page: Page): Promise<RegistrationStub> {
            const stub: RegistrationStub = {reads: 0, problems: []};
            await page.route('**/api/v1/settings/global', async (route, request) => {
                if (request.method() !== 'GET') {
                    await route.fallback();
                    return;
                }
                try {
                    const response = await route.fetch();
                    if (!response.ok()) {
                        stub.problems.push(`the real GET /settings/global answered ${response.status()}`);
                        await route.fulfill({response});
                        return;
                    }
                    const body = (await response.json()) as {items?: Array<Record<string, unknown>>};
                    const items = body.items ?? [];
                    if (!items.some((item) => item.key === 'enable_registration')) {
                        stub.problems.push(`the real GET /settings/global has no enable_registration item (keys: ${items.map((item) => String(item.key)).join(', ') || 'none'})`);
                        await route.fulfill({response});
                        return;
                    }
                    await route.fulfill({response, json: {...body, items: items.map((item) => (item.key === 'enable_registration' ? {...item, value: 'false'} : item))}});
                } catch (error) {
                    // Nobody awaits a route callback: what it throws would surface as an unhandled rejection on
                    // whatever the worker runs next. Recorded instead, and asserted by the test that needed the read.
                    stub.problems.push(`the stub failed: ${String(error)}`);
                } finally {
                    stub.reads += 1;
                }
            });
            return stub;
        }

        test('the login page does not offer «Register here» once an admin closed registration', async ({page}) => {
            const stub = await closeRegistrationForThisPage(page);

            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 10_000});
            await expect(page.getByTestId('login-form')).toBeVisible();
            // A sibling control of the link: the card is up, so a link missing below is the setting, not a slow page.
            await expect(page.getByTestId('goto-forgot')).toBeVisible();

            // Until the page has read the setting, a missing link proves nothing. Soft, so that a page that never asks
            // still goes on to report the link it shows; the test stays red either way.
            await expect.soft.poll(() => stub.reads, {message: 'The login page never read GET /api/v1/settings/global: it cannot know that an admin closed registration', timeout: 10_000}).toBeGreaterThan(0);
            expect(stub.problems, 'The stub could not answer «registration closed»: the precondition is broken, not the page').toEqual([]);

            await expect(page.getByTestId('goto-register'), 'Registration is closed: the login page must not offer «Register here»').toHaveCount(0, {timeout: 5_000});
            await expect(page.getByTestId('goto-forgot'), 'Only the register link goes: the rest of the card stays').toBeVisible();
        });
    });

    test.describe('Forgot Password Modal', () => {
        test('can open forgot password modal from login', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await page.getByTestId('goto-forgot').click();
            await expect(page.getByTestId('forgot-modal')).toBeVisible();
        });

        test('can navigate back to login from forgot password', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await page.getByTestId('goto-forgot').click();
            await expect(page.getByTestId('forgot-modal')).toBeVisible();

            // Click back to login
            await page.getByTestId('forgot-back-to-login').click();
            await expect(page.getByTestId('login-modal')).toBeVisible();
        });
    });

    test.describe('Language Selector', () => {
        test('language selector is visible and clickable', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await expect(page.getByTestId('language-selector')).toBeVisible();
            await page.getByTestId('language-selector-button').click();
            // Dropdown should open with language options (use menuitem role to be specific)
            for (const lang of SUPPORTED_LANGUAGES) {
                const info = LANGUAGE_INFO[lang];
                if (info) {
                    await expect(page.getByRole('menuitem', {name: new RegExp(info.name)})).toBeVisible();
                }
            }
        });

        // Dynamic tests for each supported language
        for (const lang of SUPPORTED_LANGUAGES) {
            const info = LANGUAGE_INFO[lang];
            if (!info) continue;

            test(`switching to ${info.name} (${lang}) updates login button text`, async ({page}) => {
                await page.goto('/');
                await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
                await setLanguage(page, lang as any);

                // Get expected login button text for this language
                const expectedText = t(lang, 'auth.login');
                await expect(page.getByTestId('login-submit')).toContainText(expectedText);
            });
        }
    });
});

// ---------------------------------------------------------------------------
// Integrated onboarding — canonical vs. newly registered accounts
// ---------------------------------------------------------------------------
//
// Seeding (backend/test_scripts/test_db/populate_mock_data.py,
// `_grandfather_onboarding_for_test_users`): every canonical E2E user (TEST_USER,
// TEST_ADMIN, ...) is grandfathered `completed` on every onboarding flow, exactly
// like a real pre-existing account under the Alembic migration. A user registered
// during a test run gets none of that: its onboarding rows are created lazily,
// `pending`, the moment anything reads them — indistinguishable from a genuine new
// signup. Each test below registers and deletes its own disposable account; nothing
// is shared with, or mutated on, a canonical user.
test.describe('Integrated onboarding', () => {
    type DisposableUser = {id: number; username: string; email: string; password: string};

    async function registerDisposableUser(request: APIRequestContext, tag: string) {
        const suffix = uniqueSuffix();
        const user = {username: `onb_${tag}_${suffix}`, email: `onb_${tag}_${suffix}@example.com`, password: `Onb9!_${suffix}`};
        const registered = await request.post('/api/v1/auth/register', {data: user});
        expect(registered.status(), 'Disposable-account registration must be enabled; do not change global settings to repair it').toBe(201);
        const created = (await registered.json()) as {user: {id: number}};
        return {...user, id: created.user.id};
    }

    async function deleteDisposableUser(request: APIRequestContext, user: DisposableUser) {
        const loggedIn = await request.post('/api/v1/auth/login', {data: {username: user.username, password: user.password}});
        expect(loggedIn.ok(), 'Cleanup must authenticate as the very account it is about to remove').toBe(true);
        expect(((await loggedIn.json()) as {user: {id: number}}).user.id, 'Cleanup must remain scoped to the account created by this test').toBe(user.id);
        const removed = await request.delete('/api/v1/auth/users/me');
        expect(removed.ok()).toBe(true);
    }

    async function selectWelcomeLocale(page: Page, locale: string) {
        const combobox = page.getByTestId('welcome-language').locator('[aria-haspopup="listbox"]');
        await combobox.click();
        await expect(combobox).toHaveAttribute('aria-controls', /.+/);
        const listboxId = await combobox.getAttribute('aria-controls');
        if (!listboxId) throw new Error('Welcome language selector did not publish its listbox id');

        // WelcomeForm does not provide SimpleSelect.optionTestId. Its generated,
        // value-bearing option id is the only stable non-translated selector exposed
        // by the control; never select the locale by its localized label.
        const option = page.locator(`[id="${listboxId}-option-${encodeURIComponent(locale)}"][role="option"]`);
        await expect(option).toBeVisible();
        await option.click();
    }

    async function expectLocaleState(page: Page, locale: string) {
        const localeState = page.locator('[data-i18n-ready]');
        await expect(localeState).toHaveAttribute('lang', locale);
        await expect(localeState).toHaveAttribute('data-i18n-ready', 'true');
    }

    /** A brand-new account always reaches the pending intro scene after Welcome.
     *  End it through the product's permanent Skip before testing later sessions. */
    async function skipIntroScene(page: Page) {
        const scene = page.getByTestId('onboarding-intro-scene');
        await expect(scene).toHaveAttribute('data-state', 'intro-scene', {timeout: 10_000});
        await page.getByTestId('onboarding-intro-close').click();
        await expect(scene).toHaveCount(0, {timeout: 5_000});
    }

    type HeldChunk = {isHeld: () => boolean; release: () => void; dispose: () => Promise<void>};

    /** The built chunk carrying the Italian catalogue. Build chunks are named by content hash, so it
     *  is found by content: the one file holding the catalogue's own Welcome description, read from
     *  `it.json` rather than copied here, so rewording the translation cannot strand the lookup. */
    function italianCatalogueChunk(): string {
        const catalogue = JSON.parse(readFileSync(new URL('../src/lib/i18n/it.json', import.meta.url), 'utf8')) as {onboarding?: {welcome?: {description?: unknown}}};
        const description = catalogue.onboarding?.welcome?.description;
        if (typeof description !== 'string' || !description) throw new Error('it.json has no onboarding.welcome.description: pick another Italian-only marker for the catalogue chunk');
        const marker = JSON.stringify(description);
        const chunksDir = new URL('../build/_app/immutable/chunks/', import.meta.url);
        const holders = readdirSync(chunksDir).filter((file) => file.endsWith('.js') && readFileSync(new URL(file, chunksDir), 'utf8').includes(marker));
        if (holders.length !== 1) throw new Error(`Expected exactly one built chunk holding the Italian catalogue under ${chunksDir.pathname}, found ${holders.length} (${holders.join(', ') || 'none'}): is the build current?`);
        return holders[0];
    }

    /** Hold the Italian catalogue chunk at the network until released. svelte-i18n 4 reports a
     *  dictionary as loading only while it is still in flight after `loadingDelay` (200 ms), so a held
     *  chunk keeps that state on screen for as long as the spec needs to observe it: the slow path,
     *  without a clock. Resolves to plain functions, never to a pending promise, which the caller's
     *  `await` would adopt and wait on. */
    async function holdItalianCatalogue(page: Page): Promise<HeldChunk> {
        const url = `**/_app/immutable/chunks/${italianCatalogueChunk()}`;
        let held = false;
        let release = () => {};
        const released = new Promise<void>((resolve) => {
            release = resolve;
        });
        const holdChunk: Parameters<Page['route']>[1] = async (route) => {
            held = true;
            await released;
            // Continued untouched, never re-served through route.fulfill: the backend sends this chunk
            // gzip-encoded, and a rewritten body blanked the page during the triage.
            await route.continue();
        };
        await page.route(url, holdChunk);
        return {
            isHeld: () => held,
            release: () => release(),
            dispose: async () => {
                release();
                await page.unroute(url, holdChunk);
            },
        };
    }

    test('public-root bootstrap retry keeps the authenticated loading state until its settings request settles', async ({page}) => {
        const userSettingsEndpoint = /\/api\/v1\/settings\/user(?:\?.*)?$/;
        let settingsReads = 0;
        let releaseRetry = () => {};
        const retryGate = new Promise<void>((resolve) => {
            releaseRetry = resolve;
        });
        const handleSettings: Parameters<Page['route']>[1] = async (route) => {
            if (route.request().method() !== 'GET') {
                await route.continue();
                return;
            }
            settingsReads += 1;
            if (settingsReads === 1) {
                await route.fulfill({status: 503, contentType: 'application/json', body: '{"detail":"BOOTSTRAP_BLOCKED_TOKEN"}'});
                return;
            }
            const response = await route.fetch();
            await retryGate;
            await route.fulfill({response});
        };
        await page.route(userSettingsEndpoint, handleSettings);

        try {
            const loggedIn = await page.request.post('/api/v1/auth/login', {
                data: {username: TEST_USER.username, password: TEST_USER.password},
            });
            expect(loggedIn.ok()).toBe(true);

            await page.goto('/');
            await expect(page.getByTestId('onboarding-bootstrap-blocked')).toBeVisible({timeout: 10_000});

            const retryRequest = page.waitForRequest((request) => request.method() === 'GET' && userSettingsEndpoint.test(request.url()), {timeout: 5_000});
            await page.getByTestId('onboarding-bootstrap-retry').click();
            await retryRequest;

            await expect(page.getByTestId('auth-loading')).toBeVisible();
            await expect(page.getByTestId('login-form')).toHaveCount(0);

            releaseRetry();
            await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});
            await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 10_000});
            await expect(page.getByTestId('auth-loading')).toHaveCount(0);
        } finally {
            releaseRetry();
            await page.unroute(userSettingsEndpoint, handleSettings);
        }
    });

    test('1: canonical seeded user lands on the real shell and is never forced through welcome', async ({page}) => {
        await login(page, TEST_USER);
        await expect(page).toHaveURL(/.*dashboard.*/);
        await expect(page.getByTestId('welcome-shell')).toHaveCount(0);
        await expect(page.getByTestId('app-header')).toBeVisible();
    });

    test('onboarding bootstrap failure blocks at root when terminal Welcome cache is missing', async ({page}) => {
        const onboardingEndpoint = /\/api\/v1\/settings\/onboarding(?:\?|$)/;
        const failOnboarding: Parameters<Page['route']>[1] = async (route) => {
            await route.fulfill({
                status: 503,
                contentType: 'application/json',
                body: JSON.stringify({detail: 'ONBOARDING_UNAVAILABLE_TOKEN'}),
            });
        };
        await page.route(onboardingEndpoint, failOnboarding);
        try {
            await login(page, TEST_USER);

            await expect(page).toHaveURL(/^https?:\/\/[^/]+\/(?:[?#].*)?$/, {timeout: 15_000});
            await expect(page.getByTestId('onboarding-bootstrap-blocked')).toBeVisible({timeout: 10_000});
            await expect(page.getByTestId('dashboard-page')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-bootstrap-degraded')).toHaveCount(0);
        } finally {
            await page.unroute(onboardingEndpoint, failOnboarding);
        }
    });

    test('2: a newly registered user is forced to /welcome behind a bare shell', async ({page, request}) => {
        const user = await registerDisposableUser(request, 'shell');
        try {
            await login(page, user);
            await expect(page).toHaveURL(/\/welcome/);
            await expect(page.getByTestId('welcome-shell')).toBeVisible();
            await expect(page.getByTestId('welcome-page')).toBeVisible();
            // Nothing from the ordinary authenticated shell renders behind it — the
            // (app)/+layout.svelte welcome branch mounts only <slot/>, no Sidebar, no
            // Header, no DeferredAppPopups.
            await expect(page.getByTestId('app-header')).toHaveCount(0);
            await expect(page.getByTestId('nav-dashboard')).toHaveCount(0);
            await expect(page.getByTestId('logout-button')).toHaveCount(0);
            await expect(page.getByTestId('deferred-app-popups')).toHaveCount(0);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('3a: completing welcome is one atomic request; refresh and next login do not re-force it', async ({page, request}) => {
        const user = await registerDisposableUser(request, 'complete');
        try {
            await login(page, user);
            await expect(page.getByTestId('welcome-shell')).toBeVisible();
            await expect(page.getByTestId('welcome-form')).toBeVisible({timeout: 10_000});

            await selectWelcomeLocale(page, 'it');

            const progress = await page.request.get('/api/v1/settings/onboarding');
            expect(progress.ok()).toBe(true);
            const flows = (await progress.json()).flows as Array<{flow: string; current_version: number}>;
            const expectedVersion = flows.find((f) => f.flow === 'welcome')?.current_version;
            expect(expectedVersion).toBeGreaterThan(0);

            const completeRequests: Array<Record<string, unknown>> = [];
            const settingsPuts: Array<Record<string, unknown>> = [];
            const recordRequest = (req: Request) => {
                const path = new URL(req.url()).pathname;
                if (req.method() === 'POST' && path === '/api/v1/settings/onboarding/welcome/complete') completeRequests.push(req.postDataJSON());
                if (req.method() === 'PUT' && path === '/api/v1/settings/user') settingsPuts.push(req.postDataJSON());
            };
            page.on('request', recordRequest);
            try {
                await page.getByTestId('welcome-continue').click();
                await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});
                await expectLocaleState(page, 'it');
                const scene = page.getByTestId('onboarding-intro-scene');
                await expect(scene).toHaveAttribute('data-state', 'intro-scene', {timeout: 10_000});
                const phrase = page.getByTestId('onboarding-intro-phrase');
                await expect(phrase).toBeVisible();
                await expect(phrase).toHaveText(/\S/);
                await expect(scene).not.toContainText('common.next');
                await expect(scene).not.toContainText(/onboarding\.[A-Za-z0-9_.-]+/);
            } finally {
                page.off('request', recordRequest);
            }

            expect(completeRequests, 'Exactly one atomic welcome-complete request').toHaveLength(1);
            expect(Object.keys(completeRequests[0]).sort()).toEqual(['expected_version', 'welcome_settings']);
            expect(completeRequests[0]).toMatchObject({expected_version: expectedVersion});
            const welcomeSettings = completeRequests[0].welcome_settings as Record<string, unknown>;
            expect(Object.keys(welcomeSettings).sort()).toEqual(['avatar_url', 'base_currency', 'language']);
            expect(welcomeSettings.language).toBe('it');
            expect(settingsPuts, 'Completing welcome must not additionally PUT /settings/user').toEqual([]);

            // Welcome applies the chosen locale before it exposes the Dashboard scene.
            // Read state, never translated copy; the literal-key check catches a catalogue
            // race without coupling the assertion to Italian wording.
            await expect(page.getByTestId('welcome-shell')).toHaveCount(0);

            await skipIntroScene(page);

            // Terminal: a reload does not re-force welcome.
            await page.reload();
            await page.waitForLoadState('domcontentloaded');
            await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
            await expect(page.getByTestId('welcome-shell')).toHaveCount(0, {timeout: 15_000});
            await expect(page.getByTestId('app-header')).toBeVisible({timeout: 15_000});
            await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);

            // Terminal across a fresh session too.
            await logout(page);
            await login(page, user);
            await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/);
            await expect(page.getByTestId('welcome-shell')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('3b: permanently skipping welcome survives a refresh and the next login', async ({page, request}) => {
        const user = await registerDisposableUser(request, 'skip');
        try {
            await login(page, user);
            await expect(page.getByTestId('welcome-shell')).toBeVisible();
            await expect(page.getByTestId('welcome-form')).toBeVisible({timeout: 10_000});

            const progress = await page.request.get('/api/v1/settings/onboarding');
            expect(progress.ok()).toBe(true);
            const flows = (await progress.json()).flows as Array<{flow: string; current_version: number}>;
            const expectedVersion = flows.find((f) => f.flow === 'welcome')?.current_version;
            expect(expectedVersion).toBeGreaterThan(0);

            const skipRequests: Array<Record<string, unknown>> = [];
            const settingsPuts: Array<Record<string, unknown>> = [];
            const recordRequest = (req: Request) => {
                const path = new URL(req.url()).pathname;
                if (req.method() === 'POST' && path === '/api/v1/settings/onboarding/welcome/skip') skipRequests.push(req.postDataJSON());
                if (req.method() === 'PUT' && path === '/api/v1/settings/user') settingsPuts.push(req.postDataJSON());
            };
            page.on('request', recordRequest);
            try {
                await page.getByTestId('welcome-skip').click();
                await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});
                await expect(page.getByTestId('onboarding-intro-scene')).toHaveAttribute('data-state', 'intro-scene', {timeout: 10_000});
            } finally {
                page.off('request', recordRequest);
            }
            expect(skipRequests, 'Exactly one atomic welcome-skip request').toHaveLength(1);
            expect(skipRequests[0]).toEqual({expected_version: expectedVersion});
            expect(settingsPuts, 'Skipping welcome must not write staged settings separately').toEqual([]);
            await expect(page.getByTestId('welcome-shell')).toHaveCount(0);

            await skipIntroScene(page);

            await page.reload();
            await page.waitForLoadState('domcontentloaded');
            await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
            await expect(page.getByTestId('welcome-shell')).toHaveCount(0, {timeout: 15_000});
            await expect(page.getByTestId('app-header')).toBeVisible({timeout: 15_000});
            await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);

            await logout(page);
            await login(page, user);
            await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/);
            await expect(page.getByTestId('welcome-shell')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    // A language picked in Welcome is only previewed: `locale.set`, nothing persisted, so that Skip can
    // restore the saved one. svelte-i18n 4 reports a catalogue still in flight after its 200 ms
    // `loadingDelay` as loading, and both layouts swapped the whole app for a placeholder on every such
    // report: the app was torn down and rebuilt, the rebuild re-read the persisted language and the
    // Welcome page re-hydrated its draft from the saved settings. The choice was lost, and completing
    // Welcome sent the old language. On an idle localhost the ~250 KB Italian catalogue lands within
    // the delay, so 3a met this only under load; here the catalogue is held until the loading state is
    // on screen, which makes the slow path deterministic instead of a matter of machine speed.
    test('3c: a Welcome language whose catalogue arrives late survives the load: same form, Italian preview, Italian completion', async ({page, request}) => {
        const user = await registerDisposableUser(request, 'latecat');
        let disposeCatalogueHold = async () => {};
        try {
            await login(page, user);
            const form = page.getByTestId('welcome-form');
            await expect(form).toBeVisible({timeout: 10_000});
            // Precondition, verified: the session runs in English, so Italian is a catalogue still to fetch.
            await expectLocaleState(page, 'en');

            // A locator re-resolves on every use and cannot tell a rebuilt form from the original;
            // a handle pins the very node on screen before the load.
            const formBeforeLoad = await form.evaluateHandle((node) => node);
            const italianCatalogue = await holdItalianCatalogue(page);
            disposeCatalogueHold = italianCatalogue.dispose;

            await selectWelcomeLocale(page, 'it');

            // Barrier, green before and after the fix: the slow path really ran. A catalogue that lands
            // within the delay is never reported as loading, and the contract below would pass vacuously.
            await expect.poll(() => italianCatalogue.isHeld(), {message: 'Picking Italian requests its catalogue chunk, and the spec holds it', timeout: 5_000}).toBe(true);
            const localeState = page.locator('[data-i18n-ready]');
            await expect(localeState, 'The held catalogue is reported as loading').toHaveAttribute('data-i18n-ready', 'false', {timeout: 5_000});

            italianCatalogue.release();
            await expect(localeState, 'The catalogue load completes once released').toHaveAttribute('data-i18n-ready', 'true', {timeout: 10_000});

            // Contract. The identity check is soft, so a red reports the teardown and the language it cost together.
            const sameForm = await formBeforeLoad.evaluate((node) => node.isConnected && node === document.querySelector('[data-testid="welcome-form"]'));
            expect.soft(sameForm, 'The Welcome form outlives the catalogue load: the same node, never torn down and rebuilt').toBe(true);
            await expectLocaleState(page, 'it');

            const completeRequests: Array<Record<string, unknown>> = [];
            const recordRequest = (req: Request) => {
                if (req.method() === 'POST' && new URL(req.url()).pathname === '/api/v1/settings/onboarding/welcome/complete') completeRequests.push(req.postDataJSON());
            };
            page.on('request', recordRequest);
            try {
                await page.getByTestId('welcome-continue').click();
                await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});
            } finally {
                page.off('request', recordRequest);
            }
            expect(completeRequests, 'Exactly one atomic welcome-complete request').toHaveLength(1);
            expect((completeRequests[0].welcome_settings as Record<string, unknown>).language, 'Welcome completes with the language picked before the load').toBe('it');
            await expectLocaleState(page, 'it');
        } finally {
            await disposeCatalogueHold();
            await deleteDisposableUser(request, user);
        }
    });

    test('4: a canonical terminal user landing directly on /welcome?returnTo=... with no replay token is redirected to the return target, never stuck on welcome', async ({page}) => {
        await login(page, TEST_USER);
        await expect(page).toHaveURL(/.*dashboard.*/);

        // TEST_USER is grandfathered `completed` on welcome (see this describe block's
        // seeding note) and carries no replay flag, so nothing here is "mid-onboarding".
        // (app)/+layout.svelte deliberately does not redirect while isWelcomeRoute is true
        // (its onboardingRouteReady guard is `isWelcomeRoute || ...`), to avoid racing
        // WelcomePage's own terminal-route effect — it is that effect, reading
        // `returnTo` off the URL, that must own the exit here.
        await page.goto('/welcome?returnTo=%2Fsettings');

        // welcome-shell is (app)/+layout.svelte's synchronous placeholder for any
        // /welcome URL, rendered before WelcomePage's effect has had a chance to run —
        // so it may flash. It must never be the state this test settles on: assert the
        // final destination, not the transient shell.
        await expect(page).toHaveURL(/\/settings/, {timeout: 15_000});
        await expect(page.getByTestId('settings-page')).toBeVisible({timeout: 10_000});
        await expect(page.getByTestId('welcome-page')).toHaveCount(0);
        await expect(page.getByTestId('welcome-shell')).toHaveCount(0);
    });

    test('5: switching from a mid-onboarding account to the canonical account carries no welcome/guide state', async ({page, request}) => {
        const user = await registerDisposableUser(request, 'boundary');
        try {
            await login(page, user);
            await expect(page.getByTestId('welcome-shell')).toBeVisible();
            await expect(page.getByTestId('welcome-form')).toBeVisible({timeout: 10_000});
            // Deliberately mid-onboarding: never completed or skipped for this account —
            // the strongest version of the boundary check, since there is no terminal
            // status at all to accidentally rely on.

            await page.getByTestId('welcome-logout').click();
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 10_000});

            await login(page, TEST_USER);
            await expect(page).not.toHaveURL(/\/welcome/);
            await expect(page.getByTestId('welcome-shell')).toHaveCount(0);
            await expect(page.getByTestId('app-header')).toBeVisible({timeout: 10_000});
            await expect(page.getByTestId('nav-dashboard')).toBeVisible({timeout: 10_000});
        } finally {
            await deleteDisposableUser(request, user);
        }
    });
});
