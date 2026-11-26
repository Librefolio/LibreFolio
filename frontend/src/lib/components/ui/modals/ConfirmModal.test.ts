// @vitest-environment jsdom
/**
 * ConfirmModal — the label of a long list with no `itemsLabel` (O-6a).
 *
 * The toggle over a list of several items used to read "3 items" in every language. It now takes the count with the
 * catalogue's word for "items", so a non-English interface never shows an English one. The test reads the label
 * back from the catalogue, never from a literal.
 */
import {get} from 'svelte/store';
import {_, locale, waitLocale} from 'svelte-i18n';
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import ConfirmModal from './ConfirmModal.svelte';

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

beforeAll(async () => {
    await setupI18n();
});

describe('ConfirmModal — default list label', () => {
    it('writes the count with the catalogue word in the interface language, not a hard-coded English "items"', async () => {
        locale.set('it');
        await waitLocale('it');
        render(ConfirmModal, {open: true, title: 't', message: 'm', items: ['a', 'b', 'c'], onConfirm: vi.fn(), onCancel: vi.fn()});

        const word = get(_)('table.items');
        expect(word).not.toBe('items');
        expect(screen.getByText(`3 ${word}`)).toBeInTheDocument();
        locale.set('en');
        await waitLocale('en');
    });
});

/**
 * The standard buttons (85 BTN-2a). The confirm button publishes its tone in `data-tone` — the one handle a test reads,
 * never a class; the ✕ is `CloseButton`, named «Close» in the interface's language; the toggle of a long list says
 * whether it is open (`aria-expanded`).
 */
describe('ConfirmModal — the standard buttons (85 BTN-2a)', () => {
    const base = () => ({open: true, title: 't', message: 'm', onConfirm: vi.fn(), onCancel: vi.fn()});

    it.each([
        [{danger: true}, 'danger'],
        [{warning: true}, 'warning'],
        [{}, 'primary'],
        [{danger: true, warning: true}, 'danger'],
    ] as const)('the confirm button of %o publishes data-tone="%s"', (mode, tone) => {
        render(ConfirmModal, {...base(), ...mode});
        expect(screen.getByTestId('confirm-modal-confirm')).toHaveAttribute('data-tone', tone);
        cleanup();
    });

    it('the ✕ is named «Close» in the interface’s language, and closes', async () => {
        locale.set('it');
        await waitLocale('it');
        try {
            const props = base();
            render(ConfirmModal, props);
            const close = get(_)('common.close');
            expect(close, 'premise: the catalogue word is not the English one').not.toBe('Close');
            const x = screen.getAllByRole('button').find((button) => button.getAttribute('aria-label') === close);
            expect(x, `a button named «${close}»`).toBeDefined();
            await fireEvent.click(x!);
            expect(props.onCancel).toHaveBeenCalledTimes(1);
            expect(props.onConfirm).not.toHaveBeenCalled();
        } finally {
            locale.set('en');
            await waitLocale('en');
        }
    });

    it('the toggle of a long list says whether it is open', async () => {
        render(ConfirmModal, {...base(), items: ['a', 'b', 'c']});
        const toggles = [...document.querySelectorAll<HTMLButtonElement>('button[aria-expanded]')];
        expect(toggles, 'one disclosure in the dialog').toHaveLength(1);
        const [toggle] = toggles;
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        expect(screen.queryByText('b')).toBeNull();
        await fireEvent.click(toggle);
        expect(toggle).toHaveAttribute('aria-expanded', 'true');
        expect(screen.getByText('b')).toBeInTheDocument();
    });
});
