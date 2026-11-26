// @vitest-environment jsdom
/**
 * TagInput — component test (Vitest + jsdom).
 *
 * TagInput is almost entirely keyboard behaviour: eight keys, three of which
 * change meaning depending on whether the buffer is empty, whether a suggestion
 * is highlighted and whether a chip is focused. Driving that through Playwright
 * would mean finding a page that embeds a tag field and then asserting on a
 * component two levels below the one under test; here the contract is exercised
 * directly.
 *
 * The component is **controlled**: it never mutates `value`, it calls
 * `onchange(next)` and waits to be re-rendered with the result. The tests assert
 * on that call — which is the actual contract — and use `rerender` when the
 * follow-up state matters.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {waitLocale} from 'svelte-i18n';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import TagInput from './TagInput.svelte';

const AVAILABLE = ['alpha', 'beta', 'gamma', 'delta'];

// The ✕ and the toggle are named from the catalogue (85 BTN-2d).
beforeAll(async () => {
    await setupI18n();
});

function setup(props: Record<string, unknown> = {}) {
    const onchange = vi.fn();
    const utils = render(TagInput, {value: [], availableTags: AVAILABLE, onchange, ...props});
    // `query`, not `get`: when the component is disabled it renders no field at
    // all, and that absence is the subject of one of the tests below.
    const field = screen.queryByTestId('tag-input-field') as HTMLInputElement;
    return {onchange, field, ...utils};
}

/** Type into the buffer the way the component sees it: input event, then keydown. */
async function type(field: HTMLInputElement, text: string) {
    await fireEvent.input(field, {target: {value: text}});
}

describe('TagInput', () => {
    it('renders one chip per value', () => {
        setup({value: ['alpha', 'beta']});

        expect(screen.getByTestId('tag-chip-0')).toHaveTextContent('alpha');
        expect(screen.getByTestId('tag-chip-1')).toHaveTextContent('beta');
        expect(screen.queryByTestId('tag-chip-2')).toBeNull();
    });

    it.each([['Enter'], [','], [';'], ['Tab']])('commits the buffer on %s', async (key) => {
        const {onchange, field} = setup();

        await type(field, 'new-tag');
        await fireEvent.keyDown(field, {key});

        expect(onchange).toHaveBeenCalledWith(['new-tag']);
    });

    it('keeps spaces inside a value instead of treating them as a separator', async () => {
        // Deliberate product decision (see the component header): tags are stored
        // comma-separated, so a space is data, not punctuation.
        const {onchange, field} = setup();

        await type(field, 'two words');
        await fireEvent.keyDown(field, {key: ' '});
        expect(onchange).not.toHaveBeenCalled();

        await fireEvent.keyDown(field, {key: 'Enter'});
        expect(onchange).toHaveBeenCalledWith(['two words']);
    });

    it('lets Tab move focus on when there is nothing to commit', async () => {
        const {onchange, field} = setup({value: ['alpha']});

        const ev = new KeyboardEvent('keydown', {key: 'Tab', bubbles: true, cancelable: true});
        await fireEvent(field, ev);

        // Not prevented → the browser's focus navigation still happens. Without
        // this the field would trap the keyboard, which is a serious a11y defect
        // and invisible to any assertion about tags.
        expect(ev.defaultPrevented).toBe(false);
        expect(onchange).not.toHaveBeenCalled();
    });

    it('refuses blanks and duplicates', async () => {
        const {onchange, field} = setup({value: ['alpha']});

        await type(field, '   ');
        await fireEvent.keyDown(field, {key: 'Enter'});
        expect(onchange).not.toHaveBeenCalled();

        await type(field, 'alpha');
        await fireEvent.keyDown(field, {key: 'Enter'});
        expect(onchange).not.toHaveBeenCalled();
    });

    it('removes a chip from its × button', async () => {
        const {onchange} = setup({value: ['alpha', 'beta', 'gamma']});

        await fireEvent.click(screen.getByTestId('tag-chip-remove-1'));

        expect(onchange).toHaveBeenCalledWith(['alpha', 'gamma']);
    });

    it('removes the last chip on Backspace with an empty buffer', async () => {
        const {onchange, field} = setup({value: ['alpha', 'beta']});

        await fireEvent.keyDown(field, {key: 'Backspace'});

        expect(onchange).toHaveBeenCalledWith(['alpha']);
    });

    it('walks the chips with the arrows and deletes the focused one', async () => {
        const {onchange, field} = setup({value: ['alpha', 'beta', 'gamma']});

        // From the input, ArrowLeft lands on the last chip, then walks backwards.
        await fireEvent.keyDown(field, {key: 'ArrowLeft'});
        await fireEvent.keyDown(field, {key: 'ArrowLeft'});
        expect(screen.getByTestId('tag-chip-1')).toHaveClass('ring-2');

        await fireEvent.keyDown(field, {key: 'Delete'});
        expect(onchange).toHaveBeenCalledWith(['alpha', 'gamma']);
    });

    it('suggests only tags that are not already used, filtered by the buffer', async () => {
        const {field} = setup({value: ['alpha']});

        await fireEvent.focus(field);
        expect(screen.queryByTestId('tag-suggestion-alpha')).toBeNull();
        expect(screen.getByTestId('tag-suggestion-beta')).toBeInTheDocument();

        await type(field, 'ta');
        // 'beta' and 'delta' contain "ta"; 'gamma' does not.
        expect(screen.getByTestId('tag-suggestion-beta')).toBeInTheDocument();
        expect(screen.getByTestId('tag-suggestion-delta')).toBeInTheDocument();
        expect(screen.queryByTestId('tag-suggestion-gamma')).toBeNull();
    });

    it('moves the highlight with the arrows and commits it on Enter', async () => {
        const {onchange, field} = setup();

        await fireEvent.focus(field);
        await fireEvent.keyDown(field, {key: 'ArrowDown'});
        expect(screen.getByTestId('tag-suggestion-alpha')).toHaveAttribute('aria-selected', 'true');

        await fireEvent.keyDown(field, {key: 'ArrowDown'});
        expect(screen.getByTestId('tag-suggestion-beta')).toHaveAttribute('aria-selected', 'true');
        expect(screen.getByTestId('tag-suggestion-alpha')).toHaveAttribute('aria-selected', 'false');

        await fireEvent.keyDown(field, {key: 'ArrowUp'});
        expect(screen.getByTestId('tag-suggestion-alpha')).toHaveAttribute('aria-selected', 'true');

        await fireEvent.keyDown(field, {key: 'Enter'});
        expect(onchange).toHaveBeenCalledWith(['alpha']);
    });

    it('indexes suggestions positionally so the highlight can be scrolled to', async () => {
        // Non-regression: the scroll-into-view lookup used to ask for a testid the
        // template never rendered, so it silently did nothing. `data-idx` is the
        // handle it needs — if it disappears, the highlight can walk off-screen
        // again and nothing else in the suite would notice.
        const {field} = setup();

        await fireEvent.focus(field);
        const dropdown = screen.getByTestId('tag-input-dropdown');
        AVAILABLE.forEach((tag, idx) => {
            expect(dropdown.querySelector(`[data-idx="${idx}"]`)).toHaveTextContent(tag);
        });
    });

    it('adds a suggestion when it is clicked', async () => {
        const {onchange, field} = setup();

        await fireEvent.focus(field);
        await fireEvent.mouseDown(screen.getByTestId('tag-suggestion-gamma'));

        expect(onchange).toHaveBeenCalledWith(['gamma']);
    });

    it('closes the dropdown on Escape', async () => {
        const {field} = setup();

        await fireEvent.focus(field);
        expect(screen.getByTestId('tag-input-dropdown')).toBeInTheDocument();

        await fireEvent.keyDown(field, {key: 'Escape'});
        expect(screen.queryByTestId('tag-input-dropdown')).toBeNull();
    });

    it('offers no input at all when disabled', () => {
        setup({value: ['alpha'], disabled: true});

        expect(screen.getByTestId('tag-chip-0')).toHaveTextContent('alpha');
        // Neither the field, nor the toggle, nor the per-chip remove button.
        expect(screen.queryByTestId('tag-input-field')).toBeNull();
        expect(screen.queryByTestId('tag-input-toggle')).toBeNull();
        expect(screen.queryByTestId('tag-chip-remove-0')).toBeNull();
    });
});

