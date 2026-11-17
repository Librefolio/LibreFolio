/**
 * Currency Graph — MultiDirectedGraph for FX conversion chain path-finding.
 *
 * Builds a directed graph where:
 * - Nodes = all ISO currency codes
 * - Edges = provider relationships (base → target, one per provider)
 *
 * Uses DFS with backtracking to find all possible conversion paths
 * between two currencies, producing only **simple paths** (no repeated nodes):
 * - No node visited twice in a path (eliminates all cycles)
 * - Max 2 uses per provider per path
 *
 * The output ChainStep[] can be sent directly as chain_steps to the backend.
 *
 * @module utils/currencyGraph
 */

// The named export (X-R75): graphology's default export is the simple Graph, which refuses a second edge between two
// currencies in the same direction, so two providers covering it made the whole route picker fail.
import {MultiDirectedGraph} from 'graphology';

// ============================================================================
// TYPES
// ============================================================================

/** Single step in a conversion chain (matches backend FXRouteStep). */
export interface ChainStep {
    from: string;
    to: string;
    provider: string;
}

/** Provider info needed for graph construction and UI display (from GET /fx/providers). */
export interface ProviderInfo {
    code: string;
    name: string;
    base_currency: string;
    base_currencies: string[];
    target_currencies: string[];
    /** True when `target_currencies` is empty because the list could not be fetched (not because the provider covers nothing). */
    currencies_unavailable?: boolean;
    /** Provider icon URL (for UI display) */
    icon_url?: string | null;
    /** Provider description (for UI display) */
    description?: string;
    /** Multilingual provider descriptions {lang_code: description} */
    description_i18n?: Record<string, string>;
    /** Multilingual provider warnings/caveats {lang_code: warning}. Empty = no warning. */
    warning_i18n?: Record<string, string>;
    /** How serious `warning_i18n` is: 'warning' (⚠️, a data limit that can mislead) or 'info' (ℹ️, a fact worth knowing). */
    warning_level?: 'info' | 'warning';
    /** URL to documentation page for this provider */
    docs_url?: string | null;
    /** False when a required setting has no value for the caller (plan 76, N1): every call would answer NOT_CONFIGURED. */
    configured?: boolean;
    /** The settings to set, `<group>.<field>` for a shared group's (N1). */
    missing_settings?: string[];
    /** Why it is not configured (N2b): `missing_fields` or `invalid_locked_setting`; null when configured. */
    missing_reason?: string | null;
    /** The environment variables with an invalid value, outside the managed profile (N2b). */
    invalid_variables?: string[];
}

/** Edge attributes stored in the graphology graph. */
export interface EdgeAttributes {
    provider: string;
}

// ============================================================================
// GRAPH CONSTRUCTION
// ============================================================================

/**
 * Build a MultiDirectedGraph from provider capabilities.
 *
 * Nodes: ALL currency codes from allCurrencyCodes (from GET /utilities/currencies).
 *        Most will be disconnected — findAllPaths returns [] for unreachable pairs.
 *
 * Edges: For each provider P, for each (base B, target T):
 *   - ONE directed edge B→T with attribute {provider: P.code}
 *   - Direction encodes the provider's native direction
 *   - The DFS can traverse edges in reverse (forEachInboundEdge)
 *   - NO bidirectional edges — bidirectionality handled by DFS exploration
 *
 * MANUAL provider is excluded (sentinel, not a real data source).
 */
export function buildCurrencyGraph(providers: ProviderInfo[], allCurrencyCodes: string[]): MultiDirectedGraph<Record<string, never>, EdgeAttributes> {
    const graph = new MultiDirectedGraph<Record<string, never>, EdgeAttributes>();

    // Add all currency codes as nodes
    for (const code of allCurrencyCodes) {
        if (!graph.hasNode(code)) {
            graph.addNode(code);
        }
    }

    // Add edges from provider capabilities
    for (const provider of providers) {
        // Skip MANUAL sentinel
        if (provider.code === 'MANUAL') continue;

        for (const base of provider.base_currencies) {
            // Ensure base node exists (might not be in allCurrencyCodes if backend has extra currencies)
            if (!graph.hasNode(base)) {
                graph.addNode(base);
            }

            for (const target of provider.target_currencies) {
                // Skip self-loops
                if (base === target) continue;

                // Ensure target node exists
                if (!graph.hasNode(target)) {
                    graph.addNode(target);
                }

                // Add directed edge base→target with provider attribution
                graph.addDirectedEdge(base, target, {provider: provider.code});
            }
        }
    }

    return graph;
}

// ============================================================================
// DFS PATH-FINDING
// ============================================================================

/**
 * Find all conversion paths between two currencies using DFS with backtracking.
 *
 * Explores the graph in both directions at each node:
 * - Outbound edges (native direction: currentNode is edge source)
 * - Inbound edges (reverse direction: currentNode is edge target)
 *
 * The ChainStep records the LOGICAL conversion direction:
 *   { from: currentNode, to: neighbor, provider }
 * The backend determines whether to invert the rate using alphabetical
 * normalization in compute_chain_rate().
 *
 * Each ChainStep[] output can be sent directly as chain_steps in
 * POST /fx/providers/routes — no transformation needed.
 *
 * Produces only **simple paths** — no node is visited twice in a path.
 * This eliminates redundant cycles (e.g. EUR→USD→GBP→EUR→RON where
 * the round-trip EUR→USD→GBP→EUR is pointless) and guarantees each
 * conversion chain is unique and optimal.
 *
 * @param graph - MultiDirectedGraph built by buildCurrencyGraph
 * @param source - Source currency code (e.g. "RON")
 * @param target - Target currency code (e.g. "USD")
 * @param maxDepth - Maximum chain length (default 4)
 * @returns Array of paths, sorted by length (shortest first).
 *          Each path is a ChainStep[] ready for chain_steps.
 */
