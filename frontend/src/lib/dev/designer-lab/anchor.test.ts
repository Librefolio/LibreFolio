// @vitest-environment jsdom
/**
 * Designer Lab — where a picked element is (`picker/anchor.ts`): its test-id chain, its CSS path and the selector of a
 * specialisation, said the way the code names things and never with the element's text — an export must carry no
 * data, and a debug build can run on real data.
 *
 * A templated id (`filter-currency-row-${code}`) is written as its prefix (`filter-currency-row-*`, `^=` in a
 * selector), so the record it names stays out. The index of the build says which ids are templated; for an id it does
 * not know (or without one, the picker's fallback) the id is cut before its first token that looks like a record — a
 * whole number or a token with a capital letter (`recordPrefix`). The route is SvelteKit's route id when the picker
 * has it, `[param]` segments kept. jsdom stands in for the page.
 */

import {beforeEach, describe, expect, it} from 'vitest';
import {codeTestid, componentSelector, countMatches, cssPath, nearestTestid, recordPrefix, retarget, routeOf, scopeClass, selectorNames, stableClasses, testidChain, testidPrefix, testidSelector} from './picker/anchor';
import type {TestidIndex} from './types';

/** As `virtual:lf-testid-index` serves it: prefixes longest first. */
const INDEX: TestidIndex = {
    statics: ['filter-currency-list', 'row-total', 'tx-page', 'tx-table'],
    prefixes: ['filter-currency-row-', 'tab-settings-', 'row-', 'tab-'],
};

/** Text a user could have on screen: none of it may reach an anchor. */
const SECRETS = ['Alice Rossi', 'IT60X0542811101000000123456', '1.234,56', 'Euro', 'USD', 'Loose text', 'Weekly salary'];

const PAGE = `
<main>
  <section data-testid="tx-page">
    <div data-testid="tx-table" class="wrapper">
      <div><div>
        <table>
          <thead><tr>
            <th class="svelte-1x2y3z sorted">Date</th>
            <th id="th2" class="svelte-1x2y3z text-gray-500 dark:text-gray-400">Amount — Alice Rossi</th>
          </tr></thead>
          <tbody>
            <tr data-testid="row-42"><td>IBAN IT60X0542811101000000123456</td><td><span id="cell">€ 1.234,56</span></td></tr>
            <tr data-testid="row-43"><td>Weekly salary</td><td><span>€ 99,00</span></td></tr>
          </tbody>
        </table>
      </div></div>
    </div>
    <ul data-testid="filter-currency-list">
      <li data-testid="filter-currency-row-EUR"><span id="eur">EUR — Euro</span></li>
      <li data-testid="filter-currency-row-USD"><span>USD</span></li>
    </ul>
  </section>
  <p id="loose">Loose text</p>
  <p>Second paragraph</p>
  <svg id="icon" class="lucide-icon lucide lucide-trash-2"><path id="icon-path" d="M0 0h1"></path></svg>
  <svg id="chart-svg"><path id="chart-path" d="M0 0h1"></path></svg>
</main>`;

const byId = (id: string): Element => {
    const el = document.getElementById(id);
    if (!el) throw new Error(`#${id} is not in the page`);
    return el;
};

const byTestid = (id: string): Element => {
    const el = document.querySelector(`[data-testid="${id}"]`);
    if (!el) throw new Error(`[data-testid="${id}"] is not in the page`);
    return el;
};

beforeEach(() => {
    document.body.innerHTML = PAGE;
});

describe('recordPrefix', () => {
    it('cuts an id before its first token that is a whole number', () => {
        expect(recordPrefix('row-42')).toBe('row-');
        expect(recordPrefix('asset-row-42-menu')).toBe('asset-row-');
        expect(recordPrefix('row-7-12')).toBe('row-');
        expect(recordPrefix('tx_row_7')).toBe('tx_row_');
    });

    it('cuts an id before its first token with a capital letter: a code, a ticker, a name', () => {
        expect(recordPrefix('kpi-gain-EUR')).toBe('kpi-gain-');
        expect(recordPrefix('filter-currency-row-EUR')).toBe('filter-currency-row-');
        expect(recordPrefix('holding-AAPL-row')).toBe('holding-');
    });

    it('keeps an id of the code’s own words whole: digits inside a word are a word', () => {
        expect(recordPrefix('risk-l2-weight')).toBeNull();
        expect(recordPrefix('step2')).toBeNull();
        expect(recordPrefix('tx-table')).toBeNull();
        expect(recordPrefix('row-')).toBeNull();
        // Lower-case codes look like words: only the index knows them.
        expect(recordPrefix('filter-currency-row-eur')).toBeNull();
    });

    it('gives nothing when what would be left is shorter than three characters', () => {
        expect(recordPrefix('a-1')).toBeNull();
        expect(recordPrefix('42-row')).toBeNull();
        expect(recordPrefix('a-EUR')).toBeNull();
        expect(recordPrefix('ab-EUR')).toBe('ab-');
    });
});

