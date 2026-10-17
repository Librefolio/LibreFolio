/**
 * Designer Lab — the route stub (`src/routes/designer-lab/+page.ts`).
 *
 * The route exists in every build, so a release build answers `/designer-lab` with this stub: a 404 before any of the
 * Lab's code is reached. `__LF_DESIGNER_LAB__` is a Vite `define` (vite.config.ts), absent under Vitest: each case
 * stubs it on the global object, where the compiled `load` reads it at call time.
 */

import {afterEach, describe, expect, it, vi} from 'vitest';
import {isHttpError} from '@sveltejs/kit';
import {load} from './+page';

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('designer-lab route stub', () => {
    it('answers 404 in a build without the Lab', () => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', false);
        let thrown: unknown = null;
        try {
            load();
        } catch (error) {
            thrown = error;
        }
        expect(isHttpError(thrown, 404), `load() threw ${String(thrown)}`).toBe(true);
    });

    it('lets the page load in a build with the Lab', () => {
        vi.stubGlobal('__LF_DESIGNER_LAB__', true);
        expect(load()).toBeUndefined();
    });
});
