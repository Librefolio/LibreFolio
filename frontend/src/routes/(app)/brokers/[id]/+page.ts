/**
 * Load function for broker detail page
 */
import type {PageLoad} from './$types';

export const load: PageLoad = async ({params}) => {
    return {
        brokerId: parseInt(params.id, 10)
    };
};

