export function matchesAssetLifecycle(active: boolean, showActive: boolean, showInactive: boolean): boolean {
    if (showActive === showInactive) return true;
    return active ? showActive : showInactive;
}

export function orderAssetsByLifecycle<T extends {active: boolean}>(assets: readonly T[]): T[] {
    return assets
        .map((asset, index) => ({asset, index}))
        .sort((left, right) => Number(right.asset.active) - Number(left.asset.active) || left.index - right.index)
        .map(({asset}) => asset);
}
