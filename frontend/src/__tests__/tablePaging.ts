/**
 * Test helper for the tables that page (B8): the reader's way to see every row — the page-size menu, then «all» (size 0).
 *
 * A table of the risk surfaces draws five rows a page (`riskTablePaging.ts`). A case that reads a row past the fifth, or counts the
 * rows, does what the reader does who wants them all: it picks «all». The helper is a no-op when the table has no pagination bar
 * (five rows or fewer), so a fixture that grows or shrinks does not break the cases that call it.
 */
import {flushSync} from 'svelte';

import {fireEvent, screen, waitFor} from './component';

export async function showAllRows(scope: ParentNode = document.body): Promise<void> {
    const trigger = scope.querySelector('[data-testid="pagination-size-trigger"]');
    if (!trigger) return;
    await fireEvent.click(trigger);
    await fireEvent.click(await waitFor(() => screen.getByTestId('pagination-size-option-0')));
}

/**
 * The same, synchronously, for a mount helper that cannot await: native clicks, each followed by `flushSync`, so the rows are
 * in the DOM when the helper returns. Also a no-op without a pagination bar.
 */
export function showAllRowsNow(scope: ParentNode = document.body): void {
    const trigger = scope.querySelector<HTMLElement>('[data-testid="pagination-size-trigger"]');
    if (!trigger) return;
    trigger.click();
    flushSync();
    document.querySelector<HTMLElement>('[data-testid="pagination-size-option-0"]')?.click();
    flushSync();
}
