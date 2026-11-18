/**
 * callUsage — the rules of the «Calls» block, without the DOM (project 76, lot U5; mock section 2).
 *
 * The contract under test:
 *   - `ownFields` and `isCallLimitField` split an entry's fields: the plugin's own, drawn as generic fields, and the five
 *     core limits, drawn as the block's boxes; `hasCallBlock` is true for an entry with a limit field or a usage block;
 *   - `callBoxes` gives one box per window, in window order: its count (null when no usage was read), its limit, its
 *     field (null when the managed profile hides it: the box is `hidden`), its control (`input` for whoever may change
 *     it, `locked` when a server variable sets it, `text` for a user who may not, `hidden`) and its state (`open`,
 *     `full`, `stopped` for a limit of 0, `invalid` for a limit variable the server refuses);
 *   - `callNote` says what a full or stopped box's note says, by key and values: the window's own sentence with the
 *     count, the limit and when it resumes (the minute and the hour only the time), «stopped» for a limit of 0 (never
 *     «resumes»), the instance's sentence for a hidden limit (no number); `resumeAt` writes that moment in UTC;
 *   - `lockNotes`, `invalidNotes` and `limitsAdminOnly` say what goes under the grid;
 *   - `cardProblem` is the red message at the top of the card: an invalid limit variable, named for an administrator
 *     (the server names it only to them), «stopped» for another user; the managed profile's text when the provider is
 *     not configured and nothing shown explains why;
 *   - `groupCallNoteKey` gives the group's own note (CoinGecko's A8), and nothing for any other entry.
 *
 * Node environment: nothing renders. Dates are written with an explicit locale; the instant `…T23:30:00Z` is on another
 * day in most time zones but UTC's, so a date written in local time would fail here.
 */
import {describe, expect, it} from 'vitest';
import type {CallUsage, CallWindow, CallWindowName, PluginSettingsEntry, SettingField} from './pluginSettingsApi';
import {callBoxes, callNote, cardProblem, groupCallNoteKey, hasCallBlock, invalidNotes, isCallLimitField, limitsAdminOnly, lockNotes, ownFields, resumeAt, type CallBox} from './callUsage';

const WINDOWS: CallWindowName[] = ['minute', 'hour', 'day', 'week', 'month'];
const LATE = '2026-11-18T23:30:00Z';

function field(over: Partial<SettingField> & Pick<SettingField, 'key'>): SettingField {
    return {
        type: 'integer',
        scope: 'system',
        secret: false,
        required: false,
        label: over.key,
        description: '',
        label_key: null,
        description_key: null,
        missing_key: null,
        options: [],
        min_length: null,
        max_length: null,
        minimum: 0,
        maximum: null,
        default: null,
        value: null,
        is_set: false,
        source: 'none',
        locked: false,
        env_variable: null,
        editable: true,
        problem: null,
        updated_at: null,
        ...over,
    };
}

const limit = (window: CallWindowName, over: Partial<SettingField> = {}) => field({key: `call_limit_${window}`, ...over});
const LIMITS = WINDOWS.map((window) => limit(window));
const CURRENCY = field({key: 'preferred_currency', type: 'select', scope: 'user'});

function usage(over: Partial<Record<CallWindowName, Partial<CallWindow>>> = {}): CallUsage {
    return {family: 'asset', plugin_code: 'justetf', windows: WINDOWS.map((window) => ({window, count: 3, limit: null, resets_at: LATE, full: false, ...over[window]}))};
}

function entry(over: Partial<PluginSettingsEntry> = {}): PluginSettingsEntry {
    return {family: 'asset', plugin_code: 'justetf', plugin_name: 'justETF', icon_url: null, configured: true, fields: [CURRENCY, ...LIMITS], groups: [], used_by: [], name_key: null, ...over};
}

const box = (boxes: CallBox[], window: CallWindowName) => boxes.find((candidate) => candidate.window === window) as CallBox;

