/**
 * Designer Lab — the engines behind a state: L1 variables, L2 stylesheets, L3 charts, the chart categories, colour-vision
 * simulation.
 *
 * Loaded by the client only when a saved state has an effect. `applyState(null)` (or a suspended state) undoes
 * everything; the module then stays loaded but idle.
 */

import {notifyChartColorsChange} from '$lib/theme/themeMode';
import {parseColor, colorKey} from '../color.js';
import {changesForTheme, hasEffect} from '../store';
import type {LabChange, LabState, LabStats} from '../types';
import {applyElementRules} from './anchors';
import {setCategoryChanges} from './categories';
import {applyCharts, reapplyAll, type AnchoredChartRule, type ChartRule} from './charts';
import {applyCvd} from './cvd';
import {applyStylesheets, normalizeSelector, variableRewrites, type LiteralRule, type SheetPlan} from './stylesheets';
import {isSafeSelector, resolveTarget} from './targets';
import {applyVars} from './vars';

export {categoryColor} from './categories';

let state: LabState | null = null;
let counts: LabStats = {cssRules: 0, chartInstances: 0, varOverrides: 0, elementRules: 0, categoryOverrides: 0};
let hits = new Map<string, number>();
let themeObserver: MutationObserver | null = null;
let lastDark = false;
/**
 * What the charts read at their next draw: the variables of the state (a role through `chartRoles`), its categories,
 * and the variables the stylesheet pass rewrote — a literal inside a role's definition changes the role too.
 */
function chartInputsOf(changes: LabChange[]): string {
    return JSON.stringify([changes.filter((c) => c.layer === 'css-var' || c.layer === 'category').map((c) => [c.id, c.to]), variableRewrites()]);
}
let chartInputs = chartInputsOf([]);

const isDark = () => document.documentElement.classList.contains('dark');

/** The colour key a literal change targets, whatever notation the designer or the catalogue wrote it in. */
function keyOf(change: LabChange): string | null {
    const rgba = parseColor(change.target);
    return rgba ? colorKey(rgba) : change.target.startsWith('oklch(') ? change.target : null;
}

function sheetPlan(changes: LabChange[]): SheetPlan {
    const literals = new Map<string, LiteralRule[]>();
    const vars = new Map<string, {changeId: string; value: string}>();
    for (const c of changes) {
        if (c.layer === 'css-var') {
            vars.set(c.target, {changeId: c.id, value: c.to});
            continue;
        }
        if (c.layer !== 'css-literal') continue;
        const key = keyOf(c);
        const target = resolveTarget(c.to);
        if (!key || !target) continue;
        const rule: LiteralRule = {changeId: c.id, target, alphaVariants: c.alphaVariants !== false};
        const match = c.match;
        if (match) rule.match = {selector: normalizeSelector(match.selector), property: match.property};
        const list = literals.get(key) ?? [];
        if (rule.match) list.unshift(rule);
        else list.push(rule);
        literals.set(key, list);
    }
    return {literals, vars};
}

function chartPlan(changes: LabChange[], dark: boolean): Map<string, ChartRule> {
    const plan = new Map<string, ChartRule>();
    for (const c of changesForTheme(changes, dark)) {
        if (c.layer !== 'chart-color') continue;
        const key = keyOf(c);
        const target = resolveTarget(c.to);
        if (key && target) plan.set(key, {changeId: c.id, target, alphaVariants: c.alphaVariants !== false});
    }
    return plan;
}

/** Chart specialisations: one colour, only in the charts the selector reaches. */
function chartAnchors(changes: LabChange[], dark: boolean): AnchoredChartRule[] {
    const rules: AnchoredChartRule[] = [];
    for (const c of changesForTheme(changes, dark)) {
        if (c.layer !== 'element' || c.property !== 'chart' || !c.colorKey || !isSafeSelector(c.target)) continue;
        const target = resolveTarget(c.to);
        if (target) rules.push({changeId: c.id, target, alphaVariants: true, key: c.colorKey, selector: c.target});
    }
    return rules;
}

function applySheetsForTheme(): void {
    const changes = state ? changesForTheme(state.changes, isDark()) : [];
    const result = applyStylesheets(changes.length ? sheetPlan(changes) : null);
    counts.cssRules = result.count;
    for (const [id, n] of result.hits) hits.set(id, n);
}

/** Re-plan the theme-dependent engines when `<html>` switches between light and dark. Only while a state is active. */
function watchTheme(active: boolean): void {
    if (!active) {
        themeObserver?.disconnect();
        themeObserver = null;
        return;
    }
    if (themeObserver) return;
    lastDark = isDark();
    themeObserver = new MutationObserver(() => {
        const dark = isDark();
        if (dark === lastDark) return;
        lastDark = dark;
        applySheetsForTheme();
        // Charts that redraw on a theme switch map their new option through the wrapper; the others are patched here.
        counts.chartInstances = reapplyAll();
        // A literal scoped to one theme rewrites a role's definition only in that theme: once the stylesheets are
        // re-planned, the charts that read a role must read it again, whatever order the theme observers ran in.
        signalChartInputs();
    });
    themeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
}

/**
 * Contract C4: the charts that read a role (`chartRoles`) or a category (`categoryColor`) when they draw rebuild their
 * option when what they read changed — a variable, a category or a role's definition applied, edited, suspended or
 * reset. Called once the other engines are in place, so that the redraw meets them.
 */
function signalChartInputs(): void {
    const inputs = chartInputsOf(state?.changes ?? []);
    if (inputs === chartInputs) return;
    chartInputs = inputs;
    notifyChartColorsChange();
}

export async function applyState(next: LabState | null): Promise<void> {
    state = hasEffect(next) ? next : null;
    const changes = state?.changes ?? [];
    hits = new Map();
    counts.varOverrides = applyVars(changes.filter((c) => c.layer === 'css-var'));
    counts.categoryOverrides = setCategoryChanges(changes);
    counts.elementRules = applyElementRules(changes.filter((c) => c.layer === 'element'));
    applySheetsForTheme();
    const charts = await applyCharts({light: chartPlan(changes, false), dark: chartPlan(changes, true), anchoredLight: chartAnchors(changes, false), anchoredDark: chartAnchors(changes, true)});
    // Without a state the pass only put the original colours back: nothing is changed any more.
    counts.chartInstances = state ? charts.instances : 0;
    for (const [id, n] of charts.hits) hits.set(id, n);
    applyCvd(state?.cvd ?? 'none');
    watchTheme(!!state);
    signalChartInputs();
}

export function isActive(): boolean {
    return state !== null;
}

export function stats(): LabStats {
    return {...counts};
}

/** How many declarations or chart colours each change touched in this tab (the Lab shows it next to the change). */
export function changeHits(): Map<string, number> {
    return new Map(hits);
}
