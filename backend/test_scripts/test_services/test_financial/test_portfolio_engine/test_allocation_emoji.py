"""Regression tests: the allocation view of the portfolio engine reads the one map of sector emoji.

``DerivedViewsBuilder.build_allocation_current()`` puts an emoji on every slice of the by-sector
allocation, and the dashboard pie shows it; the allocation history takes its glyphs from
``/utilities/sectors`` instead. Each kept its own map, and the engine's copy
(``derived_views.SECTOR_EMOJIS``) disagreed with the endpoint's on four keys: Health Care 💊 for 🏥,
Real Estate 🏢 for 🏠 (🏢 being Corporate Bonds), Utilities 🔌 for 💡, Liquidity 💵 for 💰. One
sector, two glyphs, depending on the chart. Both now read ``SECTOR_EMOJI`` from
``backend.app.utils.asset.sector`` (the designer's table, round 2, 15/10/2026), and these tests keep
the engine on it.

Since DV-2 (15/10/2026) the engine reads each glyph through ``sector_emoji()``, the lookup beside the
map: a by-sector name outside the map wears ``SECTOR_EMOJI_FALLBACK`` (❓), the fallback
``/utilities/sectors`` serves too, where it used to wear None.

The map itself (keys, glyphs, distinctness), the allocation buckets and the fallback are covered in
test_utilities/test_sector_normalization.py, the endpoint in test_api/test_utilities.py.

Pure tests — no DB, no async.
"""

from collections.abc import Mapping
from dataclasses import MISSING, fields
from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.financial_math.portfolio import derived_views
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState
from backend.app.utils.asset import sector
from backend.app.utils.asset.sector import SECTOR_EMOJI, SECTOR_EMOJI_FALLBACK

# =============================================================================
# HELPERS
# =============================================================================

# One day of a portfolio, in the shape DailyStateBuilder writes it: the sectors of the assets'
# distributions, plus "Liquidity" for the cash and "Unknown" for the holdings without a sector.
# Health Care, Real Estate, Utilities and Liquidity are the four keys the old copy disagreed on;
# Corporate Bonds is the sector whose 🏢 it also gave to Real Estate.
BY_SECTOR = {
    "Technology": Decimal("3200.00"),
    "Health Care": Decimal("1800.00"),
    "Real Estate": Decimal("1200.00"),
    "Utilities": Decimal("700.00"),
    "Corporate Bonds": Decimal("650.00"),
    "Liquidity": Decimal("2500.00"),
    "Unknown": Decimal("400.00"),
}
# The engine also writes "Liquidity" and "Unknown" as type buckets, and "Unknown" as a geography one
# (the cash has no geography): names the sector map knows, in the dimensions that wear no glyph.
BY_TYPE = {
    "STOCK": Decimal("5000.00"),
    "ETF": Decimal("2550.00"),
    "Liquidity": Decimal("2500.00"),
    "Unknown": Decimal("400.00"),
}
BY_GEOGRAPHY = {
    "USA": Decimal("4300.00"),
    "ITA": Decimal("3250.00"),
    "Unknown": Decimal("400.00"),
}

# A name outside SECTOR_EMOJI, neither a sector nor a bucket: the one key DV-2 gives the fallback.
UNMAPPED_NAME = "Not A Sector"

# The real DailyPortfolioState rather than a stand-in, so the state cannot drift from the attributes the
# engine reads. Its other required fields (valuation, accounting, performance inputs) play no part in the
# allocation view: all zero, read off the dataclass so that a new one does not break a test about emoji.
_UNRELATED_REQUIRED_FIELDS = {f.name: Decimal("0") for f in fields(DailyPortfolioState) if f.init and f.default is MISSING and f.default_factory is MISSING and f.name != "date"}


def _allocation_current(*, by_type: Mapping[str, Decimal] = BY_TYPE, by_sector: Mapping[str, Decimal] = BY_SECTOR, by_geography: Mapping[str, Decimal] = BY_GEOGRAPHY) -> tuple[list[dict], list[dict], list[dict]]:
    """``build_allocation_current()`` over a single daily state holding the three allocations given, by default the ones above."""
    state = DailyPortfolioState(
        date=date(2026, 10, 15),
        **_UNRELATED_REQUIRED_FIELDS,
        by_type=dict(by_type),
        by_sector=dict(by_sector),
        by_geography=dict(by_geography),
    )
    return DerivedViewsBuilder([state], "EUR").build_allocation_current()


# =============================================================================
# DerivedViewsBuilder.build_allocation_current() — emoji
# =============================================================================


