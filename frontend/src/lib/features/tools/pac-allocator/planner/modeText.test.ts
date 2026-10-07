// @vitest-environment node
/**
 * modeText — the plural count of a whole-quantity step, in the words of an order mode (Vitest, node).
 *
 * Subject (P1). `modeIncrementText` names the increment of a Broker order mode, the step every
 * proposed order is a multiple of. For a whole-quantity mode it calls
 * `tools.pacAllocator.planner.brokers.stepUnits`, a message that picks its noun with
 * `{count, plural, one {…} other {…}}`. The figure it shows is `formatPlannerPlainDecimal` of the
 * canonical step, so the count must be the plural count of those same digits:
 * `plannerPlainDecimalCount` (`format.ts`), the integer part plus 0.5 when the shown digits keep a
 * fraction. The call passes `Number(canonical)` instead. A step with twenty fraction digits,
 * `1.00000000000000000001`, becomes the double 1 and selects the singular next to a figure that
 * shows a fraction. `0.001` counts 0.001, while its twin counts 0.5. R7 fixed the same defect in
 * `result/text.ts` (the `stepUnits` of a result instruction); this is the Broker-side site it did
 * not reach. Red today at those two steps, privacy off and on. `1` and `1.5`, which `Number()`
 * reads correctly, are green before and after the fix.
 *
 * Wiring. A recording translator stands in for `$t`. A whole-quantity mode must make exactly one
 * call, at its key, carrying the formatter's figure and its count and nothing else, and must return
 * the translator's answer. The expected values come from the formatter functions, so literal
 * anchors keep the check from being circular: `1` is shown as `1`, counts 1, and is the only
 * singular; `1.00000000000000000001` is shown with all twenty fraction digits and does not count 1.
 * A control checks that the anchors agree with the formatter, so a site that passes the twin meets
 * both and the red is the site's alone. Counts are compared with `Object.is` (`toBe`), so a NaN
 * would match NaN.
 *
 * Privacy. A step is a Broker parameter, not wealth, so it is public. With privacy on, its figure
 * and its count stay in the clear. This is what tells `plannerPlainDecimalCount` apart from
 * `plannerQuantityCount`, the personal twin, which would count NaN there.
 *
 * A monetary-amount step is an amount of money: the text is the price formatter's output, with no
 * translator call.
 *
 * Environment. The formatter graph imports the currency catalogue store, which imports the API
 * client. The client is inert, so a price keeps its bare currency code. The shared
 * `$app/environment` mock reports `browser: false`, so the privacy flag never touches
 * `localStorage`.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

// A monetary step is formatted as a price, through the currency catalogue store, which imports the
// API client. Nothing here loads the catalogue: every call resolves to nothing.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {canonicalInput} from './decimal';
import type {DraftMode, ModeKind} from './draft.svelte';
import {formatPlannerPlainDecimal, formatPlannerPricePlain, plannerPlainDecimalCount, plannerQuantityCount} from './format';
import {modeIncrementText, type PlannerTranslate} from './modeText';

const KEY = 'tools.pacAllocator.planner.brokers.stepUnits';

/** Twenty fraction digits: every one is shown, while `Number()` reads the value as the double 1. */
const TWENTY_DIGIT_ONE = '1.00000000000000000001';

/** Moves the flag, and proves it moved. */
function privacy(on: boolean): void {
    setPrivacyEnabled(on);
    expect(isPrivacyEnabled(), 'control: the flag').toBe(on);
}

afterEach(() => {
    // The flag is module-level state shared by every test in this file.
    setPrivacyEnabled(false);
});

/** An order mode of a Broker. The increment text reads its kind, its step and, for an amount, its currency. */
function orderMode(kind: ModeKind, step: string): DraftMode {
    return {key: 'mode-1', currency: 'EUR', kind, step, fixedFee: '0', ratePercent: '0', floor: '0', cap: ''};
}

/** One call of the translator, as the site made it. */
interface TranslateCall {
    key: string;
    fallback: string | undefined;
    values: Record<string, unknown>;
}

/** What the recording translator answers: the text is the translator's answer, never one built beside it. */
function answer(key: string): string {
    return `⟨${key}⟩`;
}

/** A translator that records every call and answers with the key it was asked for. */
function recorder(): {calls: TranslateCall[]; translate: PlannerTranslate} {
    const calls: TranslateCall[] = [];
    const translate: PlannerTranslate = (key, options) => {
        calls.push({key, fallback: options?.default, values: {...options?.values}});
        return answer(key);
    };
    return {calls, translate};
}

/** A whole-quantity step, with its literal anchors: the figure shown and its count. */
interface StepCase {
    step: string;
    shown: string;
    count: number;
    why: string;
}

