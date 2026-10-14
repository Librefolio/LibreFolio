/**
 * Designer Lab — shared types (debug-only tooling; see `design-designerLab.md`).
 *
 * `ColorCatalog` mirrors what `frontend/scripts/designer-lab/scan-colors.mjs` writes (`lf-color-catalog/1`);
 * `LabState` is what the Lab keeps in localStorage and what every tab re-applies.
 */

export type Zone = 'svelte-script' | 'svelte-style' | 'svelte-markup' | 'css-file' | 'ts' | 'static';
export type Layer = 'css-literal' | 'chart-color' | 'script' | 'markup' | 'static';
export type ThemeContext = 'light' | 'dark' | 'both';

export interface CatalogLiteral {
    id: number;
    /** Index into `ColorCatalog.files`. */
    file: number;
    line: number;
    col: number;
    raw: string;
    kind: 'hex' | 'fn' | 'mix';
    /** Grouping key (`#rrggbb`, or `oklch(…)` outside sRGB); null for expressions (`color-mix`, `var()`). */
    key: string | null;
    alpha: number | null;
    zone: Zone;
    theme: ThemeContext | null;
    layer: Layer;
    /** Whether the Lab can show a change live (stylesheet rules and chart options). */
    preview: boolean;
    snippet: string;
    selector?: string | null;
    at?: string[];
    property?: string | null;
    via?: 'tw-arbitrary' | 'style-attr' | 'markup';
    chart?: boolean;
}

export interface CatalogVarDef {
    file: number;
    name: string;
    value: string;
    line: number;
    zone: Zone;
    selector: string | null;
    theme: ThemeContext | null;
    /** `root`: inherited by the whole page, overridable on `<html>`; `scoped`: the defining rule must be rewritten. */
    scope: 'root' | 'scoped';
}

export interface CatalogVar {
    name: string;
    defs: CatalogVarDef[];
    uses: number;
    files: Record<string, number>;
}

export interface CatalogPaletteEntry {
    /** `--color-emerald-600` */
    var: string;
    uses: number;
    /** Uses written with a `dark:` variant. */
    dark: number;
    classes: Record<string, number>;
    files: Record<string, number>;
    /** `[fileIndex, line]` of every use. */
    occ: [number, number][];
}

export interface ColorCatalog {
    meta: {
        schema: 'lf-color-catalog/1';
        app_version: string;
        generated_at: string;
        hash: string;
        scan_ms: number;
        parity: Record<string, number>;
        layers: Record<string, number>;
        excluded: string[];
    };
    files: string[];
    css_vars: CatalogVar[];
    palette: CatalogPaletteEntry[];
    literals: CatalogLiteral[];
    by_value: Record<string, number[]>;
}

/** Which theme a change applies to. */
export type Scope = 'light' | 'dark' | 'both';

/**
 * - `css-var`: a CSS custom property (Tailwind palette `--color-*`, `--theme-*`, brand, future `--lf-*` roles);
 * - `css-literal`: a colour written in a stylesheet (component `<style>`, `app.css`), matched by value;
 * - `chart-color`: a colour in an ECharts option, matched by value;
 * - `proposal`: no live preview (inline styles, generated colours, `offline.html`, manifest): exported only.
 */
export type ChangeLayer = 'css-var' | 'css-literal' | 'chart-color' | 'proposal';

export interface LabChange {
    /** `${layer}:${target}@${scope}`, or with `#${occurrence}` for a single stylesheet occurrence. */
    id: string;
    layer: ChangeLayer;
    /** The variable name, or the colour key (`#rrggbb` / `oklch(…)`) of a literal. */
    target: string;
    scope: Scope;
    /** The value the change starts from, as the Lab saw it. */
    from: string;
    /** Any CSS colour. */
    to: string;
    /** Literal layers: also rewrite the translucent variants of the colour, keeping their alpha. Default true. */
    alphaVariants?: boolean;
    /** `css-literal` restricted to one catalogue occurrence (literal id). */
    occurrence?: number;
    /** With `occurrence`: the rule's selector and property as the catalogue recorded them, matched in the CSSOM. */
    match?: {selector: string; property: string | null};
    note?: string;
    /** Gallery screen codes (`dashboard/kpi-top`), as in the designer package. */
    shots?: string[];
}

export type CvdMode = 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia' | 'achromatopsia';

export interface LabState {
    schema: 'lf-designer-lab-state/1';
    changes: LabChange[];
    /** Show the original colours without losing the changes. */
    suspended: boolean;
    cvd: CvdMode;
    notes: string;
    author: string;
    /** Named snapshots of `changes`, for A/B comparison. */
    variants: Record<string, LabChange[]>;
    activeVariant: string | null;
    updatedAt: string;
}

/** What the editor is editing: a variable, or a colour value of one layer. */
export interface LabSelection {
    layer: ChangeLayer;
    target: string;
}

/** What the Lab client publishes on `window.__lfDesignerLab` once it runs (E2E and console use). */
export interface LabHook {
    /** Whether any engine is active in this tab. */
    active: () => boolean;
    /** The colours of the ECharts instance inside the first element matching `selector` (debug aid). */
    chartColors: (selector: string) => Promise<string[]>;
    /** How many stylesheet declarations and chart instances the engines changed. */
    stats: () => {cssRules: number; chartInstances: number; varOverrides: number};
}
