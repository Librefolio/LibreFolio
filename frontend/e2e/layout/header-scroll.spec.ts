/**
 * Browser-only complement to Header.test.ts: actual sticky positioning,
 * transform endpoints, retained document flow and reduced-motion CSS.
 * The runner's desktop AND mobile projects run both cases. No seeded user,
 * financial fixture, database mutation or third-party request is involved.
 */
import {test as base, expect} from '../fixtures/playwright';
import type {Locator, Page} from '../fixtures/playwright';

const GEOMETRY_ID = 'review-header-geometry';
const NESTED_ID = 'review-header-nested-scroll';

const test = base.extend<{reviewHeader: Page}>({
    reviewHeader: async ({page, baseURL}, use) => {
        if (!baseURL) throw new Error('Header geometry requires the runner-provided app baseURL');
        const origin = new URL(baseURL).origin;
        // Auth is deliberately intercepted, not performed with hard-coded
        // credentials. The real protected layout and Header still mount.
        const responses = new Map<string, unknown>([
            [
                '/api/v1/auth/me',
                {
                    user: {
                        id: 876543,
                        username: 'review-header-owned',
                        email: 'review-header@example.invalid',
                        is_active: true,
                        is_superuser: false,
                        created_at: '2024-03-15T12:00:00Z',
                    },
                },
            ],
            ['/api/v1/settings/user', {language: 'en', base_currency: 'EUR', theme: 'light', avatar_url: null}],
            ['/api/v1/settings/global', {items: []}],
        ]);
        const unexpectedRequests: string[] = [];
        const handler: Parameters<Page['route']>[1] = async (route) => {
            const request = route.request();
            const url = new URL(request.url());
            if (url.origin !== origin) {
                unexpectedRequests.push(`${request.method()} ${url.origin}${url.pathname}`);
                await route.abort('blockedbyclient');
                return;
            }
            if (!url.pathname.startsWith('/api/')) {
                await route.continue();
                return;
            }
            const path = url.pathname.replace(/\/$/, '');
            if (request.method() !== 'GET' || !responses.has(path)) {
                unexpectedRequests.push(`${request.method()} ${path}`);
                await route.fulfill({status: 501, json: {detail: 'Unowned request in header geometry fixture'}});
                return;
            }
            await route.fulfill({status: 200, json: responses.get(path)});
        };
        await page.route('**/*', handler);
        try {
            await page.goto('/settings');
            await expect(page.getByTestId('settings-page')).toBeVisible({timeout: 10_000});
            await expect(page.getByTestId('app-header')).toHaveAttribute('data-scroll-state', 'visible');
            await page.evaluate(
                async ({geometryId, nestedId}) => {
                    await document.fonts.ready;
                    const main = document.querySelector('main');
                    if (!main) throw new Error('Protected layout did not publish its main content');
                    const spacer = document.createElement('section');
                    spacer.dataset.testid = geometryId;
                    spacer.style.height = '300vh';
                    const nested = document.createElement('div');
                    nested.dataset.testid = nestedId;
                    nested.style.height = '100px';
                    nested.style.overflow = 'auto';
                    const filler = document.createElement('div');
                    filler.style.height = '800px';
                    nested.append(filler);
                    spacer.append(nested);
                    main.append(spacer);

                    // A browser measurement barrier, not an elapsed-time guess:
                    // complete the initial layout/ResizeObserver delivery before
                    // exercising the separate scroll-frame state machine.
                    const header = document.querySelector('[data-testid="app-header"]');
                    if (!header) throw new Error('Header absent after settings mounted');
                    await new Promise<void>((resolve) => {
                        const observer = new ResizeObserver(() => {
                            observer.disconnect();
                            resolve();
                        });
                        observer.observe(header);
                    });
                },
                {geometryId: GEOMETRY_ID, nestedId: NESTED_ID},
            );
            await use(page);
            expect(unexpectedRequests, 'All data is synthetic; unexpected APIs must not reach the shared backend').toEqual([]);
        } finally {
            await page.evaluate((id) => document.querySelector(`[data-testid="${id}"]`)?.remove(), GEOMETRY_ID);
            await page.unroute('**/*', handler);
        }
    },
});

