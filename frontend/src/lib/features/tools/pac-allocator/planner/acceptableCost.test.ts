/**
 * The table «Maximum acceptable cost» in the page (R1-F (b) of project 67): `acceptableCost.ts`.
 *
 * Ported case by case from the backend's tests it replaces (`test_financial_math/test_acceptable_cost.py` and the table
 * half of `test_pac_planner_preview.py`, B4 tests 3–6, 12 and the consultant's Q1), so the figures provably do not move:
 *   - the rows are 1 %, 2.5 %, 5 % and 10 % of the total, to two significant digits, half up (on 13 457: 130, 340, 670,
 *     1 300); the 5 % row is the reference;
 *   - a cell is `2·λ·d²/F`;
 *   - «Custom»: `λ = x·F / (2·d_ref²)` with the row's **shown** figure, to six significant digits, and the column and the
 *     euros computed back from that λ.
 * Values are compared exactly, as rationals (cross-multiplied), never through their text.
 */
import {describe, expect, it} from 'vitest';
import {acceptableCostTable, lambdaFromReferenceAmount, LAMBDA_SIGNIFICANT_DIGITS, referenceAmountFor, referenceMisplaced, type FidelityLevelWeights} from './acceptableCost';
import type {PlannerExactMoney, PlannerExactNumber} from './types';

const decimal = (value: string): PlannerExactNumber => ({kind: 'finite_decimal', value});
const eur = (value: string): PlannerExactMoney => ({value: decimal(value), currency: 'EUR'});
const LEVELS: FidelityLevelWeights = {cost_aware: decimal('0.25'), balanced: decimal('1'), faithful: decimal('4')};

/** An exact number as `[numerator, denominator]`. */
function parts(value: PlannerExactNumber): [bigint, bigint] {
    if (value.kind === 'exact_ratio') return [BigInt(value.numerator), BigInt(value.denominator)];
    const negative = value.value.startsWith('-');
    const [whole, fraction = ''] = value.value.replace('-', '').split('.');
    return [BigInt(whole + fraction) * (negative ? -1n : 1n), 10n ** BigInt(fraction.length)];
}

/** Whether an amount equals `numerator / denominator` exactly. */
function is(amount: PlannerExactMoney | null | undefined, numerator: bigint | number, denominator: bigint | number = 1n): boolean {
    if (!amount) return false;
    const [n, d] = parts(amount.value);
    return n * BigInt(denominator) === BigInt(numerator) * d;
}

function gcd(a: bigint, b: bigint): bigint {
    let [x, y] = [a < 0n ? -a : a, b];
    while (y !== 0n) [x, y] = [y, x % y];
    return x;
}

/** A table's column, each cell as text of its exact value, reduced (`25/4` for a ratio, `12/5` for 2.4). */
function column(rows: ReturnType<typeof acceptableCostTable>, level: 'misplaced' | 'cost_aware' | 'balanced' | 'faithful' | 'custom'): string[] {
    return (rows ?? []).map((row) => {
        const amount = row[level];
        if (!amount) return '—';
        const [n, d] = parts(amount.value);
        const g = gcd(n, d) || 1n;
        return d / g === 1n ? (n / g).toString() : `${n / g}/${d / g}`;
    });
}

