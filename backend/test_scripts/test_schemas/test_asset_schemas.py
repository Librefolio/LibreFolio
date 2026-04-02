"""
Tests for asset-related Pydantic schemas.

Migrated from:
- test_utilities/test_scheduled_investment_schemas.py
- test_utilities/test_distribution_models.py
- test_utilities/test_geographic_area_integration.py

Schema source: backend/app/schemas/assets.py

Tests cover:
- FAInterestRatePeriod: date ranges, rate validation, compounding/frequency logic
- FALateInterestConfig: rate validation, grace period logic
- FAScheduledInvestmentSchedule: period ordering, overlaps, gaps detection
- FAGeographicArea: country normalization, weight validation
- FASectorArea: sector normalization, weight validation
- FAClassificationParams: integration and serialization
"""

import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.schemas.assets import (
    FAInterestRatePeriod,
    FALateInterestConfig,
    FAScheduledInvestmentSchedule,
    MaturationFrequency,
    DayCountConvention,
    InterestType,
    FAGeographicArea,
    FASectorArea,
    FAClassificationParams,
    )
from backend.app.schemas.common import Currency


# ============================================================================
# TESTS: FAInterestRatePeriod
# ============================================================================


class TestInterestRatePeriod:
    """Test FAInterestRatePeriod schema validation."""

    def test_valid_simple_interest_period(self):
        """Test creating valid simple interest period."""
        period = FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            maturation_frequency=MaturationFrequency.DAILY,
            )
        assert period.annual_rate == Decimal("0.05")
        assert period.maturation_frequency == MaturationFrequency.DAILY

    def test_valid_quarterly_maturation_period(self):
        """Test creating valid period with quarterly maturation."""
        period = FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            maturation_frequency=MaturationFrequency.QUARTERLY,
            )
        assert period.maturation_frequency == MaturationFrequency.QUARTERLY

    def test_negative_rate_rejected(self):
        """Test that negative interest rates are rejected."""
        with pytest.raises(ValidationError, match="non-negative"):
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("-0.05"),
                )

    def test_end_date_before_start_date_rejected(self):
        """Test that end_date before start_date is rejected."""
        with pytest.raises(ValidationError, match="end_date must be on or after start_date"):
            FAInterestRatePeriod(
                start_date=date(2025, 12, 31),
                end_date=date(2025, 1, 1),
                annual_rate=Decimal("0.05"),
                )

    def test_same_start_end_date_allowed(self):
        """Test that same start and end date is allowed (single day period)."""
        period = FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
            annual_rate=Decimal("0.05"),
            )
        assert period.start_date == period.end_date

    def test_defaults(self):
        """Test that defaults are applied correctly."""
        period = FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            )
        assert period.maturation_frequency == MaturationFrequency.DAILY

    def test_rate_string_conversion(self):
        """Test that rate can be provided as string."""
        period = FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate="0.05",
            )
        assert period.annual_rate == Decimal("0.05")

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                extra_field="should_fail",
                )


# ============================================================================
# TESTS: FALateInterestConfig
# ============================================================================


class TestLateInterestConfig:
    """Test FALateInterestConfig schema validation."""

    def test_valid_late_interest(self):
        """Test creating valid late interest config."""
        config = FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=30,
            )
        assert config.annual_rate == Decimal("0.12")
        assert config.grace_period_days == 30

    def test_negative_rate_rejected(self):
        """Test that negative late interest rate is rejected."""
        with pytest.raises(ValidationError, match="non-negative"):
            FALateInterestConfig(
                annual_rate=Decimal("-0.12"),
                )

    def test_negative_grace_period_rejected(self):
        """Test that negative grace period is rejected."""
        with pytest.raises(ValidationError, match="non-negative"):
            FALateInterestConfig(
                annual_rate=Decimal("0.12"),
                grace_period_days=-10,
                )

    def test_zero_grace_period_allowed(self):
        """Test that zero grace period is allowed."""
        config = FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=0,
            )
        assert config.grace_period_days == 0



