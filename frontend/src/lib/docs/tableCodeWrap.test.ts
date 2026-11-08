// @vitest-environment jsdom
/**
 * Tables in the documentation: long code wraps, and the columns share the width within limits (E9D).
 *
 * Two pieces. The script `mkdocs_src/docs/javascripts/table-code-wrap.js` marks the code spans of a table cell that are
 * messages, not names (the site keeps the code of the first two columns on one line, which suits an identifier and made a
 * log message take the width of its longest line). `mkdocs_src/docs/static/extra.css` lets a marked span wrap and gives the
 * cells of a table with three or more columns a floor and a ceiling (`min-width`, `max-width`, a higher floor for the last
 * column) and the width of the page. The table stays a table: nothing is added to its structure.
 *
 * The script is a classic script of the docs site, not an app module: it is read as text and run in jsdom. jsdom does no
 * layout, so the CSS is pinned by what it says; how it looks was measured in a browser (lot hand-over note).
 */
import {beforeEach, describe, expect, it} from 'vitest';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const ROOT = resolve(__dirname, '../../../../mkdocs_src');
const SCRIPT = readFileSync(resolve(ROOT, 'docs/javascripts/table-code-wrap.js'), 'utf-8');
const CSS = readFileSync(resolve(ROOT, 'docs/static/extra.css'), 'utf-8');
const SITE = readFileSync(resolve(ROOT, 'mkdocs.yml'), 'utf-8');

function run() {
    new Function(SCRIPT)();
}

function cell(code: string): string {
    return `<td><code>${code}</code></td>`;
}

function mount(cells: string[], head = ['A', 'B', 'C']): HTMLTableElement {
    document.body.innerHTML = `<div class="md-typeset"><table><thead><tr>${head.map((h) => `<th>${h}</th>`).join('')}</tr></thead><tbody><tr>${cells.join('')}</tr></tbody></table></div>`;
    return document.querySelector('table') as HTMLTableElement;
}

beforeEach(() => {
    document.body.innerHTML = '';
});

describe('which code spans of a table cell may wrap', () => {
    const MESSAGE = 'The instance key cannot be used: it cannot be reached (Permission denied)';

    it('a message over 60 characters is marked', () => {
        const table = mount([cell(MESSAGE), cell('x'), cell('y')]);

        run();

        expect(table.querySelector('code')!.classList.contains('lf-code-long')).toBe(true);
    });

    it('a short phrase with spaces over 28 characters is marked: a name or a path has no space', () => {
        const table = mount([cell('The password is not strong enough'), cell('x'), cell('y')]);

        run();

        expect(table.querySelector('code')!.classList.contains('lf-code-long')).toBe(true);
    });

    it.each([
        ['LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS', 'a long variable name'],
        ['/api/v1/backup/instance/options?with=a&long=query', 'a path of 50 characters'],
        ['docker compose up -d', 'a short command'],
        ['backup create --encrypt', 'a command of a few words'],
    ])('%s (%s) is not marked: an identifier is not broken', (code) => {
        const table = mount([cell(code), cell('x'), cell('y')]);

        run();

        expect(table.querySelector('code')!.classList.contains('lf-code-long')).toBe(false);
    });

    it('a name over 60 characters without a space is marked too: it must not push the table out of the page', () => {
        const table = mount([cell('x'.repeat(70)), cell('x'), cell('y')]);

        run();

        expect(table.querySelector('code')!.classList.contains('lf-code-long')).toBe(true);
    });

    it('code outside a table is left alone', () => {
        document.body.innerHTML = `<div class="md-typeset"><p><code>${MESSAGE}</code></p></div>`;

        run();

        expect(document.querySelector('code')!.classList.contains('lf-code-long')).toBe(false);
    });

    it('the table keeps its structure: no colgroup, no inline style, no class on the table', () => {
        const table = mount([cell(MESSAGE), cell('x'), cell('y')]);
        const before = table.outerHTML.replace(' class="lf-code-long"', '');

        run();

        expect(table.outerHTML.replace(' class="lf-code-long"', '')).toBe(before);
        expect(table.querySelector('colgroup')).toBeNull();
        expect(table.getAttribute('style')).toBeNull();
        expect(table.getAttribute('class')).toBeNull();
    });

    it('running twice marks once', () => {
        const table = mount([cell(MESSAGE), cell('x'), cell('y')]);

        run();
        run();

        expect(table.querySelector('code')!.className).toBe('lf-code-long');
    });
});

describe('what the site is given', () => {
    const THREE_COLUMNS = String.raw`\.md-typeset table:not\(\[class\]\):has\(> thead th:nth-child\(3\)\)`;

    it('mkdocs.yml loads the script, and the old balancer is gone', () => {
        expect(SITE).toMatch(/^ {2}- javascripts\/table-code-wrap\.js$/m);
        expect(SITE).not.toContain('table-balance');
    });

    it('a table of three or more columns gets the width of the page, and the wrapper stops sizing it to its widest line', () => {
        expect(CSS).toMatch(new RegExp(String.raw`${THREE_COLUMNS}\s*\{[^}]*display:\s*table[^}]*width:\s*100%`));
        expect(CSS).toMatch(/\.md-typeset__table:has\(> table:not\(\[class\]\) > thead th:nth-child\(3\)\)\s*\{[^}]*display:\s*block/);
    });

    it('its cells have a floor and a ceiling, the last column a higher floor', () => {
        const cells = CSS.match(new RegExp(`${THREE_COLUMNS} th,\\s*${THREE_COLUMNS} td\\s*\\{([^}]*)\\}`));
        expect(cells, 'a rule for th and td').not.toBeNull();
        expect(cells![1]).toMatch(/min-width:\s*(\d+(?:\.\d+)?)rem/);
        expect(cells![1]).toMatch(/max-width:\s*(\d+(?:\.\d+)?)rem/);
        const floor = Number(/min-width:\s*([\d.]+)rem/.exec(cells![1])![1]);
        const ceiling = Number(/max-width:\s*([\d.]+)rem/.exec(cells![1])![1]);
        expect(floor).toBeLessThan(ceiling);
        const last = CSS.match(new RegExp(`${THREE_COLUMNS} th:last-child,\\s*${THREE_COLUMNS} td:last-child\\s*\\{([^}]*)\\}`));
        expect(last, 'a rule for the last column').not.toBeNull();
        expect(Number(/min-width:\s*([\d.]+)rem/.exec(last![1])![1])).toBeGreaterThan(floor);
    });

    it('a marked code span wraps, and the rule comes after (and is stronger than) the nowrap rule of the first two columns', () => {
        const wrap = CSS.indexOf('code.lf-code-long.lf-code-long');
        expect(wrap).toBeGreaterThan(CSS.indexOf('td:nth-child(2) code'));
        expect(CSS.slice(wrap, CSS.indexOf('}', wrap))).toMatch(/white-space:\s*normal/);
        expect(CSS.slice(wrap, CSS.indexOf('}', wrap))).toMatch(/overflow-wrap:\s*break-word/);
        expect(CSS).toMatch(/td:nth-child\(1\) code,\s*\.md-typeset table:not\(\[class\]\) td:nth-child\(2\) code\s*\{[^}]*white-space:\s*nowrap/);
    });
});
