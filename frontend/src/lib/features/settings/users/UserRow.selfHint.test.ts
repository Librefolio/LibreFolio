// @vitest-environment jsdom
/**
 * UserRow, the administrator's own row (lot B10): it has no action, only a hint with a link to the Profile tab, at the
 * tab's own address (`/settings/profile`, from `settingsPaths.ts`), not the `?tab=` of 1.2.
 *
 * Mocks, as `UserRow.avatar.test.ts`: the identity translator and `formatDateTime`, which are not the subject.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/utils/core/formatDateTime', () => ({formatDateTime: () => '2026-11-08'}));

import UserRow from './UserRow.svelte';
import type {AdminAccount} from './types';

const ACCOUNT: AdminAccount = {id: 7, username: 'me', email: 'me@example.com', is_active: true, is_superuser: true, created_at: '2026-11-08T00:00:00Z', protected: false};

afterEach(() => {
    cleanup();
});

describe('UserRow — the own row links the Profile tab at its address (B10)', () => {
    it('USELF-01: the hint’s link opens /settings/profile', async () => {
        render(UserRow, {account: ACCOUNT, isSelf: true, isOnlyActiveAdmin: false, full: false, onAction: () => undefined});
        await fireEvent.click(screen.getByTestId('users-row-toggle'));

        const hint = screen.getByTestId('users-self-hint');
        expect(within(hint).getByRole('link'), 'the Profile tab, at its own address').toHaveAttribute('href', '/settings/profile');
    });
});
