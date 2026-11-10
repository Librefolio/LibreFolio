/**
 * The plugin settings form, without the DOM (workstream X, lot CP11b): what the user did and has not saved, the edits
 * it makes, what is wrong with them before the server says so, the write, and the texts a field shows. The components
 * (`PluginSettingsForm.svelte`) only draw what these functions decide, so the rules are tested here, once.
 *
 * Texts: a plugin declares English labels and, when it has translations, their keys (`label_key`, `description_key`,
 * an option's `label_key`); the interface never builds a key (plan 03 §4.4). A missing translation falls back to the
 * English text (`translateOr`). Every class and key below is a whole literal (theme-roles rule 6, i18n audit).
 */
import {Briefcase, ChartColumn, Coins, Wrench} from 'lucide-svelte';
import {translateOr, type Translate} from '$lib/utils/core/translateOr';
import type {PlainValue, PluginSettingsEntry, PluginSettingWriteItem, PluginSettingWriteResult, SettingField, SettingOption, SettingsFamily} from './pluginSettingsApi';

// =============================================================================
// Groups and texts
// =============================================================================

/** The families in the order the Plugins tab shows them. */
export const FAMILY_ORDER: readonly SettingsFamily[] = ['asset', 'fx', 'brim', 'tool'];

export const FAMILY_TITLE_KEYS: Record<SettingsFamily, string> = {
    asset: 'pluginSettings.families.asset',
    fx: 'pluginSettings.families.fx',
    brim: 'pluginSettings.families.brim',
    tool: 'pluginSettings.families.tool',
};

/** The icon before a family's title: the one the family has on the documentation's home («A Modular Ecosystem»). */
export const FAMILY_ICONS: Record<SettingsFamily, typeof ChartColumn> = {
    asset: ChartColumn,
    fx: Coins,
    brim: Briefcase,
    tool: Wrench,
};

export interface FamilyGroup {
    family: SettingsFamily;
    entries: PluginSettingsEntry[];
}

/** The entries by family, in `FAMILY_ORDER`, each family keeping the API's order; a family without entries is left out. */
export function groupByFamily(entries: readonly PluginSettingsEntry[]): FamilyGroup[] {
    return FAMILY_ORDER.map((family) => ({family, entries: entries.filter((entry) => entry.family === family)})).filter((group) => group.entries.length > 0);
}

export function fieldLabel(field: SettingField, t: Translate): string {
    return field.label_key ? translateOr(t, field.label_key, field.label) : field.label;
}

export function fieldDescription(field: SettingField, t: Translate): string {
    return field.description_key ? translateOr(t, field.description_key, field.description) : field.description;
}

export function optionLabel(option: SettingOption, t: Translate): string {
    return option.label_key ? translateOr(t, option.label_key, option.label) : option.label;
}

/** The text of the value in force in a field the caller cannot change: the option's label for a select, '—' for none. */
export function displayValue(field: SettingField, t: Translate): string {
    if (field.value === null) return '—';
    if (field.type === 'select') {
        const option = field.options.find((candidate) => candidate.value === field.value);
        return option ? optionLabel(option, t) : String(field.value);
    }
    return String(field.value);
}

export const SCOPE_KEYS: Record<SettingField['scope'], string> = {
    user: 'pluginSettings.scope.user',
    system: 'pluginSettings.scope.system',
};

/** Why a field cannot be changed here: an environment variable of the server sets it, or it is the instance's and the
 * caller is not an administrator (D-X15). Null when the caller can change it. */
export function readOnlyReason(field: SettingField): 'locked' | 'adminOnly' | null {
    if (field.editable) return null;
    return field.locked ? 'locked' : 'adminOnly';
}

/** How a secret reads: set by the server, invalid there, saved, saved but unreadable by this instance's key, or unset. */
export type SecretState = 'env' | 'invalidEnv' | 'set' | 'unreadable' | 'unset';

export function secretState(field: SettingField): SecretState {
    if (field.problem === 'invalid_env') return 'invalidEnv';
    if (field.locked || field.source === 'env') return 'env';
    if (field.problem === 'unreadable') return 'unreadable';
    return field.is_set ? 'set' : 'unset';
}

// =============================================================================
// What the user did, and the edits it makes
// =============================================================================

/**
 * What the user did to one plugin's fields and has not saved: the texts typed (text, number and secret fields), the
 * choices made (select, boolean), and the saved values to delete. The draft derives from it (`draftOf`), so a field
 * typed or chosen back to its value in force has no edit, and a field always shows what the user typed.
 */
export interface FormState {
    texts: Readonly<Record<string, string>>;
    choices: Readonly<Record<string, PlainValue>>;
    clears: readonly string[];
}

export const EMPTY_FORM: FormState = {texts: {}, choices: {}, clears: []};

/** `map[key]` when `map` holds `key` itself: a field key may be any declared name, `constructor` included, which a
 * plain lookup or `in` would find on `Object.prototype`. */
export function own<T>(map: Readonly<Record<string, T>>, key: string): T | undefined {
    return Object.hasOwn(map, key) ? map[key] : undefined;
}

