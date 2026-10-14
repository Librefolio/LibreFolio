/**
 * Guard: no page changes the browser tab title (workstream K, step 12c).
 *
 * ## What this protects
 *
 * The developer's rule of 2026-09-29: the tab always shows the `<title>` of `src/app.html`, on
 * every page. A page title is not only a label: Svelte applies a `<svelte:head><title>` by
 * assigning `document.title` in an effect after the page mounts, and never restores it when the
 * page unmounts — which is how "Files - LibreFolio" outlived the Files page (workstream J).
 *
 * ## What it does, and what it deliberately does not
 *
 * It scans the source for the two forms of a title write and fails, listing `file:line`, on any
 * of them:
 *
 *   A. a `<title>` element inside a `<svelte:head>` block, in the markup of a `.svelte` file;
 *   B. an assignment to `document.title` (`=`, `+=`, `??=`, `||=`, `&&=`, bracket access too), in
 *      any `.svelte`, `.ts` or `.js` file.
 *
 * Every such file under `src` is read, except tests (`*.test.*`, `*.spec.*`, `__tests__/`,
 * `__mocks__/`) and the API clients generated from the backend contracts: those are gitignored and
 * never written by hand, so scanning them would make the verdict depend on the checkout.
 * `static/offline.html` is a separate document with a title of its own, out of scope by decision.
 *
 * The allow-list is EMPTY and must stay empty: an entry would be a page doing exactly what the
 * rule forbids. Changing the rule is the developer's call, not an edit to this file.
 *
 * ## Completeness, stated honestly
 *
 * The forms are a floor, not a proof. The guard does not see a title written through the DOM
 * (`querySelector('title').textContent = …`), through an alias of `document`, `Object.assign` or
 * `Reflect.set`, by a component placed inside a `<svelte:head>` that renders the `<title>` itself,
 * or by a dependency. `e2e/layout/document-title.spec.ts` is the other half: it reads the title the
 * running app shows on every main page, whatever wrote it. The guard does not parse either: a
 * comment quoting a form B assignment is reported like code — reword the comment. When the rule
 * grows, grow the forms in the same change.
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: paths are reported relative to it, the directory the runner and `vitest run` start from. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SRC = join(FRONTEND, 'src');
const APP_HTML = join(SRC, 'app.html');

/** Written by `./dev.py api sync` and `frontend/scripts/generate-tools-client.mjs` from the backend contracts; gitignored. */
const GENERATED = new Set(['src/lib/api/generated.ts', 'src/lib/api/generated-tools.ts', 'src/lib/api/tool-contract-map.generated.ts']);

type Form = '<svelte:head> <title>' | 'document.title write';

interface TitleWrite {
    file: string;
    line: number;
    form: Form;
    /** The whitespace-collapsed source line. The key, together with `file`. */
    snippet: string;
}

interface AllowedTitleWrite {
    file: string;
    snippet: string;
    why: string;
}

/**
 * Title writes allowed to exist: NONE, and it must stay that way. The developer's rule (K step 12c,
 * 2026-09-29) is that no page changes the browser tab title — the tab shows the `<title>` of
 * `src/app.html` and nothing else — so an entry here would be a page breaking the rule by
 * permission. Remove the write instead.
 */
const ALLOWED_TITLE_WRITES: readonly AllowedTitleWrite[] = [];

