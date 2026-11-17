// @vitest-environment jsdom
/**
 * AssetSetLossComparisonSection — the column titles are measured again once the page's fonts are in (RN-09, C-23).
 *
 * Every value column opens as wide as its own title, measured on a canvas in the page's typeface
 * (`headerWidth(title, measureHeaderTitle)`). Measured before the web font has loaded, the canvas
 * draws the fallback face: the column comes out at the fallback's width and, once Inter lands, the
 * last title — «Risalita al massimo», in Italian — is cut on the right. So the widths are taken again
 * when `document.fonts.ready` settles.
 *
 * jsdom has neither fonts nor a canvas, so both are stood in for before the first render (the canvas
 * is created on the first measure): a canvas whose glyphs are 7 px wide with the fallback face and
 * 10 px once the fonts are in, and a `document.fonts.ready` this file resolves. Its own file because
 * `measureHeaderTitle` keeps its canvas at module scope: in a file where another case measured
 * first, jsdom's missing canvas would already be cached.
 *
 * Red first: today the widths are taken once, at mount, with the fallback face, and never again.
 */
import {afterAll, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, render, screen, setupI18n, waitFor} from '$test/component';

import AssetSetLossComparisonSection from './AssetSetLossComparisonSection.svelte';
import {headerWidth, measureHeaderTitle} from './riskReturnLevel';

let fontsLoaded = false;
let releaseFonts: () => void = () => undefined;

class FakeCanvas {
    getContext(): {font: string; measureText: (text: string) => {width: number}} {
        return {font: '', measureText: (text: string) => ({width: text.length * (fontsLoaded ? 10 : 7)})};
    }
}

const ASSETS = [101, 102];
const LABELS: ReadonlyMap<number, string> = new Map([
    [101, 'Invented fund one'],
    [102, 'Invented fund two'],
]);

describe('AssetSetLossComparisonSection — the column widths follow the fonts', () => {
    beforeAll(async () => {
        vi.stubGlobal('OffscreenCanvas', FakeCanvas);
        Object.defineProperty(document, 'fonts', {
            configurable: true,
            value: {ready: new Promise<void>((resolve) => (releaseFonts = resolve))},
        });
        vi.stubGlobal('localStorage', {getItem: () => null, setItem: () => undefined, removeItem: () => undefined});
        await setupI18n('it');
    });

    afterAll(() => {
        cleanup();
        vi.unstubAllGlobals();
    });

    it('opens «Risalita al massimo» at the fallback width, then widens it to the loaded face once document.fonts.ready settles', async () => {
        render(AssetSetLossComparisonSection, {props: {assetIds: ASSETS, assetLabels: LABELS, assetIcons: new Map(), dailyVar: null, monthlyVar: null, drawdown: null, loading: false}});
        const title = 'Risalita al massimo';
        const header = screen.getByTestId('dt-header-toPeak');
        const fallback = headerWidth(title, measureHeaderTitle);
        expect(header.style.width, 'premise: before the fonts are in, the column is measured with the fallback face').toBe(`${fallback}px`);

        fontsLoaded = true;
        releaseFonts();
        const loaded = headerWidth(title, measureHeaderTitle);
        expect(loaded, 'premise: the loaded face is wider than the fallback').toBeGreaterThan(fallback);
        // Read again: the table is drawn anew with the new widths, so the title cell is a new element.
        await waitFor(() => expect(screen.getByTestId('dt-header-toPeak').style.width, 'the fonts came in and the column kept the fallback width: its title is cut on the right').toBe(`${loaded}px`));
        expect(screen.getByTestId('dt-header-toPeak').style.minWidth).toBe(`${loaded}px`);
    });
});
