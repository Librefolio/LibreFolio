// @vitest-environment jsdom
/**
 * AuthCard — the card of the two link pages (accounts lot A5b): the brand header of the sign-in cards, then the body the
 * page puts in it.
 *
 * `LoginCard` and `RegisterCard` each draw that header themselves; the two new cards, `LinkStatusCard` and
 * `ResetPasswordCard`, take it from here instead of making a third and a fourth copy. The contract (plan A5b.1): props
 * `{testId, children}`, the container carrying `data-testid={testId}` — the handle the pages and the E2E specs find the
 * card by — with the brand header and the body inside.
 *
 * What is asserted: the test id on the container, the body inside it, and the brand logo inside it (its accessible
 * name is the product's name, not a translated string). What is not: colours and layout, which are classes and belong
 * to `e2e/layout/theme-roles.spec.ts`.
 *
 * `$lib/i18n` keeps its real exports with the translator replaced by the identity, in case the header reads a key.
 *
 * Written red-first, before `AuthCard.svelte` exists: the file fails on the import until it does.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet} from 'svelte';
import {cleanup, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const identity = readable((key: string) => key);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});

import AuthCard from './AuthCard.svelte';

/** A body the test owns, built without a wrapper component so the spec stays one file. */
const body = createRawSnippet(() => ({render: () => `<p data-testid="probe-card-body">the page's content</p>`}));

afterEach(cleanup);

describe('AuthCard — the brand header and the body, under the test id the page gives', () => {
    it('carries the test id it is given, with the body inside', () => {
        render(AuthCard, {props: {testId: 'probe-card', children: body}});

        const card = screen.getByTestId('probe-card');
        expect(within(card).getByTestId('probe-card-body')).toBeInTheDocument();
    });

    it('heads the body with the brand: the LibreFolio logo, inside the same card', () => {
        render(AuthCard, {props: {testId: 'probe-card', children: body}});

        const card = screen.getByTestId('probe-card');
        const logo = within(card).getByRole('img', {name: 'LibreFolio'});
        // The header comes first: the logo precedes the body in document order.
        expect(logo.compareDocumentPosition(within(card).getByTestId('probe-card-body')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('takes whichever test id the page chooses', () => {
        render(AuthCard, {props: {testId: 'reset-password-modal', children: body}});

        expect(screen.getByTestId('reset-password-modal')).toBeInTheDocument();
        expect(screen.queryByTestId('probe-card')).toBeNull();
    });
});
