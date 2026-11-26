/**
 * Gallery, Assets — the enrichers' catalogue the «Profilo» shots read (plan 68, E12): the enrichers' window, «Ultime
 * variazioni» and «Storia del dato» name their sources by it (`GET /assets/enrichers`, `loadEnricherNames`).
 *
 * ## Why it is served
 *
 * A test lane serves only `mockenrich` (`dev.py`, `LIBREFOLIO_ENRICHERS_ENABLED=mockenrich`): no suite and no gallery
 * shot ever reaches a real site. The real enrichers are then absent from the catalogue, and the seeded fund
 * (`PROFILE_HISTORY_FUND` in `populate_mock_data.py`, bound to justETF and Borsa Italiana) would show its sources by code
 * and its enrichers as «not active on this instance» — not what a user's instance shows. {@link serveGalleryEnrichers}
 * answers the catalogue instead, as an instance with the five real enrichers answers it. No read and no test reaches a
 * site (the shots only open and close windows); «Riconosci» and «Cerca online» of the enrichers' window are answered by
 * {@link serveGalleryEnricherAnswers} (82 ENR-4), as the real enrichers would answer for the seeded iShares Core MSCI
 * World (`GALLERY_RECOGNIZED_ASSET`).
 *
 * ## How it is made
 *
 * Generated from the plugins' declarations, no network — regenerate it whole, never by hand, when an enricher's
 * declarations change:
 *
 *     LIBREFOLIO_ENRICHERS_ENABLED=justetf,yfinance,borsa_italiana,esma,coingecko pipenv run python -c "import json; from backend.app.services.enrichers.bindings import enrichers_catalogue; print(json.dumps(enrichers_catalogue().model_dump(mode='json'), indent=4, ensure_ascii=False))"
 *
 * and paste the output as {@link GALLERY_ENRICHERS_CATALOGUE}. `configured` is the route's readiness, true for the
 * five: only CoinGecko has a required setting (its key), and the instance shown has one.
 */
import type {Page} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';