const SVELTE_HEAD_OPEN = /<svelte:head\b[^>]*>/g;
const SVELTE_HEAD_CLOSE = /<\/svelte:head\s*>/;
const TITLE_OPEN = /<title(?=[\s/>])/g;
const DOCUMENT_TITLE_WRITE = /\bdocument\s*(?:\.\s*title\b|\[\s*(['"`])title\1\s*\])\s*(?:\+|\?\?|\|\||&&)?=(?!=)/g;
/** Where a `.svelte` file is not markup: a `<svelte:head>` quoted there is text, not a block. */
const NOT_MARKUP = [/<!--[\s\S]*?-->/g, /<script\b[^>]*>[\s\S]*?<\/script\s*>/g, /<style\b[^>]*>[\s\S]*?<\/style\s*>/g];

const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');

/** Whether a path (relative to `frontend/`) is source this guard reads. */
function isScanned(path: string): boolean {
    if (!/\.(svelte|ts|js)$/.test(path) || /\.(test|spec)\.(ts|js)$/.test(path)) return false;
    if (path.split('/').some((segment) => segment === '__tests__' || segment === '__mocks__' || segment === 'node_modules')) return false;
    return !GENERATED.has(path);
}

function sourceFiles(dir: string = SRC, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) {
            sourceFiles(full, acc);
        } else {
            const path = relative(FRONTEND, full).replaceAll('\\', '/');
            if (isScanned(path)) acc.push(path);
        }
    }
    return acc;
}

/** The markup of a `.svelte` file: comments, scripts and styles blanked, newlines kept, so every offset keeps its line. */
function markupOf(text: string): string {
    return NOT_MARKUP.reduce((markup, block) => markup.replace(block, (found) => found.replace(/[^\n]/g, ' ')), text);
}

/**
 * The title writes of one source file. A function of its own so that a synthetic source goes
 * through exactly the code a real file goes through: a positive control run on a copy of this
 * logic would test the copy.
 */
function scanSource(file: string, text: string): TitleWrite[] {
    const lines = text.split('\n');
    const at = (offset: number, form: Form): TitleWrite => {
        const line = text.slice(0, offset).split('\n').length;
        return {file, line, form, snippet: collapse(lines[line - 1])};
    };
    const writes: TitleWrite[] = [];
    if (file.endsWith('.svelte')) {
        const markup = markupOf(text);
        for (const open of markup.matchAll(SVELTE_HEAD_OPEN)) {
            if (open[0].endsWith('/>')) continue;
            const start = open.index + open[0].length;
            const length = markup.slice(start).search(SVELTE_HEAD_CLOSE);
            // An unclosed block does not compile: nothing of it reaches the page.
            if (length === -1) continue;
            for (const title of markup.slice(start, start + length).matchAll(TITLE_OPEN)) writes.push(at(start + title.index, '<svelte:head> <title>'));
        }
    }
    for (const write of text.matchAll(DOCUMENT_TITLE_WRITE)) writes.push(at(write.index, 'document.title write'));
    return writes.sort((a, b) => a.line - b.line);
}

const key = (site: {file: string; snippet: string}): string => `${site.file}\u0000${site.snippet}`;
const caught = (file: string, text: string): string[] => scanSource(file, text).map((write) => `${write.form} @${write.line}`);

describe('browser tab title — no page changes it (K step 12c guard)', () => {
    const files = sourceFiles();
    const writes = files.flatMap((file) => scanSource(file, readFileSync(join(FRONTEND, file), 'utf8')));

    it('catches every form it enumerates, and none of their look-alikes', () => {
        // The positive control of the verdict below: "no title write" is also what a scanner
        // whose patterns match nothing would report.
        expect(caught('a.svelte', "<svelte:head>\n    <title>{$t('uploads.title')} - LibreFolio</title>\n</svelte:head>")).toEqual(['<svelte:head> <title> @2']);
        expect(caught('a.svelte', '<svelte:head><title>Tools · LibreFolio</title></svelte:head>')).toEqual(['<svelte:head> <title> @1']);
        expect(caught('a.svelte', '<svelte:head>\n    {#if ready}\n        <title data-x="1">{name}</title>\n    {/if}\n</svelte:head>')).toEqual(['<svelte:head> <title> @3']);
        expect(caught('a.ts', "document.title = 'LibreFolio';")).toEqual(['document.title write @1']);
        expect(caught('a.js', "window.document.title='x'")).toEqual(['document.title write @1']);
        expect(caught('a.svelte.ts', "document.title += ' · x';\ndocument['title'] = x;\ndocument.title ??= x;")).toEqual(['document.title write @1', 'document.title write @2', 'document.title write @3']);
        expect(caught('a.ts', 'document.title\n    = next;')).toEqual(['document.title write @1']);
        expect(caught('a.svelte', "<button onclick={() => (document.title = 'x')}>x</button>")).toEqual(['document.title write @1']);

        // Look-alikes: a head without a title, an SVG title, a quoted head, a read, a comparison.
        expect(caught('a.svelte', '<svelte:head>\n    <meta name="description" content="x" />\n</svelte:head>')).toEqual([]);
        expect(caught('a.svelte', '<svg viewBox="0 0 1 1"><title>Icon</title></svg>')).toEqual([]);
        expect(caught('a.svelte', '<svelte:head />\n<svg><title>Icon</title></svg>')).toEqual([]);
        expect(caught('a.svelte', "<script>\n    // e.g. <svelte:head><title>x</title></svelte:head>\n    const s = '<svelte:head><title>x</title></svelte:head>';\n</script>")).toEqual([]);
        expect(caught('a.svelte', '<!-- <svelte:head><title>x</title></svelte:head> -->')).toEqual([]);
        expect(caught('a.ts', "const html = '<svelte:head><title>x</title></svelte:head>';")).toEqual([]);
        expect(caught('a.ts', "const current = document.title;\nif (document.title === 'x' || document.title == y || document.title !== z) {}\ndocument.titleText = 'x';")).toEqual([]);
    });

    it('reads every source file of the app, and no test or generated client', () => {
        expect(isScanned('src/routes/(app)/files/+page.svelte')).toBe(true);
        expect(isScanned('src/lib/stores/app/notify.svelte.ts')).toBe(true);
        expect(isScanned('src/lib/utils/anything.js')).toBe(true);
        expect(isScanned('src/routes/(app)/layout.gate.test.ts')).toBe(false);
        expect(isScanned('src/lib/utils/anything.spec.ts')).toBe(false);
        expect(isScanned('src/__tests__/harness/AppLayoutGateHarness.svelte')).toBe(false);
        expect(isScanned('src/__mocks__/$app/navigation.ts')).toBe(false);
        expect(isScanned('src/lib/api/generated.ts')).toBe(false);
        expect(isScanned('src/app.html')).toBe(false);

        // The walk reaches the layouts and the pages where the title writers lived: a scan of the
        // wrong directory would report them clean too.
        expect(files).toEqual(expect.arrayContaining(['src/routes/+layout.svelte', 'src/routes/(app)/+layout.svelte', 'src/routes/(app)/files/+page.svelte', 'src/routes/(app)/tools/+page.svelte', 'src/routes/(app)/tools/[tool_code]/+page.svelte']));
    });

    it('keeps src/app.html as the one source of the tab title', () => {
        const titles = [...readFileSync(APP_HTML, 'utf8').matchAll(/<title\b[^>]*>([^<]*)<\/title>/g)].map((match) => match[1].trim());

        expect(titles, 'src/app.html must hold exactly one <title>: it is the only title the app shows').toHaveLength(1);
        expect(titles[0], 'the <title> of src/app.html must not be empty').not.toBe('');
    });

    it('finds no <title> in a <svelte:head> and no write to document.title anywhere in src', () => {
        const allowed = new Set(ALLOWED_TITLE_WRITES.map(key));
        const offenders = writes.filter((write) => !allowed.has(key(write))).map((write) => `${write.file}:${write.line}  [${write.form}]  ${write.snippet}`);
        const rule = "No page changes the browser tab title: the tab always shows the <title> of src/app.html (developer's rule, K step 12c).";

        expect(offenders, ['', rule, 'Remove these title writes — the allow-list stays empty:', '', ...offenders, ''].join('\n  ')).toEqual([]);
    });

    it('keeps the allow-list empty: the rule has no exceptions', () => {
        expect(ALLOWED_TITLE_WRITES).toEqual([]);
    });
});
