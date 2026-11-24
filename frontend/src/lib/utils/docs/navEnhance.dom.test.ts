// @vitest-environment jsdom
//
// The docblock above is load-bearing: the script walks the page's menu, builds a <template> and replaces list items, which
// jsdom provides; no real navigation happens, the page address is the one the test gives `location`.
/**
 * navEnhance.dom.test.ts — the browser half of `mkdocs_src/docs/javascripts/nav-enhance.js` (lane 84-D, the shared menu).
 *
 * After the build, a page keeps in its menu what Material draws for a pruned navigation: the branch of the page whole, every
 * other group one link to its first page (`li.md-nav__item--pruned`). The whole menu of the language is written once, after
 * this code, as `window.LF_NAV[language]` (every link a path from the site's root). The script runs while the page is parsed,
 * right after the menu's `<nav>`, and puts each group back. Pinned here, on the script as published:
 *
 *   - a pruned group is replaced by the group of the shared menu with the same depth and the same first page, the first page
 *     being read AGAINST THE PAGE (Material writes a link as short as it can be from the page: `../x/` inside the section) with
 *     the site's root (`data-lf-root`) taken off; the links of what is put back become `root + path`;
 *   - the key is the depth AND the first page: an outer group and its first inner group (the same first page) are not mixed up;
 *   - what is not pruned is not touched: the branch of the page, its active link, its checked toggles;
 *   - nothing to put back (no `data-lf-nav` on the menu, no shared menu for the language, no group with that key) leaves the
 *     page as it was and throws nothing;
 *   - a group is put back with the toggle and label ids of the shared menu (the ids are positions, the same in every page).
 *
 * `document.currentScript` is read-only in jsdom: the test hands the script a document stand-in whose `currentScript` is the
 * script element it has just put after the menu, as the parser does.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {afterEach, beforeEach, describe, expect, it} from 'vitest';

const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const SOURCE = readFileSync(resolve(FRONTEND, '../mkdocs_src/docs/javascripts/nav-enhance.js'), 'utf8');

/** The shared menu of the language: three groups, the second inside the first, both starting at `user/a/`; one more tab. */
const SHARED = `<ul class="md-nav__list">
<li class="md-nav__item md-nav__item--nested"><input class="md-nav__toggle md-toggle md-toggle--indeterminate" type="checkbox" id="__nav_1"><label class="md-nav__link" for="__nav_1" id="__nav_1_label"><span class="md-ellipsis">User</span><span class="md-nav__icon md-icon"></span></label>
<nav class="md-nav" data-md-level="1"><ul class="md-nav__list">
<li class="md-nav__item md-nav__item--nested"><input class="md-nav__toggle md-toggle md-toggle--indeterminate" type="checkbox" id="__nav_1_1"><label class="md-nav__link" for="__nav_1_1" id="__nav_1_1_label"><span class="md-ellipsis">Detail</span><span class="md-nav__icon md-icon"></span></label>
<nav class="md-nav" data-md-level="2"><ul class="md-nav__list"><li class="md-nav__item"><a href="user/a/" class="md-nav__link">A</a></li><li class="md-nav__item"><a href="user/b/" class="md-nav__link">B</a></li></ul></nav></li>
<li class="md-nav__item"><a href="user/c/" class="md-nav__link">C</a></li></ul></nav></li>
<li class="md-nav__item md-nav__item--nested"><input class="md-nav__toggle md-toggle md-toggle--indeterminate" type="checkbox" id="__nav_2"><label class="md-nav__link" for="__nav_2" id="__nav_2_label"><span class="md-ellipsis">Admin</span><span class="md-nav__icon md-icon"></span></label>
<nav class="md-nav" data-md-level="1"><ul class="md-nav__list"><li class="md-nav__item"><a href="admin/x/" class="md-nav__link">X</a></li></ul></nav></li>
</ul>`;

/** A page in `user/c/`: the tab «User» whole (its inner group pruned), the other tab pruned. Links are as short as Material writes them. */
const PAGE = `<div class="md-sidebar__inner"><nav class="md-nav md-nav--primary" data-lf-nav="en" data-lf-root="../../"><ul class="md-nav__list" data-md-scrollfix>
<li class="md-nav__item md-nav__item--active md-nav__item--section md-nav__item--nested"><input class="md-nav__toggle md-toggle" type="checkbox" id="__nav_1" checked><label class="md-nav__link" for="__nav_1" id="__nav_1_label"><span class="md-ellipsis">User</span><span class="md-nav__icon md-icon"></span></label>
<nav class="md-nav" data-md-level="1" aria-expanded="true"><ul class="md-nav__list">
<li class="md-nav__item md-nav__item--pruned md-nav__item--nested"><a href="../a/" class="md-nav__link"><span class="md-ellipsis">Detail</span><span class="md-nav__icon md-icon"></span></a></li>
<li class="md-nav__item md-nav__item--active"><a href="./" class="md-nav__link md-nav__link--active">C</a></li></ul></nav></li>
<li class="md-nav__item md-nav__item--pruned md-nav__item--nested"><a href="../../admin/x/" class="md-nav__link"><span class="md-ellipsis">Admin</span><span class="md-nav__icon md-icon"></span></a></li>
</ul></nav><script id="enhancer"></script></div>`;

