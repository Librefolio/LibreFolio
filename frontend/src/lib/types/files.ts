/**
 * File Types
 *
 * Types for static uploads and BRIM (Broker Report Import Manager) files.
 * Derived from Zod schemas in generated.ts.
 */

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// =============================================================================
// STATIC UPLOAD TYPES (from /uploads endpoints)
// =============================================================================

/**
 * Information about a static uploaded file.
 * Retrieved from GET /uploads
 */
export type UploadedFile = z.infer<typeof schemas.UploadFileInfo>;

// =============================================================================
// BRIM TYPES (from /brokers/import endpoints)
// =============================================================================

/**
 * Information about a BRIM file (broker report).
 * Retrieved from GET /brokers/import/files
 */
export type BrimFile = z.infer<typeof schemas.BRIMFileInfo>;

/**
 * Status of a BRIM file.
 */
export type BrimFileStatus = z.infer<typeof schemas.BRIMFileStatus>;

/**
 * Information about a BRIM import plugin.
 * Retrieved from GET /brokers/import/plugins
 */
export type BrimPlugin = z.infer<typeof schemas.BRIMPluginInfo>;

/**
 * Response from parsing a BRIM file.
 */
export type BrimParseResponse = z.infer<typeof schemas.BRIMParseResponse>;

/**
 * Asset mapping from parsed BRIM file.
 */
export type BrimAssetMapping = z.infer<typeof schemas.BRIMAssetMapping>;

/**
 * Asset candidate for mapping.
 */
export type BrimAssetCandidate = z.infer<typeof schemas.BRIMAssetCandidate>;

/**
 * Confidence level for asset matching.
 */
export type BrimMatchConfidence = z.infer<typeof schemas.BRIMMatchConfidence>;

/**
 * Duplicate detection report.
 */
export type BrimDuplicateReport = z.infer<typeof schemas.BRIMDuplicateReport>;

/**
 * Single duplicate match entry.
 */
export type BrimDuplicateMatch = z.infer<typeof schemas.BRIMDuplicateMatch>;

/**
 * Duplicate detection confidence level.
 */
export type BrimDuplicateLevel = z.infer<typeof schemas.BRIMDuplicateLevel>;

// =============================================================================
// FRONTEND-ONLY TYPES
// =============================================================================

/**
 * Combined file type for tables that show both static and BRIM files.
 */
export type FileData = UploadedFile | BrimFile;

/**
 * File with UI state for interactive components.
 */
export interface FileWithUIState {
    file: FileData;
    isSelected?: boolean;
    isLoading?: boolean;
}
