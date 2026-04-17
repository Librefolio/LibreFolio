/**
 * Load function for Asset detail page.
 * Parses the [id] param as an integer, redirects to /assets if invalid.
 */
import {redirect} from '@sveltejs/kit';

export const prerender = false;
export const csr = true;

export async function load({params}: {params: {id: string}}) {
    const assetId = parseInt(params.id, 10);
    if (isNaN(assetId) || assetId <= 0) {
        throw redirect(302, '/assets');
    }
    return {assetId};
}
