// @vitest-environment jsdom
/**
 * UserLimitPage — which page the `(app)` layout shows while the accounts are over the plan (A5-7): the choice for an
 * administrator (`$auth.user.is_superuser === true`), the wait for anyone else, a user not yet read included. Both
 * pages are stubs here: what they do is their own specs.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, render, screen} from '$test/component';

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    return {auth: writable<{user: {is_superuser?: boolean} | null}>({user: null})};
});

vi.mock('$lib/stores/app/auth', () => ({auth: mocks.auth}));
vi.mock('./UserLimitChoicePage.svelte', async () => ({default: (await import('$test/harness/UserLimitChoicePageStub.svelte')).default}));
vi.mock('./UserLimitWaitingPage.svelte', async () => ({default: (await import('$test/harness/UserLimitWaitingPageStub.svelte')).default}));

import UserLimitPage from './UserLimitPage.svelte';

afterEach(cleanup);

describe('UserLimitPage', () => {
    it.each([
        ['an administrator', {is_superuser: true}, 'stub-user-limit-choice'],
        ['an ordinary user', {is_superuser: false}, 'stub-user-limit-waiting'],
        ['a user not read yet', null, 'stub-user-limit-waiting'],
    ])('shows the right page for %s', (_who, user, testId) => {
        mocks.auth.set({user});

        render(UserLimitPage, {props: {onlogout: vi.fn()}});

        expect(screen.getByTestId(testId)).toBeInTheDocument();
    });
});
