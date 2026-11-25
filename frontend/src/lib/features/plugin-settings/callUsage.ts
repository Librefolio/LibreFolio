/**
 * The «Calls» block of a plugin's card, without the DOM (project 76, lot U5; plan §3.5 «La pagina delle impostazioni»,
 * mock section 2): the five windows of the call counter, their limits, and what the block says about them.
 * `PluginCallUsage.svelte` only draws what these functions decide.
 *
 * The data is the catalogue's (U4): the five core limit fields (`call_limit_minute` … `call_limit_month`, system
 * integers, empty = no limit, 0 = stopped) and the `call_usage` block of the entry that owns the count. The managed
 * profile hides a limit its variable sets: the field is absent and the window's `limit` null, `full` still judged by the
 * server on the real limit. So «hidden» is decided per window: a window with usage and no field.
 *
 * Every class and key below is a whole literal (theme-roles rule 6, i18n audit); a box's tint is one lookup, never two
 * classes for one property (design-system rule 4).
 */
import {own} from './pluginSettingsForm';
import {CALL_LIMIT_KEYS, CALL_WINDOWS, type CallWindowName, type PluginSettingsEntry, type SettingField} from './pluginSettingsApi';

/** Whether `field` is one of the core's five call limits: drawn in the block, not as a generic field. */
export function isCallLimitField(field: SettingField): boolean {
    return (CALL_LIMIT_KEYS as readonly string[]).includes(field.key);
}

/** The plugin's own fields, in order: every field but the call limits. */
export function ownFields(entry: PluginSettingsEntry): SettingField[] {
    return entry.fields.filter((field) => !isCallLimitField(field));
}

/** Whether the card has a «Calls» block: a limit field, or a usage block (the managed profile hides every limit). */
export function hasCallBlock(entry: PluginSettingsEntry): boolean {
    return entry.call_usage !== undefined || entry.fields.some(isCallLimitField);
}

/** How a window stands: `stopped` is a limit of 0 (it never resumes by itself), `invalid` a limit variable the server
 * refuses (the provider is stopped until it is fixed). */
export type CallBoxState = 'open' | 'full' | 'stopped' | 'invalid';

/** What the box offers: an input (whoever may change the limit), the value a server variable sets, the limit as text
 * (a user who may not change it), or nothing (the managed profile hides it). */
export type CallBoxControl = 'input' | 'locked' | 'text' | 'hidden';

export interface CallBox {
    window: CallWindowName;
    /** The calls of the window of now; null when the server could not read the counts. */
    count: number | null;
    /** The limit in force, as far as it is shown; null for none, and for a hidden one. */
    limit: number | null;
    /** The limit's field; null when the managed profile hides it. */
    field: SettingField | null;
    hidden: boolean;
    state: CallBoxState;
    control: CallBoxControl;
    /** When the window ends (ISO, UTC); null without usage. */
    resetsAt: string | null;
}

function integerOrNull(value: unknown): number | null {
    return typeof value === 'number' && Number.isInteger(value) ? value : null;
}

/** One box per window, in window order. */
export function callBoxes(entry: PluginSettingsEntry): CallBox[] {
    return CALL_WINDOWS.map((window) => {
        const field = entry.fields.find((candidate) => candidate.key === `call_limit_${window}`) ?? null;
        const usage = entry.call_usage?.windows.find((candidate) => candidate.window === window) ?? null;
        const hidden = field === null && usage !== null;
        const limit = hidden ? null : usage ? usage.limit : integerOrNull(field?.value);
        let state: CallBoxState = 'open';
        if (field?.problem === 'invalid_env') state = 'invalid';
        else if (limit === 0) state = 'stopped';
        else if (usage?.full) state = 'full';
        let control: CallBoxControl = 'hidden';
        if (field) control = field.editable ? 'input' : field.locked ? 'locked' : 'text';
        return {window, count: usage?.count ?? null, limit, field, hidden, state, control, resetsAt: usage?.resets_at ?? null};
    });
}

// =============================================================================
// Texts
// =============================================================================

export const CALL_WINDOW_KEYS: Record<CallWindowName, string> = {
    minute: 'pluginSettings.calls.window.minute',
    hour: 'pluginSettings.calls.window.hour',
    day: 'pluginSettings.calls.window.day',
    week: 'pluginSettings.calls.window.week',
    month: 'pluginSettings.calls.window.month',
};

/** A full window's note, one per window: the adjective changes the sentence. The minute and the hour name the time only. */
const FULL_KEYS: Record<CallWindowName, string> = {
    minute: 'pluginSettings.calls.full.minute',
    hour: 'pluginSettings.calls.full.hour',
    day: 'pluginSettings.calls.full.day',
    week: 'pluginSettings.calls.full.week',
    month: 'pluginSettings.calls.full.month',
};