export const GALLERY_ENRICHERS_CATALOGUE = {
    enrichers: [
        {
            code: 'borsa_italiana',
            name: 'Borsa Italiana',
            icon: 'https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico',
            help_url: null,
            terms: 'price_source',
            accepted_identifier_types: ['ISIN', 'BI_FUND_CODE'],
            params_schema: [
                {
                    key: 'language',
                    type: 'select',
                    required: false,
                    options: ['en', 'it'],
                    default: 'en',
                    label: 'Language',
                    'x-i18n-key': 'enrichers.borsa_italiana.params.language',
                },
                {
                    key: 'mic',
                    type: 'string',
                    required: false,
                    label: 'Market MIC',
                    'x-i18n-key': 'enrichers.borsa_italiana.params.mic',
                },
                {
                    key: 'platform',
                    type: 'string',
                    required: false,
                    label: 'Platform',
                    'x-i18n-key': 'enrichers.borsa_italiana.params.platform',
                },
                {
                    key: 'codice_fondo',
                    type: 'string',
                    required: false,
                    label: 'Fund internal code',
                    'x-i18n-key': 'enrichers.borsa_italiana.params.codice_fondo',
                },
            ],
            supports_search: true,
            voices: {
                BOND: [
                    'accrued_interest',
                    'coupon_frequency',
                    'coupon_period_rate',
                    'coupon_rate',
                    'coupon_type',
                    'day_count',
                    'description',
                    'geography',
                    'issuer_country',
                    'issuer_name',
                    'issuer_type',
                    'legal_form',
                    'maturity_date',
                    'min_lot',
                    'modified_duration',
                    'outstanding_amount',
                    'payout_description',
                    'reference_price_date',
                    'sector',
                    'yield_gross',
                    'yield_net',
                ],
                STOCK: ['description', 'issuer_country', 'legal_form', 'net_income', 'revenue', 'sector', 'website'],
                FUND: ['fund_currency', 'inception_date', 'management_fee'],
            },
            default_priority: {
                STOCK: 20,
                ETF: null,
                BOND: 10,
                CRYPTO: null,
                FUND: 10,
                CROWDFUND: null,
                HOLD: null,
                COMMODITY: null,
                REAL_ESTATE: null,
                INDEX: null,
                OTHER: null,
                ETF_STOCK: null,
                ETF_BOND: null,
                ETF_COMMODITY: null,
                ETF_REAL_ESTATE: null,
                ETF_CRYPTO: null,
                ETF_MONETARY: null,
                CROWDFUND_REAL_ESTATE: null,
            },
            configured: true,
            missing_settings: [],
        },
        {
            code: 'coingecko',
            name: 'CoinGecko',
            icon: 'https://www.coingecko.com/favicon.ico',
            help_url: '/mkdocs/user/assets/providers/coingecko/',
            terms: 'self_hosted',
            accepted_identifier_types: ['COINGECKO_ID'],
            params_schema: [
                {
                    key: 'vs_currency',
                    type: 'select',
                    required: false,
                    options: [
                        'AED',
                        'ARS',
                        'AUD',
                        'BDT',
                        'BHD',
                        'BMD',
                        'BRL',
                        'CAD',
                        'CHF',
                        'CLP',
                        'CNY',
                        'CZK',
                        'DKK',
                        'EUR',
                        'GBP',
                        'GEL',
                        'HKD',
                        'HUF',
                        'IDR',
                        'ILS',
                        'INR',
                        'JPY',
                        'KRW',
                        'KWD',
                        'LKR',
                        'MMK',
                        'MXN',
                        'MYR',
                        'NGN',
                        'NOK',
                        'NZD',
                        'PHP',
                        'PKR',
                        'PLN',
                        'RUB',
                        'SAR',
                        'SEK',
                        'SGD',
                        'THB',
                        'TRY',
                        'TWD',
                        'UAH',
                        'USD',
                        'VND',
                        'ZAR',
                    ],
                    default: 'EUR',
                    label: 'Market capitalisation currency',
                    'x-i18n-key': 'enrichers.coingecko.params.vs_currency',
                },
            ],
            supports_search: true,
            voices: {
                CRYPTO: ['crypto_categories', 'description', 'inception_date', 'market_cap', 'website'],
            },
            default_priority: {
                STOCK: null,
                ETF: null,
                BOND: null,
                CRYPTO: 10,
                FUND: null,
                CROWDFUND: null,
                HOLD: null,
                COMMODITY: null,
                REAL_ESTATE: null,
                INDEX: null,
                OTHER: null,
                ETF_STOCK: null,
                ETF_BOND: null,
                ETF_COMMODITY: null,
                ETF_REAL_ESTATE: null,
                ETF_CRYPTO: null,
                ETF_MONETARY: null,
                CROWDFUND_REAL_ESTATE: null,
            },
            configured: true,
            missing_settings: [],
        },
        {
            code: 'esma',
            name: 'ESMA (FIRDS)',
            icon: 'https://www.esma.europa.eu/themes/custom/esma_webst_theme/favicon.ico',
            help_url: 'https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_firds',
            terms: 'open',
            accepted_identifier_types: ['ISIN'],
            params_schema: [],
            supports_search: false,
            voices: {
                STOCK: ['issuer_lei', 'legal_form'],
                BOND: ['coupon_rate', 'coupon_type', 'issuer_lei', 'issuer_type', 'legal_form', 'maturity_date'],
                FUND: ['distribution_policy', 'issuer_lei'],
                COMMODITY: ['issuer_lei', 'legal_form'],
                ETF_STOCK: ['distribution_policy', 'issuer_lei'],
                ETF_MONETARY: ['distribution_policy', 'issuer_lei'],
                ETF: ['distribution_policy', 'issuer_lei'],
                ETF_BOND: ['distribution_policy', 'issuer_lei'],
                ETF_REAL_ESTATE: ['distribution_policy', 'issuer_lei'],
                ETF_COMMODITY: ['distribution_policy', 'issuer_lei'],
                ETF_CRYPTO: ['distribution_policy', 'issuer_lei'],
            },
            default_priority: {
                STOCK: 30,
                ETF: 30,
                BOND: 30,
                CRYPTO: null,
                FUND: 30,
                CROWDFUND: null,
                HOLD: null,
                COMMODITY: 30,
                REAL_ESTATE: null,
                INDEX: null,
                OTHER: null,
                ETF_STOCK: 30,
                ETF_BOND: 30,
                ETF_COMMODITY: 30,
                ETF_REAL_ESTATE: 30,
                ETF_CRYPTO: 30,
                ETF_MONETARY: 30,
                CROWDFUND_REAL_ESTATE: null,
            },
            configured: true,
            missing_settings: [],
        },
        {
            code: 'justetf',
            name: 'justETF',
            icon: 'https://www.justetf.com/android-chrome-144x144.png?v2',
            help_url: null,
            terms: 'price_source',
            accepted_identifier_types: ['ISIN'],
            params_schema: [],
            supports_search: true,
            voices: {
                ETF_STOCK: ['description', 'distribution_policy', 'fund_currency', 'fund_domicile', 'fund_provider', 'fund_size', 'geography', 'inception_date', 'index_name', 'replication', 'sector', 'ter'],
                ETF_MONETARY: ['description', 'distribution_policy', 'fund_currency', 'fund_domicile', 'fund_provider', 'fund_size', 'geography', 'inception_date', 'index_name', 'replication', 'sector', 'ter'],
                ETF: ['description', 'distribution_policy', 'fund_currency', 'fund_domicile', 'fund_provider', 'fund_size', 'geography', 'inception_date', 'index_name', 'legal_form', 'replication', 'sector', 'ter'],
                COMMODITY: ['description', 'distribution_policy', 'fund_currency', 'fund_domicile', 'fund_provider', 'fund_size', 'geography', 'inception_date', 'index_name', 'legal_form', 'replication', 'sector', 'ter'],
                ETF_BOND: ['description', 'distribution_policy', 'fund_currency', 'fund_domicile', 'fund_provider', 'fund_size', 'geography', 'inception_date', 'index_name', 'replication', 'sector', 'ter'],
                ETF_REAL_ESTATE: ['description', 'distribution_policy', 'fund_currency', 'fund_domicile', 'fund_provider', 'fund_size', 'geography', 'inception_date', 'index_name', 'replication', 'sector', 'ter'],
                ETF_COMMODITY: ['description', 'distribution_policy', 'fund_currency', 'fund_domicile', 'fund_provider', 'fund_size', 'geography', 'inception_date', 'index_name', 'legal_form', 'replication', 'sector', 'ter'],
                ETF_CRYPTO: ['description', 'distribution_policy', 'fund_currency', 'fund_domicile', 'fund_provider', 'fund_size', 'geography', 'inception_date', 'index_name', 'legal_form', 'replication', 'sector', 'ter'],
            },
            default_priority: {
                STOCK: null,
                ETF: 10,
                BOND: null,
                CRYPTO: null,
                FUND: null,
                CROWDFUND: null,
                HOLD: null,
                COMMODITY: 10,
                REAL_ESTATE: null,
                INDEX: null,
                OTHER: null,
                ETF_STOCK: 10,
                ETF_BOND: 10,
                ETF_COMMODITY: 10,
                ETF_REAL_ESTATE: 10,
                ETF_CRYPTO: 10,
                ETF_MONETARY: 10,
                CROWDFUND_REAL_ESTATE: null,
            },
            configured: true,
            missing_settings: [],
        },
        {
            code: 'yfinance',
            name: 'Yahoo Finance',
            icon: 'https://s.yimg.com/cv/apiv2/default/icons/favicon_y19_32x32_custom.svg',
            help_url: null,
            terms: 'price_source',
            accepted_identifier_types: ['TICKER'],
            params_schema: [],
            supports_search: true,
            voices: {
                STOCK: ['description', 'industry', 'issuer_country', 'market_cap', 'sector'],
                ETF_STOCK: ['description', 'fund_provider', 'inception_date', 'sector', 'ter'],
                ETF_MONETARY: ['description', 'fund_provider', 'inception_date', 'sector', 'ter'],
                ETF: ['description', 'fund_provider', 'inception_date', 'sector', 'ter'],
                FUND: ['description', 'fund_provider', 'inception_date', 'sector', 'ter'],
                ETF_BOND: ['description', 'fund_provider', 'inception_date', 'sector', 'ter'],
                ETF_REAL_ESTATE: ['description', 'fund_provider', 'inception_date', 'sector', 'ter'],
                ETF_COMMODITY: ['description', 'fund_provider', 'inception_date', 'sector', 'ter'],
                ETF_CRYPTO: ['description', 'fund_provider', 'inception_date', 'sector', 'ter'],
            },
            default_priority: {
                STOCK: 10,
                ETF: 20,
                BOND: null,
                CRYPTO: null,
                FUND: 20,
                CROWDFUND: null,
                HOLD: null,
                COMMODITY: null,
                REAL_ESTATE: null,
                INDEX: null,
                OTHER: null,
                ETF_STOCK: 20,
                ETF_BOND: 20,
                ETF_COMMODITY: 20,
                ETF_REAL_ESTATE: 20,
                ETF_CRYPTO: 20,
                ETF_MONETARY: 20,
                CROWDFUND_REAL_ESTATE: null,
            },
            configured: true,
            missing_settings: [],
        },
    ],
    default_order: {
        STOCK: ['yfinance', 'borsa_italiana', 'esma'],
        ETF: ['justetf', 'yfinance', 'esma'],
        BOND: ['borsa_italiana', 'esma'],
        CRYPTO: ['coingecko'],
        FUND: ['borsa_italiana', 'yfinance', 'esma'],
        CROWDFUND: [],
        HOLD: [],
        COMMODITY: ['justetf', 'esma'],
        REAL_ESTATE: [],
        INDEX: [],
        OTHER: [],
        ETF_STOCK: ['justetf', 'yfinance', 'esma'],
        ETF_BOND: ['justetf', 'yfinance', 'esma'],
        ETF_COMMODITY: ['justetf', 'yfinance', 'esma'],
        ETF_REAL_ESTATE: ['justetf', 'yfinance', 'esma'],
        ETF_CRYPTO: ['justetf', 'yfinance', 'esma'],
        ETF_MONETARY: ['justetf', 'yfinance', 'esma'],
        CROWDFUND_REAL_ESTATE: [],
    },
};

