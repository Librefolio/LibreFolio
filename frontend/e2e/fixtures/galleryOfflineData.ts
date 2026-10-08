/**
 * Gallery offline data — what the gallery answers in place of the calls that would reach a real price or
 * exchange-rate provider (the gallery-wide offline guard, `guardGalleryOffline` in galleryReportSets.ts).
 * Static: written from the repository — its code, its documentation, its committed audits — and from values observed
 * once, each with its source; nothing here is fetched when the gallery runs.
 */

// ---------------------------------------------------------------------------
// POST /api/v1/assets/prices/current — the Assets pages' live-price poll
// ---------------------------------------------------------------------------

/** One fixed current price, for the asset the populate names `displayName` (`FACurrentPriceItem` without its id and date). */
export interface OfflineCurrentPrice {
    displayName: string;
    /** A decimal, as the backend serialises `SafeDecimal`. */
    value: string;
    currency: string;
    /** The provider the real poll asks: what `FACurrentPriceItem.source` names for a provider quote. */
    source: string;
}

/**
 * The assets the populate seeds with a provider and no price history (populate_mock_data.py,
 * `populate_asset_provider_assignments`): their cards and table rows draw only what the live poll answers. The
 * values are the ones the real poll returned on the lane on 2026-10-08 at 12:49 UTC — what it wrote into the test
 * database then, under `provider:justetf`, `provider:css_scraper` and `provider:scheduled_investment`. The guard
 * dates them today, as the real poll dates a fresh quote.
 *
 * Every other asset is left out of the answer, which the pages read as "no live value": the seeded ones (Apple,
 * Microsoft, Tesla, Bitcoin, Ethereum, the two loans, the two indices) then show the last close of their seeded
 * series — the figure the real poll returns as `db:last_known` when the provider is unreachable — and the ones with
 * no price at all (NVIDIA, the KRW stock) show none.
 */
export const OFFLINE_CURRENT_PRICES: readonly OfflineCurrentPrice[] = [
    {displayName: 'Amundi Core MSCI World UCITS ETF Acc', value: '164.73', currency: 'EUR', source: 'provider:justetf'},
    {displayName: 'Amundi MSCI Semiconductors UCITS ETF Acc', value: '121.71', currency: 'EUR', source: 'provider:justetf'},
    {displayName: 'iShares Core MSCI World UCITS ETF USD (Acc)', value: '146.47', currency: 'USD', source: 'provider:justetf'},
    {displayName: 'BTP Più Sc Fb33 EUR', value: '94.40', currency: 'EUR', source: 'provider:css_scraper'},
    {displayName: 'Gold Spot Price', value: '4116.60', currency: 'USD', source: 'provider:css_scraper'},
    {displayName: 'BTP Italia 2028', value: '10956.03', currency: 'EUR', source: 'provider:scheduled_investment'},
];

// ---------------------------------------------------------------------------
// GET /api/v1/fx/providers — the exchange-rate provider catalogue
// ---------------------------------------------------------------------------

/** One provider as the catalogue lists it (`FXProviderInfo`, schemas/fx.py). */
export interface OfflineFxProvider {
    code: string;
    name: string;
    base_currency: string;
    base_currencies: string[];
    target_currencies: string[];
    description: string;
    description_i18n: Record<string, string>;
    warning_i18n: Record<string, string>;
    icon_url: string | null;
    docs_url: string | null;
}

