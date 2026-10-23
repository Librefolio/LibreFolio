// @vitest-environment jsdom
/**
 * AssetChartModeToggle and AssetCalendarWindowControls — the `idPrefix` prop (lot X5-F1).
 *
 * The FX pair detail page draws the same two controls as the asset detail page, under its own test ids. Both components take
 * an optional `idPrefix` (default `'asset'`, so every id the asset page and its tests use is unchanged), and every test id
 * they publish starts with it: `${idPrefix}-chart-primary-price`, `-price-icon`, `-calendar-return`, `-calendar-return-icon`
 * for the toggle; `${idPrefix}-calendar-window-controls`, `-calendar-window-${preset.key}`, `-calendar-window-custom`,
 * `-calendar-custom-amount`, `-calendar-custom-unit` and `-calendar-return-docs` for the window controls.
 *
 * Only ids, `aria-pressed` and callbacks are pinned, never a label (translated). Red first: the prop is unknown, so the
 * `fx` cases find no `fx-…` id (the default cases are the regression guard and pass before and after).
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import {CALENDAR_RETURN_PRESETS, DEFAULT_CALENDAR_RETURN_WINDOW} from '$lib/components/charts/calendarReturnWindow';
import AssetCalendarWindowControls from './AssetCalendarWindowControls.svelte';
import AssetChartModeToggle from './AssetChartModeToggle.svelte';

const PRESET_KEYS = CALENDAR_RETURN_PRESETS.map((preset) => preset.key);

/** Every test id inside `root`, in document order. */
function testIdsIn(root: Element): string[] {
    return Array.from(root.querySelectorAll('[data-testid]'), (element) => element.getAttribute('data-testid') ?? '');
}

/** The ids the toggle publishes under `prefix`. */
const toggleIds = (prefix: string) => [`${prefix}-chart-primary-price`, `${prefix}-chart-primary-price-icon`, `${prefix}-chart-primary-calendar-return`, `${prefix}-chart-primary-calendar-return-icon`];

function renderToggle(props: {idPrefix?: string; primaryMode?: 'price' | 'calendar-return'} = {}) {
    const onselect = vi.fn();
    const view = render(AssetChartModeToggle, {props: {primaryMode: props.primaryMode ?? 'price', onselect, ...(props.idPrefix === undefined ? {} : {idPrefix: props.idPrefix})}});
    return {onselect, container: view.container};
}

function renderControls(props: {idPrefix?: string; customEditing?: boolean} = {}) {
    const onpreset = vi.fn();
    const oncustom = vi.fn();
    const view = render(AssetCalendarWindowControls, {
        props: {
            selection: {...DEFAULT_CALENDAR_RETURN_WINDOW, kind: 'preset', preset: '3m'},
            customAmount: 3,
            customUnit: 'years',
            customEditing: props.customEditing ?? false,
            onpreset,
            oncustom,
            ...(props.idPrefix === undefined ? {} : {idPrefix: props.idPrefix}),
        },
    });
    return {onpreset, oncustom, container: view.container};
}

describe('AssetChartModeToggle idPrefix (X5-F1)', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('keeps the asset ids when no prefix is given', () => {
        const {container} = renderToggle();

        expect(testIdsIn(container)).toEqual(toggleIds('asset'));
    });

    it('publishes every id under the given prefix, and none under asset', () => {
        const {container} = renderToggle({idPrefix: 'fx'});

        expect(testIdsIn(container)).toEqual(toggleIds('fx'));
        expect(screen.queryByTestId('asset-chart-primary-price')).toBeNull();
        expect(screen.queryByTestId('asset-chart-primary-calendar-return')).toBeNull();
    });

    it.each(['price', 'calendar-return'] as const)('presses the %s button of the prefixed toggle, and only it', (mode) => {
        renderToggle({idPrefix: 'fx', primaryMode: mode});

        expect(screen.getByTestId('fx-chart-primary-price')).toHaveAttribute('aria-pressed', String(mode === 'price'));
        expect(screen.getByTestId('fx-chart-primary-calendar-return')).toHaveAttribute('aria-pressed', String(mode === 'calendar-return'));
    });

    it.each(['price', 'calendar-return'] as const)('calls onselect with %s on a click of the prefixed button', async (mode) => {
        const {onselect} = renderToggle({idPrefix: 'fx', primaryMode: mode === 'price' ? 'calendar-return' : 'price'});

        await fireEvent.click(screen.getByTestId(`fx-chart-primary-${mode}`));

        expect(onselect).toHaveBeenCalledTimes(1);
        expect(onselect).toHaveBeenCalledWith(mode);
    });

    it('keeps each glyph on the testid of its prefixed icon', () => {
        renderToggle({idPrefix: 'fx'});

        const glyph = (id: string) => Array.from(screen.getByTestId(id).classList).find((name) => name.startsWith('lucide-') && name !== 'lucide-icon');
        expect(glyph('fx-chart-primary-price-icon')).toBe('lucide-chart-line');
        expect(glyph('fx-chart-primary-calendar-return-icon')).toBe('lucide-calendar-sync');
    });
});

describe('AssetCalendarWindowControls idPrefix (X5-F1)', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    /** The ids of the window controls under `prefix`, with the editor closed: root, a button per preset, the custom badge, the docs link. */
    const controlIds = (prefix: string) => [`${prefix}-calendar-window-controls`, ...PRESET_KEYS.map((key) => `${prefix}-calendar-window-${key}`), `${prefix}-calendar-window-custom`, `${prefix}-calendar-return-docs`];

    it('keeps the asset ids when no prefix is given', () => {
        const {container} = renderControls();

        expect(testIdsIn(container).sort()).toEqual(controlIds('asset').sort());
    });

    it('publishes every id under the given prefix, and none under asset', () => {
        const {container} = renderControls({idPrefix: 'fx'});

        expect(testIdsIn(container).sort()).toEqual(controlIds('fx').sort());
        expect(testIdsIn(container).filter((id) => id.startsWith('asset-'))).toEqual([]);
    });

    it('prefixes the custom duration editor’s amount and unit while it is open', () => {
        const {container} = renderControls({idPrefix: 'fx', customEditing: true});

        const ids = testIdsIn(container);
        expect(ids).toContain('fx-calendar-custom-amount');
        expect(ids).toContain('fx-calendar-custom-unit');
        expect(ids.filter((id) => id.startsWith('asset-'))).toEqual([]);
    });

    it('keeps the asset editor ids when no prefix is given and the editor is open', () => {
        const {container} = renderControls({customEditing: true});

        const ids = testIdsIn(container);
        expect(ids).toContain('asset-calendar-custom-amount');
        expect(ids).toContain('asset-calendar-custom-unit');
    });

    it.each(PRESET_KEYS)('presses the %s preset of the prefixed controls only when it is the selection, and a click asks for it', async (key) => {
        const {onpreset, oncustom} = renderControls({idPrefix: 'fx'});

        for (const candidate of PRESET_KEYS) {
            expect(screen.getByTestId(`fx-calendar-window-${candidate}`)).toHaveAttribute('aria-pressed', String(candidate === '3m'));
        }
        await fireEvent.click(screen.getByTestId(`fx-calendar-window-${key}`));

        expect(onpreset).toHaveBeenCalledTimes(1);
        expect(onpreset).toHaveBeenCalledWith(key);
        expect(oncustom).not.toHaveBeenCalled();
    });

    it('marks the prefixed custom badge inactive while the window is a preset', () => {
        renderControls({idPrefix: 'fx'});

        expect(screen.getByTestId('fx-calendar-window-custom')).toHaveAttribute('data-active', 'false');
    });
});
