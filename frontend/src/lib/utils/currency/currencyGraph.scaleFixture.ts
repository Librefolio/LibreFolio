/**
 * A fake FX provider catalogue the size the real one reaches after wave 1 of lane 75 (central banks).
 *
 * Synthetic, not captured: the sizes and bases follow the lane plan, the currency lists are drawn from one ranked
 * universe so the overlaps look like the real ones. The majors come first, so every provider covers them; the long
 * tail is covered only by the two global providers, BDI (base EUR, ~178) and BCB (base USD, ~156), which share ~150.
 * Real ISO codes are used where there are enough of them, so a pair in the test reads like a pair a user would pick.
 *
 * MANUAL is listed as `GET /fx/providers` lists it, but `buildCurrencyGraph` skips it (a sentinel, not a data source),
 * exactly as in the app (`currencyGraphStore.getCurrencyGraph` passes every provider through unchanged).
 */
import type {ProviderInfo} from './currencyGraph';

/**
 * 182 currency codes (synthetic `XS*`, `XT*`, `XU*` codes fill the tail), ranked from the most covered to the least. The rank is what decides coverage: a provider of size
 * N covers the first N codes of this list other than its own base.
 */
// prettier-ignore
export const UNIVERSE: readonly string[] = [
    // Majors: every central bank publishes these (0-29).
    'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD', 'SEK', 'NOK',
    'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'TRY', 'CNY', 'HKD', 'SGD',
    'KRW', 'INR', 'IDR', 'MYR', 'PHP', 'THB', 'MXN', 'BRL', 'ZAR', 'ILS',
    // Second ring: ECB history, NORGES, NBU, CBR (30-59).
    'ISK', 'RUB', 'UAH', 'TWD', 'CLP', 'ARS', 'COP', 'PEN', 'AED', 'SAR',
    'KZT', 'BYN', 'MDL', 'GEL', 'AMD', 'AZN', 'RSD', 'EGP', 'MAD', 'PKR',
    'VND', 'BDT', 'KWD', 'QAR', 'UZS', 'KGS', 'TJS', 'TMT', 'LKR', 'NGN',
    // Long tail: only BDI and BCB (60-181).
    'KES', 'GHS', 'TND', 'DZD', 'JOD', 'BHD', 'OMR', 'LBP', 'IQD', 'IRR',
    'AFN', 'NPR', 'MMK', 'KHR', 'LAK', 'MNT', 'BND', 'MOP', 'FJD', 'PGK',
    'SBD', 'TOP', 'WST', 'VUV', 'XPF', 'XAF', 'XOF', 'XCD', 'BBD', 'BSD',
    'BZD', 'BMD', 'KYD', 'JMD', 'TTD', 'HTG', 'DOP', 'CUP', 'GTQ', 'HNL',
    'NIO', 'CRC', 'PAB', 'BOB', 'PYG', 'UYU', 'VES', 'GYD', 'SRD', 'AWG',
    'ANG', 'ETB', 'ERN', 'DJF', 'SOS', 'SDG', 'SSP', 'UGX', 'TZS', 'RWF',
    'BIF', 'CDF', 'AOA', 'ZMW', 'MWK', 'MZN', 'ZWL', 'BWP', 'NAD', 'LSL',
    'SZL', 'MGA', 'MUR', 'SCR', 'KMF', 'CVE', 'STN', 'GMD', 'GNF', 'SLE',
    'LRD', 'MRU', 'LYD', 'SYP', 'YER', 'MVR', 'BTN', 'ALL', 'MKD', 'BAM',
    'XAU', 'XAG', 'XDR', 'FKP', 'GIP', 'SHP', 'KPW', 'CUC', 'TVD', 'XS1',
    'XS2', 'XS3', 'XS4', 'XS5', 'XS6', 'XS7', 'XS8', 'XS9', 'XT1', 'XT2',
    'XT3', 'XT4', 'XT5', 'XT6', 'XT7', 'XT8', 'XT9', 'XU1', 'XU2', 'XU3',
    'XU4', 'XU5',
];

