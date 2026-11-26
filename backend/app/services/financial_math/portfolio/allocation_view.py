"""The filtered allocation of the «Allocazione» tab (lane 80, issue #89): which part of the net worth the user looks at.

A view splits the net worth of a day (the NAV, the KPI «Patrimonio netto») in one dimension — sector, geography, asset
type or asset — after the user's filters. Every amount of the NAV lands in exactly one of three places, so that

    base + outside + excluded = NAV    (the identity of the view; the replay's own sums, never a remainder)

A profile's weights sum to exactly 1 (``BaseDistribution`` renormalizes them), so the identity is exact up to the
last digit of the Decimal context: a long converted amount times a weight is rounded part by part.

- **base** — the slices of the selection, the 100 % of the chart;
- **outside** — what the class filter leaves out: every asset whose class is off (unless its type is kept on its own,
  ``types``), and the cash when Liquidity is off;
- **excluded** — two kinds of rows:
  - the user's: an asset taken out whole (``exclude_asset_ids``), or an asset's part in the bucket ``Unknown`` or
    ``Other`` (``exclude_buckets``), only in the dimensions where that bucket exists (sector: both; geography and
    type: ``Unknown``; asset: none) — elsewhere the choice has no effect and is no error;
  - the unattributable ones, fixed, with a reason: the securities in transit between brokers (``in_transit``, always:
    the state holds no asset for them), and the cash in the geography (``no_country``) when Liquidity is on.

The filters apply in this order: the class (outside), then the excluded asset (its whole value), then the excluded
bucket (the asset's part in it). An asset counts once, in the first place that takes it.

The class of an asset is the type of what it holds, ``type_rules.asset_type_content`` (ETF_STOCK -> STOCK); the cash is
the class ``Liquidity`` — only a class, never an excludable bucket. Every asset is split by ``daily_state``'s
``allocation_parts``, the very split of the replay's ``by_type``/``by_sector``/``by_geography``: with no filter the
view's slices are the state's, the same keys and the same shares (``by_asset`` sums an asset over its brokers before
the split, so an amount can differ from the state's in the last digit of the Decimal context; on an asset held at one
broker it is the same Decimal).

The matrix (class × dimension) shows the whole portfolio, whatever the filters: a Liquidity row where the cash has a
bucket (sector), and its ``unattributed`` amounts (the cash in the geography, the securities in transit) bring
its sum to the NAV. The type and the asset dimensions have
no matrix: a type, or an asset, sits in one class only (D-15).

Shares only through ``weights.slice_percents`` (of the base: all None when the base is at or below zero, MF-C2) and
``weights.percent_of`` (of the NAV), rounded to 0.01. Amounts are never rounded.

Pure: the engine's daily states and the maps its replay read (``PortfolioCalculationResult.asset_types`` and
``.asset_classifications``); no database, no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date as date_type
from decimal import Decimal
from enum import StrEnum

from backend.app.services.assets.type_rules import asset_type_content
from backend.app.services.financial_math.portfolio.daily_state import GEOGRAPHY_VOICE, SECTOR_VOICE, AssetClassification, allocation_voice_parts
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder, percent_cents
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState
from backend.app.services.financial_math.weights import percent_of, slice_percents

#: The cash: a class of the filter, and its slice in the sector, type and asset dimensions (as in ``by_type``).
LIQUIDITY = "Liquidity"
#: The bucket of a value with no type, sector or country (the replay's own name).
UNKNOWN = "Unknown"
#: The sources' «other sectors» bucket.
OTHER = "Other"

_ZERO = Decimal("0")


class AllocationDimension(StrEnum):
    """What the view splits by."""

    SECTOR = "sector"
    GEOGRAPHY = "geography"
    TYPE = "type"
    ASSET = "asset"


#: The dimensions with a class × dimension matrix: elsewhere every bucket sits in one class, and a matrix would say nothing.
MATRIX_DIMENSIONS: frozenset[AllocationDimension] = frozenset({AllocationDimension.SECTOR, AllocationDimension.GEOGRAPHY})


class UnattributableReason(StrEnum):
    """Why an amount of the NAV has no bucket in the dimension."""

    IN_TRANSIT = "in_transit"
    NO_COUNTRY = "no_country"


#: The buckets a user may exclude, and where each one exists. The geography's «Other» is already «Unknown» (the
#: replay names the sources' «Other» country so), the asset type's «Unknown» is an asset with no type.
EXCLUDABLE_BUCKETS: frozenset[str] = frozenset({UNKNOWN, OTHER})
BUCKETS_BY_DIMENSION: Mapping[AllocationDimension, frozenset[str]] = {
    AllocationDimension.SECTOR: frozenset({UNKNOWN, OTHER}),
    AllocationDimension.GEOGRAPHY: frozenset({UNKNOWN}),
    AllocationDimension.TYPE: frozenset({UNKNOWN}),
    AllocationDimension.ASSET: frozenset(),
}


@dataclass(frozen=True)
class AllocationFilters:
    """The user's choices. ``classes`` None = every class; an empty set = none. ``types`` adds single asset types to the
    classes kept (a class kept in part): a whole class takes every type it holds, today's and the ones to come."""

    classes: frozenset[str] | None = None
    types: frozenset[str] = frozenset()
    exclude_buckets: frozenset[str] = frozenset()
    exclude_asset_ids: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        unknown = set(self.exclude_buckets) - EXCLUDABLE_BUCKETS
        if unknown:
            raise ValueError(f"not an excludable bucket: {sorted(unknown)} (only {sorted(EXCLUDABLE_BUCKETS)})")

    def keeps(self, asset_type: str, asset_class: str) -> bool:
        """Whether an asset of this type and class is in the selection."""
        return self.classes is None or asset_class in self.classes or asset_type in self.types


