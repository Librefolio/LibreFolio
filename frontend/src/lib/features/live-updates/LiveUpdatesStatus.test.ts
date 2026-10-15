// @vitest-environment jsdom
/**
 * LiveUpdatesStatus — component test (Vitest + jsdom).
 *
 * The pill tells the user that live prices are paused because nobody has touched the page for two minutes (Z1, F26,
 * decision 31). It is a signal, not a command: the next input resumes the updates by itself, so the pill offers
 * nothing to click. It speaks only for `paused-idle`; every other state of the poller renders nothing at all — a
 * hidden tab has nobody to tell, and a running or stopped poller has nothing to say.
 *
 * What it deliberately does NOT assert: translated text. The UI ships in four languages; the test checks that a
 * label and a hint are there and are not raw keys (`liveUpdates.…`), which is what a missing catalogue entry would
 * render.
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {render, screen, setupI18n, waitFor, within} from '$test/component';
import LiveUpdatesStatus from './LiveUpdatesStatus.svelte';

const PILL = 'live-updates-status';

describe('LiveUpdatesStatus', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it.each(['running', 'stopped', 'paused-hidden'] as const)('renders nothing while %s', (state) => {
        const {container} = render(LiveUpdatesStatus, {state});

        expect(screen.queryByTestId(PILL)).toBeNull();
        expect(container.children).toHaveLength(0);
        expect(container.textContent?.trim() ?? '').toBe('');
    });

    it('shows a status pill, with a label and a hint, while paused for inactivity', () => {
        render(LiveUpdatesStatus, {state: 'paused-idle'});

        const pill = screen.getByTestId(PILL);
        expect(pill).toBeVisible();
        expect(pill).toHaveAttribute('data-state', 'paused-idle');
        expect(pill).toHaveAttribute('role', 'status');
        expect(screen.getByRole('status')).toBe(pill);

        const label = pill.textContent?.trim() ?? '';
        expect(label).not.toBe('');
        expect(label).not.toContain('liveUpdates.');

        const hint = pill.getAttribute('title')?.trim() ?? '';
        expect(hint).not.toBe('');
        expect(hint).not.toContain('liveUpdates.');
    });

    it('is a signal, not a command: it holds no button', () => {
        const {container} = render(LiveUpdatesStatus, {state: 'paused-idle'});

        expect(within(screen.getByTestId(PILL)).queryByRole('button')).toBeNull();
        expect(within(container).queryByRole('button')).toBeNull();
    });

    it('follows the poller: appears when it pauses for inactivity, goes when it resumes', async () => {
        const {rerender} = render(LiveUpdatesStatus, {state: 'running'});
        expect(screen.queryByTestId(PILL)).toBeNull();

        await rerender({state: 'paused-idle'});
        expect(screen.getByTestId(PILL)).toHaveAttribute('data-state', 'paused-idle');

        await rerender({state: 'running'});
        // An outro transition may keep the node for a moment: wait for it to leave rather than assume it is instant.
        await waitFor(() => expect(screen.queryByTestId(PILL)).toBeNull());
    });
});
