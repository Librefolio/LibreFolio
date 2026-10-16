/**
 * The types of ImportWizardModal's state that its step components share (features/transactions/import/).
 * Cut from ImportWizardModal.svelte (FE8a).
 */
import type {BrimFile, BrimParseResponse, BrimSetPreview} from '$lib/types';
import type {BrokerInfo} from '$lib/stores/reference/brokerStore';
import type {SetPreviewState} from '$lib/features/transactions/import/importReportSets';

/** The steps of the wizard, in the order they can appear. */
export type StepId = 'upload' | 'select' | 'analyze' | 'assets' | 'fix' | 'duplicates' | 'review' | 'gapFix';

export interface PendingFileEntry {
    id: string;
    file: globalThis.File;
    fileName: string;
    brokerId: number | null;
    status: 'pending' | 'uploading' | 'uploaded' | 'error';
    serverFileId?: string;
    /** The server's file info, from the upload response: role detection needs its plugins and batch. */
    serverInfo?: BrimFile;
    errorMessage?: string;
}

/** A required export missing from a set this session uploaded (design §4.2). */
export interface Step1SetWarning {
    key: string;
    pluginCode: string;
    pluginName: string;
    docsUrl: string | null;
    roleCode: string;
    roleLabel: string;
    extensions: string;
    start: string | null;
    end: string | null;
}

export interface FileSelection {
    fileId: string;
    fileName: string;
    brokerId: number;
    pluginCode: string;
}

/** A set's preview, with the members it was asked for: another membership needs another preview. */
export type SetPreviewEntry = SetPreviewState & {preview?: BrimSetPreview | null; members?: string};

export interface ParsedFileResult {
    fileId: string;
    fileName: string;
    brokerId: number;
    brokerName: string;
    brokerIconUrl: string | null;
    brokerPortalUrl: string | null;
    pluginUsed: string;
    pluginName: string;
    status: 'pending' | 'parsing' | 'done' | 'error';
    response: BrimParseResponse | null;
    errorMessage?: string;
    /** Set when the row is a report set, analysed as one through its combined file. */
    set?: ParsedSetInfo;
}

/** A report set analysed as one row: its files, and the combined file it is parsed through. */
export interface ParsedSetInfo {
    key: string;
    batchId: string;
    /** The originals of the upload left out of the set: the combine must leave them out too. */
    excludeFileIds: string[];
    uploadedAt: string;
    memberIds: string[];
    memberNames: string[];
    combinedFileId: string | null;
    summary: Record<string, unknown> | null;
    reused: boolean;
}

export interface BrokerOpeningIssue {
    brokerId: number;
    broker: BrokerInfo | {id: number; name: string};
    openedAt: string;
    minTxDate: string;
    count: number;
}
