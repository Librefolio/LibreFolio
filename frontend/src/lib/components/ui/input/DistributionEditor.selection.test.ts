// @vitest-environment jsdom
/**
 * DistributionEditor — the sector or country table on the selection panel (plan 77, SEL-D2; designer's choice 1a).
 *
 * The bar sits in the section head, between the title and the section's buttons, with no hint while nothing is ticked.
 * «Balance» spreads what is missing over the ticked rows only, and is not offered when the total is already 100
 * (Q-SEL-17: a command that makes no sense to press is not shown); «Delete» asks first, removes the ticked rows and
 * clears the ticks; the count button's × clears them too. Past five rows the table pages, and its pager sits in the
 * balloon below the table.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import DistributionEditor from './DistributionEditor.svelte';

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
    cleanup();
    vi.unstubAllGlobals();
});

function mount(value: Record<string, number>) {
    const onchange = vi.fn();
    render(DistributionEditor, {kind: 'sector', value, onchange});
    const section = screen.getByTestId('distribution-editor-sector');
    return {onchange, section};
}

/** The row checkboxes of the section, in table order (the rows' ids are generated). */
const boxes = (section: HTMLElement) => within(section).getAllByTestId(/^dt-row-checkbox-/);
/** The row whose cell shows `label`: its checkbox. */
function boxOf(section: HTMLElement, label: string): HTMLElement {
    const row = within(section)
        .getAllByRole('row')
        .find((r) => r.textContent?.includes(label));
    if (!row) throw new Error(`no row shows ${label}`);
    return within(row).getByTestId(/^dt-row-checkbox-/);
}
const before = (a: Element, b: Element) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1);
const lastValue = (spy: ReturnType<typeof vi.fn>) => spy.mock.calls.at(-1)?.[0] as Record<string, number>;

