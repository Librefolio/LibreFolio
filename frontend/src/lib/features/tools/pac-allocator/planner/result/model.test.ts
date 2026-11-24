// @vitest-environment node
/**
 * model — the help the proof badge opens, the catalogue behind every badge, and the ledger's
 * rounding column (Vitest, node).
 *
 * Subject. `resultBadges` turns a ready result into the badges at the head of the result:
 * availability, the Decimal check when the plan carries it, proof and stop reason, each with the
 * explanation it opens on hover or focus (R11.4). Since S4 (developer decision Q6 (ii)) the help
 * of a `not_proven` proof depends on how the run ended:
 *   - no plan (`no_incumbent`): the state's own explanation, since "the best plan found" would be
 *     false with no plan;
 *   - a plan and a `completed` search: `proof.floatingFinished`. The solver closed its search, so
 *     what keeps the proof from holding is the final exact check (P-c) contradicting the solver's
 *     bounds;
 *   - a plan and a `time_limit` or `node_limit` stop: `proof.floatingUnfinished`, the solver did
 *     not close every stage.
 * Before S4 every `not_proven` proof with a plan opened `floatingUnfinished`, so a search that had
 * completed was told it had stopped early: the first case is the one that pins S4. The help of
 * `optimal_proven` and `infeasibility_proven` is pinned alongside.
 *
 * Expectations. The proof badge is found by its `id`, never by its place in the list, and the
 * assertion is on the help's catalogue key: the key decides the sentence in every locale.
 *
 * Catalogue (P-d). A badge carries an English fallback for its label and for its help, and P-d
 * was about fallbacks and catalogue promising different things. For every badge the cases
 * produce, the stop badge included (its key is built from the stop reason), each fallback must
 * equal the EN catalogue's message at its key, and a key with no message in `en.json` is a
 * failure, not a skip. The check compares two sources and never spells a sentence itself.
 * Controls prove that the resolver finds nothing at a missing key or at a subtree, and that the
 * walk reached all four kinds of badge, the Decimal check and the three stop labels. They name no
 * proof help: which help the proof badge opens is the cases' subject, so a wrong help is red there
 * and only there.
 *
 * Results. Minimal objects cast to `PlannerReadyResult`: `outcome`, `stop_reason`, `proof.kind`, and
 * `primary_solution.validation` on the cases with a plan. The contract requires a primary
 * solution on `ready_incumbent` and knows its validation only as `decimal_verified`, so there the
 * Decimal-check badge appears and enters the catalogue check too.
 *
 * Ledger columns (fix A). The ledger table shows a balance column only when some row is not 0
 * there (`ledgerFields`, R9.8). A ledger row's `rounding_delta` is an exact number, a finite
 * decimal or an exact ratio, because a conversion through the reciprocal of a stored rate leaves
 * a residual with no finite decimal (-47/21700 EUR). The filter reads it as such: it hides the
 * column when every residual is an exact zero and shows it for a nonzero ratio or decimal on any
 * row. Before fix A the field was decimal text, and the filter, reading an object as text, threw.
 * The rows are minimal objects cast to `PlannerLedgerRow`, every balance `'0'`, so the rounding
 * residual is the only value that can make its column speak.
 *
 * Environment. `resultBadges` and `ledgerFields` read plain fields and touch no DOM: node is enough.
 */
import {describe, expect, it, vi} from 'vitest';

// The badges module imports the planner's formatter, which reads the currency catalogue store,
// which imports the API client. Nothing here formats an amount: every call resolves to nothing.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import en from '$lib/i18n/en.json';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {catalogCurrencyDigits, formatPlannerMoneyPlain} from '../format';
import type {PlannerExactNumber, PlannerLedgerRow, PlannerProof, PlannerReadyResult} from '../types';
import {allocationRows, hasPlanSteps, LEDGER_FIELDS, ledgerFieldList, ledgerFields, ledgerHelpKey, ledgerLabelKey, limitedEntries, notesBesideLimitsBanner, planSteps, proofStatusHelpKey, resultBadges, type LimitedEntry, type ResultBadge} from './model';
import type {RebalancerSolution} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import type {PlannerResolvedRequest} from '../types';