function omit<T>(map: Readonly<Record<string, T>>, key: string): Record<string, T> {
    const next = {...map};
    delete next[key];
    return next;
}

/** `form` after `text` was typed in the field `key`: no longer to delete. */
export function typed(form: FormState, key: string, text: string): FormState {
    return {texts: {...form.texts, [key]: text}, choices: form.choices, clears: form.clears.filter((cleared) => cleared !== key)};
}

/** `form` after `value` was chosen in the field `key`: no longer to delete. */
export function chosen(form: FormState, key: string, value: PlainValue): FormState {
    return {texts: form.texts, choices: {...form.choices, [key]: value}, clears: form.clears.filter((cleared) => cleared !== key)};
}

/** `form` with the saved value of `key` to delete, what was typed or chosen there dropped. */
export function cleared(form: FormState, key: string): FormState {
    return {texts: omit(form.texts, key), choices: omit(form.choices, key), clears: form.clears.includes(key) ? form.clears : [...form.clears, key]};
}

/** `form` with nothing done to `key`. */
export function restored(form: FormState, key: string): FormState {
    return {texts: omit(form.texts, key), choices: omit(form.choices, key), clears: form.clears.filter((cleared) => cleared !== key)};
}

/** The text a text or number field shows: the one typed, else the default when its saved value is to be deleted, else
 * the value in force. */
export function shownText(field: SettingField, form: FormState): string {
    const text = own(form.texts, field.key);
    if (text !== undefined) return text;
    const value = form.clears.includes(field.key) ? field.default : field.value;
    return value === null ? '' : String(value);
}

/** The value a select or a boolean shows: the one chosen, else the default when its saved value is to be deleted, else
 * the value in force. */
export function shownChoice(field: SettingField, form: FormState): PlainValue | null {
    const choice = own(form.choices, field.key);
    if (choice !== undefined) return choice;
    return form.clears.includes(field.key) ? field.default : field.value;
}

/**
 * One field's edit, not saved yet:
 * - `value`: a choice (select, boolean);
 * - `text`: what was typed in a text or number field, parsed when written;
 * - `secret`: a new secret, sent once and forgotten;
 * - `clear`: delete the saved value, so the default (or nothing) applies.
 */
export type FieldEdit = {kind: 'value'; value: PlainValue} | {kind: 'text'; text: string} | {kind: 'secret'; text: string} | {kind: 'clear'};

/** The edits of one plugin, by field key: only the fields that change. */
export type PluginDraft = Readonly<Record<string, FieldEdit>>;

function isNumeric(field: SettingField): boolean {
    return field.type === 'number' || field.type === 'integer';
}

function parseNumber(text: string): number | null {
    const trimmed = text.trim();
    if (trimmed === '') return null;
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
}

/** The edit a typed text makes: none when it says what is in force already; emptying a saved value deletes it. */
function textEdit(field: SettingField, text: string): FieldEdit | null {
    if (text.trim() === '') return field.source === 'db' ? {kind: 'clear'} : null;
    if (isNumeric(field)) return parseNumber(text) === field.value ? null : {kind: 'text', text};
    return text === field.value ? null : {kind: 'text', text};
}

/** The edits `form` makes on the fields the caller may change. */
export function draftOf(entry: PluginSettingsEntry, form: FormState): PluginDraft {
    const draft: Record<string, FieldEdit> = {};
    for (const field of entry.fields) {
        if (!field.editable) continue;
        const text = own(form.texts, field.key);
        const choice = own(form.choices, field.key);
        let edit: FieldEdit | null = null;
        if (form.clears.includes(field.key)) edit = {kind: 'clear'};
        else if (field.secret) edit = text ? {kind: 'secret', text} : null;
        else if (field.type === 'select' || field.type === 'boolean') edit = choice !== undefined && choice !== field.value ? {kind: 'value', value: choice} : null;
        else if (text !== undefined) edit = textEdit(field, text);
        if (edit) draft[field.key] = edit;
    }
    return draft;
}

// =============================================================================
// Checks before the server's
// =============================================================================

export type InputProblemCode = 'required' | 'number' | 'integer' | 'below' | 'above' | 'tooShort' | 'tooLong' | 'option';

export interface InputProblem {
    code: InputProblemCode;
    /** The bound the value misses: `below`/`above` a number, `tooShort`/`tooLong` a length. */
    limit?: number;
}

export const PROBLEM_KEYS: Record<InputProblemCode, string> = {
    required: 'pluginSettings.problems.required',
    number: 'pluginSettings.problems.number',
    integer: 'pluginSettings.problems.integer',
    below: 'pluginSettings.problems.below',
    above: 'pluginSettings.problems.above',
    tooShort: 'pluginSettings.problems.tooShort',
    tooLong: 'pluginSettings.problems.tooLong',
    option: 'pluginSettings.problems.option',
};

