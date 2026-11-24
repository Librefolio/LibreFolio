/**
 * enrichersEditState (plan 68, E7a): the logic of the «Arricchitori dell'asset» window, without a DOM.
 *
 * Pinned:
 * - an untouched window hands back the same config: same keys, same order, the plugin's free parameters (Borsa
 *   Italiana's `mic`, `platform`) as they came;
 * - a binding whose enricher the instance does not serve (turned off) stays in its place, drawn off and kept at the
 *   save; one whose enricher is not configured is drawn off with «Configure» and kept too;
 * - a row says its last read and outcome, from `state`; one removed and put back finds its own;
 * - removing a row keeps its binding: put back, it comes back as it was, at the end;
 * - «Non in elenco» holds every other enricher of the catalogue, with its reason: removed by you, found (to add), new
 *   (no label), still searching, not found, conflict, error, not configured, not covering this type;
 * - a binding's light checks: an identifier, a type the enricher accepts; an empty parameter is not sent.
 */
import {describe, expect, it} from 'vitest';
import * as state from './enrichersEditState';
import type {EnricherBinding, EnricherInfo, EnricherRecognition} from './enrichersEditState';

function info(code: string, extra: Partial<EnricherInfo> = {}): EnricherInfo {
    return {
        code,
        name: code.toUpperCase(),
        icon: null,
        help_url: null,
        terms: 'open',
        accepted_identifier_types: ['ISIN'],
        params_schema: [],
        supports_search: false,
        voices: {ETF: ['ter', 'geography']},
        default_priority: {ETF: 10, BOND: null},
        configured: true,
        missing_settings: [],
        ...extra,
    } as EnricherInfo;
}

const CATALOGUE: EnricherInfo[] = [
    info('justetf'),
    info('yahoo', {accepted_identifier_types: ['TICKER', 'ISIN'], supports_search: true, default_priority: {ETF: 20, BOND: null}}),
    info('borsa_italiana', {default_priority: {ETF: 30, BOND: 10}, params_schema: [{key: 'mic', type: 'string'}]}),
    info('esma', {default_priority: {ETF: 40, BOND: 20}}),
    info('keyed', {configured: false, missing_settings: ['api_key']}),
    info('bonds_only', {default_priority: {ETF: null, BOND: 5}}),
    info('gleif', {accepted_identifier_types: ['LEI']}),
];

const CONFIG: Record<string, EnricherBinding> = {
    justetf: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'},
    switched_off: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'},
    borsa_italiana: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80', mic: 'ETFP', platform: 'eurotlx'},
};

const STATE = {
    justetf: {read_at: '2026-11-08T03:00:00+00:00', status: 'ok', error_code: null, retry_after: null, voices: 12},
    borsa_italiana: {read_at: '2026-11-08T03:00:00+00:00', status: 'not_found', error_code: null, retry_after: null, voices: 0},
    yahoo: {read_at: '2026-11-01T03:00:00+00:00', status: 'error', error_code: 'RATE_LIMITED', retry_after: null, voices: 0},
};

function context(extra: Partial<state.EnrichersContext> = {}): state.EnrichersContext {
    return {catalogue: CATALOGUE, assetType: 'ETF', state: STATE, recognitions: {}, searching: [], ...extra};
}

describe('an untouched window', () => {
    it('hands back the same config: keys, order and free parameters', () => {
        const draft = state.draftFrom(CONFIG);
        const config = state.resultConfig(draft);
        expect(Object.keys(config)).toEqual(['justetf', 'switched_off', 'borsa_italiana']);
        expect(config).toEqual(CONFIG);
        expect(config.borsa_italiana).toEqual({identifier_type: 'ISIN', identifier: 'IE00BK5BQT80', mic: 'ETFP', platform: 'eurotlx'});
    });

    it('is not changed', () => {
        expect(state.isChanged(state.draftFrom(CONFIG), CONFIG)).toBe(false);
    });
});

