/**
 * The single-use links of the accounts: an invitation (`/invite#token=…`), a password reset (`/reset-password#token=…`)
 * and the setup link of the initial administrator (`/setup#token=…`), built by the backend (`token_service.token_path`).
 *
 * The token travels in the fragment, which a browser never sends to the server: it stays out of access logs and proxy
 * logs. A link page takes it out of the address bar as soon as it reads it, keeps it in memory, and asks the server
 * what it is worth. `POST /auth/tokens/inspect` answers whoever holds the token; the details (role and address of an
 * invitation, account of a reset link) come only with a valid one.
 */

import type {z} from 'zod';
import {zodiosApi} from '$lib/api';
import type {schemas} from '$lib/api/generated';

/** The links an administrator issues and shares: an invitation, a password reset. */
export type LinkPurpose = 'invite' | 'password_reset';
/** The links a page inspects: those of an administrator, and the setup link of the initial administrator (F02). */
export type InspectedLinkPurpose = LinkPurpose | 'admin_setup';
export type LinkInspection = z.infer<typeof schemas.TokenInspectResponse>;

/** What a link page shows instead of its form: the wait, why the link cannot be used, or a failed check. */
export type LinkPageStatus = 'checking' | 'expired' | 'consumed' | 'revoked' | 'unknown' | 'missing' | 'closed' | 'error';

/**
 * The token in the fragment of `url`, or `null` when there is none (a blank one counts as none). A `token` in the query
 * is not read: no link carries one.
 *
 * When the fragment carries a `token` parameter, `replace` gets the bare path once: the token then stays out of the
 * history and of a bookmark.
 */
export function takeLinkToken(url: URL, replace: (path: string) => void): string | null {
    const fragment = new URLSearchParams(url.hash.slice(1));
    if (!fragment.has('token')) return null;
    const token = fragment.get('token') ?? '';
    replace(url.pathname);
    return token.trim() ? token : null;
}

/** What the token is worth for `purpose`; a token of another purpose is `unknown`. */
export function inspectLinkToken(token: string, purpose: InspectedLinkPurpose): Promise<LinkInspection> {
    return zodiosApi.inspect_link_token_api_v1_auth_tokens_inspect_post({token, purpose});
}
