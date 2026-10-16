// @vitest-environment jsdom
/**
 * AssetCalendarWindowControls — component test (Vitest + jsdom), FE5c.
 *
 * The window of the asset chart's rolling return: a button per preset, then the custom duration badge. The
 * page keeps the selection; the controls press the preset it names and ask for a preset with `onpreset`. The
 * badge's editor is CompactDurationBadge's own and is not driven here: the badge is only present, and active
 * while the window is custom. Labels are translated, so nothing reads them.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import {CALENDAR_RETURN_PRESETS, DEFAULT_CALENDAR_RETURN_WINDOW, type CalendarReturnWindowSelection} from '$lib/components/charts/calendarReturnWindow';
import AssetCalendarWindowControls from './AssetCalendarWindowControls.svelte';

const PRESET_KEYS = CALENDAR_RETURN_PRESETS.map((preset) => preset.key);

function presetButton(key: string): HTMLElement {
    return screen.getByTestId(`asset-calendar-window-${key}`);
}

/** The controls showing `selection`, with a spy for each callback. */
function renderControls(selection: CalendarReturnWindowSelection) {
    const onpreset = vi.fn();
    const oncustom = vi.fn();
    render(AssetCalendarWindowControls, {props: {selection, customAmount: 3, customUnit: 'years', customEditing: false, onpreset, oncustom}});
    return {onpreset, oncustom};
}

describe('AssetCalendarWindowControls: a button per preset, the selected one pressed, and a click asks the page for its preset', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('shows a button per preset, in the presets’ order, then the custom duration badge', () => {
        renderControls({...DEFAULT_CALENDAR_RETURN_WINDOW});

        const testIds = Array.from(screen.getByTestId('asset-calendar-window-controls').querySelectorAll('[data-testid^="asset-calendar-window-"]'), (element) => element.getAttribute('data-testid'));

        expect(testIds).toEqual([...PRESET_KEYS.map((key) => `asset-calendar-window-${key}`), 'asset-calendar-window-custom']);
    });

    it.each(PRESET_KEYS)('presses the %s preset when it is selected, and only it', (key) => {
        renderControls({...DEFAULT_CALENDAR_RETURN_WINDOW, kind: 'preset', preset: key});

        for (const candidate of PRESET_KEYS) {
            expect(presetButton(candidate)).toHaveAttribute('aria-pressed', String(candidate === key));
        }
        expect(screen.getByTestId('asset-calendar-window-custom')).toHaveAttribute('data-active', 'false');
    });

    it('presses no preset while the window is custom, and marks the custom badge active', () => {
        renderControls({...DEFAULT_CALENDAR_RETURN_WINDOW, kind: 'custom', customAmount: 2, customUnit: 'years'});

        for (const key of PRESET_KEYS) {
            expect(presetButton(key)).toHaveAttribute('aria-pressed', 'false');
        }
        expect(screen.getByTestId('asset-calendar-window-custom')).toHaveAttribute('data-active', 'true');
    });

    it.each(PRESET_KEYS)('calls onpreset with %s on a click of its button, and nothing else', async (key) => {
        const {onpreset, oncustom} = renderControls({...DEFAULT_CALENDAR_RETURN_WINDOW});

        await fireEvent.click(presetButton(key));

        expect(onpreset).toHaveBeenCalledTimes(1);
        expect(onpreset).toHaveBeenCalledWith(key);
        expect(oncustom).not.toHaveBeenCalled();
    });
});
