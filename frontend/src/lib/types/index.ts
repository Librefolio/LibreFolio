/**
 * LibreFolio Frontend Type Library
 *
 * Centralized TypeScript types for all domain entities.
 * Types are derived from Zod schemas in generated.ts to stay in sync with backend.
 *
 * Organization:
 * - common.ts: Shared utility types (Currency, UserRole, etc.)
 * - user.ts: User and authentication types
 * - settings.ts: User preferences and global settings
 * - broker.ts: Broker entity types
 * - transaction.ts: Transaction types
 * - files.ts: Upload and BRIM file types
 * - asset.ts: Financial asset types
 *
 * Usage:
 *   import type { Broker, BrokerSummary } from '$lib/types';
 *   import type { AuthUser, UserSettings } from '$lib/types';
 *   import type { BrimFile, UploadedFile } from '$lib/types';
 *
 * @module types
 */

// Common/shared types
export * from './common';

// Domain types
export * from './user';
export * from './settings';
export * from './broker';
export * from './transaction';
export * from './files';
export * from './asset';