describe('the fields: the plugin’s own and the limits', () => {
    it('isCallLimitField names the five core keys only', () => {
        expect(LIMITS.every(isCallLimitField)).toBe(true);
        expect(isCallLimitField(CURRENCY)).toBe(false);
        expect(isCallLimitField(field({key: 'call_limit_year'}))).toBe(false);
    });

    it('ownFields keeps the plugin’s own fields, in order, without the limits', () => {
        expect(ownFields(entry({fields: [LIMITS[0], CURRENCY, LIMITS[1]]}))).toStrictEqual([CURRENCY]);
    });

    it('hasCallBlock: a limit field or a usage block makes the block; neither, no block', () => {
        expect(hasCallBlock(entry())).toBe(true);
        expect(hasCallBlock(entry({fields: [], call_usage: usage()}))).toBe(true);
        expect(hasCallBlock(entry({fields: [CURRENCY]}))).toBe(false);
    });
});

describe('callBoxes', () => {
    it('one box per window, in window order, with the usage’s count and limit', () => {
        const boxes = callBoxes(entry({call_usage: usage({day: {count: 412, limit: 2000}})}));

        expect(boxes.map((candidate) => candidate.window)).toStrictEqual(WINDOWS);
        expect(box(boxes, 'day')).toMatchObject({count: 412, limit: 2000, state: 'open', hidden: false, resetsAt: LATE});
        expect(box(boxes, 'minute')).toMatchObject({count: 3, limit: null, state: 'open'});
    });

    it('no usage read: counts are null, the limit comes from the field', () => {
        const boxes = callBoxes(entry({fields: [limit('minute', {value: 30, source: 'db', is_set: true}), ...LIMITS.slice(1)]}));

        expect(box(boxes, 'minute')).toMatchObject({count: null, limit: 30, state: 'open', resetsAt: null});
    });

    it('controls: input for an editable field, locked for a variable’s, text for a user who may not change it', () => {
        const fields = [limit('minute'), limit('hour', {editable: false, locked: true, source: 'env', value: 50}), limit('day', {editable: false}), limit('week'), limit('month')];
        const boxes = callBoxes(entry({fields, call_usage: usage()}));

        expect(boxes.map((candidate) => candidate.control)).toStrictEqual(['input', 'locked', 'text', 'input', 'input']);
    });

    it('a window with usage and no field is hidden (the managed profile): its control is hidden, its limit null', () => {
        const boxes = callBoxes(entry({fields: [CURRENCY, ...LIMITS.slice(0, 4)], call_usage: usage()}));

        expect(box(boxes, 'month')).toMatchObject({hidden: true, control: 'hidden', field: null, limit: null});
        expect(box(boxes, 'week')).toMatchObject({hidden: false});
    });

    it('states: full on the server’s word, stopped for a limit of 0, invalid for a variable the server refuses', () => {
        const fields = [limit('minute'), limit('hour'), limit('day', {editable: false, locked: true, source: 'env', problem: 'invalid_env'}), limit('week'), limit('month')];
        const boxes = callBoxes(entry({fields, call_usage: usage({minute: {count: 30, limit: 30, full: true}, hour: {count: 0, limit: 0, full: true}})}));

        expect(boxes.map((candidate) => candidate.state)).toStrictEqual(['full', 'stopped', 'invalid', 'open', 'open']);
    });

    it('a hidden window the server says is full is full', () => {
        const boxes = callBoxes(entry({fields: [], call_usage: usage({month: {count: 10000, full: true}})}));

        expect(box(boxes, 'month')).toMatchObject({state: 'full', hidden: true, limit: null});
    });
});

describe('resumeAt — the end of the window, in UTC', () => {
    it('writes the day and the time of UTC, whatever the machine’s zone', () => {
        expect(resumeAt(LATE, 'en-GB')).toStrictEqual({date: '18 November', time: '23:30'});
        expect(resumeAt('2026-12-01T00:00:00Z', 'it-IT')).toStrictEqual({date: '1 dicembre', time: '00:00'});
    });
});

