/**
 * Designer Lab — L3: colours of the ECharts options, which the app builds in JavaScript.
 *
 * Two mechanisms, both chosen by the step 0 spike:
 *   1. the shared prototype's `setOption` is wrapped, so every option an instance receives from now on — first render,
 *      theme switch, new data — has its colours mapped;
 *   2. the instances already on screen are updated in place: their current option is read back with `getOption()` and
 *      a patch holding only the changed colour properties is merged in (zoom and data are left alone). This covers
 *      the charts that never redraw on their own (5 of 17 do not redraw on a class change of `<html>`).
 *
 * Mapping is copy-on-write (the app's objects are never mutated) and reversible: every colour the engine writes is
 * remembered with the original it replaced, so a later plan, or none, starts from the app's own colours. Functions in
 * an option (`formatter`, `color`, `renderItem`) are wrapped once and map what they return with the plan in force at
 * call time.
 */

import {colorKey, COLOR_TOKEN_RE, parseColor} from '../color.js';
import {canvasString, type Target} from './targets';

type EChartsModule = typeof import('echarts');
type Instance = ReturnType<EChartsModule['init']>;
type AnyFn = (this: unknown, ...args: unknown[]) => unknown;

export interface ChartRule {
    changeId: string;
    target: Target;
    alphaVariants: boolean;
}

/** Colour key → rule, per theme; the theme in force is read when mapping, so a theme switch needs no re-plan. */
let plans: {light: Map<string, ChartRule>; dark: Map<string, ChartRule>} = {light: new Map(), dark: new Map()};
let echarts: EChartsModule | null = null;
let originalSetOption: AnyFn | null = null;
/** Every string the engine wrote → the original it replaced. */
const produced = new Map<string, string>();
const wrappers = new WeakMap<AnyFn, AnyFn>();
const isWrapper = new WeakSet<AnyFn>();
let hits = new Map<string, number>();

function activePlan(): Map<string, ChartRule> {
    return document.documentElement.classList.contains('dark') ? plans.dark : plans.light;
}

function planIsEmpty(): boolean {
    return plans.light.size === 0 && plans.dark.size === 0;
}

