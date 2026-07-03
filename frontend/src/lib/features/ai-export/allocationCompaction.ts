/**
 * Allocation Compaction — reduces long-tail geography/sector allocation lists
 * to a compact, LLM-friendly representation.
 *
 * Rule: entries below a percent threshold are grouped into a bucket
 * ("<Continent> minor countries" for geography, "Minor sectors" for sector).
 * "Unknown" and "Liquidity" are always kept as separate entries, never merged
 * into a minor bucket, regardless of their weight.
 *
 * Country codes are ISO 3166-1 alpha-3 (matching the backend's
 * `geographic_area.distribution` classification keys).
 */

import type {AiAllocationItem} from './types';

const KEEP_SEPARATE = new Set(['Unknown', 'Liquidity', 'Cash / Liquidity']);

// ─── ISO3 → Continent mapping ────────────────────────────────────────────────
// Continent buckets: Europe, Asia-Pacific, North America, South America, Africa.
// Any code not listed here falls into "Other minor countries" when below threshold.

const EUROPE = [
	'ALB', 'AND', 'AUT', 'BEL', 'BIH', 'BGR', 'HRV', 'CYP', 'CZE', 'DNK', 'EST', 'FIN', 'FRA', 'DEU', 'GRC',
	'HUN', 'ISL', 'IRL', 'ITA', 'LVA', 'LIE', 'LTU', 'LUX', 'MLT', 'MDA', 'MCO', 'MNE', 'NLD', 'MKD', 'NOR',
	'POL', 'PRT', 'ROU', 'RUS', 'SMR', 'SRB', 'SVK', 'SVN', 'ESP', 'SWE', 'CHE', 'UKR', 'GBR', 'VAT', 'BLR',
	'GIB', 'JEY', 'GGY', 'IMN', 'FRO', 'ALA', 'SJM', 'XKX',
];

const ASIA_PACIFIC = [
	'AFG', 'ARM', 'AZE', 'BHR', 'BGD', 'BTN', 'BRN', 'KHM', 'CHN', 'GEO', 'HKG', 'IND', 'IDN', 'IRN', 'IRQ',
	'ISR', 'JPN', 'JOR', 'KAZ', 'KWT', 'KGZ', 'LAO', 'LBN', 'MAC', 'MYS', 'MDV', 'MNG', 'MMR', 'NPL', 'PRK',
	'OMN', 'PAK', 'PHL', 'QAT', 'SAU', 'SGP', 'KOR', 'LKA', 'SYR', 'TWN', 'TJK', 'THA', 'TLS', 'TUR', 'TKM',
	'ARE', 'UZB', 'VNM', 'YEM', 'PSE', 'AUS', 'NZL', 'FJI', 'PNG', 'SLB', 'VUT', 'WSM', 'TON', 'KIR', 'MHL',
	'FSM', 'NRU', 'PLW', 'TUV', 'NCL', 'PYF', 'GUM', 'ASM', 'COK', 'NIU', 'TKL',
];

const NORTH_AMERICA = [
	'USA', 'CAN', 'MEX', 'BLZ', 'CRI', 'SLV', 'GTM', 'HND', 'NIC', 'PAN', 'ATG', 'BHS', 'BRB', 'CUB', 'DMA',
	'DOM', 'GRD', 'HTI', 'JAM', 'KNA', 'LCA', 'VCT', 'TTO', 'ABW', 'CUW', 'SXM', 'BMU', 'CYM', 'TCA', 'VGB',
	'VIR', 'PRI', 'GLP', 'MTQ', 'BLM', 'MAF',
];

const SOUTH_AMERICA = ['ARG', 'BOL', 'BRA', 'CHL', 'COL', 'ECU', 'GUY', 'PRY', 'PER', 'SUR', 'URY', 'VEN', 'FLK', 'GUF'];

const AFRICA = [
	'DZA', 'AGO', 'BEN', 'BWA', 'BFA', 'BDI', 'CPV', 'CMR', 'CAF', 'TCD', 'COM', 'COG', 'COD', 'CIV', 'DJI',
	'EGY', 'GNQ', 'ERI', 'SWZ', 'ETH', 'GAB', 'GMB', 'GHA', 'GIN', 'GNB', 'KEN', 'LSO', 'LBR', 'LBY', 'MDG',
	'MWI', 'MLI', 'MRT', 'MUS', 'MAR', 'MOZ', 'NAM', 'NER', 'NGA', 'RWA', 'STP', 'SEN', 'SYC', 'SLE', 'SOM',
	'ZAF', 'SSD', 'SDN', 'TZA', 'TGO', 'TUN', 'UGA', 'ZMB', 'ZWE', 'ESH', 'MYT', 'REU', 'SHN',
];

const ISO3_TO_CONTINENT: Record<string, string> = {};
for (const code of EUROPE) ISO3_TO_CONTINENT[code] = 'Europe';
for (const code of ASIA_PACIFIC) ISO3_TO_CONTINENT[code] = 'Asia-Pacific';
for (const code of NORTH_AMERICA) ISO3_TO_CONTINENT[code] = 'North America';
for (const code of SOUTH_AMERICA) ISO3_TO_CONTINENT[code] = 'South America';
for (const code of AFRICA) ISO3_TO_CONTINENT[code] = 'Africa';

function continentBucketName(iso3: string): string {
	const continent = ISO3_TO_CONTINENT[iso3];
	return continent ? `${continent} minor countries` : 'Other minor countries';
}

// ─── Compaction functions ────────────────────────────────────────────────────

/**
 * Groups country entries below `thresholdPercent` into continent buckets.
 * "Unknown" and "Liquidity" entries are always kept separate.
 */
export function compactGeography(items: AiAllocationItem[], thresholdPercent = 1): AiAllocationItem[] {
	const kept: AiAllocationItem[] = [];
	const bucketTotals = new Map<string, number>();

	for (const item of items) {
		if (KEEP_SEPARATE.has(item.name) || item.percent >= thresholdPercent) {
			kept.push(item);
			continue;
		}
		const bucket = continentBucketName(item.name);
		bucketTotals.set(bucket, (bucketTotals.get(bucket) ?? 0) + item.percent);
	}

	for (const [name, percent] of bucketTotals) {
		if (percent > 0) kept.push({name, percent: Math.round(percent * 100) / 100});
	}

	return kept.sort((a, b) => b.percent - a.percent);
}

/**
 * Groups sector entries below `thresholdPercent` into a single "Minor sectors" bucket.
 * "Unknown" and "Liquidity" entries are always kept separate.
 */
export function compactSector(items: AiAllocationItem[], thresholdPercent = 1): AiAllocationItem[] {
	const kept: AiAllocationItem[] = [];
	let minorTotal = 0;

	for (const item of items) {
		if (KEEP_SEPARATE.has(item.name) || item.percent >= thresholdPercent) {
			kept.push(item);
			continue;
		}
		minorTotal += item.percent;
	}

	if (minorTotal > 0) {
		kept.push({name: 'Minor sectors', percent: Math.round(minorTotal * 100) / 100});
	}

	return kept.sort((a, b) => b.percent - a.percent);
}
