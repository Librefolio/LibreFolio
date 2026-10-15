// @vitest-environment jsdom
/**
 * Designer Lab — specialisations (`engine/anchors.ts`): one colour property of the picked element, written as a rule
 * of the cascade layer `lf-designer-lab` for every instance of its component.
 *
 * The layer works only if it is declared before any other layer, so the statement `@layer lf-designer-lab;` must be the
 * first thing in `<head>`; the rules are `!important` inside that layer, scoped to a theme by their `html…` prefix. A
 * selector or value that could break out of the rule is refused, and a selector the browser cannot parse is skipped.
 * The variable overrides of L1 (`engine/vars.ts`) live in a `<style>` of their own, outside the layer: one `!important`
 * rule per variable, on `<html>` and on the theme subtrees of its scope (`.light`, `.dark`), as the role tokens are, the
 * rules for both themes first so that a theme's own value wins on a theme subtree too.
 * jsdom stands in for the page; what is asserted is the text the engine writes, not the cascade (the E2E specs see it).
 */

import {beforeEach, describe, expect, it} from 'vitest';
import {applyElementRules, ELEMENT_STYLE_ID, elementRule, LAB_LAYER} from './engine/anchors';
import {applyVars, OWN_ATTR, VAR_SELECTOR} from './engine/vars';
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

describe('applyVars', () => {
    /** The `<style>` the variable engine writes (its id is the engine's own, not exported). */
    const VARS_STYLE_ID = 'lf-designer-lab-vars';
    const varsStyle = () => document.getElementById(VARS_STYLE_ID);

    const override = (fields: Partial<LabChange> = {}): LabChange => ({id: '', layer: 'css-var', target: '--lf-surface-card', scope: 'both', from: '#f5f5f4', to: '#ffffff', ...fields});

    it('writes each scope with the selectors of the token blocks: `<html>` and the theme subtrees', () => {
        expect(VAR_SELECTOR).toEqual({both: 'html, .light, .dark', light: 'html:not(.dark), .light', dark: 'html.dark, .dark'});
    });

    it('overrides each variable with an important declaration under the selector of its scope, and returns how many', () => {
        expect(applyVars([override({scope: 'both'}), override({scope: 'light', to: '#fafaf9'}), override({scope: 'dark', target: '--color-gray-500', to: 'oklch(70% 0.1 250)'})])).toBe(3);
        expect(varsStyle()?.textContent).toBe(['html, .light, .dark { --lf-surface-card: #ffffff !important; }', 'html:not(.dark), .light { --lf-surface-card: #fafaf9 !important; }', 'html.dark, .dark { --color-gray-500: oklch(70% 0.1 250) !important; }'].join('\n'));
    });

    it('writes the rules for both themes before the theme rules, whatever the order of the changes', () => {
        // On a `.dark` island the dark rule and the rule for both themes match with the same specificity: written later,
        // the theme's own value wins there as it does on `<html>`. Only the text is checked: jsdom has no cascade.
        const changes = [override({scope: 'dark', to: '#0c0a09'}), override({scope: 'both', to: '#ffffff'})];
        expect(applyVars(changes)).toBe(2);
        expect(varsStyle()?.textContent?.split('\n')).toEqual(['html, .light, .dark { --lf-surface-card: #ffffff !important; }', 'html.dark, .dark { --lf-surface-card: #0c0a09 !important; }']);
        // The list of changes it was given keeps its own order.
        expect(changes.map((c) => c.scope)).toEqual(['dark', 'both']);

        expect(applyVars([override({scope: 'light', to: '#fafaf9'}), override({scope: 'both', to: '#ffffff'})])).toBe(2);
        expect(varsStyle()?.textContent?.split('\n')).toEqual(['html, .light, .dark { --lf-surface-card: #ffffff !important; }', 'html:not(.dark), .light { --lf-surface-card: #fafaf9 !important; }']);
    });

    it('keeps the order of the changes among the rules for both themes, and among the rules of one theme', () => {
        const changes = [override({scope: 'dark', target: '--a', to: '#000001'}), override({scope: 'both', target: '--b', to: '#000002'}), override({scope: 'dark', target: '--c', to: '#000003'}), override({scope: 'both', target: '--d', to: '#000004'})];
        expect(applyVars(changes)).toBe(4);
        expect(varsStyle()?.textContent?.split('\n')).toEqual(['html, .light, .dark { --b: #000002 !important; }', 'html, .light, .dark { --d: #000004 !important; }', 'html.dark, .dark { --a: #000001 !important; }', 'html.dark, .dark { --c: #000003 !important; }']);
    });

    it('is one <style> of <head>, marked as the Lab’s own, rewritten on every apply', () => {
        applyVars([override(), override({scope: 'dark', to: '#0c0a09'})]);
        expect(applyVars([override({to: 'var(--lf-surface-panel)'})])).toBe(1);
        const style = varsStyle();
        expect(style?.tagName).toBe('STYLE');
        expect(style?.parentElement).toBe(document.head);
        expect(style?.hasAttribute(OWN_ATTR)).toBe(true);
        expect(document.querySelectorAll(`#${VARS_STYLE_ID}`)).toHaveLength(1);
        expect(style?.textContent).toBe('html, .light, .dark { --lf-surface-card: var(--lf-surface-panel) !important; }');
        // The app's own stylesheet is left as it was.
        expect(document.getElementById('app-style')?.textContent).toBe('p { color: #111827; }');
    });

    it('skips a target that is not a custom property and a value that could break out of the rule, counting only what it wrote', () => {
        const changes = [override({target: '#64748b'}), override({target: 'color'}), override({target: '--x;y'}), override(), override({target: '--color-gray-500', to: 'red; background: url(x)'}), override({target: '--color-gray-500', to: 'red }'}), override({target: '--color-gray-500', to: ''})];
        expect(applyVars(changes)).toBe(1);
        expect(varsStyle()?.textContent).toBe('html, .light, .dark { --lf-surface-card: #ffffff !important; }');
    });

    it('removes its <style> once no override is left, and writes none when every change is skipped', () => {
        applyVars([override()]);
        expect(applyVars([])).toBe(0);
        expect(varsStyle()).toBeNull();
        expect(applyVars([override({to: 'red; x: y'}), override({target: 'color'})])).toBe(0);
        expect(varsStyle()).toBeNull();
        expect(document.getElementById('app-style')).not.toBeNull();
    });
});