@dataclass(frozen=True)
class SliceAsset:
    """An asset's part in a slice, and its share of the slice."""

    asset_id: int
    amount: Decimal
    share_of_slice: Decimal | None


@dataclass(frozen=True)
class AllocationSlice:
    """A slice of the base. ``key`` is the bucket (a sector, an ISO3 country, an asset type, ``Liquidity``); in the
    asset dimension the asset id as text, with ``asset_id`` set (None on the Liquidity slice). ``assets`` holds the
    assets that make it up, largest first (empty on the Liquidity slice and in the asset dimension)."""

    key: str
    asset_id: int | None
    amount: Decimal
    share_of_selection: Decimal | None
    share_of_portfolio: Decimal | None
    assets: tuple[SliceAsset, ...] = ()


@dataclass(frozen=True)
class ClassAmount:
    asset_class: str
    amount: Decimal


@dataclass(frozen=True)
class TypeAmount:
    asset_type: str
    amount: Decimal


@dataclass(frozen=True)
class ScopeClass:
    """A class of the scope, its value on the view's day, and the asset types that make it up (the cash has none)."""

    asset_class: str
    amount: Decimal
    types: tuple[TypeAmount, ...] = ()


@dataclass(frozen=True)
class BucketAmount:
    key: str
    amount: Decimal


@dataclass(frozen=True)
class AssetAmount:
    asset_id: int
    amount: Decimal


@dataclass(frozen=True)
class UnattributableAmount:
    reason: UnattributableReason
    amount: Decimal


@dataclass(frozen=True)
class OutsideAmounts:
    """What the class filter leaves out, by class (of a class kept in part, the part left out)."""

    amount: Decimal
    by_class: tuple[ClassAmount, ...]


@dataclass(frozen=True)
class ExcludedAmounts:
    """The user's exclusions (by bucket, by asset) and the unattributable amounts."""

    amount: Decimal
    by_bucket: tuple[BucketAmount, ...]
    by_asset: tuple[AssetAmount, ...]
    unattributable: tuple[UnattributableAmount, ...]


