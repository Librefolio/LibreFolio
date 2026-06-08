/** Matches backend FAKE_ASSET_ID_BASE logic (brim.py:41-49). */
const FAKE_ASSET_ID_BASE = 2 ** 31 - 1; // 2147483647

export function isFakeAssetId(id: number | null | undefined): boolean {
    if (id == null) return false;
    return id >= FAKE_ASSET_ID_BASE - 10000;
}
