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
import {render, screen, setupI18n} from '$test/component';
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
