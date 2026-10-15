/**
 * Designer Lab — the facts of a picked element: for each visible colour, its value and the declaration that sets it.
 *
 * Runs in the app tab, without the catalogue (the Lab resolves the facts against it). The declaration that sets a
 * property is proved, not guessed: the candidates — matching rules (layers, `@media`, `@supports`, nesting and
 * shorthands included), the inline style, SVG attributes — are tried in cascade order. Each is changed to a probe
 * colour, the computed value is read, the declaration is restored, and the first whose change shows wins. All of it
 * runs in one task with transitions off: nothing is painted in between and no transition starts.
 */

import {page} from '$app/state';
import index from 'virtual:lf-testid-index';
import {COLOR_TOKEN_RE, parseColor} from '../color.js';
import {BORDER_SIDES, INHERITED_COLOR_PROPERTIES, MULTI_COLOR_PROPERTIES, SHORTHANDS} from '../cssProps';
import {ELEMENT_STYLE_ID} from '../engine/anchors';
import {chartColorAtPoint, chartColorsAt} from '../engine/charts';
import {originalValue} from '../engine/stylesheets';
import {OWN_ATTR} from '../engine/vars';
import type {PickedChart, PickedDeclaration, PickedElement, PickedProperty} from '../types';
import {codeTestid, componentSelector, countMatches, cssPath, nearestTestid, routeOf, scopeClass, selectorNames, stableClasses, testidChain, testidSelector} from './anchor';

const PROBE_COLOR = 'rgb(1, 2, 3)';
type MultiColorProperty = (typeof MULTI_COLOR_PROPERTIES)[number];
/** A property that holds several colours needs a probe that is a valid value of that property. */
const PROBES: Record<MultiColorProperty, string> = {'box-shadow': `0 0 0 1px ${PROBE_COLOR}`, 'background-image': `linear-gradient(${PROBE_COLOR}, ${PROBE_COLOR})`};
const probeFor = (property: string): string => ((MULTI_COLOR_PROPERTIES as readonly string[]).includes(property) ? PROBES[property as MultiColorProperty] : PROBE_COLOR);
const MAX_PROBES = 12;
const STATE_PSEUDO = /(?<!\\):(?:hover|focus-visible|focus-within|focus|active)\b/;
const STATE_PSEUDO_ALL = new RegExp(STATE_PSEUDO.source, 'g');
const INTEREST = /^(color|background|border|outline|text-decoration|fill|stroke|box-shadow)/;

interface FlatRule {
    style: CSSStyleDeclaration;
    selector: string;
    layer: string | null;
    conditions: string[];
    sheet: string | null;
    order: number;
}

interface Match {
    rule: FlatRule;
    state: boolean;
}

interface Candidate {
    decl: PickedDeclaration;
    order: number;
    /** Put the probe in place; returns what restores the declaration exactly. */
    probe: () => () => void;
}

const sheetName = (sheet: CSSStyleSheet) => (sheet.href ? (sheet.href.split('/').pop() ?? sheet.href).split('?')[0] : 'inline <style>');

/** A nested rule's selector, made absolute (`&` stands for the parent). */
const nest = (child: string, parent: string) => (child.includes('&') ? child.replaceAll('&', `:is(${parent})`) : `:is(${parent}) ${child}`);

function declaresColors(style: CSSStyleDeclaration): boolean {
    for (let i = 0; i < style.length; i++) if (INTEREST.test(style[i])) return true;
    return false;
}

