/**
 * Gate: the early collector of enforced Content-Security-Policy violations, in the inline head script of `src/app.html`
 * (H-55 v2, step 4) — and the anti-FOUC block it must leave exactly as it is.
 *
 * ## What this protects
 *
 * The enforced policy blocks a script nobody of this instance sent (a proxy, a CDN, a browser extension), and the page
 * keeps working without it. `cspNotice.ts` makes that visible, but it is part of the bundle, which loads after the
 * violation it should report may already have happened: a script injected into the HTML is blocked while the parser
 * reads it. So `app.html` collects, before any bundle: a second block, after the theme, in the same inline script —
 *
 *     window.__lfCspViolations = [];
 *     document.addEventListener('securitypolicyviolation', …)   // pushes {directive, blockedURI, sample, sourceFile}
 *                                                                // for each violation whose disposition is 'enforce'
 *
 * — which `cspNotice.ts` drains when it starts (`cspNotice.test.ts` reads that half).
 *
 * The block is added to the most delicate place of the page: the script that decides the theme before the first paint,
 * where a thrown error takes the PWA install prompt and the service worker with it, and a changed line can flash the
 * wrong colours at every load. So this gate holds two things at once:
 *
 *   (a) the new block is what the contract says, and cannot hurt: it comes AFTER `classList.add(theme)`, in its own
 *       `try {} catch (e) {}` — outside the anti-FOUC function —, keeps only `enforce` violations, pushes exactly the four
 *       fields, and a listener that cannot be registered (a throwing `addEventListener`) leaves the theme, the
 *       install-prompt capture and the service worker registration as they were. The script is RUN here against fakes of
 *       the window and the document: the order of the calls and the buffer are observed, not read off the source;
 *   (b) nothing else changed: the anti-FOUC function is pinned verbatim — its text, comments included, is the text read
 *       today (the theme decision, `classList.add`, the `theme-color` pair `themeColorMeta.gate.test.ts` reads) — and so is
 *       the splash `<style>` (by its SHA-256: the colours it copies from `tokens.css` are that gate's business). It adds no
 *       `classList.contains('dark')` (the colour gates forbid reading the theme from the DOM) and no hash or nonce written
 *       by hand: the server computes the hashes of the page's inline scripts from the build.
 *
 * It reads source text and runs one script against fakes, not a browser: that Chromium dispatches the event, and what its
 * fields hold, is the E2E's (`layout/csp-collector.spec.ts`: an injected inline script is blocked and recorded).
 *
 * Red today: `app.html` has no such block: the buffer is never created and no listener is registered. The pins of (b) are
 * green today, and must stay so.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */

import {describe, expect, it} from 'vitest';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

/** `frontend/`: the file is read relative to it. */
const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const APP_HTML = readFileSync(join(FRONTEND, 'src/app.html'), 'utf8');

/**
 * The anti-FOUC function of `app.html` as it reads today, verbatim, from `(function () {` to `})();`: the first line at
 * column 0 as the script's text starts it there, the others as the file indents them (16 spaces). Not the text of this
 * gate's making: a copy of what is in the file, so that any edit of it — a word of a comment, a colour — is a red here.
 */
const ANTI_FOUC = [
    '(function () {',
    "                var stored = '';",
    '                try {',
    "                    stored = localStorage.getItem('librefolio-theme') || '';",
    '                } catch (e) {}',
    "                var theme = stored === 'dark' ? 'dark' : stored === 'light' ? 'light' : window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';",
    '                document.documentElement.classList.add(theme);',
    "                // PWA title bar: the green sidebar's --lf-surface-bar, the same in both themes (N2, D-T17, D-T24). Kept a pair,",
    '                // so a theme of its own stays one edit away; themeColorMeta.gate.test.ts reads the three copies.',
    '                var meta = document.querySelector(\'meta[name="theme-color"]\');',
    "                if (meta) meta.setAttribute('content', theme === 'dark' ? '#1b4334' : '#1b4334');",
    '            })();',
].join('\n');

/** SHA-256 of the body of the splash `<style>` of `app.html`, between its tags, as the file has it today. */
const SPLASH_STYLE_SHA256 = '8a6aa3aeeab7baa5a647eb57192ab3227a16f7f866db60848183baa68de2cccb';

