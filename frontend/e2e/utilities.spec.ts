/**
 * E2E Tests for Utility API endpoints.
 *
 * Tests the /api/v1/utilities/* endpoints via Playwright API requests,
 * validating the full backend→frontend pipeline for presentation data
 * (currencies, countries, sectors).
 *
 * These tests cover backend functions that serve UI presentation data:
 * - normalize_currency() → currency_utils.py
 * - list_currencies() → currency_utils.py
 * - list_countries() → geo_utils.py
 * - normalize_country_to_iso3() → geo_utils.py
 * - expand_region() → geo_utils.py
 * - FinancialSector.list_all() → sector_fin_utils.py
 */

import {expect, test} from '@playwright/test';
import {login} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';
import {goToFxPage} from './fx/fx-helpers';
import {goToAssetsPage} from './assets/assets-helpers';

const API = '/api/v1/utilities';

test.describe('Utilities API — Currencies', () => {
    test('currency list has major currencies', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/currencies`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();

        expect(data.items.length).toBeGreaterThan(100);
        const codes = data.items.map((c: any) => c.code);
        expect(codes).toContain('USD');
        expect(codes).toContain('EUR');
        expect(codes).toContain('GBP');
        expect(codes).toContain('JPY');
        expect(codes).toContain('CHF');
    });

    test('currency list in Italian has localized names', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/currencies?language=it`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();

        expect(data.language).toBe('it');
        const eur = data.items.find((c: any) => c.code === 'EUR');
        expect(eur).toBeTruthy();
        expect(eur.name.toLowerCase()).toContain('uro'); // "Euro" in Italian
    });

    test('currency list has symbols', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/currencies`);
        const data = await response.json();

        const eur = data.items.find((c: any) => c.code === 'EUR');
        expect(eur.symbol).toBe('€');
        const usd = data.items.find((c: any) => c.code === 'USD');
        expect(usd.symbol).toBe('$');
    });

    test('normalize € resolves to EUR', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/currencies/normalize?name=${encodeURIComponent('€')}`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();

        expect(data.iso_codes).toContain('EUR');
        expect(data.match_type).toBe('exact');
    });

    test('normalize Dollar contains USD', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/currencies/normalize?name=Dollar`);
        const data = await response.json();

        expect(data.iso_codes).toContain('USD');
    });

    test('normalize $ is ambiguous', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/currencies/normalize?name=${encodeURIComponent('$')}`);
        const data = await response.json();

        expect(data.match_type).toBe('symbol_ambiguous');
        expect(data.iso_codes.length).toBeGreaterThan(1);
        expect(data.iso_codes).toContain('USD');
    });

    test('normalize GBP already ISO returns exact', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/currencies/normalize?name=GBP`);
        const data = await response.json();

        expect(data.iso_codes).toContain('GBP');
        expect(data.match_type).toBe('exact');
    });

    test('normalize unknown currency returns not_found', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/currencies/normalize?name=ZZZZZ`);
        const data = await response.json();

        expect(data.match_type).toBe('not_found');
        expect(data.iso_codes).toEqual([]);
    });
});

