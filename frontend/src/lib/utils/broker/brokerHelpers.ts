/**
 * Broker Helpers — Shared utility functions for broker icon resolution.
 *
 * Priority for all icon lookups (matches `brokerIconChain.svelte.ts`):
 *  1. icon_url — explicitly uploaded by the user (most reliable)
 *  2. portal_url → origin + `/favicon.ico` (external heuristic)
 *  3. default_import_plugin → cached plugin icon (app-hosted, async)
 *  4. caller UI fallback (usually system briefcase icon)
 *
 * For reactive multi-URL fallback with load-error retry, use
 * `createBrokerIconChain` from `brokerIconChain.svelte.ts`.
 *
 * @module utils/brokerHelpers
 */

import type {BrokerLike} from './brokerColors';
import {zodiosApi} from '$lib/api';

/** Minimal shape for broker icon resolution (subset of BrokerLike). */
export interface BrokerIconSource {
    icon_url?: string | null;
    portal_url?: string | null;
    default_import_plugin?: string | null;
}

export type BrokerIconExhaustedAction = 'hide' | 'show-next-sibling';

export interface BrokerIconHtmlOptions {
    width?: number;
    height?: number;
    className?: string;
    style?: string;
    alt?: string;
    referrerPolicy?: string;
    onExhausted?: BrokerIconExhaustedAction;
}

// ============================================================================
// Plugin icon cache — loaded lazily on first need, shared for the session.
// ============================================================================

let _pluginIconCache: Map<string, string> | null = null;
let _pluginIconLoading: Promise<void> | null = null;

/** Ensure plugin icon cache is populated. Safe to call multiple times. */
export async function ensurePluginIconsLoaded(): Promise<void> {
    if (_pluginIconCache) return;
    if (_pluginIconLoading) return _pluginIconLoading;
    _pluginIconLoading = (async () => {
        try {
            const plugins = await zodiosApi.list_plugins_api_v1_brokers_import_plugins_get();
            _pluginIconCache = new Map();
            for (const p of plugins) {
                const rawIcon = p?.icon_url as string | null | undefined;
                if (rawIcon && p.code) _pluginIconCache.set(p.code, rawIcon);
            }
        } catch {
            _pluginIconCache = new Map(); // don't retry on error
        } finally {
            _pluginIconLoading = null;
        }
    })();
    return _pluginIconLoading;
}

/**
 * Sync lookup — returns the cached plugin icon URL or null.
 * Returns null if the plugin icon cache has not been loaded yet;
 * call `ensurePluginIconsLoaded()` first to populate it.
 */
export function getPluginIconUrl(pluginCode: string | null | undefined): string | null {
    const normalizedCode = normalizeBrokerIconField(pluginCode);
    if (!normalizedCode || !_pluginIconCache) return null;
    return _pluginIconCache.get(normalizedCode) ?? null;
}

