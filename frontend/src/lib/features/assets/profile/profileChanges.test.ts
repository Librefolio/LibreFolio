/**
 * profileChanges — «Cosa è cambiato» of one change of the asset profile (plan 68, E6a; the mock of round 39, approved in
 * round 41): which kind of sentence a change gets, and the values the sentence names.
 *
 * The kind is a pure function of the change (`FAProfileChange`) and its voice; the tests assert the kind and the values
 * handed to the translation, never a translated text.
 */
import {describe, expect, it} from 'vitest';
import type {ProfileVoice} from './profileStore';
import {changeKind, changeSentence, type ProfileChange} from './profileChanges';

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

describe('changeSentence', () => {
    const asked: Array<{key: string; values: Record<string, string>}> = [];
    const translate = (key: string, values: Record<string, string> = {}) => {
        asked.push({key, values});
        return key;
    };
    const format = (_voice: ProfileVoice, value: unknown) => `«${typeof value === 'object' ? JSON.stringify(value) : String(value)}»`;
    const day = (iso: string) => `[${iso}]`;
    const source = (code: string) => `<${code}>`;

    it('hands the translation the key of its kind and the values it names', () => {
        asked.length = 0;
        const back = change({has_previous: true, previous: '0.0012', value: '0.0014', previous_source: 'user', previous_user_name: 'anna', previous_read_on: '2026-11-02'});
        const sentence = changeSentence(back, TER, {translate, format, day, source});

        expect(sentence).toEqual({kind: 'backFromHand', text: 'assets.profile.changes.what.backFromHand'});
        expect(asked.at(-1)?.values).toEqual({to: '«0.0014»', from: '«0.0012»', date: '[2026-11-02]', name: 'anna', source: '<justetf>'});
    });

    it('names a deleted author with the words of the profile, never an empty name', () => {
        asked.length = 0;
        changeSentence(change({has_previous: true, previous: '0.0012', value: '0.0014', previous_source: 'user', previous_user_name: null, previous_read_on: '2026-11-02'}), TER, {translate, format, day, source});
        expect(asked.map((entry) => entry.key)).toContain('assets.profile.changes.who.deletedUser');
    });

    it('drops the final full stop of a value: the sentence ends with its own', () => {
        asked.length = 0;
        changeSentence(change({key: 'description', source: 'user', user_id: 3, value: 'A fund of the test.'}), DESCRIPTION, {translate, format: (_voice, value) => String(value), day, source});
        expect(asked.at(-1)?.values).toEqual({to: 'A fund of the test'});
    });

    it('dates a breakdown by its source dates', () => {
        asked.length = 0;
        const fields = {key: 'geography', has_previous: true, previous: {USA: '1'}, value: {USA: '0.6'}, previous_source: 'justetf', source_date: '2026-09-30', previous_source_date: '2026-08-31'};
        changeSentence(change(fields), GEOGRAPHY, {translate, format, day, source});
        expect(asked.at(-1)).toEqual({key: 'assets.profile.changes.what.newSourceDate', values: {date: '[2026-09-30]', previousDate: '[2026-08-31]'}});
    });
});
