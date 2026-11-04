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
    /** A line of the chart category tables (`lib/theme/chartCategories.ts`): the category it colours (`type:ETF`). */
    category?: string;
}

/**
 * A chart category with a fixed colour (contract C1–C2 with DV): an asset type, a sector, or one of the two buckets
 * `categoryColor` adds to both (`Liquidity`, `Unknown`). The Lab edits it by key, never by value.
 */
export interface CatalogCategory {
    /** `type:ETF`, `sector:Health Care`, `bucket:Liquidity`: the target of a `category` change. */
    target: string;
    kind: 'type' | 'sector' | 'bucket';
    /** As the table writes it (`ETF`, `Health Care`, `Liquidity`). */
    key: string;
    /** The literal (`ColorCatalog.literals` id) each theme's value is written in, null when the table has none. */
    light: number | null;
    dark: number | null;
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
    /**
     * Defined in `@theme inline`: Tailwind writes the value into the utilities and emits no variable, so nothing on the
     * page reads it. Absent for any other definition.
     */
    inline?: boolean;
    /** With `inline`: the variable the alias names when its value is exactly `var(--x)`, else null. */
    alias_of?: string | null;
}

export interface CatalogVar {
    name: string;
    defs: CatalogVarDef[];
    uses: number;
    files: Record<string, number>;
    /** Where a stylesheet reads the variable: `[fileIndex, line, selector]`, the selector null outside a rule. */
    use_sites: [number, number, string | null][];
}

export interface CatalogPaletteEntry {
    /** `--color-emerald-600` */
    var: string;
    uses: number;
    /** Uses written with a `dark:` variant. */
    dark: number;
    classes: Record<string, number>;
    files: Record<string, number>;
    /** `[fileIndex, line, classIndex]` of every use; `classIndex` indexes `Object.keys(classes)`. */
    occ: [number, number, number][];
    /**
     * The variable the classes really read, when `var` is an inline alias (`--color-lf-card` → `--lf-surface-card`, a
     * colour role of workstream T): the one to edit and to show. Absent for an ordinary palette variable.
     */
    role?: string;
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
    /** The chart categories, in the order of their tables (absent from a catalogue built before them). */
    categories?: CatalogCategory[];
    /**
     * Static test ids → `[fileIndex, line, via]`: `attr` a `data-testid="x"`, `prop` a prop a component renders as its
     * `data-testid` (`testid="x"`, `optionTestId={…}`), `script` a property or variable of a script (`testId: 'x'`).
     */
    testids: Record<string, [number, number, TestidVia][]>;
    /** Templated test ids (`row-{id}`): `[prefix, fileIndex, line, via]`, longest prefix first. */
    testid_prefixes: [string, number, number, TestidVia][];
}

export type TestidVia = 'attr' | 'prop' | 'script';

/**
 * The test ids the code writes, as the picker needs them in the app tab (`virtual:lf-testid-index`, loaded with the
 * picker only): an id of the page that is not static but starts with a prefix is one instance of a templated id.
 */
export interface TestidIndex {
    statics: string[];
    /** Longest first. */
    prefixes: string[];
}

/** Which theme a change applies to. */
export type Scope = 'light' | 'dark' | 'both';

/**
 * - `css-var`: a CSS custom property (Tailwind palette `--color-*`, `--theme-*`, brand, future `--lf-*` roles);
 * - `css-literal`: a colour written in a stylesheet (component `<style>`, `app.css`), matched by value;
 * - `chart-color`: a colour in an ECharts option, matched by value;
 * - `proposal`: no live preview (inline styles, generated colours, `offline.html`, manifest): exported only;
 * - `element`: a specialisation — one property of the element picked in the app, in every instance of its component
 *   (`target` is the selector), or one colour of the picked chart (`property: 'chart'`); the shared source is untouched;
 * - `category`: the fixed colour of a chart category (`type:ETF`, `sector:Health Care`, `bucket:Liquidity`), by key:
 *   the charts read it through `categoryColor` of `lib/theme/chartCategories.ts` (contract C1–C4 with DV).
 */
export type ChangeLayer = 'css-var' | 'css-literal' | 'chart-color' | 'proposal' | 'element' | 'category';

/** What sets a colour of a picked element, as the Lab classifies the proved declaration. */
export type SourceKind = 'var' | 'tailwind-class' | 'rule-literal' | 'inline' | 'attribute' | 'current-color' | 'chart' | 'unknown';

/** A place in the code where the agent can bind a specialisation, and the text expected there (`verify-export` looks for it). */
export interface LabAnchorCandidate {
    file: string;
    line: number;
    /** `testid`: a test id of the chain is written there; `matched-rule`: the stylesheet rule that sets the colour; `class-use`: the colour class on that line; `var-use`: the rule reading the variable; `literal`: an inline style or attribute colour. */
    why: 'testid' | 'matched-rule' | 'class-use' | 'var-use' | 'literal';
    needle: string;
}

/**
 * Where a change was decided: the element picked in the app, said with the route, the test ids and CSS — never with its
 * text, so an export carries no data. Snake case, as it appears in the export.
 */
