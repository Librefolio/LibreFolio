// @vitest-environment jsdom
/**
 * UserLimitWaitingPage — what anyone but an administrator sees while the active accounts outnumber the plan (A5-7).
 *
 * The contract: a page (`user-limit-waiting`) that says an administrator has to choose who keeps the access and to try
 * again later — a clear message, not a generic error; `user-limit-check-again` runs `oncheck` (by default the page reloads,
 * and the app starts again if the choice was made); `user-limit-logout` calls `onlogout`. It reads nothing from the API: the
 * server told this user nothing but the refusal.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '$test/component';

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const identity = readable((key: string) => key);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});
vi.mock('$lib/api', () => ({zodiosApi: new Proxy({}, {get: () => () => Promise.reject(new Error('the waiting page reads nothing'))})}));

import UserLimitWaitingPage from './UserLimitWaitingPage.svelte';

afterEach(cleanup);

describe('UserLimitWaitingPage', () => {
    it('says an administrator has to choose, with a title and a description of its own', () => {
        render(UserLimitWaitingPage, {props: {onlogout: vi.fn(), oncheck: vi.fn()}});

        expect(screen.getByTestId('user-limit-waiting')).toBeInTheDocument();
        expect(screen.getByTestId('user-limit-waiting-title').textContent).toBe('instance.userLimit.waitingTitle');
        expect(screen.getByTestId('user-limit-waiting-description').textContent).toBe('instance.userLimit.waitingDescription');
    });

    it('checks again and signs out on request', async () => {
        const oncheck = vi.fn();
        const onlogout = vi.fn();
        render(UserLimitWaitingPage, {props: {onlogout, oncheck}});

        await fireEvent.click(screen.getByTestId('user-limit-check-again'));
        await fireEvent.click(screen.getByTestId('user-limit-logout'));

        expect(oncheck).toHaveBeenCalledTimes(1);
        expect(onlogout).toHaveBeenCalledTimes(1);
    });
});
