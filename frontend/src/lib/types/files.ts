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

/**
 * Structured preview payload returned by preview endpoints.
 */
export type FilePreviewResponse = z.infer<typeof schemas.FilePreviewResponse>;

/**
 * Supported file preview categories.
 */
export type FilePreviewType = z.infer<typeof schemas.FilePreviewType>;

// =============================================================================
// BRIM TYPES (from /brokers/import endpoints)
// =============================================================================

/**
 * Information about a BRIM file (broker report).
 * Retrieved from GET /brokers/import/files
 */
export type BrimFile = z.infer<typeof schemas.BRIMFileInfo>;

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
 * Structured validation issue from BRIM parse.
 */
export type BrimValidationIssue = z.infer<typeof schemas.BRIMValidationIssue>;

/**
 * A source-data table backing a notice or a field todo.
 * Rendered as a navigable table next to the human-readable comment.
 */
export type BrimEvidence = z.infer<typeof schemas.BRIMEvidence>;

/**
 * Parser notice: an `info` or `warning` message with optional evidence tables.
 * Plugins may still emit plain strings; the backend coerces them to a
 * `warning` notice, so this type is always the shape received by the frontend.
 */
export type BrimNotice = z.infer<typeof schemas.BRIMNotice>;

/**
 * Field todo: an accepted TX with a field intentionally left incomplete.
 */
export type BrimFieldTodo = z.infer<typeof schemas.BRIMFieldTodo>;

/**
 * Asset mapping from parsed BRIM file.
 */
export type BrimAssetMapping = z.infer<typeof schemas.BRIMAssetMapping>;

/**
 * Single duplicate match entry.
 */
export type BrimDuplicateMatch = z.infer<typeof schemas.BRIMDuplicateMatch>;

// =============================================================================
// FRONTEND-ONLY TYPES
// =============================================================================

/**
 * Combined file type for tables that show both static and BRIM files.
 */
export type FileData = UploadedFile | BrimFile;
