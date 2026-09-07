/**
 * assetGrouping.ts — turn the per-file extracted assets of an import into **one entry per
 * security**, and keep the user's edits to that partition alive across recomputations.
 *
 * ## The problem this solves
 *
 * The wizard allocates one fake asset id per instrument *per file*. Two Crédit Agricole layouts
 * describing the same BTP therefore arrive as two independent assets to resolve, and the review
 * step happily creates two duplicates out of them. Worse, the correction step lists them as two
 * indistinguishable entries in its asset picker, so a tax row gets attached to half the
 * instrument with no visible sign of the mistake.
 *
 * Unification has to happen *before* anything else looks at assets — before the corrections and
 * long before the database comparison — because every later choice is made *on* the resulting
 * list.
 *
 * ## Two stages, and this is the first
 *
 * Here the contest is between the codes *the files themselves* brought: one BTP read from two
 * reports arrives with its placement ISIN and its quoted one, and only the quoted one can be
 * priced. Electing the leader is therefore part of saying "these rows are the same security",
 * not a separate errand — so it happens on this step, and the group carries the union with the
 * elected value in front.
 *
 * The second stage is a different contest: the group meets an asset that *already exists* in the
 * database and has identifiers of its own to defend. That one belongs to the identifier prompt,
 * which knows the difference between a code the asset is missing and one that competes.
 *
 * ## Why the override is a whole partition
 *
 * The automatic grouping is recomputed from scratch every time the wizard re-merges the files, so
 * a user gesture cannot be stored as a delta against a partition that no longer exists. Once the
 * user touches the layout, their partition *is* the answer; the similarity engine keeps running
 * only to explain, in the UI, why it had proposed something else.
 *
 * Members are addressed by a content-derived key rather than by fake id, because fake ids are
 * reallocated on every re-merge.
 *
 * Pure module, no Svelte and no I/O.
 *
 * @module utils/assetGrouping
 */

import {buildAssetGroups, type SimilarityGroup, type SimilarityLink} from './assetSimilarity';

/** One asset as a single file described it. */
export interface ExtractedAsset {
    /** The wizard's globally-unique fake asset id for this file's instrument. */
    fakeAssetId: number;
    fileId: string;
    fileName: string;
    name: string | null;
    isin: string | null;
    symbol: string | null;
}

/** A set of extracted assets the user (or the engine) considers one security. */
export interface AssetGroup {
    groupId: string;
    members: ExtractedAsset[];
    /** `confirmed` = strong evidence or user decision · `proposed` = weak evidence · `single` = alone. */
    state: 'confirmed' | 'proposed' | 'single';
    /** Why the engine linked these members — kept for display even under an override. */
    links: SimilarityLink[];
    /** True when this group's shape comes from the user rather than from the engine. */
    userTouched: boolean;
}

/**
 * The user's partition, as clusters of member keys. `null` means "nobody has touched it, use the
 * engine's answer".
 */
export type GroupOverride = string[][] | null;

/**
 * Stable identity of an extracted asset, immune to fake-id reallocation.
 *
 * The file is part of the key on purpose: the same instrument read from two files is exactly what
 * grouping is *about*, so the two must stay addressable as distinct members.
 */
export function memberKey(asset: ExtractedAsset): string {
    return [asset.fileId, asset.isin ?? '', asset.symbol ?? '', asset.name ?? ''].map((part) => part.trim().toUpperCase()).join('\u0000');
}

/** Signature of a cluster, order-independent — used to recognise a group across recomputations. */
export function clusterSignature(keys: readonly string[]): string {
    return [...keys].sort().join('\u0001');
}

/**
 * Compute the automatic partition, then let any user override replace its shape.
 *
 * The engine's links survive the override so the UI can still explain the proposal the user
 * rejected — a dashed arc labelled "differs only by CUM" is worth more than a silent regrouping.
 */