/**
 * The catalogue as the backend builds it (api/v1/fx.py, `list_providers`): every installed provider but the hidden
 * MANUAL, MOCKFX and MOCKFX_FAIL, in registration order (the registry imports fx_providers/*.py sorted by file name),
 * each field read from the provider's class in backend/app/services/fx_providers/.
 *
 * Only `target_currencies` comes from a network call in the backend (`get_supported_currencies`). FED and BOE answer it
 * from a static map in their own code (`CURRENCY_SERIES`), reproduced here whole. ECB and SNB load it live:
 *
 * - the SNB carries its live list as audited on 2026-08-05 — the call `snb.py` makes, `GET
 *   https://data.snb.ch/api/cube/devkum/dimensions/en`, mapped 25 currencies
 *   (LibreFolio_developer_journal/Release_2/phases/05_cleanAudit/mkdocsAudit/03_fx-market-data.md:157-160);
 * - the ECB carries the currencies its documentation page names (mkdocs_src/docs/user/fx/providers/ecb.en.md, "including:"
 *   — the page at its `docs_url`). The same audit counted 44 live (`data-api.ecb.europa.eu`) but recorded no list, and the
 *   repository holds none more complete: `ecb.py`'s own `test_currencies` is a subset of this one. So a subset of the live
 *   list, which every pair the gallery opens is covered by.
 *
 * Every list is sorted and holds the base currency, as `get_supported_currencies` returns it.
 */
