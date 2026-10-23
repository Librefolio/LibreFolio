// @vitest-environment jsdom
/**
 * OtherPeriodEffectsTable — component test (Vitest + jsdom): the «FX on cash» row (release 1.2, gap 2).
 *
 * WHAT IS UNDER TEST. The backend appends to `positions_contribution.other_effects` one `FX on cash` row
 * (category `Other`, with the broker's id and name) for each broker whose foreign cash gained or lost to
 * exchange over the period, after the unallocated income and cost rows and before the reconciliation
 * residual (`PortfolioService.get_positions_contribution`). This table renders the rows as they come:
 *   - the description is the catalogue's `dashboard.fxOnCash`, never the backend's English string, followed
 *     by the broker name, and the broker column carries the broker's badge;
 *   - the amount is signed in the display currency: `+` on a gain, the minus on a loss, no sign on zero,
 *     and a dash, never `0.00`, when the amount is missing;
 *   - the rows keep the order of `effects`, and each row's test ids are keyed by its index in `effects`,
 *     its category and its broker (`effect-{index}-{category}-{broker_id|global}`): a spec derives the key
 *     from the API's order, never from a position on screen. The ids are stamped by an effect after the
 *     table renders, on the third cell for the amount, so every case checks that the amount id lands on
 *     the `period-pnl` column.
 *
 * WHAT IS NOT ASSERTED. Translated text. Labels are read in a marker locale, where every key of the
 * English catalogue reads as `⟦key⟧`: a label the component takes from the catalogue reads as the marker
 * of its key, a literal written in the component reads as itself. The control is the section header,
 * already `dashboard.otherPeriodEffects`. Amounts are rebuilt with the same `toLocaleString` call the
 * formatter makes, so the file passes on any host locale. Broker names are the ones this file passes in.
 *
 * WHAT IS MOCKED, AND WHY. Two gaps of the environment, as in the dashboard neighbours:
 *   - `$lib/api`: the broker badge asks `GET /brokers/{id}` for the icon fields of a broker it only knows by
 *     id and name; it is answered with the id alone, and nothing else here reaches the network
 *     (`ContributionTable.test.ts`);
 *   - `getCurrencyInfo`: the real store is a session cache filled by `GET /currencies`, empty here; EUR gets
 *     its real symbol and flag, every other code keeps the store's fallback, symbol = code and no flag
 *     (`PerformanceChart.test.ts`).
 */
import type {ComponentProps} from 'svelte';
import {addMessages} from 'svelte-i18n';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, key) {
                if (key === 'get_broker_api_v1_brokers__broker_id__get') return vi.fn(async ({params}: {params: {broker_id: number}}) => ({id: params.broker_id}));
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

/** EUR as `GET /currencies` describes it. Shared by the mock and by the expectations, so the two cannot drift apart. */
const {EUR_INFO} = vi.hoisted(() => ({
    EUR_INFO: {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [] as string[], country_names: [] as string[]},
}));

vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    getCurrencyInfo: (code: string) => (code === EUR_INFO.code ? EUR_INFO : {code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []}),
}));

import en from '$lib/i18n/en.json';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {render, screen, setupI18n, waitFor} from '$test/component';
import OtherPeriodEffectsTable from './OtherPeriodEffectsTable.svelte';

type Effect = ComponentProps<typeof OtherPeriodEffectsTable>['effects'][number];

// =============================================================================
// Fixtures
// =============================================================================

/** An «FX on cash» row as the backend sends it: its English description is a contract, not a label. */
function fxOnCash(brokerId: number, brokerName: string, periodPnl: string): Effect {
    return {description: 'FX on cash', category: 'Other', period_pnl: periodPnl, broker_id: brokerId, broker_name: brokerName};
}

/** A «Transfers at market value» row as the backend sends it (one per broker): its English description is a contract, not a label. */
function transfersAtMarket(brokerId: number, brokerName: string, periodPnl: string): Effect {
    return {description: 'Transfers at market value', category: 'Other', period_pnl: periodPnl, broker_id: brokerId, broker_name: brokerName};
}

