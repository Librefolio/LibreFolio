// @vitest-environment jsdom
/**
 * A copied Broker brings its operating profile into the draft (P3 of project 67, D11, D12; Vitest + jsdom).
 *
 * Subject. Source 1.1.0 serves the account's operating profile on its Broker row (`SourceBroker.operating_profile`).
 *   - D11 (a): the first copy of a Broker whose profile has order modes takes those modes, and only those; a profile
 *     without modes, or no profile, gives today's default mode per observed currency. The conversion mode is the
 *     profile's.
 *   - D12 (a), the model of `copiedPrice`: the Broker also keeps the modes and the conversion mode **as copied**. A second
 *     copy updates that copy and never the modes the user has in the draft. The review marks the Broker «modified» when
 *     its modes or its conversion mode differ from the copy.
 *   - Fact 6: the request built from copied modes equals, field by field, the one built from the same values typed by
 *     hand. The copy translates nothing the request would see.
 *
 * Environment. jsdom for the compile target, not for the DOM (see `request.test.ts`): in the node environment
 * `draft.svelte.ts` compiles for the server, where a `$derived` is computed once.
 */
import {describe, expect, it, vi} from 'vitest';

// source.ts and the tool client import the API client. Nothing here talks to a server.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import type {OperatingProfileDocument} from '$lib/features/brokers/profile/brokerOperatingProfile';
import {applyBrokerCopy, domainBrokerKey, newCopyRecord} from './copies';
import {PlannerDraft, type DraftAsset, type DraftBroker, type DraftMode} from './draft.svelte';
import {buildRequest} from './request';
import {snapshotFacts} from './review';
import type {PlannerSource, SourceBroker} from './source';

const AS_OF = '2026-11-13';
const BROKER = 7;

/** EUR by whole units with a purchase fee of 0.19 % (min 1.5, max 18) and a sale fee; USD by amount with a fixed fee. */
const PROFILE: OperatingProfileDocument = {
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
};

function brokerRow(profile: OperatingProfileDocument | null, observed: string[] = ['EUR', 'USD']): SourceBroker {
    return {
        broker_id: `broker:${BROKER}`,
        source_broker_id: BROKER,
        name: 'Broker probe',
        icon_url: null,
        access_role: 'OWNER',
        ownership_share: '1',
        observed_currencies: observed,
        active: true,
        operating_profile_status: profile ? 'available' : 'not_available',
        operating_profile: profile,
        provenance_id: 'source:broker-domain',
    };
}

function source(row: SourceBroker): PlannerSource {
    const generatedAt = `${AS_OF}T09:30:00Z`;
    return {
        asOf: AS_OF,
        targetCurrency: 'EUR',
        generatedAt,
        provenance: [{provenance_id: 'source:broker-domain', domain: 'broker', source_ref: 'brokers', source_label: null, captured_at: generatedAt}],
        assets: [],
        brokers: [row],
        holdings: [],
        cash: [],
        prices: [],
        classifications: [],
        fxQuotes: [],
        currentDistribution: null,
        issues: [],
    };
}

function copyBroker(draft: PlannerDraft, row: SourceBroker): DraftBroker {
    const snapshot = source(row);
    applyBrokerCopy(draft, snapshot, newCopyRecord(draft, 'brokers', snapshot), [BROKER]);
    const broker = draft.broker(domainBrokerKey(BROKER));
    if (!broker) throw new Error('the Broker was not copied');
    return broker;
}

/** What a mode means, without its key. */
function values(modes: readonly DraftMode[] | null) {
    return modes?.map(({key: _key, ...rest}) => rest) ?? null;
}

function mode(broker: DraftBroker, currency: string): DraftMode {
    const found = broker.modes.filter((item) => item.currency === currency);
    expect(found).toHaveLength(1);
    return found[0];
}

const EUR_MODE = {currency: 'EUR', kind: 'whole_quantity', step: '1', fixedFee: '0', ratePercent: '0.19', floor: '1.5', cap: '18'};
const USD_MODE = {currency: 'USD', kind: 'monetary_amount', step: '0.01', fixedFee: '1', ratePercent: '0', floor: '0', cap: ''};

function brokerFact(draft: PlannerDraft) {
    const facts = snapshotFacts(draft).filter((fact) => fact.id === `broker|${domainBrokerKey(BROKER)}`);
    expect(facts).toHaveLength(1);
    return facts[0];
}

