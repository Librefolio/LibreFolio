/**
 * chartFlagFont.test.ts — K-13: a flag drawn by ECharts needs the 'LF Flags' face.
 *
 * ## What it protects (K-13)
 *
 * The app draws flags — the regional indicators U+1F1E6–1F1FF — with one global face, 'LF Flags': Apple's flags on
 * Apple devices, the self-hosted Noto subset elsewhere (`static/lf-flags.css`, gate `src/flagFont.gate.test.ts`). The
 * app's HTML reaches it through the stacks of `app.css`. ECharts does not: it paints text with the font family of its own
 * option, `sans-serif` by default, so a flag in a legend, a label, an axis or a tooltip falls to whatever the system has.
 *
 * The design these tests target (the coordinator's decision, implemented in step 2):
 * - `$lib/components/charts/chartFont` exports `CHART_FONT_FAMILY`, a CSS family list whose first family is 'LF Flags', followed by
 *   ECharts' own default so that no other glyph changes — `sans-serif` in ECharts 6.0.0, 'Microsoft YaHei' on Windows
 *   browsers (`node_modules/echarts/lib/model/globalDefault.js:104`) — and `CHART_INIT_THEME`, the theme object
 *   `{textStyle: {fontFamily: CHART_FONT_FAMILY}}`;
 * - every chart is created as `echarts.init(<el>, CHART_INIT_THEME, …)`. ECharts 6 takes a theme object as second
 *   argument; its `textStyle` is merged into the global text style (`mergeTheme`, `lib/model/Global.js:675`), which is
 *   the font of every text the instance draws unless a component sets its own family (`TEXT_PROPS_WITH_GLOBAL`,
 *   `lib/label/labelStyle.js:338`), and of the HTML tooltip; it is merged again on every reset, so it survives
 *   `setOption(option, true)`.
 *
 * ## Part A — the mechanism, with the real ECharts (no mock)
 *
 * A chart is rendered server-side to SVG (`init(null, theme, {renderer: 'svg', ssr: true, …})`, `renderToSVGString()`),
 * with flags in its legend, its x-axis categories and its pie labels. The font family of every `<text>` is read from the
 * `font-family` attribute, or from the `font-family` / `font` declaration of its `style` — zrender writes the family
 * verbatim, unescaped — quotes and entities normalised. Positive controls run on an inline theme, the mechanism with
 * nothing of K-13's: the first render, after `setOption(option, true)`, and with component text styles that set a colour
 * but no family. A detector control proves the reading sees a family that is not 'LF Flags'. Without a canvas zrender
 * estimates text widths; no width is asserted. The HTML tooltip (jsdom, `showTip`) is not covered here.
 *
 * ## Part B — every chart passes the theme and the density options (static scan)
 *
 * Every `echarts.init(` of the production sources passes exactly the identifier `CHART_INIT_THEME` as its second
 * argument. The scan reads every `.ts` and `.svelte` under `src/` — a superset of `src/lib`, where every chart lives
 * today — without `*.test.ts`, `*.spec.ts`, `.d.ts`, `__tests__/`, `__mocks__/` and the generated API clients; and
 * without `designer-lab/` (`src/lib/dev/designer-lab/`): its engine creates a 1×1 detached probe
 * (`engine/charts.ts:253`, `ec.init(host, null, …)`) only to reach the prototype every instance shares, and never paints
 * it. Comments are blanked before matching, offsets kept so the reported lines are the file's: doc comments name
 * `echarts.init()` without calling it (`echartsDataZoomTouchPan.ts:31`, `echartsTooltipHelpers.ts:273`,
 * `GrowthChart.svelte:323`, and `chartPixelRatio.ts`, which documents the rule below). In a `.svelte` file only the
 * `<script>` blocks are read; the blanking skips strings, templates and regex literals; the arguments are split by a
 * scanner that respects brackets and literals, since a call may span lines. A guard checks that no production module
 * reaches ECharts' `init` under another name, which this scan could not see. Sanity, path-agnostic: at least 18 calls in
 * at least 17 files (today: 18 in 17 — 15 component files, `LotGanttChart.svelte` with two, and the two PAC files
 * `ExposureBars` and `ExposureMaps`).
 *
 * The same scan holds DV's rule (`chartPixelRatio.ts`): every call passes `chartInitOptions(<its element>…)` as its
 * third argument — exactly that call, its first argument the call's own first argument (the same expression), more
 * arguments after it allowed — so that a chart is born at the screen's density of that moment and followed when it
 * changes. A literal `{renderer: 'canvas'}`, no third argument, another element, a spread or a call with something after
 * it would create a chart at the density zrender read when the page loaded, never followed. Since DV-14 (19/10/2026)
 * the 18 calls in 17 files all pass it, `PriceChartFull.svelte` and `CandlestickChart.svelte` included, the last two to
 * migrate. `PIXEL_RATIO_PENDING` stays, empty: a chart that cannot migrate at once is listed there with its reason, and
 * exempt. The list only shrinks and cannot go stale (the idea of `PENDING_READERS` in `src/lib/theme/roleColors.test.ts`
 * and of the allowlist of `src/lib/utils/core/escapeHtml.single.test.ts`): a listed file that is no longer a production
 * source the scan reads, that has no call any more, or whose every call passes `chartInitOptions` fails the gate, asking
 * for its line to go. Empty, that check passes on the real tree without reading a file. Synthetic controls come first,
 * and keep both checks biting: the rule tells those shapes apart, and the staleness check reports what it must.
 *
 * ## Why it was red before K-13 and DV
 *
 * - Part A: neither `CHART_FONT_FAMILY` nor `CHART_INIT_THEME` existed. They are reached through a namespace import, so a
 *   missing one is `undefined`, not an import error: the chart created with `CHART_INIT_THEME` drew in ECharts' default
 *   family, and the checks on the constants failed at their first assertion. Both live in
 *   `src/lib/components/charts/chartFont.ts`.
 * - Part B: all 18 calls passed `undefined` or nothing as second argument — e.g. `src/lib/components/charts/LineChart.svelte:384`
 *   (`echarts.init(chartContainer, undefined, {renderer: 'canvas'})`), `src/lib/features/risk/CorrelationHeatmap.svelte:458`
 *   (`echarts.init(container)`).
 * - Part B, DV's rule: all 18 calls passed `{renderer: 'canvas'}` or nothing as third argument — e.g. `LineChart.svelte`
 *   (`echarts.init(chartContainer, CHART_INIT_THEME, {renderer: 'canvas'})`), `CorrelationHeatmap.svelte`
 *   (`echarts.init(container, CHART_INIT_THEME)`) — and `chartInitOptions` did not exist. DV migrated 16 of them; the
 *   other two, `PriceChartFull.svelte` and `CandlestickChart.svelte`, waited in `PIXEL_RATIO_PENDING` until DV-14.
 *
 * Registered in chart-safety-unit (scripts/test_runner/_frontend_portfolio.py).
 */