interface ProofCase {
    proof: PlannerProof['kind'];
    outcome: PlannerReadyResult['outcome'];
    stop_reason: PlannerReadyResult['stop_reason'];
    /** A not-proven proof's reason, when the case sets one (lot SEEDS of project 67). */
    reason?: string;
    /** The catalogue key of the help the proof badge must open. */
    help: string;
    /** Why that help: the assertion's message when it fails. */
    why: string;
}

/** The states the proof badge's help is decided on. The first is S4's own: a completed search that is still not proven. */
const CASES: ProofCase[] = [
    {proof: 'not_proven', outcome: 'incumbent_found', stop_reason: 'completed', help: 'tools.pacAllocator.planner.result.proof.floatingFinished', why: 'the search completed and is still not proven: the final exact check contradicted the solver bounds'},
    {proof: 'not_proven', outcome: 'incumbent_found', stop_reason: 'time_limit', help: 'tools.pacAllocator.planner.result.proof.floatingUnfinished', why: 'the solver reached its time limit before closing every stage'},
    {proof: 'not_proven', outcome: 'incumbent_found', stop_reason: 'node_limit', help: 'tools.pacAllocator.planner.result.proof.floatingUnfinished', why: 'the solver reached its node limit before closing every stage'},
    {proof: 'not_proven', outcome: 'no_incumbent', stop_reason: 'time_limit', help: 'tools.pacAllocator.planner.result.states.noIncumbent.body', why: 'with no plan, "the best plan found" would be false: the help says what the state says'},
    {
        proof: 'not_proven',
        outcome: 'incumbent_found',
        stop_reason: 'completed',
        reason: 'allocation.proof_not_confirmed',
        help: 'tools.pacAllocator.planner.result.proof.notConfirmed',
        why: 'lot SEEDS: one search ended on this plan and no second one confirmed it; its numbers do match the exact check',
    },
    {
        proof: 'not_proven',
        outcome: 'incumbent_found',
        stop_reason: 'completed',
        reason: 'allocation.limits_leave_no_rounding_room',
        help: 'tools.pacAllocator.planner.result.proof.limitsLeaveNoRoundingRoom',
        why: 'lot SEEDS: a plan of the wide model, found counting the rounding in its favour; the exact check is not the cause',
    },
    {proof: 'not_proven', outcome: 'no_incumbent', stop_reason: 'completed', help: 'tools.pacAllocator.planner.result.states.noIncumbent.completedBody', why: 'lot ZB: the search ended with no plan the exact check accepts; no limit stopped it, so "before the limit" would be false'},
    {proof: 'optimal_proven', outcome: 'incumbent_found', stop_reason: 'completed', help: 'tools.pacAllocator.planner.result.badges.help.optimalProven', why: 'a proven optimum explains its proof'},
    {proof: 'infeasibility_proven', outcome: 'infeasible_proven', stop_reason: 'completed', help: 'tools.pacAllocator.planner.result.proof.solverInfeasibleWitness', why: 'a proven infeasibility names the solver witness'},
];

/** The stop badge builds its key from the stop reason; the cases reach all three. */
const STOP_KEYS = ['tools.pacAllocator.planner.result.stop.completed', 'tools.pacAllocator.planner.result.stop.time_limit', 'tools.pacAllocator.planner.result.stop.node_limit'];
/** The Decimal-check badge, which every case with a plan carries. */
const DECIMAL_CHECK_KEY = 'tools.pacAllocator.planner.result.badges.decimalVerified';

function caseTitle(c: ProofCase): string {
    return `${c.proof} + ${c.outcome} + ${c.stop_reason}${c.reason ? ` + ${c.reason}` : ''}`;
}

/** Only what `resultBadges` reads. A plan carries its primary solution, as the contract requires. */
function readyResult(c: ProofCase): PlannerReadyResult {
    const plan = c.outcome === 'incumbent_found' ? {primary_solution: {validation: 'decimal_verified'}} : {};
    const proof = c.reason ? {kind: c.proof, reason_code: c.reason} : {kind: c.proof};
    return {outcome: c.outcome, stop_reason: c.stop_reason, proof, ...plan} as unknown as PlannerReadyResult;
}

