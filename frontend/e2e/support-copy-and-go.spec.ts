import {expect, test, type BrowserContext, type Page} from './fixtures/playwright';
import {eventSeq, waitForEvent} from './fixtures/app-events';
import {login, navigateTo, setLanguage} from './fixtures/auth-helpers';
import {t} from './fixtures/i18n-data';
import {TEST_USER} from './fixtures/test-users';

const PUBLIC_PROJECT_URL = 'https://librefolio.github.io/LibreFolio/';
const SOCIAL_DESTINATION_RE = /^https:\/\/(?:twitter\.com\/intent\/tweet|www\.reddit\.com\/submit|www\.facebook\.com\/sharer\/sharer\.php|www\.instagram\.com\/|www\.tiktok\.com\/upload)(?:\?.*)?$/;
const TIKTOK_DESTINATION_RE = /^https:\/\/www\.tiktok\.com\/upload$/;

type SupportedLocale = 'en' | 'it' | 'fr' | 'es';
type SocialPlatform = 'x' | 'reddit' | 'facebook' | 'instagram' | 'tiktok';

type SocialRequest = {
    url: string;
    referer: string | null;
};

const SOCIAL_PLATFORMS: SocialPlatform[] = ['x', 'reddit', 'facebook', 'instagram', 'tiktok'];

async function installClipboardHarness(context: BrowserContext) {
    await context.addInitScript(() => {
        const state: {
            writes: string[];
            pending: null | {resolve: () => void; reject: (error: Error) => void};
        } = {
            writes: [],
            pending: null,
        };

        Object.defineProperty(window, '__supportCopyTest', {
            value: {
                writes: state.writes,
                resolvePending: () => {
                    const pending = state.pending;
                    state.pending = null;
                    pending?.resolve();
                },
                rejectPending: (message = 'clipboard denied') => {
                    const pending = state.pending;
                    state.pending = null;
                    pending?.reject(new Error(message));
                },
            },
            configurable: true,
        });

        Object.defineProperty(navigator, 'clipboard', {
            value: {
                writeText(text: string) {
                    state.writes.push(text);
                    return new Promise<void>((resolve, reject) => {
                        state.pending = {resolve, reject};
                    });
                },
            },
            configurable: true,
        });
    });
}

async function socialRoute(context: BrowserContext, destinationRe = SOCIAL_DESTINATION_RE): Promise<SocialRequest[]> {
    const requests: SocialRequest[] = [];
    await context.route(destinationRe, async (route) => {
        requests.push({
            url: route.request().url(),
            referer: route.request().headers().referer ?? null,
        });
        await route.fulfill({
            status: 200,
            contentType: 'text/html',
            body: '<!doctype html><html><head><title>social-share-probe</title></head><body data-testid="social-destination-probe"></body></html>',
        });
    });
    return requests;
}

async function openAboutShareModal(page: Page, platform: SocialPlatform = 'x', lang: SupportedLocale = 'en') {
    await login(page, TEST_USER);
    await navigateTo(page, '/settings');
    await setLanguage(page, lang);
    await page.getByTestId('settings-tab-about').click();
    await expect(page.getByTestId('about-tab')).toBeVisible();
    await expect(page.getByTestId('about-support-card')).toBeVisible();
    await page.getByTestId(`support-share-${platform}`).click();
    await expect(page.getByTestId('support-social-share-modal')).toBeVisible();
    await expect
        .poll(
            async () =>
                page.evaluate((key) => {
                    const icon = document.querySelector(`[data-testid="support-share-${key}"]`);
                    const copy = document.querySelector('[data-testid="support-social-share-copy"]');
                    if (!icon || !copy) throw new Error('Share icon or copy action is missing');
                    const canvas = document.createElement('canvas');
                    canvas.width = canvas.height = 1;
                    const context = canvas.getContext('2d');
                    if (!context) throw new Error('Browser color normalization is unavailable');
                    const surface = (element: Element) => {
                        const style = getComputedStyle(element);
                        // Equivalent oklab/oklch values can serialize differently during a transition.
                        context.clearRect(0, 0, 1, 1);
                        context.fillStyle = style.backgroundColor;
                        context.fillRect(0, 0, 1, 1);
                        return {color: [...context.getImageData(0, 0, 1, 1).data], image: style.backgroundImage};
                    };
                    const iconSurface = surface(icon);
                    const copySurface = surface(copy);
                    return {
                        samePaint: JSON.stringify(copySurface) === JSON.stringify(iconSurface),
                        visiblePaint: copySurface.image !== 'none' || copySurface.color[3] > 0,
                    };
                }, platform),
            {message: 'Social action and icon must settle to the same visible brand colors'},
        )
        .toEqual({samePaint: true, visiblePaint: true});
}

