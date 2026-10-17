// @vitest-environment jsdom
/**
 * PromoteMergeModal — component test (Vitest + jsdom).
 *
 * The dialog the bulk editor raises when the two rows it promotes into a pair carry a different
 * description or different tags: one block per field that differs — the left row's value, the right
 * row's, and an editable result that starts as both combined — then Confirm, which answers with the
 * resolved value of each field that differs, or Cancel.
 *
 * Why a component test. Which test ids the dialog publishes, and what its two footer buttons answer,
 * are props in, DOM and callbacks out. The promotion around it — the editor merging the two rows and
 * saving the pair — is e2e/transactions/tx-bulk-promote-exec.spec.ts (PE2 confirms, PE3 cancels).
 *
 * W-B44, one test id per element. Before it, with the dialog open, `promote-merge-modal` was stamped
 * twice — on ModalBase's dialog and again on the content wrapper inside it — and Cancel had none, so a
 * spec could reach neither the dialog nor its Cancel by test id (PE2 keys the open state off Confirm
 * for that reason). The contract: the dialog alone carries `promote-merge-modal`, as gallery.spec.ts
 * reads it (`[data-testid="promote-merge-modal"][role="dialog"]`); the wrapper is
 * `promote-merge-modal-content`, as TransactionActionModal's is `tx-action-modal-content`; Cancel is
 * `promote-merge-cancel`, beside Confirm's `promote-merge-confirm`.
 *
 * On text. `$lib/i18n` is replaced by a translator that renders a key with its values
 * (`key(name=value)`), as in PromoteAllModal.test.ts. Nothing here reads a label: elements are found
 * by test id and role, and the resolved fields are checked against the props this file passes in.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {readable, writable} from 'svelte/store';
import {fireEvent, render, screen, within} from '$test/component';
import {uiLocale} from '$lib/stores/app/uiLocale';

vi.mock('$lib/i18n', async (importOriginal) => {
    const shown = (key: string, options?: {values?: Record<string, unknown>}) => {
        const values = options?.values;
        if (!values) return key;
        const listed = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return `${key}(${listed.join(', ')})`;
    };
    const translator = readable(shown);
    // The module's other exports stay real (the supported locales, the default language): the interface-locale store
    // reads them, for this file's control on the locale and for any figure formatter the dialog may use (W-B70).
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator, locale: writable('en')};
});

import PromoteMergeModal from './PromoteMergeModal.svelte';

type Props = ComponentProps<typeof PromoteMergeModal>;

/** The two rows of the pair, as the bulk editor passes them: different descriptions, different tags sharing one. */
const TX_A = {label: '#41', description: 'Savings out', tags: ['savings', 'monthly'], date: '2026-03-02'};
const TX_B = {label: '#42', description: 'Savings in', tags: ['monthly', 'transfer'], date: '2026-03-02'};

const onConfirm = vi.fn<Props['onConfirm']>();
const onCancel = vi.fn<Props['onCancel']>();

function props(): Props {
    return {open: true, txA: TX_A, txB: TX_B, targetTypeLabel: 'Cash Transfer', onConfirm, onCancel};
}

/**
 * The one element under `root` carrying `testId`. The elements are counted first, so a missing or a
 * repeated id fails with its count instead of a dump of the DOM.
 */
function single(root: HTMLElement, testId: string): HTMLElement {
    expect(within(root).queryAllByTestId(testId).length, `elements carrying data-testid="${testId}"`).toBe(1);
    return within(root).getByTestId(testId);
}

/** Render the dialog open on the pair and return it — the one `role="dialog"` on screen — with both field blocks in it. */
function openDialog(): HTMLElement {
    render(PromoteMergeModal, props());
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).queryByTestId('promote-merge-field-description'), 'precondition: the descriptions differ, so their block is shown').not.toBeNull();
    expect(within(dialog).queryByTestId('promote-merge-field-tags'), 'precondition: the tags differ, so their block is shown').not.toBeNull();
    return dialog;
}

beforeEach(() => {
    onConfirm.mockReset();
    onCancel.mockReset();
});

