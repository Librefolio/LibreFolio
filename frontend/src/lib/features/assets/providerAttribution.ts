/**
 * providerAttribution — which attribution lines a screen owes (project 76, P4).
 *
 * A provider's terms may ask the interface to show a line with its prices (CoinGecko: «Powered by CoinGecko», linked
 * to its site; `GET /assets/provider` → `attribution`). A screen owes one line per such provider among the assets it
 * shows: never one per row, none when no asset on screen is priced by such a provider.
 *
 * @module features/assets/providerAttribution
 */

/** A provider's attribution, as the provider list gives it. */
export interface ProviderAttribution {
    text: string;
    url: string;
}

/** One line a screen owes: the provider and its attribution. */
export interface AttributionLine extends ProviderAttribution {
    code: string;
}

/** The lines owed for the providers `codes` (the assets' `provider_code`, repeats allowed), in their first order. */
export function attributionsFor(codes: readonly (string | null | undefined)[], lookup: (code: string) => ProviderAttribution | null): AttributionLine[] {
    const lines: AttributionLine[] = [];
    const seen = new Set<string>();
    for (const code of codes) {
        if (!code || seen.has(code)) continue;
        seen.add(code);
        const attribution = lookup(code);
        if (attribution) lines.push({code, text: attribution.text, url: attribution.url});
    }
    return lines;
}
