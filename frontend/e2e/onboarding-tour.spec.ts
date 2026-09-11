/**
 * Onboarding UX Round 1 — real desktop/mobile tour.
 *
 * Every test registers and deletes its own account. New accounts are the only
 * truthful way to exercise pending onboarding without mutating a canonical user's
 * shared settings or progress.
 *
 * MANUAL-ONLY SEAM: Donation/Update popup priority is not activatable in the
 * production E2E build (its debug hook is compiled out). It remains covered by the
 * real DeferredAppPopups component test and the onboarding manual runbook; this spec
 * does not fabricate either popup.
 */

import {expect, test, type APIRequestContext, type Page, type Request} from './fixtures/playwright';
import {login} from './fixtures/auth-helpers';
import {waitForSettled} from './fixtures/app-events';
import {uniqueSuffix} from './fixtures/unique';

test.setTimeout(120_000);

type DisposableUser = {id: number; username: string; email: string; password: string};

const INTRO_STEP_IDS = ['intro.scene', 'intro.dashboard', 'intro.navigation', 'intro.transactions_nav', 'intro.transactions_import', 'intro.brokers_add', 'intro.brokers_currency', 'intro.fx_add', 'intro.fx_pair', 'intro.assets_add', 'intro.assets_config', 'intro.tools', 'intro.settings'] as const;

async function registerDisposableUser(request: APIRequestContext, tag: string): Promise<DisposableUser> {
    const suffix = uniqueSuffix();
    const user = {
        username: `tour_${tag}_${suffix}`,
        email: `tour_${tag}_${suffix}@example.com`,
        password: `Tour9!_${suffix}`,
    };
    const response = await request.post('/api/v1/auth/register', {data: user});
    expect(response.status(), 'Disposable-account registration must be enabled; do not repair global settings in this spec').toBe(201);
    const created = (await response.json()) as {user: {id: number}};
    return {...user, id: created.user.id};
}

async function deleteDisposableUser(request: APIRequestContext, user: DisposableUser): Promise<void> {
    const loggedIn = await request.post('/api/v1/auth/login', {
        data: {username: user.username, password: user.password},
    });
    expect(loggedIn.ok(), 'Cleanup must authenticate as the account it owns').toBe(true);
    expect(((await loggedIn.json()) as {user: {id: number}}).user.id, 'Cleanup must remain scoped to this test user').toBe(user.id);
    const removed = await request.delete('/api/v1/auth/users/me');
    expect(removed.ok(), 'Cleanup must delete the disposable onboarding account').toBe(true);
}

async function selectWelcomeLocale(page: Page, locale: string): Promise<void> {
    const combobox = page.getByTestId('welcome-language').locator('[aria-haspopup="listbox"]');
    await combobox.click();
    await expect(combobox).toHaveAttribute('aria-expanded', 'true');
    await expect(combobox).toHaveAttribute('aria-controls', /.+/);
    const listboxId = await combobox.getAttribute('aria-controls');
    if (!listboxId) throw new Error('Welcome language selector did not publish its listbox id');

    // WelcomeForm does not provide SimpleSelect.optionTestId. Its generated,
    // value-bearing option id is the only stable non-translated selector exposed
    // by the control; never select the locale by its localized label or position.
    const targetOptionId = `${listboxId}-option-${encodeURIComponent(locale)}`;
    await combobox.press('Home');
    await expect(combobox).toHaveAttribute('aria-activedescendant', /-option-/);

    // LANGUAGE_OPTIONS contains the four supported locales. Bound keyboard
    // traversal to that public set instead of assuming Italian stays exactly
    // one ArrowDown after English.
    for (let step = 0; step < 4; step += 1) {
        const activeId = await combobox.getAttribute('aria-activedescendant');
        if (activeId === targetOptionId) break;
        if (!activeId) throw new Error('Welcome language selector lost its active descendant while open');
        await combobox.press('ArrowDown');
        await expect(combobox).not.toHaveAttribute('aria-activedescendant', activeId);
    }
    await expect(combobox).toHaveAttribute('aria-activedescendant', targetOptionId);
    await combobox.press('Enter');
    await expect(combobox).toHaveAttribute('aria-expanded', 'false');

    // Reopen through the same keyboard contract to read the selected option's
    // value-bearing id/ARIA state, then leave the control collapsed.
    await combobox.press('ArrowDown');
    await expect(combobox).toHaveAttribute('aria-expanded', 'true');
    await expect(combobox).toHaveAttribute('aria-activedescendant', targetOptionId);
    const selectedOption = page.locator(`[id="${targetOptionId}"][role="option"]`);
    await expect(selectedOption).toHaveAttribute('aria-selected', 'true');
    await combobox.press('Escape');
    await expect(combobox).toHaveAttribute('aria-expanded', 'false');
}