export function findAllPaths(graph: MultiDirectedGraph<Record<string, never>, EdgeAttributes>, source: string, target: string, maxDepth: number = 4): ChainStep[][] {
    const validPaths: ChainStep[][] = [];

    // If source or target don't exist in the graph, no paths possible
    if (!graph.hasNode(source) || !graph.hasNode(target)) return [];

    // Same currency — no conversion needed
    if (source === target) return [];

    // Steps from each node to the target, ignoring direction, simple paths and provider uses: a lower bound of what any
    // valid path needs, so cutting a branch that cannot reach the target within the steps left never drops a path
    // (lane 75, L2b: with ~180 currencies an unpruned depth-4 walk took 130-200 ms for a pair with one chain).
    const stepsToTarget = distancesTo(graph, target, maxDepth);

    // Each node's moves, outbound edges first then inbound ones, in the graph's order, keeping only the neighbors that
    // can still reach the target: built once per node per call (graphology's edge iterators are slow in a hot loop).
    const movesOf = new Map<string, [neighbor: string, provider: string][]>();
    function moves(node: string): [string, string][] {
        let list = movesOf.get(node);
        if (list === undefined) {
            list = [];
            const into = list;
            // Outbound edges: the NATIVE direction, node → neighbor
            graph.forEachOutboundEdge(node, (_edgeKey, attrs, _src, tgt) => {
                if (stepsToTarget.has(tgt)) into.push([tgt, attrs.provider]);
            });
            // Inbound edges: the edge is src → node, traversed backwards (node ← src)
            graph.forEachInboundEdge(node, (_edgeKey, attrs, src) => {
                if (stepsToTarget.has(src)) into.push([src, attrs.provider]);
            });
            movesOf.set(node, list);
        }
        return list;
    }

    /**
     * DFS with backtracking.
     *
     * @param currentNode - Current currency in the path
     * @param pathEdges - ChainSteps accumulated so far
     * @param visitedNodes - Nodes already in the current path (prevents cycles)
     * @param providerUseCount - Map<provider, count> uses in current path
     */
    function dfs(currentNode: string, pathEdges: ChainStep[], visitedNodes: Set<string>, providerUseCount: Map<string, number>): void {
        // Reached the target — record this path
        if (currentNode === target) {
            validPaths.push([...pathEdges]);
            return;
        }

        // Max depth reached
        if (pathEdges.length >= maxDepth) return;

        for (const [neighbor, provider] of moves(currentNode)) {
            // Constraint 1: simple paths only — no revisiting nodes already in the path
            // (target is allowed as the exit condition, it's not in visitedNodes)
            if (visitedNodes.has(neighbor)) continue;

            // Pruning: the target is out of reach from this neighbor in the steps left
            if (pathEdges.length + 1 + stepsToTarget.get(neighbor)! > maxDepth) continue;

            // Constraint 2: max 2 uses per provider per path
            const currentUses = providerUseCount.get(provider) ?? 0;
            if (currentUses >= 2) continue;

            // --- ADVANCE ---
            pathEdges.push({from: currentNode, to: neighbor, provider});
            visitedNodes.add(neighbor);
            providerUseCount.set(provider, currentUses + 1);

            // RECURSE — explore from neighbor
            dfs(neighbor, pathEdges, visitedNodes, providerUseCount);

            // --- BACKTRACK ---
            pathEdges.pop();
            visitedNodes.delete(neighbor);
            if (currentUses === 0) {
                providerUseCount.delete(provider);
            } else {
                providerUseCount.set(provider, currentUses);
            }
        }
    }

    // Start DFS from source — mark source as visited (can't return to it)
    dfs(source, [], new Set([source]), new Map());

    // Sort by path length (shortest first)
    validPaths.sort((a, b) => a.length - b.length);
    return validPaths;
}

/**
 * Steps from every node within `maxDepth` of `target` to `target`, edges taken in both directions (a BFS from the
 * target). A node missing from the map cannot reach the target in `maxDepth` steps.
 */
function distancesTo(graph: MultiDirectedGraph<Record<string, never>, EdgeAttributes>, target: string, maxDepth: number): Map<string, number> {
    const steps = new Map<string, number>([[target, 0]]);
    let frontier = [target];
    for (let depth = 1; depth <= maxDepth && frontier.length > 0; depth++) {
        const next: string[] = [];
        for (const node of frontier) {
            graph.forEachNeighbor(node, (neighbor) => {
                if (!steps.has(neighbor)) {
                    steps.set(neighbor, depth);
                    next.push(neighbor);
                }
            });
        }
        frontier = next;
    }
    return steps;
}

// Measured (lane 75, L2b, synthetic catalogue of ~180 currencies after wave 1): the DFS above runs in a few ms per
// pair, so no Web Worker. The route picker's own rendering of thousands of chains is a separate matter.
