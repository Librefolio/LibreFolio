// @vitest-environment jsdom
/**
 * labelShrink — the scale of labels that share a row (toolbar-width-sweep, 25/11/2026).
 *
 * jsdom lays nothing out: a label's width is stubbed as 10 px per character at its natural size, and every other number
 * is the test's own. What is pinned here:
 * - `rowShrinkRatio` is the arithmetic alone;
 * - one-word labels — whose own item gives them exactly their own width, so their per-label ratio is 1 — are shrunk by
 *   the row, and without the row they are not (the defect);
 * - the per-label ratio still wins when it is the smaller one, the floor still holds, and a row that fits leaves the
 *   labels untouched (they grow back).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {applyLinearShrink, measureNaturalWidth, rowShrinkRatio, type ShrinkTarget} from './labelShrink';

const PX_PER_CHARACTER = 10;
const NATURAL_PX = 16; // jsdom’s computed font size: what the shrink reads as the natural one

beforeEach(() => {
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
        // The width the text takes at the element's own size: the clone of the measuring pass is at the natural one.
        const px = parseFloat(this.style.fontSize) || NATURAL_PX;
        const width = ((this.textContent ?? '').length * PX_PER_CHARACTER * px) / NATURAL_PX;
        return {width, height: 16, top: 0, left: 0, right: width, bottom: 16, x: 0, y: 0, toJSON() {}} as DOMRect;
    });
});

afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
});

function label(text: string): HTMLElement {
    const element = document.createElement('span');
    element.style.lineHeight = '16px';
    element.textContent = text;
    document.body.appendChild(element);
    return element;
}

/** A label whose item gives it exactly its own natural width: what `min-width: auto` does to a one-word tab. */
function heldAtItsWidth(element: HTMLElement): ShrinkTarget {
    return {label: element, availableWidth: (element.textContent ?? '').length * PX_PER_CHARACTER};
}

describe('rowShrinkRatio', () => {
    it('is the room the row leaves the labels, over their natural widths', () => {
        expect(rowShrinkRatio([100, 200], {width: 400, fixedWidth: 100})).toBeCloseTo(1);
        expect(rowShrinkRatio([100, 200], {width: 340, fixedWidth: 100})).toBeCloseTo(0.8);
        expect(rowShrinkRatio([100, 200], {width: 100, fixedWidth: 100})).toBeCloseTo(0);
    });

    it('a row with no label has nothing to shrink', () => {
        expect(rowShrinkRatio([], {width: 100, fixedWidth: 40})).toBe(1);
        expect(rowShrinkRatio([0, 0], {width: 100, fixedWidth: 40})).toBe(1);
    });
});

describe('applyLinearShrink — labels that share a row', () => {
    it('one-word labels shrink by the row, every one to the same size', () => {
        const words = ['Overview', 'Transactions'].map(label); // 80 px and 120 px
        const scale = applyLinearShrink(words.map(heldAtItsWidth), 0.75, {width: 200, fixedWidth: 40});
        // 160 px of room over 200 px of labels
        expect(scale).toBeCloseTo(0.8);
        for (const word of words) expect(parseFloat(word.style.fontSize)).toBeCloseTo(NATURAL_PX * 0.8);
    });

    it('without the row the same labels never shrink: the defect the row closes', () => {
        const words = ['Overview', 'Transactions'].map(label);
        expect(applyLinearShrink(words.map(heldAtItsWidth), 0.75)).toBe(1);
        for (const word of words) expect(word.style.fontSize).toBe('');
    });

    it('a row that fits leaves the labels at full size, also after they were shrunk (they grow back)', () => {
        const words = ['Overview', 'Transactions'].map(label);
        applyLinearShrink(words.map(heldAtItsWidth), 0.75, {width: 200, fixedWidth: 40});
        expect(applyLinearShrink(words.map(heldAtItsWidth), 0.75, {width: 260, fixedWidth: 40})).toBe(1);
        for (const word of words) expect(word.style.fontSize).toBe('');
    });

    it('stops at the floor, however far the row overflows', () => {
        const words = ['Overview', 'Transactions'].map(label);
        expect(applyLinearShrink(words.map(heldAtItsWidth), 0.75, {width: 60, fixedWidth: 40})).toBe(0.75);
    });

    it('takes the smaller of the two: a label its own item squeezes wins over a row that would hold it', () => {
        const words = ['Overview', 'Transactions'].map(label);
        const targets = [{label: words[0], availableWidth: 72}, heldAtItsWidth(words[1])];
        // 0.9 for the first label; the row alone would leave them whole
        expect(applyLinearShrink(targets, 0.75, {width: 260, fixedWidth: 40})).toBeCloseTo(0.9);
    });
});

describe('measureNaturalWidth', () => {
    it('measures in the font the label has in its own place, not the body’s: a tab’s weight is inherited', () => {
        const tab = document.body.appendChild(document.createElement('div'));
        tab.style.fontWeight = '500';
        tab.style.letterSpacing = '1px';
        const word = label('Overview');
        tab.appendChild(word);
        const measured: Partial<CSSStyleDeclaration>[] = [];
        vi.mocked(HTMLElement.prototype.getBoundingClientRect).mockImplementation(function (this: HTMLElement) {
            measured.push({fontWeight: this.style.fontWeight, letterSpacing: this.style.letterSpacing});
            return {width: 80} as DOMRect;
        });
        expect(measureNaturalWidth(word, NATURAL_PX)).toBe(80);
        expect(measured).toEqual([{fontWeight: '500', letterSpacing: '1px'}]);
        expect(document.body.children, 'the clone is gone').toHaveLength(1);
    });
});