test.describe('Utilities API — Countries', () => {
    test('country list has flags for all entries', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/countries`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();

        expect(data.items.length).toBeGreaterThan(200);
        for (const country of data.items) {
            expect(country.flag_emoji).toBeTruthy();
        }
    });

    test('country list Italian names', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/countries?language=it`);
        const data = await response.json();

        expect(data.language).toBe('it');
        const ita = data.items.find((c: any) => c.iso3 === 'ITA');
        expect(ita).toBeTruthy();
        expect(ita.name).toBe('Italia');
        expect(ita.flag_emoji).toBe('🇮🇹');

        const usa = data.items.find((c: any) => c.iso3 === 'USA');
        expect(usa).toBeTruthy();
        expect(usa.name).toContain('Stati Uniti');
    });

    test('country list has ISO codes', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/countries`);
        const data = await response.json();

        for (const country of data.items) {
            expect(country.iso3).toHaveLength(3);
            expect(country.iso2).toHaveLength(2);
        }
    });

    test('normalize country name Italia', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/countries/normalize?name=Italia`);
        const data = await response.json();

        expect(data.iso3_codes).toContain('ITA');
        expect(data.match_type).toBe('exact');
    });

    test('normalize country ISO2 US', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/countries/normalize?name=US`);
        const data = await response.json();

        expect(data.iso3_codes).toContain('USA');
    });

    test('normalize G7 returns region with 7 countries', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/countries/normalize?name=G7`);
        const data = await response.json();

        expect(data.match_type).toBe('region');
        expect(data.iso3_codes.length).toBe(7);
    });

    test('normalize unknown country returns not_found', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/countries/normalize?name=Narnia`);
        const data = await response.json();

        expect(data.match_type).toBe('not_found');
        expect(data.iso3_codes).toEqual([]);
    });
});

test.describe('Utilities API — Sectors', () => {
    test('sector list has standard sectors', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/sectors`);
        expect(response.ok()).toBeTruthy();
        const data = await response.json();

        expect(data.items).toContain('Technology');
        expect(data.items).toContain('Financials');
        expect(data.items).toContain('Health Care');
    });

    test('sector list with Other included', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/sectors?include_other=true`);
        const data = await response.json();

        expect(data.items).toContain('Other');
    });

    test('sector list without Other', async ({page}) => {
        await login(page, TEST_USER);
        const response = await page.request.get(`${API}/sectors?include_other=false`);
        const data = await response.json();

        expect(data.items).not.toContain('Other');
    });
});

test.describe('Utilities — UI Rendering', () => {
    test('FX page shows currency flag emojis on cards', async ({page}) => {
        await login(page, TEST_USER);
        await goToFxPage(page);

        // FX cards must exist (populated by mock data)
        const cards = page.locator('[data-testid^="fx-card-"]');
        await expect(cards.first()).toBeVisible({timeout: 5_000});
        const count = await cards.count();
        expect(count, 'FX pairs must exist — check populate_mock_data.py').toBeGreaterThan(0);

        // At least one card should contain a flag emoji or ISO currency code
        const firstCard = cards.first();
        const text = await firstCard.textContent();
        // Flag emojis are regional indicator symbols (U+1F1E6..U+1F1FF) or we see ISO codes like EUR, USD
        const hasFlagOrCode = /[\u{1F1E6}-\u{1F1FF}]{2}|[A-Z]{3}/u.test(text ?? '');
        expect(hasFlagOrCode).toBeTruthy();

        // Check that emoji-flag spans exist in the card
        const flagSpans = firstCard.locator('.emoji-flag');
        const flagCount = await flagSpans.count();
        expect(flagCount).toBeGreaterThan(0);
    });

    test('Asset modal currency selector has ISO 3-letter options', async ({page}) => {
        await login(page, TEST_USER);
        await goToAssetsPage(page);

        // Open edit modal on first asset (must exist — populated by mock data)
        const firstCard = page.locator('[data-testid^="asset-card-"]').first();
        await expect(firstCard).toBeVisible({timeout: 5_000});
        await firstCard.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});

        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        // Find the currency combobox and open it
        const form = page.getByTestId('asset-modal-form');
        const combobox = form.locator('[role="combobox"]').first();
        await combobox.click();
        await page.waitForTimeout(500);

        // Listbox should show options with 3-letter ISO codes
        const listbox = page.locator('[role="listbox"]');
        await expect(listbox).toBeVisible({timeout: 3_000});
        const options = listbox.locator('button');
        await expect(options.first()).toBeVisible({timeout: 3_000});
        const optCount = await options.count();
        expect(optCount).toBeGreaterThan(0);
        // First option text should contain a 3-letter code
        const firstOptionText = await options.first().textContent();
        expect(firstOptionText).toMatch(/[A-Z]{3}/);

        await page.getByTestId('asset-modal-cancel').click();
    });
});