const STOPPED_KEYS: Record<CallWindowName, string> = {
    minute: 'pluginSettings.calls.stopped.minute',
    hour: 'pluginSettings.calls.stopped.hour',
    day: 'pluginSettings.calls.stopped.day',
    week: 'pluginSettings.calls.stopped.week',
    month: 'pluginSettings.calls.stopped.month',
};

/** The windows that end within the day: their note names the time, not the date. */
const SAME_DAY: readonly CallWindowName[] = ['minute', 'hour'];

export interface Message {
    key: string;
    values: Record<string, string>;
}

/** When a window ends, in UTC like the windows: «18 November» and «23:30» in the reader's language. */
export function resumeAt(iso: string, locale: string): {date: string; time: string} {
    const moment = new Date(iso);
    return {
        date: new Intl.DateTimeFormat(locale, {day: 'numeric', month: 'long', timeZone: 'UTC'}).format(moment),
        time: new Intl.DateTimeFormat(locale, {hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'UTC'}).format(moment),
    };
}

/** A count or a limit in the reader's language. */
export function formatCount(value: number, locale: string): string {
    return new Intl.NumberFormat(locale).format(value);
}

/**
 * The note a box takes under the grid, or null: a limit of 0 is «stopped» (it never resumes by itself); a full window
 * says its count, its limit and when it resumes; a full hidden one says only when (no number, the consultant's rule).
 */
export function callNote(box: CallBox, locale: string): Message | null {
    if (box.state === 'stopped') return {key: STOPPED_KEYS[box.window], values: {}};
    if (box.state !== 'full' || box.resetsAt === null) return null;
    const {date, time} = resumeAt(box.resetsAt, locale);
    const sameDay = SAME_DAY.includes(box.window);
    const when: Record<string, string> = sameDay ? {time} : {date, time};
    if (box.hidden || box.limit === null) return sameDay ? {key: 'pluginSettings.calls.managedFullAt', values: when} : {key: 'pluginSettings.calls.managedFull', values: when};
    return {key: FULL_KEYS[box.window], values: {count: formatCount(box.count ?? 0, locale), limit: formatCount(box.limit, locale), ...when}};
}

/** The windows a server variable sets, with the variable's name when the server gives it (administrators only). */
export function lockNotes(boxes: readonly CallBox[]): Array<{window: CallWindowName; variable: string | null}> {
    return boxes.filter((box) => box.control === 'locked' && box.state !== 'invalid').map((box) => ({window: box.window, variable: box.field?.env_variable ?? null}));
}

/** The invalid windows whose variable the server names: administrators only, so another user gets none. */
export function invalidNotes(boxes: readonly CallBox[]): Array<{window: CallWindowName; variable: string}> {
    return boxes.flatMap((box) => (box.state === 'invalid' && box.field?.env_variable ? [{window: box.window, variable: box.field.env_variable}] : []));
}

/** Whether a limit is read-only for want of the role: «Only an administrator can change the limits.». */
export function limitsAdminOnly(boxes: readonly CallBox[]): boolean {
    return boxes.some((box) => box.control === 'text');
}

export interface CardProblem extends Message {
    kind: 'invalidLimitAdmin' | 'invalidMember' | 'managed';
}

/**
 * The red message at the top of a card whose provider is stopped (mock section 2.4), or null:
 *   - a limit variable the server refuses: named (the server names it to an administrator only) with the provider, or
 *     «stopped, tell the administrator» for another user — the texts of the common window (`notConfigured.ts`);
 *   - the managed profile: the catalogue's own reason (U5b), `invalid_locked_setting` — the managed text, which names
 *     nothing, the same for everyone, with no button; any other reason shows nothing on top.
 */
export function cardProblem(entry: PluginSettingsEntry, provider: string, managed: boolean): CardProblem | null {
    // U5b (the consultant, 19/11): in the managed profile the catalogue's own reason decides, the same for an administrator
    // and a member, with no button: a variable of the hoster locks a field with an invalid value
    if (managed) return entry.reason === 'invalid_locked_setting' ? {kind: 'managed', key: 'pluginSettings.notConfigured.managed', values: {provider}} : null;
    const invalid = entry.fields.filter((field) => isCallLimitField(field) && field.problem === 'invalid_env');
    if (invalid.length > 0) {
        const variables = invalid.map((field) => field.env_variable).filter((name): name is string => !!name);
        if (variables.length > 0) return {kind: 'invalidLimitAdmin', key: 'pluginSettings.notConfigured.invalidLimitAdmin', values: {provider, variable: variables.join(', ')}};
        return {kind: 'invalidMember', key: 'pluginSettings.notConfigured.invalidMember', values: {provider}};
    }
    return null;
}

