"""FIFO lot engine data: input transactions, events, lots, fragments, closures, economic allocations, and the engine result."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Callable, Literal, Protocol

Direction = Literal["LONG", "SHORT"]
CustodyType = Literal["BROKER", "IN_TRANSIT"]
ReferencePriceSource = Literal["exact", "fallback", "unavailable"]
IssueCode = Literal[
    "REFERENCE_PRICE_FALLBACK",
    "REFERENCE_PRICE_UNAVAILABLE",
    "SHORT_TRANSFER_NOT_SUPPORTED",
    "SHORT_ADJUSTMENT_NOT_SUPPORTED",
    "FIFO_SOURCE_QUANTITY_MISSING",
    "TRANSFER_PAIR_MISSING",
    "ASSET_INCOME_NO_ELIGIBLE_LOTS",
    "ASSET_COST_NO_ELIGIBLE_LOTS",
]
# Issue codes that indicate a non-isolable quantitative replay failure (incoherent
# quantities, invalid fragment topology, or unreconstructable transfers). Their
# presence makes the whole FIFO reconstruction unreliable -> analysis_status FAILED.
# Economic issues (orphan income/cost, reference-price, FX) stay DEGRADED: they are
# isolable to a single pool/lot and never invalidate the quantitative replay.
_QUANTITATIVE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "SHORT_TRANSFER_NOT_SUPPORTED",
        "SHORT_ADJUSTMENT_NOT_SUPPORTED",
        "FIFO_SOURCE_QUANTITY_MISSING",
        "TRANSFER_PAIR_MISSING",
    }
)


def fails_the_replay(code: str) -> bool:
    """Whether an issue of this code makes the whole replay unreliable: the analysis is FAILED (J-12 withholds its lots)."""
    return code in _QUANTITATIVE_FAILURE_CODES


EventKind = Literal[
    "BUY",
    "SELL",
    "ADJUSTMENT_IN",
    "ADJUSTMENT_OUT",
    "SPLIT",
    "TRANSFER_DEPART",
    "TRANSFER_ARRIVE",
]

# --- Economic stage contract (FEE/TAX/income allocation, target-currency aware) ---
# Following the module convention (Direction/CustodyType/EventKind), economic
# taxonomies are Literal aliases rather than Enum classes.
EconomicType = Literal["FEE", "TAX", "DIVIDEND", "INTEREST"]
AllocationContext = Literal["OPENING", "CLOSURE", "INCOME", "HOLDING"]
AllocationRule = Literal[
    "ASSET_INCOME_HOLDINGS",
    "SAME_DAY_MIXED_TRADES",
    "SAME_DAY_TRADES",
    "SAME_DAY_INCOME",
    "PREVIOUS_DAY_TRADES",
    "PREVIOUS_DAY_INCOME",
    "OPEN_LOTS_FALLBACK",
]


class TransactionLike(Protocol):
    id: int | None
    broker_id: int
    asset_id: int | None
    date: date
    type: object
    quantity: Decimal
    amount: Decimal | None
    currency: str | None
    cost_basis_override: Decimal | None
    cost_basis_currency: str | None
    related_transaction_id: int | None


@dataclass(frozen=True, slots=True)
class FifoInputTransaction:
    id: int
    broker_id: int
    asset_id: int
    date: date
    type: str
    quantity: Decimal
    amount: Decimal = Decimal("0")
    currency: str | None = None
    cost_basis_override: Decimal | None = None
    cost_basis_currency: str | None = None
    related_transaction_id: int | None = None
    target_amount: Decimal | None = None
    target_currency: str | None = None
    # An ADJUSTMENT-out that hands each fragment over at its own FIFO cost (realized 0): a transfer leg leaving the scope
    # on a day without any price (``financial_math/lots/scope_boundary.py``, J-10).
    hands_over_at_own_cost: bool = False

    @classmethod
    def from_transaction(cls, tx: TransactionLike | FifoInputTransaction) -> FifoInputTransaction:
        if isinstance(tx, FifoInputTransaction):
            return tx
        tx_type = getattr(tx.type, "value", tx.type)
        # N78-1 (the developer's decision, 21/10/2026): an ADJUSTMENT-out has no value, whatever cost basis the row holds.
        # Its units leave at 0. The scope-boundary readings of J-10 build their own copies and keep their value.
        outgoing_adjustment = str(tx_type) == "ADJUSTMENT" and tx.quantity is not None and tx.quantity < 0
        return cls(
            id=_require_id(tx.id),
            broker_id=tx.broker_id,
            asset_id=_require_id(tx.asset_id),
            date=tx.date,
            type=str(tx_type),
            quantity=tx.quantity,
            amount=tx.amount or Decimal("0"),
            currency=tx.currency,
            cost_basis_override=None if outgoing_adjustment else tx.cost_basis_override,
            cost_basis_currency=None if outgoing_adjustment else tx.cost_basis_currency,
            related_transaction_id=tx.related_transaction_id,
        )


@dataclass(frozen=True, slots=True)
class ReferencePriceResolution:
    price: Decimal | None
    source: ReferencePriceSource


ReferencePriceLookup = Callable[[int, date], ReferencePriceResolution | None]


@dataclass(frozen=True, slots=True)
class FifoEvent:
    kind: EventKind
    date: date
    transaction_id: int
    broker_id: int | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    ratio: Decimal | None = None
    asset_event_id: int | None = None
    pair_id: int | None = None
    source_broker_id: int | None = None
    destination_broker_id: int | None = None
    transit_start: date | None = None
    transit_end: date | None = None
    raw_transaction_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class SplitQuantitySnapshot:
    """Signed quantities visible to one split row before its global event."""

    scoped_quantity: Decimal
    broker_custody_quantity: Decimal


@dataclass(slots=True)
class FifoDataQualityIssue:
    code: IssueCode
    transaction_id: int | None
    lot_id: int | None = None
    broker_id: int | None = None
    related_transaction_id: int | None = None
    message: str = ""
    params: dict[str, str | int | Decimal | None] = field(default_factory=dict)


@dataclass(slots=True)
class FragmentInterval:
    fragment_id: str
    lot_id: int
    direction: Direction
    custody_type: CustodyType
    quantity: Decimal
    unit_price: Decimal
    start_date: date
    broker_id: int | None = None
    end_date: date | None = None
    source_broker_id: int | None = None
    destination_broker_id: int | None = None


@dataclass(frozen=True, slots=True)
class LotClosure:
    """A piece of a lot closed by one transaction, in native amounts.

    ``open_unit_price`` is in the lot's currency; ``close_unit_price`` and ``proceeds`` are in
    ``close_currency``, the currency of the closing price (None counts as the report currency, as the
    lots analysis reads it). ``realized_pnl`` is native too, so it is None when the two currencies
    differ: the engine has no rates. The report-currency figures come from
    ``financial_math.lots.conversions.convert_closure``, each leg at its own date (decision 26).
    """

    lot_id: int
    transaction_id: int
    quantity: Decimal
    close_date: date
    close_reason: Literal["SELL", "BUY", "ADJUSTMENT_OUT"]
    fragment_id: str
    open_unit_price: Decimal
    close_unit_price: Decimal
    realized_pnl: Decimal | None
    proceeds: Decimal
    close_currency: str | None = None


@dataclass(slots=True)
class FifoLot:
    lot_id: int
    asset_id: int
    direction: Direction
    opening_transaction_id: int
    opening_broker_id: int
    opening_date: date
    original_quantity: Decimal
    opening_unit_price: Decimal
    original_cost: Decimal
    currency: str | None
    open_quantity: Decimal
    realized_quantity: Decimal = Decimal("0")
    # Native sums in the lot's currency: None once a closure is in another currency (see LotClosure). A short
    # lot's cumulative proceeds are its opening proceeds, which its closures never change.
    realized_pnl: Decimal | None = Decimal("0")
    cumulative_proceeds: Decimal | None = Decimal("0")
    reference_unit_price: Decimal | None = None
    reference_price_source: ReferencePriceSource | None = None


@dataclass(frozen=True, slots=True)
class EconomicEvent:
    """Non-quantitative economic input (FEE/TAX/DIVIDEND/INTEREST) fed to the engine.

    Carries both the native amount (as stored on the source transaction) and the
    target-currency amount pre-resolved by the service (Option B: engine is
    target-value aware, FX-mechanism agnostic). The engine never performs FX I/O.
    """

    transaction_id: int
    broker_id: int
    asset_id: int
    date: date
    economic_type: EconomicType
    native_amount: Decimal
    native_currency: str | None
    target_amount: Decimal
    target_currency: str


@dataclass(frozen=True, slots=True)
class EconomicLotAllocation:
    """Audit leaf: share of a target operation assigned to a single lot."""

    lot_id: int
    weight: Decimal
    native_amount: Decimal
    target_amount: Decimal


@dataclass(frozen=True, slots=True)
class TargetOperationAllocation:
    """Audit mid-level: one target operation (opening/closure/income/holding).

    The allocation context lives on the target operation, not the group, so the
    same lot can appear under multiple contexts (e.g. OPENING and CLOSURE) with
    its breakdown preserved.
    """

    context: AllocationContext
    operation_transaction_id: int | None
    weight: Decimal
    lot_allocations: tuple[EconomicLotAllocation, ...] = ()


@dataclass(frozen=True, slots=True)
class EconomicAllocationGroup:
    """Audit top-level: a pooled economic group and its resolved allocations."""

    economic_type: EconomicType
    asset_id: int
    broker_id: int
    date: date
    native_currency: str | None
    target_currency: str
    rule: AllocationRule
    source_transaction_ids: tuple[int, ...]
    native_pool_total: Decimal
    target_pool_total: Decimal
    operation_allocations: tuple[TargetOperationAllocation, ...] = ()
    native_orphan: Decimal = Decimal("0")
    target_orphan: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class LotEconomicAccumulators:
    """Per-lot economic accumulators (gross + allocated costs), target currency.

    Kept separate from the quantitative lot structures: economic values never
    mutate quantities, fragments or closures.
    """

    lot_id: int
    original_cost: Decimal = Decimal("0")
    sale_proceeds: Decimal = Decimal("0")
    gross_income: Decimal = Decimal("0")
    allocated_fees: Decimal = Decimal("0")
    allocated_taxes: Decimal = Decimal("0")
    open_value: Decimal = Decimal("0")


@dataclass(slots=True)
class FifoEngineResult:
    asset_id: int
    classified_events: list[FifoEvent]
    lots: list[FifoLot]
    fragment_intervals: list[FragmentInterval]
    closures: list[LotClosure]
    issues: list[FifoDataQualityIssue]
    split_quantities_by_transaction_id: dict[int, SplitQuantitySnapshot] = field(default_factory=dict)
    economic_allocation_groups: list[EconomicAllocationGroup] = field(default_factory=list)
    economic_accumulators_by_lot: dict[int, LotEconomicAccumulators] = field(default_factory=dict)
    asset_orphan_income: Decimal = Decimal("0")
    asset_orphan_fees: Decimal = Decimal("0")
    asset_orphan_taxes: Decimal = Decimal("0")

    @property
    def analysis_status(self) -> Literal["COMPLETE", "DEGRADED", "FAILED"]:
        if not self.issues:
            return "COMPLETE"
        if any(issue.code in _QUANTITATIVE_FAILURE_CODES for issue in self.issues):
            return "FAILED"
        return "DEGRADED"

    def get_lot(self, lot_id: int) -> FifoLot:
        for lot in self.lots:
            if lot.lot_id == lot_id:
                return lot
        raise KeyError(f"Lot {lot_id} not found")

    def get_lot_states(self, lot_id: int) -> set[str]:
        lot = self.get_lot(lot_id)
        active = [fragment for fragment in self.fragment_intervals if fragment.lot_id == lot_id and fragment.end_date is None]
        states = {lot.direction}
        if lot.open_quantity == Decimal("0"):
            states.add("CLOSED")
        elif lot.realized_quantity > Decimal("0"):
            states.add("PARTIALLY_CLOSED")
        else:
            states.add("OPEN")
        if any(fragment.custody_type == "IN_TRANSIT" for fragment in active):
            states.add("IN_TRANSIT")
        custody_locations = {(fragment.custody_type, fragment.broker_id) for fragment in active}
        if len(custody_locations) > 1:
            states.add("DISTRIBUTED")
        if any(issue.lot_id == lot_id for issue in self.issues):
            states.add("DEGRADED")
        return states

    def active_fragments(self, *, lot_id: int | None = None, broker_id: int | None = None, custody_type: CustodyType | None = None) -> list[FragmentInterval]:
        active = [fragment for fragment in self.fragment_intervals if fragment.end_date is None]
        if lot_id is not None:
            active = [fragment for fragment in active if fragment.lot_id == lot_id]
        if broker_id is not None:
            active = [fragment for fragment in active if fragment.broker_id == broker_id]
        if custody_type is not None:
            active = [fragment for fragment in active if fragment.custody_type == custody_type]
        return sorted(active, key=lambda fragment: (fragment.start_date, fragment.fragment_id))


def _require_id(value: int | None) -> int:
    if value is None:
        raise ValueError("Expected non-null identifier")
    return value


def _require_decimal(value: Decimal | None) -> Decimal:
    if value is None:
        raise ValueError("Expected Decimal value")
    return value


def _require_date(value: date | None) -> date:
    if value is None:
        raise ValueError("Expected date value")
    return value
