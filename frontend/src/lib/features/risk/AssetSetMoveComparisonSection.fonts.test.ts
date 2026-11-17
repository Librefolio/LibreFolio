// @vitest-environment jsdom
/**
 * AssetSetMoveComparisonSection — the column titles are measured again once the page's fonts are in (RN-19, the twin's
 * rule of RN-09).
 *
 * The move table sizes its value columns like the loss table: as wide as each title, measured on a canvas in the
 * page's typeface, taken again when `document.fonts.ready` settles. jsdom has neither fonts nor a canvas, so both are
 * stood in for before the first render: glyphs 7 px wide with the fallback face, 10 px once the fonts are in. Its own
 * file because `measureHeaderTitle` keeps its canvas at module scope.
 */
import {afterAll, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, render, screen, setupI18n, waitFor} from '$test/component';

import AssetSetMoveComparisonSection from './AssetSetMoveComparisonSection.svelte';
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

describe('AssetSetMoveComparisonSection — the column widths follow the fonts', () => {
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

    it('opens «Salita più grande» at the fallback width, then widens it to the loaded face once document.fonts.ready settles', async () => {
        render(AssetSetMoveComparisonSection, {props: {assetIds: ASSETS, assetLabels: LABELS, assetIcons: new Map(), kpi: null, monthlyVar: null, drawdown: null, loading: false}});
        const title = 'Salita più grande';
        const header = screen.getByTestId('dt-header-rally');
        const fallback = headerWidth(title, measureHeaderTitle);
        expect(header.style.width, 'premise: before the fonts are in, the column is measured with the fallback face').toBe(`${fallback}px`);

        fontsLoaded = true;
        releaseFonts();
        const loaded = headerWidth(title, measureHeaderTitle);
        expect(loaded, 'premise: the loaded face is wider than the fallback').toBeGreaterThan(fallback);
        // Read again: the table is drawn anew with the new widths, so the title cell is a new element.
        await waitFor(() => expect(screen.getByTestId('dt-header-rally').style.width, 'the fonts came in and the column kept the fallback width: its title is cut on the right').toBe(`${loaded}px`));
        expect(screen.getByTestId('dt-header-rally').style.minWidth).toBe(`${loaded}px`);
    });
});