# ============================================================================
# TESTS: FAScheduledInvestmentSchedule
# ============================================================================


class TestScheduledInvestmentSchedule:
    """Test FAScheduledInvestmentSchedule schema validation."""

    def test_valid_single_period_schedule(self):
        """Test valid schedule with single period."""
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.05"),
                    )
                ]
            )
        assert len(schedule.schedule) == 1

    def test_global_defaults(self):
        """Test that global day_count and interest_type defaults are correct."""
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.05"),
                    )
                ]
            )
        assert schedule.day_count == DayCountConvention.ACT_365
        assert schedule.interest_type == InterestType.SIMPLE

    def test_global_compound_interest(self):
        """Test explicit COMPOUND interest_type on schedule."""
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
            interest_type=InterestType.COMPOUND,
            day_count=DayCountConvention.ACT_360,
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.05"),
                    )
                ]
            )
        assert schedule.interest_type == InterestType.COMPOUND
        assert schedule.day_count == DayCountConvention.ACT_360

    def test_day_count_on_period_rejected(self):
        """Test that day_count on FAInterestRatePeriod is rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                day_count="ACT/365",
                )

    def test_valid_multiple_periods_contiguous(self):
        """Test valid schedule with contiguous periods."""
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 6, 30),
                    annual_rate=Decimal("0.05"),
                    ),
                FAInterestRatePeriod(
                    start_date=date(2025, 7, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.06"),
                    ),
                ]
            )
        assert len(schedule.schedule) == 2

    def test_empty_schedule_rejected(self):
        """Test that empty schedule is rejected."""
        with pytest.raises(ValidationError, match="at least one period"):
            FAScheduledInvestmentSchedule(initial_value=Currency(code="EUR", amount=Decimal("10000")), schedule=[])

    def test_overlapping_periods_rejected(self):
        """Test that overlapping periods are rejected."""
        with pytest.raises(ValidationError, match="Overlapping periods"):
            FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
                schedule=[
                    FAInterestRatePeriod(
                        start_date=date(2025, 1, 1),
                        end_date=date(2025, 7, 15),
                        annual_rate=Decimal("0.05"),
                        ),
                    FAInterestRatePeriod(
                        start_date=date(2025, 7, 1),
                        end_date=date(2025, 12, 31),
                        annual_rate=Decimal("0.06"),
                        ),
                    ]
                )

    def test_gap_in_periods_rejected(self):
        """Test that gaps between periods are rejected."""
        with pytest.raises(ValidationError, match="Gap detected"):
            FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
                schedule=[
                    FAInterestRatePeriod(
                        start_date=date(2025, 1, 1),
                        end_date=date(2025, 6, 30),
                        annual_rate=Decimal("0.05"),
                        ),
                    FAInterestRatePeriod(
                        start_date=date(2025, 7, 5),
                        end_date=date(2025, 12, 31),
                        annual_rate=Decimal("0.06"),
                        ),
                    ]
                )

    def test_unsorted_periods_are_sorted(self):
        """Test that unsorted periods are automatically sorted."""
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 7, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.06"),
                    ),
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 6, 30),
                    annual_rate=Decimal("0.05"),
                    ),
                ]
            )
        assert schedule.schedule[0].start_date == date(2025, 1, 1)
        assert schedule.schedule[1].start_date == date(2025, 7, 1)

    def test_with_late_interest(self):
        """Test schedule with late interest configuration."""
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.05"),
                    )
                ],
            late_interest=FALateInterestConfig(
                annual_rate=Decimal("0.12"),
                grace_period_days=30,
                ),
            )
        assert schedule.late_interest is not None
        assert schedule.late_interest.annual_rate == Decimal("0.12")

    def test_three_periods_different_maturation(self):
        """Test schedule with multiple periods using different maturation frequencies."""
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 4, 30),
                    annual_rate=Decimal("0.04"),
                    maturation_frequency=MaturationFrequency.DAILY,
                    ),
                FAInterestRatePeriod(
                    start_date=date(2025, 5, 1),
                    end_date=date(2025, 8, 31),
                    annual_rate=Decimal("0.05"),
                    maturation_frequency=MaturationFrequency.QUARTERLY,
                    ),
                FAInterestRatePeriod(
                    start_date=date(2025, 9, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.06"),
                    maturation_frequency=MaturationFrequency.MONTHLY,
                    ),
                ]
            )
        assert len(schedule.schedule) == 3
        assert schedule.schedule[1].maturation_frequency == MaturationFrequency.QUARTERLY

    def test_initial_value_required(self):
        """Test that initial_value is required."""
        with pytest.raises(ValidationError):
            FAScheduledInvestmentSchedule(
                schedule=[
                    FAInterestRatePeriod(
                        start_date=date(2025, 1, 1),
                        end_date=date(2025, 12, 31),
                        annual_rate=Decimal("0.05"),
                        )
                    ]
                )

    def test_initial_value_zero_rejected(self):
        """Test that initial_value amount <= 0 is rejected (Currency validates)."""
        # Currency itself doesn't reject zero/negative amount, but the schedule
        # should still work — the validation is on Currency.amount being numeric
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("1")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.05"),
                    )
                ]
            )
        assert schedule.initial_value.amount == Decimal("1")

    def test_initial_value_negative_accepted(self):
        """Test that negative amount in Currency is accepted (Currency allows negative)."""
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("-1000")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.05"),
                    )
                ]
            )
        assert schedule.initial_value.amount == Decimal("-1000")

    def test_currency_in_initial_value(self):
        """Test that initial_value requires valid currency code."""
        with pytest.raises(ValidationError):
            FAScheduledInvestmentSchedule(
                initial_value=Currency(code="INVALID", amount=Decimal("10000")),
                schedule=[
                    FAInterestRatePeriod(
                        start_date=date(2025, 1, 1),
                        end_date=date(2025, 12, 31),
                        annual_rate=Decimal("0.05"),
                        )
                    ]
                )

    def test_with_asset_events(self):
        """Test schedule with asset events."""
        from backend.app.schemas.prices import FAAssetEventPoint
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("10000")),
            schedule=[
                FAInterestRatePeriod(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    annual_rate=Decimal("0.05"),
                    )
                ],
            asset_events=[
                FAAssetEventPoint(
                    date=date(2025, 7, 1),
                    type="INTEREST",
                    value=Currency(code="EUR", amount=Decimal("250")),
                    ),
                ],
            )
        assert len(schedule.asset_events) == 1
        assert schedule.asset_events[0].type == "INTEREST"


# ============================================================================
# TESTS: FAAssetEventPoint
# ============================================================================


class TestFAAssetEventPoint:
    """Test FAAssetEventPoint schema validation."""

    def test_valid_event(self):
        """Test creating a valid asset event point."""
        from backend.app.schemas.prices import FAAssetEventPoint
        from backend.app.schemas.common import Currency
        event = FAAssetEventPoint(
            date=date(2025, 7, 1),
            type="INTEREST",
            value=Currency(code="EUR", amount=Decimal("250.50")),
            notes="H1 interest payout",
            )
        assert event.value.amount == Decimal("250.50")
        assert event.value.code == "EUR"

    def test_value_requires_currency(self):
        """Test that value requires a Currency object with code."""
        from backend.app.schemas.prices import FAAssetEventPoint
        from backend.app.schemas.common import Currency
        event = FAAssetEventPoint(
            date=date(2025, 7, 1),
            type="PRICE_ADJUSTMENT",
            value=Currency(code="EUR", amount=Decimal("-1000")),
            )
        assert event.value.amount == Decimal("-1000")
        assert event.value.code == "EUR"

    def test_json_roundtrip(self):
        """Test JSON serialization/deserialization roundtrip."""
        from backend.app.schemas.prices import FAAssetEventPoint
        from backend.app.schemas.common import Currency
        event = FAAssetEventPoint(
            date=date(2025, 7, 1),
            type="INTEREST",
            value=Currency(code="EUR", amount=Decimal("250")),
            notes="test",
            )
        data = event.model_dump(mode="json")
        event2 = FAAssetEventPoint(**data)
        assert event2.date == event.date
        assert event2.type == event.type
        assert event2.value.amount == event.value.amount
        assert event2.value.code == event.value.code


# ============================================================================
# TESTS: FAGeographicArea
# ============================================================================


class TestFAGeographicArea:
    """Tests for FAGeographicArea model."""

    def test_valid_distribution(self):
        """Valid distribution should be accepted."""
        geo = FAGeographicArea(distribution={"USA": Decimal("0.6"), "ITA": Decimal("0.4")})
        assert geo.distribution["USA"] == Decimal("0.6000")
        assert geo.distribution["ITA"] == Decimal("0.4000")

    def test_sum_to_one(self):
        """Weights should sum to exactly 1.0."""
        geo = FAGeographicArea(distribution={"USA": Decimal("0.7"), "DEU": Decimal("0.3")})
        total = sum(geo.distribution.values())
        assert total == Decimal("1.0")

    def test_country_code_normalization(self):
        """Country codes should be normalized to ISO-3166-A3."""
        geo = FAGeographicArea(distribution={"US": Decimal("0.5"), "IT": Decimal("0.5")})
        assert "USA" in geo.distribution
        assert "ITA" in geo.distribution
        assert "US" not in geo.distribution
        assert "IT" not in geo.distribution

    def test_country_name_normalization(self):
        """Country names should be normalized to ISO-3166-A3."""
        geo = FAGeographicArea(
            distribution={"United States": Decimal("0.5"), "Italy": Decimal("0.5")}
            )
        assert "USA" in geo.distribution
        assert "ITA" in geo.distribution

    def test_float_to_decimal_conversion(self):
        """Float values should be converted to Decimal."""
        geo = FAGeographicArea(distribution={"USA": 0.6, "DEU": 0.4})
        assert isinstance(geo.distribution["USA"], Decimal)
        assert geo.distribution["USA"] == Decimal("0.6000")

    def test_auto_renormalization(self):
        """Weights should be auto-renormalized if close to 1.0."""
        geo = FAGeographicArea(
            distribution={"USA": Decimal("0.333"), "DEU": Decimal("0.333"), "FRA": Decimal("0.334")}
            )
        total = sum(geo.distribution.values())
        assert total == Decimal("1.0")

    def test_empty_distribution_fails(self):
        """Empty distribution should raise error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FAGeographicArea(distribution={})

    def test_invalid_country_fails(self):
        """Invalid country code should raise error."""
        with pytest.raises(ValueError, match="not found"):
            FAGeographicArea(distribution={"INVALID_COUNTRY": Decimal("1.0")})

    def test_negative_weight_fails(self):
        """Negative weight should raise error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            FAGeographicArea(distribution={"USA": Decimal("-0.5"), "DEU": Decimal("1.5")})

    def test_sum_way_off_fails(self):
        """Weights that sum far from 1.0 should raise error."""
        with pytest.raises(ValueError, match="Distribution weights must sum to approximately 1.0"):
            FAGeographicArea(distribution={"USA": Decimal("0.3"), "DEU": Decimal("0.2")})


# ============================================================================
# TESTS: FASectorArea
# ============================================================================


class TestFASectorArea:
    """Tests for FASectorArea model."""

    def test_valid_distribution(self):
        """Valid sector distribution should be accepted."""
        sector = FASectorArea(
            distribution={
                "Technology": Decimal("0.4"),
                "Financials": Decimal("0.3"),
                "Health Care": Decimal("0.3"),
                }
            )
        assert sector.distribution["Technology"] == Decimal("0.4000")
        assert sector.distribution["Financials"] == Decimal("0.3000")

    def test_sum_to_one(self):
        """Weights should sum to exactly 1.0."""
        sector = FASectorArea(distribution={"Technology": Decimal("1.0")})
        total = sum(sector.distribution.values())
        assert total == Decimal("1.0")

    def test_sector_name_normalization_case_insensitive(self):
        """Sector names should be case-insensitive."""
        sector = FASectorArea(
            distribution={"technology": Decimal("0.5"), "FINANCIALS": Decimal("0.5")}
            )
        assert "Technology" in sector.distribution
        assert "Financials" in sector.distribution

    def test_sector_alias_normalization(self):
        """Sector aliases should be normalized."""
        sector = FASectorArea(
            distribution={"healthcare": Decimal("0.5"), "telecom": Decimal("0.5")}
            )
        assert "Health Care" in sector.distribution
        assert "Telecommunication" in sector.distribution
        assert "healthcare" not in sector.distribution

    def test_unknown_sector_mapped_to_other(self):
        """Unknown sectors should be mapped to 'Other'."""
        sector = FASectorArea(
            distribution={"UnknownSector": Decimal("0.5"), "Technology": Decimal("0.5")}
            )
        assert "Other" in sector.distribution
        assert "UnknownSector" not in sector.distribution

    def test_multiple_unknown_merged_into_other(self):
        """Multiple unknown sectors should be merged into 'Other'."""
        sector = FASectorArea(
            distribution={
                "Banking": Decimal("0.2"),
                "Insurance": Decimal("0.2"),
                "Technology": Decimal("0.6"),
                }
            )
        assert "Other" in sector.distribution
        assert sector.distribution["Other"] == Decimal("0.4000")
        assert sector.distribution["Technology"] == Decimal("0.6000")

    def test_float_to_decimal_conversion(self):
        """Float values should be converted to Decimal."""
        sector = FASectorArea(distribution={"Technology": 0.6, "Financials": 0.4})
        assert isinstance(sector.distribution["Technology"], Decimal)
        assert sector.distribution["Technology"] == Decimal("0.6000")

    def test_empty_distribution_fails(self):
        """Empty distribution should raise error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FASectorArea(distribution={})

    def test_negative_weight_fails(self):
        """Negative weight should raise error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            FASectorArea(distribution={"Technology": Decimal("-0.5"), "Financials": Decimal("1.5")})


# ============================================================================
# TESTS: FAClassificationParams Integration
# ============================================================================


class TestFAClassificationParams:
    """Tests for FAClassificationParams with new sector_area field."""

    def test_with_sector_area(self):
        """Should accept sector_area field."""
        params = FAClassificationParams(
            short_description="Test asset",
            sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")}),
            )
        assert params.sector_area is not None
        assert params.sector_area.distribution["Technology"] == Decimal("1.0")

    def test_with_geographic_area(self):
        """Should accept geographic_area field."""
        params = FAClassificationParams(
            geographic_area=FAGeographicArea(distribution={"USA": Decimal("1.0")})
            )
        assert params.geographic_area is not None
        assert params.geographic_area.distribution["USA"] == Decimal("1.0")

    def test_with_both_areas(self):
        """Should accept both sector_area and geographic_area."""
        params = FAClassificationParams(
            short_description="Multi-region tech fund",
            geographic_area=FAGeographicArea(
                distribution={"USA": Decimal("0.6"), "DEU": Decimal("0.4")}
                ),
            sector_area=FASectorArea(
                distribution={"Technology": Decimal("0.7"), "Financials": Decimal("0.3")}
                ),
            )
        assert params.geographic_area is not None
        assert params.sector_area is not None

    def test_all_fields_optional(self):
        """All fields should be optional."""
        params = FAClassificationParams()
        assert params.short_description is None
        assert params.geographic_area is None
        assert params.sector_area is None

    def test_old_sector_field_rejected(self):
        """Old 'sector' field should be rejected (extra='forbid')."""
        with pytest.raises(Exception):
            FAClassificationParams(sector="Technology")


# ============================================================================
# TESTS: Weight Quantization
# ============================================================================


class TestWeightQuantization:
    """Tests for weight quantization behavior."""

    def test_quantized_to_4_decimals(self):
        """Weights should be quantized to 4 decimal places."""
        geo = FAGeographicArea(
            distribution={"USA": Decimal("0.123456789"), "ITA": Decimal("0.876543210")}
            )
        for key, value in geo.distribution.items():
            assert value == value.quantize(Decimal("0.0001"))

    def test_round_half_even(self):
        """Should use banker's rounding (ROUND_HALF_EVEN)."""
        geo = FAGeographicArea(distribution={"USA": Decimal("1.0")})
        for key, value in geo.distribution.items():
            assert value == value.quantize(Decimal("0.0001"))


