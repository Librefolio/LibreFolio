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
import {login, navigateTo, setLanguage} from './fixtures/auth-helpers';
import {type Language, SUPPORTED_LANGUAGES, TEST_ADMIN} from './fixtures/test-users';
import * as path from 'path';
import * as fs from 'fs';
import {fileURLToPath} from 'url';

// ES module compatibility for __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GALLERY_ROOT = path.join(__dirname, '../../mkdocs_src/docs/gallery');
const THEMES = ['light', 'dark'] as const;
type Theme = typeof THEMES[number];

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
        `
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

async function screenshot(
    page: Page,
    viewport: 'desktop' | 'mobile',
    lang: Language,
    theme: Theme,
    category: string,
    name: string
) {
    const dir = getGalleryPath(viewport, lang, theme, category);
    ensureDir(dir);
    await page.screenshot({
        path: path.join(dir, `${name}.png`),
        fullPage: false
    });
    console.log(`  📸 ${viewport}/${lang}/${theme}/${category}/${name}.png`);
}

// Helper to run for all languages and themes
async function forEachLanguageAndTheme(
    page: Page,
    callback: (lang: Language, theme: Theme) => Promise<void>
) {
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
    });

    test.describe('Settings', () => {
        test('user preferences - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, theme, 'settings', 'user-preferences');
            });
        });

        test('global settings (admin) - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await freezeAnimations(page);
                await page.getByTestId('settings-tab-admin').click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, theme, 'settings', 'global-settings');
            });
        });

        test('about tab - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
                await freezeAnimations(page);
                await page.getByTestId('settings-tab-about').click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, theme, 'settings', 'about');
            });
        });

        test('password change modal - all languages and themes', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);

            await forEachLanguageAndTheme(page, async (lang, theme) => {
                await navigateTo(page, '/settings');
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
                await freezeAnimations(page);
                const profileTab = page.locator('[data-testid="settings-tab-profile"], [role="tab"]', {hasText: /profile/i}).first();
                if (await profileTab.isVisible().catch(() => false)) {
                    await profileTab.click();
                    await page.waitForTimeout(300);
                    await screenshot(page, viewport, lang, theme, 'settings', 'profile');
                }
            });
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
                    await page.waitForTimeout(500);
                    await screenshot(page, viewport, lang, theme, 'files', 'static-grid');
                }
            });
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
                await freezeAnimations(page);
                // Wait for broker icons to load (favicon fetching)
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
    });

    test.describe('Media & Upload', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
        });

        test('image edit modal - crop view', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const theme of THEMES) {
                // Navigate fresh each time to avoid leftover modal state
                await navigateTo(page, '/files');
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

                await screenshot(page, viewport, 'en', theme, 'media', 'image-edit-modal');
            }
        });

        test('asset picker modal - existing files', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            // Go to brokers, open first broker, click icon to open AssetPickerModal
            await navigateTo(page, '/brokers');
            await page.waitForTimeout(500);

            for (const theme of THEMES) {
                await setTheme(page, theme);
                await freezeAnimations(page);

                const card = page.locator('[data-testid^="broker-card-"]').first();
                if (await card.isVisible({timeout: 2000}).catch(() => false)) {
                    await card.click();
                    await page.waitForLoadState('networkidle');
                    await page.waitForTimeout(500);

                    // Click edit button to open BrokerModal
                    const editBtn = page.getByTestId('edit-broker-button');
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
                                await page.waitForTimeout(500);
                                await screenshot(page, viewport, 'en', theme, 'media', 'asset-picker-modal');
                                await page.keyboard.press('Escape');
                                await page.waitForTimeout(200);
                            }
                        }

                        // Close broker modal
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(200);
                    }

                    // Go back to brokers list
                    await navigateTo(page, '/brokers');
                    await page.waitForTimeout(300);
                }
            }
        });

        test('file upload with pending files', async ({page}, testInfo) => {
            const viewport = getViewport(testInfo);

            for (const theme of THEMES) {
                await navigateTo(page, '/files');
                await page.getByTestId('files-tab-static').click();
                await page.waitForTimeout(300);
                await setTheme(page, theme);
                await freezeAnimations(page);

                // Open upload area
                await page.getByTestId('upload-button').click();
                await expect(page.getByTestId('file-uploader')).toBeVisible({timeout: 3000});
                await page.waitForTimeout(300);

                await screenshot(page, viewport, 'en', theme, 'media', 'file-uploader-empty');
            }
        });
    });
});
