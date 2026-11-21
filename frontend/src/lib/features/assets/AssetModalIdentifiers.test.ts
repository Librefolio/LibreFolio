// @vitest-environment jsdom
/**
 * AssetModalIdentifiers — the Identifiers section on the selection panel (plan 77, SEL-D2; designer's choice 1a).
 *
 * The bar sits in the section's head, between the title and the section's own buttons, with no hint while nothing is
 * ticked. «Delete» carries the number of ticked rows and hands exactly those ids to the modal, which confirms; the count
 * button's × clears the ticks of the table too. With no row the head is still there, with its «Add».
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import AssetModalIdentifiers from './AssetModalIdentifiers.svelte';
import type {IdentifierRow} from './assetIdentifiers';

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

const ROWS: IdentifierRow[] = [
    {id: 'isin', type: 'ISIN', value: 'US0378331005'},
    {id: 'ticker', type: 'TICKER', value: 'AAPL'},
    {id: 'figi', type: 'FIGI', value: 'BBG000B9XRY4'},
];

function mount(rows: IdentifierRow[] = ROWS) {
    const onbulkdelete = vi.fn();
    render(AssetModalIdentifiers, {props: {rows, selectedIds: [], hasProvider: false, askingProvider: false, onmanualedit: () => {}, onaskprovider: () => {}, onbulkdelete} as never});
    return {onbulkdelete, section: screen.getByTestId('asset-modal-identifiers')};
}

/** Document order of two elements: negative when `a` comes before `b`. */
const before = (a: Element, b: Element) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1);

describe('Identifiers: the bar in the section head (77 SEL-D2)', () => {
    it('nothing ticked: the head has its title and buttons, no hint', () => {
        const {section} = mount();
        const head = within(section).getByTestId('asset-modal-identifiers-head');
        expect(within(head).getByTestId('asset-modal-add-identifier')).toBeInTheDocument();
        expect(within(section).queryByTestId('selection-toolbar-hint')).toBeNull();
        expect(within(section).queryByTestId('selection-toolbar')).toBeNull();
    });

    it('two ticked: «Delete 2» sits in the head between the title and «Add», and hands those two ids', async () => {
        const {section, onbulkdelete} = mount();
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-isin'));
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-figi'));
        const head = within(section).getByTestId('asset-modal-identifiers-head');
        const bar = within(head).getByTestId('selection-toolbar');
        expect(before(within(head).getByTestId('asset-modal-identifiers-title'), bar)).toBe(-1);
        expect(before(bar, within(head).getByTestId('asset-modal-add-identifier'))).toBe(-1);
        expect(within(bar).getByTestId('toolbar-action-delete-count').textContent?.trim()).toBe('2');

        await fireEvent.click(within(bar).getByTestId('toolbar-action-delete'));
        expect(onbulkdelete).toHaveBeenCalledTimes(1);
        expect([...onbulkdelete.mock.calls[0][0]].sort()).toEqual(['figi', 'isin']);
    });

    it('the count button’s × clears the ticks of the table', async () => {
        const {section} = mount();
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-ticker'));
        await fireEvent.click(within(section).getByTestId('selection-toolbar-clear'));
        expect(screen.getByTestId('dt-row-checkbox-ticker')).toHaveAttribute('data-state', 'unchecked');
        expect(within(section).queryByTestId('selection-toolbar')).toBeNull();
    });

    it('with no row the head is still drawn, with «Add»', () => {
        const {section} = mount([]);
        expect(within(section).getByTestId('asset-modal-identifiers-head')).toBeInTheDocument();
        expect(within(section).getByTestId('asset-modal-add-identifier')).toBeInTheDocument();
    });
});
