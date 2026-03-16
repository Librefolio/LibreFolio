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

import MultiDirectedGraph from 'graphology';

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
    /** Provider icon URL (for UI display) */
    icon_url?: string | null;
    /** Provider description (for UI display) */
    description?: string;
    /** Multilingual provider descriptions {lang_code: description} */
    description_i18n?: Record<string, string>;
    /** Multilingual provider warnings/caveats {lang_code: warning}. Empty = no warning. */
    warning_i18n?: Record<string, string>;
    /** URL to documentation page for this provider */
    docs_url?: string | null;
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
export function buildCurrencyGraph(
    providers: ProviderInfo[],
    allCurrencyCodes: string[],
): MultiDirectedGraph<Record<string, never>, EdgeAttributes> {
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
                graph.addDirectedEdge(base, target, { provider: provider.code });
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
export function findAllPaths(
    graph: MultiDirectedGraph<Record<string, never>, EdgeAttributes>,
    source: string,
    target: string,
    maxDepth: number = 4,
): ChainStep[][] {
    const validPaths: ChainStep[][] = [];

    // If source or target don't exist in the graph, no paths possible
    if (!graph.hasNode(source) || !graph.hasNode(target)) return [];

    // Same currency — no conversion needed
    if (source === target) return [];

    /**
     * DFS with backtracking.
     *
     * @param currentNode - Current currency in the path
     * @param pathEdges - ChainSteps accumulated so far
     * @param visitedNodes - Nodes already in the current path (prevents cycles)
     * @param providerUseCount - Map<provider, count> uses in current path
     */
    function dfs(
        currentNode: string,
        pathEdges: ChainStep[],
        visitedNodes: Set<string>,
        providerUseCount: Map<string, number>,
    ): void {
        // Reached the target — record this path
        if (currentNode === target) {
            validPaths.push([...pathEdges]);
            return;
        }

        // Max depth reached
        if (pathEdges.length >= maxDepth) return;

        /**
         * Try advancing to a neighbor node via an edge.
         * Used for both outbound (native) and inbound (reverse) edges.
         */
        function tryEdge(neighbor: string, provider: string): void {
            // Constraint 1: simple paths only — no revisiting nodes already in the path
            // (target is allowed as the exit condition, it's not in visitedNodes)
            if (visitedNodes.has(neighbor)) return;

            // Constraint 2: max 2 uses per provider per path
            const currentUses = providerUseCount.get(provider) ?? 0;
            if (currentUses >= 2) return;

            // --- ADVANCE ---
            pathEdges.push({ from: currentNode, to: neighbor, provider });
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

        // ── Outbound edges (NATIVE direction: currentNode → neighbor) ──
        graph.forEachOutboundEdge(currentNode, (_edgeKey, attrs, _src, tgt) => {
            tryEdge(tgt, attrs.provider);
        });

        // ── Inbound edges (REVERSE direction: currentNode ← source) ──
        // The edge in the graph is src→currentNode, but we traverse it backwards.
        graph.forEachInboundEdge(currentNode, (_edgeKey, attrs, src, _tgt) => {
            // src = edge origin (e.g. EUR), tgt = currentNode (e.g. USD)
            // neighbor = src (going towards EUR)
            tryEdge(src, attrs.provider);
        });
    }

    // Start DFS from source — mark source as visited (can't return to it)
    dfs(source, [], new Set([source]), new Map());

    // Sort by path length (shortest first)
    validPaths.sort((a, b) => a.length - b.length);
    return validPaths;
}

// TODO: Web Worker parallelization — profile first, implement only if needed.
// With ~4 providers × ~25 currencies, DFS completes in <1ms.

