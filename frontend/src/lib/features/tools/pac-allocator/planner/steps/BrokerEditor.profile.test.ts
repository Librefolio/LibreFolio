// @vitest-environment jsdom
/**
 * BrokerEditor with the shared operating profile panel (P3 of project 67, facts 5 and 7; Vitest + jsdom).
 *
 * Subject. The planner's «Configure …» window no longer writes its own fields for the order modes, the purchase fee and
 * the currency conversion: it mounts the broker's panel (`BrokerOperatingProfileBox`) with the groups `orderMode`,
 * `buyFee` and `conversion`, under the planner's test-id prefix, so the ids the gallery reads keep their names. The
 * liquidity sources stay the planner's. «Restore» goes back to the modes copied from the account's profile (D12).
 *
 * Scenario. A Broker copied from the source with a profile (EUR by units, 0.19 % min 1.5 max 18; conversion by the
 * Broker), as `applyBrokerCopy` writes it. Driven through test ids; the currency catalogue is a fixture; nothing talks to
 * a server and nothing reads translated text.
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const api = vi.hoisted(() => ({getBroker: vi.fn(), patchBroker: vi.fn(), calls: [] as string[]}));

// Nothing talks to a server: the broker read and the broker write answer what each test queues, and record their order.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get: (_target, key) => {
                if (key === 'get_broker_api_v1_brokers__broker_id__get') return api.getBroker;
                if (key === 'update_broker_api_v1_brokers__broker_id__patch') return api.patchBroker;
                return vi.fn(async () => undefined);
            },
        },
    ),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));
vi.mock('$lib/stores/reference/currencyStore', async () => ({
    // The box writes an amount's currency beside its increment (TL-6 of project 67), through the shared formatter.
    currencyStoreVersion: (await import('svelte/store')).writable(0),
    getCurrencyInfo: (code: string) => ({code, name: `${code} fixture`, symbol: code, flag_emoji: '', country_codes: [], country_names: []}),
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getAllCurrencies: () => ['EUR', 'USD', 'CHF', 'GBP'].map((code) => ({code, name: `${code} fixture`, symbol: code, flag_emoji: '', country_codes: [], country_names: []})),
    suggestCurrency: vi.fn(async () => ({canonical: true, suggestion: null, candidates: []})),
}));

import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {OperatingProfileDocument} from '$lib/features/brokers/profile/brokerOperatingProfile';
import {applyBrokerCopy, domainBrokerKey, newCopyRecord} from '../copies';
import {PlannerDraft, brokerModesModified, type DraftBroker} from '../draft.svelte';
import type {PlannerSource} from '../source';
import BrokerEditor from './BrokerEditor.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(cleanup);

beforeEach(() => {
    api.calls.length = 0;
    api.getBroker.mockReset();
    api.patchBroker.mockReset();
});

const BROKER = 7;
const KEY = domainBrokerKey(BROKER);

const PROFILE: OperatingProfileDocument = {
    profile_version: 1,
    order_modes: [
        {
            currency: 'EUR',
            capability: {kind: 'whole_quantity', capability_id: 'mode:EUR', quantity_unit: 'asset_unit', quantity_step: '1'},
            fees: [{fee_schedule_id: 'fee:EUR:buy', capability_id: 'mode:EUR', side: 'buy', rate: '0.0019', variable_floor: {amount: '1.5', currency: 'EUR'}, variable_cap: {kind: 'amount', amount: {amount: '18', currency: 'EUR'}}}],
        },
    ],
    conversion_mode: 'automatic',
};

function copiedDraft(profile: OperatingProfileDocument | null = PROFILE): PlannerDraft {
    const draft = new PlannerDraft('EUR', 'proportional');
    const generatedAt = '2026-11-13T09:30:00Z';
    const source: PlannerSource = {
        asOf: '2026-11-13',
        targetCurrency: 'EUR',
        generatedAt,
        provenance: [{provenance_id: 'p', domain: 'broker', source_ref: 'brokers', source_label: null, captured_at: generatedAt}],
        assets: [],
        brokers: [
            {
                broker_id: KEY,
                source_broker_id: BROKER,
                name: 'Broker probe',
                icon_url: null,
                access_role: 'OWNER',
                ownership_share: '1',
                observed_currencies: ['EUR'],
                active: true,
                operating_profile_status: profile ? 'available' : 'not_available',
                operating_profile: profile,
                provenance_id: 'p',
            },
        ],
        holdings: [],
        cash: [],
        prices: [],
        classifications: [],
        fxQuotes: [],
        currentDistribution: null,
        issues: [],
    };
    applyBrokerCopy(draft, source, newCopyRecord(draft, 'brokers', source), [BROKER]);
    return draft;
}

function mount(draft: PlannerDraft, props: Record<string, unknown> = {}) {
    const onclose = vi.fn();
    render(BrokerEditor, {draft, brokerKey: KEY, onclose, ...props});
    flushSync();
    return onclose;
}

const broker = (draft: PlannerDraft) => draft.broker(KEY) as DraftBroker;
const block = (currency: string) => screen.getAllByTestId('pac-planner-mode').find((item) => item.getAttribute('data-currency') === currency) as HTMLElement;
const input = (element: HTMLElement) => element as HTMLInputElement;

describe('BrokerEditor and the shared operating profile panel', () => {
    it('the editor shows the shared box with the buy groups only, under the planner ids', () => {
        mount(copiedDraft());

        const box = screen.getByTestId('pac-planner-broker-editor-profile');
        expect(
            within(box)
                .getAllByTestId('pac-planner-group')
                .map((group) => group.getAttribute('data-group')),
        ).toEqual(['orderMode', 'buyFee', 'conversion']);
        expect(screen.queryByTestId('pac-planner-mode-sell-same')).toBeNull();
        expect(screen.queryByTestId('pac-planner-tax-regime')).toBeNull();
        // The planner's root id stays unique: the box takes its own.
        expect(screen.queryByTestId('pac-planner')).toBeNull();

        // The ids the gallery reads keep their names.
        const eur = block('EUR');
        expect(eur.getAttribute('data-kind')).toBe('whole_quantity');
        for (const id of ['pac-planner-mode-currency-trigger', 'pac-planner-mode-remove', 'pac-planner-mode-kind-button', 'pac-planner-mode-step', 'pac-planner-mode-fee-floor', 'pac-planner-mode-fee-rate', 'pac-planner-mode-fee-cap', 'pac-planner-mode-fee-fixed']) {
            expect(within(eur).getByTestId(id), id).toBeTruthy();
        }
        expect(input(within(eur).getByTestId('pac-planner-mode-fee-rate')).value).toBe('0.19');
        expect(screen.getByTestId('pac-planner-mode-add')).toBeTruthy();
        expect(
            within(screen.getByTestId('pac-planner-conversion-modes'))
                .getAllByTestId('pac-planner-conversion-mode')
                .map((card) => [card.getAttribute('data-mode'), card.getAttribute('data-selected')]),
        ).toEqual([
            ['manual', 'false'],
            ['automatic', 'true'],
        ]);
        expect(screen.getAllByTestId('pac-planner-conversion-mode-radio')).toHaveLength(2);

        // The liquidity sources are still the planner's.
        expect(screen.getByTestId('pac-planner-funding-empty')).toBeTruthy();
        expect(screen.getByTestId('pac-planner-broker-editor-modes').getAttribute('data-origin')).toBe('profile');
    });

    it('an edit reaches the draft on «Apply», with the mode keys kept', async () => {
        const draft = copiedDraft();
        const keys = broker(draft).modes.map((mode) => mode.key);
        const onclose = mount(draft);

        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.25'}});
        // By amount, the increment becomes the currency's smallest unit.
        await fireEvent.click(within(block('EUR')).getByTestId('pac-planner-mode-kind-button'));
        await fireEvent.click(await screen.findByTestId('pac-planner-mode-kind-option-monetary_amount'));
        flushSync();
        expect(input(within(block('EUR')).getByTestId('pac-planner-mode-step')).value).toBe('0.01');
        await fireEvent.click(screen.getAllByTestId('pac-planner-conversion-mode-radio')[0]);
        expect(broker(draft).modes[0].ratePercent).toBe('0.19');
        expect(screen.getByTestId('pac-planner-broker-editor-modes').getAttribute('data-origin')).toBe('modified');

        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-apply'));

        expect(onclose).toHaveBeenCalledOnce();
        expect(broker(draft).modes).toEqual([{key: keys[0], currency: 'EUR', kind: 'monetary_amount', step: '0.01', fixedFee: '0', ratePercent: '0.25', floor: '1.5', cap: '18'}]);
        expect(broker(draft).conversionMode).toBe('manual');
        // The copy is untouched: the review now says «modified».
        expect(broker(draft).copiedModes?.[0].ratePercent).toBe('0.19');
    });

    it('restore puts the copied modes back', async () => {
        const draft = copiedDraft();
        mount(draft);
        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.5'}});
        await fireEvent.click(screen.getAllByTestId('pac-planner-conversion-mode-radio')[0]);
        await fireEvent.click(screen.getByTestId('pac-planner-mode-add'));
        flushSync();
        expect(screen.getAllByTestId('pac-planner-mode')).toHaveLength(2);

        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-restore'));
        await tick();

        expect(screen.getAllByTestId('pac-planner-mode').map((item) => item.getAttribute('data-currency'))).toEqual(['EUR']);
        expect(input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate')).value).toBe('0.19');
        expect(screen.getAllByTestId('pac-planner-conversion-mode').map((card) => card.getAttribute('data-selected'))).toEqual(['false', 'true']);
        expect(screen.getByTestId('pac-planner-broker-editor-modes').getAttribute('data-origin')).toBe('profile');
        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-apply'));
        expect(broker(draft).modes.map(({key: _key, ...rest}) => rest)).toEqual(broker(draft).copiedModes?.map(({key: _key, ...rest}) => rest));
        expect(broker(draft).conversionMode).toBe('automatic');
    });

    it('restore without a profile gives the default modes, as before', async () => {
        const draft = copiedDraft(null);
        mount(draft);
        expect(screen.getByTestId('pac-planner-broker-editor-modes').getAttribute('data-origin')).toBe('none');
        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-fixed'), {target: {value: '2'}});
        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-restore'));
        await tick();
        expect(input(within(block('EUR')).getByTestId('pac-planner-mode-fee-fixed')).value).toBe('0');
    });

    it('a block with no currency or a refused field stops «Apply» and says why', async () => {
        const draft = copiedDraft();
        mount(draft);
        expect(screen.queryByTestId('pac-planner-broker-editor-profile-problems')).toBeNull();

        await fireEvent.click(screen.getByTestId('pac-planner-mode-add'));
        flushSync();

        expect(screen.getByTestId('pac-planner-broker-editor-profile-problems')).toBeTruthy();
        expect((screen.getByTestId('pac-planner-broker-editor-apply') as HTMLButtonElement).disabled).toBe(true);
        expect(broker(draft).modes).toHaveLength(1);
    });

    it('opened from the Route step, the missing currency comes first and is marked', () => {
        mount(copiedDraft(), {addCurrency: 'USD', addFor: 'ETF probe'});

        expect(screen.getAllByTestId('pac-planner-mode').map((item) => [item.getAttribute('data-currency'), item.getAttribute('data-required')])).toEqual([
            ['USD', 'true'],
            ['EUR', 'false'],
        ]);
        expect(screen.getByTestId('pac-planner-mode-added-for')).toBeTruthy();
        expect((screen.getByTestId('pac-planner-broker-editor-apply') as HTMLButtonElement).disabled).toBe(false);
    });

    it('the save button is shown for a copied broker only, and is off when nothing changed', async () => {
        const draft = copiedDraft();
        mount(draft);
        const save = () => screen.getByTestId('pac-planner-broker-editor-profile-save') as HTMLButtonElement;
        expect(save().disabled).toBe(true);
        // R1-C of project 67 (the developer, 20/11): the button carries the save icon.
        expect(save().querySelector('svg')).not.toBeNull();

        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.25'}});
        expect(save().disabled).toBe(false);
        cleanup();

        // A Broker copied without a profile: anything the scenario says is new to the account.
        mount(copiedDraft(null));
        expect(save().disabled).toBe(false);
        cleanup();

        // A manual Broker has no account to write to.
        const manual = new PlannerDraft('EUR', 'proportional');
        const key = manual.addManualBroker('Manual probe').key;
        render(BrokerEditor, {draft: manual, brokerKey: key, onclose: vi.fn()});
        flushSync();
        expect(screen.getByTestId('pac-planner-broker-editor')).toBeTruthy();
        expect(screen.queryByTestId('pac-planner-broker-editor-profile-save')).toBeNull();
    });

    it('the confirmation modal shows before any write, cancel writes nothing, confirm writes once', async () => {
        const stored: OperatingProfileDocument = {...PROFILE, tax_regime: 'administered'};
        api.getBroker.mockImplementation(async () => {
            api.calls.push('read');
            return {id: BROKER, operating_profile: stored};
        });
        api.patchBroker.mockImplementation(async () => {
            api.calls.push('write');
            return {results: [{id: BROKER, success: true}], success_count: 1};
        });
        const draft = copiedDraft();
        mount(draft);
        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.25'}});
        await fireEvent.click(screen.getByTestId('pac-planner-mode-add'));
        flushSync();
        // The new block is filled with a currency the profile does not have.
        const added = screen.getAllByTestId('pac-planner-mode').find((item) => item.getAttribute('data-currency') === '') as HTMLElement;
        await fireEvent.click(within(added).getByTestId('pac-planner-mode-currency-trigger'));
        await fireEvent.click(await screen.findByTestId('search-select-option-USD'));
        flushSync();

        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-profile-save'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase')).toBe('confirm'));

        expect(api.calls).toEqual(['read']);
        expect(api.getBroker).toHaveBeenCalledWith({params: {broker_id: BROKER}});
        // R1-C of project 67: the project's confirmation modal asks, not a banner in the window; the changes are in it, open.
        expect(screen.getByTestId('pac-planner-profile-save-modal')).toBeTruthy();
        expect(screen.getByTestId('pac-planner-profile-save').hidden).toBe(true);
        expect(screen.getAllByTestId('pac-planner-profile-save-change').map((item) => [item.getAttribute('data-currency'), item.getAttribute('data-change')])).toEqual([
            ['EUR', 'updated'],
            ['USD', 'created'],
        ]);

        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        expect(screen.queryByTestId('pac-planner-profile-save')).toBeNull();
        expect(screen.queryByTestId('pac-planner-profile-save-modal')).toBeNull();
        // The confirmation gives the focus back to the button that opened it, in the Broker window (keyboard users).
        await vi.waitFor(() => expect(document.activeElement).toBe(screen.getByTestId('pac-planner-broker-editor-profile-save')));
        expect(api.patchBroker).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-profile-save'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase')).toBe('confirm'));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase')).toBe('saved'));

        expect(api.calls).toEqual(['read', 'read', 'write']);
        expect(api.patchBroker).toHaveBeenCalledOnce();
        const [body, options] = api.patchBroker.mock.calls[0];
        expect(Object.keys(body)).toEqual(['operating_profile']);
        expect(options).toEqual({params: {broker_id: BROKER}});
        // The merged document: EUR updated, USD new, the stored regime kept.
        expect(body.operating_profile.tax_regime).toBe('administered');
        expect(body.operating_profile.order_modes.map((row: {currency: string}) => row.currency)).toEqual(['EUR', 'USD']);
        expect(body.operating_profile.order_modes[0].fees[0].rate).toBe('0.0025');
    });

    it('after a saved profile the copy equals the scenario', async () => {
        api.getBroker.mockResolvedValue({id: BROKER, operating_profile: PROFILE});
        api.patchBroker.mockResolvedValue({results: [{id: BROKER, success: true}], success_count: 1});
        const draft = copiedDraft();
        mount(draft);
        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.25'}});
        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-profile-save'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase')).toBe('confirm'));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase')).toBe('saved'));

        // The draft's Broker knows the new copy even before «Apply»; after it, nothing differs.
        expect(broker(draft).copiedModes?.[0].ratePercent).toBe('0.25');
        expect(screen.getByTestId('pac-planner-broker-editor-modes').getAttribute('data-origin')).toBe('profile');
        expect((screen.getByTestId('pac-planner-broker-editor-profile-save') as HTMLButtonElement).disabled).toBe(true);
        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-apply'));
        expect(brokerModesModified(broker(draft))).toBe(false);
    });

    it('a refused save says so and changes nothing', async () => {
        api.getBroker.mockResolvedValue({id: BROKER, operating_profile: PROFILE});
        api.patchBroker.mockResolvedValue({results: [{id: BROKER, success: false, error: 'refused probe'}], success_count: 0});
        const draft = copiedDraft();
        const copyBefore = JSON.parse(JSON.stringify(broker(draft)));
        mount(draft);
        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.25'}});
        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-profile-save'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase')).toBe('confirm'));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase')).toBe('refused'));

        expect(screen.getByTestId('pac-planner-profile-save-refusal').textContent).toBe('refused probe');
        expect(JSON.parse(JSON.stringify(broker(draft)))).toEqual(copyBefore);
        expect(screen.getByTestId('pac-planner-broker-editor-modes').getAttribute('data-origin')).toBe('modified');
    });

    it('confirm closes the modal; a line says the save runs, then that it is done', async () => {
        let answer: (value: unknown) => void = () => undefined;
        api.getBroker.mockResolvedValue({id: BROKER, operating_profile: PROFILE});
        api.patchBroker.mockImplementation(() => new Promise((resolve) => (answer = resolve)));
        mount(copiedDraft());
        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.25'}});
        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-profile-save'));
        const phase = () => screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase');
        await vi.waitFor(() => expect(phase()).toBe('confirm'));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));

        await vi.waitFor(() => expect(phase()).toBe('writing'));
        expect(screen.queryByTestId('pac-planner-profile-save-modal')).toBeNull();
        expect(screen.getByTestId('pac-planner-profile-save').hidden).toBe(false);
        answer({results: [{id: BROKER, success: true}], success_count: 1});
        await vi.waitFor(() => expect(phase()).toBe('saved'));
    });

    it('nothing to save is a line in the window, never a modal', async () => {
        // The stored profile already holds the rate typed below: the plan has nothing to write.
        const [mode] = PROFILE.order_modes ?? [];
        const stored: OperatingProfileDocument = {...PROFILE, order_modes: [{...mode, fees: [{...mode.fees![0], rate: '0.0025'}]}]};
        api.getBroker.mockResolvedValue({id: BROKER, operating_profile: stored});
        mount(copiedDraft());
        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.25'}});
        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-profile-save'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save-nothing')).toBeTruthy());
        expect(screen.queryByTestId('pac-planner-profile-save-modal')).toBeNull();
        expect(screen.getByTestId('pac-planner-profile-save').hidden).toBe(false);
        expect(api.patchBroker).not.toHaveBeenCalled();
    });

    it('a broker that cannot be read is not written', async () => {
        api.getBroker.mockRejectedValue(new Error('read probe'));
        mount(copiedDraft());
        await fireEvent.input(within(block('EUR')).getByTestId('pac-planner-mode-fee-rate'), {target: {value: '0.25'}});
        await fireEvent.click(screen.getByTestId('pac-planner-broker-editor-profile-save'));
        await vi.waitFor(() => expect(screen.getByTestId('pac-planner-profile-save').getAttribute('data-phase')).toBe('readFailed'));
        expect(api.patchBroker).not.toHaveBeenCalled();
    });
});
