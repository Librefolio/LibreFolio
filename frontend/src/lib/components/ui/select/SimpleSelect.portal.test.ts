// @vitest-environment jsdom
/**
 * SimpleSelect — the dropdown lives in a portal (lot H6-1, Vitest + jsdom).
 *
 * The problem. The listbox is `position: fixed`, but a fixed element is still painted in the
 * stacking context of its ancestors. A select in a table cell sits in a row that creates one
 * (`tbody tr { position: relative; z-index: 1 }` in DataTable), so the list is painted UNDER the
 * sticky header (z-index 15) when the two overlap. No CSS inside the cell can escape that: the
 * list has to stop being a descendant of the cell.
 *
 * The contract. While the list is open its element is a direct child of `document.body`, moved
 * there with the shared action `use:portal` (`$lib/actions/portal`), and it is gone again as soon as
 * the list closes or the component is destroyed. Everything the list did before is unchanged: the
 * test ids, `role="listbox"`, mouse and keyboard selection, closing on an outside press, Escape.
 *
 * jsdom has no paint order, so the structural fact is what is pinned: the list is not under the
 * select, and no ancestor of it creates a stacking context. The paint order itself is proved in a
 * real browser by `e2e/assets/asset-select-portal.spec.ts`.
 *
 * What `SimpleSelect.test.ts` already pins (keyboard model, disabled options, the highlight) is not
 * repeated; only what changes once the list is outside the component is.
 */
