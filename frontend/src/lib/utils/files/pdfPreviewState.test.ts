/**
 * pdfPreviewState — unit tests
 *
 * The decision behind the PDF preview's `data-state` (and `aria-busy`): whether the pages in
 * view are drawn. The viewer reports three things — the document opened, the document failed,
 * and, for every page in view, its tiles with their status — and this function is the only
 * place that reads them. So every rule the preview publishes is pinned here, from the reports
 * alone, without a viewer.
 *
 * The tiles are written the way the viewer's tiling plugin reports them (plugin-tiling,
 * `visibleTiles`: page index → tiles, each `queued`, `rendering` or `ready`; the tiles a page
 * showed before a zoom stay listed as `isFallback` until every new one is ready). Only the two
 * fields the decision reads are given; the rest of a tile is not its business.
 */
import {describe, expect, it} from 'vitest';

import {NO_PDF_REPORTS, pdfPreviewState, type PdfPreviewReports, type PdfPreviewTile} from './pdfPreviewState';

const ready: PdfPreviewTile = {status: 'ready'};
const queued: PdfPreviewTile = {status: 'queued'};
const rendering: PdfPreviewTile = {status: 'rendering'};
/** A tile drawn at the previous zoom, kept on screen while the new ones arrive. */
const fallback = (status: PdfPreviewTile['status'] = 'ready'): PdfPreviewTile => ({status, isFallback: true});

/** Reports of an opened document whose pages in view carry `tiles`. */
function opened(tiles: PdfPreviewReports['tiles']): PdfPreviewReports {
    return {opened: true, failed: false, tiles};
}

describe('pdfPreviewState — error', () => {
    it('is error once the document failed, even with every tile in view ready', () => {
        expect(pdfPreviewState({opened: true, failed: true, tiles: {0: [ready, ready]}})).toBe('error');
    });

    it('is error when the document failed before it ever opened or drew a tile', () => {
        expect(pdfPreviewState({opened: false, failed: true, tiles: null})).toBe('error');
    });

    it('is error when the failure comes with tiles still rendering', () => {
        expect(pdfPreviewState({opened: true, failed: true, tiles: {0: [ready, rendering]}})).toBe('error');
    });
});

describe('pdfPreviewState — loading', () => {
    it('starts loading: no report at all', () => {
        expect(pdfPreviewState(NO_PDF_REPORTS)).toBe('loading');
    });

    it('is loading before the document opened, whatever the tiles say', () => {
        expect(pdfPreviewState({opened: false, failed: false, tiles: {0: [ready]}})).toBe('loading');
    });

    it('is loading when the document opened but no tile report came yet', () => {
        expect(pdfPreviewState(opened(null))).toBe('loading');
    });

    it('is loading with an empty tiles record: no page is in view yet', () => {
        expect(pdfPreviewState(opened({}))).toBe('loading');
    });

    it('is loading when the pages in view list no tile: nothing drawn is not "drawn"', () => {
        expect(pdfPreviewState(opened({0: [], 1: []}))).toBe('loading');
    });

    it('is loading while a tile in view is queued', () => {
        expect(pdfPreviewState(opened({0: [ready, queued, ready]}))).toBe('loading');
    });

    it('is loading while a tile in view is rendering', () => {
        expect(pdfPreviewState(opened({0: [ready, rendering]}))).toBe('loading');
    });

    it('is loading when one page is drawn and the next page in view is not', () => {
        expect(pdfPreviewState(opened({0: [ready, ready], 1: [ready, queued]}))).toBe('loading');
    });
});

describe('pdfPreviewState — ready', () => {
    it('is ready when every tile of the single page in view is ready', () => {
        expect(pdfPreviewState(opened({0: [ready]}))).toBe('ready');
    });

    it('is ready when every tile of every page in view is ready', () => {
        expect(pdfPreviewState(opened({0: [ready, ready, ready], 1: [ready, ready], 2: [ready]}))).toBe('ready');
    });

    it('is ready with a page in view that lists no tile, when the others are drawn', () => {
        expect(pdfPreviewState(opened({0: [ready, ready], 1: []}))).toBe('ready');
    });

    it('reads a tile with no isFallback flag as one of the new tiles', () => {
        expect(pdfPreviewState(opened({0: [{status: 'ready', isFallback: false}, {status: 'ready'}]}))).toBe('ready');
        expect(pdfPreviewState(opened({0: [{status: 'ready'}, {status: 'queued'}]}))).toBe('loading');
    });
});

describe('pdfPreviewState — fallback tiles are ignored', () => {
    it('is loading when the old tiles are ready but a new tile is still queued (a redraw after a zoom)', () => {
        expect(pdfPreviewState(opened({0: [fallback(), fallback(), queued]}))).toBe('loading');
    });

    it('is loading when only fallback tiles are listed: the new ones are not even queued yet', () => {
        expect(pdfPreviewState(opened({0: [fallback(), fallback()]}))).toBe('loading');
    });

    it('is ready when every new tile is ready, whatever the fallbacks still say', () => {
        expect(pdfPreviewState(opened({0: [fallback('rendering'), ready, ready]}))).toBe('ready');
        expect(pdfPreviewState(opened({0: [fallback(), ready], 1: [fallback('queued'), ready]}))).toBe('ready');
    });

    it('is loading when one page is redrawn and another is drawn: the redrawn page decides', () => {
        expect(pdfPreviewState(opened({0: [ready, ready], 1: [fallback(), rendering]}))).toBe('loading');
    });
});
