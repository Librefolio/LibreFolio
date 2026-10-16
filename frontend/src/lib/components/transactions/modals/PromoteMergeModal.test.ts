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

vi.mock('$lib/i18n', () => {
    const shown = (key: string, options?: {values?: Record<string, unknown>}) => {
        const values = options?.values;
        if (!values) return key;
        const listed = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return `${key}(${listed.join(', ')})`;
    };
    const translator = readable(shown);
    return {_: translator, t: translator, locale: writable('en')};
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
