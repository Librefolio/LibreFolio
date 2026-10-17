/**
 * @vitest-environment node
 *
 * Branch-exhaustive unit tests for the pure helpers extracted from
 * LotDataQualityBanner.svelte: lot-id resolution, overall severity, and the
 * grouping/dedup/disambiguation pipeline. i18n is injected as a plain
 * `labelForDate` echo so labels are asserted deterministically, no runtime.
 *
 * The last block (J-12) pins the two helpers of a FAILED analysis — the issue
 * partition and the failure rows; its notes are beside it.
 */
import {describe, it, expect, vi} from 'vitest';
import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {resolveLotId, groupedSeverity, buildIssueGroups, partitionLotIssues, buildFailureRows, type FailureRow, type IssueSeverity} from './lotDataQualityHelpers';
import {resolveBrokerName} from './lotChartShared';

interface RawIssue {
    code: string;
    severity: IssueSeverity;
    message_i18n_key: string;
    message_params?: Record<string, string | number | boolean | null | undefined>;
}

/** Build an issue; pass `lotId === undefined` with `withParams=false` to omit message_params entirely. */
function issue(code: string, severity: IssueSeverity, lotId?: number, opts: {key?: string; withParams?: boolean; extra?: Record<string, string | number>} = {}): RawIssue {
    const {key = 'msg.' + code, withParams = true, extra = {}} = opts;
    if (!withParams) return {code, severity, message_i18n_key: key};
    return {code, severity, message_i18n_key: key, message_params: {...(lotId === undefined ? {} : {lot_id: lotId}), ...extra}};
}

/** Echo the ISO back so chip labels are deterministic and locale-free. */
const echo = (iso: string) => iso;

describe('resolveLotId', () => {
    it('passes a number through (outer ternary true)', () => {
        expect(resolveLotId(42)).toBe(42);
    });

    it('parses a numeric string (outer false, inner true)', () => {
        expect(resolveLotId('17')).toBe(17);
    });

    it('yields NaN for a non-numeric string (inner true, Number → NaN)', () => {
        expect(resolveLotId('abc')).toBeNaN();
    });

    it('yields NaN for a non-number/non-string (both ternaries false)', () => {
        expect(resolveLotId(undefined)).toBeNaN();
        expect(resolveLotId(null)).toBeNaN();
        expect(resolveLotId(true)).toBeNaN();
        expect(resolveLotId({})).toBeNaN();
    });
});

describe('groupedSeverity', () => {
    it('is error when any error group exists (first if true)', () => {
        expect(groupedSeverity(2, 5)).toBe('error');
    });

    it('is warning when there are no errors but some warnings (first false, second true)', () => {
        expect(groupedSeverity(0, 3)).toBe('warning');
    });

    it('is info when there are neither errors nor warnings (both if false)', () => {
        expect(groupedSeverity(0, 0)).toBe('info');
    });
});

