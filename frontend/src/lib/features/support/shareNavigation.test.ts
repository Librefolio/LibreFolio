// @vitest-environment jsdom
import {afterEach, describe, expect, it, vi} from 'vitest';
import {reserveShareTab} from './shareNavigation';

interface StubTabDocument {
    createElement: ReturnType<typeof vi.fn>;
    head: {
        append: ReturnType<typeof vi.fn>;
    };
    body: {
        append: ReturnType<typeof vi.fn>;
    };
}

interface StubTab {
    closed: boolean;
    opener: unknown;
    document: StubTabDocument;
    location: {
        replace: ReturnType<typeof vi.fn>;
    };
    close: ReturnType<typeof vi.fn>;
}

function makeTab(): {tab: StubTab; meta: HTMLMetaElement; link: HTMLAnchorElement} {
    const meta = document.createElement('meta');
    const link = document.createElement('a');
    vi.spyOn(link, 'click').mockImplementation(() => {});
    const tab: StubTab = {
        closed: false,
        opener: window,
        document: {
            createElement: vi.fn((tag: string) => (tag === 'meta' ? meta : link)),
            head: {append: vi.fn()},
            body: {append: vi.fn()},
        },
        location: {
            replace: vi.fn(),
        },
        close: vi.fn(),
    };
    return {tab, meta, link};
}

afterEach(() => {
    vi.restoreAllMocks();
});

describe('reserveShareTab', () => {
    it('returns null when the browser blocks the popup reservation', () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null);

        expect(reserveShareTab()).toBeNull();
        expect(open).toHaveBeenCalledWith('about:blank', '_blank');
    });

    it('wraps the reserved tab with no-opener, no-referrer and helper methods', () => {
        const {tab, meta, link} = makeTab();
        const open = vi.spyOn(window, 'open').mockReturnValue(tab as unknown as Window);

        const reserved = reserveShareTab();

        expect(open).toHaveBeenCalledWith('about:blank', '_blank');
        expect(tab.opener).toBeNull();
        expect(tab.document.createElement).toHaveBeenCalledWith('meta');
        expect(meta.name).toBe('referrer');
        expect(meta.content).toBe('no-referrer');
        expect(tab.document.head.append).toHaveBeenCalledWith(meta);
        expect(reserved?.closed).toBe(false);

        reserved?.navigate('https://example.invalid/support');
        expect(link.href).toBe('https://example.invalid/support');
        expect(link.target).toBe('_self');
        expect(link.rel).toBe('noopener noreferrer');
        expect(link.referrerPolicy).toBe('no-referrer');
        expect(tab.document.body.append).toHaveBeenCalledWith(link);
        expect(link.click).toHaveBeenCalledTimes(1);
        expect(tab.location.replace).not.toHaveBeenCalled();

        reserved?.close();
        expect(tab.close).toHaveBeenCalledTimes(1);
    });

    it('reflects the live closed state of the underlying tab', () => {
        const {tab} = makeTab();
        vi.spyOn(window, 'open').mockReturnValue(tab as unknown as Window);

        const reserved = reserveShareTab();
        expect(reserved?.closed).toBe(false);

        tab.closed = true;
        expect(reserved?.closed).toBe(true);
    });

    it('closes the blank tab and rethrows when blank-page hardening fails', () => {
        const error = new Error('head locked');
        const {tab} = makeTab();
        tab.document.head.append.mockImplementation(() => {
            throw error;
        });
        vi.spyOn(window, 'open').mockReturnValue(tab as unknown as Window);

        expect(() => reserveShareTab()).toThrow(error);
        expect(tab.close).toHaveBeenCalledTimes(1);
    });
});