async function clipboardWrites(page: Page): Promise<string[]> {
    return page.evaluate(() => ((window as unknown as {__supportCopyTest?: {writes: string[]}}).__supportCopyTest?.writes ?? []).slice());
}

async function resolveClipboard(page: Page) {
    await page.evaluate(() => (window as unknown as {__supportCopyTest: {resolvePending: () => void}}).__supportCopyTest.resolvePending());
}

async function rejectClipboard(page: Page, message: string) {
    await page.evaluate((msg) => (window as unknown as {__supportCopyTest: {rejectPending: (message: string) => void}}).__supportCopyTest.rejectPending(msg), message);
}

async function eventNamesSince(page: Page, since: number): Promise<string[]> {
    return page.evaluate((start) => ((window as unknown as {__lf?: {events?: Array<{seq: number; name: string}>}}).__lf?.events ?? []).filter((event) => event.seq > start).map((event) => event.name), since);
}

async function visibleShareState(page: Page): Promise<{message: string; title: string | null}> {
    const message = await page.getByTestId('support-social-share-message').inputValue();
    const titleField = page.getByTestId('support-social-share-post-title');
    const title = (await titleField.count()) > 0 ? await titleField.inputValue() : null;
    return {message, title};
}

type ShareGeometry = {
    viewport: {width: number; height: number};
    badge: {x: number; y: number; width: number; height: number; right: number; bottom: number; borderRadius: number};
    icon: {x: number; y: number; width: number; height: number; right: number; bottom: number};
    close: {x: number; y: number; width: number; height: number; right: number; bottom: number};
    title: {x: number; y: number; width: number; height: number; right: number; bottom: number};
    hint: {x: number; y: number; width: number; height: number; right: number; bottom: number; lineHeight: number; scrollHeight: number; clientHeight: number};
};

async function openItalianAboutPage(page: Page) {
    await login(page, TEST_USER);

    const viewport = page.viewportSize();
    if (viewport && viewport.width > 600) {
        await page.setViewportSize({width: 560, height: Math.max(viewport.height, 800)});
    }

    await navigateTo(page, '/settings');
    await setLanguage(page, 'it');
    await page.getByTestId('settings-tab-about').click();
    await expect(page.getByTestId('about-tab')).toBeVisible();
    await expect(page.getByTestId('about-support-card')).toBeVisible();
}

async function readShareGeometry(page: Page): Promise<ShareGeometry> {
    return page.evaluate(() => {
        const modal = document.querySelector<HTMLElement>('[data-testid="support-social-share-modal"]');
        const badge = document.querySelector<HTMLElement>('[data-testid="support-social-share-badge"]');
        const close = document.querySelector<HTMLElement>('[data-testid="support-social-share-close-icon"]');
        const title = document.querySelector<HTMLElement>('[data-testid="support-social-share-title"]');
        const hint = document.querySelector<HTMLElement>('[data-testid="support-social-share-hint"]');
        const icon = badge?.querySelector<SVGSVGElement>('svg[data-social-icon]');

        if (!modal || !badge || !close || !title || !hint || !icon) {
            throw new Error('Support social share geometry targets are missing');
        }

        const snapshot = (element: Element) => {
            const rect = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            return {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
                right: rect.right,
                bottom: rect.bottom,
                borderRadius: Number.parseFloat(style.borderTopLeftRadius || '0'),
            };
        };

        const iconRect = icon.getBoundingClientRect();
        return {
            viewport: {width: window.innerWidth, height: window.innerHeight},
            badge: snapshot(badge),
            icon: {
                x: iconRect.x,
                y: iconRect.y,
                width: iconRect.width,
                height: iconRect.height,
                right: iconRect.right,
                bottom: iconRect.bottom,
            },
            close: snapshot(close),
            title: snapshot(title),
            hint: {...snapshot(hint), lineHeight: Number.parseFloat(getComputedStyle(hint).lineHeight), scrollHeight: hint.scrollHeight, clientHeight: hint.clientHeight},
        };
    });
}