/** Answer `GET /assets/enrichers` with the real enrichers' catalogue; checked against the API's schema first. */
export async function serveGalleryEnrichers(page: Page): Promise<void> {
    const body = JSON.stringify(schemas.FAEnrichersCatalogue.parse(GALLERY_ENRICHERS_CATALOGUE));
    await page.route('**/api/v1/assets/enrichers', (route) => (route.request().method() === 'GET' ? route.fulfill({status: 200, contentType: 'application/json', body}) : route.fallback()));
}

/** The seeded ETF the enrichers' window is shot on (82 ENR-4): no enrichers yet, its ISIN and its bare ticker. */
export const GALLERY_RECOGNIZED_ASSET = {name: 'iShares Core MSCI World UCITS ETF USD (Acc)', isin: 'IE00B4L5Y983', ticker: 'IWDA'};
/** What the user types in «Cerca online» for the shot. */
export const GALLERY_ENRICHER_QUERY = 'iShares Core MSCI World';

const ESMA_NAME = 'ISHARES III PLC - ISHARES CORE MSCI WORLD UCITS ETF';
const JUSTETF_NAME = 'iShares Core MSCI World UCITS ETF USD (Acc)';

function sse(events: object[]): string {
    return events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');
}

function recognition(code: string, identifierType: string, identifier: string, name: string) {
    return {event: 'enricher_result', code, identifier_type: identifierType, identifier, status: 'found', name, page_url: null, identifiers: {}, conflicts: {}, error: null, params: {}};
}