class TestAllocationCurrentEmoji:
    """The by-sector slices wear the glyphs of SECTOR_EMOJI, and its fallback for a name outside it; the by-type and by-geography slices wear none."""

    def test_every_sector_slice_reads_the_shared_map(self):
        """Each by-sector slice wears the glyph SECTOR_EMOJI gives its name."""
        _by_type, by_sector, _by_geography = _allocation_current()
        # One slice per name given, nothing more: the loop below sees all of them.
        assert sorted(item["name"] for item in by_sector) == sorted(BY_SECTOR)
        for item in by_sector:
            assert item["emoji"] == SECTOR_EMOJI[item["name"]], f"{item['name']}: the slice wears {item['emoji']!r}, SECTOR_EMOJI says {SECTOR_EMOJI[item['name']]!r}"

    @pytest.mark.parametrize(
        ("name", "glyph", "old_glyph"),
        [
            pytest.param("Health Care", "🏥", "💊", id="health-care"),
            pytest.param("Real Estate", "🏠", "🏢", id="real-estate"),
            pytest.param("Utilities", "💡", "🔌", id="utilities"),
            pytest.param("Liquidity", "💰", "💵", id="liquidity"),
        ],
    )
    def test_the_keys_the_old_copy_disagreed_on(self, name, glyph, old_glyph):
        """Regression: the engine's own SECTOR_EMOJIS gave these four keys a glyph of its own."""
        _by_type, by_sector, _by_geography = _allocation_current()
        emoji_by_name = {item["name"]: item["emoji"] for item in by_sector}
        assert emoji_by_name[name] == glyph, f"{name}: the slice wears {emoji_by_name[name]!r}, the designer's table says {glyph!r} (the engine's old copy said {old_glyph!r})"

    def test_type_and_geography_slices_carry_no_emoji(self):
        """Only the sector dimension wears glyphs: even "Liquidity" and "Unknown" carry None as a type or a geography."""
        by_type, _by_sector, by_geography = _allocation_current()
        for dimension, items, given in (("type", by_type, BY_TYPE), ("geography", by_geography, BY_GEOGRAPHY)):
            # One slice per name given, nothing more: the loop below sees all of them.
            assert sorted(item["name"] for item in items) == sorted(given), dimension
            for item in items:
                assert item["emoji"] is None, f"{dimension} slice {item['name']!r} wears {item['emoji']!r}"

    def test_a_sector_outside_the_map_wears_the_fallback(self):
        """DV-2: a by-sector name outside SECTOR_EMOJI wears SECTOR_EMOJI_FALLBACK (❓) instead of None.

        It is the fallback /utilities/sectors serves, so the engine and the endpoint agree on an unexpected key too. The
        by-type and by-geography slices still carry None, the same name included: the fallback is a sector glyph only.
        """
        assert UNMAPPED_NAME not in SECTOR_EMOJI, f"{UNMAPPED_NAME!r} is a key of SECTOR_EMOJI: this test no longer reaches the fallback"
        extra = {UNMAPPED_NAME: Decimal("100.00")}
        by_type, by_sector, by_geography = _allocation_current(by_type={**BY_TYPE, **extra}, by_sector={**BY_SECTOR, **extra}, by_geography={**BY_GEOGRAPHY, **extra})

        emoji_by_name = {item["name"]: item["emoji"] for item in by_sector}
        assert UNMAPPED_NAME in emoji_by_name, f"no by-sector slice for {UNMAPPED_NAME!r}: {sorted(emoji_by_name)}"
        assert emoji_by_name[UNMAPPED_NAME] == SECTOR_EMOJI_FALLBACK, f"{UNMAPPED_NAME!r}: the slice wears {emoji_by_name[UNMAPPED_NAME]!r}, the fallback is {SECTOR_EMOJI_FALLBACK!r}"

        for dimension, items in (("type", by_type), ("geography", by_geography)):
            names = sorted(item["name"] for item in items)
            assert UNMAPPED_NAME in names, f"no {dimension} slice for {UNMAPPED_NAME!r}: {names}"
            for item in items:
                assert item["emoji"] is None, f"{dimension} slice {item['name']!r} wears {item['emoji']!r}"

    def test_the_module_keeps_no_map_of_its_own(self):
        """derived_views reads every glyph through the one lookup: no copy of the map is left to drift from /utilities/sectors."""
        assert derived_views.sector_emoji is sector.sector_emoji
        # Neither the old copy nor the map itself: the glyphs, the fallback included, come from sector_emoji() alone.
        assert not hasattr(derived_views, "SECTOR_EMOJIS")
        assert not hasattr(derived_views, "SECTOR_EMOJI")