const STEP_CASES: StepCase[] = [
    {step: '1', shown: '1', count: 1, why: 'one unit, the singular'},
    {step: '1.5', shown: '1.5', count: 1.5, why: 'integer part 1, plus 0.5 for the fraction shown'},
    {step: '0.001', shown: '0.001', count: 0.5, why: 'integer part 0, plus 0.5 for the fraction shown, not the double 0.001'},
    {step: TWENTY_DIGIT_ONE, shown: TWENTY_DIGIT_ONE, count: 1.5, why: 'twenty fraction digits are shown, so the fraction counts, not the double 1'},
];

/** The one call a whole-quantity step makes, checked against the anchors and against the formatter. */
function checkStep(c: StepCase): void {
    const canonical = canonicalInput(c.step);
    expect(canonical, 'control: the step reads as a decimal').not.toBeNull();
    const {calls, translate} = recorder();
    const text = modeIncrementText(translate, orderMode('whole_quantity', c.step));
    expect(
        calls.map((call) => call.key),
        'one call, at its key',
    ).toEqual([KEY]);
    expect(text, "the text is the translator's answer").toBe(answer(KEY));
    const {values} = calls[0];

    // Literal anchors, independent of the formatter.
    expect(values.step, 'the figure, as shown').toBe(c.shown);
    expect(values.count === 1, 'the singular exactly when the figure shown is 1').toBe(c.shown === '1');
    expect(values.count, `its count: ${c.why}`).toBe(c.count);

    // The formatter's figure for the canonical step, and the plural count of those same digits.
    expect(values.step, 'formatPlannerPlainDecimal of the canonical step').toBe(formatPlannerPlainDecimal(canonical));
    expect(values.count, 'plannerPlainDecimalCount of the same canonical step').toBe(plannerPlainDecimalCount(canonical));
    expect(values, "the formatter's figure and its count, nothing else").toEqual({step: formatPlannerPlainDecimal(canonical), count: plannerPlainDecimalCount(canonical)});
}

describe('modeIncrementText — a whole-quantity step passes the plural count of the figure it shows', () => {
    it('control: the high-precision step tests what it claims — Number() reads it as 1, the display shows its twenty fraction digits', () => {
        expect(TWENTY_DIGIT_ONE.split('.')[1], 'twenty fraction digits').toHaveLength(20);
        expect(Number(TWENTY_DIGIT_ONE), 'as a double, it is 1').toBe(1);
        expect(formatPlannerPlainDecimal(TWENTY_DIGIT_ONE), 'every digit is shown').toBe(TWENTY_DIGIT_ONE);
        expect(plannerPlainDecimalCount(TWENTY_DIGIT_ONE), 'so its count is not the singular 1').not.toBe(1);
    });

    it('control: the anchors agree with the formatter, privacy off and on, so a site that passes the twin meets both', () => {
        for (const on of [false, true]) {
            privacy(on);
            for (const c of STEP_CASES) {
                const canonical = canonicalInput(c.step);
                expect(formatPlannerPlainDecimal(canonical), `privacy ${on ? 'on' : 'off'}, step ${c.step}: the figure`).toBe(c.shown);
                expect(plannerPlainDecimalCount(canonical), `privacy ${on ? 'on' : 'off'}, step ${c.step}: the count`).toBe(c.count);
            }
        }
    });

    for (const c of STEP_CASES) {
        it(`privacy off: step ${c.step} is shown as ${c.shown} and counts ${c.count}`, () => {
            privacy(false);
            checkStep(c);
        });
    }
});

describe('modeIncrementText — privacy on: a step is public, so its figure and its count stay in the clear', () => {
    for (const c of STEP_CASES) {
        it(`privacy on: step ${c.step} is shown as ${c.shown} and counts ${c.count}`, () => {
            privacy(true);
            // What tells the public twin from the personal one: here the personal twin counts NaN.
            expect(plannerQuantityCount(c.step), 'control: the personal twin would count NaN').toBeNaN();
            checkStep(c);
        });
    }
});

describe('modeIncrementText — a monetary-amount step is an amount of money, not a count', () => {
    for (const step of ['0.01', '1', '1.5']) {
        it(`step ${step} EUR: the price formatter's text, with no translator call`, () => {
            privacy(false);
            const {calls, translate} = recorder();
            const text = modeIncrementText(translate, orderMode('monetary_amount', step));
            expect(calls, 'no translator call').toEqual([]);
            expect(text, "the price formatter's text for the step").toBe(formatPlannerPricePlain(step, 'EUR'));
            expect(text, 'control: a figure, not the empty cell').toMatch(/\d/);
        });
    }
});