/** The badge with this id, found by what it is and never by its place in the list. */
function badgeById(badges: ResultBadge[], id: string): ResultBadge {
    const matches = badges.filter((badge) => badge.id === id);
    expect(matches, `one '${id}' badge`).toHaveLength(1);
    return matches[0];
}

/** The EN message at a dotted key; undefined when the key is missing or names a subtree. */
function catalogueMessage(key: string): string | undefined {
    const node = key.split('.').reduce<unknown>((parent, part) => (parent !== null && typeof parent === 'object' ? (parent as Record<string, unknown>)[part] : undefined), en);
    return typeof node === 'string' ? node : undefined;
}

describe('resultBadges — the help the proof badge opens', () => {
    for (const c of CASES) {
        it(`${caseTitle(c)} → ${c.help}`, () => {
            expect(badgeById(resultBadges(readyResult(c)), 'proof').help.key, c.why).toBe(c.help);
        });
    }
});

describe('resultBadges — every fallback is the EN catalogue message at its key (P-d)', () => {
    it('reads a message at a key, and nothing at a missing key or at a subtree', () => {
        expect(catalogueMessage('tools.pacAllocator.planner.result.stop.completed')).toEqual(expect.any(String));
        expect(catalogueMessage('tools.pacAllocator.planner.result.proof.noSuchMessage')).toBeUndefined();
        expect(catalogueMessage('tools.pacAllocator.planner.result.proof')).toBeUndefined();
    });

    it('holds for the label and the help of every badge the cases produce, stop badges included', () => {
        const checkedIds = new Set<string>();
        const checkedKeys = new Set<string>();
        const mismatches: string[] = [];
        for (const c of CASES) {
            for (const badge of resultBadges(readyResult(c))) {
                checkedIds.add(badge.id);
                const pairs: {part: string; key: string; fallback: string}[] = [
                    {part: 'label', key: badge.key, fallback: badge.fallback},
                    {part: 'help', key: badge.help.key, fallback: badge.help.fallback},
                ];
                for (const {part, key, fallback} of pairs) {
                    checkedKeys.add(key);
                    const message = catalogueMessage(key);
                    const where = `${caseTitle(c)}, ${badge.id} ${part} at ${key}`;
                    if (message === undefined) mismatches.push(`${where}: en.json has no message there`);
                    else if (message !== fallback) mismatches.push(`${where}: the fallback says ${JSON.stringify(fallback)}, en.json says ${JSON.stringify(message)}`);
                }
            }
        }
        // The walk reached what it claims to cover: all four kinds of badge, the Decimal check and the three stop labels.
        expect([...checkedIds]).toEqual(expect.arrayContaining(['availability', 'validation', 'proof', 'stop']));
        expect([...checkedKeys]).toEqual(expect.arrayContaining([DECIMAL_CHECK_KEY, ...STOP_KEYS]));
        expect(mismatches).toEqual([]);
    });
});

// Fix A: a ledger row's rounding residual is an exact number, no longer decimal text.

const ZERO_RESIDUAL: PlannerExactNumber = {kind: 'finite_decimal', value: '0'};
/** A USD funding converted to EUR through the reciprocal of a stored EUR/USD: no finite decimal. */
const RATIO_RESIDUAL: PlannerExactNumber = {kind: 'exact_ratio', numerator: '-47', denominator: '21700', display_decimal: '-0.002166', display_scale: 6, display_authority: 'non_authoritative'};
/** A terminating residual below the minor unit. */
const DECIMAL_RESIDUAL: PlannerExactNumber = {kind: 'finite_decimal', value: '-0.0021'};

/** A ledger row of `broker-one` whose balances are all 0, so only its rounding residual can make a column speak. */
function ledgerRow(currency: string, rounding_delta: PlannerExactNumber): PlannerLedgerRow {
    const zeros = Object.fromEntries(LEDGER_FIELDS.map((field) => [field, '0']));
    return {...zeros, broker_id: 'broker-one', currency, rounding_delta} as unknown as PlannerLedgerRow;
}

