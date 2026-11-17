/**
 * When the face the column titles are drawn in has come in, as a reactive count the titles are measured against
 * (RN-09, C-23).
 *
 * The risk tables open every value column as wide as its own title, measured on a canvas in the page's
 * typeface (`headerWidth(title, measureHeaderTitle)`). Measured before the web font has loaded, the canvas
 * draws the fallback face, and once the real one lands a title wider than its column is cut on the right —
 * «Risalita al massimo», the last column of the lab's loss table, in Italian. A width computed in a `$derived`
 * that reads this count is computed again when the face is in.
 *
 * Asked once, on the first read, for the title face itself (`HEADER_FONT` in the page's family), as
 * `chartFont.ts` asks for the flag face: already in (`fonts.check`), the count stays 0 and nothing is drawn
 * twice; otherwise it is requested (`fonts.load`) and the count rises once when the request settles, loaded or
 * not. A browser without `load` falls back on `document.fonts.ready`. Where nothing can load a font (no
 * `document.fonts`: a server) the count stays 0.
 */
import {HEADER_FONT} from './riskReturnLevel';

let settled = $state(0);
let asked = false;

function raise(): void {
    settled += 1;
}

export function headerFontsSettled(): number {
    if (!asked) {
        asked = true;
        const fonts = typeof document === 'undefined' ? undefined : document.fonts;
        if (!fonts) return settled;
        try {
            const face = `${HEADER_FONT} ${getComputedStyle(document.body).fontFamily}`;
            if (fonts.check?.(face)) return settled;
            const request = fonts.load ? fonts.load(face) : fonts.ready;
            request?.then(raise, raise);
        } catch {
            // A face string the browser refuses: the first measure stays, as before RN-09.
        }
    }
    return settled;
}
