/**
 * The report a check sends to the instance's support (FB-27): «Contact support» on a check only the host can solve,
 * and on the page of an interrupted restore.
 *
 * It carries what support needs to find the instance and the check: the check's code, how serious it is, the
 * instance's address, the app's version and the date. Never the user, an email address, a secret or any portfolio data:
 * the input has no field for them, and the check's details (its parameters) stay out too.
 */
import type {SupportReport} from '$lib/features/support/supportChannel';

export type CheckReportSeverity = 'error' | 'warning' | 'info';

export interface CheckReportInput {
    /** The check's id (`platform.hosting_panel`) or the state's code (`platform.restore_interrupted`). */
    checkId: string;
    severity: CheckReportSeverity;
    /** The instance's address, as the browser reaches it (`location.origin`). */
    instanceAddress: string;
    appVersion: string;
    date: Date;
}

/** The report of a check, in English: a subject and a plain-text body, the same for the same input. */
export function buildCheckReport(input: CheckReportInput): SupportReport {
    const lines = [`A LibreFolio check needs the person who provides this service: ${input.checkId}.`, '', `Check: ${input.checkId}`, `Severity: ${input.severity}`, `Instance: ${input.instanceAddress}`, `LibreFolio ${input.appVersion}`, `Date: ${input.date.toISOString()}`];
    return {subject: `LibreFolio: ${input.checkId} needs attention`, body: lines.join('\n')};
}
