/**
 * Load function for broker detail page
 *
 * Dynamic route - runs on client side only
 */
import type {PageLoad} from './$types';

// Dynamic route configuration
export const prerender = false;  // Cannot be prerendered (dynamic [id])
export const csr = true;         // Enable client-side routing

export const load: PageLoad = async ({params}) => {
    return {
        brokerId: parseInt(params.id, 10)
    };
};

