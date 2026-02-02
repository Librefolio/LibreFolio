/**
 * Gallery Screenshot Generator
 * 
 * Generates consistent screenshots for mkdocs documentation.
 * NOT included in normal test runs - run separately with:
 *   ./dev.py mkdocs gallery
 * 
 * Screenshots saved to: mkdocs_src/docs/gallery/{desktop|mobile}/{lang}/...
 *
 * Prerequisites:
 *   - Run `./dev.py db populate --force` before generating gallery
 *   - This ensures brokers with icons exist for realistic screenshots
 */
import { test, expect, Page } from '@playwright/test';
import { login, setLanguage, navigateTo, openMobileMenu } from './fixtures/auth-helpers';
import { TEST_USER, TEST_ADMIN, SUPPORTED_LANGUAGES, type Language } from './fixtures/test-users';
import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';

// ES module compatibility for __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GALLERY_ROOT = path.join(__dirname, '../../mkdocs_src/docs/gallery');

function ensureDir(dir: string) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

function getGalleryPath(viewport: 'desktop' | 'mobile', lang: Language, category: string): string {
    return path.join(GALLERY_ROOT, viewport, lang, category);
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

async function screenshot(
    page: Page, 
    viewport: 'desktop' | 'mobile',
    lang: Language, 
    category: string, 
    name: string
) {
    const dir = getGalleryPath(viewport, lang, category);
    ensureDir(dir);
    await page.screenshot({ 
        path: path.join(dir, `${name}.png`),
        fullPage: false 
    });
    console.log(`  📸 ${viewport}/${lang}/${category}/${name}.png`);
}

// Helper to run for all languages
async function forEachLanguage(
    page: Page,
    callback: (lang: Language) => Promise<void>
) {
    for (const lang of SUPPORTED_LANGUAGES) {
        await setLanguage(page, lang);
        await callback(lang);
    }
}

// Determine viewport from project name
function getViewport(testInfo: any): 'desktop' | 'mobile' {
    return testInfo.project.name === 'mobile' ? 'mobile' : 'desktop';
}

test.describe('Gallery Screenshots', () => {
    
    // Freeze animations for all tests in this suite
    test.beforeEach(async ({ page }) => {
        // Will be applied after navigation in each test
    });

    test.describe('Auth Pages', () => {
        test('login page - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await freezeAnimations(page);

            await forEachLanguage(page, async (lang) => {
                await page.waitForTimeout(100);
                await screenshot(page, viewport, lang, 'auth', '01-login');
            });
        });

        test('register modal - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await freezeAnimations(page);

            await forEachLanguage(page, async (lang) => {
                await expect(page.getByTestId('login-modal')).toBeVisible({ timeout: 3000 });
                await page.getByTestId('goto-register').click();
                await expect(page.getByTestId('register-modal')).toBeVisible({ timeout: 3000 });
                await page.waitForTimeout(200);
                await screenshot(page, viewport, lang, 'auth', '02-register-empty');

                // Go back to login for next iteration
                await page.getByTestId('goto-login').click();
                await expect(page.getByTestId('login-modal')).toBeVisible({ timeout: 3000 });
            });
        });

        test('register with password strength - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 3000 });
            await freezeAnimations(page);

            await forEachLanguage(page, async (lang) => {
                await expect(page.getByTestId('login-modal')).toBeVisible({ timeout: 3000 });
                await page.getByTestId('goto-register').click();
                await expect(page.getByTestId('register-modal')).toBeVisible({ timeout: 3000 });

                // Fill form with sample data to show password strength
                await page.getByTestId('register-username').fill('demo_user');
                await page.getByTestId('register-email').fill('demo@example.com');
                // Find password input within register modal
                await page.getByTestId('register-modal').locator('input[type="password"]').first().fill('MyStr0ng!Pass');
                await page.waitForTimeout(500); // Let password strength meter update

                await screenshot(page, viewport, lang, 'auth', '03-register-filled');

                // Go back to login for next iteration
                await page.getByTestId('goto-login').click();
                await expect(page.getByTestId('login-modal')).toBeVisible({ timeout: 3000 });
            });
        });
    });

    test.describe('Dashboard', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
        });

        test('main dashboard - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/dashboard');
                await page.waitForLoadState('networkidle');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, 'dashboard', 'main');
            });
        });

        test('mobile menu open', async ({ page }, testInfo) => {
            if (testInfo.project.name !== 'mobile') {
                test.skip();
                return;
            }
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/dashboard');
                await freezeAnimations(page);
                await openMobileMenu(page);
                await screenshot(page, 'mobile', lang, 'dashboard', 'menu-open');
            });
        });
    });

    test.describe('Settings', () => {
        test('user preferences - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_USER);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/settings');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, 'settings', 'user-preferences');
            });
        });

        test('global settings (admin) - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/settings');
                await freezeAnimations(page);
                await page.getByTestId('settings-tab-admin').click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, 'settings', 'global-settings');
            });
        });
    });

    test.describe('Files', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
        });

        test('static resources tab - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/files?tab=static');
                await page.waitForLoadState('networkidle');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, 'files', 'static-tab');
            });
        });

        test('broker reports tab - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/files?tab=brim');
                await page.waitForLoadState('networkidle');
                await freezeAnimations(page);
                await screenshot(page, viewport, lang, 'files', 'brim-tab');
            });
        });
    });

    test.describe('Brokers', () => {
        test.beforeEach(async ({ page }) => {
            await login(page, TEST_USER);
        });

        test('broker list - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/brokers');
                await freezeAnimations(page);
                // Wait for broker icons to load (favicon fetching)
                await page.waitForTimeout(2000);
                await screenshot(page, viewport, lang, 'brokers', 'list');
            });
        });

        test('broker detail - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/brokers');
                await freezeAnimations(page);
                const card = page.locator('[data-testid^="broker-card-"]').first();
                if (await card.isVisible()) {
                    await card.click();
                    await page.waitForLoadState('networkidle');
                    // Wait for broker icon to load
                    await page.waitForTimeout(1000);
                    await screenshot(page, viewport, lang, 'brokers', 'detail');
                }
            });
        });

        test('import modal - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/brokers');
                await freezeAnimations(page);
                const card = page.locator('[data-testid^="broker-card-"]').first();
                if (await card.isVisible()) {
                    await card.click();
                    const btn = page.getByRole('button', { name: /import/i });
                    if (await btn.isVisible()) {
                        await btn.click();
                        await page.waitForTimeout(300);
                        await screenshot(page, viewport, lang, 'brokers', 'import-modal');
                        await page.keyboard.press('Escape');
                    }
                }
            });
        });
    });
});