function escapeHtmlAttr(value: string): string {
    return value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export function normalizeBrokerIconField(value: unknown): string | null {
    if (typeof value === 'string') {
        const trimmed = value.trim();
        return trimmed ? trimmed : null;
    }
    if (Array.isArray(value)) {
        for (const item of value) {
            const normalized = normalizeBrokerIconField(item);
            if (normalized) return normalized;
        }
    }
    return null;
}

function getExhaustedScript(action: BrokerIconExhaustedAction): string {
    const exhausted = action === 'show-next-sibling' ? "this.style.display='none';const fallback=this.nextElementSibling;if(fallback){fallback.style.display='inline-flex';}" : "this.style.display='none';";
    return `try{const raw=this.dataset.fallbacks||'[]';const urls=JSON.parse(raw);const next=urls.shift();if(next){this.dataset.fallbacks=JSON.stringify(urls);this.src=next;return;}}catch{}${exhausted}`;
}

function getBrokerSourceById(brokerId: number, brokers: Map<number, BrokerIconSource> | ReadonlyArray<BrokerLike>): BrokerIconSource | undefined {
    if (brokers instanceof Map) {
        return brokers.get(brokerId);
    }
    return brokers.find((b) => b.id === brokerId);
}

function buildBriefcaseFallbackHtml({width = 16, height = 16, className, style, visible = false}: Pick<BrokerIconHtmlOptions, 'width' | 'height' | 'className' | 'style'> & {visible?: boolean} = {}): string {
    const attrs = ['aria-hidden="true"', `style="${escapeHtmlAttr((style ?? '') + `;display:${visible ? 'inline-flex' : 'none'};align-items:center;justify-content:center;flex-shrink:0;`)}"`];
    if (className) attrs.push(`class="${escapeHtmlAttr(className)}"`);
    return [
        `<span ${attrs.join(' ')}>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">`,
        '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"></rect>',
        '<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>',
        '</svg>',
        '</span>',
    ].join('');
}

/**
 * Build the ordered list of candidate icon URLs for a broker.
 * Priority matches the reactive chain in `brokerIconChain.svelte.ts`:
 *   1. icon_url (custom, most reliable)
 *   2. portal_url/favicon.ico (external heuristic)
 *   3. default_import_plugin → cached plugin icon (app-hosted, async-loaded)
 *
 * For non-reactive contexts (inline HTML renderers). For full fallback
 * chain with load-error retry use `createBrokerIconChain` in components.
 */
export function getBrokerIconCandidates(broker: BrokerIconSource | null | undefined): string[] {
    if (!broker) return [];
    const urls: string[] = [];
    const iconUrl = normalizeBrokerIconField(broker.icon_url);
    const portalUrl = normalizeBrokerIconField(broker.portal_url);
    if (iconUrl) urls.push(iconUrl);
    if (portalUrl) {
        try {
            urls.push(new URL(portalUrl).origin + '/favicon.ico');
        } catch {
            /* invalid URL — skip */
        }
    }
    const pluginIcon = getPluginIconUrl(broker.default_import_plugin);
    if (pluginIcon) urls.push(pluginIcon);
    return urls;
}

/**
 * Resolve the ordered list of broker icon candidates by id.
 *
 * Accepts both `Map<number, BrokerIconSource>` and `ReadonlyArray<BrokerLike>`.
 */
export function getBrokerIconCandidatesById(brokerId: number, brokers: Map<number, BrokerIconSource> | ReadonlyArray<BrokerLike>): string[] {
    return getBrokerIconCandidates(getBrokerSourceById(brokerId, brokers));
}

/**
 * Resolve the best icon URL for a broker using the fallback chain.
 * Returns the first available URL from the candidate list (sync, cache-dependent).
 *
 * NOTE: The returned URL may still fail to load (e.g. favicon 404).
 * Components that support multi-URL fallback should use `getBrokerIconCandidates()`
 * and `BrokerIcon.svelte` instead, which handle load errors reactively.
 */
export function getBrokerIconUrl(broker: BrokerIconSource | null | undefined): string | null {
    const candidates = getBrokerIconCandidates(broker);
    return candidates[0] ?? null;
}

/**
 * Resolve a broker icon URL by id from a list/map of brokers.
 *
 * Accepts both `Map<number, BrokerIconSource>` and `ReadonlyArray<BrokerLike>`.
 */
export function getBrokerIconUrlById(brokerId: number, brokers: Map<number, BrokerIconSource> | ReadonlyArray<BrokerLike>): string | null {
    return getBrokerIconCandidatesById(brokerId, brokers)[0] ?? null;
}

/**
 * Build chained `<img>` HTML for raw-HTML contexts (tooltips, HtmlCell).
 * Uses the same ordered candidate list as the reactive Svelte components.
 */
export function getBrokerIconImgHtml(broker: BrokerIconSource | null | undefined, {width = 16, height = 16, className, style, alt = '', referrerPolicy = 'no-referrer', onExhausted = 'hide'}: BrokerIconHtmlOptions = {}): string {
    const candidates = getBrokerIconCandidates(broker);
    if (candidates.length === 0) return '';
    const attrs = [
        `src="${escapeHtmlAttr(candidates[0])}"`,
        `alt="${escapeHtmlAttr(alt)}"`,
        `width="${width}"`,
        `height="${height}"`,
        `data-fallbacks="${escapeHtmlAttr(JSON.stringify(candidates.slice(1)))}"`,
        `onerror="${escapeHtmlAttr(getExhaustedScript(onExhausted))}"`,
        `referrerpolicy="${escapeHtmlAttr(referrerPolicy)}"`,
    ];
    if (className) attrs.push(`class="${escapeHtmlAttr(className)}"`);
    if (style) attrs.push(`style="${escapeHtmlAttr(style)}"`);
    return `<img ${attrs.join(' ')}>`;
}

/**
 * Build broker icon HTML with a hidden briefcase fallback sibling.
 * Useful in raw-HTML contexts that still need the full 4-step chain.
 */
export function getBrokerIconHtml(broker: BrokerIconSource | null | undefined, options: BrokerIconHtmlOptions = {}): string {
    const imgHtml = getBrokerIconImgHtml(broker, {...options, onExhausted: 'show-next-sibling'});
    if (!imgHtml) {
        return buildBriefcaseFallbackHtml({...options, visible: true});
    }
    return imgHtml + buildBriefcaseFallbackHtml(options);
}

export function getBrokerIconImgHtmlById(brokerId: number, brokers: Map<number, BrokerIconSource> | ReadonlyArray<BrokerLike>, options: BrokerIconHtmlOptions = {}): string {
    return getBrokerIconImgHtml(getBrokerSourceById(brokerId, brokers), options);
}

export function getBrokerIconHtmlById(brokerId: number, brokers: Map<number, BrokerIconSource> | ReadonlyArray<BrokerLike>, options: BrokerIconHtmlOptions = {}): string {
    return getBrokerIconHtml(getBrokerSourceById(brokerId, brokers), options);
}