/** The key the component derives for the effect at `index`, the one its test ids carry. */
function keyOf(index: number, effect: Effect): string {
    return `effect-${index}-${effect.category}-${effect.broker_id ?? 'global'}`;
}

// =============================================================================
// What the component prints, rebuilt with the calls it makes
// =============================================================================

/**
 * The number `formatCurrencyAmountPlain` prints: the absolute value with two decimals, through the same call and in the same
 * locale — the interface locale (`uiLocale()`), never the host's, so the file passes on an Italian machine too.
 */
function plainAmount(value: number): string {
    return Math.abs(value).toLocaleString(uiLocale(), {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

/** What `formatCurrencyAmountPlain` appends for EUR under the currency mock: symbol, flag, code. */
const EUR_TAIL = ` ${EUR_INFO.symbol} ${EUR_INFO.flag_emoji} ${EUR_INFO.code}`;

/** What the table renders for a missing amount: a dash, written in the component, never a zero. */
const DASH = '—';

/** A private-use language (BCP 47 reserves qaa–qtz): Intl accepts it, and it is none of the app's catalogues. */
const MARKER_LOCALE = 'qaa';

/** How a catalogue label reads in the marker locale. */
const marked = (key: string): string => `⟦${key}⟧`;

/** Every dotted key of a catalogue that holds a string. */
function stringKeysOf(node: unknown, prefix = ''): string[] {
    if (typeof node === 'string') return [prefix];
    if (node === null || typeof node !== 'object') return [];
    return Object.entries(node).flatMap(([part, child]) => stringKeysOf(child, prefix ? `${prefix}.${part}` : part));
}

/** Switch svelte-i18n to the marker locale: every key of the English catalogue reads as its marker. */
async function useMarkerLocale(): Promise<void> {
    addMessages(MARKER_LOCALE, Object.fromEntries(stringKeysOf(en).map((key) => [key, marked(key)])));
    await setupI18n(MARKER_LOCALE);
}

// =============================================================================
// Reading the table
// =============================================================================

/** The row of `key`, once the component has stamped its test id (an effect does it after the table renders). */
async function rowOf(key: string): Promise<HTMLElement> {
    return waitFor(() => screen.getByTestId(`other-period-effects-row-${key}`));
}

/** The amount cell of `key`: the id the component stamps, checked to sit on the period P&L column. */
async function amountCellOf(key: string): Promise<HTMLElement> {
    await rowOf(key);
    const cell = await waitFor(() => screen.getByTestId(`other-period-effects-pnl-${key}`));
    expect(cell.getAttribute('data-column-id'), `the amount id of ${key} is stamped on the period P&L column`).toBe('period-pnl');
    return cell;
}

function cellIn(row: HTMLElement, columnId: string): HTMLElement {
    const cell = row.querySelector<HTMLElement>(`td[data-column-id="${columnId}"]`);
    if (!cell) throw new Error(`the row has no ${columnId} cell`);
    return cell;
}

/** The row ids in the order the table shows them. */
function renderedKeys(): string[] {
    return [...document.querySelectorAll<HTMLElement>('tbody tr[data-row-id]')].map((row) => row.getAttribute('data-row-id') ?? '');
}

// =============================================================================
// Harness
// =============================================================================

beforeAll(async () => {
    await setupI18n();
});

afterEach(async () => {
    await setupI18n('en');
});

describe('OtherPeriodEffectsTable — the FX on cash row (release 1.2, gap 2)', () => {
    it("labels an FX on cash row with the catalogue's dashboard.fxOnCash beside the broker name, under the Other category, with the broker's badge", async () => {
        await useMarkerLocale();
        const effect = fxOnCash(41, 'Probe FX Broker', '-175');
        const key = keyOf(0, effect);
        render(OtherPeriodEffectsTable, {effects: [effect], displayCurrency: 'EUR'});

        const header = screen.getByTestId('other-period-effects-header');
        expect(header, 'control: the header already takes its title from the catalogue, so the marker locale is live').toHaveTextContent(marked('dashboard.otherPeriodEffects'));

        const row = await rowOf(key);
        expect(cellIn(row, 'description').textContent?.trim(), 'the backend string is mapped to its catalogue key, then the broker name').toBe(`${marked('dashboard.fxOnCash')} — Probe FX Broker`);
        expect(screen.getByTestId(`other-period-effects-category-${key}`).textContent?.trim()).toBe(marked('dashboard.categoryOther'));
        const badge = cellIn(row, 'broker').querySelector<HTMLElement>('[data-testid="broker-badge-41"]');
        expect(badge, 'the broker column shows the badge of the broker the row belongs to').not.toBeNull();
        expect(badge).toHaveTextContent('Probe FX Broker');
    });

    it('prints the amount signed in the display currency: + on a gain, the minus on a loss, no sign on zero, a dash when it is missing', async () => {
        const effects = [
            fxOnCash(41, 'Gain Broker', '125.5'),
            fxOnCash(42, 'Loss Broker', '-1234.5'),
            fxOnCash(43, 'Flat Broker', '0'),
            // The contract types the amount as a string; the component still guards a missing one, and must
            // say it does not know it rather than print a zero.
            {...fxOnCash(44, 'Unknown Broker', '0'), period_pnl: null as unknown as string},
        ];
        const expected = [`+${plainAmount(125.5)}${EUR_TAIL}`, `-${plainAmount(1234.5)}${EUR_TAIL}`, `${plainAmount(0)}${EUR_TAIL}`, DASH];
        render(OtherPeriodEffectsTable, {effects, displayCurrency: 'EUR'});

        for (const [index, effect] of effects.entries()) {
            const cell = await amountCellOf(keyOf(index, effect));
            expect(cell.textContent?.trim(), `${keyOf(index, effect)} (${String(effect.period_pnl)})`).toBe(expected[index]);
        }
    });

    it('prints the amount in the display currency it is given, not in a default one', async () => {
        const effect = fxOnCash(41, 'Probe FX Broker', '-175');
        render(OtherPeriodEffectsTable, {effects: [effect], displayCurrency: 'CHF'});

        // CHF has no symbol of its own under the store's fallback: the amount, then the code.
        const cell = await amountCellOf(keyOf(0, effect));
        expect(cell.textContent?.trim()).toBe(`-${plainAmount(175)} CHF`);
    });

    it('keeps the rows in the order of effects — not by amount, broker or category — and re-keys them when the order changes', async () => {
        // The backend's order: unallocated income and costs first, then the FX rows in access order (here broker
        // 42 before broker 41), then the residual. Nothing in it is sorted by a column.
        const effects: Effect[] = [
            {description: 'Unallocated income', category: 'Income', period_pnl: '80', broker_id: 7, broker_name: 'Income Broker'},
            {description: 'Unallocated costs', category: 'Cost', period_pnl: '-8', broker_id: 7, broker_name: 'Income Broker'},
            fxOnCash(42, 'Second Access Broker', '-103.25'),
            fxOnCash(41, 'First Id Broker', '262.5'),
            {description: 'Other / reconciliation residual', category: 'Other', period_pnl: '-10', broker_id: null, broker_name: null},
        ];
        const amounts = [`+${plainAmount(80)}`, `-${plainAmount(8)}`, `-${plainAmount(103.25)}`, `+${plainAmount(262.5)}`, `-${plainAmount(10)}`].map((amount) => `${amount}${EUR_TAIL}`);
        const {rerender} = render(OtherPeriodEffectsTable, {effects, displayCurrency: 'EUR'});

        const keys = effects.map((effect, index) => keyOf(index, effect));
        expect(keys, 'the residual has no broker: its key ends in global').toContain('effect-4-Other-global');
        await waitFor(() => expect(renderedKeys()).toEqual(keys));
        for (const [index, key] of keys.entries()) {
            expect((await rowOf(key)).getAttribute('data-row-id')).toBe(key);
            expect((await amountCellOf(key)).textContent?.trim(), `${key} carries the amount of effects[${index}]`).toBe(amounts[index]);
        }

        const reversed = [...effects].reverse();
        const reversedKeys = reversed.map((effect, index) => keyOf(index, effect));
        await rerender({effects: reversed, displayCurrency: 'EUR'});

        await waitFor(() => expect(renderedKeys()).toEqual(reversedKeys));
        for (const [index, key] of reversedKeys.entries()) {
            await waitFor(() => expect(screen.getByTestId(`other-period-effects-pnl-${key}`).textContent?.trim(), `${key} carries the amount of the reversed effects[${index}]`).toBe(amounts[effects.length - 1 - index]));
        }
    });
});

describe('OtherPeriodEffectsTable — the Transfers at market value row (Y5-F5)', () => {
    it("labels a Transfers at market value row with the catalogue's dashboard.transfersAtMarketValue beside the broker name, under the Other category, with the broker's badge", async () => {
        await useMarkerLocale();
        const effect = transfersAtMarket(51, 'Probe Transfer Broker', '-60');
        const key = keyOf(0, effect);
        render(OtherPeriodEffectsTable, {effects: [effect], displayCurrency: 'EUR'});

        const header = screen.getByTestId('other-period-effects-header');
        expect(header, 'control: the header already takes its title from the catalogue, so the marker locale is live').toHaveTextContent(marked('dashboard.otherPeriodEffects'));

        const row = await rowOf(key);
        expect(cellIn(row, 'description').textContent?.trim(), 'the backend string is mapped to its catalogue key, then the broker name').toBe(`${marked('dashboard.transfersAtMarketValue')} — Probe Transfer Broker`);
        expect(screen.getByTestId(`other-period-effects-category-${key}`).textContent?.trim()).toBe(marked('dashboard.categoryOther'));
        const badge = cellIn(row, 'broker').querySelector<HTMLElement>('[data-testid="broker-badge-51"]');
        expect(badge, 'the broker column shows the badge of the broker the row belongs to').not.toBeNull();
        expect(badge).toHaveTextContent('Probe Transfer Broker');
    });

    it('keeps the backend order of a row from two brokers, and each row shows its own broker name', async () => {
        await useMarkerLocale();
        // One row per broker, in the backend's access order (broker 62 before broker 61): nothing sorts them.
        const effects: Effect[] = [transfersAtMarket(62, 'Second Access Broker', '40'), transfersAtMarket(61, 'First Id Broker', '-40')];
        render(OtherPeriodEffectsTable, {effects, displayCurrency: 'EUR'});

        const keys = effects.map((effect, index) => keyOf(index, effect));
        await waitFor(() => expect(renderedKeys()).toEqual(keys));
        const names = ['Second Access Broker', 'First Id Broker'];
        for (const [index, key] of keys.entries()) {
            const row = await rowOf(key);
            expect(cellIn(row, 'description').textContent?.trim(), `${key} shows its own broker`).toBe(`${marked('dashboard.transfersAtMarketValue')} — ${names[index]}`);
        }
    });

    it('guard: a description the table does not know is still printed as the backend sent it', async () => {
        await useMarkerLocale();
        const effect: Effect = {description: 'Probe unknown effect', category: 'Other', period_pnl: '5', broker_id: 71, broker_name: 'Probe Broker'};
        const key = keyOf(0, effect);
        render(OtherPeriodEffectsTable, {effects: [effect], displayCurrency: 'EUR'});

        const row = await rowOf(key);
        expect(cellIn(row, 'description').textContent?.trim()).toBe('Probe unknown effect — Probe Broker');
    });
});