import {existsSync, readdirSync, readFileSync} from 'node:fs';
import {basename, dirname, join, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import * as echarts from 'echarts';
import {describe, expect, it} from 'vitest';
import * as chartFont from '$lib/components/charts/chartFont';

/** The K-13 constants of chartFont, reached through the namespace: a missing one reads `undefined` and fails its own assertion, not the import of the whole file. */
const theme = chartFont as unknown as Record<string, unknown>;

const FLAG_FACE = 'LF Flags';

// =============================================================================
// Part A — reading the fonts of a server-side SVG
// =============================================================================

/** The positive controls' theme: the mechanism, with nothing of K-13's. */
const INLINE_THEME = {textStyle: {fontFamily: "'LF Flags', sans-serif"}};

/** Texts that carry a flag, one group per kind of drawn text. */
const LEGEND_TEXT = '🇮🇹 Italia';
const AXIS_TEXTS = ['🇩🇪 Deutschland', '🇪🇸 España'];
const PIE_TEXTS = ['🇵🇹 Portugal', '🇬🇷 Ellada'];

/** Component options merged into the flag chart: what a chart sets on its legend, its x-axis labels and its pie labels. */
interface Overrides {
    legend?: Record<string, unknown>;
    axisLabel?: Record<string, unknown>;
    pieLabel?: Record<string, unknown>;
}

/** A chart whose legend, x-axis categories and pie labels all carry flags. Nothing truncates them: a pie label defaults to `overflow: 'truncate'`. */
function flagOption(overrides: Overrides = {}): echarts.EChartsCoreOption {
    return {
        animation: false,
        legend: {top: 0, data: [LEGEND_TEXT], ...overrides.legend},
        grid: {left: 40, top: 50, width: 260, height: 220},
        xAxis: {type: 'category', data: AXIS_TEXTS, axisLabel: {interval: 0, ...overrides.axisLabel}},
        yAxis: {type: 'value'},
        series: [
            {type: 'bar', name: LEGEND_TEXT, data: [3, 5]},
            {type: 'pie', center: [480, 200], radius: [0, 50], label: {show: true, position: 'outside', overflow: 'none', ...overrides.pieLabel}, data: PIE_TEXTS.map((name, index) => ({name, value: 3 + 2 * index}))},
        ],
    };
}

/** The flag chart rendered server-side to SVG with `initTheme` — again after `setOption(option, true)` when `reset`. */
function renderSvg(initTheme: object | undefined, option: echarts.EChartsCoreOption, reset = false): string {
    const chart = echarts.init(null, initTheme, {renderer: 'svg', ssr: true, width: 640, height: 360});
    try {
        chart.setOption(option);
        if (reset) chart.setOption(option, true);
        return chart.renderToSVGString();
    } finally {
        chart.dispose();
    }
}

const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');

/** `&quot;`, `&#39;`, `&amp;`… back to their characters. */
function decodeEntities(text: string): string {
    const named: Record<string, string> = {quot: '"', apos: "'", amp: '&', lt: '<', gt: '>', nbsp: '\u00a0'};
    return text.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (whole, entity: string) => {
        const lower = entity.toLowerCase();
        if (lower.startsWith('#x')) return String.fromCodePoint(Number.parseInt(lower.slice(2), 16));
        if (lower.startsWith('#')) return String.fromCodePoint(Number.parseInt(lower.slice(1), 10));
        return named[lower] ?? whole;
    });
}

/** Split on the commas that are not inside quotes or parentheses (the reader of `src/flagFont.gate.test.ts`). */
function splitTopLevel(value: string): string[] {
    const parts: string[] = [];
    let current = '';
    let quote: string | null = null;
    let depth = 0;
    for (const c of value) {
        if (quote) {
            current += c;
            if (c === quote) quote = null;
            continue;
        }
        if (c === '"' || c === "'") quote = c;
        else if (c === '(') depth++;
        else if (c === ')') depth--;
        else if (c === ',' && depth === 0) {
            parts.push(current.trim());
            current = '';
            continue;
        }
        current += c;
    }
    if (current.trim()) parts.push(current.trim());
    return parts;
}