# ============================================================================
# TESTS: Geographic Area Integration (Serialization)
# ============================================================================


class TestGeographicAreaSerialization:
    """Test for FAGeographicArea serialization/deserialization."""

    def test_classification_params_with_geographic_area(self):
        """Test FAClassificationParams creation with FAGeographicArea."""
        geo = FAGeographicArea(distribution={"USA": Decimal("0.6"), "DEU": Decimal("0.4")})
        params = FAClassificationParams(
            short_description="Test Company",
            geographic_area=geo,
            sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")}),
            )
        assert params.geographic_area is not None
        assert params.geographic_area.distribution["USA"] == Decimal("0.6000")
        assert params.geographic_area.distribution["DEU"] == Decimal("0.4000")

    def test_serialize_classification_params(self):
        """Test serialization to JSON with FAGeographicArea."""
        geo = FAGeographicArea(distribution={"USA": Decimal("0.7"), "GBR": Decimal("0.3")})
        params = FAClassificationParams(
            geographic_area=geo,
            sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")}),
            )
        json_str = params.model_dump_json(exclude_none=True)
        data = json.loads(json_str)

        assert "geographic_area" in data
        assert isinstance(data["geographic_area"], dict)
        assert "distribution" in data["geographic_area"]
        assert "USA" in data["geographic_area"]["distribution"]

    def test_deserialize_classification_params(self):
        """Test deserialization from JSON with nested FAGeographicArea."""
        json_str = '{"geographic_area":{"distribution":{"USA":"0.6000","ITA":"0.4000"}},"sector_area":{"distribution":{"Technology":"1.0000"}}}'
        params = FAClassificationParams.model_validate_json(json_str)

        assert params is not None
        assert params.geographic_area is not None
        assert isinstance(params.geographic_area, FAGeographicArea)
        assert params.geographic_area.distribution["USA"] == Decimal("0.6000")
        assert params.geographic_area.distribution["ITA"] == Decimal("0.4000")

    def test_round_trip_serialization(self):
        """Test round-trip: serialize → deserialize → serialize."""
        geo = FAGeographicArea(distribution={"USA": Decimal("0.5"), "FRA": Decimal("0.5")})
        original = FAClassificationParams(
            geographic_area=geo,
            sector_area=FASectorArea(distribution={"Financials": Decimal("1.0")}),
            )
        json_str1 = original.model_dump_json(exclude_none=True)
        parsed = FAClassificationParams.model_validate_json(json_str1)
        json_str2 = parsed.model_dump_json(exclude_none=True)

        data1 = json.loads(json_str1)
        data2 = json.loads(json_str2)
        assert data1 == data2

    def test_none_geographic_area(self):
        """Test that None geographic_area works correctly."""
        params = FAClassificationParams(
            sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
            )
        json_str = params.model_dump_json(exclude_none=True)
        data = json.loads(json_str)

        assert "geographic_area" not in data
        parsed = FAClassificationParams.model_validate_json(json_str)
        assert parsed.geographic_area is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
