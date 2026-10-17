// @vitest-environment jsdom
/**
 * LotAnalysisFailedNotice — a FAILED lots analysis says what failed, where, and which transaction to fix (workstream Y,
 * lot J-12, panel half).
 *
 * The contract. `POST /portfolio/lots/analysis` answers `calculation_status: FAILED` when the FIFO replay of the
 * quantities fails (backend `_QUANTITATIVE_FAILURE_CODES`). Until J-12 the panel showed one red line («figures may be
 * incomplete»), kept drawing every chart, and left the issues to the banner, whose catalogue messages end in
 * «(broker {broker_id})»: the user read «(broker 7)». The developer's decision: on FAILED the panel shows a plain
 * explanation and, per blocking issue, the broker's name, the day and a way to the transaction to fix. This component
 * is that notice. The panel partitions the issues (`partitionLotIssues`) and hands it the blocking ones; the notice
 * draws `buildFailureRows(issues, brokers, quantity formatter)`:
 *   - the root `lots-analysis-panel-failed` (the test id of today's line), `role="alert"`, with the explanation
 *     `lots-analysis-failed-explanation`;
 *   - when there are rows, `lots-analysis-failed-list` and one `lots-analysis-failed-row-{code}-{transaction id|none}`
 *     per (code, transaction), in day order, each with `lots-analysis-failed-broker` (the name),
 *     `lots-analysis-failed-date` (`formatDay`, absent without a day), `lots-analysis-failed-message` (the catalogue
 *     message with its params) and `lots-analysis-failed-goto-{id}`, a button calling `onGotoTransaction(id)`, absent
 *     without a transaction id.
 * The fixtures follow the contract agreed with J, whose backend half lands later: each blocking issue carries
 * `transaction_date` and `fails_analysis: true` besides today's params; `related_transaction_id` may name a partner leg
 * the user cannot see and is never offered as a way in.
 *
 * The harness. As in LotCustodyModal.test.ts: the notice runs with real i18n, the real formatters and no module mocked.
 * The broker list is the `brokers` prop, as the panel passes it. Privacy is the in-memory rune: the shared
 * `$app/environment` mock reports `browser: false`, so `setPrivacyEnabled` never touches `localStorage`.
 *
 * Expectations. Broker names are the ones put in the props. A day is `formatDay(iso)` and a quantity
 * `maskableQuantity(formatExactDecimal(raw, {minFrac: 0, maxFrac: 10}))` — the backend's decimal string, exact, up to the
 * ten decimals of its column (C-97c-2: the notice cuts at the eighth until the cure, and RAW_QUANTITY reads the same at
 * both), masked under privacy by D5′ — computed here, in this runtime, by the functions the notice uses: never a frozen
 * locale string. The clear quantity is checked once against the digits put in; the
 * masked one is the formatter's own placeholder. The broker ids are long enough to be unmistakable, and are looked for
 * in each row's text with the separators a locale writes inside a number taken out, so `98,765` is caught as well as
 * `98765`. Nothing here reads translated text: the explanation and the sentences belong to the catalogue.
 *
 * Absence. Each «no …» assertion follows a presence barrier in the same mount — the row it looks into, and a sibling
 * row that does show the thing — so an absent element cannot mean an absent component.
 *
 * Red, before the cure: the file does not collect, because `./LotAnalysisFailedNotice.svelte` does not exist. Once it
 * does, «never shows a bare broker id» stays red until the catalogue texts stop printing `{broker_id}` (today
 * «… (broker {broker_id})»): that rewrite is part of the cure.
 *
 * C-97c-2 (the last block): a missing quantity keeps the ten decimals of its column, where the notice cuts it at the
 * eighth. Red until that cure.
 */
