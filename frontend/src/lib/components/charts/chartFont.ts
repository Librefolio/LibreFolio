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
