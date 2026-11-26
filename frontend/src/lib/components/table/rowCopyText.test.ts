// @vitest-environment jsdom
/**
 * rowCopyText — what «Copy cell» and «Copy row» of a finger's row menu copy (85 BTN-0): the text the screen shows, read
 * from the DOM, never from the data. A screen-reader-only text and an `aria-hidden` subtree are left out, whitespace
 * collapses to one space, a row is its data cells joined by tabs, and a value the privacy mode masks stays masked.
 *
 * jsdom has no `checkVisibility` and no CSS: an element hidden by a stylesheet is the browser's case (the E2E's), here
 * every element counts unless it is `.sr-only` or `aria-hidden`.
 */
import {afterEach, describe, expect, it} from 'vitest';
import {cellScreenText, rowScreenText} from './rowCopyText';

function cell(html: string): HTMLTableCellElement {
    const table = document.body.appendChild(document.createElement('table'));
    const tr = table.insertRow();
    const td = tr.insertCell();
    td.className = 'td-data';
    td.innerHTML = html;
    return td;
}

afterEach(() => {
    document.body.innerHTML = '';
});

describe('cellScreenText', () => {
    it('a plain cell', () => {
        expect(cellScreenText(cell('Apple Inc.'))).toBe('Apple Inc.');
    });

    it('nested spans read in order, as one text', () => {
        expect(cellScreenText(cell('<span>€</span><span><b>1</b>,234.<i>50</i></span>'))).toBe('€1,234.50');
    });

    it('a screen-reader-only child is left out', () => {
        expect(cellScreenText(cell('<span>AAPL</span><span class="sr-only"> (Apple Inc., stock)</span>'))).toBe('AAPL');
    });

    it('an aria-hidden subtree is left out', () => {
        expect(cellScreenText(cell('<span aria-hidden="true"><svg><text>icon</text></svg>★</span> Favourite'))).toBe('Favourite');
    });

    it('whitespace and new lines collapse to one space, trimmed', () => {
        expect(cellScreenText(cell('\n   Line   one\n\n\tline\ttwo   '))).toBe('Line one line two');
    });

    it('a masked value is copied as shown', () => {
        expect(cellScreenText(cell('<span>€•••</span>'))).toBe('€•••');
        expect(cellScreenText(cell('-••• <span>CHF</span>'))).toBe('-••• CHF');
    });

    it('only the subtree inside the cell decides: an aria-hidden ancestor outside it does not hide it', () => {
        const wrapper = document.body.appendChild(document.createElement('div'));
        wrapper.setAttribute('aria-hidden', 'true');
        const td = cell('Visible');
        wrapper.appendChild(td.closest('table')!);
        expect(cellScreenText(td)).toBe('Visible');
    });
});

describe('cellScreenText — fields give their value, as the screen shows it', () => {
    function withField(html: string, setup?: (td: HTMLTableCellElement) => void): HTMLTableCellElement {
        const td = cell(html);
        setup?.(td);
        return td;
    }

    it('an input gives its current value (what the user typed, not the attribute)', () => {
        const td = withField('<input type="text" value="old" />', (c) => (c.querySelector('input')!.value = 'AAPL'));
        expect(cellScreenText(td)).toBe('AAPL');
    });

    it('a number input gives its value, beside the cell’s own text', () => {
        expect(cellScreenText(withField('<input type="number" value="12.5" /> <span>%</span>'))).toBe('12.5 %');
    });

    it('a password input gives nothing', () => {
        expect(cellScreenText(withField('<span>Key</span><input type="password" value="s3cret" />'))).toBe('Key');
    });

    it('a checkbox and a range give nothing', () => {
        expect(cellScreenText(withField('<input type="checkbox" checked /><input type="range" value="40" />'))).toBe('');
    });

    it('a textarea gives its value, on one line', () => {
        const td = withField('<textarea>first</textarea>', (c) => (c.querySelector('textarea')!.value = 'line one\nline two'));
        expect(cellScreenText(td)).toBe('line one line two');
    });

    it('a select gives only its chosen option, never the others', () => {
        const td = withField('<select><option value="a">Alpha</option><option value="b">Beta</option><option value="c">Gamma</option></select>', (c) => (c.querySelector('select')!.value = 'b'));
        expect(cellScreenText(td)).toBe('Beta');
    });

    it('a field inside a hidden subtree gives nothing', () => {
        expect(cellScreenText(withField('<span>Shown</span><span aria-hidden="true"><input value="ghost" /></span>'))).toBe('Shown');
    });
});

describe('rowScreenText', () => {
    it('joins only the data cells with tabs: the select and actions cells are left out', () => {
        const table = document.body.appendChild(document.createElement('table'));
        const tr = table.insertRow();
        tr.innerHTML =
            '<td class="td-fixed td-select"><button>☐</button></td>' + '<td class="td-data">Apple <span class="sr-only">stock</span></td>' + '<td class="td-data">  €•••  </td>' + '<td class="td-data"><span>12</span> <span>shares</span></td>' + '<td class="td-actions"><button>⋮</button></td>';
        expect(rowScreenText(tr)).toBe('Apple\t€•••\t12 shares');
    });

    it('a row mixing text cells and field cells is tab-joined, each field by its value', () => {
        const table = document.body.appendChild(document.createElement('table'));
        const tr = table.insertRow();
        tr.innerHTML =
            '<td class="td-data">Apple</td>' +
            '<td class="td-data"><input type="text" value="AAPL" /></td>' +
            '<td class="td-data"><select><option>USD</option><option selected>EUR</option></select></td>' +
            '<td class="td-data"><input type="password" value="x" /></td>' +
            '<td class="td-data">12 <span>shares</span></td>';
        expect(rowScreenText(tr)).toBe('Apple\tAAPL\tEUR\t\t12 shares');
    });

    it('takes another selector when given one', () => {
        const table = document.body.appendChild(document.createElement('table'));
        const tr = table.insertRow();
        tr.innerHTML = '<td class="a">1</td><td class="b">2</td><td class="a">3</td>';
        expect(rowScreenText(tr, 'td.a')).toBe('1\t3');
    });
});
