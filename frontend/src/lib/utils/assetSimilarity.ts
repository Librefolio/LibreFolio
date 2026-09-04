/**
 * assetSimilarity.ts — Decide whether two extracted assets are the *same security*.
 *
 * ## Why this exists
 *
 * A multi-file import can describe one security in several inconsistent ways:
 *
 * - the same broker uses two report layouts, one carrying the ISIN and one not
 *   (Crédit Agricole's *Deposito Titoli* vs *Movimenti Conto*);
 * - an Italian retail government bond (BTP Valore / BTP Più / BTP Italia) is issued
 *   under a non-tradeable "CUM" ISIN and traded under a different, quoted one. Both
 *   describe one asset in LibreFolio — the CUM code lives in `identifier_other`.
 *
 * Without unification each variant reaches the review step as a separate asset to be
 * resolved independently, which is how duplicates get created.
 *
 * ## The discriminator
 *
 * The naive approach — plain string similarity on the name — is actively dangerous for
 * bonds, because `BTP 1/3/32` and `BTP 1/3/35` are ~97% similar and are *different
 * securities*. The rule that works:
 *
 * - **numeric** tokens (maturity dates, coupon rates, series numbers) *identify* a bond →
 *   any difference is a **strong negative** signal, never propose a merge;
 * - **trailing alphabetic** tokens (`CUM`, `EX`, `ACC`, `DIST`, share classes) describe a
 *   *phase or class* of the same instrument → differences there are neutral.
 *
 * Treating both the same way is the mistake to avoid.
 *
 * ## Output contract
 *
 * Signals are graded, never silently applied:
 * - `strong` → the group is formed automatically (solid border in the UI);
 * - `weak` → the group is *proposed*, the user confirms or splits (dashed border);
 * - `none` / `negative` → the items stay separate.
 *
 * Pure module, no Svelte and no I/O, so it is unit-testable in isolation.
 *
 * @module utils/assetSimilarity
 */

// ============================================================================
// TYPES
// ============================================================================

/** Minimal shape needed to compare two assets extracted from import files. */
export interface SimilarityInput {
    /** Stable key of the extracted asset (the wizard's fake asset id). */
    key: number;
    /** File the extracted asset came from. */
    fileId?: string;
    name?: string | null;
    isin?: string | null;
    symbol?: string | null;
}

/** Why two extracted assets were linked. */
export type LinkReason = 'isin' | 'ticker' | 'name' | 'nameSuffix' | 'nameNoIsin';

/** How much the evidence is worth. */
export type LinkStrength = 'strong' | 'weak' | 'none' | 'negative';

/** A directed-but-symmetric edge between two extracted assets. */
export interface SimilarityLink {
    from: number;
    to: number;
    reason: LinkReason;
    strength: LinkStrength;
    /** Name similarity in [0, 1]; 1 for identifier-based links. */
    score: number;
}

/** A set of extracted assets believed to be one security. */
export interface SimilarityGroup {
    groupId: string;
    members: number[];
    /** `confirmed` = strong evidence, `proposed` = weak evidence, `single` = alone. */
    state: 'confirmed' | 'proposed' | 'single';
    links: SimilarityLink[];
}

// ============================================================================
// NORMALIZATION
// ============================================================================

/**
 * Two names differ *marginally* when what separates them is small enough to be a phase or
 * class marker rather than a different instrument — `CUM`, `EX`, `ACC`, a share-class letter.
 *
 * There is deliberately **no lexicon**. A hardcoded list of "neutral" words only recognises
 * the markers someone thought of, silently rejects every other convention, and turns a
 * general rule into a private dictionary that has to be maintained. The judgement is
 * structural instead: by the time this flag is consulted the numeric guard has already run,
 * so every date, coupon and maturity is known to match — and a couple of short alphabetic
 * tokens on top of an otherwise identical name are not enough to claim two different
 * securities. Not enough to *merge* either: this only ever produces a **proposal**.
 */
const MINOR_TOKEN_MAX_LENGTH = 4;
const MINOR_TOKEN_MAX_COUNT = 2;

/** Corporate/legal noise that carries no identifying power. */
const STOPWORD_TOKENS = new Set(['SPA', 'S', 'P', 'A', 'SRL', 'NV', 'SA', 'AG', 'PLC', 'INC', 'CORP', 'LTD', 'THE', 'DI', 'DE', 'DEL', 'DELLA']);

