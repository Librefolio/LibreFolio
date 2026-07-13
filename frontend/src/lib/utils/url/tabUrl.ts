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
