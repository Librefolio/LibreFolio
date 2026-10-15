/**
 * linkShare — the link an administrator copies out of the Invite and Reset dialogs (accounts lot A6b).
 *
 * The backend answers a new invitation or reset link with `path` — `/invite#token=…` or `/reset-password#token=…`,
 * the token in the fragment, which a browser never sends to a server (`token_service.token_path`) — and `url`:
 * `LIBREFOLIO_PUBLIC_URL` followed by `path`, or null when the variable is unset (`registration_service.public_link`).
 * `LinkShare` shows the address the link starts with, prefilled and editable (decision D-A3), and the link built on
 * it. Two pure functions do that arithmetic (plan A6b.1), pinned here:
 *   - `initialBase(url, path, origin)` is the prefill. When `url` ends with `path`, the part of `url` before it — the
 *     public address, path prefix of a reverse proxy included (`https://x.example/librefolio`) —, otherwise `origin`,
 *     the browser's own address (`window.location.origin`, passed in by the caller). Trailing slashes are removed
 *     either way: the backend removes only one from `LIBREFOLIO_PUBLIC_URL`, so `https://x.example/librefolio//`
 *     gives a `url` of `https://x.example/librefolio//invite#token=…`.
 *   - `composeLink(base, path)` is `base` (already normalized: no trailing slash) followed by `path`, character for
 *     character. Not a URL resolution — `new URL('/invite', 'https://x.example/librefolio/')` drops the prefix — and
 *     not a re-encoding: the link page decodes the token once, so a token encoded twice, or decoded early, is
 *     another token.
 *
 * Neither function reads the page: the cases run in Node, where an origin read from `window` instead of the argument
 * fails on its own.
 *
 * Written red-first, before `linkShare.ts` exists: every case fails on the import until it does.
 */
import {describe, expect, it} from 'vitest';

import {composeLink, initialBase} from './linkShare';

/** A token as the backend mints them (`secrets.token_urlsafe(32)`): 43 base64url characters, `-` and `_` included. */
const TOKEN = 'Xq3-Lr_9Zt0Vb8Nc7Md6-Ke5Jf4_Hg3Gs2Fa1De0Cw9';
/** The paths the backend answers with: the page that takes the token, then the token in the fragment. */
const INVITE_PATH = `/invite#token=${TOKEN}`;
const RESET_PATH = `/reset-password#token=${TOKEN}`;
/** The address the browser is on: what the prefill falls back to. */
const ORIGIN = 'http://127.0.0.1:6182';

