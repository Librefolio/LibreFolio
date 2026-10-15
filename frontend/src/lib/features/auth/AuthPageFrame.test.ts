// @vitest-environment jsdom
/**
 * AuthPageFrame — the frame of the pages a visitor reaches signed out (accounts lot A5b): the login page and the two
 * link pages, `/invite` and `/reset-password`.
 *
 * Extracted from `routes/+page.svelte` so the three pages share one DOM: the bar at the top right (the coffee link,
 * ThemeToggle, LanguageSelector, HelpMenu) and the centred container the page's card goes in. The contract (plan
 * A5b.1): props `{testId?, children}`, the container carrying `data-testid={testId}` — `login-page`, `invite-page`,
 * `reset-password-page`, the handles every E2E login and both link specs wait on.
 *
 * A smoke test, on purpose: the frame is markup, and what it looks like is `e2e/layout/theme-roles.spec.ts`'s. The three
 * controls of the bar are replaced by no-op components — each reaches for stores, `localStorage` or the document, and
 * none of them is the subject — so what is left to assert is the container, its test id, and the page's content inside
 * it.
 *
 * Written red-first, before `AuthPageFrame.svelte` exists: the file fails on the import until it does.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet} from 'svelte';
import {cleanup, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const identity = readable((key: string) => key);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});
vi.mock('$lib/components/ui/ThemeToggle.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/LanguageSelector.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/HelpMenu.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/ui/AnimatedBackground.svelte', () => ({default: () => {}}));

import AuthPageFrame from './AuthPageFrame.svelte';

/** The page's card, as a stand-in the test owns. */
const card = createRawSnippet(() => ({render: () => `<div data-testid="probe-page-card">a card</div>`}));

afterEach(cleanup);

describe('AuthPageFrame — the container the page gives a test id, with the card inside', () => {
    it('carries the test id it is given, with the page content inside', () => {
        render(AuthPageFrame, {props: {testId: 'probe-page', children: card}});

        expect(within(screen.getByTestId('probe-page')).getByTestId('probe-page-card')).toBeInTheDocument();
    });

    it('still draws the page content without a test id', () => {
        render(AuthPageFrame, {props: {children: card}});

        expect(screen.getByTestId('probe-page-card')).toBeInTheDocument();
    });
});
