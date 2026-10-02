// @vitest-environment jsdom
/**
 * sanitizeHtml — the sanitiser for the `{@html}` sinks that must render mixed markup of mixed origin
 * (workstream K, step 13, item 0): toasts, tooltips, resolved validation messages.
 *
 * What it must do is two-sided, and both sides are pinned here:
 *   - remove what runs: event-handler attributes, `<script>`, `javascript:` URLs;
 *   - keep what the app itself puts into those messages: spans with classes (the emoji flags), icons
 *     as `<img src alt class>` and as inline lucide `<svg>`, `<br>`, `<strong>`/`<b>`, `<code>`, inline
 *     `style`, KaTeX's span markup, and the app's own links with their `data-testid` — a sanitiser
 *     that strips those breaks the UI (and the toast specs that click those links) while looking safe.
 *
 * Assertions read the parsed result, never the serialised string: attribute order and quoting are
 * the sanitiser's business, what reaches the DOM is ours.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action
 * `component-unit`): DOMPurify needs a DOM, so this file runs in jsdom like the component tests.
 */
import {describe, expect, it} from 'vitest';
import {sanitizeHtml} from './sanitizeHtml';

/** What `{@html}` would build from the sanitised string, in a detached container. */
function rendered(html: string): HTMLElement {
    const out = sanitizeHtml(html);
    expect(typeof out).toBe('string');
    const host = document.createElement('div');
    host.innerHTML = out;
    return host;
}

const withHandlers = (root: HTMLElement): string[] =>
    [...root.querySelectorAll('*')].flatMap((el) =>
        el
            .getAttributeNames()
            .filter((name) => name.toLowerCase().startsWith('on'))
            .map((name) => `<${el.tagName.toLowerCase()} ${name}>`),
    );

describe('sanitizeHtml — removes what runs', () => {
    it('drops event-handler attributes and keeps the element they were on', () => {
        const root = rendered('<img src="x" alt="flag" class="w-4 h-4" onerror="window.__k13=1"><span class="badge" onclick="alert(1)" onmouseover="alert(2)">A</span>');
        expect(withHandlers(root)).toEqual([]);

        const img = root.querySelector('img');
        expect(img).not.toBeNull();
        expect(img?.getAttribute('src')).toBe('x');
        expect(img?.getAttribute('alt')).toBe('flag');
        expect(img?.getAttribute('class')).toBe('w-4 h-4');
        const badge = root.querySelector('span');
        expect(badge?.getAttribute('class')).toBe('badge');
        expect(badge?.textContent).toBe('A');
    });

    it('drops <script> with its content, and keeps the markup around it', () => {
        const root = rendered('<b>before</b><script>window.__k13=1</script><strong>after</strong>');
        expect(root.querySelector('script')).toBeNull();
        expect(root.textContent).not.toContain('window.__k13');
        expect(root.querySelector('b')?.textContent).toBe('before');
        expect(root.querySelector('strong')?.textContent).toBe('after');
    });

    it('drops javascript: URLs in any spelling, and keeps the link text', () => {
        const root = rendered('<a href="javascript:alert(1)">one</a><a href="JaVaScRiPt:alert(2)">two</a><a href=" javascript:alert(3)">three</a>');
        const hrefs = [...root.querySelectorAll('a')].map((a) => a.getAttribute('href') ?? '');
        expect(hrefs.filter((href) => /^\s*javascript:/i.test(href))).toEqual([]);
        expect(root.textContent).toBe('onetwothree');
    });

    it('turns the toast payload of the stored-XSS report into the harmless part only', () => {
        const root = rendered('<img src=x onerror="window.__k13Toast=1"><span class="emoji-flag">🇮🇹</span> Saved');
        expect(withHandlers(root)).toEqual([]);
        expect(root.querySelector('span.emoji-flag')?.textContent).toBe('🇮🇹');
        expect(root.textContent).toContain('Saved');
    });
});

describe('sanitizeHtml — keeps what the app puts in its own messages', () => {
    it('keeps formatting: <br>, <strong>, <b>, <code> and inline style', () => {
        const root = rendered('<strong>Total</strong><br><b>bold</b> <code>ISIN</code> <span style="color: rgb(220, 38, 38); font-weight: 600">−12.00</span>');
        expect(root.querySelector('strong')?.textContent).toBe('Total');
        expect(root.querySelector('br')).not.toBeNull();
        expect(root.querySelector('b')?.textContent).toBe('bold');
        expect(root.querySelector('code')?.textContent).toBe('ISIN');
        const styled = root.querySelector('span');
        expect(styled?.getAttribute('style')).toContain('color');
        expect(styled?.getAttribute('style')).toContain('font-weight');
    });

    it('keeps an inline lucide-like <svg> with its geometry', () => {
        const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3 4 7l4 4"></path><line x1="12" y1="20" x2="12" y2="10"></line></svg>';
        const root = rendered(svg);
        const el = root.querySelector('svg');
        expect(el).not.toBeNull();
        expect(el?.getAttribute('viewBox')).toBe('0 0 24 24');
        expect(el?.getAttribute('stroke')).toBe('currentColor');
        expect(root.querySelector('path')?.getAttribute('d')).toBe('M8 3 4 7l4 4');
        expect(root.querySelector('line')?.getAttribute('x1')).toBe('12');
    });

    it("keeps KaTeX's span markup: classes, aria-hidden and inline style", () => {
        const katex = '<span class="katex"><span class="katex-html" aria-hidden="true"><span class="base"><span class="strut" style="height:0.6944em;"></span><span class="mord mathnormal">x</span><span class="mbin">+</span><span class="mord">1</span></span></span></span>';
        const root = rendered(katex);
        expect(root.querySelector('span.katex > span.katex-html')?.getAttribute('aria-hidden')).toBe('true');
        expect(root.querySelector('span.strut')?.getAttribute('style')).toContain('height');
        expect(root.querySelector('span.mord.mathnormal')?.textContent).toBe('x');
        expect(root.textContent).toBe('x+1');
    });

    it("keeps the app's own links: a relative href and their data-testid", () => {
        // `entityDetailLinkHtml` puts these in toasts, and ToastContainer.test.ts clicks them by testid.
        const root = rendered('<a href="/assets/42" data-testid="toast-asset-link" class="underline">Owned asset</a>');
        const link = root.querySelector('a');
        expect(link?.getAttribute('href')).toBe('/assets/42');
        expect(link?.getAttribute('data-testid')).toBe('toast-asset-link');
        expect(link?.textContent).toBe('Owned asset');
    });

    it('leaves plain text alone, and keeps escaped text escaped', () => {
        expect(sanitizeHtml('Saved 3 transactions')).toBe('Saved 3 transactions');
        const root = rendered('&lt;img src=x onerror=alert(1)&gt; stays text');
        expect(root.querySelector('img')).toBeNull();
        expect(root.textContent).toBe('<img src=x onerror=alert(1)> stays text');
    });
});
