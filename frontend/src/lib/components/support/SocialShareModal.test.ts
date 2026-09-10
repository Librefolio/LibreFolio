// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {locale} from 'svelte-i18n';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import en from '$lib/i18n/en.json';
import itCatalog from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const notify = vi.fn();

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: (...args: unknown[]) => notify(...args)}));
vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));
vi.mock('$lib/utils/clipboard', () => ({writeTextToClipboard: vi.fn()}));
vi.mock('./shareNavigation', () => ({reserveShareTab: vi.fn()}));

import SocialShareModal from './SocialShareModal.svelte';
import {PUBLIC_PROJECT_URL, SOCIAL_SHARE_CONFIG, SOCIAL_SHARE_ORDER, buildSocialShareCopy, buildSocialShareUrl, type SocialPlatform} from './supportLinks';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import {writeTextToClipboard} from '$lib/utils/clipboard';
import {reserveShareTab} from './shareNavigation';

const SHARE_CATALOG = {en, it: itCatalog, fr, es} as const;
const SUPPORTED_LOCALES = ['en', 'it', 'fr', 'es'] as const;

type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];
type CloseHandler = () => void;

interface MockShareTab {
    readonly closed: boolean;
    navigate: Mock<(url: string) => void>;
    close: Mock<() => void>;
}

function translation(localeCode: SupportedLocale, key: string): string {
    const value = key.split('.').reduce<unknown>((current, part) => {
        if (!current || typeof current !== 'object') return undefined;
        return (current as Record<string, unknown>)[part];
    }, SHARE_CATALOG[localeCode]);
    if (typeof value !== 'string') throw new Error(`Missing translation for ${localeCode}:${key}`);
    return value;
}

function messageFor(localeCode: SupportedLocale, platform: SocialPlatform): string {
    return translation(localeCode, `support.share.${platform}.message`);
}

function hintFor(localeCode: SupportedLocale, platform: SocialPlatform): string {
    return translation(localeCode, `support.share.${platform}.hint`);
}

function titleFor(localeCode: SupportedLocale): string {
    return translation(localeCode, 'support.share.reddit.title');
}

function titleLabelFor(localeCode: SupportedLocale): string {
    return translation(localeCode, 'support.share.titleLabel');
}

function commonCopiedFor(localeCode: SupportedLocale): string {
    return translation(localeCode, 'common.copiedToClipboard');
}

type AfterCopyPlatform = 'facebook' | 'instagram' | 'tiktok';

function afterCopyFor(localeCode: SupportedLocale, platform: AfterCopyPlatform): string {
    return translation(localeCode, `support.share.${platform}.afterCopy`);
}