describe('ledgerFields — the rounding column reads an exact number', () => {
    it('hides the rounding column when every residual is an exact zero', () => {
        const rows = [ledgerRow('EUR', ZERO_RESIDUAL), ledgerRow('USD', ZERO_RESIDUAL)];
        // Control: `all` brings every column back without reading a value.
        expect(ledgerFields(rows, true)).toEqual([...LEDGER_FIELDS]);

        const fields = ledgerFields(rows, false);
        expect(fields, 'the anchors are always shown').toEqual(expect.arrayContaining(['initial_selected', 'final_spendable']));
        expect(fields).not.toContain('rounding_delta');
    });

    it('shows it for a residual with no finite decimal, an exact ratio', () => {
        expect(ledgerFields([ledgerRow('EUR', RATIO_RESIDUAL), ledgerRow('USD', ZERO_RESIDUAL)], false)).toContain('rounding_delta');
    });

    it('shows it for a nonzero finite decimal on any row, not only the first', () => {
        expect(ledgerFields([ledgerRow('EUR', ZERO_RESIDUAL), ledgerRow('USD', DECIMAL_RESIDUAL)], false)).toContain('rounding_delta');
    });
});

describe('limitedEntries — the entries with a limit, read from the resolved request (F2 of project 67, M20)', () => {
    it('keeps every entry with a minimum or a maximum, in wire order, and nothing else', () => {
        const amount = {kind: 'amount', amount: {amount: '500', currency: 'EUR'}};
        const share = {kind: 'share', share: '0.35'};
        const resolved = {
            target_weights: [
                {kind: 'asset', asset_id: 'a-free', weight: '0.2', minimum: null, maximum: null},
                {kind: 'asset', asset_id: 'a-max', weight: '0.3', minimum: null, maximum: share},
                {kind: 'cash', broker_id: 'b-1', currency: 'USD', weight: '0', minimum: amount, maximum: null},
                {kind: 'asset', asset_id: 'a-min', weight: '0.5', minimum: amount, maximum: null},
            ],
        } as unknown as PlannerResolvedRequest;

        expect(limitedEntries(resolved)).toEqual([
            {kind: 'asset', id: 'a-max', brokerId: null, currency: null, minimum: null, maximum: share},
            {kind: 'cash', id: 'b-1:USD', brokerId: 'b-1', currency: 'USD', minimum: amount, maximum: null},
            {kind: 'asset', id: 'a-min', brokerId: null, currency: null, minimum: amount, maximum: null},
        ]);
    });

    it('a request without limits has no limited entry', () => {
        const resolved = {target_weights: [{kind: 'asset', asset_id: 'a', weight: '1', minimum: null, maximum: null}]} as unknown as PlannerResolvedRequest;
        expect(limitedEntries(resolved)).toEqual([]);
    });
});

describe('notesBesideLimitsBanner — the backend notes that would repeat the limits banner (F2, M20)', () => {
    const BOUNDS = {code: 'allocation.bounds_unsatisfiable'};
    const OTHER = {code: 'allocation.something_else'};
    const ENTRY: LimitedEntry = {kind: 'asset', id: 'a', brokerId: null, currency: null, minimum: {kind: 'share', share: '1'}, maximum: null};
    const result = (state: string) => ({result_state: state, issues: [BOUNDS, OTHER]}) as unknown as PlannerReadyResult;

    it('drops the per-entry «bounds unsatisfiable» notes when the banner lists the entries', () => {
        expect(notesBesideLimitsBanner(result('ready_infeasible'), [ENTRY])).toEqual([OTHER]);
    });

    it('keeps every note when there is no banner: no limit, or a state other than infeasible', () => {
        expect(notesBesideLimitsBanner(result('ready_infeasible'), [])).toEqual([BOUNDS, OTHER]);
        expect(notesBesideLimitsBanner(result('ready_no_incumbent'), [ENTRY])).toEqual([BOUNDS, OTHER]);
    });
});

