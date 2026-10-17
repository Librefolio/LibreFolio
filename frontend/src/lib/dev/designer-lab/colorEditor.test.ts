// @vitest-environment jsdom
/**
 * Designer Lab — the opacity slider of the colour editor (`ColorEditor.svelte`, workstream L).
 *
 * The role tokens that carry an opacity are written `color-mix(in <space>, <base> p%, transparent)`: the backdrop, the
 * shadow roles, the selected tint over the focus role. The editor used to refuse that form (no sliders, Apply off), and
 * its colour controls forced the alpha to 1. Now it resolves the mix, shows the share on an A slider (`lab-editor-a`:
 * not `lab-editor-alpha`, which is the «Translucent variants too» checkbox of the literal layers), changes the
 * percentage in place, and its colour controls — L/C/H, the sRGB input, the variable snap — keep the opacity: a mix at
 * 0% too, since only the slider moves a share, but not a fully transparent literal, which holds no colour to keep it
 * for (a colour picked there comes in opaque). A mix in a space CSS does not know is no colour at all.
 *
 * The catalogue is synthetic and carries only what the editor reads. Every colour is made up by the test and nothing
 * reads `tokens.css`: the role names are the real ones, their values are not. The editor reads variables as computed
 * on `<html>`, so a variable it must resolve is set there (jsdom answers custom properties on `<html>`), and the test
 * where it is missing is the control that proves it is read. Assertions go through test ids and the values the test
 * passed in, never through the Lab's labels.
 *
 * The last block is the editor of a chart category (`category`, contract C1–C4 with DV): it starts from the value the
 * tables write for the scope, lists the category's line in each theme, offers no translucent variants (a category is
 * edited by key, not by value), and a chart colour that is also a category's colour warns which categories editing the
 * value reaches. Its keys and values are made up too.
 */

import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '$test/component';
import ColorEditor from './ColorEditor.svelte';
import {parseColor, rgbaToOklch, type Rgba} from './color.js';
import {changeId, emptyState, upsertChange} from './store';
import type {CatalogLiteral, CatalogVar, ColorCatalog, LabChange, LabSelection, LabState, Scope} from './types';

const OVERLAY = 'color-mix(in oklab, #0f1412 60%, transparent)';
const SELECTED = 'color-mix(in oklab, var(--lf-focus) 12%, transparent)';
const FOCUS = '#2f6f8f';
const ACCENT = '#8f2f6f';
const SLATE = '#64748b';

const FILES = ['src/lab-test/roles.css', 'src/lab-test/Widget.svelte'];

/** A role defined once at the root, for both themes. */
function role(name: string, value: string, line: number): CatalogVar {
    return {name, defs: [{file: 0, name, value, line, zone: 'css-file', selector: ':root', theme: null, scope: 'root'}], uses: 1, files: {[FILES[1]]: 1}, use_sites: [[1, line + 20, '.panel']]};
}

/** A stylesheet occurrence of the slate literal. */
function slate(id: number, raw: string, alpha: number, line: number): CatalogLiteral {
    return {id, file: 1, line, col: 12, raw, kind: raw.startsWith('#') ? 'hex' : 'fn', key: SLATE, alpha, zone: 'svelte-style', theme: null, layer: 'css-literal', preview: true, snippet: `color: ${raw};`, selector: '.muted', property: 'color'};
}

const catalog: ColorCatalog = {
    meta: {schema: 'lf-color-catalog/1', app_version: 'test', generated_at: '2026-10-15T00:00:00.000Z', hash: 'lab-test', scan_ms: 0, parity: {}, layers: {}, excluded: []},
    files: FILES,
    css_vars: [role('--lf-surface-overlay', OVERLAY, 3), role('--lf-selected', SELECTED, 4), role('--lf-focus', FOCUS, 5), role('--lf-accent', ACCENT, 6)],
    palette: [],
    literals: [slate(1, SLATE, 1, 12), slate(2, 'rgba(100, 116, 139, 0.5)', 0.5, 18)],
    by_value: {[SLATE]: [1, 2]},
    testids: {},
    testid_prefixes: [],
};