function lengthProblem(field: SettingField, text: string): InputProblem | null {
    // Counted like the server's len(): by code point, not by UTF-16 unit.
    const length = [...text].length;
    if (field.min_length !== null && length < field.min_length) return {code: 'tooShort', limit: field.min_length};
    if (field.max_length !== null && length > field.max_length) return {code: 'tooLong', limit: field.max_length};
    return null;
}

/** What is wrong with an edit, as far as the declared rules tell; null when the server should accept it. */
function editProblem(field: SettingField, edit: FieldEdit): InputProblem | null {
    if (edit.kind === 'clear') return null;
    if (edit.kind === 'secret') return edit.text === '' ? {code: 'required'} : lengthProblem(field, edit.text);
    if (edit.kind === 'value') return field.type === 'select' && !field.options.some((option) => option.value === edit.value) ? {code: 'option'} : null;
    if (!isNumeric(field)) return lengthProblem(field, edit.text);
    const parsed = parseNumber(edit.text);
    if (parsed === null) return {code: 'number'};
    if (field.type === 'integer' && !Number.isInteger(parsed)) return {code: 'integer'};
    if (field.minimum !== null && parsed < field.minimum) return {code: 'below', limit: field.minimum};
    if (field.maximum !== null && parsed > field.maximum) return {code: 'above', limit: field.maximum};
    return null;
}

/** The problems of a draft, by field key. */
export function draftProblems(entry: PluginSettingsEntry, draft: PluginDraft): Record<string, InputProblem> {
    const problems: Record<string, InputProblem> = {};
    for (const field of entry.fields) {
        const edit = own(draft, field.key);
        const problem = edit ? editProblem(field, edit) : null;
        if (problem) problems[field.key] = problem;
    }
    return problems;
}

// =============================================================================
// The write and its answer
// =============================================================================

/** The items of a write, in the order the plugin declares its fields: one per edit. */
export function writeItems(entry: PluginSettingsEntry, draft: PluginDraft): PluginSettingWriteItem[] {
    const items: PluginSettingWriteItem[] = [];
    for (const field of entry.fields) {
        const edit = own(draft, field.key);
        if (!edit) continue;
        const item: PluginSettingWriteItem = {family: entry.family, plugin_code: entry.plugin_code, field_key: field.key, scope: field.scope};
        if (edit.kind === 'clear') item.clear = true;
        else if (edit.kind === 'secret') item.secret_value = edit.text;
        else if (edit.kind === 'value') item.value = edit.value;
        else item.value = isNumeric(field) ? (parseNumber(edit.text) ?? edit.text) : edit.text;
        items.push(item);
    }
    return items;
}

const REFUSAL_KEYS: Record<string, string> = {
    UNKNOWN_FIELD: 'pluginSettings.refusals.UNKNOWN_FIELD',
    FORBIDDEN_SCOPE: 'pluginSettings.refusals.FORBIDDEN_SCOPE',
    LOCKED_BY_ENV: 'pluginSettings.refusals.LOCKED_BY_ENV',
    INVALID_VALUE: 'pluginSettings.refusals.INVALID_VALUE',
};

/** The key of a refusal's text: a code this interface does not know reads as an invalid value. */
export function refusalKey(code: string): string {
    return own(REFUSAL_KEYS, code) ?? REFUSAL_KEYS.INVALID_VALUE;
}

/** The refused items of a write, by field key, with their code. */
export function refusalsByField(results: readonly PluginSettingWriteResult[]): Record<string, string> {
    const refused: Record<string, string> = {};
    for (const result of results) {
        if (!result.success && result.error_code) refused[result.field_key] = result.error_code;
    }
    return refused;
}

// =============================================================================
// Classes: whole literals, colour roles only (theme-roles)
// =============================================================================

export const STATUS_BADGE_CLASSES: Record<'configured' | 'notConfigured', string> = {
    configured: 'inline-flex items-center gap-1 rounded-full bg-lf-success-soft px-2.5 py-0.5 text-xs font-semibold text-lf-success-on-soft',
    notConfigured: 'inline-flex items-center gap-1 rounded-full bg-lf-warning-soft px-2.5 py-0.5 text-xs font-semibold text-lf-warning-on-soft',
};

export const NOTE_CLASSES: Record<'muted' | 'warning' | 'error', string> = {
    muted: 'text-xs text-lf-muted',
    warning: 'rounded-md border border-lf-warning-line bg-lf-warning-soft px-3 py-2 text-xs text-lf-warning-on-soft',
    error: 'rounded-md border border-lf-danger-line bg-lf-danger-soft px-3 py-2 text-xs text-lf-danger-on-soft',
};

export const INPUT_CLASS = 'w-full rounded-md border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:outline-none focus:ring-2 focus:ring-lf-focus disabled:cursor-not-allowed disabled:opacity-50';

export const SECONDARY_BUTTON_CLASS = 'inline-flex items-center gap-1 rounded-md border border-lf-input bg-lf-card px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover disabled:cursor-not-allowed disabled:opacity-50';

export const PRIMARY_BUTTON_CLASS = 'rounded-md bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50';

export const LINK_BUTTON_CLASS = 'text-xs text-lf-link hover:underline disabled:cursor-not-allowed disabled:opacity-50';
