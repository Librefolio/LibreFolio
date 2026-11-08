/**
 * The signal between the modal that restores a kept backup and the restore card (A10, T-15).
 *
 * «Restore» on a row of the kept backups opens a modal of its own, wherever the list is (Settings › Backup, Files ›
 * Backups). When that modal closes on a check left for later, dropped, or failed, the card reads its state again: it
 * lists the checks waiting for a decision, to resume or discard. A counter, as `backupListSignal`: a card that mounts
 * later reads the state anyway.
 */
export const restoreSignal = $state({version: 0});

/** Tell the restore card, if one is on screen, to read the state of the restore again. */
export function notifyRestoreChanged(): void {
    restoreSignal.version += 1;
}
