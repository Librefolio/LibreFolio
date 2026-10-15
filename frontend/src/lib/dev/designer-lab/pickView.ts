/**
 * Designer Lab — what the Lab makes of a picked element. For each colour the app tab reported: the source that sets
 * it in the code (a variable, a Tailwind class, a stylesheet rule, an inline style…), what editing that shared source
 * means, the specialisation of the element alone, and the places in the code where an agent would bind it. Pure
 * functions over the catalogue and the reported facts.
 */

import {COLOR_TOKEN_RE, colorKey, parseColor} from './color.js';
import {sourceVarValue} from './catalogView';
import {declares, ELEMENT_PROPERTIES} from './cssProps';
import {normalizeSelector} from './engine/stylesheets';
import type {CatalogLiteral, ColorCatalog, LabAnchor, LabAnchorCandidate, LabSelection, PickedDeclaration, PickedElement, PickedProperty, SourceKind} from './types';

const VAR_RE = /var\(\s*(--[\w-]+)/;
/** Tailwind v4 writes its utilities in the cascade layer `utilities`. */
const UTILITY_LAYER = /(^|\.)utilities$/;
const DARK_ONLY = /(^|[\s,(>+~])html\.dark\b/;
const MAX_CHAIN = 6;
const MAX_CANDIDATES = 12;
/** A class or variable used in more places than this is no anchor by itself: only its uses near the test ids count. */
const MAX_LOOSE_SITES = 6;

export interface PropertyView {
    property: string;
    computed: string;
    /** The colour keys of the computed value. */
    keys: string[];
    depth: number;
    ancestorTag: string | null;
    ancestorTestid: string | null;
    kind: SourceKind;
    winner: PickedDeclaration | null;
    /** The variable the winning declaration reads, then the variables it is defined with in the picked theme. */
    varChain: string[];
    /** The Tailwind utility that sets the colour (`text-gray-500`, `dark:bg-slate-800`). */
    className: string | null;
    /** A Tailwind utility the winning declaration overrides (an `app.css` dark override on top of a class). */
    overriddenClass: string | null;
    /** The catalogue occurrences of the winning stylesheet colour. */
    literals: CatalogLiteral[];
    /** The winner is an `!important` rule for the dark theme: an override of `app.css` (P1). */
    darkOverride: boolean;
    labOverride: boolean;
    /** The value is `currentColor`: editing `color` changes it. */
    followsColor: boolean;
    /** Editing the shared source: every element that uses it changes. Null when there is nothing to edit live. */
    edit: LabSelection | null;
    /** The specialisation of the picked element (every instance of its component). Null when it cannot be specialised. */
    specialise: LabSelection | null;
    candidates: LabAnchorCandidate[];
}

export interface ChartColorView {
    color: string;
    key: string;
    pointed: boolean;
    edit: LabSelection;
    specialise: LabSelection;
}

export interface ChartView {
    hostTestid: string | null;
    selector: string;
    matches: number;
    colors: ChartColorView[];
}

/** What the lists keep when filtered on the picked element. */
export interface PickFilter {
    vars: Set<string>;
    keys: Set<string>;
}

export interface PickView {
    element: PickedElement;
    properties: PropertyView[];
    chart: ChartView | null;
    filter: PickFilter;
}

/** The grouping key of a CSS colour (`#rrggbb`, or `oklch(…)` outside sRGB), or null when it is not a colour. */
export function keyOfColor(value: string): string | null {
    const rgba = parseColor(value.trim());
    return rgba ? colorKey(rgba) : null;
}

/** The keys of the colours a value contains (a shadow or a gradient has several). */
export function keysOf(value: string): string[] {
    const whole = keyOfColor(value);
    if (whole) return [whole];
    const keys = [...value.matchAll(COLOR_TOKEN_RE)].map((m) => keyOfColor(m[0])).filter((k): k is string => k !== null);
    return [...new Set(keys)];
}

/** The first class of a selector, unescaped: `.dark\:text-gray-400:where(.dark, .dark *)` → `dark:text-gray-400`. */
export function firstClass(selector: string | null): string | null {
    const m = selector ? /\.((?:\\[0-9a-fA-F]{1,6}\s?|\\.|[\w-])+)/.exec(selector) : null;
    if (!m) return null;
    return m[1].replace(/\\([0-9a-fA-F]{1,6})\s?|\\(.)/g, (_, hex: string | undefined, ch: string | undefined) => (hex ? String.fromCodePoint(parseInt(hex, 16)) : (ch ?? '')));
}

/** The variable, then what it is defined with in the theme, as far as the app's sources define it. */
export function varChain(catalog: ColorCatalog, name: string, dark: boolean): string[] {
    const chain = [name];
    for (let i = 0; i < MAX_CHAIN; i++) {
        const next = VAR_RE.exec(sourceVarValue(catalog, chain[chain.length - 1], dark, ''))?.[1];
        if (!next || chain.includes(next)) break;
        chain.push(next);
    }
    return chain;
}

interface Classified {
    kind: SourceKind;
    winner: PickedDeclaration | null;
    varName: string | null;
    className: string | null;
}

export function classify(p: PickedProperty): Classified {
    const winner = p.proved ? (p.declarations.find((d) => d.wins) ?? null) : null;
    if (!winner) return {kind: p.current_color ? 'current-color' : 'unknown', winner: null, varName: null, className: null};
    if (p.current_color && /currentcolor/i.test(winner.value)) return {kind: 'current-color', winner, varName: null, className: null};
    if (winner.origin === 'inline') return {kind: 'inline', winner, varName: VAR_RE.exec(winner.value)?.[1] ?? null, className: null};
    if (winner.origin === 'attribute') return {kind: 'attribute', winner, varName: null, className: null};
    const varName = VAR_RE.exec(winner.value)?.[1] ?? null;
    if (winner.layer !== null && UTILITY_LAYER.test(winner.layer)) return {kind: 'tailwind-class', winner, varName, className: firstClass(winner.selector)};
    return {kind: varName ? 'var' : 'rule-literal', winner, varName, className: null};
}

const fileIndexes = (catalog: ColorCatalog, files: Set<string>) => new Set([...files].map((f) => catalog.files.indexOf(f)).filter((i) => i >= 0));

/** Where the code writes the test ids of the chain: the nearest id the catalogue knows, static or templated (`prefix*`). */
export function testidSites(catalog: ColorCatalog, testids: string[]): LabAnchorCandidate[] {
    for (const id of testids) {
        const out: LabAnchorCandidate[] = [];
        if (id.endsWith('*')) {
            // A templated id, or one the picker cut before a record-like token: the longest catalogue prefix it extends.
            const prefix = id.slice(0, -1);
            const known = catalog.testid_prefixes.reduce<string | null>((best, [p]) => (prefix.startsWith(p) && p.length > (best?.length ?? -1) ? p : best), null);
            if (known) for (const [p, f, line] of catalog.testid_prefixes) if (p === known) out.push({file: catalog.files[f], line, why: 'testid', needle: p});
        } else {
            for (const [f, line] of catalog.testids[id] ?? []) out.push({file: catalog.files[f], line, why: 'testid', needle: id});
            // An id of the page the scanner saw only as a template (`tab-${id}`).
            if (!out.length) {
                const prefix = catalog.testid_prefixes.find(([p]) => id.length > p.length && id.startsWith(p));
                if (prefix) for (const [p, f, line] of catalog.testid_prefixes) if (p === prefix[0]) out.push({file: catalog.files[f], line, why: 'testid', needle: p});
            }
        }
        if (out.length) return out.slice(0, 4);
    }
    return [];
}

/** The catalogue occurrences of the winning rule's colour: same colour, same rule, a declaration of the property. */
export function ruleLiterals(catalog: ColorCatalog, winner: PickedDeclaration, property: string, nearFiles: Set<number>): CatalogLiteral[] {
    const keys = new Set(keysOf(winner.value));
    if (!keys.size) return [];
    const of = (l: CatalogLiteral) => l.layer === 'css-literal' && !!l.key && keys.has(l.key) && declares(l.property, property);
    const selector = winner.selector ? normalizeSelector(winner.selector) : null;
    const bySelector = selector ? catalog.literals.filter((l) => of(l) && l.selector && normalizeSelector(l.selector) === selector) : [];
    const near = bySelector.filter((l) => nearFiles.has(l.file));
    if (near.length) return near;
    if (bySelector.length) return bySelector.slice(0, MAX_LOOSE_SITES);
    // Nested or wrapped rules do not compare: the colour in the component's files.
    return catalog.literals.filter((l) => of(l) && nearFiles.has(l.file)).slice(0, MAX_LOOSE_SITES);
}

function classSites(catalog: ColorCatalog, className: string, varName: string | null, nearFiles: Set<number>): LabAnchorCandidate[] {
    // The class reads the variable directly (`text-gray-500`, `--color-gray-500`) or through an inline alias
    // (`bg-lf-card` → `--color-lf-card` → `--lf-surface-card`, the role the utility really reads).
    const entry = varName ? catalog.palette.find((p) => (p.var === varName || p.role === varName) && Object.keys(p.classes).includes(className)) : undefined;
    if (!entry) return [];
    const names = Object.keys(entry.classes);
    const index = names.indexOf(className);
    if (index === -1) return [];
    const uses = entry.occ.filter(([, , c]) => c === index);
    const near = uses.filter(([f]) => nearFiles.has(f));
    const chosen = near.length ? near : uses.length <= MAX_LOOSE_SITES ? uses : [];
    return chosen.map(([f, line]) => ({file: catalog.files[f], line, why: 'class-use' as const, needle: className}));
}

function varSites(catalog: ColorCatalog, name: string, selector: string | null, nearFiles: Set<number>): LabAnchorCandidate[] {
    const sites = catalog.css_vars.find((v) => v.name === name)?.use_sites ?? [];
    const wanted = selector ? normalizeSelector(selector) : null;
    const bySelector = wanted ? sites.filter(([, , s]) => s && normalizeSelector(s) === wanted) : [];
    const near = sites.filter(([f]) => nearFiles.has(f));
    const chosen = bySelector.length ? bySelector : near.length ? near : sites.length <= MAX_LOOSE_SITES ? sites : [];
    return chosen.map(([f, line]) => ({file: catalog.files[f], line, why: 'var-use' as const, needle: name}));
}

function markupSites(catalog: ColorCatalog, keys: string[], nearFiles: Set<number>): LabAnchorCandidate[] {
    const all = catalog.literals.filter((l) => l.key && keys.includes(l.key) && l.zone === 'svelte-markup');
    const near = all.filter((l) => nearFiles.has(l.file));
    const chosen = near.length ? near : all.length <= MAX_LOOSE_SITES ? all : [];
    return chosen.map((l) => ({file: catalog.files[l.file], line: l.line, why: 'literal' as const, needle: l.raw}));
}

function dedupe(list: LabAnchorCandidate[]): LabAnchorCandidate[] {
    const seen = new Set<string>();
    return list.filter((c) => {
        const k = `${c.file}:${c.line}:${c.why}`;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
    });
}

/** The anchor of a change decided on the picked element: where it is, what sets the colour, where to bind it. */
export function buildAnchor(element: PickedElement, view: Pick<PropertyView, 'property' | 'computed' | 'kind' | 'winner' | 'varChain' | 'className' | 'candidates'>, selector = element.selector, matches = element.matches, breadth = element.breadth): LabAnchor {
    return {
        route: element.route,
        theme: element.theme,
        testids: element.testids,
        css_path: element.css_path,
        element: element.element,
        selector,
        breadth,
        matches,
        property: view.property,
        computed: view.computed,
        source: {kind: view.kind, selector: view.winner?.selector ?? null, var: view.varChain[0] ?? null, class: view.className},
        candidates: view.candidates,
    };
}

function propertyView(catalog: ColorCatalog, element: PickedElement, p: PickedProperty, nearFiles: Set<number>, testidCandidates: LabAnchorCandidate[]): PropertyView {
    const dark = element.theme === 'dark';
    const {kind, winner, varName, className} = classify(p);
    const chain = varName ? varChain(catalog, varName, dark) : [];
    const keys = [...new Set(p.colors.map((c) => keyOfColor(c)).filter((k): k is string => k !== null))];
    const literals = kind === 'rule-literal' && winner ? ruleLiterals(catalog, winner, p.property, nearFiles) : [];
    const overridden = p.declarations.find((d) => !d.wins && !d.state && d.layer !== null && UTILITY_LAYER.test(d.layer));

    const exact: LabAnchorCandidate[] = [];
    if (kind === 'rule-literal') exact.push(...literals.map((l) => ({file: catalog.files[l.file], line: l.line, why: 'matched-rule' as const, needle: l.raw})));
    if (kind === 'tailwind-class' && className) exact.push(...classSites(catalog, className, varName, nearFiles));
    if ((kind === 'var' || kind === 'tailwind-class') && varName && !exact.length) exact.push(...varSites(catalog, varName, kind === 'var' ? (winner?.selector ?? null) : null, nearFiles));
    if (kind === 'inline' || kind === 'attribute') exact.push(...markupSites(catalog, keys, nearFiles));
    const candidates = dedupe([...exact, ...testidCandidates]).slice(0, MAX_CANDIDATES);

    const winnerKey = winner ? (keysOf(winner.value)[0] ?? null) : null;
    let edit: LabSelection | null = null;
    if (varName) edit = {layer: 'css-var', target: varName};
    else if ((kind === 'rule-literal' || kind === 'tailwind-class') && winnerKey) edit = {layer: 'css-literal', target: winnerKey, ...(literals.length === 1 ? {occurrence: literals[0].id} : {})};
    else if ((kind === 'inline' || kind === 'attribute') && (winnerKey ?? keys[0])) edit = {layer: 'proposal', target: (winnerKey ?? keys[0]) as string};

    const view: PropertyView = {
        property: p.property,
        computed: p.computed,
        keys,
        depth: p.depth,
        ancestorTag: p.ancestor_tag ?? null,
        ancestorTestid: p.ancestor_testid,
        kind,
        winner,
        varChain: chain,
        className,
        overriddenClass: overridden && overridden !== winner ? firstClass(overridden.selector) : null,
        literals,
        darkOverride: !!winner?.important && DARK_ONLY.test(winner.selector ?? ''),
        labOverride: p.lab_override,
        followsColor: kind === 'current-color',
        edit,
        specialise: null,
        candidates,
    };
    // A background seen through from outside the component would only paint the picked element's own box.
    const own = !(p.property.startsWith('background') && p.depth > 0 && !p.at_ancestor);
    const selector = p.selector ?? element.selector;
    const matches = p.matches ?? element.matches;
    if (own && ELEMENT_PROPERTIES.includes(p.property)) {
        view.specialise = {layer: 'element', target: selector, property: p.property, from: p.computed, anchor: buildAnchor(element, view, selector, matches, p.breadth ?? element.breadth)};
    }
    if (edit) edit.anchor = buildAnchor(element, view, selector, matches, p.breadth ?? element.breadth);
    return view;
}

function chartView(catalog: ColorCatalog, element: PickedElement, nearFiles: Set<number>, testidCandidates: LabAnchorCandidate[]): ChartView | null {
    const chart = element.chart;
    if (!chart) return null;
    const pointedKey = chart.pointed ? keyOfColor(chart.pointed) : null;
    const seen = new Set<string>();
    const colors: ChartColorView[] = [];
    for (const color of chart.colors) {
        const key = keyOfColor(color);
        if (!key || seen.has(key)) continue;
        seen.add(key);
        const sites = catalog.literals.filter((l) => l.layer === 'chart-color' && l.key === key && nearFiles.has(l.file));
        const candidates = dedupe([...sites.map((l) => ({file: catalog.files[l.file], line: l.line, why: 'literal' as const, needle: l.raw})), ...testidCandidates]).slice(0, MAX_CANDIDATES);
        const base = {property: 'chart', computed: color, kind: 'chart' as const, winner: null, varChain: [], className: null, candidates};
        const anchor = buildAnchor(element, base, chart.selector, chart.matches);
        colors.push({
            color,
            key,
            pointed: key === pointedKey,
            edit: {layer: 'chart-color', target: key, anchor},
            specialise: {layer: 'element', target: chart.selector, property: 'chart', colorKey: key, from: color, anchor},
        });
    }
    colors.sort((a, b) => Number(b.pointed) - Number(a.pointed));
    return {hostTestid: chart.host_testid, selector: chart.selector, matches: chart.matches, colors};
}

/** Everything the Lab shows about a picked element. */
export function pickView(catalog: ColorCatalog, element: PickedElement): PickView {
    const testidCandidates = testidSites(catalog, element.testids);
    const nearFiles = fileIndexes(catalog, new Set(testidCandidates.map((c) => c.file)));
    const properties = element.properties.map((p) => propertyView(catalog, element, p, nearFiles, testidCandidates));
    const chart = chartView(catalog, element, nearFiles, testidCandidates);
    const vars = new Set<string>();
    const keys = new Set<string>();
    for (const v of properties) {
        for (const name of v.varChain) vars.add(name);
        for (const k of v.keys) keys.add(k);
        for (const l of v.literals) if (l.key) keys.add(l.key);
    }
    for (const c of chart?.colors ?? []) keys.add(c.key);
    // The colours the element would have without the winners, too: the class an `app.css` override hides, a hover state.
    for (const p of element.properties) {
        for (const d of p.declarations) {
            const name = VAR_RE.exec(d.value)?.[1];
            if (name) for (const v of varChain(catalog, name, element.theme === 'dark')) vars.add(v);
            for (const k of keysOf(d.value)) keys.add(k);
        }
    }
    // The palette lists a role's classes under their inline alias (`--color-lf-card` for `--lf-surface-card`).
    for (const p of catalog.palette) if (p.role && vars.has(p.role)) vars.add(p.var);
    return {element, properties, chart, filter: {vars, keys}};
}
