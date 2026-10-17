/**
 * @vitest-environment node
 *
 * Branch-exhaustive unit tests for the pure helpers extracted from
 * LotDataQualityBanner.svelte: lot-id resolution, overall severity, and the
 * grouping/dedup/disambiguation pipeline. i18n is injected as a plain
 * `labelForDate` echo so labels are asserted deterministically, no runtime.
 *
 * Two blocks close the file, each with its notes beside it: J-12 pins the two
 * helpers of a FAILED analysis — the issue partition and the failure rows; J-53
 * pins the lines of a group — every lot-less issue keeps its own message.
 */
import {describe, it, expect, vi} from 'vitest';
import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {resolveLotId, groupedSeverity, buildIssueGroups, partitionLotIssues, buildFailureRows, type FailureRow, type IssueGroup, type IssueSeverity} from './lotDataQualityHelpers';
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
        expect(groups[0]).toMatchObject({code: 'REF', severity: 'warning'});
        expect(groups[0].messages.map((message) => message.messageKey)).toEqual(['msg.REF']);
        expect(groups[0].lots).toEqual([{lotId: 10, label: '2024-03-15'}]);
    });

    it('preserves message params and key on the group’s message', () => {
        const groups = buildIssueGroups([issue('REF', 'warning', 10, {extra: {foo: 'bar'}})], new Map([[10, 'd']]), echo);
        expect(groups[0].messages).toHaveLength(1);
        expect(groups[0].messages[0].params).toEqual({lot_id: 10, foo: 'bar'});
        expect(groups[0].messages[0].messageKey).toBe('msg.REF');
    });

    it('defaults the message params to {} when the issue has none (?? {} right arm)', () => {
        const groups = buildIssueGroups([issue('REF', 'info', undefined, {withParams: false})], new Map(), echo);
        expect(groups[0].messages).toHaveLength(1);
        expect(groups[0].messages[0].params).toEqual({});
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

/**
 * J-53 — every lot-less issue keeps its own message (workstream Y).
 *
 * The contract. The lots banner groups the issues by code: one block per code, keyed by the code and drawn as
 * `lot-data-quality-issue-{code}`, the header counting categories. Until J-53 a group kept the message key and the
 * params of its FIRST issue only (`IssueGroup.messageKey`, `messageParams`). A lot-scoped code loses nothing that way:
 * its issues say the same thing of different lots, and the lots come back as chips. A lot-less issue loses everything.
 * The backend puts `lot_id` in the params of every engine issue, null when the issue has no lot
 * (`lots_analysis_service.py`, `_build_data_quality_report`), and the engine sends `ASSET_INCOME_NO_ELIGIBLE_LOTS` and
 * `ASSET_COST_NO_ELIGIBLE_LOTS` once per orphan pool (`engine.py`), each with its own `economic_type`, `as_of_date`,
 * `target_amount` and `target_currency`: with two pools the banner showed one amount and one date and hid the other,
 * understating the income left unallocated. `_report_gaps` may likewise send `MISSING_FX_RATES` twice, under two
 * message keys (the pairs a provider syncs, the manual pairs) and without any `lot_id`: the second never showed.
 *
 * The cure (the coordinator's decision; its shape, Y's). `IssueGroup.messages` replaces `messageKey` and
 * `messageParams`: the group's lines, never empty, each `{key, messageKey, params}`.
 *   - An issue is lot-less when `resolveLotId(message_params?.lot_id)` is not finite: null, absent, not a number. A
 *     finite id the visible-lot map lacks (a hidden lot) is a lot: that issue stays lot-bearing, with no chip.
 *   - The lot-bearing issues of a code make ONE line, the first one's key and params, and their visible lots the
 *     chips, as before.
 *   - Each lot-less issue makes a line of its own, with its own key and params (`?? {}`); a repeat — the same key and
 *     deep-equal params — makes none: the first occurrence wins.
 *   - The lines come in first-occurrence order: the lot-bearing line where the first lot-bearing issue came, each
 *     lot-less line where its issue came.
 *   - A line's `key` is unique within its group, which the banner keys its lines by; its format is the cure's
 *     business, and nothing here reads it.
 *   - The groups, their severity order and the chips: unchanged.
 *
 * Fixtures. The issues are built as the client receives them (`DataQualityIssue`, domain included): an engine issue
 * carries `transaction_id`, `lot_id`, `broker_id` and `related_transaction_id`, null when it has none, then its own
 * params, amounts as decimal strings; a `_report_gaps` issue carries its own params only (the fields beside them,
 * which the helper does not read, are left out). Groups are found by their code, never by position; the lines of a
 * group are compared in order, because their order is the contract.
 *
 * Red, before the cure: every test of this block fails on `messages`, undefined on today's groups, except the one
 * named «control», which holds today and must hold after the cure. Three tests of the `buildIssueGroups` block above
 * read the message from `messages` now, and are red for the same reason; the others are untouched and stay green.
 */

/** The params of an issue, as sent. */
type Params = Record<string, Param>;

/** The catalogue key the backend sends with each orphan code (`_message_key_for_issue`). */
const ORPHAN_KEY = {
    ASSET_INCOME_NO_ELIGIBLE_LOTS: 'dataQuality.assetIncomeNoEligibleLots',
    ASSET_COST_NO_ELIGIBLE_LOTS: 'dataQuality.assetCostNoEligibleLots',
} as const;

type OrphanCode = keyof typeof ORPHAN_KEY;

const INCOME = 'ASSET_INCOME_NO_ELIGIBLE_LOTS' as const;
const COST = 'ASSET_COST_NO_ELIGIBLE_LOTS' as const;
const FALLBACK = 'REFERENCE_PRICE_FALLBACK';
const FX_RATES = 'MISSING_FX_RATES';

/** An orphan pool as its issue names it (`engine.py`): the pool's first source row, its broker, the engine's four params. */
interface Pool {
    transaction_id: number;
    broker_id: number;
    economic_type: string;
    as_of_date: string;
    target_amount: string;
    target_currency: string;
}

/** An orphan pool's issue as `_build_data_quality_report` serialises it: a warning, with no lot and no related row. */
function orphan(code: OrphanCode, {transaction_id, broker_id, ...params}: Pool): WireIssue {
    return {domain: 'PORTFOLIO', code, severity: 'warning', message_i18n_key: ORPHAN_KEY[code], message_params: {transaction_id, lot_id: null, broker_id, related_transaction_id: null, ...params}};
}

/** `REFERENCE_PRICE_FALLBACK` as the engine sends it for a lot an adjustment opened: the lot is its opening row. */
function priceFallback(lotId: number, brokerId: number, referencePrice: string): WireIssue {
    return {domain: 'PORTFOLIO', code: FALLBACK, severity: 'warning', message_i18n_key: MESSAGE_KEY[FALLBACK], message_params: {transaction_id: lotId, lot_id: lotId, broker_id: brokerId, related_transaction_id: null, reference_price: referencePrice}};
}

/** Two orphan income pools at Broker Alfa: 12.50 EUR of dividends on 15 March, 30.75 EUR on 20 June. */
const MARCH = orphan(INCOME, {transaction_id: 7101, broker_id: ALFA.id, economic_type: 'DIVIDEND', as_of_date: '2024-03-15', target_amount: '12.50', target_currency: 'EUR'});
const JUNE = orphan(INCOME, {transaction_id: 7102, broker_id: ALFA.id, economic_type: 'DIVIDEND', as_of_date: '2024-06-20', target_amount: '30.75', target_currency: 'EUR'});

/** Two orphan cost pools: a fee at Broker Alfa on 2 May, a tax at Broker Beta on 20 June. */
const FEE_MAY = orphan(COST, {transaction_id: 7201, broker_id: ALFA.id, economic_type: 'FEE', as_of_date: '2024-05-02', target_amount: '4.90', target_currency: 'EUR'});
const TAX_JUNE = orphan(COST, {transaction_id: 7202, broker_id: BETA.id, economic_type: 'TAX', as_of_date: '2024-06-20', target_amount: '7.30', target_currency: 'EUR'});

/** `_report_gaps`'s two issues of one code (`build_data_quality_report`): the pairs a provider syncs, the manual pairs. */
const FX_PROVIDER: WireIssue = {domain: 'PORTFOLIO', code: FX_RATES, severity: 'warning', message_i18n_key: 'dataQuality.missingFxRates', message_params: {count: 2, date_from: '2024-02-01', date_to: '2024-05-31', dates_count: 14}};
const FX_MANUAL: WireIssue = {domain: 'PORTFOLIO', code: FX_RATES, severity: 'warning', message_i18n_key: 'dataQuality.missingFxRatesManual', message_params: {count: 1}};

/** The visible lots, lot id → opening day: 501 and 502. Lots 998 and 999 are hidden. */
const LOT_DATES: ReadonlyMap<number, string> = new Map([
    [501, '2024-01-10'],
    [502, '2024-02-05'],
]);

/** A line as the banner writes it, its key left out: the catalogue key and its params. */
interface Line {
    messageKey: string;
    params: Params;
}

/** The lines of `group`, in order. */
function linesOf(group: IssueGroup): Line[] {
    return group.messages.map(({messageKey, params}) => ({messageKey, params}));
}

/** The line an issue makes on its own: its key and its params. */
function lineOf(sent: RawIssue): Line {
    return {messageKey: sent.message_i18n_key, params: sent.message_params ?? {}};
}

/** The one group of `code`: found by its code, never by its position. */
function groupOf(groups: readonly IssueGroup[], code: string): IssueGroup {
    const found = groups.filter((group) => group.code === code);
    expect(found, `one group for ${code}`).toHaveLength(1);
    return found[0];
}

describe('J-53 — every lot-less issue keeps its own message', () => {
    describe('lot-less issues', () => {
        // Why: the defect itself — with two pools the banner wrote one amount and one day, and hid the other pool.
        it('two orphan income pools: one group, a line per pool with its own params, in input order, and no chip', () => {
            // June first: the engine sends the pools by day, so only an input out of day order tells input order from a sort.
            const groups = buildIssueGroups([JUNE, MARCH], LOT_DATES, echo);

            expect(
                groups.map((group) => group.code),
                'one group for the two pools',
            ).toEqual([INCOME]);
            const group = groupOf(groups, INCOME);
            expect(linesOf(group), 'each pool its own amount and day, in the order sent').toEqual([lineOf(JUNE), lineOf(MARCH)]);
            expect(group.lots, 'no lot named, no chip').toEqual([]);
        });

        it('orphan cost pools alongside: two groups, each with its own pools as lines', () => {
            const groups = buildIssueGroups([MARCH, FEE_MAY, JUNE, TAX_JUNE], LOT_DATES, echo);

            expect(groups.map((group) => group.code).sort(), 'a group per code').toEqual([COST, INCOME].sort());
            expect(linesOf(groupOf(groups, INCOME)), 'the income pools').toEqual([lineOf(MARCH), lineOf(JUNE)]);
            expect(linesOf(groupOf(groups, COST)), 'the cost pools').toEqual([lineOf(FEE_MAY), lineOf(TAX_JUNE)]);
        });

        // Why: `_report_gaps` sends MISSING_FX_RATES once for the pairs a provider syncs and once for the manual ones —
        // two sentences, two things to do; the second hid behind the first.
        it('MISSING_FX_RATES twice, the pairs a provider syncs and the manual pairs: one group, two lines, each with its own message key', () => {
            const group = groupOf(buildIssueGroups([FX_PROVIDER, FX_MANUAL], LOT_DATES, echo), FX_RATES);

            expect(linesOf(group)).toEqual([lineOf(FX_PROVIDER), lineOf(FX_MANUAL)]);
            expect(group.lots).toEqual([]);
        });

        // Why: lot-less is «no finite lot id», in every form the id can be missing — `_report_gaps`'s issues send none.
        it.each([
            {name: 'null, as the backend sends it', lotId: null},
            {name: 'absent', lotId: ABSENT},
            {name: 'not a number', lotId: 'n/a'},
        ] as ReadonlyArray<{name: string; lotId: Param | typeof ABSENT}>)('lot_id $name: the issue is lot-less, a line of its own', ({lotId}) => {
            const march = withParam(MARCH, 'lot_id', lotId);
            const june = withParam(JUNE, 'lot_id', lotId);

            expect(linesOf(groupOf(buildIssueGroups([march, june], LOT_DATES, echo), INCOME))).toEqual([lineOf(march), lineOf(june)]);
        });

        // Why: the same pool reported twice must not print the same sentence twice.
        it('a repeat — the same key, deep-equal params, another object — makes no line: the first occurrence keeps its place', () => {
            const repeat = structuredClone(MARCH);
            expect(repeat, 'control: the repeat is another object').not.toBe(MARCH);

            const group = groupOf(buildIssueGroups([MARCH, JUNE, repeat], LOT_DATES, echo), INCOME);

            expect(linesOf(group)).toEqual([lineOf(MARCH), lineOf(JUNE)]);
        });

        // Why: the same amount on the same day is not the same pool — another source row, another broker, another currency.
        it.each([
            {name: 'its source transaction', param: 'transaction_id', value: 7199},
            {name: 'its broker', param: 'broker_id', value: BETA.id},
            {name: 'its economic type', param: 'economic_type', value: 'INTEREST'},
            {name: 'its day', param: 'as_of_date', value: '2024-03-16'},
            {name: 'its amount', param: 'target_amount', value: '12.51'},
            {name: 'its currency', param: 'target_currency', value: 'USD'},
        ] as ReadonlyArray<{name: string; param: string; value: Param}>)('two pools apart only by $name are two lines', ({param, value}) => {
            const twin = withParam(MARCH, param, value);

            expect(linesOf(groupOf(buildIssueGroups([MARCH, twin], LOT_DATES, echo), INCOME))).toEqual([lineOf(MARCH), lineOf(twin)]);
        });

        // Why: a repeat is the same key AND the same params; the same params under another key are another sentence.
        it('the same params under another message key are two lines', () => {
            const one = issue('GAP', 'warning', undefined, {key: 'msg.one', extra: {count: 1}});
            const other = issue('GAP', 'warning', undefined, {key: 'msg.other', extra: {count: 1}});

            expect(linesOf(groupOf(buildIssueGroups([one, other], new Map(), echo), 'GAP'))).toEqual([lineOf(one), lineOf(other)]);
        });
    });

    describe('lot-bearing issues', () => {
        // Why: a lot-scoped code says the same thing of each lot, and names the lots as chips. Unchanged by J-53.
        it('the lot-bearing issues of a code make one line, the first one’s, and their visible lots the chips', () => {
            const lot502 = priceFallback(502, BETA.id, '99.80');
            const lot501 = priceFallback(501, ALFA.id, '101.25');

            const group = groupOf(buildIssueGroups([lot502, lot501], LOT_DATES, echo), FALLBACK);

            expect(linesOf(group), 'one line: the first issue’s key and params').toEqual([lineOf(lot502)]);
            expect(group.lots, 'a chip per lot, by opening day').toEqual([
                {lotId: 501, label: '2024-01-10'},
                {lotId: 502, label: '2024-02-05'},
            ]);
        });

        // Why: a hidden lot is still a lot. It gets no chip — it is not on screen — and no line of its own either.
        it('an issue on a hidden lot (a finite id the map lacks) stays lot-bearing: no chip, and no line of its own', () => {
            const hidden = priceFallback(999, ALFA.id, '88.00');
            const visible = priceFallback(501, ALFA.id, '101.25');
            // A digit string is a finite id too.
            const hiddenAsText = withParam(priceFallback(998, BETA.id, '91.40'), 'lot_id', '998');
            expect(
                [999, 998].filter((lotId) => LOT_DATES.has(lotId)),
                'control: lots 998 and 999 are hidden',
            ).toEqual([]);

            const group = groupOf(buildIssueGroups([hidden, visible, hiddenAsText], LOT_DATES, echo), FALLBACK);

            expect(linesOf(group), 'one line: the first lot-bearing issue’s, on the hidden lot').toEqual([lineOf(hidden)]);
            expect(group.lots, 'a chip for the visible lot only').toEqual([{lotId: 501, label: '2024-01-10'}]);
        });

        // Why: not seen in practice, pinned anyway — the lines keep the order their issues came in.
        it('a code with both kinds: the lot-bearing line where the first lot-bearing issue came, each lot-less line where its own came', () => {
            const noLotA = withParam(priceFallback(601, ALFA.id, '90.00'), 'lot_id', null);
            const noLotB = withParam(priceFallback(602, BETA.id, '95.00'), 'lot_id', null);
            const lot501 = priceFallback(501, ALFA.id, '101.25');
            const lot502 = priceFallback(502, BETA.id, '99.80');

            const lotLessFirst = groupOf(buildIssueGroups([noLotA, lot501, noLotB, lot502], LOT_DATES, echo), FALLBACK);
            expect(linesOf(lotLessFirst), 'lot-less, lot-bearing, lot-less: the second lot-bearing issue joins the first one’s line').toEqual([lineOf(noLotA), lineOf(lot501), lineOf(noLotB)]);
            expect(
                lotLessFirst.lots.map((lot) => lot.lotId),
                'the chips, as before',
            ).toEqual([501, 502]);

            const lotBearingFirst = groupOf(buildIssueGroups([lot502, noLotA, lot501, noLotB], LOT_DATES, echo), FALLBACK);
            expect(linesOf(lotBearingFirst), 'lot-bearing first: its line first, with the first lot-bearing issue’s params').toEqual([lineOf(lot502), lineOf(noLotA), lineOf(noLotB)]);
            expect(
                lotBearingFirst.lots.map((lot) => lot.lotId),
                'the chips, as before',
            ).toEqual([501, 502]);
        });
    });

    describe('the groups', () => {
        // Why: the banner keys a block's lines by `key`; two equal keys are a Svelte error (`each_key_duplicate`).
        it('gives each line a key no other line of its group has', () => {
            const noLot = withParam(priceFallback(601, ALFA.id, '90.00'), 'lot_id', null);
            const groups = buildIssueGroups([priceFallback(501, ALFA.id, '101.25'), noLot, MARCH, FEE_MAY, JUNE, TAX_JUNE, FX_PROVIDER, FX_MANUAL, priceFallback(502, BETA.id, '99.80')], LOT_DATES, echo);

            expect(groups.map((group) => group.code).sort(), 'barrier: the four groups').toEqual([COST, FALLBACK, FX_RATES, INCOME].sort());
            for (const group of groups) {
                const keys = group.messages.map((message) => message.key);
                expect(keys.length, `barrier: ${group.code} has lines to tell apart`).toBeGreaterThan(1);
                expect(new Set(keys).size, `${group.code}: no two lines share a key`).toBe(keys.length);
            }
        });

        // Why: the banner keys its blocks by code and the header counts categories: one group per code, whatever it carries.
        it('one group per code however many lot-less issues it carries, and none without a line', () => {
            const atCost: WireIssue = {domain: 'PORTFOLIO', code: 'CURRENT_PRICE_ASSUMED_AT_COST', severity: 'warning', message_i18n_key: 'dataQuality.currentPriceAssumedAtCostRange', message_params: {asset_id: 9031, date_from: '2024-01-10', date_to: '2024-02-29'}};
            const costBasis: WireIssue = {domain: 'PORTFOLIO', code: 'MISSING_COST_BASIS', severity: 'warning', message_i18n_key: 'dataQuality.missingCostBasis', message_params: {count: 1}};
            const incomePools = [MARCH, JUNE, withParam(MARCH, 'as_of_date', '2024-09-16'), withParam(JUNE, 'as_of_date', '2024-12-16')];
            const costPools = [FEE_MAY, TAX_JUNE, withParam(FEE_MAY, 'as_of_date', '2024-08-01')];
            const issues = [priceFallback(501, ALFA.id, '101.25'), priceFallback(502, BETA.id, '99.80'), ...incomePools, ...costPools, atCost, FX_PROVIDER, FX_MANUAL, costBasis];

            const groups = buildIssueGroups(issues, LOT_DATES, echo);

            expect(groups.map((group) => group.code).sort(), 'each code of the input, once').toEqual([...new Set(issues.map((sent) => sent.code))].sort());
            expect(Object.fromEntries(groups.map((group) => [group.code, group.messages.length])), 'the lines of each group').toEqual({
                [FALLBACK]: 1,
                [INCOME]: 4,
                [COST]: 3,
                CURRENT_PRICE_ASSUMED_AT_COST: 1,
                [FX_RATES]: 2,
                MISSING_COST_BASIS: 1,
            });
        });

        // Control, green before and after the cure: the lines change nothing in the order of the groups.
        it('control: the groups still come by severity — error, warning, info — whatever lines they carry', () => {
            const lotLess = (code: string, severity: IssueSeverity, count: number): RawIssue => issue(code, severity, undefined, {extra: {count}});

            const groups = buildIssueGroups([lotLess('I', 'info', 1), lotLess('W', 'warning', 1), lotLess('I', 'info', 2), lotLess('E', 'error', 1), lotLess('W', 'warning', 2), lotLess('E', 'error', 2)], new Map(), echo);

            expect(groups.map((group) => group.code)).toEqual(['E', 'W', 'I']);
        });
    });
});
