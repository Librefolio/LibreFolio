/**
 * brokerProfileAdapter (P3 of project 67): the planner's order modes ↔ the shared panel's draft, both ways, pure.
 *
 * The planner's «Configure …» window edits its modes with the broker's operating profile panel. A mode goes in as a rule
 * (its purchase fee only) and comes back as the same mode, key included: the request's capability ids and the issues'
 * routing read the key. A rule added in the panel gets a new key. A stored profile becomes modes with the planner's zero
 * where the profile writes nothing.
 */
import {describe, expect, it} from 'vitest';
import {newRule, type OperatingProfileDocument} from '$lib/features/brokers/profile/brokerOperatingProfile';
import {modeKeys, modesFromProfile, modesOf, profileDraftOf} from './brokerProfileAdapter';
import type {DraftMode} from './draft.svelte';

const MODES: DraftMode[] = [
    {key: 'mode:1', currency: 'EUR', kind: 'whole_quantity', step: '1', fixedFee: '0', ratePercent: '0.19', floor: '1.5', cap: '18'},
    {key: 'mode:2', currency: 'USD', kind: 'monetary_amount', step: '0.01', fixedFee: '1', ratePercent: '0', floor: '0', cap: ''},
];

function counter(prefix: string) {
    let next = 0;
    return () => `${prefix}:${++next}`;
}

describe('brokerProfileAdapter', () => {
    it('the draft modes and the box draft convert both ways without loss', () => {
        const draft = profileDraftOf(MODES, 'automatic');

        expect(draft.rules.map((rule) => rule.key)).toEqual(['mode:1', 'mode:2']);
        expect(draft.rules[0]).toMatchObject({currency: 'EUR', orderKind: 'whole_quantity', step: '1', buy: {minimum: '1.5', ratePercent: '0.19', maximum: '18', fixed: '0'}, sellSameAsBuy: true});
        expect(draft.taxRegime).toBeNull();

        const back = modesOf(
            draft,
            modeKeys(
                MODES.map((mode) => mode.key),
                counter('new'),
            ),
        );
        expect(back).toEqual({modes: MODES, conversionMode: 'automatic'});
    });

    it('a rule added in the box takes a new key, with the planner zero for an empty fee field', () => {
        const draft = profileDraftOf(MODES, 'manual');
        draft.rules.push({...newRule('CHF')});
        draft.conversionMode = null;

        const keyFor = modeKeys(
            MODES.map((mode) => mode.key),
            counter('mode-new'),
        );
        const back = modesOf(draft, keyFor);

        expect(back.modes.slice(0, 2)).toEqual(MODES);
        expect(back.modes[2]).toEqual({key: 'mode-new:1', currency: 'CHF', kind: 'whole_quantity', step: '1', fixedFee: '0', ratePercent: '0', floor: '0', cap: ''});
        // No conversion chosen reads the default (TL-6 of project 67: the Broker converts by itself).
        expect(back.conversionMode).toBe('automatic');
        // A later edit of the same draft keeps the new mode's key.
        draft.rules[2].step = '2';
        expect(modesOf(draft, keyFor).modes[2]).toMatchObject({key: 'mode-new:1', step: '2'});
    });

    it('a stored profile gives one mode per rule, its purchase fee only; none without rules', () => {
        const profile: OperatingProfileDocument = {
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
            ],
        };

        expect(modesFromProfile(profile, counter('mode'))).toEqual([{key: 'mode:1', currency: 'EUR', kind: 'whole_quantity', step: '1', fixedFee: '0', ratePercent: '0.19', floor: '1.5', cap: '18'}]);
        expect(modesFromProfile({profile_version: 1, order_modes: [], conversion_mode: 'automatic'}, counter('mode'))).toBeNull();
        expect(modesFromProfile(null, counter('mode'))).toBeNull();
    });
});