@dataclass(frozen=True)
class ScopeAsset:
    """An asset of the scope, its class and its value on the view's day (zero when held only earlier in the window)."""

    asset_id: int
    asset_class: str
    amount: Decimal


@dataclass(frozen=True)
class MatrixCell:
    asset_class: str
    key: str
    amount: Decimal
    share_of_portfolio: Decimal | None


@dataclass(frozen=True)
class AllocationMatrix:
    """Class × dimension over the whole portfolio. ``rows`` and ``columns`` largest first; ``unattributed`` closes
    the sum to the NAV."""

    rows: tuple[str, ...]
    columns: tuple[str, ...]
    cells: tuple[MatrixCell, ...]
    unattributed: tuple[UnattributableAmount, ...]


@dataclass(frozen=True)
class AllocationView:
    """The view of one day (``as_of``, the last state), and optionally its history in steps.

    ``classes`` and ``assets`` are the scope's: every class and asset held on some day of the window, with the view's
    day's amount — what the filter panel lists. ``history`` items are ``{date, through, base, components}``, the
    components as ``build_allocation_history``'s (``{name, value, amount}``, plus ``id`` in the asset dimension).
    """

    as_of: date_type | None
    dimension: AllocationDimension
    portfolio_total: Decimal
    base: Decimal
    base_share_of_portfolio: Decimal | None
    slices: tuple[AllocationSlice, ...]
    outside: OutsideAmounts
    excluded: ExcludedAmounts
    classes: tuple[ScopeClass, ...]
    assets: tuple[ScopeAsset, ...]
    matrix: AllocationMatrix | None
    history: list[dict] = field(default_factory=list)


# =============================================================================
# The split of one state
# =============================================================================


@dataclass
class _Split:
    slices: dict[str | int, Decimal] = field(default_factory=dict)
    slice_assets: dict[str | int, dict[int, Decimal]] = field(default_factory=dict)
    outside: dict[str, Decimal] = field(default_factory=dict)
    excluded_buckets: dict[str, Decimal] = field(default_factory=dict)
    excluded_assets: dict[int, Decimal] = field(default_factory=dict)
    unattributable: dict[UnattributableReason, Decimal] = field(default_factory=dict)


def _add[K](bucket: dict[K, Decimal], key: K, amount: Decimal) -> None:
    bucket[key] = bucket.get(key, _ZERO) + amount


def _keyed_parts(
    dimension: AllocationDimension,
    asset_id: int,
    asset_type: str,
    classification: AssetClassification | None,
    day: date_type,
    value: Decimal,
) -> tuple[tuple[str | int, Decimal], ...]:
    """An asset's ``(key, amount)`` pairs in the dimension: the replay's split (``allocation_parts``: the type whole, a
    voice through ``allocation_voice_parts``), in its order. Only the asked voice is split: a history reads it on every
    change row."""
    if dimension is AllocationDimension.ASSET:
        return ((asset_id, value),)
    if dimension is AllocationDimension.TYPE:
        return ((asset_type, value),)
    return allocation_voice_parts(classification, SECTOR_VOICE if dimension is AllocationDimension.SECTOR else GEOGRAPHY_VOICE, day, value)


def _cash(state: DailyPortfolioState) -> Decimal:
    """The Liquidity of a day, as ``by_type``'s: the cash and the cash in transit."""
    return state.cash_value + state.in_transit_cash_value


def _place_cash(split: _Split, cash: Decimal, dimension: AllocationDimension, filters: AllocationFilters) -> None:
    """The cash: outside when Liquidity is off; with no country in the geography; else the Liquidity slice."""
    if filters.classes is not None and LIQUIDITY not in filters.classes:
        if cash:
            _add(split.outside, LIQUIDITY, cash)
    elif dimension is AllocationDimension.GEOGRAPHY:
        if cash:
            _add(split.unattributable, UnattributableReason.NO_COUNTRY, cash)
    else:
        # Kept at zero too, as by_type/by_sector and the asset view keep it: the same slices as today's allocation
        _add(split.slices, LIQUIDITY, cash)


