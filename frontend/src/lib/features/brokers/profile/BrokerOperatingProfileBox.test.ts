// @vitest-environment jsdom
/**
 * BrokerOperatingProfileBox (P2 of project 67, M10, M21, M6, D17): the one operating profile panel, for «Edit broker»
 * and, from P3, the planner's «Configure …» window.
 *
 * It knows neither the broker nor the planner: it gets a draft and reports every edit with a callback (a fresh copy of the
 * whole draft). `groups` chooses what it shows (all of them by default), and what it does not show it hands back
 * untouched. Driven through test ids; the catalogue of currencies is a fixture.
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/stores/reference/currencyStore', async () => ({
    // The box writes an amount's currency beside its increment (TL-6 of project 67), through the shared formatter.
    currencyStoreVersion: (await import('svelte/store')).writable(0),
    getCurrencyInfo: (code: string) => ({code, name: `${code} fixture`, symbol: code, flag_emoji: '', country_codes: [], country_names: []}),
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getAllCurrencies: () => ['EUR', 'USD', 'CHF', 'GBP'].map((code) => ({code, name: `${code} fixture`, symbol: code, flag_emoji: '', country_codes: [], country_names: []})),
    suggestCurrency: vi.fn(async () => ({canonical: true, suggestion: null, candidates: []})),
}));

import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {fromDraft, toDraft, type OperatingProfileDocument, type ProfileDraft} from './brokerOperatingProfile';
import BrokerOperatingProfileBox from './BrokerOperatingProfileBox.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(cleanup);

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
    ],
    conversion_mode: 'manual',
    tax_regime: 'administered',
};

function mount(draft: ProfileDraft, props: Record<string, unknown> = {}) {
    const onchange = vi.fn<(next: ProfileDraft) => void>();
    render(BrokerOperatingProfileBox, {draft, onchange, ...props});
    flushSync();
    return onchange;
}

const last = (onchange: ReturnType<typeof vi.fn>) => onchange.mock.calls.at(-1)?.[0] as ProfileDraft;
const block = (currency: string) => screen.getAllByTestId('broker-profile-mode').find((item) => item.getAttribute('data-currency') === currency) as HTMLElement;

describe('BrokerOperatingProfileBox', () => {
    it('a Broker that said nothing reads «The Broker converts», badged as the default; «Converti tu» keeps the badge on the default (TL-6)', async () => {
        const onchange = mount(toDraft(null));
        const card = (mode: string) => screen.getAllByTestId('broker-profile-conversion-mode').find((item) => item.getAttribute('data-mode') === mode) as HTMLElement;
        expect(card('automatic').getAttribute('data-selected')).toBe('true');
        expect(card('manual').getAttribute('data-selected')).toBe('false');
        expect(within(card('automatic')).getByTestId('broker-profile-conversion-modes-default')).toBeTruthy();
        expect(within(card('manual')).queryByTestId('broker-profile-conversion-modes-default')).toBeNull();
        await fireEvent.click(within(card('manual')).getByTestId('broker-profile-conversion-mode-radio'));
        expect(last(onchange).conversionMode).toBe('manual');
        document.body.innerHTML = '';
        mount({...toDraft(null), conversionMode: 'manual'});
        expect(card('manual').getAttribute('data-selected')).toBe('true');
        expect(within(card('automatic')).getByTestId('broker-profile-conversion-modes-default')).toBeTruthy();
    });

    it('the order row has three columns: an amount shows its currency beside the number, aligned right; whole units none (TL-6)', async () => {
        const draft = toDraft(DOCUMENT);
        draft.rules[0].orderKind = 'monetary_amount';
        draft.rules[0].step = '0.01';
        mount(draft);
        const row = within(block('EUR')).getByTestId('broker-profile-mode-row');
        const currency = within(row).getByTestId('broker-profile-mode-step-currency');
        expect(currency.getAttribute('data-currency')).toBe('EUR');
        expect(currency.textContent).toContain('EUR');
        expect(within(row).getByTestId('broker-profile-mode-step').className).toContain('text-right');
        document.body.innerHTML = '';
        mount(toDraft(DOCUMENT));
        const units = within(block('EUR')).getByTestId('broker-profile-mode-step-currency');
        expect(units.getAttribute('data-currency')).toBe('');
        expect(units.textContent?.trim()).toBe('');
    });

    it('renders one block per currency and reports every edit', async () => {
        const onchange = mount(toDraft(DOCUMENT));
        expect(screen.getAllByTestId('broker-profile-mode').map((item) => item.getAttribute('data-currency'))).toEqual(['EUR']);

        // A decimal typed.
        await fireEvent.input(within(block('EUR')).getByTestId('broker-profile-mode-fee-rate'), {target: {value: '0.2'}});
        expect(last(onchange).rules[0].buy.ratePercent).toBe('0.2');

        // The order type, through the project's select.
        await fireEvent.click(within(block('EUR')).getByTestId('broker-profile-mode-kind-button'));
        await fireEvent.click(await screen.findByTestId('broker-profile-mode-kind-option-monetary_amount'));
        expect(last(onchange).rules[0].orderKind).toBe('monetary_amount');

        // The conversion and the regime, as big cards; the conversion keeps the planner's ids (`…-conversion-mode`, `data-mode`).
        expect(screen.getAllByTestId('broker-profile-conversion-mode').map((card) => card.getAttribute('data-mode'))).toEqual(['manual', 'automatic']);
        await fireEvent.click(screen.getAllByTestId('broker-profile-conversion-mode-radio')[1]);
        expect(last(onchange).conversionMode).toBe('automatic');
        await fireEvent.click(screen.getAllByTestId('broker-profile-tax-regime-radio')[1]);
        expect(last(onchange).taxRegime).toBe('declarative');

        // Add a currency, then remove it.
        await fireEvent.click(screen.getByTestId('broker-profile-mode-add'));
        expect(last(onchange).rules).toHaveLength(2);
        const added = screen.getAllByTestId('broker-profile-mode')[1];
        await fireEvent.click(within(added).getByTestId('broker-profile-mode-remove'));
        expect(last(onchange).rules).toHaveLength(1);
    });

    it('groups chooses what the box shows', () => {
        mount(toDraft(DOCUMENT));
        expect(screen.getAllByTestId('broker-profile-group').map((item) => item.getAttribute('data-group'))).toEqual(['orderMode', 'buyFee', 'sellFee', 'conversion', 'taxRegime']);
        cleanup();

        mount(toDraft(DOCUMENT), {groups: ['orderMode', 'buyFee', 'conversion']});
        const shown = screen.getAllByTestId('broker-profile-group').map((item) => item.getAttribute('data-group'));
        expect(shown).toEqual(['orderMode', 'buyFee', 'conversion']);
        expect(screen.queryByTestId('broker-profile-tax-regime')).toBeNull();
        expect(screen.queryByTestId('broker-profile-mode-sell-same')).toBeNull();
    });

    it('hidden groups travel through untouched', async () => {
        const onchange = mount(toDraft(DOCUMENT), {groups: ['orderMode', 'buyFee', 'conversion']});

        await fireEvent.input(within(block('EUR')).getByTestId('broker-profile-mode-fee-rate'), {target: {value: '0.25'}});

        const saved = fromDraft(last(onchange));
        const fees = saved?.order_modes?.[0].fees ?? [];
        expect(fees.find((fee) => fee.side === 'sell')).toEqual(DOCUMENT.order_modes?.[0].fees?.[1]);
        expect(saved?.tax_regime).toBe('administered');
        expect(fees.find((fee) => fee.side === 'buy')?.rate).toBe('0.0025');
    });

    it('copy rules from another currency adds one block, and a currency already there cannot be the target', async () => {
        const onchange = mount(toDraft(DOCUMENT));

        await fireEvent.click(screen.getByTestId('broker-profile-copy-open'));
        await fireEvent.click(screen.getByTestId('broker-profile-copy-to-trigger'));
        // EUR already has rules: it is not offered as a target.
        expect(screen.queryByTestId('search-select-option-EUR')).toBeNull();
        await fireEvent.click(await screen.findByTestId('search-select-option-CHF'));
        await fireEvent.click(screen.getByTestId('broker-profile-copy-confirm'));
        await tick();

        const rules = last(onchange).rules;
        expect(rules.map((item) => item.currency)).toEqual(['EUR', 'CHF']);
        expect({...rules[1], key: rules[0].key, currency: 'EUR'}).toEqual(rules[0]);
    });

    it('an empty field is as tall as a filled one', () => {
        mount(toDraft(DOCUMENT));
        const filled = within(block('EUR')).getByTestId('broker-profile-mode-fee-floor');
        const empty = within(block('EUR')).getByTestId('broker-profile-mode-fee-fixed');

        expect((filled as HTMLInputElement).value).toBe('1.5');
        expect((empty as HTMLInputElement).value).toBe('');
        expect(empty.tagName).toBe(filled.tagName);
        expect(empty.className).toBe(filled.className);
    });

    it('a field the backend would refuse is marked, and none is a select element', async () => {
        mount(toDraft(DOCUMENT));
        await fireEvent.input(within(block('EUR')).getByTestId('broker-profile-mode-step'), {target: {value: '0'}});
        flushSync();

        expect(within(block('EUR')).getByTestId('broker-profile-mode-step').getAttribute('aria-invalid')).toBe('true');
        expect(
            within(block('EUR'))
                .getAllByTestId('broker-profile-mode-problem')
                .map((item) => item.getAttribute('data-key')),
        ).toEqual(['stepNotPositive']);
        expect(document.querySelector('select')).toBeNull();
    });

    it('the currencies a plan needs and the profile lacks come as empty blocks to fill (the planner, P3)', () => {
        mount(toDraft(DOCUMENT), {requiredCurrencies: ['EUR', 'USD']});

        expect(screen.getAllByTestId('broker-profile-mode').map((item) => [item.getAttribute('data-currency'), item.getAttribute('data-required')])).toEqual([
            ['EUR', 'true'],
            ['USD', 'true'],
        ]);
        expect(within(block('USD')).getByTestId('broker-profile-mode-required')).toBeVisible();
    });
    it('a caller can rename the root and reset the increment when the order type changes (the planner, P3)', async () => {
        const stepFor = (kind: string, currency: string) => (kind === 'whole_quantity' ? '1' : currency === 'EUR' ? '0.01' : '1');
        const onchange = mount(toDraft(DOCUMENT), {rootTestid: 'probe-root', stepFor});
        expect(screen.getByTestId('probe-root')).toBeVisible();
        expect(screen.queryByTestId('broker-profile')).toBeNull();
        expect(block('EUR').getAttribute('data-kind')).toBe('whole_quantity');

        await fireEvent.click(within(block('EUR')).getByTestId('broker-profile-mode-kind-button'));
        await fireEvent.click(await screen.findByTestId('broker-profile-mode-kind-option-monetary_amount'));
        flushSync();

        expect(last(onchange).rules[0]).toMatchObject({orderKind: 'monetary_amount', step: '0.01'});
        expect(block('EUR').getAttribute('data-kind')).toBe('monetary_amount');
        expect((within(block('EUR')).getByTestId('broker-profile-mode-step') as HTMLInputElement).value).toBe('0.01');
    });

    it('without stepFor the increment stays as typed («Edit broker»)', async () => {
        const onchange = mount(toDraft(DOCUMENT));
        await fireEvent.click(within(block('EUR')).getByTestId('broker-profile-mode-kind-button'));
        await fireEvent.click(await screen.findByTestId('broker-profile-mode-kind-option-monetary_amount'));
        expect(last(onchange).rules[0]).toMatchObject({orderKind: 'monetary_amount', step: '1'});
    });
});
