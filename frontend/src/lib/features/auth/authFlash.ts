/**
 * A message for the login page, handed over by a page that sends the user there: the invitation and the
 * password-reset pages, once their form succeeds.
 *
 * It is read once: the login page takes it when it mounts, and after that it is gone. Kept in memory only, so a reload
 * of the login page shows nothing.
 *
 * It has a tone, `success` unless the sender says `warning` (an account was created but its activation email was held:
 * lot E-26 (b)). The tone is read with `takeAuthFlashTone()`, once, and set again with every message.
 */

export type AuthFlashTone = 'success' | 'warning';

let pending = '';
let pendingTone: AuthFlashTone = 'success';

export function setAuthFlash(message: string, tone: AuthFlashTone = 'success'): void {
    pending = message;
    pendingTone = tone;
}

/** The message left for the login page, or `''`; the next call returns `''`. */
export function takeAuthFlash(): string {
    const message = pending;
    pending = '';
    return message;
}

/** The tone of the message left for the login page, `success` when none was given; the next call returns `success`. */
export function takeAuthFlashTone(): AuthFlashTone {
    const tone = pendingTone;
    pendingTone = 'success';
    return tone;
}
