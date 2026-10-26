/**
 * X5-F1 wiring: the FX pair detail page has the rolling return, read from its source.
 *
 * The asset detail page has two primary modes (prices, the calendar rolling return) and the window controls of the
 * latter. The FX pair page now draws the same two controls (`AssetChartModeToggle`, `AssetCalendarWindowControls`, under the
 * test ids of `idPrefix="fx"`), asks the rolling return of the pair and of every pair its `fx-pair` signals compare through
 * `buildFxDetailCalendarQuery(`, reads the answer with `fxDetailCalendarViews(`, draws the compared pairs with
 * `renderCalendarPairComparisons(`, publishes `data-primary-mode` on its chart card and saves the mode with the pair's chart
 * settings (`setPairSettings(` with `primaryView`).
 *
 * Mounting the page loads a dozen endpoints and stores, so, like the «Y-41 wiring» and «N64 wiring» blocks of
 * `chartPageSignals.test.ts` (whose helpers are copied below, the file being its own), the adoption is proven from the source
 * with its comments blanked: a floor, not a proof. What the page shows and sends is pinned by
 * `e2e/fx/fx-detail-rolling-return.spec.ts` (`X5-F1`).
 */
import {describe, expect, it} from 'vitest';
import {readFileSync} from 'node:fs';

const FX_PAGE = new URL('../../../routes/(app)/fx/[pair]/+page.svelte', import.meta.url);

// ---------------------------------------------------------------------------
// Helpers (own copies of the ones in chartPageSignals.test.ts)
// ---------------------------------------------------------------------------

