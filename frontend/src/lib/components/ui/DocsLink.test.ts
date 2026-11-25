// @vitest-environment jsdom
/**
 * DocsLink — the icon that opens a page of the guide, now a standard Button (85 BTN-2a, the consultant's C12).
 *
 * - `variant="link-muted"` `inline`: the line's size, a hair of padding, a 24 px target.
 * - `size` in px, as the callers wrote it, maps to the button sizes: 11–12 → xs (a 12 px icon), 14 → sm, 16 → md,
 *   18–20 → lg.
 * - `labelDisplay` maps to `display`: `hidden` → the icon alone, `responsive` → the word from `sm` up, `visible` → always.
 * - The name is the label (default `common.documentation`); the `data-testid` is on the `<button>` itself: no Tooltip
 *   wrapper around it any more.
 * - A click opens the page in the interface's language, in a new window (`window.open`).
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {_} from 'svelte-i18n';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {buttonClasses, ICON_PX, WORD_HIDDEN_BELOW} from './button/buttonClasses';

const language = vi.hoisted(() => ({store: null as null | {set: (value: string) => void}}));
vi.mock('$lib/stores/app/language', async () => {
    const {writable: make} = await import('svelte/store');
    const currentLanguage = make('en');
    language.store = currentLanguage;
    return {currentLanguage};
});

import DocsLink from './DocsLink.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    language.store?.set('en');
});

const TID = 'probe-docs';

function mount(props: Record<string, unknown> = {}) {
    render(DocsLink, {props: {path: 'user/fx/index.md', testId: TID, ...props}});
    return screen.getByTestId(TID);
}

describe('DocsLink — a standard Button (85 BTN-2a)', () => {
    it('the test id is on the <button>, with no Tooltip wrapper around it', () => {
        const button = mount();
        expect(button.tagName).toBe('BUTTON');
        expect(button.parentElement?.getAttribute('role'), 'no role="button" wrapper').not.toBe('button');
        expect(button.hasAttribute('title')).toBe(false);
    });

    it('its name is the label, «Documentation» by default', () => {
        expect(mount()).toHaveAttribute('aria-label', get(_)('common.documentation'));
        cleanup();
        expect(mount({label: 'How the FX routes work'})).toHaveAttribute('aria-label', 'How the FX routes work');
    });

    it('is the link-muted inline recipe', () => {
        expect(mount().className).toBe(buttonClasses({variant: 'link-muted', size: 'xs', shape: 'icon', inline: true}));
    });

    it.each([
        [11, 'xs'],
        [12, 'xs'],
        [14, 'sm'],
        [16, 'md'],
        [18, 'lg'],
        [20, 'lg'],
    ] as const)('size %d → the %s button, its icon at ICON_PX', (size, buttonSize) => {
        const button = mount({size});
        const icon = button.querySelector('svg');
        expect(icon?.getAttribute('width')).toBe(String(ICON_PX[buttonSize]));
        expect(button.className).toBe(buttonClasses({variant: 'link-muted', size: buttonSize, shape: 'icon', inline: true}));
    });

    it('labelDisplay hidden → the icon alone; visible → the word; responsive → the word from sm up', () => {
        const word = (button: HTMLElement) => button.querySelector('[data-lf-word]');
        expect(word(mount({labelDisplay: 'hidden'}))).toBeNull();
        cleanup();
        const visible = word(mount({labelDisplay: 'visible', label: 'Guide'}));
        expect(visible?.textContent?.trim()).toBe('Guide');
        expect(visible?.className.trim()).toBe('');
        cleanup();
        const responsive = word(mount({labelDisplay: 'responsive', label: 'Guide'}));
        expect(responsive?.classList.contains(WORD_HIDDEN_BELOW.sm)).toBe(true);
    });

    it('a click opens the page in the interface’s language, in a new window', async () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null);
        await fireEvent.click(mount());
        expect(open).toHaveBeenCalledExactlyOnceWith('/mkdocs/user/fx/index.md', '_blank', 'noopener');

        language.store?.set('it');
        cleanup();
        await fireEvent.click(mount({localizedFallbackPath: 'user/fx/index.it-fallback.md'}));
        expect(open).toHaveBeenLastCalledWith('/mkdocs/it/user/fx/index.it-fallback.md', '_blank', 'noopener');

        cleanup();
        await fireEvent.click(mount());
        expect(open).toHaveBeenLastCalledWith('/mkdocs/it/user/fx/index.md', '_blank', 'noopener');
    });
});