const unquote = (s: string): string => collapse(s.trim().replace(/^(['"])([\s\S]*)\1$/, '$2'));

/** A font-family value as the list of its families: quotes, entities and `!important` gone. */
const familyList = (value: string): string[] =>
    splitTopLevel(decodeEntities(value).replace(/!\s*important\s*$/i, ''))
        .map(unquote)
        .filter((family) => family !== '');

/**
 * An attribute of a `<text>` open tag. zrender does not escape attribute values, so a family quoted with `"` would close
 * a naive `"([^"]*)"`: the value ends at the quote that is followed by another attribute or by the end of the tag.
 */
function attributeOf(attributes: string, name: string): string | undefined {
    return new RegExp(`(?:^|\\s)${name}="([\\s\\S]*?)"(?=\\s+[\\w:-]+=|\\s*\\/?$)`).exec(attributes)?.[1];
}

/** The families a `<text>` is drawn with: its `font-family` attribute, else its style's `font-family`, else the families of its `font` shorthand. */
function familiesOf(attributes: string): string[] {
    const presentation = attributeOf(attributes, 'font-family');
    if (presentation !== undefined) return familyList(presentation);
    const style = decodeEntities(attributeOf(attributes, 'style') ?? '');
    const family = /(?:^|;)\s*font-family\s*:\s*([^;]*)/i.exec(style)?.[1];
    if (family !== undefined) return familyList(family);
    const shorthand = /(?:^|;)\s*font\s*:\s*([^;]*)/i.exec(style)?.[1];
    if (shorthand === undefined) return [];
    const afterSize = /(?:^|\s)\d*\.?\d+(?:px|pt|em|rem|%)(?:\/\S+)?\s+([\s\S]+)$/.exec(collapse(shorthand))?.[1];
    return afterSize === undefined ? [] : familyList(afterSize);
}

/** A text as the SVG draws it: its characters, and its font families in order. */
interface DrawnText {
    text: string;
    families: string[];
}

function drawnTexts(svg: string): DrawnText[] {
    return [...svg.matchAll(/<text\b([^>]*)>([\s\S]*?)<\/text>/g)].map(([, attributes, content]) => ({text: decodeEntities(content), families: familiesOf(attributes)}));
}

const describeText = ({text, families}: DrawnText): string => `«${text}» → ${families.length > 0 ? families.join(', ') : '(no family)'}`;

/** The texts not drawn with LF Flags first, described. */
const notFlagFirst = (texts: DrawnText[]): string[] => texts.filter((drawn) => drawn.families[0] !== FLAG_FACE).map(describeText);

/** Barrier: the legend, the x axis and the pie labels each drew their flags, so the check below is about flags. */
function expectFlagsDrawn(texts: DrawnText[]): void {
    const missing = [LEGEND_TEXT, ...AXIS_TEXTS, ...PIE_TEXTS].filter((flag) => !texts.some((drawn) => drawn.text.includes(flag)));
    expect(missing, `barrier: these flag texts were not drawn — drawn: ${texts.map(describeText).join(' | ')}`).toEqual([]);
}

/** ECharts' own default family list, read off a chart drawn without a theme — never typed here. */
function echartsDefaultFamilies(): string[] {
    const texts = drawnTexts(renderSvg(undefined, flagOption()));
    const lists = [...new Set(texts.map((drawn) => drawn.families.join(', ')))];
    expect(lists, 'without a theme the texts are drawn in more than one family list: no single default to compare with').toHaveLength(1);
    return texts[0].families;
}

// =============================================================================
// Part B — reading the sources: comments blanked, offsets kept
// =============================================================================

/** `frontend/`: the nearest directory above this file holding `vitest.config.ts` and `src/` — found, not counted, so the file can move. */
function frontendRoot(): string {
    const here = dirname(fileURLToPath(import.meta.url));
    for (let dir = here; ; dir = dirname(dir)) {
        if (existsSync(join(dir, 'vitest.config.ts')) && existsSync(join(dir, 'src'))) return dir;
        if (dirname(dir) === dir) throw new Error(`no frontend/ (vitest.config.ts beside src/) above ${here}`);
    }
}

const FRONTEND = frontendRoot();
const SRC = join(FRONTEND, 'src');

/** Written by `./dev.py api sync` and `frontend/scripts/generate-tools-client.mjs`; gitignored, never hand-written. */
const GENERATED = new Set(['src/lib/api/generated.ts', 'src/lib/api/generated-tools.ts', 'src/lib/api/tool-contract-map.generated.ts']);

/** The Designer Lab's folder: its probe chart is never painted (see the header). A segment, so the folder may move. */
const DESIGNER_LAB = 'designer-lab';

/** Whether a path (relative to `frontend/`) is a production source this scan reads. */
function isProductionSource(path: string): boolean {
    if (!/\.(ts|svelte)$/.test(path) || /\.(test|spec)\.ts$/.test(path) || path.endsWith('.d.ts')) return false;
    if (path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules' || segment === DESIGNER_LAB)) return false;
    return !GENERATED.has(path);
}

function sourceFiles(dir: string = SRC, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) sourceFiles(full, acc);
        else if (entry.isFile()) {
            const path = relative(FRONTEND, full).split(sep).join('/');
            if (isProductionSource(path)) acc.push(path);
        }
    }
    return acc.sort();
}

/** The role of a character of a script: code, comment, or literal (a string, a template's text, a regex). */
const CODE = 0;
const COMMENT = 1;
const LITERAL = 2;

/** Words after which a `/` opens a regular expression instead of dividing. */
const REGEX_AFTER_WORD = new Set(['return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void', 'throw', 'case', 'do', 'else', 'yield', 'await']);
/** Punctuation after which a `/` opens a regular expression instead of dividing. */
const REGEX_AFTER_PUNCTUATION = new Set(['(', ',', '=', ':', '[', '!', '&', '|', '?', '{', '}', ';', '+', '-', '*', '%', '<', '>', '~', '^']);

const isSpace = (code: number): boolean => code <= 32 || code === 0xa0 || code === 0xfeff || code === 0x2028 || code === 0x2029;
const isWord = (code: number): boolean => (code >= 48 && code <= 57) || (code >= 65 && code <= 90) || (code >= 97 && code <= 122) || code === 95 || code === 36 || code > 127;

/** Every character but newlines turned into a space: lengths, offsets and line numbers survive. */
const blank = (text: string): string => text.replace(/[^\n]/g, ' ');

/**
 * The role of every character of a JS/TS script. A small lexer, not a parser: enough to tell a `//` inside
 * `'https://…'`, a template or `/\/\//` from a comment. Whether a `/` opens a regex or divides is guessed from the token
 * before it, the usual heuristic; strings and regexes never span a line, so a wrong guess costs at most one line.
 */
function classify(src: string): Uint8Array {
    const n = src.length;
    const kinds = new Uint8Array(n).fill(CODE);
    const mark = (from: number, to: number, kind: number): void => {
        kinds.fill(kind, from, Math.min(to, n));
    };

    const quoted = (start: number): number => {
        const quote = src[start];
        let i = start + 1;
        while (i < n && src[i] !== quote && src[i] !== '\n') i += src[i] === '\\' ? 2 : 1;
        const end = i < n && src[i] === quote ? i + 1 : Math.min(i, n);
        mark(start, end, LITERAL);
        return end;
    };

    /** A regex literal from `start`, or `start` itself when none closes on its line — then the `/` divides. */
    const regex = (start: number): number => {
        let inClass = false;
        let i = start + 1;
        while (i < n) {
            const c = src[i];
            if (c === '\n' || c === '\r') return start;
            if (c === '\\') {
                if (src[i + 1] === '\n') return start;
                i += 2;
                continue;
            }
            if (c === '/' && !inClass) break;
            if (c === '[') inClass = true;
            else if (c === ']') inClass = false;
            i++;
        }
        if (i >= n) return start;
        i++;
        while (i < n && isWord(src.charCodeAt(i))) i++;
        mark(start, i, LITERAL);
        return i;
    };

    const template = (start: number): number => {
        let segment = start;
        let i = start + 1;
        while (i < n) {
            const c = src[i];
            if (c === '\\') {
                i += 2;
            } else if (c === '`') {
                mark(segment, i + 1, LITERAL);
                return i + 1;
            } else if (c === '$' && src[i + 1] === '{') {
                mark(segment, i + 2, LITERAL);
                const close = code(i + 2, true);
                segment = close;
                i = close + 1;
            } else {
                i++;
            }
        }
        mark(segment, n, LITERAL);
        return n;
    };

    /** Code from `start`; when `nested`, it stops at the `}` closing a `${` and returns that index. */
    function code(start: number, nested: boolean): number {
        let depth = 0;
        let regexAllowed = true;
        let i = start;
        while (i < n) {
            const c = src[i];
            const charCode = src.charCodeAt(i);
            if (c === '/' && src[i + 1] === '/') {
                const eol = src.indexOf('\n', i);
                const end = eol === -1 ? n : eol;
                mark(i, end, COMMENT);
                i = end;
            } else if (c === '/' && src[i + 1] === '*') {
                const close = src.indexOf('*/', i + 2);
                const end = close === -1 ? n : close + 2;
                mark(i, end, COMMENT);
                i = end;
            } else if (c === '/') {
                const end = regexAllowed ? regex(i) : i;
                if (end > i) {
                    i = end;
                    regexAllowed = false;
                } else {
                    i++;
                    regexAllowed = true;
                }
            } else if (c === "'" || c === '"') {
                i = quoted(i);
                regexAllowed = false;
            } else if (c === '`') {
                i = template(i);
                regexAllowed = false;
            } else if (isSpace(charCode)) {
                i++;
            } else if (isWord(charCode)) {
                let j = i + 1;
                while (j < n && isWord(src.charCodeAt(j))) j++;
                regexAllowed = REGEX_AFTER_WORD.has(src.slice(i, j));
                i = j;
            } else {
                if (nested && c === '}') {
                    if (depth === 0) return i;
                    depth--;
                } else if (nested && c === '{') {
                    depth++;
                }
                regexAllowed = REGEX_AFTER_PUNCTUATION.has(c);
                i++;
            }
        }
        return n;
    }

    code(0, false);
    return kinds;
}

/** The `>` that ends the tag opened before `from`, outside quoted attribute values (`generics="A<B>"`); -1 when none. */
function tagEnd(markup: string, from: number): number {
    let quote: string | null = null;
    for (let k = from; k < markup.length; k++) {
        const c = markup[k];
        if (quote) {
            if (c === quote) quote = null;
        } else if (c === '"' || c === "'") {
            quote = c;
        } else if (c === '>') {
            return k;
        }
    }
    return -1;
}

/** Every character outside the `<script>` blocks of a Svelte component blanked, HTML comments first: offsets stay the file's. */
function scriptBlocksOf(markup: string): string {
    const bodies: Array<[number, number]> = [];
    const closing = /<\/script\s*>/gi;
    let i = markup.indexOf('<');
    while (i !== -1) {
        if (markup.startsWith('<!--', i)) {
            const close = markup.indexOf('-->', i + 4);
            if (close === -1) break;
            i = markup.indexOf('<', close + 3);
        } else if (markup.slice(i, i + 7).toLowerCase() === '<script' && /[\s>]/.test(markup.charAt(i + 7))) {
            const open = tagEnd(markup, i + 7);
            if (open === -1) break;
            closing.lastIndex = open + 1;
            const close = closing.exec(markup);
            bodies.push([open + 1, close ? close.index : markup.length]);
            if (!close) break;
            i = markup.indexOf('<', close.index + close[0].length);
        } else {
            i = markup.indexOf('<', i + 1);
        }
    }
    let out = '';
    let last = 0;
    for (const [start, end] of bodies) {
        out += blank(markup.slice(last, start)) + markup.slice(start, end);
        last = end;
    }
    return out + blank(markup.slice(last));
}

/** A source as the scans read it: its scripts with the comments blanked, and the role of each character. */
interface Code {
    text: string;
    kinds: Uint8Array;
}

function codeOf(file: string, source: string): Code {
    const script = file.endsWith('.svelte') ? scriptBlocksOf(source) : source;
    const kinds = classify(script);
    let text = '';
    let start = 0;
    while (start < script.length) {
        const comment = kinds[start] === COMMENT;
        let end = start + 1;
        while (end < script.length && (kinds[end] === COMMENT) === comment) end++;
        text += comment ? blank(script.slice(start, end)) : script.slice(start, end);
        start = end;
    }
    return {text, kinds};
}

/** The 1-based line of `offset` in `text`. */
function lineAt(text: string, offset: number): number {
    let line = 1;
    for (let newline = text.indexOf('\n'); newline !== -1 && newline < offset; newline = text.indexOf('\n', newline + 1)) line++;
    return line;
}

// =============================================================================
// Part B — the calls, and the ways to reach init the scan could not see
// =============================================================================

/** One `echarts.init(` call of a source. */
interface InitCall {
    file: string;
    line: number;
    /** Its arguments, whitespace collapsed; a trailing empty one (Prettier's trailing comma) dropped. */
    args: string[];
    /** The source line it starts on, as written. */
    snippet: string;
}

const INIT_CALL = /\becharts\s*\.\s*init\s*\(/g;
const THEME_ARGUMENT = 'CHART_INIT_THEME';

/** The arguments of the call whose `(` is at `open`, split on top-level commas; `null` when the call does not close. */
function callArguments(text: string, kinds: Uint8Array, open: number): string[] | null {
    const args: string[] = [];
    let depth = 0;
    let start = open + 1;
    for (let i = open + 1; i < text.length; i++) {
        if (kinds[i] !== CODE) continue;
        const c = text[i];
        if (c === '(' || c === '[' || c === '{') {
            depth++;
        } else if (c === ')' || c === ']' || c === '}') {
            if (depth > 0) {
                depth--;
                continue;
            }
            if (c !== ')') return null;
            args.push(text.slice(start, i));
            const cleaned = args.map(collapse);
            if (cleaned.length > 0 && cleaned[cleaned.length - 1] === '') cleaned.pop();
            return cleaned;
        } else if (c === ',' && depth === 0) {
            args.push(text.slice(start, i));
            start = i + 1;
        }
    }
    return null;
}

function initCallsIn(file: string, source: string): InitCall[] {
    const {text, kinds} = codeOf(file, source);
    const lines = source.split('\n');
    const calls: InitCall[] = [];
    for (const match of text.matchAll(INIT_CALL)) {
        if (kinds[match.index] !== CODE) continue;
        const line = lineAt(text, match.index);
        calls.push({file, line, args: callArguments(text, kinds, match.index + match[0].length - 1) ?? ['<the call does not close>'], snippet: lines[line - 1] ?? ''});
    }
    return calls;
}

const isOffender = (call: InitCall): boolean => call.args[1] !== THEME_ARGUMENT;
const describeCall = (call: InitCall): string => `${call.file}:${call.line}  echarts.init(${call.args.join(', ')}) — second argument: ${call.args[1] ?? '(none)'}`;

/** DV: the third argument of every call, `chartInitOptions(<its element>…)` from `$lib/components/charts/chartPixelRatio`. */
const PIXEL_RATIO_CALLEE = 'chartInitOptions';

/**
 * The files whose calls do not pass `chartInitOptions` yet, each with its reason: exempt from DV's rule. Empty since
 * DV-14 (19/10/2026), when `PriceChartFull.svelte` and `CandlestickChart.svelte`, the last two, migrated: the 18 calls
 * in 17 files all pass it. Kept for a chart that cannot migrate at once, listed here with its reason. The list only
 * shrinks: once a listed file passes it everywhere, the staleness check asks for its line to go — and for the exemption
 * to leave the developer page (`mkdocs_src/docs/developer/frontend/components/charts.md`).
 */
const PIXEL_RATIO_PENDING: Readonly<Record<string, string>> = {};

/**
 * `callee(a, b, …)` as its callee and its arguments, whitespace collapsed; `null` when `expression` is not exactly one
 * call — a spread around it, an operator or a member after it. Literals and comments are told apart as in a source.
 */
function asCall(expression: string): {callee: string; args: string[]} | null {
    const kinds = classify(expression);
    const open = expression.indexOf('(');
    if (open <= 0 || kinds[open] !== CODE) return null;
    let depth = 0;
    for (let i = open; i < expression.length; i++) {
        if (kinds[i] !== CODE) continue;
        const c = expression[i];
        if (c === '(' || c === '[' || c === '{') {
            depth++;
        } else if (c === ')' || c === ']' || c === '}') {
            depth--;
            if (depth > 0) continue;
            if (c !== ')' || expression.slice(i + 1).trim() !== '') return null;
            const args = callArguments(expression, kinds, open);
            return args && {callee: collapse(expression.slice(0, open)), args};
        }
    }
    return null;
}

/** Whether a call passes, as its third argument, exactly `chartInitOptions(<its own first argument>…)`. */
function passesPixelRatio(call: InitCall): boolean {
    const third = call.args[2] === undefined ? null : asCall(call.args[2]);
    return third !== null && third.callee === PIXEL_RATIO_CALLEE && third.args.length > 0 && third.args[0] === call.args[0];
}

const describePixelRatio = (call: InitCall): string => `${call.file}:${call.line}  echarts.init(${call.args.join(', ')}) — third argument: ${call.args[2] ?? '(none)'}`;

/**
 * The lines of `pending` that no longer hold, each saying why: a file that is not among the production sources the scan
 * reads (`files`) any more, one without a call, one whose every call passes `chartInitOptions`. A file half migrated
 * still holds its line. Pure, so the controls run it on synthetic calls.
 */
function stalePixelRatioExemptions(pending: Readonly<Record<string, string>>, calls: InitCall[], files: readonly string[]): string[] {
    return Object.keys(pending).flatMap((file) => {
        if (!files.includes(file)) return [`${file}: not a production source the scan reads any more (moved, renamed or deleted)`];
        const own = calls.filter((call) => call.file === file);
        if (own.length === 0) return [`${file}: no echarts.init call any more`];
        if (own.every(passesPixelRatio)) return [`${file}: every call passes chartInitOptions now`];
        return [];
    });
}

/** An import or export of ECharts in a form that could bring `init` in under another name. */
interface HiddenInit {
    file: string;
    line: number;
    form: string;
}

const STATIC_FROM_ECHARTS = /\b(import|export)\s+((?:(?!\b(?:import|export)\b)[^;])*?)\s*\bfrom\s*(['"])echarts\3/g;
const DYNAMIC_ECHARTS = /(?<!\btypeof\s*)\b(?:import|require)\s*\(\s*(['"])echarts\1\s*\)/g;

/**
 * The ways a source reaches ECharts' `init` that `echarts.init(` does not match: a namespace under another name, a
 * named `init`, a default import, a re-export, a dynamic import or a `require`. A type-only import, `* as echarts`, and
 * named imports without `init` are fine.
 */
function hiddenInitsIn(file: string, source: string): HiddenInit[] {
    const {text, kinds} = codeOf(file, source);
    const found: HiddenInit[] = [];
    for (const match of text.matchAll(STATIC_FROM_ECHARTS)) {
        if (kinds[match.index] !== CODE) continue;
        const [, keyword, rawClause] = match;
        const clause = collapse(rawClause);
        if (/^type\b/.test(clause)) continue;
        if (keyword === 'import' && clause === '* as echarts') continue;
        if (keyword === 'import' && /^\{[^}]*\}$/.test(clause) && !/(?:^|[{,\s])init\b/.test(clause)) continue;
        found.push({file, line: lineAt(text, match.index), form: `${keyword} ${clause} from 'echarts'`});
    }
    for (const match of text.matchAll(DYNAMIC_ECHARTS)) {
        if (kinds[match.index] !== CODE) continue;
        found.push({file, line: lineAt(text, match.index), form: collapse(match[0])});
    }
    return found;
}

interface ChartScan {
    files: string[];
    calls: InitCall[];
    hidden: HiddenInit[];
}

let chartScan: ChartScan | undefined;

/** The production tree, scanned once per run. A source that never names `echarts` can neither call nor import it, and is not lexed. */
function scanCharts(): ChartScan {
    if (!chartScan) {
        const files = sourceFiles();
        const calls: InitCall[] = [];
        const hidden: HiddenInit[] = [];
        for (const file of files) {
            const source = readFileSync(join(FRONTEND, file), 'utf8');
            if (!source.includes('echarts')) continue;
            calls.push(...initCallsIn(file, source));
            hidden.push(...hiddenInitsIn(file, source));
        }
        chartScan = {files, calls, hidden};
    }
    return chartScan;
}

// =============================================================================
// The synthetic sources of the scanner controls
// =============================================================================

/** A component: calls in an HTML comment, a doc comment, a line comment, markup and a style; four real ones, one spanning lines. */
const SYNTHETIC_CHART = [
    '<!--',
    '  A doc comment: echarts.init(el) creates the chart in a <script> block.',
    '-->',
    '<script lang="ts">',
    "    import * as echarts from 'echarts';",
    "    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';",
    '    /** Not a call: echarts.init(doc) in a doc comment. */',
    '    // Not a call either: echarts.init(line)',
    "    const url = 'https://example.org'; const a = echarts.init(el, CHART_INIT_THEME, {renderer: 'canvas'});",
    '    const b = echarts.init(',
    '        container,',
    '        undefined,',
    "        {renderer: 'canvas', locale: `it-${'IT'}`},",
    '    );',
    '    const c = echarts.init(host, /* the theme */ CHART_INIT_THEME);',
    '    const d = echarts.init(node);',
    '</script>',
    '',
    "<p>Don't echarts.init(markup): it's text.</p>",
    '<style>',
    '    /* echarts.init(css) */',
    '</style>',
].join('\n');

/** A helper module: a doc comment naming the call, then calls behind a regex, a string, a template and a division that hold `//`, and one inside a string. */
const SYNTHETIC_HELPER = [
    '/**',
    ' * Attach to the element passed to `echarts.init()`.',
    ' */',
    'const re = /https?:\\/\\//; const one = echarts.init(dom1, CHART_INIT_THEME);',
    "const url = 'https://example.org'; const two = echarts.init(dom2);",
    'const t = `https://${host}/x`; const three = echarts.init(dom3, theme.CHART_INIT_THEME);',
    'const half = width / 2; const four = echarts.init(dom4, CHART_INIT_THEME); // width / 2',
    "const label = 'echarts.init(not, a, call)';",
].join('\n');

/** Every way of importing ECharts: the four the scan can rely on, and the four that would hide an init from it. */
const SYNTHETIC_IMPORTS = [
    "import * as echarts from 'echarts';",
    "import type {ECharts, EChartsOption} from 'echarts';",
    "import type * as types from 'echarts';",
    "import {graphic} from 'echarts';",
    "import * as ec from 'echarts';",
    'import {',
    '    init as makeChart,',
    "} from 'echarts';",
    "type Module = typeof import('echarts');",
    "const lazy = await import('echarts');",
    "// import {init} from 'echarts';",
    "export {init} from 'echarts';",
].join('\n');

const callLines = (calls: InitCall[]): string[] => calls.map((call) => `${call.line}: ${call.args.join(' | ')}`);

/**
 * DV's rule on a component: three calls that pass `chartInitOptions` on their own element (one with a locale, one over
 * lines with a comment inside and Prettier's trailing commas), then one call per shape that does not.
 */
const SYNTHETIC_PIXEL_RATIO = [
    '<script lang="ts">',
    "    import * as echarts from 'echarts';",
    "    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';",
    "    import {chartInitOptions} from '$lib/components/charts/chartPixelRatio';",
    '    const a = echarts.init(el, CHART_INIT_THEME, chartInitOptions(el));',
    "    const b = echarts.init(el, CHART_INIT_THEME, chartInitOptions(el, {locale: 'it,IT'}));",
    '    const c = echarts.init(',
    '        container,',
    '        CHART_INIT_THEME,',
    '        chartInitOptions(',
    '            /* its element */ container,',
    '        ),',
    '    );',
    "    const d = echarts.init(el, CHART_INIT_THEME, {renderer: 'canvas'});",
    '    const e = echarts.init(el, CHART_INIT_THEME);',
    '    const f = echarts.init(host, CHART_INIT_THEME, chartInitOptions(el));',
    '    const g = echarts.init(el, CHART_INIT_THEME, {...chartInitOptions(el), width: 2});',
    '    const h = echarts.init(el, CHART_INIT_THEME, chartInitOptions(el) ?? {});',
    '    const i = echarts.init(el, CHART_INIT_THEME, chartInitOptions());',
    '    const j = echarts.init(el, CHART_INIT_THEME, myChartInitOptions(el));',
    '    const k = echarts.init(el, CHART_INIT_THEME, chartInitOptions(host, el));',
    '</script>',
].join('\n');

// =============================================================================
// K-13 — Part A: the mechanism
// =============================================================================

describe('K-13 — Part A: a theme object gives every ECharts text the LF Flags face (real ECharts, server-side SVG)', () => {
    it('control — without a theme ECharts draws every text in its own default family, not LF Flags: what CHART_INIT_THEME is measured against', () => {
        const texts = drawnTexts(renderSvg(undefined, flagOption()));

        expectFlagsDrawn(texts);
        expect(texts.filter((drawn) => drawn.families[0] === FLAG_FACE).map(describeText), 'without a theme a text is already drawn in LF Flags: nothing could tell the theme apart').toEqual([]);
        expect(echartsDefaultFamilies().length, "ECharts' default family list is empty: the reading of the SVG finds no family").toBeGreaterThan(0);
    });

    it('control — an inline theme {textStyle: {fontFamily}} draws every text with LF Flags first: legend, axis labels, pie labels', () => {
        const texts = drawnTexts(renderSvg(INLINE_THEME, flagOption()));

        expectFlagsDrawn(texts);
        expect(notFlagFirst(texts)).toEqual([]);
    });

    it('control — the theme survives setOption(option, true): LF Flags first after a full reset', () => {
        const texts = drawnTexts(renderSvg(INLINE_THEME, flagOption(), true));

        expectFlagsDrawn(texts);
        expect(notFlagFirst(texts)).toEqual([]);
    });

    it('control — a component text style that sets a colour and no family keeps LF Flags first: legend, axis labels, pie labels', () => {
        const texts = drawnTexts(renderSvg(INLINE_THEME, flagOption({legend: {textStyle: {color: '#123456'}}, axisLabel: {color: '#654321'}, pieLabel: {color: '#abcdef'}})));

        expectFlagsDrawn(texts);
        expect(notFlagFirst(texts)).toEqual([]);
    });

    it('control — the reading sees a family that is not LF Flags: a fontFamily set on the x-axis labels wins over the theme, on exactly those texts', () => {
        const texts = drawnTexts(renderSvg(INLINE_THEME, flagOption({axisLabel: {fontFamily: 'serif'}})));

        expectFlagsDrawn(texts);
        expect(
            texts
                .filter((drawn) => drawn.families[0] !== FLAG_FACE)
                .map((drawn) => `${drawn.text} → ${drawn.families[0]}`)
                .sort(),
        ).toEqual(AXIS_TEXTS.map((text) => `${text} → serif`).sort());
    });

    it('a chart created with CHART_INIT_THEME draws every text with LF Flags first', () => {
        const texts = drawnTexts(renderSvg(theme.CHART_INIT_THEME as object | undefined, flagOption()));

        expectFlagsDrawn(texts);
        expect(notFlagFirst(texts), "texts drawn without LF Flags first: chartFont exports no CHART_INIT_THEME (undefined: ECharts' default family), or its textStyle sets no such fontFamily").toEqual([]);
    });

    it('CHART_FONT_FAMILY is a family list whose first family is LF Flags', () => {
        expect(typeof theme.CHART_FONT_FAMILY, 'chartFont exports no CHART_FONT_FAMILY string').toBe('string');

        expect(familyList(String(theme.CHART_FONT_FAMILY))[0]).toBe(FLAG_FACE);
    });

    it("after LF Flags, CHART_FONT_FAMILY is ECharts' own default family: no other glyph changes", () => {
        expect(typeof theme.CHART_FONT_FAMILY, 'chartFont exports no CHART_FONT_FAMILY string').toBe('string');

        expect(familyList(String(theme.CHART_FONT_FAMILY)).slice(1)).toEqual(echartsDefaultFamilies());
    });

    it('CHART_INIT_THEME is {textStyle: {fontFamily: CHART_FONT_FAMILY}}', () => {
        const initTheme = theme.CHART_INIT_THEME as {textStyle?: {fontFamily?: unknown}} | null | undefined;
        expect(typeof initTheme === 'object' && initTheme !== null, 'chartFont exports no CHART_INIT_THEME object').toBe(true);
        expect(typeof theme.CHART_FONT_FAMILY, 'chartFont exports no CHART_FONT_FAMILY string').toBe('string');

        expect(initTheme?.textStyle?.fontFamily).toBe(theme.CHART_FONT_FAMILY);
    });
});

// =============================================================================
// K-13 — Part B: every chart passes the theme
// =============================================================================

describe('K-13 and DV — Part B: every chart is created with echarts.init(<el>, CHART_INIT_THEME, chartInitOptions(<el>)) (static scan)', {timeout: 60_000}, () => {
    it('control — the scanner on a component: comments, markup and styles hold no call, a call may span lines, a comment inside one is blank', () => {
        const calls = initCallsIn('src/synthetic/Chart.svelte', SYNTHETIC_CHART);

        expect(callLines(calls)).toEqual(["9: el | CHART_INIT_THEME | {renderer: 'canvas'}", "10: container | undefined | {renderer: 'canvas', locale: `it-${'IT'}`}", '15: host | CHART_INIT_THEME', '16: node']);
        expect(calls.filter(isOffender).map((call) => call.line)).toEqual([10, 16]);
        expect(hiddenInitsIn('src/synthetic/Chart.svelte', SYNTHETIC_CHART)).toEqual([]);
    });

    it('control — the scanner on TypeScript: a doc comment holds no call, a // in a regex, a string or a template is no comment, a string holds no call', () => {
        const calls = initCallsIn('src/synthetic/chartHelper.ts', SYNTHETIC_HELPER);

        expect(callLines(calls)).toEqual(['4: dom1 | CHART_INIT_THEME', '5: dom2', '6: dom3 | theme.CHART_INIT_THEME', '7: dom4 | CHART_INIT_THEME']);
        expect(calls.filter(isOffender).map((call) => call.line)).toEqual([5, 6]);
    });

    it('control — the hidden-init forms: another namespace, a named init (over lines), a dynamic import and a re-export are found; types, * as echarts and graphic are not', () => {
        const lines = hiddenInitsIn('src/synthetic/imports.ts', SYNTHETIC_IMPORTS)
            .map((found) => found.line)
            .sort((left, right) => left - right);

        expect(lines).toEqual([5, 6, 10, 12]);
    });

    it('sanity — the scan sees the charts: at least 18 calls in at least 17 files, LotGanttChart.svelte with two, no doc comment counted', () => {
        const {files, calls} = scanCharts();
        const count = (name: string): number => calls.filter((call) => basename(call.file) === name).length;

        expect(files.length, 'the scan read too few production sources: wrong directory, or a filter too strict').toBeGreaterThanOrEqual(500);
        expect(calls.length, `the scan found ${calls.length} echarts.init calls, fewer than the 18 of today: a chart was removed (lower this floor) or the scanner lost some: ${calls.map(describeCall).join(' | ')}`).toBeGreaterThanOrEqual(18);
        expect(new Set(calls.map((call) => call.file)).size, 'the calls sit in fewer than the 17 files of today').toBeGreaterThanOrEqual(17);
        expect({
            'LineChart.svelte has a call': count('LineChart.svelte') > 0,
            'CorrelationHeatmap.svelte has a call': count('CorrelationHeatmap.svelte') > 0,
            'GrowthChart.svelte (its doc comment names echarts.init() too)': count('GrowthChart.svelte'),
            'LotGanttChart.svelte': count('LotGanttChart.svelte'),
            'echartsTooltipHelpers.ts (a doc comment only)': count('echartsTooltipHelpers.ts'),
            'echartsDataZoomTouchPan.ts (a doc comment only)': count('echartsDataZoomTouchPan.ts'),
            'chartPixelRatio.ts (a doc comment only)': count('chartPixelRatio.ts'),
        }).toEqual({
            'LineChart.svelte has a call': true,
            'CorrelationHeatmap.svelte has a call': true,
            'GrowthChart.svelte (its doc comment names echarts.init() too)': 1,
            'LotGanttChart.svelte': 2,
            'echartsTooltipHelpers.ts (a doc comment only)': 0,
            'echartsDataZoomTouchPan.ts (a doc comment only)': 0,
            'chartPixelRatio.ts (a doc comment only)': 0,
        });
    });

    it('sanity — every call is read whole, and none sits on a comment line', () => {
        const {calls} = scanCharts();

        expect(calls.filter((call) => call.args.includes('<the call does not close>')).map(describeCall), 'a call whose arguments the scanner could not close').toEqual([]);
        expect(
            calls.filter((call) => /^\s*(?:\*|\/\/|\/\*|<!--)/.test(call.snippet)).map((call) => `${describeCall(call)}  «${call.snippet.trim()}»`),
            'a call reported on a comment line: the blanking let a comment through',
        ).toEqual([]);
    });

    it("guard — no production module reaches ECharts' init under another name: the scan reads `echarts.init(` only", () => {
        expect(
            scanCharts().hidden.map((found) => `${found.file}:${found.line}  ${found.form}`),
            "a form that could create a chart the scan cannot see: import ECharts as `import * as echarts from 'echarts'`, or extend INIT_CALL",
        ).toEqual([]);
    });

    it('every echarts.init call passes exactly CHART_INIT_THEME as its second argument', () => {
        const {calls} = scanCharts();
        const offenders = calls.filter(isOffender).map(describeCall);

        expect(offenders, `${offenders.length} of ${calls.length} echarts.init calls do not pass CHART_INIT_THEME (from $lib/components/charts/chartFont) as their second argument (paths relative to frontend/)`).toEqual([]);
    });

    it('control — DV’s rule on a component: chartInitOptions on the call’s own element passes (extra arguments, lines, a comment inside); a literal, no third argument, another element, a spread, an operator after it, no element, another function do not', () => {
        const calls = initCallsIn('src/synthetic/Density.svelte', SYNTHETIC_PIXEL_RATIO);

        expect(callLines(calls).slice(0, 3), 'barrier: the three passing calls are read whole').toEqual(['5: el | CHART_INIT_THEME | chartInitOptions(el)', "6: el | CHART_INIT_THEME | chartInitOptions(el, {locale: 'it,IT'})", '7: container | CHART_INIT_THEME | chartInitOptions( container, )']);
        expect(calls.filter(passesPixelRatio).map((call) => call.line)).toEqual([5, 6, 7]);
        expect(calls.filter((call) => !passesPixelRatio(call)).map((call) => call.line)).toEqual([14, 15, 16, 17, 18, 19, 20, 21]);
    });

    it('control — the staleness check: a pending file that passes chartInitOptions now, has no call, or is gone is reported; one still pending, or half migrated, is not', () => {
        const component = (...lines: string[]): string => ['<script lang="ts">', ...lines.map((line) => `    ${line}`), '</script>'].join('\n');
        const sources: Record<string, string> = {
            'src/synthetic/Pending.svelte': component("const a = echarts.init(el, CHART_INIT_THEME, {renderer: 'canvas'});"),
            'src/synthetic/Half.svelte': component('const a = echarts.init(el, CHART_INIT_THEME, chartInitOptions(el));', 'const b = echarts.init(host, CHART_INIT_THEME);'),
            'src/synthetic/Migrated.svelte': component('const a = echarts.init(el, CHART_INIT_THEME, chartInitOptions(el));'),
            'src/synthetic/NoChart.ts': 'export const nothing = 0;',
        };
        const calls = Object.entries(sources).flatMap(([file, source]) => initCallsIn(file, source));
        const pending = Object.fromEntries([...Object.keys(sources), 'src/synthetic/Gone.svelte'].map((file) => [file, 'a reason']));

        expect(stalePixelRatioExemptions(pending, calls, Object.keys(sources))).toEqual([
            'src/synthetic/Migrated.svelte: every call passes chartInitOptions now',
            'src/synthetic/NoChart.ts: no echarts.init call any more',
            'src/synthetic/Gone.svelte: not a production source the scan reads any more (moved, renamed or deleted)',
        ]);
    });

    it('DV — every echarts.init call passes chartInitOptions(<its element>) as its third argument, but those of the files in PIXEL_RATIO_PENDING', () => {
        const {calls} = scanCharts();
        const offenders = calls.filter((call) => !Object.hasOwn(PIXEL_RATIO_PENDING, call.file) && !passesPixelRatio(call)).map(describePixelRatio);

        expect(
            offenders,
            `${offenders.length} of ${calls.length} echarts.init calls do not pass chartInitOptions(<their element>) (from $lib/components/charts/chartPixelRatio) as their third argument: their chart is born at the density zrender read when the page loaded, and never follows a change (paths relative to frontend/)`,
        ).toEqual([]);
    });

    it('DV — PIXEL_RATIO_PENDING cannot go stale: each listed file is a production source whose calls do not all pass chartInitOptions yet', () => {
        const {files, calls} = scanCharts();

        expect(stalePixelRatioExemptions(PIXEL_RATIO_PENDING, calls, files), 'remove these lines from PIXEL_RATIO_PENDING (chartFlagFont.test.ts), and their exemption from the developer page charts.md').toEqual([]);
    });
});
