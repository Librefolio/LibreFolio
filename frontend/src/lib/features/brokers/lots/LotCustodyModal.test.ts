// @vitest-environment jsdom
/**
 * LotCustodyModal — the lot's opening value is the backend's `original_cost` (workstream Y, lot Y12a, U8).
 *
 * The contract. The modal's summary shows the lot's opening value (`brokers.lots.modal.openingValue`). By U8 (plan
 * rule 10) the frontend shows the backend's figure, and the backend sends it: `LotSummarySchema.original_cost`, the
 * original lot cost in the response's target currency, null when the rate at the opening date is missing. The lots
 * table, the WAC chart and the Gantt read that field. Until Y12a the modal rebuilt the figure in the browser instead, as
 * `original_quantity × opening_unit_price` (`lotOpeningValue`, through `multiplyOrNull`).
 *
 * Agreed with J, owner of the lot numbers, on 16/10: the engine keeps `original_quantity × opening_unit_price =
 * original_cost`, so reading the field changes no figure (it only drops the rounding of a float product), and the
 * null cases are the same (a missing rate). J's edge cases: a lot opened by an adjustment without cost is worth 0, not
 * «—» (the third test); a short lot is worth the notional sold.
 *
 * On `d5c3c3ae3`, with the cell's test id added, the first two tests are red on their subject assertion: the cell
 * shows the product, 100, where the backend said 150 and where it said null. The third is a control, green before and
 * after the cure: a cost of zero is a value, not a missing one.
 *
 * The harness. The modal runs as in the app, with real i18n, the real ModalBase, the real formatter and no module
 * mocked. Its lot is parsed by the generated client's own schema (`schemas.LotSummarySchema`), so the component
 * receives what the client lets through: every required field present, the schema's defaults filled in. The builder
 * checks that the three amounts survive the parse. The lot is fully closed, so it holds no custody slice and no
 * BrokerBadge (with its broker icon) is mounted. The asset store is only looked up, and it is empty, so the title
 * names the asset `#id`. Neither makes a request.
 *
 * Expectations. The cell is read by its test id, `lot-custody-modal-opening-value`, inside the modal's own. An amount is
 * expected through the formatter `formatPrice` calls, `formatCurrencyAmountPlain(value, currency)` with no options, in
 * this runtime: the locale and the currency suffix are whatever the modal gets, never a frozen string. The missing
 * value is `formatPrice`'s own `—`, a literal: a placeholder has no locale. Nothing here reads translated text.
 *
 * C-97c-2 (the last block): the modal's quantities and prices per unit lose no digit. That block mounts lots with a
 * history, because its subject is shown there; the opening value above does not depend on it.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {z} from 'zod';
import {cleanup, render, screen, setupI18n, within} from '$test/component';
import {schemas} from '$lib/api';
import {uiLocale} from '$lib/stores/app/uiLocale';
import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import LotCustodyModal from './LotCustodyModal.svelte';

type LotSummary = z.infer<typeof schemas.LotSummarySchema>;
type LotTimelineEvent = z.infer<typeof schemas.LotTimelineEventSchema>;

/** The three amounts under test, as the API serialises them: Decimal strings, null where the backend has no value. */
interface OpeningAmounts {
    original_quantity: string;
    opening_unit_price: string;
    original_cost: string | null;
}

/** The response's target currency: the modal's `currency` prop, in which `formatPrice` writes every amount. */
const CURRENCY = 'EUR';

/** The opening-value cell: the `<dd>` under `brokers.lots.modal.openingValue`. */
const OPENING_VALUE = 'lot-custody-modal-opening-value';

/** What the modal's `formatPrice` renders for a missing amount (`parsed == null ? '—' : …`). */
const MISSING = '—';

const LOT_ID = 7_412;

/**
 * A fully closed LONG lot as `POST /portfolio/lots/analysis` serialises it, parsed by the generated client's schema
 * as the app receives it. Every required field of `LotSummarySchema` is here. `states` and `current_custody` are what
 * the backend sends for a closed lot (it always sends both). The optional fields left out are filled by the schema's
 * own defaults where it has one (`asset_income`, `allocated_fees`, `allocated_taxes`: '0'; `net_metrics_status`:
 * AVAILABLE), as for a real response.
 */
function closedLot(amounts: OpeningAmounts): LotSummary {
    const lot = schemas.LotSummarySchema.parse({
        lot_id: LOT_ID,
        opening_transaction_id: LOT_ID, // equals lot_id, as the schema states
        asset_id: 9_031,
        direction: 'LONG',
        opening_broker_id: 61,
        opening_date: '2025-02-03',
        closing_date: '2025-09-15',
        open_quantity: '0',
        realized_quantity: amounts.original_quantity,
        states: ['LONG', 'CLOSED'],
        current_custody: [],
        ...amounts,
    });
    // Control: the client lets the three amounts through unchanged. A generated schema without `original_cost` would
    // strip it here, and the red would belong to the client, not to the modal.
    expect({original_quantity: lot.original_quantity, opening_unit_price: lot.opening_unit_price, original_cost: lot.original_cost}, 'control: the generated client keeps the amounts as sent').toEqual(amounts);
    return lot;
}

