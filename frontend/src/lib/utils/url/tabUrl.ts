import {getOptionalQueryParam, setOptionalQueryParam} from '$lib/utils/url/queryParams';

const TAB_QUERY_PARAM = 'tab';

export function getOptionalTabParam<T extends string>(searchParams: URLSearchParams, validTabIds: readonly T[]): T | undefined {
    const tabId = getOptionalQueryParam(searchParams, TAB_QUERY_PARAM);
    if (!tabId) return undefined;
    return validTabIds.includes(tabId as T) ? (tabId as T) : undefined;
}

export function getResolvedTabParam<T extends string>(searchParams: URLSearchParams, validTabIds: readonly T[], fallbackTabId: T): T {
    return getOptionalTabParam(searchParams, validTabIds) ?? fallbackTabId;
}

export function buildTabUrl(currentUrl: URL, tabId: string | null | undefined): string {
    const params = new URLSearchParams(currentUrl.searchParams);
    params.delete(TAB_QUERY_PARAM);
    setOptionalQueryParam(params, TAB_QUERY_PARAM, tabId);

    const search = params.toString();
    return search ? `${currentUrl.pathname}?${search}` : currentUrl.pathname;
}

/**
 * The tab URL built from the address bar instead of SvelteKit's `$page.url`. A page that writes its dates with
 * `history.replaceState` (`replaceHistoryDateRange`) changes the bar but not `$page.url`, so building from `$page.url`
 * puts the old dates back on a tab change (K-20).
 */
export function buildTabUrlFromLocation(currentHref: string, tabId: string | null | undefined): string {
    return buildTabUrl(new URL(currentHref), tabId);
}