def _split(
    state: DailyPortfolioState,
    day: date_type,
    dimension: AllocationDimension,
    filters: AllocationFilters,
    asset_types: Mapping[int, str],
    asset_classifications: Mapping[int, AssetClassification | None],
    *,
    with_members: bool = True,
) -> _Split:
    """Where every amount of the state's NAV goes under ``filters``: class, then excluded asset, then excluded bucket.
    ``with_members`` False skips each slice's assets: a history step shows the slices only."""
    split = _Split()
    excludable = filters.exclude_buckets & BUCKETS_BY_DIMENSION[dimension]
    for asset_id, value in state.by_asset.items():
        asset_type = asset_types.get(asset_id, UNKNOWN)
        asset_class = asset_type_content(asset_type)
        if not filters.keeps(asset_type, asset_class):
            _add(split.outside, asset_class, value)
            continue
        if asset_id in filters.exclude_asset_ids:
            _add(split.excluded_assets, asset_id, value)
            continue
        for key, amount in _keyed_parts(dimension, asset_id, asset_type, asset_classifications.get(asset_id), day, value):
            if key in excludable:
                _add(split.excluded_buckets, key, amount)
                continue
            _add(split.slices, key, amount)
            if with_members:
                _add(split.slice_assets.setdefault(key, {}), asset_id, amount)
    _place_cash(split, _cash(state), dimension, filters)
    if state.in_transit_asset_market_value:
        _add(split.unattributable, UnattributableReason.IN_TRANSIT, state.in_transit_asset_market_value)
    return split


def _largest_first[K](amounts: Mapping[K, Decimal]) -> list[tuple[K, Decimal]]:
    """Largest amount first; a tie keeps the mapping's order (as the allocation views sort)."""
    return sorted(amounts.items(), key=lambda item: -item[1])


def _slice_key(dimension: AllocationDimension, key: str | int) -> tuple[str, int | None]:
    if dimension is AllocationDimension.ASSET and isinstance(key, int):
        return str(key), key
    return str(key), None


def _slices(split: _Split, dimension: AllocationDimension, nav: Decimal) -> tuple[AllocationSlice, ...]:
    percents = slice_percents(split.slices)
    slices = []
    for key, amount in _largest_first(split.slices):
        text, asset_id = _slice_key(dimension, key)
        members = split.slice_assets.get(key, {}) if dimension is not AllocationDimension.ASSET else {}
        member_percents = slice_percents(members)
        assets = tuple(SliceAsset(asset_id=member, amount=part, share_of_slice=percent_cents(member_percents[member])) for member, part in _largest_first(members))
        slices.append(
            AllocationSlice(
                key=text,
                asset_id=asset_id,
                amount=amount,
                share_of_selection=percent_cents(percents[key]),
                share_of_portfolio=percent_cents(percent_of(amount, nav)),
                assets=assets,
            )
        )
    return tuple(slices)


def _unattributable(amounts: Mapping[UnattributableReason, Decimal]) -> tuple[UnattributableAmount, ...]:
    return tuple(UnattributableAmount(reason=reason, amount=amounts[reason]) for reason in UnattributableReason if reason in amounts)


# =============================================================================
# The matrix, the scope, the history
# =============================================================================


