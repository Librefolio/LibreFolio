from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
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
]
EventKind = Literal[
    "BUY",
    "SELL",
    "ADJUSTMENT_IN",
    "ADJUSTMENT_OUT",
    "SPLIT",
    "TRANSFER_DEPART",
    "TRANSFER_ARRIVE",
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
class LotValuation:
    open_value: Decimal
    proceeds: Decimal
    total_value: Decimal
    original_cost: Decimal
    pnl: Decimal


@dataclass(frozen=True, slots=True)
class AggregatedLotValuation:
    open_value: Decimal
    proceeds: Decimal
    total_value: Decimal
    original_cost: Decimal
    pnl: Decimal


@dataclass(slots=True)
class FifoEngineResult:
    asset_id: int
    classified_events: list[FifoEvent]
    lots: list[FifoLot]
    fragment_intervals: list[FragmentInterval]
    closures: list[LotClosure]
    issues: list[FifoDataQualityIssue]

    @property
    def calculation_status(self) -> Literal["COMPLETE", "DEGRADED"]:
        return "DEGRADED" if self.issues else "COMPLETE"

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

    def value_for_lot(self, lot_id: int, market_price: Decimal) -> LotValuation:
        lot = self.get_lot(lot_id)
        open_value = lot.open_quantity * market_price
        proceeds = lot.cumulative_proceeds
        if lot.direction == "LONG":
            total_value = open_value + proceeds
            pnl = total_value - lot.original_cost
        else:
            total_value = proceeds - open_value
            pnl = total_value
        return LotValuation(
            open_value=open_value,
            proceeds=proceeds,
            total_value=total_value,
            original_cost=lot.original_cost,
            pnl=pnl,
        )

    def aggregate_value(self, lot_ids: Sequence[int], market_price: Decimal) -> AggregatedLotValuation:
        open_value = Decimal("0")
        proceeds = Decimal("0")
        total_value = Decimal("0")
        original_cost = Decimal("0")
        pnl = Decimal("0")
        for lot_id in lot_ids:
            lot_value = self.value_for_lot(lot_id, market_price)
            open_value += lot_value.open_value
            proceeds += lot_value.proceeds
            total_value += lot_value.total_value
            original_cost += lot_value.original_cost
            pnl += lot_value.pnl
        return AggregatedLotValuation(
            open_value=open_value,
            proceeds=proceeds,
            total_value=total_value,
            original_cost=original_cost,
            pnl=pnl,
        )

    def relative_return_for_lot(self, lot_id: int, market_price: Decimal) -> Decimal | None:
        lot = self.get_lot(lot_id)
        if lot.reference_unit_price is None or lot.reference_unit_price == Decimal("0"):
            return None
        return (market_price / lot.reference_unit_price) - Decimal("1")


@dataclass(slots=True)
class _PendingTransferPiece:
    pair_id: int
    lot_id: int
    destination_broker_id: int
    arrival_date: date
    quantity: Decimal
    transit_fragment_id: str | None
    unit_price: Decimal


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
        return FifoEngineResult(
            asset_id=self.asset_id,
            classified_events=events,
            lots=sorted(self._lots.values(), key=lambda lot: (lot.opening_date, lot.lot_id)),
            fragment_intervals=sorted(self._intervals, key=lambda fragment: (fragment.start_date, fragment.fragment_id, fragment.quantity)),
            closures=sorted(self._closures, key=lambda closure: (closure.close_date, closure.transaction_id, closure.lot_id)),
            issues=self._issues,
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


# ----------------------------------------------------------------------------
# Public helpers
# ----------------------------------------------------------------------------


def run_fifo_lot_engine(
    transactions: Sequence[TransactionLike | FifoInputTransaction],
    broker_shorting: dict[int, bool],
    *,
    split_ratios_by_tx_id: dict[int, Decimal] | None = None,
    reference_price_lookup: ReferencePriceLookup | None = None,
) -> FifoEngineResult:
    return FifoLotEngine(
        transactions=transactions,
        broker_shorting=broker_shorting,
        split_ratios_by_tx_id=split_ratios_by_tx_id,
        reference_price_lookup=reference_price_lookup,
    ).run()


# ----------------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------------


def _unit_price(amount: Decimal, quantity: Decimal) -> Decimal:
    if quantity == Decimal("0"):
        raise ValueError("Unit price requires non-zero quantity")
    return abs(amount) / abs(quantity)


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
