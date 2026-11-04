// @vitest-environment jsdom
/**
 * RegisterCard — the language picked while a message is on screen (FB-21, release 1.3 wave 6).
 *
 * On `/invite` (and on the sign-in page) the language selector changed the labels of the form but not the messages it
 * had already written: a validation message or the server's refusal was translated once, when it appeared, and kept
 * that language. The messages are now kept as catalogue keys and translated where they are drawn.
 *
 * The translator is a store the test moves: it answers `<language>:<key>`, so a message that did not follow the
 * language shows the old prefix. No translated text is read.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';

const language = vi.hoisted(() => {
    // hoisted with the mock below; the store comes from the module graph, loaded by the mock factory as well
    const subscribers = new Set<(value: string) => void>();
    let value = 'en';
    return {
        subscribe(run: (v: string) => void) {
            subscribers.add(run);
            run(value);
            return () => subscribers.delete(run);
        },
        set(next: string) {
            value = next;
            subscribers.forEach((run) => run(value));
        },
    };
});
vi.mock('$lib/i18n', async () => {
    const {derived} = await import('svelte/store');
    return {_: derived(language, ($language) => (key: string) => `${$language}:${key}`)};
});
vi.mock('$lib/api', () => ({zodiosApi: {register_api_v1_auth_register_post: vi.fn()}}));

import RegisterCard from './RegisterCard.svelte';
import {zodiosApi} from '$lib/api';

const register = vi.mocked(zodiosApi.register_api_v1_auth_register_post);

afterEach(() => {
    cleanup();
    language.set('en');
    vi.clearAllMocks();
});

describe('RegisterCard — messages follow the language (FB-21)', () => {
    it('RGL-01: a field message already on screen is redrawn in the language picked afterwards', async () => {
        render(RegisterCard);
        const username = screen.getByTestId('register-username');
        await fireEvent.input(username, {target: {value: 'ab'}});
        await fireEvent.blur(username);
        await waitFor(() => expect(screen.getByText('en:auth.validation.usernameMinLength')).toBeTruthy());

        language.set('it');

        await waitFor(() => expect(screen.getByText('it:auth.validation.usernameMinLength')).toBeTruthy());
        expect(screen.queryByText('en:auth.validation.usernameMinLength')).toBeNull();
    });

    it("RGL-02: the server's refusal on screen is redrawn in the language picked afterwards", async () => {
        register.mockRejectedValue(Object.assign(new Error('x'), {isAxiosError: true, response: {status: 409, data: {detail: {error_code: 'USER_LIMIT_REACHED'}}}}));
        render(RegisterCard);
        await fireEvent.input(screen.getByTestId('register-email'), {target: {value: 'a@example.com'}});
        await fireEvent.input(screen.getByTestId('register-username'), {target: {value: 'alice'}});
        await fireEvent.input(screen.getByTestId('register-password'), {target: {value: 'Abcdef1!x'}});
        await fireEvent.input(screen.getByTestId('register-confirm-password'), {target: {value: 'Abcdef1!x'}});
        await fireEvent.submit(screen.getByTestId('register-form'));
        await waitFor(() => expect(screen.getByText('en:auth.userLimitReached')).toBeTruthy());

        language.set('fr');

        await waitFor(() => expect(screen.getByText('fr:auth.userLimitReached')).toBeTruthy());
        expect(screen.queryByText('en:auth.userLimitReached')).toBeNull();
    });
});
