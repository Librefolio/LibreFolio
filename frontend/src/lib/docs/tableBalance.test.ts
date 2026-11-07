// @vitest-environment jsdom
/**
 * The documentation's table balancer (`mkdocs_src/docs/javascripts/table-balance.js`).
 *
 * A table with a long log line in one column and a short instruction in another used to be laid out in proportion to
 * the widest cell: the long column took nearly all the width, the instruction column a few words per line, and every
 * row grew very tall. One script, for every page and language, gives such a table fixed columns in proportion to the
 * square root of their text length, on a wide screen only, and leaves every other table alone.
 *
 * The script is a classic script of the docs site, not an app module: it is read as text and run in jsdom, with
 * `matchMedia` answering what the test says. jsdom does no layout, so what is pinned is the decision (which tables) and
 * the result written on the table (a colgroup, the class `lf-balanced`, a fixed layout); the look was checked in a browser.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const SCRIPT = readFileSync(resolve(__dirname, '../../../../mkdocs_src/docs/javascripts/table-balance.js'), 'utf-8');

const viewport = {wide: true};

/** `matchMedia` answers from `viewport`, so a test can change the screen after the script has registered its listener. */
function setViewport(wide: boolean) {
    viewport.wide = wide;
    const listeners: Array<() => void> = [];
    vi.stubGlobal(
        'matchMedia',
        vi.fn(() => ({
            get matches() {
                return viewport.wide;
            },
            addEventListener: (_: string, listener: () => void) => listeners.push(listener),
        })),
    );
    return listeners;
}

/** A table `<div class="md-typeset">` with the given header and rows. */
function mount(head: string[], rows: string[][], attributes = ''): HTMLTableElement {
    document.body.innerHTML = `<div class="md-typeset"><table ${attributes}><thead><tr>${head.map((h) => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    return document.querySelector('table') as HTMLTableElement;
}

function run() {
    new Function(SCRIPT)();
}

const LOG = 'The instance key cannot be used: it cannot be reached (Permission denied) or it cannot be read at all because of the owner'.repeat(2);
const ACTION = 'Fix the owner of both.';
const LEVEL = '⚠️ warning';

beforeEach(() => {
    document.body.innerHTML = '';
});
afterEach(() => {
    vi.unstubAllGlobals();
});

describe('which tables are balanced', () => {
    it('a table with a long log column next to short ones gets a colgroup, the class and a fixed layout', () => {
        setViewport(true);
        const table = mount(
            ['Level', 'The log says', 'Do'],
            [
                [LEVEL, LOG, ACTION],
                [LEVEL, LOG, ACTION],
            ],
        );

        run();

        expect(table.classList.contains('lf-balanced')).toBe(true);
        expect(table.style.tableLayout).toBe('fixed');
        expect(table.style.width).toBe('100%');
        const widths = [...table.querySelectorAll('colgroup col')].map((col) => parseFloat((col as HTMLElement).style.width));
        expect(widths).toHaveLength(3);
        expect(widths.reduce((a, b) => a + b, 0)).toBeCloseTo(100, 1);
        // The long column is the widest, and the instruction column is not squeezed: more than the short level column, and a real share.
        expect(widths[1]).toBeGreaterThan(widths[2]);
        expect(widths[2]).toBeGreaterThan(widths[0]);
        expect(widths[2]).toBeGreaterThan(15);
        expect(Math.min(...widths)).toBeGreaterThanOrEqual(8 - 0.01);
    });

    it('the long column no longer takes everything: well below its share of the text', () => {
        setViewport(true);
        const table = mount(['A', 'B', 'C'], [['x', LOG, ACTION]]);

        run();

        const widths = [...table.querySelectorAll('colgroup col')].map((col) => parseFloat((col as HTMLElement).style.width));
        const textShare = (100 * LOG.length) / (1 + LOG.length + ACTION.length);
        expect(widths[1]).toBeLessThan(textShare - 10);
    });

    it.each([
        ['two columns', ['A', 'B'], [['x', LOG]]],
        ['no long cell', ['A', 'B', 'C'], [['short', 'also short', 'short again']]],
        ['all columns long', ['A', 'B', 'C'], [[LOG, LOG, LOG]]],
    ] as const)('a table with %s is left to the theme', (_name, head, rows) => {
        setViewport(true);
        const table = mount(
            [...head],
            rows.map((row) => [...row]),
        );

        run();

        expect(table.querySelector('colgroup')).toBeNull();
        expect(table.classList.contains('lf-balanced')).toBe(false);
        expect(table.style.tableLayout).toBe('');
    });

    it('a row whose cells do not match the header (a spanning cell) leaves the table alone', () => {
        setViewport(true);
        const table = mount(['A', 'B', 'C'], [['x', LOG, ACTION]]);
        table.querySelector('tbody')!.insertAdjacentHTML('beforeend', `<tr><td colspan="3">${LOG}</td></tr>`);

        run();

        expect(table.querySelector('colgroup')).toBeNull();
    });

    it('a table with a class of its own (not a content table) is not touched', () => {
        setViewport(true);
        const table = mount(['A', 'B', 'C'], [['x', LOG, ACTION]], 'class="highlighttable"');

        run();

        expect(table.querySelector('colgroup')).toBeNull();
    });

    it('a narrow screen keeps the theme layout: the table scrolls sideways as before', () => {
        setViewport(false);
        const table = mount(['A', 'B', 'C'], [['x', LOG, ACTION]]);

        run();

        expect(table.querySelector('colgroup')).toBeNull();
        expect(table.style.tableLayout).toBe('');
    });

    it('going from wide to narrow undoes it, and back again does it again', () => {
        const listeners = setViewport(true);
        const table = mount(['A', 'B', 'C'], [['x', LOG, ACTION]]);
        run();
        expect(table.classList.contains('lf-balanced')).toBe(true);

        viewport.wide = false;
        listeners.forEach((listener) => listener());
        expect(table.querySelector('colgroup')).toBeNull();
        expect(table.classList.contains('lf-balanced')).toBe(false);
        expect(table.style.tableLayout).toBe('');

        viewport.wide = true;
        listeners.forEach((listener) => listener());
        expect(table.querySelectorAll('colgroup')).toHaveLength(1);
        expect(table.classList.contains('lf-balanced')).toBe(true);
    });

    it('running twice does not add a second colgroup', () => {
        setViewport(true);
        const table = mount(['A', 'B', 'C'], [['x', LOG, ACTION]]);

        run();
        run();

        expect(table.querySelectorAll('colgroup')).toHaveLength(1);
    });
});

describe('what the site is given', () => {
    const site = readFileSync(resolve(__dirname, '../../../../mkdocs_src/mkdocs.yml'), 'utf-8');
    const css = readFileSync(resolve(__dirname, '../../../../mkdocs_src/docs/static/extra.css'), 'utf-8');

    it('mkdocs.yml loads the script', () => {
        expect(site).toMatch(/^ {2}- javascripts\/table-balance\.js$/m);
    });

    it('the stylesheet lets the code of a balanced table wrap: in a fixed layout a cell that does not wrap spills over its neighbour', () => {
        expect(css).toMatch(/\.md-typeset table\.lf-balanced code\s*\{[^}]*white-space:\s*normal/);
        expect(css).toMatch(/\.md-typeset table\.lf-balanced td[^{]*\{[^}]*overflow-wrap:\s*anywhere/);
    });
});
