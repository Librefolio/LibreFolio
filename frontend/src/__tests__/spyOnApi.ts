import {vi} from 'vitest';
import {zodiosApi} from '$lib/api';

/**
 * `vi.spyOn(zodiosApi, alias)` for one alias of the generated API client.
 *
 * The cast is on purpose: the client's type is so large that the compiler's instantiation limit ("Type instantiation is
 * excessively deep") is crossed by a spy on it each time the OpenAPI document gains a few operations, and always in a
 * different test file. Typed through a plain record the spy costs nothing and the test keeps its own types for the values.
 */
export function spyOnApi(alias: string) {
    return vi.spyOn(zodiosApi as unknown as Record<string, (...args: unknown[]) => Promise<unknown>>, alias);
}