function deferred<T>() {
    let resolve!: (value: T | PromiseLike<T>) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

function makeTab(options: {closed?: boolean; navigateImpl?: (url: string) => void} = {}): MockShareTab {
    let closed = options.closed ?? false;
    const navigate: Mock<(url: string) => void> = vi.fn((url: string) => options.navigateImpl?.(url));
    const close: Mock<() => void> = vi.fn(() => {
        closed = true;
    });
    return {
        get closed() {
            return closed;
        },
        navigate,
        close,
    };
}

function mount(props: Partial<{open: boolean; platform: SocialPlatform; onClose: CloseHandler}> = {}) {
    const onClose: Mock<CloseHandler> = vi.fn();
    return {
        onClose,
        ...render(SocialShareModal, {open: true, platform: 'x', onClose, ...props}),
    };
}

type MountedModal = Pick<ReturnType<typeof mount>, 'onClose' | 'rerender' | 'unmount'>;

function notificationNames(): string[] {
    return notify.mock.calls.map(([event]) => (event as {name: string}).name);
}

async function flushMicrotasks() {
    await Promise.resolve();
    await Promise.resolve();
}

beforeEach(async () => {
    await setupI18n('en');
    notify.mockReset();
    vi.mocked(writeTextToClipboard).mockReset();
    vi.mocked(reserveShareTab).mockReset();
    transitionClientSession(null);
    transitionClientSession('review-support-social');
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(
        () =>
            [
                {
                    x: 0,
                    y: 0,
                    width: 1,
                    height: 1,
                    top: 0,
                    right: 1,
                    bottom: 1,
                    left: 0,
                },
            ] as unknown as DOMRectList,
    );
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.restoreAllMocks();
});

describe('SocialShareModal — public share surface', () => {
    it('keeps the public URL out of editable fields, shows the Reddit title field and preserves the fixed footer order', async () => {
        mount({platform: 'reddit'});
        const dialog = screen.getByTestId('support-social-share-modal');
        const title = screen.getByTestId('support-social-share-title');
        const titleField = screen.getByTestId('support-social-share-post-title') as HTMLInputElement;
        const message = screen.getByTestId('support-social-share-message') as HTMLTextAreaElement;
        const copy = screen.getByTestId('support-social-share-copy');
        const actions = screen.getByTestId('support-social-share-actions');

        expect(dialog.getAttribute('style')).toContain('z-index: 60');
        expect(title.id).toBeTruthy();
        expect(dialog).toHaveAttribute('aria-labelledby', title.id);
        expect(titleField).toHaveAttribute('readonly');
        expect(titleField).toHaveValue(titleFor('en'));
        expect(message).toHaveAttribute('readonly');
        expect(message).toHaveValue(messageFor('en', 'reddit'));
        expect(screen.getByTestId('support-social-share-hint')).toHaveTextContent(hintFor('en', 'reddit'));
        expect(screen.getByTestId('support-social-share-title-label')).toHaveTextContent(titleLabelFor('en'));
        expect(dialog.querySelector('[data-social-icon="reddit"]')).not.toBeNull();
        expect(screen.queryByTestId('support-social-share-url')).toBeNull();
        expect(screen.queryByTestId('support-social-share-open')).toBeNull();
        expect(copy).toHaveAttribute('data-copy-state', 'idle');
        expect(copy).toHaveAttribute('data-social-platform', 'reddit');
        expect(copy.className).toContain(SOCIAL_SHARE_CONFIG.reddit.brandClass);
        expect(copy).not.toBeDisabled();
        expect(Array.from(actions.children).map((child) => child.getAttribute('data-testid'))).toEqual(['support-social-share-close', 'support-social-share-copy']);

        await fireEvent.focus(titleField);
        expect(titleField.selectionStart).toBe(0);
        expect(titleField.selectionEnd).toBe(titleField.value.length);

        await fireEvent.focus(message);
        expect(message.selectionStart).toBe(0);
        expect(message.selectionEnd).toBe(message.value.length);

        await fireEvent.click(message);
        expect(message.selectionStart).toBe(0);
        expect(message.selectionEnd).toBe(message.value.length);
    });

    it.each(
        SUPPORTED_LOCALES.flatMap((lang) =>
            SOCIAL_SHARE_ORDER.map((platform) => ({
                lang,
                platform,
            })),
        ),
    )('binds the active $lang locale copy and hint for $platform', async ({lang, platform}: {lang: SupportedLocale; platform: SocialPlatform}) => {
        await setupI18n(lang);
        mount({platform});
        const message = screen.getByTestId('support-social-share-message') as HTMLTextAreaElement;
        const copy = screen.getByTestId('support-social-share-copy');

        expect(message).toHaveValue(messageFor(lang, platform));
        expect(screen.getByTestId('support-social-share-hint')).toHaveTextContent(hintFor(lang, platform));
        expect(copy).toHaveAttribute('data-social-platform', platform);
        expect(copy.className).toContain(SOCIAL_SHARE_CONFIG[platform].brandClass);

        if (platform === 'reddit') {
            expect(screen.getByTestId('support-social-share-post-title')).toHaveValue(titleFor(lang));
            expect(screen.getByTestId('support-social-share-title-label')).toHaveTextContent(titleLabelFor(lang));
        } else {
            expect(screen.queryByTestId('support-social-share-post-title')).toBeNull();
        }

        if (platform === 'x') {
            const [headline, hashtags = ''] = message.value.split('\n');
            expect(headline).not.toMatch(/^#/);
            expect(hashtags).toMatch(/^#/);
        }
    });

    it('updates the visible message and Reddit title when the active locale changes while open', async () => {
        mount({platform: 'reddit'});
        const message = screen.getByTestId('support-social-share-message');
        const title = screen.getByTestId('support-social-share-post-title');
        expect(message).toHaveValue(messageFor('en', 'reddit'));
        await setupI18n('it');
        await waitFor(() => expect(message).toHaveValue(messageFor('it', 'reddit')));
        expect(title).toHaveValue(titleFor('it'));
        expect(screen.getByTestId('support-social-share-hint')).toHaveTextContent(hintFor('it', 'reddit'));
    });

    it('traps focus inside the modal, closes on Escape and restores the opener when dismissed', async () => {
        const opener = document.createElement('button');
        opener.type = 'button';
        document.body.appendChild(opener);
        opener.focus();

        const onClose: Mock<CloseHandler> = vi.fn();
        const view = render(SocialShareModal, {open: true, platform: 'x', onClose});
        const dialog = screen.getByTestId('support-social-share-modal');
        const first = screen.getByTestId('support-social-share-close-icon');
        const last = screen.getByTestId('support-social-share-copy');

        await waitFor(() => expect(first).toHaveFocus());

        last.focus();
        await fireEvent.keyDown(dialog, {key: 'Tab'});
        expect(first).toHaveFocus();

        first.focus();
        await fireEvent.keyDown(dialog, {key: 'Tab', shiftKey: true});
        expect(last).toHaveFocus();

        await fireEvent.keyDown(dialog, {key: 'Escape'});
        expect(onClose).toHaveBeenCalledTimes(1);

        await view.rerender({open: false, platform: 'x', onClose});
        await waitFor(() => expect(screen.queryByTestId('support-social-share-modal')).toBeNull());
        await waitFor(() => expect(opener).toHaveFocus());
        opener.remove();
    });
});

describe('SocialShareModal — copy and navigation flow', () => {
    it('starts copy before reserving the tab, then navigates only after copy succeeds', async () => {
        vi.useFakeTimers();
        const copyRequest = deferred<void>();
        const tab = makeTab();
        const copyWriter = vi.mocked(writeTextToClipboard);
        const reserve = vi.mocked(reserveShareTab);
        copyWriter.mockReturnValue(copyRequest.promise);
        reserve.mockReturnValue(tab);
        mount();
        const copy = screen.getByTestId('support-social-share-copy');
        const message = screen.getByTestId('support-social-share-message') as HTMLTextAreaElement;

        await fireEvent.click(copy);

        expect(copyWriter).toHaveBeenCalledWith(buildSocialShareCopy(message.value));
        expect(copyWriter.mock.calls[0][0]).toContain(PUBLIC_PROJECT_URL);
        expect(copyWriter.mock.invocationCallOrder[0]).toBeLessThan(reserve.mock.invocationCallOrder[0]);
        expect(copy).toHaveAttribute('data-copy-state', 'pending');
        expect(copy).toBeDisabled();
        expect(tab.navigate).not.toHaveBeenCalled();

        copyRequest.resolve(undefined);
        await flushMicrotasks();
        await waitFor(() => expect(copy).toHaveAttribute('data-copy-state', 'copied'));

        expect(tab.navigate).toHaveBeenCalledWith(buildSocialShareUrl('x', message.value));
        expect(tab.close).not.toHaveBeenCalled();
        expect(notificationNames()).toEqual(['support.social.copy.copied', 'support.social.open.requested']);
        expect(notify.mock.calls[0][0]).not.toHaveProperty('toast');
        expect(notify).toHaveBeenNthCalledWith(
            2,
            expect.objectContaining({
                name: 'support.social.open.requested',
                detail: {platform: 'x'},
                toast: expect.objectContaining({variant: 'success', message: commonCopiedFor('en')}),
            }),
        );
        expect(copy).not.toBeDisabled();

        await vi.advanceTimersByTimeAsync(1_999);
        expect(copy).toHaveAttribute('data-copy-state', 'copied');

        await vi.advanceTimersByTimeAsync(1);
        await waitFor(() => expect(copy).toHaveAttribute('data-copy-state', 'idle'));
    });

    it('routes Reddit with a separate readonly title and the copied body payload', async () => {
        vi.mocked(writeTextToClipboard).mockResolvedValue(undefined);
        const tab = makeTab();
        vi.mocked(reserveShareTab).mockReturnValue(tab);
        mount({platform: 'reddit'});
        const copy = screen.getByTestId('support-social-share-copy');
        const message = screen.getByTestId('support-social-share-message') as HTMLTextAreaElement;
        const titleField = screen.getByTestId('support-social-share-post-title') as HTMLInputElement;

        await fireEvent.click(copy);
        await waitFor(() => expect(copy).toHaveAttribute('data-copy-state', 'copied'));

        expect(titleField.value).not.toBe(message.value);
        expect(writeTextToClipboard).toHaveBeenCalledWith(buildSocialShareCopy(message.value));
        expect(tab.navigate).toHaveBeenCalledWith(buildSocialShareUrl('reddit', message.value, titleField.value));

        const destination = new URL(tab.navigate.mock.calls[0][0]);
        expect(destination.searchParams.get('type')).toBe('TEXT');
        expect(destination.searchParams.get('selftext')).toBe('true');
        expect(destination.searchParams.get('title')).toBe(titleField.value);
        expect(destination.searchParams.get('text')).toBe(buildSocialShareCopy(message.value));
        expect(destination.searchParams.get('url')).toBeNull();
        expect(notificationNames()).toEqual(['support.social.copy.copied', 'support.social.open.requested']);
        expect(notify).toHaveBeenNthCalledWith(
            2,
            expect.objectContaining({
                name: 'support.social.open.requested',
                detail: {platform: 'reddit'},
                toast: expect.objectContaining({variant: 'success', message: commonCopiedFor('en')}),
            }),
        );
    });

    it('treats a synchronous clipboard failure as a copy error before any tab reservation happens', async () => {
        const copyWriter = vi.mocked(writeTextToClipboard);
        const reserve = vi.mocked(reserveShareTab);
        copyWriter.mockImplementation(() => {
            throw new Error('Clipboard copy was rejected.');
        });
        mount();
        const copy = screen.getByTestId('support-social-share-copy');

        await fireEvent.click(copy);

        await waitFor(() => expect(copy).toHaveAttribute('data-copy-state', 'error'));
        expect(reserve).not.toHaveBeenCalled();
        expect(notificationNames()).toEqual(['support.social.copy.failed']);
        expect(notify).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'support.social.copy.failed',
                detail: {platform: 'x', reason: 'Clipboard copy was rejected.'},
                toast: expect.objectContaining({variant: 'error'}),
            }),
        );
    });

    it('shows an explicit copy failure, closes the reserved tab and never requests navigation', async () => {
        const tab = makeTab();
        vi.mocked(writeTextToClipboard).mockRejectedValue(new Error('clipboard rejected'));
        vi.mocked(reserveShareTab).mockReturnValue(tab);
        const {onClose} = mount({platform: 'reddit'});
        const copy = screen.getByTestId('support-social-share-copy');

        await fireEvent.click(copy);

        await waitFor(() => expect(copy).toHaveAttribute('data-copy-state', 'error'));
        expect(screen.getByTestId('support-social-share-error')).toHaveTextContent(/\S/);
        expect(copy).not.toBeDisabled();
        expect(tab.close).toHaveBeenCalledTimes(1);
        expect(tab.navigate).not.toHaveBeenCalled();
        expect(onClose).not.toHaveBeenCalled();
        expect(notificationNames()).toEqual(['support.social.copy.failed']);
        expect(notify).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'support.social.copy.failed',
                detail: {platform: 'reddit', reason: 'clipboard rejected'},
                toast: expect.objectContaining({variant: 'error'}),
            }),
        );
    });

    it.each(['facebook', 'instagram', 'tiktok'] as const)('uses the localized after-copy toast for $platform and still navigates to the public intent contract', async (platform) => {
        vi.mocked(writeTextToClipboard).mockResolvedValue(undefined);
        const tab = makeTab();
        vi.mocked(reserveShareTab).mockReturnValue(tab);
        mount({platform});
        const copy = screen.getByTestId('support-social-share-copy');
        const message = screen.getByTestId('support-social-share-message') as HTMLTextAreaElement;

        await fireEvent.click(copy);
        await waitFor(() => expect(copy).toHaveAttribute('data-copy-state', 'copied'));

        expect(writeTextToClipboard).toHaveBeenCalledWith(buildSocialShareCopy(message.value));
        expect(tab.navigate).toHaveBeenCalledWith(buildSocialShareUrl(platform, message.value));
        expect(notificationNames()).toEqual(['support.social.copy.copied', 'support.social.open.requested']);
        expect(notify).toHaveBeenNthCalledWith(
            2,
            expect.objectContaining({
                name: 'support.social.open.requested',
                detail: {platform},
                toast: expect.objectContaining({variant: 'success', message: afterCopyFor('en', platform)}),
            }),
        );

        const destination = new URL(tab.navigate.mock.calls[0][0]);
        if (platform === 'facebook') {
            expect(destination.searchParams.get('u')).toBe(PUBLIC_PROJECT_URL);
        } else {
            expect(destination.search).toBe('');
        }
        if (platform === 'tiktok') {
            expect(`${destination.origin}${destination.pathname}`).toBe('https://www.tiktok.com/upload');
        }
    });

    it.each([
        {
            name: 'the popup reservation is blocked',
            reserve: () => null,
            expectedReason: 'blocked',
            expectedCloseCalls: 0,
        },
        {
            name: 'the reserved tab is already closed',
            reserve: () => makeTab({closed: true}),
            expectedReason: 'closed',
            expectedCloseCalls: 0,
        },
        {
            name: 'reserving the tab throws during hardening',
            reserve: () => {
                throw new Error('reservation failed');
            },
            expectedReason: 'reservation-failed',
            expectedCloseCalls: 0,
        },
        {
            name: 'navigation throws after the copy succeeds',
            reserve: () =>
                makeTab({
                    navigateImpl: () => {
                        throw new Error('navigation failed');
                    },
                }),
            expectedReason: 'navigation-failed',
            expectedCloseCalls: 1,
        },
    ])('shows a warning and no false social success when $name', async ({reserve, expectedReason, expectedCloseCalls}) => {
        vi.mocked(writeTextToClipboard).mockResolvedValue(undefined);
        const observed: {tab: MockShareTab | null} = {tab: null};
        vi.mocked(reserveShareTab).mockImplementation(() => {
            observed.tab = reserve();
            return observed.tab;
        });
        const {onClose} = mount();
        const copy = screen.getByTestId('support-social-share-copy');

        await fireEvent.click(copy);

        await waitFor(() => expect(copy).toHaveAttribute('data-copy-state', 'error'));
        expect(screen.getByTestId('support-social-share-error')).toHaveTextContent(/\S/);
        expect(copy).not.toBeDisabled();
        expect(onClose).not.toHaveBeenCalled();
        expect(notificationNames()).toEqual(['support.social.copy.copied', 'support.social.open.failed']);
        expect(notify).toHaveBeenNthCalledWith(
            2,
            expect.objectContaining({
                name: 'support.social.open.failed',
                detail: {platform: 'x', reason: expectedReason, copied: true},
                toast: expect.objectContaining({variant: 'warning'}),
            }),
        );
        expect(notify).not.toHaveBeenCalledWith(expect.objectContaining({name: 'support.social.open.requested'}));
        if (observed.tab) {
            expect(observed.tab.navigate).toHaveBeenCalledTimes(expectedReason === 'navigation-failed' ? 1 : 0);
            expect(observed.tab.close).toHaveBeenCalledTimes(expectedCloseCalls);
        }
    });

    it.each([
        {
            name: 'the modal is explicitly closed',
            invalidate: async ({onClose}: MountedModal) => {
                await fireEvent.click(screen.getByTestId('support-social-share-close'));
                expect(onClose).toHaveBeenCalledTimes(1);
            },
        },
        {
            name: 'the platform changes',
            invalidate: async ({rerender, onClose}: MountedModal) => {
                await rerender({open: true, platform: 'reddit', onClose});
            },
        },
        {
            name: 'the locale changes',
            invalidate: async () => {
                locale.set('it');
                await waitFor(() => expect(screen.getByTestId('support-social-share-message')).toHaveValue(messageFor('it', 'x')));
            },
        },
        {
            name: 'the client session changes',
            invalidate: async () => {
                transitionClientSession('review-support-social-next');
            },
        },
        {
            name: 'the modal unmounts',
            invalidate: async ({unmount}: MountedModal) => {
                unmount();
            },
        },
    ])('closes the reserved tab and ignores a late clipboard success when $name', async ({invalidate}) => {
        const copyRequest = deferred<void>();
        const tab = makeTab();
        vi.mocked(writeTextToClipboard).mockReturnValue(copyRequest.promise);
        vi.mocked(reserveShareTab).mockReturnValue(tab);
        const view = mount();
        const copy = screen.getByTestId('support-social-share-copy');

        await fireEvent.click(copy);
        expect(copy).toHaveAttribute('data-copy-state', 'pending');

        await invalidate(view);
        expect(tab.close).toHaveBeenCalledTimes(1);

        copyRequest.resolve(undefined);
        await flushMicrotasks();

        expect(notificationNames()).toEqual([]);
        const maybeCopy = screen.queryByTestId('support-social-share-copy');
        if (maybeCopy) {
            expect(maybeCopy).toHaveAttribute('data-copy-state', 'idle');
            expect(maybeCopy).not.toHaveAttribute('data-copy-state', 'copied');
        }
    });

    it('never closes an already handed-off social tab after successful navigation', async () => {
        vi.useFakeTimers();
        const tab = makeTab();
        vi.mocked(writeTextToClipboard).mockResolvedValue(undefined);
        vi.mocked(reserveShareTab).mockReturnValue(tab);
        const view = mount();

        await fireEvent.click(screen.getByTestId('support-social-share-copy'));
        await waitFor(() => expect(screen.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'copied'));

        expect(tab.navigate).toHaveBeenCalledTimes(1);
        expect(tab.close).not.toHaveBeenCalled();

        view.unmount();
        expect(tab.close).not.toHaveBeenCalled();
    });

    it('cleans up the copied-reset timer when the modal unmounts', async () => {
        vi.useFakeTimers();
        vi.mocked(writeTextToClipboard).mockResolvedValue(undefined);
        vi.mocked(reserveShareTab).mockReturnValue(makeTab());
        const view = mount();

        await fireEvent.click(screen.getByTestId('support-social-share-copy'));
        await waitFor(() => expect(screen.getByTestId('support-social-share-copy')).toHaveAttribute('data-copy-state', 'copied'));
        expect(vi.getTimerCount()).toBeGreaterThan(0);

        view.unmount();
        expect(vi.getTimerCount()).toBe(0);
    });
});
