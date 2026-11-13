// @vitest-environment jsdom
/**
 * ChoiceCards (P2 of project 67, M6, M18): a choice among a few options as big cards, one radio each, never a menu.
 * The broker's operating profile uses it for the currency conversion and the tax regime; the option a profile starts
 * from carries the «default» badge. Props in, DOM and a callback out; read through test ids and states, never text.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import ChoiceCards from './ChoiceCards.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(cleanup);

const OPTIONS = [
    {value: 'administered', label: 'Administered', description: 'The broker withholds the taxes.'},
    {value: 'declarative', label: 'Declarative', description: 'You declare them.'},
];

const cards = () => screen.getAllByTestId('probe-card');
const card = (value: string) => cards().find((item) => item.getAttribute('data-value') === value) as HTMLElement;

describe('ChoiceCards', () => {
    it('the regime and the conversion are big choice cards, and the default is badged', () => {
        render(ChoiceCards, {name: 'probe', legend: 'Tax regime', options: OPTIONS, value: null, defaultValue: 'declarative', testid: 'probe', onchange: () => {}});

        expect(cards().map((item) => item.getAttribute('data-value'))).toEqual(['administered', 'declarative']);
        expect(screen.getAllByRole('radio')).toHaveLength(2);
        expect(document.querySelector('select')).toBeNull();
        // The default is badged, and reads as chosen while nothing is chosen.
        expect(card('declarative').querySelector('[data-testid="probe-default"]')).not.toBeNull();
        expect(card('administered').querySelector('[data-testid="probe-default"]')).toBeNull();
        expect(card('declarative').getAttribute('data-selected')).toBe('true');
        expect(card('administered').getAttribute('data-selected')).toBe('false');
    });

    it('one choice at a time, reported through the callback', async () => {
        const onchange = vi.fn();
        render(ChoiceCards, {name: 'probe', legend: 'Tax regime', options: OPTIONS, value: 'declarative', defaultValue: 'declarative', testid: 'probe', onchange});

        await fireEvent.click(card('administered').querySelector('input') as HTMLInputElement);

        expect(onchange).toHaveBeenCalledWith('administered');
    });

    it('a chosen value is shown as chosen', () => {
        render(ChoiceCards, {name: 'probe', legend: 'Tax regime', options: OPTIONS, value: 'administered', defaultValue: 'declarative', testid: 'probe', onchange: () => {}});

        expect(card('administered').getAttribute('data-selected')).toBe('true');
        expect((card('administered').querySelector('input') as HTMLInputElement).checked).toBe(true);
        expect(card('declarative').getAttribute('data-selected')).toBe('false');
    });

    it('a caller can keep its own ids and value attribute', () => {
        render(ChoiceCards, {name: 'mode', legend: 'Conversion', options: OPTIONS, value: 'administered', testid: 'x-modes', cardTestid: 'x-mode', radioTestid: 'x-mode-radio', valueAttribute: 'mode', onchange: () => {}});

        expect(screen.getAllByTestId('x-mode').map((item) => item.getAttribute('data-mode'))).toEqual(['administered', 'declarative']);
        expect(screen.getAllByTestId('x-mode-radio')).toHaveLength(2);
        expect(screen.getByTestId('x-modes').tagName).toBe('FIELDSET');
    });
});