describe('testidPrefix / codeTestid', () => {
    it('reads with the index: a static id stays itself, an instance of a templated id becomes its longest prefix', () => {
        expect(testidPrefix('tx-table', INDEX)).toBeNull();
        // Static beats a prefix it happens to start with.
        expect(testidPrefix('row-total', INDEX)).toBeNull();
        expect(testidPrefix('filter-currency-row-EUR', INDEX)).toBe('filter-currency-row-');
        expect(testidPrefix('tab-settings-general', INDEX)).toBe('tab-settings-');
        // An id equal to a prefix is not an instance of it.
        expect(testidPrefix('row-', INDEX)).toBeNull();
    });

    it('trusts the index over the record heuristic', () => {
        // The heuristic would keep `row-total-`; the code templates `row-${…}`.
        expect(recordPrefix('row-total-2')).toBe('row-total-');
        expect(testidPrefix('row-total-2', INDEX)).toBe('row-');
        // A lower-case code the heuristic cannot see.
        expect(testidPrefix('filter-currency-row-eur', INDEX)).toBe('filter-currency-row-');
    });

    it('falls back to the record heuristic for an id the index does not know, and without an index', () => {
        expect(testidPrefix('item-42', INDEX)).toBe('item-');
        expect(testidPrefix('kpi-gain-EUR', INDEX)).toBe('kpi-gain-');
        expect(testidPrefix('unknown-id', INDEX)).toBeNull();
        expect(testidPrefix('row-42')).toBe('row-');
        expect(testidPrefix('asset-row-42-menu', null)).toBe('asset-row-');
        expect(testidPrefix('risk-l2-weight')).toBeNull();
    });

    it('writes an id as the code writes it: itself when static, `prefix*` for an instance', () => {
        expect(codeTestid('tx-table', INDEX)).toBe('tx-table');
        expect(codeTestid('filter-currency-row-EUR', INDEX)).toBe('filter-currency-row-*');
        expect(codeTestid('row-42')).toBe('row-*');
        expect(codeTestid('kpi-gain-EUR')).toBe('kpi-gain-*');
        expect(codeTestid('risk-l2-weight')).toBe('risk-l2-weight');
    });
});

describe('testidChain / nearestTestid', () => {
    it('lists the test ids from the element up, nearest first, as the code writes them', () => {
        expect(testidChain(byId('cell'), INDEX)).toEqual(['row-*', 'tx-table', 'tx-page']);
        expect(testidChain(byId('eur'), INDEX)).toEqual(['filter-currency-row-*', 'filter-currency-list', 'tx-page']);
        expect(testidChain(byId('loose'), INDEX)).toEqual([]);
    });

    it('stops at eight ids', () => {
        const letters = 'abcdefghij';
        document.body.innerHTML = [...letters].map((l) => `<div data-testid="level-${l}">`).join('') + '<b id="leaf"></b>' + '</div>'.repeat(letters.length);
        expect(testidChain(byId('leaf'), INDEX)).toEqual(['level-j', 'level-i', 'level-h', 'level-g', 'level-f', 'level-e', 'level-d', 'level-c']);
    });

    it('finds the nearest element with a test id, the element itself included', () => {
        expect(nearestTestid(byId('cell'))).toBe(byTestid('row-42'));
        expect(nearestTestid(byTestid('tx-table'))).toBe(byTestid('tx-table'));
        expect(nearestTestid(byId('loose'))).toBeNull();
        expect(nearestTestid(null)).toBeNull();
    });
});

describe('testidSelector', () => {
    it('selects a static id exactly, and every instance of a templated one by its prefix', () => {
        expect(testidSelector(byTestid('tx-table'), INDEX)).toBe('[data-testid="tx-table"]');
        const row = testidSelector(byTestid('row-42'), INDEX);
        expect(row).toBe('[data-testid^="row-"]');
        expect(countMatches(row)).toBe(2);
    });

    it('escapes quotes and backslashes, so the selector still finds the element', () => {
        const odd = document.createElement('div');
        odd.setAttribute('data-testid', 'say "hi" \\o/');
        document.body.appendChild(odd);
        const selector = testidSelector(odd, INDEX);
        expect(selector).toBe('[data-testid="say \\"hi\\" \\\\o/"]');
        expect(document.querySelector(selector)).toBe(odd);
    });
});

