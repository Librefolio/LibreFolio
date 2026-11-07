/**
 * The example a check of `LIBREFOLIO_PUBLIC_URL` gives (`email.checks.links.missing` and `.invalid`): the address the
 * administrator is using right now, as the value to set. It is a suggestion shown in the text, never saved: the browser
 * address is not trusted by the server, which builds emailed links only from the variable (developer decision 45).
 */

/** What the example is when the browser's own address cannot stand for a public one (an opaque origin, `file:`). */
export const PUBLIC_URL_EXAMPLE_FALLBACK = 'https://librefolio.example.com';

const HTTP_ORIGIN = /^https?:\/\/[^\s/?#@]+$/i;

/** The origin of the page, `https://host` or `http://host:port` without a path, when it can be a value of the variable. */
export function publicUrlExample(origin: string | null | undefined = typeof window === 'undefined' ? null : window.location.origin): string {
    return origin && HTTP_ORIGIN.test(origin) ? origin : PUBLIC_URL_EXAMPLE_FALLBACK;
}

/** The checks whose text names the example: `email.checks.links.missing` and `.invalid` (`.ok` takes no value). */
const EXAMPLE_KEYS = new Set(['email.checks.links.missing', 'email.checks.links.invalid']);

/** The values a check's message is rendered with: its own parameters, plus the `example` for the two PUBLIC_URL texts only. */
export function checkMessageValues(messageKey: string, params: Record<string, string | number> | undefined): Record<string, string | number> | undefined {
    return EXAMPLE_KEYS.has(messageKey) ? {...params, example: publicUrlExample()} : params;
}
