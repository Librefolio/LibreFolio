/**
 * planProfileSave (P3 of project 67, D18, N4): what «Save to the broker profile» writes, and the list the confirm banner
 * shows, from the profile read again and the scenario's modes. Pure.
 *
 * D18: only the scenario's currencies and the conversion mode are merged in; the profile's other currencies, its sale
 * fees and its tax regime stay as stored. N4: the banner lists, per scenario currency, whether it is created or updated.
 * Fact 9: a currency the user did not fill is never invented.
 */
import {describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({zodiosApi: {}}));

import type {OperatingProfileDocument} from '$lib/features/brokers/profile/brokerOperatingProfile';
import {planProfileSave} from './brokerProfileSave';
import type {DraftMode} from './draft.svelte';

/** EUR with a purchase fee and a different sale fee; USD with «same as the purchase»; a tax regime. */
const STORED: OperatingProfileDocument = {
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
            fees: [
                {fee_schedule_id: 'fee:USD:buy', capability_id: 'mode:USD', side: 'buy', fixed_fee: {amount: '1', currency: 'USD'}, variable_cap: {kind: 'none'}},
                {fee_schedule_id: 'fee:USD:sell', capability_id: 'mode:USD', side: 'sell', fixed_fee: {amount: '1', currency: 'USD'}, variable_cap: {kind: 'none'}},
            ],
        },
    ],
    conversion_mode: 'manual',
    tax_regime: 'administered',
};

const EUR: DraftMode = {key: 'mode:1', currency: 'EUR', kind: 'whole_quantity', step: '1', fixedFee: '0', ratePercent: '0.19', floor: '1.5', cap: '18'};
const USD: DraftMode = {key: 'mode:2', currency: 'USD', kind: 'monetary_amount', step: '0.01', fixedFee: '1', ratePercent: '0', floor: '0', cap: ''};

const row = (document: OperatingProfileDocument | null, currency: string) => document?.order_modes?.find((item) => item.currency === currency);
const fee = (document: OperatingProfileDocument | null, currency: string, side: 'buy' | 'sell') => row(document, currency)?.fees?.find((item) => item.side === side);

describe('planProfileSave', () => {
    it('save to the broker profile merges the scenario currencies into the stored document', () => {
        const plan = planProfileSave(STORED, [{...EUR, ratePercent: '0.25'}], 'manual');

        expect(plan.changes).toEqual([{kind: 'currency', currency: 'EUR', change: 'updated'}]);
        expect(fee(plan.document, 'EUR', 'buy')).toMatchObject({rate: '0.0025', variable_floor: {amount: '1.5', currency: 'EUR'}});
        // The stored sale fee, different from the purchase fee, survives; USD and the regime are as stored.
        expect(fee(plan.document, 'EUR', 'sell')).toEqual(fee(STORED, 'EUR', 'sell'));
        expect(row(plan.document, 'USD')).toEqual(row(STORED, 'USD'));
        expect(plan.document?.tax_regime).toBe('administered');
        expect(plan.document?.conversion_mode).toBe('manual');
    });

    it('a sale fee «same as the purchase» follows the new purchase fee', () => {
        const plan = planProfileSave(STORED, [{...USD, fixedFee: '2'}], 'manual');

        expect(plan.changes).toEqual([{kind: 'currency', currency: 'USD', change: 'updated'}]);
        expect(fee(plan.document, 'USD', 'buy')?.fixed_fee).toEqual({amount: '2', currency: 'USD'});
        expect(fee(plan.document, 'USD', 'sell')?.fixed_fee).toEqual({amount: '2', currency: 'USD'});
    });

    it('save lists what is created and what is updated, per currency', () => {
        const onlyEur: OperatingProfileDocument = {...STORED, order_modes: [row(STORED, 'EUR') as NonNullable<ReturnType<typeof row>>]};

        const plan = planProfileSave(onlyEur, [{...EUR, cap: ''}, USD], 'automatic');

        expect(plan.changes).toEqual([
            {kind: 'currency', currency: 'EUR', change: 'updated'},
            {kind: 'currency', currency: 'USD', change: 'created'},
            {kind: 'conversion', mode: 'automatic'},
        ]);
        expect(fee(plan.document, 'EUR', 'buy')?.variable_cap).toEqual({kind: 'none'});
        expect(row(plan.document, 'USD')?.capability).toEqual({kind: 'monetary_amount', capability_id: 'mode:USD', order_amount_step: {amount: '0.01', currency: 'USD'}});
        // A new currency starts with the sale fee «same as the purchase» (the panel's default).
        expect(fee(plan.document, 'USD', 'sell')?.fixed_fee).toEqual({amount: '1', currency: 'USD'});
    });

    it('a profile currency the scenario does not have is neither listed nor changed', () => {
        const plan = planProfileSave(STORED, [EUR], 'manual');

        expect(plan.changes).toEqual([]);
        expect(plan.document).toEqual(STORED);
    });

    it('save to the broker profile does not invent a mode for a currency the user did not fill', () => {
        // A block left without a currency, and no profile at all: only EUR is written.
        // The planner's Broker at the default conversion (TL-6: «automatic»), so the conversion is not a change either.
        const plan = planProfileSave(null, [EUR, {...USD, key: 'mode:3', currency: ''}], 'automatic');

        expect(plan.changes).toEqual([{kind: 'currency', currency: 'EUR', change: 'created'}]);
        expect(plan.document?.order_modes?.map((item) => item.currency)).toEqual(['EUR']);
        expect(plan.document).not.toHaveProperty('tax_regime');
    });

    it('the profile as the backend serves it (defaults written out) and the same scenario change nothing', () => {
        // GET /brokers/{id} writes every fee field, its default included (seen in G4): `rate: "0"`, `null` amounts.
        const served = {
            profile_version: 1,
            order_modes: [
                {
                    currency: 'EUR',
                    capability: {kind: 'whole_quantity', capability_id: 'mode:EUR', quantity_unit: 'asset_unit', quantity_step: '1'},
                    fees: [
                        {fee_schedule_id: 'fee:EUR:buy', capability_id: 'mode:EUR', side: 'buy', fixed_fee: null, rate: '0.0019', variable_floor: {amount: '1.5', currency: 'EUR'}, variable_cap: {kind: 'amount', amount: {amount: '18', currency: 'EUR'}}},
                        {fee_schedule_id: 'fee:EUR:sell', capability_id: 'mode:EUR', side: 'sell', fixed_fee: {amount: '5', currency: 'EUR'}, rate: '0', variable_floor: null, variable_cap: {kind: 'none'}},
                    ],
                },
            ],
            conversion_mode: 'manual',
        } as OperatingProfileDocument;

        const plan = planProfileSave(served, [EUR], 'manual');

        expect(plan.changes).toEqual([]);
        expect(fee(plan.document, 'EUR', 'sell')?.fixed_fee).toEqual({amount: '5', currency: 'EUR'});
    });
});
