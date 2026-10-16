// @vitest-environment jsdom
/**
 * Designer Lab — contract C4 with DV: the engine tells the charts to read their colours again.
 *
 * A chart reads a role (`chartRoles`) or a category (`categoryColor`) when it builds its option, so a Lab edit of
 * either reaches it only at its next draw. `applyState` (`engine/index.ts`) therefore sends
 * `notifyChartColorsChange()` — the event `lf:chart-colors-change` on `document` that `onChartColorsChange` listens to —
 * whenever what the charts read changed: the `css-var` and `category` changes, compared by id and value with the last
 * state applied, and the variables the stylesheet pass rewrote (`variableRewrites()`): a literal inside a variable's
 * definition — every `--lf-*` role of `tokens.css` is one, `:root { --lf-…: #… }` — changes the role a chart reads. Once
 * per change of them: a state applied, an edit, a suspension, a reset back to none, and a theme switch that re-plans a
 * one-theme literal of a definition; never for a state applied again with the same inputs, nor for one whose changes the
 * charts do not read (stylesheet literals that define no variable, specialisations, colour-vision simulation).
 *
 * The listener is the one the charts use (`onChartColorsChange` of `lib/theme/themeMode`), and it reads the category the
 * way a chart would at that moment: the redraw must meet the new state, so the event comes after the engines.
 *
 * No module is mocked: every state here leaves the chart engine idle (no `chart-color` change, so ECharts is never
 * loaded), and jsdom carries the stylesheet, variable and specialisation engines — its CSSOM parses a `<style>` the test
 * inserts, custom properties included. Each test loads a fresh engine, so "the last state applied" starts from none.
 */

import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {onChartColorsChange} from '$lib/theme/themeMode';
import {colorKey, parseColor} from './color.js';
import {changeId, emptyState} from './store';
import type {LabChange, LabState} from './types';

type Engine = typeof import('./engine/index');

/** A change as the Lab stores it, with the id the store gives it. */
function make(fields: Omit<LabChange, 'id'>): LabChange {
    return {...fields, id: changeId(fields)};
}

// Made-up targets and colours: nothing here is a real role or category.
const VAR = make({layer: 'css-var', target: '--lf-test-role', scope: 'both', from: '#0a0a0a', to: '#112233'});
const CAT = make({layer: 'category', target: 'type:AAA', scope: 'light', from: '#0b0b0b', to: '#445566'});
const LIT = make({layer: 'css-literal', target: '#778899', scope: 'both', from: '#778899', to: '#000000', alphaVariants: true});
const ELEMENT = make({layer: 'element', target: '[data-testid="lab-test-box"]', scope: 'both', from: 'rgb(0, 0, 0)', to: '#123456', property: 'color'});

const stateOf = (changes: LabChange[], extra: Partial<LabState> = {}): LabState => ({...emptyState(), changes, ...extra});

const html = () => document.documentElement;

let engine: Engine;
let listener: {disconnect: () => void};
/** What a chart reads for `type:AAA` in the light theme, at each event. */
let heard: (string | undefined)[];

/** How many events one `applyState` sends. */
async function events(state: LabState | null): Promise<number> {
    const before = heard.length;
    await engine.applyState(state);
    return heard.length - before;
}

beforeEach(async () => {
    vi.resetModules();
    engine = await import('./engine/index');
    heard = [];
    listener = onChartColorsChange(() => heard.push(engine.categoryColor('type', 'AAA', false)));
});

afterEach(async () => {
    listener.disconnect();
    await engine.applyState(null);
});