describe('PromoteMergeModal — one test id per element (W-B44)', () => {
    it('stamps promote-merge-modal on the dialog alone', () => {
        openDialog();
        expect(single(document.body, 'promote-merge-modal'), 'the element carrying it is the dialog').toHaveAttribute('role', 'dialog');
    });

    it('names the content wrapper inside the dialog promote-merge-modal-content', () => {
        const dialog = openDialog();
        const content = single(dialog, 'promote-merge-modal-content');
        // The wrapper of the whole content: the field blocks and the footer are inside it.
        for (const testId of ['promote-merge-field-description', 'promote-merge-field-tags', 'promote-merge-confirm']) {
            expect(within(content).queryByTestId(testId), `${testId} inside the wrapper`).not.toBeNull();
        }
    });

    it('gives Cancel a test id of its own: it answers onCancel once and confirms nothing', async () => {
        const dialog = openDialog();
        const cancel = single(dialog, 'promote-merge-cancel');
        expect(cancel).toHaveRole('button');

        await fireEvent.click(cancel);

        expect(onCancel).toHaveBeenCalledOnce();
        expect(onConfirm).not.toHaveBeenCalled();
    });
});

describe('PromoteMergeModal — confirming', () => {
    it('Confirm answers onConfirm once with every field that differs, both combined by default, and never onCancel', async () => {
        const dialog = openDialog();

        await fireEvent.click(single(dialog, 'promote-merge-confirm'));

        // Only the fields that differ; each as the dialog proposes it untouched: the two descriptions on
        // two lines, the union of the tags in order, the shared one once.
        expect(onConfirm).toHaveBeenCalledExactlyOnceWith({description: 'Savings out\nSavings in', tags: ['savings', 'monthly', 'transfer']});
        expect(onCancel).not.toHaveBeenCalled();
    });
});

/**
 * W-B70 (decision D-W70-3 of the coordinator, 17/10) — the notes' limit, counted under the textarea.
 *
 * A transaction's notes hold 500 characters (`max_length=500`, which the backend counts as Python does: in code
 * points). The dialog proposes both descriptions combined, one per line (`mergeStrings`), and nothing checks the
 * length: two descriptions of 300 characters prefill 601, Confirm answers them as they are, and the save is then
 * refused on the promote (`string_too_long`). The contract:
 *   - a counter under the textarea, `promote-merge-desc-counter`, whose text holds the current length in code points
 *     and the limit, 500, with `data-state="ok"` up to 500 and `"over"` past it;
 *   - past 500: the textarea `aria-invalid="true"`, a message `promote-merge-desc-too-long` with `data-max="500"`, and
 *     Confirm disabled; up to 500: no message, the textarea not invalid, Confirm enabled;
 *   - the count follows the text wherever it comes from: typed, or set by the dialog's own choices.
 *
 * Reading. The counter's numbers are matched as whole tokens of its text — no digit, decimal mark or group separator
 * glued to either side — whether the dialog writes them itself or through a translation, which this file's translator
 * renders as `key(name=value)`. They are written in the interface locale, en-US under jsdom (checked before each case);
 * every length here is under 1000, where en-US writes no separator. The message's text is not read. A click past the
 * limit is the native one, `HTMLElement.click()`, which a disabled control never performs, as for a user:
 * `fireEvent.click` dispatches an event that jsdom delivers even to a disabled button, and Svelte runs the handler of
 * the button the event targets. Text is typed by setting the textarea's value and firing `input`, the event
 * `bind:value` listens to.
 *
 * Red today: no counter, no message, no `aria-invalid`, Confirm enabled — and, clicked past the limit, it answers the
 * 601 characters. The case of 300 😀 (600 UTF-16 units) guards the count in code points; the last case, green today,
 * guards that the counter belongs to the description block, shown only when the descriptions differ.
 */
