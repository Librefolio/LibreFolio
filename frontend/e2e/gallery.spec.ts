/**
 * Gallery Screenshot Generator
 * 
 * Generates consistent screenshots for mkdocs documentation.
 * NOT included in normal test runs - run separately with:
 *   ./dev.py mkdocs gallery
 * 
 * Screenshots saved to: mkdocs_src/docs/gallery/{desktop|mobile}/{lang}/...
 */
import { test, Page } from '@playwright/test';
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
    
    test.describe('Auth Pages', () => {
        test('login page - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            
            await forEachLanguage(page, async (lang) => {
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, 'auth', 'login');
            });
        });

        test('register modal - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await page.goto('/');
            
            await forEachLanguage(page, async (lang) => {
                await page.getByRole('button', { name: /register|sign up|registrati/i }).click();
                await page.waitForTimeout(300);
                await screenshot(page, viewport, lang, 'auth', 'register-modal');
                // Close modal
                await page.keyboard.press('Escape');
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
                await screenshot(page, viewport, lang, 'settings', 'user-preferences');
            });
        });

        test('global settings (admin) - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            await login(page, TEST_ADMIN);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/settings');
                await page.getByRole('tab', { name: /global/i }).click();
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
                await screenshot(page, viewport, lang, 'files', 'static-tab');
            });
        });

        test('broker reports tab - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await page.goto('/files?tab=brim');
                await page.waitForLoadState('networkidle');
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
                await screenshot(page, viewport, lang, 'brokers', 'list');
            });
        });

        test('broker detail - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/brokers');
                const card = page.getByTestId('broker-card').first();
                if (await card.isVisible()) {
                    await card.click();
                    await page.waitForLoadState('networkidle');
                    await screenshot(page, viewport, lang, 'brokers', 'detail');
                }
            });
        });

        test('import modal - all languages', async ({ page }, testInfo) => {
            const viewport = getViewport(testInfo);
            
            await forEachLanguage(page, async (lang) => {
                await navigateTo(page, '/brokers');
                const card = page.getByTestId('broker-card').first();
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