// A service worker must not serve cached responses outside the owned route
// boundary. This is local to this spec; the shared Playwright config is untouched.
test.use({serviceWorkers: 'block'});

async function documentY(page: Page) {
    return page.evaluate(() => window.scrollY);
}

async function scrollDocument(page: Page, y: number) {
    await page.evaluate((top) => window.scrollTo({top, behavior: 'instant'}), y);
    await expect.poll(() => documentY(page), {timeout: 5_000}).toBe(y);
}

async function documentMainTop(page: Page) {
    return page.locator('main').evaluate((main) => main.getBoundingClientRect().top + window.scrollY);
}

async function expectAtTop(header: Locator) {
    await expect.poll(() => header.evaluate((el) => Math.abs(el.getBoundingClientRect().top)), {timeout: 5_000}).toBeLessThan(0.75);
}

for (const reducedMotion of ['no-preference', 'reduce'] as const) {
    test(`header retains flow and scroll visibility with motion=${reducedMotion}`, async ({reviewHeader: page}) => {
        await page.emulateMedia({reducedMotion});
        const header = page.getByTestId('app-header');
        await scrollDocument(page, 0);
        await expect(header).toHaveAttribute('data-scroll-state', 'visible');
        await expectAtTop(header);
        const height = await header.evaluate((el) => el.getBoundingClientRect().height);
        expect(height).toBeGreaterThan(0);
        const mainTop = await documentMainTop(page);
        const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
        const nested = page.getByTestId(NESTED_ID);
        await expect(nested).toBeAttached();
        expect(await nested.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
        await nested.evaluate((el) => {
            el.scrollTop = 80;
        });
        await expect.poll(() => nested.evaluate((el) => el.scrollTop)).toBe(80);
        expect(await documentY(page)).toBe(0);
        await expect(header).toHaveAttribute('data-scroll-state', 'visible');

        const down = Math.ceil(height) + 100;
        await scrollDocument(page, down);
        await expect(header).toHaveAttribute('data-scroll-state', 'hidden');
        // `toBeVisible` alone is wrong here: a translated off-screen element
        // still has a non-empty bounding box. Assert the viewport endpoint.
        await expect.poll(() => header.evaluate((el) => el.getBoundingClientRect().bottom), {timeout: 5_000}).toBeLessThanOrEqual(0.75);
        expect(await header.evaluate((el) => el.getBoundingClientRect().height)).toBeCloseTo(height, 3);
        expect(await documentMainTop(page)).toBeCloseTo(mainTop, 3);
        expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(scrollHeight);

        await scrollDocument(page, down - 4);
        await expect(header).toHaveAttribute('data-scroll-state', 'visible');
        await expectAtTop(header);
        expect(await documentMainTop(page)).toBeCloseTo(mainTop, 3);

        // A real hit-testable control is the positive barrier for menu pinning.
        const help = header.getByTestId('help-menu-button');
        await expect(help).toBeVisible();
        await help.click();
        await expect(page.getByTestId('help-menu-panel')).toBeVisible();
        await expect(header).toHaveAttribute('data-scroll-state', 'pinned');
        await scrollDocument(page, down + 100);
        await expectAtTop(header);
        await expect(header).toHaveAttribute('data-help-menu-open', 'true');
        await help.click();
        await expect(page.getByTestId('help-menu-panel')).toBeHidden();
        // Closing a menu does not release focus. Move focus outside explicitly.
        await page.getByTestId(GEOMETRY_ID).evaluate((el) => {
            (el as HTMLElement).tabIndex = -1;
            (el as HTMLElement).focus({preventScroll: true});
        });
        await expect(header).toHaveAttribute('data-scroll-state', 'visible');
        await scrollDocument(page, down + 108);
        await expect(header).toHaveAttribute('data-scroll-state', 'hidden');
        await scrollDocument(page, 0);
        await expect(header).toHaveAttribute('data-scroll-state', 'visible');
        await expectAtTop(header);

        const transition = await header.evaluate((el) => {
            const style = getComputedStyle(el);
            return {property: style.transitionProperty, durations: style.transitionDuration.split(',').map((part) => Number.parseFloat(part))};
        });
        if (reducedMotion === 'reduce') expect(transition.property).toBe('none');
        else expect(transition.durations.some((duration) => duration > 0)).toBe(true);
    });
}
