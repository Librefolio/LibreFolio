/**
 * Gate: no inline event-handler attribute written inside a string, a template literal or raw HTML (H-55 v2).
 *
 * The enforced `script-src` has no 'unsafe-inline', so `<img onerror="…">` is blocked (a `script-src-attr` violation)
 * and the handler never runs. A Svelte `onclick={fn}` attribute is a different thing — it compiles to addEventListener
 * and is allowed — and so is `on:click`. What this gate finds is an `on…=` followed by a QUOTE: that is the HTML
 * attribute form, which only exists inside a string or an HTML file.
 *
 * Scans `src/**` for .ts .svelte .js .html, minus `*.test.ts`, `__tests__` and `node_modules`; `src/app.html` is part of
 * the scan and must hold none. Each hit is reported as file:line.
 */
import {existsSync, readdirSync, readFileSync, statSync} from 'node:fs';
import {join, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

const SRC = fileURLToPath(new URL('.', import.meta.url));
const EXTENSIONS = ['.ts', '.svelte', '.js', '.html'];

/** `on<letters>` not glued to a longer name, then `=`, then a quote: the HTML attribute form (also right after a quote). */
const INLINE_HANDLER = /(?<![\w$-])on[a-z]+\s*=\s*["']/;

function isScanned(path: string): boolean {
    if (!EXTENSIONS.some((e) => path.endsWith(e))) return false;
    if (path.endsWith('.test.ts')) return false;
    const parts = path.split(sep);
    return !parts.includes('__tests__') && !parts.includes('node_modules');
}

function walk(dir: string, out: string[] = []): string[] {
    for (const name of readdirSync(dir)) {
        if (name === 'node_modules' || name === '__tests__') continue;
        const full = join(dir, name);
        if (statSync(full).isDirectory()) walk(full, out);
        else if (isScanned(full)) out.push(full);
    }
    return out;
}

/** `file:line` plus the trimmed line, for each line of `text` that carries an inline handler attribute. */
function findInlineHandlers(text: string, label: string): string[] {
    const hits: string[] = [];
    text.split('\n').forEach((line, i) => {
        if (INLINE_HANDLER.test(line)) hits.push(`${label}:${i + 1}  ${line.trim().slice(0, 140)}`);
    });
    return hits;
}

describe('no inline event handlers (the enforced CSP blocks them)', () => {
    it('the scanner flags a synthetic inline handler in a template literal', () => {
        const sample = ['const a = `<img src="${u}" onerror="this.style.display=\'none\'" />`;', 'const b = \'<a href="#" onclick="go()">x</a>\';', "const c = `<img\n  onload='ok()'>`;"].join('\n');
        const hits = findInlineHandlers(sample, 'synthetic');
        expect(hits.map((h) => h.split('  ')[0])).toEqual(['synthetic:1', 'synthetic:2', 'synthetic:4']);
    });

    it('the scanner does not flag Svelte handler attributes or ordinary code', () => {
        const sample = ['<button onclick={fn}>x</button>', '<button onclick={() => open = "yes"}>x</button>', '<input on:input={fn} />', 'const isOn = "yes";', 'const x = { onChange: () => {} };'].join('\n');
        expect(findInlineHandlers(sample, 'synthetic')).toEqual([]);
    });

    it('src/app.html holds no inline event handler', () => {
        const html = join(SRC, 'app.html');
        expect(existsSync(html)).toBe(true);
        expect(findInlineHandlers(readFileSync(html, 'utf8'), 'src/app.html')).toEqual([]);
    });

    it('no source file under src/ carries an inline event-handler attribute', () => {
        const files = walk(SRC);
        expect(files.length).toBeGreaterThan(100); // the scan really walked the tree
        const hits: string[] = [];
        for (const file of files) {
            const rel = 'src/' + relative(SRC, file).split(sep).join('/');
            hits.push(...findInlineHandlers(readFileSync(file, 'utf8'), rel));
        }
        expect(hits, `inline event-handler attributes are blocked by the enforced script-src; use data-hide-on-error or a listener:\n${hits.join('\n')}`).toEqual([]);
    });
});
