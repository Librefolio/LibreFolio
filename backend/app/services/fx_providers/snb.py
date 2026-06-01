"""
Swiss National Bank (SNB) FX rate provider.

This provider fetches exchange rates from the SNB Data Portal using the JSON API.
SNB provides **monthly** average rates with CHF as base currency.

Dataset: `devkum` — monthly exchange rates (no daily dataset available from SNB API).
Each data point represents a monthly average. We assign it to the 1st of the month.

Key API endpoints used:
  - Dimensions:  GET /api/cube/devkum/dimensions/en   → dynamic currency map
  - Data (JSON): GET /api/cube/devkum/data/json/en     → filtered rate data

JSON response structure (filtered):
    {
      "timeseries": [
        {
          "header": [
            {"dim": "Monthly average/End of month", "dimItem": "Monthly average"},
            {"dim": "Currency", "dimItem": "Europe - EUR 1"}
          ],
          "metadata": {"key": "EPB@SNB.devkum{M0,EUR1}", ...},
          "values": [
            {"date": "2025-02", "value": 0.94114},
            {"date": "2025-03", "value": 0.95}
          ]
        }, ...
      ]
    }

API Documentation: https://data.snb.ch/en/topics/ziredev/cube/devkum
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx import FXRateProvider, FXServiceError
from backend.app.services.provider_registry import FXProviderRegistry, register_provider

logger = get_logger(__name__)

# Regex to extract ISO currency code and multiplier from D1 id (e.g. "CNY100" → CNY, 100)
_D1_RE = re.compile(r"^([A-Z]{3})(\d+)$")

# D1 ids to skip: forward rates and SDR (not real currencies)
_SKIP_D1_IDS = {"USD3M", "USD6M", "XDR1"}


@register_provider(FXProviderRegistry)
class SNBProvider(FXRateProvider):
    """
    Swiss National Bank FX rate provider.

    Provides **monthly** exchange rates with CHF as base currency.
    Data source: SNB Data Portal (dataset: devkum, JSON API).

    Note: SNB does NOT offer a daily-rate API. The `devkum` dataset provides
    monthly averages (M0) and month-end snapshots (M1). We use M0 and assign
    each rate to the 1st of the month for compatibility with the daily-rate
    storage model.

    The currency map is loaded dynamically from the /dimensions endpoint the
    first time it's needed (lazy init, cached for the process lifetime).

    Coverage: ~25 currencies (USD, EUR, GBP, JPY, CNY, AUD, CAD, ...)
    Update frequency: Monthly (published around 2nd business day of next month)
    """

    BASE_URL = "https://data.snb.ch/api/cube"
    DATASET = "devkum"

    # ── Lazy-loaded currency map ────────────────────────────────────────────
    # Maps ISO code → D1 id  (e.g. "CNY" → "CNY100")
    # and D1 id → (iso_code, multiplier)  (e.g. "CNY100" → ("CNY", 100))
    _iso_to_d1: dict[str, str] | None = None
    _d1_to_iso: dict[str, tuple[str, int]] | None = None

    # ── Provider identity ───────────────────────────────────────────────────

    @property
    def code(self) -> str:
        return "SNB"

    @property
    def provider_code(self) -> str:
        return self.code

    @property
    def name(self) -> str:
        return "Swiss National Bank"

    @property
    def icon(self) -> str | None:
        return "https://data.snb.ch/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/developer/backend/fx/providers_list/#snb"

    @property
    def base_currency(self) -> str:
        return "CHF"

    @property
    def description(self) -> str:
        return "Monthly average exchange rates from Swiss National Bank (no daily data available)"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Swiss National Bank — publishes monthly average exchange rates for ~25 currencies against CHF. Updated around the 2nd business day of the following month. One data point per month (⚠️ no daily data).",
            "it": "Banca Nazionale Svizzera — pubblica tassi di cambio medi mensili per ~25 valute contro CHF. Aggiornamento verso il 2° giorno lavorativo del mese successivo. Un dato al mese (⚠️ nessun dato giornaliero).",
            "fr": "Banque Nationale Suisse — publie des taux de change moyens mensuels pour ~25 devises contre CHF. Mise à jour vers le 2e jour ouvrable du mois suivant. Un point par mois (⚠️ pas de données quotidiennes).",
            "es": "Banco Nacional Suizo — publica tipos de cambio promedio mensuales para ~25 monedas contra CHF. Actualizado hacia el 2° día hábil del mes siguiente. Un dato por mes (⚠️ sin datos diarios).",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "SNB provides only monthly averages (one value per month, on the 1st). In conversion chains, rates are computed only on dates where ALL providers have data — days without SNB data will have no chain rate.",
            "it": "La SNB fornisce solo medie mensili (un valore al mese, il 1°). Nelle catene di conversione, i tassi vengono calcolati solo nelle date in cui TUTTI i provider hanno dati — i giorni senza dati SNB non avranno tasso di catena.",
            "fr": "La BNS ne fournit que des moyennes mensuelles (une valeur par mois, le 1er). Dans les chaînes de conversion, les taux ne sont calculés que les jours où TOUS les fournisseurs ont des données — les jours sans données BNS n'auront pas de taux de chaîne.",
            "es": "El BNS solo proporciona promedios mensuales (un valor por mes, el 1°). En las cadenas de conversión, los tipos se calculan solo en fechas donde TODOS los proveedores tienen datos — los días sin datos del BNS no tendrán tipo de cadena.",
        }

    @property
    def test_currencies(self) -> list[str]:
        return ["CHF", "USD", "EUR", "GBP", "JPY"]

    # ── Currency map (dynamic from /dimensions) ─────────────────────────────

    async def _ensure_currency_map(self) -> None:
        """Load the currency map from the SNB dimensions API (once per process)."""
        if self._iso_to_d1 is not None:
            return

        url = f"{self.BASE_URL}/{self.DATASET}/dimensions/en"
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            logger.error(f"Failed to fetch SNB dimensions: {e}")
            raise FXServiceError(f"Cannot load SNB currency list: {e}") from e

        iso_to_d1: dict[str, str] = {}
        d1_to_iso: dict[str, tuple[str, int]] = {}

        # Navigate: dimensions → find D1 → recurse dimensionItems
        for dim in data.get("dimensions", []):
            if dim.get("id") != "D1":
                continue
            self._walk_dimension_items(dim.get("dimensionItems", []), iso_to_d1, d1_to_iso)

        logger.debug(f"SNB dimensions loaded: {len(iso_to_d1)} currencies mapped")
        # Class-level cache (shared across instances within the same process)
        SNBProvider._iso_to_d1 = iso_to_d1
        SNBProvider._d1_to_iso = d1_to_iso

    @staticmethod
    def _walk_dimension_items(
        items: list[dict],
        iso_to_d1: dict[str, str],
        d1_to_iso: dict[str, tuple[str, int]],
    ) -> None:
        """Recursively walk dimension items to extract currency codes."""
        for item in items:
            d1_id = item.get("id", "")

            # Skip group headers (D1_0, D1_1, ...) — recurse into children
            if d1_id.startswith("D1_"):
                SNBProvider._walk_dimension_items(item.get("dimensionItems", []), iso_to_d1, d1_to_iso)
                continue

            # Skip forward rates and SDR
            if d1_id in _SKIP_D1_IDS:
                continue

            # Parse D1 id: "CNY100" → ("CNY", 100)
            m = _D1_RE.match(d1_id)
            if not m:
                logger.debug(f"SNB: skipping unrecognized D1 id: {d1_id}")
                continue

            iso_code = m.group(1)
            multiplier = int(m.group(2))

            iso_to_d1[iso_code] = d1_id
            d1_to_iso[d1_id] = (iso_code, multiplier)

    # ── Public API ──────────────────────────────────────────────────────────

    async def get_supported_currencies(self) -> list[str]:
        """Get list of supported ISO currency codes (dynamic from SNB API)."""
        await self._ensure_currency_map()
        assert self._iso_to_d1 is not None
        currencies = {"CHF"}
        currencies.update(self._iso_to_d1.keys())
        return sorted(currencies)

    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None,
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch FX rates from SNB JSON API for given date range and currencies.

        Uses the filtered JSON endpoint with dimSel to request only the needed
        currencies and only M0 (monthly average) data.

        Args:
            date_range: (start_date, end_date) inclusive
            currencies: List of ISO 4217 currency codes
            base_currency: Must be None or "CHF"

        Returns:
            Dict mapping currency → [(date, foreign_cur, "CHF", rate_per_1_unit), ...]
        """
        if base_currency is not None and base_currency != "CHF":
            raise ValueError(f"SNB only supports CHF as base currency, got {base_currency}")

        await self._ensure_currency_map()
        assert self._iso_to_d1 is not None and self._d1_to_iso is not None

        start_date, end_date = date_range
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {}

        # Resolve which D1 codes we need
        d1_codes_needed: list[str] = []
        for currency in currencies:
            if currency == "CHF":
                continue
            d1_code = self._iso_to_d1.get(currency)
            if d1_code is None:
                logger.warning(f"Currency {currency} not supported by SNB, skipping")
                results[currency] = []
                continue
            d1_codes_needed.append(d1_code)

        if not d1_codes_needed:
            return results

        # Build filtered JSON request
        # dimSel=D0(M0),D1(EUR1,CNY100,...)  → only monthly average, only requested currencies
        d1_sel = ",".join(d1_codes_needed)
        dim_sel = f"D0(M0),D1({d1_sel})"

        # fromDate/toDate use YYYY-MM format for monthly data
        from_date = f"{start_date.year}-{start_date.month:02d}"
        to_date = f"{end_date.year}-{end_date.month:02d}"

        url = f"{self.BASE_URL}/{self.DATASET}/data/json/en"
        params = {
            "dimSel": dim_sel,
            "fromDate": from_date,
            "toDate": to_date,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch FX rates from SNB: {e}")
            raise FXServiceError(f"SNB API error: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse SNB JSON response: {e}")
            raise FXServiceError(f"Unexpected SNB response: {e}") from e

        # Parse JSON timeseries
        results = self._parse_json(data, start_date, end_date)
        return results

    def _parse_json(
        self,
        data: dict,
        start_date: date,
        end_date: date,
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Parse SNB JSON response.

        Each timeseries entry has:
          - metadata.key like "EPB@SNB.devkum{M0,CNY100}" → extract D1 id
          - values: [{"date": "2025-02", "value": 11.18798}, ...]
        """
        assert self._d1_to_iso is not None
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {}

        for ts in data.get("timeseries", []):
            # Extract D1 id from metadata key: "EPB@SNB.devkum{M0,CNY100}" → "CNY100"
            meta_key = ts.get("metadata", {}).get("key", "")
            d1_id = self._extract_d1_from_key(meta_key)
            if d1_id is None:
                # Fallback: try to extract from header
                d1_id = self._extract_d1_from_header(ts.get("header", []))
            if d1_id is None or d1_id not in self._d1_to_iso:
                logger.debug(f"SNB: skipping timeseries with unrecognized key: {meta_key}")
                continue

            iso_code, multiplier = self._d1_to_iso[d1_id]
            rates: list[tuple[date, str, str, Decimal]] = []

            for point in ts.get("values", []):
                date_str = point.get("date", "")
                raw_value = point.get("value")
                if raw_value is None:
                    continue

                try:
                    # Parse date: "YYYY-MM" → 1st of month
                    if len(date_str) == 7:
                        year, month = int(date_str[:4]), int(date_str[5:7])
                        rate_date = date(year, month, 1)
                    elif len(date_str) == 10:
                        rate_date = date.fromisoformat(date_str)
                    else:
                        continue

                    # Filter to requested range (1st-of-month comparison)
                    if rate_date < start_date.replace(day=1) or rate_date > end_date:
                        continue

                    # Normalize: SNB gives rate for {multiplier} units → per 1 unit
                    raw_rate = Decimal(str(raw_value))
                    if raw_rate == 0:
                        continue

                    rate_per_unit = raw_rate / Decimal(str(multiplier))
                    rates.append((rate_date, iso_code, "CHF", rate_per_unit))

                except (ValueError, ZeroDivisionError) as e:
                    logger.debug(f"SNB: skipping invalid value {raw_value} for {date_str}: {e}")
                    continue

            if rates:
                results[iso_code] = rates
                logger.debug(f"Parsed {len(rates)} rates for {iso_code} from SNB")

        return results

    @staticmethod
    def _extract_d1_from_key(meta_key: str) -> str | None:
        """Extract D1 id from metadata key like 'EPB@SNB.devkum{M0,CNY100}' → 'CNY100'."""
        m = re.search(r"\{([^}]+)\}", meta_key)
        if not m:
            return None
        parts = m.group(1).split(",")
        if len(parts) >= 2:
            return parts[1].strip()
        return None

    @staticmethod
    def _extract_d1_from_header(header: list[dict]) -> str | None:  # pragma: no cover
        """Fallback: extract D1 id from header dimItem like 'Europe - EUR 1' → 'EUR1'."""
        for h in header:
            if h.get("dim", "").startswith("Currency"):
                dim_item = h.get("dimItem", "")
                m = re.search(r"([A-Z]{3})\s+(\d+)", dim_item)
                if m:
                    return f"{m.group(1)}{m.group(2)}"
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# DEBUG / EXPLORATION — run with: pipenv run python -m backend.app.services.fx_providers.snb
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    import sys

    async def _debug_dimensions():
        """Fetch and display the dynamic currency map from /dimensions."""
        provider = SNBProvider()
        SNBProvider._iso_to_d1 = None
        SNBProvider._d1_to_iso = None
        await provider._ensure_currency_map()
        print(f"[dimensions] {len(provider._iso_to_d1)} currencies mapped:")
        for iso, d1 in sorted(provider._iso_to_d1.items()):
            mult = provider._d1_to_iso[d1][1]
            print(f"    {iso:5s} → {d1:10s} (×{mult})")

    async def _debug_json_fetch():
        """Fetch filtered JSON for a few currencies and show structure."""
        url = "https://data.snb.ch/api/cube/devkum/data/json/en"
        params = {
            "dimSel": "D0(M0),D1(USD1,CNY100,EUR1)",
            "fromDate": "2026-01",
            "toDate": "2026-03",
        }
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            r = await client.get(url, params=params)
            data = r.json()
            ts_list = data.get("timeseries", [])
            print(f"[json_fetch] status={r.status_code}, timeseries_count={len(ts_list)}")
            for ts in ts_list:
                key = ts.get("metadata", {}).get("key", "?")
                values = ts.get("values", [])
                print(f"  key={key}, values={len(values)}")
                for v in values[:3]:
                    print(f"    {v}")

    async def _debug_test_parser():
        """Test the full fetch_rates pipeline — should show rates for USD, CNY, EUR, JPY."""
        provider = SNBProvider()
        SNBProvider._iso_to_d1 = None
        SNBProvider._d1_to_iso = None
        result = await provider.fetch_rates(
            (date(2025, 10, 1), date(2026, 3, 6)),
            ["USD", "CNY", "EUR", "JPY"],
        )
        for currency, rates in sorted(result.items()):
            print(f"[parser] {currency}: {len(rates)} rates")
            for r in rates:
                print(f"    {r}")
        cny_count = len(result.get("CNY", []))
        print(f"\n[parser] CNY rates: {cny_count}")
        print("[parser] ✅ CNY works!" if cny_count > 0 else "[parser] ❌ CNY broken")

    async def _debug_supported():
        """List all supported currencies (from API, not hardcoded)."""
        provider = SNBProvider()
        SNBProvider._iso_to_d1 = None
        SNBProvider._d1_to_iso = None
        currencies = await provider.get_supported_currencies()
        print(f"[supported] {len(currencies)} currencies:")
        for c in currencies:
            print(f"    {c}")

    async def _debug_dataset_check():
        """Check which SNB datasets exist."""
        datasets = ["devkut", "devkum", "devkua", "devkur", "devkub", "devkuw"]
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for ds in datasets:
                url = f"https://data.snb.ch/api/cube/{ds}/data/json/en"
                params = {"fromDate": "2026-02", "toDate": "2026-03"}
                try:
                    r = await client.get(url, params=params)
                    if r.status_code == 200:
                        data = r.json()
                        ts_count = len(data.get("timeseries", []))
                        print(f"[datasets] {ds}: status=200, timeseries={ts_count}")
                    else:
                        print(f"[datasets] {ds}: status={r.status_code}")
                except Exception as e:
                    print(f"[datasets] {ds}: ERROR {e}")

    tests = {
        "dimensions": _debug_dimensions,
        "json": _debug_json_fetch,
        "parser": _debug_test_parser,
        "supported": _debug_supported,
        "datasets": _debug_dataset_check,
    }

    test_name = sys.argv[1] if len(sys.argv) > 1 else "all"
    if test_name == "all":
        for name, fn in tests.items():
            print(f"\n{'=' * 60}")
            print(f"  {name}")
            print(f"{'=' * 60}")
            asyncio.run(fn())
    elif test_name in tests:
        asyncio.run(tests[test_name]())
    else:
        print(f"Unknown test: {test_name}")
        print(f"Available: {', '.join(tests.keys())}, all")
