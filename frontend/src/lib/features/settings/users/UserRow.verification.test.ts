// @vitest-environment jsdom
/**
 * UserRow and email verification (lot E5b, developer decision 44): «Reactivate» for an inactive account on a full
 * instance.
 *
 * The contract under test: an account waiting for its email verification with a live link (`holds_place: true`, from
 * `GET /users`) already holds its place, so «Reactivate» stays usable on a full instance — no `limit` reason —, and a
 * click asks for it; an inactive account without it (`holds_place` false or absent: an older server) is turned off on a
 * full instance with the `limit` reason, as before; with a free place «Reactivate» is usable either way. A control
 * turned off is asserted disabled with its reason and never clicked: jsdom dispatches a click to a disabled button,
 * and Svelte's delegated handler runs, where a browser sends nothing.
 *
 * Mocks: the identity translator (a message renders as its key) and `formatDateTime` (the row's date is not the
 * subject). What runs for real: the row. Red until E5b is applied (`AdminAccount.holds_place`).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/utils/core/formatDateTime', () => ({formatDateTime: () => '2026-10-16'}));

import UserRow from './UserRow.svelte';
import type {AdminAccount} from './types';

function waiting(holdsPlace: boolean | undefined): AdminAccount {
    const account: AdminAccount = {id: 7, username: 'zq_vera', email: 'zq_vera@example.com', is_active: false, is_superuser: false, created_at: '2026-10-16T00:00:00Z', protected: false};
    return holdsPlace === undefined ? account : {...account, holds_place: holdsPlace};
}

async function opened(account: AdminAccount, full: boolean): Promise<{onAction: ReturnType<typeof vi.fn>; reactivate: HTMLElement}> {
    const onAction = vi.fn();
    render(UserRow, {props: {account, isSelf: false, isOnlyActiveAdmin: false, full, onAction}});
    await fireEvent.click(screen.getByTestId('users-row-toggle'));
    return {onAction, reactivate: screen.getByTestId('users-action-reactivate')};
}

afterEach(() => {
    cleanup();
});

describe('UserRow — «Reactivate» on a full instance', () => {
    it('UVR-01: a waiting account whose live link holds its place: usable, no limit reason, and the click asks for it', async () => {
        const account = waiting(true);
        const {onAction, reactivate} = await opened(account, true);

        expect(reactivate).toBeEnabled();
        expect(reactivate).not.toHaveAttribute('data-disabled-reason');
        expect(screen.queryByText('settings.usersTab.reasons.limit')).toBeNull();
        await fireEvent.click(reactivate);
        expect(onAction).toHaveBeenCalledWith('reactivate', account);
    });

    it.each([
        ['holds_place false', false],
        ['holds_place absent (an older server)', undefined],
    ])('UVR-02: an inactive account with %s: turned off with the limit reason', async (_label, holdsPlace) => {
        const {reactivate} = await opened(waiting(holdsPlace), true);

        expect(reactivate).toBeDisabled();
        expect(reactivate).toHaveAttribute('data-disabled-reason', 'limit');
        expect(screen.getByText('settings.usersTab.reasons.limit')).toBeInTheDocument();
    });

    it.each([true, false])('UVR-03: with a free place, «Reactivate» is usable whatever holds_place says (%s)', async (holdsPlace) => {
        const {reactivate} = await opened(waiting(holdsPlace), false);

        expect(reactivate).toBeEnabled();
        expect(reactivate).not.toHaveAttribute('data-disabled-reason');
    });
});
