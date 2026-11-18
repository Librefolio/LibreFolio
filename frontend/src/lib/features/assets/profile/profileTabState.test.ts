/**
 * profileTabState (plan 68, E3+E4): the logic of the «Profilo» tab, without a DOM.
 *
 * Pinned:
 * - the read follows the period chosen at the top of the asset page (I16): two days, or `start: 'min'` for «Tutti»;
 * - a voice's value is the one of its last step in the period (the backend clips the steps to the range); a step with a
 *   null value was emptied on purpose; no step: not available;
 * - the key figure cards, the detail groups and their order come from the catalogue (`groups`, `key_figure`, `charted`),
 *   never from a list here; a voice with no group has no cell;
 * - the «dati al» of the classification: the days a composition changed in the period, newest first, and the
 *   composition of the day chosen;
 * - the company's sector is the sector map of one sector at 100 %; a map of several sectors is a fund's, shown in the
 *   classification only;
 * - a charted key figure draws its steps; one that is not charted, or has no value in the period, draws nothing;
 * - values are written as the interface writes them: a percentage stored as a fraction in percent, a choice by its
 *   label, an amount with its currency (a public figure of the asset, never masked), a date without a time-zone shift.
 */
import {describe, expect, it} from 'vitest';
import * as tab from './profileTabState';
import type {ProfileStep, ProfileVoice, ProfileVoices} from './profileStore';

function voice(key: string, shape: string, extra: Partial<ProfileVoice> = {}): ProfileVoice {
    return {key, shape, sign: null, unit: null, groups: [], key_figure: false, charted: false, volatile: false, choices: [], map_keys: null, topic: 'structure', ...extra} as ProfileVoice;
}

function step(date: string, through: string, value: unknown, source = 'justetf', update_id = 1): ProfileStep {
    return {date, through, value, source, update_id} as ProfileStep;
}

const CATALOGUE: ProfileVoice[] = [
    voice('geography', 'map', {map_keys: 'country', groups: ['classification']}),
    voice('sector', 'map', {map_keys: 'sector', groups: ['classification', 'company']}),
    voice('description', 'text'),
    voice('withholding_tax', 'percentage', {groups: ['key_figures'], key_figure: true}),
    voice('ter', 'percentage', {groups: ['key_figures'], key_figure: true, charted: true}),
    voice('fund_size', 'amount', {groups: ['key_figures'], key_figure: true, charted: true, volatile: true}),
    voice('modified_duration', 'number', {unit: 'years', groups: ['key_figures'], key_figure: true, charted: true, volatile: true}),
    voice('maturity_date', 'date', {groups: ['key_figures'], key_figure: true}),
    voice('fund_provider', 'text', {groups: ['fund']}),
    voice('distribution_policy', 'choice', {groups: ['fund'], choices: ['accumulating', 'distributing']}),
    voice('fund_domicile', 'country', {groups: ['fund']}),
    voice('industry', 'text', {groups: ['company']}),
    voice('coupon_type', 'choice', {groups: ['bond'], choices: ['fixed', 'step_up']}),
    voice('coupon_schedule', 'table', {groups: ['bond']}),
    voice('legal_form', 'choice', {groups: ['identity'], choices: ['bond', 'ucits_fund']}),
    voice('issuer_lei', 'text'),
];

describe('the read follows the period of the page', () => {
    it('sends the two days of a period', () => {
        expect(tab.profileReadRange({start: '2025-11-17', end: '2026-11-17', all: false})).toEqual({start: '2025-11-17', end: '2026-11-17'});
    });

    it('sends start min for «Tutti», up to the last day of the page', () => {
        expect(tab.profileReadRange({start: '2019-01-04', end: '2026-11-17', all: true})).toEqual({start: 'min', end: '2026-11-17'});
    });
});

describe('the value of a voice', () => {
    const ter = CATALOGUE.find((v) => v.key === 'ter')!;

    it('is the last step of the period', () => {
        const cell = tab.profileCell(ter, [step('2025-11-17', '2026-03-01', '0.0022', 'justetf', 1), step('2026-03-02', '2026-11-17', '0.0019', 'justetf', 2)]);
        expect(cell.state).toBe('value');
        expect(cell.step?.value).toBe('0.0019');
        expect(cell.step?.update_id).toBe(2);
    });

    it('is emptied when the last step is null, and not available with no step', () => {
        expect(tab.profileCell(ter, [step('2025-11-17', '2026-11-17', null, 'user')]).state).toBe('emptied');
        expect(tab.profileCell(ter, undefined).state).toBe('unavailable');
        expect(tab.profileCell(ter, []).state).toBe('unavailable');
    });
});