/**
 * The plan's steps on the backend counter (F4a of project 67, step 1; contract §6.3). The fixture is the engine's own
 * answer to the G5 browser scenario, in the executable order the engine gives it: under the cash rule (lot CR) the euros
 * travel to the Broker that spends them (1), which changes them into dollars (2), then the purchases (3–7). The lists come
 * in their own order (the transfers apart); the steps follow `sequence` and nothing else, with no rule of the frontend
 * about which kind goes first. The purchases are not steps here: they are listed per Broker.
 */
describe('planSteps — the backend counter, transfers included (F4a step 1)', () => {
    const solution = browser.result.primary_solution as unknown as RebalancerSolution;

    it('plan steps follow the backend counter: the transfer, then the conversion it pays for', () => {
        const steps = planSteps(solution.funding_actions, solution.conversions, solution.transfers);
        expect(steps.map((step) => [step.kind, step.sequence])).toEqual([
            ['transfer', 1],
            ['conversion', 2],
        ]);
    });

    it('follows the counter, not the kind: a conversion numbered first comes first', () => {
        // The same two steps with their numbers swapped (built here, the fixture untouched).
        const conversions = solution.conversions.map((row) => (row.sequence === null ? row : {...row, sequence: 1}));
        const transfers = solution.transfers.map((row) => ({...row, sequence: 2}));
        const steps = planSteps(solution.funding_actions, conversions, transfers);
        expect(steps.map((step) => [step.kind, step.sequence])).toEqual([
            ['conversion', 1],
            ['transfer', 2],
        ]);
    });

    it('a plan of transfers only is still a plan', () => {
        const transfersOnly = {funding_actions: [], conversions: [], order_rows: [], transfers: solution.transfers};
        expect(hasPlanSteps(transfersOnly)).toBe(true);
        expect(hasPlanSteps({funding_actions: [], conversions: [], order_rows: [], transfers: []})).toBe(false);
        // The PAC's solution carries no transfers at all.
        expect(hasPlanSteps({funding_actions: [], conversions: [], order_rows: []})).toBe(false);
    });
});

/**
 * The allocation's rows (F4a of project 67, step 3; contract §6.2): one per Asset, one per cash entry, then the
 * «uninvested» row, last. On the engine's G5 answer: seven Assets, two cash entries with a target, the uninvested row. The
 * rows are the published ones, in the published order: nothing is computed. The PAC's solution has its Assets only.
 */
describe('allocationRows — before, target and after (F4a step 3)', () => {
    const solution = browser.result.primary_solution as unknown as RebalancerSolution;

    it('before, target and after rows include cash entries and the uninvested row’s two parts, last (TL-5)', () => {
        const rows = allocationRows(solution);
        expect(rows.map((row) => row.kind)).toEqual([...solution.asset_rows.map(() => 'asset'), ...solution.cash_rows.map(() => 'cash'), 'untargeted_cash', 'costs']);
        expect(rows.map((row) => row.id)).toEqual([...solution.asset_rows.map((row) => row.asset_id), ...solution.cash_rows.map((row) => `cash:${row.broker_id}:${row.currency}`), 'untargeted_cash', 'costs']);
        expect(rows.at(-2)?.row).toBe(solution.uninvested_row.untargeted_cash);
        expect(rows.at(-1)?.row).toBe(solution.uninvested_row.costs);
    });

    it('the PAC has its Assets only', () => {
        const rows = allocationRows({asset_rows: solution.asset_rows});
        expect(rows.map((row) => row.kind)).toEqual(solution.asset_rows.map(() => 'asset'));
    });
});

/**
 * The balances' columns per Tool (F4a of project 67, step 5; contract §6.5). The Rebalancer moves money between Brokers as
 * transfers, published as `transfer_in` and `transfer_out`; the PAC never does, and keeps its fourteen columns, four of them
 * «always 0 in a PAC». The keys are tested, never the texts.
 */
