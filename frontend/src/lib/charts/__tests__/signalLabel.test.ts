// @vitest-environment jsdom
/**
 * signalLabelToHtml — a signal label is text, in both places it lands (workstream K, step 13, item 0).
 *
 * `signalLabelToHtml` builds, as raw HTML, the label of the chart tooltips and of the measure table,
 * and its callers hand it asset display names verbatim: `PriceChartFull` (main and overlay tooltip
 * rows), `CandlestickChart` (tooltip header), `MeasurePanel` (summary-table `html` cell). The label
 * reaches the markup twice — as the text of its span and as the span's `title` — so a name must come
 * out as text in both: no element from its `<`, no attribute from its `"`. An asset named
 * `<img src=x onerror=…>` otherwise runs on the asset detail chart and in the measure table.
 *
 * `htmlInterpolation.gate.test.ts` does not see this site: `label` is not one of its text-field
 * suffixes, by design, because most labels are bundled translations. This file is what holds it.
 *
 * Truncation is the subtle half. `truncateAt` shortens the tooltip label; it must cut the RAW label
 * and escape the cut. Escaping first and cutting after slices through an entity (`&amp;` → `&am…`);
 * not escaping at all lets a cut `<b` open a tag.
 *
 * Assertions read the parsed output — a `<template>` holds it inert, nothing runs or loads — the way
 * the tooltip and the table cell render it: what reaches the DOM is the contract.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action
 * `core-unit`) next to the other `src/lib/charts` tests; the jsdom environment is per file.
 */
import {describe, expect, it} from 'vitest';
import {signalLabelToHtml} from '../signalLabel';

function parse(html: string): DocumentFragment {
    const template = document.createElement('template');
    template.innerHTML = html;
    return template.content;
}

/** The label span: the one element of the output that carries a `title`. */
const labelSpan = (fragment: DocumentFragment): Element | null => fragment.querySelector('span[title]');

const handlerAttributes = (fragment: DocumentFragment): string[] =>
    [...fragment.querySelectorAll('*')].flatMap((el) =>
        el
            .getAttributeNames()
            .filter((name) => name.toLowerCase().startsWith('on'))
            .map((name) => `<${el.tagName.toLowerCase()} ${name}>`),
    );

describe('signalLabelToHtml — the label is text (K step 13, item 0)', () => {
    it('shows a markup label as its characters: no element, no handler, the same title', () => {
        const label = '<img src=x onerror="window.__k13=1">';
        const html = signalLabelToHtml({label});
        expect.soft(html, 'the label must not reach the output as raw markup').not.toContain('<img src=x');

        const out = parse(html);
        expect.soft(out.querySelectorAll('img').length, 'the label must not become an <img>').toBe(0);
        expect.soft(handlerAttributes(out), 'the label must not add a handler').toEqual([]);
        expect.soft(out.textContent, 'the label must be shown as the characters it is made of').toBe(label);
        expect.soft(labelSpan(out)?.getAttribute('title'), 'the title must be the literal label').toBe(label);
    });

    it('keeps a quote of the label inside the title attribute', () => {
        const label = 'x" onmouseover="alert(1)';
        const out = parse(signalLabelToHtml({label}));
        const span = labelSpan(out);
        expect(span, 'the label span must exist').not.toBeNull();

        expect.soft(span?.getAttribute('title'), 'the title must be exactly the literal label').toBe(label);
        expect.soft(span?.hasAttribute('onmouseover'), 'the label must not open an attribute of its own').toBe(false);
        expect.soft(handlerAttributes(out)).toEqual([]);
        expect.soft(out.textContent).toBe(label);
    });

    it.each([
        {label: 'AAAAAAAAAAAAA&BB', why: 'an ampersand at the cut (escape-then-cut prints &am…)'},
        {label: 'AAAAAAAAAAAAA<b>BB', why: 'markup at the cut (no escaping opens a tag)'},
    ])('cuts the raw label, then escapes the cut — $why', ({label}) => {
        const n = 15;
        const out = parse(signalLabelToHtml({label}, n));
        expect.soft(out.textContent, 'the visible text is the first n characters of the raw label, then an ellipsis').toBe(label.slice(0, n) + '…');
        expect.soft(labelSpan(out)?.getAttribute('title'), 'the title keeps the whole label').toBe(label);
    });

    it('renders a normal label unchanged, and keeps the markup the renderer itself adds', () => {
        const out = parse(signalLabelToHtml({label: 'Bitcoin', iconUrl: '/icons/btc.png', isCrown: true, suffix: '<span data-testid="label-suffix">🇪🇺 EUR</span>'}, 15));
        expect(labelSpan(out)?.textContent).toBe('Bitcoin');
        expect(labelSpan(out)?.getAttribute('title')).toBe('Bitcoin');
        expect(out.querySelector('img')?.getAttribute('src')).toBe('/icons/btc.png');
        // The suffix is markup by contract (a currency badge): it must stay an element.
        expect(out.querySelector('[data-testid="label-suffix"]')?.textContent).toBe('🇪🇺 EUR');
        expect(out.textContent).toBe('👑Bitcoin🇪🇺 EUR');
    });
});