/** Every style rule of the page that can set a colour, outside the Lab's own sheets, in document order. */
export function collectRules(doc: Document = document): FlatRule[] {
    const rules: FlatRule[] = [];
    let order = 0;
    const walk = (list: CSSRuleList, ctx: {layer: string | null; conditions: string[]; sheet: string | null; parent: string | null}): void => {
        for (const rule of Array.from(list)) {
            if (rule instanceof CSSStyleRule) {
                const selector = ctx.parent ? nest(rule.selectorText, ctx.parent) : rule.selectorText;
                if (declaresColors(rule.style)) rules.push({style: rule.style, selector, layer: ctx.layer, conditions: ctx.conditions, sheet: ctx.sheet, order: order++});
                if (rule.cssRules?.length) walk(rule.cssRules, {...ctx, parent: selector});
            } else if (rule instanceof CSSMediaRule) {
                if (window.matchMedia(rule.media.mediaText).matches) walk(rule.cssRules, {...ctx, conditions: [...ctx.conditions, `@media ${rule.media.mediaText}`]});
            } else if (rule instanceof CSSSupportsRule) {
                if (CSS.supports(rule.conditionText)) walk(rule.cssRules, {...ctx, conditions: [...ctx.conditions, `@supports ${rule.conditionText}`]});
            } else if (rule instanceof CSSLayerBlockRule) {
                walk(rule.cssRules, {...ctx, layer: ctx.layer ? `${ctx.layer}.${rule.name}` : rule.name});
            } else if (rule instanceof CSSGroupingRule && !/^CSSStartingStyleRule$/.test(rule.constructor.name)) {
                // @container, @scope…: conditions the page cannot evaluate here; the probe decides.
                walk(rule.cssRules, {...ctx, conditions: [...ctx.conditions, rule.cssText.slice(0, rule.cssText.indexOf('{')).trim()]});
            }
        }
    };
    for (const sheet of Array.from(doc.styleSheets)) {
        const owner = sheet.ownerNode;
        if (owner instanceof Element && owner.hasAttribute(OWN_ATTR)) continue;
        let list: CSSRuleList;
        try {
            list = sheet.cssRules;
        } catch {
            continue;
        }
        walk(list, {layer: null, conditions: [], sheet: sheetName(sheet), parent: null});
    }
    return rules;
}

function matchesSafe(el: Element, selector: string): boolean {
    try {
        return el.matches(selector);
    } catch {
        return false;
    }
}

/** The rules matching `el`, and those that would match it in a state it is not in (`:hover`, `:focus`…). */
function matchRules(el: Element, rules: FlatRule[]): Match[] {
    const out: Match[] = [];
    for (const rule of rules) {
        if (rule.selector.includes('::')) continue;
        if (matchesSafe(el, rule.selector)) out.push({rule, state: false});
        else if (STATE_PSEUDO.test(rule.selector)) {
            const stripped = rule.selector.replace(STATE_PSEUDO_ALL, '');
            if (stripped && matchesSafe(el, stripped)) out.push({rule, state: true});
        }
    }
    return out;
}

/** The declaration of `property` in a block: the longhand, or the shorthand that sets it (a `var()` in a shorthand leaves the longhand empty). */
function declarationIn(style: CSSStyleDeclaration, property: string): {value: string; declaredAs: string; important: boolean} | null {
    for (const name of [property, ...(SHORTHANDS[property] ?? [])]) {
        const value = style.getPropertyValue(name);
        if (value) return {value: originalValue(style, name) ?? value, declaredAs: name, important: style.getPropertyPriority(name) === 'important'};
    }
    return null;
}

const probeStyle = (style: CSSStyleDeclaration, property: string, important: boolean) => () => {
    const snapshot = style.cssText;
    style.setProperty(property, probeFor(property), important ? 'important' : '');
    return () => {
        style.cssText = snapshot;
    };
};

/** Higher first: important; inline before rules before attributes; unlayered before layered for normal declarations (the reverse for important); later first. */
function cascadeRank(c: Candidate): number[] {
    const origin = c.decl.origin === 'inline' ? 2 : c.decl.origin === 'rule' ? 1 : 0;
    const layered = c.decl.layer !== null ? 1 : 0;
    return [c.decl.state ? 0 : 1, c.decl.important ? 1 : 0, origin, c.decl.important ? layered : 1 - layered, c.order];
}

