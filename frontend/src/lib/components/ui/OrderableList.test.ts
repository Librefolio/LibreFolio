// @vitest-environment jsdom
/**
 * OrderableList — the arrows of a row are standard icon Buttons (85 BTN-2a).
 *
 * Below `md` each row carries «Move up» and «Move down»: named from the catalogue (`common.moveUp`, `common.moveDown`)
 * in the user's language, `dense` (a 24 px target, so the two stacked arrows never cover each other). The arrow that
 * cannot move (up on the first row, down on the last) is off but reachable: `aria-disabled`, in the tab order, its name
 * shown at a tap, and its click dropped. The others reorder. Rows are found by the text the test gave them.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, type Snippet} from 'svelte';
import {get} from 'svelte/store';
import {_} from 'svelte-i18n';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import OrderableList from './OrderableList.svelte';

const ITEMS = ['alpha', 'beta', 'gamma'];

const row = createRawSnippet<[{item: string; index: number}]>((args) => ({render: () => `<span data-testid="probe-item-${args().item}">${args().item}</span>`}));

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

function mount(props: Record<string, unknown> = {}) {
    const onReorder = vi.fn();
    // The list is generic; mounted from a test it sees `unknown` items, so the string helpers are widened to it.
    const keyFn = ((item: string) => item) as (item: unknown) => string;
    const children = row as unknown as Snippet<[{item: unknown; index: number}]>;
    render(OrderableList, {props: {items: ITEMS, keyFn, onReorder, children, ...props}});
    return {onReorder};
}

/** The up and down arrows of the row holding `item`. */
function arrows(item: string): {up: HTMLElement; down: HTMLElement} {
    const listItem = screen.getByTestId(`probe-item-${item}`).closest<HTMLElement>('[role="listitem"]');
    if (!listItem) throw new Error(`no row for ${item}`);
    const up = get(_)('common.moveUp');
    const down = get(_)('common.moveDown');
    const buttons = within(listItem).getAllByRole('button');
    const find = (name: string) => {
        const found = buttons.find((button) => button.getAttribute('aria-label') === name);
        if (!found) throw new Error(`no «${name}» in the row of ${item}: ${buttons.map((b) => b.getAttribute('aria-label')).join(', ')}`);
        return found;
    };
    return {up: find(up), down: find(down)};
}

describe('OrderableList — the arrows (85 BTN-2a)', () => {
    it('are named from the catalogue, never the raw keys, with no title', () => {
        mount();
        expect(get(_)('common.moveUp')).not.toBe('common.moveUp');
        expect(get(_)('common.moveDown')).not.toBe('common.moveDown');
        const {up, down} = arrows('beta');
        expect(up.hasAttribute('title')).toBe(false);
        expect(down.hasAttribute('title')).toBe(false);
        expect(up.classList.contains('lf-btn-dense'), 'stacked neighbours: the 24 px target').toBe(true);
    });

    it('the first «up» is off but reachable: aria-disabled, focusable, its click dropped', async () => {
        const {onReorder} = mount();
        const {up} = arrows('alpha');
        expect(up).toHaveAttribute('aria-disabled', 'true');
        expect(up.hasAttribute('disabled'), 'never natively disabled: the name must reach the finger').toBe(false);
        expect(up.tabIndex).toBe(0);
        expect(await fireEvent.click(up), 'the click is cancelled').toBe(false);
        expect(onReorder).not.toHaveBeenCalled();
    });

    it('the last «down» is off too', () => {
        mount();
        expect(arrows('gamma').down).toHaveAttribute('aria-disabled', 'true');
        expect(arrows('gamma').up).not.toHaveAttribute('aria-disabled');
    });

    it('a live arrow reorders (the positive control)', async () => {
        const {onReorder} = mount();
        await fireEvent.click(arrows('beta').up);
        expect(onReorder).toHaveBeenCalledExactlyOnceWith(['beta', 'alpha', 'gamma']);
        await fireEvent.click(arrows('beta').down);
        expect(onReorder).toHaveBeenLastCalledWith(['alpha', 'gamma', 'beta']);
    });

    it('a list that cannot be reordered draws no arrows', () => {
        mount({disabled: true});
        const listItem = screen.getByTestId('probe-item-alpha').closest<HTMLElement>('[role="listitem"]')!;
        expect(within(listItem).queryAllByRole('button')).toEqual([]);
    });
});