describe('the rows chosen', () => {
    it('keep their order and say whether the instance can use them', () => {
        const rows = state.chosenRows(state.draftFrom(CONFIG), context());
        expect(rows.map((row) => [row.code, row.position, row.availability])).toEqual([
            ['justetf', 1, 'ok'],
            ['switched_off', 2, 'off'],
            ['borsa_italiana', 3, 'ok'],
        ]);
        expect(rows[1].info).toBeNull();
    });

    it('a not configured enricher is drawn off, with what is missing', () => {
        const rows = state.chosenRows(state.draftFrom({keyed: {identifier_type: 'ISIN', identifier: 'X'}}), context());
        expect(rows[0]).toMatchObject({availability: 'not_configured', missing: ['api_key']});
    });

    it('say their last read and its outcome, from state', () => {
        const rows = state.chosenRows(state.draftFrom(CONFIG), context());
        expect(rows[0].lastRead).toEqual({day: '2026-11-08', status: 'ok', errorCode: null});
        expect(rows[1].lastRead).toBeNull();
        expect(rows[2].lastRead).toEqual({day: '2026-11-08', status: 'not_found', errorCode: null});
    });

    it('say which voices each one fills for the asset type', () => {
        const rows = state.chosenRows(state.draftFrom(CONFIG), context());
        expect(rows[0].fills).toEqual(['ter', 'geography']);
        expect(rows[1].fills).toEqual([]);
    });

    it('take the name a recognition found', () => {
        const recognitions: Record<string, EnricherRecognition> = {justetf: recognition('justetf', 'found', 'Vanguard FTSE All-World')};
        expect(state.chosenRows(state.draftFrom(CONFIG), context({recognitions}))[0].foundName).toBe('Vanguard FTSE All-World');
    });
});

describe('removing, putting back, reordering', () => {
    it('a removed row keeps its binding and comes back at the end as it was', () => {
        let draft = state.removeEnricher(state.draftFrom(CONFIG), 'borsa_italiana');
        expect(Object.keys(state.resultConfig(draft))).toEqual(['justetf', 'switched_off']);
        draft = state.reorder(draft, ['switched_off', 'justetf']);
        draft = state.addEnricher(draft, 'borsa_italiana');
        const config = state.resultConfig(draft);
        expect(Object.keys(config)).toEqual(['switched_off', 'justetf', 'borsa_italiana']);
        expect(config.borsa_italiana).toEqual(CONFIG.borsa_italiana);
        expect(state.isChanged(draft, CONFIG)).toBe(true);
    });

    it('one removed and put back finds its own last read', () => {
        const draft = state.addEnricher(state.removeEnricher(state.draftFrom(CONFIG), 'justetf'), 'justetf');
        const row = state.chosenRows(draft, context()).find((candidate) => candidate.code === 'justetf');
        expect(row?.lastRead?.status).toBe('ok');
    });

    it('a found enricher is added with the binding its recognition named', () => {
        const recognitions = {gleif: recognition('gleif', 'found', 'Vanguard', {identifier_type: 'LEI', identifier: 'EEXSPYGY7X8YAH8ZJF49'})};
        const draft = state.addEnricher(state.draftFrom(CONFIG), 'gleif', recognitions.gleif);
        expect(state.resultConfig(draft).gleif).toEqual({identifier_type: 'LEI', identifier: 'EEXSPYGY7X8YAH8ZJF49'});
    });

    it('a new enricher is added with the first identifier type it accepts, waiting for the identifier', () => {
        const draft = state.addEnricher(state.draftFrom({}), 'gleif', null, {accepted: ['LEI']});
        expect(state.resultConfig(draft).gleif).toEqual({identifier_type: 'LEI', identifier: ''});
    });

    it('a new enricher without a binding is added empty, and its row has an issue until it has one', () => {
        const draft = state.addEnricher(state.draftFrom({}), 'esma');
        const rows = state.chosenRows(draft, context());
        expect(rows[0].issue).toBe('no_identifier');
        expect(state.draftIssues(draft, context())).toEqual({esma: 'no_identifier'});
    });

    it('reordering ignores unknown codes and keeps the codes it was not told about at the end', () => {
        const draft = state.reorder(state.draftFrom(CONFIG), ['borsa_italiana', 'nope']);
        expect(Object.keys(state.resultConfig(draft))).toEqual(['borsa_italiana', 'justetf', 'switched_off']);
    });
});

