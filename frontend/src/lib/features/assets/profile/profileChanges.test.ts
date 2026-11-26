/**
 * profileChanges — one change of the asset profile as the tables show it (plan 68, E6a; 87, A3): its kind, the value
 * before, the value after, and the note the two values do not say.
 *
 * The kind is a pure function of the change (`FAProfileChange`) and its voice; the tests assert the kind, the two values
 * and what the translation is handed, never a translated text.
 */
import {describe, expect, it} from 'vitest';
import type {ProfileVoice} from './profileStore';
import {changeKind, changeParts, type ProfileChange} from './profileChanges';

function voice(key: string, shape: string, extra: Partial<ProfileVoice> = {}): ProfileVoice {
    return {key, shape, groups: ['other'], volatile: false, ...extra} as unknown as ProfileVoice;
}

const TER = voice('ter', 'percentage');
const YIELD = voice('yield_gross', 'percentage', {volatile: true});
const DESCRIPTION = voice('description', 'text');
const GEOGRAPHY = voice('geography', 'map', {map_keys: 'country'});

function change(fields: Partial<ProfileChange>): ProfileChange {
    return {
        id: 1,
        key: 'ter',
        value: '0.0014',
        previous: null,
        has_previous: false,
        source: 'justetf',
        user_id: null,
        user_name: null,
        user_avatar_url: null,
        read_on: '2026-11-08',
        source_date: null,
        created_at: '2026-11-08T10:00:00Z',
        previous_source: null,
        previous_user_id: null,
        previous_user_name: null,
        previous_read_on: null,
        previous_source_date: null,
        ...fields,
    } as ProfileChange;
}

describe('changeKind', () => {
    it('names the first value of a voice by who gave it', () => {
        expect(changeKind(change({}), TER)).toBe('first');
        expect(changeKind(change({source: 'user', user_id: 3}), TER)).toBe('firstByHand');
        expect(changeKind(change({source: 'legacy'}), TER)).toBe('firstLegacy');
    });

    it('says a value left empty, by hand or by a source', () => {
        expect(changeKind(change({value: null, has_previous: true, previous: '0.0012', source: 'user'}), TER)).toBe('emptied');
        expect(changeKind(change({value: null, has_previous: true, previous: '0.0012'}), TER)).toBe('emptiedBySource');
    });

    it('never says «from» an empty value: a voice written again after it was emptied', () => {
        expect(changeKind(change({source: 'user', user_id: 3, has_previous: true, previous: null, value: '0.0012', previous_source: 'user'}), TER)).toBe('firstByHand');
        expect(changeKind(change({has_previous: true, previous: null, value: '0.0014', previous_source: 'user'}), TER)).toBe('refilled');
        expect(changeKind(change({has_previous: true, previous: null, value: '0.0014', previous_source: 'justetf'}), TER)).toBe('refilled');
    });

    it('says a correction by hand, and a source value that replaces one', () => {
        expect(changeKind(change({source: 'user', has_previous: true, previous: '0.0014', value: '0.0012'}), TER)).toBe('byHand');
        expect(changeKind(change({has_previous: true, previous: '0.0012', value: '0.0014', previous_source: 'user', previous_user_name: 'anna'}), TER)).toBe('backFromHand');
    });

    it('moves a number up or down, and changes anything else', () => {
        expect(changeKind(change({key: 'yield_gross', has_previous: true, previous: '0.034', value: '0.0361', previous_source: 'borsa_italiana'}), YIELD)).toBe('up');
        expect(changeKind(change({key: 'yield_gross', has_previous: true, previous: '0.0361', value: '0.034', previous_source: 'borsa_italiana'}), YIELD)).toBe('down');
        expect(changeKind(change({key: 'description', has_previous: true, previous: 'A fund', value: 'An ETF', previous_source: 'justetf'}), DESCRIPTION)).toBe('changed');
    });

    it('says the new data date of a breakdown whose source dated it', () => {
        const fields = {key: 'geography', has_previous: true, previous: {USA: '1'}, value: {USA: '0.6', JPN: '0.4'}, previous_source: 'justetf', source_date: '2026-09-30', previous_source_date: '2026-08-31'};
        expect(changeKind(change(fields), GEOGRAPHY)).toBe('newSourceDate');
        expect(changeKind(change({...fields, previous_source_date: null}), GEOGRAPHY)).toBe('changed');
    });
});