/** Map the colour tokens of a string; a token the engine wrote earlier is first turned back into its original. */
function mapString(s: string, plan: Map<string, ChartRule>): string {
    if (s.length > 20000 || !/#|rgb|hsl|oklch|oklab|color\(/i.test(s)) return s;
    return s.replace(COLOR_TOKEN_RE, (raw) => {
        const original = produced.get(raw) ?? raw;
        const rgba = parseColor(original);
        if (!rgba) return raw;
        const rule = plan.get(colorKey(rgba));
        if (!rule || (rgba.alpha < 0.9995 && !rule.alphaVariants)) return original;
        const out = canvasString(rule.target, rgba.alpha);
        if (!out) return original;
        produced.set(out, original);
        hits.set(rule.changeId, (hits.get(rule.changeId) ?? 0) + 1);
        return out;
    });
}

function wrap(fn: AnyFn): AnyFn {
    if (isWrapper.has(fn)) return fn;
    let w = wrappers.get(fn);
    if (!w) {
        w = function (this: unknown, ...args: unknown[]) {
            const result = fn.apply(this, args);
            return planIsEmpty() ? result : mapValue(result, activePlan(), new WeakMap());
        };
        wrappers.set(fn, w);
        isWrapper.add(w);
    }
    return w;
}

function isOpaqueObject(v: object): boolean {
    return ArrayBuffer.isView(v) || v instanceof Date || (typeof Node !== 'undefined' && v instanceof Node) || (typeof ImageBitmap !== 'undefined' && v instanceof ImageBitmap);
}

/** Copy-on-write deep map: returns the same object when nothing inside it changes. */
function mapValue(v: unknown, plan: Map<string, ChartRule>, seen: WeakMap<object, unknown>, depth = 0): unknown {
    if (typeof v === 'string') return mapString(v, plan);
    if (typeof v === 'function') return wrap(v as AnyFn);
    if (!v || typeof v !== 'object' || depth > 40 || isOpaqueObject(v)) return v;
    const memo = seen.get(v);
    if (memo !== undefined) return memo;
    seen.set(v, v);
    let out: unknown;
    if (Array.isArray(v)) {
        let copy: unknown[] | null = null;
        for (let i = 0; i < v.length; i++) {
            const item = v[i];
            if (item === null || typeof item === 'number' || typeof item === 'boolean' || item === undefined) continue;
            const mapped = mapValue(item, plan, seen, depth + 1);
            if (mapped !== item) (copy ??= v.slice())[i] = mapped;
        }
        out = copy ?? v;
    } else {
        let copy: Record<string, unknown> | null = null;
        const obj = v as Record<string, unknown>;
        for (const key of Object.keys(obj)) {
            const item = obj[key];
            if (item === null || typeof item === 'number' || typeof item === 'boolean' || item === undefined) continue;
            const mapped = mapValue(item, plan, seen, depth + 1);
            if (mapped !== item) (copy ??= Object.assign(Object.create(Object.getPrototypeOf(obj)), obj) as Record<string, unknown>)[key] = mapped;
        }
        out = copy ?? v;
    }
    seen.set(v, out);
    return out;
}

/**
 * The patch that brings an option read back with `getOption()` to the plan: only the paths whose colour changes.
 * Component lists at the root merge by index, so they get `{}` placeholders; every other array is replaced whole by
 * ECharts (`data`, `colorStops`, a palette), so a changed one is sent complete.
 */
function rootPatch(option: Record<string, unknown>, plan: Map<string, ChartRule>): Record<string, unknown> | null {
    const seen = new WeakMap<object, unknown>();
    let patch: Record<string, unknown> | null = null;
    for (const [key, value] of Object.entries(option)) {
        if (Array.isArray(value) && value.length && value.every((c) => c && typeof c === 'object' && !Array.isArray(c))) {
            let changed = false;
            const list = value.map((component) => {
                const p = objectPatch(component as Record<string, unknown>, plan, seen);
                if (p) changed = true;
                return p ?? {};
            });
            if (changed) (patch ??= {})[key] = list;
        } else {
            const mapped = mapValue(value, plan, seen);
            if (mapped !== value) (patch ??= {})[key] = mapped;
        }
    }
    return patch;
}

function objectPatch(obj: Record<string, unknown>, plan: Map<string, ChartRule>, seen: WeakMap<object, unknown>): Record<string, unknown> | null {
    let patch: Record<string, unknown> | null = null;
    for (const [key, value] of Object.entries(obj)) {
        if (value && typeof value === 'object' && !Array.isArray(value) && !isOpaqueObject(value) && !('colorStops' in value)) {
            const p = objectPatch(value as Record<string, unknown>, plan, seen);
            if (p) (patch ??= {})[key] = p;
        } else {
            const mapped = mapValue(value, plan, seen);
            if (mapped !== value) (patch ??= {})[key] = mapped;
        }
    }
    if (patch && obj.id !== undefined) patch.id = obj.id;
    return patch;
}

async function loadEcharts(): Promise<EChartsModule> {
    echarts ??= await import('echarts');
    return echarts;
}

function instances(): Instance[] {
    if (!echarts) return [];
    const found: Instance[] = [];
    for (const dom of Array.from(document.querySelectorAll<HTMLElement>('[_echarts_instance_]'))) {
        const inst = echarts.getInstanceByDom(dom);
        if (inst && !inst.isDisposed()) found.push(inst);
    }
    return found;
}

/** Wrap `setOption` on the prototype every instance shares (the app imports one `echarts` module). */
function install(ec: EChartsModule): void {
    if (originalSetOption) return;
    let probe: Instance | null = null;
    let sample = instances()[0];
    if (!sample) {
        const host = document.createElement('div');
        probe = ec.init(host, null, {width: 1, height: 1});
        sample = probe;
    }
    const proto = Object.getPrototypeOf(sample) as {setOption: AnyFn};
    const original = proto.setOption;
    originalSetOption = original;
    proto.setOption = function (this: unknown, option: unknown, ...rest: unknown[]) {
        const mapped = planIsEmpty() ? option : mapValue(option, activePlan(), new WeakMap());
        return original.call(this, mapped, ...rest);
    };
    probe?.dispose();
}

/** Apply the current plan to the instances on screen. Returns how many were patched. */
export function reapplyAll(): number {
    if (!originalSetOption) return 0;
    let patched = 0;
    for (const inst of instances()) {
        const patch = rootPatch(inst.getOption() as Record<string, unknown>, activePlan());
        if (!patch) continue;
        originalSetOption.call(inst, patch, {lazyUpdate: false});
        patched++;
    }
    return patched;
}

/** The option `setOption` receives under `plan` (copy-on-write: the same object when nothing changes). For tests. */
export function mapChartOption(option: unknown, plan: Map<string, ChartRule>): unknown {
    return mapValue(option, plan, new WeakMap());
}

/** The patch that brings an option read back with `getOption()` to `plan`, or null. For tests. */
export function chartPatch(option: Record<string, unknown>, plan: Map<string, ChartRule>): Record<string, unknown> | null {
    return rootPatch(option, plan);
}

/**
 * Set the plan (per theme) and bring every chart on screen to it. The prototype is wrapped on the first non-empty
 * plan; after that an empty plan makes the wrapper a pass-through and puts the original colours back.
 */
export async function applyCharts(next: {light: Map<string, ChartRule>; dark: Map<string, ChartRule>}): Promise<{instances: number; hits: Map<string, number>}> {
    plans = next;
    hits = new Map();
    if (planIsEmpty() && !originalSetOption) return {instances: 0, hits};
    install(await loadEcharts());
    return {instances: reapplyAll(), hits};
}

/** The distinct colours of the chart inside the first element matching `selector` (E2E and console aid). */
export async function chartColorsOf(selector: string): Promise<string[]> {
    const ec = await loadEcharts();
    const host = document.querySelector<HTMLElement>(selector);
    if (!host) return [];
    const dom = host.hasAttribute('_echarts_instance_') ? host : host.querySelector<HTMLElement>('[_echarts_instance_]');
    const inst = dom ? ec.getInstanceByDom(dom) : undefined;
    if (!inst) return [];
    const colors = new Set<string>();
    const collect = (v: unknown, depth: number): void => {
        if (depth > 40) return;
        if (typeof v === 'string') {
            if (parseColor(v)) colors.add(v);
        } else if (Array.isArray(v)) v.forEach((x) => collect(x, depth + 1));
        else if (v && typeof v === 'object' && !isOpaqueObject(v)) Object.values(v).forEach((x) => collect(x, depth + 1));
    };
    collect(inst.getOption(), 0);
    return [...colors];
}
