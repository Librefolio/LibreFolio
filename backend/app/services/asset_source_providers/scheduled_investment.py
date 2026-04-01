"""
Scheduled Investment Provider — Pure Deterministic Engine.

This provider calculates synthetic values for scheduled-yield assets such as:
- Crowdfunding loans (P2P lending)
- Bonds with fixed interest schedules
- Any asset with predictable cash flows

The provider is PURE and DETERMINISTIC:
- Given provider_params → produces prices + events
- NO database access
- NO transaction dependency

How it works:
1. Receives provider_params with initial_value, currency, schedule, asset_events
2. Calculates value for any date based on:
   - initial_value as base principal
   - Accrued interest from schedule periods
   - Asset events (INTEREST payments reduce price, PRICE_ADJUSTMENT modifies value)
3. Returns prices and events for the requested range

Supports:
- Multiple day count conventions: ACT/365, ACT/360, ACT/ACT, 30/360
- Interest types: SIMPLE and COMPOUND
- Multiple compounding frequencies: DAILY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL, CONTINUOUS
- Asset events: INTEREST (ex-date drop), PRICE_ADJUSTMENT (write-down/write-up)

For detailed parameter structure documentation, see:
- backend.app.schemas.assets.FAScheduledInvestmentSchedule
- backend.app.schemas.assets.FAInterestRatePeriod
- backend.app.schemas.assets.FALateInterestConfig
"""

from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional

from backend.app.db.models import (
    IdentifierType,
    ProviderInputType,
    )
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    FACurrentValue,
    FAHistoricalData,
    FAPricePoint,
    FAScheduledInvestmentSchedule,
    CompoundingType,
    FAInterestRatePeriod,
    DayCountConvention,
    )
from backend.app.schemas.prices import FAAssetEventPoint
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.utils.financial_math import (
    calculate_day_count_fraction,
    calculate_simple_interest,
    calculate_compound_interest,
    )

logger = get_logger(__name__)


