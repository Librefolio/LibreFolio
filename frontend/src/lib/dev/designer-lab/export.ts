/**
 * Designer Lab — the export the agent reads (`lf-designer-lab/1`, see `design-designerLab.md` §7) and its Markdown
 * twin for people. Every change carries where it lives in the code: file, line, and for stylesheet colours the
 * selector and property, from the catalogue the Lab was built with (`catalog_hash`). Pure functions, except
 * `downloadText`.
 */

import {changeId, STATE_SCHEMA} from './store';
import type {CatalogLiteral, ColorCatalog, LabChange, LabState, Layer, Scope} from './types';
import {isSafeCssValue} from './engine/targets';

export const EXPORT_SCHEMA = 'lf-designer-lab/1';
const LAYERS = ['css-var', 'css-literal', 'chart-color', 'proposal'] as const;
const SCOPES: Scope[] = ['light', 'dark', 'both'];
const LITERAL_LAYERS: Record<string, Layer[]> = {'css-literal': ['css-literal'], 'chart-color': ['chart-color'], proposal: ['script', 'markup', 'static']};

export interface ExportOccurrence {
    file: string;
    line: number;
    col?: number;
    raw?: string;
    selector?: string | null;
    property?: string | null;
    theme_context?: string | null;
    layer?: string;
    snippet?: string;
}

export interface ExportChange {
    id: string;
    layer: LabChange['layer'];
    scope: Scope;
    preview: boolean;
    target: string;
    from: string;
    to: string;
    granularity?: 'value' | 'occurrence';
    alpha_variants?: boolean;
    impact?: {uses: number; files: number; classes?: Record<string, number>};
    definitions?: {file: string; line: number; selector: string | null; theme: string | null; value: string}[];
    occurrences: ExportOccurrence[];
    note?: string;
    shots?: string[];
}

export interface ContrastRow {
    fg: string;
    bg: string;
    scope: 'light' | 'dark';
    before: number;
    after: number;
}

export interface LabExport {
    schema: typeof EXPORT_SCHEMA;
    app_version: string;
    catalog_hash: string;
    exported_at: string;
    author: string;
    notes: string;
    changes: ExportChange[];
    contrast: ContrastRow[];
    variants: Record<string, LabChange[]>;
}

function literalOccurrence(catalog: ColorCatalog, lit: CatalogLiteral): ExportOccurrence {
    const occ: ExportOccurrence = {file: catalog.files[lit.file], line: lit.line, col: lit.col, raw: lit.raw, layer: lit.layer, theme_context: lit.theme};
    if (lit.selector !== undefined) occ.selector = lit.selector;
    if (lit.property !== undefined) occ.property = lit.property;
    occ.snippet = lit.snippet;
    return occ;
}

/** The literals a change reaches: same colour, the change's layers and theme, alpha variants when asked, one occurrence when set. */
export function literalsOf(catalog: ColorCatalog, change: LabChange): CatalogLiteral[] {
    const layers = LITERAL_LAYERS[change.layer] ?? [];
    if (change.occurrence !== undefined) return catalog.literals.filter((l) => l.id === change.occurrence);
    const key = change.target.toLowerCase();
    // A one-theme change leaves out the occurrences that certainly belong to the other theme: a stylesheet selector
    // or a `dark:` class says so. A script's theme is a guess from names and ternaries, so a script occurrence is
    // always kept, and the agent reads its `theme_context`.
    const certain = (l: CatalogLiteral) => l.zone === 'css-file' || l.zone === 'svelte-style' || l.zone === 'svelte-markup';
    const themeOk = (l: CatalogLiteral) => change.scope === 'both' || !certain(l) || l.theme === null || l.theme === 'both' || l.theme === change.scope;
    return catalog.literals.filter((l) => l.key === key && layers.includes(l.layer) && themeOk(l) && (change.alphaVariants !== false || (l.alpha ?? 1) >= 0.9995));
}

