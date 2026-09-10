import {describe, expect, expectTypeOf, it} from 'vitest';
import {entityDetailLinkHtml} from '../entityLink';

type Target = Parameters<typeof entityDetailLinkHtml>[0];

/**
 * Node-only tests: this helper constructs markup, not DOM. Only the two internal
 * detail routes are accepted, and the label is always text, never supplied HTML.
 */
describe('entityDetailLinkHtml', () => {
    it('accepts only typed asset and FX destinations, not arbitrary URLs', () => {
        expectTypeOf<Target>().toEqualTypeOf<{kind: 'asset'; id: number} | {kind: 'fx'; slug: string}>();
    });

    it.each([1, 42, Number.MAX_SAFE_INTEGER])('links positive safe asset ID %s to its detail route', (id) => {
        const html = entityDetailLinkHtml({kind: 'asset', id}, 'Owned asset');

        expect(html).toMatch(/^<a\b/);
        expect(html).toContain(`href="/assets/${id}"`);
        expect(html).toContain('data-testid="toast-asset-link"');
        expect(html).toMatch(/>Owned asset<\/a>$/);
        expect(html.match(/\bhref=/g)).toHaveLength(1);
    });

    it.each([0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.MAX_SAFE_INTEGER + 1])('rejects invalid asset ID %s', (id) => {
        expect(() => entityDetailLinkHtml({kind: 'asset', id}, 'Owned asset')).toThrow('Asset detail links require a positive integer ID');
    });

    it.each(['JPY-RON', 'EUR-USD', 'XAU-USD'])('links uppercase pair %s to its detail route', (slug) => {
        const html = entityDetailLinkHtml({kind: 'fx', slug}, 'Pair label');

        expect(html).toMatch(/^<a\b/);
        expect(html).toContain(`href="/fx/${slug}"`);
        expect(html).toContain('data-testid="toast-fx-link"');
        expect(html).toMatch(/>Pair label<\/a>$/);
        expect(html.match(/\bhref=/g)).toHaveLength(1);
    });

    it.each([
        '',
        'JPY',
        'jpy-RON',
        'JPY-ron',
        'JP-RON',
        'JPYY-RON',
        'JP1-RON',
        'JPY/RON',
        'JPY-RON-USD',
        ' JPY-RON',
        'JPY-RON ',
        'JPY-RON\n',
        'JPY-RON\r',
        '../JPY-RON',
        '/fx/JPY-RON',
        'https://example.invalid/JPY-RON',
        'javascript:alert(1)',
        'JPY-RON?redirect=https://example.invalid',
        'JPY-RON" onclick="alert(1)',
    ])('rejects malformed or URL-like FX slug %j', (slug) => {
        expect(() => entityDetailLinkHtml({kind: 'fx', slug}, 'Pair label')).toThrow('FX detail links require an AAA-BBB pair slug');
    });

    const destinations: Target[] = [
        {kind: 'asset', id: 42},
        {kind: 'fx', slug: 'JPY-RON'},
    ];

    it.each(destinations)('escapes hostile labels exactly once for $kind links', (target) => {
        const label = `<img src=x onerror="alert('x')"> & <script>bad()</script>`;
        const escaped = '&lt;img src=x onerror=&quot;alert(&#39;x&#39;)&quot;&gt; &amp; &lt;script&gt;bad()&lt;/script&gt;';
        const html = entityDetailLinkHtml(target, label);

        expect(html).toContain(`>${escaped}</a>`);
        expect(html).not.toContain('<img');
        expect(html).not.toContain('<script');
        expect(html).not.toContain('&amp;lt;');
        expect(html.match(/<a\b/g)).toHaveLength(1);
    });

    it.each(destinations)('keeps URL-shaped labels as text without replacing the $kind destination', (target) => {
        const html = entityDetailLinkHtml(target, 'https://example.invalid/?x=1&y=2');
        const href = target.kind === 'asset' ? '/assets/42' : '/fx/JPY-RON';

        expect(html).toContain(`href="${href}"`);
        expect(html).toContain('>https://example.invalid/?x=1&amp;y=2</a>');
        expect(html.match(/\bhref=/g)).toHaveLength(1);
    });

    it.each(destinations)('does not interpret pre-escaped $kind labels as markup', (target) => {
        expect(entityDetailLinkHtml(target, '&lt;b&gt;name&lt;/b&gt;')).toContain('>&amp;lt;b&amp;gt;name&amp;lt;/b&amp;gt;</a>');
    });
});
