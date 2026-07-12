/**
 * Helpers for broker FIFO lot detail panel URL state.
 *
 * Keeps currently opened asset panel synced with `?asset=`.
 */
import {getOptionalNumberParam, setOptionalNumberParam} from '$lib/utils/url/queryParams';

const ASSET_QUERY_PARAM = 'asset';

export function getAssetPanelAssetId(searchParams: URLSearchParams): number | undefined {
    return getOptionalNumberParam(searchParams, ASSET_QUERY_PARAM);
}

export function buildAssetPanelUrl(currentUrl: URL, assetId: number | null | undefined): string {
    const params = new URLSearchParams(currentUrl.searchParams);
    params.delete(ASSET_QUERY_PARAM);
    setOptionalNumberParam(params, ASSET_QUERY_PARAM, assetId);

    const search = params.toString();
    return search ? `${currentUrl.pathname}?${search}` : currentUrl.pathname;
}
