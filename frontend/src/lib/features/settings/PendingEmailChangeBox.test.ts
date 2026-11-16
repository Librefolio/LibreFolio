// @vitest-environment jsdom
/**
 * PendingEmailChangeBox — the information box under the Email row of Profile while a change of address waits for its
 * link (release 1.4, project 71, step 2.7; decision D5.3 P1).
 *
 * The contract under test, a controlled component (it never calls the server: the profile does):
 *   - `profile-email-pending`, with the address written in full in `profile-email-pending-address`, and the expiry in a
 *     `<time>` (`profile-email-pending-expires`) whose `datetime` is the expiry as given and whose text is the local date
 *     and time (`formatDateTime`); the root carries `data-expires-at` too;
 *   - `profile-email-pending-resend` calls `onResend`, `profile-email-pending-cancel` calls `onCancel`, once each;
 *   - while `busy`, both buttons are disabled, a click calls nothing, and the root says `data-busy="true"`;
 *   - every key it reads is a sentence in the four catalogues.
 *
 * Mocks: the identity translator. No assertion reads a translated text.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen} from '$test/component';
import {formatDateTime} from '$lib/utils/core/formatDateTime';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

// The identity translator; the rest of the module as it is (formatDateTime reads the interface locale through it).
vi.mock('$lib/i18n', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/i18n')>()), _: readable((key: string) => key)}));

import PendingEmailChangeBox from './PendingEmailChangeBox.svelte';

const ADDRESS = 'zq.anan.rossi+long-alias@zq-mail.example.org';
const EXPIRES_AT = '2026-11-13T14:30:00Z';
const KEYS = ['title', 'body', 'expires', 'resend', 'cancel', 'sent', 'resent', 'cancelled', 'rateLimited', 'deliveryFailed', 'unavailable'];

function mount(busy = false) {
    const onResend = vi.fn();
    const onCancel = vi.fn();
    render(PendingEmailChangeBox, {props: {email: ADDRESS, expiresAt: EXPIRES_AT, busy, onResend, onCancel}});
    return {onResend, onCancel};
}

afterEach(cleanup);

describe('PendingEmailChangeBox', () => {
    it('PEB-01 shows the waiting address in full and the expiry as a local date and time', () => {
        mount();

        const box = screen.getByTestId('profile-email-pending');
        expect(screen.getByTestId('profile-email-pending-address').textContent?.trim()).toBe(ADDRESS);
        const expires = screen.getByTestId('profile-email-pending-expires');
        expect(expires.tagName).toBe('TIME');
        expect(expires.getAttribute('datetime')).toBe(EXPIRES_AT);
        expect(expires.textContent?.trim()).toBe(formatDateTime(EXPIRES_AT));
        expect(box.getAttribute('data-expires-at')).toBe(EXPIRES_AT);
        expect(box.getAttribute('data-busy')).toBe('false');
    });

    it('PEB-02 «Send again» and «Cancel the request» call their callbacks once each', async () => {
        const {onResend, onCancel} = mount();

        await fireEvent.click(screen.getByTestId('profile-email-pending-resend'));
        await fireEvent.click(screen.getByTestId('profile-email-pending-cancel'));

        expect(onResend).toHaveBeenCalledTimes(1);
        expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('PEB-03 while busy both buttons are disabled and a click calls nothing', async () => {
        const {onResend, onCancel} = mount(true);

        const resend = screen.getByTestId('profile-email-pending-resend') as HTMLButtonElement;
        const cancel = screen.getByTestId('profile-email-pending-cancel') as HTMLButtonElement;
        expect([resend.disabled, cancel.disabled]).toEqual([true, true]);
        expect(screen.getByTestId('profile-email-pending').getAttribute('data-busy')).toBe('true');
        await fireEvent.click(resend);
        await fireEvent.click(cancel);

        expect(onResend).not.toHaveBeenCalled();
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('PEB-04 every key of settings.emailPending is a sentence in the four catalogues', () => {
        for (const catalogue of [en, itCatalogue, fr, es]) {
            const section = (catalogue as {settings: {emailPending?: Record<string, string>}}).settings.emailPending ?? {};
            for (const key of KEYS) {
                expect(typeof section[key] === 'string' && section[key].trim().length > 0, `settings.emailPending.${key}`).toBe(true);
            }
        }
    });
});