describe('PromoteMergeModal — the notes’ limit (W-B70, D-W70-3)', () => {
    const LIMIT = 500;
    const LEFT_300 = 'L'.repeat(300);
    const RIGHT_300 = 'R'.repeat(300);

    /** The dialog and the elements a case reads. */
    interface View {
        dialog: HTMLElement;
        block: HTMLElement;
        textarea: HTMLTextAreaElement;
        confirm: HTMLButtonElement;
    }

    /** The length the dialog must count: code points, as the backend counts them. */
    const codePoints = (text: string): number => Array.from(text).length;

    /** `value` as the interface locale writes it, matched as a whole token of a text. */
    function numberToken(value: number): RegExp {
        const written = new Intl.NumberFormat(uiLocale()).format(value);
        return new RegExp(`(?<![\\d.,])${written.replace(/[.,]/g, '\\$&')}(?![.,]?\\d)`);
    }

    /** The dialog open on `props`, with its description block, textarea and Confirm. */
    function viewOf(overrides: Partial<Props>): View {
        render(PromoteMergeModal, {...props(), ...overrides});
        const dialog = screen.getByRole('dialog');
        const block = single(dialog, 'promote-merge-field-description');
        return {dialog, block, textarea: single(block, 'promote-merge-desc-input') as HTMLTextAreaElement, confirm: single(dialog, 'promote-merge-confirm') as HTMLButtonElement};
    }

    /** Two rows whose descriptions differ and whose tags agree: the description block is the only one. */
    function openOnDescriptions(descriptionA: string, descriptionB: string): View {
        const view = viewOf({txA: {...TX_A, description: descriptionA, tags: ['monthly']}, txB: {...TX_B, description: descriptionB, tags: ['monthly']}});
        expect(within(view.dialog).queryByTestId('promote-merge-field-tags'), 'precondition: the tags agree, so theirs is not shown').toBeNull();
        return view;
    }

    /** The counter: one, inside the description block, after the textarea. */
    function counterOf({block, textarea}: View): HTMLElement {
        const counter = single(block, 'promote-merge-desc-counter');
        expect(textarea.compareDocumentPosition(counter) & Node.DOCUMENT_POSITION_FOLLOWING, 'the counter comes after the textarea').toBeTruthy();
        return counter;
    }

    /** The counter shows `length` and the limit, in the state they make. */
    function expectCounter(view: View, length: number, state: 'ok' | 'over'): void {
        const counter = counterOf(view);
        expect(counter.textContent, `the counter holds the length, ${length}`).toMatch(numberToken(length));
        expect(counter.textContent, `and the limit, ${LIMIT}`).toMatch(numberToken(LIMIT));
        expect(counter).toHaveAttribute('data-state', state);
    }

    /** Past the limit: counter over, textarea invalid, the message naming the limit, Confirm disabled. */
    function expectOver(view: View, length: number): void {
        expectCounter(view, length, 'over');
        expect(view.textarea).toHaveAttribute('aria-invalid', 'true');
        expect(single(view.dialog, 'promote-merge-desc-too-long')).toHaveAttribute('data-max', String(LIMIT));
        expect(view.confirm).toBeDisabled();
    }

    /** Within the limit: counter ok, the textarea not invalid, no message, Confirm enabled. */
    function expectWithin(view: View, length: number): void {
        expectCounter(view, length, 'ok');
        expect(['false', null], 'the textarea is not invalid').toContain(view.textarea.getAttribute('aria-invalid'));
        expect(within(view.dialog).queryByTestId('promote-merge-desc-too-long'), 'no too-long message').toBeNull();
        expect(view.confirm).toBeEnabled();
    }

    /** Make `text` the textarea's whole value, as typing it would. */
    async function typeInto(textarea: HTMLTextAreaElement, text: string): Promise<void> {
        await fireEvent.input(textarea, {target: {value: text}});
        expect(textarea.value).toBe(text);
    }

    beforeEach(() => {
        expect(uiLocale(), 'control: the interface on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    it('two descriptions of 300 prefill 601 characters: the counter holds 601 and 500, over', () => {
        const view = openOnDescriptions(LEFT_300, RIGHT_300);
        expect(view.textarea.value, 'precondition: the prefill is both descriptions, one per line').toBe(`${LEFT_300}\n${RIGHT_300}`);
        expect(codePoints(view.textarea.value)).toBe(601);

        expectCounter(view, 601, 'over');
    });

    it('past 500 the textarea is invalid and a message names the limit, data-max="500"', () => {
        const view = openOnDescriptions(LEFT_300, RIGHT_300);

        expect.soft(view.textarea, 'the textarea is invalid').toHaveAttribute('aria-invalid', 'true');
        expect(single(view.dialog, 'promote-merge-desc-too-long')).toHaveAttribute('data-max', '500');
    });

    it('past 500 Confirm is disabled, and clicking it answers nothing', () => {
        const view = openOnDescriptions(LEFT_300, RIGHT_300);

        view.confirm.click();

        expect.soft(view.confirm, 'Confirm is disabled past the limit').toBeDisabled();
        expect(onConfirm, 'nothing is answered past the limit (today: the 601 characters)').not.toHaveBeenCalled();
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('edited back to 500, the dialog is within the limit again, and Confirm answers the edited text', async () => {
        const view = openOnDescriptions(LEFT_300, RIGHT_300);
        expect(view.confirm, 'precondition: past the limit, Confirm is disabled').toBeDisabled();
        const edited = `${LEFT_300}\n${'R'.repeat(199)}`;
        expect(edited).toHaveLength(500);

        await typeInto(view.textarea, edited);

        expectWithin(view, 500);
        await fireEvent.click(view.confirm);
        expect(onConfirm).toHaveBeenCalledExactlyOnceWith({description: edited});
    });

    it('the limit is inclusive: 501 is over, 500 is within', async () => {
        const view = openOnDescriptions(LEFT_300, RIGHT_300);

        await typeInto(view.textarea, 'E'.repeat(501));
        expectOver(view, 501);

        await typeInto(view.textarea, 'E'.repeat(500));
        expectWithin(view, 500);
    });

    it('counts code points: 300 😀, 600 UTF-16 units, are 300 — within the limit, and confirmed as typed', async () => {
        const view = openOnDescriptions(LEFT_300, RIGHT_300);
        const emoji = '😀'.repeat(300);
        expect(emoji.length, 'control: 600 UTF-16 units').toBe(600);

        await typeInto(view.textarea, emoji);

        expectWithin(view, 300);
        await fireEvent.click(view.confirm);
        expect(onConfirm).toHaveBeenCalledExactlyOnceWith({description: emoji});
    });

    it('follows the dialog’s own choices: one side alone is within the limit, combining them again is past it', async () => {
        const view = openOnDescriptions(LEFT_300, RIGHT_300);

        await fireEvent.click(single(view.block, 'promote-merge-desc-left'));
        expect(view.textarea.value, 'the left description alone').toBe(LEFT_300);
        expectWithin(view, 300);

        await fireEvent.click(single(view.dialog, 'promote-merge-all-merge'));
        expect(view.textarea.value, 'both again, one per line').toBe(`${LEFT_300}\n${RIGHT_300}`);
        expectOver(view, 601);
    });

    it('within the limit from the start: the pair of this file, 22 characters combined, reads ok', () => {
        const view = viewOf({});
        expect(view.textarea.value, 'precondition: the two descriptions, one per line').toBe('Savings out\nSavings in');

        expectWithin(view, 22);
    });

    it('guard: no counter when the descriptions agree — no description block, and Confirm enabled', () => {
        render(PromoteMergeModal, {...props(), txA: {...TX_A, description: 'Same notes'}, txB: {...TX_B, description: 'Same notes'}});
        const dialog = screen.getByRole('dialog');
        expect(within(dialog).queryByTestId('promote-merge-field-tags'), 'presence: the tags differ, so their block is shown').not.toBeNull();

        expect(within(dialog).queryByTestId('promote-merge-field-description'), 'the descriptions agree: no description block').toBeNull();
        expect(within(dialog).queryByTestId('promote-merge-desc-counter'), 'and no counter').toBeNull();
        expect(within(dialog).queryByTestId('promote-merge-desc-too-long'), 'nor a too-long message').toBeNull();
        expect(single(dialog, 'promote-merge-confirm')).toBeEnabled();
    });
});