describe('«Non in elenco»', () => {
    it('lists every other enricher of the catalogue with its reason', () => {
        const recognitions = {
            yahoo: recognition('yahoo', 'not_found'),
            gleif: recognition('gleif', 'found', 'Vanguard', {identifier_type: 'LEI', identifier: 'EEXSPYGY7X8YAH8ZJF49'}),
        };
        let draft = state.draftFrom(CONFIG);
        draft = state.removeEnricher(draft, 'justetf');
        const others = state.otherRows(draft, context({recognitions, searching: ['esma']}));
        expect(others.map((row) => [row.code, row.reason])).toEqual([
            ['justetf', 'removed'],
            ['gleif', 'found'],
            ['esma', 'searching'],
            ['yahoo', 'not_found'],
            ['keyed', 'not_configured'],
            ['bonds_only', 'not_covering'],
        ]);
        expect(others[0].binding).toEqual(CONFIG.justetf);
        expect(others.find((row) => row.code === 'esma')?.canAdd).toBe(false);
        expect(others[1].binding).toEqual({identifier_type: 'LEI', identifier: 'EEXSPYGY7X8YAH8ZJF49'});
    });

    it('an enricher with no recognition and nothing known is new, with no label', () => {
        const others = state.otherRows(state.draftFrom(CONFIG), context());
        expect(others.find((row) => row.code === 'esma')?.reason).toBe('new');
    });

    it('a conflict and an error say so', () => {
        const recognitions = {esma: recognition('esma', 'conflict'), gleif: recognition('gleif', 'error')};
        const reasons = Object.fromEntries(state.otherRows(state.draftFrom(CONFIG), context({recognitions})).map((row) => [row.code, row.reason]));
        expect(reasons.esma).toBe('conflict');
        expect(reasons.gleif).toBe('error');
    });

    it('for a bond the ETF-only enrichers do not cover the type', () => {
        const reasons = Object.fromEntries(state.otherRows(state.draftFrom({}), context({assetType: 'BOND'})).map((row) => [row.code, row.reason]));
        expect(reasons.justetf).toBe('not_covering');
        expect(reasons.bonds_only).toBe('new');
    });
});

describe('a binding', () => {
    it('needs an identifier and a type its enricher accepts', () => {
        const yahoo = CATALOGUE[1];
        expect(state.bindingIssue({identifier_type: 'TICKER', identifier: 'VWRA.L'}, yahoo)).toBeNull();
        expect(state.bindingIssue({identifier_type: 'TICKER', identifier: '  '}, yahoo)).toBe('no_identifier');
        expect(state.bindingIssue({identifier_type: 'LEI', identifier: 'X'}, yahoo)).toBe('type_not_accepted');
        expect(state.bindingIssue({identifier_type: 'ANY', identifier: 'X'}, null)).toBeNull();
    });

    it('a search result fills type and identifier and keeps the parameters', () => {
        const next = state.bindingFromResult(CONFIG.borsa_italiana, {identifier_type: 'ISIN', identifier: 'IE00B3RBWM25'});
        expect(next).toEqual({identifier_type: 'ISIN', identifier: 'IE00B3RBWM25', mic: 'ETFP', platform: 'eurotlx'});
    });

    it('an empty parameter is not sent, a value is trimmed', () => {
        const next = state.withParams(CONFIG.borsa_italiana, {mic: '', platform: ' tlx '});
        expect(next).toEqual({identifier_type: 'ISIN', identifier: 'IE00BK5BQT80', platform: 'tlx'});
    });
});

