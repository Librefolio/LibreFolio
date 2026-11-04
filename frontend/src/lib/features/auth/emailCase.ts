/**
 * Email addresses compared the way the server compares them (decision P18): an address is the same one whatever the
 * capitals of its A–Z letters, and of nothing else. The server's unique index is on SQLite's `lower(email)`, which folds
 * A–Z only, so `Émile@…` and `émile@…` stay two addresses (a documented limit); `user_service.email_fold` is the same
 * rule in the backend. Nothing is trimmed: spaces are part of what was typed.
 */

/** `address` with A–Z folded to a–z and every other character as written. */
export function emailFold(address: string): string {
    return address.replace(/[A-Z]/g, (letter) => letter.toLowerCase());
}

/** Whether two addresses are the same one for the server: equal once their A–Z letters are folded. */
export function sameEmail(first: string, second: string): boolean {
    return emailFold(first) === emailFold(second);
}
