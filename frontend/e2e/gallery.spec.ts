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
import {expect, Page, test} from '@playwright/test';
import {login, logout, navigateTo, setLanguage} from './fixtures/auth-helpers';
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
    test.setTimeout(180_000); // 3 minutes per test

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
    });

    test.describe('Dashboard', () => {
        test.beforeEach(async ({page}) => {
            // Use TEST_ADMIN since db populate assigns brokers to admin
            await login(page, TEST_ADMIN);
        });

        test('main dashboard - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'main');
            });
        });

        test('mobile menu open', async ({page}, testInfo) => {
            if (testInfo.project.name !== 'mobile') {
                test.skip();
                return;
            }

            const menuToggle = page.getByTestId('mobile-menu-toggle');

            // Take screenshot for each language and theme
            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // Navigate fresh to dashboard for each combo (ensures clean state)
                    await page.goto('/dashboard');
                    await page.waitForLoadState('networkidle');
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

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle');
                await freezeAnimations(page);
                // Scroll to the allocation panel
                const allocPanel = page.getByTestId('allocation-panel');
                if (await allocPanel.isVisible({timeout: 5_000}).catch(() => false)) {
                    await allocPanel.scrollIntoViewIfNeeded();
                    await waitForNetworkSettled(page);
                    await page.waitForTimeout(800); // Extra time for ECharts render
                }
                await screenshot(page, viewport, lang, theme, 'dashboard', 'allocation-charts');
                // Scroll back to top so next iteration starts clean
                await page.evaluate(() => window.scrollTo(0, 0));
            });
        });

        test('dashboard empty state - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            // Logout TEST_ADMIN (from beforeEach) and switch to empty user
            await logout(page);
            await login(page, TEST_EMPTY);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'dashboard', 'empty-state');
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
                await page.waitForLoadState('networkidle');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'files', 'static-tab');
            });
        });

        test('broker reports tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/files?tab=brim');
                await page.waitForLoadState('networkidle');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'files', 'brim-tab');
            });
        });

        test('static resources grid view - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await page.goto('/files?tab=static');
                await page.waitForLoadState('networkidle');
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
                    await page.waitForLoadState('networkidle');
                    await freezeAnimations(page);
                    await page.waitForTimeout(500);

                    // Click the preview action on the first BRIM file row
                    const previewBtn = page.locator('[data-testid="files-table-brim"] [data-testid="row-action-preview"]').first();
                    if (await previewBtn.isVisible({timeout: 3_000}).catch(() => false)) {
                        await previewBtn.click();
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
                        await page.waitForLoadState('networkidle');
                        await freezeAnimations(page);
                        await page.waitForTimeout(500);

                        // Find first row with a preview button
                        const table = page.locator('[data-testid="files-table-static"]');
                        const firstPreviewBtn = table.locator('[data-testid="row-action-preview"]').first();
                        if (await firstPreviewBtn.isVisible({timeout: 3_000}).catch(() => false)) {
                            await firstPreviewBtn.click();
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

        test('transaction form modal variants - all languages and themes', async ({page}, testInfo) => {
            // Screenshots for different transaction types in the form modal
            const viewport = getViewport(testInfo);
            const typesToShoot: Array<{type: string; name: string}> = [
                {type: 'SELL', name: 'form-modal-sell'},
                {type: 'DIVIDEND', name: 'form-modal-dividend'},
                {type: 'DEPOSIT', name: 'form-modal-deposit'},
                {type: 'TRANSFER', name: 'form-modal-transfer'},
                {type: 'FX_CONVERSION', name: 'form-modal-fxconversion'},
            ];

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    for (const {type, name} of typesToShoot) {
                        await navigateTo(page, '/transactions');
                        await setLanguage(page, lang);
                        await setTheme(page, theme);
                        await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});

                        // Open Add form
                        await page.getByTestId('tx-add-button').click();
                        const formModal = page.getByTestId('tx-form-modal');
                        await expect(formModal).toBeVisible({timeout: 8_000});
                        await waitForNetworkSettled(page);
                        await page.waitForTimeout(200);

                        // Change type via the type search-select:
                        // SearchSelect shows input INSIDE the open dropdown, not inline.
                        // 1) Click the combobox trigger to open dropdown
                        // 2) Click the specific option by testid
                        const typeCombobox = page.locator('[data-testid="tx-form-type"] [role="combobox"]');
                        if (await typeCombobox.isVisible({timeout: 2_000}).catch(() => false)) {
                            await typeCombobox.click();
                            await page.waitForTimeout(400);
                            const option = page.locator(`[data-testid="search-select-option-${type}"]`);
                            if (await option.isVisible({timeout: 2_000}).catch(() => false)) {
                                await option.click();
                                await waitForNetworkSettled(page);
                                await page.waitForTimeout(400);
                            }
                        }
                        await freezeAnimations(page);
                        await screenshot(page, viewport, lang, theme, 'transactions', name);

                        // Close form
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                        const discardBtn = page.getByTestId('confirm-modal-confirm');
                        if (await discardBtn.isVisible({timeout: 500}).catch(() => false)) {
                            await discardBtn.click();
                            await page.waitForTimeout(200);
                        }
                    }
                }
            }
        });

        test('transaction picker modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await navigateTo(page, '/transactions');
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
                    await freezeAnimations(page);

                    // Open BulkModal by hovering the first row and clicking edit
                    const firstRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first();
                    await expect(firstRow).toBeVisible({timeout: 5_000});
                    await firstRow.hover();
                    await page.waitForTimeout(200);
                    const editAction = firstRow.locator('button[data-action-id="edit"]');
                    if (await editAction.isVisible({timeout: 2_000}).catch(() => false)) {
                        await editAction.click();
                        // BulkModal or FormModal opens — wait for BulkModal
                        const bulkModal = page.locator('[data-testid="tx-bulk-modal-root"]');
                        if (await bulkModal.isVisible({timeout: 5_000}).catch(() => false)) {
                            // Close any nested FormModal first
                            const formClose = page.getByTestId('tx-form-close');
                            if (await formClose.isVisible({timeout: 1_000}).catch(() => false)) {
                                await formClose.click();
                                await page.waitForTimeout(200);
                            }
                            // Open the TransactionPickerModal
                            const pickerBtn = page.getByTestId('tx-bulk-picker');
                            if (await pickerBtn.isVisible({timeout: 3_000}).catch(() => false)) {
                                await pickerBtn.click();
                                const pickerModal = page.getByTestId('tx-picker-modal');
                                await expect(pickerModal).toBeVisible({timeout: 5_000});
                                await waitForNetworkSettled(page);
                                await page.waitForTimeout(300);
                                await screenshot(page, viewport, lang, theme, 'transactions', 'picker-modal');
                                await page.keyboard.press('Escape');
                                await page.waitForTimeout(200);
                            }
                        }
                    }
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

                    // Find a paired TX row that has a split action
                    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
                    const rowCount = await rows.count();
                    let found = false;
                    for (let i = 0; i < Math.min(rowCount, 30) && !found; i++) {
                        const row = rows.nth(i);
                        await row.hover();
                        await page.waitForTimeout(150);
                        const splitBtn = row.locator('button[data-action-id="split"]');
                        if (await splitBtn.isVisible({timeout: 500}).catch(() => false)) {
                            await splitBtn.click();
                            const actionModal = page.getByTestId('tx-action-modal');
                            if (await actionModal.isVisible({timeout: 3_000}).catch(() => false)) {
                                await page.waitForTimeout(300);
                                await screenshot(page, viewport, lang, theme, 'transactions', 'action-modal');
                                await page.getByTestId('tx-action-modal-cancel').click();
                                await page.waitForTimeout(200);
                                found = true;
                            }
                        }
                    }
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

                    // Find a linked pair TX (rebalance tag indicates TRANSFER pairs)
                    const rows = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]');
                    const rowCount = await rows.count();
                    let found = false;

                    for (let i = 0; i < Math.min(rowCount, 50) && !found; i++) {
                        const row = rows.nth(i);
                        const text = (await row.textContent()) ?? '';
                        // Look for a transfer or fx-conversion with known tag or description
                        if (text.includes('rebalance') || text.includes('TRANSFER') || text.includes('Transfer')) {
                            await row.hover();
                            await page.waitForTimeout(150);
                            const deleteBtn = row.locator('button.action-btn.danger');
                            if (await deleteBtn.isVisible({timeout: 500}).catch(() => false)) {
                                await deleteBtn.click();
                                const deleteModal = page.getByTestId('tx-delete-modal');
                                if (await deleteModal.isVisible({timeout: 3_000}).catch(() => false)) {
                                    // Check if it's the linked layout (shows From/To)
                                    const isLinked = await deleteModal.locator('[data-testid="tx-delete-paired-details"]').isVisible({timeout: 1_000}).catch(() => false);
                                    if (isLinked) {
                                        await page.waitForTimeout(300);
                                        await screenshot(page, viewport, lang, theme, 'transactions', 'bulk-delete-pair-modal');
                                        found = true;
                                    }
                                    await deleteModal.getByTestId('tx-delete-modal-cancel').click();
                                    await page.waitForTimeout(200);
                                }
                            }
                        }
                    }
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
                    await page.waitForLoadState('networkidle');
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
                    await page.waitForLoadState('networkidle');
                    await page.waitForTimeout(500);

                    // Scroll to and click import files button
                    const importBtn = page.getByTestId('import-files-button');
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

                            // Continue to step 4
                            await page.getByTestId('import-wizard-continue').click();
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
            // ibkr-trades-export.csv was already uploaded; if the DB has matching transactions
            // from populate_mock_data, they'll be flagged as likely-duplicate in step 4.
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

                    // Select ibkr-trades-export.csv
                    const step2 = page.getByTestId('import-wizard-step2');
                    const fileRow = step2.locator('tr[data-row-id]').filter({hasText: 'ibkr-trades-export.csv'}).first();
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

                    // Open BulkModal via edit action on the first row
                    const firstRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first();
                    await firstRow.hover();
                    await page.waitForTimeout(200);
                    const editAction = firstRow.locator('button[data-action-id="edit"]');
                    if (await editAction.isVisible({timeout: 2_000}).catch(() => false)) {
                        await editAction.click();
                        // BulkModal opens
                        const bulkModal = page.locator('[data-testid="tx-bulk-modal-root"]');
                        if (await bulkModal.isVisible({timeout: 6_000}).catch(() => false)) {
                            // Close any auto-opened FormModal
                            const formClose = page.getByTestId('tx-form-close');
                            if (await formClose.isVisible({timeout: 1_000}).catch(() => false)) {
                                await formClose.click();
                                await page.waitForTimeout(200);
                            }
                            await page.waitForTimeout(300);
                            await screenshot(page, viewport, lang, theme, 'brokers', 'import-bulk-staging');
                        }
                    }

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
                    await page.waitForLoadState('networkidle');
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
                    await page.waitForLoadState('networkidle');
                    await page.waitForTimeout(300);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);
                    await page.waitForTimeout(500);

                    const card = page.locator('[data-testid^="broker-card-"]').first();
                    if (await card.isVisible({timeout: 2000}).catch(() => false)) {
                        await card.click();
                        await page.waitForLoadState('networkidle');
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
                    await page.waitForLoadState('networkidle');
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

        test('broker sharing modal', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    // Navigate to brokers page
                    await navigateTo(page, '/brokers');
                    await page.waitForLoadState('networkidle');
                    await page.waitForTimeout(300);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    // Click Coinbase broker (5th card, index 4) for rich multi-user demo
                    const brokerCards = page.locator('[data-testid^="broker-card-"]');
                    const coinbaseCard = brokerCards.nth(0); // Coinbase is the 5th broker
                    if (await coinbaseCard.isVisible({timeout: 3000}).catch(() => false)) {
                        await coinbaseCard.click();
                        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 5000});
                        await page.waitForTimeout(300);

                        // Click Share button (only visible for OWNER)
                        const shareBtn = page.getByTestId('broker-share-button');
                        if (await shareBtn.isVisible({timeout: 2000}).catch(() => false)) {
                            await shareBtn.click();
                            await expect(page.getByTestId('broker-sharing-modal')).toBeVisible({timeout: 3000});
                            await page.waitForTimeout(500); // Wait for chart to render

                            await screenshot(page, viewport, lang, theme, 'brokers', 'sharing-modal');

                            // Close modal
                            await page.keyboard.press('Escape');
                            await page.waitForTimeout(200);
                        }
                    }
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
                await freezeAnimations(page);
                // Wait for charts (canvas) to render
                await page.waitForTimeout(2000);
                await screenshot(page, viewport, lang, theme, 'fx', 'list');
            });
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
                    await modal.locator('[data-testid^="fx-route-chain-section"]').first().waitFor({state: 'visible', timeout: 5000});
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
                await freezeAnimations(page);
                await page.waitForTimeout(1500);
                await screenshot(page, viewport, lang, theme, 'assets', 'list');
            });
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
                    await page.waitForTimeout(500);
                    await screenshot(page, viewport, lang, theme, 'assets', 'detail-chart');
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
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    // Open signals panel and add EMA indicator
                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    if (await signalsToggle.isVisible({timeout: 2000}).catch(() => false)) {
                        await signalsToggle.click();
                        await page.waitForTimeout(500);

                        // Select EMA from the indicator dropdown
                        const indicatorSelect = page.getByTestId('signals-indicator-select-button');
                        if (await indicatorSelect.isVisible({timeout: 2000}).catch(() => false)) {
                            await indicatorSelect.click();
                            await page.waitForTimeout(300);
                            // SimpleSelect options use role="menuitem"
                            const emaOption = page.locator('[role="menuitem"]').filter({hasText: /EMA/i}).first();
                            if (await emaOption.isVisible({timeout: 1000}).catch(() => false)) {
                                await emaOption.click();
                                await page.waitForTimeout(1500); // Wait for EMA to render on chart
                                // Scroll to chart to center it in viewport
                                await page.getByTestId('asset-detail-chart').scrollIntoViewIfNeeded();
                                await page.waitForTimeout(300);
                                await freezeAnimations(page);
                                await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-ema');
                            }
                        }
                    }
                }
            }
        });

        test('Asset detail signals RSI - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    if (await signalsToggle.isVisible({timeout: 2000}).catch(() => false)) {
                        await signalsToggle.click();
                        await page.waitForTimeout(500);

                        const indicatorSelect = page.getByTestId('signals-indicator-select-button');
                        if (await indicatorSelect.isVisible({timeout: 2000}).catch(() => false)) {
                            await indicatorSelect.click();
                            await page.waitForTimeout(300);
                            const rsiOption = page.locator('[role="menuitem"]').filter({hasText: /RSI/i}).first();
                            if (await rsiOption.isVisible({timeout: 1000}).catch(() => false)) {
                                await rsiOption.click();
                                await page.waitForTimeout(1500);
                                await page.getByTestId('asset-detail-chart').scrollIntoViewIfNeeded();
                                await page.waitForTimeout(300);
                                await freezeAnimations(page);
                                await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-rsi');
                            }
                        }
                    }
                }
            }
        });

        test('Asset detail signals MACD - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const lang of SUPPORTED_LANGUAGES) {
                for (const theme of THEMES) {
                    await goToAssetsPage(page);
                    await setLanguage(page, lang);
                    await setTheme(page, theme);
                    await freezeAnimations(page);

                    await navigateToAssetByName(page, GALLERY_ASSET);
                    await page.waitForSelector('canvas', {timeout: 5000}).catch(() => null);
                    await page.waitForTimeout(1000);

                    const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
                    if (await signalsToggle.isVisible({timeout: 2000}).catch(() => false)) {
                        await signalsToggle.click();
                        await page.waitForTimeout(500);

                        const indicatorSelect = page.getByTestId('signals-indicator-select-button');
                        if (await indicatorSelect.isVisible({timeout: 2000}).catch(() => false)) {
                            await indicatorSelect.click();
                            await page.waitForTimeout(300);
                            const macdOption = page.locator('[role="menuitem"]').filter({hasText: /MACD/i}).first();
                            if (await macdOption.isVisible({timeout: 1000}).catch(() => false)) {
                                await macdOption.click();
                                await page.waitForTimeout(1500);
                                await page.getByTestId('asset-detail-chart').scrollIntoViewIfNeeded();
                                await page.waitForTimeout(300);
                                await freezeAnimations(page);
                                await screenshot(page, viewport, lang, theme, 'assets', 'detail-signals-macd');
                            }
                        }
                    }
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

        test('Asset create modal from import wizard - all languages and themes', async ({page}, testInfo) => {
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
