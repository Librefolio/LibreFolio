/**
 * Whether the PDF preview has finished drawing what it shows: the state the preview
 * publishes as `data-state` (and `aria-busy`) on its stage.
 *
 * The viewer (EmbedPDF) draws a page as tiles, asynchronously, long after the preview's
 * own fetch is done — so the shell's `data-busy` says nothing about it. What the viewer
 * does report: the document opened, or failed to; and, for every page in view, its
 * tiles with their status (`queued`, `rendering`, `ready`). While a page is redrawn —
 * after a zoom or a scroll — the tiles it showed before stay on screen as fallbacks,
 * until all the new ones are ready. So what is on screen is final only when every tile
 * that is not a fallback is ready.
 *
 * Pure: the component feeds it the viewer's latest reports, and this decides.
 */

export type PdfPreviewState = 'loading' | 'ready' | 'error';

/** A tile as the viewer reports it: only what the decision reads. */
export interface PdfPreviewTile {
    status: 'queued' | 'rendering' | 'ready';
    isFallback?: boolean;
}

/** The viewer's latest reports. `tiles` is null until the first tile report. */
export interface PdfPreviewReports {
    opened: boolean;
    /** The latest attempt to open failed: a broken file, or a password still missing or wrong. A later open clears it. */
    failed: boolean;
    tiles: Readonly<Record<number, readonly PdfPreviewTile[]>> | null;
}

export const NO_PDF_REPORTS: PdfPreviewReports = {opened: false, failed: false, tiles: null};

/**
 * - `error` while the latest attempt to open has failed, whatever else was reported;
 * - `ready` when it is open and every tile in view that is not a fallback is ready —
 *   at least one: before the first layout no page is in view yet, and nothing drawn
 *   is not "drawn";
 * - `loading` otherwise.
 */
export function pdfPreviewState(reports: PdfPreviewReports): PdfPreviewState {
    if (reports.failed) return 'error';
    if (!reports.opened || reports.tiles === null) return 'loading';
    const drawn = Object.values(reports.tiles)
        .flat()
        .filter((tile) => !tile.isFallback);
    return drawn.length > 0 && drawn.every((tile) => tile.status === 'ready') ? 'ready' : 'loading';
}
