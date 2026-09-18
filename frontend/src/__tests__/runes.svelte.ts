/**
 * Rune harness for unit tests that exercise a `.svelte.ts` store.
 *
 * Two things are easy to get wrong here, and both produce a green test that
 * proves nothing.
 *
 *   1. `$effect.root` is a rune, so it can only be *written* in a `.svelte`
 *      or `.svelte.js/ts` file. Calling it straight from a `.test.ts` throws
 *      `rune_outside_svelte`. Hence this file, rather than a helper inside the
 *      spec.
 *
 *   2. The spec that imports it **must** carry `// @vitest-environment jsdom`
 *      on its first line. Measured on this repo's config, under the default
 *      `node` environment a `.svelte.ts` is compiled correctly — the transform
 *      really does emit `$.derived(...)` — but at runtime `$state` reacts while
 *      `$derived` returns the stale value and `$effect` **never runs at all**.
 *
 * The second one is the dangerous half, and it is worth being explicit about
 * why: an assertion that something did *not* happen — "the effect did not
 * re-fire", "reopening the accordion did not refetch" — passes vacuously under
 * `node`, because no effect ever fires. The test is green and defends nothing.
 * `assertEffectsRun` below turns that silent pass into a loud failure.
 */
import {flushSync} from 'svelte';

/** Runs `fn` inside an effect root and hands back its value plus the teardown. */
export function effectRoot<T>(fn: () => T): {value: T; stop: () => void} {
    let value!: T;
    const stop = $effect.root(() => {
        value = fn();
    });
    return {value, stop};
}

/**
 * A mutable reactive object a spec can assign to.
 *
 * `$state` is a rune too, so a `.test.ts` cannot declare one: reading
 * `box.field = x` from a spec only propagates if the object was created here.
 */
export function reactiveBox<T extends object>(initial: T): T {
    const box = $state({...initial});
    return box;
}

/**
 * Fails loudly if the current vitest environment cannot run effects.
 *
 * Call it once per spec, before the first assertion that depends on reactivity.
 * Cheap, synchronous, and it converts the "green because nothing ran" failure
 * mode into an explicit message naming the missing docblock.
 */
export function assertEffectsRun(): void {
    let ran = false;
    const stop = $effect.root(() => {
        $effect(() => {
            ran = true;
        });
    });
    // `$effect.root` schedules; flush it the same way the specs do.
    flushSync();
    stop();
    if (!ran) {
        throw new Error('Effects did not run: add `// @vitest-environment jsdom` as the first line of this spec. Under the default `node` environment $effect never fires and every negative assertion passes vacuously.');
    }
}