/** Open the modal on `lot`, with no history and no broker list, and return its opening-value cell. */
function openingValueCellFor(lot: LotSummary): HTMLElement {
    render(LotCustodyModal, {open: true, lot, history: [], brokers: [], currency: CURRENCY, onClose: vi.fn()});
    return within(screen.getByTestId('lot-custody-modal')).getByTestId(OPENING_VALUE);
}

/** An amount as the modal's `formatPrice` writes it: the shared formatter, called the way `formatPrice` calls it. */
function money(amount: number): string {
    return formatCurrencyAmountPlain(amount, CURRENCY);
}

/** The text the cell shows. */
function shown(cell: HTMLElement): string {
    return (cell.textContent ?? '').trim();
}

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
});

/**
 * The amounts are inconsistent on purpose. The engine's own numbers agree (quantity × price = cost), and with them the
 * product and the field print the same text, so a test could not tell which one the modal reads. Here 10 × 10 = 100
 * while the backend says 150, or null: the cell can match one source only.
 *
 * The history is left empty on purpose too. The opening value does not depend on it, and J's CP-7a (backend, entering
 * soon) changes the values the modal's history shows, its closure rows. Pinning those here would turn that change red
 * for a reason that is not this one. Nothing in this block reads the history section (the C-97c-2 block, at the end of
 * the file, does: its subject is shown there).
 */
describe('LotCustodyModal — the opening value is the backend’s original_cost (Y12a, U8)', () => {
    // Red on d5c3c3ae3: the cell shows the product, 10 × 10 = 100.
    it('shows original_cost (150), not original_quantity × opening_unit_price (10 × 10 = 100)', () => {
        const lot = closedLot({original_quantity: '10', opening_unit_price: '10', original_cost: '150'});
        // Controls: the expected text carries the digits put in and differs from the product's. A formatter that masked
        // both (privacy on) would otherwise leave this test unable to tell the two sources apart.
        expect(money(150).replace(/\D/g, ''), 'control: the expected text carries the digits of 150').toBe('15000');
        expect(money(150), 'control: the cost and the product print differently').not.toBe(money(100));

        const cell = openingValueCellFor(lot);

        expect(shown(cell), 'the opening value is original_cost, formatted as the modal formats money, not the product of quantity and price').toBe(money(150));
    });

    // Red on d5c3c3ae3: quantity and price are both there, so the product is a number, 100.
    it('shows the missing-value placeholder when original_cost is null, quantity and price present', () => {
        const cell = openingValueCellFor(closedLot({original_quantity: '10', opening_unit_price: '10', original_cost: null}));

        expect(shown(cell), 'no cost from the backend (no rate at the opening date): «—», not a product rebuilt in the browser').toBe(MISSING);
    });

    // Green before and after the cure: J's edge case, a lot opened by an adjustment without cost.
    it('control (J’s edge case): a lot opened without cost, original_cost 0, is worth zero, not the placeholder', () => {
        const cell = openingValueCellFor(closedLot({original_quantity: '10', opening_unit_price: '0', original_cost: '0'}));

        expect(money(0), 'control: zero prints as an amount, not as the placeholder').not.toBe(MISSING);
        expect(shown(cell), 'a cost of zero is a value: zero formatted as money').toBe(money(0));
    });
});

// ---------------------------------------------------------------------------
// C-97c-2 — the modal's quantities and prices per unit lose no digit
// ---------------------------------------------------------------------------

