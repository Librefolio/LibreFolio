// @vitest-environment jsdom
/**
 * AssetChartModeToggle — component test (Vitest + jsdom), FE5c.
 *
 * The two primary modes of the asset chart: prices, and the rolling return of the calendar view. The page
 * keeps the mode; the toggle presses the button of the mode it is given and asks for a mode with `onselect`.
 * Only that wiring is pinned — `aria-pressed` and the callback — never a label, which is translated.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import AssetChartModeToggle, {type AssetChartPrimaryMode} from './AssetChartModeToggle.svelte';

const MODES: readonly AssetChartPrimaryMode[] = ['price', 'calendar-return'];

/** The button of each mode. */
const BUTTON_TEST_IDS: Record<AssetChartPrimaryMode, string> = {price: 'asset-chart-primary-price', 'calendar-return': 'asset-chart-primary-calendar-return'};

describe('AssetChartModeToggle: the button of the given mode is pressed, and a click asks the page for its mode', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it.each(MODES)('presses the %s button, and only it', (mode) => {
        render(AssetChartModeToggle, {props: {primaryMode: mode, onselect: vi.fn()}});

        for (const candidate of MODES) {
            expect(screen.getByTestId(BUTTON_TEST_IDS[candidate])).toHaveAttribute('aria-pressed', String(candidate === mode));
        }
    });

    it.each(MODES)('calls onselect with %s on a click of its button', async (mode) => {
        const onselect = vi.fn();
        render(AssetChartModeToggle, {props: {primaryMode: 'price', onselect}});

        await fireEvent.click(screen.getByTestId(BUTTON_TEST_IDS[mode]));

        expect(onselect).toHaveBeenCalledTimes(1);
        expect(onselect).toHaveBeenCalledWith(mode);
    });

    it('leaves the mode to the page: a click alone presses nothing, the mode the page passes back does', async () => {
        const onselect = vi.fn();
        const {rerender} = render(AssetChartModeToggle, {props: {primaryMode: 'price', onselect}});

        await fireEvent.click(screen.getByTestId(BUTTON_TEST_IDS['calendar-return']));

        expect(screen.getByTestId(BUTTON_TEST_IDS.price)).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId(BUTTON_TEST_IDS['calendar-return'])).toHaveAttribute('aria-pressed', 'false');

        await rerender({primaryMode: 'calendar-return'});

        expect(screen.getByTestId(BUTTON_TEST_IDS.price)).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId(BUTTON_TEST_IDS['calendar-return'])).toHaveAttribute('aria-pressed', 'true');
    });
});
