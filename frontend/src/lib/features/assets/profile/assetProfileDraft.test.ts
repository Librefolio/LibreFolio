/**
 * assetProfileDraft (plan 68, E8b): the profile's pending changes as the asset window holds them, without a DOM.
 *
 * Pinned (plan E8, PROF §14.8; the advisor's review of the E8b design):
 * - the «Dati del profilo» row counts every pending change, the automatic fills too (as the mock), and names them in the
 *   catalogue's order;
 * - the automatic «Chiedi» starts only at creation, with the enrichers settled — «Riconosci» done or a list the user
 *   applied — never on the proposal still growing, never in edit mode, never in the tour's preview, never without an
 *   enricher; one question per (type, list);
 * - its answer fills the empty voices only: a voice the user wrote always wins, and a difference is dropped (the
 *   comparison window is the user's own «Chiedi»); a later answer replaces the fills the user did not touch;
 * - a fill whose source left the list is dropped (the creation would refuse the whole asset: «not an enricher of this
 *   asset»);
 * - the automatic fills alone are not the user's changes (they must not ask to discard anything);
 * - a pending change the window would refuse (a broker file's prefill can be wrong) blocks the save.
 */
import {describe, expect, it} from 'vitest';
import * as draft from './assetProfileDraft';
import type {AskAnswer, PendingChanges, PendingVoice} from './profileEditState';
import type {ProfileVoice} from './profileStore';

function voice(key: string, shape: string, extra: Partial<ProfileVoice> = {}): ProfileVoice {
    return {key, shape, sign: null, unit: null, groups: [], key_figure: false, charted: false, volatile: false, choices: [], map_keys: null, topic: 'structure', ...extra} as ProfileVoice;
}

