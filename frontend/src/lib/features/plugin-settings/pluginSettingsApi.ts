/**
 * The plugin settings API (workstream X, lot CP11b; backend `api/v1/plugin_settings.py`, plan 03 §4.4): the settings
 * the plugins declare, as the signed-in user sees them, and the writes, all or nothing.
 *
 * Thin wrappers over the generated client, shared by the Plugins tab, the Configure dialog and their tests. A secret
 * travels only in a write's `secret_value`: no answer carries one, and nothing here keeps or logs it.
 */
import {isAxiosError} from 'axios';
import {ApiError, zodiosApi} from '$lib/api';

/** The plugin families, and `group`: a shared settings group, the values several plugins read (project 76). */
export type SettingsFamily = 'asset' | 'fx' | 'brim' | 'tool' | 'enricher' | 'group';
export type SettingType = 'string' | 'number' | 'integer' | 'boolean' | 'select';
export type SettingScope = 'user' | 'system';
/** Where a value comes from: an environment variable of the server, a saved value, the declared default, nowhere. */
export type SettingSource = 'env' | 'db' | 'default' | 'none';
/** `unreadable`: a saved secret this instance's key cannot read; `invalid_env`: the server variable that sets it is
 * invalid; `invalid_stored`: a saved value the field refuses now, the default applies. */
export type SettingProblem = 'unreadable' | 'invalid_env' | 'invalid_stored';
export type PlainValue = string | number | boolean;

export interface SettingOption {
    value: string;
    /** English, the fallback of `label_key`. */
    label: string;
    label_key: string | null;
}

/** One field as the caller sees it. A secret has neither `value` nor `default`: only `is_set` and `problem`. */
export interface SettingField {
    key: string;
    type: SettingType;
    scope: SettingScope;
    secret: boolean;
    required: boolean;
    label: string;
    description: string;
    label_key: string | null;
    description_key: string | null;
    /** The i18n key of the field named in a sentence, with its article (project 76, N3a2): the «to configure» window. */
    missing_key: string | null;
    options: SettingOption[];
    min_length: number | null;
    max_length: number | null;
    minimum: number | null;
    maximum: number | null;
    default: PlainValue | null;
    /** The value in force (the environment's, the saved one or the default), never for a secret. */
    value: PlainValue | null;
    is_set: boolean;
    source: SettingSource;
    locked: boolean;
    /** The variable that locks the field: administrators only. */
    env_variable: string | null;
    /** The caller may write it now. */
    editable: boolean;
    problem: SettingProblem | null;
    /** When the saved value last changed (ISO). */
    updated_at: string | null;
}

export interface PluginSettingsEntry {
    family: SettingsFamily;
    plugin_code: string;
    plugin_name: string;
    /** The plugin's icon, as its family's provider list publishes it (a remote URL or a path of this instance); null
     * when it has none, and the form shows a neutral icon. */
    icon_url: string | null;
    /** Every required field has a usable value: otherwise the plugin answers its calls with NOT_CONFIGURED. */
    configured: boolean;
    fields: SettingField[];
    /** The shared groups the plugin reads, by name: their fields are in the groups' own entries (project 76). */
    groups: string[];
    /** For a group: the plugins that read it. */
    used_by: PluginRef[];
    /** For a group: the i18n key of its name; `plugin_name` is the English fallback. */
    name_key: string | null;
    /** The calls counted and the limits, on the entry that owns the count (project 76, U4); absent elsewhere, and when the
     * server could not read the counts. */
    call_usage?: CallUsage;
}

/** The windows of the call counter, shortest first: calendar windows, UTC (project 76, U4). */
export const CALL_WINDOWS = ['minute', 'hour', 'day', 'week', 'month'] as const;
export type CallWindowName = (typeof CALL_WINDOWS)[number];

/** One window of a call counter: the calls of the window of now, its limit (null: none, or hidden by the managed
 * profile), when it ends (ISO, UTC), and whether it is full (judged by the server on the real limit). */
export interface CallWindow {
    window: CallWindowName;
    count: number;
    limit: number | null;
    resets_at: string;
    full: boolean;
}

/** The call counter of the entry that owns it: a plugin that calls out and reads no credit-sharing group, or such a group. */
export interface CallUsage {
    family: string;
    plugin_code: string;
    windows: CallWindow[];
}

/** A plugin another entry names: the plugins that read a group. */
export interface PluginRef {
    family: SettingsFamily;
    plugin_code: string;
    plugin_name: string;
}

/** One write item: exactly one of `value`, `secret_value`, `clear`. */
export interface PluginSettingWriteItem {
    family: SettingsFamily;
    plugin_code: string;
    field_key: string;
    scope: SettingScope;
    value?: PlainValue;
    secret_value?: string;
    clear?: boolean;
}

