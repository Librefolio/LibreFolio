/**
 * dateOutOfRange catalogue — the text of `transactions.errors.dateOutOfRange` is ceiling-only (D-P4, lot L3).
 *
 * The backend refuses a transaction date only when it is past the server's tomorrow, with `params: {max}` and no
 * `min`: the floor of 1900-01-01 is gone (the frontend asks one confirmation before a date before 1900 instead). So
 * the text uses `{max}` and never `{min}` — an unfilled `{min}` would reach the user as a broken sentence.
 *
 * Reads the four catalogue SOURCES (`src/lib/i18n/transactions/<lang>.json`, tracked; the merged `src/lib/i18n/<lang>.json`
 * is generated and ignored by git) and checks the placeholders only, never the sentence.
 */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {describe, expect, it} from 'vitest';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;

/** The value at a dotted key of a parsed catalogue, or undefined. */
function messageAt(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The placeholders a message names, `{name}` or `{name, …}`, each once. */
function placeholdersOf(message: string): string[] {
    return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
}

/** A source, as the tests run from `frontend/` (the Vitest root). */
function source(lang: string): unknown {
    return JSON.parse(readFileSync(resolve(process.cwd(), 'src/lib/i18n/transactions', `${lang}.json`), 'utf-8'));
}

describe('transactions.errors.dateOutOfRange — ceiling-only in the four sources (D-P4 lot L3)', () => {
    for (const lang of LANGUAGES) {
        it(`${lang}: the text names {max} and no {min}`, () => {
            const message = messageAt(source(lang), 'transactions.errors.dateOutOfRange');

            expect(typeof message, `${lang}: transactions.errors.dateOutOfRange is a message of the source`).toBe('string');
            expect(message as string, `${lang}: the ceiling the backend sends`).toContain('{max}');
            expect(message as string, `${lang}: the floor is gone, so no {min}`).not.toContain('{min}');
            expect(placeholdersOf(message as string), `${lang}: {max} and nothing else`).toEqual(['max']);
        });
    }
});