/** A source with its comments blanked, the way the gate blanks them: a name in a comment is no code. `//` after `:` stays (`https://`). */
function withoutComments(source: string): string {
    const blank = (text: string, pattern: RegExp): string => text.replace(pattern, (found) => found.replace(/[^\n]/g, ' '));
    return blank(blank(blank(source, /<!--[\s\S]*?-->/g), /\/\*[\s\S]*?\*\//g), /(?<![:\\])\/\/[^\n]*/g);
}

/**
 * Whether `code` calls `name(` as itself: not a longer name, not a method of something (`other.name(`), but a spread of
 * its result is a call (`...name(`): a single `.` before the name is member access, three are a spread.
 */
const callsFunction = (code: string, name: string): boolean => new RegExp(`(?<![\\w$])(?<!(?<!\\.)\\.)${name}\\s*\\(`).test(code);

/** Every import statement of `code`: whether it is `import type`, its clause (default and/or braces) and its module. */
function importStatements(code: string): Array<{typeOnly: boolean; clause: string; source: string}> {
    return [...code.matchAll(/import\s+(type\s+)?([^;'"]*?)\s*\bfrom\s*['"]([^'"]+)['"]/g)].map(([, typeOnly, clause, source]) => ({typeOnly: Boolean(typeOnly), clause, source}));
}

/** Whether `code` imports `name` as a value from the module `from`: a named specifier (`{name}`, `{name as other}`), not a `type` one. */
function importsNamedValue(code: string, name: string, from: string): boolean {
    return importStatements(code).some(({typeOnly, clause, source}) => {
        if (typeOnly || source !== from) return false;
        const braces = clause.match(/\{([^}]*)\}/)?.[1] ?? '';
        return braces.split(',').some((specifier) => !/^\s*type\s/.test(specifier) && specifier.trim().split(/\s+as\s+/)[0] === name);
    });
}

/** Whether `code` imports the default export of the module `from` under `name` (`import Name from '…'`, `import Name, {type X} from '…'`), not as a type. */
function importsDefault(code: string, name: string, from: string): boolean {
    return importStatements(code).some(({typeOnly, clause, source}) => !typeOnly && source === from && clause.split(/[,{]/)[0].trim() === name);
}

/** The opening tags `<name …>` of `markup`: their attribute text, with `{…}` expressions skipped whole (a `>` inside one does not end the tag). */
function openingTags(markup: string, name: string): string[] {
    const tags: string[] = [];
    const start = new RegExp(`<${name}(?![\\w$.-])`, 'g');
    for (let found = start.exec(markup); found; found = start.exec(markup)) {
        let depth = 0;
        let quote: string | null = null;
        let end = -1;
        for (let index = found.index + found[0].length; index < markup.length; index++) {
            const char = markup[index];
            if (quote) {
                if (char === quote) quote = null;
            } else if (depth > 0) {
                if (char === '{') depth++;
                else if (char === '}') depth--;
            } else if (char === '"' || char === "'") quote = char;
            else if (char === '{') depth++;
            else if (char === '>') {
                end = index;
                break;
            }
        }
        if (end >= 0) tags.push(markup.slice(found.index + found[0].length, end));
    }
    return tags;
}

/** Whether a tag's attribute text sets `idPrefix` to the literal `prefix`: `idPrefix="fx"`, `idPrefix='fx'` or `idPrefix={'fx'}`. */
const setsIdPrefix = (attributes: string, prefix: string): boolean => new RegExp(`(?<![\\w$-])idPrefix\\s*=\\s*(?:"${prefix}"|'${prefix}'|\\{\\s*['"]${prefix}['"]\\s*\\})`).test(attributes);

/** The text between the parentheses of each call `name(…)` in `code`, parentheses matched. */
function callArguments(code: string, name: string): string[] {
    const calls: string[] = [];
    const start = new RegExp(`(?<![\\w$])(?<!(?<!\\.)\\.)${name}\\s*\\(`, 'g');
    for (let found = start.exec(code); found; found = start.exec(code)) {
        let depth = 1;
        for (let index = found.index + found[0].length; index < code.length; index++) {
            if (code[index] === '(') depth++;
            else if (code[index] === ')' && --depth === 0) {
                calls.push(code.slice(found.index + found[0].length, index));
                break;
            }
        }
    }
    return calls;
}

// ---------------------------------------------------------------------------
// The form: what keeps the FX page from the rolling return
// ---------------------------------------------------------------------------

const TOGGLE = {name: 'AssetChartModeToggle', from: '$lib/components/assets/detail/AssetChartModeToggle.svelte'} as const;
const WINDOW_CONTROLS = {name: 'AssetCalendarWindowControls', from: '$lib/components/assets/detail/AssetCalendarWindowControls.svelte'} as const;

/** What keeps the FX page from drawing the two controls of the rolling return under the ids of the FX page. */
function controlsProblems(source: string): string[] {
    const code = withoutComments(source);
    const problems: string[] = [];
    for (const {name, from} of [TOGGLE, WINDOW_CONTROLS]) {
        if (!importsDefault(code, name, from)) problems.push(`${name} is not imported as a value from ${from}`);
        const tags = openingTags(code, name);
        if (tags.length === 0) problems.push(`<${name} is never rendered`);
        else if (!tags.some((attributes) => setsIdPrefix(attributes, 'fx'))) problems.push(`<${name} is rendered but never with idPrefix="fx": its test ids stay the asset page's`);
    }
    return problems;
}

/** What keeps the FX page from asking the rolling return and drawing the compared pairs from its answer. */
function requestProblems(source: string): string[] {
    const code = withoutComments(source);
    const problems: string[] = [];
    for (const name of ['buildFxDetailCalendarQuery', 'fxDetailCalendarViews']) {
        if (!importsNamedValue(code, name, '$lib/charts/fxDetailCalendar')) problems.push(`${name} is not imported as a value from $lib/charts/fxDetailCalendar`);
        if (!callsFunction(code, name)) problems.push(`${name}( is never called`);
    }
    if (!importsNamedValue(code, 'renderCalendarPairComparisons', '$lib/charts/chartSignalRendering')) problems.push('renderCalendarPairComparisons is not imported as a value from $lib/charts/chartSignalRendering');
    if (!callsFunction(code, 'renderCalendarPairComparisons')) problems.push('renderCalendarPairComparisons( is never called');
    return problems;
}

/** What keeps the FX page from publishing its mode and saving it with the pair's chart settings. */
function modeProblems(source: string): string[] {
    const code = withoutComments(source);
    const problems: string[] = [];
    if (!/(?<![\w$-])data-primary-mode\s*=\s*\{/.test(code)) problems.push('data-primary-mode={…} is never written on the chart card');
    const saves = callArguments(code, 'setPairSettings');
    if (saves.length === 0) problems.push('setPairSettings( is never called');
    else if (!saves.some((args) => /(?<![\w$])primaryView(?![\w$])/.test(args))) problems.push('no setPairSettings( call carries primaryView: the mode is not saved with the pair’s chart settings');
    return problems;
}

const listed = (what: string, problems: readonly string[]): string => ['', `The FX detail page ${what} (X5-F1). ${problems.length} finding(s):`, '', ...problems, ''].join('\n  ');

describe('X5-F1 wiring, read from the FX detail page’s source', () => {
    const source = readFileSync(FX_PAGE, 'utf8');

    it('renders the mode toggle and the window controls of the asset page, under the ids of idPrefix="fx"', () => {
        const problems = controlsProblems(source);

        expect(problems, listed('does not draw the rolling-return controls under its own ids: import AssetChartModeToggle and AssetCalendarWindowControls and render them with idPrefix="fx"', problems)).toEqual([]);
    });

    it('asks the rolling return of the pair and of its compared pairs, reads the answer, and draws the compared pairs', () => {
        const problems = requestProblems(source);

        expect(problems, listed('does not ask or draw the rolling return: build the request with buildFxDetailCalendarQuery(, read it with fxDetailCalendarViews( and draw the compared pairs with renderCalendarPairComparisons(', problems)).toEqual([]);
    });

    it('publishes its mode on the chart card and saves it with the pair’s chart settings', () => {
        const problems = modeProblems(source);

        expect(problems, listed('does not publish or save its primary mode: write data-primary-mode on the chart card and call setPairSettings( with primaryView', problems)).toEqual([]);
    });

    describe('the form reads what it claims (controls)', () => {
        const WIRED = [
            "import AssetChartModeToggle, {type AssetChartPrimaryMode} from '$lib/components/assets/detail/AssetChartModeToggle.svelte';",
            "import AssetCalendarWindowControls from '$lib/components/assets/detail/AssetCalendarWindowControls.svelte';",
            "import {buildFxDetailCalendarQuery, fxDetailCalendarViews} from '$lib/charts/fxDetailCalendar';",
            "import {renderCalendarPairComparisons, renderLocalSignals} from '$lib/charts/chartSignalRendering';",
            "import {setPairSettings} from '$lib/stores/chartSettingsStore.svelte';",
            'const entries = buildFxDetailCalendarQuery(input);',
            'const views = fxDetailCalendarViews(answer, entries);',
            'const rendered = renderCalendarPairComparisons(signals, views.targets);',
            "setPairSettings(slug, {...settings, primaryView: 'calendar-return', signals: [...signals]});",
            '<div data-testid="fx-detail-chart" data-primary-mode={primaryMode}>',
            '    <AssetChartModeToggle {primaryMode} onselect={setPrimaryMode} idPrefix="fx" />',
            "    <AssetCalendarWindowControls selection={sel} onpreset={(p) => pick(p > 1 ? 'a' : 'b')} idPrefix={'fx'} />",
            '</div>',
        ].join('\n');

        it('pass a page that does all of it', () => {
            expect(controlsProblems(WIRED)).toEqual([]);
            expect(requestProblems(WIRED)).toEqual([]);
            expect(modeProblems(WIRED)).toEqual([]);
        });

        it('fail an import of the type only, a component never rendered, and one without the fx prefix or with another', () => {
            expect(controlsProblems(WIRED.replace('import AssetChartModeToggle,', 'import type AssetChartModeToggle,'))).toEqual([`${TOGGLE.name} is not imported as a value from ${TOGGLE.from}`]);
            expect(controlsProblems(WIRED.replace('    <AssetChartModeToggle {primaryMode} onselect={setPrimaryMode} idPrefix="fx" />\n', ''))).toEqual([`<${TOGGLE.name} is never rendered`]);
            expect(controlsProblems(WIRED.replace('idPrefix="fx"', ''))).toEqual([`<${TOGGLE.name} is rendered but never with idPrefix="fx": its test ids stay the asset page's`]);
            expect(controlsProblems(WIRED.replace("idPrefix={'fx'}", 'idPrefix="asset"'))).toEqual([`<${WINDOW_CONTROLS.name} is rendered but never with idPrefix="fx": its test ids stay the asset page's`]);
        });

        it('read a component’s tag whole when an attribute holds a ">" in an expression', () => {
            const tags = openingTags('<AssetCalendarWindowControls onpreset={(p) => p > 1} idPrefix="fx" />', 'AssetCalendarWindowControls');

            expect(tags).toHaveLength(1);
            expect(setsIdPrefix(tags[0], 'fx')).toBe(true);
        });

        it('fail a call only in a comment, an import of the type only, and a page that asks nothing', () => {
            expect(requestProblems(WIRED.replace('const entries = buildFxDetailCalendarQuery(input);', '// const entries = buildFxDetailCalendarQuery(input);'))).toEqual(['buildFxDetailCalendarQuery( is never called']);
            expect(requestProblems(WIRED.replace('import {buildFxDetailCalendarQuery, fxDetailCalendarViews}', 'import {type buildFxDetailCalendarQuery, fxDetailCalendarViews}'))).toEqual(['buildFxDetailCalendarQuery is not imported as a value from $lib/charts/fxDetailCalendar']);
            expect(requestProblems(WIRED.replace('renderCalendarPairComparisons(signals, views.targets)', 'other.renderCalendarPairComparisons(signals, views.targets)'))).toEqual(['renderCalendarPairComparisons( is never called']);
            expect(requestProblems('')).toHaveLength(6);
        });

        it('fail a mode never published, and a save without primaryView', () => {
            expect(modeProblems(WIRED.replace('data-primary-mode={primaryMode}', 'data-view-mode={viewMode}'))).toEqual(['data-primary-mode={…} is never written on the chart card']);
            expect(modeProblems(WIRED.replace(" primaryView: 'calendar-return',", ''))).toEqual(['no setPairSettings( call carries primaryView: the mode is not saved with the pair’s chart settings']);
            expect(modeProblems(WIRED.replace("setPairSettings(slug, {...settings, primaryView: 'calendar-return', signals: [...signals]});", "// setPairSettings(slug, {primaryView: 'x'});"))).toEqual(['setPairSettings( is never called']);
            expect(modeProblems(WIRED.replace('primaryView: ', 'primaryViewX: '))).toHaveLength(1);
        });
    });
});
