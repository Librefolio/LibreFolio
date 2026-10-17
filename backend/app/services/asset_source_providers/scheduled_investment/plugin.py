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
- backend.app.schemas.assets.scheduled_investment.FAScheduledInvestmentSchedule
- backend.app.schemas.assets.scheduled_investment.FAInterestRatePeriod
"""

import hashlib
import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

from backend.app.db.models import (
    IdentifierType,
    ProviderInputType,
)
from backend.app.logging_config import get_logger
from backend.app.schemas.assets.events import FAAssetEventPoint
from backend.app.schemas.assets.scheduled_investment import (
    SCHEDULE_MAX_DATE,
    DayCountConvention,
    FAInterestRatePeriod,
    FAScheduledInvestmentSchedule,
    InterestType,
    MaturationFrequency,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import (
    FACurrentValue,
    FAHistoricalData,
    FAPricePoint,
)
from backend.app.schemas.provider import FAProviderKind
from backend.app.services.assets.base import AssetHistoryStartDate, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.financial_math.interest import calculate_day_count_fraction, calculate_simple_interest, compound_growth
from backend.app.services.provider_registry import register_provider
from backend.app.utils.runtime.cache import get_ttl_cache

# ============================================================================
# MATURATION DATES HELPER
# ============================================================================


def _compute_maturation_dates(start: date_type, end: date_type, frequency: MaturationFrequency) -> set[date_type]:
    """Compute all maturation dates within [start, end] for given frequency.

    Always includes start and end as anchors.
    """
    from dateutil.relativedelta import relativedelta  # noqa: PLC0415 — lazy import / avoid circular

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
# A result with more points is computed on every call, never stored: ten years of DAILY points (~1 MB), so the 256
# entries stay bounded (R13-SEC7-2, N73).
_CACHE_MAX_POINTS = 3_660


def _cache_key(schedule: FAScheduledInvestmentSchedule) -> str:
    """Generate deterministic hash from canonical JSON of schedule params."""
    canonical = json.dumps(schedule.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.md5(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class _AccrualDay:
    """One day of a schedule's accrual walk.

    ``value`` is the value at the end of the day: after the day's interest and manual events, before an auto-coupon.
    ``coupon`` is the day's auto-generated payout, if any — everything above the principal, paid at a maturation date
    of a ``generate_interest`` period, after which the accrual restarts from the principal.
    """

    day: date_type
    value: Decimal
    is_maturation: bool
    coupon: Decimal | None


def _schedule_maturation_dates(schedule: FAScheduledInvestmentSchedule) -> set[date_type]:
    """The maturation dates of every period of the schedule (each period's start and end included)."""
    dates: set[date_type] = set()
    for period in schedule.schedule:
        dates |= _compute_maturation_dates(period.start_date, period.end_date, period.maturation_frequency)
    return dates


def _manual_events_by_date(schedule: FAScheduledInvestmentSchedule) -> dict[date_type, list[FAAssetEventPoint]]:
    """The schedule's manual events by date, in their given order."""
    events_by_date: dict[date_type, list[FAAssetEventPoint]] = {}
    for event in schedule.asset_events:
        events_by_date.setdefault(event.date, []).append(event)
    return events_by_date


def _active_period(periods: list[FAInterestRatePeriod], day: date_type, start_index: int) -> tuple[FAInterestRatePeriod | None, int]:
    """The period covering ``day``, searched from ``start_index`` on, and its index (``start_index`` when none does)."""
    for index in range(start_index, len(periods)):
        period = periods[index]
        if period.start_date <= day <= period.end_date:
            return period, index
    return None, start_index


def _apply_manual_events(event_adjustment: Decimal, events: Iterable[FAAssetEventPoint]) -> Decimal:
    """The running adjustment after a day's manual events: an INTEREST payout lowers it, a PRICE_ADJUSTMENT moves it."""
    for event in events:
        if event.type == "INTEREST":
            event_adjustment -= event.value.amount
        elif event.type == "PRICE_ADJUSTMENT":
            event_adjustment += event.value.amount
    return event_adjustment


def _accrual_days(schedule: FAScheduledInvestmentSchedule, until: date_type) -> Iterator[_AccrualDay]:
    """Walk a non-empty schedule day by day, from its first start to ``until`` included.

    The provider's one accrual walk: the history curve (``_generate_schedule_values``) and the value on one day
    (``_compute_value_at``) both read it. Each day, in order:

    1. the interest of the day at the active period's rate — SIMPLE: I = P₀ · r · Δt, on the principal; COMPOUND:
       I = (P₀ + accrued interest) · r · Δt — none on the first day, nor on a day no period covers;
    2. the manual events of the day (``_apply_manual_events``);
    3. the day's value, yielded with its coupon;
    4. a paid coupon resets the accrued interest and the manual adjustments: the next day restarts from the principal.
    """
    principal = schedule.initial_value.amount
    is_compound = schedule.interest_type == InterestType.COMPOUND
    first_start = schedule.schedule[0].start_date
    maturation_dates = _schedule_maturation_dates(schedule)
    events_by_date = _manual_events_by_date(schedule)

    total_interest = Decimal("0")
    event_adjustment = Decimal("0")
    current_date = first_start
    period_index = 0
    while current_date <= until:
        period, period_index = _active_period(schedule.schedule, current_date, period_index)
        if period is not None and current_date > first_start:
            day_fraction = calculate_day_count_fraction(
                start_date=current_date - timedelta(days=1),
                end_date=current_date,
                convention=schedule.day_count,
            )
            if day_fraction > 0:
                base = principal + total_interest if is_compound else principal
                total_interest += calculate_simple_interest(principal=base, annual_rate=period.annual_rate, time_fraction=day_fraction)
        event_adjustment = _apply_manual_events(event_adjustment, events_by_date.get(current_date, ()))

        value = principal + total_interest + event_adjustment
        is_maturation = current_date in maturation_dates
        coupon = value - principal if is_maturation and period is not None and period.generate_interest and value - principal > 0 else None
        yield _AccrualDay(day=current_date, value=value, is_maturation=is_maturation, coupon=coupon)

        if coupon is not None:
            total_interest = Decimal("0")
            event_adjustment = Decimal("0")
        current_date += timedelta(days=1)


def _log_cache_lookup(key: str, schedule: FAScheduledInvestmentSchedule, *, hit: bool) -> None:
    first = schedule.schedule[0] if schedule.schedule else None
    logger.debug(
        "scheduled_investment cache %s key=%s periods=%d first_freq=%s first_gen_int=%s",
        "HIT" if hit else "MISS",
        key[:8],
        len(schedule.schedule),
        first.maturation_frequency if first else "-",
        first.generate_interest if first else "-",
    )


def _generate_schedule_values(
    schedule: FAScheduledInvestmentSchedule,
) -> tuple[dict[date_type, Decimal], list[FAAssetEventPoint]]:
    """
    Generate values for the entire schedule range at maturation dates.

    The engine computes day-by-day internally (``_accrual_days``, for correctness), but emits
    price points only at maturation dates defined by each period's
    maturation_frequency. Start and end dates of each period are always
    included as anchors.

    A maturation date's value is the accrued one, before its coupon (I-bis #26: emitted after the
    reset, a generate_interest + DAILY schedule drew a flat ``initial_value`` line).

    When generate_interest=True on a period, at each maturation date the engine
    auto-generates an INTEREST event (coupon), dated on the maturation date where the chart shows
    the peak. After the coupon, the value resets to initial_value and the accrual restarts from there.

    Without late interest, the last period closes the asset with a MATURITY_SETTLEMENT on its end date, worth
    what is left after that day's coupon: the principal when the final coupon is paid (it resets the value), the
    day's value when no coupon is paid. The final coupon is the INTEREST event of that day, never counted twice (J-39).

    Returns:
        Tuple of (values dict, auto_events list).
        - values: date → Decimal for maturation dates in the schedule range
        - auto_events: list of FAAssetEventPoint auto-generated (INTEREST + MATURITY_SETTLEMENT)
    """
    key = _cache_key(schedule)

    # Check cache first — theine handles TTL expiration via timer wheel
    cached, ok = _CACHE.get(key)
    if ok:
        _log_cache_lookup(key, schedule, hit=True)
        return cached
    _log_cache_lookup(key, schedule, hit=False)

    if not schedule.schedule:
        empty = ({}, [])
        _CACHE.set(key, empty)
        return empty

    principal = schedule.initial_value.amount
    currency_code = schedule.initial_value.code
    last_end = schedule.schedule[-1].end_date

    values: dict[date_type, Decimal] = {}
    auto_events: list[FAAssetEventPoint] = []
    last_coupon_day: date_type | None = None
    for day in _accrual_days(schedule, last_end):
        if day.is_maturation:
            values[day.day] = day.value
        if day.coupon is not None:
            last_coupon_day = day.day
            # Reset: value returns to initial_value (D1/D2); the coupon includes both accrued interest and any price adjustments.
            auto_events.append(
                FAAssetEventPoint(
                    date=day.day,
                    type="INTEREST",
                    value=Currency(code=currency_code, amount=day.coupon),
                    notes="Auto-generated interest payout",
                )
            )

    # === D6: MATURITY_SETTLEMENT at end of schedule (if no late interest) ===
    last_period = schedule.schedule[-1]
    if last_period.generate_interest and not schedule.late_interest:
        # values[last_end] is the pre-coupon peak the chart draws: after a final coupon only the principal is left.
        settlement_value = principal if last_coupon_day == last_end else values.get(last_end, principal)
        auto_events.append(
            FAAssetEventPoint(
                date=last_end,
                type="MATURITY_SETTLEMENT",
                value=Currency(code=currency_code, amount=settlement_value),
                notes="Maturity settlement — asset closed",
            )
        )

    result = (values, auto_events)
    if len(values) <= _CACHE_MAX_POINTS:
        _CACHE.set(key, result)
    return result


def _compute_value_at(
    schedule: FAScheduledInvestmentSchedule,
    target_date: date_type,
) -> Decimal | None:
    """
    Compute the accrued value at ``target_date`` — the "current_price"
    helper.

    **Why this exists** (retest 2026-04-24, follow-up to I-bis #26 fix):
    ``_generate_schedule_values`` only emits values at *maturation dates*
    (so the cached dict is sparse for SEMIANNUAL / WEEKLY schedules).
    Previously, ``get_current_value`` would backward-fill from the most
    recent maturation date, which returned the **pre-reset peak** — i.e.
    the value right before the auto-coupon was paid. That is wrong for any
    day **after** a coupon: the real accrual has restarted from
    ``initial_value`` (D1/D2 reset) and only the intra-cycle days matter.

    Example (BTP-style, SEMIANNUAL, generate_interest=True, start Jan 1):
      - cached[Jul 1] = principal + 6mo interest  (peak, pre-reset)
      - On Jul 2 the value resets to ``initial_value``.
      - Today = Oct 15 → the correct value is ``initial_value + 3.5mo
        interest``, *not* cached[Jul 1].

    It reads the same walk as the history curve (``_accrual_days``) up to
    ``target_date``, so manual events (INTEREST coupons, PRICE_ADJUSTMENT)
    and auto-coupon resets apply on the way, and returns the value of that
    day: after its manual events, before an auto-coupon reset it would pay —
    the chart peak ``_generate_schedule_values`` emits.

    The walk is bounded by ``target_date`` (not ``last_end``) so cost is
    O(days-since-start); no caching is needed because this is called
    once per current-price sync. ``_generate_schedule_values`` remains
    the cached source of truth for the *history* curve.

    Returns:
        ``Decimal`` with the accrued value at ``target_date``, or
        ``None`` if ``target_date`` falls outside the schedule range
        (caller decides fallback).
    """
    if not schedule.schedule:
        return None

    first_start = schedule.schedule[0].start_date
    last_end = schedule.schedule[-1].end_date
    if target_date < first_start or target_date > last_end:
        return None

    value = schedule.initial_value.amount
    for day in _accrual_days(schedule, target_date):
        value = day.value
    return value


def _late_compound_growth(schedule: FAScheduledInvestmentSchedule, start: date_type, end: date_type, maturity_date: date_type) -> Decimal:
    """The COMPOUND late-interest growth from ``start`` to ``end``: a day up to the end of the grace period accrues at the
    last period's rate, a day after it at the late rate."""
    li = schedule.late_interest
    grace_end = maturity_date + timedelta(days=li.grace_period_days)
    last_rate = schedule.schedule[-1].annual_rate
    growth = compound_growth(start, min(end, grace_end), last_rate, schedule.day_count)
    return growth * compound_growth(max(start, grace_end), end, li.annual_rate, schedule.day_count)


def _late_interest_values(schedule: FAScheduledInvestmentSchedule, dates: list[date_type], last_scheduled_value: Decimal, maturity_date: date_type) -> dict[date_type, Decimal]:
    """The late-interest value on each of ``dates``: the closed form of each date, in constant time (``compound_growth``),
    so the history, the current value and the settlement read the same digits for a day, whatever window is read."""
    return {day: _compute_late_interest_value(schedule, day, last_scheduled_value, maturity_date) for day in dates}


def _compute_late_interest_value(
    schedule: FAScheduledInvestmentSchedule,
    target_date: date_type,
    last_scheduled_value: Decimal,
    maturity_date: date_type,
) -> Decimal:
    """
    Compute value for a date after schedule ends (grace + late interest).

    The grace period runs at the last period's rate, then late interest at its own rate.
    Uses skip formula (D9) for efficiency:
    - SIMPLE: closed-form V = V_maturity + P * r * Δt, one segment per rate
    - COMPOUND: closed-form V = V_maturity · Π (1 + r · f) (``compound_growth``), one segment per rate (R13-SEC7-2: the
      day-by-day loop made the late history quadratic)

    Args:
        schedule: Full schedule config (provides day_count, late_interest)
        target_date: The date to compute
        last_scheduled_value: Value at maturity_date (from cache)
        maturity_date: Last day of the schedule
    """
    if not schedule.late_interest:
        return last_scheduled_value

    li = schedule.late_interest
    principal = schedule.initial_value.amount
    convention = schedule.day_count
    grace_end = maturity_date + timedelta(days=li.grace_period_days)
    last_rate = schedule.schedule[-1].annual_rate

    if li.interest_type == InterestType.COMPOUND:
        return last_scheduled_value * _late_compound_growth(schedule, maturity_date, target_date, maturity_date)

    # SIMPLE skip formula: the grace segment, then the late segment once the grace period is over.
    grace_fraction = calculate_day_count_fraction(
        start_date=maturity_date,
        end_date=min(target_date, grace_end),
        convention=convention,
    )
    value = last_scheduled_value + calculate_simple_interest(
        principal=principal,
        annual_rate=last_rate,
        time_fraction=grace_fraction,
    )
    if target_date > grace_end:
        late_fraction = calculate_day_count_fraction(
            start_date=grace_end,
            end_date=target_date,
            convention=convention,
        )
        value += calculate_simple_interest(
            principal=principal,
            annual_rate=li.annual_rate,
            time_fraction=late_fraction,
        )
    return value


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
    def supports_meaningful_volume(self) -> bool:
        """Parametrically generated synthetic series (fixed-income
        schedules) — there is no trading activity and no volume concept."""
        return False

    @property
    def provider_kind(self) -> FAProviderKind:
        """
        Parametric generation provider (#R3-4): the price series is produced
        **deterministically** from ``provider_params`` (initial_value, schedule,
        maturation_frequency, annual_rate, …). No external data source.

        A change in ``provider_params`` invalidates the existing series by
        definition, so ``bulk_assign_providers`` wipes and regenerates on every
        confirmed params update. The frontend uses this kind to show a
        "Regenerate Prices?" confirm dialog instead of a generic "Sync".
        """
        return FAProviderKind.PARAMETRIC_GENERATION

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
                # Exact cached maturation date: use the pre-reset peak directly.
                # ``_generate_schedule_values`` already applies manual events and
                # auto-coupon logic symmetrically here.
                value = cached[target_date]
            elif cached and target_date > max(cached.keys()):
                # Post-maturity: compute late interest one-shot
                maturity_date = max(cached.keys())
                value = _compute_late_interest_value(schedule, target_date, cached[maturity_date], maturity_date)
            elif cached and target_date < min(cached.keys()):
                # Before schedule: return initial_value
                value = schedule.initial_value.amount
            elif cached:
                # Between maturation dates — retest 2026-04-24: backward-fill
                # from the most recent maturation date was WRONG when
                # ``generate_interest=True``, because it returned the peak value
                # BEFORE the coupon reset. Real accrual has restarted from
                # principal and only intra-cycle days matter.
                # ``_compute_value_at`` walks the schedule up to ``target_date``
                # applying the same reset semantics as ``_generate_schedule_values``.
                computed = _compute_value_at(schedule, target_date)
                value = computed if computed is not None else schedule.initial_value.amount
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

    async def get_history_value(  # noqa: C901 — flat segment assembly (cached/late/settlement), guarded emission
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict,
        start_date: AssetHistoryStartDate,
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
            # "min" is the earliest available point: the schedule's first value or its first manual event, whichever comes
            # first (a refresh reads "min" once, on the first sync, so an earlier event would never be read again); with
            # neither, end_date (MF-SI1).
            effective_start = start_date
            if start_date == "min":
                effective_start = min([*cached.keys(), *(event.date for event in schedule.asset_events)], default=end_date)

            # Check for MATURITY_SETTLEMENT in cached events
            settlement_evt = next((e for e in cached_auto_events if e.type == "MATURITY_SETTLEMENT"), None)
            settlement_date = settlement_evt.date if settlement_evt else None

            prices = []

            # Emit cached values that fall within the requested range
            for d in sorted(cached.keys()):
                if effective_start <= d <= end_date:
                    prices.append(FAPricePoint(date=d, close=cached[d], currency=currency))

            # Handle post-maturity range with late interest maturation dates
            late_auto_events: list[FAAssetEventPoint] = []
            # Late interest is valued up to SCHEDULE_MAX_DATE at most (R13-SEC7-2, N73): no point is emitted after it.
            late_end = min(end_date, SCHEDULE_MAX_DATE)
            if maturity_date and late_end > maturity_date and schedule.late_interest:
                li = schedule.late_interest
                late_start = max(maturity_date + timedelta(days=1), effective_start)
                late_mat_dates = _compute_maturation_dates(
                    maturity_date + timedelta(days=1),
                    late_end,
                    li.maturation_frequency,
                )
                sorted_late_dates = sorted(late_mat_dates)
                last_late_date = sorted_late_dates[-1] if sorted_late_dates else None
                valued_dates = [d for d in sorted_late_dates if not (settlement_date and d > settlement_date)]
                emitted_dates = [d for d in valued_dates if late_start <= d <= late_end]
                late_values = _late_interest_values(schedule, sorted({*emitted_dates, *valued_dates[-1:]}), cached[maturity_date], maturity_date)

                for d in emitted_dates:
                    value = late_values[d]
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
                    # The last late price itself, so the settlement equals the chart's last point.
                    settle_value = late_values[last_late_date]
                    late_auto_events.append(
                        FAAssetEventPoint(
                            date=last_late_date,
                            type="MATURITY_SETTLEMENT",
                            value=Currency(code=currency, amount=settle_value),
                            notes="Late interest maturity settlement — asset closed",
                        )
                    )

            elif maturity_date and end_date > maturity_date and not schedule.late_interest:
                # No late interest config — emit maturity value as flat line at end_date (with late interest, a maturity
                # on the horizon itself emits nothing after it)
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
            if cached and effective_start < min(cached.keys()):
                prices.insert(0, FAPricePoint(date=effective_start, close=principal, currency=currency))

            # Sort by date (in case late interest dates interleave)
            prices.sort(key=lambda p: p.date)

            # Merge cached auto-events + late auto-events + manual events, filtered to range
            all_events = [e for e in cached_auto_events if effective_start <= e.date <= end_date]
            all_events += [e for e in late_auto_events if effective_start <= e.date <= end_date]
            all_events += [e for e in schedule.asset_events if effective_start <= e.date <= end_date]
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