export function groupExtractedAssets(assets: readonly ExtractedAsset[], override: GroupOverride = null, confirmedSignatures: ReadonlySet<string> = new Set()): AssetGroup[] {
    const byKey = new Map<number, ExtractedAsset>();
    for (const asset of assets) byKey.set(asset.fakeAssetId, asset);

    const auto = buildAssetGroups(assets.map((a) => ({key: a.fakeAssetId, fileId: a.fileId, name: a.name, isin: a.isin, symbol: a.symbol})));
    const allLinks = auto.flatMap((g) => g.links);

    const clusters = override ? clustersFromOverride(assets, override) : auto.map((g) => g.members.map((key) => byKey.get(key)).filter((m): m is ExtractedAsset => !!m));

    const groups: AssetGroup[] = [];
    for (const members of clusters) {
        if (members.length === 0) continue;
        const ids = new Set(members.map((m) => m.fakeAssetId));
        const links = allLinks.filter((l) => ids.has(l.from) && ids.has(l.to));
        const signature = clusterSignature(members.map(memberKey));
        groups.push({
            groupId: `grp-${Math.min(...ids)}`,
            members,
            state: resolveState(members.length, links, override !== null || confirmedSignatures.has(signature)),
            links,
            userTouched: override !== null,
        });
    }
    // Extraction order, never by size. Sorting by member count means every merge or split
    // reshuffles the whole page under the hand that caused it, and the user loses track of the
    // security they were working on. Position is taken from the input array rather than from the
    // fake id, whose direction is the caller's business.
    const rank = new Map(assets.map((a, i) => [a.fakeAssetId, i]));
    const firstSeen = (g: AssetGroup) => Math.min(...g.members.map((m) => rank.get(m.fakeAssetId) ?? Number.MAX_SAFE_INTEGER));
    groups.sort((a, b) => firstSeen(a) - firstSeen(b));
    return groups;
}

/**
 * A group is `proposed` only while the evidence is weak *and* nobody has ruled on it. A user
 * decision — or an explicit confirmation — settles it as firmly as an identical ISIN would.
 */
function resolveState(size: number, links: readonly SimilarityLink[], settled: boolean): AssetGroup['state'] {
    if (size <= 1) return 'single';
    if (settled) return 'confirmed';
    return links.length > 0 && links.every((l) => l.strength === 'strong') ? 'confirmed' : 'proposed';
}

/**
 * Rebuild clusters from a stored override.
 *
 * Members the override does not mention — a newly added file, typically — fall back to being
 * alone rather than being dropped: losing a security silently would be far worse than showing it
 * ungrouped.
 */
function clustersFromOverride(assets: readonly ExtractedAsset[], override: string[][]): ExtractedAsset[][] {
    const remaining = new Map<string, ExtractedAsset>();
    for (const asset of assets) remaining.set(memberKey(asset), asset);

    const clusters: ExtractedAsset[][] = [];
    for (const keys of override) {
        const cluster: ExtractedAsset[] = [];
        for (const key of keys) {
            const asset = remaining.get(key);
            if (!asset) continue;
            remaining.delete(key);
            cluster.push(asset);
        }
        if (cluster.length > 0) clusters.push(cluster);
    }
    for (const asset of remaining.values()) clusters.push([asset]);
    return clusters;
}

/** The current partition in override form, ready to be edited and stored. */
export function partitionOf(groups: readonly AssetGroup[]): string[][] {
    return groups.map((g) => g.members.map(memberKey));
}

/**
 * Move `keys` into the cluster that holds `targetKey`, or into a new cluster when `targetKey` is
 * null. Emptied clusters disappear; everything else keeps its place.
 */
export function movePartition(partition: readonly string[][], keys: readonly string[], targetKey: string | null): string[][] {
    const moving = new Set(keys);
    const stripped = partition.map((cluster) => cluster.filter((key) => !moving.has(key)));
    const ordered = [...keys];

    if (targetKey === null) {
        // Extracting: each key becomes its own cluster.
        return [...stripped, ...ordered.map((key) => [key])].filter((cluster) => cluster.length > 0);
    }

    const targetIndex = stripped.findIndex((cluster) => cluster.includes(targetKey));
    if (targetIndex === -1) return [...stripped, [targetKey, ...ordered]].filter((cluster) => cluster.length > 0);

    const next = stripped.map((cluster, i) => (i === targetIndex ? [...cluster, ...ordered.filter((key) => !cluster.includes(key))] : cluster));
    return next.filter((cluster) => cluster.length > 0);
}

