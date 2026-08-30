// @vitest-environment jsdom
/**
 * DataTablePagination — component test (Vitest + jsdom).
 *
 * The floating pager every DataTable mounts once its rows outgrow a page. Until
 * now it was reached only incidentally, through whichever E2E happened to page a
 * table, so its own decisions — the ellipsis window, the page-input parsing, the
 * bounds guard on `goToPage`, the "∞" page size — were exercised by accident.
 * Here each is a prop and a callback: the component owns no data, it hands the
 * parent `onPageChange(pageIndex)` / `onPageSizeChange(pageSize)`, and the
 * assertions are on what the parent receives and on the disabled/enabled state
 * of the two nav buttons, never on the page-size label or the "items" text
 * (those come from the catalogue in four languages).
 *
 * What it deliberately does NOT assert:
 *   - the `.selected` highlight on the current page-size option. It is a
 *     `class:selected={…}` directive with no data mirror; both arms are still
 *     *evaluated* when the dropdown renders with a known size, so the branch is
 *     covered without an assertion on a CSS class (which the suite forbids).
 *   - the sticky/floating position of the balloon. That is CSS only; jsdom has
 *     no layout engine.
 */
import {describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import DataTablePagination from './DataTablePagination.svelte';

/** Mount with sensible defaults; every case overrides only what it exercises. */
function mount(props: Partial<{pageIndex: number; pageSize: number; totalItems: number; pageSizeOptions: number[]}> = {}) {
    const onPageChange = vi.fn();
    const onPageSizeChange = vi.fn();
    const utils = render(DataTablePagination, {
        pageIndex: 0,
        pageSize: 10,
        totalItems: 100,
        pageSizeOptions: [10, 25, 50, 0],
        onPageChange,
        onPageSizeChange,
        ...props,
    });
    return {onPageChange, onPageSizeChange, ...utils};
}

const lastArg = (spy: Mock): number | undefined => spy.mock.calls.at(-1)?.[0];

/** The current-page input (the one page number rendered as an editable field). */
function pageInput(container: HTMLElement): HTMLInputElement {
    const el = container.querySelector<HTMLInputElement>('input.page-input');
    if (!el) throw new Error('page input is not rendered');
    return el;
}

/** The clickable page-number buttons, in DOM order, as their printed labels. */
function pageButtons(container: HTMLElement): string[] {
    return [...container.querySelectorAll('button.page-btn')].map((b) => b.textContent?.trim() ?? '');
}

/** How many ellipsis gaps the pager is showing. */
function ellipsisCount(container: HTMLElement): number {
    return container.querySelectorAll('span.ellipsis').length;
}

describe('DataTablePagination — navigation buttons', () => {
    it('disables prev on the first page and leaves next reachable', async () => {
        await setupI18n();
        mount({pageIndex: 0});
        expect(screen.getByTestId('pagination-prev')).toBeDisabled();
        expect(screen.getByTestId('pagination-next')).toBeEnabled();
    });

    it('disables next on the last page and leaves prev reachable', async () => {
        await setupI18n();
        mount({pageIndex: 9, totalItems: 100, pageSize: 10}); // 10 pages, on the last
        expect(screen.getByTestId('pagination-next')).toBeDisabled();
        expect(screen.getByTestId('pagination-prev')).toBeEnabled();
    });

    it('enables both on a middle page', async () => {
        await setupI18n();
        mount({pageIndex: 4});
        expect(screen.getByTestId('pagination-prev')).toBeEnabled();
        expect(screen.getByTestId('pagination-next')).toBeEnabled();
    });

    it('moves forward and back by one page through the parent callback', async () => {
        await setupI18n();
        const {onPageChange} = mount({pageIndex: 4});
        await fireEvent.click(screen.getByTestId('pagination-next'));
        expect(lastArg(onPageChange)).toBe(5);
        await fireEvent.click(screen.getByTestId('pagination-prev'));
        expect(lastArg(onPageChange)).toBe(3);
    });

    it('jumps straight to a numbered page button', async () => {
        await setupI18n();
        const {onPageChange, container} = mount({pageIndex: 0, totalItems: 30, pageSize: 10}); // 3 pages, all shown
        expect(pageButtons(container)).toEqual(['2', '3']); // page 1 is the input
        const three = [...container.querySelectorAll('button.page-btn')].find((b) => b.textContent?.trim() === '3')!;
        await fireEvent.click(three);
        expect(lastArg(onPageChange)).toBe(2); // 0-based
    });
});

describe('DataTablePagination — the ellipsis window', () => {
    it('shows every page and no ellipsis when there are seven or fewer', async () => {
        await setupI18n();
        const {container} = mount({pageIndex: 0, totalItems: 70, pageSize: 10}); // exactly 7 pages
        expect(ellipsisCount(container)).toBe(0);
        expect(pageButtons(container)).toEqual(['2', '3', '4', '5', '6', '7']);
    });

    it('shows only a trailing gap near the start', async () => {
        await setupI18n();
        const {container} = mount({pageIndex: 0, totalItems: 100, pageSize: 10}); // 10 pages, on page 1
        expect(ellipsisCount(container)).toBe(1);
        // [1] 2 … 10  — 1 is the input, so the buttons are 2 and 10.
        expect(pageButtons(container)).toEqual(['2', '10']);
    });

    it('shows a gap on both sides in the middle', async () => {
        await setupI18n();
        const {container} = mount({pageIndex: 4, totalItems: 100, pageSize: 10}); // page 5 of 10
        expect(ellipsisCount(container)).toBe(2);
        // 1 … 4 [5] 6 … 10  — 5 is the input.
        expect(pageButtons(container)).toEqual(['1', '4', '6', '10']);
    });

    it('shows only a leading gap near the end', async () => {
        await setupI18n();
        const {container} = mount({pageIndex: 9, totalItems: 100, pageSize: 10}); // page 10 of 10
        expect(ellipsisCount(container)).toBe(1);
        // 1 … 9 [10]  — 10 is the input.
        expect(pageButtons(container)).toEqual(['1', '9']);
    });
});

describe('DataTablePagination — the page input', () => {
    it('commits a typed page on Enter', async () => {
        await setupI18n();
        const {onPageChange, container} = mount({pageIndex: 0, totalItems: 100, pageSize: 10});
        const input = pageInput(container);
        await fireEvent.input(input, {target: {value: '4'}});
        await fireEvent.keyDown(input, {key: 'Enter'});
        expect(lastArg(onPageChange)).toBe(3); // 0-based
    });

    it('ignores a non-numeric entry on Enter', async () => {
        await setupI18n();
        const {onPageChange, container} = mount({pageIndex: 0});
        const input = pageInput(container);
        await fireEvent.input(input, {target: {value: 'abc'}});
        await fireEvent.keyDown(input, {key: 'Enter'});
        expect(onPageChange).not.toHaveBeenCalled();
    });

    it('ignores a page beyond the last one', async () => {
        await setupI18n();
        const {onPageChange, container} = mount({pageIndex: 0, totalItems: 30, pageSize: 10}); // 3 pages
        const input = pageInput(container);
        await fireEvent.input(input, {target: {value: '99'}});
        await fireEvent.keyDown(input, {key: 'Enter'});
        expect(onPageChange).not.toHaveBeenCalled();
    });

    it('selects the whole field when the user clicks it to edit', async () => {
        await setupI18n();
        const {container} = mount({pageIndex: 2, totalItems: 100, pageSize: 10}); // page 3
        const input = pageInput(container);
        await fireEvent.click(input);
        // The click handler calls input.select(); jsdom reflects that as a full range.
        expect(input.selectionStart).toBe(0);
        expect(input.selectionEnd).toBe(input.value.length);
    });

    it('restores the current page on Escape without navigating', async () => {
        await setupI18n();
        const {onPageChange, container} = mount({pageIndex: 2, totalItems: 100, pageSize: 10}); // page 3
        const input = pageInput(container);
        await fireEvent.input(input, {target: {value: '7'}});
        await fireEvent.keyDown(input, {key: 'Escape'});
        expect(input.value).toBe('3');
        expect(onPageChange).not.toHaveBeenCalled();
    });

    it('commits a valid page on blur', async () => {
        await setupI18n();
        const {onPageChange, container} = mount({pageIndex: 0, totalItems: 100, pageSize: 10});
        const input = pageInput(container);
        await fireEvent.input(input, {target: {value: '6'}});
        await fireEvent.blur(input);
        expect(lastArg(onPageChange)).toBe(5);
    });

    it('snaps an out-of-range entry back to the current page on blur', async () => {
        await setupI18n();
        const {onPageChange, container} = mount({pageIndex: 1, totalItems: 100, pageSize: 10}); // page 2
        const input = pageInput(container);
        await fireEvent.input(input, {target: {value: '0'}});
        await fireEvent.blur(input);
        expect(input.value).toBe('2');
        expect(onPageChange).not.toHaveBeenCalled();
    });
});

describe('DataTablePagination — page size', () => {
    /** Opens the size dropdown and returns its option buttons. */
    async function openSizeMenu(container: HTMLElement): Promise<HTMLButtonElement[]> {
        const toggle = container.querySelector<HTMLButtonElement>('button.page-size-btn')!;
        await fireEvent.click(toggle);
        return [...container.querySelectorAll<HTMLButtonElement>('.page-size-dropdown button.dropdown-option')];
    }

    it('opens the dropdown and reports the chosen size to the parent', async () => {
        await setupI18n();
        const {onPageSizeChange, container} = mount({pageSize: 10});
        const options = await openSizeMenu(container);
        const twentyFive = options.find((o) => o.textContent?.trim() === '25')!;
        await fireEvent.click(twentyFive);
        expect(lastArg(onPageSizeChange)).toBe(25);
    });

    it('maps the ∞ option to a very large page size', async () => {
        await setupI18n();
        const {onPageSizeChange, container} = mount({pageSize: 10});
        const options = await openSizeMenu(container);
        const infinity = options.find((o) => o.textContent?.trim() === '∞')!;
        await fireEvent.click(infinity);
        expect(lastArg(onPageSizeChange)).toBe(999999);
    });

    it('prints the current size as ∞ when the table is showing everything', async () => {
        await setupI18n();
        const {container} = mount({pageSize: 999999});
        const toggle = container.querySelector<HTMLButtonElement>('button.page-size-btn')!;
        expect(toggle.textContent?.trim()).toBe('∞');
    });

    it('closes the dropdown on an outside click', async () => {
        await setupI18n();
        const {container} = mount();
        const toggle = container.querySelector<HTMLButtonElement>('button.page-size-btn')!;
        await fireEvent.click(toggle);
        expect(container.querySelector('.page-size-dropdown')).not.toBeNull();
        await fireEvent.click(document.body);
        expect(container.querySelector('.page-size-dropdown')).toBeNull();
    });
});

/*
 * Branches deliberately left uncovered (measured with monocart/v8, `mcr merge
 * --reports json`, reading `b`/`branchMap`). 3 of 37 remain, all either dead by
 * construction or a coverage-tool artifact — none is a reachable user state:
 *
 *   1. getPageNumbers, `if (totalPages > 1) pages.push(totalPages)`. This line
 *      only runs inside the `totalPages > 7` block, so `totalPages > 1` is always
 *      true there; the false arm is dead. (A guard the author kept for safety.)
 *
 *   2. the page input's `onclick`, `if (el instanceof HTMLInputElement)`. The
 *      handler is bound to the <input>, so `e.target` is always that input; the
 *      false arm cannot fire. The true arm (`el.select()`) IS exercised by
 *      "selects the whole field when the user clicks it" — that test only passes
 *      because select() actually ran (selectionEnd becomes value.length), yet the
 *      merged report still marks the arm uncovered. monocart's remap of Svelte's
 *      compiled output places these branch locations approximately, so the last
 *      two residuals are reported at source positions (75:8, 135:70) that do not
 *      correspond to a real un-taken decision. Both the blur-else (an invalid
 *      page snapping back) and the input click-select are covered by name above.
 *
 * Nothing here is chased further: there is no user who reaches an un-taken side
 * of any of the three.
 */
