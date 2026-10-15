/**
 * Designer Lab — where a picked element is, said the way the project names things: its `data-testid` chain and CSS.
 * Never its text: an export must carry no data (a debug build can run on real data, `dev.py server --debug`). An id
 * the code templates (`filter-currency-row-${code}`) is written as its prefix (`filter-currency-row-*`), so the record
 * it names stays out too, and the selector reaches every instance of the component; an id the index does not know is
 * cut before its first token that looks like a record (`recordPrefix`). The route keeps its `[param]` segments.
 *
 * Pure DOM functions, testable in jsdom; the test-id index is a parameter (the picker passes the build's).
 */

import type {TestidIndex} from '../types';

const MAX_TESTIDS = 8;
/** Beyond this, more classes only make the selector longer, not more precise. */
const MAX_SELECTOR_LENGTH = 400;

const staticSets = new WeakMap<TestidIndex, Set<string>>();

/**
 * Without a match in the index (an id built in a script, or no index at all): the part of the id before the first
 * token that looks like a record — a whole number (`row-42`, `asset-row-42-menu`) or a token with a capital letter
 * (`kpi-gain-EUR`, a ticker, a name). The project writes test ids as lower-case kebab words, digits included
 * (`risk-l2-weight`), so neither form is a word of the code. Null when no token looks like one, or when what would be
 * left is shorter than three characters.
 */
export function recordPrefix(id: string): string | null {
    let prefix = '';
    for (const token of id.split(/(?<=[-_])/)) {
        if (/^\d+[-_]?$/.test(token) || /[A-Z]/.test(token)) return prefix.length >= 3 ? prefix : null;
        prefix += token;
    }
    return null;
}

/** The prefix of the templated id `id` is an instance of; null for a static id, or an unknown one that names no record. */
export function testidPrefix(id: string, index?: TestidIndex | null): string | null {
    if (index) {
        let statics = staticSets.get(index);
        if (!statics) staticSets.set(index, (statics = new Set(index.statics)));
        if (statics.has(id)) return null;
        const prefix = index.prefixes.find((p) => id.length > p.length && id.startsWith(p));
        if (prefix) return prefix;
    }
    return recordPrefix(id);
}

/** The id as the code writes it: itself when static, `prefix*` for an instance of a templated id. */
export function codeTestid(id: string, index?: TestidIndex | null): string {
    const prefix = testidPrefix(id, index);
    return prefix ? `${prefix}*` : id;
}

export function nearestTestid(el: Element | null): Element | null {
    return el?.closest('[data-testid]') ?? null;
}

/** Test ids from the element up, nearest first, as the code writes them. */
export function testidChain(el: Element, index?: TestidIndex | null): string[] {
    const ids: string[] = [];
    for (let cur: Element | null = el; cur && ids.length < MAX_TESTIDS; cur = cur.parentElement) {
        const id = cur.getAttribute('data-testid');
        if (id) ids.push(codeTestid(id, index));
    }
    return ids;
}

