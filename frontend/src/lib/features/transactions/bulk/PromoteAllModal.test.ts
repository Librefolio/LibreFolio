// @vitest-environment jsdom
/**
 * PromoteAllModal — component test (Vitest + jsdom).
 *
 * «Merge all» of the bulk editor's banner: one answer for every suggested pair whose two rows carry a
 * different description or different tags — keep the left row's (the one the banner lists first),
 * the right row's, or combine both. Combining is what the single merge (PromoteMergeModal) proposes,
 * so it is the default, and every opening starts from it again: an answer given to one batch of
 * pairs must not be silently reused for the next.
 *
 * Props in, a choice and two callbacks out: `onConfirm(strategy)`, `onCancel()`. What the editor
 * does with the strategy — every banner pair merged and saved as Cash Transfers — is
 * e2e/transactions/tx-import-scalable-transfers.spec.ts (S4).
 *
 * On text. `$lib/i18n` is replaced by a translator that renders a key with its values
 * (`key(name=value)`), so the count the dialog announces is checked by the value passed in, never by a
 * translation; the choices are found by test id.
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

import PromoteAllModal, {type PromoteAllStrategy} from './PromoteAllModal.svelte';

type Props = ComponentProps<typeof PromoteAllModal>;

const STRATEGIES: readonly PromoteAllStrategy[] = ['left', 'merge', 'right'];

const onConfirm = vi.fn<(strategy: PromoteAllStrategy) => void>();
const onCancel = vi.fn<() => void>();

function props(overrides: Partial<Props> = {}): Props {
    return {open: true, count: 2, onConfirm, onCancel, ...overrides};
}

/** The radio of one answer. */
function radioOf(strategy: PromoteAllStrategy): HTMLInputElement {
    return within(screen.getByTestId(`promote-all-choice-${strategy}`)).getByRole('radio') as HTMLInputElement;
}

/** The answer whose radio is checked, read from the DOM: exactly one must be. */
function checkedStrategies(): PromoteAllStrategy[] {
    return STRATEGIES.filter((strategy) => radioOf(strategy).checked);
}

beforeEach(() => {
    onConfirm.mockReset();
    onCancel.mockReset();
});

describe('PromoteAllModal — the answer for every pair', () => {
    it('offers the three answers in one radiogroup, combining both chosen by default', () => {
        render(PromoteAllModal, props());
        const group = screen.getByTestId('promote-all-choices');
        expect(group).toHaveAttribute('role', 'radiogroup');
        expect(within(group).getAllByRole('radio'), 'left, merge, right').toHaveLength(3);
        expect(checkedStrategies()).toEqual(['merge']);
    });

    it('confirms the default, combining both, when nothing else is picked', async () => {
        render(PromoteAllModal, props());
        await fireEvent.click(screen.getByTestId('promote-all-confirm'));
        expect(onConfirm).toHaveBeenCalledExactlyOnceWith('merge');
        expect(onCancel).not.toHaveBeenCalled();
    });

    it.each([['left'], ['right']] as const)('confirms %s once it is picked', async (strategy) => {
        render(PromoteAllModal, props());

        await fireEvent.click(radioOf(strategy));

        expect(checkedStrategies(), 'one answer at a time').toEqual([strategy]);
        await fireEvent.click(screen.getByTestId('promote-all-confirm'));
        expect(onConfirm).toHaveBeenCalledExactlyOnceWith(strategy);
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('confirms the last answer picked', async () => {
        render(PromoteAllModal, props());
        await fireEvent.click(radioOf('left'));
        await fireEvent.click(radioOf('right'));
        await fireEvent.click(radioOf('merge'));
        await fireEvent.click(radioOf('left'));
        await fireEvent.click(screen.getByTestId('promote-all-confirm'));
        expect(onConfirm).toHaveBeenCalledExactlyOnceWith('left');
    });

    it('announces how many pairs it merges', () => {
        render(PromoteAllModal, props({count: 3}));
        expect(screen.getByTestId('promote-all-confirm')).toHaveTextContent('n=3');
    });
});

describe('PromoteAllModal — every opening starts from combining both', () => {
    it('a reopened dialog has forgotten the previous answer', async () => {
        const {rerender} = render(PromoteAllModal, props());
        await fireEvent.click(radioOf('right'));
        expect(checkedStrategies(), 'precondition: right is picked').toEqual(['right']);

        await rerender(props({open: false}));
        expect(screen.queryByTestId('promote-all-modal'), 'closed').not.toBeInTheDocument();
        await rerender(props({open: true}));

        expect(checkedStrategies()).toEqual(['merge']);
        await fireEvent.click(screen.getByTestId('promote-all-confirm'));
        expect(onConfirm).toHaveBeenCalledExactlyOnceWith('merge');
    });
});

describe('PromoteAllModal — cancelling', () => {
    it('Cancel answers with onCancel and merges nothing', async () => {
        render(PromoteAllModal, props());
        await fireEvent.click(radioOf('left'));
        await fireEvent.click(screen.getByTestId('promote-all-cancel'));
        expect(onCancel).toHaveBeenCalledOnce();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('Escape cancels too', async () => {
        render(PromoteAllModal, props());
        await fireEvent.keyDown(screen.getByTestId('promote-all-modal'), {key: 'Escape'});
        expect(onCancel).toHaveBeenCalledOnce();
        expect(onConfirm).not.toHaveBeenCalled();
    });
});