const OVERLAY_VAR: LabSelection = {layer: 'css-var', target: '--lf-surface-overlay'};
const SELECTED_VAR: LabSelection = {layer: 'css-var', target: '--lf-selected'};
const SLATE_LITERAL: LabSelection = {layer: 'css-literal', target: SLATE};

function renderEditor(selection: LabSelection, lab: LabState = emptyState()) {
    const onApply = vi.fn<(change: LabChange) => void>();
    const onRemove = vi.fn<(id: string) => void>();
    const onClose = vi.fn<() => void>();
    render(ColorEditor, {props: {catalog, lab, selection, scope: 'both', dark: false, revision: 0, onApply, onRemove, onClose}});
    return {onApply};
}

const html = () => document.documentElement;
const field = (testid: string) => screen.getByTestId(testid) as HTMLInputElement;
const to = () => field('lab-editor-to');
const slider = () => field('lab-editor-a');
/** The percentage the editor writes beside the A slider. */
const shown = () => slider().closest('label')?.querySelector('code')?.textContent;

const move = (testid: string, value: string) => fireEvent.input(field(testid), {target: {value}});
const color = (text: string): Rgba => {
    const rgba = parseColor(text);
    if (!rgba) throw new Error(`not a colour: ${text}`);
    return rgba;
};

afterEach(() => {
    cleanup();
    html().removeAttribute('style');
});

