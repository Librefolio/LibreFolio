/**
 * providerInputTypes — how the interface names a provider's input type, and its example (project 76, P3).
 *
 * TICKER, ISIN and URL read the same in every language and are shown as they are; a code with an underscore reads with
 * a space (AUTO GENERATED). PROVIDER_ID, a provider's own code for the asset (CoinGecko's «bitcoin»), has a translated
 * label and example. One place for the assignment section and the asset detail.
 *
 * @module features/assets/providerInputTypes
 */

type Translate = (key: string) => string;

/** The label of an input type: PROVIDER_ID translated, the others as their code. */
export function providerInputTypeLabel(type: string, t: Translate): string {
    if (type === 'PROVIDER_ID') return t('assets.provider.inputType.PROVIDER_ID');
    return type.replace(/_/g, ' ');
}

/** The example the identifier field shows for an input type. */
export function providerInputTypePlaceholder(type: string, t: Translate): string {
    switch (type) {
        case 'PROVIDER_ID':
            return t('assets.provider.inputTypePlaceholder.PROVIDER_ID');
        case 'URL':
            return 'https://example.com/price';
        case 'ISIN':
            return 'IE00B4L5Y983';
        case 'TICKER':
            return 'AAPL, MSFT…';
        default:
            return 'AAPL, IE00B4L5Y983, https://...';
    }
}