describe('callNote — what a full or stopped box says', () => {
    const fullOn = (window: CallWindowName, over: Partial<CallWindow> = {}) => box(callBoxes(entry({call_usage: usage({[window]: {count: 2000, limit: 2000, full: true, ...over}})})), window);

    it('a full day, week or month: its own sentence, count, limit, date and time', () => {
        expect(callNote(fullOn('day'), 'en-GB')).toStrictEqual({key: 'pluginSettings.calls.full.day', values: {count: '2,000', limit: '2,000', date: '18 November', time: '23:30'}});
        expect(callNote(fullOn('week'), 'en-GB')?.key).toBe('pluginSettings.calls.full.week');
        expect(callNote(fullOn('month'), 'en-GB')?.key).toBe('pluginSettings.calls.full.month');
    });

    it('a full minute or hour: the time only', () => {
        expect(callNote(fullOn('minute', {count: 30, limit: 30}), 'en-GB')).toStrictEqual({key: 'pluginSettings.calls.full.minute', values: {count: '30', limit: '30', time: '23:30'}});
        expect(callNote(fullOn('hour'), 'en-GB')?.key).toBe('pluginSettings.calls.full.hour');
        expect(callNote(fullOn('hour'), 'en-GB')?.values).not.toHaveProperty('date');
    });

    it('a limit of 0: «stopped», never «resumes»', () => {
        expect(callNote(fullOn('day', {count: 0, limit: 0}), 'en-GB')).toStrictEqual({key: 'pluginSettings.calls.stopped.day', values: {}});
        expect(callNote(fullOn('minute', {count: 0, limit: 0}), 'en-GB')?.key).toBe('pluginSettings.calls.stopped.minute');
    });

    it('a hidden limit, full: the instance’s sentence, no number; the time only for the minute and the hour', () => {
        const hidden = (window: CallWindowName) => box(callBoxes(entry({fields: [], call_usage: usage({[window]: {count: 10000, full: true}})})), window);

        expect(callNote(hidden('month'), 'en-GB')).toStrictEqual({key: 'pluginSettings.calls.managedFull', values: {date: '18 November', time: '23:30'}});
        expect(callNote(hidden('hour'), 'en-GB')).toStrictEqual({key: 'pluginSettings.calls.managedFullAt', values: {time: '23:30'}});
    });

    it('an open or invalid box has no note', () => {
        const boxes = callBoxes(entry({fields: [limit('minute', {problem: 'invalid_env', locked: true, editable: false}), ...LIMITS.slice(1)], call_usage: usage()}));

        expect(boxes.map((candidate) => callNote(candidate, 'en-GB'))).toStrictEqual([null, null, null, null, null]);
    });
});

describe('the notes under the grid', () => {
    it('lockNotes: one per window a variable sets, with its name when the server gives it; an invalid one is not a lock note', () => {
        const fields = [
            limit('minute'),
            limit('hour', {editable: false, locked: true, source: 'env', value: 9}),
            limit('day', {editable: false, locked: true, source: 'env', problem: 'invalid_env', env_variable: 'LF_DAY'}),
            limit('week'),
            limit('month', {editable: false, locked: true, source: 'env', value: 50000, env_variable: 'LF_MONTH'}),
        ];
        const boxes = callBoxes(entry({fields, call_usage: usage()}));

        expect(lockNotes(boxes)).toStrictEqual([
            {window: 'hour', variable: null},
            {window: 'month', variable: 'LF_MONTH'},
        ]);
    });

    it('invalidNotes: the invalid windows whose variable the server names (administrators only)', () => {
        const named = limit('day', {editable: false, locked: true, source: 'env', problem: 'invalid_env', env_variable: 'LF_DAY'});
        const unnamed = limit('day', {editable: false, locked: true, source: 'env', problem: 'invalid_env'});

        expect(invalidNotes(callBoxes(entry({fields: [LIMITS[0], LIMITS[1], named, LIMITS[3], LIMITS[4]]})))).toStrictEqual([{window: 'day', variable: 'LF_DAY'}]);
        expect(invalidNotes(callBoxes(entry({fields: [LIMITS[0], LIMITS[1], unnamed, LIMITS[3], LIMITS[4]]})))).toStrictEqual([]);
    });

    it('limitsAdminOnly: true when a limit is read-only for want of the role, not for a variable', () => {
        const member = LIMITS.map((candidate) => ({...candidate, editable: false}));
        const lockedOnly = LIMITS.map((candidate) => ({...candidate, editable: false, locked: true}));

        expect(limitsAdminOnly(callBoxes(entry({fields: member})))).toBe(true);
        expect(limitsAdminOnly(callBoxes(entry()))).toBe(false);
        expect(limitsAdminOnly(callBoxes(entry({fields: lockedOnly})))).toBe(false);
        expect(limitsAdminOnly(callBoxes(entry({fields: [], call_usage: usage()}))), 'the managed profile: nothing to change, no such line').toBe(false);
    });
});