describe('C4 — the charts hear when what they read changed', () => {
    it('sends one event per change of the variables and categories, none for the same inputs again', async () => {
        expect(await events(stateOf([VAR])), 'a variable applied').toBe(1);
        expect(engine.stats()).toMatchObject({varOverrides: 1, categoryOverrides: 0});

        expect(await events(stateOf([VAR])), 'the same state again').toBe(0);

        expect(await events(stateOf([VAR, CAT])), 'a category added').toBe(1);
        expect(engine.stats()).toMatchObject({varOverrides: 1, categoryOverrides: 1});
        expect(heard.at(-1), 'the redraw meets the new category').toBe('#445566');

        expect(await events(stateOf([VAR, {...CAT, to: '#556677'}])), 'the category edited').toBe(1);
        expect(heard.at(-1)).toBe('#556677');
        expect(engine.stats().categoryOverrides).toBe(1);

        expect(
            await events(
                stateOf([
                    {...VAR, to: '#223344'},
                    {...CAT, to: '#556677'},
                ]),
            ),
            'the variable edited',
        ).toBe(1);

        expect(
            await events(
                stateOf(
                    [
                        {...VAR, to: '#223344'},
                        {...CAT, to: '#556677'},
                    ],
                    {suspended: true},
                ),
            ),
            'the state suspended',
        ).toBe(1);
        expect(heard.at(-1), 'the redraw meets the table colours again').toBeUndefined();
        expect(engine.stats()).toMatchObject({varOverrides: 0, categoryOverrides: 0});

        expect(await events(null), 'reset after a suspension: nothing left to undo').toBe(0);
        expect(engine.stats().categoryOverrides).toBe(0);
    });

    it('sends one event on a reset straight from a state with a category, and none on a second reset', async () => {
        expect(await events(stateOf([CAT]))).toBe(1);
        expect(engine.stats().categoryOverrides).toBe(1);
        expect(await events(null)).toBe(1);
        expect(heard.at(-1)).toBeUndefined();
        expect(engine.stats().categoryOverrides).toBe(0);
        expect(await events(null)).toBe(0);
    });

    it('stays silent, from scratch, for states whose changes the charts do not read', async () => {
        expect(await events(stateOf([LIT])), 'a stylesheet literal no sheet writes in a variable').toBe(0);
        expect(engine.isActive(), 'barrier: the state was applied').toBe(true);

        expect(await events(stateOf([LIT, ELEMENT])), 'a specialisation added').toBe(0);
        expect(engine.stats().elementRules, 'barrier: the specialisation was written').toBe(1);

        expect(await events(stateOf([], {cvd: 'protanopia'})), 'colour-vision simulation only').toBe(0);
        expect(engine.isActive(), 'barrier: a simulation alone is a state with an effect').toBe(true);

        expect(engine.stats()).toMatchObject({varOverrides: 0, categoryOverrides: 0});
        expect(await events(null), 'a reset from them').toBe(0);
    });
});

