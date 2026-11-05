// @vitest-environment jsdom
/**
 * SimulationHorizonField — the horizon as days or `2y3m5d` (F-8; Vitest + jsdom).
 *
 * The reading itself is pinned in `horizonExpression.test.ts`. Here only the wiring a helper cannot see, on test ids and
 * data attributes, never on translated text:
 *
 * - the field starts as the plain number the parent holds, and says the days it comes to under itself;
 * - an expression in the interface language's letters changes the days the parent is told (`onchange`), and the text
 *   the user typed stays as typed;
 * - a malformed text puts the error in the field (`aria-invalid`, the error line) and tells the parent nothing;
 * - the other languages' letters are not accepted, and the units come from the catalogue of the active language.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

import {fireEvent, render, screen, setupI18n} from '$test/component';

import SimulationHorizonField from './SimulationHorizonField.svelte';

const INPUT = 'risk-simulation-horizon';

beforeAll(async () => {
    await setupI18n('en');
});

async function type(text: string): Promise<HTMLInputElement> {
    const input = screen.getByTestId(INPUT) as HTMLInputElement;
    await fireEvent.input(input, {target: {value: text}});
    return input;
}

describe('SimulationHorizonField', () => {
    it('starts as the plain number of days, with the days it comes to under it', () => {
        render(SimulationHorizonField, {props: {days: 365}});

        expect((screen.getByTestId(INPUT) as HTMLInputElement).value).toBe('365');
        expect(screen.getByTestId(`${INPUT}-days`).getAttribute('data-days')).toBe('365');
        expect(screen.queryByTestId(`${INPUT}-error`)).toBeNull();
    });

    it('reads an expression in the interface language and keeps the text as typed', async () => {
        const onchange = vi.fn();
        render(SimulationHorizonField, {props: {days: 365, onchange}});

        const input = await type('2y3m5d');

        expect(input.value).toBe('2y3m5d');
        // A fixed sum: 730 + 90 + 5.
        expect(screen.getByTestId(`${INPUT}-days`).getAttribute('data-days')).toBe('825');
        expect(input.getAttribute('aria-invalid')).toBe('false');
        expect(onchange).toHaveBeenCalledTimes(1);
    });

    it('takes a value past its natural range', async () => {
        render(SimulationHorizonField, {props: {days: 365}});

        await type('24m66d');

        expect(screen.getByTestId(`${INPUT}-days`).getAttribute('data-days')).toBe('786');
    });

    it('puts the error in the field and tells the parent nothing', async () => {
        const onchange = vi.fn();
        render(SimulationHorizonField, {props: {days: 365, onchange}});

        const input = await type('2a3m5g');

        expect(input.getAttribute('aria-invalid')).toBe('true');
        expect(screen.getByTestId(`${INPUT}-error`).getAttribute('data-error')).toBe('format');
        expect(screen.queryByTestId(`${INPUT}-days`)).toBeNull();
        expect(onchange).not.toHaveBeenCalled();
    });

    it('names the bound that was crossed', async () => {
        render(SimulationHorizonField, {props: {days: 365}});

        await type('0');
        expect(screen.getByTestId(`${INPUT}-error`).getAttribute('data-error')).toBe('tooShort');

        await type('3651');
        expect(screen.getByTestId(`${INPUT}-error`).getAttribute('data-error')).toBe('tooLong');

        await type('3650');
        expect(screen.queryByTestId(`${INPUT}-error`)).toBeNull();
    });

    it('takes the letters of the active language: Italian reads a/m/g', async () => {
        await setupI18n('it');
        try {
            render(SimulationHorizonField, {props: {days: 365}});

            await type('2a3m5g');
            expect(screen.getByTestId(`${INPUT}-days`).getAttribute('data-days')).toBe('825');
            expect(screen.queryByTestId(`${INPUT}-error`)).toBeNull();

            await type('2y3m5d');
            expect(screen.getByTestId(`${INPUT}-error`).getAttribute('data-error')).toBe('format');
        } finally {
            await setupI18n('en');
        }
    });
});
