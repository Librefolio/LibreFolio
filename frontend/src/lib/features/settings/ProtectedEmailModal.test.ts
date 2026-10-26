// @vitest-environment jsdom
/**
 * ProtectedEmailModal — what the paying administrator of a managed instance reads when it tries to change its own email
 * address from the profile (lot A5-1b, developer decision of 23/10/2026).
 *
 * The server refuses with 409 `ACCOUNT_PROTECTED`; the profile does not draw a bare error but opens this modal: the address
 * is the subscription owner's, so it cannot be changed here, and the host does it. The modal offers one link to the host:
 * the billing page (`LIBREFOLIO_BILLING_URL`, read from `GET /system/block`, administrators only), else the support address
 * (`LIBREFOLIO_SUPPORT_URL`, from the public configuration), else no link at all.
 *
 * The contract under test:
 *   - closed: nothing is drawn, and nothing is asked of the server; opened: `protected-email-modal`, saying
 *     `settings.protectedEmail.message` under `settings.protectedEmail.title`, and `protected-email-close` calls `onClose`;
 *   - the link `protected-email-link`: `data-kind="billing"` to the billing address when the block answer has an http(s)
 *     one, labelled by `settings.usersTab.billing`; else `data-kind="support"` to the support address (http(s) or mailto:),
 *     labelled by `settings.protectedEmail.support`; else no link. It opens in a new tab (`target=_blank`, `rel` noopener);
 *   - a billing address that is not http(s) is no link; a block answer that fails leaves the support address; and nothing
 *     here ever throws at the profile;
 *   - the four keys are sentences in the four catalogues.
 *
 * Mocks: the identity translator, the public configuration (a getter over a box the test sets). The block answer is
 * injected through the `fetchBlock` prop, as in `InstanceBlockedPage`.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));

const box = vi.hoisted(() => ({supportUrl: null as string | null}));
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    instanceConfig: {
        get config() {
            return {profile: 'managed', accounts: {registration_mode: 'invite', registration_locked: false}, support_url: box.supportUrl};
        },
    },
}));

import ProtectedEmailModal from './ProtectedEmailModal.svelte';

type Block = {blocked: boolean; billing_url?: string | null};
const fetchBlock = vi.fn<() => Promise<Block>>();
const onClose = vi.fn();

function mount(open = true) {
    return render(ProtectedEmailModal, {props: {open, onClose, fetchBlock}});
}

beforeEach(() => {
    box.supportUrl = null;
    fetchBlock.mockReset().mockResolvedValue({blocked: false, billing_url: null});
    onClose.mockReset();
});

afterEach(cleanup);

describe('ProtectedEmailModal — what is said (PEM-01…02)', () => {
    it('PEM-01: closed, nothing is drawn and nothing is asked', async () => {
        mount(false);

        expect(screen.queryByTestId('protected-email-modal')).toBeNull();
        expect(fetchBlock).not.toHaveBeenCalled();
    });

    it('PEM-02: opened, it says the title and the message, and its close button closes', async () => {
        mount();

        const modal = await screen.findByTestId('protected-email-modal');
        expect(modal).toHaveTextContent('settings.protectedEmail.title');
        expect(modal).toHaveTextContent('settings.protectedEmail.message');
        await fireEvent.click(screen.getByTestId('protected-email-close'));
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});

describe('ProtectedEmailModal — the one link to the host (PEM-03…08)', () => {
    it('PEM-03: the billing address first, labelled as the subscription link, in a new tab', async () => {
        fetchBlock.mockResolvedValue({blocked: false, billing_url: 'https://billing.example.test/sub'});
        box.supportUrl = 'https://support.example.test/help';
        mount();

        const link = await screen.findByTestId('protected-email-link');
        expect(link).toHaveAttribute('data-kind', 'billing');
        expect(link).toHaveAttribute('href', 'https://billing.example.test/sub');
        expect(link).toHaveAttribute('target', '_blank');
        expect(link.getAttribute('rel') ?? '').toContain('noopener');
        expect(link).toHaveTextContent('settings.usersTab.billing');
    });

    it.each(['https://support.example.test/help', 'mailto:help@example.test'])('PEM-04: no billing address → the support address (%s), labelled as support', async (support) => {
        box.supportUrl = support;
        mount();

        const link = await screen.findByTestId('protected-email-link');
        expect(link).toHaveAttribute('data-kind', 'support');
        expect(link).toHaveAttribute('href', support);
        expect(link).toHaveTextContent('settings.protectedEmail.support');
    });

    it('PEM-05: neither address → no link at all, and the message still stands', async () => {
        mount();

        await waitFor(() => expect(fetchBlock).toHaveBeenCalled());
        await screen.findByTestId('protected-email-modal');
        expect(screen.queryByTestId('protected-email-link')).toBeNull();
    });

    it('PEM-06: a billing address that is not http(s) is no link — the support address stands in', async () => {
        fetchBlock.mockResolvedValue({blocked: false, billing_url: 'javascript:alert(1)'});
        box.supportUrl = 'https://support.example.test/help';
        mount();

        const link = await screen.findByTestId('protected-email-link');
        expect(link).toHaveAttribute('data-kind', 'support');
    });

    it('PEM-07: a support address that is neither http(s) nor mailto: is no link', async () => {
        box.supportUrl = 'javascript:alert(1)';
        mount();

        await waitFor(() => expect(fetchBlock).toHaveBeenCalled());
        await screen.findByTestId('protected-email-modal');
        expect(screen.queryByTestId('protected-email-link')).toBeNull();
    });

    it('PEM-08: the block answer fails → the support address, and nothing escapes', async () => {
        fetchBlock.mockRejectedValue(new Error('network'));
        box.supportUrl = 'https://support.example.test/help';
        mount();

        const link = await screen.findByTestId('protected-email-link');
        expect(link).toHaveAttribute('data-kind', 'support');
    });
});

describe('ProtectedEmailModal — its words (PEM-09)', () => {
    it.each(['settings.protectedEmail.title', 'settings.protectedEmail.message', 'settings.protectedEmail.support'])('PEM-09: %s is a sentence in the four catalogues', (key) => {
        for (const [language, catalogue] of Object.entries({en, it: itCatalogue, fr, es})) {
            const message = key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
            expect(typeof message === 'string' && message.trim() !== '', `${language}: ${key}`).toBe(true);
            expect(String(message), `${language}: ${key} names no value`).not.toMatch(/\{/);
        }
    });
});