describe('buildIssueGroups', () => {
    it('returns an empty array for no issues', () => {
        expect(buildIssueGroups([], new Map(), echo)).toEqual([]);
    });

    it('builds one group with one labelled chip for a resolvable in-range lot', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 10)], new Map([[10, '2024-03-15']]), echo);
        expect(groups).toHaveLength(1);
        expect(groups[0]).toMatchObject({code: 'REF', severity: 'warning', messageKey: 'msg.REF'});
        expect(groups[0].lots).toEqual([{lotId: 10, label: '2024-03-15'}]);
    });

    it('preserves message params and key on the group', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 10, {extra: {foo: 'bar'}})], new Map([[10, 'd']]), echo);
        expect(groups[0].messageParams).toEqual({lot_id: 10, foo: 'bar'});
    });

    it('defaults messageParams to {} when the issue has none (?? {} right arm)', () => {
        const groups = buildIssueGroups([issue('REF', 'info', undefined, {withParams: false})], new Map(), echo);
        expect(groups[0].messageParams).toEqual({});
        expect(groups[0].lots).toEqual([]);
    });

    it('dedups repeated per-lot issues of the same code into one group (existing-group branch)', () => {
        const groups = buildIssueGroups(
            [issue('REF', 'warning', 10), issue('REF', 'warning', 11)],
            new Map([
                [10, '2024-01-02'],
                [11, '2024-01-01'],
            ]),
            echo,
        );
        expect(groups).toHaveLength(1);
        // Ordered by opening date ascending → lot 11 (Jan 1) before lot 10 (Jan 2), distinct dates ⇒ no #index.
        expect(groups[0].lots).toEqual([
            {lotId: 11, label: '2024-01-01'},
            {lotId: 10, label: '2024-01-02'},
        ]);
    });

    it('skips a lot_id that is not in the visible-date map (has() false branch), keeping the group', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 999)], new Map([[10, 'd']]), echo);
        expect(groups[0].lots).toEqual([]);
    });

    it('skips a NaN lot_id (isFinite false branch)', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', undefined, {extra: {lot_id: 'not-a-number'}})], new Map([[10, 'd']]), echo);
        expect(groups[0].lots).toEqual([]);
    });

    it('does not add the same lot twice within a group (includes true branch)', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 10), issue('REF', 'warning', 10)], new Map([[10, 'd']]), echo);
        expect(groups[0].lots).toEqual([{lotId: 10, label: 'd'}]);
    });

    it('suffixes lots sharing an opening day with #index in id order (total > 1 branch + id tie-break)', () => {
        const groups = buildIssueGroups(
            [issue('REF', 'warning', 11), issue('REF', 'warning', 10)],
            new Map([
                [10, '2024-05-01'],
                [11, '2024-05-01'],
            ]),
            echo,
        );
        // Same date ⇒ sorted by id (10 then 11), each gets a #index.
        expect(groups[0].lots).toEqual([
            {lotId: 10, label: '2024-05-01 #1'},
            {lotId: 11, label: '2024-05-01 #2'},
        ]);
    });

    it('orders groups by severity: error, then warning, then info', () => {
        const groups = buildIssueGroups([issue('I', 'info'), issue('E', 'error'), issue('W', 'warning')], new Map(), echo);
        expect(groups.map((g) => g.code)).toEqual(['E', 'W', 'I']);
    });
});

/**
 * J-12, panel half — a FAILED analysis names what failed, where, and the row to fix (workstream Y).
 *
 * The contract. `POST /portfolio/lots/analysis` answers `calculation_status: FAILED` when the FIFO replay of the
 * quantities fails (backend `_QUANTITATIVE_FAILURE_CODES`: SHORT_TRANSFER_NOT_SUPPORTED, SHORT_ADJUSTMENT_NOT_SUPPORTED,
 * FIFO_SOURCE_QUANTITY_MISSING, TRANSFER_PAIR_MISSING). Agreed with J, owner of the backend half, which lands later — so
 * the fixtures below follow the agreement, not today's backend: every issue that makes the analysis FAILED carries,
 * besides today's `transaction_id`, `broker_id`, `related_transaction_id`, `lot_id` (null) and engine params such as
 * `missing_quantity` (a decimal string), two new params: `transaction_date` (the ISO day of the row `transaction_id`)
 * and `fails_analysis: true`. No other issue carries the flag. `transaction_id` is a row the user can open;
 * `related_transaction_id` may name a partner leg the user cannot see, so it is never offered as a link.
 *
 * Two pure helpers carry the decision, with no i18n and no store:
 * - `partitionLotIssues(issues, failed)` sends the issues to the failure notice or to the banner, on the flag alone
 *   (strictly `true`) and only when the analysis FAILED, each list in input order;
 * - `buildFailureRows(issues, brokers, formatQuantity)` turns the blocking issues into one row per (code, transaction):
 *   the transaction id read from `transaction_id` only, the ISO day or nothing, the broker's NAME from the panel's
 *   broker list (`resolveBrokerName` with its defaults), the message params with `missing_quantity`, and only it,
 *   written by the injected quantity formatter; de-duplicated (first occurrence wins) and ordered by day, then
 *   transaction id, then code.
 *
 * Fixtures. Issues are built as the client receives them (`DataQualityIssue`, domain included). The quantity formatter
 * is a stub whose output names its input, so a formatted param is recognisable and no locale enters this file.
 *
 * Red, before the cure: every test of this block fails with «… is not a function» — neither export exists yet. The
 * tests above it are untouched and stay green.
 */

