"""
Scheduled Investment Provider — Pure Deterministic Engine with Cache.

This provider calculates synthetic values for scheduled-yield assets such as:
- Crowdfunding loans (P2P lending)
- Bonds with fixed interest schedules
- Any asset with predictable cash flows

The provider is PURE and DETERMINISTIC:
- Given provider_params → produces prices + events
- NO database access
- NO transaction dependency

Calculation is cached:
- Hash of canonical params → TTL cache (48h, theine timer wheel auto-expire)
- Single function generates ALL values for the schedule range
- Late interest computed on-demand from last scheduled value

How it works:
1. Receives provider_params with initial_value (Currency), schedule, asset_events
2. Generates all daily values for the schedule range (first period start → last period end)
3. Caches the result by params hash
4. For late interest (post-maturity): computes from last cached value + grace period

Global properties (from FAScheduledInvestmentSchedule):
- interest_type: SIMPLE (I = P₀ * r * Δt) or COMPOUND (I = V_{t-1} * r * Δt)
- day_count: Day count convention (ACT/365, ACT/360, etc.) — applies to all periods

Late interest (from FALateInterestConfig):
- interest_type: configurable per-event (default: COMPOUND — penalties grow on accumulated value)

For detailed parameter structure documentation, see:
- backend.app.schemas.assets.FAScheduledInvestmentSchedule
- backend.app.schemas.assets.FAInterestRatePeriod
"""

import hashlib
import json
from datetime import date as date_type, timedelta
from decimal import Decimal

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
    FAInterestRatePeriod,
    DayCountConvention,
    InterestType,
    MaturationFrequency,
    )
from backend.app.schemas.common import Currency
from backend.app.services.asset_source import AssetSourceProvider, AssetSourceError
from backend.app.services.provider_registry import register_provider, AssetProviderRegistry
from backend.app.utils.cache_utils import get_ttl_cache
from backend.app.utils.financial_math import (
    calculate_day_count_fraction,
    calculate_simple_interest,
    calculate_compound_interest,
    )

logger = get_logger(__name__)

# Cache: hash(params) → dict[date, Decimal] — all scheduled values
_CACHE = get_ttl_cache("scheduled_investment", maxsize=256, ttl=172800)  # 48h


