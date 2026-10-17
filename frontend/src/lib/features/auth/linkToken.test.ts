/**
 * linkToken — reading the token of an invitation or password-reset link, and asking the server what it is worth
 * (accounts lot A5b).
 *
 * An administrator sends `/invite#token=…` or `/reset-password#token=…`. The token travels in the URL FRAGMENT, never in
 * the query: a browser does not send the fragment to the server, so the token stays out of uvicorn's access log and of
 * any reverse proxy's. The page that opens reads it once and takes it out of the address bar at once, so it does not
 * stay in the history, in a bookmark or in a screenshot; then it asks `POST /api/v1/auth/tokens/inspect` what the link
 * is worth before showing a form.
 *
 * The contract (plan A5b.1, with the fragment decision of 2026-10-15):
 *   - `takeLinkToken(url, replace)` returns the `token` parameter of the fragment
 *     (`new URLSearchParams(url.hash.slice(1)).get('token')`), `null` when there is none or it is blank;
 *   - whenever the fragment carries a `token` parameter, it calls `replace(url.pathname)` exactly once — the bare path:
 *     no fragment, no query — and when it carries none it calls nothing;
 *   - a `token` in the QUERY is not read: such a link is treated as carrying no token at all (`null`, no call). A link
 *     built that way has already reached the server's logs, and accepting it would keep that shape alive;
 *   - `inspectLinkToken(token, purpose)` posts `{token, purpose}` through the generated client
 *     (`inspect_link_token_api_v1_auth_tokens_inspect_post`) and returns its answer as it is; a failure is the
 *     caller's to handle (the page shows `error` and offers a retry), so it is not swallowed.
 *
 * `$lib/api` is a mock: the generated client is the subject of one call only. The pages that use these two functions
 * are pinned in `src/routes/invite/page.test.ts` and `src/routes/reset-password/page.test.ts`.
 *
 * Written red-first, before `linkToken.ts` exists: every case fails on the import until it does.
 *
 * Accounts lot A7b (F02; plan A7b, C3): a third link, `/setup#token=…`, the setup link of the initial administrator,
 * read with the same `takeLinkToken` and inspected with the purpose `admin_setup` (`InspectedLinkPurpose`: `LinkPurpose`
 * stays the links an administrator shares). Its case below was red at the type checker (`front check`), not under vitest:
 * `inspectLinkToken` forwards whatever purpose it is given, so at runtime the case passes before A7b and after. The
 * runtime red of the purpose is the page's, in `src/routes/setup/page.test.ts`.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
    inspect: vi.fn().mockName('zodiosApi.inspect_link_token_api_v1_auth_tokens_inspect_post'),
}));

vi.mock('$lib/api', () => ({zodiosApi: {inspect_link_token_api_v1_auth_tokens_inspect_post: mocks.inspect}}));

import {inspectLinkToken, takeLinkToken} from './linkToken';

const ORIGIN = 'https://librefolio.example';

/** `takeLinkToken` on `path`, with a `replace` that records what it was asked. */
function take(path: string): {token: string | null; replaced: string[]} {
    const replaced: string[] = [];
    const token = takeLinkToken(new URL(path, ORIGIN), (next: string) => {
        replaced.push(next);
    });
    return {token, replaced};
}

beforeEach(() => {
    mocks.inspect.mockReset();
});

describe('takeLinkToken — the token, read from the fragment once and taken out of the address bar', () => {
    it('returns the token of an invitation link, and replaces the address with its bare path', () => {
        expect(take('/invite#token=Ab3-_xYz09')).toEqual({token: 'Ab3-_xYz09', replaced: ['/invite']});
    });

    it('does the same on the password-reset page', () => {
        expect(take('/reset-password#token=rst-0123')).toEqual({token: 'rst-0123', replaced: ['/reset-password']});
    });

    it('takes the whole fragment and the query away, not only the token', () => {
        // `replace(url.pathname)`: whatever rode along with the token goes with it.
        expect(take('/invite?lang=it#token=inv-1&utm_source=mail')).toEqual({token: 'inv-1', replaced: ['/invite']});
    });

    it('returns null and leaves the address alone when the fragment carries no token', () => {
        expect(take('/invite')).toEqual({token: null, replaced: []});
        expect(take('/invite#')).toEqual({token: null, replaced: []});
        expect(take('/invite#lang=it')).toEqual({token: null, replaced: []});
    });

    it('does not read a token from the query: the server has already logged that one', () => {
        expect(take('/invite?token=leaked-0123')).toEqual({token: null, replaced: []});
        expect(take('/reset-password?token=leaked-0123')).toEqual({token: null, replaced: []});
    });

    it.each([
        ['an empty token', '/invite#token='],
        ['a blank token', '/invite#token=%20%20'],
    ])('reads %s as no token, and still takes the parameter away', (_label, path) => {
        expect(take(path)).toEqual({token: null, replaced: ['/invite']});
    });
});

describe('inspectLinkToken — what the server says the link is worth', () => {
    it.each(['invite', 'password_reset'] as const)('posts {token, purpose: %s} and returns the answer as it is', async (purpose) => {
        const answer = {status: 'valid', purpose, expires_at: '2026-10-20T08:00:00Z'};
        mocks.inspect.mockResolvedValue(answer);

        const result = await inspectLinkToken('tok-42', purpose);

        expect(mocks.inspect).toHaveBeenCalledTimes(1);
        expect(mocks.inspect.mock.calls[0][0], 'the body of POST /auth/tokens/inspect').toStrictEqual({token: 'tok-42', purpose});
        expect(result, 'the answer of the generated client, untouched').toBe(answer);
    });

    // red until A7b — at the type checker only (`front check`): `inspectLinkToken` did not admit 'admin_setup'.
    it("posts {token, purpose: 'admin_setup'} for the setup link of the initial administrator, and returns the answer as it is", async () => {
        const answer = {status: 'valid', purpose: 'admin_setup', expires_at: '2026-10-17T08:00:00Z', username: 'carla.rossi'};
        mocks.inspect.mockResolvedValue(answer);

        const result = await inspectLinkToken('setup-tok-42', 'admin_setup');

        expect(mocks.inspect).toHaveBeenCalledTimes(1);
        expect(mocks.inspect.mock.calls[0][0], 'the body of POST /auth/tokens/inspect').toStrictEqual({token: 'setup-tok-42', purpose: 'admin_setup'});
        expect(result, 'the answer of the generated client, untouched: the account to set up included').toBe(answer);
    });

    it('lets a failed request through to the caller, who shows the error and offers a retry', async () => {
        const failure = new Error('Network Error');
        mocks.inspect.mockRejectedValue(failure);

        await expect(inspectLinkToken('tok-42', 'invite')).rejects.toBe(failure);
    });
});
