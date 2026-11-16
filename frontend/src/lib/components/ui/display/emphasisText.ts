/**
 * The two marks a catalogue text may carry to be read at a glance (lot E4 of project 71, 13/11/2026): a line break
 * (`\n`) after each sentence that stands on its own, and `**…**` around the words that matter. Rendered by
 * `EmphasisText.svelte` as text nodes, never as HTML: a translation cannot inject markup, and a value interpolated into
 * it can at most turn bold. The same marks are read by the emails (`backend/app/services/email/messages.py`).
 */

/** A piece of one line: its text, and whether it is one of the words that matter. */
export interface EmphasisPiece {
    text: string;
    strong: boolean;
}

/** The lines of `text`, each a list of pieces. A `**` without its pair stays as it is written; empty pieces are dropped. */
export function emphasisLines(text: string): EmphasisPiece[][] {
    return text.split('\n').map((line) => {
        const parts = line.split('**');
        // An even number of parts means one `**` has no pair: it is text, joined back to what follows it
        if (parts.length % 2 === 0) parts.splice(parts.length - 2, 2, `${parts[parts.length - 2]}**${parts[parts.length - 1]}`);
        return parts.map((part, index) => ({text: part, strong: index % 2 === 1})).filter((piece) => piece.text !== '');
    });
}
