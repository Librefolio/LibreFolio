"""
Tests for sector normalization utilities.

Tests the FinancialSector enum, the normalization functions, SECTOR_EMOJI (the one map of sector emoji), the allocation
buckets beside the sectors, and sector_emoji() with its fallback.
"""

import pytest

from backend.app.utils.asset.sector import ALLOCATION_BUCKETS, SECTOR_EMOJI, SECTOR_EMOJI_FALLBACK, FinancialSector, normalize_sector, sector_emoji, validate_sector

# ============================================================
# FinancialSector Enum Tests
# ============================================================


class TestFinancialSectorEnum:
    """Tests for FinancialSector enum."""

    def test_all_sectors_have_values(self):
        """All sectors should have string values."""
        for sector in FinancialSector:
            assert isinstance(sector.value, str)
            assert len(sector.value) > 0

    def test_expected_sectors_exist(self):
        """All expected GICS-inspired sectors should exist."""
        expected = [
            "Industrials",
            "Technology",
            "Financials",
            "Consumer Discretionary",
            "Health Care",
            "Real Estate",
            "Basic Materials",
            "Energy",
            "Consumer Staples",
            "Telecommunication",
            "Utilities",
            "Corporate Bonds",
            "Government Bonds",
            "Other",
        ]
        actual = [s.value for s in FinancialSector]
        for sector in expected:
            assert sector in actual, f"Missing sector: {sector}"

    def test_list_all_excludes_other(self):
        """list_all() should exclude OTHER."""
        sectors = FinancialSector.list_all()
        assert "Other" not in sectors
        assert "Corporate Bonds" in sectors
        assert "Government Bonds" in sectors
        assert len(sectors) == 13  # 14 total - 1 (Other)

    def test_list_all_with_other_includes_all(self):
        """list_all_with_other() should include all sectors."""
        sectors = FinancialSector.list_all_with_other()
        assert "Other" in sectors
        assert "Corporate Bonds" in sectors
        assert "Government Bonds" in sectors
        assert len(sectors) == 14


# ============================================================
# from_string Tests
# ============================================================