/**
 * D-C97c-1 (the coordinator, 17/10), applied to the lots (BK). A lot quantity keeps the ten decimals of its column; a
 * price per unit the decimals its first four significant digits need (`priceFractionDigits`, formatFixed.ts). Today the
 * modal's `formatQuantity` hands a number to `formatExactDecimal(abs, {maxFrac: 8})`: 0.1234567891 is cut at the eighth
 * decimal, and a quantity under 1e-6 goes through `String()`, so 0.0000001 reads `1e-7`. Its `formatUnitPrice`, the
 * opening and the closing price per unit (public), writes two fixed decimals: 0.000003457312 EUR reads 0.00. The
 * contract: the quantity through the lots' shared `formatLotQuantity` (up to ten decimals, never an exponent), the price
 * per unit with `{minFraction, maxFraction}` from `priceFractionDigits(value)`. Totals stay money, as they are.
 *
 * Reds: a quantity of 0.1234567891 and one of 0.0000001 (10 satoshis), in every quantity cell the modal marks with a
 * test id — the custody summary row, the custody fragment row, and the history's opening (BUY, signed) and departure
 * (TRANSFER_DEPART) rows; a price per unit of 0.000003457312, in the history's opening (BUY) and closing (SELL) details.
 * Guards, green today and after: a quantity of 2.5 in the same cells — the control that each cell is read where its
 * quantity is — and a price per unit of 123.45 in both details. The summary's quantity and price cells carry no test id:
 * they go through the same two functions, and are not read here.
 *
 * Fixtures, each parsed by the generated client's schemas, as the app receives it. An open lot in transit: bought at
 * Broker Alfa at 1 EUR a unit (so its cost is its quantity), then sent off; its one custody slice is IN_TRANSIT, so no
 * BrokerBadge is mounted (its icon would ask the API for the broker). A closed lot: 10 units bought and sold at one
 * price, the sale carrying it as `close_unit_price` and `unit_price` alike (the modal reads the first, else the second),
 * with the proceeds of 10 units at that price — a figure no price token can be mistaken for. The history rows come by
 * date, so the opening is row 0.
 *
 * Reading. A cell by its test id inside the modal's own; a figure is matched as a whole number token in the cell's text —
 * no digit, decimal mark or separator glued to either side — never as the full currency string, which stays the shared
 * formatter's business. English UI: jsdom's browser is en-US, checked before each case, so the expected digits are typed.
 */
