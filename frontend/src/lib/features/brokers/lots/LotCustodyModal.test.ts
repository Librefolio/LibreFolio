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
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import type {z} from 'zod';
import {cleanup, render, screen, setupI18n, within} from '$test/component';
import {schemas} from '$lib/api';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import LotCustodyModal from './LotCustodyModal.svelte';

type LotSummary = z.infer<typeof schemas.LotSummarySchema>;

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
 * for a reason that is not this one. Nothing below reads the history section.
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