describe('ColorEditor — the opacity of a translucent role', () => {
    it('shows the share of a mix on the A slider, with L/C/H, and lets it be applied', () => {
        renderEditor(OVERLAY_VAR);
        expect(screen.getByTestId('lab-editor-from')).toHaveTextContent(OVERLAY);
        expect(to()).toHaveValue(OVERLAY);
        expect(screen.queryByTestId('lab-editor-invalid')).toBeNull();
        expect(slider()).toHaveAttribute('type', 'range');
        expect(Number(slider().value)).toBeCloseTo(0.6, 9);
        expect(shown()).toBe('60%');
        for (const id of ['lab-editor-l', 'lab-editor-c', 'lab-editor-h']) expect(screen.getByTestId(id)).toBeInTheDocument();
        expect(screen.getByTestId('lab-editor-apply')).toBeEnabled();
        // The variants checkbox belongs to the literal layers only.
        expect(screen.queryByTestId('lab-editor-alpha')).toBeNull();
    });

    it('moves the share in place and applies the mix', async () => {
        const {onApply} = renderEditor(OVERLAY_VAR);
        await move('lab-editor-a', '0.25');
        expect(to()).toHaveValue('color-mix(in oklab, #0f1412 25%, transparent)');
        expect(shown()).toBe('25%');

        await fireEvent.click(screen.getByTestId('lab-editor-apply'));
        expect(onApply).toHaveBeenCalledTimes(1);
        const change = {layer: 'css-var', target: '--lf-surface-overlay', scope: 'both', from: OVERLAY, to: 'color-mix(in oklab, #0f1412 25%, transparent)'} as const;
        expect(onApply.mock.calls[0][0]).toEqual({...change, id: changeId(change)});
    });

    it('changes the base with L and keeps the share', async () => {
        renderEditor(OVERLAY_VAR);
        await move('lab-editor-l', '0.7');
        expect(to().value).toMatch(/^color-mix\(in oklab, oklch\(70% [\d.]+ [\d.]+\) 60%, transparent\)$/);
        expect(shown()).toBe('60%');
    });

    it('keeps a mix at 0% when its colour changes: only the slider moves the share', async () => {
        renderEditor(OVERLAY_VAR);
        await move('lab-editor-a', '0');
        expect(to()).toHaveValue('color-mix(in oklab, #0f1412 0%, transparent)');
        expect(shown()).toBe('0%');
        await move('lab-editor-color', '#ff00aa');
        expect(to()).toHaveValue('color-mix(in oklab, #ff00aa 0%, transparent)');
        expect(shown()).toBe('0%');
    });

    it('keeps the variable a mix names: the share moves, the role stays referenced', async () => {
        html().style.setProperty('--lf-focus', FOCUS);
        renderEditor(SELECTED_VAR);
        expect(to()).toHaveValue(SELECTED);
        expect(Number(slider().value)).toBeCloseTo(0.12, 9);
        expect(shown()).toBe('12%');

        await move('lab-editor-a', '0.3');
        expect(to()).toHaveValue('color-mix(in oklab, var(--lf-focus) 30%, transparent)');
        // At 100% the mix is the bare variable, still on the slider, which brings the mix back.
        await move('lab-editor-a', '1');
        expect(to()).toHaveValue('var(--lf-focus)');
        expect(shown()).toBe('100%');
        await move('lab-editor-a', '0.5');
        expect(to()).toHaveValue('color-mix(in oklab, var(--lf-focus) 50%, transparent)');
    });

    it('cannot show a mix of a variable the page does not define (the control of the case above)', () => {
        renderEditor(SELECTED_VAR);
        expect(to()).toHaveValue(SELECTED);
        expect(screen.getByTestId('lab-editor-invalid')).toBeInTheDocument();
        expect(screen.queryByTestId('lab-editor-a')).toBeNull();
        expect(screen.getByTestId('lab-editor-apply')).toBeDisabled();
    });

    it('snaps a mix to another variable without losing its share', async () => {
        html().style.setProperty('--lf-focus', FOCUS);
        html().style.setProperty('--lf-accent', ACCENT);
        renderEditor(SELECTED_VAR);
        const snap = screen.getByTestId('lab-editor-snap') as HTMLSelectElement;
        expect(snap).toHaveValue('');
        await fireEvent.change(snap, {target: {value: '--lf-accent'}});
        expect(to()).toHaveValue('color-mix(in oklab, var(--lf-accent) 12%, transparent)');
        expect(shown()).toBe('12%');
    });

    it('loads a saved mix with its variable in the snap and its share on the slider', () => {
        html().style.setProperty('--lf-accent', ACCENT);
        const saved: LabChange = {id: '', layer: 'css-var', target: '--lf-selected', scope: 'both', from: SELECTED, to: 'color-mix(in oklab, var(--lf-accent) 40%, transparent)'};
        renderEditor(SELECTED_VAR, upsertChange(emptyState(), saved));
        expect(screen.getByTestId('lab-editor-remove')).toBeInTheDocument();
        expect(to()).toHaveValue(saved.to);
        expect(screen.getByTestId('lab-editor-snap')).toHaveValue('--lf-accent');
        expect(shown()).toBe('40%');
    });
});