async function expectItalianLocale(page: Page): Promise<void> {
    const localeState = page.locator('[data-i18n-ready]');
    await expect(localeState).toHaveAttribute('lang', 'it');
    await expect(localeState).toHaveAttribute('data-i18n-ready', 'true');
}

async function introReplaySteps(page: Page): Promise<string[]> {
    return page.evaluate(() => {
        const matches: string[] = [];
        for (let index = 0; index < window.sessionStorage.length; index += 1) {
            const key = window.sessionStorage.key(index);
            if (!key?.includes('_onboarding_replay_intro_tour_v')) continue;
            const raw = window.sessionStorage.getItem(key);
            if (!raw) continue;
            try {
                const parsed = JSON.parse(raw) as {stepId?: unknown};
                matches.push(typeof parsed.stepId === 'string' ? parsed.stepId : 'invalid');
            } catch {
                matches.push('invalid');
            }
        }
        return matches.sort();
    });
}

async function expectIntroReplayStep(page: Page, stepId: string): Promise<void> {
    await expect.poll(() => introReplaySteps(page), {timeout: 5_000}).toEqual([stepId]);
}

async function expectNoIntroReplay(page: Page): Promise<void> {
    await expect.poll(() => introReplaySteps(page), {timeout: 5_000}).toEqual([]);
}