/** The first `size` codes of the universe, the provider's own base left out. */
function firstCodes(base: string, size: number): string[] {
    return UNIVERSE.filter((code) => code !== base).slice(0, size);
}

/** A provider as `GET /fx/providers` describes it, reduced to what the graph reads. */
function provider(code: string, base: string, targets: string[]): ProviderInfo {
    return {code, name: `Scale ${code}`, base_currency: base, base_currencies: [base], target_currencies: targets};
}

/**
 * BDI covers everything but the last three codes (178 targets); BCB covers the first 153 codes other than USD and those
 * last three (156 targets). The two global providers share 152 targets and each has a few of its own, as the real ones do.
 */
const BDI_TARGETS = UNIVERSE.slice(0, 179).filter((code) => code !== 'EUR');
const BCB_ONLY = UNIVERSE.slice(179);

/** Scenario 1: the catalogue after wave 1 — ECB, FED, BOE, SNB, BDI, BCB, NORGES, NBU, BOC, plus the MANUAL sentinel. */
export function wave1Providers(): ProviderInfo[] {
    return [
        provider('ECB', 'EUR', firstCodes('EUR', 45)),
        provider('FED', 'USD', firstCodes('USD', 23)),
        provider('BOE', 'GBP', firstCodes('GBP', 15)),
        provider('SNB', 'CHF', firstCodes('CHF', 25)),
        provider('BDI', 'EUR', BDI_TARGETS),
        provider('BCB', 'USD', [...firstCodes('USD', 153), ...BCB_ONLY]),
        provider('NORGES', 'NOK', firstCodes('NOK', 40)),
        provider('NBU', 'UAH', firstCodes('UAH', 41)),
        provider('BOC', 'CAD', firstCodes('CAD', 24)),
        provider('MANUAL', 'EUR', []),
    ];
}

/** Scenario 2: scenario 1 plus CBR (base RUB, ~54). */
export function wave1PlusCbrProviders(): ProviderInfo[] {
    return [...wave1Providers(), provider('CBR', 'RUB', firstCodes('RUB', 54))];
}

/**
 * Scenario 0: today's catalogue, with the real lists. FED and BOE from their `CURRENCY_SERIES`, ECB and NORGES from
 * their `FALLBACK_CURRENCIES`, SNB from the live list audited on 2026-08-05 (`e2e/fixtures/galleryOfflineData.ts`).
 * The base is left out of the targets: `buildCurrencyGraph` skips that self-loop anyway.
 */
// prettier-ignore
export function todayProviders(): ProviderInfo[] {
    const real = (code: string, base: string, list: string) => provider(code, base, list.split(' ').filter((c) => c !== base));
    return [
        real('ECB', 'EUR', 'ARS AUD BGN BRL CAD CHF CNY CYP CZK DKK DZD EEK GBP GRD HKD HRK HUF IDR ILS INR ISK JPY KRW LTL LVL MAD MTL MXN MYR NOK NZD PHP PLN RON RUB SEK SGD SIT SKK THB TRY TWD USD ZAR'),
        real('FED', 'USD', 'AUD BRL CAD CHF CNY DKK EUR GBP HKD INR JPY KRW LKR MXN MYR NOK NZD SEK SGD THB TWD VES ZAR'),
        real('BOE', 'GBP', 'AUD CAD CHF CNY DKK EUR HKD INR JPY NOK NZD SEK SGD USD ZAR'),
        real('SNB', 'CHF', 'ARS AUD BRL CAD CNY CZK DKK EUR GBP HKD HUF JPY KRW MXN MYR NOK NZD PLN RUB SEK SGD THB TRY USD ZAR'),
        real('NORGES', 'NOK', 'AUD BDT BRL BYN CAD CHF CNY CZK DKK EUR GBP HKD HUF IDR ILS INR ISK JPY KRW MMK MXN MYR NZD PHP PKR PLN RON SEK SGD THB TRY TWD USD VND ZAR'),
        provider('MANUAL', 'EUR', []),
    ];
}
