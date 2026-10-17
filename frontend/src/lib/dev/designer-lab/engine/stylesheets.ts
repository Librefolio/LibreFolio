/**
 * Designer Lab — L2: colours written in stylesheets (component `<style>` blocks, `app.css`, Tailwind arbitrary
 * classes), rewritten in the CSSOM of the page, plus the CSS variables a component defines for its own elements.
 *
 * Matching is by colour, never by text: the CSSOM serialises `#64748b` as `rgb(100, 116, 139)` and expands
 * shorthands into longhands (step 0 spike). Every rewritten declaration keeps its priority and its original text, so
 * a new plan, or none, starts from the page as it was. Stylesheets inserted later — SvelteKit loads CSS per route —
 * are rewritten as they arrive, for as long as a plan is active.
 */

import {colorKey, COLOR_TOKEN_RE, parseColor} from '../color.js';
import {OWN_ATTR} from './vars';
import {cssWithAlpha, type Target} from './targets';

export interface LiteralRule {
    changeId: string;
    target: Target;
    alphaVariants: boolean;
    /** Restrict to one occurrence: the rule's selector and property, as the catalogue recorded them. */
    match?: {selector: string; property: string | null};
}

export interface SheetPlan {
    /** Colour key → rules, single-occurrence rules first. */
    literals: Map<string, LiteralRule[]>;
    /** Variable name → value, for the rules that define it on component elements. */
    vars: Map<string, {changeId: string; value: string}>;
}

interface Saved {
    style: CSSStyleDeclaration;
    prop: string;
    value: string;
    priority: string;
}

let saved: Saved[] = [];
let plan: SheetPlan | null = null;
let hits = new Map<string, number>();
let headObserver: MutationObserver | null = null;

// Selectors that define a variable for the whole page: L1 overrides those on `<html>`, so their rules are left alone.
// Same list as ROOT_SELECTOR_RE in frontend/scripts/designer-lab/scan-colors.mjs, which sets a variable's `scope`:
// change both together.
const ROOT_SELECTOR = /^(:root|html|:host|html\.(light|dark)|\.dark|\.light|html:not\(\.(dark|light)\))$/;

/** A selector as the source writes it and as the CSSOM serialises it, made comparable. */
export function normalizeSelector(selector: string): string {
    let s = selector.replace(/\.svelte-[a-z0-9]+/g, '');
    for (let i = 0; i < 4 && s.includes(':global'); i++) s = s.replace(/:global\(([^()]*(?:\([^()]*\))*[^()]*)\)/g, '$1').replace(/:global\s+/g, '');
    return s
        .replace(/\s*([>+~,])\s*/g, '$1')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
}

function isRootRule(rule: CSSStyleRule): boolean {
    return rule.selectorText.split(',').every((s) => ROOT_SELECTOR.test(s.trim()));
}

function propertyMatches(prop: string, wanted: string | null): boolean {
    return wanted === null || prop === wanted || prop.startsWith(wanted + '-');
}