function exportChange(catalog: ColorCatalog, change: LabChange): ExportChange {
    const out: ExportChange = {id: change.id, layer: change.layer, scope: change.scope, preview: change.layer !== 'proposal', target: change.target, from: change.from, to: change.to, occurrences: []};
    if (change.layer === 'css-var') {
        const palette = catalog.palette.find((p) => p.var === change.target);
        const v = catalog.css_vars.find((x) => x.name === change.target);
        out.impact = {uses: (palette?.uses ?? 0) + (v?.uses ?? 0), files: new Set([...Object.keys(palette?.files ?? {}), ...Object.keys(v?.files ?? {})]).size};
        if (palette) {
            out.impact.classes = palette.classes;
            out.occurrences = palette.occ.map(([f, line]) => ({file: catalog.files[f], line}));
        }
        if (v?.defs.length) out.definitions = v.defs.map((d) => ({file: catalog.files[d.file], line: d.line, selector: d.selector, theme: d.theme, value: d.value}));
    } else {
        out.granularity = change.occurrence === undefined ? 'value' : 'occurrence';
        out.alpha_variants = change.alphaVariants !== false;
        out.occurrences = literalsOf(catalog, change).map((lit) => literalOccurrence(catalog, lit));
    }
    if (change.note) out.note = change.note;
    if (change.shots?.length) out.shots = change.shots;
    return out;
}

export function buildExport(state: LabState, catalog: ColorCatalog, appVersion: string, contrast: ContrastRow[] = [], now = new Date()): LabExport {
    return {
        schema: EXPORT_SCHEMA,
        app_version: appVersion,
        catalog_hash: catalog.meta.hash,
        exported_at: isoWithOffset(now),
        author: state.author,
        notes: state.notes,
        changes: state.changes.map((c) => exportChange(catalog, c)),
        contrast,
        variants: state.variants,
    };
}

/** ISO 8601 with the local offset (`2026-10-20T15:02:11+02:00`), as people read dates. */
export function isoWithOffset(d: Date): string {
    const pad = (n: number) => String(Math.trunc(Math.abs(n))).padStart(2, '0');
    const off = -d.getTimezoneOffset();
    const sign = off >= 0 ? '+' : '-';
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}${sign}${pad(off / 60)}:${pad(off % 60)}`;
}

const MD_ROWS = 40;
const cell = (s: unknown) =>
    String(s ?? '')
        .replaceAll('|', '\\|')
        .replaceAll('\n', ' ');

/** The Markdown twin of an export, in the Lab's language for the headings. */
export function renderMarkdown(doc: LabExport, lang: 'it' | 'en' = 'it'): string {
    const it = lang === 'it';
    const L: string[] = [];
    L.push(`# Designer Lab — ${it ? 'modifiche' : 'changes'} (${doc.changes.length})`, '');
    L.push(`- schema: \`${doc.schema}\``, `- app: \`${doc.app_version}\``, `- ${it ? 'catalogo' : 'catalogue'}: \`${doc.catalog_hash}\``, `- ${it ? 'esportato il' : 'exported at'}: ${doc.exported_at}`);
    if (doc.author) L.push(`- ${it ? 'autore' : 'author'}: ${doc.author}`);
    L.push('');
    if (doc.notes) L.push(`## ${it ? 'Note' : 'Notes'}`, '', doc.notes, '');
    for (const c of doc.changes) {
        L.push(`## ${c.layer} · \`${c.target}\` · ${c.scope}`, '');
        L.push(`- \`${c.from || '—'}\` → \`${c.to}\`${c.preview ? '' : it ? ' (proposta, senza anteprima)' : ' (proposal, no preview)'}`);
        if (c.granularity) L.push(`- ${it ? 'ambito' : 'reach'}: ${c.granularity}${c.alpha_variants ? (it ? ', con le varianti trasparenti' : ', translucent variants included') : ''}`);
        if (c.impact) L.push(`- ${it ? 'impatto' : 'impact'}: ${c.impact.uses} ${it ? 'usi' : 'uses'}, ${c.impact.files} file`);
        if (c.note) L.push(`- ${it ? 'nota' : 'note'}: ${c.note}`);
        if (c.shots?.length) L.push(`- ${it ? 'schermate' : 'screens'}: ${c.shots.map((s) => `\`${s}\``).join(', ')}`);
        if (c.definitions?.length) {
            L.push('', `${it ? 'Definizioni' : 'Definitions'}:`, '');
            for (const d of c.definitions) L.push(`- \`${d.file}:${d.line}\` \`${d.selector ?? ''}\` = \`${d.value}\``);
        }
        if (c.occurrences.length) {
            L.push('', `| ${it ? 'File' : 'File'} | ${it ? 'Riga' : 'Line'} | ${it ? 'Valore' : 'Value'} | ${it ? 'Selettore / proprietà' : 'Selector / property'} |`, '|---|---:|---|---|');
            for (const o of c.occurrences.slice(0, MD_ROWS)) L.push(`| \`${cell(o.file)}\` | ${o.line} | ${o.raw ? `\`${cell(o.raw)}\`` : ''} | ${o.selector ? `\`${cell(o.selector)}\` ${cell(o.property ?? '')}` : ''} |`);
            if (c.occurrences.length > MD_ROWS) L.push('', `… ${c.occurrences.length - MD_ROWS} ${it ? 'altre nel JSON' : 'more in the JSON'}`);
        }
        L.push('');
    }
    if (doc.contrast.length) {
        L.push(`## ${it ? 'Contrasto' : 'Contrast'}`, '', `| fg | bg | ${it ? 'tema' : 'theme'} | ${it ? 'prima' : 'before'} | ${it ? 'dopo' : 'after'} |`, '|---|---|---|---:|---:|');
        for (const r of doc.contrast) L.push(`| \`${r.fg}\` | \`${r.bg}\` | ${r.scope} | ${r.before.toFixed(2)} | ${r.after.toFixed(2)} |`);
        L.push('');
    }
    return L.join('\n');
}

