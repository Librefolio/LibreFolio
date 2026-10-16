/**
 * The font of the text ECharts draws (K-13): legends, labels and axes on the canvas, and the HTML tooltip.
 *
 * ECharts does not read the app's CSS. It draws on a canvas and writes its tooltip with an inline `font`, both in its
 * own default family: `sans-serif`, or `'Microsoft YaHei'` on Windows. A flag — the regional indicators U+1F1E6–1F1FF —
 * therefore fell to whatever the system does with them, which on Windows and Linux is two letters. The app has one face
 * for flags, `'LF Flags'` (`static/lf-flags.css`): Apple's flags on Apple devices, the self-hosted Noto subset
 * elsewhere. Its `unicode-range` holds the flags and nothing else, so every other character falls through to the next
 * family — ECharts' own default, chosen the way ECharts chooses it (`echarts/lib/model/globalDefault.js`) — and the
 * text that is not a flag keeps the font it had.
 *
 * A canvas paints its text once, with the faces loaded at that moment, and the browser fetches a `unicode-range` face
 * only for text in the page that needs it — canvas text does not count. So the face is asked for here, when the first
 * chart module loads and before any chart can paint ({@link chartFontReady}), and a chart that painted before it
 * arrived paints again once it is in (`scheduleFirstRenderStabilityFix`).
 *
 * The colours of the charts live in `$lib/theme/chartTheme`; this module holds no colour.
 *
 * @module lib/components/charts/chartFont
 */

/** ECharts' own default family, read the way ECharts reads it. */
const ECHARTS_DEFAULT_FAMILY = typeof navigator !== 'undefined' && /^Win/.test(navigator.platform || '') ? "'Microsoft YaHei'" : 'sans-serif';

/** Every chart's font family: the flag face first, then ECharts' default. */
export const CHART_FONT_FAMILY = `'LF Flags', ${ECHARTS_DEFAULT_FAMILY}`;

/**
 * The theme every chart is created with: `echarts.init(element, CHART_INIT_THEME, …)`.
 *
 * Its `textStyle` is ECharts' global font, for the canvas text and for the tooltip's inline `font`. A theme is merged
 * again on every `setOption`, a `notMerge` one included, which an option-level `textStyle` would not survive.
 */
export const CHART_INIT_THEME = {textStyle: {fontFamily: CHART_FONT_FAMILY}};

/** The face, as a CSS `font` shorthand the font loading API accepts. */
const FLAG_FONT = "16px 'LF Flags'";

/** A flag to ask for the face with: it holds the regional indicators and nothing else, so other text would load nothing. */
const FLAG_SAMPLE = '\u{1F1FA}\u{1F1F8}';

let flagFaceRequest: Promise<void> | undefined;

/**
 * Asks the browser for the flag face, once, and resolves when the request has settled. It never rejects and never
 * throws: a face that fails to load leaves the system's fallback, as before K-13. Where nothing can load a font — no
 * `document.fonts`, as in a test or on a server — it resolves at once.
 */
export function chartFontReady(): Promise<void> {
    if (!flagFaceRequest) {
        const fonts = typeof document === 'undefined' ? undefined : document.fonts;
        try {
            flagFaceRequest = fonts?.load
                ? fonts.load(FLAG_FONT, FLAG_SAMPLE).then(
                      () => undefined,
                      () => undefined,
                  )
                : Promise.resolve();
        } catch {
            // The request runs when the first chart module loads: a throw here would break every chart's import.
            flagFaceRequest = Promise.resolve();
        }
    }
    return flagFaceRequest;
}

/** Whether the flag face is already in, so that a canvas painting now draws flags with it. True where fonts cannot load. */
export function chartFontLoaded(): boolean {
    const fonts = typeof document === 'undefined' ? undefined : document.fonts;
    try {
        return !fonts?.check || fonts.check(FLAG_FONT, FLAG_SAMPLE);
    } catch {
        return true;
    }
}

// Every chart imports this module before it can paint: asking for the face here puts the request ahead of the first paint.
void chartFontReady();