/**
 * The ✕ of a tag and the suggestions toggle are standard Buttons (85 BTN-2d), named from the catalogue with the tag's
 * own text: until then they said «remove tag» and «Toggle tag suggestions», in English, in every language.
 */
describe('TagInput — the standard buttons (85 BTN-2d)', () => {
    it.each(['en', 'it'])('the ✕ names its own tag, in the interface’s language (%s)', async (lang) => {
        await setupI18n(lang);
        await waitLocale(lang);
        try {
            setup({value: ['alpha', 'beta']});
            for (const [index, tag] of ['alpha', 'beta'].entries()) {
                const expected = get(_)('common.removeTag', {values: {tag}});
                expect(expected, 'premise: the catalogue names the tag').toContain(tag);
                expect(expected).not.toBe('common.removeTag');
                const remove = screen.getByTestId(`tag-chip-remove-${index}`);
                expect(remove).toHaveAttribute('aria-label', expected);
                expect(remove.hasAttribute('title')).toBe(false);
            }
        } finally {
            cleanup();
            await setupI18n('en');
        }
    });

    it('premise of the case above: the two languages do not say it the same way', async () => {
        const en = get(_)('common.removeTag', {values: {tag: 'alpha'}});
        await setupI18n('it');
        try {
            expect(get(_)('common.removeTag', {values: {tag: 'alpha'}})).not.toBe(en);
        } finally {
            await setupI18n('en');
        }
    });

    it('a click on the ✕ removes its tag and stays its own: it does not reach the chip', async () => {
        const {onchange} = setup({value: ['alpha', 'beta']});
        const chip = screen.getByTestId('tag-chip-0');
        const onChip = vi.fn();
        chip.addEventListener('click', onChip);
        await fireEvent.click(screen.getByTestId('tag-chip-remove-0'));
        expect(onchange).toHaveBeenCalledExactlyOnceWith(['beta']);
        expect(onChip).not.toHaveBeenCalled();
    });

    it('the suggestions toggle is a named disclosure: aria-expanded follows the list', async () => {
        setup();
        const toggle = screen.getByTestId('tag-input-toggle');
        const name = get(_)('common.showSuggestions');
        expect(name).not.toBe('common.showSuggestions');
        expect(toggle).toHaveAttribute('aria-label', name);
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        await fireEvent.click(toggle);
        expect(toggle).toHaveAttribute('aria-expanded', 'true');
        expect(screen.getByTestId('tag-input-dropdown')).toBeInTheDocument();
        await fireEvent.click(toggle);
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        expect(screen.queryByTestId('tag-input-dropdown')).toBeNull();
    });
});