/** How a write item went: `error_code` when refused (`UNKNOWN_FIELD`, `FORBIDDEN_SCOPE`, `LOCKED_BY_ENV`, `INVALID_VALUE`). */
export interface PluginSettingWriteResult {
    field_key: string;
    success: boolean;
    error_code: string | null;
}

/**
 * What a write came to:
 * - `saved`: every item written;
 * - `refused`: nothing written, `results` says which item was refused and why (422);
 * - `conflict`: nothing written, another write changed the same settings meanwhile (409);
 * - `keyUnavailable`: nothing written, a secret cannot be encrypted with this instance's key (503);
 * - `failed`: no answer, or one this module does not know.
 */
export type SaveOutcome = {kind: 'saved'} | {kind: 'refused'; results: PluginSettingWriteResult[]} | {kind: 'conflict'} | {kind: 'keyUnavailable'} | {kind: 'failed'};

const FAMILIES: readonly string[] = ['asset', 'fx', 'brim', 'tool', 'enricher', 'group'];
const TYPES: readonly string[] = ['string', 'number', 'integer', 'boolean', 'select'];
const SOURCES: readonly string[] = ['env', 'db', 'default', 'none'];
const PROBLEMS: readonly string[] = ['unreadable', 'invalid_env', 'invalid_stored'];

function record(value: unknown): Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function textOrNull(value: unknown): string | null {
    return typeof value === 'string' && value ? value : null;
}

