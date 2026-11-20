"""
Banco de México (BANXICO) FX rate provider.

This provider reads the Banco de México SIE API: the FIX of the US dollar and the daily quotes of the SDR basket
currencies, every series «MXN per 1 unit of the foreign currency». MXN is the base of the provider. The API needs a
free token (64 characters), which the administrator asks the bank for and sets in the plugin settings: it travels only
in the ``Bmx-Token`` header, never in the URL.

API documentation: https://www.banxico.org.mx/SieAPIRest/service/v1/ (``doc/consultaDatosSerieRango``).
Terms: «Salvedad de uso» (https://www.banxico.org.mx/footer-es/salvedad-politicas-uso-banco-.html) — the bank grants a
general authorisation to reproduce and use its data, citing the source and the bank's web address.

Series (the SIE catalogue, read row by row on 19/11/2026, lane 75):

- ``SF43718``: USD, the FIX, dated on the day it is determined (12:00, Mexico City), from 1991-11-12, table CF102. Not
  ``SF60653``, the same FIX dated on its settlement day.
- table CF307, from 2018-07-31: ``SF46410`` EUR, ``SF46406`` JPY (four decimals, 0.1160), ``SF46407`` GBP,
  ``SF290383`` CNY, ``SF46411`` the SDR (XDR).

Measured on 19/11/2026:

- ``GET …/series/{id1,id2,…}/datos/{yyyy-MM-dd}/{yyyy-MM-dd}`` answers up to 20 series in one request (the doc), as
  ``{"bmx": {"series": [{"idSerie", "titulo", "datos": [{"fecha": "dd/MM/yyyy", "dato": "18.5525"}]}]}}``. A day
  without a publication (a Mexican bank holiday) is ``"dato": "N/E"``.
- Without a valid token: HTTP 400, ``{"error": {"mensaje": "Token inválido", …}}``. The connection with ``httpx``
  works (the API asks for TLS 1.3).
- Limits (the doc): 200 requests every 5 minutes and 10 000 a day. A request over the limit is HTTP 400 with the
  header ``Bmx-secondsToReset``, mapped here to ``FXRateLimitedError`` with that wait.
- Budget: one request per sync, for every currency and the whole range, «min» included (❔ with a real token: the
  largest range one request accepts was not measured).
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXNotConfiguredError, FXProviderStartDate, FXRateLimitedError, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_registry import register_provider
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingScope, SettingType

logger = get_logger(__name__)

API_ROOT = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"
#: The series of each currency, «MXN per 1 unit» (see the module docstring).
SERIES: dict[str, str] = {
    "USD": "SF43718",
    "EUR": "SF46410",
    "JPY": "SF46406",
    "GBP": "SF46407",
    "CNY": "SF290383",
    "XDR": "SF46411",
}
#: The first FIX of ``SF43718``; the CF307 series start on 2018-07-31 and simply answer from there.
FIRST_DAY = date(1991, 11, 12)
#: The header the bank names for the wait after a request over its limit, in seconds.
RESET_HEADER = "Bmx-secondsToReset"
#: A value with thousands separators, «1,234.5»: the API's numbers use a dot for decimals.
_THOUSANDS = re.compile(r"\d{1,3}(,\d{3})+(\.\d+)?")

_CURRENCIES = sorted([*SERIES, "MXN"])


@register_provider(FXProviderRegistry)
class BanxicoProvider(FXRateProvider):
    """
    Banco de México FX rate provider.

    Provides the FIX of the US dollar and the daily quotes of EUR, JPY, GBP, CNY and the SDR with MXN as base currency
    (MXN per unit of each foreign currency). Data source: the SIE API, one request for every currency. Needs a token.

    Coverage: a fixed table of 6 currencies plus MXN.
    Update frequency: every Mexican banking day, the FIX at 12:00 Mexico City time.
    """

    settings_fields = (
        PluginSettingField(
            key="token",
            type=SettingType.STRING,
            scope=SettingScope.SYSTEM,
            secret=True,
            required=True,
            label="API token (Bmx-Token)",
            description="The free token of the Banco de México SIE API, 64 characters, asked for on the bank's site.",
            label_key="pluginSettings.fx.BANXICO.label.token",
            description_key="pluginSettings.fx.BANXICO.description.token",
            missing_key="pluginSettings.fx.BANXICO.missing.token",
        ),
    )

    @property
    def code(self) -> str:
        return "BANXICO"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Banco de México"

    @property
    def icon(self) -> str | None:
        return "https://www.banxico.org.mx/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/banxico/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Banco de México — the official FIX of the US dollar against MXN, from 1991, and the daily quotes of EUR, JPY, GBP, CNY and the SDR (XDR) against MXN, from 2018. Needs a free API token from the bank. Source: Banco de México (banxico.org.mx).",
            "it": "Banco de México — il FIX ufficiale del dollaro USA contro MXN, dal 1991, e le quotazioni giornaliere di EUR, JPY, GBP, CNY e del DSP (XDR) contro MXN, dal 2018. Serve un token API gratuito della banca. Fonte: Banco de México (banxico.org.mx).",
            "fr": "Banco de México — le FIX officiel du dollar américain contre MXN, depuis 1991, et les cotations quotidiennes de l'EUR, du JPY, de la GBP, du CNY et du DTS (XDR) contre MXN, depuis 2018. Nécessite un jeton API gratuit de la banque. Source : Banco de México (banxico.org.mx).",
            "es": "Banco de México — el FIX oficial del dólar estadounidense contra MXN, desde 1991, y las cotizaciones diarias del EUR, JPY, GBP, CNY y el DEG (XDR) contra MXN, desde 2018. Requiere un token gratuito de la API del banco. Fuente: Banco de México (banxico.org.mx).",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "USD is the FIX, determined at 12:00 Mexico City time on each banking day and dated that day (not the day the DOF publishes it). The other currencies are the daily quotes of Banxico table CF307, from 31/07/2018; JPY has four decimals (0.1160 MXN), so its rate moves in steps of about 0.1%. No rate on Mexican bank holidays.",
            "it": "USD è il FIX, determinato alle 12:00 di Città del Messico in ogni giorno bancario e datato quel giorno (non il giorno in cui lo pubblica il DOF). Le altre valute sono le quotazioni giornaliere della tabella CF307 di Banxico, dal 31/07/2018; JPY ha quattro decimali (0,1160 MXN), quindi il suo tasso si muove a passi di circa lo 0,1%. Nessun tasso nei festivi bancari messicani.",
            "fr": "USD est le FIX, déterminé à 12h00 heure de Mexico chaque jour bancaire et daté de ce jour (pas du jour où le DOF le publie). Les autres devises sont les cotations quotidiennes du tableau CF307 de Banxico, depuis le 31/07/2018 ; le JPY a quatre décimales (0,1160 MXN) : son taux varie par pas d'environ 0,1 %. Aucun taux les jours fériés bancaires mexicains.",
            "es": "USD es el FIX, determinado a las 12:00 hora de Ciudad de México cada día bancario y fechado ese día (no el día en que lo publica el DOF). Las demás monedas son las cotizaciones diarias del cuadro CF307 de Banxico, desde el 31/07/2018; el JPY tiene cuatro decimales (0,1160 MXN), así que su tipo se mueve en pasos de alrededor del 0,1 %. Sin tipo en los días inhábiles bancarios de México.",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        # Facts worth knowing (which FIX, which date, JPY's step), not a data limit that misleads: info (lane 75)
        return "info"

    @property
    def base_currency(self) -> str:
        return "MXN"

    @property
    def test_currencies(self) -> list[str]:
        return ["MXN", "USD", "EUR", "JPY"]

    @property
    def fallback_currencies(self) -> list[str]:
        return list(_CURRENCIES)

    async def get_supported_currencies(self) -> list[str]:
        """The fixed table, plus MXN: no request (the catalogue of SIE has no list of these series to read)."""
        return list(_CURRENCIES)

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch every asked currency in one request on the SIE API: ``(day, CUR, 'MXN', MXN per 1 CUR)``.

        Every value keeps the day the bank gives it (D2). «N/E» or a value that is no positive number loses its day only
        (X-R50). A currency with no series answers an empty list and is not asked.

        Raises:
            ValueError: base_currency is neither None nor MXN
            FXNotConfiguredError: no token is set
            FXRateLimitedError: the bank refused for too many requests (HTTP 429, or 400 with ``Bmx-secondsToReset``)
            FXServiceError: the token was refused, the request failed, or the answer is not the series JSON
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"Banco de México provider only supports MXN as base currency, got {base_currency}")

        start_date, end_date = date_range
        request_start = FIRST_DAY if start_date == "min" else max(start_date, FIRST_DAY)
        asked = sorted({c for c in currencies if c != self.base_currency})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in asked}
        wanted = [currency for currency in asked if currency in SERIES]
        if not wanted or request_start > end_date:
            return results

        token = self.settings.secret("token")
        if not token:
            raise FXNotConfiguredError(self.provider_code, ["token"])

        currency_of = {SERIES[currency]: currency for currency in wanted}
        url = f"{API_ROOT}/{','.join(SERIES[currency] for currency in wanted)}/datos/{request_start.isoformat()}/{end_date.isoformat()}"
        for serie in await self._get_series(url, token):
            currency = currency_of.get(serie.get("idSerie"))
            if currency is None:
                continue
            for row in serie.get("datos") or []:
                day = self._day(row)
                value = self._value(row)
                if day is None or value is None or not request_start <= day <= end_date:
                    continue
                results[currency].append((day, currency, self.base_currency, value))
        return results

    @staticmethod
    def _day(row: object) -> date | None:
        """``{"fecha": "13/11/2026"}`` as a date, or None."""
        try:
            return datetime.strptime(row["fecha"], "%d/%m/%Y").date()  # type: ignore[index]
        except (TypeError, KeyError, ValueError):
            logger.debug(f"BANXICO: skipping a row with no readable day: {row!r}")
            return None

    @staticmethod
    def _value(row: object) -> Decimal | None:
        """``{"dato": "18.5525"}`` as ``Decimal``; None for «N/E» or anything that is no positive number."""
        text = row.get("dato") if isinstance(row, dict) else None
        if not isinstance(text, str):
            return None
        text = text.strip()
        if _THOUSANDS.fullmatch(text):
            text = text.replace(",", "")
        try:
            value = Decimal(text)
        except InvalidOperation:
            return None
        return value if value.is_finite() and value > 0 else None

    async def _get_series(self, url: str, token: str) -> list[dict]:
        """GET ``url`` with the token in its header and return ``bmx.series``; anything else is an ``FXServiceError``."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, headers={"Bmx-Token": token, "Accept": "application/json"})
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            failed = getattr(e, "response", None)
            if failed is not None:
                self._raise_refusal(failed, e)
            logger.warning(f"Banco de México request failed: {e}")
            raise FXServiceError(f"Banco de México API error: {e}") from e

        body = response.text
        if body.lstrip()[:1] == "<":
            raise FXServiceError("Banco de México answer is an HTML page, not the SIE JSON (endpoint changed or request refused)")
        try:
            data = response.json()
        except ValueError:
            raise FXServiceError(f"Banco de México answer is not JSON: first bytes {body.lstrip()[:40]!r}") from None
        bmx = data.get("bmx") if isinstance(data, dict) else None
        series = bmx.get("series") if isinstance(bmx, dict) else None
        if not isinstance(series, list):
            raise FXServiceError("Banco de México answer has no bmx.series list (endpoint changed)")
        return [serie for serie in series if isinstance(serie, dict)]

    def _raise_refusal(self, response: httpx.Response, error: Exception) -> None:
        """A request over the limit (``Bmx-secondsToReset``), a refused token, or another refusal the bank explains in
        ``error.mensaje``: the error that says which. Nothing raised for an answer without either."""
        reset = response.headers.get(RESET_HEADER)
        if reset is not None:
            try:
                retry_after: float | None = max(float(reset), 0.0)
            except ValueError:
                retry_after = None
            raise FXRateLimitedError(f"{self.provider_code}: too many requests (HTTP {response.status_code}, {RESET_HEADER})", retry_after=retry_after) from error
        try:
            message = str(response.json()["error"]["mensaje"])
        except (ValueError, KeyError, TypeError):
            return
        if "token" in message.lower():
            raise FXServiceError("Banco de México refused the API token: check the BANXICO token in the instance's plugin settings") from error
        logger.warning(f"Banco de México refused the request: HTTP {response.status_code}, {message!r}")
        raise FXServiceError(f"Banco de México API error (HTTP {response.status_code}): {message}") from error
