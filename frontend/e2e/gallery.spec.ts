/**
 * Gallery Screenshot Generator
 *
 * Generates consistent screenshots for mkdocs documentation.
 * NOT included in normal test runs - run separately with:
 *   ./dev.py mkdocs gallery
 *
 * Screenshots saved to: mkdocs_src/docs/gallery/{desktop|mobile}/{lang}/{theme}/...
 *
 * Prerequisites:
 *   - Run `./dev.py db populate --force` before generating gallery
 *   - This ensures brokers with icons exist for realistic screenshots
 */
import {expect, type Locator, type Page, test} from './fixtures/playwright';
import {login, logout, navigateTo, openMobileMenu, setLanguage} from './fixtures/auth-helpers';
import {waitForSettled} from './fixtures/app-events';
import {type Language, SUPPORTED_LANGUAGES, TEST_ADMIN, TEST_EMPTY} from './fixtures/test-users';
import {goToFxDetailPage, goToFxPage, openAddPairModal} from './fx/fx-helpers';
import {goToAssetsPage, navigateToAssetByName} from './assets/assets-helpers';
import * as path from 'path';
import * as fs from 'fs';
import {fileURLToPath} from 'url';

// ES module compatibility for __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GALLERY_ROOT = path.join(__dirname, '../../mkdocs_src/docs/gallery');
const THEMES = ['light', 'dark'] as const;
type Theme = (typeof THEMES)[number];

async function clickRowAction(page: Page, scope: Page | Locator, actionId: string, index = 0): Promise<void> {
    const actionsButton = scope.getByTestId(/^row-actions-/).nth(index);
    await expect(actionsButton).toBeVisible({timeout: 5_000});
    await actionsButton.scrollIntoViewIfNeeded();
    await actionsButton.click();
    await page.getByTestId(`context-menu-action-${actionId}`).click();
}

/**
 * Open the grouped SignalTreeSelect (indicators category), expand a family group and
 * pick an option. Options render only while their group is expanded (or the search box
 * is filled); open() auto-expands the FIRST family, so the group click is conditional.
 * Assert-loud on purpose: the indicator select appears only after the backend signal
 * catalog has loaded, so a missing button is a real failure, not a skip.
 */