function recognition(code: string, status: string, name: string | null = null, binding: {identifier_type: string; identifier: string} = {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'}): EnricherRecognition {
    return {code, status, name, page_url: null, identifiers: {}, conflicts: {}, error: null, ...binding} as EnricherRecognition;
}

describe('what an enricher fills, in topics (E7b)', () => {
    /** A catalogue slice: each voice declares its topic (`GET /assets/profile/catalogue`). */
    const VOICES = [
        {key: 'geography', topic: 'countries'},
        {key: 'sector', topic: 'sectors'},
        {key: 'description', topic: 'description'},
        {key: 'ter', topic: 'costs'},
        {key: 'management_fee', topic: 'costs'},
        {key: 'fund_size', topic: 'size'},
        {key: 'replication', topic: 'structure'},
        {key: 'fund_domicile', topic: 'structure'},
    ] as unknown as Parameters<typeof state.topicsOf>[1];

    it('names the topics of its voices once, in the order the window shows them, at most four and how many more', () => {
        const fills = ['geography', 'sector', 'description', 'ter', 'management_fee', 'fund_size', 'replication', 'fund_domicile'];
        expect(state.topicsOf(fills, VOICES)).toEqual({topics: ['costs', 'structure', 'countries', 'sectors'], more: 2});
    });

    it('fewer than four: all of them, none more; a voice the catalogue does not list is skipped', () => {
        expect(state.topicsOf(['sector', 'not_a_voice', 'ter'], VOICES)).toEqual({topics: ['costs', 'sectors'], more: 0});
        expect(state.topicsOf([], VOICES)).toEqual({topics: [], more: 0});
    });
});

describe('the last read of the asset (E6c)', () => {
    const config = {justetf: {identifier_type: 'ISIN', identifier: 'IE00B4L5Y983'}, yahoo: {identifier_type: 'TICKER', identifier: 'SWDA.MI'}};

    it('is the latest read of the enrichers still bound, a not-found included', () => {
        const read = {justetf: {read_at: '2026-11-01T03:00:00+00:00', status: 'ok'}, yahoo: {read_at: '2026-11-08T03:00:00+00:00', status: 'not_found'}};
        expect(state.assetLastRead(config, read)).toBe('2026-11-08');
    });

    it('ignores the state of an enricher no longer bound', () => {
        const read = {justetf: {read_at: '2026-11-01T03:00:00+00:00', status: 'ok'}, borsa_italiana: {read_at: '2026-11-15T03:00:00+00:00', status: 'ok'}};
        expect(state.assetLastRead(config, read)).toBe('2026-11-01');
    });

    it('is null for an asset never read', () => {
        expect(state.assetLastRead(config, {})).toBeNull();
        expect(state.assetLastRead({}, {justetf: {read_at: '2026-11-01T03:00:00+00:00', status: 'ok'}})).toBeNull();
    });
});

describe('an enricher added with what the asset knows (ENR-1, R3)', () => {
    const ISIN = 'IE00BK5BQT80';

    it('from a recognition that found it: the binding it was found by', () => {
        const found = recognition('yahoo', 'found', 'Vanguard', {identifier_type: 'TICKER', identifier: 'VWCE.DE'});
        const draft = state.addEnricher(state.draftFrom({}), 'yahoo', found, {accepted: ['TICKER', 'ISIN'], identifiers: {ISIN}});
        expect(state.resultConfig(draft).yahoo).toEqual({identifier_type: 'TICKER', identifier: 'VWCE.DE'});
    });

    it('from a recognition that did not find it: the binding it asked with, and the row says so until the identifier changes', () => {
        const notFound = recognition('esma', 'not_found');
        let draft = state.addEnricher(state.draftFrom({}), 'esma', notFound, {accepted: ['ISIN'], identifiers: {ISIN}});
        expect(state.resultConfig(draft).esma).toEqual({identifier_type: 'ISIN', identifier: ISIN});
        const recognitions = {esma: notFound};
        expect(state.chosenRows(draft, context({recognitions}))[0].notFoundWith).toEqual({identifier_type: 'ISIN', identifier: ISIN});
        draft = state.setBinding(draft, 'esma', {identifier_type: 'ISIN', identifier: 'IE00B3RBWM25'});
        expect(state.chosenRows(draft, context({recognitions}))[0].notFoundWith).toBeNull();
    });

    it('a row with no recognition never says it was not found', () => {
        const draft = state.addEnricher(state.draftFrom({}), 'esma', null, {accepted: ['ISIN'], identifiers: {ISIN}});
        expect(state.chosenRows(draft, context())[0].notFoundWith).toBeNull();
    });

    it('with no recognition: the ISIN of the asset for an enricher that reads ISINs only', () => {
        const draft = state.addEnricher(state.draftFrom({}), 'esma', null, {accepted: ['ISIN'], identifiers: {ISIN: ` ${ISIN} `, TICKER: 'VWCE'}});
        expect(state.resultConfig(draft).esma).toEqual({identifier_type: 'ISIN', identifier: ISIN});
        expect(state.draftIssues(draft, context())).toEqual({});
    });

    it('takes the first type it accepts, in its plugin order, that the asset holds', () => {
        const identifiers = {ISIN, TICKER: 'VWCE'};
        const tickerFirst = state.addEnricher(state.draftFrom({}), 'yahoo', null, {accepted: ['TICKER', 'ISIN'], identifiers});
        expect(state.resultConfig(tickerFirst).yahoo).toEqual({identifier_type: 'TICKER', identifier: 'VWCE'});
        const isinFirst = state.addEnricher(state.draftFrom({}), 'yahoo', null, {accepted: ['ISIN', 'TICKER'], identifiers});
        expect(state.resultConfig(isinFirst).yahoo).toEqual({identifier_type: 'ISIN', identifier: ISIN});
    });

    it('skips an accepted type the asset holds blank', () => {
        const draft = state.addEnricher(state.draftFrom({}), 'yahoo', null, {accepted: ['TICKER', 'ISIN'], identifiers: {TICKER: '  ', ISIN}});
        expect(state.resultConfig(draft).yahoo).toEqual({identifier_type: 'ISIN', identifier: ISIN});
    });

    it('is empty, on the first type it accepts, when the asset holds none of them; with nothing known, fully empty', () => {
        expect(state.assetBinding({accepted: ['LEI', 'ISIN'], identifiers: {TICKER: 'VWCE'}})).toEqual({identifier_type: 'LEI', identifier: ''});
        expect(state.assetBinding({})).toEqual({identifier_type: '', identifier: ''});
    });

    it('a removed one keeps its parameters when put back, whatever the asset knows', () => {
        let draft = state.removeEnricher(state.draftFrom(CONFIG), 'borsa_italiana');
        draft = state.addEnricher(draft, 'borsa_italiana', null, {accepted: ['ISIN'], identifiers: {ISIN: 'IE00B3RBWM25'}});
        expect(state.resultConfig(draft).borsa_italiana).toEqual(CONFIG.borsa_italiana);
    });

    it('🗑 makes the reason «removed», and «+» puts it back with the binding it had, even over a recognition', () => {
        const recognitions = {justetf: recognition('justetf', 'found', 'Vanguard', {identifier_type: 'ISIN', identifier: 'IE00B3RBWM25'})};
        let draft = state.removeEnricher(state.draftFrom(CONFIG), 'justetf');
        const row = state.otherRows(draft, context({recognitions})).find((candidate) => candidate.code === 'justetf');
        expect(row?.reason).toBe('removed');
        expect(row?.binding).toEqual(CONFIG.justetf);
        draft = state.addEnricher(draft, 'justetf', row?.recognition, {accepted: ['ISIN'], identifiers: {}});
        expect(state.resultConfig(draft).justetf).toEqual(CONFIG.justetf);
    });
});

describe('«Riconosci» proposal taken into the draft (ENR-1, R2)', () => {
    const PROPOSAL = {
        gleif: {identifier_type: 'LEI', identifier: 'EEXSPYGY7X8YAH8ZJF49'},
        justetf: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'},
    };

    it('an empty draft takes the proposal, in the proposal order', () => {
        const draft = state.adoptProposal(state.draftFrom({}), PROPOSAL);
        expect(Object.keys(state.resultConfig(draft))).toEqual(['gleif', 'justetf']);
        expect(state.resultConfig(draft)).toEqual(PROPOSAL);
    });

    it('follows the proposal as it grows or shrinks, and keeps the bindings of what left (to put back)', () => {
        let draft = state.adoptProposal(state.draftFrom({}), {justetf: PROPOSAL.justetf});
        draft = state.adoptProposal(draft, PROPOSAL);
        expect(draft.order).toEqual(['gleif', 'justetf']);
        draft = state.adoptProposal(draft, {justetf: PROPOSAL.justetf});
        expect(draft.order).toEqual(['justetf']);
        expect(draft.bindings.gleif).toEqual(PROPOSAL.gleif);
    });

    it('an empty proposal empties the order', () => {
        expect(state.adoptProposal(state.draftFrom({}), {}).order).toEqual([]);
    });
});

describe('a ticker alone does not enter the list (ENR-1, R2)', () => {
    it('entersAlone: found by an ISIN or a LEI yes; by a ticker, not found, conflict, none: no', () => {
        expect(state.entersAlone(recognition('a', 'found'))).toBe(true);
        expect(state.entersAlone(recognition('a', 'found', 'X', {identifier_type: 'LEI', identifier: 'L'}))).toBe(true);
        expect(state.entersAlone(recognition('a', 'found', 'X', {identifier_type: 'TICKER', identifier: 'VWCE.DE'}))).toBe(false);
        expect(state.entersAlone(recognition('a', 'not_found'))).toBe(false);
        expect(state.entersAlone(recognition('a', 'conflict'))).toBe(false);
        expect(state.entersAlone(null)).toBe(false);
        expect(state.entersAlone(undefined)).toBe(false);
    });

    it('«Non in elenco» marks a ticker-only find, with its name and binding, and still lets it be added', () => {
        const recognitions = {
            yahoo: recognition('yahoo', 'found', 'Vanguard FTSE All-World UCITS', {identifier_type: 'TICKER', identifier: 'VWCE.DE'}),
            gleif: recognition('gleif', 'found', 'Vanguard', {identifier_type: 'LEI', identifier: 'EEXSPYGY7X8YAH8ZJF49'}),
        };
        const rows = Object.fromEntries(state.otherRows(state.draftFrom({}), context({recognitions})).map((row) => [row.code, row]));
        expect(rows.yahoo.reason).toBe('found');
        expect(rows.yahoo.tickerOnly).toBe(true);
        expect(rows.yahoo.canAdd).toBe(true);
        expect(rows.yahoo.recognition?.name).toBe('Vanguard FTSE All-World UCITS');
        expect(rows.yahoo.binding).toEqual({identifier_type: 'TICKER', identifier: 'VWCE.DE'});
        expect(rows.gleif.tickerOnly).toBe(false);
        expect(rows.esma.tickerOnly).toBe(false);
    });
});

describe('the line of «Riconosci» (ENR-1, R1)', () => {
    const COVERING = ['justetf', 'yahoo', 'esma'];
    const answers = (...codes: string[]) => Object.fromEntries(codes.map((code) => [code, recognition(code, code === 'yahoo' ? 'not_found' : 'found')]));

    it('nothing to say before it starts, when there is something to ask with', () => {
        expect(state.recognitionLine('idle', {}, COVERING, true)).toBeNull();
    });

    it('counts on the enrichers that can answer: one accepting no identifier the asset holds is never asked, so «N of M» still ends at M', () => {
        // Yahoo reads a ticker, the asset has an ISIN only: the cascade never answers for it
        const line = state.recognitionLine('running', answers('justetf', 'esma'), COVERING, true, ['justetf', 'esma']);
        expect(line).toMatchObject({state: 'running', answered: 2, asked: 2});
        const yahooFound = {...answers('justetf'), yahoo: recognition('yahoo', 'found')};
        expect(state.recognitionLine('done', yahooFound, COVERING, true, ['justetf'])?.found, 'a found one is named even outside the askable ones').toEqual(['justetf', 'yahoo']);
    });

    it('nothing to ask with: no_identifiers', () => {
        expect(state.recognitionLine('idle', {}, COVERING, false)).toMatchObject({state: 'no_identifiers', asked: 3, found: []});
    });

    it('running: how many of the covering ones answered, counting no stranger', () => {
        const line = state.recognitionLine('running', {...answers('justetf', 'yahoo'), gleif: recognition('gleif', 'found')}, COVERING, true);
        expect(line).toEqual({state: 'running', answered: 2, asked: 3, found: ['justetf']});
    });

    it('done: found with who, in the catalogue order; none when nobody was', () => {
        expect(state.recognitionLine('done', answers('esma', 'justetf', 'yahoo'), COVERING, true)).toEqual({state: 'found', answered: 3, asked: 3, found: ['justetf', 'esma']});
        expect(state.recognitionLine('done', {yahoo: recognition('yahoo', 'not_found')}, COVERING, true)).toMatchObject({state: 'none', found: []});
    });

    it('refused and error say so, whatever else is known', () => {
        expect(state.recognitionLine('refused', {}, COVERING, false)?.state).toBe('refused');
        expect(state.recognitionLine('error', {}, COVERING, true)?.state).toBe('error');
    });
});

describe('a conflict stays on the row (ENR-1)', () => {
    const conflicting = () => ({...recognition('esma', 'conflict'), conflicts: {LEI: 'OTHERLEI0000000000AA'}}) as EnricherRecognition;

    it('conflictWith copies what the source named while the binding is still the one asked with', () => {
        const recognitions = {esma: conflicting()};
        let draft = state.addEnricher(state.draftFrom({}), 'esma', recognitions.esma, {accepted: ['ISIN'], identifiers: {}});
        const row = state.chosenRows(draft, context({recognitions}))[0];
        expect(row.conflictWith).toEqual({LEI: 'OTHERLEI0000000000AA'});
        expect(row.conflictWith).not.toBe(recognitions.esma.conflicts);
        expect(row.notFoundWith).toBeNull();
        draft = state.setBinding(draft, 'esma', {identifier_type: 'ISIN', identifier: 'IE00B3RBWM25'});
        expect(state.chosenRows(draft, context({recognitions}))[0].conflictWith).toBeNull();
    });

    it('is null for a conflict that names nothing, and for an error', () => {
        const empty = {esma: {...conflicting(), conflicts: {}} as EnricherRecognition, gleif: recognition('gleif', 'error', null, {identifier_type: 'LEI', identifier: 'L'})};
        const draft = state.draftFrom({esma: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'}, gleif: {identifier_type: 'LEI', identifier: 'L'}});
        const rows = state.chosenRows(draft, context({recognitions: empty}));
        expect(rows.map((row) => row.conflictWith)).toEqual([null, null]);
    });
});
