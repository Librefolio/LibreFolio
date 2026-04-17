/**
 * URL Filter Utilities for DataTable
 *
 * Provides functions to sync DataTable filters with URL query parameters.
 * Enables deep-linking to specific filter states.
 */

import type {DateFilter, EnumFilter, FilterValue, SizeFilter, TextFilter} from '$lib/components/table/types';

/**
 * Configuration for a URL-filterable column
 */
export interface UrlFilterConfig {
    /** URL parameter key */
    urlKey: string;
    /** Filter type (must match column type) */
    type: 'text' | 'enum' | 'size' | 'date';
}

/**
 * Parse URL search params into filter values.
 * Unknown keys are silently ignored.
 *
 * @param searchParams - URL search params to parse
 * @param columns - Column configurations defining valid URL keys
 * @returns Map of urlKey -> FilterValue
 *
 * @example
 * // URL: ?filename=report&broker=1,2&status=uploaded,parsed&size=1000-50000
 * const filters = parseUrlFilters(url.searchParams, [
 *   { urlKey: 'filename', type: 'text' },
 *   { urlKey: 'broker', type: 'enum' },
 *   { urlKey: 'status', type: 'enum' },
 *   { urlKey: 'size', type: 'size' },
 * ]);
 */
export function parseUrlFilters(searchParams: URLSearchParams, columns: UrlFilterConfig[]): Map<string, FilterValue> {
    const filters = new Map<string, FilterValue>();
    const columnMap = new Map(columns.map((c) => [c.urlKey, c]));

    for (const [key, value] of searchParams.entries()) {
        const col = columnMap.get(key);
        if (!col || !value) continue;

        try {
            switch (col.type) {
                case 'text': {
                    // Format: "value" or "value:matchMode"
                    // matchMode can be: contains, startsWith, endsWith, equals
                    let textValue = value;
                    let matchMode: 'contains' | 'startsWith' | 'endsWith' | 'equals' = 'contains';

                    const lastColon = value.lastIndexOf(':');
                    if (lastColon > 0) {
                        const possibleMode = value.substring(lastColon + 1);
                        if (['contains', 'startsWith', 'endsWith', 'equals'].includes(possibleMode)) {
                            textValue = value.substring(0, lastColon);
                            matchMode = possibleMode as typeof matchMode;
                        }
                    }

                    const filter: TextFilter = {
                        type: 'text',
                        value: textValue,
                        matchMode,
                    };
                    filters.set(key, filter);
                    break;
                }

                case 'enum': {
                    const selected = value.split(',').filter((v) => v.trim());
                    if (selected.length > 0) {
                        const filter: EnumFilter = {
                            type: 'enum',
                            selected,
                        };
                        filters.set(key, filter);
                    }
                    break;
                }

                case 'size': {
                    // Format: "min-max" (either can be empty)
                    const [minStr, maxStr] = value.split('-');
                    const minBytes = minStr ? parseInt(minStr, 10) : undefined;
                    const maxBytes = maxStr ? parseInt(maxStr, 10) : undefined;

                    if ((minBytes !== undefined && !isNaN(minBytes)) || (maxBytes !== undefined && !isNaN(maxBytes))) {
                        const filter: SizeFilter = {
                            type: 'size',
                            minBytes: minBytes && !isNaN(minBytes) ? minBytes : undefined,
                            maxBytes: maxBytes && !isNaN(maxBytes) ? maxBytes : undefined,
                        };
                        filters.set(key, filter);
                    }
                    break;
                }

                case 'date': {
                    // Format: "from,to" (either can be empty)
                    const [from, to] = value.split(',');
                    if (from || to) {
                        const filter: DateFilter = {
                            type: 'date',
                            from: from || undefined,
                            to: to || undefined,
                        };
                        filters.set(key, filter);
                    }
                    break;
                }
            }
        } catch (e) {
            // Skip malformed values
            console.warn(`Failed to parse URL filter for key "${key}":`, e);
        }
    }

    return filters;
}

/**
 * Build URL search params from filter values.
 * Only includes non-empty filter values.
 *
 * @param filters - Map of columnId -> FilterValue
 * @param columns - Column configurations for URL key mapping
 * @param columnIdToUrlKey - Optional mapping from column ID to URL key (if different)
 * @returns URLSearchParams with filter values
 */
export function buildUrlFilters(filters: Map<string, FilterValue>, columns: UrlFilterConfig[], columnIdToUrlKey?: Map<string, string>): URLSearchParams {
    const params = new URLSearchParams();
    const validKeys = new Set(columns.map((c) => c.urlKey));

    for (const [columnId, filterValue] of filters.entries()) {
        if (!filterValue) continue;

        // Get URL key (might be different from column ID)
        const urlKey = columnIdToUrlKey?.get(columnId) ?? columnId;
        if (!validKeys.has(urlKey)) continue;

        switch (filterValue.type) {
            case 'text': {
                if (filterValue.value) {
                    // Include matchMode if not default (contains)
                    if (filterValue.matchMode && filterValue.matchMode !== 'contains') {
                        params.set(urlKey, `${filterValue.value}:${filterValue.matchMode}`);
                    } else {
                        params.set(urlKey, filterValue.value);
                    }
                }
                break;
            }

            case 'enum': {
                if (filterValue.selected && filterValue.selected.length > 0) {
                    params.set(urlKey, filterValue.selected.join(','));
                }
                break;
            }

            case 'size': {
                const min = filterValue.minBytes;
                const max = filterValue.maxBytes;
                if (min !== undefined || max !== undefined) {
                    const minStr = min !== undefined ? String(min) : '';
                    const maxStr = max !== undefined ? String(max) : '';
                    params.set(urlKey, `${minStr}-${maxStr}`);
                }
                break;
            }

            case 'date': {
                const from = filterValue.from;
                const to = filterValue.to;
                if (from || to) {
                    params.set(urlKey, `${from || ''},${to || ''}`);
                }
                break;
            }
        }
    }

    return params;
}

/**
 * Check if any filters are active
 */
export function hasActiveFilters(filters: Map<string, FilterValue>): boolean {
    for (const [_, value] of filters) {
        if (!value) continue;

        switch (value.type) {
            case 'text':
                if (value.value) return true;
                break;
            case 'enum':
                if (value.selected && value.selected.length > 0) return true;
                break;
            case 'size':
                if (value.minBytes !== undefined || value.maxBytes !== undefined) return true;
                break;
            case 'date':
                if (value.from || value.to) return true;
                break;
        }
    }
    return false;
}

/**
 * Clean URL by removing empty/invalid filter params
 */
export function cleanUrlParams(searchParams: URLSearchParams, validKeys: Set<string>): URLSearchParams {
    const cleaned = new URLSearchParams();

    for (const [key, value] of searchParams.entries()) {
        if (validKeys.has(key) && value) {
            cleaned.set(key, value);
        }
    }

    return cleaned;
}