async function completeWelcomeInItalian(page: Page) {
    await expect(page).toHaveURL(/\/welcome(?:[/?#]|$)/, {timeout: 15_000});
    await expect(page.getByTestId('welcome-form')).toBeVisible({timeout: 10_000});

    await selectWelcomeLocale(page, 'it');
    const submittedAt = await page.evaluate(() => Date.now());
    await page.getByTestId('welcome-continue').click();

    await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});
    await expectItalianLocale(page);
    const scene = page.getByTestId('onboarding-intro-scene');
    await expect(scene).toHaveAttribute('data-state', 'intro-scene', {timeout: 10_000});
    const phrase = page.getByTestId('onboarding-intro-phrase');
    await expect(phrase).toBeVisible();
    await expect(phrase).toHaveText(/\S/);
    await expect(page.getByTestId('onboarding-intro-start')).toBeVisible();
    await expect(scene).not.toContainText('common.next');
    await expect(scene).not.toContainText(/onboarding\.[A-Za-z0-9_.-]+/);
    return {scene, submittedAt};
}

async function expectRouteReady(page: Page, route: RegExp, rootTestId: string, publishesBusy = true): Promise<void> {
    await expect(page).toHaveURL(route, {timeout: 15_000});
    const root = page.getByTestId(rootTestId);
    await expect(root).toBeVisible({timeout: 15_000});
    if (publishesBusy) await waitForSettled(root, 20_000);
}

async function expectAppShellInert(page: Page, expected: boolean): Promise<void> {
    const appShell = page.getByTestId('app-shell');
    await expect(appShell).toHaveAttribute('data-guide-inert', expected ? 'true' : 'false');
    await expect(appShell).toHaveJSProperty('inert', expected);
}

async function expectAnchoredIntroStep(page: Page, stepId: string, targetTestId?: string) {
    const coachmark = page.getByTestId('onboarding-coachmark');
    await expect(coachmark).toHaveAttribute('data-step-id', stepId, {timeout: 15_000});
    await expect(coachmark).toHaveAttribute('data-guide-state', 'anchored', {timeout: 15_000});
    await expect(page.getByTestId('onboarding-coachmark-backdrop')).toBeVisible({timeout: 15_000});
    await expectAppShellInert(page, true);
    await expectItalianLocale(page);
    await expect(coachmark).not.toContainText('common.next');
    await expect(coachmark).not.toContainText(/onboarding\.[A-Za-z0-9_.-]+/);
    if (targetTestId) {
        await expect(page.getByTestId(targetTestId)).toHaveAttribute('aria-describedby', 'onboarding-coachmark-description', {timeout: 10_000});
    }
    return coachmark;
}

async function nextIntroStep(page: Page): Promise<void> {
    const next = page.getByTestId('onboarding-coachmark-next');
    await expect(next).toBeVisible();
    await next.click();
}

async function logoutFromResponsiveShell(page: Page, mobile: boolean): Promise<void> {
    if (mobile) {
        await page.getByTestId('mobile-menu-toggle').click();
        await expect(page.getByTestId('app-header')).toHaveAttribute('data-sidebar-open', 'true');
    }
    await page.getByTestId('logout-button').click();
    await expect(page.getByTestId('login-page')).toBeVisible({timeout: 10_000});
}

test.describe('Onboarding intro tour', () => {
    test('manual Start follows the semantic desktop/mobile route and non-writing preview order', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, `walk_${testInfo.project.name}`);
        try {
            await login(page, user);
            const {scene} = await completeWelcomeInItalian(page);
            const observed: string[] = ['intro.scene'];
            const financialWrites: string[] = [];
            const finishRequests: Array<Record<string, unknown>> = [];
            const recordFinancialWrite = (req: Request) => {
                if (req.method() !== 'POST') return;
                const path = new URL(req.url()).pathname;
                if (['/api/v1/brokers', '/api/v1/assets', '/api/v1/fx/providers/routes', '/api/v1/transactions/commit'].includes(path)) {
                    financialWrites.push(`${req.method()} ${path}`);
                }
                if (path === '/api/v1/settings/onboarding/intro_tour/complete') {
                    finishRequests.push(req.postDataJSON());
                }
            };
            page.on('request', recordFinancialWrite);

            try {
                await page.getByTestId('onboarding-intro-start').click();
                await expect(scene).toHaveCount(0, {timeout: 5_000});
                await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
                await expectAnchoredIntroStep(page, 'intro.dashboard', 'dashboard-page');
                observed.push('intro.dashboard');

                // Dashboard explanation precedes navigation, and neither explanatory
                // step navigates away from Dashboard.
                await nextIntroStep(page);
                await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
                const navigationTarget = testInfo.project.name === 'mobile' ? 'mobile-menu-toggle' : 'sidebar-collapse-toggle';
                await expectAnchoredIntroStep(page, 'intro.navigation', navigationTarget);
                observed.push('intro.navigation');

                await nextIntroStep(page);
                await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
                if (testInfo.project.name === 'mobile') {
                    await expect(page.getByTestId('app-header')).toHaveAttribute('data-sidebar-open', 'true');
                }
                await expectAnchoredIntroStep(page, 'intro.transactions_nav', 'nav-transactions');
                observed.push('intro.transactions_nav');

                // The highlighted navigation item is explanatory only. The guide's Next
                // action is the sole operation that changes route.
                await nextIntroStep(page);
                await expectRouteReady(page, /\/transactions(?:[/?#]|$)/, 'transactions-page');
                if (testInfo.project.name === 'mobile') {
                    await expect(page.getByTestId('app-header')).toHaveAttribute('data-sidebar-open', 'false');
                }
                await expectAnchoredIntroStep(page, 'intro.transactions_import', 'tx-import-button');
                observed.push('intro.transactions_import');

                await nextIntroStep(page);
                await expectRouteReady(page, /\/brokers(?:[/?#]|$)/, 'brokers-page');
                await expect(page.getByTestId('add-broker-button')).toBeVisible();
                // SEAM: on an empty account the empty-state Add button registers the same
                // semantic anchor after the header button, but has no stable testid. The
                // coachmark's anchored state proves resolution without guessing a selector.
                await expectAnchoredIntroStep(page, 'intro.brokers_add');
                observed.push('intro.brokers_add');

                // The preview hosts do not yet publish a dedicated
                // data-tour-preview state. Use the observable contract they do expose:
                // the owned modal/field is present, its write CTA is absent, and the
                // request ledger below stays empty across all three previews.
                await nextIntroStep(page);
                await expect(page).toHaveURL(/\/brokers(?:[/?#]|$)/);
                await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 10_000});
                await expectAnchoredIntroStep(page, 'intro.brokers_currency', 'broker-tour-currency');
                await expect(page.getByTestId('broker-form-submit')).toHaveCount(0);
                observed.push('intro.brokers_currency');

                await nextIntroStep(page);
                await expectRouteReady(page, /\/fx(?:[/?#]|$)/, 'fx-page');
                await expect(page.getByTestId('broker-modal')).toHaveCount(0);
                await expect(page.getByTestId('fx-add-pair-button')).toBeVisible();
                // Same duplicate semantic-anchor seam as the empty Brokers page above.
                await expectAnchoredIntroStep(page, 'intro.fx_add');
                observed.push('intro.fx_add');

                await nextIntroStep(page);
                await expect(page).toHaveURL(/\/fx(?:[/?#]|$)/);
                await expect(page.getByTestId('fx-add-pair-modal')).toBeVisible({timeout: 10_000});
                await expectAnchoredIntroStep(page, 'intro.fx_pair', 'fx-tour-pair-selectors');
                await expect(page.getByTestId('fx-add-pair-base')).toBeVisible();
                await expect(page.getByTestId('fx-add-pair-quote')).toBeVisible();
                await expect(page.getByTestId('fx-add-pair-save')).toHaveCount(0);
                observed.push('intro.fx_pair');

                await nextIntroStep(page);
                await expectRouteReady(page, /\/assets(?:[/?#]|$)/, 'assets-page');
                await expect(page.getByTestId('fx-add-pair-modal')).toHaveCount(0);
                await expect(page.getByTestId('assets-add-button')).toBeVisible();
                // Same duplicate semantic-anchor seam as Brokers/FX empty states.
                await expectAnchoredIntroStep(page, 'intro.assets_add');
                observed.push('intro.assets_add');

                await nextIntroStep(page);
                await expect(page).toHaveURL(/\/assets(?:[/?#]|$)/);
                await expect(page.getByTestId('asset-modal')).toBeVisible({timeout: 10_000});
                await expectAnchoredIntroStep(page, 'intro.assets_config', 'asset-modal-currency-group');
                const providerHeader = page.getByTestId('asset-modal-provider-header');
                await expect(providerHeader).toBeVisible();
                await expect(providerHeader).toHaveAttribute('data-expanded', 'true');
                const noProvider = page.getByTestId('asset-modal-no-provider');
                await expect(noProvider).toBeVisible();
                await expect(noProvider).not.toBeChecked();
                await expect(page.getByTestId('provider-code-select-button')).toBeEnabled();
                await expect(page.getByTestId('asset-modal-save')).toHaveCount(0);
                observed.push('intro.assets_config');

                await nextIntroStep(page);
                await expectRouteReady(page, /\/tools(?:[/?#]|$)/, 'tools-hub');
                await expect(page.getByTestId('asset-modal')).toHaveCount(0);
                await expectAnchoredIntroStep(page, 'intro.tools', 'tools-hub');
                observed.push('intro.tools');

                await nextIntroStep(page);
                await expectRouteReady(page, /\/settings(?:[/?#]|$)/, 'settings-page', false);
                const settingsCoachmark = await expectAnchoredIntroStep(page, 'intro.settings', 'onboarding-replay-section');
                observed.push('intro.settings');
                expect(observed).toEqual(INTRO_STEP_IDS);

                await nextIntroStep(page);
                await expect(settingsCoachmark).toHaveCount(0, {timeout: 10_000});
                await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
                await expectAppShellInert(page, false);
                await expectItalianLocale(page);
                expect(finishRequests, 'Finish must issue exactly one intro_tour completion').toHaveLength(1);
                expect(Object.keys(finishRequests[0]).sort()).toEqual(['expected_version']);
                expect(finishRequests[0].expected_version).toEqual(expect.any(Number));
                await expectNoIntroReplay(page);
                expect(financialWrites, 'Tour preview surfaces must not persist broker, FX, asset, or transaction data').toEqual([]);
            } finally {
                page.off('request', recordFinancialWrite);
            }
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('the published ten-second scene deadline auto-starts exactly once', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, `auto_${testInfo.project.name}`);
        try {
            await login(page, user);
            const {scene, submittedAt} = await completeWelcomeInItalian(page);
            await expectIntroReplayStep(page, 'intro.scene');
            await expect(scene).toHaveAttribute('data-auto-start-at', /^\d+$/, {timeout: 5_000});
            const rawDeadline = await scene.getAttribute('data-auto-start-at');
            if (!rawDeadline || !/^\d+$/.test(rawDeadline)) {
                throw new Error(`intro scene must publish a numeric auto-start deadline, received ${String(rawDeadline)}`);
            }
            const deadline = Number(rawDeadline);

            const observedAt = await page.evaluate(() => Date.now());
            expect(deadline - submittedAt).toBeGreaterThanOrEqual(10_000);
            expect(deadline).toBeGreaterThan(observedAt);
            expect(deadline - observedAt).toBeLessThanOrEqual(10_000);

            // The phrase sequence advances on its own before the same published
            // deadline starts the tour; this is a retrying state assertion, not a
            // clock sleep.
            await expect(scene).toHaveAttribute('data-phase', 'tour', {timeout: 9_000});

            const coachmark = page.getByTestId('onboarding-coachmark');
            await expect
                .poll(
                    async () => {
                        if ((await scene.count()) > 0) return 'intro.scene';
                        return (await coachmark.getAttribute('data-step-id')) ?? 'missing';
                    },
                    {timeout: Math.max(5_000, deadline - Date.now() + 5_000)},
                )
                .toBe('intro.dashboard');

            const transitionObservedAt = await page.evaluate(() => Date.now());
            expect(transitionObservedAt).toBeGreaterThanOrEqual(deadline);
            expect(transitionObservedAt - deadline).toBeLessThan(5_000);
            await expect(scene).toHaveCount(0);
            await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
            await expectAnchoredIntroStep(page, 'intro.dashboard', 'dashboard-page');
            await expectIntroReplayStep(page, 'intro.dashboard');

            // End this owned flow terminally; a single visible coachmark after the
            // deadline is the E2E-observable outcome of the one-shot transition.
            await page.getByTestId('onboarding-coachmark-skip').click();
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            await expectAppShellInert(page, false);
            await expectNoIntroReplay(page);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });

    test('X suspends the semantic step across reload/login and permanent Skip prevents restart', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, `resume_${testInfo.project.name}`);
        const mobile = testInfo.project.name === 'mobile';
        try {
            await login(page, user);
            await completeWelcomeInItalian(page);
            await page.getByTestId('onboarding-intro-start').click();
            await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
            await expectAnchoredIntroStep(page, 'intro.dashboard', 'dashboard-page');
            await nextIntroStep(page);
            const coachmark = await expectAnchoredIntroStep(page, 'intro.navigation', mobile ? 'mobile-menu-toggle' : 'sidebar-collapse-toggle');

            await page.getByTestId('onboarding-coachmark-close').click();
            await expect(page.getByTestId('dashboard-page')).toBeVisible();
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            await expectAppShellInert(page, false);
            await expect(page.getByTestId('app-header')).toHaveAttribute('data-guide-active', 'false');
            await expectIntroReplayStep(page, 'intro.navigation');

            // A fresh runtime consumes the retained replay token and resumes the exact
            // semantic step, rather than restarting at intro.scene or advancing by index.
            await page.reload();
            await page.waitForLoadState('domcontentloaded');
            await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
            await expectAnchoredIntroStep(page, 'intro.navigation', mobile ? 'mobile-menu-toggle' : 'sidebar-collapse-toggle');
            await expectIntroReplayStep(page, 'intro.navigation');

            await page.getByTestId('onboarding-coachmark-close').click();
            await expect(coachmark).toHaveCount(0, {timeout: 5_000});
            await expectAppShellInert(page, false);
            await expectIntroReplayStep(page, 'intro.navigation');
            await logoutFromResponsiveShell(page, mobile);
            await login(page, user);
            await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
            await expectAnchoredIntroStep(page, 'intro.navigation', mobile ? 'mobile-menu-toggle' : 'sidebar-collapse-toggle');
            await expectIntroReplayStep(page, 'intro.navigation');

            const skipRequests: string[] = [];
            const recordSkip = (req: Request) => {
                if (req.method() === 'POST' && new URL(req.url()).pathname === '/api/v1/settings/onboarding/intro_tour/skip') {
                    skipRequests.push(req.url());
                }
            };
            page.on('request', recordSkip);
            try {
                await page.getByTestId('onboarding-coachmark-skip').click();
                await expect(page.getByTestId('dashboard-page')).toBeVisible();
                await expect(coachmark).toHaveCount(0, {timeout: 5_000});
                await expectAppShellInert(page, false);
                await expect(page.getByTestId('app-header')).toHaveAttribute('data-guide-active', 'false');
            } finally {
                page.off('request', recordSkip);
            }
            expect(skipRequests, 'Permanent Skip must issue exactly one intro_tour transition').toHaveLength(1);
            await expectNoIntroReplay(page);

            await logoutFromResponsiveShell(page, mobile);
            await login(page, user);
            await expectRouteReady(page, /\/dashboard(?:[/?#]|$)/, 'dashboard-page');
            await expectItalianLocale(page);
            await expect(page.getByTestId('app-header')).toBeVisible();
            await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);
            await expectNoIntroReplay(page);
        } finally {
            await deleteDisposableUser(request, user);
        }
    });
});