/** A data-quality issue as the lots analysis serialises it: `DataQualityIssue`, with its domain. */
interface WireIssue extends RawIssue {
    domain: string;
}

type Param = string | number | boolean | null | undefined;

/** Marks a param to leave out of an issue altogether, as opposed to sending it null. */
const ABSENT = Symbol('absent');

/** The catalogue key the backend sends with each code (`_message_key_for_issue`). */
const MESSAGE_KEY: Record<string, string> = {
    FIFO_SOURCE_QUANTITY_MISSING: 'dataQuality.fifoSourceQuantityMissing',
    SHORT_ADJUSTMENT_NOT_SUPPORTED: 'dataQuality.shortAdjustmentNotSupported',
    SHORT_TRANSFER_NOT_SUPPORTED: 'dataQuality.shortTransferNotSupported',
    TRANSFER_PAIR_MISSING: 'dataQuality.transferPairMissing',
    REFERENCE_PRICE_FALLBACK: 'dataQuality.referencePriceFallback',
    CURRENT_PRICE_ASSUMED_AT_COST: 'dataQuality.currentPriceAssumedAtCost',
};

// The four codes that fail the replay (backend `_QUANTITATIVE_FAILURE_CODES`).
const SOURCE_MISSING = 'FIFO_SOURCE_QUANTITY_MISSING';
const SHORT_ADJUSTMENT = 'SHORT_ADJUSTMENT_NOT_SUPPORTED';
const SHORT_TRANSFER = 'SHORT_TRANSFER_NOT_SUPPORTED';
const PAIR_MISSING = 'TRANSFER_PAIR_MISSING';

/**
 * A blocking issue as J's half serialises it: `lot_id` null, `related_transaction_id` null unless given, and
 * `fails_analysis: true`. `params` carries the rest — `transaction_id`, `broker_id`, `transaction_date`, engine params —
 * and what it leaves out is absent.
 */
function blockingIssue(code: string, params: Record<string, Param>): WireIssue {
    return {domain: 'PORTFOLIO', code, severity: 'error', message_i18n_key: MESSAGE_KEY[code], message_params: {lot_id: null, related_transaction_id: null, ...params, fails_analysis: true}};
}

/** A lot issue that does not fail the analysis, as today: no `fails_analysis`. */
function bannerIssue(code: string, severity: IssueSeverity, params: Record<string, Param>): WireIssue {
    return {domain: 'PORTFOLIO', code, severity, message_i18n_key: MESSAGE_KEY[code], message_params: {transaction_id: null, broker_id: null, related_transaction_id: null, ...params}};
}

/** A copy of `issue` with the param `key` set to `value`, or left out when `value` is ABSENT. */
function withParam(issue: WireIssue, key: string, value: Param | typeof ABSENT): WireIssue {
    const params: Record<string, Param> = {...issue.message_params};
    if (value === ABSENT) delete params[key];
    else params[key] = value;
    return {...issue, message_params: params};
}

/** The panel's broker list (`BrokerLike`): two named brokers and one known by id only. */
const ALFA: BrokerLike = {id: 98765, name: 'Broker Alfa'};
const BETA: BrokerLike = {id: 98766, name: 'Broker Beta'};
const NAMELESS: BrokerLike = {id: 98767};
const BROKERS: ReadonlyArray<BrokerLike> = [ALFA, BETA, NAMELESS];

/** A quantity formatter whose output names its input. */
const markQuantity = (raw: unknown): string => `qty(${String(raw)})`;

/** The keys of the rows built from `issues`, in the order the notice draws them. */
function rowKeys(issues: readonly WireIssue[]): string[] {
    return buildFailureRows(issues, BROKERS, markQuantity).map((row) => row.key);
}

