// @vitest-environment jsdom
//
// The docblock above is load-bearing: what this file tests is the page — the computed style of an element, and a
// `<canvas>`. jsdom resolves custom properties in a computed style, inline or from a sheet, and inherits them down the
// tree as a browser does; it has no 2D context, so the canvas cases install one.
/**
 * roleColors through a page — the paths of `chartRoles` that read the DOM (D-T5, DV; T's review of the bridge).
 *
 * - **Where it reads.** The computed style of the chart's own element when it is given (`scope`): tokens.css
 *   recomputes the roles in the `.light`/`.dark` subtrees, so a chart in a forced subtree reads that subtree's values,
 *   inherited. `<html>` when there is no scope. `dark` picks a stand-in only for a role the page does not set.
 * - **When it reads.** One `getComputedStyle` per `chartRoles` call, taken at the first read — never at creation,
 *   never twice for one draw — and never kept across draws: a role changed between two draws is read anew.
 * - **Any other notation goes through a canvas `fillStyle`**, written over black and over white: a colour the canvas
 *   takes comes back the same both times, as the canvas serialises it — `rgba()` when translucent, handed to the chart
 *   as it is, never flattened; one it ignores comes back as the two colours it was written over, and the stand-in takes
 *   its place. Each raw value is resolved once, valid or not. The installed context behaves as a browser's does: it
 *   takes the colours it knows and ignores the rest. The probe and the resolutions are module state, so each canvas
 *   case loads a fresh copy of the module.
 *
 * The parity of the stand-ins with tokens.css, and the paths that need no page, are `roleColors.test.ts`'s (node).
 *
 * @module lib/theme/roleColors.dom.test
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

import {chartRoles, type ChartRole, setRoleReader} from './roleColors';

const ROLES: readonly ChartRole[] = ['--lf-surface-card', '--lf-surface-panel', '--lf-text-primary', '--lf-text-on-inverse', '--lf-danger', '--lf-info'];

const html = document.documentElement;
/** Every element a test adds to the page — sheets and subtrees — removed after it. */
let added: Element[] = [];

afterEach(() => {
    setRoleReader(null);
    vi.restoreAllMocks();
    for (const role of ROLES) html.style.removeProperty(role);
    for (const element of added) element.remove();
    added = [];
});

/** A stylesheet, as tokens.css sets the roles: on `:root`, and again in the `.light`/`.dark` subtrees. */
function addSheet(css: string): void {
    const sheet = document.head.appendChild(document.createElement('style'));
    sheet.textContent = css;
    added.push(sheet);
}

/** A chart's element inside a subtree forced to `theme`, as the Designer Lab's preview or a forced panel holds one. */
function chartInForcedSubtree(theme: 'light' | 'dark'): HTMLElement {
    const subtree = document.body.appendChild(document.createElement('div'));
    subtree.className = theme;
    added.push(subtree);
    return subtree.appendChild(document.createElement('div'));
}

/** What a role reads where the page does not set it: the stand-in, as an empty role reads it. */
function standIn(role: ChartRole, dark: boolean): string {
    setRoleReader(() => '');
    const value = chartRoles(dark, null).color(role);
    setRoleReader(null);
    return value;
}

