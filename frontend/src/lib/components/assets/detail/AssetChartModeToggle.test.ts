// @vitest-environment jsdom
/**
 * AssetChartModeToggle — component test (Vitest + jsdom), FE5c.
 *
 * The two primary modes of the asset chart: prices, and the rolling return of the calendar view. The page
 * keeps the mode; the toggle presses the button of the mode it is given and asks for a mode with `onselect`.
 * Only that wiring is pinned — `aria-pressed` and the callback — never a label, which is translated.
 *
 * The glyphs (Y-40, developer decision V-8b): the rolling-return button draws the lucide `CalendarSync`, the one the list's
 * card button and top bar draw for the same view, and the price button keeps `ChartLine`; `Percent` is the glyph of the
 * percent view and belongs to neither. A glyph is read from the class token lucide-svelte writes on every icon it renders,
 * `lucide-<name>` (`dist/Icon.svelte`): the library's own name for the shape, not a style, as `PasswordStrength.test.ts` reads it.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import AssetChartModeToggle, {type AssetChartPrimaryMode} from './AssetChartModeToggle.svelte';

const MODES: readonly AssetChartPrimaryMode[] = ['price', 'calendar-return'];

/** The button of each mode. */
const BUTTON_TEST_IDS: Record<AssetChartPrimaryMode, string> = {price: 'asset-chart-primary-price', 'calendar-return': 'asset-chart-primary-calendar-return'};

/** The icon each button gives its glyph's testid to. */
const ICON_TEST_IDS: Record<AssetChartPrimaryMode, string> = {price: 'asset-chart-primary-price-icon', 'calendar-return': 'asset-chart-primary-calendar-return-icon'};

/** The glyph an svg draws, by lucide's name for it: `lucide-calendar-sync` gives `calendar-sync`. */
function glyphOf(svg: Element): string {
    const token = Array.from(svg.classList).find((name) => name.startsWith('lucide-') && name !== 'lucide-icon');
    return token ? token.slice('lucide-'.length) : '(no lucide glyph)';
}

/** Every glyph drawn inside `root`, in document order. */
function glyphsIn(root: Element): string[] {
    return Array.from(root.querySelectorAll('svg')).map(glyphOf);
}

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

describe('AssetChartModeToggle glyphs (Y-40, V-8b): CalendarSync for the rolling return, ChartLine for the prices, never Percent', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    // Whichever mode the page is in: the glyph names the mode, it does not change with the press.
    it.each(MODES)('draws the rolling-return button with CalendarSync when the page is in %s mode', (mode) => {
        render(AssetChartModeToggle, {props: {primaryMode: mode, onselect: vi.fn()}});

        expect(glyphOf(screen.getByTestId(ICON_TEST_IDS['calendar-return']))).toBe('calendar-sync');
    });

    it.each(MODES)('keeps ChartLine on the price button when the page is in %s mode', (mode) => {
        render(AssetChartModeToggle, {props: {primaryMode: mode, onselect: vi.fn()}});

        expect(glyphOf(screen.getByTestId(ICON_TEST_IDS.price))).toBe('chart-line');
    });

    // The two tests above read the glyph that carries the testid; this one reads every glyph inside each button, so a Percent
    // added beside, or in place of, the named one is seen as well.
    it.each(MODES)('draws no Percent glyph on either button, and one glyph on each, when the page is in %s mode', (mode) => {
        render(AssetChartModeToggle, {props: {primaryMode: mode, onselect: vi.fn()}});

        const drawn = MODES.map((candidate) => ({mode: candidate, glyphs: glyphsIn(screen.getByTestId(BUTTON_TEST_IDS[candidate]))}));
        expect(
            drawn.filter(({glyphs}) => glyphs.includes('percent')).map(({mode: candidate}) => candidate),
            'the buttons that draw Percent',
        ).toEqual([]);
        expect(drawn).toEqual([
            {mode: 'price', glyphs: ['chart-line']},
            {mode: 'calendar-return', glyphs: ['calendar-sync']},
        ]);
    });
});
