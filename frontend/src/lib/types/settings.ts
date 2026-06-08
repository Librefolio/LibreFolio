/**
 * Settings Types
 *
 * Types for user preferences and global application settings.
 * Derived from Zod schemas in generated.ts.
 */

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * User settings (preferences).
 * Retrieved from GET /settings/user
 */
export type UserSettings = z.infer<typeof schemas.UserSettingsRead>;

/**
 * Request body for PUT /settings/user
 */
export type UserSettingsUpdate = z.infer<typeof schemas.UserSettingsUpdate>;

/**
 * Single global setting.
 */
export type GlobalSetting = z.infer<typeof schemas.GlobalSettingRead>;

/**
 * Response from GET /settings/global (list all)
 */
export type GlobalSettingsListResponse = z.infer<typeof schemas.GlobalSettingsListResponse>;

// =============================================================================
// FRONTEND-ONLY TYPES
// =============================================================================

/**
 * Theme options for the UI.
 */
export type Theme = 'light' | 'dark' | 'auto';

/**
 * Supported locales for i18n.
 */
export type SupportedLocale = 'en' | 'it' | 'fr' | 'es';