function byCascade(a: Candidate, b: Candidate): number {
    const ra = cascadeRank(a);
    const rb = cascadeRank(b);
    for (let i = 0; i < ra.length; i++) if (ra[i] !== rb[i]) return rb[i] - ra[i];
    return 0;
}

function candidatesOf(el: Element, property: string, matches: Match[]): Candidate[] {
    const out: Candidate[] = [];
    const base = {layer: null, sheet: null, conditions: [] as string[], state: false, wins: false};
    if (el instanceof HTMLElement || el instanceof SVGElement) {
        const inline = declarationIn(el.style, property);
        if (inline) out.push({decl: {...base, origin: 'inline', selector: null, value: inline.value, declared_as: inline.declaredAs, important: inline.important}, order: Number.MAX_SAFE_INTEGER, probe: probeStyle(el.style, property, inline.important)});
    }
    for (const m of matches) {
        const d = declarationIn(m.rule.style, property);
        if (!d) continue;
        out.push({
            decl: {origin: 'rule', selector: m.rule.selector, value: d.value, declared_as: d.declaredAs, important: d.important, layer: m.rule.layer, sheet: m.rule.sheet, conditions: m.rule.conditions, state: m.state, wins: false},
            order: m.rule.order,
            probe: probeStyle(m.rule.style, property, d.important),
        });
    }
    const attribute = property === 'fill' || property === 'stroke' || property === 'color' ? el.getAttribute(property) : null;
    if (el instanceof SVGElement && attribute) {
        out.push({
            decl: {...base, origin: 'attribute', selector: null, value: attribute, declared_as: property, important: false},
            order: -1,
            probe: () => {
                el.setAttribute(property, PROBE_COLOR);
                return () => el.setAttribute(property, attribute);
            },
        });
    }
    return out.sort(byCascade);
}

/** The index of the candidate whose change shows in `observed`'s computed value, or -1. */
function prove(observed: Element, property: string, candidates: Candidate[]): number {
    const read = () => getComputedStyle(observed).getPropertyValue(property);
    const before = read();
    let tried = 0;
    for (let i = 0; i < candidates.length && tried < MAX_PROBES; i++) {
        if (candidates[i].decl.state) continue;
        tried++;
        const restore = candidates[i].probe();
        const after = read();
        restore();
        if (after !== before) return i;
    }
    return -1;
}

const colorsOf = (value: string): string[] => [...value.matchAll(COLOR_TOKEN_RE)].map((m) => m[0]);
const invisible = (value: string) => {
    const rgba = parseColor(value);
    return rgba ? rgba.alpha < 0.001 : value === 'transparent' || value === '';
};

interface OwnRule {
    selector: string;
    property: string;
}

/** The Lab's own specialisation rules, to tell when one sets a property right now. */
function ownElementRules(): OwnRule[] {
    const out: OwnRule[] = [];
    const style = document.getElementById(ELEMENT_STYLE_ID) as HTMLStyleElement | null;
    const walk = (list: CSSRuleList): void => {
        for (const rule of Array.from(list)) {
            if (rule instanceof CSSStyleRule) for (let i = 0; i < rule.style.length; i++) out.push({selector: rule.selectorText, property: rule.style[i]});
            else if (rule instanceof CSSGroupingRule) walk(rule.cssRules);
        }
    };
    try {
        if (style?.sheet) walk(style.sheet.cssRules);
    } catch {
        // unreadable: no override reported
    }
    return out;
}

const sets = (longhand: string, property: string) => longhand === property || (property === 'border-color' && /^border-(top|right|bottom|left)-color$/.test(longhand));

interface Context {
    matchOf: (el: Element) => Match[];
    own: OwnRule[];
    picked: Element;
}