describe('chartRoles — where it reads: the chart’s own element, <html> without one', () => {
    it('reads <html> when no scope is given, or a null one: a role set inline and one set by a :root rule', () => {
        html.style.setProperty('--lf-surface-card', '#ABCDEF');
        addSheet(':root { --lf-danger: #654321; }');

        for (const roles of [chartRoles(false), chartRoles(false, null)]) {
            expect(roles.color('--lf-surface-card')).toBe('#ABCDEF');
            expect(roles.color('--lf-danger')).toBe('#654321');
        }
    });

    it('reads the scope: a chart in a forced .dark subtree inherits the subtree’s roles, whatever <html> says and whatever the flag', () => {
        addSheet(':root { --lf-info: #145dee; } .dark { --lf-info: #5899fa; }');
        const chart = chartInForcedSubtree('dark');

        expect(chartRoles(false).color('--lf-info'), '<html>').toBe('#145dee');
        expect(chartRoles(false, chart).color('--lf-info'), 'the chart in the forced subtree, light flag').toBe('#5899fa');
        expect(chartRoles(true, chart).color('--lf-info'), 'the same chart, dark flag: the page decides, not the flag').toBe('#5899fa');
    });

    it('stands in, per theme, for a role the page does not set — as for an empty one', () => {
        const chart = chartInForcedSubtree('light');
        for (const role of ROLES) {
            expect(getComputedStyle(chart).getPropertyValue(role), `premise: the page sets no ${role}`).toBe('');
            for (const dark of [false, true]) expect(chartRoles(dark, chart).color(role), `${role}, dark ${dark}`).toBe(standIn(role, dark));
        }
        expect(standIn('--lf-surface-card', false), 'barrier: the two stand-ins differ, so the theme was picked').not.toBe(standIn('--lf-surface-card', true));
    });

    it('reads readableText’s three roles from the scope too: the texts and the card of the subtree', () => {
        addSheet(':root { --lf-text-primary: #000001; --lf-text-on-inverse: #fffffe; --lf-surface-card: #ffffff; } .dark { --lf-text-primary: #fffffe; --lf-text-on-inverse: #000001; --lf-surface-card: #000000; }');
        const chart = chartInForcedSubtree('dark');
        const veil = 'rgba(0, 0, 0, 0.5)';

        expect(chartRoles(false).readableText(veil), 'on <html>: a white card, the veil a mid grey, the dark text').toBe('#000001');
        expect(chartRoles(false, chart).readableText(veil), 'in the dark subtree: a black card, the veil black, the light text').toBe('#fffffe');
    });
});

describe('chartRoles — when it reads: one computed style per draw', () => {
    it('takes no computed style at creation, one at the first read, and no other for the rest of the draw', () => {
        const getComputedStyleSpy = vi.spyOn(globalThis, 'getComputedStyle');
        const chart = chartInForcedSubtree('light');

        const roles = chartRoles(false, chart);
        expect(getComputedStyleSpy, 'at creation').not.toHaveBeenCalled();

        roles.color('--lf-surface-card');
        roles.color('--lf-danger');
        roles.readableText('#808080');
        expect(getComputedStyleSpy, 'three roles, then readableText').toHaveBeenCalledTimes(1);
        expect(getComputedStyleSpy).toHaveBeenCalledWith(chart);

        chartRoles(false, chart).color('--lf-info');
        expect(getComputedStyleSpy, 'the next draw takes its own').toHaveBeenCalledTimes(2);
    });

    it('keeps nothing across draws: a role changed between two draws is read anew, and removed it stands in again', () => {
        html.style.setProperty('--lf-surface-panel', '#111111');
        expect(chartRoles(true).color('--lf-surface-panel')).toBe('#111111');

        html.style.setProperty('--lf-surface-panel', '#222222');
        expect(chartRoles(true).color('--lf-surface-panel')).toBe('#222222');

        html.style.removeProperty('--lf-surface-panel');
        expect(chartRoles(true).color('--lf-surface-panel')).toBe(standIn('--lf-surface-panel', true));
    });
});

/**
 * A 2D context as far as the probe uses it: `fillStyle` takes a `#rrggbb` or a colour listed in `known` — stored in
 * the form the canvas serialises it to — and ignores anything else, keeping the colour it had, as a browser does.
 * `writes` records every assignment, so a test can tell a resolution from a remembered one.
 */
function installCanvas(known: Readonly<Record<string, string>>) {
    let current = '#000000';
    const writes: string[] = [];
    const context = {
        get fillStyle(): string {
            return current;
        },
        set fillStyle(value: string) {
            writes.push(value);
            const canonical = /^#[0-9a-f]{6}$/i.test(value) ? value.toLowerCase() : known[value];
            if (canonical !== undefined) current = canonical;
        },
    };
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context as unknown as RenderingContext);
    return {writes, getContext};
}