export const OFFLINE_FX_PROVIDERS: readonly OfflineFxProvider[] = [
    {
        code: 'BOE',
        name: 'Bank of England',
        base_currency: 'GBP',
        base_currencies: ['GBP'],
        target_currencies: ['AUD', 'CAD', 'CHF', 'CNY', 'DKK', 'EUR', 'GBP', 'HKD', 'INR', 'JPY', 'NOK', 'NZD', 'SEK', 'SGD', 'USD', 'ZAR'],
        description: 'Official exchange rates from Bank of England',
        description_i18n: {
            en: 'Bank of England — publishes daily spot exchange rates for 20+ currencies against GBP. Updated each business day. One data point per day.',
            it: 'Bank of England — pubblica tassi di cambio spot giornalieri per 20+ valute contro GBP. Aggiornamento ogni giorno lavorativo. Un dato al giorno.',
            fr: "Banque d'Angleterre — publie des taux de change spot quotidiens pour 20+ devises contre GBP. Mise à jour chaque jour ouvrable. Un point par jour.",
            es: 'Banco de Inglaterra — publica tipos de cambio spot diarios para 20+ monedas contra GBP. Actualizado cada día hábil. Un dato por día.',
        },
        warning_i18n: {},
        icon_url: 'https://www.bankofengland.co.uk/favicon.svg?ver=2c06d',
        docs_url: '/mkdocs/user/fx/providers/boe/',
    },
    {
        code: 'ECB',
        name: 'European Central Bank',
        base_currency: 'EUR',
        base_currencies: ['EUR'],
        target_currencies: ['AUD', 'BGN', 'BRL', 'CAD', 'CHF', 'CNY', 'CZK', 'DKK', 'EUR', 'GBP', 'HKD', 'HUF', 'INR', 'JPY', 'KRW', 'MXN', 'NOK', 'NZD', 'PLN', 'RON', 'SEK', 'SGD', 'TRY', 'USD', 'ZAR'],
        description: 'Official exchange rates from European Central Bank',
        description_i18n: {
            en: 'European Central Bank — publishes daily reference exchange rates for 30+ currencies against EUR. Updated every business day around 16:00 CET. One data point per day.',
            it: 'Banca Centrale Europea — pubblica tassi di cambio di riferimento giornalieri per 30+ valute contro EUR. Aggiornamento ogni giorno lavorativo verso le 16:00 CET. Un dato al giorno.',
            fr: 'Banque Centrale Européenne — publie des taux de change de référence quotidiens pour 30+ devises contre EUR. Mise à jour chaque jour ouvrable vers 16h00 CET. Un point par jour.',
            es: 'Banco Central Europeo — publica tipos de cambio de referencia diarios para 30+ monedas contra EUR. Actualizado cada día hábil alrededor de las 16:00 CET. Un dato por día.',
        },
        warning_i18n: {},
        icon_url: 'https://www.ecb.europa.eu/favicon-32.png',
        docs_url: '/mkdocs/user/fx/providers/ecb/',
    },
    {
        code: 'FED',
        name: 'Federal Reserve Bank',
        base_currency: 'USD',
        base_currencies: ['USD'],
        target_currencies: ['AUD', 'BRL', 'CAD', 'CHF', 'CNY', 'DKK', 'EUR', 'GBP', 'HKD', 'INR', 'JPY', 'KRW', 'MXN', 'NOK', 'NZD', 'SEK', 'SGD', 'THB', 'TWD', 'USD', 'ZAR'],
        description: 'Official exchange rates from Federal Reserve (H.10 Release)',
        description_i18n: {
            en: 'Federal Reserve Bank (FRED) — publishes daily exchange rates from the H.10 Statistical Release for 20+ currencies against USD. Updated each business day. One data point per day.',
            it: 'Federal Reserve Bank (FRED) — pubblica tassi di cambio giornalieri dal bollettino statistico H.10 per 20+ valute contro USD. Aggiornamento ogni giorno lavorativo. Un dato al giorno.',
            fr: 'Federal Reserve Bank (FRED) — publie des taux de change quotidiens du bulletin statistique H.10 pour 20+ devises contre USD. Mise à jour chaque jour ouvrable. Un point par jour.',
            es: 'Federal Reserve Bank (FRED) — publica tipos de cambio diarios del boletín estadístico H.10 para 20+ monedas contra USD. Actualizado cada día hábil. Un dato por día.',
        },
        warning_i18n: {},
        icon_url: 'https://fred.stlouisfed.org/favicon.ico',
        docs_url: '/mkdocs/user/fx/providers/fed/',
    },
    {
        code: 'SNB',
        name: 'Swiss National Bank',
        base_currency: 'CHF',
        base_currencies: ['CHF'],
        // The 25 currencies of the live SNB dimensions, as audited on 2026-08-05 (03_fx-market-data.md:157-160), and CHF.
        target_currencies: ['ARS', 'AUD', 'BRL', 'CAD', 'CHF', 'CNY', 'CZK', 'DKK', 'EUR', 'GBP', 'HKD', 'HUF', 'JPY', 'KRW', 'MXN', 'MYR', 'NOK', 'NZD', 'PLN', 'RUB', 'SEK', 'SGD', 'THB', 'TRY', 'USD', 'ZAR'],
        description: 'Monthly average exchange rates from Swiss National Bank (no daily data available)',
        description_i18n: {
            en: 'Swiss National Bank — publishes monthly average exchange rates for ~25 currencies against CHF. Updated around the 2nd business day of the following month. One data point per month (⚠️ no daily data).',
            it: 'Banca Nazionale Svizzera — pubblica tassi di cambio medi mensili per ~25 valute contro CHF. Aggiornamento verso il 2° giorno lavorativo del mese successivo. Un dato al mese (⚠️ nessun dato giornaliero).',
            fr: 'Banque Nationale Suisse — publie des taux de change moyens mensuels pour ~25 devises contre CHF. Mise à jour vers le 2e jour ouvrable du mois suivant. Un point par mois (⚠️ pas de données quotidiennes).',
            es: 'Banco Nacional Suizo — publica tipos de cambio promedio mensuales para ~25 monedas contra CHF. Actualizado hacia el 2° día hábil del mes siguiente. Un dato por mes (⚠️ sin datos diarios).',
        },
        warning_i18n: {
            en: 'SNB provides only monthly averages (one value per month, on the 1st). In conversion chains, rates are computed only on dates where ALL providers have data — days without SNB data will have no chain rate.',
            it: 'La SNB fornisce solo medie mensili (un valore al mese, il 1°). Nelle catene di conversione, i tassi vengono calcolati solo nelle date in cui TUTTI i provider hanno dati — i giorni senza dati SNB non avranno tasso di catena.',
            fr: "La BNS ne fournit que des moyennes mensuelles (une valeur par mois, le 1er). Dans les chaînes de conversion, les taux ne sont calculés que les jours où TOUS les fournisseurs ont des données — les jours sans données BNS n'auront pas de taux de chaîne.",
            es: 'El BNS solo proporciona promedios mensuales (un valor por mes, el 1°). En las cadenas de conversión, los tipos se calculan solo en fechas donde TODOS los proveedores tienen datos — los días sin datos del BNS no tendrán tipo de cadena.',
        },
        icon_url: 'https://data.snb.ch/favicon.ico',
        docs_url: '/mkdocs/user/fx/providers/snb/',
    },
];