def _matrix(
    state: DailyPortfolioState,
    day: date_type,
    dimension: AllocationDimension,
    asset_types: Mapping[int, str],
    asset_classifications: Mapping[int, AssetClassification | None],
) -> AllocationMatrix | None:
    """Class × dimension of the whole portfolio (no filter), with what has no column; None outside :data:`MATRIX_DIMENSIONS`."""
    if dimension not in MATRIX_DIMENSIONS:
        return None
    cells: dict[tuple[str, str], Decimal] = {}
    for asset_id, value in state.by_asset.items():
        asset_type = asset_types.get(asset_id, UNKNOWN)
        asset_class = asset_type_content(asset_type)
        for key, amount in _keyed_parts(dimension, asset_id, asset_type, asset_classifications.get(asset_id), day, value):
            _add(cells, (asset_class, str(key)), amount)
    unattributed: dict[UnattributableReason, Decimal] = {}
    cash = _cash(state)
    if cash:
        if dimension is AllocationDimension.GEOGRAPHY:
            unattributed[UnattributableReason.NO_COUNTRY] = cash
        else:
            _add(cells, (LIQUIDITY, LIQUIDITY), cash)
    if state.in_transit_asset_market_value:
        unattributed[UnattributableReason.IN_TRANSIT] = state.in_transit_asset_market_value
    row_totals: dict[str, Decimal] = {}
    column_totals: dict[str, Decimal] = {}
    for (asset_class, key), amount in cells.items():
        _add(row_totals, asset_class, amount)
        _add(column_totals, key, amount)
    rows = tuple(name for name, _amount in _largest_first(row_totals))
    columns = tuple(name for name, _amount in _largest_first(column_totals))
    row_rank = {name: rank for rank, name in enumerate(rows)}
    column_rank = {name: rank for rank, name in enumerate(columns)}
    ordered = sorted(cells.items(), key=lambda item: (row_rank[item[0][0]], column_rank[item[0][1]]))
    nav = state.nav_value
    return AllocationMatrix(
        rows=rows,
        columns=columns,
        cells=tuple(MatrixCell(asset_class=asset_class, key=key, amount=amount, share_of_portfolio=percent_cents(percent_of(amount, nav))) for (asset_class, key), amount in ordered),
        unattributed=_unattributable(unattributed),
    )


def _scope(
    builder: DerivedViewsBuilder,
    state: DailyPortfolioState,
    date_from: date_type | None,
    asset_types: Mapping[int, str],
) -> tuple[tuple[ScopeClass, ...], tuple[ScopeAsset, ...]]:
    """The classes (with their types) and assets held on some day of the window, with the view's day's amounts, largest first."""
    asset_ids = builder.allocation_asset_ids(date_from) | set(state.by_asset)
    assets = sorted(
        (ScopeAsset(asset_id=asset_id, asset_class=asset_type_content(asset_types.get(asset_id, UNKNOWN)), amount=state.by_asset.get(asset_id, _ZERO)) for asset_id in asset_ids),
        key=lambda asset: (-asset.amount, asset.asset_id),
    )
    class_amounts: dict[str, Decimal] = {}
    type_amounts: dict[str, dict[str, Decimal]] = {}
    for asset in assets:
        _add(class_amounts, asset.asset_class, asset.amount)
        _add(type_amounts.setdefault(asset.asset_class, {}), asset_types.get(asset.asset_id, UNKNOWN), asset.amount)
    cash = _cash(state)
    if cash or builder.allocation_has_cash(date_from):
        _add(class_amounts, LIQUIDITY, cash)
    classes = sorted(
        (
            ScopeClass(
                asset_class=name,
                amount=amount,
                types=tuple(sorted((TypeAmount(asset_type=asset_type, amount=part) for asset_type, part in type_amounts.get(name, {}).items()), key=lambda item: (-item.amount, item.asset_type))),
            )
            for name, amount in class_amounts.items()
        ),
        key=lambda item: (-item.amount, item.asset_class),
    )
    return tuple(classes), tuple(assets)