function numberOrNull(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function plainOrNull(value: unknown): PlainValue | null {
    return typeof value === 'string' || typeof value === 'boolean' || (typeof value === 'number' && Number.isFinite(value)) ? value : null;
}

function oneOf<T extends string>(value: unknown, allowed: readonly string[], fallback: T): T {
    return typeof value === 'string' && allowed.includes(value) ? (value as T) : fallback;
}

function optionOf(raw: unknown): SettingOption {
    const option = record(raw);
    return {value: String(option.value ?? ''), label: String(option.label ?? option.value ?? ''), label_key: textOrNull(option.label_key)};
}

/** A field as the components trust it: the generated type of an optional field is wider than its runtime schema. */
export function fieldOf(raw: unknown): SettingField {
    const field = record(raw);
    const secret = field.secret === true;
    return {
        key: String(field.key ?? ''),
        type: oneOf<SettingType>(field.type, TYPES, 'string'),
        scope: field.scope === 'system' ? 'system' : 'user',
        secret,
        required: field.required === true,
        label: String(field.label ?? field.key ?? ''),
        description: typeof field.description === 'string' ? field.description : '',
        label_key: textOrNull(field.label_key),
        description_key: textOrNull(field.description_key),
        missing_key: textOrNull(field.missing_key),
        options: Array.isArray(field.options) ? field.options.map(optionOf) : [],
        min_length: numberOrNull(field.min_length),
        max_length: numberOrNull(field.max_length),
        minimum: numberOrNull(field.minimum),
        maximum: numberOrNull(field.maximum),
        default: secret ? null : plainOrNull(field.default),
        value: secret ? null : plainOrNull(field.value),
        is_set: field.is_set === true,
        source: oneOf<SettingSource>(field.source, SOURCES, 'none'),
        locked: field.locked === true,
        env_variable: textOrNull(field.env_variable),
        editable: field.editable === true,
        problem: typeof field.problem === 'string' && PROBLEMS.includes(field.problem) ? (field.problem as SettingProblem) : null,
        updated_at: textOrNull(field.updated_at),
    };
}

/** A plugin named by a group, or null for an item that is not one: no object, no code, a family this module does not know. */
function refOf(raw: unknown): PluginRef | null {
    const ref = record(raw);
    const code = textOrNull(ref.plugin_code);
    if (code === null || typeof ref.family !== 'string' || !FAMILIES.includes(ref.family)) return null;
    return {family: ref.family as SettingsFamily, plugin_code: code, plugin_name: textOrNull(ref.plugin_name) ?? code};
}

function countOrNull(value: unknown): number | null {
    return typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : null;
}

/** A window as the block trusts it, or null for an item that is not one: an unknown window, no count, no end. */
function windowOf(raw: unknown): CallWindow | null {
    const item = record(raw);
    const count = countOrNull(item.count);
    const resetsAt = textOrNull(item.resets_at);
    if (typeof item.window !== 'string' || !(CALL_WINDOWS as readonly string[]).includes(item.window) || count === null || resetsAt === null) return null;
    return {window: item.window as CallWindowName, count, limit: countOrNull(item.limit), resets_at: resetsAt, full: item.full === true};
}

/** The usage block, its windows in window order, each once (the first kept); null when there is no block. */
function usageOf(raw: unknown): CallUsage | null {
    const usage = record(raw);
    if (!Array.isArray(usage.windows)) return null;
    const read = usage.windows.map(windowOf).filter((window): window is CallWindow => window !== null);
    const windows = CALL_WINDOWS.map((name) => read.find((window) => window.window === name)).filter((window): window is CallWindow => window !== undefined);
    return {family: String(usage.family ?? ''), plugin_code: String(usage.plugin_code ?? ''), windows};
}

/**
 * The core's call-limit fields (project 76, U4), which the server lists on every plugin that calls an external service
 * and on every group that shares credits: the «Calls» block draws them (U5).
 */
export const CALL_LIMIT_KEYS = ['call_limit_minute', 'call_limit_hour', 'call_limit_day', 'call_limit_week', 'call_limit_month'] as const;

/** `fields` with the call-limit fields grouped after the plugin's own (kept in the server's order), in window order. */
function limitsLast(fields: SettingField[]): SettingField[] {
    const keys: readonly string[] = CALL_LIMIT_KEYS;
    const own = fields.filter((field) => !keys.includes(field.key));
    const limits = fields.filter((field) => keys.includes(field.key)).sort((a, b) => keys.indexOf(a.key) - keys.indexOf(b.key));
    return [...own, ...limits];
}

export function entryOf(raw: unknown): PluginSettingsEntry {
    const entry = record(raw);
    const usage = usageOf(entry.call_usage);
    return {
        family: oneOf<SettingsFamily>(entry.family, FAMILIES, 'asset'),
        plugin_code: String(entry.plugin_code ?? ''),
        plugin_name: String(entry.plugin_name ?? entry.plugin_code ?? ''),
        icon_url: textOrNull(entry.icon_url),
        configured: entry.configured === true,
        fields: Array.isArray(entry.fields) ? limitsLast(entry.fields.map(fieldOf)) : [],
        groups: Array.isArray(entry.groups) ? entry.groups.filter((name): name is string => typeof name === 'string' && name.length > 0) : [],
        used_by: Array.isArray(entry.used_by) ? entry.used_by.map(refOf).filter((ref): ref is PluginRef => ref !== null) : [],
        name_key: textOrNull(entry.name_key),
        // No block, no key: an entry without usage is exactly what it was before U4
        ...(usage ? {call_usage: usage} : {}),
    };
}

/**
 * The plugins that declare settings, with each field's state for the caller; an entry listed only for its usage block
 * (the managed profile, U4b) included. Without `pluginCode` a test-only plugin is not listed (the API lists one only
 * when named).
 */
export async function fetchPluginSettings(filter: {family?: SettingsFamily; pluginCode?: string} = {}): Promise<PluginSettingsEntry[]> {
    const queries: {family?: SettingsFamily; plugin_code?: string} = {};
    if (filter.family) queries.family = filter.family;
    if (filter.pluginCode) queries.plugin_code = filter.pluginCode;
    const answer = await zodiosApi.get_plugin_settings_api_v1_settings_plugins_get({queries});
    return (answer.plugins ?? []).map(entryOf);
}

/** The settings of one plugin for the caller; null when it declares none (or is not one the caller may see). */
export async function fetchPluginEntry(family: SettingsFamily, pluginCode: string): Promise<PluginSettingsEntry | null> {
    const entries = await fetchPluginSettings({family, pluginCode});
    return entries.find((entry) => entry.family === family && entry.plugin_code === pluginCode) ?? null;
}

function refusal(error: unknown): {status: number | undefined; body: unknown} {
    if (isAxiosError(error)) return {status: error.response?.status, body: error.response?.data};
    if (error instanceof ApiError) return {status: error.status, body: error.data};
    return {status: undefined, body: undefined};
}

function resultOf(raw: unknown): PluginSettingWriteResult {
    const result = record(raw);
    return {field_key: String(result.field_key ?? ''), success: result.success === true, error_code: textOrNull(result.error_code)};
}

/** Write `items`, all or nothing. Never throws: every end is a `SaveOutcome`. */
export async function savePluginSettings(items: PluginSettingWriteItem[]): Promise<SaveOutcome> {
    try {
        await zodiosApi.update_plugin_settings_api_v1_settings_plugins_bulk_patch({items});
        return {kind: 'saved'};
    } catch (error) {
        const {status, body} = refusal(error);
        if (status === 409) return {kind: 'conflict'};
        if (status === 503) return {kind: 'keyUnavailable'};
        const results = record(record(body).detail).results;
        if (status === 422 && Array.isArray(results)) return {kind: 'refused', results: results.map(resultOf)};
        return {kind: 'failed'};
    }
}
