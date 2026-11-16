"""
Banco Central do Brasil (BCB) FX rate provider.

This provider fetches the PTAX closing bulletin of the Banco Central do Brasil: for about 150 currencies, the parity
against the US dollar (paridade), and the real (BRL) against the dollar (cotação). USD is the base of the provider:
every currency is one step from the dollar, and BRL is one of them.

Licence: the PTAX dataset («Taxas de câmbio — todos os boletins diários», https://dadosabertos.bcb.gov.br, package
``taxas-de-cambio-todos-os-boletins-diarios``) is published under the Open Data Commons Open Database License (ODbL):
attribution «Source: Banco Central do Brasil, PTAX, ODbL», in the provider's description. The bank says the parities come
from Refinitiv (except USD/BRL) and are not guaranteed by it. The CSV read here (feed C) gives the same values as the
dataset's OData API; the developer's decision (lane 75, 16/11/2026): use it under the dataset's ODbL.

Path used (feed C, see ``studio-BCB.md`` in the developer journal):
``https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?method=gerarCSVFechamentoMoedaNoPeriodo&ChkMoeda=<id>&DATAINI=dd/mm/yyyy&DATAFIM=dd/mm/yyyy``
— one request per currency for any range, its whole history in one answer (USD from 1984: ~570 KB, ~2.6 s). The
``ChkMoeda`` ids are internal: ``SERIES`` maps each ISO code to its id, BCB code and symbol, built once by the journal
script ``bcb_chkmoeda_table.py`` from the query form, the currency registry and one probe per currency (16/11/2026); every
answer is checked against them (``_parse.read_rows``). The path is not documented and can change.

Measured on 16/11/2026:

- Type A: paridade = units per 1 USD → ``(d, 'USD', CUR, v)``; type B (EUR, GBP, AUD, XDR…): USD per 1 unit →
  ``(d, CUR, 'USD', v)``. The type is read row by row (NGN was B until 04/08/1998). The value is the mean of compra and
  venda; the cotação (BRL per unit) is used for BRL only (from the USD series): for small units it is rounded.
- History from 01/02/1999 (``FLOOR``): before, two bulletins a day, a cotação not in reais before 07/1994, wrong types.
  VES from 04/10/2021 (÷10⁶ inside the same code). SLL is published in old leones: stored as SLE ÷ 1000
  (``SLL_PER_SLE``). Dropped: MRO (stale), XAU (per gram), CNH (not ISO).
- No data in the range, or an unknown id: HTTP 200 with an HTML page (``msgErro``): see ``_parse.check_html``.
- Brazilian business days only; the closing bulletin comes out around 13:00–13:10 Brasília time.

Reference: the open-source python-bcb (MIT) reads the same feed.
"""

import asyncio
from datetime import date
from decimal import Decimal
from typing import Literal, NamedTuple

import httpx

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXProviderStartDate, FXRateLimitedError, FXRateProvider, FXServiceError, raise_if_fx_rate_limited
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx_providers.bcb import _parse
from backend.app.services.platform.provider_registry import register_provider

logger = get_logger(__name__)

#: The first day the feed is clean for every currency (studio-BCB.md §2).
FLOOR = date(1999, 2, 1)
#: BCB publishes the Sierra Leone leone in old leones (SLL); the ISO list has only SLE: 1 SLE = 1 000 SLL.
SLL_PER_SLE = Decimal(1000)


class BcbSeries(NamedTuple):
    """One currency of feed C: its ``ChkMoeda`` id, the BCB code and symbol its rows carry, the first day read and the
    divisor that turns BCB's unit into the ISO currency's."""

    chk_moeda: int
    bcb_code: int
    symbol: str
    first_day: date = FLOOR
    divisor: Decimal = Decimal(1)


#: The dollar's series: USD itself is the base, and BRL is read from its cotação.
USD_SERIES = BcbSeries(61, 220, "USD")