function replaceLiterals(value: string, rule: CSSStyleRule, prop: string, literals: Map<string, LiteralRule[]>): string {
    if (!/#|rgb|hsl|oklch|oklab|color\(/i.test(value)) return value;
    return value.replace(COLOR_TOKEN_RE, (raw) => {
        const rgba = parseColor(raw);
        if (!rgba) return raw;
        const candidates = literals.get(colorKey(rgba));
        if (!candidates) return raw;
        for (const c of candidates) {
            if (rgba.alpha < 0.9995 && !c.alphaVariants) continue;
            if (c.match && !(normalizeSelector(rule.selectorText) === c.match.selector && propertyMatches(prop, c.match.property))) continue;
            hits.set(c.changeId, (hits.get(c.changeId) ?? 0) + 1);
            return cssWithAlpha(c.target, rgba.alpha);
        }
        return raw;
    });
}

function applyRule(rule: CSSStyleRule, current: SheetPlan): void {
    const style = rule.style;
    const pending: [string, string, string][] = [];
    for (let i = 0; i < style.length; i++) {
        const prop = style[i];
        const value = style.getPropertyValue(prop);
        let next = value;
        if (prop.startsWith('--')) {
            const v = current.vars.get(prop);
            if (v && !isRootRule(rule)) {
                next = v.value;
                hits.set(v.changeId, (hits.get(v.changeId) ?? 0) + 1);
            } else if (current.literals.size) next = replaceLiterals(value, rule, prop, current.literals);
        } else if (current.literals.size) next = replaceLiterals(value, rule, prop, current.literals);
        if (next !== value) pending.push([prop, value, next]);
    }
    for (const [prop, value, next] of pending) {
        const priority = style.getPropertyPriority(prop);
        saved.push({style, prop, value, priority});
        style.setProperty(prop, next, priority);
    }
}

function walk(rules: CSSRuleList, current: SheetPlan): void {
    for (const rule of Array.from(rules)) {
        if (rule instanceof CSSStyleRule) applyRule(rule, current);
        const nested = (rule as CSSRule & {cssRules?: CSSRuleList}).cssRules;
        if (nested?.length) walk(nested, current);
    }
}

function applySheet(sheet: CSSStyleSheet, current: SheetPlan): void {
    const owner = sheet.ownerNode;
    if (owner instanceof Element && owner.hasAttribute(OWN_ATTR)) return;
    let rules: CSSRuleList;
    try {
        rules = sheet.cssRules;
    } catch {
        return; // not readable (another origin)
    }
    walk(rules, current);
}

function restore(): void {
    for (let i = saved.length - 1; i >= 0; i--) {
        const s = saved[i];
        s.style.setProperty(s.prop, s.value, s.priority);
    }
    saved = [];
}

/**
 * The variables the pass rewrote, rule by rule, with their value now: a literal inside a variable's definition (every
 * `--lf-*` role of `tokens.css` is written as one) or a variable a component defines. A chart that reads a role when it
 * draws (`chartRoles`) meets them, so the engine compares them for contract C4.
 */
export function variableRewrites(): string[] {
    const out: string[] = [];
    for (const s of saved) {
        if (!s.prop.startsWith('--')) continue;
        const selector = (s.style.parentRule as CSSStyleRule | null)?.selectorText ?? '';
        out.push(`${selector}|${s.prop}|${s.style.getPropertyValue(s.prop).trim()}`);
    }
    return out.sort();
}

/** The value a declaration had before the Lab rewrote it, or null when the Lab has not touched it (element picker). */
export function originalValue(style: CSSStyleDeclaration, prop: string): string | null {
    for (const s of saved) if (s.style === style && s.prop === prop) return s.value;
    return null;
}

function watchHead(): void {
    if (headObserver) return;
    headObserver = new MutationObserver((records) => {
        if (!plan) return;
        for (const record of records) {
            for (const node of Array.from(record.addedNodes)) {
                if (node instanceof HTMLLinkElement && node.rel === 'stylesheet') {
                    const current = plan;
                    const onLoad = () => node.sheet && plan === current && applySheet(node.sheet, current);
                    if (node.sheet) onLoad();
                    else node.addEventListener('load', onLoad, {once: true});
                } else if (node instanceof HTMLStyleElement && node.sheet) applySheet(node.sheet, plan);
            }
        }
    });
    headObserver.observe(document.head, {childList: true});
}

/**
 * Restore every declaration rewritten so far, then apply `next` to every stylesheet of the page. Returns the number of
 * declarations rewritten and, per change, how many it touched.
 */
export function applyStylesheets(next: SheetPlan | null): {count: number; hits: Map<string, number>} {
    restore();
    hits = new Map();
    plan = next && (next.literals.size || next.vars.size) ? next : null;
    if (!plan) {
        headObserver?.disconnect();
        headObserver = null;
        return {count: 0, hits};
    }
    for (const sheet of Array.from(document.styleSheets)) applySheet(sheet, plan);
    watchHead();
    return {count: saved.length, hits};
}