/** Break a cluster apart: every member ends up alone. */
export function splitPartition(partition: readonly string[][], keys: readonly string[]): string[][] {
    return movePartition(partition, keys, null);
}

/**
 * The identifiers a group carries, unioned across its members and deduplicated
 * case-insensitively, in member order.
 *
 * Provenance order, not preference order: use `orderedIdentifiers` when the caller needs the
 * elected leader in front.
 */
export function groupIdentifiers(members: readonly ExtractedAsset[]): {isins: string[]; symbols: string[]; names: string[]} {
    const collect = (pick: (m: ExtractedAsset) => string | null): string[] => {
        const seen = new Set<string>();
        const out: string[] = [];
        for (const member of members) {
            const value = (pick(member) ?? '').trim();
            if (value === '') continue;
            const key = value.toUpperCase();
            if (seen.has(key)) continue;
            seen.add(key);
            out.push(value);
        }
        return out;
    };
    return {isins: collect((m) => m.isin), symbols: collect((m) => m.symbol), names: collect((m) => m.name)};
}

/**
 * The value the user promoted to lead its kind, per group. Absent kinds simply keep the
 * automatic order.
 */
export interface GroupPrimary {
    isin?: string;
    symbol?: string;
    name?: string;
}

/**
 * Elections keyed by cluster signature rather than by group id or fake id: both are recomputed on
 * every re-merge, the signature is derived from the members' content and therefore survives it —
 * as long as the group still holds the same members, which is exactly when the election still
 * means something.
 */
export type PrimaryMap = Record<string, GroupPrimary>;

export type IdentifierKind = 'isin' | 'symbol' | 'name';

/** The signature under which this group's election is stored. */
export function groupSignature(group: Pick<AssetGroup, 'members'>): string {
    return clusterSignature(group.members.map(memberKey));
}

/** Store one election, leaving the other kinds of the same group alone. */
export function electPrimary(map: PrimaryMap, signature: string, kind: IdentifierKind, value: string): PrimaryMap {
    return {...map, [signature]: {...(map[signature] ?? {}), [kind]: value}};
}

/** Whether `value` is the elected leader of its kind for this group. */
export function isPrimary(primary: GroupPrimary | undefined, kind: IdentifierKind, value: string): boolean {
    return (primary?.[kind] ?? '').trim().toUpperCase() === value.trim().toUpperCase();
}

/**
 * The group's identifiers with the elected value of each kind moved to the front.
 *
 * Reordering rather than flagging is deliberate: every consumer downstream already reads
 * `groupIsins[0]` as "the code to use", so the election reaches the creation form, the search
 * hints and the identifier prompt without any of them learning a new concept.
 *
 * An election naming a value the group no longer holds — the chip was extracted after the
 * choice — is simply inert, which is what makes stale entries harmless. A **name** is the one
 * exception: a value nobody extracted is a deliberate rename, and it leads the list.
 */
export function orderedIdentifiers(members: readonly ExtractedAsset[], primary: GroupPrimary | undefined): {isins: string[]; symbols: string[]; names: string[]} {
    const ids = groupIdentifiers(members);
    return {
        isins: leadWith(ids.isins, primary?.isin),
        symbols: leadWith(ids.symbols, primary?.symbol),
        names: leadWith(ids.names, primary?.name, true),
    };
}

function leadWith(values: readonly string[], elected: string | undefined, allowNew = false): string[] {
    if (!elected) return [...values];
    const target = elected.trim().toUpperCase();
    const index = values.findIndex((v) => v.trim().toUpperCase() === target);
    // A name the files never carried is a rename, and it has to reach the front or it would be
    // silently dropped. A *code* the files never carried would be an invention, so only names
    // are allowed in.
    if (index === -1) return allowNew && elected.trim() !== '' ? [elected, ...values] : [...values];
    if (index === 0) return [...values];
    return [values[index], ...values.slice(0, index), ...values.slice(index + 1)];
}

