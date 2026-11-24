/**
 * providerAttribution — which attribution lines a list of providers owes (project 76, P4 and TL42).
 *
 * A provider's terms may ask for a line crediting it (CoinGecko: «Powered by CoinGecko», linked to its site;
 * `GET /assets/provider` → `attribution`). The line lives on the provider's own card in Settings › Plugins, never on
 * the screens that show its prices (TL42). One line per such provider among the codes given, never one per repeat.
 *
 * @module features/assets/providerAttribution
 */

/** A provider's attribution, as the provider list gives it. */
export interface ProviderAttribution {
    text: string;
    url: string;
}

/** One line owed: the provider and its attribution. */
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
