// @vitest-environment jsdom
/**
 * RiskFreeRateField — the reader's risk-free rate, under the period line of every risk page (RN-21, Vitest + jsdom).
 *
 * The consultant's decisions (17/11/2026), pinned here:
 *   1. **It shows the shared value**, 0 % until the reader sets one, in the reader's decimal separator.
 *   2. **It applies on Enter or on leaving the field**, never on a keystroke: a half-typed «2,» asks nothing.
 *   3. **A text the engine would refuse is not taken**: the field says so (`aria-invalid`) and the shared value stays;
 *      Escape brings the shared value back.
 *   4. **One value for every page**: a second field shows what the first set, and the store holds it.
 *   5. **The hint is in the ⓘ only**, under its own key.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

const storage = vi.hoisted(() => {
    const backing = new Map<string, string>();
    Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        writable: true,
        value: {
            getItem: (key: string) => backing.get(key) ?? null,
            setItem: (key: string, value: string) => void backing.set(key, String(value)),
            removeItem: (key: string) => void backing.delete(key),
            clear: () => backing.clear(),
        },
    });
    return {backing};
});

import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import {riskFreeRate} from './riskFreeRateStore.svelte';
import RiskFreeRateField from './RiskFreeRateField.svelte';

let userSeq = 0;

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    storage.backing.clear();
    transitionClientSession(`risk-free-field-u${++userSeq}`);
});

afterEach(() => cleanup());

const input = (index = 0): HTMLInputElement => screen.getAllByTestId('risk-free-rate')[index] as HTMLInputElement;

describe('RiskFreeRateField', () => {
    it('shows 0 for a reader who never set a rate', () => {
        render(RiskFreeRateField);
        expect(input().value).toBe('0');
        expect(input()).toHaveAttribute('aria-invalid', 'false');
    });

    it('applies on Enter, and not on a keystroke', async () => {
        render(RiskFreeRateField);
        await fireEvent.input(input(), {target: {value: '2,5'}});
        expect(riskFreeRate.percent, 'a keystroke asks nothing').toBe(0);

        await fireEvent.keyDown(input(), {key: 'Enter'});
        expect(riskFreeRate.percent).toBe(2.5);
    });

    it('applies on leaving the field', async () => {
        render(RiskFreeRateField);
        await fireEvent.input(input(), {target: {value: '3.25'}});
        await fireEvent.blur(input());
        expect(riskFreeRate.percent).toBe(3.25);
    });

    it('does not take a text the engine would refuse, says so, and Escape brings the shared value back', async () => {
        riskFreeRate.set(1.5);
        render(RiskFreeRateField);
        await fireEvent.input(input(), {target: {value: 'abc'}});
        await fireEvent.keyDown(input(), {key: 'Enter'});
        expect(riskFreeRate.percent).toBe(1.5);
        expect(input()).toHaveAttribute('aria-invalid', 'true');

        await fireEvent.input(input(), {target: {value: '-100'}});
        await fireEvent.blur(input());
        expect(riskFreeRate.percent).toBe(1.5);
        expect(input()).toHaveAttribute('aria-invalid', 'true');

        await fireEvent.keyDown(input(), {key: 'Escape'});
        expect(input().value).toBe('1.5');
        expect(input()).toHaveAttribute('aria-invalid', 'false');
    });

    it('is one value: a second field shows what the first set', async () => {
        render(RiskFreeRateField);
        render(RiskFreeRateField, {props: {testId: 'risk-free-rate'}});
        await fireEvent.input(input(0), {target: {value: '2'}});
        await fireEvent.keyDown(input(0), {key: 'Enter'});
        expect(input(1).value).toBe('2');
    });

    it('carries its hint in the ⓘ, under its own key', () => {
        render(RiskFreeRateField);
        expect(screen.getByTestId('risk-free-rate-hint')).toBeInTheDocument();
    });
});