/** True when the user has actually ruled on this kind for this group. */
export function hasElection(primary: GroupPrimary | undefined, kind: IdentifierKind): boolean {
    return (primary?.[kind] ?? '').trim() !== '';
}

/** One reason the members of a group belong together, and how much of the group it accounts for. */
export interface LinkSummary {
    reason: SimilarityLink['reason'];
    /** The weakest evidence seen among the links sharing this reason. */
    score: number;
    /** Members touched by at least one link of this reason, in group order. */
    members: number[];
    /** This reason alone accounts for every member: there is nothing left to attribute. */
    coversAll: boolean;
}

/**
 * Collapse the pairwise links into one line per reason.
 *
 * Four files carrying the same ISIN produce six links, and printing them one by one gives six
 * copies of "same ISIN · 100%" — noise that hides the *one* line that differs, which is the only
 * one the user has to judge. Reasons that cover the whole group need no member list either: when
 * everything matches, naming the parties adds nothing.
 */
export function summariseLinks(group: Pick<AssetGroup, 'members' | 'links'>): LinkSummary[] {
    const order = new Map(group.members.map((m, i) => [m.fakeAssetId, i]));
    const byReason = new Map<SimilarityLink['reason'], {score: number; members: Set<number>}>();

    for (const link of group.links) {
        const entry = byReason.get(link.reason) ?? {score: 1, members: new Set<number>()};
        entry.score = Math.min(entry.score, link.score);
        entry.members.add(link.from);
        entry.members.add(link.to);
        byReason.set(link.reason, entry);
    }

    const summaries: LinkSummary[] = [...byReason.entries()].map(([reason, entry]) => ({
        reason,
        score: entry.score,
        members: [...entry.members].sort((a, b) => (order.get(a) ?? 0) - (order.get(b) ?? 0)),
        coversAll: entry.members.size === group.members.length,
    }));

    // The reason that explains the most comes first: it is the headline, the rest are exceptions.
    summaries.sort((a, b) => Number(b.coversAll) - Number(a.coversAll) || b.members.length - a.members.length);
    return summaries;
}

/**
 * Which member speaks for the group.
 *
 * The one carrying an ISIN wins, then the one carrying a ticker, then the first: a representative
 * without identifiers would make the group look unidentifiable in every list that shows only the
 * representative, even though a sibling knew the code all along.
 */
export function representativeOf(members: readonly ExtractedAsset[]): ExtractedAsset {
    return members.find((m) => (m.isin ?? '').trim() !== '') ?? members.find((m) => (m.symbol ?? '').trim() !== '') ?? members[0];
}

/**
 * Where every extracted asset ends up once the groups are folded: member fake id → the fake id
 * that survives.
 *
 * This map *is* the guarantee the unification step exists to give. Every list built from the
 * resolutions — the correction step's asset picker above all — shows one entry per value in its
 * image, so a total function onto the representatives is what makes "one entry per security"
 * true rather than merely likely. Representatives map to themselves, so callers can apply it
 * unconditionally.
 */
export function representativeMap(groups: readonly AssetGroup[]): Map<number, number> {
    const map = new Map<number, number>();
    for (const group of groups) {
        const lead = representativeOf(group.members);
        for (const member of group.members) map.set(member.fakeAssetId, lead.fakeAssetId);
    }
    return map;
}

/** Every group that still needs the user to rule on it. */
export function hasOpenProposals(groups: readonly AssetGroup[]): boolean {
    return groups.some((g) => g.state === 'proposed');
}

/**
 * Convenience for `SimilarityGroup` consumers that only need the raw engine output.
 * Exported so callers do not have to import two modules to reach one answer.
 */
export type {SimilarityGroup, SimilarityLink};