describe('the key figure cards', () => {
    const voices: ProfileVoices = {
        ter: [step('2025-11-17', '2026-03-01', '0.0022'), step('2026-03-02', '2026-11-17', '0.0019')],
        modified_duration: [step('2025-11-17', '2026-11-17', null, 'user')],
        withholding_tax: [step('2025-11-17', '2026-11-17', '0.15', 'user')],
    };

    it('are the key figures of the catalogue, in its order, available or not', () => {
        expect(tab.keyFigureCards(CATALOGUE, voices).map((card) => [card.key, card.state])).toEqual([
            ['withholding_tax', 'value'],
            ['ter', 'value'],
            ['fund_size', 'unavailable'],
            ['modified_duration', 'emptied'],
            ['maturity_date', 'unavailable'],
        ]);
    });

    it('draw the steps of a charted voice, in percent for a percentage, closed on the last day', () => {
        const ter = tab.keyFigureCards(CATALOGUE, voices).find((card) => card.key === 'ter')!;
        expect(ter.chart).toEqual([
            {date: '2025-11-17', value: 0.22},
            {date: '2026-03-02', value: 0.19},
            {date: '2026-11-17', value: 0.19},
        ]);
    });

    it('draw nothing for a voice not charted, or with no value in the period', () => {
        const cards = tab.keyFigureCards(CATALOGUE, voices);
        expect(cards.find((card) => card.key === 'withholding_tax')!.chart).toBeNull();
        expect(cards.find((card) => card.key === 'modified_duration')!.chart).toBeNull();
        expect(cards.find((card) => card.key === 'fund_size')!.chart).toBeNull();
    });

    it('draw an amount by its number, and break the line where the value was emptied', () => {
        const points = tab.chartPoints(CATALOGUE.find((v) => v.key === 'fund_size')!, [step('2026-01-01', '2026-01-31', {amount: '1500000000', currency: 'EUR'}), step('2026-02-01', '2026-02-28', null, 'user'), step('2026-03-01', '2026-03-31', {amount: '1600000000', currency: 'EUR'})]);
        expect(points).toEqual([
            {date: '2026-01-01', value: 1500000000},
            {date: '2026-02-01', value: 0, missing: true},
            {date: '2026-03-01', value: 1600000000},
            {date: '2026-03-31', value: 1600000000},
        ]);
    });
});

describe('the detail groups', () => {
    it('are the fund, the company, the identity and the bond, each with its voices in catalogue order', () => {
        const groups = tab.detailGroups(CATALOGUE, {});
        expect(groups.map((group) => [group.group, group.cells.map((cell) => cell.key)])).toEqual([
            ['fund', ['fund_provider', 'distribution_policy', 'fund_domicile']],
            ['company', ['sector', 'industry']],
            ['identity', ['legal_form']],
            ['bond', ['coupon_type', 'coupon_schedule']],
        ]);
        expect(groups.flatMap((group) => group.cells).every((cell) => cell.state === 'unavailable')).toBe(true);
    });

    it('show the company sector only when the map is one sector', () => {
        const company = (voices: ProfileVoices) =>
            tab
                .detailGroups(CATALOGUE, voices)
                .find((group) => group.group === 'company')!
                .cells.find((cell) => cell.key === 'sector')!;
        expect(company({sector: [step('2026-01-01', '2026-11-17', {Technology: '1'})]}).state).toBe('value');
        expect(company({sector: [step('2026-01-01', '2026-11-17', {Technology: '0.6', Financials: '0.4'})]}).state).toBe('unavailable');
    });
});

describe('the composition and its «dati al»', () => {
    const voices: ProfileVoices = {
        geography: [step('2025-11-17', '2026-03-31', {USA: '0.6', JPN: '0.4'}), step('2026-04-01', '2026-11-17', {USA: '0.62', JPN: '0.38'})],
        sector: [step('2025-11-17', '2026-06-30', {Technology: '0.3', Financials: '0.7'}), step('2026-07-01', '2026-11-17', null, 'user')],
    };

    it('lists the days a composition changed, newest first, emptied ones included: the newest is the end of the period', () => {
        expect(tab.compositionDays(voices)).toEqual(['2026-07-01', '2026-04-01', '2025-11-17']);
        expect(tab.compositionDays({})).toEqual([]);
    });

    it('gives the composition of a day, as fractions', () => {
        expect(tab.compositionAt(voices, '2026-02-01')).toEqual({geography: {USA: 0.6, JPN: 0.4}, sector: {Technology: 0.3, Financials: 0.7}});
        expect(tab.compositionAt(voices, '2026-08-01')).toEqual({geography: {USA: 0.62, JPN: 0.38}, sector: null});
        expect(tab.compositionAt(voices, '2020-01-01')).toEqual({geography: null, sector: null});
    });
});

