/**
 * profileEditState (plan 68, E10c1): the logic of the «Modifica i dati» window, without a DOM.
 *
 * Pinned:
 * - the pending changes are keyed by voice (the shape the asset window will hold, E8/E9); each is a value (stored form),
 *   «Lascia vuoto», or «dalla fonte» (an enricher's value, with what the user saw), and says where it came from
 *   (`new`, `source`, `file`) for the row's badge;
 * - rows ↔ pending: a percentage is typed in percent («0,20») and stored as a fraction («0.002»), exactly; a number is
 *   stored as canonical decimal text; an amount as `{amount, currency}`; a date ISO; a choice, a country, a currency as
 *   their codes; a long text as it is; maps (sectors, countries) come from their panel as fractions and go as decimal
 *   text, never floats (the catalogue refuses them);
 * - the light checks of a row: no voice, the same voice twice, an empty value without «Lascia vuoto», a text that is not
 *   a number. Sign, choices and sums stay the backend's (`POST /assets/validate`);
 * - the `profile` of `PATCH /assets`: a value, `null` for «Lascia vuoto», `{from, seen}` for a value taken from a source;
 * - the comparison after «Chiedi»: the baseline of a voice is its pending change, else «Adesso»; a source value over an
 *   empty baseline fills it («dalla fonte»), an equal one (numerically: 0.0020 = 0.002; maps in any key order) shows
 *   nothing, a different one is a difference to choose; a voice asked that no source gives is «no data», unless a
 *   source did not answer (error or refused for too many requests): then «no answer»;
 * - applying the differences chosen makes them «dalla fonte».
 */
import {describe, expect, it} from 'vitest';
import * as state from './profileEditState';
import type {ProfileVoice} from './profileStore';

function voice(key: string, shape: string, extra: Partial<ProfileVoice> = {}): ProfileVoice {
    return {key, shape, sign: null, unit: null, groups: [], key_figure: false, charted: false, volatile: false, choices: [], map_keys: null, ...extra} as ProfileVoice;
}

const CATALOGUE: ProfileVoice[] = [
    voice('geography', 'map', {map_keys: 'country'}),
    voice('sector', 'map', {map_keys: 'sector'}),
    voice('description', 'text'),
    voice('ter', 'percentage', {sign: 'non_negative'}),
    voice('fund_size', 'amount', {sign: 'non_negative'}),
    voice('modified_duration', 'number', {sign: 'non_negative', unit: 'years'}),
    voice('maturity_date', 'date'),
    voice('fund_provider', 'text'),
    voice('distribution_policy', 'choice', {choices: ['accumulating', 'distributing']}),
    voice('fund_domicile', 'country'),
    voice('fund_currency', 'currency'),
    voice('coupon_schedule', 'table', {sign: 'non_negative'}),
];
const BY_KEY = new Map(CATALOGUE.map((v) => [v.key, v]));

describe('which voices go where', () => {
    it('puts the «dry» voices in the table, maps in panels, the table voice in its own panel', () => {
        expect(state.voicePlace(BY_KEY.get('ter')!)).toBe('row');
        expect(state.voicePlace(BY_KEY.get('fund_size')!)).toBe('row');
        expect(state.voicePlace(BY_KEY.get('maturity_date')!)).toBe('row');
        expect(state.voicePlace(BY_KEY.get('description')!)).toBe('row');
        expect(state.voicePlace(BY_KEY.get('geography')!)).toBe('panel');
        expect(state.voicePlace(BY_KEY.get('sector')!)).toBe('panel');
        expect(state.voicePlace(BY_KEY.get('coupon_schedule')!)).toBe('table');
    });
});