test.describe('Support copy-and-go', () => {
    test.beforeEach(async ({context}) => {
        await installClipboardHarness(context);
    });

    test('reserves an about:blank popup first and navigates it only after clipboard success', async ({page, context}) => {
        const socialRequests = await socialRoute(context);
        await openAboutShareModal(page, 'x', 'en');
        const {message, title} = await visibleShareState(page);

        expect(title).toBeNull();
        expect(message).toBe(t('en', 'support.share.x.message'));

        const since = await eventSeq(page);
        const popupPromise = page.waitForEvent('popup');
        await page.getByTestId('support-social-share-copy').click();

        const popup = await popupPromise;
        await popup.waitForLoadState('domcontentloaded');

        const [payload] = await clipboardWrites(page);
        expect(payload).toBe(`${message}\n${PUBLIC_PROJECT_URL}`);
        await expect(page.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'pending');
        await expect(page).toHaveURL(/\/settings$/);
        await expect(page.getByTestId('about-tab')).toBeVisible();
        await expect(page.getByTestId('support-social-share-modal')).toBeVisible();
        expect(popup.url()).toBe('about:blank');
        expect(socialRequests).toHaveLength(0);
        await expect
            .poll(
                async () =>
                    popup.evaluate(() => ({
                        openerIsNull: window.opener === null,
                        referrerPolicy: document.querySelector('meta[name="referrer"]')?.getAttribute('content') ?? null,
                    })),
                {message: 'the reserved popup should be hardened before external navigation'},
            )
            .toEqual({openerIsNull: true, referrerPolicy: 'no-referrer'});

        await resolveClipboard(page);
        await waitForEvent(page, 'support.social.open.requested', {since});
        await popup.waitForURL(/^https:\/\/twitter\.com\/intent\/tweet\?/);

        const shareUrl = new URL(popup.url());
        expect(shareUrl.searchParams.get('text')).toBe(message);
        expect(shareUrl.searchParams.get('url')).toBe(PUBLIC_PROJECT_URL);
        expect(socialRequests).toHaveLength(1);
        expect(socialRequests[0].referer).toBeNull();
        expect(await eventNamesSince(page, since)).toEqual(['support.social.copy.copied', 'support.social.open.requested']);
        await expect(page.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'copied');
        await expect(page.getByTestId('toast-success')).toBeVisible();
        await expect(page.getByTestId('support-social-share-modal')).toBeVisible();
        await expect(page.getByTestId('about-tab')).toBeVisible();
    });

    test('opens Reddit with a localized title and body while keeping the public URL in the copied text only', async ({page, context}) => {
        const socialRequests = await socialRoute(context);
        await openAboutShareModal(page, 'reddit', 'fr');
        const {message, title} = await visibleShareState(page);

        expect(message).toBe(t('fr', 'support.share.reddit.message'));
        expect(title).toBe(t('fr', 'support.share.reddit.title'));
        expect(title).not.toBe(message);

        const since = await eventSeq(page);
        const popupPromise = page.waitForEvent('popup');
        await page.getByTestId('support-social-share-copy').click();

        const popup = await popupPromise;
        await popup.waitForLoadState('domcontentloaded');

        const [payload] = await clipboardWrites(page);
        expect(payload).toBe(`${message}\n${PUBLIC_PROJECT_URL}`);
        await expect(page.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'pending');
        expect(socialRequests).toHaveLength(0);
        expect(popup.url()).toBe('about:blank');

        await resolveClipboard(page);
        await waitForEvent(page, 'support.social.open.requested', {since});
        await popup.waitForURL(/^https:\/\/www\.reddit\.com\/submit\?/);

        const shareUrl = new URL(popup.url());
        expect(shareUrl.searchParams.get('type')).toBe('TEXT');
        expect(shareUrl.searchParams.get('selftext')).toBe('true');
        expect(shareUrl.searchParams.get('title')).toBe(title);
        expect(shareUrl.searchParams.get('text')).toBe(payload);
        expect(shareUrl.searchParams.get('url')).toBeNull();
        expect(socialRequests).toHaveLength(1);
        expect(socialRequests[0].referer).toBeNull();
        expect(await eventNamesSince(page, since)).toEqual(['support.social.copy.copied', 'support.social.open.requested']);
        await expect(page.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'copied');
        await expect(page.getByTestId('toast-success')).toBeVisible();
    });

    test('copies the localized caption, then opens Instagram without inventing unsupported query prefills', async ({page, context}) => {
        const socialRequests = await socialRoute(context);
        await openAboutShareModal(page, 'instagram', 'es');
        const {message, title} = await visibleShareState(page);

        expect(title).toBeNull();
        expect(message).toBe(t('es', 'support.share.instagram.message'));

        const since = await eventSeq(page);
        const popupPromise = page.waitForEvent('popup');
        await page.getByTestId('support-social-share-copy').click();

        const popup = await popupPromise;
        await popup.waitForLoadState('domcontentloaded');

        const [payload] = await clipboardWrites(page);
        expect(payload).toBe(`${message}\n${PUBLIC_PROJECT_URL}`);

        await resolveClipboard(page);
        await waitForEvent(page, 'support.social.open.requested', {since});
        await popup.waitForURL('https://www.instagram.com/');

        expect(popup.url()).toBe('https://www.instagram.com/');
        expect(new URL(popup.url()).search).toBe('');
        expect(socialRequests).toHaveLength(1);
        expect(socialRequests[0].url).toBe('https://www.instagram.com/');
        expect(socialRequests[0].referer).toBeNull();
        expect(await eventNamesSince(page, since)).toEqual(['support.social.copy.copied', 'support.social.open.requested']);
        await expect(page.getByTestId('toast-success')).toBeVisible();
    });

    test('copies the Italian TikTok caption, then opens the upload flow without appending query prefills', async ({page, context}) => {
        const socialRequests = await socialRoute(context, TIKTOK_DESTINATION_RE);
        await openAboutShareModal(page, 'tiktok', 'it');
        const {message, title} = await visibleShareState(page);

        expect(title).toBeNull();
        expect(message).toBe(t('it', 'support.share.tiktok.message'));

        const since = await eventSeq(page);
        const popupPromise = page.waitForEvent('popup');
        await page.getByTestId('support-social-share-copy').click();

        const popup = await popupPromise;
        await popup.waitForLoadState('domcontentloaded');

        const [payload] = await clipboardWrites(page);
        expect(payload).toBe(`${message}\n${PUBLIC_PROJECT_URL}`);

        await resolveClipboard(page);
        await waitForEvent(page, 'support.social.open.requested', {since});
        await popup.waitForURL('https://www.tiktok.com/upload');

        expect(popup.url()).toBe('https://www.tiktok.com/upload');
        expect(new URL(popup.url()).search).toBe('');
        expect(socialRequests).toHaveLength(1);
        expect(socialRequests[0].url).toBe('https://www.tiktok.com/upload');
        expect(socialRequests[0].referer).toBeNull();
        expect(await eventNamesSince(page, since)).toEqual(['support.social.copy.copied', 'support.social.open.requested']);
        await expect(page.getByTestId('toast-success')).toBeVisible();
        await expect(page.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'copied');
    });

    test('shows an explicit error and never reaches a social destination when the clipboard write is denied', async ({page, context}) => {
        const socialRequests = await socialRoute(context);
        await openAboutShareModal(page, 'reddit', 'en');
        const {message, title} = await visibleShareState(page);

        expect(title).toBe(t('en', 'support.share.reddit.title'));
        expect(message).toBe(t('en', 'support.share.reddit.message'));

        const since = await eventSeq(page);
        const popupPromise = page.waitForEvent('popup');
        await page.getByTestId('support-social-share-copy').click();

        const popup = await popupPromise;
        await popup.waitForLoadState('domcontentloaded');

        expect(await clipboardWrites(page)).toEqual([`${message}\n${PUBLIC_PROJECT_URL}`]);
        await expect(page.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'pending');
        expect(socialRequests).toHaveLength(0);
        expect(popup.url()).toBe('about:blank');

        await rejectClipboard(page, 'clipboard denied');
        await waitForEvent(page, 'support.social.copy.failed', {since});

        await expect(page.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'error');
        await expect(page.getByTestId('support-social-share-error')).toBeVisible();
        await expect(page.getByTestId('toast-error')).toBeVisible();
        await expect(page.getByTestId('about-tab')).toBeVisible();
        await expect(page.getByTestId('support-social-share-modal')).toBeVisible();
        await expect(page.getByTestId('toast-success')).toHaveCount(0);
        expect(await eventNamesSince(page, since)).toEqual(['support.social.copy.failed']);
        expect(socialRequests).toHaveLength(0);
        await expect.poll(() => popup.isClosed(), {message: 'the reserved blank popup should be closed when copy fails'}).toBe(true);
    });

    test('keeps every Italian share badge square and the close icon in view when the About hints wrap', async ({page}) => {
        await openItalianAboutPage(page);

        for (const platform of SOCIAL_PLATFORMS) {
            await page.getByTestId(`support-share-${platform}`).click();

            const modal = page.getByTestId('support-social-share-modal');
            await expect(modal).toBeVisible();
            await expect(page.getByTestId('support-social-share-hint')).toHaveText(t('it', `support.share.${platform}.hint`));
            await expect
                .poll(
                    async () => {
                        const {badge, icon} = await readShareGeometry(page);
                        return {badgeWidth: badge.width, badgeHeight: badge.height, iconWidth: icon.width, iconHeight: icon.height};
                    },
                    {message: 'The modal entrance must settle to the fixed social badge geometry'},
                )
                .toEqual({badgeWidth: 40, badgeHeight: 40, iconWidth: 24, iconHeight: 24});

            const geometry = await readShareGeometry(page);

            expect(geometry.badge.width).toBe(40);
            expect(geometry.badge.height).toBe(40);
            expect(geometry.badge.borderRadius).toBeGreaterThanOrEqual(20);
            expect(geometry.icon.width).toBe(24);
            expect(geometry.icon.height).toBe(24);
            expect(geometry.icon.x).toBeGreaterThanOrEqual(geometry.badge.x - 0.5);
            expect(geometry.icon.y).toBeGreaterThanOrEqual(geometry.badge.y - 0.5);
            expect(geometry.icon.right).toBeLessThanOrEqual(geometry.badge.right + 0.5);
            expect(geometry.icon.bottom).toBeLessThanOrEqual(geometry.badge.bottom + 0.5);
            expect(geometry.hint.height).toBeGreaterThan(0);
            expect(geometry.hint.scrollHeight).toBeLessThanOrEqual(geometry.hint.clientHeight + 1);
            expect(geometry.hint.x).toBeGreaterThanOrEqual(geometry.badge.right);
            expect(geometry.hint.right).toBeLessThanOrEqual(geometry.viewport.width + 0.5);
            if (platform === 'tiktok') expect(geometry.hint.height).toBeGreaterThan(geometry.hint.lineHeight);
            expect(geometry.close.x).toBeGreaterThanOrEqual(-0.5);
            expect(geometry.close.y).toBeGreaterThanOrEqual(-0.5);
            expect(geometry.close.right).toBeLessThanOrEqual(geometry.viewport.width + 0.5);
            expect(geometry.close.bottom).toBeLessThanOrEqual(geometry.viewport.height + 0.5);
            await expect(page.getByTestId('support-social-share-close-icon')).toBeVisible();

            await page.getByTestId('support-social-share-close-icon').click();
            await expect(modal).toBeHidden();
            await expect(page.getByTestId('about-tab')).toBeVisible();
            await expect(page.getByTestId('about-support-card')).toBeVisible();
        }
    });
});