describe('LotCustodyModal — quantities and prices per unit lose no digit (C-97c-2, D-C97c-1)', () => {
    const BROKER = {id: 61, name: 'Broker Alfa'} satisfies BrokerLike;
    /** The transfer that sends the open lot off; the backend keys its departure row by the pair id. */
    const TRANSFER_ID = 7_520;
    /** The sale that closes the closed lot. */
    const SALE_ID = 7_530;

    /** A price per unit, and the value of 10 units at it, as decimal strings: the closed lot's figures. */
    interface PriceCase {
        price: string;
        tenUnits: string;
    }

    /** Its first four significant digits are 0.000003457. */
    const TINY_PRICE: PriceCase = {price: '0.000003457312', tenUnits: '0.00003457312'};
    const PLAIN_PRICE: PriceCase = {price: '123.45', tenUnits: '1234.5'};

    /** A number written in exponent notation, as `String()` writes one under 1e-6: `1e-7`. */
    const EXPONENT = /\d[eE][-+]?\d/;

    /** `digits` as a whole number in a text: no digit, decimal mark or group separator glued to either side. */
    function numberToken(digits: string): RegExp {
        return new RegExp(`(?<![\\d.,])${digits.replace(/\./g, '\\.')}(?![.,]?\\d)`);
    }

    /** A timeline event of the lot, as the generated client parses it. */
    function timelineEvent(event: Record<string, unknown>): LotTimelineEvent {
        return schemas.LotTimelineEventSchema.parse({lot_id: LOT_ID, ...event});
    }

    /** The text of the modal's element `testId`, whitespace runs collapsed. */
    function textOf(testId: string): string {
        return (within(screen.getByTestId('lot-custody-modal')).getByTestId(testId).textContent ?? '').replace(/\s+/g, ' ').trim();
    }

    /** Mount the modal on an open LONG lot of `quantity`, bought at Broker Alfa at 1 EUR a unit and now in transit. */
    function mountLotInTransit(quantity: string): void {
        const lot = schemas.LotSummarySchema.parse({
            lot_id: LOT_ID,
            opening_transaction_id: LOT_ID,
            asset_id: 9_031,
            direction: 'LONG',
            opening_broker_id: BROKER.id,
            opening_date: '2025-02-03',
            opening_unit_price: '1',
            original_quantity: quantity,
            original_cost: quantity, // 1 EUR a unit
            open_quantity: quantity,
            realized_quantity: '0',
            states: ['LONG', 'OPEN', 'IN_TRANSIT'],
            current_custody: [{custody_type: 'IN_TRANSIT', broker_id: null, quantity}],
        });
        const history = [
            timelineEvent({date: '2025-02-03', kind: 'BUY', transaction_id: LOT_ID, broker_id: BROKER.id, quantity, unit_price: '1', opening_value: quantity}),
            timelineEvent({
                date: '2025-03-10',
                kind: 'TRANSFER_DEPART',
                transaction_id: TRANSFER_ID,
                related_transaction_id: TRANSFER_ID,
                broker_id: null,
                source_broker_id: BROKER.id,
                destination_broker_id: 62,
                fragment_id: `lot:${LOT_ID}/transfer:${TRANSFER_ID}/transit`,
                quantity,
                unit_price: '1',
            }),
        ];
        // Control: the client keeps the quantity as sent — the lot's, its custody slice's and both events'.
        expect([lot.original_quantity, lot.open_quantity, lot.current_custody?.[0]?.quantity, ...history.map((event) => event.quantity)], 'control: the generated client keeps the quantity as sent').toEqual(new Array<string>(5).fill(quantity));
        render(LotCustodyModal, {open: true, lot, history, brokers: [BROKER], currency: CURRENCY, onClose: vi.fn()});
    }

    /** What each quantity cell of the modal shows, by its test id. */
    function quantityCells(): Record<string, string> {
        return {
            'custody summary': textOf('lot-custody-modal-custody-summary-row-0'),
            'custody fragment': textOf('lot-custody-modal-custody-row-0'),
            'history, opening': textOf('lot-custody-modal-history-row-0'),
            'history, departure': textOf('lot-custody-modal-history-row-1'),
        };
    }

    /** Mount the modal on a closed LONG lot: 10 units bought at Broker Alfa at `price`, sold at the same price. */
    function mountLotClosedAt({price, tenUnits}: PriceCase): void {
        const lot = schemas.LotSummarySchema.parse({
            lot_id: LOT_ID,
            opening_transaction_id: LOT_ID,
            asset_id: 9_031,
            direction: 'LONG',
            opening_broker_id: BROKER.id,
            opening_date: '2025-02-03',
            closing_date: '2025-09-15',
            opening_unit_price: price,
            original_quantity: '10',
            original_cost: tenUnits,
            open_quantity: '0',
            realized_quantity: '10',
            realized_pnl: '0',
            cumulative_proceeds: tenUnits,
            states: ['LONG', 'CLOSED'],
            current_custody: [],
        });
        const history = [
            timelineEvent({date: '2025-02-03', kind: 'BUY', transaction_id: LOT_ID, broker_id: BROKER.id, quantity: '10', unit_price: price, opening_value: tenUnits}),
            timelineEvent({date: '2025-09-15', kind: 'SELL', transaction_id: SALE_ID, broker_id: BROKER.id, quantity: '10', unit_price: price, open_unit_price: price, close_unit_price: price, proceeds: tenUnits, realized_pnl: '0'}),
        ];
        // Control: the client keeps the price as sent, in each field the modal reads it from.
        expect([history[0].unit_price, history[1].close_unit_price, history[1].unit_price], 'control: the generated client keeps the price as sent').toEqual([price, price, price]);
        render(LotCustodyModal, {open: true, lot, history, brokers: [BROKER], currency: CURRENCY, onClose: vi.fn()});
    }

    /** The details of the history's opening (BUY) and closing (SELL) rows, by their test ids. */
    function priceDetails(): {opening: string; closing: string} {
        return {opening: textOf('lot-custody-modal-history-details-0'), closing: textOf('lot-custody-modal-history-details-1')};
    }

    beforeEach(() => {
        // The expected digits are typed: the premise that the modal writes en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    it('a quantity of 0.1234567891 reads whole in every quantity cell: the ten decimals of its column, not eight', () => {
        mountLotInTransit('0.1234567891');

        for (const [cell, shown] of Object.entries(quantityCells())) {
            expect.soft(shown, `${cell}: ten decimals (today cut at the eighth: 0.12345678)`).toMatch(numberToken('0.1234567891'));
        }
    });

    it('a quantity of 0.0000001, a lot of 10 satoshis, reads 0.0000001 in every quantity cell, never in exponent notation', () => {
        mountLotInTransit('0.0000001');

        for (const [cell, shown] of Object.entries(quantityCells())) {
            expect.soft(shown, `${cell}: its seventh decimal (today 1e-7)`).toMatch(numberToken('0.0000001'));
            expect.soft(shown, `${cell}: no exponent notation (today 1e-7: String() of a number under 1e-6)`).not.toMatch(EXPONENT);
        }
    });

    it('guard: a quantity of 2.5 still reads 2.5 in every quantity cell — the control that each cell is read where its quantity is', () => {
        mountLotInTransit('2.5');

        for (const [cell, shown] of Object.entries(quantityCells())) {
            expect.soft(shown, cell).toMatch(numberToken('2.5'));
        }
    });

    it('a price per unit of 0.000003457312 EUR shows 0.000003457, opening and closing: four significant digits, not 0.00', () => {
        mountLotClosedAt(TINY_PRICE);
        const {opening, closing} = priceDetails();

        expect.soft(opening, 'the opening price (today 0.00)').toMatch(numberToken('0.000003457'));
        expect.soft(closing, 'the closing price (today 0.00)').toMatch(numberToken('0.000003457'));
    });

    it('guard: a price per unit of 123.45 EUR still shows 123.45, opening and closing', () => {
        mountLotClosedAt(PLAIN_PRICE);
        const {opening, closing} = priceDetails();

        expect.soft(opening, 'the opening price').toMatch(numberToken('123.45'));
        expect.soft(closing, 'the closing price').toMatch(numberToken('123.45'));
    });
});
