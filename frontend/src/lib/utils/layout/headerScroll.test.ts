// @vitest-environment node
import {afterEach, beforeEach, describe, expect, it} from 'vitest';
import {clampDocumentScrollY, getDocumentScrollMaxY, getDocumentScrollY} from './headerScroll';

describe('clampDocumentScrollY', () => {
    it.each([
        {scrollY: -30, maxScrollY: 100, expected: 0},
        {scrollY: -0, maxScrollY: 100, expected: 0},
        {scrollY: 0, maxScrollY: 100, expected: 0},
        {scrollY: 42, maxScrollY: 100, expected: 42},
        {scrollY: 42.75, maxScrollY: 100, expected: 42.75},
        {scrollY: 100, maxScrollY: 100, expected: 100},
        {scrollY: 130, maxScrollY: 100, expected: 100},
        {scrollY: 130, maxScrollY: 100.5, expected: 100.5},
    ])('clamps $scrollY within [0, $maxScrollY] to $expected', ({scrollY, maxScrollY, expected}) => {
        expect(clampDocumentScrollY(scrollY, maxScrollY)).toBe(expected);
    });

    it.each([NaN, Infinity, -Infinity])('returns zero for non-finite offset %s', (scrollY) => {
        expect(clampDocumentScrollY(scrollY, 100)).toBe(0);
    });

    it.each([0, -100, NaN, Infinity, -Infinity])('returns zero for unusable maximum %s', (maxScrollY) => {
        expect(clampDocumentScrollY(40, maxScrollY)).toBe(0);
    });
});

type ScrollMetrics = {scrollHeight?: number; scrollTop?: number};
type SyntheticWindow = {innerHeight: number; scrollY?: number};
type SyntheticDocument = {
    scrollingElement: ScrollMetrics | null | undefined;
    documentElement: {scrollHeight: number; scrollTop?: number};
};

describe('document scroll readers', () => {
    let browserWindow: SyntheticWindow;
    let browserDocument: SyntheticDocument;
    let originalWindow: PropertyDescriptor | undefined;
    let originalDocument: PropertyDescriptor | undefined;

    function setGlobal(name: 'window' | 'document', value: unknown): void {
        Object.defineProperty(globalThis, name, {configurable: true, writable: true, value});
    }

    function restoreGlobal(name: 'window' | 'document', descriptor: PropertyDescriptor | undefined): void {
        if (descriptor) {
            Object.defineProperty(globalThis, name, descriptor);
        } else {
            Reflect.deleteProperty(globalThis, name);
        }
    }

    beforeEach(() => {
        // Replace only our two globals, never mutate an existing browser object.
        originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');
        originalDocument = Object.getOwnPropertyDescriptor(globalThis, 'document');
        browserWindow = {innerHeight: 800, scrollY: 125.5};
        browserDocument = {
            scrollingElement: {scrollHeight: 2000, scrollTop: 450},
            documentElement: {scrollHeight: 3200, scrollTop: 900},
        };
        setGlobal('window', browserWindow);
        setGlobal('document', browserDocument);
    });

    afterEach(() => {
        // Preserve original accessors/flags as well as values and property absence.
        restoreGlobal('document', originalDocument);
        restoreGlobal('window', originalWindow);
    });

    it.each(['window', 'document', 'both'] as const)('returns zero when %s is unavailable', (missing) => {
        if (missing === 'window' || missing === 'both') setGlobal('window', undefined);
        if (missing === 'document' || missing === 'both') setGlobal('document', undefined);

        expect(getDocumentScrollMaxY()).toBe(0);
        expect(getDocumentScrollY()).toBe(0);
    });

    describe('getDocumentScrollMaxY', () => {
        it('uses the scrolling element rather than a taller document element', () => {
            expect(getDocumentScrollMaxY()).toBe(1200);
        });

        it.each([null, undefined])('falls back to documentElement when scrollingElement is %s', (scrollingElement) => {
            browserDocument.scrollingElement = scrollingElement;

            expect(getDocumentScrollMaxY()).toBe(2400);
        });

        it('falls back to documentElement when the scrolling element has no height', () => {
            browserDocument.scrollingElement = {scrollTop: 450};

            expect(getDocumentScrollMaxY()).toBe(2400);
        });

        it.each([
            {scrollHeight: 0, expected: 0},
            {scrollHeight: 600, expected: 0},
            {scrollHeight: 800, expected: 0},
            {scrollHeight: 801, expected: 1},
        ])('returns $expected for document height $scrollHeight and viewport 800', ({scrollHeight, expected}) => {
            browserDocument.scrollingElement = {scrollHeight};

            expect(getDocumentScrollMaxY()).toBe(expected);
        });
    });

    describe('getDocumentScrollY', () => {
        it.each([
            {scrollY: 0, expected: 0},
            {scrollY: 125.5, expected: 125.5},
            {scrollY: -20, expected: 0},
            {scrollY: 1800, expected: 1200},
            {scrollY: NaN, expected: 0},
            {scrollY: Infinity, expected: 0},
            {scrollY: -Infinity, expected: 0},
        ])('prefers window offset $scrollY and normalizes it to $expected', ({scrollY, expected}) => {
            // Both element offsets differ, including when window.scrollY is zero.
            browserWindow.scrollY = scrollY;

            expect(getDocumentScrollY()).toBe(expected);
        });

        it('reads scrollingElement.scrollTop when window.scrollY is unavailable', () => {
            delete browserWindow.scrollY;

            expect(getDocumentScrollY()).toBe(450);
        });

        it('reads documentElement.scrollTop when window.scrollY and scrollingElement are unavailable', () => {
            delete browserWindow.scrollY;
            browserDocument.scrollingElement = null;

            expect(getDocumentScrollY()).toBe(900);
        });

        it('returns zero when neither offset source supplies a value', () => {
            delete browserWindow.scrollY;
            browserDocument.scrollingElement = {scrollHeight: 2000};

            expect(getDocumentScrollY()).toBe(0);
        });

        it('also clamps the fallback element offset', () => {
            delete browserWindow.scrollY;
            browserDocument.scrollingElement = {scrollHeight: 2000, scrollTop: 1500};

            expect(getDocumentScrollY()).toBe(1200);
        });

        it('re-reads offsets and dimensions instead of retaining a previous range', () => {
            expect(getDocumentScrollMaxY()).toBe(1200);
            expect(getDocumentScrollY()).toBe(125.5);

            browserWindow.scrollY = 1100;
            expect(getDocumentScrollY()).toBe(1100);

            browserDocument.scrollingElement = {scrollHeight: 1400, scrollTop: 450};
            expect(getDocumentScrollMaxY()).toBe(600);
            expect(getDocumentScrollY()).toBe(600);

            browserWindow.innerHeight = 1600;
            expect(getDocumentScrollMaxY()).toBe(0);
            expect(getDocumentScrollY()).toBe(0);
        });
    });
});