describe('C4 — a literal inside a variable’s definition changes the variable', () => {
    // Made-up variables and colours, in sheets the test inserts: `ROLE` is written in variables, `PLAIN` in ordinary
    // declarations only.
    const ROLE = '#778800';
    const PLAIN = '#556600';

    function sheet(css: string): void {
        const style = document.createElement('style');
        style.setAttribute('data-lab-test', '');
        style.textContent = css;
        document.head.appendChild(style);
    }

    const literal = (target: string, to: string, scope: LabChange['scope'] = 'both') => make({layer: 'css-literal', target, scope, from: target, to, alphaVariants: true});

    /** The value the test's rule `selector` gives `prop` now, as the CSSOM holds it. */
    function declared(selector: string, prop: string): string {
        for (const style of Array.from(document.querySelectorAll<HTMLStyleElement>('style[data-lab-test]'))) for (const rule of Array.from(style.sheet?.cssRules ?? [])) if (rule instanceof CSSStyleRule && rule.selectorText === selector) return rule.style.getPropertyValue(prop).trim();
        throw new Error(`no rule ${selector}`);
    }

    /**
     * Switch the theme class of <html>, and return how many events the engine sent for it. Every observer of the class
     * change is called in one notification before the promise below resumes: the engine's re-plan included.
     */
    async function switchTheme(dark: boolean): Promise<number> {
        const before = heard.length;
        await new Promise<void>((resolve) => {
            const barrier = new MutationObserver(() => {
                barrier.disconnect();
                resolve();
            });
            barrier.observe(html(), {attributes: true, attributeFilter: ['class']});
            html().classList.toggle('dark', dark);
        });
        return heard.length - before;
    }

    afterEach(async () => {
        await engine.applyState(null);
        for (const style of Array.from(document.querySelectorAll('style[data-lab-test]'))) style.remove();
        html().removeAttribute('class');
    });

    it('sends one event when a literal of a role’s definition is rewritten, edited or reset, none for the same state again', async () => {
        sheet(`:root { --lf-test-role: ${ROLE}; }`);
        const change = literal(ROLE, '#112200');
        expect(await events(stateOf([change])), 'applied').toBe(1);
        expect(declared(':root', '--lf-test-role'), 'barrier: the definition was rewritten').toBe('#112200');
        expect(await events(stateOf([change])), 'the same state again').toBe(0);
        expect(await events(stateOf([{...change, to: '#113300'}])), 'edited').toBe(1);
        expect(declared(':root', '--lf-test-role')).toBe('#113300');
        expect(await events(null), 'reset').toBe(1);
        expect(declared(':root', '--lf-test-role'), 'the definition restored').toBe(ROLE);
        expect(await events(null), 'a second reset').toBe(0);
    });

    it('stays silent for a literal that only an ordinary declaration writes', async () => {
        sheet(`.lab-box { color: ${PLAIN}; }`);
        expect(await events(stateOf([literal(PLAIN, '#112200')]))).toBe(0);
        expect(engine.stats().cssRules, 'barrier: the declaration was rewritten').toBeGreaterThan(0);
        // jsdom serialises an ordinary colour as `rgb()`: compared by colour.
        expect(colorKey(parseColor(declared('.lab-box', 'color')) ?? {r: 0, g: 0, b: 0, alpha: 0})).toBe('#112200');
        expect(await events(null), 'reset').toBe(0);
    });

    it('sends one event when a literal of a variable a component defines is rewritten, and one when it is reset', async () => {
        sheet(`.lab-scope { --lf-test-local: ${ROLE}; }`);
        expect(await events(stateOf([literal(ROLE, '#112200')]))).toBe(1);
        expect(declared('.lab-scope', '--lf-test-local'), 'barrier: the definition was rewritten').toBe('#112200');
        expect(await events(null)).toBe(1);
    });

    it.each([
        ['light', 1],
        ['both', 0],
    ] as const)('re-plans a %s literal of a role’s definition on a theme switch, with %i event each way', async (scope, expected) => {
        sheet(`:root { --lf-test-role: ${ROLE}; }`);
        expect(await events(stateOf([literal(ROLE, '#112200', scope)])), 'applied in light').toBe(1);
        expect(await switchTheme(true), 'to dark').toBe(expected);
        expect(declared(':root', '--lf-test-role'), 'the definition in dark').toBe(scope === 'light' ? ROLE : '#112200');
        expect(await switchTheme(false), 'back to light').toBe(expected);
        expect(declared(':root', '--lf-test-role'), 'the definition in light').toBe('#112200');
    });

    it('lists the variables the pass rewrote — rule, property and value now, sorted — and nothing after a reset', async () => {
        sheet(
            [
                `:root { --lf-test-b: ${ROLE}; --lf-test-a: ${ROLE}; color: ${ROLE}; }`,
                // Longhands only: jsdom expands a shorthand into its longhands, each a declaration of its own.
                `.lab-scope { --lf-test-local: ${PLAIN}; background-color: ${PLAIN}; }`,
                // A variable defined for the page and in a component: a `css-var` change overrides the first on <html>
                // (L1) and rewrites the second.
                ':root { --lf-test-component: #000001; }',
                '.lab-card { --lf-test-component: #000001; }',
            ].join('\n'),
        );
        // The instance the engine loaded: the modules were reset before it.
        const {variableRewrites} = await import('./engine/stylesheets');
        expect(variableRewrites()).toEqual([]);
        await engine.applyState(stateOf([literal(ROLE, '#112200'), literal(PLAIN, '#223300'), make({layer: 'css-var', target: '--lf-test-component', scope: 'both', from: '#000001', to: '#334400'})]));
        expect(variableRewrites()).toEqual(['.lab-card|--lf-test-component|#334400', '.lab-scope|--lf-test-local|#223300', ':root|--lf-test-a|#112200', ':root|--lf-test-b|#112200']);
        // The two ordinary declarations were rewritten as well, and are not listed.
        expect(engine.stats().cssRules).toBe(6);
        await engine.applyState(null);
        expect(variableRewrites()).toEqual([]);
    });
});
