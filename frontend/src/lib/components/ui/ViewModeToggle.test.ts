// @vitest-environment jsdom
/**
 * ViewModeToggle — the cards / table switch of the Assets and FX lists (Y2, the FB-8 defect found here too).
 *
 * A `ButtonGroup` of segments (85 BTN-2d). Each button says what it does in the standard button's own tooltip, on a rest (never a
 * `title`, which is a browser tooltip and appears only where the browser decides), and carries a translated accessible name; no
 * tooltip wrapper stands around it. A click chooses the mode and is the button's own: it never reaches what is around the toggle.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';

import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {HOVER_DELAY_MS} from '$lib/components/ui/button/pressable.svelte';
import {buttonClasses, WORD_HIDDEN_BELOW} from '$lib/components/ui/button/buttonClasses';
import ViewModeToggle from './ViewModeToggle.svelte';

vi.mock('$lib/utils/storage', () => ({getUserStorage: (_key: string, fallback: unknown) => fallback, setUserStorage: vi.fn()}));

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    document.body.innerHTML = '';
});

const RAW_KEY = /^[\w-]+(\.[\w-]+)+$/;

/** The mouse rests on `element` for the standard delay; answers the tooltip then open, if any. Fake timers must be on. */
async function restOn(element: HTMLElement): Promise<HTMLElement | null> {
    const event = new MouseEvent('pointerenter', {cancelable: true});
    Object.defineProperty(event, 'pointerType', {value: 'mouse'});
    element.dispatchEvent(event);
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS);
    flushSync();
    return screen.queryByRole('tooltip');
}

describe('ViewModeToggle', () => {
    afterEach(() => {
        cleanup();
        vi.useRealTimers();
    });

    it.each(['grid', 'list'] as const)('the %s button is named, carries no title, and shows its name in the standard tooltip on a rest', async (mode) => {
        vi.useFakeTimers();
        render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode'}});
        const button = screen.getByTestId(`view-mode-${mode}`);
        expect(button.hasAttribute('title'), 'a title attribute is a browser tooltip').toBe(false);
        const label = button.getAttribute('aria-label') ?? '';
        expect(label.trim(), 'an accessible name stands in for the text').not.toBe('');
        expect(RAW_KEY.test(label), `the aria-label is a rendered text, not the key "${label}"`).toBe(false);
        expect(screen.queryByTestId(`view-mode-${mode}-tooltip`), 'no wrapper around the button any more').toBeNull();
        expect((await restOn(button))?.textContent?.trim()).toBe(label);
    });

    it('is a named group of joined segments', () => {
        render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode', testId: 'probe-toggle'}});
        const group = screen.getByTestId('probe-toggle');
        expect(group.getAttribute('role')).toBe('group');
        const name = group.getAttribute('aria-label') ?? '';
        expect(name.trim()).not.toBe('');
        expect(RAW_KEY.test(name), `the group's name is a rendered text, not the key "${name}"`).toBe(false);
        for (const mode of ['grid', 'list']) expect(screen.getByTestId(`view-mode-${mode}`).classList.contains('lf-btn-segment'), mode).toBe(true);
    });

    it('compact takes the small button’s lower box (C18), so a row of tables does not move', () => {
        render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode', compact: true, showLabels: true}});
        const button = screen.getByTestId('view-mode-grid');
        expect(button.className).toBe(buttonClasses({size: 'sm', compact: true, segment: true, joined: true, pressed: true}));
    });

    it('a click stays the button’s own: it never reaches a clickable parent around the toggle', async () => {
        const {container} = render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode'}});
        const around = vi.fn();
        container.addEventListener('click', around);
        await fireEvent.click(screen.getByTestId('view-mode-list'));
        expect(around).not.toHaveBeenCalled();
    });

    it('the two buttons have different names', () => {
        render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode'}});
        expect(screen.getByTestId('view-mode-grid').getAttribute('aria-label')).not.toBe(screen.getByTestId('view-mode-list').getAttribute('aria-label'));
    });

    it('chooses the mode on a click, and the click does not pin the hint over the list', async () => {
        const onchange = vi.fn();
        render(ViewModeToggle, {props: {mode: 'grid', storageKey: 'probeViewMode', onchange}});
        await fireEvent.click(screen.getByTestId('view-mode-list'));
        expect(onchange).toHaveBeenCalledExactlyOnceWith('list');
        expect(screen.queryByRole('tooltip'), 'a click opens no hint over the list that is redrawn').toBeNull();
    });
});

describe('ViewModeToggle with options (project 74: the Positions panel’s «Globale / Broker»)', () => {
    async function options() {
        const {Globe, Briefcase} = await import('lucide-svelte');
        return [
            {value: 'asset', icon: Globe, label: 'Globale', hint: 'One row per asset', testId: 'positions-grouping-asset'},
            {value: 'broker', icon: Briefcase, label: 'Broker', testId: 'positions-grouping-broker'},
        ];
    }

    it('draws the options given, the chosen one pressed, the grid/list buttons gone', async () => {
        render(ViewModeToggle, {props: {mode: 'broker', options: await options(), testId: 'positions-grouping-toggle'}});
        expect(screen.getByTestId('positions-grouping-broker').getAttribute('aria-pressed')).toBe('true');
        expect(screen.getByTestId('positions-grouping-asset').getAttribute('aria-pressed')).toBe('false');
        expect(screen.queryByTestId('view-mode-grid')).toBeNull();
        expect(screen.getByTestId('positions-grouping-toggle').getAttribute('role')).toBe('group');
    });

    it('labels show only when asked, and hide below the sm breakpoint (the icon and the name stay)', async () => {
        render(ViewModeToggle, {props: {mode: 'broker', options: await options()}});
        expect(screen.getByTestId('positions-grouping-asset').querySelector('[data-lf-word]')).toBeNull();
        cleanup();
        render(ViewModeToggle, {props: {mode: 'broker', options: await options(), showLabels: true}});
        const button = screen.getByTestId('positions-grouping-asset');
        const word = button.querySelector('[data-lf-word]');
        expect(word?.textContent?.trim()).toBe('Globale');
        expect(word?.classList.contains(WORD_HIDDEN_BELOW.sm), 'hidden below sm').toBe(true);
        expect(button.getAttribute('aria-label'), 'a word that may hide leaves the name').toBe('Globale');
        expect(button.querySelector('svg'), 'the icon is always there').not.toBeNull();
    });

    it('an option’s hint shows under its name on a rest', async () => {
        const list = await options();
        vi.useFakeTimers();
        try {
            render(ViewModeToggle, {props: {mode: 'broker', options: list}});
            const tip = await restOn(screen.getByTestId('positions-grouping-asset'));
            expect(tip?.querySelector('strong')?.textContent).toBe('Globale');
            expect(tip?.textContent).toContain('One row per asset');
        } finally {
            cleanup();
            vi.useRealTimers();
        }
    });

    it('without a storage key the caller owns the persistence: a click reports the mode and stores nothing', async () => {
        const storage = await import('$lib/utils/storage');
        const onchange = vi.fn();
        render(ViewModeToggle, {props: {mode: 'broker', options: await options(), onchange}});
        await fireEvent.click(screen.getByTestId('positions-grouping-asset'));
        expect(onchange).toHaveBeenCalledExactlyOnceWith('asset');
        expect(storage.setUserStorage).not.toHaveBeenCalledWith(undefined, 'asset');
        expect(vi.mocked(storage.setUserStorage).mock.calls.filter(([, value]) => value === 'asset')).toEqual([]);
    });
});