/** A shared group's own note on its count (CoinGecko's A8: its month may start on another day), by group name. */
const GROUP_CALL_NOTE_KEYS: Readonly<Record<string, string>> = {
    coingecko: 'pluginSettings.group.coingecko.callsNote',
};

export function groupCallNoteKey(entry: PluginSettingsEntry): string | null {
    return entry.family === 'group' ? (own(GROUP_CALL_NOTE_KEYS, entry.plugin_code) ?? null) : null;
}

// =============================================================================
// Classes: whole literals, colour roles only
// =============================================================================

type Tone = 'plain' | 'warning' | 'danger';

/** The tint of a box's state (rule 12): amber for a full or stopped window, red for an invalid variable. */
export function callTone(box: CallBox): Tone {
    if (box.state === 'invalid') return 'danger';
    return box.state === 'full' || box.state === 'stopped' ? 'warning' : 'plain';
}

/** A window's box, by the width of its «Calls» block (the developer, 19/11, project 76 S1c; container queries, the block
 * is the `@container`): narrow (a phone), the window, the count and the limit on one line; from 24rem, the count on the
 * window's line and the limit below it. A flex row that WRAPS, not a grid (81 U47): the label never shrinks and is never
 * broken, the count never breaks, and when the two do not fit a box's width (the member's «0 nessun limite» in a
 * five-box row, an Italian «Settimana») the count goes to the next line, on the right, instead of over the label. */
export const CALL_BOX_CLASSES: Record<Tone, string> = {
    plain: 'flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-1 rounded-md border border-lf-subtle px-2 py-1.5 @sm:py-2',
    warning: 'flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-1 rounded-md border border-lf-warning-line bg-lf-warning-soft px-2 py-1.5 @sm:py-2',
    danger: 'flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-1 rounded-md border border-lf-danger-line bg-lf-danger-soft px-2 py-1.5 @sm:py-2',
};

export const CALL_LABEL_CLASSES: Record<Tone, string> = {
    plain: 'shrink-0 whitespace-nowrap text-xs text-lf-muted',
    warning: 'shrink-0 whitespace-nowrap text-xs text-lf-warning-on-soft',
    danger: 'shrink-0 whitespace-nowrap text-xs text-lf-danger-on-soft',
};

export const CALL_COUNT_CLASSES: Record<Tone, string> = {
    plain: 'whitespace-nowrap text-sm font-semibold tabular-nums text-lf-primary @sm:ml-auto @sm:text-right',
    warning: 'whitespace-nowrap text-sm font-semibold tabular-nums text-lf-warning-on-soft @sm:ml-auto @sm:text-right',
    danger: 'whitespace-nowrap text-sm font-semibold tabular-nums text-lf-danger-on-soft @sm:ml-auto @sm:text-right',
};

export const CALL_SMALL_CLASSES: Record<Tone, string> = {
    plain: 'text-xs font-normal text-lf-secondary',
    warning: 'text-xs font-normal text-lf-warning-on-soft',
    danger: 'text-xs font-normal text-lf-danger-on-soft',
};

/** The value a server variable sets, drawn like a field nobody can type in. */
export const CALL_LOCKED_CLASSES: Record<Tone, string> = {
    plain: 'flex min-h-7 min-w-[8.5rem] flex-1 items-center gap-1 rounded-md border border-lf-subtle bg-lf-panel px-2 py-1 text-xs tabular-nums text-lf-secondary',
    warning: 'flex min-h-7 min-w-[8.5rem] flex-1 items-center gap-1 rounded-md border border-lf-warning-line bg-lf-card px-2 py-1 text-xs tabular-nums text-lf-warning-on-soft',
    danger: 'flex min-h-7 min-w-[8.5rem] flex-1 items-center gap-1 rounded-md border border-lf-danger-line bg-lf-card px-2 py-1 text-xs tabular-nums text-lf-danger-on-soft',
};

/** A limit's input: the card's input roles (`INPUT_CLASS`), compact and without the number spinner, so «No limit» and a
 * seven-digit limit fit a box of the five-column row. Beside the label and the count on a narrow block (one box per line), the
 * whole line below them otherwise. */
export const CALL_INPUT_CLASS =
    'min-w-[8.5rem] flex-1 rounded-md border border-lf-input bg-lf-field px-2 py-1 text-xs tabular-nums text-lf-primary placeholder:text-lf-placeholder [appearance:textfield] hover:border-lf-input-hover focus:outline-none focus:ring-2 focus:ring-lf-focus disabled:cursor-not-allowed disabled:opacity-50 @sm:min-w-0 @sm:flex-none @sm:basis-full [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none';