/**
 * Strip accents, punctuation and case, then collapse whitespace.
 *
 * Punctuation inside numeric groups matters (`1/3/32` must not become `1 3 32`, or the
 * date would shatter into three weak tokens), so separators between digits are kept and
 * canonicalised to `-`. The trailing digit is matched with a lookahead rather than
 * consumed, otherwise the global regex would skip past it and only the first separator
 * of a three-part date would be rewritten.
 */
export function normalizeAssetName(raw: string | null | undefined): string {
    if (!raw) return '';
    return raw
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase()
        .replace(/(\d)\s*[/.,\-]\s*(?=\d)/g, '$1-')
        .replace(/[^A-Z0-9%\-\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

/** A token is "numeric" when it carries any digit — dates, rates, series numbers. */
function isNumericToken(token: string): boolean {
    return /\d/.test(token);
}

/** Split a normalized name into tokens, dropping legal-form noise. */
export function tokenizeAssetName(normalized: string): string[] {
    if (!normalized) return [];
    return normalized.split(' ').filter((tk) => tk.length > 0 && !(STOPWORD_TOKENS.has(tk) && !isNumericToken(tk)));
}

/** Uppercase + trim an identifier; empty strings collapse to null. */
function normalizeIdentifier(raw: string | null | undefined): string | null {
    const v = (raw ?? '').trim().toUpperCase();
    return v === '' ? null : v;
}

// ============================================================================
// NAME COMPARISON
// ============================================================================

/** Outcome of a token-aware name comparison. */
export interface NameComparison {
    /** Jaccard-style overlap in [0, 1] computed over identifying tokens. */
    score: number;
    /** True when the two names disagree on at least one numeric token. */
    numericMismatch: boolean;
    /**
     * True when the names differ only by a couple of short alphabetic tokens — the shape of a
     * phase or class marker (`CUM`, `EX`, `ACC`) rather than of a different instrument.
     */
    onlyMinorTokenDiff: boolean;
}

/**
 * Compare two asset names token by token.
 *
 * The numeric check runs on the *full* numeric token sets: a maturity or coupon present
 * on one side and absent on the other is just as disqualifying as two different values,
 * because it means one name pins down something the other contradicts or omits.
 */
export function compareAssetNames(a: string | null | undefined, b: string | null | undefined): NameComparison {
    const tokensA = tokenizeAssetName(normalizeAssetName(a));
    const tokensB = tokenizeAssetName(normalizeAssetName(b));
    if (tokensA.length === 0 || tokensB.length === 0) {
        return {score: 0, numericMismatch: false, onlyMinorTokenDiff: false};
    }

    const setA = new Set(tokensA);
    const setB = new Set(tokensB);

    const numericA = [...setA].filter(isNumericToken).sort();
    const numericB = [...setB].filter(isNumericToken).sort();
    const numericMismatch = numericA.length !== numericB.length || numericA.some((tk, i) => tk !== numericB[i]);

    let shared = 0;
    for (const tk of setA) if (setB.has(tk)) shared += 1;
    const union = new Set([...setA, ...setB]).size;
    const score = union === 0 ? 0 : shared / union;

    // Everything present on one side but not the other. The non-numeric guard is explicit
    // rather than inherited from the caller: this flag is exported, so it must hold on its own.
    const diff = [...new Set([...setA, ...setB])].filter((tk) => !setA.has(tk) || !setB.has(tk));
    const onlyMinorTokenDiff = diff.length > 0 && diff.length <= MINOR_TOKEN_MAX_COUNT && diff.every((tk) => !isNumericToken(tk) && tk.length <= MINOR_TOKEN_MAX_LENGTH) && shared > 0;

    return {score, numericMismatch, onlyMinorTokenDiff};
}

// ============================================================================
// PAIRWISE EVIDENCE
// ============================================================================

/** Names must overlap this much before a merge is even proposed. */
const WEAK_NAME_THRESHOLD = 0.6;
/** Above this, two names are treated as the same label. */
const STRONG_NAME_THRESHOLD = 0.999;

/**
 * Weigh the evidence that two extracted assets are the same security.
 *
 * Returns `null` when there is no link at all — including the explicitly *negative*
 * case of two different ISINs whose names disagree on a numeric token.
 */
export function compareAssets(a: SimilarityInput, b: SimilarityInput): SimilarityLink | null {
    const isinA = normalizeIdentifier(a.isin);
    const isinB = normalizeIdentifier(b.isin);
    const symA = normalizeIdentifier(a.symbol);
    const symB = normalizeIdentifier(b.symbol);

    const link = (reason: LinkReason, strength: LinkStrength, score: number): SimilarityLink => ({from: a.key, to: b.key, reason, strength, score});

    // Strong: the same hard identifier on both sides.
    if (isinA && isinB && isinA === isinB) return link('isin', 'strong', 1);
    if (symA && symB && symA === symB) return link('ticker', 'strong', 1);

    const cmp = compareAssetNames(a.name, b.name);

    // Strong: identical normalized names and no contradicting ISIN.
    if (cmp.score >= STRONG_NAME_THRESHOLD && !(isinA && isinB && isinA !== isinB)) {
        return link('name', 'strong', cmp.score);
    }

    // Hard negative: different bonds. A maturity or coupon mismatch is decisive — it is
    // exactly what tells `BTP 1/3/32` from `BTP 1/3/35`, no matter how similar they look.
    if (cmp.numericMismatch) return null;

    if (cmp.score < WEAK_NAME_THRESHOLD && !cmp.onlyMinorTokenDiff) return null;

    // Weak: two different ISINs but the names differ only marginally.
    // This is the BTP "CUM" ↔ market pair — propose, never decide.
    if (isinA && isinB && isinA !== isinB) {
        return cmp.onlyMinorTokenDiff ? link('nameSuffix', 'weak', cmp.score) : null;
    }

    // Weak: one side has no ISIN at all and the names are close — the two-layout case,
    // where the same holding appears with and without its code.
    if (!isinA || !isinB) return link('nameNoIsin', 'weak', cmp.score);

    return null;
}

// ============================================================================
// GROUPING
// ============================================================================

/**
 * Cluster extracted assets into groups via union-find over the pairwise links.
 *
 * Only `strong` links merge on their own. `weak` links merge too — but they mark the
 * resulting group `proposed`, so the UI asks for confirmation instead of assuming.
 * Leaving weakly-correlated items visually separate was rejected on purpose: free-floating
 * arcs across a list produce crossing spaghetti, whereas a dashed box keeps every arc
 * *inside* the box it belongs to.
 */
export function buildAssetGroups(items: SimilarityInput[]): SimilarityGroup[] {
    const parent = new Map<number, number>();
    const find = (x: number): number => {
        let root = x;
        while (parent.get(root) !== root) root = parent.get(root)!;
        // Path compression.
        let cur = x;
        while (parent.get(cur) !== root) {
            const next = parent.get(cur)!;
            parent.set(cur, root);
            cur = next;
        }
        return root;
    };
    const union = (x: number, y: number): void => {
        const rx = find(x);
        const ry = find(y);
        if (rx !== ry) parent.set(ry, rx);
    };

    for (const it of items) parent.set(it.key, it.key);

    const links: SimilarityLink[] = [];
    for (let i = 0; i < items.length; i += 1) {
        for (let j = i + 1; j < items.length; j += 1) {
            const l = compareAssets(items[i], items[j]);
            if (!l) continue;
            links.push(l);
            union(l.from, l.to);
        }
    }

    const byRoot = new Map<number, SimilarityInput[]>();
    for (const it of items) {
        const root = find(it.key);
        const bucket = byRoot.get(root);
        if (bucket) bucket.push(it);
        else byRoot.set(root, [it]);
    }

    const groups: SimilarityGroup[] = [];
    for (const [root, members] of byRoot) {
        const memberKeys = new Set(members.map((m) => m.key));
        const groupLinks = links.filter((l) => memberKeys.has(l.from) && memberKeys.has(l.to));
        let state: SimilarityGroup['state'];
        if (members.length === 1) state = 'single';
        else if (groupLinks.every((l) => l.strength === 'strong')) state = 'confirmed';
        else state = 'proposed';
        groups.push({
            groupId: `grp-${root}`,
            // Keep the caller's original ordering so the UI is stable across recomputes.
            members: items.filter((it) => memberKeys.has(it.key)).map((it) => it.key),
            state,
            links: groupLinks,
        });
    }

    // Groups first (most actionable), singles last; stable within each bucket.
    return groups.sort((x, y) => {
        const rank = (g: SimilarityGroup): number => (g.state === 'proposed' ? 0 : g.state === 'confirmed' ? 1 : 2);
        return rank(x) - rank(y);
    });
}