const attrValue = (value: string) => value.replace(/["\\]/g, '\\$&');

/** `[data-testid="x"]`, or `[data-testid^="row-"]` for an instance of a templated id. */
export function testidSelector(el: Element, index?: TestidIndex | null): string {
    const id = el.getAttribute('data-testid') ?? '';
    const prefix = testidPrefix(id, index);
    return prefix ? `[data-testid^="${attrValue(prefix)}"]` : `[data-testid="${attrValue(id)}"]`;
}

const SCOPE_CLASS = /^svelte-[a-z0-9]+$/;

/** The element's classes, without Svelte's per-build scope class. */
export function stableClasses(el: Element): string[] {
    return Array.from(el.classList).filter((c) => !SCOPE_CLASS.test(c));
}

export function scopeClass(el: Element): string | null {
    return Array.from(el.classList).find((c) => SCOPE_CLASS.test(c)) ?? null;
}

function escapeClass(name: string): string {
    return typeof CSS !== 'undefined' && typeof CSS.escape === 'function' ? CSS.escape(name) : name.replace(/[^\w-]/g, (ch) => `\\${ch}`);
}

const tagOf = (el: Element) => el.tagName.toLowerCase();

/** The element's own path below its nearest test id, positions included: this element, in every instance of a templated id. */
export function cssPath(el: Element, index?: TestidIndex | null): string {
    if (el.hasAttribute('data-testid')) return testidSelector(el, index);
    const root = nearestTestid(el.parentElement);
    const segments: string[] = [];
    for (let cur: Element | null = el; cur && cur !== root && cur !== document.body && cur !== document.documentElement; cur = cur.parentElement) {
        const node: Element = cur;
        let segment = tagOf(node);
        const siblings = node.parentElement ? Array.from(node.parentElement.children).filter((c) => c.tagName === node.tagName) : [];
        if (siblings.length > 1) segment += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        segments.unshift(segment);
    }
    return [root ? testidSelector(root, index) : 'body', ...segments].join(' > ');
}

/** Path segments below the test id a component selector keeps: a deeper element keeps its last ones. */
const MAX_PATH = 6;

/** `th.sorted`: the tag and the classes `keep` accepts (a class with a brace or `<` is left out). */
function tagWith(el: Element, keep: (name: string) => boolean): string {
    let out = tagOf(el);
    for (const name of stableClasses(el)) if (!/[{}<;]/.test(name) && keep(name)) out += `.${escapeClass(name)}`;
    return out;
}

/** Whether a selector names the class `name` (`.name`, not a longer class that starts with it). */
export function selectorNames(selector: string | null, name: string): boolean {
    if (!selector) return false;
    const token = `.${escapeClass(name)}`;
    for (let at = selector.indexOf(token); at !== -1; at = selector.indexOf(token, at + 1)) {
        if (!/[\w\\-]/.test(selector[at + token.length] ?? '')) return true;
    }
    return false;
}

/**
 * The selector of a specialisation: the element in every instance of its component (decision of 14/10) — the nearest
 * test id (its prefix for a templated one), then the element's place below it without positions, that is the same
 * node of the same template. Only the classes `keep` accepts are written — the picker keeps those the colour's own
 * rule names — so a layout or state class (`flex`, `sorted`) neither widens nor narrows it. Without a test id around,
 * the element's own path.
 */
export function componentSelector(el: Element, index?: TestidIndex | null, keep: (name: string) => boolean = () => false): {selector: string; breadth: 'component' | 'element'} {
    if (el.hasAttribute('data-testid')) return {selector: testidSelector(el, index), breadth: 'component'};
    const root = nearestTestid(el.parentElement);
    if (!root) return {selector: cssPath(el, index), breadth: 'element'};
    const segments: string[] = [];
    for (let cur: Element | null = el; cur && cur !== root; cur = cur.parentElement) segments.unshift(cur === el ? tagWith(cur, keep) : tagOf(cur));
    const head = testidSelector(root, index);
    const selector = segments.length <= MAX_PATH ? `${head} > ${segments.join(' > ')}` : `${head} ${segments.slice(-MAX_PATH).join(' > ')}`;
    return {selector: selector.length <= MAX_SELECTOR_LENGTH ? selector : `${head} ${tagWith(el, keep)}`, breadth: 'component'};
}

export function countMatches(selector: string, scope: ParentNode = document): number {
    try {
        return scope.querySelectorAll(selector).length;
    } catch {
        return 0;
    }
}

/**
 * The route without data: SvelteKit's route id when the picker knows it — dynamic segments stay `[param]`, so a
 * detail page gives `/assets/[id]`, never the record's id; route groups such as `(app)` are dropped — else the path;
 * and the dashboard tab when there is one.
 */
export function routeOf(location: Pick<Location, 'pathname' | 'search'>, routeId?: string | null): string {
    const path = routeId ? routeId.replace(/\/\([^/)]+\)/g, '') || '/' : location.pathname;
    const tab = new URLSearchParams(location.search).get('tab');
    return tab ? `${path}?tab=${encodeURIComponent(tab)}` : path;
}

/** A lucide icon's `<path>` means its `<svg>`: the icon is what the designer points at. */
export function retarget(el: Element): Element {
    const svg = el.closest('svg');
    return svg && svg !== el && /\blucide\b/.test(svg.getAttribute('class') ?? '') ? svg : el;
}