describe('cssPath', () => {
    it('walks from the nearest test id down to the element, with positions among same-tag siblings', () => {
        const path = cssPath(byId('th2'), INDEX);
        expect(path).toBe('[data-testid="tx-table"] > div > div > table > thead > tr > th:nth-of-type(2)');
        expect(document.querySelector(path)).toBe(byId('th2'));
    });

    it('starts from `body` when no test id surrounds the element', () => {
        const path = cssPath(byId('loose'), INDEX);
        expect(path).toBe('body > main > p:nth-of-type(1)');
        expect(document.querySelector(path)).toBe(byId('loose'));
    });

    it('starts from the prefix of a templated id, and is the test id itself for an element that has one', () => {
        const path = cssPath(byId('cell'), INDEX);
        expect(path).toBe('[data-testid^="row-"] > td:nth-of-type(2) > span');
        expect(Array.from(document.querySelectorAll(path))).toContain(byId('cell'));
        expect(cssPath(byTestid('tx-table'), INDEX)).toBe('[data-testid="tx-table"]');
    });
});

describe('componentSelector', () => {
    it('is the test id itself for an element that has one', () => {
        expect(componentSelector(byTestid('row-42'), INDEX)).toEqual({selector: '[data-testid^="row-"]', breadth: 'component'});
    });

    it('reaches the same node in every instance: the path below the nearest test id, without positions or classes', () => {
        const {selector, breadth} = componentSelector(byId('th2'), INDEX);
        expect(selector).toBe('[data-testid="tx-table"] > div > div > table > thead > tr > th');
        expect(breadth).toBe('component');
        expect(countMatches(selector)).toBe(2);
        expect(componentSelector(byId('cell'), INDEX).selector).toBe('[data-testid^="row-"] > td > span');
        expect(countMatches(componentSelector(byId('cell'), INDEX).selector)).toBe(2);
    });

    it('writes only the classes `keep` accepts, on the element alone, escaped, never Svelte’s scope class', () => {
        const one = componentSelector(byId('th2'), INDEX, (name) => name === 'text-gray-500').selector;
        expect(one).toBe('[data-testid="tx-table"] > div > div > table > thead > tr > th.text-gray-500');
        expect(countMatches(one)).toBe(1);

        const all = componentSelector(byId('th2'), INDEX, () => true).selector;
        expect(all).toBe('[data-testid="tx-table"] > div > div > table > thead > tr > th.text-gray-500.dark\\:text-gray-400');
        expect(document.querySelector(all)).toBe(byId('th2'));
    });

    it('leaves out a class that could break the selector', () => {
        byId('th2').classList.add('a{b', 'c;d', 'e<f');
        expect(componentSelector(byId('th2'), INDEX, () => true).selector).toBe('[data-testid="tx-table"] > div > div > table > thead > tr > th.text-gray-500.dark\\:text-gray-400');
    });

    it('keeps the last six segments of a deeper element, below the test id as a descendant', () => {
        document.body.innerHTML = `<div data-testid="six">${'<div>'.repeat(5)}<b id="at-six"></b>${'</div>'.repeat(5)}</div><div data-testid="deep">${'<div>'.repeat(7)}<b id="at-eight"></b>${'</div>'.repeat(7)}</div>`;
        expect(componentSelector(byId('at-six'), INDEX).selector).toBe('[data-testid="six"] > div > div > div > div > div > b');
        const deep = componentSelector(byId('at-eight'), INDEX).selector;
        expect(deep).toBe('[data-testid="deep"] div > div > div > div > div > b');
        expect(document.querySelector(deep)).toBe(byId('at-eight'));
    });

    it('falls back to the element’s own path when no test id surrounds it', () => {
        expect(componentSelector(byId('loose'), INDEX)).toEqual({selector: 'body > main > p:nth-of-type(1)', breadth: 'element'});
    });
});

describe('selectorNames', () => {
    it('finds a class only where it ends: `.text-gray-5` is not named by `.text-gray-500`', () => {
        expect(selectorNames('.text-gray-500', 'text-gray-500')).toBe(true);
        expect(selectorNames('.text-gray-500:hover', 'text-gray-500')).toBe(true);
        expect(selectorNames('th.sorted.text-gray-500', 'sorted')).toBe(true);
        expect(selectorNames('.text-gray-500', 'text-gray-5')).toBe(false);
        expect(selectorNames('.x-text-gray-500', 'text-gray-500')).toBe(false);
        expect(selectorNames(null, 'text-gray-500')).toBe(false);
    });

    it('reads escaped class names as the stylesheet writes them', () => {
        expect(selectorNames('.dark\\:text-gray-400:where(.dark, .dark *)', 'dark:text-gray-400')).toBe(true);
        expect(selectorNames('.w-1\\/2', 'w-1/2')).toBe(true);
        // `.dark\:text-gray-400` is not the class `dark`.
        expect(selectorNames('.dark\\:text-gray-400', 'dark')).toBe(false);
    });
});