describe('a row and its pending change', () => {
    it('stores a percentage typed in percent as an exact fraction, and shows it back in percent', () => {
        const row = state.newRow('r1', 'ter', '0,20');
        const pending = state.pendingFromRow(row, BY_KEY.get('ter')!);
        expect(pending).toEqual({key: 'ter', kind: 'value', value: '0.002', origin: 'new'});
        expect(state.rowFromPending(pending!, BY_KEY.get('ter')!).input).toBe('0.2');
    });

    it('stores a number as canonical decimal text, never a float', () => {
        expect(state.pendingFromRow(state.newRow('r1', 'modified_duration', '6,210'), BY_KEY.get('modified_duration')!)?.value).toBe('6.21');
    });

    it('stores an amount as {amount, currency} with the amount as text', () => {
        const row = {...state.newRow('r1', 'fund_size', ''), amount: {amount: '55173000000', currency: 'EUR'}};
        expect(state.pendingFromRow(row, BY_KEY.get('fund_size')!)?.value).toEqual({amount: '55173000000', currency: 'EUR'});
    });

    it('stores a date, a choice, a country, a currency and a text as they are', () => {
        for (const [key, input] of [
            ['maturity_date', '2028-10-10'],
            ['distribution_policy', 'accumulating'],
            ['fund_domicile', 'IRL'],
            ['fund_currency', 'USD'],
            ['fund_provider', 'Vanguard'],
        ] as const) {
            expect(state.pendingFromRow(state.newRow('r1', key, input), BY_KEY.get(key)!)?.value, key).toBe(input);
        }
    });

    it('keeps «Lascia vuoto» as an emptied change, whatever the shape', () => {
        const row = {...state.newRow('r1', 'ter', ''), emptied: true};
        expect(state.pendingFromRow(row, BY_KEY.get('ter')!)).toEqual({key: 'ter', kind: 'emptied', origin: 'new'});
    });

    it('keeps a value taken from a source as «dalla fonte» while unchanged, and makes it the user’s once edited', () => {
        const fromSource: state.PendingVoice = {key: 'ter', kind: 'source', value: '0.0022', source: 'justetf', seen: '0.0022', origin: 'source'};
        const row = state.rowFromPending(fromSource, BY_KEY.get('ter')!);
        expect(state.pendingFromRow(row, BY_KEY.get('ter')!)).toEqual(fromSource);

        const edited = {...row, input: '0,19'};
        expect(state.pendingFromRow(edited, BY_KEY.get('ter')!)).toEqual({key: 'ter', kind: 'value', value: '0.0019', origin: 'new'});
    });

    it('keeps the origin of a value prefilled from a broker file', () => {
        const fromFile: state.PendingVoice = {key: 'fund_provider', kind: 'value', value: 'Anima SGR', origin: 'file'};
        const row = state.rowFromPending(fromFile, BY_KEY.get('fund_provider')!);
        expect(row.origin).toBe('file');
        expect(state.pendingFromRow(row, BY_KEY.get('fund_provider')!)).toEqual(fromFile);
    });
});

describe('the light checks of the rows', () => {
    it('names what is wrong with each row, and nothing for a valid one', () => {
        const rows = [
            state.newRow('ok', 'ter', '0,20'),
            state.newRow('no-voice', null, '5'),
            state.newRow('empty', 'fund_provider', '   '),
            {...state.newRow('emptied', 'maturity_date', ''), emptied: true},
            state.newRow('nan', 'modified_duration', 'abc'),
            state.newRow('dup-1', 'fund_domicile', 'IRL'),
            state.newRow('dup-2', 'fund_domicile', 'LUX'),
            {...state.newRow('amount-empty', 'fund_size', ''), amount: {amount: null, currency: 'EUR'}},
        ];
        expect(state.rowIssues(rows, BY_KEY)).toEqual({
            'no-voice': 'no_voice',
            empty: 'empty',
            nan: 'not_a_number',
            'dup-1': 'duplicate',
            'dup-2': 'duplicate',
            'amount-empty': 'empty',
        });
    });

    it('gives no pending change for a row with an issue', () => {
        expect(state.pendingFromRow(state.newRow('nan', 'modified_duration', 'abc'), BY_KEY.get('modified_duration')!)).toBeNull();
        expect(state.pendingFromRow(state.newRow('empty', 'fund_provider', ''), BY_KEY.get('fund_provider')!)).toBeNull();
    });
});

describe('the profile of PATCH /assets', () => {
    it('writes a value, null for «Lascia vuoto», {from, seen} for a value taken from a source', () => {
        const pending: state.PendingChanges = {
            ter: {key: 'ter', kind: 'value', value: '0.002', origin: 'new'},
            maturity_date: {key: 'maturity_date', kind: 'emptied', origin: 'new'},
            fund_provider: {key: 'fund_provider', kind: 'source', value: 'Vanguard', source: 'justetf', seen: 'Vanguard', origin: 'source'},
        };
        expect(state.profilePatch(pending)).toEqual({ter: '0.002', maturity_date: null, fund_provider: {from: 'justetf', seen: 'Vanguard'}});
    });

    it('turns a panel’s weights into decimal text, never floats', () => {
        const pending = state.pendingFromPanel('sector', {Technology: 0.6, Financials: 0.4}, 'new');
        expect(pending).toEqual({key: 'sector', kind: 'value', value: {Technology: '0.6', Financials: '0.4'}, origin: 'new'});
        expect(state.profilePatch({sector: pending})).toEqual({sector: {Technology: '0.6', Financials: '0.4'}});
    });

    it('reads a stored map back as numbers for the panel', () => {
        expect(state.panelWeights({Financials: '0.4000', Technology: '0.6000'})).toEqual({Financials: 0.4, Technology: 0.6});
        expect(state.panelWeights(null)).toBeNull();
    });

    it('never sends a map empty: an emptied panel empties on purpose a map «Adesso» holds, and is no change over none (E9b)', () => {
        // The backend refuses an empty map: the last row taken out of a panel must leave as null, or as nothing at all
        const now = {geography: {value: {USA: '0.75', ITA: '0.25'}, source: 'user'}};
        const other = {sector: state.pendingFromPanel('sector', {Technology: 1}, 'new')};
        expect(state.withPanel(other, 'geography', {}, now)).toEqual({...other, geography: {key: 'geography', kind: 'emptied', origin: 'new'}});
        expect(state.profilePatch(state.withPanel({}, 'geography', {}, now))).toEqual({geography: null});
        // Nothing stored: an empty panel is no change, and a change waiting there is taken back
        expect(state.withPanel({...other, geography: state.pendingFromPanel('geography', {USA: 1}, 'new')}, 'geography', {}, {})).toEqual(other);
        // Weights are a value, as before
        expect(state.withPanel({}, 'geography', {USA: 1}, now)).toEqual({geography: state.pendingFromPanel('geography', {USA: 1}, 'new')});
    });
});

