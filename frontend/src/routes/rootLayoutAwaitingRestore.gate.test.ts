/**
 * Gate: the root layout wraps every page in `AwaitingRestoreGate` (workstream H, lot H-62).
 *
 * ## What this protects
 *
 * While the hosting panel restores the instance on an empty volume the backend answers 423 to every route but
 * `GET /system/instance`. The customer must see `InstanceAwaitingRestorePage` instead of whatever page they opened:
 * the login (`/`), the anonymous link pages (`/setup`, `/invite`, …) and the `(app)` pages alike. Only the root layout
 * (`src/routes/+layout.svelte`) sits above all of them, so the gate must wrap its `<slot />` there — not in `(app)`,
 * which the login does not go through.
 *
 * ## The rule, as this file checks it
 *
 * Read on the source text, comments removed (an HTML comment or a script comment that names the gate does not count):
 *   - the layout imports the default export of `$lib/features/instance/components/AwaitingRestoreGate.svelte`;
 *   - its one `<slot />` sits between `<AwaitingRestoreGate …>` and `</AwaitingRestoreGate>`;
 *   - the gate opens inside the branch where the first dictionary is ready (the `i18nBooted` block): the page it may show
 *     reads `$_`, which throws before svelte-i18n has a locale.
 *
 * What the gate does is `AwaitingRestoreGate.test.ts`'s. Red until H-62: the layout renders the slot unwrapped.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {describe, expect, it} from 'vitest';
import {readFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const LAYOUT = join(dirname(fileURLToPath(import.meta.url)), '+layout.svelte');

/** The layout without its comments: HTML comments, and `//` / block comments of the script. */
function layoutSource(): string {
    return readFileSync(LAYOUT, 'utf8')
        .replace(/<!--[\s\S]*?-->/g, '')
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/(^|[^:'"`])\/\/.*$/gm, '$1');
}

describe('root layout — AwaitingRestoreGate wraps every page (H-62)', () => {
    it('control: the layout renders exactly one slot', () => {
        expect(layoutSource().match(/<slot\s*\/>/g) ?? []).toHaveLength(1);
    });

    it('imports AwaitingRestoreGate from the instance feature', () => {
        expect(layoutSource()).toMatch(/import\s+AwaitingRestoreGate\s+from\s+['"]\$lib\/features\/instance\/components\/AwaitingRestoreGate\.svelte['"]/);
    });

    it('wraps the slot in the gate', () => {
        expect(layoutSource()).toMatch(/<AwaitingRestoreGate\b[^>]*>[\s\S]*<slot\s*\/>[\s\S]*<\/AwaitingRestoreGate>/);
    });

    it('opens the gate only once the first dictionary is ready', () => {
        const source = layoutSource();
        const gate = source.indexOf('<AwaitingRestoreGate');
        expect(gate, 'Barrier: the gate is in the markup').toBeGreaterThan(-1);
        const before = source.slice(0, gate);

        expect(before, 'an i18nBooted block opens before the gate').toMatch(/\{#if\s+!?\s*i18nBooted\s*\}/);
        expect(before.lastIndexOf('{#if'), 'the i18nBooted block is still open where the gate opens').toBeGreaterThan(before.lastIndexOf('{/if}'));
    });
});
