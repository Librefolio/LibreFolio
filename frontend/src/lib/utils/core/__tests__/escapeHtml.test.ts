import {describe, expect, it} from 'vitest';
import {escapeHtml} from '../escapeHtml';

/**
 * The contract is narrow but load-bearing: this is the only thing standing
 * between provider-supplied names and the raw HTML we hand to ECharts tooltips
 * and to `{@html}` cells. The cases below pin the five substitutions, the order
 * they have to happen in, and the fact that the function is a pure string
 * transform with no opinion about its input beyond the type.
 */
describe('escapeHtml', () => {
    it.each([
        ['&', '&amp;'],
        ['<', '&lt;'],
        ['>', '&gt;'],
        ['"', '&quot;'],
        ["'", '&#39;'],
    ])('escapes %s', (input, expected) => {
        expect(escapeHtml(input)).toBe(expected);
    });

    it('escapes every entity in one pass', () => {
        expect(escapeHtml(`&<>"'`)).toBe('&amp;&lt;&gt;&quot;&#39;');
    });

    it('escapes the ampersand first, so the other entities are not double-escaped', () => {
        // The classic ordering bug: replace `<` before `&` and the `&` of the
        // freshly written `&lt;` gets escaped again, yielding `&amp;lt;`, which
        // renders as the literal text `&lt;` instead of `<`.
        expect(escapeHtml('<')).toBe('&lt;');
        expect(escapeHtml('a < b & c')).toBe('a &lt; b &amp; c');
    });

    it('returns the empty string unchanged', () => {
        expect(escapeHtml('')).toBe('');
    });

    it('leaves a string with nothing to escape untouched', () => {
        const plain = 'Vanguard FTSE All-World UCITS ETF (VWCE) 12.34 EUR';
        expect(escapeHtml(plain)).toBe(plain);
    });

    it('neutralises a script tag rather than merely stripping it', () => {
        // Nothing is removed — the point is that the result can no longer open
        // an element, so it renders as visible text instead of executing.
        const payload = '<script>alert(1)</script>';
        const escaped = escapeHtml(payload);
        expect(escaped).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
        expect(escaped).not.toContain('<');
    });

    it('closes the attribute-injection route for both quoting styles', () => {
        // A name like this is what turns `title="${name}"` into an onerror sink.
        // Both quote characters must go, because the function cannot see which
        // one its call site used.
        const escaped = escapeHtml(`" onmouseover="alert(1)`);
        expect(escaped).not.toContain('"');
        expect(escapeHtml(`' onmouseover='alert(1)`)).not.toContain("'");
    });

    it('escapes every occurrence, not just the first', () => {
        expect(escapeHtml('a&b&c')).toBe('a&amp;b&amp;c');
    });

    it('is not idempotent, so callers must escape exactly once', () => {
        // Documented rather than fixed: making it idempotent would mean parsing
        // entities, and a name that genuinely contains "&amp;" would then be
        // rendered as "&". Escaping twice is a call-site bug, not one this
        // function can absorb.
        expect(escapeHtml(escapeHtml('&'))).toBe('&amp;amp;');
    });
});