describe('the rows: 1 %, 2.5 %, 5 %, 10 % of the total, to two significant digits', () => {
    it.each([
        ['13457', ['130', '340', '670', '1300']],
        ['20000', ['200', '500', '1000', '2000']],
        // Below 100 €: two significant digits, cents included (1 % of 57.30 is 0.573 → 0.57).
        ['57.30', ['57/100', '7/5', '29/10', '57/10']],
    ])('on %s', (total, rows) => {
        const table = acceptableCostTable(eur(total), LEVELS, null);
        expect(column(table, 'misplaced')).toEqual(rows);
        expect(table?.map((row) => row.reference)).toEqual([false, false, true, false]);
        expect(table?.every((row) => row.misplaced.currency === 'EUR')).toBe(true);
    });

    it.each([
        // [total, its 1 % row]: 134.57 → 130, 335 → 340 (half goes up), 995 → 1 000 (carries to a new digit), one digit
        // stays, cents keep two digits (0.0456 → 0.046).
        ['13457', 130n, 1n],
        ['33500', 340n, 1n],
        ['99500', 1000n, 1n],
        ['700', 7n, 1n],
        ['4.56', 46n, 1000n],
    ])('half up, on single values: one percent of %s', (total, numerator, denominator) => {
        expect(is(acceptableCostTable(eur(total), LEVELS, null)?.[0].misplaced, numerator, denominator)).toBe(true);
    });

    it('the reference row is the 5 % one, as shown', () => {
        expect(is(referenceMisplaced(eur('13457')), 670)).toBe(true);
        expect(referenceMisplaced(eur('0'))).toBeNull();
    });
});

describe('a cell is 2·λ·d²/F', () => {
    it('on 20 000 €: 1 / 4 / 16, 25/4 / 25 / 100, 25 / 100 / 400, 100 / 400 / 1 600 (B4 test 3)', () => {
        const table = acceptableCostTable(eur('20000'), LEVELS, null);
        expect(column(table, 'cost_aware')).toEqual(['1', '25/4', '25', '100']);
        expect(column(table, 'balanced')).toEqual(['4', '25', '100', '400']);
        expect(column(table, 'faithful')).toEqual(['16', '100', '400', '1600']);
        expect(column(table, 'custom')).toEqual(['—', '—', '—', '—']);
    });

    it('reads a level λ given as an exact ratio', () => {
        const levels: FidelityLevelWeights = {...LEVELS, cost_aware: {kind: 'exact_ratio', numerator: '1', denominator: '3', display_decimal: '0.333333', display_scale: 6, display_authority: 'non_authoritative'}};
        expect(column(acceptableCostTable(eur('20000'), levels, null), 'cost_aware')).toEqual(['4/3', '25/3', '100/3', '400/3']);
    });

    it('no table without a positive total or with a level λ that is not positive', () => {
        expect(acceptableCostTable(eur('0'), LEVELS, null)).toBeNull();
        expect(acceptableCostTable(eur('-5'), LEVELS, null)).toBeNull();
        expect(acceptableCostTable(eur('20000'), {...LEVELS, balanced: decimal('0')}, null)).toBeNull();
    });
});

