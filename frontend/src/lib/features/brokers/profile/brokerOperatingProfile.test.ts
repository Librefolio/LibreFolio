/**
 * brokerOperatingProfile (P2 of project 67): the operating profile panel's draft ↔ the stored document, pure logic.
 *
 * The panel edits a draft of text fields (a fee rate in percent, an empty maximum for «none»); the API stores the document of
 * contract §7 (a rate as a fraction, `variable_cap: {kind: 'none'}`). Every conversion is exact (`exactDecimal`): 0.19 %
 * is `"0.0019"`, never a float. The draft keeps every group, shown or not, so a panel that hides the sale fee or the tax
 * regime hands them back untouched (fact 8). The local checks are the backend's D4 refusals, said before sending.
 */
import {describe, expect, it} from 'vitest';
import {copyRules, DEFAULT_CONVERSION_MODE, draftsEqual, fromDraft, newRule, profileProblems, toDraft, type OperatingProfileDocument, type ProfileDraft} from './brokerOperatingProfile';

const DOCUMENT: OperatingProfileDocument = {
    profile_version: 1,
    order_modes: [
        {
            currency: 'EUR',
            capability: {kind: 'whole_quantity', capability_id: 'mode:EUR', quantity_unit: 'asset_unit', quantity_step: '1'},
            fees: [
                {fee_schedule_id: 'fee:EUR:buy', capability_id: 'mode:EUR', side: 'buy', rate: '0.0019', variable_floor: {amount: '1.5', currency: 'EUR'}, variable_cap: {kind: 'amount', amount: {amount: '18', currency: 'EUR'}}},
                {fee_schedule_id: 'fee:EUR:sell', capability_id: 'mode:EUR', side: 'sell', fixed_fee: {amount: '5', currency: 'EUR'}, variable_cap: {kind: 'none'}},
            ],
        },
        {
            currency: 'USD',
            capability: {kind: 'monetary_amount', capability_id: 'mode:USD', order_amount_step: {amount: '0.01', currency: 'USD'}},
            fees: [{fee_schedule_id: 'fee:USD:buy', capability_id: 'mode:USD', side: 'buy', fixed_fee: {amount: '1', currency: 'USD'}, variable_cap: {kind: 'none'}}],
        },
    ],
    conversion_mode: 'automatic',
    tax_regime: 'administered',
};

function rule(draft: ProfileDraft, currency: string) {
    const found = draft.rules.find((item) => item.currency === currency);
    if (!found) throw new Error(`no ${currency} rule`);
    return found;
}

