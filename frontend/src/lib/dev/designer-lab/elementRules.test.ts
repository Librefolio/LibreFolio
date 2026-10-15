// @vitest-environment jsdom
/**
 * Designer Lab — specialisations (`engine/anchors.ts`): one colour property of the picked element, written as a rule
 * of the cascade layer `lf-designer-lab` for every instance of its component.
 *
 * The layer works only if it is declared before any other layer, so the statement `@layer lf-designer-lab;` must be the
 * first thing in `<head>`; the rules are `!important` inside that layer, scoped to a theme by their `html…` prefix. A
 * selector or value that could break out of the rule is refused, and a selector the browser cannot parse is skipped.
 * jsdom stands in for the page; what is asserted is the text the engine writes, not the cascade (the E2E specs see it).
 */

import {beforeEach, describe, expect, it} from 'vitest';
import {applyElementRules, ELEMENT_STYLE_ID, elementRule, LAB_LAYER} from './engine/anchors';
import {OWN_ATTR} from './engine/vars';
import type {LabChange} from './types';

const TH = '[data-testid="tx-table"] > div > table > thead > tr > th';

const specialise = (fields: Partial<LabChange> = {}): LabChange => ({id: '', layer: 'element', target: TH, scope: 'both', from: 'rgb(100, 116, 139)', to: '#dc2626', property: 'color', ...fields});

/** The `<style>` elements of `<head>` that hold the Lab's layer. */
const labStyles = () => Array.from(document.head.querySelectorAll('style')).filter((s) => (s.textContent ?? '').includes(LAB_LAYER));

beforeEach(() => {
    document.head.innerHTML = '<meta charset="utf-8"><style id="app-style">p { color: #111827; }</style>';
});

describe('elementRule', () => {
    it('scopes the rule to a theme with its `html` prefix, inside `:is()`, as an important declaration', () => {
        expect(elementRule(specialise({scope: 'both'}))).toBe(`html :is(${TH}) { color: #dc2626 !important; }`);
        expect(elementRule(specialise({scope: 'light'}))).toBe(`html:not(.dark) :is(${TH}) { color: #dc2626 !important; }`);
        expect(elementRule(specialise({scope: 'dark'}))).toBe(`html.dark :is(${TH}) { color: #dc2626 !important; }`);
    });

    it('writes any one-colour property, `border-color` for the four sides, and a selector with escaped classes', () => {
        expect(elementRule(specialise({property: 'border-color', to: 'oklch(70% 0.1 250)'}))).toBe(`html :is(${TH}) { border-color: oklch(70% 0.1 250) !important; }`);
        expect(elementRule(specialise({property: 'fill', to: 'var(--theme-accent)'}))).toBe(`html :is(${TH}) { fill: var(--theme-accent) !important; }`);
        const escaped = '[data-testid="kpi-card"] > p.dark\\:text-gray-400';
        expect(elementRule(specialise({target: escaped}))).toBe(`html :is(${escaped}) { color: #dc2626 !important; }`);
    });

    it('writes nothing for a chart colour, a property it does not specialise, or another layer', () => {
        expect(elementRule(specialise({property: 'chart', colorKey: '#10b981'}))).toBeNull();
        expect(elementRule(specialise({property: 'box-shadow'}))).toBeNull();
        expect(elementRule(specialise({property: 'background'}))).toBeNull();
        expect(elementRule(specialise({property: undefined}))).toBeNull();
        expect(elementRule(specialise({layer: 'css-var', target: '--color-gray-500'}))).toBeNull();
    });

    it.each([
        ['a block', `${TH} { color: red }`],
        ['a closing brace', `${TH} }`],
        ['a semicolon', `${TH};`],
        ['a new line', `${TH}\n td`],
        ['a comment', `${TH} /* x */`],
        ['a tag delimiter', '</style><script>'],
        ['nothing', ''],
        ['more than 600 characters', `${'div > '.repeat(100)}th`],
    ])('refuses a selector with %s', (_label, target) => {
        expect(elementRule(specialise({target}))).toBeNull();
    });

    it.each([
        ['a second declaration', 'red; background: url(x)'],
        ['a closing brace', 'red }'],
        ['quotes', '"red"'],
        ['a backslash', 'r\\65 d'],
        ['a comment', 'red /* x */'],
        ['nothing', ''],
        ['more than 200 characters', `rgb(${'1 '.repeat(100)})`],
    ])('refuses a value with %s', (_label, to) => {
        expect(elementRule(specialise({to}))).toBeNull();
    });
});

describe('applyElementRules', () => {
    it('declares the layer first in <head>, then writes the rules inside it, and returns how many', () => {
        const rules = [specialise({scope: 'light'}), specialise({scope: 'dark', property: 'background-color', to: '#1e293b'})];
        expect(applyElementRules(rules)).toBe(2);

        const first = document.head.firstElementChild;
        expect(first?.tagName).toBe('STYLE');
        expect(first?.textContent).toBe(`@layer ${LAB_LAYER};`);
        expect(first?.hasAttribute(OWN_ATTR)).toBe(true);

        const style = document.getElementById(ELEMENT_STYLE_ID);
        expect(style?.parentElement).toBe(document.head);
        expect(style?.hasAttribute(OWN_ATTR)).toBe(true);
        expect(style?.textContent).toBe(`@layer ${LAB_LAYER} {\n${elementRule(rules[0])}\n${elementRule(rules[1])}\n}`);
        // The app's own stylesheet comes after the layer statement and is left as it was.
        expect(document.getElementById('app-style')?.textContent).toBe('p { color: #111827; }');
    });

    it('rewrites the same two elements on every apply, never a second copy', () => {
        applyElementRules([specialise(), specialise({property: 'border-color'})]);
        expect(applyElementRules([specialise({to: '#2563eb'})])).toBe(1);
        expect(labStyles()).toHaveLength(2);
        expect(document.head.firstElementChild?.textContent).toBe(`@layer ${LAB_LAYER};`);
        expect(document.getElementById(ELEMENT_STYLE_ID)?.textContent).toBe(`@layer ${LAB_LAYER} {\nhtml :is(${TH}) { color: #2563eb !important; }\n}`);
    });

    it('removes the statement and the rules once no specialisation is left', () => {
        applyElementRules([specialise()]);
        expect(applyElementRules([])).toBe(0);
        expect(labStyles()).toEqual([]);
        expect(document.getElementById(ELEMENT_STYLE_ID)).toBeNull();
        expect(document.getElementById('app-style')).not.toBeNull();
    });

    it('skips a selector the browser cannot parse, and a chart colour, which is not a CSS rule', () => {
        expect(applyElementRules([specialise({target: 'th['}), specialise(), specialise({property: 'chart', colorKey: '#10b981', target: '[data-testid="growth-chart"]'})])).toBe(1);
        expect(document.getElementById(ELEMENT_STYLE_ID)?.textContent).toBe(`@layer ${LAB_LAYER} {\n${elementRule(specialise())}\n}`);

        expect(applyElementRules([specialise({target: 'th['})])).toBe(0);
        expect(labStyles()).toEqual([]);
    });
});