describe('ColorEditor — the opacity of a colour literal', () => {
    it('starts opaque, takes the alpha as hex, and L and the sRGB input keep it', async () => {
        const {onApply} = renderEditor(SLATE_LITERAL);
        expect(to()).toHaveValue(SLATE);
        expect(Number(slider().value)).toBe(1);
        expect(shown()).toBe('100%');

        await move('lab-editor-a', '0.5');
        expect(to()).toHaveValue('#64748b80');

        // L rewrites the colour in OKLCH: chroma and hue stay, and so does the alpha — 0x80 is 128/255, 0.502.
        await move('lab-editor-l', '0.7');
        const lighter = to().value;
        expect(lighter).toMatch(/^oklch\(70% [\d.]+ [\d.]+ \/ 0\.502\)$/);
        const before = rgbaToOklch(color(SLATE));
        const after = rgbaToOklch(color(lighter));
        expect(after.c).toBeCloseTo(before.c, 3);
        expect(after.h).toBeCloseTo(before.h, 1);
        expect(shown()).toBe('50%');

        await move('lab-editor-color', '#ff00aa');
        expect(to()).toHaveValue('#ff00aa80');

        await fireEvent.click(screen.getByTestId('lab-editor-apply'));
        expect(onApply).toHaveBeenCalledTimes(1);
        const change = {layer: 'css-literal', target: SLATE, scope: 'both', from: SLATE, to: '#ff00aa80'} as const;
        expect(onApply.mock.calls[0][0]).toEqual({...change, alphaVariants: true, id: changeId(change)});
    });

    it('takes a colour picked over a fully transparent literal opaque, from L as from the sRGB input', async () => {
        renderEditor(SLATE_LITERAL);
        await move('lab-editor-a', '0');
        expect(to()).toHaveValue('#64748b00');
        expect(shown()).toBe('0%');
        await move('lab-editor-l', '0.7');
        expect(to().value).toMatch(/^oklch\(70% [\d.]+ [\d.]+\)$/);
        expect(shown()).toBe('100%');

        await move('lab-editor-a', '0');
        expect(to().value).toMatch(/^oklch\(70% [\d.]+ [\d.]+ \/ 0\)$/);
        await move('lab-editor-color', '#ff00aa');
        expect(to()).toHaveValue('#ff00aa');
        expect(shown()).toBe('100%');
    });

    it('keeps the «Translucent variants too» checkbox, a control apart from the A slider', () => {
        renderEditor(SLATE_LITERAL);
        const variants = field('lab-editor-alpha');
        expect(variants).toHaveAttribute('type', 'checkbox');
        expect(variants).toBeChecked();
        expect(variants).not.toBe(slider());
    });
});

describe('ColorEditor — a value that is not a colour', () => {
    it.each([
        ['a word', 'nonsense'],
        ['a mix in a misspelt space', 'color-mix(in oklabb, #0f1412 60%, transparent)'],
        ['a mix with a hue method on a rectangular space', 'color-mix(in srgb longer hue, #0f1412 60%, transparent)'],
    ])('flags %s, with no slider and Apply off', async (_label, value) => {
        renderEditor(OVERLAY_VAR);
        // The slider is there first, so its absence below is the editor's answer, not a slow mount.
        expect(slider()).toBeInTheDocument();
        await fireEvent.input(to(), {target: {value}});
        expect(to()).toHaveValue(value);
        expect(screen.getByTestId('lab-editor-invalid')).toBeInTheDocument();
        expect(screen.queryByTestId('lab-editor-a')).toBeNull();
        expect(screen.queryByTestId('lab-editor-l')).toBeNull();
        expect(screen.getByTestId('lab-editor-apply')).toBeDisabled();
    });
});

