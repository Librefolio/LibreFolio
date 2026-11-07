/**
 * A sentence with one amount in it, drawn with the amount as a badge (P6).
 *
 * The word order differs by language, so the amount is a placeholder *inside* the translated message and never glued to it:
 * the message is formatted with a marker where the amount goes and cut there. The marker is a private-use character no
 * translation, name or amount can hold.
 */
export const AMOUNT_MARKER = '';

export interface AmountSentence {
    before: string;
    after: string;
}

/** Cuts a message formatted with {@link AMOUNT_MARKER} for its `{amount}` at the marker. A message without it ends with the amount. */
export function splitAtAmount(message: string): AmountSentence {
    const at = message.indexOf(AMOUNT_MARKER);
    if (at === -1) return {before: `${message} `, after: ''};
    return {before: message.slice(0, at), after: message.slice(at + AMOUNT_MARKER.length)};
}
