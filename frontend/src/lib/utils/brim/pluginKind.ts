/**
 * Generic fallback import plugins — the generic CSV — as the backend ranks them.
 *
 * `BRIMProvider.detection_priority` (backend/app/services/brim_provider.py) suggests 100 and up for
 * broker-specific plugins, 50-99 for semi-generic ones and 0-49 for generic fallbacks. A plugin below
 * this limit was not made for one broker. Wherever a plugin made for the broker must win over a
 * generic one — the import wizard's wrong-broker check, the broker icon chain — this is the one place
 * that tells them apart.
 */
export const FALLBACK_PLUGIN_PRIORITY_LIMIT = 50;

/** What the check reads of a plugin: without a priority a plugin is broker-specific, the backend's default (100). */
export interface PluginPriority {
    detection_priority?: number | null;
}

export function isFallbackPlugin(plugin: PluginPriority): boolean {
    return (plugin.detection_priority ?? 100) < FALLBACK_PLUGIN_PRIORITY_LIMIT;
}