describe('ColorEditor — a chart category, edited by key', () => {
    const TABLES = 'src/lab-test/categories.ts';
    /** A line of the category tables, or (without a category) a chart colour elsewhere: made-up values. */
    function chartLine(id: number, file: number, line: number, raw: string, theme: 'light' | 'dark', category?: string): CatalogLiteral {
        return {id, file, line, col: 16, raw, kind: 'hex', key: raw.toLowerCase(), alpha: 1, zone: 'ts', theme, layer: 'chart-color', preview: true, chart: true, snippet: `${theme}: '${raw}',`, ...(category ? {category} : {})};
    }
    // `type:AAA` and `sector:Zed Sector` share their light value: an edit of that value reaches both categories.
    const categoryCatalog: ColorCatalog = {
        ...catalog,
        files: [TABLES, 'src/lab-test/Chart.svelte'],
        css_vars: [],
        literals: [chartLine(0, 0, 10, '#2B4C7E', 'light', 'type:AAA'), chartLine(1, 0, 11, '#7EA6E0', 'dark', 'type:AAA'), chartLine(2, 0, 20, '#2B4C7E', 'light', 'sector:Zed Sector'), chartLine(3, 0, 21, '#334455', 'dark', 'sector:Zed Sector'), chartLine(4, 1, 5, '#5A6B7C', 'light')],
        by_value: {},
        categories: [
            {target: 'type:AAA', kind: 'type', key: 'AAA', light: 0, dark: 1},
            {target: 'sector:Zed Sector', kind: 'sector', key: 'Zed Sector', light: 2, dark: 3},
        ],
    };
    const AAA: LabSelection = {layer: 'category', target: 'type:AAA'};

    function renderCategory(selection: LabSelection, scope: Scope, dark = false) {
        const onApply = vi.fn<(change: LabChange) => void>();
        render(ColorEditor, {props: {catalog: categoryCatalog, lab: emptyState(), selection, scope, dark, revision: 0, onApply, onRemove: vi.fn(), onClose: vi.fn()}});
        return {onApply};
    }

    it.each([
        ['light', false, '#2B4C7E'],
        ['dark', false, '#7EA6E0'],
        ['both', false, '#2B4C7E'],
        ['both', true, '#7EA6E0'],
    ] as const)('starts from the value the table writes for the scope (%s, page dark %s)', (scope, dark, value) => {
        renderCategory(AAA, scope, dark);
        expect(screen.getByTestId('lab-editor-from')).toHaveTextContent(value);
        expect(to()).toHaveValue(value);
    });

    it('says what a category edit reaches and lists its line in each theme, with no translucent-variants checkbox', () => {
        renderCategory(AAA, 'both');
        expect(screen.getByTestId('lab-editor-category-reach')).toBeInTheDocument();
        const rows = Array.from(screen.getByTestId('lab-editor-category-lines').querySelectorAll('li'));
        expect(rows.map((li) => li.textContent?.includes(`${TABLES}:10`) && li.textContent.includes('#2B4C7E'))).toEqual([true, false]);
        expect(rows.map((li) => li.textContent?.includes(`${TABLES}:11`) && li.textContent.includes('#7EA6E0'))).toEqual([false, true]);
        expect(screen.queryByTestId('lab-editor-alpha')).toBeNull();
        expect(screen.queryByTestId('lab-editor-occurrences')).toBeNull();
        // Edited by key: the value the category shares with another is not this editor's concern.
        expect(screen.queryByTestId('lab-editor-category-warning')).toBeNull();
    });

    it('applies a category change: its layer, target and scope, the table’s value as the start', async () => {
        const {onApply} = renderCategory(AAA, 'dark');
        await fireEvent.input(to(), {target: {value: '#123456'}});
        await fireEvent.click(screen.getByTestId('lab-editor-apply'));
        expect(onApply).toHaveBeenCalledTimes(1);
        const change = {layer: 'category', target: 'type:AAA', scope: 'dark', from: '#7EA6E0', to: '#123456'} as const;
        const applied = onApply.mock.calls[0][0];
        expect(applied).toEqual({...change, id: changeId(change)});
        expect('alphaVariants' in applied).toBe(false);
    });

    it('warns, on a chart colour that is a category’s colour, which categories editing the value reaches', () => {
        renderCategory({layer: 'chart-color', target: '#2b4c7e'}, 'both');
        const warning = screen.getByTestId('lab-editor-category-warning');
        expect(warning).toHaveTextContent('type:AAA');
        expect(warning).toHaveTextContent('sector:Zed Sector');
    });

    it('gives no warning on a chart colour no category writes', () => {
        renderCategory({layer: 'chart-color', target: '#5a6b7c'}, 'both');
        // Barrier: the editor lists the colour's occurrence, so the warning had what it needs to appear.
        expect(screen.getByTestId('lab-editor-occurrences').querySelectorAll('li')).toHaveLength(1);
        expect(screen.queryByTestId('lab-editor-category-warning')).toBeNull();
    });
});
