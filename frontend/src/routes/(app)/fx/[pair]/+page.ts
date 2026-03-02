/**
 * Load function for FX pair detail page.
 * Parses the [pair] slug (e.g., "EUR-USD") into base and quote currencies.
 */
import {redirect} from '@sveltejs/kit';
export const prerender = false;
export const csr = true;
export async function load({params}: {params: {pair: string}}) {
    const slug = params.pair;
    const parts = slug.split('-');
    if (parts.length !== 2 || parts[0].length !== 3 || parts[1].length !== 3) {
        throw redirect(302, '/fx');
    }
    const base = parts[0].toUpperCase();
    const quote = parts[1].toUpperCase();
    // Ensure alphabetical order — redirect if not canonical
    if (base > quote) {
        throw redirect(302, `/fx/${quote}-${base}`);
    }
    return {
        base,
        quote,
        slug: `${base}-${quote}`,
    };
}