def _history(
    builder: DerivedViewsBuilder,
    dimension: AllocationDimension,
    filters: AllocationFilters,
    asset_types: Mapping[int, str],
    asset_classifications: Mapping[int, AssetClassification | None],
    names: Mapping[int, str],
    date_from: date_type | None,
) -> list[dict]:
    """The selection's slices in steps from ``date_from``: ``{date, through, base, components}``."""

    def components(state: DailyPortfolioState) -> list[dict]:
        # A change row's state is its segment's, dated at the segment's start. The weights cannot change inside a
        # segment (a profile step starts a segment: DailyStateBuilder's dirty days), so the start's are the row's
        split = _split(state, state.date, dimension, filters, asset_types, asset_classifications, with_members=False)
        percents = slice_percents(split.slices)
        rows = []
        for key, amount in _largest_first(split.slices):
            if dimension is AllocationDimension.ASSET:
                asset_id = key if isinstance(key, int) else None
                name = LIQUIDITY if asset_id is None else names.get(asset_id, f"Asset {asset_id}")
                rows.append({"name": name, "id": asset_id, "value": percent_cents(percents[key]), "amount": amount})
            else:
                rows.append({"name": key, "value": percent_cents(percents[key]), "amount": amount})
        return rows

    steps = builder.component_steps(components, date_from)
    for step in steps:
        step["base"] = sum((component["amount"] for component in step["components"]), _ZERO)
    return steps


# =============================================================================
# Entry point
# =============================================================================


def build_allocation_view(
    daily_states: Sequence[DailyPortfolioState],
    *,
    asset_types: Mapping[int, str],
    asset_classifications: Mapping[int, AssetClassification | None],
    dimension: AllocationDimension,
    filters: AllocationFilters | None = None,
    date_from: date_type | None = None,
    include_history: bool = False,
    names: Mapping[int, str] | None = None,
    target_currency: str = "EUR",
) -> AllocationView:
    """The view of the last state (the day «Ora»), its scope from ``date_from``, and its history when asked.

    ``daily_states`` are the engine's (``PortfolioCalculationResult.daily_states``), ``asset_types`` and
    ``asset_classifications`` the maps its replay read; ``names`` name the asset dimension's history components (the
    asset views' ``Asset {id}`` fallback otherwise). With no state the view is empty.
    """
    filters = filters or AllocationFilters()
    dimension = AllocationDimension(dimension)
    builder = DerivedViewsBuilder(daily_states, target_currency)
    if not daily_states:
        return AllocationView(
            as_of=None,
            dimension=dimension,
            portfolio_total=_ZERO,
            base=_ZERO,
            base_share_of_portfolio=None,
            slices=(),
            outside=OutsideAmounts(amount=_ZERO, by_class=()),
            excluded=ExcludedAmounts(amount=_ZERO, by_bucket=(), by_asset=(), unattributable=()),
            classes=(),
            assets=(),
            matrix=None if dimension not in MATRIX_DIMENSIONS else AllocationMatrix(rows=(), columns=(), cells=(), unattributed=()),
        )
    state = daily_states[-1]
    day = state.date
    split = _split(state, day, dimension, filters, asset_types, asset_classifications)
    nav = state.nav_value
    base = sum(split.slices.values(), _ZERO)
    outside = OutsideAmounts(
        amount=sum(split.outside.values(), _ZERO),
        by_class=tuple(ClassAmount(asset_class=name, amount=amount) for name, amount in _largest_first(split.outside)),
    )
    unattributable = _unattributable(split.unattributable)
    excluded = ExcludedAmounts(
        amount=sum(split.excluded_buckets.values(), _ZERO) + sum(split.excluded_assets.values(), _ZERO) + sum(split.unattributable.values(), _ZERO),
        by_bucket=tuple(BucketAmount(key=key, amount=amount) for key, amount in _largest_first(split.excluded_buckets)),
        by_asset=tuple(AssetAmount(asset_id=asset_id, amount=amount) for asset_id, amount in _largest_first(split.excluded_assets)),
        unattributable=unattributable,
    )
    classes, assets = _scope(builder, state, date_from, asset_types)
    return AllocationView(
        as_of=day,
        dimension=dimension,
        portfolio_total=nav,
        base=base,
        base_share_of_portfolio=percent_cents(percent_of(base, nav)),
        slices=_slices(split, dimension, nav),
        outside=outside,
        excluded=excluded,
        classes=classes,
        assets=assets,
        matrix=_matrix(state, day, dimension, asset_types, asset_classifications),
        history=_history(builder, dimension, filters, asset_types, asset_classifications, names or {}, date_from) if include_history else [],
    )
