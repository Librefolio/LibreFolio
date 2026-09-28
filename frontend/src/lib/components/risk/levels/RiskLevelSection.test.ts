// @vitest-environment jsdom
/**
 * RiskLevelSection — the frame around one risk level (Vitest + jsdom).
 *
 * What is pinned: how the frame names a measurement that did not come back whole,
 * in `{testId}-health`. The caller hands over identifiers and the frame words
 * them, from one of two sources: the entry's own `label` — an i18n key, used
 * where the analytic's name would be ambiguous, since L1 asks `historical_var`
 * once for a day and once for a month — else the analytic's catalogue name, keyed
 * by `analyticNameKey`, the camelCase rule the notice above the levels shares.
 *
 * A snake_case code is the case the rule exists for: `historical_var` lives at
 * `risk.analytics.historicalVar.name`. A frame that built the key from the raw
 * code would find nothing and print `historical_var` through its `{default: code}`
 * fallback — and `partialNotice.test.ts` could not see it, because it tests the
 * rule, not whether this frame uses it.
 *
 * Expected text is resolved from the shipped catalogue through the same `$_` the
 * component uses; no sentence is written down here. The harness case guards the
 * ways that could go vacuous: a key missing from the catalogue (svelte-i18n
 * echoes the id back), a name that reads like the raw code (then the fallback
 * would pass for it), an uncamelled key that happens to exist (then a frame
 * without the rule would pass too), and a label that reads like the analytic's
 * name (then which branch rendered has no answer).
 *
 * Mounted alone, with props only: no controller, no store, no mock.
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';

import {render, screen, setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';

import type {ResultHealth} from './levelHelpers';
import RiskLevelSection from './RiskLevelSection.svelte';

const TEST_ID = 'risk-level-under-test';
/** A multi-word analytic code: the one shape the camelCase rule changes. */
const CODE = 'historical_var';
const NAME_KEY = 'risk.analytics.historicalVar.name';
/** The key a frame would build from the raw code, without the camelCase rule. */
const UNCAMELLED_KEY = `risk.analytics.${CODE}.name`;
const FAILED_KEY = 'risk.states.failed';
const UNAVAILABLE_KEY = 'risk.states.unavailable';
/** The label L1 gives its one-day VaR, the instance the analytic's name alone cannot tell from the month. */
const DAY_LABEL = 'risk.levels.l1.rows.day';

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence as the component formats it: `$_`, no values. */
function resolve(key: string): string {
    return normalize(get(_)(key));
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The frame, open (it is not collapsible), holding `health` and nothing else; its health line. */
function healthLine(health: ResultHealth[]): HTMLElement {
    render(RiskLevelSection, {props: {title: 'Synthetic level title', level: 1, testId: TEST_ID, health}});
    const line = screen.getByTestId(`${TEST_ID}-health`);
    // Barrier: one entry per measurement given, so the text below is about these and nothing else.
    expect(line, 'the health line does not hold one entry per measurement').toHaveAttribute('data-count', String(health.length));
    return line;
}

beforeAll(async () => {
    await setupI18n('en');
});

describe('RiskLevelSection — the harness itself', () => {
    it('resolves every key it compares against, and none of them reads like another outcome', () => {
        for (const key of [NAME_KEY, FAILED_KEY, UNAVAILABLE_KEY, DAY_LABEL]) {
            expect(typeof at(en, key), `${key} is missing from en.json`).toBe('string');
            expect(resolve(key), `${key} does not resolve: the catalogue is not loaded`).not.toBe(key);
        }
        const name = resolve(NAME_KEY);
        // A missed key prints the raw code (`{default: code}`): were the name the code, a miss would pass.
        expect(name, `${NAME_KEY} reads like the raw code: a missed key could not be told from a found one`).not.toBe(CODE);
        // The key a frame without the rule would build must miss, or that frame would find a name too.
        expect(get(_)(UNCAMELLED_KEY), `${UNCAMELLED_KEY} exists after all: a frame that skipped the camelCase rule would still be named`).toBe(UNCAMELLED_KEY);
        expect(resolve(DAY_LABEL), 'the label reads like the analytic name: which of the two rendered could not be told').not.toBe(name);
    });
});

describe('RiskLevelSection — how a measurement that did not come back whole is named', () => {
    it('names a failed snake_case measurement by its catalogue name, found through the camelCase rule', () => {
        const line = healthLine([{instanceId: 'synthetic-var', code: CODE, status: 'failed'}]);
        expect(normalize(line.textContent), `${CODE} is not named by ${NAME_KEY}: the frame built its key without analyticNameKey`).toBe(`${resolve(NAME_KEY)}: ${resolve(FAILED_KEY)}`);
    });

    it('names a labelled measurement by its label, not by the analytic behind it', () => {
        const line = healthLine([{instanceId: 'synthetic-day-var', code: CODE, status: 'unavailable', label: DAY_LABEL}]);
        expect(normalize(line.textContent), `the entry is not named by its label ${DAY_LABEL}`).toBe(`${resolve(DAY_LABEL)}: ${resolve(UNAVAILABLE_KEY)}`);
    });
});
