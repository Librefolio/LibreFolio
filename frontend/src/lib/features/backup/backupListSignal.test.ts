// @vitest-environment jsdom
/**
 * backupList.svelte.ts — the signal that tells the backup table to read again, and the short form of a SHA-256 (lot
 * FB-24, written red first against `B6r-fb24-frontend-interface.md` §2).
 *
 * The contract under test:
 *   - `backupListSignal` is a `$state({version: 0})` object: a number, the same object every time;
 *   - `notifyBackupListChanged()` adds exactly 1 to `version` per call — the card calls it when a backup ends and when it
 *     deletes one, the table reads again at every change of `version`;
 *   - the signal is reactive: an effect that reads `version` runs again after a notification (a plain object behind the
 *     name would pass a direct read and never wake the table);
 *   - `shortHash(sha)` is `sha.slice(0, 12) + '…'`.
 *
 * The module is loaded inside each case (`await import`), so that while it does not exist each case fails on its own
 * instead of the whole file on a missing import. jsdom, not node: an `$effect` never runs in the node environment (see
 * `$test/runes.svelte`; `assertEffectsRun()` fails the file loudly should the docblock above be lost).
 */
import {flushSync} from 'svelte';
import {beforeAll, describe, expect, it} from 'vitest';
import {assertEffectsRun, recordReads} from '$test/runes.svelte';

// A literal path would fail the whole file at transform time while the module is missing; a variable path fails each case alone.
const MODULE = './backupList.svelte';
const load = (): Promise<typeof import('./backupList.svelte')> => import(/* @vite-ignore */ MODULE);

const SHA = 'a3f1c9d2e4b5a6978877665544332211a3f1c9d2e4b5a6978877665544332211';

beforeAll(() => {
    assertEffectsRun();
});

describe('shortHash', () => {
    it('keeps the first twelve characters and adds an ellipsis', async () => {
        const {shortHash} = await load();

        expect(shortHash(SHA)).toBe('a3f1c9d2e4b5…');
        expect(shortHash(SHA)).toBe(SHA.slice(0, 12) + '…');
    });

    it('is a different string from the whole hash, and shorter', async () => {
        const {shortHash} = await load();

        expect(shortHash(SHA)).not.toBe(SHA);
        expect(shortHash(SHA).length).toBeLessThan(SHA.length);
    });

    it('does not change which characters come first', async () => {
        const {shortHash} = await load();

        expect(shortHash('0123456789abcdefFFFF')).toBe('0123456789ab…');
    });
});

describe('backupListSignal and notifyBackupListChanged', () => {
    it('version is a number, and the signal is one object for every importer', async () => {
        const first = await load();
        const second = await load();

        expect(typeof first.backupListSignal.version).toBe('number');
        expect(second.backupListSignal).toBe(first.backupListSignal);
    });

    it('each notification adds exactly one to version', async () => {
        const {backupListSignal, notifyBackupListChanged} = await load();
        const before = backupListSignal.version;

        notifyBackupListChanged();
        expect(backupListSignal.version).toBe(before + 1);

        notifyBackupListChanged();
        notifyBackupListChanged();
        expect(backupListSignal.version).toBe(before + 3);
    });

    it('is reactive: an effect reading version runs again after a notification', async () => {
        const {backupListSignal, notifyBackupListChanged} = await load();
        const reads = recordReads(() => backupListSignal.version);
        try {
            flushSync();
            const seen = reads.values.length;
            expect(seen, 'the effect ran once on its own').toBeGreaterThanOrEqual(1);

            notifyBackupListChanged();
            flushSync();

            expect(reads.values.length, 'the effect ran again').toBe(seen + 1);
            expect(reads.values.at(-1)).toBe(backupListSignal.version);
        } finally {
            reads.stop();
        }
    });
});
