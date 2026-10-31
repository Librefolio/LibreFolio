// @vitest-environment jsdom
/**
 * ColumnVisibilityToggle — the «reset layout» button is written in the interface language (P-15).
 *
 * The caption was an English literal in the markup. It is the catalogue's `table.resetLayout`, and the button has a handle of its own.
 * The table is a fake: only what the toggle reads of it (`getColumnsForVisibility`, `resetColumnLayout`) is there.
 */
import {get} from 'svelte/store';
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {_ as translate, waitLocale} from 'svelte-i18n';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {currentLanguage} from '$lib/stores/app/language';
import ColumnVisibilityToggle from './ColumnVisibilityToggle.svelte';

function fakeTable() {
    return {
        getColumnsForVisibility: () => [{id: 'name', header: 'Name', visible: true}],
        toggleColumnVisibilityById: vi.fn(),
        setColumnOrder: vi.fn(),
        resetColumnLayout: vi.fn(),
    };
}

beforeAll(async () => {
    await setupI18n();
});

describe('ColumnVisibilityToggle — reset layout', () => {
    it('has a handle of its own and resets the layout of the table', async () => {
        const table = fakeTable();
        render(ColumnVisibilityToggle, {props: {tableRef: table as never}});
        await fireEvent.click(screen.getByTestId('column-visibility-toggle'));

        await fireEvent.click(await screen.findByTestId('column-visibility-reset'));

        expect(table.resetColumnLayout).toHaveBeenCalledTimes(1);
    });

    it.each(['en', 'it', 'fr', 'es'] as const)('%s: the caption is the catalogue’s table.resetLayout', async (lang) => {
        await waitLocale(lang);
        currentLanguage.set(lang);
        await waitLocale(lang);
        render(ColumnVisibilityToggle, {props: {tableRef: fakeTable() as never}});
        await fireEvent.click(screen.getByTestId('column-visibility-toggle'));

        const button = await screen.findByTestId('column-visibility-reset');
        const expected = get(translate)('table.resetLayout');
        expect(expected, 'control: the key exists in the catalogue').not.toBe('table.resetLayout');
        await waitFor(() => expect(button.textContent?.trim()).toBe(expected));
    });
});
