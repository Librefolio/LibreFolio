"""S3 (project 76; the developer, 20/11/2026: «Sì, nella 76»): a search result may carry the asset's icon.

A price provider that knows an asset's icon when it searches (CoinGecko's ``/search`` gives each coin's logo) puts it in
its result dict as ``"icon_url"``; the search (``AssetSearchService.search``) and the streamed search the web form reads
(``AssetSearchService.search_stream``) carry it to ``FAProviderSearchResultItem.icon_url`` — optional, None when absent,
so a provider that says nothing gives the result it gave before. An icon must be an ``http(s)`` address or a path of
this instance; anything else (another scheme, a blank, not a string) is dropped, quietly — it is decoration — and the
result stays.

The providers are this file's own (``_QuoteBaseFake`` of ``test_quote_base_suggestion.py``): no network.
"""

from __future__ import annotations

import pytest

from backend.app.db.models import IdentifierType
from backend.app.schemas.provider import FAProviderSearchResultItem
from backend.app.services.assets.search import AssetSearchService
from backend.test_scripts.test_services.test_quote_base_suggestion import _code, _hand_out, _QuoteBaseFake, _sse, _unique, private_cooldowns  # noqa: F401 — the fixture is used by name
from backend.test_scripts.test_utils import print_section, print_success

LOGO = "https://coin-images.coingecko.com/coins/images/29850/large/pepe-token.jpeg"
LOCAL = "/api/v1/uploads/plugin/asset/cssscraper.png"


def _row(identifier: str, icon: object = ...) -> dict:
    row = {"identifier": identifier, "identifier_type": IdentifierType.TICKER, "display_name": f"S3 {identifier}", "currency": "EUR", "type": "CRYPTO"}
    if icon is not ...:
        row["icon_url"] = icon
    return row


ROWS = [
    _row("S3-REMOTE", LOGO),
    _row("S3-LOCAL", LOCAL),
    _row("S3-WITHOUT"),
    _row("S3-SCRIPT", "javascript:alert(1)"),
    _row("S3-DATA", "data:image/png;base64,AAAA"),
    _row("S3-BLANK", "   "),
    _row("S3-NUMBER", 42),
]
EXPECTED = {"S3-REMOTE": LOGO, "S3-LOCAL": LOCAL, "S3-WITHOUT": None, "S3-SCRIPT": None, "S3-DATA": None, "S3-BLANK": None, "S3-NUMBER": None}


def test_s3_a_search_result_has_an_optional_icon():
    print_section("S3 1: the schema")
    assert FAProviderSearchResultItem.model_fields["icon_url"].default is None
    item = FAProviderSearchResultItem(identifier="X", identifier_type="TICKER", display_name="X", provider_code="p")
    assert item.icon_url is None and item.model_dump(mode="json")["icon_url"] is None
    print_success("icon_url: optional, null when absent")


@pytest.mark.asyncio
async def test_s3_the_search_carries_a_valid_icon_and_drops_another(monkeypatch: pytest.MonkeyPatch):
    print_section("S3 2: the search")
    code = _code()
    _hand_out(monkeypatch, _QuoteBaseFake(code, items=ROWS))

    response = await AssetSearchService.search(_unique("s3"), provider_codes=[code])

    assert (response.providers_queried, response.providers_with_errors) == ([code], []), "the provider answered, an invalid icon is no error"
    got = {item.identifier: item.icon_url for item in response.results}
    assert got == EXPECTED, f"icons: {got}"
    print_success("http(s) and local paths kept, the rest dropped, every result kept")


@pytest.mark.asyncio
async def test_s3_the_streamed_search_carries_the_same_icons(monkeypatch: pytest.MonkeyPatch):
    print_section("S3 3: the streamed search")
    code = _code()
    _hand_out(monkeypatch, _QuoteBaseFake(code, items=ROWS))

    events = await _sse(AssetSearchService.search_stream(_unique("s3-stream"), provider_codes=[code]))

    (answer,) = [event for event in events if event.get("event") == "provider_results" and event.get("provider_code") == code]
    got = {result["identifier"]: result.get("icon_url", "(missing)") for result in answer["results"]}
    assert got == EXPECTED, f"streamed icons: {got}"
    print_success("the stream as the plain search")