describe('Distribution: the bar in the section head (77 SEL-D2)', () => {
    it('nothing ticked: the head has its title and buttons, no hint', () => {
        const {section} = mount({Technology: 0.6, Energy: 0.4});
        const head = within(section).getByTestId('distribution-head-sector');
        expect(within(head).getByTestId('distribution-add-sector')).toBeInTheDocument();
        expect(within(section).queryByTestId('selection-toolbar-hint')).toBeNull();
        expect(within(section).queryByTestId('selection-toolbar')).toBeNull();
    });

    it('a total short of 100: «Balance 2» and «Delete 2» in the head; Balance fills only the ticked rows', async () => {
        const {section, onchange} = mount({Technology: 0.5, Energy: 0.2, Utilities: 0.1});
        await fireEvent.click(boxOf(section, 'Technology'));
        await fireEvent.click(boxOf(section, 'Utilities'));
        const head = within(section).getByTestId('distribution-head-sector');
        const bar = within(head).getByTestId('selection-toolbar');
        expect(before(within(head).getByTestId('distribution-title-sector'), bar)).toBe(-1);
        expect(before(bar, within(head).getByTestId('distribution-add-sector'))).toBe(-1);
        expect(within(bar).getByTestId('toolbar-action-balance-count').textContent?.trim()).toBe('2');
        expect(within(bar).getByTestId('toolbar-action-delete-count').textContent?.trim()).toBe('2');

        await fireEvent.click(within(bar).getByTestId('toolbar-action-balance'));
        const next = lastValue(onchange);
        expect(next.Energy, 'an unticked row keeps its weight').toBeCloseTo(0.2, 6);
        expect(next.Technology + next.Energy + next.Utilities).toBeCloseTo(1, 4);
        expect(next.Technology).toBeGreaterThan(0.5);
        expect(next.Utilities).toBeGreaterThan(0.1);
    });

    it('a total of 100: «Balance» is not offered, «Delete» is', async () => {
        const {section} = mount({Technology: 0.6, Energy: 0.4});
        await fireEvent.click(boxOf(section, 'Energy'));
        const bar = within(section).getByTestId('selection-toolbar');
        expect(within(bar).queryByTestId('toolbar-action-balance')).toBeNull();
        expect(within(bar).getByTestId('toolbar-action-delete-count').textContent?.trim()).toBe('1');
    });

    it('«Delete» asks, then removes the ticked rows and clears the ticks', async () => {
        const {section, onchange} = mount({Technology: 0.5, Energy: 0.3, Utilities: 0.2});
        await fireEvent.click(boxOf(section, 'Energy'));
        await fireEvent.click(within(section).getByTestId('toolbar-action-delete'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(Object.keys(lastValue(onchange)).sort()).toEqual(['Technology', 'Utilities']));
        expect(within(section).queryByTestId('selection-toolbar')).toBeNull();
        for (const box of boxes(section)) expect(box).toHaveAttribute('data-state', 'unchecked');
    });

    it('the count button’s × clears the ticks of the table', async () => {
        const {section} = mount({Technology: 0.6, Energy: 0.4});
        await fireEvent.click(boxOf(section, 'Technology'));
        await fireEvent.click(within(section).getByTestId('selection-toolbar-clear'));
        expect(boxOf(section, 'Technology')).toHaveAttribute('data-state', 'unchecked');
        expect(within(section).queryByTestId('selection-toolbar')).toBeNull();
    });

    it('ticked rows put the head in selection mode; the title stays in the DOM; the last row deleted leaves it', async () => {
        // Below 40rem of head (a container query: only a browser measures it, e2e `asset-profile-edit`) the bar takes
        // the title's place: the title is visually hidden, never removed (designer, 20/11, option (a)).
        const {section} = mount({Technology: 0.5, Energy: 0.3, Utilities: 0.2});
        const head = within(section).getByTestId('distribution-head-sector');
        expect(head).toHaveAttribute('data-selecting', 'false');
        await fireEvent.click(boxOf(section, 'Energy'));
        expect(head).toHaveAttribute('data-selecting', 'true');
        expect(within(head).getByTestId('distribution-title-sector').textContent?.trim()).not.toBe('');
        await fireEvent.click(within(section).getByTestId('toolbar-action-delete'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(within(section).getByTestId('distribution-head-sector')).toHaveAttribute('data-selecting', 'false'));
    });

    it('past five rows the pager sits in the balloon below the table', () => {
        const {section} = mount({Technology: 0.2, Energy: 0.2, Utilities: 0.2, Industrials: 0.1, Materials: 0.1, Financials: 0.1, Healthcare: 0.1});
        const dock = within(section).getByTestId('dt-dock');
        expect(within(dock).getByTestId('data-table-pagination')).toBeInTheDocument();
    });
});

describe('Distribution: the row menu (77 SEL-M)', () => {
    /** Open the row menu of the row that shows `label`, through its ⋮. */
    async function openRowMenu(section: HTMLElement, label: string): Promise<HTMLElement> {
        const row = within(section)
            .getAllByRole('row')
            .find((r) => r.textContent?.includes(label));
        if (!row) throw new Error(`no row shows ${label}`);
        const kebab = within(row).getByTestId(/^row-actions-/);
        // jsdom has no layout: a menu anchored on a ⋮ of no size closes at once
        vi.spyOn(kebab, 'getBoundingClientRect').mockReturnValue(new DOMRect(10, 10, 24, 24));
        await fireEvent.click(kebab);
        return screen.findByTestId('context-menu');
    }

    it('at a total of 100 there is nothing to balance: «Balance» is not offered; below it is', async () => {
        const {section} = mount({Technology: 0.6, Energy: 0.4});
        let menu = await openRowMenu(section, 'Energy');
        expect(within(menu).queryByTestId('context-menu-action-balance')).toBeNull();
        await fireEvent.keyDown(window, {key: 'Escape'});
        await waitFor(() => expect(screen.queryByTestId('context-menu')).toBeNull());
        cleanup();

        const short = mount({Technology: 0.5, Energy: 0.3});
        menu = await openRowMenu(short.section, 'Energy');
        expect(within(menu).getByTestId('context-menu-action-balance')).not.toHaveAttribute('aria-disabled');
    });
});

// 81 U48 (issue #89) — sorted on the weight, a weight typed out of order does not move its row from under the cursor.
describe('Distribution: the order holds while a weight is typed (81 U48)', () => {
    const rowOf = (section: HTMLElement, label: string): HTMLElement => {
        const row = within(section)
            .getAllByRole('row')
            .find((r) => r.textContent?.includes(label));
        if (!row) throw new Error(`no row shows ${label}`);
        return row;
    };
    const weightField = (section: HTMLElement, label: string) => rowOf(section, label).querySelector('input.cell-editable-number') as HTMLInputElement;
    const order = (section: HTMLElement) => [...section.querySelectorAll('tbody tr[data-row-id]')].map((r) => r.querySelector('input.cell-editable-number') as HTMLInputElement).map((i) => i.value);

    it('the row keeps its place and the focus until the field is left, then the table sorts again', async () => {
        const {section} = mount({Technology: 0.5, Energy: 0.3, Utilities: 0.1});
        await fireEvent.click(within(section).getByTestId('dt-sort-weight'));
        expect(order(section)).toEqual(['10', '30', '50']);

        const field = weightField(section, 'Utilities');
        field.focus();
        await fireEvent.input(field, {target: {value: '90'}});

        expect(order(section), 'the row of the weight being typed stayed first').toEqual(['90', '30', '50']);
        expect(document.activeElement).toBe(field);
        expect(weightField(section, 'Utilities')).toBe(field);

        field.blur();
        await waitFor(() => expect(order(section)).toEqual(['30', '50', '90']));
    });
});