#: ISO code → feed C series, from ``bcb_chkmoeda_table.py`` (journal, 16/11/2026). USD and BRL are not here.
# fmt: off
SERIES: dict[str, BcbSeries] = {
    "AED": BcbSeries(43, 145, "AED"),
    "AFN": BcbSeries(1, 5, "AFN"),
    "ALL": BcbSeries(105, 490, "ALL"),
    "AMD": BcbSeries(71, 275, "AMD"),
    "AOA": BcbSeries(139, 635, "AOA"),
    "ARS": BcbSeries(156, 706, "ARS"),
    "AUD": BcbSeries(45, 150, "AUD"),
    "AWG": BcbSeries(76, 328, "AWG"),
    "AZN": BcbSeries(130, 607, "AZN"),
    "BBD": BcbSeries(51, 175, "BBD"),
    "BDT": BcbSeries(202, 905, "BDT"),
    "BHD": BcbSeries(31, 105, "BHD"),
    "BIF": BcbSeries(84, 365, "BIF"),
    "BMD": BcbSeries(47, 160, "BMD"),
    "BND": BcbSeries(53, 185, "BND"),
    "BOB": BcbSeries(9, 30, "BOB"),
    "BSD": BcbSeries(46, 155, "BSD"),
    "BTN": BcbSeries(149, 665, "BTN"),
    "BWP": BcbSeries(167, 755, "BWP"),
    "BYN": BcbSeries(2432, 831, "BYN"),
    "BZD": BcbSeries(52, 180, "BZD"),
    "CAD": BcbSeries(48, 165, "CAD"),
    "CDF": BcbSeries(83, 363, "CDF"),
    "CHF": BcbSeries(97, 425, "CHF"),
    "CLF": BcbSeries(2392, 197, "CLF"),
    "CLP": BcbSeries(158, 715, "CLP"),
    "CNY": BcbSeries(178, 795, "CNY"),
    "COP": BcbSeries(159, 720, "COP"),
    "COU": BcbSeries(2512, 721, "COU"),
    "CRC": BcbSeries(11, 40, "CRC"),
    "CUP": BcbSeries(160, 725, "CUP"),
    "CVE": BcbSeries(72, 295, "CVE"),
    "CZK": BcbSeries(21, 75, "CZK"),
    "DJF": BcbSeries(90, 390, "DJF"),
    "DKK": BcbSeries(15, 55, "DKK"),
    "DOP": BcbSeries(161, 730, "DOP"),
    "DZD": BcbSeries(29, 95, "DZD"),
    "EGP": BcbSeries(114, 535, "EGP"),
    "ERN": BcbSeries(137, 625, "ERN"),
    "ETB": BcbSeries(3, 9, "ETB"),
    "EUR": BcbSeries(222, 978, "EUR"),
    "FJD": BcbSeries(56, 200, "FJD"),
    "FKP": BcbSeries(116, 545, "FKP"),
    "GBP": BcbSeries(115, 540, "GBP"),
    "GEL": BcbSeries(103, 482, "GEL"),
    "GHS": BcbSeries(10, 35, "GHS"),
    "GIP": BcbSeries(113, 530, "GIP"),
    "GMD": BcbSeries(28, 90, "GMD"),
    "GNF": BcbSeries(92, 398, "GNF"),
    "GTQ": BcbSeries(170, 770, "GTQ"),
    "GYD": BcbSeries(49, 170, "GYD"),
    "HKD": BcbSeries(57, 205, "HKD"),
    "HNL": BcbSeries(106, 495, "HNL"),
    "HTG": BcbSeries(98, 440, "HTG"),
    "HUF": BcbSeries(80, 345, "HUF"),
    "IDR": BcbSeries(194, 865, "IDR"),
    "ILS": BcbSeries(197, 880, "ILS"),
    "INR": BcbSeries(193, 860, "INR"),
    "IQD": BcbSeries(33, 115, "IQD"),
    "IRR": BcbSeries(182, 815, "IRR"),
    "ISK": BcbSeries(18, 60, "ISK"),
    "JMD": BcbSeries(63, 230, "JMD"),
    "JOD": BcbSeries(35, 125, "JOD"),
    "JPY": BcbSeries(101, 470, "JPY"),
    "KES": BcbSeries(216, 950, "KES"),
    "KGS": BcbSeries(199, 892, "KGS"),
    "KHR": BcbSeries(184, 825, "KHR"),
    "KMF": BcbSeries(85, 368, "KMF"),
    "KRW": BcbSeries(212, 930, "KRW"),
    "KWD": BcbSeries(30, 100, "KWD"),
    "KYD": BcbSeries(54, 190, "KYD"),
    "KZT": BcbSeries(205, 913, "KZT"),
    "LAK": BcbSeries(175, 780, "LAK"),
    "LBP": BcbSeries(119, 560, "LBP"),
    "LKR": BcbSeries(192, 855, "LKR"),
    "LRD": BcbSeries(64, 235, "LRD"),
    "LSL": BcbSeries(128, 603, "LSL"),
    "LYD": BcbSeries(36, 130, "LYD"),
    "MAD": BcbSeries(42, 139, "MAD"),
    "MDL": BcbSeries(108, 503, "MDL"),
    "MGA": BcbSeries(2331, 406, "MGA"),
    "MKD": BcbSeries(37, 132, "MKD"),
    "MMK": BcbSeries(171, 775, "MMK"),
    "MNT": BcbSeries(207, 915, "MNT"),
    "MOP": BcbSeries(152, 685, "MOP"),
    "MRU": BcbSeries(2452, 671, "MRU"),
    "MUR": BcbSeries(189, 840, "MUR"),
    "MVR": BcbSeries(195, 870, "MVR"),
    "MWK": BcbSeries(168, 760, "MWK"),
    "MXN": BcbSeries(165, 741, "MXN"),
    "MYR": BcbSeries(185, 828, "MYR"),
    "MZN": BcbSeries(136, 622, "MZN"),
    "NAD": BcbSeries(50, 173, "NAD"),
    "NGN": BcbSeries(138, 630, "NGN"),
    "NIO": BcbSeries(14, 51, "NIO"),
    "NOK": BcbSeries(19, 65, "NOK"),
    "NPR": BcbSeries(190, 845, "NPR"),
    "NZD": BcbSeries(66, 245, "NZD"),
    "OMR": BcbSeries(180, 805, "OMR"),
    "PAB": BcbSeries(6, 20, "PAB"),
    "PEN": BcbSeries(147, 660, "PEN"),
    "PGK": BcbSeries(173, 778, "PGK"),
    "PHP": BcbSeries(162, 735, "PHP"),
    "PKR": BcbSeries(196, 875, "PKR"),
    "PLN": BcbSeries(221, 975, "PLN"),
    "PYG": BcbSeries(99, 450, "PYG"),
    "QAR": BcbSeries(179, 800, "QAR"),
    "RON": BcbSeries(110, 506, "RON"),
    "RSD": BcbSeries(38, 133, "RSD"),
    "RUB": BcbSeries(187, 830, "RUB"),
    "RWF": BcbSeries(96, 420, "RWF"),
    "SAR": BcbSeries(183, 820, "SAR"),
    "SBD": BcbSeries(67, 250, "SBD"),
    "SCR": BcbSeries(191, 850, "SCR"),
    "SDG": BcbSeries(39, 134, "SDG"),
    "SEK": BcbSeries(20, 70, "SEK"),
    "SGD": BcbSeries(55, 195, "SGD"),
    "SHP": BcbSeries(121, 570, "SHP"),
    "SLE": BcbSeries(107, 500, "SLL", divisor=SLL_PER_SLE),
    "SOS": BcbSeries(218, 960, "SOS"),
    "SRD": BcbSeries(68, 255, "SRD"),
    "SSP": BcbSeries(2372, 136, "SSP"),
    "STN": BcbSeries(2492, 149, "STN"),
    "SVC": BcbSeries(12, 45, "SVC"),
    "SYP": BcbSeries(122, 575, "SYP"),
    "SZL": BcbSeries(124, 585, "SZL"),
    "THB": BcbSeries(5, 15, "THB"),
    "TJS": BcbSeries(188, 835, "TJS"),
    "TMT": BcbSeries(131, 608, "TMT"),
    "TND": BcbSeries(40, 135, "TND"),
    "TOP": BcbSeries(151, 680, "TOP"),
    "TRY": BcbSeries(142, 642, "TRY"),
    "TTD": BcbSeries(58, 210, "TTD"),
    "TWD": BcbSeries(141, 640, "TWD"),
    "TZS": BcbSeries(215, 946, "TZS"),
    "UAH": BcbSeries(100, 460, "UAH"),
    "UGX": BcbSeries(217, 955, "UGX"),
    "UYU": BcbSeries(166, 745, "UYU"),
    "UZS": BcbSeries(200, 893, "UZS"),
    "VES": BcbSeries(2472, 27, "VES", first_day=date(2021, 10, 4)),
    "VND": BcbSeries(69, 260, "VND"),
    "VUV": BcbSeries(210, 920, "VUV"),
    "WST": BcbSeries(2412, 912, "WST"),
    "XAF": BcbSeries(86, 370, "XAF"),
    "XCD": BcbSeries(59, 215, "XCD"),
    "XCG": BcbSeries(2552, 326, "XCG"),
    "XDR": BcbSeries(41, 138, "XDR"),
    "XOF": BcbSeries(87, 372, "XOF"),
    "XPF": BcbSeries(88, 380, "XPF"),
    "YER": BcbSeries(181, 810, "YER"),
    "ZAR": BcbSeries(176, 785, "ZAR"),
    "ZMW": BcbSeries(2352, 766, "ZMW"),
}
# fmt: on


