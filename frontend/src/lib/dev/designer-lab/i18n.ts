/**
 * Designer Lab — its own small dictionary, Italian and English (developer's decision, 14/10/2026: the Lab is a debug
 * tool and stays out of the app's translation catalogue). Italian for an Italian UI, English otherwise.
 */

import {derived, type Readable} from 'svelte/store';
import {locale} from '$lib/i18n';

const STRINGS = {
    title: {it: 'Designer Lab', en: 'Designer Lab'},
    subtitle: {it: 'Colori dal vivo, solo nelle build di debug', en: 'Live colours, debug builds only'},
    catalog: {it: 'catalogo', en: 'catalogue'},
    editing: {it: 'Modifica', en: 'Editing'},
    'scope.light': {it: 'chiaro', en: 'light'},
    'scope.dark': {it: 'scuro', en: 'dark'},
    'scope.both': {it: 'entrambi', en: 'both'},
    suspend: {it: 'Sospendi', en: 'Suspend'},
    resume: {it: 'Riprendi', en: 'Resume'},
    resetAll: {it: 'Ripristina tutto', en: 'Reset all'},
    resetAllConfirm: {it: 'Togliere tutte le modifiche?', en: 'Remove every change?'},
    exportBoth: {it: 'Esporta JSON + MD', en: 'Export JSON + MD'},
    copySummary: {it: 'Copia riassunto', en: 'Copy summary'},
    copied: {it: 'Riassunto copiato', en: 'Summary copied'},
    exported: {it: 'Export scaricato', en: 'Export downloaded'},
    import: {it: 'Importa', en: 'Import'},
    imported: {it: 'Export importato', en: 'Export imported'},
    importFailed: {it: 'Import non valido', en: 'Invalid import'},
    cvd: {it: 'Daltonismo', en: 'Colour vision'},
    'cvd.none': {it: 'nessuno', en: 'none'},
    'cvd.protanopia': {it: 'protanopia', en: 'protanopia'},
    'cvd.deuteranopia': {it: 'deuteranopia', en: 'deuteranopia'},
    'cvd.tritanopia': {it: 'tritanopia', en: 'tritanopia'},
    'cvd.achromatopsia': {it: 'acromatopsia', en: 'achromatopsia'},
    variant: {it: 'Variante', en: 'Variant'},
    variantNone: {it: '(corrente)', en: '(current)'},
    variantSave: {it: 'Salva variante', en: 'Save variant'},
    variantName: {it: 'Nome della variante', en: 'Variant name'},
    'tab.overview': {it: 'Panoramica', en: 'Overview'},
    'tab.palette': {it: 'Palette Tailwind', en: 'Tailwind palette'},
    'tab.vars': {it: 'Variabili dell’app', en: 'App variables'},
    'tab.sheets': {it: 'Fogli di stile', en: 'Stylesheets'},
    'tab.charts': {it: 'Grafici', en: 'Charts'},
    'tab.proposals': {it: 'Senza anteprima', en: 'No preview'},
    'tab.changes': {it: 'Modifiche', en: 'Changes'},
    'tab.contrast': {it: 'Contrasto', en: 'Contrast'},
    'tab.notes': {it: 'Note', en: 'Notes'},
    search: {it: 'Cerca (nome, valore, file)', en: 'Search (name, value, file)'},
    uses: {it: 'usi', en: 'uses'},
    files: {it: 'file', en: 'files'},
    occurrences: {it: 'occorrenze', en: 'occurrences'},
    modified: {it: 'modificato', en: 'changed'},
    'overview.layers': {it: 'Colori scritti a mano, per livello', en: 'Hand-written colours, by layer'},
    'overview.live': {it: 'modificabili dal vivo', en: 'live-editable'},
    'overview.palette': {it: 'Variabili della palette Tailwind in uso', en: 'Tailwind palette variables in use'},
    'overview.vars': {it: 'Variabili CSS definite nell’app', en: 'CSS variables defined in the app'},
    'overview.hint': {
        it: 'Apri l’app in altre schede dello stesso indirizzo: ogni modifica si vede subito, grafici compresi. Le modifiche restano in questo browser finché non le esporti.',
        en: 'Open the app in other tabs of the same address: every change shows at once, charts included. Changes stay in this browser until you export them.',
    },
    'layer.css-literal': {it: 'fogli di stile', en: 'stylesheets'},
    'layer.chart-color': {it: 'grafici', en: 'charts'},
    'layer.script': {it: 'script (senza anteprima)', en: 'scripts (no preview)'},
    'layer.markup': {it: 'markup (senza anteprima)', en: 'markup (no preview)'},
    'layer.static': {it: 'fuori dall’app (senza anteprima)', en: 'outside the app (no preview)'},
    'layer.css-var': {it: 'variabile', en: 'variable'},
    'layer.proposal': {it: 'proposta', en: 'proposal'},
    'editor.title': {it: 'Modifica colore', en: 'Edit colour'},
    'editor.from': {it: 'Valore attuale', en: 'Current value'},
    'editor.to': {it: 'Nuovo valore (qualsiasi colore CSS)', en: 'New value (any CSS colour)'},
    'editor.invalid': {it: 'Colore non riconosciuto', en: 'Unrecognised colour'},
    'editor.gamut': {it: 'Fuori da sRGB: gli schermi normali e i grafici lo mostrano ridotto', en: 'Outside sRGB: ordinary screens and charts show it clamped'},
    'editor.snap': {it: 'Aggancia a una variabile', en: 'Snap to a variable'},
    'editor.snapNone': {it: '(nessuna)', en: '(none)'},
    'editor.alpha': {it: 'Anche le varianti trasparenti (alfa conservato)', en: 'Translucent variants too (alpha kept)'},
    'editor.granularity': {it: 'Ambito nel codice', en: 'Reach in the code'},
    'editor.allOccurrences': {it: 'Tutte le occorrenze di questo valore', en: 'Every occurrence of this value'},
    'editor.oneOccurrence': {it: 'Solo questa occorrenza', en: 'This occurrence only'},
    'editor.note': {it: 'Nota', en: 'Note'},
    'editor.shots': {it: 'Codici schermata (es. dashboard/kpi-top)', en: 'Screen codes (e.g. dashboard/kpi-top)'},
    'editor.apply': {it: 'Applica', en: 'Apply'},
    'editor.remove': {it: 'Togli la modifica', en: 'Remove the change'},
    'editor.close': {it: 'Chiudi', en: 'Close'},
    'editor.noPreview': {it: 'Nessuna anteprima: la proposta finisce solo nell’export', en: 'No preview: the proposal only goes into the export'},
    'editor.sharedRule': {it: 'Alcune regole valgono in entrambi i temi: la modifica di un solo tema le cambia solo in quel tema', en: 'Some rules apply to both themes: a one-theme change alters them in that theme only'},
    'editor.impact': {it: 'Impatto', en: 'Impact'},
    'editor.definedAt': {it: 'Definita in', en: 'Defined at'},
    'contrast.title': {it: 'Contrasto WCAG', en: 'WCAG contrast'},
    'contrast.declared': {it: 'Coppie dichiarate (testi su superfici)', en: 'Declared pairs (text on surfaces)'},
    'contrast.custom': {it: 'Coppia libera', en: 'Custom pair'},
    'contrast.fg': {it: 'Primo piano', en: 'Foreground'},
    'contrast.bg': {it: 'Sfondo', en: 'Background'},
    'contrast.before': {it: 'prima', en: 'before'},
    'contrast.after': {it: 'dopo', en: 'after'},
    'notes.general': {it: 'Nota generale', en: 'General note'},
    'notes.author': {it: 'Autore', en: 'Author'},
    'changes.empty': {it: 'Nessuna modifica', en: 'No changes'},
    'changes.layer': {it: 'Livello', en: 'Layer'},
    'changes.target': {it: 'Obiettivo', en: 'Target'},
    'changes.scope': {it: 'Tema', en: 'Theme'},
    staleCatalog: {it: 'Il codice è cambiato: ricarica per aggiornare il catalogo', en: 'The code changed: reload to refresh the catalogue'},
    moreRows: {it: 'altre {n}', en: '{n} more'},
} satisfies Record<string, {it: string; en: string}>;

export type LabKey = keyof typeof STRINGS;

const TABLE: Record<string, {it: string; en: string}> = STRINGS;

/** `t(key, {n: 3})`, in the Lab's language (Italian when the app is Italian, English otherwise). Unknown keys echo. */
export const labT: Readable<(key: LabKey | `${string}.${string}`, params?: Record<string, string | number>) => string> = derived(locale, ($locale) => {
    const lang: 'it' | 'en' = ($locale ?? '').startsWith('it') ? 'it' : 'en';
    return (key: LabKey | `${string}.${string}`, params?: Record<string, string | number>): string => {
        let text: string = TABLE[key]?.[lang] ?? key;
        if (params) for (const [k, v] of Object.entries(params)) text = text.replaceAll(`{${k}}`, String(v));
        return text;
    };
});

export const labLang: Readable<'it' | 'en'> = derived(locale, ($locale) => (($locale ?? '').startsWith('it') ? 'it' : 'en'));
