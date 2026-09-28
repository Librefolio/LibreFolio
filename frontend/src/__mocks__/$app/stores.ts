/**
 * Vitest mock for SvelteKit `$app/stores`, wired by the alias in `vitest.config.ts`. Vite resolves
 * imports while it compiles a component, before any `vi.mock` runs, so without the alias no test
 * can even load a component that imports `$app/stores` (the Sidebar, the route pages, the layouts).
 *
 * It only makes that import resolve. It does NOT simulate navigation or routing: `page` is a fixed
 * root URL with no route id, params, data or form and never changes; `navigating` is always `null`;
 * `updated` never reports a new version, and `check()` resolves `false`. A test that depends on the
 * current route, on `$page` changing or on navigation must `vi.mock('$app/stores', …)` with its own
 * stores, as `src/routes/(app)/layout.gate.test.ts` does.
 */
import {readable} from 'svelte/store';

export const page = readable({url: new URL('http://localhost/'), params: {}, route: {id: null}, status: 200, error: null, data: {}, form: null, state: {}});
export const navigating = readable(null);
export const updated = {subscribe: readable(false).subscribe, check: () => Promise.resolve(false)};