class TestFinancialSectorFromString:
    """Tests for FinancialSector.from_string() method."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            # Exact matches (case-insensitive)
            ("Technology", FinancialSector.TECHNOLOGY),
            ("technology", FinancialSector.TECHNOLOGY),
            ("TECHNOLOGY", FinancialSector.TECHNOLOGY),
            ("Financials", FinancialSector.FINANCIALS),
            ("financials", FinancialSector.FINANCIALS),
            ("Industrials", FinancialSector.INDUSTRIALS),
            ("Consumer Discretionary", FinancialSector.CONSUMER_DISCRETIONARY),
            ("consumer discretionary", FinancialSector.CONSUMER_DISCRETIONARY),
            ("Health Care", FinancialSector.HEALTH_CARE),
            ("Real Estate", FinancialSector.REAL_ESTATE),
            ("Basic Materials", FinancialSector.BASIC_MATERIALS),
            ("Energy", FinancialSector.ENERGY),
            ("Consumer Staples", FinancialSector.CONSUMER_STAPLES),
            ("Telecommunication", FinancialSector.TELECOMMUNICATION),
            ("Utilities", FinancialSector.UTILITIES),
            ("Corporate Bonds", FinancialSector.CORPORATE_BONDS),
            ("corporate bonds", FinancialSector.CORPORATE_BONDS),
            ("Government Bonds", FinancialSector.GOVERNMENT_BONDS),
            ("government bonds", FinancialSector.GOVERNMENT_BONDS),
            ("Other", FinancialSector.OTHER),
        ],
    )
    def test_exact_matches(self, input_val, expected):
        """Exact sector names should be recognized."""
        assert FinancialSector.from_string(input_val) == expected

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            # Aliases
            ("healthcare", FinancialSector.HEALTH_CARE),  # No space
            ("materials", FinancialSector.BASIC_MATERIALS),  # Short form
            ("telecom", FinancialSector.TELECOMMUNICATION),  # Short form
            ("HealthCare", FinancialSector.HEALTH_CARE),
            # Yahoo Finance aliases
            ("Financial Services", FinancialSector.FINANCIALS),
            ("Communication Services", FinancialSector.TELECOMMUNICATION),
            ("Consumer Cyclical", FinancialSector.CONSUMER_DISCRETIONARY),
            ("Consumer Defensive", FinancialSector.CONSUMER_STAPLES),
            # Bond aliases
            ("corporate", FinancialSector.CORPORATE_BONDS),
            ("corporate bond", FinancialSector.CORPORATE_BONDS),
            ("government", FinancialSector.GOVERNMENT_BONDS),
            ("government bond", FinancialSector.GOVERNMENT_BONDS),
        ],
    )
    def test_aliases(self, input_val, expected):
        """Aliases should be recognized."""
        assert FinancialSector.from_string(input_val) == expected

    @pytest.mark.parametrize(
        "input_val",
        [
            # Unknown sectors should map to OTHER
            "Unknown",
            "Software",
            "Hardware",
            "Banking",
            "Insurance",
            "Aerospace",
            "Gaming",
            "Automotive",
            "SomeRandomSector",
        ],
    )
    def test_unknown_sectors_map_to_other(self, input_val):
        """Unknown sector names should map to OTHER."""
        result = FinancialSector.from_string(input_val)
        assert result == FinancialSector.OTHER

    def test_empty_string_maps_to_other(self):
        """Empty string should map to OTHER."""
        assert FinancialSector.from_string("") == FinancialSector.OTHER

    def test_none_maps_to_other(self):
        """None should map to OTHER."""
        assert FinancialSector.from_string(None) == FinancialSector.OTHER

    def test_whitespace_trimmed(self):
        """Whitespace should be trimmed."""
        assert FinancialSector.from_string("  Technology  ") == FinancialSector.TECHNOLOGY
        assert FinancialSector.from_string("\tFinancials\n") == FinancialSector.FINANCIALS


# ============================================================
# normalize_sector Function Tests
# ============================================================


class TestNormalizeSector:
    """Tests for normalize_sector() function."""

    def test_returns_string_value(self):
        """Should return the string value, not enum."""
        result = normalize_sector("Technology")
        assert result == "Technology"
        assert isinstance(result, str)

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        assert normalize_sector("technology") == "Technology"
        assert normalize_sector("TECHNOLOGY") == "Technology"
        assert normalize_sector("TeCHNoLoGy") == "Technology"

    def test_alias_normalization(self):
        """Should normalize aliases to standard names."""
        assert normalize_sector("healthcare") == "Health Care"
        assert normalize_sector("materials") == "Basic Materials"
        assert normalize_sector("telecom") == "Telecommunication"
        assert normalize_sector("corporate") == "Corporate Bonds"
        assert normalize_sector("corporate bond") == "Corporate Bonds"
        assert normalize_sector("corporate bonds") == "Corporate Bonds"
        assert normalize_sector("government") == "Government Bonds"
        assert normalize_sector("government bond") == "Government Bonds"
        assert normalize_sector("government bonds") == "Government Bonds"

    def test_yahoo_finance_alias_normalization(self):
        """Yahoo Finance sector names should normalize to standard GICS names."""
        assert normalize_sector("Financial Services") == "Financials"
        assert normalize_sector("Communication Services") == "Telecommunication"
        assert normalize_sector("Consumer Cyclical") == "Consumer Discretionary"
        assert normalize_sector("Consumer Defensive") == "Consumer Staples"

    def test_unknown_returns_other(self):
        """Unknown sectors should return 'Other'."""
        assert normalize_sector("SomeUnknownSector") == "Other"
        assert normalize_sector("Banking") == "Other"


# ============================================================
# validate_sector Function Tests
# ============================================================


class TestValidateSector:
    """Tests for validate_sector() function."""

    def test_valid_sectors_return_true(self):
        """Known sectors should return True."""
        assert validate_sector("Technology") is True
        assert validate_sector("Financials") is True
        assert validate_sector("Corporate Bonds") is True
        assert validate_sector("Government Bonds") is True
        assert validate_sector("healthcare") is True  # Alias

    def test_bond_aliases_return_true(self):
        """Bond aliases should be recognized as valid sectors."""
        assert validate_sector("corporate") is True
        assert validate_sector("corporate bond") is True
        assert validate_sector("government") is True
        assert validate_sector("government bond") is True

    def test_yahoo_finance_aliases_return_true(self):
        """Yahoo Finance sector names should be recognized as valid."""
        assert validate_sector("Financial Services") is True
        assert validate_sector("Communication Services") is True
        assert validate_sector("Consumer Cyclical") is True
        assert validate_sector("Consumer Defensive") is True

    def test_other_returns_false(self):
        """'Other' should return False (not a recognized sector)."""
        assert validate_sector("Other") is False
        assert validate_sector("other") is False

    def test_unknown_returns_false(self):
        """Unknown sectors should return False."""
        assert validate_sector("Banking") is False
        assert validate_sector("Unknown") is False


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_sector_enum_is_str_enum(self):
        """FinancialSector should be usable as string."""
        sector = FinancialSector.TECHNOLOGY
        # Should be comparable to string
        assert sector == "Technology"
        # Should be usable in f-strings
        assert f"{sector.value}" == "Technology"

    def test_sector_in_dict_key(self):
        """Sectors should work as dict keys."""
        data = {FinancialSector.TECHNOLOGY: 0.5, FinancialSector.FINANCIALS: 0.5}
        assert data[FinancialSector.TECHNOLOGY] == 0.5
        # Also works with string lookup since it's a str enum
        assert data["Technology"] == 0.5


# ============================================================
# SECTOR_EMOJI Map Tests
# ============================================================

# The two buckets the portfolio engine adds on its own, outside FinancialSector: the cash, and the holdings without a sector.
# Written out rather than read from ALLOCATION_BUCKETS: these are the names DailyStateBuilder writes, which the constant
# must match.
ENGINE_BUCKETS = ("Liquidity", "Unknown")

# The designer's table, round 2 (15/10/2026). A design contract: every glyph is pinned on purpose.
DESIGNER_SECTOR_EMOJI = {
    "Industrials": "🏭",
    "Technology": "💻",
    "Financials": "🏦",
    "Consumer Discretionary": "🛍️",
    "Health Care": "🏥",
    "Real Estate": "🏠",
    "Basic Materials": "⛏️",
    "Energy": "⚡",
    "Consumer Staples": "🛒",
    "Telecommunication": "📡",
    "Utilities": "💡",
    "Corporate Bonds": "🏢",
    "Government Bonds": "🏛️",
    "Other": "📦",
    "Liquidity": "💰",
    "Unknown": "❓",
}


class TestSectorEmojiMap:
    """Tests for SECTOR_EMOJI, the one map of sector emoji.

    `/utilities/sectors` (behind the allocation history) and the allocation view of the portfolio engine
    (behind the dashboard pie) both read it. They used to keep a copy each, and the copies disagreed on
    four keys: one sector, two glyphs, depending on the chart.
    """

    def test_keys_are_every_sector_plus_the_engine_buckets(self):
        """Every FinancialSector value has an emoji, and so do Liquidity and Unknown: nothing else is in the map."""
        expected_keys = {sector.value for sector in FinancialSector} | set(ENGINE_BUCKETS)
        assert {str(key) for key in SECTOR_EMOJI} == expected_keys
        # Derived from the enum, never a literal: one key per sector, plus the two buckets.
        assert len(SECTOR_EMOJI) == len(FinancialSector) + len(ENGINE_BUCKETS)

    def test_glyphs_are_the_designer_table(self):
        """Each key reads exactly the glyph of the designer's table."""
        # str() turns the FinancialSector keys into their plain names, so a failure diffs readable keys.
        assert {str(key): glyph for key, glyph in SECTOR_EMOJI.items()} == DESIGNER_SECTOR_EMOJI

    def test_plain_string_and_enum_member_read_the_same_glyph(self):
        """A plain-string lookup, the one the API and the engine do with names, reads the glyph of the enum member."""
        for sector in FinancialSector:
            name = sector.value
            assert type(name) is str, f"{name!r} is not a plain str: the lookup below would not test what it says"
            assert SECTOR_EMOJI.get(name) == SECTOR_EMOJI[sector], f"{name}: the plain string reads {SECTOR_EMOJI.get(name)!r}, the member {SECTOR_EMOJI[sector]!r}"

    def test_glyphs_are_distinct_non_empty_strings(self):
        """Every glyph is a non-empty string, and no two keys share one.

        Two keys with one glyph are two pie slices nobody can tell apart: the engine's old copy gave 🏢 to both
        Real Estate and Corporate Bonds.
        """
        owners: dict[str, list[str]] = {}
        for key, glyph in SECTOR_EMOJI.items():
            assert isinstance(glyph, str), f"{key}: {glyph!r} is not a string"
            assert glyph.strip(), f"{key}: the glyph is empty"
            # Compared without U+FE0F, the emoji presentation selector: it changes the string, not the symbol.
            owners.setdefault(glyph.replace("\ufe0f", ""), []).append(str(key))
        shared = {glyph: keys for glyph, keys in owners.items() if len(keys) > 1}
        assert not shared, f"glyphs shared by more than one key: {shared}"


