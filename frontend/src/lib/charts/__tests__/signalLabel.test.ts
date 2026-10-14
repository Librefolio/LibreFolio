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
import {signalLabelToHtml, type SignalLabelInfo} from '../signalLabel';

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

// =============================================================================
// K step 16, item 1 — `{inline: true}`: the enclosing box decides where the label ends
// =============================================================================

/**
 * The price chart's tooltip now fits each row into the chart's width: the row's label item shrinks and ellipsizes
 * (`buildFittedTooltipRow`, `echartsTooltipHelpers.ts`). The label text span built here carries a box of its own —
 * `display:inline-block;max-width:calc(100% - 40px);min-width:0;flex-shrink:1` and its own ellipsis — and inside a
 * label item sized to its content that `calc()` resolves 5 px short of the name: the crown and the icon take 35 of
 * the 40 px it reserves, so the name ends in an ellipsis with room to spare (a static replica of the cure's markup
 * in Chromium, 06/10: 173 px of name in 168).
 *
 * So a third, optional parameter. With `{inline: true}` the text span is a plain inline box — no max-width,
 * min-width, flex-shrink or ellipsis of its own — and the enclosing box decides where the text ends. Nothing else
 * moves: crown, dot, icon and suffix, the text and its title, and the escaping the K13 tests above hold (their
 * hostile labels are reused below). Without the option, or with `{inline: false}`, the output is today's byte for
 * byte: the measure table and every other caller keep their own ellipsis. Today's bytes were captured from the
 * implementation as it stood before the option (06/10).
 */
describe('signalLabelToHtml — {inline: true}: the enclosing box decides where the label ends (K step 16, item 1)', () => {
    const CASES: Array<{why: string; info: SignalLabelInfo; truncateAt: number | undefined; today: string}> = [
        {
            why: 'crown, icon and suffix, cut at 15',
            info: {label: 'Bitcoin', iconUrl: '/icons/btc.png', isCrown: true, suffix: '<span data-testid="label-suffix">🇪🇺 EUR</span>'},
            truncateAt: 15,
            today: '<span style="display:inline-block;width:16px;text-align:center;margin-right:2px;vertical-align:middle">👑</span><img src="/icons/btc.png" alt="" style="width:14px;height:14px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:3px;display:inline-block;" /><span style="vertical-align:middle;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:inline-block;max-width:calc(100% - 40px);min-width:0;flex-shrink:1" title="Bitcoin">Bitcoin</span><span style="vertical-align:middle;white-space:nowrap;flex-shrink:0"><span data-testid="label-suffix">🇪🇺 EUR</span></span>',
        },
        {
            why: 'colour dot, no icon, no cut',
            info: {label: 'EUR/USD', color: '#3b82f6'},
            truncateAt: undefined,
            today: '<span style="display:inline-block;width:16px;text-align:center;margin-right:2px;vertical-align:middle;line-height:0"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#3b82f6;"></span></span><span style="vertical-align:middle;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:inline-block;max-width:calc(100% - 40px);min-width:0;flex-shrink:1" title="EUR/USD">EUR/USD</span>',
        },
        {
            why: 'an ampersand at the cut, cut at 15',
            info: {label: 'AAAAAAAAAAAAA&BB'},
            truncateAt: 15,
            today: '<span style="vertical-align:middle;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:inline-block;max-width:calc(100% - 40px);min-width:0;flex-shrink:1" title="AAAAAAAAAAAAA&amp;BB">AAAAAAAAAAAAA&amp;B…</span>',
        },
    ];

    /** The label text span of `html`: the one element with a title. */
    function textSpan(html: string): HTMLElement {
        const span = labelSpan(parse(html));
        if (!(span instanceof HTMLElement)) throw new Error(`no label text span (span[title]) in: ${html}`);
        return span;
    }

    /** `html` with its label text span replaced by a marker: everything that must not move when only that span changes. */
    function aroundTheLabel(html: string): string {
        const template = document.createElement('template');
        template.innerHTML = html;
        const span = template.content.querySelector('span[title]');
        if (!span) throw new Error(`no label text span (span[title]) in: ${html}`);
        span.replaceWith('⟨label⟩');
        return template.innerHTML;
    }

    it.each(CASES)('with {inline: true} the label text is a plain inline box — no max-width, min-width, flex-shrink or ellipsis of its own — $why', ({info, truncateAt}) => {
        const {style} = textSpan(signalLabelToHtml(info, truncateAt, {inline: true}));
        expect.soft(['', 'inline'], `an inline box, not display "${style.display}"`).toContain(style.display);
        expect.soft(style.maxWidth, 'no max-width of its own').toBe('');
        expect.soft(style.minWidth, 'no min-width of its own').toBe('');
        expect.soft(style.flexShrink, 'no flex-shrink of its own').toBe('');
        expect.soft(style.textOverflow, 'no ellipsis of its own').toBe('');
    });

    it.each(CASES)('with {inline: true} nothing else moves: crown, dot, icon and suffix, the text and its title — $why', ({info, truncateAt}) => {
        const today = signalLabelToHtml(info, truncateAt);
        const inline = signalLabelToHtml(info, truncateAt, {inline: true});
        expect(aroundTheLabel(inline), 'crown, dot, icon and suffix: the same markup').toBe(aroundTheLabel(today));
        expect(textSpan(inline).textContent, 'the same text, cut the same way').toBe(textSpan(today).textContent);
        expect(textSpan(inline).getAttribute('title'), 'the same title').toBe(textSpan(today).getAttribute('title'));
    });

    it.each([
        {label: '<img src=x onerror="window.__k13=1">', why: 'markup'},
        {label: 'x" onmouseover="alert(1)', why: 'a quote'},
    ])('with {inline: true} the label is still text — the K13 hostile label made of $why stays characters, in the text and in the title', ({label}) => {
        const html = signalLabelToHtml({label}, undefined, {inline: true});
        expect.soft(html, 'the label must not reach the output as raw markup').not.toContain('<img src=x');
        const out = parse(html);
        expect.soft(out.querySelectorAll('img').length, 'the label must not become an <img>').toBe(0);
        expect.soft(handlerAttributes(out), 'the label must not add a handler').toEqual([]);
        expect.soft(out.textContent, 'the label must be shown as the characters it is made of').toBe(label);
        expect.soft(labelSpan(out)?.getAttribute('title'), 'the title must be the literal label').toBe(label);
    });

    it.each(CASES)("without the option, or with {inline: false}, the output is today's byte for byte — $why", ({info, truncateAt, today}) => {
        expect(signalLabelToHtml(info, truncateAt), 'no options').toBe(today);
        expect(signalLabelToHtml(info, truncateAt, undefined), 'options undefined').toBe(today);
        expect(signalLabelToHtml(info, truncateAt, {inline: false}), '{inline: false}').toBe(today);
    });
});
