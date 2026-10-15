/**
 * Browser-only complement to Header.test.ts: actual sticky positioning,
 * transform endpoints, retained document flow and reduced-motion CSS — and
 * the focus rule, which only a browser classifies: keyboard focus inside the
 * header (`:focus-visible`) pins it, while the focus a mouse click leaves on a
 * header button (Chrome keeps it there) does not, so after a click on the
 * theme toggle the header still hides on a downward scroll (developer report,
 * 15/10). Header.test.ts states the focus kind by owning `:focus-visible`;
 * here Chrome decides it, from a real click and a real Tab.
 *
 * The runner's desktop AND mobile projects run every case. No seeded user,
 * financial fixture, database mutation or third-party request is involved:
 * every API the protected layout calls is answered from the synthetic table
 * below, and a request that is not in it fails the fixture's teardown.
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
            // The sidebar's connection-security line (plan 36): the answer the lane's plain-HTTP loopback gets.
            ['/api/v1/system/connection', {client_class: 'loopback', cookie_secure: false}],
            // The instance's public configuration (InstanceConfigResponse), read by the (app) layout on mount: a
            // self-hosted instance, the store's own DEFAULT_INSTANCE_CONFIG, so the page draws what it draws unanswered.
            ['/api/v1/system/instance', {profile: 'selfhosted'}],
            [
                '/api/v1/settings/onboarding',
                {
                    flows: (['welcome', 'intro_tour', 'import_guide'] as const).map((flow) => ({
                        flow,
                        status: 'completed',
                        version: 1,
                        current_version: 1,
                        update_available: false,
                        created_at: '2024-03-15T12:00:00Z',
                        updated_at: '2024-03-15T12:00:00Z',
                        completed_at: '2024-03-15T12:00:00Z',
                        skipped_at: null,
                    })),
                },
            ],
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

/**
 * Scrolls the document to `y` and returns once the header has handled that
 * scroll, so a state read afterwards is the header's verdict on it. A "still
 * pinned" needs this: an unchanged attribute reads the same before the header
 * has looked. The header reads a scroll in the animation frame its window
 * `scroll` listener schedules; the listener added here comes after the
 * header's, so the barrier is that `scroll` event, then two frames. A
 * rendering barrier, like the fixture's ResizeObserver one, not a clock.
 */
async function scrollDocumentSeen(page: Page, y: number) {
    expect(await documentY(page), `the scroll must move the document, or no scroll event would come: it is already at ${y}`).not.toBe(y);
    await page.evaluate(async (top) => {
        const scrolled = new Promise<void>((resolve) => window.addEventListener('scroll', () => resolve(), {once: true}));
        window.scrollTo({top, behavior: 'instant'});
        await scrolled;
        await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
    }, y);
    expect(await documentY(page)).toBe(y);
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
        // Closing a menu does not release focus: the click left it on the button. That mouse focus no longer pins
        // the header (the focus cases below); it moves outside explicitly all the same, so this case does not depend
        // on how the browser classifies it.
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

// The focus rule. The header pins only on a focus the browser shows (`:focus-visible`): a keyboard user must not lose
// the control they are on, while the focus Chrome leaves on a clicked button must not hold the header for good — that
// was the report: after a click on the theme toggle the header never hid again. Both cases use theme-toggle, drawn by
// both projects, and each checks the kind of focus it got before reading the header.

test('a mouse click on a header control leaves the header free to hide on a downward scroll', async ({reviewHeader: page}) => {
    const header = page.getByTestId('app-header');
    const theme = header.getByTestId('theme-toggle');
    await scrollDocument(page, 0);
    await expect(header).toHaveAttribute('data-scroll-state', 'visible');
    const down = Math.ceil(await header.evaluate((el) => el.getBoundingClientRect().height)) + 100;

    await expect(theme).toBeVisible();
    await theme.click();
    // The precondition of the report, checked rather than assumed: the focus is inside the header — without it this
    // case would pass under the old rule as well — and it is not keyboard focus.
    await expect(theme, 'Chrome leaves the focus of a mouse click on the button').toBeFocused();
    expect(await theme.evaluate((el) => el.matches(':focus-visible')), 'a mouse click gives no keyboard focus').toBe(false);
    await expect(header, 'a focus the browser does not show does not pin the header').toHaveAttribute('data-scroll-state', 'visible');

    await scrollDocument(page, down);
    await expect(header).toHaveAttribute('data-scroll-state', 'hidden');
    // Off-screen, measured as the case above measures it: a translated header still has a bounding box.
    await expect.poll(() => header.evaluate((el) => el.getBoundingClientRect().bottom), {timeout: 5_000}).toBeLessThanOrEqual(0.75);
    await expect(theme, 'the header hid with the focus of the click still inside it').toBeFocused();
});

test('keyboard focus on a header control keeps the header pinned and on screen through a downward scroll', async ({reviewHeader: page}) => {
    const header = page.getByTestId('app-header');
    const privacy = header.getByTestId('privacy-toggle');
    const theme = header.getByTestId('theme-toggle');
    await scrollDocument(page, 0);
    await expect(header).toHaveAttribute('data-scroll-state', 'visible');
    const down = Math.ceil(await header.evaluate((el) => el.getBoundingClientRect().height)) + 100;

    // Keyboard focus, made deterministic: the last hop is a Tab, which Chrome always marks :focus-visible. A bare
    // focus() would inherit the kind of the page's last interaction instead (not visible after a mouse click), so the
    // case would test the page's history, not the rule. The hop starts on privacy-toggle, the control just before
    // theme-toggle in the header on both projects: a Tab that lands anywhere else fails here, not three steps later.
    await expect(privacy).toBeVisible();
    await expect(theme).toBeVisible();
    await privacy.focus();
    await page.keyboard.press('Tab');
    await expect(theme, 'Tab from privacy-toggle lands on theme-toggle, the next control of the header').toBeFocused();
    expect(await theme.evaluate((el) => el.matches(':focus-visible')), 'a focus that arrives by Tab is keyboard focus').toBe(true);
    await expect(header).toHaveAttribute('data-scroll-state', 'pinned');

    await scrollDocumentSeen(page, down);
    expect(await header.getAttribute('data-scroll-state'), 'read once the header has handled the scroll: the keyboard focus held the pin').toBe('pinned');
    await expectAtTop(header);
    await expect(theme, 'the pin still has its cause: the keyboard focus never left the control').toBeFocused();

    // Positive control of the barrier: without the focus, the same barrier already shows the hide, so the "pinned"
    // above is the header's verdict on the scroll and not a reading taken before it looked.
    await page.getByTestId(GEOMETRY_ID).evaluate((el) => {
        (el as HTMLElement).tabIndex = -1;
        (el as HTMLElement).focus({preventScroll: true});
    });
    await expect(header, 'focus left the header: the pin is released').toHaveAttribute('data-scroll-state', 'visible');
    await scrollDocumentSeen(page, down + 100);
    expect(await header.getAttribute('data-scroll-state'), 'without the focus pin, the same barrier sees the header hide').toBe('hidden');
});
