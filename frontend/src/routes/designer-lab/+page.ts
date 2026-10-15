import {error} from '@sveltejs/kit';

/**
 * The Designer Lab exists only in debug builds (`__LF_DESIGNER_LAB__`, vite.config.ts). A release build keeps this
 * stub, which answers 404, and none of the Lab's code.
 */
export function load(): void {
    if (!__LF_DESIGNER_LAB__) error(404, 'Not found');
}
