/**
 * `spyOnApi` — `vi.spyOn` on one alias of the generated client, through a one-key view of it.
 *
 * Spying through the whole type of `zodiosApi` makes TypeScript instantiate every endpoint of the client, and the first
 * statement of the whole program to do it overflows the instantiation depth once the client has grown by one endpoint
 * (the trade-amount route of #47 did): the error then lands on whichever test file is checked first, and moves to the next
 * when that one is fixed. This view names the alias and nothing else, so the type of the client is never expanded.
 * What it gives up: the alias is checked as a string, not against the client — the call under test is typed by its own
 * module, and a mistyped alias fails the test at once (nothing is spied, the real client answers).
 */
import {vi} from 'vitest';

export function spyOnApi(client: unknown, alias: string) {
    return vi.spyOn(client as Record<string, (...args: unknown[]) => unknown>, alias);
}