def _cache_key(schedule: FAScheduledInvestmentSchedule) -> str:
    """Generate deterministic hash from canonical JSON of schedule params."""
    canonical = json.dumps(schedule.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.md5(canonical.encode()).hexdigest()


def _generate_schedule_values(
    schedule: FAScheduledInvestmentSchedule,
    ) -> dict[date_type, Decimal]:
    """
    Generate ALL daily values for the entire schedule range.

    This is the core calculation: from first period start to last period end,
    compute the value for each day.

    Interest calculation depends on schedule.interest_type:
    - SIMPLE: I = P₀ * r * Δt (always on initial principal)
    - COMPOUND: I = V_{t-1} * r * Δt (on running accumulated value)

    Day count convention is global (schedule.day_count).

    The result is cached by params hash for 48h (theine timer wheel auto-expire).

    Returns:
        Dict mapping date → value for every day in the schedule range.
    """
    key = _cache_key(schedule)

    # Check cache first — theine handles TTL expiration via timer wheel
    cached, ok = _CACHE.get(key)
    if ok:
        return cached

    principal = schedule.initial_value.amount
    is_compound = schedule.interest_type == InterestType.COMPOUND
    convention = schedule.day_count

    if not schedule.schedule:
        _CACHE.set(key, {})
        return {}

    first_start = schedule.schedule[0].start_date
    last_end = schedule.schedule[-1].end_date

    # Build period lookup: for each day, which period applies
    values: dict[date_type, Decimal] = {}
    total_interest = Decimal("0")

    # Pre-index events by date for O(1) lookup
    events_by_date: dict[date_type, list] = {}
    for e in schedule.asset_events:
        events_by_date.setdefault(e.date, []).append(e)

    # Track event adjustments cumulatively
    event_adjustment = Decimal("0")

    current_date = first_start
    current_period_idx = 0

    while current_date <= last_end:
        # Find active period for this date
        period = None
        for i in range(current_period_idx, len(schedule.schedule)):
            p = schedule.schedule[i]
            if p.start_date <= current_date <= p.end_date:
                period = p
                current_period_idx = i
                break

        # Calculate daily interest increment
        if period is not None and current_date > first_start:
            day_fraction = calculate_day_count_fraction(
                start_date=current_date - timedelta(days=1),
                end_date=current_date,
                convention=convention,
                )
            if day_fraction > 0:
                if is_compound:
                    # COMPOUND: interest on running value (principal + accumulated interest)
                    base = principal + total_interest
                    total_interest += calculate_simple_interest(
                        principal=base,
                        annual_rate=period.annual_rate,
                        time_fraction=day_fraction,
                        )
                else:
                    # SIMPLE: interest always on initial principal
                    total_interest += calculate_simple_interest(
                        principal=principal,
                        annual_rate=period.annual_rate,
                        time_fraction=day_fraction,
                        )

        # Apply events on this date
        if current_date in events_by_date:
            for evt in events_by_date[current_date]:
                if evt.type == "INTEREST":
                    event_adjustment -= evt.value.amount
                elif evt.type == "PRICE_ADJUSTMENT":
                    event_adjustment += evt.value.amount

        values[current_date] = principal + total_interest + event_adjustment
        current_date += timedelta(days=1)

    _CACHE.set(key, values)
    return values


def _compute_late_interest_value(
    schedule: FAScheduledInvestmentSchedule,
    target_date: date_type,
    last_scheduled_value: Decimal,
    maturity_date: date_type,
    ) -> Decimal:
    """
    Compute value for a date after schedule ends (grace + late interest).

    Late interest type is configurable per FALateInterestConfig.interest_type
    (defaults to COMPOUND — penalties grow on accumulated value).

    Args:
        schedule: Full schedule config (provides day_count, late_interest)
        target_date: The date to compute
        last_scheduled_value: Value at maturity_date (from cache)
        maturity_date: Last day of the schedule
    """
    if not schedule.late_interest:
        return last_scheduled_value

    li = schedule.late_interest
    is_compound = li.interest_type == InterestType.COMPOUND
    principal = schedule.initial_value.amount
    convention = schedule.day_count
    grace_end = maturity_date + timedelta(days=li.grace_period_days)

    # During grace period: use last scheduled rate
    if target_date <= grace_end:
        last_period = schedule.schedule[-1]
        if is_compound:
            # Day-by-day compound from maturity to target
            value = last_scheduled_value
            current = maturity_date + timedelta(days=1)
            while current <= target_date:
                frac = calculate_day_count_fraction(
                    start_date=current - timedelta(days=1),
                    end_date=current,
                    convention=convention,
                    )
                value += calculate_simple_interest(
                    principal=value,
                    annual_rate=last_period.annual_rate,
                    time_fraction=frac,
                    )
                current += timedelta(days=1)
            return value
        else:
            grace_fraction = calculate_day_count_fraction(
                start_date=maturity_date,
                end_date=target_date,
                convention=convention,
                )
            grace_interest = calculate_simple_interest(
                principal=principal,
                annual_rate=last_period.annual_rate,
                time_fraction=grace_fraction,
                )
            return last_scheduled_value + grace_interest

    # After grace: grace interest + late interest
    last_period = schedule.schedule[-1]
    if is_compound:
        # Day-by-day compound: grace period at last rate, then late rate
        value = last_scheduled_value
        current = maturity_date + timedelta(days=1)
        while current <= target_date:
            rate = last_period.annual_rate if current <= grace_end else li.annual_rate
            frac = calculate_day_count_fraction(
                start_date=current - timedelta(days=1),
                end_date=current,
                convention=convention,
                )
            value += calculate_simple_interest(
                principal=value,
                annual_rate=rate,
                time_fraction=frac,
                )
            current += timedelta(days=1)
        return value
    else:
        grace_fraction = calculate_day_count_fraction(
            start_date=maturity_date,
            end_date=grace_end,
            convention=convention,
            )
        grace_interest = calculate_simple_interest(
            principal=principal,
            annual_rate=last_period.annual_rate,
            time_fraction=grace_fraction,
            )

        late_fraction = calculate_day_count_fraction(
            start_date=grace_end,
            end_date=target_date,
            convention=convention,
            )
        late_interest = calculate_simple_interest(
            principal=principal,
            annual_rate=li.annual_rate,
            time_fraction=late_fraction,
            )

        return last_scheduled_value + grace_interest + late_interest


@register_provider(AssetProviderRegistry)
class ScheduledInvestmentProvider(AssetSourceProvider):
    """
    Provider for scheduled-yield assets (loans, bonds).

    Calculates synthetic values based on interest schedules.
    Pure deterministic engine — no external API calls, no DB access.
    Results are cached with 48h TTL.
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
                    initial_value=Currency(code="EUR", amount=Decimal("10000")),
                    day_count=DayCountConvention.ACT_365,
                    schedule=[
                        FAInterestRatePeriod(
                            start_date=date_type(2025, 1, 1),
                            end_date=date_type(2025, 12, 31),
                            annual_rate=Decimal("0.05"),
                            maturation_frequency=MaturationFrequency.DAILY,
                            )
                        ],
                    late_interest=None,
                    asset_events=[],
                    ).model_dump(),
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

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict,
        ) -> FACurrentValue:
        """
        Calculate current value for scheduled investment.

        Uses cached schedule values. For post-maturity dates,
        computes late interest one-shot from last cached value.
        """
        try:
            schedule = self.validate_params(provider_params)
            target_date = date_type.today()

            # Reference to cached schedule values (not a copy — safe, read-only access)
            cached = _generate_schedule_values(schedule)

            if target_date in cached:
                value = cached[target_date]
            elif cached and target_date > max(cached.keys()):
                # Post-maturity: compute late interest one-shot
                maturity_date = max(cached.keys())
                value = _compute_late_interest_value(
                    schedule, target_date, cached[maturity_date], maturity_date
                    )
            elif cached and target_date < min(cached.keys()):
                # Before schedule: return initial_value
                value = schedule.initial_value.amount
            else:
                value = schedule.initial_value.amount

            return FACurrentValue(
                value=value,
                currency=schedule.initial_value.code,
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

        Uses cached schedule values for the scheduled range.
        For post-maturity dates, iterates day-by-day applying late interest.
        """
        try:
            schedule = self.validate_params(provider_params)
            currency = schedule.initial_value.code
            principal = schedule.initial_value.amount

            # Reference to cached schedule values (not a copy — safe, read-only access)
            cached = _generate_schedule_values(schedule)
            maturity_date = max(cached.keys()) if cached else None

            prices = []
            current_date = start_date
            while current_date <= end_date:
                if current_date in cached:
                    value = cached[current_date]
                elif maturity_date and current_date > maturity_date:
                    value = _compute_late_interest_value(schedule, current_date, cached[maturity_date], maturity_date)
                else:
                    # Before schedule or empty: initial_value
                    value = principal

                prices.append(FAPricePoint(date=current_date, close=value, currency=currency))
                current_date += timedelta(days=1)

            # Events filtered to range
            events = [e for e in schedule.asset_events if start_date <= e.date <= end_date]

            return FAHistoricalData(
                prices=prices,
                events=events,
                currency=currency,
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

    def validate_params(self, provider_params: dict) -> FAScheduledInvestmentSchedule:
        """
        Validate provider parameters for scheduled investment.

        Uses Pydantic FAScheduledInvestmentSchedule model for validation.
        Requires initial_value (Currency) and schedule.
        """
        if not provider_params:
            raise AssetSourceError(
                "Provider params required for scheduled_investment",
                error_code="MISSING_PARAMS",
                details={"required": ["initial_value", "schedule"]},
                )

        try:
            return FAScheduledInvestmentSchedule(**provider_params)
        except ValueError as e:
            raise AssetSourceError(
                f"Invalid provider params: {e}",
                error_code="INVALID_PARAMS",
                details={"error": str(e)},
                )