describe('a copied Broker and its operating profile', () => {
    it("a first copy takes the profile's modes and keeps them as the copy", () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        // CHF is observed but the profile has no rule for it: no silent zero-fee mode (D11 a).
        const broker = copyBroker(draft, brokerRow(PROFILE, ['CHF', 'EUR', 'USD']));

        expect(values(broker.modes)).toEqual([EUR_MODE, USD_MODE]);
        expect(values(broker.copiedModes)).toEqual([EUR_MODE, USD_MODE]);
        expect(broker.conversionMode).toBe('automatic');
        expect(broker.copiedConversionMode).toBe('automatic');
        expect(new Set(broker.modes.map((item) => item.key)).size).toBe(2);
    });

    it("a second copy updates the copy and leaves the user's modes", () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        copyBroker(draft, brokerRow(PROFILE));
        mode(draft.broker(domainBrokerKey(BROKER)) as DraftBroker, 'EUR').ratePercent = '0.25';

        // The same copy again changes nothing the request sees.
        const fingerprint = draft.fingerprint;
        copyBroker(draft, brokerRow(PROFILE));
        expect(draft.fingerprint.replace(/copy:\d+/g, 'copy')).toBe(fingerprint.replace(/copy:\d+/g, 'copy'));

        // A changed profile updates the copy only.
        const changed: OperatingProfileDocument = {...PROFILE, order_modes: [PROFILE.order_modes?.[1] as NonNullable<OperatingProfileDocument['order_modes']>[number]], conversion_mode: 'manual'};
        const broker = copyBroker(draft, brokerRow(changed));
        expect(values(broker.modes)).toEqual([{...EUR_MODE, ratePercent: '0.25'}, USD_MODE]);
        expect(broker.conversionMode).toBe('automatic');
        expect(values(broker.copiedModes)).toEqual([USD_MODE]);
        expect(broker.copiedConversionMode).toBe('manual');
    });

    it('a Broker without a profile is copied as today', () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        const broker = copyBroker(draft, brokerRow(null));

        expect(broker.modes.map((item) => item.currency)).toEqual(['EUR', 'USD']);
        expect(mode(broker, 'EUR')).toMatchObject({kind: 'whole_quantity', step: '1', fixedFee: '0', ratePercent: '0', floor: '0', cap: ''});
        // TL-6 of project 67: a Broker that said nothing converts by itself.
        expect(broker.conversionMode).toBe('automatic');
        expect(broker.copiedModes).toBeNull();
        expect(broker.copiedConversionMode).toBeNull();
        // A profile with no order mode gives the default modes too, and its conversion mode.
        const other = new PlannerDraft('EUR', 'proportional');
        const onlyConversion = copyBroker(other, brokerRow({profile_version: 1, order_modes: [], conversion_mode: 'manual'}));
        expect(onlyConversion.modes.map((item) => item.currency)).toEqual(['EUR', 'USD']);
        expect(onlyConversion.conversionMode).toBe('manual');
    });

    it('the request built from copied modes equals the one built by hand', () => {
        const scenario = (profile: OperatingProfileDocument | null): PlannerDraft => {
            const draft = new PlannerDraft('EUR', 'proportional');
            draft.data.asOf = AS_OF;
            const broker = copyBroker(draft, brokerRow(profile));
            if (!profile) {
                // The same values, typed by hand in the Broker editor.
                Object.assign(mode(broker, 'EUR'), {ratePercent: '0.19', floor: '1.5', cap: '18'});
                Object.assign(mode(broker, 'USD'), {kind: 'monetary_amount', step: '0.01', fixedFee: '1'});
                broker.conversionMode = 'automatic';
            }
            const asset: DraftAsset = {
                key: draft.nextId('manual-asset'),
                origin: 'manual',
                sourceAssetId: null,
                name: 'Manual ETF probe',
                ticker: '',
                assetClass: 'etf',
                iconUrl: null,
                active: true,
                price: {amount: '10', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: AS_OF},
                priceManual: false,
                copiedPrice: null,
                priceStamp: null,
                priceSource: null,
                exposures: [],
                copiedExposures: null,
                exposureStamp: null,
                enteredAt: `${AS_OF}T10:00:00.000Z`,
            };
            draft.addAsset(asset);
            draft.data.targets[asset.key] = '100';
            draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
            return draft;
        };
        const build = (draft: PlannerDraft) => {
            const outcome = buildRequest(draft, new Date(`${AS_OF}T12:00:00Z`));
            expect(outcome.ok ? [] : outcome.problems.map((problem) => problem.id)).toEqual([]);
            if (!outcome.ok) throw new Error('unreachable');
            return outcome.built.request;
        };

        // The manual account's entry time is part of the wire: both scenarios are built at the same instant.
        vi.useFakeTimers({toFake: ['Date']});
        vi.setSystemTime(new Date(`${AS_OF}T10:00:00Z`));
        const copied = build(scenario(PROFILE));
        const typed = build(scenario(null));
        vi.useRealTimers();

        expect(copied).toEqual(typed);
        // The fees did reach the wire: the comparison is not between two empty requests.
        expect(JSON.stringify(copied)).toContain('0.0019');
    });

    it('the review marks a Broker modified when its modes differ from the copy', () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        copyBroker(draft, brokerRow(PROFILE));
        expect(brokerFact(draft)).toMatchObject({origin: 'copied', modified: false});

        // The same value written another way is not a change.
        mode(draft.broker(domainBrokerKey(BROKER)) as DraftBroker, 'EUR').ratePercent = '0.190';
        expect(brokerFact(draft).modified).toBe(false);

        mode(draft.broker(domainBrokerKey(BROKER)) as DraftBroker, 'EUR').cap = '';
        expect(brokerFact(draft).modified).toBe(true);
        mode(draft.broker(domainBrokerKey(BROKER)) as DraftBroker, 'EUR').cap = '18';
        expect(brokerFact(draft).modified).toBe(false);

        (draft.broker(domainBrokerKey(BROKER)) as DraftBroker).conversionMode = 'manual';
        expect(brokerFact(draft).modified).toBe(true);

        // Without a copy there is nothing to differ from.
        const plain = new PlannerDraft('EUR', 'proportional');
        copyBroker(plain, brokerRow(null));
        mode(plain.broker(domainBrokerKey(BROKER)) as DraftBroker, 'EUR').ratePercent = '1';
        expect(brokerFact(plain).modified).toBe(false);
    });
});
