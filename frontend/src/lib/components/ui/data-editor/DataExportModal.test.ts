// @vitest-environment jsdom
/**
 * DataExportModal (FB-30) — component test (Vitest + jsdom).
 *
 * The small dialog the data editors open from their «Export» button: it lets the user pick CSV or JSON and hands the choice
 * to the caller (`onexport(format)`), which downloads the file. Driven as the user drives it: pick a format, press Export.
 * The assertions read what the caller receives and what stays on screen, never the words.
 *
 * Contract:
 * - closed: nothing on screen;
 * - open: CSV is chosen; the other choice is JSON;
 * - Export hands the chosen format to `onexport`, then closes the dialog (`onclose`);
 * - a download that fails keeps the dialog open and says so (`data-export-error`), so the user can try again;
 * - while the download runs, Export cannot be pressed twice.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, `front_component_unit` (action `component-unit`).
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import DataExportModal from './DataExportModal.svelte';

beforeAll(async () => {
    await setupI18n();
});

function mount(overrides: Partial<{open: boolean; onexport: (format: 'csv' | 'json') => Promise<void>}> = {}) {
    const onexport = overrides.onexport ?? vi.fn(async () => {});
    const onclose = vi.fn();
    render(DataExportModal, {props: {open: overrides.open ?? true, title: 'Export prices', onexport, onclose}});
    return {onexport, onclose};
}

describe('DataExportModal', () => {
    it('closed: nothing on screen', () => {
        mount({open: false});

        expect(screen.queryByTestId('data-export-modal')).toBeNull();
    });

    it('open: CSV is chosen and JSON is the other choice', () => {
        mount();

        expect(screen.getByTestId('data-export-format-csv')).toBeChecked();
        expect(screen.getByTestId('data-export-format-json')).not.toBeChecked();
    });

    it('Export hands the chosen format to the caller and closes: CSV by default', async () => {
        const {onexport, onclose} = mount();

        await fireEvent.click(screen.getByTestId('data-export-confirm'));

        await waitFor(() => expect(onclose).toHaveBeenCalledTimes(1));
        expect(onexport).toHaveBeenCalledExactlyOnceWith('csv');
    });

    it('Export hands JSON when JSON is chosen', async () => {
        const {onexport, onclose} = mount();

        await fireEvent.click(screen.getByTestId('data-export-format-json'));
        await fireEvent.click(screen.getByTestId('data-export-confirm'));

        await waitFor(() => expect(onclose).toHaveBeenCalledTimes(1));
        expect(onexport).toHaveBeenCalledExactlyOnceWith('json');
    });

    it('a download that fails keeps the dialog open and says so', async () => {
        const onexport = vi.fn(async () => {
            throw new Error('boom');
        });
        const {onclose} = mount({onexport});

        await fireEvent.click(screen.getByTestId('data-export-confirm'));

        await waitFor(() => expect(screen.getByTestId('data-export-error')).toBeVisible());
        expect(onclose).not.toHaveBeenCalled();
        expect(screen.getByTestId('data-export-confirm')).toBeEnabled();
    });

    it('while the download runs, Export cannot be pressed twice', async () => {
        let finish: () => void = () => {};
        const onexport = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)));
        const {onclose} = mount({onexport});

        await fireEvent.click(screen.getByTestId('data-export-confirm'));
        await waitFor(() => expect(screen.getByTestId('data-export-confirm')).toBeDisabled());
        await fireEvent.click(screen.getByTestId('data-export-confirm'));

        expect(onexport).toHaveBeenCalledTimes(1);
        finish();
        await waitFor(() => expect(onclose).toHaveBeenCalledTimes(1));
    });
});
