import type {ComponentProps} from 'svelte';
import {zodiosApi} from '$lib/api';
import {safeNumber, safeScalar, safeString} from '$lib/types/common';
import type AssetModal from './AssetModal.svelte';
import {normalizeDistribution} from './assetPayload';

export type AssetEditData = NonNullable<ComponentProps<typeof AssetModal>['editData']>;

/** List summaries omit classification; an edit needs all three authoritative reads. */
export async function loadAssetEditData(assetId: number): Promise<AssetEditData> {
    const [assets, metadata, assignments] = await Promise.all([
        zodiosApi.list_assets_api_v1_assets_query_get({queries: {}}),
        zodiosApi.read_assets_bulk_api_v1_assets_get({queries: {asset_ids: [assetId]}}),
        zodiosApi.get_provider_assignments_api_v1_assets_provider_assignments_get({queries: {asset_ids: [assetId]}}),
    ]);
    const asset = assets.find((item) => item.id === assetId);
    const detail = metadata.find((item) => item.asset_id === assetId);
    if (!asset || !detail || detail.classification_params === undefined) {
        throw new Error('Complete asset metadata could not be loaded.');
    }
    const assignment = assignments.find((item) => item.asset_id === assetId);
    const classification = safeScalar(detail.classification_params);
    const sector = safeScalar(classification?.sector_area);
    const geographic = safeScalar(classification?.geographic_area);

    return {
        id: asset.id,
        display_name: asset.display_name,
        currency: asset.currency,
        asset_type: safeString(asset.asset_type) ?? 'STOCK',
        icon_url: safeString(asset.icon_url),
        quote_base_quantity: safeNumber(asset.quote_base_quantity),
        active: asset.active,
        classification_params: classification
            ? {
                  short_description: safeString(classification.short_description),
                  sector_area: sector ? {distribution: normalizeDistribution(sector.distribution)} : null,
                  geographic_area: geographic ? {distribution: normalizeDistribution(geographic.distribution)} : null,
              }
            : null,
        identifier_isin: safeString(asset.identifier_isin),
        identifier_ticker: safeString(asset.identifier_ticker),
        identifier_cusip: safeString(asset.identifier_cusip),
        identifier_sedol: safeString(asset.identifier_sedol),
        identifier_figi: safeString(asset.identifier_figi),
        identifier_uuid: safeString(asset.identifier_uuid),
        identifier_other: asset.identifier_other?.filter((value): value is string => typeof value === 'string') ?? null,
        provider_code: assignment?.provider_code ?? null,
        provider_identifier: safeString(assignment?.identifier) ?? '',
        provider_identifier_type: assignment?.identifier_type ?? 'TICKER',
        provider_params: safeScalar(assignment?.provider_params),
        provider_user_url: safeString(asset.user_url) ?? '',
        provider_url: safeString(assignment?.provider_url),
    };
}
