/**
 * Colours drawn outside CSS — handed to a canvas library or baked into an SVG data URL — where a
 * `var(--lf-cmp-*)` token cannot reach (plan 55, workstream R). Same values and same strings as before: the
 * designer decides any change (phase B).
 */

/**
 * Spreadsheet preview (`FilePreviewModal`, cheetah-grid): rows the caller points at. Amber, matching the
 * "look at this row" accent used by the evidence tables. Same in both themes.
 */
export const SPREADSHEET_TARGET_ROW_BG = 'rgba(251, 191, 36, 0.35)';

/** Spreadsheet preview, light theme: firmer grid lines over cheetah-grid's `MATERIAL_DESIGN` theme. */
export const SPREADSHEET_LIGHT_BORDERS = {borderColor: '#cbd5e1', frozenRowsBorderColor: '#94a3b8'};

/** Spreadsheet preview, dark theme: a fresh cheetah-grid theme object at every call. */
export function buildDarkSpreadsheetTheme() {
    return {
        color: '#e2e8f0',
        frozenRowsColor: '#cbd5e1',
        defaultBgColor: '#0f172a',
        frozenRowsBgColor: '#111827',
        selectionBgColor: 'rgba(37, 99, 235, 0.38)',
        highlightBgColor: '#1e293b',
        borderColor: '#475569',
        frozenRowsBorderColor: '#64748b',
        highlightBorderColor: '#60a5fa',
        checkbox: {
            uncheckBgColor: '#0f172a',
            checkBgColor: '#2563eb',
            borderColor: '#64748b',
        },
        radioButton: {
            checkColor: '#60a5fa',
            checkBorderColor: '#60a5fa',
            uncheckBorderColor: '#64748b',
            uncheckBgColor: '#0f172a',
            checkBgColor: '#0f172a',
        },
        button: {
            color: '#e2e8f0',
            bgColor: '#2563eb',
        },
        tree: {
            lineColor: '#475569',
        },
        header: {
            sortArrowColor: '#94a3b8',
        },
        messages: {
            infoBgColor: '#1d4ed8',
            errorBgColor: '#b91c1c',
            warnBgColor: '#b45309',
        },
        indicators: {
            topLeftColor: '#475569',
        },
        underlayBackgroundColor: '#0f172a',
    };
}

/** Placeholder images of `LazyImage` (SVG data URLs), the same in both themes. */
export const IMAGE_PLACEHOLDER_COLORS = {background: '#e5e7eb', shape: '#9ca3af'};

/** Initial of the uploader avatars in the files table (SVG data URL), drawn over a `getStringColor` disc. */
export const FILE_AVATAR_INITIAL_COLOR = '#ffffff';