const SPLASH_STYLE = /<style>([\s\S]*?)<\/style>/;

/** The event's name, as a string literal in either quote. */
const VIOLATION_EVENT = /['"]securitypolicyviolation['"]/;

/** `html` without its HTML comments and its `//` comments (a `//` after `:` is a URL): what is code, for counting a name. */
function withoutComments(html: string): string {
    return html.replace(/<!--[\s\S]*?-->/g, '').replace(/(^|[^:\\])\/\/[^\n]*/g, '$1');
}

/** The head's first inline script: the body between `<script>` and `</script>`, before SvelteKit's placeholders. */
function inlineHeadScript(): string {
    const head = APP_HTML.slice(0, APP_HTML.indexOf('%sveltekit.head%'));
    const match = /<script>([\s\S]*?)<\/script>/.exec(head);
    if (!match) throw new Error('src/app.html has no inline <script> in its head: the anti-FOUC script is gone');
    return match[1];
}

/** The index of the `}` that closes the `{` at `open`, counting braces; -1 when the text ends first. Strings and comments of this script hold no braces. */
function closingBrace(text: string, open: number): number {
    let depth = 0;
    for (let index = open; index < text.length; index += 1) {
        if (text[index] === '{') depth += 1;
        else if (text[index] === '}') {
            depth -= 1;
            if (depth === 0) return index;
        }
    }
    return -1;
}

/** The `try {…} catch…` statement that holds `at`, innermost first: its start, the end of its `try` block, and its `catch` clause's end. */
function tryAround(script: string, at: number): {start: number; blockEnd: number; end: number; text: string} | null {
    const starts = [...script.matchAll(/\btry\s*\{/g)].map((match) => match.index).filter((start) => start < at);
    for (const start of starts.reverse()) {
        const blockEnd = closingBrace(script, script.indexOf('{', start));
        if (blockEnd <= at) continue;
        const handler = /^\s*catch\s*(\([^)]*\))?\s*\{/.exec(script.slice(blockEnd + 1));
        if (!handler) continue;
        const handlerOpen = blockEnd + 1 + handler[0].length - 1;
        const end = closingBrace(script, handlerOpen);
        return {start, blockEnd, end, text: script.slice(start, end + 1)};
    }
    return null;
}

// ---------------------------------------------------------------------------
// Running the script against fakes
// ---------------------------------------------------------------------------

type Listener = (event: unknown) => void;

interface Run {
    /** Every call that matters, in order: `classList.add:<theme>`, `document.addEventListener:<type>`, `window.addEventListener:<type>`, `serviceWorker.register`. */
    calls: string[];
    window: Record<string, unknown>;
    listeners: Map<string, Listener[]>;
    thrown: unknown;
}

/**
 * Runs the inline head script with a window, a document and a navigator of this file: light scheme, no stored theme.
 * `refuseViolationListener` makes `document.addEventListener('securitypolicyviolation', …)` throw, as a document that
 * cannot take it would; `frozenWindow` makes the window throw when the buffer is assigned.
 */
function runScript(script: string, {refuseViolationListener = false, frozenWindow = false}: {refuseViolationListener?: boolean; frozenWindow?: boolean} = {}): Run {
    const calls: string[] = [];
    const listeners = new Map<string, Listener[]>();
    const target: Record<string, unknown> = {
        matchMedia: () => ({matches: false}),
        addEventListener: (type: string) => void calls.push(`window.addEventListener:${type}`),
    };
    // A window that refuses the buffer: setting it throws, as a frozen or a hostile one would in strict code
    const win: Record<string, unknown> = frozenWindow
        ? new Proxy(target, {
              set(owner, property, value) {
                  if (property === '__lfCspViolations') throw new TypeError('this window takes no new property');
                  return Reflect.set(owner, property, value);
              },
          })
        : target;
    const doc = {
        documentElement: {classList: {add: (name: string) => void calls.push(`classList.add:${name}`)}},
        querySelector: () => ({setAttribute: () => void calls.push('meta.setAttribute')}),
        addEventListener: (type: string, listener: Listener) => {
            calls.push(`document.addEventListener:${type}`);
            if (refuseViolationListener && type === 'securitypolicyviolation') throw new TypeError('this document takes no such listener');
            listeners.set(type, [...(listeners.get(type) ?? []), listener]);
        },
    };
    const navigator = {serviceWorker: {register: () => void calls.push('serviceWorker.register')}};
    const localStorage = {getItem: () => null};
    let thrown: unknown;
    try {
        new Function('window', 'document', 'navigator', 'localStorage', script)(win, doc, navigator, localStorage);
    } catch (error) {
        thrown = error;
    }
    return {calls, window: target, listeners, thrown};
}

/** A `securitypolicyviolation` event, with more fields than the block keeps. */
function violation(disposition: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {effectiveDirective: 'script-src-elem', blockedURI: 'inline', sample: 'window.__injected = 1;', sourceFile: 'http://localhost:6041/', lineNumber: 7, columnNumber: 3, violatedDirective: 'script-src', disposition, ...overrides};
}

const dispatch = (run: Run, event: Record<string, unknown>): void => {
    for (const listener of run.listeners.get('securitypolicyviolation') ?? []) listener(event);
};

describe('app.html — the early collector of enforced CSP violations', () => {
    const script = inlineHeadScript();

    it('(a1) the block exists once, in the head script: one securitypolicyviolation listener in the whole page, and the buffer it fills', () => {
        expect(withoutComments(APP_HTML).match(/securitypolicyviolation/g) ?? [], 'one listener in the page’s code, in the inline head script — not a second in the body (a comment may name the event)').toHaveLength(1);
        expect(withoutComments(script), 'the head script holds it').toMatch(VIOLATION_EVENT);
        const buffer = /window\.__lfCspViolations\s*=\s*\[\s*\]/.exec(script);
        expect(buffer, 'and the buffer, started before the listener').not.toBeNull();
        expect(buffer?.index ?? Number.MAX_SAFE_INTEGER, 'the buffer is created before the listener is registered').toBeLessThan(script.search(VIOLATION_EVENT));
    });

    it('(a2) it follows the theme: after classList.add(theme), outside the anti-FOUC function, in a try/catch of its own', () => {
        const listenerAt = script.search(VIOLATION_EVENT);
        const themeAt = script.indexOf('classList.add(theme)');
        expect(themeAt, 'premise: the theme is applied by classList.add(theme)').toBeGreaterThan(-1);
        expect(listenerAt, 'the block comes after the theme is applied').toBeGreaterThan(themeAt);

        const iifeEnd = script.indexOf('})();') + '})();'.length;
        expect(script.indexOf('})();'), 'premise: the anti-FOUC function closes with })();').toBeGreaterThan(themeAt);
        const guard = tryAround(script, listenerAt);
        expect(guard, 'the listener sits inside a try { } catch { } statement').not.toBeNull();
        expect(guard?.start, 'a try of its own: it starts after the anti-FOUC function has closed, so it is not a handler inside it').toBeGreaterThanOrEqual(iifeEnd);
        expect(guard?.text, 'and it holds the buffer and the filter too: one block').toMatch(/__lfCspViolations\s*=\s*\[\s*\][\s\S]*securitypolicyviolation[\s\S]*['"]enforce['"]/);
        expect(
            script
                .slice(iifeEnd, guard?.start)
                .replace(/\/\/[^\n]*/g, '')
                .trim(),
            'between the function and the try: nothing that can throw on its own',
        ).toBe('');
    });

    it('(a3) run: the theme is applied first, then the buffer and the listener; an enforced violation is pushed with exactly four fields, a report-only one is not', () => {
        const run = runScript(script);

        expect(run.thrown, 'the script runs to its end').toBeUndefined();
        const themeAt = run.calls.indexOf('classList.add:light');
        const listenerAt = run.calls.indexOf('document.addEventListener:securitypolicyviolation');
        expect(themeAt, 'the theme was applied').toBeGreaterThan(-1);
        expect(listenerAt, 'the listener was registered on the document').toBeGreaterThan(-1);
        expect(themeAt, 'the theme first: nothing of the collector stands between the page and its colours').toBeLessThan(listenerAt);
        expect(run.window.__lfCspViolations, 'an empty buffer from the start: cspNotice drains it, even when nothing was blocked').toEqual([]);

        dispatch(run, violation('enforce'));
        dispatch(run, violation('report', {blockedURI: 'https://cdn.example.com/x.js'}));
        dispatch(run, violation('enforce', {effectiveDirective: 'script-src', blockedURI: 'eval', sample: '1 + 1', sourceFile: ''}));

        expect(run.window.__lfCspViolations, 'enforced ones only, each as {directive, blockedURI, sample, sourceFile} and nothing more').toEqual([
            {directive: 'script-src-elem', blockedURI: 'inline', sample: 'window.__injected = 1;', sourceFile: 'http://localhost:6041/'},
            {directive: 'script-src', blockedURI: 'eval', sample: '1 + 1', sourceFile: ''},
        ]);
    });

    it('(a4) a listener that cannot be registered changes nothing else: the theme, the install-prompt capture and the service worker are as without the block', () => {
        const refused = runScript(script, {refuseViolationListener: true});

        expect(refused.thrown, 'its own try/catch swallows it: the script is not stopped').toBeUndefined();
        expect(refused.calls, 'what comes after the block still runs').toEqual(expect.arrayContaining(['classList.add:light', 'meta.setAttribute', 'window.addEventListener:beforeinstallprompt', 'serviceWorker.register']));
        expect(refused.calls.indexOf('document.addEventListener:securitypolicyviolation'), 'premise: the block did try to register it').toBeGreaterThan(-1);
    });

    it('(a5) a window that refuses the buffer (its assignment throws) does not stop the script either', () => {
        const frozen = runScript(script, {frozenWindow: true});

        expect(frozen.thrown, 'the buffer assignment is inside the block’s try/catch').toBeUndefined();
        expect(frozen.calls).toEqual(expect.arrayContaining(['classList.add:light', 'window.addEventListener:beforeinstallprompt', 'serviceWorker.register']));
    });
});

describe('app.html — what the block must not touch', () => {
    const script = inlineHeadScript();

    it('(b1) the anti-FOUC function is, character for character, the one read today: the theme decision, classList.add, the theme-color pair', () => {
        const start = script.indexOf('(function () {');
        const end = script.indexOf('})();', start) + '})();'.length;

        expect(start, 'premise: the anti-FOUC function is the head script’s first statement').toBeGreaterThan(-1);
        expect(script.slice(start, end), 'the function is unchanged: any edit of it — even a comment — is a decision of the colour workstream, not of the CSP').toBe(ANTI_FOUC);
        expect(
            script
                .slice(0, start)
                .trim()
                .replace(/\/\/[^\n]*/g, '')
                .trim(),
            'and nothing precedes it but its comments: the collector comes after',
        ).toBe('');
    });

    it('(b2) the splash <style> is the one read today (by its SHA-256), and the block reads no theme from the DOM', () => {
        const style = SPLASH_STYLE.exec(APP_HTML);
        expect(style, 'premise: app.html has its splash <style>').not.toBeNull();
        expect(
            createHash('sha256')
                .update(style?.[1] ?? '', 'utf8')
                .digest('hex'),
            'the splash’s copies of the colour roles are tokens.css’s business (themeColorMeta.gate.test.ts): not touched here',
        ).toBe(SPLASH_STYLE_SHA256);
        expect(APP_HTML, 'no classList.contains(dark): the theme is not read back from the DOM (the colour gates)').not.toMatch(/classList\.contains\(\s*['"]dark['"]\s*\)/);
    });

    it('(b3) no hash and no nonce written by hand: the server computes the hashes of the page’s inline scripts from the build', () => {
        expect(APP_HTML, 'no sha256/sha384/sha512 source of a policy').not.toMatch(/['"]sha(256|384|512)-[A-Za-z0-9+/=]+['"]/);
        expect(APP_HTML, 'no nonce').not.toMatch(/nonce-|\bnonce=/i);
        expect(APP_HTML, 'no policy of its own in a <meta>: the header is the server’s').not.toMatch(/http-equiv\s*=\s*["']content-security-policy/i);
    });
});