import {describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import type {SelectOption} from './types';
import SimpleSelect from './SimpleSelect.svelte';
import simpleSelectSource from './SimpleSelect.svelte?raw';

const FRUITS: SelectOption[] = [
    {value: 'apple', label: 'Apple'},
    {value: 'banana', label: 'Banana'},
    {value: 'cherry', label: 'Cherry'},
    {value: 'date', label: 'Date'},
];

/** Every open list in the document, whoever owns it: the attribute is published by the component for exactly this. */
function openLists(): HTMLElement[] {
    return [...document.body.querySelectorAll<HTMLElement>('[data-simpleselect-dropdown]')];
}

function mount(testId = 'fruit', props: Partial<ComponentProps<typeof SimpleSelect>> = {}) {
    const onchange = vi.fn();
    const utils = render(SimpleSelect, {
        value: '',
        options: FRUITS,
        testId,
        optionTestId: (option: SelectOption) => `${testId}-opt-${option.value}`,
        ...props,
        onchange,
    });
    return {onchange, trigger: screen.getByTestId(`${testId}-button`), ...utils};
}

/** Opens the list the way a user does and returns it. */
async function open(trigger: HTMLElement, testId = 'fruit'): Promise<HTMLElement> {
    await fireEvent.click(trigger);
    expect(trigger, 'the list did not open: the state under test was never reached').toHaveAttribute('aria-expanded', 'true');
    return screen.getByTestId(`${testId}-dropdown`);
}

describe('SimpleSelect — the list is a child of the body while open (H6-1)', () => {
    it('is a direct child of document.body and not inside the select', async () => {
        await setupI18n();
        const {trigger, container} = mount();

        const list = await open(trigger);

        expect(list.parentElement, 'the open list must be moved to <body>').toBe(document.body);
        expect(container.contains(list), 'the open list is still inside the component’s wrapper').toBe(false);
        expect(screen.getByTestId('fruit').contains(list), 'the open list is still inside the select’s own container').toBe(false);
    });

    it('keeps everything the list published before: role, test id, the portal marker, one listbox', async () => {
        await setupI18n();
        const {trigger} = mount();

        const list = await open(trigger);

        expect(list).toHaveAttribute('role', 'listbox');
        expect(list).toHaveAttribute('data-testid', 'fruit-dropdown');
        expect(list, 'the marker other components use to recognise a click in a select list').toHaveAttribute('data-simpleselect-dropdown', list.id);
        expect(trigger, 'the trigger still points at the list by id').toHaveAttribute('aria-controls', list.id);
        expect(screen.getAllByRole('listbox')).toHaveLength(1);
    });

    it('stays under <html>, so the dark theme still reaches it', async () => {
        await setupI18n();
        document.documentElement.classList.add('dark');
        try {
            const {trigger} = mount();
            const list = await open(trigger);
            expect(list.closest('html.dark'), 'the list is detached from the themed document').not.toBeNull();
        } finally {
            document.documentElement.classList.remove('dark');
        }
    });

    it('keeps its fixed position from the trigger: top, left and the trigger’s width are written on the moved node', async () => {
        await setupI18n();
        const {trigger} = mount('fruit', {matchTriggerWidth: true});

        const list = await open(trigger);

        expect(list.style.top).toMatch(/px$/);
        expect(list.style.left).toMatch(/px$/);
        expect(list.style.minWidth).toMatch(/px$/);
        expect(list.className, 'the list stays position: fixed after the move').toContain('fixed');
    });

    it('uses the shared portal action', () => {
        // The move is the whole fix; a hand-written appendChild would not be removed with the component.
        expect(simpleSelectSource).toMatch(/import\s*\{\s*portal\s*\}\s*from\s*['"]\$lib\/actions\/portal['"]/);
        expect(simpleSelectSource).toMatch(/use:portal/);
    });
});

describe('SimpleSelect — no orphan is left in the body (H6-1)', () => {
    it('removes the list from the body when Escape closes it', async () => {
        await setupI18n();
        const {trigger} = mount();
        await open(trigger);
        expect(openLists()).toHaveLength(1);

        await fireEvent.keyDown(trigger, {key: 'Escape'});

        expect(trigger).toHaveAttribute('aria-expanded', 'false');
        expect(openLists(), 'a list stayed in <body> after Escape').toHaveLength(0);
    });

    it('removes the list from the body when an option is chosen', async () => {
        await setupI18n();
        const {trigger, onchange} = mount();
        await open(trigger);

        await fireEvent.click(screen.getByTestId('fruit-opt-banana'));

        expect(onchange).toHaveBeenCalledExactlyOnceWith('banana');
        expect(trigger).toHaveAttribute('aria-expanded', 'false');
        expect(openLists(), 'a list stayed in <body> after a choice').toHaveLength(0);
    });

    it('removes the list from the body when a press outside closes it', async () => {
        await setupI18n();
        const {trigger, onchange} = mount();
        await open(trigger);

        await fireEvent.mouseDown(document.body);

        expect(trigger).toHaveAttribute('aria-expanded', 'false');
        expect(openLists(), 'a list stayed in <body> after an outside press').toHaveLength(0);
        expect(onchange).not.toHaveBeenCalled();
    });

    it('removes the list from the body when the component is destroyed while open', async () => {
        await setupI18n();
        const {trigger, unmount} = mount();
        await open(trigger);
        expect(openLists()).toHaveLength(1);

        unmount();

        expect(openLists(), 'an open list outlived its select: an orphan in <body>').toHaveLength(0);
    });

    it('draws one list again on every reopening, never an accumulation', async () => {
        await setupI18n();
        const {trigger} = mount();

        for (let round = 0; round < 3; round += 1) {
            await open(trigger);
            expect(openLists(), `round ${round}: one list while open`).toHaveLength(1);
            await fireEvent.keyDown(trigger, {key: 'Escape'});
            expect(openLists(), `round ${round}: none once closed`).toHaveLength(0);
        }
    });

    it('never leaves two lists when a second select is opened after the first', async () => {
        await setupI18n();
        const first = mount('first');
        const second = mount('second');

        await open(first.trigger, 'first');
        expect(openLists()).toHaveLength(1);

        // What a user does: the press that lands on the second trigger is an outside press for the first.
        await fireEvent.mouseDown(second.trigger);
        await open(second.trigger, 'second');

        expect(first.trigger, 'the first select stayed open under the second').toHaveAttribute('aria-expanded', 'false');
        const lists = openLists();
        expect(lists, 'two lists are in <body> at once').toHaveLength(1);
        expect(lists[0]).toHaveAttribute('data-testid', 'second-dropdown');
        expect(lists[0].parentElement).toBe(document.body);
    });
});

describe('SimpleSelect — interaction with the list outside the component (H6-1)', () => {
    it('chooses by click: onchange once with the value, then closed', async () => {
        await setupI18n();
        const {trigger, onchange} = mount('fruit', {value: 'apple'});
        await open(trigger);

        // The press of a real click comes first and happens inside the moved list.
        await fireEvent.mouseDown(screen.getByTestId('fruit-opt-cherry'));
        expect(trigger, 'the press inside the list closed it before the option’s click').toHaveAttribute('aria-expanded', 'true');
        await fireEvent.click(screen.getByTestId('fruit-opt-cherry'));

        expect(onchange).toHaveBeenCalledExactlyOnceWith('cherry');
        expect(trigger).toHaveAttribute('aria-expanded', 'false');
        expect(screen.queryByTestId('fruit-dropdown')).toBeNull();
    });

    it('does not close on a press inside the list: on an option, and on the list itself', async () => {
        await setupI18n();
        const {trigger, onchange} = mount();
        const list = await open(trigger);

        await fireEvent.mouseDown(screen.getByTestId('fruit-opt-banana'));
        expect(trigger).toHaveAttribute('aria-expanded', 'true');
        expect(screen.getByTestId('fruit-dropdown')).toBe(list);

        await fireEvent.mouseDown(list);
        expect(trigger).toHaveAttribute('aria-expanded', 'true');
        expect(openLists()).toHaveLength(1);
        expect(onchange, 'a press is not a choice').not.toHaveBeenCalled();
    });

    it('reads the option under the keyboard highlight from the list in <body>', async () => {
        await setupI18n();
        const {trigger, onchange} = mount('fruit', {value: 'apple'});
        const list = await open(trigger);
        const optionIn = (value: string) => list.querySelector<HTMLElement>(`[data-testid="fruit-opt-${value}"]`)!;

        expect(trigger.getAttribute('aria-activedescendant'), 'the highlight names an option of the moved list').toBe(optionIn('apple').id);

        await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
        expect(trigger).toHaveAttribute('aria-activedescendant', optionIn('banana').id);

        await fireEvent.keyDown(trigger, {key: 'End'});
        expect(trigger).toHaveAttribute('aria-activedescendant', optionIn('date').id);

        await fireEvent.keyDown(trigger, {key: 'Home'});
        expect(trigger).toHaveAttribute('aria-activedescendant', optionIn('apple').id);

        await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
        await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
        await fireEvent.keyDown(trigger, {key: 'Enter'});

        expect(onchange).toHaveBeenCalledExactlyOnceWith('cherry');
        expect(openLists()).toHaveLength(0);
    });

    it('closes on Escape from the trigger and gives the focus back to it', async () => {
        await setupI18n();
        const {trigger} = mount();
        await open(trigger);
        trigger.focus();

        await fireEvent.keyDown(trigger, {key: 'Escape'});

        expect(openLists()).toHaveLength(0);
        expect(trigger).toHaveFocus();
    });
});

describe('SimpleSelect — inside a stacking context of the page (H6-1)', () => {
    /** Whether an element on its own creates a stacking context, from what jsdom can compute (inline styles). */
    function createsStackingContext(element: HTMLElement): boolean {
        const style = getComputedStyle(element);
        const positioned = style.position !== '' && style.position !== 'static';
        return style.isolation === 'isolate' || (positioned && style.zIndex !== '' && style.zIndex !== 'auto') || style.position === 'sticky' || (style.transform !== '' && style.transform !== 'none');
    }

    it('is not a descendant of a sticky, isolated, z-indexed wrapper (the stand-in for the table’s sticky header)', async () => {
        await setupI18n();
        const {trigger, container} = mount();
        // The stand-in: what the sticky header (and the row of an editable cell) does to everything inside it.
        container.style.cssText = 'position: sticky; top: 0; z-index: 5; isolation: isolate; transform: translateZ(0);';
        expect(createsStackingContext(container), 'premise: the wrapper creates a stacking context').toBe(true);

        const list = await open(trigger);

        expect(container.contains(list), 'the list is inside the stacking context: it is painted under whatever is above that context').toBe(false);
        let ancestor: HTMLElement | null = list.parentElement;
        const trapping: string[] = [];
        while (ancestor) {
            if (createsStackingContext(ancestor)) trapping.push(ancestor.tagName.toLowerCase());
            ancestor = ancestor.parentElement;
        }
        expect(trapping, 'an ancestor of the open list creates a stacking context').toEqual([]);
    });

    it('is not a descendant of a clipping wrapper either (overflow hidden)', async () => {
        await setupI18n();
        const {trigger, container} = mount();
        container.style.cssText = 'overflow: hidden; height: 10px;';

        const list = await open(trigger);

        expect(container.contains(list)).toBe(false);
        expect(list.parentElement).toBe(document.body);
    });
});