/** A few lines to paste in a chat or an email. */
export function renderSummary(doc: LabExport): string {
    const lines = [`Designer Lab · ${doc.app_version} · ${doc.changes.length} changes · ${doc.catalog_hash.slice(0, 19)}`];
    for (const c of doc.changes) lines.push(`- [${c.layer}/${c.scope}] ${c.target}: ${c.from || '—'} → ${c.to} (${c.occurrences.length} occ.)${c.note ? ` — ${c.note}` : ''}`);
    if (doc.notes) lines.push('', doc.notes);
    return lines.join('\n');
}

export interface ImportResult {
    state: LabState | null;
    errors: string[];
    warnings: string[];
}

/** Read an export back into a state, refusing what the Lab cannot apply safely. */
export function parseImport(text: string, base: LabState, catalog: ColorCatalog): ImportResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    let doc: Partial<LabExport>;
    try {
        doc = JSON.parse(text);
    } catch {
        return {state: null, errors: ['not JSON'], warnings};
    }
    if (doc.schema !== EXPORT_SCHEMA) return {state: null, errors: [`schema is not ${EXPORT_SCHEMA}`], warnings};
    if (!Array.isArray(doc.changes)) return {state: null, errors: ['changes missing'], warnings};
    if (doc.catalog_hash && doc.catalog_hash !== catalog.meta.hash) warnings.push('catalog_hash differs: the code changed since the export (verify it with frontend/scripts/designer-lab/verify-export.mjs)');
    const changes: LabChange[] = [];
    doc.changes.forEach((raw, i) => {
        const c = raw as Partial<ExportChange>;
        if (!c || !LAYERS.includes(c.layer as (typeof LAYERS)[number]) || typeof c.target !== 'string' || !SCOPES.includes(c.scope as Scope) || typeof c.to !== 'string' || !isSafeCssValue(c.to)) {
            errors.push(`change ${i}: invalid`);
            return;
        }
        const change: LabChange = {id: '', layer: c.layer as LabChange['layer'], target: c.target, scope: c.scope as Scope, from: typeof c.from === 'string' ? c.from : '', to: c.to};
        if (c.layer !== 'css-var') change.alphaVariants = c.alpha_variants !== false;
        if (c.granularity === 'occurrence' && c.occurrences?.length === 1) {
            // Ids belong to one catalogue: find the occurrence again by place and value.
            const o = c.occurrences[0];
            const fileIndex = catalog.files.indexOf(o.file);
            const lit = catalog.literals.find((l) => l.file === fileIndex && l.line === o.line && l.raw === o.raw);
            if (lit) {
                change.occurrence = lit.id;
                change.match = {selector: lit.selector ?? '', property: lit.property ?? null};
            } else warnings.push(`change ${i}: occurrence ${o.file}:${o.line} not found, applied to every occurrence of ${c.target}`);
        }
        if (typeof c.note === 'string' && c.note) change.note = c.note;
        if (Array.isArray(c.shots)) change.shots = c.shots.filter((s): s is string => typeof s === 'string');
        change.id = changeId(change);
        changes.push(change);
    });
    const state: LabState = {
        ...base,
        schema: STATE_SCHEMA,
        changes,
        notes: typeof doc.notes === 'string' ? doc.notes : base.notes,
        author: typeof doc.author === 'string' ? doc.author : base.author,
        variants: doc.variants && typeof doc.variants === 'object' ? (doc.variants as Record<string, LabChange[]>) : base.variants,
    };
    return {state, errors, warnings};
}

/** Offer a text as a file download. */
export function downloadText(filename: string, text: string, mime: string): void {
    const url = URL.createObjectURL(new Blob([text], {type: `${mime};charset=utf-8`}));
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
}