/**
 * «Riconosci» and «Cerca online» answered as the real enrichers would for {@link GALLERY_RECOGNIZED_ASSET} (82 ENR-4):
 * justETF and ESMA know its ISIN (they enter the list by themselves), Yahoo Finance finds only its bare ticker (it waits
 * in «Non in elenco»); a search by name finds three Yahoo listings, each on its market. Every other enricher answers
 * nothing.
 */
export async function serveGalleryEnricherAnswers(page: Page): Promise<void> {
    const {isin, ticker} = GALLERY_RECOGNIZED_ASSET;
    const recognized = sse([
        recognition('justetf', 'ISIN', isin, JUSTETF_NAME),
        recognition('esma', 'ISIN', isin, ESMA_NAME),
        recognition('yfinance', 'TICKER', ticker, 'iShares Core MSCI World UCITS ETF USD (Acc)'),
        {event: 'done', found_order: ['justetf', 'esma', 'yfinance'], default_order: ['justetf', 'yfinance', 'esma'], identifiers: {ISIN: isin, TICKER: ticker}},
    ]);
    await page.route('**/api/v1/assets/enrichers/recognize', (route) => route.fulfill({status: 200, contentType: 'text/event-stream', body: recognized}));
    await page.route('**/api/v1/assets/enrichers/search?*', (route) => {
        const url = new URL(route.request().url());
        const codes = url.searchParams.getAll('codes');
        const hit = (symbol: string, market: string) => ({name: 'iShares Core MSCI World UCITS ETF', binding: {identifier_type: 'TICKER', identifier: symbol}, asset_type: 'ETF', page_url: `https://finance.yahoo.com/quote/${symbol}`, market});
        const results = (code: string) => (code === 'yfinance' ? [hit('SWDA.MI', 'Milan'), hit('SWDA.L', 'London'), hit('IWDA.AS', 'Amsterdam')] : []);
        const events = codes.map((code) => ({event: 'enricher_results', code, status: 'ok', via: 'search', results: results(code), accepted_identifier_types: code === 'yfinance' ? ['TICKER'] : ['ISIN'], retry_after: null, error_code: null}));
        return route.fulfill({status: 200, contentType: 'text/event-stream', body: sse([...events, {event: 'done', codes}])});
    });
}
