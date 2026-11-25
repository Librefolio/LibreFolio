// @vitest-environment jsdom
/**
 * CloseButton — the ✕ of a dialog, a panel or a banner (project 85, BTN-0, D7: a ✕ never comes without a name).
 *
 * - Named «Close» in the active language by default: the name is the catalogue's `common.close` for that language,
 *   never a raw key and never a hard-coded English word (checked in English and in Italian).
 * - A caller's label wins.
 * - Icon only, ghost: its name is the `aria-label`, no word in view.
 * - Disabled, it stays reachable (`aria-disabled`): an icon must still say what it is.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {locale} from 'svelte-i18n';
import {_ as t} from '$lib/i18n';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import CloseButton from './CloseButton.svelte';
import {buttonClasses} from './buttonClasses';

const RAW_KEY = /^[\w-]+(\.[\w-]+)+$/;

beforeAll(async () => {
    await setupI18n();
});

afterEach(async () => {
    cleanup();
    await setupI18n('en');
});

describe('CloseButton', () => {
    it.each(['en', 'it'])('is named common.close of the active language (%s), not a raw key', async (lang) => {
        await setupI18n(lang);
        expect(get(locale)).toBe(lang);
        render(CloseButton, {props: {'data-testid': 'probe-close'}});
        const name = screen.getByTestId('probe-close').getAttribute('aria-label') ?? '';
        expect(name.trim()).not.toBe('');
        expect(RAW_KEY.test(name), `the name is a rendered text, not the key "${name}"`).toBe(false);
        expect(name).toBe(get(t)('common.close'));
    });

    it('the names differ between two languages: the default follows the language', async () => {
        await setupI18n('en');
        const en = get(t)('common.close');
        await setupI18n('it');
        expect(get(t)('common.close')).not.toBe(en);
    });

    it('a custom label wins', () => {
        render(CloseButton, {props: {label: 'Close editor', 'data-testid': 'probe-close'}});
        expect(screen.getByTestId('probe-close')).toHaveAttribute('aria-label', 'Close editor');
    });

    it('is an icon-only ghost button: no word, an icon, the ghost recipe', () => {
        render(CloseButton, {props: {'data-testid': 'probe-close'}});
        const button = screen.getByTestId('probe-close');
        expect(button.tagName).toBe('BUTTON');
        expect(button.querySelector('[data-lf-word]'), 'no word in view').toBeNull();
        expect(button.querySelector('svg')).not.toBeNull();
        expect(button.className).toBe(buttonClasses({variant: 'ghost', size: 'md', shape: 'icon'}));
    });

    it('acts on a click', async () => {
        const onclick = vi.fn();
        render(CloseButton, {props: {onclick, 'data-testid': 'probe-close'}});
        await fireEvent.click(screen.getByTestId('probe-close'));
        expect(onclick).toHaveBeenCalledTimes(1);
    });

    it('disabled, stays reachable: aria-disabled, never natively disabled, the click dropped', async () => {
        const onclick = vi.fn();
        render(CloseButton, {props: {onclick, disabled: true, 'data-testid': 'probe-close'}});
        const button = screen.getByTestId('probe-close');
        expect(button).toHaveAttribute('aria-disabled', 'true');
        expect(button.hasAttribute('disabled')).toBe(false);
        expect(button.tabIndex).toBe(0);
        await fireEvent.click(button);
        expect(onclick).not.toHaveBeenCalled();
    });
});