describe('the comparison after «Chiedi»', () => {
    const ask = (voices: Record<string, {value: unknown; source: string}>, outcomes: Array<{code: string; status: string; error_code?: string | null}> = [{code: 'justetf', status: 'ok'}]) => ({
        voices: Object.fromEntries(Object.entries(voices).map(([k, v]) => [k, {...v, source_date: null, others: {}}])),
        outcomes: outcomes.map((o) => ({identifier_type: 'ISIN', identifier: 'IE0001', voices: [], error_code: null, retry_after: null, from_cache: false, ...o})),
    });

    it('fills an empty voice, shows nothing for an equal one, and asks for a different one', () => {
        const result = state.compareAsk(
            ask({
                fund_provider: {value: 'Vanguard', source: 'justetf'},
                ter: {value: '0.0022', source: 'justetf'},
                fund_currency: {value: 'USD', source: 'justetf'},
            }),
            {
                keys: ['fund_provider', 'ter', 'fund_currency'],
                pending: {ter: {key: 'ter', kind: 'value', value: '0.002', origin: 'new'}},
                current: {fund_currency: {value: 'USD', source: 'legacy'}},
            },
        );
        expect(result.fills).toEqual([{key: 'fund_provider', kind: 'source', value: 'Vanguard', source: 'justetf', seen: 'Vanguard', origin: 'source'}]);
        expect(result.equal).toEqual(['fund_currency']);
        expect(result.differences).toEqual([{key: 'ter', current: '0.002', proposed: '0.0022', source: 'justetf'}]);
        expect(result.missing).toEqual([]);
        expect(result.unanswered).toEqual([]);
    });

    it('compares numbers by value and maps in any key order', () => {
        const result = state.compareAsk(ask({ter: {value: '0.0020', source: 'justetf'}, geography: {value: {USA: '0.6000', JPN: '0.4000'}, source: 'justetf'}}), {
            keys: ['ter', 'geography'],
            pending: {},
            current: {ter: {value: '0.002', source: 'user'}, geography: {value: {JPN: '0.4', USA: '0.6'}, source: 'legacy'}},
        });
        expect(result.equal.sort()).toEqual(['geography', 'ter']);
        expect(result.differences).toEqual([]);
    });

    it('treats an emptied voice as empty: a source value fills it', () => {
        const result = state.compareAsk(ask({maturity_date: {value: '2028-10-10', source: 'borsa_italiana'}}), {
            keys: ['maturity_date'],
            pending: {maturity_date: {key: 'maturity_date', kind: 'emptied', origin: 'new'}},
            current: {},
        });
        expect(result.fills.map((f) => f.key)).toEqual(['maturity_date']);
    });

    it('says which voices no source gives, and which ones no source could answer for', () => {
        const noData = state.compareAsk(ask({}), {keys: ['index_name'], pending: {}, current: {}});
        expect(noData.missing).toEqual(['index_name']);
        expect(noData.unanswered).toEqual([]);

        const refused = state.compareAsk(ask({}, [{code: 'justetf', status: 'error', error_code: 'RATE_LIMITED'}]), {keys: ['index_name'], pending: {}, current: {}});
        expect(refused.missing).toEqual([]);
        expect(refused.unanswered).toEqual(['index_name']);
    });

    it('«Chiedi tutto» (no keys) looks at every voice a source gave, also those not in the table yet', () => {
        const result = state.compareAsk(ask({fund_domicile: {value: 'IRL', source: 'justetf'}, ter: {value: '0.0022', source: 'justetf'}}), {
            keys: null,
            pending: {},
            current: {ter: {value: '0.0022', source: 'justetf'}},
        });
        expect(result.fills.map((f) => f.key)).toEqual(['fund_domicile']);
        expect(result.equal).toEqual(['ter']);
        expect(result.missing).toEqual([]);
    });

    it('makes the differences chosen «dalla fonte», and leaves the others as they were', () => {
        const pending: state.PendingChanges = {ter: {key: 'ter', kind: 'value', value: '0.002', origin: 'new'}};
        const differences = [
            {key: 'ter', current: '0.002', proposed: '0.0022', source: 'justetf'},
            {key: 'fund_provider', current: 'Mine', proposed: 'Vanguard', source: 'justetf'},
        ];
        expect(state.applyDifferences(pending, differences, ['fund_provider'])).toEqual({
            ter: {key: 'ter', kind: 'value', value: '0.002', origin: 'new'},
            fund_provider: {key: 'fund_provider', kind: 'source', value: 'Vanguard', source: 'justetf', seen: 'Vanguard', origin: 'source'},
        });
    });
});