describe('changeParts', () => {
    const asked: Array<{key: string; values: Record<string, string>}> = [];
    const translate = (key: string, values: Record<string, string> = {}) => {
        asked.push({key, values});
        return key;
    };
    const format = (_voice: ProfileVoice, value: unknown) => `«${typeof value === 'object' ? JSON.stringify(value) : String(value)}»`;
    const day = (iso: string) => `[${iso}]`;
    const source = (code: string) => `<${code}>`;
    const parts = (fields: Partial<ProfileChange>, of: ProfileVoice | null = TER) => changeParts(change(fields), of ?? undefined, {translate, format, day, source});

    it('gives the value before and the value after apart, and no note when they say it all', () => {
        asked.length = 0;
        expect(parts({key: 'yield_gross', has_previous: true, previous: '0.034', value: '0.0361', previous_source: 'borsa_italiana'}, YIELD)).toEqual({kind: 'up', before: '«0.034»', after: '«0.0361»', note: ''});
        expect(parts({key: 'description', has_previous: true, previous: 'A fund.', value: 'An ETF.', previous_source: 'justetf'}, DESCRIPTION)).toEqual({kind: 'changed', before: '«A fund.»', after: '«An ETF.»', note: ''});
        expect(asked, 'nothing asked of the translation').toEqual([]);
    });

    it('leaves a side empty where there is no value: the first one, and one left empty', () => {
        expect(parts({})).toMatchObject({kind: 'first', before: '', after: '«0.0014»', note: 'assets.profile.changes.note.first'});
        expect(parts({value: null, has_previous: true, previous: '0.0012', source: 'user'})).toMatchObject({kind: 'emptied', before: '«0.0012»', after: '', note: 'assets.profile.changes.note.emptied'});
        expect(parts({has_previous: true, previous: null, value: '0.0014', previous_source: 'user'})).toMatchObject({kind: 'refilled', before: '', after: '«0.0014»'});
    });

    it('notes who had corrected a value the source took back, and by whom it is now', () => {
        asked.length = 0;
        const back = parts({has_previous: true, previous: '0.0012', value: '0.0014', previous_source: 'user', previous_user_name: 'anna', previous_read_on: '2026-11-02'});
        expect(back).toEqual({kind: 'backFromHand', before: '«0.0012»', after: '«0.0014»', note: 'assets.profile.changes.note.backFromHand'});
        expect(asked.at(-1)?.values).toEqual({date: '[2026-11-02]', name: 'anna', source: '<justetf>'});
    });

    it('names a deleted author with the words of the profile, never an empty name', () => {
        asked.length = 0;
        parts({has_previous: true, previous: '0.0012', value: '0.0014', previous_source: 'user', previous_user_name: null, previous_read_on: '2026-11-02'});
        expect(asked.map((entry) => entry.key)).toContain('assets.profile.changes.who.deletedUser');
    });

    it('dates a breakdown by its source dates, beside its two values', () => {
        asked.length = 0;
        const dated = parts({key: 'geography', has_previous: true, previous: {USA: '1'}, value: {USA: '0.6'}, previous_source: 'justetf', source_date: '2026-09-30', previous_source_date: '2026-08-31'}, GEOGRAPHY);
        expect(dated).toMatchObject({kind: 'newSourceDate', before: '«{"USA":"1"}»', after: '«{"USA":"0.6"}»'});
        expect(asked.at(-1)).toEqual({key: 'assets.profile.changes.note.newSourceDate', values: {date: '[2026-09-30]', previousDate: '[2026-08-31]'}});
    });

    it('shows a value of a voice the catalogue does not list as it is stored', () => {
        expect(parts({key: 'unknown', has_previous: true, previous: 'a', value: 'b', previous_source: 'justetf'}, null)).toMatchObject({before: 'a', after: 'b'});
    });
});
