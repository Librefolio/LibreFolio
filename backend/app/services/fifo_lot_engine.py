from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Callable, Literal, Protocol, Sequence

# Tolerance for the split cost invariant (q*p0 = const). Division by a ratio that
# doesn't divide evenly (e.g. a 3:1 split) produces a non-terminating decimal that
# Decimal's default 28-digit context truncates, so unit_price*ratio recombined with
# quantity/ratio can differ from the original cost by a sub-cent amount (~1E-25 for
# typical magnitudes) purely from truncation — not a real bug. A strict `!=` check
# would crash the engine on ordinary, common split ratios. Genuine logic errors
# produce discrepancies many orders of magnitude larger than this tolerance.
_COST_INVARIANT_TOLERANCE = Decimal("0.01")

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

    @classmethod
    def from_transaction(cls, tx: TransactionLike) -> FifoInputTransaction:
        tx_type = getattr(tx.type, "value", tx.type)
        return cls(
            id=_require_id(tx.id),
            broker_id=tx.broker_id,
            asset_id=_require_id(tx.asset_id),
            date=tx.date,
            type=str(tx_type),
            quantity=tx.quantity,
            amount=tx.amount or Decimal("0"),
            currency=tx.currency,
            cost_basis_override=tx.cost_basis_override,
            cost_basis_currency=tx.cost_basis_currency,
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
    pair_id: int | None = None
    source_broker_id: int | None = None
    destination_broker_id: int | None = None
    transit_start: date | None = None
    transit_end: date | None = None
    raw_transaction_ids: tuple[int, ...] = ()


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
    lot_id: int
    transaction_id: int
    quantity: Decimal
    close_date: date
    close_reason: Literal["SELL", "BUY", "ADJUSTMENT_OUT"]
    fragment_id: str
    open_unit_price: Decimal
    close_unit_price: Decimal
    realized_pnl: Decimal
    proceeds: Decimal


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
    realized_pnl: Decimal = Decimal("0")
    cumulative_proceeds: Decimal = Decimal("0")
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

    def signed_quantity_by_broker(self, broker_id: int) -> Decimal:
        total = Decimal("0")
        for fragment in self.active_fragments(broker_id=broker_id, custody_type="BROKER"):
            sign = Decimal("1") if fragment.direction == "LONG" else Decimal("-1")
            total += sign * fragment.quantity
        return total


@dataclass(slots=True)
class _PendingTransferPiece:
    pair_id: int
    lot_id: int
    destination_broker_id: int
    arrival_date: date
    quantity: Decimal
    transit_fragment_id: str | None
    unit_price: Decimal


@dataclass(slots=True)
class _EconomicStageResult:
    """Internal carrier for the post-replay economic allocation outputs."""

    groups: list[EconomicAllocationGroup] = field(default_factory=list)
    accumulators: dict[int, LotEconomicAccumulators] = field(default_factory=dict)
    orphan_income: Decimal = Decimal("0")
    orphan_fees: Decimal = Decimal("0")
    orphan_taxes: Decimal = Decimal("0")


class FifoLotEngine:
    """Pure event-sourced FIFO engine for one asset across many brokers.

    Split scope judgement call: only fragments touched by broker with explicit split-linked
    transaction are transformed. Broker-custodied fragments match on `broker_id`; in-transit
    fragments are included only when their source or destination broker matches split broker.

    Transfer judgement call: source/destination direction follows quantity sign, but transit
    window follows chronological `[min(date_a, date_b), max(date_a, date_b))`. To preserve
    half-open intervals for same-day split handling, transfer depart/arrive state transitions
    run at start of day before split events and ordinary transactions.
    """

    def __init__(
        self,
        transactions: Sequence[TransactionLike | FifoInputTransaction],
        broker_shorting: dict[int, bool],
        *,
        split_ratios_by_tx_id: dict[int, Decimal] | None = None,
        reference_price_lookup: ReferencePriceLookup | None = None,
        economic_events: Sequence[EconomicEvent] = (),
        target_currency: str = "",
    ) -> None:
        normalized = [tx if isinstance(tx, FifoInputTransaction) else FifoInputTransaction.from_transaction(tx) for tx in transactions]
        if not normalized:
            raise ValueError("FifoLotEngine requires at least one transaction")
        asset_ids = {tx.asset_id for tx in normalized}
        if len(asset_ids) != 1:
            raise ValueError(f"FifoLotEngine requires single asset input, got {sorted(asset_ids)}")
        self.asset_id = normalized[0].asset_id
        self.transactions = normalized
        self.broker_shorting = broker_shorting
        self.split_ratios_by_tx_id = split_ratios_by_tx_id or {}
        self.reference_price_lookup = reference_price_lookup
        self.economic_events = tuple(economic_events)
        self.target_currency = target_currency
        self._tx_by_id = {tx.id: tx for tx in normalized}
        self._issues: list[FifoDataQualityIssue] = []
        self._lots: dict[int, FifoLot] = {}
        self._intervals: list[FragmentInterval] = []
        self._active_fragments: dict[str, FragmentInterval] = {}
        self._closures: list[LotClosure] = []
        self._pending_transfers: dict[int, list[_PendingTransferPiece]] = {}
        self._transfer_arrival_dates: dict[int, date] = {}
        self._classified_events_cache: list[FifoEvent] | None = None

    def run(self) -> FifoEngineResult:
        events = self.classify_events()
        for event in events:
            if event.kind == "BUY":
                self._apply_buy(event)
            elif event.kind == "SELL":
                self._apply_sell(event)
            elif event.kind == "ADJUSTMENT_IN":
                self._apply_adjustment_in(event)
            elif event.kind == "ADJUSTMENT_OUT":
                self._apply_adjustment_out(event)
            elif event.kind == "TRANSFER_DEPART":
                self._apply_transfer_depart(event)
            elif event.kind == "TRANSFER_ARRIVE":
                self._apply_transfer_arrive(event)
            elif event.kind == "SPLIT":
                self._apply_split(event)
        economic = self._allocate_economics()
        return FifoEngineResult(
            asset_id=self.asset_id,
            classified_events=events,
            lots=sorted(self._lots.values(), key=lambda lot: (lot.opening_date, lot.lot_id)),
            fragment_intervals=sorted(self._intervals, key=lambda fragment: (fragment.start_date, fragment.fragment_id, fragment.quantity)),
            closures=sorted(self._closures, key=lambda closure: (closure.close_date, closure.transaction_id, closure.lot_id)),
            issues=self._issues,
            economic_allocation_groups=economic.groups,
            economic_accumulators_by_lot=economic.accumulators,
            asset_orphan_income=economic.orphan_income,
            asset_orphan_fees=economic.orphan_fees,
            asset_orphan_taxes=economic.orphan_taxes,
        )

    def classify_events(self) -> list[FifoEvent]:
        if self._classified_events_cache is not None:
            return self._classified_events_cache
        events: list[FifoEvent] = []
        processed_transfer_pairs: set[int] = set()
        for tx in self.transactions:
            if tx.id in self.split_ratios_by_tx_id:
                events.append(FifoEvent(kind="SPLIT", date=tx.date, transaction_id=tx.id, broker_id=tx.broker_id, ratio=self.split_ratios_by_tx_id[tx.id], raw_transaction_ids=(tx.id,)))
                continue
            if tx.type == "TRANSFER":
                pair_id = tx.id if tx.related_transaction_id is None else min(tx.id, tx.related_transaction_id)
                if pair_id in processed_transfer_pairs:
                    continue
                pair = self._resolve_transfer_pair(tx)
                if pair is None:
                    processed_transfer_pairs.add(pair_id)
                    continue
                out_leg, in_leg = pair
                start = min(out_leg.date, in_leg.date)
                end = max(out_leg.date, in_leg.date)
                processed_transfer_pairs.add(min(out_leg.id, in_leg.id))
                depart_transaction_id = min(out_leg.id, in_leg.id) if start == end else (out_leg.id if out_leg.date == start else in_leg.id)
                arrive_transaction_id = max(out_leg.id, in_leg.id) if start == end else (out_leg.id if out_leg.date == end else in_leg.id)
                transfer_pair_id = min(out_leg.id, in_leg.id)
                quantity = abs(out_leg.quantity)
                self._transfer_arrival_dates[transfer_pair_id] = end
                events.append(
                    FifoEvent(
                        kind="TRANSFER_DEPART",
                        date=start,
                        transaction_id=depart_transaction_id,
                        pair_id=transfer_pair_id,
                        source_broker_id=out_leg.broker_id,
                        destination_broker_id=in_leg.broker_id,
                        quantity=quantity,
                        transit_start=start,
                        transit_end=end,
                        raw_transaction_ids=(out_leg.id, in_leg.id),
                    )
                )
                events.append(
                    FifoEvent(
                        kind="TRANSFER_ARRIVE",
                        date=end,
                        transaction_id=arrive_transaction_id,
                        pair_id=transfer_pair_id,
                        source_broker_id=out_leg.broker_id,
                        destination_broker_id=in_leg.broker_id,
                        quantity=quantity,
                        transit_start=start,
                        transit_end=end,
                        raw_transaction_ids=(out_leg.id, in_leg.id),
                    )
                )
                continue
            if tx.type == "BUY":
                events.append(FifoEvent(kind="BUY", date=tx.date, transaction_id=tx.id, broker_id=tx.broker_id, quantity=abs(tx.quantity), unit_price=_unit_price(tx.amount, tx.quantity), raw_transaction_ids=(tx.id,)))
            elif tx.type == "SELL":
                events.append(FifoEvent(kind="SELL", date=tx.date, transaction_id=tx.id, broker_id=tx.broker_id, quantity=abs(tx.quantity), unit_price=_unit_price(tx.amount, tx.quantity), raw_transaction_ids=(tx.id,)))
            elif tx.type == "ADJUSTMENT" and tx.quantity > Decimal("0"):
                events.append(FifoEvent(kind="ADJUSTMENT_IN", date=tx.date, transaction_id=tx.id, broker_id=tx.broker_id, quantity=tx.quantity, unit_price=Decimal("0"), raw_transaction_ids=(tx.id,)))
            elif tx.type == "ADJUSTMENT" and tx.quantity < Decimal("0"):
                events.append(FifoEvent(kind="ADJUSTMENT_OUT", date=tx.date, transaction_id=tx.id, broker_id=tx.broker_id, quantity=abs(tx.quantity), unit_price=Decimal("0"), raw_transaction_ids=(tx.id,)))
        self._classified_events_cache = sorted(events, key=self._event_sort_key)
        return self._classified_events_cache

    def _resolve_transfer_pair(self, tx: FifoInputTransaction) -> tuple[FifoInputTransaction, FifoInputTransaction] | None:
        if tx.related_transaction_id is None:
            self._issue(
                code="TRANSFER_PAIR_MISSING",
                transaction_id=tx.id,
                broker_id=tx.broker_id,
                message="Transfer transaction is missing related_transaction_id.",
            )
            return None
        pair = self._tx_by_id.get(tx.related_transaction_id)
        if pair is None or pair.type != "TRANSFER" or pair.related_transaction_id != tx.id or pair.asset_id != tx.asset_id:
            self._issue(
                code="TRANSFER_PAIR_MISSING",
                transaction_id=tx.id,
                broker_id=tx.broker_id,
                related_transaction_id=tx.related_transaction_id,
                message="Transfer pair missing or not bidirectional.",
            )
            return None
        txs = (tx, pair)
        negative = [candidate for candidate in txs if candidate.quantity < Decimal("0")]
        positive = [candidate for candidate in txs if candidate.quantity > Decimal("0")]
        if len(negative) != 1 or len(positive) != 1 or abs(negative[0].quantity) != abs(positive[0].quantity):
            self._issue(
                code="TRANSFER_PAIR_MISSING",
                transaction_id=tx.id,
                broker_id=tx.broker_id,
                related_transaction_id=tx.related_transaction_id,
                message="Transfer pair must have one negative leg, one positive leg, same absolute quantity.",
            )
            return None
        return negative[0], positive[0]

    @staticmethod
    def _event_sort_key(event: FifoEvent) -> tuple[date, int, int, int]:
        phase = 0 if event.kind == "TRANSFER_DEPART" else 1 if event.kind == "TRANSFER_ARRIVE" else 2 if event.kind == "SPLIT" else 3
        return event.date, phase, event.transaction_id, event.pair_id or event.transaction_id

    def _apply_buy(self, event: FifoEvent) -> None:
        closed = self._consume_broker_fragments(
            broker_id=_require_id(event.broker_id),
            direction="SHORT",
            quantity=_require_decimal(event.quantity),
            event_date=event.date,
            transaction_id=event.transaction_id,
            close_reason="BUY",
            close_unit_price=_require_decimal(event.unit_price),
        )
        remainder = _require_decimal(event.quantity) - closed
        if remainder > Decimal("0"):
            self._open_lot(
                transaction_id=event.transaction_id,
                broker_id=_require_id(event.broker_id),
                opened_at=event.date,
                direction="LONG",
                quantity=remainder,
                unit_price=_require_decimal(event.unit_price),
                currency=self._tx_by_id[event.transaction_id].currency,
                reference_resolution=None,
            )

    def _apply_sell(self, event: FifoEvent) -> None:
        broker_id = _require_id(event.broker_id)
        closed = self._consume_broker_fragments(
            broker_id=broker_id,
            direction="LONG",
            quantity=_require_decimal(event.quantity),
            event_date=event.date,
            transaction_id=event.transaction_id,
            close_reason="SELL",
            close_unit_price=_require_decimal(event.unit_price),
        )
        remainder = _require_decimal(event.quantity) - closed
        if remainder <= Decimal("0"):
            return
        if self.broker_shorting.get(broker_id, False):
            self._open_lot(
                transaction_id=event.transaction_id,
                broker_id=broker_id,
                opened_at=event.date,
                direction="SHORT",
                quantity=remainder,
                unit_price=_require_decimal(event.unit_price),
                currency=self._tx_by_id[event.transaction_id].currency,
                reference_resolution=None,
            )
            return
        self._issue(
            code="FIFO_SOURCE_QUANTITY_MISSING",
            transaction_id=event.transaction_id,
            broker_id=broker_id,
            message="SELL exceeds available LONG quantity and broker does not allow shorting.",
            params={"missing_quantity": remainder},
        )

    def _apply_adjustment_in(self, event: FifoEvent) -> None:
        broker_id = _require_id(event.broker_id)
        closed = self._consume_broker_fragments(
            broker_id=broker_id,
            direction="SHORT",
            quantity=_require_decimal(event.quantity),
            event_date=event.date,
            transaction_id=event.transaction_id,
            close_reason="BUY",
            close_unit_price=Decimal("0"),
        )
        remainder = _require_decimal(event.quantity) - closed
        if remainder <= Decimal("0"):
            return
        resolution = self._resolve_reference_price(self.asset_id, event.date)
        self._open_lot(
            transaction_id=event.transaction_id,
            broker_id=broker_id,
            opened_at=event.date,
            direction="LONG",
            quantity=remainder,
            unit_price=Decimal("0"),
            currency=self._tx_by_id[event.transaction_id].currency,
            reference_resolution=resolution,
        )
        if resolution.source == "fallback":
            self._issue(
                code="REFERENCE_PRICE_FALLBACK",
                transaction_id=event.transaction_id,
                lot_id=event.transaction_id,
                broker_id=broker_id,
                message="Reference price fallback used for ADJUSTMENT+ relative return.",
                params={"reference_price": resolution.price},
            )
        elif resolution.source == "unavailable":
            self._issue(
                code="REFERENCE_PRICE_UNAVAILABLE",
                transaction_id=event.transaction_id,
                lot_id=event.transaction_id,
                broker_id=broker_id,
                message="Reference price unavailable for ADJUSTMENT+ relative return.",
            )

    def _apply_adjustment_out(self, event: FifoEvent) -> None:
        broker_id = _require_id(event.broker_id)
        closed = self._consume_broker_fragments(
            broker_id=broker_id,
            direction="LONG",
            quantity=_require_decimal(event.quantity),
            event_date=event.date,
            transaction_id=event.transaction_id,
            close_reason="ADJUSTMENT_OUT",
            close_unit_price=Decimal("0"),
        )
        remainder = _require_decimal(event.quantity) - closed
        if remainder <= Decimal("0"):
            return
        if self.signed_quantity_for_broker(broker_id) < Decimal("0") or any(fragment.direction == "SHORT" for fragment in self._broker_fragments(broker_id, "SHORT")):
            self._issue(
                code="SHORT_ADJUSTMENT_NOT_SUPPORTED",
                transaction_id=event.transaction_id,
                broker_id=broker_id,
                message="ADJUSTMENT- cannot consume or open SHORT position in phase 1.",
                params={"missing_quantity": remainder},
            )
            return
        self._issue(
            code="FIFO_SOURCE_QUANTITY_MISSING",
            transaction_id=event.transaction_id,
            broker_id=broker_id,
            message="ADJUSTMENT- exceeds available LONG quantity.",
            params={"missing_quantity": remainder},
        )

    def _apply_transfer_depart(self, event: FifoEvent) -> None:
        pair_id = _require_id(event.pair_id)
        source_broker_id = _require_id(event.source_broker_id)
        destination_broker_id = _require_id(event.destination_broker_id)
        quantity = _require_decimal(event.quantity)
        if self.signed_quantity_for_broker(source_broker_id) < Decimal("0") or any(fragment.direction == "SHORT" for fragment in self._broker_fragments(source_broker_id, "SHORT")):
            self._issue(
                code="SHORT_TRANSFER_NOT_SUPPORTED",
                transaction_id=event.transaction_id,
                broker_id=source_broker_id,
                related_transaction_id=pair_id,
                message="Transfer of SHORT position is not supported in phase 1.",
            )
            return
        pieces = self._extract_transfer_pieces(
            source_broker_id=source_broker_id,
            destination_broker_id=destination_broker_id,
            quantity=quantity,
            transfer_date=_require_date(event.transit_start),
            pair_id=pair_id,
        )
        transferred = sum((piece.quantity for piece in pieces), Decimal("0"))
        remainder = quantity - transferred
        if remainder > Decimal("0"):
            self._issue(
                code="FIFO_SOURCE_QUANTITY_MISSING",
                transaction_id=event.transaction_id,
                broker_id=source_broker_id,
                related_transaction_id=pair_id,
                message="TRANSFER exceeds available LONG quantity on source broker.",
                params={"missing_quantity": remainder},
            )
        if pieces:
            self._pending_transfers[pair_id] = pieces

    def _apply_transfer_arrive(self, event: FifoEvent) -> None:
        pair_id = _require_id(event.pair_id)
        pieces = self._pending_transfers.pop(pair_id, [])
        if not pieces:
            return
        for piece in pieces:
            unit_price = piece.unit_price
            quantity = piece.quantity
            if piece.transit_fragment_id is not None:
                transit_fragment = self._active_fragments.get(piece.transit_fragment_id)
                if transit_fragment is None:
                    continue
                quantity = transit_fragment.quantity
                unit_price = transit_fragment.unit_price
                self._close_fragment(transit_fragment, piece.arrival_date)
            destination_fragment_id = f"lot:{piece.lot_id}/transfer:{piece.pair_id}/to:{piece.destination_broker_id}"
            self._open_fragment(
                fragment_id=destination_fragment_id,
                lot_id=piece.lot_id,
                direction=self._lots[piece.lot_id].direction,
                custody_type="BROKER",
                quantity=quantity,
                unit_price=unit_price,
                start_date=piece.arrival_date,
                broker_id=piece.destination_broker_id,
            )

    def _apply_split(self, event: FifoEvent) -> None:
        ratio = _require_decimal(event.ratio)
        broker_id = _require_id(event.broker_id)
        impacted = [fragment for fragment in self._active_fragments.values() if self._fragment_matches_split_scope(fragment, broker_id)]
        lot_open_qty_before = {fragment.lot_id: sum(current.quantity for current in self._active_fragments.values() if current.lot_id == fragment.lot_id) for fragment in impacted}
        for fragment in sorted(impacted, key=lambda item: (self._lots[item.lot_id].opening_date, item.fragment_id)):
            new_quantity = fragment.quantity * ratio
            new_unit_price = fragment.unit_price / ratio
            old_cost = fragment.quantity * fragment.unit_price
            self._transition_fragment(fragment, event.date, new_quantity=new_quantity, new_unit_price=new_unit_price)
            if abs(new_quantity * new_unit_price - old_cost) > _COST_INVARIANT_TOLERANCE:
                raise AssertionError("Split cost invariant violated")
        impacted_lot_ids = {fragment.lot_id for fragment in impacted}
        for lot_id in impacted_lot_ids:
            lot = self._lots[lot_id]
            lot.open_quantity = sum(fragment.quantity for fragment in self._active_fragments.values() if fragment.lot_id == lot_id)
            if lot.realized_quantity == Decimal("0"):
                lot.original_quantity = lot.open_quantity
            else:
                lot.original_quantity += lot.open_quantity - lot_open_qty_before[lot_id]
            lot.opening_unit_price = lot.original_cost / lot.original_quantity if lot.original_quantity else Decimal("0")
            if lot.reference_unit_price is not None and lot_open_qty_before[lot_id] > Decimal("0") and lot.open_quantity > Decimal("0"):
                lot.reference_unit_price *= lot_open_qty_before[lot_id] / lot.open_quantity
            if abs(lot.original_quantity * lot.opening_unit_price - lot.original_cost) > _COST_INVARIANT_TOLERANCE:
                raise AssertionError("Lot cost invariant violated")

    def _fragment_matches_split_scope(self, fragment: FragmentInterval, broker_id: int) -> bool:
        if fragment.custody_type == "BROKER":
            return fragment.broker_id == broker_id
        return fragment.source_broker_id == broker_id or fragment.destination_broker_id == broker_id

    def _extract_transfer_pieces(
        self,
        *,
        source_broker_id: int,
        destination_broker_id: int,
        quantity: Decimal,
        transfer_date: date,
        pair_id: int,
    ) -> list[_PendingTransferPiece]:
        pieces: list[_PendingTransferPiece] = []
        remaining = quantity
        for fragment in self._broker_fragments(source_broker_id, "LONG"):
            if remaining <= Decimal("0"):
                break
            matched = min(remaining, fragment.quantity)
            lot = self._lots[fragment.lot_id]
            source_remainder = fragment.quantity - matched
            unit_price = fragment.unit_price
            self._transition_fragment(fragment, transfer_date, new_quantity=source_remainder, new_unit_price=unit_price)
            transit_fragment_id: str | None = None
            arrival_date = self._pending_arrival_date(pair_id)
            if transfer_date < arrival_date:
                transit_fragment_id = f"lot:{lot.lot_id}/transfer:{pair_id}/transit"
                self._open_fragment(
                    fragment_id=transit_fragment_id,
                    lot_id=lot.lot_id,
                    direction=lot.direction,
                    custody_type="IN_TRANSIT",
                    quantity=matched,
                    unit_price=unit_price,
                    start_date=transfer_date,
                    source_broker_id=source_broker_id,
                    destination_broker_id=destination_broker_id,
                )
            pieces.append(
                _PendingTransferPiece(
                    pair_id=pair_id,
                    lot_id=lot.lot_id,
                    destination_broker_id=destination_broker_id,
                    arrival_date=arrival_date,
                    quantity=matched,
                    transit_fragment_id=transit_fragment_id,
                    unit_price=unit_price,
                )
            )
            remaining -= matched
        return pieces

    def _pending_arrival_date(self, pair_id: int) -> date:
        if pair_id not in self._transfer_arrival_dates:
            raise KeyError(f"Transfer pair {pair_id} arrival date not found")
        return self._transfer_arrival_dates[pair_id]

    def _consume_broker_fragments(
        self,
        *,
        broker_id: int,
        direction: Direction,
        quantity: Decimal,
        event_date: date,
        transaction_id: int,
        close_reason: Literal["SELL", "BUY", "ADJUSTMENT_OUT"],
        close_unit_price: Decimal,
    ) -> Decimal:
        consumed = Decimal("0")
        remaining = quantity
        for fragment in self._broker_fragments(broker_id, direction):
            if remaining <= Decimal("0"):
                break
            matched = min(remaining, fragment.quantity)
            self._close_position_piece(
                fragment=fragment,
                matched_quantity=matched,
                event_date=event_date,
                transaction_id=transaction_id,
                close_reason=close_reason,
                close_unit_price=close_unit_price,
            )
            consumed += matched
            remaining -= matched
        return consumed

    def _close_position_piece(
        self,
        *,
        fragment: FragmentInterval,
        matched_quantity: Decimal,
        event_date: date,
        transaction_id: int,
        close_reason: Literal["SELL", "BUY", "ADJUSTMENT_OUT"],
        close_unit_price: Decimal,
    ) -> None:
        lot = self._lots[fragment.lot_id]
        if lot.direction == "LONG":
            realized_pnl = matched_quantity * (close_unit_price - fragment.unit_price)
            proceeds = matched_quantity * close_unit_price if close_reason == "SELL" else Decimal("0")
        else:
            realized_pnl = matched_quantity * (fragment.unit_price - close_unit_price)
            proceeds = Decimal("0")
        lot.realized_quantity += matched_quantity
        lot.open_quantity -= matched_quantity
        lot.realized_pnl += realized_pnl
        lot.cumulative_proceeds += proceeds
        self._closures.append(
            LotClosure(
                lot_id=lot.lot_id,
                transaction_id=transaction_id,
                quantity=matched_quantity,
                close_date=event_date,
                close_reason=close_reason,
                fragment_id=fragment.fragment_id,
                open_unit_price=fragment.unit_price,
                close_unit_price=close_unit_price,
                realized_pnl=realized_pnl,
                proceeds=proceeds,
            )
        )
        remainder = fragment.quantity - matched_quantity
        self._transition_fragment(fragment, event_date, new_quantity=remainder, new_unit_price=fragment.unit_price)

    def _open_lot(
        self,
        *,
        transaction_id: int,
        broker_id: int,
        opened_at: date,
        direction: Direction,
        quantity: Decimal,
        unit_price: Decimal,
        currency: str | None,
        reference_resolution: ReferencePriceResolution | None,
    ) -> None:
        lot = FifoLot(
            lot_id=transaction_id,
            asset_id=self.asset_id,
            direction=direction,
            opening_transaction_id=transaction_id,
            opening_broker_id=broker_id,
            opening_date=opened_at,
            original_quantity=quantity,
            opening_unit_price=unit_price,
            original_cost=quantity * unit_price,
            currency=currency,
            open_quantity=quantity,
            cumulative_proceeds=quantity * unit_price if direction == "SHORT" else Decimal("0"),
            reference_unit_price=reference_resolution.price if reference_resolution else None,
            reference_price_source=reference_resolution.source if reference_resolution else None,
        )
        self._lots[transaction_id] = lot
        fragment_id = f"lot:{transaction_id}/origin:{broker_id}"
        self._open_fragment(
            fragment_id=fragment_id,
            lot_id=transaction_id,
            direction=direction,
            custody_type="BROKER",
            quantity=quantity,
            unit_price=unit_price,
            start_date=opened_at,
            broker_id=broker_id,
        )

    def _resolve_reference_price(self, asset_id: int, opened_at: date) -> ReferencePriceResolution:
        if self.reference_price_lookup is None:
            return ReferencePriceResolution(price=None, source="unavailable")
        result = self.reference_price_lookup(asset_id, opened_at)
        if result is None:
            return ReferencePriceResolution(price=None, source="unavailable")
        return result

    def _open_fragment(
        self,
        *,
        fragment_id: str,
        lot_id: int,
        direction: Direction,
        custody_type: CustodyType,
        quantity: Decimal,
        unit_price: Decimal,
        start_date: date,
        broker_id: int | None = None,
        source_broker_id: int | None = None,
        destination_broker_id: int | None = None,
    ) -> FragmentInterval:
        fragment = FragmentInterval(
            fragment_id=fragment_id,
            lot_id=lot_id,
            direction=direction,
            custody_type=custody_type,
            quantity=quantity,
            unit_price=unit_price,
            start_date=start_date,
            broker_id=broker_id,
            source_broker_id=source_broker_id,
            destination_broker_id=destination_broker_id,
        )
        self._intervals.append(fragment)
        self._active_fragments[fragment_id] = fragment
        return fragment

    def _close_fragment(self, fragment: FragmentInterval, event_date: date) -> None:
        fragment.end_date = event_date
        self._active_fragments.pop(fragment.fragment_id, None)

    def _transition_fragment(self, fragment: FragmentInterval, event_date: date, *, new_quantity: Decimal, new_unit_price: Decimal) -> None:
        self._close_fragment(fragment, event_date)
        if new_quantity <= Decimal("0"):
            return
        self._open_fragment(
            fragment_id=fragment.fragment_id,
            lot_id=fragment.lot_id,
            direction=fragment.direction,
            custody_type=fragment.custody_type,
            quantity=new_quantity,
            unit_price=new_unit_price,
            start_date=event_date,
            broker_id=fragment.broker_id,
            source_broker_id=fragment.source_broker_id,
            destination_broker_id=fragment.destination_broker_id,
        )

    def _broker_fragments(self, broker_id: int, direction: Direction) -> list[FragmentInterval]:
        return sorted(
            [fragment for fragment in self._active_fragments.values() if fragment.custody_type == "BROKER" and fragment.broker_id == broker_id and fragment.direction == direction],
            key=lambda fragment: (self._lots[fragment.lot_id].opening_date, fragment.lot_id, fragment.start_date, fragment.fragment_id),
        )

    def signed_quantity_for_broker(self, broker_id: int) -> Decimal:
        total = Decimal("0")
        for fragment in self._active_fragments.values():
            if fragment.custody_type != "BROKER" or fragment.broker_id != broker_id:
                continue
            sign = Decimal("1") if fragment.direction == "LONG" else Decimal("-1")
            total += sign * fragment.quantity
        return total

    def _issue(
        self,
        *,
        code: IssueCode,
        transaction_id: int | None,
        lot_id: int | None = None,
        broker_id: int | None = None,
        related_transaction_id: int | None = None,
        message: str,
        params: dict[str, str | int | Decimal | None] | None = None,
    ) -> None:
        self._issues.append(
            FifoDataQualityIssue(
                code=code,
                transaction_id=transaction_id,
                lot_id=lot_id,
                broker_id=broker_id,
                related_transaction_id=related_transaction_id,
                message=message,
                params=params or {},
            )
        )

    # ------------------------------------------------------------------
    # Economic allocation stage (post-replay): income now, FEE/TAX later.
    # Quantities, fragments and closures are never mutated here.
    # ------------------------------------------------------------------

    def _allocate_economics(self) -> _EconomicStageResult:
        stage = _EconomicStageResult()
        if not self.economic_events:
            return stage
        fragments_by_lot: dict[int, list[FragmentInterval]] = defaultdict(list)
        for fragment in self._intervals:
            fragments_by_lot[fragment.lot_id].append(fragment)
        mutable_accumulators: dict[int, dict[str, Decimal]] = {}

        income_events = [event for event in self.economic_events if event.economic_type in ("DIVIDEND", "INTEREST")]
        stage.orphan_income += self._allocate_income_pools(income_events, fragments_by_lot, stage.groups, mutable_accumulators)

        fee_events = [event for event in self.economic_events if event.economic_type == "FEE"]
        stage.orphan_fees += self._allocate_cost_pools(fee_events, "FEE", "allocated_fees", fragments_by_lot, stage.groups, mutable_accumulators)

        tax_events = [event for event in self.economic_events if event.economic_type == "TAX"]
        stage.orphan_taxes += self._allocate_cost_pools(tax_events, "TAX", "allocated_taxes", fragments_by_lot, stage.groups, mutable_accumulators)

        stage.accumulators = {lot_id: LotEconomicAccumulators(lot_id=lot_id, **values) for lot_id, values in mutable_accumulators.items()}
        return stage

    def _allocate_income_pools(
        self,
        income_events: Sequence[EconomicEvent],
        fragments_by_lot: dict[int, list[FragmentInterval]],
        groups: list[EconomicAllocationGroup],
        accumulators: dict[int, dict[str, Decimal]],
    ) -> Decimal:
        """Allocate DIVIDEND/INTEREST to lots eligible as of D-1 within the paying broker.

        Pool key = (broker, date, economic_type, native_currency, target_currency). Eligibility
        (open LONG quantity on ``date - 1``) is shared across DIVIDEND and INTEREST since it is a
        function of holdings, but the two remain distinct audit groups by economic_type. A pool is
        allocated entirely (running-remainder conserves the total) or, when no lot is eligible,
        recorded entirely as orphan income (returned to the caller for the asset-level total).
        """
        orphan_total = Decimal("0")
        pools: dict[tuple[int, date, str, str | None, str], list[EconomicEvent]] = defaultdict(list)
        for event in income_events:
            pools[(event.broker_id, event.date, event.economic_type, event.native_currency, event.target_currency)].append(event)
        for key in sorted(pools, key=lambda item: (item[1], item[0], str(item[2]), str(item[3] or ""))):
            broker_id, event_date, economic_type, native_currency, target_currency = key
            pool_events = pools[key]
            cutoff = event_date - timedelta(days=1)
            eligible: list[tuple[int, Decimal]] = []
            for lot_id, lot in self._lots.items():
                if lot.direction != "LONG":
                    continue
                quantity = self._eligible_income_quantity(fragments_by_lot.get(lot_id, ()), broker_id, cutoff)
                if quantity > Decimal("0"):
                    eligible.append((lot_id, quantity))
            eligible.sort(key=lambda item: item[0])
            native_pool = sum((abs(event.native_amount) for event in pool_events), Decimal("0"))
            target_pool = sum((abs(event.target_amount) for event in pool_events), Decimal("0"))
            source_ids = tuple(sorted(event.transaction_id for event in pool_events))
            if not eligible:
                orphan_total += target_pool
                self._issues.append(
                    FifoDataQualityIssue(
                        code="ASSET_INCOME_NO_ELIGIBLE_LOTS",
                        transaction_id=source_ids[0] if source_ids else None,
                        broker_id=broker_id,
                        params={
                            "economic_type": economic_type,
                            "as_of_date": event_date.isoformat(),
                            "target_amount": target_pool,
                            "target_currency": target_currency,
                        },
                    )
                )
                groups.append(
                    EconomicAllocationGroup(
                        economic_type=economic_type,
                        asset_id=self.asset_id,
                        broker_id=broker_id,
                        date=event_date,
                        native_currency=native_currency,
                        target_currency=target_currency,
                        rule="ASSET_INCOME_HOLDINGS",
                        source_transaction_ids=source_ids,
                        native_pool_total=native_pool,
                        target_pool_total=target_pool,
                        operation_allocations=(),
                        native_orphan=native_pool,
                        target_orphan=target_pool,
                    )
                )
                continue
            total_quantity = sum((quantity for _lot_id, quantity in eligible), Decimal("0"))
            lot_allocations: list[EconomicLotAllocation] = []
            remaining_target = target_pool
            remaining_native = native_pool
            for index, (lot_id, quantity) in enumerate(eligible):
                if index == len(eligible) - 1:
                    allocated_target = remaining_target
                    allocated_native = remaining_native
                else:
                    allocated_target = target_pool * quantity / total_quantity
                    allocated_native = native_pool * quantity / total_quantity
                    remaining_target -= allocated_target
                    remaining_native -= allocated_native
                accumulator = accumulators.setdefault(lot_id, _new_economic_accumulator())
                accumulator["gross_income"] += allocated_target
                lot_allocations.append(
                    EconomicLotAllocation(
                        lot_id=lot_id,
                        weight=quantity / total_quantity,
                        native_amount=allocated_native,
                        target_amount=allocated_target,
                    )
                )
            groups.append(
                EconomicAllocationGroup(
                    economic_type=economic_type,
                    asset_id=self.asset_id,
                    broker_id=broker_id,
                    date=event_date,
                    native_currency=native_currency,
                    target_currency=target_currency,
                    rule="ASSET_INCOME_HOLDINGS",
                    source_transaction_ids=source_ids,
                    native_pool_total=native_pool,
                    target_pool_total=target_pool,
                    operation_allocations=(
                        TargetOperationAllocation(
                            context="HOLDING",
                            operation_transaction_id=None,
                            weight=Decimal("1"),
                            lot_allocations=tuple(lot_allocations),
                        ),
                    ),
                )
            )
        return orphan_total

    @staticmethod
    def _eligible_income_quantity(fragments: Sequence[FragmentInterval], broker_id: int, cutoff: date) -> Decimal:
        """Open quantity attributable to ``broker_id`` as of ``cutoff`` (transfer-aware).

        Broker-custodied fragments count for their broker; in-transit fragments count for their
        SOURCE broker (the payer of record during transit), never the destination — which only
        becomes eligible once the arrival fragment exists on/after the arrival date.
        """
        total = Decimal("0")
        for fragment in fragments:
            if not (fragment.start_date <= cutoff and (fragment.end_date is None or cutoff < fragment.end_date)):
                continue
            if fragment.custody_type == "BROKER" and fragment.broker_id == broker_id:
                total += fragment.quantity
            elif fragment.custody_type == "IN_TRANSIT" and fragment.source_broker_id == broker_id:
                total += fragment.quantity
        return total

    # ------------------------------------------------------------------
    # FEE/TAX allocation (asset-linked costs). Deterministic matching order
    # (§4.3): FEE  = same-day trades -> previous-day trades -> holdings fallback -> orphan;
    #         TAX  = same-day income -> same-day trades -> previous-day income ->
    #                previous-day trades -> holdings fallback -> orphan.
    # Native and target totals are conserved by running-remainder at every split.
    # ------------------------------------------------------------------

    def _allocate_cost_pools(
        self,
        cost_events: Sequence[EconomicEvent],
        economic_type: EconomicType,
        accumulator_field: str,
        fragments_by_lot: dict[int, list[FragmentInterval]],
        groups: list[EconomicAllocationGroup],
        accumulators: dict[int, dict[str, Decimal]],
    ) -> Decimal:
        """Allocate FEE or TAX pools; returns the orphaned target total (unallocatable pools)."""
        orphan_total = Decimal("0")
        pools: dict[tuple[int, date, str | None, str], list[EconomicEvent]] = defaultdict(list)
        for event in cost_events:
            pools[(event.broker_id, event.date, event.native_currency, event.target_currency)].append(event)
        for key in sorted(pools, key=lambda item: (item[1], item[0], str(item[2] or ""))):
            broker_id, event_date, native_currency, target_currency = key
            pool_events = pools[key]
            native_pool = sum((abs(event.native_amount) for event in pool_events), Decimal("0"))
            target_pool = sum((abs(event.target_amount) for event in pool_events), Decimal("0"))
            source_ids = tuple(sorted(event.transaction_id for event in pool_events))
            operations, rule = self._match_cost_operations(
                economic_type=economic_type,
                broker_id=broker_id,
                event_date=event_date,
                native_pool=native_pool,
                target_pool=target_pool,
                fragments_by_lot=fragments_by_lot,
            )
            if operations is None:
                orphan_total += target_pool
                self._issues.append(
                    FifoDataQualityIssue(
                        code="ASSET_COST_NO_ELIGIBLE_LOTS",
                        transaction_id=source_ids[0] if source_ids else None,
                        broker_id=broker_id,
                        params={
                            "economic_type": economic_type,
                            "as_of_date": event_date.isoformat(),
                            "target_amount": target_pool,
                            "target_currency": target_currency,
                        },
                    )
                )
                groups.append(
                    EconomicAllocationGroup(
                        economic_type=economic_type,
                        asset_id=self.asset_id,
                        broker_id=broker_id,
                        date=event_date,
                        native_currency=native_currency,
                        target_currency=target_currency,
                        rule=rule,
                        source_transaction_ids=source_ids,
                        native_pool_total=native_pool,
                        target_pool_total=target_pool,
                        operation_allocations=(),
                        native_orphan=native_pool,
                        target_orphan=target_pool,
                    )
                )
                continue
            for operation in operations:
                for allocation in operation.lot_allocations:
                    accumulator = accumulators.setdefault(allocation.lot_id, _new_economic_accumulator())
                    accumulator[accumulator_field] += allocation.target_amount
            groups.append(
                EconomicAllocationGroup(
                    economic_type=economic_type,
                    asset_id=self.asset_id,
                    broker_id=broker_id,
                    date=event_date,
                    native_currency=native_currency,
                    target_currency=target_currency,
                    rule=rule,
                    source_transaction_ids=source_ids,
                    native_pool_total=native_pool,
                    target_pool_total=target_pool,
                    operation_allocations=tuple(operations),
                )
            )
        return orphan_total

    def _match_cost_operations(
        self,
        *,
        economic_type: EconomicType,
        broker_id: int,
        event_date: date,
        native_pool: Decimal,
        target_pool: Decimal,
        fragments_by_lot: dict[int, list[FragmentInterval]],
    ) -> tuple[list[TargetOperationAllocation] | None, AllocationRule]:
        """Resolve a pool to target operations following the matching order (§4.3).

        Returns ``(operations, rule)``; ``operations is None`` means the pool is orphan and
        ``rule`` records the level that failed (e.g. ``SAME_DAY_INCOME`` when a taxed income pool
        was itself orphan -> the whole TAX pool is orphan, no mixed allocated/orphan).
        """
        previous_day = event_date - timedelta(days=1)
        if economic_type == "TAX":
            if self._income_on(broker_id, event_date):
                # TAX follows the income it taxes: same D-1 holding weights (§4.2). If that income
                # was orphan (no eligible lot) the whole TAX pool is orphan -> stop here.
                ops = self._holding_operations(broker_id, event_date - timedelta(days=1), native_pool, target_pool, fragments_by_lot, "INCOME")
                return ops, "SAME_DAY_INCOME"
            same_day_trades = self._trades_on(broker_id, event_date)
            if same_day_trades:
                ops = self._trade_operations(same_day_trades, native_pool, target_pool)
                if ops is not None:
                    return ops, self._trade_rule(same_day_trades)
            if self._income_on(broker_id, previous_day):
                ops = self._holding_operations(broker_id, previous_day - timedelta(days=1), native_pool, target_pool, fragments_by_lot, "INCOME")
                return ops, "PREVIOUS_DAY_INCOME"
            previous_day_trades = self._trades_on(broker_id, previous_day)
            if previous_day_trades:
                ops = self._trade_operations(previous_day_trades, native_pool, target_pool)
                if ops is not None:
                    return ops, "PREVIOUS_DAY_TRADES"
            ops = self._holding_operations(broker_id, event_date - timedelta(days=1), native_pool, target_pool, fragments_by_lot, "HOLDING")
            return ops, "OPEN_LOTS_FALLBACK"

        # FEE
        same_day_trades = self._trades_on(broker_id, event_date)
        if same_day_trades:
            ops = self._trade_operations(same_day_trades, native_pool, target_pool)
            if ops is not None:
                return ops, self._trade_rule(same_day_trades)
        previous_day_trades = self._trades_on(broker_id, previous_day)
        if previous_day_trades:
            ops = self._trade_operations(previous_day_trades, native_pool, target_pool)
            if ops is not None:
                return ops, "PREVIOUS_DAY_TRADES"
        ops = self._holding_operations(broker_id, event_date - timedelta(days=1), native_pool, target_pool, fragments_by_lot, "HOLDING")
        return ops, "OPEN_LOTS_FALLBACK"

    def _income_on(self, broker_id: int, on_date: date) -> bool:
        return any(event.economic_type in ("DIVIDEND", "INTEREST") and event.broker_id == broker_id and event.date == on_date for event in self.economic_events)

    def _trades_on(self, broker_id: int, on_date: date) -> list[FifoInputTransaction]:
        """BUY/SELL of the broker on ``on_date`` (ADJUSTMENT/TRANSFER excluded), sorted by id."""
        return sorted(
            (tx for tx in self.transactions if tx.broker_id == broker_id and tx.date == on_date and tx.type in ("BUY", "SELL")),
            key=lambda tx: tx.id,
        )

    @staticmethod
    def _trade_rule(trades: Sequence[FifoInputTransaction]) -> AllocationRule:
        kinds = {tx.type for tx in trades}
        return "SAME_DAY_MIXED_TRADES" if "BUY" in kinds and "SELL" in kinds else "SAME_DAY_TRADES"

    @staticmethod
    def _trade_target_value(tx: FifoInputTransaction) -> Decimal:
        """Target-currency controvalue used as the pooling weight (§3.5).

        Falls back to the native amount when the service did not resolve a target (single-currency
        pools -> weights are ratios, so native and target give identical shares).
        """
        return abs(tx.target_amount) if tx.target_amount is not None else abs(tx.amount)

    def _trade_operations(
        self,
        trades: Sequence[FifoInputTransaction],
        native_pool: Decimal,
        target_pool: Decimal,
    ) -> list[TargetOperationAllocation] | None:
        """Distribute a cost pool over trades by target controvalue, then split each trade's quota
        into its OPENING and CLOSURE lots (crossing-safe). ``None`` when total trade value is zero."""
        values = [(tx, self._trade_target_value(tx)) for tx in trades]
        total_value = sum((value for _tx, value in values), Decimal("0"))
        if total_value <= Decimal("0"):
            return None
        operations: list[TargetOperationAllocation] = []
        remaining_native = native_pool
        remaining_target = target_pool
        for index, (tx, value) in enumerate(values):
            if index == len(values) - 1:
                trade_native = remaining_native
                trade_target = remaining_target
            else:
                trade_target = target_pool * value / total_value
                trade_native = native_pool * value / total_value
                remaining_target -= trade_target
                remaining_native -= trade_native
            operations.extend(self._split_trade_cost(tx, trade_native, trade_target, target_pool))
        return operations

    def _split_trade_cost(
        self,
        tx: FifoInputTransaction,
        native_share: Decimal,
        target_share: Decimal,
        pool_target: Decimal,
    ) -> list[TargetOperationAllocation]:
        """Split one trade's cost quota between the lots it opened (OPENING) and closed (CLOSURE).

        ``q = q_close + q_open`` (§5): ``Cost_close = share * q_close / q`` to closed lots by closed
        quantity; ``Cost_open`` (remainder) to opened lots by original quantity. Pure BUY -> OPENING
        only; pure SELL -> CLOSURE only; a crossing trade splits across both.
        """
        closed_by_lot: dict[int, Decimal] = defaultdict(Decimal)
        for closure in self._closures:
            if closure.transaction_id == tx.id:
                closed_by_lot[closure.lot_id] += closure.quantity
        opened_by_lot: dict[int, Decimal] = defaultdict(Decimal)
        for lot in self._lots.values():
            if lot.opening_transaction_id == tx.id:
                opened_by_lot[lot.lot_id] += lot.original_quantity
        q_close = sum(closed_by_lot.values(), Decimal("0"))
        q_open = sum(opened_by_lot.values(), Decimal("0"))
        total_q = q_close + q_open
        operations: list[TargetOperationAllocation] = []
        if total_q <= Decimal("0"):
            return operations
        open_target = target_share * q_open / total_q
        open_native = native_share * q_open / total_q
        close_target = target_share - open_target
        close_native = native_share - open_native
        if q_open > Decimal("0"):
            operations.append(self._lot_operation("OPENING", tx.id, sorted(opened_by_lot.items()), open_native, open_target, pool_target))
        if q_close > Decimal("0"):
            operations.append(self._lot_operation("CLOSURE", tx.id, sorted(closed_by_lot.items()), close_native, close_target, pool_target))
        return operations

    def _holding_operations(
        self,
        broker_id: int,
        cutoff: date,
        native_pool: Decimal,
        target_pool: Decimal,
        fragments_by_lot: dict[int, list[FragmentInterval]],
        context: AllocationContext,
    ) -> list[TargetOperationAllocation] | None:
        """Distribute the whole pool over LONG lots open at ``cutoff`` (D-1 holdings). ``None`` when
        no lot is eligible (orphan). Reused for the FEE/TAX holdings fallback and for TAX-on-income
        (same D-1 eligibility as the income, ``context=INCOME``)."""
        eligible: list[tuple[int, Decimal]] = []
        for lot_id, lot in self._lots.items():
            if lot.direction != "LONG":
                continue
            quantity = self._eligible_income_quantity(fragments_by_lot.get(lot_id, ()), broker_id, cutoff)
            if quantity > Decimal("0"):
                eligible.append((lot_id, quantity))
        if not eligible:
            return None
        eligible.sort(key=lambda item: item[0])
        return [self._lot_operation(context, None, eligible, native_pool, target_pool, target_pool)]

    def _lot_operation(
        self,
        context: AllocationContext,
        operation_transaction_id: int | None,
        lot_weights: Sequence[tuple[int, Decimal]],
        native_share: Decimal,
        target_share: Decimal,
        pool_target: Decimal,
    ) -> TargetOperationAllocation:
        """Build one audit operation, distributing ``*_share`` over lots by weight (running-remainder)."""
        total_weight = sum((weight for _lot_id, weight in lot_weights), Decimal("0"))
        lot_allocations: list[EconomicLotAllocation] = []
        remaining_native = native_share
        remaining_target = target_share
        for index, (lot_id, weight) in enumerate(lot_weights):
            if index == len(lot_weights) - 1 or total_weight <= Decimal("0"):
                allocated_target = remaining_target
                allocated_native = remaining_native
            else:
                allocated_target = target_share * weight / total_weight
                allocated_native = native_share * weight / total_weight
                remaining_target -= allocated_target
                remaining_native -= allocated_native
            lot_allocations.append(
                EconomicLotAllocation(
                    lot_id=lot_id,
                    weight=(weight / total_weight) if total_weight > Decimal("0") else Decimal("0"),
                    native_amount=allocated_native,
                    target_amount=allocated_target,
                )
            )
        operation_weight = (target_share / pool_target) if pool_target and pool_target != Decimal("0") else Decimal("1")
        return TargetOperationAllocation(
            context=context,
            operation_transaction_id=operation_transaction_id,
            weight=operation_weight,
            lot_allocations=tuple(lot_allocations),
        )


# ----------------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------------


def run_fifo_lot_engine(
    transactions: Sequence[TransactionLike | FifoInputTransaction],
    broker_shorting: dict[int, bool],
    *,
    split_ratios_by_tx_id: dict[int, Decimal] | None = None,
    reference_price_lookup: ReferencePriceLookup | None = None,
    economic_events: Sequence[EconomicEvent] = (),
    target_currency: str = "",
) -> FifoEngineResult:
    return FifoLotEngine(
        transactions=transactions,
        broker_shorting=broker_shorting,
        split_ratios_by_tx_id=split_ratios_by_tx_id,
        reference_price_lookup=reference_price_lookup,
        economic_events=economic_events,
        target_currency=target_currency,
    ).run()


# ----------------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------------


def _unit_price(amount: Decimal, quantity: Decimal) -> Decimal:
    if quantity == Decimal("0"):
        raise ValueError("Unit price requires non-zero quantity")
    return abs(amount) / abs(quantity)


def _new_economic_accumulator() -> dict[str, Decimal]:
    return {
        "original_cost": Decimal("0"),
        "sale_proceeds": Decimal("0"),
        "gross_income": Decimal("0"),
        "allocated_fees": Decimal("0"),
        "allocated_taxes": Decimal("0"),
        "open_value": Decimal("0"),
    }


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
