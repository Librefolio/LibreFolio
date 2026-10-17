// @vitest-environment jsdom
/**
 * «Send by email» registered in A's share dialogs (workstream E, lot E4b): `LINK_SHARE_ACTIONS`
 * (`features/settings/users/linkShareActions.ts`, workstream A's registry) carries E's action, and the dialogs offer it
 * only while emails with a link can go out.
 *
 * The contract under test:
 *   - the registry holds exactly one entry with the id `send-by-email`; its component is `SendLinkByEmail` (the default
 *     export of `features/email/SendLinkByEmail.svelte`), no other entry draws that component, and the entry has a
 *     `visible` predicate (an entry without one is always drawn);
 *   - `visibleLinkShareActions(purpose, context)` includes it once when `GET /system/instance` said
 *     `email.links === true`, and leaves it out with no email part, `links` false or `links` absent — for an
 *     invitation with or without an address and for a reset link alike;
 *   - the predicate reads the configuration when it is asked, never a value frozen at import: the action comes and goes
 *     as the configuration changes.
 * Only E's entry is asserted, never the registry's length: the registry is A's, and other entries may join it.
 *
 * Mocks: the instance configuration is a fake whose `config` the test sets, as `sendLinkApi.test.ts` does, and `notify`
 * a spy. `$lib/i18n` is the real module with `_` replaced by an identity translator — partial, because the component's
 * language picker and the select family it imports read `DEFAULT_LOCALE`, `SUPPORTED_LOCALES`, `LANGUAGE_OPTIONS` and
 * `LOCALE_NAMES` from it (the language store is built at import). Importing it still loads no catalogue: the module
 * only registers lazy loaders and never calls `initI18n()`, and the language store sets no locale while `browser` is
 * false, as under Vitest. Nothing is mounted: the jsdom environment is for the component's module only, compiled for
 * the browser as every component test compiles it.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const fake = vi.hoisted(() => ({config: {} as Record<string, unknown>}));

vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    instanceConfig: {
        get config() {
            return fake.config;
        },
    },
}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: readable((key: string) => key)};
});
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));

import SendLinkByEmail from '$lib/features/email/SendLinkByEmail.svelte';
import type {LinkPurpose} from '$lib/features/auth/linkToken';
import {LINK_SHARE_ACTIONS, visibleLinkShareActions, type LinkShareContext} from '$lib/features/settings/users/linkShareActions';

const ID = 'send-by-email';
const BASE_CONFIG = {profile: 'selfhosted', accounts: {registration_mode: 'invite', registration_locked: false}};

/** The links the dialogs share: an invitation with an address written in it, one without, and a reset link. */
const SHARES: Array<{share: string; purpose: LinkPurpose; context: LinkShareContext}> = [
    {share: 'an invitation with an address', purpose: 'invite', context: {email: 'zq-guest@example.com'}},
    {share: 'an invitation without one', purpose: 'invite', context: {email: null}},
    {share: 'a reset link', purpose: 'password_reset', context: {username: 'zq_alice', email: 'zq-alice@example.com', userId: 7}},
];

/** What `GET /system/instance` may say of email, and whether «send by email» is then offered. */
const EMAIL_PARTS: Array<{label: string; email: unknown; shown: boolean}> = [
    {label: 'no email part (an older server)', email: undefined, shown: false},
    {label: 'email available, links false', email: {available: true, links: false}, shown: false},
    {label: 'email unavailable, links absent', email: {available: false}, shown: false},
    {label: 'links true', email: {available: true, links: true}, shown: true},
];

function configure(email: unknown): void {
    fake.config = email === undefined ? {...BASE_CONFIG} : {...BASE_CONFIG, email};
}

/** E's entries among the actions the dialog would draw: none, or exactly once. */
function ours(purpose: LinkPurpose, context: LinkShareContext) {
    return visibleLinkShareActions(purpose, context).filter((action) => action.id === ID);
}

beforeEach(() => {
    configure(undefined);
});

describe('LINK_SHARE_ACTIONS — E’s entry', () => {
    it('LSR-01: exactly one entry is send-by-email; its component is SendLinkByEmail, which no other entry draws; it has a visible predicate', () => {
        const entries = LINK_SHARE_ACTIONS.filter((action) => action.id === ID);

        expect(entries).toHaveLength(1);
        expect(entries[0].component).toBe(SendLinkByEmail);
        expect(typeof entries[0].visible, 'without a predicate the action would be drawn even with email off').toBe('function');
        expect(LINK_SHARE_ACTIONS.filter((action) => action.component === SendLinkByEmail).map((action) => action.id)).toEqual([ID]);
    });
});

describe('visibleLinkShareActions — «send by email» only while emails with a link can go out', () => {
    describe.each(SHARES)('$share', ({purpose, context}) => {
        it.each(EMAIL_PARTS)('LSR-02: $label → shown: $shown', ({email, shown}) => {
            configure(email);

            const drawn = ours(purpose, context);

            expect(drawn.map((action) => action.id)).toEqual(shown ? [ID] : []);
            if (shown) expect(drawn[0].component).toBe(SendLinkByEmail);
        });
    });

    it('LSR-03: the predicate reads the configuration when asked — offered, withdrawn, offered again as it changes', () => {
        const {purpose, context} = SHARES[0];

        configure({available: true, links: true});
        const first = ours(purpose, context).length;
        configure({available: true, links: false});
        const second = ours(purpose, context).length;
        configure({available: true, links: true});
        const third = ours(purpose, context).length;

        expect([first, second, third]).toEqual([1, 0, 1]);
    });
});