# ============================================================
# ALLOCATION_BUCKETS Tests
# ============================================================


class TestAllocationBuckets:
    """Tests for ALLOCATION_BUCKETS, the two buckets the portfolio engine adds beside the sectors.

    `/utilities/sectors` lists them apart from the sectors, with their emoji: the frontend reads their glyphs from there
    and keeps no map of its own.
    """

    def test_the_buckets_are_liquidity_then_unknown(self):
        """The cash, then the holdings without a sector: the names DailyStateBuilder writes, in the order the endpoint lists them."""
        assert ALLOCATION_BUCKETS == ENGINE_BUCKETS

    def test_every_bucket_has_an_emoji(self):
        """Both buckets are keys of SECTOR_EMOJI, so each has a glyph of its own in the map."""
        missing = [bucket for bucket in ALLOCATION_BUCKETS if bucket not in SECTOR_EMOJI]
        assert not missing, f"allocation buckets without an emoji: {missing}"

    def test_no_bucket_is_a_sector(self):
        """Neither bucket is a FinancialSector value, and the normalization turns either name into Other.

        So no asset is ever classified in a bucket (FASectorArea normalizes every key it is given), and a sector select,
        fed with the FinancialSector values, never offers one.
        """
        sector_values = {sector.value for sector in FinancialSector}
        both = sorted(sector_values & set(ALLOCATION_BUCKETS))
        assert not both, f"allocation buckets that are also sectors: {both}"
        for bucket in ALLOCATION_BUCKETS:
            assert normalize_sector(bucket) == FinancialSector.OTHER, f"{bucket!r} normalizes to {normalize_sector(bucket)!r}, not Other"