describe('cardProblem — the red message at the top of the card', () => {
    const invalidDay = (variable: string | null) => limit('day', {editable: false, locked: true, source: 'env', problem: 'invalid_env', env_variable: variable});

    it('an invalid limit variable, named: the administrator’s text with the variable and the provider', () => {
        const fields = [CURRENCY, LIMITS[0], LIMITS[1], invalidDay('LF_DAY'), LIMITS[3], limit('month', {editable: false, locked: true, source: 'env', problem: 'invalid_env', env_variable: 'LF_MONTH'})];

        expect(cardProblem(entry({configured: false, fields}), 'justETF')).toStrictEqual({kind: 'invalidLimitAdmin', key: 'pluginSettings.notConfigured.invalidLimitAdmin', values: {provider: 'justETF', variable: 'LF_DAY, LF_MONTH'}});
    });

    it('an invalid limit variable, not named (another user): «stopped, tell the administrator»', () => {
        const fields = [CURRENCY, LIMITS[0], LIMITS[1], invalidDay(null), LIMITS[3], LIMITS[4]];

        expect(cardProblem(entry({configured: false, fields}), 'justETF')).toStrictEqual({kind: 'invalidMember', key: 'pluginSettings.notConfigured.invalidMember', values: {provider: 'justETF'}});
    });

    it('the managed profile: not configured, every limit hidden, nothing shown to fix → the managed text', () => {
        expect(cardProblem(entry({configured: false, fields: [], call_usage: usage()}), 'Yahoo Finance')).toStrictEqual({kind: 'managed', key: 'pluginSettings.notConfigured.managed', values: {provider: 'Yahoo Finance'}});
    });

    it('no message: configured; or something shown explains it (a required field unset, a field’s problem, a group)', () => {
        const managed = {fields: [], call_usage: usage()};
        expect(cardProblem(entry(), 'justETF')).toBeNull();
        expect(cardProblem(entry({...managed}), 'Yahoo Finance'), 'managed but configured').toBeNull();
        expect(cardProblem(entry({...managed, configured: false, fields: [field({key: 'api_key', secret: true, required: true, type: 'string'})]}), 'X')).toBeNull();
        expect(cardProblem(entry({...managed, configured: false, fields: [field({key: 'region', type: 'string', problem: 'invalid_stored'})]}), 'X')).toBeNull();
        expect(cardProblem(entry({...managed, configured: false, groups: ['mock']}), 'X')).toBeNull();
        expect(cardProblem(entry({configured: false, fields: [CURRENCY, ...LIMITS]}), 'X'), 'not managed, no invalid limit: the fields say why').toBeNull();
    });
});

describe('groupCallNoteKey', () => {
    it('CoinGecko’s group has its note (A8); its price plugin, another group and a plugin have none', () => {
        expect(groupCallNoteKey(entry({family: 'group', plugin_code: 'coingecko'}))).toBe('pluginSettings.group.coingecko.callsNote');
        expect(groupCallNoteKey(entry({family: 'asset', plugin_code: 'coingecko'}))).toBeNull();
        expect(groupCallNoteKey(entry({family: 'group', plugin_code: 'mock'}))).toBeNull();
        expect(groupCallNoteKey(entry({family: 'group', plugin_code: 'constructor'}))).toBeNull();
    });
});