describe('stableClasses / scopeClass', () => {
    it('separates Svelte’s per-build scope class from the classes the code writes', () => {
        expect(stableClasses(byId('th2'))).toEqual(['text-gray-500', 'dark:text-gray-400']);
        expect(scopeClass(byId('th2'))).toBe('svelte-1x2y3z');
        expect(stableClasses(byId('loose'))).toEqual([]);
        expect(scopeClass(byId('loose'))).toBeNull();
        const named = document.createElement('div');
        named.className = 'svelte-kit-layout';
        expect(stableClasses(named)).toEqual(['svelte-kit-layout']);
        expect(scopeClass(named)).toBeNull();
    });
});

describe('routeOf', () => {
    it('keeps the path, and the dashboard tab when there is one, and drops every other parameter', () => {
        expect(routeOf({pathname: '/dashboard', search: '?tab=risk&asset=42'})).toBe('/dashboard?tab=risk');
        expect(routeOf({pathname: '/transactions', search: '?broker=7&q=Alice%20Rossi'})).toBe('/transactions');
        expect(routeOf({pathname: '/dashboard', search: '?tab=a b'})).toBe('/dashboard?tab=a%20b');
        expect(routeOf({pathname: '/designer-lab', search: ''})).toBe('/designer-lab');
    });

    it('names the route by its id when it has one: `[param]` kept, route groups dropped, the record left out', () => {
        expect(routeOf({pathname: '/assets/1234', search: ''}, '/(app)/assets/[id]')).toBe('/assets/[id]');
        expect(routeOf({pathname: '/dashboard', search: '?tab=risk&asset=42'}, '/(app)/dashboard')).toBe('/dashboard?tab=risk');
        expect(routeOf({pathname: '/settings/brokers', search: ''}, '/(app)/(admin)/settings/[section]')).toBe('/settings/[section]');
        expect(routeOf({pathname: '/', search: ''}, '/(app)')).toBe('/');
        // No route id: the path, as before.
        expect(routeOf({pathname: '/assets/1234', search: ''}, null)).toBe('/assets/1234');
        expect(routeOf({pathname: '/assets/1234', search: ''}, '')).toBe('/assets/1234');
    });
});

describe('retarget / countMatches', () => {
    it('turns a lucide icon’s path into its svg, and leaves any other element alone', () => {
        expect(retarget(byId('icon-path'))).toBe(byId('icon'));
        expect(retarget(byId('icon'))).toBe(byId('icon'));
        expect(retarget(byId('chart-path'))).toBe(byId('chart-path'));
        expect(retarget(byId('loose'))).toBe(byId('loose'));
    });

    it('counts the matches of a selector, in a scope, and zero for one the browser rejects', () => {
        expect(countMatches('th')).toBe(2);
        expect(countMatches('span', byTestid('row-42'))).toBe(1);
        expect(countMatches('th[')).toBe(0);
    });
});

describe('no text of the page in an anchor', () => {
    it('never writes the text of any element, with the index the picker uses', () => {
        const outputs: string[] = [];
        for (const el of Array.from(document.body.querySelectorAll('*'))) {
            outputs.push(...testidChain(el, INDEX), cssPath(el, INDEX), componentSelector(el, INDEX).selector, componentSelector(el, INDEX, () => true).selector, ...stableClasses(el), scopeClass(el) ?? '');
            if (el.hasAttribute('data-testid')) outputs.push(testidSelector(el, INDEX), codeTestid(el.getAttribute('data-testid') ?? '', INDEX));
        }
        outputs.push(routeOf({pathname: '/transactions', search: '?q=Alice Rossi&iban=IT60X0542811101000000123456'}));
        outputs.push(routeOf({pathname: '/assets/IT60X0542811101000000123456', search: '?q=Alice%20Rossi'}, '/(app)/assets/[id]'));
        for (const secret of SECRETS) {
            expect(
                outputs.filter((o) => o.includes(secret)),
                secret,
            ).toEqual([]);
        }
        // The control: the outputs are not empty, and they do name the page's structure.
        expect(outputs).toContain('filter-currency-row-*');
        expect(outputs).toContain('[data-testid="tx-table"] > div > div > table > thead > tr > th:nth-of-type(2)');
    });
});