describe('brokerOperatingProfile', () => {
    it('a saved profile becomes the section draft and back, unchanged', () => {
        const draft = toDraft(DOCUMENT);

        expect(rule(draft, 'EUR')).toMatchObject({orderKind: 'whole_quantity', step: '1', buy: {ratePercent: '0.19', minimum: '1.5', maximum: '18', fixed: ''}, sellSameAsBuy: false});
        expect(rule(draft, 'USD')).toMatchObject({orderKind: 'monetary_amount', step: '0.01', buy: {fixed: '1', maximum: ''}, sellSameAsBuy: false});
        expect(fromDraft(draft)).toEqual(DOCUMENT);
    });

    it('a rate in percent is the exact fraction, and an empty maximum is «none»', () => {
        const draft = toDraft(null);
        draft.rules.push({...newRule('EUR'), buy: {minimum: '', ratePercent: '0.19', maximum: '', fixed: ''}});

        const fee = fromDraft(draft)?.order_modes?.[0].fees?.[0];

        expect(fee).toMatchObject({side: 'buy', rate: '0.0019', variable_cap: {kind: 'none'}});
        expect(fee).not.toHaveProperty('fixed_fee');
        expect(fee).not.toHaveProperty('variable_floor');
    });

    it('«same as the purchase» writes the sale fee from the purchase fee', () => {
        const draft = toDraft(null);
        draft.rules.push({...newRule('EUR'), buy: {minimum: '1.5', ratePercent: '0.19', maximum: '18', fixed: ''}, sellSameAsBuy: true});

        const fees = fromDraft(draft)?.order_modes?.[0].fees ?? [];

        expect(fees.map((fee) => fee.side)).toEqual(['buy', 'sell']);
        expect({...fees[1], side: 'buy', fee_schedule_id: 'fee:EUR:buy'}).toEqual(fees[0]);
        // Read back, equal fees on both sides are «same as the purchase» again.
        expect(rule(toDraft(fromDraft(draft)), 'EUR').sellSameAsBuy).toBe(true);
    });

    it('an empty box is no profile', () => {
        expect(fromDraft(toDraft(null))).toBeNull();
        // The backend serves `conversion_mode` always: a profile left with the default alone is no profile (TL-6: «automatic»).
        expect(fromDraft(toDraft({profile_version: 1, order_modes: [], conversion_mode: 'automatic'}))).toBeNull();
        // A choice that differs from the default is a profile; an untouched regime writes no tax_regime (it reads «declarative»).
        const draft = toDraft(null);
        draft.conversionMode = 'manual';
        expect(fromDraft(draft)).toEqual({profile_version: 1, order_modes: [], conversion_mode: 'manual'});
        expect(fromDraft(draft)).not.toHaveProperty('tax_regime');
    });

    it('the conversion, as TL-6 saves it: the Broker converting is the default, «Converti tu» is a choice', () => {
        expect(DEFAULT_CONVERSION_MODE).toBe('automatic');
        const withMode = (conversionMode: ProfileDraft['conversionMode']): ProfileDraft => ({...toDraft(null), conversionMode});
        // Nothing chosen, or the default alone: nothing to save.
        expect(fromDraft(withMode(null))).toBeNull();
        expect(fromDraft(withMode('automatic'))).toBeNull();
        // «Converti tu» alone is saved, and read back as it was saved.
        const manual = fromDraft(withMode('manual'));
        expect(manual).toEqual({profile_version: 1, order_modes: [], conversion_mode: 'manual'});
        expect(toDraft(manual).conversionMode).toBe('manual');
        // Rules with no choice leave the key out (the backend reads the default).
        const rules = {...withMode(null), rules: [newRule('EUR')]};
        expect(fromDraft(rules)).not.toHaveProperty('conversion_mode');
        // A stored «Converti tu» alone, switched to the default, goes back to «no profile».
        const stored = toDraft({profile_version: 1, order_modes: [], conversion_mode: 'manual'});
        expect(draftsEqual(stored, {...stored, conversionMode: 'automatic'})).toBe(false);
        expect(fromDraft({...stored, conversionMode: 'automatic'})).toBeNull();
    });

    it.each([
        [
            'currencyMissing',
            (draft: ProfileDraft): void => {
                draft.rules[0].currency = '';
            },
        ],
        [
            'notANumber',
            (draft: ProfileDraft): void => {
                draft.rules[0].step = 'abc';
            },
        ],
        [
            'stepNotPositive',
            (draft: ProfileDraft): void => {
                draft.rules[0].step = '0';
            },
        ],
        [
            'stepNotWhole',
            (draft: ProfileDraft): void => {
                draft.rules[0].step = '1.5';
            },
        ],
        [
            'notANumber',
            (draft: ProfileDraft): void => {
                draft.rules[0].buy.ratePercent = 'x';
            },
        ],
        [
            'feeNegative',
            (draft: ProfileDraft): void => {
                draft.rules[0].buy.fixed = '-1';
            },
        ],
        [
            'feeNegative',
            (draft: ProfileDraft): void => {
                draft.rules[0].sell.maximum = '-2';
            },
        ],
    ] as const)('local problems name the field: %s', (key, edit) => {
        const draft = toDraft(DOCUMENT);
        expect(profileProblems(draft)).toEqual([]);

        edit(draft);

        const problems = profileProblems(draft);
        expect(problems.map((problem) => problem.key)).toEqual([key]);
        expect(problems[0].ruleKey).toBe(draft.rules[0].key);
    });

    it('a sale fee hidden behind «same as the purchase» is not checked', () => {
        const draft = toDraft(DOCUMENT);
        draft.rules[0].sell.fixed = '-1';
        draft.rules[0].sellSameAsBuy = true;
        expect(profileProblems(draft)).toEqual([]);
    });

    it('two drafts with the same values are equal', () => {
        const a = toDraft(DOCUMENT);
        const b = toDraft(DOCUMENT);
        b.rules[0].buy.ratePercent = '0.190';
        b.rules[0].buy.minimum = '1.50';
        expect(draftsEqual(a, b)).toBe(true);

        b.rules[0].buy.maximum = '19';
        expect(draftsEqual(a, b)).toBe(false);
    });

    it('copy rules from another currency adds one rule with those rules, never a second one for a currency', () => {
        const draft = toDraft(DOCUMENT);
        const eur = rule(draft, 'EUR');

        expect(copyRules(draft, eur.key, 'CHF')).toBe(true);
        const chf = rule(draft, 'CHF');
        expect({...chf, key: eur.key, currency: 'EUR'}).toEqual(eur);
        // The copied amounts are in the new currency once written.
        expect(fromDraft(draft)?.order_modes?.find((row) => row.currency === 'CHF')?.fees?.[0].variable_floor).toEqual({amount: '1.5', currency: 'CHF'});

        expect(copyRules(draft, eur.key, 'USD')).toBe(false);
        expect(draft.rules.filter((item) => item.currency === 'USD')).toHaveLength(1);
    });
});
