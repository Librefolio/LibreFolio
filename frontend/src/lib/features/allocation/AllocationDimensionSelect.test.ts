// @vitest-environment jsdom
/**
 * AllocationDimensionSelect — Sector, Area, Type, Asset: four buttons on a wide screen, one select on a phone, never both.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import AllocationDimensionSelect from './AllocationDimensionSelect.svelte';

beforeAll(async () => {
    await setupI18n();
});
afterEach(cleanup);

function viewport(wide: boolean) {
    window.matchMedia = ((query: string) => ({matches: wide, media: query, addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {}, onchange: null, dispatchEvent: () => false})) as unknown as typeof window.matchMedia;
}

describe('on a wide screen', () => {
    it('is four buttons, the chosen one pressed, and a click asks for that dimension', async () => {
        viewport(true);
        const onchange = vi.fn();
        render(AllocationDimensionSelect, {value: 'sector', onchange, testId: 'd'});
        expect(['sector', 'geography', 'type', 'asset'].map((id) => screen.getByTestId(`d-${id}`).getAttribute('aria-pressed'))).toEqual(['true', 'false', 'false', 'false']);
        expect(screen.queryByTestId('d-select-button')).toBeNull();
        await fireEvent.click(screen.getByTestId('d-geography'));
        expect(onchange).toHaveBeenCalledWith('geography');
    });
});

describe('on a phone', () => {
    it('is one select, with the four dimensions, and no buttons', async () => {
        viewport(false);
        const onchange = vi.fn();
        render(AllocationDimensionSelect, {value: 'type', onchange, testId: 'd'});
        expect(screen.queryByTestId('d-sector')).toBeNull();
        const trigger = screen.getByTestId('d-select-button');
        await fireEvent.click(trigger);
        for (const id of ['sector', 'geography', 'type', 'asset']) expect(screen.getByTestId(`d-select-option-${id}`)).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('d-select-option-asset'));
        expect(onchange).toHaveBeenCalledWith('asset');
    });
});