export interface LabAnchor {
    route: string;
    theme: 'light' | 'dark';
    /** Test ids from the element up, nearest first. */
    testids: string[];
    /** The element's own path below its nearest test id, positions included. */
    css_path: string;
    element: {tag: string; classes: string[]; scope_class: string | null};
    /** The selector of a specialisation: every instance of the element in its component (`component`), or the element alone when no test id surrounds it (`element`). */
    selector: string;
    breadth: 'component' | 'element';
    /** How many elements `selector` matched in the app tab when the element was picked. */
    matches: number;
    property: string;
    computed: string;
    source: {kind: SourceKind; selector: string | null; var: string | null; class: string | null};
    candidates: LabAnchorCandidate[];
}

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
    /** `element`: the CSS property the specialisation sets, or `chart` for one colour of the anchored charts. */
    property?: string;
    /** `element` with `property: 'chart'`: the colour key replaced inside the charts the selector reaches. */
    colorKey?: string;
    /** The picked element the change was decided on: required for `element`, context for the other layers. */
    anchor?: LabAnchor;
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

/** What the editor is editing: a variable, a colour value of one layer, or a specialisation of the picked element. */
export interface LabSelection {
    layer: ChangeLayer;
    target: string;
    /** `css-literal`: the occurrence to preselect (the picked element's rule). */
    occurrence?: number;
    /** `element`: the property, its value on the picked element, and the chart colour key. */
    property?: string;
    from?: string;
    colorKey?: string;
    /** Set when the editor is opened from the picked element: the change keeps it. */
    anchor?: LabAnchor;
}

/** A declaration that can set one colour property of a picked element. */
export interface PickedDeclaration {
    origin: 'rule' | 'inline' | 'attribute';
    /** The rule's selector (nested rules resolved), null for an inline style or an attribute. */
    selector: string | null;
    /** The declared text, as written before any Lab change. */
    value: string;
    /** The property as declared: the longhand, or the shorthand that sets it (`border-color`, `background`…). */
    declared_as: string;
    important: boolean;
    /** Cascade layer (`utilities`), `''` for an anonymous one, null when unlayered. */
    layer: string | null;
    /** The stylesheet file (`0.C3P6fEz2.css`), or `inline <style>`. */
    sheet: string | null;
    /** Enclosing `@media`, `@supports`, `@container` conditions. */
    conditions: string[];
    /** Matches only in a state the element was not in when picked (`:hover`, `:focus`…). */
    state: boolean;
    /** Proved to set the computed value. */
    wins: boolean;
}

export interface PickedProperty {
    /** `color`, `background-color`, `border-color` (four equal sides), `border-top-color`…, `outline-color`, `text-decoration-color`, `fill`, `stroke`, `box-shadow`, `background-image`. */
    property: string;
    computed: string;
    /** The colours of the computed value (several for `box-shadow` and gradients). */
    colors: string[];
    /** 0: set on the element; n: on the n-th ancestor (an inherited colour, or the background seen through). */
    depth: number;
    /** The tag of that ancestor (`th`), null at depth 0. */
    ancestor_tag: string | null;
    ancestor_testid: string | null;
    /** Winner first when proved; then the others in cascade order. */
    declarations: PickedDeclaration[];
    proved: boolean;
    /** The value is `currentColor`: it follows `color`. */
    current_color: boolean;
    /** A Lab specialisation sets it right now (the declarations are what is underneath). */
    lab_override: boolean;
    /**
     * The selector a specialisation of this property writes: the element that declares the colour when it is inside the
     * picked element's component (an inherited colour, a background seen through), else the picked element.
     */
    selector: string;
    breadth: 'component' | 'element';
    /** How many elements `selector` matched in the app tab. */
    matches: number;
    /** `selector` names the declaring ancestor, not the picked element. */
    at_ancestor: boolean;
}

export interface PickedChart {
    host_testid: string | null;
    /** The selector of the chart's component, for a chart specialisation. */
    selector: string;
    /** How many elements `selector` matched in the app tab. */
    matches: number;
    /** The colours of its option, as the app wrote them (Lab changes undone). */
    colors: string[];
    /** The colour of the shape under the pointer, when ECharts tells. */
    pointed: string | null;
}

/** What the app tab reports about the element picked: facts only, no catalogue (the Lab resolves them). */
export interface PickedElement {
    at: number;
    route: string;
    theme: 'light' | 'dark';
    testids: string[];
    css_path: string;
    element: {tag: string; classes: string[]; scope_class: string | null};
    selector: string;
    breadth: 'component' | 'element';
    matches: number;
    properties: PickedProperty[];
    chart: PickedChart | null;
}

/** What the Lab client publishes on `window.__lfDesignerLab` once it runs (E2E and console use). */
export interface LabHook {
    /** Whether any engine is active in this tab. */
    active: () => boolean;
    /** Whether this tab is waiting for an element to be picked. */
    picking: () => boolean;
    /** The colours of the ECharts instance inside the first element matching `selector` (debug aid). */
    chartColors: (selector: string) => Promise<string[]>;
    /** How many stylesheet declarations, chart instances, variables and specialisations the engines changed. */
    stats: () => LabStats;
    /**
     * Contract C3 with DV: the colour a `category` change gives a chart category in a theme, asked by `categoryColor`
     * of `lib/theme/chartCategories.ts` — `#rrggbb`, or `rgba()` when translucent; undefined when no change applies.
     */
    categoryColor: (kind: 'type' | 'sector', key: string, dark: boolean) => string | undefined;
}

export interface LabStats {
    cssRules: number;
    chartInstances: number;
    varOverrides: number;
    elementRules: number;
    /** `category` changes the engine answers `categoryColor` with. */
    categoryOverrides: number;
}
