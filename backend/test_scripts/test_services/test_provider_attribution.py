"""A provider's attribution: the line its terms ask the interface to show with its prices (project 76, lot P4).

CoinGecko's terms ask every price it gives to be shown with «Powered by CoinGecko», prominent, linked to its site
(journal ``76_cryptoPrices/ricerca-cripto-prezzi.md`` §6). The contract pinned here:

1. ``FAProviderAttribution`` is typed: a short text and an ``https://`` link; anything else is refused.
2. The base provider has none; CoinGecko's is «Powered by CoinGecko» → https://www.coingecko.com/.
3. Every shipped provider's attribution is ``None`` or valid: a constant, built with no I/O and no setting.
4. ``FAProviderInfo`` carries it, ``None`` by default.

Pure: no database, no server, no network.
Red on HEAD: no such model, no such property.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.schemas.provider import FAProviderAttribution, FAProviderInfo
from backend.app.services.asset_source_providers.coingecko.plugin import CoinGeckoProvider
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.test_scripts.test_utils import print_section, print_success


def test_p4_coingecko_says_powered_by_coingecko_linked_to_its_site():
    print_section("P4: the attribution")
    attribution = CoinGeckoProvider().attribution
    assert attribution == FAProviderAttribution(text="Powered by CoinGecko", url="https://www.coingecko.com/")
    print_success("Powered by CoinGecko → https://www.coingecko.com/")


def test_p4_a_provider_says_none_by_default():
    assert MockProvider().attribution is None


def test_p4_every_registered_provider_has_none_or_a_valid_one():
    codes = [entry["code"] for entry in AssetProviderRegistry.list_providers()]
    assert "coingecko" in codes and "yfinance" in codes, f"barrier: the registry lists the shipped providers: {codes}"
    for code in codes:
        plugin = AssetProviderRegistry.get_plugin(code)
        assert plugin is not None
        attribution = plugin().attribution
        assert attribution is None or isinstance(attribution, FAProviderAttribution), code


@pytest.mark.parametrize(
    ("text", "url"),
    [("", "https://www.coingecko.com/"), ("Powered by CoinGecko", "http://www.coingecko.com/"), ("Powered by CoinGecko", "javascript:alert(1)"), ("Powered by CoinGecko", "/local"), ("x" * 81, "https://www.coingecko.com/")],
)
def test_p4_an_attribution_is_a_short_text_and_an_https_link(text: str, url: str):
    with pytest.raises(ValidationError):
        FAProviderAttribution(text=text, url=url)


def test_p4_the_provider_info_carries_it_none_by_default():
    assert FAProviderInfo(code="x", name="x", description="d", supports_search=False).attribution is None
    info = FAProviderInfo(code="x", name="x", description="d", supports_search=False, attribution=FAProviderAttribution(text="Powered by X", url="https://x.example/"))
    assert info.model_dump(mode="json")["attribution"] == {"text": "Powered by X", "url": "https://x.example/"}
