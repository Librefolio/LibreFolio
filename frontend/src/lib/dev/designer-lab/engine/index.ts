/**
 * Designer Lab — the engines behind a state: L1 variables, L2 stylesheets, L3 charts, colour-vision simulation.
 *
 * Loaded by the client only when a saved state has an effect. `applyState(null)` (or a suspended state) undoes
 * everything; the module then stays loaded but idle.
 */

import {parseColor, colorKey} from '../color.js';
import {changesForTheme, hasEffect} from '../store';
import type {LabChange, LabState} from '../types';
import {applyCharts, reapplyAll, type ChartRule} from './charts';
import {applyCvd} from './cvd';
import {applyStylesheets, normalizeSelector, type LiteralRule, type SheetPlan} from './stylesheets';
import {resolveTarget} from './targets';
import {applyVars} from './vars';

let state: LabState | null = null;
let counts = {cssRules: 0, chartInstances: 0, varOverrides: 0};
let hits = new Map<string, number>();
let themeObserver: MutationObserver | null = null;
let lastDark = false;

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
    });
    themeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
}

export async function applyState(next: LabState | null): Promise<void> {
    state = hasEffect(next) ? next : null;
    const changes = state?.changes ?? [];
    hits = new Map();
    counts.varOverrides = applyVars(changes.filter((c) => c.layer === 'css-var'));
    applySheetsForTheme();
    const charts = await applyCharts({light: chartPlan(changes, false), dark: chartPlan(changes, true)});
    counts.chartInstances = charts.instances;
    for (const [id, n] of charts.hits) hits.set(id, n);
    applyCvd(state?.cvd ?? 'none');
    watchTheme(!!state);
}

export function isActive(): boolean {
    return state !== null;
}

export function stats(): {cssRules: number; chartInstances: number; varOverrides: number} {
    return {...counts};
}

/** How many declarations or chart colours each change touched in this tab (the Lab shows it next to the change). */
export function changeHits(): Map<string, number> {
    return new Map(hits);
}
