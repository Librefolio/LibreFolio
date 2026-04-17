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

import calendar
import hashlib
import json
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

from backend.app.db.models import (
    IdentifierType,
    ProviderInputType,
)
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    DayCountConvention,
    FACurrentValue,
    FAHistoricalData,
    FAInterestRatePeriod,
    FAPricePoint,
    FAScheduledInvestmentSchedule,
    InterestType,
    MaturationFrequency,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FAAssetEventPoint
from backend.app.services.asset_source import AssetSourceError, AssetSourceProvider
from backend.app.services.provider_registry import AssetProviderRegistry, register_provider
from backend.app.utils.cache_utils import get_ttl_cache

# ============================================================================
# FINANCIAL MATH — Day count conventions & simple interest
# ============================================================================


def calculate_day_count_fraction(
    start_date: date_type,
    end_date: date_type,
    convention: DayCountConvention = DayCountConvention.ACT_365,
) -> Decimal:
    """
    Calculate day fraction using specified day count convention.

    Supports multiple conventions:
    - ACT/365: Actual days / 365
    - ACT/360: Actual days / 360
    - ACT/ACT: Actual days / actual days in year (365 or 366 if leap year)
    - 30/360: Assumes 30 days per month, 360 days per year

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        convention: Day count convention to use

    Returns:
        Decimal fraction representing the time period
    """
    if convention == DayCountConvention.ACT_365:
        return _calculate_act_fixed(start_date, end_date, 365)
    elif convention == DayCountConvention.ACT_360:
        return _calculate_act_fixed(start_date, end_date, 360)
    elif convention == DayCountConvention.ACT_ACT:
        return _calculate_act_act(start_date, end_date)
    elif convention == DayCountConvention.THIRTY_360:
        return _calculate_30_360(start_date, end_date)
    else:
        raise ValueError(f"Unsupported day count convention: {convention}")


def _calculate_act_fixed(start_date: date_type, end_date: date_type, denominator: int) -> Decimal:
    """ACT/N: Actual days / fixed denominator (365 or 360)."""
    days = (end_date - start_date).days
    return Decimal(days) / Decimal(denominator)


def _calculate_act_act(start_date: date_type, end_date: date_type) -> Decimal:
    """
    ACT/ACT: Actual days / actual days in year.

    Handles leap years correctly by calculating the fraction for each year separately.
    """
    if start_date.year == end_date.year:
        days = (end_date - start_date).days
        days_in_year = 366 if calendar.isleap(start_date.year) else 365
        return Decimal(days) / Decimal(days_in_year)

    total_fraction = Decimal("0")
    current_year = start_date.year

    last_year = end_date.year
    if end_date.month == 1 and end_date.day == 1:
        last_year -= 1

    while current_year <= last_year:
        if current_year == start_date.year:
            period_start = start_date
            if current_year == last_year:
                period_end = end_date
            else:
                period_end = date_type(current_year, 12, 31)
        elif current_year == last_year:
            period_start = date_type(current_year, 1, 1)
            period_end = end_date
        else:
            period_start = date_type(current_year, 1, 1)
            period_end = date_type(current_year, 12, 31)

        days = (period_end - period_start).days
        days_in_year = 366 if calendar.isleap(current_year) else 365
        total_fraction += Decimal(days) / Decimal(days_in_year)
        current_year += 1

    return total_fraction


def _calculate_30_360(start_date: date_type, end_date: date_type) -> Decimal:
    """
    30/360: Assumes 30 days per month, 360 days per year (US NASD convention).
    """
    d1 = start_date.day
    d2 = end_date.day
    m1 = start_date.month
    m2 = end_date.month
    y1 = start_date.year
    y2 = end_date.year

    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 >= 30:
        d2 = 30

    days = (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)
    return Decimal(days) / Decimal(360)


def calculate_simple_interest(principal: Decimal, annual_rate: Decimal, time_fraction: Decimal) -> Decimal:
    """
    Calculate simple interest: I = P * r * t.

    Args:
        principal: Principal amount
        annual_rate: Annual interest rate (e.g., 0.05 for 5%)
        time_fraction: Time period as fraction of year

    Returns:
        Interest earned
    """
    return principal * annual_rate * time_fraction


# ============================================================================
# MATURATION DATES HELPER
# ============================================================================