@register_provider(FXProviderRegistry)
class BCBProvider(FXRateProvider):
    """
    Banco Central do Brasil FX rate provider.

    Provides the PTAX closing parities with USD as base currency, for about 150 currencies, and BRL per USD.
    Data source: BCB PTAX bulletin, feed C (one CSV per currency and period).

    Coverage: fixed table (152 currencies plus USD and BRL on 2026-11-16).
    Update frequency: daily, Brazilian business days, around 13:10 Brasília time.
    """

    FEED_URL = "https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do"
    SERIES = SERIES
    #: Pause between two requests of one call (D9: an explicit, slow pace).
    PAUSE_SECONDS = 1.2

    @property
    def code(self) -> str:
        return "BCB"

    @property
    def provider_code(self) -> str:
        """Alias for code (required by unified registry)."""
        return self.code

    @property
    def name(self) -> str:
        return "Banco Central do Brasil"

    @property
    def icon(self) -> str | None:
        return "https://www.bcb.gov.br/favicon.ico"

    @property
    def docs_url(self) -> str | None:
        return "/mkdocs/user/fx/providers/bcb/"

    @property
    def description_i18n(self) -> dict[str, str]:
        return {
            "en": "Banco Central do Brasil — the PTAX closing bulletin: about 150 currencies against the US dollar, and the Brazilian real. Brazilian business days, history from 1999. Source: Banco Central do Brasil, PTAX, ODbL. Parities other than USD/BRL come from Refinitiv and are not guaranteed by the bank.",
            "it": "Banco Central do Brasil — il bollettino di chiusura PTAX: circa 150 valute contro il dollaro USA, e il real brasiliano. Giorni lavorativi brasiliani, storia dal 1999. Fonte: Banco Central do Brasil, PTAX, ODbL. Le parità diverse da USD/BRL vengono da Refinitiv e la banca non le garantisce.",
            "fr": "Banco Central do Brasil — le bulletin de clôture PTAX : environ 150 devises contre le dollar américain, et le réal brésilien. Jours ouvrables brésiliens, historique depuis 1999. Source : Banco Central do Brasil, PTAX, ODbL. Les parités autres que USD/BRL viennent de Refinitiv et ne sont pas garanties par la banque.",
            "es": "Banco Central do Brasil — el boletín de cierre PTAX: unas 150 monedas contra el dólar estadounidense, y el real brasileño. Días hábiles brasileños, historial desde 1999. Fuente: Banco Central do Brasil, PTAX, ODbL. Las paridades distintas de USD/BRL vienen de Refinitiv y el banco no las garantiza.",
        }

    @property
    def warning_i18n(self) -> dict[str, str]:
        return {
            "en": "BCB rates are the mean of the buying and selling PTAX closing rates. Their base is the US dollar: every route through BCB goes through USD. The Sierra Leone leone is published in old leones and stored as SLE (divided by 1000).",
            "it": "I tassi BCB sono la media dei tassi PTAX di chiusura in acquisto e in vendita. La loro base è il dollaro USA: ogni route attraverso BCB passa per USD. Il leone della Sierra Leone è pubblicato in leoni vecchi e salvato come SLE (diviso per 1000).",
            "fr": "Les taux BCB sont la moyenne des taux PTAX de clôture à l'achat et à la vente. Leur base est le dollar américain : toute route par BCB passe par l'USD. Le leone de Sierra Leone est publié en anciens leones et enregistré comme SLE (divisé par 1000).",
            "es": "Los tipos BCB son la media de los tipos PTAX de cierre de compra y de venta. Su base es el dólar estadounidense: toda ruta por BCB pasa por USD. El leone de Sierra Leona se publica en leones antiguos y se guarda como SLE (dividido por 1000).",
        }

    @property
    def warning_level(self) -> Literal["info", "warning"]:
        return "info"

    @property
    def base_currency(self) -> str:
        return "USD"

    @property
    def test_currencies(self) -> list[str]:
        return ["USD", "BRL", "EUR", "GBP", "JPY", "NGN"]

    async def get_supported_currencies(self) -> list[str]:
        """The fixed table, plus USD and BRL: no request (the ChkMoeda ids cannot be discovered at runtime)."""
        return sorted({*self.SERIES, self.base_currency, "BRL"})

    async def fetch_rates(self, date_range: tuple[FXProviderStartDate, date], currencies: list[str], base_currency: str | None = None) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch each asked currency's PTAX closings, one request per currency, in series with a pause: type A rows as
        ``(d, 'USD', CUR, units per USD)``, type B as ``(d, CUR, 'USD', USD per unit)``, BRL as ``(d, 'USD', 'BRL', BRL
        per USD)`` from the dollar's series.

        A currency whose answer fails or is not its CSV is skipped with one warning (XRL-H09); a value that is no number
        loses its day (X-R50). A 429 stops the call.

        Raises:
            ValueError: base_currency is neither None nor USD
            FXRateLimitedError: the bank refused for too many requests
        """
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(f"BCB provider only supports USD as base currency, got {base_currency}")

        start_date, end_date = date_range
        wanted = sorted({c for c in currencies if c != self.base_currency and (c in self.SERIES or c == "BRL")})
        results: dict[str, list[tuple[date, str, str, Decimal]]] = {currency: [] for currency in wanted}
        asked = 0
        for currency in wanted:
            series = USD_SERIES if currency == "BRL" else self.SERIES[currency]
            start = series.first_day if start_date == "min" else max(start_date, series.first_day)
            if start > end_date:
                continue
            if asked:
                await asyncio.sleep(self.PAUSE_SECONDS)
            asked += 1
            try:
                rows = await self._fetch_rows(currency, series, start, end_date)
            except FXRateLimitedError:
                raise
            except FXServiceError as e:
                logger.warning(f"BCB fetch failed for {currency}, skipping: {e}")
                continue
            results[currency] = self._to_rates(rows, currency, series)
        return results

    @staticmethod
    def _read_rows(body: str, series: BcbSeries, start: date, end: date) -> list[_parse.BcbRow]:
        return _parse.read_rows(body, series.bcb_code, series.symbol, start, end)

    @staticmethod
    def _to_rates(rows: list[_parse.BcbRow], currency: str, series: BcbSeries) -> list[tuple[date, str, str, Decimal]]:
        """Each row as a rate in the bank's direction; a row whose value is unreadable loses its day."""
        rates = []
        for row in rows:
            if currency == "BRL":
                value = _parse.mean(row.cotacao_compra, row.cotacao_venda)
                pair = ("USD", "BRL")
            else:
                parity = _parse.mean(row.paridade_compra, row.paridade_venda)
                value = parity / series.divisor if parity is not None else None
                pair = ("USD", currency) if row.kind == "A" else (currency, "USD")
            if value is None:
                logger.debug(f"BCB: skipping a day with no readable value for {currency} on {row.day}")
                continue
            rates.append((row.day, *pair, value))
        return rates

    async def _fetch_rows(self, currency: str, series: BcbSeries, start: date, end: date) -> list[_parse.BcbRow]:
        params = {"method": "gerarCSVFechamentoMoedaNoPeriodo", "ChkMoeda": str(series.chk_moeda), "DATAINI": start.strftime("%d/%m/%Y"), "DATAFIM": end.strftime("%d/%m/%Y")}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(self.FEED_URL, params=params)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise_if_fx_rate_limited(e, self.provider_code)
            raise FXServiceError(f"BCB request failed for {currency}: {e}") from e
        body = response.content.decode("latin-1")
        if _parse.is_html(body, response.headers.get("content-type", "")):
            _parse.check_html(body, currency, start, end)
            return []
        return self._read_rows(body, series, start, end)
