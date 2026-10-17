/**
 * A message for the login page, handed over by a page that sends the user there: the invitation and the
 * password-reset pages, once their form succeeds.
 *
 * It is read once: the login page takes it when it mounts, and after that it is gone. Kept in memory only, so a reload
 * of the login page shows nothing.
 */

let pending = '';

export function setAuthFlash(message: string): void {
    pending = message;
}

/** The message left for the login page, or `''`; the next call returns `''`. */
export function takeAuthFlash(): string {
    const message = pending;
    pending = '';
    return message;
}