describe('«Custom»', () => {
    it('60 € on the reference row of 20 000 € give λ = 0.6 and the column 2.4 / 15 / 60 / 240 (B4 test 4)', () => {
        const lambda = lambdaFromReferenceAmount(eur('20000'), '60');
        expect(lambda).toBe('0.6');
        expect(column(acceptableCostTable(eur('20000'), LEVELS, lambda), 'custom')).toEqual(['12/5', '15', '60', '240']);
    });

    it('λ = 0.6 gives back 60 € and the same column: the round trip is exact (B4 test 5)', () => {
        expect(is(referenceAmountFor(eur('20000'), '0.6'), 60)).toBe(true);
        expect(column(acceptableCostTable(eur('20000'), LEVELS, '0.6'), 'custom')).toEqual(['12/5', '15', '60', '240']);
    });

    it('λ is computed on the row as shown, 670, never the exact 5 % (672.85), to six significant digits (B4 test 6, Q1)', () => {
        expect(LAMBDA_SIGNIFICANT_DIGITS).toBe(6);
        // 60·13 457/(2·670²) = 40 371/44 890 = 0.89933170…
        expect(lambdaFromReferenceAmount(eur('13457'), '60')).toBe('0.899332');
    });

    it('the round trip is stable: the euros come back as 60.00 € to the cent, and λ sent back gives the same column (Q1)', () => {
        const lambda = lambdaFromReferenceAmount(eur('13457'), '60') as string;
        const amount = referenceAmountFor(eur('13457'), lambda);
        const [n, d] = parts(amount!.value);
        // 2·0.899332·670²/13 457, half up to the cent.
        expect((n * 100n * 2n + d) / (2n * d)).toBe(6000n);
        const again = lambdaFromReferenceAmount(eur('13457'), '60');
        expect(column(acceptableCostTable(eur('13457'), LEVELS, again), 'custom')).toEqual(column(acceptableCostTable(eur('13457'), LEVELS, lambda), 'custom'));
    });

    it.each([
        // λ = x·20 000/(2·1 000²) = x/100, to six significant digits, half up.
        ['12345650', '123457'],
        ['99.99995', '1'],
        // A tiny amount never gives λ = 0: 0.01 € on 200 000 € (row 10 000) is 1e-5 (Q1).
    ])('six significant digits, half up: %s € on 20 000 € give λ %s', (euros, lambda) => {
        expect(lambdaFromReferenceAmount(eur('20000'), euros)).toBe(lambda);
    });

    it('a tiny amount never gives a zero λ: 0.01 € on 200 000 € is 0.00001 (Q1)', () => {
        expect(lambdaFromReferenceAmount(eur('200000'), '0.01')).toBe('0.00001');
    });

    it('reads the euros as typed, grouping and decimal comma tolerated', () => {
        expect(lambdaFromReferenceAmount(eur('20000'), '1.234,5')).toBe(lambdaFromReferenceAmount(eur('20000'), '1234.5'));
    });

    it('no λ for euros that are not a positive figure, without a positive total, or past what the plan accepts', () => {
        for (const euros of ['', '0', '-1', 'abc']) expect(lambdaFromReferenceAmount(eur('20000'), euros)).toBeNull();
        expect(lambdaFromReferenceAmount(eur('0'), '60')).toBeNull();
        // λ = 1e98: 99 digits, beyond the 96 characters of the plan's decimal.
        expect(lambdaFromReferenceAmount(eur('20000'), '1' + '0'.repeat(100))).toBeNull();
        expect(lambdaFromReferenceAmount(eur('20000'), '1' + '0'.repeat(90))).toBe('1' + '0'.repeat(88));
    });

    it('no column and no euros for a λ that is not a positive decimal', () => {
        for (const lambda of [null, '', '0', '-0.5']) {
            expect(column(acceptableCostTable(eur('20000'), LEVELS, lambda), 'custom')).toEqual(['—', '—', '—', '—']);
            expect(referenceAmountFor(eur('20000'), lambda)).toBeNull();
        }
    });
});

describe('a total with no decimal form (an FX rate)', () => {
    // 5 300 + 4 000 000/1 085 = 1 950 100/217: the 7 and the 31 of 1 085 stay in the denominator.
    const total: PlannerExactMoney = {
        value: {kind: 'exact_ratio', numerator: '1950100', denominator: '217', display_decimal: '8986.635944700460829493', display_scale: 18, display_authority: 'non_authoritative'},
        currency: 'EUR',
    };

    it('is read from its numerator and denominator, and its cells are exact ratios', () => {
        const table = acceptableCostTable(total, LEVELS, null);
        expect(column(table, 'misplaced')).toEqual(['90', '220', '450', '900']);
        expect(column(table, 'balanced')).toEqual(['35154/19501', '210056/19501', '878850/19501', '3515400/19501']);
        const cell = table?.[0].balanced.value;
        expect(cell?.kind).toBe('exact_ratio');
        if (cell?.kind === 'exact_ratio') expect([cell.display_decimal, cell.display_authority]).toEqual(['1.80267678580585611', 'non_authoritative']);
    });

    it('«Custom» on it: 60 € give λ = 1.33135, and their euros 468 022 779/7 800 400', () => {
        const lambda = lambdaFromReferenceAmount(total, '60');
        expect(lambda).toBe('1.33135');
        expect(is(referenceAmountFor(total, lambda), 468022779n, 7800400n)).toBe(true);
    });
});