describe('the label of a composition (PROF, 17/11)', () => {
    function opened(date: string, through: string, value: unknown, extra: Partial<ProfileStep>): ProfileStep {
        return {...step(date, through, value), opened_on: date, source_date: null, ...extra} as ProfileStep;
    }

    it('says the source date when the source gives one', () => {
        const voices: ProfileVoices = {geography: [opened('2026-01-01', '2026-11-17', {USA: '1'}, {opened_on: '2025-10-04', source_date: '2025-09-30'})]};
        expect(tab.compositionLabel(voices, '2026-06-01')).toEqual({kind: 'source_date', day: '2025-09-30'});
    });

    it('says the true day of the read without a source date, never the day the period cut it to', () => {
        const voices: ProfileVoices = {sector: [opened('2026-01-01', '2026-11-17', {Technology: '1'}, {opened_on: '2025-10-04'})]};
        expect(tab.compositionLabel(voices, '2026-06-01')).toEqual({kind: 'opened_on', day: '2025-10-04'});
    });

    it('gives no date to a value from before the profile', () => {
        const voices: ProfileVoices = {geography: [opened('2026-01-01', '2026-11-17', {USA: '1'}, {opened_on: '2019-03-01', source: 'legacy'})]};
        expect(tab.compositionLabel(voices, '2026-06-01')).toEqual({kind: 'legacy'});
    });

    it('takes the newest of the two parts, and nothing for a day with no composition', () => {
        const voices: ProfileVoices = {
            geography: [opened('2026-01-01', '2026-11-17', {USA: '1'}, {opened_on: '2025-10-04', source_date: '2025-09-30'})],
            sector: [opened('2026-01-01', '2026-11-17', {Technology: '1'}, {opened_on: '2025-11-02', source_date: '2025-10-31'})],
        };
        expect(tab.compositionLabel(voices, '2026-06-01')).toEqual({kind: 'source_date', day: '2025-10-31'});
        expect(tab.compositionLabel(voices, '2020-01-01')).toBeNull();
    });
});

describe('a value as the tab writes it', () => {
    const labels: Record<string, string> = {
        'assets.profile.choices.distribution_policy.accumulating': 'Ad accumulo',
        'assets.profile.units.years': 'anni',
        'sectors.Technology': 'Tecnologia',
    };
    const context: tab.ProfileFormatContext = {
        translate: (key) => labels[key] ?? key,
        locale: 'it-IT',
        countryName: (iso3) => (iso3 === 'IRL' ? 'Irlanda' : iso3),
    };
    const byKey = (key: string) => CATALOGUE.find((v) => v.key === key)!;

    it('writes a percentage stored as a fraction in percent, in the interface locale', () => {
        expect(tab.formatProfileValue(byKey('ter'), '0.0014', context)).toBe('0,14%');
        expect(tab.formatProfileValue(byKey('withholding_tax'), '0.01125', context)).toBe('1,125%');
    });

    it('writes a choice by its label, a country by its name, a number with its unit', () => {
        expect(tab.formatProfileValue(byKey('distribution_policy'), 'accumulating', context)).toBe('Ad accumulo');
        expect(tab.formatProfileValue(byKey('fund_domicile'), 'IRL', context)).toBe('Irlanda');
        expect(tab.formatProfileValue(byKey('modified_duration'), '1.78', context)).toBe('1,78 anni');
    });

    it('writes a date in the interface locale, with no time-zone shift', () => {
        expect(tab.formatProfileValue(byKey('maturity_date'), '2028-10-10', context)).toBe('10/10/2028');
    });

    it('writes an amount with its currency, never masked: a public figure of the asset', () => {
        const text = tab.formatProfileValue(byKey('fund_size'), {amount: '55200000000', currency: 'EUR'}, context);
        expect(text).toContain('EUR');
        expect(text).toContain('55.200.000.000');
        expect(text).not.toContain('•');
    });

    it('writes the one sector of a company map by its label', () => {
        expect(tab.formatProfileValue(byKey('sector'), {Technology: '1'}, context)).toBe('Tecnologia');
    });

    it('writes a map of several keys as its three largest, by label, in percent', () => {
        const text = tab.formatProfileValue(byKey('sector'), {Energy: '0.1', Technology: '0.6', Utilities: '0.05', Financials: '0.25'}, context);
        expect(text).toBe('Tecnologia 60%, sectors.Financials 25%, sectors.Energy 10%');
        expect(tab.formatProfileValue(byKey('geography'), {IRL: '0.7', USA: '0.3'}, context)).toBe('Irlanda 70%, USA 30%');
    });

    it('writes nothing for a missing value', () => {
        expect(tab.formatProfileValue(byKey('ter'), null, context)).toBe('');
    });
});
