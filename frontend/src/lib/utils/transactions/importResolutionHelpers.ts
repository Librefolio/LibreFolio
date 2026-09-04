/**
 * Pure helpers for the import wizard's asset-resolution cards (Step 3 "assets").
 *
 * Extracted verbatim from `ImportWizardModal.svelte` so every branch can be exercised
 * directly instead of only through the seven-step wizard. Each function reads its
 * arguments and returns a fresh value; the one lookup that needs the asset store
 * (`resolutionLabel`) takes it as an injected callback so the module stays pure.
 */
import type {AssetResolution} from './importTypes';

/**
 * Every distinct, non-blank name the group knows for an instrument: the archive's own
 * names first, then the raw extraction, then each candidate's name. Deduplicated, blanks
 * and whitespace-only entries dropped — a name that identified the instrument in *any*
 * file must survive.
 */
export function createNamesFor(res: AssetResolution | undefined): string[] {
    return res ? [...new Set([...res.groupNames, res.extractedName, ...(res.candidates ?? []).map((c) => c.name)].filter((n): n is string => !!n && n.trim() !== ''))] : [];
}

/** Everything the group knows that is not the elected primary, ready for `identifier_other`. */
export function createOtherFor(res: AssetResolution | undefined, primaryIsin: string | null, primarySymbol: string | null): string[] {
    if (!res) return [];
    const norm = (v: string) => v.trim().toUpperCase();
    const rest = [...res.groupIsins.filter((v) => norm(v) !== norm(primaryIsin ?? '')), ...res.groupSymbols.filter((v) => norm(v) !== norm(primarySymbol ?? ''))];
    return [...new Set([...createNamesFor(res), ...rest])];
}

/**
 * The exact/high-confidence candidates, but only when at least two exist. Two
 * identifier-grade candidates for one extracted security almost always means the database
 * holds the same instrument twice; name matches are deliberately excluded upstream.
 */
export function duplicateCandidates(res: AssetResolution): AssetResolution['candidates'] {
    const strong = res.candidates.filter((c) => c.match_confidence.toLowerCase() === 'exact' || c.match_confidence.toLowerCase() === 'high');
    return strong.length >= 2 ? strong : [];
}

/**
 * The label shown on a resolution card. When the fake id is bound to a real asset, the
 * database's own name wins (looked up via the injected `dbDisplayName`), falling back to
 * the matched candidate's name; otherwise the elected/typed group name, then the raw
 * extraction, then the fake id.
 *
 * `dbDisplayName` returns the stored display name for a resolved asset id, or null/undefined
 * when the store does not (yet) know it — in the component it wraps `getAssetInfo`.
 */
export function resolutionLabel(res: AssetResolution, dbDisplayName: (assetId: number) => string | null | undefined): string {
    if (res.resolvedAssetId !== null) {
        const dbName = dbDisplayName(res.resolvedAssetId) ?? res.candidates.find((c) => c.asset_id === res.resolvedAssetId)?.name;
        if (dbName && dbName.trim() !== '') return dbName;
    }
    return res.groupNames[0] || res.extractedName || res.extractedSymbol || res.extractedIsin || `#${res.fakeAssetId}`;
}
