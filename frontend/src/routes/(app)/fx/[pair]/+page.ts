/**
 * Load function for FX pair detail page.
 * Parses the [pair] slug (e.g., "EUR-USD" or "USD-EUR") into currencies.
 * URL order determines display direction; canonical (alphabetical) order is used for stores/API.
 */
import {redirect} from '@sveltejs/kit';

export const prerender = false;
export const csr = true;

export async function load({params}: { params: { pair: string } }) {
    const slug = params.pair;
    const parts = slug.split('-');
    if (parts.length !== 2 || parts[0].length !== 3 || parts[1].length !== 3) {
        throw redirect(302, '/fx');
    }
    const urlBase = parts[0].toUpperCase();
    const urlQuote = parts[1].toUpperCase();
    // Canonical = always alphabetical (matching backend + store keys)
    const canonicalBase = urlBase < urlQuote ? urlBase : urlQuote;
    const canonicalQuote = urlBase < urlQuote ? urlQuote : urlBase;
    const canonicalSlug = `${canonicalBase}-${canonicalQuote}`;
    const inverted = urlBase > urlQuote; // true when URL order ≠ canonical
    return {
        urlBase, urlQuote,
        canonicalBase, canonicalQuote, canonicalSlug,
        inverted,
    };
}
