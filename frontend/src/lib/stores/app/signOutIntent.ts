/**
 * Whether the user asked to sign out (`auth.logout()`), apart from a session that ended on its own (a 401).
 *
 * A sign-out the user asked for returns to a plain login; a session that ended on its own carries the page to come back
 * to (`/?redirect=…`). Set before the auth store flips, so whatever reacts to the flip can tell the two apart; cleared by
 * the next sign-in or authenticated check. Its own module, so that the API client's 401 interceptor can read it without
 * importing the auth store, which imports the client.
 */
let requested = false;

export function setSignOutRequested(value: boolean): void {
    requested = value;
}

export function isSignOutRequested(): boolean {
    return requested;
}
