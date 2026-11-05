/**
 * The signal between the backup card and the table of the backups the instance keeps (lot FB-24).
 *
 * The card tells «read the list again» when a backup ends or one is deleted; every `BackupList` on screen listens. A
 * counter, not an event: a table that mounts later reads the list once anyway, and one that is not mounted misses nothing.
 */
export const backupListSignal = $state({version: 0});

/** Tell every table of kept backups to read the list again. */
export function notifyBackupListChanged(): void {
    backupListSignal.version += 1;
}

/** A SHA-256 as the table shows it: its first twelve characters. The whole hash is what the copy button copies. */
export function shortHash(sha: string): string {
    return `${sha.slice(0, 12)}…`;
}