describe('initialBase — the address the link starts with, before the administrator edits it', () => {
    it.each([
        ['an https origin', 'https://folio.example', INVITE_PATH],
        ['an origin with a port', 'http://folio.example:8080', RESET_PATH],
        ['an IPv6 literal with a port', 'http://[::1]:6182', INVITE_PATH],
    ])('LSH-P-01: url ends with path, on %s: the part of url before path — LIBREFOLIO_PUBLIC_URL, not the browser’s address', (_label, publicUrl, path) => {
        expect(initialBase(`${publicUrl}${path}`, path, ORIGIN), 'the public address the server knows wins over the one the browser is on').toBe(publicUrl);
    });

    it.each([
        ['one segment', 'https://x.example/librefolio', INVITE_PATH],
        ['two segments', 'https://x.example/apps/librefolio', RESET_PATH],
    ])('LSH-P-02: url ends with path, under a path prefix of %s: the prefix belongs to the base', (_label, publicUrl, path) => {
        expect(initialBase(`${publicUrl}${path}`, path, ORIGIN), 'a reverse proxy serves the instance under a prefix: the link must stay under it').toBe(publicUrl);
    });

    it.each([
        ['an invitation', INVITE_PATH],
        ['a reset link', RESET_PATH],
    ])('LSH-P-03: url is null (LIBREFOLIO_PUBLIC_URL unset), for %s: the browser’s origin', (_label, path) => {
        expect(initialBase(null, path, ORIGIN), 'with no public address the prefill is the address the administrator is on').toBe(ORIGIN);
    });

    it.each([
        ['a link carrying another token', `https://folio.example/invite#token=${TOKEN}0`, INVITE_PATH],
        ['the link of the other page', `https://folio.example${RESET_PATH}`, INVITE_PATH],
        ['the public address alone', 'https://folio.example', INVITE_PATH],
        ['a url holding path in its middle, not at its end', `https://folio.example${INVITE_PATH}&next=/`, INVITE_PATH],
        ['an empty url', '', RESET_PATH],
    ])('LSH-P-04: url does not end with path (%s): the browser’s origin, never a piece of url', (_label, url, path) => {
        expect(initialBase(url, path, ORIGIN), `${JSON.stringify(url)} is not this link: no part of it can be the base`).toBe(ORIGIN);
    });

    it.each([
        ['the slash the backend leaves (LIBREFOLIO_PUBLIC_URL ending in //)', 'https://x.example/librefolio/', INVITE_PATH, 'https://x.example/librefolio'],
        ['a bare origin and its slash', 'https://folio.example/', RESET_PATH, 'https://folio.example'],
        ['several slashes', 'https://x.example/librefolio///', INVITE_PATH, 'https://x.example/librefolio'],
    ])('LSH-P-05: the part of url before path loses its trailing slashes: %s', (_label, before, path, expected) => {
        expect(initialBase(`${before}${path}`, path, ORIGIN), 'the base carries no trailing slash, or the composed link would hold //').toBe(expected);
    });

    it.each<[string, string | null, string]>([
        ['url is null', null, 'http://127.0.0.1:6182/'],
        ['url does not end with path', 'https://folio.example/elsewhere', 'http://127.0.0.1:6182///'],
    ])('LSH-P-06: the origin loses its trailing slashes too (%s)', (_label, url, origin) => {
        expect(initialBase(url, INVITE_PATH, origin), 'the fallback is a base like any other: no trailing slash').toBe(ORIGIN);
    });
});

describe('composeLink — the base, then the path, character for character', () => {
    it('LSH-P-07: base + path: the page, then the fragment with its token, as the backend wrote them', () => {
        expect(composeLink('https://folio.example', INVITE_PATH)).toBe(`https://folio.example/invite#token=${TOKEN}`);
    });

    it('LSH-P-08: a path prefix is kept: the link stays under /librefolio', () => {
        expect(composeLink('https://x.example/librefolio', RESET_PATH), 'resolving path against the base as a URL would drop the prefix').toBe(`https://x.example/librefolio/reset-password#token=${TOKEN}`);
    });

    it.each([
        ['http://127.0.0.1:6182', INVITE_PATH],
        ['http://[::1]:6182', RESET_PATH],
    ])('LSH-P-09: the port and the IPv6 literal of %s are kept', (base, path) => {
        expect(composeLink(base, path)).toBe(`${base}${path}`);
    });

    it('LSH-P-10: the path is neither decoded nor re-encoded: %-escapes in the fragment reach the link as they are', () => {
        // urlencode() writes a + or an = of a token as %2B / %3D, and the link page decodes them once (URLSearchParams):
        // encoded again (%252B) or decoded here (a +, which the page reads back as a space) it would read another token.
        const path = '/invite#token=Ab-_c%2Bd%3D%3D';

        expect(composeLink('https://folio.example', path)).toBe('https://folio.example/invite#token=Ab-_c%2Bd%3D%3D');
    });

    it.each<[string, string | null, string, string]>([
        ['under a path prefix', `https://x.example/librefolio${INVITE_PATH}`, INVITE_PATH, `https://x.example/librefolio${INVITE_PATH}`],
        ['on a bare origin', `https://folio.example${RESET_PATH}`, RESET_PATH, `https://folio.example${RESET_PATH}`],
        ['with no public address', null, INVITE_PATH, `${ORIGIN}${INVITE_PATH}`],
    ])('LSH-P-11: the prefilled base composes the backend’s own link, %s', (_label, url, path, expected) => {
        expect(composeLink(initialBase(url, path, ORIGIN), path), 'before any edit the link shown is the link the server issued, character for character').toBe(expected);
    });
});
