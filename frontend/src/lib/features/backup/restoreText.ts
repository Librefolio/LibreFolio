/**
 * The restore's codes, as whole i18n keys (lot B5b): every key written out, so that the completeness test of the four
 * catalogues reads them all, and an unknown code falls back to a generic sentence instead of showing a key.
 */

/** The rollback reasons of a restore (`RestoreStatus.reason`). */
export const REASON_KEYS: Record<string, string> = {
    first_start_failed: 'backup.restore.reason.first_start_failed',
    swap_interrupted: 'backup.restore.reason.swap_interrupted',
    swap_failed: 'backup.restore.reason.swap_failed',
    stage_missing: 'backup.restore.reason.stage_missing',
};

/** Why a start left a pending restore waiting (`RestoreStatus.waiting`). */
export const WAITING_KEYS: Record<string, string> = {
    backup_running: 'backup.restore.waiting.backup_running',
    other_data_directory: 'backup.restore.waiting.other_data_directory',
    server_running: 'backup.restore.waiting.server_running',
    instance_blocked: 'backup.restore.waiting.instance_blocked',
};

/** The warnings of a check's report, which let the restore go on. */
export const WARNING_KEYS: Record<string, string> = {
    rows_changed: 'backup.restore.report.warning.rows_changed',
    foreign_key_violations: 'backup.restore.report.warning.foreign_key_violations',
    foreign_key_violations_added: 'backup.restore.report.warning.foreign_key_violations_added',
    control_totals_changed: 'backup.restore.report.warning.control_totals_changed',
    control_totals_unreadable: 'backup.restore.report.warning.control_totals_unreadable',
};

/** How the ledger's control totals compare (lot B-13). */
export const TOTALS_KEYS: Record<string, string> = {
    same: 'backup.restore.report.totals.same',
    changed: 'backup.restore.report.totals.changed',
    absent: 'backup.restore.report.totals.absent',
    other_version: 'backup.restore.report.totals.other_version',
    unreadable: 'backup.restore.report.totals.unreadable',
};

/** Every refusal of the upload, the check, the confirmation, the cancellation and the restart, and the check's codes. */
export const ERROR_KEYS: Record<string, string> = {
    // The upload
    backup_upload_empty: 'backup.restore.errors.backup_upload_empty',
    backup_upload_incomplete: 'backup.restore.errors.backup_upload_incomplete',
    backup_too_large: 'backup.restore.errors.backup_too_large',
    backup_no_space: 'backup.restore.errors.backup_no_space',
    backup_upload_unavailable: 'backup.restore.errors.backup_upload_unavailable',
    backup_restore_unavailable: 'backup.restore.errors.backup_restore_unavailable',
    backup_upload_failed: 'backup.restore.errors.backup_upload_failed',
    backup_upload_not_found: 'backup.restore.errors.backup_upload_not_found',
    restore_folder_unusable: 'backup.restore.errors.restore_folder_unusable',
    // The check
    restore_busy: 'backup.restore.errors.restore_busy',
    restore_stage_running: 'backup.restore.errors.restore_stage_running',
    restore_stage_not_found: 'backup.restore.errors.restore_stage_not_found',
    not_a_backup: 'backup.restore.errors.not_a_backup',
    archive_unreadable: 'backup.restore.errors.archive_unreadable',
    archive_damaged: 'backup.restore.errors.archive_damaged',
    manifest_newer_format: 'backup.restore.errors.manifest_newer_format',
    manifest_invalid: 'backup.restore.errors.manifest_invalid',
    manifest_unreadable: 'backup.restore.errors.manifest_unreadable',
    manifest_too_large: 'backup.restore.errors.manifest_too_large',
    too_many_entries: 'backup.restore.errors.too_many_entries',
    unpacked_too_large: 'backup.restore.errors.unpacked_too_large',
    duplicate_entry: 'backup.restore.errors.duplicate_entry',
    unexpected_entry: 'backup.restore.errors.unexpected_entry',
    not_a_file: 'backup.restore.errors.not_a_file',
    encrypted_entry: 'backup.restore.errors.encrypted_entry',
    unsupported_entry: 'backup.restore.errors.unsupported_entry',
    checksum_mismatch: 'backup.restore.errors.checksum_mismatch',
    missing_entry: 'backup.restore.errors.missing_entry',
    no_space: 'backup.restore.errors.no_space',
    stage_failed: 'backup.restore.errors.stage_failed',
    database_damaged: 'backup.restore.errors.database_damaged',
    database_foreign_objects: 'backup.restore.errors.database_foreign_objects',
    manifest_mismatch: 'backup.restore.errors.manifest_mismatch',
    head_unknown: 'backup.restore.errors.head_unknown',
    revision_missing: 'backup.restore.errors.revision_missing',
    revision_unknown: 'backup.restore.errors.revision_unknown',
    upgrade_failed: 'backup.restore.errors.upgrade_failed',
    post_migration_failed: 'backup.restore.errors.post_migration_failed',
    restore_interrupted: 'backup.restore.errors.restore_interrupted',
    // A secure backup (lot B4): its password, or an envelope that cannot be opened
    wrong_password: 'backup.restore.errors.wrong_password',
    password_required: 'backup.restore.errors.password_required',
    envelope_damaged: 'backup.restore.errors.envelope_damaged',
    envelope_unsupported: 'backup.restore.errors.envelope_unsupported',
    // The confirmation, the cancellation, the restart
    restore_stage_expired: 'backup.restore.errors.restore_stage_expired',
    restore_stage_outdated: 'backup.restore.errors.restore_stage_outdated',
    restore_not_restorable: 'backup.restore.errors.restore_not_restorable',
    restore_already_pending: 'backup.restore.errors.restore_already_pending',
    restore_not_pending: 'backup.restore.errors.restore_not_pending',
    restore_pending: 'backup.restore.errors.restore_pending',
    restore_confirm_failed: 'backup.restore.errors.restore_confirm_failed',
    restore_cancel_failed: 'backup.restore.errors.restore_cancel_failed',
    restore_restart_failed: 'backup.restore.errors.restore_restart_failed',
    restore_state_unreadable: 'backup.restore.errors.restore_state_unreadable',
    // No usable answer
    network: 'backup.restore.errors.network',
    unexpected: 'backup.restore.errors.unexpected',
};

function keyFor(keys: Record<string, string>, code: string | null | undefined, fallback: string): string {
    return code !== null && code !== undefined && Object.hasOwn(keys, code) ? keys[code] : fallback;
}

export function restoreErrorKey(code: string | null | undefined): string {
    return keyFor(ERROR_KEYS, code, ERROR_KEYS.unexpected);
}

export function restoreReasonKey(reason: string | null | undefined): string {
    return keyFor(REASON_KEYS, reason, 'backup.restore.reason.unknown');
}

export function restoreWaitingKey(waiting: string | null | undefined): string {
    return keyFor(WAITING_KEYS, waiting, 'backup.restore.waiting.unknown');
}

export function restoreWarningKey(warning: string): string {
    return keyFor(WARNING_KEYS, warning, 'backup.restore.report.warning.unknown');
}

export function restoreTotalsKey(status: string | null | undefined): string {
    return keyFor(TOTALS_KEYS, status, TOTALS_KEYS.absent);
}