function build(ctx: Context, property: string, observed: Element, depth: number, candidates: Candidate[], winner: number): PickedProperty {
    const style = getComputedStyle(observed);
    const computed = style.getPropertyValue(property).trim();
    const declarations = candidates.map((c, i) => ({...c.decl, wins: i === winner}));
    if (winner > 0) declarations.unshift(...declarations.splice(winner, 1));
    const winnerValue = winner >= 0 ? candidates[winner].decl.value : '';
    const currentColor = property !== 'color' && (/currentcolor/i.test(winnerValue) || (winner < 0 && computed === style.getPropertyValue('color').trim()));
    const ancestor = depth > 0 ? (observed.hasAttribute('data-testid') ? observed : nearestTestid(observed)) : null;
    const ancestorId = ancestor?.getAttribute('data-testid');
    // Specialise where the colour is declared while that stays inside the picked element's component: a text colour
    // declared on its `th`, a card background. Above it (the page, `body`), the picked element itself.
    const root = nearestTestid(ctx.picked);
    const atAncestor = observed !== ctx.picked && root !== null && root.contains(observed);
    const target = atAncestor ? observed : ctx.picked;
    const winnerSelector = winner >= 0 ? candidates[winner].decl.selector : null;
    const {selector, breadth} = componentSelector(target, index, (name) => selectorNames(winnerSelector, name));
    return {
        property,
        computed,
        colors: colorsOf(computed),
        depth,
        ancestor_tag: depth > 0 ? observed.tagName.toLowerCase() : null,
        ancestor_testid: ancestorId ? codeTestid(ancestorId, index) : null,
        declarations,
        proved: winner >= 0,
        current_color: currentColor,
        lab_override: ctx.own.some((r) => sets(r.property, property) && (matchesSafe(ctx.picked, r.selector) || matchesSafe(observed, r.selector))),
        selector,
        breadth,
        matches: countMatches(selector),
        at_ancestor: atAncestor,
    };
}

/** A property set on the element itself (or, for an inherited one, on the nearest ancestor that declares it). */
function analyse(ctx: Context, el: Element, property: string): PickedProperty {
    let depth = 0;
    for (let cur: Element | null = el; cur; cur = cur.parentElement, depth++) {
        const candidates = candidatesOf(cur, property, ctx.matchOf(cur));
        if (candidates.some((c) => !c.decl.state)) {
            const winner = prove(cur, property, candidates);
            const value = winner >= 0 ? candidates[winner].decl.value.trim() : '';
            // `inherit` (Tailwind's preflight writes `color: inherit` on buttons and inputs) hands the colour to the parent.
            const inherits = /^(inherit|unset)$/i.test(value) || (property === 'color' && /^currentcolor$/i.test(value));
            if (!(inherits && INHERITED_COLOR_PROPERTIES.has(property))) return build(ctx, property, cur, depth, candidates, winner);
        } else if (!INHERITED_COLOR_PROPERTIES.has(property)) break;
    }
    return build(ctx, property, el, 0, [], -1);
}