describe('the ledger columns per Tool (F4a step 5)', () => {
    const PAC_SHARED = 'tools.pacAllocator.planner.result.ledger';
    const REBALANCER = 'tools.portfolioRebalancer.planner.result.ledger';

    it('PAC ledger still marks four columns as always zero, and has no transfer column', () => {
        expect(ledgerFieldList('pac')).toEqual([...LEDGER_FIELDS]);
        expect(ledgerFieldList('pac')).not.toEqual(expect.arrayContaining(['transfer_in']));
        const alwaysZero = ledgerFieldList('pac').filter((field) => ledgerHelpKey(field, 'pac') === `${PAC_SHARED}.help.alwaysZero`);
        expect(alwaysZero).toEqual(['gross_sell_credit', 'sell_fees', 'broker_withheld_tax', 'self_reserved_tax']);
        expect(ledgerHelpKey('funding_in', 'pac')).toBe(`${PAC_SHARED}.help.funding_in`);
        expect(ledgerLabelKey('funding_in')).toBe(`${PAC_SHARED}.fields.funding_in`);
    });

    it('the Rebalancer has the transfer columns after the funding ones, in the order of the ledger identity', () => {
        const fields = ledgerFieldList('rebalancer');
        expect(fields.slice(0, 5)).toEqual(['initial_selected', 'funding_in', 'funding_out', 'transfer_in', 'transfer_out']);
        expect(fields.filter((field) => !field.startsWith('transfer_'))).toEqual([...LEDGER_FIELDS]);
        expect(ledgerLabelKey('transfer_in')).toBe(`${REBALANCER}.fields.transfer_in`);
        expect(ledgerLabelKey('transfer_out')).toBe(`${REBALANCER}.fields.transfer_out`);
    });

    it('the Rebalancer help: deposits, no funding out, its transfers, sales at 0 with «Invest only»; never the PAC note', () => {
        const help = Object.fromEntries(ledgerFieldList('rebalancer').map((field) => [field, ledgerHelpKey(field, 'rebalancer')]));
        expect(Object.values(help)).not.toContain(`${PAC_SHARED}.help.alwaysZero`);
        expect(help.funding_in).toBe(`${REBALANCER}.help.funding_in`);
        expect(help.funding_out).toBe(`${REBALANCER}.help.funding_out`);
        expect(help.transfer_in).toBe(`${REBALANCER}.help.transfer_in`);
        expect(help.transfer_out).toBe(`${REBALANCER}.help.transfer_out`);
        for (const field of ['gross_sell_credit', 'sell_fees', 'broker_withheld_tax', 'self_reserved_tax']) expect(help[field]).toBe(`${REBALANCER}.help.alwaysZeroInvestOnly`);
        expect(help.buy_debit).toBe(`${PAC_SHARED}.help.buy_debit`);
    });

    it('every name and help the two Tools may read is in the catalogue', () => {
        for (const text of ['pac', 'rebalancer'] as const)
            for (const field of ledgerFieldList(text)) {
                expect(catalogueMessage(ledgerLabelKey(field)), ledgerLabelKey(field)).toBeTypeOf('string');
                expect(catalogueMessage(ledgerHelpKey(field, text)), ledgerHelpKey(field, text)).toBeTypeOf('string');
            }
    });

    it("on the engine's G5 answer the transfer columns speak", () => {
        const rows = (browser.result.primary_solution as unknown as RebalancerSolution).ledger_rows;
        expect(ledgerFields(rows, false, ledgerFieldList('rebalancer'))).toEqual(expect.arrayContaining(['transfer_in', 'transfer_out']));
        expect(ledgerFields(rows, true, ledgerFieldList('rebalancer'))).toEqual(ledgerFieldList('rebalancer'));
    });
});

/**
 * F4a of project 67, step 6 (the D4 follow-up): a Rebalancer tie-break can be unfinished without any limit, its plan set
 * aside by the exact comparison; its «Status» help says so. The PAC keeps its own (its cascade has no such stage).
 */
describe('the «Status» help of the solver stages', () => {
    it("is the Rebalancer's own, and the PAC keeps the shared one", () => {
        expect(proofStatusHelpKey('rebalancer')).toBe('tools.portfolioRebalancer.planner.result.proof.help.status');
        expect(proofStatusHelpKey('pac')).toBe('tools.pacAllocator.planner.result.proof.help.status');
    });
});

