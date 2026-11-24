import {error} from '@sveltejs/kit';

/**
 * The Button Lab (project 85, BTN-0): the standard button's behaviour to try with a finger on a real phone. It exists
 * only in debug builds, like the Designer Lab (`__LF_DESIGNER_LAB__`, vite.config.ts): a release build keeps this stub,
 * which answers 404, and none of the Lab's code.
 */
export function load(): void {
    if (!__LF_DESIGNER_LAB__) error(404, 'Not found');
}