import {afterEach, beforeAll, describe, expect, it, vi, type Mock} from 'vitest';
import {flushSync, tick} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {formatDay} from '$lib/utils/core/formatAxisDate';
import {formatExactDecimal} from '$lib/utils/core/formatFixed';
import {maskableQuantity, PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import LotAnalysisFailedNotice from './LotAnalysisFailedNotice.svelte';

type Params = NonNullable<DataQualityIssue['message_params']>;

/** The catalogue key the backend sends with each blocking code (`_message_key_for_issue`). */
const MESSAGE_KEY = {
    FIFO_SOURCE_QUANTITY_MISSING: 'dataQuality.fifoSourceQuantityMissing',
    SHORT_ADJUSTMENT_NOT_SUPPORTED: 'dataQuality.shortAdjustmentNotSupported',
    TRANSFER_PAIR_MISSING: 'dataQuality.transferPairMissing',
} as const;

type BlockingCode = keyof typeof MESSAGE_KEY;

/** The panel's broker list, as the `brokers` prop carries it. */
const ALFA = {id: 98765, name: 'Broker Alfa'} satisfies BrokerLike;
const BETA = {id: 98766, name: 'Broker Beta'} satisfies BrokerLike;
const BROKERS: ReadonlyArray<BrokerLike> = [ALFA, BETA];

/**
 * A blocking issue as J's half of J-12 serialises it: today's params — `transaction_id`, `broker_id`,
 * `related_transaction_id`, `lot_id` null, engine params — plus `transaction_date` and `fails_analysis: true`. What
 * `params` leaves out of `transaction_date` and the engine params is absent.
 */
function blocking(code: BlockingCode, params: Params): DataQualityIssue {
    return {domain: 'PORTFOLIO', code, severity: 'error', message_i18n_key: MESSAGE_KEY[code], message_params: {transaction_id: null, broker_id: null, related_transaction_id: null, lot_id: null, ...params, fails_analysis: true}};
}

/** Tx 4242 at Broker Alfa, 5 March 2026: a sale 4 units beyond what the broker holds. The later of the pair. */
const SHORTFALL = blocking('FIFO_SOURCE_QUANTITY_MISSING', {transaction_id: 4242, broker_id: ALFA.id, transaction_date: '2026-03-05', missing_quantity: '4.000000'});

/** Tx 4243 at Broker Beta, 1 February 2026: an adjustment that would touch a short position. The earlier, so the first row. */
const SHORT_ADJUSTMENT = blocking('SHORT_ADJUSTMENT_NOT_SUPPORTED', {transaction_id: 4243, broker_id: BETA.id, transaction_date: '2026-02-01', missing_quantity: '2.500000'});

/** A quantity whose formatting shows: four integer digits to group, trailing zeros to drop. */
const RAW_QUANTITY = '1234.56780000';

/** Tx 4244 at Broker Alfa, 9 March 2026, short by RAW_QUANTITY: the row whose quantity is read. */
const BIG_SHORTFALL = blocking('FIFO_SOURCE_QUANTITY_MISSING', {transaction_id: 4244, broker_id: ALFA.id, transaction_date: '2026-03-09', missing_quantity: RAW_QUANTITY});

const ROW_PREFIX = 'lots-analysis-failed-row-';

/** RAW_QUANTITY as the notice must write it with privacy off; set once in `beforeAll`. */
let clearQuantity = '';

/** A row's test id: `lots-analysis-failed-row-{code}-{transaction id | none}`. */
function rowId(code: BlockingCode, transactionId: number | 'none'): string {
    return `${ROW_PREFIX}${code}-${transactionId}`;
}

/** Mount the notice on `issues`, with the panel's broker list and a spy as the way to a transaction. */
function mountNotice(issues: DataQualityIssue[]): {notice: HTMLElement; onGotoTransaction: Mock<(transactionId: number) => void>} {
    const onGotoTransaction = vi.fn<(transactionId: number) => void>();
    render(LotAnalysisFailedNotice, {issues, brokers: BROKERS, onGotoTransaction});
    return {notice: screen.getByTestId('lots-analysis-panel-failed'), onGotoTransaction};
}

/** The test ids of the notice's rows, in document order: the order the user reads them. */
function rowIdsIn(notice: HTMLElement): (string | null)[] {
    const list = within(notice).getByTestId('lots-analysis-failed-list');
    return within(list)
        .getAllByTestId(new RegExp(`^${ROW_PREFIX}`))
        .map((row) => row.getAttribute('data-testid'));
}

/** The message of the row `id`. */
function messageOf(notice: HTMLElement, id: string): HTMLElement {
    return within(within(notice).getByTestId(id)).getByTestId('lots-analysis-failed-message');
}

/** The text an element shows. */
function shown(element: HTMLElement): string {
    return (element.textContent ?? '').trim();
}

/** An element's text with the separators a locale may write inside a number taken out: `98,765`, `98 765` read `98765`. */
function ungrouped(element: HTMLElement): string {
    return (element.textContent ?? '').replace(/[\s.,'’\u00a0\u202f]/g, '');
}

/** A quantity as the notice must write it: the backend's decimal string, exact, up to the ten decimals of its column (C-97c-2), masked under privacy (D5′). */
function quantity(raw: string): string {
    return maskableQuantity(formatExactDecimal(raw, {minFrac: 0, maxFrac: 10}));
}

/** Set the privacy flag, then flush: synchronously, and once more through the microtask the app itself waits on. */
async function setPrivacy(value: boolean): Promise<void> {
    setPrivacyEnabled(value);
    flushSync();
    await tick();
}

beforeAll(async () => {
    await setupI18n();
    setPrivacyEnabled(false);
    clearQuantity = quantity(RAW_QUANTITY);
    // The expected quantity is the formatter's own output: check once that it carries the digits put in, or «the message
    // shows the quantity» would compare the placeholder with itself.
    expect(clearQuantity.replace(/\D/g, ''), 'control: the clear quantity carries the digits put in').toBe('12345678');
    expect(clearQuantity, 'control: the formatting shows — grouping, trailing zeros dropped').not.toBe(RAW_QUANTITY);
});

afterEach(() => {
    // Module-level flag: a leftover `true` would mount the next notice masked.
    setPrivacyEnabled(false);
    cleanup();
});

describe('LotAnalysisFailedNotice — what failed, where, and the transaction to fix (J-12)', () => {
    it('lists one row per blocking issue in day order, each with its broker’s name, its day and a button to its transaction', () => {
        const {notice} = mountNotice([SHORTFALL, SHORT_ADJUSTMENT]);

        expect(notice, 'an alert: the analysis did not come out').toHaveAttribute('role', 'alert');
        expect(within(notice).getByTestId('lots-analysis-failed-explanation')).toBeInTheDocument();
        expect(rowIdsIn(notice), 'one row per blocking issue, 1 February before 5 March, although sent the other way round').toEqual([rowId('SHORT_ADJUSTMENT_NOT_SUPPORTED', 4243), rowId('FIFO_SOURCE_QUANTITY_MISSING', 4242)]);

        const expectedRows = [
            {id: rowId('SHORT_ADJUSTMENT_NOT_SUPPORTED', 4243), broker: BETA, day: '2026-02-01', transactionId: 4243},
            {id: rowId('FIFO_SOURCE_QUANTITY_MISSING', 4242), broker: ALFA, day: '2026-03-05', transactionId: 4242},
        ];
        for (const {id, broker, day, transactionId} of expectedRows) {
            const row = within(notice).getByTestId(id);
            expect(shown(within(row).getByTestId('lots-analysis-failed-broker')), `${id}: the broker, by its name`).toBe(broker.name);
            expect(formatDay(day), 'control: a formatted day is not the ISO string').not.toBe(day);
            expect(shown(within(row).getByTestId('lots-analysis-failed-date')), `${id}: the day of its transaction`).toBe(formatDay(day));
            expect(within(row).getByTestId('lots-analysis-failed-message'), `${id}: its message`).toBeInTheDocument();
            expect(within(row).getByTestId(`lots-analysis-failed-goto-${transactionId}`).tagName, `${id}: a button to its own transaction`).toBe('BUTTON');
        }
    });

    // Red until the catalogue rewrite: today's texts end in «(broker {broker_id})», so each row prints 98765 or 98766.
    it('never shows a bare broker id in a row: the user reads the broker’s name', () => {
        const {notice} = mountNotice([SHORTFALL, SHORT_ADJUSTMENT]);

        for (const {id, issue} of [
            {id: rowId('SHORT_ADJUSTMENT_NOT_SUPPORTED', 4243), issue: SHORT_ADJUSTMENT},
            {id: rowId('FIFO_SOURCE_QUANTITY_MISSING', 4242), issue: SHORTFALL},
        ]) {
            const row = within(notice).getByTestId(id);
            const message = shown(within(row).getByTestId('lots-analysis-failed-message'));
            // Barriers: an empty message, or a key the catalogue did not resolve, would let the check below pass on nothing.
            expect(message, `${id}: barrier — the message is written`).not.toBe('');
            expect(message, `${id}: barrier — the catalogue resolved its key`).not.toBe(issue.message_i18n_key);
            for (const brokerId of [ALFA.id, BETA.id]) {
                expect(ungrouped(row), `${id}: the row’s text shows no broker id ${brokerId}`).not.toContain(String(brokerId));
            }
        }
    });

    it('a row’s button calls onGotoTransaction once, with that row’s transaction id', async () => {
        const {notice, onGotoTransaction} = mountNotice([SHORTFALL, SHORT_ADJUSTMENT]);
        const row = within(notice).getByTestId(rowId('FIFO_SOURCE_QUANTITY_MISSING', 4242));

        await fireEvent.click(within(row).getByTestId('lots-analysis-failed-goto-4242'));

        expect(onGotoTransaction, 'one click, one call').toHaveBeenCalledTimes(1);
        expect(onGotoTransaction, 'with the transaction of that row').toHaveBeenCalledWith(4242);
    });

    it('writes the missing quantity as the lots write a quantity, not as the backend sent it', () => {
        const {notice} = mountNotice([BIG_SHORTFALL]);

        const message = shown(messageOf(notice, rowId('FIFO_SOURCE_QUANTITY_MISSING', 4244)));

        expect(message, 'the quantity, written by the lots’ formatter in this runtime').toContain(clearQuantity);
        expect(message, 'not the decimal string as sent').not.toContain(RAW_QUANTITY);
    });

    // Why: a component that formats once at mount looks right and never follows the toggle (R20): only a toggle in
    // place, both ways, tells it apart from one that tracks the flag.
    it('masks the quantity when privacy turns on, and shows it again when privacy turns off, in place (D5′)', async () => {
        const {notice} = mountNotice([BIG_SHORTFALL]);
        const message = () => shown(messageOf(notice, rowId('FIFO_SOURCE_QUANTITY_MISSING', 4244)));
        expect(message(), 'mounted with privacy off: the quantity in the clear').toContain(clearQuantity);

        await setPrivacy(true);
        expect(isPrivacyEnabled(), 'control: the flag').toBe(true);
        expect(quantity(RAW_QUANTITY), 'control: a fresh formatter call masks').toBe(PRIVACY_PLACEHOLDER);
        expect(message(), 'privacy on: the placeholder').toContain(PRIVACY_PLACEHOLDER);
        expect(message(), 'privacy on: not the quantity').not.toContain(clearQuantity);

        await setPrivacy(false);
        expect(isPrivacyEnabled(), 'control: the flag').toBe(false);
        expect(message(), 'privacy off again: the quantity is back').toContain(clearQuantity);
        expect(message(), 'privacy off again: no placeholder left').not.toContain(PRIVACY_PLACEHOLDER);
    });

    it('mounted with privacy on, masks the quantity from the first paint', async () => {
        await setPrivacy(true);
        expect(isPrivacyEnabled(), 'control: the flag').toBe(true);

        const {notice} = mountNotice([BIG_SHORTFALL]);
        const message = shown(messageOf(notice, rowId('FIFO_SOURCE_QUANTITY_MISSING', 4244)));

        expect(message, 'the placeholder').toContain(PRIVACY_PLACEHOLDER);
        expect(message, 'not the quantity').not.toContain(clearQuantity);
    });

    it('shows a repeated (code, transaction) once', () => {
        const repeat = blocking('FIFO_SOURCE_QUANTITY_MISSING', {transaction_id: 4242, broker_id: ALFA.id, transaction_date: '2026-03-05', missing_quantity: '4.000000'});

        const {notice} = mountNotice([SHORTFALL, repeat]);

        expect(rowIdsIn(notice), 'one row for the two copies').toEqual([rowId('FIFO_SOURCE_QUANTITY_MISSING', 4242)]);
        expect(within(notice).getAllByTestId('lots-analysis-failed-goto-4242'), 'one button to the transaction').toHaveLength(1);
    });

    // Why: related_transaction_id may name a partner leg the user cannot see; only transaction_id is ever a way in.
    it('offers no button without a transaction id, and never one to the related leg', () => {
        const untraced = blocking('TRANSFER_PAIR_MISSING', {transaction_id: null, broker_id: ALFA.id, related_transaction_id: 55, transaction_date: null});
        const traced = blocking('TRANSFER_PAIR_MISSING', {transaction_id: 4250, broker_id: BETA.id, related_transaction_id: 56, transaction_date: '2026-04-10'});

        const {notice} = mountNotice([untraced, traced]);

        // Barriers: the sibling row draws its button; the untraced row is there, with its broker and its message.
        const tracedRow = within(notice).getByTestId(rowId('TRANSFER_PAIR_MISSING', 4250));
        expect(within(tracedRow).getByTestId('lots-analysis-failed-goto-4250'), 'barrier: a row with a transaction has its button').toBeInTheDocument();
        const untracedRow = within(notice).getByTestId(rowId('TRANSFER_PAIR_MISSING', 'none'));
        expect(shown(within(untracedRow).getByTestId('lots-analysis-failed-broker')), 'barrier: the untraced row names its broker').toBe(ALFA.name);
        expect(within(untracedRow).getByTestId('lots-analysis-failed-message'), 'barrier: the untraced row has its message').toBeInTheDocument();

        expect(within(untracedRow).queryAllByTestId(/^lots-analysis-failed-goto-/), 'no transaction id, no button').toEqual([]);
        expect(screen.queryByTestId('lots-analysis-failed-goto-55'), 'the related leg of the untraced issue is offered nowhere').toBeNull();
        expect(screen.queryByTestId('lots-analysis-failed-goto-56'), 'nor the related leg of the traced one').toBeNull();
    });

    it('leaves the day out of a row whose issue carries none, and puts that row after the dated ones', () => {
        const undated = blocking('FIFO_SOURCE_QUANTITY_MISSING', {transaction_id: 4260, broker_id: ALFA.id, missing_quantity: '1.000000'});

        const {notice} = mountNotice([undated, SHORT_ADJUSTMENT]);

        expect(rowIdsIn(notice), 'the dated row first, the undated one last').toEqual([rowId('SHORT_ADJUSTMENT_NOT_SUPPORTED', 4243), rowId('FIFO_SOURCE_QUANTITY_MISSING', 4260)]);
        // Barriers: the sibling row shows its day; the undated row is there, with its broker and its button.
        const datedRow = within(notice).getByTestId(rowId('SHORT_ADJUSTMENT_NOT_SUPPORTED', 4243));
        expect(shown(within(datedRow).getByTestId('lots-analysis-failed-date')), 'barrier: a dated row shows its day').toBe(formatDay('2026-02-01'));
        const undatedRow = within(notice).getByTestId(rowId('FIFO_SOURCE_QUANTITY_MISSING', 4260));
        expect(shown(within(undatedRow).getByTestId('lots-analysis-failed-broker')), 'barrier: the undated row names its broker').toBe(ALFA.name);
        expect(within(undatedRow).getByTestId('lots-analysis-failed-goto-4260'), 'barrier: the undated row has its button').toBeInTheDocument();

        expect(within(undatedRow).queryByTestId('lots-analysis-failed-date'), 'no day sent, no day drawn').toBeNull();
    });

    it('with no blocking issue still explains the failure, and draws no list', () => {
        const {notice} = mountNotice([]);

        expect(notice, 'barrier: the notice is there, as an alert').toHaveAttribute('role', 'alert');
        expect(within(notice).getByTestId('lots-analysis-failed-explanation'), 'the explanation').toBeInTheDocument();
        expect(screen.queryByTestId('lots-analysis-failed-list'), 'nothing to list').toBeNull();
        expect(screen.queryAllByTestId(new RegExp(`^${ROW_PREFIX}`)), 'no row').toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// C-97c-2 — a missing quantity keeps every decimal of its column
// ---------------------------------------------------------------------------

/**
 * D-C97c-1 (the coordinator, 17/10), applied to the lots (BK). The notice writes `missing_quantity`, the backend's decimal
 * string, with `formatExactDecimal(raw, {maxFrac: 8})`, so 0.1234567891 reads 0.12345678. A lot quantity keeps ten
 * decimals; the contract: `maxFrac: 10`. Red today. The cases above stay green before and after the cure: RAW_QUANTITY,
 * 1234.5678 once its trailing zeros go, reaches no cut at the eighth decimal nor at the tenth.
 *
 * The expected text is `quantity()`'s — the contract's formatter, in this runtime — checked once against the ten decimals
 * put in, and matched as a whole number token in the message: no digit, decimal mark or separator glued to either side.
 */
describe('LotAnalysisFailedNotice — a missing quantity keeps every decimal of its column, up to ten (C-97c-2)', () => {
    /** Ten decimals, as a lot quantity keeps them. */
    const TEN_DECIMAL_QUANTITY = '0.1234567891';

    /** Tx 4270 at Broker Alfa, 12 March 2026, a sale TEN_DECIMAL_QUANTITY beyond what the broker holds. */
    const TEN_DECIMAL_SHORTFALL = blocking('FIFO_SOURCE_QUANTITY_MISSING', {transaction_id: 4270, broker_id: ALFA.id, transaction_date: '2026-03-12', missing_quantity: TEN_DECIMAL_QUANTITY});

    /** `text` as a whole number in a longer text: no digit, decimal mark or group separator glued to either side. */
    function numberToken(text: string): RegExp {
        return new RegExp(`(?<![\\d.,])${text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![.,]?\\d)`);
    }

    it('writes a missing quantity of 0.1234567891 whole: the ten decimals of its column, not eight', () => {
        const expected = quantity(TEN_DECIMAL_QUANTITY);
        expect(expected.replace(/\D/g, ''), 'control: the expected text keeps the ten decimals put in').toBe('01234567891');

        const {notice} = mountNotice([TEN_DECIMAL_SHORTFALL]);
        const message = shown(messageOf(notice, rowId('FIFO_SOURCE_QUANTITY_MISSING', 4270)));

        expect(message, 'the ten decimals (today cut at the eighth: 0.12345678)').toMatch(numberToken(expected));
    });
});
