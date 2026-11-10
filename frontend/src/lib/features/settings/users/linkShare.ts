/**
 * The links the Users tab shares (invitations, password resets): the base an administrator shares them at, and the
 * link built on it. The backend builds `url` with `LIBREFOLIO_PUBLIC_URL` when the variable is set (decision D-A3).
 */

function withoutTrailingSlashes(value: string): string {
    return value.replace(/\/+$/, '');
}

/** The base the address field starts from: the public URL the backend used for `url`, otherwise the browser's origin. */
export function initialBase(url: string | null, path: string, origin: string): string {
    if (url && path && url.length > path.length && url.endsWith(path)) {
        return withoutTrailingSlashes(url.slice(0, url.length - path.length));
    }
    return withoutTrailingSlashes(origin);
}

/** The link to share: the base, without its trailing slashes, then the path (which carries the token in its fragment). */
export function composeLink(base: string, path: string): string {
    return `${withoutTrailingSlashes(base)}${path}`;
}