async function selectIndicatorFromTree(page: Page, groupKey: string, optionValue: string): Promise<void> {
    const selectButton = page.getByTestId('signals-indicator-select-button');
    await expect(selectButton).toBeVisible({timeout: 15_000});
    await selectButton.click();
    // open() auto-expands the FIRST family group — click only when this one is collapsed
    const group = page.getByTestId(`signal-tree-group-${groupKey}`);
    await expect(group).toBeVisible({timeout: 3_000});
    if ((await group.getAttribute('aria-expanded')) !== 'true') {
        await group.click();
        await expect(group).toHaveAttribute('aria-expanded', 'true', {timeout: 3_000});
    }
    const option = page.getByTestId(`signal-tree-option-${optionValue}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
}

/** Wait until every configured signal card has finished its backend computation. */
async function waitForSignalCardsSettled(page: Page, timeout = 30_000): Promise<void> {
    await expect(page.getByTestId('asset-detail-signals-panel').getByTestId('signal-loading')).toHaveCount(0, {timeout});
}

/**
 * Forget persisted chart settings (signal configs live in user-scoped localStorage).
 * Call at the START of a combo, before navigation: the next full page load re-hydrates
 * an empty store, so each lang/theme iteration starts with no signals configured and
 * cards never accumulate across combos.
 */
async function resetChartSettings(page: Page): Promise<void> {
    await page.evaluate(() => {
        for (const key of Object.keys(localStorage)) {
            if (key.endsWith('_chartSettingsStore')) localStorage.removeItem(key);
        }
    });
}

function ensureDir(dir: string) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, {recursive: true});
    }
}

function getGalleryPath(viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, category: string): string {
    return path.join(GALLERY_ROOT, viewport, lang, theme, category);
}

/**
 * Freeze all CSS animations at 10% for consistent screenshots.
 * This ensures the animated background is always at the same state.
 */
async function freezeAnimations(page: Page) {
    await page.addStyleTag({
        content: `
            *, *::before, *::after {
                animation-play-state: paused !important;
                animation-delay: -0.1s !important;
                transition-duration: 0s !important;
            }
        `,
    });
}

/**
 * Set the application theme (light/dark)
 */
async function setTheme(page: Page, theme: Theme) {
    const currentTheme = await page.evaluate(() => {
        return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    });

    if (currentTheme !== theme) {
        await page.getByTestId('theme-toggle').click();
        await page.waitForTimeout(100); // Let theme transition complete
    }
}

/**
 * Wait until all pending network requests to the backend API have settled.
 * Uses networkidle + a small buffer to handle late-arriving responses.
 */
async function waitForNetworkSettled(page: Page) {
    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
    await page.waitForTimeout(200);
}

/**
 * Wait until the app splash screen (logo + spinner) has been removed.
 * The splash lives in app.html as #app-splash and is removed once i18n loads.
 */
async function waitForSplashGone(page: Page) {
    await page.waitForFunction(() => !document.getElementById('app-splash'), {timeout: 10_000}).catch(() => {});
}

async function screenshot(page: Page, viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, category: string, name: string) {
    await waitForSplashGone(page);
    await waitForNetworkSettled(page);
    const dir = getGalleryPath(viewport, lang, theme, category);
    ensureDir(dir);
    await page.screenshot({
        path: path.join(dir, `${name}.png`),
        fullPage: false,
    });
    console.log(`  📸 ${viewport}/${lang}/${theme}/${category}/${name}.png`);
}

// Helper to run for all languages and themes
async function forEachLanguageAndTheme(page: Page, callback: (lang: Language, theme: Theme) => Promise<void>) {
    for (const lang of SUPPORTED_LANGUAGES) {
        await setLanguage(page, lang);
        for (const theme of THEMES) {
            await setTheme(page, theme);
            await callback(lang, theme);
        }
    }
}

// Determine viewport from project name
function getViewport(testInfo: any): 'desktop' | 'mobile' {
    return testInfo.project.name === 'mobile' ? 'mobile' : 'desktop';
}

test.describe('Gallery Screenshots', () => {
    // Gallery tests iterate over 4 languages × 2 themes = 8 screenshots per test
    // Some tests also navigate (broker detail, import modal) so need extra time
    // Bumped from 180s: CI runs on a 4-vCPU public runner with --workers matched
    // to CPU count, but transient contention (backend workers, mkdocs build,
    // node overhead) still warrants a bit more default headroom.
    test.setTimeout(240_000); // 4 minutes per test (default; heavy tests override above)

    // Each gallery test is independent (logs in fresh, navigates, screenshots).
    // Run in parallel across workers for faster generation.
    test.describe.configure({mode: 'parallel'});

    test.describe('Auth Pages', () => {
        test('login page - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await freezeAnimations(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.waitForTimeout(100);
                await screenshot(page, viewport, lang, theme, 'auth', '01-login');
            });
        });

        test('register modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await freezeAnimations(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: 3000});
                await page.getByTestId('goto-register').click();
                await expect(page.getByTestId('register-modal')).toBeVisible({timeout: 3000});
                await page.waitForTimeout(200);
                await screenshot(page, viewport, lang, theme, 'auth', '02-register-empty');

                // Go back to login for next iteration
                await page.getByTestId('goto-login').click();
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: 3000});
            });
        });

        test('register with password strength - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});
            await freezeAnimations(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: 3000});
                await page.getByTestId('goto-register').click();
                await expect(page.getByTestId('register-modal')).toBeVisible({timeout: 3000});

                // Fill form with sample data to show password strength
                await page.getByTestId('register-username').fill('demo_user');
                await page.getByTestId('register-email').fill('demo@example.com');
                // Find password input within register modal
                await page.getByTestId('register-modal').locator('input[type="password"]').first().fill('MyStr0ng!Pass');
                await page.waitForTimeout(500); // Let password strength meter update

                await screenshot(page, viewport, lang, theme, 'auth', '03-register-filled');

                // Go back to login for next iteration
                await page.getByTestId('goto-login').click();
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: 3000});
            });
        });

        test('update available modal (mocked release) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            // Deterministic mock: seed the 24h-throttled update-check cache with a fake
            // newer release BEFORE the app boots. The admin layout probe
            // (checkForNewerRelease) then reads the fresh cache instead of fetching GitHub,
            // and prompts. addInitScript re-runs on every full page load, so each reload
            // re-seeds a fresh cache and the modal reappears.
            await page.addInitScript(() => {
                localStorage.setItem(
                    'librefolio-update-check',
                    JSON.stringify({
                        checkedAt: Date.now(),
                        latest: {
                            version: '99.9.0',
                            url: 'https://github.com/Librefolio/LibreFolio/releases/tag/v99.9.0',
                            name: 'v99.9.0',
                        },
                    }),
                );
            });
            // The prompt is now double-gated: GitHub release (mocked via the seeded cache
            // above) AND the GHCR image manifest. Intercept the manifest HEAD too, or the
            // 404 for the fake 99.9.0 tag silences the prompt (the gate working as designed).
            await page.route('**/ghcr.io/v2/**/manifests/**', (route) => route.fulfill({status: 200}));

            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // The modal backdrop blocks the header selectors, so language/theme are
                    // seeded into localStorage (read by i18n + theme boot) instead of clicked.
                    await page.evaluate(
                        ([l, t]) => {
                            localStorage.setItem('librefolio-locale', l);
                            localStorage.setItem('librefolio-theme', t);
                        },
                        [lang, theme] as [string, string],
                    );
                    // Full reload → layout auth check → cached probe → prompt (once per load)
                    await page.reload();
                    await page.waitForSelector('html[data-i18n-ready="true"]', {timeout: 15_000});
                    const modal = page.getByTestId('update-available-modal');
                    await expect(modal).toBeVisible({timeout: 20_000});
                    await expect(page.locator('html')).toHaveAttribute('lang', lang);
                    await expect(page.locator('html')).toHaveClass(new RegExp(`\\b${theme}\\b`));
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'auth', 'update-available-modal');
                }
            }
        });
    });

    function parseLocalDateString(s: string): Date {
        const [year, month, day] = s.split('-').map(Number);
        return new Date(year, month - 1, day);
    }

    function getLocalDateString(d: Date): string {
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function shiftDatesToToday(obj: any): any {
        const datePattern = /^\d{4}-\d{2}-\d{2}$/;
        let maxDateStr: string | null = null;

        function findMaxDate(val: any) {
            if (typeof val === 'string' && datePattern.test(val)) {
                if (!maxDateStr || val > maxDateStr) {
                    maxDateStr = val;
                }
            } else if (Array.isArray(val)) {
                for (const item of val) findMaxDate(item);
            } else if (val && typeof val === 'object') {
                for (const key of Object.keys(val)) findMaxDate(val[key]);
            }
        }
        findMaxDate(obj);

        if (!maxDateStr) return obj;

        const today = new Date();
        const maxDate = parseLocalDateString(maxDateStr);

        today.setHours(0, 0, 0, 0);
        maxDate.setHours(0, 0, 0, 0);

        const diffTime = today.getTime() - maxDate.getTime();
        const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
        if (diffDays === 0) return obj;

        function shift(val: any): any {
            if (typeof val === 'string' && datePattern.test(val)) {
                const d = parseLocalDateString(val);
                d.setDate(d.getDate() + diffDays);
                return getLocalDateString(d);
            } else if (Array.isArray(val)) {
                return val.map(shift);
            } else if (val && typeof val === 'object') {
                const newObj: any = {};
                for (const key of Object.keys(val)) {
                    newObj[key] = shift(val[key]);
                }
                return newObj;
            }
            return val;
        }

        return shift(obj);
    }

    /**
     * The captured dashboard-report.json is a REAL user snapshot. If it stops validating
     * against the current report schema (zodios rejects the whole response and the
     * dashboard renders zeroed KPIs), do NOT patch or delete blocks to make it pass —
     * the snapshot must be RE-CAPTURED from a real backend by the user (see the comment
     * in the docs/testing guides). A loud failure beats a silently wrong screenshot.
     */

    async function setupDashboardMockReport(page: Page) {
        const mockDataPath = path.join(__dirname, 'dashboard-report.json');
        if (fs.existsSync(mockDataPath)) {
            try {
                const rawMockData = JSON.parse(fs.readFileSync(mockDataPath, 'utf8'));
                const adjustedMockData = shiftDatesToToday(rawMockData);
                // NOTE: no sanitizing — if the snapshot no longer validates, the shots
                // must fail loudly until the fixture is re-captured from a real backend.
                await page.route('**/api/v1/portfolio/report', async (route) => {
                    const postData = route.request().postDataJSON?.() as {include_positions_contribution?: boolean} | undefined;
                    if (postData?.include_positions_contribution) {
                        const liveResponse = await route.fetch();
                        const liveData = await liveResponse.json();
                        await route.fulfill({
                            status: liveResponse.status(),
                            contentType: 'application/json',
                            body: JSON.stringify({
                                ...adjustedMockData,
                                positions_contribution: liveData.positions_contribution ?? null,
                            }),
                        });
                        return;
                    }
                    await route.fulfill({
                        status: 200,
                        contentType: 'application/json',
                        body: JSON.stringify(adjustedMockData),
                    });
                });
            } catch (err) {
                console.error('Failed to setup mock portfolio report:', err);
            }
        }
    }

    async function selectMaxDateRange(page: Page) {
        const maxBtn = page.getByTestId('date-preset-max');
        const y2Btn = page.getByTestId('date-preset-2y');
        if (await maxBtn.isVisible({timeout: 500}).catch(() => false)) {
            await maxBtn.click();
        } else if (await y2Btn.isVisible({timeout: 500}).catch(() => false)) {
            await y2Btn.click();
        }
    }

    // Non-FIFO screenshots use a fixed 1-year window (deterministic, not the ambient
    // 3-month sessionStorage default) — FIFO screenshots use selectMaxDateRange() instead
    // so the engine auto-centers on the lots' full lifecycle.
    async function selectOneYearDateRange(page: Page) {
        const y1Btn = page.getByTestId('date-preset-1y');
        if (await y1Btn.isVisible({timeout: 500}).catch(() => false)) {
            await y1Btn.click();
        }
    }

    const POSITIONS_SCREENSHOT_VARIANTS = [
        {
            semantic: 'holdings',
            visual: 'table',
            name: 'positions-holdings-table',
        },
        {
            semantic: 'holdings',
            visual: 'map',
            name: 'positions-holdings-map',
        },
        {
            semantic: 'performance',
            visual: 'table',
            name: 'positions-performance-table',
        },
        {
            semantic: 'performance',
            visual: 'map',
            name: 'positions-performance-map',
        },
    ] as const;

    async function openBrokerCardByName(page: Page, brokerName: string) {
        const brokerCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: brokerName}).first();
        await expect(brokerCard).toBeVisible({timeout: 5_000});
        await brokerCard.scrollIntoViewIfNeeded();
        await brokerCard.click();
        await page.waitForLoadState('networkidle', {timeout: 20_000});
    }

    async function setPositionsView(page: Page, semantic: 'holdings' | 'performance', visual: 'table' | 'map') {
        const semanticButton = page.getByTestId(`positions-toggle-${semantic}`);
        await expect(semanticButton).toBeVisible({timeout: 5_000});
        await semanticButton.scrollIntoViewIfNeeded();
        await semanticButton.click({timeout: 5_000});

        const visualButton = page.getByTestId(`positions-toggle-${visual}`);
        await expect(visualButton).toBeVisible({timeout: 5_000});
        await visualButton.scrollIntoViewIfNeeded();
        await visualButton.click({timeout: 5_000}).catch(async () => {
            await visualButton.click({timeout: 5_000, force: true});
        });

        // Wait for the ACTUAL content root, not networkidle+fixed-sleep. PositionsPanel
        // shows an animate-pulse skeleton while `loading`/`contributionLoading` is true
        // and only swaps to real content once data has arrived — that swap is the true
        // "loaded" signal. The previous networkidle+700ms wasn't always enough for the
        // on-demand `performance` contribution fetch (bug: mobile positions-performance-table
        // gallery screenshot captured the loading skeleton instead of real rows).
        const contentTestId = semantic === 'holdings' ? (visual === 'table' ? 'exposure-table' : 'exposure-treemap') : visual === 'table' ? 'contribution-table' : 'performance-chart';
        await expect(page.getByTestId(contentTestId)).toBeVisible({timeout: 15_000});
        await page.waitForTimeout(400); // settle for chart redraw (treemap/performance-chart use ECharts)
    }

    async function screenshotPositionsVariants(page: Page, viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, category: string) {
        const positionsPanel = page.getByTestId('positions-panel');
        await expect(positionsPanel).toBeVisible({timeout: 5_000});
        await positionsPanel.scrollIntoViewIfNeeded();
        await page.waitForTimeout(300);

        for (const variant of POSITIONS_SCREENSHOT_VARIANTS) {
            await setPositionsView(page, variant.semantic, variant.visual);
            await screenshot(page, viewport, lang, theme, category, variant.name);
        }
    }

    const LOTS_SCREENSHOT_VARIANTS = [
        {testId: 'lot-wac-price-chart', name: 'fifo-lots-wac-chart'},
        {testId: 'lot-gantt-chart', name: 'fifo-lots-gantt-chart'},
        {testId: 'unified-lots-table', name: 'fifo-lots-table'},
        {testId: 'lot-comparison-chart', name: 'fifo-lots-comparison-chart'},
    ] as const;

    async function captureLotsAnalysisScreenshots(page: Page, viewport: 'desktop' | 'mobile', lang: Language, theme: Theme, category: string) {
        const panel = page.getByTestId('lots-analysis-panel');
        await expect(panel).toBeVisible({timeout: 5_000});
        await panel.evaluate((el) => el.scrollIntoView({block: 'start'}));
        await page.waitForTimeout(800);
        await screenshot(page, viewport, lang, theme, category, 'fifo-lots-panel');

        for (const variant of LOTS_SCREENSHOT_VARIANTS) {
            const block = page.getByTestId(variant.testId);
            await expect(block).toBeVisible({timeout: 10_000});
            await block.scrollIntoViewIfNeeded();
            await page.waitForTimeout(300);
            await screenshot(page, viewport, lang, theme, category, variant.name);
        }

        const comparisonReturnToggle = page.getByTestId('lot-comparison-mode-return');
        if (await comparisonReturnToggle.isVisible({timeout: 2_000}).catch(() => false)) {
            await comparisonReturnToggle.click();
            await page.waitForTimeout(300);
            await screenshot(page, viewport, lang, theme, category, 'fifo-lots-comparison-chart-return');
        }

        const table = page.getByTestId('unified-lots-table');
        await clickRowAction(page, table, 'lot-view-details-action');
        await expect(page.getByTestId('lot-custody-modal')).toBeVisible({timeout: 5_000});
        await page.waitForTimeout(300);
        await screenshot(page, viewport, lang, theme, category, 'fifo-lots-custody-modal');
        await page.getByTestId('lot-custody-modal-close').click();
        await expect(page.getByTestId('lot-custody-modal')).toBeHidden({timeout: 5_000});
    }

    test.describe('Dashboard', () => {
        test.beforeEach(async ({page}) => {
            // Use TEST_ADMIN since db populate assigns brokers to admin
            await login(page, TEST_ADMIN);
        });

        test('main dashboard - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);

                // Top-of-dashboard screenshot (scroll=0): KPI cards with real portfolio
                // data — previously only captured empty (dashboard-empty-state test uses
                // TEST_EMPTY). Wait for the KPI row to swap out of its loading skeleton,
                // then give the svelte/motion `tweened()` counters (900ms JS-driven
                // count-up, NOT a CSS animation — freezeAnimations() can't freeze it)
                // time to settle so numbers aren't captured mid-animation.
                const kpiRow = page.getByTestId('kpi-row');
                if (await kpiRow.isVisible({timeout: 5_000}).catch(() => false)) {
                    await expect(kpiRow.getByTestId('kpi-value').first()).toBeVisible({timeout: 10_000});
                    await page.waitForTimeout(1_000);
                }
                await page.evaluate(() => window.scrollTo(0, 0));
                await screenshot(page, viewport, lang, theme, 'dashboard', 'kpi-top');

                // Scroll to the growth chart so it is visible and positioned nicely
                const growthChart = page.getByTestId('growth-chart');
                if (await growthChart.isVisible({timeout: 5000}).catch(() => false)) {
                    await growthChart.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(500); // Give e-charts time to redraw/stabilize
                }

                // Screenshot absolute mode (default)
                await screenshot(page, viewport, lang, theme, 'dashboard', 'main');

                // Toggle and screenshot percentage mode
                const pctToggle = page.getByTestId('growth-toggle-pct');
                if (await pctToggle.isVisible({timeout: 2000}).catch(() => false)) {
                    await pctToggle.click();
                    await page.waitForTimeout(500); // Give e-charts time to redraw
                }
                await screenshot(page, viewport, lang, theme, 'dashboard', 'main-pct');
            });
        });

        test('mobile menu open', async ({page}, testInfo) => {
            if (testInfo.project.name !== 'mobile') {
                test.skip();
                return;
            }
            await setupDashboardMockReport(page);

            const menuToggle = page.getByTestId('mobile-menu-toggle');

            // Take screenshot for each language and theme
            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // Navigate fresh to dashboard for each combo (ensures clean state)
                    await page.goto('/dashboard');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await freezeAnimations(page);

                    // Set language and theme while menu is closed
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.waitForTimeout(100);

                    // Open the menu for screenshot
                    await menuToggle.click();
                    await page.waitForTimeout(400); // Let menu animation complete

                    await screenshot(page, 'mobile', lang, theme, 'dashboard', 'menu-open');
                    // No need to close - we navigate away next iteration
                }
            }
        });

        test('dashboard allocation charts - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);

                // Scroll to the allocation panel
                const allocPanel = page.getByTestId('allocation-panel');
                if (await allocPanel.isVisible({timeout: 5_000}).catch(() => false)) {
                    await allocPanel.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(400);
                }

                const viewNowBtn = page.getByTestId('allocation-view-now');
                const viewHistBtn = page.getByTestId('allocation-view-history');
                const tabTypeBtn = page.getByTestId('allocation-tab-type');
                const tabSectorBtn = page.getByTestId('allocation-tab-sector');
                const tabGeoBtn = page.getByTestId('allocation-tab-geo');

                // 1. TYPE + NOW
                await tabTypeBtn.click();
                await viewNowBtn.click();
                await page.waitForTimeout(500); // Wait for ECharts animation
                await screenshot(page, viewport, lang, theme, 'dashboard', 'allocation-type-now');

                // 2. TYPE + HISTORY
                await viewHistBtn.click();
                await page.waitForLoadState('networkidle', {timeout: 10_000});
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'allocation-type-history');

                // 3. SECTOR + NOW
                await tabSectorBtn.click();
                await viewNowBtn.click();
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'allocation-sector-now');

                // 4. SECTOR + HISTORY
                await viewHistBtn.click();
                await page.waitForLoadState('networkidle', {timeout: 10_000});
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'allocation-sector-history');

                // 5. GEO + NOW
                await tabGeoBtn.click();
                await viewNowBtn.click();
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'allocation-geo-now');

                // 6. GEO + HISTORY
                await viewHistBtn.click();
                await page.waitForLoadState('networkidle', {timeout: 10_000});
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'allocation-geo-history');

                // Scroll back to top so next iteration starts clean
                await page.evaluate(() => window.scrollTo(0, 0));
            });
        });

        test('dashboard positions tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);

                await page.getByTestId('dashboard-tab-posizioni').click();
                await expect(page.getByTestId('dashboard-positions-tab')).toBeVisible({timeout: 5_000});
                await screenshotPositionsVariants(page, viewport, lang, theme, 'dashboard');
            });
        });

        test('dashboard fifo lots panel - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // Deliberately NOT using setupDashboardMockReport here: that fixture is a static,
            // pre-captured snapshot whose holdings[].asset_id values don't reliably correspond
            // to real FIFO lots in a freshly-populated test DB. The other dashboard tests only
            // show aggregate data (growth/allocation), so the mock's staleness doesn't matter
            // there — but "analyze lots" drills into one specific real asset, so we need the
            // live (unmocked) report, exactly like the broker detail equivalent test does.

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                let panelReady = false;

                for (let attempt = 1; attempt <= 2 && !panelReady; attempt++) {
                    await page.goto('/dashboard');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await selectMaxDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await freezeAnimations(page);

                    await page.getByTestId('dashboard-tab-posizioni').click();
                    await expect(page.getByTestId('dashboard-positions-tab')).toBeVisible({timeout: 5_000});
                    await setPositionsView(page, 'holdings', 'table');

                    // Target "Apple Inc." specifically instead of `.first()` (highest
                    // current value). Holdings sort by value desc (ExposureTable.svelte),
                    // which currently puts "RE Loan Milano" first — but that asset has
                    // exactly ONE PriceHistory row ever (see populate_mock_data.py
                    // populate_price_history() loan_price_points), so its WAC/Market
                    // chart renders empty. Apple has the richest lot history in the mock
                    // dataset (buys across 3 brokers/currencies + a partial sell +
                    // dividend + 3-year price history) — a proper FIFO/WAC demo.
                    const positionsPanel = page.getByTestId('positions-panel');
                    const appleRow = positionsPanel.locator('tr[data-row-id]').filter({hasText: 'Apple'}).first();
                    await clickRowAction(page, appleRow, 'analyze-lots');

                    await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5_000});
                    const panelLoading = page.getByTestId('lots-analysis-panel-loading');
                    if (await panelLoading.isVisible({timeout: 1_000}).catch(() => false)) {
                        await panelLoading.waitFor({state: 'hidden', timeout: 15_000}).catch(() => {});
                    }

                    if (
                        await page
                            .getByTestId('login-page')
                            .isVisible({timeout: 1_000})
                            .catch(() => false)
                    ) {
                        if (attempt === 2) {
                            throw new Error('Dashboard FIFO lots panel redirected to login page during capture.');
                        }
                        await login(page, TEST_ADMIN);
                        continue;
                    }

                    const wacChartVisible = await page
                        .getByTestId('lot-wac-price-chart')
                        .isVisible({timeout: 10_000})
                        .catch(() => false);
                    const ganttChartVisible = await page
                        .getByTestId('lot-gantt-chart')
                        .isVisible({timeout: 10_000})
                        .catch(() => false);
                    if (!wacChartVisible || !ganttChartVisible) {
                        if (attempt === 2) {
                            await expect(page.getByTestId('lot-wac-price-chart')).toBeVisible({timeout: 10_000});
                            await expect(page.getByTestId('lot-gantt-chart')).toBeVisible({timeout: 10_000});
                        }
                        continue;
                    }

                    panelReady = true;
                    await captureLotsAnalysisScreenshots(page, viewport, lang, theme, 'dashboard');

                    await page.getByTestId('lots-analysis-panel-close').click();
                    await expect(page.getByTestId('lots-analysis-panel')).toBeHidden({timeout: 5_000});
                }
            });
        });
        test('dashboard transactions tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await setupDashboardMockReport(page);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);

                await page.getByTestId('dashboard-tab-transazioni').click();
                await expect(page.getByTestId('dashboard-transactions-tab')).toBeVisible({timeout: 5_000});
                await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'transactions-tab');
            });
        });

        test('dashboard empty state - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // Logout TEST_ADMIN (from beforeEach) and switch to empty user.
            // On mobile the logout button is inside the collapsed sidebar — open the menu first.
            const isMobile = testInfo.project.name === 'mobile';
            if (isMobile) {
                await openMobileMenu(page);
                await page.waitForTimeout(300);
            }
            await logout(page);
            await login(page, TEST_EMPTY);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'empty-state');
            });
        });

        test('dashboard data-quality banner (mocked issues) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            // The populated DB produces no data-quality issues deterministically, so inject
            // two synthetic ones into the mocked portfolio report (same route the other
            // dashboard shots mock). One warning with CTA + one info row.
            const mockDataPath = path.join(__dirname, 'dashboard-report.json');
            const rawMockData = JSON.parse(fs.readFileSync(mockDataPath, 'utf8'));
            const adjustedMockData = shiftDatesToToday(rawMockData);
            adjustedMockData.summary = {
                ...adjustedMockData.summary,
                data_quality: {
                    data_quality_status: 'partial',
                    issues: [
                        {
                            domain: 'portfolio',
                            code: 'STALE_PRICE',
                            severity: 'warning',
                            message_i18n_key: 'dataQuality.stalePrice',
                            message_params: {count: 2},
                            count: 2,
                            affected_asset_ids: [1, 2],
                            affected_asset_names: ['Apple Inc.', 'Microsoft Corp.'],
                            cta_action: 'navigate_asset',
                            cta_target: '1',
                            group_key: 'stale_price',
                        },
                        {
                            domain: 'portfolio',
                            code: 'MISSING_FX_MARKET',
                            severity: 'info',
                            message_i18n_key: 'dataQuality.missingFx',
                            message_params: {count: 1},
                            count: 1,
                            affected_fx_pairs: ['USD-CHF'],
                            cta_action: 'add_fx_pair',
                            cta_target: 'USD-CHF',
                            group_key: 'missing_fx_market',
                        },
                    ],
                },
            };
            await page.route('**/api/v1/portfolio/report', async (route) => {
                const postData = route.request().postDataJSON?.() as {include_positions_contribution?: boolean} | undefined;
                if (postData?.include_positions_contribution) {
                    const liveResponse = await route.fetch();
                    const liveData = await liveResponse.json();
                    await route.fulfill({
                        status: liveResponse.status(),
                        contentType: 'application/json',
                        body: JSON.stringify({
                            ...adjustedMockData,
                            positions_contribution: liveData.positions_contribution ?? null,
                        }),
                    });
                    return;
                }
                await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(adjustedMockData)});
            });

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);

                const bannerToggle = page.getByTestId('data-quality-toggle');
                await expect(bannerToggle).toBeVisible({timeout: 10_000});
                // Collapsed by default — expand to show the issue chips + CTAs
                await bannerToggle.click();
                await page.waitForTimeout(300);
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'data-quality-banner');
            });
        });
    });

    test.describe('Settings', () => {
        test('user preferences - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await waitForSplashGone(page);
                await waitForNetworkSettled(page);
                // Wait for settings page to be fully rendered
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                // Click preferences tab explicitly (default tab may be profile)
                const prefsTab = page.getByTestId('settings-tab-preferences');
                if (await prefsTab.isVisible().catch(() => false)) {
                    await prefsTab.click();
                    await waitForNetworkSettled(page);
                }
                await page.waitForTimeout(500); // Let tab content render
                await screenshot(page, viewport, lang, theme, 'settings', 'user-preferences');
            });
        });

        test('global settings (admin) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await waitForNetworkSettled(page);
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                await page.getByTestId('settings-tab-admin').click();
                // Wait for admin tab content to finish loading
                await page.getByTestId('global-settings-tab').waitFor({state: 'visible', timeout: 10_000});
                // Wait for LoadingSpinner (role="status") to disappear inside admin tab
                await page
                    .locator('[data-testid="global-settings-tab"] [role="status"]')
                    .waitFor({state: 'hidden', timeout: 15_000})
                    .catch(() => {});
                await waitForNetworkSettled(page);
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'settings', 'global-settings');
            });
        });

        test('about tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await waitForNetworkSettled(page);
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                await page.getByTestId('settings-tab-about').click();
                // Wait for about tab to render and system info to load
                await page.getByTestId('about-tab').waitFor({state: 'visible', timeout: 10_000});
                await page
                    .locator('[data-testid="about-tab"] [role="status"]')
                    .waitFor({state: 'hidden', timeout: 15_000})
                    .catch(() => {});
                // Also wait for version string to replace placeholder "..."
                await page.getByTestId('about-version').filter({hasNotText: '...'}).waitFor({state: 'visible', timeout: 10_000});
                await waitForNetworkSettled(page);
                await page.waitForTimeout(500);
                await screenshot(page, viewport, lang, theme, 'settings', 'about');
            });
        });

        test('password change modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                // Click change password button
                await page.getByTestId('change-password-button').click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, theme, 'settings', 'password-modal');
                // Close modal
                await page.keyboard.press('Escape');
                await page.waitForTimeout(100);
            });
        });

        test('profile tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                await freezeAnimations(page);
                const profileTab = page.locator('[data-testid="settings-tab-profile"], [role="tab"]', {hasText: /profile/i}).first();
                if (await profileTab.isVisible().catch(() => false)) {
                    await profileTab.click();
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'settings', 'profile');
                }
            });
        });

        test('scheduler config modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Navigate to admin tab
                    await page.getByTestId('settings-tab-admin').click();
                    await page.getByTestId('global-settings-tab').waitFor({state: 'visible', timeout: 10_000});
                    await page
                        .locator('[data-testid="global-settings-tab"] [role="status"]')
                        .waitFor({state: 'hidden', timeout: 15_000})
                        .catch(() => {});
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(500);

                    // Settings start locked by default — unlock via the lock toggle
                    // before interacting with scheduler-config-btn (disabled while locked)
                    const lockToggle = page.getByTestId('settings-lock-toggle');
                    if (await lockToggle.isVisible({timeout: 3_000}).catch(() => false)) {
                        const isLocked = await page
                            .getByTestId('scheduler-config-btn')
                            .isDisabled()
                            .catch(() => false);
                        if (isLocked) {
                            await lockToggle.click();
                            await page.waitForTimeout(200);
                        }
                    }

                    // Click the configure button to open SchedulerConfigModal
                    const configBtn = page.getByTestId('scheduler-config-btn');
                    await configBtn.scrollIntoViewIfNeeded();
                    if (await configBtn.isVisible({timeout: 3_000}).catch(() => false)) {
                        await configBtn.click();
                        const configModal = page.getByTestId('scheduler-config-modal');
                        await expect(configModal).toBeVisible({timeout: 5_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'settings', 'scheduler-config');
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        test('scheduler log modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Navigate to admin tab
                    await page.getByTestId('settings-tab-admin').click();
                    await page.getByTestId('global-settings-tab').waitFor({state: 'visible', timeout: 10_000});
                    await page
                        .locator('[data-testid="global-settings-tab"] [role="status"]')
                        .waitFor({state: 'hidden', timeout: 15_000})
                        .catch(() => {});
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(500);

                    // Click the scheduler status row to open SchedulerLogModal
                    const statusRow = page.getByTestId('scheduler-status-row');
                    await statusRow.scrollIntoViewIfNeeded();
                    if (await statusRow.isVisible({timeout: 3_000}).catch(() => false)) {
                        await statusRow.click();
                        const logModal = page.getByTestId('scheduler-log-modal');
                        await expect(logModal).toBeVisible({timeout: 5_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'settings', 'scheduler-log');
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        test('changelog modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            const isMobile = testInfo.project.name === 'mobile';
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/dashboard');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Sidebar version chip opens the bundled changelog (mobile: inside the burger menu)
                    if (isMobile) {
                        await openMobileMenu(page);
                    }
                    await page.getByTestId('sidebar-version').click();
                    const modal = page.getByTestId('changelog-modal');
                    await expect(modal).toBeVisible({timeout: 8_000});
                    // Chapters render from the bundled CHANGELOG — wait for one to exist
                    await expect(page.locator('[data-testid^="changelog-chapter-"]').first()).toBeVisible({timeout: 8_000});
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'settings', 'changelog-modal');

                    // Second shot: search narrows the index, one fold opened by a hit
                    await page.getByTestId('changelog-search').fill('Added');
                    const hits = page.getByTestId('changelog-search-results');
                    await expect(hits).toBeVisible({timeout: 5_000});
                    await hits.locator('[data-testid^="changelog-hit-"]').first().click();
                    await page.waitForTimeout(400); // scroll-into-view after the fold opens
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'settings', 'changelog-modal-search');

                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('cache panel - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                    await page.getByTestId('settings-tab-admin').click();
                    await page.getByTestId('global-settings-tab').waitFor({state: 'visible', timeout: 10_000});
                    await page
                        .locator('[data-testid="global-settings-tab"] [role="status"]')
                        .waitFor({state: 'hidden', timeout: 15_000})
                        .catch(() => {});

                    // Unlock as admin so the Clear actions are rendered too
                    const lockToggle = page.getByTestId('settings-lock-toggle');
                    if (await lockToggle.isVisible({timeout: 3_000}).catch(() => false)) {
                        const isLocked = await page
                            .getByTestId('scheduler-config-btn')
                            .isDisabled()
                            .catch(() => false);
                        if (isLocked) {
                            await lockToggle.click();
                            await page.waitForTimeout(200);
                        }
                    }

                    // Narrow to the Memory category when the category sidebar is rendered (desktop)
                    const memoryCategory = page.getByTestId('global-settings-category-memory');
                    if (await memoryCategory.isVisible({timeout: 1_000}).catch(() => false)) {
                        await memoryCategory.click();
                        await page.waitForTimeout(300);
                    }

                    const cachePanel = page.getByTestId('cache-panel');
                    await expect(cachePanel).toBeVisible({timeout: 10_000});
                    // Wait out the cache-status fetch (spinner → table or empty state)
                    await cachePanel
                        .locator('[role="status"]')
                        .waitFor({state: 'hidden', timeout: 15_000})
                        .catch(() => {});
                    await cachePanel.scrollIntoViewIfNeeded();
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'settings', 'cache-panel');
                    // No re-lock needed: the next combo re-navigates and the tab remounts locked.
                }
            }
        });

        test('about plugin diagnostics - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/settings');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('settings-page').waitFor({state: 'visible', timeout: 10_000});
                    await page.getByTestId('settings-tab-about').click();
                    await page.getByTestId('about-tab').waitFor({state: 'visible', timeout: 10_000});
                    await page
                        .locator('[data-testid="about-tab"] [role="status"]')
                        .waitFor({state: 'hidden', timeout: 15_000})
                        .catch(() => {});

                    // Expand the Plugin diagnostics collapsible (4 registries: asset/fx/brim/signals)
                    const diagnostics = page.getByTestId('about-plugin-diagnostics');
                    await expect(diagnostics).toBeVisible({timeout: 8_000});
                    if ((await diagnostics.getAttribute('open')) === null) {
                        await diagnostics.locator('summary').click();
                        await expect(diagnostics).toHaveAttribute('open', '', {timeout: 3_000});
                    }
                    await diagnostics.scrollIntoViewIfNeeded();
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'settings', 'about-plugin-diagnostics');
                }
            }
        });
    });

    test.describe('Files', () => {
        test.beforeEach(async ({page}) => {
            // Use TEST_ADMIN since db populate assigns brokers to admin
            await login(page, TEST_ADMIN);
        });

        test('static resources tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/files?tab=static');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'files', 'static-tab');
            });
        });

        test('broker reports tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/files?tab=brim');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'files', 'brim-tab');
            });
        });

        test('static resources grid view - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/files?tab=static');
                await page.waitForLoadState('networkidle', {timeout: 20_000});
                await freezeAnimations(page);
                // Switch to grid view if toggle exists
                const gridBtn = page.getByTestId('view-mode-grid');
                if (await gridBtn.isVisible().catch(() => false)) {
                    await gridBtn.click();
                    await page.waitForTimeout(2000); // Wait for image previews to load
                    await screenshot(page, viewport, lang, theme, 'files', 'static-grid');
                }
            });
        });

        test('file preview modal (BRIM) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await page.goto('/files?tab=brim');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await freezeAnimations(page);
                    await page.waitForTimeout(500);

                    // Click the preview action on the first BRIM file row
                    const previewActionsBtn = page
                        .locator('[data-testid="files-table-brim"]')
                        .getByTestId(/^row-actions-/)
                        .first();
                    if (await previewActionsBtn.isVisible({timeout: 3_000}).catch(() => false)) {
                        await previewActionsBtn.click();
                        await page.getByTestId('context-menu-action-preview').click();
                        const previewModal = page.getByTestId('file-preview-modal');
                        await expect(previewModal).toBeVisible({timeout: 8_000});
                        await page.waitForTimeout(1000); // Wait for file content to load
                        await screenshot(page, viewport, lang, theme, 'files', 'preview-modal-csv');
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        test('file preview modal (image) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // File types to preview, with URL filter to find the specific file
            const previewTypes: Array<{filename: string; name: string}> = [
                {filename: '.png', name: 'preview-modal-image'},
                {filename: 'ebook.pdf', name: 'preview-modal-pdf'},
                {filename: 'preview_markdown_sample.md', name: 'preview-modal-markdown'},
                {filename: 'preview_notes_sample.txt', name: 'preview-modal-text'},
            ];

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    for (const {filename, name} of previewTypes) {
                        // Navigate with URL filter to directly show the target file
                        await page.goto(`/files?tab=static&filename=${encodeURIComponent(filename)}`);
                        await setLanguage(page, lang);
                        await setTheme(page, theme);
                        await page.waitForLoadState('networkidle', {timeout: 20_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(500);

                        // Find first row with a preview action
                        const table = page.locator('[data-testid="files-table-static"]');
                        const firstPreviewActionsBtn = table.getByTestId(/^row-actions-/).first();
                        if (await firstPreviewActionsBtn.isVisible({timeout: 3_000}).catch(() => false)) {
                            await firstPreviewActionsBtn.click();
                            await page.getByTestId('context-menu-action-preview').click();
                            const previewModal = page.getByTestId('file-preview-modal');
                            if (await previewModal.isVisible({timeout: 8_000}).catch(() => false)) {
                                await waitForNetworkSettled(page);
                                await page.waitForTimeout(1500); // Wait for content to load (PDF may take longer)
                                await screenshot(page, viewport, lang, theme, 'files', name);
                                await page.keyboard.press('Escape');
                                await page.waitForTimeout(200);
                            }
                        }
                    }
                }
            }
        });
    });

    test.describe('Transactions', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        test('transaction list - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/transactions');
                await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                await waitForNetworkSettled(page);
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'transactions', 'list');
            });
        });

        test('transaction form modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Click the Add transaction button
                    await page.getByTestId('tx-add-button').click();
                    const formModal = page.getByTestId('tx-form-modal');
                    await expect(formModal).toBeVisible({timeout: 8_000});
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'transactions', 'form-modal');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    // Confirm discard if dialog appears
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        const TX_FORM_VARIANT_TYPES: Array<{type: string; name: string}> = [
            {type: 'SELL', name: 'form-modal-sell'},
            {type: 'DIVIDEND', name: 'form-modal-dividend'},
            {type: 'DEPOSIT', name: 'form-modal-deposit'},
            {type: 'ADJUSTMENT', name: 'form-modal-adjustment'},
            {type: 'TRANSFER', name: 'form-modal-transfer'},
            {type: 'FX_CONVERSION', name: 'form-modal-fxconversion'},
            {type: 'CASH_TRANSFER', name: 'form-modal-cash-transfer'},
            {type: 'WITHDRAWAL', name: 'form-modal-withdrawal'},
            {type: 'INTEREST', name: 'form-modal-interest'},
            {type: 'FEE', name: 'form-modal-fee'},
            {type: 'TAX', name: 'form-modal-tax'},
        ];

        /**
         * Select a transaction type in the form's type combobox and wait for the
         * reactive re-render to land — NOT for network. `setType()` only mutates
         * local Svelte state (draft.type) and TransactionTypeSearchSelect issues
         * zero fetch calls, so a type switch never touches the network. The type
         * icon's `src` is keyed by type code, so waiting for it to change from its
         * previous value is a precise, language-agnostic, network-independent
         * completion signal — resolves in ~10-50ms instead of racing a 10s
         * networkidle timeout under parallel CI load.
         */
        async function selectTransactionType(page: Page, type: string) {
            const typeCombobox = page.locator('[data-testid="tx-form-type"] [role="combobox"]');
            if (!(await typeCombobox.isVisible({timeout: 2_000}).catch(() => false))) return;
            const icon = typeCombobox.locator('img');
            const prevSrc = await icon.getAttribute('src').catch(() => null);
            await typeCombobox.click();
            const option = page.locator(`[data-testid="search-select-option-${type}"]`);
            if (!(await option.isVisible({timeout: 2_000}).catch(() => false))) return;
            await option.click();
            if (prevSrc != null) {
                await expect(icon).not.toHaveAttribute('src', prevSrc, {timeout: 3_000});
            } else {
                await icon.waitFor({state: 'attached', timeout: 3_000}).catch(() => {});
            }
        }

        /** Close the form modal, then the TransactionBulkModal that hosts it (tx-add-button
         *  opens a bulk modal wrapping the form) — both must be gone before the next
         *  lang/theme switch, since their backdrop covers the header selectors. */
        async function closeTxFormAndBulkModal(page: Page, formModal: ReturnType<Page['getByTestId']>) {
            await page.keyboard.press('Escape');
            await page.waitForTimeout(200);
            const discardBtn = page.getByTestId('confirm-modal-confirm');
            if (await discardBtn.isVisible({timeout: 500}).catch(() => false)) {
                await discardBtn.click();
                await page.waitForTimeout(200);
            }
            await expect(formModal).not.toBeVisible({timeout: 3_000});

            const bulkModal = page.getByTestId('tx-bulk-modal');
            if (await bulkModal.isVisible({timeout: 500}).catch(() => false)) {
                await page.getByTestId('tx-bulk-close').click();
                await page.waitForTimeout(200);
                const bulkDiscardBtn = page.getByTestId('confirm-modal-confirm');
                if (await bulkDiscardBtn.isVisible({timeout: 500}).catch(() => false)) {
                    await bulkDiscardBtn.click();
                    await page.waitForTimeout(200);
                }
                await expect(bulkModal).not.toBeVisible({timeout: 3_000});
            }
        }

        // Generate one test PER (lang, theme) combo instead of looping inside a
        // single test — this is what actually lets Playwright's worker pool run
        // combos in parallel (viewport parallelism already existed via the
        // desktop/mobile `--project` split). Each combo still opens the Add form
        // ONCE and cycles all 7 types inside it (no re-entering per screenshot).
        for (const lang of SUPPORTED_LANGUAGES) {
            for (const theme of THEMES) {
                test(`transaction form modal variants - ${lang} - ${theme}`, async ({page}, testInfo) => {
                    const viewport = getViewport(testInfo);

                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    // Open Add form ONCE for this combo
                    await page.getByTestId('tx-add-button').click();
                    const formModal = page.getByTestId('tx-form-modal');
                    await expect(formModal).toBeVisible({timeout: 8_000});
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(200);

                    // Cycle through each type inside the same open modal — no
                    // close/reopen between screenshots.
                    for (const {type, name} of TX_FORM_VARIANT_TYPES) {
                        await selectTransactionType(page, type);
                        await freezeAnimations(page);
                        await screenshot(page, viewport, lang, theme, 'transactions', name);
                    }

                    await closeTxFormAndBulkModal(page, formModal);
                });
            }
        }

        test('transaction picker modal - all languages and themes', async ({page}, testInfo) => {
            // Heavier than the default 3-min budget: nested modal navigation × 4 langs × 2 themes.
            test.setTimeout(300_000); // 5 minutes
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Open BulkModal via the row kebab (row actions are kebab-only since 05712844).
                    // Deterministic post-populate: admin owns every row → edit is always offered.
                    const txTable = page.getByTestId('tx-table');
                    await expect(txTable.locator('tbody tr[data-row-id]').first()).toBeVisible({timeout: 5_000});
                    await clickRowAction(page, txTable, 'edit');
                    // BulkModal opens with the FormModal auto-opened on top (single-row edit intent)
                    const bulkModal = page.locator('[data-testid="tx-bulk-modal-root"]');
                    await expect(bulkModal).toBeVisible({timeout: 8_000});
                    // Close the nested FormModal first
                    const formClose = page.getByTestId('tx-form-close');
                    await expect(formClose).toBeVisible({timeout: 3_000});
                    await formClose.click();
                    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
                    // Open the TransactionPickerModal
                    const pickerBtn = page.getByTestId('tx-bulk-picker');
                    await expect(pickerBtn).toBeVisible({timeout: 5_000});
                    await pickerBtn.click();
                    const pickerModal = page.getByTestId('tx-picker-modal');
                    await expect(pickerModal).toBeVisible({timeout: 5_000});
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'transactions', 'picker-modal');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                    // Close any open modals
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('transaction split action modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Find a paired TX row that has a split action. Row actions are kebab-only
                    // since 05712844: open each row's kebab and keep the first offering
                    // `context-menu-action-split` (paired rows only — rule: scan candidates,
                    // don't infer).
                    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
                    const rowCount = await rows.count();
                    let found = false;
                    for (let i = 0; i < Math.min(rowCount, 30) && !found; i++) {
                        const kebab = page
                            .getByTestId('tx-table')
                            .getByTestId(/^row-actions-/)
                            .nth(i);
                        if (!(await kebab.isVisible({timeout: 1_000}).catch(() => false))) continue;
                        await kebab.scrollIntoViewIfNeeded();
                        await kebab.click();
                        const splitAction = page.getByTestId('context-menu-action-split');
                        if (await splitAction.isVisible({timeout: 500}).catch(() => false)) {
                            await splitAction.click();
                            const actionModal = page.getByTestId('tx-action-modal');
                            await expect(actionModal).toBeVisible({timeout: 5_000});
                            await page.waitForTimeout(300);
                            await screenshot(page, viewport, lang, theme, 'transactions', 'action-modal');
                            await page.getByTestId('tx-action-modal-cancel').click();
                            await page.waitForTimeout(200);
                            found = true;
                        } else {
                            // Not a paired row — close the menu before trying the next one
                            await page.keyboard.press('Escape');
                            await page.waitForTimeout(150);
                        }
                    }
                    if (!found) throw new Error('action-modal: no paired row with a split action found in the first 30 rows');
                }
            }
        });

        test('transaction clone flow - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Clone the first row via its kebab — the BulkModal opens in clone intent
                    // with the duplicated row staged (and the form auto-opened on top).
                    // Deterministic post-populate: admin can edit every broker → clone offered.
                    const txTable = page.getByTestId('tx-table');
                    await expect(txTable.locator('tbody tr[data-row-id]').first()).toBeVisible({timeout: 5_000});
                    await clickRowAction(page, txTable, 'clone');

                    const bulkModal = page.locator('[data-testid="tx-bulk-modal-root"]');
                    await expect(bulkModal).toBeVisible({timeout: 8_000});
                    // The pre-filled form auto-opens only for a single-row clone; cloning a
                    // paired row stages both legs instead (no form). Close it when present.
                    const formClose = page.getByTestId('tx-form-close');
                    if (await formClose.isVisible({timeout: 3_000}).catch(() => false)) {
                        await formClose.click();
                        await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
                    }
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'transactions', 'clone-flow');

                    // Close BulkModal (discard the staged clone)
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('transaction promote-merge modal - all languages and themes', async ({page}, testInfo) => {
            // Note: this test finds 2 compatible standalone TXs (WITHDRAWAL+DEPOSIT)
            // and opens the PromoteMergeModal or ConfirmModal. Silently skips if not found.
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions?types=WITHDRAWAL,DEPOSIT&page_size=50');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(1500); // Wait for type store to load

                    const rows = page.locator('[data-testid="tx-table"] tr[data-row-id^="tx-"]');
                    const rowCount = await rows.count();
                    if (rowCount < 2) continue;

                    // Try the first 4 row combinations
                    let screenshotTaken = false;
                    const maxTry = Math.min(rowCount, 4);

                    for (let i = 0; i < maxTry && !screenshotTaken; i++) {
                        for (let j = i + 1; j < maxTry && !screenshotTaken; j++) {
                            // Clear any prior selection before EACH attempt
                            const clearBtn = page.locator('button.selected-count-btn').first();
                            if (await clearBtn.isVisible({timeout: 300}).catch(() => false)) {
                                await clearBtn.click();
                                await page.waitForTimeout(200);
                            }

                            const cbI = rows.nth(i).locator('.checkbox-btn').first();
                            const cbJ = rows.nth(j).locator('.checkbox-btn').first();
                            await cbI.click({timeout: 2_000}).catch(() => {});
                            await page.waitForTimeout(300);
                            await cbJ.click({timeout: 2_000}).catch(() => {});
                            await page.waitForTimeout(800); // Wait for Svelte to re-derive promoteMatch

                            const promoteBtn = page.getByTestId('toolbar-action-promote');
                            const promoteBtnVisible = await promoteBtn.isVisible({timeout: 5_000}).catch(() => false);
                            if (promoteBtnVisible) {
                                await promoteBtn.click();
                                await page.waitForTimeout(500);
                                await freezeAnimations(page);

                                // Use role=dialog to target the ModalBase backdrop (not the inner div)
                                // which also has data-testid="promote-merge-modal"
                                const mergeModal = page.locator('[data-testid="promote-merge-modal"][role="dialog"]');
                                const confirmBtn = page.getByTestId('confirm-modal-confirm');
                                if (await mergeModal.isVisible({timeout: 3_000}).catch(() => false)) {
                                    await screenshot(page, viewport, lang, theme, 'transactions', 'promote-merge-modal');
                                    screenshotTaken = true;
                                } else if (await confirmBtn.isVisible({timeout: 3_000}).catch(() => false)) {
                                    await screenshot(page, viewport, lang, theme, 'transactions', 'promote-merge-modal');
                                    screenshotTaken = true;
                                }
                                await page.keyboard.press('Escape');
                                await page.waitForTimeout(200);
                                const cancelBtn = page.getByTestId('confirm-modal-cancel');
                                if (await cancelBtn.isVisible({timeout: 300}).catch(() => false)) {
                                    await cancelBtn.click();
                                    await page.waitForTimeout(200);
                                }
                            }
                        }
                    }
                    // Clear selection at end of this lang/theme iteration
                    const finalClear = page.locator('button.selected-count-btn').first();
                    if (await finalClear.isVisible({timeout: 300}).catch(() => false)) {
                        await finalClear.click();
                        await page.waitForTimeout(100);
                    }
                }
            }
        });

        test('delete linked pair modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // T4: the dedicated delete modal is gone — a single-row delete
                    // opens the bulk workspace with the pair collapsed into one row
                    // pre-marked for deletion, plus the split-hint banner. That IS
                    // the shot; it is richer than the old modal (grid + banner).
                    //
                    // The mock ships a paired "delete-safe" ETH TRANSFER — find it
                    // by its tag (tags are never translated, unlike the type name
                    // the old text scan relied on). Hard assertions, no probe: this
                    // shot is referenced by the docs, so a silent skip is doc rot.
                    const pairRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').filter({hasText: 'delete-safe'}).filter({hasText: 'ETH'}).first();
                    await expect(pairRow, 'the delete-safe ETH pair must exist — check populate_mock_data.py').toBeVisible({timeout: 10_000});

                    await pairRow.hover();
                    const kebabBtn = pairRow.getByTestId(/^row-actions-/);
                    await expect(kebabBtn, 'the delete-safe pair must offer row actions (TEST_ADMIN owns both brokers)').toBeVisible({timeout: 3_000});
                    await kebabBtn.click();
                    await page.getByTestId('context-menu-action-delete').click();

                    const bulkModal = page.getByTestId('tx-bulk-modal');
                    await expect(bulkModal).toBeVisible({timeout: 5_000});
                    // The pair is staged as ONE collapsed row, marked for deletion,
                    // and the split hint explains the alternative. Both are the
                    // contract this shot documents.
                    await expect(bulkModal.locator('tbody tr.row-deleted')).toHaveCount(1);
                    await expect(bulkModal.getByTestId('tx-bulk-split-hint')).toBeVisible();
                    await waitForSettled(bulkModal.getByTestId('tx-bulk-modal-root'));
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'transactions', 'bulk-delete-pair-modal');

                    // Close WITHOUT committing — the pair is shared mock data and
                    // must survive for the real test suites (tx-delete reads it).
                    await bulkModal.getByTestId('tx-bulk-cancel').click();
                    await expect(bulkModal).not.toBeVisible({timeout: 5_000});
                }
            }
        });
    });

    test.describe('Brokers', () => {
        test.beforeEach(async ({page}) => {
            // Use TEST_ADMIN since db populate assigns brokers to admin
            await login(page, TEST_ADMIN);
        });

        test('broker list - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/brokers');
                await waitForSplashGone(page);
                await freezeAnimations(page);
                // Wait for at least one broker card to be rendered
                await page.locator('[data-testid^="broker-card-"]').first().waitFor({state: 'visible', timeout: 10_000});
                // Extra time for broker icons to load (favicon fetching)
                await page.waitForTimeout(2000);
                await screenshot(page, viewport, lang, theme, 'brokers', 'list');
            });
        });

        test('broker detail - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // Navigate fresh each iteration to ensure clean state
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for cards to load
                    await page.waitForTimeout(1000);

                    const card = page.locator('[data-testid^="broker-card-"]').first();
                    await expect(card).toBeVisible({timeout: 3000});
                    await card.click();
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    // Wait for broker icon to load
                    await page.waitForTimeout(1000);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'detail');
                }
            }
        });

        test('broker edit modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // Navigate fresh each iteration to ensure clean state
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for cards to load
                    await waitForNetworkSettled(page);

                    const card = page.locator('[data-testid^="broker-card-"]').first();
                    await expect(card).toBeVisible({timeout: 5000});
                    await card.click();
                    await waitForNetworkSettled(page);

                    // Click edit button to open BrokerModal
                    const editBtn = page.getByTestId('broker-edit-button');
                    await expect(editBtn).toBeVisible({timeout: 5000});
                    await editBtn.click();
                    await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 5000});
                    await screenshot(page, viewport, lang, theme, 'brokers', 'edit-modal');

                    // Close modal
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('broker sharing modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await waitForSplashGone(page);
                    await freezeAnimations(page);
                    await page.locator('[data-testid^="broker-card-"]').first().waitFor({state: 'visible', timeout: 10_000});

                    const coinbaseCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: 'Coinbase'}).first();
                    await expect(coinbaseCard).toBeVisible({timeout: 5_000});

                    const shareButton = coinbaseCard.locator('[data-testid^="broker-share-"]').first();
                    await expect(shareButton).toBeVisible({timeout: 5_000});
                    await shareButton.click();
                    await expect(page.getByTestId('broker-sharing-modal')).toBeVisible({timeout: 5_000});
                    await page.waitForTimeout(500);

                    await screenshot(page, viewport, lang, theme, 'brokers', 'sharing-modal');

                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('broker info tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await waitForNetworkSettled(page);

                    await openBrokerCardByName(page, 'Coinbase');
                    await page.getByTestId('broker-tab-info').click();
                    await expect(page.getByTestId('broker-info-tab')).toBeVisible({timeout: 5_000});
                    await expect(page.getByTestId('broker-metadata')).toBeVisible({timeout: 5_000});
                    await expect(page.getByTestId('broker-sharing-section')).toBeVisible({timeout: 5_000});
                    await page.waitForTimeout(500);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'info-tab');
                }
            }
        });

        test('broker positions tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await waitForNetworkSettled(page);

                    await openBrokerCardByName(page, 'Coinbase');
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await page.getByTestId('broker-tab-posizioni').click();
                    await expect(page.getByTestId('broker-holdings')).toBeVisible({timeout: 5_000});
                    await screenshotPositionsVariants(page, viewport, lang, theme, 'brokers');
                }
            }
        });

        test('broker fifo lots panel - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await waitForNetworkSettled(page);

                    await openBrokerCardByName(page, 'Coinbase');
                    await selectMaxDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await page.getByTestId('broker-tab-posizioni').click();
                    await expect(page.getByTestId('broker-holdings')).toBeVisible({timeout: 5_000});
                    await setPositionsView(page, 'holdings', 'table');

                    await clickRowAction(page, page, 'analyze-lots');

                    await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 5_000});
                    await expect(page.getByTestId('lot-wac-price-chart')).toBeVisible({timeout: 10_000});
                    await expect(page.getByTestId('lot-gantt-chart')).toBeVisible({timeout: 10_000});
                    await captureLotsAnalysisScreenshots(page, viewport, lang, theme, 'brokers');

                    await page.getByTestId('lots-analysis-panel-close').click();
                    await expect(page.getByTestId('lots-analysis-panel')).toBeHidden({timeout: 5_000});
                }
            }
        });

        test('import modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // Navigate fresh each iteration
                    await navigateTo(page, '/brokers');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for cards to load
                    await page.waitForTimeout(1000);

                    const card = page.locator('[data-testid^="broker-card-"]').first();
                    await expect(card).toBeVisible({timeout: 3000});
                    await card.click();
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await page.waitForTimeout(500);

                    // Switch to the Transazioni tab, where the import/new-tx buttons live
                    await page.getByTestId('broker-tab-transazioni').click();
                    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 5000});
                    await page.waitForTimeout(500);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'transactions-tab');

                    // Scroll to and click the import history button
                    const importBtn = page.getByTestId('broker-show-import-history');
                    await importBtn.scrollIntoViewIfNeeded();
                    await expect(importBtn).toBeVisible({timeout: 3000});
                    await importBtn.click();

                    // Wait for modal to appear
                    const modal = page.getByTestId('import-files-modal');
                    await expect(modal).toBeVisible({timeout: 3000});
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-modal');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard step 1 - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Open ImportWizardModal via the Import button on the transactions page
                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});
                    await page.getByTestId('import-wizard-step1').waitFor({state: 'visible', timeout: 5_000});
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-step1');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    // Confirm discard if needed
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    // Also close BulkModal if open
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard step 2 - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    // Open ImportWizardModal
                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});

                    // Skip step 1 (DB already has uploaded files)
                    await page.getByTestId('import-wizard-next').click();
                    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 8_000});
                    await page.waitForTimeout(800); // Wait for broker panels to load
                    await freezeAnimations(page);
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-step2');

                    // Close
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard step 4 asset resolution - all languages and themes', async ({page}, testInfo) => {
            // Heavier than the default 3-min budget: real CSV parse via backend × 4 langs × 2 themes.
            test.setTimeout(300_000); // 5 minutes
            // generic_simple.csv contains UNETF (unknown asset → unresolved card in step 4)
            const viewport = getViewport(testInfo);
            const GENERIC_SIMPLE = path.resolve(__dirname, '../../backend/app/services/brim_providers/sample_reports/generic_simple.csv');

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    // Open ImportWizardModal
                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});

                    // Skip step 1 (go to step 2 which shows files already in DB)
                    await page.getByTestId('import-wizard-next').click();
                    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 8_000});
                    await page.waitForTimeout(800);

                    // Find and select the generic_simple.csv row
                    const step2 = page.getByTestId('import-wizard-step2');
                    const fileRow = step2.locator('tr[data-row-id]').filter({hasText: 'generic_simple.csv'}).first();
                    if (await fileRow.isVisible({timeout: 3_000}).catch(() => false)) {
                        const checkbox = fileRow.locator('td.td-select button.checkbox-btn');
                        await checkbox.scrollIntoViewIfNeeded();
                        await page.keyboard.press('Escape'); // dismiss any open dropdown
                        await page.waitForTimeout(200);
                        await checkbox.click();

                        // Parse (step 3)
                        const parseBtn = page.getByTestId('import-wizard-parse');
                        if (await parseBtn.isEnabled({timeout: 3_000}).catch(() => false)) {
                            await parseBtn.click();
                            await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 15_000});
                            await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: 30_000});
                            await page.waitForTimeout(500); // Let UI settle
                            await freezeAnimations(page);
                            await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-step3');

                            // Continue to step 4
                            await page.getByTestId('import-wizard-continue').click();
                            // Handle parse warnings overlay (intercepts step3 → step4 transition)
                            const warningConfirm = page.getByTestId('import-wizard-warning-confirm');
                            if (await warningConfirm.isVisible({timeout: 3_000}).catch(() => false)) {
                                await warningConfirm.click();
                                await page.waitForTimeout(300);
                            }
                            await page.getByTestId('import-wizard-step4').waitFor({state: 'visible', timeout: 10_000});
                            await page.waitForTimeout(500);
                            await freezeAnimations(page);
                            await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-step4-resolution');
                        }
                    }

                    // Close
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard duplicate detection - all languages and themes', async ({page}, testInfo) => {
            // generic_simple.csv has AAPL rows that match transactions already in the DB.
            // After parsing, step4 shows the transaction table with "likely duplicate" badges.
            // We scroll to center on the table to make the duplicate status visible.
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});

                    // Skip to step 2
                    await page.getByTestId('import-wizard-next').click();
                    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 8_000});
                    await page.waitForTimeout(800);

                    // Select generic_simple.csv — has AAPL/MSFT rows + UNETF (unresolved)
                    // The AAPL rows match existing DB transactions → show as "likely duplicate"
                    const step2 = page.getByTestId('import-wizard-step2');
                    const fileRow = step2.locator('tr[data-row-id]').filter({hasText: 'generic_simple.csv'}).first();
                    if (await fileRow.isVisible({timeout: 3_000}).catch(() => false)) {
                        const checkbox = fileRow.locator('td.td-select button.checkbox-btn');
                        await checkbox.scrollIntoViewIfNeeded();
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                        await checkbox.click();

                        const parseBtn = page.getByTestId('import-wizard-parse');
                        if (await parseBtn.isEnabled({timeout: 3_000}).catch(() => false)) {
                            await parseBtn.click();
                            await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 15_000});
                            await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: 30_000});
                            await page.getByTestId('import-wizard-continue').click();
                            // Handle parse warnings overlay (intercepts step3 → step4 transition)
                            const warningConfirm = page.getByTestId('import-wizard-warning-confirm');
                            if (await warningConfirm.isVisible({timeout: 3_000}).catch(() => false)) {
                                await warningConfirm.click();
                                await page.waitForTimeout(300);
                            }
                            await page.getByTestId('import-wizard-step4').waitFor({state: 'visible', timeout: 10_000});
                            await page.waitForTimeout(500);

                            // Scroll to the transaction table (below the resolve section) to show duplicate badges
                            const step4 = page.getByTestId('import-wizard-step4');
                            const txTable = step4.locator('table').first();
                            if (await txTable.isVisible({timeout: 2_000}).catch(() => false)) {
                                await txTable.evaluate((el) => el.scrollIntoView({block: 'center'}));
                                await page.waitForTimeout(300);
                            }
                            await freezeAnimations(page);
                            await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-duplicate');
                        }
                    }

                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import bulk staging - all languages and themes', async ({page}, testInfo) => {
            // Heavier than the default 3-min budget under load: real backend list load × 4 langs × 2 themes.
            test.setTimeout(300_000); // 5 minutes
            // Show the BulkModal (staging grid) — open it in edit mode from the transactions table.
            // The BulkModal staging view is the same whether populated from wizard import or manual edit.
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await waitForNetworkSettled(page);
                    await freezeAnimations(page);

                    // Open BulkModal via the row kebab edit action (kebab-only since 05712844).
                    // Deterministic post-populate: admin owns every row → edit is always offered.
                    const txTable = page.getByTestId('tx-table');
                    await expect(txTable.locator('tbody tr[data-row-id]').first()).toBeVisible({timeout: 5_000});
                    await clickRowAction(page, txTable, 'edit');
                    // BulkModal opens with the FormModal auto-opened on top (single-row edit intent)
                    const bulkModal = page.locator('[data-testid="tx-bulk-modal-root"]');
                    await expect(bulkModal).toBeVisible({timeout: 8_000});
                    // Close the auto-opened FormModal to reveal the staging grid
                    const formClose = page.getByTestId('tx-form-close');
                    await expect(formClose).toBeVisible({timeout: 3_000});
                    await formClose.click();
                    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'brokers', 'import-bulk-staging');

                    // Close BulkModal
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('import wizard conditional steps (assets / fix / duplicates / n-way compare) - all languages and themes', async ({page}, testInfo) => {
            // Heaviest wizard test: two real uploads + backend parse + four step walkthrough × 8 combos.
            test.setTimeout(600_000); // 10 minutes
            const viewport = getViewport(testInfo);
            const TITOLI_CSV = path.join(__dirname, 'assets', 'demo_credit_agricole_titoli.csv');
            const CONTO_CSV = path.join(__dirname, 'assets', 'demo_credit_agricole_conto.csv');

            // Track this test's own uploads via the upload responses, so cleanup deletes
            // exactly those files (never a parallel worker's same-named copies).
            const uploadedFileIds = new Set<string>();
            page.on('response', (response) => {
                if (!response.url().includes('/api/v1/brokers/import/upload')) return;
                if (!response.ok()) return;
                response
                    .json()
                    .then((body) => {
                        const id = (body as {file_id?: string})?.file_id;
                        if (id) uploadedFileIds.add(id);
                    })
                    .catch(() => {});
            });
            const cleanupUploadedFiles = async () => {
                for (const id of uploadedFileIds) {
                    await page.request.delete(`/api/v1/brokers/import/files/${id}`).catch(() => {});
                }
                uploadedFileIds.clear();
            };

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    try {
                        // ── Step 1: upload the two Credit Agricole demo files ──
                        await page.getByTestId('tx-import-button').click();
                        await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});
                        const step1 = page.getByTestId('import-wizard-step1');
                        await step1.waitFor({state: 'visible', timeout: 5_000});
                        const dropzoneMore = page.getByTestId('import-wizard-upload-more');
                        if (await dropzoneMore.isVisible({timeout: 1_000}).catch(() => false)) {
                            await dropzoneMore.click();
                        }
                        await step1.locator('[data-testid="file-input"]').setInputFiles([TITOLI_CSV, CONTO_CSV]);
                        // Both pending rows rendered
                        await expect(step1.locator('tbody tr[data-row-id]')).toHaveCount(2, {timeout: 5_000});

                        // Assign the global broker (both files to the same broker — duplicates
                        // arbitration is per-broker). Prefer Interactive Brokers (has an icon in
                        // the populated DB); fall back to the first editable broker.
                        await page.getByTestId('import-wizard-step1-broker-select').locator('[role="combobox"]').click();
                        const listbox = page.locator('[role="listbox"]').first();
                        await expect(listbox).toBeVisible({timeout: 5_000});
                        await expect(listbox).toHaveAttribute('aria-busy', 'false', {timeout: 8_000});
                        const ibOption = listbox.locator('[data-testid^="search-select-option-"]').filter({hasText: 'Interactive Brokers'}).first();
                        if (await ibOption.isVisible({timeout: 1_000}).catch(() => false)) {
                            await ibOption.click();
                        } else {
                            await listbox.locator('[data-testid^="search-select-option-"]').first().click();
                        }

                        // Upload on Next — uploaded files arrive pre-selected in step 2 (T7)
                        await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
                        await page.getByTestId('import-wizard-next').click();
                        const step2 = page.getByTestId('import-wizard-step2');
                        await step2.waitFor({state: 'visible', timeout: 10_000});
                        await expect(step2).toHaveAttribute('data-busy', 'false', {timeout: 20_000});

                        // ── Step 2 → 3: parse both files (plugin auto-picked: broker_credit_agricole) ──
                        const parseBtn = page.getByTestId('import-wizard-parse');
                        await expect(parseBtn).toBeEnabled({timeout: 10_000});
                        await parseBtn.click();
                        await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 15_000});
                        await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: 60_000});
                        await page.getByTestId('import-wizard-continue').click();
                        // Parse-warnings overlay intercepts the step3 → next transition
                        const warningConfirm = page.getByTestId('import-wizard-warning-confirm');
                        if (await warningConfirm.isVisible({timeout: 3_000}).catch(() => false)) {
                            await warningConfirm.click();
                            await page.waitForTimeout(300);
                        }

                        // ── Assets step: proposed (AMUNDI name-suffix) + confirmed (BTP) groups ──
                        const assetsStep = page.getByTestId('import-wizard-step-assets');
                        await expect(assetsStep).toBeVisible({timeout: 15_000});
                        await expect(assetsStep.getByTestId('asset-group-step')).toBeVisible({timeout: 10_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-assets-step');
                        await page.getByTestId('import-wizard-assets-continue').click();

                        // ── Fix step: bundled-amount warning + unresolved-asset blocker ──
                        const fixStep = page.getByTestId('import-wizard-step-fix');
                        await expect(fixStep).toBeVisible({timeout: 15_000});
                        await expect(fixStep.getByTestId('fix-step-row').first()).toBeVisible({timeout: 10_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-fix-step');
                        // Settle every flagged row (keep the plugin's fallback) to unlock Continue
                        await fixStep.getByTestId('fix-step-accept-all').click();
                        await expect(page.getByTestId('import-wizard-fix-continue')).toBeEnabled({timeout: 10_000});
                        await page.getByTestId('import-wizard-fix-continue').click();

                        // ── Duplicates step: cross-file coupon pair (probable/partial tier) ──
                        const dupStep = page.getByTestId('import-wizard-step-duplicates');
                        await expect(dupStep).toBeVisible({timeout: 20_000});
                        await expect(dupStep.getByTestId('import-wizard-duplicate-resolver')).toBeVisible({timeout: 10_000});
                        // Probable-tier groups start expanded; expand the resolver when all tiers are 'sure'
                        const resolverToggle = dupStep.getByTestId('import-wizard-duplicate-resolver-toggle');
                        if (
                            !(await dupStep
                                .getByTestId('import-wizard-file-priority')
                                .isVisible({timeout: 500})
                                .catch(() => false))
                        ) {
                            await resolverToggle.click();
                            await expect(dupStep.getByTestId('import-wizard-file-priority')).toBeVisible({timeout: 3_000});
                        }
                        // Open the first tier panel so its groups are listed in the shot
                        const tierToggle = dupStep.locator('[data-testid^="import-wizard-resolver-tier-toggle-"]').first();
                        await expect(tierToggle).toBeVisible({timeout: 5_000});
                        await tierToggle.click();
                        await expect(dupStep.getByTestId('import-wizard-duplicate-group').first()).toBeVisible({timeout: 3_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'brokers', 'import-wizard-duplicates-step');

                        // ── N-way compare modal from a duplicate group ──
                        // The compare action lives inside the expanded group's body
                        await dupStep.getByTestId('import-wizard-duplicate-group').first().locator('button').first().click();
                        const compareBtn = dupStep.locator('[data-testid^="import-wizard-resolver-compare-"]').first();
                        await expect(compareBtn).toBeVisible({timeout: 5_000});
                        await compareBtn.click();
                        const compareModal = page.getByTestId('import-wizard-compare-modal');
                        await expect(compareModal).toBeVisible({timeout: 5_000});
                        await expect(compareModal.getByTestId('import-wizard-compare-table')).toBeVisible({timeout: 5_000});
                        await freezeAnimations(page);
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, theme, 'brokers', 'import-nway-compare');
                        await page.getByTestId('import-wizard-compare-close').click();
                        await expect(compareModal).not.toBeVisible({timeout: 3_000});
                    } finally {
                        // Close the wizard (confirming the discard) and remove this combo's uploads
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(300);
                        const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                        if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                            await confirmDiscard.click();
                            await page.waitForTimeout(200);
                        }
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                        await cleanupUploadedFiles();
                    }
                }
            }
        });
    });

    test.describe('Media & Upload', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        test('image edit modal - crop view', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // Navigate fresh each time to avoid leftover modal state
                    await navigateTo(page, '/files');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await page.waitForTimeout(300);
                    await setLanguage(page, lang);
                    await page.getByTestId('files-tab-static').click();
                    await page.waitForTimeout(300);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Open upload area
                    await page.getByTestId('upload-button').click();
                    await expect(page.getByTestId('file-uploader')).toBeVisible({timeout: 3000});

                    // Add an image file via the hidden file input
                    const testImagePath = path.resolve(__dirname, '../static/icons/transactions/buy.png');
                    await page.getByTestId('file-input').setInputFiles(testImagePath);

                    // Wait for file to appear in pending list
                    await expect(page.locator('.file-item')).toBeVisible({timeout: 3000});

                    // Click the edit (pencil) button on the image file
                    const editBtn = page.getByTestId('file-edit-btn').first();
                    await expect(editBtn).toBeVisible({timeout: 2000});
                    await editBtn.click();

                    // Wait for ImageEditModal to appear and cropper to initialize
                    await expect(page.getByTestId('image-edit-modal')).toBeVisible({timeout: 5000});
                    const cropperReady = page.locator('[data-cropper-ready="true"]');
                    await cropperReady.waitFor({state: 'attached', timeout: 8000});
                    await page.waitForTimeout(800);

                    await screenshot(page, viewport, lang, theme, 'media', 'image-edit-modal');

                    // Close the modal to ensure clean state for next iteration
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    // If confirmation dialog appears, dismiss it
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        test('asset picker modal - existing files', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // Navigate fresh each iteration to ensure clean state
                    await navigateTo(page, '/brokers');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await page.waitForTimeout(300);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await page.waitForTimeout(500);

                    const card = page.locator('[data-testid^="broker-card-"]').first();
                    if (await card.isVisible({timeout: 2000}).catch(() => false)) {
                        await card.click();
                        await page.waitForLoadState('networkidle', {timeout: 20_000});
                        await page.waitForTimeout(500);

                        // Click edit button to open BrokerModal
                        const editBtn = page.getByTestId('broker-edit-button');
                        if (await editBtn.isVisible({timeout: 2000}).catch(() => false)) {
                            await editBtn.click();
                            await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 3000});
                            await page.waitForTimeout(300);

                            // Click on broker icon to open AssetPickerModal
                            const iconTrigger = page.getByTestId('broker-icon-trigger');
                            if (await iconTrigger.isVisible({timeout: 1000}).catch(() => false)) {
                                await iconTrigger.click();
                                const pickerModal = page.getByTestId('asset-picker-modal');
                                if (await pickerModal.isVisible({timeout: 3000}).catch(() => false)) {
                                    await waitForNetworkSettled(page);
                                    await page.waitForTimeout(1500); // Wait for file previews to load
                                    await screenshot(page, viewport, lang, theme, 'media', 'asset-picker-modal');
                                    await page.keyboard.press('Escape');
                                    await page.waitForTimeout(200);
                                }
                            }

                            // Close broker modal
                            await page.keyboard.press('Escape');
                            await page.waitForTimeout(200);
                        }
                    }
                }
            }
        });

        test('file upload with pending files', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/files');
                    await page.waitForLoadState('networkidle', {timeout: 20_000});
                    await page.waitForTimeout(300);
                    await setLanguage(page, lang);
                    await page.getByTestId('files-tab-static').click();
                    await page.waitForTimeout(300);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Open upload area
                    await page.getByTestId('upload-button').click();
                    await expect(page.getByTestId('file-uploader')).toBeVisible({timeout: 3000});
                    await page.waitForTimeout(300);

                    await screenshot(page, viewport, lang, theme, 'media', 'file-uploader-empty');
                }
            }
        });
    });

    test.describe('FX', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        test('FX list page', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await goToFxPage(page);
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                await freezeAnimations(page);
                // Wait for charts (canvas) to render
                await page.waitForTimeout(2000);
                await screenshot(page, viewport, lang, theme, 'fx', 'list');
            });
        });

        test('FX list table', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Switch to table view
                    const tableBtn = page.getByTestId('view-mode-list');
                    if (await tableBtn.isVisible({timeout: 2000}).catch(() => false)) {
                        await tableBtn.click();
                        await page.waitForTimeout(1000); // Wait for table to render
                    }
                    await screenshot(page, viewport, lang, theme, 'fx', 'list-table');
                }
            }
        });

        test('FX list filtered', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Apply currency filter (EUR)
                    const filterSelect = page.getByTestId('fx-currency-filter').first();
                    if (await filterSelect.isVisible({timeout: 2000}).catch(() => false)) {
                        await filterSelect.locator('[role="combobox"]').click();
                        await page.waitForTimeout(300);
                        const option = page.locator('[role="listbox"] button').filter({hasText: 'EUR'}).first();
                        if (await option.isVisible({timeout: 1000}).catch(() => false)) {
                            await option.click();
                            await page.waitForTimeout(1500); // Wait for charts to re-render
                        }
                    }
                    await screenshot(page, viewport, lang, theme, 'fx', 'list-filtered');
                }
            }
        });

        test('Add pair - direct routes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openAddPairModal(page);
                    const modal = page.getByTestId('fx-add-pair-modal');
                    const selects = modal.locator('[role="combobox"]');
                    await expect(selects.first()).toBeVisible({timeout: 3000});

                    // Select USD as base (not excluded — EUR is excluded because EUR-USD exists)
                    await selects.first().click();
                    await page.waitForTimeout(300);
                    const searchInput1 = modal.locator('input[type="text"]').first();
                    if (await searchInput1.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput1.fill('USD');
                        await page.waitForTimeout(400);
                    }
                    const usdOption = page.locator('[role="listbox"] button').filter({hasText: 'USD'}).first();
                    await expect(usdOption).toBeVisible({timeout: 2000});
                    await usdOption.click();
                    await page.waitForTimeout(500);

                    // Select CHF as quote (not excluded — FED provides USD→CHF direct)
                    await selects.nth(1).click();
                    await page.waitForTimeout(300);
                    const searchInput2 = modal.locator('input[type="text"]').first();
                    if (await searchInput2.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput2.fill('CHF');
                        await page.waitForTimeout(400);
                    }
                    const chfOption = page.locator('[role="listbox"] button').filter({hasText: 'CHF'}).first();
                    await expect(chfOption).toBeVisible({timeout: 2000});
                    await chfOption.click();

                    // Wait for route discovery to complete (loading spinner → route-select div)
                    const routeSelect = modal.locator('[data-testid="fx-route-select"]');
                    await routeSelect.waitFor({state: 'visible', timeout: 10_000});

                    // Open route picker to show discovered routes
                    const addRouteBtn = routeSelect
                        .locator('button')
                        .filter({hasText: /add|aggiungi|ajouter|añadir/i})
                        .first();
                    await addRouteBtn.waitFor({state: 'visible', timeout: 5000});
                    await addRouteBtn.click();

                    // Scroll modal body to bottom so picker content is in view
                    await modal.locator('.overflow-y-auto').evaluate((el) => (el.scrollTop = el.scrollHeight));

                    // Wait for direct routes section to render
                    await modal.locator('[data-testid="fx-route-direct-section"]').waitFor({state: 'visible', timeout: 5000});
                    await page.waitForTimeout(500); // Extra settle time for provider icons

                    await screenshot(page, viewport, lang, theme, 'fx', 'add-pair-routes');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                }
            }
        });

        test('Add pair - chain', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await openAddPairModal(page);
                    const modal = page.getByTestId('fx-add-pair-modal');
                    const selects = modal.locator('[role="combobox"]');
                    await expect(selects.first()).toBeVisible({timeout: 3000});

                    // Select NOK as base (not excluded)
                    await selects.first().click();
                    await page.waitForTimeout(300);
                    const searchInput1 = modal.locator('input[type="text"]').first();
                    if (await searchInput1.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput1.fill('NOK');
                        await page.waitForTimeout(400);
                    }
                    const nokOption = page.locator('[role="listbox"] button').filter({hasText: 'NOK'}).first();
                    await expect(nokOption).toBeVisible({timeout: 2000});
                    await nokOption.click();
                    await page.waitForTimeout(500);

                    // Select CHF as quote (not excluded — chain route: ECB NOK→EUR + ECB EUR→CHF)
                    await selects.nth(1).click();
                    await page.waitForTimeout(300);
                    const searchInput2 = modal.locator('input[type="text"]').first();
                    if (await searchInput2.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput2.fill('CHF');
                        await page.waitForTimeout(400);
                    }
                    const chfOption = page.locator('[role="listbox"] button').filter({hasText: 'CHF'}).first();
                    await expect(chfOption).toBeVisible({timeout: 2000});
                    await chfOption.click();

                    // Wait for route discovery to complete (loading spinner → route-select div)
                    const routeSelect = modal.locator('[data-testid="fx-route-select"]');
                    await routeSelect.waitFor({state: 'visible', timeout: 10_000});

                    // Open route picker to show discovered chain routes
                    const addRouteBtn = routeSelect
                        .locator('button')
                        .filter({hasText: /add|aggiungi|ajouter|añadir/i})
                        .first();
                    await addRouteBtn.waitFor({state: 'visible', timeout: 5000});
                    await addRouteBtn.click();
                    await page.waitForTimeout(500); // Let Svelte render the picker

                    // Scroll modal body to bottom so picker content is in view
                    await modal.locator('.overflow-y-auto').evaluate((el) => (el.scrollTop = el.scrollHeight));

                    // Wait for chain routes section to render
                    const chainSection = modal.locator('[data-testid^="fx-route-chain-section"]').first();
                    await chainSection.waitFor({state: 'visible', timeout: 5000});

                    // Click the chain section header to expand it (collapsed by default when direct routes exist)
                    const chainHeader = chainSection.locator('button').first();
                    if (await chainHeader.isVisible({timeout: 1000}).catch(() => false)) {
                        await chainHeader.click();
                        await page.waitForTimeout(500); // Let chain routes expand
                    }

                    // Click the first chain route item to add it — this shows the 2-step route in the selected panel
                    const firstChainRoute = chainSection.locator('[data-testid^="fx-route-chain-"]').first();
                    if (await firstChainRoute.isVisible({timeout: 2000}).catch(() => false)) {
                        await firstChainRoute.click();
                        await page.waitForTimeout(500); // Wait for route to appear in the selected list
                    }

                    // Scroll modal body to bottom so the selected chain route + detail are in view
                    await modal.locator('.overflow-y-auto').evaluate((el) => (el.scrollTop = el.scrollHeight));
                    await page.waitForTimeout(500); // Extra settle time for provider icons

                    await screenshot(page, viewport, lang, theme, 'fx', 'add-pair-chain');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                }
            }
        });

        test('Sync All modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Click sync all button
                    const syncBtn = page.getByTestId('fx-sync-all-button');
                    if (await syncBtn.isVisible({timeout: 2000}).catch(() => false)) {
                        await syncBtn.click();
                        // Wait for sync modal to appear and show progress
                        await page.waitForTimeout(1500);
                        await screenshot(page, viewport, lang, theme, 'fx', 'sync-progress');
                        // Close modal
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                    }
                }
            }
        });

        test('Detail page chart', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await goToFxDetailPage(page, 'EUR-USD');
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                await freezeAnimations(page);
                // Wait for ECharts canvas to render
                await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                await page.waitForTimeout(2000);
                await screenshot(page, viewport, lang, theme, 'fx', 'detail-chart');
            });
        });

        test('Detail signals overlay', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for chart canvas
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1500);

                    // Toggle signals panel
                    const signalsToggle = page.getByTestId('fx-detail-signals-toggle');
                    if (await signalsToggle.isVisible({timeout: 2000}).catch(() => false)) {
                        await signalsToggle.click();
                        await page.waitForTimeout(500);
                        // Scroll down to make signals panel content visible
                        const signalsPanel = page.getByTestId('fx-detail-signals-panel');
                        if (await signalsPanel.isVisible({timeout: 2000}).catch(() => false)) {
                            await signalsPanel.scrollIntoViewIfNeeded();
                            await page.waitForTimeout(300);
                        }
                    }
                    await screenshot(page, viewport, lang, theme, 'fx', 'detail-signals');
                }
            }
        });

        test('Detail measures panel', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for chart canvas
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1500);

                    // Toggle measures panel
                    const measuresToggle = page.getByTestId('fx-detail-measures-toggle');
                    if (await measuresToggle.isVisible({timeout: 2000}).catch(() => false)) {
                        await measuresToggle.click();
                        await page.waitForTimeout(500);
                    }
                    await screenshot(page, viewport, lang, theme, 'fx', 'detail-measures');
                }
            }
        });

        test('Detail data editor', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for chart canvas
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    // Click edit button to open data editor
                    const editBtn = page.getByTestId('fx-detail-edit-btn');
                    if (await editBtn.isVisible({timeout: 2000}).catch(() => false)) {
                        await editBtn.click();
                        await page.waitForTimeout(500);
                        // Scroll to editor panel for full view
                        const editorPanel = page.getByTestId('fx-detail-editor-panel');
                        if (await editorPanel.isVisible({timeout: 2000}).catch(() => false)) {
                            await editorPanel.scrollIntoViewIfNeeded();
                            await page.waitForTimeout(300);
                        }
                    }
                    await screenshot(page, viewport, lang, theme, 'fx', 'detail-editor');
                }
            }
        });

        test('Detail CSV import modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Wait for chart
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    // Open data editor first
                    const editBtn = page.getByTestId('fx-detail-edit-btn');
                    await editBtn.scrollIntoViewIfNeeded();
                    await expect(editBtn).toBeVisible({timeout: 3000});
                    await editBtn.click();
                    await page.waitForTimeout(800);

                    // Scroll to editor panel to make Import CSV button visible
                    const editorPanel = page.getByTestId('fx-detail-editor-panel');
                    await editorPanel.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(300);

                    // Click Import CSV button
                    const importBtn = page.getByTestId('fx-data-import-btn');
                    await importBtn.scrollIntoViewIfNeeded();
                    await expect(importBtn).toBeVisible({timeout: 3000});
                    await importBtn.click();
                    const importModal = page.getByTestId('data-import-modal');
                    await expect(importModal).toBeVisible({timeout: 3000});
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'fx', 'detail-csv-import');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Chart settings modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await page.waitForTimeout(1500);

                    // Click chart settings button (scroll to it first)
                    const settingsBtn = page.getByTestId('fx-chart-settings-button');
                    await settingsBtn.scrollIntoViewIfNeeded();
                    await expect(settingsBtn).toBeVisible({timeout: 3000});
                    await settingsBtn.click();
                    const settingsModal = page.getByTestId('chart-settings-modal');
                    await expect(settingsModal).toBeVisible({timeout: 3000});
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'fx', 'chart-settings');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Provider config modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToFxDetailPage(page, 'EUR-USD');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await page.waitForTimeout(1000);

                    // Click provider button (scroll to it first)
                    const providerBtn = page.getByTestId('fx-detail-provider-btn');
                    await providerBtn.scrollIntoViewIfNeeded();
                    await expect(providerBtn).toBeVisible({timeout: 3000});
                    await providerBtn.click();
                    // Wait for the inner modal (FxPairAddModal in editMode)
                    const addPairModal = page.getByTestId('fx-add-pair-modal');
                    await expect(addPairModal).toBeVisible({timeout: 5000});
                    await page.waitForTimeout(2000); // Extra time for provider icons and route loading
                    await screenshot(page, viewport, lang, theme, 'fx', 'provider-config');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });
    });

    test.describe('Assets', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        // Gallery target: Apple Inc. — has 30 days of price history from db populate
        const GALLERY_ASSET = 'Apple';

        test('Asset list page', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await goToAssetsPage(page);
                await selectOneYearDateRange(page);
                await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                await freezeAnimations(page);
                await page.waitForTimeout(1500);
                await screenshot(page, viewport, lang, theme, 'assets', 'list');
            });
        });

        test('Asset list table', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Switch to table view
                    const tableBtn = page.getByTestId('view-mode-list');
                    if (await tableBtn.isVisible({timeout: 2000}).catch(() => false)) {
                        await tableBtn.click();
                        await page.waitForTimeout(1000); // Wait for table to render
                    }
                    await screenshot(page, viewport, lang, theme, 'assets', 'list-table');
                }
            }
        });

        test('Asset list filtered', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Type search text
                    const searchInput = page.getByTestId('assets-search-input');
                    if (await searchInput.isVisible({timeout: 2000}).catch(() => false)) {
                        await searchInput.fill('ETF');
                        await page.waitForTimeout(1000);
                    }
                    await screenshot(page, viewport, lang, theme, 'assets', 'list-filtered');
                }
            }
        });

        test('Asset detail chart', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(500);
                    // Screenshot 1: line chart (default)
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-chart');

                    // Screenshot 2: candlestick chart
                    const candlestickBtn = page.getByTestId('chart-type-candlestick');
                    if (await candlestickBtn.isVisible({timeout: 2000}).catch(() => false)) {
                        await candlestickBtn.click();
                        await page.waitForTimeout(800); // Wait for candlestick to render
                        await freezeAnimations(page);
                        await screenshot(page, viewport, lang, theme, 'assets', 'detail-chart-candlestick');
                        // Reset to line for next iteration
                        const lineBtn = page.getByTestId('chart-type-line');
                        if (await lineBtn.isVisible({timeout: 1000}).catch(() => false)) {
                            await lineBtn.click();
                            await page.waitForTimeout(300);
                        }
                    }
                }
            }
        });

        test('Asset detail signals', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});

                    // Toggle signals panel
                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    if (await signalsToggle.isVisible({timeout: 2000}).catch(() => false)) {
                        await signalsToggle.click();
                        await page.waitForTimeout(500);
                    }
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals');
                }
            }
        });

        test('Asset detail signals EMA - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    // Open signals panel and add EMA indicator via the grouped SignalTreeSelect
                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    await expect(signalsToggle).toBeVisible({timeout: 5_000});
                    await signalsToggle.click();
                    await page.waitForTimeout(500);

                    await selectIndicatorFromTree(page, 'trend', 'ema');
                    await waitForSignalCardsSettled(page);
                    await page.waitForTimeout(500); // Let the chart redraw the overlay
                    // Scroll the chart into center of viewport
                    await page.getByTestId('asset-detail-chart').evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await page.waitForTimeout(300);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-ema');
                }
            }
        });

        test('Asset detail signals RSI - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    await expect(signalsToggle).toBeVisible({timeout: 5_000});
                    await signalsToggle.click();
                    await page.waitForTimeout(500);

                    await selectIndicatorFromTree(page, 'momentum', 'rsi');
                    await waitForSignalCardsSettled(page);
                    await page.waitForTimeout(500);
                    // Scroll the chart into center of viewport (not just into view)
                    await page.getByTestId('asset-detail-chart').evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await page.waitForTimeout(300);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-rsi');
                }
            }
        });

        test('Asset detail signals MACD - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    await expect(signalsToggle).toBeVisible({timeout: 5_000});
                    await signalsToggle.click();
                    await page.waitForTimeout(500);

                    await selectIndicatorFromTree(page, 'momentum', 'macd');
                    await waitForSignalCardsSettled(page);
                    await page.waitForTimeout(500);
                    // Scroll the chart into center of viewport
                    await page.getByTestId('asset-detail-chart').evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await page.waitForTimeout(300);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-macd');
                }
            }
        });

        test('Asset detail signals Bollinger - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    await expect(signalsToggle).toBeVisible({timeout: 5_000});
                    await signalsToggle.click();
                    await page.waitForTimeout(500);

                    await selectIndicatorFromTree(page, 'volatility', 'bollinger');
                    await waitForSignalCardsSettled(page);
                    await page.waitForTimeout(500);
                    await page.getByTestId('asset-detail-chart').evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await page.waitForTimeout(300);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-bollinger');
                }
            }
        });

        test('Asset detail signals tree select open - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});

                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    await expect(signalsToggle).toBeVisible({timeout: 5_000});
                    await signalsToggle.click();
                    await page.waitForTimeout(500);

                    // Open the grouped indicator dropdown: family groups with count badges +
                    // search box. The first family (trend) opens expanded on open — the shot
                    // shows both an expanded family with options and the collapsed others.
                    const selectButton = page.getByTestId('signals-indicator-select-button');
                    await expect(selectButton).toBeVisible({timeout: 15_000});
                    await selectButton.scrollIntoViewIfNeeded();
                    await selectButton.click();
                    const trendGroup = page.getByTestId('signal-tree-group-trend');
                    await expect(trendGroup).toBeVisible({timeout: 3_000});
                    await expect(trendGroup).toHaveAttribute('aria-expanded', 'true', {timeout: 3_000});
                    await expect(page.getByTestId('signal-tree-option-sma')).toBeVisible({timeout: 3_000});
                    await freezeAnimations(page);
                    await page.waitForTimeout(200);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-tree');
                    // Close the dropdown without selecting
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Asset detail signals drawdown - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await resetChartSettings(page); // each combo starts with no signals configured
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});

                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    await expect(signalsToggle).toBeVisible({timeout: 5_000});
                    await signalsToggle.click();
                    await page.waitForTimeout(500);

                    // Underwater Drawdown card with its Full history toggle (risk family)
                    await selectIndicatorFromTree(page, 'risk', 'risk-drawdown');
                    await waitForSignalCardsSettled(page, 45_000); // full-history load is heavier
                    const fullHistoryParam = page.getByTestId('signal-param-full_history');
                    await expect(fullHistoryParam).toBeVisible({timeout: 5_000});
                    await fullHistoryParam.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(300);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-drawdown');
                }
            }
        });

        test('Asset chart settings modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await page.waitForTimeout(1000);

                    // Global-scope chart settings from the Assets list toolbar (live preview)
                    const settingsBtn = page.getByTestId('assets-chart-settings-button');
                    await settingsBtn.scrollIntoViewIfNeeded();
                    await expect(settingsBtn).toBeVisible({timeout: 3_000});
                    await settingsBtn.click();
                    const settingsModal = page.getByTestId('chart-settings-modal');
                    await expect(settingsModal).toBeVisible({timeout: 5_000});
                    // Wait for the live preview chart to paint
                    await settingsModal
                        .locator('canvas')
                        .first()
                        .waitFor({state: 'visible', timeout: 8_000})
                        .catch(() => {});
                    await page.waitForTimeout(500);
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'chart-settings');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Asset detail event popover - all languages and themes', async ({page}, testInfo) => {
            // Mocked chart + bounded hover sweep × 8 combos — above the default budget under load.
            test.setTimeout(360_000); // 6 minutes
            const viewport = getViewport(testInfo);

            // The chart canvas gives markers no DOM handle, so make the geometry known:
            // mock the bulk price query with a gentle linear ramp and a single DIVIDEND at
            // the exact mid date → the marker sits at the grid's centre, and a small hover
            // sweep around the canvas centre hits it deterministically.
            const today = new Date();
            const dayMs = 24 * 60 * 60 * 1000;
            const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
            const days = 240; // ~8 months of daily points — comfortably "daily" resolution
            const dates: string[] = [];
            for (let i = days - 1; i >= 0; i--) dates.push(fmt(new Date(today.getTime() - i * dayMs)));
            const midDate = dates[Math.floor(dates.length / 2)];
            await page.route('**/api/v1/assets/prices/query', async (route) => {
                // The assets LIST also bulk-queries prices (per-card sparklines) before we
                // reach the detail page — answer every requested item, not just Apple's.
                // postDataJSON throws on an empty/non-JSON body; an unhandled throw leaves the
                // request pending forever and the page stuck at data-busy — fall back to [].
                let postData: Array<{asset_id?: number; target_currency?: string; include_events?: boolean}> = [];
                try {
                    postData = route.request().postDataJSON() ?? [];
                } catch {
                    postData = [];
                }
                const items = postData.map((item) => {
                    const currency = item?.target_currency ?? 'USD';
                    return {
                        asset_id: item?.asset_id ?? 0,
                        prices: dates.map((d, i) => ({date: d, close: (100 + i * 0.2).toFixed(4), currency})),
                        events: item?.include_events ? [{date: midDate, type: 'DIVIDEND', value: {code: currency, amount: '2.5000'}, notes: 'Gallery demo dividend', id: 1, is_auto: false}] : [],
                        errors: [],
                        signals: [],
                    };
                });
                await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({items})});
            });

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectMaxDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await page.waitForSelector('canvas', {timeout: 8_000});

                    const chartCard = page.getByTestId('asset-detail-chart');
                    await chartCard.evaluate((el) => el.scrollIntoView({block: 'center'}));
                    await page.waitForTimeout(500);
                    const canvas = chartCard.locator('canvas').first();
                    const box = await canvas.boundingBox();
                    if (!box) throw new Error('detail-events: chart canvas has no bounding box');

                    // Sweep a small spiral around the canvas centre until the event tooltip
                    // (item trigger on the scatter marker) appears. In headless CI the hover
                    // never lands on the marker — so after the sweep, drive ECharts directly:
                    // showTip on the scatter point instead of trusting the mouse.
                    const tooltip = chartCard.getByText('💰');
                    for (const dy of [0, -20, 20, -40, 40]) {
                        for (let dx = -80; dx <= 80; dx += 10) {
                            await page.mouse.move(box.x + box.width / 2 + dx, box.y + box.height / 2 + dy);
                            await page.waitForTimeout(80);
                            if (await tooltip.isVisible().catch(() => false)) break;
                        }
                        if (await tooltip.isVisible().catch(() => false)) break;
                    }
                    if (!(await tooltip.isVisible().catch(() => false))) {
                        // Deterministic fallback: drive the component's ECharts instance
                        // (exposed on the container as __lfChart) and showTip the first point
                        // of the "Events: …" scatter series (the mocked dividend).
                        await canvas.evaluate((el) => {
                            let node: HTMLElement | null = el as unknown as HTMLElement;
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            let chart: any = null;
                            while (node && !chart) {
                                chart = (node as any).__lfChart ?? null;
                                node = node.parentElement;
                            }
                            if (!chart) return;
                            const series = (chart.getOption().series as any[]) ?? [];
                            const idx = series.findIndex((s) => String(s?.name ?? '').startsWith('Events: '));
                            if (idx < 0) return;
                            chart.dispatchAction({type: 'showTip', seriesIndex: idx, dataIndex: 0});
                        });
                    }
                    await expect(tooltip).toBeVisible({timeout: 2_000});
                    await freezeAnimations(page);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-events');
                    // Move away to dismiss the tooltip for the next iteration
                    await page.mouse.move(box.x + 5, box.y + box.height - 5);
                    await page.waitForTimeout(150);
                }
            }
        });

        test('Asset detail measures', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await selectOneYearDateRange(page);
                    await page.waitForLoadState('networkidle', {timeout: 10_000}).catch(() => {});
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    // Toggle measures panel — screenshot 1: panel open (empty)
                    const measuresToggle = page.getByTestId('asset-detail-measures-toggle');
                    if (await measuresToggle.isVisible({timeout: 2000}).catch(() => false)) {
                        await measuresToggle.click();
                        await page.waitForTimeout(500);
                    }
                    await page.getByTestId('asset-detail-chart').scrollIntoViewIfNeeded();
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-measures');

                    // Screenshot 2: panel with a measurement added (full date range)
                    const addMeasureBtn = page.getByTestId('asset-detail-add-measure-btn');
                    if (await addMeasureBtn.isVisible({timeout: 2000}).catch(() => false)) {
                        await addMeasureBtn.click();
                        await page.waitForTimeout(800); // Wait for measurement to appear
                        await page.getByTestId('asset-detail-chart').scrollIntoViewIfNeeded();
                        await page.waitForTimeout(300);
                        await freezeAnimations(page);
                        await screenshot(page, viewport, lang, theme, 'assets', 'detail-measures-active');
                    }
                }
            }
        });

        test('Asset detail classification', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);

                    // Toggle classification (metadata) panel
                    const metadataToggle = page.getByTestId('asset-detail-metadata-toggle');
                    if (await metadataToggle.isVisible({timeout: 2000}).catch(() => false)) {
                        await metadataToggle.click();
                        await page.waitForTimeout(1000); // Wait for pie charts and map to render

                        // Scroll to classification panel
                        const metadataPanel = page.getByTestId('asset-detail-metadata-panel');
                        if (await metadataPanel.isVisible({timeout: 2000}).catch(() => false)) {
                            await metadataPanel.scrollIntoViewIfNeeded();
                            await page.waitForTimeout(500);
                        }
                    }
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-classification');
                }
            }
        });

        test('Asset detail data editor', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);

                    // Click edit data button
                    const editDataBtn = page.getByTestId('asset-detail-editdata-btn');
                    if (await editDataBtn.isVisible({timeout: 2000}).catch(() => false)) {
                        await editDataBtn.click();
                        await page.waitForTimeout(500);
                        // Scroll to editor panel
                        const editorPanel = page.getByTestId('asset-detail-editor-panel');
                        if (await editorPanel.isVisible({timeout: 2000}).catch(() => false)) {
                            await editorPanel.scrollIntoViewIfNeeded();
                            await page.waitForTimeout(300);
                        }
                    }
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-editor');
                }
            }
        });

        test('Asset create modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Open create modal
                    await page.getByTestId('assets-add-button').click();
                    await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});
                    await page.waitForTimeout(500);
                    await screenshot(page, viewport, lang, theme, 'assets', 'create-modal');
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Asset distribution editors - sector and geographic', async ({page}, testInfo) => {
            // Tesla is populated with both distributions summing to exactly 100%
            // (sector: Consumer Discretionary 70 / Energy 30 — geographic: USA 50 / CHN 25 / DEU 25),
            // so both editors render filled rows plus the green 100% total badge.
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);

                    // Search for Tesla directly: navigateToAssetByName races the filter
                    // debounce (waits data-busy=false, which is already false pre-refilter),
                    // so instead wait until the first card actually shows the search hit.
                    const searchInput = page.getByTestId('assets-search-input');
                    await expect(searchInput).toBeVisible({timeout: 10_000});
                    await searchInput.fill('Tesla');
                    const teslaCard = page.locator('[data-testid^="asset-card-"]').first();
                    await expect(teslaCard).toContainText('Tesla', {timeout: 10_000});
                    await teslaCard.click();
                    await page.waitForSelector('[data-testid="asset-detail-page"][data-busy="false"]', {timeout: 20_000});
                    await expect(page.getByTestId('asset-detail-header')).toBeVisible({timeout: 10_000});

                    // Open the edit modal — the button stays disabled until asset info
                    // and classification have loaded, so waiting for enabled is the gate.
                    const editBtn = page.getByTestId('asset-detail-edit-btn');
                    await expect(editBtn).toBeEnabled({timeout: 10_000});
                    await editBtn.click();
                    await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5_000});

                    // Expand More Info (Identifiers + Classification area)
                    const moreInfo = page.getByTestId('asset-modal-more-info');
                    if ((await moreInfo.getAttribute('data-expanded')) !== 'true') {
                        await moreInfo.click();
                    }

                    await expect(page.getByTestId('distribution-editor-sector')).toBeVisible({timeout: 5_000});
                    await expect(page.getByTestId('distribution-editor-geographic')).toBeVisible({timeout: 5_000});
                    // Populated distributions sum to 100% → totals render in the green (valid) state
                    const sectorTotal = page.getByTestId('distribution-total-sector');
                    const geoTotal = page.getByTestId('distribution-total-geographic');
                    await expect(sectorTotal).toHaveClass(/text-green-600/, {timeout: 5_000});
                    await expect(geoTotal).toHaveClass(/text-green-600/, {timeout: 5_000});
                    await freezeAnimations(page);

                    await sectorTotal.scrollIntoViewIfNeeded();
                    await page.waitForTimeout(200);
                    await screenshot(page, viewport, lang, theme, 'assets', 'distribution-editor-sector');

                    await page.getByTestId('distribution-editor-geographic').scrollIntoViewIfNeeded();
                    await page.waitForTimeout(200);
                    await screenshot(page, viewport, lang, theme, 'assets', 'distribution-editor-geographic');

                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });

        test('Asset create modal from import wizard - all languages and themes', async ({page}, testInfo) => {
            // Heavier than the default 3-min budget: full import wizard + CSV parse × 4 langs × 2 themes.
            test.setTimeout(300_000); // 5 minutes
            // Opens AssetModal from ImportWizard step4 — pre-filled with extracted ticker/ISIN/name
            // Uses generic_simple.csv which has UNETF (unresolved asset)
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                    // Open wizard from transactions import button
                    await page.getByTestId('tx-import-button').click();
                    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 8_000});

                    // Skip step 1, advance to step 2
                    await page.getByTestId('import-wizard-next').click();
                    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 8_000});
                    await page.waitForTimeout(800);

                    // Select generic_simple.csv (has UNETF - unresolved asset)
                    const step2 = page.getByTestId('import-wizard-step2');
                    const fileRow = step2.locator('tr[data-row-id]').filter({hasText: 'generic_simple.csv'}).first();
                    if (await fileRow.isVisible({timeout: 3_000}).catch(() => false)) {
                        const checkbox = fileRow.locator('td.td-select button.checkbox-btn');
                        await checkbox.scrollIntoViewIfNeeded();
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                        await checkbox.click();

                        const parseBtn = page.getByTestId('import-wizard-parse');
                        if (await parseBtn.isEnabled({timeout: 3_000}).catch(() => false)) {
                            await parseBtn.click();
                            await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 15_000});
                            await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: 30_000});
                            await page.getByTestId('import-wizard-continue').click();
                            // Handle warnings if any
                            const warningConfirm = page.getByTestId('import-wizard-warning-confirm');
                            if (await warningConfirm.isVisible({timeout: 3_000}).catch(() => false)) {
                                await warningConfirm.click();
                                await page.waitForTimeout(300);
                            }
                            await page.getByTestId('import-wizard-step4').waitFor({state: 'visible', timeout: 10_000});
                            await page.waitForTimeout(800);

                            // The resolve section defaults to expanded when there are unresolved assets.
                            // Just find the AssetSelect directly — it's inside the resolve section.
                            // Use the [role="combobox"] inside the asset-select element.
                            const assetSelect = page.getByTestId('asset-select').first();
                            if (await assetSelect.isVisible({timeout: 5_000}).catch(() => false)) {
                                // Open the search dropdown by clicking the combobox trigger
                                const combobox = assetSelect.locator('[role="combobox"], input[type="text"]').first();
                                if (await combobox.isVisible({timeout: 1_000}).catch(() => false)) {
                                    await combobox.click();
                                } else {
                                    await assetSelect.click();
                                }
                                await page.waitForTimeout(400);

                                // Click the "Create new" option in the dropdown
                                const createNewBtn = page.getByTestId('search-select-create-new');
                                if (await createNewBtn.isVisible({timeout: 2_000}).catch(() => false)) {
                                    await createNewBtn.click();
                                    // AssetModal opens pre-filled with extracted ticker/ISIN/name
                                    const assetModal = page.getByTestId('asset-modal-form');
                                    if (await assetModal.isVisible({timeout: 5_000}).catch(() => false)) {
                                        await waitForNetworkSettled(page);
                                        await page.waitForTimeout(500);
                                        await freezeAnimations(page);
                                        await screenshot(page, viewport, lang, theme, 'assets', 'create-wizard-modal');
                                        await page.keyboard.press('Escape');
                                        await page.waitForTimeout(200);
                                        // Close any confirm dialog
                                        const confirmClose = page.getByTestId('confirm-modal-confirm');
                                        if (await confirmClose.isVisible({timeout: 500}).catch(() => false)) {
                                            await confirmClose.click();
                                            await page.waitForTimeout(200);
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Close all wizard/bulk modals
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(300);
                    const confirmDiscard = page.getByTestId('confirm-modal-confirm');
                    if (await confirmDiscard.isVisible({timeout: 500}).catch(() => false)) {
                        await confirmDiscard.click();
                        await page.waitForTimeout(200);
                    }
                    await page.keyboard.press('Escape');
                    await page.waitForTimeout(200);
                }
            }
        });
    });
});