/** `transaction_id` as it may arrive, and the id the row must read from it: a positive safe integer, or null. */
const TRANSACTION_ID_CASES: ReadonlyArray<{name: string; raw: Param | typeof ABSENT; expected: number | null}> = [
    {name: 'a positive integer', raw: 4242, expected: 4242},
    {name: 'a digit string', raw: '4242', expected: 4242},
    {name: 'zero', raw: 0, expected: null},
    {name: 'a negative integer', raw: -7, expected: null},
    {name: 'a negative number as a string', raw: '-7', expected: null},
    {name: 'a fraction', raw: 42.5, expected: null},
    {name: 'a fraction as a string', raw: '42.5', expected: null},
    {name: 'NaN', raw: Number.NaN, expected: null},
    {name: 'Infinity', raw: Number.POSITIVE_INFINITY, expected: null},
    {name: 'an integer beyond the safe range', raw: 2 ** 53, expected: null},
    {name: 'a digit string beyond the safe range', raw: '9007199254740993', expected: null},
    {name: 'a non-numeric string', raw: 'abc', expected: null},
    {name: 'an empty string', raw: '', expected: null},
    {name: 'a boolean', raw: true, expected: null},
    {name: 'null', raw: null, expected: null},
    {name: 'absent', raw: ABSENT, expected: null},
];

/** `transaction_date` as it may arrive, and the day the row keeps: a bare `YYYY-MM-DD` as sent, or null. */
const TRANSACTION_DATE_CASES: ReadonlyArray<{name: string; raw: Param | typeof ABSENT; expected: string | null}> = [
    {name: 'an ISO day', raw: '2026-03-05', expected: '2026-03-05'},
    {name: 'a day without zero padding', raw: '2026-3-5', expected: null},
    {name: 'a timestamp', raw: '2026-03-05T10:00:00Z', expected: null},
    {name: 'a day in another order', raw: '05/03/2026', expected: null},
    {name: 'free text', raw: 'yesterday', expected: null},
    {name: 'an empty string', raw: '', expected: null},
    {name: 'a number', raw: 20260305, expected: null},
    {name: 'null', raw: null, expected: null},
    {name: 'absent', raw: ABSENT, expected: null},
];

/** `broker_id` as it may arrive, the id it parses to (as the transaction id does), and the name the row shows. */
const BROKER_CASES: ReadonlyArray<{name: string; raw: Param | typeof ABSENT; parsed: number | null; expected: string}> = [
    {name: 'a broker of the list', raw: ALFA.id, parsed: ALFA.id, expected: 'Broker Alfa'},
    {name: 'a digit string', raw: String(BETA.id), parsed: BETA.id, expected: 'Broker Beta'},
    {name: 'an id not in the list', raw: 31337, parsed: 31337, expected: '#31337'},
    {name: 'a broker of the list without a name', raw: NAMELESS.id, parsed: NAMELESS.id, expected: '#98767'},
    {name: 'null', raw: null, parsed: null, expected: '—'},
    {name: 'absent', raw: ABSENT, parsed: null, expected: '—'},
    {name: 'a non-numeric string', raw: 'abc', parsed: null, expected: '—'},
];