/** A fresh copy of the module: its probe and its resolutions are module state, and each canvas case starts with none. */
async function freshRoleColors(): Promise<typeof import('./roleColors')> {
    vi.resetModules();
    return import('./roleColors');
}

/** The raw value of a role as the page computes it — jsdom may rewrite what was set — once it is set inline on `<html>`. */
function setOnPage(role: ChartRole, value: string): string {
    html.style.setProperty(role, value);
    const raw = getComputedStyle(html).getPropertyValue(role).trim();
    expect(raw, `premise: the page holds ${role}`).not.toBe('');
    return raw;
}

describe('chartRoles — any other notation, painted by a canvas (a 2D context installed: jsdom has none)', () => {
    it('hands back what the canvas paints for a notation of the page, the value written over black and over white', async () => {
        const roles = await freshRoleColors();
        const raw = setOnPage('--lf-surface-panel', 'color-mix(in oklab, #b42332 40%, #eee9de)');
        const {writes} = installCanvas({[raw]: '#d7a3a6'});

        expect(roles.chartRoles(false).color('--lf-surface-panel')).toBe('#d7a3a6');
        expect(writes, 'over black, then over white').toEqual(['#000000', raw, '#ffffff', raw]);
    });

    it('hands a translucent colour to the chart as the canvas reports it — rgba(), never flattened', async () => {
        const roles = await freshRoleColors();
        const raw = setOnPage('--lf-surface-card', 'rgb(0 0 0 / 50%)');
        installCanvas({[raw]: 'rgba(0, 0, 0, 0.5)'});

        expect(roles.chartRoles(true).color('--lf-surface-card')).toBe('rgba(0, 0, 0, 0.5)');
    });

    it('stands in for a value the canvas ignores: it comes back as the two colours it was written over', async () => {
        const roles = await freshRoleColors();
        installCanvas({});

        for (const value of ['not-a-colour', 'oklch(0.5)']) {
            const raw = setOnPage('--lf-info', value);
            expect(roles.chartRoles(false).color('--lf-info'), `${raw}, light`).toBe(standIn('--lf-info', false));
            expect(roles.chartRoles(true).color('--lf-info'), `${raw}, dark`).toBe(standIn('--lf-info', true));
        }
    });

    it('resolves each raw value once, valid or not: the next draws never touch the canvas again', async () => {
        const roles = await freshRoleColors();
        const valid = setOnPage('--lf-danger', 'oklch(0.55 0.18 25)');
        const invalid = setOnPage('--lf-info', 'not-a-colour');
        const {writes, getContext} = installCanvas({[valid]: '#b42332'});

        const first = [roles.chartRoles(false).color('--lf-danger'), roles.chartRoles(false).color('--lf-info')];
        const written = writes.length;
        expect(written, 'barrier: both were resolved through the canvas the first time').toBe(8);

        expect([roles.chartRoles(false).color('--lf-danger'), roles.chartRoles(false).color('--lf-info')], 'the same answers').toEqual(first);
        expect(writes.length, 'read again, neither is written to the canvas again').toBe(written);
        expect(getContext, 'one canvas for the module').toHaveBeenCalledTimes(1);
    });

    it('stands in for every other notation where no 2D context exists, and still passes a #rrggbb', async () => {
        const roles = await freshRoleColors();
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);

        setOnPage('--lf-danger', 'oklch(0.55 0.18 25)');
        expect(roles.chartRoles(true).color('--lf-danger')).toBe(standIn('--lf-danger', true));
        setOnPage('--lf-danger', '#ABCDEF');
        expect(roles.chartRoles(true).color('--lf-danger')).toBe('#ABCDEF');
    });
});
