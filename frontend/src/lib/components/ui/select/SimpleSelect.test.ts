// @vitest-environment jsdom
/**
 * SimpleSelect — component test (Vitest + jsdom).
 *
 * `frontend/e2e/select-components.spec.ts` already drives this component through
 * the language switcher: opening, closing on Escape, closing on an outside click,
 * picking a value. None of that is repeated here.
 *
 * What the E2E cannot reach is everything that depends on an option list it does
 * not control. The language list has no disabled entries, is never empty, and is
 * never loading, so three whole branches of the keyboard logic and two of the
 * dropdown body have never been executed by anything. Those are the subject.
 *
 * The highlighted option is tracked through `aria-activedescendant`, which is
 * both the accessibility contract and the only non-cosmetic expression of the
 * highlight — the alternative would be asserting on a Tailwind class.
 */
import {describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {SelectOption} from './types';
import SimpleSelect from './SimpleSelect.svelte';

/**
 * A list whose *first and last* entries are disabled on purpose: those are the
 * two positions where an off-by-one in the "skip disabled" logic hides, and a
 * fixture that ends on a selectable option cannot see it.
 */
const FRUITS: SelectOption[] = [
    {value: 'acai', label: 'Acai', disabled: true},
    {value: 'apple', label: 'Apple'},
    {value: 'banana', label: 'Banana', disabled: true},
    {value: 'cherry', label: 'Cherry'},
    {value: 'date', label: 'Date', disabled: true},
    {value: 'elderberry', label: 'Elderberry'},
    {value: 'fig', label: 'Fig', disabled: true},
];

function mount(props: Partial<ComponentProps<typeof SimpleSelect>> = {}) {
    const onchange = vi.fn();
    const utils = render(SimpleSelect, {
        value: '',
        options: FRUITS,
        testId: 'fruit',
        optionTestId: (option: SelectOption) => `fruit-opt-${option.value}`,
        ...props,
        onchange,
    });
    const trigger = screen.getByTestId('fruit-button');
    return {onchange, trigger, ...utils};
}

/** The option element for a value the test itself put in the list. */
function option(value: string): HTMLElement {
    return screen.getByTestId(`fruit-opt-${value}`);
}

/** Asserts which option the roving highlight currently points at. */
function expectHighlighted(trigger: HTMLElement, value: string) {
    expect(trigger).toHaveAttribute('aria-activedescendant', option(value).id);
}

describe('SimpleSelect', () => {
    describe('selection', () => {
        it('marks only the current value as selected and reports the new one on change', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({value: 'apple'});

            await fireEvent.click(trigger);

            expect(option('apple')).toHaveAttribute('aria-selected', 'true');
            expect(option('cherry')).toHaveAttribute('aria-selected', 'false');

            await fireEvent.click(option('cherry'));

            expect(onchange).toHaveBeenCalledExactlyOnceWith('cherry');
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(screen.queryByTestId('fruit-dropdown')).toBeNull();
        });

        it('refuses a disabled option', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({value: 'apple'});
            await fireEvent.click(trigger);

            expect(option('banana')).toHaveAttribute('aria-disabled', 'true');
            await fireEvent.click(option('banana'));

            expect(onchange).not.toHaveBeenCalled();
            // The list stays open: nothing was chosen, so there is nothing to close for.
            expect(screen.getByTestId('fruit-dropdown')).toBeInTheDocument();
        });

        it('does not move the highlight onto a disabled option under the pointer', async () => {
            await setupI18n();
            const {trigger} = mount({value: 'apple'});
            await fireEvent.click(trigger);

            await fireEvent.mouseEnter(option('cherry'));
            expectHighlighted(trigger, 'cherry');

            await fireEvent.mouseEnter(option('banana'));
            // Still cherry — a highlight the keyboard would refuse to leave on
            // Enter must not be reachable with the mouse either.
            expectHighlighted(trigger, 'cherry');
        });
    });

    describe('keyboard', () => {
        it('opens on the keys that are supposed to open it', async () => {
            await setupI18n();
            for (const key of ['Enter', ' ', 'ArrowDown', 'ArrowUp']) {
                const {trigger, unmount} = mount();
                expect(trigger).toHaveAttribute('aria-expanded', 'false');

                await fireEvent.keyDown(trigger, {key});

                expect(trigger, `key ${key} should open the dropdown`).toHaveAttribute('aria-expanded', 'true');
                unmount();
            }
        });

        it('starts on the selected option rather than the top of the list', async () => {
            await setupI18n();
            const {trigger} = mount({value: 'elderberry'});

            await fireEvent.click(trigger);

            expectHighlighted(trigger, 'elderberry');
        });

        it('starts on the first selectable option when nothing is selected', async () => {
            await setupI18n();
            // The list opens with no value, so there is no selection to return to.
            const {trigger} = mount({value: ''});

            await fireEvent.click(trigger);

            expectHighlighted(trigger, 'apple');
        });

        it('steps over disabled options in both directions', async () => {
            await setupI18n();
            const {trigger} = mount({value: 'apple'});
            await fireEvent.click(trigger);
            expectHighlighted(trigger, 'apple');

            // banana is disabled, so ArrowDown must land on cherry.
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
            expectHighlighted(trigger, 'cherry');

            // date is disabled too: two in a row are skipped in one press.
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
            expectHighlighted(trigger, 'elderberry');

            await fireEvent.keyDown(trigger, {key: 'ArrowUp'});
            expectHighlighted(trigger, 'cherry');

            await fireEvent.keyDown(trigger, {key: 'ArrowUp'});
            expectHighlighted(trigger, 'apple');
        });

        it('stays put at the ends of the list instead of wrapping', async () => {
            await setupI18n();
            const {trigger} = mount({value: 'apple'});
            await fireEvent.click(trigger);

            // `acai` sits above `apple` and is disabled: there is nowhere legal to
            // go, so the highlight must hold rather than wrap round to the bottom.
            await fireEvent.keyDown(trigger, {key: 'ArrowUp'});
            expectHighlighted(trigger, 'apple');

            // Same at the other end, where `fig` is disabled.
            await fireEvent.keyDown(trigger, {key: 'End'});
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
            expectHighlighted(trigger, 'elderberry');
        });

        it('jumps to the first and last selectable option with Home and End', async () => {
            await setupI18n();
            const {trigger} = mount({value: 'cherry'});
            await fireEvent.click(trigger);

            await fireEvent.keyDown(trigger, {key: 'End'});
            // Not `fig`, which is last in the list but disabled.
            expectHighlighted(trigger, 'elderberry');

            await fireEvent.keyDown(trigger, {key: 'Home'});
            // Not `acai`, which is first in the list but disabled.
            expectHighlighted(trigger, 'apple');
        });

        it('chooses the highlighted option on Enter', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({value: 'apple'});
            await fireEvent.click(trigger);

            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
            await fireEvent.keyDown(trigger, {key: 'Enter'});

            expect(onchange).toHaveBeenCalledExactlyOnceWith('cherry');
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
        });

        it('closes on Tab without choosing anything', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({value: 'apple'});
            await fireEvent.click(trigger);
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});

            await fireEvent.keyDown(trigger, {key: 'Tab'});

            // Moving focus away is not a decision — the highlight is abandoned.
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(onchange).not.toHaveBeenCalled();
            expect(trigger).not.toHaveAttribute('aria-activedescendant');
        });
    });

    describe('unavailable states', () => {
        it('says the list is empty rather than showing an empty box', async () => {
            await setupI18n();
            const {trigger} = mount({options: []});

            await fireEvent.click(trigger);

            const dropdown = screen.getByTestId('fruit-dropdown');
            expect(within(dropdown).getByTestId('fruit-empty')).toBeInTheDocument();
            expect(within(dropdown).queryAllByRole('option')).toHaveLength(0);
            // Nothing to point at, so nothing is announced as active.
            expect(trigger).not.toHaveAttribute('aria-activedescendant');
        });

        it('cannot be opened while disabled', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({disabled: true});

            expect(trigger).toBeDisabled();
            await fireEvent.click(trigger);
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});

            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(screen.queryByTestId('fruit-dropdown')).toBeNull();
            expect(onchange).not.toHaveBeenCalled();
        });

        it('cannot be opened while loading', async () => {
            await setupI18n();
            const {trigger} = mount({loading: true});

            await fireEvent.click(trigger);
            await fireEvent.keyDown(trigger, {key: 'Enter'});

            // Opening onto a list that is about to be replaced would offer stale
            // choices, so the trigger simply does not respond yet.
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(screen.queryByTestId('fruit-dropdown')).toBeNull();
        });

        it('replaces the options with a loading state if it starts loading while open', async () => {
            await setupI18n();
            const {trigger, rerender} = mount({value: 'apple'});
            await fireEvent.click(trigger);
            expect(screen.getByTestId('fruit-opt-apple')).toBeInTheDocument();

            // The parent refreshes the list under an open dropdown.
            await rerender({loading: true});

            const dropdown = screen.getByTestId('fruit-dropdown');
            expect(within(dropdown).getByTestId('fruit-loading')).toBeInTheDocument();
            expect(within(dropdown).queryAllByRole('option')).toHaveLength(0);
        });
    });

    describe('accessible name', () => {
        it('combines the field label with the current selection', async () => {
            await setupI18n();
            // Both halves come from props this test passed, so the assertion holds
            // in every language the app ships in.
            const {trigger} = mount({value: 'cherry', ariaLabel: 'Fruit'});

            expect(trigger).toHaveAttribute('aria-label', 'Fruit, Cherry');
        });

        it('does not repeat itself when the label and the selection coincide', async () => {
            await setupI18n();
            const {trigger} = mount({value: 'cherry', ariaLabel: 'Cherry'});

            // "Cherry, Cherry" is what a naive join would produce, and a screen
            // reader would read it out twice.
            expect(trigger).toHaveAttribute('aria-label', 'Cherry');
        });
    });

    describe('section headers', () => {
        /**
         * A list bracketed by headers: one leads it, one sits between two sections, one trails it.
         * First and last are the positions where a "skip the header" off-by-one hides, and a
         * fixture that began or ended on a real option could never catch them. Only the three plain
         * rows are choosable; the three `header` rows are section labels.
         */
        const SECTIONED: SelectOption[] = [
            {value: '__sec:auto', label: 'Automatic', header: true},
            {value: 'ecb', label: 'ECB'},
            {value: 'boc', label: 'Bank of Canada'},
            {value: '__sec:manual', label: 'Manual', header: true},
            {value: 'fixed', label: 'Fixed rate'},
            {value: '__sec:footer', label: 'Other', header: true},
        ];

        it('renders a header as a label, not one of the listbox options', async () => {
            await setupI18n();
            const {trigger} = mount({options: SECTIONED, value: ''});
            await fireEvent.click(trigger);

            const dropdown = screen.getByTestId('fruit-dropdown');
            // The three real choices are options; the three headers are furniture.
            expect(within(dropdown).getAllByRole('option')).toHaveLength(3);
            expect(screen.queryByTestId('fruit-opt-__sec:auto')).toBeNull();
            expect(screen.getByTestId('fruit-header-__sec:auto')).toBeInTheDocument();
        });

        it('does not select a header when its row is clicked', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({options: SECTIONED, value: ''});
            await fireEvent.click(trigger);

            // Whether the header is a label (correct) or was wrongly rendered as an option (the
            // bug), clicking where it sits must never choose it.
            const header = screen.queryByTestId('fruit-opt-__sec:auto') ?? screen.getByTestId('fruit-header-__sec:auto');
            await fireEvent.click(header);

            expect(onchange).not.toHaveBeenCalled();
            // Nothing was chosen, so the list has no reason to close.
            expect(screen.getByTestId('fruit-dropdown')).toBeInTheDocument();
        });

        it('opens onto the first selectable option, stepping over a leading header', async () => {
            await setupI18n();
            const {trigger} = mount({options: SECTIONED, value: ''});

            await fireEvent.click(trigger);

            // '__sec:auto' is first in the list but a header; the highlight starts below it.
            expectHighlighted(trigger, 'ecb');
        });

        it('steps over the header between two sections with the arrow keys', async () => {
            await setupI18n();
            const {trigger} = mount({options: SECTIONED, value: ''});
            await fireEvent.click(trigger);
            expectHighlighted(trigger, 'ecb');

            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
            expectHighlighted(trigger, 'boc');

            // '__sec:manual' sits between boc and fixed; one press must clear it.
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
            expectHighlighted(trigger, 'fixed');

            await fireEvent.keyDown(trigger, {key: 'ArrowUp'});
            expectHighlighted(trigger, 'boc');
        });

        it('lands Home and End on the first and last selectable option, not a header', async () => {
            await setupI18n();
            const {trigger} = mount({options: SECTIONED, value: 'boc'});
            await fireEvent.click(trigger);

            await fireEvent.keyDown(trigger, {key: 'End'});
            // '__sec:footer' is the last row but a header; End stops at 'fixed'.
            expectHighlighted(trigger, 'fixed');

            await fireEvent.keyDown(trigger, {key: 'Home'});
            // '__sec:auto' is the first row but a header; Home stops at 'ecb'.
            expectHighlighted(trigger, 'ecb');
        });

        it('never yields a header value through the keyboard', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({options: SECTIONED, value: ''});
            await fireEvent.click(trigger);

            // The highlight opened on a selectable option, so Enter chooses that — never the
            // header that leads the list.
            await fireEvent.keyDown(trigger, {key: 'Enter'});
            expect(onchange).toHaveBeenCalledExactlyOnceWith('ecb');
        });
    });
});