# ============================================================
# sector_emoji() and SECTOR_EMOJI_FALLBACK Tests
# ============================================================


class TestSectorEmojiLookup:
    """Tests for sector_emoji() and SECTOR_EMOJI_FALLBACK, the one lookup behind `/utilities/sectors` and the engine.

    DV-2 (15/10/2026): one fallback beside the map, the same for the endpoint and the engine. Before it the endpoint fell
    back to 📊 and the engine to None.
    """

    def test_the_fallback_is_the_glyph_of_unknown(self):
        """SECTOR_EMOJI_FALLBACK is ❓, the glyph of the Unknown bucket: a key outside the map reads as unclassified.

        And as no sector: the glyphs of the map are distinct (test_glyphs_are_distinct_non_empty_strings).
        """
        assert SECTOR_EMOJI_FALLBACK == "❓"
        assert SECTOR_EMOJI_FALLBACK == SECTOR_EMOJI["Unknown"]

    def test_a_mapped_key_reads_its_own_glyph(self):
        """sector_emoji() of a key in the map is the glyph of that key: the fallback never shadows a mapped key."""
        for key, glyph in SECTOR_EMOJI.items():
            assert sector_emoji(key) == glyph, f"{key}: sector_emoji reads {sector_emoji(key)!r}, SECTOR_EMOJI says {glyph!r}"
            # The plain name too: the endpoint and the engine pass names, not enum members.
            assert sector_emoji(str(key)) == glyph, f"{key}: by plain name sector_emoji reads {sector_emoji(str(key))!r}, SECTOR_EMOJI says {glyph!r}"

    @pytest.mark.parametrize(
        "key",
        [
            pytest.param("Not A Sector", id="made-up-name"),
            pytest.param("", id="empty-string"),
        ],
    )
    def test_a_name_nobody_knows_reads_the_fallback(self, key):
        """A name that is neither a sector nor a bucket reads SECTOR_EMOJI_FALLBACK."""
        assert key not in SECTOR_EMOJI, f"{key!r} is a key of SECTOR_EMOJI: this case no longer reaches the fallback"
        assert sector_emoji(key) == SECTOR_EMOJI_FALLBACK, f"{key!r}: sector_emoji reads {sector_emoji(key)!r}, the fallback is {SECTOR_EMOJI_FALLBACK!r}"

    @pytest.mark.parametrize(
        ("key", "sector"),
        [
            pytest.param("health care", FinancialSector.HEALTH_CARE, id="case-variant"),
            pytest.param("Healthcare", FinancialSector.HEALTH_CARE, id="from-string-alias"),
        ],
    )
    def test_a_non_canonical_sector_name_reads_the_fallback(self, key, sector):
        """A name from_string() takes for a sector, but not the sector's canonical value, reads the fallback.

        The map is case-sensitive and holds no alias. Pinned on purpose: the engine only ever passes canonical
        FinancialSector values, and the lookup does not normalize for a caller that does not.
        """
        # The precondition, verified rather than assumed: from_string() takes the name for the sector...
        assert FinancialSector.from_string(key) == sector
        # ...yet the name is not the sector's canonical value, whose glyph is not the fallback.
        assert key != sector.value
        assert SECTOR_EMOJI[sector] != SECTOR_EMOJI_FALLBACK
        assert sector_emoji(key) == SECTOR_EMOJI_FALLBACK, f"{key!r}: sector_emoji reads {sector_emoji(key)!r}, the fallback is {SECTOR_EMOJI_FALLBACK!r} ({sector.value} reads {SECTOR_EMOJI[sector]!r})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