@register_provider(AssetProviderRegistry)
class ScheduledInvestmentProvider(AssetSourceProvider):
    """
    Provider for scheduled-yield assets (loans, bonds).

    Calculates synthetic values based on interest schedules.
    Pure deterministic engine — no external API calls, no DB access.
    """

    @property
    def provider_code(self) -> str:
        return "scheduled_investment"

    @property
    def provider_name(self) -> str:
        return "Scheduled Investment Calculator"

    @property
    def accepted_identifier_types(self) -> list:
        return [ProviderInputType.AUTO_GENERATED]

    @property
    def get_icon(self) -> str:
        """Return provider icon URL from local static assets."""
        return self.generate_static_url("scheduled_investment.png")

    @property
    def provider_help_url(self) -> str:
        return "/mkdocs/user/assets/providers/scheduled-investment/"

    @property
    def params_schema(self) -> list[dict]:
        return [
            {
                "key": "_ui_component",
                "type": "ui_component",
                "required": False,
                "description": "Custom editor: ScheduledInvestmentEditor",
                "default": "scheduled_investment"
            },
        ]

    @property
    def test_cases(self) -> list[dict]:
        """Test cases for scheduled investment provider."""
        return [
            {
                "identifier": "test-scheduled-1",
                "provider_params": FAScheduledInvestmentSchedule(
                    initial_value=Decimal("10000"),
                    currency="EUR",
                    schedule=[
                        FAInterestRatePeriod(
                            start_date=date_type(2025, 1, 1),
                            end_date=date_type(2025, 12, 31),
                            annual_rate=Decimal("0.05"),
                            compounding=CompoundingType.SIMPLE,
                            day_count=DayCountConvention.ACT_365,
                            )
                        ],
                    late_interest=None,
                    asset_events=[],
                    ).model_dump(mode="json"),
                }
            ]

    @property
    def supports_search(self) -> bool:
        """Search not applicable for scheduled investments."""
        return False

    @property
    def supports_history(self) -> bool:
        """This provider supports historical data (calculated)."""
        return True

    @property
    def supports_events(self) -> bool:
        """This provider produces asset events."""
        return True

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict,
        ) -> FACurrentValue:
        """
        Calculate current value for scheduled investment.

        Pure deterministic: uses only provider_params, no DB access.

        Formula: value = initial_value + accrued_interest - Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)
        """
        try:
            schedule = self.validate_params(provider_params)
            target_date = date_type.today()
            value = self._calculate_value_for_date(schedule, target_date)

            return FACurrentValue(
                value=value,
                currency=schedule.currency,
                as_of_date=target_date,
                source=self.provider_name,
                )

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to calculate current value: {e}",
                error_code="CALCULATION_ERROR",
                details={"error": str(e)},
                )

    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict,
        start_date: date_type,
        end_date: date_type,
        ) -> FAHistoricalData:
        """
        Calculate historical values for scheduled investment.

        Pure deterministic: generates daily values for requested date range.
        Also returns asset events filtered to the requested range.
        """
        try:
            schedule = self.validate_params(provider_params)

            # Generate daily prices
            prices = []
            current_date = start_date
            while current_date <= end_date:
                value = self._calculate_value_for_date(schedule, current_date)
                prices.append(FAPricePoint(date=current_date, close=value, currency=schedule.currency))
                current_date += timedelta(days=1)

            # Build events list from schedule.asset_events filtered to range
            events = [
                FAAssetEventPoint(
                    date=e.date,
                    type=e.type,
                    value=e.value,
                    currency=e.currency,
                    notes=e.notes,
                    )
                for e in schedule.asset_events
                if start_date <= e.date <= end_date
                ]

            return FAHistoricalData(
                prices=prices,
                events=events,
                currency=schedule.currency,
                source=self.provider_name,
                )

        except AssetSourceError:
            raise
        except Exception as e:
            raise AssetSourceError(
                f"Failed to calculate history: {e}",
                error_code="CALCULATION_ERROR",
                details={"error": str(e)},
                )

    @property
    def test_search_query(self) -> str | None:
        """Search not applicable for scheduled investments."""
        return None

    async def search(self, query: str) -> list[dict]:
        """Search not applicable for scheduled investments."""
        raise AssetSourceError(
            "Search not supported for scheduled_investment provider",
            error_code="NOT_SUPPORTED",
            details={"message": "Scheduled investments require manual configuration"},
            )

    def _calculate_value_for_date(
        self,
        schedule: FAScheduledInvestmentSchedule,
        target_date: date_type,
        ) -> Decimal:
        """Period-based synthetic value calculation.

        Pure deterministic: given schedule config, produce a price for any date.

        Steps:
          1. Start with initial_value (face_value).
          2. Calculate accrued interest from schedule periods up to target_date.
          3. Handle post-maturity (grace + late interest).
          4. Apply asset events:
             - INTEREST: subtract from price (ex-date drop — user received cash)
             - PRICE_ADJUSTMENT: add algebraically (negative = write-down)
          5. Return face_value + total_interest - Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)

        Interest is ALWAYS calculated on initial_value, not on the current running value.
        Per-period compounding handles simple/compound within each period.
        """
        face_value = schedule.initial_value

        if not schedule.schedule:
            return face_value

        first_start = schedule.schedule[0].start_date
        maturity_date = schedule.schedule[-1].end_date

        if target_date < first_start:
            # Before any schedule starts: apply only events before this date
            event_adjustment = self._calculate_event_adjustment(schedule, target_date)
            return face_value + event_adjustment

        periods_to_process: list[FAInterestRatePeriod] = []

        # 1. Real scheduled periods (truncate to target_date)
        for p in schedule.schedule:
            if p.start_date > target_date:
                break
            eff_start = p.start_date
            eff_end = p.end_date if p.end_date <= target_date else target_date
            if eff_end >= eff_start:
                periods_to_process.append(
                    FAInterestRatePeriod(
                        start_date=eff_start,
                        end_date=eff_end,
                        annual_rate=p.annual_rate,
                        compounding=p.compounding,
                        compound_frequency=p.compound_frequency,
                        day_count=p.day_count,
                        )
                    )

        # 2. Post-maturity synthetic periods
        if target_date > maturity_date and schedule.late_interest:
            li = schedule.late_interest
            grace_end = maturity_date + timedelta(days=li.grace_period_days)
            last_rate_period = schedule.schedule[-1]

            # Grace segment
            grace_start = maturity_date + timedelta(days=1)
            if grace_start <= target_date and li.grace_period_days > 0:
                grace_segment_end = min(grace_end, target_date)
                if grace_segment_end >= grace_start:
                    periods_to_process.append(
                        FAInterestRatePeriod(
                            start_date=grace_start,
                            end_date=grace_segment_end,
                            annual_rate=last_rate_period.annual_rate,
                            compounding=last_rate_period.compounding,
                            compound_frequency=last_rate_period.compound_frequency,
                            day_count=last_rate_period.day_count,
                            )
                        )

            # Late segment (after grace_end)
            late_start = grace_end + timedelta(days=1)
            if target_date >= late_start:
                late_end = target_date
                if late_end >= late_start:
                    periods_to_process.append(
                        FAInterestRatePeriod(
                            start_date=late_start,
                            end_date=late_end,
                            annual_rate=li.annual_rate,
                            compounding=li.compounding,
                            compound_frequency=li.compound_frequency,
                            day_count=li.day_count,
                            )
                        )

        # 3. Sum interest per period
        total_interest = Decimal("0")
        for period in periods_to_process:
            time_fraction = calculate_day_count_fraction(
                start_date=period.start_date,
                end_date=period.end_date,
                convention=period.day_count,
                )
            if time_fraction <= 0:
                continue
            if period.compounding == CompoundingType.SIMPLE:
                segment_interest = calculate_simple_interest(
                    principal=face_value,
                    annual_rate=period.annual_rate,
                    time_fraction=time_fraction,
                    )
            else:
                if period.compound_frequency is None:
                    raise ValueError("compound_frequency required for COMPOUND interest")
                segment_interest = calculate_compound_interest(
                    principal=face_value,
                    annual_rate=period.annual_rate,
                    time_fraction=time_fraction,
                    frequency=period.compound_frequency,
                    )
            total_interest += segment_interest

        # 4. Apply asset events
        event_adjustment = self._calculate_event_adjustment(schedule, target_date)

        return face_value + total_interest + event_adjustment

    @staticmethod
    def _calculate_event_adjustment(
        schedule: FAScheduledInvestmentSchedule,
        target_date: date_type,
        ) -> Decimal:
        """Calculate net adjustment from asset events up to target_date.

        - INTEREST events: subtract from price (ex-date drop, user received cash)
        - PRICE_ADJUSTMENT events: add algebraically (negative = write-down, positive = write-up)
        """
        adjustment = Decimal("0")
        for event in schedule.asset_events:
            if event.date <= target_date:
                if event.type == "INTEREST":
                    adjustment -= event.value
                elif event.type == "PRICE_ADJUSTMENT":
                    adjustment += event.value
        return adjustment

    def validate_params(self, provider_params: dict) -> FAScheduledInvestmentSchedule:
        """
        Validate provider parameters for scheduled investment.

        Uses Pydantic FAScheduledInvestmentSchedule model for validation.
        Requires initial_value, currency, and schedule.
        """
        if not provider_params:
            raise AssetSourceError(
                "Provider params required for scheduled_investment",
                error_code="MISSING_PARAMS",
                details={"required": ["initial_value", "currency", "schedule"]},
                )

        try:
            return FAScheduledInvestmentSchedule(**provider_params)
        except ValueError as e:
            raise AssetSourceError(
                f"Invalid provider params: {e}",
                error_code="INVALID_PARAMS",
                details={"error": str(e)},
                )
