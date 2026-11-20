// @vitest-environment jsdom
/**
 * UploadStep — the files of step 1 on the selection panel (plan 77, SEL-D; Q-SEL-8, Q-SEL-15, Q-SEL-1).
 *
 * The table of the files about to be uploaded draws its bar itself: at the top of the table, with the shared hint while
 * nothing is ticked, and «Remove» with the number of files it takes once some are. «Remove» takes the ticked files out
 * of the list and clears the ticks; the count button's × clears them too.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import UploadStep from './UploadStep.svelte';
import type {ColumnDef} from '$lib/components/table/types';
import type {PendingFileEntry} from './wizardTypes';

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    vi.stubGlobal(
        'IntersectionObserver',
        class {
            observe() {}
            unobserve() {}
            disconnect() {}
            takeRecords() {
                return [];
            }
        },
    );
});

afterEach(() => {
    vi.unstubAllGlobals();
});

const entry = (id: string): PendingFileEntry => ({id, file: new File(['x'], `${id}.csv`), fileName: `${id}.csv`, brokerId: null, status: 'pending'});
const columns: ColumnDef<PendingFileEntry>[] = [{id: 'name', header: 'Name', type: 'text', cell: (row) => row.fileName, getValue: (row) => row.fileName}];

function mount(files: PendingFileEntry[]) {
    const removePendingFilesByIds = vi.fn();
    render(UploadStep, {
        props: {
            brokers: [],
            brokersLoading: false,
            createBrokerContext: null,
            createBrokerOpen: false,
            dropZoneContainerRef: undefined,
            dropZoneExpanded: false,
            fileUploaderRef: undefined,
            globalBrokerId: null,
            pendingFiles: files,
            step1SelectedIds: [],
            step1SetWarnings: [],
            step1TableRef: undefined,
            uploadError: null,
            uploading: false,
            pendingFileActions: [],
            pendingFileColumns: columns,
            formatSetDay: (iso: string | null | undefined) => iso ?? '',
            handleFilesChanged: () => {},
            onGlobalBrokerChange: () => {},
            removePendingFilesByIds,
        } as never,
    });
    return {removePendingFilesByIds};
}

describe('step 1: the files on the selection panel (77 SEL-D)', () => {
    it('nothing ticked: the bar at the top of the table holds the hint', () => {
        mount([entry('a'), entry('b')]);
        expect(screen.getByTestId('dt-selection-top')).toBeInTheDocument();
        expect(screen.getByTestId('selection-toolbar-hint')).toBeInTheDocument();
        expect(screen.queryByTestId('selection-toolbar')).toBeNull();
    });

    it('«Remove» carries the number of ticked files and removes exactly those, then clears the ticks', async () => {
        const {removePendingFilesByIds} = mount([entry('a'), entry('b'), entry('c')]);
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-a'));
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-c'));
        const bar = screen.getByTestId('selection-toolbar');
        expect(bar).toHaveAttribute('data-variant', 'top');
        expect(screen.getByTestId('toolbar-action-bulk-delete-count').textContent?.trim()).toBe('2');

        await fireEvent.click(screen.getByTestId('toolbar-action-bulk-delete'));
        expect(removePendingFilesByIds).toHaveBeenCalledTimes(1);
        expect([...removePendingFilesByIds.mock.calls[0][0]].sort()).toEqual(['a', 'c']);
        await waitFor(() => expect(screen.getByTestId('dt-row-checkbox-a')).toHaveAttribute('data-state', 'unchecked'));
        expect(screen.getByTestId('dt-row-checkbox-c')).toHaveAttribute('data-state', 'unchecked');
    });

    it('the count button’s × clears the ticks', async () => {
        mount([entry('a'), entry('b')]);
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-b'));
        await fireEvent.click(screen.getByTestId('selection-toolbar-clear'));
        expect(screen.getByTestId('dt-row-checkbox-b')).toHaveAttribute('data-state', 'unchecked');
        expect(screen.queryByTestId('selection-toolbar')).toBeNull();
    });
});
