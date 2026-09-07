/**
 * Collision-proof names for rows a spec creates.
 *
 * ## Why this exists
 *
 * The idiom that spread through the specs was `Date.now().toString().slice(-6)`.
 * It reads as "unique", and it was — while one Playwright process ran at a time.
 * Under concurrent workers, tests start in bursts: four workers can call it
 * inside the same millisecond and produce the *same* six digits.
 *
 * Measured instance: `brokers.name` carries a UNIQUE index, and the duplicate
 * check in `BrokerService.create_bulk` is a SELECT followed by an INSERT, so
 * both requests pass the check and the loser fails at flush time. The spec saw
 * a bare `Internal Server Error` from `POST /brokers` and had no way to explain
 * it. (The backend now answers 409 with the reason — but the name still has to
 * be unique.)
 *
 * ## The rule
 *
 * Any name a spec writes to a shared, uniquely-indexed column goes through
 * this. Time alone is not identity when four processes share a clock.
 */

/**
 * A suffix unique across concurrent workers and across repeated runs.
 *
 * Time gives ordering (useful when reading leftovers in a database), randomness
 * gives uniqueness. Both are needed: randomness alone makes leftovers unsortable,
 * time alone collides.
 */
export function uniqueSuffix(): string {
    return `${Date.now().toString().slice(-6)}${Math.random().toString(36).slice(2, 7)}`;
}

/**
 * A fixed-length uppercase alphanumeric token, for columns that enforce a width.
 *
 * `uniqueSuffix()` is variable-length and cannot be embedded in a field with a
 * hard size — an ISIN is exactly 12 characters, so `IT0` + suffix + `AAA` has
 * exactly six to spend. Six base-36 characters are ~2.2·10⁹ possibilities, which
 * is uniqueness enough; what made the old idiom collide was that it was *time*,
 * not that it was short.
 *
 * Uppercase because the fields that impose a width are usually codes (ISIN,
 * ticker), and mixed case there reads as a bug.
 */
export function uniqueToken(length: number): string {
    let out = '';
    while (out.length < length) out += Math.random().toString(36).slice(2);
    return out.slice(0, length).toUpperCase();
}