describe('J-12 — a FAILED lots analysis: partitionLotIssues and buildFailureRows', () => {
    describe('partitionLotIssues', () => {
        const shortfall = blockingIssue(SOURCE_MISSING, {transaction_id: 4242, broker_id: ALFA.id, transaction_date: '2026-03-05', missing_quantity: '4.000000'});
        const unpaired = blockingIssue(PAIR_MISSING, {transaction_id: 4250, broker_id: BETA.id, related_transaction_id: 55, transaction_date: '2026-04-10'});
        const fallback = bannerIssue('REFERENCE_PRICE_FALLBACK', 'warning', {lot_id: 10, reference_price: '12.50'});
        const atCost = bannerIssue('CURRENT_PRICE_ASSUMED_AT_COST', 'info', {lot_id: 11});

        // Why: on FAILED the notice lists what broke the replay and the banner keeps the rest, nothing shown twice; the
        // banner's groups take their params from the first issue of a code, so its input order is kept.
        it('FAILED: the issues flagged fails_analysis go to the failure, every other one to the banner, both in input order', () => {
            const issues = [fallback, shortfall, atCost, unpaired];
            const before = [...issues];

            expect(partitionLotIssues(issues, true)).toEqual({failure: [shortfall, unpaired], banner: [fallback, atCost]});
            expect(issues, 'the list read is left as it was').toEqual(before);
        });

        // Why: the backend decides what fails the analysis; the frontend keeps no copy of its code list.
        it('FAILED: the flag decides, not the code — a blocking code without the flag stays in the banner', () => {
            const unflagged = withParam(shortfall, 'fails_analysis', ABSENT);

            expect(partitionLotIssues([unflagged, unpaired], true)).toEqual({failure: [unpaired], banner: [unflagged]});
        });

        // Why: only the boolean `true` of the contract blocks; a lookalike is not the contract.
        it.each([
            {name: 'the string "true"', value: 'true'},
            {name: 'the number 1', value: 1},
            {name: 'false', value: false},
            {name: 'null', value: null},
        ])('FAILED: fails_analysis as $name does not block — the issue stays in the banner', ({value}) => {
            const lookalike = withParam(shortfall, 'fails_analysis', value);

            expect(partitionLotIssues([lookalike], true)).toEqual({failure: [], banner: [lookalike]});
        });

        it('FAILED: an issue without message_params stays in the banner', () => {
            const bare: WireIssue = {domain: 'PORTFOLIO', code: 'CURRENT_PRICE_ASSUMED_AT_COST', severity: 'info', message_i18n_key: MESSAGE_KEY.CURRENT_PRICE_ASSUMED_AT_COST};

            expect(partitionLotIssues([bare], true)).toEqual({failure: [], banner: [bare]});
        });

        // Why: COMPLETE and DEGRADED draw the analysis; with no failure to explain, nothing leaves the banner.
        it('not FAILED: every issue goes to the banner, flagged ones included, and the failure is empty', () => {
            expect(partitionLotIssues([fallback, shortfall, unpaired], false)).toEqual({failure: [], banner: [fallback, shortfall, unpaired]});
        });

        it('no issues: two empty lists, FAILED or not', () => {
            expect(partitionLotIssues([], true)).toEqual({failure: [], banner: []});
            expect(partitionLotIssues([], false)).toEqual({failure: [], banner: []});
        });
    });

    describe('buildFailureRows', () => {
        const shortfall = blockingIssue(SOURCE_MISSING, {transaction_id: 4242, broker_id: ALFA.id, transaction_date: '2026-03-05', missing_quantity: '4.000000'});

        // Why: the row the notice draws, field by field — the FailureRow agreed for the cure, and nothing else.
        it('maps a blocking issue to its row: key, code, transaction, day, broker name, message key and params', () => {
            const expected: FailureRow = {
                key: 'FIFO_SOURCE_QUANTITY_MISSING:4242',
                code: SOURCE_MISSING,
                transactionId: 4242,
                transactionDate: '2026-03-05',
                brokerName: 'Broker Alfa',
                messageKey: 'dataQuality.fifoSourceQuantityMissing',
                messageParams: {...shortfall.message_params, missing_quantity: 'qty(4.000000)'},
            };

            expect(buildFailureRows([shortfall], BROKERS, markQuantity)).toEqual([expected]);
        });

        it('no issues, no rows', () => {
            expect(buildFailureRows([], BROKERS, markQuantity)).toEqual([]);
        });

        describe('the transaction', () => {
            // Why: the id becomes the way to /transactions?highlight=<id>; anything but a real row id must give no way.
            it.each(TRANSACTION_ID_CASES)('transaction_id as $name → $expected, and the key follows it', ({raw, expected}) => {
                const issue = withParam(blockingIssue(SOURCE_MISSING, {broker_id: ALFA.id, transaction_date: '2026-03-05'}), 'transaction_id', raw);

                const [row] = buildFailureRows([issue], BROKERS, markQuantity);

                expect(row.transactionId).toBe(expected);
                expect(row.key).toBe(`${SOURCE_MISSING}:${expected ?? 'none'}`);
            });

            // Why: related_transaction_id may name a partner leg the user cannot see; it never stands in for the row.
            it('never takes it from related_transaction_id', () => {
                const rows = buildFailureRows(
                    [
                        blockingIssue(PAIR_MISSING, {transaction_id: null, broker_id: ALFA.id, related_transaction_id: 55}),
                        blockingIssue(SHORT_TRANSFER, {broker_id: BETA.id, related_transaction_id: 56}),
                        blockingIssue(SOURCE_MISSING, {transaction_id: 4250, broker_id: BETA.id, related_transaction_id: 57, transaction_date: '2026-04-10', missing_quantity: '1.000000'}),
                    ],
                    BROKERS,
                    markQuantity,
                );

                expect(Object.fromEntries(rows.map((row) => [row.code, row.transactionId]))).toEqual({[PAIR_MISSING]: null, [SHORT_TRANSFER]: null, [SOURCE_MISSING]: 4250});
            });
        });

        describe('the day', () => {
            // Why: the notice formats the day itself (`formatDay`); a value that is not a bare day has nothing to show.
            it.each(TRANSACTION_DATE_CASES)('transaction_date as $name → $expected', ({raw, expected}) => {
                const issue = withParam(blockingIssue(SOURCE_MISSING, {transaction_id: 4242, broker_id: ALFA.id}), 'transaction_date', raw);

                expect(buildFailureRows([issue], BROKERS, markQuantity)[0].transactionDate).toBe(expected);
            });
        });

        describe('the broker', () => {
            // Why: the user reads a name, never «(broker 7)»; resolveBrokerName's own defaults cover what has none.
            it.each(BROKER_CASES)('broker_id as $name → $expected', ({raw, parsed, expected}) => {
                expect(resolveBrokerName(parsed, BROKERS), 'control: resolveBrokerName’s own answer for that id').toBe(expected);
                const issue = withParam(blockingIssue(SOURCE_MISSING, {transaction_id: 4242, transaction_date: '2026-03-05'}), 'broker_id', raw);

                expect(buildFailureRows([issue], BROKERS, markQuantity)[0].brokerName).toBe(expected);
            });
        });

        describe('the message', () => {
            // Why: the missing quantity is the figure of a lots context, so it goes through the lots' formatter — the
            // place privacy masks it (D5′). The other params are the catalogue's business, as sent.
            it('writes missing_quantity, and only it, through formatQuantity: every other param stays as sent', () => {
                const formatQuantity = vi.fn(markQuantity);
                // `requested_quantity` is no engine param: a quantity-looking param the contract does not name.
                const issue = blockingIssue(SOURCE_MISSING, {transaction_id: 4242, broker_id: ALFA.id, transaction_date: '2026-03-05', missing_quantity: '4.000000', requested_quantity: '10.000000'});

                const [row] = buildFailureRows([issue], BROKERS, formatQuantity);

                expect(
                    formatQuantity.mock.calls.map(([raw]) => raw),
                    'one call, with the decimal string as sent',
                ).toEqual(['4.000000']);
                expect(row.messageParams).toEqual({...issue.message_params, missing_quantity: 'qty(4.000000)'});
            });

            it.each([
                {name: 'absent', value: ABSENT},
                {name: 'null', value: null},
            ] as ReadonlyArray<{name: string; value: Param | typeof ABSENT}>)('leaves a missing_quantity $name as it is, without calling formatQuantity', ({value}) => {
                const formatQuantity = vi.fn(markQuantity);
                const issue = withParam(blockingIssue(PAIR_MISSING, {transaction_id: 4250, broker_id: BETA.id, related_transaction_id: 55, transaction_date: '2026-04-10'}), 'missing_quantity', value);

                const [row] = buildFailureRows([issue], BROKERS, formatQuantity);

                expect(formatQuantity).not.toHaveBeenCalled();
                expect(row.messageParams).toEqual(issue.message_params);
            });

            // Why: present means not null, not truthy — a zero is a quantity too, and a quantity left raw is one privacy
            // never masks.
            it('writes a missing_quantity of zero through formatQuantity too', () => {
                const formatQuantity = vi.fn(markQuantity);
                const issue = blockingIssue(SOURCE_MISSING, {transaction_id: 4242, broker_id: ALFA.id, transaction_date: '2026-03-05', missing_quantity: 0});

                expect(buildFailureRows([issue], BROKERS, formatQuantity)[0].messageParams.missing_quantity).toBe('qty(0)');
                expect(formatQuantity.mock.calls.map(([raw]) => raw)).toEqual([0]);
            });

            // Why: the panel rebuilds the rows on every privacy toggle and hands the same issues to the banner; a
            // formatted value written back would be formatted a second time, or reach the banner masked.
            it('changes nothing in the issues it reads', () => {
                const issues = [shortfall, blockingIssue(SHORT_ADJUSTMENT, {transaction_id: 4243, broker_id: BETA.id, transaction_date: '2026-02-01', missing_quantity: '2.500000'})];
                const before = structuredClone(issues);

                buildFailureRows(issues, BROKERS, markQuantity);

                expect(issues).toEqual(before);
            });

            it('turns an issue without message_params into a row that names nothing', () => {
                const formatQuantity = vi.fn(markQuantity);
                const bare: WireIssue = {domain: 'PORTFOLIO', code: PAIR_MISSING, severity: 'error', message_i18n_key: MESSAGE_KEY[PAIR_MISSING]};

                expect(buildFailureRows([bare], BROKERS, formatQuantity)).toEqual([{key: 'TRANSFER_PAIR_MISSING:none', code: PAIR_MISSING, transactionId: null, transactionDate: null, brokerName: '—', messageKey: 'dataQuality.transferPairMissing', messageParams: {}}]);
                expect(formatQuantity).not.toHaveBeenCalled();
            });
        });

        describe('one row per (code, transaction)', () => {
            // Why: corrupt data may repeat an issue; the notice names each row to fix once, and keys its list by `key`.
            it('collapses a repeated (code, transaction id) into one row: the first occurrence wins', () => {
                // The repeat names the same transaction as a digit string, with another broker, an earlier day and other figures.
                const repeat = blockingIssue(SOURCE_MISSING, {transaction_id: '4242', broker_id: BETA.id, transaction_date: '2026-01-15', missing_quantity: '9.000000'});

                const rows = buildFailureRows([shortfall, repeat], BROKERS, markQuantity);

                expect(rows).toHaveLength(1);
                expect(rows[0]).toMatchObject({key: 'FIFO_SOURCE_QUANTITY_MISSING:4242', transactionDate: '2026-03-05', brokerName: 'Broker Alfa'});
                expect(rows[0].messageParams.missing_quantity).toBe('qty(4.000000)');
            });

            it('keeps the same transaction under two codes as two rows', () => {
                const alsoShort = blockingIssue(SHORT_TRANSFER, {transaction_id: 4242, broker_id: ALFA.id, related_transaction_id: 4300, transaction_date: '2026-03-05'});

                expect(rowKeys([shortfall, alsoShort]).sort()).toEqual(['FIFO_SOURCE_QUANTITY_MISSING:4242', 'SHORT_TRANSFER_NOT_SUPPORTED:4242']);
            });

            it('collapses two issues of one code without a transaction id: they share the key (code, none)', () => {
                const first = blockingIssue(PAIR_MISSING, {transaction_id: null, broker_id: ALFA.id, related_transaction_id: 55});
                const second = blockingIssue(PAIR_MISSING, {transaction_id: null, broker_id: BETA.id, related_transaction_id: 56});

                const rows = buildFailureRows([first, second], BROKERS, markQuantity);

                expect(rows.map((row) => [row.key, row.brokerName])).toEqual([['TRANSFER_PAIR_MISSING:none', 'Broker Alfa']]);
            });
        });

        describe('order', () => {
            /** A blocking issue reduced to what orders it. */
            const at = (code: string, transaction_id: number | null, transaction_date: string | null): WireIssue => blockingIssue(code, {transaction_id, broker_id: ALFA.id, transaction_date});

            // Why: the replay breaks at its first wrong row, so the user reads the rows in the order of their days.
            it('earlier day first, whatever the input order', () => {
                expect(rowKeys([at(SOURCE_MISSING, 4242, '2026-03-05'), at(SHORT_ADJUSTMENT, 4243, '2026-02-01')])).toEqual(['SHORT_ADJUSTMENT_NOT_SUPPORTED:4243', 'FIFO_SOURCE_QUANTITY_MISSING:4242']);
            });

            it('same day: lower transaction id first, before the code; a row without one after them', () => {
                expect(rowKeys([at(SOURCE_MISSING, null, '2026-03-05'), at(SOURCE_MISSING, 5002, '2026-03-05'), at(PAIR_MISSING, 5001, '2026-03-05')])).toEqual(['TRANSFER_PAIR_MISSING:5001', 'FIFO_SOURCE_QUANTITY_MISSING:5002', 'FIFO_SOURCE_QUANTITY_MISSING:none']);
            });

            it('same day and transaction: by code', () => {
                expect(rowKeys([at(SHORT_TRANSFER, 4242, '2026-03-05'), at(SOURCE_MISSING, 4242, '2026-03-05')])).toEqual(['FIFO_SOURCE_QUANTITY_MISSING:4242', 'SHORT_TRANSFER_NOT_SUPPORTED:4242']);
            });

            it('rows without a day after every dated row; among them by transaction id, none last, then by code', () => {
                expect(rowKeys([at(PAIR_MISSING, null, null), at(SOURCE_MISSING, 11, null), at(SHORT_ADJUSTMENT, 9999, '2026-12-31'), at(SOURCE_MISSING, 10, null), at(SHORT_TRANSFER, null, null)])).toEqual([
                    'SHORT_ADJUSTMENT_NOT_SUPPORTED:9999',
                    'FIFO_SOURCE_QUANTITY_MISSING:10',
                    'FIFO_SOURCE_QUANTITY_MISSING:11',
                    'SHORT_TRANSFER_NOT_SUPPORTED:none',
                    'TRANSFER_PAIR_MISSING:none',
                ]);
            });

            it('the whole order at once, from a shuffled input and from its reverse', () => {
                const issues = [
                    at(PAIR_MISSING, null, null),
                    at(SHORT_TRANSFER, 4242, '2026-03-05'),
                    at(SOURCE_MISSING, 4242, '2026-03-05'),
                    at(SOURCE_MISSING, 10, null),
                    at(SOURCE_MISSING, null, '2026-03-05'),
                    at(SHORT_ADJUSTMENT, 4243, '2026-02-01'),
                    at(SOURCE_MISSING, 11, null),
                    at(PAIR_MISSING, 4241, '2026-03-05'),
                ];
                const expected = [
                    'SHORT_ADJUSTMENT_NOT_SUPPORTED:4243',
                    'TRANSFER_PAIR_MISSING:4241',
                    'FIFO_SOURCE_QUANTITY_MISSING:4242',
                    'SHORT_TRANSFER_NOT_SUPPORTED:4242',
                    'FIFO_SOURCE_QUANTITY_MISSING:none',
                    'FIFO_SOURCE_QUANTITY_MISSING:10',
                    'FIFO_SOURCE_QUANTITY_MISSING:11',
                    'TRANSFER_PAIR_MISSING:none',
                ];

                expect(rowKeys(issues)).toEqual(expected);
                expect(rowKeys([...issues].reverse())).toEqual(expected);
            });
        });
    });
});
