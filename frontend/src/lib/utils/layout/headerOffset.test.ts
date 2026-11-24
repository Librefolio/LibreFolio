// @vitest-environment jsdom
/**
 * headerOffset — what the app header takes of the window, and the scroll that brings a list's start back under it
 * (81 U38). Real stand-under-a-scroll is `e2e/settings/settings-filter-menu.spec.ts`; here the arithmetic and the guards.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {clearHeaderOffset, HEADER_OFFSET_EVENT, prefersReducedMotion, publishHeaderOffset, readHeaderHeight, readHeaderOffset, scrollStartIntoView, START_GAP} from './headerOffset';

function anchorAt(top: number): Element {
    const el = document.createElement('div');
    el.getBoundingClientRect = () => ({top, bottom: top + 10, left: 0, right: 10, width: 10, height: 10, x: 0, y: top, toJSON: () => ({})});
    return el;
}

let scrollTo: ReturnType<typeof vi.fn>;
let reduced = false;

beforeEach(() => {
    reduced = false;
    scrollTo = vi.fn();
    vi.stubGlobal('scrollTo', scrollTo);
    vi.stubGlobal('matchMedia', (query: string) => ({matches: reduced && query.includes('reduce'), media: query}));
    Object.defineProperty(window, 'scrollY', {value: 2000, configurable: true});
    Object.defineProperty(window, 'innerHeight', {value: 800, configurable: true});
    Object.defineProperty(document.documentElement, 'scrollHeight', {value: 8000, configurable: true});
    publishHeaderOffset(64, false);
});
afterEach(() => {
    clearHeaderOffset();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe('publishing', () => {
    it('the height while the header shows, 0 while it is hidden, the whole height in both', () => {
        expect({offset: readHeaderOffset(), height: readHeaderHeight()}).toEqual({offset: 64, height: 64});
        publishHeaderOffset(64, true);
        expect({offset: readHeaderOffset(), height: readHeaderHeight()}).toEqual({offset: 0, height: 64});
        expect(document.documentElement.style.getPropertyValue('--lf-header-offset')).toBe('0px');
    });

    it('rounds a measured height to a whole pixel and never goes below 0', () => {
        publishHeaderOffset(64.4, false);
        expect(readHeaderOffset()).toBe(64);
        publishHeaderOffset(-5, false);
        expect(readHeaderOffset()).toBe(0);
    });

    it('says so on window at every publication and at the clear', () => {
        const heard = vi.fn();
        window.addEventListener(HEADER_OFFSET_EVENT, heard);
        publishHeaderOffset(70, false);
        clearHeaderOffset();
        window.removeEventListener(HEADER_OFFSET_EVENT, heard);
        expect(heard).toHaveBeenCalledTimes(2);
    });

    it('without a header both read 0', () => {
        clearHeaderOffset();
        expect({offset: readHeaderOffset(), height: readHeaderHeight()}).toEqual({offset: 0, height: 0});
    });
});

describe('scrollStartIntoView', () => {
    it('brings a start above the window back 16 px under the whole header, and says it moved', () => {
        expect(scrollStartIntoView(anchorAt(-1500))).toBe(true);
        // now at -1500 → wanted at 64 + 16: the page scrolls up by 1580 from 2000
        expect(scrollTo).toHaveBeenCalledWith({top: 2000 - 1500 - (64 + START_GAP), behavior: 'smooth'});
    });

    it('stops at the WHOLE header height even while it is hidden: a scroll up shows it again', () => {
        publishHeaderOffset(64, true);
        scrollStartIntoView(anchorAt(-100));
        expect(scrollTo).toHaveBeenCalledWith({top: 2000 - 100 - 80, behavior: 'smooth'});
    });

    it('moves nothing when the start is already at or under the stop', () => {
        expect(scrollStartIntoView(anchorAt(80))).toBe(false);
        expect(scrollStartIntoView(anchorAt(300))).toBe(false);
        expect(scrollTo).not.toHaveBeenCalled();
    });

    it('moves a start that sits under the header itself', () => {
        expect(scrollStartIntoView(anchorAt(30))).toBe(true);
        expect(scrollTo).toHaveBeenCalledWith({top: 2000 + 30 - 80, behavior: 'smooth'});
    });

    it('does not animate when the person asked for less motion', () => {
        reduced = true;
        expect(prefersReducedMotion()).toBe(true);
        scrollStartIntoView(anchorAt(-100));
        expect(scrollTo).toHaveBeenCalledWith(expect.objectContaining({behavior: 'auto'}));
    });

    it('never goes above the top of the page', () => {
        Object.defineProperty(window, 'scrollY', {value: 40, configurable: true});
        scrollStartIntoView(anchorAt(-200));
        expect(scrollTo).toHaveBeenCalledWith({top: 0, behavior: 'smooth'});
    });

    it('leaves a page that cannot scroll, and a missing anchor, alone', () => {
        Object.defineProperty(document.documentElement, 'scrollHeight', {value: 600, configurable: true});
        expect(scrollStartIntoView(anchorAt(-100))).toBe(false);
        expect(scrollStartIntoView(null)).toBe(false);
        expect(scrollStartIntoView(undefined)).toBe(false);
        expect(scrollTo).not.toHaveBeenCalled();
    });
});