function run(document_: Document): void {
    const script = document_.getElementById('enhancer') as HTMLScriptElement;
    const standIn = {currentScript: script, createElement: (tag: string) => document_.createElement(tag)};
    new Function('document', 'window', 'location', SOURCE)(standIn, window, window.location);
}

function mount(html = PAGE, shared: string | null = SHARED, language = 'en'): void {
    document.body.innerHTML = html;
    const w = window as unknown as {LF_NAV?: Record<string, string>};
    w.LF_NAV = shared === null ? undefined : {[language]: shared};
}

const links = () => [...document.querySelectorAll('nav a[href]')].map((a) => a.getAttribute('href'));

describe('nav-enhance.js', () => {
    beforeEach(() => {
        window.history.replaceState({}, '', '/LibreFolio/user/c/');
    });
    afterEach(() => {
        document.body.innerHTML = '';
        delete (window as unknown as {LF_NAV?: unknown}).LF_NAV;
    });

    it('puts every pruned group back, found by depth and first page read against the page', () => {
        mount();
        run(document);

        expect(document.querySelectorAll('.md-nav__item--pruned')).toHaveLength(0);
        // the inner group «Detail» (a stub whose link was `../a/`) and the other tab «Admin» (`../../admin/x/`) are the shared ones
        expect(document.getElementById('__nav_1_1')).not.toBeNull();
        expect(document.getElementById('__nav_2')).not.toBeNull();
        expect(document.querySelector('#__nav_1_1_label .md-ellipsis')?.textContent).toBe('Detail');
        expect(document.querySelector('#__nav_2_label .md-ellipsis')?.textContent).toBe('Admin');
        // each id exactly once: «Detail» is not the whole tab «User» (same first page, other depth) put in its place
        for (const id of ['__nav_1', '__nav_1_1', '__nav_2']) expect(document.querySelectorAll(`#${id}`)).toHaveLength(1);
    });

    it('turns the links of what it puts back into root + path', () => {
        mount();
        run(document);

        expect(links()).toEqual(expect.arrayContaining(['../../user/a/', '../../user/b/', '../../admin/x/']));
        expect(links().some((href) => href === 'user/a/' || href === 'admin/x/')).toBe(false); // none is left as a path from the root
    });

    it('does not touch what is not pruned', () => {
        mount();
        run(document);

        const active = document.querySelector('a.md-nav__link--active');
        expect(active?.getAttribute('href')).toBe('./');
        expect((document.getElementById('__nav_1') as HTMLInputElement).checked).toBe(true);
        expect(document.querySelector('li.md-nav__item--section')).not.toBeNull();
    });

    it('does not mix an outer group with its first inner group (the same first page)', () => {
        // two stubs with the SAME first page: the tab «User» (depth 1) and «Detail» inside it (depth 2) — each gets its own group
        mount(
            `<div><nav class="md-nav md-nav--primary" data-lf-nav="en" data-lf-root="../"><ul class="md-nav__list">
<li class="md-nav__item md-nav__item--pruned md-nav__item--nested"><a href="../user/a/" class="md-nav__link"><span class="md-ellipsis">User</span></a></li>
</ul></nav><script id="enhancer"></script></div>`,
        );
        run(document);

        // depth 1 + first page user/a/ is the tab «User», not «Detail»
        expect(document.getElementById('__nav_1')).not.toBeNull();
        expect(document.getElementById('__nav_1_1')).not.toBeNull(); // inside it, as in the shared menu
        expect(document.querySelectorAll('#__nav_1_label')).toHaveLength(1);
    });

    it('leaves the page as it was when there is nothing to put back', () => {
        mount(PAGE, null);
        const before = document.body.innerHTML;
        expect(() => run(document)).not.toThrow();
        expect(document.body.innerHTML).toBe(before);

        mount(PAGE, SHARED, 'it'); // a shared menu for another language
        const other = document.body.innerHTML;
        run(document);
        expect(document.body.innerHTML).toBe(other);

        mount(PAGE.replace(' data-lf-nav="en"', ''));
        const unmarked = document.body.innerHTML;
        run(document);
        expect(document.body.innerHTML).toBe(unmarked);
    });

    it('leaves a group whose key the shared menu does not hold', () => {
        mount(PAGE.replace('href="../../admin/x/"', 'href="../../admin/other/"'));
        run(document);

        const stubs = document.querySelectorAll('.md-nav__item--pruned');
        expect(stubs).toHaveLength(1);
        expect(stubs[0].querySelector('a')?.getAttribute('href')).toBe('../../admin/other/');
        expect(document.getElementById('__nav_1_1')).not.toBeNull(); // the other group was still put back
    });
});