/**
 * F4a of project 67, step 7: the Rebalancer's «Proven optimal» badge says what is proven, its objective (the score, or
 * the distance then the money lost), not «objective by objective in the order chosen in Strategy»: its tie-breaks may
 * stop earlier, and they only choose among plans as good. Every other help is shared; the PAC keeps its own.
 */
describe('resultBadges — the Rebalancer proof badge', () => {
    const proven: ProofCase = {proof: 'optimal_proven', outcome: 'incumbent_found', stop_reason: 'time_limit', help: '', why: ''};
    it('names the objective it proves, the tie-breaks apart', () => {
        const help = badgeById(resultBadges(readyResult(proven), 'rebalancer'), 'proof').help;
        expect(help.key).toBe('tools.portfolioRebalancer.planner.result.badges.help.optimalProven');
        expect(catalogueMessage(help.key), 'the key is in the catalogue').toBeTypeOf('string');
        expect(badgeById(resultBadges(readyResult(proven)), 'proof').help.key, 'the PAC keeps its own').toBe('tools.pacAllocator.planner.result.badges.help.optimalProven');
    });
});

/**
 * Lot MG of project 67 (the developer's «ottimo dimostrato» / «ottimo locale (entro X)»): a plan not proven reads «local
 * optimum», with its margin in parentheses when the backend publishes one (`proof.margin`, in the valuation currency), and
 * its help says what the margin is, with «should» (the bound is the solver's). The margin is money: personal, masked with
 * privacy on. Without a margin, «local optimum» alone. Keys are tested, never the texts.
 */
describe('resultBadges — a result with no plan is not a «local optimum» (lot MG)', () => {
    it('the no-plan states keep their own name for the proof', () => {
        for (const c of CASES.filter((item) => item.outcome === 'no_incumbent')) expect(badgeById(resultBadges(readyResult(c)), 'proof').key, caseTitle(c)).toBe('tools.pacAllocator.planner.result.badges.noPlanNotProven');
        expect(catalogueMessage('tools.pacAllocator.planner.result.badges.noPlanNotProven')).toBeTypeOf('string');
    });
});

describe('resultBadges — «local optimum» and its margin (lot MG)', () => {
    const digits = catalogCurrencyDigits([{currency: 'EUR', minor_unit: '0.01'}]);
    const notProven = (margin: {amount: string; currency: string} | null) =>
        ({outcome: 'incumbent_found', stop_reason: 'completed', proof: {kind: 'not_proven', reason_code: 'allocation.proof_not_confirmed', margin}, primary_solution: {validation: 'decimal_verified'}}) as unknown as PlannerReadyResult;

    it('names the margin in the badge, and the help says what it is', () => {
        const badge = badgeById(resultBadges(notProven({amount: '0.14', currency: 'EUR'}), 'rebalancer', digits), 'proof');
        expect(badge.key).toBe('tools.pacAllocator.planner.result.badges.notProvenWithin');
        expect(badge.values?.margin).toBe(formatPlannerMoneyPlain('0.14', 'EUR', {digits}));
        expect(badge.help.extra?.key).toBe('tools.pacAllocator.planner.result.badges.help.margin');
        expect(badge.help.extra?.values?.margin).toBe(badge.values?.margin);
        for (const key of [badge.key, badge.help.extra?.key as string]) expect(catalogueMessage(key), key).toBeTypeOf('string');
    });

    it('without a margin, «local optimum» alone', () => {
        const badge = badgeById(resultBadges(notProven(null), 'rebalancer', digits), 'proof');
        expect(badge.key).toBe('tools.pacAllocator.planner.result.badges.notProven');
        expect([badge.values, badge.help.extra]).toEqual([undefined, undefined]);
    });

    it('the margin is personal: masked with privacy on', () => {
        setPrivacyEnabled(true);
        try {
            expect(badgeById(resultBadges(notProven({amount: '0.14', currency: 'EUR'}), 'rebalancer', digits), 'proof').values?.margin).toContain(PRIVACY_PLACEHOLDER);
        } finally {
            setPrivacyEnabled(false);
        }
    });
});