const CATALOGUE: ProfileVoice[] = [voice('geography', 'map', {map_keys: 'country'}), voice('ter', 'percentage', {sign: 'non_negative'}), voice('fund_provider', 'text'), voice('fund_domicile', 'country'), voice('inception_date', 'date')];
const JUSTETF = {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'};
const fill = (key: string, value: unknown, source = 'justetf'): PendingVoice => ({key, kind: 'source', value, source, seen: value, origin: 'source'});
const typed = (key: string, value: unknown): PendingVoice => ({key, kind: 'value', value, origin: 'new'});
const answer = (voices: Record<string, unknown>, source = 'justetf'): AskAnswer => ({voices: Object.fromEntries(Object.entries(voices).map(([key, value]) => [key, {value, source}])), outcomes: [{code: source, status: 'ok'}]});

describe('the «Dati del profilo» row', () => {
    it('counts every pending change, the fills too, and names them in the catalogue order', () => {
        const pending: PendingChanges = {fund_domicile: fill('fund_domicile', 'IRL'), ter: typed('ter', '0.002'), unknown_voice: typed('unknown_voice', 'x')};
        expect(draft.profileRowSummary(pending, CATALOGUE)).toEqual({count: 3, keys: ['ter', 'fund_domicile', 'unknown_voice']});
        expect(draft.profileRowSummary({}, CATALOGUE)).toEqual({count: 0, keys: []});
    });
});

describe('when the automatic «Chiedi» starts', () => {
    const base = {editMode: false, tourPreview: false, assetType: 'ETF', enrichers: {justetf: JUSTETF}, settled: true};

    it('asks with the type and the settled list at creation', () => {
        expect(draft.autoAskRequest(base)).toEqual({asset_type: 'ETF', enrichers: {justetf: JUSTETF}});
    });

    it('waits while the list is still growing, and asks nothing in edit mode, in the preview or without an enricher', () => {
        expect(draft.autoAskRequest({...base, settled: false})).toBeNull();
        expect(draft.autoAskRequest({...base, editMode: true})).toBeNull();
        expect(draft.autoAskRequest({...base, tourPreview: true})).toBeNull();
        expect(draft.autoAskRequest({...base, enrichers: {}})).toBeNull();
        expect(draft.autoAskRequest({...base, assetType: ''})).toBeNull();
    });

    it('keys a question by the type and the list, in its order', () => {
        const one = draft.autoAskKey({asset_type: 'ETF', enrichers: {justetf: JUSTETF, yahoo_finance: {identifier_type: 'TICKER', identifier: 'VWCE'}}});
        const reordered = draft.autoAskKey({asset_type: 'ETF', enrichers: {yahoo_finance: {identifier_type: 'TICKER', identifier: 'VWCE'}, justetf: JUSTETF}});
        expect(one).not.toBe(reordered);
        expect(one).toBe(draft.autoAskKey({asset_type: 'ETF', enrichers: {justetf: {...JUSTETF}, yahoo_finance: {identifier_type: 'TICKER', identifier: 'VWCE'}}}));
    });
});

describe('what the answer does to the pending changes', () => {
    it('fills the empty voices «dalla fonte», keeps what the user wrote, and drops a difference', () => {
        const pending: PendingChanges = {ter: typed('ter', '0.002')};
        const {pending: next, auto} = draft.mergeAutoFills(pending, {}, answer({ter: '0.0022', fund_provider: 'Vanguard'}), {});
        expect(next.ter).toEqual(typed('ter', '0.002'));
        expect(next.fund_provider).toEqual(fill('fund_provider', 'Vanguard'));
        expect(Object.keys(auto)).toEqual(['fund_provider']);
    });

    it('replaces, on a later answer, the fills the user did not touch, and keeps the one the user changed', () => {
        const first = draft.mergeAutoFills({}, {}, answer({fund_provider: 'Vanguard', fund_domicile: 'IRL'}), {});
        const touched: PendingChanges = {...first.pending, fund_domicile: typed('fund_domicile', 'LUX')};
        const second = draft.mergeAutoFills(touched, first.auto, answer({fund_provider: 'Vanguard Group'}), {});
        expect(second.pending.fund_provider).toEqual(fill('fund_provider', 'Vanguard Group'));
        expect(second.pending.fund_domicile).toEqual(typed('fund_domicile', 'LUX'));
        expect(Object.keys(second.auto)).toEqual(['fund_provider']);
    });

    it('fills nothing over a value «Adesso» already holds', () => {
        const {pending} = draft.mergeAutoFills({}, {}, answer({fund_provider: 'Vanguard'}), {fund_provider: {value: 'Vanguard Asset Management', source: 'user'}});
        expect(pending).toEqual({});
    });
});

describe('the fills of a source that left the list', () => {
    it('are dropped, and the other changes stay', () => {
        const pending: PendingChanges = {fund_provider: fill('fund_provider', 'Vanguard', 'justetf'), fund_domicile: fill('fund_domicile', 'IRL', 'yahoo_finance'), ter: typed('ter', '0.002')};
        expect(Object.keys(draft.withoutFillsOutside(pending, {justetf: JUSTETF}))).toEqual(['fund_provider', 'ter']);
    });
});

describe('the changes that count as the user’s', () => {
    it('leaves out the automatic fills the user did not touch', () => {
        const auto = {fund_provider: fill('fund_provider', 'Vanguard')};
        const pending: PendingChanges = {...auto, ter: typed('ter', '0.002')};
        expect(Object.keys(draft.userChanges(pending, auto))).toEqual(['ter']);
        expect(Object.keys(draft.userChanges({...pending, fund_provider: typed('fund_provider', 'Vanguard Group')}, auto))).toEqual(['fund_provider', 'ter']);
    });
});

describe('a pending change the window would refuse', () => {
    it('blocks the save: a number that is no number, a date that is no date', () => {
        expect(draft.profileBlocksSave({ter: typed('ter', '0.002'), inception_date: typed('inception_date', '2019-07-23')}, CATALOGUE)).toBe(false);
        expect(draft.profileBlocksSave({ter: typed('ter', 'abc')}, CATALOGUE)).toBe(true);
        expect(draft.profileBlocksSave({inception_date: typed('inception_date', '23/07/2019')}, CATALOGUE)).toBe(true);
    });

    it('does not judge a voice the catalogue does not list, nor a fill or an emptied voice', () => {
        expect(draft.profileBlocksSave({unknown_voice: typed('unknown_voice', 'x'), fund_provider: fill('fund_provider', 'Vanguard'), ter: {key: 'ter', kind: 'emptied', origin: 'new'}}, CATALOGUE)).toBe(false);
    });
});