function analyseAll(ctx: Context, el: Element): PickedProperty[] {
    const out: PickedProperty[] = [analyse(ctx, el, 'color')];
    const cs = getComputedStyle(el);

    // The background the designer sees: the element's, or the first ancestor's that is not transparent.
    let bg: Element | null = el;
    let depth = 0;
    while (bg && invisible(getComputedStyle(bg).backgroundColor) && getComputedStyle(bg).backgroundImage === 'none') {
        bg = bg.parentElement;
        depth++;
    }
    if (bg) {
        const bgStyle = getComputedStyle(bg);
        for (const property of ['background-color', 'background-image']) {
            const visible = property === 'background-color' ? !invisible(bgStyle.backgroundColor) : colorsOf(bgStyle.backgroundImage).length > 0;
            if (!visible) continue;
            const candidates = candidatesOf(bg, property, ctx.matchOf(bg));
            out.push(build(ctx, property, bg, depth, candidates, prove(bg, property, candidates)));
        }
    }

    const sides: PickedProperty[] = [];
    for (const side of BORDER_SIDES) {
        if (parseFloat(cs.getPropertyValue(`border-${side}-width`)) > 0 && !/^(none|hidden)$/.test(cs.getPropertyValue(`border-${side}-style`))) sides.push(analyse(ctx, el, `border-${side}-color`));
    }
    const same = (a: PickedProperty, b: PickedProperty) => a.computed === b.computed && a.declarations[0]?.selector === b.declarations[0]?.selector && a.declarations[0]?.value === b.declarations[0]?.value;
    if (sides.length === 4 && sides.every((s) => same(s, sides[0]))) out.push({...sides[0], property: 'border-color'});
    else out.push(...sides);

    if (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) out.push(analyse(ctx, el, 'outline-color'));
    if (cs.textDecorationLine !== 'none') out.push(analyse(ctx, el, 'text-decoration-color'));
    if (el instanceof SVGElement) {
        for (const property of ['fill', 'stroke']) if (cs.getPropertyValue(property) !== 'none') out.push(analyse(ctx, el, property));
    }
    if (cs.boxShadow !== 'none' && colorsOf(cs.boxShadow).length) {
        const candidates = candidatesOf(el, 'box-shadow', ctx.matchOf(el));
        out.push(build(ctx, 'box-shadow', el, 0, candidates, prove(el, 'box-shadow', candidates)));
    }
    return out;
}

/** Run `work` with transitions off and every style flushed before and after, so no probe is painted or animated. */
function withoutTransitions<T>(work: () => T): T {
    const style = document.createElement('style');
    style.setAttribute(OWN_ATTR, '');
    style.textContent = '*, *::before, *::after { transition: none !important; }';
    document.head.appendChild(style);
    void getComputedStyle(document.documentElement).color;
    try {
        return work();
    } finally {
        void getComputedStyle(document.documentElement).color;
        style.remove();
    }
}

async function chartOf(el: Element, point: {x: number; y: number}): Promise<PickedChart | null> {
    const host = el.closest('[_echarts_instance_]');
    if (!(host instanceof HTMLElement)) return null;
    const rect = host.getBoundingClientRect();
    const owner = nearestTestid(host);
    const ownerId = owner?.getAttribute('data-testid');
    const selector = owner ? testidSelector(owner, index) : cssPath(host, index);
    return {
        host_testid: ownerId ? codeTestid(ownerId, index) : null,
        selector,
        matches: countMatches(selector),
        colors: await chartColorsAt(host),
        pointed: await chartColorAtPoint(host, point.x - rect.left, point.y - rect.top),
    };
}

/** Everything the Lab needs about `el`: where it is (test ids, CSS), its visible colours and what sets each one. */
export async function describeElement(el: Element, point: {x: number; y: number}): Promise<PickedElement> {
    const rules = collectRules();
    const cache = new Map<Element, Match[]>();
    const ctx: Context = {
        own: ownElementRules(),
        picked: el,
        matchOf: (node) => {
            let found = cache.get(node);
            if (!found) cache.set(node, (found = matchRules(node, rules)));
            return found;
        },
    };
    // A specialisation would win every probe: switch the Lab's own rules off while the page's are tried.
    const ownSheet = (document.getElementById(ELEMENT_STYLE_ID) as HTMLStyleElement | null)?.sheet ?? null;
    const properties = withoutTransitions(() => {
        if (ownSheet) ownSheet.disabled = true;
        try {
            return analyseAll(ctx, el);
        } finally {
            if (ownSheet) ownSheet.disabled = false;
        }
    });
    const {selector, breadth} = componentSelector(el, index);
    return {
        at: Date.now(),
        route: routeOf(location, page.route.id),
        theme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
        testids: testidChain(el, index),
        css_path: cssPath(el, index),
        element: {tag: el.tagName.toLowerCase(), classes: stableClasses(el), scope_class: scopeClass(el)},
        selector,
        breadth,
        matches: countMatches(selector),
        properties,
        chart: await chartOf(el, point),
    };
}