def _compute_maturation_dates(start: date_type, end: date_type, frequency: MaturationFrequency) -> set[date_type]:
    """Compute all maturation dates within [start, end] for given frequency.

    Always includes start and end as anchors.
    """
    from dateutil.relativedelta import relativedelta

    dates = {start, end}
    if frequency == MaturationFrequency.DAILY:
        d = start
        while d <= end:
            dates.add(d)
            d += timedelta(days=1)
        return dates

    delta_map = {
        MaturationFrequency.WEEKLY: relativedelta(weeks=1),
        MaturationFrequency.MONTHLY: relativedelta(months=1),
        MaturationFrequency.QUARTERLY: relativedelta(months=3),
        MaturationFrequency.SEMIANNUAL: relativedelta(months=6),
        MaturationFrequency.ANNUAL: relativedelta(years=1),
    }
    delta = delta_map[frequency]
    d = start
    while d <= end:
        dates.add(d)
        d += delta
    return dates


logger = get_logger(__name__)

# Cache: hash(params) → dict[date, Decimal] — all scheduled values at maturation dates
_CACHE = get_ttl_cache("scheduled_investment", maxsize=256, ttl=172800)  # 48h


def _cache_key(schedule: FAScheduledInvestmentSchedule) -> str:
    """Generate deterministic hash from canonical JSON of schedule params."""
    canonical = json.dumps(schedule.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.md5(canonical.encode()).hexdigest()


def _generate_schedule_values(
    schedule: FAScheduledInvestmentSchedule,
) -> tuple[dict[date_type, Decimal], list[FAAssetEventPoint]]:
    """
    Generate values for the entire schedule range at maturation dates.

    The engine computes day-by-day internally (for correctness), but emits
    price points only at maturation dates defined by each period's
    maturation_frequency. Start and end dates of each period are always
    included as anchors.

    When generate_interest=True on a period, at each maturation date the engine
    auto-generates an INTEREST event (coupon). After the coupon, the value resets
    to initial_value and compound interest restarts from there.

    Returns:
        Tuple of (values dict, auto_events list).
        - values: date → Decimal for maturation dates in the schedule range
        - auto_events: list of FAAssetEventPoint auto-generated (INTEREST + MATURITY_SETTLEMENT)
    """
    key = _cache_key(schedule)

    # Check cache first — theine handles TTL expiration via timer wheel
    cached, ok = _CACHE.get(key)
    if ok:
        return cached

    principal = schedule.initial_value.amount
    currency_code = schedule.initial_value.code
    is_compound = schedule.interest_type == InterestType.COMPOUND
    convention = schedule.day_count

    if not schedule.schedule:
        empty = ({}, [])
        _CACHE.set(key, empty)
        return empty

    first_start = schedule.schedule[0].start_date
    last_end = schedule.schedule[-1].end_date

    # Pre-compute all maturation dates across all periods
    all_maturation_dates: set[date_type] = set()
    for p in schedule.schedule:
        all_maturation_dates |= _compute_maturation_dates(p.start_date, p.end_date, p.maturation_frequency)

    values: dict[date_type, Decimal] = {}
    auto_events: list[FAAssetEventPoint] = []
    total_interest = Decimal("0")

    # Pre-index manual events by date for O(1) lookup
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

        # === D8 Step 1: Calculate daily interest increment ===
        if period is not None and current_date > first_start:
            day_fraction = calculate_day_count_fraction(
                start_date=current_date - timedelta(days=1),
                end_date=current_date,
                convention=convention,
            )
            if day_fraction > 0:
                if is_compound:
                    # COMPOUND interest formula: I = V_{t-1} * r * Δt
                    base = principal + total_interest
                    total_interest += calculate_simple_interest(
                        principal=base,
                        annual_rate=period.annual_rate,
                        time_fraction=day_fraction,
                    )
                else:
                    # Simple interest formula: I = P₀ * r * Δt
                    total_interest += calculate_simple_interest(
                        principal=principal,
                        annual_rate=period.annual_rate,
                        time_fraction=day_fraction,
                    )

        # === D8 Step 2: Auto-coupon at maturation date (generate_interest) ===
        if current_date in all_maturation_dates and period and period.generate_interest:
            current_value = principal + total_interest + event_adjustment
            interest_amount = current_value - principal
            if interest_amount > 0:
                auto_events.append(
                    FAAssetEventPoint(
                        date=current_date,
                        type="INTEREST",
                        value=Currency(code=currency_code, amount=interest_amount),
                        notes="Auto-generated interest payout",
                    )
                )
                # Reset: value returns to initial_value (D1/D2)
                # Coupon includes both accrued interest + any price adjustments
                total_interest = Decimal("0")
                event_adjustment = Decimal("0")

        # === D8 Step 3: Apply manual events on this date ===
        if current_date in events_by_date:
            for evt in events_by_date[current_date]:
                if evt.type == "INTEREST":
                    event_adjustment -= evt.value.amount
                elif evt.type == "PRICE_ADJUSTMENT":
                    event_adjustment += evt.value.amount

        # === D8 Step 4: Emit value only at maturation dates ===
        if current_date in all_maturation_dates:
            values[current_date] = principal + total_interest + event_adjustment
        current_date += timedelta(days=1)

    # === D6: MATURITY_SETTLEMENT at end of schedule (if no late interest) ===
    last_period = schedule.schedule[-1]
    if last_period.generate_interest and not schedule.late_interest:
        settlement_value = values.get(last_end, principal)
        auto_events.append(
            FAAssetEventPoint(
                date=last_end,
                type="MATURITY_SETTLEMENT",
                value=Currency(code=currency_code, amount=settlement_value),
                notes="Maturity settlement — asset closed",
            )
        )

    result = (values, auto_events)
    _CACHE.set(key, result)
    return result


def _compute_late_interest_value(
    schedule: FAScheduledInvestmentSchedule,
    target_date: date_type,
    last_scheduled_value: Decimal,
    maturity_date: date_type,
) -> Decimal:
    """
    Compute value for a date after schedule ends (grace + late interest).

    Uses skip formula (D9) for efficiency:
    - SIMPLE: closed-form V = V_maturity + P * r * Δt
    - COMPOUND: day-by-day only for the requested sub-range

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
    last_period = schedule.schedule[-1]

    if target_date <= grace_end:
        # During grace period: use last scheduled rate
        if is_compound:
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
            # SIMPLE skip formula: V = V_maturity + P * r * Δt
            grace_fraction = calculate_day_count_fraction(
                start_date=maturity_date,
                end_date=target_date,
                convention=convention,
            )
            return last_scheduled_value + calculate_simple_interest(
                principal=principal,
                annual_rate=last_period.annual_rate,
                time_fraction=grace_fraction,
            )

    # After grace: grace interest + late interest
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
        # SIMPLE skip formula for both grace + late segments
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
            {"key": "_ui_component", "type": "ui_component", "required": False, "description": "Custom editor: ScheduledInvestmentEditor", "default": "scheduled_investment"},
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

            # Destructure cached tuple (values, auto_events)
            cached, auto_events = _generate_schedule_values(schedule)

            # Check for MATURITY_SETTLEMENT — if past settlement, return settlement value
            settlement_evt = next((e for e in auto_events if e.type == "MATURITY_SETTLEMENT"), None)
            if settlement_evt and target_date >= settlement_evt.date:
                return FACurrentValue(
                    value=settlement_evt.value.amount,
                    currency=schedule.initial_value.code,
                    as_of_date=target_date,
                    source=self.provider_name,
                )

            if target_date in cached:
                value = cached[target_date]
            elif cached and target_date > max(cached.keys()):
                # Post-maturity: compute late interest one-shot
                maturity_date = max(cached.keys())
                value = _compute_late_interest_value(schedule, target_date, cached[maturity_date], maturity_date)
            elif cached and target_date < min(cached.keys()):
                # Before schedule: return initial_value
                value = schedule.initial_value.amount
            elif cached:
                # Between maturation dates: use most recent cached value (backward-fill)
                earlier_dates = [d for d in cached.keys() if d <= target_date]
                if earlier_dates:
                    value = cached[max(earlier_dates)]
                else:
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
            ) from e

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

        Emits price points only at maturation dates (selective emission).
        Uses cached schedule values for the scheduled range.
        For post-maturity dates, computes at late interest maturation dates.
        """
        try:
            schedule = self.validate_params(provider_params)
            currency = schedule.initial_value.code
            principal = schedule.initial_value.amount

            # Destructure cached tuple (values, auto_events)
            cached, cached_auto_events = _generate_schedule_values(schedule)
            maturity_date = max(cached.keys()) if cached else None

            # Check for MATURITY_SETTLEMENT in cached events
            settlement_evt = next((e for e in cached_auto_events if e.type == "MATURITY_SETTLEMENT"), None)
            settlement_date = settlement_evt.date if settlement_evt else None

            prices = []

            # Emit cached values that fall within the requested range
            for d in sorted(cached.keys()):
                if start_date <= d <= end_date:
                    prices.append(FAPricePoint(date=d, close=cached[d], currency=currency))

            # Handle post-maturity range with late interest maturation dates
            late_auto_events: list[FAAssetEventPoint] = []
            if maturity_date and end_date > maturity_date and schedule.late_interest:
                li = schedule.late_interest
                late_start = max(maturity_date + timedelta(days=1), start_date)
                late_mat_dates = _compute_maturation_dates(
                    maturity_date + timedelta(days=1),
                    end_date,
                    li.maturation_frequency,
                )
                sorted_late_dates = sorted(late_mat_dates)
                last_late_date = sorted_late_dates[-1] if sorted_late_dates else None

                for d in sorted_late_dates:
                    if late_start <= d <= end_date:
                        # Skip if past settlement
                        if settlement_date and d > settlement_date:
                            break
                        value = _compute_late_interest_value(schedule, d, cached[maturity_date], maturity_date)
                        prices.append(FAPricePoint(date=d, close=value, currency=currency))

                        # Auto-generate late INTEREST events if generate_interest=True
                        if li.generate_interest:
                            interest_amount = value - principal
                            if interest_amount > 0:
                                late_auto_events.append(
                                    FAAssetEventPoint(
                                        date=d,
                                        type="INTEREST",
                                        value=Currency(code=currency, amount=interest_amount),
                                        notes="Auto-generated late interest payout",
                                    )
                                )

                # Late interest MATURITY_SETTLEMENT at last maturation date
                if li.generate_interest and last_late_date and not settlement_date:
                    settle_value = _compute_late_interest_value(schedule, last_late_date, cached[maturity_date], maturity_date)
                    late_auto_events.append(
                        FAAssetEventPoint(
                            date=last_late_date,
                            type="MATURITY_SETTLEMENT",
                            value=Currency(code=currency, amount=settle_value),
                            notes="Late interest maturity settlement — asset closed",
                        )
                    )

            elif maturity_date and end_date > maturity_date:
                # No late interest config — emit maturity value as flat line at end_date
                if end_date not in cached:
                    if not settlement_date or end_date <= settlement_date:
                        prices.append(FAPricePoint(date=end_date, close=cached[maturity_date], currency=currency))

            # If past settlement, emit settlement value as final anchor
            if settlement_date and end_date > settlement_date:
                # Ensure no prices after settlement
                prices = [p for p in prices if p.date <= settlement_date]
                if end_date > settlement_date:
                    prices.append(FAPricePoint(date=end_date, close=settlement_evt.value.amount, currency=currency))

            # If start_date is before schedule, emit initial_value as anchor
            if cached and start_date < min(cached.keys()):
                prices.insert(0, FAPricePoint(date=start_date, close=principal, currency=currency))

            # Sort by date (in case late interest dates interleave)
            prices.sort(key=lambda p: p.date)

            # Merge cached auto-events + late auto-events + manual events, filtered to range
            all_events = [e for e in cached_auto_events if start_date <= e.date <= end_date]
            all_events += [e for e in late_auto_events if start_date <= e.date <= end_date]
            all_events += [e for e in schedule.asset_events if start_date <= e.date <= end_date]
            all_events.sort(key=lambda e: e.date)

            return FAHistoricalData(
                prices=prices,
                events=all_events,
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
            ) from e

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
            # Return a default schedule with initial_value for probe support
            # (allows "Test Connection" to work before any periods are configured)
            return FAScheduledInvestmentSchedule(
                initial_value=Currency(code="EUR", amount=Decimal("10000")),
                schedule=[],
            )

        try:
            return FAScheduledInvestmentSchedule(**provider_params)
        except ValueError as e:
            raise AssetSourceError(
                f"Invalid provider params: {e}",
                error_code="INVALID_PARAMS",
                details={"error": str(e)},
            ) from e
